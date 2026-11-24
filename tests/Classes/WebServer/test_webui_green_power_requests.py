#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PUT and DELETE /zgp-device from the REST handler to the heartbeat.

The handlers run with the WebServer as self and the heartbeat with the plugin. The
widget queue and the flush flag were set on self, so the type given to a Green Power
device on the WebUI was recorded and its widgets never came.

So the two are distinct here: the real BasePlugin, the real WebServer built by the real
start_web_server, the real handler, store and device types, and the real
processListOfDevices. Only Domoticz is faked, and the WebServer does not listen.

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

    class FakeUnit:
        next_id = 1000

        def __init__(self, DeviceID, Name, Unit, Type=None, Subtype=None, Switchtype=0, **_):
            self.DeviceID, self.Name, self.Unit = DeviceID, Name, Unit
            self.Type, self.SubType, self.SwitchType = Type, Subtype, Switchtype
            self.nValue, self.sValue, self.Options, self.Color = 0, "", {}, ""
            self.ID = -1

        def Create(self):
            FakeUnit.next_id += 1
            self.ID = FakeUnit.next_id
            devices.setdefault(self.DeviceID, types.SimpleNamespace(DeviceID=self.DeviceID, Units={}, TimedOut=0)).Units[self.Unit] = self

        def Update(self, **_):
            pass

    devices = {}
    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Connection", "Log", "Debug", "Error", "Status", "Device"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Unit = FakeUnit
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    domoticz.Parameters = {"Name": "Zigbee"}
    domoticz.Devices = devices
    sys.modules["DomoticzEx"] = domoticz

    import plugin as plugin_module
    from Classes.PluginStore import PluginStore
    from Classes.WebServer.WebServer import WebServer
    from Classes.WebServer.rest_GreenPower import rest_zgp_device
    from Modules.greenPowerModels import load_gp_models
    from Modules.greenPowerStore import GP_STORE_NAME, GP_STORE_VERSION
    from Modules.heartbeat import processListOfDevices

    for _name in ("startWebServer", "certified_devices_update"):
        setattr(WebServer, _name, MagicMock(name=_name))
    plugin_module.Devices = devices

    GP_IEEE, MODEL = "0000000001020304", "GreenPower-OnOff-Dim"

    plugin = plugin_module.BasePlugin()
    plugin.log = MagicMock()
    plugin.pluginconf = MagicMock()
    plugin.pluginconf.pluginConf = {"forceSwitchSelectorPushButton": 0, "logDeviceUpdate": 0, "Lang": "en-US"}
    plugin.pluginParameters = {"Name": "Zigbee"}
    plugin.ControllerLink = MagicMock()
    plugin.zigbee_communication = "zigpy"
    plugin.DomoticzMajor, plugin.DomoticzMinor = 2026, 4
    plugin.adminWidgets = None
    plugin.groupmgt = None
    plugin.ListOfDevices = {}
    # Device ID 0xfe and no command: nothing applies until the user gives it a type
    store = PluginStore(GP_STORE_NAME, GP_STORE_VERSION)
    store.set(GP_IEEE, {"ieee": GP_IEEE, "nwk": "0304", "src_id": 0x01020304, "device_id": 0xfe, "commands": [], "security_key": "00" * 16})
    plugin.PluginStores = {GP_STORE_NAME: store}
    load_gp_models(plugin, "Conf/")

    plugin_module.start_web_server(plugin, "9440", "/nonexistent")
    webserver = plugin.webserver
    assert webserver is not plugin

    def call(verb, body=None):
        response = rest_zgp_device(webserver, verb, None if body is None else json.dumps(body).encode(), [GP_IEEE])
        assert response["Status"] == "200 OK", response

    def heartbeat():
        processListOfDevices(plugin, devices)
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


def test_the_type_given_on_the_webui_creates_the_widgets_at_the_next_heartbeat():
    _run(
        """
        call("PUT", {"Model": MODEL})
        assert devices == {}, "the REST handler must leave Domoticz alone"

        heartbeat()

        assert len(devices[GP_IEEE].Units) > 0
        assert store.get(GP_IEEE)["Model"] == MODEL
        bound = {idx for ep in store.get(GP_IEEE)["Ep"].values() for idx in ep["ClusterType"]}
        assert bound == {str(unit.ID) for unit in devices[GP_IEEE].Units.values()}, bound
        assert plugin.flush_list_of_devices is True
        """
    )


def test_a_removal_from_the_webui_is_written_at_the_next_heartbeat():
    _run(
        """
        call("DELETE")
        assert plugin.flush_list_of_devices is False

        heartbeat()

        assert GP_IEEE not in store
        assert plugin.flush_list_of_devices is True
        """
    )


def test_a_request_is_served_once():
    _run(
        """
        call("PUT", {"Model": MODEL})
        heartbeat()
        widgets = len(devices[GP_IEEE].Units)
        plugin.flush_list_of_devices = False

        heartbeat()

        assert len(devices[GP_IEEE].Units) == widgets
        assert plugin.flush_list_of_devices is False
        """
    )
