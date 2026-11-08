"""Read cached InjectFix containers without loading assemblies or executing code.

Layout reference (pinned): Tencent/InjectFix FileVirtualMachineBuilder.cs,
commit 5ba42eb8f63fe37134a3c78690f97d8425e13588. Opcode meanings are not decoded.
Unknown layouts, interface slots, invalid indexes and trailing data fail closed.
"""
import argparse,hashlib,json,struct
from pathlib import Path

MAGIC=bytes.fromhex('3d575de849000000')
WATCHED={'SkillBase','SkillComponent','SkillRelease','ConditionCheckerManager',
 'ConditionSkillFinishChecker','RaidBuffDelayEffect','RaidEffectSystem',
 'RaidGameActionProjectile','RaidGameProjectileConfig','RaidGameProjectileLine',
 'RaidSESummonObject','SummonPropertyComponent','SkillDamageCalSystem',
 'RaidFightStatisticsMgr','HeroPropertyComponent','SoldierPropertyComponent',
 'SurvivorData','RaidEntityManager','RaidUtils'}

class Reader:
    def __init__(self,data):self.data=data;self.position=0
    def read(self,size):
        if size<0 or self.position+size>len(self.data):raise ValueError('Truncated hotfix container')
        value=self.data[self.position:self.position+size];self.position+=size;return value
    def integer(self):return struct.unpack('<i',self.read(4))[0]
    def count(self):
        value=self.integer()
        if not 0<=value<=100000:raise ValueError('Invalid container count')
        return value
    def boolean(self):
        value=self.read(1)[0]
        if value not in (0,1):raise ValueError('Invalid boolean')
        return bool(value)
    def string(self):
        length=0
        for shift in range(0,35,7):
            value=self.read(1)[0];length|=(value&127)<<shift
            if not value&128:return self.read(length).decode('utf-8')
        raise ValueError('Invalid string length')

def parse(data):
    if len(data)>16*1024*1024:raise ValueError('Container exceeds audit size bound')
    reader=Reader(data)
    if reader.read(8)!=MAGIC:raise ValueError('Unknown instruction format')
    bridge=reader.string()
    if not bridge.startswith('IFix.ILFixInterfaceBridge,'):raise ValueError('Unknown bridge layout')
    types=[reader.string() for _ in range(reader.count())]
    def type_name():
        index=reader.integer()
        if not 0<=index<len(types):raise ValueError('Invalid type index')
        return types[index]
    def method():
        generic=reader.boolean();owner=type_name();name=reader.string()
        generic_args=[type_name() for _ in range(reader.count())] if generic else []
        arguments=[(reader.string() if reader.boolean() else type_name()) if generic else type_name() for _ in range(reader.count())]
        return {'type':owner.split(',')[0],'name':name,'arguments':arguments,'generic_arguments':generic_args}
    bodies=[]
    for _ in range(reader.count()):
        count=reader.count();code=reader.read(count*8)
        bodies.append({'instruction_count':count,'body_sha256':hashlib.sha256(code).hexdigest()})
        reader.read(reader.count()*24)  # Six integer fields per exception handler.
    extern=[method() for _ in range(reader.count())]
    for _ in range(reader.count()):reader.string()
    for _ in range(reader.count()):
        new=reader.boolean();type_name();reader.string()
        if new:type_name();reader.integer()
    for _ in range(reader.count()):type_name();reader.integer()
    for _ in range(reader.count()):
        reader.read(reader.count()*4);reader.integer();reader.count()
        if reader.count():raise ValueError('Interface slots require runtime metadata; unsupported')
        reader.read(reader.count()*4)
    reader.string();reader.string()  # Wrapper and assembly identities, never activated.
    replacements=[]
    for _ in range(reader.count()):
        identity=method();index=reader.integer()
        if not 0<=index<len(bodies):raise ValueError('Invalid replacement body index')
        replacements.append({**identity,**bodies[index]})
    for _ in range(reader.count()):reader.string()
    if reader.position!=len(data):raise ValueError('Unconsumed container data')
    return {'type_count':len(types),'external_method_count':len(extern),'body_count':len(bodies),'replacements':replacements}

def audit(directory):
    files=sorted(p for p in directory.iterdir() if p.is_file())
    if not files:raise ValueError('No cached patches')
    result=[]
    for path in files:
        raw=path.read_bytes();parsed=parse(raw)
        relevant=[r for r in parsed['replacements'] if r['type'].rsplit('.',1)[-1] in WATCHED]
        result.append({'file':path.name,'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'fully_consumed':True,'replacement_count':len(parsed['replacements']),'watched_replacements':relevant})
    return {'schema':1,'scope':'Cached containers only; no process attachment, assembly loading or patch execution.',
        'format_reference':'https://github.com/Tencent/InjectFix/blob/5ba42eb8f63fe37134a3c78690f97d8425e13588/Source/VSProj/Src/Builder/FileVirtualMachineBuilder.cs',
        'instruction_format_magic':MAGIC.hex(),'watched_types':sorted(WATCHED),'files':result,
        'direct_watched_replacements':sum(len(f['watched_replacements']) for f in result),
        'live_loaded_patch_verified':False,
        'limits':['Absence means no direct watched-type replacement in these files, not proof of all transitive behavior.',
                  'Runtime load selection, future/downloaded patches and original server code are not inspected.',
                  'Bodies are structurally skipped and hashed; opcode meanings and replacement execution are not simulated.']}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=audit(args.directory)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f"Parsed {len(result['files'])} cached patches to EOF; {result['direct_watched_replacements']} direct watched-type replacements.")
