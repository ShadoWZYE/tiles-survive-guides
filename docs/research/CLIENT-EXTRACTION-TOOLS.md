# Tiles Survive client inspection tools

Tested on 5 October 2026. This guide records how to inspect an installed client without changing the game, and what is still missing from the investigation into placing the alliance Gather Point on Ghoulion Pursuit. Asset extraction works. Native metadata deobfuscation and the exact Ghoulion button visibility condition are not solved.

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

All repository scripts listed above are under `work/hero-extraction/`. UnityPy, pefile and Capstone are external dependencies. The audit and synthetic tests need only Python's standard library. None of these commands attaches to the game or executes a game DLL.

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

The header suggests a custom wrapper or transformation. Its algorithm and keys are **not identified**. Preserved magic does not mean the file is usable, and replacing the second word with a guessed Unity version is not decryption.

The available Il2CppDumper executable was in the private tools inventory at `Desktop\Tiles Survival Tools\work\tools\Il2CppDumper\Il2CppDumper.exe`. Parameterized usage:

```powershell
$dumper = 'PATH_TO_PRIVATE_TOOLS\Il2CppDumper.exe'
& $dumper "$buildRoot\GameAssembly.dll" "$buildRoot\tspc_Data\il2cpp_data\Metadata\global-metadata.dat" "$privateOutput\il2cpp"
```

On this build it fails with `Metadata file supplied is not valid metadata file`. A subsequent redirected-input `ReadKey` exception is a secondary console problem. For unattended runs use a private tool copy with `RequireAnyKey` false. `ForceVersion` affects the binary parser, not the metadata parser. Dummy assemblies restore type information, not original C# method bodies. These limits are documented by [Il2CppDumper](https://github.com/Perfare/Il2CppDumper#common-errors).

The [Il2CppInspector XOR plugin source](https://raw.githubusercontent.com/djkaty/Il2CppInspectorPlugins/master/Core/XOR-Decryptor/Plugin.cs) inspected here enters its image decoding path for ELF inputs and returns for other formats. It is not a verified decoder for this Windows PE client. Do not reuse keys, RVAs or decoder recipes from another game merely because it also ships NEP2.

## Gather Point findings and remaining work

Localization includes an event-screen `Set Gather Point` string and a message allowing **R4 or R5** to set the alliance Gather Point. This supports general R4 permission; it does not establish every event-specific UI condition.

The extracted `AllianceGatherSetGatherPointsParameter.lua` constructs the `AllianceGather:SetGatherPoints` request with alliance ID and map X/Y. This identifies the request shape, not a safe way to bypass the client or proof that the server accepts occupied-building coordinates. No request was sent.

`TradeStationModule:CanSetAllianceGatherPointByCoordinate` blocks coordinates in pieces configured with a trade station, without checking whether that activity is active. It is one Lua-side restriction, not the complete placement rule.

`ui_alliance_portal_advanced` is associated with `AllianceBossUIMediator` and contains `p_btn_relocation`, serialized inactive by default. The Gather Point dialog is associated with `AllianceGatherSetUIMediator` and has X/Y value labels and a setting button. The event module is referenced through the native bridge as `AlliancePortalModule`.

The important unresolved step is to recover and inspect the **runtime visibility and click handlers** for the event relocation control, then trace the target coordinates into `AllianceGatherSetUIMediator`. A prefab's inactive flag cannot prove an R5-only requirement, cooldown gate, or absence of the feature. The clover alliance marker is a separate system and is not evidence of the Gather Point's position.

Read-only process checks found limited query access but Windows denied VM_READ and full query access with error 5. The running tool token had medium integrity and no SeDebugPrivilege. Codex filesystem full access does not imply an elevated Windows process token. No memory dump was obtained. Do not repeatedly retry the same denied call or describe it as successful extraction.

Future attempts should first recheck file hashes and version pairing, reproduce the asset export, and pursue offline loader analysis or a build-specific metadata decoder. Only accept a decoded candidate after validating its header, table bounds, strings and compatibility with the corresponding binary. Then trace the UI handler; do not turn the current partial findings into instructions for users.

## Privacy and publication

Keep raw game code, bundles, metadata, DLLs, captures and memory dumps out of this public repository. Use the ignored repository `tmp/` directory or a separate private directory. Publish scripts, synthetic tests and the findings above. Review `git status` and the staged diff before pushing. This investigation does not modify the installation, launch its DLLs, inject code, disable protections, or change alliance state.

## Offline decoding investigation

The user selected offline analysis only because runtime inspection could interact with anti-cheat. Do not attach to the game, request its process memory, execute a client DLL, or use a runtime hook as part of this route. The following commands operate on disk bytes only:

```powershell
& $taskPython work/hero-extraction/probe_metadata_patterns.py --metadata "$buildRoot\tspc_Data\il2cpp_data\Metadata\global-metadata.dat" --reference-offset 0x800000 --period 128 --known-text AllianceGatherSetUIMediator --known-text AllianceBossUIMediator --known-text AlliancePortalModule --candidate-output "$privateOutput\xor128-candidate"
& $taskPython work/hero-extraction/trace_native_file.py --binary "$buildRoot\GameAssembly.dll" --output "$privateOutput\loader-trace.json"
```

The statistical probe assumes the most common plaintext byte is lowercase `e` in its reference region. This is a hypothesis, not a recovered loader key. Its default reference window is 1 MiB starting at 8 MiB. The candidate output is intentionally named `candidate.dat`, not `global-metadata.dat`.

In a 64 KiB region beginning at offset 4096, equal-byte frequency at lag 128 was **30.45%**, versus **0.34%** at lag 1. The XOR candidate recovered exact occurrences of `AllianceGatherSetUIMediator` at offset 733540, `AllianceBossUIMediator` at 3251415, and `AlliancePortalModule` at 736626. Its header still fails validation, and many surrounding bytes remain corrupt. These observations support a repeating-mask layer; they do not establish the complete encoding algorithm.

Additional readable candidate fragments identify `AllianceGatherSetUIMediator-CanSetGatherPoint0`, the setting-button update method, `OnSetGatherPointClick`, and `OnRelocationClick`. The event prefab contains separate focus, automation and relocation objects, while candidate member names include `_setFocusButton`, `_autoButton` and `_btnRelocation`. Do not equate relocation with Gather Point placement. Recover the actual bindings and handler bodies before attributing an action to a button.

The bounded entry trace visited 11 blocks and 126 instructions before an indirect jump through `r9`. Offline arithmetic on the entry seed and its file-backed operand resolved that first dispatch target to RVA `0xB08C8F5`. A second trace from that RVA visited 6 blocks and 57 instructions and ended in a push/return dispatch. The tracer records unresolved indirect branches and possible push/return dispatch; it does not emulate them or claim to unpack the image. Further static dispatcher analysis is still required before reaching the metadata loader.

Other probes tried a zero-frequency mask, an English-frequency score, whole-word XOR/subtraction masks, and simple position-counter corrections. None yielded validated metadata. Searching known-text mask fragments found matches inside metadata but not in GameAssembly, NEP2 or UnityPlayer. Do not report these attempts as a working decoder.
