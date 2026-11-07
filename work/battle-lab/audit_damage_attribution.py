"""Hash-gated audit of static Raid report attribution, not the full battle engine."""
import argparse,bisect,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'work/hero-extraction'))
from audit_native_combat import metadata_index,SELECTED,DECODED_METADATA_SHA256
import audit_native_combat as native
from refresh_hero_data import verified_tables
from decode_cfg import decode_table
IMAGE_SHA='5afef9adf2a4dc85b40adc702149a45bf10728ef2c9de1895f3b648a9128b14d'
INDEX_SHA='ee94b9e060a9d0db87e2787b52a339dcf7555e3f65933d21a5ad9e583be13af4'
METHODS={'RaidFightStatisticsMgr':['OnEntityDamage','OnShieldAbsorbDamage','GetStatisticsData','InitStatisticsData','GetBattleReplayPetStatisticsData'],'RaidFightStatisticsData':['AddDamage','AddBeDamage','AddHeal','AddBeHeal'],'SurvivorEquipmentModule':['GetEquipPower']}
FIELDS={'RaidEntityHpChange':{'guid':16,'beDamageGuid':24,'combineData':32,'hpChange':60},'RaidEntityShieldAbsorbEvent':{'Guid':16,'BeAbsorbGuid':24,'AbsorbDmg':32},'PveNewEffectConfigCell':{'IsNotStatistics':232},'PveNewMonsterConfigCell':{'IsNotStatistics':304},'SummonDataSource':{'MonsterConfigCell':56},'SurvivorEquipmentLevelNppConfigCell':{'Power':72,'BenefitLvSlgPower':96},'SurvivorEquipmentRankNppConfigCell':{'BenefitSlg':48,'ExtendPower':88,'BenefitLevelStage':96},'SurvivorEquipmentBreakStageConfigCell':{'StageBenefitSlg':48}}
def fingerprints(image,index_bytes,metadata):
    if hashlib.sha256(image).hexdigest()!=IMAGE_SHA or hashlib.sha256(index_bytes).hexdigest()!=INDEX_SHA or hashlib.sha256(metadata).hexdigest()!=DECODED_METADATA_SHA256:
        raise ValueError('Unverified native attribution artifacts')
    original=native.SELECTED
    try:
        native.SELECTED={**original,**{name:[] for name in FIELDS}}
        types,_=metadata_index(metadata,image)
    finally:native.SELECTED=original
    for name,expected in FIELDS.items():
        fields=dict(types[name]['fields'])
        if any(fields.get(k)!=v for k,v in expected.items()):raise ValueError('Attribution field mapping changed')
    methods=json.loads(index_bytes);addresses=sorted({m['rva'] for m in methods});result=[]
    for kind,names in METHODS.items():
        for name in names:
            m=next(m for m in methods if m['type']==kind and m['name']==name);end=addresses[bisect.bisect_right(addresses,m['rva'])]
            result.append({**m,'byte_count':end-m['rva'],'code_sha256':hashlib.sha256(image[m['rva']:end]).hexdigest()})
    return result

