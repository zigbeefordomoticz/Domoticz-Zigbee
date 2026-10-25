#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the Time cluster (0x000a) server in Modules/timeServer.py, against
ZCL revision 8 section 3.12.

Coverage:
  - build_time_snapshot
      * Time, TimeZone (standard offset, DST excluded), StandardTime, LocalTime,
        DstStart / DstEnd / DstShift for LA, Sofia, Sydney and Auckland before,
        during and after DST. Reference values are those of zigpy PR #1806,
        DstEnd being one second earlier because ZCL tests DstStart <= Time <= DstEnd
      * DstStart / DstEnd use the Zigbee epoch (2000), to the second (regression:
        Unix epoch at local midnight of the following day)
      * southern hemisphere periods cross the new year (regression: Jan 1 .. Apr)
      * a zone without DST reports invalid DstStart / DstEnd and a zero DstShift
      * no IANA zone: DST invalid, TimeZone carries the full current offset,
        MasterZoneDst not claimed
      * for every instant sampled, Local Time computed with the ZCL formula equals
        the zone's wall clock, including the seconds around each transition
      * TimeStatus is Master | MasterZoneDst, never Master | Synchronized
  - TimeServerEpoch device configuration attribute
      * absent: ZCL r8 values; 1970_LOCALTIME: LocalTime is the wall clock since 1970
        (TS0601-thermostat, regression: the UTC offset was added twice); 1970_UTC and
        2000_LOCAL as zigbee-herdsman-converters' customTimeResponse(); the other
        attributes never change
      * read from the device's model configuration; an unknown value falls back to
        ZCL time and is logged once per model
  - resolve_time_zone / get_local_timezone
      * a zone disagreeing with the system clock is not trusted, logged once
      * TZ names with or without a leading ':'; a POSIX TZ rule string does not raise
  - DST periods are scanned once per year, not on every read
  - timeserver_multiple_read_attribute_request
      * full response payload, attribute by attribute
      * negative TimeZone encoded as two's complement (regression: struct.error,
        no answer at all in the Americas)
      * unsupported attributes answered with a status-only record (regression:
        TypeError, no answer for the whole request)
      * ClusterRevision answered
      * duplicate SQN is not answered twice
"""

import importlib
import sys
import time
import types
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

ZIGATE_EP = "01"
NWKID = "1234"
EP = "01"
ZIGBEE_EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)
INVALID = 0xFFFFFFFF


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


@pytest.fixture(scope="module")
def ts():
    """Import the real Modules.timeServer with its plugin dependencies stubbed out."""
    _raw_APS_request = MagicMock(name="raw_APS_request")
    stubs = {
        "Modules.sendZigateCommand": _make_stub("Modules.sendZigateCommand", raw_APS_request=_raw_APS_request),
        "Modules.tools": _make_stub(
            "Modules.tools",
            get_deviceconf_parameter_value=lambda self, model, attribute, return_default=None: self.DeviceConf.get(model, {}).get(attribute, return_default),
            is_ack_tobe_disabled=MagicMock(name="is_ack_tobe_disabled", return_value=False),
        ),
        "Modules.zigateConsts": _make_stub("Modules.zigateConsts", ZIGATE_EP=ZIGATE_EP),
    }

    saved = {name: sys.modules.get(name) for name in [*stubs, "Modules.timeServer"]}
    sys.modules.update(stubs)

    sys.modules.pop("Modules.timeServer", None)
    module = importlib.import_module("Modules.timeServer")
    module._mock_raw_APS_request = _raw_APS_request

    yield module

    for name, old in saved.items():
        if old is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old


@pytest.fixture(autouse=True)
def _reset_mocks(ts):
    ts._mock_raw_APS_request.reset_mock()


@pytest.fixture
def system_tz(monkeypatch):
    """Set the process time zone (what datetime.astimezone() uses) for one test."""
    def _set(tz_name):
        monkeypatch.setenv("TZ", tz_name)
        time.tzset()

    yield _set
    monkeypatch.undo()
    time.tzset()


def _plugin(model="SomeModel", epoch=None):
    p = MagicMock()
    p.log = MagicMock()
    p.log.logging = MagicMock()
    p.ListOfDevices = {NWKID: {"Model": model}}
    p.DeviceConf = {model: {"TimeServerEpoch": epoch}} if epoch else {}
    return p


def _utc(zigbee_seconds):
    return ZIGBEE_EPOCH + timedelta(seconds=zigbee_seconds)


def _zcl_local_time(snapshot):
    """Local Time as a ZCL client derives it, ZCL r8 section 3.12.2.2.4."""
    standard = snapshot["time"] + snapshot["time_zone"]
    if snapshot["dst_start"] <= snapshot["time"] <= snapshot["dst_end"]:
        return standard + snapshot["dst_shift"]
    return standard


def _wall_clock(now_utc, zone):
    """The zone's wall clock at now_utc, in seconds since 2000-01-01 local."""
    return int((now_utc.astimezone(zone).replace(tzinfo=None) - datetime(2000, 1, 1)).total_seconds())


