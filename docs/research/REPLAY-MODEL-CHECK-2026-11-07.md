# Replay model check — 7 November 2026

**Follow-up:** model 16 resolves the gear residual below through omitted level milestone bonuses. See [damage attribution and scoring follow-up](DAMAGE-ATTRIBUTION-AND-SCORING-2026-11-07.md) for the correction and newer measurement report.

The supplied recording shows one PvP defence report and its replay. Account names, alliances and coordinates are excluded from the public observation. The report and replay count as one battle. No prediction was saved before the result, so this is a mechanics check, not held-out validation.

## Correction shipped in model 15

The progression exporter omitted `survivor_skill_main.Benefits` from skill stat inputs. Some fourth skills supply flat hero ATK/DEF/HP through benefit IDs 301825/301826/301827, even though their Raid display parameters contain presentation-only effects. Excluding those fake damage effects was correct; excluding their separate flat stats was not.

Both planners now add the selected skill row's flat stats once, before modeled runtime percentage modifiers. Upgrade stat returns include them too. Skill BattlePower is still counted once. Unrecorded, locked, invalid or rank-gated skills receive no benefit. Reference anchors include the same maximum skill benefits, so score scales have changed; score changes are not damage percentages.

| Recorded skill | ATK | DEF | HP |
|---|---:|---:|---:|
| Freja fourth skill, level 1 | 5,378 | 1,075 | 358,560 |
| Maddie fourth skill, level 1 | 6,480 | 1,296 | 432,000 |

The current downloaded skill table was verified against the current manifest and matches the table used for progression data. Exported rows retain source hashes. Other benefit families, including troop percentages in `OverallBenefit`, are not silently converted to flat hero stats.

## What the recording verifies

- Five opening active-skill HUD countdowns agree with the configured delays under a ceiling-display hypothesis. Countdown readiness is not an observed hit or completed cast.
- The recorded friendly skill levels reconstruct **1,165,764 skill power**, exactly matching the report.
- Friendly hero damage totals **32.79M** and Behemoth damage **5.12M**. Behemoths account for about **13.5%** of displayed outgoing damage. Their direct battle contribution remains outside the planner combat score; the existing configured hero-stat contribution is separate.
- The front heroes grey out much earlier than the back heroes. Therefore total damage share cannot be used directly as an intrinsic hero damage weight.

## Replay sensitivity simulator

`work/battle-lab/analyse-replay.cjs` now replays resolved coefficient schedules with an externally supplied survival window. It stops new casts and direct damage dispatch after that window, handles in-flight dispatches, and separates cancellation from persistence of already-applied periodic effects. It keeps the full observation duration as the rate denominator and honors supported parent-finish triggers. It does not predict death times.

Broad HUD intervals and a playback speed compatible with 2x give illustrative survival windows of Rosie 10–13 seconds, Freja 8–13, Becca/Ray 20–23 and Maddie 24–27. These are scenario bounds, not precise engine timings or confidence intervals. Damage per alive-second is descriptive: it still includes differences in build, targets, summons and mitigation. No global 55/35/10 score weights or front-pair survival weight were fitted to this one battle.

## Unresolved discrepancies kept visible

1. Transcribed equipped items sum to **1,757,868 gear power**, versus **1,927,128** displayed: residual **169,260**. No gear multiplier or inferred upgrade has been invented to close it. The player's saved profile was not altered.
2. The report gives **10% troop health** for three matching heroes. Current manifest-verified `battle_formula_coefficient.same_unit_type_add_up` includes that 10% tier, while `game_configs.same_unit_type_add_up_desc` supplies the planner's **8% Final Health** description tier. Two local definitions exist. The runtime selector and whether these apply to different hero/troop calculations remain untraced; a server override is not established. This recording does not justify replacing all Final Health tiers.
3. Enemy displayed damage does not exactly equal friendly damage taken. Shield, overkill, attribution and summon accounting are not resolved, so conservation was not forced.

Full target selection, movement, interruptions, effective healing, conditional execution and Behemoth attacks remain necessary for an actual outcome simulator. Overall prediction accuracy remains unmeasured.

## Reproduce

Run `node work/battle-lab/analyse-replay.cjs` and `node --test work/battle-lab/test_replay.cjs`. Normalized input and output are `outputs/hero-report/Replay-Observation-2026-11-07.json` and `Replay-Checks-2026-11-07.json`. Raw video and extracted frames remain private. `validate_model_evidence.py` accepts repeated `--evidence` paths and rejects duplicate battle IDs; its default set includes this recording.
