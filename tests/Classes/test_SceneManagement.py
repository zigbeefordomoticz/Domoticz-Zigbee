#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Classes/SceneManagement.py

The module is imported with Modules.tools, Modules.zigateConsts and the two
Zigbee command modules stubbed, so the commands sent are mock calls, and the store
is a real PluginStore that is never loaded: it lives in memory.

The frames themselves are in tests/Zigbee/test_zcl_raw_scene_commands.py.
"""

import importlib
import json
import sys
import time
import types
from unittest.mock import MagicMock, patch

import pytest

from Classes.PluginStore import PluginStore

GROUP = "1001"
CEILING, CEILING_IEEE = "5c3e", "a1b2c3d4e5f60708"
SOFA, SOFA_IEEE = "7a11", "1112131415161718"
STRIP, STRIP_IEEE = "a77f", "0102030405060708"
REMOTE, REMOTE_IEEE = "b001", "2122232425262728"

COMMANDS = (
    "zcl_raw_add_scene", "zcl_raw_get_scene_membership", "zcl_raw_recall_scene",
    "zcl_raw_remove_all_scenes", "zcl_raw_remove_scene", "zcl_raw_store_scene",
)


def lamp(ieee, ep, cluster_in, cluster_out=(), state=None):
    return {
        "IEEE": ieee,
        "ZDeviceName": "name-" + ieee[:4],
        "Epv2": {ep: {"ClusterIn": dict.fromkeys(cluster_in, {}), "ClusterOut": dict.fromkeys(cluster_out, {})}},
        # As the Simple Descriptor decoder does: in and out clusters together
        "Ep": {ep: {**dict.fromkeys(cluster_in, {}), **dict.fromkeys(cluster_out, {}), **(state or {})}},
    }


def is_hex(value):
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


@pytest.fixture(scope="module")
def loaded():
    """
    Module scoped: swapping sys.modules once per test disturbs unrelated tests of
    the suite, see tests/Classes/Groups/test_legrand_group_recovery.py.
    """
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
    for name in COMMANDS:
        setattr(raw_commands, name, MagicMock(name=name))

    stubs = {
        "Modules.tools": tools, "Modules.zigateConsts": consts,
        "Zigbee.zclCommands": zcl_commands, "Zigbee.zclRawCommands": raw_commands,
    }
    sys.modules.pop("Classes.SceneManagement", None)
    with patch.dict(sys.modules, stubs):
        module = importlib.import_module("Classes.SceneManagement")
    sys.modules.pop("Classes.SceneManagement", None)
    return module


@pytest.fixture
def mod(loaded):
    """The commands sent are what the tests assert on, so they start each test clean."""
    for name in COMMANDS + ("zcl_move_to_level_with_onoff", "zcl_onoff_off_noeffect", "zcl_onoff_on"):
        getattr(loaded, name).reset_mock()
    return loaded


@pytest.fixture
def plugin():
    p = types.SimpleNamespace()
    p.log = MagicMock()
    p.ControllerLink = MagicMock()
    p.ControllerLink.loadTransmit.return_value = 0
    p.ListOfDevices = {
        "0000": {"IEEE": "00124b0000000000", "Epv2": {"01": {"ClusterIn": {"0005": {}, "0006": {}}}}},
        CEILING: lamp(CEILING_IEEE, "0b", ("0005", "0006", "0008")),
        SOFA: lamp(SOFA_IEEE, "01", ("0005", "0006", "0008")),
        STRIP: lamp(STRIP_IEEE, "01", ("0006", "0008"), state={"0006": {"0000": "01"}, "0008": {"0000": "78"}}),
        REMOTE: lamp(REMOTE_IEEE, "01", ("0000",), cluster_out=("0005", "0006")),
    }
    p.IEEE2NWK = {device["IEEE"]: nwkid for nwkid, device in p.ListOfDevices.items()}
    p.groupmgt = types.SimpleNamespace(ListOfGroups={
        GROUP: {"Name": "Living room", "Devices": [
            ["0000", "01", "00124b0000000000"],
            [CEILING, "0b", CEILING_IEEE],
            [SOFA, "01", SOFA_IEEE],
            [STRIP, "01", STRIP_IEEE],
            [REMOTE, "01", REMOTE_IEEE],
        ]},
        "2002": {"Name": "Garden", "Devices": [[STRIP, "01", STRIP_IEEE]]},
        "0000": {"Name": "Lightlink", "Devices": [[CEILING, "0b", CEILING_IEEE]]},
    })
    return p


@pytest.fixture
def store():
    return PluginStore("Z4D_Scenes", 1)


@pytest.fixture
def scenes(mod, plugin, store):
    return mod.SceneManagement(plugin, store)


def stored(store, scene="01", group=GROUP):
    return store.get(group)["scenes"][scene]


def complete_capture(mod, scenes, nwkid, ep, status="00", scene="01"):
    scenes.scene_response("Add", nwkid, ep, "00", GROUP, scene)
    scenes.scene_response("Store", nwkid, ep, status, GROUP, scene)


def error_code(callable_, *args, **kwargs):
    with pytest.raises(Exception) as caught:
        callable_(*args, **kwargs)
    return caught.value.code


# ─── Who is a member ─────────────────────────────────────────────────────────

class TestMembers:

    def test_only_lamps_are_members(self, scenes):
        view = scenes.group_view(GROUP)
        assert {m["ieee"]: m["capability"] for m in view["members"]} == {
            CEILING_IEEE: "native", SOFA_IEEE: "native", STRIP_IEEE: "fallback",
        }

    def test_a_group_of_fallback_devices_is_not_capable(self, scenes):
        assert scenes.group_view("2002")["capable"] is False

    def test_group_0_is_not_capable(self, scenes):
        assert scenes.group_view("0000")["capable"] is False

    def test_two_endpoints_of_a_device_are_two_members(self, scenes, plugin, store):
        plugin.ListOfDevices[CEILING]["Epv2"]["0c"] = {"ClusterIn": {"0005": {}}}
        plugin.groupmgt.ListOfGroups[GROUP]["Devices"].append([CEILING, "0c", CEILING_IEEE])
        scenes.create_scene(GROUP, "Reading")
        assert {CEILING_IEEE + "-0b", CEILING_IEEE + "-0c"} <= set(stored(store)["members"])

    def test_a_new_nwkid_is_followed(self, mod, scenes, plugin):
        plugin.IEEE2NWK[CEILING_IEEE] = "9999"
        plugin.ListOfDevices["9999"] = plugin.ListOfDevices.pop(CEILING)
        scenes.create_scene(GROUP, "Reading")
        assert "9999" in [c.args[1] for c in mod.zcl_raw_add_scene.call_args_list]


# ─── Capture ─────────────────────────────────────────────────────────────────

class TestCapture:

    def test_add_scene_goes_to_each_native_member_with_the_transition(self, mod, scenes):
        scenes.create_scene(GROUP, "Reading", 3)
        sent = {c.args[1:7] for c in mod.zcl_raw_add_scene.call_args_list}
        assert sent == {(CEILING, "01", "0b", GROUP, "01", 3), (SOFA, "01", "01", GROUP, "01", 3)}

    def test_store_scene_waits_for_the_add_response(self, mod, scenes):
        scenes.create_scene(GROUP, "Reading")
        mod.zcl_raw_store_scene.assert_not_called()
        scenes.scene_response("Add", CEILING, "0b", "00", GROUP, "01")
        mod.zcl_raw_store_scene.assert_called_once()
        assert mod.zcl_raw_store_scene.call_args.args[1:6] == (CEILING, "01", "0b", GROUP, "01")

    def test_a_refused_add_still_goes_to_store(self, mod, scenes):
        # Add Scene only carries the transition time: Store Scene is the verdict
        scenes.create_scene(GROUP, "Reading")
        scenes.scene_response("Add", CEILING, "0b", "85", GROUP, "01")
        mod.zcl_raw_store_scene.assert_called_once()

    def test_new_scene_is_pending(self, scenes, store):
        view = scenes.create_scene(GROUP, "Reading")
        assert view["sceneId"] == "01"
        assert (view["synced"], view["native"]) == (0, 2)
        assert {m["status"] for m in stored(store)["members"].values()} == {"pending", "n/a"}

    def test_store_success_is_synced(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        complete_capture(mod, scenes, CEILING, "0b")
        complete_capture(mod, scenes, SOFA, "01")
        assert scenes.group_view(GROUP)["scenes"][0]["synced"] == 2
        member = stored(store)["members"][CEILING_IEEE + "-0b"]
        assert member["status"] == "synced"
        assert isinstance(member["lastCheck"], int)

    def test_store_failure_keeps_the_status_code(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        complete_capture(mod, scenes, CEILING, "0b", status="89")
        member = stored(store)["members"][CEILING_IEEE + "-0b"]
        assert (member["status"], member["error"]) == ("failed", "89")

    def test_fallback_member_keeps_a_snapshot_and_gets_no_frame(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        member = stored(store)["members"][STRIP_IEEE + "-01"]
        assert member["snapshot"] == {"onOff": 1, "level": 0x78}
        assert STRIP not in [c.args[1] for c in mod.zcl_raw_add_scene.call_args_list]

    @pytest.mark.parametrize("response", [
        ("Store", CEILING, "0b", "00", GROUP, "01"),    # not the expected step
        ("Add", CEILING, "0b", "00", "2002", "01"),     # another group
        ("Add", CEILING, "0b", "00", GROUP, "07"),      # another scene
        ("Add", "ffff", "0b", "00", GROUP, "01"),       # unknown device
    ])
    def test_an_unexpected_response_is_ignored(self, mod, scenes, store, response):
        scenes.create_scene(GROUP, "Reading")
        scenes.scene_response(*response)
        mod.zcl_raw_store_scene.assert_not_called()
        assert stored(store)["members"][CEILING_IEEE + "-0b"]["status"] == "pending"

    def test_scene_ids_reuse_the_lowest_free_one(self, scenes):
        for name in ("One", "Two", "Three"):
            scenes.create_scene(GROUP, name)
        scenes.delete_scene(GROUP, "02")
        assert scenes.create_scene(GROUP, "Four")["sceneId"] == "02"

    def test_records_are_json(self, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        json.dumps(store.snapshot())


class TestTimeouts:

    def _expire(self, mod, scenes):
        real = mod.time
        with patch.object(mod, "time", lambda: real() + mod.SCENE_RESPONSE_TIMEOUT + 1):
            scenes.heartbeat()

    def test_no_add_response(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        self._expire(mod, scenes)
        member = stored(store)["members"][CEILING_IEEE + "-0b"]
        assert (member["status"], member["error"]) == ("failed", "timeout")

    def test_no_store_response(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        scenes.scene_response("Add", CEILING, "0b", "00", GROUP, "01")
        self._expire(mod, scenes)
        assert stored(store)["members"][CEILING_IEEE + "-0b"]["status"] == "failed"

    def test_a_late_response_changes_nothing(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        self._expire(mod, scenes)
        scenes.scene_response("Add", CEILING, "0b", "00", GROUP, "01")
        mod.zcl_raw_store_scene.assert_not_called()

    def test_the_heartbeat_leaves_the_rest_waiting(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        scenes.heartbeat()
        assert stored(store)["members"][CEILING_IEEE + "-0b"]["status"] == "pending"

    def test_a_restart_fails_what_was_pending(self, mod, plugin, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        complete_capture(mod, scenes, SOFA, "01")
        mod.SceneManagement(plugin, store)
        members = stored(store)["members"]
        assert (members[CEILING_IEEE + "-0b"]["status"], members[CEILING_IEEE + "-0b"]["error"]) == ("failed", "interrupted")
        assert members[SOFA_IEEE + "-01"]["status"] == "synced"


# ─── Refused requests ────────────────────────────────────────────────────────

class TestRefused:

    @pytest.mark.parametrize("group, name, transition, code", [
        ("dead", "Reading", 1, "GROUP_NOT_FOUND"),
        ("0000", "Reading", 1, "GROUP_NOT_ALLOWED"),
        ("2002", "Reading", 1, "NO_CAPABLE_MEMBER"),
        (GROUP, "", 1, "NAME_REQUIRED"),
        (GROUP, "   ", 1, "NAME_REQUIRED"),
        (GROUP, None, 1, "NAME_REQUIRED"),
        (GROUP, "a|b", 1, "NAME_INVALID"),
        (GROUP, "x" * 33, 1, "NAME_INVALID"),
        (GROUP, "Reading", 1.5, "TRANSITION_INVALID"),
        (GROUP, "Reading", -1, "TRANSITION_INVALID"),
        (GROUP, "Reading", 0xffff, "TRANSITION_INVALID"),
        (GROUP, "Reading", True, "TRANSITION_INVALID"),
    ])
    def test_create(self, mod, scenes, store, group, name, transition, code):
        assert error_code(scenes.create_scene, group, name, transition) == code
        mod.zcl_raw_add_scene.assert_not_called()
        assert store.keys() == []

    def test_duplicate_name_ignores_case(self, scenes):
        scenes.create_scene(GROUP, "Reading")
        assert error_code(scenes.create_scene, GROUP, " reading ") == "NAME_DUPLICATE"

    def test_the_same_name_is_fine_in_another_group(self, scenes, plugin):
        plugin.groupmgt.ListOfGroups["3003"] = {"Name": "Hall", "Devices": [[SOFA, "01", SOFA_IEEE]]}
        scenes.create_scene(GROUP, "Reading")
        assert scenes.create_scene("3003", "Reading")["sceneId"] == "01"

    def test_coordinator_busy(self, mod, scenes, plugin):
        plugin.ControllerLink.loadTransmit.return_value = mod.MAX_LOAD_ZIGATE + 1
        assert error_code(scenes.create_scene, GROUP, "Reading") == "COORDINATOR_BUSY"
        mod.zcl_raw_add_scene.assert_not_called()

    def test_scene_ids_exhausted(self, scenes, store):
        store.set(GROUP, {"scenes": {"%02x" % i: {"name": str(i), "members": {}} for i in range(1, 256)}})
        assert error_code(scenes.create_scene, GROUP, "Reading") == "SCENE_ID_EXHAUSTED"

    @pytest.mark.parametrize("request_name", ["capture_scene", "retry_scene", "recall_scene", "delete_scene"])
    def test_unknown_scene(self, scenes, request_name):
        assert error_code(getattr(scenes, request_name), GROUP, "07") == "SCENE_NOT_FOUND"

    def test_rename_unknown_scene(self, scenes):
        assert error_code(scenes.rename_scene, GROUP, "07", "New") == "SCENE_NOT_FOUND"

    def test_unknown_group_view(self, scenes):
        assert error_code(scenes.group_view, "dead") == "GROUP_NOT_FOUND"


# ─── Re-capture, retry, rename ───────────────────────────────────────────────

class TestRecapture:

    def _synced_scene(self, mod, scenes):
        scenes.create_scene(GROUP, "Reading", 2)
        complete_capture(mod, scenes, CEILING, "0b")
        complete_capture(mod, scenes, SOFA, "01")
        mod.zcl_raw_add_scene.reset_mock()
        mod.zcl_raw_store_scene.reset_mock()

    def test_keeps_the_scene_id(self, mod, scenes):
        self._synced_scene(mod, scenes)
        assert scenes.capture_scene(GROUP, "01")["sceneId"] == "01"
        assert mod.zcl_raw_add_scene.call_count == 2

    def test_a_member_that_missed_it_is_not_synced(self, mod, scenes, store):
        # Get Scene Membership would say synced: the scene ID is on the device already
        self._synced_scene(mod, scenes)
        scenes.capture_scene(GROUP, "01")
        complete_capture(mod, scenes, SOFA, "01")
        real = mod.time
        with patch.object(mod, "time", lambda: real() + mod.SCENE_RESPONSE_TIMEOUT + 1):
            scenes.heartbeat()
        assert stored(store)["members"][CEILING_IEEE + "-0b"]["status"] == "failed"
        assert stored(store)["members"][SOFA_IEEE + "-01"]["status"] == "synced"

    def test_a_new_transition_is_sent(self, mod, scenes, store):
        self._synced_scene(mod, scenes)
        scenes.capture_scene(GROUP, "01", 7)
        assert {c.args[6] for c in mod.zcl_raw_add_scene.call_args_list} == {7}
        assert stored(store)["transitionTime"] == 7

    def test_brings_in_a_member_added_since(self, mod, scenes, plugin):
        self._synced_scene(mod, scenes)
        plugin.ListOfDevices["c003"] = lamp("3132333435363738", "01", ("0005",))
        plugin.IEEE2NWK["3132333435363738"] = "c003"
        plugin.groupmgt.ListOfGroups[GROUP]["Devices"].append(["c003", "01", "3132333435363738"])
        assert [m["ieee"] for m in scenes.group_view(GROUP)["scenes"][0]["missing"]] == ["3132333435363738"]
        view = scenes.capture_scene(GROUP, "01")
        assert view["missing"] == []
        assert view["native"] == 3


class TestRetry:

    def test_only_failed_members(self, mod, scenes):
        scenes.create_scene(GROUP, "Reading", 2)
        complete_capture(mod, scenes, CEILING, "0b", status="89")
        complete_capture(mod, scenes, SOFA, "01")
        mod.zcl_raw_add_scene.reset_mock()
        scenes.retry_scene(GROUP, "01")
        mod.zcl_raw_add_scene.assert_called_once()
        assert mod.zcl_raw_add_scene.call_args.args[1:7] == (CEILING, "01", "0b", GROUP, "01", 2)

    def test_a_retried_member_is_pending_again(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        complete_capture(mod, scenes, CEILING, "0b", status="89")
        scenes.retry_scene(GROUP, "01")
        member = stored(store)["members"][CEILING_IEEE + "-0b"]
        assert (member["status"], member["error"]) == ("pending", None)
        complete_capture(mod, scenes, CEILING, "0b")
        assert stored(store)["members"][CEILING_IEEE + "-0b"]["status"] == "synced"


class TestRename:

    def test_nothing_goes_to_the_devices(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        mod.zcl_raw_add_scene.reset_mock()
        scenes.rename_scene(GROUP, "01", "Evening")
        assert stored(store)["name"] == "Evening"
        for name in COMMANDS:
            getattr(mod, name).assert_not_called()

    def test_a_scene_can_keep_its_name(self, scenes):
        scenes.create_scene(GROUP, "Reading")
        assert scenes.rename_scene(GROUP, "01", "READING")["name"] == "READING"

    def test_another_scene_name_is_refused(self, scenes):
        scenes.create_scene(GROUP, "Reading")
        scenes.create_scene(GROUP, "Dinner")
        assert error_code(scenes.rename_scene, GROUP, "02", "Reading") == "NAME_DUPLICATE"


# ─── Recall ──────────────────────────────────────────────────────────────────

class TestRecall:

    def test_one_group_cast(self, mod, scenes):
        scenes.create_scene(GROUP, "Reading")
        scenes.recall_scene(GROUP, "01")
        mod.zcl_raw_recall_scene.assert_called_once()
        call = mod.zcl_raw_recall_scene.call_args
        assert (call.args[1], call.args[4], call.args[5]) == (GROUP, GROUP, "01")
        assert call.kwargs["groupaddrmode"] is True

    def test_is_recorded(self, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        scenes.recall_scene(GROUP, "01")
        assert isinstance(stored(store)["lastRecalled"], int)

    def test_fallback_member_goes_to_its_level(self, mod, scenes):
        scenes.create_scene(GROUP, "Reading", 2)
        scenes.recall_scene(GROUP, "01")
        mod.zcl_move_to_level_with_onoff.assert_called_once()
        call = mod.zcl_move_to_level_with_onoff.call_args
        assert call.args[1:5] == (STRIP, "01", "01", "78")
        assert call.kwargs["transition"] == "0014"  # 2 s, in 1/10 s

    def test_fallback_member_off(self, mod, scenes, plugin):
        plugin.ListOfDevices[STRIP]["Ep"]["01"]["0006"]["0000"] = "00"
        scenes.create_scene(GROUP, "Reading")
        scenes.recall_scene(GROUP, "01")
        mod.zcl_onoff_off_noeffect.assert_called_once()
        mod.zcl_move_to_level_with_onoff.assert_not_called()

    def test_fallback_member_without_a_level(self, mod, scenes, plugin):
        del plugin.ListOfDevices[STRIP]["Ep"]["01"]["0008"]
        scenes.create_scene(GROUP, "Reading")
        scenes.recall_scene(GROUP, "01")
        mod.zcl_onoff_on.assert_called_once()

    def test_fallback_member_with_nothing_cached_gets_no_frame(self, mod, scenes, plugin):
        plugin.ListOfDevices[STRIP]["Ep"]["01"] = {}
        scenes.create_scene(GROUP, "Reading")
        scenes.recall_scene(GROUP, "01")
        mod.zcl_onoff_on.assert_not_called()
        mod.zcl_onoff_off_noeffect.assert_not_called()
        mod.zcl_move_to_level_with_onoff.assert_not_called()

    def test_a_member_gone_from_the_group_is_left_alone(self, mod, scenes, plugin):
        scenes.create_scene(GROUP, "Reading")
        devices = plugin.groupmgt.ListOfGroups[GROUP]["Devices"]
        plugin.groupmgt.ListOfGroups[GROUP]["Devices"] = [d for d in devices if d[0] != STRIP]
        scenes.recall_scene(GROUP, "01")
        mod.zcl_move_to_level_with_onoff.assert_not_called()

    def test_without_a_native_member_no_group_cast(self, mod, scenes, plugin):
        scenes.create_scene(GROUP, "Reading")
        devices = plugin.groupmgt.ListOfGroups[GROUP]["Devices"]
        plugin.groupmgt.ListOfGroups[GROUP]["Devices"] = [d for d in devices if d[0] == STRIP]
        scenes.recall_scene(GROUP, "01")
        mod.zcl_raw_recall_scene.assert_not_called()
        mod.zcl_move_to_level_with_onoff.assert_called_once()


# ─── Removal ─────────────────────────────────────────────────────────────────

class TestDelete:

    def test_goes_to_each_native_member(self, mod, scenes):
        scenes.create_scene(GROUP, "Reading")
        scenes.delete_scene(GROUP, "01")
        sent = {c.args[1:6] for c in mod.zcl_raw_remove_scene.call_args_list}
        assert sent == {(CEILING, "01", "0b", GROUP, "01"), (SOFA, "01", "01", GROUP, "01")}

    def test_the_last_scene_takes_the_record(self, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        scenes.delete_scene(GROUP, "01")
        assert store.keys() == []

    def test_a_capture_in_progress_stops(self, mod, scenes):
        scenes.create_scene(GROUP, "Reading")
        scenes.delete_scene(GROUP, "01")
        scenes.scene_response("Add", CEILING, "0b", "00", GROUP, "01")
        mod.zcl_raw_store_scene.assert_not_called()


class TestMemberRemoved:

    def test_remove_all_scenes_once_for_the_group(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        scenes.create_scene(GROUP, "Dinner")
        scenes.member_removed(GROUP, CEILING, "0b", CEILING_IEEE)
        mod.zcl_raw_remove_all_scenes.assert_called_once()
        assert mod.zcl_raw_remove_all_scenes.call_args.args[1:5] == (CEILING, "01", "0b", GROUP)
        for scene in ("01", "02"):
            assert CEILING_IEEE + "-0b" not in stored(store, scene)["members"]

    def test_fallback_member_gets_no_frame(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        scenes.member_removed(GROUP, STRIP, "01", STRIP_IEEE)
        mod.zcl_raw_remove_all_scenes.assert_not_called()
        assert STRIP_IEEE + "-01" not in stored(store)["members"]

    def test_a_device_in_no_scene_gets_no_frame(self, mod, scenes):
        scenes.create_scene(GROUP, "Reading")
        scenes.member_removed(GROUP, REMOTE, "01", REMOTE_IEEE)
        mod.zcl_raw_remove_all_scenes.assert_not_called()

    def test_the_last_member_takes_the_scene(self, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        scenes.member_removed(GROUP, CEILING, "0b", CEILING_IEEE)
        scenes.member_removed(GROUP, SOFA, "01", SOFA_IEEE)
        scenes.member_removed(GROUP, STRIP, "01", STRIP_IEEE)
        assert store.keys() == []

    def test_a_group_without_scenes(self, mod, scenes):
        scenes.member_removed("2002", STRIP, "01", STRIP_IEEE)
        mod.zcl_raw_remove_all_scenes.assert_not_called()


class TestStoreSurvivesTheGroups:

    def test_a_group_list_lost_costs_no_scene(self, scenes, plugin, store):
        scenes.create_scene(GROUP, "Reading")
        plugin.groupmgt.ListOfGroups.clear()
        assert scenes.groups_view() == []
        scenes.heartbeat()
        assert store.keys() == [GROUP]

    def test_a_member_gone_outside_the_plugin_stays_in_the_store(self, scenes, plugin, store):
        scenes.create_scene(GROUP, "Reading")
        devices = plugin.groupmgt.ListOfGroups[GROUP]["Devices"]
        plugin.groupmgt.ListOfGroups[GROUP]["Devices"] = [d for d in devices if d[0] != SOFA]
        view = scenes.group_view(GROUP)["scenes"][0]
        assert SOFA_IEEE not in [m["ieee"] for m in view["members"]]
        assert SOFA_IEEE + "-01" in stored(store)["members"]


# ─── Scan ────────────────────────────────────────────────────────────────────

def scan_both(scenes, ceiling, sofa):
    scenes.scan_group(GROUP)
    scenes.membership_response(CEILING, "0b", "00", GROUP, ceiling)
    scenes.membership_response(SOFA, "01", "00", GROUP, sofa)


class TestScan:

    def test_asks_each_native_member_and_no_other(self, mod, scenes):
        view = scenes.scan_group(GROUP)
        assert [c.args[1] for c in mod.zcl_raw_get_scene_membership.call_args_list] == [CEILING, SOFA]
        assert view["scan"]["running"] is True
        assert view["scan"]["members"] == 2

    def test_a_scene_set_by_something_else_appears(self, scenes, store):
        scenes.scan_group(GROUP)
        scenes.membership_response(CEILING, "0b", "00", GROUP, ["03"])
        found = stored(store, "03")
        assert found["name"] == "Scene 03"
        assert found["discovered"] is True
        assert found["transitionTime"] is None
        assert found["members"][CEILING_IEEE + "-0b"]["status"] == "synced"

    def test_the_two_members_end_up_in_one_scene(self, scenes):
        scenes.scan_group(GROUP)
        scenes.membership_response(CEILING, "0b", "00", GROUP, ["03"])
        scenes.membership_response(SOFA, "01", "00", GROUP, ["03"])
        view = scenes.group_view(GROUP)
        assert [(s["sceneId"], s["discovered"], s["synced"], s["native"]) for s in view["scenes"]] == [("03", True, 2, 2)]
        assert view["scan"] == {"running": False, "at": view["scan"]["at"], "members": 2, "found": 1, "noAnswer": []}

    def test_a_member_without_the_scene_is_offered_a_capture(self, scenes):
        scenes.scan_group(GROUP)
        scenes.membership_response(CEILING, "0b", "00", GROUP, ["03"])
        scenes.membership_response(SOFA, "01", "00", GROUP, [])
        scene = scenes.group_view(GROUP)["scenes"][0]
        assert (scene["synced"], scene["native"]) == (1, 1)
        assert SOFA_IEEE in [member["ieee"] for member in scene["missing"]]

    def test_a_capture_after_a_scan_skips_the_id_found(self, mod, scenes):
        scenes.scan_group(GROUP)
        scenes.membership_response(CEILING, "0b", "00", GROUP, ["01", "02"])
        assert scenes.create_scene(GROUP, "Reading")["sceneId"] == "03"

    def test_a_scene_name_already_taken_is_not_reused(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Scene 03")
        scenes.scan_group(GROUP)
        scenes.membership_response(CEILING, "0b", "00", GROUP, ["03"])
        assert stored(store, "03")["name"] == "Scene 03 (2)"

    def test_a_scene_the_plugin_knows_is_not_touched(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Reading", 4)
        complete_capture(mod, scenes, CEILING, "0b")
        scenes.scan_group(GROUP)
        scenes.membership_response(CEILING, "0b", "00", GROUP, ["01"])
        scene = stored(store)
        assert (scene["name"], scene["transitionTime"], "discovered" in scene) == ("Reading", 4, False)

    def test_a_scene_lost_by_a_member_shows_as_failed_and_comes_back(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        complete_capture(mod, scenes, CEILING, "0b")
        scan_both(scenes, [], [])
        member = stored(store)["members"][CEILING_IEEE + "-0b"]
        assert (member["status"], member["error"]) == ("failed", "absent")

        scan_both(scenes, ["01"], [])
        member = stored(store)["members"][CEILING_IEEE + "-0b"]
        assert (member["status"], member["error"]) == ("synced", None)

    def test_a_capture_in_progress_is_left_to_finish(self, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        scenes.scan_group(GROUP)
        scenes.membership_response(CEILING, "0b", "00", GROUP, [])
        assert stored(store)["members"][CEILING_IEEE + "-0b"]["status"] == "pending"

    def test_a_failed_store_stays_failed_when_the_id_is_there(self, mod, scenes, store):
        scenes.create_scene(GROUP, "Reading")
        complete_capture(mod, scenes, CEILING, "0b", status="89")
        scenes.scan_group(GROUP)
        scenes.membership_response(CEILING, "0b", "00", GROUP, ["01"])
        assert stored(store)["members"][CEILING_IEEE + "-0b"]["status"] == "failed"

    def test_a_refused_scan_learns_nothing(self, scenes, store, plugin):
        plugin.ListOfDevices[CEILING]["ZDeviceName"] = "Ceiling"
        scenes.scan_group(GROUP)
        scenes.membership_response(CEILING, "0b", "85", GROUP, [])
        assert store.get(GROUP) is None
        assert scenes.group_view(GROUP)["scan"]["noAnswer"] == ["Ceiling"]

    def test_a_silent_member_ends_the_scan_by_timeout(self, mod, scenes, plugin):
        plugin.ListOfDevices[SOFA]["ZDeviceName"] = "Sofa"
        scenes.scan_group(GROUP)
        scenes.membership_response(CEILING, "0b", "00", GROUP, [])
        with patch.object(mod, "time", return_value=time.time() + mod.SCENE_RESPONSE_TIMEOUT + 1):
            scenes.heartbeat()
        scan = scenes.group_view(GROUP)["scan"]
        assert (scan["running"], scan["noAnswer"]) == (False, ["Sofa"])

    def test_a_second_scan_waits_for_the_first(self, mod, scenes):
        scenes.scan_group(GROUP)
        scenes.scan_group(GROUP)
        assert mod.zcl_raw_get_scene_membership.call_count == 2

    def test_a_response_out_of_a_scan_is_ignored(self, scenes, store):
        scenes.membership_response(CEILING, "0b", "00", GROUP, ["03"])
        assert store.get(GROUP) is None

    def test_refused_like_a_capture(self, scenes, plugin):
        assert error_code(scenes.scan_group, "0000") == "GROUP_NOT_ALLOWED"
        assert error_code(scenes.scan_group, "2002") == "NO_CAPABLE_MEMBER"
        assert error_code(scenes.scan_group, "9999") == "GROUP_NOT_FOUND"
        plugin.ControllerLink.loadTransmit.return_value = 99
        assert error_code(scenes.scan_group, GROUP) == "COORDINATOR_BUSY"


class TestDiscoveredScene:

    @pytest.fixture
    def found(self, scenes):
        scan_both(scenes, ["03"], [])
        return scenes

    def test_can_be_recalled(self, mod, found):
        found.recall_scene(GROUP, "03")
        assert mod.zcl_raw_recall_scene.call_args.args[4:6] == (GROUP, "03")

    def test_can_be_renamed(self, found, store):
        found.rename_scene(GROUP, "03", "Movie")
        assert stored(store, "03")["name"] == "Movie"

    def test_a_capture_makes_it_a_scene_of_the_plugin(self, mod, found, store):
        found.capture_scene(GROUP, "03", 2)
        assert stored(store, "03")["transitionTime"] == 2
        assert "discovered" not in stored(store, "03")

    def test_a_capture_without_a_transition_time_gets_the_default(self, mod, found, store):
        found.capture_scene(GROUP, "03")
        assert stored(store, "03")["transitionTime"] == 1
        assert mod.zcl_raw_add_scene.call_args.args[6] == 1

    def test_a_retry_sends_a_valid_transition_time(self, mod, found):
        scan_both(found, [], [])
        found.retry_scene(GROUP, "03")
        assert mod.zcl_raw_add_scene.call_args.args[6] == 1

    def test_deleting_it_removes_it_from_the_devices(self, mod, found, store):
        found.delete_scene(GROUP, "03")
        assert mod.zcl_raw_remove_scene.call_args.args[1] == CEILING
        assert store.get(GROUP) is None


# ─── Logging ─────────────────────────────────────────────────────────────────

def logged(plugin, level):
    """(module, message) of what went to the plugin log at this level."""
    return [(c.args[0], c.args[2]) for c in plugin.log.logging.call_args_list if c.args[1] == level]


class TestLogging:

    def test_scene_actions_log_under_scene(self, scenes, plugin):
        scenes.create_scene(GROUP, "Reading")
        scenes.rename_scene(GROUP, "01", "Evening")
        scenes.recall_scene(GROUP, "01")
        scenes.delete_scene(GROUP, "01")
        debug = logged(plugin, "Debug")
        assert {module for module, _ in debug} == {"Scene"}
        for action in ("create_scene", "_capture", "rename_scene", "recall_scene", "delete_scene"):
            assert any(message.startswith(action) for _, message in debug), action

    def test_the_outcome_of_a_capture_is_followed(self, mod, scenes, plugin):
        scenes.create_scene(GROUP, "Reading")
        complete_capture(mod, scenes, CEILING, "0b")
        messages = [message for _, message in logged(plugin, "Debug")]
        assert any("sending Store" in message for message in messages)
        assert any(message.endswith("synced") for message in messages)

    def test_a_response_nobody_waits_for_is_traced(self, scenes, plugin):
        scenes.scene_response("Add", CEILING, "0b", "00", GROUP, "07")
        assert any("not waited for" in message for _, message in logged(plugin, "Debug"))

    def test_a_refused_rename_does_not_log_as_done(self, scenes, plugin):
        scenes.create_scene(GROUP, "Reading")
        error_code(scenes.rename_scene, GROUP, "01", "a|b")
        assert not any(message.startswith("rename_scene") for _, message in logged(plugin, "Debug"))

    def test_a_member_leaving_logs_under_groups_and_scene(self, scenes, plugin):
        scenes.create_scene(GROUP, "Reading")
        plugin.log.logging.reset_mock()
        scenes.member_removed(GROUP, CEILING, "0b", CEILING_IEEE)
        assert [module for module, _ in logged(plugin, "Debug")] == [["Groups", "Scene"]]

    def test_a_failed_store_still_reaches_the_log_without_debug(self, mod, scenes, plugin):
        scenes.create_scene(GROUP, "Reading")
        complete_capture(mod, scenes, CEILING, "0b", status="89")
        assert [module for module, _ in logged(plugin, "Log")] == ["Scene"]
