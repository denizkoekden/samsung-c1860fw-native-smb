# Technical notes

## Scope

This project changes the GUI application in two exact Samsung C1860FW update
images. It does not implement SMB, modify the mainboard's SMB engine, add a
shell, change model identity, or disable an authentication/signature check.
It does not establish why Samsung chose these UI gates.

The `.04.06` package was installed on one owned printer using the stock
SyncThru wizard, followed by a native display-initiated scan to an SMB share.
The `.02.50` package was only inspected and rebuilt offline.

## Instruction patches

The addresses below are virtual addresses in the original ELF32 ARM GUI. File
offsets refer to that ELF member, not to the compressed firmware container.
Both originals and both modified GUI functions were decompiled to check the
control flow. The old profile uses separately verified addresses and hashes.

| Firmware / UI | Function | ELF VA | File offset | Original bytes | Patched bytes |
| --- | --- | --- | --- | --- | --- |
| .04.06 / .20.03 | `Window_ScanMgr_FeatureEntryCheck` | `0x64fdc` | `0x5cfdc` | `b0 30 9f e5` | `05 00 00 ea` |
| .04.06 / .20.03 | `Window_ScanMgr_Set_EnableDisable_Status` | `0x6551c` | `0x5d51c` | `00 10 a0 e3` | `01 10 a0 e3` |
| .02.50 / .51.05, UNTESTED | `Window_ScanMgr_FeatureEntryCheck` | `0x64f78` | `0x5cf78` | `b0 30 9f e5` | `05 00 00 ea` |
| .02.50 / .51.05, UNTESTED | `Window_ScanMgr_Set_EnableDisable_Status` | `0x654b8` | `0x5d4b8` | `00 10 a0 e3` | `01 10 a0 e3` |

The first replacement is an ARM branch that skips two extra scanner-capability
tests **after** the existing SMB-enabled setting has been checked. Its targets
are `0x64ff8` for `.04.06` and `0x64f94` for `.02.50`. The resulting logic keeps
the SMB enable setting instead of clearing it because the capability object
omits SMB support.

The second replacement changes `mov r1,#0` to `mov r1,#1` in the SMB feature-4
availability assignment for the model-restricted path. FTP (5) and shared
folder (9) assignments are left alone. It is not a general unlock of all scan
features, and compatibility with the other model strings in that function has
not been demonstrated.

There are two changed instructions but only five differing bytes in the GUI
file. All remaining bytes of the uncompressed root TAR stay identical,
including TAR headers, permissions, timestamps and padding.

## Container rebuilding

Both inputs have a mainboard image followed by a separate display component.
The display section begins at `0x040a00c4` in `.04.06` and `0x041000c4` in `.02.50`.
The `$GUI` header is 0x30 bytes into that section. The UI payload begins 24
bytes after the magic. The declared payload length is big-endian.

The payload contains:

1. A bzip2-compressed root TAR stream.
2. Three little-endian 32-bit lengths and their blobs: `uboot.bin`, `uImage`,
   `xloader.bin`.
3. A 10,000-byte metadata block: metadata-bzip length, repeated root-bzip
   length, metadata bzip2 stream, then `0xaa` padding.
4. `0xff` padding, a 10-byte date, and a two-byte checksum correction.

The patcher replaces only the GUI data bytes in the uncompressed root TAR,
compresses it with bzip2 level 9, updates its MD5 in `update/md5sum`, recompresses
the metadata TAR and adjusts padding. It preserves the original total payload
allocation and the date. The big-endian 16-bit word sum over the payload is
corrected to `0xa5a5`, matching the GUI's `FlashCheckSum` behavior.

The result is independently re-parsed. Every listed component MD5 is checked,
and the kernel/bootloader blobs, root TAR bytes and metadata TAR are compared
against expected values. The full output is checked against a fixed SHA-256
before being written.

`.04.06` has zero-length UI bootloader/xloader blobs. `.02.50` contains a
655,360-byte original UI bootloader and a 1,966,080-byte kernel blob. These are
preserved, not removed. Do not equate byte preservation with absence of flash
writes. In particular, the stock display updater can rewrite the included
kernel and removes the GUI directory before checking/extracting replacement
files. A failed update is not guaranteed recoverable over the network.

No vendor firmware is included in the repository. The constants and original
instruction bytes identify only the tiny patch locations; users obtain their
own full input from the official archive.

## Exact profiles

Machine-readable sizes, input/output hashes, GUI hashes, download URLs and
patch offsets: [firmware-profiles.json](firmware-profiles.json).

The `.04.06` output hash is identical to the physically installed package:

```text
be79af6cf998e8c260ed14c2611cca128db97a6d535e6b00acbe251c75a5a09b
```

The `.02.50` output hash is an **offline reference only**:

```text
111486f2aef5bc7c58bdca50bda49bf187c7adc936ed8b5546b28552fff585c1
```

## Optional address-book helper

`configure_smb.py` uses three ordinary SyncThru handlers under
`/sws/app/addressbook/`:

- `GetUsedSpeedNoInABook.jsp`: read occupied individual speed-dial numbers.
- `GetIndividualInABook.jsp`: read an entry back.
- `SetIndividualInABook.jsp`, `cmd=add`: add one new favorite after the user
  confirms the specific destination.

The helper supports only the guest-login parameter set used in the hardware
test. It sends Basic authentication and the existing SyncThru authentication
cookie to the user-entered printer. It does not store these credentials,
accept redirects, disable HTTPS verification or use a system proxy.
Plain HTTP has no transport encryption.

The helper uses a small data-only parser for the vendor's object syntax with
unquoted property names. No response is executed with `eval`. A write is never
automatically retried after an ambiguous response. The helper has no firmware,
scan-job, SSH or internal raw-network functionality.

## Manufacturer references

The official ZIPs linked in the guide include release notes. The newer release
notes describe the `.03.02` OPE/display hardware change and incompatibility
between generations. The older notes distinguish the `.02.50` branch. The
existing factory sticker on the tested unit listed `.04.03`; that does not
establish the factory firmware of every C1860FW ever shipped.
