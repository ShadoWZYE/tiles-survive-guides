"""Build transparent low-confidence all-hero reference estimates from audited data.

This is an inference model, not an implementation of the game's combat engine.
"""
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def presentation_effect(identifier):
    name = identifier.lower()
    return name.startswith('text_') or '_text' in name or name == 'effect_skill_3_empty'


def buff_dispatch_offset(evidence,buff_id):
    nodes=evidence.get('skill_nodes',[])
    if not nodes:return None
    ids={e['id'] for e in nodes[0]['effects'] if e.get('buff_id')==buff_id}
    offsets=[e['offset_seconds'] for e in nodes[0].get('timed_dispatches',[]) if e['reference'] in ids]
    return offsets[0] if len(offsets)==1 else None


def healing_budgets(evidence,params):
    """Raw per-dispatch amounts only, never effective healing or score weights."""
    nodes=evidence.get('skill_nodes',[])
    if not nodes:return []
    root=nodes[0];modifiers={}
    for param in params:
        a=param.split('|')
        if a[0]=='pve_effect' and len(a) in (4,5):
            try:value=float(a[-1])
            except ValueError:continue
            if not math.isfinite(value) or value<0:continue
            key=(a[1],a[2],int(a[3]) if len(a)==5 and a[3].isdigit() else None)
            modifiers[key]=value
    result=[]
    for e in evidence.get('dependency_effects',[]):
        if e['type']!=1 or presentation_effect(e['id']) or e['custom_formula'] or e.get('has_attribute_fixes'):continue
        allowed={'effect_param2','effect_param3','effect_constant_attr_rate'}
        if any(k[0]==e['id'] and k[1] not in allowed for k in modifiers):continue
        terms=[];valid=True
        sources=e.get('property_sources',[]);properties=e.get('property_ids',[]);rates=e.get('property_rates_per_mille',[])
        if len(sources)!=len(properties) or len(sources)!=len(rates):continue
        for i,(owner,prop,rate) in enumerate(zip(sources,properties,rates)):
            if owner not in (0,1) or prop not in (1,2,3) or rate<0:valid=False;break
            terms.append({'owner':'caster' if owner==0 else 'recipient','property':{1:'ATK',2:'DEF',3:'HP'}[prop],
                'coefficient':rate/1000*modifiers.get((e['id'],'effect_constant_attr_rate',i),1)})
        if not valid or e['base_param2']<0 or e['base_param3']<0:continue
        attack=e['base_param2']/1000*modifiers.get((e['id'],'effect_param2',None),1)
        flat=e['base_param3']/1000*modifiers.get((e['id'],'effect_param3',None),1)
        if not (attack or flat or any(t['coefficient'] for t in terms)):continue
        periodic=[b for b in evidence.get('referenced_buffs',[]) if b['Type']==10 and e['id'] in b['ParamString']]
        direct=e['id'] in root['effect_ids']
        conditional=bool(root['condition'] or e.get('unlock_condition') or e.get('return_condition'))
        execution='conditional/dependency'
        if periodic:execution='periodic tick'
        elif direct:execution='direct dispatch'
        elif evidence.get('summoned_actors'):execution='summon-dependent'
        if conditional:execution='conditional '+execution
        result.append({'effect_id':e['id'],'attack_coefficient':attack,'flat_amount':flat,'property_terms':terms,
            'execution':execution,'effective_healing_verified':False})
    return result


def timed_damage_budget(root,damage,combo_node,combo,root_cast,modifiers,representative):
    ids={e['id']:e for e in damage}
    selected=[e for e in root.get('timed_dispatches',[]) if e['reference'] in ids]
    if Counter(e['reference'] for e in selected)!=Counter(e['reference'] for e in root['events'] if e['reference'] in ids):return []
    result=[{'offset_seconds':e['offset_seconds'],'coefficient':ids[e['reference']]['base_param2']/1000*modifiers.get(e['reference'],1)} for e in selected]
    if combo:
        ids={e['id']:e for e in combo}
        selected=[e for e in combo_node.get('timed_dispatches',[]) if e['reference'] in ids]
        if Counter(e['reference'] for e in selected)!=Counter({k:1 for k in ids}):return []
        result.extend({'offset_seconds':root_cast+e['offset_seconds'],'coefficient':ids[e['reference']]['base_param2']/1000*modifiers.get(e['reference'],1)} for e in selected)
    return sorted(result,key=lambda e:e['offset_seconds']) if math.isclose(sum(e['coefficient'] for e in result),representative,abs_tol=1e-10) else []


