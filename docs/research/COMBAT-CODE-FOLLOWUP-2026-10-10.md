# Further combat analysis without new battle reports

The local client still contains useful, unmodelled dependencies. This follow-up is a dependency audit, not a new combat ranking or a claim that the current optimiser simulates every skill.

## Confirmed gaps

The current `audit_combat_effects.py` inspects each root skill's releases and timelines but does not traverse `SubSkill`. Traversing the extracted configuration finds **12 additional child nodes across 114 resolved root skills**. Affected heroes are Knotty, Tara, Tarzan (two skills), Undine, Ray, Shark, Ragnar, Rosie, Layla, Candy and Mike.

| Example | Verified local dependency | What remains to establish |
| --- | --- | --- |
| Rosie basic attack | Root links to `survivor_rosie_attack_2`; both exported timelines reference their own damage effect. Child condition 158000097 is `rosie_attack_combo`, Type 19, referencing `survivor_rosie_attack`. | Native condition evaluation and scheduling: when the second attack runs and how it affects the attack cycle. |
| Ray second skill | Root links to `survivor_ray_skill_2_triger`; root and child reference condition 158000027, `ray_skill_3`, Type 19. | Trigger dispatch, gating and effect application. Child cooldown is not proof of unconditional cast frequency. |
| Layla first skill | Child condition 158000173 is Type 18 and references `survivor_layla_skill_1`. Buff rows separately reference healing and damage effects, with Time 5000 and Param1 1000. | Trigger order, meaning of timing fields, tick boundaries and stacking. |
| Ray/Maddie summons and zones | Type 7 effects contain prefab references and lifetimes omitted from the current effect summary. | Prefab components, their own skills, inherited stats, tick schedules, targeting and lifetime rules. |
| Rosie/Ray buffs | Buff configuration includes lifesteal/healing references and attack/defence/health modifier fields. | Property mapping, arithmetic, per-level overrides, stack rules and whether modifiers are already included elsewhere. |

The `pve_condition` table was extracted from the installed cache only after its manifest identity was verified and the pack SHA-256 matched the existing planner data snapshot. Numeric condition types and field names are observations; their gameplay semantics still require native implementation analysis.

## Recommended implementation order

1. Extend the dependency inventory to recursively follow child skills, conditions, releases, effects, buffs and prefab references, preserving unresolved edges and avoiding cycles. Keep dependency collection separate from executed hit counts.
2. Trace native condition evaluators and skill scheduling, then buff application/removal, periodic ticks and summon inheritance. Check patch dispatch where applicable.
3. Recover damage/healing arithmetic and per-level overrides. Model time, targets and frontline survival explicitly rather than valuing a skill from its strongest effect alone.
4. Integrate verified paths into both native and browser estimators with parity checks. For unresolved mechanics expose uncertainty or bounded scenarios; do not assign arbitrary trigger rates.
5. Use the supplied reports as outcome checks. Request targeted new recordings only for ambiguities that local assets and code cannot resolve.

Additional reports are not a prerequisite for these steps. They will still help validate server behaviour, practical uptime, targeting and patch-dependent results. No numerical scores or distributed planner packages were changed by this follow-up audit.
