"""Build transparent low-confidence all-hero reference estimates from audited data.

This is an inference model, not an implementation of the game's combat engine.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build(upgrades, audit, roster):
    if audit['provenance']['config_pack_sha256'] != upgrades['provenance']['config_pack_sha256']:
        raise ValueError('Combat audit and progression data must identify the same snapshot.')
    result = {'version': 1, 'reference_level': 110, 'reference_rank': 3,
              'reference_step': 6, 'heroes': {}}
    for slug, hero in upgrades['heroes'].items():
        stage = next(s for s in hero['stages'] if s['rank'] == 3 and s['step'] == 6)
        level = next(s for s in hero['levels'] if s['level'] == min(110, stage['level_max']))
        ref_stats = [a + b for a, b in zip(stage['stats'], level['stats'])]
        source_skills = {s['internal_name']: s for s in roster[slug]['skills']}
        audited = {s['id']: s for s in audit['heroes'][slug]['skills']}
        curves = []
        for skill in hero['skills']:
            evidence = audited[skill['id']]
            effects = [e for e in evidence['referenced_effects'] if '_text' not in e['id'].lower()]
            damage = [e for e in effects if e['type'] == 0 and not e['custom_formula'] and e['base_param2'] > 0]
            source = source_skills[skill['id']]
            text = ' '.join([source.get('game_description', ''), *[e['id'] for e in effects]]).lower()
            # Dimensionless planning priors. They are deliberately not native effect magnitudes.
            utility = (1.3 if any(e['type'] == 1 for e in effects) or 'heal' in text else 0)
            for tokens, weight in [(['shield'], 1.2), (['stun'], .8), (['slow'], .35),
                                   (['atk_down', 'attack reduction'], .6), (['def_down', 'defense reduction'], .8),
                                   (['damage reduction', 'dmg_reduce'], .9), (['summon'], .6)]:
                if any(t in text for t in tokens):
                    utility += weight
            if any(e['type'] == 7 for e in effects) and 'summon' not in text:
                utility += .6
            cadence = skill['cooldown'] / 1000 if skill['cooldown'] > 0 else (2 if skill['slot'] == 0 else 12)
            cadence = max(.5, cadence)
            levels = [{'level': 0, 'damage': 0, 'utility': 0}]
            for row in skill['levels']:
                modifiers = {}
                for param in row['params']:
                    parts = param.split('|')
                    if len(parts) == 4 and parts[0] == 'pve_effect' and parts[2] == 'effect_param2':
                        try:
                            n = float(parts[3])
                            if math.isfinite(n) and n >= 0:
                                modifiers[parts[1]] = n
                        except ValueError:
                            pass
                # One representative non-text effect per assumed activation, never a sum of references.
                representative = max((e['base_param2'] / 1000 * modifiers.get(e['id'], 1) for e in damage), default=0)
                # Unknown is not zero: generic pressure prior when effects cannot be resolved.
                unresolved = not effects or bool(evidence['missing_assets']) or bool(evidence['unresolved_event_references']) or any(e['custom_formula'] for e in effects)
                pressure = representative / cadence if damage else ((.25 if skill['slot'] == 0 else .08) if unresolved else 0)
                levels.append({'level': row['level'], 'damage': round(pressure, 8), 'utility': utility})
            curves.append({'id': skill['id'], 'slot': skill['slot'], 'levels': levels,
                           'reference_level': min(stage['skill_caps'][skill['slot']], max(r['level'] for r in levels)),
                           'damage_effects': [e['id'] for e in damage], 'cadence_assumed_seconds': cadence,
                           'uses_generic_pressure_prior': not bool(damage)})
        result['heroes'][slug] = {'reference_stage': stage['id'], 'reference_level': level['level'],
                                  'reference_stats': ref_stats, 'skills': curves}
    # Fixed anchors from the reference roster: changing a user's build never re-normalizes everyone else.
    raw = []
    for model in result['heroes'].values():
        rates = [next(r for r in s['levels'] if r['level'] == s['reference_level']) for s in model['skills']]
        a, d, h = model['reference_stats']
        pressure = sum(r['damage'] for r in rates); utility = sum(r['utility'] for r in rates)
        raw.append([a * (1 + .5 * math.log1p(pressure)),
                    (.7 * h + 30 * d) * (1 + .08 * utility), 1 + utility])
    result['scales'] = [max(r[i] for r in raw) for i in range(3)]
    result['source_pack_sha256'] = upgrades['provenance']['config_pack_sha256']
    result['confidence'] = 'low'
    return result


if __name__ == '__main__':
    folder = ROOT / 'outputs/hero-report'
    read = lambda name: json.loads((folder / name).read_text(encoding='utf-8'))
    model = build(read('TilesSurvive-Upgrade-Data.json'), read('Hero-Combat-Audit.json'),
                  {h['asset_slug']: h for h in read('TilesSurvive-Hero-Data.json')})
    (folder / 'Hero-Estimate-Model.json').write_text(json.dumps(model, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Built low-confidence reference model for {len(model["heroes"])} heroes.')
