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

# Independently recovered on 2.6.300.293. These five streams cover the selected
# combat methods and registration data; .pdata and the virtualized stub remain
# outside the decoded scope. Never reuse either layout on an unknown hash.
CURRENT_SHA256 = '6eb2faca25a7b21b3dc2ae53b98db41b9408906387af4f72d7bcd6b54274d37c'
CURRENT_STREAMS = (
    (0x8DADCEB, 0x574000, 29581775, 101944832),
    (0xAE8DD60, 0x1000, 1192117, 5710848),
    (0xAE854C9, 0x86A6000, 14, 512),
    (0xAFC8EF8, 0x7846000, 1015440, 7238144),
    (0xABB8C68, 0x66AD000, 2658250, 18451456),
)
CURRENT_DECODED_SHA256 = (
    '507c884c57415d6615878013900138c9bad4de1681bf1652bcc5921973ebbd90',
    'c320c61a0df1e2d769c62c473dcae417984ba76e3f1ce60a5886fad52fc190c9',
    '076a27c79e5ace2a3d47f9dd2e83e4ff6ea8872b3c2218f66c92b89b55f36560',
    'cde6e076f5a47608d078afe860857b9d686d0d2216fb1860b47c78bfca189053',
    '7eb967555e7cdc5d5781fefe30ac0a8ad7991b0f28287bafb215ccda83d64e80',
)


# Independently recovered 2.6.400.304 disk streams. Sizes, end markers and
# decompressed fingerprints are checked before any metadata/method audit.
LATEST_SHA256 = '54b80f6a283cfbb7e8c7ab5698038132d6e9c439620f108bcd668fa7d568de2c'
LATEST_STREAMS = tuple((142716928 + offset - 1024, destination, compressed, size) for offset,destination,compressed,size in [
    (35528322,4096,1193731,5712896), (5859547,5718016,29640560,102105600),
    (46600,107827200,2664950,18473472), (2883040,126304256,1016927,7248896)])
LATEST_DECODED_SHA256 = ('748be08f5f0b3f81493b2113c7d9d1b567330a91e6d4b7786cdf82949f9dfb0e','e38ea519ca5897a96434286cb8322a11e935291df137cfe8760ba8e0d91c459d','2da2765aa5e33bcffd83e54387edd5728bb199ee7cf42fd902c4eea7758927d9','eecc47ecc304508e0c040346adecd57bffaa9c2d973bf1bf425f502c176867c4')


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
    digest=hashlib.sha256(data).hexdigest()
    if digest not in (VERIFIED_SHA256,CURRENT_SHA256,LATEST_SHA256):
        raise ValueError('Unverified client hash; do not reuse these RVAs on another build')
    streams=LATEST_STREAMS if digest==LATEST_SHA256 else CURRENT_STREAMS if digest==CURRENT_SHA256 else STREAMS
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
    for index,(source, destination, compressed_size, decoded_size) in enumerate(streams):
        section = next((s for s in sections if s['rva'] <= source and
                        source + compressed_size <= s['rva'] + s['raw_size']), None)
        if section is None or destination + decoded_size > image_size:
            raise ValueError('Stream extends outside verified input or image')
        offset = section['raw_offset'] + source - section['rva']
        decoded = decode_stream(data[offset:offset + compressed_size], decoded_size)
        if digest==LATEST_SHA256 and hashlib.sha256(decoded).hexdigest()!=LATEST_DECODED_SHA256[index]:raise ValueError('Current decoded fingerprint mismatch')
        if digest==CURRENT_SHA256 and hashlib.sha256(decoded).hexdigest()!=CURRENT_DECODED_SHA256[index]:
            raise ValueError('Decoded stream fingerprint mismatch')
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
    raw=args.binary.read_bytes()
    image, streams = unpack(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(image)
    report = {'input_sha256': hashlib.sha256(raw).hexdigest(), 'format': 'RVA-indexed analysis bytes',
              'runtime_fixups_applied': False, 'streams': streams}
    args.output.with_suffix('.report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