def permanent_stats(evidence, params):
    """Only unconditionally released, permanent ATK/DEF/HP buffs. No tooltip rows."""
    nodes = evidence.get('skill_nodes', [])
    self_stats, team_stats, selected = [0., 0., 0.], [0., 0., 0.], []
    if not nodes: return self_stats, team_stats, selected
    node = nodes[0]; condition = node['condition']
    if not condition or condition['Type'] != 0 or condition['ConditionAnd'] or condition['ConditionOr']:
        return self_stats, team_stats, selected
    scope = 'self' if node['attack_targets'] == [2] else 'team' if set(node['attack_targets']) == {1,2} and node['attack_area'] == [1,99999] else None
    if not scope: return self_stats, team_stats, selected
    effects = {e['buff_id']:e for e in evidence['referenced_effects'] if e.get('buff_id') and e['id'] in node['effect_ids']}
    overrides = {}
    for param in params:
        a = param.split('|')
        if len(a) == 5 and a[0] == 'pve_buff' and a[2] == 'param3':
            overrides[(a[1],int(a[3]))] = float(a[4])
    for b in evidence.get('referenced_buffs', []):
        if b['Id'] not in effects or '_text' in b['Id'] or b['Type'] != 0 or b['Time'] != -1 or b['Plus'] or b['EffectCondition'] or b['Param2'] or b['ParamString']:
            continue
        if len(b['Param1']) != len(b['Param3']) or any(i not in (1,2,3) for i in b['Param1']):continue
        target_type=effects[b['Id']].get('target_type')
        if target_type not in (0,1):continue
        effect_scope='self' if target_type == 1 else scope
        # Native RaidBuffPropertyModify divides Param3 by 1000; property modifiers add.
        values = [0.,0.,0.]
        for index, prop in enumerate(b['Param1']):values[prop-1] += b['Param3'][index]*overrides.get((b['Id'],index),1)/1000
        for i in range(3):(self_stats if effect_scope == 'self' else team_stats)[i] += values[i]
        selected.append({'id':b['Id'],'scope':effect_scope,'percent':values})
    return self_stats, team_stats, selected


def periodic_budgets(evidence, params):
    """Full-lifetime potential only; one recipient, no overlapping refresh credit."""
    nodes=evidence.get('skill_nodes',[])
    if not nodes:return []
    root=nodes[0]; buffs={b['Id']:b for b in evidence.get('referenced_buffs',[])}
    effects={e['id']:e for e in evidence.get('dependency_effects',[])}
    factors={}
    for p in params:
        a=p.split('|')
        if len(a)==4 and a[0]=='pve_effect' and a[2]=='effect_param2':factors[a[1]]=float(a[3])
    result=[]
    for e in root['effects']:
        b=buffs.get(e.get('buff_id'))
        if not b or b['Type']!=10 or b['Time']<=0 or len(b['Param1'])!=1 or b['Param1'][0]<=0 or b['Plus'] or b['EffectCondition']:continue
        interval=b['Param1'][0];duration=b['Time']
        timing_override=any(p.startswith('pve_buff|'+b['Id']+'|') for p in params)
        # Base lifetime expiry precedes the tick check. Endpoint rounding is not guaranteed.
        ticks=max(0,math.ceil(duration/interval)-1)
        overlaps=root['cooldown_ms']<=0 or root['cooldown_ms']<duration
        for ref in b['ParamString']:
            tick=effects.get(ref)
            if not tick or tick['type'] not in (0,1) or tick['custom_formula'] or tick.get('return_condition') or tick.get('unlock_condition') or presentation_effect(ref):continue
            result.append({'buff_id':b['Id'],'effect_id':ref,'type':tick['type'],
                           'duration_ms':duration,'interval_ms':interval,'nominal_ticks':ticks,
                           'overlapping_refresh':overlaps,'application_condition':e.get('unlock_condition'),
                           'application_offset_seconds':buff_dispatch_offset(evidence,b['Id']),
                           'reapplication_policy':'replace_same_id_and_restart_tick_timer',
                           'coefficient_per_tick':tick['base_param2']/1000*factors.get(ref,1),
                           'scored':tick['type']==0 and not e.get('unlock_condition') and not overlaps and not timing_override and root['condition'] is None})
    return result