# ── Snapshot values, reference data from zigpy PR #1806 ──────────────────────

# (zone, Time, TimeZone, StandardTime, LocalTime, DstStart, DST end transition, DstShift)
REFERENCE = [
    pytest.param("America/Los_Angeles", 790286400, -28800, 790257600, 790257600, 794829600, 815389200, 3600, id="la_jan_before_dst"),
    pytest.param("America/Los_Angeles", 798058800, -28800, 798030000, 798033600, 794829600, 815389200, 3600, id="la_apr_during_dst"),
    pytest.param("America/Los_Angeles", 805921200, -28800, 805892400, 805896000, 794829600, 815389200, 3600, id="la_jul_during_dst"),
    pytest.param("America/Los_Angeles", 816552000, -28800, 816523200, 816523200, 826279200, 846838800, 3600, id="la_nov_after_dst"),
    pytest.param("Europe/Sofia", 790250400, 7200, 790257600, 790257600, 796611600, 814755600, 3600, id="sofia_jan_before_dst"),
    pytest.param("Europe/Sofia", 798022800, 7200, 798030000, 798033600, 796611600, 814755600, 3600, id="sofia_apr_during_dst"),
    pytest.param("Europe/Sofia", 805885200, 7200, 805892400, 805896000, 796611600, 814755600, 3600, id="sofia_jul_during_dst"),
    pytest.param("Europe/Sofia", 816516000, 7200, 816523200, 816523200, 828061200, 846205200, 3600, id="sofia_nov_after_dst"),
    pytest.param("Australia/Sydney", 790218000, 36000, 790254000, 790257600, 781459200, 797184000, 3600, id="sydney_jan_during_dst"),
    pytest.param("Australia/Sydney", 797997600, 36000, 798033600, 798033600, 812908800, 828633600, 3600, id="sydney_apr_after_dst"),
    pytest.param("Australia/Sydney", 805860000, 36000, 805896000, 805896000, 812908800, 828633600, 3600, id="sydney_jul_before_dst"),
    pytest.param("Australia/Sydney", 816483600, 36000, 816519600, 816523200, 812908800, 828633600, 3600, id="sydney_nov_during_dst"),
    pytest.param("Pacific/Auckland", 790210800, 43200, 790254000, 790257600, 780847200, 797176800, 3600, id="auckland_jan_during_dst"),
    pytest.param("Pacific/Auckland", 797990400, 43200, 798033600, 798033600, 812296800, 828626400, 3600, id="auckland_apr_after_dst"),
    pytest.param("Pacific/Auckland", 805852800, 43200, 805896000, 805896000, 812296800, 828626400, 3600, id="auckland_jul_before_dst"),
    pytest.param("Pacific/Auckland", 816476400, 43200, 816519600, 816523200, 812296800, 828626400, 3600, id="auckland_nov_during_dst"),
]


