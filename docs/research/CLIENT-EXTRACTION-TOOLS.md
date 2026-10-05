# Tiles Survive client inspection tools

Tested on 5 October 2026. The installed Windows client explicitly shows the Ghoulion Pursuit **Set Gather Point** button only to **R5 or above**. Ordinary open-ground Gather Points are a separate R4/R5 workflow. The Ghoulion button passes the building's own coordinates to the Gather Point dialog. This guide documents that finding and the offline tools used to verify it without interacting with the running game.

The remembered tool name is likely **IL2CPP / Il2CppDumper**, not LLCP. IL2CPP is Unity's native compilation system; Il2CppDumper reads its binary and metadata. It is not a universal decryptor.

## Tool inventory

| Tool | Purpose | Verified result |
| --- | --- | --- |
| `decode_language_pack.py` | Decode the language pack with its known client XOR key | Readable localization, including Gather Point strings |
| `extract_config_pack.py` | Catalogue and extract SOS configuration entries | Existing configuration inspection path; not a native-code decoder |
| `extract_hero_images.py` helpers | Read asset names, bundle IDs and hashes from binary indices | Used successfully by the new asset exporter |
| `export_client_asset.py` | Find loose or SOS-packed bundles; export Unity trees or Lua | Gather Point dialog recovered from the current cache |
| UnityPy 1.25.4 | Parse UnityFS objects | 150 objects in the dialog bundle; 146 exported trees, 4 texture/sprite trees skipped |
| `audit_native_client.py` | Inspect metadata headers, hashes and PE sections | Identified nonstandard metadata header and packed binary layout |
| Il2CppDumper 6.7.46 | Recover IL2CPP type information from usable native inputs | Current metadata rejected as invalid |
| pefile 2024.8.26 and Capstone 5.0.9 | Read PE layout and disassemble disk bytes offline | Entry-point inspection works; not proof of unpacking |
| `probe_metadata_patterns.py` | Measure repetition and try an explicitly unvalidated frequency-based XOR mask | Readable target names recovered; metadata header remains invalid |
| `trace_native_file.py` | Follow bounded direct control flow in disk-backed x64 PE sections | Loader reaches an unresolved indirect dispatcher; no game code executed |
| `unpack_client_lzma.py` | Decode seven verified raw LZMA streams directly from disk | Native sections recovered; refuses a different client SHA-256 |
| Unicorn 2.1.4 in a private investigation script | Interpret loader bytes in isolated guest memory | Located compression streams; stopped at an unmodeled external call |

All repository scripts listed above are under `work/hero-extraction/`. UnityPy, pefile and Capstone are external dependencies. The audit, metadata probe and disk LZMA decoder use Python's standard library. The synthetic tracer test uses its optional dependencies. None of the published commands attaches to the game, loads a game DLL, or executes game instructions.

## Paths and versions

The inspected installation has native build `2.6.200.276` and a downloaded bundle list named `bundle_list_G_2.6.200.285.json`. These are different version layers. Do not label extracted cache assets as native build 285 or combine arbitrary old indices and new hashes without checking the resolved asset.

From the repository root, set explicit paths. Change versions after inspecting the installation:

```powershell
$taskPython = 'python'
$gameRoot = 'C:\Program Files (x86)\FunPlus\Tiles Survive'
$buildRoot = Join-Path $gameRoot 'ngame\2.6.200.276'
$packagedAssets = Join-Path $buildRoot 'tspc_Data\StreamingAssets\GameAssets'
$gameAssets = Join-Path $gameRoot 'GameData\GameAssets'
$privateOutput = Join-Path $PWD 'tmp\client-inspection'
$assetIndex = Join-Path $packagedAssets 'AssetBundle2\G\Windows\bundle_assets_G_2.6.200.276.json'
$bundleList = Join-Path $gameAssets 'AssetBundle2\bundle_list_G_2.6.200.285.json'
```

The `.json` suffix on these two indices is misleading: the existing helpers parse their binary structure. Do not run `json.load` on them.

The verified local runtime was Python 3.12.14. An older private UnityPy environment contained Python 3.14 native wheels and failed under 3.12 at `_brotli`. Install dependencies with the interpreter that will run the scripts:

