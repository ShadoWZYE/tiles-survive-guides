"""Bounded offline x64 control-flow inspection. Never loads or executes a DLL.

Requires pefile and capstone. Keep disassembly output private.
Indirect branches are reported, not emulated or guessed.
"""
from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path


def main() -> None:
    import capstone
    import pefile

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--rva', type=lambda value: int(value, 0))
    parser.add_argument('--max-blocks', type=int, default=64)
    parser.add_argument('--max-instructions', type=int, default=2048)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.max_blocks <= 512 or not 1 <= args.max_instructions <= 16384:
        parser.error('Use 1..512 blocks and 1..16384 instructions')
    pe = pefile.PE(str(args.binary))
    if pe.FILE_HEADER.Machine != 0x8664:
        parser.error('Only x64 PE files are supported')
    base = pe.OPTIONAL_HEADER.ImageBase
    start = args.rva if args.rva is not None else pe.OPTIONAL_HEADER.AddressOfEntryPoint

    def file_backed(rva: int) -> bool:
        return any(section.VirtualAddress <= rva < section.VirtualAddress + section.SizeOfRawData
                   and section.Characteristics & 0x20000000 for section in pe.sections)

    if not file_backed(start):
        parser.error('Start RVA is not in a file-backed executable section')
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    pending = deque([start])
    visited = set()
    blocks = []
    total = 0
    indirect = 0
    while pending and len(blocks) < args.max_blocks and total < args.max_instructions:
        rva = pending.popleft()
        if rva in visited or not file_backed(rva):
            continue
        visited.add(rva)
        block = {'rva': hex(rva), 'instructions': []}
        for instruction in md.disasm(pe.get_data(rva, 1024), base + rva):
            current = instruction.address - base
            if not file_backed(current) or total >= args.max_instructions:
                break
            record = {'rva': hex(current), 'mnemonic': instruction.mnemonic,
                      'operands': instruction.op_str}
            block['instructions'].append(record)
            total += 1
            jump = instruction.group(capstone.CS_GRP_JUMP)
            call = instruction.group(capstone.CS_GRP_CALL)
            if jump or call:
                operands = instruction.operands
                if operands and operands[0].type == capstone.x86.X86_OP_IMM:
                    target = operands[0].imm - base
                    record['direct_target_rva'] = hex(target)
                    if file_backed(target):
                        pending.append(target)
                else:
                    record['unresolved_indirect_branch'] = True
                    indirect += 1
            if instruction.group(capstone.CS_GRP_RET) and len(block['instructions']) > 1:
                if block['instructions'][-2]['mnemonic'] == 'push':
                    record['possible_push_ret_dispatch'] = True
                    indirect += 1
            if instruction.group(capstone.CS_GRP_RET) or instruction.mnemonic in ('jmp', 'int3', 'ud2'):
                break
        blocks.append(block)
    report = {'file': args.binary.name, 'start_rva': hex(start),
              'blocks': blocks, 'instruction_count': total,
              'unresolved_indirect_branches': indirect,
              'budget_reached': bool(pending) and (len(blocks) >= args.max_blocks or total >= args.max_instructions),
              'note': 'Static disk bytes only. Indirect targets and runtime unpacking are not resolved.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'blocks={len(blocks)} instructions={total} indirect={indirect} budget_reached={report["budget_reached"]}')


if __name__ == '__main__':
    main()
