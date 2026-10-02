from __future__ import annotations

import argparse
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TypeSpec:
    code: int
    args: tuple["TypeSpec", ...] = ()
    object_name: str | None = None


@dataclass(frozen=True)
class Field:
    name: str
    type: TypeSpec
    offset: int


def read_varuint(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, pos
        shift += 7
        if shift > 35:
            raise ValueError("Invalid variable-length integer")


def read_text(data: bytes, pos: int) -> tuple[str, int]:
    size, pos = read_varuint(data, pos)
    end = pos + size
    return data[pos:end].decode("utf-8"), end


def read_relative_target(data: bytes, pos: int) -> int | None:
    relative = struct.unpack_from("<i", data, pos)[0]
    return None if relative == 0 else pos + 4 + relative


class SchemaReader:
    def __init__(self, data: bytes, pos: int):
        self.data = data
        self.pos = pos

    def text(self) -> str:
        value, self.pos = read_text(self.data, self.pos)
        return value

    def type_spec(self, code: int | None = None) -> TypeSpec:
        if code is None:
            code = self.data[self.pos]
            self.pos += 1
        if code in (10, 12):
            return TypeSpec(code, object_name=self.text())
        if code == 7:
            key_code = self.data[self.pos]
            self.pos += 1
            return TypeSpec(code, (TypeSpec(key_code),), object_name=self.text())
        if code == 11:
            return TypeSpec(code, (self.type_spec(),))
        if code == 9:
            return TypeSpec(code, (self.type_spec(), self.type_spec()))
        return TypeSpec(code)


def storage_size(spec: TypeSpec, schemas: dict[str, list[Field]]) -> int:
    if spec.code == 0:
        return 1
    if spec.code in (4, 6):
        return 8
    return 4


def parse_schema(data: bytes, offset: int) -> tuple[str, list[Field], dict[str, list[Field]]]:
    reader = SchemaReader(data, offset)
    schema_count = struct.unpack_from("<I", data, reader.pos)[0]
    reader.pos += 4
    if schema_count < 1:
        raise ValueError("CFG has no schemas")
    raw_schemas: dict[str, list[tuple[str, TypeSpec]]] = {}
    root_name: str | None = None
    for _ in range(schema_count):
        root = reader.type_spec()
        if root.code not in (10, 12) or not root.object_name:
            raise ValueError("CFG schema definition is not a table or embedded value")
        if root_name is None:
            if root.code != 12:
                raise ValueError("First CFG schema definition is not the root table")
            root_name = root.object_name
        field_count = struct.unpack_from("<I", data, reader.pos)[0]
        reader.pos += 4
        raw_fields: list[tuple[str, TypeSpec]] = []
        for _ in range(field_count):
            code = data[reader.pos]
            reader.pos += 1
            name = reader.text()
            raw_fields.append((name, reader.type_spec(code)))
        raw_schemas[root.object_name] = raw_fields
    if reader.pos != len(data):
        raise ValueError(f"Schema did not consume the table: {len(data) - reader.pos} bytes remain")
    schemas: dict[str, list[Field]] = {}

    def build_fields(name: str) -> list[Field]:
        if name in schemas:
            return schemas[name]
        schemas[name] = []
        for _, spec in raw_schemas[name]:
            if spec.code == 10 and spec.object_name:
                build_fields(spec.object_name)
        row_offset = 0
        fields: list[Field] = []
        for field_name, spec in raw_schemas[name]:
            fields.append(Field(field_name, spec, row_offset))
            row_offset += storage_size(spec, schemas)
        schemas[name] = fields
        return fields

    for name in raw_schemas:
        build_fields(name)
    assert root_name is not None
    return root_name, schemas[root_name], schemas


def decode_at(data: bytes, pos: int, spec: TypeSpec, schemas: dict[str, list[Field]]) -> Any:
    if spec.code == 0:
        return data[pos] != 0
    if spec.code == 3:
        return struct.unpack_from("<i", data, pos)[0]
    if spec.code == 4:
        return struct.unpack_from("<q", data, pos)[0]
    if spec.code == 6:
        return struct.unpack_from("<d", data, pos)[0]
    if spec.code == 8:
        target = read_relative_target(data, pos)
        return "" if target is None else read_text(data, target)[0]
    if spec.code == 7:
        # A nullable CFG reference is stored as the referenced table's scalar key.
        value = struct.unpack_from("<i", data, pos)[0]
        return None if value == 0 else value
    if spec.code == 10:
        if not spec.object_name or spec.object_name not in schemas:
            raise ValueError(f"Missing embedded schema for {spec.object_name!r}")
        target = read_relative_target(data, pos)
        if target is None:
            return None
        return {
            field.name: decode_at(data, target + field.offset, field.type, schemas)
            for field in schemas[spec.object_name]
        }
    if spec.code in (9, 11):
        target = read_relative_target(data, pos)
        if target is None:
            return {} if spec.code == 9 else []
        count = struct.unpack_from("<I", data, target)[0]
        cursor = target + 4
        if spec.code == 11:
            item_spec = spec.args[0]
            result = []
            for _ in range(count):
                result.append(decode_at(data, cursor, item_spec, schemas))
                cursor += storage_size(item_spec, schemas)
            return result
        key_spec, value_spec = spec.args
        result: dict[str, Any] = {}
        for _ in range(count):
            key = decode_at(data, cursor, key_spec, schemas)
            cursor += storage_size(key_spec, schemas)
            value = decode_at(data, cursor, value_spec, schemas)
            cursor += storage_size(value_spec, schemas)
            result[str(key)] = value
        return result
    raise ValueError(f"Unsupported CFG type code {spec.code}")


def decode_table(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if data[1:4] != b"CFG":
        raise ValueError(f"Not a CFG table: {path}")
    index_offset, schema_offset, declared_count = struct.unpack_from("<III", data, 4)
    table_name, fields, schemas = parse_schema(data, schema_offset)
    count = struct.unpack_from("<I", data, index_offset)[0]
    offsets = struct.unpack_from(f"<{count}I", data, index_offset + 4)
    key_count_pos = index_offset + 4 + count * 4
    key_count = struct.unpack_from("<I", data, key_count_pos)[0]
    if count != declared_count or key_count != count:
        raise ValueError(
            f"CFG index count mismatch: header={declared_count}, offsets={count}, keys={key_count}"
        )
    keys = struct.unpack_from(f"<{count}i", data, key_count_pos + 4)
    rows = []
    for key, row_pos in zip(keys, offsets):
        row = {
            field.name: decode_at(data, row_pos + field.offset, field.type, schemas)
            for field in fields
        }
        rows.append({"_key": key, **row})
    return {
        "table": table_name,
        "source": str(path),
        "row_count": count,
        "row_size": sum(storage_size(field.type, schemas) for field in fields),
        "fields": [field.name for field in fields],
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Decode an extracted Tiles Survive CFG table")
    parser.add_argument("table", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    decoded = decode_table(args.table)
    rendered = json.dumps(decoded, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"decoded={decoded['row_count']} output={args.output}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
