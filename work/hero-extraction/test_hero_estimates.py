import copy
import json
from pathlib import Path
import unittest
from build_estimate_model import build


class ReferenceEstimateTests(unittest.TestCase):
    def test_reproducible_and_same_snapshot_required(self):
        folder = Path(__file__).resolve().parents[2] / 'outputs/hero-report'
        read = lambda name: json.loads((folder / name).read_text(encoding='utf-8'))
        upgrades, audit = read('TilesSurvive-Upgrade-Data.json'), read('Hero-Combat-Audit.json')
        roster = {h['asset_slug']: h for h in read('TilesSurvive-Hero-Data.json')}
        self.assertEqual(build(upgrades, audit, roster), read('Hero-Estimate-Model.json'))
        stale = copy.deepcopy(audit); stale['provenance']['config_pack_sha256'] = 'stale'
        with self.assertRaisesRegex(ValueError, 'same snapshot'):
            build(upgrades, stale, roster)

    def test_known_heal_is_not_given_damage_pressure_based_on_name(self):
        folder = Path(__file__).resolve().parents[2] / 'outputs/hero-report'
        read = lambda name: json.loads((folder / name).read_text(encoding='utf-8'))
        upgrades, audit = read('TilesSurvive-Upgrade-Data.json'), read('Hero-Combat-Audit.json')
        roster = {h['asset_slug']: h for h in read('TilesSurvive-Hero-Data.json')}
        skill = audit['heroes']['rosie']['skills'][0]
        skill['referenced_effects'] = [{'id': 'damage_heal_effect', 'type': 1, 'base_param2': 9000, 'base_param3': 0, 'custom_formula': False}]
        skill['missing_assets'] = []; skill['unresolved_event_references'] = []
        rows = build(upgrades, audit, roster)['heroes']['rosie']['skills'][0]['levels']
        self.assertTrue(all(row['damage'] == 0 for row in rows))


if __name__ == '__main__':
    unittest.main()
