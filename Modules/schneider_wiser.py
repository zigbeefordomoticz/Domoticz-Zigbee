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
    Module: schneider_wiser.py

    Description:

"""

import json
import os.path
import struct
from time import time

from Modules.basicOutputs import read_attribute, write_attribute
from Modules.bindings import WebBindStatus, webBind
from Modules.domoMaj import MajDomoDevice
from Modules.pluginDbAttributes import STORE_CONFIGURE_REPORTING
from Modules.readAttributes import ReadAttributeRequest_0001
from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import (checkAndStoreAttributeValue, get_and_inc_ZCL_SQN,
                           get_device_nickname, getAttributeValue,
                           is_ack_tobe_disabled,
                           retreive_cmd_payload_from_8002)
from Modules.writeAttributes import write_attribute_when_awake
from Modules.zigateConsts import MAX_LOAD_ZIGATE, ZIGATE_EP
from Zigbee.zclCommands import zcl_onoff_off_noeffect, zcl_onoff_on

SCHNEIDER_MANUF_ID = "105e"
SCHNEIDER_META_DATA = "Schneider"
WISER_LEGACY_MODEL_NAME_PREFIX = "EH-ZB"
WISER_LEGACY_BASE_EP = "0b"

ONOFF_CLUSTER = "0006"
ONOFF_STATUS = "0000"

METERING_CLUSTER = "0702"
INSTANT_POWER = "0400"

THERMOSTAT_CLUSTER = "0201"
LOCAL_TEMPERATURE = "0000"
PI_HEATING_DEMAND = "0008"
OCCUPIED_SETPOINT = "0012"
MIN_SETPOINT = "0015"
MAX_SETPOINT = "0016"
CONTROL_SEQUENCE_OPERATION = "001b"
SYSTEM_MODE = "001c"
SCHNEIDER_ZONE_MODE = "e010"

TARGET_SETPOINT = "Target SetPoint"
TIMESTAMP_SETPOINT = "TimeStamp SetPoint"
TARGET_MODE = "Target Mode"
TIMESTAMP_MODE = "TimeStamp Mode"

TEMPERATURE_CLUSTER = "0402"
TEMPERATURE_VALUE = "0000"

SCHNEIDER_SPECIFIC_PILOT_MODE_CLUSTER = "ff23"
PILOT_MODE_ATTRIBUTE = "0031"
PILOT_MODE_DATA_TYPE = "30"
DEFAULT_PILOT_MODE = 0x01  # Conventional mode (relay)
FIP_PILOT_MODE = 0x03

FAST_REPORTING_INTERVAL = 14 * 60  # 14 minutes

CONFIG_REPORTING_FAST = {
    "0000": {
        "Change": "0000ffffffffffff",
        "DataType": "25",
        "MaxInterval": "001E",
        "MinInterval": "001E",
        "TimeOut": "0000",
    },
    "0400": {
        "Change": "00000190",
        "DataType": "2a",
        "MaxInterval": "001E",
        "MinInterval": "001E",
        "TimeOut": "0000",
    },
    "0002": {
        "Change": "0000000000ffffff",
        "DataType": "25",
        "MaxInterval": "001E",
        "MinInterval": "001E",
        "TimeOut": "0000",
    },
}
CONFIG_REPORTING_NORMAL = {
    "0000": {
        "Change": "0000ffffffffffff",
        "DataType": "25",
        "MaxInterval": "0258",
        "MinInterval": "0258",
        "TimeOut": "0000",
    },
    "0400": {
        "Change": "00000190",
        "DataType": "2a",
        "MaxInterval": "0258",
        "MinInterval": "001E",
        "TimeOut": "0000",
    },
    "0002": {
        "Change": "0000000000ffffff",
        "DataType": "25",
        "MaxInterval": "0258",
        "MinInterval": "0258",
        "TimeOut": "0000",
    },
}
EHZBRTS_THERMO_MODE = {
    0: 0x00,
    10: 0x01,
    20: 0x02,
    30: 0x03,
    40: 0x04,
    50: 0x05,
    60: 0x06,
}


def pollingSchneider(self, key):
    # sourcery skip: inline-immediately-returned-variable

    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """

    rescheduleAction = False

    return rescheduleAction


def callbackDeviceAwake_Schneider(self, Devices, nwk_id, ep, cluster):
    """
    Called when receiving a message from a manufacturer battery-based device.
    This function is executed after processing the readCluster part.

    Parameters:
        Devices (dict): The list of known devices.
        nwk_id (str): Network ID of the device.
        ep (str): The endpoint identifier.
        cluster (str): The cluster ID.
    """

    #self.log.logging("Schneider", "Debug", f"callbackDeviceAwake_Schneider - NwkId: {nwk_id}, EndPoint: {ep}, cluster: {cluster}", nwk_id)

    # Direct function call for cluster Thermostat
    if cluster == THERMOSTAT_CLUSTER:
        callbackDeviceAwake_Schneider_SetPoints(self, nwk_id, ep, cluster)

    # Retrieve device details once to avoid redundant lookups
    device = self.ListOfDevices.get(nwk_id)
    if not device:
        return

    model = device.get("Model")

    # Handle "EH-ZB-VACT" Reporting Mode change
    schneider_data = device.get(SCHNEIDER_META_DATA)
    if (
        model == "EH-ZB-VACT" and schneider_data 
        and (schneider_data.get("ReportingMode") == "Fast" )
        and (schneider_data.get("Registration", 0) + FAST_REPORTING_INTERVAL) <= time()
    ):
        self.log.logging("Schneider", "Status", f"{nwk_id}/{ep} Switching Reporting to NORMAL mode")
        vact_config_reporting_normal(self, nwk_id, ep)

    # Handle override setpoint check for thermostats
    if model in ("Wiser2-Thermostat", "iTRV"):
        check_end_of_override_setpoint(self, Devices, nwk_id, ep)



def wiser_thermostat_monitoring_heating_demand(self, Devices):
    # Let check what is the Heating Demand
    updated_pi_demand = None

    for NwkId in list(self.ListOfDevices):
        device = self.ListOfDevices.get(NwkId, {})

        if (
            device.get("Model") != "Wiser2-Thermostat"
            or "Param" not in device
            or "WiserRoomNumber" not in device["Param"]
            or THERMOSTAT_CLUSTER not in device.get("Ep", {}).get("01", {})
        ):
            continue

        device["Ep"]["01"][THERMOSTAT_CLUSTER].setdefault(PI_HEATING_DEMAND, 0)

        # We have found a Wiser Thermostat
        thermostat_room_number = int(self.ListOfDevices[NwkId]["Param"]["WiserRoomNumber"])
        updated_pi_demand = 0
        cnt_actioners = 0

        # We need to find if there is any devices where this parameter is set and with the same value
        for x in list(self.ListOfDevices):
            if x == NwkId:
                continue
            if "Param" not in self.ListOfDevices[x]:
                continue
            if "WiserRoomNumber" not in self.ListOfDevices[x]["Param"]:
                continue
            if int(self.ListOfDevices[x]["Param"]["WiserRoomNumber"]) != thermostat_room_number:
                continue

            # We have a device which belongs to the same room
            for y in list(self.ListOfDevices[x]["Ep"]):
                if THERMOSTAT_CLUSTER in self.ListOfDevices[x]["Ep"][y]:
                    if PI_HEATING_DEMAND in self.ListOfDevices[x]["Ep"][y][THERMOSTAT_CLUSTER]:
                        # Pi Demand based on 0201 Cluster
                        updated_pi_demand += int(self.ListOfDevices[x]["Ep"][y][THERMOSTAT_CLUSTER][PI_HEATING_DEMAND])
                        cnt_actioners += 1

                    elif METERING_CLUSTER in self.ListOfDevices[x]["Ep"][y] and INSTANT_POWER in self.ListOfDevices[x]["Ep"][y][METERING_CLUSTER]:
                        # Mostlikely a FIP, then we check if there is some instant power or not
                        cnt_actioners += 1
                        if int(self.ListOfDevices[x]["Ep"][y][METERING_CLUSTER][INSTANT_POWER]) > 0:
                            updated_pi_demand += 100

                elif ONOFF_CLUSTER in self.ListOfDevices[x]["Ep"][y]:
                    # It is a simple ON/Off
                    if ONOFF_STATUS in self.ListOfDevices[x]["Ep"][y][ONOFF_CLUSTER]:
                        cnt_actioners += 1
                        if int(self.ListOfDevices[x]["Ep"][y][ONOFF_CLUSTER][ONOFF_STATUS]):
                            updated_pi_demand += 100

        if cnt_actioners:
            pi_demand = int(round(updated_pi_demand / cnt_actioners))
            self.ListOfDevices[NwkId]["Ep"]["01"][THERMOSTAT_CLUSTER][PI_HEATING_DEMAND] = pi_demand
            MajDomoDevice( self, Devices, NwkId, "01", THERMOSTAT_CLUSTER, pi_demand, Attribute_=PI_HEATING_DEMAND, )


def callbackDeviceAwake_Schneider_SetPoints(self, NwkId, EndPoint, cluster):

    self.log.logging("Schneider", "Debug", f"callbackDeviceAwake_Schneider_SetPoints - Nwkid: {NwkId}, EndPoint: {EndPoint}, cluster: {cluster}", NwkId)

    # Retrieve device once to avoid redundant lookups
    device = self.ListOfDevices.get(NwkId)

    # Ensure the device exists, has the correct model, and contains the expected cluster
    if not device or device.get("Model") != "EH-ZB-VACT" or THERMOSTAT_CLUSTER not in device.get("Ep", {}).get(EndPoint, {}):
        return

    # Manage SetPoint
    now = time()
    ep_data = device.get("Ep", {}).get(EndPoint, {})
    thermostat_cluster_data = ep_data.get(THERMOSTAT_CLUSTER, {})
    schneider_data = device.get(SCHNEIDER_META_DATA, {})
    
    if OCCUPIED_SETPOINT in thermostat_cluster_data:
        schneider_data = self.ListOfDevices.setdefault(NwkId, {}).setdefault(SCHNEIDER_META_DATA, {})
        target_setpoint = schneider_data.get(TARGET_SETPOINT)
        timestamp_setpoint = schneider_data.get(TIMESTAMP_SETPOINT)
        if target_setpoint is not None:
            if timestamp_setpoint is None:
                schneider_setpoint(self, NwkId, target_setpoint, call_back=True)
            elif (
                target_setpoint != int(self.ListOfDevices[NwkId]["Ep"][EndPoint][THERMOSTAT_CLUSTER][OCCUPIED_SETPOINT])
                and now > (timestamp_setpoint + 15)
            ):
                self.log.logging("Schneider", "Debug", "callbackDeviceAwake_Schneider_SetPoints - time to send a setpoint command", NwkId)
                schneider_setpoint(self, NwkId, target_setpoint, call_back=True)

    # Manage Zone Mode
    if SCHNEIDER_ZONE_MODE in thermostat_cluster_data and TARGET_MODE in schneider_data:
        target_mode = schneider_data.get(TARGET_MODE)
        timestamp_mode = schneider_data.get(TIMESTAMP_MODE)
        current_mode = int(self.ListOfDevices[NwkId]["Ep"][EndPoint][THERMOSTAT_CLUSTER][SCHNEIDER_ZONE_MODE], 16)

        if target_mode is not None:
            desired_mode = EHZBRTS_THERMO_MODE.get(target_mode)

            if desired_mode == current_mode:
                schneider_data[TARGET_MODE] = None
                schneider_data[TIMESTAMP_MODE] = None
            elif timestamp_mode is not None and now > (timestamp_mode + 15):
                schneider_EHZBRTS_thermoMode(self, NwkId, target_mode)


