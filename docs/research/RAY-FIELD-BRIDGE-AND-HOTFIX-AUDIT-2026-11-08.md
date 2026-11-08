# Ray, field combat and cached hotfixes — 8 November 2026

## The percentage shown on hero cards

The former “model gap” label meant **difference from the highest roster score**, not measured prediction error. It is replaced with “% below leader” and “Highest roster score” in both editions. In My builds, cards using incomplete data also show **Base est.** and **Defaults · N missing**. Hovering lists the missing fields. No saved progression is changed.

An unrecorded hero is evaluated at base rank and level 1 with no unrecorded skill or gear upgrades. Several such heroes can have identical scores because their base stats and enabled account context match. A large difference from a developed hero does not establish that the model mispredicts combat by that percentage. This UI correction does not lower the real replay errors.

## Ray's eagle trigger: owner binding resolved

The selected static client path is now traced end to end:

1. `SkillBase.AddConditionTriggerListener` reads `OwnerObj` and passes it to `ConditionCheckerManager.GetConditionCheckerByConfigId`.
2. Both factory overloads preserve that source. `ConditionTarget = 0` retains it as the watched entity; Ray's `ConditionTarget_2` is also zero.
3. The Type-19 checker binds that entity and subscribes to its skill-over event. `ParamInt = [1]` selects active skills. Interrupted completions are rejected.

Therefore the current **own completed active** requirement has direct static support. Casting by another hero is not a missing source of eagle procs in this path. This removes one proposed explanation for Ray's residual without adding an unsupported multiplier.

## Cached hotfixes: checked, not assumed

All **22 cached containers** were parsed to the end of their data, including their replacement-method identities. None directly replaces the 19 watched combat/data classes, including Ray's condition checker, skill scheduling, summons, damage calculation and statistics attribution.

The audit reads structure and hashes instruction bodies; it never loads an assembly or executes a patch. Its format reference is the pinned [Tencent InjectFix loader](https://github.com/Tencent/InjectFix/blob/5ba42eb8f63fe37134a3c78690f97d8425e13588/Source/VSProj/Src/Builder/FileVirtualMachineBuilder.cs). Invalid indexes, unknown layouts, truncation and trailing bytes fail rather than producing a false “no replacements” result.

This establishes absence of **direct replacements in the inspected cache**. It does not establish which patch was loaded at runtime, exclude transitive changes through other code/config, or reveal original server equations.

## Field/Lite skill bridge: mapped across the roster

Manifest-verified current tables link the planner's 29 heroes to **114 field effects**. All 114 use **Type 11100**. They contain selection/count fields, but do not supply a resolved damage equation in the inspected rows. For example, Ray's field active points to a single-target Lite proxy; his Raid active has three projectile/zone dispatches. These are different representations, and their numerical execution bridge remains unverified. Neither raw Lite cooldown units nor target-count fields are substituted into Raid calculations.

The native Raid path passes `EffectiveSurvivor` through a target-filter helper before area filtering. That helper limits distance-cull entities; the value is not a guaranteed impact multiplier. Doubling Ray's output merely because one row contains `2` would not be justified.

## What changed numerically

**No damage weights or fitted hero multipliers changed in this pass.** The previously measured one-battle errors remain: default offense proxy 24.15% fitted weighted absolute error / 29.25% internal held-owner error; the optional predicted-survival/ATK experiment has 21.52% internal held-owner error and underpredicts Ray by about 36%. These are not independent-battle accuracy estimates.

The remaining original field/Lite calculation and report source attribution still prevent a defensible Ray-specific correction. Existing recordings show outcomes and presentation; they do not independently identify the server's per-source arithmetic. The code work narrows that problem to a concrete bridge rather than treating all local Raid paths as equally uncertain.

Reproducible artifacts: [field bridge findings](../../outputs/hero-report/Field-Bridge-Audit.json), [cached hotfix inventory](../../outputs/hero-report/Cached-Combat-Hotfix-Audit.json), [field auditor](../../work/battle-lab/audit_field_bridge.py), [safe cache parser](../../work/hero-extraction/audit_cached_hotfixes.py).
