#!/usr/bin/env python3
"""Local view of the printer's ORIGINAL SMB/FTP address-book dialogs.

Temporary browser-side presentation override, not a firmware patch. Only the
GXI_S2SERVER_SUPPORT field of abook.json is changed. Credentials and vendor
scripts are never saved. The printer still performs all address-book work.
"""
import argparse
import http.client
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from configure_smb import SetupError, parse_sws, printer_url


CAPABILITIES = "/sws/app/addressbook/abook.json"
ADDRESSBOOK = "/sws/app/addressbook/"
LOGIN = "/sws/app/gnb/login/login.jsp"
MAX_REQUEST = 1024 * 1024
MAX_RESPONSE = 8 * 1024 * 1024
HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate",
               "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"}
READ_POSTS = {
    "GetIndividualInABook.jsp", "GetGroupInABook.jsp", "GetUsedSpeedNoInABook.jsp",
    "GetUsedMemberNoOfGroupInABook.jsp", "GetSMBTestStatus.jsp", "GetFTPTestStatus.jsp",
}
WRITE_POSTS = {
    "SetIndividualInABook.jsp", "SetGroupInABook.jsp", "CreateGroupInABook.jsp",
    "EditMemberOfGroupInABook.jsp", "RequestSMBTest.jsp", "RequestFTPTest.jsp",
}


def override_capability(body):
    """Fail closed unless precisely one known numeric support field is present."""
    try:
        value = parse_sws(body.decode("utf-8"))
    except (UnicodeDecodeError, SetupError) as exc:
        raise SetupError("Unbekanntes Format von abook.json; keine Änderung.") from exc
    if (not isinstance(value, dict) or type(value.get("GXI_S2SERVER_SUPPORT")) is not int
            or value["GXI_S2SERVER_SUPPORT"] not in (0, 1)
            or type(value.get("max_individual")) is not int):
        raise SetupError("Unbekannte Adressbuch-Fähigkeiten; keine Änderung.")
    pattern = rb'(?<![\w"])(?:"GXI_S2SERVER_SUPPORT"|GXI_S2SERVER_SUPPORT)\s*:\s*[01](?![\w.])'
    matches = list(re.finditer(pattern, body))
    if len(matches) != 1:
        raise SetupError("Adressbuch-Feld ist nicht eindeutig; keine Änderung.")
    match = matches[0]
    changed = body[:match.end() - 1] + b"1" + body[match.end():]
    expected = dict(value, GXI_S2SERVER_SUPPORT=1)
    if parse_sws(changed.decode("utf-8")) != expected:
        raise SetupError("Adressbuch-Prüfung fehlgeschlagen; keine Änderung.")
    return changed


def clean_path(target):
    parsed = urlsplit(target)
    if (parsed.scheme or parsed.netloc or parsed.fragment or not parsed.path.startswith("/sws/")
            or "%" in parsed.path or "\\" in parsed.path or "//" in parsed.path
            or any(part in (".", "..") for part in parsed.path.split("/"))):
        raise SetupError("Nur direkte SyncThru-Pfade sind erlaubt.")
    return parsed.path


def route_allowed(method, path, allow_writes):
    if method in ("GET", "HEAD"):
        return not path.endswith(".jsp") or path.startswith(ADDRESSBOOK) and path[len(ADDRESSBOOK):] in READ_POSTS
    if method != "POST":
        return False
    if path == LOGIN:
        return True
    if path == CAPABILITIES:
        return True
    if not path.startswith(ADDRESSBOOK):
        return False
    name = path[len(ADDRESSBOOK):]
    return name in READ_POSTS or allow_writes and name in WRITE_POSTS


class AddressBookServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, port, target, allow_writes=False, trace=False):
        self.target = urlsplit(printer_url(target))
        self.allow_writes = allow_writes
        self.trace = trace
        super().__init__(("127.0.0.1", port), Handler)
        self.local_host = "127.0.0.1:" + str(self.server_port)
        self.origin = "http://" + self.local_host


