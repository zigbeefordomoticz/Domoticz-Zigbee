#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_configure_reporting_color_zdeviceid.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Regression test for #2335: the default reporting table limits the colour
attributes of cluster 0300 to a list of ZDeviceID written in uppercase
("010D"), while the Simple Descriptor decoder stores the device id in
lowercase ("010d"). An Extended Color Light never matched, and its colour X,
colour Y and colour temperature reporting was never configured.

Classes.ConfigureReporting is imported inside a module-scoped fixture, against
locally stubbed dependencies, and sys.modules is restored on teardown (same
pattern as test_configure_reporting_mismatch_retry.py). The reporting table is
the real one.

Run with:
    python -m pytest tests/Classes/ConfigureReporting/test_configure_reporting_color_zdeviceid.py -v
"""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest


NWKID = "35fd"
EP = "01"
CLUSTER = "0300"

COLOR_X = "0003"
COLOR_Y = "0004"
COLOR_TEMP = "0007"
COLOR_MODE = "0008"

_STUBS = {
    "Classes.ZigateTransport.sqnMgmt": (
        "TYPE_APP_ZCL", "sqn_get_internal_sqn_from_app_sqn",
    ),
    "Modules.bindings": ("bindDevice", "unbindDevice"),
    "Modules.tools": (
        "check_datastruct", "deviceconf_device", "get_device_config_param",
        "get_isqn_datastruct", "get_list_isqn_attr_datastruct",
        "get_list_isqn_int_attr_datastruct", "getClusterListforEP",
        "is_ack_tobe_disabled", "is_attr_unvalid_datastruct", "is_bind_ep",
        "is_fake_ep", "is_time_to_perform_work", "mainPoweredDevice",
        "reset_attr_datastruct", "set_isqn_datastruct", "set_status_datastruct",
        "set_timestamp_datastruct",
    ),
    "Zigbee.zclCommands": (
        "zcl_configure_reporting_requestv2", "zcl_read_report_config_request",
    ),
}

# Other test modules may have installed stand-ins for these: force a real import.
_REAL_MODULES = ["Modules.pluginDbAttributes", "Modules.zigateConsts"]


@pytest.fixture(scope="module")
def cr_module():
    names = list(_STUBS) + ["Classes.ConfigureReporting"] + _REAL_MODULES
    saved = {name: sys.modules.pop(name, None) for name in names}
    for name, attrs in _STUBS.items():
        stub = types.ModuleType(name)
        for attr in attrs:
            setattr(stub, attr, MagicMock(name=attr))
        sys.modules[name] = stub

    yield importlib.import_module("Classes.ConfigureReporting")

    for name in names:
        sys.modules.pop(name, None)
    for name, mod in saved.items():
        if mod is not None:
            sys.modules[name] = mod


def _configured_attributes(cr_module, zdeviceid, cluster_configuration=None):
    """Run the 0300 reporting for a device with this ZDeviceID, return the attributes requested."""
    o = object.__new__(cr_module.ConfigureReporting)
    o.log = MagicMock()
    o.DeviceConf = {}
    o.zigbee_communication = "zigpy"
    o.pluginconf = MagicMock()
    o.ListOfDevices = {NWKID: {"ZDeviceID": zdeviceid, "Ep": {EP: {CLUSTER: {}}}}}
    o.prepare_and_send_configure_reporting = MagicMock()

    if cluster_configuration is None:
        cluster_configuration = o.retreive_configuration_reporting_definition(NWKID)[CLUSTER]["Attributes"]
    cr_module.configure_reporting_for_one_cluster(o, NWKID, EP, CLUSTER, False, cluster_configuration)

    o.prepare_and_send_configure_reporting.assert_called_once()
    return o.prepare_and_send_configure_reporting.call_args.args[-1]


@pytest.mark.parametrize("zdeviceid", ["010d", "010D"])
def test_extended_color_light_gets_its_colour_reporting(cr_module, zdeviceid):
    """010d, as stored by the Simple Descriptor decoder, and 010D are the same device id."""
    assert _configured_attributes(cr_module, zdeviceid) == [COLOR_X, COLOR_Y, COLOR_TEMP, COLOR_MODE]


@pytest.mark.parametrize("zdeviceid, expected", [
    ("0200", [COLOR_X, COLOR_Y, COLOR_MODE]),
    ("0210", [COLOR_X, COLOR_Y, COLOR_TEMP, COLOR_MODE]),
    ("0102", [COLOR_TEMP, COLOR_MODE]),
    ("0220", [COLOR_TEMP, COLOR_MODE]),
    ("0100", [COLOR_MODE]),
    ("010c", [COLOR_MODE]),
])
def test_other_device_ids_are_unchanged(cr_module, zdeviceid, expected):
    assert _configured_attributes(cr_module, zdeviceid) == expected


@pytest.mark.parametrize("zdeviceid", [None, "", {}])
def test_unknown_device_id_configures_nothing(cr_module, zdeviceid):
    assert _configured_attributes(cr_module, zdeviceid) == []


def test_attribute_without_device_id_list_is_configured(cr_module):
    """A device specific configuration has no ZDeviceID list."""
    assert _configured_attributes(cr_module, "010d", {COLOR_X: {"DataType": "21"}}) == [COLOR_X]
