# Faction effects in formation rankings

Checked 6 October 2026 against the supplied in-game Faction Effect screenshot and the installed client's current downloaded configuration. `game_configs`, `faction_restrain` and `battle_formula_coefficient` matched `BinVersionList_Realtime.json` MD5 identities. Raw extracts remain private in `tmp/faction-audit`.

## Composition

`game_configs.same_unit_type_add_up_desc` matches the screenshot: `2|0.02,2_2|0.04,3|0.08,3_2|0.12,4|0.18,5|0.25`. The last tier is below the screenshot's visible area. The matching counter-bonus description is `2|0,2_2|0,3|0,3_2|0.05,4|0.05,5|0.05`.

The screenshot explicitly says Mariners count as any faction. The planner enumerates valid assignments of each `Sea` hero to exactly one of Mountain, Wasteland or Sky and selects the highest Final Health tier. It never counts the same wildcard in two groups. Unknown faction labels do not count as Mariners.

## Counter scenario and limits

The standard cycle is Wasteland/Rover → Mountain/Stalwart → Sky/Aeronaut → Wasteland/Rover, with +20% damage on a countered target. The faction-restrain table contains no Sea relationship. Sea therefore remains neutral for counter attacks even when it fills a composition wildcard slot.

Enemy target faction defaults to Unknown. A selected target faction applies the +20% counter and applicable +5% composition counter bonus only to standard-faction heroes countering that target, weighted by their offense indices. It assumes their attacks land on the selected faction. It does not simulate enemy composition, individual targeting, incoming counter damage, resistance research, PvP troop formulas or battle outcomes. The UI identifies the setting as a target scenario.

Older `Faction_Ocean` localization mentions per-Mariner ATK/HP modifiers. The supplied current screenshot instead uses `Faction_New_Ocean`, with only wildcard wording. No obsolete per-Mariner modifier is added. Likewise, the older `battle_formula_coefficient.same_unit_type_add_up` list conflicts with the supplied screenshot; the screenshot-matching current display tiers above are used rather than the older list.

## Scoring

Faction bonuses are calculated per candidate squad before ranking and displayed separately from skill synergy. The same calculation drives selected formations and recommendations for additional heroes in both editions.

For reference/recorded estimates, health contribution is the HP component of the existing durability formula: `durability × (0.7 × HP)/(0.7 × HP + 30 × DEF)`. The faction HP percentage changes only that contribution. Its score contribution follows existing objective weights. For flat stats, the change is calculated through the existing 70% min-max HP term; individual displayed hero indices are unchanged. Counter scenarios similarly affect the offense component and follow existing objective weights. These are planning indices, not combat simulations.

## Verification

- Explicit checks for every screenshot tier, five matching heroes, wildcard allocation, input order, unknown factions, counter direction, Sea neutrality and conditional scoring.
- All 1,024 five-slot faction combinations checked for native/browser composition parity, with 40 scoring cases per combination (four modes, two comparison bases, five enemy targets).
- WPF integration verifies that a Mariner completing a five-faction composition is preferred over an otherwise identical four-faction composition and that score components sum to the actual ranking score.
- Native selector synchronization/profile saving, browser target changes and reset to Unknown, existing build/profile controls and mobile layout checked with isolated test profiles.

Live server overrides remain unobserved. The model uses the supplied current screenshot and manifest-matched local configuration; it does not assert measured battle performance.
