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
IAS ACE (Intruder Alarm System - Arm Control Equipment) Command Handler
=======================================================================

This module implements the logic for handling Zigbee IAS ACE (Cluster 0x0501)
commands, typically used by security keypads (e.g. Develco KEYZB-110)
and control panels in alarm systems.

It manages the bidirectional communication between Zigbee IAS devices and
the Domoticz environment, including interpreting arm/disarm commands,
handling keypad PIN code inputs, sending panel status updates, and
generating appropriate Zigbee ZCL responses.

----------------------------------------------------------------------
Main Responsibilities
----------------------------------------------------------------------

1. **Command Dispatching**
   - Decodes and handles IAS ACE commands (`Arm`, `Emergency`, `Get Panel Status`, etc.).
   - Routes commands either to a general handler or a dedicated IAS keypad handler.

2. **Keypad Interaction**
   - Decodes keypad payloads (PIN codes, arm mode).
   - Stores the last arm command and PIN used by a given device.
   - Generates feedback responses (LEDs, tones, panel status) per IAS specification.

3. **Panel Status Management**
   - Tracks and updates the current arm/disarm status of devices.
   - Handles exit/entry delays and status transitions (e.g. arming, in alarm, not ready).
   - Builds and sends IAS ACE ZCL responses such as `ArmResponse` and `PanelStatusChanged`.

4. **Integration with Domoticz**
   - Synchronizes Zigbee IAS states with Domoticz virtual devices through `MajDomoDevice`.

----------------------------------------------------------------------
Key Functions
----------------------------------------------------------------------

- **handle_ias_ace_command()**
  Entry point for processing incoming IAS ACE Zigbee commands.
  Determines the command type and dispatches to the appropriate handler.

- **handle_ias_keyboard_arm()**
  Processes keypad `Arm` requests with PIN validation.
  Updates the device state and schedules exit delay timers.

- **get_panel_status_response()**
  Responds to `Get Panel Status` Zigbee requests with the current alarm state.

- **send_panel_status_change()**
  Sends asynchronous `PanelStatusChanged` notifications when state transitions occur.

- **store_panel_status() / get_panel_status_from_widget()**
  Maintains and retrieves the current panel status for each Zigbee node.

- **decode_kepzb_110_hex_string()**
  Decodes Develco KEYZB-110 PIN payload from hexadecimal to ASCII format.

- **ias_keypad_feedback_*()**
  A family of helper functions that send feedback to the keypad to update
  LEDs or indicate specific alarm states (armed, not ready, alarm, etc.).

----------------------------------------------------------------------
Constants
----------------------------------------------------------------------

- `IAS_ACE_COMMANDS` : Mapping of IAS ACE command IDs to readable names.
- `ARM_COMMANDS` : Translation of arm mode codes to textual states.
- `ARM_NOTIFICATION_RESPONSE` : Maps textual states to ZCL notification codes.
- `PANEL_STATUS_DESC_TO_CODE` / `PANEL_STATUS_CODE_TO_DESC` :
  Bidirectional mappings between panel status names and their numeric codes.
- `ARM_COMMAND_DISPATCH` : Defines cluster/value/notification triplets for arm actions.

----------------------------------------------------------------------
Dependencies
----------------------------------------------------------------------

- **Modules.domoMaj.MajDomoDevice**
  Updates corresponding Domoticz devices with the current IAS state.

- **Modules.tools**
  Provides helpers such as `get_and_inc_ZCL_SQN`, `get_device_config_param`,
  and `get_deviceconf_parameter_value`.

- **Zigbee.zclRawCommands**
  Provides low-level functions for crafting and sending ZCL raw responses:
  - `zcl_raw_arm_response`
  - `zcl_raw_get_panel_status_response`
  - `zcl_raw_panel_status_change`

----------------------------------------------------------------------
Usage Example
----------------------------------------------------------------------

The command is then interpreted and translated into the appropriate
Domoticz updates and Zigbee responses.

----------------------------------------------------------------------
Author
----------------------------------------------------------------------
Patrick Pichon, 2025

