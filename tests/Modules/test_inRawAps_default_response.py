#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A ZCL Default Response (general command 0x0b) from a device with no manufacturer
handler in Modules/inRawAps.py used to be logged as
"inRawAps ... not processed !!!" on every command sent to it.

Field log, Profalux blind answering a Move to Level (0x00) with SUCCESS:
    inRawAps a864/01 Cluster 0008 Manuf: 1110/Profalux Command: 0b Data: 0000 Payload: 081c0b0000 not processed !!!

Modules.inRawAps imports the real Modules.* package, which conflicts with the
stubs tests/conftest.py installs for the rest of the session. The checks are
therefore executed in a subprocess, fully isolated from the pytest session.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.readAttributes  # noqa: F401  (breaks the Modules.domoMaj <-> Modules.tuya import cycle)
    import Modules.inRawAps as inrawaps

    class Plugin:
        def __init__(self, manufacturer, manufacturer_name):
            self.ListOfDevices = {
                "a864": {"Model": "MAI-ZTM22C", "Manufacturer": manufacturer, "Manufacturer Name": manufacturer_name}
            }
            self.DeviceConf = {}
            self.log = MagicMock(name="log")

    def run(plugin, global_command, command, data, payload, cluster="0008"):
        inrawaps.inRawAps(plugin, {}, "a864", "01", cluster, "0000", "01", "1c", global_command, None, command, data, payload)
        return [[c.args[1], c.args[2]] for c in plugin.log.logging.call_args_list if c.args[0] == "inRawAPS"]
    """
)


def _run(snippet):
    """Execute `snippet` against the real (unstubbed) plugin modules; it prints a JSON result."""
    result = subprocess.run(  # nosec B603
        [sys.executable, "-B", "-c", PREAMBLE + textwrap.dedent(snippet)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


def _not_processed(logs):
    return [msg for _level, msg in logs if "not processed" in msg]


def test_profalux_default_response_success_is_debug_only():
    logs = _run(
        """
        print(json.dumps(run(Plugin("1110", "Profalux"), True, "0b", "0000", "081c0b0000")))
        """
    )
    assert _not_processed(logs) == []
    default_response = [entry for entry in logs if "Default Response" in entry[1]]
    assert len(default_response) == 1
    level, msg = default_response[0]
    assert level == "Debug"
    assert "command 0x00" in msg
    assert "status 0x00" in msg


def test_default_response_failure_status_is_logged():
    logs = _run(
        """
        print(json.dumps(run(Plugin("1110", "Profalux"), True, "0b", "1086", "081c0b1086")))
        """
    )
    assert _not_processed(logs) == []
    assert [level for level, msg in logs if "Default Response" in msg] == ["Log"]
    assert any("command 0x10" in msg and "status 0x86" in msg for _level, msg in logs)


def test_unhandled_cluster_command_still_reported():
    # Cluster-specific frame (FCF 0x19), not a Default Response: unchanged behaviour.
    logs = _run(
        """
        print(json.dumps(run(Plugin("1110", "Profalux"), False, "0b", "0000", "191c0b0000")))
        """
    )
    assert len(_not_processed(logs)) == 1


def test_manufacturer_handler_still_receives_default_response():
    # A manufacturer with a handler keeps receiving every frame, Default Responses included.
    called = _run(
        """
        handler = MagicMock(name="ikeaReadRawAPS")
        inrawaps.CALLBACK_TABLE["117c"] = handler
        logs = run(Plugin("117c", "IKEA of Sweden"), True, "0b", "0000", "081c0b0000")
        assert not [msg for _level, msg in logs if "not processed" in msg or "Default Response" in msg], logs
        print(json.dumps(handler.call_count))
        """
    )
    assert called == 1