def schneider_wiser_registration(self, Devices, key):
    """
    This method is called during the pairing/discovery process.
    Purpose is to do some initialisation (write) on the coming device.
    """
    self.log.logging("Schneider", "Debug", f"schneider_wiser_registration for device {key}", nwkid=key)


    if "Model" in self.ListOfDevices[key] and self.ListOfDevices[key]["Model"] in ("iTRV",):
        iTRV_registration(self, key)
        wiser_home_lockout_thermostat(self, key, 0)

    if "Model" in self.ListOfDevices[key] and self.ListOfDevices[key]["Model"] in ("Wiser2-Thermostat",):
        wiser_home_lockout_thermostat(self, key, 0)

    if SCHNEIDER_META_DATA not in self.ListOfDevices[key]:
        self.ListOfDevices[key][SCHNEIDER_META_DATA] = {}
    self.ListOfDevices[key][SCHNEIDER_META_DATA]["Registration"] = int(time())

    # nwkid might have changed so we need to reload the zoning
    self.SchneiderZone = None
    importSchneiderZoning(self)

    EPout = WISER_LEGACY_BASE_EP

    if "Model" not in self.ListOfDevices[key]:
        _context = {"Error code": "SCHN0001", "Device": self.ListOfDevices[key]}
        self.log.logging("Schneider", "Error", "Undefined Model, registration !!!", key, _context)
        return

    # Set Commissioning as Done 0x0000/0xe050 (Manuf Specific)
    wiser_set_commission_done(self, key, EPout)

    if self.ListOfDevices[key]["Model"] in ("EH-ZB-VACT"):  # Thermostatic Valve
        # Config file is based on a Fast Reporting mode.
        self.ListOfDevices[key][SCHNEIDER_META_DATA]["ReportingMode"] = "Fast"

    # Set 0x00 to 0x0201/0xe013 : ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_THRESHOLD
    if self.ListOfDevices[key]["Model"] in ("EH-ZB-VACT"):  # Thermostatic Valve
        wiser_set_thermostat_window_detection(self, key, EPout, 0x00)

    # Set 0x00 to 0x0201/0x0010 : Local Temperature Calibration
    if self.ListOfDevices[key]["Model"] in ("EH-ZB-HACT", "EH-ZB-VACT"):  # Actuator, Valve
        wiser_set_calibration(self, key, EPout)

    # ATTRIBUTE_THERMOSTAT_ZONE_MODE ( 0xe010 )
    if self.ListOfDevices[key]["Model"] in ("EH-ZB-HACT", "EH-ZB-VACT"):  # Actuator, Valve
        wiser_set_zone_mode(self, key, EPout)

    # Write Location to 0x0000/0x5000 for all devices
    wiser_set_location(self, key, EPout)

    # Set Language to en
    if self.ListOfDevices[key]["Model"] in ("EH-ZB-RTS",):  # Thermostat
        wiser_set_lang(self, key, EPout, "en")

    # Set default Thermostat temp
    if self.ListOfDevices[key]["Model"] in ("EH-ZB-RTS", "EH-ZB-VACT"):  # Thermostat
        cluster_id = "%04x" % 0x0201
        Hattribute = "%04x" % 0x0012
        default_temperature = 2000
        setpoint = schneider_find_attribute_and_set(self, key, EPout, cluster_id, Hattribute, default_temperature)
        schneider_update_ThermostatDevice(self, Devices, key, EPout, cluster_id, setpoint)

    # Bind thermostat if needed
    if self.ListOfDevices[key]["Model"] in ("EH-ZB-RTS",):  # Thermostat
        schneider_thermostat_check_and_bind(self, key)

    # set fip mode if nothing and dont touch if already exists
    if self.ListOfDevices[key]["Model"] in ("EH-ZB-HACT"):  # Actuator
        schneider_hact_heater_type(self, key, "registration")
        schneider_actuator_check_and_bind(self, key)

    # BMS: current monitoring systemlets initialize the alarm widget to 00
    if self.ListOfDevices[key]["Model"] == "EH-ZB-BMS":
        cluster_id = "%04x" % 0x0009
        value = "00"
        self.log.logging("Schneider", "Debug", f"Schneider update Alarm Domoticz device Attribute {key} Endpoint:{EPout} / cluster: {cluster_id} to {value}", nwkid=key)

        MajDomoDevice(self, Devices, key, EPout, cluster_id, value)

    # Pilotage Chauffe eau
    if self.ListOfDevices[key]["Model"] in ("EH-ZB-LMACT"):
        #sendZigateCmd(self, "0092", "02" + key + ZIGATE_EP + EPout + "00")
        zcl_onoff_off_noeffect(self, key, EPout)
        #sendZigateCmd(self, "0092", "02" + key + ZIGATE_EP + EPout + "01")
        zcl_onoff_on(self, key, EPout)

    # Redo Temp
    if self.ListOfDevices[key]["Model"] in ("EH-ZB-VACT"):  # Actuator, Valve
        wiser_set_calibration(self, key, EPout)
    self.ListOfDevices[key]["Heartbeat"] = "0"
    
    
def wiser_set_zone_mode(self, key, EPout):  # 0x0201/0xe010

    # Set 0x0201/0xe010
    # 0x01 User Mode Manual
    # 0x02 User Mode Schedule
    # 0x03 User Mode Manual Energy Saver

    manuf_id = "0000"  # Not a manufacturer specific with VACT <-> HUB
    manuf_spec = "00"

    cluster_id = "%04x" % 0x0201
    Hattribute = "%04x" % 0xE010
    data_type = "30"
    data = "01"
    self.log.logging("Schneider", "Debug", f"Schneider Write Attribute (zone_mode) {key} with value {data} / cluster: {cluster_id}, attribute: {Hattribute} type: {data_type}", nwkid=key)

    write_attribute(
        self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )


def wiser_set_location(self, key, EPout):  # 0x0000/0x0010
    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" % 0x0000
    Hattribute = "%04x" % 0x0010
    data_type = "42"
    data = "Zigate zone".encode("utf-8").hex()  # Zigate zone
    self.log.logging("Schneider", "Debug", f"Schneider Write Attribute (zone name) {key} with value {data} / cluster: {cluster_id}, attribute: {Hattribute} type: {data_type}", nwkid=key)

    write_attribute(
        self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )


def wiser_set_calibration(self, key, EPout):  # 0x0201/0x0010
    #  This is used to set the Local Temperature Calibration ( specifies  the  offset  that  can  be  added/subtracted  to  the  actual displayed room temperature )
    calibration = 0

    if (
        "Param" in self.ListOfDevices[key]
        and "Calibration" in self.ListOfDevices[key]["Param"]
        and isinstance(self.ListOfDevices[key]["Param"]["Calibration"], (float, int))
    ):
        calibration = int(10 * self.ListOfDevices[key]["Param"]["Calibration"])

    if SCHNEIDER_META_DATA not in self.ListOfDevices[key]:
        self.ListOfDevices[key][SCHNEIDER_META_DATA] = {}

    if (
        "Calibration" in self.ListOfDevices[key][SCHNEIDER_META_DATA]
        and calibration == 10 * self.ListOfDevices[key][SCHNEIDER_META_DATA]["Calibration"]
    ):
        return

    if calibration < -25:
        calibration = -24
    if calibration > 25:
        calibration = 24

    if calibration < 0:
        # in two’s complement form
        calibration = int(hex(-calibration - pow(2, 32))[9:], 16)

    self.log.logging( "Schneider", "Log", "Calibration: 0x%02x" % calibration)

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" % 0x0201
    Hattribute = "%04x" % 0x0010
    data_type = "28"
    data = "%02x" % calibration

    self.log.logging(
        "Schneider",
        "Debug",
        "wiser_set_calibration Schneider Write Attribute (no Calibration) %s with value %s / cluster: %s, attribute: %s type: %s"
        % (key, data, cluster_id, Hattribute, data_type),
        nwkid=key,
    )
    write_attribute(
        self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )
    read_attribute(
        self, key, ZIGATE_EP, EPout, cluster_id, "00", manuf_spec, manuf_id, 1, Hattribute, ackIsDisabled=False
    )


def wiser_set_thermostat_window_detection(self, key, EPout, Mode):  # 0x0201/0xe013
    # 0x00  After a first Pairing
    # 0x04  After 15' or a restat of the HUB

    cluster_id = "%04x" % 0x0201
    manuf_id = "0000"
    manuf_spec = "00"
    Hattribute = "%04x" % 0xE013
    data_type = "20"

    data = "%02x" % Mode
    self.log.logging("Schneider", "Debug", f"wiser_set_thermostat_window_detection - Schneider Write Attribute {key} with value {data} / cluster: {cluster_id}, attribute: {Hattribute} type: {data_type}", nwkid=key)

    write_attribute(
        self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )


def wiser_set_commission_done(self, key, EPout):  # 0x0000/0xE050
    manuf_id = SCHNEIDER_MANUF_ID
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0000
    Hattribute = "%04x" % 0xE050
    data_type = "10"  # Bool
    data = "%02x" % 1
    self.log.logging("Schneider", "Debug", f"wiser_set_commission_done Schneider Write Attribute (commisionning done) {key} with value {data} / Endpoint : {EPout}, cluster: {cluster_id}, attribute: {Hattribute} type: {data_type}", nwkid=key)

    write_attribute(
        self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )


def wiser_set_lang(self, key, EPout, lang="eng"):  # 0x0000/0x5011
    manuf_id = SCHNEIDER_MANUF_ID
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0000
    Hattribute = "%04x" % 0x5011
    data_type = "42"  # String
    data = lang.encode("utf-8").hex()  # 'en'
    self.log.logging("Schneider", "Debug", f"wiser_set_lang Schneider Write Attribute (Lang) {key} with value {data} / cluster: {cluster_id}, attribute: {Hattribute} type: {data_type}", nwkid=key)

    write_attribute(
        self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )


def iTRV_registration(self, NwkId):
    manuf_id = SCHNEIDER_MANUF_ID
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0201
    Hattribute = "%04x" % 0xE103
    data_type = "10"  # Bool
    data = "01"
    self.log.logging("Schneider", "Debug", f"iTRV_registration Schneider Write Attribute {NwkId}", nwkid=NwkId)

    write_attribute(
        self, NwkId, ZIGATE_EP, "01", cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )


def wiser_set_thermostat_default_temp(self, Devices, key, EPout):  # 0x0201/0x0012
    cluster_id = "%04x" % 0x0201
    Hattribute = "%04x" % 0x0012
    default_temperature = 2000
    setpoint = schneider_find_attribute_and_set(self, key, EPout, cluster_id, Hattribute, default_temperature)
    schneider_update_ThermostatDevice(self, Devices, key, EPout, cluster_id, setpoint)


def schneider_hact_heater_type(self, key, type_heater):

    model_name = self.ListOfDevices[key].get("Model")
    if model_name == "EH-ZB-HACT":
        return schneider_hact_heater_type_wiser1(self, key, type_heater)
    if model_name == "CCTFR6700":
        return schneider_hact_heater_type_wiser2(self, key, type_heater)
    _context = {"Error code": "SCHN0004", "model_name": model_name, 'type_heater': type_heater}
    self.log.logging( "Schneider", "Error", "schneider_hact_heater_type - %s unknown model %s" % (key, model_name), key, _context )


def schneider_hact_heater_type_wiser1(self, key, type_heater):
    """[summary]
         allows to set the heater in "fip" or "conventional" mode
         by default it will set it to fip mode
    Arguments:
        key {[int]} -- id of the device
        type {[string]} -- type of heater "fip" of "conventional"
    """
    EPout = WISER_LEGACY_BASE_EP

    attrValue = getAttributeValue(self, key, EPout, THERMOSTAT_CLUSTER, "e011")
    if attrValue is not None:
        current_value = int(attrValue, 16)
        force_update = False
    else:
        current_value = 0x82
        force_update = True

    # value received is :
    # bit 0 - mode of heating  : 0 is setpoint, 1 is fip mode
    # bit 1 - mode of heater : 0 is conventional heater, 1 is fip enabled heater
    # for validation , 0x80 is added to he value retrived from HACT

    current_value -= 0x80
    if type_heater == "conventional":
        new_value = current_value & 0xFD  # we set the bit 1 to 0 and dont touch the other ones . logical_AND 1111 1101
    elif type_heater in ("fip", "FIP"):
        new_value = current_value | 2  # we set the bit 1 to 1 and dont touch the other ones . logical_OR 0000 0010
    else:
        # Registration or unknown mode
        new_value = current_value


    new_value = new_value & 3  # cleanup, to remove everything else but the last two bits
    if (current_value == new_value) and not force_update:  # no change, let's get out
        return

    manuf_id = SCHNEIDER_MANUF_ID
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0201
    Hattribute = "%04x" % 0xE011
    data_type = "18"
    data = "%02X" % new_value
    self.log.logging(
        "Schneider",
        "Debug",
        "schneider_hact_heater_type Write Attribute (heating mode) %s with value %s / cluster: %s, attribute: %s type: %s"
        % (key, data, cluster_id, Hattribute, data_type),
        nwkid=key,
    )
    write_attribute(
        self,
        key,
        ZIGATE_EP,
        EPout,
        cluster_id,
        manuf_id,
        manuf_spec,
        Hattribute,
        data_type,
        data,
        ackIsDisabled=is_ack_tobe_disabled(self, key),
    )

    if EPout in self.ListOfDevices[key]["Ep"] and THERMOSTAT_CLUSTER in self.ListOfDevices[key]["Ep"][EPout]:
        self.ListOfDevices[key]["Ep"][EPout][THERMOSTAT_CLUSTER]["e011"] = "%02x" % (new_value + 0x80)



