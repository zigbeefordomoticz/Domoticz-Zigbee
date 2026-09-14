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
Sonoff Zigbee Device Control for Domoticz

This module provides specialized support for Sonoff Zigbee devices within the
Domoticz Zigbee plugin. It includes functions for configuring and interacting
with various Sonoff device models, such as smart thermostatic radiator valves
(TRVs), temperature and humidity sensors (e.g., SNZB-02LD), smart valves (e.g., SWV),
and inching controllers (e.g., ZBMicro).

The module enables:
- Setting child lock and window detection modes on TRVs
- Configuring temperature and humidity thresholds
- Handling real-time irrigation parameters (duration, volume)
- Auto-shutdown of valves on water shortage
- SWV-ZFE/ZFU manual irrigation session defaults, valve alarms and flow unit
- Decoding the SWV-ZFE/ZFU manual default settings (0x501d), valve alarm settings (0x5020) and irrigation
  schedule status (0x501f) reports
- Adjusting radio power modes (e.g., Turbo Mode)
- Setting temperature unit (Celsius/Fahrenheit)
- Performing temperature calibration

Functions log debug and error messages using the plugin’s logging mechanism,
and write Zigbee attributes using the `write_attribute` utility.

Constants for manufacturer IDs, cluster IDs, and attribute IDs are defined
for internal use, following the Zigbee specification and Sonoff extensions.

Authors:
    zaraki673, pipiche38 (2015–2024)

License:
    GNU General Public License v3.0 (SPDX: GPL-3.0)

Repository:
    https://github.com/zigbeefordomoticz/Domoticz-Zigbee
