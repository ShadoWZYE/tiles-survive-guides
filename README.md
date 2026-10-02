# Tiles Survive Tools and Guides

Unofficial community tools, extracted hero reference data, and English/Russian guides for **Tiles Survive**.

## Ready-to-use downloads

- [Offline Hero Planner](outputs/Tiles-Survive-Hero-Planner-Offline.html) - one self-contained HTML file for Windows, macOS, and Linux. No installation or server is required.
- [Windows Hero Planner package](downloads/Tiles-Survive-Hero-Planner-Windows.rar) - packaged desktop edition.
- [Tiles Survive Helper](downloads/TilesSurviveHelper.exe) - Windows window-management companion.

## Hero optimizer

The Hero Planner supports:

- Owned-roster selection and portable profile import/export
- Balanced, Offense, Survival, and PvE squad scoring
- Five-position front-to-back formation guidance
- Modeled skill synergy and resource-priority explanations
- F2P, event-accessible, owned-only, and IAP-linked filters
- Hero stats, skill icons, decoded descriptions, and release/access evidence
- Persistent server-opening date and release timeline
- Resizable panes, click-drag roster scrolling, and responsive browser layout

Source locations:

- `work/HeroPlanner/` - .NET 8 WPF desktop application
- `work/HeroPlannerWeb/` - dependency-free browser source and offline bundler
- `outputs/hero-report/` - normalized hero data, ranking CSV, and methodology
- `outputs/hero-tool/images/` - hero portraits and skill icons used by the planners

### Build the desktop planner

```powershell
dotnet build work\HeroPlanner\HeroPlanner.csproj -c Release
```

### Rebuild the offline browser edition

```powershell
python work\HeroPlannerWeb\build_offline.py
python -m unittest work.HeroPlannerWeb.test_offline_build
```

## Windows companion and display tools

`work/TilesSurviveHelper/` contains the source for the helper that reattaches to the game window after launcher restarts. The `outputs/` directory also includes the F11 and true-borderless PowerShell launchers.

Build the helper with:

```powershell
dotnet publish work\TilesSurviveHelper\TilesSurviveHelper.csproj -c Release
```

Then run `work\TilesSurviveHelper\Install-RunningHelper.ps1` to copy the published build to `downloads/` and the current user's Desktop.

## Guides and reports

Current bilingual PDFs place English first and Russian second in the same file:

- [Collections Guide - EN/RU](docs/Tiles-Survive-Collections-Guide-EN-RU.pdf)
- [Hero Gear Upgrade Guide - EN/RU](docs/Tiles-Survive-Hero-Gear-Upgrade-Guide-EN-RU.pdf)

Additional earlier reports are under `docs/reports/`. New PDFs should continue using the combined English/Russian format.

- March Capacity report
- Troop Load report
- Reservoir Raid guides
- Stalwart Battlefield leaderboard explanation
- Metropolis alliance-attack guide
- Ghoulion Pursuit preliminary alliance analysis

Rebuild the current bilingual PDFs with:

```powershell
python -m pip install -r requirements.txt
python scripts\build_collection_guide.py
python scripts\build_hero_gear_guide.py
```

## Hero-data extraction

The scripts under `work/hero-extraction/` decode the relevant client configuration and build the normalized report consumed by both planners. Extracted temporary client tables are deliberately excluded from this public repository.

Tests that require those locally extracted tables skip with an explicit message in a clean public checkout. The checked-in normalized data and all planner artwork remain sufficient to build both planners.

## Privacy and safety

Raw packet captures, session material, certificates, local browser profiles, personal account coordinates, and temporary reverse-engineering output are intentionally excluded. The included capture launcher writes only to the ignored local `captures/` directory.

## Accuracy and affiliation

The planner uses transparent comparison heuristics; it is not a frame-by-frame combat simulator. Client configuration can describe future or inactive content and should not be treated as guaranteed live scheduling.

This is an unofficial community project and is not affiliated with or endorsed by the game publisher. Tiles Survive names, images, and visual identity belong to their respective owners.
