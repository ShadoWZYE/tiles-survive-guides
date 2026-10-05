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
- Modeled skill synergy and formation-specific investment explanations (separate from squad scoring)
- Optional current-star / personal-target fields and a saved star-upgrade queue
- F2P, event-accessible, owned-only, and IAP-linked filters
- Hero stats, skill icons, decoded descriptions, and release/access evidence
- Persistent server-opening date and release timeline
- Resizable panes, click-drag roster scrolling, and responsive browser layout

Source locations:

- `work/HeroPlanner/` - .NET 8 WPF desktop application
- `work/HeroPlannerWeb/` - dependency-free browser source and offline bundler
- `outputs/hero-report/` - normalized hero data, ranking CSV, and methodology
- `outputs/hero-tool/images/` - hero portraits and skill icons used by the planners

Investment guidance is a transparent role-based policy, not an upgrade-return simulator. Balanced and PvE use primary damage core, frontline anchor, secondary damage core, then sustain/utility; Survival moves the anchor and sustain first; Offense develops both damage candidates first. If your frontline dies early, fix that before following the default damage order. Damage candidates use the extracted offense index among non-melee heroes, keeping midline healers in the sustain layer where possible. Ties prefer ranged heroes, then stable IDs, not a claimed combat advantage. Enemy-wide DEF/ATK reduction is recognized alongside the existing team-effect tags.

For example, Rosie / Layla / Becca / Ray / Maddie defaults to **Becca → Rosie → Ray → Layla → Maddie** in Balanced mode. This is a starting policy, not proof that Becca has the highest live DPS or the cheapest next upgrade.

In **My roster**, select a hero and optionally save current whole stars and your chosen target. Leave either blank when unknown. The star queue follows the formation's investment order and skips heroes already at their chosen target; it does not remove them from gear/skill priorities. No star-to-power multiplier, skill-unlock breakpoint, sub-star progress, ascension conversion, shard-cost or gear simulation is assumed. Old profiles still load with unknown star progress. Star fields are local to each edition's existing profile format; the formats are not interchangeable.

### Build the desktop planner

```powershell
dotnet build work\HeroPlanner\HeroPlanner.csproj -c Release
```

### Rebuild the offline browser edition

```powershell
python work\HeroPlannerWeb\build_offline.py
python -m unittest work.HeroPlannerWeb.test_offline_build
dotnet build work\HeroPlanner.Tests
node --test work\HeroPlannerWeb\test_formation_priority.cjs
```

Windows-only UI regression (uses an isolated temporary profile): `dotnet run --project work/HeroPlanner.UiTests`. Optional browser interaction regression: install Playwright, then run `node work/HeroPlannerWeb/test_browser_smoke.cjs`; `PLANNER_PLAYWRIGHT` can point to its module and `PLANNER_BROWSER` can select an installed Chromium executable. Both test ownership preservation, star persistence and goal-dependent priorities.

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
- [VeD Reservoir Raid battle plan - EN/RU](docs/reports/Tiles-Survive-Reservoir-Raid-VeD-Battle-Plan-EN-RU.pdf): named assignments for 30 starters and 8 confirmed substitutes, R4 calls, rotations, and the Blockbuster entry contingency. [Copy-paste alliance messages](docs/reports/Tiles-Survive-Reservoir-Raid-VeD-Battle-Plan-EN-RU.txt). Rebuild with `python work/ReservoirRaid/build_battle_plan.py` (requires ReportLab).

Additional earlier reports are under `docs/reports/`. New PDFs should continue using the combined English/Russian format.

Standalone Reservoir Raid quick-reference images: [English PNG](outputs/reservoir-raid/VeD-Reservoir-Raid-Quick-Reference-EN.png) and [Russian PNG](outputs/reservoir-raid/VeD-Reservoir-Raid-Quick-Reference-RU.png). Rebuild with `python work/ReservoirRaid/build_quick_reference.py` (requires Pillow); this does not modify the PDF.

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

For reproducible asset inspection, native-file auditing, and the current Ghoulion Gather Point findings, see [Client inspection tools](docs/research/CLIENT-EXTRACTION-TOOLS.md). It separates working asset extraction from the unresolved native metadata decoding step and includes tested commands and cache-pack pitfalls.

## Privacy and safety

Raw packet captures, session material, certificates, local browser profiles, personal account coordinates, and temporary reverse-engineering output are intentionally excluded. The included capture launcher writes only to the ignored local `captures/` directory.

## Accuracy and affiliation

The planner uses transparent comparison heuristics; it is not a frame-by-frame combat simulator. Client configuration can describe future or inactive content and should not be treated as guaranteed live scheduling.

This is an unofficial community project and is not affiliated with or endorsed by the game publisher. Tiles Survive names, images, and visual identity belong to their respective owners.
