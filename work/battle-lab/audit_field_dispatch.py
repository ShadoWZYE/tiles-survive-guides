"""Audit inspected source coverage and the report-input boundary, not server damage."""
import argparse,bisect,hashlib,json,struct,sys
from pathlib import Path
from audit_damage_attribution import fingerprints,IMAGE_SHA,INDEX_SHA
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'work/hero-extraction'))
from native_literal_reader import NativeLiteralReader,COUNT
from extract_hero_images import text,bundle_hashes

LITERALS={0xbebe1c:'survivor_damage_and_withstand',0xbebe4b:'titan_damage_and_withstand',0xbebe82:'pet_damage_and_withstand',
          0x38ed784:'rounds_info',0x38edad2:'hp',0x38edb36:'pos',0x38edb9a:'start_hp',0x38edbfd:'heal_hp'}
METHODS={'GotoUtils':['GenBattleReportInputData'],'BattleReportReplayModule':['OnGetSubMailData','ParMailBattleReportData','SetBattleReportData','OnRemove'],
         'RaidFightStatisticsMgr':['GetBattleReplayStatisticsData'],'MarchFightingSkillData':['.ctor']}
FIELDS={'UnitStatus':{'hp':16,'pos':24,'start_hp':32,'heal_hp':40},
        'BattleReportStatisticsData':{'i_survivor':16,'cure':24,'damage':32,'withstand':40},
        'InputBattleReportData':{'ReportData':128,'MyStatisticsData':160,'MyTitanStatisticsData':168,'MyPetStatisticsData':176},
        'BattleReportReplayModule':{'_allReportDict':24}}

def source_coverage(index,lua_directory,provenance):
    data=index.read_bytes();count=struct.unpack_from('<I',data)[0];position=4;expected={}
    for _ in range(count):
        version,_=struct.unpack_from('<II',data,position);position+=8
        if version!=1:raise ValueError('Unknown asset-index record')
        name,position=text(data,position);bundle=struct.unpack_from('<I',data,position)[0];position+=4
        if name.endswith('.lua'):expected[name.casefold()]=bundle
    records_end=position
    aliases=struct.unpack_from('<I',data,position)[0];position+=4
    for _ in range(aliases):_,position=text(data,position)
    for _ in range(2):
        size=struct.unpack_from('<I',data,position)[0];position+=4
        if size!=aliases:raise ValueError('Asset-index secondary array size changed')
        position+=size*4
    if position+4!=len(data) or struct.unpack_from('<I',data,position)[0]!=records_end:
        raise ValueError('Asset-index directory footer changed')
    files=list(lua_directory.glob('*.lua'));actual={p.name.casefold():p for p in files}
    if set(actual)!=set(expected):raise ValueError('Lua corpus does not cover the selected asset index')
    fingerprints_by_name={};hits={};numeric=[]
    symbols=['SurvivorSlgEffectNew','SurvivorSlgSkillNew','EffectAttrRate','TargetTypeLite','DamageParam','CalSkillDamage']
    import re
    for key,path in actual.items():
        raw=path.read_bytes();body=raw.decode('utf-8')
        if raw.startswith((b'\x1bLua',b'\x1bLJ')):raise ValueError('Opaque Lua bytecode cannot count as searched source')
        digest=hashlib.sha256(raw).hexdigest()
        if provenance['files'].get(path.name)!=digest:raise ValueError('Lua source changed after extraction')
        fingerprints_by_name[key]=digest
        matched=[symbol for symbol in symbols if symbol.casefold() in body.casefold()]
        if matched:hits[path.name]=matched
        if re.search(r'(?<![0-9])11100(?![0-9])',body):numeric.append(path.name)
    corpus=json.dumps(sorted(fingerprints_by_name.items()),separators=(',',':')).encode()
    return {'asset_index_sha256':hashlib.sha256(data).hexdigest(),'indexed_lua_count':len(expected),'searched_utf8_sources':len(actual),
            'missing_sources':0,'corpus_sha256':hashlib.sha256(corpus).hexdigest(),'bundle_count':len(set(expected.values())),
            'bundle_ids':sorted(set(expected.values())),
            'searched_symbols':symbols,'symbol_hits':hits,'numeric_11100_files':sorted(numeric),
            'scope':'Text-source and selected-symbol coverage only; dynamically constructed names and indirect calls are not excluded.'}

