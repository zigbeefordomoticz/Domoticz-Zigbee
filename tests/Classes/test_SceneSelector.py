#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Classes/SceneSelector.py and what Classes/SceneManagement.py does with it.

Both modules are real. What Domoticz does is a small fake of the abstract layer that
keeps the widgets, as Domoticz would, so the tests read what a user would see on the
Selector. The commands sent are mock calls and the store is a real PluginStore that is
never loaded, as in test_SceneManagement.py.

The way through plugin.py is in test_SceneSelector_routing.py.
"""

import importlib
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from Classes.PluginStore import PluginStore

GROUP = "1001"
LAMP, LAMP_IEEE = "5c3e", "a1b2c3d4e5f60708"
SELECTOR_UNIT = 2
FULL_OPTIONS = {"LevelNames", "LevelActions", "LevelOffHidden", "SelectorStyle"}

RAW_COMMANDS = (
    "zcl_raw_add_scene", "zcl_raw_get_scene_membership", "zcl_raw_recall_scene",
    "zcl_raw_remove_all_scenes", "zcl_raw_remove_scene", "zcl_raw_store_scene",
)


class FakeDomoticz:
    """The abstract layer and what GrpDomoticz does with it, keeping {DeviceID: {Unit: widget}}."""

    def __init__(self):
        self.widgets = {}
        self.created = []
        self.deleted = []
        self.updates = []
        self.refuse_creation = False

    def create_selector(self, DeviceID_, Name_, widgetOptions):
        if self.refuse_creation:
            return -1
        self.widgets.setdefault(DeviceID_, {})[SELECTOR_UNIT] = {
            "Name": Name_, "Options": dict(widgetOptions), "nValue": 0, "sValue": "",
        }
        self.created.append(DeviceID_)
        return 1234

    def delete(self, plugin, Devices, DeviceID_, Unit_):
        del self.widgets[DeviceID_][Unit_]
        if not self.widgets[DeviceID_]:
            del self.widgets[DeviceID_]
        self.deleted.append(DeviceID_)

    def read_values(self, plugin, Devices, DeviceID, Unit):
        widget = self.widgets[DeviceID][Unit]
        return widget["nValue"], widget["sValue"]

    def read_options(self, plugin, Devices, DeviceId_, Unit_):
        return dict(self.widgets[DeviceId_][Unit_]["Options"])

    def update(self, plugin, Devices, DeviceID_, Unit_, nValue, sValue, Options=None, SuppressTriggers=False):
        widget = self.widgets[DeviceID_][Unit_]
        widget.update({"nValue": nValue, "sValue": sValue})
        if Options is not None:
            widget["Options"] = dict(Options)
        self.updates.append({"nValue": nValue, "sValue": sValue, "Options": Options, "SuppressTriggers": SuppressTriggers})

    def selector_unit(self, DeviceID):
        return SELECTOR_UNIT if self.has_selector(DeviceID) else None

    def group_unit(self, DeviceID):
        return next((unit for unit in self.widgets.get(DeviceID, {}) if unit != SELECTOR_UNIT), None)

    def has_selector(self, DeviceID=GROUP):
        return SELECTOR_UNIT in self.widgets.get(DeviceID, {})

    def user_deletes_selector(self):
        del self.widgets[GROUP][SELECTOR_UNIT]
        if not self.widgets[GROUP]:
            del self.widgets[GROUP]

    def selector(self):
        return self.widgets[GROUP][SELECTOR_UNIT]

    def names(self):
        return self.selector()["Options"]["LevelNames"].split("|")

    def level(self):
        return self.selector()["sValue"]


def is_hex(value):
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


@pytest.fixture(scope="module")
def loaded():
    """Module scoped, see test_SceneManagement.py."""
    tools = types.ModuleType("Modules.tools")
    tools.is_ack_tobe_disabled = lambda plugin, nwkid: False
    tools.is_hex = is_hex
    consts = types.ModuleType("Modules.zigateConsts")
    consts.MAX_LOAD_ZIGATE = 5
    consts.ZIGATE_EP = "01"
    zcl_commands = types.ModuleType("Zigbee.zclCommands")
    for name in ("zcl_move_to_level_with_onoff", "zcl_onoff_off_noeffect", "zcl_onoff_on"):
        setattr(zcl_commands, name, MagicMock(name=name))
    raw_commands = types.ModuleType("Zigbee.zclRawCommands")
    for name in RAW_COMMANDS:
        setattr(raw_commands, name, MagicMock(name=name))
    abstract = types.ModuleType("Modules.domoticzAbstractLayer")
    for name in ("domo_delete_widget", "domo_read_nValue_sValue", "domo_read_Options", "domo_update_api"):
        setattr(abstract, name, MagicMock(name=name))

    stubs = {
        "Modules.tools": tools, "Modules.zigateConsts": consts,
        "Zigbee.zclCommands": zcl_commands, "Zigbee.zclRawCommands": raw_commands,
        "Modules.domoticzAbstractLayer": abstract,
    }
    sys.modules.pop("Classes.SceneManagement", None)
    sys.modules.pop("Classes.SceneSelector", None)
    with patch.dict(sys.modules, stubs):
        management = importlib.import_module("Classes.SceneManagement")
        selector = importlib.import_module("Classes.SceneSelector")
    sys.modules.pop("Classes.SceneManagement", None)
    sys.modules.pop("Classes.SceneSelector", None)
    return types.SimpleNamespace(management=management, selector=selector)


@pytest.fixture
def domoticz(loaded):
    """The functions the module imported are repointed at a new fake for each test."""
    fake = FakeDomoticz()
    module = loaded.selector
    module.domo_delete_widget = fake.delete
    module.domo_read_nValue_sValue = fake.read_values
    module.domo_read_Options = fake.read_options
    module.domo_update_api = fake.update
    return fake


@pytest.fixture
def plugin(domoticz):
    p = types.SimpleNamespace()
    p.log = MagicMock()
    p.ControllerLink = MagicMock()
    p.ControllerLink.loadTransmit.return_value = 0
    p.ListOfDevices = {LAMP: {
        "IEEE": LAMP_IEEE, "ZDeviceName": "Ceiling",
        "Epv2": {"0b": {"ClusterIn": {"0005": {}, "0006": {}, "0008": {}}}},
        "Ep": {"0b": {"0005": {}, "0006": {}, "0008": {}}},
    }}
    p.IEEE2NWK = {LAMP_IEEE: LAMP}
    p.groupmgt = types.SimpleNamespace(
        ListOfGroups={GROUP: {"Name": "Living room", "Devices": [[LAMP, "0b", LAMP_IEEE]]}},
        Devices={}, processCommand=MagicMock(name="processCommand"),
        FullRemoveOfGroup=MagicMock(name="FullRemoveOfGroup"),
        create_scene_selector=domoticz.create_selector,
        group_widget_unit=domoticz.group_unit, scene_selector_unit=domoticz.selector_unit,
    )
    return p


@pytest.fixture
def store():
    return PluginStore("Z4D_Scenes", 1)


@pytest.fixture
def scenes(loaded, domoticz, plugin, store):
    for name in RAW_COMMANDS:
        getattr(loaded.management, name).reset_mock()
    return loaded.management.SceneManagement(plugin, store, loaded.selector.SceneSelector(plugin))


def add(scenes, *names):
    """Capture scenes and let the heartbeat bring the Selector up to date."""
    for name in names:
        scenes.create_scene(GROUP, name)
    scenes.heartbeat()


def scene_id(scenes, name):
    return next(scene["sceneId"] for scene in scenes.group_view(GROUP)["scenes"] if scene["name"] == name)


# ─── What the Selector shows ─────────────────────────────────────────────────

class TestLevels:

    def test_a_selector_comes_with_the_first_scene(self, scenes, domoticz):
        assert domoticz.widgets == {}
        add(scenes, "Movie")
        assert domoticz.selector()["Name"] == "Living room - Scenes"
        assert domoticz.names() == ["Off", "Movie"]

    def test_the_selector_is_unit_2_of_the_group(self, scenes, domoticz):
        domoticz.widgets[GROUP] = {1: {"Options": {}}}
        add(scenes, "Movie")
        assert sorted(domoticz.widgets) == [GROUP]
        assert sorted(domoticz.widgets[GROUP]) == [1, SELECTOR_UNIT]

    def test_nothing_touches_domoticz_before_the_heartbeat(self, scenes, domoticz):
        # create_scene comes from a REST thread
        scenes.create_scene(GROUP, "Movie")
        assert domoticz.created == []

    def test_a_group_without_a_name(self, scenes, domoticz, plugin):
        plugin.groupmgt.ListOfGroups[GROUP]["Name"] = ""
        add(scenes, "Movie")
        assert domoticz.selector()["Name"] == "1001 - Scenes"

    def test_levels_follow_the_scenes(self, scenes, domoticz):
        add(scenes, "Movie", "Reading")
        assert domoticz.names() == ["Off", "Movie", "Reading"]
        assert len(domoticz.created) == 1

    def test_a_rename_changes_the_name_at_its_level(self, scenes, domoticz):
        add(scenes, "Movie", "Reading")
        scenes.rename_scene(GROUP, scene_id(scenes, "Movie"), "Cinema")
        scenes.heartbeat()
        assert domoticz.names() == ["Off", "Cinema", "Reading"]

    def test_a_deleted_scene_leaves_its_slot(self, scenes, domoticz):
        add(scenes, "Movie", "Reading", "Dinner")
        scenes.delete_scene(GROUP, scene_id(scenes, "Reading"))
        scenes.heartbeat()
        assert domoticz.names() == ["Off", "Movie", "-", "Dinner"]

    def test_a_new_scene_takes_the_lowest_free_slot(self, scenes, domoticz):
        add(scenes, "Movie", "Reading", "Dinner")
        scenes.delete_scene(GROUP, scene_id(scenes, "Movie"))
        scenes.delete_scene(GROUP, scene_id(scenes, "Reading"))
        add(scenes, "Night")
        assert domoticz.names() == ["Off", "Night", "-", "Dinner"]

    def test_the_last_slot_goes_with_its_scene(self, scenes, domoticz):
        add(scenes, "Movie", "Reading")
        scenes.delete_scene(GROUP, scene_id(scenes, "Reading"))
        scenes.heartbeat()
        assert domoticz.names() == ["Off", "Movie"]

    def test_a_scene_found_by_a_scan_is_a_level(self, scenes, domoticz):
        scenes.scan_group(GROUP)
        scenes.membership_response(LAMP, "0b", "00", GROUP, ["2a"])
        scenes.heartbeat()
        assert domoticz.names() == ["Off", "Scene 2a"]

    def test_a_capture_keeps_the_level(self, scenes, domoticz, store):
        add(scenes, "Movie", "Reading")
        scenes.capture_scene(GROUP, scene_id(scenes, "Movie"))
        scenes.heartbeat()
        assert domoticz.names() == ["Off", "Movie", "Reading"]

    def test_the_levels_survive_a_restart(self, loaded, scenes, domoticz, plugin, store):
        add(scenes, "Movie", "Reading", "Dinner")
        scenes.delete_scene(GROUP, scene_id(scenes, "Movie"))
        scenes.heartbeat()
        restarted = loaded.management.SceneManagement(plugin, store, loaded.selector.SceneSelector(plugin))
        add(restarted, "Night")
        assert domoticz.names() == ["Off", "Night", "Reading", "Dinner"]

    def test_scenes_from_before_the_selector_get_one_at_the_start(self, loaded, scenes, domoticz, plugin, store):
        """Scenes stored by a plugin without this code have no level."""
        scenes.create_scene(GROUP, "Movie")
        scenes.create_scene(GROUP, "Reading")
        record = store.get(GROUP)
        assert all("selectorLevel" not in scene for scene in record["scenes"].values())
        restarted = loaded.management.SceneManagement(plugin, store, loaded.selector.SceneSelector(plugin))
        restarted.heartbeat()
        assert domoticz.names() == ["Off", "Movie", "Reading"]

    def test_a_restart_with_nothing_new_does_not_update_the_widget(self, loaded, scenes, domoticz, plugin, store):
        add(scenes, "Movie")
        domoticz.updates.clear()
        restarted = loaded.management.SceneManagement(plugin, store, loaded.selector.SceneSelector(plugin))
        restarted.heartbeat()
        assert domoticz.updates == []


class TestOptions:
    """Domoticz replaces the options as a whole, and they are partly the user's."""

    def test_buttons_by_default_so_a_scene_can_be_recalled_again(self, scenes, domoticz):
        """
        The dashboard's dropdown is a selectmenu that only reacts to a change of level, so
        the level on show could not be chosen again (www/app/widgets/dzLightWidget.js).
        """
        add(scenes, "Movie")
        assert domoticz.selector()["Options"]["SelectorStyle"] == "0"

    def test_all_options_are_sent_with_new_levels(self, scenes, domoticz):
        add(scenes, "Movie")
        add(scenes, "Reading")
        assert set(domoticz.updates[-1]["Options"]) == FULL_OPTIONS

    def test_the_user_keeps_style_and_hidden_off(self, scenes, domoticz):
        add(scenes, "Movie")
        domoticz.selector()["Options"].update({"SelectorStyle": "1", "LevelOffHidden": "true"})
        add(scenes, "Reading")
        options = domoticz.selector()["Options"]
        assert (options["SelectorStyle"], options["LevelOffHidden"]) == ("1", "true")

    def test_the_actions_stay_on_their_levels(self, scenes, domoticz):
        add(scenes, "Movie", "Reading")
        domoticz.selector()["Options"]["LevelActions"] = "|http://movie|http://reading"
        add(scenes, "Dinner")
        assert domoticz.selector()["Options"]["LevelActions"] == "|http://movie|http://reading|"

    def test_one_action_per_level_at_creation(self, scenes, domoticz):
        add(scenes, "Movie", "Reading")
        assert domoticz.selector()["Options"]["LevelActions"].count("|") == 2

    def test_a_list_of_names_is_no_event(self, scenes, domoticz):
        add(scenes, "Movie")
        add(scenes, "Reading")
        assert domoticz.updates[-1]["SuppressTriggers"] is True


