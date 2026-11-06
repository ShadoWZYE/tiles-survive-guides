"""Record provenance of the manually inspected static Raid damage helper.

Hash-gated private artifacts come from audit_native_combat.py. No executable is
loaded. This does not validate the field/Lite engine bridge or active patches.
"""
import argparse
import bisect
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMAGE_SHA = '5afef9adf2a4dc85b40adc702149a45bf10728ef2c9de1895f3b648a9128b14d'
INDEX_SHA = 'ee94b9e060a9d0db87e2787b52a339dcf7555e3f65933d21a5ad9e583be13af4'


def audit(image, index_bytes, prior):
    if hashlib.sha256(image).hexdigest() != IMAGE_SHA or hashlib.sha256(index_bytes).hexdigest() != INDEX_SHA:
        raise ValueError('Unverified private native artifacts; do not reuse the mapping on a different build.')
    if prior['client_build'] != '2.6.400.304':
        raise ValueError('Prior native audit build mismatch.')
    methods = json.loads(index_bytes)
    addresses = sorted({m['rva'] for m in methods})
    selected = []
    for name in ['CalSkillBaseDamage', 'CalSkillDamage', 'CalPowerFixFactorByRatio', 'CalPowerRatio']:
        row = next(m for m in methods if m['type'] == 'SkillDamageCalSystem' and m['name'] == name)
        end = addresses[bisect.bisect_right(addresses, row['rva'])]
        selected.append({**row, 'byte_count': end-row['rva'],
                         'code_sha256': hashlib.sha256(image[row['rva']:end]).hexdigest()})
    return {
        'client_build': prior['client_build'], 'binary_sha256': prior['binary_sha256'],
        'metadata_sha256': prior['metadata_sha256'], 'private_image_sha256': IMAGE_SHA,
        'private_method_index_sha256': INDEX_SHA, 'methods': selected,
        'manually_traced_helper': {
            'method': 'SkillDamageCalSystem.CalSkillBaseDamage',
            'formula': 'ATK^2 / (ATK + defense_parameter * max(0, DEF-flat_penetration) * max(0, 1-percent_penetration)) * coefficient + flat_damage + property_source + custom_formula + external_additive',
            'defense_parameter_config_key': 'function_dmg_defparam', 'configured_value': 2.5,
            'scope': 'Current static base helper only. The caller adds more modifiers. Not proved to govern field-fiend damage.',
            'implementation': 'work/fiend-lab/raid_damage_kernel.py',
        },
        'field_fiend_bridge_verified': False,
        'power_ratio_applicability_to_fiends_verified': False,
        'not_used_as_damage_formulas': ['pve_formula rows explicitly named test/damage_test/heal_test/buff_test'],
        'unverified': ['Active ILFix patches', 'Field/Lite Type 11100 execution and engine selection',
                       'Final field benefit stacking and power scaling', 'Targeting and troop-casualty mapping'],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', type=Path, required=True)
    p.add_argument('--index', type=Path, required=True)
    p.add_argument('--output', type=Path, default=ROOT/'outputs/fiend-lab/Native-Bridge-Audit.json')
    args = p.parse_args()
    result = audit(args.image.read_bytes(), args.index.read_bytes(),
                   json.loads((ROOT/'outputs/hero-report/Hero-Native-Combat-Audit.json').read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print('Recorded four native method fingerprints; field-fiend bridge remains unverified.')


if __name__ == '__main__':
    main()
