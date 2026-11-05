"""Export current survivor release timelines privately from matched asset indices."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from decode_cfg import decode_table
from extract_hero_images import asset_bundle_ids, bundle_hashes
from export_client_asset import locate_bundle

ROOT = Path(__file__).resolve().parents[2]

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ['releases', 'asset-index', 'bundle-list', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--root', type=Path, action='append', required=True)
    a = p.parse_args()
    wanted = {r['SkillEvent'] for r in decode_table(a.releases)['rows'] if r['SkillEvent'] and 'survivor_' in r['SkillEvent']}
    indexed = asset_bundle_ids(a.asset_index, wanted)
    hashes = bundle_hashes(a.bundle_list, set(indexed.values()))
    sys.path.insert(0, str(ROOT / 'work/tools/unitypy'))
    import UnityPy
    a.output.mkdir(parents=True, exist_ok=True)
    found = {}
    for digest in sorted(set(hashes.values())):
        raw, _ = locate_bundle(a.root, 'G', digest)
        start = raw.find(b'UnityFS')
        if start < 0: raise ValueError('Bundle is not UnityFS')
        for obj in UnityPy.load(raw[start:]).objects:
            if obj.type.name != 'TextAsset': continue
            value = obj.read()
            if value.m_Name not in wanted: continue
            script = value.m_Script
            if isinstance(script, bytes): script = script.decode('utf-8')
            json.loads(script)
            if value.m_Name in found and found[value.m_Name] != script: raise ValueError('Conflicting timeline')
            found[value.m_Name] = script
    for name, script in found.items():
        (a.output / (name + '-TextAsset.json')).write_text(json.dumps({'m_Name': name, 'm_Script': script}), encoding='utf-8')
    report = {'asset_index_sha256': hashlib.sha256(a.asset_index.read_bytes()).hexdigest(), 'bundle_list_sha256': hashlib.sha256(a.bundle_list.read_bytes()).hexdigest(), 'bundles': sorted(set(hashes.values())), 'exported': len(found), 'missing': sorted(wanted-found.keys())}
    (a.output / 'provenance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'exported':len(found),'unavailable':len(report['missing'])}))
