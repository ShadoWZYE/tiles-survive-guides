"""Export only traced hero-stat effects; retain unsupported effects as visible limits."""
import argparse,hashlib,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from decode_cfg import decode_table
from decode_language_pack import decode_language_pack
ROOT=Path(__file__).resolve().parents[2]

def export(source,language):
    names=['survivor_exclusive_gear','survivor_exclusive_gear_main','research_main','research_group','research_tree','benefits','benefits_map','benefit_calc','behemoth_base','behemoth_level','behemoth_star_level','behemoth_base_data','survivor_skill_main','survivor_skill_type','survivor_slg_skill_new','survivor_slg_effect_new','effect_buff']
    tables={n:decode_table(source/(n+'.cfg'))['rows'] for n in names}
    lang=decode_language_pack(language);benefits={r['InternalId']:r['Id'] for r in tables['benefits']}
    heroes=json.loads((ROOT/'outputs/hero-report/TilesSurvive-Hero-Data.json').read_text(encoding='utf-8'))
    byid={r['hero_id']:r for r in heroes};scope={}
    for start,target,scene in [(301825,'all','all'),(301828,'all','all'),(301878,'Melee','all'),(301881,'Mid','all'),(301884,'Range','all'),(301939,'all','pve'),(301944,'all','gve'),(301992,'Mountain','all'),(301995,'Wasteland','all'),(301998,'Sky','all'),(302001,'Sea','all')]:
        for i in range(3):scope[start+i]=(target,scene,i)
    # Verify mappings against the client formula and faction alias tables.
    calc={r['Id']:r for r in tables['benefit_calc']}
    assert calc['calc_prop_hero_attack']['BaseBenefit']==301825 and 301828 in calc['calc_prop_hero_attack']['ValueParam']
    for bid in [301992,301995,301998,302001]:
        alias=next(r for r in tables['benefits_map'] if r['Id']==str(bid));assert alias['BenefitsExchangeId']==[301878,301881,301884]
    def effects(values):
        found=[];excluded=[]
        for v in values or []:
            bid=v['benefit_id'];value=v['benefit_value']
            if bid in scope:
                target,scene,stat=scope[bid];found.append({'scope':target,'scene':scene,'stat':stat,'value':value})
            elif not benefits.get(bid,'').startswith('prop_se1.5_'):excluded.append(benefits.get(bid,str(bid)))
        return found,sorted(set(excluded))
    indexed={name:{r['InternalId']:r for r in tables[name]} for name in ['survivor_skill_main','survivor_skill_type','survivor_slg_skill_new','survivor_slg_effect_new']}
    def skill_evidence(row):
        main=indexed['survivor_skill_main'].get(row['GearSkillSlg'],{})
        kind=indexed['survivor_skill_type'].get(main.get('SkillType'),{})
        lite=indexed['survivor_slg_skill_new'].get(kind.get('SurvivorSlgSkillNew_ID'),{})
        links=[indexed['survivor_slg_effect_new'].get(key,{}) for key in lite.get('SkillEffectNew_ID',[])]
        markers={benefits.get(e['benefit_id'],'') for e in row['BenefitSlg'] if benefits.get(e['benefit_id'],'').startswith('benefits_')}
        buffs=[{k:b[k] for k in ['Id','TypeLite','AdditonTypeLite','ParamLite']} for b in tables['effect_buff'] if any(b['Id'].startswith(marker+'_buff_') for marker in markers)]
        return {'status':'unverified_runtime','field_skill':lite.get('Id'),'effect_types':sorted({e['Type'] for e in links if 'Type' in e}), 'raid_skill':kind.get('RaidNewSkill'),'candidate_buffs':buffs,'scope_note':'Field Lite links and similarly named buff rows; marker-to-buff application, recipients, operand formula and stacking are not verified. Excluded from scoring.'}
    signature={}
    for gear in tables['survivor_exclusive_gear']:
        hero=byid.get(gear['Survivor'])
        if not hero:continue
        levels=[]
        for r in sorted([r for r in tables['survivor_exclusive_gear_main'] if r['GearId']==gear['InternalId']],key=lambda r:r['Level']):
            fx,excluded=effects(r['BenefitSlg'])
            description=lang.get(r['GearSkillDes'],r['GearSkillDes'])
            for index,value in enumerate(r['GearSkillParam']):description=description.replace('{'+str(index)+'}',value)
            import re
            description=re.sub(r'<[^>]+>','',description)
            levels.append({'level':r['Level'],'effects':fx,'unmodeled':excluded,'linked_skill':bool(r['GearSkillSlg']),'description':description,'skill_evidence':skill_evidence(r)})
        signature[hero['asset_slug']]={'name':lang.get(gear['GearName'],hero['name']+' Signature Gear'),'levels':levels,'icon_asset':gear['Icon'],'skill_icon_asset':gear['GearSkillIcon'],'skill_name':lang.get(gear['GearSkillName'],gear['GearSkillName'])}
    research={};groups={r['InternalId']:r for r in tables['research_group']};trees={r['InternalId']:r for r in tables['research_tree']}
    for r in tables['research_main']:
        fx,excluded=effects(r['Benefits'])
        if not fx:continue
        g=groups[r['Group']];key=g['Id']
        entry=research.setdefault(key,{'name':lang.get(g['Name'],key)+' · '+lang.get(g['LevelRoman'],g['LevelRoman'].replace('roman_numeral_','')),'levels':[],'icon_asset':g['Image'],'tree':str(g['Tree']),'tier':g['Tier'],'row':g['Row']})
        entry['levels'].append({'level':r['Level'],'effects':fx,'unmodeled':excluded,'linked_skill':False})
    for entry in research.values():
        entry['levels'].sort(key=lambda r:r['level']);assert len({r['level'] for r in entry['levels']})==len(entry['levels'])
    # Native TitanDatabaseCell.GetAllBenefit merges the selected FRONT level and star Benefit rows once each.
    # Never add the Back row too or sum every preceding level. skill_benefits / talents / full_skills are separate.
    base_rows={r['InternalId']:r for r in tables['behemoth_base_data']}
    behemoths={}
    for beast in tables['behemoth_base']:
        entries={}
        for table_name,key,field in [('behemoth_level','levels','BehemothLevel'),('behemoth_star_level','stars','BehemothStarLevelTotal')]:
            values=[]
            for row in tables[table_name]:
                if row['BehemothId']!=beast['InternalId']:continue
                base=base_rows.get(row['BehemothBaseFront'])
                if not base:continue
                fx,excluded=effects(base['Benefit'])
                values.append({'level':row[field],'effects':fx,'unmodeled':excluded,'linked_skill':False})
            # Legacy placeholder variants can have no traced modern hero-stat contribution.
            entries[key]=sorted(values,key=lambda r:r['level'])
        if not any(row['effects'] for row in entries['levels']+entries['stars']):continue
        assert all(len({row['level'] for row in entries[k]})==len(entries[k]) for k in ['levels','stars'])
        behemoths[beast['Id']]={'name':lang.get(beast['ArticleName'],beast['Id'])+' ('+beast['Id']+')','icon_asset':beast['PhotoIcon'],'availability_note':('Gated client entry; live availability is unconfirmed.' if beast['ServerOpenDays']>=99999 else 'Confirm availability and applicability in-game.'),**entries}
    return {'version':4,'audited_date':'2026-11-04','signature':signature,'research':research,'behemoths':behemoths,'research_trees':{str(i):{'name':lang.get(t['Name'],t['Name']),'legacy':bool(t['IsOld']),'order':t['Position']} for i,t in trees.items() if any(g['tree']==str(i) for g in research.values())},

      'heroes':{r['asset_slug']:{'role':r['role'],'faction':r['faction']} for r in heroes},
      'source_hashes':{n:hashlib.sha256((source/(n+'.cfg')).read_bytes()).hexdigest() for n in names},
      'limits':'Stat-only context. Signature linked skills, troop multipliers, Behemoth battle skills and own combat stats are excluded. Behemoth source is either a manual combined hero-bonus snapshot or configured current level/star front-row benefits. Sources never stack with one another; skills/talents/full-skill bonuses remain separate. Own Behemoth ATK/DEF/HP is not hero stats. Blank sources are excluded, not proven absent.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--language',type=Path,required=True);args=parser.parse_args()
    data=export(args.source,args.language);out=ROOT/'outputs/hero-report/Hero-Army-Context.json';out.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8');print(out,len(data['signature']),len(data['research']))
