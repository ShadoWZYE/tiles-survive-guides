# Combat evidence and optimiser improvements — 10 October 2026

The supplied PvP video, 16 screenshots and PvE video support improvements to
formation scoring and effect classification. They do not establish accurate DPS
or win probabilities for all 29 heroes. Both Windows and browser editions now use
the same corrected skill dataset and formation model.

## Which report pages are most useful?

| Page | What it establishes | Use |
| --- | --- | --- |
| Battle Stats: complete Damage Dealt and Damage Taken | Rounded per-hero output and exposure; separate Griffin row | Highest priority for validating damage shares and targeting |
| Heroes: formation diagram | Actual front pair/back three and survivors | Essential context for damage, death and uptime |
| Skills and Gear: all heroes on both sides | Actual development differences | Essential for fair comparisons; power totals cannot replace these |
| Troops | Count, tier and displayed relative damage percentage | Essential matchup control; not a verified universal damage formula |
| Faction and signature equipment | Composition bonuses and extra equipment | Controls for otherwise unexplained differences |
| Research, Griffin and Collections | Account-wide differences and extra combat sources | Necessary when comparing different players |
| Overview or rally contribution percentage | Outcome and sequential rounds | Useful identification; weak evidence for individual skill coefficients |

The screenshots contain **8 distinct images**, repeated across 16 attachments.
They describe one PvP attack at displayed 15:50:42, with two rounds. Round 1 has
Rosie/Layla in front and Becca/Maddie/Ray behind, all level 110, against Chef/Rusty
and Lucky/Maddie/Ray. The skills are materially different: friendly Rosie, Layla
and Becca have 10/10/10, Maddie 27/28/18 and Ray 18/20/18. Friendly gear power is
1,227,286 against 467,085. The troop page shows 41,000 tier VIII against 34,200
tier VII, with 120% displayed friendly damage. Friendly faction health is +4%,
enemy +12% with +5% composition counter bonus. No Battle Stats damage breakdown
is included in this screenshot set, and partial star steps remain untranscribed.

[Screenshot observations](../../outputs/battle-reports/2026-10-10/screenshots/observations.json)
preserve gear colours/levels, skills, formation, context and duplicate hashes.
These records do not alter the user's saved profile.

The first video supplies three complete PvP round breakdowns from two reports.
The two front heroes receive **97.08%, 95.99% and 94.08%** of displayed friendly
hero incoming damage. These are descriptive shares for those observations.
[Initial assessment](BATTLE-REPORT-OPTIMISER-2026-10-10.md) and
[numeric observations](../../outputs/battle-reports/2026-10-10/observations.json).

The PvE video shows three successful level-10 Tusker rallies with displayed player
contributions 63%, 82% and 83%. It revisits first-round statistics; matching screens
are not counted as independent experiments. In the visible statistics, Layla and
Nikola take damage and Rosie/Becca/Ray each display zero incoming damage. Its
296×640 resolution makes some small numbers uncertain, which remain unknown.
The first round's displayed friendly damage order is Rosie, Nikola, Becca, Layla,
Ray (17.11M, 13.83M, 12.73M, 10.52M, 9.38M). These are rounded observations,
not controlled equal-build rankings. Rally share depends on other participants,
round count and troop carryover; it is not a skill multiplier.
[PvE observations and evidence](../../outputs/battle-reports/2026-10-10/pve/observations.json).

## Implemented: formation position matters

Previously, five heroes contributed equal shares to squad durability regardless
of where they stood. Role sorting could put a fragile second melee hero ahead of
a stronger mid hero. The new model selects the two most durable non-ranged
candidates when available and fills from all heroes when necessary. It protects
ranged carries and sorts the back three by offense. Front/back jobs are labelled
by actual recommended position, rather than by class alone.

For estimated squads, effective durability includes the composition's existing
HP contribution. The front pair uses its harmonic mean so one strong hero cannot
mask a fragile partner. Squad survival proxy is:

```
front = harmonic_mean(front_hero_1, front_hero_2)
formation_durability = 0.75 * front + 0.25 * mean(back_three)
frontline_fit = existing_mode_durability_weight *
                (formation_durability - mean(all_five))
```

