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


import time

from Modules.casaia import CASAIA_MANUF_CODE, casaiaReadRawAPS
from Modules.domoMaj import MajDomoDevice
from Modules.heiman import heimanReadRawAPS
from Modules.ikeaTradfri import ikea_openclose_remote, ikeaReadRawAPS
from Modules.legrand_netatmo import legrandReadRawAPS
from Modules.livolo import livoloReadRawAPS
from Modules.lumi import lumiReadRawAPS
from Modules.orvibo import orviboReadRawAPS
from Modules.philips import philipsReadRawAPS
from Modules.pollControl import receive_poll_cluster
from Modules.schneider_wiser import schneiderReadRawAPS
from Modules.tools import (get_device_config_param,
                           get_deviceconf_parameter_value)
from Modules.tuya import tuyaReadRawAPS
from Modules.tuyaTools import tuya_manufacturer_device
from Zigbee.zclRawCommands import (zcl_raw_arm_response,
                                   zcl_raw_get_panel_status_response)

# Requires Zigate firmware > 3.1d
CALLBACK_TABLE = {
    # Manuf : ( callbackDeviceAwake_xxxxx function )
    "117c": ikeaReadRawAPS,
    "105e": schneiderReadRawAPS,
    "1021": legrandReadRawAPS,
    "120b": heimanReadRawAPS,
    "115f": lumiReadRawAPS,
    "100b": philipsReadRawAPS,
    "1002": tuyaReadRawAPS,
    CASAIA_MANUF_CODE: casaiaReadRawAPS,
}

CALLBACK_TABLE2 = {
    # Manufacturer Name
    "IKEA of Sweden": ikeaReadRawAPS,
    "LIVOLO": livoloReadRawAPS,
    "欧瑞博": orviboReadRawAPS,
    "Legrand": legrandReadRawAPS,
    "Schneider": schneiderReadRawAPS,
    "Schneider Electric": schneiderReadRawAPS,
    "LUMI": lumiReadRawAPS,
    "Philips": philipsReadRawAPS,
    "OWON": casaiaReadRawAPS,
    "CASAIA": casaiaReadRawAPS,
    "HEIMAN": heimanReadRawAPS,
}


