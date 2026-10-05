"""Export an installed client asset, including bundles held in SOS/VFS packs.

Read-only with respect to the game. Keep output private; it may contain game code.
Requires UnityPy only for --mode lua or --mode tree.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path

from extract_hero_images import asset_bundle_ids, bundle_hashes


def read_sos_entry(pack: Path, digest: str) -> bytes | None:
    with pack.open("rb") as stream:
        header = stream.read(16)
        if len(header) != 16 or header[:4] != b"\x00SOS":
            return None
        geometry, slots, count = struct.unpack_from("<III", header, 4)
        if geometry not in (2048, 4096) or slots != 4096 or count > slots:
            raise ValueError(f"Unsupported SOS directory: {pack.name}")
        directory = stream.read(slots * (12 + 256))
        if len(directory) != slots * (12 + 256):
            raise ValueError("Truncated SOS directory")
        for index in range(count):
            ordinal, block, size = struct.unpack_from("<III", directory, index * 12)
            if ordinal == 0xFFFFFFFF:
                continue  # Deleted entry in an updated cache pack.
            if ordinal >= slots:
                raise ValueError("SOS name-slot index outside directory")
            pos = slots * 12 + ordinal * 256
            length = directory[pos]
            name = directory[pos + 1:pos + 1 + length].decode("utf-8")
            if name != digest:
                continue
            # Both observed directory geometries use 4096-byte address units.
            # Do not multiply the stored block by the geometry header value.
            offset = block * 4096
            if offset + size > pack.stat().st_size:
                raise ValueError("SOS entry extends outside pack")
            stream.seek(offset)
            return stream.read(size)
    return None


def locate_bundle(roots: list[Path], channel: str, digest: str) -> tuple[bytes, Path]:
    if not re.fullmatch(r"[a-fA-F0-9]{32}", digest):
        raise ValueError("Expected a 32-character bundle digest")
    for root in roots:
        direct = root / "AssetBundle2" / channel / "Windows" / digest
        if direct.is_file():
            return direct.read_bytes(), direct
    for root in roots:
        directory = root / "AssetBundle2" / channel / "Windows"
        if not directory.is_dir():
            continue
        for pack in sorted(directory.glob("*.ss")):
            result = read_sos_entry(pack, digest)
            if result is not None:
                return result, pack
    raise FileNotFoundError(f"Bundle {digest} not found in supplied roots")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-index", type=Path, required=True)
    parser.add_argument("--bundle-list", type=Path, required=True)
    parser.add_argument("--asset", required=True, help="Exact indexed asset name")
    parser.add_argument("--root", type=Path, action="append", required=True,
                        help="GameAssets root; repeat for downloaded and packaged roots")
    parser.add_argument("--channel", choices=("G", "R"), default="G")
    parser.add_argument("--mode", choices=("bundle", "lua", "tree"), default="tree")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ids = asset_bundle_ids(args.asset_index, {args.asset})
    if args.asset not in ids:
        raise SystemExit("Asset name not present in supplied asset index")
    bid = ids[args.asset]
    digest = bundle_hashes(args.bundle_list, {bid})[bid]
    raw, source = locate_bundle(args.root, args.channel, digest)
    start = raw.find(b"UnityFS")
    if start < 0:
        raise SystemExit("No UnityFS signature; do not assume this entry is decoded")
    args.output.mkdir(parents=True, exist_ok=True)
    if args.mode == "bundle":
        (args.output / f"{digest}.bundle").write_bytes(raw[start:])
        count = 1
    else:
        import UnityPy
        environment = UnityPy.load(raw[start:])
        count = 0
        for obj in environment.objects:
            if args.mode == "lua":
                if obj.type.name != "TextAsset":
                    continue
                value = obj.read()
                if not value.m_Name.lower().endswith(".lua"):
                    continue
                name = Path(value.m_Name.replace("\\", "/")).name
                script = value.m_Script
                data = script.encode("utf-8", errors="surrogateescape") if isinstance(script, str) else script
                (args.output / name).write_bytes(data)
            else:
                try:
                    tree = obj.read_typetree()
                    serialized = json.dumps(tree, ensure_ascii=False, indent=2)
                except (ValueError, TypeError, KeyError) as error:
                    print(f"Skipped {obj.path_id} {obj.type.name}: {type(error).__name__}")
                    continue
                (args.output / f"{obj.path_id}-{obj.type.name}.json").write_text(serialized + "\n", encoding="utf-8")
            count += 1
    print(f"asset={args.asset} bundle_id={bid} digest={digest} source={source.name} exported={count}")


if __name__ == "__main__":
    main()