def schneider_hact_heater_type_wiser2(self, nwkid: str, type_heater: str) -> None:
    """
    Configure the pilot mode for a Schneider HACT heater via Wiser2.

    Parameters:
        self: Reference to the class instance.
        key (str): Unique identifier for the device.
        type_heater (str): Type of heater mode to set. Accepted values:
            - "conventional": Sets pilot mode to 0x01 (Relay mode).
            - "fip" or "FIP": Sets pilot mode to 0x03 (FIP mode).
    """

    # Determine the correct pilot mode
    pilot_mode = FIP_PILOT_MODE if type_heater.lower() == "fip" else DEFAULT_PILOT_MODE
    self.log.logging( "Schneider", "Debug", "Determined pilot_mode: %s", hex(pilot_mode), nwkid=nwkid )

    # Write the attribute to configure the heater
    self.log.logging(
        "Schneider",
        "Debug",
        "Writing attribute with params: CLUSTER=%s, MANUF_ID=%s, ATTRIBUTE=%s, DATA_TYPE=%s, VALUE=%s",
        SCHNEIDER_SPECIFIC_PILOT_MODE_CLUSTER, SCHNEIDER_MANUF_ID, PILOT_MODE_ATTRIBUTE, PILOT_MODE_DATA_TYPE, hex(pilot_mode),
        nwkid=nwkid)

    write_attribute(
        self,
        nwkid,
        ZIGATE_EP,
        "01",
        SCHNEIDER_SPECIFIC_PILOT_MODE_CLUSTER,
        SCHNEIDER_MANUF_ID,
        "01",
        PILOT_MODE_ATTRIBUTE,
        PILOT_MODE_DATA_TYPE,
        pilot_mode,
        ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
    )
    self.log.logging( "Schneider", "Debug", "Attribute write completed for key=%s", nwkid )


def schneider_hact_heating_mode(self, key, mode):
    """
    Allow switching between "setpoint" and "FIP" mode
    Set 0x0201/0xe011
    HAC into Fil Pilot FIP 0x03, in Covential Mode 0x00
    """

    MODE = {"setpoint": 0x02, "FIP": 0x03}

    self.log.logging(
        "Schneider", "Debug", "schneider_hact_heating_mode for device %s requesting mode: %s" % (key, mode), nwkid=key
    )
    if mode not in MODE:
        _context = {"Error code": "SCHN0002", "mode": mode, "MODE": MODE}
        self.log.logging(
            "Schneider", "Error", "schneider_hact_heating_mode - %s unknown mode %s" % (key, mode), key, _context
        )
        return

    EPout = WISER_LEGACY_BASE_EP

    attrValue = getAttributeValue(self, key, EPout, THERMOSTAT_CLUSTER, "e011")
    if attrValue is not None:
        current_value = int(attrValue, 16)
        force_update = False
    else:
        current_value = 0x82
        force_update = True

    # value received is:
    # bit 0 - mode of heating  : 0 is setpoint, 1 is fip mode
    # bit 1 - mode of heater : 0 is conventional heater, 1 is fip enabled heater
    # for validation , 0x80 is added to he value retrived from HACT

    current_value -= 0x80
    if mode == "setpoint":
        new_value = current_value & 0xFE  # we set the bit 0 to 0 and dont touch the other ones . logical_AND 1111 1110

    elif mode in ("fip", "FIP"):
        new_value = current_value | 1  # we set the bit 0 to 1 and dont touch the other ones . logical_OR 0000 0001

    new_value = new_value & 3  # cleanup, to remove everything else but the last two bits
    if (current_value == new_value) and not force_update:  # no change, let's get out
        return

    manuf_id = SCHNEIDER_MANUF_ID
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0201
    Hattribute = "%04x" % 0xE011
    data_type = "18"
    data = "%02X" % new_value
    self.log.logging(
        "Schneider",
        "Debug",
        "schneider_hact_heating_mode Write Attribute (heating mode) %s with value %s / cluster: %s, attribute: %s type: %s"
        % (key, data, cluster_id, Hattribute, data_type),
        nwkid=key,
    )
    write_attribute(
        self,
        key,
        ZIGATE_EP,
        EPout,
        cluster_id,
        manuf_id,
        manuf_spec,
        Hattribute,
        data_type,
        data,
        ackIsDisabled=is_ack_tobe_disabled(self, key),
    )
    # Reset Heartbeat in order to force a ReadAttribute when possible
    self.ListOfDevices[key]["Heartbeat"] = "0"
    # ReadAttributeRequest_0201(self,key)
    if EPout in self.ListOfDevices[key]["Ep"]:
        if THERMOSTAT_CLUSTER in self.ListOfDevices[key]["Ep"][EPout]:
            self.ListOfDevices[key]["Ep"][EPout][THERMOSTAT_CLUSTER]["e011"] = "%02x" % (new_value + 0x80)


def schneider_hact_fip_mode(self, key, mode):
    """[summary]
        set fil pilote mode for the actuator
    Arguments:
        key {[int]} -- id of actuator
        mode {[string]} -- 'Confort' , 'Confort -1' , 'Confort -2', 'Eco', 'Frost Protection', 'Off'
    """
    # APS Data: 0x00 0x0b 0x01 0x02 0x04 0x01 0x0b 0x45 0x11 0xc1 0xe1 0x00 0x01 0x03

    MODE = {"Confort": 0x00, "Confort -1": 0x01, "Confort -2": 0x02, "Eco": 0x03, "Frost Protection": 0x04, "Off": 0x05}

    self.log.logging("Schneider", "Debug", f"schneider_hact_fip_mode for device {key} requesting mode: {mode}", key)


    if mode not in MODE:
        _context = {"Error code": "SCHN0003", "mode": mode, "MODE": MODE}
        self.log.logging("Schneider", "Error", f"schneider_hact_fip_mode - {key} unknown mode: {mode}", key, _context)


    EPout = WISER_LEGACY_BASE_EP

    schneider_hact_heating_mode(self, key, "FIP")

    cluster_frame = "11"
    sqn = get_and_inc_ZCL_SQN(self, key)
    cmd = "e1"

    zone_mode = "01"  # Heating
    fipmode = "%02X" % MODE[mode]
    prio = "01"  # Prio

    payload = cluster_frame + sqn + cmd + zone_mode + fipmode + prio + "ff"

    self.log.logging("Schneider", "Debug", f"schneider_hact_fip_mode for device {key} sending command: {cmd} , zone_monde: {zone_mode}, fipmode: {fipmode}", key)


    raw_APS_request(
        self, key, EPout, THERMOSTAT_CLUSTER, "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=is_ack_tobe_disabled(self, key)
    )
    # Reset Heartbeat in order to force a ReadAttribute when possible
    self.ListOfDevices[key]["Heartbeat"] = "0"


def schneider_thermostat_check_and_bind(self, key, forceRebind=False):
    """bind the thermostat to the actuators based on the zoning json fie
    Arguments:
        key {[type]} -- [description]
    """
    self.log.logging("Schneider", "Debug", f"schneider_thermostat_check_and_bind : {key} ", key)


    importSchneiderZoning(self)
    if self.SchneiderZone is None:
        return

    Cluster_bind1 = THERMOSTAT_CLUSTER
    Cluster_bind2 = TEMPERATURE_CLUSTER
    for zone in self.SchneiderZone:
        if self.SchneiderZone[zone]["Thermostat"]["NWKID"] != key:
            continue

        for hact in self.SchneiderZone[zone]["Thermostat"]["HACT"]:

            if hact not in self.ListOfDevices:
                continue

            srcIeee = self.SchneiderZone[zone]["Thermostat"]["IEEE"]
            targetIeee = self.SchneiderZone[zone]["Thermostat"]["HACT"][hact]["IEEE"]
            statusBind1 = WebBindStatus(
                self, srcIeee, WISER_LEGACY_BASE_EP, targetIeee, WISER_LEGACY_BASE_EP, Cluster_bind1
            )

            if not (statusBind1 == "requested"):
                if (statusBind1 != "binded") or forceRebind:
                    webBind(self, srcIeee, WISER_LEGACY_BASE_EP, targetIeee, WISER_LEGACY_BASE_EP, Cluster_bind1)
                    webBind(self, targetIeee, WISER_LEGACY_BASE_EP, srcIeee, WISER_LEGACY_BASE_EP, Cluster_bind1)

            statusBind2 = WebBindStatus(
                self, srcIeee, WISER_LEGACY_BASE_EP, targetIeee, WISER_LEGACY_BASE_EP, Cluster_bind2
            )
            if not (statusBind2 == "requested"):
                if (statusBind2 != "binded") or forceRebind:
                    webBind(self, srcIeee, WISER_LEGACY_BASE_EP, targetIeee, WISER_LEGACY_BASE_EP, Cluster_bind2)
                    webBind(self, targetIeee, WISER_LEGACY_BASE_EP, srcIeee, WISER_LEGACY_BASE_EP, Cluster_bind2)


def schneider_actuator_check_and_bind(self, key, forceRebind=False):
    """[summary]
        bind the actuators to the thermostat based on the zoning json fie
    Arguments:
        key {[type]} -- [description]
    """
    self.log.logging("Schneider", "Debug", f"schneider_actuator_check_and_bind : {key} ", key)


    importSchneiderZoning(self)
    if self.SchneiderZone is None:
        return

    Cluster_bind1 = THERMOSTAT_CLUSTER
    Cluster_bind2 = TEMPERATURE_CLUSTER
    for zone in self.SchneiderZone:
        for hact in self.SchneiderZone[zone]["Thermostat"]["HACT"]:
            if hact != key:
                continue

            thermostat_key = self.SchneiderZone[zone]["Thermostat"]["NWKID"]
            if thermostat_key not in self.ListOfDevices:
                continue

            srcIeee = self.SchneiderZone[zone]["Thermostat"]["HACT"][hact]["IEEE"]
            targetIeee = self.SchneiderZone[zone]["Thermostat"]["IEEE"]
            statusBind1 = WebBindStatus(
                self, srcIeee, WISER_LEGACY_BASE_EP, targetIeee, WISER_LEGACY_BASE_EP, Cluster_bind1
            )
            if not (statusBind1 == "requested"):
                if (statusBind1 != "binded") or forceRebind:
                    webBind(self, srcIeee, WISER_LEGACY_BASE_EP, targetIeee, WISER_LEGACY_BASE_EP, Cluster_bind1)
                    webBind(self, targetIeee, WISER_LEGACY_BASE_EP, srcIeee, WISER_LEGACY_BASE_EP, Cluster_bind1)

            statusBind2 = WebBindStatus(
                self, srcIeee, WISER_LEGACY_BASE_EP, targetIeee, WISER_LEGACY_BASE_EP, Cluster_bind2
            )
            if not (statusBind2 == "requested"):
                if (statusBind2 != "binded") or forceRebind:
                    webBind(self, srcIeee, WISER_LEGACY_BASE_EP, targetIeee, WISER_LEGACY_BASE_EP, Cluster_bind2)
                    webBind(self, targetIeee, WISER_LEGACY_BASE_EP, srcIeee, WISER_LEGACY_BASE_EP, Cluster_bind2)


def schneider_setpoint_thermostat(self, key, setpoint):
    """[summary]
        called from domoticz device when user change setpoint
        update internal value about the current setpoint value of thermostat , we need it to answer the thermostat when it will ask for it
        update the actuators that are linked to this thermostat based on the zoning json file.
        updating linked actuatorswon't apply to vact as it is a thermostat and an actuator
    Arguments:
        key {[type]} -- [description]
        setpoint {[type]} -- [description]
    """
    # SetPoint is in centidegrees

    EPout = WISER_LEGACY_BASE_EP
    if "Model" in self.ListOfDevices[key] and self.ListOfDevices[key]["Model"] in ("Wiser2-Thermostat", "iTRV"):
        EPout = "01"

    ClusterID = THERMOSTAT_CLUSTER
    attr = OCCUPIED_SETPOINT
    NWKID = key

    if "Model" in self.ListOfDevices[key] and self.ListOfDevices[key]["Model"] not in ( "EH-ZB-VACT", ):
        schneider_find_attribute_and_set(self, NWKID, EPout, ClusterID, attr, OCCUPIED_SETPOINT, setpoint)

    importSchneiderZoning(self)
    schneider_thermostat_check_and_bind(self, NWKID)

    if self.SchneiderZone is not None:
        for zone in self.SchneiderZone:
            self.log.logging("Schneider", "Debug", f"schneider_setpoint - Zone Information: {zone} ", NWKID)

            if self.SchneiderZone[zone]["Thermostat"]["NWKID"] == NWKID:
                self.log.logging("Schneider", "Debug", f"schneider_setpoint - found {zone} ", NWKID)

                for hact in self.SchneiderZone[zone]["Thermostat"]["HACT"]:
                    self.log.logging("Schneider", "Debug", f"schneider_setpoint - found hact {hact} ", NWKID)

                    schneider_setpoint_actuator(self, hact, setpoint)
                    # Reset Heartbeat in order to force a ReadAttribute when possible
                    self.ListOfDevices[key]["Heartbeat"] = "0"
                    schneider_actuator_check_and_bind(self, hact)
                    # ReadAttributeRequest_0201(self,key)

