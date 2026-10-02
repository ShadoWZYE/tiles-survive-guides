from __future__ import annotations

import argparse
import bisect
from collections import Counter
import csv
import re
import struct
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PACK = Path(
    r"C:\Program Files (x86)\FunPlus\Tiles Survive\ngame\2.6.0.235"
    r"\tspc_Data\StreamingAssets\GameAssets\BinaryConfigPack.ss"
)
NAME_SLOT_SIZE = 256


@dataclass(frozen=True)
class Entry:
    index: int
    block: int
    size: int
    name: str

    @property
    def offset(self) -> int:
        return self.block * 4096


def read_entries(data: bytes) -> list[Entry]:
    if data[:4] != b"\x00SOS":
        raise ValueError("Not a Tiles Survive SOS configuration pack")
    block_size, name_slots, count = struct.unpack_from("<III", data, 4)
    if block_size != 4096 or name_slots != 4096:
        raise ValueError(f"Unexpected pack geometry: {block_size=}, {name_slots=}")

    name_table_offset = 16 + name_slots * 12
    entries: list[Entry] = []
    for index in range(count):
        ordinal, block, size = struct.unpack_from("<III", data, 16 + index * 12)
        if ordinal != index:
            raise ValueError(f"Directory ordinal mismatch at {index}: {ordinal}")
        name_pos = name_table_offset + index * NAME_SLOT_SIZE
        name_size = data[name_pos]
        name = data[name_pos + 1 : name_pos + 1 + name_size].decode("utf-8")
        entries.append(Entry(index, block, size, name))
    return entries


def build_interval_index(entries: list[Entry]) -> tuple[list[int], list[Entry]]:
    ordered = sorted(entries, key=lambda entry: entry.offset)
    return [entry.offset for entry in ordered], ordered


def containing_entry(starts: list[int], entries: list[Entry], offset: int) -> Entry | None:
    index = bisect.bisect_right(starts, offset) - 1
    if index < 0:
        return None
    entry = entries[index]
    return entry if offset < entry.offset + entry.size else None


def safe_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "generated")
    parser.add_argument("--term", action="append", default=[])
    parser.add_argument("--int32", action="append", type=int, default=[], help="Find a little-endian signed 32-bit value")
    parser.add_argument("--extract", action="append", default=[])
    parser.add_argument(
        "--occurrences",
        action="store_true",
        help="Print every term offset instead of a compact per-table summary",
    )
    args = parser.parse_args()

    data = args.pack.read_bytes()
    lowered_data = data.lower()
    entries = read_entries(data)
    starts, ordered_entries = build_interval_index(entries)
    args.output.mkdir(parents=True, exist_ok=True)

    with (args.output / "table-catalog.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("index", "name", "block", "offset", "size", "has_cfg_magic"))
        for entry in entries:
            writer.writerow((
                entry.index,
                entry.name,
                entry.block,
                entry.offset,
                entry.size,
                data[entry.offset + 1 : entry.offset + 4] == b"CFG",
            ))

    for term in args.term:
        needle = term.encode("utf-8")
        lowered_needle = needle.lower()
        start = 0
        owners: Counter[str] = Counter()
        outside = 0
        while True:
            offset = lowered_data.find(lowered_needle, start)
            if offset < 0:
                break
            entry = containing_entry(starts, ordered_entries, offset)
            owner = entry.name if entry else "<pack-directory-or-padding>"
            if entry:
                owners[owner] += 1
            else:
                outside += 1
            if args.occurrences:
                print(f"term={term!r} offset=0x{offset:X} table={owner}")
            start = offset + 1
        print(f"term={term!r} matches={sum(owners.values()) + outside}")
        for owner, count in owners.most_common():
            print(f"  table={owner} count={count}")
        if outside:
            print(f"  table=<pack-directory-or-padding> count={outside}")

    for value in args.int32:
        needle = struct.pack("<i", value)
        start = 0
        owners: Counter[str] = Counter()
        outside = 0
        while True:
            offset = data.find(needle, start)
            if offset < 0:
                break
            entry = containing_entry(starts, ordered_entries, offset)
            if entry:
                owners[entry.name] += 1
            else:
                outside += 1
            if args.occurrences:
                print(f"int32={value} offset=0x{offset:X} table={entry.name if entry else '<pack-directory-or-padding>'}")
            start = offset + 1
        print(f"int32={value} matches={sum(owners.values()) + outside}")
        for owner, count in owners.most_common():
            print(f"  table={owner} count={count}")
        if outside:
            print(f"  table=<pack-directory-or-padding> count={outside}")

    patterns = [re.compile(pattern, re.I) for pattern in args.extract]
    for entry in entries:
        if patterns and not any(pattern.search(entry.name) for pattern in patterns):
            continue
        raw = data[entry.offset : entry.offset + entry.size]
        (args.output / f"{entry.index:04}_{safe_filename(entry.name)}.cfg").write_bytes(raw)

    print(f"tables={len(entries)} catalog={args.output / 'table-catalog.csv'}")


if __name__ == "__main__":
    main()
