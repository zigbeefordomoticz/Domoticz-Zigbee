#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Zigbee/zclRawCommands.py - zcl_raw_ota_image_notify()

Coverage:
  - the payload type decides which optional fields follow the query jitter
    (ZCL 07-5123 rev 8 - 11.13.3.1): type 0 carries the query jitter only,
    type 3 adds manufacturer code, image type and file version, little endian
  - the frame is cluster specific, Server→Client, Disable Default Response set

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

    def notify(payload_type):
        p = types.SimpleNamespace()
        p.log = MagicMock()
        p.pluginconf = types.SimpleNamespace(pluginConf={"trackZclClustersOut": False})
        with patch.object(zcl, "raw_APS_request") as raw_aps, patch.object(zcl, "get_and_inc_ZCL_SQN", return_value="3c"):
            zcl.zcl_raw_ota_image_notify(p, "d841", "01", "01", payload_type, "64", "1021", "0013", "003F45FF")
        raw_aps.assert_called_once()
        assert raw_aps.call_args.args[1:5] == ("d841", "01", "0019", "0104"), raw_aps.call_args
        return raw_aps.call_args.args[5]
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


def test_payload_type_0_carries_the_query_jitter_only():
    _run(
        """
        # FCF 09 | TSN 3c | Image Notify 00 | payload type 00 | jitter 64
        assert notify("00") == "093c000064", notify("00")
        """
    )


def test_payload_type_1_adds_the_manufacturer_code():
    _run(
        """
        assert notify("01") == "093c0001642110", notify("01")
        """
    )


def test_payload_type_3_adds_image_type_and_file_version():
    _run(
        """
        # ... | manufacturer 2110 | image type 1300 | file version ff453f00 (little endian)
        assert notify("03") == "093c00036421101300ff453f00", notify("03")
        """
    )
