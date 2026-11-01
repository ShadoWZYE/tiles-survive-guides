import hashlib
import json
import unittest
from pathlib import Path
from audit_native_combat import decode_metadata,fingerprint,SELECTED,CURRENT_SHA256
from unpack_client_lzma import unpack

try:
    import capstone
except ImportError:
    capstone=None


class NativeAuditTests(unittest.TestCase):
    def test_unknown_binary_and_metadata_are_rejected_before_decoding(self):
        with self.assertRaisesRegex(ValueError,'Unverified'):unpack(b'unknown')
        with self.assertRaisesRegex(ValueError,'Unverified'):decode_metadata(b'unknown')

    def test_shipped_audit_covers_selected_methods_and_is_joined_by_hash(self):
        folder=Path(__file__).resolve().parents[2]/'outputs/hero-report'
        raw=(folder/'Hero-Native-Combat-Audit.json').read_bytes();audit=json.loads(raw)
        graph=json.loads((folder/'Hero-Combat-Audit.json').read_bytes())
        required={(t,m) for t,names in SELECTED.items() for m in names}
        self.assertTrue(required<={(m['type'],m['name']) for m in audit['methods']})
        self.assertEqual(audit['binary_sha256'],CURRENT_SHA256)
        self.assertEqual(graph['native_audit']['audit_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertTrue(audit['verified_claims']['finish_condition_ignores_interrupted'])
        self.assertEqual(audit['baseline_comparison']['base_path_matches'],audit['baseline_comparison']['checked_count'])

    @unittest.skipUnless(capstone,'Private disassembler dependency unavailable')
    def test_patch_id_normalization_preserves_gameplay_constants(self):
        # mov ecx, ID; call 0x100; mov eax, GAMEPLAY; ret; padding.
        def code(patch,value,pad=0):
            return b'\xb9'+patch.to_bytes(4,'little')+b'\xe8\xf6\x00\x00\x00\xb8'+value.to_bytes(4,'little')+b'\xc3'+b'\xcc'*pad
        def fp(raw,targets=(0x100,)):return fingerprint(raw,0,len(raw),targets)[0]
        a=fp(code(100,7));b=fp(code(200,7,3));c=fp(code(200,8))
        self.assertNotEqual(a['normalized_sha256'],b['normalized_sha256'])
        self.assertEqual(a['base_path_sha256'],b['base_path_sha256'])
        self.assertNotEqual(b['base_path_sha256'],c['base_path_sha256'])
        self.assertNotEqual(fp(code(100,7),())['base_path_sha256'],fp(code(200,7),())['base_path_sha256'])


if __name__=='__main__':unittest.main()
