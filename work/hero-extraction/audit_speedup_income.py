"""Selected construction-usable rewards; manifest verified, no population-average claim."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from decode_cfg import decode_table
from extract_config_pack import read_entries

ROOT = Path(__file__).resolve().parents[2]
GAME = Path('C:/Program Files (x86)/FunPlus/Tiles Survive/GameData/GameAssets')

def audit():
    manifest = json.loads((GAME/'BinaryConfig/BinVersionList_Realtime.json').read_bytes())
    pack = (GAME/'BinaryConfigPack.ss').read_bytes()
    entries = {e.name:e for e in read_entries(pack)}
    hashes = {}
    def table(name):
        loose = GAME/'BinaryConfig'/f'{name}.bin'
        e = entries.get(name)
        raw = loose.read_bytes() if loose.exists() else pack[e.offset:e.offset+e.size]
        assert hashlib.md5(raw).hexdigest() == manifest[name], name
        hashes[name] = hashlib.sha256(raw).hexdigest()
        p = ROOT/'tmp/speedup-income-audit'/f'{name}.cfg'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        return decode_table(p)['rows']
    items = {r['InternalId']:r for r in table('itemlist')}
    groups = {r['InternalId']:r for r in table('drop_group')}
    drops = defaultdict(list)
    for r in table('drop_main'): drops[r['DropGroup']].append(r)
    def seconds(i):
        r = items.get(int(i), {})
        return r.get('Value', 0) if r.get('Type') in ('building_speedup','speedup') else 0
    def reward(values):
        if isinstance(values,dict): return sum(seconds(i)*n for i,n in values.items())
        return sum(seconds(r['i_id'])*r['num'] for r in values)
    def drop(g):
        # EV assumes Chance / 10000 and uniform integer counts within Min/Max.
        return sum(seconds(r['ItemId'])*r['Chance']/10000*(r['MinValue']+r['MaxValue'])/2 for r in drops[g] if r['ItemId'] is not None)
    daily = defaultdict(float)
    for r in table('daily_reward'): daily[r['GroupId']] += reward(r['ItemReward'])
    assert set(daily.values()) == {900}
    duel = sum(reward(r['IndividualScoreBoxReward']) for r in table('activity_alliance_1v1_duel_box'))
    assert duel == 3000
    rally = [r for r in table('gve_new_reward') if r['Id'] in ('gve_boss_new_period_10_1','gve_boss_new_period_10_2')]
    rally_rewards = [drop(next(iter(r['DamageReward'].values()))) for r in rally]
    assert rally_rewards == [3600,3600]
    gift = next(g for g,r in groups.items() if r['Id']==items[202003]['Para1'])
    gifts = {r['Id']:drop(g) for g,r in groups.items() if r['Id'].startswith('drop_group_item_alliance_package_chest_')}
    assert len(gifts) == 5
    intel = {r['Id']:drop(g) for g,r in groups.items() if r['Id'].startswith('intel_daily_dig_drop_')}
    result = {'date':'2026-10-11','table_sha256':hashes,'daily_activity_seconds':900,
        'duel_full_nine_chests_seconds_per_eligible_day':duel,
        'fiend_level10_period_branch_seconds_per_eligible_personal_claim':3600,
        'fiend_branch_reward_rows':[r['Id'] for r in rally],
        'alliance_rally_chest_expected_seconds':drop(gift),
        'alliance_package_expected_seconds':gifts,'intel_dig_expected_seconds':intel,
        'random_reward_assumption':'Chance/10000; uniform MinValue..MaxValue; expectations, not guarantees',
        'scenario':'3-5 eligible level-10 personal fiend claims; all daily activity; 20-60 alliance rally chests; 0-1 full duel ladder/day. Claim counts are planning assumptions, not observed F2P averages.',
        'core_hours_per_day':[(900+3*3600+20*drop(gift))/3600,(900+5*3600+60*drop(gift)+duel)/3600],
        'not_in_core':'Intel dig tables have not been linked to this account active reward path; paid-package gifts, other events and aid crates are separate additions.'}
    (ROOT/'outputs/Speedup-Income-Audit-2026-10-11.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__ == '__main__': print(json.dumps(audit(),indent=2))
