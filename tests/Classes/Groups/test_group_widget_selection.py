"""
tests/Classes/GroupMgtv2/test_group_widget_selection.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for group widget selection logic in Classes/GroupMgtv2/GrpDomoticz.py.

Covers:
  - my_best_widget_offer         : pairwise capability negotiation
  - negotiate_endpoint_widget    : per-device-endpoint logic (blind detection, covering, colour)
  - best_group_widget            : full group scan, specifically the 1xWW + 2xRGBWW scenario

The module is imported in isolation against minimal stubs so no Domoticz
framework or radio backend is required.

Run with:
    pytest tests/Classes/GroupMgtv2/test_group_widget_selection.py -v
"""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Stubs — only what GrpDomoticz.py actually imports
# ---------------------------------------------------------------------------

def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


_GRP_DOMO_DEPS = {
    "Classes.GroupMgtv2.GrpCommands": dict(
        set_hue_saturation=MagicMock(),
        set_kelvin_color=MagicMock(),
        set_rgb_color=MagicMock(),
    ),
    "Classes.GroupMgtv2.GrpDatabase": dict(
        update_due_to_nwk_id_change=MagicMock(),
    ),
    "Modules.domoticzAbstractLayer": dict(
        domo_create_api=MagicMock(return_value=1),
        domo_delete_widget=MagicMock(),
        domo_read_Name=MagicMock(return_value="Group"),
        domo_read_nValue_sValue=MagicMock(return_value=(0, "Off")),
        domo_read_SwitchType_SubType_Type=MagicMock(return_value=(0, 0, 244)),
        domo_update_api=MagicMock(),
        domo_update_name=MagicMock(),
        domo_update_SwitchType_SubType_Type=MagicMock(),
        find_first_unit_widget_from_deviceID=MagicMock(return_value=1),
        is_domoticz_latest_typename=MagicMock(return_value=False),
    ),
    "Modules.tools": dict(
        Hex_Format=MagicMock(return_value="00"),
        get_deviceconf_parameter_value=MagicMock(return_value=None),
        is_domoticz_latest_typename=MagicMock(return_value=False),
        is_hex=MagicMock(return_value=True),
    ),
    "Modules.zigateConsts": dict(
        ADDRESS_MODE={"short": 2, "ieee": 3, "group": 4},
        LEGRAND_REMOTES=[],
        ZIGATE_EP="01",
    ),
    "Zigbee.zclCommands": dict(
        zcl_group_level_move_to_level=MagicMock(),
        zcl_group_move_to_level_stop=MagicMock(),
        zcl_group_move_to_level_with_onoff=MagicMock(),
        zcl_group_onoff_off_noeffect=MagicMock(),
        zcl_group_onoff_off_witheffect=MagicMock(),
        zcl_group_onoff_on=MagicMock(),
        zcl_group_window_covering_level=MagicMock(),
        zcl_group_window_covering_off=MagicMock(),
        zcl_group_window_covering_on=MagicMock(),
        zcl_group_window_covering_stop=MagicMock(),
    ),
}