@pytest.mark.parametrize("tz_name, utc_s, tz_std, standard, local, dst_start, dst_end_transition, dst_shift", REFERENCE)
def test_snapshot_matches_reference(ts, tz_name, utc_s, tz_std, standard, local, dst_start, dst_end_transition, dst_shift):
    snap = ts.build_time_snapshot(_plugin(), _utc(utc_s), ZoneInfo(tz_name))

    assert snap["time"] == utc_s
    assert snap["time_zone"] == tz_std
    assert snap["standard_time"] == standard
    assert snap["local_time"] == local
    assert snap["dst_start"] == dst_start
    assert snap["dst_end"] == dst_end_transition - 1
    assert snap["dst_shift"] == dst_shift
    assert snap["time_status"] == ts.TIME_STATUS_MASTER | ts.TIME_STATUS_MASTER_ZONE_DST


def test_paris_dst_window_is_zigbee_epoch_and_exact(ts):
    """Regression: Unix epoch, local midnight of the day after each change."""
    snap = ts.build_time_snapshot(_plugin(), datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc), ZoneInfo("Europe/Paris"))

    assert _utc(snap["dst_start"]) == datetime(2026, 3, 29, 1, 0, tzinfo=timezone.utc)
    assert _utc(snap["dst_end"] + 1) == datetime(2026, 10, 25, 1, 0, tzinfo=timezone.utc)
    assert snap["time_zone"] == 3600           # regression: 7200, DST counted twice
    assert snap["dst_shift"] == 3600


def test_paris_after_dst_reports_next_period(ts):
    snap = ts.build_time_snapshot(_plugin(), datetime(2026, 10, 25, 1, 0, tzinfo=timezone.utc), ZoneInfo("Europe/Paris"))

    assert _utc(snap["dst_start"]) == datetime(2027, 3, 28, 1, 0, tzinfo=timezone.utc)
    assert _utc(snap["dst_end"] + 1) == datetime(2027, 10, 31, 1, 0, tzinfo=timezone.utc)


def test_zone_without_dst(ts):
    snap = ts.build_time_snapshot(_plugin(), datetime(2026, 7, 15, 3, 0, tzinfo=timezone.utc), ZoneInfo("Asia/Tokyo"))

    assert snap["time_zone"] == 9 * 3600
    assert snap["dst_start"] == INVALID
    assert snap["dst_end"] == INVALID
    assert snap["dst_shift"] == 0
    assert snap["local_time"] == snap["time"] + 9 * 3600
    assert snap["time_status"] == ts.TIME_STATUS_MASTER | ts.TIME_STATUS_MASTER_ZONE_DST


def test_no_zone_folds_dst_into_time_zone(ts, system_tz):
    system_tz("Europe/Paris")
    snap = ts.build_time_snapshot(_plugin(), datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc), None)

    assert snap["time_zone"] == 7200
    assert snap["dst_start"] == INVALID
    assert snap["dst_end"] == INVALID
    assert snap["dst_shift"] == 0
    assert snap["time_status"] == ts.TIME_STATUS_MASTER
    assert _zcl_local_time(snap) == snap["local_time"]


@pytest.mark.parametrize("tz_name", ["Europe/Paris", "America/New_York", "Australia/Sydney", "Pacific/Auckland", "Australia/Lord_Howe", "Asia/Kolkata"])
def test_zcl_formula_gives_wall_clock(ts, tz_name):
    """A client applying ZCL r8 3.12.2.2.4 to our values gets the zone's wall clock, transitions included."""
    zone = ZoneInfo(tz_name)
    p = _plugin()
    year_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    instants = [year_start + timedelta(hours=h) for h in range(0, 365 * 24, 7)]
    for _start, end, _offset, _shift in ts.scan_offset_periods(zone, 2026)[:-1]:
        instants += [end - timedelta(seconds=1), end, end + timedelta(seconds=1)]

    for now in instants:
        snap = ts.build_time_snapshot(p, now, zone)
        assert _zcl_local_time(snap) == _wall_clock(now, zone), now
        assert snap["local_time"] == _wall_clock(now, zone), now
        assert snap["standard_time"] == snap["time"] + snap["time_zone"], now


def test_lord_howe_half_hour_shift(ts):
    snap = ts.build_time_snapshot(_plugin(), datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc), ZoneInfo("Australia/Lord_Howe"))

    assert snap["time_zone"] == 37800
    assert snap["dst_shift"] == 1800


