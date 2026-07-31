#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Modules/tools_device_lookup.py

Coverage:
  - IEEEExist           – present, absent, empty string
  - NwkIdExist          – present, absent
  - getSaddrfromIEEE    – found, not found, empty input
  - getListOfEpForCluster  – returns only eps with ClusterType, excludes fake eps (via stub),
                             respects old-fashion global ClusterType
  - getEPforClusterType – match, no match
  - getClusterListforEP – returns clusters excluding meta-keys
  - getEpForCluster     – found, not found (strict vs non-strict)
"""

import pytest
import sys
import types
from unittest.mock import MagicMock

# Stub Modules.tools_device_lifecycle (only imported lazily inside function bodies)
_lifecycle_stub = types.ModuleType("Modules.tools_device_lifecycle")
_lifecycle_stub.remap_device_nwkid = MagicMock()
_lifecycle_stub.is_fake_ep = MagicMock(return_value=False)
sys.modules.setdefault("Modules.tools_device_lifecycle", _lifecycle_stub)

from Modules.tools_device_lookup import (
    IEEEExist,
    NwkIdExist,
    getClusterListforEP,
    getEPforClusterType,
    getEpForCluster,
    getListOfEpForCluster,
    getSaddrfromIEEE,
)


def _plugin(devices=None, ieee2nwk=None, device_conf=None):
    p = MagicMock()
    p.ListOfDevices = devices if devices is not None else {}
    p.IEEE2NWK = ieee2nwk if ieee2nwk is not None else {}
    p.DeviceConf = device_conf if device_conf is not None else {}
    return p


# ---------------------------------------------------------------------------
# IEEEExist
# ---------------------------------------------------------------------------

class TestIEEEExist:
    def test_present(self):
        p = _plugin(ieee2nwk={"aabbccdd": "1234"})
        assert IEEEExist(p, "aabbccdd") is True

    def test_absent(self):
        p = _plugin(ieee2nwk={})
        assert IEEEExist(p, "aabbccdd") is False

    def test_empty_string(self):
        p = _plugin(ieee2nwk={"aabbccdd": "1234"})
        assert IEEEExist(p, "") is False


# ---------------------------------------------------------------------------
# NwkIdExist
# ---------------------------------------------------------------------------

class TestNwkIdExist:
    def test_present(self):
        p = _plugin(devices={"1234": {}})
        assert NwkIdExist(p, "1234") is True

    def test_absent(self):
        p = _plugin(devices={})
        assert NwkIdExist(p, "dead") is False


# ---------------------------------------------------------------------------
# getSaddrfromIEEE
# ---------------------------------------------------------------------------

class TestGetSaddrFromIEEE:
    def test_found(self):
        p = _plugin(devices={"1234": {"IEEE": "aabb"}})
        assert getSaddrfromIEEE(p, "aabb") == "1234"

    def test_not_found_returns_empty(self):
        p = _plugin(devices={})
        assert getSaddrfromIEEE(p, "aabb") == ""

    def test_empty_input_returns_empty(self):
        p = _plugin()
        assert getSaddrfromIEEE(p, "") == ""


# ---------------------------------------------------------------------------
# getListOfEpForCluster
# ---------------------------------------------------------------------------

class TestGetListOfEpForCluster:
    def setUp_plugin(self, fake_ep=False):
        _lifecycle_stub.is_fake_ep.return_value = fake_ep
        devices = {
            "1234": {
                "Model": "",
                "Ep": {
                    "01": {
                        "0006": {},
                        "ClusterType": {"1": "Switch"},
                    }
                },
            }
        }
        return _plugin(devices=devices)

    def test_returns_ep_with_cluster_and_clustertype(self):
        p = self.setUp_plugin(fake_ep=False)
        result = getListOfEpForCluster(p, "1234", "0006")
        assert "01" in result

    def test_excludes_fake_ep(self):
        p = self.setUp_plugin(fake_ep=True)
        result = getListOfEpForCluster(p, "1234", "0006")
        assert result == []

    def test_missing_device_returns_empty(self):
        p = _plugin({})
        assert getListOfEpForCluster(p, "dead", "0006") == []

    def test_old_fashion_global_clustertype(self):
        _lifecycle_stub.is_fake_ep.return_value = False
        devices = {
            "1234": {
                "Model": "",
                "ClusterType": {"1": "Switch"},
                "Ep": {"01": {"0006": {}}},
            }
        }
        p = _plugin(devices=devices)
        result = getListOfEpForCluster(p, "1234", "0006")
        assert "01" in result


# ---------------------------------------------------------------------------
# getEPforClusterType
# ---------------------------------------------------------------------------

class TestGetEPforClusterType:
    def test_match(self):
        devices = {
            "1234": {
                "Ep": {
                    "01": {"ClusterType": {"1": "Switch"}},
                    "02": {"ClusterType": {"2": "ColorControl"}},
                }
            }
        }
        p = _plugin(devices=devices)
        result = getEPforClusterType(p, "1234", "Switch")
        assert "01" in result
        assert "02" not in result

    def test_no_match_returns_empty(self):
        devices = {"1234": {"Ep": {"01": {"ClusterType": {"1": "Switch"}}}}}
        p = _plugin(devices=devices)
        assert getEPforClusterType(p, "1234", "Dimmer") == []


# ---------------------------------------------------------------------------
# getClusterListforEP
# ---------------------------------------------------------------------------

class TestGetClusterListforEP:
    def test_returns_clusters_excluding_meta(self):
        devices = {
            "1234": {
                "Ep": {
                    "01": {
                        "0006": {},
                        "0008": {},
                        "ClusterType": {"1": "Switch"},
                        "Type": "ZLL",
                        "ColorMode": "1",
                    }
                }
            }
        }
        p = _plugin(devices=devices)
        result = getClusterListforEP(p, "1234", "01")
        assert "0006" in result
        assert "0008" in result
        assert "ClusterType" not in result
        assert "Type" not in result
        assert "ColorMode" not in result

    def test_missing_ep_returns_empty(self):
        p = _plugin({"1234": {"Ep": {}}})
        assert getClusterListforEP(p, "1234", "99") == []


# ---------------------------------------------------------------------------
# getEpForCluster
# ---------------------------------------------------------------------------

class TestGetEpForCluster:
    def test_found(self):
        devices = {"1234": {"Ep": {"01": {"0006": {}}, "02": {"0008": {}}}}}
        p = _plugin(devices=devices)
        result = getEpForCluster(p, "1234", "0006")
        assert "01" in result
        assert "02" not in result

    def test_not_found_non_strict_returns_empty(self):
        devices = {"1234": {"Ep": {"01": {"0008": {}}}}}
        p = _plugin(devices=devices)
        assert getEpForCluster(p, "1234", "0006") == []

    def test_not_found_strict_returns_none(self):
        devices = {"1234": {"Ep": {"01": {"0008": {}}}}}
        p = _plugin(devices=devices)
        assert getEpForCluster(p, "1234", "0006", strict=True) is None

    def test_multiple_eps_with_cluster(self):
        devices = {"1234": {"Ep": {"01": {"0006": {}}, "02": {"0006": {}}}}}
        p = _plugin(devices=devices)
        result = getEpForCluster(p, "1234", "0006")
        assert set(result) == {"01", "02"}
