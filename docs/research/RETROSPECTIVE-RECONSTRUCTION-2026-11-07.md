# Retrospective fight reconstruction — 7 November 2026

We can measure how well a model reproduces an already observed fight without requiring a repeat. This report does that. Reconstruction error is kept separate from independent future-fight accuracy.

The most complete recorded PvP case has five friendly hero rows, 32.79M displayed hero damage and 5.12M separate Behemoth damage. Candidate rank steps from the existing build snapshot plus the video's level/skill/gear/Signature observations reproduce the hero overview exactly: **6,562,465 power**. Exact rank sectors are still candidate individual inputs; matching their total is not independent proof of every sector. Baseline fixed features include the video's known bonuses, with missing context excluded.

## Damage-dealt reconstruction

| Model | Shared fitted parameters | Fitted WAPE | Worst hero error | Leave-one-owner-out WAPE |
|---|---:|---:|---:|---:|
| Current planner offense index + shared scale | 1 | 25.1% | 64.2% | 30.3% |
| ATK × full 30-second coefficient | 1 | 27.2% | 38.5% | 39.3% |
| ATK × observed-lifetime coefficient | 1 | 30.0% | 55.7% | 37.9% |
| Known ATK × observed survival time | 1 | 16.1% | 28.6% | 22.1% |
| ATK × survival time + shared exposure | 2 | 9.9% | 42.2% | 14.8% |
| Native base helper + fitted defence grid | 2 | 30.0% | 55.7% | 37.9% |
| Lifetime-only control | 1 | 9.9% | 42.2% | 12.1% |
| Coefficient + shared exposure term | 2 | 9.9% | 42.2% | 14.7% |
| Basic/other coefficients + exposure | 3 | 9.9% | 41.6% | 16.0% |

The additional **ATK × observed survival time** probe uses the same single shared fitted scale as the production-index probe, and no Raid skill coefficients. It gives **16.1% fitted WAPE**, **28.6% worst-owner error** and **22.1% internal leave-one-owner-out WAPE**, versus 25.1%, 64.2% and 30.3% for the production offense proxy. This is a better same-fight reconstruction, not a replacement general hero ranking: survival times come from the recorded outcome and are not predicted. Adding a second shared exposure term collapses back to the lifetime-only control; it does not identify troop DPS.

WAPE is the sum of absolute row errors divided by the sum of observed row damage. It is not the difference between team totals. One shared multiplier can make a total look right while individual heroes are very wrong; both mean and worst-row error are shown. Nonnegative least squares fits at most three shared coefficients. No separate multiplier is fitted for each hero.

The leave-one-owner-out column fits on four hero rows and reconstructs the fifth, repeating for all five. Defence-grid selection also excludes that fifth outcome. This is an internal same-fight stress test, not independent battle validation: the owners share a battle, missing context and observations.

The simple lifetime control fits 9.9% weighted error, but Rosie is still 42.2% off. Its per-owner reconstruction is:

| Hero | Observed damage | Fitted damage | Signed error |
|---|---:|---:|---:|
| Rosie | 2.990M | 4.253M | +42.2% |
| Freja | 3.630M | 3.883M | +7.0% |
| Becca | 7.720M | 7.951M | +3.0% |
| Maddie | 9.220M | 9.430M | +2.3% |
| Ray | 9.230M | 7.951M | -13.9% |

Adding skill/source terms does not improve the internal test: the lifetime control gives 12.1% leave-one-owner-out WAPE, compared with 14.7% for coefficient plus exposure and 16.0% for basic/other plus exposure. The richer fits put almost all output into the generic exposure term. **That is a warning that the current skill features are missing or misapplying important information, not evidence that soldiers supply nearly all damage.**

The native-helper defence grid chooses its zero-defence boundary and does not improve the coefficient model. This is not recovered enemy DEF. A shared defence adjustment alone does not explain these rows under the available inputs.

## Damage-taken reconstruction

All five friendly heroes fall in this report. Their reported incoming totals can be tested against known flat hero HP with a shared scale and shared offset:

| Model | Shared fitted parameters | Fitted WAPE | Worst hero error | Leave-one-owner-out WAPE |
|---|---:|---:|---:|---:|
| Known flat HP × shared scale | 1 | 13.8% | 24.5% | 17.2% |
| Known flat HP × scale + shared incoming offset | 2 | 1.2% | 2.4% | 1.9% |

The two-parameter fit is approximately **reported damage taken = 1.3416 × known flat HP + 10.5967M**.

