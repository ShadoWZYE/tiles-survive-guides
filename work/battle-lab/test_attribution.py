import importlib.util,json,unittest
from pathlib import Path
from damage_ledger import ledger,owner
from audit_damage_attribution import fingerprints
class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.entities={'soldier':{'camp':0,'kind':'soldier','follow_hero':'hero'},'dog':{'camp':0,'kind':'summon','host':'hero','template_present':True,'is_not_statistics':0},'excluded':{'camp':0,'kind':'summon','host':'hero','template_present':True,'is_not_statistics':1}}
        self.registered=['hero','target','pet']
    def test_ownership_is_one_hop_with_direct_registration_first(self):
        for guid in ['soldier','dog']:self.assertEqual(owner(guid,self.entities,self.registered),'hero')
        self.assertIsNone(owner('excluded',self.entities,self.registered))
        self.entities['dog']['host']='soldier';self.assertIsNone(owner('dog',self.entities,self.registered))
        self.entities['pet']={'camp':1};self.assertEqual(owner('pet',self.entities,self.registered),'pet')
    def test_owner_and_mechanism_are_different_axes_and_shields_are_damage(self):
        events=[{'kind':'hp_change','source':'dog','target':'target','hp_change':-100,'mechanism':'summon'}, {'kind':'shield_absorb','source':'dog','target':'target','amount':40,'mechanism':'summon'}, {'kind':'hp_change','source':'pet','target':'hero','hp_change':25,'mechanism':'pet'}]
        result=ledger(events,self.entities,self.registered)
        self.assertEqual(result['owners']['hero']['damage'],140);self.assertEqual(result['owners']['target']['damage_taken'],140)
        self.assertEqual(result['owners']['hero']['hp_change_damage'],100);self.assertEqual(result['owners']['hero']['shield_absorbed'],40)
        self.assertEqual(result['owners']['pet']['healing'],25);self.assertEqual(result['owners']['hero']['healing_received'],25)
        self.assertEqual(result['mechanisms']['summon']['shield_absorbed'],40)
    def test_effect_opt_out_and_actor_opt_out_are_different(self):
        ignored={'kind':'hp_change','source':'hero','target':'target','hp_change':-100,'effect_is_not_statistics':1}
        r=ledger([ignored],self.entities,self.registered);self.assertEqual(r['owners']['hero']['damage'],0);self.assertEqual(r['ignored_hp_change_events'],1)
        r=ledger([dict(ignored,source='excluded',effect_is_not_statistics=0)],self.entities,self.registered)
        self.assertEqual(r['owners']['target']['damage_taken'],100);self.assertEqual(r['unattributed']['outgoing_damage'],100)
        r=ledger([{'kind':'shield_absorb','source':'hero','target':'excluded','amount':30,'effect_is_not_statistics':1}],self.entities,self.registered)
        self.assertEqual(r['owners']['hero']['damage'],30);self.assertEqual(r['unattributed']['incoming_damage'],30)
    def test_wrong_native_artifact_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unverified'):fingerprints(b'wrong',b'wrong',b'wrong')
    def test_invalid_event_numbers_are_rejected(self):
        for value in [float('nan'),float('inf'),True]:
            with self.assertRaises(ValueError):ledger([{'kind':'hp_change','hp_change':value}],{},[])
if __name__=='__main__':unittest.main()
