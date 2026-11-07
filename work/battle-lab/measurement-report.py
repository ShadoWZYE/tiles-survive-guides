"""Measured reconstruction errors and evidence eligibility, not an accuracy claim."""
import hashlib,json
from pathlib import Path
from accuracy_metrics import damage_metrics,paired_ranking_metrics
ROOT=Path(__file__).resolve().parents[2];FOLDER=ROOT/'outputs/hero-report'
def discrepancy(outgoing,incoming,rounding_budget):
    gap=outgoing-incoming
    return {'outgoing_display_sum':outgoing,'incoming_display_sum':incoming,'difference':gap,'relative_to_outgoing':gap/outgoing if outgoing else None,'conservative_display_rounding_budget':rounding_budget,'larger_than_rounding_budget':abs(gap)>rounding_budget,'attributed_cause':None}
def report(observation,checks,model_bytes):
    hero_taken=sum(h['damage_taken'] for h in observation['heroes']);enemy_taken=sum(observation['opponent']['damage_taken_by_hero'].values())
    outgoing=checks['damage']['total'];enemy_out=observation['opponent']['hero_damage']+observation['opponent']['behemoth_damage']
    skill=checks['skill_power'];gear=checks['gear_power']
    digest=hashlib.sha256(model_bytes).hexdigest()
    return {'schema':1,'battle_id':observation['id'],'model_sha256':digest,'source_sha256':observation['source_sha256'],
        'input_reconstruction_checks':{'skill_power_absolute_error':abs(skill['reconstructed']-skill['observed']),'gear_power_absolute_error':abs(gear['residual']),'gear_power_relative_error':abs(gear['residual'])/gear['observed'],'opening_countdowns_consistent':sum(c['consistent'] for c in checks['opening_countdowns']),'opening_countdowns_checked':len(checks['opening_countdowns']),'scope':'Input and rounded-readiness consistency only. These are not simulated damage or winner errors.'},
        'attribution_axes':{'known_owner_bucket_damage':{'heroes_including_eligible_owned_actors':checks['damage']['hero'],'separate_behemoth_rows':checks['damage']['behemoth']},'within_owner_mechanism_split':None,'direct_hero_vs_soldier_vs_summon_identifiable_from_report':False,'shield_vs_hp_damage_identifiable_from_report':False,'scope':'Ownership and mechanism are separate axes; adding summons or shields on top of an inclusive hero row double counts.'},
        'counter_reconciliation':{'enemy_outgoing_vs_friendly_hero_taken':discrepancy(enemy_out,hero_taken,12*10000),'friendly_outgoing_vs_enemy_hero_taken':discrepancy(outgoing,enemy_taken,7*10000+sum(observation['opponent']['damage_taken_rounding_quanta'])),'rounding_scope':'Conservative one full display unit per row, not a claimed rounding algorithm. Comparison includes pet outgoing rows but only visible hero incoming rows; missing actor coverage and attribution must be checked before treating residual as model error. Shields enter both counters when both endpoints resolve, so shields alone do not prove the cause.'},
        'held_out_simulation':damage_metrics([observation],digest),'matched_global_scoring':paired_ranking_metrics([],digest),
        'next_measurable_tests':['Freeze a complete prediction with model and input hashes before an independent outcome.','Use owner-inclusive report damage as a distinct target from HP removed; never compare the two definitions.','For squad-score validation compare fresh identical enemy states, exact builds/context and troop count, with no uncontrolled rally participants; record the declared outcome metric.'],
        'overall_accuracy_percentage':None}
def main():
    read=lambda n:json.loads((FOLDER/n).read_text(encoding='utf-8'))
    r=report(read('Replay-Observation-2026-11-07.json'),read('Replay-Checks-2026-11-07.json'),(FOLDER/'Hero-Estimate-Model.json').read_bytes());(FOLDER/'Simulation-Measurement-Report.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps({'input_checks':r['input_reconstruction_checks'],'counter_gaps':{k:v['difference'] for k,v in r['counter_reconciliation'].items() if isinstance(v,dict)},'held_out_damage_pairs':r['held_out_simulation']['owner_pairs'],'matched_score_pairs':r['matched_global_scoring']['matched_pairs']}))
if __name__=='__main__':main()
