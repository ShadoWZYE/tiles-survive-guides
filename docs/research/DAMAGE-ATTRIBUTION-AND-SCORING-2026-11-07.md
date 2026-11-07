# Damage attribution, measurement and model 16

**Follow-up:** [retrospective reconstruction](RETROSPECTIVE-RECONSTRUCTION-2026-11-07.md) adds measured fit errors and identifies a report-driven replay path. Generic Raid counter rules below do not establish the original server report's mechanism accounting.

## A closed gap: gear level milestone bonuses

The earlier 169,260 gear-power discrepancy was an exporter omission. `survivor_equipment_level_npp` has both `BenefitSlg` / `Power` and **`BenefitLvSlg` / `BenefitLvSlgPower`**. The latter current-row milestone bonuses were missing. The selected static native `SurvivorEquipmentModule.GetEquipPower` path adds both power fields for base-rank gear without breakthrough or external additions.

| Recorded hero | Previously omitted gear power |
|---|---:|
| Rosie | 35,120 |
| Freja | 12,320 |
| Becca | 75,920 |
| Maddie | 13,460 |
| Ray | 32,440 |
| Total | **169,260** |

Base rows sum to 1,757,868. Adding the milestone rows gives **1,927,128**, exactly the report. Model 16 now includes the corresponding flat ATK/DEF/HP and power once in both editions. Current rows already contain the applicable bonus: earlier milestone rows are not summed again. Reference anchors and gear XP upgrade returns are regenerated. For example, yellow armour 19 to 20 now correctly adds 222 DEF rather than only the 72 base DEF increase, at the same 5,200 XP cost. A cheap level crossing a milestone can therefore outrank another upgrade.

Unrecorded gear rank, breakthrough and enchants are still excluded. The native power function has separate paths for those; this fix does not grant them automatically. The saved profile is not edited.

## What a damage row actually measures

Ten selected static native methods and relevant field offsets were fingerprinted against the verified 2.6.400.304 private image and metadata. Summon/effect/gear tables were independently checked against the current downloaded manifest.

`RaidFightStatisticsMgr.GetStatisticsData` first looks for a registered GUID. If absent, its camp-0 soldier fallback looks up `FollowHeroGuid`. Its camp-0 summon fallback looks up `HostGUID`, provided a template exists and its `IsNotStatistics` field is not 1. This is a single registered-host lookup, not an arbitrary recursive ownership graph.

Thus a hero-owned row can include soldiers and eligible summons. Maddie's arrow/dog and Ray's four mapped damage-zone templates have the eligible flag value 0. This establishes possible attribution, not that every referenced actor executed or hit. Frank's unresolved attack timeline remains unresolved.

The signed HP-change callback adds negative magnitude to outgoing/incoming damage, and nonnegative magnitude to outgoing/received healing. Effect configuration `IsNotStatistics == 1` skips that callback's counters. A separate shield callback adds absorbed damage to outgoing and incoming damage counters. Consequently, **displayed damage is not necessarily HP removed**. The raw healing counter does not independently establish effective healing or overheal behavior upstream.

There are two overlapping axes: **owner** (hero-owned or separate Behemoth) and **mechanism** (direct, soldier, summon, shield absorption). Summon damage and absorbed damage cannot simply be added on top of an inclusive hero row. Their amounts remain unidentifiable from these aggregate columns alone.

The local manager initializes self-side hero, titan and pet records. It does not prove that server report collection uses identical code or that active hotfixes preserve it. The audit and ledger explicitly retain that boundary.

## What can be measured now

For this recording:

- Skill power: **zero reconstruction error**.
- Gear power after model 16: **zero reconstruction error**.
- Opening readiness displays: **5 of 5 consistent** with configured rounded delays.
- Displayed hero-owned outgoing damage: **32.79M**; separate Behemoths: **5.12M**.
- Opponent outgoing rows exceed friendly visible hero incoming rows by **3.72M**.
- Friendly outgoing rows exceed opponent visible hero incoming rows by **3,990,520**. The newly transcribed opponent incoming rows are 18.19M, 13.85M, 605.14K, 808.53K and 465.81K.

Both residuals exceed conservative display-precision budgets (120,000 and 90,030 respectively). Rounding alone cannot explain them under those budgets. These comparisons include pet outgoing rows and only the visible hero incoming rows. Actor coverage, attribution and collection definitions must be reconciled before calling either a simulation error. Shield callbacks add to both endpoints when both resolve, so shields alone are not a demonstrated explanation for a counter mismatch.

**These are input/accounting checks, not damage prediction accuracy.** There is still no frozen independent damage prediction for this fight. Held-out damage MAE/WAPE and matched squad-ranking agreement therefore remain unavailable, rather than being reported as zero error or perfect accuracy.

`damage_ledger.py` implements the selected static callback rules for supplied synthetic events. It separates owner and mechanism axes, shield and HP-change damage, healing, opt-out effects and unresolved endpoints. Tests demonstrate why the visible rows need not conserve when an endpoint lacks a registered owner. No unobserved real events are generated to explain the residuals.

`accuracy_metrics.py` now measures owner-level MAE and WAPE only for compatible definitions, the current model hash, a timestamped prediction before outcome, held-out designation and unique battle identity. The separate paired ranking metric requires reviewed matched starting context and a declared outcome target. It excludes uncontrolled rally shares. Input provenance and independence still require review; a flag is not self-verifying evidence.

## Global scoring sensitivity

`Global-Score-Sensitivity.json` tests the **individual index**, not squad composition. The controlled scope is all 29 supported base heroes, equal maximum T5 builds, no account context and no enemy counter. Nine weight choices vary offence from 45–65% and utility from 5–15%, with defence taking the remainder. Production weights remain 55/35/10.

Only **Lava and Kiki** stay in the top five across all nine deliberately selected weight scenarios. The baseline top five are Lava, Kiki, Ragnar, Nikola and Becca. With baseline weights, opening 10/20/30-second assumptions also change membership/order: Maddie enters the 10/20-second top five and Mike enters at 30 seconds. These are robustness results, not empirical probabilities or evidence that these heroes win actual fights. Faction composition, team synergy and front placement are outside this individual-index diagnostic.

The new physical-stat correction is shipped; global coefficients are not fitted to one mixed-build loss. A useful global validation target is paired lineup performance against a fresh identical enemy, with exact builds, troop counts and account context, and no uncontrolled rally participants. Record predictions before the result and group repeated reports/replay views as the same battle. A balanced utility score should not be judged solely against a damage leaderboard.

## Reproduce

- `python work/battle-lab/audit_damage_attribution.py` — private native artifacts and installed game data required; exports hashes, selected fields and normalized reference facts only.
- `node work/battle-lab/analyse-replay.cjs`
- `node work/battle-lab/score-sensitivity.cjs`
- `python work/battle-lab/measurement-report.py`
- `python -m unittest discover -s work/battle-lab -p 'test_*.py'`
- `node --test work/battle-lab/test_replay.cjs work/battle-lab/test_sensitivity.cjs`

Public artifacts are under `outputs/hero-report`. Raw disassembly, recordings, frames and personal profiles remain private.
