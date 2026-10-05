"""Inventory offline combat dependencies; never infer a complete battle graph.

Inputs are local files only. Raw CFGs/timelines stay private. Published output is
a selected numeric/reference audit, not a redistribution of game scripts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from decode_cfg import decode_table
from refresh_hero_data import verified_tables

TABLES = {'survivor_skill_type', 'pve_new_skill', 'pve_skill_release', 'pve_new_effect'}


def events(value, context='timeline'):
    """Keep projectile-hit context; a launch time is not an impact time."""
    found = []
    if isinstance(value, dict):
        if value.get('Action') == 'RaidEvent':
            found.append({'reference': value.get('StringParam0', ''),
                          'event_type': value.get('RaidEventType'), 'context': context})
        for key, child in value.items():
            found.extend(events(child, 'projectile_hit' if key == 'HitActions' else context))
    elif isinstance(value, list):
        for child in value:
            found.extend(events(child, context))
    return found


def effect_summary(row):
    return {'id': row['Id'], 'type': row['Type'],
            'base_param2': row['EffectParam2'], 'base_param3': row['EffectParam3'],
            'custom_formula': bool(row.get('Formula')),
            'summon_lifetime_ms': row.get('SummonLifeTime', 0)}


def build_report(data, tables, timelines):
    types = {r['Id']: r for r in tables['survivor_skill_type']}
    skills = {r['InternalId']: r for r in tables['pve_new_skill']}
    releases = {r['InternalId']: r for r in tables['pve_skill_release']}
    effects = {r['Id']: r for r in tables['pve_new_effect']}
    effects_by_number = {r['InternalId']: r for r in tables['pve_new_effect']}
    heroes = {}
    for slug, hero in data['heroes'].items():
        audited = []
        for exported in hero['skills']:
            runtime = skills.get(types[exported['id']]['RaidNewSkill'])
            references, actions, absent = set(), [], []
            if runtime:
                for release_id in runtime['SkillRelease']:
                    release = releases.get(release_id)
                    if not release:
                        absent.append(f'release:{release_id}')
                        continue
                    for number in release.get('SkillNewEffect', []):
                        if number in effects_by_number:
                            references.add(effects_by_number[number]['Id'])
                        else:
                            absent.append(f'effect:{number}')
                    name = release.get('SkillEvent')
                    if name:
                        timeline = timelines.get(name)
                        if timeline is None:
                            absent.append(f'timeline:{name}')
                        else:
                            for stage in timeline.get('Stages', []):
                                for event in events(stage.get('Actions', [])):
                                    actions.append({'stage_time_seconds': stage.get('Time'), **event})
                                    references.add(event['reference'])
            # Skill-level modifiers are additional dependencies, not proof of hits.
            for level in exported['levels']:
                for param in level.get('params', []):
                    parts = param.split('|')
                    if len(parts) >= 4 and parts[0] == 'pve_effect':
                        references.add(parts[1])
            matched = [effect_summary(effects[r]) for r in sorted(references) if r in effects]
            audited.append({'id': exported['id'], 'runtime_skill': runtime['Id'] if runtime else None,
                            'base_cooldown_ms': runtime['Cooldown'] if runtime else None,
                            'base_pre_cooldown_ms': runtime['PreCooldown'] if runtime else None,
                            'timeline_events': actions, 'referenced_effects': matched,
                            'missing_assets': absent,
                            'unresolved_event_references': sorted(references - effects.keys()),
                            'complete_combat_graph_verified': False})
        heroes[slug] = {'name': hero['name'], 'skills': audited}
    return {'heroes_verified': len(heroes), 'heroes': heroes,
            'scope': 'Dependency inventory only. References and modifiers are not executed hit counts. '
                     'No complete combat graph or combat-return ranking certified.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pack', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--upgrade-data', type=Path, required=True)
    p.add_argument('--timelines', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    pack = args.pack.read_bytes(); manifest = args.manifest.read_bytes()
    data = json.loads(args.upgrade_data.read_text(encoding='utf-8'))
    if data.get('provenance', {}).get('config_pack_sha256') != hashlib.sha256(pack).hexdigest():
        raise ValueError('Upgrade data does not identify the same config-pack snapshot.')
    verified = verified_tables(pack, json.loads(manifest), TABLES)
    with TemporaryDirectory(prefix='tiles-combat-audit-') as temp:
        tables = {}
        for name, (_, raw) in verified.items():
            path = Path(temp) / f'{name}.cfg'; path.write_bytes(raw)
            tables[name] = decode_table(path)['rows']
    timelines = {}; hashes = {}
    for path in args.timelines.glob('*-TextAsset.json'):
        raw = path.read_bytes(); asset = json.loads(raw)
        name = asset['m_Name']
        if name in timelines:
            raise ValueError(f'Duplicate timeline: {name}')
        timelines[name] = json.loads(asset['m_Script'])
        hashes[name] = hashlib.sha256(raw).hexdigest()
    report = build_report(data, tables, timelines)
    report['provenance'] = {'native_build': data['client_build'], 'audit_date': data['provenance']['audited_date'],
                            'config_pack_sha256': hashlib.sha256(pack).hexdigest(),
                            'manifest_sha256': hashlib.sha256(manifest).hexdigest(),
                            'table_sha256': {n: hashlib.sha256(raw).hexdigest() for n, (_, raw) in verified.items()},
                            'timeline_export_sha256': hashes}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Audited {len(report["heroes"])} heroes; {len(timelines)} timeline assets. Complete graphs: 0.')


if __name__ == '__main__':
    main()
