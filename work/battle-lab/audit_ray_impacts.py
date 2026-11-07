"""Fingerprint selected static summon paths and compare graph accounting against the prior model."""
import json,hashlib,subprocess
from pathlib import Path
from audit_damage_attribution import fingerprints,IMAGE_SHA,INDEX_SHA
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'work/hero-extraction'))
from build_estimate_model import projectile_zone_dispatches

def main():
    folder=ROOT/'outputs/hero-report';native=ROOT/'tmp/scoring-close-2026-11-05/native';read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    methods=fingerprints((native/'verified/native-rva-image.bin').read_bytes(),(native/'verified/method-index.json').read_bytes(),(native/'metadata.dat').read_bytes(),{'RaidSESummonObject':['GetSkillParamLevelUpOwner','CreateSkillComponent'],'SkillComponent':['AutoUseNoClipSkill'],'RaidEffectSystem':['ProcessEffectSummon']},{'RaidSESummonObject':{'_hostGUID':240,'_hostEntity':264}})
    audit=read(folder/'Hero-Combat-Audit.json');model=read(folder/'Hero-Estimate-Model.json');prior=json.loads(subprocess.check_output(['git','show','350272f:outputs/hero-report/Retrospective-Damage-Reconstruction.json'],cwd=ROOT));current=read(folder/'Retrospective-Damage-Reconstruction.json')
    for name in ['Replay-Observation-2026-11-07.json','Replay-Reconstruction-Inputs-2026-11-07.json','Hero-Army-Context.json']:assert current['source_hashes'][name]==prior['source_hashes'][name],name
    old_upgrades=json.loads(subprocess.check_output(['git','show','350272f:outputs/hero-report/TilesSurvive-Upgrade-Data.json'],cwd=ROOT))
    new_upgrades=read(folder/'TilesSurvive-Upgrade-Data.json')
    for gear in new_upgrades['gear'].values():gear.pop('icon_asset',None)
    assert new_upgrades==old_upgrades,'Upgrade numerical data changed beyond gear icon metadata'
    old_model=json.loads(subprocess.check_output(['git','show','350272f:outputs/hero-report/Hero-Estimate-Model.json'],cwd=ROOT))
    assert model['scales']==old_model['scales'],'Reference anchors changed'
    for slug in ['rosie','freja','becca','maddie']:
        before=old_model['heroes'][slug];after=model['heroes'][slug]
        for skill in after['skills']:
            skill.pop('projectile_zone_dispatches',None)
            previous=next(s for s in before['skills'] if s['id']==skill['id'])
            if slug=='maddie' and skill['damage_selection_basis']=='projectile_zone_dispatch_potential':skill['damage_selection_basis']=previous['damage_selection_basis']
        assert after==before,slug+' non-Ray curve changed'
    model=read(folder/'Hero-Estimate-Model.json')
    paths=[]
    for skill in audit['heroes']['ray']['skills']:
        dispatches=projectile_zone_dispatches(skill)
        if not dispatches:continue
        curve=next(s for s in model['heroes']['ray']['skills'] if s['id']==skill['id']);paths.append({'skill':skill['id'],'dispatches':dispatches,'level_1_per_target_potential':curve['levels'][1]['cast_budget']['direct_coefficient'],'projectile_timing_used_as_caster_offset':False})
    summary=lambda r:{m['id']:{'fitted_wape':m['in_sample']['wape'],'internal_held_owner_wape':m['leave_one_owner_out']['wape'],'ray_relative_error':next(x['relative_error'] for x in m['in_sample']['rows'] if x['hero']=='ray')} for m in r['models']}
    result={'schema':1,'client_build':'2.6.400.304','private_image_sha256':IMAGE_SHA,'private_index_sha256':INDEX_SHA,'native_methods':methods,'paths':paths,'static_trace':[{'method':'RaidSESummonObject.GetSkillParamLevelUpOwner','finding':'Uses _hostGUID to resolve and cache _hostEntity, then returns that host.','instruction_rvas':['0x298e9ad','0x298e9b7','0x298e9d2']},{'method':'RaidSESummonObject.CreateSkillComponent','finding':'Constructs a SkillComponent for the summon; effect execution still depends on target/skill gates.','instruction_rvas':['0x298e8e2']},{'method':'SkillComponent.AutoUseNoClipSkill','finding':'Includes configured no-clip eligibility, filtered target selection and UseSkill dispatch paths.','instruction_rvas':['0x29320f7','0x2932166','0x29321c8']}],
    'previous_error':'The representative-dependency maximum credited an unlinked 0.6 basic fallback instead of the linked 0.36 zone, and retained only max(2.4,3.2,4.0) rather than the three distinct active impact potentials.',
    'comparison_roster':['rosie','freja','becca','maddie','ray'],'comparison_scope':'The fixed recorded friendly roster; other roster corrections are audited separately.','baseline_commit':'350272f','before':summary(prior),'after':summary(current),'assumptions':['One eligible target and one activation per bound impact; no measured hit success or area coverage is inferred.','Configured child cooldown exceeds zone lifetime and known stat-inheritance rates are one; unknown repeat, scaling, condition or property-source cases are rejected.','Projectile-local hit offsets are not substituted for caster timeline offsets.','These static Raid paths do not establish original world-report field/Lite execution or active ILFix behavior.'], 'source_sha256':{n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in ['Hero-Combat-Audit.json','Hero-Estimate-Model.json','Retrospective-Damage-Reconstruction.json']}}
    (folder/'Ray-Impact-Audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('Audited',len(paths),'Ray dispatch paths; compared unchanged battle inputs before and after the correction.')
if __name__=='__main__':main()
