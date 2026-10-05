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
- Fair all-hero Equal builds comparison by default; Flat max stats and opt-in My builds modes. Resource priorities use actual owned builds; details stay collapsed ([model](docs/research/HERO-REFERENCE-ESTIMATES.md))
- Five-position front-to-back formation guidance
- Modeled skill synergy (separate from build-specific upgrade comparisons)
- Exact rank-step, level, skill and optional universal-gear recording
- Native rank-step slider with game star art and partial progress; every valid edit autosaves
- Native Targeted Draft target recommendations from the eligible pool and remaining fragment cost
- Next-upgrade stat/contribution returns grouped by actual resource, with balances and affordability filtering
- Selectable native priority cards, resource-class filters, and top-three percentage gains (hero fragments compared together)
- One-click local recording of completed upgrades, with balance updates and last-action Undo
- Optional legacy whole-star / personal-target notes, preserved but not converted into exact rank progress
- F2P, event-accessible, owned-only, and IAP-linked filters
- Hero stats, skill icons, decoded descriptions, and release/access evidence
- Persistent server-opening date and release timeline
- Resizable panes, click-drag roster scrolling, and responsive browser layout

Source locations:

- `work/HeroPlanner/` - .NET 8 WPF desktop application
- `work/HeroPlannerWeb/` - dependency-free browser source and offline bundler
- `outputs/hero-report/` - normalized hero data, ranking CSV, and methodology
- `outputs/hero-tool/images/` - hero portraits and skill icons used by the planners

### Data-driven upgrade comparisons

Investment recommendations no longer impose a role-based hero order. Select five heroes, record their builds under **My roster → My build**, and choose a return metric. The calculator recomputes each adjacent rank, level, skill or recorded gear upgrade from the installed client tables. All five exact ranks/levels are required; blank skill levels remain unknown, not maximum. Gear can be explicitly absent or unknown/excluded. Invalid caps and duplicate gear slots are rejected.

**Data provenance:** roster and progression were checked on **5 October 2026** against the installed **2.6.200.276** client's downloaded configuration cache, with all 20 source tables matching `BinVersionList_Realtime.json`. The refreshed dataset covers **29 base heroes**, including Lava, and 18 universal gear types. All 28 previously included heroes had identical exported progression, stats and skills, including Ray; no unverified nerf multiplier is applied. Audit evidence is in `outputs/hero-report/Hero-Config-Audit.json`, with table hashes in `TilesSurvive-Upgrade-Data.json`. This verifies local configuration, not unobserved server overrides or a full battle simulation. Raw tables remain private.

**How returns are calculated:** each candidate changes one recorded build while holding the other four constant. Gain is the percentage change in the selected formation total; efficiency is that gain per 100 units of the exact listed resource. Rankings compare only the same resource ID. Hero-specific shards are not treated as a shared currency; mixed/unlisted costs have no efficiency ranking. Configured power contributions and ATK/DEF/HP totals are not win-rate, survival or live-damage predictions. Rank unlocks raise caps but do not automatically grant skill upgrades. Skill costs use the configured `SlgItemReq` field; verify the applicable expense in-game.

**Offline combat audit:** native inspection invalidated the experimental display-`DamageParam` damage model. Direct-output mode has been withdrawn; old saved selections migrate to configured power without changing builds or balances. Offense indices now use verified ATK only, not guessed skill coefficients. Power/stat modes measure only their named contributions, not combat strength. See [the audit](docs/research/HERO-COMBAT-AUDIT-2026-10-05.md) for verified parameter arithmetic, Ray's projectile/damage-zone chain, all-29-hero dependency coverage and unresolved runtime limits.

Costs use destination rank/skill rows, cumulative hero-XP differences, and current gear-row next-level XP. XP assumes zero progress toward the next level. Building gates must be checked in-game; affordability means enough recorded materials, not a guarantee the upgrade is unlocked. Ascension, profession/exclusive gear, refinement and shard conversion are excluded. Exact rank/step labels are client identifiers, not an unverified conversion to displayed whole stars. Legacy whole-star notes remain saved separately.

The Windows app calculates upgrades **natively**. Each hero card has a small **edit button below its owned checkbox**. It opens an in-app overlay with separate rank/step dropdowns, current skill caps and the game's skill icons. Gear and comparison details are collapsed initially. **Every valid edit saves immediately** in the Windows profile (`hero_builds` / `upgrade_settings`), including metric and balance changes; no Save/Cancel action is needed. Invalid entries retain the last valid data and display a warning. Close/Escape simply dismiss the overlay without undoing saved edits. Profile updates use an atomic temporary-file replacement. Opening the editor never changes ownership or the selected squad. In **My roster**, clicking a card toggles owned/unowned again; in **Squad Builder**, clicking a card selects/removes it from the formation. The checkbox changes ownership in either view. Native results and browser results have regression-tested numerical parity. The Windows package no longer launches or embeds a browser calculator. No game process hooking, online requests or automatic spending is involved.

### Build the desktop planner

```powershell
dotnet build work\HeroPlanner\HeroPlanner.csproj -c Release
```

### Rebuild the offline browser edition

```powershell
python work\HeroPlannerWeb\build_offline.py
python -m unittest work.HeroPlannerWeb.test_offline_build
dotnet build work\HeroPlanner.Tests
node --test work\HeroPlannerWeb\test_formation_priority.cjs work\HeroPlannerWeb\test_upgrade_model.cjs
```