```powershell
& $taskPython -m pip install --target "$privateOutput\lib" UnityPy==1.25.4 pefile==2024.8.26 capstone==5.0.9
$env:PYTHONPATH = "$privateOutput\lib"
```

Use a dedicated shell or restore its previous PYTHONPATH afterward. Keep libraries and output private, not in the published source tree.

## Decode language and inspect configuration

```powershell
& $taskPython work/hero-extraction/decode_language_pack.py "$gameAssets\Languages\InGameBin\language_en.json.bin.enc" --output "$privateOutput\language_en.json"
& $taskPython work/hero-extraction/extract_config_pack.py --pack "$packagedAssets\BinaryConfigPack.ss" --output "$privateOutput\config" --term Gather --term AllianceBoss
```

The configuration command creates a catalogue and searches entries. Use `--extract EXACT_ENTRY_NAME` to extract selected entries from that catalogue. The language XOR key is content obfuscation, not an account credential; it does not decode native metadata. The configuration reader expects its observed 4096 geometry and is not interchangeable with the cache bundle reader.

## Export the Gather Point and Ghoulion interfaces

```powershell
& $taskPython work/hero-extraction/export_client_asset.py --asset-index $assetIndex --bundle-list $bundleList --asset ui_set_gathering_point --root $gameAssets --root $packagedAssets --mode tree --output "$privateOutput\gather-ui"
& $taskPython work/hero-extraction/export_client_asset.py --asset-index $assetIndex --bundle-list $bundleList --asset ui_alliance_portal_advanced --root $gameAssets --root $packagedAssets --mode tree --output "$privateOutput\ghoulion-ui"
```

Use `--mode bundle` to save the UnityFS bundle instead, or `--mode lua` for an indexed asset containing Lua TextAssets. Lua mode needs an exact name present in the supplied index; it is not a bulk search command. Tree mode reports skipped object types rather than claiming a complete export. Prefer a fresh output directory so stale files cannot be mistaken for current results.

The verified Gather Point asset has bundle ID `210427` and cache digest `39897e010ed6a14628f7b0aee5f56f49`. It was found in `5c19ab08fa734b6bd334719823241e81.ss`, not a loose file. The entry had a 54-byte prefix before UnityFS.

Cache packs have important traps:

- The observed header geometry can be 2048, but stored block addresses still use 4096-byte units. Multiplying by 2048 reads unrelated data.
- Directory rows can refer to a different name-slot index. The first word is not always the row number.
- `0xFFFFFFFF` denotes a deleted directory entry and must be skipped.
- Finding a UnityFS signature is a parsing checkpoint, not proof that every object or native dependency was decoded.

These cases are covered by the exporter and its synthetic fixture test.

## Audit native files before trying Il2CppDumper

```powershell
& $taskPython work/hero-extraction/audit_native_client.py --metadata "$buildRoot\tspc_Data\il2cpp_data\Metadata\global-metadata.dat" --binary "$buildRoot\GameAssembly.dll" --binary "$buildRoot\NEP2.dll"
& $taskPython -m unittest discover -s work/hero-extraction -p test_client_inspection.py -v
```

The audit prints JSON with sizes, SHA-256 hashes, section layout, first metadata bytes and sample entropy. Entropy is calculated from a bounded sample; it is not a full-section measurement or a cipher detector.

Current native evidence:

- Metadata size: **50,901,712 bytes**. First two little-endian words: `0xFAB11BAF`, **50,901,712**. The second word equals file length rather than a normal metadata version.
- Metadata SHA-256: `c7200f7d6ba95ea7b9e207683eefc6848c4b3018ddd12e41ee5c9229a4bb3c9f`.
- GameAssembly SHA-256: `e91333faf1fe03f6cbca1a676c38ed8a4d9f7fe3af8e77824b86727f2961de61`.
- The usual GameAssembly code sections have zero raw size; the large `.201` section holds most disk content. This is evidence of a packed layout, not ordinary directly readable method bodies.
- Entry-point RVA `0xB02FEB7` starts with a push and a call into another address in the packed section. That stub does not expose the Gather Point method.
- Literal searches did not find `global-metadata.dat` or the metadata magic in GameAssembly or NEP2. NEP2's presence does not establish which component transforms the metadata.

