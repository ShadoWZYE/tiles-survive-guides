"""Evaluate compatible, frozen predictions; never turn mechanics checks into accuracy."""
import math
from datetime import datetime

def valid_number(x):return isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x) and x>=0

def damage_metrics(cases,model_sha256):
    errors=[];actuals=[];excluded={};battles=set();pairs=[]
    def reject(reason):excluded[reason]=excluded.get(reason,0)+1
    for case in cases:
        identity=case.get('id')
        if not identity or identity in battles:reject('duplicate_or_missing_battle_id');continue
        battles.add(identity);prediction=case.get('prediction')
        if not prediction:reject('no_frozen_prediction');continue
        try:
            before=datetime.fromisoformat(prediction['recorded_at'].replace('Z','+00:00'));after=datetime.fromisoformat(case['outcome_recorded_at'].replace('Z','+00:00'))
            frozen=before.utcoffset() is not None and after.utcoffset() is not None and before<after
        except (KeyError,TypeError,ValueError):frozen=False
        if case.get('evaluation_role')!='held_out' or not frozen or prediction.get('model_sha256')!=model_sha256:reject('not_current_independent_held_out_prediction');continue
        if not case.get('damage_definition') or case['damage_definition']!=prediction.get('damage_definition'):reject('incompatible_damage_definition');continue
        observed=case.get('damage_observed',{});predicted=prediction.get('damage',{})
        for owner,actual in observed.items():
            guess=predicted.get(owner)
            if not valid_number(actual) or not valid_number(guess):reject('missing_or_invalid_owner_prediction');continue
            errors.append(abs(guess-actual));actuals.append(actual);pairs.append({'battle_id':identity,'owner':owner,'observed':actual,'predicted':guess,'absolute_error':abs(guess-actual)})
    return {'independent_eligible_battles':len({p['battle_id'] for p in pairs}),'owner_pairs':len(pairs),'mae':sum(errors)/len(errors) if errors else None,'wape':sum(errors)/sum(actuals) if sum(actuals)>0 else None,'exclusions':excluded,'pairs':pairs,'scope':'Same definition, current model hash, held-out timestamped predictions only. WAPE is an error ratio, not winner or global ranking accuracy.'}

def paired_ranking_metrics(pairs,model_sha256):
    checked=[];excluded={};seen=set()
    for pair in pairs:
        identity=pair.get('id')
        reason=None
        if not identity or identity in seen:reason='duplicate_or_missing_pair_id'
        elif pair.get('model_sha256')!=model_sha256:reason='not_current_model'
        elif not pair.get('matched_starting_context_verified'):reason='unmatched_context'
        elif pair.get('confounded_by_other_participants'):reason='other_participants'
        elif pair.get('evaluation_role')!='held_out':reason='not_held_out'
        elif not pair.get('prediction_frozen_before_both_outcomes_verified'):reason='prediction_not_independently_frozen'
        elif pair.get('metric') not in ['damage','enemy_troop_losses','remaining_troops']:reason='unknown_target_metric'
        if identity:seen.add(identity)
        a,b=pair.get('observed',[]),pair.get('predicted_scores',[])
        if reason is None and (len(a)!=2 or len(b)!=2 or not all(valid_number(v) for v in a+b)):reason='invalid_values'
        if reason:excluded[reason]=excluded.get(reason,0)+1;continue
        actual=a[0]-a[1];predicted=b[0]-b[1]
        if actual==0 or predicted==0:excluded['tie']=excluded.get('tie',0)+1;continue
        checked.append((actual>0)==(predicted>0))
    return {'matched_pairs':len(checked),'pairwise_agreement':sum(checked)/len(checked) if checked else None,'exclusions':excluded,'scope':'Agreement for the declared outcome metric and reviewed matched context. Does not imply universal balanced-score accuracy.'}
