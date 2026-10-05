import unittest
import json
from pathlib import Path
from audit_combat_effects import events, effect_summary


class CombatAuditTests(unittest.TestCase):
    def test_projectile_launch_does_not_become_impact_time(self):
        self.assertEqual(events({'Action': 'Projectile', 'HitActions': [
            {'Action': 'RaidEvent', 'StringParam0': 'zone', 'RaidEventType': 1}]}),
            [{'reference': 'zone', 'event_type': 1, 'context': 'projectile_hit'}])

    def test_damage_name_does_not_override_heal_type(self):
        row = effect_summary({'Id': 'damage_heal_text', 'Type': 1,
                              'EffectParam2': 300, 'EffectParam3': 0})
        self.assertEqual(row['type'], 1)
        self.assertNotIn('damage_coefficient', row)

    def test_all_roster_offense_indices_use_attack_not_display_parameters(self):
        path = Path(__file__).resolve().parents[2] / 'outputs/hero-report/TilesSurvive-Hero-Data.json'
        heroes = json.loads(path.read_text(encoding='utf-8'))
        low = min(h['max_level_attack'] for h in heroes)
        high = max(h['max_level_attack'] for h in heroes)
        for hero in heroes:
            self.assertIsNone(hero['best_non_basic_damage_coefficient'], hero['name'])
            expected = round((hero['max_level_attack'] - low) / (high - low) * 100, 2)
            self.assertEqual(hero['offense_index'], expected, hero['name'])


if __name__ == '__main__':
    unittest.main()
