# Weitere Funktionen und native SMB-Zielverwaltung

## Nicht jede Modellgrenze ist eine reine Softwaresperre

Die gemeinsame Samsung-Anleitung und GUI beschreiben mehrere Druckermodelle.
Ein Eintrag beweist nicht, dass ein C1860FW die nötige Hardware und den gesamten
Backendpfad besitzt.

| Funktion | Beleg | Status dieses Projekts |
| --- | --- | --- |
| SMB-Scan zu externem NAS/Server | Capability- und Modellsperre im Display; Scanengine funktioniert | **Freigeschaltet, Display-zu-NAS-Scan getestet** |
| FTP-Scan | Im selben Modellblock ausgeblendet | Nicht gepatcht, kein Ende-zu-Ende-Test |
| „Shared Folder“ | Im selben Modellblock gesperrt; Hersteller beschreibt lokalen Gerätespeicher/Massenspeicher | Nicht gepatcht; **kein Synonym für ein externes SMB-Ziel** |
| PDF-Verschlüsselung beim Scannen | Herstellerübersicht ordnet sie bestimmten Varianten zu | Backend und Freischaltbarkeit ungeprüft |
| Stempel/Stamp bei Kopierfunktionen | Herstellerübersicht nennt andere Varianten | Freischaltbarkeit ungeprüft |
| Dokumentbox, gespeicherte/gesicherte Druckjobs, ImageOverwrite | Teilweise an Gerätevariante/lokalen Speicher gebunden | Kein Beleg einer bloßen GUI-Sperre |
| Automatisches Duplexdrucken/-scannen | Benötigt entsprechende Mechanik/Sensorik | Fehlende Hardware lässt sich nicht per Menüpatch ergänzen |
| Weitere Papierzuführung, optionale Anschlüsse/Speicher | Modell- und hardwareabhängig | Nicht Bestandteil dieses Patches |

**Keine vollständige Firmware-Sperreninventur:** Bei den weiteren Punkten
werden Herstellerangaben genannt, keine ungeprüften Freischaltungen behauptet.
E-Mail-Scan ist etwa nicht allein deshalb „gesperrt“, weil er ohne
SMTP-Konfiguration grau erscheint.

Quellen: [Samsung-Menüübersicht](https://samsungsetup.com/ts/manual/Samsung%20C1860%20Series/English/manual/menu_overview.htm),
[Samsung-Handbuch zu Shared Folder/Massenspeicher](https://www.manualslib.com/manual/416466/Samsung-Clx-6260nd.html?page=302)
und die GUI-Funktionen in [TECHNICAL.md](TECHNICAL.md).

## Wie die native Zielpflege gedacht ist

Der vorgesehene Weg ist das **Adressbuch in SyncThru Web Service**. Die
originalen Hinzufügen-/Bearbeiten-Dialoge enthalten SMB-Felder für Server, Port,
Gast beziehungsweise Benutzer/Passwort/Domain, Freigabe, Dateipräfix und
Ablagerichtlinien. Der Display-Scan wählt gespeicherte Ziele aus.

Unser Displaypatch schaltet die Webmaske **nicht automatisch mit frei**. Nach
dem erfolgreichen Patch meldete das `.04.06`-Testgerät weiterhin:

```text
/sws/app/addressbook/abook.json
GXI_S2SERVER_SUPPORT: 0
```

`aBook.js` übernimmt dies in `ABOOK.SMB_FTP_SUPPORT`. `aBookICmd.js` erzeugt die
SMB-/FTP-Felder und ihre Speicherparameter nur bei aktivem Flag. Das ist eine
**separate Präsentationssperre in SyncThru**.

Die Speicherhandler sind vorhanden: Der funktionierende Testfavorit wurde über
sie angelegt, blieb über die Updates erhalten und war am Display auswählbar.

## Was der enthaltene Helfer kann und was noch fehlt

`configure_smb.py` erstellt nach Bestätigung einen **neuen Gast-SMB-Favoriten**
über diese vorhandene Verwaltung und liest ihn zurück. Er ist **kein
vollständiger Editor**: keine Änderung/Löschung bestehender Kontakte und keine
Einrichtung eines NAS-Passworts. Die Firmwarepatches bleiben bei den zwei
SMB-Displayänderungen.

Für die vollständige **originale** Webpflege müsste die separate
SyncThru-Präsentationssperre gezielt aufgehoben und der originale
Hinzufügen-/Bearbeiten-/Löschen-/Passwortablauf getestet werden. Alternativ wäre
ein eigener vollständiger Editor über die vorhandenen Handler möglich.
Beides ist noch keine fertige Erweiterung dieses Releases. Ein zusätzlicher
Mainboard-/Web-Firmwarepatch wäre eine neue, nicht vom bisherigen Hardwaretest
abgedeckte Änderung.

Die originale Websoftware nutzt eigene Passwort-Übertragungsformate
(`MakeSWSData`). Ein geratenes Klartext-Passwortfeld ist kein geprüfter Ersatz.
Vorhandene Handler, sichtbare Support-Anzeigen und erfolgreiche Gastanmeldung
belegen nicht automatisch sämtliche NAS-Authentifizierungsarten.