@pytest.fixture(scope="module")
def grp_domo():
    """
    Load GrpDomoticz directly from its file path so the fixture is immune
    to whatever package state is already in sys.modules at collection time.
    Stubs are injected before loading and cleaned up on teardown.
    """
    import importlib.util
    import pathlib

    module_path = pathlib.Path(__file__).parents[3] / "Classes" / "GroupMgtv2" / "GrpDomoticz.py"

    saved = {name: sys.modules.pop(name, None) for name in _GRP_DOMO_DEPS}
    for name, attrs in _GRP_DOMO_DEPS.items():
        sys.modules[name] = _make_stub(name, **attrs)

    spec = importlib.util.spec_from_file_location("Classes.GroupMgtv2.GrpDomoticz", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    yield module

    for name in _GRP_DOMO_DEPS:
        sys.modules.pop(name, None)
        if saved.get(name) is not None:
            sys.modules[name] = saved[name]


# ---------------------------------------------------------------------------
# Minimal self-like object for functions that take `self`
# ---------------------------------------------------------------------------

class _FakeSelf:
    def __init__(self, list_of_devices=None, list_of_groups=None):
        self.ListOfDevices = list_of_devices or {}
        self.ListOfGroups  = list_of_groups  or {}

    def logging(self, level, msg, *args, **kwargs):
        pass  # silence debug output during tests


# ---------------------------------------------------------------------------
# Tests: my_best_widget_offer
# ---------------------------------------------------------------------------

class TestMyBestWidgetOffer:
    """
    Verify that my_best_widget_offer always returns the LESS capable
    (lower-rank) of the two widgets, implementing the 'minimum common
    capability' policy for groups.

    The function signature on rc-stable8-domoticzex is:
        my_best_widget_offer(current_widget, current_group_widget)
    — no self parameter.
    """

    def test_none_candidate_returns_current_widget(self, grp_domo):
        assert grp_domo.my_best_widget_offer("ColorControlWW", None) == "ColorControlWW"

    def test_same_widget_returns_it(self, grp_domo):
        assert grp_domo.my_best_widget_offer("ColorControlRGBWW", "ColorControlRGBWW") == "ColorControlRGBWW"

    # --- colour hierarchy ---

    def test_ww_vs_rgbww_returns_ww(self, grp_domo):
        """RGBWW (rank 5) is more capable than WW (rank 3) → keep WW."""
        assert grp_domo.my_best_widget_offer("ColorControlRGBWW", "ColorControlWW") == "ColorControlWW"

    def test_rgbww_vs_ww_returns_ww(self, grp_domo):
        """Symmetric: WW candidate, RGBWW incoming → WW wins."""
        assert grp_domo.my_best_widget_offer("ColorControlWW", "ColorControlRGBWW") == "ColorControlWW"

    def test_colorfull_vs_ww_returns_ww(self, grp_domo):
        """ColorControlFull (rank 6) vs WW (rank 3) → WW wins."""
        assert grp_domo.my_best_widget_offer("ColorControlFull", "ColorControlWW") == "ColorControlWW"

    def test_ww_vs_colorfull_returns_ww(self, grp_domo):
        assert grp_domo.my_best_widget_offer("ColorControlWW", "ColorControlFull") == "ColorControlWW"

    def test_colorcontrol_vs_ww_returns_ww(self, grp_domo):
        """Key case: ColorControl (rank 6) vs WW (rank 3) must return WW."""
        assert grp_domo.my_best_widget_offer("ColorControl", "ColorControlWW") == "ColorControlWW"

    def test_ww_vs_colorcontrol_returns_ww(self, grp_domo):
        assert grp_domo.my_best_widget_offer("ColorControlWW", "ColorControl") == "ColorControlWW"

    def test_rgb_vs_rgbww_returns_rgb(self, grp_domo):
        assert grp_domo.my_best_widget_offer("ColorControlRGBWW", "ColorControlRGB") == "ColorControlRGB"

    def test_lvlcontrol_vs_colorcontrolww_returns_lvlcontrol(self, grp_domo):
        assert grp_domo.my_best_widget_offer("ColorControlWW", "LvlControl") == "LvlControl"

    def test_switch_beats_everything(self, grp_domo):
        for widget in ("LvlControl", "ColorControlWW", "ColorControlRGB",
                       "ColorControlRGBWW", "ColorControl", "ColorControlFull"):
            assert grp_domo.my_best_widget_offer(widget, "Switch") == "Switch", widget

    def test_unknown_widget_keeps_candidate(self, grp_domo):
        """An unknown widget type must not corrupt the existing candidate."""
        assert grp_domo.my_best_widget_offer("WeirdWidget", "ColorControlWW") == "ColorControlWW"


# ---------------------------------------------------------------------------
# Tests: negotiate_endpoint_widget
# ---------------------------------------------------------------------------

class TestNegotiateEndpointWidget:
    """Verify per-endpoint capability negotiation and blind/covering detection."""

    def _ep(self, cluster_type, type_field=None):
        ep = {"ClusterType": cluster_type}
        if type_field is not None:
            ep["Type"] = type_field
        return ep

    def test_single_ww_device_sets_candidate(self, grp_domo):
        self_ = _FakeSelf()
        style, candidate = grp_domo.negotiate_endpoint_widget(
            self_, "1234",
            device_info={},
            device_ep_info=self._ep({"1": "ColorControlWW"}),
            GroupWidgetStyle=None,
            group_widget_type_candidate=None,
        )
        assert candidate == "ColorControlWW"
        assert style is None

    def test_rgbww_device_on_ww_candidate_stays_ww(self, grp_domo):
        """An RGBWW device must not upgrade a WW-only group candidate."""
        self_ = _FakeSelf()
        style, candidate = grp_domo.negotiate_endpoint_widget(
            self_, "5678",
            device_info={},
            device_ep_info=self._ep({"1": "ColorControlRGBWW"}),
            GroupWidgetStyle=None,
            group_widget_type_candidate="ColorControlWW",
        )
        assert candidate == "ColorControlWW"

    def test_blind_type_returns_blind_percent(self, grp_domo):
        self_ = _FakeSelf()
        style, candidate = grp_domo.negotiate_endpoint_widget(
            self_, "ABCD",
            device_info={},
            device_ep_info=self._ep({"1": "LvlControl"}, type_field="Blind"),
            GroupWidgetStyle=None,
            group_widget_type_candidate=None,
        )
        assert style == "BlindPercent"
        assert candidate == "LvlControl"

    def test_blind_inverted_type_returns_blind_percent_inverted(self, grp_domo):
        self_ = _FakeSelf()
        style, candidate = grp_domo.negotiate_endpoint_widget(
            self_, "ABCD",
            device_info={},
            device_ep_info=self._ep({"1": "LvlControl"}, type_field="BlindInverted"),
            GroupWidgetStyle=None,
            group_widget_type_candidate=None,
        )
        assert style == "BlindPercentInverted"
        assert candidate == "LvlControl"

    def test_venetian_widget_returns_venetian_inverted(self, grp_domo):
        self_ = _FakeSelf()
        style, candidate = grp_domo.negotiate_endpoint_widget(
            self_, "CCCC",
            device_info={},
            device_ep_info=self._ep({"1": "VenetianInverted"}),
            GroupWidgetStyle=None,
            group_widget_type_candidate=None,
        )
        assert style == "VenetianInverted"
        assert candidate == "LvlControl"

    def test_none_cluster_type_is_skipped(self, grp_domo):
        self_ = _FakeSelf()
        style, candidate = grp_domo.negotiate_endpoint_widget(
            self_, "1111",
            device_info={},
            device_ep_info=self._ep({"1": None, "2": "ColorControlWW"}),
            GroupWidgetStyle=None,
            group_widget_type_candidate=None,
        )
        assert candidate == "ColorControlWW"

    def test_lvlcontrol_with_no_type_field_does_not_raise(self, grp_domo):
        """device_type missing on both ep and device_info must not raise TypeError."""
        self_ = _FakeSelf()
        style, candidate = grp_domo.negotiate_endpoint_widget(
            self_, "2222",
            device_info={},
            device_ep_info=self._ep({"1": "LvlControl"}),
            GroupWidgetStyle=None,
            group_widget_type_candidate=None,
        )
        # No blind markers → stays as LvlControl candidate
        assert candidate == "LvlControl"


# ---------------------------------------------------------------------------
# Tests: best_group_widget — the 1xWW + 2xRGBWW scenario and others
# ---------------------------------------------------------------------------

def _make_device(widget_type, ep="01"):
    return {
        "Ep": {
            ep: {
                "ClusterType": {"1": widget_type},
            }
        }
    }


def _make_group(devices):
    """devices: list of (NwkId, ep, IEEE) tuples."""
    return {"Devices": devices, "Tradfri Remote": {}}


class TestBestGroupWidget:

    def _run(self, grp_domo, devices_spec):
        """
        devices_spec: list of (NwkId, ep, IEEE, widget_type).
        Returns (Type_, Subtype_, SwitchType_).
        """
        list_of_devices = {}
        group_devices   = []
        for nwk, ep, ieee, wt in devices_spec:
            list_of_devices[nwk] = _make_device(wt, ep)
            group_devices.append((nwk, ep, ieee))

        self_ = _FakeSelf(
            list_of_devices=list_of_devices,
            list_of_groups={"0001": _make_group(group_devices)},
        )
        return grp_domo.best_group_widget(self_, "0001"), self_.ListOfGroups["0001"]

    # --- the key scenario reported by the user ---

    def test_1ww_2rgbww_yields_ww_widget(self, grp_domo):
        """1×WW + 2×RGBWW: minimum common capability is WW."""
        result, group = self._run(grp_domo, [
            ("1111", "01", "aa:bb:cc:dd:00:01:00:01", "ColorControlWW"),
            ("2222", "01", "aa:bb:cc:dd:00:02:00:01", "ColorControlRGBWW"),
            ("3333", "01", "aa:bb:cc:dd:00:03:00:01", "ColorControlRGBWW"),
        ])
        assert group["GroupWidgetType"] == "ColorControlWW"
        assert group["GroupWidgetStyle"] == "ColorControlWW"
        assert result == grp_domo.WIDGET_STYLE["ColorControlWW"]

    def test_1ww_2rgbww_order_independent(self, grp_domo):
        """Result must be the same regardless of iteration order."""
        result_a, group_a = self._run(grp_domo, [
            ("1111", "01", "ieee1", "ColorControlWW"),
            ("2222", "01", "ieee2", "ColorControlRGBWW"),
            ("3333", "01", "ieee3", "ColorControlRGBWW"),
        ])
        result_b, group_b = self._run(grp_domo, [
            ("2222", "01", "ieee2", "ColorControlRGBWW"),
            ("3333", "01", "ieee3", "ColorControlRGBWW"),
            ("1111", "01", "ieee1", "ColorControlWW"),
        ])
        assert group_a["GroupWidgetType"] == group_b["GroupWidgetType"]
        assert result_a == result_b

    def test_1colorfull_1ww_yields_ww(self, grp_domo):
        """ColorControlFull + WW → WW (the bug case from the review)."""
        _, group = self._run(grp_domo, [
            ("1111", "01", "ieee1", "ColorControlFull"),
            ("2222", "01", "ieee2", "ColorControlWW"),
        ])
        assert group["GroupWidgetType"] == "ColorControlWW"

    def test_1colorcontrol_1ww_yields_ww(self, grp_domo):
        """ColorControl + WW → WW (the exact bug case)."""
        _, group = self._run(grp_domo, [
            ("1111", "01", "ieee1", "ColorControl"),
            ("2222", "01", "ieee2", "ColorControlWW"),
        ])
        assert group["GroupWidgetType"] == "ColorControlWW"

    def test_all_rgbww_yields_rgbww(self, grp_domo):
        """Homogeneous RGBWW group stays RGBWW."""
        _, group = self._run(grp_domo, [
            ("1111", "01", "ieee1", "ColorControlRGBWW"),
            ("2222", "01", "ieee2", "ColorControlRGBWW"),
        ])
        assert group["GroupWidgetType"] == "ColorControlRGBWW"

    def test_switch_and_color_yields_switch(self, grp_domo):
        """Switch + any colour device → Switch (most restrictive)."""
        _, group = self._run(grp_domo, [
            ("1111", "01", "ieee1", "Switch"),
            ("2222", "01", "ieee2", "ColorControlRGBWW"),
        ])
        assert group["GroupWidgetType"] == "Switch"

    def test_coordinator_skipped(self, grp_domo):
        """NwkId 0000 (coordinator) must be skipped."""
        list_of_devices = {"1111": _make_device("ColorControlWW")}
        self_ = _FakeSelf(
            list_of_devices=list_of_devices,
            list_of_groups={"0001": _make_group([
                ("0000", "01", "00:00:00:00:00:00:00:00"),
                ("1111", "01", "ieee1"),
            ])},
        )
        grp_domo.best_group_widget(self_, "0001")
        assert self_.ListOfGroups["0001"]["GroupWidgetType"] == "ColorControlWW"

    def test_empty_group_defaults_to_colorfull(self, grp_domo):
        """A group with no contributable devices falls back to ColorControlFull."""
        self_ = _FakeSelf(
            list_of_devices={},
            list_of_groups={"0001": _make_group([])},
        )
        grp_domo.best_group_widget(self_, "0001")
        assert self_.ListOfGroups["0001"]["GroupWidgetType"] == "ColorControlFull"

    def test_cluster_set_correctly(self, grp_domo):
        """Cluster must be set from CLUSTER_MAPPING for the resolved widget type."""
        _, group = self._run(grp_domo, [
            ("1111", "01", "ieee1", "ColorControlWW"),
        ])
        assert group["Cluster"] == grp_domo.CLUSTER_MAPPING["ColorControlWW"]

