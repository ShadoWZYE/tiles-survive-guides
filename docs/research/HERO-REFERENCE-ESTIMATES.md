# All-hero reference estimates

This deliberately low-confidence inference model covers all 29 supported base
heroes without personal build input. The native Windows and offline browser
planners display one compact **Est.** score. Per-hero assumptions, basis and
scenario range are hidden under **Estimate details**, collapsed by default. No
mandatory build inputs or save buttons are required. One compact comparison-basis
selector keeps personal progress separate from fair comparisons:

- **Equal builds · max T5** (default): maximum configured hero level and rank, every skill at its available cap, and the same three-piece yellow T5 Alloy set at maximum gear level. Saved personal progression is ignored. Enabled Research/Behemoth context can apply; Signature Gear remains My builds only.
- **Max heroes · no gear** (stored profile key `flat`): the same maximum hero level, rank and skills, with no gear or account context. It uses the same skill-aware score, faction and frontline calculations as Equal builds.
- **My builds** (opt-in): only recorded upgrades count. Missing rank uses the first base rank, missing hero level uses 1, and unrecorded or locked skills and gear grant no upgrade bonus. Partially recorded heroes remain eligible.

The selected basis is saved separately; existing profile keys remain compatible.
Resource priorities independently use recorded builds of owned heroes only;
comparison defaults are never written into observations or used to record an upgrade.

## Maximum and personal data

As of the 2.6.400.304 data, maximum base-hero development is level 165 and rank 10 step 6. Skill caps are resolved per hero and slot from the available data (up to 40 for standard skills, with separate caps for fourth skills). The standard yellow T5 set is Alloy Helmet, Alloy Armor and Alloy Greaves, each at level 80. These are universal equipment pieces; Signature Gear, refinement and unsupported exclusive effects are not invented as part of this set.

Both maximum modes use this same hero development. Their deliberate difference is gear and account context. This is equal specified development, not equal resource expenditure. Normalization anchors now use the maximum T5 reference roster, so index values differ from the former level-110 reference version; the change is not a game buff or nerf.

Basis labels distinguish Max heroes, no gear; Equal max T5 build; Recorded + base defaults; and Recorded build. Even a fully recorded build retains low confidence because combat mechanics are incompletely modeled.
Every unowned/unrecorded hero remains in the candidate pool subject to existing
access/ownership filters. Changing a build does not re-normalize unrelated heroes.

## Inputs and assumptions

`build_estimate_model.py` consumes the manifest-verified combat dependency audit,
progression dataset and roster from the same pack and manifest fingerprints. Manifest-verified loose cache tables take precedence over older packed rows. For each skill it
prefers non-text **Type 0** effects explicitly referenced by timeline hit events,
falling back to the strongest dependency effect when the direct path is unresolved.
Empty/stat-presentation effects never provide healing or pressure credit. This includes both `text_...` prefixes and `..._text...` identifiers: six heroes previously received false pressure from description-only modifier rows. Real stat and support paths remain separate. Damage
zones are not credited as summoned allies; recognized lifesteal retains qualitative
healing utility. Version 9 records selection basis, zone/summon dependencies, permanent stat buffs, checked child strikes and unverified execution for every skill. It retains a representative effect for unresolved paths. Where every selected direct-damage event is a literal top-level immediate projectile, the root is unconditional, the cast duration is bound and the effects have no custom property source, it counts those dispatches as single-recipient potential. Six multi-hit paths qualify. Traveling and nested projectile paths retain the representative rule. Rosie and Tarzan also include their checked non-interrupted finish-linked child strikes. Target count and actual hit success are not inferred.
It applies the matching numeric effect-param2 level multiplier and divides the
base parameter by 1000. This supplies an input for a **representative-effect
pressure proxy**, not damage dealt. Multiple rows are not blindly added together. Lucky has a separately linked non-overlapping periodic damage buff: its pressure budget uses nominal pre-expiry ticks, assuming one recipient survives the full lifetime. Conditional or overlapping burn paths are not multiplied into guaranteed cast damage.
Type 1 healing rows are not classified as damage because of their names.

The selected skill's configured cooldown supplies an assumed activation cadence;
zero cooldown uses a 2-second basic / 12-second other-skill prior. Minimum assumed
cadence is 0.5 seconds. Base-model animator references now bind override clips for all 29 heroes. The budget uses the larger of configured cooldown and uninterrupted release occupancy at owner speed 1, including configured waits, explicit loop/custom-length precedence and positive release-speed multipliers. Native cooldowns begin at cast start and overlap casting. For Rosie and Tarzan, the budget includes both root and finish-linked child clip durations, rather than adding child cooldowns: approximately 3.133 seconds and 1.600 seconds respectively. Eighteen skill budgets are animation-limited under these assumptions. Skill competition, interruption, live speed modifiers and frame rounding are not simulated. A complete cast scheduler, effect inheritance, flight time,
target count, traveling-projectile multi-hit behavior and zone ticks are not simulated. If unresolved effects
leave pressure unknown, generic priors are 0.25 basic / 0.08 other. Known non-damage
effects do not receive that pressure prior unless additional dependencies remain
unresolved. These priors are deliberate uncertainty handling, not game facts.

