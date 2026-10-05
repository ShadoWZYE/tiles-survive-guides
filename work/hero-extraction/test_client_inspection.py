from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from audit_native_client import entropy, metadata_header, pe_sections
from export_client_asset import read_sos_entry


class ClientInspectionTests(unittest.TestCase):
    def test_metadata_wrapper_is_not_standard_version(self):
        data = struct.pack("<II", 0xFAB11BAF, 64) + bytes(56)
        self.assertTrue(metadata_header(data)["second_word_equals_file_size"])
        self.assertFalse(metadata_header(data)["plausible_standard_header"])

    def test_header_is_only_plausibility(self):
        self.assertTrue(metadata_header(struct.pack("<II", 0xFAB11BAF, 29))["plausible_standard_header"])
        self.assertFalse(metadata_header(b"x")["plausible_standard_header"])

    def test_entropy(self):
        self.assertEqual(entropy(b""), 0)
        self.assertEqual(entropy(bytes(100)), 0)
        self.assertEqual(entropy(bytes(range(256))), 8)

    def test_reject_non_pe(self):
        with self.assertRaises(ValueError):
            pe_sections(b"not-a-dll")

    def test_reject_truncated_pe(self):
        data = bytearray(64)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 0x3C, 60)
        data[60:] = b"PE\0\0"
        with self.assertRaises(ValueError):
            pe_sections(data)

    def test_sos_geometry_does_not_change_address_unit(self):
        slots = 4096
        name = "a" * 32
        payload = b"prefixUnityFSfixture"
        block = 270
        data = bytearray(block * 4096 + len(payload))
        struct.pack_into("<4sIII", data, 0, b"\x00SOS", 2048, slots, 1)
        struct.pack_into("<III", data, 16, 332, block, len(payload))
        pos = 16 + slots * 12 + 332 * 256
        data[pos] = len(name)
        data[pos + 1:pos + 1 + len(name)] = name.encode()
        data[block * 4096:] = payload
        with tempfile.TemporaryDirectory() as folder:
            pack = Path(folder) / "fixture.ss"
            pack.write_bytes(data)
            self.assertEqual(read_sos_entry(pack, name), payload)
            self.assertIsNone(read_sos_entry(pack, "b" * 32))
            struct.pack_into("<I", data, 16, 0xFFFFFFFF)
            pack.write_bytes(data)
            self.assertIsNone(read_sos_entry(pack, name))


if __name__ == "__main__":
    unittest.main()
