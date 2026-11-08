import unittest
from audit_field_bridge import export

class FieldBridgeTests(unittest.TestCase):
    def fixture(self):
        tables={'survivor_skill_type':[{'Id':'source','SurvivorSlgSkillNew_ID':10}],
                'survivor_slg_skill_new':[{'InternalId':10,'Id':'field','SkillEffectNew_ID':[20],'InitialCd':100,'CommonCd':300}],
                'survivor_slg_effect_new':[{'InternalId':20,'Id':'proxy','Type':11100,'EffectAttrRate':0,'TargetTypeLite':1,
                 'TargetPosition':1,'TargetNum':1,'TargetArmy':0,'SpecialTarget':0,'AttackCount':1,'AttackInterval':0,'ExtraTriggerSkill':[]}]}
        return tables,[{'asset_slug':'hero','skills':[{'internal_name':'source'}]}]
    def test_proxy_is_not_promoted_to_damage_formula(self):
        tables,roster=self.fixture();link=export(tables,roster)['hero'][0]
        self.assertFalse(link['damage_bridge_verified']);self.assertEqual(link['effects'][0]['Type'],11100)
        self.assertEqual(link['common_cd_raw'],300)
    def test_broken_identity_is_not_a_silent_zero(self):
        tables,roster=self.fixture();tables['survivor_slg_effect_new']=[]
        with self.assertRaises(ValueError):export(tables,roster)
        tables,roster=self.fixture();roster[0]['skills'][0]['internal_name']='different_hero'
        with self.assertRaises(KeyError):export(tables,roster)

if __name__=='__main__':unittest.main()
