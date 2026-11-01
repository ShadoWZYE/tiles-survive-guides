"""Inventory offline combat dependencies; never infer a complete battle graph.

Inputs are local files only. Raw CFGs/timelines stay private. Published output is
a selected numeric/reference audit, not a redistribution of game scripts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from decode_cfg import decode_table
from refresh_hero_data import verified_tables

TABLES = {'survivor_skill_type', 'pve_new_skill', 'pve_skill_release', 'pve_new_effect', 'pve_new_buff', 'pve_condition', 'pve_new_monster'}


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
            'summon_lifetime_ms': row.get('SummonLifeTime', 0),
            'summon_template_id':row.get('EffectParam1','') if row['Type']==7 else '',
            'summon_stat_rates_per_mille':[row.get(k,0) for k in ['SummonRateAtk','SummonRateDef','SummonRateHp']] if row['Type']==7 else [],
            'buff_id': row.get('EffectParam1', '') if row['Type'] == 4 else '',
            'target_type': row.get('TargetType'),
            'return_condition': row.get('EffectReturnCondition', ''),
            'unlock_condition': row.get('UnlockCondition'),
            'property_sources':row.get('EffectConstantSource',[]),
            'property_ids':row.get('EffectConstantAttrId',[]),
            'property_rates_per_mille':row.get('EffectConstantAttrRate',[]),
            'has_attribute_fixes':bool(row.get('EffectAttrFixSource')),
            'has_property_sources': bool(row.get('EffectConstantSource'))}


def immediate_hit_events(timeline):
    """Only literal top-level immediate projectiles, not nested or traveling hits."""
    result=[]
    for stage in timeline.get('Stages', []):
        for action in stage.get('Actions', []):
            if action.get('Action') != 'Projectile' or action.get('Type') != 'Immediate':continue
            for hit in action.get('HitActions', []):
                if hit.get('Action') == 'RaidEvent' and hit.get('RaidEventType') == 1:
                    result.append({'reference':hit.get('StringParam0',''),'stage_time_seconds':stage.get('Time')})
    return result


def condition_dependencies(seeds, conditions):
    """Selected condition graph, including nested AND/OR gates; never assume uptime."""
    found, pending = {}, list(seeds)
    while pending:
        key = pending.pop()
        if not key or key in found or key not in conditions: continue
        row = conditions[key]
        found[key] = {k: row[k] for k in ['InternalId','Id','Type','ParamInt','ParamString',
                                        'ConditionAnd','ConditionOr','ConditionTarget','ConditionTarget_2']}
        pending.extend(row['ConditionAnd'] + row['ConditionOr'])
    return [found[k] for k in sorted(found)]


def release_timing(release, timeline, takes):
    """Uninterrupted release occupancy at owner speed 1; no inferred clip endpoint."""
    take = timeline.get('Take') if timeline else None
    clip = takes.get(take)
    waits = [release.get('PreWait', 0), release.get('AfterWait', 0)]
    duration = None
    basis = 'missing_timeline_or_clip'
    if min(waits) >= 0:
        if not release.get('SkillEvent'):
            duration, basis = 0., 'no_clip'
        elif timeline:
            if release.get('LoopTime', 0) > 0:
                duration, basis = release['LoopTime']/1000, 'explicit_loop_time'
            elif timeline.get('CustomLength', 0) > 0:
                duration, basis = timeline['CustomLength'], 'explicit_custom_length'
            elif clip and clip['duration_seconds'] > 0:
                speed = release.get('Speed', 0)/1000 if release.get('Speed', 0) > 0 else 1
                duration, basis = clip['duration_seconds']/speed, 'bound_override_clip'
        if duration is not None: duration += sum(waits)/1000
    return {'release_id':release['Id'],'take':take,'basis':basis,
            'clip_name':clip['clip_name'] if clip else None,
            'clip_duration_seconds':clip['duration_seconds'] if clip else None,
            'duration_at_unit_speed_seconds':duration}


def timed_dispatches(release, timeline, takes, start=0):
    """Direct dispatch times only: traveling launches never become impact times."""
    timing=release_timing(release,timeline,takes)
    duration=timing['duration_at_unit_speed_seconds']
    if start is None or duration is None or not timeline or timeline.get('Loop') or release.get('LoopTime',0)>0 or timeline.get('Speed',1)!=1:
        return []
    speed=release.get('Speed',0)/1000 if release.get('Speed',0)>0 else 1
    result=[]
    for stage in timeline.get('Stages',[]):
        at=stage.get('Time')
        if not isinstance(at,(int,float)) or not math.isfinite(at) or at<0:continue
        offset=release.get('PreWait',0)/1000+at/speed
        if offset>duration+1e-9:continue
        for action in stage.get('Actions',[]):
            hits=([action] if action.get('Action')=='RaidEvent' else
                  action.get('HitActions',[]) if action.get('Action')=='Projectile' and action.get('Type')=='Immediate' else [])
            for hit in hits:
                if hit.get('Action')=='RaidEvent' and hit.get('RaidEventType')==1:
                    result.append({'reference':hit.get('StringParam0',''),'offset_seconds':start+offset})
    return result


def summon_inventory(seeds,effects,monsters,skills,releases,timelines):
    """Follow actor skill references without promoting dependencies to damage."""
    pending=sorted(seeds);seen=set();result=[]
    by_number={r['InternalId']:r for r in effects.values()}
    while pending:
        ref=pending.pop()
        if ref in seen:continue
        seen.add(ref);effect=effects.get(ref)
        if not effect or effect['Type']!=7:continue
        monster=monsters.get(effect.get('EffectParam1'));missing=[];nodes=[]
        if monster:
            todo=[int(k) for k in monster['SkillConfig']];visited=set()
            while todo:
                key=todo.pop()
                if key in visited:continue
                visited.add(key);skill=skills.get(key)
                if not skill:
                    missing.append('skill:'+str(key));continue
                refs=set()
                for release_id in skill['SkillRelease']:
                    release=releases.get(release_id)
                    if not release:
                        missing.append('release:'+str(release_id));continue
                    for number in release.get('SkillNewEffect',[]):
                        if number in by_number:refs.add(by_number[number]['Id'])
                        else:missing.append('effect:'+str(number))
                    name=release.get('SkillEvent')
                    if name:
                        timeline=timelines.get(name)
                        if timeline is None:missing.append('timeline:'+name)
                        else:refs.update(e['reference'] for e in events(timeline))
                missing.extend('effect:'+r for r in refs if r not in effects)
                pending.extend(r for r in refs if r in effects and effects[r]['Type']==7)
                nodes.append({'id':skill['Id'],'type':skill['Type'],'cooldown_ms':skill['Cooldown'],
                    'pre_cooldown_ms':skill['PreCooldown'],'condition_id':skill.get('Condition'),
                    'attack_targets':skill['AttackTarget'],'attack_area':skill['AttackArea'],
                    'configured_level':monster['SkillConfig'].get(str(key)),
                    'effects':[effect_summary(effects[r]) for r in sorted(refs) if r in effects]})
                todo.extend(skill['SubSkill'])
        else:missing.append('actor_template:'+str(effect.get('EffectParam1')))
        result.append({'effect_id':ref,'template_id':effect.get('EffectParam1'),
            'actor_type':monster['Type'] if monster else None,
            'lifetime_ms':effect.get('SummonLifeTime',0),
            'stat_rates_per_mille':[effect.get(k,0) for k in ['SummonRateAtk','SummonRateDef','SummonRateHp']],
            'skills':sorted(nodes,key=lambda n:n['id']),'missing_references':sorted(set(missing)),
            'scored_as_executed_damage':False})
    return sorted(result,key=lambda r:r['effect_id'])


def build_report(data, tables, timelines, animations=None):
    types = {r['Id']: r for r in tables['survivor_skill_type']}
    skills = {r['InternalId']: r for r in tables['pve_new_skill']}
    releases = {r['InternalId']: r for r in tables['pve_skill_release']}
    effects = {r['Id']: r for r in tables['pve_new_effect']}
    effects_by_number = {r['InternalId']: r for r in tables['pve_new_effect']}
    buffs = {r['Id']: r for r in tables.get('pve_new_buff', [])}
    monsters={r['Id']:r for r in tables.get('pve_new_monster',[])}
    conditions = {r['InternalId']: r for r in tables.get('pve_condition', [])}
    heroes = {}
    for slug, hero in data['heroes'].items():
        takes = (animations or {}).get('heroes', {}).get(slug, {}).get('takes', {})
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
            # Collect child graphs without claiming every dependency executes.
            nodes, seen, pending = [], set(), [runtime] if runtime else []
            while pending:
                node = pending.pop()
                if node['InternalId'] in seen: continue
                seen.add(node['InternalId'])
                cond = conditions.get(node.get('Condition'))
                node_effects, node_events, timing, immediate, dispatches = set(), [], [], [], []
                elapsed=0.
                for release_id in node['SkillRelease']:
                    release = releases.get(release_id)
                    if not release:
                        timing.append({'duration_at_unit_speed_seconds':None,'basis':'missing_release'})
                        elapsed=None
                        continue
                    node_effects.update(effects_by_number[n]['Id'] for n in release.get('SkillNewEffect', []) if n in effects_by_number)
                    timeline = timelines.get(release.get('SkillEvent'))
                    timing.append(release_timing(release, timeline, takes))
                    dispatches.extend(timed_dispatches(release,timeline,takes,elapsed))
                    duration=timing[-1]['duration_at_unit_speed_seconds']
                    elapsed=elapsed+duration if elapsed is not None and duration is not None else None
                    if timeline:
                        immediate.extend(immediate_hit_events(timeline))
                        for stage in timeline.get('Stages', []):
                            node_events.extend({'stage_time_seconds':stage.get('Time'), **e} for e in events(stage.get('Actions', [])))
                node_effects.update(e['reference'] for e in node_events)
                nodes.append({'id':node['Id'],'cooldown_ms':node['Cooldown'],
                    'skill_type':node['Type'],'priority':node['SkillPriority'],'pre_cooldown_ms':node['PreCooldown'],
                    'condition':{k:cond[k] for k in ['Id','Type','ParamInt','ParamString','ConditionAnd','ConditionOr']} if cond else None,
                    'attack_targets':node['AttackTarget'],'attack_area':node['AttackArea'],
                    'events':node_events,'effect_ids':sorted(node_effects),'children':node['SubSkill'],
                    'release_timings':timing,
                    'immediate_hit_events':immediate,
                    'timed_dispatches':dispatches,
                    'cast_duration_at_unit_speed_seconds':sum(t['duration_at_unit_speed_seconds'] for t in timing) if timing and all(t['duration_at_unit_speed_seconds'] is not None for t in timing) else None,
                    'effects':[effect_summary(effects[n]) for n in sorted(node_effects) if n in effects]})
                for child in node['SubSkill']:
                    if child in skills: pending.append(skills[child])
                    else: absent.append(f'child_skill:{child}')
            # Follow child and periodic buff dependencies without promoting them to hits.
            dependency_ids = {e['id'] for n in nodes for e in n['effects']} | references
            buff_rows, seen_buffs = [], set()
            pending_effects = sorted(dependency_ids)
            while pending_effects:
                effect = effects.get(pending_effects.pop())
                buff_id = effect.get('EffectParam1') if effect and effect['Type'] == 4 else None
                if buff_id not in buffs or buff_id in seen_buffs: continue
                seen_buffs.add(buff_id); b = buffs[buff_id]
                buff_rows.append({k:b[k] for k in ['Id','Type','Time','Plus','PlusType','Param1','Param2','Param3','ParamString','EffectCondition','Effect','EffectLimit']})
                if b['Type'] in (10,16):
                    for ref in b['ParamString']:
                        if ref in effects and ref not in dependency_ids:
                            dependency_ids.add(ref);pending_effects.append(ref)
            buff_rows.sort(key=lambda b:b['Id'])
            condition_seeds = [skills[k].get('Condition') for k in seen]
            condition_seeds += [effects[k].get('UnlockCondition') for k in dependency_ids if k in effects]
            condition_seeds += [b['EffectCondition'] for b in buff_rows]
            audited.append({'id': exported['id'], 'runtime_skill': runtime['Id'] if runtime else None,
                            'base_cooldown_ms': runtime['Cooldown'] if runtime else None,
                            'base_pre_cooldown_ms': runtime['PreCooldown'] if runtime else None,
                            'timeline_events': actions, 'referenced_effects': matched,
                            'skill_nodes':nodes,'referenced_buffs':buff_rows,
                            'dependency_effects':[effect_summary(effects[k]) for k in sorted(dependency_ids) if k in effects],
                            'referenced_conditions':condition_dependencies(condition_seeds, conditions),
                            'summoned_actors':summon_inventory(dependency_ids,effects,monsters,skills,releases,timelines),
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
    p.add_argument('--animations', type=Path, help='Selected base-model override clip audit')
    p.add_argument('--native-audit', type=Path, help='Hash-gated selected current native base-path audit')
    args = p.parse_args()
    pack = args.pack.read_bytes(); manifest = args.manifest.read_bytes()
    data = json.loads(args.upgrade_data.read_text(encoding='utf-8'))
    if data.get('provenance', {}).get('config_pack_sha256') != hashlib.sha256(pack).hexdigest():
        raise ValueError('Upgrade data does not identify the same config-pack snapshot.')
    verified = verified_tables(pack, json.loads(manifest), TABLES, args.manifest.parent)
    for name, (_, raw) in verified.items():
        expected = data.get('source_hashes', {}).get(name)
        if expected and expected != hashlib.sha256(raw).hexdigest():
            raise ValueError(f'Progression/combat table snapshot mismatch: {name}')
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
    animations = json.loads(args.animations.read_text(encoding='utf-8')) if args.animations else None
    if animations:
        for key in ['config_pack_sha256','manifest_sha256']:
            if animations['provenance'][key] != data['provenance'][key]:
                raise ValueError('Animation/progression snapshot mismatch: '+key)
        if animations['client_build'] != data['client_build']:
            raise ValueError('Animation/progression native build mismatch')
    report = build_report(data, tables, timelines, animations)
    if args.native_audit:
        native=json.loads(args.native_audit.read_text(encoding='utf-8'))
        if native['client_build']!=data['client_build']:raise ValueError('Native/progression build mismatch')
        from audit_native_combat import CURRENT_SHA256,METADATA_SHA256
        if native['binary_sha256']!=CURRENT_SHA256 or native['metadata_sha256']!=METADATA_SHA256:raise ValueError('Native profile fingerprint mismatch')
        report['native_audit']={k:native[k] for k in ['client_build','binary_sha256','metadata_sha256','verified_claims','scope']}
        report['native_audit']['selected_method_count']=len(native['methods'])
        report['native_audit']['audit_sha256']=hashlib.sha256(args.native_audit.read_bytes()).hexdigest()
    if animations:report['animation_audit_sha256']=hashlib.sha256(args.animations.read_bytes()).hexdigest()
    report['provenance'] = {'native_build': data['client_build'], 'audit_date': data['provenance']['audited_date'],
                            'config_pack_sha256': hashlib.sha256(pack).hexdigest(),
                            'manifest_sha256': hashlib.sha256(manifest).hexdigest(),
                            'table_sha256': {n: hashlib.sha256(raw).hexdigest() for n, (_, raw) in verified.items()},
                            'timeline_export_sha256': hashes}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Audited {len(report["heroes"])} heroes; {len(timelines)} timeline assets. Complete graphs: 0.')


if __name__ == '__main__':
    main()
