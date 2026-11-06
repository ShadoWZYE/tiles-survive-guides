"""Compare independently transcribed report inputs; this is not prediction validation."""
import argparse
import hashlib
import json
from pathlib import Path
from simulate_fiend import casualty_expectation

ROOT = Path(__file__).resolve().parents[2]


def check(data, observation):
    first_round = observation['visible_first_round']
    encounter = data['encounters']['gve_boss_new_period_10']
    checks = []
    for f in encounter['formations']:
        checks.append({
            'formation': f['id'],
            'troops': {'observed': first_round['enemy_troop_count'], 'configured': f['troop_count'],
                       'match': first_round['enemy_troop_count'] == f['troop_count']},
            'hero_power': {'observed': first_round['enemy_hero_power'], 'configured': f['configured_hero_power_sum'],
                           'match': first_round['enemy_hero_power'] == f['configured_hero_power_sum']},
        })
    return {
        'scope': 'Cross-date configuration consistency against one recorded encounter, not held-out battle prediction.',
        'source': observation['source'], 'target_display': observation['target_display'],
        'independent_observed_encounters': 1,
        'note': 'Five matching variants are not five independent report samples. Rounded rally contribution percentages are not single-fight damage coefficients.',
        'checks': checks, 'damage_prediction_cases': 0, 'winner_prediction_cases': 0,
        'accuracy_percentage': None,
        'report_reconstruction_limitations': observation['limitations'],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--observation', type=Path, required=True)
    p.add_argument('--data', type=Path, default=ROOT/'outputs/fiend-lab/Fiend-Encounter-Data.json')
    p.add_argument('--extra-observation', type=Path, default=ROOT/'outputs/fiend-lab/November-Fiend-Observation.json')
    p.add_argument('--output', type=Path, default=ROOT/'outputs/fiend-lab/Report-Input-Checks.json')
    args = p.parse_args()
    data = json.loads(args.data.read_text(encoding='utf-8'))
    result = check(data, json.loads(args.observation.read_text(encoding='utf-8')))
    if args.extra_observation.is_file():
        extra = json.loads(args.extra_observation.read_text(encoding='utf-8'))
        observed = extra['casualty_observation']
        expected = casualty_expectation(observed['incapacitated'], data['casualty_rule_candidates'][observed['candidate_rule']])
        result['casualty_consistency_check'] = {
            'source_sha256': extra['source_sha256'], 'frame_seconds_approx': observed['frame_seconds_approx'],
            'candidate_rule': observed['candidate_rule'], 'expected_unrounded': expected,
            'matches': expected['hospital_unrounded'] == observed['hospitalised'] and
                       expected['minor_wounded_unrounded'] == observed['lightly_wounded'] and
                       expected['permanent_unrounded'] == observed['permanent_losses'],
            'scope': observed['classification'],
        }
    result['data_sha256'] = hashlib.sha256(args.data.read_bytes()).hexdigest()
    result['observation_sha256'] = hashlib.sha256(args.observation.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    if not all(c['troops']['match'] and c['hero_power']['match'] for c in result['checks']):
        raise SystemExit('Report/config mismatch; inspect encounter identity before calibration.')
    if result.get('casualty_consistency_check', {}).get('matches') is False:
        raise SystemExit('Casualty candidate does not match the observation.')
    print('Troop count and hero power match the report; no prediction accuracy inferred.')


if __name__ == '__main__':
    main()
