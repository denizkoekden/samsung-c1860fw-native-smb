# C1860FW: direkt vom Display auf eine SMB-Freigabe scannen

Diese Anleitung führt vom unveränderten Drucker zum Menüpunkt **SMB Scan**.
Der eigentliche Scan läuft danach direkt vom Drucker zum NAS. Auf dem NAS wird
keine zusätzliche Scansoftware benötigt.

**Der vollständige Ablauf wurde an genau einem Samsung Xpress C1860FW mit
System V4.00.04.06 und Display V5.08.20.03 erfolgreich getestet.**
Die zweite Variante V4.00.02.50 ist **am Gerät UNGETESTET**.

Der Patcher erstellt nur eine Datei auf deinem Computer. Du installierst sie
anschließend selbst über die vorhandene Drucker-Weboberfläche.

## Vorher wissen

- Du brauchst einen Samsung **Xpress C1860FW**, einen Computer mit Python 3.10+
  und einen erreichbaren SMB-Server, zum Beispiel ein NAS.
- Firmware kann den Drucker oder sein Display unbrauchbar machen. Ein
  vollständiger Backup-/Recovery-Weg ist hier **nicht nachgewiesen**. Eine
  Reparatur könnte das Öffnen des Geräts erfordern.
- Exportierte Druckereinstellungen sichern Kontakte und Einstellungen, nicht
  den gesamten Flashspeicher.
- Der Patch hebt die beiden SMB-Menüsperren auf. Er aktualisiert keine
  Sicherheitskomponenten und erweitert nicht den RAM.
- **Die Firmwarezweige nicht mischen.** Die alte `.02.xx`-Displayhardware und
  die neuere `.03.02`/`.04.xx`-Displayhardware sind laut Hersteller nicht
  austauschbar. Eine größere Versionsnummer ist hier kein universelles Upgrade.

## 1. Firmware und Hardwarezweig prüfen

**Vor dem Download [Firmwaregeneration und Recovery](FIRMWARE-UND-RECOVERY.md)
lesen.** Dort werden System-/UI-Paare, der Aufkleber hinter dem RAM-Türchen,
vertauschte Firmwarelinien und Grenzen bekannter Reparaturberichte erklärt.

1. Drucker normal einschalten und den Startbildschirm abwarten.
2. Seine IP-Adresse herausfinden, zum Beispiel in den Netzwerkeinstellungen des
   Druckers oder in der Geräteliste deines Routers.
3. Am Computer einen Browser öffnen. In die **Adresszeile** oben eingeben:
   `http://DEINE-DRUCKER-IP`. Beispiel: `http://192.168.1.50`.
4. Die Samsung-Seite heißt **SyncThru Web Service**. Dort mit deinem bestehenden
   Administratorzugang anmelden. Ein verlorenes Passwort nicht durch einen
   unüberlegten Werksreset ersetzen; nutze die Herstelleranleitung.
5. Oben **Wartung → Firmware-Upgrade** öffnen. Die Werte für
   **Firmware-Version des Systems** und **UI-Firmware-Version** notieren.

| Dein Stand | Einordnung | Vorgehen |
| --- | --- | --- |
| System `.04.06`, UI `.20.03` | Neue Displaygeneration | Getestete Patcher-Variante `.04.06` |
| System `.04.03`, UI `.20.02` | Neue Displaygeneration, so war das Testgerät ab Werk | Der getestete Ablauf war zuerst das unveränderte offizielle `.04.06`-Update, danach der `.04.06`-SMB-Patch |
| System `.02.50`, UI `.51.05` | Alte Displaygeneration | Nur der als UNGETESTET gekennzeichnete `.02.50`-Kandidat; kein Hardware-Erfolgsnachweis |
| Andere oder widersprüchliche Werte | Hier nicht am Gerät geprüft | Zuerst Hersteller-Release-Notes und technische Zuordnung prüfen; nicht raten |

Die Herstellerhinweise trennen die Zweige bei `.03.02` und dokumentieren den
Wechsel der Bedienfeldhardware. Eine Zuordnung anhand der Systemversion darf
nicht benutzt werden, um widersprüchliche UI-Werte zu übergehen.

**Der Patcher kann deine Druckerhardware nicht erkennen**, weil er offline
arbeitet. Er erkennt ausschließlich die ausgewählte Originaldatei.

## 2. Die passende Originalfirmware herunterladen

In diesem Repo gibt es absichtlich keine Firmware zum Herunterladen.
Besorge die passende Originaldatei direkt vom Hersteller-Archiv bei HP:

