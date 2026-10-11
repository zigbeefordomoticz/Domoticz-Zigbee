"""
tests/Modules/test_legrand_group_id_allocation.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for legrand_preferred_group_id() and the allocation it feeds in
get_groupid_for_remote(), in Modules/legrand_netatmo.py.

A Legrand remote gets one group per gang, allocated out of the 0xFE00-0xFEFE band.
get_available_grp_id() returns the highest id in that band that is not already a
group, so the id a gang ended up with depended on the rest of the group list: create
a group at 0xfefe first and gang 01 silently landed on 0xfefd. Deriving the id from
the gang keeps it predictable, and lets a group that already exists at that id be
adopted rather than stepped over.

The module is imported in isolation against minimal stubs so no Domoticz framework or
radio backend is required.

Run with:
    pytest tests/Modules/test_legrand_group_id_allocation.py -v
"""

import sys
import types
from unittest.mock import MagicMock

import pytest

# Only what Modules/legrand_netatmo.py imports at module level.
_LEGRAND_DEPS = {
    "Modules.basicOutputs": dict(
        read_attribute=MagicMock(),
        write_attribute=MagicMock(),
        write_attributeNoResponse=MagicMock(),
    ),
    "Modules.bindings": dict(bindDevice=MagicMock(), unbindDevice=MagicMock()),
    "Modules.domoMaj": dict(MajDomoDevice=MagicMock()),
    "Modules.readAttributes": dict(
        ReadAttributeRequest_0b04_050b=MagicMock(),
        ReadAttributeRequest_0001=MagicMock(),
        ReadAttributeRequest_0006_0000=MagicMock(),
        ReadAttributeRequest_fc01=MagicMock(),
        ReadAttributeRequest_fc40=MagicMock(),
    ),
    "Modules.sendZigateCommand": dict(raw_APS_request=MagicMock()),
    "Modules.tools": dict(
        extract_info_from_8085=MagicMock(),
        get_and_inc_ZCL_SQN=MagicMock(return_value="01"),
        get_deviceconf_parameter_value=MagicMock(return_value=None),
        is_ack_tobe_disabled=MagicMock(return_value=False),
        retreive_cmd_payload_from_8002=MagicMock(),
    ),
    "Modules.zigateConsts": dict(
        HEARTBEAT=5,
        LEGRAND_REMOTES=("Remote switch", "Double gangs remote switch"),
        MAX_LOAD_ZIGATE=3,
        ZIGATE_EP="01",
    ),
}


def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


