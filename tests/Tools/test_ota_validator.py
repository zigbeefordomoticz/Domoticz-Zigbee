#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Tools/ota_validator.py

Coverage:
  - parse_wireshark_json    – valid blocks, size mismatch warning, src_addr filter, first_block_only
  - parse_trace_log         – valid blocks, size mismatch warning, first_block_only
  - merge_blocks            – merging, last-writer-wins, sorted output
  - check_offset_continuity – continuous, gap, single block
  - compare_per_block       – matching, mismatch, endian swap, block exceeds source
  - rebuild_image           – correct size, correct content
  - compare_final           – perfect match, byte diff, size mismatch
"""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "Tools" / "ota_validator.py"

spec = importlib.util.spec_from_file_location("ota_validator", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

parse_wireshark_json    = mod.parse_wireshark_json
parse_trace_log         = mod.parse_trace_log
merge_blocks            = mod.merge_blocks
check_offset_continuity = mod.check_offset_continuity
compare_per_block       = mod.compare_per_block
rebuild_image           = mod.rebuild_image
compare_final           = mod.compare_final


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ws_packet(offset: int, data: bytes, wpan_src: str | None = None) -> dict:
    payload = {
        "zbee_zcl_general.ota.image.data": data.hex(),
        "zbee_zcl_general.ota.file.offset": str(offset),
        "zbee_zcl_general.ota.data_size": str(len(data)),
    }
    layers: dict = {"zbee_zcl": {"Payload": payload}}
    if wpan_src is not None:
        layers["wpan"] = {"wpan.src16": wpan_src}
    return {"_source": {"layers": layers}}


def _write_ws(tmp_path, packets: list) -> Path:
    p = tmp_path / "wireshark.json"
    p.write_text(json.dumps(packets))
    return p


def _write_trace(tmp_path, blocks: list[tuple[int, int, bytes]]) -> Path:
    lines = []
    for seq, (offset, size, data) in enumerate(blocks):
        lines.append(f"Seq:{seq} | Offset:{offset} | Size:{size} | Data:{data.hex()}")
    p = tmp_path / "trace.log"
    p.write_text("\n".join(lines))
    return p


# ---------------------------------------------------------------------------
# parse_wireshark_json
# ---------------------------------------------------------------------------

class TestParseWiresharkJson:
    def test_basic_block(self, tmp_path):
        data = b"\xAA\xBB\xCC"
        f = _write_ws(tmp_path, [_ws_packet(0, data)])
        result = parse_wireshark_json(str(f))
        assert result == {0: data}

    def test_multiple_blocks(self, tmp_path):
        d1, d2 = b"\x01" * 4, b"\x02" * 4
        f = _write_ws(tmp_path, [_ws_packet(0, d1), _ws_packet(4, d2)])
        result = parse_wireshark_json(str(f))
        assert result == {0: d1, 4: d2}

    def test_size_mismatch_warns(self, tmp_path, capsys):
        # Provide fewer bytes than declared size
        pkt = _ws_packet(0, b"\xAA")
        # Tamper the declared size
        pkt["_source"]["layers"]["zbee_zcl"]["Payload"]["zbee_zcl_general.ota.data_size"] = "5"
        f = _write_ws(tmp_path, [pkt])
        parse_wireshark_json(str(f))
        assert "size mismatch" in capsys.readouterr().out

    def test_src_addr_filter(self, tmp_path):
        d1 = b"\xAA" * 2
        d2 = b"\xBB" * 2
        pkts = [
            _ws_packet(0, d1, wpan_src="0x1234"),
            _ws_packet(2, d2, wpan_src="0x5678"),
        ]
        f = _write_ws(tmp_path, pkts)
        result = parse_wireshark_json(str(f), src_addr=0x1234)
        assert 0 in result
        assert 2 not in result

    def test_first_block_only(self, tmp_path):
        pkts = [_ws_packet(0, b"\x01"), _ws_packet(1, b"\x02")]
        f = _write_ws(tmp_path, pkts)
        result = parse_wireshark_json(str(f), first_block_only=True)
        assert list(result.keys()) == [0]

    def test_missing_fields_skipped(self, tmp_path):
        # Packet without OTA fields should be silently ignored
        pkt = {"_source": {"layers": {"zbee_zcl": {"Payload": {}}}}}
        f = _write_ws(tmp_path, [pkt])
        result = parse_wireshark_json(str(f))
        assert result == {}


# ---------------------------------------------------------------------------
# parse_trace_log
# ---------------------------------------------------------------------------

class TestParseTraceLog:
    def test_basic_block(self, tmp_path):
        data = b"\xDE\xAD"
        f = _write_trace(tmp_path, [(0, len(data), data)])
        result = parse_trace_log(str(f))
        assert result == {0: data}

    def test_multiple_blocks(self, tmp_path):
        d1, d2 = b"\x01\x02", b"\x03\x04"
        f = _write_trace(tmp_path, [(0, 2, d1), (2, 2, d2)])
        result = parse_trace_log(str(f))
        assert result == {0: d1, 2: d2}

    def test_size_mismatch_warns(self, tmp_path, capsys):
        data = b"\xAA"
        lines = ["Seq:0 | Offset:0 | Size:5 | Data:aa"]  # declared 5, only 1 byte
        p = tmp_path / "trace.log"
        p.write_text("\n".join(lines))
        parse_trace_log(str(p))
        assert "size mismatch" in capsys.readouterr().out

    def test_first_block_only(self, tmp_path):
        d1, d2 = b"\xAA", b"\xBB"
        f = _write_trace(tmp_path, [(0, 1, d1), (1, 1, d2)])
        result = parse_trace_log(str(f), first_block_only=True)
        assert list(result.keys()) == [0]

    def test_non_matching_lines_ignored(self, tmp_path):
        p = tmp_path / "trace.log"
        p.write_text("Some log line with no OTA data\nAnother irrelevant line\n")
        result = parse_trace_log(str(p))
        assert result == {}


# ---------------------------------------------------------------------------
# merge_blocks
# ---------------------------------------------------------------------------

class TestMergeBlocks:
    def test_single_dict(self):
        blocks = {0: b"\x01", 4: b"\x02"}
        result = merge_blocks(blocks)
        assert result == [(0, b"\x01"), (4, b"\x02")]

    def test_merge_two_dicts(self):
        a = {0: b"\xAA"}
        b = {4: b"\xBB"}
        result = merge_blocks(a, b)
        assert dict(result) == {0: b"\xAA", 4: b"\xBB"}

    def test_later_dict_wins(self):
        a = {0: b"\xAA"}
        b = {0: b"\xBB"}
        result = merge_blocks(a, b)
        assert result[0][1] == b"\xBB"

    def test_sorted_by_offset(self):
        a = {8: b"\x08", 0: b"\x00", 4: b"\x04"}
        result = merge_blocks(a)
        offsets = [o for o, _ in result]
        assert offsets == sorted(offsets)


# ---------------------------------------------------------------------------
# check_offset_continuity
# ---------------------------------------------------------------------------

class TestCheckOffsetContinuity:
    def test_continuous(self, capsys):
        blocks = [(0, b"\x01\x02"), (2, b"\x03\x04")]
        errors = check_offset_continuity(blocks)
        assert errors == 0
        assert "continuous" in capsys.readouterr().out

    def test_gap_detected(self, capsys):
        blocks = [(0, b"\x01\x02"), (5, b"\x03\x04")]  # gap of 3
        errors = check_offset_continuity(blocks)
        assert errors == 1

    def test_single_block_no_error(self, capsys):
        blocks = [(0, b"\xFF" * 16)]
        errors = check_offset_continuity(blocks)
        assert errors == 0


# ---------------------------------------------------------------------------
# compare_per_block
# ---------------------------------------------------------------------------

class TestComparePerBlock:
    def test_all_match(self, capsys):
        original = b"\xAA\xBB\xCC\xDD"
        blocks = [(0, original)]
        errors = compare_per_block(blocks, original)
        assert errors == 0
        assert "match" in capsys.readouterr().out

    def test_mismatch_detected(self, capsys):
        original = b"\xAA\xBB\xCC\xDD"
        blocks = [(0, b"\xFF\xFF\xFF\xFF")]
        errors = compare_per_block(blocks, original)
        assert errors == 1

    def test_block_exceeds_source(self, capsys):
        original = b"\x00" * 4
        blocks = [(2, b"\xFF" * 8)]  # 2+8 > 4
        errors = compare_per_block(blocks, original)
        assert errors == 1

    def test_endian_swap(self, capsys):
        # Build source with swapped pairs so that after our swap it matches
        original = bytes([0xBB, 0xAA, 0xDD, 0xCC])
        logged   = bytes([0xAA, 0xBB, 0xCC, 0xDD])
        blocks = [(0, logged)]
        errors = compare_per_block(blocks, original, handle_endian=True)
        assert errors == 0


# ---------------------------------------------------------------------------
# rebuild_image
# ---------------------------------------------------------------------------

class TestRebuildImage:
    def test_contiguous_blocks(self):
        blocks = [(0, b"\x01\x02"), (2, b"\x03\x04")]
        result = rebuild_image(blocks)
        assert result == b"\x01\x02\x03\x04"

    def test_gap_filled_with_ff(self):
        blocks = [(0, b"\xAA"), (3, b"\xBB")]
        result = rebuild_image(blocks)
        assert result[1] == 0xFF
        assert result[2] == 0xFF
        assert result[3] == 0xBB

    def test_total_size_correct(self):
        blocks = [(0, b"\x00" * 16), (16, b"\xFF" * 16)]
        result = rebuild_image(blocks)
        assert len(result) == 32


# ---------------------------------------------------------------------------
# compare_final
# ---------------------------------------------------------------------------

class TestCompareFinal:
    def test_perfect_match(self, capsys):
        data = b"\xAB" * 32
        diffs = compare_final(data, data)
        assert diffs == 0
        assert "PERFECT" in capsys.readouterr().out

    def test_byte_difference(self, capsys):
        original = b"\xAA" * 32
        rebuilt  = bytearray(original)
        rebuilt[5] = 0xFF
        diffs = compare_final(original, bytes(rebuilt))
        assert diffs == 1

    def test_size_mismatch(self, capsys):
        diffs = compare_final(b"\x00" * 4, b"\x00" * 8)
        assert diffs == 1
        assert "Size mismatch" in capsys.readouterr().out
