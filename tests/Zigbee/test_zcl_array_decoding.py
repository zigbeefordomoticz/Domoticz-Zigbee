#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Zigbee.zclDecoders.extract_value_size on ZCL Array (0x48) and
Structure (0x4c) attribute values.

Regression: an Array value used to be decoded as "everything up to the end of the
frame", so any attribute following it in the same Read Attributes Response or
Report Attributes frame was swallowed into its value and never decoded (seen on a
Sonoff SWV-ZFE: fc11/501d read back as its 12 bytes + the raw 501c and 501b
records). Arrays of fixed-size elements are now sized from their element type and
element count; structures and arrays of unsized elements keep the legacy behaviour.

Zigbee.zclDecoders imports the real Modules.* package, which conflicts with the
stubs tests/conftest.py installs for the session, so the calls run in a subprocess.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Sonoff SWV-ZFE 0x501d: element type uint8 (0x20), 12 elements (0c00 LE), then the 12 bytes
SWV_501D = "20" + "0c00" + "0002cf02cf000a01000002cf"
# ... followed in the same read response by 501c (LE 1c50) status 00 uint32 0, and 501b likewise
TRAILING = "1c50" + "00" + "23" + "00000000" + "1b50" + "00" + "23" + "00000000"
# attribute 501d, status 00, type 48 as laid out in a read response
PREFIX = "1d50" + "00" + "48"

CASES = {
    # name: (data, idx, dtype, expected (idx, size, value))
    "uint8_array_followed_by_other_attributes": (SWV_501D + TRAILING, 0, "48", (6, 24, "0002cf02cf000a01000002cf")),
    "uint8_array_last_in_frame": (SWV_501D, 0, "48", (6, 24, "0002cf02cf000a01000002cf")),
    "array_at_offset": (PREFIX + SWV_501D + TRAILING, len(PREFIX), "48", (len(PREFIX) + 6, 24, "0002cf02cf000a01000002cf")),
    "uint16_array_uses_element_size": ("21" + "0300" + "0100" + "0200" + "0300" + "ffff", 0, "48", (6, 12, "010002000300")),
    # legacy behaviour: skip element type + low count byte, take the rest
    "count_larger_than_frame_falls_back": ("20" + "ff00" + "0102", 0, "48", (4, 6, "000102")),
    "unsized_elements_fall_back": ("42" + "0100" + "03616263", 0, "48", (4, 10, "0003616263")),
    "structure_keeps_legacy": ("0200" + "10" + "01" + "21" + "3412", 0, "4c", (4, 10, "1001213412")),
}


@pytest.fixture(scope="module")
def results():
    snippet = textwrap.dedent(
        """
        import json, sys, types
        for name in ("Domoticz", "DomoticzEx"):
            sys.modules[name] = types.ModuleType(name)
        from Zigbee.zclDecoders import extract_value_size
        cases = json.loads(sys.argv[1])
        print(json.dumps({name: list(extract_value_size(None, data, idx, dtype)) for name, (data, idx, dtype) in cases.items()}))
        """
    )
    inputs = {name: case[:3] for name, case in CASES.items()}
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, json.dumps(inputs)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout)


@pytest.mark.parametrize("name", list(CASES))
def test_extract_value_size(results, name):
    data, idx, dtype, expected = CASES[name]
    got = tuple(results[name])

    assert got == expected
    # the caller advances by size: the next attribute record must start right after the value
    assert data[got[0] + got[1]:] == (TRAILING if TRAILING in data else data[got[0] + got[1]:])
