"""Portable, offline Tiles Survive extraction entry point."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
TOOLS = BASE / "tools" if (BASE / "tools").is_dir() else BASE.parent / "hero-extraction"
sys.path.insert(0, str(TOOLS))
sys.dont_write_bytecode = True


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def identity(path):
    path = path.resolve(strict=True)
    return {"path": str(path), "size": path.stat().st_size, "sha256": sha256(path)}


def doctor():
    result = {"python": sys.version, "executable": sys.executable, "dependencies": {}}
    for module, package in (("UnityPy", "UnityPy"), ("PIL", "Pillow"),
                            ("pefile", "pefile"), ("capstone", "capstone")):
        importlib.import_module(module)  # Exercise native-extension loading too.
        result["dependencies"][package] = importlib.metadata.version(package)
    print(json.dumps(result, indent=2))


def discover(root):
    root = root.resolve(strict=True)
    # Inventory candidates; never silently pair different native/cache versions.
    patterns = ("**/BinaryConfigPack.ss", "**/BinVersionList*.json",
                "**/bundle_assets_*.json", "**/bundle_list_*.json",
                "**/language_*.json.bin.enc", "**/GameAssembly.dll", "**/global-metadata.dat")
    print(json.dumps({"game_root": str(root), "candidates": {
        pattern: [str(p) for p in sorted(root.glob(pattern)) if p.is_file()]
        for pattern in patterns}}, indent=2))


def invoke(script, arguments, output):
    command = [sys.executable, "-B", "-X", "utf8", str(TOOLS / script), *map(str, arguments)]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            encoding="utf-8", errors="replace")
    (output / "tool.log").write_text(result.stdout, encoding="utf-8")
    print(result.stdout, end="")
    if result.returncode:
        raise RuntimeError(f"{script} failed with exit code {result.returncode}; see tool.log")


def run(args):
    output = args.output.resolve()
    inputs = []
    for key in ("source", "pack", "metadata", "binary", "asset_index", "bundle_list"):
        value = getattr(args, key, None)
        for path in (value if isinstance(value, list) else [value]):
            if path is not None:
                inputs.append(identity(path))
    roots = [p.resolve(strict=True) for p in getattr(args, "root", [])]
    # Output must be fresh and outside supplied game/input directories.
    protected = roots + [Path(item["path"]).parent for item in inputs]
    if any(output == p or p in output.parents or output in p.parents for p in protected):
        raise ValueError("Output must be separate from input/game directories")
    output.mkdir(parents=True, exist_ok=False)
    report = {"command": args.command, "started_utc": datetime.now(timezone.utc).isoformat(),
              "arguments": {k: str(v) for k, v in vars(args).items()},
              "python": sys.version, "inputs": inputs, "status": "running"}
    save(output / "run.json", report)
    try:
        if args.command == "config":
            command = ["--pack", args.pack.resolve(), "--output", output / "tables"]
            for flag, values in (("--extract", args.extract), ("--term", args.term)):
                for value in values:
                    command += [flag, value]
            invoke("extract_config_pack.py", command, output)
            if args.decode:
                from decode_cfg import decode_table
                decoded = output / "decoded"
                decoded.mkdir()
                for table in sorted((output / "tables").glob("*.cfg")):
                    save(decoded / (table.stem + ".json"), decode_table(table))
        elif args.command in ("language", "table"):
            script = "decode_language_pack.py" if args.command == "language" else "decode_cfg.py"
            invoke(script, [args.source.resolve(), "--output", output / "decoded.json"], output)
        elif args.command == "asset":
            from extract_hero_images import asset_bundle_ids, bundle_hashes
            from export_client_asset import locate_bundle
            ids = asset_bundle_ids(args.asset_index, {args.asset})
            digest = bundle_hashes(args.bundle_list, {ids[args.asset]})[ids[args.asset]]
            raw, source = locate_bundle(roots, args.channel, digest)
            report["bundle"] = {"source": str(source), "digest": digest,
                                "entry_sha256": hashlib.sha256(raw).hexdigest()}
            if args.mode == "sprites":
                import UnityPy
                start = raw.find(b"UnityFS")
                if start < 0:
                    raise ValueError("No UnityFS signature")
                count = 0
                for obj in UnityPy.load(raw[start:]).objects:
                    if obj.type.name == "Sprite":
                        sprite = obj.read()
                        # Numeric IDs prevent asset names from escaping the output directory.
                        sprite.image.save(output / f"sprite-{obj.path_id}.png")
                        count += 1
                report["sprites_exported"] = count
                if not count:
                    raise ValueError("Bundle contains no sprites")
            else:
                command = ["--asset-index", args.asset_index.resolve(), "--bundle-list",
                           args.bundle_list.resolve(), "--asset", args.asset, "--channel", args.channel,
                           "--mode", args.mode, "--output", output / "asset"]
                for root in roots:
                    command += ["--root", root]
                invoke("export_client_asset.py", command, output)
                if not any(p.is_file() for p in (output / "asset").rglob("*")):
                    raise ValueError("Asset export produced no files; inspect tool.log")
        elif args.command == "native":
            command = ["--metadata", args.metadata.resolve()]
            for binary in args.binary:
                command += ["--binary", binary.resolve()]
            invoke("audit_native_client.py", command, output)
        elif args.command in ("unpack", "trace"):
            script = "unpack_client_lzma.py" if args.command == "unpack" else "trace_native_file.py"
            command = ["--binary", args.binary.resolve(), "--output",
                       output / ("native-image.bin" if args.command == "unpack" else "trace.json")]
            if args.command == "trace" and args.rva:
                command += ["--rva", args.rva]
            invoke(script, command, output)
        if any(sha256(Path(item["path"])) != item["sha256"] for item in inputs):
            raise ValueError("An input changed during extraction; retry from a stable snapshot")
        report["status"] = "success"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = str(error)
        raise
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        report["outputs"] = [{"path": str(p.relative_to(output)), "sha256": sha256(p)}
                             for p in sorted(output.rglob("*")) if p.is_file() and p.name != "run.json"]
        save(output / "run.json", report)
    print(f"Completed: {output}")


def verify():
    manifest = json.loads((BASE / "package-manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = BASE / item["path"]
        if sha256(path) != item["sha256"]:
            raise ValueError(f"Package checksum mismatch: {item['path']}")
    print(f"Verified {len(manifest['files'])} packaged files")


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Check the bundled runtime and dependencies")
    commands.add_parser("verify", help="Verify packaged-file SHA-256 checksums")
    discovery = commands.add_parser("discover", help="List available input paths without guessing versions")
    discovery.add_argument("--game-root", type=Path, required=True)
    for name in ("config", "language", "table", "asset", "native", "unpack", "trace"):
        command = commands.add_parser(name)
        command.add_argument("--output", type=Path, required=True, help="New private output directory")
        if name == "config":
            command.add_argument("--pack", type=Path, required=True)
            command.add_argument("--extract", action="append", default=[], help="Table-name regex; omit for all")
            command.add_argument("--term", action="append", default=[])
            command.add_argument("--decode", action="store_true", help="Also decode selected CFG files to JSON")
        elif name in ("language", "table"):
            command.add_argument("--source", type=Path, required=True)
        elif name == "asset":
            for flag in ("asset-index", "bundle-list"):
                command.add_argument("--" + flag, type=Path, required=True)
            command.add_argument("--root", type=Path, action="append", required=True)
            command.add_argument("--asset", required=True)
            command.add_argument("--channel", choices=("G", "R"), default="G")
            command.add_argument("--mode", choices=("bundle", "tree", "lua", "sprites"), default="tree")
        else:
            command.add_argument("--binary", type=Path, required=True, **({"action": "append"} if name == "native" else {}))
            if name == "native":
                command.add_argument("--metadata", type=Path, required=True)
            if name == "trace":
                command.add_argument("--rva", help="Optional start RVA, e.g. 0x1000")
    return result


def interactive():
    print("Tiles Survive Extraction Kit\n1. Check runtime\n2. Find game inputs\n3. Extract configuration\n4. Decode language\n5. Help")
    choice = input("Select [1-5]: ").strip()
    if choice == "1":
        return ["doctor"]
    if choice == "2":
        return ["discover", "--game-root", input("Game installation folder: ").strip().strip('"')]
    if choice in ("3", "4"):
        source = input("Full path to config pack or encrypted language file: ").strip().strip('"')
        output = input("New output folder: ").strip().strip('"')
        if choice == "3":
            return ["config", "--pack", source, "--output", output, "--decode"]
        return ["language", "--source", source, "--output", output]
    return ["--help"]


def main():
    args = parser().parse_args(sys.argv[1:] if len(sys.argv) > 1 else interactive())
    try:
        if args.command == "doctor":
            doctor()
        elif args.command == "verify":
            verify()
        elif args.command == "discover":
            discover(args.game_root)
        else:
            run(args)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
