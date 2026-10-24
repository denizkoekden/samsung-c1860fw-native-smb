import bz2
from dataclasses import replace
import io
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import patcher as p


def archive(members):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tar:
        for name, value in members.items():
            member = tarfile.TarInfo(name)
            member.size = len(value)
            member.mode = 0o755
            tar.addfile(member, io.BytesIO(value))
    return stream.getvalue()


def fixture():
    gui = bytes.fromhex("b0309fe5") + b"KEEP" + bytes.fromhex("0010a0e3") + b"TAIL"
    patched = bytes.fromhex("050000ea") + b"KEEP" + bytes.fromhex("0110a0e3") + b"TAIL"
    root = bz2.compress(archive({p.GUI_PATH: gui, "etc/keep": b"untouched\n"}), 9)
    blobs = {"uboot.bin": b"BOOTLOADER-MUST-STAY", "uImage": b"KERNEL-MUST-STAY", "xloader.bin": b""}
    digests = "".join(f"{p.md5(data)}  {name}\n" for name, data in
                      {"rootfs_patch.tar.bz2": root, "uImage": blobs["uImage"],
                       "uboot.bin": blobs["uboot.bin"]}.items())
    meta = bz2.compress(archive({"update/md5sum": digests.encode(),
                                "update/post_update.sh": b"do not execute me\n"}), 9)
    payload = bytearray(root)
    for blob in blobs.values():
        payload += struct.pack("<I", len(blob)) + blob
    payload += struct.pack("<II", len(meta), len(root)) + meta
    payload += b"\xaa" * (p.META_BLOCK - 8 - len(meta))
    payload += b"\xff" * (32768 - 12 - len(payload)) + b"2016-05-25"
    payload += struct.pack(">H", (p.CHECKSUM - p.checksum16(payload)) & 65535)
    section = 256
    header = bytearray(b"H" * (section + 0x30 + 24))
    struct.pack_into(">I", header, 0x54, section - 0x50)
    header[section + 0x30:section + 0x34] = b"$GUI"
    struct.pack_into(">I", header, section + 0x38, len(payload))
    data = bytes(header + payload)
    profile = p.Profile("test", "test", True, len(data), p.sha256(data),
        p.sha256(gui), p.sha256(patched), section,
        ((0, gui[:4], patched[:4]), (8, gui[8:12], patched[8:12])), "https://example.invalid")
    return data, profile, gui, patched


