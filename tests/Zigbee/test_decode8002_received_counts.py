#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Zigbee/decode8002.py - ReceivedZDO / ReceivedZCL counters

Coverage:
  - a ZDO frame (profile 0x0000) counts in ReceivedZDO, any other profile in ReceivedZCL
  - every frame counts, the same frame received twice counts twice
  - a frame from a NwkId the plugin does not know creates no record
  - a new device record starts both counters at 0

Zigbee.decode8002 imports the real Modules.* package, which conflicts with
the stubs tests/conftest.py installs for the rest of the session. The checks
are therefore executed in a subprocess, fully isolated from the pytest session.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import sys, types
    from unittest.mock import MagicMock, patch

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)
    import Zigbee.decode8002 as d8002

    def make_plugin(*nwkids):
        p = types.SimpleNamespace()
        p.log = MagicMock()
        p.zigbee_communication = "zigpy"
        p.ControllerLink = MagicMock()
        p.ControllerLink.app.get_device_rssi.return_value = None
        p.ListOfDevices = {}
        for nwkid in nwkids:
            Modules.tools.initialize_device_record(p, nwkid)
        return p

    def frame(profile, nwkid, payload="18010a0000"):
        # 8002 frame: status, profile, cluster, src/dst ep, short src, short dst 0000, payload; then LQI
        msg = "00" + profile + "0006" + "01" + "01" + "02" + nwkid + "02" + "0000" + payload
        return "01" + "8002" + "%04x" % (len(msg) // 2) + "00" + msg + "ff" + "03"

    def receive(p, profile, nwkid):
        with patch.object(d8002, "zdp_decoders", side_effect=lambda *a: a[-1]), \\
                patch.object(d8002, "zcl_decoders", side_effect=lambda *a: a[-1]):
            return d8002.decode8002_and_process(p, frame(profile, nwkid))
    """
)


def _run(snippet):
    """Execute `snippet` against the real (unstubbed) plugin modules."""
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(snippet)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return result.stdout.strip()


def test_new_record_starts_at_zero():
    _run(
        """
        p = make_plugin("1234")
        assert p.ListOfDevices["1234"]["ReceivedZDO"] == 0
        assert p.ListOfDevices["1234"]["ReceivedZCL"] == 0
        """
    )


def test_zdo_and_zcl_counted_apart():
    _run(
        """
        p = make_plugin("1234")
        receive(p, "0000", "1234")
        receive(p, "0104", "1234")
        receive(p, "0104", "1234")
        receive(p, "a1e0", "1234")
        assert p.ListOfDevices["1234"]["ReceivedZDO"] == 1, p.ListOfDevices["1234"]
        assert p.ListOfDevices["1234"]["ReceivedZCL"] == 3, p.ListOfDevices["1234"]
        """
    )


def test_record_without_counters_starts_counting():
    _run(
        """
        # The coordinator record ("0000") is created without the default setup
        p = make_plugin()
        p.ListOfDevices["0000"] = {"Status": ""}
        receive(p, "0000", "0000")
        assert p.ListOfDevices["0000"] == {"Status": "", "ReceivedZDO": 1}, p.ListOfDevices["0000"]
        """
    )


def test_unknown_nwkid_creates_no_record():
    _run(
        """
        p = make_plugin("1234")
        with patch.object(d8002, "lookupForIEEE", return_value=False):
            assert receive(p, "0104", "abcd") is None
        receive(p, "0000", "abcd")
        assert list(p.ListOfDevices) == ["1234"], p.ListOfDevices
        """
    )
