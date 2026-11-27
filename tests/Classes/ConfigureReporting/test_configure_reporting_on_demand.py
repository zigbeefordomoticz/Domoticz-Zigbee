#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_configure_reporting_on_demand.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"Send reporting again" (WebUI Tools > Binding / Reporting, GET cfgrpt-ondemand) on a
battery device sent nothing: the request went through the batch mode of the heartbeat,
which skips the devices which are not main powered. It must now build the Configure
Reporting frames, for a battery device and for a main powered one, whatever the device
last reported.

Runs in a subprocess, with the real Modules.tools: the conftest stubs of the session would
hide the checks under test.

Run with:
    python -m pytest tests/Classes/ConfigureReporting/test_configure_reporting_on_demand.py -v
"""

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]

SCRIPT = r"""
import json, sys, types
from unittest.mock import MagicMock

for name in ("Domoticz", "DomoticzEx"):
    sys.modules[name] = MagicMock()

import Classes.ConfigureReporting as CR
import Classes.WebServer.rest_CfgReporting as REST

case = json.loads(sys.argv[1])
sent, bound = [], []
CR.zcl_configure_reporting_requestv2 = lambda self, key, epin, epout, cluster, d, ms, m, records, ack: (sent.append([epout, cluster, records]), "01")[1]
CR.bindDevice = lambda self, ieee, ep, cluster: bound.append([ep, cluster])
CR.is_ack_tobe_disabled = lambda self, key: False

cr = object.__new__(CR.ConfigureReporting)
cr.zigbee_communication = "zigpy"
cr.log = MagicMock()
cr.busy = case.get("busy", False)
cr.ControllerLink = MagicMock(); cr.ControllerLink.loadTransmit.return_value = 0
cr.FirmwareVersion = None
cr.pluginconf = MagicMock()
cr.pluginconf.pluginConf = {"allowReBindingClusters": 1, "doUnbindBind": 0, "checkConfigurationReporting": 75600, "ConfigureReportingChunk": 3}
cr.DeviceConf = {"SML001": {"bindEp": ["02"], "ConfigureReporting": {}}}
device = {
    "Status": "inDB", "Model": "SML001", "IEEE": "0017880100000001", "ProfileID": "0104", "ZDeviceID": "0107",
    "MacCapa": case["MacCapa"], "PowerSource": case["PowerSource"], "Param": {},
    "Ep": {"01": {"0006": {}}, "02": {"0406": {}, "Type": "Motion"}},
    "ParamConfigureReporting": {"0406": {"Attributes": {"0000": {
        "DataType": "18", "MinInterval": "0000", "MaxInterval": "012c", "TimeOut": "0fff"}}}},
}
device.update(case.get("extra", {}))
cr.ListOfDevices = {"687b": device}

web = types.SimpleNamespace(ControllerData=True, configureReporting=cr, ListOfDevices=cr.ListOfDevices, logging=lambda *a: None)
REST.setupHeadersResponse = lambda *a: {}
REST.prepResponseMessage = lambda *a: {"Data": None}
response = REST.rest_cfgrpt_ondemand(web, "GET", None, ["687b"])
print("RESULT" + json.dumps({"sent": sent, "bound": bound, "data": response["Data"], "store": dict(device.get("ConfigureReporting", {}))}))
"""

BATTERY = {"MacCapa": "80", "PowerSource": "Battery"}
MAIN = {"MacCapa": "8e", "PowerSource": "Main"}

RECORD = {"Attribute": "0000", "DataType": "18", "minInter": "0000", "maxInter": "012c", "timeOut": "0fff"}


def run(case):
    out = subprocess.run(
        [sys.executable, "-B", "-c", SCRIPT, json.dumps(case)], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.split("RESULT", 1)[1])


@pytest.mark.parametrize(
    "extra",
    [
        {},  # after "Reporting back to defaults", as in the field log
        {"ConfigureReporting": {"Ep": {"02": {"0406": {"TimeStamp": 0, "iSQN": {}, "Attributes": {"0000": "00"}, "ZigateRequest": {}}}}}},
        {"Health": "Not Reachable"},  # a sleeping device: the user wakes it up and asks
    ],
    ids=["no-record", "already-configured", "not-reachable"],
)
def test_battery_device_is_sent_its_reporting(extra):
    result = run({**BATTERY, "extra": extra})
    assert result["sent"] == [["02", "0406", [RECORD]]]
    assert result["bound"] == []  # no extra frame for a device awake a few seconds


def test_main_powered_device_is_sent_its_reporting_even_when_it_matches():
    result = run({
        **MAIN,
        "extra": {
            "ConfigureReporting": {"Ep": {"02": {"0406": {
                "TimeStamp": 9999999999, "iSQN": {}, "Attributes": {"0000": "00"}, "ZigateRequest": {},
                "MismatchRetry": {"Count": 2, "Reported": True}}}}},
            "ReadConfigureReporting": {"TimeStamp": 9999999999, "Ep": {"02": {"0406": {"0000": {
                "Status": "00", "DataType": "18", "MinInterval": "0000", "MaxInterval": "012c"}}}}},
        },
    })
    assert result["sent"] == [["02", "0406", [RECORD]]]
    assert result["bound"] == [["02", "0406"]]
    assert "MismatchRetry" not in result["store"]["Ep"]["02"]["0406"]


def test_main_powered_device_is_left_to_the_heartbeat_when_busy():
    result = run({**MAIN, "busy": True, "extra": {"ConfigureReporting": {"Ep": {}}}})
    assert result["sent"] == []
    assert result["store"] == {}  # the heartbeat sends it as soon as it finds no record
