import struct,unittest
from native_literal_reader import validate_heap,decode_usage,NativeLiteralReader

class NativeLiteralTests(unittest.TestCase):
    def test_contiguous_utf8_heap_and_usage_kind(self):
        raw=struct.pack('<IIII',2,0,3,2)+b'hppos';strings=validate_heap(raw,0,16,21,2)
        self.assertEqual(strings,['hp','pos']);self.assertEqual(decode_usage(0xa0000003,strings),'pos')
        for bad in [0xa0000000,0x80000001,0xa0000005,-1,2**32+1]:
            with self.assertRaises(ValueError):decode_usage(bad,strings)
    def test_gaps_truncation_and_unconsumed_bytes_are_rejected(self):
        for raw in [struct.pack('<IIII',2,0,3,1)+b'hppos',struct.pack('<IIII',2,0,4,2)+b'hppos']:
            with self.assertRaises(ValueError):validate_heap(raw,0,16,21,2)
        with self.assertRaises(ValueError):validate_heap(b'',0,16,21,2)
        with self.assertRaises(ValueError):validate_heap(struct.pack('<II',1,0)+b'ab',0,8,10,1)
    def test_unknown_snapshot_never_decodes(self):
        with self.assertRaises(ValueError):NativeLiteralReader(b'unknown image',b'unknown metadata')

if __name__=='__main__':unittest.main()