def inRawAps( self, Devices, srcnwkid, srcep, cluster, dstnwkid, dstep, Sqn, GlobalCommand, ManufacturerCode, Command, Data, payload, ):

    """
    This function is called by Decode8002
    """

    if srcnwkid not in self.ListOfDevices:
        self.log.logging( "inRawAPS", "Error", "inRawAps Nwkid: %s Ep: %s Cluster: %s ManufCode: %s Cmd: %s Data: %s not found in ListOfDevices !!" % (
            srcnwkid, srcep, cluster, ManufacturerCode, Command, Data), srcnwkid, )
        return
    
    self.log.logging( "inRawAPS", "Debug", "inRawAps Nwkid: %s Ep: %s Cluster: %s ManufCode: %s Cmd: %s Data: %s" % (
        srcnwkid, srcep, cluster, ManufacturerCode, Command, Data), srcnwkid, )
    
    model_name = self.ListOfDevices[srcnwkid].get("Model", "")

    if cluster == "0020":  # Poll Control ( Not implemented in firmware )
        # self.log.logging("inRawAPS","Log","Cluster 0020 -- POLL CLUSTER")
        receive_poll_cluster(self, srcnwkid, srcep, cluster, dstnwkid, dstep, Sqn, ManufacturerCode, Command, Data)
        return

    if cluster == "0019":  # OTA Cluster
        if self.OTA and Command == "01":
            # Query Next Image Request
            self.OTA.query_next_image_request(srcnwkid, srcep, Sqn, Data)
        return

    if cluster == "0500":  # IAS Cluster
        # "00":
        # "01" # inRawAps 56ba/23 Cluster 0500 Manuf: None Command: 01 Data: 0d001510 Payload: 1922010d001510
        # 0x00  Zone Enroll Response
        # 0x01  Initiate Normal Operation Mode
        # 0x02  Initiate Test Mode

        enroll_response_code = Data[:2]
        zone_id = Data[2:4]

        if Command == "00":
            pass

        elif Command == "01":
            pass

        elif Command == "02":
            pass

        return

    if cluster == "0501":  # IAS ACE
        handle_ias_ace_command( self, Devices, srcnwkid, srcep, Sqn, model_name, Command, Data )
        return
        
    if cluster == "0300":  # Color Control
        if Command == "0a":  # Move to Color Temperature
            color_temp_mired = payload[8:10] + payload[6:8]
            transition_time = payload[12:14] + payload[10:12]
            # self.log.logging("inRawAPS","Log","Move to Color Temp - Command: %s Temp_Mired: %s TransitionTime: %s" %(Command, color_temp_mired, transition_time))
            if model_name == "tint-Remote-white":
                COLOR_SCENE_WHITE = {
                    "022b": "09",
                    "01dc": "10",
                    "01a1": "11",
                    "0172": "12",
                    "00fa": "13",
                    "00c8": "14",
                    "0099": "15",
                }
                if color_temp_mired in COLOR_SCENE_WHITE:
                    MajDomoDevice(self, Devices, srcnwkid, srcep, "0008", COLOR_SCENE_WHITE[color_temp_mired])

        elif Command == "4b":  # Move Color Temperature
            move_mode = payload[6:8]
            rate = payload[10:12] + payload[8:10]
            color_temp_min_mireds = payload[14:16] + payload[12:14]
            color_temp_max_mireds = payload[18:20] + payload[16:18]
            # self.log.logging("inRawAPS","Log","Move Color Temperature - Command: %s mode: %s rate: %s min_mired: %s max_mired: %s" %(
            #    Command, move_mode, rate, color_temp_min_mireds, color_temp_max_mireds))
            if model_name == "tint-Remote-white":
                if move_mode == "01":  # Down
                    MajDomoDevice(self, Devices, srcnwkid, srcep, "0008", "16")

                elif move_mode == "03":  # Up
                    MajDomoDevice(self, Devices, srcnwkid, srcep, "0008", "17")

        elif Command == "47":  # Stop Move Step
            # self.log.logging("inRawAPS","Log","Stop Move Step - Command: %s" %Command)
            if model_name == "tint-Remote-white":
                MajDomoDevice(self, Devices, srcnwkid, srcep, "0008", "18")

        else:
            self.log.logging("inRawAPS", "Log", "Unknown Color Control Command: %s" % Command)

        return

    if cluster == "0102":  # Window Covering
        if model_name == "TRADFRI openclose remote":
            ikea_openclose_remote(self, Devices, srcnwkid, srcep, Command, Data, Sqn)
            return

        if Command == "00":  # Up/Open
            self.log.logging("inRawAPS", "Log", "Window Covering - Up/Open Command")

        elif Command == "01":  # Down / Close
            self.log.logging("inRawAPS", "Log", "Window Covering - Down/Close Command")

        elif Command == "02":  # Stop
            self.log.logging("inRawAPS", "Log", "Window Covering - Stop Command")

        elif Command == "04":  # Go To Lift Value
            self.log.logging("inRawAPS", "Log", "Window Covering - Go To Lift value Command %s" % Data[0:])

        elif Command == "05":  # Go To Lift Percentage
            self.log.logging("inRawAPS", "Log", "Window Covering - Go To Lift percentage Command %s" % Data[0:])

        elif Command == "07":  # Go to Tilt Value
            self.log.logging("inRawAPS", "Log", "Window Covering - Go To Tilt value Command %s" % Data[0:])

        elif Command == "08":  # Go to Tilt Percentage
            self.log.logging("inRawAPS", "Log", "Window Covering - Go To Tilt percentage Command %s" % Data[0:])

        else:
            self.log.logging("inRawAPS", "Log", "Unknown Window Covering Command: %s" % Command)

    if cluster == "0201":  # Thermostat
        if Command == "00":  # Setpoint Raise/Lower
            # Data: 06020100004006a4016c075802400658024006fc036c0764054006
            # Mode ( 0x00 Heat, 0x01 Coll, 0x02 Both) / Amount ( signed 8 bit int)
            self.log.logging( "inRawAPS", "Debug", "inRawAps - Cluster 0201 Command 00 (Setpoint Raise/Lower) Data %s" %Data)

        elif Command == "01":  # Set Weekly Schedule
            self.log.logging( "inRawAPS", "Debug", "inRawAps - Cluster 0201 Command 01 (Set Weekly Schedule) Data %s" %Data)

        elif Command == "02":  # Get weekly Schedule
            self.log.logging( "inRawAPS", "Debug", "inRawAps - Cluster 0201 Command 02 (Get weekly Schedule) Data %s" %Data)

        elif Command == "03":  # Clear Weekly schedule
            self.log.logging( "inRawAPS", "Debug", "inRawAps - Cluster 0201 Command 03 (Clear Weekly schedule) Data %s" %Data)

        elif Command == "04":  # Get Relay status Log
            self.log.logging( "inRawAPS", "Debug", "inRawAps - Cluster 0201 Command 04 (Get Relay status Log) Data %s" %Data)

    if "Manufacturer" not in self.ListOfDevices[srcnwkid]:
        return

    manuf = str(self.ListOfDevices[srcnwkid]["Manufacturer"]) if "Manufacturer" in self.ListOfDevices[srcnwkid] else ""
    manuf_name = self.ListOfDevices[srcnwkid]["Manufacturer Name"] if "Manufacturer Name" in self.ListOfDevices[srcnwkid] else ""

    self.log.logging( "inRawAPS", "Debug", "inRawAps Nwkid: %s Ep: %s Cluster: %s ManufCode: %s manuf: %s manuf_name: %s Cmd: %s Data: %s" % (
        srcnwkid, srcep, cluster, ManufacturerCode, manuf, manuf_name, Command, Data), srcnwkid, )

    func = None
    if manuf in CALLBACK_TABLE:
        func = CALLBACK_TABLE[manuf]

    elif manuf_name in CALLBACK_TABLE2:
        func = CALLBACK_TABLE2[manuf_name]

    elif tuya_manufacturer_device(self, srcnwkid):
        func = tuyaReadRawAPS

    else:
        self.log.logging( "inRawAPS", "Log", "inRawAps %s/%s Cluster %s Manuf: %s/%s Command: %s Data: %s Payload: %s not processed !!!" % (
            srcnwkid, srcep, cluster, manuf, manuf_name, Command, Data, payload), )

    if func:
        func(self, Devices, srcnwkid, srcep, cluster, dstnwkid, dstep, payload)


