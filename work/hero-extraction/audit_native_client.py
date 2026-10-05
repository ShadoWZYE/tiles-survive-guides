"""Inspect native client files without loading DLLs or attaching to the game."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    return -sum((n / len(data)) * math.log2(n / len(data)) for n in Counter(data).values())


def metadata_header(data: bytes) -> dict:
    if len(data) < 8:
        return {"plausible_standard_header": False, "reason": "Too short"}
    magic, version = struct.unpack_from("<II", data)
    return {"magic_hex": f"0x{magic:08X}", "second_word": version,
            "second_word_equals_file_size": version == len(data),
            "plausible_standard_header": magic == 0xFAB11BAF and 16 <= version <= 40,
            "note": "Header plausibility is not proof of successful decryption."}


def pe_sections(data: bytes) -> list[dict]:
    if data[:2] != b"MZ" or len(data) < 64:
        raise ValueError("Not a PE image")
    pos = struct.unpack_from("<I", data, 0x3C)[0]
    if pos + 24 > len(data) or data[pos:pos + 4] != b"PE\0\0":
        raise ValueError("Invalid PE signature")
    count = struct.unpack_from("<H", data, pos + 6)[0]
    optional_size = struct.unpack_from("<H", data, pos + 20)[0]
    section_table = pos + 24 + optional_size
    if section_table + count * 40 > len(data):
        raise ValueError("Truncated PE section table")
    result = []
    for index in range(count):
        p = section_table + index * 40
        name = data[p:p + 8].rstrip(b"\0").decode("ascii", errors="replace")
        virtual_size, rva, size, offset = struct.unpack_from("<IIII", data, p + 8)
        if size and offset + size > len(data):
            raise ValueError("PE section extends outside file")
        result.append({"name": name, "rva": rva, "virtual_size": virtual_size,
                       "raw_size": size, "raw_offset": offset,
                       "entropy": round(entropy(data[offset:offset + min(size, 1048576)]), 4)})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--binary", type=Path, action="append", required=True)
    args = parser.parse_args()
    data = args.metadata.read_bytes()
    report = {"metadata": {"file": args.metadata.name, "size": len(data),
              "sha256": hashlib.sha256(data).hexdigest(), **metadata_header(data),
              "first_64_bytes_hex": data[:64].hex(),
              "sample_entropy": round(entropy(data[8:65544]), 4)}, "binaries": []}
    for path in args.binary:
        raw = path.read_bytes()
        report["binaries"].append({"file": path.name, "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(), "sections": pe_sections(raw),
            "metadata_filename_offset": raw.find(b"global-metadata.dat"),
            "metadata_magic_offset": raw.find(bytes.fromhex("af1bb1fa"))})
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
