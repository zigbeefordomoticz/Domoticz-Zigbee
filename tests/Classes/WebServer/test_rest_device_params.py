#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.WebServer.rest_device_params error handling.

A client calling GET /rest-z4d/1/device-param without a NwkId used to be
answered with a Python set literal -- _response["Data"] = {message} -- which
encode_body_to_bytes() serialises through str(), so the caller received
"{'unexpected parameter [] '}" with a 200 OK instead of JSON. The sibling
branch was worse: rest_update_device_param's "missing IEEE or NWKID" case
called the 4-argument helper with 3 arguments and raised TypeError, so that
error was never reported as such.

Every error path now goes through _log_and_return_with_error(self, message,
_response) and comes back as {"BE_Error": message}, which encodes to JSON.

Classes.WebServer.rest_device_params imports the real Modules.* package, which
conflicts with the stubs tests/conftest.py installs for the session, so the
calls run in a subprocess.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

NWKID = "1234"
IEEE = "00124b00224bf1a2"
PARAM = {"Disabled": 0, "PowerOnAfterOffOn": 255}

SNIPPET = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock
    for name in ("Domoticz", "DomoticzEx"):
        mod = types.ModuleType(name)
        mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
        sys.modules[name] = mod

    # Modules.paramDevice pulls in the whole device-module graph, which does not
    # import standalone; sanity_check_of_param is not what is under test here.
    param_device = types.ModuleType("Modules.paramDevice")
    param_device.sanity_check_of_param = MagicMock(name="sanity_check_of_param")
    sys.modules["Modules.paramDevice"] = param_device

    from Classes.WebServer.rest_device_params import rest_device_param
    from Classes.WebServer.sendresponse import encode_body_to_bytes

    NWKID, IEEE, PARAM = sys.argv[2], sys.argv[3], json.loads(sys.argv[4])

    class PluginConf:
        pluginConf = {}

    class Plugin:
        def __init__(self):
            self.pluginconf = PluginConf()
            self.errors = []
            self.IEEE2NWK = {IEEE: NWKID}
            self.ListOfDevices = {NWKID: {"ZDeviceName": "valve", "IEEE": IEEE, "Param": dict(PARAM)}}
        def logging(self, level, message, *args, **kwargs):
            if level == "Error":
                self.errors.append(message)

    CALLS = {
        "get_no_parameter":     ("GET", None, []),
        "get_two_parameters":   ("GET", None, [NWKID, NWKID]),
        "get_unknown_nwkid":    ("GET", None, ["abcd"]),
        "get_unknown_ieee":     ("GET", None, ["00124b00deadbeef"]),
        "get_by_nwkid":         ("GET", None, [NWKID]),
        "get_by_ieee":          ("GET", None, [IEEE]),
        "put_no_nwkid_no_ieee": ("PUT", json.dumps({"Param": PARAM}).encode("utf8"), []),
        "put_no_param":         ("PUT", json.dumps({"NWKID": NWKID}).encode("utf8"), []),
        "put_unknown_nwkid":    ("PUT", json.dumps({"Param": PARAM, "NWKID": "abcd"}).encode("utf8"), []),
        "put_by_nwkid":         ("PUT", json.dumps({"Param": {"Disabled": 1}, "NWKID": NWKID}).encode("utf8"), []),
        "put_by_ieee":          ("PUT", json.dumps({"Param": {"Disabled": 1}, "IEEE": IEEE}).encode("utf8"), []),
    }

    out = {}
    for name in json.loads(sys.argv[1]):
        verb, data, parameters = CALLS[name]
        plugin = Plugin()
        try:
            response = rest_device_param(plugin, verb, data, parameters)
        except Exception as exc:
            out[name] = {"raised": "%s: %s" % (type(exc).__name__, exc)}
            continue
        out[name] = {
            "raised": None,
            "status": response.get("Status"),
            "body": encode_body_to_bytes(response).decode("utf8"),
            "errors": plugin.errors,
            "stored_param": plugin.ListOfDevices[NWKID].get("Param"),
        }
    print(json.dumps(out))
    """
)

ERROR_CASES = {
    "get_no_parameter": "expecting a single NwkId or IEEE",
    "get_two_parameters": "expecting a single NwkId or IEEE",
    "get_unknown_nwkid": "unknown device",
    "get_unknown_ieee": "unknown device",
    "put_no_nwkid_no_ieee": "missing IEEE or NWKID",
    "put_no_param": "unexpected parameter",
    "put_unknown_nwkid": "unknown device",
}
OK_CASES = ["get_by_nwkid", "get_by_ieee", "put_by_nwkid", "put_by_ieee"]


@pytest.fixture(scope="module")
def results():
    names = list(ERROR_CASES) + OK_CASES
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", SNIPPET, json.dumps(names), NWKID, IEEE, json.dumps(PARAM)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout)


@pytest.mark.parametrize("name", list(ERROR_CASES))
def test_error_path_reports_json_and_does_not_raise(results, name):
    got = results[name]

    # The "missing IEEE or NWKID" branch used to raise TypeError on the helper call.
    assert got["raised"] is None

    # The body used to be str(set) -- "{'unexpected parameter [] '}" -- and was not parsable.
    body = json.loads(got["body"])
    assert ERROR_CASES[name] in body["BE_Error"]

    # Exactly one Error logged, carrying the same wording as the body.
    assert got["errors"] == [body["BE_Error"]]


@pytest.mark.parametrize("name", OK_CASES)
def test_nominal_path_is_unchanged(results, name):
    got = results[name]

    assert got["raised"] is None
    assert got["errors"] == []
    json.loads(got["body"])  # a valid body, whatever its shape


def test_get_returns_the_stored_param(results):
    assert json.loads(results["get_by_nwkid"]["body"]) == PARAM
    assert results["get_by_ieee"]["body"] == results["get_by_nwkid"]["body"]


@pytest.mark.parametrize("name", ["put_by_nwkid", "put_by_ieee"])
def test_put_stores_the_param(results, name):
    assert results[name]["stored_param"] == {"Disabled": 1}
