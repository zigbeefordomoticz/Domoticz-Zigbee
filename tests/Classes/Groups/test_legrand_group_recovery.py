"""
tests/Classes/Groups/test_legrand_group_recovery.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for recover_legrand_groups_from_devices() in
Classes/GroupMgtv2/GrpServices.py.

A Legrand remote keeps its group assignment internally, told to it with fc01 command
0x0c, and it cannot be read back. The plugin's only record is
ListOfDevices[nwkid]["Legrand"]["RemoteGroup"]. When the group list is lost while the
device list survives, the remote goes on commanding a group the plugin no longer
knows and every press logs "update_domoticz_group_device - unknown group: fefe".

The module is loaded in isolation against stubs, so the decisions are observed through
checkToCreateOrUpdateGroup() and LookForGroupAndCreateIfNeeded() rather than by
building real groups.
"""

import sys
import types
from unittest.mock import MagicMock

import pytest

NWKID = "a80f"
IEEE = "000474000082702a"


def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def _deps():
    """Fresh stubs per test: the mocks carry the call history the tests assert on."""
    return {
        "Classes.GroupMgtv2.GrpCallBackResponses": dict(checkToCreateOrUpdateGroup=MagicMock()),
        "Classes.GroupMgtv2.GrpCommands": dict(
            add_group_member_ship=MagicMock(),
            check_group_member_ship=MagicMock(),
            look_for_group_member_ship=MagicMock(),
            remove_group_member_ship=MagicMock(),
            send_group_member_ship_identify_effect=MagicMock(),
        ),
        "Classes.GroupMgtv2.GrpDatabase": dict(
            check_if_group_empty=MagicMock(return_value=False),
            checkNwkIdAndUpdateIfAny=MagicMock(),
            create_group=MagicMock(),
            remove_group=MagicMock(),
            remove_nwkid_from_all_groups=MagicMock(),
        ),
        "Classes.GroupMgtv2.GrpDomoticz": dict(
            LookForGroupAndCreateIfNeeded=MagicMock(),
            create_domoticz_group_device=MagicMock(),
            remove_domoticz_group_device=MagicMock(),
            update_domoticz_group_name=MagicMock(),
        ),
        "Classes.GroupMgtv2.GrpIkeaRemote": dict(
            checkIfIkeaRound5BToBeAdded=MagicMock(return_value=False),
            checkIfIkeaRound5BToBeRemoved=MagicMock(return_value=False),
        ),
        "Modules.domoticzAbstractLayer": dict(find_first_unit_widget_from_deviceID=MagicMock(return_value=1)),
        "Modules.tools": dict(mainPoweredDevice=MagicMock(return_value=True)),
            "Modules.zigateConsts": dict(LEGRAND_REMOTES=("Double gangs remote switch",)),
    }


