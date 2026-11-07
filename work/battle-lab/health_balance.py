"""HP accounting identities and a tested report-interpretation hypothesis."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def finite(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('Finite numeric value required')
    return value

def health_ledger(max_hp,events,initial_hp=None):
    maximum=finite(max_hp);initial=maximum if initial_hp is None else finite(initial_hp)
    if maximum<=0 or not 0<=initial<=maximum:raise ValueError('Invalid initial HP')
    hp=initial;damage=shield=applied=overkill=healing=overheal=0.
    for event in events:
        amount=finite(event['amount'])
        if amount<0:raise ValueError('Negative amount')
        if event['kind']=='damage':
            absorbed=finite(event.get('shield_absorbed',0))
            if not 0<=absorbed<=amount:raise ValueError('Invalid shield absorption')
            taken=min(hp,amount-absorbed);damage+=amount;shield+=absorbed;applied+=taken;overkill+=amount-absorbed-taken;hp-=taken
        elif event['kind']=='heal':
            actual=min(maximum-hp,amount);healing+=actual;overheal+=amount-actual;hp+=actual
        else:raise ValueError('Unsupported HP event')
    net=initial-hp
    return {'initial_hp':initial,'final_hp':hp,'gross_damage':damage,'shield_absorbed':shield,'hp_damage_applied':applied,'effective_healing':healing,'overheal':overheal,'overkill':overkill,'net_hp_lost':net,'balance_residual':damage-(net+healing+shield+overkill),'scope':'Bookkeeping for supplied post-defence event magnitudes. No targeting, mitigation, recovery eligibility or revival rules are simulated.'}

def reconcile(gross,taken,shown_healing,rounding):
    for n in [gross,taken,shown_healing,rounding]:
        if finite(n)<0:raise ValueError('Negative report aggregate')
    before=gross-taken;after=before-shown_healing
    return {'gross_outgoing_display':gross,'taken_display':taken,'shown_opponent_healing':shown_healing,'unadjusted_gap':before,'healing_adjusted_gap':after,'unadjusted_gap_fraction':before/gross if gross else None,'adjusted_gap_fraction':after/gross if gross else None,'conservative_rounding_budget':rounding,'within_display_precision':abs(after)<=rounding,'remaining_gap_interval':[after-rounding,after+rounding]}

def report(observation):
    friendly_damage=sum(h['damage'] for h in observation['heroes'])+sum(p['damage'] for p in observation['friendly']['behemoths'])
    friendly_taken=sum(h['damage_taken'] for h in observation['heroes'])
    friendly_heals=sum(h['healing'] for h in observation['heroes'] if h['healing'] is not None)+sum(p['healing'] for p in observation['friendly']['behemoths'] if p['healing'] is not None)
    enemy_taken=sum(observation['opponent']['damage_taken_by_hero'].values());enemy_heals=sum(x['value'] for x in observation['opponent']['shown_healing'])
    enemy_damage=observation['opponent']['hero_damage']+observation['opponent']['behemoth_damage']
    return {'schema':1,'battle_id':observation['id'],'source_sha256':observation['source_sha256'],'fitted_parameters':0,
        'hypothesis':'Displayed outgoing damage is gross pressure while the incoming column may describe net HP depletion. Test outgoing = taken + effective recovery + shield/overkill/coverage terms; reported shown healing is only a proxy for effective recovery.',
        'friendly_outgoing':reconcile(friendly_damage,enemy_taken,enemy_heals,90030+sum(x['display_quantum'] for x in observation['opponent']['shown_healing'])),
        'enemy_outgoing':reconcile(enemy_damage,friendly_taken,friendly_heals,140020),
        'status':'Consistent within display precision in the friendly-outgoing direction. Reverse direction retains a positive residual; this is evidence for a bookkeeping hypothesis, not proof of the server counter definitions.',
        'limits':['Shown healing may differ from effective recovery and may have recipient coverage not visible in the report.','The remaining reverse-direction residual could include overkill, shields, omitted recovery or actor coverage; it is not assigned to any one cause.','Neither per-hero damage predictions nor global scoring weights are calibrated by this accounting identity.','Conservative display budgets use one full shown unit per value, not an assumed exact rounding implementation.']}
def main():
    folder=ROOT/'outputs/hero-report';r=report(json.loads((folder/'Replay-Observation-2026-11-07.json').read_text(encoding='utf-8')));(folder/'Health-Balance-Reconciliation.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:r[k] for k in ['friendly_outgoing','enemy_outgoing']},indent=2))
if __name__=='__main__':main()
