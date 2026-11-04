"""Record Signature skill links without interpreting unverified Lite buff semantics.

Input must be the private CFG directory obtained with verified_tables. No game
assets are copied into the published audit; only selected identifiers/parameters.
"""
import argparse
import hashlib
import json
from pathlib import Path
from decode_cfg import decode_table

ROOT = Path(__file__).resolve().parents[2]


def audit(source):
    names = ['survivor_exclusive_gear_main', 'survivor_skill_main',
             'survivor_skill_type', 'survivor_slg_skill_new',
             'survivor_slg_effect_new', 'effect_buff']
    tables = {name: decode_table(source / (name + '.cfg'))['rows'] for name in names}
    indexed = {name: {r['InternalId']: r for r in rows} for name, rows in tables.items()}
    gears = []
    for gear in tables['survivor_exclusive_gear_main']:
        if gear['Level'] != 1:
            continue
        main = indexed['survivor_skill_main'].get(gear['GearSkillSlg'], {})
        kind = indexed['survivor_skill_type'].get(main.get('SkillType'), {})
        lite = indexed['survivor_slg_skill_new'].get(kind.get('SurvivorSlgSkillNew_ID'), {})
        effects = [indexed['survivor_slg_effect_new'].get(i, {})
                   for i in lite.get('SkillEffectNew_ID', [])]
        gears.append({'gear': gear['Id'], 'skill': main.get('Id'),
                      'skill_type': kind.get('Id'), 'raid_new_skill': kind.get('RaidNewSkill'),
                      'lite_skill': lite.get('Id'),
                      'effects': [{'id': e.get('Id'), 'type': e.get('Type')} for e in effects],
                      'legacy_se_overall_benefits': gear['GearSkillSeOverallBenefit'],
                      'explicit_slg_skill_benefits': gear['GearSkillSlgBenefit'],
                      'gear_skill_addition': gear['GearSkillAddition'],
                      'score_status': 'excluded_pending_runtime_semantics'})
    levels = tables['survivor_exclusive_gear_main']
    return {
        'coverage': {'configured_levels': len(levels), 'levels_with_gear_skill_addition': sum(bool(r['GearSkillAddition']) for r in levels), 'levels_with_explicit_slg_skill_benefits': sum(bool(r['GearSkillSlgBenefit']) for r in levels), 'levels_with_legacy_se_overall_benefits': sum(bool(r['GearSkillSeOverallBenefit']) for r in levels)},
        'audited_date': '2026-11-04',
        'scope': 'Configuration links, not verified combat outcomes or buff formulas.',
        'source_hashes': {n: hashlib.sha256((source / (n + '.cfg')).read_bytes()).hexdigest() for n in names},
        'level_one_links': gears,
        'gear_named_buff_rows': [
            {k: r[k] for k in ['Id', 'TypeLite', 'AdditonTypeLite', 'ParamLite']}
            for r in tables['effect_buff'] if '_gear_' in r['Id']],
        'unavailable': [
            'Legacy SE-only overall percentages cannot establish the field Lite skill formula. Runtime resolution of Type 11100 and gear benefit markers into buff applications.',
            'Meaning of the two numeric ParamLite operands, level interpolation and stacking rules.',
            'Recipients, uptime and equivalence between field Lite effects and raid comparison model.',
        ],
        'conclusion': 'Gear-named PhysicalDamageIncrease/Reduce rows exist. Their presence does not justify treating tooltip ATK/DEF percentages as field damage multipliers. No server override is established by this evidence.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    result = audit(args.source)
    output = ROOT / 'outputs/hero-report/Hero-Signature-Link-Audit.json'
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'{len(result["level_one_links"])} gear links; {len(result["gear_named_buff_rows"])} gear-named buff rows; unresolved effects excluded.')
