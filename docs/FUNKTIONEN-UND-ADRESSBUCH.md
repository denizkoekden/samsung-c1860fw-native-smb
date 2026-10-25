# Weitere Funktionen und native SMB-Zielverwaltung

## Nicht jede Modellgrenze ist eine reine Softwaresperre

Die gemeinsame Samsung-Anleitung und GUI beschreiben mehrere Druckermodelle.
Ein Eintrag beweist nicht, dass ein C1860FW die nötige Hardware und den gesamten
Backendpfad besitzt.

| Funktion | Beleg | Status dieses Projekts |
| --- | --- | --- |
| SMB-Scan zu externem NAS/Server | Capability- und Modellsperre im Display; Scanengine funktioniert | **Freigeschaltet, Display-zu-NAS-Scan getestet** |
| FTP-Scan | Im selben Modellblock ausgeblendet | Experiment für beide Zweige offline geprüft; `.04.06`-Kandidat mit ausdrücklicher Zustimmung installiert, Neustart bestätigt. Originaler FTP-Verbindungs-/Anmelde-/Berechtigungstest erfolgreich und Ziel gespeichert. Displaymenü und echter Scan noch nicht bestätigt; nicht Bestandteil des veröffentlichten SMB-Patchprofils |
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
Release `v1.0.0` enthält diese Erweiterung noch nicht. Im aktuellen
Entwicklungsstand gibt es die [lokale originale Adressbuchansicht](ADRESSBUCH-ANSICHT.md):
die SMB-/FTP-Dialoge wurden am `.04.06`-Gerät geöffnet und ein vorhandener
Gast-SMB-Kontakt erfolgreich gespeichert. Rücklesen bestätigte nur den beabsichtigten
Anzeigenamenwechsel; alle Serverparameter blieben identisch. SMB-Hinzufügen,
Löschen und SMB-/NAS-Passwortanmeldung sind über diese Ansicht noch ungetestet.

Anschließend wurde auch ein **neues FTP-Ziel mit Benutzer/Passwort** über die
Originalmaske angelegt und unabhängig zurückgelesen. Der originale Server-Test
des Druckers meldete Verbindung, Anmeldung und Berechtigungen erfolgreich.
Das belegt diese FTP-Zielpflege, noch keinen tatsächlich übertragenen Scan und
keine SMB-Anmeldung mit NAS-Passwort. Löschen wurde nicht getestet.
Ein Wiederholungstest nach erneutem Öffnen des Kontakts bestand ebenfalls mit
den gespeicherten FTP-Zugangsdaten, ohne das Passwort erneut einzugeben.

Nach dem zusätzlichen experimentellen FTP-Firmwareupdate war das vorhandene
Adressbuch beim Rücklesen leer. Der zuvor lokal gesicherte Gast-SMB-Favorit wurde
daraufhin wiederhergestellt und mit identischen SMB-Parametern verifiziert.
Die Ursache ist noch ungeklärt; frühere SMB-Updates hatten das Ziel erhalten.
Vor weiteren Updates deshalb auch die Ziele sichern. Ein Konfigurationsexport
ist weiterhin kein vollständiges Firmwarebackup.

Diese lokale Ansicht setzt ausschließlich das Anzeigefeld in der Browserantwort.
Für eine **dauerhafte** Änderung der direkten SyncThru-Druckeradresse müsste das
Netzwerkmodul auf der Hauptplatine bearbeitet werden: dessen Variablentabelle
enthält für `GXI_S2SERVER_SUPPORT` einen Getter, aber keinen Setter. Für dieses
Hauptplatinenmodul ist noch kein geprüfter Neuverpackungs-/Installationsweg
implementiert. Das ist eine andere Änderung als der getestete Displaypatch.

Die originale Websoftware nutzt eigene Passwort-Übertragungsformate
(`MakeSWSData`). Ein geratenes Klartext-Passwortfeld ist kein geprüfter Ersatz.
Vorhandene Handler, sichtbare Support-Anzeigen und erfolgreiche Gastanmeldung
belegen nicht automatisch sämtliche NAS-Authentifizierungsarten.

## Was die weiteren Funktionen tatsächlich machen

### PDF-Verschlüsselung

Der Scanner erzeugt ein verschlüsseltes PDF. Zum Öffnen benötigt der Empfänger
ein Passwort. Zusätzlich können die Samsung-PDF-Optionen ein Eigentümerpasswort
und Berechtigungen für Drucken, Ändern und Textextraktion vorsehen. Die allgemeine
Hersteller-Sicherheitsbeschreibung nennt RC4 und AES; das beweist für sich allein
keine Implementierung auf jeder Gerätevariante.