def schneider_setpoint_actuator(self, key, setpoint,send_command=True):
    """[summary]
        send new setpoint to actuators via an e0 command with the new setpoint value
        it is called
        - via schneider_setpoint_thermostat when actuators are linked to a thermostat
        - or schneider awake when a vact woke up and we had a setpoint setting pending

    Arguments:
        key {[type]} -- [description]
        setpoint {[int]} -- [description]
    """
    # SetPoint 2100 (21 degree C) => 0x0834
    # APS Data: 0x00 0x0b 0x01 0x02 0x04 0x01 0x0b 0x45 0x11 0xc1 0xe0 0x00 0x01 0x34 0x08 0xff
    #                                                                            |---------------> LB HB Setpoint
    #                                                             |--|---------------------------> Command 0xe0
    #                                                        |--|--------------------------------> SQN
    #                                                   |--|-------------------------------------> Cluster Frame

    if key not in self.ListOfDevices:
        self.log.logging("Schneider", "Debug", f"schneider_setpoint_actuator - unknown key: {key} in ListOfDevices!")

        return

    cluster_frame = "11"
    sqn = "00"

    EPout = "01"
    for tmpEp in self.ListOfDevices[key]["Ep"]:
        if THERMOSTAT_CLUSTER in self.ListOfDevices[key]["Ep"][tmpEp]:
            EPout = tmpEp
    sqn = get_and_inc_ZCL_SQN(self, key)

    cmd = "e0"

    setpoint = int((setpoint * 2) / 2)  # Round to 0.5 degrees
    if SCHNEIDER_META_DATA not in self.ListOfDevices[key]:
        self.ListOfDevices[key][SCHNEIDER_META_DATA] = {}
    self.ListOfDevices[key][SCHNEIDER_META_DATA]["Target SetPoint"] = setpoint
    self.ListOfDevices[key][SCHNEIDER_META_DATA][TIMESTAMP_SETPOINT] = int(time())

    # Make sure that we are in setpoint Mode
    if "Model" in self.ListOfDevices[key] and self.ListOfDevices[key]["Model"] == "EH-ZB-HACT":
        schneider_hact_heating_mode(self, key, "setpoint")

    if not send_command:
        return
    
    setpoint = "%04X" % setpoint
    zone = "01"

    payload = cluster_frame + sqn + cmd + "00" + zone + setpoint[2:4] + setpoint[:2] + "ff"

    raw_APS_request( self, key, EPout, THERMOSTAT_CLUSTER, "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=is_ack_tobe_disabled(self, key) )
    # Reset Heartbeat in order to force a ReadAttribute when possible
    self.ListOfDevices[key]["Heartbeat"] = "0"
    self.ListOfDevices[key]["Heartbeat"] = "0"


def schneider_setpoint(self, NwkId, setpoint, call_back=False):

    if NwkId not in self.ListOfDevices:
        self.log.logging("Schneider", "Debug", f"schneider_setpoint - unknown NwkId: {NwkId} in ListOfDevices!")
        return

    if "Model" in self.ListOfDevices[NwkId]:
        if self.ListOfDevices[NwkId]["Model"] == "EH-ZB-VACT":
            self.log.logging("Schneider", "Debug", f"schneider_setpoint - Call_Back : {call_back} setpoint {setpoint} for {NwkId} model EH-ZB-VACT")
            
            wiser_set_calibration(self, NwkId, WISER_LEGACY_BASE_EP)
            #schneider_setpoint_thermostat(self, NwkId, setpoint)
            schneider_setpoint_actuator(self, NwkId, setpoint, send_command=call_back)
            return
        
        if self.ListOfDevices[NwkId]["Model"] in ("EH-ZB-RTS", "Wiser2-Thermostat", ):
            schneider_setpoint_thermostat(self, NwkId, setpoint)
            return
        
        if self.ListOfDevices[NwkId]["Model"] == "iTRV": 
            cancel_override_attribute( self, NwkId )
            schneider_setpoint_thermostat(self, NwkId, setpoint)   
            return
            
        wiser_set_calibration(self, NwkId, WISER_LEGACY_BASE_EP)
        schneider_setpoint_actuator(self, NwkId, setpoint)


def schneider_temp_Setcurrent(self, key, setpoint):
    # SetPoint 2100 (21 degree C) => 0x0834
    # APS Data: 0x00 0x0b 0x01 0x02 0x04 0x01 0x0b 0x45 0x11 0xc1 0xe0 0x00 0x01 0x34 0x08 0xff
    #                                                                            |---------------> LB HB Setpoint
    #                                                             |--|---------------------------> Command 0xe0
    #                                                        |--|--------------------------------> SQN
    #                                                   |--|-------------------------------------> Cluster Frame

    if key not in self.ListOfDevices:
        self.log.logging("Schneider", "Debug", f"schneider_temp_Setcurrent - unknown key: {key} in ListOfDevices!")

        return

    cluster_frame = "18"
    attr = "0000"
    sqn = "00"
    data_type = "29"
    sqn = get_and_inc_ZCL_SQN(self, key)

    cmd = "0a"

    setpoint = int((setpoint * 2) / 2)  # Round to 0.5 degrees
    setpoint = "%04X" % setpoint

    payload = cluster_frame + sqn + cmd + attr + data_type + setpoint[2:4] + setpoint[:2]


    EPout = "01"
    for tmpEp in self.ListOfDevices[key]["Ep"]:
        if TEMPERATURE_CLUSTER in self.ListOfDevices[key]["Ep"][tmpEp]:
            EPout = tmpEp

    self.log.logging("Schneider", "Debug", f"schneider_temp_Setcurrent for device {key} sending command: {cmd} , setpoint: {setpoint}", key)


    disable_ack = "PowerSource" not in self.ListOfDevices[key] or self.ListOfDevices[key]["PowerSource"] != "Battery"

    read_attribute(self, key, ZIGATE_EP, EPout, THERMOSTAT_CLUSTER, "00", "00", "0000", 1, OCCUPIED_SETPOINT, ackIsDisabled=disable_ack)
    raw_APS_request(
        self, key, EPout, TEMPERATURE_CLUSTER, "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=is_ack_tobe_disabled(self, key)
    )
    self.ListOfDevices[key]["Heartbeat"] = "0"


def schneider_EHZBRTS_thermoMode(self, key, mode):

    # Attribute 0x0201 / 0xE010 ==> 0x01 ==> Mode Manuel   / Data Type 0x30
    #                               0x02 ==> Mode Programme
    #                               0x03 ==> Mode Economie
    #                               0x06 ==> Mode Vacances

    EHZBRTS_THERMO_MODE = {
        0: 0x00,
        10: 0x01,
        20: 0x02,
        30: 0x03,
        40: 0x04,
        50: 0x05,
        60: 0x06,
    }

    if key not in self.ListOfDevices:
        self.log.logging("Schneider", "Debug", f"schneider_EHZBRTS_thermoMode - unknown key: {key} in ListOfDevices!")

        return

    self.log.logging("Schneider", "Debug", f"schneider_EHZBRTS_thermoMode - {key} Mode: {mode}", key)


    if mode not in EHZBRTS_THERMO_MODE:
        _context = {"Error code": "SCHN0004", "mode": mode, "MODE": EHZBRTS_THERMO_MODE}
        self.log.logging("Schneider", "Error", f"Unknow Thermostat Mode {mode} for {key}", key, _context)

        return

    if SCHNEIDER_META_DATA not in self.ListOfDevices[key]:
        self.ListOfDevices[key][SCHNEIDER_META_DATA] = {}
    self.ListOfDevices[key][SCHNEIDER_META_DATA][TARGET_MODE] = mode
    self.ListOfDevices[key][SCHNEIDER_META_DATA][TIMESTAMP_MODE] = int(time())

    manuf_id = SCHNEIDER_MANUF_ID
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0201
    Hattribute = "%04x" % 0xE010
    data_type = "30"  # Uint8
    data = "%02x" % EHZBRTS_THERMO_MODE[mode]

    EPout = "01"
    for tmpEp in self.ListOfDevices[key]["Ep"]:
        if THERMOSTAT_CLUSTER in self.ListOfDevices[key]["Ep"][tmpEp]:
            EPout = tmpEp

    self.log.logging("Schneider", "Debug", f"Schneider EH-ZB-RTS Thermo Mode  {key} with value {data} / cluster: {cluster_id}, attribute: {Hattribute} type: {data_type}", nwkid=key)


    write_attribute(
        self,
        key,
        ZIGATE_EP,
        EPout,
        cluster_id,
        manuf_id,
        manuf_spec,
        Hattribute,
        data_type,
        data,
        ackIsDisabled=is_ack_tobe_disabled(self, key),
    )

    self.ListOfDevices[key]["Heartbeat"] = "0"
    self.ListOfDevices[key]["Heartbeat"] = "0"


def schneiderRenforceent(self, NWKID):

    if NWKID not in self.ListOfDevices:
        self.log.logging("Schneider", "Debug", f"schneiderRenforceent - unknown key: {NWKID} in ListOfDevices!")

        return

    rescheduleAction = False
    if "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] == "EH-ZB-VACT":
        return rescheduleAction

    if "Schneider Wiser" in self.ListOfDevices[NWKID]:
        if "HACT Mode" in self.ListOfDevices[NWKID]["Schneider Wiser"]:
            if not self.busy and self.ControllerLink.loadTransmit() <= MAX_LOAD_ZIGATE:
                schneider_hact_heating_mode(self, NWKID, self.ListOfDevices[NWKID]["Schneider Wiser"]["HACT Mode"])
            else:
                rescheduleAction = True
        if "HACT FIP Mode" in self.ListOfDevices[NWKID]["Schneider Wiser"]:
            if not self.busy and self.ControllerLink.loadTransmit() <= MAX_LOAD_ZIGATE:
                schneider_hact_fip_mode(self, NWKID, self.ListOfDevices[NWKID]["Schneider Wiser"]["HACT FIP Mode"])
            else:
                rescheduleAction = True

    return rescheduleAction


def schneider_multiple_read_attribute_request(self, Devices, nwkid, src_ep, dst_ep, sqn, cluster_id, manuf_specif, mabnuf_code, MsgData, nbAttribute):
    """ Handle a read request with multiple attributes on cluster 0x0201"""

    payload = None
    cmd = "01"
    status = "00"

    # Extract additional message components, and build a response
    for idx in range(0, len(MsgData), 4):
        attribute = MsgData[idx:idx + 4]
        self.log.logging("Schneider", "Debug", f"schneider_multiple_read_attribute_request - nwkid {nwkid} attribute {attribute}", nwkid)

        # Handle different cluster IDs and attributes
        zigate_ep, cluster_frame, data_type, data = get_response_data_for_schneider_thermostat_request(self, Devices, nwkid, src_ep, attribute)
        self.log.logging("Schneider", "Debug", f"schneider_multiple_read_attribute_request -  response {data_type} {data}", nwkid)
        if payload is None:
            payload = cluster_frame + sqn + cmd
        payload += attribute[2:4] + attribute[:2] + status + data_type
        payload += data[2:4] + data[:2] if data_type == "29" else data
    
    self.log.logging("Schneider", "Debug", f"schneider_multiple_read_attribute_request Response - nwkid {nwkid} ep: {src_ep} , clusterId: {cluster_id}, sqn: {sqn},payload: {payload}", nwkid)
        
    raw_APS_request( self, nwkid, src_ep, cluster_id, "0104", payload, zigate_ep=zigate_ep, ackIsDisabled=is_ack_tobe_disabled(self, nwkid), )
    

def schneider_thermostat_answer_attribute_request(self, Devices, nwkid, EPout, cluster_id, sqn, attribute):
    """Receive an attribute request from thermostat to know if the user has change the domoticz widget
    we answer the current temperature stored in the device

    Arguments:
        NWKID {[type]} -- [description]
        EPout {[type]} -- [description]
        ClusterID {[type]} -- [description]
        sqn {[type]} -- [description]
        rawAttr {[type]} -- [description]
    """
    self.log.logging("Schneider", "Debug", f"schneider_thermostat_answer_attribute_request: nwkid {nwkid} ep: {EPout} , clusterId: {cluster_id}, sqn: {sqn},rawAttr: {attribute}", nwkid)

    cmd = "01"
    status = "00"

    zigate_ep, cluster_frame, data_type, data = get_response_data_for_schneider_thermostat_request(self, Devices, nwkid, EPout, attribute)

    if data == data_type == "":
        # Unable to find a match
        wiser_unsupported_attribute(self, nwkid, EPout, sqn, cluster_id, attribute)
        return

    payload = cluster_frame + sqn + cmd + attribute[2:4] + attribute[:2] + status + data_type
    payload += data[2:4] + data[:2] if data_type == "29" else data

    self.log.logging("Schneider", "Debug", f"schneider_thermostat_answer_attribute_request Response - nwkid {nwkid} ep: {EPout} , clusterId: {cluster_id}, sqn: {sqn},payload: {payload}", nwkid)

    raw_APS_request( self, nwkid, EPout, cluster_id, "0104", payload, zigate_ep=zigate_ep, ackIsDisabled=is_ack_tobe_disabled(self, nwkid), )


def get_response_data_for_schneider_thermostat_request(self, Devices, NWKID, EPout, attr):

    model_name = self.ListOfDevices[NWKID].get("Model", "")

    # default values
    zigate_ep = ZIGATE_EP
    cluster_frame = "18"  # Disable default response

    # Mapping of model names to their configurations
    model_config = {
        "Wiser2-Thermostat": {"EPout": "01", "zigate_ep": "01", "cluster_frame": "08"},  
        "iTRV": {"EPout": "02", "zigate_ep": "01", "cluster_frame": "08"},
    }

    # Apply configuration based on model_name
    config = model_config.get(model_name)
    if config:
        EPout = config["EPout"]
        zigate_ep = config["zigate_ep"]
        cluster_frame = config["cluster_frame"]

    self.log.logging("Schneider", "Debug", f"Schneider receive attribute request: nwkid {NWKID} ep: {EPout} , zigate_ep {zigate_ep} cluster_frame= {cluster_frame}", NWKID)

    data = data_type = payload = ""
    boost_mode = is_boost_in_progress(self, NWKID)
    diagnostic_e001 = self.ListOfDevices[NWKID].get("Ep", {}).get("01", {}).get("0b05", {}).get("e001", 0xffff)
 
    if attr == LOCAL_TEMPERATURE:  # Local Temperature
        data_type = "29"
        if ( model_name in ( "iTRV",) ):
            # In case we have an iTRV alone (no room sensor, then we just return 0x8000)
            data = '%04x' %iTRV_local_temperature(self, NWKID)
        else:
            data = "%04x" % int(100 * schneider_find_attribute(self, NWKID, "01", THERMOSTAT_CLUSTER, LOCAL_TEMPERATURE))

    elif attr == SCHNEIDER_ZONE_MODE:  # mode of operation
        data_type = "30"
        data = "01"  # Manual

    elif attr == MIN_SETPOINT:  # min setpoint temp
        data_type = "29"
        data = ( "02bc" if self.ListOfDevices[NWKID]["Model"] in ("EH-ZB-VACT",) else "0032" )

    elif attr == MAX_SETPOINT:  # max setpoint temp
        data_type = "29"
        data = ( "0bb8" if self.ListOfDevices[NWKID]["Model"] in ("EH-ZB-VACT",) else "0dac" )

    elif attr == OCCUPIED_SETPOINT:  # occupied setpoint temp
        if (
           NWKID in self.ListOfDevices
           and SCHNEIDER_META_DATA in self.ListOfDevices[NWKID]
           and "BoostDemand" in self.ListOfDevices[NWKID][SCHNEIDER_META_DATA]
           ):
            del self.ListOfDevices[NWKID][SCHNEIDER_META_DATA]["BoostDemand"]

        data_type = "29"
        value = int(schneider_find_attribute_and_set(self, NWKID, EPout, THERMOSTAT_CLUSTER, OCCUPIED_SETPOINT, 2000))
        data = "%04X" % value

    elif attr == SYSTEM_MODE:  # System Mode for Wiser Home
        data_type = "30"  # enum8
        data = "04"  # 0x00 Off, 0x01 Auto, 0x04 Heat

    elif attr == CONTROL_SEQUENCE_OPERATION:  # ControlSequenceOfOperation for Wiser Home
        data_type = "30"  # enum8
        data = "02"  # Heating only

    elif attr == PI_HEATING_DEMAND:  # Pi Heating Demand  (valve position %) for Wiser Home
        # In case eof iTRV, it looks like we have to trigger the heating demand.
        # In case the new setpoint is above the local temp, and the Heating Demand is 0, let's enable it
        if (
           NWKID in self.ListOfDevices
           and SCHNEIDER_META_DATA in self.ListOfDevices[NWKID]
           and "BoostDemand" in self.ListOfDevices[NWKID][SCHNEIDER_META_DATA]
           ):
            del self.ListOfDevices[NWKID][SCHNEIDER_META_DATA]["BoostDemand"]

        define_heating_demand_for_iTRV(self, Devices, NWKID)
        
        data_type = "20"  # uint8
        data = "%02x" % schneider_find_attribute_and_set(self, NWKID, EPout, THERMOSTAT_CLUSTER, PI_HEATING_DEMAND, 0)

    elif attr == "e110":  # ?? for Wiser Home
        # 0x02 then 0x01, 0x12 (after 0x80 - 0x0301 Boost) and back to 0x01 after 0x80 - 0x0300 Cancel Boost)
        # Mostlikely we are 0x02 during the pairing phase and when getting 0x0b05/0xe001 is shitfing from 0xfffe to 0x0000, then 0x01
        data_type = "30"  # enum8
        data = "02" if diagnostic_e001 != 0 else ("12" if boost_mode else "01")

    return zigate_ep, cluster_frame, data_type, data 


def define_heating_demand_for_iTRV(self, Devices, nwkid):
    # We force to use Ep 0x01 even if the iTRV is communicating on Ep 0x02

    GAP_TO_DEMAND = {
        -1000: 100,
        -700: 75,
        -400: 50,
        0: 25
    }

    if self.ListOfDevices.get(nwkid, {}).get("Model") not in {"Wiser2-Thermostat", "iTRV"}:
        return

    current_setpoint = int(schneider_find_attribute(self, nwkid, "01", THERMOSTAT_CLUSTER, OCCUPIED_SETPOINT))
    current_demand = schneider_find_attribute_and_set(self, nwkid, "01", THERMOSTAT_CLUSTER, PI_HEATING_DEMAND, 0)

    local_temp = iTRV_local_temperature(self, nwkid)
    if local_temp == 0x8000:
        # We use the inside Temp sensor, let's get local sensor temp (instead of the room sensor)
        local_temp = int( 100 * schneider_find_attribute(self, nwkid, "01", THERMOSTAT_CLUSTER, LOCAL_TEMPERATURE) )

    self.log.logging( "Schneider", "Debug", f"define_heating_demand_for_iTRV: local temp {local_temp} current setpoint {current_setpoint} current demand {current_demand}", nwkid)

    gap_temp = local_temp - current_setpoint
    self.log.logging("Schneider", "Debug", f'define_heating_demand_for_iTRV: gap: {gap_temp}')

    # Define the ranges and corresponding pi_demand values

    # Determine pi_demand based on gap_temp
    pi_demand = 0 if gap_temp >= 0 else next(
        GAP_TO_DEMAND[threshold] for threshold in sorted(GAP_TO_DEMAND) if gap_temp < threshold
    )

    self.log.logging("Schneider", "Debug", f'define_heating_demand_for_iTRV: pi_demand: {pi_demand}')

    if ( current_demand != 0 and gap_temp > 0):
        self.ListOfDevices[nwkid]["Ep"]["01"][THERMOSTAT_CLUSTER][PI_HEATING_DEMAND] = 0
        MajDomoDevice(self, Devices, nwkid, "01", THERMOSTAT_CLUSTER, 0, Attribute_=PI_HEATING_DEMAND)

    elif pi_demand != current_demand:
        self.ListOfDevices[nwkid]["Ep"]["01"][THERMOSTAT_CLUSTER][PI_HEATING_DEMAND] = pi_demand
        MajDomoDevice(self, Devices, nwkid, "01", THERMOSTAT_CLUSTER, pi_demand, Attribute_=PI_HEATING_DEMAND)


def schneider_update_ThermostatDevice(self, Devices, NWKID, srcEp, ClusterID, new_setpoint):
    """we received a new setpoint from the thermostat device , we need to update the domoticz widget

    Arguments:
        Devices {[type]} -- [description]
        NWKID {[type]} -- [description]
        srcEp {[type]} -- [description]
        ClusterID {[type]} -- [description]
        setpoint {[type]} -- [description]
    """
    # Check if nwkid is the ListOfDevices
    if NWKID not in self.ListOfDevices:
        return

    # modify attribute of thermostat to store the new temperature requested
    schneider_find_attribute_and_set(self, NWKID, srcEp, ClusterID, OCCUPIED_SETPOINT, new_setpoint, new_setpoint)
    MajDomoDevice(self, Devices, NWKID, srcEp, ClusterID, round(new_setpoint / 100, 1), Attribute_=OCCUPIED_SETPOINT)

    importSchneiderZoning(self)
    if self.SchneiderZone is not None:
        for zone in self.SchneiderZone:
            if self.SchneiderZone[zone]["Thermostat"]["NWKID"] != NWKID:
                continue
            self.log.logging("Schneider", "Debug", f"schneider_update_ThermostatDevice - found {zone} ", NWKID)

            for hact in self.SchneiderZone[zone]["Thermostat"]["HACT"]:
                self.log.logging("Schneider", "Debug", f"schneider_update_ThermostatDevice - update hact setpoint mode hact nwwkid:{hact} ", NWKID)

                schneider_hact_heating_mode(self, hact, "setpoint")


def schneiderAlarmReceived(self, Devices, NWKID, srcEp, ClusterID, start, payload):
    """
    Function called when a command is received from the schneider device to alert about over consumption
    """

    # uint8  0x10: low voltage, 0x11 high voltage, 0x16 high current
    AlertCode = int(payload[:2], 16)  

    AlertClusterId = payload[4:6] + payload[2:4]  # uint16
    self.log.logging(
        "Schneider",
        "Debug",
        "schneiderAlarmReceived start:%s, AlertCode: %s, AlertClusterID: %s" % (start, AlertCode, AlertClusterId),
        NWKID,
    )

    if AlertCode == 0x16:  # max current of contract reached
        cluster_id = "%04x" % 0x0009
        value = "00"
        if start:
            schneider_bms_change_reporting(self, NWKID, srcEp, True)
            current_consumption = 0
            if "Shedding" in self.ListOfDevices[NWKID]:
                if self.ListOfDevices[NWKID]["Shedding"]:
                    self.log.logging("Schneider", "Debug", "schneiderAlarmReceived already shedding - EXIT", NWKID)
                    return  # we are already shedding

            if srcEp in self.ListOfDevices[NWKID]["Ep"]:
                if METERING_CLUSTER in self.ListOfDevices[NWKID]["Ep"][srcEp]:
                    current_consumption = float(self.ListOfDevices[NWKID]["Ep"][srcEp][METERING_CLUSTER][INSTANT_POWER])

            if (SCHNEIDER_META_DATA in self.ListOfDevices[NWKID]) and (
                "contractPowerLevel" in self.ListOfDevices[NWKID][SCHNEIDER_META_DATA]
            ):
                contractPowerLevel = self.ListOfDevices[NWKID][SCHNEIDER_META_DATA]["contractPowerLevel"]
            else:
                contractPowerLevel = 65535

            self.log.logging(
                "Schneider",
                "Debug",
                "schneiderAlarmReceived contract max: %s current: %s" % (contractPowerLevel, current_consumption),
                NWKID,
            )

            if (current_consumption * 110 / 100) > contractPowerLevel:
                self.log.logging("Schneider", "Debug", "schneiderAlarmReceived shedding", NWKID)
                value = "04"
                self.ListOfDevices[NWKID]["Shedding"] = True
            else:
                self.log.logging("Schneider", "Debug", "schneiderAlarmReceived current consumption is ok - EXIT", NWKID)
                return

        else:
            schneider_bms_change_reporting(self, NWKID, srcEp, False)
            if "Shedding" in self.ListOfDevices[NWKID] and not self.ListOfDevices[NWKID]["Shedding"]:
                self.log.logging("Schneider", "Debug", "schneiderAlarmReceived not shedding - EXIT", NWKID)
                return
            self.ListOfDevices[NWKID]["Shedding"] = False

        self.log.logging(
            "Schneider",
            "Debug",
            "Schneider update Alarm Domoticz device Attribute %s Endpoint:%s / cluster: %s to %s"
            % (NWKID, srcEp, cluster_id, value),
            NWKID,
        )
        MajDomoDevice(self, Devices, NWKID, srcEp, cluster_id, value)

    elif AlertCode == 0x10:  # battery low
        ReadAttributeRequest_0001(self, NWKID)
    # Modules.output.ReadAttributeRequest_0702(self, NWKID)


def schneider_set_contract(self, key, EPout, kva):
    """
    Configure the schneider device to report an alarm when consumption is above a threshold in miliamps
    """

    POWER_FACTOR = 0.92
    max_real_power_in_kwh = kva * 1000 * POWER_FACTOR
    max_real_amps = max_real_power_in_kwh / 235
    max_real_amps_before_tripping = max_real_amps * 110 / 100
    max_real_milli_amps_before_tripping = round(max_real_amps_before_tripping * 1000)
    self.log.logging("Schneider", "Debug", f"schneider_set_contract for device {key} {EPout} requesting max_real_milli_amps_before_tripping: {max_real_milli_amps_before_tripping} milliamps", key)


    if SCHNEIDER_META_DATA not in self.ListOfDevices[key]:
        self.ListOfDevices[key][SCHNEIDER_META_DATA] = {}

    self.ListOfDevices[key][SCHNEIDER_META_DATA]["contractPowerLevel"] = kva * 1000

    ClusterId = METERING_CLUSTER  # Simple Metering
    ManufacturerID = "0000"
    ManufacturerSpecfic = "00"
    AttributeID = "5121"  # Max Current
    DataType = "22"  # 24 bits unsigned integer
    data = "%06x" % max_real_milli_amps_before_tripping
    write_attribute_when_awake(
        self, key, ZIGATE_EP, EPout, ClusterId, ManufacturerID, ManufacturerSpecfic, AttributeID, DataType, data
    )

    AttributeID = "7003"  # Contract Name
    DataType = "42"  # String
    data = "BASE".encode("utf-8").hex()  # BASE
    write_attribute_when_awake(
        self, key, ZIGATE_EP, EPout, ClusterId, ManufacturerID, ManufacturerSpecfic, AttributeID, DataType, data
    )


def schneiderReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):
    """Function called when raw APS indication are received for a schneider device - it then decide how to handle it
    Arguments:
        Devices {[type]} -- list of devices
        srcNWKID {[type]} -- id of the device that generated the request
        srcEp {[type]} -- Endpoint of the device that generated the request
        ClusterID {[type]} -- cluster Id of the device that generated the request
        dstNWKID {[type]} -- Id of the device that should receive the request
        dstEP {[type]} -- Endpoint of the device that should receive the request
        MsgPayload {[type]} -- [description]
    """
    self.log.logging("Schneider", "Debug", f"Schneider read raw APS nwkid: {srcNWKID} ep: {srcEp} , clusterId: {ClusterID}, dstnwkid: {dstNWKID}, dstep: {dstEP}, payload: {MsgPayload}", srcNWKID)

    default_response, GlobalCommand, Sqn, ManufacturerCode, Command, Data = retreive_cmd_payload_from_8002(MsgPayload)
    self.log.logging("Schneider", "Debug", "         -- SQN: %s, CMD: %s, Data: %s" % (Sqn, Command, Data), srcNWKID)

    if ClusterID == THERMOSTAT_CLUSTER:  # Thermostat cluster
        if GlobalCommand and Command == "00":  # read attributes
            idx = nbAttribute = 0
            while idx < len(Data):
                nbAttribute += 1
                Attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx: idx + 4], 16)))[0]
                idx += 4
                if self.zigbee_communication == "native" and self.FirmwareVersion and int(self.FirmwareVersion, 16) <= 0x031C:
                    wiser_unsupported_attribute(self, srcNWKID, srcEp, Sqn, ClusterID, Attribute)
                else:
                    self.log.logging("Schneider", "Debug", f"Schneider cmd 0x00 [{Sqn}] Read Attribute Request on Src: {srcNWKID}/{srcEp} for {ClusterID}/{Attribute} Dst: {dstNWKID}/{dstEP}", srcNWKID)
                    schneider_thermostat_answer_attribute_request(self, Devices, srcNWKID, srcEp, ClusterID, Sqn, Attribute)

        #elif not GlobalCommand and Command == "00":  # Setpoint Raise/Lower
        #    # Decode8002 - NwkId: 656d Ep: 01 Cluster: 0201 GlobalCommand: False Command: 00 Data: 00fb  - 0,05
        #    # inRawAps Nwkid: 656d Ep: 01 Cluster: 0201 ManufCode: None manuf: 105e manuf_name: Schneider Electric Cmd: 00 Data: 0005   + 0,05
        #    setpoint_mode = Data[:2]
        #    amount = Data[2:4]
        #    wiser2_setpoint_raiserlower(self, Devices, srcNWKID, setpoint_mode, amount)

        elif Command == "e0":  # command to change setpoint from thermostat
            sTemp = Data[4:8]
            setpoint = struct.unpack("h", struct.pack(">H", int(sTemp, 16)))[0]
            schneider_update_ThermostatDevice(self, Devices, srcNWKID, srcEp, ClusterID, setpoint)

        elif Command == "80":  # command to change setpoint with a time
            change_setpoint_for_time(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, Data)

    elif ClusterID == "0009":  # Alarm cluster
        if Command == "00":  # start of alarm
            self.log.logging("Schneider", "Debug", "Schneider cmd 0x00", srcNWKID)
            schneiderAlarmReceived(self, Devices, srcNWKID, srcEp, ClusterID, True, Data)
        elif Command == "50":  # end of alarm
            self.log.logging("Schneider", "Debug", "Schneider cmd 0x50", srcNWKID)
            schneiderAlarmReceived(self, Devices, srcNWKID, srcEp, ClusterID, False, Data)

    elif ClusterID == "0000":
        if Command == "00":
            wiserhome_ZCLVersion_response(self, Devices, srcNWKID, srcEp, Sqn)


