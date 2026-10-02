#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the P1Meter import/export mode of Modules/domoMaj.py (device Param P1METER_IMPORT_EXPORT): Usage1 is fed by
0x0702/0x0000, Return1 by 0x0702/0x0001, a negative instant power is shown as production, and the Linky HC/HP indexes
(0x0702/0x0100, 0x0102) are never used. Without the Param the P1Meter behaviour is unchanged.
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
IMPORT_EXPORT = {"P1METER_IMPORT_EXPORT": True}


@pytest.mark.parametrize("value, expected", [
    (None, False), (True, True), (1, True), ("1", True), (" true ", True), ("yes", True), ("on", True),
    (False, False), (0, False), ("0", False), ("false", False), ("", False),
])
def test_is_p1meter_import_export(domoMaj_module, monkeypatch, value, expected):
    monkeypatch.setattr(domoMaj_module, "get_device_config_param", lambda self, nwkid, name: value if name == "P1METER_IMPORT_EXPORT" else None)

    assert domoMaj_module.is_p1meter_import_export(MagicMock(), NWKID) is expected


def test_zlinky_is_never_import_export(domoMaj_module, monkeypatch):
    monkeypatch.setattr(domoMaj_module, "get_device_config_param", lambda self, nwkid, name: True)
    monkeypatch.setattr(domoMaj_module, "ZLINK_CONF_MODEL", ("ZLinky_TIC-standard-mono",))
    plugin = MagicMock()
    plugin.ListOfDevices = {NWKID: {"Model": "ZLinky_TIC-standard-mono"}}

    assert domoMaj_module.is_p1meter_import_export(plugin, NWKID) is False


@pytest.mark.parametrize("instant_power, expected", [(750, (750, 0)), (0, (0, 0)), (-420, (0, 420)), (-0.5, (0, 0.5))])
def test_split_p1meter_instant_power(domoMaj_module, instant_power, expected):
    assert domoMaj_module.split_p1meter_instant_power(instant_power) == expected


def _patch(domoMaj_module, monkeypatch, params, current, instant_power=500):
    update = MagicMock(name="update_domoticz_widget")
    monkeypatch.setattr(domoMaj_module, "update_domoticz_widget", update)
    monkeypatch.setattr(domoMaj_module, "get_device_config_param", lambda self, nwkid, name: params.get(name))
    monkeypatch.setattr(domoMaj_module, "get_deviceconf_parameter_value", lambda *args, **kwargs: None)
    monkeypatch.setattr(domoMaj_module, "_retreive_instant_power", lambda *args: instant_power)
    monkeypatch.setattr(domoMaj_module, "retrieve_data_from_current", lambda *args: current.split(";"))
    return update


def _summation_update(domoMaj_module, monkeypatch, params, attribute, value, instant_power=500):
    update = _patch(domoMaj_module, monkeypatch, params, "111;0;333;0;0;0", instant_power)
    plugin = MagicMock()
    plugin.ListOfDevices = {NWKID: {"Model": "SDM01W", "Param": params}}
    domoMaj_module.process_p1meters_meter_with_summation(
        plugin, "P1Meter", attribute, value, {}, IEEE, 7, 0, "111;0;333;0;0;0", NWKID, EP, 255, 12)
    update.assert_called_once()
    return update.call_args.args[5]


def test_delivered_summation_feeds_usage1(domoMaj_module, monkeypatch):
    assert _summation_update(domoMaj_module, monkeypatch, IMPORT_EXPORT, "0000", 1000) == "1000;0;333;0;500;0"


def test_received_summation_feeds_return1(domoMaj_module, monkeypatch):
    assert _summation_update(domoMaj_module, monkeypatch, IMPORT_EXPORT, "0001", 2000) == "111;0;2000;0;500;0"


def test_summation_with_negative_instant_power_shows_production(domoMaj_module, monkeypatch):
    assert _summation_update(domoMaj_module, monkeypatch, IMPORT_EXPORT, "0001", 2000, instant_power=-420) == "111;0;2000;0;0;420"


def test_summation_without_param_is_unchanged(domoMaj_module, monkeypatch):
    assert _summation_update(domoMaj_module, monkeypatch, {}, "0000", 1000) == "1000;0;333;0;500;0"


