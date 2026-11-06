# Fiend mechanics lab

This is the first simulation layer, separate from the community planner's scoring model. It resolves configured encounters and generates **raw cooldown opportunities**, not a predicted battle winner or a damage percentage. No fitted coefficient or observed result has been inserted to make the examples agree with the reports.

## Inputs recovered on 6 November 2026

- Ten `gve_boss_new_period` encounters, each referencing five NPC formations.
- All five enemy units per formation: levels, rank steps, separate level/rank/shared benefits, skills and configuration power.
- 115 linked field/Lite skills across enemies and the supported hero roster, with target fields, cooldown fields and dependency identifiers.
- 48 battle coefficients, including the configured defense parameter, troop-power exponent, battle limit, healing coefficients and morale settings. Their presence does not establish every formula that uses them.
- Candidate monster/rally casualty rules.

Tables are exported only after their bytes match the installed cache manifest. Raw tables, native bytes, scripts, profiles and recordings remain private. The published JSON contains selected identifiers, scalars and provenance hashes.

## Report checks

The level-10 Tusker configuration matches the independently transcribed report inputs:

| Input | Configuration | Report |
|---|---:|---:|
| Troops per enemy formation | 62,414 | 62,414 |
| Sum of five enemy heroes' configuration power | 6,179,105 | 6,179,105 |

Its configured display-power reference is 115,194,150 (115.19M when rounded), and the five formations contain 312,070 troops in total. These also agree with the November recording's displayed reference values. Configuration agreement identifies the encounter; it is **not battle-prediction accuracy**. Five identical variants do not create five independent observations.

The November recording at approximately 73 seconds shows 60,000 incapacitated friendly troops: 180 hospitalised, 59,820 lightly wounded and zero permanent losses. The candidate `battle_gve_rally` rule has rates 0.003 and 0.997, reproducing that split. The helper keeps fractional expectations unrounded because the game's rounding policy has not been established for all troop counts. The rule does not predict the number incapacitated, and a single matching report does not prove every mode's rule routing.

The 23% and 19% mail summaries are rally contribution shares. They cannot be used as per-hero damage coefficients or a matched single-round prediction target without the other participants, round order and carry-over state.

## What runs now

`simulate_fiend.py` resolves one explicit enemy formation and produces cooldown opportunities over a caller-specified horizon in **raw configuration units**. It can also load a local desktop profile and five selected heroes. Missing or locked skills produce no activity, and the profile is never modified. Skills with unresolved conditions, triggered cadence or limits are excluded from this initial scheduling layer.

The output deliberately leaves seconds, winner and damage prediction null. Simultaneously ready skills are opportunities; the field engine's cast arbitration, interruption rules and conversion to seconds have not been established. A supplied death boundary stops opportunities, but death times are not inferred.

`raid_damage_kernel.py` is an independently tested translation of the inspected current **Raid** base-damage helper:

```
effective_DEF = max(0, DEF - flat_penetration) * max(0, 1 - percent_penetration)
base = ATK² / (ATK + defense_parameter * effective_DEF)
damage = base * coefficient + flat + property_source + custom_formula + external_additive
```

The configured defense parameter is 2.5. The native caller applies additional effects, crit, floating rolls and power corrections. **This helper is not established as the field/Lite fiend formula and is not used by the fiend scheduler or the released planner.** Matching constants in two systems do not prove that their formulas or runtime paths are interchangeable. The `pve_formula` examples named `test` and `damage_test` are not treated as authoritative formulas.

## Next gaps to trace

1. Resolve the field/Lite `Type 11100` operation, skill magnitude source and modifiers. The enemy and hero links use field skill records, so a verified bridge is required before reusing Raid formulas.
2. Reconstruct final ATK/DEF/HP from the distinct hero, troop, research, faction and behemoth sources, and establish troop-count scaling.
3. Establish clock units, targeting, death timing, buffs, heals, shields and behemoth combat execution.
4. Model rally participant ordering and state carried between rounds/formations.
5. Save predictions before running a new matched fight, then compare per-round damage, healing, survivors and casualties. Existing reports can check mechanics or calibrate parameters, but cannot retrospectively become held-out predictions.

No claim is made that a server override causes the current uncertainty. It is an unverified execution/formula boundary in the extracted client evidence.

## Reproduce

Run from the repository root. `build_fiend_data.py --help` lists the pack, manifest, loose-cache and private-output arguments. It refuses mismatched table hashes.

```
python work/fiend-lab/simulate_fiend.py --horizon-ticks 500 --output outputs/fiend-lab/Tusker-Level-10-Cooldown-Example.json
python -m unittest discover -s work/fiend-lab -p "test_*.py"
```

For a private roster test, add `--profile PATH --squad rosie freja becca maddie ray` and write the output under `tmp/`. The caller must choose a formation explicitly if different from index zero. This does not automatically simulate five formations at once.

`check_report_inputs.py` accepts the private transcribed October PvE observation and compares the known enemy troop count and hero power. `audit_native_bridge.py` checks the exact private native image/index hashes before recording fingerprints; it never loads the executable. See `outputs/fiend-lab/` for the normalized catalog, example and audits.
