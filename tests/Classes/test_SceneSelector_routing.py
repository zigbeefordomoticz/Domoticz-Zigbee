#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The Selector of the scenes through the real onCommand and onDeviceRemoved of
plugin.py, the real abstract layer and the real start-up check of the widgets, with
only Domoticz and the frame replaced. The fake Domoticz is held to what its source
does: Options only reach the database with UpdateOptions, and they replace what
was there (hardware/plugins/PythonObjectEx.cpp, CUnitEx_update).

What matters most here is onDeviceRemoved: it takes a DeviceID in ListOfGroups for
the group itself, so a Selector on the group's DeviceID would empty the group.

plugin.py imports the real Modules.* package, which conflicts with the stubs
tests/conftest.py installs for the session, so this runs in a subprocess.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SCRIPT = textwrap.dedent(
    """
    import sys, types
    from unittest.mock import MagicMock

    class FakeUnit:
        next_id = 100

        def __init__(self, DeviceID, Name, Unit, Type=None, Subtype=None, Switchtype=None, Options=None):
            self.DeviceID, self.Name, self.Unit = DeviceID, Name, Unit
            self.Type, self.SubType, self.SwitchType = Type, Subtype, Switchtype
            self.Options = dict(Options or {})
            self.stored_options = dict(Options or {})
            self.nValue, self.sValue = 0, ""
            self.updates = []

        def Create(self):
            FakeUnit.next_id += 1
            self.ID = FakeUnit.next_id
            device = devices.setdefault(self.DeviceID, types.SimpleNamespace(Units={}, TimedOut=0, Delete=lambda: None))
            device.Units[self.Unit] = self

        def Update(self, Log=False, SuppressTriggers=False, UpdateProperties=False, UpdateOptions=False):
            if UpdateOptions:
                self.stored_options = dict(self.Options)
            self.updates.append({"SuppressTriggers": SuppressTriggers, "UpdateOptions": UpdateOptions})

        def Delete(self):
            del devices[self.DeviceID].Units[self.Unit]
            if not devices[self.DeviceID].Units:
                del devices[self.DeviceID]

    devices = {}
    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Connection", "Log", "Debug", "Error", "Status", "Device"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Unit = FakeUnit
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    domoticz.Parameters = {}
    domoticz.Devices = devices
    sys.modules["DomoticzEx"] = domoticz

    import plugin as plugin_module
    import Classes.SceneManagement as scene_module
    from Classes.PluginStore import PluginStore
    from Classes.SceneSelector import SceneSelector
    from Modules.database import checkListOfDevice2Devices

    GROUP, NWKID, EP, IEEE = "1001", "c577", "0b", "a1b2c3d4e5f60708"
    SELECTOR = "Z4D-Scenes-" + GROUP

    for name in ("zcl_raw_add_scene", "zcl_raw_recall_scene", "zcl_raw_store_scene", "zcl_raw_remove_scene"):
        setattr(scene_module, name, MagicMock(name=name))

    plugin = types.SimpleNamespace(
        log=MagicMock(),
        pluginParameters={"Name": "Zigbee"},
        ListOfDomoticzWidget={},
        DeviceConf={},
        ListOfDevices={NWKID: {
            "IEEE": IEEE, "ZDeviceName": "Ceiling", "Ep": {EP: {}},
            "Epv2": {EP: {"ClusterIn": {"0005": {}, "0006": {}, "0008": {}}}},
        }},
        IEEE2NWK={IEEE: NWKID},
        ControllerIEEE="00124b0000000000",
        ControllerLink=MagicMock(),
        VersionNewFashion=True,
        pluginconf=types.SimpleNamespace(pluginConf={}),
    )
    plugin.ControllerLink.loadTransmit.return_value = 0
    plugin.groupmgt = MagicMock()
    plugin.groupmgt.Devices = devices
    plugin.groupmgt.ListOfGroups = {GROUP: {"Name": "Living room", "Devices": [[NWKID, EP, IEEE]]}}
    plugin.scenemgt = scene_module.SceneManagement(plugin, PluginStore("Z4D_Scenes", 1), SceneSelector(plugin))

    on_command = plugin_module.BasePlugin.onCommand
    on_removed = plugin_module.BasePlugin.onDeviceRemoved
    FakeUnit(GROUP, "Living room", 1, Type=241, Subtype=7, Switchtype=7).Create()

    # The first scene creates the widget, through the real abstract layer
    plugin.scenemgt.create_scene(GROUP, "Movie")
    plugin.scenemgt.create_scene(GROUP, "Reading")
    plugin.scenemgt.heartbeat()
    unit = devices[SELECTOR].Units[1]
    assert unit.Name == "Zigbee - Living room - Scenes", unit.Name
    assert (unit.Type, unit.SubType, unit.SwitchType) == (244, 62, 18)
    assert unit.stored_options["LevelNames"] == "Off|Movie|Reading", unit.stored_options

    # A third scene: the names reach the database, with the options of the user
    unit.Options["SelectorStyle"] = "0"
    plugin.scenemgt.create_scene(GROUP, "Dinner")
    plugin.scenemgt.heartbeat()
    assert unit.stored_options["LevelNames"] == "Off|Movie|Reading|Dinner", unit.stored_options
    assert unit.stored_options["SelectorStyle"] == "0"
    assert unit.updates[-1] == {"SuppressTriggers": True, "UpdateOptions": True}, unit.updates

    # A command on the widget goes to the scene, never to the group
    on_command(plugin, SELECTOR, 1, "Set Level", 20, "")
    plugin.groupmgt.processCommand.assert_not_called()
    scene_module.zcl_raw_recall_scene.assert_called_once()
    assert (unit.nValue, unit.sValue) == (2, "20")
    assert unit.updates[-1] == {"SuppressTriggers": False, "UpdateOptions": False}, unit.updates

    # Off is the group switched off, on the unit of the group
    on_command(plugin, SELECTOR, 1, "Off", 0, "")
    plugin.groupmgt.processCommand.assert_called_once_with(1, GROUP, "Off", 0, "")
    assert (unit.nValue, unit.sValue) == (0, "0")

    # The group widget still goes to the group
    plugin.groupmgt.processCommand.reset_mock()
    on_command(plugin, GROUP, 1, "On", 0, "")
    plugin.groupmgt.processCommand.assert_called_once_with(1, GROUP, "On", 0, "")

    # At each start the widgets are checked: the Selector is not an unknown one
    plugin.log.reset_mock()
    plugin.ListOfDomoticzWidget[unit.ID] = {"DeviceID": SELECTOR, "Name": unit.Name}
    checkListOfDevice2Devices(plugin, devices)
    not_found = [call for call in plugin.log.logging.call_args_list if "not found" in str(call)]
    assert not not_found, not_found

    # Deleted by the user: the group and its scenes do not move
    unit.Delete()
    on_removed(plugin, SELECTOR, 1)
    plugin.groupmgt.FullRemoveOfGroup.assert_not_called()
    assert len(plugin.scenemgt.group_view(GROUP)["scenes"]) == 3
    assert plugin.scenemgt.store.get(GROUP)["selectorRemoved"] is True
    plugin.scenemgt.heartbeat()
    assert SELECTOR not in devices

    # And deleting the group itself is still what removes the group
    on_removed(plugin, GROUP, 1)
    plugin.groupmgt.FullRemoveOfGroup.assert_called_once_with(1, GROUP)

    # Without scenes started, a Selector left in Domoticz is an unknown device, not a crash
    plugin.scenemgt = None
    plugin.log.reset_mock()
    on_command(plugin, SELECTOR, 1, "Set Level", 10, "")
    assert any(call.args[1] == "Error" for call in plugin.log.logging.call_args_list)

    print("OK")
    """
)


def test_selector_through_plugin_py():
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", SCRIPT], cwd=REPO_ROOT, capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().endswith("OK")