# ─── Commands from Domoticz ──────────────────────────────────────────────────

class TestCommands:

    def recall(self, loaded):
        return loaded.management.zcl_raw_recall_scene

    def test_a_level_recalls_its_scene_with_one_frame(self, loaded, scenes, domoticz):
        add(scenes, "Movie", "Reading")
        scenes.selector_command(GROUP, "Set Level", 20)
        recall = self.recall(loaded)
        recall.assert_called_once()
        assert recall.call_args.args[1:5] + (recall.call_args.args[5],) == (GROUP, "01", "01", GROUP, scene_id(scenes, "Reading"))
        assert recall.call_args.kwargs == {"groupaddrmode": True}

    def test_the_selector_shows_the_level_with_triggers(self, scenes, domoticz):
        add(scenes, "Movie", "Reading")
        scenes.selector_command(GROUP, "Set Level", 20)
        assert (domoticz.selector()["nValue"], domoticz.level()) == (2, "20")
        assert domoticz.updates[-1]["SuppressTriggers"] is False

    def test_the_same_level_recalls_again(self, loaded, scenes, domoticz):
        """The lamps may have been changed since: choosing a scene again is not a no-op."""
        add(scenes, "Movie")
        scenes.selector_command(GROUP, "Set Level", 10)
        scenes.selector_command(GROUP, "Set Level", 10)
        assert self.recall(loaded).call_count == 2

    def test_a_recall_from_the_webui_moves_the_selector(self, scenes, domoticz):
        add(scenes, "Movie", "Reading")
        scenes.recall_scene(GROUP, scene_id(scenes, "Reading"))
        scenes.heartbeat()
        assert domoticz.level() == "20"
        assert domoticz.updates[-1]["SuppressTriggers"] is False

    def test_a_recall_before_the_first_heartbeat(self, scenes, domoticz):
        scenes.create_scene(GROUP, "Movie")
        scenes.recall_scene(GROUP, scene_id(scenes, "Movie"))
        scenes.heartbeat()
        assert domoticz.level() == "10"

    def test_a_recall_is_shown_once(self, scenes, domoticz):
        add(scenes, "Movie")
        scenes.selector_command(GROUP, "Set Level", 10)
        domoticz.selector()["sValue"] = "0"
        scenes.heartbeat()
        assert domoticz.level() == "0"

    def test_off_switches_the_group_off(self, scenes, domoticz, plugin):
        domoticz.widgets[GROUP] = {1: {"Options": {}, "nValue": 1, "sValue": "On"}}
        add(scenes, "Movie")
        scenes.selector_command(GROUP, "Set Level", 10)
        scenes.selector_command(GROUP, "Off", 0)
        plugin.groupmgt.processCommand.assert_called_once_with(1, GROUP, "Off", 0, "")
        assert (domoticz.selector()["nValue"], domoticz.level()) == (0, "0")

    def test_off_recalls_nothing(self, loaded, scenes, domoticz):
        add(scenes, "Movie")
        scenes.selector_command(GROUP, "Off", 0)
        self.recall(loaded).assert_not_called()

    def test_a_free_slot_does_nothing(self, loaded, scenes, domoticz, plugin):
        add(scenes, "Movie", "Reading", "Dinner")
        scenes.selector_command(GROUP, "Set Level", 30)
        scenes.delete_scene(GROUP, scene_id(scenes, "Reading"))
        scenes.heartbeat()
        self.recall(loaded).reset_mock()
        scenes.selector_command(GROUP, "Set Level", 20)
        self.recall(loaded).assert_not_called()
        plugin.groupmgt.processCommand.assert_not_called()
        assert domoticz.level() == "30"

    def test_other_commands_are_ignored(self, loaded, scenes, domoticz, plugin):
        add(scenes, "Movie")
        scenes.selector_command(GROUP, "On", 0)
        self.recall(loaded).assert_not_called()
        plugin.groupmgt.processCommand.assert_not_called()

    def test_a_group_that_is_gone(self, loaded, scenes, domoticz, plugin):
        add(scenes, "Movie")
        del plugin.groupmgt.ListOfGroups[GROUP]
        scenes.selector_command(GROUP, "Set Level", 10)
        scenes.selector_command(GROUP, "Off", 0)
        self.recall(loaded).assert_not_called()
        plugin.groupmgt.processCommand.assert_not_called()


