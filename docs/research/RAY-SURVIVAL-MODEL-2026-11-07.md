# Ray and survival model update — 7 November 2026

The default model now follows Ray's checked projectile impact paths rather than selecting the largest dependency. His basic attack uses its linked zone (0.36 at level 1). His active has three distinct impact zones (2.4 + 3.2 + 4.0 = 9.6 per-target potential at level 1). This does not assume three enemies are hit. Projectile travel and interruptions remain unresolved.

## Measured effect on the existing replay

| Check | Previous model | Model 17 |
|---|---:|---:|
| Default offense proxy, fitted weighted error | 25.14% | 24.15% |
| Default offense proxy, internal held-owner error | 30.32% | 29.25% |
| Full 30-second coefficient proxy, fitted error | 27.18% | 21.77% |
| Ray full-window signed error | −38.47% | −22.18% |

These are reconstruction errors from one battle, not overall accuracy or win prediction. A single shared output scale is fitted. Other hero curves and the fixed reference anchors retain their previous values. Checked client summon/skill paths support the dispatch interpretation; they do not establish which impacts actually hit in the recorded server battle.

## Optional HP survival benchmark

An event-driven front/back pressure model now predicts survival from pre-fight modeled HP. It redirects pressure after deaths. It never takes observed death times or damage as runtime inputs. A separate laboratory fit estimates aggregate pressure and the back-row share using the existing replay.

Fitted survival error is 6.53%; internal leave-one-owner-out error is 11.31%. Each owner's outcomes are withheld from every calibration choice for their own prediction. A simple position-only control scores 11.05%, so superiority over that baseline is not established. Only two of five held-owner predictions fall inside the broad presentation-time intervals. Replay presentation time has not been established as the original combat clock.

The optional benchmark is OFF by default. Model 19 removes its original My-builds-only restriction: it now uses the same rules across all comparison modes. It discounts personal offense by predicted alive time and affects the actual squad search. A regression test demonstrates a fragile high-output candidate being replaced by a sturdier candidate; turning the benchmark off restores previous scoring. Unknown or unavailable stats never provide a survival bonus. Other durability, utility, faction and synergy components retain their existing model. See the [mode parity and wider roster audit](PROJECTILE-BURSTS-AND-MODEL-PARITY-2026-11-07.md).

Coupled predicted-survival damage remains imperfect: ATK-based internal held-owner error is 21.52%, with Ray underestimated by about 36%. Troop HP, healing, shields, targeting, control, mitigation and summon attribution remain unresolved. This is a reference-pressure experiment, not an opponent-specific or fiend combat simulator. Independent-battle prediction accuracy remains unavailable.

## Interface and saved-data changes

- Native startup explicitly shows/restores the window; duplicate launches activate the existing instance.
- Universal gear selection uses 18 exact client item sprites and selectable panels, including explicit empty slots. No maximum levels or unknown gear are inferred.
- Completeness refresh runs independently of estimate changes, including while comparing maximum builds.
- Build review dates are explicit: a single field edit does not revalidate untouched values. A reminder appears after 14 days, on a data-snapshot change, or when no confirmation exists. The period is a product reminder, not a game expiry rule.
- Account review covers Research, Behemoths and Signature Gear. Changing the recorded account context requests another review. Confirmation gives blank or unowned sources no bonus.
- Model 18 changes the actual normalization scale from 100 to 1000. Offense, durability, utility, scenario ranges, passive contributions and all formation score components now use those units before ranking. Formatting no longer remaps scores or appends `/1000`. Physical stats, stamina percentages, score ratios, ordering and resource efficiencies are unchanged by rescaling. The maximum T5 reference anchors are 1000 per channel; external bonuses can exceed those reference maxima and are not clipped.
- The persistent header is smaller in both editions.
- Draft-based date clues are conditional. Introduction windows are not confirmed draft activation schedules; a merge can use unknown server overrides. Existing dates are not automatically overwritten. Match the live draft before using the clue.

Machine-readable evidence: [Ray audit](../../outputs/hero-report/Ray-Impact-Audit.json), [survival reconstruction](../../outputs/hero-report/Survival-Reconstruction.json), [runtime benchmark](../../outputs/hero-report/Survival-Benchmark.json).
