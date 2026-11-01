import unittest,struct
from audit_city_stacking import aggregate_cities,patch_type_names


class CityStackingTests(unittest.TestCase):
    def setUp(self):
        self.configs={1:{'benefits':[{'id':100,'value':.05}]},2:{'benefits':[{'id':100,'value':.20}]},
            3:{'benefits':[{'id':200,'value':.10}]},4:{'benefits':[{'id':200,'value':.10}]}}

    def test_repeated_configuration_counts_once(self):
        self.assertEqual(aggregate_cities([('a',1),('b',1),('c',1)],self.configs,{}),{100:.05})

    def test_distinct_configuration_ids_add_not_highest_only(self):
        self.assertEqual(aggregate_cities([('a',1),('b',2)],self.configs,{}),{100:.25})

    def test_same_value_same_stat_different_configurations_add(self):
        self.assertEqual(aggregate_cities([('a',3),('b',4)],self.configs,{}),{200:.20})

    def test_all_six_level_five_sites_still_two_entries(self):
        self.assertEqual(aggregate_cities([(str(i),3 if i<3 else 4) for i in range(6)],self.configs,{}),{200:.20})

    def test_inactive_first_copy_does_not_suppress_active_second_copy(self):
        self.assertEqual(aggregate_cities([('a',1),('b',1)],self.configs,{'a':0}),{100:.05})
        self.assertEqual(aggregate_cities([('a',1)],self.configs,{'a':0}),{})

    def test_absent_eligibility_container_or_missing_config_is_not_a_bonus(self):
        self.assertEqual(aggregate_cities([('a',1)],self.configs,None),{})
        self.assertEqual(aggregate_cities([('a',999)],self.configs,{}),{})

    def test_different_stats_remain_separate(self):
        self.assertEqual(aggregate_cities([('a',1),('b',3)],self.configs,{}),{100:.05,200:.10})

    def test_unknown_patch_format_rejected(self):
        with self.assertRaises(ValueError):patch_type_names(b'unknown')
        def string(s):
            raw=s.encode();return bytes([len(raw)])+raw
        raw=struct.pack('<Q',317431043901)+string('IFix.Bridge')+struct.pack('<i',1)+string('StrongholdPage, Assembly-CSharp')
        self.assertEqual(patch_type_names(raw),{'StrongholdPage'})
        with self.assertRaises(ValueError):patch_type_names(raw[:-2])


if __name__=='__main__':unittest.main()