def temporary_stats(evidence,params,window_seconds=0):
    """Time-averaged positive self stat buffs; cadence remains an explicit assumption."""
    result=[0.,0.,0.];sources=[]
    nodes=evidence.get('skill_nodes',[])
    if not nodes or nodes[0]['condition'] is not None or nodes[0]['cooldown_ms']<=0:return result,sources
    root=nodes[0];buffs={b['Id']:b for b in evidence.get('referenced_buffs',[])}
    factors={}
    for p in params:
        a=p.split('|')
        if len(a)==5 and a[0]=='pve_buff' and a[2]=='param3':factors[(a[1],int(a[3]))]=float(a[4])
    for e in root['effects']:
        b=buffs.get(e.get('buff_id'))
        is_self=e.get('target_type')==1 or (e.get('target_type')==0 and root['attack_targets']==[2])
        if not is_self or not b or b['Type']!=0 or b['Time']<=0 or b['Plus'] or b['EffectCondition'] or b['Param2'] or b['ParamString']:continue
        if e.get('return_condition') or e.get('unlock_condition') or len(b['Param1'])!=len(b['Param3']) or any(p not in (1,2,3) for p in b['Param1']):continue
        if any(v<0 for v in b['Param3']):continue
        # Do not ignore an unsupported duration modifier and silently use a stale value.
        if any(b['Id'] in p and '|param3|' not in p for p in params):continue
        uptime=min(1,b['Time']/root['cooldown_ms']);values=[0.,0.,0.]
        if window_seconds:
            cast=root.get('cast_duration_at_unit_speed_seconds')
            if cast is None:continue
            first=evidence.get('base_pre_cooldown_ms',0)/1000+cast
            cadence=max(root['cooldown_ms']/1000,cast)
            intervals=[]
            while first < window_seconds:
                intervals.append((first,min(window_seconds,first+b['Time']/1000)))
                first+=cadence
            end=0.;covered=0.
            for start,stop in intervals:
                covered+=max(0,stop-max(start,end));end=max(end,stop)
            uptime=covered/window_seconds
        for i,p in enumerate(b['Param1']):values[p-1]+=b['Param3'][i]*factors.get((b['Id'],i),1)/1000*uptime
        result=[a+b for a,b in zip(result,values)]
        sources.append({'id':b['Id'],'duration_ms':b['Time'],'cadence_ms':root['cooldown_ms'],'assumed_uptime':uptime,'average_percent':values})
    return result,sources


def opening_pressure(evidence,cadence,cast,direct_coefficient,periodic,window):
    """Independent uninterrupted casts, counted at completion; no survival fit."""
    first=(evidence.get('base_pre_cooldown_ms') or 0)/1000
    if cast is None:
        # Unresolved cast timing must not acquire invented full-hit dispatches.
        return None
    time=first+cast;total=0.
    while time <= window+1e-9:
        total+=direct_coefficient
        for p in periodic:
            if not p['scored']:continue
            ticks=min(p['nominal_ticks'],max(0,math.floor((window-time)*1000/p['interval_ms']+1e-9)))
            total+=ticks*p['coefficient_per_tick']
        time+=cadence
    return round(total/window,8)


