#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Time cluster (0x000a) server, as specified in ZCL revision 8, section 3.12.

The coordinator is the network's master clock. All attributes of one Read
Attributes request are answered from a single snapshot of the clock, so that
Time, TimeZone, the DST window and LocalTime are consistent with each other:

    StandardTime = Time + TimeZone                       (TimeZone excludes DST)
    LocalTime    = StandardTime + DstShift   if DstStart <= Time <= DstEnd
    LocalTime    = StandardTime              otherwise

DstStart and DstEnd are UTC instants counted from the Zigbee epoch
(2000-01-01 UTC). They describe the DST period in force, or the next one when
DST is not in force, so that a southern-hemisphere period crossing the new year
is reported whole. The DST rules come from the system's IANA time zone. When it
cannot be determined, the DST attributes are reported as invalid and TimeZone
carries the current full offset, so a device deriving its local time from
Time + TimeZone still gets it right.
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import is_ack_tobe_disabled
from Modules.zigateConsts import ZIGATE_EP

ZIGBEE_EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)
TUYA_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

INVALID_TIME = 0xFFFFFFFF           # ZCL non-value for UTC and uint32 time attributes
MAX_TIME = INVALID_TIME - 1
TIME_CLUSTER_REVISION = 0x0002      # ZCL r8 section 3.12.1.1

# TimeStatus bits, ZCL r8 Table 3-70. Synchronized is never set: "If the Master
# bit is 1, the value of this bit is 0."
TIME_STATUS_MASTER = 0x01
TIME_STATUS_MASTER_ZONE_DST = 0x04

# ZCL data types used by the Time cluster, and their size in bytes
DATA_TYPE_MAP8 = "18"
DATA_TYPE_UINT16 = "21"
DATA_TYPE_UINT32 = "23"
DATA_TYPE_INT32 = "2b"
DATA_TYPE_UTC = "e2"
DATA_TYPE_SIZE = {DATA_TYPE_MAP8: 1, DATA_TYPE_UINT16: 2, DATA_TYPE_UINT32: 4, DATA_TYPE_INT32: 4, DATA_TYPE_UTC: 4}

STATUS_SUCCESS = "00"
STATUS_UNSUPPORTED_ATTRIBUTE = "86"

# DST transitions are found with UTC probes, then bisected to the second. Time
# zone rules never change offset twice within 6 hours (same step as zigpy PR #1916).
DST_PROBE_STEP = timedelta(hours=6)

# Models whose LocalTime is local wall-clock seconds since 1970-01-01 instead of 2000-01-01
TUYA_EPOCH_MODELS = ("TS0601-thermostat",)


def get_local_timezone():
    """
    Return the system's IANA time zone as a ZoneInfo, or None when it cannot be determined.

    Looked up, in order, from the TZ environment variable, the /etc/localtime symlink
    and /etc/timezone. A POSIX TZ rule string (e.g. "CET-1CEST,M3.5.0,M10.5.0/3") is
    not an IANA name and is skipped.
    """
    candidates = [os.environ.get("TZ", "").lstrip(":")]

    try:
        parts = Path("/etc/localtime").resolve().parts
        if "zoneinfo" in parts:
            idx = len(parts) - 1 - parts[::-1].index("zoneinfo")
            candidates.append("/".join(parts[idx + 1:]))
    except (OSError, RuntimeError):
        pass

    try:
        candidates.append(Path("/etc/timezone").read_text(encoding="utf-8").strip())
    except (OSError, UnicodeDecodeError):
        pass

    for tz_name in candidates:
        if not tz_name:
            continue
        try:
            return ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError, OSError):
            continue

    return None


def resolve_time_zone(self, now_utc):
    """
    Return the IANA zone to report DST rules from, or None.

    The zone is only trusted when it agrees with the offset the system clock applies
    right now, so a stale /etc/timezone or a TZ rule string never yields DST values
    that contradict the local time.
    """
    zone = get_local_timezone()
    if zone is None:
        _log_once(self, "TimeServer_001", "No IANA time zone found (TZ, /etc/localtime, /etc/timezone), DST attributes reported as invalid")
        return None

    system_offset = now_utc.astimezone().utcoffset()
    zone_offset = now_utc.astimezone(zone).utcoffset()
    if system_offset != zone_offset:
        _log_once(
            self,
            "TimeServer_002",
            f"Time zone {zone.key} ({zone_offset}) disagrees with the system clock ({system_offset}), DST attributes reported as invalid",
        )
        return None

    return zone


