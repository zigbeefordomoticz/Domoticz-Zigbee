#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_configure_reporting_manufacturer_code.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A reporting configuration saved from the WebUI (PUT cfgrpt-ondemand-config) lost the
manufacturer code of its attributes (ManufSpecific): they were then configured as standard
ones.

Runs in a subprocess, with the real Modules.tools, from the REST command to the APS payload:
only the radio is replaced.

Run with:
    python -m pytest tests/Classes/ConfigureReporting/test_configure_reporting_manufacturer_code.py -v
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
import Zigbee.zclRawCommands as raw

case = json.loads(sys.argv[1])
frames = []
raw.raw_APS_request = lambda self, nwkid, ep, cluster, profile, payload, **kw: frames.append([ep, cluster, payload])
raw.get_and_inc_ZCL_SQN = lambda self, nwkid: "42"
CR.is_ack_tobe_disabled = lambda self, key: False

cr = object.__new__(CR.ConfigureReporting)
cr.zigbee_communication = "zigpy"
cr.log = MagicMock()
cr.busy = False
cr.FirmwareVersion = None
cr.pluginconf = types.SimpleNamespace(pluginConf={"ConfigureReportingChunk": 3, "trackZclClustersOut": 0})
certified = {"0201": {"Attributes": {
    "0000": {"DataType": "29", "MinInterval": "003C", "MaxInterval": "0258", "TimeOut": "0FFF", "Change": "0032"},
    "4000": {"DataType": "30", "MinInterval": "0001", "MaxInterval": "FFFE", "TimeOut": "0FFF", "ManufSpecific": "1246"},
}}}
cr.DeviceConf = {"eTRV0100": {"ConfigureReporting": certified}} if case.get("certified", True) else {}
device = {
    "Status": "inDB", "Model": "eTRV0100", "IEEE": "14b457fffe000001", "ProfileID": "0104", "ZDeviceID": "0301",
    "MacCapa": "80", "PowerSource": "Battery", "Param": {}, "Ep": {"01": {"0201": {}}},
}
device.update(case.get("extra", {}))
cr.ListOfDevices = {"5f02": device}
web = types.SimpleNamespace(
    ControllerData=True, configureReporting=cr, ListOfDevices=cr.ListOfDevices, DeviceConf=cr.DeviceConf,
    logging=lambda *a: None, pluginconf=types.SimpleNamespace(pluginConf={}))

before = json.dumps(certified)
if case.get("save", True):
    # As the WebUI does: what GET gave, with one value changed
    clusters = json.loads(REST.rest_cfgrpt_ondemand_with_config(web, "GET", None, ["5f02"])["Data"])
    for attribute in clusters[0]["Attributes"]:
        attribute["Infos"][0]["MinInterval"] = "A"
        if case.get("strip"):
            attribute["Infos"][0].pop("ManufSpecific", None)
    REST.rest_cfgrpt_ondemand_with_config(web, "PUT", json.dumps({"Nwkid": "5f02", "Clusters": clusters}).encode(), [])
CR.configure_reporting_for_one_device(cr, "5f02", False)
print("RESULT" + json.dumps({"frames": frames, "custom": device.get("ParamConfigureReporting"), "certified_kept": before == json.dumps(certified)}))
"""

STANDARD = "10" "42" "06" "00" "0000" "29" "0a00" "5802" "3200"
MANUFACTURER = "14" "4612" "42" "06" "00" "0040" "30" "0a00" "feff"


def run(**case):
    out = subprocess.run(
        [sys.executable, "-B", "-c", SCRIPT, json.dumps(case)], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.split("RESULT", 1)[1])


def custom(**manufacturer):
    """A custom configuration, as saved before (without the manufacturer code) or after the fix."""
    return {"ParamConfigureReporting": {"0201": {"Attributes": {
        "0000": {"DataType": "29", "MinInterval": "000a", "MaxInterval": "0258", "TimeOut": "0fff", "Change": "0032"},
        "4000": {"DataType": "30", "MinInterval": "000a", "MaxInterval": "fffe", "TimeOut": "0fff", **manufacturer},
    }}}}


@pytest.mark.parametrize("strip", [False, True], ids=["code-sent-back", "code-not-sent-back"])
def test_save_keeps_the_manufacturer_code(strip):
    result = run(strip=strip)
    attributes = result["custom"]["0201"]["Attributes"]
    assert attributes["4000"] == {
        "DataType": "30", "MinInterval": "000a", "MaxInterval": "fffe", "TimeOut": "0fff", "ManufSpecific": "1246"}
    assert "ManufSpecific" not in attributes["0000"]
    assert result["frames"] == [["01", "0201", STANDARD], ["01", "0201", MANUFACTURER]]
    assert result["certified_kept"]


def test_configuration_saved_before_the_fix_is_sent_with_the_manufacturer_code():
    result = run(save=False, extra=custom())
    assert result["frames"] == [["01", "0201", STANDARD], ["01", "0201", MANUFACTURER]]


def test_next_save_puts_the_manufacturer_code_back():
    assert run(extra=custom())["custom"]["0201"]["Attributes"]["4000"]["ManufSpecific"] == "1246"


def test_custom_configuration_of_a_model_without_device_configuration():
    result = run(certified=False, extra=custom(ManufSpecific="1246"))
    assert result["custom"]["0201"]["Attributes"]["4000"]["ManufSpecific"] == "1246"
    assert result["frames"] == [["01", "0201", STANDARD], ["01", "0201", MANUFACTURER]]


def test_attribute_without_manufacturer_code_stays_standard():
    result = run(certified=False, save=False, extra=custom())
    assert [f[2][:2] for f in result["frames"]] == ["10"]
