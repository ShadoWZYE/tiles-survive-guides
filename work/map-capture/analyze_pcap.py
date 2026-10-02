from __future__ import annotations

import collections
import hashlib
import json
import math
import socket
import struct
import sys
from pathlib import Path


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = collections.Counter(data)
    size = len(data)
    return -sum((count / size) * math.log2(count / size) for count in counts.values())


def iter_pcapng_packets(path: Path):
    raw = path.read_bytes()
    offset = 0
    endian = "<"
    interfaces: list[int] = []
    while offset + 12 <= len(raw):
        block_type_le = struct.unpack_from("<I", raw, offset)[0]
        if block_type_le == 0x0A0D0D0A:
            magic = raw[offset + 8 : offset + 12]
            if magic == b"\x4d\x3c\x2b\x1a":
                endian = "<"
            elif magic == b"\x1a\x2b\x3c\x4d":
                endian = ">"
            else:
                raise ValueError(f"bad section byte-order magic at {offset}")
        block_type, block_len = struct.unpack_from(endian + "II", raw, offset)
        if block_len < 12 or offset + block_len > len(raw):
            raise ValueError(f"bad block length {block_len} at {offset}")
        if block_type == 1:
            link_type = struct.unpack_from(endian + "H", raw, offset + 8)[0]
            interfaces.append(link_type)
        elif block_type == 6:
            interface_id, ts_hi, ts_lo, cap_len, packet_len = struct.unpack_from(
                endian + "IIIII", raw, offset + 8
            )
            packet = raw[offset + 28 : offset + 28 + cap_len]
            link_type = interfaces[interface_id] if interface_id < len(interfaces) else -1
            yield interface_id, link_type, (ts_hi << 32) | ts_lo, packet_len, packet
        offset += block_len


def parse_tcp(packet: bytes, link_type: int):
    if link_type == 1:
        if len(packet) < 14:
            return None
        ether_type = struct.unpack_from("!H", packet, 12)[0]
        ip_offset = 14
        if ether_type == 0x8100 and len(packet) >= 18:
            ether_type = struct.unpack_from("!H", packet, 16)[0]
            ip_offset = 18
        if ether_type != 0x0800:
            return None
    elif link_type in (101, 228):
        ip_offset = 0
    else:
        return None

    if len(packet) < ip_offset + 20 or packet[ip_offset] >> 4 != 4:
        return None
    ihl = (packet[ip_offset] & 0x0F) * 4
    total_len = struct.unpack_from("!H", packet, ip_offset + 2)[0]
    protocol = packet[ip_offset + 9]
    if protocol != 6 or len(packet) < ip_offset + ihl + 20:
        return None
    src = socket.inet_ntoa(packet[ip_offset + 12 : ip_offset + 16])
    dst = socket.inet_ntoa(packet[ip_offset + 16 : ip_offset + 20])
    tcp_offset = ip_offset + ihl
    src_port, dst_port, seq, ack = struct.unpack_from("!HHII", packet, tcp_offset)
    data_offset = (packet[tcp_offset + 12] >> 4) * 4
    flags = packet[tcp_offset + 13]
    payload_start = tcp_offset + data_offset
    payload_end = min(ip_offset + total_len, len(packet))
    payload = packet[payload_start:payload_end]
    return src, src_port, dst, dst_port, seq, ack, flags, payload


def assemble(segments):
    unique = {}
    for seq, payload in segments:
        if payload:
            unique[(seq, hashlib.sha256(payload).digest())] = payload
    ordered = sorted(((seq, payload) for (seq, _), payload in unique.items()), key=lambda x: x[0])
    if not ordered:
        return b"", []
    base = ordered[0][0]
    output = bytearray()
    gaps = []
    for seq, payload in ordered:
        relative = seq - base
        if relative > len(output):
            gaps.append((len(output), relative))
            output.extend(b"\x00" * (relative - len(output)))
        overlap = len(output) - relative
        if overlap < len(payload):
            output.extend(payload[max(0, overlap):])
    return bytes(output), gaps


def main(path: Path):
    packets = list(iter_pcapng_packets(path))
    print(f"pcap={path}")
    print(f"enhanced_packet_blocks={len(packets)}")
    print("interfaces=" + repr(collections.Counter(link for _, link, _, _, _ in packets)))

    parsed = []
    for interface_id, link_type, timestamp, packet_len, packet in packets:
        tcp = parse_tcp(packet, link_type)
        if tcp and (tcp[1] == 9300 or tcp[3] == 9300):
            parsed.append((interface_id, timestamp, *tcp))
    print(f"tcp_9300_packets={len(parsed)}")

    distinct = {}
    for row in parsed:
        interface_id, timestamp, src, src_port, dst, dst_port, seq, ack, flags, payload = row
        key = (src, src_port, dst, dst_port, seq, ack, flags, hashlib.sha256(payload).digest())
        distinct.setdefault(key, row)
    rows = sorted(distinct.values(), key=lambda row: row[1])
    print(f"distinct_tcp_packets={len(rows)}")

    directions = collections.defaultdict(list)
    for row in rows:
        _, _, src, src_port, dst, dst_port, seq, ack, flags, payload = row
        direction = f"{src}:{src_port} -> {dst}:{dst_port}"
        if payload:
            directions[direction].append((seq, payload))

    for direction, segments in directions.items():
        stream, gaps = assemble(segments)
        nonzero = stream.replace(b"\x00", b"")
        print("\nDIRECTION", direction)
        print(f"segments={len(segments)} bytes_with_gaps={len(stream)} nonzero_bytes={len(nonzero)} gaps={gaps}")
        print(f"entropy={entropy(nonzero):.4f}")
        print(f"head={stream[:160].hex(' ')}")
        printable = ''.join(chr(byte) if 32 <= byte < 127 else '.' for byte in stream[:500])
        print(f"ascii={printable}")
        for i, (seq, payload) in enumerate(sorted(segments, key=lambda item: item[0])[:30]):
            print(f"segment[{i}] seq={seq} len={len(payload)} entropy={entropy(payload):.3f} head={payload[:48].hex(' ')}")

        safe_name = hashlib.sha256(direction.encode()).hexdigest()[:12]
        stream_path = path.with_name(path.stem + f"-{safe_name}.bin")
        stream_path.write_bytes(stream)
        print(f"stream_file={stream_path}")

        text = stream.decode("utf-8", errors="replace")
        decoder = json.JSONDecoder()
        decoded_objects = []
        for start, char in enumerate(text):
            if char != "{":
                continue
            try:
                obj, end = decoder.raw_decode(text, start)
            except json.JSONDecodeError:
                continue
            decoded_objects.append((start, end, obj))
        maximal = []
        for candidate in decoded_objects:
            start, end, _ = candidate
            if not any(parent_start <= start and end <= parent_end for parent_start, parent_end, _ in maximal):
                maximal.append(candidate)
        print(f"json_objects={len(maximal)}")
        for index, (start, end, obj) in enumerate(maximal):
            if isinstance(obj, dict):
                keys = list(obj.keys())
            else:
                keys = [type(obj).__name__]
            encoded = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            keywords = sorted({word for word in ("map", "tile", "coord", "position", "x", "y", "player", "city", "wilderness") if word in encoded.lower()})
            print(f"json[{index}] offset={start}:{end} chars={end-start} keys={keys[:15]} keywords={keywords}")
            if keywords:
                print(encoded[:1200])


if __name__ == "__main__":
    main(Path(sys.argv[1]))
