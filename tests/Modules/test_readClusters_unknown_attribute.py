#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Modules/readClusters.py:ReadCluster, fallback branch

Coverage:
  - An attribute with no ZCL definition (generic or device specific) and no
    legacy decoder is stored raw and logged, as before.
  - Its read status / timestamp is now recorded in "ReadAttributes", as the
    two other branches already did.
  - It is NOT routed to process_cluster_attribute_response(): with no
    definition that call has no action to run, so nothing would be stored,
    and it logs an Error for each parameter lookup on an unknown cluster.
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


NWKID = "c4b2"
EP = "01"
CLUSTER = "fc99"   # no ZCL definition and not in DECODE_CLUSTER


def _plugin():
    p = MagicMock()
    p.ListOfDevices = {NWKID: {"Model": "x", "Ep": {EP: {}}}}
    return p


def test_unknown_attribute_is_stored_raw_with_status(rc, monkeypatch):
    assert CLUSTER not in rc.DECODE_CLUSTER
    check_store = MagicMock()
    set_status = MagicMock()
    set_timestamp = MagicMock()
    process = MagicMock()
    monkeypatch.setattr(rc, "is_cluster_zcl_config_available", lambda *a, **kw: False)
    monkeypatch.setattr(rc, "checkAndStoreAttributeValue", check_store)
    monkeypatch.setattr(rc, "set_status_datastruct", set_status)
    monkeypatch.setattr(rc, "set_timestamp_datastruct", set_timestamp)
    monkeypatch.setattr(rc, "process_cluster_attribute_response", process)

    p = _plugin()
    rc.ReadCluster(p, {}, "8100", "01", NWKID, EP, CLUSTER, "0010", "00", "21", "0002", "000a", Source="8100")

    check_store.assert_called_once_with(p, NWKID, EP, CLUSTER, "0010", "000a")
    set_status.assert_called_once_with(p, "ReadAttributes", NWKID, EP, CLUSTER, "0010", "00")
    set_timestamp.assert_called_once()
    process.assert_not_called()
    assert any("unknow" in str(c.args) for c in p.log.logging.call_args_list)


def test_error_status_still_returns_early(rc, monkeypatch):
    check_store = MagicMock()
    set_status = MagicMock()
    monkeypatch.setattr(rc, "checkAndStoreAttributeValue", check_store)
    monkeypatch.setattr(rc, "set_status_datastruct", set_status)
    monkeypatch.setattr(rc, "set_timestamp_datastruct", MagicMock())

    p = _plugin()
    rc.ReadCluster(p, {}, "8100", "01", NWKID, EP, CLUSTER, "0010", "86", "21", "0000", "", Source="8100")

    set_status.assert_called_once_with(p, "ReadAttributes", NWKID, EP, CLUSTER, "0010", "86")
    check_store.assert_not_called()