def finish_trigger(evidence,hero_audit,native):
    """Narrow one-source, no-clip finish -> one-shot delay-buff potential.

    Retains one recipient and requires a buff update after the source finishes.
    Rejects compound gates, stacking, duration/target/property formulas and loops.
    """
    if not native.get('verified_claims',{}).get('delay_buff_fires_once'):return None
    nodes=evidence.get('skill_nodes',[])
    if not nodes:return None
    root=nodes[0];c=root.get('condition')
    if not c or c['Type']!=19 or c['ParamInt']!=[1] or c['ParamString'] or c['ConditionAnd'] or c['ConditionOr']:return None
    conditions=[x for x in evidence.get('referenced_conditions',[]) if x['Id']==c['Id']]
    if len(conditions)!=1 or conditions[0]['ConditionTarget']!=0 or conditions[0]['ConditionTarget_2']!=0:return None
    if root['cast_duration_at_unit_speed_seconds']!=0 or root['skill_type']!=2 or root['events']:return None
    sources=[s for s in hero_audit['skills'] if s['skill_nodes'] and s['skill_nodes'][0]['skill_type']==1 and s['skill_nodes'][0]['condition'] is None]
    if len(sources)!=1 or sources[0]['skill_nodes'][0]['cast_duration_at_unit_speed_seconds'] is None:return None
    buffs={b['Id']:b for b in evidence.get('referenced_buffs',[])}
    if len(root['effects'])!=1:return None
    effect=root['effects'][0];b=buffs.get(effect.get('buff_id'))
    if effect['type']!=4 or effect.get('unlock_condition') or effect.get('return_condition') or not b:return None
    if b['Type']!=16 or b['Plus'] or b['EffectCondition'] or b['EffectLimit'] or b['Param2'] or b['Param3'] or len(b['Param1'])!=1 or len(b['ParamString'])!=1:return None
    if b['Param1'][0]<0 or b['Time']<=b['Param1'][0] or root['cooldown_ms']<=b['Param1'][0]:return None
    damage=[e for e in evidence['dependency_effects'] if e['id']==b['ParamString'][0] and e['type']==0 and not e['custom_formula'] and not e.get('unlock_condition') and not e.get('return_condition') and not e.get('has_property_sources')]
    if len(damage)!=1:return None
    return {'source_skill_id':sources[0]['id'],'cooldown_seconds':root['cooldown_ms']/1000,
            'delay_seconds':b['Param1'][0]/1000,'requires_buff_update':True,'buff_id':b['Id'],'effect_id':damage[0]['id']}


