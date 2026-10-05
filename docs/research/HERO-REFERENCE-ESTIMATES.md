# All-hero reference estimates

This deliberately low-confidence inference model covers all 29 supported base
heroes without personal build input. The native Windows and offline browser
planners display one compact **Est.** score. Per-hero assumptions, basis and
scenario range are hidden under **Estimate details**, collapsed by default. No
mandatory build inputs or save buttons are required. One compact comparison-basis
selector keeps personal progress separate from fair comparisons:

- **Equal builds** (default): all heroes use the same reference development;
  saved rank, level, skills, gear and ownership do not affect their scores.
- **Flat max stats**: original maximum-stat indices only, with no inferred skill
  pressure, utility, Stamina economy or synergy bonus. Identical stats tie honestly.
- **My builds** (opt-in): valid recorded values replace reference defaults.

The selected basis is saved separately. Old profiles default to Equal builds.
Resource priorities independently use recorded builds of owned heroes only;
reference assumptions are never substituted into upgrade costs or record actions.

## Reference and personal data

The reference is level 110, rank 3 step 6, skills at that rank's configured caps,
no gear. This compares equal development, **not equal resource expenditure**.
In My builds mode only, valid saved rank, level, skill and gear values replace the respective defaults.
Missing skills use the reference skill level limited by the effective rank's cap;
explicitly locked level 0 remains locked. Invalid values are not accepted as
observations. Assumptions remain in the calculation only: they are never written
back as the user's actual build or used to record an upgrade.

Basis labels distinguish Reference build, Recorded + assumed, and Recorded build.
Even a fully recorded build retains low confidence: combat mechanics are inferred.
Every unowned/unrecorded hero remains in the candidate pool subject to existing
access/ownership filters. Changing a build does not re-normalize unrelated heroes.

## Inputs and assumptions

`build_estimate_model.py` consumes the manifest-verified combat dependency audit,
progression dataset and roster from the same pack fingerprint. For each skill it
selects the strongest referenced non-text **Type 0** effect with no custom formula.
It applies the matching numeric effect-param2 level multiplier and divides the
base parameter by 1000. This supplies an input for a **representative-effect
pressure proxy**, not damage dealt. Multiple rows are not blindly added together.
Type 1 healing rows are not classified as damage because of their names.

The selected skill's configured cooldown supplies an assumed activation cadence;
zero cooldown uses a 2-second basic / 12-second other-skill prior. Minimum assumed
cadence is 0.5 seconds. A complete cast scheduler, effect inheritance, flight time,
target count, multi-hit or zone ticks are not simulated. If unresolved effects
leave pressure unknown, generic priors are 0.25 basic / 0.08 other. Known non-damage
effects do not receive that pressure prior unless additional dependencies remain
unresolved. These priors are deliberate uncertainty handling, not game facts.

Utility is a qualitative, dimensionless planning weight: healing 1.3, shield 1.2,
stun 0.8, slow 0.35, ATK reduction 0.6, DEF reduction 0.8, damage reduction 0.9,
summon 0.6, based on effect types and identifiers/descriptions. Each tag contributes
once per skill. These magnitudes, application rates and rank-independent utility
weights are **model assumptions**, not extracted combat values. An absent tag is
not proof that a hero lacks additional utility. AoE and conditional uptime remain
unresolved. Stamina economy and the existing capped formation-synergy heuristic
remain separate; neither is measured battle damage.

## Scoring and sensitivity

With effective stats A/D/H, summed pressure P and utility U:

```
offense_raw = A * (1 + 0.5 * log(1 + P))
durability_raw = (0.7 * H + 30 * D) * (1 + 0.08 * U)
utility_raw = 1 + U
```

Each component is divided by the maximum of that component across the fixed
reference roster and multiplied by 100. Balanced score is 55% offense, 35%
durability, 10% utility. Existing objective-specific squad weights operate on
these estimated components. The logarithm dampens uncertain large effect values;
all weights are inspectable heuristics. A developed build may exceed 100.

Conservative/optimistic scenarios multiply P by 0.5/2.5 and U by 0.5/1.5. The
displayed range is a **sensitivity range**, not a statistical confidence interval,
guaranteed bound or probability of winning. It does not cover every possible
server override. Similar scores and overlapping ranges should not be treated as
precise tier differences; valid ties are kept.

This model is deliberately separate from resource-priority percentages, which
still compare the explicitly chosen configured power/ATK/DEF/HP contribution.
It does not resurrect the invalid affine DamageParam model or claim to prove a
Ray nerf. See [the native audit](HERO-COMBAT-AUDIT-2026-10-05.md).

Regenerate normalized model with `python work/hero-extraction/build_estimate_model.py`.
Native/browser parity tests cover every hero under reference, recorded, partial
and locked builds. UI regressions check coverage, non-collapsed SSR estimates,
collapsed details and preservation of real user profile data.
