#!/usr/bin/env python3
"""Optional interactive SyncThru helper for one GUEST SMB address-book entry.

This is separate from the offline firmware patcher. It contacts only the
printer address entered by the user. No firmware upload, scanning, shell,
internal-network trick, NAS connection, or existing-entry modification.
"""
import base64
import getpass
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import (HTTPRedirectHandler, HTTPSHandler, ProxyHandler,
                            Request, build_opener)


class SetupError(ValueError):
    pass


def parse_sws(text):
    """Parse the vendor's JSON-like data with bare keys. Never evaluate JS."""
    position = 0
    decoder = json.JSONDecoder()

    def whitespace():
        nonlocal position
        while position < len(text) and text[position].isspace():
            position += 1

    def token():
        nonlocal position
        whitespace()
        match = re.match(r"[A-Za-z_][A-Za-z_0-9]*", text[position:])
        if not match:
            raise SetupError("Unerwartete Antwort des Druckers.")
        position += len(match.group())
        return match.group()

    def value(depth=0):
        nonlocal position
        whitespace()
        if depth > 20 or position >= len(text):
            raise SetupError("Unvollständige oder zu komplexe Druckerantwort.")
        character = text[position]
        if character == "{":
            position += 1
            result = {}
            whitespace()
            if position < len(text) and text[position] == "}":
                position += 1
                return result
            while True:
                whitespace()
                if position < len(text) and text[position] == '"':
                    key, position = decoder.raw_decode(text, position)
                else:
                    key = token()
                whitespace()
                if key in result or position >= len(text) or text[position] != ":":
                    raise SetupError("Ungültiges oder doppeltes Antwortfeld.")
                position += 1
                result[key] = value(depth + 1)
                whitespace()
                if position < len(text) and text[position] == "}":
                    position += 1
                    return result
                if position >= len(text) or text[position] != ",":
                    raise SetupError("Ungültiges Antwortobjekt.")
                position += 1
        if character == "[":
            position += 1
            result = []
            whitespace()
            if position < len(text) and text[position] == "]":
                position += 1
                return result
            while True:
                result.append(value(depth + 1))
                whitespace()
                if position < len(text) and text[position] == "]":
                    position += 1
                    return result
                if position >= len(text) or text[position] != ",":
                    raise SetupError("Ungültige Antwortliste.")
                position += 1
        try:
            result, position = decoder.raw_decode(text, position)
            return result
        except json.JSONDecodeError as exc:
            raise SetupError("Die Druckerantwort enthält keine erlaubten Daten.") from exc

    result = value()
    whitespace()
    if position != len(text):
        raise SetupError("Zusätzliche Daten nach der Druckerantwort.")
    return result


