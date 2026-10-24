#!/usr/bin/env python3
"""Offline, exact-input SMB menu patcher for Samsung Xpress C1860FW firmware.

Python 3.10+, standard library only. Never communicates with a printer.
See docs/TECHNICAL.md for the container format and instruction changes.
"""
from __future__ import annotations

import argparse
import bz2
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import sys
import tarfile

VERSION = "1.0.0"
MAX_IMAGE = 128 * 1024 * 1024
MAX_TAR = 128 * 1024 * 1024
META_BLOCK = 10000
CHECKSUM = 0xA5A5
GUI_PATH = "usr/local/GUI/GV3_linux"


class PatchError(ValueError):
    """An input or output failed a required check."""


@dataclass(frozen=True)
class Profile:
    version: str
    ui: str
    tested: bool
    size: int
    source_sha256: str
    gui_sha256: str
    patched_gui_sha256: str
    section: int
    patches: tuple[tuple[int, bytes, bytes], ...]
    download: str
    expected_output_sha256: str = ""


PROFILES = (
    Profile(
        "4.00.04.06", "5.08.20.03", True, 99090700,
        "24baf64b6cb39c34eb4e97da3f910ef9ce5ac8882ef8f3a2aff9b8bfc5d14b05",
        "099d1330e6bd461ccdb0875ac59a334642cc5006be66b9392b4585c66af47873",
        "513abc9d6da9dcd2ad10c6bc8a7007d0479a5bea12937b4c54aab239b7895a58",
        0x040A00C4,
        ((0x5CFDC, bytes.fromhex("b0309fe5"), bytes.fromhex("050000ea")),
         (0x5D51C, bytes.fromhex("0010a0e3"), bytes.fromhex("0110a0e3"))),
        "https://ftp.hp.com/pub/softlib/software13/printers/SS/SL-C1860FW/SL-C1860_V4.00.04.06.zip",
        "be79af6cf998e8c260ed14c2611cca128db97a6d535e6b00acbe251c75a5a09b",
    ),
    Profile(
        "4.00.02.50", "5.08.51.05", False, 103285004,
        "9ef315565b2d16b69319679f958b988fdf272c7a3ba99562f57062176f967849",
        "65c91209f6792d4daf3a0495d1d4e2e161f05c39ae922fc8d3cf1ade4ca82998",
        "3292105b448d703b0f7673b24577873e7b35e8c8b548fd4f56e01ceea80d2358",
        0x041000C4,
        ((0x5CF78, bytes.fromhex("b0309fe5"), bytes.fromhex("050000ea")),
         (0x5D4B8, bytes.fromhex("0010a0e3"), bytes.fromhex("0110a0e3"))),
        "https://ftp.hp.com/pub/softlib/software13/printers/SS/SL-C1860FW/SL1860FW_V4.00.02.50.zip",
        "111486f2aef5bc7c58bdca50bda49bf187c7adc936ed8b5546b28552fff585c1",
    ),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PatchError(message)


def sha256(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def md5(data: bytes) -> str:
    # Format compatibility with the vendor updater; not a security primitive.
    return hashlib.md5(data, usedforsecurity=False).hexdigest()


def checksum16(data: bytes | bytearray) -> int:
    require(len(data) % 2 == 0, "UI payload has an odd byte count.")
    return sum(w[0] for w in struct.iter_unpack(">H", data)) & 0xFFFF


def identify(data: bytes) -> Profile:
    digest = sha256(data)
    for profile in PROFILES:
        if digest == profile.source_sha256:
            require(len(data) == profile.size, "Unexpected firmware length.")
            return profile
    raise PatchError(
        "Unsupported file or already patched firmware. Nothing was changed.\n"
        f"SHA-256: {digest}\n"
        "Select the ORIGINAL .hd extracted from one of the supported HP ZIPs, "
        "not the ZIP, a firmware dump, or an SMB output file."
    )


def decompress_first(data: bytes) -> tuple[bytes, int]:
    decoder = bz2.BZ2Decompressor()
    try:
        result = decoder.decompress(data, max_length=MAX_TAR + 1)
    except (OSError, EOFError) as exc:
        raise PatchError("Invalid bzip2 stream.") from exc
    require(len(result) <= MAX_TAR and decoder.eof,
            "Incomplete or oversized bzip2 stream.")
    return result, len(data) - len(decoder.unused_data)


def tar_member(data: bytes, name: str) -> tuple[tarfile.TarInfo, bytes]:
    # Read members in memory. Never extract archive paths to the filesystem.
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
            matches = [m for m in archive if m.name.lstrip("./") == name]
            require(len(matches) == 1 and matches[0].isfile(),
                    f"Expected one regular TAR member: {name}")
            member = matches[0]
            require(member.offset_data + member.size <= len(data), "Truncated TAR member.")
            stream = archive.extractfile(member)
            require(stream is not None, "Cannot read TAR member.")
            return member, stream.read()
    except (tarfile.TarError, OSError) as exc:
        raise PatchError("Invalid TAR archive.") from exc


def parse_payload(payload: bytes) -> dict:
    require(12 < len(payload) <= MAX_IMAGE, "Invalid UI payload length.")
    require(checksum16(payload) == CHECKSUM, "UI checksum does not match 0xA5A5.")
    root_tar, root_length = decompress_first(payload)
    position = root_length
    blobs = {}
    for name in ("uboot.bin", "uImage", "xloader.bin"):
        require(position + 4 <= len(payload) - 12, "Missing component size.")
        size = struct.unpack_from("<I", payload, position)[0]
        position += 4
        require(position + size <= len(payload) - 12, "Component exceeds UI payload.")
        blobs[name] = payload[position:position + size]
        position += size
    metadata_offset = position
    require(position + META_BLOCK <= len(payload) - 12, "Missing metadata block.")
    metadata_length, repeated_root = struct.unpack_from("<II", payload, position)
    require(repeated_root == root_length, "Root stream length footer mismatch.")
    require(0 < metadata_length <= META_BLOCK - 8, "Invalid metadata stream length.")
    metadata_bzip = payload[position + 8:position + 8 + metadata_length]
    metadata_tar, consumed = decompress_first(metadata_bzip)
    require(consumed == metadata_length, "Metadata stream boundary mismatch.")
    padding = payload[position + 8 + metadata_length:position + META_BLOCK]
    require(padding == b"\xaa" * len(padding), "Unexpected metadata padding.")
    padding = payload[position + META_BLOCK:-12]
    require(padding == b"\xff" * len(padding), "Unexpected UI trailing data.")
    member, digest_bytes = tar_member(metadata_tar, "update/md5sum")
    try:
        digest_text = digest_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise PatchError("Non-ASCII MD5 manifest.") from exc
    checks = {}
    for line in digest_text.splitlines():
        match = re.fullmatch(r"([0-9a-f]{32})\s+\*?([A-Za-z0-9_.]+)", line)
        require(match is not None, "Unexpected MD5 manifest entry.")
        digest, name = match.groups()
        require(name not in checks, "Duplicate MD5 manifest entry.")
        checks[name] = digest
    components = {"rootfs_patch.tar.bz2": payload[:root_length], **blobs}
    require("rootfs_patch.tar.bz2" in checks and "uImage" in checks,
            "Incomplete MD5 manifest.")
    for name, digest in checks.items():
        require(name in components and md5(components[name]) == digest,
                f"MD5 verification failed: {name}")
    return dict(root_tar=root_tar, root_bzip=payload[:root_length], blobs=blobs,
                metadata_tar=metadata_tar, digest_text=digest_text,
                digest_offset=member.offset_data, date=payload[-12:-2])


def patch_gui(original: bytes, profile: Profile) -> bytes:
    require(sha256(original) == profile.gui_sha256, "GUI SHA-256 mismatch.")
    patched = bytearray(original)
    for offset, before, after in profile.patches:
        require(len(before) == len(after) == 4, "Invalid patch instruction size.")
        require(patched[offset:offset + 4] == before,
                f"Unexpected instruction at file offset 0x{offset:x}.")
        patched[offset:offset + 4] = after
    require(sum(a != b for a, b in zip(original, patched)) == 5,
            "Expected exactly five changed GUI bytes.")
    require(sha256(patched) == profile.patched_gui_sha256, "Patched GUI SHA-256 mismatch.")
    return bytes(patched)


def rebuild_payload(payload: bytes, profile: Profile) -> tuple[bytes, dict]:
    parsed = parse_payload(payload)
    member, gui = tar_member(parsed["root_tar"], GUI_PATH)
    patched_gui = patch_gui(gui, profile)
    modified_tar = bytearray(parsed["root_tar"])
    modified_tar[member.offset_data:member.offset_data + member.size] = patched_gui
    require(sum(a != b for a, b in zip(parsed["root_tar"], modified_tar)) == 5,
            "Unexpected root TAR modification.")
    root_bzip = bz2.compress(bytes(modified_tar), compresslevel=9)
    old_digest, new_digest = md5(parsed["root_bzip"]), md5(root_bzip)
    require(parsed["digest_text"].count(old_digest) == 1, "Ambiguous root MD5 entry.")
    digest_text = parsed["digest_text"].replace(old_digest, new_digest)
    metadata_tar = bytearray(parsed["metadata_tar"])
    offset = parsed["digest_offset"]
    metadata_tar[offset:offset + len(digest_text)] = digest_text.encode("ascii")
    metadata_bzip = bz2.compress(bytes(metadata_tar), compresslevel=9)
    require(len(metadata_bzip) <= META_BLOCK - 8, "Metadata exceeds allocated block.")
    new_payload = bytearray(root_bzip)
    for name in ("uboot.bin", "uImage", "xloader.bin"):
        blob = parsed["blobs"][name]
        new_payload += struct.pack("<I", len(blob)) + blob
    new_payload += struct.pack("<II", len(metadata_bzip), len(root_bzip))
    new_payload += metadata_bzip
    new_payload += b"\xaa" * (META_BLOCK - 8 - len(metadata_bzip))
    remaining = len(payload) - 12 - len(new_payload)
    require(remaining >= 0, "Patched payload exceeds original allocation.")
    new_payload += b"\xff" * remaining + parsed["date"]
    new_payload += struct.pack(">H", (CHECKSUM - checksum16(new_payload)) & 0xFFFF)
    require(len(new_payload) == len(payload), "UI payload size changed.")
    verified = parse_payload(bytes(new_payload))
    require(verified["root_tar"] == modified_tar, "Root TAR roundtrip failed.")
    require(verified["metadata_tar"] == metadata_tar, "Metadata roundtrip failed.")
    require(verified["blobs"] == parsed["blobs"], "Kernel or bootloader bytes changed.")
    return bytes(new_payload), {
        "gui_changed_bytes": 5,
        "gui_changed_instructions": 2,
        "mainboard_payload_unchanged": True,
        "other_root_tar_bytes_unchanged": True,
        "kernel_and_bootloader_bytes_unchanged": True,
        "original_bootloader_component_bytes": len(parsed["blobs"]["uboot.bin"]),
        "original_xloader_component_bytes": len(parsed["blobs"]["xloader.bin"]),
        "gui_sha256": sha256(patched_gui),
        "ui_checksum16_be": "0xa5a5",
        "metadata_md5_verified": True,
    }


def build_image(data: bytes, profile: Profile) -> tuple[bytes, dict]:
    require(len(data) == profile.size and sha256(data) == profile.source_sha256,
            "Firmware does not match the selected profile.")
    section = profile.section
    magic = section + 0x30
    payload_offset = magic + 24
    require(0x50 + struct.unpack_from(">I", data, 0x54)[0] == section,
            "Mainboard image boundary mismatch.")
    require(data[magic:magic + 4] == b"$GUI", "Missing UI component header.")
    require(struct.unpack_from(">I", data, magic + 8)[0] == len(data) - payload_offset,
            "UI component length mismatch.")
    payload, checks = rebuild_payload(data[payload_offset:], profile)
    result = data[:payload_offset] + payload
    require(result[:payload_offset] == data[:payload_offset] and len(result) == len(data),
            "Headers, mainboard image or total size changed.")
    if profile.expected_output_sha256:
        require(sha256(result) == profile.expected_output_sha256,
                "Output differs from the reviewed reproducible build. No output written.")
    return result, checks


def inspect_file(path: Path) -> Profile:
    require(path.is_file(), f"File not found: {path}")
    require(path.stat().st_size <= MAX_IMAGE, "File exceeds supported maximum size.")
    return identify(path.read_bytes())


def patch_file(path: Path, output: Path | None = None, *, allow_untested: bool = False,
               log=print) -> dict:
    profile = inspect_file(path)
    require(profile.tested or allow_untested,
            "V4.00.02.50 is UNTESTED on hardware. Read docs/ANLEITUNG.md. "
            "Explicitly use --allow-untested, or the GUI checkbox, to build it.")
    if output is None:
        suffix = "_SMB.hd" if profile.tested else "_SMB_UNTESTED.hd"
        output = path.with_name(path.stem + suffix)
    output = Path(output)
    report = output.with_suffix(output.suffix + ".json")
    require(path.resolve() != output.resolve(), "Refusing to overwrite the original.")
    require(not output.exists() and not report.exists(),
            f"Output already exists; choose a new name: {output}")
    require(output.parent.is_dir(), "Output directory does not exist.")
    log(f"Firmware V{profile.version}; UI V{profile.ui}; "
        + ("TESTED on one printer" if profile.tested else "UNTESTED on hardware"))
    log("Reading and checking firmware, TAR members, MD5 and UI checksum...")
    original = path.read_bytes()
    result, checks = build_image(original, profile)
    metadata = {
        "patcher_version": VERSION, "firmware_version": profile.version,
        "ui_version": profile.ui, "hardware_tested": profile.tested,
        "input_name": path.name, "output_name": output.name,
        "input_sha256": sha256(original), "output_sha256": sha256(result),
        "output_bytes": len(result), "checks": checks,
        "printer_contacted": False, "firmware_uploaded": False,
        "warning": "This report verifies the offline file, not installation or recovery.",
    }
    # Exclusive creation also protects against a file appearing after the check.
    created = []
    try:
        with output.open("xb") as stream:
            created.append(output)
            stream.write(result)
        with report.open("x", encoding="utf-8") as stream:
            created.append(report)
            json.dump(metadata, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    except BaseException:
        for target in reversed(created):
            target.unlink(missing_ok=True)
        raise
    log(f"Created: {output}")
    log(f"SHA-256: {metadata['output_sha256']}")
    log("Done. No printer contacted. Follow docs/ANLEITUNG.md for manual SyncThru installation.")
    return metadata


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, nargs="?", help="Original manufacturer .hd file")
    parser.add_argument("-o", "--output", type=Path, help="New .hd path; must not exist")
    parser.add_argument("--allow-untested", action="store_true", help="Allow the untested .02.50 profile")
    parser.add_argument("--inspect", action="store_true", help="Identify the input without writing output")
    parser.add_argument("--list", action="store_true", help="List supported exact firmware hashes")
    parser.add_argument("--gui", action="store_true", help="Open the optional Tk file chooser")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args(argv)
    if args.gui or (args.input is None and not any(
            (args.list, args.inspect, args.output, args.allow_untested))):
        try:
            from patcher_gui import main as gui_main
            gui_main()
            return 0
        except ImportError:
            print("Tkinter unavailable. Use: python patcher.py ORIGINAL.hd\n"
                  "See docs/ANLEITUNG.md for Python/Tk installation.", file=sys.stderr)
            return 2
    if args.list:
        for p in PROFILES:
            print(f"V{p.version} / UI V{p.ui}: "
                  f"{'TESTED' if p.tested else 'UNTESTED'}\n  SHA-256 {p.source_sha256}")
        return 0
    if args.input is None:
        parser.error("an original firmware input is required")
    try:
        if args.inspect:
            p = inspect_file(args.input)
            print(f"Recognized V{p.version} / UI V{p.ui}; "
                  f"{'TESTED' if p.tested else 'UNTESTED'}. No output written.")
        else:
            patch_file(args.input, args.output, allow_untested=args.allow_untested)
        return 0
    except (PatchError, OSError, struct.error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
