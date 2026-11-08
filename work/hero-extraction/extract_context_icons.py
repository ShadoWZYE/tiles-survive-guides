"""Extract the exact Signature/Behemoth/Research sprites referenced by the context catalog."""
import argparse
import json
import sys
from pathlib import Path
from extract_hero_images import asset_bundle_ids, bundle_hashes
from export_client_asset import locate_bundle

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--asset-index', type=Path, required=True)
    parser.add_argument('--bundle-list', type=Path, required=True)
    parser.add_argument('--root', type=Path, action='append', required=True)
    parser.add_argument('--stars-only', action='store_true')
    parser.add_argument('--gear-only', action='store_true')
    parser.add_argument('--talents-only', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'work/tools/unitypy'))
    import UnityPy
    catalog = json.loads((ROOT / 'outputs/hero-report/Hero-Army-Context.json').read_text(encoding='utf-8'))
    wanted = {row[key] for group in ['signature', 'behemoths', 'research']
              for row in catalog[group].values() for key in ['icon_asset', 'skill_icon_asset'] if row.get(key)}
    if args.stars_only: wanted = set(catalog['behemoth_star_display']['sprites'])
    if args.gear_only:
        upgrades=json.loads((ROOT/'outputs/hero-report/TilesSurvive-Upgrade-Data.json').read_text(encoding='utf-8'))
        wanted={g['icon_asset'] for g in upgrades['gear'].values()}
    if args.talents_only: wanted = {n['icon_asset'] for b in catalog['faction_talents'].values() for n in b['nodes'].values()}
    ids = asset_bundle_ids(args.asset_index, wanted)
    hashes = bundle_hashes(args.bundle_list, set(ids.values()))
    if wanted - ids.keys():
        raise ValueError('Sprites absent from index: ' + str(sorted(wanted - ids.keys())))
    by_bundle = {}
    for name, bid in ids.items():
        by_bundle.setdefault(hashes[bid], set()).add(name)
    output = ROOT / ('outputs/hero-tool/images/gear-icons' if args.gear_only else 'outputs/hero-tool/images/context-icons')
    output.mkdir(parents=True, exist_ok=True)
    found = set()
    for digest, names in by_bundle.items():
        raw, _ = locate_bundle(args.root, 'G', digest)
        start = raw.find(b'UnityFS')
        if start < 0:
            raise ValueError('Bundle has no UnityFS signature')
        env = UnityPy.load(raw[start:])
        for obj in env.objects:
            if obj.type.name != 'Sprite':
                continue
            sprite = obj.read()
            if sprite.m_Name in names:
                sprite.image.save(output / (sprite.m_Name + '.png'))
                found.add(sprite.m_Name)
    if wanted - found:
        raise ValueError('Missing sprites: ' + str(sorted(wanted - found)))
    print(f'Extracted {len(found)} exact client context sprites.')


if __name__ == '__main__':
    main()