"""


import time
from datetime import datetime, timedelta

from Modules.basicOutputs import write_attribute
from Modules.tools import get_device_config_param
from Modules.zigateConsts import ZIGATE_EP

SONOFF_MAUFACTURER_NAME = "SONOFF"
SONOFF_MANUFACTURER_ID = "1286"
SONOFF_CLUSTER_ID = "fc11"
SONOFF_ILLUMINATION_ATTRIBUTE = "2001"
SONOFF_MAX_TEMP = "0003"
SONOFF_MIN_TEMP = "0004"
SONOFF_MAX_HUMI = "0005"
SONOFF_MIN_HUMI = "0006"

# Sonoff Smart Valve - SWV model
SONOFF_REALTIME_IRRIGATION_DURATION = "5006"
SONOFF_REALTIME_IRRIGATION_VOLUME = "5007"
SONOFF_VALVE_ABNORMAL_STATE = "500c"
SONOFF_IRRIGATIM_START_TIME = "500d"
SONOFF_IRRIGATION_END_TIME = "500e"
SONOFF_DAILY_IRRIGATION_VOLUME = "500F"
SONOFF_VALVE_WORK_STATE = "5010"
SONOFF_WATER_CLOSE_VALVE_TIMEOUT_ATTRIBUTE = "5011"

# Sonoff Smart Valve - SWV-ZFE / SWV-ZFU models (fc11 private attributes, see
# zigbee-herdsman-converters src/devices/sonoff.ts "SWV-ZFE")
SONOFF_SWV_MANUAL_DEFAULT_SETTINGS_ATTRIBUTE = "501d"   # ARRAY(uint8)[12]
SONOFF_SWV_VALVE_ALARM_SETTINGS_ATTRIBUTE = "5020"      # ARRAY(uint8)[4]
SONOFF_SWV_UNIT_OF_WATER_FLOW_ATTRIBUTE = "5021"        # uint8
SONOFF_SWV_IRRIGATION_SCHEDULE_STATUS_ATTRIBUTE = "501f"  # ARRAY(uint8)[15] (start/standby) or [21] (running/end)
ZCL_ARRAY_DATA_TYPE = "48"
ZCL_UINT8_DATA_TYPE = "20"

SONOFF_SWV_MAX_IRRIGATION_MINUTES = 719
SONOFF_SWV_IRRIGATION_MODE = {"duration": 0x00, "capacity": 0x01}
# 0x501d amount unit byte (legacy mapping, valid on every firmware): 0 = US gallon, 1 = liter
SONOFF_SWV_AMOUNT_UNIT = {"us_gallon": 0x00, "liter": 0x01}
# 0x5021 unit of water flow (firmware >= 1.1.0): 0 = liter, 1 = US gallon, 2 = imperial gallon
SONOFF_SWV_WATER_FLOW_UNIT = {"liter": 0x00, "us_gallon": 0x01, "imperial_gallon": 0x02}

# 0x501f irrigation schedule status report (Sonoff documentation, mirrored by
# zigbee-herdsman-converters irrigationScheduleStatus)
SONOFF_SWV_SCHEDULE_STATUS = {0x00: "start", 0x01: "end", 0x02: "running", 0x03: "standby"}
SONOFF_SWV_SCHEDULE_TYPE = {0x00: "automatic", 0x01: "manual"}
SONOFF_SWV_IRRIGATION_MODE_NAME = {0x00: "duration", 0x01: "capacity", 0x02: "duration_with_interval"}
# 0x501d/0x501f amount unit byte: 0 = US gallon, 1 = liter, 2 = imperial gallon (firmware >= 1.1.0)
SONOFF_SWV_AMOUNT_UNIT_NAME = {0x00: "us_gallon", 0x01: "liter", 0x02: "imperial_gallon"}
SONOFF_SWV_SCHEDULE_STATUS_START_STANDBY_LEN = 15
# The irrigation status is logged and pushed to the TextStatus widget on every status change (a Domoticz
# On/Off produces start->running and end->standby transitions, so those are always reported), and otherwise
# at most every SONOFF_SWV_STATUS_REPORT_INTERVAL seconds (Param, default 5 min; the valve reports every ~6 s
# while running).
SONOFF_SWV_STATUS_REPORT_DEFAULT_SECONDS = 300
_swv_status_last_report = {}   # nwkid -> (schedule_status, timestamp)
# Water flow (L/min) derived from the running 0x501f reports: volume delta between two samples at least
# SONOFF_SWV_FLOW_RATE_INTERVAL seconds apart (Param, default 60 s). The reported amount has a 1 unit resolution,
# so a longer window is more accurate but slower to react. Handed to the Flow widget under "flow_l_min" once per
# window and as 0 when the session ends; the session average is given in the "end" status text.
SONOFF_SWV_FLOW_RATE_DEFAULT_SECONDS = 60
SONOFF_SWV_LITERS_PER_UNIT = {"liter": 1.0, "us_gallon": 3.785411784, "imperial_gallon": 4.54609}
_swv_flow_window = {}   # nwkid -> (sample time (unix s), liters, last flow L/min or None)
# Daily irrigation volume (liters, local date) computed from the 0x501f reports: the sessions ended today plus the
# running one. The valve's own fc11/0x500f DailyIrrigationVolume was seen not to move for hours, so it is not used.
# Kept in memory: a plugin restart starts the day again at the running session.
_swv_daily_volume = {}   # nwkid -> {"date": ISO date, "ended": liters, "running": liters}
# WaterCounter (Domoticz incremental counter) increments computed from the 0x501f reports: the volume delta since
# the previous report of the same session. fc11/0x5007 RealtimeIrrigationVolume is a per-session total (and a read
# re-reports it), so pushing it to an incremental counter adds the whole session again on every report/read.
_swv_water_counter = {}   # nwkid -> (session start_time, liters already counted for that session)
SONOFF_SWV_SCHEDULE_STATUS_RUNNING_END_LEN = 21
SONOFF_SWV_MANUAL_DEFAULT_SETTINGS_LEN = 12
SONOFF_SWV_VALVE_ALARM_SETTINGS_LEN = 4
# The valve stamps its schedule with the Time cluster LocalTime (0x000a/0x0007) the plugin
# serves: local wall-clock seconds since 2000-01-01, not UTC.
ZIGBEE_EPOCH_LOCAL = datetime(2000, 1, 1)

# Sonoff InchingController - ZBMicro model
SONOFF_RADIO_POWER_TURBO_MODE = "0012"

# Sonoff SNZB-02LD - Temperature Sensor
SONOFF_CALIBRATION_ATTRIBUTE = "2003"
SONOFF_TEMPERATURE_UNIT_ATTRIBUTE = "0007"

def is_sonoff_device(self, nwkid):
    return self.ListOfDevices[nwkid]["Manufacturer"] == SONOFF_MANUFACTURER_ID or self.ListOfDevices[nwkid]["Manufacturer Name"] == SONOFF_MAUFACTURER_NAME


def sonoff_child_lock(self, nwkid, lock_mode):
    self.log.logging("Sonoff", "Debug", "sonoff_child_lock - Nwkid: %s Mode: %s" % (nwkid, lock_mode), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", "0000", "10", "%02x" %lock_mode, ackIsDisabled=False)


def sonoff_open_window_detection(self, nwkid, detection):
    self.log.logging("Sonoff", "Debug", "sonoff_child_lock - Nwkid: %s Mode: %s" %(nwkid, detection), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", "6000", "10", "%02x" %detection, ackIsDisabled=False)


def sonoff_temp_humi_ranges(self, nwkid, value):
    self.log.logging("Sonoff", "Debug", "sonoff_temp_humi_ranges - Nwkid: %s Mode: %s" %(nwkid, value), nwkid)
    temp_max = get_device_config_param(self, nwkid, "SONOFF_TEMP_MAX")
    temp_min = get_device_config_param(self, nwkid, "SONOFF_TEMP_MIN")
    humi_max = get_device_config_param(self, nwkid, "SONOFF_HUMI_MAX")
    humi_min = get_device_config_param(self, nwkid, "SONOFF_HUMI_MIN")

    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_MAX_TEMP, "29", "%04x" %temp_max, ackIsDisabled=False)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_MIN_TEMP, "29", "%04x" %temp_min, ackIsDisabled=False)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_MAX_HUMI, "21", "%04x" %humi_max, ackIsDisabled=False)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_MIN_HUMI, "21", "%04x" %humi_min, ackIsDisabled=False)


def sonoff_realtime_irrigation_duration(self, nwkid, value):
    """ Real-time Irrigation duration """
    self.log.logging("Sonoff", "Debug", "sonoff_realtime_irrigation_duration - Nwkid: %s value: %s" % (nwkid, value), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "00", SONOFF_REALTIME_IRRIGATION_DURATION, "23", "%08x" %value, ackIsDisabled=False)


def sonoff_realtime_irrigation_volume(self, nwkid, value):
    """ Real-time Irrigation volume """
    self.log.logging("Sonoff", "Debug", "sonoff_realtime_irrigation_duration - Nwkid: %s value: %s" % (nwkid, value), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "00", SONOFF_REALTIME_IRRIGATION_VOLUME, "23", "%08x" %value, ackIsDisabled=False)


def sonoff_realtime_irrigation_daily_volume(self, nwkid, value):
    """ Daily irigation volume """
    self.log.logging("Sonoff", "Debug", "sonoff_realtime_irrigation_duration - Nwkid: %s value: %s" % (nwkid, value), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "00", SONOFF_DAILY_IRRIGATION_VOLUME, "23", "%08x" %value, ackIsDisabled=False)


def auto_close_when_water_shortage(self, nwkid, value):
    """ Automatically shut down the water valve after the water shortage exceeds 30 minutes. """

    self.log.logging("Sonoff", "Debug", "auto_close_when_water_shortage - Nwkid: %s value: %s" % (nwkid, value), nwkid)
    water_close_valve_timeout = "%04x" % value
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "00", SONOFF_WATER_CLOSE_VALVE_TIMEOUT_ATTRIBUTE, "21", water_close_valve_timeout, ackIsDisabled=False)


def _zcl_uint8_array(elements):
    """ Encode a ZCL ARRAY (0x48) of uint8 as hex: element type, count (uint16 LE), elements """
    return ZCL_UINT8_DATA_TYPE + len(elements).to_bytes(2, "little").hex() + bytes(elements).hex()


def _param_int(self, nwkid, param, default, minimum, maximum):
    value = get_device_config_param(self, nwkid, param)
    if value is None:
        return default
    try:
        value = int(value)
    except (TypeError, ValueError):
        self.log.logging("Sonoff", "Error", "%s invalid value %s, expected an integer" % (param, value), nwkid)
        return default
    return max(minimum, min(value, maximum))


def _param_choice(self, nwkid, param, choices, default):
    value = get_device_config_param(self, nwkid, param)
    if value is None:
        return default
    if value not in choices:
        self.log.logging("Sonoff", "Error", "%s invalid value %s, expected one of %s" % (param, value, sorted(choices)), nwkid)
        return default
    return choices[value]


def sonoff_swv_manual_default_settings(self, nwkid, value):
    """ SWV-ZFE/ZFU: settings applied to a manual 'On' (single irrigation session).

    The valve always closes by itself at the end of the session; the factory default is 2 minutes.
    All SONOFF_SWV_MANUAL_* params are folded into the single 0x501d array, so any of them triggers a full write.
    Layout (big endian): mode, total duration, irrigation duration, interval, amount unit, amount, fail-safe timeout.
    """
    self.log.logging("Sonoff", "Debug", "sonoff_swv_manual_default_settings - Nwkid: %s value: %s" % (nwkid, value), nwkid)

    duration = _param_int(self, nwkid, "SONOFF_SWV_MANUAL_IRRIGATION_DURATION", 2, 1, SONOFF_SWV_MAX_IRRIGATION_MINUTES)
    mode = _param_choice(self, nwkid, "SONOFF_SWV_MANUAL_IRRIGATION_MODE", SONOFF_SWV_IRRIGATION_MODE, SONOFF_SWV_IRRIGATION_MODE["duration"])
    amount_unit = _param_choice(self, nwkid, "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT_UNIT", SONOFF_SWV_AMOUNT_UNIT, SONOFF_SWV_AMOUNT_UNIT["liter"])
    amount = _param_int(self, nwkid, "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT", 0, 0, 10000)
    # Safety timeout mostly matters in capacity mode; default it to the duration so a session can never run longer than requested
    fail_safe = _param_int(self, nwkid, "SONOFF_SWV_MANUAL_FAIL_SAFE", duration, 0, SONOFF_SWV_MAX_IRRIGATION_MINUTES)
    interval = 10  # fixed upstream

    elements = (
        [mode]
        + list(duration.to_bytes(2, "big"))
        + list(duration.to_bytes(2, "big"))
        + list(interval.to_bytes(2, "big"))
        + [amount_unit]
        + list(amount.to_bytes(2, "big"))
        + list(fail_safe.to_bytes(2, "big"))
    )
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_SWV_MANUAL_DEFAULT_SETTINGS_ATTRIBUTE, ZCL_ARRAY_DATA_TYPE, _zcl_uint8_array(elements), ackIsDisabled=False)


def sonoff_swv_valve_alarm_settings(self, nwkid, value):
    """ SWV-ZFE/ZFU: water shortage / leak alarms and auto-close on shortage (0x5020).

    All SONOFF_SWV_ALARM_* params are folded into the single 0x5020 array, so any of them triggers a full write.
    """
    self.log.logging("Sonoff", "Debug", "sonoff_swv_valve_alarm_settings - Nwkid: %s value: %s" % (nwkid, value), nwkid)

    enable_bits = 0
    if _param_int(self, nwkid, "SONOFF_SWV_ALARM_WATER_SHORTAGE", 0, 0, 1):
        enable_bits |= 0b00001
    if _param_int(self, nwkid, "SONOFF_SWV_ALARM_WATER_LEAK", 0, 0, 1):
        enable_bits |= 0b00010
    if _param_int(self, nwkid, "SONOFF_SWV_WATER_SHORTAGE_AUTO_CLOSE", 0, 0, 1):
        enable_bits |= 0b01000
    shortage_duration = _param_int(self, nwkid, "SONOFF_SWV_ALARM_WATER_SHORTAGE_DURATION", 5, 1, 10)
    leak_duration = _param_int(self, nwkid, "SONOFF_SWV_ALARM_WATER_LEAK_DURATION", 1, 1, 3)

    elements = [enable_bits, shortage_duration, leak_duration, 0x00]
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_SWV_VALVE_ALARM_SETTINGS_ATTRIBUTE, ZCL_ARRAY_DATA_TYPE, _zcl_uint8_array(elements), ackIsDisabled=False)


def sonoff_swv_water_flow_unit(self, nwkid, unit):
    """ SWV-ZFE/ZFU: unit used by the flow-meter attributes (0x5021, firmware >= 1.1.0) """
    if unit not in SONOFF_SWV_WATER_FLOW_UNIT:
        self.log.logging("Sonoff", "Error", "SONOFF_SWV_WATER_FLOW_UNIT invalid value %s, expected one of %s" % (unit, sorted(SONOFF_SWV_WATER_FLOW_UNIT)), nwkid)
        return
    self.log.logging("Sonoff", "Debug", "sonoff_swv_water_flow_unit - Nwkid: %s unit: %s" % (nwkid, unit), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_SWV_UNIT_OF_WATER_FLOW_ATTRIBUTE, ZCL_UINT8_DATA_TYPE, "%02x" % SONOFF_SWV_WATER_FLOW_UNIT[unit], ackIsDisabled=False)


def _swv_local_time_to_iso(seconds):
    """ 0x501f timestamp (local seconds since 2000-01-01) -> ISO 8601 with the plugin's local offset """
    if seconds == 0:
        return None
    return (ZIGBEE_EPOCH_LOCAL + timedelta(seconds=seconds)).astimezone().isoformat(timespec="seconds")


