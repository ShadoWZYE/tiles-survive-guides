"""Hash-gated static string references for the inspected 2.6.400.304 image.

Reads file bytes only. No process access, DLL loading, patching or execution.
The literal layout was inferred from four independently known report keys, then
validated across all 68,874 descriptors and the complete contiguous string heap.
"""
import hashlib,struct
from audit_native_combat import DECODED_METADATA_SHA256

IMAGE_SHA='5afef9adf2a4dc85b40adc702149a45bf10728ef2c9de1895f3b648a9128b14d'
DEFINITIONS=256
DATA=551248
END=2346196
COUNT=(DATA-DEFINITIONS)//8

def validate_heap(metadata,definitions,data,end,count):
    if not 0<=definitions<=data<=end<=len(metadata) or definitions+count*8!=data:
        raise ValueError('Invalid literal layout')
    strings=[];expected=0
    for index in range(count):
        length,offset=struct.unpack_from('<II',metadata,definitions+index*8)
        if offset!=expected or offset+length>end-data:raise ValueError('Invalid literal descriptor')
        strings.append(metadata[data+offset:data+offset+length].decode('utf-8'));expected+=length
    if expected!=end-data:raise ValueError('Literal heap has unconsumed bytes')
    return strings

def decode_usage(encoded,strings):
    if encoded>=2**32 or encoded<0 or encoded>>29!=5 or not encoded&1:
        raise ValueError('Not an unresolved static string-literal usage')
    index=(encoded&0x1fffffff)>>1
    if index>=len(strings):raise ValueError('Literal usage index outside heap')
    return strings[index]

class NativeLiteralReader:
    def __init__(self,image,metadata):
        if hashlib.sha256(image).hexdigest()!=IMAGE_SHA or hashlib.sha256(metadata).hexdigest()!=DECODED_METADATA_SHA256:
            raise ValueError('Native literal snapshot mismatch')
        self.image=image;self.strings=validate_heap(metadata,DEFINITIONS,DATA,END,COUNT)
    def at_slot(self,rva):
        if not 0<=rva<=len(self.image)-8:raise ValueError('Slot outside image')
        return decode_usage(struct.unpack_from('<Q',self.image,rva)[0],self.strings)
    def at_instruction(self,rva):
        if not 0<=rva<=len(self.image)-7:raise ValueError('Instruction outside image')
        rex,opcode,modrm=self.image[rva:rva+3]
        if rex not in (0x48,0x4c) or opcode!=0x8b or modrm&0xc7!=0x05:
            raise ValueError('Expected a 64-bit RIP-relative MOV')
        slot=rva+7+struct.unpack_from('<i',self.image,rva+3)[0]
        return {'instruction_rva':hex(rva),'slot_rva':hex(slot),'literal':self.at_slot(slot)}
