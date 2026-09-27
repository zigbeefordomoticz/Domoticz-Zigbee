#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the P1Meter_HPHC HC/HP attributes of Modules/domoMaj.py (issue #2050): by default HC, Usage1 (T1), is fed by
0x0702/0x0100 and HP, Usage2 (T2), by 0x0702/0x0102. The device Params LINKY_IDX_HC / LINKY_IDX_HP can swap
them, but only when both are defined and valid; otherwise the default mapping is kept.
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