@pytest.fixture(scope="module")
def grp():
    """
    Load GrpServices from its file path with its imports stubbed.

    Module scoped on purpose: swapping entries in and out of sys.modules once per test
    churned the import cache enough to disturb an unrelated test elsewhere in the
    suite, so the swap happens once and the mocks are reset between tests by
    reset_stub_mocks below.
    """
    import importlib.util
    import pathlib

    module_path = pathlib.Path(__file__).parents[3] / "Classes" / "GroupMgtv2" / "GrpServices.py"

    deps = _deps()
    saved = {name: sys.modules.pop(name, None) for name in deps}
    for name, attrs in deps.items():
        sys.modules[name] = _make_stub(name, **attrs)

    spec = importlib.util.spec_from_file_location("Classes.GroupMgtv2.GrpServices", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    yield module

    for name in deps:
        sys.modules.pop(name, None)
        if saved.get(name) is not None:
            sys.modules[name] = saved[name]


@pytest.fixture(autouse=True)
def reset_stub_mocks(grp):
    """The tests assert on call history, so every mock starts each test clean."""
    mocks = (
        grp.checkToCreateOrUpdateGroup,
        grp.LookForGroupAndCreateIfNeeded,
        grp.find_first_unit_widget_from_deviceID,
    )
    for mock in mocks:
        mock.reset_mock()
    grp.find_first_unit_widget_from_deviceID.return_value = 1
    yield


def _remote(remote_group, ep=None):
    return {
        "IEEE": IEEE,
        "Model": "Double gangs remote switch",
        "Ep": ep if ep is not None else {"01": {}, "02": {}},
        "Legrand": {"RemoteGroup": remote_group},
    }


class _FakeSelf:
    def __init__(self, list_of_devices=None, list_of_groups=None):
        self.ListOfDevices = list_of_devices if list_of_devices is not None else {}
        self.ListOfGroups = list_of_groups if list_of_groups is not None else {}
        self.Devices = {}
        self.logging = MagicMock()


def _group_with(ieee, ep="01"):
    return {"Name": "Zigate Group", "Devices": [[NWKID, ep, ieee]]}


class TestRecoverLegrandGroups:

    def test_missing_groups_are_recreated_on_the_gang_endpoint(self, grp):
        """The reported case: device record intact, ListOfGroups empty."""
        plugin = _FakeSelf({NWKID: _remote({"01": "fefe", "02": "fefd"})}, {})
        grp.recover_legrand_groups_from_devices(plugin)

        calls = [call.args for call in grp.checkToCreateOrUpdateGroup.call_args_list]
        assert calls == [(plugin, NWKID, "01", "fefe"), (plugin, NWKID, "02", "fefd")]

    def test_a_healthy_installation_is_left_alone(self, grp):
        plugin = _FakeSelf(
            {NWKID: _remote({"01": "fefe", "02": "fefd"})},
            {"fefe": _group_with(IEEE, "01"), "fefd": _group_with(IEEE, "02")},
        )
        grp.recover_legrand_groups_from_devices(plugin)

        grp.checkToCreateOrUpdateGroup.assert_not_called()
        grp.LookForGroupAndCreateIfNeeded.assert_not_called()

    def test_a_group_that_lost_the_remote_gets_it_back(self, grp):
        plugin = _FakeSelf(
            {NWKID: _remote({"01": "fefe"})},
            {"fefe": {"Name": "Kitchen", "Devices": [["1111", "01", "00158d0001aaaaaa"]]}},
        )
        grp.recover_legrand_groups_from_devices(plugin)
        grp.checkToCreateOrUpdateGroup.assert_called_once_with(plugin, NWKID, "01", "fefe")

    def test_a_group_without_its_domoticz_widget_is_recreated(self, grp):
        plugin = _FakeSelf({NWKID: _remote({"01": "fefe"})}, {"fefe": _group_with(IEEE, "01")})
        grp.find_first_unit_widget_from_deviceID.return_value = None

        grp.recover_legrand_groups_from_devices(plugin)

        grp.LookForGroupAndCreateIfNeeded.assert_called_once_with(plugin, "fefe")
        grp.checkToCreateOrUpdateGroup.assert_not_called()

    def test_single_gang_remote_recovers_on_endpoint_01(self, grp):
        plugin = _FakeSelf({NWKID: _remote({"Single": "fefe"}, ep={"01": {}})}, {})
        grp.recover_legrand_groups_from_devices(plugin)
        grp.checkToCreateOrUpdateGroup.assert_called_once_with(plugin, NWKID, "01", "fefe")

    def test_a_gang_the_device_does_not_expose_falls_back_to_endpoint_01(self, grp):
        plugin = _FakeSelf({NWKID: _remote({"02": "fefd"}, ep={"01": {}})}, {})
        grp.recover_legrand_groups_from_devices(plugin)
        grp.checkToCreateOrUpdateGroup.assert_called_once_with(plugin, NWKID, "01", "fefd")

    def test_a_gang_with_no_group_reserved_yet_is_skipped(self, grp):
        plugin = _FakeSelf({NWKID: _remote({"01": None, "02": "fefd"})}, {})
        grp.recover_legrand_groups_from_devices(plugin)
        grp.checkToCreateOrUpdateGroup.assert_called_once_with(plugin, NWKID, "02", "fefd")

    @pytest.mark.parametrize("status", ["Leave", "Removed"])
    def test_a_remote_that_has_left_is_not_recovered(self, grp, status):
        device = _remote({"01": "fefe"})
        device["Status"] = status
        plugin = _FakeSelf({NWKID: device}, {})
        grp.recover_legrand_groups_from_devices(plugin)
        grp.checkToCreateOrUpdateGroup.assert_not_called()
        grp.LookForGroupAndCreateIfNeeded.assert_not_called()

    def test_a_remote_still_in_the_network_is_recovered(self, grp):
        device = _remote({"01": "fefe"})
        device["Status"] = "inDB"
        plugin = _FakeSelf({NWKID: device}, {})
        grp.recover_legrand_groups_from_devices(plugin)
        grp.checkToCreateOrUpdateGroup.assert_called_once_with(plugin, NWKID, "01", "fefe")

    def test_devices_without_a_legrand_record_are_ignored(self, grp):
        plugin = _FakeSelf({"1111": {"IEEE": "00158d0001aaaaaa", "Ep": {"01": {}}}}, {})
        grp.recover_legrand_groups_from_devices(plugin)
        grp.checkToCreateOrUpdateGroup.assert_not_called()

    def test_malformed_records_do_not_raise(self, grp):
        plugin = _FakeSelf(
            {
                "1111": "not a dict",
                "2222": {"Legrand": ""},
                "3333": {"Legrand": {"RemoteGroup": ""}},
                "4444": {"Legrand": {}},
                NWKID: _remote({"01": "fefe"}),
            },
            {},
        )
        grp.recover_legrand_groups_from_devices(plugin)
        grp.checkToCreateOrUpdateGroup.assert_called_once_with(plugin, NWKID, "01", "fefe")

    def test_a_group_whose_devices_list_is_malformed_is_treated_as_missing_the_remote(self, grp):
        plugin = _FakeSelf({NWKID: _remote({"01": "fefe"})}, {"fefe": {"Devices": [None, ["short"]]}})
        grp.recover_legrand_groups_from_devices(plugin)
        grp.checkToCreateOrUpdateGroup.assert_called_once_with(plugin, NWKID, "01", "fefe")

    def test_a_remote_without_an_ieee_is_treated_as_missing(self, grp):
        """Without an IEEE nothing can be matched, so the group is rebuilt; the real
        checkToCreateOrUpdateGroup() then returns early on the same missing IEEE."""
        device = _remote({"01": "fefe"})
        del device["IEEE"]
        plugin = _FakeSelf({NWKID: device}, {"fefe": _group_with(IEEE, "01")})
        grp.recover_legrand_groups_from_devices(plugin)
        grp.checkToCreateOrUpdateGroup.assert_called_once_with(plugin, NWKID, "01", "fefe")
