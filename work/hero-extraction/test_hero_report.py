from __future__ import annotations

import unittest
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_hero_report import build
from decode_cfg import decode_table


SOURCE = Path(__file__).resolve().parent / "generated-v2"
requires_extracted_config = unittest.skipUnless(
    (SOURCE / "1824_survivor.cfg").exists(),
    "requires locally extracted client configuration under generated-v2",
)


class HeroExtractionTests(unittest.TestCase):
    @requires_extracted_config
    def test_cfg_geometry_and_roster(self) -> None:
        decoded = decode_table(SOURCE / "1824_survivor.cfg")
        self.assertEqual(81, decoded["row_count"])
        self.assertEqual(420, decoded["row_size"])
        heroes = build(SOURCE)
        self.assertEqual(28, len(heroes))

    @requires_extracted_config
    def test_late_client_records(self) -> None:
        heroes = {hero["asset_slug"]: hero for hero in build(SOURCE)}
        self.assertEqual(25300241, heroes["dave"]["hero_id"])
        self.assertEqual("2.5.500", heroes["dave"]["client_version"])
        self.assertEqual("Sea", heroes["dave"]["faction"])
        self.assertEqual((34, 36), (heroes["dave"]["release_week_min"], heroes["dave"]["release_week_max"]))

    @requires_extracted_config
    def test_undine_max_level_stats(self) -> None:
        heroes = {hero["asset_slug"]: hero for hero in build(SOURCE)}
        undine = heroes["undine"]
        self.assertEqual(150, undine["max_level"])
        self.assertEqual(24000.0, undine["max_level_attack"])
        self.assertEqual(4800.0, undine["max_level_defense"])
        self.assertEqual(1600000.0, undine["max_level_health"])

    @requires_extracted_config
    def test_verified_rarities_and_ascensions(self) -> None:
        heroes = {hero["asset_slug"]: hero for hero in build(SOURCE)}
        self.assertEqual("SSR", heroes["maddie"]["rarity"])
        self.assertEqual("SR", heroes["lucky"]["rarity"])
        self.assertEqual("R", heroes["tim"]["rarity"])
        ascended = {hero["asset_slug"] for hero in heroes.values() if hero["has_ascension"]}
        self.assertEqual({"lucky", "sarge", "ken", "freja", "travis", "eva"}, ascended)

    def test_all_portraits_are_native_card_size(self) -> None:
        images = Path(__file__).resolve().parents[2] / "outputs" / "hero-tool" / "images"
        roster = json.loads((images.parent.parent / 'hero-report' / 'TilesSurvive-Hero-Data.json').read_text(encoding='utf-8'))
        portraits = sorted(images / (hero['asset_slug'] + '.png') for hero in roster)
        self.assertEqual({h['asset_slug'] for h in roster}, {p.stem for p in portraits})
        for portrait in portraits:
            data = portrait.read_bytes()
            self.assertEqual(b"\x89PNG\r\n\x1a\n", data[:8])
            width = int.from_bytes(data[16:20], "big")
            height = int.from_bytes(data[20:24], "big")
            self.assertEqual((360, 492), (width, height), portrait.name)

    @requires_extracted_config
    def test_acquisition_evidence_groups(self) -> None:
        heroes = {hero["asset_slug"]: hero for hero in build(SOURCE)}
        counts = {}
        for hero in heroes.values():
            counts[hero["acquisition_class"]] = counts.get(hero["acquisition_class"], 0) + 1
        self.assertEqual({"f2p_confirmed": 14, "event_mixed": 13, "unknown": 1}, counts)
        self.assertEqual("f2p_confirmed", heroes["maddie"]["acquisition_class"])
        self.assertEqual("event_mixed", heroes["dave"]["acquisition_class"])
        self.assertEqual("unknown", heroes["lucky"]["acquisition_class"])

    @requires_extracted_config
    def test_localized_skill_intelligence_and_icons(self) -> None:
        heroes = {hero["asset_slug"]: hero for hero in build(SOURCE)}
        hydro_barrage = heroes["dave"]["skills"][1]
        self.assertEqual("Hydro Barrage", hydro_barrage["display_name"])
        self.assertIn("3 consecutive high-pressure water blasts", hydro_barrage["game_description"])
        self.assertEqual("sp_icon_survivor_skill_dave_2", hydro_barrage["icon_asset"])
        icons = Path(__file__).resolve().parents[2] / "outputs" / "hero-tool" / "images" / "skill-icons"
        self.assertTrue((icons / f'{hydro_barrage["icon_asset"]}.png').exists())


if __name__ == "__main__":
    unittest.main()
