import hashlib,json,struct,tempfile,unittest
from pathlib import Path
from audit_field_dispatch import source_coverage

class DispatchCoverageTests(unittest.TestCase):
    def test_complete_corpus_and_missing_or_changed_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);scripts=root/'lua';scripts.mkdir();path=scripts/'Alpha.lua';raw=b'local example = 1';path.write_bytes(raw)
            record=struct.pack('<III',1,1,0)+b'\x09alpha.lua'+struct.pack('<I',42)
            index=root/'assets';index.write_bytes(record+struct.pack('<IIII',0,0,0,len(record)))
            provenance={'files':{'Alpha.lua':hashlib.sha256(raw).hexdigest()}}
            result=source_coverage(index,scripts,provenance);self.assertEqual(result['searched_utf8_sources'],1)
            self.assertEqual(result['symbol_hits'],{})
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):source_coverage(index,scripts,provenance)
            path.unlink()
            with self.assertRaises(ValueError):source_coverage(index,scripts,provenance)

if __name__=='__main__':unittest.main()
