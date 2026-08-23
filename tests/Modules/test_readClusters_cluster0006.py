#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Modules/readClusters.py:Cluster0006

Coverage:
  - TUYA_REMOTE-flagged devices (e.g. TS0041 and its siblings): a plain OnOff
    (0x0006 attribute 0x0000) Report Attributes frame must NOT be forwarded to
    MajDomoDevice. These devices report their real clicks exclusively via the
    manufacturer-specific 0xFD/0xFC commands (see Z4D_decoders/z4d_decoder_
    Remotes.py:Decode8095), which never go through Cluster0006 at all. A plain
    attribute report from such a device is just an idle/heartbeat re-statement
    of the resting state and previously forced a spurious Domoticz widget
    update (and any dzVents "on device" automation) on every occurrence.
  - Non-TUYA_REMOTE devices are unaffected: the OnOff attribute report is
    still forwarded to MajDomoDevice as before (regression guard).
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
def rc():
    """Import Modules.readClusters with all external deps stubbed out."""
    stubs = {
        "Modules.domoMaj": _make_stub(
            "Modules.domoMaj", MajDomoDevice=MagicMock(name="MajDomoDevice")
        ),
        "Modules.ikeaTradfri": _make_stub(
            "Modules.ikeaTradfri", ikea_air_purifier_cluster=MagicMock(name="ikea_air_purifier_cluster")
        ),
        "Modules.lumi": _make_stub(
            "Modules.lumi",
            AqaraOppleDecoding0012=MagicMock(name="AqaraOppleDecoding0012"),
            cube_decode=MagicMock(name="cube_decode"),
            decode_vibr=MagicMock(name="decode_vibr"),
            decode_vibrAngle=MagicMock(name="decode_vibrAngle"),
        ),
        "Modules.philips": _make_stub(
            "Modules.philips", philips_dimmer_switch=MagicMock(name="philips_dimmer_switch")
        ),
        "Modules.readZclClusters": _make_stub(
            "Modules.readZclClusters",
            is_cluster_zcl_config_available=MagicMock(name="is_cluster_zcl_config_available", return_value=False),
            process_cluster_attribute_response=MagicMock(name="process_cluster_attribute_response"),
        ),
        "Modules.schneider_wiser": _make_stub(
            "Modules.schneider_wiser",
            receiving_heatingdemand_attribute=MagicMock(name="receiving_heatingdemand_attribute"),
            receiving_heatingpoint_attribute=MagicMock(name="receiving_heatingpoint_attribute"),
        ),
        "Modules.tools": _make_stub(
            "Modules.tools",
            DeviceExist=MagicMock(name="DeviceExist", return_value=True),
            checkAndStoreAttributeValue=MagicMock(name="checkAndStoreAttributeValue"),
            checkAttribute=MagicMock(name="checkAttribute"),
            checkValidValue=MagicMock(name="checkValidValue", return_value=True),
            get_deviceconf_parameter_value=MagicMock(name="get_deviceconf_parameter_value", return_value=None),
            getEPforClusterType=MagicMock(name="getEPforClusterType", return_value=[]),
            set_status_datastruct=MagicMock(name="set_status_datastruct"),
            set_timestamp_datastruct=MagicMock(name="set_timestamp_datastruct"),
        ),
        "Modules.zclClusterHelpers": _make_stub(
            "Modules.zclClusterHelpers", compute_metering_conso=MagicMock(name="compute_metering_conso")
        ),
        "Modules.zigateConsts": _make_stub("Modules.zigateConsts", ZONE_TYPE={}),
    }

    # Track "Modules.readClusters" itself too, so teardown restores whatever
    # was cached before this fixture ran (e.g. a real module imported during
    # collection) instead of evicting it and leaving downstream tests to
    # re-import it against the (incomplete) global conftest stubs.
    tracked = list(stubs) + ["Modules.readClusters"]
    saved = {name: sys.modules.get(name) for name in tracked}
    sys.modules.update(stubs)

    sys.modules.pop("Modules.readClusters", None)
    module = importlib.import_module("Modules.readClusters")

    yield module

    for name, old in saved.items():
        if old is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old


def _plugin(model="TS0041"):
    p = MagicMock()
    p.log = MagicMock()
    p.log.logging = MagicMock()
    p.ListOfDevices = {"c4b2": {"Model": model}}
    return p


NWKID = "c4b2"
EP = "01"
CLUSTER = "0006"


def test_tuya_remote_onoff_report_is_dropped(rc, monkeypatch):
    """Regression: a TS0041-style plain OnOff heartbeat must not reach MajDomoDevice."""
    monkeypatch.setattr(rc, "get_deviceconf_parameter_value", lambda *a, **kw: True)
    maj_domo = MagicMock()
    check_store = MagicMock()
    monkeypatch.setattr(rc, "MajDomoDevice", maj_domo)
    monkeypatch.setattr(rc, "checkAndStoreAttributeValue", check_store)

    p = _plugin(model="TS0041")
    rc.Cluster0006(p, {}, "01", NWKID, EP, CLUSTER, "0000", "10", "0001", "00", Source="8102")

    maj_domo.assert_not_called()
    check_store.assert_called_once_with(p, NWKID, EP, CLUSTER, "0000", "00")


def test_non_tuya_remote_onoff_report_is_forwarded(rc, monkeypatch):
    """Regression guard: ordinary OnOff devices keep forwarding to MajDomoDevice."""
    monkeypatch.setattr(rc, "get_deviceconf_parameter_value", lambda *a, **kw: None)
    maj_domo = MagicMock()
    check_store = MagicMock()
    monkeypatch.setattr(rc, "MajDomoDevice", maj_domo)
    monkeypatch.setattr(rc, "checkAndStoreAttributeValue", check_store)

    p = _plugin(model="TS011F-plug")
    rc.Cluster0006(p, {}, "01", NWKID, EP, CLUSTER, "0000", "10", "0001", "00", Source="8102")

    maj_domo.assert_called_once_with(p, {}, NWKID, EP, CLUSTER, "00")
    check_store.assert_called_once_with(p, NWKID, EP, CLUSTER, "0000", "00")
