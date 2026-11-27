#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A Tuya sensor that does not apply its SamplingInterval gets it again when it reports,
and before the Default Response.

In the field log (ZNP, NTCHT01, 258 bursts of reports), only the first frame sent back to
the sensor was ever delivered. It used to be the Default Response every time.

Zigbee.zclDecoders imports the real Modules.* package, which conflicts with the stubs
tests/conftest.py installs for the session, so the checks run in a subprocess.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import collections, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)

    # Modules.input cannot be imported on its own: Modules.domoMaj is only reached
    # through a circular import that plugin.py resolves.
    domo_maj = types.ModuleType("Modules.domoMaj")
    domo_maj.__getattr__ = lambda name: MagicMock(name=name)
    sys.modules["Modules.domoMaj"] = domo_maj

    import Modules.input
    import Modules.tuyaTools
    import Zigbee.zclDecoders as decoders
    import Zigbee.zclRawCommands
    from Modules.tuya import tuyaReadRawAPS

    NWKID, MODEL = "5cd2", "NTCHT01-sonde-temp-humi"

    # Start of a burst of reports: battery, then the sampling interval or the probe temperature
    BATTERY = "0d01003002001f0402000400000064"
    PROBE = "0d010033020020010200040000009d"
    INTERVAL_600 = "0d0100b40200176502000400000258"
    INTERVAL_60 = "0d01000b020002650200040000003c"

    sent = []

    def record(self, targetaddr, dest_ep, cluster, profileId, payload, *args, **kwargs):
        # ZCL command: third byte, or fifth when there is a manufacturer code
        command = payload[8:10] if int(payload[:2], 16) & 0x04 else payload[4:6]
        sent.append("default response" if command == "0b" else payload[10:])

    Modules.tuyaTools.raw_APS_request = record
    Zigbee.zclRawCommands.raw_APS_request = record

    def plugin(param, communication="zigpy"):
        p = types.SimpleNamespace()
        p.log = MagicMock()
        p.pluginconf = types.SimpleNamespace(pluginConf=collections.defaultdict(bool))
        p.zigbee_communication = communication
        p.FirmwareVersion = None
        p.tuya_sampling_requests = {}
        p.ControllerLink = MagicMock()
        p.ListOfDevices = {NWKID: {"Model": MODEL, "MacCapa": "80", "Param": param, "Tuya": {}, "Ep": {"01": {"ef00": {}}}}}
        p.DeviceConf = {MODEL: {"TS0601_DP": {
            "65": {"store_tuya_attribute": "sampling_interval", "action_type": "SamplingInterval"},
            "01": {"store_tuya_attribute": "probe"}, "04": {"store_tuya_attribute": "battery"}}}}
        return p

    def receive(p, payload):
        # What the plugin does with an ef00 frame: zcl_decoders, then inRawAPS
        del sent[:]
        decoders.zcl_decoders(p, NWKID, "01", "01", "ef00", payload, "frame")
        out = list(sent)
        tuyaReadRawAPS(p, {}, NWKID, "01", "ef00", "0000", "01", payload)
        return out

    def command(value):
        return lambda payload: payload.endswith("650200" + "04" + "%08x" % value)
    """
)


def run(code):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(code)], cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr


def test_resent_before_the_default_response():
    run("""
        p = plugin({"SamplingInterval": 300})
        assert receive(p, INTERVAL_600) == ["default response"]     # not known yet when the frame comes in
        first, second = receive(p, PROBE)
        assert command(300)(first), first
        assert second == "default response"
        assert receive(p, BATTERY) == ["default response"]          # same burst
    """)


def test_next_burst_then_confirmed():
    run("""
        p = plugin({"SamplingInterval": 60})
        receive(p, INTERVAL_600)
        assert len(receive(p, PROBE)) == 2
        p.tuya_sampling_requests[NWKID]["last"] -= 60
        assert len(receive(p, BATTERY)) == 2
        receive(p, INTERVAL_60)
        p.tuya_sampling_requests.get(NWKID, {})["last"] = 0
        assert receive(p, BATTERY) == ["default response"]
        assert p.tuya_sampling_requests == {}
    """)


def test_other_devices_only_get_the_default_response():
    run("""
        p = plugin({})
        receive(p, INTERVAL_600)
        assert receive(p, PROBE) == ["default response"]
    """)


def test_zigate_is_left_alone():
    run("""
        p = plugin({"SamplingInterval": 300}, communication="native")
        p.ListOfDevices[NWKID]["Tuya"]["sampling_interval"] = "00000258"
        assert decoders.resend_tuya_settings(p, NWKID) is None
        assert sent == []
    """)