def test_time_status_never_master_and_synchronized(ts):
    snap = ts.build_time_snapshot(_plugin(), datetime(2026, 7, 15, tzinfo=timezone.utc), ZoneInfo("Europe/Paris"))

    assert snap["time_status"] & 0x03 == 0x01


PARIS_SUMMER = datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc)   # 12:00 CEST
UNIX_NOW = int(PARIS_SUMMER.timestamp())
ZIGBEE_NOW = int((PARIS_SUMMER - ZIGBEE_EPOCH).total_seconds())


# (TimeServerEpoch, Time 0x0000, LocalTime 0x0007)
EPOCHS = [
    pytest.param(None, ZIGBEE_NOW, ZIGBEE_NOW + 7200, id="zcl"),
    pytest.param("1970_LOCALTIME", ZIGBEE_NOW, UNIX_NOW + 7200, id="1970_LOCALTIME"),
    pytest.param("1970_UTC", UNIX_NOW, UNIX_NOW + 7200, id="1970_UTC"),
    pytest.param("2000_LOCAL", ZIGBEE_NOW + 7200, ZIGBEE_NOW + 7200, id="2000_LOCAL"),
]


@pytest.mark.parametrize("epoch, time_value, local_time_value", EPOCHS)
def test_time_server_epoch(ts, epoch, time_value, local_time_value):
    snap = ts.build_time_snapshot(_plugin(), PARIS_SUMMER, ZoneInfo("Europe/Paris"))

    assert ts.time_attribute_value("0000", snap, epoch) == ("00", "e2", time_value)
    assert ts.time_attribute_value("0007", snap, epoch) == ("00", "23", local_time_value)
    for attribute in ("0001", "0002", "0003", "0004", "0005", "0006"):
        assert ts.time_attribute_value(attribute, snap, epoch) == ts.time_attribute_value(attribute, snap), attribute


def test_tuya_thermostat_local_time_is_wall_clock_since_1970(ts):
    """Regression: TS0601-thermostat got Unix time + 2 x UTC offset."""
    snap = ts.build_time_snapshot(_plugin(), PARIS_SUMMER, ZoneInfo("Europe/Paris"))

    assert ts.time_attribute_value("0007", snap, "1970_LOCALTIME")[2] == int(datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc).timestamp())


def test_device_time_epoch_from_model_configuration(ts):
    assert ts.device_time_epoch(_plugin(model="TS0601-thermostat", epoch="1970_LOCALTIME"), NWKID) == "1970_LOCALTIME"
    assert ts.device_time_epoch(_plugin(model="TRVZB"), NWKID) is None


def test_device_time_epoch_without_model(ts):
    p = _plugin()
    p.ListOfDevices = {NWKID: {}}

    assert ts.device_time_epoch(p, NWKID) is None


def test_device_time_epoch_unknown_value_logged_once_per_model(ts):
    p = _plugin(model="Thermo", epoch="1970")
    p.DeviceConf["Other"] = {"TimeServerEpoch": "local"}
    p.ListOfDevices["5678"] = {"Model": "Other"}

    assert ts.device_time_epoch(p, NWKID) is None
    assert ts.device_time_epoch(p, NWKID) is None
    assert ts.device_time_epoch(p, "5678") is None
    assert p.log.logging.call_count == 2


# ── Time zone resolution ─────────────────────────────────────────────────────

def test_resolve_time_zone_trusts_matching_zone(ts, system_tz, monkeypatch):
    system_tz("Europe/Paris")
    monkeypatch.setattr(ts, "get_local_timezone", lambda: ZoneInfo("Europe/Paris"))

    assert ts.resolve_time_zone(_plugin(), datetime(2026, 7, 15, tzinfo=timezone.utc)).key == "Europe/Paris"


def test_resolve_time_zone_rejects_zone_disagreeing_with_system_and_logs_once(ts, system_tz, monkeypatch):
    system_tz("Europe/Paris")
    monkeypatch.setattr(ts, "get_local_timezone", lambda: ZoneInfo("Asia/Tokyo"))
    p = _plugin()
    p.__dict__.pop("_timeserver_reported", None)

    assert ts.resolve_time_zone(p, datetime(2026, 7, 15, tzinfo=timezone.utc)) is None
    assert ts.resolve_time_zone(p, datetime(2026, 7, 15, tzinfo=timezone.utc)) is None
    assert p.log.logging.call_count == 1


