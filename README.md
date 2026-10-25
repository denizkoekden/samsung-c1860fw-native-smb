# Samsung C1860FW native SMB scan

Enable **SMB Scan on the printer's own touchscreen**, using the SMB scan engine
already present in the Samsung Xpress C1860FW firmware.

**[Deutsche Schritt-für-Schritt-Anleitung →](docs/ANLEITUNG.md)**

**[Read before flashing: incompatible display generations, RAM-door label and recovery limits](docs/FIRMWARE-UND-RECOVERY.md)**

| Original firmware | Display firmware | Status |
| --- | --- | --- |
| **V4.00.04.06** | V5.08.20.03 | **Tested on one physical C1860FW**: installed through SyncThru, SMB menu selectable, scan started at the display and PDF received on a NAS |
| V4.00.02.50 | V5.08.51.05 | **UNTESTED on hardware**: patch locations checked in disassembly/decompilation; complete image rebuilt and verified offline only |

**These versions belong to different display hardware generations. They are not
interchangeable. Never install `.02.50` on a printer from the `.03.02`/`.04.xx`
branch, or use `.04.06` to upgrade an old `.02.xx` display.** Read the vendor's
release notes included in each original download and the [compatibility guide](docs/ANLEITUNG.md#1-firmware-und-hardwarezweig-prüfen).

<img src="docs/images/01-smb-menu.jpg" width="560" alt="C1860FW touchscreen with native SMB Scan selected">

## What the patch does

The UI contains two independent SMB gates: a capability check and an explicit
model-based availability check. This patch changes **two ARM instructions** in
`usr/local/GUI/GV3_linux` — **five differing bytes** — and rebuilds the display
update container and its checksums.

The mainboard image, component headers, display kernel, and included bootloader
bytes remain unchanged. **Unchanged bytes do not mean that the vendor installer
will skip writing those components.** The old `.02.50` package includes an
original bootloader component; `.04.06` has no UI bootloader component.

The existing SMB enable setting is still respected. FTP and shared-folder menu
gates are not patched. No shell, SSH, UART, scan relay, Docker container, or NAS
scanner daemon is required for this native scan path. A NAS/computer providing
the SMB share must of course be running.

## Download and run

1. Download [the latest patcher release](https://github.com/denizkoekden/samsung-c1860fw-native-smb/releases/latest) and extract it.
2. Install **Python 3.10 or later** from [python.org](https://www.python.org/downloads/) if needed. No `pip` packages are required.
3. Obtain the matching **original manufacturer firmware** from HP; links are in the [guide](docs/ANLEITUNG.md#2-die-passende-originalfirmware-herunterladen).
4. On Windows double-click `Start-Windows.cmd`; on macOS run `Start-macOS.command` as explained in the guide. Alternatively:

   ```sh
   python3 patcher.py --gui
   ```

5. Select the original `.hd` and create a new `_SMB.hd`. Follow the [manual SyncThru installation and SMB setup steps](docs/ANLEITUNG.md).

The **firmware patcher is entirely offline**. It never contacts or flashes a
printer. It accepts only the two exact original SHA-256 hashes, verifies the GUI
and expected instructions, validates MD5/checksum fields, re-parses the result,
and checks a fixed expected output SHA-256. It refuses unknown inputs, patched
inputs and existing output files.

CLI examples (`py -3` on Windows, usually `python3` on macOS/Linux):

```sh
python3 patcher.py --list
python3 patcher.py SL1860FW_V4.00.04.06.hd --inspect
python3 patcher.py SL1860FW_V4.00.04.06.hd

# OLD hardware branch only; produces *_SMB_UNTESTED.hd:
python3 patcher.py SL1860FW_V4.00.02.50.hd --allow-untested
```

Each output has a small `.hd.json` report with input/output hashes and checks.
The exact supported hashes are also in [firmware-profiles.json](docs/firmware-profiles.json).

## Setting the destination

Some SyncThru builds also hide the SMB address-book fields. The separate,
optional `configure_smb.py` helper uses the printer's normal SyncThru handlers to
add **one new guest SMB favorite**, after an explicit interactive confirmation.
It checks for an unused speed-dial number and reads back the new entry. It does
not upload firmware, start scans, edit existing contacts, or change NAS settings.

```sh
python3 configure_smb.py
```

This helper currently supports **guest shares only**; NAS username/password setup
is not implemented. Do not confuse the printer's SyncThru admin password with a
NAS login. See the [full setup instructions](docs/ANLEITUNG.md#7-smb-ziel-einrichten).

The direct printer URL still gates the original SyncThru SMB editor separately.
The current development tree additionally includes **`syncthru_addressbook.py`**,
a loopback-only view that exposes the **original Samsung SMB/FTP editor** by
overriding one presentation flag. Editing an existing guest SMB destination was
verified on the `.04.06` printer. This is a temporary local browser view, **not a
permanent mainboard-firmware unlock**. It is not included in release `v1.0.0`.
See the [step-by-step address-book guide](docs/ADRESSBUCH-ANSICHT.md) and
[other feature limits](docs/FUNKTIONEN-UND-ADRESSBUCH.md).

After setup: **Scan → SMB Scan → Next → select destination → Start**.

## Evidence and limits

The `.04.06` result is byte-identical to the package installed on the tested
printer. The owner photographed the native menu, destination and active scan;
a new **473,120-byte `Scan.pdf`** was independently observed on the SMB share.
See [test status and photos](docs/TESTING.md).

There is **no verified full-device backup/recovery procedure** in this project.
Firmware installation can make a printer or display unusable. A configuration
export is not a flash backup, and reinstalling stock firmware is not a proven
recovery method if the display no longer starts. Use only a device you own or
are authorized to administer. A later stock firmware update may restore the UI
gates. This is not a firmware security update.

## Development

```sh
python3 -m unittest discover -s tests -v
```

The synthetic tests do not contain vendor firmware. They cover preservation of
non-GUI data and boot components, checksum/MD5 failures, unknown/already patched
inputs, experimental opt-in, output collisions, bounded decompression and the
address-book response parser. CI runs them on Linux, Windows and macOS. CI is
not a hardware test or a graphical-launcher test.

[Technical details](docs/TECHNICAL.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

## Related work and license

[oushen/asustor-samsung-c1860-scan](https://github.com/oushen/asustor-samsung-c1860-scan)
provides a NAS-side approach using Samsung's Scan-to-PC protocol and SANE. This
project documents an alternative that enables the printer's built-in SMB path
through a firmware modification. The approaches have different requirements
and risks.

Original project code and documentation: [MIT](LICENSE). No Samsung/HP firmware
is distributed here. Not affiliated with or endorsed by Samsung or HP.