@pytest.fixture(scope="module")
def legrand():
    """Load legrand_netatmo from its file path, with its imports stubbed."""
    import importlib.util
    import pathlib

    module_path = pathlib.Path(__file__).parents[2] / "Modules" / "legrand_netatmo.py"

    saved = {name: sys.modules.pop(name, None) for name in _LEGRAND_DEPS}
    for name, attrs in _LEGRAND_DEPS.items():
        sys.modules[name] = _make_stub(name, **attrs)

    spec = importlib.util.spec_from_file_location("Modules.legrand_netatmo", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    yield module

    for name in _LEGRAND_DEPS:
        sys.modules.pop(name, None)
        if saved.get(name) is not None:
            sys.modules[name] = saved[name]


DOUBLE_GANGS = {"Ep": {"01": {}, "02": {}}, "Model": "Double gangs remote switch"}
SINGLE_GANG = {"Ep": {"01": {}}, "Model": "Remote switch"}


class _FakeSelf:
    def __init__(self, list_of_devices=None, groupmgt=None):
        self.ListOfDevices = list_of_devices if list_of_devices is not None else {}
        self.groupmgt = groupmgt
        self.log = types.SimpleNamespace(logging=MagicMock())


class TestLegrandPreferredGroupId:

    def test_first_gang_gets_the_top_of_the_band(self, legrand):
        plugin = _FakeSelf({"ee9f": dict(DOUBLE_GANGS)})
        assert legrand.legrand_preferred_group_id(plugin, "ee9f", "01") == "fefe"

    def test_second_gang_gets_the_next_one_down(self, legrand):
        plugin = _FakeSelf({"ee9f": dict(DOUBLE_GANGS)})
        assert legrand.legrand_preferred_group_id(plugin, "ee9f", "02") == "fefd"

    def test_single_gang_remote_gets_the_top_of_the_band(self, legrand):
        plugin = _FakeSelf({"ee9f": dict(SINGLE_GANG)})
        assert legrand.legrand_preferred_group_id(plugin, "ee9f", None) == "fefe"

    def test_highest_gang_stays_inside_the_band(self, legrand):
        plugin = _FakeSelf({"ee9f": dict(DOUBLE_GANGS)})
        assert legrand.legrand_preferred_group_id(plugin, "ee9f", "ff") == "fe00"

    def test_gang_zero_is_refused(self, legrand):
        plugin = _FakeSelf({"ee9f": dict(DOUBLE_GANGS)})
        assert legrand.legrand_preferred_group_id(plugin, "ee9f", "00") is None

    def test_unparsable_gang_is_refused(self, legrand):
        plugin = _FakeSelf({"ee9f": dict(DOUBLE_GANGS)})
        assert legrand.legrand_preferred_group_id(plugin, "ee9f", "zz") is None

    def test_id_held_by_another_remote_is_refused(self, legrand):
        plugin = _FakeSelf({
            "ee9f": dict(DOUBLE_GANGS),
            "1111": {"Legrand": {"RemoteGroup": {"01": "fefe"}}},
        })
        assert legrand.legrand_preferred_group_id(plugin, "ee9f", "01") is None

    def test_id_held_by_this_remote_itself_is_not_a_collision(self, legrand):
        plugin = _FakeSelf({"ee9f": {**DOUBLE_GANGS, "Legrand": {"RemoteGroup": {"01": "fefe"}}}})
        assert legrand.legrand_preferred_group_id(plugin, "ee9f", "01") == "fefe"

    def test_malformed_legrand_records_are_ignored(self, legrand):
        """Device records carrying "" or a non-dict where a dict is expected."""
        plugin = _FakeSelf({
            "ee9f": dict(DOUBLE_GANGS),
            "1111": {"Legrand": ""},
            "2222": {"Legrand": {"RemoteGroup": ""}},
            "3333": "not a dict",
        })
        assert legrand.legrand_preferred_group_id(plugin, "ee9f", "01") == "fefe"


class TestGetGroupIdForRemoteAllocation:

    def _plugin(self, devices=None):
        plugin = _FakeSelf(devices if devices is not None else {"ee9f": dict(DOUBLE_GANGS)})
        plugin.groupmgt = MagicMock()
        plugin.groupmgt.get_available_grp_id = MagicMock(return_value="fe42")
        return plugin

    def test_preferred_id_is_used_without_scanning_the_band(self, legrand):
        plugin = self._plugin()
        assert legrand.get_groupid_for_remote(plugin, "ee9f", "01", "01") == "fefe"
        plugin.groupmgt.get_available_grp_id.assert_not_called()

    def test_an_existing_group_at_the_preferred_id_is_reused(self, legrand):
        """
        The behaviour this change is for: a group already sitting at 0xfefe, holding
        the devices the gang should drive, is adopted rather than stepped over.
        """
        plugin = self._plugin()
        plugin.groupmgt.ListOfGroups = {"fefe": {"Name": "Kitchen", "Devices": []}}
        assert legrand.get_groupid_for_remote(plugin, "ee9f", "01", "01") == "fefe"
        plugin.groupmgt.add_group_member_ship_from_remote.assert_called_once_with("ee9f", "01", "fefe")

    def test_falls_back_to_the_band_scan_when_another_remote_holds_the_id(self, legrand):
        plugin = self._plugin({
            "ee9f": dict(DOUBLE_GANGS),
            "1111": {"Legrand": {"RemoteGroup": {"01": "fefe"}}},
        })
        assert legrand.get_groupid_for_remote(plugin, "ee9f", "01", "01") == "fe42"
        plugin.groupmgt.get_available_grp_id.assert_called_once_with(0xFEFE, 0xFE00)

    def test_the_two_gangs_get_the_two_top_ids(self, legrand):
        plugin = self._plugin()
        assert legrand.get_groupid_for_remote(plugin, "ee9f", "01", "01") == "fefe"
        assert legrand.get_groupid_for_remote(plugin, "ee9f", "02", "02") == "fefd"
        plugin.groupmgt.get_available_grp_id.assert_not_called()

    def test_an_already_reserved_gang_keeps_its_id(self, legrand):
        """Unchanged behaviour: the stored id is returned without allocating again."""
        plugin = self._plugin({"ee9f": {**DOUBLE_GANGS, "Legrand": {"RemoteGroup": {"02": "fe10"}}}})
        assert legrand.get_groupid_for_remote(plugin, "ee9f", "02", "02") == "fe10"
        plugin.groupmgt.add_group_member_ship_from_remote.assert_not_called()
