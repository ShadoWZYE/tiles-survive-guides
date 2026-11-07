"""Reproduce catalogue exclusions and selected UI/native provenance from private extracted files."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'work/battle-lab'))
from decode_cfg import decode_table
from audit_damage_attribution import fingerprints,IMAGE_SHA

def main():
    source=ROOT/'tmp/army-context-2026-11-04';private=ROOT/'tmp/field-bridge-2026-11-07';native=ROOT/'tmp/scoring-close-2026-11-05/native'
    tables={name:decode_table(source/(name+'.cfg'))['rows'] for name in ['research_tree','behemoth_base','survivor_skill_type','survivor_slg_skill_new','survivor_slg_effect_new']}
    methods=fingerprints((native/'verified/native-rva-image.bin').read_bytes(),(native/'verified/method-index.json').read_bytes(),(native/'metadata.dat').read_bytes(),{'ResearchTreeConfigCell':['CanShow'],'ResearchModule':['IsTreeUnlock','GetTreeLearnedCount']},{'ResearchTreeConfigCell':{'ShowUnlock':64}})
    prefab=private/'titan-prefab';objects={int(p.stem.rsplit('-',1)[0]):json.loads(p.read_text(encoding='utf-8')) for p in prefab.glob('*.json')};images=[]
    for obj in objects.values():
        if 'm_FillMethod' not in obj:continue
        name=objects[obj['m_GameObject']['m_PathID']]['m_Name']
        if not name.startswith('p_star_icon_'):continue
        images.append({'name':name,'fill_method':obj['m_FillMethod'],'fill_origin':obj['m_FillOrigin'],'clockwise':obj['m_FillClockwise']})
    assert len(images)==5 and all((x['fill_method'],x['fill_origin'],x['clockwise'])==(4,1,0) for x in images)
    kinds=tables['survivor_skill_type'];skills={r['InternalId']:r for r in tables['survivor_slg_skill_new']};effects={r['InternalId']:r for r in tables['survivor_slg_effect_new']};links=[]
    for slug in ['rosie','freja','becca','maddie','ray']:
        for kind in kinds:
            if kind['Id'] not in [f'survivor_{slug}_attack',*[f'survivor_{slug}_skill_{i}' for i in range(1,4)]]:continue
            skill=skills[kind['SurvivorSlgSkillNew_ID']]
            links.append({'hero':slug,'skill':kind['Id'],'raid_skill_id':kind['RaidNewSkill'],'field_skill':skill['Id'],'initial_cd_raw':skill['InitialCd'],'common_cd_raw':skill['CommonCd'],'effects':[{k:effects[e][k] for k in ['Id','Type','EffectAttrRate','TargetTypeLite','TargetNum','AttackCount']} for e in skill['SkillEffectNew_ID']]})
    result={'schema':1,'client_build':'2.6.400.304','private_image_sha256':IMAGE_SHA,'native_methods':methods,
      'research':{'legacy_excluded':[r['Id'] for r in tables['research_tree'] if r['IsOld']], 'faction_branches':[{'id':r['Id'],'feature_gate':r['ShowUnlock'],'research_prerequisites':r['NeedResearchTree']} for r in tables['research_tree'] if r['InternalId'] in [4300013,4300014,4300015,4300016]],'static_trace':'ResearchTreeConfigCell.CanShow passes ShowUnlock at offset 64 to FeatureOpenModule.IsFeatureOpen. IsTreeUnlock separately checks learned-tree prerequisites. GetTreeLearnedCount increments its learned count for topology child entries passing IsLearn. This does not establish the live gate state or inspect active ILFix overrides.'},
      'behemoths':{'normal_catalogue':['caser','water_dragon'],'unavailable_excluded':[{'id':r['Id'],'server_open_days':r['ServerOpenDays'],'name_key':r['ArticleName'],'icon':r['PhotoIcon']} for r in tables['behemoth_base'] if r['ServerOpenDays']>=99999],'release_note':'99999 is a configured gate, not a future release announcement. griffon_eagle shares water_dragon name/icon keys; their records are not merged or added together.'},
      'star_fill':{'asset':'p_titan_star','bundle_digest':'69df84a87541042f926c7ccd149c8a46','asset_list_build':'2.6.400.312','lua_sha256':hashlib.sha256((source.parent/'army-completion-2026-11-04/lua-titan/TitanStarCountComponent.lua').read_bytes()).hexdigest(),'images':sorted(images,key=lambda x:x['name']),'unity_enum_source':'https://github.com/Unity-Technologies/uGUI/blob/main/com.unity.ugui/Runtime/UGUI/UI/Core/Image.cs','interpretation':'Radial360, right origin, counter-clockwise. Lua sets partial fill to remaining steps / 6.'},
      'selected_field_skill_links':links,'field_damage_formula_identified':False,'field_scope':'Selected linked Lite effect records have Type 11100 and zero EffectAttrRate. These rows do not expose a verified numerical damage formula. RaidNewSkill is a separate link; substituting its coefficient/animation into the original world report remains unverified.'}
    out=ROOT/'outputs/hero-report/Planner-Catalog-Audit.json';out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('Audited gated research, unavailable Behemoths, five star images and',len(links),'field skill links.')
if __name__=='__main__':main()
