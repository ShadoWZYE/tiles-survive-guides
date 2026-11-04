# Signature Gear, Behemoth and Research context

Audited 4 November 2026 against the installed downloaded configuration manifest. This is an optional extension to the existing low-confidence hero comparison model, not a complete battle simulator.

## Finding

These systems cannot be declared ranking-neutral. Shared bonuses can sometimes preserve order, but faction/role research and hero-specific Signature Gear can change relative hero scores. Signature and Behemoth battle skills may also change interactions beyond the implemented stat subset.

The planner's existing offense/durability/utility weights are unchanged. The new context changes stat inputs before modeled in-battle passive modifiers; it does not refit weights, renormalize the roster, or claim a measured win-rate improvement.

## Implemented in both editions

Use the hero-local **Signature Gear** card in Hero Stats, Skills or My Roster (also the native build editor), and the separate **Behemoths** top tab. The cards use 45 exact game sprites. Use **Army stat context** for Research and shared settings. Record the sources, enable the context and save. The profile saves the selection. Old profiles default to excluded context and retain their previous scores.

- **Signature Gear:** 21 supported heroes have a level selector sourced from `survivor_exclusive_gear -> survivor_exclusive_gear_main`. Only `BenefitSlg` flat hero ATK/DEF/HP is credited. Each level is the current row, not a sum of all prior levels. This applies only in **My builds**, so personal equipment cannot bias **Equal builds**. The actual owned build can still contain unknown fields and retain reference defaults. Selecting a gear level does not prove the feature or that level is unlocked in the live state.
- **Research:** 147 nodes contain traced flat hero-stat benefits. Record the current level of each researched node. General, role, faction and explicitly selected PvE/GVE restrictions apply. A node contributes only its selected row; prior levels are not added again. Other benefits in that node remain excluded and are flagged in the hero's estimate details.
- **Behemoth:** choose either a manual combined flat **all-hero** ATK/DEF/HP snapshot or configured current level + exact star-progression step. The two sources never stack. Configured mode uses current Front level/star benefit rows once each, without historical levels or Back aliases. Record only Behemoths whose benefits apply to the chosen march/encounter. The star step is a configuration index, not displayed stars; leave unknown steps excluded. Skills, talents and full-skill bonuses remain outside the configured base-stat calculation. Do not enter the Behemoth's own combat stats, total hero stats, or Research totals in the manual fields.
- **Comparison modes:** shared Research/Behemoth stat context applies in Equal builds and My builds. Signature Gear applies only in My builds. Flat max stats ignores the entire context. The encounter selector is independent of the score objective: General/PvP, PvE or GVE.
- **Propagation:** adjusted ATK/DEF/HP reaches the offense/durability estimates, health contribution, passive-recipient contribution, faction health bonus, frontline fit and the squad search. Existing raw upgrade-return/resource-cost panels still compare their named contributions without this external context; they are not context-adjusted investment forecasts.

## Client evidence

Source tables are decoded from entries checked by `verified_tables` against `BinVersionList_Realtime.json`. Source hashes are included in `Hero-Army-Context.json`.

`benefit_calc` links `prop_hero_attack_value` (301825) and `prop_all_hero_attack_value` (301828), with corresponding DEF/HP rows. Role formula rows add the corresponding infantry/cavalry/ranged hero benefits. `benefits_map` aliases faction hero benefits (301992 onward) into the matching faction's role benefit rows. The exporter checks these links. Legacy SE1.5 duplicates are not added on top of SLG hero benefits.

Native `SurvivorDatabaseCell.GetRaidSoldierProperty` calls `ExplorationUtils.GetSurvivorBenefitValue`; that helper looks up `BenefitCalcConfig` and uses `BenefitCalc.RaidBenefitFormulaDouble`. This supports tracing external stat sources into hero properties, but does not prove every live runtime branch or modifier is simulated.

Native `TitanDatabaseCell.GetAllBenefit` (RVA `0x1f3af30` in the inspected image) merges the selected Front level and star `Benefit` fields, with skill/full-skill and talent sources handled separately. `TitanBenefitProvider.GetTitanSeBenefit` iterates the encounter preparation Titan inputs. This supports the selected-row calculation, not automatically crediting every owned creature. The hand-calculated Legendary Griffin (`caser`) level 1 + star step 1 base vector is ATK 1,257 / DEF 252 / HP 83,784. This is a configured subset, not a complete live-account total.

Signature `GearSkillSlg` links are distinct from the flat stat benefit list. Behemoth data likewise contains separate battle-skill groups and own combat properties. Those fields are evidence against assuming the entire system is a common team multiplier.

## Controlled ranking sensitivity

The reproducible sensitivity report compares **individual Balanced hero estimates**, holding reference builds constant under My builds. It does not report complete formation rankings, actual account builds, or observed combat outcomes.

| Scenario | Heroes changing individual rank |
|---|---:|
| Context excluded | 0 |
| Illustrative Behemoth all-hero bonus vector | 0 |
| Configured Griffin level 1 + star step 1, base-stat subset | 2 |
| General ATK Research at level 2 | 0 |
| Selected Mountain Research node at maximum configured level | 27 |
| Rosie Signature Gear at configured level 1, stat subset only | 12 |