def wiser2_setpoint_raiserlower(self, Devices, NwkId, mode, amount):

    self.log.logging("Schneider", "Debug", f"wiser2_setpoint_raiserlower {NwkId} mode: {mode} {amount}", NwkId)
    
    if is_boost_in_progress(self, NwkId):
        self.log.logging("Schneider", "Debug", "wiser2_setpoint_raiserlower Boost in progress - EXIT", NwkId)
        return

    amount = int((struct.unpack("b", struct.pack(">B", int(amount, 16)))[0])) * 10

    if mode == "00":  # Heat adjust Heat Setpoint
        current_setpoint = schneider_find_attribute_and_set(self, NwkId, "01", THERMOSTAT_CLUSTER, OCCUPIED_SETPOINT, 2000)
        new_setpoint = int(((current_setpoint + amount) * 20) / 20)  # Round to °.5
        self.log.logging("Schneider", "Debug", f"wiser2_setpoint_raiserlower cmd Mode [Heat] amount: {amount} {current_setpoint} => {new_setpoint}")
        schneider_update_ThermostatDevice(self, Devices, NwkId, "01", THERMOSTAT_CLUSTER, new_setpoint)

    elif mode == "01":  # Cool (adjust Cool Setpoint)
        self.log.logging("Schneider", "Debug", "wiser2_setpoint_raiserlower cmd Mode [Cool] amount: %s" % amount)
        value = schneider_find_attribute_and_set(self, NwkId, "01", THERMOSTAT_CLUSTER, "0011", 2000)
        schneider_find_attribute_and_set(self, NwkId, "01", THERMOSTAT_CLUSTER, "0011", 2000, newValue=value + amount)

    elif mode == "02":  # Both ( adjust Heat Setpoint and Cool Setpoint)
        self.log.logging("Schneider", "Debug", f"wiser2_setpoint_raiserlower cmd Mode [Heat+Cool] amount: {amount}")


