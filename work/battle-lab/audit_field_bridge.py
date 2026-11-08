"""Verify current field/Lite links and Ray condition scope, without inventing a damage bridge."""
import bisect,hashlib,json,sys
from pathlib import Path
from audit_damage_attribution import fingerprints,IMAGE_SHA,INDEX_SHA
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'work/hero-extraction'))
from refresh_hero_data import verified_tables
from decode_cfg import decode_table

def export(tables,roster):
    types={r['Id']:r for r in tables['survivor_skill_type']}
    skills={r['InternalId']:r for r in tables['survivor_slg_skill_new']}
    effects={r['InternalId']:r for r in tables['survivor_slg_effect_new']}
    heroes={}
    for hero in roster:
        links=[]
        for skill in hero['skills']:
            source=types[skill['internal_name']];field=skills.get(source['SurvivorSlgSkillNew_ID'])
            if field is None:
                links.append({'skill':source['Id'],'linked_field_skill':None});continue
            resolved=[]
            for key in field['SkillEffectNew_ID']:
                effect=effects.get(key)
                if effect is None:raise ValueError('Missing linked field effect')
                resolved.append({k:effect[k] for k in ['Id','Type','EffectAttrRate','TargetTypeLite','TargetPosition','TargetNum','TargetArmy','SpecialTarget','AttackCount','AttackInterval','ExtraTriggerSkill']})
            links.append({'skill':source['Id'],'linked_field_skill':field['Id'],'initial_cd_raw':field['InitialCd'],
                'common_cd_raw':field['CommonCd'],'effects':resolved,'damage_bridge_verified':False})
        heroes[hero['asset_slug']]=links
    return heroes

def main():
    folder=ROOT/'outputs/hero-report';game=Path('C:/Program Files (x86)/FunPlus/Tiles Survive/GameData/GameAssets')
    manifest=(game/'BinaryConfig/BinVersionList_Realtime.json').read_bytes();pack=(game/'BinaryConfigPack.ss').read_bytes()
    wanted={'survivor_skill_type','survivor_slg_skill_new','survivor_slg_effect_new','pve_condition'}
    private=ROOT/'tmp/ray-field-2026-11-07';private.mkdir(exist_ok=True);tables={};hashes={}
    for name,(_,raw) in verified_tables(pack,json.loads(manifest),wanted,game/'BinaryConfig').items():
        target=private/(name+'.cfg');target.write_bytes(raw);tables[name]=decode_table(target)['rows'];hashes[name]=hashlib.sha256(raw).hexdigest()
    snapshot=json.loads((folder/'Hero-Combat-Audit.json').read_text(encoding='utf-8'))['provenance']
    if hashlib.sha256(pack).hexdigest()!=snapshot['config_pack_sha256'] or any(hashes[name]!=snapshot['table_sha256'][name] for name in ['pve_condition','survivor_skill_type']):
        raise ValueError('Current shared tables differ from the audited native/config snapshot')
    native=ROOT/'tmp/scoring-close-2026-11-05/native';image=(native/'verified/native-rva-image.bin').read_bytes();index=(native/'verified/method-index.json').read_bytes()
    methods=fingerprints(image,index,(native/'metadata.dat').read_bytes(),
        {'SkillBase':['AddConditionTriggerListener'],'ConditionCheckerManager':['GetConditionCheckerByConfig','GetConditionCheckerByConfigId'],
         'ConditionSkillFinishChecker':['OnBeginCheck','OnTargetEntitySkillFinish'],'RaidEntityManager':['GetSkillTargetsBySkillData'],'RaidUtils':['FilterTargetNum']},
        {'PveConditionConfigCell':{'ConditionTarget':72,'ConditionTarget_2':76},'ConditionSkillFinishChecker':{'_targetEntity':48,'_tarSkillType':56}})
    records=json.loads(index);overload=next(r for r in records if r['rva']==0x28d9150 and r['type']=='ConditionCheckerManager' and r['name']=='GetConditionCheckerByConfigId')
    addresses=sorted({r['rva'] for r in records});end=addresses[bisect.bisect_right(addresses,overload['rva'])]
    methods.append({**overload,'byte_count':end-overload['rva'],'code_sha256':hashlib.sha256(image[overload['rva']:end]).hexdigest()})
    condition=next(r for r in tables['pve_condition'] if r['Id']=='ray_skill_3')
    assert condition['Type']==19 and condition['ConditionTarget']==condition['ConditionTarget_2']==0 and condition['ParamInt']==[1] and not condition['ParamString'] and not condition['ConditionAnd'] and not condition['ConditionOr']
    roster=json.loads((folder/'TilesSurvive-Hero-Data.json').read_text(encoding='utf-8'))
    heroes=export(tables,roster);all_effects=[e for h in heroes.values() for s in h for e in s.get('effects',[])]
    result={'schema':1,'client_build':'2.6.400.304','native_methods':methods,'private_image_sha256':IMAGE_SHA,'private_index_sha256':INDEX_SHA,
        'manifest_sha256':hashlib.sha256(manifest).hexdigest(),'config_pack_sha256':hashlib.sha256(pack).hexdigest(),'table_sha256':hashes,
        'roster_sha256':hashlib.sha256((folder/'TilesSurvive-Hero-Data.json').read_bytes()).hexdigest(),
        'heroes':heroes,'linked_effect_count':len(all_effects),'type_11100_count':sum(e['Type']==11100 for e in all_effects),
        'ray_trigger':{'scope':'owner_active_completion','condition':{k:condition[k] for k in ['Id','Type','ParamInt','ConditionTarget','ConditionTarget_2']},
            'trace':[{'rva':'0x292866a','finding':'SkillBase reads its OwnerObj, passes it as the condition source at 0x2928682, and calls the condition factory at 0x292868f.'},
                     {'rva':'0x28d9217','finding':'ConditionTarget zero retains the source entity; the Type-19 factory binds that entity to the finish checker.'},
                     {'rva':'0x28e5c36','finding':'Subscribes to the bound entity skill-over stream; interrupted completions are rejected at 0x28e5d38.'}]},
        'target_cap_trace':{'rva':'0x297edff','finding':'GetSkillTargetsBySkillData passes EffectiveSurvivor to FilterTargetNum before area filtering. FilterTargetNum limits distance-cull entities, not guaranteed impacts; do not multiply damage by this raw field.'},
        'field_damage_bridge_verified':False,'scope':'Static config identity and selected native dispatch only. Field/Lite Type-11100 execution, cooldown units and original server formula remain unverified.',
        'hotfix_inventory':'Cached-Combat-Hotfix-Audit.json','runtime_model_weights_changed':False}
    (folder/'Field-Bridge-Audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f"Verified owner-only Ray trigger and {len(heroes)} hero field links; {result['type_11100_count']}/{len(all_effects)} linked effects use Type 11100. No damage multipliers inferred.")

if __name__=='__main__':main()
