# Hero planner: guide cross-check and client-code refinement

Initial native audit: 11 October 2026, client 2.6.200.276. Current configuration/asset refresh: 25 October 2026, installed build 2.6.300.293. Both editions now consume model v11; 44 selected current native base paths are audited. Full-engine and live-patch behavior remain unverified. Earlier sections below record the successive refinements. Rankings remain heuristic estimates, not measured DPS or win probabilities.

## Guide claims checked

Guides help identify mechanics to investigate; repeated claims on commercial sites are not independent confirmation. No tier list has been copied into the scoring weights.

| Published claim | Client evidence and model decision |
|---|---|
| Layla is a durable front-line healer with an HP passive. [Packsify Layla guide](https://www.packsify.com/blogs/tiles-survive-best-layla-build) | Permanent HP buff and temporary support dependencies exist. The real HP buff starts at 100 per mille, while the separate tooltip buff starts at 200. With the level-30 factor 1.29, these give 12.9% and 25.8% respectively. Use the real linked buff; flag the display/runtime discrepancy. Healing uptime remains qualitative. |
| Four Guardians plus one Gunner grant a special HP bonus. [Same guide](https://www.packsify.com/blogs/tiles-survive-best-layla-build) | The verified faction configuration instead gives four matching faction heroes +18% Final Health and +5% counter damage, with counters conditional on the opponent. Keep the existing faction model; do not introduce an unsupported role bonus. |
| Rosie performs a two-strike basic attack and heals based on damage dealt. [MTurboGamer Rosie guide](https://mturbogamer.com/2026/08/tiles-survive-how-to-get-rosie/) | The second strike is a linked child skill triggered by a non-interrupted finish of the first. Include that child damage coefficient. The client description expresses recovery in terms of Attack, but its real lifesteal property and tooltip-only healing parameter differ; neither description nor the guide proves the live formula. Keep recovery qualitative rather than assigning a damage-based healing rate. |
| Tara provides useful team defense. [Packsify tier guide](https://www.packsify.com/blogs/tiles-survive-her-tier-list) | Whole-team targeting and a permanent DEF percentage buff are linked. Native arithmetic operates on each recipient's property. Add recipient-based DEF support, not an invented multiplier based on Tara's own DEF. The guide's prescribed lineup is not treated as universally optimal. |
| Becca has line damage, enemy DEF reduction and a low-health crit condition. [Lootbar Becca guide](https://www.lootbar.com/blog/en/tiles-survive-becca-build-guide.html) | These are useful kit hypotheses consistent with the inspected dependency categories. Do not equate additional crit chance with an unconditional damage percentage, or assume every line attack hits the whole enemy team. Keep target count, crit uptime and signature-gear claims outside the numeric refinement until their runtime paths are resolved. |

## Native paths supporting the changes

Recovered method bodies are from the local executable image, with ILFix patch-dispatch branches present. The audit does not observe which live patches a server session might apply.

| Method / RVA | Relevant behavior |
|---|---|
| `RaidBuffPropertyModify.Init` / `0x28bdcf0` | Resolves configured property modifiers and obtains buff Param3 overrides; percentage values divide by 1000. |
| `SkillCellDataSystem.GetValueWithBuffParam3` / `0x28db980` | Resolves the configured value with the skill's multiplier and additive modifier. |
| `RaidPropertyUtils.CalculateFinalPropertyValue` / `0x28cd0a0` | Accepted modifiers accumulate: base property times one plus summed factors, then summed flat values. Percentage buffs do not multiply each other. |
| `ConditionCheckerManager.GetConditionCheckerByConfig` / `0x2884290` | Type 0 resolves to pass-once; Type 19 with the inspected skill string resolves to the skill-finish checker. |
| `ConditionSkillFinishChecker.OnTargetEntitySkillFinish` / `0x2890670` | Interrupted finishes are rejected; the source skill identity must match before satisfying the condition. |

Public normalized references and hashes are in `outputs/hero-report/Hero-Combat-Audit.json`; raw tables, method disassembly and private extraction artifacts are not distributed.

## Model changes

1. **Permanent stat passives:** 16 buff records across 12 heroes: Tony, Layla, Mike, Tithi, Tara, Tarzan, Chiron, Shark, Ragnar, Knotty, Undine and Ken. Only linked unconditional permanent self/team ATK, DEF and HP paths qualify. Percentages follow the selected skill level; level 0 gives zero. Temporary and conditional paths are excluded from this numeric rule.
2. **Team recipients:** individual estimates include their own self/team buff once. Squad scoring adds buffs from other providers to each recipient, using additive percentage factors. This also affects front-line durability and placement. Flat max stats mode omits inferred skill effects.
3. **Rosie's child strike:** the root and checked child each supply a 940 base damage parameter. The pressure proxy includes both, using the larger of root cooldown and the bound uninterrupted root/child animation occupancy. The current unit-speed budget is approximately 3.133 seconds; live modifiers and interruption remain unresolved. Other child references are not automatically added.
4. **Support progression:** qualitative healing/shield/buff weights now respond to level parameters that address real dependencies. Presentation-only rows cannot establish healing, damage or runtime scaling. Rosie's unresolved tooltip-only recovery scaling remains excluded.
5. **Cache integrity:** manifest-verified loose tables now take priority over older packed rows. All 20 progression source tables verified against the current manifest; all 29 heroes' exported progression stayed unchanged. Combat and progression inputs must match both pack and manifest fingerprints.

Fixed reference normalization is regenerated once with the new model. Editing one personal build never rescales unrelated heroes. Upgrade-resource recommendations remain based on configured power/stat gains and actual recorded builds, separate from combat estimates.

## Remaining limits

- Cast scheduling, attack animation duration, projectile travel, interrupts and death times are not simulated. Configured cooldowns are assumed activation budgets.
- Ray's zones and eagle chain, Maddie's summon inheritance, periodic healing and temporary buff stacking/uptime need deeper runtime tracing. A dependency graph alone cannot establish damage per fight.
- Fourth-slot all-stat presentation effects do not yet establish a complete live stat-application path. They do not receive invented numeric combat credit.
- Opponent targeting, line/AoE victim count, low-health crit uptime, research, troop tiers and behemoth contributions can alter a battle without changing an intrinsic hero score.
- Qualitative kit synergy remains a heuristic; the follow-up now excludes explicitly locked and rank-gated skills, although active effects still use qualitative pairing weights. The sensitivity range varies pressure/utility assumptions; it does not cover every missing mechanic or live override.
- Runtime-versus-tooltip discrepancies may reflect different modes, stale presentation data or live patches. Use local runtime rows for this estimate, while preserving the disagreement explicitly.

The supplied reports establish context and outcomes, but one heavily unequal fight cannot identify individual hero coefficients. Further code analysis can still improve conditional triggering, targeting and summon/zone execution without new uploads. For later empirical calibration, the most useful additional sample is repeated fights against the same enemy with identical troops, research, gear and other modifiers, changing only one hero or one skill level; capture the full replay and both sides' Battle Stats, including damage/healing by hero when available.

## Verification

- Python extraction/model regressions: 36 tests, one skipped.
- Selected browser/native suites: 22 passing tests, including 116 real estimate cases, 1,536 formation/support cases, 40,960 faction scoring cases and 60 upgrade cases.
- Native Release build and isolated-profile WPF UI regression pass.
- Offline browser interaction smoke passes: comparison bases, ownership, build persistence, resource returns and mobile layout.

See [full scoring assumptions](HERO-REFERENCE-ESTIMATES.md) and [earlier combat findings](COMBAT-CODE-FOLLOWUP-2026-10-10.md).

## Follow-up refinements: skill availability and PvE economy

- Effective skill IDs now accompany every estimate in both editions. Formation synergy, providers, structural gaps and battle advice use only those IDs. An explicit level 0 or a zero rank cap removes the skill; omitted levels still use the documented capped reference assumption. Switching builds invalidates native mechanic caches. Skill reference cards continue to show the complete kit.
- PvE ranking no longer adds up to 40 arbitrary points per hero for maximum configured Stamina savings. Economy benefits are labeled separately and do not establish fighting strength or a formation requirement. The maximum-value economy label is not a claim about the player's current benefit.
- Tarzan's basic child strike has the same verified Type-19 parent-finish condition as Rosie's, with direct timeline-linked damage. Both base strike coefficients are 210. The root skill's level-30 modifier is 1.29; the child has no matching modifier in that progression row, so it stays at its configured coefficient. Both checked chains now use the nominal root cooldown, following the scheduler correction below. Tarzan's Type-100 counterattack is not counted as guaranteed damage. Other child chains are conditional or have different trigger types and remain unresolved.
- Additional regressions verify all 29 heroes' active skills, 116 native/browser build cases, locked/re-unlocked native synergy, stamina-independent native PvE scoring and locked-skill browser formation advice. Python now runs 37 tests (one skipped); selected Node suites run 23 passing tests. Existing UI/persistence checks still pass.

## Follow-up refinements: periodic and temporary effects

The expanded audit follows child buffs and Type-10 periodic buff effect references with cycle protection. It retains dependency-only effects separately from direct timeline hits. This exposes Layla's child damage-over-time buff and Lava's burn tick without declaring either an unconditional direct hit.

### Timing evidence

- `RaidBuffDotEffect.AddEffect` (`0x28bb220`) reads the configured interval from buff Param1, divides by 1000 and initializes elapsed tick time to zero. It does not grant an immediate tick.
- `RaidBuffDotEffect.OnUpdate` (`0x28bbae0`) calls the base lifetime update before checking whether the buff remains effected. It then accumulates time and dispatches at most one due tick in that update. Large frame steps can therefore lose idealized tick opportunities.
- `RaidBuffBase.OnUpdate` (`0x2897cf0`) requests removal at elapsed time greater than or equal to duration. `RemoveEffect` (`0x2897ec0`) clears the effected flag. Removal scheduling and floating-point/frame boundaries remain reasons not to treat an endpoint tick as guaranteed.
- `RaidBuffDotEffect.OnEffectTriggered` (`0x28bb5d0`) resolves configured effect IDs and dispatches them through the effect system using the buff's source and cached recipient context.
- `RaidEffectSystem.ProcessEffectRecoverHp` (`0x28a2bb0`) resolves effect parameters and calls `SkillDamageCalSystem.CalSkillHeal` (`0x28e2490`). The latter reads source ATK and healing-related recipient/source properties. This supports an Attack-based path for Type-1 recovery; it does not resolve Rosie's separate lifesteal property or prove live effective healing after overheal and deaths.

### Scoring changes and boundaries

- **Lucky:** the root cast applies a 2,500 ms periodic buff with 100 ms interval and a 200-base damage effect. The model uses 24 nominal ticks before the expiry endpoint, instead of scoring one tick as the whole cast. At skill level 1 this is a 4.8 coefficient budget divided by the configured 8-second cadence. This is potential for one recipient that survives the complete buff lifetime, not guaranteed damage, an AoE multiplier or measured DPS. Tick-specific level parameters scale that budget. Tooltip damage rows are excluded.
- **Nikola:** the linked unconditional self ATK buff lasts 5 seconds with a configured 7-second skill cadence. Its 20% factor becomes approximately 14.29% time-averaged ATK under uninterrupted repeated casting. Its actual first-cast delay, availability, interrupts and buff refresh behavior are not simulated. Explicitly locking the skill removes the averaged factor. Unsupported duration overrides are excluded rather than silently ignored.
- **Layla and Candy:** the linked five-second, one-second-interval recovery buffs expose four nominal pre-expiry ticks. These are preserved as recovery evidence, not turned into damage or added as guaranteed effective HP. Target selection, overheal, deaths and the complete heal-property path still prevent a faithful numeric recovery comparison.
- **Lava:** burn application has an unlock condition and repeats faster than its lifetime. The model records its periodic dependency but does not multiply full-lifetime burn ticks by basic-attack frequency. Its separately gated low-health recovery no longer supplies unconditional basic-attack healing utility. Conditional effects need their own availability/uptime model before receiving guaranteed credit.
- `EffectReturnCondition` and `UnlockCondition` are distinct fields. A return-trigger string is not automatically evidence that the initial damage is conditional; existing Becca and Knotty direct effects are not rejected merely for having a return trigger.

The temporal additions remain low-confidence pressure/stat proxies. They do not settle zones, summon inheritance, incoming attacks or full battle scheduling. All 29 heroes retain fixed reference anchors and desktop/browser parity. Upgrade-resource returns continue to use configured recorded-build contributions independently.

Verification after this refinement: 41 Python tests run with one skipped; selected Node suites have 23 passing tests, including 116 native/browser estimates, 1,536 formation cases and 40,960 faction cases. Isolated-profile WPF and browser interaction checks pass; published packages and checksums are refreshed.

## Follow-up refinements: replacement, effect gates and cooldown overlap

Model v5 corrects two scoring assumptions and records further native evidence:

- **Description rows:** the old filter rejected `_text` inside an identifier but missed the `text_` prefix. Lucky, Sarge, Ken, Freja, Travis and Eva consequently received small false damage contributions from description modifier rows. Both patterns are now excluded consistently from damage, generic-pressure fallback and periodic-tick selection. Real stat buffs, shields and summons retain their existing credit. Reference anchors are regenerated; small score changes elsewhere can follow the fixed-anchor update.
- **Cooldown overlap:** `SkillBase.OnUseSkill` (`0x28d46b0`, specifically `0x28d47b8`–`0x28d47c5`) writes the remaining cooldown at cast start, adjusted by the owner's speed factor. `SkillBase.Update` (`0x28d4c90`) can decrement it while release objects update, subject to state/enable guards. `SkillBase.CanUseSkill` (`0x28d33f0`) checks remaining cooldown and conditions. A child skill's 300 ms cooldown is therefore not evidence for adding 300 ms of cast occupancy. Rosie and Tarzan's checked child strikes now use the same nominal root-cooldown rule as other skills: 1 second, rather than the former unsupported 1.3-second sum. This is a pressure proxy, not a measured attack cycle.
- **Unresolved clip duration:** `SkillRelease.PlayReleaseClip` (`0x28ece00`) obtains explicit `LoopTime` when positive, otherwise queries the game-event/model clip length, and adds release waits. `RaidGameEventComponent.GetRaidGameEventLength` (`0x2967980`) can delegate to `RaidModelActor.GetGameSkillLength`. The inspected basic release rows have zero `LoopTime` and timeline `CustomLength`; their last event timestamps do not establish full animation length. Do not replace missing clip duration with a child cooldown or claim scheduler accuracy from this pass.
- **Replacement versus refresh:** `RaidBuffComponent.AddBuff` (`0x28b55c0`) branches on `Plus` at `0x28b582f`. For the inspected `Plus <= 1` path, it removes the first matching buff ID, then instantiates a new buff through the factory. Type-10 `AddEffect` initializes its tick clock to zero. The separate `RaidBuffBase.RefreshBuff` (`0x2897db0`) resets lifetime and condition-trigger count, without resetting the derived tick clock, but that is not the inspected non-stacking reapplication path. This distinction is now retained in periodic evidence. Lava's chance-gated burn cannot be approximated by full-lifetime ticks times attack frequency or a simple proc multiplier.
- **Condition graph:** effect unlock gates, skill conditions and buff effect conditions now retain recursively linked AND/OR dependencies, with cycle protection and target selectors. Lava's Type-40 `[200]` chance, Type-6 `[500]` health threshold, and compound buff-presence conditions remain distinct. `ConditionRandomProbabilityChecker.Init` (`0x2890100`) converts the chance through the per-mille utility; no proc frequency or battle-state uptime is inferred from the graph. Conditional effects still receive no new guaranteed credit.

Raw native artifacts and game scripts remain private. Only selected normalized references and parameters ship with the audit. Live ILFix branches, animation occupancy, successful proc spacing, recipient survival and battle state remain unobserved. No new uploads were required for these corrections.

Verification for model v5: 44 Python tests run, one skipped; 23 selected Node tests pass, including 116 native/browser estimates, 1,536 formation cases and 40,960 faction cases. Isolated-profile WPF and offline browser interaction checks pass. Release publish and RAR integrity checks pass; the published executable matches the fresh build, model regeneration is exact and distribution checksums are refreshed.

## Follow-up refinements: bound animations and repeated immediate hits

Model v6 supersedes the v5 cooldown-only budget where a complete release duration is available. All 29 base models now have an animation audit. The extractor resolves the model's Animator pointer, external serialized-file pointer and override-controller clip pairs, then maps original take names to the exact override clip. Its inputs are the native-build asset index and selected installed-cache bundle list. Selected numeric references and source fingerprints are published in `Hero-Animation-Audit.json`; raw Unity asset trees and animation curves remain private.

### Native timing evidence

- `RaidModelActor.BuildAnimatorOverrideControllerTimeData` (`0x29011c0`) builds a length dictionary keyed by original clip name, using the override AnimationClip length where available. It does not use the last timeline event as an endpoint.
- `RaidModelActor.GetGameSkillLength` (`0x2901c30`) looks up that take and divides the cached duration by the GameSkill speed. `SkillRelease.GetCurGameSkillSpeed` (`0x28ec2d0`) applies a positive configured release Speed as a per-mille multiplier to owner attack speed.
- `SkillRelease.PlayReleaseClip` (`0x28ece00`) prefers positive explicit LoopTime; otherwise the game-event path uses positive CustomLength or the model clip duration. `OnReleaseGoRunning` (`0x28ec900`) scales configured pre/post waits by owner speed. At the model's assumed owner speed 1, waits add directly.
- `SkillRelease.Update` (`0x28ed760`, completion comparison at `0x28ed84d`) checks elapsed time against the total release duration before finishing. `SkillComponent.UseSkill` (`0x28df880`) rejects reusing the same unfinished clipped skill; other eligible skills can interrupt under separate guards. An uninterrupted finish-linked child cannot begin before its parent finishes.
- Base attack speed defaults to 1 in `BasePropertyComponent.get_AttackSpeed` (`0x28c0510`); the SE implementation (`0x29168c0`) reads property 30. The planner does not yet reconstruct live attack-speed modifiers or the complete derived property state.

### Scoring changes

At unit owner speed, the nominal budget is `max(configured cooldown, uninterrupted cast occupancy, minimum cadence)`. Complete configured release chains are summed. Explicit LoopTime/CustomLength and configured release-speed scaling take precedence over a bound clip; missing/ambiguous clips remain unknown. No guessed endpoint is derived from an event timestamp.

Eighteen skill budgets are now limited by animation occupancy. Examples: Rosie's checked basic chain is approximately 1.400 + 1.733 = 3.133 seconds; Tarzan's is 0.800 + 0.800 = 1.600 seconds; Lava's basic clip is approximately 0.933 seconds. These replace cooldown-only proxies, not observed battle intervals. Other skills competing for the same caster, interruptions, deaths, frame boundaries and live speed modifiers can still alter actual cadence.

Six repeated-hit paths also receive a stricter cast-potential budget: Tony's active skill (3 immediate dispatches), Jacob basic (3), Ragnar basic (2 configured releases), Lava basic (2 distinct damage effects), Freja basic (2 configured releases), Tim basic (4). The rule requires an unconditional root, complete duration, literal top-level Immediate projectile hit actions, coverage of every selected direct-damage event and no custom property source. Each event receives its own matching effect-level multiplier. It does not multiply by AoE victims or assume traveling shots connect. Sarge's traveling basic shots and Eva's line projectiles retain representative-effect scoring.

The model remains low-confidence. Buff proc timing, shared cast scheduling, conditional recovery and zone/summon inheritance remain limits; no extra recordings were needed for this pass.

Verification for model v6: 48 Python tests run, one skipped; 23 selected Node tests pass, including 116 native/browser estimates, 1,536 formation cases and 40,960 faction cases. Isolated-profile WPF and browser interaction checks pass. All 29 animation bindings reproduce exactly. Release publish and RAR integrity checks pass; the published executable matches the fresh build, model regeneration is exact and distribution checksums are refreshed.

## 25 October replay evidence and opening-window scenarios (model v7)

The new 115.38-second desktop recording contains two complete replay losses with damage/healing and damage-taken panels, plus other browsed reports. A video fingerprint, rounded transcription, timestamp references and cache drift results are saved in `outputs/battle-reports/Battle-Replay-Evidence-2026-10-25.json`.

| Replay | Friendly / enemy displayed power | Friendly heroes' displayed damage | Separate Griffin damage | Displayed healing |
|---|---|---|---|---|
| First | 10.37M / 24.56M | Rusty 1.10M; Ghost 1.79M; Freja 2.86M; Maddie 5.92M; Lucky 5.24M | 1.22M | Maddie 938.45K |
| Second | 9.06M / 12.50M | Layla 1.98M; Nikola 1.86M; Becca 8.28M; Ray 8.95M; Rosie 6.18M | 2.99M | Layla 298.33K; Ray 104.35K; Rosie 553.38K |

These rounded totals establish what each report attributes; they do not isolate skill coefficients, summons, troop contributions or overheal semantics. Empty healing entries mean no visible green bar. The first replay includes Ghost, supported as internal ID `tim`. The original unsupported-hero note was incorrect and has been corrected in the normalized evidence.

### What the video resolves

- Initial countdowns agree with the configured opening delays: approximately Layla 7 seconds, Becca/Ray 6.3, Rosie 5.6 and Nikola 4.9. Those fields were stored but previously unused in scoring. Both editions now expose optional 10/20/30 game-second opening scenarios. The sustained default remains available and unchanged.
- Complete-cast pressure excludes casts before their initial delay and ticks beyond the selected horizon. Temporary self-stat uptime starts after the opening cast, instead of using steady-state uptime immediately. At level 1, Nikola's opening-10s ATK average is approximately 7.6%, compared with the sustained 14.29%, under the model's completion-time assumption.
- Replay countdowns advance faster than video wall time; no exact playback multiplier is fitted. Grey Rusty/Ghost skill portraits coexist with their visible actors, so HUD availability is not used as an actor death log.
- Rear heroes receive substantial damage. The front pair accounts for about 37% of the displayed cumulative hero damage taken in each loss. This does not refute or calibrate an initial front-exposure prior: final taken totals also depend on HP, mitigation, heals, late targeting and troop state. The existing positional prior is therefore retained, explicitly heuristic.

### Current-client drift check

The installed native build changed from 2.6.200.276 to 2.6.300.293. All 24 requested current-cache tables passed their current manifest hashes, but 18 tables differ from the prior snapshot. Selected existing-hero comparisons found no changes in 114 initial delays, 126 skill-node cooldown/target fields, 359 effect references and 66 linked-buff references. The published evidence records this narrowly: current native method bodies, all progression rows, animations and new heroes were not re-audited, so the old snapshot is not relabeled as current.

### Limits kept explicit

The initial v7 opening scenarios counted independent uninterrupted casts, at owner speed 1, with damage credited at completion. Model v8 below replaces the independent-cast assumption with a single casting slot. Deaths remain unsimulated. Unresolved cast timing retains its previous sustained proxy. Support utility stays qualitative; full-lifetime healing and summon/zone DPS are not invented. Fixed sustained normalization and resource-upgrade returns remain separate. Two unequal defeats cannot fit intrinsic tiers or win probability.

Useful next evidence: repeated fights against the same opponent while changing just one hero or skill; capture both teams' builds/troops/modifiers and both final stat tabs, with a visible replay-speed setting. The existing video is sufficient for this opening-delay refinement; a full current-build refresh and shared-cast scheduling still need code work.

Verification for the 25 October v7 update: 51 Python tests run, one skipped; 24 selected Node tests pass, including 464 native/browser estimate cases across all four windows, 1,536 formation cases and 40,960 faction cases. Native isolated-profile UI checks cover window recalculation, preference persistence and return to sustained scoring; browser interaction/reload checks pass. Windows release and offline packages are rebuilt; RAR integrity, exact model regeneration, published-binary equality and distribution checksums pass. The running desktop app was closed normally for installation; user profile data was preserved.

## 25 October follow-up: current data and shared casting (model v8)

The model now consumes freshly manifest-verified configuration/progression for the same 29 supported hero identities. Twenty source tables pass the current cache manifest. No progression, stat or skill-value changes were found for these heroes. Ghost is supported as `tim`; Kiki is `tithi` and Chef is `ken`. Display names are joined through the exported roster, not treated as internal asset names. A regression covers those aliases.

The current asset index and bundle list were used to resolve all 29 base-model Animator/override bindings again, and to export the fresh 232-asset timeline bundle. Selected combat graphs and clip durations did not change. The animation extractor no longer assumes a fixed template bundle number: current builds renumber it. Missing bound attack clips are now rejected, instead of accepting an empty take dictionary. Alita and Furiosa are present in configuration but are recorded as outside this scoped roster refresh; Alita lacks the expected indexed base model, so new hero support is not silently inferred.

### One casting slot per hero

The opening scenarios now resolve ready unlocked clipped skills against a shared per-hero slot. Configured higher priority wins among ready skills; ties use deterministic slot/ID order. Initial delays remain in force, cooldown readiness starts at cast start, and the entire uninterrupted cast/checked child chain occupies the slot. Skills that become ready mid-cast wait until it completes. This reduces basic attacks available while active skills are casting. A locked skill is removed before scheduling, so it neither deals damage nor consumes casting time.

Per-skill completion times drive the finite direct coefficient budget, remaining periodic tick budget and modeled temporary ATK uptime. Overlapping temporary intervals merge rather than double-count time. Estimate details expose completed cast counts in both editions. Rosie's reference opening-20s scenario completes four basic chains and two active casts; Ghost's completes six basic attacks and two actives. These are inspectable scenario outputs, not fitted replay counts.

The old native `SkillComponent.SortSkillPriority` path (`0x28df3c0`) compares the second skill priority against the first; `GetAIUsableSkill` sorts candidates and tries that order. The prior native cast gate rejects reuse of an unfinished clipped skill and permits other interruption paths. Model v8 deliberately chooses a non-preemptive scenario; it is not an exact implementation of those interruption decisions. The actual method bodies were inspected on build 2.6.200.276. Current selected configuration/assets are refreshed, but the new executable's native semantics and live patches remain unverified, explicitly recorded in the model metadata.

Sustained scores and resource-return rules are preserved. Conditional triggers, summoned actors, damage zones, targeting, movement and deaths remain incomplete. This pass improves short-fight timing consistency without fitting win rates or healing/targeting constants from unequal defeats.

Verification for model v8: 52 Python tests run, one skipped; 26 selected Node tests pass, including 464 native/browser estimate cases with queued cast-count parity, 1,536 formation cases and 40,960 faction cases. Hand-calculated scheduling/overlap cases and locked-active/basic-capacity regressions pass. WPF and browser UI checks pass, including completed-cast evidence. The 29 refreshed heroes retain identical sustained curves and normalization anchors. Native/offline releases, RAR integrity, exact model regeneration, embedded-model equality, current config/animation/combat provenance joins, binary equality and distribution hashes pass.

## Further confidence work: dispatch timing, actor links and validation (model v9)

### Mechanical refinements

Twenty-one direct-damage skill paths now use eligible dispatch offsets rather than animation completion as the damage timestamp. The extractor accepts top-level RaidEvent dispatches and literal Immediate-projectile hit actions, scales release speed, adds pre-wait and preceding release occupancy, and rejects unsupported loop/speed cases. Traveling projectile launches, nested branches and unresolved effects retain their conservative completion fallback. A full per-cast direct budget must be covered and its coefficient sum must match before using the event list.

The shared casting scenario can retain one unfinished cast at the horizon for timing evaluation. Only dispatched events/applications at or before the horizon contribute; completed-cast counts still exclude that unfinished cast. This corrects an omission without granting a full future cast. Rosie's finish-linked child offsets follow the parent duration; Ghost's four immediate basic-hit offsets remain distinct. Nikola's ATK buff is dispatched at 0.5 seconds inside his active skill, rather than at its approximately 1.3-second completion. Periodic tick windows use known application offsets where present; Lucky's traveling Laser application remains conservatively completion-based.

Sixteen actor links now resolve through `pve_new_monster` to configured skills/releases/effects. Ray's basic zone and three active-zone templates each link to their own skill; Maddie's active container and Frank are also mapped. Configured life and stat-inheritance rates are preserved. The old native `RaidEffectSystem.ProcessEffectSummon` resolves `PveNewMonsterConfig`, supporting the table join; its current-build body remains unverified. This is dependency evidence, not a completed summon/zone simulator, and adds no guaranteed actor DPS or target multiplier.

### Confidence measurement

The new `Hero-Model-Validation.json` report joins exact source fingerprints, verifies display-name identities, checks ten rounded opening countdown observations and enumerates per-hero execution gaps. All ten countdown observations are consistent with configured initial delays under the ceiling-display hypothesis. These checks reuse the supplied recordings and are not held-out tests. No win/damage predictions were recorded beforehand, so predictive accuracy and error remain unknown.

The benchmark evaluator separates winner accuracy, damage MAE and positive-observed-damage MAPE. It excludes mechanics/calibration cases, predictions dated after outcomes, missing timestamp/model provenance and wrong-model hashes. A supplied timestamp cannot establish independent provenance on its own; held-out status must be reviewed. This avoids calling implementation parity, graph coverage or a rounded countdown match an accuracy percentage.

### Remaining limits

The installed `2.6.300.293` executable is packed and its metadata header is nonstandard. Its DLL hash differs from the hash-gated older extraction image. The old RVAs/unpacking parameters were not reused or relabeled as current. Current configuration/assets remain verified; current native methods and live patches are still a high-priority gap.

Skill competition remains a unit-speed, non-preemptive scenario. Actual interrupts, actor deaths, movement/targeting, conditional triggers, summon/zone execution, effective healing, troop/research/behemoth interaction and complete stat provenance are not solved. Overall confidence stays low despite the concrete timing improvements. Sustained scores and their normalization remain unchanged.

The next useful measured batch is two lineups with a single controlled hero/skill change, five repeats each against one unchanged opponent, with full build/modifier context and both final stat views. A separate subsequent batch must record predictions before results if it is to measure predictive performance.

Verification for model v9: 61 Python tests run, one skipped; 27 selected Node tests pass, including 464 native/browser estimate cases, 1,536 formation cases and 40,960 faction cases. Partial-cast dispatch, cross-release timing, traveling-impact exclusion, actor-cycle protection, buff onset and benchmark-provenance checks pass. WPF and offline interaction checks pass. Sustained curves and normalization are unchanged from v8. Windows/offline release, RAR integrity, exact model regeneration, embedded-model equality, validation-report reproduction and distribution hashes pass. No overall accuracy percentage or high-confidence prediction claim is made.


## Current native base paths and finish-triggered damage (model v10)

This supersedes the current-native limitation recorded in the v9 section above, only for the selected static paths. The installed 2.6.300.293 DLL and metadata are individually hash-gated. Five independently recovered compressed streams decode to verified lengths and SHA-256 fingerprints without loading the DLL or attaching to the game. Selected method ownership, tokens and field layouts are recovered from the current module. Raw metadata, code and disassembly stay under private tmp directories.

`Hero-Native-Combat-Audit.json` covers 43 method bodies in 16 selected types: cast/cooldown/interrupt gates, release timing, buff lifetime and periodic/delayed execution, damage/heal/summon dispatch, summon initialization, property calculation, finish conditions and one behavior-tree wait action. All 43 have matching normalized instruction shapes against the hash-gated older baseline. Normalization removes relocation-dependent addresses and only patch IDs that flow into identified IsPatched/GetPatch calls. Immediate gameplay constants and memory operand widths are retained; RIP-addressed data require separate comparison. This comparison does not establish equivalence of every call target or referenced data, nor validate active hot patches. The full-runtime reverified flag remains false, accompanied by an explicit selected-current scope.

The current Type-19 finish checker ignores interrupted finishes; an integer selector of 1 selects active skill completion. Type-16 buffs are RaidBuffDelayEffect, not recurring tick buffs: AddEffect resets the timer and fired flag, Param1[0]/1000 sets a nonnegative delay, and OnUpdate dispatches the configured effect once while the buff remains active. Ray's zero-delay eagle buff is linked through this route to active completion. Its old independent five-second damage assumption is replaced with a source-completion dependency: nominal active cadence is nine seconds, so the level-1 single-recipient coefficient pressure becomes 4/9 rather than 4/5. Own skill-level effect modifiers still apply. The passive's five-second cooldown remains an additional gate.

Opening scenarios use completed scheduled active casts, not partial active casts, to admit the delayed effect. A buff update is required, so a source finishing exactly at the window boundary receives no extra delayed hit. Locking either the passive or its source active removes this contribution; locking the source also removes the passive's qualitative recovery credit. Recipient survival/coverage, effective healing and frame-exact buff update order remain assumptions. No extra AoE recipients are counted. Compound conditions, stacking, unsupported modifiers and ambiguous sources are rejected by this narrow rule.

The current normal cast path permits interrupting hero basics, while actives/passives reject that interruption route. A behavior-tree skill action can wait for the current skill. These capabilities do not establish the complete tree's selection/abort policy, so the existing explicitly non-preemptive opening scenario is retained. No guessed preemption frequency is introduced.

Verification for v10: 68 Python tests and 28 selected Node tests pass, including 464 native/browser estimates, 1,536 formation cases and 40,960 faction cases. Source-lock and delayed-trigger boundary checks pass in both languages. WPF and offline UI checks pass. All other hero curves and fixed normalization anchors are unchanged. Release EXE, single-entry RAR integrity, source/audit joins, exact model regeneration, embedded-model equality, validation-report reproduction and distribution checksums are verified.


## Raw healing formulas and property ownership (model v11)

A further current-native trace adds SkillDamageCalSystem.CalPropertySourceValue (44 selected method bodies total). CalSkillHeal's base expression combines caster ATK times EffectParam2/1000, EffectParam3/1000, configured property-source terms and any custom expression before outgoing, incoming and contextual modifiers. The selected property-source path uses source 0 for caster and source 1 for recipient; each selected property value is multiplied by its configured per-mille rate. Custom formulas, unsupported property IDs/owners, malformed arrays, negative coefficients and attribute-fix paths are excluded from the new raw-formula display.

Nine non-presentation healing effect paths can now be expressed as selected raw formulas. At skill level 1, Chef's linked direct heal is 0.15 times caster HP; Frank's heal is 0.05 times recipient HP in the current base code/config. Frank's tooltip instead refers to Maddie's ATK. This is a code/tooltip discrepancy, not proof of live-patch behavior; the displayed path is explicitly conditional and summon-dependent. Layla has separate 2.84 times caster ATK direct and 0.10 times caster ATK periodic-tick formulas. Candy's direct/tick formulas are each 0.67 times caster ATK. Real effect-specific skill-level multipliers scale the relevant coefficient, including indexed property-rate modifiers; description rows remain excluded.

Both editions expose these formulas under Estimate details for the currently selected build, with locks and the source-skill dependency respected. The amounts are per dispatch to one recipient, before modifiers and overheal. Direct dispatch, periodic tick and conditional/summon dependencies are labeled separately. No group-heal recipient multiplier, trigger frequency, summon survival, HPS, effective recovery or ranking weight is inferred. All previous v10 score components and anchors are preserved.

Verification: 70 Python tests and 29 selected Node tests pass, including 464 native/browser comparisons of the raw healing evidence as well as score components. Both UI checks inspect the caster/recipient distinction and informational scope. The release package and offline data are rebuilt and verified separately.
