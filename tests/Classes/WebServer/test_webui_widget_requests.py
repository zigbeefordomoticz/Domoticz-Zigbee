#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Widgets (re)created from the WebUI: from the REST handler to the Domoticz widget.

Field case (easydomoticz forum t=14845, 9.1.010): "recreate widgets" was accepted and
logged as queued, and nothing followed. The handlers run with the WebServer as self and
the heartbeat with the plugin, and each had a queue of its own.

So the two are distinct here: the real BasePlugin, the real WebServer built by the real
start_web_server, the real REST handlers, and the real processListOfDevices. Only
Domoticz is faked (DomoticzEx: Devices is keyed by DeviceID, a Unit has Create and
Delete, a Device has neither), and the WebServer does not listen.

plugin.py imports the real Modules.* package, which conflicts with the stubs
tests/conftest.py installs for the session, so this runs in a subprocess.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

PREAMBLE = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock

    TRIO = {"Temperature": (80, 5, 0), "Humidity": (81, 1, 0), "Temp+Hum": (82, 1, 0)}

    class FakeUnit:
        next_id = 1000

        def __init__(self, DeviceID, Name, Unit, TypeName=None, Type=None, Subtype=None, Switchtype=0, **_):
            self.DeviceID, self.Unit = DeviceID, Unit
            self.Name = "Zigbee - " + Name
            self.Type, self.SubType, self.SwitchType = TRIO[TypeName] if TypeName else (Type, Subtype, Switchtype)
            self.nValue, self.sValue, self.Options, self.Color = 0, "", {}, ""
            self.ID = -1

        def Create(self):
            FakeUnit.next_id += 1
            self.ID = FakeUnit.next_id
            device = devices.setdefault(self.DeviceID, types.SimpleNamespace(DeviceID=self.DeviceID, Units={}, TimedOut=0))
            assert self.Unit not in device.Units, "unit already created"
            device.Units[self.Unit] = self

        def Update(self, **_):
            pass

        def Delete(self):
            # As CUnitEx_delete: the row goes, Units keeps the unit
            deleted.append(self.ID)

    devices, deleted = {}, []
    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Connection", "Log", "Debug", "Error", "Status", "Device"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Unit = FakeUnit
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    domoticz.Parameters = {"Name": "Zigbee"}
    domoticz.Devices = devices
    sys.modules["DomoticzEx"] = domoticz

    import plugin as plugin_module
    from Classes.WebServer.WebServer import WebServer
    from Classes.WebServer.rest_change_ModelName import rest_change_model_name
    from Classes.WebServer.rest_recreateWidget import rest_recreate_widgets
    from Modules.heartbeat import processListOfDevices

    for _name in ("startWebServer", "certified_devices_update"):
        setattr(WebServer, _name, MagicMock(name=_name))
    plugin_module.Devices = devices

    NWKID, IEEE = "76c4", "a4c1380000000001"

    plugin = plugin_module.BasePlugin()
    plugin.log = MagicMock()
    plugin.pluginconf = MagicMock()
    plugin.pluginconf.pluginConf = {}
    plugin.pluginParameters = {"Name": "Zigbee"}
    plugin.ControllerLink = MagicMock()
    plugin.zigbee_communication = "zigpy"
    plugin.DomoticzMajor, plugin.DomoticzMinor = 2026, 4
    plugin.adminWidgets = None
    plugin.ControllerIEEE = "00124b0000000000"
    plugin.groupmgt = None
    plugin.ListOfDevices = {NWKID: {
        "IEEE": IEEE, "Model": "probe", "Status": "inDB", "ProfileID": "0104", "ZDeviceID": "0000", "Type": "",
        "Ep": {"01": {"Type": "Temp/Humi", "ClusterType": {}}, "f1": {"Type": "Temp", "ClusterType": {}}},
    }}
    plugin.IEEE2NWK = {IEEE: NWKID}
    plugin.DeviceConf = {
        "probe": {"Ep": {"01": {"Type": "Temp/Humi"}, "f1": {"Type": "Temp"}}},
        "humidity": {"Ep": {"01": {"Type": "Humi"}, "f1": {"Type": ""}}},
    }

    # The device loop itself is not under test: it would poll the device
    import Modules.heartbeat as heartbeat_module
    heartbeat_module.hr_process_device = MagicMock()
    heartbeat_module.check_and_reset_device_if_needed = MagicMock()

    plugin_module.start_web_server(plugin, "9440", "/nonexistent")
    webserver = plugin.webserver
    assert webserver is not plugin

    def put(handler, body):
        return handler(webserver, "PUT", json.dumps(body).encode(), [])

    def recreate():
        put(rest_recreate_widgets, {"NWKID": NWKID})

    def heartbeat():
        processListOfDevices(plugin, devices)

    def user_deletes(cluster_type, ep):
        # Domoticz calls onDeviceRemoved with the unit still in Units, and drops it after
        for unit, widget in list(devices[IEEE].Units.items()):
            if plugin.ListOfDevices[NWKID]["Ep"][ep]["ClusterType"].get(str(widget.ID)) == cluster_type:
                plugin.onDeviceRemoved(IEEE, unit)
                del devices[IEEE].Units[unit]
                return
        raise AssertionError("no such widget")

    def bound():
        return {ep: sorted(data["ClusterType"].values()) for ep, data in plugin.ListOfDevices[NWKID]["Ep"].items()}

    def indexes():
        return {idx for data in plugin.ListOfDevices[NWKID]["Ep"].values() for idx in data["ClusterType"]}

    COMPLETE = {"01": ["Humi", "Temp", "Temp+Hum"], "f1": ["Temp"]}
    """
)


def _run(snippet):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(snippet)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_recreate_creates_the_widgets_at_the_next_heartbeat():
    _run(
        """
        recreate()
        assert devices == {}, "the REST handler must leave Domoticz alone"

        heartbeat()

        assert bound() == COMPLETE, bound()
        assert plugin.ListOfDevices[NWKID]["Status"] == "inDB"
        """
    )


def test_recreate_one_widget_after_the_other_as_reported():
    # The three steps of the report, each on the result of the one before
    _run(
        """
        recreate()
        heartbeat()
        for cluster_type, ep in (("Temp+Hum", "01"), ("Humi", "01"), ("Temp", "f1")):
            user_deletes(cluster_type, ep)
            kept = indexes()
            assert len(kept) == 3, bound()

            recreate()
            heartbeat()

            assert bound() == COMPLETE, (cluster_type, ep, bound())
            assert kept < indexes(), "the widgets that were there are kept"
            assert len(devices[IEEE].Units) == 4, devices[IEEE].Units
        """
    )


def test_a_request_is_served_once():
    _run(
        """
        recreate()
        recreate()
        heartbeat()
        assert plugin.widget_creation_requests == {}
        assert len(devices[IEEE].Units) == 4

        user_deletes("Humi", "01")
        heartbeat()
        assert len(devices[IEEE].Units) == 3, "nothing was asked for"
        """
    )


def test_the_webserver_holds_the_queue_of_the_plugin():
    _run(
        """
        assert webserver.widget_creation_requests is plugin.widget_creation_requests
        """
    )


def test_a_model_change_replaces_the_widgets():
    _run(
        """
        recreate()
        heartbeat()
        old = {int(idx) for idx in indexes()}

        put(rest_change_model_name, {"NWKID": NWKID, "Model": "humidity"})
        assert deleted == [], "the REST handler must leave Domoticz alone"
        heartbeat()

        assert plugin.ListOfDevices[NWKID]["Model"] == "humidity"
        assert set(deleted) == old, (deleted, old)
        assert "Humi" in bound()["01"], bound()
        assert "Temp" not in bound()["01"], bound()
        assert not old & {int(idx) for idx in indexes()}
        """
    )
