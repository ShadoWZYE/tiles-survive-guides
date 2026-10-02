from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


DEFAULT_LANGUAGE_PACK = Path(
    r"C:\Program Files (x86)\FunPlus\Tiles Survive\GameData\GameAssets"
    r"\Languages\InGameBin\language_en.json.bin.enc"
)

# This is the fixed client-side XOR key used by the installed language pack.
# It is content obfuscation, not account/session material.
XOR_KEY = bytes.fromhex(
    "4f626459517a56526854464e46356c74594f364830707a7378394e52466c4d46"
)


def decode_language_pack(path: Path) -> dict[str, str]:
    encrypted = path.read_bytes()
    data = bytes(value ^ XOR_KEY[index % len(XOR_KEY)] for index, value in enumerate(encrypted))
    version, count, first_offset = struct.unpack_from(">III", data, 0)
    if version != 1 or count < 2 or first_offset != 0:
        raise ValueError("Unsupported Tiles Survive language pack header")

    position = 12
    index_rows: list[tuple[str, int]] = []
    # The final index record is a sentinel containing the value block size/base.
    for _ in range(count - 1):
        offset, name_length = struct.unpack_from(">II", data, position)
        position += 8
        name = data[position : position + name_length].decode("utf-8")
        position += name_length
        index_rows.append((name, offset))

    value_block_size, value_block_offset = struct.unpack_from(">II", data, position)
    if value_block_offset + value_block_size > len(data):
        raise ValueError("Language pack value block does not match file length")

    # Each row stores the end offset of the preceding value. Therefore the value
    # for a key begins at the following row's offset (or the sentinel for last).
    offsets = [offset for _, offset in index_rows] + [value_block_size]
    result: dict[str, str] = {}
    for index, (name, _) in enumerate(index_rows):
        value_offset = offsets[index + 1]
        length = struct.unpack_from(">I", data, value_block_offset + value_offset)[0]
        start = value_block_offset + value_offset + 4
        result[name] = data[start : start + length].decode("utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Decode a Tiles Survive language string pack")
    parser.add_argument("source", nargs="?", type=Path, default=DEFAULT_LANGUAGE_PACK)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    strings = decode_language_pack(args.source)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(strings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"strings={len(strings)} output={args.output}")
    else:
        print(f"strings={len(strings)}")


if __name__ == "__main__":
    main()