def handle_ias_ace_command(self, Devices, nwkid, ep, sqn, model_name, command, payload):
    """
    Handle IAS ACE (Intruder Alarm System - Arm Control Equipment) commands.
    """

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

    cmd_name = IAS_ACE_COMMANDS.get(command)
    self.log.logging("inRawAPS", "Log", f"IAS ACE Command: {command} ({cmd_name}) Payload: {payload}")

    if not cmd_name:
        self.log.logging("inRawAPS", "Warn", f"Unknown IAS ACE command: {command} - {payload}")
        return

    # Retrieve device configuration once
    is_ias_keyboard = get_deviceconf_parameter_value(self, model_name, "CIE_NOT_TRIGGER_ENROLMENT")

    # --- ARM Command ---
    if cmd_name == "Arm":
        _handle_arm_command(self, Devices, nwkid, ep, sqn, payload, is_ias_keyboard)

    elif cmd_name == "Emergency":
        MajDomoDevice(self, Devices, nwkid, ep, "0006", "01")

    elif cmd_name == "Get Panel Status":
        self.log.logging("inRawAPS", "Log", f"IAS ACE Get Panel Status {command} - {payload}")
        get_panel_status_response(self, Devices, nwkid, ep, sqn)

    else:
        self.log.logging("inRawAPS", "Warn", f"Unhandled IAS ACE command: {cmd_name} ({command}) Payload: {payload}")


def _handle_arm_command(self, Devices, nwkid, ep, sqn, payload, is_ias_keyboard):
    arm_mode = payload[:2]

    ARM_COMMANDS = {
        "00": "Disarm",
        "01": "ArmHome",
        "02": "ArmNight",
        "03": "ArmAllZones",
    }

    arm_desc = ARM_COMMANDS.get(arm_mode, "Unknown")
    self.log.logging("inRawAPS", "Log", f"IAS ACE Arm Command: {arm_mode} ({arm_desc}) Payload: {payload}")
    if is_ias_keyboard:
        _handle_ias_keyboard_arm(self, Devices, nwkid, ep, sqn, arm_mode, arm_desc, payload)
        return

    # Simplified dispatch for arm modes
    arm_actions = {
        "Disarm": ("0006", "04", "00"),
        "ArmHome": ("0006", "01", "01"),
        "ArmAllZones": ("0006", "03", "03"),
    }

    if arm_desc in arm_actions:
        cluster, value, notif_code = arm_actions[arm_desc]
        MajDomoDevice(self, Devices, nwkid, ep, cluster, value)
        arm_response(self, nwkid, ep, sqn, notif_code)


