import unittest
from accuracy_metrics import damage_metrics,paired_ranking_metrics
class AccuracyTests(unittest.TestCase):
    def case(self):
        return {'id':'one','evaluation_role':'held_out','outcome_recorded_at':'2026-11-07T12:01:00Z','damage_definition':'owned_rows_including_absorption','damage_observed':{'hero':100,'pet':0},'prediction':{'model_sha256':'a'*64,'recorded_at':'2026-11-07T12:00:00Z','damage_definition':'owned_rows_including_absorption','damage':{'hero':80,'pet':5}}}
    def test_real_metrics_and_duplicate_rejection(self):
        c=self.case();r=damage_metrics([c,c],'a'*64);self.assertEqual(r['mae'],12.5);self.assertEqual(r['wape'],.25);self.assertEqual(r['independent_eligible_battles'],1);self.assertEqual(r['exclusions']['duplicate_or_missing_battle_id'],1)
    def test_no_prediction_or_mismatched_definition_is_not_zero_error(self):
        for mode in ['definition','future','hash','calibration','missing']:
            c=self.case()
            if mode=='definition':c['prediction']['damage_definition']='hp_removed_only'
            if mode=='future':c['prediction']['recorded_at']='2026-11-07T12:02:00Z'
            if mode=='hash':c['prediction']['model_sha256']='b'*64
            if mode=='calibration':c['evaluation_role']='calibration'
            if mode=='missing':c['prediction']=None
            r=damage_metrics([c],'a'*64);self.assertEqual(r['owner_pairs'],0);self.assertIsNone(r['mae']);self.assertIsNone(r['wape'])
    def test_zero_observation_allows_absolute_but_not_relative_error(self):
        c=self.case();c['damage_observed']={'pet':0};r=damage_metrics([c],'a'*64);self.assertEqual(r['mae'],5);self.assertIsNone(r['wape'])
    def test_rally_shares_cannot_validate_global_lineup_ranking(self):
        p={'id':'pair','model_sha256':'a'*64,'evaluation_role':'held_out','matched_starting_context_verified':True,'prediction_frozen_before_both_outcomes_verified':True,'metric':'enemy_troop_losses','observed':[23,19],'predicted_scores':[80,90]}
        r=paired_ranking_metrics([p],'a'*64);self.assertEqual(r['pairwise_agreement'],0)
        self.assertEqual(paired_ranking_metrics([p],'b'*64)['matched_pairs'],0)
        p['confounded_by_other_participants']=True;r=paired_ranking_metrics([p],'a'*64);self.assertEqual(r['matched_pairs'],0);self.assertIsNone(r['pairwise_agreement'])
if __name__=='__main__':unittest.main()
