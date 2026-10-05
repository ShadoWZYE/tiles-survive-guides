"""Decode verified disk LZMA streams without executing or loading the client.

Build-specific, hash-gated. Output is a private RVA-indexed byte image, not a
loadable DLL, a live memory dump, or a complete initialized runtime image.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
from pathlib import Path
import struct

from audit_native_client import pe_sections

VERIFIED_SHA256 = 'e91333faf1fe03f6cbca1a676c38ed8a4d9f7fe3af8e77824b86727f2961de61'
# source RVA, destination RVA, compressed length, decompressed length.
STREAMS = (
    (0x8CFB41C, 0x1000, 1191810, 5706240),
    (0x8E218D1, 0x573000, 29515961, 101586944),
    (0x8A64148, 0x6655000, 2674642, 18408448),
    (0x8969B54, 0x77E4000, 1011759, 7218688),
    (0xAA56087, 0x81A1000, 4838624, 4829184),
    (0xB04E8B4, 0x863C000, 14, 512),
    (0xAF46F47, 0x863D000, 903002, 1326592),
)


def decode_stream(payload: bytes, expected_size: int) -> bytes:
    if not 0 < expected_size <= 134217728:
        raise ValueError('Decompressed size outside private image budget')
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[{
        'id': lzma.FILTER_LZMA1, 'dict_size': 134217728,
        'lc': 3, 'lp': 0, 'pb': 2,
    }])
    decoded = decoder.decompress(payload, max_length=expected_size + 1)
    if len(decoded) != expected_size or not decoder.eof or decoder.unused_data:
        raise ValueError('LZMA stream size or end marker does not match')
    return decoded


def unpack(data: bytes) -> tuple[bytearray, list[dict]]:
    if hashlib.sha256(data).hexdigest() != VERIFIED_SHA256:
        raise ValueError('Unverified client hash; do not reuse these RVAs on another build')
    sections = pe_sections(data)
    pe_offset = struct.unpack_from('<I', data, 0x3C)[0]
    optional = pe_offset + 24
    if struct.unpack_from('<H', data, optional)[0] != 0x20B:
        raise ValueError('Expected verified 64-bit PE layout')
    image_size, header_size = struct.unpack_from('<II', data, optional + 56)
    if image_size > 268435456 or header_size > len(data):
        raise ValueError('PE image exceeds bounded allocation')
    image = bytearray(image_size)
    image[:header_size] = data[:header_size]
    for section in sections:
        offset, size, rva = section['raw_offset'], section['raw_size'], section['rva']
        if rva + size > image_size:
            raise ValueError('Raw section outside RVA image')
        image[rva:rva + size] = data[offset:offset + size]
    report = []
    for source, destination, compressed_size, decoded_size in STREAMS:
        section = next((s for s in sections if s['rva'] <= source and
                        source + compressed_size <= s['rva'] + s['raw_size']), None)
        if section is None or destination + decoded_size > image_size:
            raise ValueError('Stream extends outside verified input or image')
        offset = section['raw_offset'] + source - section['rva']
        decoded = decode_stream(data[offset:offset + compressed_size], decoded_size)
        image[destination:destination + decoded_size] = decoded
        report.append({'source_rva': hex(source), 'destination_rva': hex(destination),
                       'compressed_size': compressed_size, 'decoded_size': decoded_size,
                       'decoded_sha256': hashlib.sha256(decoded).hexdigest()})
    return image, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() == args.binary.resolve():
        parser.error('Output must not replace the source client')
    if args.output.suffix.lower() in ('.dll', '.exe'):
        parser.error('Use .bin for the analysis image, not an executable extension')
    image, streams = unpack(args.binary.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(image)
    report = {'input_sha256': VERIFIED_SHA256, 'format': 'RVA-indexed analysis bytes',
              'runtime_fixups_applied': False, 'streams': streams}
    args.output.with_suffix('.report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