def printer_url(value):
    if "://" not in value:
        value = "http://" + value
    parsed = urlsplit(value)
    if (parsed.scheme not in ("http", "https") or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/")):
        raise SetupError("Nur Drucker-IP oder http(s)://Drucker-IP eingeben, ohne weiteren Pfad.")
    return value.rstrip("/")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SetupError("Weiterleitung abgelehnt; die Zugangsdaten werden nicht weitergereicht.")


class Client:
    ROUTES = {"GetUsedSpeedNoInABook.jsp", "GetIndividualInABook.jsp",
              "SetIndividualInABook.jsp"}

    def __init__(self, address, username, password):
        self.address = printer_url(address)
        self.auth = "Basic " + base64.b64encode((username + ":" + password).encode()).decode()
        # Avoid proxying printer credentials. HTTPS uses normal certificate verification.
        self.opener = build_opener(ProxyHandler({}), HTTPSHandler(), NoRedirect())

    def post(self, route, parameters):
        if route not in self.ROUTES:
            raise SetupError("Nicht erlaubter Aufruf.")
        request = Request(self.address + "/sws/app/addressbook/" + route,
            data=urlencode(parameters).encode(), method="POST",
            headers={"Authorization": self.auth, "Cookie": "Authentication=" + self.auth,
                     "Content-Type": "application/x-www-form-urlencoded"})
        with self.opener.open(request, timeout=12) as response:
            data = response.read(262145)
        if len(data) > 262144:
            raise SetupError("Druckerantwort ist unerwartet groß.")
        result = parse_sws(data.decode("utf-8"))
        if not isinstance(result, dict) or result.get("success") is not True:
            raise SetupError("Drucker lehnt die Anfrage ab; Zugangsdaten und Gerät prüfen.")
        return result

    def used(self):
        value = self.post("GetUsedSpeedNoInABook.jsp", {"type": 0}).get("usedSpeedNo")
        if not isinstance(value, str) or not re.fullmatch(r"\s*(?:\d+(?:\s*,\s*\d+)*)?\s*", value):
            raise SetupError("Belegte Kurzwahlnummern nicht sicher lesbar; nichts wurde gespeichert.")
        return {int(v) for v in re.findall(r"\d+", value)}

    def read_entry(self, slot):
        # The vendor's list API uses ispeedNo=0 here; passing the desired
        # contact number does not reliably select that contact on .04.06.
        start = 0
        for _ in range(100):
            result = self.post("GetIndividualInABook.jsp", dict(
                ispeedNo=0, condition=10, keyword=1, sort=1, sortField=1, start=start, limit=30))
            rows, count = result.get("recordData"), result.get("TotalCount")
            if not isinstance(rows, list) or not isinstance(count, int) or count < 0:
                raise SetupError("Adressbuch konnte nicht eindeutig gelesen werden.")
            record = next((r for r in rows if isinstance(r, dict) and r.get("ispeedNo") == slot), None)
            if record is not None:
                return record
            start += len(rows)
            if not rows or start >= count:
                return None
        raise SetupError("Adressbuch überschreitet die begrenzte Rückleseprüfung.")


def guest_parameters(slot, name, server, share):
    if not 1 <= slot <= 50:
        raise SetupError("Dieser Helfer verwendet nur Kurzwahl 1 bis 50.")
    if not name or len(name) > 30 or not server or len(server) > 128:
        raise SetupError("Name oder NAS-Adresse fehlt oder ist zu lang.")
    if not re.fullmatch(r"[A-Za-z0-9 +.,'/*#&@-]{1,30}", name):
        raise SetupError("Anzeigename: Buchstaben A-Z, Ziffern oder Leerzeichen verwenden. "
                         "Der originale SyncThru-Editor akzeptiert z. B. keinen Unterstrich. "
                         "Der Freigabename darf weiterhin Unterstriche enthalten.")
    if "://" in server or "/" in server or "\\" in server:
        raise SetupError("NAS-IP/Hostname eingeben, keine smb://-URL und keinen Pfad.")
    if not share or len(share) > 128 or share in (".", "..") or any(c in share for c in "/\\"):
        raise SetupError("Nur den Freigabenamen eingeben, z. B. Scans, keinen lokalen NAS-Pfad.")
    return dict(cmd="add", ispeedNo=slot, iname=name, favorite=1, fax="", email="",
        smb_added=1, smb_addr=server, smb_port=445, smb_anonymous=1, smb_id="",
        smb_password="", smb_domain="", smb_sharedFolder=share, smb_filePrefix="Scan",
        smb_filingPolicy=3, smb_folderPolicy=0, smb_folderDateFormat=1,
        ftp_added=0, ftp_password="")


def main():
    print("SMB-GASTZIEL im Druckeradressbuch eintragen – keine Firmware und kein Scan.\n"
          "Voraussetzung: eigenes vertrauenswürdiges LAN und bereits eingerichtete\n"
          "SMB-Freigabe mit Schreibrecht für Gast. NAS-Kennwörter unterstützt dieser Helfer nicht.\n"
          "Zuerst Konfiguration in SyncThru sichern; siehe docs/ANLEITUNG.md.\n")
    address = printer_url(input("Drucker-IP (nicht die NAS-IP): ").strip())
    if address.startswith("http://"):
        print("Hinweis: Die alte HTTP-Weboberfläche überträgt Admin-Zugangsdaten unverschlüsselt.")
    username = input("SyncThru-Benutzername [admin]: ").strip() or "admin"
    password = getpass.getpass("Bestehendes SyncThru-Passwort: ")
    client = Client(address, username, password)
    used = client.used()
    slot = next((n for n in range(1, 51) if n not in used), None)
    if slot is None:
        raise SetupError("Keine freie Nummer zwischen 1 und 50. Keine Änderung vorgenommen.")
    name = input("Name am Display [Scans]: ").strip() or "Scans"
    server = input("NAS-IP/Hostname (z. B. 192.168.1.20): ").strip()
    share = input("SMB-Freigabename (z. B. Scans): ").strip()
    parameters = guest_parameters(slot, name, server, share)
    print(f"\nDrucker: {address}\nNeuer Favorit: {name}, Kurzwahl {slot}\n"
          f"SMB-Ziel: {server}:445 / {share}\nAnmeldung: Gast\n"
          "Vorhandene Einträge werden nicht bearbeitet. Es wird kein Scan ausgelöst.")
    if input("Diesen neuen Eintrag speichern? Genau JA eingeben: ").strip() != "JA":
        print("Abgebrochen. Nichts gespeichert.")
        return 0
    if slot in client.used():
        raise SetupError("Nummer ist inzwischen belegt. Nichts gespeichert.")
    try:
        client.post("SetIndividualInABook.jsp", parameters)
    except Exception as exc:
        raise SetupError("Speicherergebnis unklar. Nicht blind wiederholen: zuerst im "
                         "Adressbuch nachsehen. Es erfolgt kein automatischer Wiederholungsversuch.") from exc
    record = client.read_entry(slot)
    expected = {"addr": server, "port": 445, "anonymous": 1, "sharedFolder": share}
    if (record is None or record.get("iname") != name or record.get("favorite") != 1
            or any(record.get("smb", {}).get(k) != v for k, v in expected.items())):
        raise SetupError("Speichern wurde bestätigt, Rücklesen aber nicht eindeutig verifiziert. "
                         "Adressbuch am Drucker prüfen; nicht erneut hinzufügen.")
    print("\nGespeichert und vom Drucker zurückgelesen.\n"
          "Am Display: Scan → SMB Scan → Next → Ziel auswählen → Start.\n"
          "Anschließend die neue Datei im NAS-Ordner kontrollieren.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SetupError, OSError, HTTPError, URLError, ValueError) as exc:
        print("FEHLER:", exc, file=sys.stderr)
        raise SystemExit(2)
    except (KeyboardInterrupt, EOFError):
        print("\nAbgebrochen.", file=sys.stderr)
        raise SystemExit(2)
