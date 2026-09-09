#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression test for Modules/readZclClusters.py:process_cluster_attribute_response /
compute_attribute_value

Context (Sonoff SWV-ZFE smart water valve, cluster 0xfc11):
  Attributes 0x5006 (RealtimeIrrigationDuration) and 0x5007 (RealtimeIrrigationVolume)
  are 32-bit unsigned integers (DataType 0x23). Field observation on device 0x86e6
  showed the firmware serializes these two live counters with reversed byte order
  when pushed unsolicited via "Report Attributes" (internal Source "8102"), but in
  the correct order when answering our own "Read Attributes" request (Source "8100"):

      Source 8102: Data "3e000000" -> naive decode = 1040187392  (wrong; real value 62)
      Source 8100: Data "0000003e" -> naive decode = 62          (correct)

  The z4d-certified-devices config for SWV-ZFE.json compensates for this purely via
  an "EvalExp" formula that is conditional on Source (byte-swap unless Source=="8100"),
  which requires Source to be visible inside compute_attribute_value()'s eval() scope.
  This test locks in that plumbing.
"""

import sys
import types
import importlib
from unittest.mock import MagicMock

import pytest


def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


@pytest.fixture(scope="module")
def rzc():
    """Import Modules.readZclClusters with all external deps stubbed out."""
    stubs = {
        "DevicesModules": _make_stub(
            "DevicesModules", FUNCTION_MODULE={}, FUNCTION_WITH_ACTIONS_MODULE={}
        ),
        "Modules.batterieManagement": _make_stub(
            "Modules.batterieManagement", UpdateBatteryAttribute=MagicMock(name="UpdateBatteryAttribute")
        ),
        "Modules.domoMaj": _make_stub(
            "Modules.domoMaj", MajDomoDevice=MagicMock(name="MajDomoDevice")
        ),
        "Modules.tools": _make_stub(
            "Modules.tools",
            checkAndStoreAttributeValue=MagicMock(name="checkAndStoreAttributeValue"),
            get_device_config_param=MagicMock(name="get_device_config_param", return_value=False),
            get_deviceconf_parameter_value=MagicMock(name="get_deviceconf_parameter_value", return_value=None),
            getAttributeValue=MagicMock(name="getAttributeValue"),
            store_battery_percentage_time_stamp=MagicMock(name="store_battery_percentage_time_stamp"),
            store_battery_voltage_time_stamp=MagicMock(name="store_battery_voltage_time_stamp"),
        ),
        "Modules.zclClusterHelpers": _make_stub(
            "Modules.zclClusterHelpers",
            # Mirrors the real (byte-order-naive) decode_32bit_uint: plain int(hex, 16).
            decoding_attribute_data=MagicMock(
                name="decoding_attribute_data",
                side_effect=lambda attribute_type, attribute_value, handle_errors=False: (
                    int(attribute_value, 16) if attribute_value else ""
                ),
            ),
            handle_model_name=MagicMock(name="handle_model_name"),
        ),
    }

    tracked = list(stubs) + ["Modules.readZclClusters"]
    saved = {name: sys.modules.get(name) for name in tracked}
    sys.modules.update(stubs)

    sys.modules.pop("Modules.readZclClusters", None)
    module = importlib.import_module("Modules.readZclClusters")

    yield module

    for name, old in saved.items():
        if old is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old


NWKID = "86e6"
EP = "01"
CLUSTER = "fc11"
ATTR_VOLUME = "5007"

BYTE_SWAP_EVAL_EXP = (
    "value if Source == '8100' else "
    "(((value & 0xFF) << 24) | ((value & 0xFF00) << 8) | ((value >> 8) & 0xFF00) | ((value >> 24) & 0xFF))"
)


def _plugin():
    p = MagicMock()
    p.log = MagicMock()
    p.log.logging = MagicMock()
    p.pluginconf = MagicMock()
    p.pluginconf.pluginConf = {"TrackingEraticValue": False, "trackZclClustersIn": False}
    p.ListOfDevices = {NWKID: {"Model": "SWV-ZFE"}}
    p.DeviceConf = {
        "SWV-ZFE": {
            "Ep": {
                EP: {
                    CLUSTER: {
                        "Attributes": {
                            ATTR_VOLUME: {
                                "Name": "RealtimeIrrigationVolume",
                                "DataType": "23",
                                "EvalExp": BYTE_SWAP_EVAL_EXP,
                                "ActionList": ["check_store_value", "upd_domo_device"],
                            }
                        }
                    }
                }
            }
        }
    }
    p.readZclClusters = {}
    return p


def test_report_attributes_reversed_bytes_corrected(rzc, monkeypatch):
    """Source 8102 (unsolicited report): raw bytes are reversed on this device -> must be swapped back to 62."""
    maj_domo = MagicMock()
    monkeypatch.setattr(rzc, "MajDomoDevice", maj_domo)

    rzc.process_cluster_attribute_response(
        _plugin(), {}, "01", NWKID, EP, CLUSTER, ATTR_VOLUME, "23", "0004", "3e000000", Source="8102",
    )

    maj_domo.assert_called_once()
    assert maj_domo.call_args.args[5] == 62


def test_read_attribute_response_correct_bytes_untouched(rzc, monkeypatch):
    """Source 8100 (our own read response): raw bytes already correct -> must be passed through unchanged."""
    maj_domo = MagicMock()
    monkeypatch.setattr(rzc, "MajDomoDevice", maj_domo)

    rzc.process_cluster_attribute_response(
        _plugin(), {}, "01", NWKID, EP, CLUSTER, ATTR_VOLUME, "23", "0004", "0000003e", Source="8100",
    )

    maj_domo.assert_called_once()
    assert maj_domo.call_args.args[5] == 62
