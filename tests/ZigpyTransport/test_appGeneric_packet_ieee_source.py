#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for AppGeneric.packet_received() handing the plugin a NWK source
address when the radio reports an IEEE one.

zigpy-deconz maps the firmware's IEEE and NWK_AND_IEEE source modes to
AddrMode.IEEE. The plugin got a 8002 frame with source mode 03 and a 16-digit
address: decode8002 dropped every report as "unknown NwkId", and a
Node_Desc_req was answered to "58e6", the first four digits of the IEEE
(espressif/arduino-esp32#12520, ConBee III + ESP32 ZBOSS end device).

Each scenario runs in a subprocess, as test_appGeneric_packet_rssi.py does:
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

IEEE = "58e6c5fffe16073c"
NWK = 0x5E39
# Report Attributes, 0x0402/0x0000 int16 0x0960 (24.00 °C)
TEMPERATURE_REPORT = "08000a0000296009"

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
    ieee = t.EUI64.convert(scenario["ieee"])

    class Log:
        def logging(self, *args, **kwargs):
            pass

    class Upstream:
        # Stands for zigpy's ControllerApplication, reached via super(type(self), self)
        def get_device(self, ieee=None, nwk=None):
            key = ieee if ieee is not None else nwk
            if key not in self.devices:
                raise KeyError(key)
            return self.devices[key]

        def packet_received(self, packet):
            self.upstream_src.append(packet.src.addr_mode.name)

    class FakeApp(Upstream):
        def __init__(self):
            self.log = Log()
            self.pluginconf = types.SimpleNamespace(pluginConf={})
            self.captureRxFrame = None
            self.upstream_src = []
            self.devices = {}
            if scenario["in_zigpy"]:
                self.devices[ieee] = types.SimpleNamespace(nwk=t.NWK(scenario["nwk"]), rssi=None)
            self.callBackGetDevice = self._plugin_get_device
            self.frames = []
            self.callBackFunction = self.frames.append

        def _plugin_get_device(self, ieee_str, nwk_str):
            # plugin.py zigpy_get_device(): (nwk, ieee) as ints, or None
            if scenario["in_plugin"] and ieee_str == scenario["ieee"]:
                return scenario["nwk"], int(ieee_str, 16)
            return None

    src = (
        t.AddrModeAddress(addr_mode=t.AddrMode.IEEE, address=ieee)
        if scenario["src_mode"] == "ieee"
        else t.AddrModeAddress(addr_mode=t.AddrMode.NWK, address=t.NWK(scenario["nwk"]))
    )
    packet = t.ZigbeePacket(
        src=src,
        src_ep=scenario["src_ep"],
        dst=t.AddrModeAddress(addr_mode=t.AddrMode.NWK, address=t.NWK(0x0000)),
        dst_ep=scenario["dst_ep"],
        profile_id=scenario["profile"],
        cluster_id=scenario["cluster"],
        data=t.SerializableBytes(bytes.fromhex(scenario["data"])),
        lqi=203,
        rssi=-60,
    )

    app = FakeApp()
    AG.packet_received(app, packet)
    print(json.dumps({"frames": app.frames, "upstream_src": app.upstream_src}))
    """
)


def run(src_mode="ieee", in_zigpy=True, in_plugin=False, profile=0x0104, cluster=0x0402, src_ep=0x0A, dst_ep=0x01, data=TEMPERATURE_REPORT):
    scenario = {
        "ieee": IEEE, "nwk": NWK, "src_mode": src_mode, "in_zigpy": in_zigpy, "in_plugin": in_plugin,
        "profile": profile, "cluster": cluster, "src_ep": src_ep, "dst_ep": dst_ep, "data": data,
    }
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", SNIPPET, json.dumps(scenario)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def source_of(frame):
    """(addr mode, address) of a plugin 8002 frame, as decode8002 reads them."""
    msg = frame[12:-4]
    mode = msg[14:16]
    return mode, msg[16:20] if mode == "02" else msg[16:32]


def test_a_report_from_an_ieee_source_reaches_the_plugin_with_the_nwk_address():
    out = run()

    assert len(out["frames"]) == 1
    assert source_of(out["frames"][0]) == ("02", "%04x" % NWK)
    assert out["frames"][0][12:-4].endswith(TEMPERATURE_REPORT)


def test_the_nwk_address_comes_from_the_plugin_when_zigpy_does_not_know_the_device():
    out = run(in_zigpy=False, in_plugin=True)

    assert source_of(out["frames"][0]) == ("02", "%04x" % NWK)


def test_an_unknown_ieee_source_is_passed_on_unchanged():
    out = run(in_zigpy=False, in_plugin=False)

    assert source_of(out["frames"][0]) == ("03", IEEE)


def test_a_zdo_request_from_an_ieee_source_carries_the_nwk_address():
    # Node_Desc_req to the coordinator: TSN 01, NWKAddrOfInterest 0x0000
    out = run(profile=0x0000, cluster=0x0002, src_ep=0x00, dst_ep=0x00, data="010000")

    assert source_of(out["frames"][0]) == ("02", "%04x" % NWK)
    assert out["upstream_src"] == ["NWK"]


def test_a_nwk_source_is_left_alone():
    out = run(src_mode="nwk")

    assert source_of(out["frames"][0]) == ("02", "%04x" % NWK)