def export(image,index,metadata,game_assets,private):
    methods=fingerprints(image,index,metadata)
    manifest_path=game_assets/'BinaryConfig/BinVersionList_Realtime.json';manifest=manifest_path.read_bytes();pack=(game_assets/'BinaryConfigPack.ss').read_bytes()
    tables={};hashes={}
    for name,(number,raw) in verified_tables(pack,json.loads(manifest),{'pve_new_effect','pve_new_monster','survivor_equipment_level_npp'},manifest_path.parent).items():
        path=private/(name+'.cfg');path.write_bytes(raw);tables[name]={r['Id']:r for r in decode_table(path)['rows']};hashes[name]=hashlib.sha256(raw).hexdigest()
    combat=json.loads((ROOT/'outputs/hero-report/Hero-Combat-Audit.json').read_text(encoding='utf-8'));summons=[]
    for slug,hero in combat['heroes'].items():
        for skill in hero['skills']:
            for actor in skill.get('summoned_actors',[]):
                template=tables['pve_new_monster'].get(actor['template_id'])
                if template is None:raise ValueError('Missing audited summon template')
                flag=template['IsNotStatistics'];effects=[]
                for node in actor['skills']:
                    for effect in node['effects']:
                        row=tables['pve_new_effect'][effect['id']]
                        effects.append({'id':effect['id'],'is_not_statistics':row['IsNotStatistics'],'type':row['Type']})
                summons.append({'hero':slug,'skill':skill['id'],'template':actor['template_id'],'is_not_statistics':flag,'host_credit_allowed_by_static_lookup':flag!=1,'effects':effects,'execution_verified':False})
    observation=json.loads((ROOT/'outputs/hero-report/Replay-Observation-2026-11-07.json').read_text(encoding='utf-8'))
    gear_rows=[]
    for hero in observation['heroes']:
        rows=[tables['survivor_equipment_level_npp'][g['id']+'_level_'+str(g['level'])] for g in hero['gear']]
        gear_rows.append({'hero':hero['planner_slug'],'base_power':sum(r['Power'] for r in rows),'level_bonus_power':sum(r['BenefitLvSlgPower'] for r in rows)})
    return {'schema':1,'client_build':'2.6.400.304','private_image_sha256':IMAGE_SHA,'private_index_sha256':INDEX_SHA,'decoded_metadata_sha256':DECODED_METADATA_SHA256,'methods':methods,'selected_field_offsets':FIELDS,'config_pack_sha256':hashlib.sha256(pack).hexdigest(),'manifest_sha256':hashlib.sha256(manifest).hexdigest(),'table_sha256':hashes,
        'static_rules':{'signed_hp_change':'Negative: absolute magnitude to Damage/BeDamage. Nonnegative: magnitude to Heal/BeHeal.','effect_filter':'OnEntityDamage skips effect configuration IsNotStatistics == 1 before both counters.','shield':'OnShieldAbsorbDamage adds AbsorbDmg to source Damage and target BeDamage independently of HP-change callback.','ownership':'Direct registered GUID first. Missing GUID: camp 0 soldier credits FollowHeroGuid; camp 0 summon credits HostGUID only with non-null template and IsNotStatistics != 1. Single registered-host lookup, not recursive.','registration':'InitStatisticsData registers self heroes, titans and pets. Other camp GUIDs absent from registry do not receive fallback credit.','pet_import':'Replay pet export copies pet Damage and Heal plus BeDamage into separate pet row.'},
        'observed_gear_reconciliation':{'heroes':gear_rows,'reconstructed':sum(r['base_power']+r['level_bonus_power'] for r in gear_rows),'observed':observation['friendly']['gear_power']},'gear_power_static_path':{'method':'SurvivorEquipmentModule.GetEquipPower','base_rank_no_breakthrough_no_enchant':'level.Power + level.BenefitLvSlgPower','other_paths':'Rank multipliers, ExtendPower, breakthrough multiplier and external additive are separate; no missing upgrades inferred.'},'summon_templates':summons,'live_patch_override_checked':False,'event_values_available':False,'server_report_collection_equivalence_verified':False,'scope':'Manually inspected static local Raid statistics path. Not proof of server report aggregation, actual summon execution, active hotfix behavior or per-source numerical totals.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);base=ROOT/'tmp/scoring-close-2026-11-05/native'
    p.add_argument('--image',type=Path,default=base/'verified/native-rva-image.bin');p.add_argument('--index',type=Path,default=base/'verified/method-index.json');p.add_argument('--metadata',type=Path,default=base/'metadata.dat');p.add_argument('--game-assets',type=Path,default=Path('C:/Program Files (x86)/FunPlus/Tiles Survive/GameData/GameAssets'));p.add_argument('--private',type=Path,default=ROOT/'tmp/damage-attribution-2026-11-07');p.add_argument('--output',type=Path,default=ROOT/'outputs/hero-report/Damage-Attribution-Audit.json');a=p.parse_args();a.private.mkdir(parents=True,exist_ok=True)
    result=export(a.image.read_bytes(),a.index.read_bytes(),a.metadata.read_bytes(),a.game_assets,a.private);a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(f"Fingerprinted {len(result['methods'])} selected methods and {len(result['summon_templates'])} summon references; no live damage fractions inferred.")
if __name__=='__main__':main()
