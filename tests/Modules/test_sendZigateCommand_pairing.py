#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the pairing flag the plugin puts on each zigpy request (Modules/sendZigateCommand.py).

Coverage:
  - device_is_pairing: PairingInProgress, PairingTime within / beyond PAIRING_SEND_WINDOW, unknown device
  - zigpy_raw_APS_request sends the flag with the RAW-COMMAND

The real Modules.* package conflicts with the stubs tests/conftest.py installs
for the rest of the session. The checks are therefore executed in a subprocess,
fully isolated from the pytest session.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)
    import Modules.sendZigateCommand as szc

    clock = [10000.0]
    szc.time = types.SimpleNamespace(time=lambda: clock[0])

    def plugin(devices):
        p = types.SimpleNamespace()
        p.log = MagicMock()
        p.pluginconf = types.SimpleNamespace(pluginConf={})
        p.ControllerLink = MagicMock()
        p.DeviceConf = {}
        p.ListOfDevices = devices
        return p
    """
)


def _run(body):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(body)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_pairing_in_progress():
    _run(
        """
        assert szc.device_is_pairing(plugin({"abcd": {"PairingInProgress": True}}), "abcd") is True
        assert szc.device_is_pairing(plugin({"abcd": {"PairingInProgress": False}}), "abcd") is False
        assert szc.device_is_pairing(plugin({"abcd": {}}), "abcd") is False
        """
    )


def test_pairing_time_window():
    _run(
        """
        window = szc.PAIRING_SEND_WINDOW
        assert window == 300
        assert szc.device_is_pairing(plugin({"abcd": {"PairingTime": clock[0]}}), "abcd") is True
        assert szc.device_is_pairing(plugin({"abcd": {"PairingTime": clock[0] - window}}), "abcd") is True
        assert szc.device_is_pairing(plugin({"abcd": {"PairingTime": clock[0] - window - 1}}), "abcd") is False
        # Not a time: never taken as pairing
        assert szc.device_is_pairing(plugin({"abcd": {"PairingTime": "x"}}), "abcd") is False
        """
    )


def test_unknown_device_is_not_pairing():
    _run(
        """
        assert szc.device_is_pairing(plugin({}), "abcd") is False
        """
    )


def test_raw_command_carries_the_pairing_flag():
    _run(
        """
        def send(devices):
            p = plugin(devices)
            szc.zigpy_raw_APS_request(p, "abcd", "01", "0500", "0104", "1001021000f0", "01", zigpyzqn="01")
            cmd, data = p.ControllerLink.sendData.call_args.args[:2]
            assert cmd == "RAW-COMMAND"
            return data["Pairing"]

        assert send({"abcd": {"PairingInProgress": True}}) is True
        assert send({"abcd": {"PairingTime": clock[0] - 10}}) is True
        assert send({"abcd": {"PairingTime": clock[0] - 3600}}) is False
        assert send({}) is False
        """
    )
