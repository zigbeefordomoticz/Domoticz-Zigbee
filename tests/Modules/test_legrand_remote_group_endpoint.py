"""
tests/Modules/test_legrand_remote_group_endpoint.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for legrand_remote_group_endpoint() and the endpoint it hands to
get_groupid_for_remote(), in Modules/legrand_netatmo.py.

A Legrand remote sends every fc01 frame from endpoint 01, whatever gang was pressed,
and identifies the gang with the leftright byte. The group membership must be recorded
against the endpoint that emits that gang's commands (gang 02 -> endpoint 02), while
the fc01 command itself must keep going to endpoint 01, where the cluster lives.

The module is imported in isolation against minimal stubs so no Domoticz framework or
radio backend is required.

Run with:
    pytest tests/Modules/test_legrand_remote_group_endpoint.py -v
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


class TestLegrandRemoteGroupEndpoint:

    def test_second_gang_maps_to_endpoint_02(self, legrand):
        plugin = _FakeSelf({"ee9f": dict(DOUBLE_GANGS)})
        assert legrand.legrand_remote_group_endpoint(plugin, "ee9f", "01", "02") == "02"

    def test_first_gang_stays_on_endpoint_01(self, legrand):
        plugin = _FakeSelf({"ee9f": dict(DOUBLE_GANGS)})
        assert legrand.legrand_remote_group_endpoint(plugin, "ee9f", "01", "01") == "01"

    def test_no_leftright_keeps_the_source_endpoint(self, legrand):
        """Single gang remotes send no leftright byte: endpoint 01 is already right."""
        plugin = _FakeSelf({"ee9f": dict(SINGLE_GANG)})
        assert legrand.legrand_remote_group_endpoint(plugin, "ee9f", "01", None) == "01"

    def test_leftright_the_device_does_not_expose_keeps_the_source_endpoint(self, legrand):
        """
        Only the double gangs model has been observed. A remote declaring a single
        endpoint must not get a member on an endpoint it does not have.
        """
        plugin = _FakeSelf({"ee9f": dict(SINGLE_GANG)})
        assert legrand.legrand_remote_group_endpoint(plugin, "ee9f", "01", "02") == "01"

    def test_unknown_device_keeps_the_source_endpoint(self, legrand):
        plugin = _FakeSelf({})
        assert legrand.legrand_remote_group_endpoint(plugin, "ee9f", "01", "02") == "01"

    def test_device_without_ep_keeps_the_source_endpoint(self, legrand):
        plugin = _FakeSelf({"ee9f": {}})
        assert legrand.legrand_remote_group_endpoint(plugin, "ee9f", "01", "02") == "01"


class TestAssignGroupMembershipEndpoints:
    """
    The two endpoints must not be conflated: membership follows the gang, while the
    fc01 command keeps going to endpoint 01, the only endpoint carrying that cluster.
    """

    def _run(self, legrand, monkeypatch, leftright, device=None):
        plugin = _FakeSelf({"ee9f": dict(device or DOUBLE_GANGS)})
        plugin.groupmgt = MagicMock()
        plugin.groupmgt.get_available_grp_id = MagicMock(return_value="fefd")

        sent = MagicMock()
        monkeypatch.setattr(legrand, "send_legrand_command", sent)
        monkeypatch.setattr(legrand, "get_and_inc_ZCL_SQN", MagicMock(return_value="01"))

        legrand.assign_group_membership_to_legrand_remote(plugin, "ee9f", "01", leftright)
        return plugin, sent

    def test_second_gang_is_registered_on_endpoint_02(self, legrand, monkeypatch):
        plugin, _ = self._run(legrand, monkeypatch, "02")
        plugin.groupmgt.add_group_member_ship_from_remote.assert_called_once_with("ee9f", "02", "fefd")

    def test_first_gang_is_registered_on_endpoint_01(self, legrand, monkeypatch):
        plugin, _ = self._run(legrand, monkeypatch, "01")
        plugin.groupmgt.add_group_member_ship_from_remote.assert_called_once_with("ee9f", "01", "fefd")

    def test_fc01_command_still_goes_to_endpoint_01(self, legrand, monkeypatch):
        """Regression guard: fc01 is absent from endpoint 02, so the command must not move."""
        _, sent = self._run(legrand, monkeypatch, "02")
        assert sent.call_count == 1
        assert sent.call_args[0][3] == "01"      # ep argument of send_legrand_command
        assert sent.call_args[0][4] == "fc01"

    def test_fc01_payload_still_carries_the_group_and_the_leftright_byte(self, legrand, monkeypatch):
        _, sent = self._run(legrand, monkeypatch, "02")
        # 0xfefd little endian, then the leftright byte
        assert sent.call_args[0][6] == "fdfe" + "02"

    def test_single_gang_remote_is_registered_on_endpoint_01(self, legrand, monkeypatch):
        plugin, sent = self._run(legrand, monkeypatch, None, device=SINGLE_GANG)
        plugin.groupmgt.add_group_member_ship_from_remote.assert_called_once_with("ee9f", "01", "fefd")
        assert sent.call_args[0][6] == "fdfe"

    def test_the_two_gangs_are_registered_on_different_endpoints(self, legrand, monkeypatch):
        """
        The defect: both gangs landed on endpoint 01, leaving the two groups with
        identical member entries and no GroupMemberShip key for endpoint 02.
        """
        plugin = _FakeSelf({"ee9f": dict(DOUBLE_GANGS)})
        plugin.groupmgt = MagicMock()
        plugin.groupmgt.get_available_grp_id = MagicMock(side_effect=["fefe", "fefd"])
        monkeypatch.setattr(legrand, "send_legrand_command", MagicMock())
        monkeypatch.setattr(legrand, "get_and_inc_ZCL_SQN", MagicMock(return_value="01"))

        legrand.assign_group_membership_to_legrand_remote(plugin, "ee9f", "01", "01")
        legrand.assign_group_membership_to_legrand_remote(plugin, "ee9f", "01", "02")

        calls = [call.args for call in plugin.groupmgt.add_group_member_ship_from_remote.call_args_list]
        assert calls == [("ee9f", "01", "fefe"), ("ee9f", "02", "fefd")]
