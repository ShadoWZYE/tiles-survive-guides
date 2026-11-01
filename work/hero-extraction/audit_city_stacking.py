"""Selected static city aggregation proof and executable arithmetic reference.

Never loads the game. Hash-gated native bodies stay private. The result proves
conditional local arithmetic, not live eligibility or effective stacking.
"""
import hashlib,json,struct
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BODIES=[
 ('StrongholdPage.GetCurrentBenefit',0x2858210,0x28586A0,'82df13afb2b21cc2006ee70a6d77d86143a231845f6604b485804a9b6f6ac7e7'),
 ('Benefit.MergeBenefit',0x1D93570,0x1D93760,'07d87e2b513291f2ae622c4a892125177efbad5869cf94169ff4940056ff922e'),
 ('AnalysisCenterModule.GetMyAnalysisCenter',0x3805130,0x38053B0,'24e83966893d287249290ffa6bec4699e2e1c1bdc22c8bb930dc062c64bf10bc'),
 ('StrongholdCellTipUIMediator.IsHaveSameAnalysis',0x2856E70,0x2857060,'0bb779eb5511006d034486ec2a7f1f93a96756965d76ad29152c9eedfcfe6d25')]
ANCHORS={0x28584E3:'488b5750',0x28584EA:'e8c1ea6c02',0x28584F1:'0f85e9feffff',
         0x28584FE:'4c8b4648',0x2858509:'e8c2326e02',0x28585E4:'e887af53ff',
         0x1D93680:'3b7010',0x1D936C5:'f20f587018',0x1D936CE:'f20f117318'}


def aggregate_cities(cities,configs,flags):
    """Mirror owned-list -> server eligibility -> unique config -> add benefit IDs.

    cities contains already-owned (physical_key, configuration_id) pairs. A null
    server eligibility map contributes nothing; an explicit zero skips that site.
    """
    selected={}
    if flags is None:return {}
    for physical,config_id in cities:
        if physical in flags and flags[physical]==0:continue
        if config_id not in configs or config_id in selected:continue
        selected[config_id]=configs[config_id]['benefits']
    result={}
    for benefits in selected.values():
        for benefit in benefits:
            key=benefit['id'];result[key]=result.get(key,Decimal(0))+Decimal(str(benefit['value']))
    return {key:float(value) for key,value in result.items()}


