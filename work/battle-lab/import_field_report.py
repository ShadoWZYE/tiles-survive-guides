"""Normalize explicitly selected report fields offline; never contacts the game.

Provide JSON pointers to the selected owner's totals and, optionally, round states.
Unknown IDs and malformed values fail. Player IDs, names and unrelated fields are
not copied. Raw input and normalized output should stay outside public artifacts.
"""
import argparse,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def pointer(document,path):
    if path=='':return document
    if not path.startswith('/'):raise ValueError('Use an explicit JSON pointer')
    current=document
    for part in path[1:].split('/'):
        part=part.replace('~1','/').replace('~0','~')
        current=current[int(part)] if isinstance(current,list) else current[part]
    return current

def number(value,label,integer=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
        raise ValueError('Invalid '+label)
    if integer and (not isinstance(value,int) or value>2**63-1):raise ValueError('Expected integer '+label)
    return value

def normalize(owner,roster,rounds=None):
    if not isinstance(owner,dict) or not isinstance(owner.get('survivor_damage_and_withstand'),list):
        raise ValueError('Select an owner containing survivor_damage_and_withstand')
    identities={h['hero_id']:h['asset_slug'] for h in roster};heroes=[];seen=set()
    rows=owner['survivor_damage_and_withstand']
    if not 1<=len(rows)<=5:raise ValueError('Select one army/round with one to five heroes')
    for row in rows:
        identifier=number(row['i_survivor'],'hero identity',True)
        if identifier not in identities or identifier in seen:raise ValueError('Unknown or duplicated hero identity')
        seen.add(identifier);heroes.append({'hero':identities[identifier],'damage':number(row['damage'],'damage'),
             'healing':number(row['cure'],'cure'),'damage_taken':number(row['withstand'],'withstand')})
    states=[]
    if rounds is not None:
        if not isinstance(rounds,list) or not rounds:raise ValueError('Select the nested round-state list')
        for index,round_data in enumerate(rounds):
            if not isinstance(round_data,list):raise ValueError('Unsupported round-state layout')
            snapshots=[]
            for inner_index,snapshot in enumerate(round_data):
                if not isinstance(snapshot,list):raise ValueError('Unsupported snapshot layout')
                positions=set();units=[]
                for unit in snapshot:
                    pos=number(unit['pos'],'position',True)
                    if pos in positions:raise ValueError('Duplicated snapshot position')
                    positions.add(pos);units.append({key:number(unit[key],key,True) for key in ['pos','hp','start_hp','heal_hp']})
                snapshots.append({'inner_index':inner_index,'units':units})
            states.append({'outer_index':index,'snapshots':snapshots})
    return {'schema':1,'source_kind':'provided_field_report_fields','source_authenticity_verified':False,
        'heroes':heroes,'round_states':states,'position_owner_mapping':'not supplied or inferred','time_units':'unresolved; array index is not seconds',
        'hp_units':'raw supplied values; not assumed hero-only HP','per_source_damage_identified':False,
        'simulation_inputs_complete':False,'winner_prediction':None,'independent_damage_accuracy':None}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--owner-pointer',required=True);parser.add_argument('--rounds-pointer')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.input.resolve()==args.output.resolve():raise ValueError('Output must not overwrite input')
    raw=args.input.read_bytes()
    def reject(value):raise ValueError('Non-finite JSON number '+value)
    document=json.loads(raw,parse_constant=reject)
    roster=json.loads((ROOT/'outputs/hero-report/TilesSurvive-Hero-Data.json').read_text(encoding='utf-8'))
    result=normalize(pointer(document,args.owner_pointer),roster,pointer(document,args.rounds_pointer) if args.rounds_pointer is not None else None)
    result['source_sha256']=hashlib.sha256(raw).hexdigest();args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    snapshots=sum(len(row['snapshots']) for row in result['round_states'])
    print(f"Imported {len(result['heroes'])} owner totals and {snapshots} snapshots; no prediction inferred.")

if __name__=='__main__':main()
