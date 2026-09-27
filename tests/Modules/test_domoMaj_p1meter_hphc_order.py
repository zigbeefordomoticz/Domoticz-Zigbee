#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the P1Meter_HPHC HC/HP attributes of Modules/domoMaj.py (issue #2050): by default HC, Usage1 (T1), is fed by
0x0702/0x0100 and HP, Usage2 (T2), by 0x0702/0x0102. The device Params LINKY_IDX_HC / LINKY_IDX_HP declare which
attribute counts HC and HP on the meter, only when both are defined and valid; otherwise the default mapping is kept.
LINKY_HPHC_ORDER = HP_HC shows HP in Usage1 (T1) and HC in Usage2 (T2), whatever attributes carry them.
"""

import sys
import types
import importlib
from unittest.mock import MagicMock

import pytest


def _ensure_stub(name, **attrs):
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    for k, v in attrs.items():
        if not hasattr(mod, k):
            setattr(mod, k, v)
    return mod


@pytest.fixture
def domoMaj_module():
    stubs = {
        "Modules.basicOutputs": dict(read_attribute=MagicMock()),
        "Modules.domoticzAbstractLayer": dict(
            domo_check_unit=MagicMock(), domo_read_Device_Idx=MagicMock(), domo_read_nValue_sValue=MagicMock(),
            domo_read_Options=MagicMock(), domo_read_SwitchType_SubType_Type=MagicMock(), domo_update_api=MagicMock(),
            find_widget_unit_from_WidgetID=MagicMock(), is_dimmable_blind=MagicMock(),
        ),
        "Modules.domoTools": dict(
            RetreiveSignalLvlBattery=MagicMock(), retrieve_widget_type_list=MagicMock(), TypeFromCluster=MagicMock(),
            remove_bad_cluster_type_entry=MagicMock(), update_domoticz_widget=MagicMock(),
        ),
        "Modules.linky": dict(linky_tarif_color=MagicMock(), linky_tarif_color_ntarf=MagicMock()),
        "Modules.switchSelectorWidgets": dict(SWITCH_SELECTORS={}),
        "Modules.tools": dict(
            get_device_config_param=MagicMock(return_value=None), get_deviceconf_parameter_value=MagicMock(return_value=None),
            is_fake_ep=MagicMock(return_value=False), str_round=MagicMock(), zigpy_plugin_sanity_check=MagicMock(return_value=False),
        ),
        "Modules.zigateConsts": dict(THERMOSTAT_MODE_2_LEVEL={}, ZIGATE_EP="01"),
        "Modules.zlinky": dict(
            ZLINK_CONF_MODEL=(), get_instant_power=MagicMock(), get_notification_day_color=MagicMock(),
            get_tarif_color=MagicMock(), zlinky_sum_all_indexes=MagicMock(),
        ),
        "Zigbee.zdpCommands": dict(zdp_IEEE_address_request=MagicMock()),
    }
    for name, attrs in stubs.items():
        _ensure_stub(name, **attrs)

    sys.modules.pop("Modules.domoMaj", None)
    mod = importlib.import_module("Modules.domoMaj")
    yield mod
    sys.modules.pop("Modules.domoMaj", None)


NWKID, EP, IEEE = "1a2b", "01", "aabbccddeeff0011"
DEFAULT = ("0100", "0102")
SWAPPED = ("0102", "0100")


@pytest.mark.parametrize("idx_hc, idx_hp, expected, has_error", [
    (None, None, DEFAULT, False),
    ("0100", "0102", DEFAULT, False),
    ("0102", "0100", SWAPPED, False),
    ("0x0102", "0x0100", SWAPPED, False),
    (" 0102 ", "0100", SWAPPED, False),
    (102, 100, SWAPPED, False),
    ("0102", None, DEFAULT, True),
    (None, "0100", DEFAULT, True),
    ("0102", "0102", DEFAULT, True),
    ("0100", "0104", DEFAULT, True),
    ("", "", DEFAULT, True),
])
def test_resolve_p1meter_hphc_indexes(domoMaj_module, idx_hc, idx_hp, expected, has_error):
    indexes, error = domoMaj_module.resolve_p1meter_hphc_indexes(idx_hc, idx_hp)

    assert indexes == expected
    assert (error is not None) == has_error


def _summation_update(domoMaj_module, monkeypatch, params, attribute, value):
    update = MagicMock(name="update_domoticz_widget")
    monkeypatch.setattr(domoMaj_module, "update_domoticz_widget", update)
    monkeypatch.setattr(domoMaj_module, "get_device_config_param", lambda self, nwkid, name: params.get(name))
    monkeypatch.setattr(domoMaj_module, "get_deviceconf_parameter_value", lambda *args, **kwargs: None)
    monkeypatch.setattr(domoMaj_module, "_retreive_instant_power", lambda *args: 500)
    monkeypatch.setattr(domoMaj_module, "retrieve_data_from_current", lambda *args: ["111", "222", "0", "0", "0", "0"])
    plugin = MagicMock()
    plugin.ListOfDevices = {NWKID: {"Model": "TICMeter", "Param": params}}
    domoMaj_module.process_p1meters_meter_with_summation(
        plugin, "P1Meter", attribute, value, {}, IEEE, 7, 0, "111;222;0;0;0;0", NWKID, EP, 255, 12)
    update.assert_called_once()
    return update.call_args.args[5]


@pytest.mark.parametrize("params", [{}, {"LINKY_IDX_HC": "0102"}, {"LINKY_IDX_HC": "0102", "LINKY_IDX_HP": "0104"}])
def test_default_order_when_params_missing_or_invalid(domoMaj_module, monkeypatch, params):
    assert _summation_update(domoMaj_module, monkeypatch, params, "0100", 1000) == "1000;222;0;0;500;0"
    assert _summation_update(domoMaj_module, monkeypatch, params, "0102", 2000) == "111;2000;0;0;500;0"


def test_swapped_order_with_both_params(domoMaj_module, monkeypatch):
    params = {"LINKY_IDX_HC": "0102", "LINKY_IDX_HP": "0100"}

    assert _summation_update(domoMaj_module, monkeypatch, params, "0102", 2000) == "2000;222;0;0;500;0"
    assert _summation_update(domoMaj_module, monkeypatch, params, "0100", 1000) == "111;1000;0;0;500;0"


def test_total_index_still_feeds_usage1_of_p1meter(domoMaj_module, monkeypatch):
    params = {"LINKY_IDX_HC": "0102", "LINKY_IDX_HP": "0100"}

    assert _summation_update(domoMaj_module, monkeypatch, params, "0000", 3000) == "3000;222;0;0;500;0"


def test_instant_power_backfills_usages_in_the_configured_order(domoMaj_module, monkeypatch):
    update = MagicMock(name="update_domoticz_widget")
    monkeypatch.setattr(domoMaj_module, "update_domoticz_widget", update)
    params = {"LINKY_IDX_HC": "0102", "LINKY_IDX_HP": "0100"}
    monkeypatch.setattr(domoMaj_module, "get_device_config_param", lambda self, nwkid, name: params.get(name))
    monkeypatch.setattr(domoMaj_module, "retrieve_data_from_current", lambda *args: ["0", "0", "0", "0", "0", "0"])
    plugin = MagicMock()
    plugin.ListOfDevices = {NWKID: {"Model": "TICMeter", "Param": params, "Ep": {EP: {"0702": {"0100": "1000", "0102": "2000"}}}}}

    domoMaj_module.process_p1meters_meter_with_instant_power(
        plugin, "P1Meter_HPHC", "050f", "750", {}, IEEE, 7, 0, "0;0;0;0;0;0", NWKID, EP, 255, 12)

    assert update.call_args.args[5] == "2000;1000;0;0;750.0;0"


SWAP_PARAMS = {"LINKY_IDX_HC": "0102", "LINKY_IDX_HP": "0100"}


@pytest.mark.parametrize("params, ep, expected", [
    ({}, "01", ("0100", "0102")),
    ({}, "f2", ("0104", "0106")),
    ({}, "f3", ("0108", "010a")),
    (SWAP_PARAMS, "01", ("0102", "0100")),
    (SWAP_PARAMS, "f2", ("0106", "0104")),
    (SWAP_PARAMS, "f3", ("010a", "0108")),
    ({"LINKY_IDX_HC": "0102"}, "f2", ("0104", "0106")),
    (SWAP_PARAMS, "f4", None),
])
def test_zlinky_p1meter_indexes(domoMaj_module, monkeypatch, params, ep, expected):
    monkeypatch.setattr(domoMaj_module, "get_device_config_param", lambda self, nwkid, name: params.get(name))

    assert domoMaj_module.get_zlinky_p1meter_indexes(MagicMock(), NWKID, ep) == expected


def _zlinky_update(domoMaj_module, monkeypatch, params, ep, attribute, value):
    update = MagicMock(name="update_domoticz_widget")
    monkeypatch.setattr(domoMaj_module, "update_domoticz_widget", update)
    monkeypatch.setattr(domoMaj_module, "get_device_config_param", lambda self, nwkid, name: params.get(name))
    monkeypatch.setattr(domoMaj_module, "ZLINK_CONF_MODEL", ("ZLinky_TIC-standard-mono",))
    monkeypatch.setattr(domoMaj_module, "get_tarif_color", lambda *args: "Blue")
    monkeypatch.setattr(domoMaj_module, "get_instant_power", lambda *args: 500)
    monkeypatch.setattr(domoMaj_module, "retreive_device_unit", lambda *args: 7)
    monkeypatch.setattr(domoMaj_module, "domo_read_nValue_sValue", lambda *args: (0, "111;222;0;0;0;0"))
    monkeypatch.setattr(domoMaj_module, "retrieve_data_from_current", lambda *args: [111, 222, 0, 0, 0, 0])
    monkeypatch.setattr(domoMaj_module, "domo_read_SwitchType_SubType_Type", lambda *args: (0, 1, 250))
    monkeypatch.setattr(domoMaj_module, "RetreiveSignalLvlBattery", lambda *args: (12, 255))
    plugin = MagicMock()
    plugin.ListOfDevices = {NWKID: {"Model": "ZLinky_TIC-standard-mono", "Param": params}}
    domoMaj_module._domo_maj_one_cluster_type_entry(
        plugin, {}, NWKID, ep, IEEE, "ZLinky_TIC-standard-mono", "Power", [(ep, 42, "P1Meter_ZL")], "0702", value, attribute, "", ep, 42, "P1Meter_ZL")
    return update


@pytest.mark.parametrize("params, ep, attribute, expected", [
    ({}, "01", "0100", "1000;222;0;0;500;0"),
    ({}, "01", "0102", "111;1000;0;0;500;0"),
    (SWAP_PARAMS, "01", "0102", "1000;222;0;0;500;0"),
    (SWAP_PARAMS, "01", "0100", "111;1000;0;0;500;0"),
    ({}, "f2", "0104", "1000;222;0;0;0.0;0"),
    (SWAP_PARAMS, "f2", "0106", "1000;222;0;0;0.0;0"),
    (SWAP_PARAMS, "f3", "0108", "111;1000;0;0;0.0;0"),
])
def test_zlinky_p1meter_zl_usage_slot(domoMaj_module, monkeypatch, params, ep, attribute, expected):
    update = _zlinky_update(domoMaj_module, monkeypatch, params, ep, attribute, 1000)

    update.assert_called_once()
    assert update.call_args.args[5] == expected


@pytest.mark.parametrize("ep, attribute", [("01", "0104"), ("f2", "0100"), ("f3", "0106"), ("f4", "0100")])
def test_zlinky_p1meter_zl_ignores_index_of_another_ep(domoMaj_module, monkeypatch, ep, attribute):
    update = _zlinky_update(domoMaj_module, monkeypatch, SWAP_PARAMS, ep, attribute, 1000)

    update.assert_not_called()


@pytest.mark.parametrize("params, current_tarif, attribute, triggers", [
    ({}, "HC..", "0100", False),
    ({}, "HC..", "0102", True),
    ({}, "HP..", "0100", True),
    (SWAP_PARAMS, "HC..", "0102", False),
    (SWAP_PARAMS, "HC..", "0100", True),
    (SWAP_PARAMS, "HP..", "0102", True),
    (SWAP_PARAMS, "HP..", "0100", False),
])
def test_chameleon_color_transition_follows_hc_hp_params(domoMaj_module, monkeypatch, params, current_tarif, attribute, triggers):
    read = MagicMock(name="read_attribute")
    monkeypatch.setattr(domoMaj_module, "read_attribute", read)
    monkeypatch.setattr(domoMaj_module, "get_device_config_param", lambda self, nwkid, name: params.get(name))
    plugin = MagicMock()
    plugin.ListOfDevices = {NWKID: {"Model": "ERL Z3", "Param": params, "Chameleon": {"NGTF/OPTARIF": "HC", "PTEC/LTARF": current_tarif}}}

    domoMaj_module.check_and_update_chameleon_erz3_linky_color_if_needed(plugin, NWKID, attribute)

    assert read.called == triggers


ORDER_PARAMS = {"LINKY_HPHC_ORDER": "HP_HC"}
BOTH_PARAMS = {**SWAP_PARAMS, **ORDER_PARAMS}


@pytest.mark.parametrize("param_order, expected, has_error", [
    (None, "HC_HP", False),
    ("HC_HP", "HC_HP", False),
    ("HP_HC", "HP_HC", False),
    (" hp_hc ", "HP_HC", False),
    ("HPHC", "HC_HP", True),
    ("", "HC_HP", True),
])
def test_resolve_p1meter_hphc_order(domoMaj_module, param_order, expected, has_error):
    order, error = domoMaj_module.resolve_p1meter_hphc_order(param_order)

    assert order == expected
    assert (error is not None) == has_error


@pytest.mark.parametrize("params, expected", [
    ({}, DEFAULT),
    (SWAP_PARAMS, SWAPPED),
    (ORDER_PARAMS, SWAPPED),
    (BOTH_PARAMS, DEFAULT),
    ({"LINKY_HPHC_ORDER": "bogus"}, DEFAULT),
])
def test_p1meter_usage_indexes_combine_hc_hp_and_order(domoMaj_module, monkeypatch, params, expected):
    monkeypatch.setattr(domoMaj_module, "get_device_config_param", lambda self, nwkid, name: params.get(name))

    assert domoMaj_module.get_p1meter_usage_indexes(MagicMock(), NWKID) == expected


def test_hp_first_order_with_default_meter_mapping(domoMaj_module, monkeypatch):
    # Meter counts HC on 0100 and HP on 0102, Domoticz T1 price is the HP one
    assert _summation_update(domoMaj_module, monkeypatch, ORDER_PARAMS, "0102", 2000) == "2000;222;0;0;500;0"
    assert _summation_update(domoMaj_module, monkeypatch, ORDER_PARAMS, "0100", 1000) == "111;1000;0;0;500;0"


def test_hp_first_order_with_swapped_meter_mapping(domoMaj_module, monkeypatch):
    # Meter counts HC on 0102 and HP on 0100, Domoticz T1 price is the HP one
    assert _summation_update(domoMaj_module, monkeypatch, BOTH_PARAMS, "0100", 1000) == "1000;222;0;0;500;0"
    assert _summation_update(domoMaj_module, monkeypatch, BOTH_PARAMS, "0102", 2000) == "111;2000;0;0;500;0"


@pytest.mark.parametrize("params, ep, expected", [
    (ORDER_PARAMS, "01", ("0102", "0100")),
    (ORDER_PARAMS, "f2", ("0106", "0104")),
    (ORDER_PARAMS, "f3", ("010a", "0108")),
    (BOTH_PARAMS, "f2", ("0104", "0106")),
])
def test_zlinky_p1meter_indexes_follow_order(domoMaj_module, monkeypatch, params, ep, expected):
    monkeypatch.setattr(domoMaj_module, "get_device_config_param", lambda self, nwkid, name: params.get(name))

    assert domoMaj_module.get_zlinky_p1meter_indexes(MagicMock(), NWKID, ep) == expected


@pytest.mark.parametrize("current_tarif, attribute, triggers", [
    ("HC..", "0100", False),
    ("HC..", "0102", True),
    ("HP..", "0102", False),
    ("HP..", "0100", True),
])
def test_chameleon_color_transition_ignores_display_order(domoMaj_module, monkeypatch, current_tarif, attribute, triggers):
    read = MagicMock(name="read_attribute")
    monkeypatch.setattr(domoMaj_module, "read_attribute", read)
    monkeypatch.setattr(domoMaj_module, "get_device_config_param", lambda self, nwkid, name: ORDER_PARAMS.get(name))
    plugin = MagicMock()
    plugin.ListOfDevices = {NWKID: {"Model": "ERL Z3", "Param": ORDER_PARAMS, "Chameleon": {"NGTF/OPTARIF": "HC", "PTEC/LTARF": current_tarif}}}

    domoMaj_module.check_and_update_chameleon_erz3_linky_color_if_needed(plugin, NWKID, attribute)

    assert read.called == triggers