Windows-only UI regression (isolated temporary profile): `dotnet run --project work/HeroPlanner.UiTests`. Build the native console tests, then run `node --test work/HeroPlannerWeb/test_native_upgrade_parity.cjs` for 60 cross-edition cases spanning rank steps, metrics, unknown skill levels and gear. Browser interaction regression: install Playwright, then run `node work/HeroPlannerWeb/test_browser_smoke.cjs`; `PLANNER_PLAYWRIGHT` can point to its module and `PLANNER_BROWSER` can select an installed Chromium executable. Tests cover cost-driven order changes, currencies, unknown builds, skill caps, ownership, native overlay and immediate autosave, invalid-save protection, profile persistence and mobile layout. Legacy role-helper parity tests are retained for regression, but that policy no longer drives displayed investment recommendations.

### Local working directory

The canonical working repository is **`C:\Users\Shadow\Desktop\Tiles Survival Tools`**, consolidated with the latest published files. Private extracts and Desktop-only scratch tools remain local and excluded from publication. The previous Desktop history is retained on local branch `desktop-before-consolidation-20261005`; overwritten older public files were backed up in `C:\Users\Shadow\Desktop\Tiles-Tools-Merge-Backup-20261005`. The earlier Downloads checkout is left intact as a fallback, not an active working directory. Do not switch future development back to Downloads.

After publishing the native executable, `work/HeroPlanner/install_desktop.ps1` creates a real **Tiles Survive Hero Planner** Desktop shortcut targeting the current published build in this repository. It gracefully closes the planner, preserves an old standalone Desktop executable under `Tiles-Tools-Launcher-Backup`, verifies the shortcut target and relaunches the app. Existing saved profiles are unaffected.

To refresh progression after privately extracting the selected config tables:

```powershell
python work\hero-extraction\build_upgrade_data.py PRIVATE_EXTRACT_DIRECTORY --client-build YOUR_CLIENT_BUILD --targeted-source PRIVATE_DRAFT_TABLE_DIRECTORY
python work\HeroPlannerWeb\build_offline.py
```

The exporter uses the existing CFG/language decoders, refuses missing/ambiguous tables and stores normalized fields only. For a current-cache refresh, use `work/hero-extraction/refresh_hero_data.py` with explicit `--pack`, `--manifest`, `--language`, `--client-build`, `--audited-date`, `--private-output` (fresh directory) and `--output outputs/hero-report`. This refuses stale manifest hashes and audits changes for every hero before publishing normalized output. Recheck model assumptions when refreshing to another client version.

### Native Targeted Draft guidance

Select the in-game pool under a hero's **Upgrade comparison → Targeted Draft**. This setting saves automatically. The selectable targets come from `survival_card_pool → survival_up_card_pool → survival_up_drop_contrast → itemlist → survivor`; they are not inferred from server age. Draft Voucher item ID is `208308`. The client UI uses `UpHero` for selectable targets, not the decorative `HeroFullPic` list.

For heroes in the selected formation, the planner sums destination fragment costs through the next completed six-step rank (or next configured rank above that range), subtracts recorded hero-specific fragments, and compares the selected stat/power gain per missing fragment. Already affordable milestones say to use existing fragments first. Unknown balances produce a **provisional** target; missing build data blocks the recommendation. This is not an expected return per voucher or a replacement/unlock recommendation for heroes outside the formation. Skill caps do not grant free skill levels; book costs and utility effects remain separate. Building gates must be checked in-game.

Displayed selected-target probabilities are retained as category rates, not interpreted as guaranteed fragments. Duplicate conversion, pity progress, reward-quantity distribution, live pool eligibility overrides and full battle outcomes are not simulated. The native rank slider stores exact configured rank/step identifiers. Its five-slot preview matches the supplied base-hero screenshots: ranks 1–5 fill purple stars, and ranks 6–10 replace them with gold stars; step 6 completes a star. Partial gold appears over the existing purple slot, rather than erasing the previous tier. Full/empty sprites are extracted client art; partial sectors are rendered by the planner and represent steps, not proportional fragment cost. Ascension star colours beyond that range are not guessed. Legacy whole-star notes are preserved separately and never silently converted.

```powershell
dotnet run --project work\HeroPlanner.Tests -- unused --targeted outputs\hero-report\TilesSurvive-Upgrade-Data.json
```

### Native resource priority actions

The formation panel separates resources into selectable upgrade cards. Filter by **Rank fragments**, **Skill materials**, **Hero XP**, **Gear XP** or **Mixed / other**. All hero-fragment upgrades share one list, with the top three across heroes by formation **percentage increase**. Other resources show their top three per individual material. Cost efficiency per 100 units is displayed separately. Actual hero-specific fragment costs and balances remain intact; recording does not silently convert or deduct universal fragments. Mixed-cost combinations stay separate. Other, locked and unmodeled upgrades remain available in collapsed sections.

Targeted Draft uses a concise suggested target followed by individual hero cards with milestone gain, fragment efficiency and remaining cost. Skill caps, pool rates and model limitations are collapsed separately. Text remains selectable. The native build editor uses the same structured resource comparison, without recording buttons while editing.

After completing an upgrade in the game, use **Record completed** on its card. This only advances the locally saved hero rank step, level, skill or gear level. Known resource balances are deducted; unknown balances remain unknown. Insufficient known balances and invalid rank/level gates block recording. Building gates still require an in-game check. The action re-evaluates its destination and rejects stale cards; a save failure restores the in-memory build and inventory. No request is sent to the game and no vouchers are spent.

**Undo last recorded upgrade** restores the previous local build and balances for the last action in this app session. It refuses to overwrite a later build or inventory edit. All priority text and expanded details support text selection/copying. Native regression tests cover the top-three ordering, filters, all four upgrade kinds, immediate disk persistence, stale clicks, insufficient/unknown balances, rollback on a locked profile file, and Undo protection.

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
