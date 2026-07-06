#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Modules.philips.is_philips_device.

Regression coverage for GitHub issue #1997: a Tuya device (e.g. TS011F-plug,
manufacturer "_TZ3000_cehuw1lw") can misreport ManufacturerCode 0x100b, which
is Signify/Philips's registered code. is_philips_device() used to trust that
code blindly, causing On/Off writes to be routed to the wrong endpoint.

Modules.tuyaTools is imported for real (not stubbed) so the fix - delegating
to tuya_manufacturer_device() - is actually exercised end to end.
"""

import sys
import types
import importlib

import pytest
from unittest.mock import MagicMock


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
def philips_module():
    stubs = {
        "Modules.basicOutputs": dict(
            raw_APS_request=MagicMock(name="raw_APS_request"),
            set_poweron_afteroffon=MagicMock(name="set_poweron_afteroffon"),
            write_attribute=MagicMock(name="write_attribute"),
        ),
        "Modules.domoMaj": dict(MajDomoDevice=MagicMock(name="MajDomoDevice")),
        "Modules.readAttributes": dict(
            ReadAttributeRequest_0006_0000=MagicMock(name="ReadAttributeRequest_0006_0000"),
            ReadAttributeRequest_0006_400x=MagicMock(name="ReadAttributeRequest_0006_400x"),
            ReadAttributeRequest_0008_0000=MagicMock(name="ReadAttributeRequest_0008_0000"),
            ReadAttributeRequest_0406_philips_0030=MagicMock(name="ReadAttributeRequest_0406_philips_0030"),
        ),
        "Modules.tools": dict(
            checkAndStoreAttributeValue=MagicMock(name="checkAndStoreAttributeValue"),
            get_device_config_param=MagicMock(name="get_device_config_param", return_value=None),
            get_deviceconf_parameter_value=MagicMock(name="get_deviceconf_parameter_value", return_value=None),
            is_hex=MagicMock(name="is_hex", return_value=True),
            retreive_cmd_payload_from_8002=MagicMock(name="retreive_cmd_payload_from_8002"),
            is_ack_tobe_disabled=MagicMock(name="is_ack_tobe_disabled", return_value=False),
        ),
        "Modules.tuyaConst": dict(TUYA_MANUFACTURER_NAME=()),
        "Modules.zigateConsts": dict(ZIGATE_EP="01"),
    }
    for name, attrs in stubs.items():
        _ensure_stub(name, **attrs)

    # Import the real tuyaTools so the fix (delegating to
    # tuya_manufacturer_device) is genuinely exercised, not mocked away.
    sys.modules.pop("Modules.tuyaTools", None)
    sys.modules.pop("Modules.philips", None)
    mod = importlib.import_module("Modules.philips")
    yield mod
    sys.modules.pop("Modules.philips", None)
    sys.modules.pop("Modules.tuyaTools", None)


@pytest.fixture
def plugin():
    p = MagicMock()
    p.DeviceConf = {}
    return p


NWKID = "1234"


def test_tuya_device_misreporting_100b_is_not_philips(philips_module, plugin):
    """Regression #1997: _TZ3000 Tuya plug reporting ManufacturerCode 100b."""
    plugin.ListOfDevices = {
        NWKID: {
            "Manufacturer": "100b",
            "Manufacturer Name": "_TZ3000_cehuw1lw",
            "Model": "TS011F-plug",
        }
    }
    assert philips_module.is_philips_device(plugin, NWKID) is False


def test_genuine_philips_device_by_manufacturer_code(philips_module, plugin):
    plugin.ListOfDevices = {
        NWKID: {"Manufacturer": "100b", "Manufacturer Name": "Signify Netherlands B.V.", "Model": "LCT001"}
    }
    assert philips_module.is_philips_device(plugin, NWKID) is True


def test_genuine_philips_device_by_manufacturer_name(philips_module, plugin):
    plugin.ListOfDevices = {
        NWKID: {"Manufacturer": "1234", "Manufacturer Name": "Philips", "Model": "LWB010"}
    }
    assert philips_module.is_philips_device(plugin, NWKID) is True


def test_unrelated_device_is_not_philips(philips_module, plugin):
    plugin.ListOfDevices = {
        NWKID: {"Manufacturer": "1021", "Manufacturer Name": "IKEA of Sweden", "Model": "TRADFRI bulb"}
    }
    assert philips_module.is_philips_device(plugin, NWKID) is False