class TestShownLevel:

    def test_deleting_the_scene_on_show_goes_back_to_off_quietly(self, scenes, domoticz):
        add(scenes, "Movie", "Reading")
        scenes.selector_command(GROUP, "Set Level", 10)
        scenes.delete_scene(GROUP, scene_id(scenes, "Movie"))
        scenes.heartbeat()
        assert domoticz.level() == "0"
        assert domoticz.updates[-1]["SuppressTriggers"] is True

    def test_a_new_level_keeps_the_scene_on_show(self, scenes, domoticz):
        add(scenes, "Movie")
        scenes.selector_command(GROUP, "Set Level", 10)
        add(scenes, "Reading")
        assert domoticz.level() == "10"

    def test_a_value_domoticz_set_itself(self, scenes, domoticz):
        add(scenes, "Movie")
        domoticz.selector()["sValue"] = "Off"
        add(scenes, "Reading")
        assert domoticz.level() == "0"


# ─── Removal ─────────────────────────────────────────────────────────────────

class TestRemoval:

    def test_no_scene_left_no_selector(self, scenes, domoticz):
        add(scenes, "Movie")
        scenes.delete_scene(GROUP, scene_id(scenes, "Movie"))
        scenes.heartbeat()
        assert not domoticz.has_selector()

    def test_the_widget_of_the_group_keeps_the_group(self, scenes, domoticz, plugin):
        domoticz.widgets[GROUP] = {1: {"Options": {}}}
        add(scenes, "Movie")
        scenes.delete_scene(GROUP, scene_id(scenes, "Movie"))
        scenes.heartbeat()
        assert not domoticz.has_selector()
        plugin.groupmgt.FullRemoveOfGroup.assert_not_called()

    def test_without_the_widget_of_the_group_the_selector_was_holding_it(self, scenes, domoticz, plugin):
        add(scenes, "Movie")
        scenes.delete_scene(GROUP, scene_id(scenes, "Movie"))
        scenes.heartbeat()
        plugin.groupmgt.FullRemoveOfGroup.assert_called_once_with(None, GROUP)

    def test_a_member_leaving_with_the_last_scene(self, scenes, domoticz):
        add(scenes, "Movie")
        scenes.member_removed(GROUP, LAMP, "0b", LAMP_IEEE)
        scenes.heartbeat()
        assert not domoticz.has_selector()

    def test_the_user_deleting_it_keeps_scenes_and_group(self, scenes, domoticz, plugin, store):
        add(scenes, "Movie")
        domoticz.user_deletes_selector()
        scenes.selector_removed(GROUP)
        assert len(scenes.group_view(GROUP)["scenes"]) == 1
        assert GROUP in plugin.groupmgt.ListOfGroups
        assert store.get(GROUP)["selectorRemoved"] is True

    def test_it_stays_deleted_across_a_restart(self, loaded, scenes, domoticz, plugin, store):
        add(scenes, "Movie")
        domoticz.user_deletes_selector()
        scenes.selector_removed(GROUP)
        restarted = loaded.management.SceneManagement(plugin, store, loaded.selector.SceneSelector(plugin))
        restarted.heartbeat()
        assert not domoticz.has_selector()

    def test_it_stays_deleted_after_a_rename(self, scenes, domoticz):
        add(scenes, "Movie")
        domoticz.user_deletes_selector()
        scenes.selector_removed(GROUP)
        scenes.rename_scene(GROUP, scene_id(scenes, "Movie"), "Cinema")
        scenes.heartbeat()
        assert not domoticz.has_selector()

    def test_a_new_scene_brings_it_back_with_every_scene(self, scenes, domoticz):
        add(scenes, "Movie")
        domoticz.user_deletes_selector()
        scenes.selector_removed(GROUP)
        add(scenes, "Reading")
        assert domoticz.names() == ["Off", "Movie", "Reading"]

    def test_a_removal_after_the_last_scene_is_nothing(self, scenes, domoticz, store):
        add(scenes, "Movie")
        scenes.delete_scene(GROUP, scene_id(scenes, "Movie"))
        scenes.heartbeat()
        scenes.selector_removed(GROUP)
        assert store.get(GROUP) is None

    def test_a_group_list_that_could_not_be_read_costs_no_widget(self, scenes, domoticz, plugin):
        add(scenes, "Movie")
        del plugin.groupmgt.ListOfGroups[GROUP]
        scenes._selector_changed(GROUP)
        scenes.heartbeat()
        assert domoticz.has_selector()


class TestWithoutASelector:
    """As in test_SceneManagement.py: no selector given, nothing asked of Domoticz."""

    def test_scenes_work(self, loaded, domoticz, plugin, store):
        scenes = loaded.management.SceneManagement(plugin, store)
        scenes.create_scene(GROUP, "Movie")
        scenes.heartbeat()
        assert domoticz.widgets == {}


class TestCreationRefused:

    def test_scenes_stay_usable(self, loaded, scenes, domoticz, plugin):
        domoticz.refuse_creation = True
        add(scenes, "Movie")
        assert domoticz.widgets == {}
        assert scenes.recall_scene(GROUP, scene_id(scenes, "Movie"))["name"] == "Movie"

    def test_the_next_change_tries_again(self, scenes, domoticz):
        domoticz.refuse_creation = True
        add(scenes, "Movie")
        domoticz.refuse_creation = False
        add(scenes, "Reading")
        assert domoticz.names() == ["Off", "Movie", "Reading"]