Utility is a qualitative, dimensionless planning weight: healing 1.3, shield 1.2,
stun 0.8, slow 0.35, ATK reduction 0.6, DEF reduction 0.8, damage reduction 0.9,
summon 0.6, based on effect types and identifiers/descriptions. Each tag contributes
once per skill. These magnitudes and application rates are **model assumptions**, not extracted combat values. Where a numeric level modifier addresses a real healing, shielding or buff dependency, the qualitative weight scales with that modifier. Tooltip-only parameters do not establish runtime scaling. An absent tag is
not proof that a hero lacks additional utility. AoE and conditional uptime remain
unresolved. Stamina economy is excluded from combat scoring. Qualitative mechanic pairings are informational; their former extra score was removed to avoid duplicate utility credit. Numeric permanent team stat buffs remain scored. My builds assigns no benefit to unrecorded or locked skills. PvE farming ranks modeled Stamina saving first and then combat strength; economy does not inflate combat scores.

## Permanent stat buffs and formation recipients

Sixteen linked permanent ATK/DEF/HP buff records across 12 heroes now supply explicit self/team percentages. Only unconditional pass-once roots with verified self or whole-team targeting, permanent non-stacking property buffs and matching real parameter paths qualify. Temporary buffs, conditional buffs and presentation rows are excluded from this numeric path.

Native property arithmetic adds percentage factors before multiplying the recipient's base stat. Individual estimates include the hero's self buffs and its own team buff once. Formation scoring adds each other provider's team buff to the recipient, excludes the recipient's already-counted provider, and uses those adjusted DEF/HP contributions when choosing the front two. Multiple providers add rather than multiply. Numeric team stat credit is separate from the cap on qualitative synergy. Existing faction bonuses retain their separate Final Health policy; the complete interaction with live battle properties is not simulated.

Layla's level-30 HP path exposes a client discrepancy: the runtime buff supplies 12.9%, while its tooltip counterpart supplies 25.8%. The model uses the linked runtime row and flags the discrepancy rather than copying the guide's roughly 26% claim. This does not establish what an unobserved server/hotfix executes. Maximum-mode skill caps now follow each hero’s maximum available rank and skill rows.

See [guide cross-check and native evidence](HERO-GUIDE-CROSSCHECK-2026-10-11.md).

## Temporary stat timing

Nikola's linked self ATK buff uses a steady-state duration/cooldown assumption: 20% multiplied by 5/7, approximately 14.29% average ATK. It is included in the effective self stat factor, not counted as permanent or always fully active. First-cast timing, interrupts and death are not modeled. Periodic heal tick budgets are recorded as evidence; effective healing is still qualitative. Explicitly gated recovery does not receive unconditional healing utility.

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

## Buff reapplication and effect gates

The audited non-stacking Type-10 buff path removes a matching buff ID and creates a fresh object. Its tick accumulator starts at zero. It is not the separate base `RefreshBuff` method, which resets lifetime without resetting the derived tick timer. Periodic budgets now retain this replacement policy. Repeated applications can postpone ticks; a configured 20% burn proc chance does not mean 20% of the full-lifetime damage on every attack. Frame timing, targeting and successful application spacing remain unresolved.

The selected condition graph includes nested AND/OR dependencies and both target selectors. Lava's burn chance (`200` per mille), low-health gate (`500` per mille) and compound buff-state gates are preserved separately. Conditional effects receive no new guaranteed damage or recovery credit in this pass. The raw graph supports subsequent conditional modeling without guessing uptime.

## Animation provenance and immediate-hit potential

`Hero-Animation-Audit.json` retains only named base-model/controller bindings, selected take names and clip durations, plus source fingerprints. The audit resolves each model Animator to its exact external AnimatorOverrideController and matches original clip names to overrides through serialized file/object references. It does not select the shortest clip or guess from a hero name. Sarge's bundle includes zombie animators; the hero animator is selected separately, so summoned animations do not become his attack duration. Raw curves, meshes and controllers are not distributed.

Repeated immediate-hit budgets currently cover Tony's active skill (three dispatches), Jacob's basic (three), Ragnar's basic (two configured releases), Lava's basic (two distinct effects), Freja's basic (two configured releases), and Tim's basic (four). Matching effect-specific level modifiers apply to each dispatch. This is potential during a complete uninterrupted cast, for one surviving recipient per dispatch; there is no AoE victim multiplier or simulated accuracy.

