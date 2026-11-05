"""Audit base-hero override clip durations without publishing raw Unity assets.

Requires the existing local UnityPy dependency; installed assets are read-only.
"""
import sys,json,hashlib,struct,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'work/tools/unitypy'))
import UnityPy
from extract_hero_images import asset_bundle_ids,bundle_hashes,text
from export_client_asset import locate_bundle
parser=argparse.ArgumentParser(description=__doc__)
for name in ['packaged-assets','downloaded-assets','asset-index','bundle-list','upgrade-data','hero-data','output']:
 parser.add_argument('--'+name,type=Path,required=True)
parser.add_argument('--asset-build',help='Explicit cache revision when newer than the installed executable')
args=parser.parse_args();pkg=args.packaged_assets;dl=args.downloaded_assets
roster=json.loads(args.hero_data.read_text(encoding='utf-8'))
progression=json.loads(args.upgrade_data.read_text(encoding='utf-8'))
index=args.asset_index;lst=args.bundle_list
if not index.name.endswith('_'+(args.asset_build or progression['client_build'])+'.json'):
 raise ValueError('Asset index must identify the progression native build')
am=asset_bundle_ids(index,{'model_survivor_'+h['asset_slug'] for h in roster})
if len(am)!=len(roster):raise ValueError('Missing hero model asset indices')
raw=lst.read_bytes();n=struct.unpack_from('<I',raw)[0];pos=4;bundles={};templates=set()
for _ in range(n):
 ver,bid=struct.unpack_from('<II',raw,pos);pos+=8;name,pos=text(raw,pos);digest,pos=text(raw,pos);pos+=16;vfs,pos=text(raw,pos)
 if name.endswith('animation@exploration@template'):templates.add(bid)
 if bid in am.values() or ('@exploration@character@' in name and any(h['asset_slug'] in name for h in roster) and 'timeline' not in name) or bid in templates:bundles[bid]=(name,digest)
objects={};models={};provenance={}
for bid,(name,digest) in bundles.items():
 try:raw,src=locate_bundle([dl,pkg],'G',digest)
 except FileNotFoundError:print('MISSING',bid,name);continue
 env=UnityPy.load(raw[raw.find(b'UnityFS'):]);provenance[bid]={'name':name,'digest':digest,'sha256':hashlib.sha256(raw).hexdigest()}
 for obj in env.objects:
  if obj.type.name not in ['AnimationClip','AnimatorOverrideController','Animator']:continue
  t=obj.read_typetree();file=obj.assets_file
  key=(file.name,obj.path_id)
  if key in objects and objects[key]['tree'] != t:raise ValueError('Conflicting animation object: '+str(key))
  objects[key]={'type':obj.type.name,'tree':t,'external':[e.path.split('/')[-1] for e in file.externals],'bundle_id':bid,'file_name':file.name}
  if bid in am.values() and obj.type.name=='Animator':
   go=file.objects[t['m_GameObject']['m_PathID']].read_typetree()
   objects[key]['game_object_name']=go['m_Name']
   models.setdefault(bid,[]).append(key)
 print('READ',bid,flush=True)
def resolve(obj,ptr):
 file=obj['external'][ptr['m_FileID']-1] if ptr['m_FileID'] else obj['file_name']
 return objects.get((file,ptr['m_PathID']))
heroes={}
for hero in roster:
 slug=hero['asset_slug'];bid=am['model_survivor_'+slug];animators=models.get(bid,[])
 if len(animators)>1:animators=[k for k in animators if 'survivor_'+slug in objects[k]['game_object_name'].lower()]
 if len(animators)!=1:raise ValueError('Ambiguous base model animator: '+slug)
 anim=objects[animators[0]];ctl=resolve(anim,anim['tree']['m_Controller'])
 if not ctl or ctl['type']!='AnimatorOverrideController':raise ValueError('Missing base model override controller: '+slug)
 takes={}
 for pair in ctl['tree']['m_Clips']:
  original=resolve(ctl,pair['m_OriginalClip']);override=resolve(ctl,pair['m_OverrideClip'])
  if not original or not override:continue
  clip=override['tree'];muscle=clip.get('m_MuscleClip',{})
  if 'm_StopTime' not in muscle or 'm_StartTime' not in muscle:continue
  name=original['tree']['m_Name'];duration=muscle['m_StopTime']-muscle['m_StartTime']
  if name in takes:raise ValueError('Ambiguous take '+slug+' '+name)
  takes[name]={'clip_name':clip['m_Name'],'duration_seconds':duration,'bundle_id':override['bundle_id']}
 heroes[slug]={'model_asset':'model_survivor_'+slug,'controller':ctl['tree']['m_Name'],'model_bundle_id':bid,'takes':takes}
 if 'attack' not in takes:raise ValueError('Missing bound attack clip: '+slug)
 print('MAPPED',slug,{k:round(v['duration_seconds'],4) for k,v in takes.items() if k in ['attack','attack02','skill']},flush=True)
used={h['model_bundle_id'] for h in heroes.values()}|{v['bundle_id'] for h in heroes.values() for v in h['takes'].values()}|templates
result={'version':1,'client_build':progression['client_build'],'scope':'Base model override-clip durations at unit speed; no battle scheduling or live-patch verification.','provenance':{'config_pack_sha256':progression['provenance']['config_pack_sha256'],'manifest_sha256':progression['provenance']['manifest_sha256'],'asset_build':args.asset_build or progression['client_build'],'asset_index_sha256':hashlib.sha256(index.read_bytes()).hexdigest(),'bundle_list_sha256':hashlib.sha256(lst.read_bytes()).hexdigest(),'bundles':{str(k):v for k,v in provenance.items() if k in used}},'heroes':heroes}
args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('Mapped',len(heroes),'heroes')
