#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for WebServer.rest_zigate, the GET /coordinator endpoint.

The WebUI asks for /coordinator as soon as the WebServer is up, which is a few
seconds before the radio has started and the firmware and network details have
been put into ControllerData. The endpoint read every key with
ControllerData[...], so each request in that window raised
KeyError: 'Firmware Version' and logged an error with its traceback.

Importing Classes/WebServer/WebServer.py pulls the real Modules.* package in,
which conflicts with the stubs tests/conftest.py installs for the session, so
the calls run in a subprocess.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

RADIO_STARTED = {
    "Firmware Version": "Branch: 20 Major: 0000 Version: 20240710",
    "IEEE": "00124b00256c1207",
    "Short Address": "0000",
    "Channel": 20,
    "PANID": "1a2b",
    "Extended PANID": "2820484504015e10",
    "Branch Version": "20",
    "Major Version": "0000",
    "Minor Version": "Z-Stack 3.30+ (build 20240710)",
}

CASES = {
    "radio_not_started": {},
    "network_known_firmware_not_yet": {key: RADIO_STARTED[key] for key in ("IEEE", "Short Address", "Channel", "PANID", "Extended PANID")},
    "radio_started": RADIO_STARTED,
}

SNIPPET = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock
    for name in ("Domoticz", "DomoticzEx"):
        mod = types.ModuleType(name)
        mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
        sys.modules[name] = mod

    from Classes.WebServer.WebServer import WebServer

    results = {}
    for name, controller_data in json.loads(sys.argv[2]).items():
        server = types.SimpleNamespace(
            ControllerData=controller_data,
            pluginconf=types.SimpleNamespace(pluginConf={}),
        )
        response = WebServer.rest_zigate(server, "GET", None, [])
        results[name] = {"Status": response["Status"], "Data": json.loads(response["Data"])}

    print(json.dumps(results))
    """
)


@pytest.fixture(scope="module")
def coordinator_results():
    completed = subprocess.run(  # nosec B603
        [sys.executable, "-c", SNIPPET, "run", json.dumps(CASES)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


class TestCoordinatorBeforeTheRadioStarted:
    def test_no_details_yet_answers_with_nulls(self, coordinator_results):
        result = coordinator_results["radio_not_started"]
        assert result["Status"] == "200 OK"
        assert set(result["Data"]) == set(RADIO_STARTED)
        assert all(value is None for value in result["Data"].values())

    def test_no_display_firmware_version_without_a_branch(self, coordinator_results):
        assert "Display Firmware Version" not in coordinator_results["radio_not_started"]["Data"]

    def test_network_details_known_before_the_firmware(self, coordinator_results):
        data = coordinator_results["network_known_firmware_not_yet"]["Data"]
        assert data["Channel"] == 20
        assert data["IEEE"] == "00124b00256c1207"
        assert data["Firmware Version"] is None
        assert "Display Firmware Version" not in data


class TestCoordinatorOnceTheRadioStarted:
    def test_every_detail_is_returned(self, coordinator_results):
        data = coordinator_results["radio_started"]["Data"]
        for key, value in RADIO_STARTED.items():
            assert data[key] == value

    def test_display_firmware_version_follows_the_branch(self, coordinator_results):
        data = coordinator_results["radio_started"]["Data"]
        assert data["Display Firmware Version"] == "Znp - Z-Stack 3.30+ (build 20240710)"
