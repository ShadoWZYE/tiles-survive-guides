"""Reproducible evidence checks; software parity is not predictive accuracy.

Only cases explicitly marked held_out with a recorded prediction can contribute
to prediction metrics. Existing replay reports are mechanics observations only.
"""
import argparse
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def prediction_metrics(cases,model_sha256=None):
    winners=[];errors=[];relative=[];excluded=0
    for case in cases:
        if case.get('evaluation_role')!='held_out':continue
        prediction=case.get('prediction') or {}
        try:
            before=datetime.fromisoformat(prediction['recorded_at'].replace('Z','+00:00'))
            after=datetime.fromisoformat(case['outcome_recorded_at'].replace('Z','+00:00'))
            digest=prediction['model_sha256']
            valid=before.utcoffset() is not None and after.utcoffset() is not None and before<after and bool(re.fullmatch('[a-fA-F0-9]{64}',digest))
            if model_sha256 is not None:valid=valid and digest.lower()==model_sha256.lower()
        except (KeyError,TypeError,ValueError,AttributeError):valid=False
        if not valid:
            excluded+=1;continue
        observed=case.get('outcome');predicted=prediction.get('outcome')
        if observed in ('win','loss') and predicted in ('win','loss'):
            winners.append(observed==predicted)
        for key,actual in case.get('damage_observed',{}).items():
            guess=prediction.get('damage',{}).get(key)
            if not all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and x>=0 for x in (actual,guess)):continue
            errors.append(abs(guess-actual))
            if actual>0:relative.append(abs(guess-actual)/actual)
    return {'winner_cases':len(winners),'winner_accuracy':sum(winners)/len(winners) if winners else None,
            'excluded_held_out_cases':excluded,
            'damage_pairs':len(errors),'damage_mae':sum(errors)/len(errors) if errors else None,
            'positive_actual_damage_pairs':len(relative),'damage_mape':sum(relative)/len(relative) if relative else None,
            'limits':'Held-out designation and prediction provenance must be independently reviewed. These metrics are not confidence intervals or a tier-ranking accuracy measure.'}


def check_countdown(observed,configured_seconds):
    if not isinstance(observed,int) or isinstance(observed,bool) or observed<1:return False
    if not isinstance(configured_seconds,(int,float)) or not math.isfinite(configured_seconds):return False
    return observed-1<configured_seconds<=observed