def _swv_array_elements(value, element_counts):
    """ Strip whatever ZCL ARRAY(uint8) framing is left in front of the elements.

    The generic ARRAY decoder (Zigbee/zclDecoders.py extract_value_size) skips the element type
    and the low count byte only, so the elements normally arrive prefixed by the high count
    byte (0x00). Also accept a complete array (0x20 + LE count + elements) and bare elements.
    element_counts lists the element counts this attribute is known to carry.
    """
    data = bytes.fromhex(value)
    if len(data) >= 3 and data[0] == 0x20 and len(data) == 3 + int.from_bytes(data[1:3], "little"):
        return data[3:]
    if data and data[0] == 0x00 and len(data) - 1 >= min(element_counts):
        # high count byte left by the legacy decoder; whatever follows the elements (the next attribute of
        # the same frame, swallowed by that decoder) is ignored by the callers, which read fixed offsets
        return data[1:]
    return data


def sonoff_swv_decode_manual_default_settings(self, nwkid, ep, cluster, attribut, value):
    """ SWV-ZFE/ZFU: decode the 0x501d manual default settings array (EvalFunc).

      [0] mode  [1..2] total duration (min)  [3..4] irrigation duration (min)  [5..6] interval (min)
      [7] amount unit  [8..9] amount  [10..11] fail-safe timeout (min)
    Big endian. The valve reads back with [3..4] zeroed, so like upstream fall back to the
    total duration when the irrigation duration is 0.
    """
    self.log.logging("Sonoff", "Debug", "sonoff_swv_decode_manual_default_settings - Nwkid: %s value: %s" % (nwkid, value), nwkid)
    try:
        data = _swv_array_elements(value, (SONOFF_SWV_MANUAL_DEFAULT_SETTINGS_LEN,))
    except (ValueError, TypeError):
        self.log.logging("Sonoff", "Error", "sonoff_swv_decode_manual_default_settings - invalid 0x501d payload %s" % value, nwkid)
        return None

    if len(data) < SONOFF_SWV_MANUAL_DEFAULT_SETTINGS_LEN:
        self.log.logging("Sonoff", "Error", "sonoff_swv_decode_manual_default_settings - 0x501d payload has %s bytes, expected %s: %s" % (
            len(data), SONOFF_SWV_MANUAL_DEFAULT_SETTINGS_LEN, value), nwkid)
        return None

    total_duration = int.from_bytes(data[1:3], "big")
    irrigation_duration = int.from_bytes(data[3:5], "big")
    result = {
        "irrigation_mode": SONOFF_SWV_IRRIGATION_MODE_NAME.get(data[0], data[0]),
        "irrigation_duration": irrigation_duration or total_duration,
        "irrigation_amount_unit": SONOFF_SWV_AMOUNT_UNIT_NAME.get(data[7], data[7]),
        "irrigation_amount": int.from_bytes(data[8:10], "big"),
        "fail_safe": int.from_bytes(data[10:12], "big"),
    }
    self.log.logging("Sonoff", "Debug", "sonoff_swv_decode_manual_default_settings - Nwkid: %s decoded: %s" % (nwkid, result), nwkid)
    return result


