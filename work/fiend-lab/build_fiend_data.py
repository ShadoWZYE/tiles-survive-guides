"""Export manifest-verified field-fiend encounters; raw CFGs stay private.

This deliberately does not substitute RaidNewSkill formulas for the field/Lite
skill links used by the NPC records. It exports inputs for independent testing.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'work/hero-extraction'))
from refresh_hero_data import verified_tables
from decode_cfg import decode_table

TABLES = {
    'gve_boss', 'npc_monster', 'npc_survivor', 'survivor', 'survivor_level',
    'survivor_rank', 'survivor_level_main', 'survivor_rank_main',
    'survivor_skill_type', 'survivor_skill_main', 'survivor_slg_skill_new',
    'survivor_slg_effect_new', 'benefits', 'battle_formula_coefficient', 'battle_wounded',
}


def build(tables, roster):
    index = {name: {r['InternalId']: r for r in rows} for name, rows in tables.items()}
    benefits = index['benefits']
    def values(rows):
        result = {}
        for row in rows:
            name = benefits[row['benefit_id']]['Id']
            result[name] = result.get(name, 0) + row['benefit_value']
        return result

    skill_rows = {}
    for row in tables['survivor_skill_main']:
        skill_rows[(row['SkillType'], row['Level'])] = row
    levels = {(r['SurvivorType'], r['Level']): r for r in tables['survivor_level_main']}
    ranks = {(r['SurvivorType'], r['Rank'], r['RankSmall']): r for r in tables['survivor_rank_main']}
    skills = {}

    def linked_skill(skill_type):
        kind = index['survivor_skill_type'][skill_type]
        link = kind['SurvivorSlgSkillNew_ID']
        if not link:
            return None
        row = index['survivor_slg_skill_new'][link]
        if row['Id'] not in skills:
            effects = [index['survivor_slg_effect_new'][i] for i in row['SkillEffectNew_ID']]
            skills[row['Id']] = {
                'id': row['Id'], 'initial_cd_raw': row['InitialCd'],
                'common_cd_raw': row['CommonCd'], 'type': row['Type'],
                'condition': row['Condition'], 'prepare_round': row['PrepareRound'],
                'round_limit': row['RoundLimit'], 'total_limit': row['TotalLimit'],
                'round_type': row['RoundType'], 'round_param': row['RoundParam'],
                'start_rate_raw': row['StartRate'],
                'effects': [{k: e[k] for k in [
                    'Id', 'Type', 'TargetTypeLite', 'TargetPosition', 'TargetNum',
                    'TargetArmy', 'SpecialTarget', 'AttackCount', 'AttackInterval',
                    'ExtraTriggerSkill', 'SkillDuration', 'BuffId', 'EffectAttrRate',
                    'EffectType', 'Lag', 'StartRate', 'Condition',
                ]} for e in effects],
            }
        return row['Id']

    encounters = {}
    for boss in tables['gve_boss']:
        if not boss['Id'].startswith('gve_boss_new_period_'):
            continue
        formations = []
        for npc_id in boss['Monsters']:
            npc = index['npc_monster'][npc_id]
            units = []
            for position, actor_id in enumerate(npc['Survivor']):
                actor = index['npc_survivor'][actor_id]
                kind = index['survivor'][actor['Type']]
                level = index['survivor_level'][actor['Level']]['Level']
                rank = index['survivor_rank'][actor['Rank']]
                level_row = levels[(kind['InternalId'], level)]
                rank_row = ranks[(kind['InternalId'], rank['Rank'], rank['ChildRank'])]
                actor_skills = []
                for skill_id, slot in kind['SkillConfig'].items():
                    skill_id = int(skill_id)
                    n = actor['Skill'][slot] if slot < len(actor['Skill']) else 0
                    row = skill_rows.get((skill_id, n))
                    actor_skills.append({
                        'skill_type': index['survivor_skill_type'][skill_id]['Id'],
                        'slot': slot, 'level': n, 'lite_skill': linked_skill(skill_id),
                        'configured_skill_power': row['BattlePower'] if row else None,
                        'field_benefits': values(row['Benefits']) if row else {},
                        'combat_skill_override_id': row['CombatSkill'] if row else None,
                    })
                units.append({
                    'position_index': position, 'npc_actor': actor['Id'],
                    'hero_type': kind['Id'], 'level': level,
                    'rank': rank['Rank'], 'rank_step': rank['ChildRank'],
                    'configured_power': level_row['BattlePower'] + rank_row['BattlePower'] +
                        sum(s['configured_skill_power'] or 0 for s in actor_skills),
                    # Preserve distinct sources. Their final stacking is not inferred here.
                    'level_benefits': values(level_row['BenefitsTroops']),
                    'rank_benefits': values(rank_row['BenefitTroop']),
                    'skills': actor_skills,
                })
            formations.append({
                'id': npc['Id'], 'name_key': npc['Name'],
                'troops': npc['Troops'], 'troop_count': sum(npc['Troops'].values()),
                'display_power_reference': npc['RecommendedPower'],
                'configured_hero_power_sum': sum(u['configured_power'] for u in units),
                'shared_benefits': values(npc['Benefit']), 'units': units,
            })
        encounters[boss['Id']] = {
            'level': boss['BossLevel'], 'array_num_raw': boss['ArrayNum'],
            'min_round_raw': boss['MinRound'], 'formations': formations,
            'total_configured_troops': sum(f['troop_count'] for f in formations),
        }

    heroes = {}
    for hero in roster:
        kind = index['survivor'][hero['hero_id']]
        heroes[hero['asset_slug']] = {
            'name': hero['name'],
            'skills': [{
                'id': index['survivor_skill_type'][int(key)]['Id'], 'slot': slot,
                'lite_skill': linked_skill(int(key)),
            } for key, slot in kind['SkillConfig'].items()],
        }
    return {
        'schema': 1, 'scope': 'Field-fiend encounter inputs and raw cooldown opportunities; not a win-rate model.',
        'encounters': encounters, 'heroes': heroes, 'lite_skills': skills,
        'battle_constants': {r['Id']: {'value_raw': r['Value'], 'state_overrides_raw': r['KidValue']}
                             for r in tables['battle_formula_coefficient']},
        'casualty_rule_candidates': {r['Id']: {k: r[k] for k in ['LossRate', 'WoundRate', 'MinorWoundRate', 'IsForced', 'WoundRateForced', 'MinorWoundRateForced']}
                                    for r in tables['battle_wounded'] if r['Id'] in ['battle_gve_rally', 'battle_monster_rally', 'battle_monster_attack']},
        'unresolved': [
            'Type 11100 field-effect dispatch and final skill magnitudes',
            'Final property composition, troop-count scaling and casualties',
            'Cooldown units, runtime cooldown modifiers and shared-cast arbitration',
            'Target selection, movement, death times, buffs, shields and healing execution',
            'Behemoth combat skills, rally ordering and carry-over state',
            'Applicability of the separate Raid damage/power-ratio formulas to field battles',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--loose-directory', type=Path)
    parser.add_argument('--private-output', type=Path, required=True)
    parser.add_argument('--client-build', required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/fiend-lab/Fiend-Encounter-Data.json')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    found = verified_tables(args.pack.read_bytes(), manifest, TABLES, args.loose_directory)
    args.private_output.mkdir(parents=True, exist_ok=True)
    tables, hashes = {}, {}
    for name, (_, raw) in found.items():
        target = args.private_output / (name + '.cfg')
        target.write_bytes(raw)
        tables[name] = decode_table(target)['rows']
        hashes[name] = hashlib.sha256(raw).hexdigest()
    roster = json.loads((ROOT / 'outputs/hero-report/TilesSurvive-Hero-Data.json').read_text(encoding='utf-8'))
    result = build(tables, roster)
    result.update(client_build=args.client_build, source_hashes=hashes,
                  manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                  pack_sha256=hashlib.sha256(args.pack.read_bytes()).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"Exported {len(result['encounters'])} encounters and {len(result['lite_skills'])} linked field skills.")


if __name__ == '__main__':
    main()
