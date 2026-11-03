#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Zigbee/zclDecoders.py - Image Page Request (OTA cluster 0x0019, command 0x04)

Coverage:
  - an Image Page Request is turned into an 8502 message
  - it logs at Debug level only: a device downloading with page requests sends
    one per page, about a thousand per upgrade (Legrand NLV, 2026-10-26)
  - the Debug lines name the 8502 builder

Zigbee.zclDecoders imports the real Modules.* package, which conflicts with the
stubs tests/conftest.py installs for the rest of the session. The checks are
therefore executed in a subprocess, fully isolated from the pytest session.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Image Page Request of a Legrand NLV: Field Control 00, manufacturer 0x1021, image type 0x0013,
# file version 0x003F45FF, offset 0x00003D46, max data size 64, page size 256, spacing 200 ms
PAGE_REQUEST = "0021101300ff453f00463d0000400001c800"
FRAME = "0180020044ff0001040019010102d8410200000141040021101300ff453f00463d0000400001c800ec03"


@pytest.fixture(scope="module")
def decoded():
    snippet = textwrap.dedent(
        """
        import json, sys, types
        for name in ("Domoticz", "DomoticzEx"):
            sys.modules[name] = types.ModuleType(name)
        import Zigbee.zclDecoders as decoders

        frame, data = sys.argv[1], sys.argv[2]

        class Log:
            def __init__(self):
                self.calls = []

            def logging(self, module, logType, message, nwkid=None, context=None):
                self.calls.append({"level": logType, "message": message})

        plugin = types.SimpleNamespace(log=Log())
        returned = decoders.buildframe_for_cluster_0019(plugin, "04", frame, "41", "d841", "01", "01", "0019", data)
        print(json.dumps({"returned": returned, "logs": plugin.log.calls}))
        """
    )
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, FRAME, PAGE_REQUEST],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout)


def test_page_request_becomes_an_8502_message(decoded):
    # encapsulated plugin frame: 01 | message type 8502 | ...
    assert decoded["returned"].startswith("018502"), decoded["returned"]


def test_page_request_logs_at_debug_level_only(decoded):
    assert decoded["logs"], "the decoder logs nothing at all"
    assert {call["level"] for call in decoded["logs"]} == {"Debug"}, decoded["logs"]


def test_debug_lines_name_the_8502_builder(decoded):
    assert all("buildframe_for_cluster_8503" not in call["message"] for call in decoded["logs"]), decoded["logs"]
