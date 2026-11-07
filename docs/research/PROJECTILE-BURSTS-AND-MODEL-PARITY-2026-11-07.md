# Shared combat rules and projectile corrections — 7 November 2026

Model 19 corrects four projectile budgets and removes a comparison-mode restriction from the optional survival model. It keeps the existing 1000-point reference anchors and score weights.

## Equal builds and My builds

Both editions now apply the same survival benchmark when enabled, regardless of comparison mode. Previously, the benchmark silently operated only in My builds. The toggle is still off by default because its calibration comes from one battle.

Modes select inputs: Equal builds supplies maximum hero rank, level, skills and yellow T5 gear; My builds supplies recorded upgrades. Missing recorded level means level 1; missing or locked skills and gear give no bonus. Personal Signature Gear is a recorded-build input; shared account settings retain their documented scope. Different inputs can produce different scores, but the mode label must not change combat rules. Maximum recorded builds and the equivalent Equal builds now have automated score, formation and survival parity checks in both editions. No-gear maximum builds also receive the shared combat calculations.

## Projectile accounting

The earlier repeated-hit path counted immediate projectiles, but traveling bursts fell back to one representative damage effect. The corrected path counts distinct bounded launches with one eligible-recipient opportunity each. Simultaneous launches remain distinct when their action identities differ.

| Hero / skill | Distinct launches | Old level-1 coefficient | Corrected potential |
|---|---:|---:|---:|
| Tony basic | 6 | 0.1 | 0.6 |
| Dave active | 3 | 4.5 | 13.5 |
| Sarge basic | 3 | 0.2 | 0.6 |
| Eva active | 8 | 0.75 | 6.0 |

These are summed coefficients for one eligible recipient per launch, before target mitigation and hit success. They are not guaranteed damage, target counts, or multipliers on the hero's entire score. Skill-level modifiers, unlocks and the existing casting queue still apply. A locked skill remains worth zero.

The verified local projectile constructor defaults `HitTargetNumLimit` to 1. The action creates a projectile per target/action; sharing a launch timestamp does not merge actions. Unknown loops, conditions, property sources, altered timing and unsupported hit limits do not enter this path. Launch timestamps are not traveling impact timestamps, so opening-window calculations retain their completion fallback.

Maddie and Wright's active attacks also pass the same structural projectile-to-zone checks as Ray. Their numerical curves do not change; their linked damage source is now explicit. No hero-name whitelist is needed.

The [reproducible audit](../../work/battle-lab/audit_projectile_bursts.py) verifies hashes and field offsets against client 2.6.400.304, checks the four changed curves against commit `58d8382`, and rejects unexpected numerical changes elsewhere. Its [normalized findings](../../outputs/hero-report/Projectile-Burst-Audit.json) contain no raw client binary or player profile.

## Ray and measured error

These four corrected heroes are absent from the fully specified recorded friendly lineup. Consequently, the existing replay errors are unchanged: the default offense proxy has 24.15% fitted weighted absolute error and 29.25% internal held-owner error. The optional predicted-survival/ATK experiment has 21.52% internal held-owner error and underestimates Ray by about 36%. None is an independent-battle accuracy estimate.

The local skill-finish checker subscribes to the bound entity's skill-over stream. This does not support multiplying Ray's passive by every allied or enemy active cast. The full entity binding, live hotfix behavior and equivalence to the server's field combat remain unverified; no extra triggers are invented.

We also tested integrating configured skill coefficients only until *predicted* death, fitting pressure and damage scale without the held hero's labels. Internal held-owner error was **29.74%**, worse than the simpler 21.52% ATK control. Adding an unexplained exposure term reduced it to **19.49%**, but required four fitted parameters on five heroes and did not identify soldier damage. Neither experiment was promoted to the optimiser. The [probe](../../work/battle-lab/probe_survival_damage.cjs), [results](../../outputs/hero-report/Survival-Damage-Probes.json) and label-independence regression preserve this negative finding.

The remaining gaps include soldier contribution credited to heroes, effective healing and shields, targeting, mitigation and actual impact success. Replay presentation time is not a verified original combat clock. Existing recordings constrain these questions, but do not identify a unique full battle model. No per-hero correction multipliers or higher global confidence are claimed from these changes.
