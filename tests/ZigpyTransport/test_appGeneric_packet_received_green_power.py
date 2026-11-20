#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the Green Power routing in AppGeneric.packet_received().

Green Power frames tunneled by a proxy, and the Device_annce of a GPD alias,
go to zigpy only: they must never reach the plugin decoder. Every other
frame keeps its routing, checked here for the frames next to them (non
tunnel GP cluster traffic, a real Device_annce, ZCL).

Driven against a fake app whose base class records packet_received() calls,
so that `super(type(self), self).packet_received()` resolves to it as it
resolves to zigpy's ControllerApplication.packet_received() with the real
radio libraries. Packets are real zigpy ZigbeePacket objects.

Importing AppGeneric pulls in Classes.ZigpyTransport.Transport and
Classes.ZigateTransport.sqnMgmt, which tests/conftest.py stubs for the rest
of the session. Each scenario therefore runs in a subprocess, as in
test_appGeneric_initialize.py.
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

GP_ALIAS = 0x5A3C
GP_EP = 0xF2
PROFILE_GP = 0xA1E0
PROFILE_ZHA = 0x0104
CLUSTER_GP = 0x0021
DEVICE_ANNCE = 0x0013

# ZCL header: cluster specific, client to server, disable default response
GP_NOTIFICATION = "110500" + "00" * 10
GP_COMMISSIONING_NOTIFICATION = "110504" + "00" * 10
# ZCL header: global command, Report Attributes
GP_REPORT_ATTRIBUTES = "18050a" + "00" * 4
ZCL_ON_OFF_REPORT = "18070a00001001"

ALIAS_IEEE = "ff" * 8
REAL_IEEE = "0102030405060708"

HARNESS = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import zigpy.types as t

    import Classes.ZigpyTransport.AppGeneric as AG

    sc = json.loads(sys.argv[1])
    if sc.get("no_tunneling"):
        AG.zgp_tunneling = None

    class Log:
        def logging(self, category, level, message, *args, **kwargs):
            pass

    class RadioControllerApplication:
        # Stands in for zigpy.application.ControllerApplication.packet_received()
        def packet_received(self, packet):
            self.upstream.append(packet.cluster_id)

    class FakeApp(RadioControllerApplication):
        def __init__(self):
            self.upstream = []
            self.plugin_frames = []
            self.log = Log()
            self.pluginconf = types.SimpleNamespace(pluginConf={})
            self.captureRxFrame = None
            self.callBackFunction = self.plugin_frames.append

    packet = t.ZigbeePacket(
        src=t.AddrModeAddress(addr_mode=t.AddrMode.NWK, address=t.NWK(sc["src"])),
        src_ep=sc["src_ep"],
        dst=t.AddrModeAddress(addr_mode=t.AddrMode.NWK, address=t.NWK(0x0000)),
        dst_ep=sc["dst_ep"],
        profile_id=sc["profile"],
        cluster_id=sc["cluster"],
        data=t.SerializableBytes(bytes.fromhex(sc["data"])),
        lqi=200,
    )

    app = FakeApp()
    AG.packet_received(app, packet)
    print("RESULT=" + json.dumps({"upstream": app.upstream, "plugin_frames": len(app.plugin_frames)}))
    """
)


def _run(**scenario):
    proc = subprocess.run(  # nosec B603
        [sys.executable, "-c", HARNESS, json.dumps(scenario)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    line = next(ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT="))
    return json.loads(line[len("RESULT="):])


def _gp_frame(data, **extra):
    return dict(src=GP_ALIAS, src_ep=GP_EP, dst_ep=GP_EP, profile=PROFILE_GP, cluster=CLUSTER_GP, data=data, **extra)


def _device_annce(src, ieee):
    # TSN + NWKAddr (LE) + IEEEAddr (LE) + Capability
    nwk_le = src.to_bytes(2, "little").hex()
    ieee_le = bytes.fromhex(ieee)[::-1].hex()
    return dict(src=src, src_ep=0, dst_ep=0, profile=0, cluster=DEVICE_ANNCE, data="00" + nwk_le + ieee_le + "8e")


class TestGreenPowerTunnels:

    def test_notification_goes_to_zigpy_only(self):
        result = _run(**_gp_frame(GP_NOTIFICATION))
        assert result == {"upstream": [CLUSTER_GP], "plugin_frames": 0}

    def test_commissioning_notification_goes_to_zigpy_only(self):
        result = _run(**_gp_frame(GP_COMMISSIONING_NOTIFICATION))
        assert result == {"upstream": [CLUSTER_GP], "plugin_frames": 0}

    def test_other_gp_cluster_traffic_keeps_its_routing(self):
        # Not a tunnel: plugin frame, and upstream as for any non ZHA profile
        result = _run(**_gp_frame(GP_REPORT_ATTRIBUTES))
        assert result == {"upstream": [CLUSTER_GP], "plugin_frames": 1}

    def test_zigpy_without_tunneling_keeps_the_old_routing(self):
        result = _run(**_gp_frame(GP_NOTIFICATION, no_tunneling=True))
        assert result == {"upstream": [CLUSTER_GP], "plugin_frames": 1}


class TestGreenPowerAliasAnnouncement:

    def test_alias_announcement_goes_to_zigpy_only(self):
        result = _run(**_device_annce(GP_ALIAS, ALIAS_IEEE))
        assert result == {"upstream": [DEVICE_ANNCE], "plugin_frames": 0}

    def test_alias_announced_by_the_coordinator_goes_to_zigpy_only(self):
        # Radios that cannot send with an alias announce it as the coordinator
        result = _run(**_device_annce(0x0000, ALIAS_IEEE))
        assert result == {"upstream": [DEVICE_ANNCE], "plugin_frames": 0}

    def test_alias_announcement_dropped_without_tunneling(self):
        result = _run(no_tunneling=True, **_device_annce(GP_ALIAS, ALIAS_IEEE))
        assert result == {"upstream": [DEVICE_ANNCE], "plugin_frames": 0}

    def test_real_announcement_keeps_its_routing(self):
        result = _run(**_device_annce(0x1234, REAL_IEEE))
        assert result == {"upstream": [DEVICE_ANNCE], "plugin_frames": 1}


class TestOtherFrames:

    def test_zcl_from_a_device_goes_to_the_plugin_only(self):
        result = _run(src=0x1234, src_ep=1, dst_ep=1, profile=PROFILE_ZHA, cluster=0x0006, data=ZCL_ON_OFF_REPORT)
        assert result == {"upstream": [], "plugin_frames": 1}