## Opening-window comparisons (25 October recording)

The Battle window selector defaults to **sustained**, preserving existing comparisons. Opening **10, 20 or 30 game seconds** supplies an optional short-fight scenario in both editions; it is independent of Equal builds/My builds. Both maximum modes now apply it. The profile saves this preference separately from build observations, and fixed sustained anchors use the maximum T5 reference roster.

For resolved unconditional clipped paths, the opening scenario uses one casting slot per hero. Skills become ready after PreCooldown, the highest configured priority among ready skills takes the slot, and its cooldown starts at cast start. A complete cast or checked root/child chain occupies the slot without interruption; the next skill waits. Ties use stable slot/identifier order as a planner rule. Known direct-dispatch and literal Immediate-projectile events now supply damage at their timeline offsets, including events in an unfinished cast. A periodic budget receives only nominal ticks that fit after its known application offset; unknown application/impact times keep the conservative completion fallback. Release waits, positive release-speed scaling and earlier releases are included in offsets. Looping, unsupported timeline speeds, nested actions and traveling projectile launches do not establish exact impacts. It is not a frame simulation. Unresolved cast paths retain the sustained proxy, rather than acquiring invented timestamps. Locked skills remain zero.

Nikola's temporary self-stat path also honors its opening delay. The linked unconditional ATK buff dispatches 0.5 seconds into the active cast; the model integrates covered intervals from that offset instead of granting sustained uptime from time zero. Unknown buff application times keep the completion fallback. Permanent buffs and qualitative utility weights remain unchanged. No new guaranteed healing, death-time or incoming-damage model is fitted.

The supplied 25 October recording has two complete loss replays with both final stat views, and additional browsed reports. Rounded per-hero damage/healing and damage-taken values, source timestamps and video fingerprint are preserved in `outputs/battle-reports/Battle-Replay-Evidence-2026-10-25.json`. Opening countdowns support the stored initial delays. Replay time visibly advances faster than wall clock, so video seconds are not used directly as game seconds. Grey skill portraits coexist with visible actors and do not establish actor death.

The shipped 29-hero configuration/progression and asset bindings are now refreshed from the installed `2.6.300.293` native build and selected current cache. All 20 progression source tables pass the current manifest; all supported heroes retain the same progression/stat/skill values. The fresh timeline bundle has 232 assets, and the selected combat graph and bound clip durations match the prior audit. The v8/v9 native trace used `2.6.200.276`; model v10 now re-audits 43 selected static base paths on `2.6.300.293`. Complete runtime and live hot patches remain unverified. Ghost is already supported as internal slug `tim`; the initial unsupported-hero note was wrong. Alita and Furiosa appear in the refreshed config and are recorded separately pending full supported-asset/mechanic validation.

## Shared casting slot (model v8)

Opening 10/20/30-second scenarios now schedule selected, unlocked, unconditional clipped skills on one caster lane. Active casts reduce basic-attack opportunities instead of letting both run independently. The planner uses configured priority, initial delay and existing uninterrupted animation occupancy; an unfinished cast receives only eligible timeline-dispatched hits/applications before the endpoint; unknown impacts keep the completion fallback. It does not preempt a basic chain when an active skill becomes ready. Zero-duration/no-clip, conditional and unresolved paths keep their previous independent/fallback treatment. These are stated scenario assumptions, not a recovered complete AI scheduler.

Finite damage and periodic tick potential use scheduled cast starts plus eligible dispatch offsets, falling back to completion for unknown impacts. Nikola's modeled temporary ATK uptime integrates intervals from its linked dispatch, merging overlaps. Locking a skill removes its queue occupancy and buff contribution. Permanent buffs, qualitative support utility, sustained scoring and resource-upgrade returns remain separate. The per-hero Estimate details list completed cast counts so the scenario can be inspected.

For example, Rosie's reference opening-20s scenario completes four basic chains and two active casts, rather than six independent basic chains plus two independent actives. A fifth unfinished chain may contribute its first timestamped hit before 20 seconds, without being counted as a completed chain. This is not a claim about her measured replay DPS. No actor deaths, movement, target changes, interrupt decisions or live attack-speed modifiers are simulated.

## Evidence validation and remaining execution gaps (model v9)

Twenty-one direct-damage paths have eligible timeline dispatch offsets. Known full-cast coefficient sums are preserved; this update changes opening timing, not sustained normalization. Positive skill-level multipliers apply per event. The selected event list must cover the complete modeled direct coefficient budget before it replaces completion-based scoring. No extra AoE victims, conditional hits or unverified projectile impacts are added.