def _handle_ias_keyboard_arm(self, Devices, nwkid, ep, sqn, arm_mode, arm_desc, payload):
    """
    Handle IAS keypad 'Arm' commands with PIN code input.
    """
    EXIT_DELAY = 30  # seconds
    exit_delay = get_device_config_param(self, nwkid, "ARM_EXIT_DELAY") or EXIT_DELAY
    if "IAS_KEYPAD" not in self.ListOfDevices.get(nwkid, {}):
        self.ListOfDevices.setdefault(nwkid, {})["IAS_KEYPAD"] = {}

    decoded_code = _decode_kepzb_110_hex_string(payload[2:])

    self.ListOfDevices[nwkid]["IAS_KEYPAD"]["Last"] = {
        "TimeStamp": (time.time() + exit_delay),
        "LastArmMode": arm_mode,
        "LastArmModeDescription": arm_desc,
        "Code": decoded_code,
        "Sqn": sqn,
    }

    self.log.logging("inRawAPS", "Log", f"IAS Keyboard - {arm_mode} {arm_desc} {payload} Decoded PIN: {decoded_code} Last: {self.ListOfDevices[nwkid]['IAS_KEYPAD']['Last']}")

    text_message = f"{arm_desc},{decoded_code}"
    MajDomoDevice(self, Devices, nwkid, ep, "0501", text_message)

    if not _pin_code_valid(self, nwkid, decoded_code):
        self.log.logging("inRawAPS", "Warn", f"IAS Keyboard - Invalid PIN code for {arm_desc} {decoded_code} versus expected {get_device_config_param(self, nwkid, 'DISARM_PINCODE')}")
        arm_response(self, nwkid, ep, sqn, "04")  # InvalidCode
        return

    ARM_NOTIFICATION_RESPONSE = {
        "Disarm": "00",
        "ArmHome": "01",
        "ArmNight": "02",
        "ArmAllZones": "03",
        "InvalidCode": "04",
        "NotReady": "05",
        "AlreadyDiarmed": "06",
    }

    if arm_desc in ARM_NOTIFICATION_RESPONSE:
        arm_response(self, nwkid, ep, sqn, ARM_NOTIFICATION_RESPONSE[arm_desc])

def _pin_code_valid(self, nwkid, pin_code: str) -> bool:
    """
    Validate the PIN code.
    """
    disarm_pincode = get_device_config_param(self, nwkid, "DISARM_PINCODE")
    if disarm_pincode == "":
        return True  # No PIN code set, accept any code
    return False if disarm_pincode is None else pin_code == disarm_pincode


def _decode_kepzb_110_hex_string(hex_string: str) -> str:
    """
    Decode Develco KEYZB-110 keypad PIN payload.
    The first byte is the ASCII string length.
    """
    if not hex_string:
        return ""
    data = bytes.fromhex(hex_string)
    length = data[0]
    return data[1:1 + length].decode("ascii", errors="ignore")

    
def get_panel_status_response(self, Devices, nwkid, ep, sqn):
    """
    Handle IAS ACE Get Panel Status Response command.
    """
    panel_status = f"{_get_panel_status_from_widget(self, nwkid):02x}"
    seconds_remaining = _get_remaining_time(self, nwkid)
    audible_notification = "00"
    alarm_status = "00"
    
    payload = panel_status + seconds_remaining + audible_notification + alarm_status
    self.log.logging("inRawAPS", "Log", f"get_panel_status_response: Panel Status={panel_status} Payload={payload}")
    zcl_raw_get_panel_status_response( self, "01", ep, nwkid, sqn, payload )


def _get_remaining_time(self, nwkid):
    """
    Get remaining time for exit/entry delay from widget or memory.
    """
    now = time.time()
    second_remaining = int(now - self.ListOfDevices.get(nwkid, {}).get("IAS_KEYPAD", {}).get("Last", {}).get("TimeStamp", now))
    return f"{second_remaining:02x}"


def _get_panel_status_from_widget(self, nwkid):
    """
    Get current IAS panel status from widget or memory.
    """
    PANEL_STATUS = {
        "Disarm": 0x00,
        "ArmHome": 0x01,
        "ArmNight": 0x02,
        "ArmAllZones": 0x03,
        "ExitDelay": 0x04,
        "EntryDelay": 0x05,
        "NotReady": 0x06,
        "InAlarm": 0x07,
    }

    keypad_data = self.ListOfDevices.get(nwkid, {}).get("IAS_KEYPAD", {}).get("Current", {})
    return PANEL_STATUS.get(keypad_data.get("CurrentArmMode", "NotReady"), 0x06)


def arm_response(self, nwkid, ep, sqn, arm_notification_code):
    """Send IAS ACE Arm Response."""
    self.log.logging("inRawAPS", "Log", f"arm_response: {nwkid} - {arm_notification_code}")
    zcl_raw_arm_response(self, "01", ep, nwkid, sqn, arm_notification_code)