def test_resolve_time_zone_none_when_unknown(ts, monkeypatch):
    monkeypatch.setattr(ts, "get_local_timezone", lambda: None)

    assert ts.resolve_time_zone(_plugin(), datetime(2026, 7, 15, tzinfo=timezone.utc)) is None


@pytest.mark.parametrize("tz_env", ["Europe/Paris", ":Europe/Paris"])
def test_get_local_timezone_from_tz_env(ts, monkeypatch, tz_env):
    monkeypatch.setenv("TZ", tz_env)

    assert ts.get_local_timezone().key == "Europe/Paris"


def test_get_local_timezone_skips_posix_rule_string(ts, monkeypatch):
    monkeypatch.setenv("TZ", "CET-1CEST,M3.5.0,M10.5.0/3")

    zone = ts.get_local_timezone()  # falls back to /etc/localtime, /etc/timezone or None
    assert zone is None or zone.key != "CET-1CEST,M3.5.0,M10.5.0/3"


def test_dst_periods_scanned_once_per_year(ts, monkeypatch):
    calls = []
    real_scan = ts.scan_offset_periods
    monkeypatch.setattr(ts, "scan_offset_periods", lambda zone, year: calls.append(year) or real_scan(zone, year))
    p = _plugin()
    p.__dict__.pop("_dst_cache", None)
    zone = ZoneInfo("Europe/Paris")

    for day in range(1, 30):
        ts.build_time_snapshot(p, datetime(2026, 7, day, tzinfo=timezone.utc), zone)
    ts.build_time_snapshot(p, datetime(2027, 1, 2, tzinfo=timezone.utc), zone)

    assert calls == [2026, 2027]


# ── Read Attributes Response ─────────────────────────────────────────────────

NEW_YORK_NOW = datetime(2026, 7, 15, 16, 0, tzinfo=timezone.utc)   # 12:00 EDT


def _fix_clock(ts, monkeypatch, now_utc, tz_name):
    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now_utc.astimezone(tz) if tz else now_utc.astimezone().replace(tzinfo=None)

    monkeypatch.setattr(ts, "datetime", _FixedDatetime)
    monkeypatch.setattr(ts, "resolve_time_zone", lambda self, now: ZoneInfo(tz_name))


@pytest.fixture
def new_york_clock(ts, monkeypatch):
    _fix_clock(ts, monkeypatch, NEW_YORK_NOW, "America/New_York")


def _le32(value):
    return value.to_bytes(4, "little", signed=value < 0).hex()


def _request(ts, p, attributes, sqn="05"):
    ts.timeserver_multiple_read_attribute_request(p, {}, NWKID, EP, ZIGATE_EP, sqn, "000a", "00", "0000", "".join(attributes), f"{len(attributes):02x}")


def test_full_response_payload(ts, new_york_clock):
    p = _plugin()
    time_s = int((NEW_YORK_NOW - ZIGBEE_EPOCH).total_seconds())
    dst_start = int((datetime(2026, 3, 8, 7, 0, tzinfo=timezone.utc) - ZIGBEE_EPOCH).total_seconds())
    dst_end = int((datetime(2026, 11, 1, 6, 0, tzinfo=timezone.utc) - ZIGBEE_EPOCH).total_seconds()) - 1

    _request(ts, p, ["0000", "0001", "0002", "0003", "0004", "0005", "0006", "0007", "0008", "0009", "fffd", "1234"])

    expected = (
        "18" + "05" + "01"
        + "0000" + "00" + "e2" + _le32(time_s)
        + "0100" + "00" + "18" + "05"
        + "0200" + "00" + "2b" + _le32(-18000)
        + "0300" + "00" + "23" + _le32(dst_start)
        + "0400" + "00" + "23" + _le32(dst_end)
        + "0500" + "00" + "2b" + _le32(3600)
        + "0600" + "00" + "23" + _le32(time_s - 18000)
        + "0700" + "00" + "23" + _le32(time_s - 14400)
        + "0800" + "86"
        + "0900" + "86"
        + "fdff" + "00" + "21" + "0200"
        + "3412" + "86"
    )
    ts._mock_raw_APS_request.assert_called_once()
    args, kwargs = ts._mock_raw_APS_request.call_args
    assert args[1:5] == (NWKID, EP, "000a", "0104")
    assert args[5] == expected
    assert kwargs["zigate_ep"] == ZIGATE_EP