class Handler(BaseHTTPRequestHandler):
    # No URL/query/body/authentication data in ordinary access/error logs.
    def log_message(self, format, *args):
        pass

    def error(self, status, message):
        body = (message + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def forward(self):
        conn = None
        try:
            self.connection.settimeout(20)
            if self.headers.get("Host") != self.server.local_host:
                return self.error(403, "Nur der angezeigte lokale Browserzugriff ist erlaubt.")
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                return self.error(403, "Seitenfremde Anfragen sind gesperrt.")
            path = clean_path(self.path)
            if not route_allowed(self.command, path, self.server.allow_writes):
                if self.server.trace:
                    print("Gesperrt:", self.command, path, flush=True)
                return self.error(403, "Dieser Aufruf gehört nicht zur freigegebenen Adressbuchpflege.")
            if self.command == "POST":
                origin = self.headers.get("Origin")
                referer = self.headers.get("Referer", "")
                if origin != self.server.origin and not (origin is None and referer.startswith(self.server.origin + "/")):
                    return self.error(403, "Adressbuchänderungen erfordern denselben lokalen Browserursprung.")
            if self.headers.get("Transfer-Encoding"):
                return self.error(400, "Transfer-Encoding wird nicht angenommen.")
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) > 1 or lengths and not re.fullmatch(r"[0-9]+", lengths[0]):
                return self.error(400, "Ungültige Anfragegröße.")
            length = int(lengths[0]) if lengths else 0
            if length > MAX_REQUEST or self.command != "POST" and length:
                return self.error(413, "Anfrage ist zu groß oder hat einen unerwarteten Inhalt.")
            body = self.rfile.read(length) if length else None
            if body is not None and len(body) != length:
                return self.error(400, "Anfrage ist unvollständig.")
            target = self.server.target
            connection_type = http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
            conn = connection_type(target.hostname, target.port, timeout=12)
            connection_tokens = {v.strip().lower() for v in self.headers.get("Connection", "").split(",")}
            excluded = HOP_HEADERS | connection_tokens | {"host", "accept-encoding", "origin", "referer", "content-length"}
            headers = {k: v for k, v in self.headers.items() if k.lower() not in excluded}
            headers["Accept-Encoding"] = "identity"
            headers["Connection"] = "close"
            if self.command == "POST":
                headers["Content-Length"] = str(length)
                headers["Origin"] = target.scheme + "://" + target.netloc
                headers["Referer"] = headers["Origin"] + "/sws/index.html"
            conn.request(self.command, self.path, body=body, headers=headers)
            upstream = conn.getresponse()
            response_body = upstream.read(MAX_RESPONSE + 1)
            if len(response_body) > MAX_RESPONSE:
                return self.error(502, "Druckerantwort ist unerwartet groß.")
            if path == CAPABILITIES and self.command != "HEAD" and upstream.status == 200:
                if upstream.getheader("Content-Encoding", "identity").lower() != "identity":
                    return self.error(502, "Komprimierte Fähigkeitenantwort wird nicht verändert.")
                response_body = override_capability(response_body)
            response_headers = []
            connection_tokens = {v.strip().lower() for v in upstream.getheader("Connection", "").split(",")}
            excluded = HOP_HEADERS | connection_tokens | {"content-length", "cache-control", "etag", "expires", "last-modified"}
            for key, value in upstream.getheaders():
                if key.lower() in excluded:
                    continue
                if key.lower() == "location":
                    redirect = urlsplit(value)
                    if redirect.netloc and (redirect.netloc != target.netloc or redirect.scheme != target.scheme):
                        return self.error(502, "Weiterleitung zu einem anderen Gerät ist gesperrt.")
                    redirect_path = (redirect.path or "/sws/index.html") + ("?" + redirect.query if redirect.query else "")
                    clean_path(redirect_path)
                    value = redirect_path
                if key.lower() == "set-cookie":
                    value = re.sub(r";\s*Domain=[^;]*", "", value, flags=re.I)
                response_headers.append((key, value))
            self.send_response(upstream.status)
            for key, value in response_headers:
                self.send_header(key, value)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(response_body)
        except (SetupError, ValueError):
            self.error(502, "Unbekannter Pfad oder Antwortaufbau; keine Freischaltung vorgenommen.")
        except (OSError, http.client.HTTPException):
            self.error(502, "Drucker nicht erreichbar oder Antwort unvollständig. Schreibaufrufe werden nicht wiederholt.")
        finally:
            if conn:
                conn.close()

    do_GET = forward
    do_HEAD = forward
    do_POST = forward


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("printer", help="Drucker-IP oder http(s)://Drucker-IP")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--allow-addressbook-writes", action="store_true",
                        help="Originales Speichern/Löschen und SMB-/FTP-Servertests erlauben")
    parser.add_argument("--trace", action="store_true", help="Nur gesperrte Methoden/Pfade ohne Anfragewerte anzeigen")
    args = parser.parse_args()
    try:
        with AddressBookServer(args.port, args.printer, args.allow_addressbook_writes, args.trace) as server:
            print("Originale SyncThru-Oberfläche:", server.origin + "/sws/index.html", flush=True)
            print("Temporäre Ansicht: nur SMB-/FTP-Felder des Adressbuchs eingeblendet.", flush=True)
            print("Adressbuch speichern/löschen:", "erlaubt" if args.allow_addressbook_writes else "gesperrt (nur ansehen)", flush=True)
            print("Keine Firmwareänderung. Beenden mit Strg+C.", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except (OSError, SetupError, ValueError) as exc:
        print("Start fehlgeschlagen:", str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
