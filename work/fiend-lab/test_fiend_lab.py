import copy
import json
import unittest
from pathlib import Path
from simulate_fiend import cooldown_opportunities, friendly_skills, simulate, casualty_expectation
from raid_damage_kernel import base_damage
from check_report_inputs import check

ROOT = Path(__file__).resolve().parents[2]


class FiendLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'outputs/fiend-lab/Fiend-Encounter-Data.json').read_text(encoding='utf-8'))
        cls.progression = json.loads((ROOT / 'outputs/hero-report/TilesSurvive-Upgrade-Data.json').read_text(encoding='utf-8'))

    def test_tusker_level_10_matches_independent_report_inputs(self):
        encounter = self.data['encounters']['gve_boss_new_period_10']
        self.assertEqual(len(encounter['formations']), 5)
        self.assertEqual(encounter['total_configured_troops'], 312070)
        for f in encounter['formations']:
            self.assertEqual(f['troop_count'], 62414)
            self.assertEqual(f['display_power_reference'], 115194150)
            self.assertEqual(f['configured_hero_power_sum'], 6179105)
            self.assertEqual(len(f['units']), 5)
            self.assertEqual([u['level'] for u in f['units']], [150] * 5)

    def test_all_encounters_resolve_and_keep_formation_troops_separate_from_heroes(self):
        self.assertEqual(len(self.data['encounters']), 10)
        for encounter in self.data['encounters'].values():
            self.assertEqual(encounter['total_configured_troops'], sum(f['troop_count'] for f in encounter['formations']))
            for f in encounter['formations']:
                self.assertEqual(f['configured_hero_power_sum'], sum(u['configured_power'] for u in f['units']))
                for unit in f['units']:
                    for skill in unit['skills']:
                        self.assertIn(skill['lite_skill'], self.data['lite_skills'])

    def test_raw_cooldowns_use_half_open_boundary_and_explicit_death_boundary(self):
        catalog = {'a': {'id': 'a', 'initial_cd_raw': 100, 'common_cd_raw': 100,
            'condition': '', 'round_limit': 0, 'total_limit': 0, 'round_type': 0,
            'prepare_round': 0, 'effects': []}}
        selected = [{'id': 'attack', 'lite_skill': 'a', 'level': 1}]
        self.assertEqual([e['at_raw_tick'] for e in cooldown_opportunities(selected, catalog, 300)['events']], [100, 200])
        self.assertEqual([e['at_raw_tick'] for e in cooldown_opportunities(selected, catalog, 500, 200)['events']], [100])
        self.assertEqual(cooldown_opportunities([{**selected[0], 'level': 0}], catalog, 300)['events'], [])
        catalog['a']['common_cd_raw'] = 0
        self.assertEqual(len(cooldown_opportunities(selected, catalog, 300)['excluded']), 1)

    def test_missing_and_rank_locked_skills_have_no_activity_and_saved_data_is_untouched(self):
        saved = {'Skills': {'survivor_freja_skill_3': 3}}
        snapshot = copy.deepcopy(saved)
        selected = friendly_skills('freja', saved, self.data['heroes'], self.progression)
        self.assertTrue(all(s['level'] == 0 for s in selected))
        self.assertEqual(saved, snapshot)

    def test_actual_level_10_enemy_opportunities_do_not_claim_outcomes(self):
        result = simulate(self.data, 'gve_boss_new_period_10', 500)
        self.assertEqual(len(result['enemy']), 5)
        self.assertTrue(all(len(u['events']) == 4 for u in result['enemy']))
        self.assertIsNone(result['winner'])
        self.assertIsNone(result['damage_prediction'])
        self.assertIsNone(result['time_in_seconds'])

    def test_invalid_horizons_fail_before_scheduling(self):
        for value in [-1, 100001, float('inf'), True, 3.5]:
            with self.assertRaises(ValueError):
                cooldown_opportunities([], {}, value)
        for value in [float('nan'), float('inf'), True, -1]:
            with self.assertRaises(ValueError):
                cooldown_opportunities([], {}, 100, value)

    def test_gve_casualty_candidate_matches_visible_60000_troop_report(self):
        rule = self.data['casualty_rule_candidates']['battle_gve_rally']
        self.assertEqual(casualty_expectation(60000, rule), {
            'hospital_unrounded': 180, 'minor_wounded_unrounded': 59820,
            'permanent_unrounded': 0})
        # Fractional expectations are not silently advertised as an observed integer rule.
        self.assertEqual(casualty_expectation(1, rule)['hospital_unrounded'], .003)

    def test_report_checks_detect_wrong_encounter_inputs_without_claiming_accuracy(self):
        observation = {'visible_first_round': {'enemy_troop_count': 62413, 'enemy_hero_power': 6179105},
                       'source': {}, 'target_display': 'Lv. 10 Tusker', 'limitations': []}
        result = check(self.data, observation)
        self.assertTrue(all(not r['troops']['match'] for r in result['checks']))
        self.assertIsNone(result['accuracy_percentage'])
        self.assertEqual(result['winner_prediction_cases'], 0)

    def test_static_raid_helper_translation_and_penetration_bounds(self):
        self.assertAlmostEqual(base_damage(100, 20, 2), 400 / 3)
        self.assertEqual(base_damage(100, 20, 2, percent_penetration=1), 200)
        self.assertEqual(base_damage(100, 20, 2, flat_penetration=200), 200)
        self.assertEqual(base_damage(100, 0, 2, flat_damage=3, property_source=4,
                         custom_formula=5, external_additive=6), 218)
        with self.assertRaises(ValueError):
            base_damage(0, 20, 2)


if __name__ == '__main__':
    unittest.main()
