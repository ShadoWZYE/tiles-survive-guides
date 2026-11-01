# Pet unlock: installed client 2.6.200.276

Inspected the current installed BinaryConfigPack.ss and the previously extracted offline native RVA image on 2026-10-06.

## Configuration

- `function_pet_system` (23200730): Type 41, Param `15`, dependent function 23200769.
- `function_pet_system_2` (23200769): Type 1, Param `10`.
- `week_card_npp_pet`: also Type 41, Param `15`.
- `pet_unlock_function_open`: `function_pet_system`.

## Native interpretation

`FeatureOpenModule.FeatureTypePass` at RVA 0xC82500 dispatches Type minus one through the table at 0xC836C4. Entry 40 (Type 41) points to 0xC8363F. This branch calls `PlayerModule.GetActivityWeekAndDay` (0x1387840), then compares its low 32-bit week component with the integer configuration parameter, using greater-than-or-equal. Thus the pet requirement is **activity week >= 15**, not day 15 or feature-switch number 15.

`GetActivityWeekAndDay` reads displayWeekNum (offset 184), displayWeekDay (188), and serverGroup (192). It adds one to the displayed week when serverGroup equals 2. `GetRealtimeWeekAndDay` (0x1388760) advances that week/day by elapsed days since RecordEntryGameTime. Its result is a two-int value: week in the low 32 bits, day in the high 32 bits; the constructor at 0x649050 writes those two fields.

Type 1 falls back to `LevelPass`. `GetCurLevelForFeature` (0xC83AC0) resolves Type 1 to `PlayerModule.get_StrongholdLevel` (0x1391AF0). The dependent requirement is therefore stronghold / Power Plant level >= 10. `DependantFeaturesPass` checks the configured FunctionOpens list through IsFeatureOpen.

## Timing limits

The client contains a useful week threshold, but the date depends on its supplied activity calendar and server group. Assuming week 1 starts with the recorded server opening date of 2026-09-02, week 15 starts around 2026-12-09; the group-2 adjustment can move eligibility a week earlier, around 2026-12-02. Calendar alignment can further affect the precise reset. These are conditional estimates, not a verified server unlock timestamp. Native methods also support ILFix hotpatch overrides, which were not evaluated here.

The earlier day-60-to-90 estimate had no code basis and should be discarded.

## Local evidence

- `tmp/pet-unlock-audit/0870_function_open.cfg`
- `tmp/pet-unlock-audit/gate-disasm.txt`
- `tmp/pet-unlock-audit/week-day-disasm.txt`
- `tmp/pet-unlock-audit/week-conversion-disasm.txt`
- `tmp/pet-unlock-audit/int2-disasm.txt`

Shared-RVA method labels in disassembly are not uniquely reliable. The 0x649050 routine was interpreted from its actual instructions, rather than the unrelated alias printed by the probe.