The Behemoth sample vector comes from the flat-benefit fields of an inspected client row; it is not a claim that a specific live Behemoth level grants exactly that complete total. The Mountain scenario is a sensitivity probe, not proof the maximum row is currently reachable. Rank movement includes heroes displaced by another hero's improvement. Zero changes in a small shared-bonus scenario do not prove invariance at all account strengths.

## Significant remaining gaps

- Signature linked skill effects and additional gated benefits are excluded; the UI warns explicitly. A stat-only gear result is incomplete, not a full gear ranking.
- Behemoth active skills, direct damage, control, inheritance and own combat stats remain unmodeled. Current level/star base-stat reconstruction is implemented; talents and skill reconstruction are not.
- Troop percentage multipliers, damage modifiers, capacity, conditional battlefield benefits, advanced/alliance Research outside this catalog and actual troop survival are excluded. Faction/role stat bonuses included here do not substitute for those systems.
- Effective healing, overheal, deaths, target selection, runtime hotfixes and server overrides remain uncertain.

## Rebuild and verification

```powershell
python work/hero-extraction/build_army_context.py PRIVATE_TABLE_DIRECTORY --language GAME_LANGUAGE_FILE
node work/hero-extraction/audit_army_context.cjs
python work/HeroPlannerWeb/build_offline.py
dotnet build work/HeroPlanner.Tests
node --test work/HeroPlannerWeb/test_army_context.cjs work/HeroPlannerWeb/test_estimate_model.cjs
dotnet run --project work/HeroPlanner.UiTests
```

Tests cover current-row-only Research, faction/role/encounter gating, unknown/invalid source handling, Signature comparison-basis isolation, stat propagation, unchanged baseline scores, 696 native/browser context scenarios, and profile persistence through both UIs. The audit report is `outputs/hero-report/Hero-Army-Context-Sensitivity.json`.

## Signature runtime audit and unavailable semantics

`Hero-Signature-Link-Audit.json` follows 23 configured level-one gear links (21 correspond to planner-supported heroes) through skill-main/type into the field Lite skill/effect tables. It also records 18 gear-named `effect_buff` rows. Several contain `PhysicalDamageIncrease;0.005;0.001` and `PhysicalDamageReduce;0.005;0.001`; others contain zero operands. These are structured clues, not proof of the interpolation formula, recipients, stacking or uptime.

The inspected Rosie link reaches a Type 11100 effect with no inline magnitude. The linked skill type has no RaidNewSkill counterpart. The gear tooltip describes ATK/DEF increases, whereas the gear-named Lite buff rows describe physical damage increase/reduction. Copying the tooltip percentages into the existing raid proxy would silently mix systems. Runtime marker resolution and parameter interpretation remain **unavailable / not yet verified**; these effects stay excluded. This evidence does not establish a server override. Regenerate with `python work/hero-extraction/audit_signature_links.py PRIVATE_CFG_DIRECTORY`.

## Ownership checkbox repair

The native ownership checkbox previously handled PreviewMouseLeftButtonUp itself, swallowing the release needed by WPF ButtonBase to release mouse capture. It now uses normal CheckBox handling, while its Click event stops the nested click from selecting the hero card. A stale roster drag is also cleared when the left button is no longer held. The UI regression simulates the native capture/pressed state and two routed release sequences, verifies one toggle per click, capture release without Tab, and unchanged squad selection. Both context source selection and saved Behemoth level/star fields are checked through Apply/reopen.

## Follow-up: hero-local controls and deeper gear audit

Both editions now use the same persisted context for hero-local Signature Gear cards and the separate Behemoths top tab. Saving one source preserves all other recorded sources and other heroes' gear. The native and browser Behemoth view uses the full workspace. Client-gated Behemoth entries are labeled with live availability unconfirmed; a selectable row does not prove unlock eligibility.

The expanded Signature audit checks all **360 configured gear levels**: zero contain `GearSkillSlgBenefit` values and zero contain `GearSkillAddition` formulas. Fifteen contain legacy `GearSkillSeOverallBenefit` rows (Rosie's SE ATK/DEF percentages), which do not establish the field Lite formula. The level-one trace covers all 23 configured gear entries; supported hero catalogs expose 21. Context catalog rows now retain the linked Lite skill, effect types and gear-marker-named buff candidates per level, explicitly unscored. The numeric operands are not treated as a confirmed base-plus-level formula.

The client Lua `SurvivorExclusiveGearModule.GetSkillDesc` formats `GearSkillDes` with `GearSkillParam`; it does not compute combat magnitudes. The inspected native survivor benefit path aggregates stored survivor benefits and applies gameplay-scene filters (`SurvivorDatabaseCell.SurvivorBenefitSceneDict`, RVA `0x1f2db10`); this does not reveal the field Type 11100 runtime implementation. No server override or exact runtime buff formula is established by these paths. Verified flat stat support remains enabled; linked skill mechanics remain **unavailable / unverified**, visibly separated from the client skill description.

Additional checks cover hero-local saving, hero isolation, cross-source preservation, source switching, creature/gear icon decoding, Behemoth tab navigation and restoration of the hero roster, profile persistence, and phone-width browser layouts. `test_army_context_ui.cjs` is the reproducible browser UI regression. `extract_context_icons.py` exports the exact referenced Sprite assets from matching asset-index/bundle-list revisions; it fails on missing assets. No raw game code or user profile is published.