The 75% weighting is a **conservative planning assumption**, not a fitted damage
probability. PvP and PvE observations motivate front emphasis but cannot determine
the optimal coefficient. HP is not added twice: the fit is a redistribution
relative to the existing mean contribution, after the existing faction bonus.
Mode durability weights derive from the existing component mixture: Balanced
0.35, Offense 0.0875, Survival 0.8375, PvE 0.3875. Equal durability produces zero
adjustment. Individual hero indices and resource-return percentages are separate.
Flat max stats excludes this adjustment.

The separate signed **frontline fit** component appears in both search results
and the selected formation score. It therefore affects squad selection and
unlock recommendations consistently. This is still a heuristic: targeting,
damage saturation, actual death times, conditional passives and pair synergies
are not simulated.

## Implemented: correct skill evidence classification

The previous builder could choose generic damage_attack_100 ahead of the actual
hit-linked damage_becca_attack, damage_maddie_attack or damage_layla_attack.
Version 2 prefers effects referenced by actual extracted hit events, falling back
to a representative dependency only when necessary. It retains one representative
effect; it does not invent a complete hit count from a dependency list.

Empty effect_skill_3_empty rows no longer give healing credit. Text/presentation
rows cannot supply damage or healing. A skill with only known presentation rows
does not receive an unknown-damage prior. Damage-zone Type 7 effects no longer
receive summoned-ally utility credit. Real summon dependencies and recognized
lifesteal/recovery descriptions retain qualitative utility. Locked level-zero
skills still contribute zero.

Every skill records direct-hit selection basis, observed event count, base
pre-cooldown, zone/summon dependencies and unverified execution. Estimate details
show a hero-specific evidence summary. Fixed roster normalization anchors are
regenerated from the corrected model. My builds, Equal builds and Flat max stats
remain distinct; no screenshot value is silently written into a build.

This fixes identifiable model errors but does not certify accurate hero tiers.
Rosie's description says her basic hits twice; the current audit exposes one
hit reference plus additional damage dependencies, without proving all executions.
Ray's active has three projectile-hit events dispatching damage zones. Zone ticks,
AoE targets and eagle triggers remain incomplete. Layla's heal-over-time and damage
ticks, stat passives, critical hits, penetration and live defense formulas remain
unresolved. No report-total fitting or claimed Ray nerf is introduced.

## Exactly what additional data is needed

For **one round**, capture these in order, including the report timestamp and
round number so pages cannot be mixed:

1. Heroes tab: full formation diagram with both sides and remaining health bars.
2. Battle Stats: scroll through every Damage Dealt row (including Griffin), every
   Damage Taken row and troop casualties. If tapping a bar reveals a label or
   tooltip, include it to establish the green bar's meaning.
3. Heroes tab: all Gear and Skills rows on both sides, faction bonus and signature
   gear. For partial stars, open each friendly hero's own rank page showing the
   exact rank/step; capture their actual ATK, DEF and HP detail pages as well.
4. Troops tab: count/tier, Griffin and its skills, Research and Collections.
5. **Actual battle replay** from start to finish at original resolution and normal
   speed. This is the missing evidence for duration, basic-hit cadence, active
   casts, multi-hit/zone ticks, targeting, stun time and death order. A recording
   of the report screens cannot establish those timings.

For a useful comparison, repeat the same target with the same troop count/tier,
account buffs and Griffin. Change **one variable**: one hero, one front position,
or one skill level. Start with Rosie versus Ray at comparable development, or
Rosie/Layla versus Rosie/Nikola in front. An unchanged-run repeat helps expose
random crit variance; several repeats improve stability without guaranteeing it.
Use separate PvP and PvE comparisons. In a rally, use the same participant set,
join order and selected round; contribution percentages alone are insufficient.

## Validation

The new regressions cover fragile-frontline behavior, protected ranged carries,
input-order stability, zero durability, incomplete/flat squads, faction health,
actual search score breakdowns and removal of fake healing/summon credits.
Native/browser placement and adjustment parity covers 1,536 cases. Existing
hero-estimate parity, all faction combinations, upgrade returns, profile safety,
browser mobile behavior and WPF autosave/record/Undo are also checked.