def wiserhome_ZCLVersion_response(self, Devices, srcNWKID, srcEp, Sqn):
    cmd = "01"
    status = "00"
    cluster_frame = "08"

    data_type = "20"
    ZCLVersion = "03"
    payload = cluster_frame + Sqn + cmd + "0000" + status + data_type + ZCLVersion
    raw_APS_request(
        self,
        srcNWKID,
        srcEp,
        "0000",
        "0104",
        payload,
        zigate_ep=ZIGATE_EP,
        ackIsDisabled=is_ack_tobe_disabled(self, srcNWKID),
    )
    self.log.logging("Schneider", "Debug", f"Schneider Wiser Home Response ZCLVersion {ZCLVersion} to device {srcNWKID}", srcNWKID)


def wiser_read_attribute_request(self, Devices, NwkId, Ep, Sqn, ClusterId, Attribute):

    if self.zigbee_communication == "native" and self.FirmwareVersion and int(self.FirmwareVersion, 16) <= 0x031C:
        # We shouldn't reach here, as the firmware itself will reject and respond.
        wiser_unsupported_attribute(self, NwkId, Ep, Sqn, ClusterId, Attribute)
    else:
        self.log.logging("Schneider", "Debug", f"Schneider cmd 0x00 [{Sqn}] Read Attribute Request on {ClusterId}/{Attribute}", NwkId)

        schneider_thermostat_answer_attribute_request(self, Devices, NwkId, Ep, ClusterId, Sqn, Attribute)


def wiser_unsupported_attribute(self, srcNWKID, srcEp, Sqn, ClusterID, attribute):
    cluster_frame = "18"
    cmd = "01"
    payload = cluster_frame + Sqn + cmd + attribute[2:4] + attribute[:2] + "86"
    self.log.logging("Schneider", "Debug", f"wiser_unsupported_attribute for device {srcNWKID} sending command: {cmd} , attribute: {attribute}", srcNWKID)

    raw_APS_request(
        self,
        srcNWKID,
        "0b",
        ClusterID,
        "0104",
        payload,
        zigate_ep=ZIGATE_EP,
        ackIsDisabled=is_ack_tobe_disabled(self, srcNWKID),
    )


def importSchneiderZoning(self):
    """
    Import Schneider Zoning Configuration, and populate the corresponding datastructutreÒ
    {
            "zone1": {
                "ieee_thermostat": "ieee of my thermostat",
                "actuator": ["IEEE1","IEEE2"]
            },
            " zone2": {
                "ieee_thermostat": "ieee of my thermostat",
                "actuator": ["IEEE1","IEEE2"]
            }
    }
    """

    if self.SchneiderZone is not None:
        # Alreday imported. We do it only once
        return

    SCHNEIDER_ZONING = "schneider_zoning.json"

    self.SchneiderZoningFilename = self.pluginconf.pluginConf["pluginConfig"] + os.sep + SCHNEIDER_ZONING

    if not os.path.isfile(self.SchneiderZoningFilename):
        self.log.logging("Schneider", "Debug", f"importSchneiderZoning - Nothing to import from {self.SchneiderZoningFilename}")

        self.SchneiderZone = None
        return

    self.SchneiderZone = {}
    with open(self.SchneiderZoningFilename, "rt") as handle:
        SchneiderZoning = json.load(handle)

    for zone in SchneiderZoning:
        if "ieee_thermostat" not in SchneiderZoning[zone]:
            # Missing Thermostat
            _context = {"Error code": "SCHN0005", "zone": zone, "SchneiderZoning": SchneiderZoning[zone]}
            self.log.logging("Schneider", "Error", f"importSchneiderZoning - Missing Thermostat entry in {SchneiderZoning[zone]}", context=_context)

            continue

        if SchneiderZoning[zone]["ieee_thermostat"] not in self.IEEE2NWK:
            # Thermostat IEEE not known!
            _context = {
                "Error code": "SCHN0006",
                "zone": zone,
                "SchneiderZoning[zone]": SchneiderZoning[zone]["ieee_thermostat"],
                "IEEE": self.IEEE2NWK,
            }
            self.log.logging("Schneider", "Error", f'importSchneiderZoning - Thermostat IEEE {SchneiderZoning[zone]["ieee_thermostat"]} do not exist', context=_context)

            continue

        self.SchneiderZone[zone] = {"Thermostat": {"IEEE": SchneiderZoning[zone]["ieee_thermostat"]}}

        self.SchneiderZone[zone]["Thermostat"]["NWKID"] = self.IEEE2NWK[SchneiderZoning[zone]["ieee_thermostat"]]
        self.SchneiderZone[zone]["Thermostat"]["HACT"] = {}

        if "actuator" not in SchneiderZoning[zone]:
            # We just have a simple Thermostat
            _context = {"Error code": "SCHN0007", "zone": zone, "SchneiderZoning": SchneiderZoning[zone]}
            self.log.logging("Schneider", "Debug", f"importSchneiderZoning - No actuators for this Zone: {zone}", context=_context)

            continue

        for hact in SchneiderZoning[zone]["actuator"]:
            if hact not in list(self.IEEE2NWK):
                continue
            
            _nwkid = self.IEEE2NWK[hact]
            if hact not in self.IEEE2NWK:
                # Unknown in IEEE2NWK
                _context = {
                    "Error code": "SCHN0008",
                    "zone": zone,
                    "hact": hact,
                    "SchneiderZoning[zone]": SchneiderZoning[zone]["actuator"],
                    "IEEE": self.IEEE2NWK,
                }
                self.log.logging("Schneider", "Error", f"importSchneiderZoning - Unknown HACT: {hact}", _nwkid, _context)

                continue

            if self.IEEE2NWK[hact] not in self.ListOfDevices:
                # Unknown in ListOfDevices
                _context = {
                    "Error code": "SCHN0009",
                    "zone": zone,
                    "hact": hact,
                    "SchneiderZoning[zone]": SchneiderZoning[zone]["actuator"],
                }
                self.log.logging("Schneider", "Error", f"importSchneiderZoning - Unknown HACT: {_nwkid}", _nwkid, _context)

                continue

            self.SchneiderZone[zone]["Thermostat"]["HACT"][_nwkid] = {"IEEE": hact}
    # At that stage we have imported all informations
    self.log.logging("Schneider", "Debug", f"importSchneiderZoning - Zone Information: {self.SchneiderZone} ")


