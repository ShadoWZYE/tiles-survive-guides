# Faction Star Talents: implementation and evidence

The supplied screenshot matches the client's Hero Faction Talent feature. This establishes availability for the account shown, not a universal release date. The planner now exposes all three branches, 24 nodes and 72 level rows in both editions.

### Reported 39 / 28 / 26 point case

With Stalwart basic stats at 3/3/3, Rover at 3/2/3 and Aeronaut at 3/3/3, the guidance is:

- Stalwart: Firepower Burst Lv 1 costs 3 of 9 available points; its configured troop attack bonus is +0.5%.
- Rover: Armor Boost Lv 3 costs 4 points, with 2 available. Save 2 more. Completing it unlocks Firepower Burst because Endurance Boost is already at Lv 3.
- Aeronaut: Firepower Burst Lv 1 costs the 2 available points; its configured troop attack bonus is +0.5%.

These are separate point pools. The two troop bonuses are displayed from config and remain outside the numerical hero-only score.

## Quick recording

The selected-node inspector has +1 level and −1 level buttons. These immediately save the planner record, update available points and recalculate recommendations. One level may cost multiple Star Points; the + button shows the exact next-row cost. Total earned points are never decremented. Removing a recorded level releases that row's cost in the available-point calculation.

Adding requires a known sufficient faction budget and completed prerequisites. Removing a prerequisite level is blocked while a purchased dependent needs it. Invalid totals, maximum/minimum levels and invalid draft selections disable the relevant action. The existing dropdown and Save button remain available for entering a complete historical build. Quick recording does not perform an action in the game.

## What enters the model

The first three nodes of each branch provide additive **all-hero** ATK, DEF and HP. Their benefit IDs are 301828–301830. The current `benefits` names and `benefit_calc` ValueParam references are checked during export. Purchased current-level values enter the existing external-flat-stat path before passive percentages. The planner does not add all historical level rows together, multiply a node by squad size, or restrict these global bonuses to the faction that paid for them.

At level 3, each branch grants +2,100 ATK, +420 DEF and +140,000 HP. Buying all three nodes costs 30 points in Mountain/Wasteland, 24 in Sky. Those are separate currencies. All three branches' verified additive stats can stack. With every basic stat node purchased, the combined contribution is +6,300 ATK, +1,260 DEF and +420,000 HP per hero.

Recorded values feed hero ranking, squad scoring and optimization through the same stat path as other account bonuses. My builds and Equal builds use identical combat rules. The existing Max heroes/no gear mode intentionally excludes account context. Unrecorded nodes and unspent points supply no bonus.

## Tree interface

Both editions display the in-game arrangement: Rover above the central faction emblem, Stalwart down-left and Aeronaut down-right. Exact client icons, faction colours, prerequisite connectors and current levels identify nodes. The tree fills the available desktop viewport; +/− controls and the mouse wheel zoom from 50% to 300%, dragging empty space pans, and Fit recentres the entire tree. Navigation does not alter purchased levels. Mouse/pointer capture is released when dragging ends, is cancelled or the view is unloaded. Selecting a node opens a single inspector, leaving the tree visible. Stalwart fork coordinates are reflected to match the supplied in-game reference: defense is above-left of health, including the troop-stat pair. Rover and Aeronaut retain their existing orientation; benefit identities and prerequisites are unchanged.

The best affordable **scored** next upgrade in each independent point pool receives a gold glow and a NEXT badge. Once no scored option remains, affordable non-conditional nodes continue as explicitly labelled **progression guides**, following node unlock order rather than an invented combat ranking. Their declared benefit is displayed without a numerical hero-score gain. The matching recommendation button opens that node without purchasing or changing its recorded level. The white outline identifies selection, not a recommendation. Up to three gold markers can appear, one for each known faction point pool. Blank totals explicitly ask the user to fill the point cards. Badges update when points or purchased levels change; missing totals, unmet prerequisites and invalid edits cannot receive an affordable NEXT marker. An unaffordable legal next level has a blue SAVE badge and names the target, exact shortfall, total cost, currently available points and any newly completed unlock. Saving targets use the smallest shortfall, then unlock order. Conditional capstones with conflicting client rows receive REVIEW guidance rather than a spending recommendation. Unverified effects are never promoted to a scored recommendation.

