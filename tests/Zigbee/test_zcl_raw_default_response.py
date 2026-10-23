#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Zigbee/zclRawCommands.py - zcl_raw_default_response()

Coverage:
  - the Default Response sent to an attribute report is Client→Server, with
    Disable Default Response set (ZCL 07-5123 rev 8 - 2.4.1.1.3, 2.4.1.1.4)
  - manufacturer specific: FCF bit and little-endian manufacturer code
  - a command from a client cluster is still answered Server→Client
  - no Default Response to a Default Response

Zigbee.zclRawCommands imports the real Modules.* package, which conflicts with
the stubs tests/conftest.py installs for the rest of the session. The checks
are therefore executed in a subprocess, fully isolated from the pytest session.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import sys, types
    from unittest.mock import MagicMock, patch

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)
    import Zigbee.zclRawCommands as zcl

    def make_plugin():
        p = types.SimpleNamespace()
        p.log = MagicMock()
        p.pluginconf = types.SimpleNamespace(pluginConf={"trackZclClustersOut": False})
        return p

    def send(response_to_command="0a", **kwargs):
        p = make_plugin()
        with patch.object(zcl, "raw_APS_request") as raw_aps, patch.object(zcl, "is_ack_tobe_disabled", return_value=False):
            zcl.zcl_raw_default_response(p, "2082", "01", "04", "fc12", response_to_command, "3c", **kwargs)
        return p, raw_aps
    """
)


def _run(snippet):
    """Execute `snippet` against the real (unstubbed) plugin modules."""
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(snippet)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return result.stdout.strip()


def test_report_is_answered_client_to_server():
    _run(
        """
        p, raw_aps = send(orig_fcf="08")
        raw_aps.assert_called_once()
        # FCF 10 | TSN 3c | Default Response 0b | to command 0a | SUCCESS 00
        assert raw_aps.call_args.args[5] == "103c0b0a00", raw_aps.call_args
        """
    )


def test_manufacturer_specific_report():
    _run(
        """
        p, raw_aps = send(orig_fcf="0c", manufcode="1286")
        # FCF 14 | manufacturer code little endian 8612 | TSN 3c | 0b | 0a | 00
        assert raw_aps.call_args.args[5] == "1486123c0b0a00", raw_aps.call_args
        """
    )


def test_client_command_is_answered_server_to_client():
    _run(
        """
        p, raw_aps = send(response_to_command="02", orig_fcf="01")
        assert raw_aps.call_args.args[5] == "183c0b0200", raw_aps.call_args
        """
    )


def test_no_default_response_to_a_default_response():
    _run(
        """
        p, raw_aps = send(response_to_command="0b", orig_fcf="08")
        raw_aps.assert_not_called()
        """
    )

