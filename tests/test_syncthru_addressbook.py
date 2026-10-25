import http.client
import threading
import unittest
from unittest.mock import patch

import syncthru_addressbook as s


FIXTURE = b'{max_individual:200,GXI_S2SERVER_SUPPORT:0,GXI_INSTALL_OPTION_HDD:2}'


class AddressBookViewTests(unittest.TestCase):
    def test_only_presentation_flag_changes(self):
        result = s.override_capability(FIXTURE)
        self.assertEqual(result, FIXTURE.replace(b'SUPPORT:0', b'SUPPORT:1'))
        self.assertEqual(s.override_capability(result), result)
        self.assertEqual(s.override_capability(b'{"max_individual":200,"GXI_S2SERVER_SUPPORT":0}'),
                         b'{"max_individual":200,"GXI_S2SERVER_SUPPORT":1}')

    def test_unknown_capabilities_fail_closed(self):
        for body in [b'login page', b'{GXI_S2SERVER_SUPPORT:0}',
                     b'{max_individual:200,GXI_S2SERVER_SUPPORT:true}',
                     b'{max_individual:200,GXI_S2SERVER_SUPPORT:2}',
                     b'{max_individual:200,GXI_S2SERVER_SUPPORT:0,GXI_S2SERVER_SUPPORT:1}']:
            with self.subTest(body=body), self.assertRaises(s.SetupError):
                s.override_capability(body)

    def test_routes_block_system_firmware_and_addressbook_writes_by_default(self):
        for path in ['/sws/app/maintenance/fw/upgrade.jsp', '/sws/app/gnb/jobs/Cancel.jsp',
                     '/sws/app/settings/network/set.jsp']:
            self.assertFalse(s.route_allowed('POST', path, True))
        path = s.ADDRESSBOOK + 'SetIndividualInABook.jsp'
        self.assertFalse(s.route_allowed('POST', path, False))
        self.assertTrue(s.route_allowed('POST', path, True))
        self.assertFalse(s.route_allowed('GET', path, True))
        self.assertFalse(s.route_allowed('DELETE', path, True))
        self.assertTrue(s.route_allowed('POST', s.LOGIN, False))

    def test_ambiguous_and_foreign_paths_are_rejected(self):
        for path in ['http://evil.invalid/sws/app/a.json', '//evil.invalid/sws/a',
                     '/sws/../a', '/sws/%2e%2e/a', '/sws/a\\b', '/sws//a', '/other']:
            with self.subTest(path=path), self.assertRaises(s.SetupError):
                s.clean_path(path)
        self.assertEqual(s.clean_path(s.CAPABILITIES + '?cache=123'), s.CAPABILITIES)

    def test_live_handler_rejects_rebinding_foreign_origin_and_default_write(self):
        with s.AddressBookServer(0, '192.0.2.10') as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for headers, method, path in [
                    ({'Host': 'evil.invalid'}, 'GET', '/sws/index.html'),
                    ({'Host': server.local_host, 'Origin': 'http://evil.invalid'}, 'POST', s.LOGIN),
                    ({'Host': server.local_host, 'Origin': server.origin}, 'POST', s.ADDRESSBOOK + 'SetIndividualInABook.jsp'),
                    ({'Host': server.local_host, 'Sec-Fetch-Site': 'cross-site'}, 'GET', '/sws/index.html'),
                ]:
                    with patch.object(s.http.client, 'HTTPConnection') as upstream:
                        # Save the genuine class before mocking the module's reference.
                        conn = REAL_CONNECTION('127.0.0.1', server.server_port, timeout=3)
                        conn.request(method, path, headers=headers)
                        response = conn.getresponse()
                        self.assertEqual(response.status, 403)
                        response.read()
                        conn.close()
                        upstream.assert_not_called()
            finally:
                server.shutdown()
                thread.join(3)


REAL_CONNECTION = http.client.HTTPConnection

if __name__ == '__main__':
    unittest.main()
