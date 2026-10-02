from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DATA_PATH = ROOT / "outputs" / "hero-report" / "TilesSurvive-Hero-Data.json"
IMAGE_ROOT = ROOT / "outputs" / "hero-tool" / "images"
ICON_PATH = ROOT / "work" / "HeroPlanner" / "Assets" / "app-icon.png"
OUTPUT_PATH = ROOT / "outputs" / "Tiles-Survive-Hero-Planner-Offline.html"


def png_data(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def main() -> None:
    heroes = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    for hero in heroes:
        portrait = IMAGE_ROOT / f"{hero['asset_slug']}.png"
        hero["portrait_data"] = "data:image/png;base64," + png_data(portrait)
        for skill in hero.get("skills", []):
            icon_name = skill.get("icon_asset")
            icon = IMAGE_ROOT / "skill-icons" / f"{icon_name}.png"
            skill["icon_data"] = "data:image/png;base64," + png_data(icon) if icon_name and icon.exists() else ""

    html = (HERE / "index.template.html").read_text(encoding="utf-8")
    html = html.replace("__APP_CSS__", (HERE / "app.css").read_text(encoding="utf-8"))
    html = html.replace("__APP_JS__", (HERE / "app.js").read_text(encoding="utf-8"))
    html = html.replace("__APP_ICON__", png_data(ICON_PATH))
    html = html.replace("__EMBEDDED_HERO_JSON__", json.dumps(heroes, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Built {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1024 / 1024:.1f} MiB)")


if __name__ == "__main__":
    main()