def sonoff_swv_decode_valve_alarm_settings(self, nwkid, ep, cluster, attribut, value):
    """ SWV-ZFE/ZFU: decode the 0x5020 valve alarm settings array (EvalFunc).

      [0] enable bits (bit0 water shortage alarm, bit1 water leak alarm, bit3 auto-close on shortage, as
          written by zigbee-herdsman-converters; the raw byte is kept as the firmware sets bits it does not
          document), [1] shortage alarm duration (min), [2] leak alarm duration (min), [3] reserved
    """
    self.log.logging("Sonoff", "Debug", "sonoff_swv_decode_valve_alarm_settings - Nwkid: %s value: %s" % (nwkid, value), nwkid)
    try:
        data = _swv_array_elements(value, (SONOFF_SWV_VALVE_ALARM_SETTINGS_LEN,))
    except (ValueError, TypeError):
        self.log.logging("Sonoff", "Error", "sonoff_swv_decode_valve_alarm_settings - invalid 0x5020 payload %s" % value, nwkid)
        return None
    if len(data) < SONOFF_SWV_VALVE_ALARM_SETTINGS_LEN:
        self.log.logging("Sonoff", "Error", "sonoff_swv_decode_valve_alarm_settings - 0x5020 payload has %s bytes, expected %s: %s" % (
            len(data), SONOFF_SWV_VALVE_ALARM_SETTINGS_LEN, value), nwkid)
        return None

    result = {
        "enable_bits": data[0],
        "enable_alarm_water_shortage": bool(data[0] & 0x01),
        "enable_alarm_water_leak": bool(data[0] & 0x02),
        "enable_water_shortage_auto_close": bool(data[0] & 0x08),
        "alarm_water_shortage_duration": data[1],
        "alarm_water_leak_duration": data[2],
    }
    self.log.logging("Sonoff", "Debug", "sonoff_swv_decode_valve_alarm_settings - Nwkid: %s decoded: %s" % (nwkid, result), nwkid)
    return result