def build(upgrades, audit, roster):
    if audit['provenance']['config_pack_sha256'] != upgrades['provenance']['config_pack_sha256']:
        raise ValueError('Combat audit and progression data must identify the same snapshot.')
    if audit['provenance']['manifest_sha256'] != upgrades['provenance']['manifest_sha256']:
        raise ValueError('Combat audit and progression manifest snapshots differ.')
    result = {'version': 12, 'reference_level': 110, 'reference_rank': 3,
              'reference_step': 6, 'heroes': {}}
    result['opening_scheduler']='single_caster_non_preemptive_configured_priority_scenario'
    result['native_semantics_build']='2.6.200.276'
    result['current_native_semantics_reverified']=False
    result['utility_credit_policy']='single_utility_channel_no_durability_multiplier_or_trait_pair_score'
    native=audit.get('native_audit',{})
    if native:
        if native['client_build']!=upgrades['client_build']:raise ValueError('Native/model build mismatch')
        result['native_semantics_build']=native['client_build']
        result['native_selected_method_count']=native['selected_method_count']
        result['native_audit_sha256']=native['audit_sha256']
        result['native_verification_scope']='selected_current_static_base_paths; full_engine_and_live_patches_unverified'
    for slug, hero in upgrades['heroes'].items():
        stage = next(s for s in hero['stages'] if s['rank'] == 3 and s['step'] == 6)
        level = next(s for s in hero['levels'] if s['level'] == min(110, stage['level_max']))
        ref_stats = [a + b for a, b in zip(stage['stats'], level['stats'])]
        source_skills = {s['internal_name']: s for s in roster[slug]['skills']}
        audited = {s['id']: s for s in audit['heroes'][slug]['skills']}
        curves = []
        for skill in hero['skills']:
            evidence = audited[skill['id']]
            effects = [e for e in evidence['referenced_effects'] if not presentation_effect(e['id'])]
            finish=finish_trigger(evidence,audit['heroes'][slug],native)
            if finish and any(p.startswith(('pve_buff|','pve_skill|')) for row in skill['levels'] for p in row['params']):finish=None
            damage_candidates = [e for e in effects if e['type'] == 0 and not e['custom_formula'] and not e.get('unlock_condition') and e['base_param2'] > 0]
            direct_ids = {event['reference'] for event in evidence.get('timeline_events', [])}
            direct_damage = [e for e in damage_candidates if e['id'] in direct_ids]
            # Prefer explicitly dispatched hit effects to generic display/fallback rows.
            # One representative effect still cannot establish repeated hits or target count.
            periodic_ids={p['effect_id'] for p in periodic_budgets(evidence,[]) if p['scored']}
            damage = direct_damage or [e for e in damage_candidates if e['id'] not in periodic_ids]
            source = source_skills[skill['id']]
            text = ' '.join([source.get('game_description', ''), *[e['id'] for e in effects]]).lower()
            # Dimensionless planning priors. They are deliberately not native effect magnitudes.
            heal_rows=[e for e in effects if e['type']==1]
            unconditional_heal=any(not e.get('unlock_condition') for e in heal_rows)
            utility = (1.3 if unconditional_heal or (not heal_rows and any(t in text for t in
                       ['heal', 'leech', 'recover health', 'recovers health', 'restore health', 'restores health'])) else 0)
            for tokens, weight in [(['shield'], 1.2), (['stun'], .8), (['slow'], .35),
                                   (['atk_down', 'attack reduction'], .6), (['def_down', 'defense reduction'], .8),
                                   (['damage reduction', 'dmg_reduce'], .9)]:
                if any(t in text for t in tokens):
                    utility += weight
            # Type 7 is also used for damage containers (including Maddie's arrow),
            # so its presence/name alone cannot establish a useful summoned ally.
            summon_effects = [e for e in effects if e['type'] == 7 and 'damagezone' not in e['id'].lower()
                              and 'damage_zone' not in e['id'].lower()]
            real_summon = bool(summon_effects) and ('summon' in source.get('game_description', '').lower()
                           or any(e['type'] == 1 for e in effects)
                           or any('dog' in e['id'].lower() or 'frank' in e['id'].lower() for e in summon_effects))
            if real_summon or 'summon' in source.get('game_description', '').lower():
                utility += .6
            cadence = skill['cooldown'] / 1000 if skill['cooldown'] > 0 else (2 if skill['slot'] == 0 else 12)
            cadence = max(.5, cadence)
            # These two inspected basic chains have a non-interrupted parent-finish strike.
            # Conditional counterattacks and other child nodes remain dependency inventory.
            combo = []
            combo_node=None
            nodes = evidence.get('skill_nodes', [])
            root_cast = nodes[0].get('cast_duration_at_unit_speed_seconds') if nodes else None
            child_cast = 0.
            checked_children = {'survivor_rosie_attack':'survivor_rosie_attack_2',
                                'survivor_tarzan_attack':'survivor_tarzan_attack_2'}
            if skill['id'] in checked_children:
                for node in evidence.get('skill_nodes', [])[1:]:
                    c = node['condition']
                    if node['id'] == checked_children[skill['id']] and c and c['Type'] == 19 and c['ParamString'] == [skill['id']] and not c['ParamInt'] and not c['ConditionAnd'] and not c['ConditionOr']:
                        combo = [e for e in node['effects'] if e['type'] == 0 and not e['custom_formula'] and e['base_param2'] > 0 and e['id'] in {x['reference'] for x in node['events']}]
                        # Cooldowns start at each skill's cast start and can overlap casting.
                        # A child's cooldown is not its animation duration or serial queue cost.
                        # Keep the root's nominal budget, as for other inspected skills.
                        if combo:
                            child_cast = node.get('cast_duration_at_unit_speed_seconds')
                            combo_node=node
            # Cooldown overlaps casting. Completion-linked child releases occupy the
            # same caster sequentially; use the full uninterrupted chain duration.
            cast = root_cast + child_cast if root_cast is not None and child_cast is not None else None
            if cast is not None:cadence=max(cadence,cast)
            immediate_counts=Counter(e['reference'] for e in nodes[0].get('immediate_hit_events',[]) if e['reference'] in {d['id'] for d in direct_damage}) if nodes else Counter()
            all_hit_counts=Counter(e['reference'] for e in evidence.get('timeline_events',[]) if e['reference'] in {d['id'] for d in direct_damage})
            counted_hits=bool(direct_damage) and nodes[0]['condition'] is None and cast is not None and immediate_counts==all_hit_counts and all(not e.get('has_property_sources') for e in direct_damage)
            levels = [{'level': 0, 'damage': 0, 'utility': 0, 'self_percent':[0,0,0], 'team_percent':[0,0,0]}]
            uses_prior = False
            stat_sources = []
            temp_sources = []
            for row in skill['levels']:
                modifiers = {}
                for param in row['params']:
                    parts = param.split('|')
                    if len(parts) == 4 and parts[0] == 'pve_effect' and parts[2] == 'effect_param2':
                        try:
                            n = float(parts[3])
                            if math.isfinite(n) and n >= 0:
                                modifiers[parts[1]] = n
                        except ValueError:
                            pass
                # One representative non-text effect per assumed activation, never a sum of references.
                representative = max((e['base_param2'] / 1000 * modifiers.get(e['id'], 1) for e in damage), default=0)
                if counted_hits:
                    representative=sum(immediate_counts[e['id']]*e['base_param2']/1000*modifiers.get(e['id'],1) for e in direct_damage)
                representative += sum(e['base_param2']/1000*modifiers.get(e['id'],1) for e in combo)
                periodic=periodic_budgets(evidence,row['params'])
                periodic_pressure=sum(p['coefficient_per_tick']*p['nominal_ticks'] for p in periodic if p['scored'])
                self_percent, team_percent, stat_sources = permanent_stats(evidence,row['params'])
                temporary_percent,temp_sources=temporary_stats(evidence,row['params'])
                self_percent=[a+b for a,b in zip(self_percent,temporary_percent)]
                # Utility remains a planning prior, but only executed support modifiers scale it.
                support_ids = {e['id'] for e in effects if e['type'] in (1,4,7)} | {b['Id'] for b in evidence.get('referenced_buffs', []) if '_text' not in b['Id']}
                support_factors = []
                for param in row['params']:
                    a = param.split('|')
                    if len(a) in (4,5) and a[1] in support_ids:
                        value=float(a[-1])
                        if math.isfinite(value) and value>=0:support_factors.append(value)
                scaled_utility=utility*max(support_factors,default=1)
                # Unknown is not zero: generic pressure prior when effects cannot be resolved.
                presentation_only = bool(evidence['referenced_effects']) and all(
                    presentation_effect(e['id']) for e in evidence['referenced_effects'])
                unresolved = (not effects and not presentation_only) or bool(evidence['missing_assets']) or bool(evidence['unresolved_event_references']) or any(e['custom_formula'] for e in effects)
                pressure = (representative+periodic_pressure) / cadence if damage or periodic_pressure else ((.25 if skill['slot'] == 0 else .08) if unresolved else 0)
                uses_prior |= not damage and unresolved
                levels.append({'level': row['level'], 'damage': round(pressure, 8), 'utility': scaled_utility,
                               'self_percent':self_percent,'team_percent':team_percent})
                windows={}
                permanent_self,_,_=permanent_stats(evidence,row['params'])
                for window in (10,20,30):
                    opening=opening_pressure(evidence,cadence,cast,representative,periodic,window) if damage or periodic_pressure else None
                    temp, _=temporary_stats(evidence,row['params'],window)
                    windows[str(window)]={'damage':opening if opening is not None else round(pressure,8),
                        'self_percent':[a+b for a,b in zip(permanent_self,temp)]}
                levels[-1]['opening_windows']=windows
                levels[-1]['cast_budget']={
                    'direct_coefficient':representative if damage else (pressure*cadence if not periodic_pressure else 0),
                    'direct_events':timed_damage_budget(nodes[0],direct_damage,combo_node,combo,root_cast,modifiers,representative) if counted_hits else [],
                    'periodic_ticks':[p for p in periodic if p['scored']],
                    'permanent_self_percent':permanent_self,
                    'temporary_buffs':[{'duration_seconds':s['duration_ms']/1000,
                        'application_offset_seconds':buff_dispatch_offset(evidence,s['id']),
                        'percent':[v/s['assumed_uptime'] for v in s['average_percent']]}
                        for s in temp_sources if s['assumed_uptime']>0]}
                if native.get('verified_claims',{}).get('raw_heal_formula'):
                    levels[-1]['healing_budgets']=healing_budgets(evidence,row['params'])
            curves.append({'id': skill['id'], 'slot': skill['slot'], 'levels': levels,
                           'reference_level': min(stage['skill_caps'][skill['slot']], max(r['level'] for r in levels)),
                           'damage_effects': [e['id'] for e in damage], 'cadence_assumed_seconds': cadence,
                           'uses_generic_pressure_prior': uses_prior,
                           'damage_selection_basis': 'direct_hit_reference' if direct_damage else 'periodic_buff_potential' if periodic_ids else 'representative_dependency' if damage else 'no_resolved_damage',
                           'direct_damage_effect_ids': [e['id'] for e in direct_damage],
                           'unresolved_execution': (not evidence['complete_combat_graph_verified']),
                           'has_damage_zone': any(e['type'] == 7 and ('damagezone' in e['id'].lower() or 'damage_zone' in e['id'].lower()) for e in effects)
                                              or (bool(summon_effects) and bool(damage_candidates) and not real_summon),
                           'has_summon_dependency': real_summon,
                           'observed_event_count': len(evidence.get('timeline_events', [])),
                           'base_pre_cooldown_ms': evidence.get('base_pre_cooldown_ms', 0)})
            curves[-1]['permanent_stat_sources']=stat_sources
            curves[-1]['temporary_stat_sources']=temp_sources
            curves[-1]['periodic_budgets']=periodic_budgets(evidence,[])
            curves[-1]['sequence_effect_ids']=[e['id'] for e in combo]
            curves[-1]['cadence_model']='root_cooldown_with_overlapping_child_assumption' if combo else 'configured_cooldown_assumption'
            curves[-1]['cooldown_starts_at_cast_start']=True
            curves[-1]['cast_duration_at_unit_speed_seconds']=cast
            curves[-1]['opening_timing_resolved']=cast is not None
            curves[-1]['queue_eligible']=bool(nodes and nodes[0].get('skill_type') in (0,1) and nodes[0]['condition'] is None and cast is not None and cast>0)
            curves[-1]['priority']=nodes[0].get('priority',0) if nodes else 0
            curves[-1]['animation_limited']=cast is not None and cast > max(.5,skill['cooldown']/1000 if skill['cooldown']>0 else (2 if skill['slot']==0 else 12))
            curves[-1]['direct_hit_counts']=dict(immediate_counts) if counted_hits else {}
            curves[-1]['direct_hit_budget_basis']='unconditional_immediate_timeline_potential' if counted_hits else 'representative_effect'
            if cast is not None:curves[-1]['cadence_model']='max_cooldown_and_uninterrupted_clip_chain_at_unit_speed'
            curves[-1]['conditional_effects']=[{'id':e['id'],'condition_id':e['unlock_condition']} for e in effects if e.get('unlock_condition')]
            curves[-1]['condition_dependencies']=evidence.get('referenced_conditions',[])
            if finish:
                curves[-1]['finish_trigger']=finish
                curves[-1]['damage_selection_basis']='finish_triggered_delayed_effect'
        for curve in curves:
            trigger=curve.get('finish_trigger')
            if not trigger:continue
            parent=next(s for s in curves if s['id']==trigger['source_skill_id'])
            # One parent completion can trigger once, never an independent cooldown clock.
            source_cadence=parent['cadence_assumed_seconds']
            cadence=source_cadence*max(1,math.ceil(curve['cadence_assumed_seconds']/source_cadence-1e-9))
            curve['cadence_assumed_seconds']=cadence
            curve['cadence_model']='completed_source_skill_and_passive_cooldown'
            for row in curve['levels'][1:]:
                row['damage']=round(row['cast_budget']['direct_coefficient']/cadence,8)
                for opening in row['opening_windows'].values():opening['damage']=row['damage']
        result['heroes'][slug] = {'reference_stage': stage['id'], 'reference_level': level['level'],
                                  'reference_stats': ref_stats, 'skills': curves}
    # Fixed anchors from the reference roster: changing a user's build never re-normalizes everyone else.
    raw = []
    for model in result['heroes'].values():
        rates = [next(r for r in s['levels'] if r['level'] == s['reference_level']) for s in model['skills']]
        stats = [v*(1+sum(r['self_percent'][i]+r['team_percent'][i] for r in rates)) for i,v in enumerate(model['reference_stats'])]
        a, d, h = stats
        pressure = sum(r['damage'] for r in rates); utility = sum(r['utility'] for r in rates)
        raw.append([a * (1 + .5 * math.log1p(pressure)),
                    (.7 * h + 30 * d), 1 + utility])
    result['scales'] = [max(r[i] for r in raw) for i in range(3)]
    result['source_pack_sha256'] = upgrades['provenance']['config_pack_sha256']
    result['confidence'] = 'low'
    return result


if __name__ == '__main__':
    folder = ROOT / 'outputs/hero-report'
    read = lambda name: json.loads((folder / name).read_text(encoding='utf-8'))
    model = build(read('TilesSurvive-Upgrade-Data.json'), read('Hero-Combat-Audit.json'),
                  {h['asset_slug']: h for h in read('TilesSurvive-Hero-Data.json')})
    (folder / 'Hero-Estimate-Model.json').write_text(json.dumps(model, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Built low-confidence reference model for {len(model["heroes"])} heroes.')