def report(folder,evidence):
    read=lambda name:json.loads((folder/name).read_text(encoding='utf-8'))
    model=read('Hero-Estimate-Model.json');audit=read('Hero-Combat-Audit.json');upgrades=read('TilesSurvive-Upgrade-Data.json')
    roster={h['asset_slug']:h for h in read('TilesSurvive-Hero-Data.json')}
    if set(roster)!=set(model['heroes']) or set(roster)!=set(audit['heroes']):raise ValueError('Mismatched hero coverage')
    if model['source_pack_sha256']!=upgrades['provenance']['config_pack_sha256']:raise ValueError('Model/progression snapshot mismatch')
    for key in ['config_pack_sha256','manifest_sha256']:
        if audit['provenance'][key]!=upgrades['provenance'][key]:raise ValueError('Combat/progression snapshot mismatch: '+key)
    native=audit.get('native_audit',{})
    if native:
        digest=hashlib.sha256((folder/'Hero-Native-Combat-Audit.json').read_bytes()).hexdigest()
        if digest!=native['audit_sha256'] or digest!=model.get('native_audit_sha256'):raise ValueError('Native audit/model fingerprint mismatch')
    checks=[]
    for battle in evidence.get('battles',[]):
        for hero in battle['heroes']:
            if 'opening_countdown_display' not in hero:continue
            slug=hero['planner_slug']
            if roster[slug]['name']!=hero['name']:raise ValueError('Replay identity mapping mismatch: '+hero['name'])
            skill=next(s for s in model['heroes'][slug]['skills'] if s['slot']==1)
            seconds=skill['base_pre_cooldown_ms']/1000
            checks.append({'battle_id':battle['id'],'hero':hero['name'],'slug':slug,
                'frame_seconds':battle['opening_countdown_frame_seconds'],
                'observed_display':hero['opening_countdown_display'],'configured_seconds':seconds,
                'consistent':check_countdown(hero['opening_countdown_display'],seconds)})
    heroes={}
    for slug,hero in model['heroes'].items():
        skills=hero['skills']
        heroes[slug]={'name':roster[slug]['name'],
            'bound_cast_paths':sum(s.get('cast_duration_at_unit_speed_seconds') is not None for s in skills),
            'timed_direct_paths':sum(bool(s['levels'][1].get('cast_budget',{}).get('direct_events')) for s in skills),
            'damage_zone_paths':sum(s['has_damage_zone'] for s in skills),
            'summon_dependency_paths':sum(s['has_summon_dependency'] for s in skills),
            'mapped_actor_links':sum(len(s.get('summoned_actors',[])) for s in audit['heroes'][slug]['skills']),
            'conditional_effect_references':sum(len(s.get('conditional_effects',[])) for s in skills),
            'proxy_damage_paths':sum(s['damage_selection_basis']=='representative_dependency' for s in skills),
            'resolved_raw_healing_effects':sum(len(s['levels'][1].get('healing_budgets',[])) for s in skills),
            'prediction_confidence':'not empirically calibrated'}
    return {'version':1,'model_version':model['version'],'client_data_build':upgrades['client_build'],
        'native_semantics':{'traced_build':model['native_semantics_build'],
            'current_build_reverified':model['current_native_semantics_reverified'],
            'selected_current_method_count':model.get('native_selected_method_count',0),
            'scope':model.get('native_verification_scope','prior build only')},
        'source_sha256':{n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in
            ['Hero-Estimate-Model.json','Hero-Combat-Audit.json','TilesSurvive-Upgrade-Data.json','TilesSurvive-Hero-Data.json']},
        'mechanics_checks':{'kind':'in-sample consistency, not held-out prediction validation',
            'countdown_rule':'Ceiling-display hypothesis: displayed minus one < configured initial delay <= displayed. Intro counts are rounded, not measured cast-start timestamps.',
            'opening_countdowns':checks,'consistent_count':sum(c['consistent'] for c in checks),'checked_count':len(checks)},
        'prediction_metrics':prediction_metrics(evidence.get('battles',[]),hashlib.sha256((folder/'Hero-Estimate-Model.json').read_bytes()).hexdigest()),
        'healing_scope':'Selected raw per-dispatch formulas only, before live outgoing/incoming/contextual modifiers. No effective healing, recipient counts, missing HP, overheal or HPS calibration.',
        'heroes':heroes,'remaining_global_gaps':['Untraced current executable paths, referenced data and live patches',
            'Interrupt/AI decisions, movement, target selection, live attack speed and deaths',
            'Troop/research/behemoth interaction with live hero damage',
            'Conditional, summon, zone and effective-healing execution',
            'Held-out matched fight predictions recorded before outcomes'],
        'accuracy_percentage':None,'accuracy_status':'No validated overall accuracy percentage. Consistency checks and software parity do not establish battle prediction accuracy.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,default=ROOT/'outputs/hero-report')
    p.add_argument('--evidence',type=Path,default=ROOT/'outputs/battle-reports/Battle-Replay-Evidence-2026-10-25.json')
    p.add_argument('--output',type=Path,default=ROOT/'outputs/hero-report/Hero-Model-Validation.json')
    args=p.parse_args();evidence=json.loads(args.evidence.read_text(encoding='utf-8'))
    result=report(args.data,evidence)
    result['evidence_sha256']=hashlib.sha256(args.evidence.read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    checks=result['mechanics_checks']
    print(f"Opening countdown consistency: {checks['consistent_count']}/{checks['checked_count']}; held-out winner cases: {result['prediction_metrics']['winner_cases']}. Overall accuracy unvalidated.")


if __name__=='__main__':main()
