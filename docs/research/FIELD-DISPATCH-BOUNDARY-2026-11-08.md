# Field calculation boundary — 8 November 2026

The original field/Lite calculation is the priority for predicting the supplied world-battle reports. “Bridge” describes the **unverified connection between field effects and the Raid model**, not a client function that has already been located.

## New evidence

- Exported and searched all **11,354 UTF-8 Lua sources in 53 bundles** indexed by asset snapshot 2.6.400.312. No source was missing or Lua bytecode. The searched field-effect symbols produced no matches. Exact numeric `11100` also occurs as unrelated configuration data; that is not an effect handler.
- Enumerated **11 direct native call/jump references** to the two field skill/effect configuration getters in the verified 2.6.400.304 image. These lead to configuration/name lookups, wrappers and registration. In particular, `MarchFightingSkillData` reads the skill name for display; it does not supply the missing damage equation.
- Recovered the native string-literal layout and validated **all 68,874 descriptors**, UTF-8 strings and the complete contiguous literal heap. Selected RIP-relative references now identify report keys directly instead of inferring their meaning from a method name.

These are bounded static searches. Reflection, dynamically constructed identifiers, indirect execution and original server code are not exhausted. **A server-only implementation is plausible, but not proved.** No original Type-11100 damage handler has been identified in the inspected paths.

## The exact report-input boundary

`GotoUtils.GenBattleReportInputData` reads three supplied total groups:

- `survivor_damage_and_withstand`
- `titan_damage_and_withstand`
- `pet_damage_and_withstand`

The hero record has fields `i_survivor`, `cure`, `damage`, `withstand`. In the selected replay-statistics converter, these supplied damage, healing and damage-taken values are copied into the displayed statistics. They are not recomputed from the visible projectiles.

Separately, `BattleReportReplayModule.ParMailBattleReportData` parses `rounds_info` containing unit `pos`, `hp`, `start_hp`, `heal_hp`. The native metadata declares exactly those unit-state fields. The supplied state stream and outgoing owner totals are different evidence: a unit's HP delta alone cannot identify which enemy or effect caused it.

The associated request class uses `Mail:GetSubMail`. The inspected account-preference files, empty HTTP cache and existing task JSON files did not provide the original numerical payload. Reports are also retained in the client's `_allReportDict` in memory. No process-memory attachment or live network request was used for this work.

## What the new tooling does

The [source audit](../../work/battle-lab/audit_field_dispatch.py) verifies hashes, selected field offsets, literal references, corpus coverage and direct getter references. Its [normalized evidence](../../outputs/hero-report/Field-Dispatch-Source-Audit.json) contains no raw game scripts or player profile.

The [offline importer](../../work/battle-lab/import_field_report.py) accepts explicit JSON pointers to a selected owner's totals and optional round-state arrays. It preserves supplied numerical precision, maps exact supported hero IDs, rejects malformed/abbreviated values and duplicate identities, and excludes player IDs/names. It does not guess owner/camp, convert rounds to seconds, infer effective healing, or label imported observations as predictions. Inputs and normalized case output should remain private.

For example, a privately saved response can be processed with `--input`, `--owner-pointer`, optional `--rounds-pointer`, and `--output`. The nested state hierarchy is preserved without assigning its array dimensions to camps or seconds. The wrapper paths must match the actual response; no universal wrapper schema is assumed. No server request, credentials or new recording is needed by the importer.

## Numerical outcome and next evidence

**No runtime weights or Ray-specific multiplier changed. The existing replay errors are unchanged.** This pass identifies where supplied numerical outcomes enter presentation and rules out several assumed local calculation paths; it does not recover the original arithmetic.

The next useful evidence is a sanitized numerical report case: the selected owner's unrounded `survivor_damage_and_withstand`, matching `rounds_info`, and matched pre-fight hero/troop stats and builds. Preserve source totals separately from any fitted parameters. Even then, round snapshots do not establish per-hit attribution or a unique battle equation; additional independent cases are needed to validate a prediction model. Another animation recording alone is unlikely to resolve this boundary.
