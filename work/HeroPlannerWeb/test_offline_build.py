from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "outputs" / "Tiles-Survive-Hero-Planner-Offline.html"
DATA = ROOT / "outputs" / "hero-report" / "TilesSurvive-Hero-Data.json"


class OfflineBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = OUTPUT.read_text(encoding="utf-8")
        cls.heroes = json.loads(DATA.read_text(encoding="utf-8"))

    def test_all_hero_records_and_images_are_embedded(self) -> None:
        self.assertEqual(self.html.count('"asset_slug"'), len(self.heroes))
        expected_images = 2 + len(self.heroes) + sum(len(hero.get("skills", [])) for hero in self.heroes)
        self.assertEqual(self.html.count("data:image/png;base64,"), expected_images)

    def test_no_build_placeholders_or_network_dependencies_remain(self) -> None:
        self.assertNotIn("__EMBEDDED_HERO_JSON__", self.html)
        self.assertNotIn("__APP_CSS__", self.html)
        self.assertNotIn("__APP_JS__", self.html)
        self.assertIsNone(re.search(r"(?:src|href)=[\"']https?://", self.html))
        self.assertIsNone(re.search(r"\bfetch\s*\(", self.html))

    def test_portable_profile_controls_are_present(self) -> None:
        self.assertIn("Export profile", self.html)
        self.assertIn("Import profile", self.html)
        self.assertIn("localStorage.setItem", self.html)
        self.assertIn('serverOpenDate: "2026-09-02"', self.html)
        self.assertIn("FormationPriority.sanitizeProgress", self.html)
        self.assertIn('id="save-stars"', self.html)
        self.assertIn("Star-upgrade queue", self.html)

    def test_completed_squad_guide_and_release_selection_are_embedded(self) -> None:
        self.assertIn("Formation ready", self.html)
        self.assertIn("Resource priority", self.html)
        self.assertIn("Battle guide", self.html)
        self.assertIn("object-fit:contain", self.html)
        self.assertIn("releaseActive", self.html)
        self.assertIn("Click a hero card on the left to inspect", self.html)


if __name__ == "__main__":
    unittest.main()