def test_negative_time_zone_is_twos_complement(ts, new_york_clock):
    """Regression: struct.error on '-0004650', the device got no answer at all."""
    _request(ts, _plugin(), ["0002"])

    assert ts._mock_raw_APS_request.call_args[0][5] == "180501" + "0200" + "00" + "2b" + "b0b9ffff"


def test_unsupported_attribute_does_not_drop_the_response(ts, new_york_clock):
    """Regression: TypeError on data_type None, no answer for the whole request."""
    _request(ts, _plugin(), ["0000", "0008"])

    payload = ts._mock_raw_APS_request.call_args[0][5]
    assert payload.startswith("180501" + "0000" + "00" + "e2")
    assert payload.endswith("0800" + "86")


def test_duplicate_sqn_not_answered_twice(ts, new_york_clock):
    p = _plugin()
    _request(ts, p, ["0000"], sqn="07")
    _request(ts, p, ["0000"], sqn="07")

    assert ts._mock_raw_APS_request.call_count == 1


def test_time_server_epoch_in_response(ts, new_york_clock):
    _request(ts, _plugin(model="TRVZB", epoch="1970_UTC"), ["0000", "0007"])

    unix_now = int(NEW_YORK_NOW.timestamp())
    assert ts._mock_raw_APS_request.call_args[0][5] == (
        "180501" + "0000" + "00" + "e2" + _le32(unix_now) + "0700" + "00" + "23" + _le32(unix_now - 14400)
    )


def test_invalid_dst_window_encoded_as_non_value(ts, monkeypatch):
    """Zone without DST: DstStart / DstEnd are the uint32 non-value, DstShift 0."""
    _fix_clock(ts, monkeypatch, datetime(2026, 7, 15, 3, 0, tzinfo=timezone.utc), "Asia/Tokyo")

    _request(ts, _plugin(), ["0003", "0004", "0005"])

    assert ts._mock_raw_APS_request.call_args[0][5] == (
        "180501" + "0300" + "00" + "23" + "ffffffff" + "0400" + "00" + "23" + "ffffffff" + "0500" + "00" + "2b" + "00000000"
    )


def test_dst_period_cut_by_scan_range_is_not_reported(ts):
    """A DST period running past the scanned years has unknown bounds: report none rather than a wrong one."""
    utc = timezone.utc
    periods = [
        (datetime(2025, 1, 1, tzinfo=utc), datetime(2026, 3, 29, 1, tzinfo=utc), 3600, 0),
        (datetime(2026, 3, 29, 1, tzinfo=utc), datetime(2028, 1, 1, tzinfo=utc), 7200, 3600),
    ]

    assert ts.select_dst_period(periods, datetime(2026, 7, 15, tzinfo=utc), 7200, 3600) is None


def test_dst_period_ignores_standard_time_change(ts):
    """A period under another standard offset is a change of standard time, not this zone's DST."""
    utc = timezone.utc
    periods = [
        (datetime(2025, 1, 1, tzinfo=utc), datetime(2026, 9, 1, tzinfo=utc), 7200, 0),      # standard UTC+2 now
        (datetime(2026, 9, 1, tzinfo=utc), datetime(2026, 11, 1, tzinfo=utc), 7200, 3600),  # UTC+1 rules with DST
        (datetime(2026, 11, 1, tzinfo=utc), datetime(2028, 1, 1, tzinfo=utc), 3600, 0),
    ]

    assert ts.select_dst_period(periods, datetime(2026, 7, 15, tzinfo=utc), 7200, 0) is None
