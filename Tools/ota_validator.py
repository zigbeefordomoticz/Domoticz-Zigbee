#!/usr/bin/env python3
"""
OTA Validator

This script validates Zigbee OTA firmware updates by comparing:
1. Blocks extracted from a Wireshark-decrypted JSON log
2. Blocks from a tracing log (Seq/Offset/Size/Data)
3. Original OTA firmware binary file

It supports:
- Merging both sources, handling retransmissions
- Optional endian swap (16-bit)
- Offset continuity checks
- Per-block byte-by-byte comparison
- Rebuilding full firmware image
- Filtering first block or by source network address

Usage examples:
python3 ota_validator.py --wireshark-json wireshark.json \
    --source firmware.zigbee --output rebuilt.bin
"""

import argparse
from pathlib import Path
from binascii import unhexlify
import json
import re

# -------------------------
# Parse Wireshark JSON OTA blocks
# -------------------------
def parse_wireshark_json(path, first_block_only=False, src_addr=None):
    blocks = {}
    with open(path, "r") as f:
        entries = json.load(f)
        for pkt in entries:
            layers = pkt.get("_source", {}).get("layers", {})

            if src_addr is not None:
                wpan_src = layers.get("wpan", {}).get("wpan.src16")
                if wpan_src is None or int(wpan_src, 16) != src_addr:
                    continue

            zcl_payload = layers.get("zbee_zcl", {}).get("Payload", {})
            ota_data_hex = zcl_payload.get("zbee_zcl_general.ota.image.data")
            offset_str = zcl_payload.get("zbee_zcl_general.ota.file.offset")
            size_str = zcl_payload.get("zbee_zcl_general.ota.data_size")

            if ota_data_hex is None or offset_str is None or size_str is None:
                continue

            offset = int(offset_str)
            size = int(size_str)
            data = bytes.fromhex(ota_data_hex.replace(":", ""))
            if len(data) != size:
                print(f"[WARN] WS block @ offset {offset} size mismatch (declared={size}, actual={len(data)})")

            blocks[offset] = data
            if first_block_only:
                break
    return blocks

# -------------------------
# Parse tracing log
# -------------------------
TRACE_REGEX = re.compile(
    r"Seq:(?P<seq>\d+)\s+\|\s+Offset:(?P<offset>\d+)\s+\|\s+Size:(?P<size>\d+)\s+\|\s+Data:(?P<data>[0-9a-fA-F]+)"
)

def parse_trace_log(path, first_block_only=False):
    blocks = {}
    with open(path, "r") as f:
        for line in f:
            m = TRACE_REGEX.search(line)
            if not m:
                continue
            offset = int(m.group("offset"))
            size = int(m.group("size"))
            data = bytes.fromhex(m.group("data"))
            if len(data) != size:
                print(f"[WARN] Trace block @ offset {offset} size mismatch (declared={size}, actual={len(data)})")
            blocks[offset] = data
            if first_block_only:
                break
    return blocks

# -------------------------
# Merge blocks
# -------------------------
def merge_blocks(*block_dicts):
    merged = {}
    for d in block_dicts:
        merged.update(d)
    return sorted(merged.items(), key=lambda x: x[0])

# -------------------------
# Checks
# -------------------------
def check_offset_continuity(sorted_blocks):
    print("\n🔎 Checking offset continuity…")
    prev_offset = None
    prev_size = None
    errors = 0
    for offset, data in sorted_blocks:
        if prev_offset is not None:
            expected = prev_offset + prev_size
            if offset != expected:
                print(f"❌ Offset error: expected {expected}, got {offset} (gap={offset - expected})")
                errors += 1
        prev_offset = offset
        prev_size = len(data)
    if errors == 0:
        print("✅ All offsets are continuous")
    else:
        print(f"⚠️ {errors} offset continuity issues found")
    return errors