def schneider_find_attribute(self, NWKID, EP, ClusterID, attr):

    if EP not in self.ListOfDevices[NWKID]["Ep"]:
        self.ListOfDevices[NWKID]["Ep"][EP] = {}
    if ClusterID not in self.ListOfDevices[NWKID]["Ep"][EP]:
        self.ListOfDevices[NWKID]["Ep"][EP][ClusterID] = {}
    if not isinstance(self.ListOfDevices[NWKID]["Ep"][EP][ClusterID], dict):
        self.ListOfDevices[NWKID]["Ep"][EP][ClusterID] = {}
    if attr not in self.ListOfDevices[NWKID]["Ep"][EP][ClusterID]:
        self.ListOfDevices[NWKID]["Ep"][EP][ClusterID][attr] = 0
    if isinstance(self.ListOfDevices[NWKID]["Ep"][EP][ClusterID][attr], dict):
        self.ListOfDevices[NWKID]["Ep"][EP][ClusterID][attr] = 0

    return self.ListOfDevices[NWKID]["Ep"][EP][ClusterID][attr]


def schneider_find_attribute_and_set(self, NWKID, EP, ClusterID, attr, defaultValue, newValue=None):
    """
    Finds an attribute in the device list and updates it if needed.

    Parameters:
        NWKID (str): The network ID of the device.
        EP (str): The endpoint identifier.
        ClusterID (str): The Zigbee cluster ID.
        attr (str): The attribute to search for.
        defaultValue: The default value to set if the attribute is not found.
        newValue (optional): A new value to update the attribute.

    Returns:
        The found or updated attribute value.
    """
    self.log.logging(
        "Schneider", "Debug",
        f"schneider_find_attribute_and_set NWKID:{NWKID}, EP:{EP}, ClusterID:{ClusterID}, attr:{attr}, defaultValue:{defaultValue}, newValue:{newValue}",
        NWKID
    )

    # Adjust endpoint for specific models
    if self.ListOfDevices.get(NWKID, {}).get("Model") == "iTRV":
        EP = '01'  # Store all iTRV attributes on Ep 0x01

    # Ensure dictionary structure exists
    device = self.ListOfDevices.setdefault(NWKID, {})
    ep_data = device.setdefault("Ep", {}).setdefault(EP, {}).setdefault(ClusterID, {})

    # Get the current value or assign default/newValue if missing
    found = ep_data.get(attr, newValue if newValue is not None else defaultValue)

    if attr not in ep_data:
        self.log.logging("Schneider", "Debug", f"Setting {attr} to {found}", NWKID)
        ep_data[attr] = found

    self.log.logging("Schneider", "Debug", f"Found value {found}", NWKID)

    # Update the attribute if newValue is provided
    if newValue is not None:
        self.log.logging("Schneider", "Debug", f"Updating {attr} to {newValue} on {NWKID}/{EP}", NWKID)
        ep_data[attr] = newValue
        found = newValue

    return found


def schneider_bms_change_reporting(self, NWKID, srcEp, fast):
    
    if fast:
        schneider_UpdateConfigureReporting(self, NWKID, srcEp, METERING_CLUSTER, CONFIG_REPORTING_FAST)
    else:
        schneider_UpdateConfigureReporting(self, NWKID, srcEp, METERING_CLUSTER, CONFIG_REPORTING_NORMAL)


def vact_config_reporting_normal(self, NwkId, EndPoint):

    AttributesConfig = {
        "0020": {"DataType": "20", "MinInterval": "0E10", "MaxInterval": "0E10", "TimeOut": "0000", "Change": "01"}
    }
    schneider_UpdateConfigureReporting(self, NwkId, EndPoint, "0001", AttributesConfig)

    # Set the Window Detection to 0x04
    wiser_set_thermostat_window_detection(self, NwkId, EndPoint, 0x04)

    AttributesConfig = {
        "0012": {"DataType": "29", "MinInterval": "0258", "MaxInterval": "0258", "TimeOut": "0000", "Change": "7FFF"},
        "0000": {"DataType": "29", "MinInterval": "003C", "MaxInterval": "0258", "TimeOut": "0000", "Change": "0001"},
        "e030": {"DataType": "20", "MinInterval": "003C", "MaxInterval": "0258", "TimeOut": "0000", "Change": "01"},
        "e031": {"DataType": "30", "MinInterval": "000A", "MaxInterval": "0258", "TimeOut": "0000", "Change": "01"},
        "e012": {"DataType": "30", "MinInterval": "000A", "MaxInterval": "0258", "TimeOut": "0000", "Change": "01"},
    }
    schneider_UpdateConfigureReporting(self, NwkId, EndPoint, THERMOSTAT_CLUSTER, AttributesConfig)

    AttributesConfig = {
        "0001": {"DataType": "30", "MinInterval": "001E", "MaxInterval": "0258", "TimeOut": "0000", "Change": "00"}
    }

    schneider_UpdateConfigureReporting(self, NwkId, EndPoint, "0204", AttributesConfig)

    self.ListOfDevices[NwkId][SCHNEIDER_META_DATA]["ReportingMode"] = "Normal"

 
def schneider_UpdateConfigureReporting(self, NwkId, Ep, ClusterId=None, AttributesConfig=None):
    """
    Will send a Config reporting to a specific Endpoint of a Wiser Device.
    It is assumed that the device is on Receive at the time we will be sending the command
    If ClusterId is not None, it will use the AttributesConfig dictionnary for the reporting config,
    otherwise it will retreive the config from the DeviceConf for this particular Model name

    AttributesConfig must have the same format:
        {
            "0000": {"DataType": "29", "MinInterval":"0258", "MaxInterval":"0258", "TimeOut":"0000","Change":"0001"},
            "0012": {"DataType": "29", "MinInterval":"0258", "MaxInterval":"0258", "TimeOut":"0000","Change":"7FFF"},
            "e030": {"DataType": "20", "MinInterval":"003C", "MaxInterval":"0258", "TimeOut":"0000","Change":"01"},
            "e031": {"DataType": "30", "MinInterval":"001E", "MaxInterval":"0258", "TimeOut":"0000","Change":"01"},
            "e012": {"DataType": "30", "MinInterval":"001E", "MaxInterval":"0258", "TimeOut":"0000","Change":"01"}
        }
    """

    if NwkId not in self.ListOfDevices:
        return

    if ClusterId is None:
        return

    if AttributesConfig is None:
        # AttributesConfig is not defined, so lets get it from the Model
        if "Model" not in self.ListOfDevices[NwkId]:
            return

        _modelName = self.ListOfDevices[NwkId]["Model"]
        if _modelName not in self.DeviceConf:
            return

        if STORE_CONFIGURE_REPORTING not in self.DeviceConf[_modelName]:
            return

        if ClusterId not in self.DeviceConf[_modelName][STORE_CONFIGURE_REPORTING]:
            return

        if "Attributes" not in self.DeviceConf[_modelName][STORE_CONFIGURE_REPORTING][ClusterId]:
            return

        AttributesConfig = self.DeviceConf[self.ListOfDevices[NwkId]["Model"]][STORE_CONFIGURE_REPORTING][ClusterId][
            "Attributes"
        ]

    ListOfAttributesToConfigure = AttributesConfig.keys()
    self.log.logging( "Schneider", "Debug", "schneider_UpdateConfigureReporting - ClusterId: %s ClusterList: %s ListOfAttribute: %s" %(
        ClusterId, str(AttributesConfig), str(ListOfAttributesToConfigure)))
    if self.configureReporting:
        self.configureReporting.prepare_and_send_configure_reporting(
            NwkId, Ep, AttributesConfig, ClusterId, "00", "00", "0000", ListOfAttributesToConfigure)
    

# Management of EH-ZB-VACT, iTRV
def is_boost_in_progress(self, NwkId):
    device = self.ListOfDevices.get(NwkId, {})
    boost_demand = device.get(SCHNEIDER_META_DATA, {}).get("BoostDemand")
    if boost_demand:
        return True

    thermostat_override = device.get(SCHNEIDER_META_DATA, {}).get("ThermostatOverride")

    if thermostat_override is None:
        return False

    thermostat_override_start_time = thermostat_override.get("OverrideStartTime")
    thermostat_override_duration = thermostat_override.get("OverrideDuration")

    remaining_time = int(thermostat_override_start_time + thermostat_override_duration - time())
    return remaining_time > 0

  
def receiving_heatingdemand_attribute( self, Devices, NwkId, Ep, value, MsgClusterId, MsgAttrID):
    
    self.log.logging("Schneider", "Debug", f"receiving_heatingdemand_attribute -- for device {NwkId} / {Ep}")
    if is_boost_in_progress(self, NwkId ):
        return
    checkAndStoreAttributeValue(self, NwkId, Ep, MsgClusterId, MsgAttrID, value)


def receiving_heatingpoint_attribute( self, Devices, NwkId, Ep, ValueTemp, value, ClusterId, AttributeId):

    if is_boost_in_progress(self, NwkId):
        self.log.logging("Schneider", "Debug", "receiving_heatingpoint_attribute - boost in progress", NwkId)
        return

    self.log.logging("Schneider", "Debug", f"receiving_heatingpoint_attribute - ValueTemp: {ValueTemp} -> {int(((ValueTemp * 100) * 2) / 2)}", NwkId)

    if SCHNEIDER_META_DATA not in self.ListOfDevices[NwkId]:
        self.log.logging( "Schneider", "Debug", "receiving_heatingpoint_attribute - Updating because Schneider do not exist")
        # No Schneider section, so we assumed Setpoint has been updated manualy.
        self.ListOfDevices[NwkId][SCHNEIDER_META_DATA] = {TARGET_SETPOINT: None, TIMESTAMP_SETPOINT: None}
        checkAndStoreAttributeValue(self, NwkId, Ep, ClusterId, AttributeId, int(value))
        MajDomoDevice(self, Devices, NwkId, Ep, ClusterId, ValueTemp, Attribute_=AttributeId)
        return

    if TARGET_SETPOINT not in self.ListOfDevices[NwkId][SCHNEIDER_META_DATA]:
        self.log.logging( "Schneider", "Debug", "receiving_heatingpoint_attribute - Updating because Target SetPoint do not exist")
        # No Target Setpoint, so we assumed Setpoint has been updated manualy.
        checkAndStoreAttributeValue(self, NwkId, Ep, ClusterId, AttributeId, int(value))
        self.ListOfDevices[NwkId][SCHNEIDER_META_DATA][TARGET_SETPOINT] = None
        self.ListOfDevices[NwkId][SCHNEIDER_META_DATA][TIMESTAMP_SETPOINT] = None
        MajDomoDevice(self, Devices, NwkId, Ep, ClusterId, ValueTemp, Attribute_=AttributeId)
        return

    if self.ListOfDevices[NwkId][SCHNEIDER_META_DATA][TARGET_SETPOINT] is None:
        self.log.logging( "Schneider", "Debug", "receiving_heatingpoint_attribute - Updating because Target SetPoint is None")
        # Target is None
        checkAndStoreAttributeValue(self, NwkId, Ep, ClusterId, AttributeId, int(value))
        MajDomoDevice(self, Devices, NwkId, Ep, ClusterId, ValueTemp, Attribute_=AttributeId)
        return

    if self.ListOfDevices[NwkId][SCHNEIDER_META_DATA][TARGET_SETPOINT] == int(((ValueTemp * 100) * 2) / 2):
        # Existing Target equal Local Setpoint in Device
        checkAndStoreAttributeValue(self, NwkId, Ep, ClusterId, AttributeId, int(value))
        self.ListOfDevices[NwkId][SCHNEIDER_META_DATA][TARGET_SETPOINT] = None
        self.ListOfDevices[NwkId][SCHNEIDER_META_DATA][TIMESTAMP_SETPOINT] = None
        MajDomoDevice(self, Devices, NwkId, Ep, ClusterId, ValueTemp, Attribute_=AttributeId)
        return

    if (
        "Model" in self.ListOfDevices[NwkId] 
        and self.ListOfDevices[NwkId]["Model"] == "EH-ZB-VACT" 
        and ( time() > ( self.ListOfDevices[NwkId][SCHNEIDER_META_DATA][TIMESTAMP_SETPOINT] + ( 12 * 60) ))
    ):
        # We reached here because the Setpoint do not equal to the Setpoint in the plugin
        # Most likely we have tried to set a new setpoint, but didn't go through
        # It could also happen if the SetPoint has been set manualy.
        # Let's use a time window of 5 minutes, after that, we drop
        self.log.logging("Schneider", "Debug", f"receiving_heatingpoint_attribute - ValueTemp: {int(value)} diff from plugin, so we save it", NwkId)
        checkAndStoreAttributeValue(self, NwkId, Ep, ClusterId, AttributeId, int(value))
        MajDomoDevice(self, Devices, NwkId, Ep, ClusterId, ValueTemp, Attribute_=AttributeId)


    # We reach here because most-likely there is a Target SetPoint defined, and the value we receive is not the same.
    self.log.logging("Schneider", "Debug", f"receiving_heatingpoint_attribute - ValueTemp: {int(((ValueTemp * 100) * 2) / 2)} nothing done", NwkId)