| Zweig | Original-ZIP | Enthaltene Datei |
| --- | --- | --- |
| Neu, getestet | [SL-C1860_V4.00.04.06.zip](https://ftp.hp.com/pub/softlib/software13/printers/SS/SL-C1860FW/SL-C1860_V4.00.04.06.zip) | `SL1860FW_V4.00.04.06.hd` |
| Alt, UNGETESTET | [SL1860FW_V4.00.02.50.zip](https://ftp.hp.com/pub/softlib/software13/printers/SS/SL-C1860FW/SL1860FW_V4.00.02.50.zip) | `SL1860FW_V4.00.02.50.hd` |

1. Die ZIP-Datei herunterladen und **entpacken**. Unter Windows: Rechtsklick
   auf die ZIP → **Alle extrahieren**. Auf dem Mac: ZIP doppelklicken.
2. Die enthaltenen englischen Release-Notes lesen, besonders die Hinweise zur
   Hardwaregeneration und zum Update.
3. Die `.hd` ist das Firmwarepaket. **Nicht** die ZIP, PDF oder `usblist2.exe`
   beim Patcher auswählen. Das Windows-Flashprogramm wird hier nicht benötigt.

Der Patcher prüft den gesamten Dateiinhalt per SHA-256. Er akzeptiert nicht
einfach alles, was zufällig den richtigen Dateinamen hat.

Falls HP den Download entfernt oder eine andere Fassung bereitstellt, wird
eine abweichende Datei abgelehnt. Die Hashprüfung nicht herausnehmen.

## 3. Einstellungen sichern

1. In SyncThru als Administrator anmelden.
2. **Wartung → Klonen** öffnen.
3. Die Funktion zum Exportieren/Sichern der Einstellungen wählen. Wenn
   Kategorien angeboten werden, alle benötigten Kategorien einschließlich
   Adressbuch auswählen.
4. Die Sicherungsdatei auf deinem Computer speichern und sicher aufbewahren.
   Sie kann vertrauliche Einstellungen enthalten und gehört nicht in ein
   öffentliches Issue.

Die genaue Beschriftung kann je nach Sprache/Stand abweichen. Eine
Konfigurationssicherung ist **kein vollständiges Firmwarebackup**.

## 4. Den Patcher starten

### Einmal vorbereiten

1. [Die aktuelle Patcher-Release](https://github.com/denizkoekden/samsung-c1860fw-native-smb/releases/latest)
   öffnen und die Datei `c1860fw-native-smb-patcher-v1.0.0.zip` herunterladen.
2. ZIP vollständig entpacken. Das Programm nicht direkt aus der ZIP starten.
3. Falls Python noch fehlt: [python.org/downloads](https://www.python.org/downloads/).
   **Python 3.10 oder neuer** installieren. Unter Windows die Option zum
   Hinzufügen von Python zum PATH auswählen, wenn der Installer sie anbietet.
   Die regulären Windows-/macOS-Installer von python.org enthalten üblicherweise
   auch die benötigte Tk-Oberfläche.

### Windows

1. Den entpackten Patcher-Ordner öffnen.
2. `Start-Windows.cmd` doppelklicken. Ein Auswahlfenster sollte erscheinen.
3. Falls Windows den Dateityp ausblendet: In Explorer **Dateinamenerweiterungen**
   einschalten, um nicht versehentlich eine gleichnamige andere Datei zu öffnen.
4. Öffnet sich kein Fenster, eine Eingabeaufforderung im Patcher-Ordner öffnen
   und eingeben:

   ```bat
   py -3 patcher.py --gui
   ```

### macOS

1. Im entpackten Ordner `Start-macOS.command` starten.
2. Falls die Datei keine Ausführungsberechtigung hat, ist der direkte Weg über
   Terminal einfacher: Terminal öffnen, `cd ` **mit Leerzeichen** eingeben,
   den entpackten Patcher-Ordner ins Terminal ziehen und Enter drücken.
3. Danach eingeben:

   ```sh
   python3 patcher.py --gui
   ```

### Linux oder ohne grafisches Auswahlfenster

Im Patcher-Ordner:

```sh
python3 patcher.py "/pfad/zur/SL1860FW_V4.00.04.06.hd"
```

Auf manchen Linux-Systemen muss Tk separat als Distributionspaket installiert
werden. Die Kommandozeilenvariante braucht Tk nicht.

## 5. Die SMB-Datei erstellen

1. Im Fenster **Original .hd auswählen…** anklicken.
2. Die **unveränderte Original-.hd** aus Schritt 2 auswählen.
3. **SMB-Datei erstellen – kein Flashen** anklicken.
4. Einen neuen Dateinamen und Speicherort wählen. Für den getesteten Zweig
   bietet das Programm `SL1860FW_V4.00.04.06_SMB.hd` an.
5. Warten. Prüfen und Neu-Komprimieren kann je nach Computer einige Minuten
   dauern. Das Fenster bleibt offen und zeigt Meldungen an.
6. Am Ende müssen die neue `.hd` und die zugehörige `.hd.json` existieren.
   Die JSON-Datei ist nur ein Prüfbericht; sie wird nicht auf den Drucker geladen.

Das Original bleibt erhalten. Vorhandene Ausgabedateien werden auch nach einer
Bestätigung im Speichern-Dialog nicht überschrieben; dann einen neuen Namen wählen.

Für `.02.50` muss zusätzlich das Feld für den **UNGETESTETEN alten Hardwarezweig**
aktiviert werden. Die Ausgabe heißt dann `_SMB_UNTESTED.hd`. Per Kommandozeile:

```sh
python3 patcher.py "/pfad/zur/SL1860FW_V4.00.02.50.hd" --allow-untested
```

Das erfolgreiche Erstellen dieser Datei bestätigt **keine Hardwarekompatibilität
oder sichere Installation**. Für `.02.50` gibt es hier noch keinen
Installationserfolg. Der folgende am Gerät geprüfte Installationsablauf bezieht
sich auf `.04.06`.

## 6. Über SyncThru installieren – getesteter .04.06-Ablauf

### Drucker vorbereiten

1. Drucker und Computer müssen sich zuverlässig im selben Netz erreichen.
2. Alle Druck-/Scan-/Faxaufträge fertig werden lassen. In SyncThru oben
   **Auftragsstatus** prüfen: **0 aktive Aufträge**.
3. Am Drucker unter **Setup → Admin Setup → Firmware Upgrade** die
   Updatefreigabe einschalten, soweit diese Einstellung bei dir angeboten wird.
   Die deutschen Bezeichnungen können abweichen.
4. Beim erfolgreichen Test war das USB-Kabel zum Server getrennt. Verwendet
   wurde der Netzwerkweg über SyncThru.
5. Drucker am Display aufwecken und auf den normalen Startbildschirm wechseln.
   Für zuverlässige Stromversorgung sorgen. Während der Installation nichts
   ausschalten, abziehen oder am RAM umbauen.

### Falls dein Gerät noch .04.03 hat

Beim Testgerät wurde zunächst die **unveränderte Original-.04.06-HD** mit dem
folgenden Assistenten installiert. Danach zeigte die Versionsseite System
`.04.06` und UI `.20.03`. Erst anschließend wurde das SMB-Paket installiert.
Dieser Zweischritt ist der hier dokumentierte erprobte Weg; ein direkter
Sprung von `.04.03` zum modifizierten Paket wurde nicht getestet.

### Die richtige Datei auswählen und installieren

1. Im Browser SyncThru öffnen und als Administrator anmelden.
2. **Wartung → Firmware-Upgrade → Aktualisierungsassistent** öffnen.
3. **Durchsuchen/Datei auswählen** anklicken und die neue
   `SL1860FW_V4.00.04.06_SMB.hd` auswählen.
4. **Weiter** anklicken. SyncThru prüft die Firmware. Diese Prüfung kann eine
   Weile dauern; ein laufender Upload ist noch keine fertige Installation.
5. Wenn die Versionsbestätigung erscheint, müssen aktuell und neu beim
   bereits aktualisierten Gerät beide `.04.06` heißen. **Das ist bei diesem
   Menü-Patch normal.** Die Versionszeichenfolge wird nicht erhöht.
6. Noch einmal **Weiter** anklicken, um die Installation tatsächlich zu starten.
7. Bei **„Die Firmware wird programmiert“** warten. Keine zweite Installation
   und keinen manuellen Neustart auslösen. Beim Test dauerte der gesamte
   Vorgang mehrere Minuten.
8. SyncThru sollte **„Die Firmware-Aktualisierung ist abgeschlossen“** melden
   und zur Startseite zurückkehren. Der Drucker startet automatisch neu.
9. Wieder anmelden und die Versionswerte prüfen: System `.04.06`, UI `.20.03`.
   Diese Nummern allein beweisen den SMB-Patch noch nicht; entscheidend ist
   das neue Menü am Display.

Falls die Abschlussseite nur kurz zu sehen ist: Nicht deshalb erneut flashen.
Startbildschirm, Geräteerreichbarkeit und SMB-Menü prüfen.

**Keine Firmware als normalen Druckauftrag senden**, nicht auf Port 9100
kopieren und nicht aus einer Druckwarteschlange „drucken“. Diese Anleitung
verwendet ausschließlich den SyncThru-Firmwareassistenten.

## 7. SMB-Ziel einrichten

Ein sichtbarer SMB-Menüpunkt braucht noch einen gespeicherten Zielordner.
Beim Test wurde eine vorhandene **Gastfreigabe** verwendet. Der Ziel-Assistent
dieses Repos unterstützt derzeit nur diesen Fall.

### Freigabe am NAS vorbereiten

1. Einen eigenen SMB-Ordner für Scans anlegen, zum Beispiel `Scans`.
2. Für den getesteten Gastweg muss dieser Ordner für Gäste beschreibbar sein.
   Das kann im lokalen Netz weitere Personen zum Lesen/Schreiben berechtigen;
   daher nur die dafür vorgesehene Scan-Freigabe verwenden.
3. IP-Adresse/Hostname des NAS und **Freigabename** notieren.
   Beispiel: NAS `192.168.1.20`, Freigabe `Scans`.
4. Auf dem Computer prüfen, ob du auf diese Freigabe zugreifen und dort eine
   eigene Testdatei anlegen kannst. Die NAS-Oberfläche ist herstellerspezifisch.

Ein lokaler NAS-Pfad wie `/volume1/Scans` oder `/mnt/user/Scans` ist **nicht** der
Freigabename. Im Assistenten nur `Scans` eingeben. Auch eine Bonjour-Service-URL
wie `smb://Name._smb._tcp.local/Scans` nicht komplett in das IP-Feld kopieren.

Für ein NAS, das zwingend Benutzername/Passwort verlangt, ist dieser Helfer
noch nicht geeignet. Das muss über eine passende Hersteller-Eingabemaske oder
eine separat geprüfte Erweiterung eingerichtet werden. Nicht die globale
NAS-Authentifizierung oder SMB-Protokollversion pauschal herabsetzen.

### Favorit im Drucker speichern

Die SMB-Felder können in SyncThru auch nach dem Display-Patch verborgen bleiben.
`configure_smb.py` spricht deshalb die vorhandenen normalen SyncThru-Handler an.
Eine Shell, SSH-Verbindung oder spezielle interne API ist dafür nicht nötig.

Warum der originale Webeditor verborgen bleibt und was für vollständige native
Zielpflege fehlt: [Funktionen und Adressbuch](FUNKTIONEN-UND-ADRESSBUCH.md).

1. Nach dem Firmwareupdate die Druckerkonfiguration erneut sichern, bevor du
   das Adressbuch änderst.
2. Unter Windows `Setup-SMB-Windows.cmd` starten, unter macOS
   `Setup-SMB-macOS.command`. Alternativ im Patcher-Ordner:

   ```sh
   python3 configure_smb.py
   ```

   Unter Windows lautet der Befehl `py -3 configure_smb.py`.
3. **Drucker-IP** eingeben. Diese ist nicht die NAS-IP.
4. SyncThru-Benutzername und bestehendes **Drucker-Adminpasswort** eingeben.
   Während der Passworteingabe sieht man üblicherweise keine Zeichen; das ist normal.
5. Namen für den Displayeintrag wählen, zum Beispiel `Scans`.
6. **NAS-IP/Hostname** und **SMB-Freigabename** eingeben.
7. Die Zusammenfassung prüfen. Der Helfer wählt eine freie Kurzwahlnummer
   zwischen 1 und 50 und markiert den neuen Eintrag als Favorit.
8. Nur wenn alles stimmt, zur Bestätigung genau **JA** eingeben.
9. Die Meldung **„Gespeichert und vom Drucker zurückgelesen“** abwarten.

Der Helfer speichert keine Zugangsdaten auf dem Computer, versucht keinen Scan
und verändert keine NAS-Einstellungen. Bei Nutzung der alten HTTP-Weboberfläche
werden die Drucker-Adminzugangsdaten unverschlüsselt zum angegebenen Drucker
übertragen. Nur im eigenen vertrauenswürdigen Netz verwenden.

Ist das Speicherergebnis unklar, **nicht blind erneut hinzufügen**. Zuerst im
Adressbuch/am Display prüfen. Vorhandene Kontakte werden vom Helfer nicht editiert.
Der Helfer kann bestehende Ziele nicht ändern oder löschen. Soweit die
jeweiligen Felder in deiner Geräteverwaltung sichtbar sind, deren normale
Adressbuchfunktionen verwenden. Eine vollständig freigeschaltete originale
SMB-Webverwaltung gehört noch nicht zu diesem Release.

## 8. Den ersten nativen Scan machen

1. Vorlage auf das Glas legen.
2. Am Drucker **Scan** öffnen.
3. In der horizontalen Auswahl gegebenenfalls weiterblättern, bis **SMB Scan**
   erscheint.
4. **SMB Scan → Next → deinen Favoriten auswählen → Start**.
5. Warten, bis der Vorgang beendet ist.
6. Auf dem NAS nach einer neuen Datei suchen. Der getestete Lauf erzeugte
   `Scan.pdf`. Der Dateiname hängt auch von den Scan-/Adressbucheinstellungen ab.

![SMB-Menü](images/01-smb-menu.jpg)

![Zielauswahl](images/02-smb-destination.jpg)

![Am Display gestarteter Scan](images/03-native-scan.jpg)

Die Fotos stammen vom erfolgreich gepatchten `.04.06`-Testgerät. Sichtbare
Tonerwarnungen verhinderten den dortigen SMB-Scan nicht; daraus folgt keine
Aussage über alle möglichen Gerätefehler.

## Wenn etwas nicht klappt

| Symptom | Nächster Schritt |
| --- | --- |
| Patcher meldet unbekannten SHA-256 | Original `.hd` aus dem richtigen Hersteller-ZIP auswählen. Kein ZIP, Dump oder bereits gepatchtes Paket verwenden. |
| Ausgabe existiert bereits | Neuen Dateinamen wählen oder die alte selbst verwaltete Ausgabe vorher verschieben. Das Original behalten. |
| Python/Tk fehlt | Python-Version prüfen. Regulären python.org-Installer mit Tk verwenden oder den CLI-Befehl nutzen. |
| „Gerät ist nicht bereit“ während der Prüfung | Aufträge prüfen, Drucker am Display aufwecken, Startbildschirm abwarten. Wenn die Prüfung beendet/abgebrochen ist und kein Flashvorgang läuft, kann ein normaler Neustart mit getrenntem USB helfen. Das ist eine Beobachtung vom Testgerät, keine garantierte Ursache oder Lösung. |
| „Firmware wird programmiert“ | Warten. Nicht ausschalten und nicht erneut hochladen. Bei ungewöhnlich langem Stillstand Displaymeldung dokumentieren und erst den Zustand klären. |
| Versionsnummer bleibt gleich | Beim SMB-Patch normal. SMB-Menü und tatsächlichen Scan prüfen. |
| SMB-Menü fehlt oder ist ausgegraut | System-/UI-Version, verwendeten Paket-Hash und Scan-Funktionseinstellungen prüfen. Keine FTP-/Shared-Folder-Freischaltung erwarten. Nicht auf Verdacht Firmwarezweige wechseln. |
| Zielliste leer | SMB-Favorit muss gespeichert sein; Schritt 7. Name und Kurzwahlnummer kontrollieren. |
| Ziel vorhanden, Scan schlägt fehl | NAS-IP, Freigabename, Gast-Schreibrecht und NAS-Logs prüfen. Den Drucker aufwecken. Nicht pauschal SMB1 oder globale Gastrechte aktivieren. |

Für Fehlerberichte: [neues Issue](https://github.com/denizkoekden/samsung-c1860fw-native-smb/issues/new).
Nenne Modell, System-/UI-Version, Patcher-Version und die öffentliche Fehlermeldung.
Keine Passwörter, Scans, vollständigen Konfigurationssicherungen oder Firmwaredateien anhängen.

## Rückkehr zum Original

Solange die reguläre Updatefunktion noch arbeitet, wäre das passende unveränderte
Herstellerpaket der normale Kandidat zur Rückkehr zum Original. **Diese Rückkehr
wurde nach dem SMB-Patch nicht am Gerät getestet.** Sie ist kein nachgewiesener
Notfall-Recovery-Weg für ein nicht mehr startendes Display. Nach einem späteren
Herstellerupdate kann das SMB-Menü wieder verschwinden.
