"""Hash-gated static audit of selected current combat methods. No DLL loading.

Requires capstone for instruction fingerprints. Raw code/metadata and optional
disassembly stay in the private output directory; public output contains hashes,
method identities, field offsets and scope limitations only.
"""
import argparse
import bisect
import hashlib
import json
from pathlib import Path
import struct
from probe_metadata_patterns import infer_xor_mask
from unpack_client_lzma import unpack,LATEST_SHA256 as CURRENT_SHA256

METADATA_SHA256='9a5f4a19ce4f3f9f8c60e8402a253da9feddc901e01f27b4af654e93fc92be26'
DECODED_METADATA_SHA256='1af8d51d9fbda243f06033505e98dd1edba6ac4070b57584fb5c6d7aa01c81cb'
STRING_BASE=2346196
TYPE_BASE=43922704
METHOD_BASE=13870044
FIELD_BASE=36125568
FIELD_POINTERS=126304256
METHOD_POINTERS=0x7966830
TYPE_COUNT=24983
METHOD_COUNT=170826
BASE=0x180000000
SELECTED={
 'SkillBase':['OnUseSkill','Update','CanUseSkill','CanInterruptSkill','InterruptSkill','ReleaseFinished','IsSkillEnd'],
 'SkillComponent':['GetAIUsableSkill','UseSkill','SortSkillPriority','IsCurSkillEnd'],
 'SkillRelease':['OnUseSkill','Update','OnReleaseGoRunning','PlayReleaseClip','GetCurGameSkillSpeed'],
 'RaidModelActor':['BuildAnimatorOverrideControllerTimeData','GetGameSkillLength'],
 'RaidBuffBase':['RefreshBuff','OnUpdate','RemoveEffect'],
 'RaidBuffComponent':['AddBuff'],
 'RaidBuffDotEffect':['AddEffect','OnUpdate','OnEffectTriggered'],
 'RaidEffectSystem':['ProcessEffectSummon','ProcessEffectRecoverHp','ProcessEffectDamage'],
 'SummonPropertyComponent':['Initialize'],
 'SkillDamageCalSystem':['CalSkillHeal','CalPropertySourceValue'],
 'RaidBuffPropertyModify':['Init'],
 'RaidPropertyUtils':['CalculateFinalPropertyValue'],
 'ConditionSkillFinishChecker':['OnTargetEntitySkillFinish'],
 'ConditionRandomProbabilityChecker':['IsConditionSatisfied'],
 'RaidBuffDelayEffect':['.ctor','AddEffect','OnUpdate','OnEffectTriggered'],
 'RBT_UseSkill':['OnUpdate'],
}


def decode_metadata(raw):
    if hashlib.sha256(raw).hexdigest()!=METADATA_SHA256:raise ValueError('Unverified metadata hash')
    period=1152;start=8388608//period*period
    mask=infer_xor_mask(raw[start:start+1048576],period,ord('e'))
    decoded=bytearray(len(raw))
    for phase,key in enumerate(mask):
        decoded[phase::period]=raw[phase::period].translate(bytes(v^key for v in range(256)))
    if hashlib.sha256(decoded).hexdigest()!=DECODED_METADATA_SHA256:raise ValueError('Selected metadata decoding fingerprint mismatch')
    return bytes(decoded)


def metadata_index(metadata,image):
    def string(index):
        pos=STRING_BASE+index
        if not STRING_BASE<=pos<len(metadata):raise ValueError('String reference outside metadata')
        end=metadata.find(b'\0',pos,pos+4096)
        if end<0:raise ValueError('Unterminated metadata name')
        return metadata[pos:end].decode('utf-8')
    types={};methods=[]
    for index in range(TYPE_COUNT):
        off=TYPE_BASE+index*88;name=string(struct.unpack_from('<I',metadata,off)[0])
        method_start=struct.unpack_from('<i',metadata,off+36)[0]
        method_count,_,field_count=struct.unpack_from('<HHH',metadata,off+64)
        fields=[]
        if name in SELECTED:
            field_start=struct.unpack_from('<i',metadata,off+32)[0]
            pointer=struct.unpack_from('<Q',image,FIELD_POINTERS+index*8)[0]-BASE
            for j in range(field_count):
                n=string(struct.unpack_from('<I',metadata,FIELD_BASE+(field_start+j)*12)[0])
                fields.append([n,struct.unpack_from('<i',image,pointer+j*4)[0]])
            types[name]={'index':index,'namespace':string(struct.unpack_from('<I',metadata,off+4)[0]),'fields':fields}
        if method_count and method_start<0:raise ValueError('Invalid method range')
        for j in range(method_count):
            mo=METHOD_BASE+(method_start+j)*36
            n,owner=struct.unpack_from('<II',metadata,mo);token=struct.unpack_from('<I',metadata,mo+24)[0]
            if owner!=index:raise ValueError('Method owner mismatch')
            ordinal=(token&0xffffff)-1
            if not 0<=ordinal<METHOD_COUNT:raise ValueError('Method token outside module')
            rva=struct.unpack_from('<Q',image,METHOD_POINTERS+ordinal*8)[0]-BASE
            if 0<rva<len(image):methods.append({'type':name,'name':string(n),'rva':rva,'token':hex(token),
                'parameter_count':struct.unpack_from('<H',metadata,mo+34)[0]})
    required={(t,n) for t,names in SELECTED.items() for n in names}
    if required-{(r['type'],r['name']) for r in methods}:raise ValueError('Missing selected current methods')
    expected={'skillCdTime':100,'skillRemainCdTime':104,'_curRunningReleaseIndex':96}
    if any(dict(types['SkillBase']['fields']).get(k)!=v for k,v in expected.items()):raise ValueError('Unexpected skill ABI')
    return types,methods