| Hero | Observed damage taken | Reconstructed | Signed error |
|---|---:|---:|---:|
| Rosie | 13.470M | 13.331M | -1.0% |
| Freja | 13.500M | 13.819M | +2.4% |
| Becca | 15.230M | 15.092M | -0.9% |
| Maddie | 15.230M | 15.328M | +0.6% |
| Ray | 14.250M | 14.110M | -1.0% |

This is a useful small-margin reconstruction: 1.2% fitted weighted error, 2.4% worst-row error and 1.9% internal leave-one-owner-out weighted error. It supports testing a shared account/army/context budget rather than attributing all durability to intrinsic hero HP. **The offset is not identified troop HP, Research or Behemoth HP.** Damage taken can include other accounting, shielding, healing and overkill effects; no per-hero healing allocation has been invented.

## Existing saved context and timing uncertainty

A second scenario uses the saved Research/Behemoth configuration. The video agrees with its Behemoth levels and Signature, but exact historical Research and star steps are not independently established. This scenario is kept separate, rather than silently declaring the snapshot to be the fight state.

With it, the current offense-index fit is 26.7% WAPE; the shared incoming-budget fit remains about 1.2%. Simply adding this candidate context does not close the outgoing model. The full JSON preserves all scenario metrics and inputs.

For the lifetime control, choosing the broad earliest and latest observed presentation windows produces 10.3% and 11.5% fitted WAPE, versus 9.9% at the midpoint. Those are scenario results, not confidence bounds, and the best window is not selected separately for each hero.

## Important native-code finding: report replay is not an independent fight calculation

The [replay-authority audit](../../outputs/hero-report/Replay-Authority-Audit.json) fingerprints 13 selected static methods in the verified client build:

- `HeroPropertyComponent.Initialize` selects `SupplyBattleReportProperty` for its Type-12 branch. That path initializes hero base ATK to **0** and HP/HP-max to **100**. Replay soldiers are also initialized with zero ATK and 100 HP/HP-max. These are presentation setup values, not the report heroes' actual battle stats.
- `RaidBattleReplayPlayMode.OnStart` loads `InputBattleReportData.ReportData.rounds_info`. Its round handling has explicit death and healing scheduling calls.
- `RaidFightStatisticsMgr.GetAllStatisticsData` has a Type-12 path which imports supplied hero/titan/pet statistics from `InputBattleReportData` instead of returning the normal accumulated counters.

Thus matching report/replay totals can mean reading the same supplied records. Animation-derived survival and cooldown behavior must not be treated as independent evidence of the original battle equations. The lifetime fits above remain descriptive reconstructions of the available recording, not recovered original combat timing. The audit establishes selected static paths; live ILFix overrides and exact live dispatch were not dynamically inspected. It does not prove which mathematical formulas the original server shares with other client modes.

This does **not** make reconstruction pointless. It pinpoints the next bridge to resolve: the original report-round/field skill calculation, not an assumption that the visible Raid animations generated the report. The Type-11100 field/Lite bridge is still untraced.

## Field-lab slot correction

A separate concrete bug was found while tracing the field links: the fiend export used values from `survivor.SkillConfig` as skill-slot indices. Those are not the canonical slot numbers; an entry such as 86 could make a recorded unlocked fourth skill appear capped at zero. The export now uses `survivor_skill_type.SkillNo`, retains the old value only as explicitly raw metadata, and has a regression for Freja's unlocked/locked fourth skill. This fixes input gating; it does not establish the field effect's damage formula or execution.

## Implications for the optimiser

The current offense index does not reproduce this fight closely enough to claim accurate damage prediction. The incoming-budget fit is encouraging, but fitting that offset does not justify adding invented stats to My builds. Balanced scoring also includes utility and survival; it cannot be fitted to outgoing damage columns alone. Production scoring weights and saved builds are unchanged by this experiment.

The next useful refinements are to trace the original round/field calculation and identify the shared account/army contribution, then rerun these same cases. Existing incomplete fights can supply further constraints, but their missing builds must be represented explicitly rather than filled with maximum reference heroes. New recordings or exact repeat fights are not prerequisites for measuring retrospective fit.

## Reproduce

1. `python work/battle-lab/audit_replay_authority.py` requires the private hash-verified native artifacts; its normalized output is committed.
2. `node work/battle-lab/reconstruct-damage.cjs`
3. `python work/battle-lab/render_reconstruction_report.py`
4. `node --test work/battle-lab/test_reconstruction.cjs`

[Complete reconstruction results and source hashes](../../outputs/hero-report/Retrospective-Damage-Reconstruction.json). [Frozen candidate inputs](../../outputs/hero-report/Replay-Reconstruction-Inputs-2026-11-07.json). Raw profiles, recordings and disassembly remain private. All fitted values are experimental outputs and never become saved build bonuses.
