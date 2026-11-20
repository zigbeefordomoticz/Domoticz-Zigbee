#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.WebServer.WebServer.device_conf_identity, and for the
"DeviceConfIdentity" it adds to GET /zdevice-raw.

A device may report a manufacturer-private ZDeviceID: the CASAIA CPR412-E roller
shutter module reports c412 under profile 0104. Its configuration then states what
the device is to be taken for with a top-level "ZDeviceID" (and "ProfileID"). The
WebUI gets the configured values in "DeviceConfIdentity", on every entry of the list
and beside "Device" on a single-device answer. The reported values stay untouched
in ListOfDevices, and so does ListOfDevices itself.

Classes.WebServer.WebServer imports the real Modules.* package, which conflicts
with the stubs tests/conftest.py installs for the session, so the calls run in
a subprocess.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

DEVICE_CONF = {
    "CPR412-E": {"Ep": {"01": {"0006": "", "0008": "", "Type": "VenetianInverted"}}, "Type": "", "ZDeviceID": "0202"},
    "TRADFRI remote control": {"Ep": {"01": {"0005": ""}}, "Type": "", "ProfileID": "c05e", "ZDeviceID": "0830"},
    "Uppercase": {"ProfileID": "C05E", "ZDeviceID": "010D"},
    "Malformed": {"ProfileID": "104", "ZDeviceID": "0x0202"},
    "NotStrings": {"ProfileID": 260, "ZDeviceID": ["0202"]},
    "NoIdentity": {"Ep": {"01": {"0006": ""}}, "Type": "Switch", "_comment": "documentation only"},
    "Broken": ["not", "a", "dict"],
}

CASES = {
    # name: (DeviceConf, model, expected)
    "zdeviceid_only": (DEVICE_CONF, "CPR412-E", {"ZDeviceID": "0202"}),
    "zdeviceid_and_profileid": (DEVICE_CONF, "TRADFRI remote control", {"ZDeviceID": "0830", "ProfileID": "c05e"}),
    "uppercase_is_lowered": (DEVICE_CONF, "Uppercase", {"ZDeviceID": "010d", "ProfileID": "c05e"}),
    "malformed_values_left_out": (DEVICE_CONF, "Malformed", {}),
    "non_string_values_left_out": (DEVICE_CONF, "NotStrings", {}),
    "model_without_identity": (DEVICE_CONF, "NoIdentity", {}),
    "unknown_model": (DEVICE_CONF, "lumi.unknown", {}),
    "model_not_a_string": (DEVICE_CONF, {}, {}),
    "model_missing": (DEVICE_CONF, None, {}),
    "configuration_not_a_dict": (DEVICE_CONF, "Broken", {}),
    "no_device_conf": (None, "CPR412-E", {}),
}

NWKID = "c1a8"
IEEE = "84fd27fffe5ad6a1"
OTHER_NWKID = "1234"


def _run(snippet, *args):
    proc = subprocess.run(  # nosec B603
        [sys.executable, "-c", textwrap.dedent(snippet), *args],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


PRELUDE = """
import json, sys, types
from unittest.mock import MagicMock
for name in ("Domoticz", "DomoticzEx"):
    mod = types.ModuleType(name)
    mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
    sys.modules[name] = mod
"""


@pytest.fixture(scope="module")
def results():
    return _run(
        PRELUDE + """
from Classes.WebServer.WebServer import device_conf_identity

cases = json.loads(sys.argv[1])
print(json.dumps({name: device_conf_identity(conf, model) for name, (conf, model, _) in cases.items()}))
""",
        json.dumps(CASES),
    )


@pytest.mark.parametrize("name", sorted(CASES))
def test_device_conf_identity(results, name):
    assert results[name] == CASES[name][2]


@pytest.fixture(scope="module")
def answers():
    return _run(
        PRELUDE + """
import Classes.WebServer.WebServer as webserver

# Not under test: the plugin parameters attached to a single-device answer
webserver.get_plugin_parameters = lambda self, filter=False: {"Mode": "zigpy"}

NWKID, IEEE, OTHER_NWKID, DEVICE_CONF = sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4])

class PluginConf:
    pluginConf = {"PluginAnalytics": False}

class Plugin:
    def __init__(self):
        self.pluginconf = PluginConf()
        self.Devices = {1: object()}
        self.DeviceConf = DEVICE_CONF
        self.IEEE2NWK = {IEEE: NWKID}
        self.ListOfDevices = {
            NWKID: {"IEEE": IEEE, "Model": "CPR412-E", "ProfileID": "0104", "ZDeviceID": "c412"},
            OTHER_NWKID: {"IEEE": "00158d0000000000", "Model": {}, "ProfileID": "0104", "ZDeviceID": "0402"},
        }

answers = {}
for name, parameters in (("by_nwkid", [NWKID]), ("by_ieee", [IEEE]), ("list", [])):
    plugin = Plugin()
    answer = json.loads(webserver.WebServer.rest_zDevice_raw(plugin, "GET", None, parameters)["Data"])
    answers[name] = {"answer": answer, "ListOfDevices": plugin.ListOfDevices}
print(json.dumps(answers))
""",
        NWKID, IEEE, OTHER_NWKID, json.dumps(DEVICE_CONF),
    )


@pytest.mark.parametrize("name", ["by_nwkid", "by_ieee"])
def test_single_device_answer_carries_the_configured_identity(answers, name):
    answer = answers[name]["answer"]
    assert answer["DeviceConfIdentity"] == {"ZDeviceID": "0202"}
    # The reported values are served unchanged, and the identity is not a note
    assert answer["Device"]["ZDeviceID"] == "c412"
    assert "DeviceConfIdentity" not in answer["Device"]
    assert "ZDeviceID" not in answer["DeviceConfInfo"]


def test_list_answer_carries_the_configured_identity_per_device(answers):
    by_nwkid = {entry["NwkID"]: entry for entry in answers["list"]["answer"]}
    assert by_nwkid[NWKID]["DeviceConfIdentity"] == {"ZDeviceID": "0202"}
    assert by_nwkid[NWKID]["ZDeviceID"] == "c412"
    # A device without a configuration gets an empty identity, so the WebUI can tell an older plugin apart
    assert by_nwkid[OTHER_NWKID]["DeviceConfIdentity"] == {}


@pytest.mark.parametrize("name", ["by_nwkid", "by_ieee", "list"])
def test_list_of_devices_is_not_modified(answers, name):
    for device in answers[name]["ListOfDevices"].values():
        assert "DeviceConfIdentity" not in device
    assert answers[name]["ListOfDevices"][NWKID]["ZDeviceID"] == "c412"
