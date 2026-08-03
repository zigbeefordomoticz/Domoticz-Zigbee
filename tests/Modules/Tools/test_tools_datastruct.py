#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Modules/tools_datastruct.py

Coverage:
  - get_cluster_attribute_value   – found, missing device/ep/cluster/attr
  - check_datastruct              – creates skeleton, unknown device returns None
  - is_time_to_perform_work       – elapsed, not elapsed, unknown device
  - set/get_timestamp_datastruct  – stores and retrieves timestamp
  - get_list_isqn_attr_datastruct / get_list_isqn_int_attr_datastruct
  - set/get_request_datastruct    – stores and retrieves all fields
  - set_request_phase_datastruct  – updates phase
  - get_list_waiting_request_datastruct – returns only "waiting" attributes
  - set/get_isqn_datastruct       – stores and retrieves iSQN
  - set/get_status_datastruct     – stores and retrieves status
  - is_attr_unvalid_datastruct    – 86, 8c, != 00, no status
  - reset_attr_datastruct         – deletes attribute from all sub-dicts
  - reset_cluster_datastruct      – removes cluster entirely
  - reset_device_attribute        – resets top-level attribute to {}
  - clean_old_datastruct          – removes stale attribute key
"""

import pytest
from unittest.mock import MagicMock

from Modules.tools_datastruct import (
    check_datastruct,
    clean_old_datastruct,
    get_cluster_attribute_value,
    get_isqn_datastruct,
    get_list_isqn_attr_datastruct,
    get_list_isqn_int_attr_datastruct,
    get_list_waiting_request_datastruct,
    get_request_datastruct,
    get_status_datastruct,
    is_attr_unvalid_datastruct,
    is_time_to_perform_work,
    reset_attr_datastruct,
    reset_cluster_datastruct,
    reset_device_attribute,
    reset_mismatch_retry_datastruct,
    set_isqn_datastruct,
    set_request_datastruct,
    set_request_phase_datastruct,
    set_status_datastruct,
    set_timestamp_datastruct,
)

NWKID = "1234"
DA    = "configureReporting"
EP    = "01"
CL    = "0006"
AT    = "0000"


def _plugin(devices=None):
    p = MagicMock()
    p.ListOfDevices = devices if devices is not None else {}
    return p


def _ready_plugin():
    """Plugin with a device already present (check_datastruct will build the skeleton)."""
    p = _plugin({NWKID: {}})
    check_datastruct(p, DA, NWKID, EP, CL)
    return p


# ---------------------------------------------------------------------------
# get_cluster_attribute_value
# ---------------------------------------------------------------------------

class TestGetClusterAttributeValue:
    def test_returns_value(self):
        devices = {NWKID: {"Ep": {EP: {CL: {AT: "on"}}}}}
        p = _plugin(devices)
        assert get_cluster_attribute_value(p, NWKID, EP, CL, AT) == "on"

    def test_missing_device_returns_none(self):
        assert get_cluster_attribute_value(_plugin(), "dead", EP, CL, AT) is None

    def test_missing_attr_returns_none(self):
        devices = {NWKID: {"Ep": {EP: {CL: {}}}}}
        p = _plugin(devices)
        assert get_cluster_attribute_value(p, NWKID, EP, CL, AT) is None


# ---------------------------------------------------------------------------
# check_datastruct
# ---------------------------------------------------------------------------

class TestCheckDatastruct:
    def test_creates_skeleton(self):
        p = _plugin({NWKID: {}})
        result = check_datastruct(p, DA, NWKID, EP, CL)
        assert result is True
        cluster = p.ListOfDevices[NWKID][DA]["Ep"][EP][CL]
        assert "TimeStamp" in cluster
        assert "iSQN" in cluster
        assert "Attributes" in cluster
        assert "ZigateRequest" in cluster

    def test_unknown_device_returns_none(self):
        p = _plugin({})
        assert check_datastruct(p, DA, "dead", EP, CL) is None

    def test_idempotent(self):
        p = _plugin({NWKID: {}})
        check_datastruct(p, DA, NWKID, EP, CL)
        check_datastruct(p, DA, NWKID, EP, CL)
        assert p.ListOfDevices[NWKID][DA]["Ep"][EP][CL]["TimeStamp"] == 0


# ---------------------------------------------------------------------------
# is_time_to_perform_work
# ---------------------------------------------------------------------------

class TestIsTimeToPerformWork:
    def test_elapsed(self):
        p = _ready_plugin()
        # TimeStamp is 0, now=1000, period=100 → 1000 >= 100 → True
        assert is_time_to_perform_work(p, DA, NWKID, EP, CL, 1000, 100) is True

    def test_not_elapsed(self):
        p = _ready_plugin()
        set_timestamp_datastruct(p, DA, NWKID, EP, CL, 900)
        # now=950, period=100 → 950 >= 1000 → False
        assert is_time_to_perform_work(p, DA, NWKID, EP, CL, 950, 100) is False

    def test_unknown_device_returns_false(self):
        assert is_time_to_perform_work(_plugin(), DA, "dead", EP, CL, 9999, 1) is False


# ---------------------------------------------------------------------------
# set/get_timestamp_datastruct
# ---------------------------------------------------------------------------

class TestTimestamp:
    def test_stores_and_retrieves(self):
        p = _ready_plugin()
        set_timestamp_datastruct(p, DA, NWKID, EP, CL, 12345)
        ts = p.ListOfDevices[NWKID][DA]["Ep"][EP][CL]["TimeStamp"]
        assert ts == 12345


# ---------------------------------------------------------------------------
# iSQN list helpers
# ---------------------------------------------------------------------------

class TestISQNLists:
    def test_empty_list(self):
        p = _ready_plugin()
        assert get_list_isqn_attr_datastruct(p, DA, NWKID, EP, CL) == []
        assert get_list_isqn_int_attr_datastruct(p, DA, NWKID, EP, CL) == []

    def test_with_entries(self):
        p = _ready_plugin()
        set_isqn_datastruct(p, DA, NWKID, EP, CL, AT, "0a")
        keys = get_list_isqn_attr_datastruct(p, DA, NWKID, EP, CL)
        assert AT in keys
        # int_keys converts the *keys* (attribute IDs) to int, not the iSQN values
        int_keys = get_list_isqn_int_attr_datastruct(p, DA, NWKID, EP, CL)
        assert int(AT, 16) in int_keys


# ---------------------------------------------------------------------------
# set/get_request_datastruct
# ---------------------------------------------------------------------------

class TestRequestDatastruct:
    def _store(self, p):
        set_request_datastruct(p, DA, NWKID, EP, CL, AT,
                               datatype="10", EPin="01", EPout="01",
                               manuf_id="0000", manuf_spec=False,
                               data="01", ackIsDisabled=False, phase="waiting")

    def test_stores_and_retrieves(self):
        p = _ready_plugin()
        self._store(p)
        result = get_request_datastruct(p, DA, NWKID, EP, CL, AT)
        assert result is not None
        dtype, epin, epout, mid, mspec, data, ack = result
        assert dtype == "10"
        assert data == "01"

    def test_missing_attr_returns_none(self):
        p = _ready_plugin()
        assert get_request_datastruct(p, DA, NWKID, EP, CL, "ffff") is None

    def test_unknown_device_returns_none(self):
        assert get_request_datastruct(_plugin(), DA, "dead", EP, CL, AT) is None


# ---------------------------------------------------------------------------
# set_request_phase_datastruct
# ---------------------------------------------------------------------------

class TestRequestPhase:
    def test_updates_phase(self):
        p = _ready_plugin()
        set_request_datastruct(p, DA, NWKID, EP, CL, AT,
                               datatype="10", EPin="01", EPout="01",
                               manuf_id="0000", manuf_spec=False,
                               data="01", ackIsDisabled=False, phase="waiting")
        set_request_phase_datastruct(p, DA, NWKID, EP, CL, AT, "done")
        status = p.ListOfDevices[NWKID][DA]["Ep"][EP][CL]["ZigateRequest"][AT]["Status"]
        assert status == "done"


# ---------------------------------------------------------------------------
# get_list_waiting_request_datastruct
# ---------------------------------------------------------------------------

class TestWaitingRequests:
    def test_returns_waiting_only(self):
        p = _ready_plugin()
        set_request_datastruct(p, DA, NWKID, EP, CL, "0001",
                               datatype="10", EPin="01", EPout="01",
                               manuf_id="0000", manuf_spec=False,
                               data="01", ackIsDisabled=False, phase="waiting")
        set_request_datastruct(p, DA, NWKID, EP, CL, "0002",
                               datatype="10", EPin="01", EPout="01",
                               manuf_id="0000", manuf_spec=False,
                               data="01", ackIsDisabled=False, phase="done")
        waiting = get_list_waiting_request_datastruct(p, DA, NWKID, EP, CL)
        assert "0001" in waiting
        assert "0002" not in waiting

    def test_unknown_device_returns_empty(self):
        assert get_list_waiting_request_datastruct(_plugin(), DA, "dead", EP, CL) == []


# ---------------------------------------------------------------------------
# set/get_isqn_datastruct
# ---------------------------------------------------------------------------

class TestISQNDatastruct:
    def test_stores_and_retrieves(self):
        p = _ready_plugin()
        set_isqn_datastruct(p, DA, NWKID, EP, CL, AT, "0f")
        assert get_isqn_datastruct(p, DA, NWKID, EP, CL, AT) == "0f"

    def test_none_isqn_not_stored(self):
        p = _ready_plugin()
        set_isqn_datastruct(p, DA, NWKID, EP, CL, AT, None)
        assert get_isqn_datastruct(p, DA, NWKID, EP, CL, AT) is None

    def test_unknown_device_returns_none(self):
        assert get_isqn_datastruct(_plugin(), DA, "dead", EP, CL, AT) is None


# ---------------------------------------------------------------------------
# set/get_status_datastruct
# ---------------------------------------------------------------------------

class TestStatusDatastruct:
    def test_stores_and_retrieves_ok(self):
        p = _ready_plugin()
        set_status_datastruct(p, DA, NWKID, EP, CL, AT, "00")
        assert get_status_datastruct(p, DA, NWKID, EP, CL, AT) == "00"

    def test_missing_attr_returns_none(self):
        p = _ready_plugin()
        assert get_status_datastruct(p, DA, NWKID, EP, CL, "ffff") is None


# ---------------------------------------------------------------------------
# is_attr_unvalid_datastruct
# ---------------------------------------------------------------------------

class TestIsAttrUnvalid:
    def test_status_86_is_invalid(self):
        p = _ready_plugin()
        set_status_datastruct(p, DA, NWKID, EP, CL, AT, "86")
        assert is_attr_unvalid_datastruct(p, DA, NWKID, EP, CL, AT) is True

    def test_status_8c_is_invalid(self):
        p = _ready_plugin()
        set_status_datastruct(p, DA, NWKID, EP, CL, AT, "8c")
        assert is_attr_unvalid_datastruct(p, DA, NWKID, EP, CL, AT) is True

    def test_status_00_is_valid(self):
        p = _ready_plugin()
        set_status_datastruct(p, DA, NWKID, EP, CL, AT, "00")
        assert is_attr_unvalid_datastruct(p, DA, NWKID, EP, CL, AT) is False

    def test_no_status_returns_false(self):
        p = _ready_plugin()
        assert is_attr_unvalid_datastruct(p, DA, NWKID, EP, CL, AT) is False

    def test_other_non_zero_status_is_invalid(self):
        p = _ready_plugin()
        set_status_datastruct(p, DA, NWKID, EP, CL, AT, "01")
        assert is_attr_unvalid_datastruct(p, DA, NWKID, EP, CL, AT) is True


# ---------------------------------------------------------------------------
# reset_attr_datastruct
# ---------------------------------------------------------------------------

class TestResetAttr:
    def test_removes_from_all_sub_dicts(self):
        p = _ready_plugin()
        set_isqn_datastruct(p, DA, NWKID, EP, CL, AT, "01")
        set_status_datastruct(p, DA, NWKID, EP, CL, AT, "00")
        reset_attr_datastruct(p, DA, NWKID, EP, CL, AT)
        cluster = p.ListOfDevices[NWKID][DA]["Ep"][EP][CL]
        assert AT not in cluster["iSQN"]
        assert AT not in cluster["Attributes"]

    def test_unknown_device_no_crash(self):
        reset_attr_datastruct(_plugin(), DA, "dead", EP, CL, AT)


# ---------------------------------------------------------------------------
# reset_cluster_datastruct
# ---------------------------------------------------------------------------

class TestResetCluster:
    def test_removes_cluster(self):
        p = _ready_plugin()
        reset_cluster_datastruct(p, DA, NWKID, EP, CL)
        assert CL not in p.ListOfDevices[NWKID][DA]["Ep"][EP]


# ---------------------------------------------------------------------------
# reset_device_attribute
# ---------------------------------------------------------------------------

class TestResetDeviceAttribute:
    def test_resets_to_empty_dict(self):
        p = _plugin({NWKID: {"configureReporting": {"some": "data"}}})
        reset_device_attribute(p, NWKID, "configureReporting")
        assert p.ListOfDevices[NWKID]["configureReporting"] == {}

    def test_unknown_device_no_crash(self):
        reset_device_attribute(_plugin(), "dead", "configureReporting")


# ---------------------------------------------------------------------------
# clean_old_datastruct
# ---------------------------------------------------------------------------

class TestCleanOldDatastruct:
    def test_removes_stale_key(self):
        p = _ready_plugin()
        # Manually inject a stale key at the cluster level
        p.ListOfDevices[NWKID][DA]["Ep"][EP][CL][AT] = "stale"
        clean_old_datastruct(p, DA, NWKID, EP, CL, AT)
        assert AT not in p.ListOfDevices[NWKID][DA]["Ep"][EP][CL]

    def test_unknown_device_returns_false(self):
        assert clean_old_datastruct(_plugin(), DA, "dead", EP, CL, AT) is False


# ---------------------------------------------------------------------------
# reset_mismatch_retry_datastruct
# ---------------------------------------------------------------------------

class TestResetMismatchRetryDatastruct:
    def test_clears_mismatch_retry_keeps_other_keys(self):
        p = _ready_plugin()
        cluster = p.ListOfDevices[NWKID][DA]["Ep"][EP][CL]
        cluster["MismatchRetry"] = {"Count": 3, "TimeStamp": 12345, "Reported": True}
        set_timestamp_datastruct(p, DA, NWKID, EP, CL, 999)
        set_isqn_datastruct(p, DA, NWKID, EP, CL, AT, "0a")

        reset_mismatch_retry_datastruct(p, DA, NWKID)

        assert "MismatchRetry" not in cluster
        # Untouched state used by the rest of the plugin
        assert cluster["TimeStamp"] == 999
        assert cluster["iSQN"][AT] == "0a"

    def test_clears_across_multiple_ep_and_clusters(self):
        p = _ready_plugin()
        check_datastruct(p, DA, NWKID, "02", "0402")
        p.ListOfDevices[NWKID][DA]["Ep"][EP][CL]["MismatchRetry"] = {"Count": 1, "TimeStamp": 1, "Reported": False}
        p.ListOfDevices[NWKID][DA]["Ep"]["02"]["0402"]["MismatchRetry"] = {"Count": 2, "TimeStamp": 2, "Reported": True}

        reset_mismatch_retry_datastruct(p, DA, NWKID)

        assert "MismatchRetry" not in p.ListOfDevices[NWKID][DA]["Ep"][EP][CL]
        assert "MismatchRetry" not in p.ListOfDevices[NWKID][DA]["Ep"]["02"]["0402"]

    def test_no_mismatch_retry_present_is_a_no_op(self):
        p = _ready_plugin()
        # Should not raise even though "MismatchRetry" was never set
        reset_mismatch_retry_datastruct(p, DA, NWKID)
        assert "MismatchRetry" not in p.ListOfDevices[NWKID][DA]["Ep"][EP][CL]

    def test_unknown_device_no_crash(self):
        reset_mismatch_retry_datastruct(_plugin(), DA, "dead")

    def test_device_without_the_attribute_no_crash(self):
        p = _plugin({NWKID: {}})
        reset_mismatch_retry_datastruct(p, DA, NWKID)
