#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_configure_reporting_read_on_demand.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
PUT cfgrpt-read/<nwkid> asks a device how its attributes report, GET cfgrpt-read/<nwkid>
gives what it answered (WebUI Tools > Binding / Reporting).

Runs in a subprocess, with the real Modules.tools, from the REST command to the APS
payload, and from the answer of the device back to the REST command: only the radio is
replaced.

Run with:
    python -m pytest tests/Classes/ConfigureReporting/test_configure_reporting_read_on_demand.py -v
"""

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

SCRIPT = r"""
import json, sys, types
from unittest.mock import MagicMock

for name in ("Domoticz", "DomoticzEx"):
    sys.modules[name] = MagicMock()

import Classes.ConfigureReporting as CR
import Classes.WebServer.dispatcher as dispatcher
import Classes.WebServer.rest_CfgReporting as REST
import Zigbee.zclRawCommands as raw
import Zigbee.zclDecoders as decoders
from Z4D_decoders.z4d_decoder_config_reporting import Decode8122

case = json.loads(sys.argv[1])
frames = []
raw.raw_APS_request = lambda self, nwkid, ep, cluster, profile, payload, **kw: frames.append([ep, cluster, payload])
raw.get_and_inc_ZCL_SQN = lambda self, nwkid: "42"
CR.is_ack_tobe_disabled = lambda self, key: False

ATTR = lambda **kw: {"DataType": "18", "MinInterval": "0001", "MaxInterval": "012C", "TimeOut": "0FFF", **kw}
cr = object.__new__(CR.ConfigureReporting)
cr.zigbee_communication = "zigpy"
cr.log = MagicMock()
cr.busy = True
cr.ControllerLink = MagicMock(); cr.ControllerLink.loadTransmit.return_value = 99
cr.FirmwareVersion = None
cr.pluginconf = types.SimpleNamespace(pluginConf={"ConfigureReportingChunk": 2, "trackZclClustersOut": 0})
cr.DeviceConf = {"SML001": {"bindEp": ["02"], "ConfigureReporting": {
    "0001": {"Attributes": {"0021": ATTR(DataType="20")}},
    "0402": {"Attributes": {"0000": ATTR(DataType="29", Change="0014")}},
    "0406": {"Attributes": {"0000": ATTR(), "0030": ATTR(ManufSpecific="100b")}},
    "0500": {"Attributes": {"0000": ATTR()}},
}}}
device = {
    "Status": "inDB", "Model": "SML001", "IEEE": "0017880100000001", "ProfileID": "0104", "ZDeviceID": "0107",
    "MacCapa": "80", "PowerSource": "Battery", "Health": "Not Reachable", "Param": {},
    "Ep": {"01": {"0406": {}}, "02": {"0406": {}, "0402": {}, "0001": {}, "Type": "Motion"}},
}
device.update(case.get("extra", {}))
cr.ListOfDevices = {"0000": {}, "687b": device}

log = []
web = types.SimpleNamespace(
    configureReporting=cr if case.get("ready", True) else None, ListOfDevices=cr.ListOfDevices, REST_COMMANDS={},
    logging=lambda level, message: log.append(level), pluginconf=types.SimpleNamespace(pluginConf={}))

def call(verb, *parameters):
    r = REST.rest_cfgrpt_read(web, verb, None, list(parameters))
    return [r["Status"], json.loads(r["Data"])]

out = {"before": call("GET", "687b"), "unknown": [call("PUT", "ffff"), call("GET", "0000"), call("GET")], "put": call("PUT", "687b"), "frames": list(frames), "log": log}

# The device answers: 0402/0000 reports every 60 to 600 s for a change of 50, 0406/0000 has no reporting, 0001/0021 is unsupported
out["untouched"] = "ReadConfigureReporting" not in device
plugin = types.SimpleNamespace(log=MagicMock(), configureReporting=cr)
for cluster, data in (("0402", "00" "00" "0000" "29" "3c00" "5802" "3200"), ("0406", "8b" "00" "0000"), ("0001", "86" "00" "2100")):
    frame = decoders.foundation_cluster_read_configure_reporting_response(plugin, "0" * 40, "42", "687b", "02", "01", cluster, data)
    # encapsulated: 01 + type (4) + len (4) + checksum (2) + payload + lqi (2) + 03
    Decode8122(plugin, {}, frame[12:-4], "ff")