# Wiser New Version
def wiser_home_lockout_thermostat(self, NwkId, mode):

    self.log.logging("Schneider", "Debug", f"wiser_home_lockout_thermostat -- mode: {mode}")

    mode = int(mode)
    if mode in {0, 1}:
        write_attribute(
            self, NwkId, ZIGATE_EP, "01", "0204", "0000", "00", "0001", "30", "%02x" % mode, ackIsDisabled=False
        )
    else:
        return


def change_setpoint_for_time(self, Devices, nwkid, srcEp, ClusterID, dstNWKID, dstEP, data):
    # sourcery skip: merge-comparisons, merge-duplicate-blocks, remove-redundant-if, remove-redundant-slice-index
    # Command 0x80: 0301 2e09 7800
    #               0301 d007 1e00   ( 20° for 30 minutes)
    #               0301 7206 1e00   ( 16.5° for 30 minutes)
    #               0300 ff0f 0000   ( cancel last boost )
    #               0300 ff0f 0000

    #               0201 5a0a 3c00   ( 26.5 for 60' )
    #               0202 ca08 3c00   ( 22.5 for 60 )
    #               0202 ca08 3c00

    BOOST = [ "0102", "0103", "0202"]
    CANCEL_BOOST = "0003"

    action = data[2:4] + data[0:2]
    setpoint = int(data[6:8] + data[4:6], 16)
    duration = int(data[10:12] + data[8:10], 16)
    
    self.log.logging("Schneider", "Debug", f"change_setpoint_for_time -- action: {action} setpoint: {setpoint} duration: {duration}", nwkid)
    
    schneider_data = self.ListOfDevices.get(nwkid, {}).get(SCHNEIDER_META_DATA, {})
    ep_out = "01" if self.ListOfDevices.get(nwkid, {}).get("Model") == "iTRV" else srcEp

    if action in BOOST:
        self.log.logging("Schneider", "Debug", f"change_setpoint_for_time -- Setpoint to {setpoint} for {duration} min")
        setpoint = override_setpoint(self, nwkid, ep_out, setpoint, duration)
        schneider_update_ThermostatDevice(self, Devices, nwkid, ep_out, ClusterID, setpoint)
        schneider_data["BoostDemand"] = True

    elif action == CANCEL_BOOST :
        self.log.logging("Schneider", "Debug", "change_setpoint_for_time -- Cancel setpoint")
        cancel_override_attribute( self, nwkid )
        thermostat_override_current_setpoint = schneider_data.get("ThermostatOverride", {}).get("CurrentSetpoint")
        if thermostat_override_current_setpoint:
            schneider_update_ThermostatDevice(self, Devices, nwkid, ep_out, ClusterID, thermostat_override_current_setpoint)
    else:
        self.log.logging("Schneider", "Error", f"change_setpoint_for_time -- Unknown action: {action} setpoint: {setpoint} duration: {duration}", nwkid)


def cancel_override_attribute( self, nwkid ):
    if SCHNEIDER_META_DATA not in self.ListOfDevices[nwkid]:
        return
    if "ThermostatOverride" not in self.ListOfDevices[nwkid][SCHNEIDER_META_DATA]:
        return
    nickname = get_device_nickname(self, NwkId=nwkid)
    self.log.logging("Schneider", "Status", f"Cancelling temperature boost for device {nickname}", nwkid)
    
    del self.ListOfDevices[nwkid][SCHNEIDER_META_DATA]["ThermostatOverride"]
    self.ListOfDevices[nwkid ][SCHNEIDER_META_DATA]["BoostDemand"] = False


def check_end_of_override_setpoint(self, Devices, NwkId, Ep):
    """Check if the override setpoint duration has ended and revert the thermostat setpoint if needed."""

    device = self.ListOfDevices.get(NwkId, {})
    thermostat_override = self.ListOfDevices.get(NwkId, {}).get(SCHNEIDER_META_DATA, {}).get("ThermostatOverride", {})

    thermostat_override_override_setpoint = thermostat_override.get("OverrideSetpoint")
    thermostat_override_start_time = thermostat_override.get("OverrideStartTime")
    thermostat_override_duration = thermostat_override.get("OverrideDuration")
    thermostat_override_current_setpoint = thermostat_override.get("CurrentSetpoint")

    if None in (thermostat_override_override_setpoint, thermostat_override_start_time, thermostat_override_duration, thermostat_override_current_setpoint):
        return  # Missing required override data, exit early

    current_setpoint = device.get("Ep", {}).get(Ep, {}).get(THERMOSTAT_CLUSTER, {}).get(OCCUPIED_SETPOINT)

    remaining_time = int(thermostat_override_start_time + thermostat_override_duration - time())

    self.log.logging(
        "Schneider",
        "Debug",
        f"check_end_of_override_setpoint remains {remaining_time} sec before reverting Setpoint to {thermostat_override_current_setpoint} (from override {thermostat_override_override_setpoint})"
    )

    if remaining_time > 0 and current_setpoint != thermostat_override_override_setpoint:
        schneider_setpoint_thermostat(self, NwkId, thermostat_override_override_setpoint)
        schneider_update_ThermostatDevice(self, Devices, NwkId, Ep, THERMOSTAT_CLUSTER, thermostat_override_override_setpoint)

    if remaining_time <= 0:
        self.log.logging(
            "Schneider",
            "Debug",
            f"check_end_of_override_setpoint -- Time to update the Thermostat back from {thermostat_override_override_setpoint} to {thermostat_override_current_setpoint}"
        )
        schneider_setpoint_thermostat(self, NwkId, thermostat_override_current_setpoint)
        schneider_update_ThermostatDevice(self, Devices, NwkId, Ep, THERMOSTAT_CLUSTER, thermostat_override_current_setpoint)
        cancel_override_attribute(self, NwkId)


def override_setpoint(self, nwkid, ep, override, duration):
    """ Override the setpoint of a thermostat device for a specified duration. """

    self.log.logging("Schneider", "Debug", f"override_setpoint -- NwkId: {nwkid} Ep: {ep} Override: {override} Duration: {duration}")

    device = self.ListOfDevices.get(nwkid)
    if device is None:
        return

    schneider_meta_data = device.setdefault(SCHNEIDER_META_DATA, {})
    thermostat_override = schneider_meta_data.setdefault("ThermostatOverride", {})

    # Get current Setpoint
    current_setpoint = schneider_find_attribute(self, nwkid, ep, THERMOSTAT_CLUSTER, OCCUPIED_SETPOINT)
    if current_setpoint == {}:
        current_setpoint = 2000

    if "Param" in device:
        if "OverrideDurationInMinutes" in device["Param"]:
            duration = device["Param"]["OverrideDurationInMinutes"]
            self.log.logging("Schneider", "Debug", f"override_setpoint -- Get from Device Param Duration: {duration}")

        if "OverrideTempInDegree" in device["Param"]:
            if current_setpoint < override:
                override = current_setpoint + ( device["Param"]["OverrideTempInDegree"] * 100)
                override = min(override, 3000)
            else:
                override = current_setpoint - ( device["Param"]["OverrideTempInDegree"] * 100)
                override = max(override, 700)
            self.log.logging("Schneider", "Debug", f"override_setpoint -- override: {override}")

    thermostat_override["CurrentSetpoint"] = current_setpoint
    thermostat_override["OverrideSetpoint"] = override
    thermostat_override["OverrideDuration"] = duration * 60
    thermostat_override["OverrideStartTime"] = time()
    schneider_meta_data["BoostDemand"] = True
    
    nickname = get_device_nickname(self, NwkId=nwkid)
    self.log.logging("Schneider", "Status", f"Temperature boost for device {nickname} from {current_setpoint} to {override}", nwkid)

    return override


def iTRV_open_window_detection(self, NwkId, enable=False):

    self.log.logging("Schneider", "Debug", f"iTRV_open_window_detection enable: {enable}")


    manuf_id = SCHNEIDER_MANUF_ID
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0201

    Hattribute = "%04x" % 0xE013
    data_type = "20"  # Bool
    data = "04" if enable else "00"
    self.log.logging("Schneider", "Debug", f"iTRV_open_window_detection Schneider {NwkId} Write Attribute: 0xe013", nwkid=NwkId)

    write_attribute(
        self, NwkId, ZIGATE_EP, "01", cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )

    Hattribute = "%04x" % 0xE014
    data_type = "21"  # 16Uint
    data = "%04x" % 600 if enable else "00"
    self.log.logging("Schneider", "Debug", f"iTRV_open_window_detection Schneider {NwkId} Write Attribute: 0xe013", nwkid=NwkId)

    write_attribute(
        self, NwkId, ZIGATE_EP, "01", cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )

    Hattribute = "%04x" % 0xE015
    data_type = "21"  # 16Uint
    data = "%04x" % 120 if enable else "00"
    self.log.logging("Schneider", "Debug", f"iTRV_open_window_detection Schneider {NwkId} Write Attribute: 0xe013", nwkid=NwkId)

    write_attribute(
        self, NwkId, ZIGATE_EP, "01", cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )


def iTRV_local_temperature(self, nwk_id):
    """Retrieve the local temperature for an iTRV device in the WiserRoom."""
    
    self.log.logging("Schneider", "Debug", f"iTRV_local_temperature for: {nwk_id}")

    # Get room temperature from a related device
    wiser_room = get_wiserroom(self, nwk_id)
    room_temperature = get_local_temperature_from_wiserroom(self, nwk_id, wiser_room)

    self.log.logging("Schneider", "Debug", f"iTRV_local_temperature for: {nwk_id} room temp: {room_temperature}")

    # If no room temperature is found and the device is a Wiser2-Thermostat, fetch stored temperature
    if room_temperature is None and self.ListOfDevices.get(nwk_id, {}).get("Model") == "Wiser2-Thermostat":
        room_temperature = schneider_find_attribute_and_set(self, nwk_id, "01", TEMPERATURE_CLUSTER, TEMPERATURE_VALUE, 0) * 100

    return room_temperature if room_temperature is not None else 0x8000


def get_wiserroom(self, NwkId):
    """Retrieve the WiserRoomNumber for a given device if available."""
    self.log.logging("Schneider", "Debug", f"get_wiserroom for: {NwkId}")

    wiser_room = self.ListOfDevices.get(NwkId, {}).get("Param", {}).get("WiserRoomNumber")
    
    if wiser_room is not None:
        self.log.logging("Schneider", "Debug", f"get_wiserroom for: {NwkId} is room: {wiser_room}")
    
    return wiser_room


def get_local_temperature_from_wiserroom(self, NwkId, room=None):
    """Retrieve the local temperature from a device in the same WiserRoomNumber."""
    
    self.log.logging("Schneider", "Debug", f"get_local_temperature_from_wiserroom for: {NwkId} and room: {room}")
    
    if room is None:
        return None

    for x, device in self.ListOfDevices.items():
        
        if x == NwkId:
            continue
        
        wiser_room = device.get("Param", {}).get("WiserRoomNumber")
        if wiser_room != room:
            continue

        # We have a matching device in the same room
        self.log.logging("Schneider", "Debug", f"get_local_temperature_from_wiserroom: potential candidate {x}")

        # Ignore iTRV models
        if device.get("Model") in ("iTRV",):
            continue

        # Check for temperature sensor
        for ep_data in device.get("Ep", {}).values():
            temp_cluster = ep_data.get(TEMPERATURE_CLUSTER, {})
            if TEMPERATURE_VALUE in temp_cluster:
                local_temp = temp_cluster[TEMPERATURE_VALUE]
                self.log.logging("Schneider", "Debug", f"get_local_temperature_from_wiserroom: confirmed candidate {x} with temp: {local_temp}")

                if isinstance(local_temp, (int, float)):
                    return int(local_temp * 100)

    return None


def wiser_lift_duration( self, nwkid, duration):
    if 0 < duration < 300:
        write_attribute( self, nwkid, ZIGATE_EP, "05", "0102", SCHNEIDER_MANUF_ID, "01", "e000", "21", "%04x" % duration if 0 < duration < 300 else 120, ackIsDisabled=False)


SCHNEIDER_DEVICE_PARAMETERS = {
    "WiserLockThermostat": wiser_home_lockout_thermostat,
    "WiseriTrvWindowOpen": iTRV_open_window_detection,
    "WiserShutterDuration": wiser_lift_duration,
}
