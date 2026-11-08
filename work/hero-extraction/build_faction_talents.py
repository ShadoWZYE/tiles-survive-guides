"""Normalize manifest-verified faction talents; never infer purchased nodes from stars."""
import hashlib
import json
import re
from pathlib import Path
from decode_cfg import decode_table
from decode_language_pack import decode_language_pack, DEFAULT_LANGUAGE_PACK


def export(source, language=DEFAULT_LANGUAGE_PACK):
    names = ['hero_faction_talent', 'hero_faction_talent_branch', 'benefits', 'benefit_calc']
    tables = {n: decode_table(source / (n + '.cfg'))['rows'] for n in names}
    lang = decode_language_pack(language)
    benefits = {r['InternalId']: r['Id'] for r in tables['benefits']}
    for i, stat in enumerate(['attack', 'defense', 'health']):
        assert benefits[301828+i] == 'prop_all_hero_' + stat + '_value'
        calc = next(r for r in tables['benefit_calc'] if r['Id'] == 'calc_prop_hero_' + stat)
        assert 301828+i in calc['ValueParam']
    result = {}
    for branch in tables['hero_faction_talent_branch']:
        nodes = {}
        for row in tables['hero_faction_talent']:
            if row['BranchId'] != branch['InternalId']:
                continue
            node = nodes.setdefault(str(row['SerialNumber']), {
                'name': lang.get(row['NameDescription'], row['NameDescription']),
                'icon_asset': row['Icon'], 'type': row['TalentType'], 'levels': []})
            description = lang.get(row['AttributeDescription'], row['AttributeDescription'])
            if row['TalentType'] != 3 and '{' not in description:
                description += ' +' + ' / '.join(row['AttributeDescriptionParam'])
            for i, value in enumerate(row['AttributeDescriptionParam']):
                description = description.replace('{' + str(i) + '}', value)
            effects, excluded = [], []
            # These three additive values are already traced through benefit_calc.
            # Type 3 has placeholder/conflicting Benefit and description data: do not score it.
            for value in row['Benefit']:
                bid = value['benefit_id']
                if row['TalentType'] != 3 and 301828 <= bid <= 301830:
                    effects.append({'scope': 'all', 'scene': 'all', 'stat': bid - 301828,
                                    'value': value['benefit_value']})
                else:
                    excluded.append(benefits.get(bid, str(bid)))
            node['levels'].append({
                'id': row['InternalId'], 'level': row['TalentLevel'],
                'cost': row['RequiredQuantity'], 'requires': row['PreliminaryId'],
                'effects': effects, 'unmodeled': excluded, 'linked_skill': bool(row['SkillId']),
                'description': re.sub(r'<[^>]+>', '', description)})
        for node in nodes.values():
            node['levels'].sort(key=lambda r: r['level'])
        result[str(branch['InternalId'])] = {
            'name': {1: 'Mountain / Stalwart', 2: 'Wasteland / Rover', 3: 'Sky / Aeronaut'}[branch['Faction']],
            'faction': branch['Faction'], 'enabled': bool(branch['Enabled']), 'nodes': nodes}
    return result, {n: hashlib.sha256((source / (n + '.cfg')).read_bytes()).hexdigest() for n in names}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--context', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.context.read_text(encoding='utf-8'))
    data['faction_talents'], hashes = export(args.source)
    data['version'] = 7
    data['faction_talent_source_hashes'] = hashes
    data['faction_talent_audited_date'] = '2026-11-08'
    args.context.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
