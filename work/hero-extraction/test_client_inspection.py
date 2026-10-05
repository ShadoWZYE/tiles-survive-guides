import importlib.util
import json
import lzma
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from audit_native_client import entropy, metadata_header, pe_sections
from export_client_asset import read_sos_entry
from probe_metadata_patterns import infer_xor_mask, xor_bytes
from unpack_client_lzma import decode_stream, unpack


class ClientInspectionTests(unittest.TestCase):
    def test_lzma_decoder_requires_exact_complete_stream(self):
        plain = b'Offline synthetic code bytes' * 100
        encoded = lzma.compress(plain, format=lzma.FORMAT_RAW, filters=[{
            'id': lzma.FILTER_LZMA1, 'dict_size': 8388608, 'lc': 3, 'lp': 0, 'pb': 2}])
        self.assertEqual(decode_stream(encoded, len(plain)), plain)
        for payload, size in ((encoded, len(plain)-1), (encoded, len(plain)+1),
                              (encoded[:-1], len(plain)), (encoded+b'x', len(plain))):
            with self.assertRaises(ValueError):
                decode_stream(payload, size)
        with self.assertRaises(ValueError):
            decode_stream(encoded, 0)

    def test_lzma_layout_is_hash_gated(self):
        with self.assertRaisesRegex(ValueError, 'Unverified client hash'):
            unpack(b'not the verified client')

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

    def test_statistical_mask_on_synthetic_fixture(self):
        mask = bytes((1, 2, 3, 4))
        plain = b'e' * 4096
        encoded = xor_bytes(plain, mask)
        inferred = infer_xor_mask(encoded, 4, ord('e'))
        self.assertEqual(inferred, mask)
        self.assertEqual(xor_bytes(encoded, inferred), plain)
        self.assertEqual(xor_bytes(encoded[1:5], inferred, 1), b'eeee')

    def test_invalid_statistical_parameters(self):
        with self.assertRaises(ValueError):
            infer_xor_mask(b'x', 128, 0)
        with self.assertRaises(ValueError):
            xor_bytes(b'x', b'')

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

    @unittest.skipUnless(importlib.util.find_spec('pefile') and importlib.util.find_spec('capstone'),
                         'Optional offline tracing dependencies are not installed')
    def test_static_tracer_does_not_resolve_indirect_jump(self):
        data = bytearray(1024)
        data[:2] = b'MZ'
        struct.pack_into('<I', data, 0x3C, 0x80)
        data[0x80:0x84] = b'PE\0\0'
        struct.pack_into('<HHIIIHH', data, 0x84, 0x8664, 1, 0, 0, 0, 0xF0, 0x2022)
        optional = 0x98
        struct.pack_into('<H', data, optional, 0x20B)
        struct.pack_into('<I', data, optional + 16, 0x1000)
        struct.pack_into('<Q', data, optional + 24, 0x180000000)
        struct.pack_into('<II', data, optional + 32, 0x1000, 512)
        struct.pack_into('<II', data, optional + 56, 0x2000, 512)
        section = optional + 0xF0
        data[section:section + 8] = b'.text\0\0\0'
        struct.pack_into('<IIII', data, section + 8, 512, 0x1000, 512, 512)
        struct.pack_into('<I', data, section + 36, 0x60000020)
        data[512:514] = b'\xFF\xE0'  # jmp rax, inspected as bytes only.
        with tempfile.TemporaryDirectory() as folder:
            binary = Path(folder)/'synthetic.bin'
            output = Path(folder)/'trace.json'
            binary.write_bytes(data)
            subprocess.run([sys.executable, str(Path(__file__).with_name('trace_native_file.py')),
                            '--binary', str(binary), '--output', str(output)],
                           check=True, capture_output=True, timeout=20)
            result = json.loads(output.read_text())
            self.assertEqual(result['instruction_count'], 1)
            self.assertEqual(result['unresolved_indirect_branches'], 1)
            self.assertFalse(result['budget_reached'])

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
