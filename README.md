# Tiles Survive Guides

Independent bilingual reference guides for **Tiles Survive**, based on client configuration data and in-game verification.

Each PDF contains both languages in one file:

- English first
- Russian second

## Published guides

- [Collections Guide - EN/RU](docs/Tiles-Survive-Collections-Guide-EN-RU.pdf)
- [Hero Gear Upgrade Guide - EN/RU](docs/Tiles-Survive-Hero-Gear-Upgrade-Guide-EN-RU.pdf)

## Rebuild the PDFs

Install Python 3.10+ and ReportLab:

```bash
python -m pip install -r requirements.txt
python scripts/build_collection_guide.py
python scripts/build_hero_gear_guide.py
```

The scripts write the finished PDFs to `docs/`. They support common Windows, macOS, and Linux font locations and require a Unicode font capable of rendering Cyrillic.

## Accuracy and affiliation

The guides identify their client build and evidence limits. Game updates may change requirements, rewards, or unlock timing.

This is an unofficial community project and is not affiliated with or endorsed by the game publisher. Tiles Survive names and visual identity belong to their respective owners.