----------------------------------------------------------------------
License
----------------------------------------------------------------------
This module is distributed under the same license as the parent Zigbee
integration or Domoticz plugin it belongs to.
"""

import time

from Modules.domoMaj import MajDomoDevice
from Modules.tools import (get_and_inc_ZCL_SQN, get_device_config_param,
                           get_deviceconf_parameter_value)
from Zigbee.zclRawCommands import (zcl_raw_arm_response,
                                   zcl_raw_get_panel_status_response,
                                   zcl_raw_panel_status_change)

IAS_ACE_COMMANDS = {
    "00": "Arm",
    "01": "Bypass",
    "02": "Emergency",
    "03": "Fire",
    "04": "Panic",
    "05": "Get Zone ID Map",
    "06": "Get Zone Information",
    "07": "Get Panel Status",
    "08": "Get Bypassed Zone List",
    "09": "Get Zone Status",
}

ARM_COMMANDS = {
    "00": "Disarm",
    "01": "ArmHome",
    "02": "ArmNight",
    "03": "ArmAllZones",
}

ARM_NOTIFICATION_RESPONSE = {
    "Disarm": "00",
    "ArmHome": "01",
    "ArmNight": "02",
    "ArmAllZones": "03",
    "InvalidCode": "04",
    "NotReady": "05",
    "AlreadyDisarmed": "06",
}

PANEL_STATUS_DESC_TO_CODE = {
    "Disarm": 0x00,
    "ArmHome": 0x01,
    "ArmNight": 0x02,
    "ArmAllZones": 0x03,
    "ExitDelay": 0x04,
    "EntryDelay": 0x05,
    "NotReady": 0x06,
    "InAlarm": 0x07,
    "ArmingStay": 0x08,
    "ArmingNight": 0x09,
    "ArmingAway": 0x0A,
}
PANEL_STATUS_CODE_TO_DESC = {
    "00": "Disarm",
    "01": "ArmHome",
    "02": "ArmNight",
    "03": "ArmAllZones",
    "04": "ExitDelay",
    "05": "EntryDelay",
    "06": "NotReady",
    "07": "InAlarm",
    "08": "ArmingStay",
    "09": "ArmingNight",
    "0A": "ArmingAway",
}


ARM_COMMAND_DISPATCH = {  
    # Cluster, Value, NotificationCode
    "Disarm": ("0006", "04", "00"),
    "ArmHome": ("0006", "01", "01"),
    "ArmAllZones": ("0006", "03", "03"),
    }


def handle_ias_ace_command(self, Devices, nwkid, ep, sqn, model_name, command, payload):
    """
    Handle IAS ACE (Intruder Alarm System - Arm Control Equipment) commands.
    """

    cmd_name = IAS_ACE_COMMANDS.get(command)
    self.log.logging("IAS_ACE", "Debug", f"IAS ACE Command: {command} ({cmd_name}) Payload: {payload}")

    if not cmd_name:
        self.log.logging("IAS_ACE", "Warn", f"Unknown IAS ACE command: {command} - {payload}")
        return

    if cmd_name == "Arm":
        # Retrieve device configuration once, to check if this is a keyboard
        is_ias_keyboard = get_deviceconf_parameter_value(self, model_name, "IAS_KEYBOARD")
        self.log.logging("IAS_ACE", "Debug", f"IAS ACE Command: {command} ({cmd_name}) is_ias_keyboard={is_ias_keyboard}")

        arm_code = payload[:2]
        arm_desc = ARM_COMMANDS.get(arm_code, "Unknown")
        if is_ias_keyboard:
            handle_ias_keyboard_arm(self, Devices, nwkid, ep, sqn, arm_code, arm_desc, payload)
            return
        # Else normal arm command without keypad
        handle_arm_command(self, Devices, nwkid, ep, sqn, arm_code, arm_desc, payload, is_ias_keyboard)

    elif cmd_name == "Emergency":
        MajDomoDevice(self, Devices, nwkid, ep, "0006", "01")

    elif cmd_name == "Get Panel Status":
        self.log.logging("IAS_ACE", "Debug", f"IAS ACE Get Panel Status {command} - {payload}")
        get_panel_status_response(self, Devices, nwkid, ep, sqn)

    else:
        self.log.logging("IAS_ACE", "Warn", f"Unhandled IAS ACE command: {cmd_name} ({command}) Payload: {payload}")


def handle_arm_command(self, Devices, nwkid, ep, sqn, arm_code, arm_desc, payload, is_ias_keyboard):
    self.log.logging("IAS_ACE", "Debug", f"_handle_arm_command: Payload: {payload} Code: {arm_code} Desc: {arm_desc} {is_ias_keyboard}")

    if arm_desc in ARM_COMMAND_DISPATCH:
        cluster, value, notif_code = ARM_COMMAND_DISPATCH[arm_desc]
        MajDomoDevice(self, Devices, nwkid, ep, cluster, value)
        zcl_raw_arm_response(self, "01", ep, nwkid, sqn, notif_code)


def get_panel_status_response(self, Devices, nwkid, ep, sqn):
    """
    Handle IAS ACE Get Panel Status Response command.
    """
    panel_status_code =get_panel_status_from_widget(self, nwkid)
    if panel_status_code is None:
        # We assume that we do not have a status and waiting for the processing of the arm command
        # So we do not respond anything
        self.log.logging("IAS_ACE", "Debug", f"get_panel_status_response: {nwkid}/{ep} - No status available yet. we do not respond.")
        return

    panel_status = f"{panel_status_code:02x}"
    seconds_remaining = get_remaining_time(self, nwkid)
    audible_notification = "00" if seconds_remaining == "00" else "03"
    alarm_status = "00"
    
    payload = panel_status + seconds_remaining + audible_notification + alarm_status
    self.log.logging("IAS_ACE", "Debug", f"get_panel_status_response: {nwkid}/{ep} Panel Status={panel_status} Payload={payload}")
    zcl_raw_get_panel_status_response( self, "01", ep, nwkid, sqn, payload )


def send_panel_status_change(self, nwkid, ep, sqn, panel_status_code, alarm_status="00"):
    """Send IAS ACE Panel Status Change Notification."""
    self.log.logging("IAS_ACE", "Debug", f"send_panel_status_change: {nwkid}/{ep} - {panel_status_code}")
    
    panel_status = panel_status_code
    seconds_remaining = get_remaining_time(self, nwkid)
    audible_notification = "03"
    payload = panel_status + seconds_remaining + audible_notification + alarm_status

    self.log.logging("IAS_ACE", "Debug", f"send_panel_status_change: {nwkid}/{ep} Panel Status={panel_status} Payload={payload}")
    zcl_raw_panel_status_change( self, "01", ep, nwkid, sqn, payload, )


def handle_ias_keyboard_arm(self, Devices, nwkid, ep, sqn, arm_code, arm_desc, payload):
    """
    Handle IAS keypad 'Arm' commands with PIN code input.
    """
    self.log.logging("IAS_ACE", "Debug", f"handle_ias_keyboard_arm: {arm_code} {arm_desc} Payload: {payload}")
    
    EXIT_DELAY = 0xff  # Max / 255 seconds - The delay will be handled via the 
    exit_delay = get_device_config_param(self, nwkid, "ARM_EXIT_DELAY") or EXIT_DELAY

    if "IAS_KEYPAD" not in self.ListOfDevices.get(nwkid, {}):
        self.ListOfDevices.setdefault(nwkid, {})["IAS_KEYPAD"] = {}

    decoded_code = decode_kepzb_110_hex_string(payload[2:])

    self.ListOfDevices[nwkid]["IAS_KEYPAD"]["Last"] = {
        "TimeStamp": (time.time() + exit_delay),
        "LastArmMode": arm_code,
        "LastArmModeDescription": arm_desc,
        "Code": decoded_code,
        "Sqn": sqn,
    }

    self.log.logging("IAS_ACE", "Debug", f"IAS Keyboard - {arm_code} {arm_desc} {payload} Decoded PIN: {decoded_code} Last: {self.ListOfDevices[nwkid]['IAS_KEYPAD']['Last']}")

    text_message = f"{arm_desc},{decoded_code}"
    MajDomoDevice(self, Devices, nwkid, ep, "0501", text_message)

    # We have received an arm command from the keypad, set the panel status to Empty for now
    self.ListOfDevices.get(nwkid, {}).get("IAS_KEYPAD", {}).get("Current", {})

    # We stop here, waiting for Domoticz to process the command and send back the appropriate feedback
    #if arm_desc in ARM_NOTIFICATION_RESPONSE:
    #    arm_response(self, nwkid, ep, sqn, ARM_NOTIFICATION_RESPONSE[arm_desc])
    #    send_panel_status_change(self, nwkid, ep, sqn, arm_desc)


def store_panel_status(self, nwkid, arm_code):
    self.log.logging("IAS_ACE", "Debug", f"store_panel_status: {nwkid} - {arm_code}")
    if "IAS_KEYPAD" not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]["IAS_KEYPAD"] = {}

    self.ListOfDevices[nwkid]["IAS_KEYPAD"]["Current"] = {
        "CurrentArmMode": arm_code,
        "CurrentArmModeDescription": PANEL_STATUS_CODE_TO_DESC.get(arm_code, "NotReady"),
        }


def get_panel_status_from_widget(self, nwkid):
    """
    Get current IAS panel status from widget or memory. And respond NotReady if not found.
    """
    keypad_data = self.ListOfDevices.get(nwkid, {}).get("IAS_KEYPAD", {}).get("Current", {})
    if keypad_data == {}:
        return None
    return PANEL_STATUS_DESC_TO_CODE.get(keypad_data.get("CurrentArmModeDescription", 0x06), 0x06)


def get_remaining_time(self, nwkid):
    """
    Get remaining time for exit/entry delay from widget or memory.
    """
    now = time.time()
    second_remaining = int(self.ListOfDevices.get(nwkid, {}).get("IAS_KEYPAD", {}).get("Last", {}).get("TimeStamp", now) - now)
    second_remaining = max(second_remaining, 0)
    return f"{second_remaining:02x}"


def decode_kepzb_110_hex_string(hex_string: str) -> str:
    """
    Decode Develco KEYZB-110 keypad PIN payload.
    The first byte is the ASCII string length.
    """
    if not hex_string:
        return ""
    data = bytes.fromhex(hex_string)
    length = data[0]
    return data[1:1 + length].decode("ascii", errors="ignore")

def ias_keyboard_feedback_arm_response_all_zone_disarmed(self, nwkid, ep):
    # this should be a response to an invalid PIN code
    self.log.logging("IAS_ACE", "Debug", f"ias_keyboard_feedback_pincode_invalid: {nwkid}/{ep}")
    sqn = self.ListOfDevices[nwkid].get("IAS_KEYPAD", {}).get("Last", {}).get("Sqn", "00")
    zcl_raw_arm_response(self, "01", ep, nwkid, sqn, "00")
    ias_keypad_feedback_panel_status_disarm(self, nwkid, ep)


def ias_keyboard_feedback_arm_response_arming_stay(self, nwkid, ep):
    # this should be a response to an invalid PIN code
    self.log.logging("IAS_ACE", "Debug", f"ias_keyboard_feedback_arm_response_arming_stay: {nwkid}/{ep}")
    sqn = self.ListOfDevices[nwkid].get("IAS_KEYPAD", {}).get("Last", {}).get("Sqn", "00")
    zcl_raw_arm_response(self, "01", ep, nwkid, sqn, "01")
    ias_keypad_feedback_panel_status_arming_stay(self, nwkid, ep, )


def ias_keyboard_feedback_arm_response_arming_night(self, nwkid, ep):
    # this should be a response to an invalid PIN code
    self.log.logging("IAS_ACE", "Debug", f"ias_keyboard_feedback_arm_response_arming_night: {nwkid}/{ep}")
    sqn = self.ListOfDevices[nwkid].get("IAS_KEYPAD", {}).get("Last", {}).get("Sqn", "00")
    zcl_raw_arm_response(self, "01", ep, nwkid, sqn, "02")
    ias_keypad_feedback_panel_status_arming_night(self, nwkid, ep)


def ias_keyboard_feedback_arm_response_arming_away(self, nwkid, ep):
    # this should be a response to an invalid PIN code
    self.log.logging("IAS_ACE", "Debug", f"ias_keyboard_feedback_arm_response_arming_away: {nwkid}/{ep}")
    sqn = self.ListOfDevices[nwkid].get("IAS_KEYPAD", {}).get("Last", {}).get("Sqn", "00")
    zcl_raw_arm_response(self, "01", ep, nwkid, sqn, "03")
    ias_keypad_feedback_panel_status_arming_away(self, nwkid, ep)


def ias_keyboard_feedback_arm_response_invalid_code(self, nwkid, ep):
    # this should be a response to an invalid PIN code
    self.log.logging("IAS_ACE", "Debug", f"ias_keyboard_feedback_arm_response_invalid_code: {nwkid}/{ep}")
    sqn = self.ListOfDevices[nwkid].get("IAS_KEYPAD", {}).get("Last", {}).get("Sqn", "00")
    zcl_raw_arm_response(self, "01", ep, nwkid, sqn, "04")


def ias_keyboard_feedback_not_ready(self, nwkid, ep):
    # this should be a response to an invalid PIN code
    self.log.logging("IAS_ACE", "Debug", f"ias_keyboard_feedback_not_ready: {nwkid}/{ep}")
    sqn = self.ListOfDevices[nwkid].get("IAS_KEYPAD", {}).get("Last", {}).get("Sqn", "00")
    zcl_raw_arm_response(self, "01", ep, nwkid, sqn, "05")
    ias_keypad_panel_status_not_ready(self, nwkid, ep)


def ias_keypad_feedback_panel_status_disarm(self, nwkid, ep):
    # Led Green 3s Fix
    # Code 0x00
    self.log.logging("IAS_ACE", "Debug", f"ias_keypad_feedback_panel_status_disarm: {nwkid}/{ep}")
    store_panel_status(self, nwkid, "00")
    send_panel_status_change(self, nwkid, ep, get_and_inc_ZCL_SQN(self, nwkid), "00")


def ias_keypad_feedback_panel_status_arming_stay(self, nwkid, ep, ):
    # Led Rouge Fix
    # Code 0x08
    self.log.logging("IAS_ACE", "Debug", f"ias_keypad_feedback_panel_status_arming_stay: {nwkid}/{ep}")
    store_panel_status(self, nwkid, "01")
    send_panel_status_change(self, nwkid, ep, get_and_inc_ZCL_SQN(self, nwkid), "01")


def ias_keypad_feedback_panel_status_arming_night(self, nwkid, ep):
    # Led Rouge Fix
    # Code 0x09
    self.log.logging("IAS_ACE", "Debug", f"ias_keypad_feedback_panel_status_arming_night: {nwkid}/{ep}")
    store_panel_status(self, nwkid, "02")
    send_panel_status_change(self, nwkid, ep, get_and_inc_ZCL_SQN(self, nwkid), "02")


def ias_keypad_feedback_panel_status_arming_away(self, nwkid, ep):
    # Led Rouge Fix
    # Code 0x0a
    self.log.logging("IAS_ACE", "Debug", f"ias_keypad_feedback_panel_status_arming_away: {nwkid}/{ep}")
    store_panel_status(self, nwkid, "03")
    send_panel_status_change(self, nwkid, ep, get_and_inc_ZCL_SQN(self, nwkid), "03")


def ias_keypad_panel_status_exit_delay(self, nwkid, ep):    
    # Exit Delay / grace period = exit delay
    # Code 0x04
    self.log.logging("IAS_ACE", "Debug", f"ias_keypad_panel_status_exit_delay: {nwkid}/{ep}")
    store_panel_status(self, nwkid, "04")
    send_panel_status_change(self, nwkid, ep, get_and_inc_ZCL_SQN(self, nwkid), "04")


def ias_keypad_panel_status_entry_delay(self, nwkid, ep):    
    # Entry Delay / Alarm detected, grace period = entry delay
    # Code 0x05
    self.log.logging("IAS_ACE", "Debug", f"ias_keypad_panel_status_entry_delay: {nwkid}/{ep}")
    store_panel_status(self, nwkid, "05")
    send_panel_status_change(self, nwkid, ep, get_and_inc_ZCL_SQN(self, nwkid), "05")


def ias_keypad_panel_status_not_ready(self, nwkid, ep):
    # Led Blinking  / Led 2 Yellow
    # Code 0x06
    self.log.logging("IAS_ACE", "Debug", f"ias_keypad_panel_status_not_ready: {nwkid}/{ep}")
    store_panel_status(self, nwkid, "06")
    send_panel_status_change(self, nwkid, ep, get_and_inc_ZCL_SQN(self, nwkid), "06")


def ias_keypad_panel_status_in_alarm(self, nwkid, ep):
    # Alarm detected
    # Code 0x07
    self.log.logging("IAS_ACE", "Debug", f"ias_keypad_panel_status_in_alarm: {nwkid}/{ep}")
    store_panel_status(self, nwkid, "07")
    send_panel_status_change(self, nwkid, ep, get_and_inc_ZCL_SQN(self, nwkid), "07", alarm_status="01")


def ias_keypad_panel_status_armed_night(self, nwkid, ep):    
    # Led Rouge Fix
    # Code 0x02
    self.log.logging("IAS_ACE", "Debug", f"ias_keypad_panel_status_armed_night: {nwkid}/{ep}")
    store_panel_status(self, nwkid, "09")
    send_panel_status_change(self, nwkid, ep, get_and_inc_ZCL_SQN(self, nwkid), "09")


def ias_keypad_panel_status_armed_home(self, nwkid, ep):    
    # Led Rouge Fix
    # Code 0x01
    self.log.logging("IAS_ACE", "Debug", f"ias_keypad_panel_status_armed_home: {nwkid}/{ep}")
    store_panel_status(self, nwkid, "08")
    send_panel_status_change(self, nwkid, ep, get_and_inc_ZCL_SQN(self, nwkid), "08")


def ias_keypad_panel_status_armed_all_zones(self, nwkid, ep):    
    # Led Rouge Fix
    # Code 0x03
    self.log.logging("IAS_ACE", "Debug", f"ias_keypad_panel_status_armed_all_zones: {nwkid}/{ep}")
    store_panel_status(self, nwkid, "0a")
    send_panel_status_change(self, nwkid, ep, get_and_inc_ZCL_SQN(self, nwkid), "0a")
