import unittest
from unittest.mock import Mock, patch

import configure_smb as c


class ConfigurationTests(unittest.TestCase):
    def test_vendor_response_with_bare_keys_and_nested_records(self):
        result = c.parse_sws('{success: true, recordData: [{ispeedNo: 1, iname: "Scans", '
                             'smb: {addr: "192.0.2.20", anonymous: 1}}]}')
        self.assertEqual(result["recordData"][0]["smb"]["anonymous"], 1)

    def test_strings_are_not_rewritten_and_executable_input_is_rejected(self):
        self.assertEqual(c.parse_sws('{name: "{key: value} \\"ok\\""}')["name"], '{key: value} "ok"')
        for value in ['{success: doSomething()}', '{a:1,a:2}', '{success:true};evil()', '{a:[1,]}']:
            with self.subTest(value=value), self.assertRaises(c.SetupError):
                c.parse_sws(value)

    def test_url_cannot_include_credentials_paths_or_redirects(self):
        self.assertEqual(c.printer_url("192.0.2.10"), "http://192.0.2.10")
        for url in ["ftp://192.0.2.10", "http://user:secret@192.0.2.10", "http://192.0.2.10/path",
                    "http://192.0.2.10/?token=1"]:
            with self.subTest(url=url), self.assertRaises(c.SetupError):
                c.printer_url(url)
        with self.assertRaises(c.SetupError):
            c.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "http://example.invalid")

    def test_guest_entry_contains_no_nas_password_or_edit_command(self):
        result = c.guest_parameters(2, "Scans", "192.0.2.20", "Scans")
        self.assertEqual(result["cmd"], "add")
        self.assertEqual(result["smb_password"], "")
        self.assertEqual(result["smb_anonymous"], 1)
        self.assertEqual(result["favorite"], 1)
        for server, share in [("smb://NAS", "Scans"), ("NAS", "../Scans"), ("NAS", "Scans/sub")]:
            with self.subTest(server=server, share=share), self.assertRaises(c.SetupError):
                c.guest_parameters(2, "Scans", server, share)

    def test_unknown_used_number_format_fails_closed(self):
        client = c.Client("192.0.2.10", "admin", "not a real password")
        with patch.object(client, "post", return_value={"usedSpeedNo": "1,2"}):
            self.assertEqual(client.used(), {1, 2})
        with patch.object(client, "post", return_value={"usedSpeedNo": "unknown"}):
            with self.assertRaises(c.SetupError):
                client.used()

    def test_readback_uses_vendor_list_selector_and_handles_pagination(self):
        client = c.Client("192.0.2.10", "admin", "not a real password")
        responses = [
            {"recordData": [{"ispeedNo": 2}], "TotalCount": 2},
            {"recordData": [{"ispeedNo": 1, "iname": "Scans"}], "TotalCount": 2},
        ]
        with patch.object(client, "post", side_effect=responses) as request:
            self.assertEqual(client.read_entry(1)["iname"], "Scans")
            self.assertEqual(request.call_args_list[0].args[1]["ispeedNo"], 0)
            self.assertEqual(request.call_args_list[1].args[1]["start"], 1)

    def test_cancelled_setup_never_sends_a_write(self):
        client = Mock()
        client.used.return_value = {1}
        answers = ["192.0.2.10", "admin", "Scans", "192.0.2.20", "Scans", "NEIN"]
        with patch.object(c, "Client", return_value=client), patch("builtins.input", side_effect=answers), \
                patch.object(c.getpass, "getpass", return_value="not real"), patch("builtins.print"):
            self.assertEqual(c.main(), 0)
        client.post.assert_not_called()

    def test_ambiguous_write_is_not_retried(self):
        client = Mock()
        client.used.return_value = {1}
        client.post.side_effect = c.URLError("timeout")
        answers = ["192.0.2.10", "admin", "Scans", "192.0.2.20", "Scans", "JA"]
        with patch.object(c, "Client", return_value=client), patch("builtins.input", side_effect=answers), \
                patch.object(c.getpass, "getpass", return_value="not real"), patch("builtins.print"):
            with self.assertRaisesRegex(c.SetupError, "unklar"):
                c.main()
        self.assertEqual(client.post.call_count, 1)
        self.assertEqual(client.post.call_args.args[0], "SetIndividualInABook.jsp")
        self.assertEqual(client.post.call_args.args[1]["ispeedNo"], 2)


if __name__ == "__main__":
    unittest.main()
