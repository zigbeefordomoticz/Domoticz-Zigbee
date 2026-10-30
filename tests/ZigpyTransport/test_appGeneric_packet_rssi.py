#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for AppGeneric.packet_received() keeping zigpy's Device.rssi in step
with the packet it hands to the plugin.

decode8002 fills RollingRSSI from zigpy's Device.rssi (get_device_rssi()) for
every ZCL frame. zigpy only refreshes Device.rssi in its own packet_received(),
which a ZCL packet from a device never reaches (the plugin owns the response),
so RollingRSSI kept repeating the RSSI of the last ZDO packet.

Each scenario runs in a subprocess, as test_appGeneric_initialize.py does:
importing AppGeneric pulls in modules tests/conftest.py stubs for the session.
The real zigpy package is required to build a genuine ZigbeePacket.
"""

import importlib.util
import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("zigpy") is None, reason="requires the real zigpy package"
)

REPO_ROOT = Path(__file__).resolve().parents[2]

SNIPPET = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import zigpy.types as t

    import Classes.ZigpyTransport.AppGeneric as AG

    scenario = json.loads(sys.argv[1])

    class Log:
        def logging(self, *args, **kwargs):
            pass

    class Upstream:
        # Stands for zigpy's ControllerApplication, reached via super(type(self), self)
        def get_device(self, ieee=None, nwk=None):
            if nwk not in self.devices:
                raise KeyError(nwk)
            return self.devices[nwk]

        def packet_received(self, packet):
            self.upstream_calls += 1

    class FakeApp(Upstream):
        def __init__(self):
            self.log = Log()
            self.pluginconf = types.SimpleNamespace(pluginConf={})
            self.captureRxFrame = None
            self.upstream_calls = 0
            self.devices = {}
            if scenario["known"]:
                self.devices[t.NWK(0x1A2B)] = types.SimpleNamespace(rssi=scenario["stored_rssi"])
            self.rssi_when_queued = []
            self.callBackFunction = self._queue

        def _queue(self, frame):
            dev = self.devices.get(t.NWK(0x1A2B))
            self.rssi_when_queued.append(dev.rssi if dev else "no device")

    packet = t.ZigbeePacket(
        src=t.AddrModeAddress(addr_mode=t.AddrMode.NWK, address=t.NWK(0x1A2B)),
        src_ep=0x01,
        dst=t.AddrModeAddress(addr_mode=t.AddrMode.NWK, address=t.NWK(0x0000)),
        dst_ep=0x01,
        profile_id=scenario["profile"],
        cluster_id=0x0006,
        data=t.SerializableBytes(bytes.fromhex("18010a00001001")),
        lqi=200,
        rssi=scenario["rssi"],
    )

    app = FakeApp()
    AG.packet_received(app, packet)

    dev = app.devices.get(t.NWK(0x1A2B))
    print(json.dumps({
        "rssi_when_queued": app.rssi_when_queued,
        "rssi_after": dev.rssi if dev else None,
        "upstream_calls": app.upstream_calls,
    }))
    """
)

PROFILE_ZHA = 0x0104
PROFILE_OTHER = 0xC25D


def run(rssi, profile=PROFILE_ZHA, stored_rssi=-90, known=True):
    scenario = {"rssi": rssi, "profile": profile, "stored_rssi": stored_rssi, "known": known}
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", SNIPPET, json.dumps(scenario)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_a_zcl_packet_refreshes_the_rssi_before_the_frame_is_queued():
    # The regression: zigpy never sees this packet, so decode8002 read -90
    out = run(rssi=-61)

    assert out["upstream_calls"] == 0
    assert out["rssi_when_queued"] == [-61]
    assert out["rssi_after"] == -61


def test_a_packet_forwarded_upstream_has_its_rssi_set_before_the_frame_is_queued():
    # Upstream is called after the frame is queued, too late for decode8002
    out = run(rssi=-58, profile=PROFILE_OTHER)

    assert out["upstream_calls"] == 1
    assert out["rssi_when_queued"] == [-58]


def test_a_radio_without_rssi_leaves_the_stored_value_alone():
    # zigpy-znp and zigpy-blz deliver rssi=None
    out = run(rssi=None)

    assert out["rssi_when_queued"] == [-90]
    assert out["rssi_after"] == -90


def test_a_device_zigpy_does_not_know_still_gets_its_frame():
    out = run(rssi=-61, known=False)

    assert out["rssi_when_queued"] == ["no device"]
