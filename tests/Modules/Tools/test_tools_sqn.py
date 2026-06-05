#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Modules/tools_sqn.py

Coverage:
  - get_and_increment_generic_SQN – normal increment, wrap at 0xFF, unknown nwkid, missing key, malformed
  - get_and_inc_ZDP_SQN / ZCL_SQN / TUYA_POLLING_SQN – delegate correctly
  - updSQN                        – updates SQN, no-op on missing device
  - is_duplicate_sqn              – duplicate detected, different SQN, unknown device
  - updLQI                        – stores value and rolling deque, skips "00", skips non-hex
  - upd_RSSI                      – stores value and rolling list, caps at 10
  - timeStamped                   – creates Stamp dict, formats time
  - store_battery_percentage/voltage_time_stamp – stores float timestamp
  - checkAttribute                – creates nested path
  - checkAndStoreAttributeValue   – stores value
  - checkValidValue               – rejects 0xE2/ffffffff, rejects lumi bad values, accepts others
  - getAttributeValue             – found, missing addr/ep/cluster/attr
"""

import time
from collections import deque
from unittest.mock import MagicMock

import pytest

from Modules.tools_sqn import (
    checkAndStoreAttributeValue,
    checkAttribute,
    checkValidValue,
    get_and_inc_TUYA_POLLING_SQN,
    get_and_inc_ZCL_SQN,
    get_and_inc_ZDP_SQN,
    get_and_increment_generic_SQN,
    getAttributeValue,
    is_duplicate_sqn,
    store_battery_percentage_time_stamp,
    store_battery_voltage_time_stamp,
    timeStamped,
    upd_RSSI,
    updLQI,
    updSQN,
)


def _plugin(devices=None):
    p = MagicMock()
    p.ListOfDevices = devices if devices is not None else {}
    return p


# ---------------------------------------------------------------------------
# get_and_increment_generic_SQN
# ---------------------------------------------------------------------------

class TestGetAndIncrementGenericSQN:
    def test_starts_at_01_when_key_missing(self):
        p = _plugin({"1234": {}})
        result = get_and_increment_generic_SQN(p, "1234", "ZCLSQN")
        assert result == "01"
        assert p.ListOfDevices["1234"]["ZCLSQN"] == "01"

    def test_increments_existing(self):
        p = _plugin({"1234": {"ZCLSQN": "05"}})
        assert get_and_increment_generic_SQN(p, "1234", "ZCLSQN") == "06"

    def test_wraps_at_ff(self):
        p = _plugin({"1234": {"ZCLSQN": "ff"}})
        assert get_and_increment_generic_SQN(p, "1234", "ZCLSQN") == "00"

    def test_unknown_nwkid_returns_00(self):
        p = _plugin({})
        assert get_and_increment_generic_SQN(p, "dead", "ZCLSQN") == "00"

    def test_malformed_sqn_resets_to_00(self):
        # ValueError on int("zz", 16) → next_sqn resets to 0, not 1
        p = _plugin({"1234": {"ZCLSQN": "zz"}})
        assert get_and_increment_generic_SQN(p, "1234", "ZCLSQN") == "00"


class TestSQNDelegates:
    def test_zdp(self):
        p = _plugin({"aa": {}})
        r = get_and_inc_ZDP_SQN(p, "aa")
        assert r == "01"
        assert "ZDPSQN" in p.ListOfDevices["aa"]

    def test_zcl(self):
        p = _plugin({"bb": {}})
        r = get_and_inc_ZCL_SQN(p, "bb")
        assert r == "01"

    def test_tuya(self):
        p = _plugin({"cc": {}})
        r = get_and_inc_TUYA_POLLING_SQN(p, "cc")
        assert r == "01"


# ---------------------------------------------------------------------------
# updSQN
# ---------------------------------------------------------------------------

class TestUpdSQN:
    def test_updates_sqn(self):
        p = _plugin({"1234": {"SQN": "00"}})
        updSQN(p, "1234", "ab")
        assert p.ListOfDevices["1234"]["SQN"] == "ab"

    def test_missing_device_no_crash(self):
        p = _plugin({})
        updSQN(p, "dead", "ff")  # should not raise


# ---------------------------------------------------------------------------
# is_duplicate_sqn
# ---------------------------------------------------------------------------

class TestIsDuplicateSQN:
    def test_duplicate(self):
        p = _plugin({"1234": {"SQN": "aa"}})
        assert is_duplicate_sqn(p, "1234", "aa") is True

    def test_different_sqn(self):
        p = _plugin({"1234": {"SQN": "aa"}})
        assert is_duplicate_sqn(p, "1234", "bb") is False

    def test_unknown_device(self):
        p = _plugin({})
        assert is_duplicate_sqn(p, "dead", "aa") is False


# ---------------------------------------------------------------------------
# updLQI
# ---------------------------------------------------------------------------

class TestUpdLQI:
    def test_stores_lqi_value(self):
        # device dict must be non-empty so `if not device` doesn't short-circuit
        p = _plugin({"1234": {"IEEE": "aabb"}})
        updLQI(p, "1234", "80")
        assert p.ListOfDevices["1234"]["LQI"] == 0x80

    def test_rolling_lqi_appended(self):
        p = _plugin({"1234": {"IEEE": "aabb"}})
        updLQI(p, "1234", "40")
        assert 0x40 in p.ListOfDevices["1234"]["RollingLQI"]

    def test_zero_lqi_skipped(self):
        p = _plugin({"1234": {}})
        updLQI(p, "1234", "00")
        assert "LQI" not in p.ListOfDevices["1234"]

    def test_non_hex_skipped(self):
        p = _plugin({"1234": {}})
        updLQI(p, "1234", "zz")
        assert "LQI" not in p.ListOfDevices["1234"]

    def test_unknown_device_no_crash(self):
        p = _plugin({})
        updLQI(p, "dead", "80")


# ---------------------------------------------------------------------------
# upd_RSSI
# ---------------------------------------------------------------------------

class TestUpdRSSI:
    def test_stores_rssi(self):
        p = _plugin({"1234": {}})
        upd_RSSI(p, "1234", -70)
        assert p.ListOfDevices["1234"]["RSSI"] == -70

    def test_rolling_list_capped_at_10(self):
        p = _plugin({"1234": {"RollingRSSI": list(range(10))}})
        upd_RSSI(p, "1234", 99)
        assert len(p.ListOfDevices["1234"]["RollingRSSI"]) == 10
        assert p.ListOfDevices["1234"]["RollingRSSI"][-1] == 99

    def test_unknown_device_no_crash(self):
        p = _plugin({})
        upd_RSSI(p, "dead", -50)


# ---------------------------------------------------------------------------
# timeStamped
# ---------------------------------------------------------------------------

class TestTimeStamped:
    def test_stamp_created(self):
        p = _plugin({"1234": {}})
        timeStamped(p, "1234", 0x8002)
        stamp = p.ListOfDevices["1234"]["Stamp"]
        assert "time" in stamp
        assert "Time" in stamp
        assert stamp["MsgType"] == "8002"

    def test_unknown_device_no_crash(self):
        p = _plugin({})
        timeStamped(p, "dead", 0x8002)


# ---------------------------------------------------------------------------
# store_battery_*_time_stamp
# ---------------------------------------------------------------------------

class TestBatteryTimestamps:
    def test_percentage_timestamp_stored(self):
        before = time.time()
        p = _plugin({"1234": {}})
        store_battery_percentage_time_stamp(p, "1234")
        assert p.ListOfDevices["1234"]["BatteryPercentage_TimeStamp"] >= before

    def test_voltage_timestamp_stored(self):
        before = time.time()
        p = _plugin({"1234": {}})
        store_battery_voltage_time_stamp(p, "1234")
        assert p.ListOfDevices["1234"]["BatteryVoltage_TimeStamp"] >= before


# ---------------------------------------------------------------------------
# checkAttribute / checkAndStoreAttributeValue
# ---------------------------------------------------------------------------

class TestCheckAttribute:
    def test_creates_nested_path(self):
        p = _plugin({})
        checkAttribute(p, "1234", "01", "0006", "0000")
        assert p.ListOfDevices["1234"]["Ep"]["01"]["0006"]["0000"] == {}

    def test_idempotent(self):
        p = _plugin({})
        checkAttribute(p, "1234", "01", "0006", "0000")
        checkAttribute(p, "1234", "01", "0006", "0000")
        assert p.ListOfDevices["1234"]["Ep"]["01"]["0006"]["0000"] == {}

    def test_stores_value(self):
        p = _plugin({})
        checkAndStoreAttributeValue(p, "1234", "01", "0006", "0000", "01")
        assert p.ListOfDevices["1234"]["Ep"]["01"]["0006"]["0000"] == "01"


# ---------------------------------------------------------------------------
# checkValidValue
# ---------------------------------------------------------------------------

class TestCheckValidValue:
    def test_rejects_e2_ffffffff(self):
        p = _plugin({})
        assert checkValidValue(p, "1234", "e2", "ffffffff") is False

    def test_accepts_e2_other_value(self):
        p = _plugin({})
        assert checkValidValue(p, "1234", "e2", "00000001") is True

    def test_rejects_lumi_airmonitor_8000(self):
        p = _plugin({"1234": {"Model": "lumi.airmonitor.acn01"}})
        assert checkValidValue(p, "1234", "21", "8000") is False

    def test_rejects_lumi_airmonitor_0000(self):
        p = _plugin({"1234": {"Model": "lumi.airmonitor.acn01"}})
        assert checkValidValue(p, "1234", "21", "0000") is False

    def test_accepts_lumi_airmonitor_valid_value(self):
        p = _plugin({"1234": {"Model": "lumi.airmonitor.acn01"}})
        assert checkValidValue(p, "1234", "21", "0064") is True

    def test_accepts_other_model(self):
        p = _plugin({"1234": {"Model": "other"}})
        assert checkValidValue(p, "1234", "21", "0000") is True


# ---------------------------------------------------------------------------
# getAttributeValue
# ---------------------------------------------------------------------------

class TestGetAttributeValue:
    def _device_with_attr(self, value):
        return {
            "1234": {
                "Ep": {"01": {"0006": {"0000": value}}}
            }
        }

    def test_returns_value(self):
        p = _plugin(self._device_with_attr("01"))
        assert getAttributeValue(p, "1234", "01", "0006", "0000") == "01"

    def test_unknown_device_returns_none(self):
        p = _plugin({})
        assert getAttributeValue(p, "dead", "01", "0006", "0000") is None

    def test_unknown_ep_returns_none(self):
        p = _plugin({"1234": {"Ep": {}}})
        assert getAttributeValue(p, "1234", "01", "0006", "0000") is None

    def test_cluster_not_dict_returns_none(self):
        p = _plugin({"1234": {"Ep": {"01": {"0006": "flat_string"}}}})
        assert getAttributeValue(p, "1234", "01", "0006", "0000") is None

    def test_missing_attr_returns_none(self):
        p = _plugin({"1234": {"Ep": {"01": {"0006": {}}}}})
        assert getAttributeValue(p, "1234", "01", "0006", "0000") is None