def fingerprint(image,rva,end,patch_targets=()):
    import capstone
    from capstone import x86_const as x
    md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
    instructions=list(md.disasm(bytes(image[rva:end]),rva))
    while instructions and instructions[-1].mnemonic in ('int3','nop'):instructions.pop()
    positions={i.address:j for j,i in enumerate(instructions)}
    patch_ids={}
    for j,ins in enumerate(instructions):
        if ins.mnemonic!='call' or not ins.operands or ins.operands[0].type!=x.X86_OP_IMM or ins.operands[0].imm not in patch_targets:continue
        for k in range(j-1,max(-1,j-12),-1):
            prior=instructions[k]
            if prior.group(capstone.CS_GRP_CALL) or prior.group(capstone.CS_GRP_JUMP):break
            _,writes=prior.regs_access()
            if any(prior.reg_name(r) in ('ecx','rcx','cx','cl','ch') for r in writes):
                if prior.mnemonic=='mov' and len(prior.operands)==2 and prior.operands[0].type==x.X86_OP_REG and prior.reg_name(prior.operands[0].reg)=='ecx' and prior.operands[1].type==x.X86_OP_IMM:
                    patch_ids[k]=prior.operands[1].imm
                break
    normalized=[];base_path=[];text=[]
    for ins in instructions:
        operands=[]
        branch=ins.group(capstone.CS_GRP_CALL) or ins.group(capstone.CS_GRP_JUMP)
        for op in ins.operands:
            if op.type==x.X86_OP_REG:operands.append(['reg',ins.reg_name(op.reg)])
            elif op.type==x.X86_OP_IMM:operands.append(['target',positions.get(op.imm,'external')] if branch else ['imm',op.imm])
            elif op.type==x.X86_OP_MEM:
                operands.append(['mem',op.size,ins.reg_name(op.mem.base),ins.reg_name(op.mem.index),op.mem.scale,
                    'relocated' if op.mem.base==x.X86_REG_RIP else op.mem.disp])
        normalized.append([ins.mnemonic,operands])
        base_path.append([ins.mnemonic,[['patch_id'] if j==1 and len(normalized)-1 in patch_ids else op for j,op in enumerate(operands)]])
        text.append(f'{ins.address:X}: {ins.mnemonic} {ins.op_str}')
    return {'instruction_count':len(instructions),'code_sha256':hashlib.sha256(image[rva:end]).hexdigest(),
        'normalized_sha256':hashlib.sha256(json.dumps(normalized,separators=(',',':')).encode()).hexdigest(),
        'base_path_sha256':hashlib.sha256(json.dumps(base_path,separators=(',',':')).encode()).hexdigest(),
        'patch_dispatch_ids':sorted(set(patch_ids.values()))},text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--private-output',type=Path,required=True)
    p.add_argument('--prior-report',type=Path,help='Previously reviewed static audit for structural continuity checks')
    p.add_argument('--baseline-image',type=Path);p.add_argument('--baseline-index',type=Path)
    args=p.parse_args();raw=args.binary.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=CURRENT_SHA256:raise ValueError('Unverified native combat profile')
    image,streams=unpack(raw);metadata=decode_metadata(args.metadata.read_bytes());types,methods=metadata_index(metadata,image)
    addresses=sorted({r['rva'] for r in methods});rows=[];private=[]
    patch_targets={r['rva'] for r in methods if r['type']=='WrappersManagerImpl' and r['name'] in ('IsPatched','GetPatch')}
    for row in methods:
        if row['type'] not in SELECTED or row['name'] not in SELECTED[row['type']]:continue
        i=bisect.bisect_right(addresses,row['rva']);end=addresses[i] if i<len(addresses) else row['rva']+24000
        if end-row['rva']>32768:raise ValueError('Selected method exceeds static audit bound')
        info,lines=fingerprint(image,row['rva'],end,patch_targets);rows.append({**row,'byte_count':end-row['rva'],**info})
        private.extend([row['type']+'.'+row['name'],*lines])
    args.private_output.mkdir(parents=True,exist_ok=True)
    (args.private_output/'native-rva-image.bin').write_bytes(image)
    (args.private_output/'method-index.json').write_text(json.dumps(methods),encoding='utf-8')
    (args.private_output/'selected-methods.txt').write_text('\n'.join(private),encoding='utf-8')
    result={'version':2,'client_build':'2.6.400.304','binary_sha256':CURRENT_SHA256,'metadata_sha256':METADATA_SHA256,
        'decoded_metadata_sha256':DECODED_METADATA_SHA256,'decoded_streams':streams,'selected_types':types,'methods':rows,
        'verified_claims':{
            'delay_buff_type':16,'delay_buff_fires_once':True,'delay_buff_delay_param':'Param1[0] / 1000, clamped to zero',
            'finish_condition_type':19,'finish_condition_ignores_interrupted':True,
            'finish_condition_param_int_selects_skill_type':True,'hero_basic_interruptible':True,
            'raw_heal_formula':'(caster_ATK * Param2/1000 + Param3/1000 + property_source_terms + custom_formula) before outgoing, incoming and contextual modifiers',
            'property_source_owners':{'0':'caster','1':'recipient'},
            'hero_active_and_passive_interruptible_via_normal_path':False},
        'scope':'Selected current method identities, fields and manually traced static base paths. No client loading, process attachment, live patches or complete combat-engine verification. Normalization omits branch addresses and RIP displacements; equal fingerprints alone do not validate referenced data. Base-path fingerprints additionally mask only immediate patch IDs flowing into identified IsPatched/GetPatch calls; immediate gameplay constants and memory operand widths remain significant. RIP-addressed constants require separate comparison.'}
    if bool(args.baseline_image)!=bool(args.baseline_index):raise ValueError('Supply both baseline artifacts')
    if args.baseline_image:
        old_image=args.baseline_image.read_bytes();old_index=args.baseline_index.read_bytes()
        expected_image='d97fd289b235193f32f16e44fe72b91b1b39fe23a897da16b31994048478cb76'
        expected_index='d580611e36c36176dd5fa83b15ebf2ca399a18e540db63a2025cd61fea26887e'
        if hashlib.sha256(old_image).hexdigest()!=expected_image or hashlib.sha256(old_index).hexdigest()!=expected_index:raise ValueError('Unverified baseline artifacts')
        old_methods=[r for t in json.loads(old_index) if t['index']<24804 for r in t['methods'] if 0<r['rva']<len(old_image)]
        old_addresses=sorted({r['rva'] for r in old_methods})
        old_patches={r['rva'] for r in old_methods if r['type']=='WrappersManagerImpl' and r['name'] in ('IsPatched','GetPatch')}
        comparisons=[]
        for row in rows:
            candidates=[]
            for prior in old_methods:
                if (prior['type'],prior['name'])!=(row['type'],row['name']):continue
                idx=bisect.bisect_right(old_addresses,prior['rva'])
                if idx==len(old_addresses) or old_addresses[idx]-prior['rva']>32768:continue
                info,_=fingerprint(old_image,prior['rva'],old_addresses[idx],old_patches)
                candidates.append({'rva':prior['rva'],'base_path_sha256':info['base_path_sha256']})
            comparisons.append({'type':row['type'],'name':row['name'],'current_rva':row['rva'],
                'base_path_match':any(c['base_path_sha256']==row['base_path_sha256'] for c in candidates),'baseline_candidates':candidates})
        result['baseline_comparison']={'build':'2.6.200.276','image_sha256':expected_image,'index_sha256':expected_index,
            'checked_count':len(comparisons),'base_path_matches':sum(c['base_path_match'] for c in comparisons),'methods':comparisons,
            'scope':'Instruction-shape comparison with relocated addresses and identified patch IDs normalized. Referenced data, call-target equivalence and active patches require separate analysis.'}
    if args.prior_report:
        previous=json.loads(args.prior_report.read_text(encoding='utf-8'));comparisons=[]
        for row in rows:
            candidates=[p for p in previous['methods'] if (p['type'],p['name'],p['parameter_count'])==(row['type'],row['name'],row['parameter_count'])]
            comparisons.append({'type':row['type'],'name':row['name'],'parameter_count':row['parameter_count'],'base_path_match':any(p['base_path_sha256']==row['base_path_sha256'] for p in candidates)})
        result['baseline_comparison']={'build':previous['client_build'],'audit_sha256':hashlib.sha256(args.prior_report.read_bytes()).hexdigest(),'checked_count':len(comparisons),'base_path_matches':sum(r['base_path_match'] for r in comparisons),'selected_field_layouts_match':all(types[k]['fields']==v['fields'] for k,v in previous['selected_types'].items()),'methods':comparisons,'scope':'Selected method instruction shapes and field layouts. Dynamic patch-wrapper identities, generic/runtime callee bodies and active patches are not proved equivalent.'}
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f'Audited {len(rows)} current method bodies and {len(types)} selected types; raw artifacts remain private.')


if __name__=='__main__':main()