Quelle: [Samsung-Handbuch, Scan](https://samsungsetup.com/ts/manual/Samsung%20C1860%20Series/English/manual/CIHDJJGF.htm),
[Samsung-Sicherheitsbeschreibung, Abschnitt 8.1.3](https://image-us.samsung.com/SamsungUS/b2b/resource/2013/06/19/MultifunctionPrinterSecurity.pdf).

**Befund an unserem Gerät:** Die bereits lokal gesicherte interne
Scanjobfactory meldet `secureCap: "sfTrue"` sowie AES-128, RC4-128 und RC4-40
als mögliche Werte. Der passende Displaycode enthält Passwortfelder und
überträgt `secure`, `secureEncryption`, `secureOwnerPassword` und
`secureUserPassword` an die Scanner-API. Das ist ein konkreter Kandidat für einen
weiteren Test. Ein erfolgreich verschlüsseltes PDF und der Zugang zu den nötigen
Displayoptionen wurden noch nicht nachgewiesen. Es wurde kein PDF-Patch installiert.

### Dokumentbox

Die Dokumentbox ist die Bedienoberfläche für im Drucker aufbewahrte Dokumente:
**Stored Print** ruft gespeicherte Druckdaten ab, **Secured Print** verlangt
dafür ein Passwort. Sie ist nicht schon dadurch eine neue externe NAS-Verbindung.
Für Aufbewahrung und Wiederabruf muss ein tatsächlicher Speicherpfad vorhanden
sein; das bloße Einblenden einer Taste erzeugt ihn nicht.

Quelle: [Samsung-Handbuch, Document box](https://printersetup.ext.hp.com/ts/manual/Samsung%20C145x%20Series/English/manual/machine_status_2.htm).

### Gespeicherte Druckaufträge

Dies sind die Aufträge innerhalb der Dokumentbox beziehungsweise Jobverwaltung.
Der Druckertreiber kann beispielsweise **Proof** (erst eine Kontrollkopie),
**Confidential** (Freigabe am Gerät mit Passwort), **Store** (nur speichern) oder
**Store and Print** (drucken und für später behalten) anbieten. Welche davon
funktionieren, hängt von Gerät, Treiber und Speicher ab. Bei einigen Samsung-Modellen
ermöglicht eine RAM-Disk nur Normal/Proof/Confidential; daraus folgt keine
entsprechende Zusage für den C1860FW. Eine RAM-Disk verliert ihren Inhalt beim
Ausschalten; mehr RAM ist kein Ersatz für dauerhaften Massenspeicher.

Quellen: [Samsung-Treiberhandbuch, Print Mode](https://h10032.www1.hp.com/ctg/Manual/c05791007.pdf),
[Samsung M403x, ausdrücklich modellabhängige RAM-Disk-Grenzen](https://printersetup.ext.hp.com/ts/manual/Samsung%20M403x%20Series/English/manual/CACHBFHB.htm).

### Stempel

Gemeint sind auf **Kopien** aufgedruckte Angaben wie Datum/Uhrzeit, Gerätename,
IP-Adresse, Benutzerkennung oder Seitennummer mit Position/Deckkraft. Das ist
eine andere Funktion als die Verschlüsselung eines Scan-PDFs.

Quelle: [Samsung-Handbuch, System setup](https://printersetup.ext.hp.com/ts/manual/Samsung%20C145x%20Series/English/manual/machine_status_2.htm).
Im Displaycode ist die Auswahl vorhandener Stempel-Fähigkeiten implementiert;
ein erfolgreicher Stempelauftrag am C1860FW wurde nicht getestet.

### Scan in „Shared Folder“

Samsung beschreibt hier einen vom **Drucker bereitgestellten Ordner** für Scans
und Dokumente. Der Computer greift auf diesen Gerätespeicher zu. Das ist ein
anderer Ablageweg als **SMB Scan** zu einer Freigabe auf einem externen NAS.
Das Herstellerhandbuch bindet Shared Folder an Modelle mit Massenspeicher.

Quelle: [Samsung-Handbuch, Using shared folder features](https://www.manualslib.com/manual/416466/Samsung-Clx-6260nd.html?page=302).

**Speicherbefund:** Das getestete Gerät meldet im echten SyncThru weiterhin
`GXI_INSTALL_OPTION_HDD: 2`; laut originalem Webcode bedeutet `2` **nicht
installiert**. Dieser Wert wird vom lokalen Helfer nicht verändert. Ob eine
tatsächlich vorhandene alternative RAM-/Speicherimplementierung für Shared
Folder, Dokumentbox oder bestimmte gespeicherte Jobs nutzbar ist, ist noch offen.
Ein eingeblendetes Menü oder eine allgemeine API-Fähigkeitenliste wäre dafür
kein ausreichender Ende-zu-Ende-Nachweis. Diese Funktionen sind noch nicht
freigeschaltet.
