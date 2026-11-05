#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The widgets of a group through the real onCommand and onDeviceRemoved of plugin.py,
the real GroupsManagement, SceneManagement and SceneSelector, the real abstract layer
and the real start-up check of the widgets, with only Domoticz and the frames replaced.

A group holds two widgets on one DeviceID: unit 1 for the group, unit 2 for the Selector
of its scenes. What matters most is how they go: the members leave with the last of them,
in either order, and a group widget that is gone must not make the Selector look like it.

The fake Domoticz is held to what its source does:
- Options only reach the database with UpdateOptions, and they replace what was there
  (hardware/plugins/PythonObjectEx.cpp, CUnitEx_update)
- Unit.Delete() takes the row away, leaves the unit in Units and calls nothing back
  (CUnitEx_delete). There is no Device.Delete() (CDeviceEx_methods)
- a user deleting a widget calls onDeviceRemoved with the unit still in Units, and
  Units only loses it after the call (PluginMessages.h, onDeviceRemovedCallback)

plugin.py imports the real Modules.* package, which conflicts with the stubs
tests/conftest.py installs for the session, so this runs in a subprocess.
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

    class FakeUnit:
        next_id = 100

        def __init__(self, DeviceID, Name, Unit, Type=None, Subtype=None, Switchtype=None, Options=None, TypeName=None):
            self.DeviceID, self.Name, self.Unit = DeviceID, Name, Unit
            self.Type, self.SubType, self.SwitchType = Type, Subtype, Switchtype
            self.Options = dict(Options or {})
            self.stored_options = dict(Options or {})
            self.nValue, self.sValue, self.Color = 0, "", ""
            self.updates = []
            self.in_database = False

        def Create(self):
            FakeUnit.next_id += 1
            self.ID = FakeUnit.next_id
            self.in_database = True
            device = devices.setdefault(self.DeviceID, types.SimpleNamespace(Units={}, TimedOut=0))
            device.Units[self.Unit] = self

        def Update(self, Log=False, SuppressTriggers=False, UpdateProperties=False, UpdateOptions=False, TypeName=None):
            assert self.in_database, "Update of a unit deleted from Domoticz"
            if UpdateOptions:
                self.stored_options = dict(self.Options)
            self.updates.append({"SuppressTriggers": SuppressTriggers, "UpdateOptions": UpdateOptions})

        def Delete(self):
            self.in_database = False

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
    import Classes.GroupMgtv2.GrpDomoticz as group_widgets
    import Classes.GroupMgtv2.GrpServices as group_services
    import Classes.SceneManagement as scene_module
    from Classes.GroupMgtv2.GroupManagement import GroupsManagement
    from Classes.PluginStore import PluginStore
    from Classes.SceneSelector import SceneSelector
    from Modules.database import checkListOfDevice2Devices

    NWKID, EP, IEEE = "c577", "0b", "a1b2c3d4e5f60708"
    SELECTOR_UNIT = 2

    for name in ("zcl_raw_add_scene", "zcl_raw_recall_scene", "zcl_raw_store_scene", "zcl_raw_remove_scene",
                 "zcl_raw_remove_all_scenes"):
        setattr(scene_module, name, MagicMock(name=name))
    group_services.remove_group_member_ship = MagicMock(name="remove_group_member_ship")
    group_widgets.zcl_group_onoff_off_noeffect = MagicMock(name="zcl_group_onoff_off_noeffect")
    group_widgets.zcl_group_onoff_off_witheffect = MagicMock(name="zcl_group_onoff_off_witheffect")
    group_widgets.zcl_group_onoff_on = MagicMock(name="zcl_group_onoff_on")
    GroupsManagement.write_groups_list = MagicMock(name="write_groups_list")

    plugin = types.SimpleNamespace(
        log=MagicMock(),
        pluginParameters={"Name": "Zigbee"},
        ListOfDomoticzWidget={},
        DeviceConf={},
        ListOfDevices={NWKID: {
            "IEEE": IEEE, "ZDeviceName": "Ceiling", "Ep": {EP: {"ClusterType": {"501": "LvlControl"}, "0006": {"0000": "01"}, "0008": {"0000": "80"}}},
            "Epv2": {EP: {"ClusterIn": {"0005": {}, "0006": {}, "0008": {}}}},
        }},
        IEEE2NWK={IEEE: NWKID},
        ControllerIEEE="00124b0000000000",
        ControllerLink=MagicMock(),
        VersionNewFashion=True,
        adminWidgets=MagicMock(),
        pluginconf=types.SimpleNamespace(pluginConf={
            "pingViaGroup": 0, "reComputeGroupState": 1, "pluginData": "/nonexistent", "GrpfadingOff": 0, "forceGroupDeviceRefresh": 0, "OnIfOneOn": 0,
        }),
    )
    plugin.ControllerLink.loadTransmit.return_value = 0
    plugin.groupmgt = GroupsManagement(
        MagicMock(), True, 2025, 2, 0, plugin.pluginconf, plugin.ControllerLink, plugin.adminWidgets, "/tmp", 1, devices,
        plugin.ListOfDevices, plugin.IEEE2NWK, plugin.ListOfDomoticzWidget, plugin.DeviceConf, plugin.log, MagicMock(),
        plugin.pluginParameters, [],
    )
    plugin.groupmgt.GroupStatus = "ready"

    def start_scenes():
        plugin.scenemgt = scene_module.SceneManagement(plugin, PluginStore("Z4D_Scenes", 1), SceneSelector(plugin))
        plugin.groupmgt.scenemgt = plugin.scenemgt

    def stop_scenes():
        plugin.scenemgt = plugin.groupmgt.scenemgt = None

    start_scenes()
    on_command = plugin_module.BasePlugin.onCommand
    on_removed = plugin_module.BasePlugin.onDeviceRemoved

    def add_group(group, unit=1, scenes=("Movie",)):
        plugin.groupmgt.ListOfGroups[group] = {"Name": "Living room", "Devices": [[NWKID, EP, IEEE]]}
        FakeUnit(group, "Zigbee - Living room", unit, Type=241, Subtype=7, Switchtype=7).Create()
        for name in scenes:
            plugin.scenemgt.create_scene(group, name)
        plugin.scenemgt.heartbeat()

    def user_deletes(group, unit):
        widget = devices[group].Units[unit]
        widget.in_database = False
        on_removed(plugin, group, unit)
        del devices[group].Units[unit]

    def units(group):
        return sorted(devices[group].Units) if group in devices else []

    def scene_count(group):
        return len(plugin.scenemgt.group_view(group)["scenes"])

    def errors():
        return [call for call in plugin.log.logging.call_args_list if call.args[1] == "Error"]

    def members_left():
        return group_services.remove_group_member_ship.call_count

    def clear():
        group_services.remove_group_member_ship.reset_mock()
        scene_module.zcl_raw_remove_all_scenes.reset_mock()
        scene_module.zcl_raw_recall_scene.reset_mock()
        group_widgets.zcl_group_onoff_off_noeffect.reset_mock()
        group_widgets.zcl_group_onoff_off_witheffect.reset_mock()
        group_widgets.zcl_group_onoff_on.reset_mock()
        plugin.log.reset_mock()

    def group_off_sent():
        return group_widgets.zcl_group_onoff_off_noeffect.called or group_widgets.zcl_group_onoff_off_witheffect.called
    """
)

SCENARIOS = {
    "the_selector_is_unit_2_of_the_group": """
        add_group("1001", scenes=("Movie", "Reading"))
        assert units("1001") == [1, SELECTOR_UNIT]
        selector = devices["1001"].Units[SELECTOR_UNIT]
        assert selector.Name == "Zigbee - Living room - Scenes", selector.Name
        assert (selector.Type, selector.SubType, selector.SwitchType) == (244, 62, 18)
        assert selector.stored_options["LevelNames"] == "Off|Movie|Reading", selector.stored_options

        selector.Options["SelectorStyle"] = "1"
        plugin.scenemgt.create_scene("1001", "Dinner")
        plugin.scenemgt.heartbeat()
        assert selector.stored_options["LevelNames"] == "Off|Movie|Reading|Dinner", selector.stored_options
        assert selector.stored_options["SelectorStyle"] == "1"
        assert selector.updates[-1] == {"SuppressTriggers": True, "UpdateOptions": True}, selector.updates
    """,
    "the_commands_go_where_they_belong": """
        add_group("1001", scenes=("Movie", "Reading"))
        selector = devices["1001"].Units[SELECTOR_UNIT]
        group = devices["1001"].Units[1]
        group.updates.clear()

        on_command(plugin, "1001", SELECTOR_UNIT, "Set Level", 20, "")
        scene_module.zcl_raw_recall_scene.assert_called_once()
        assert (selector.nValue, selector.sValue) == (2, "20")
        assert selector.updates[-1] == {"SuppressTriggers": False, "UpdateOptions": False}, selector.updates
        assert not group.updates, group.updates

        on_command(plugin, "1001", SELECTOR_UNIT, "Off", 0, "")
        assert group_off_sent()
        assert (selector.nValue, selector.sValue) == (0, "0")
        assert group.nValue == 0, group.nValue

        clear()
        on_command(plugin, "1001", 1, "On", 0, "")
        group_widgets.zcl_group_onoff_on.assert_called()
        scene_module.zcl_raw_recall_scene.assert_not_called()
        assert (selector.nValue, selector.sValue) == (0, "0")
        assert not errors(), errors()
    """,
    "the_start_up_check_knows_the_selector": """
        add_group("1001")
        unit = devices["1001"].Units[SELECTOR_UNIT]
        plugin.ListOfDomoticzWidget[unit.ID] = {"DeviceID": "1001", "Name": unit.Name}
        clear()
        checkListOfDevice2Devices(plugin, devices)
        not_found = [call for call in plugin.log.logging.call_args_list if "not found" in str(call)]
        assert not not_found, not_found
    """,
    "without_a_scene_a_group_is_as_it_was": """
        add_group("1001", scenes=())
        assert units("1001") == [1]
        clear()
        user_deletes("1001", 1)
        assert members_left() == 1
        assert not errors(), errors()
    """,
    "selector_first_then_the_group": """
        add_group("1001")
        clear()
        user_deletes("1001", SELECTOR_UNIT)
        assert members_left() == 0
        assert scene_count("1001") == 1
        assert plugin.scenemgt.store.get("1001")["selectorRemoved"] is True
        plugin.scenemgt.heartbeat()
        assert units("1001") == [1]

        user_deletes("1001", 1)
        assert members_left() == 1
        scene_module.zcl_raw_remove_all_scenes.assert_called_once()
        assert not errors(), errors()
    """,
    "group_first_the_members_stay_until_the_selector_goes": """
        add_group("1001")
        selector = devices["1001"].Units[SELECTOR_UNIT]
        before = (selector.Type, selector.SubType, selector.SwitchType, selector.nValue, selector.sValue)
        clear()
        user_deletes("1001", 1)
        assert members_left() == 0
        scene_module.zcl_raw_remove_all_scenes.assert_not_called()
        assert plugin.groupmgt.ListOfGroups["1001"]["Devices"] == [[NWKID, EP, IEEE]]
        assert scene_count("1001") == 1

        # What follows a state change must neither bring the widget back nor take the Selector for it
        assert plugin.groupmgt.group_widget_unit("1001") is None
        plugin.groupmgt.update_domoticz_group_device("1001")
        plugin.scenemgt.heartbeat()
        assert units("1001") == [SELECTOR_UNIT]
        assert before == (selector.Type, selector.SubType, selector.SwitchType, selector.nValue, selector.sValue)

        # The scenes still work, Off included
        on_command(plugin, "1001", SELECTOR_UNIT, "Set Level", 10, "")
        scene_module.zcl_raw_recall_scene.assert_called_once()
        assert selector.sValue == "10"
        on_command(plugin, "1001", SELECTOR_UNIT, "Off", 0, "")
        assert group_off_sent()
        assert selector.sValue == "0"
        assert not errors(), errors()

        user_deletes("1001", SELECTOR_UNIT)
        assert members_left() == 1
        scene_module.zcl_raw_remove_all_scenes.assert_called_once()
        plugin.scenemgt.heartbeat()
        assert plugin.scenemgt.store.get("1001") is None
        assert not errors(), errors()
    """,
    "group_first_then_the_last_scene_deleted_in_the_webui": """
        add_group("1001")
        scene = plugin.scenemgt.group_view("1001")["scenes"][0]["sceneId"]
        clear()
        user_deletes("1001", 1)
        assert members_left() == 0

        plugin.scenemgt.delete_scene("1001", scene)
        plugin.scenemgt.heartbeat()
        assert units("1001") == []
        assert members_left() == 1
        assert not errors(), errors()
    """,
    "the_selector_comes_back_after_the_last_scene": """
        add_group("1001")
        scene = plugin.scenemgt.group_view("1001")["scenes"][0]["sceneId"]
        first = devices["1001"].Units[SELECTOR_UNIT]
        plugin.scenemgt.delete_scene("1001", scene)
        plugin.scenemgt.heartbeat()
        assert units("1001") == [1]
        assert not first.in_database

        plugin.scenemgt.create_scene("1001", "Reading")
        plugin.scenemgt.heartbeat()
        assert units("1001") == [1, SELECTOR_UNIT]
        assert devices["1001"].Units[SELECTOR_UNIT] is not first
        assert devices["1001"].Units[SELECTOR_UNIT].in_database
        assert not errors(), errors()
    """,
    "a_group_from_before_8_1_003_sitting_on_unit_2": """
        add_group("1001", unit=SELECTOR_UNIT)
        assert units("1001") == [SELECTOR_UNIT, 3]
        assert plugin.groupmgt.group_widget_unit("1001") == SELECTOR_UNIT
        assert plugin.groupmgt.scene_selector_unit("1001") == 3
        selector = devices["1001"].Units[3]
        assert (selector.Type, selector.SubType) == (244, 62)

        clear()
        on_command(plugin, "1001", SELECTOR_UNIT, "On", 0, "")
        group_widgets.zcl_group_onoff_on.assert_called()
        on_command(plugin, "1001", 3, "Set Level", 10, "")
        scene_module.zcl_raw_recall_scene.assert_called_once()

        user_deletes("1001", SELECTOR_UNIT)
        assert members_left() == 0
        user_deletes("1001", 3)
        assert members_left() == 1
        assert not errors(), errors()
    """,
    "the_selector_stays_a_selector_when_the_user_changes_its_switch_type": """
        add_group("1001")
        devices["1001"].Units[SELECTOR_UNIT].SwitchType = 0
        assert plugin.groupmgt.is_scene_selector("1001", SELECTOR_UNIT)
        assert plugin.groupmgt.group_widget_unit("1001") == 1
    """,
    "native_scenes_turned_off_with_a_selector_left_behind": """
        add_group("1001")
        stop_scenes()
        clear()

        # Not a command for the group, and deleting it, the way to clean up, must not empty it
        on_command(plugin, "1001", SELECTOR_UNIT, "Set Level", 10, "")
        group_widgets.zcl_group_onoff_on.assert_not_called()
        assert not group_off_sent()
        user_deletes("1001", SELECTOR_UNIT)
        assert members_left() == 0
        assert not errors(), errors()

        user_deletes("1001", 1)
        assert members_left() == 1
    """,
    "a_selector_outliving_its_group": """
        add_group("1001")
        del plugin.groupmgt.ListOfGroups["1001"]
        clear()
        on_command(plugin, "1001", SELECTOR_UNIT, "Set Level", 10, "")
        scene_module.zcl_raw_recall_scene.assert_not_called()
        user_deletes("1001", SELECTOR_UNIT)
        assert plugin.scenemgt.store.get("1001")["selectorRemoved"] is True
        assert members_left() == 0
        assert not errors(), errors()
    """,
    "an_admin_widget_is_a_selector_and_not_a_scene_selector": """
        FakeUnit("Zigate-01-0001", "Admin", 1, Type=244, Subtype=62, Switchtype=18).Create()
        assert not plugin.groupmgt.is_scene_selector("Zigate-01-0001", 1)
        on_command(plugin, "Zigate-01-0001", 1, "Set Level", 10, "")
        plugin.adminWidgets.handleCommand.assert_called_once()
    """,
    "a_device_widget_is_not_a_group": """
        assert not plugin.groupmgt.is_group_widget(IEEE, 1)
        assert not plugin.groupmgt.is_scene_selector("1001", None)
    """,
}


def run_scenario(body):
    script = PREAMBLE + textwrap.dedent(body) + '\nprint("OK")\n'
    return subprocess.run(  # nosec B603
        [sys.executable, "-c", script], cwd=REPO_ROOT, capture_output=True, text=True, timeout=120
    )


def pytest_generate_tests(metafunc):
    if "scenario" in metafunc.fixturenames:
        metafunc.parametrize("scenario", SCENARIOS)


def test_group_widgets_through_plugin_py(scenario):
    result = run_scenario(SCENARIOS[scenario])
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().endswith("OK")
