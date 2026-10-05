# Offline combat audit — 5 October 2026

## Result

The previous experimental direct-output calculation was incorrect. It multiplied
ATK by display `DamageParam` values, assumed affine level growth, then counted
casts using a cooldown. Native code instead resolves per-effect parameters and
dispatches effects through timelines, projectiles, summons and conditional paths.
The experimental metric and misleading skill `× ATK` labels have been withdrawn
in both the Windows and browser planners. Old saved direct-mode settings migrate
to configured power; builds, ownership and balances are preserved.

The offense index also used the largest non-basic display parameter as 35% of
its score. That input has been removed for every hero. Offense now compares the
normalized max-level ATK stat only. Composite and squad weights remain explicitly
planning heuristics, not native combat formulas. Resource recommendations still
compare the configured power/ATK/DEF/HP changes of the user's recorded builds.

## Evidence and boundaries

Inspected disk files only: installed native build `2.6.200.276`, current local
config cache matched against `BinVersionList_Realtime`, and cached timeline bundle
205144 (`814ae4a6882cefe89a6ff63691429200`, referenced by the G2.6.200.285 bundle
list). No process attachment, memory reading, game requests, injection, live
battle or anti-cheat interaction was used.

Recovered native image SHA256 is reproducible using the existing build-specific
decoder. Original GameAssembly SHA256:
`e91333faf1fe03f6cbca1a676c38ed8a4d9f7fe3af8e77824b86727f2961de61`.
Metadata SHA256:
`c7200f7d6ba95ea7b9e207683eefc6848c4b3018ddd12e41ee5c9229a4bb3c9f`.
Native addresses below are RVAs for this exact build, not reusable function signatures.

| Default native path | Observed operation | What it does not establish |
| --- | --- | --- |
| `SkillCellDataSystem.GetValueWithEffectParam2`, 0x28DBE10, arithmetic at 0x28DBF9D | Config base parameter is multiplied by the resolved skill modifier, then the resolved addend is added; base fallback when no owner component is available | Generic affine growth by skill level |
| `RaidEffectSystem.ProcessEffectDamage`, 0x28A0FD0, scaling at 0x28A111C | Resolved damage-effect parameter2 and parameter3 are divided by 1000 before `CalSkillDamage` | Final outgoing damage equals ATK times this value |
| `SkillBase.InitSkill`, 0x28D3BE0 | Resolved cooldown and configured pre-cooldown are converted from milliseconds to seconds | Uninterrupted casts every cooldown, guaranteed hits, attack speed or flight time |
| `SkillDamageCalSystem.CalSkillDamage`, 0x28E15E0 | Separate property, defense/penetration, custom expression and modifier paths feed damage calculation | A complete verified defense/critical/random/PvP formula for the planner |

These are verified operations in the native **default** path, not a certification
of the active runtime. The inspected routines include ILFix patched-method
dispatch. Disk inspection has not established which overrides are selected in a
live session. No complete numerical damage, healing, shield or summon simulation
is claimed.

## Ray: concrete discrepancy

- Runtime basic effect `damage_ray_attack` has parameter2 **360**. Its resolved
  damage-effect input is divided by 1000: **0.36 times the resolved modifier**,
  before the remaining damage formula. This is not the old display coefficient.
- The active skill has base cooldown **9000 ms**, pre-cooldown **6300 ms**.
  Its animation launches three projectiles at approximately **0.310 / 0.443 /
  0.573 seconds**. Their **hit actions**, not launch times, dispatch three
  damage-zone references. Zone lifetime, repeated effects, targeting and summon
  chains must be resolved before counting damage hits.
- Referenced damage rows include base parameters **3200 / 2400 / 4000** and a
  `*_text` row **9600**. A parameter row is not proof of an executed hit; summing
  every referenced row would risk counting presentation/aggregate values twice.
- `damage_ray_skill_1_effect_text` is runtime **Type 1**, a healing path, despite
  its name containing "damage". The old skill-label implementation selected the
  largest number from names containing that word and called it an ATK coefficient.
  This classification is unsafe and has been removed for all heroes.

No numeric nerf is invented from these findings. There is no earlier native/effect
snapshot comparison here proving a specific Ray balance change. The earlier
configuration audit found unchanged progression/maximum stats for the 28 existing
heroes and added Lava, bringing the roster to 29.

## All-hero coverage

[Hero-Combat-Audit.json](../../outputs/hero-report/Hero-Combat-Audit.json) inventories
all **29 heroes**, their linked runtime skills, base cooldowns, timeline event
references and referenced per-effect numeric parameters. All directly linked
release/timeline assets were found in the **229-asset** export. This does not mean
all nested summon, buff, trigger or condition graphs are complete. Each skill is
explicitly marked `complete_combat_graph_verified: false`.

The four CFG tables used by the audit are individually checked against the current
manifest before decoding. Output records table hashes, pack/manifest hashes and
timeline-export hashes. Raw CFGs, recovered metadata/native images and timeline
scripts remain private and excluded from Git.

## Repeating the audit

See [CLIENT-EXTRACTION-TOOLS.md](CLIENT-EXTRACTION-TOOLS.md) for the metadata probe,
build-specific offline LZMA image recovery and Unity asset export workflow. This
investigation also used Capstone 5.0.9 installed only under ignored `tmp/` for
disassembly. The exploratory metadata/RVA mapping script is build-specific,
unvalidated for other assemblies, and remains private; it is not an execution tool.

After exporting timeline TextAssets into a private directory:

```powershell
python work/hero-extraction/audit_combat_effects.py `
  --pack '<current BinaryConfigPack.ss>' `
  --manifest '<current BinVersionList_Realtime.json>' `
  --upgrade-data outputs/hero-report/TilesSurvive-Upgrade-Data.json `
  --timelines '<private TextAsset export directory>' `
  --output outputs/hero-report/Hero-Combat-Audit.json
```

This script produces a dependency audit, not combat rankings. Extending a battle
simulator requires verified complete effect graphs, property formulas and cast
scheduling. Server-only balance changes cannot be certified by this snapshot.
Live validation is outside the user's chosen scope.
