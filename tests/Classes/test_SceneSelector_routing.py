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
                 "zcl_raw_remove_all_scenes", "zcl_raw_get_scene_membership"):
        setattr(scene_module, name, MagicMock(name=name))
    group_services.remove_group_member_ship = MagicMock(name="remove_group_member_ship")
    group_services.look_for_group_member_ship = MagicMock(name="look_for_group_member_ship")
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
    def group_management():
        return GroupsManagement(
            MagicMock(), True, 2025, 2, 0, plugin.pluginconf, plugin.ControllerLink, plugin.adminWidgets, "/tmp", 1, devices,
            plugin.ListOfDevices, plugin.IEEE2NWK, plugin.ListOfDomoticzWidget, plugin.DeviceConf, plugin.log, MagicMock(),
            plugin.pluginParameters, [],
        )

    plugin.groupmgt = group_management()

    def start_scenes():
        plugin.scenemgt = scene_module.SceneManagement(plugin, PluginStore("Z4D_Scenes", 1), SceneSelector(plugin))
        plugin.groupmgt.scenemgt = plugin.scenemgt

    def stop_scenes():
        plugin.scenemgt = plugin.groupmgt.scenemgt = None

    def restart(groups=None, store=None):
        # The file and the store as they are, or as given, and Domoticz as it is
        saved = plugin.groupmgt.ListOfGroups if groups is None else groups
        kept_store = plugin.scenemgt.store if store is None else store
        GroupsManagement.load_groups_list_from_json = lambda self: setattr(self, "ListOfGroups", saved)
        plugin.groupmgt = group_management()
        plugin.scenemgt = scene_module.SceneManagement(plugin, kept_store, SceneSelector(plugin))
        plugin.groupmgt.scenemgt = plugin.scenemgt
        plugin.scenemgt.heartbeat()

    def group_heartbeats():
        plugin.groupmgt.hearbeat_group_mgt()
        plugin.scenemgt.heartbeat()

    def group_scan():
        group_services.scan_device_for_grp_membership(plugin.groupmgt, NWKID, EP)

    def group_answer(group):
        plugin.groupmgt.look_for_group_member_ship_response("01" + EP + "0004" + "ff" + "01" + group + NWKID)

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
        assert plugin.scenemgt.store.get("1001") is not None
        assert members_left() == 0

        # Told apart from a device: the Selector is known as deleted, and stays so when the group returns
        plugin.groupmgt.ListOfGroups["1001"] = {"Name": "Living room", "Devices": [[NWKID, EP, IEEE]]}
        plugin.scenemgt._selector_changed("1001")
        plugin.scenemgt.heartbeat()
        assert units("1001") == [1]
        assert not errors(), errors()
    """,
    "an_admin_widget_is_a_selector_and_not_a_scene_selector": """
        FakeUnit("Zigate-01-0001", "Admin", 1, Type=244, Subtype=62, Switchtype=18).Create()
        assert not plugin.groupmgt.is_scene_selector("Zigate-01-0001", 1)
        on_command(plugin, "Zigate-01-0001", 1, "Set Level", 10, "")
        plugin.adminWidgets.handleCommand.assert_called_once()
    """,
    "a_restart_brings_the_group_widget_back": """
        add_group("1001")
        clear()
        user_deletes("1001", 1)
        restart()
        assert units("1001") == [1, SELECTOR_UNIT]
        assert devices["1001"].Units[1].Name == "Zigbee - Living room", devices["1001"].Units[1].Name
        assert members_left() == 0
        assert plugin.groupmgt.ListOfGroups["1001"]["Devices"] == [[NWKID, EP, IEEE]]
        assert scene_count("1001") == 1
        assert not errors(), errors()

        # Back for good: the group now goes by removing both again
        user_deletes("1001", SELECTOR_UNIT)
        assert members_left() == 0
        user_deletes("1001", 1)
        assert members_left() == 1
    """,
    "a_restart_brings_the_selector_back": """
        add_group("1001", scenes=("Movie", "Reading"))
        user_deletes("1001", SELECTOR_UNIT)
        plugin.scenemgt.heartbeat()
        assert units("1001") == [1]
        clear()
        restart()
        assert units("1001") == [1, SELECTOR_UNIT]
        assert devices["1001"].Units[SELECTOR_UNIT].stored_options["LevelNames"] == "Off|Movie|Reading"
        assert not errors(), errors()
    """,
    "a_group_scan_brings_both_back": """
        add_group("1001")
        user_deletes("1001", 1)
        group_heartbeats()
        assert units("1001") == [SELECTOR_UNIT]
        plugin.groupmgt.request_widgets_restore()
        group_heartbeats()
        assert units("1001") == [1, SELECTOR_UNIT]

        user_deletes("1001", SELECTOR_UNIT)
        group_heartbeats()
        assert units("1001") == [1]
        plugin.groupmgt.request_widgets_restore()
        group_heartbeats()
        assert units("1001") == [1, SELECTOR_UNIT]
        assert not errors(), errors()
    """,
    "a_scene_scan_brings_both_back": """
        add_group("1001")
        user_deletes("1001", SELECTOR_UNIT)
        group_heartbeats()
        plugin.scenemgt.scan_group("1001")
        group_heartbeats()
        assert units("1001") == [1, SELECTOR_UNIT]
        assert not errors(), errors()
    """,
    "the_ping_group_gets_no_widget": """
        plugin.pluginconf.pluginConf["pingViaGroup"] = 0x1234
        plugin.groupmgt.ListOfGroups["1234"] = {"Name": "Ping", "Devices": [[NWKID, EP, IEEE]]}
        plugin.groupmgt.restore_group_widgets()
        assert units("1234") == []
    """,
    "a_scan_of_a_single_lamp_keeps_its_group": """
        add_group("1001")
        widget, selector = devices["1001"].Units[1], devices["1001"].Units[SELECTOR_UNIT]
        clear()
        group_scan()
        group_heartbeats()

        # The lamp has not answered yet, or will not: nothing went
        assert plugin.groupmgt.ListOfGroups["1001"]["Name"] == "Living room"
        assert plugin.groupmgt.ListOfGroups["1001"]["Devices"] == []
        assert devices["1001"].Units[1] is widget and widget.in_database
        assert devices["1001"].Units[SELECTOR_UNIT] is selector and selector.in_database
        assert scene_count("1001") == 1

        group_answer("1001")
        assert plugin.groupmgt.ListOfGroups["1001"]["Name"] == "Living room"
        assert plugin.groupmgt.ListOfGroups["1001"]["Devices"] == [[NWKID, EP, IEEE]]
        assert devices["1001"].Units[1] is widget
        assert not errors(), errors()
    """,
    "a_scan_brings_back_the_widget_of_a_known_group": """
        add_group("1001", scenes=())
        del devices["1001"].Units[1]
        group_answer("1001")
        assert units("1001") == [1]
        assert devices["1001"].Units[1].Name == "Zigbee - Living room"
    """,
    "lost_configuration_rebuilt_by_a_scan_then_a_scene_scan": """
        # Groups and scenes lost, and Domoticz lost its widgets too
        restart(groups={}, store=PluginStore("Z4D_Scenes", 1))
        assert devices == {}

        group_answer("1001")
        assert plugin.groupmgt.ListOfGroups["1001"]["Devices"] == [[NWKID, EP, IEEE]]
        assert units("1001") == [1]
        plugin.scenemgt.heartbeat()
        assert units("1001") == [1]

        plugin.scenemgt.scan_group("1001")
        plugin.scenemgt.membership_response(NWKID, EP, "00", "1001", ["03", "07"])
        group_heartbeats()
        assert units("1001") == [1, SELECTOR_UNIT]
        assert devices["1001"].Units[SELECTOR_UNIT].stored_options["LevelNames"] == "Off|Scene 03|Scene 07"
        assert not errors(), errors()
    """,
    "lost_configuration_with_the_widgets_still_in_domoticz": """
        add_group("1001", scenes=("Movie", "Reading"))
        widget, selector = devices["1001"].Units[1], devices["1001"].Units[SELECTOR_UNIT]
        selector.Options["SelectorStyle"] = "1"
        restart(groups={}, store=PluginStore("Z4D_Scenes", 1))

        group_answer("1001")
        plugin.scenemgt.scan_group("1001")
        plugin.scenemgt.membership_response(NWKID, EP, "00", "1001", ["01", "02"])
        group_heartbeats()
        assert units("1001") == [1, SELECTOR_UNIT]
        assert devices["1001"].Units[1] is widget and devices["1001"].Units[SELECTOR_UNIT] is selector
        assert selector.stored_options["LevelNames"] == "Off|Scene 01|Scene 02", selector.stored_options
        assert selector.stored_options["SelectorStyle"] == "1"
        assert not errors(), errors()
    """,
    "an_empty_group_goes_with_its_widgets": """
        add_group("1001")
        group_scan()
        clear()
        user_deletes("1001", 1)
        assert "1001" in plugin.groupmgt.ListOfGroups
        user_deletes("1001", SELECTOR_UNIT)
        assert "1001" not in plugin.groupmgt.ListOfGroups
        assert plugin.scenemgt.store.get("1001") is None
        assert not errors(), errors()
    """,
    "an_empty_group_deleted_from_the_webui": """
        import Classes.GroupMgtv2.GrpWebServices as web
        add_group("1001")
        group_scan()
        clear()

        # As REST: from another thread, so no widget moves there
        web.delGroup(plugin.groupmgt, "1001")
        assert "1001" in plugin.groupmgt.ListOfGroups
        assert units("1001") == [1, SELECTOR_UNIT]

        group_heartbeats()
        assert "1001" not in plugin.groupmgt.ListOfGroups
        assert plugin.scenemgt.store.get("1001") is None
        assert units("1001") == []
        assert not errors(), errors()
    """,
    "a_device_removed_leaves_a_group_with_a_selector": """
        add_group("1001")
        plugin.groupmgt.RemoveNwkIdFromAllGroups(NWKID)
        assert plugin.groupmgt.ListOfGroups["1001"]["Devices"] == []
        assert units("1001") == [1, SELECTOR_UNIT]
    """,
    "a_device_removed_takes_a_group_without_a_scene_as_before": """
        add_group("1001", scenes=())
        plugin.groupmgt.RemoveNwkIdFromAllGroups(NWKID)
        assert "1001" not in plugin.groupmgt.ListOfGroups
    """,
    "a_device_removed_leaves_an_unrelated_empty_group": """
        add_group("1001")
        plugin.groupmgt.ListOfGroups["2002"] = {"Name": "Empty", "Devices": []}
        FakeUnit("2002", "Zigbee - Empty", 1, Type=244, Subtype=73, Switchtype=0).Create()
        plugin.groupmgt.RemoveNwkIdFromAllGroups(NWKID)
        assert "2002" in plugin.groupmgt.ListOfGroups
        assert units("2002") == [1]
    """,
    "the_scan_routes_of_the_webui_bring_the_widgets_back": """
        import Classes.WebServer.rest_Groups as rest
        web = types.SimpleNamespace(groupmgt=plugin.groupmgt, logging=MagicMock(), pluginconf=plugin.pluginconf)
        add_group("1001")

        user_deletes("1001", 1)
        rest.rest_rescan_group(web, "GET", None, [])
        assert units("1001") == [SELECTOR_UNIT], "a REST thread must not touch a widget"
        group_heartbeats()
        assert units("1001") == [1, SELECTOR_UNIT]

        user_deletes("1001", 1)
        group_heartbeats()
        assert units("1001") == [SELECTOR_UNIT]
        rest.rest_scan_devices_for_group(web, "PUT", b'["c577"]', [])
        assert units("1001") == [SELECTOR_UNIT], "a REST thread must not touch a widget"
        group_heartbeats()
        assert units("1001") == [1, SELECTOR_UNIT]
    """,
    "a_group_id_used_again_is_not_held": """
        add_group("1001", scenes=("Movie",))
        user_deletes("1001", 1)
        assert "1001" in plugin.groupmgt.GroupWidgetsRemoved
        user_deletes("1001", SELECTOR_UNIT)
        del plugin.groupmgt.ListOfGroups["1001"]

        group_answer("1001")
        assert units("1001") == [1]
        del devices["1001"].Units[1]
        group_answer("1001")
        assert units("1001") == [1]
    """,
    "a_device_leaving_the_scene_takes_the_selector_to_off": """
        clock = [1000]
        scene_module.time = lambda: clock[0]
        add_group("1001", scenes=("Movie", "Reading"))
        selector = devices["1001"].Units[SELECTOR_UNIT]
        state = plugin.ListOfDevices[NWKID]["Ep"][EP]

        on_command(plugin, "1001", SELECTOR_UNIT, "Set Level", 10, "")
        assert selector.sValue == "10"
        # The transition (1 s) and SCENE_SETTLE_TIME: what the fade reports is not a change
        state["0008"]["0000"] = "40"
        clock[0] += 10
        plugin.scenemgt.heartbeat()
        assert selector.sValue == "10"
        state["0008"]["0000"] = "c0"
        clock[0] += 2
        plugin.scenemgt.heartbeat()
        plugin.scenemgt.heartbeat()
        assert selector.sValue == "10"

        clear()
        state["0006"]["0000"] = "00"
        plugin.scenemgt.heartbeat()
        assert (selector.nValue, selector.sValue) == (0, "0"), selector.sValue
        assert selector.updates[-1] == {"SuppressTriggers": True, "UpdateOptions": False}, selector.updates
        assert not group_off_sent()
        scene_module.zcl_raw_recall_scene.assert_not_called()
        assert not errors(), errors()

        count = len(selector.updates)
        plugin.scenemgt.heartbeat()
        state["0006"]["0000"] = "01"
        plugin.scenemgt.heartbeat()
        assert len(selector.updates) == count, "Off stays until a scene is chosen"
    """,
    "a_level_moves_the_selector_only_past_the_reporting_change": """
        clock = [1000]
        scene_module.time = lambda: clock[0]
        add_group("1001")
        selector = devices["1001"].Units[SELECTOR_UNIT]
        state = plugin.ListOfDevices[NWKID]["Ep"][EP]
        on_command(plugin, "1001", SELECTOR_UNIT, "Set Level", 10, "")
        clock[0] += 12
        plugin.scenemgt.heartbeat()
        state["0008"]["0000"] = "85"
        plugin.scenemgt.heartbeat()
        assert selector.sValue == "10", "a dimmer holds back a change of 5"
        state["0008"]["0000"] = "86"
        plugin.scenemgt.heartbeat()
        assert selector.sValue == "0", "a change of 6 is a command"
    """,
    "the_level_of_a_lamp_that_is_off_is_not_a_change": """
        clock = [1000]
        scene_module.time = lambda: clock[0]
        add_group("1001")
        selector = devices["1001"].Units[SELECTOR_UNIT]
        state = plugin.ListOfDevices[NWKID]["Ep"][EP]
        state["0006"]["0000"] = "00"
        on_command(plugin, "1001", SELECTOR_UNIT, "Set Level", 10, "")
        clock[0] += 12
        plugin.scenemgt.heartbeat()
        state["0008"]["0000"] = "20"
        plugin.scenemgt.heartbeat()
        assert selector.sValue == "10"
    """,
    "the_settle_time_follows_the_transition": """
        clock = [1000]
        scene_module.time = lambda: clock[0]
        add_group("1001", scenes=())
        plugin.scenemgt.create_scene("1001", "Slow", 30)
        plugin.scenemgt.heartbeat()
        selector = devices["1001"].Units[SELECTOR_UNIT]
        state = plugin.ListOfDevices[NWKID]["Ep"][EP]
        on_command(plugin, "1001", SELECTOR_UNIT, "Set Level", 10, "")
        clock[0] += 39
        state["0008"]["0000"] = "20"
        plugin.scenemgt.heartbeat()
        state["0008"]["0000"] = "80"
        plugin.scenemgt.heartbeat()
        assert selector.sValue == "10", "still fading"
    """,
    "a_device_outside_the_scene_does_not_count": """
        clock = [1000]
        scene_module.time = lambda: clock[0]
        add_group("1001")
        other, other_ieee = "d001", "b1b2c3d4e5f60708"
        plugin.ListOfDevices[other] = {
            "IEEE": other_ieee, "ZDeviceName": "Plug", "Ep": {"01": {"ClusterType": {"501": "Switch"}, "0006": {"0000": "01"}}},
            "Epv2": {"01": {"ClusterIn": {"0005": {}, "0006": {}}}},
        }
        plugin.IEEE2NWK[other_ieee] = other
        plugin.groupmgt.ListOfGroups["1001"]["Devices"].append([other, "01", other_ieee])
        selector = devices["1001"].Units[SELECTOR_UNIT]
        on_command(plugin, "1001", SELECTOR_UNIT, "Set Level", 10, "")
        clock[0] += 12
        plugin.scenemgt.heartbeat()
        plugin.ListOfDevices[other]["Ep"]["01"]["0006"]["0000"] = "00"
        plugin.scenemgt.heartbeat()
        assert selector.sValue == "10"
    """,
    "a_member_taken_out_of_the_scene_no_longer_counts": """
        clock = [1000]
        scene_module.time = lambda: clock[0]
        add_group("1001", scenes=())
        other, other_ieee = "d001", "b1b2c3d4e5f60708"
        plugin.ListOfDevices[other] = {
            "IEEE": other_ieee, "ZDeviceName": "Plug", "Ep": {"01": {"ClusterType": {"501": "Switch"}, "0006": {"0000": "01"}}},
            "Epv2": {"01": {"ClusterIn": {"0005": {}, "0006": {}}}},
        }
        plugin.IEEE2NWK[other_ieee] = other
        plugin.groupmgt.ListOfGroups["1001"]["Devices"].append([other, "01", other_ieee])
        scene_id = plugin.scenemgt.create_scene("1001", "Movie")["sceneId"]
        plugin.scenemgt.heartbeat()
        selector = devices["1001"].Units[SELECTOR_UNIT]
        on_command(plugin, "1001", SELECTOR_UNIT, "Set Level", 10, "")
        clock[0] += 12
        plugin.scenemgt.heartbeat()
        plugin.scenemgt.edit_scene("1001", scene_id, "Movie", members=["%s-%s" % (IEEE, EP)])
        plugin.ListOfDevices[other]["Ep"]["01"]["0006"]["0000"] = "00"
        plugin.scenemgt.heartbeat()
        assert selector.sValue == "10"
        assert not errors(), errors()
    """,
    "after_a_restart_the_selector_still_follows_its_scene": """
        clock = [1000]
        scene_module.time = lambda: clock[0]
        add_group("1001", scenes=("Movie", "Reading"))
        selector = devices["1001"].Units[SELECTOR_UNIT]
        on_command(plugin, "1001", SELECTOR_UNIT, "Set Level", 20, "")
        restart()
        plugin.scenemgt.heartbeat()
        plugin.scenemgt.heartbeat()
        assert selector.sValue == "20"
        plugin.ListOfDevices[NWKID]["Ep"][EP]["0006"]["0000"] = "00"
        plugin.scenemgt.heartbeat()
        assert selector.sValue == "0"
    """,
    "off_or_a_gone_scene_stops_the_watch": """
        clock = [1000]
        scene_module.time = lambda: clock[0]
        add_group("1001", scenes=("Movie", "Reading"))
        selector = devices["1001"].Units[SELECTOR_UNIT]
        state = plugin.ListOfDevices[NWKID]["Ep"][EP]

        on_command(plugin, "1001", SELECTOR_UNIT, "Set Level", 10, "")
        clock[0] += 12
        plugin.scenemgt.heartbeat()
        on_command(plugin, "1001", SELECTOR_UNIT, "Off", 0, "")
        assert plugin.scenemgt._selector_shown == {}

        on_command(plugin, "1001", SELECTOR_UNIT, "Set Level", 20, "")
        clock[0] += 12
        plugin.scenemgt.heartbeat()
        plugin.scenemgt.delete_scene("1001", plugin.scenemgt.group_view("1001")["scenes"][1]["sceneId"])
        plugin.scenemgt.heartbeat()
        plugin.scenemgt.heartbeat()
        assert selector.sValue == "0"
        assert plugin.scenemgt._selector_shown == {}

        on_command(plugin, "1001", SELECTOR_UNIT, "Set Level", 10, "")
        user_deletes("1001", SELECTOR_UNIT)
        assert plugin.scenemgt._selector_shown == {}
        state["0006"]["0000"] = "00"
        plugin.scenemgt.heartbeat()
        assert not errors(), errors()
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
