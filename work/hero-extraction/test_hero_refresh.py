import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from refresh_hero_data import verified_tables
from extract_config_pack import read_entries

class RefreshTests(unittest.TestCase):
    def fixture(self):
        slots = 4096; block = 270; payload = b'\x00CFGsynthetic'
        data = bytearray(block * 4096 + len(payload))
        struct.pack_into('<4sIII', data, 0, b'\x00SOS', 4096, slots, 2)
        struct.pack_into('<III', data, 16, 332, block, len(payload))
        struct.pack_into('<III', data, 28, 0xffffffff, 0, 0)
        pos = 16 + slots * 12 + 332 * 256
        data[pos] = 8; data[pos+1:pos+9] = b'survivor'
        data[block * 4096:] = payload
        return data, payload

    def test_updated_slot_and_deleted_entry(self):
        data, payload = self.fixture()
        entries = read_entries(data)
        self.assertEqual(['survivor'], [e.name for e in entries])
        result = verified_tables(data, {'survivor': hashlib.md5(payload).hexdigest()}, {'survivor'})
        self.assertEqual(payload, result['survivor'][1])

    def test_stale_or_missing_manifest_rejected(self):
        data, _ = self.fixture()
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            verified_tables(data, {'survivor': '0'*32}, {'survivor'})
        with self.assertRaisesRegex(ValueError, 'Missing'):
            verified_tables(data, {}, {'not_present'})

    def test_public_roster_and_progression_stay_joined_by_id(self):
        root = Path(__file__).resolve().parents[2] / 'outputs' / 'hero-report'
        roster = json.loads((root / 'TilesSurvive-Hero-Data.json').read_text(encoding='utf-8'))
        upgrades = json.loads((root / 'TilesSurvive-Upgrade-Data.json').read_text(encoding='utf-8'))
        self.assertEqual({h['asset_slug'] for h in roster}, set(upgrades['heroes']))
        for hero in roster:
            progression = upgrades['heroes'][hero['asset_slug']]
            self.assertEqual(hero['hero_id'], progression['id'])
            level = max(progression['levels'], key=lambda x:x['level'])
            self.assertEqual([hero['max_level_attack'],hero['max_level_defense'],hero['max_level_health']],level['stats'])
            self.assertEqual(hero['max_level_battle_power'],level['power'])
            self.assertEqual({s['internal_name'] for s in hero['skills']},{s['id'] for s in progression['skills']})

if __name__ == '__main__':
    unittest.main()