def _swv_hhmm(iso, now=None):
    """ 'HH:MM' from an ISO timestamp, prefixed with the date when it is not today; '' for None """
    if not iso:
        return ""
    stamp = datetime.fromisoformat(iso)
    now = now or datetime.now(stamp.tzinfo)
    return stamp.strftime("%H:%M") if stamp.date() == now.date() else stamp.strftime("%a %d/%m %H:%M")


def _swv_minutes_between(start_iso, end_iso):
    if not start_iso or not end_iso:
        return None
    return int(round((datetime.fromisoformat(end_iso) - datetime.fromisoformat(start_iso)).total_seconds() / 60))


def _swv_iso_to_unix(iso):
    return datetime.fromisoformat(iso).timestamp() if iso else None


def _swv_liters(status):
    return status["actual_irrigation_amount"] * SONOFF_SWV_LITERS_PER_UNIT.get(status["irrigation_amount_unit"], 1.0)


def _swv_session_average_flow(status):
    """ L/min over the whole session of an end report; None when the timestamps do not allow it """
    start, end = _swv_iso_to_unix(status["start_time"]), _swv_iso_to_unix(status["actual_end_time"])
    if start is None or end is None or end <= start:
        return None
    return round(_swv_liters(status) * 60 / (end - start), 1)


def _swv_flow_rate(self, nwkid, status):
    """ Flow in L/min for the Flow widget: the volume delta over the last SONOFF_SWV_FLOW_RATE_INTERVAL seconds
    of a running session (None while the window is still open), 0 whenever the valve is not running.

    While running, actual_end_time is the time the reported amount was measured at, so the rate is computed
    on the valve's own clock and does not depend on when the report reached the plugin.
    """
    if status["schedule_status"] != "running":
        _swv_flow_window.pop(nwkid, None)
        return 0
    now, liters = _swv_iso_to_unix(status["actual_end_time"]), _swv_liters(status)
    if now is None:
        return None
    since, since_liters, _ = _swv_flow_window.get(nwkid, (None, None, None))
    if since is None or now < since or liters < since_liters:
        # first sample of the window (or a new session seen without its start report): open a window
        _swv_flow_window[nwkid] = (now, liters, None)
        return None
    interval = _param_int(self, nwkid, "SONOFF_SWV_FLOW_RATE_INTERVAL", SONOFF_SWV_FLOW_RATE_DEFAULT_SECONDS, 10, 3600)
    if now - since < interval:
        return None
    flow = round((liters - since_liters) * 60 / (now - since), 1)
    _swv_flow_window[nwkid] = (now, liters, flow)
    return flow


