# Hero configuration audit — 5 October 2026

Verified the installed Windows client `2.6.200.276` and its current downloaded configuration pack, not just the older packaged defaults. All 20 roster/progression/draft source tables matched the game's `BinVersionList_Realtime.json` content hashes. The source pack and manifest SHA-256 hashes are recorded in `outputs/hero-report/Hero-Config-Audit.json`; each table SHA-256 remains in the upgrade dataset.

## Findings and corrections

- All 28 previously supported heroes were compared field by field. Their exported rank/level stats, skill parameters, skill power and costs, gear data and draft inputs were unchanged. Their roster stat/skill records were also unchanged.
- Ray's configured max-level ATK / DEF / HP remain **24,000 / 4,800 / 1,600,000**. His basic-attack DamageParam remains `[1.14769, 0.01231]`; Boomstick `[0.59815, 0.04985]`; Falcon Dive `[0.02215, 0.00185]`. No Ray-specific numerical nerf appears between the previous exported records and the current local records.
- Lava was missing from the roster. Added his current configuration, progression, portrait and skill icons. Comparative ranks now include all 29 base heroes.
- Native and browser headers used an outdated roster version. They now derive the displayed build and roster count from the embedded dataset.
- Cache updates can move table names to a different directory slot and mark entries deleted. Fixed the reader to honor those slots. The roster exporter no longer relies on old table ordinal numbers. The refresh now refuses table/cache-manifest mismatches.

## What the numbers mean

Resource priority's **power** mode compares configured BattlePower contributions for saved builds. It is not measured combat damage: a combat nerf need not change BattlePower. The squad optimiser's offense/composite indices remain transparent max-level configuration heuristics, not a simulation of the user's current stars, targeting or the live meta. Direct-output mode remains experimental: affine DamageParam growth and PVE cooldowns are assumptions, not verified full squad-runtime formulas. Ray's eagle, healing, terrain and multi-hit behavior are not simulated. No fabricated penalty was added to force an expected ordering.

The [official v2.4.200 notes](https://tilesurvivegame.com/en/blog/800) describe Falcon Dive converting part of Rolex's damage into front-row healing and changes to Boomstick visuals. Those notes do not establish a numerical nerf in the current inspected build. Server-only overrides, later uninstalled clients, and runtime behavior outside the exported configuration are not certified by this audit.

Validation: offline extraction tests, all-hero roster/progression identity and max-stat agreement, native/browser calculation parity and isolated native UI regression. No game DLL was executed or injected and no game request was sent.