def compare_per_block(sorted_blocks, original, handle_endian=False):
    print("\n🔍 Per-block mismatch check…")
    total_errors = 0
    for offset, data in sorted_blocks:
        if handle_endian:
            swapped = bytearray()
            for i in range(0, len(data)-1, 2):
                swapped += data[i:i+2][::-1]
            if len(data) % 2:
                swapped += data[-1:]
            compare_data = swapped
        else:
            compare_data = data

        end = offset + len(compare_data)
        if end > len(original):
            print(f"❌ Block @ {offset}: exceeds source size")
            total_errors += 1
            continue

        orig_slice = original[offset:end]
        if compare_data != orig_slice:
            total_errors += 1
            print(f"❌ Block mismatch @ offset {offset}:")
            print(f"   - Logged block: {compare_data.hex()}")
            print(f"   - Source block: {orig_slice.hex()}")
            diff_count = 0
            for i, (a, b) in enumerate(zip(compare_data, orig_slice)):
                if a != b:
                    print(f"     byte +0x{i:02X}: log={a:02X} / src={b:02X}")
                    diff_count += 1
                    if diff_count >= 16:
                        print("     ... (more differences omitted)")
                        break
    if total_errors == 0:
        print("✅ All blocks match the source file")
    else:
        print(f"⚠️ {total_errors} blocks had mismatches")
    return total_errors

def rebuild_image(sorted_blocks):
    total_size = max(offset + len(data) for offset, data in sorted_blocks)
    buffer = bytearray([0xFF] * total_size)
    for offset, data in sorted_blocks:
        buffer[offset:offset+len(data)] = data
    return bytes(buffer)

def compare_final(original, rebuilt):
    print("\n🔎 Final full-image comparison…")
    if len(original) != len(rebuilt):
        print(f"❌ Size mismatch: source={len(original)} / rebuilt={len(rebuilt)}")
        return 1
    diffs = sum(bool(a != b)
            for a, b in zip(original, rebuilt))
    if diffs == 0:
        print("✅ Final image is a PERFECT MATCH")
        return 0
    else:
        print(f"❌ Final image differs in {diffs} bytes")
        return diffs

# -------------------------
# Main
# -------------------------
def main():
    parser = argparse.ArgumentParser(description="OTA validator from Wireshark JSON + trace log")
    parser.add_argument("--wireshark-json", help="Wireshark JSON log file with OTA blocks")
    parser.add_argument("--trace-log", help="Tracing log file (Seq/Offset/Size/Data)")
    parser.add_argument("--source", required=True, help="Original OTA firmware file")
    parser.add_argument("--output", help="Write rebuilt image to file")
    parser.add_argument("--handle-endian", action="store_true", help="Swap every 2 bytes in logged blocks before comparison")
    parser.add_argument("--first-block-only", action="store_true", help="Compare/rebuild only the first block")
    parser.add_argument("--src-addr", type=lambda x: int(x,0), help="Filter Wireshark blocks by source network address (hex or decimal)")
    parser.add_argument("--check-offsets", dest="check_offsets", action="store_true")
    parser.add_argument("--no-check-offsets", dest="check_offsets", action="store_false")
    parser.set_defaults(check_offsets=True)
    parser.add_argument("--check-blocks", dest="check_blocks", action="store_true")
    parser.add_argument("--no-check-blocks", dest="check_blocks", action="store_false")
    parser.set_defaults(check_blocks=True)
    parser.add_argument("--check-final", dest="check_final", action="store_true")
    parser.add_argument("--no-check-final", dest="check_final", action="store_false")
    parser.set_defaults(check_final=True)
    parser.add_argument("--rebuild", dest="rebuild", action="store_true")
    parser.add_argument("--no-rebuild", dest="rebuild", action="store_false")
    parser.set_defaults(rebuild=True)
    args = parser.parse_args()

    ws_blocks = parse_wireshark_json(args.wireshark_json, first_block_only=args.first_block_only, src_addr=args.src_addr) if args.wireshark_json else {}
    trace_blocks = parse_trace_log(args.trace_log, first_block_only=args.first_block_only) if args.trace_log else {}

    if not ws_blocks and not trace_blocks:
        print("[WARN] No blocks found from any source. Exiting.")
        return

    # Merge blocks, trace log has priority
    sorted_blocks = merge_blocks(ws_blocks, trace_blocks)

    original = Path(args.source).read_bytes()

    if args.check_offsets:
        check_offset_continuity(sorted_blocks)
    if args.check_blocks:
        compare_per_block(sorted_blocks, original, handle_endian=args.handle_endian)
    rebuilt = None
    if args.rebuild:
        print("\n🔧 Rebuilding full firmware image…")
        rebuilt = rebuild_image(sorted_blocks)
        print(f" → Size: {len(rebuilt)} bytes")
        if args.output:
            Path(args.output).write_bytes(rebuilt)
            print(f" → Output saved to {args.output}")
    if args.check_final:
        if rebuilt is None:
            print("\n[ERROR] Rebuild is disabled but --check-final was requested.")
            return
        compare_final(original, rebuilt)

if __name__ == "__main__":
    main()