def _swv_today():
    return datetime.now().astimezone().date().isoformat()


def _swv_daily_volume_liters(self, nwkid, status):
    """ Liters irrigated today for the WaterVolume widget: ended sessions since local midnight + the running one.

    Running/end reports are dated by the valve's actual_end_time; the day of an idle report is the plugin's,
    so the widget drops to 0 on the first report of a new day. A session crossing midnight is counted on
    the day it ends.
    """
    kind = status["schedule_status"]
    with_actuals = kind in ("running", "end") and status["actual_end_time"]
    day = datetime.fromisoformat(status["actual_end_time"]).astimezone().date().isoformat() if with_actuals else _swv_today()
    daily = _swv_daily_volume.get(nwkid)
    if daily is None or daily["date"] != day:
        daily = _swv_daily_volume[nwkid] = {"date": day, "ended": 0.0, "running": 0.0}
    if kind == "running" and with_actuals:
        daily["running"] = _swv_liters(status)
    elif kind == "end" and with_actuals:
        daily["ended"] += _swv_liters(status)
        daily["running"] = 0.0
    elif kind == "start":
        daily["running"] = 0.0
    return round(daily["ended"] + daily["running"], 1)


def _swv_water_counter_increment(self, nwkid, status):
    """ Liters to add to the WaterCounter: the volume delta since the previous running/end report of the same
    session (identified by start_time); None when there is nothing to add """
    if status["schedule_status"] not in ("running", "end") or not status["actual_end_time"]:
        return None
    session, counted = _swv_water_counter.get(nwkid, (None, 0.0))
    liters = _swv_liters(status)
    if session != status["start_time"]:
        counted = 0.0
    _swv_water_counter[nwkid] = (status["start_time"], max(liters, counted))
    increment = round(liters - counted, 1)
    return increment if increment > 0 else None


def _swv_schedule_status_text(status, flow=None):
    """ One-line, human readable summary of a decoded 0x501f record (log line and TextStatus widget);
    flow is the last measured L/min of a running session, when known """
    kind = "%s%s" % (status["schedule_type"], "" if status["schedule_type"] == "manual" else " plan %s" % status["schedule_index"])
    mode = str(status["irrigation_mode"]).replace("_", " ")
    unit = {"liter": "L", "us_gallon": "gal", "imperial_gallon": "imp gal"}.get(status["irrigation_amount_unit"], str(status["irrigation_amount_unit"]))
    start, expected_end = _swv_hhmm(status["start_time"]), _swv_hhmm(status["expected_end_time"])
    if status["schedule_status"] == "running":
        flow_text = "" if flow is None else ", %s L/min" % flow
        return "Running (%s, %s) since %s, %s %s%s, expected end %s" % (kind, mode, start, status["actual_irrigation_amount"], unit, flow_text, expected_end)
    if status["schedule_status"] == "end":
        minutes = _swv_minutes_between(status["start_time"], status["actual_end_time"])
        average = _swv_session_average_flow(status)
        average_text = "" if average is None else ", avg %s L/min" % average
        return "Ended %s after %s min, %s %s%s (%s, %s)" % (_swv_hhmm(status["actual_end_time"]), minutes, status["actual_irrigation_amount"], unit, average_text, kind, mode)
    if status["schedule_status"] == "start":
        return "Started %s (%s, %s), expected end %s" % (start, kind, mode, expected_end)
    # standby: the next scheduled occurrence
    return "Idle, next: %s (%s) %s to %s" % (kind, mode, start, expected_end)


def _swv_schedule_status_report_due(self, nwkid, schedule_status, now):
    """ True on a status change (never throttled), or once every SONOFF_SWV_STATUS_REPORT_INTERVAL seconds otherwise """
    last_status, last_time = _swv_status_last_report.get(nwkid, (None, 0))
    interval = _param_int(self, nwkid, "SONOFF_SWV_STATUS_REPORT_INTERVAL", SONOFF_SWV_STATUS_REPORT_DEFAULT_SECONDS, 0, 86400)
    if schedule_status != last_status or now - last_time >= interval:
        _swv_status_last_report[nwkid] = (schedule_status, now)
        return True
    return False


