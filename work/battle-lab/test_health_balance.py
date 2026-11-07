import json,unittest
from pathlib import Path
from health_balance import health_ledger,reconcile,report
class HealthBalanceTests(unittest.TestCase):
    def test_hp_damage_healing_shield_overkill_and_net_loss_remain_distinct(self):
        r=health_ledger(100,[{'kind':'damage','amount':80},{'kind':'heal','amount':20},{'kind':'damage','amount':70,'shield_absorbed':10}])
        self.assertEqual(r['gross_damage'],150);self.assertEqual(r['net_hp_lost'],100);self.assertEqual(r['effective_healing'],20);self.assertEqual(r['shield_absorbed'],10);self.assertEqual(r['overkill'],20);self.assertEqual(r['balance_residual'],0)
        r=health_ledger(100,[{'kind':'damage','amount':60},{'kind':'heal','amount':80}]);self.assertEqual(r['overheal'],20);self.assertEqual(r['effective_healing'],60);self.assertEqual(r['net_hp_lost'],0)
    def test_invalid_events_fail_without_inventing_HP(self):
        for amount in [float('nan'),-1,True]:
            with self.assertRaises(ValueError):health_ledger(100,[{'kind':'damage','amount':amount}])
    def test_recorded_totals_reconcile_with_no_fitted_parameters_but_keep_reverse_residual(self):
        p=Path(__file__).resolve().parents[2]/'outputs/hero-report/Replay-Observation-2026-11-07.json';r=report(json.loads(p.read_text(encoding='utf-8')))
        self.assertEqual(r['fitted_parameters'],0);self.assertEqual(r['friendly_outgoing']['healing_adjusted_gap'],14290);self.assertTrue(r['friendly_outgoing']['within_display_precision']);self.assertEqual(r['enemy_outgoing']['healing_adjusted_gap'],491830);self.assertFalse(r['enemy_outgoing']['within_display_precision'])
if __name__=='__main__':unittest.main()
