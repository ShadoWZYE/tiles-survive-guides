# Planner refinements — 7 November 2026

## Measured damage reconstruction

The production offense index is a ranking proxy, not a damage simulator. Its one-scale fit to the five recorded hero rows remains 25.1% weighted absolute error. A new equally small probe, **known ATK × observed survival time**, improves that reconstruction:

| Same-fight diagnostic | Fitted WAPE | Worst hero | Internal leave-one-owner-out WAPE |
|---|---:|---:|---:|
| Production offense index + one shared scale | 25.1% | 64.2% | 30.3% |
| Known ATK × observed survival time + one shared scale | **16.1%** | **28.6%** | **22.1%** |

The broad earliest/latest presentation intervals give 14.8–18.7% fitted WAPE for the new probe. These are scenario results, not confidence bounds. Its midpoint predictions are Rosie 2.993M, Freja 2.974M, Becca 8.412M, Maddie 10.506M and Ray 6.592M. Ray remains the largest residual, 28.6% below his displayed output.

Both probes fit one shared multiplier; there are no per-hero correction factors. The new probe uses survival observations from the finished fight, so it is not an independent future-fight prediction. General ranking weights remain 55% offense, 35% durability and 10% utility. The useful finding is that exposure matters and the current Raid coefficient feature does not yet explain the field report reliably. A two-component ATK/exposure fit puts zero weight on ATK and returns the simpler lifetime control; it does not identify a soldier-damage fraction.

The new catalogue audit follows the separate field links for the five heroes' 20 skills. Their selected linked Lite effects have Type 11100 and zero `EffectAttrRate`. The linked row therefore does not supply a verified numerical damage formula. `RaidNewSkill` is a separate link. This narrows the missing bridge; it does not prove there is no calculation elsewhere or justify copying Raid animation coefficients into world combat.

[Detailed reconstruction](RETROSPECTIVE-RECONSTRUCTION-2026-11-07.md) · [Complete measurements](../../outputs/hero-report/Retrospective-Damage-Reconstruction.json)

## Research and Behemoth catalogue corrections

- Legacy research is removed from the supported catalogue, picker and calculation inputs. Old unsupported selections are excluded during profile cleaning.
- Stalwart Power, Rover Power, Aeronaut Power and Might of the Ocean come from `research_tree` entries 4300013–4300016. Their `ShowUnlock` feature gates and prerequisite count of 118 learned research entries in Special Forces are separate from the visible Heroes branch. The checked static `CanShow` method calls `FeatureOpenModule.IsFeatureOpen` with that gate; it does not establish the live server's gate state. These branches are hidden by default and available only through an explicitly labelled gated-client option. Users should record them only if they can identify them in-game.
- The normal Behemoth catalogue contains **Legendary Griffin** (`caser`) and **Tidal Drake** (`water_dragon`). The extra `griffon_eagle` record reuses Drake's name/icon keys and has a 99999-day gate. It is excluded rather than merged or counted twice. Blazing Reaper also has that gate and is excluded. No future release date is established.

## Star fill, configuration notices and score readability

The extracted `p_titan_star` prefab sets all five overlays to Radial360, origin 1 and counter-clockwise. For Radial360, Unity's origin 1 means **Right**, unlike its Radial180 enumeration. Both planner editions now start their partial Behemoth fill at the right and retain the client's six steps per star and thirty steps per colour. The numerical interpretation was checked against [Unity's Image source](https://github.com/Unity-Technologies/uGUI/blob/main/com.unity.ugui/Runtime/UGUI/UI/Core/Image.cs).

Squad Builder now shows a compact notice for incomplete hero data and omitted account context. Expanding it lists missing rank/step, level, eligible skill levels and gear, with direct build-edit links. Account bonuses remain optional: unavailable or unowned bonuses should stay blank and receive no benefit. Maximum reference comparisons are identified separately from personal My builds recommendations.

Scores are **not capped at 100**. They use fixed reference anchors and logarithmic skill compression. Hero cards now show two decimal places and their percentage model-score gap from the roster leader; details show the offense/durability/utility components and their weights. A score gap is not a measured strength, damage or win-rate percentage. No cosmetic rescaling or new combat coefficient has been introduced.

Windows navigation buttons now use consistent spacing, including the later Research, Behemoths and Army Setup buttons.

## Restart persistence

Two Windows planner instances were observed using the same profile. Each held its own in-memory copy, allowing a stale instance to overwrite newer saved settings. The application now allows one instance per Windows session and brings it forward on relaunch. Saved comparison basis, active army, formations and army modes are checked across restart. This addresses an observed overwrite route; it is not proof that every previously reported reset had that cause.

Existing personal builds and supported context are preserved. Removed legacy/unavailable catalogue selections are excluded rather than credited to another source. Private pre-update backups are retained locally.

[Catalogue/native/prefab audit](../../outputs/hero-report/Planner-Catalog-Audit.json)