out["after"] = call("GET", "687b")
frames.clear()
out["again"] = call("PUT", "687b"); out["frames_again"] = len(frames)
print("RESULT" + json.dumps(out))
"""


def run(**case):
    out = subprocess.run(
        [sys.executable, "-B", "-c", SCRIPT, json.dumps(case)], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.split("RESULT", 1)[1])


def test_put_asks_for_every_configured_attribute_of_the_bound_endpoint():
    """A sleeping battery device, with no earlier record and a busy plugin, is asked all the same."""
    result = run()
    assert result["put"][0] == "200 OK"
    assert result["put"][1]["Attributes"] == 4
    assert sorted(result["frames"]) == [
        ["02", "0001", "004208" "00" "2100"],
        ["02", "0402", "004208" "00" "0000"],
        ["02", "0406", "004208" "00" "0000"],
        ["02", "0406", "04" "0b10" "4208" "00" "3000"],  # manufacturer specific: a frame of its own
    ]
    assert result["untouched"]  # asking stores nothing: the heartbeat must not see a read in progress


def test_get_gives_what_the_device_answered():
    result = run()
    assert result["before"] == ["200 OK", {"TimeStamp": None, "Records": []}]

    status, data = result["after"]
    assert status == "200 OK"
    assert data["TimeStamp"] > 0
    records = {(r["Ep"], r["ClusterId"], r["Attribute"]): r for r in data["Records"]}
    assert set(records) == {("02", "0402", "0000"), ("02", "0406", "0000"), ("02", "0001", "0021")}
    temperature = records["02", "0402", "0000"]
    assert {k: temperature[k] for k in ("Status", "DataType", "MinInterval", "MaxInterval", "Change")} == {
        "Status": "00", "DataType": "29", "MinInterval": "003c", "MaxInterval": "0258", "Change": "0032"}
    assert records["02", "0406", "0000"]["Status"] == "8b"
    assert "MinInterval" not in records["02", "0406", "0000"]
    assert records["02", "0001", "0021"]["Status"] == "86"


def test_an_attribute_no_longer_configured_is_still_read():
    result = run(extra={
        "ReadConfigureReporting": {"TimeStamp": 1, "Ep": {"02": {"0402": {"0003": {"Status": "86", "TimeStamp": 1}}}}}})
    assert ["02", "0402", "004208" "00" "0000" "00" "0300"] in result["frames"]


def test_requests_are_cut_into_chunks():
    result = run(extra={"ReadConfigureReporting": {"Ep": {"02": {"0402": {"0003": {}, "0004": {}}}}}})
    assert [f for f in result["frames"] if f[1] == "0402"] == [
        ["02", "0402", "004208" "00" "0000" "00" "0300"],
        ["02", "0402", "004208" "00" "0400"],
    ]


def test_reset_record_is_an_empty_table():
    result = run(extra={"ReadConfigureReporting": {}})
    assert result["before"] == ["200 OK", {"TimeStamp": None, "Records": []}]


def test_unknown_device_is_refused_without_a_domoticz_error():
    result = run()
    assert result["unknown"] == [["404 NOT FOUND", {"Error": "UNKNOWN_DEVICE"}]] * 3
    assert "Error" not in result["log"]


def test_not_ready():
    assert run(ready=False)["put"] == ["503 SERVICE UNAVAILABLE", {"Error": "NOT_READY"}]


def test_route_is_declared():
    source = (ROOT / "Classes/WebServer/dispatcher.py").read_text(encoding="utf-8")
    assert '{"Name": "cfgrpt-read", "Verbs": {"GET", "PUT"}, "function": self.rest_cfgrpt_read}' in source
    assert "rest_cfgrpt_read)" in (ROOT / "Classes/WebServer/WebServer.py").read_text(encoding="utf-8")
