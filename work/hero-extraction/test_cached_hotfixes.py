import struct,unittest
from audit_cached_hotfixes import MAGIC,parse

def integer(value):return struct.pack('<i',value)
def string(value):
    raw=value.encode();assert len(raw)<128;return bytes([len(raw)])+raw
def fixture(*,type_index=0,body_index=0):
    # One method body, one external type, no optional metadata or anonymous slots.
    data=MAGIC+string('IFix.ILFixInterfaceBridge, Assembly-CSharp')+integer(1)+string('SkillBase, Assembly-CSharp')
    data+=integer(1)+integer(1)+integer(0)+integer(0)+integer(0)
    data+=integer(0)*5  # external methods, strings, fields, static fields, anonymous objects
    data+=string('IFix.WrappersManagerImpl')+string(', Assembly-CSharp')+integer(1)
    data+=b'\0'+integer(type_index)+string('OnUseSkill')+integer(0)+integer(body_index)+integer(0)
    return data

class CachedHotfixTests(unittest.TestCase):
    def test_exact_replacement_identity_and_body_hash(self):
        result=parse(fixture());self.assertEqual(result['replacements'][0]['type'],'SkillBase')
        self.assertEqual(result['replacements'][0]['name'],'OnUseSkill')
        self.assertEqual(result['replacements'][0]['instruction_count'],1)
    def test_every_truncation_is_rejected(self):
        raw=fixture()
        for size in range(len(raw)):
            with self.subTest(size=size),self.assertRaises((ValueError,UnicodeDecodeError)):parse(raw[:size])
    def test_unknown_layout_and_trailing_data_are_rejected(self):
        for raw in [b'xxxxxxxx'+fixture()[8:],fixture()+b'\0',fixture(type_index=-1),fixture(type_index=1),fixture(body_index=-1),fixture(body_index=1)]:
            with self.subTest(raw=raw[:12]),self.assertRaises(ValueError):parse(raw)
    def test_corrupt_count_is_not_an_empty_success(self):
        raw=fixture();offset=8+1+len('IFix.ILFixInterfaceBridge, Assembly-CSharp')
        for count in [-1,100001]:
            with self.assertRaises(ValueError):parse(raw[:offset]+integer(count)+raw[offset+4:])

if __name__=='__main__':unittest.main()