def _log_once(self, error_code, description):
    """Log a time zone problem once per plugin instance instead of on every Time cluster read."""
    reported = self.__dict__.setdefault("_timeserver_reported", set())
    if error_code in reported:
        return
    reported.add(error_code)
    self.log.logging(["TimeServer", "Input"], "Log", f"TimeServer - {description}", context={"Error": error_code, "Description": description})


def zigbee_time(instant):
    """Seconds from the Zigbee epoch to instant, or INVALID_TIME when not representable."""
    seconds = int((instant - ZIGBEE_EPOCH).total_seconds())
    return seconds if 0 <= seconds <= MAX_TIME else INVALID_TIME


def _offsets(instant, zone):
    """(UTC offset, DST shift) in seconds that zone applies at the UTC instant."""
    local = instant.astimezone(zone)
    return (
        int((local.utcoffset() or timedelta(0)).total_seconds()),
        int((local.dst() or timedelta(0)).total_seconds()),
    )


def scan_offset_periods(zone, year):
    """
    Split year-1 .. year+1 into periods of constant (UTC offset, DST shift).

    Return a chronological list of (start, end, offset, shift), start inclusive and
    end exclusive, both timezone-aware UTC datetimes.
    """
    lower = datetime(year - 1, 1, 1, tzinfo=timezone.utc)
    upper = datetime(year + 2, 1, 1, tzinfo=timezone.utc)

    periods = []
    period_start = probe = lower
    current = _offsets(probe, zone)

    while probe < upper:
        following = min(probe + DST_PROBE_STEP, upper)
        following_offsets = _offsets(following, zone)
        if following_offsets != current:
            # Bisect on whole seconds: left keeps the old offsets, right has the new ones
            left, right = probe, following
            while (right - left) > timedelta(seconds=1):
                middle = left + timedelta(seconds=int((right - left).total_seconds()) // 2)
                if _offsets(middle, zone) == current:
                    left = middle
                else:
                    right = middle
            periods.append((period_start, right, current[0], current[1]))
            period_start = right
            current = following_offsets
        probe = following

    periods.append((period_start, upper, current[0], current[1]))
    return periods


def get_offset_periods(self, zone, year):
    """scan_offset_periods(), cached per plugin instance, zone and year."""
    # Each Domoticz plugin instance gets its own cache, which avoids shared state
    # when multiple instances run in the same process.
    instance_cache = self.__dict__.setdefault("_dst_cache", {})
    key = (zone.key, year)
    if key not in instance_cache:
        instance_cache.clear()
        instance_cache[key] = scan_offset_periods(zone, year)
    return instance_cache[key]


def select_dst_period(periods, now_utc, offset, shift):
    """
    Return the (start, end, shift) of the DST period in force at now_utc, or of the next one.

    Only periods sharing the current standard offset qualify, so a political change of
    standard time is not mistaken for DST. Return None when there is no such period, or
    when it touches the edge of the scanned range and its true bounds are unknown.
    """
    standard_offset = offset - shift
    for start, end, period_offset, period_shift in periods:
        if end <= now_utc or period_shift == 0 or period_offset - period_shift != standard_offset:
            continue
        if start == periods[0][0] or end == periods[-1][1]:
            return None
        return start, end, period_shift
    return None


def build_time_snapshot(self, now_utc, zone):
    """
    Compute every Time cluster value for the UTC instant now_utc.

    zone is the IANA zone from resolve_time_zone(), or None to only use the
    system's current offset.
    """
    if zone is None:
        offset = int((now_utc.astimezone().utcoffset() or timedelta(0)).total_seconds())
        shift = 0
        period = None
    else:
        offset, shift = _offsets(now_utc, zone)
        period = select_dst_period(get_offset_periods(self, zone, now_utc.year), now_utc, offset, shift)

    master_zone_dst = zone is not None and (period is not None or shift == 0)
    if master_zone_dst:
        # TimeZone is the standard offset, DST is applied through the DST attributes
        time_zone = offset - shift
    else:
        # DST window unknown: fold the current DST shift into TimeZone instead
        time_zone = offset

    if period is not None:
        start, end, dst_shift = period
        dst_start = zigbee_time(start)
        # ZCL tests DstStart <= Time <= DstEnd, DstEnd is the last second of DST
        dst_end = min(MAX_TIME, zigbee_time(end) - 1)
    else:
        dst_start = dst_end = INVALID_TIME
        dst_shift = 0

    utc_seconds = zigbee_time(now_utc)
    return {
        "time": utc_seconds,
        "time_status": TIME_STATUS_MASTER | (TIME_STATUS_MASTER_ZONE_DST if master_zone_dst else 0),
        "time_zone": time_zone,
        "dst_start": dst_start,
        "dst_end": dst_end,
        "dst_shift": dst_shift,
        "standard_time": zigbee_time(now_utc + timedelta(seconds=time_zone)),
        "local_time": zigbee_time(now_utc + timedelta(seconds=offset)),
        "tuya_local_time": int((now_utc - TUYA_EPOCH).total_seconds()) + offset,
    }


def time_attribute_value(self, nwkid, attribute, snapshot):
    """Return (status, data_type, value) answering attribute (big-endian hex string) from snapshot."""
    if attribute == "0000":  # Time
        return STATUS_SUCCESS, DATA_TYPE_UTC, snapshot["time"]

    if attribute == "0001":  # TimeStatus
        return STATUS_SUCCESS, DATA_TYPE_MAP8, snapshot["time_status"]

    if attribute == "0002":  # TimeZone
        return STATUS_SUCCESS, DATA_TYPE_INT32, snapshot["time_zone"]

    if attribute == "0003":  # DstStart
        return STATUS_SUCCESS, DATA_TYPE_UINT32, snapshot["dst_start"]

    if attribute == "0004":  # DstEnd
        return STATUS_SUCCESS, DATA_TYPE_UINT32, snapshot["dst_end"]

    if attribute == "0005":  # DstShift
        return STATUS_SUCCESS, DATA_TYPE_INT32, snapshot["dst_shift"]

    if attribute == "0006":  # StandardTime
        return STATUS_SUCCESS, DATA_TYPE_UINT32, snapshot["standard_time"]

    if attribute == "0007":  # LocalTime
        if self.ListOfDevices.get(nwkid, {}).get("Model") in TUYA_EPOCH_MODELS:
            self.log.logging(["TimeServer", "Input"], "Debug", "time_attribute_value - LocalTime uses EPOCH from 1970-01-01 instead of 2000-01-01", nwkid)
            return STATUS_SUCCESS, DATA_TYPE_UINT32, snapshot["tuya_local_time"]
        return STATUS_SUCCESS, DATA_TYPE_UINT32, snapshot["local_time"]

    if attribute == "fffd":  # ClusterRevision
        return STATUS_SUCCESS, DATA_TYPE_UINT16, TIME_CLUSTER_REVISION

    # LastSetTime, ValidUntilTime and anything else
    return STATUS_UNSUPPORTED_ATTRIBUTE, None, None


def encode_attribute_record(attribute, status, data_type, value):
    """One Read Attributes Response record: attribute id (LE), status, then type and value (LE) on success."""
    record = attribute[2:4] + attribute[:2] + status
    if status != STATUS_SUCCESS:
        return record
    size = DATA_TYPE_SIZE[data_type]
    return record + data_type + value.to_bytes(size, "little", signed=(data_type == DATA_TYPE_INT32)).hex()


def timeserver_multiple_read_attribute_request(self, Devices, nwkid, src_ep, dst_ep, sqn, cluster_id, manuf_specif, manuf_code, MsgData, nbAttribute):
    """ Handle a read request with one or more attributes on cluster 0x000a"""

    if sqn == self.ListOfDevices[nwkid].get("SQN_000a"):
        self.log.logging(["TimeServer","Input"], "Debug", f"Decode0100 - timeserver_multiple_read_attribute_request - duplicate request nwkid {nwkid} nbAttribute: {nbAttribute}", nwkid)
        return

    self.ListOfDevices[nwkid]["SQN_000a"] = sqn

    now_utc = datetime.now(timezone.utc)
    snapshot = build_time_snapshot(self, now_utc, resolve_time_zone(self, now_utc))
    self.log.logging(["TimeServer","Input"], "Debug", f"Decode0100 - timeserver_multiple_read_attribute_request - nwkid {nwkid} snapshot {snapshot}", nwkid)

    cluster_frame = "18"  # Profile-wide, Server to Client, Disable default Response
    cmd = "01"            # Read Attributes Response
    payload = cluster_frame + sqn + cmd

    for idx in range(0, len(MsgData), 4):
        attribute = MsgData[idx:idx + 4]
        status, data_type, value = time_attribute_value(self, nwkid, attribute, snapshot)
        self.log.logging(["TimeServer","Input"], "Debug", f"Decode0100 - timeserver_multiple_read_attribute_request - nwkid {nwkid} attribute {attribute} status {status} type {data_type} value {value}", nwkid)
        payload += encode_attribute_record(attribute, status, data_type, value)

    self.log.logging(["TimeServer","Input"], "Debug", f"Decode0100 - timeserver_multiple_read_attribute_request Response - nwkid {nwkid} ep: {src_ep} , clusterId: {cluster_id}, sqn: {sqn},payload: {payload}", nwkid)

    raw_APS_request( self, nwkid, src_ep, cluster_id, "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=is_ack_tobe_disabled(self, nwkid), )
