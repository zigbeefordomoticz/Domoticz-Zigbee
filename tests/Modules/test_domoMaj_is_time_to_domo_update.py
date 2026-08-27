#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Modules.domoMaj.is_time_to_domo_update.

Regression coverage for the FakeEp auto-vivification fix: a device whose
certified config maps a datapoint to a virtual/fake Ep (domo_ep override,
e.g. Excellux NTCHT01/02 probe temperature on Ep "f1") never gets that Ep
discovered over the air - pairing explicitly skips fake Eps. Before the fix,
MajDomoDevice rejected every widget update for such an Ep forever with
"not known Endpoint". is_time_to_domo_update must now create the Ep entry
on first use when - and only when - is_fake_ep() says it's a declared fake
Ep, and must keep rejecting genuinely unknown (non-fake) Eps as before.
"""

import sys
import types
import importlib

import pytest
from unittest.mock import MagicMock


def _ensure_stub(name, **attrs):
    """Ensure sys.modules[name] exists and carries the given attributes.

    Existing modules/stubs (e.g. those installed by conftest, or a real
    module already imported by another test file) are augmented rather
    than replaced, so we don't clobber fixtures shared with other tests.
    """
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
    """Import a fresh Modules.domoMaj with its collaborators stubbed out.

    Popped before and after import so the real module (with the real
    is_time_to_domo_update we're testing) is never left cached in
    sys.modules for other test files that expect Modules.domoMaj to be a
    lightweight MagicMock stub (e.g. test_tuya.py).
    """
    stubs = {
        "Modules.basicOutputs": dict(read_attribute=MagicMock(name="read_attribute")),
        "Modules.domoticzAbstractLayer": dict(
            domo_check_unit=MagicMock(name="domo_check_unit"),
            domo_read_Device_Idx=MagicMock(name="domo_read_Device_Idx"),
            domo_read_nValue_sValue=MagicMock(name="domo_read_nValue_sValue"),
            domo_read_Options=MagicMock(name="domo_read_Options"),
            domo_read_SwitchType_SubType_Type=MagicMock(name="domo_read_SwitchType_SubType_Type"),
            domo_update_api=MagicMock(name="domo_update_api"),
            find_widget_unit_from_WidgetID=MagicMock(name="find_widget_unit_from_WidgetID"),
            is_dimmable_blind=MagicMock(name="is_dimmable_blind"),
        ),
        "Modules.domoTools": dict(
            RetreiveSignalLvlBattery=MagicMock(name="RetreiveSignalLvlBattery"),
            retrieve_widget_type_list=MagicMock(name="retrieve_widget_type_list"),
            TypeFromCluster=MagicMock(name="TypeFromCluster"),
            remove_bad_cluster_type_entry=MagicMock(name="remove_bad_cluster_type_entry"),
            update_domoticz_widget=MagicMock(name="update_domoticz_widget"),
        ),
        "Modules.linky": dict(
            linky_tarif_color=MagicMock(name="linky_tarif_color"),
            linky_tarif_color_ntarf=MagicMock(name="linky_tarif_color_ntarf"),
        ),
        "Modules.switchSelectorWidgets": dict(SWITCH_SELECTORS={}),
        "Modules.tools": dict(
            get_device_config_param=MagicMock(name="get_device_config_param", return_value=None),
            get_deviceconf_parameter_value=MagicMock(name="get_deviceconf_parameter_value", return_value=None),
            is_fake_ep=MagicMock(name="is_fake_ep", return_value=False),
            str_round=MagicMock(name="str_round"),
            zigpy_plugin_sanity_check=MagicMock(name="zigpy_plugin_sanity_check", return_value=False),
        ),
        "Modules.zigateConsts": dict(THERMOSTAT_MODE_2_LEVEL={}, ZIGATE_EP="01"),
        "Modules.zlinky": dict(
            ZLINK_CONF_MODEL=(),
            get_instant_power=MagicMock(name="get_instant_power"),
            get_notification_day_color=MagicMock(name="get_notification_day_color"),
            get_tarif_color=MagicMock(name="get_tarif_color"),
            zlinky_sum_all_indexes=MagicMock(name="zlinky_sum_all_indexes"),
        ),
        "Zigbee.zdpCommands": dict(zdp_IEEE_address_request=MagicMock(name="zdp_IEEE_address_request")),
    }
    for name, attrs in stubs.items():
        _ensure_stub(name, **attrs)

    sys.modules.pop("Modules.domoMaj", None)
    mod = importlib.import_module("Modules.domoMaj")
    yield mod
    sys.modules.pop("Modules.domoMaj", None)


NWKID = "10f9"
FAKE_EP = "f1"
REAL_EP = "01"


def _plugin(ep_dict=None, extra_device_attrs=None):
    p = MagicMock()
    p.log = MagicMock()
    p.log.logging = MagicMock()
    p.pairing_in_progress = False
    p.pluginconf = MagicMock()
    p.pluginconf.pluginConf = {}
    device = {"Ep": ep_dict if ep_dict is not None else {}, "IEEE": "aabbccddeeff0011"}
    if extra_device_attrs:
        device.update(extra_device_attrs)
    p.ListOfDevices = {NWKID: device}
    return p


class TestIsTimeToDomoUpdate:
    def test_unknown_device_returns_false(self, domoMaj_module):
        p = _plugin()
        p.ListOfDevices = {}
        assert domoMaj_module.is_time_to_domo_update(p, NWKID, REAL_EP) is False

    def test_disabled_device_returns_false(self, domoMaj_module):
        p = _plugin(extra_device_attrs={"Health": "Disabled"})
        assert domoMaj_module.is_time_to_domo_update(p, NWKID, REAL_EP) is False

    def test_known_ep_is_untouched(self, domoMaj_module, monkeypatch):
        """Regression guard: an already-known Ep must not even consult
        is_fake_ep, and behavior is unchanged by the fix."""
        fake_ep_check = MagicMock(name="is_fake_ep")
        monkeypatch.setattr(domoMaj_module, "is_fake_ep", fake_ep_check)
        p = _plugin(ep_dict={REAL_EP: {}})

        assert domoMaj_module.is_time_to_domo_update(p, NWKID, REAL_EP) is True
        fake_ep_check.assert_not_called()

    def test_unknown_non_fake_ep_is_rejected(self, domoMaj_module, monkeypatch):
        """A genuinely unknown Ep (not declared FakeEp) must still be
        rejected, and must not be created in ListOfDevices."""
        monkeypatch.setattr(domoMaj_module, "is_fake_ep", MagicMock(return_value=False))
        p = _plugin(ep_dict={})

        assert domoMaj_module.is_time_to_domo_update(p, NWKID, FAKE_EP) is False
        assert FAKE_EP not in p.ListOfDevices[NWKID]["Ep"]
        p.log.logging.assert_any_call(
            "Widget", "Error", "MajDomoDevice - %s/%s not known Endpoint" % (NWKID, FAKE_EP), NWKID
        )

    def test_declared_fake_ep_is_auto_vivified(self, domoMaj_module, monkeypatch):
        """The bug fix: a declared FakeEp is created on first use instead
        of being dropped, and the update is allowed to proceed."""
        monkeypatch.setattr(domoMaj_module, "is_fake_ep", MagicMock(return_value=True))
        p = _plugin(ep_dict={})

        assert domoMaj_module.is_time_to_domo_update(p, NWKID, FAKE_EP) is True
        assert p.ListOfDevices[NWKID]["Ep"][FAKE_EP] == {}
        assert not any(
            call.args[:2] == ("Widget", "Error") for call in p.log.logging.call_args_list
        )
