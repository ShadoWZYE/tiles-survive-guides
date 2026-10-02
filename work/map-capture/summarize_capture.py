from __future__ import annotations

import collections
import hashlib
import re
import socket
import struct
import sys
from pathlib import Path

from analyze_pcap import assemble, entropy, iter_pcapng_packets, parse_tcp


KEYWORDS = (
    b"map", b"tile", b"coord", b"position", b"player", b"user_info",
    b"city", b"wilderness", b"kingdom", b"world", b"uid", b"name",
)


def ipv4_offset(packet: bytes, link_type: int):
    if link_type == 1:
        if len(packet) < 14:
            return None
        ether_type = struct.unpack_from("!H", packet, 12)[0]
        offset = 14
        if ether_type == 0x8100 and len(packet) >= 18:
            ether_type = struct.unpack_from("!H", packet, 16)[0]
            offset = 18
        return offset if ether_type == 0x0800 else None
    if link_type in (101, 228):
        return 0
    return None


def parse_udp(packet: bytes, link_type: int):
    ip_offset = ipv4_offset(packet, link_type)
    if ip_offset is None or len(packet) < ip_offset + 28 or packet[ip_offset] >> 4 != 4:
        return None
    ihl = (packet[ip_offset] & 0x0F) * 4
    if packet[ip_offset + 9] != 17:
        return None
    src = socket.inet_ntoa(packet[ip_offset + 12:ip_offset + 16])
    dst = socket.inet_ntoa(packet[ip_offset + 16:ip_offset + 20])
    udp_offset = ip_offset + ihl
    src_port, dst_port, length = struct.unpack_from("!HHH", packet, udp_offset)
    payload = packet[udp_offset + 8:udp_offset + min(length, len(packet) - udp_offset)]
    return src, src_port, dst, dst_port, payload


def describe_payload(data: bytes):
    lowered = data.lower()
    hits = {word.decode(): lowered.count(word) for word in KEYWORDS if word in lowered}
    tls_records = len(re.findall(rb"[\x14-\x17]\x03[\x01-\x04]..", data))
    json_starts = data.count(b'{"')
    printable = sum(32 <= value < 127 or value in (9, 10, 13) for value in data)
    return hits, tls_records, json_starts, printable / len(data) if data else 0.0


def main(path: Path):
    packets = list(iter_pcapng_packets(path))
    tcp_rows = {}
    udp_rows = {}
    for interface_id, link_type, timestamp, packet_len, packet in packets:
        tcp = parse_tcp(packet, link_type)
        if tcp:
            src, src_port, dst, dst_port, seq, ack, flags, payload = tcp
            key = (src, src_port, dst, dst_port, seq, ack, flags, hashlib.sha256(payload).digest())
            tcp_rows.setdefault(key, (timestamp, *tcp))
            continue
        udp = parse_udp(packet, link_type)
        if udp:
            src, src_port, dst, dst_port, payload = udp
            key = (src, src_port, dst, dst_port, hashlib.sha256(payload).digest())
            udp_rows.setdefault(key, (timestamp, *udp))

    tcp_directions = collections.defaultdict(list)
    for timestamp, src, src_port, dst, dst_port, seq, ack, flags, payload in tcp_rows.values():
        if payload:
            tcp_directions[(src, src_port, dst, dst_port)].append((seq, payload))

    print(f"capture={path.name} blocks={len(packets)} distinct_tcp={len(tcp_rows)} distinct_udp={len(udp_rows)}")
    print("\nTCP DIRECTIONS")
    for endpoint, segments in sorted(tcp_directions.items(), key=lambda item: -sum(len(p) for _, p in item[1])):
        stream, gaps = assemble(segments)
        hits, tls, json_starts, printable = describe_payload(stream)
        name = hashlib.sha256(repr(endpoint).encode()).hexdigest()[:12]
        out = path.with_name(path.stem + f"-tcp-{name}.bin")
        out.write_bytes(stream)
        print(
            f"{endpoint[0]}:{endpoint[1]} -> {endpoint[2]}:{endpoint[3]} "
            f"segments={len(segments)} bytes={len(stream)} gaps={len(gaps)} "
            f"entropy={entropy(stream):.3f} printable={printable:.2%} tls={tls} "
            f"json={json_starts} hits={hits} head={stream[:20].hex()} file={out.name}"
        )

    udp_directions = collections.defaultdict(list)
    for timestamp, src, src_port, dst, dst_port, payload in udp_rows.values():
        if payload:
            udp_directions[(src, src_port, dst, dst_port)].append(payload)
    print("\nUDP DIRECTIONS")
    for endpoint, payloads in sorted(udp_directions.items(), key=lambda item: -sum(map(len, item[1]))):
        data = b"".join(payloads)
        hits, tls, json_starts, printable = describe_payload(data)
        print(
            f"{endpoint[0]}:{endpoint[1]} -> {endpoint[2]}:{endpoint[3]} "
            f"datagrams={len(payloads)} bytes={len(data)} entropy={entropy(data):.3f} "
            f"printable={printable:.2%} json={json_starts} hits={hits} head={data[:20].hex()}"
        )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