The dependency audit also follows Type-7 actor templates through the current manifest-verified `pve_new_monster` table to their configured skills, child skills, releases and effect references, with cycle protection. Sixteen actor links are mapped, including Ray's stationary zone templates, Maddie's arrow container and Frank. Configured lifetime and ATK/DEF/HP inheritance rates are retained. These links remain inventory-only: AI triggering, recipients, inherited live properties and target coverage do not become guaranteed damage. The prototype actor's configured flat ATK is not substituted for the summoner's actual ATK.

`python work/hero-extraction/validate_model_evidence.py` regenerates `outputs/hero-report/Hero-Model-Validation.json`. It checks model/data provenance and roster identity, lists per-hero resolved timing and important execution gaps, and checks ten rounded opening-HUD countdown observations against the configured initial delays. All ten satisfy the ceiling-display interval hypothesis. These are in-sample mechanics-consistency checks; they do not measure winner prediction, damage error or ranking accuracy.

Prediction metrics remain unknown (`null`) until eligible held-out records exist. The optional benchmark records use `evaluation_role: held_out`, an `outcome` of win/loss, `outcome_recorded_at` with timezone, and a `prediction` containing outcome, numeric per-hero `damage`, `recorded_at` and the exact model SHA-256. Numeric observed damage belongs in `damage_observed`, using the same unit and hero IDs. The predictor timestamp must precede the outcome timestamp and the model digest must match. Calibration/mechanics cases and retroactive/wrong-model predictions are excluded. Provenance still needs independent review: timestamps supplied in a file are not proof against fabrication. Win accuracy, damage MAE and positive-actual-damage MAPE are reported separately; there is no manufactured overall percentage.

A useful calibration batch is two lineups differing in one hero or skill, five repeats each against the same enemy with unchanged troops/tier, gear, research, behemoth, collection and buffs. Record both teams' builds, the full replay with visible speed, and both final stat tabs. Use a separate later batch for predictions recorded before seeing outcomes. Even complete combat-input records cannot by themselves resolve every live-server override.


## Source-completion dependencies and current native audit (model v10)

The current hash-gated executable and metadata now support a selected 43-method static audit, linked by SHA-256 through combat data, estimates and evidence validation. All 43 normalized base instruction shapes match the prior baseline, with relocation addresses and identified patch IDs masked. This is selected-path evidence, not complete runtime verification; the full-engine reverified flag remains false. Raw code/metadata/disassembly are kept private.

Ray's eagle damage is a one-shot Type-16 delayed buff following a Type-19 active-finish condition. It no longer receives an independent damage activation every five seconds. The nominal sustained single-recipient budget follows active completion (nine-second source cadence), subject to the passive cooldown. Opening windows admit the effect only after a completed scheduled source and a buff update; an in-flight or exactly-at-endpoint active receives no delayed hit. Either skill being locked suppresses the dependent damage. Source locking also suppresses the associated qualitative recovery credit. Skill-level coefficients still scale normally; no AoE victim count or effective-healing amount is inferred.

The current normal interrupt gate permits interrupting a hero basic and rejects interrupting active/passive casts through that route. The complete behavior-tree abort policy is not recovered, so the opening scenario remains explicitly non-preemptive. This evidence does not justify a guessed live interruption rate or a higher empirical accuracy percentage.

Verification for v10: 68 Python tests and 28 selected Node tests pass, including 464 native/browser estimates, 1,536 formation cases and 40,960 faction cases. Source-lock and delayed-trigger boundary checks pass in both languages. WPF and offline UI checks pass. All other hero curves and fixed normalization anchors are unchanged. Release EXE, single-entry RAR integrity, source/audit joins, exact model regeneration, embedded-model equality, validation-report reproduction and distribution checksums are verified.


## Raw healing evidence (model v11)

Estimate details now show nine selected raw healing formulas with actual skill-level scaling. They distinguish caster ATK, caster HP and recipient HP and identify direct dispatches, periodic ticks and conditional/summon dependencies. The current native audit covers 44 selected bodies, including property-source ownership. At level 1, Chef's selected heal has a 0.15 caster-HP term, while Frank's has a 0.05 recipient-HP term. Frank's tooltip describes Maddie's ATK instead; this code/tooltip discrepancy remains subject to live patches.

These formulas apply per dispatch to one recipient before outgoing/incoming/contextual modifiers and overheal. They are informational and grant no extra ranking credit. Unknown expressions, unsupported property mappings, malformed arrays and attribute-fix paths are excluded. Locked skills give no raw preview; Ray's dependent recovery preview also disappears if the source active is locked. Existing damage, utility weights, reference anchors and rankings remain unchanged from v10. Effective healing, target counts, health deficits, summon execution and HPS remain uncalibrated.