## Configuration and recommendations

- Enter the game's **total** earned points, not remaining Available points. Blank totals stay unknown; no affordability recommendation is made for that branch.
- Record purchased node levels. The exporter preserves exact per-level costs and PreliminaryId prerequisites. Earlier prerequisites still matter when recording a higher level, even if that higher row has an empty prerequisite array.
- A save rejects missing prerequisites and a recorded spend above a known point total. Invalid imported branch selections contribute no stats. Other valid branches remain usable.
- Recommendations group branches separately because faction currencies cannot be exchanged. Within each branch they compare affordable, legal **next-level** upgrades by change in the selected squad's mean hero score per point. This is a local marginal comparison, not a globally optimal full-tree spending plan or predicted battle-damage percentage. Unknown-effect nodes are shown separately as unscored, not asserted to be worthless.
- The client Lua counts completed ranks of eligible owned blue/purple/orange heroes and excludes replaced/hidden and X heroes. Small-star steps do not create another point. In-game totals remain authoritative; the planner does not calculate an account total from an incomplete roster or assume a server point conversion.
- Talent table hashes participate in account revalidation; blank unlocked talents are listed in the account-data notice. Settings persist with the rest of the profile, including through the advanced account editor and restart. Nothing from the user's screenshot is silently applied to their saved account.

## Effects deliberately not converted into invented hero strength

Nodes 4–6 contain troop ATK/DEF/HP percentages. These are retained with descriptions, costs and prerequisites, but the hero-only model has no verified troop damage/health allocation engine. Applying those percentages directly to hero stats would conflate two different quantities.

Node 7 contains damage-reduction or offensive modifiers whose runtime application is not established by the stat-only interface. Node 8 is more problematic: its generic Benefit rows conflict with its conditional description. For example, Stoneclad Resolve describes hero defense gained as health is lost, but its Benefit row supplies `prop_physic_defense_reduce_percent`. Some localization parameters are inconsistent as well (a fractional value is substituted into a count-of-stacks placeholder). SkillId is empty. These are not sufficient grounds to invent a trigger, recipient, uptime, critical formula or stacking rule. Such rows remain visibly excluded from numerical scoring.

This change adds known account stats. It does not close the separate world-battle calculation bridge or establish a new independent prediction-accuracy percentage.

## Reproducible sources

Raw game files stay private. `build_faction_talents.py` consumes manifest-verified decoded extracts of `hero_faction_talent`, `hero_faction_talent_branch`, `benefits` and `benefit_calc`. Their SHA-256 values are stored under `faction_talent_source_hashes` in the normalized context catalog; the older Signature/Research/Behemoth provenance is preserved separately.

The tables were extracted using `refresh_hero_data.verified_tables`, which checks the current `BinVersionList_Realtime.json` and prefers matching loose binary patches over packed rows. Lua evidence: `HeroFactionTalentModule.GetHeroTalentPoints`, `GetBranchTotalPoints`, `GetBranchAvailablePoints`, `IsNodePrerequisiteMet`, `GetPropertyPreviewData`, and `HeroFactionTalentDataUtil.GetActivatedTalentIds`. Preview code counts only the current purchased row and explicitly excludes large-talent Benefit rows from its flat-property merge. Preview code alone is not proof of the excluded conditional combat mechanics.

Run the faction exporter after the base context exporter when rebuilding the complete catalog. Exact icon assets are exported with `extract_context_icons.py --talents-only`; no substitute artwork is used.

## Verification

Native/browser numerical tests cover cumulative current-row values, all-faction scope, separate budgets, invalid/locked/unrecorded selections, full-tree placeholder exclusion, marginal recommendations and identical max-build scores across comparison modes. UI tests cover all 24 nodes and their icons, prerequisite rejection, saved levels and totals, restart, and preservation through the advanced context editor. Existing scoring, context, formation and UI checks are also rerun. Test profiles are isolated from the user's real profile.
