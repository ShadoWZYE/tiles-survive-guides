# Battle recording assessment — 10 October 2026

The supplied 83.23-second recording provides useful combat observations, especially
for formation exposure and testing build-aware estimates. It does not yet support
fitting universal hero damage multipliers. This was the initial recording-only
assessment; subsequent screenshots/PvE analysis and implemented changes are in
[the combined model report](COMBAT-MODEL-IMPROVEMENTS-2026-10-10.md).

## Evidence retained

[Structured observations](../../outputs/battle-reports/2026-10-10/observations.json)
contains three complete per-hero numeric breakdowns from two reports, the source
video SHA256, timestamps, visible levels, troop context and explicit unknowns.
Nine full-resolution source frames are retained beside the JSON. Values are rounded
screen displays, manually transcribed, not exact underlying damage counters.
Other reports and build pages in the recording remain only partially inventoried.

The attack report at displayed 03:50:41 has multiple rounds: the first two are
transcribed. They are dependent observations from one battle, not two independent
experiments. The defence report at displayed 03:50:17 supplies a separate round.
In-game timestamps are retained as displayed; their timezone is not verified.

## Main squad: repeatable ordering within this recording

All five friendly heroes are level 145. These are raw red-bar totals under
Damage Dealt; they exclude the separately displayed Griffin damage.

| Hero | Attack round 1 | Attack round 2 | Pre-correction equal-build offense index |
| --- | ---: | ---: | ---: |
| Layla | 12.89M | 9.26M | 76.18 |
| Nikola | 15.13M | 12.78M | 78.66 |
| Rosie | 19.90M | 14.30M | 86.13 |
| Becca | 16.17M | 11.30M | 95.86 |
| Ray | 10.47M | 8.61M | 89.24 |

Rosie leads both rounds; Ray is last in both. The model's reference offense order
is Becca, Ray, Rosie, Nikola, Layla. This is a useful discrepancy to investigate,
not a measured equal-build error: actual skill levels and equipment differ.
For example, the skills page near 70 seconds shows Rosie's basic/active skills
at 35/35 and Becca's at 30/30. Levels alone do not establish equal development.
No Ray balance change is established by this report.

Evidence: [round 1 damage](../../outputs/battle-reports/2026-10-10/evidence-50s.jpg),
[round 2 damage and incoming damage](../../outputs/battle-reports/2026-10-10/evidence-75s.jpg).
Reference indices were calculated with the current browser EstimateModel.evaluate
using null saved builds and the current local upgrade/estimate JSON files.
Those indices are planning proxies, not percentages of observed damage.

## Formation exposure is a stronger actionable signal

Layla and Nikola occupy the two front positions in the main squad. Their incoming
damage is 5.38M + 3.30M in round 1, versus 0.26104M combined on the other three:
**97.08% of the friendly heroes' displayed damage taken falls on the front pair**.
In round 2 the same calculation gives **95.99%**.

The defence squad is Rusty 116, Freja 145, Ghost 124, Maddie 145, Sarge 145.
Rusty and Freja receive 14.24M + 20.98M of the squad's 37.43764M displayed incoming
damage: **94.08%**. Maddie leads its damage output at 21.38M, followed by Sarge
16.01M, Freja 15.62M, Ghost 11.52M and Rusty 4.69M.

Evidence: [defence damage](../../outputs/battle-reports/2026-10-10/evidence-64s.jpg),
[defence incoming damage](../../outputs/battle-reports/2026-10-10/evidence-65s.jpg).

This supports investigating position-dependent targeting, survival and cast uptime.
It does not prove a universal 97% targeting rule. Damage taken alone cannot rank
tank quality: it also depends on targeting, fight length, mitigation and healing.
The current browser orderFormation groups Melee, Mid, Range and sorts within those
groups; evaluateSynergy and the formation search do not simulate incoming damage
or position-dependent uptime. Native EstimateModel uses the same position-agnostic
hero component calculation. A future formation model should evaluate the two front
positions jointly with the three back positions and retain uncertainty.

## Confounders to preserve

- Main attack detail: 95,000 tier IX versus 57,500 tier VIII troops; the UI says
  friendly troops dealt 133% damage. Defence detail says 127%. These are observed
  UI comparisons, not established standalone multipliers for every hero.
- The round 2 overview begins with 89.79K troops while its Troops detail repeats
  95,000. Preserve both; avoid silently treating the detail as the round-start count.
- Friendly Griffin is level 207 versus enemy 126. Record its output separately
  and account for possible team effects rather than adding it to a hero's damage.
- Main-squad hero power is 21,160,910 versus 8,645,811 in round 1 and 4,107,385
  in round 2. Research, collections, gear, skills and signature gear also differ.
- The round 2 faction page shows friendly troop health +12%, counter bonus +5%,
  enemy troop health +4%. These match compose's 3+2 and 2+2 tiers for the visible
  lineups. This corroborates those cases, not all faction rules or a full mixed
  opponent damage formula.
- Green secondary bars are visible on some heroes and the Griffin. Their meaning
  is not labelled in the captured statistics; retain the numbers without asserting
  they are healing, shielding or additional damage. Missing bars remain unknown.
- No battle duration, cast counts, kill order, control uptime or replay is supplied.
  Totals cannot be converted to DPS, per-cast coefficients or calibrated win odds.

## Recommended use in the optimiser

1. Keep a separate observation dataset keyed by report and round, with exact builds,
   positions, troop counts/tiers, opponent composition and video evidence. Do not
   overwrite Equal builds or saved personal builds from an incomplete report.
2. Compare fully recorded builds against observed within-squad damage shares in
   repeatable matchups. Use discrepancies to audit effect graphs, targeting and
   cast schedules. Do not divide damage by hero power as a substitute for stat
   normalization.
3. Add a formation-aware planning model only after collecting examples that isolate
   position or hero changes. Support metrics must cover team benefit, survival and
   cast opportunities, rather than rewarding raw damage alone.
4. Keep multiple rounds clustered by battle and evaluate calibration on held-out
   battles. Shrink any future empirical adjustment toward the existing prior when
   evidence is sparse; no fixed universal report count guarantees enough coverage.

The most useful next sample is the same squad and opponent with one hero or front
position changed, plus complete gear/skill/signature pages and a replay or duration.
This recording already provides an initial validation corpus and concrete model
questions, without claiming more certainty than the reports support.