def eligibility_boundary_proof():
    """Verify UI -> stored runtime input -> eligibility branch, without live data.

    This does not establish the actual eligibility values or server policy.
    """
    image=(ROOT/'tmp/native-293/verified/native-rva-image.bin').read_bytes()
    index=json.loads((ROOT/'tmp/native-293/verified/method-index.json').read_text(encoding='utf-8'))
    bodies=[
        ('AllianceExtDatabaseCell.AutoFill',0x1e0f560,0x1e10c00,'0f496d89294a5edac2a6334d5c14c09385a844eccda1bef5139199cba82d0bac'),
        ('AllianceExtDatabaseCell.get_StatsInfo',0x1e12170,0x1e12200,'78cb14ad2bddc852863886d642615700af1d3004b7b26248449ed8b0c9492a43'),
        ('StrongholdPage.BenefitCheck',0x2857ee0,0x2858210,'0daf3c4db639f32ffb947a068dbd5631859752aaba8fe52dd06a73351c99342e')]
    methods=[]
    for name,start,end,expected in bodies:
        assert any(r['type']+'.'+r['name']==name and r['rva']==start for r in index)
        assert hashlib.sha256(image[start:end]).hexdigest()==expected
        methods.append({'method':name,'rva':hex(start),'end_rva':hex(end),'sha256':expected})
    anchors={
        0x1e0fc95:'488b55f0488d8b900000004889939000000041b601',
        0x1e121a5:'488b8b280200004885c9743c4c8b0588e0dd05488b93900000004883c4205b',
        0x285815f:'e8ac000000',0x2858413:'e87810b4fe',0x2858426:'e8459d5bff',
        0x2858434:'488b70204885f60f8431020000488b7618',0x2858488:'85c00f8450ffffff'}
    for start,value in anchors.items():
        assert image[start:start+len(bytes.fromhex(value))]==bytes.fromhex(value)
    return {
        'analysis_failure_status':'CONFIRMED_UNVERIFIED_ELIGIBILITY_ASSUMPTION',
        'live_discrepancy_cause_status':'UNRESOLVED_UNAVAILABLE_RUNTIME_DATA',
        'missing_input':'AllianceExtDatabaseCell.stats_info -> AllianceStatsInfo.analysis_center for the alliance and time shown in the screenshot',
        'trace':[
            'StrongholdPage.BenefitCheck calls GetCurrentBenefit at RVA 0x285815f.',
            'AllianceExtDatabaseCell.AutoFill assigns incoming record data to stats_info (+0x90); get_StatsInfo reads that stored field.',
            'GetCurrentBenefit reads PlayerModule.AllianceExt -> StatsInfo -> analysis_center (+0x20).',
            'It looks up the physical city StringId; an explicit zero value skips that city at RVA 0x2858488. Missing keys are not the same as explicit zero values.',
            'Only surviving cities reach configuration-ID deduplication and Benefit.MergeBenefit addition.'],
        'why_prior_report_was_wrong':'Reference examples supplied flags={} (no explicit exclusions) and assumed both configured Lv.5 entries active. The prior report promoted this conditional result to a confirmed live +20% prediction without obtaining the actual runtime map.',
        'identifiability_limit':'Either Research Center excluded in the reference model yields the same five observed totals. The screenshot cannot distinguish those two cases, let alone prove a universal cap or highest-only policy.',
        'not_established':['Which city, if either, was marked zero','The server policy deciding eligibility','A universal same-stat cap','A merge-specific stacking change','A server bug or an independently measured training timer effect'],
        'data_needed':'A decoded alliance stats_info record including analysis_center and live per-city configuration IDs, matched in time to the Bonuses panel; exact active client/patch version if it differs from the inspected local build.',
        'practical_fallback':'A fresh relogged panel plus individual city tooltips can reduce stale-display/configuration uncertainty, but cannot reveal the missing eligibility policy.',
        'methods':methods,'instruction_anchors':{hex(k):v for k,v in anchors.items()}}


def patch_type_names(raw):
    """Read the standard InjectFix header/extern types, without executing bytecode."""
    if len(raw)<12 or struct.unpack_from('<Q',raw)[0]!=317431043901:raise ValueError('Unknown patch format')
    pos=8
    def string():
        nonlocal pos
        length=0;shift=0
        for _ in range(5):
            if pos>=len(raw):raise ValueError('Truncated patch string')
            b=raw[pos];pos+=1;length|=(b&127)<<shift;shift+=7
            if b<128:break
        else:raise ValueError('Invalid patch string length')
        if pos+length>len(raw):raise ValueError('Patch string exceeds file')
        value=raw[pos:pos+length].decode('utf-8');pos+=length;return value
    bridge=string()
    if not bridge.startswith('IFix.'):raise ValueError('Unexpected patch bridge')
    count=struct.unpack_from('<i',raw,pos)[0];pos+=4
    if not 0<=count<=20000:raise ValueError('Unbounded patch type count')
    return {string().split(',')[0] for _ in range(count)}


