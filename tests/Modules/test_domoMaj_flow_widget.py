#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the Flow (Domoticz Waterflow, L/min) branch of Modules/domoMaj.py:_domo_maj_one_cluster_type_entry.

The value is either the flow itself (cluster 0404 MeasuredValue) or a dict carrying it under
"flow_l_min" (an EvalFunc record routed to several widgets); a dict without it means there is
nothing new to display and the widget is left untouched.
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


def _update_flow(domoMaj_module, monkeypatch, value):
    update = MagicMock(name="update_domoticz_widget")
    monkeypatch.setattr(domoMaj_module, "update_domoticz_widget", update)
    monkeypatch.setattr(domoMaj_module, "retreive_device_unit", lambda *args: 7)
    monkeypatch.setattr(domoMaj_module, "domo_read_nValue_sValue", lambda *args: (0, "0.0"))
    monkeypatch.setattr(domoMaj_module, "domo_read_SwitchType_SubType_Type", lambda *args: (0, 30, 243))
    monkeypatch.setattr(domoMaj_module, "RetreiveSignalLvlBattery", lambda *args: (12, 255))
    plugin = MagicMock()
    plugin.log.logging = MagicMock()
    domoMaj_module._domo_maj_one_cluster_type_entry(
        plugin, {}, NWKID, EP, IEEE, "SWV-ZFE", "Flow", [(EP, 42, "Flow")], "Flow", value, "", "", EP, 42, "Flow")
    return update


def test_flow_value_updates_the_widget(domoMaj_module, monkeypatch):
    update = _update_flow(domoMaj_module, monkeypatch, 15.3)

    update.assert_called_once()
    assert update.call_args.args[4:6] == (0, "15.3")


def test_flow_dict_value_updates_the_widget(domoMaj_module, monkeypatch):
    update = _update_flow(domoMaj_module, monkeypatch, {"text": "Running", "flow_l_min": 14.4})

    assert update.call_args.args[4:6] == (0, "14.4")


def test_flow_zero_is_displayed(domoMaj_module, monkeypatch):
    update = _update_flow(domoMaj_module, monkeypatch, {"flow_l_min": 0})

    assert update.call_args.args[4:6] == (0, "0")


def test_flow_dict_without_flow_leaves_the_widget_untouched(domoMaj_module, monkeypatch):
    update = _update_flow(domoMaj_module, monkeypatch, {"text": "Running"})

    update.assert_not_called()