def sonoff_swv_irrigation_schedule_status(self, nwkid, ep, cluster, attribut, value):
    """ SWV-ZFE/ZFU: decode the 0x501f irrigation schedule status report (EvalFunc).

    Reported when a schedule starts, while it runs, when it ends (or is interrupted) and when
    the valve is idle. start/standby reports carry 15 elements, running/end reports 21:
      [0] status  [1] schedule index  [2] schedule type  [3] irrigation mode
      [4..7] start time  [8..11] expected end time  ([12..15] actual end time, running/end only)
      unit byte, expected amount (uint16), (actual amount (uint16), running/end only)
    Multi-byte fields are big endian; amounts follow the reported unit byte.
    """
    self.log.logging("Sonoff", "Debug", "sonoff_swv_irrigation_schedule_status - Nwkid: %s value: %s" % (nwkid, value), nwkid)
    try:
        data = _swv_array_elements(value, (SONOFF_SWV_SCHEDULE_STATUS_START_STANDBY_LEN, SONOFF_SWV_SCHEDULE_STATUS_RUNNING_END_LEN))
    except (ValueError, TypeError):
        self.log.logging("Sonoff", "Error", "sonoff_swv_irrigation_schedule_status - invalid 0x501f payload %s" % value, nwkid)
        return None

    if len(data) < 4:
        self.log.logging("Sonoff", "Error", "sonoff_swv_irrigation_schedule_status - 0x501f payload too short (%s bytes): %s" % (len(data), value), nwkid)
        return None

    status = data[0]
    if status not in SONOFF_SWV_SCHEDULE_STATUS:
        self.log.logging("Sonoff", "Error", "sonoff_swv_irrigation_schedule_status - unknown 0x501f schedule status 0x%02x: %s" % (status, value), nwkid)
        return None

    with_actuals = status in (0x01, 0x02)   # end / running
    expected_len = SONOFF_SWV_SCHEDULE_STATUS_RUNNING_END_LEN if with_actuals else SONOFF_SWV_SCHEDULE_STATUS_START_STANDBY_LEN
    if len(data) < expected_len:
        self.log.logging("Sonoff", "Error", "sonoff_swv_irrigation_schedule_status - 0x501f %s report has %s bytes, expected %s: %s" % (
            SONOFF_SWV_SCHEDULE_STATUS[status], len(data), expected_len, value), nwkid)
        return None

    result = {
        "schedule_status": SONOFF_SWV_SCHEDULE_STATUS[status],
        "schedule_index": data[1],
        "schedule_type": SONOFF_SWV_SCHEDULE_TYPE.get(data[2], data[2]),
        "irrigation_mode": SONOFF_SWV_IRRIGATION_MODE_NAME.get(data[3], data[3]),
        "start_time": _swv_local_time_to_iso(int.from_bytes(data[4:8], "big")),
        "expected_end_time": _swv_local_time_to_iso(int.from_bytes(data[8:12], "big")),
        "actual_end_time": None,
        "actual_irrigation_amount": None,
    }
    idx = 12
    if with_actuals:
        result["actual_end_time"] = _swv_local_time_to_iso(int.from_bytes(data[12:16], "big"))
        idx = 16
    result["irrigation_amount_unit"] = SONOFF_SWV_AMOUNT_UNIT_NAME.get(data[idx], data[idx])
    result["expected_irrigation_amount"] = int.from_bytes(data[idx + 1:idx + 3], "big")
    if with_actuals:
        result["actual_irrigation_amount"] = int.from_bytes(data[idx + 3:idx + 5], "big")

    self.log.logging("Sonoff", "Debug", "sonoff_swv_irrigation_schedule_status - Nwkid: %s decoded: %s" % (nwkid, result), nwkid)

    # Flow (L/min): handed to the Flow widget under "flow_l_min" (upd_domo_device with
    # "UpdDomoDeviceWithCluster": "TextStatus/Flow/WaterVolume/WaterCounter") once per SONOFF_SWV_FLOW_RATE_INTERVAL while
    # running, 0 otherwise; absent when nothing new has been measured.
    flow = _swv_flow_rate(self, nwkid, result)
    if flow is not None:
        result["flow_l_min"] = flow
    # Daily volume (L): handed to the WaterVolume widget under "water_volume_l" on every report
    result["water_volume_l"] = _swv_daily_volume_liters(self, nwkid, result)
    # Consumption (L): handed to the WaterCounter widget under "water_counter_l" as an increment, when there is one
    increment = _swv_water_counter_increment(self, nwkid, result)
    if increment is not None:
        result["water_counter_l"] = increment

    # Human readable status: logged, and handed to the TextStatus widget under "text", on every status change
    # and at most once per SONOFF_SWV_STATUS_REPORT_INTERVAL otherwise.
    if _swv_schedule_status_report_due(self, nwkid, result["schedule_status"], time.time()):
        result["text"] = _swv_schedule_status_text(result, _swv_flow_window.get(nwkid, (None, None, None))[2])
        self.log.logging("Sonoff", "Log", "Irrigation %s: %s" % (nwkid, result["text"]), nwkid)
    return result