def city_stacking_proof(base_map_cities,positions):
    image=(ROOT/'tmp/native-293/verified/native-rva-image.bin').read_bytes()
    methods=json.loads((ROOT/'tmp/native-293/verified/method-index.json').read_text(encoding='utf-8'))
    rows=[]
    for name,start,end,expected in BODIES:
        if not any(x['type']+'.'+x['name']==name and x['rva']==start for x in methods):raise ValueError('Native method identity mismatch')
        digest=hashlib.sha256(image[start:end]).hexdigest()
        if digest!=expected:raise ValueError('City aggregation native body changed: '+name)
        rows.append({'method':name,'rva':hex(start),'end_rva':hex(end),'sha256':digest})
    for start,value in ANCHORS.items():
        if image[start:start+len(bytes.fromhex(value))]!=bytes.fromhex(value):raise ValueError('Instruction proof anchor mismatch')
    patches=[]
    for p in sorted(Path('C:/Program Files (x86)/FunPlus/Tiles Survive/GameData/assets/patch').glob('*')):
        if not p.is_file():continue
        raw=p.read_bytes();types=patch_type_names(raw)
        relevant=bool(types&{'StrongholdPage','AnalysisCenterModule','StrongholdCellTipUIMediator'}) or b'MergeBenefit' in raw
        patches.append({'file':p.name,'sha256':hashlib.sha256(raw).hexdigest(),'relevant_target_reference_found':relevant})
    if any(p['relevant_target_reference_found'] for p in patches):raise ValueError('Inspect matching patch before claiming current base calculator')
    by_name={r['id']:r['configuration_id'] for r in base_map_cities}
    configs={r['configuration_id']:r for r in base_map_cities}
    examples=[]
    for label,names,expected in [
      ('Two physical copies of the same +5% Village entry',['analysis_center_1_1']*2,{300300:.05}),
      ('Distinct +5% Village and +20% Metropolis entries',['analysis_center_1_1','analysis_center_4_1'],{300300:.25}),
      ('Distinct +5% training Factory and +10% Research Center entries',['analysis_center_2_3','analysis_center_5_1'],{300321:.15}),
      ('Distinct +2% ATK Town and +5% ATK Military Base entries',['analysis_center_3_1','analysis_center_6_1'],{301835:.07}),
      ('One Lv.5 city from each configuration group',['analysis_center_5_1','analysis_center_5_2'],{300321:.20}),
      ('All six base-map Lv.5 cities still count only two configuration groups',['analysis_center_5_1']*3+['analysis_center_5_2']*3,{300321:.20}),
      ('Different entries may add even with the same level and stat, if both are eligible',['analysis_center_1_1','analysis_center_1_3'],{300300:.10}),
      ('Different benefit IDs remain separate',['analysis_center_1_1','analysis_center_1_2'],{300300:.05,300747:.05})]:
        result=aggregate_cities([(str(i),by_name[n]) for i,n in enumerate(names)],configs,{})
        if result!=expected:raise ValueError('Reference translation failed a hand-calculated example')
        examples.append({'case':label,'configuration_entries':names,'benefit_totals':{str(k):v for k,v in result.items()}})
    level5=[]
    for config in ['analysis_center_5_1','analysis_center_5_2']:
        sites=[p['Coordinate'] for p in positions if p['SeasonType']=='S1' and p['AnalysisCenter']==by_name[config]]
        if len(sites)!=3:raise ValueError('Recheck base-map Lv.5 position groups')
        level5.append({'configuration_entry':config,'training_speed_contribution':.10,'base_map_S1_coordinates':sites})
    all_totals=aggregate_cities([(str(i),r['configuration_id']) for i,r in enumerate(base_map_cities)],configs,{})
    return {'status':'conditional_static_path_not_live_stacking_confirmation',
        'rule':'Count each eligible i_analysis_center configuration ID once; sum the retained Benefit lists by benefit_id. No highest-only selection across distinct configuration IDs.',
        'duplicate_key':'AnalysisCenterDatabaseCell.i_analysis_center, not physical coordinates, city name, level or benefit_id',
        'eligibility':'Owned/occupied alliance list. StrongholdPage.GetCurrentBenefit consults AllianceStatsInfo.analysis_center for each physical city; explicit zero entries are skipped. Server controls eligibility.',
        'methods':rows,'instruction_anchors':{hex(k):v for k,v in ANCHORS.items()},
        'cached_patch_scan':patches,'patch_scan_scope':'All cached patch extern-type tables parsed; no relevant city-calculator/merge replacement references found. This is not proof about unavailable future or live server code.',
        'reference_examples':examples,'level5_groups':level5,'conditional_all_eligible_sum_not_an_effective_maximum':{str(k):v for k,v in all_totals.items()},
        'scope':'Only verifies conditional arithmetic in the local method. Live observation on 29 October contradicts the all-eligible Lv.5 +20% prediction. This does not confirm effective stacking. Coordinates are for the S1/base map, not seasonal replacement maps. It does not independently execute the server combat/economy implementation or establish every server-side eligibility condition.'}
