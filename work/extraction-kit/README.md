# Tiles Survive Extraction Kit - Windows x64

Unzip the entire package to a writable folder. Double-click **Extract.cmd** for
the menu, or run it from PowerShell. Python and all extraction dependencies are
bundled. The receiving machine needs no Python installation, pip, admin rights,
repository checkout or internet connection. The game files must already exist
locally; content not downloaded by the game cannot be recovered from an absent cache.

This kit targets **Tiles Survive**, using our existing offline decoders. It does
not extract arbitrary games or recreate the original Unity/C# project. Native
unpacking supports only the exact binary hash already verified by our decoder;
other builds are rejected. A successful native audit is not successful unpacking.

## Start on another machine

```powershell
.\Extract.cmd verify
.\Extract.cmd doctor
.\Extract.cmd discover --game-root 'D:\Games\Tiles Survive'
```

Discovery lists every candidate pack, manifest, language file, binary and bundle
index. Choose inputs explicitly. Native build, packaged asset version and cache
version are separate layers; do not blindly select the lexicographically last
file. The misleading `.json` bundle indices contain a binary format.

Use a **new output folder for every run**, outside game/input directories. Failed
runs remain marked `failed` in `run.json`; inspect the error/log and use a fresh
folder when retrying. Reports include UTC timestamps, input SHA-256 hashes,
arguments and output hashes. Asset reports also hash the actual resolved bundle
entry, including SOS-packed bundles. Close the game during extraction to obtain
a stable snapshot. Results are private game content; share the clean kit ZIP.

## Extract and decode

Replace the example paths with paths found by `discover`:

```powershell
# Extract all configuration tables, or filter with repeated --extract regexes.
.\Extract.cmd config --pack 'D:\Games\Tiles Survive\GameData\GameAssets\BinaryConfigPack.ss' --extract '^survivor_' --decode --output '.\results\config-01'

.\Extract.cmd language --source 'D:\Games\Tiles Survive\GameData\GameAssets\Languages\InGameBin\language_en.json.bin.enc' --output '.\results\english-01'

.\Extract.cmd table --source '.\results\config-01\tables\0000_example.cfg' --output '.\results\table-01'

.\Extract.cmd asset --asset-index 'D:\PATH\bundle_assets_G_VERSION.json' --bundle-list 'D:\PATH\bundle_list_G_VERSION.json' --root 'D:\Games\Tiles Survive\GameData\GameAssets' --root 'D:\PATH\StreamingAssets\GameAssets' --asset ui_set_gathering_point --mode tree --output '.\results\gather-01'

.\Extract.cmd native --metadata 'D:\PATH\global-metadata.dat' --binary 'D:\PATH\GameAssembly.dll' --output '.\results\native-audit-01'

.\Extract.cmd unpack --binary 'D:\PATH\GameAssembly.dll' --output '.\results\native-unpack-01'
.\Extract.cmd trace --binary 'D:\PATH\GameAssembly.dll' --output '.\results\trace-01'
```

Asset modes: `tree` exports readable Unity object trees (unsupported objects are
logged), `lua` exports Lua TextAssets, `bundle` saves the resolved UnityFS bundle,
and `sprites` exports Sprite objects as PNGs named by their numeric object IDs.
Use `--channel R` for R-channel assets. The asset name must exist in the supplied
index. This is selected-bundle extraction, not a recursive export of every
dependency, model, sound or texture in the installation.

The raw config extractor does not validate realtime overrides against their
manifest. Use the repository's `refresh_hero_data.py` workflow when publishing
planner data; do not treat a raw table export as a validated planner refresh.
The planner/report generation pipeline is outside this kit's initial scope.

Native audit JSON is in `tool.log`; the unpacker creates an RVA-indexed analysis
image, not a runnable DLL or recovered C# source. All tools inspect disk files;
they do not attach to the game, execute its DLLs or require Il2CppDumper. Historical
research and advanced limitations are in `ADVANCED-NOTES.md`. Its old paths and
versions are examples, not the paths selected by this kit.

## Rebuild and verify

The build machine needs Python with pip and internet. From the repository root:

```powershell
python work/extraction-kit/build.py --output outputs/Tiles-Survive-Extraction-Kit-Windows-x64.zip
```

The builder downloads the official Python 3.13.14 embedded x64 runtime and checks
its pinned SHA-256, installs binary wheels into the package, includes their license
metadata and Python's license, then runs runtime, checksum and synthetic extraction
tests using **the bundled interpreter**. It includes only an explicit source-file
allowlist. No installed game data, accounts, captures, private tools or extracts
are bundled. `requirements-lock.txt` pins transitive wheels and hashes; the
package manifest records every distributed file except the manifest itself.
The ZIP's adjacent `.sha256` file verifies the archive after copying it.

Rebuilding requires this source folder beside `work/hero-extraction` in the repo;
the distributed `build.py` is included as build provenance. To replicate extraction
on another machine, copy the ZIP, not the build environment. `verify` checks file
integrity against the included manifest; it is not a publisher signature.

Source: https://www.python.org/downloads/release/python-31314/

Unofficial tool; game assets remain the property of their owners.
