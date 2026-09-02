#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Regression coverage for the "Interface Error 0 / Unknown Error" reported by the
WebUI when starting a Network Topology (or Network Energy) scan on a zigpy
coordinator.

zigpy coordinators always run with ControllerInRawMode = True (plugin.py), so
every ZDP request issued by NetworkMap / NetworkEnergy goes through
raw_APS_request() -> zigpy_raw_APS_request() -> device_listening_on_iddle(),
which resolves the certified-device configuration through `self.DeviceConf`.

NetworkMap and ZigpyTopology used to store that dict as `self.DeviceConfig`,
and NetworkEnergy did not carry it at all, so the very first ZDP request of a
scan raised `AttributeError: ... object has no attribute 'DeviceConf'`. The
exception escaped do_rest() up to handle_client(), which closed the socket
without ever sending an HTTP response -- the WebUI then reported HTTP status 0.

These tests pin the attribute name that
Modules.tools_model.get_deviceconf_parameter_value expects, on every object
that is passed as `self` down the raw APS path.

The scan classes import the real Modules.* package, which conflicts with the
stubs tests/conftest.py installs for the rest of the session. The checks are
therefore executed in a subprocess, fully isolated from the pytest session.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

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

    DEVICE_CONF = {"TRADFRI Signal Repeater": {"ReceiveOnIdle": False}}

    class Log:
        def logging(self, *args, **kwargs):
            pass

    def make_network_map():
        from Classes.NetworkMap import NetworkMap
        return NetworkMap(
            "zigpy", {"TopologyV2": 1}, MagicMock(), {"0000": {}}, DEVICE_CONF, {}, 1, Log(), False
        )

    def make_network_energy():
        from Classes.NetworkEnergy import NetworkEnergy
        return NetworkEnergy(
            "zigpy", {}, MagicMock(), {"0000": {}}, DEVICE_CONF, {}, 1, Log(), False
        )
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


@pytest.mark.parametrize("factory", ["make_network_map", "make_network_energy"])
def test_scan_class_exposes_deviceconf(factory):
    """The raw APS path reads self.DeviceConf -- not self.DeviceConfig."""
    assert _run(f"""
        instance = {factory}()
        assert instance.DeviceConf is DEVICE_CONF, "DeviceConf not exposed"
        print("ok")
    """) == "ok"


@pytest.mark.parametrize("factory", ["make_network_map", "make_network_energy"])
def test_device_listening_on_iddle_accepts_scan_class(factory):
    """device_listening_on_iddle() is called with the scan object as `self`."""
    assert _run(f"""
        from Modules.tools_mac_capa import device_listening_on_iddle
        instance = {factory}()
        instance.ListOfDevices["0000"] = {{"Model": "TRADFRI Signal Repeater", "Capability": []}}
        # Must not raise AttributeError on self.DeviceConf
        assert device_listening_on_iddle(instance, "0000") is False
        print("ok")
    """) == "ok"


def test_start_scan_rolls_back_topology_start_time_on_failure():
    """A failing start_scan() must not leave the scan-in-progress marker behind.

    While ListOfDevices["0000"]["TopologyStartTime"] is set,
    remove_entry_from_all_tables() refuses to delete any report and the matching
    report is filtered out of get_list_of_timestamps() -- so a scan that dies on
    its first ZDP request would otherwise make the WebUI report list unusable
    until the next successful scan.
    """
    assert _run("""
        import Classes.NetworkMap as nm

        instance = make_network_map()

        def boom(_self):
            raise RuntimeError("ZDP request failed")

        nm._initNeighbours = boom

        try:
            instance.start_scan()
        except RuntimeError:
            pass
        else:
            raise AssertionError("start_scan() swallowed the failure")

        assert "TopologyStartTime" not in instance.ListOfDevices["0000"], "marker leaked"
        assert instance.NetworkMapPhase() == 0, "scan phase left in progress"
        print("ok")
    """) == "ok"


def test_finish_scan_tolerates_missing_topology_start_time():
    """finish_scan() must not raise KeyError if the marker is already gone."""
    assert _run("""
        import Classes.NetworkMap as nm

        instance = make_network_map()
        instance.pluginconf = type("Conf", (), {"pluginConf": {"TopologyV2": 1}})()
        instance.Neighbours = {}

        # No TopologyStartTime set at all
        nm.finish_scan(instance)
        print("ok")
    """) == "ok"


def test_zigpy_topology_exposes_deviceconf():
    pytest.importorskip("zigpy")
    assert _run("""
        from Classes.ZigpyTopology import ZigpyTopology
        instance = ZigpyTopology(
            "zigpy", {}, MagicMock(), {"0000": {}}, {}, DEVICE_CONF, {}, 1, Log(), False
        )
        assert instance.DeviceConf is DEVICE_CONF, "DeviceConf not exposed"
        print("ok")
    """) == "ok"
