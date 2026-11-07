import json
import unittest
from pathlib import Path
from validate_model_evidence import prediction_metrics,check_countdown,report


class EvidenceValidationTests(unittest.TestCase):
    def test_cli_rejects_duplicate_report_replay_evidence(self):
        import subprocess, sys, tempfile
        root=Path(__file__).resolve().parents[2]
        evidence=root/'outputs/hero-report/Replay-Observation-2026-11-07.json'
        with tempfile.TemporaryDirectory() as folder:
            result=subprocess.run([sys.executable,str(root/'work/hero-extraction/validate_model_evidence.py'),
                '--evidence',str(evidence),'--evidence',str(evidence),'--output',str(Path(folder)/'out.json')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Duplicate battle observation',result.stderr)
            self.assertFalse((Path(folder)/'out.json').exists())

    def test_absent_predictions_are_unknown_not_zero_or_perfect_accuracy(self):
        result=prediction_metrics([{'outcome':'loss','evaluation_role':'mechanics_observation'},
            {'outcome':'win','evaluation_role':'calibration','prediction':{'outcome':'win'}}])
        self.assertEqual(result['winner_cases'],0)
        self.assertIsNone(result['winner_accuracy'])
        self.assertIsNone(result['damage_mape'])

    def test_held_out_metrics_and_zero_observed_damage(self):
        def held(outcome,damage,predicted):
            return {'evaluation_role':'held_out','outcome':outcome,'outcome_recorded_at':'2026-10-25T12:01:00Z',
                'prediction':{'outcome':'win','damage':predicted,'recorded_at':'2026-10-25T12:00:00Z','model_sha256':'a'*64},'damage_observed':damage}
        result=prediction_metrics([
            held('win',{'a':100,'b':0},{'a':80,'b':5}),held('loss',{'a':50},{'a':float('nan')})])
        self.assertEqual(result['winner_accuracy'],.5)
        self.assertEqual(result['damage_pairs'],2)
        self.assertEqual(result['damage_mae'],12.5)
        self.assertEqual(result['damage_mape'],.2)

    def test_retroactive_predictions_and_wrong_model_cannot_claim_accuracy(self):
        case={'evaluation_role':'held_out','outcome':'win','outcome_recorded_at':'2026-10-25T12:00:00Z',
            'prediction':{'outcome':'win','recorded_at':'2026-10-25T12:01:00Z','model_sha256':'a'*64}}
        self.assertIsNone(prediction_metrics([case])['winner_accuracy'])
        case['prediction']['recorded_at']='2026-10-25T11:59:00Z'
        self.assertEqual(prediction_metrics([case],model_sha256='b'*64)['excluded_held_out_cases'],1)

    def test_countdown_display_is_an_interval_not_an_exact_cast_timestamp(self):
        self.assertTrue(check_countdown(5,4.9))
        self.assertFalse(check_countdown(5,4))
        self.assertFalse(check_countdown(5,5.1))
        self.assertFalse(check_countdown(True,1))

    def test_supplied_reports_never_claim_predictive_accuracy(self):
        root=Path(__file__).resolve().parents[2]
        evidence=json.loads((root/'outputs/battle-reports/Battle-Replay-Evidence-2026-10-25.json').read_text(encoding='utf-8'))
        result=report(root/'outputs/hero-report',evidence)
        self.assertEqual(result['mechanics_checks']['checked_count'],10)
        self.assertEqual(result['mechanics_checks']['consistent_count'],10)
        self.assertIsNone(result['accuracy_percentage'])
        self.assertEqual(result['prediction_metrics']['winner_cases'],0)


if __name__=='__main__':unittest.main()