def direct_getter_references(image,index,capstone):
    rows=json.loads(index);by={row['rva']:row for row in rows};addresses=sorted(by)
    targets={row['rva']:row for row in rows if row['type']=='ConfigRefer' and row['name'] in ['get_SurvivorSlgEffectNewConfig','get_SurvivorSlgSkillNewConfig']}
    decoder=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);result=[]
    for opcode in [b'\xe8',b'\xe9']:
        at=-1
        while True:
            at=image.find(opcode,at+1)
            if at<0 or at+5>len(image):break
            destination=at+5+struct.unpack_from('<i',image,at+1)[0]
            if destination not in targets:continue
            ordinal=bisect.bisect_right(addresses,at)-1
            if ordinal<0 or ordinal+1>=len(addresses):continue
            start,end=addresses[ordinal:ordinal+2]
            ins=next((i for i in decoder.disasm(image[start:end],start) if i.address==at),None)
            if ins is None or ins.mnemonic not in ['call','jmp']:continue
            result.append({'callsite_rva':hex(at),'caller':by[start],'target':targets[destination]})
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--capstone-dir',type=Path,required=True)
    args=parser.parse_args();sys.path.insert(0,str(args.capstone_dir));import capstone
    base=ROOT/'tmp/scoring-close-2026-11-05/native';image=(base/'verified/native-rva-image.bin').read_bytes();index=(base/'verified/method-index.json').read_bytes();metadata=(base/'metadata.dat').read_bytes()
    methods=fingerprints(image,index,metadata,METHODS,FIELDS);reader=NativeLiteralReader(image,metadata)
    literals=[reader.at_instruction(rva) for rva in LITERALS]
    if [r['literal'] for r in literals]!=list(LITERALS.values()):raise ValueError('Selected report-key mapping changed')
    private=ROOT/'tmp/ray-field-2026-11-07';game=Path('C:/Program Files (x86)/FunPlus/Tiles Survive/GameData/GameAssets/AssetBundle2')
    provenance=json.loads((private/'lua-corpus-provenance.json').read_text(encoding='utf-8'))
    if provenance['missing_bundles']:raise ValueError('Incomplete source extraction')
    coverage=source_coverage(game/'G/Windows/bundle_assets_G_2.6.400.312.json',private/'lua-all',provenance)
    digests=bundle_hashes(game/'bundle_list_G_2.6.400.312.json',set(coverage.pop('bundle_ids')))
    if set(digests.values())!={row['digest'] for row in provenance['bundles']}:raise ValueError('Extracted bundles differ from selected source index')
    coverage['bundle_list_sha256']=hashlib.sha256((game/'bundle_list_G_2.6.400.312.json').read_bytes()).hexdigest()
    coverage['extracted_bundle_sha256']=provenance['bundles']
    result={'schema':1,'native_build':'2.6.400.304','lua_asset_index_build':'2.6.400.312','private_image_sha256':IMAGE_SHA,'private_index_sha256':INDEX_SHA,
        'literal_descriptors_validated':COUNT,'selected_literal_references':literals,'native_methods':methods,'field_offsets':FIELDS,
        'direct_config_getter_references':direct_getter_references(image,index,capstone),'lua_coverage':coverage,
        'report_boundary':{'round_states':['hp','pos','start_hp','heal_hp'],'owner_totals':['i_survivor','cure','damage','withstand'],
            'source':'Supplied report/response records; the replay builder assigns owner totals and round states to separate input fields.',
            'self_hero_conversion':[{'rva':'0x2a16b0d','operation':'Adds supplied damage at offset 32.'},{'rva':'0x2a16b1d','operation':'Adds supplied cure at offset 24.'},{'rva':'0x2a16b31','operation':'Adds supplied withstand at offset 40.'}],
            'numeric_report_input_supplied_to_this_audit':False},
        'field_damage_handler_identified':False,'server_only_proven':False,'weights_changed':False,'independent_damage_accuracy':None,
        'conclusions':['No Type-11100 damage handler was identified in the inspected source paths. This is not proof of absence in all executable or server code.',
            'Direct getter references cover configuration/name lookup, generated wrappers and registration; reflection and indirect calls remain outside that scan.',
            'Original unrounded report states/totals would improve numerical validation, but round HP deltas alone do not identify outgoing damage sources.',
            'Raid animation agreement with a report is not independent validation of the original field damage arithmetic.']}
    output=ROOT/'outputs/hero-report/Field-Dispatch-Source-Audit.json';output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f"Validated {COUNT} literals, {coverage['searched_utf8_sources']} Lua sources and {len(result['direct_config_getter_references'])} direct getter references; original field formula not identified.")

if __name__=='__main__':main()
