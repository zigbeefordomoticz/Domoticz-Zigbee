#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the Profalux model handling in Modules.profalux.

Regression coverage for z4d-certified-devices issue #175: the MAI-ZTM22C remote
reports its own model in Basic and has a temperature sensor on endpoint 03.
profalux_fake_deviceModel() used to rename every battery-powered Profalux device
to "Telecommande-Profalux" at pairing, so the device was provisioned with that
configuration (a useless LvlControl widget, Param Disabled) and its own
configuration was never used.
"""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest

NWKID = "9be0"
PROFALUX_FAKE_MODELS = ("VoletBSO-Profalux", "BSO-Profalux", "Volet-Profalux", "Telecommande-Profalux")


def _ensure_stub(name, **attrs):
    """Ensure sys.modules[name] exists and carries the given attributes.

    Existing modules/stubs (e.g. those installed by conftest) are augmented
    rather than replaced, so we don't clobber fixtures shared with other tests.
    """
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    for k, v in attrs.items():
        if not hasattr(mod, k):
            setattr(mod, k, v)
    return mod


@pytest.fixture(scope="module")
def profalux():
    # Modules.profalux pulls in Modules.tools (and through it the whole plugin) only
    # for the configure-reporting helpers, which these tests do not exercise.
    stubs = {
        "Modules.pluginDbAttributes": dict(STORE_CONFIGURE_REPORTING="ConfigureReporting"),
        "Modules.sendZigateCommand": dict(raw_APS_request=MagicMock(name="raw_APS_request")),
        "Modules.tools": dict(get_and_inc_ZCL_SQN=MagicMock(name="get_and_inc_ZCL_SQN")),
        "Modules.zigateConsts": dict(ZIGATE_EP="01"),
        "Zigbee.zclCommands": dict(zcl_configure_reporting_requestv2=MagicMock(name="zcl_configure_reporting_requestv2")),
    }
    for name, attrs in stubs.items():
        _ensure_stub(name, **attrs)

    sys.modules.pop("Modules.profalux", None)
    mod = importlib.import_module("Modules.profalux")
    yield mod
    sys.modules.pop("Modules.profalux", None)


def _plugin(model, mac_capa="80", zdevice_id="0302", device_conf=None):
    plugin = MagicMock()
    plugin.DeviceConf = device_conf if device_conf is not None else {
        "MAI-ZTM22C": {},
        "MOT-C1Z06C": {},
        "Telecommande-Profalux": {},
        "VoletBSO-Profalux": {},
    }
    plugin.ListOfDevices = {
        NWKID: {
            "Model": model,
            "MacCapa": mac_capa,
            "ZDeviceID": zdevice_id,
            "ProfileID": "0104",
            "Manufacturer": "1110",
            "Manufacturer Name": "",
            "Ep": {},
        }
    }
    return plugin


class TestProfaluxModelHasOwnConfig:
    def test_reported_model_with_config(self, profalux):
        assert profalux.profalux_model_has_own_config(_plugin("MAI-ZTM22C"), NWKID) is True

    def test_reported_model_without_config(self, profalux):
        assert profalux.profalux_model_has_own_config(_plugin("MAI-UNKNOWN"), NWKID) is False

    @pytest.mark.parametrize("model", PROFALUX_FAKE_MODELS)
    def test_made_up_models_do_not_count(self, profalux, model):
        assert profalux.PROFALUX_FAKE_MODELS == PROFALUX_FAKE_MODELS
        device_conf = {name: {} for name in PROFALUX_FAKE_MODELS}
        assert profalux.profalux_model_has_own_config(_plugin(model, device_conf=device_conf), NWKID) is False

    @pytest.mark.parametrize("model", [{}, "", None])
    def test_missing_model(self, profalux, model):
        # The plugin initialises Model to {}, which is not hashable
        assert profalux.profalux_model_has_own_config(_plugin(model), NWKID) is False

    def test_unknown_device(self, profalux):
        assert profalux.profalux_model_has_own_config(_plugin("MAI-ZTM22C"), "ffff") is False


class TestProfaluxFakeDeviceModel:
    def test_remote_with_own_config_keeps_its_model(self, profalux):
        plugin = _plugin("MAI-ZTM22C")
        profalux.profalux_fake_deviceModel(plugin, NWKID)
        assert plugin.ListOfDevices[NWKID]["Model"] == "MAI-ZTM22C"

    def test_motor_with_own_config_keeps_its_model(self, profalux):
        plugin = _plugin("MOT-C1Z06C", mac_capa="8e", zdevice_id="0200")
        profalux.profalux_fake_deviceModel(plugin, NWKID)
        assert plugin.ListOfDevices[NWKID]["Model"] == "MOT-C1Z06C"

    def test_remote_without_own_config_becomes_telecommande(self, profalux):
        plugin = _plugin({}, zdevice_id="0201")
        profalux.profalux_fake_deviceModel(plugin, NWKID)
        assert plugin.ListOfDevices[NWKID]["Model"] == "Telecommande-Profalux"
        assert plugin.ListOfDevices[NWKID]["Manufacturer Name"] == "Profalux"

    def test_mains_powered_shutter_without_own_config_becomes_voletbso(self, profalux):
        plugin = _plugin("", mac_capa="8e", zdevice_id="0200")
        profalux.profalux_fake_deviceModel(plugin, NWKID)
        assert plugin.ListOfDevices[NWKID]["Model"] == "VoletBSO-Profalux"

    def test_made_up_model_is_still_refined(self, profalux):
        # A shutter already named VoletBSO-Profalux is renamed again from its Location
        plugin = _plugin("VoletBSO-Profalux", mac_capa="8e", zdevice_id="0200")
        plugin.ListOfDevices[NWKID]["Ep"] = {"01": {"0000": {"0010": "BSO"}}}
        profalux.profalux_fake_deviceModel(plugin, NWKID)
        assert plugin.ListOfDevices[NWKID]["Model"] == "BSO-Profalux"
