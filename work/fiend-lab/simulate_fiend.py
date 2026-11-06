"""First fiend simulation layer: encounter resolution and cooldown opportunities.

Uses raw field/Lite cooldown units. It intentionally has no guessed conversion
to seconds, damage formula, death model or win prediction. Ready skills are
opportunities, not proof that the runtime executes simultaneous casts.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def casualty_expectation(incapacitated, rule):
    """Unrounded split for an explicitly selected rule; does not predict defeats.

Rule routing and integer rounding must be checked separately. A forced treatment
rule is rejected because its triggering context is not yet implemented.
"""
    if not isinstance(incapacitated, int) or isinstance(incapacitated, bool) or incapacitated < 0:
        raise ValueError('Provide a nonnegative known incapacitated troop count.')
    if rule['IsForced'] or rule['LossRate'] != 1:
        raise ValueError('Forced or scaled casualty rule is outside the verified split helper.')
    hospital, minor = rule['WoundRate'], rule['MinorWoundRate']
    if not 0 <= hospital <= 1 or not 0 <= minor <= 1 or hospital + minor > 1 + 1e-12:
        raise ValueError('Invalid casualty rates.')
    return {'hospital_unrounded': incapacitated * hospital,
            'minor_wounded_unrounded': incapacitated * minor,
            'permanent_unrounded': incapacitated * max(0, 1 - hospital - minor)}


def cooldown_opportunities(skills, catalog, horizon_ticks, alive_until=None):
    if not isinstance(horizon_ticks, int) or isinstance(horizon_ticks, bool) or not 0 <= horizon_ticks <= 100000:
        raise ValueError('Horizon must be an integer from 0 to 100000 raw cooldown units.')
    if alive_until is not None and (not isinstance(alive_until, (int, float)) or isinstance(alive_until, bool) or not math.isfinite(alive_until) or alive_until < 0):
        raise ValueError('Invalid explicit alive-until boundary.')
    stop = horizon_ticks if alive_until is None else min(horizon_ticks, alive_until)
    events, excluded = [], []
    for selected in skills:
        if not isinstance(selected.get('level'), int) or selected['level'] <= 0:
            continue  # Unrecorded/locked grants no activity, matching My builds.
        skill = catalog.get(selected.get('lite_skill'))
        if skill is None:
            excluded.append({'skill': selected.get('id', selected.get('skill_type')), 'reason': 'missing field skill link'})
            continue
        initial, period = skill['initial_cd_raw'], skill['common_cd_raw']
        if initial < 0 or period <= 0 or skill['condition'] or skill['round_limit'] or skill['total_limit'] or skill['round_type'] or skill['prepare_round']:
            excluded.append({'skill': skill['id'], 'reason': 'conditional, triggered, limited or invalid cadence'})
            continue
        # Half-open [0, horizon): no cast is credited at the stop/death boundary.
        t = initial
        while t < stop:
            events.append({'at_raw_tick': t, 'skill': skill['id'],
                           'effect_ids': [e['Id'] for e in skill['effects']]})
            t += period
    events.sort(key=lambda e: (e['at_raw_tick'], e['skill']))
    return {'events': events, 'excluded': excluded}


def friendly_skills(slug, saved, hero_catalog, progression):
    """Conservative saved-skill selection, without modifying a stored profile."""
    saved = saved or {}
    hero = progression['heroes'][slug]
    stage_id = saved.get('stage', saved.get('Stage'))
    stage = next((s for s in hero['stages'] if s['id'] == stage_id),
                 min(hero['stages'], key=lambda s: (s['rank'], s['step'])))
    recorded = saved.get('skills', saved.get('Skills')) or {}
    result = []
    for skill in hero_catalog[slug]['skills']:
        n = recorded.get(skill['id'], 0)
        caps = stage['skill_caps']
        cap = caps[skill['slot']] if skill['slot'] < len(caps) else 0
        row = next(s for s in hero['skills'] if s['id'] == skill['id'])
        if not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= cap or n > 0 and not any(r['level'] == n for r in row['levels']):
            n = 0
        result.append({**skill, 'level': n})
    return result


def simulate(data, encounter_id, horizon_ticks, formation=0, squad=None, profile=None, progression=None):
    encounter = data['encounters'][encounter_id]
    if not 0 <= formation < len(encounter['formations']):
        raise ValueError('Unknown formation index.')
    enemy = encounter['formations'][formation]
    result = {
        'scope': 'Raw cooldown opportunity simulation; no live battle outcome prediction.',
        'encounter': encounter_id, 'formation_index': formation, 'horizon_raw_ticks': horizon_ticks,
        'time_in_seconds': None, 'winner': None, 'damage_prediction': None,
        'assumptions': ['All listed actors remain alive for this horizon.',
                        'Unmodified field cooldowns; no cast arbitration, movement or interruptions.',
                        'Other formations are separate inputs, not assumed simultaneous enemies.'],
        'enemy': [], 'friendly': [], 'unresolved': data['unresolved'],
    }
    for unit in enemy['units']:
        result['enemy'].append({'actor': unit['npc_actor'], 'position_index': unit['position_index'],
                                **cooldown_opportunities(unit['skills'], data['lite_skills'], horizon_ticks)})
    if squad:
        if len(squad) != 5 or len(set(squad)) != 5 or progression is None:
            raise ValueError('Supply exactly five distinct heroes and progression data.')
        if progression['client_build'] != data['client_build']:
            raise ValueError('Encounter and hero-progression builds differ; refresh before comparing.')
        builds = (profile or {}).get('hero_builds', {})
        for slot, slug in enumerate(squad):
            selected = friendly_skills(slug, builds.get(slug), data['heroes'], progression)
            result['friendly'].append({'actor': slug, 'position_index': slot,
                **cooldown_opportunities(selected, data['lite_skills'], horizon_ticks)})
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, default=ROOT / 'outputs/fiend-lab/Fiend-Encounter-Data.json')
    p.add_argument('--encounter', default='gve_boss_new_period_10')
    p.add_argument('--formation', type=int, default=0)
    p.add_argument('--horizon-ticks', type=int, required=True)
    p.add_argument('--profile', type=Path)
    p.add_argument('--squad', nargs=5)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    read = lambda f: json.loads(f.read_text(encoding='utf-8'))
    result = simulate(read(args.data), args.encounter, args.horizon_ticks, args.formation,
                      args.squad, read(args.profile) if args.profile else None,
                      read(ROOT / 'outputs/hero-report/TilesSurvive-Upgrade-Data.json') if args.squad else None)
    result['encounter_data_sha256'] = hashlib.sha256(args.data.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"Simulated cooldown opportunities for {len(result['enemy'])} enemies and {len(result['friendly'])} heroes. Damage/winner remain unvalidated.")


if __name__ == '__main__':
    main()
