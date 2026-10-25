# Originale SMB-/FTP-Zielpflege über eine lokale Ansicht

**Entwicklungsstand, 25.10.2026:** Die originale Samsung-Maske wurde auf dem
`.04.06`-Testgerät geöffnet und zum Speichern eines bestehenden Gast-SMB-Ziels
benutzt. Unabhängiges Rücklesen bestätigte: nur dessen Anzeigename änderte sich;
alle SMB-/FTP-Parameter blieben gleich. Hinzufügen, Löschen und die Verbindung
mit NAS-Benutzerpasswort wurden über diese Ansicht noch nicht Ende zu Ende getestet.
Die ältere `.02.50`-Weboberfläche wurde damit nicht getestet.

## Was das ist

`syncthru_addressbook.py` startet auf deinem Computer einen nur unter
`127.0.0.1` erreichbaren Vermittler. Er lädt die **originale Weboberfläche direkt
von deinem Drucker**. In genau einer Antwort, `/sws/app/addressbook/abook.json`,
setzt er das Anzeigefeld `GXI_S2SERVER_SUPPORT` für diesen Browser auf `1`.
Samsung erzeugt daraufhin selbst seine SMB-/FTP-Felder. Seine Dialoge,
Passwortaufbereitung und Speicherhandler bleiben die originalen.

**Das ist noch keine dauerhafte Freischaltung der direkten Drucker-Webadresse.**
Ohne den Helfer meldet der Drucker weiter sein ursprüngliches Modellflag.
Die mit der Maske gespeicherten Ziele bleiben dagegen im echten Drucker-Adressbuch
gespeichert. Zum späteren Scannen am bereits gepatchten Display wird der Helfer
nicht gebraucht. Er installiert nichts im Drucker und flasht keine Firmware.

## Schritt für Schritt

1. Verwende eine aktuelle Arbeitskopie dieses Repos mit `syncthru_addressbook.py`.
   Das ursprüngliche Release `v1.0.0` enthält diesen Helfer noch nicht.
2. Öffne ein Terminal im entpackten Projektordner. Python 3.10 oder neuer genügt;
   zusätzliche Pakete sind nicht nötig.
3. Starte zuerst zum Ansehen, mit **deiner Drucker-IP**:

   ```sh
   python3 syncthru_addressbook.py 192.168.1.50
   ```

   Windows: `py -3` statt `python3`.
4. Öffne die angezeigte lokale Adresse, normalerweise
   `http://127.0.0.1:8765/sws/index.html`. Der Helfer und Browser müssen auf
   demselben Computer laufen.
5. Melde dich in der originalen Samsung-Maske mit deinem **Drucker-Adminzugang**
   an. Diese Anmeldung wird direkt an den von dir angegebenen Drucker vermittelt.
6. Öffne **Adressbuch → Person**. Die Liste zeigt jetzt SMB und FTP. Wähle
   einen Kontakt und **Bearb.**, oder öffne **Hinzufügen**. Im ersten Modus sind
   tatsächliches Speichern, Löschen und die Servertests gesperrt. **Abbrechen**
   schließt einen Dialog ohne Speichern.
7. Zum tatsächlichen Pflegen den Helfer im Terminal mit **Strg+C** beenden und
   ausdrücklich mit Schreibzugriff neu starten:

   ```sh
   python3 syncthru_addressbook.py 192.168.1.50 --allow-addressbook-writes
   ```

8. In derselben lokalen Browseradresse erneut das Adressbuch öffnen. SMB/FTP im
   Kontakt aktivieren, Server und Pfad eintragen und mit **Übernehmen** speichern.
   NAS-Benutzer/Passwort gehören in die SMB-Felder, nicht in die Drucker-Anmeldung.
   Bei Gastfreigaben **Anonym** verwenden. Beim Anzeigenamen z. B. `Scanner raw`
   benutzen: die getestete originale Maske verweigert `_` im **Anzeigenamen**.
   Eine Freigabe wie `Scanner_raw` im **Pfad** ist dagegen zulässig.
9. Ein gespeichertes Ziel erneut öffnen und die Angaben prüfen. Ein abgebrochener
   Speichervorgang wird vom Helfer nicht automatisch wiederholt. Bei unklarem
   Ergebnis erst nachsehen, bevor du ein zweites Ziel anlegst.
10. Danach Helfer mit **Strg+C** beenden. Ein gespeichertes SMB-Ziel kann weiter
    direkt am freigeschalteten Druckerdisplay gewählt werden.

Die originale Schaltfläche **Test** verbindet den Drucker mit dem Zielserver
und kann dort Testverzeichnisse anlegen/löschen. **Löschen** entfernt echte
Adressbucheinträge; die lokale Ansicht ist kein Sandbox-Adressbuch.

## Grenzen

- Der Helfer blendet keine FTP-Scan-Schaltfläche am Druckerdisplay ein. Die
  Display-Firmware dieses Projekts schaltet bislang nur SMB frei.
- Andere POST-/Schreibpfade, etwa Firmware, Druckaufträge und Systemeinstellungen,
  sind im Helfer gesperrt. Verwende für solche Aufgaben bei Bedarf die normale
  direkte Drucker-Webadresse.
- Der Helfer speichert keine Kennwörter und protokolliert keine Anfrageinhalte.
  `--trace` zeigt ausschließlich gesperrte Methode/Pfad-Paare zur Fehlersuche.
- Die Verbindung zum Drucker verwendet das angegebene HTTP oder HTTPS. HTTP wird
  dadurch nicht verschlüsselt. Bei HTTPS bleibt die normale Zertifikatsprüfung
  aktiv.
- Unerwartete Fähigkeitenantworten führen zu einem Fehler statt zu einer
  geratenen Änderung. `GXI_INSTALL_OPTION_HDD` wird ausdrücklich nicht verändert.
- Es werden keine Hersteller-Webdateien im Repository verteilt: sie werden
  jeweils von deinem eigenen Drucker geladen.
