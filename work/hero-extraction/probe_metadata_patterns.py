"""Offline pattern measurements and explicitly unvalidated XOR candidates.

No process access, DLL execution or game writes. Candidate files stay private.
Frequency guesses do not recover a loader or prove successful decryption.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from audit_native_client import entropy, metadata_header


def infer_xor_mask(sample: bytes, period: int, common_byte: int) -> bytes:
    if period < 1 or len(sample) < period or not 0 <= common_byte <= 255:
        raise ValueError('Invalid period, sample length or assumed plaintext byte')
    return bytes(Counter(sample[position::period]).most_common(1)[0][0] ^ common_byte
                 for position in range(period))


def xor_bytes(data: bytes, mask: bytes, offset: int = 0) -> bytes:
    if not mask:
        raise ValueError('Empty mask')
    return bytes(value ^ mask[(index + offset) % len(mask)] for index, value in enumerate(data))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--reference-offset', type=lambda value: int(value, 0), default=0x800000)
    parser.add_argument('--sample-size', type=int, default=1048576)
    parser.add_argument('--period', type=int, default=128)
    parser.add_argument('--assumed-common-byte', type=lambda value: int(value, 0), default=0x65,
                        help='Hypothesis only: 0x65 is lowercase e; use 0 for a zero-rich region')
    parser.add_argument('--known-text', action='append', default=[])
    parser.add_argument('--candidate-output', type=Path,
                        help='Optional private directory for candidate bytes and inferred mask')
    args = parser.parse_args()
    data = args.metadata.read_bytes()
    if not 1 <= args.period <= 4096 or not args.period <= args.sample_size <= 16777216:
        parser.error('Use period 1..4096 and sample size period..16777216')
    if args.reference_offset < 0 or args.reference_offset % args.period:
        parser.error('Reference offset must be nonnegative and aligned to the period')
    sample = data[args.reference_offset:args.reference_offset + args.sample_size]
    try:
        mask = infer_xor_mask(sample, args.period, args.assumed_common_byte)
    except ValueError as error:
        parser.error(str(error))
    start = 4096
    region = data[start:start + 65536]
    measurements = []
    for lag in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024):
        if len(region) <= lag:
            continue
        measurements.append({'lag': lag, 'equal_byte_fraction':
                             round(sum(a == b for a,b in zip(region, region[lag:])) / (len(region)-lag), 6)})
    candidate = xor_bytes(data, mask)
    report = {'status': 'unvalidated statistical candidate',
              'reference_offset': args.reference_offset, 'period': args.period,
              'assumed_common_byte': args.assumed_common_byte,
              'reference_sample_entropy': round(entropy(sample), 4),
              'lag_measurement_offset': start, 'lag_measurements': measurements,
              'candidate_header': metadata_header(candidate),
              'known_text_matches': [{'text': text, 'offset': candidate.find(text.encode('utf-8'))}
                                     for text in args.known_text],
              'warning': 'Readable fragments do not validate the mask, metadata tables or native method recovery.'}
    if args.candidate_output:
        args.candidate_output.mkdir(parents=True, exist_ok=True)
        (args.candidate_output/'candidate.dat').write_bytes(candidate)
        (args.candidate_output/'inferred-mask.bin').write_bytes(mask)
        (args.candidate_output/'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