The metadata body has a recoverable 1,152-byte repeating XOR layer, described below. Its protected prefix and tail are not fully decoded. Preserved magic does not mean the complete file is usable, and replacing the second word with a guessed Unity version is not decryption.

The available Il2CppDumper executable was in the private tools inventory at `Desktop\Tiles Survival Tools\work\tools\Il2CppDumper\Il2CppDumper.exe`. Parameterized usage:

```powershell
$dumper = 'PATH_TO_PRIVATE_TOOLS\Il2CppDumper.exe'
& $dumper "$buildRoot\GameAssembly.dll" "$buildRoot\tspc_Data\il2cpp_data\Metadata\global-metadata.dat" "$privateOutput\il2cpp"
```

On this build it fails with `Metadata file supplied is not valid metadata file`. A subsequent redirected-input `ReadKey` exception is a secondary console problem. For unattended runs use a private tool copy with `RequireAnyKey` false. `ForceVersion` affects the binary parser, not the metadata parser. Dummy assemblies restore type information, not original C# method bodies. These limits are documented by [Il2CppDumper](https://github.com/Perfare/Il2CppDumper#common-errors).

The [Il2CppInspector XOR plugin source](https://raw.githubusercontent.com/djkaty/Il2CppInspectorPlugins/master/Core/XOR-Decryptor/Plugin.cs) inspected here enters its image decoding path for ELF inputs and returns for other formats. It is not a verified decoder for this Windows PE client. Do not reuse keys, RVAs or decoder recipes from another game merely because it also ships NEP2.

## How to place the Gather Point on Ghoulion Pursuit

Ask the alliance **R5** to open the Ghoulion Pursuit event screen, tap **Set Gather Point**, then confirm the coordinates in the Gather Point dialog. The event handler supplies the existing Ghoulion building's coordinates automatically. Do not use the clover marker editor or select neighboring open ground for this operation.

The missing button on an R4 screen is explained by the event-specific **R5** visibility check. Localization allowing R4/R5 applies to the ordinary Gather Point workflow; it does not override the Ghoulion screen's stricter check. No cooldown check appears on the native visibility or click path for this button. The click handler requires an existing alliance portal and rejects its state value 8. Do not translate that state into a named gameplay condition without checking the enum.

This is verified against native Windows build **2.6.200.276**, paired with the inspected cache assets. It establishes the client workflow and button gate, not a live server acceptance test. No Gather Point request or alliance-state change was made. A different build or a hotfix replacing these methods needs its own check.

### Evidence from the recovered native sections

| Check | Verified result |
| --- | --- |
| `AllianceBossUIMediator.OnCompShow`, RVA `0x364D480` | Calls `PlayerModule.get_IsR5orAbove`, then uses that result to show/hide `_setFocusButton` |
| Native field offsets | `_setFocusButton` is at instance offset `0x288`; `_btnRelocation` is separately at `0x300` |
| `AllianceBossUIMediator.OnClickSetFocus`, RVA `0x364CDE0` | Gets the alliance's portal, obtains `GetLocation`, and copies that coordinate into the dialog parameter |
| Dialog parameter type | Metadata identifies `AllianceGatherSetUIMediator.Parameter`; its `coord` field is at `0x10` |
| UI destination | The handler reads `UINameConstant` static offset `0x930`, identified as `AllianceGatherSetUIMediator`, and opens that UI |
| `AllianceGatherSetUIMediator.OnSettingClick`, RVA `0x32F6470` | Reads map X/Y from the supplied coordinate and creates the Gather Point request |

`AllianceGatherSetGatherPointsParameter.lua` identifies the request as `AllianceGather:SetGatherPoints`, with alliance ID, map X and map Y. It was inspected, not sent. `TradeStationModule:CanSetAllianceGatherPointByCoordinate` adds a Lua-side restriction for pieces configured with a trade station. That is not the Ghoulion button's visibility rule.

The clover alliance marker is a separate system. The focus, automation and relocation objects in the event prefab are also separate controls. A serialized inactive flag alone is not evidence of a permission gate; the R5 finding comes from the recovered handler and field-offset table.

## Privacy and publication

Keep raw game code, bundles, metadata, DLLs, captures and memory dumps out of this public repository. Use the ignored repository `tmp/` directory or a separate private directory. Publish scripts, synthetic tests and the findings above. Review `git status` and the staged diff before pushing. This investigation does not modify the installation, launch its DLLs, inject code, disable protections, or change alliance state.

## Offline decoding investigation

The user selected offline analysis only because runtime inspection could interact with anti-cheat. Do not attach to the game, request its process memory, load a client DLL, or use a runtime hook as part of this route. The following published commands operate on disk bytes only:

```powershell
& $taskPython work/hero-extraction/probe_metadata_patterns.py --metadata "$buildRoot\tspc_Data\il2cpp_data\Metadata\global-metadata.dat" --reference-offset 8387712 --period 1152 --sample-size 2097152 --known-text AllianceGatherSetUIMediator --known-text AllianceBossUIMediator --known-text AlliancePortalModule --candidate-output "$privateOutput\xor1152-candidate"
& $taskPython work/hero-extraction/trace_native_file.py --binary "$buildRoot\GameAssembly.dll" --output "$privateOutput\loader-trace.json"
& $taskPython work/hero-extraction/unpack_client_lzma.py --binary "$buildRoot\GameAssembly.dll" --output "$privateOutput\native-rva-image.bin"
```

The statistical probe assumes the most common plaintext byte is lowercase `e` in its reference region. This is a hypothesis, not a recovered loader key. Its default reference window is 1 MiB starting at 8 MiB. The candidate output is intentionally named `candidate.dat`, not `global-metadata.dat`.

The earlier 128-byte probe was incomplete. The larger observed period is **1,152 bytes**; lag equality was about **62.13%**, compared with **30.45%** at 128 and **0.34%** at 1. The selected reference offset is aligned to 1,152. About **99.8%** of the candidate's 1–10 MiB region was ASCII or NUL. Structural checks recovered coherent strings, methods, types, images and native field offsets. The first 136 bytes and last 72 bytes remain unsuitable for treating the candidate as fully decoded metadata.

Useful recovered layout checkpoints are string literals at `0x100`, literal data at `0x85EE0`, strings at `0x239D88`, 36-byte method records at `0xD25778`, 12-byte field records at `0x2244AA0`, and 88-byte type records at `0x29A9798`. There are 43,318 type definitions and 129 images. Method records match the version-31 layout, including `returnParameterToken`; this does not repair the protected header. The `Assembly-CSharp.dll` native module is at RVA `0x6977660`, its method-pointer table at `0x78D5700`, and the field-offset pointer table at `0x77E4000`. These are build-specific offsets, not portable recipes.

The bounded static tracer cannot follow the loader's indirect VM dispatch on its own. A private Unicorn CPU model interpreted only disk-backed bytes in synthetic guest memory, with imported functions replaced by stop hooks. Local allocation, name lookup, memory protection and the observed checksum loop were modeled without invoking Windows APIs. No running process was read. Disk copies of Windows module headers/exports supplied lookup data; their function entry points remained stop hooks. The model stopped at `GetProcessAffinityMask` after locating seven LZMA streams. No actual process-affinity query was made.

The published decoder reproduces those seven stream decodes directly, without CPU modeling, using raw LZMA with `lc=3`, `lp=0`, `pb=2`. It validates the client hash, exact compressed lengths, decompressed lengths, and end markers. Its output is indexed by RVA, with original pointer values at the preferred image base. It does not apply runtime fixups, initialize IL2CPP, repair metadata, or create a loadable DLL. Keep that output private and read it as analysis bytes.

Other probes tried a zero-frequency mask, an English-frequency score, whole-word XOR/subtraction masks, and simple position-counter corrections. None yielded validated metadata. Searching known-text mask fragments found matches inside metadata but not in GameAssembly, NEP2 or UnityPlayer. Do not report these attempts as a working decoder.

## Offline hero combat audit

`work/hero-extraction/audit_combat_effects.py` inventories all supported heroes'
runtime skill/release links, timeline events (keeping projectile-hit context),
and per-effect numeric dependencies. It requires the same pack fingerprint as
the planner dataset and validates its four tables against the current manifest.
It does not execute effects or produce a combat ranking. See
[the 2026-10-05 audit](HERO-COMBAT-AUDIT-2026-10-05.md) for native RVAs, findings,
private disassembly tooling and remaining limitations. Keep raw timelines,
metadata and recovered native images private; publish only normalized audit data.