def _instant_update(domoMaj_module, monkeypatch, params, value, current="0;0;0;0;0;0"):
    update = _patch(domoMaj_module, monkeypatch, params, current)
    plugin = MagicMock()
    plugin.ListOfDevices = {NWKID: {"Model": "SDM01W", "Param": params, "Ep": {EP: {"0702": {
        "0000": "1000", "0001": "2000", "0100": "400", "0102": "300"}}}}}
    domoMaj_module.process_p1meters_meter_with_instant_power(
        plugin, "P1Meter", "", value, {}, IEEE, 7, 0, current, NWKID, EP, 255, 12)
    update.assert_called_once()
    return update.call_args.args[5]


def test_instant_power_backfills_from_total_indexes_only(domoMaj_module, monkeypatch):
    # 0x0100 / 0x0102 are per phase energy on such meters, they must not land in Usage2
    assert _instant_update(domoMaj_module, monkeypatch, IMPORT_EXPORT, "750") == "1000;0;2000;0;750.0;0"


def test_negative_instant_power_shows_production(domoMaj_module, monkeypatch):
    assert _instant_update(domoMaj_module, monkeypatch, IMPORT_EXPORT, "-420", current="1000;0;2000;0;0;0") == "1000;0;2000;0;0;420.0"


def test_instant_power_without_param_keeps_linky_backfill(domoMaj_module, monkeypatch):
    assert _instant_update(domoMaj_module, monkeypatch, {}, "750") == "400;300;0;0;750.0;0"


def _widget_update(domoMaj_module, monkeypatch, params, cluster_type, cluster_id, attribute, value, widgets):
    update = _patch(domoMaj_module, monkeypatch, params, "111;0;333;0;0;0")
    monkeypatch.setattr(domoMaj_module, "retreive_device_unit", lambda *args: 7)
    monkeypatch.setattr(domoMaj_module, "domo_read_nValue_sValue", lambda *args: (0, "111;0;333;0;0;0"))
    monkeypatch.setattr(domoMaj_module, "domo_read_SwitchType_SubType_Type", lambda *args: (0, 1, 250))
    monkeypatch.setattr(domoMaj_module, "RetreiveSignalLvlBattery", lambda *args: (12, 255))
    plugin = MagicMock()
    plugin.ListOfDevices = {NWKID: {"Model": "SDM01W", "Param": params}}
    domoMaj_module._domo_maj_one_cluster_type_entry(
        plugin, {}, NWKID, EP, IEEE, "SDM01W", cluster_type, widgets, cluster_id, value, attribute, "", EP, 42, "P1Meter")
    return update


def test_received_summation_reaches_p1meter_only_with_param(domoMaj_module, monkeypatch):
    widgets = [(EP, 42, "P1Meter")]
    update = _widget_update(domoMaj_module, monkeypatch, IMPORT_EXPORT, "Meter", "0702", "0001", 2000, widgets)
    update.assert_called_once()
    assert update.call_args.args[5] == "111;0;2000;0;500;0"

    update = _widget_update(domoMaj_module, monkeypatch, {}, "Meter", "0702", "0001", 2000, widgets)
    update.assert_not_called()


def test_negative_power_with_prodmeter_widget(domoMaj_module, monkeypatch):
    widgets = [(EP, 42, "P1Meter"), (EP, 43, "ProdMeter")]
    # Opt-in: the P1Meter splits the negative power itself
    update = _widget_update(domoMaj_module, monkeypatch, IMPORT_EXPORT, "Power", "0b04", "", -420, widgets)
    assert update.call_args.args[5] == "111;0;333;0;0;420.0"

    # Legacy: the widget is zeroed
    update = _widget_update(domoMaj_module, monkeypatch, {}, "Power", "0b04", "", -420, widgets)
    assert update.call_args.args[5] == "0"


@pytest.mark.parametrize("attribute, expected", [("0100", "1000;0;333;0;500;0"), ("0102", "111;1000;333;0;500;0")])
def test_p1meter_hphc_indexes_ignore_param(domoMaj_module, monkeypatch, attribute, expected):
    # P1Meter_HPHC reaches the summation processing as "P1Meter" with 0x0100 / 0x0102: Linky behaviour must be kept
    assert _summation_update(domoMaj_module, monkeypatch, IMPORT_EXPORT, attribute, 1000) == expected