class PatcherTests(unittest.TestCase):
    def test_roundtrip_preserves_headers_components_and_other_tar_bytes(self):
        data, profile, gui, patched = fixture()
        result, checks = p.build_image(data, profile)
        offset = profile.section + 0x30 + 24
        before, after = p.parse_payload(data[offset:]), p.parse_payload(result[offset:])
        self.assertEqual(data[:offset], result[:offset])
        self.assertEqual(len(data), len(result))
        self.assertEqual(before["blobs"], after["blobs"])
        self.assertEqual(p.tar_member(after["root_tar"], p.GUI_PATH)[1], patched)
        self.assertEqual(p.tar_member(after["root_tar"], "etc/keep")[1], b"untouched\n")
        self.assertEqual(sum(a != b for a, b in zip(before["root_tar"], after["root_tar"])), 5)
        self.assertEqual(checks["original_bootloader_component_bytes"], len(b"BOOTLOADER-MUST-STAY"))
        self.assertEqual(p.checksum16(result[offset:]), p.CHECKSUM)

    def test_unknown_or_modified_firmware_is_rejected(self):
        with self.assertRaises(p.PatchError):
            p.identify(b"not official firmware")
        data, profile, _, _ = fixture()
        with patch.object(p, "PROFILES", (profile,)):
            with self.assertRaises(p.PatchError):
                p.identify(data[:-1] + bytes([data[-1] ^ 1]))

    def test_already_patched_input_is_rejected(self):
        data, profile, _, _ = fixture()
        result, _ = p.build_image(data, profile)
        with patch.object(p, "PROFILES", (profile,)):
            with self.assertRaises(p.PatchError):
                p.identify(result)

    def test_checksums_and_md5_cannot_be_bypassed_by_outer_checksum(self):
        data, profile, _, _ = fixture()
        offset = profile.section + 0x30 + 24
        payload = bytearray(data[offset:])
        parsed = p.parse_payload(bytes(payload))
        kernel_position = len(parsed["root_bzip"]) + 4 + len(parsed["blobs"]["uboot.bin"]) + 4
        payload[kernel_position] ^= 1
        payload[-2:] = struct.pack(">H", (p.CHECKSUM - p.checksum16(payload[:-2])) & 65535)
        with self.assertRaisesRegex(p.PatchError, "MD5"):
            p.parse_payload(bytes(payload))

    def test_wrong_instruction_or_gui_hash_is_rejected(self):
        _, profile, gui, _ = fixture()
        invalid = replace(profile, patches=((0, b"NOPE", b"1234"), *profile.patches[1:]))
        with self.assertRaisesRegex(p.PatchError, "instruction"):
            p.patch_gui(gui, invalid)
        with self.assertRaisesRegex(p.PatchError, "SHA-256"):
            p.patch_gui(gui + b"extra", profile)

    def test_untested_profile_needs_explicit_opt_in(self):
        data, profile, _, _ = fixture()
        with tempfile.TemporaryDirectory() as folder, patch.object(p, "PROFILES", (replace(profile, tested=False),)):
            source = Path(folder) / "original.hd"
            source.write_bytes(data)
            with self.assertRaisesRegex(p.PatchError, "UNTESTED"):
                p.patch_file(source, log=lambda _: None)
            self.assertEqual(list(Path(folder).iterdir()), [source])
            info = p.patch_file(source, allow_untested=True, log=lambda _: None)
            self.assertFalse(info["hardware_tested"])
            self.assertTrue(info["output_name"].endswith("_SMB_UNTESTED.hd"))

    def test_existing_files_and_original_are_not_overwritten(self):
        data, profile, _, _ = fixture()
        with tempfile.TemporaryDirectory() as folder, patch.object(p, "PROFILES", (profile,)):
            source = Path(folder) / "original.hd"
            source.write_bytes(data)
            output = Path(folder) / "output.hd"
            output.write_bytes(b"keep me")
            for target in (source, output):
                with self.assertRaises(p.PatchError):
                    p.patch_file(source, target, log=lambda _: None)
            self.assertEqual(output.read_bytes(), b"keep me")
            self.assertEqual(source.read_bytes(), data)

    def test_report_collision_does_not_leave_output(self):
        data, profile, _, _ = fixture()
        with tempfile.TemporaryDirectory() as folder, patch.object(p, "PROFILES", (profile,)):
            source = Path(folder) / "original.hd"
            source.write_bytes(data)
            output = Path(folder) / "output.hd"
            output.with_suffix(".hd.json").write_text("keep report")
            with self.assertRaises(p.PatchError):
                p.patch_file(source, output, log=lambda _: None)
            self.assertFalse(output.exists())

    def test_decompression_size_limit_and_truncation(self):
        compressed = bz2.compress(b"x" * 100)
        with patch.object(p, "MAX_TAR", 50):
            with self.assertRaises(p.PatchError):
                p.decompress_first(compressed)
        with self.assertRaises(p.PatchError):
            p.decompress_first(compressed[:-5])

    def test_gui_symlink_is_not_accepted_as_file(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as tar:
            member = tarfile.TarInfo(p.GUI_PATH)
            member.type = tarfile.SYMTYPE
            member.linkname = "/etc/passwd"
            tar.addfile(member)
        with self.assertRaises(p.PatchError):
            p.tar_member(stream.getvalue(), p.GUI_PATH)


if __name__ == "__main__":
    unittest.main()
