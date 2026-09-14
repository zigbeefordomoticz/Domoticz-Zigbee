#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the WaterVolume (Domoticz Custom sensor, liters) branch of
Modules/domoMaj.py:_domo_maj_one_cluster_type_entry, fed e.g. by the Sonoff SWV-ZFE
fc11/0x500f DailyIrrigationVolume attribute.
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


NWKID, EP, IEEE = "86e6", "01", "aabbccddeeff0011"


def _update(domoMaj_module, monkeypatch, cluster_type, widget_type, value):
    update = MagicMock(name="update_domoticz_widget")
    monkeypatch.setattr(domoMaj_module, "update_domoticz_widget", update)
    monkeypatch.setattr(domoMaj_module, "retreive_device_unit", lambda *args: 7)
    monkeypatch.setattr(domoMaj_module, "domo_read_nValue_sValue", lambda *args: (0, "0"))
    monkeypatch.setattr(domoMaj_module, "domo_read_SwitchType_SubType_Type", lambda *args: (0, 31, 243))
    monkeypatch.setattr(domoMaj_module, "RetreiveSignalLvlBattery", lambda *args: (12, 255))
    plugin = MagicMock()
    plugin.log.logging = MagicMock()
    domoMaj_module._domo_maj_one_cluster_type_entry(
        plugin, {}, NWKID, EP, IEEE, "SWV-ZFE", cluster_type, [(EP, 42, widget_type)], cluster_type, value, "", "", EP, 42, widget_type)
    return update


def test_water_volume_updates_the_custom_sensor(domoMaj_module, monkeypatch):
    update = _update(domoMaj_module, monkeypatch, "WaterVolume", "WaterVolume", 21)

    update.assert_called_once()
    assert update.call_args.args[4:6] == (0, "21")


def test_water_volume_dict_value_updates_the_custom_sensor(domoMaj_module, monkeypatch):
    update = _update(domoMaj_module, monkeypatch, "WaterVolume", "WaterVolume", {"text": "Running", "water_volume_l": 33.5})

    assert update.call_args.args[4:6] == (0, "33.5")


def test_water_volume_dict_without_volume_leaves_the_widget_untouched(domoMaj_module, monkeypatch):
    update = _update(domoMaj_module, monkeypatch, "WaterVolume", "WaterVolume", {"text": "Running"})

    update.assert_not_called()


def test_water_volume_ignores_other_widgets(domoMaj_module, monkeypatch):
    update = _update(domoMaj_module, monkeypatch, "WaterVolume", "Flow", 21)

    update.assert_not_called()


def test_widget_is_declared_as_a_custom_sensor_in_liters():
    src = open("Modules/domoCreate.py").read()
    assert '"WaterVolume": { "widgetType": "Custom", "Options": "1;L" }' in src
    assert '"WaterVolume": "WaterVolume"' in open("Modules/domoTools.py").read()
