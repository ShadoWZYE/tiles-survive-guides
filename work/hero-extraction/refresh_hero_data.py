"""Refresh normalized planner data from a manifest-verified offline cache snapshot.

Never attaches to the game. Raw tables remain in the caller's private directory.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from build_hero_report import TABLE_FILES, build, write_outputs
from build_upgrade_data import export, export_targeted
from decode_language_pack import decode_language_pack
from extract_config_pack import read_entries

TABLES = {name.split('_', 1)[1].removesuffix('.cfg') for name in TABLE_FILES.values()} | {
    'survivor_rank_main', 'survivor_level', 'pve_new_skill', 'survivor_equipment_npp',
    'survivor_equipment_level_npp', 'itemlist', 'survival_card_pool',
    'survival_up_card_pool', 'survival_up_drop_contrast'}

def verified_tables(pack: bytes, manifest: dict, wanted: set[str]) -> dict[str, tuple[int, bytes]]:
    tables = {}
    for entry in read_entries(pack):
        if entry.name not in wanted:
            continue
        if entry.name in tables:
            raise ValueError(f'Duplicate active table: {entry.name}')
        raw = pack[entry.offset:entry.offset + entry.size]
        # MD5 is the game's content identity, not a security guarantee.
        if hashlib.md5(raw).hexdigest() != manifest.get(entry.name):
            raise ValueError(f'Cache/manifest mismatch: {entry.name}')
        tables[entry.name] = (entry.index, raw)
    if wanted - tables.keys():
        raise ValueError(f'Missing current tables: {sorted(wanted - tables.keys())}')
    return tables

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--language', type=Path, required=True)
    parser.add_argument('--client-build', required=True)
    parser.add_argument('--audited-date', required=True)
    parser.add_argument('--private-output', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pack = args.pack.read_bytes(); manifest_bytes = args.manifest.read_bytes()
    tables = verified_tables(pack, json.loads(manifest_bytes), TABLES)
    args.private_output.mkdir(parents=True, exist_ok=True)
    if list(args.private_output.glob('*.cfg')):
        raise ValueError('Use a fresh private output directory; stale extracts are not accepted.')
    for name, (index, raw) in tables.items():
        (args.private_output / f'{index:04}_{name}.cfg').write_bytes(raw)
    heroes = build(args.private_output, args.language)
    data = export(args.private_output, heroes, args.client_build, decode_language_pack(args.language))
    data['targeted_draft'] = export_targeted(args.private_output, args.private_output, heroes, data['source_hashes'])
    old_path = args.output / 'TilesSurvive-Upgrade-Data.json'
    old = json.loads(old_path.read_text(encoding='utf-8')) if old_path.exists() else {'heroes': {}}
    old_roster_path = args.output / 'TilesSurvive-Hero-Data.json'
    old_roster = {h['asset_slug']: h for h in json.loads(old_roster_path.read_text(encoding='utf-8'))} if old_roster_path.exists() else {}
    new_roster = {h['asset_slug']: h for h in heroes}
    common = old['heroes'].keys() & data['heroes'].keys()
    changes = {slug: [field for field, value in data['heroes'][slug].items() if old['heroes'][slug].get(field) != value]
               for slug in sorted(common) if old['heroes'][slug] != data['heroes'][slug]}
    # Exclude comparative ranks (which naturally move when the roster expands).
    stat_fields = ['max_level', 'max_level_attack', 'max_level_defense', 'max_level_health', 'max_level_battle_power', 'skills']
    roster_changes = {slug: [field for field in stat_fields if old_roster[slug].get(field) != new_roster[slug][field]]
                      for slug in sorted(old_roster.keys() & new_roster.keys())}
    roster_changes = {slug: fields for slug, fields in roster_changes.items() if fields}
    provenance = {'audited_date': args.audited_date, 'native_build': args.client_build,
        'config_pack_sha256': hashlib.sha256(pack).hexdigest(),
        'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
        'language_sha256': hashlib.sha256(args.language.read_bytes()).hexdigest(),
        'tables_verified': len(tables), 'heroes_verified': len(heroes),
        'previous_heroes_compared': len(common), 'progression_changes': changes,
        'roster_stat_skill_changes': roster_changes,
        'added_heroes': sorted(data['heroes'].keys() - old['heroes'].keys()),
        'scope': 'Current local cache matched to BinVersionList_Realtime; no server overrides or full battle runtime simulated.'}
    data['provenance'] = provenance
    write_outputs(heroes, args.output, args.client_build)
    (args.output / 'TilesSurvive-Upgrade-Data.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    (args.output / 'Hero-Config-Audit.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(provenance, indent=2))

if __name__ == '__main__':
    main()