def zbmicro_radio_power_turbo_mode(self, nwkid, mode):
    """ Enable/disable Radio Power Turbo Mode """
    RADIO_POWER_MODE = {
        "Normal": 0x09,
        "Turbo": 0x14
    }
    self.log.logging("Sonoff", "Debug", "zbmicro_radio_power_turbo_mode - Nwkid: %s value: %s" % (nwkid, mode), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, SONOFF_MANUFACTURER_ID, "01", SONOFF_RADIO_POWER_TURBO_MODE, "29", "%08x" %RADIO_POWER_MODE.get( mode, 0x09), ackIsDisabled=False)


def sonoff_temperature_unit(self, nwkid, unit):
    """ Set temperature unit for Sonoff SNZB-02LD """
    if unit not in [0, 1]:  # 0 for Celsius, 1 for Fahrenheit
        self.log.logging("Sonoff", "Error", "Invalid temperature unit: %s. Use 0 for Celsius or 1 for Fahrenheit." % unit, nwkid)
        return  # Invalid unit, do not proceed
    self.log.logging("Sonoff", "Debug", "sonoff_temperature_unit - Nwkid: %s Unit: %s" % (nwkid, unit), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, "0000", "00", SONOFF_TEMPERATURE_UNIT_ATTRIBUTE, "21", "%04x" %unit, ackIsDisabled=False)


def sonoff_temperature_calibration(self, nwkid, calibration):
    """ Set temperature calibration for Sonoff SNZB-02LD """
    if not isinstance(calibration, int):
        self.log.logging("Sonoff", "Error", "Invalid calibration value: %s. It should be an integer." % calibration, nwkid)
        return  # Invalid calibration, do not proceed
    if calibration < -50 or calibration > 50:
        self.log.logging("Sonoff", "Error", "Calibration value out of range: %s. It should be between -100 and 100." % calibration, nwkid)
        return  # Calibration out of range, do not proceed
    # Convert calibration to a 16-bit signed integer
    calibration = int(calibration * 100)
    self.log.logging("Sonoff", "Debug", "sonoff_temperature_calibration - Nwkid: %s Calibration: %s" % (nwkid, calibration), nwkid)
    write_attribute(self, nwkid, ZIGATE_EP, "01", SONOFF_CLUSTER_ID, "0000", "00", SONOFF_CALIBRATION_ATTRIBUTE, "29", "%04x" %calibration, ackIsDisabled=False)


# Dictionary to map Sonoff device parameters to their respective functions
SONOFF_DEVICE_PARAMETERS = {
    "SonOffTRVChildLock": sonoff_child_lock,
    "SonOffTRVWindowDectection": sonoff_open_window_detection,
    "SONOFF_TEMP_MAX": sonoff_temp_humi_ranges,
    "SONOFF_TEMP_MIN": sonoff_temp_humi_ranges,
    "SONOFF_HUMI_MAX": sonoff_temp_humi_ranges,
    "SONOFF_HUMI_MIN": sonoff_temp_humi_ranges,
    "SONOFF_REALTIME_IRRIGATION_DURATION": sonoff_realtime_irrigation_duration,
    "SONOFF_REALTIME_IRRIGATION_VOLUME": sonoff_realtime_irrigation_volume,
    "SONOFF_DAILY_IRRIGATION_VOLUME": sonoff_realtime_irrigation_daily_volume,
    "SONOFF_SWV_WATER_CLOSE_VALVE_TIMEOUT": auto_close_when_water_shortage,
    "SONOFF_CHILD_LOCK": sonoff_child_lock,
    "SONOFF_SWV_MANUAL_IRRIGATION_DURATION": sonoff_swv_manual_default_settings,
    "SONOFF_SWV_MANUAL_IRRIGATION_MODE": sonoff_swv_manual_default_settings,
    "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT_UNIT": sonoff_swv_manual_default_settings,
    "SONOFF_SWV_MANUAL_IRRIGATION_AMOUNT": sonoff_swv_manual_default_settings,
    "SONOFF_SWV_MANUAL_FAIL_SAFE": sonoff_swv_manual_default_settings,
    "SONOFF_SWV_ALARM_WATER_SHORTAGE": sonoff_swv_valve_alarm_settings,
    "SONOFF_SWV_ALARM_WATER_LEAK": sonoff_swv_valve_alarm_settings,
    "SONOFF_SWV_WATER_SHORTAGE_AUTO_CLOSE": sonoff_swv_valve_alarm_settings,
    "SONOFF_SWV_ALARM_WATER_SHORTAGE_DURATION": sonoff_swv_valve_alarm_settings,
    "SONOFF_SWV_ALARM_WATER_LEAK_DURATION": sonoff_swv_valve_alarm_settings,
    "SONOFF_SWV_WATER_FLOW_UNIT": sonoff_swv_water_flow_unit,
    "SONOFF_ZBMICRO_RADIO_POWER_TURBO_MODE": zbmicro_radio_power_turbo_mode,
    "SONOFF_TEMP_CALIBRATION": sonoff_temperature_calibration,
    "SONOFF_TEMP_UNIT": sonoff_temperature_unit
}
