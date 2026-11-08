import unittest
from import_field_report import normalize,pointer

class FieldReportImportTests(unittest.TestCase):
    def fixture(self):
        owner={'uid':'PRIVATE','survivor_damage_and_withstand':[{'i_survivor':123,'damage':9230123,'cure':98831,'withstand':14250017}]}
        roster=[{'hero_id':123,'asset_slug':'ray'}]
        rounds=[[[{'pos':4,'hp':1000123,'start_hp':2000456,'heal_hp':901}]]]
        return owner,roster,rounds
    def test_precision_identity_and_private_fields(self):
        owner,roster,rounds=self.fixture();result=normalize(owner,roster,rounds)
        self.assertEqual(result['heroes'][0]['damage'],9230123);self.assertEqual(result['round_states'][0]['snapshots'][0]['units'][0]['hp'],1000123)
        self.assertNotIn('uid',result);self.assertNotIn('PRIVATE',str(result));self.assertIsNone(result['independent_damage_accuracy'])
    def test_no_implicit_identity_or_owner_guess(self):
        owner,roster,rounds=self.fixture()
        self.assertEqual(normalize(owner,roster,rounds)['position_owner_mapping'],'not supplied or inferred')
        with self.assertRaises(ValueError):normalize(owner,[],rounds)
        owner['survivor_damage_and_withstand']*=2
        with self.assertRaises(ValueError):normalize(owner,roster)
    def test_invalid_and_abbreviated_values_are_rejected(self):
        for value in [True,-1,float('nan'),float('inf'),'9.23M']:
            owner,roster,_=self.fixture();owner['survivor_damage_and_withstand'][0]['damage']=value
            with self.subTest(value=value),self.assertRaises(ValueError):normalize(owner,roster)
    def test_round_layout_and_position_are_not_silently_filled(self):
        owner,roster,rounds=self.fixture();rounds[0][0]*=2
        with self.assertRaises(ValueError):normalize(owner,roster,rounds)
        self.assertEqual(pointer({'a/b':{'~key':[10]}},'/a~1b/~0key/0'),10)
        with self.assertRaises(ValueError):pointer({},'guess owner')

if __name__=='__main__':unittest.main()
