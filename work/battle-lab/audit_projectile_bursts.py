"""Reproduce bounded projectile corrections against the previous published model."""
import hashlib,json,subprocess
from pathlib import Path
from audit_damage_attribution import fingerprints,IMAGE_SHA,INDEX_SHA

ROOT=Path(__file__).resolve().parents[2]
FOLDER=ROOT/'outputs/hero-report'
BASELINE='58d8382f7df3340a9b30a70630914fd2b70c88b7'

def main():
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    native=ROOT/'tmp/scoring-close-2026-11-05/native'
    methods=fingerprints((native/'verified/native-rva-image.bin').read_bytes(),(native/'verified/method-index.json').read_bytes(),(native/'metadata.dat').read_bytes(),
        {'RaidGameProjectileConfig':['.ctor'],'RaidGameActionProjectile':['ProcessOneTarget'],'RaidGameProjectileLine':['OnHit'],'ConditionSkillFinishChecker':['OnBeginCheck','OnTargetEntitySkillFinish']},
        {'RaidGameProjectileConfig':{'timeScale':32,'HitTargetNumLimit':36}})
    before=json.loads(subprocess.check_output(['git','show',BASELINE+':outputs/hero-report/Hero-Estimate-Model.json'],cwd=ROOT))
    after=read(FOLDER/'Hero-Estimate-Model.json');audit=read(FOLDER/'Hero-Combat-Audit.json')
    assert before['scales']==after['scales'] and before['score_scale']==after['score_scale']==1000
    expected={'tony':(0,6,.1,.6),'dave':(1,3,4.5,13.5),'sarge':(0,3,.2,.6),'eva':(1,8,.75,6.)}
    corrections=[];changed=[];zones=[]
    for slug,hero in after['heroes'].items():
        old=before['heroes'][slug]
        if [s['levels'] for s in old['skills']]!=[s['levels'] for s in hero['skills']]:changed.append(slug)
        for skill in hero['skills']:
            previous=next(s for s in old['skills'] if s['id']==skill['id'])
            if skill['damage_selection_basis']=='projectile_zone_dispatch_potential' and previous['damage_selection_basis']!=skill['damage_selection_basis']:
                assert skill['levels']==previous['levels'];zones.append({'hero':slug,'skill':skill['id'],'coefficient_changed':False})
        if slug not in expected:continue
        slot,count,old_coefficient,new_coefficient=expected[slug]
        skill=next(s for s in hero['skills'] if s['slot']==slot);previous=next(s for s in old['skills'] if s['id']==skill['id'])
        evidence=next(s for s in audit['heroes'][slug]['skills'] if s['id']==skill['id'])
        launches=[p for p in evidence['skill_nodes'][0]['projectile_launches'] if p['reference'] in skill['direct_damage_effect_ids']]
        assert len(launches)==sum(skill['direct_hit_counts'].values())==count
        assert all(p['impact_offset_seconds'] is None and p['hit_target_limit']==1 for p in launches)
        assert abs(previous['levels'][1]['cast_budget']['direct_coefficient']-old_coefficient)<1e-9
        assert abs(skill['levels'][1]['cast_budget']['direct_coefficient']-new_coefficient)<1e-9
        assert all(not row.get('cast_budget',{}).get('direct_events') for row in skill['levels'])
        corrections.append({'hero':slug,'skill':skill['id'],'launches':launches,'level_1_before':old_coefficient,'level_1_after':new_coefficient,'basis':skill['damage_selection_basis']})
    assert set(changed)==set(expected),changed
    result={'schema':1,'client_build':'2.6.400.304','baseline_commit':BASELINE,'model_version':after['version'],
        'private_image_sha256':IMAGE_SHA,'private_index_sha256':INDEX_SHA,'native_methods':methods,
        'native_findings':[{'method':'RaidGameProjectileConfig..ctor','instruction_rva':'0x29c194f','finding':'Default HitTargetNumLimit is 1.'},
            {'method':'RaidGameActionProjectile.ProcessOneTarget','instruction_rva':'0x29b8eac','finding':'Creates a projectile for the action/target. Distinct actions are not deduplicated by launch timestamp.'},
            {'method':'ConditionSkillFinishChecker.OnBeginCheck','instruction_rva':'0x28e5c36','finding':'Registers the bound entity skill-over event. This is not evidence that Ray triggers on every allied or enemy cast; full entity binding and live patch behavior remain unverified.'}],
        'corrections':corrections,'resolved_zone_paths':zones,'numeric_skill_curve_changes':sorted(changed),
        'scope':'One eligible-target opportunity per literal bounded launch; not guaranteed hits, multi-target damage or a recovered server simulation.',
        'limits':['Traveling launch time is not impact time; retain completion fallback.','Reject unbounded loops, unknown timing, conditions, scaling and unsupported hit limits.','These four heroes are absent from the fully specified recorded friendly squad: no improvement to that replay error is claimed.','Static client Raid behavior does not establish server field/Lite equivalence or active hotfix behavior.'],
        'source_sha256':{name:hashlib.sha256((FOLDER/name).read_bytes()).hexdigest() for name in ['Hero-Combat-Audit.json','Hero-Estimate-Model.json']}}
    (FOLDER/'Projectile-Burst-Audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Verified four numerical corrections, two additional zone paths, and unchanged reference anchors.')

if __name__=='__main__':main()
