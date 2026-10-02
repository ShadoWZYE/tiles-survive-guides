from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path


DEFAULT_GAME_ASSETS = Path(
    r"C:\Program Files (x86)\FunPlus\Tiles Survive\ngame\2.6.0.235"
    r"\tspc_Data\StreamingAssets\GameAssets"
)
DEFAULT_DOWNLOADED_ASSETS = Path(
    r"C:\Program Files (x86)\FunPlus\Tiles Survive\GameData\GameAssets"
)


def varuint(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, pos
        shift += 7


def text(data: bytes, pos: int) -> tuple[str, int]:
    length, pos = varuint(data, pos)
    return data[pos : pos + length].decode("utf-8"), pos + length


def asset_bundle_ids(path: Path, wanted: set[str]) -> dict[str, int]:
    data = path.read_bytes()
    count, = struct.unpack_from("<I", data, 0)
    pos = 4
    found: dict[str, int] = {}
    for record_index in range(count):
        record_version, _ = struct.unpack_from("<II", data, pos)
        pos += 8
        if record_version != 1:
            raise ValueError(f"Unsupported asset record version {record_version}")
        name, pos = text(data, pos)
        bundle_id, = struct.unpack_from("<I", data, pos)
        pos += 4
        if name in wanted:
            found[name] = bundle_id
    return found


def bundle_hashes(path: Path, wanted: set[int]) -> dict[int, str]:
    data = path.read_bytes()
    count, = struct.unpack_from("<I", data, 0)
    pos = 4
    found: dict[int, str] = {}
    for record_index in range(count):
        record_version, bundle_id = struct.unpack_from("<II", data, pos)
        pos += 8
        if record_version != 1:
            raise ValueError(
                f"Unsupported bundle record version {record_version} at record {record_index}, offset {pos - 8}"
            )
        _, pos = text(data, pos)
        digest, pos = text(data, pos)
        struct.unpack_from("<QQ", data, pos)
        pos += 16
        _, pos = text(data, pos)  # optional virtual-file-system source
        if bundle_id in wanted:
            found[bundle_id] = digest
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract hero portraits and skill icons from installed Unity bundles")
    parser.add_argument("--game-assets", type=Path, default=DEFAULT_GAME_ASSETS)
    parser.add_argument("--downloaded-assets", type=Path, default=DEFAULT_DOWNLOADED_ASSETS)
    parser.add_argument(
        "--hero-data", type=Path,
        default=Path(__file__).resolve().parents[2] / "outputs" / "hero-report" / "TilesSurvive-Hero-Data.json",
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).resolve().parents[2] / "outputs" / "hero-tool" / "images",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "unitypy"))
    import UnityPy  # type: ignore[import-not-found]

    heroes = json.loads(args.hero_data.read_text(encoding="utf-8"))
    portrait_assets = {hero["portrait_asset"] for hero in heroes if hero.get("portrait_asset")}
    skill_assets = {
        skill["icon_asset"]
        for hero in heroes
        for skill in hero.get("skills", [])
        if skill.get("icon_asset")
    }
    wanted = portrait_assets | skill_assets
    locations: dict[str, tuple[str, str]] = {}

    for channel in ("G", "R"):
        index_dir = args.game_assets / "AssetBundle2" / channel / "Windows"
        asset_indices = sorted(index_dir.glob(f"bundle_assets_{channel}_*.json"))
        bundle_indices = sorted(index_dir.glob(f"bundle_list_{channel}_*.json"))
        if not asset_indices or not bundle_indices:
            continue
        asset_map = asset_bundle_ids(asset_indices[-1], wanted - locations.keys())
        hashes = bundle_hashes(bundle_indices[-1], set(asset_map.values()))
        for asset_name, bundle_id in asset_map.items():
            if bundle_id in hashes:
                locations[asset_name] = (channel, hashes[bundle_id])

    by_bundle: dict[tuple[str, str], set[str]] = {}
    for asset_name, location in locations.items():
        by_bundle.setdefault(location, set()).add(asset_name)

    args.output.mkdir(parents=True, exist_ok=True)
    skill_output = args.output / "skill-icons"
    skill_output.mkdir(parents=True, exist_ok=True)
    extracted: set[str] = set()
    hero_by_asset = {hero["portrait_asset"]: hero for hero in heroes}
    for (channel, digest), names in by_bundle.items():
        candidates = (
            args.downloaded_assets / "AssetBundle2" / channel / "Windows" / digest,
            args.game_assets / "AssetBundle2" / channel / "Windows" / digest,
        )
        bundle_path = next((path for path in candidates if path.exists()), None)
        if bundle_path is None:
            continue
        raw = bundle_path.read_bytes()
        unity_offset = raw.find(b"UnityFS")
        if unity_offset < 0:
            continue
        environment = UnityPy.load(raw[unity_offset:])
        for obj in environment.objects:
            if obj.type.name != "Sprite":
                continue
            sprite = obj.read()
            if sprite.m_Name not in names:
                continue
            if sprite.m_Name in hero_by_asset:
                hero = hero_by_asset[sprite.m_Name]
                sprite.image.save(args.output / f'{hero["asset_slug"]}.png')
            else:
                sprite.image.save(skill_output / f"{sprite.m_Name}.png")
            extracted.add(sprite.m_Name)

    missing = sorted(wanted - extracted)
    print(f"wanted={len(wanted)} extracted={len(extracted)} missing={len(missing)}")
    for name in missing:
        print(f"missing={name}")


if __name__ == "__main__":
    main()
