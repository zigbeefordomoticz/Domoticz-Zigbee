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


import calendar
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from Modules.basicInputs import read_attribute_response
from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import is_ack_tobe_disabled, to_little_endian
from Modules.zigateConsts import ZIGATE_EP

ZIGBEE_EPOCH = datetime(2000, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
TUYA_EPOCTime = datetime(1970, 1, 1, 0, 0, 0, 0)


def get_local_timezone():
    """
    Get the local time zone name from the system environment.

    :return: The name of the local time zone.
    """
    return os.environ.get('TZ', 'UTC') or 'UTC'


def calculate_dst_times(self):
    """
    Calculate the DST start and end times for the current year in the local time zone.

    :return: Tuple containing DST start time, DST end time, and DST shift in seconds.
    """
    # Get the local time zone name
    local_tz_name = get_local_timezone()
    # If the time zone is UTC, no DST exists → return (0, 0, 0) immediately
    if local_tz_name == "UTC":
        return 0, 0, 0

    try:
        local_tz = ZoneInfo(local_tz_name)
    except Exception as er:
        _context = {
            'Error': "TimeServer_001",
            'Description': str(er),
            'Local_tz_name': local_tz_name,
        }
        self.log.logging(["TimeServer","Input"], "Error", "Decode0100 - calculate_dst_times - invalid time zone ", context=_context)
        return 0, 0, 0

    current_year = datetime.now().year

    # Find the DST start and end times for the current year
    dst_start = None
    dst_end = None

    # Iterate over the year to find DST transitions
    for month in range(1, 13):
        num_days = calendar.monthrange(current_year, month)[1]  # Get correct number of days
        for day in range(1, num_days + 1):
            try:
                date = datetime(current_year, month, day, tzinfo=local_tz)
                if date.dst() != timedelta(0) and dst_start is None:
                    dst_start = date
                elif date.dst() == timedelta(0) and dst_start is not None:
                    dst_end = date
                    break  # Stop searching once we find dst_end

            except Exception as er:
                _context = {
                    'Error': "TimeServer_001",
                    'Description': str(er),
                    'Local_tz_name': local_tz_name,
                    'Local_tz': local_tz,
                    'Current_year': current_year,
                    'Month': month,
                    'Day': day,
                    'Date': date
                }
                self.log.logging(["TimeServer","Input"], "Error", "Decode0100 - calculate_dst_times - invalid date ", context=_context)
                return 0, 0, 0

        if dst_end:
            break

    if dst_start is None or dst_end is None:
        print("No DST transition found for this time zone.")
        return 0, 0, 0  # Return zero values if no DST change occurs

    # Calculate the DST shift in seconds
    dst_shift = int(dst_start.dst().total_seconds())

    # Convert DST start and end times to UTC
    dst_start_utc = int(dst_start.timestamp())
    dst_end_utc = int(dst_end.timestamp())

    return dst_start_utc, dst_end_utc, dst_shift


def timeserver_multiple_read_attribute_request(self, Devices, nwkid, src_ep, dst_ep, sqn, cluster_id, manuf_specif, manuf_code, MsgData, nbAttribute):
    """ Handle a read request with multiple attributes on cluster 0x000a"""

    if sqn == self.ListOfDevices[nwkid].get("SQN_000a"):
        self.log.logging(["TimeServer","Input"], "Debug", f"Decode0100 - timeserver_multiple_read_attribute_request - duplicate request nwkid {nwkid} nbAttribute: {nbAttribute}", nwkid)
        return

    self.ListOfDevices[nwkid]["SQN_000a"] = sqn
    
    payload = None
    cmd = "01"
    status = "00"
    cluster_frame = "18"

    # Extract all attributes, and build a response
    for idx in range(0, len(MsgData), 4):
        attribute = MsgData[idx:idx + 4]
        self.log.logging(["TimeServer","Input"], "Debug", f"Decode0100 - timeserver_multiple_read_attribute_request - nwkid {nwkid} attribute {attribute}", nwkid)

        # Handle different cluster IDs and attributes
        status, data_type, value = get_response_data_for_timer_attribute_request(self, nwkid, attribute)
        self.log.logging(["TimeServer","Input"], "Debug", f"Decode0100 - timeserver_multiple_read_attribute_request -  response {data_type} {value}", nwkid)
        if payload is None:
            payload = cluster_frame + sqn + cmd
        payload += attribute[2:4] + attribute[:2] + status + data_type

        payload += to_little_endian(value)

    self.log.logging(["TimeServer","Input"], "Debug", f"Decode0100 - timeserver_multiple_read_attribute_request Response - nwkid {nwkid} ep: {src_ep} , clusterId: {cluster_id}, sqn: {sqn},payload: {payload}", nwkid)
        
    raw_APS_request( self, nwkid, src_ep, cluster_id, "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=is_ack_tobe_disabled(self, nwkid), )


def get_response_data_for_timer_attribute_request( self, nwkid, attribute):
    # Default values
    data_type = None
    value = None
    status = "86"  # Default to unsupported attribute

    now = datetime.now(timezone.utc)

    attribute_map = {
        "0000": {"value": f"{int((now - ZIGBEE_EPOCH).total_seconds()):08x}", "data_type": "e2", "status": "00"},  # Time
        "0001": {"value": f"{0x07:02x}", "data_type": "18", "status": "00"},  # Time Status: Master, Synchronized, MasterZone
        "0002": {
            "value": f"{int(datetime.now().astimezone().utcoffset().total_seconds() if datetime.now().astimezone().utcoffset() else 0):08x}",
            "data_type": "2b",
            "status": "00",
        },  # Timezone
        "0003": {"value": f"{calculate_dst_times(self)[0]:08x}", "data_type": "23", "status": "00"},  # DST Start
        "0004": {"value": f"{calculate_dst_times(self)[1]:08x}", "data_type": "23", "status": "00"},  # DST End
        "0005": {"value": f"{calculate_dst_times(self)[2]:08x}", "data_type": "2b", "status": "00"},  # DST Shift
        "0006": {"value": "00000000", "data_type": "23", "status": "00"},  # Standard Time
    }

    if attribute in attribute_map:
        value = attribute_map[attribute]["value"]
        data_type = attribute_map[attribute]["data_type"]
        status = attribute_map[attribute]["status"]

    elif attribute == "0007":  # LocalTime
        self.log.logging(["TimeServer","Input"], "Debug", f"-->Local Time: {datetime.now()}")

        epoch = TUYA_EPOCTime if self.ListOfDevices.get(nwkid, {}).get("Model") == "TS0601-thermostat" else ZIGBEE_EPOCH
        if epoch == TUYA_EPOCTime:
            self.log.logging(
                ["TimeServer","Input"],
                "Debug",
                "timeserver_read_attribute_request Response uses EPOCH from 1970-01-01 instead of 2000-01-01",
            )

        tz_offset = datetime.now().astimezone().utcoffset() or timedelta(seconds=0)
        local_time = int((now + tz_offset - epoch).total_seconds())
        value = f"{local_time:08x}"
        data_type = "23"  # uint32
        status = "00"

    return status, data_type, value


def timeserver_read_attribute_request(self, sqn, nwkid, ep, cluster, manuf_spec, manuf_code, attribute):
    """Handles reading various time-related attributes for a Zigbee timeserver."""

    self.log.logging(
        ["TimeServer","Input"],
        "Debug",
        f"timeserver_read_attribute_request [{sqn}] {nwkid}/{ep} Cluster: {cluster} Attribute: {attribute}"
    )

    self.ListOfDevices[nwkid]["SQN_000a"] = sqn

    status, data_type, value = get_response_data_for_timer_attribute_request(self, nwkid, attribute)

    self.log.logging(
        ["TimeServer","Input"],
        "Debug",
        f"timeserver_read_attribute_request Response: status: {status} attribute: {attribute} value: {value}"
    )

    read_attribute_response(self, nwkid, ep, sqn, cluster, status, data_type, attribute, value, manuf_code="0000")
