#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38 & badz
#
"""
    Module: schneider_wiser.py

    Description:

"""

import json
import os.path
import struct
from time import time

import Domoticz
from Zigbee.zclCommands import zcl_onoff_off_noeffect, zcl_onoff_on

from Modules.basicOutputs import read_attribute, write_attribute
from Modules.bindings import WebBindStatus, webBind
from Modules.domoMaj import MajDomoDevice
from Modules.readAttributes import ReadAttributeRequest_0001
from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import (get_and_inc_ZCL_SQN, getAttributeValue,
                           is_ack_tobe_disabled,
                           retreive_cmd_payload_from_8002)
from Modules.writeAttributes import write_attribute_when_awake
from Modules.zigateConsts import MAX_LOAD_ZIGATE, ZIGATE_EP


WISER_LEGACY_MODEL_NAME_PREFIX = "EH-ZB"
WISER_LEGACY_BASE_EP = "0b"


def pollingSchneider(self, key):
    # sourcery skip: inline-immediately-returned-variable

    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """

    rescheduleAction = False

    return rescheduleAction


def callbackDeviceAwake_Schneider(self, Devices, NwkId, EndPoint, cluster):

    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part
    """

    self.log.logging(
        "Schneider",
        "Debug2",
        "callbackDeviceAwake_Schneider - Nwkid: %s, EndPoint: %s cluster: %s" % (NwkId, EndPoint, cluster),
        NwkId,
    )
    if cluster == "0201":
        callbackDeviceAwake_Schneider_SetPoints(self, NwkId, EndPoint, cluster)

    if (
        "Model" in self.ListOfDevices[NwkId]
        and self.ListOfDevices[NwkId]["Model"] == "EH-ZB-VACT"
        and "Schneider" in self.ListOfDevices[NwkId]
        and "ReportingMode" in self.ListOfDevices[NwkId]["Schneider"]
        and self.ListOfDevices[NwkId]["Schneider"]["ReportingMode"] == "Fast"
        and (self.ListOfDevices[NwkId]["Schneider"]["Registration"] + (14 * 60)) <= time()
    ):

        Domoticz.Log("%s/%s Switching Reporting to NORMAL mode" % (NwkId, EndPoint))
        vact_config_reporting_normal(self, NwkId, EndPoint)

    if "Model" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Model"] in ("Wiser2-Thermostat", "iTRV"):
        check_end_of_override_setpoint(self, Devices, NwkId, EndPoint)


def wiser_thermostat_monitoring_heating_demand(self, Devices):
    # Let check what is the Heating Demand
    updated_pi_demand = None

    for NwkId in list(self.ListOfDevices):
        if "Model" not in self.ListOfDevices[NwkId]:
            continue
        if self.ListOfDevices[NwkId]["Model"] != "Wiser2-Thermostat":
            continue
        if "Param" not in self.ListOfDevices[NwkId]:
            continue
        if "WiserRoomNumber" not in self.ListOfDevices[NwkId]["Param"]:
            continue
        if "0201" not in self.ListOfDevices[NwkId]["Ep"]["01"]:
            continue
        if "0008" not in self.ListOfDevices[NwkId]["Ep"]["01"]["0201"]:
            self.ListOfDevices[NwkId]["Ep"]["01"]["0201"]["0008"] = 0
        if "Model" not in self.ListOfDevices[NwkId]:
            continue

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
                if "0201" in self.ListOfDevices[x]["Ep"][y]:
                    if "0008" in self.ListOfDevices[x]["Ep"][y]["0201"]:
                        # Pi Demand based on 0201 Cluster
                        updated_pi_demand += int(self.ListOfDevices[x]["Ep"][y]["0201"]["0008"])
                        cnt_actioners += 1

                    elif "0702" in self.ListOfDevices[x]["Ep"][y] and "0400" in self.ListOfDevices[x]["Ep"][y]["0702"]:
                        # Mostlikely a FIP, then we check if there is some instant power or not
                        cnt_actioners += 1
                        if int(self.ListOfDevices[x]["Ep"][y]["0702"]["0400"]) > 0:
                            updated_pi_demand += 100

                elif "0006" in self.ListOfDevices[x]["Ep"][y]:
                    # It is a simple ON/Off
                    if "0000" in self.ListOfDevices[x]["Ep"][y]["0006"]:
                        cnt_actioners += 1
                        if int(self.ListOfDevices[x]["Ep"][y]["0006"]["0000"]):
                            updated_pi_demand += 100

        if cnt_actioners:
            # Domoticz.Log("---- Actioners: %s  Pi Demand: %s" %(cnt_actioners,updated_pi_demand ))
            self.ListOfDevices[NwkId]["Ep"]["01"]["0201"]["0008"] = int(round(updated_pi_demand / cnt_actioners))
            MajDomoDevice(
                self,
                Devices,
                NwkId,
                "01",
                "0201",
                self.ListOfDevices[NwkId]["Ep"]["01"]["0201"]["0008"],
                Attribute_="0008",
            )


def callbackDeviceAwake_Schneider_SetPoints(self, NwkId, EndPoint, cluster):

    # Schneider Wiser Valve Thermostat is a battery device, which receive commands only when it has sent a Report Attribut
    if "Model" not in self.ListOfDevices[NwkId]:
        return
    if self.ListOfDevices[NwkId]["Model"] != "EH-ZB-VACT":
        return
    if "0201" not in self.ListOfDevices[NwkId]["Ep"][EndPoint]:
        return

    # Manage SetPoint
    now = time()
    if "0012" in self.ListOfDevices[NwkId]["Ep"][EndPoint]["0201"]:
        if "Schneider" not in self.ListOfDevices[NwkId]:
            self.ListOfDevices[NwkId]["Schneider"] = {}
        if "Target SetPoint" in self.ListOfDevices[NwkId]["Schneider"]:
            if self.ListOfDevices[NwkId]["Schneider"]["Target SetPoint"] and self.ListOfDevices[NwkId]["Schneider"][
                "Target SetPoint"
            ] != int(self.ListOfDevices[NwkId]["Ep"][EndPoint]["0201"]["0012"]):
                # Protect against overloading Zigate
                if now > self.ListOfDevices[NwkId]["Schneider"]["TimeStamp SetPoint"] + 15:
                    schneider_setpoint(self, NwkId, self.ListOfDevices[NwkId]["Schneider"]["Target SetPoint"])
    # Manage Zone Mode
    if "e010" in self.ListOfDevices[NwkId]["Ep"][EndPoint]["0201"]:
        if "Target Mode" in self.ListOfDevices[NwkId]["Schneider"]:
            EHZBRTS_THERMO_MODE = {
                0: 0x00,
                10: 0x01,
                20: 0x02,
                30: 0x03,
                40: 0x04,
                50: 0x05,
                60: 0x06,
            }
            if self.ListOfDevices[NwkId]["Schneider"]["Target Mode"] is not None:
                if EHZBRTS_THERMO_MODE[self.ListOfDevices[NwkId]["Schneider"]["Target Mode"]] == int(
                    self.ListOfDevices[NwkId]["Ep"][EndPoint]["0201"]["e010"], 16
                ):
                    self.ListOfDevices[NwkId]["Schneider"]["Target Mode"] = None
                    self.ListOfDevices[NwkId]["Schneider"]["TimeStamp Mode"] = None
                else:
                    if now > self.ListOfDevices[NwkId]["Schneider"]["TimeStamp Mode"] + 15:
                        schneider_EHZBRTS_thermoMode(self, NwkId, self.ListOfDevices[NwkId]["Schneider"]["Target Mode"])


def schneider_wiser_registration(self, Devices, key):
    """
    This method is called during the pairing/discovery process.
    Purpose is to do some initialisation (write) on the coming device.
    """
    self.log.logging("Schneider", "Debug", "schneider_wiser_registration for device %s" % key, nwkid=key)

    #if (
    #    "Manufacturer Name" in self.ListOfDevices[key]
    #    and self.ListOfDevices[key]["Manufacturer Name"] == "Schneider Electric"
    #):
    #    return

    if "Model" in self.ListOfDevices[key] and self.ListOfDevices[key]["Model"] in ("iTRV",):
        iTRV_registration(self, key)
        wiser_home_lockout_thermostat(self, key, 0)

    if "Model" in self.ListOfDevices[key] and self.ListOfDevices[key]["Model"] in ("Wiser2-Thermostat",):
        wiser_home_lockout_thermostat(self, key, 0)

    if "Schneider" not in self.ListOfDevices[key]:
        self.ListOfDevices[key]["Schneider"] = {}
    self.ListOfDevices[key]["Schneider"]["Registration"] = int(time())

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
        self.ListOfDevices[key]["Schneider"]["ReportingMode"] = "Fast"

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
        self.log.logging(
            "Schneider",
            "Debug",
            "Schneider update Alarm Domoticz device Attribute %s Endpoint:%s / cluster: %s to %s"
            % (key, EPout, cluster_id, value),
            nwkid=key,
        )
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

    # Close the Network
    # ZigatePermitToJoin( self, 0 )


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
    self.log.logging(
        "Schneider",
        "Debug",
        "Schneider Write Attribute (zone_mode) %s with value %s / cluster: %s, attribute: %s type: %s"
        % (key, data, cluster_id, Hattribute, data_type),
        nwkid=key,
    )
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
    self.log.logging(
        "Schneider",
        "Debug",
        "Schneider Write Attribute (zone name) %s with value %s / cluster: %s, attribute: %s type: %s"
        % (key, data, cluster_id, Hattribute, data_type),
        nwkid=key,
    )
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

    if "Schneider" not in self.ListOfDevices[key]:
        self.ListOfDevices[key]["Schneider"] = {}

    if (
        "Calibration" in self.ListOfDevices[key]["Schneider"]
        and calibration == 10 * self.ListOfDevices[key]["Schneider"]["Calibration"]
    ):
        return

    if calibration < -25:
        calibration = -24
    if calibration > 25:
        calibration = 24

    if calibration < 0:
        # in two’s complement form
        calibration = int(hex(-calibration - pow(2, 32))[9:], 16)

    Domoticz.Log("Calibration: 0x%02x" % calibration)

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
    self.log.logging(
        "Schneider",
        "Debug",
        "wiser_set_thermostat_window_detection - Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
        % (key, data, cluster_id, Hattribute, data_type),
        nwkid=key,
    )
    write_attribute(
        self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )


def wiser_set_commission_done(self, key, EPout):  # 0x0000/0xE050
    manuf_id = "105e"
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0000
    Hattribute = "%04x" % 0xE050
    data_type = "10"  # Bool
    data = "%02x" % True
    self.log.logging(
        "Schneider",
        "Debug",
        "wiser_set_commission_done Schneider Write Attribute (commisionning done) %s with value %s / Endpoint : %s, cluster: %s, attribute: %s type: %s"
        % (key, data, EPout, cluster_id, Hattribute, data_type),
        nwkid=key,
    )
    write_attribute(
        self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )


def wiser_set_lang(self, key, EPout, lang="eng"):  # 0x0000/0x5011
    manuf_id = "105e"
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0000
    Hattribute = "%04x" % 0x5011
    data_type = "42"  # String
    data = lang.encode("utf-8").hex()  # 'en'
    self.log.logging(
        "Schneider",
        "Debug",
        "wiser_set_lang Schneider Write Attribute (Lang) %s with value %s / cluster: %s, attribute: %s type: %s"
        % (key, data, cluster_id, Hattribute, data_type),
        nwkid=key,
    )
    write_attribute(
        self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )


def iTRV_registration(self, NwkId):
    manuf_id = "105e"
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0201
    Hattribute = "%04x" % 0xE103
    data_type = "10"  # Bool
    data = "01"
    self.log.logging("Schneider", "Debug", "iTRV_registration Schneider Write Attribute %s" % (NwkId), nwkid=NwkId)
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
    """[summary]
         allows to set the heater in "fip" or "conventional" mode
         by default it will set it to fip mode
    Arguments:
        key {[int]} -- id of the device
        type {[string]} -- type of heater "fip" of "conventional"
    """
    EPout = WISER_LEGACY_BASE_EP

    attrValue = getAttributeValue(self, key, EPout, "0201", "e011")
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

    current_value = current_value - 0x80
    if type_heater == "conventional":
        new_value = current_value & 0xFD  # we set the bit 1 to 0 and dont touch the other ones . logical_AND 1111 1101
    elif type_heater == "fip":
        new_value = current_value | 2  # we set the bit 1 to 1 and dont touch the other ones . logical_OR 0000 0010
    elif type_heater == "registration":
        new_value = current_value

    new_value = new_value & 3  # cleanup, to remove everything else but the last two bits
    if (current_value == new_value) and not force_update:  # no change, let's get out
        return

    manuf_id = "105e"
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

    if EPout in self.ListOfDevices[key]["Ep"] and "0201" in self.ListOfDevices[key]["Ep"][EPout]:
        self.ListOfDevices[key]["Ep"][EPout]["0201"]["e011"] = "%02x" % (new_value + 0x80)


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

    attrValue = getAttributeValue(self, key, EPout, "0201", "e011")
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

    current_value = current_value - 0x80
    if mode == "setpoint":
        new_value = current_value & 0xFE  # we set the bit 0 to 0 and dont touch the other ones . logical_AND 1111 1110

    elif mode == "FIP":
        new_value = current_value | 1  # we set the bit 0 to 1 and dont touch the other ones . logical_OR 0000 0001

    new_value = new_value & 3  # cleanup, to remove everything else but the last two bits
    if (current_value == new_value) and not force_update:  # no change, let's get out
        return

    manuf_id = "105e"
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
        if "0201" in self.ListOfDevices[key]["Ep"][EPout]:
            self.ListOfDevices[key]["Ep"][EPout]["0201"]["e011"] = "%02x" % (new_value + 0x80)


def schneider_hact_fip_mode(self, key, mode):
    """[summary]
        set fil pilote mode for the actuator
    Arguments:
        key {[int]} -- id of actuator
        mode {[string]} -- 'Confort' , 'Confort -1' , 'Confort -2', 'Eco', 'Frost Protection', 'Off'
    """
    # APS Data: 0x00 0x0b 0x01 0x02 0x04 0x01 0x0b 0x45 0x11 0xc1 0xe1 0x00 0x01 0x03

    MODE = {"Confort": 0x00, "Confort -1": 0x01, "Confort -2": 0x02, "Eco": 0x03, "Frost Protection": 0x04, "Off": 0x05}

    self.log.logging(
        "Schneider", "Debug", "schneider_hact_fip_mode for device %s requesting mode: %s" % (key, mode), key
    )

    if mode not in MODE:
        _context = {"Error code": "SCHN0003", "mode": mode, "MODE": MODE}
        self.log.logging(
            "Schneider", "Error", "schneider_hact_fip_mode - %s unknown mode: %s" % (key, mode), key, _context
        )

    EPout = WISER_LEGACY_BASE_EP

    schneider_hact_heating_mode(self, key, "FIP")

    cluster_frame = "11"
    sqn = get_and_inc_ZCL_SQN(self, key)
    cmd = "e1"

    zone_mode = "01"  # Heating
    fipmode = "%02X" % MODE[mode]
    prio = "01"  # Prio

    payload = cluster_frame + sqn + cmd + zone_mode + fipmode + prio + "ff"

    self.log.logging(
        "Schneider",
        "Debug",
        "schneider_hact_fip_mode for device %s sending command: %s , zone_monde: %s, fipmode: %s"
        % (key, cmd, zone_mode, fipmode),
        key,
    )

    raw_APS_request(
        self, key, EPout, "0201", "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=is_ack_tobe_disabled(self, key)
    )
    # Reset Heartbeat in order to force a ReadAttribute when possible
    self.ListOfDevices[key]["Heartbeat"] = "0"


def schneider_thermostat_check_and_bind(self, key, forceRebind=False):
    """bind the thermostat to the actuators based on the zoning json fie
    Arguments:
        key {[type]} -- [description]
    """
    self.log.logging("Schneider", "Debug", "schneider_thermostat_check_and_bind : %s " % key, key)

    importSchneiderZoning(self)
    if self.SchneiderZone is None:
        return

    Cluster_bind1 = "0201"
    Cluster_bind2 = "0402"
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
    self.log.logging("Schneider", "Debug", "schneider_actuator_check_and_bind : %s " % key, key)

    importSchneiderZoning(self)
    if self.SchneiderZone is None:
        return

    Cluster_bind1 = "0201"
    Cluster_bind2 = "0402"
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

    ClusterID = "0201"
    attr = "0012"
    NWKID = key

    schneider_find_attribute_and_set(self, NWKID, EPout, ClusterID, attr, setpoint, setpoint)

    importSchneiderZoning(self)
    schneider_thermostat_check_and_bind(self, NWKID)

    if self.SchneiderZone is not None:
        for zone in self.SchneiderZone:
            self.log.logging("Schneider", "Debug", "schneider_setpoint - Zone Information: %s " % zone, NWKID)
            if self.SchneiderZone[zone]["Thermostat"]["NWKID"] == NWKID:
                self.log.logging("Schneider", "Debug", "schneider_setpoint - found %s " % zone, NWKID)
                for hact in self.SchneiderZone[zone]["Thermostat"]["HACT"]:
                    self.log.logging("Schneider", "Debug", "schneider_setpoint - found hact %s " % hact, NWKID)
                    schneider_setpoint_actuator(self, hact, setpoint)
                    # Reset Heartbeat in order to force a ReadAttribute when possible
                    self.ListOfDevices[key]["Heartbeat"] = "0"
                    schneider_actuator_check_and_bind(self, hact)
                    # ReadAttributeRequest_0201(self,key)


def schneider_setpoint_actuator(self, key, setpoint):
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
        self.log.logging(
            "Schneider", "Debug", "schneider_setpoint_actuator - unknown key: %s in ListOfDevices!" % (key)
        )
        return

    cluster_frame = "11"
    sqn = "00"

    EPout = "01"
    for tmpEp in self.ListOfDevices[key]["Ep"]:
        if "0201" in self.ListOfDevices[key]["Ep"][tmpEp]:
            EPout = tmpEp
    sqn = get_and_inc_ZCL_SQN(self, key)

    cmd = "e0"

    setpoint = int((setpoint * 2) / 2)  # Round to 0.5 degrees
    if "Schneider" not in self.ListOfDevices[key]:
        self.ListOfDevices[key]["Schneider"] = {}
    self.ListOfDevices[key]["Schneider"]["Target SetPoint"] = setpoint
    self.ListOfDevices[key]["Schneider"]["TimeStamp SetPoint"] = int(time())

    # Make sure that we are in setpoint Mode
    if "Model" in self.ListOfDevices[key] and self.ListOfDevices[key]["Model"] == "EH-ZB-HACT":
        schneider_hact_heating_mode(self, key, "setpoint")

    setpoint = "%04X" % setpoint
    zone = "01"

    payload = cluster_frame + sqn + cmd + "00" + zone + setpoint[2:4] + setpoint[0:2] + "ff"

    raw_APS_request(
        self, key, EPout, "0201", "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=is_ack_tobe_disabled(self, key)
    )
    # Reset Heartbeat in order to force a ReadAttribute when possible
    self.ListOfDevices[key]["Heartbeat"] = "0"
    # ReadAttributeRequest_0201(self,key)


def schneider_setpoint(self, NwkId, setpoint):

    if NwkId not in self.ListOfDevices:
        self.log.logging("Schneider", "Debug", "schneider_setpoint - unknown NwkId: %s in ListOfDevices!" % (NwkId))
        return

    if "Model" in self.ListOfDevices[NwkId]:
        if self.ListOfDevices[NwkId]["Model"] in ("EH-ZB-RTS", "Wiser2-Thermostat", ):
            schneider_setpoint_thermostat(self, NwkId, setpoint)
            
        elif self.ListOfDevices[NwkId]["Model"] in ( "iTRV", ): 
            schneider_setpoint_thermostat(self, NwkId, setpoint)   
            
        elif self.ListOfDevices[NwkId]["Model"] == "EH-ZB-VACT":
            wiser_set_calibration(self, NwkId, WISER_LEGACY_BASE_EP)
            schneider_setpoint_thermostat(self, NwkId, setpoint)
            schneider_setpoint_actuator(self, NwkId, setpoint)
        else:
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
        self.log.logging("Schneider", "Debug", "schneider_temp_Setcurrent - unknown key: %s in ListOfDevices!" % (key))
        return

    cluster_frame = "18"
    attr = "0000"
    sqn = "00"
    dataType = "29"
    sqn = get_and_inc_ZCL_SQN(self, key)

    cmd = "0a"

    setpoint = int((setpoint * 2) / 2)  # Round to 0.5 degrees
    setpoint = "%04X" % setpoint

    payload = cluster_frame + sqn + cmd + attr + dataType + setpoint[2:4] + setpoint[0:2]

    EPout = "01"
    for tmpEp in self.ListOfDevices[key]["Ep"]:
        if "0402" in self.ListOfDevices[key]["Ep"][tmpEp]:
            EPout = tmpEp

    self.log.logging(
        "Schneider",
        "Debug",
        "schneider_temp_Setcurrent for device %s sending command: %s , setpoint: %s" % (key, cmd, setpoint),
        key,
    )

    # In the case of VACT, the device is listening more a less every 30s to 50s,
    # if raw_APS is not sent with ACK there is a risk to lost the command !
    disableAck = True
    if "PowerSource" in self.ListOfDevices[key] and self.ListOfDevices[key]["PowerSource"] == "Battery":
        disableAck = False
    read_attribute(self, key, ZIGATE_EP, EPout, "0201", "00", "00", "0000", 1, "0012", ackIsDisabled=disableAck)
    raw_APS_request(
        self, key, EPout, "0402", "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=is_ack_tobe_disabled(self, key)
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
        self.log.logging(
            "Schneider", "Debug", "schneider_EHZBRTS_thermoMode - unknown key: %s in ListOfDevices!" % (key)
        )
        return

    self.log.logging("Schneider", "Debug", "schneider_EHZBRTS_thermoMode - %s Mode: %s" % (key, mode), key)

    if mode not in EHZBRTS_THERMO_MODE:
        _context = {"Error code": "SCHN0004", "mode": mode, "MODE": EHZBRTS_THERMO_MODE}
        self.log.logging("Schneider", "Error", "Unknow Thermostat Mode %s for %s" % (mode, key), key, _context)
        return

    if "Schneider" not in self.ListOfDevices[key]:
        self.ListOfDevices[key]["Schneider"] = {}
    self.ListOfDevices[key]["Schneider"]["Target Mode"] = mode
    self.ListOfDevices[key]["Schneider"]["TimeStamp Mode"] = int(time())

    manuf_id = "105e"
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0201
    Hattribute = "%04x" % 0xE010
    data_type = "30"  # Uint8
    data = "%02x" % EHZBRTS_THERMO_MODE[mode]

    EPout = "01"
    for tmpEp in self.ListOfDevices[key]["Ep"]:
        if "0201" in self.ListOfDevices[key]["Ep"][tmpEp]:
            EPout = tmpEp

    self.log.logging(
        "Schneider",
        "Debug",
        "Schneider EH-ZB-RTS Thermo Mode  %s with value %s / cluster: %s, attribute: %s type: %s"
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

    self.ListOfDevices[key]["Heartbeat"] = "0"


def schneiderRenforceent(self, NWKID):

    if NWKID not in self.ListOfDevices:
        self.log.logging("Schneider", "Debug", "schneiderRenforceent - unknown key: %s in ListOfDevices!" % (NWKID))
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


def schneider_thermostat_answer_attribute_request(self, NWKID, EPout, ClusterID, sqn, attr):
    """Receive an attribute request from thermostat to know if the user has change the domoticz widget
        we answer the current temperature stored in the device

    Arguments:
        NWKID {[type]} -- [description]
        EPout {[type]} -- [description]
        ClusterID {[type]} -- [description]
        sqn {[type]} -- [description]
        rawAttr {[type]} -- [description]
    """
    self.log.logging(
        "Schneider",
        "Debug",
        "Schneider receive attribute request: nwkid %s ep: %s , clusterId: %s, sqn: %s,rawAttr: %s"
        % (NWKID, EPout, ClusterID, sqn, attr),
        NWKID,
    )

    data = dataType = payload = ""

    zigate_ep = ZIGATE_EP
    if "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] in ("Wiser2-Thermostat",):
        EPout = "01"
        zigate_ep = "01"
        cluster_frame = "08"
    elif "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] in ("iTRV",):
        EPout = "02"
        zigate_ep = "01"
        cluster_frame = "08"        
    else:
        cluster_frame = "18"

    if attr == "0000":  # Local Temperature
        dataType = "29"
        if ( "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] in ( "iTRV",) ):
            # In case we have an iTRV alone (no room sensor, then we just return 0x8000)
            data = '%04x' %iTRV_local_temperature(self, NWKID)
        else:
            data = "%04x" % int(100 * schneider_find_attribute(self, NWKID, "01", "0201", "0000"))

    elif attr == "e010":  # mode of operation
        dataType = "30"
        data = "01"  # Manual

    elif attr == "0015":  # min setpoint temp
        dataType = "29"
        data = ( "02bc" if self.ListOfDevices[NWKID]["Model"] in ("EH-ZB-VACT",) else "0032" )

    elif attr == "0016":  # max setpoint temp
        dataType = "29"
        data = ( "0bb8" if self.ListOfDevices[NWKID]["Model"] in ("EH-ZB-VACT",) else "0dac" )

    elif attr == "0012":  # occupied setpoint temp
        dataType = "29"
        value = int(schneider_find_attribute_and_set(self, NWKID, EPout, ClusterID, attr, 2000))
        data = "%04X" % value

    elif attr == "001c":  # System Mode for Wiser Home
        dataType = "30"  # enum8
        data = "04"  # 0x00 Off, 0x01 Auto, 0x04 Heat

    elif attr == "001b":  # ControlSequenceOfOperation for Wiser Home
        dataType = "30"  # enum8
        data = "02"  # Heating only

    elif attr == "0008":  # Pi Heating Demand  (valve position %) for Wiser Home
        # In case of iTRV, it looks like we have to trigger the heating demand.
        # In case the new setpoint is above the local temp, and the Heating Demand is 0, let's enable it
        define_heating_demand_for_iTRV(self, NWKID)

        dataType = "20"  # uint8
        #data = "%02x" % self.ListOfDevices[NWKID]["Ep"]["01"]["0201"]["0008"]
        data = "%02x" % schneider_find_attribute_and_set(self, NWKID, EPout, "0201", "0008", 0)

    elif attr == "e110":  # ?? for Wiser Home
        dataType = "30"  # enum8
        data = "01"  # 0x02 then 0x030, 0x11

    else:
        return

    if data == dataType == "":
        # Unable to find a match
        wiser_unsupported_attribute(self, NWKID, EPout, sqn, ClusterID, attr)
        return

    cmd = "01"
    status = "00"

    self.log.logging(
        "Schneider",
        "Debug",
        "schneider_thermostat_answer_attribute_request: nwkid %s ep: %s , clusterId: %s, sqn: %s, attr: %s, dataType: %s, data: %s"
        % (NWKID, EPout, ClusterID, sqn, attr, dataType, data),
        NWKID,
    )

    if dataType == "29":
        payload = cluster_frame + sqn + cmd + attr[2:4] + attr[0:2] + status + dataType + data[2:4] + data[0:2]
    else:
        payload = cluster_frame + sqn + cmd + attr[2:4] + attr[0:2] + status + dataType + data
    raw_APS_request(
        self,
        NWKID,
        EPout,
        ClusterID,
        "0104",
        payload,
        zigate_ep=zigate_ep,
        ackIsDisabled=is_ack_tobe_disabled(self, NWKID),
    )

def define_heating_demand_for_iTRV(self, NwkId):
    # We force to use Ep 0x01 even if the iTRV is communicating on Ep 0x02
    
    if "Model" not in self.ListOfDevices[NwkId] or self.ListOfDevices[NwkId]["Model"] not in ( "Wiser2-Thermostat", "iTRV",):
        return

    local_temp = iTRV_local_temperature(self, NwkId)
    self.log.logging(
        "Schneider",
        "Debug",
        "define_heating_demand_for_iTRV: 0x0000 = %s (%s) 0x0012 %s (%s)" %(
            schneider_find_attribute(self, NwkId, "01", "0201", "0000"), type(schneider_find_attribute(self, NwkId, "01", "0201", "0000")),
            schneider_find_attribute(self, NwkId, "01", "0201", "0012"), type(schneider_find_attribute(self, NwkId, "01", "0201", "0012"))))
    
    if local_temp == 0x8000:
        # We use the inside Temp sensor, let's get local temperature
        local_temp = int( 100 * schneider_find_attribute(self, NwkId, "01", "0201", "0000") )
    gap_temp = local_temp - int(schneider_find_attribute(self, NwkId, "01", "0201", "0012"))
    self.log.logging(
        "Schneider",
        "Debug",
        "define_heating_demand_for_iTRV: Local_temp: %s , Target: %s gap: %s" %(
            local_temp, int(schneider_find_attribute(self, NwkId, "01", "0201", "0012")), gap_temp))
    
    if ( schneider_find_attribute_and_set( self, NwkId, "01", "0201", "0008", 0 ) == 0 and  gap_temp < 0):
        if gap_temp < -500:
            self.ListOfDevices[NwkId]["Ep"]["01"]["0201"]["0008"] = 100
        elif gap_temp < -250:
            self.ListOfDevices[NwkId]["Ep"]["01"]["0201"]["0008"] = 75
        elif gap_temp < -100:
            self.ListOfDevices[NwkId]["Ep"]["01"]["0201"]["0008"] = 50
        else:
            self.ListOfDevices[NwkId]["Ep"]["01"]["0201"]["0008"] = 25

    elif ( schneider_find_attribute_and_set( self, NwkId, "01", "0201", "0008", 0 ) != 0 and  gap_temp > 0):
        self.ListOfDevices[NwkId]["Ep"]["01"]["0201"]["0008"] = 0
    self.log.logging(
        "Schneider",
        "Debug",
        "define_heating_demand_for_iTRV: Local_temp: %s , Target: %s gap: %s Heating Demand: %s" %(
            local_temp, int(schneider_find_attribute(self, NwkId, "01", "0201", "0012")), gap_temp, self.ListOfDevices[NwkId]["Ep"]["01"]["0201"]["0008"]))


def schneider_update_ThermostatDevice(self, Devices, NWKID, srcEp, ClusterID, setpoint):
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

    # Look for TargetSetPoint
    domoTemp = round(setpoint / 100, 1)

    self.log.logging(
        "Schneider", "Debug", "Schneider updateThermostat setpoint:%s  , domoTemp : %s" % (setpoint, domoTemp), NWKID
    )

    MajDomoDevice(self, Devices, NWKID, srcEp, ClusterID, domoTemp, "0012")

    # modify attribute of thermostat to store the new temperature requested
    schneider_find_attribute_and_set(self, NWKID, srcEp, ClusterID, "0012", setpoint, setpoint)

    importSchneiderZoning(self)
    if self.SchneiderZone is not None:
        for zone in self.SchneiderZone:
            if self.SchneiderZone[zone]["Thermostat"]["NWKID"] == NWKID:
                self.log.logging("Schneider", "Debug", "schneider_update_ThermostatDevice - found %s " % zone, NWKID)
                for hact in self.SchneiderZone[zone]["Thermostat"]["HACT"]:
                    self.log.logging(
                        "Schneider",
                        "Debug",
                        "schneider_update_ThermostatDevice - update hact setpoint mode hact nwwkid:%s " % hact,
                        NWKID,
                    )
                    schneider_hact_heating_mode(self, hact, "setpoint")


def schneiderAlarmReceived(self, Devices, NWKID, srcEp, ClusterID, start, payload):
    """
    Function called when a command is received from the schneider device to alert about over consumption
    """

    AlertCode = int(payload[0:2], 16)  # uint8  0x10: low voltage, 0x11 high voltage, 0x16 high current

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
                if "0702" in self.ListOfDevices[NWKID]["Ep"][srcEp]:
                    current_consumption = float(self.ListOfDevices[NWKID]["Ep"][srcEp]["0702"]["0400"])

            if ("Schneider" in self.ListOfDevices[NWKID]) and (
                "contractPowerLevel" in self.ListOfDevices[NWKID]["Schneider"]
            ):
                contractPowerLevel = self.ListOfDevices[NWKID]["Schneider"]["contractPowerLevel"]
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
            if "Shedding" in self.ListOfDevices[NWKID]:
                if not self.ListOfDevices[NWKID]["Shedding"]:
                    self.log.logging("Schneider", "Debug", "schneiderAlarmReceived not shedding - EXIT", NWKID)
                    return  # we are already shedding
            value = "00"
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
    self.log.logging(
        "Schneider",
        "Debug",
        "schneider_set_contract for device %s %s requesting max_real_milli_amps_before_tripping: %s milliamps"
        % (key, EPout, max_real_milli_amps_before_tripping),
        key,
    )

    if "Schneider" not in self.ListOfDevices[key]:
        self.ListOfDevices[key]["Schneider"] = {}

    self.ListOfDevices[key]["Schneider"]["contractPowerLevel"] = kva * 1000

    ClusterId = "0702"  # Simple Metering
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
    self.log.logging(
        "Schneider",
        "Debug",
        "Schneider read raw APS nwkid: %s ep: %s , clusterId: %s, dstnwkid: %s, dstep: %s, payload: %s"
        % (srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload),
        srcNWKID,
    )

    GlobalCommand, Sqn, ManufacturerCode, Command, Data = retreive_cmd_payload_from_8002(MsgPayload)
    self.log.logging("Schneider", "Debug", "         -- SQN: %s, CMD: %s, Data: %s" % (Sqn, Command, Data), srcNWKID)

    if ClusterID == "0201":  # Thermostat cluster
        if GlobalCommand and Command == "00":  # read attributes
            # ManufSpec = "00"
            # ManufCode = "0000"
            # if ManufacturerCode:
            #     ManufSpec = "01"
            #     ManufCode = ManufacturerCode
            # buildPayload = (
            #     Sqn + srcNWKID + srcEp + "01" + ClusterID + "01" + ManufSpec + ManufCode + "%02x" % (len(Data) // 4)
            # )
            idx = nbAttribute = 0
            while idx < len(Data):
                nbAttribute += 1
                Attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx: idx + 4], 16)))[0]
                idx += 4
                if self.FirmwareVersion and int(self.FirmwareVersion, 16) <= 0x031C:
                    wiser_unsupported_attribute(self, srcNWKID, srcEp, Sqn, ClusterID, Attribute)
                else:
                    self.log.logging(
                        "Schneider",
                        "Debug",
                        "Schneider cmd 0x00 [%s] Read Attribute Request on Src: %s/%s for %s/%s Dst: %s/%s" % (
                            Sqn, srcNWKID, srcEp, ClusterID, Attribute, dstNWKID, dstEP),
                        srcNWKID,
                    )
                    schneider_thermostat_answer_attribute_request(self, srcNWKID, srcEp, ClusterID, Sqn, Attribute)

        elif not GlobalCommand and Command == "00":  # Setpoint Raise/Lower
            # Decode8002 - NwkId: 656d Ep: 01 Cluster: 0201 GlobalCommand: False Command: 00 Data: 00fb  - 0,05
            # inRawAps Nwkid: 656d Ep: 01 Cluster: 0201 ManufCode: None manuf: 105e manuf_name: Schneider Electric Cmd: 00 Data: 0005   + 0,05
            setpoint_mode = Data[0:2]
            amount = Data[2:4]
            wiser2_setpoint_raiserlower(self, Devices, srcNWKID, setpoint_mode, amount)

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

    amount = int((struct.unpack("b", struct.pack(">B", int(amount, 16)))[0])) * 10

    if mode == "00":  # Heat adjust Heat Setpoint
        self.log.logging("Schneider", "Debug", "wiser2_setpoint_raiserlower cmd Mode [Heat] amount: %s" % amount)
        value = schneider_find_attribute_and_set(self, NwkId, "01", "0201", "0012", 2000)
        setpoint = int(((value + amount) * 20) / 20)  # Round to °.5
        schneider_update_ThermostatDevice(self, Devices, NwkId, "01", "0201", setpoint)

    elif mode == "01":  # Cool (adjust Cool Setpoint)
        self.log.logging("Schneider", "Debug", "wiser2_setpoint_raiserlower cmd Mode [Cool] amount: %s" % amount)
        value = schneider_find_attribute_and_set(self, NwkId, "01", "0201", "0011", 2000)
        schneider_find_attribute_and_set(self, NwkId, "01", "0201", "0011", 2000, newValue=value + amount)

    elif mode == "02":  # Both ( adjust Heat Setpoint and Cool Setpoint)
        self.log.logging("Schneider", "Debug", "wiser2_setpoint_raiserlower cmd Mode [Heat+Cool] amount: %s" % amount)


def wiserhome_ZCLVersion_response(self, Devices, srcNWKID, srcEp, Sqn):
    cmd = "01"
    status = "00"
    cluster_frame = "08"

    dataType = "20"
    ZCLVersion = "03"
    payload = cluster_frame + Sqn + cmd + "0000" + status + dataType + ZCLVersion
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
    self.log.logging(
        "Schneider",
        "Debug",
        "Schneider Wiser Home Response ZCLVersion %s to device %s" % (ZCLVersion, srcNWKID),
        srcNWKID,
    )


def wiser_read_attribute_request(self, NwkId, Ep, Sqn, ClusterId, Attribute):

    if self.FirmwareVersion and int(self.FirmwareVersion, 16) <= 0x031C:
        # We shouldn't reach here, as the firmware itself will reject and respond.
        wiser_unsupported_attribute(self, NwkId, Ep, Sqn, ClusterId, Attribute)
    else:
        self.log.logging(
            "Schneider",
            "Debug",
            "Schneider cmd 0x00 [%s] Read Attribute Request on %s/%s" % (Sqn, ClusterId, Attribute),
            NwkId,
        )
        schneider_thermostat_answer_attribute_request(self, NwkId, Ep, ClusterId, Sqn, Attribute)


def wiser_unsupported_attribute(self, srcNWKID, srcEp, Sqn, ClusterID, attribute):
    cluster_frame = "18"
    cmd = "01"
    payload = cluster_frame + Sqn + cmd + attribute[2:4] + attribute[0:2] + "86"
    self.log.logging(
        "Schneider",
        "Debug",
        "wiser_unsupported_attribute for device %s sending command: %s , attribute: %s" % (srcNWKID, cmd, attribute),
        srcNWKID,
    )
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

    self.SchneiderZoningFilename = self.pluginconf.pluginConf["pluginConfig"] + SCHNEIDER_ZONING

    if not os.path.isfile(self.SchneiderZoningFilename):
        self.log.logging(
            "Schneider", "Debug", "importSchneiderZoning - Nothing to import from %s" % self.SchneiderZoningFilename
        )
        self.SchneiderZone = None
        return

    self.SchneiderZone = {}
    with open(self.SchneiderZoningFilename, "rt") as handle:
        SchneiderZoning = json.load(handle)

    for zone in SchneiderZoning:
        if "ieee_thermostat" not in SchneiderZoning[zone]:
            # Missing Thermostat
            _context = {"Error code": "SCHN0005", "zone": zone, "SchneiderZoning": SchneiderZoning[zone]}
            self.log.logging(
                "Schneider",
                "Error",
                "importSchneiderZoning - Missing Thermostat entry in %s" % SchneiderZoning[zone],
                context=_context,
            )
            continue

        if SchneiderZoning[zone]["ieee_thermostat"] not in self.IEEE2NWK:
            # Thermostat IEEE not known!
            _context = {
                "Error code": "SCHN0006",
                "zone": zone,
                "SchneiderZoning[zone]": SchneiderZoning[zone]["ieee_thermostat"],
                "IEEE": self.IEEE2NWK,
            }
            self.log.logging(
                "Schneider",
                "Error",
                "importSchneiderZoning - Thermostat IEEE %s do not exist" % SchneiderZoning[zone]["ieee_thermostat"],
                context=_context,
            )
            continue

        self.SchneiderZone[zone] = {"Thermostat": {"IEEE": SchneiderZoning[zone]["ieee_thermostat"]}}

        self.SchneiderZone[zone]["Thermostat"]["NWKID"] = self.IEEE2NWK[SchneiderZoning[zone]["ieee_thermostat"]]
        self.SchneiderZone[zone]["Thermostat"]["HACT"] = {}

        if "actuator" not in SchneiderZoning[zone]:
            # We just have a simple Thermostat
            _context = {"Error code": "SCHN0007", "zone": zone, "SchneiderZoning": SchneiderZoning[zone]}
            self.log.logging(
                "Schneider", "Debug", "importSchneiderZoning - No actuators for this Zone: %s" % zone, context=_context
            )
            continue

        for hact in SchneiderZoning[zone]["actuator"]:
            if hact in list(self.IEEE2NWK):
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
                    self.log.logging(
                        "Schneider", "Error", "importSchneiderZoning - Unknown HACT: %s" % hact, _nwkid, _context
                    )
                    continue

                if self.IEEE2NWK[hact] not in self.ListOfDevices:
                    # Unknown in ListOfDevices
                    _context = {
                        "Error code": "SCHN0009",
                        "zone": zone,
                        "hact": hact,
                        "SchneiderZoning[zone]": SchneiderZoning[zone]["actuator"],
                    }
                    self.log.logging(
                        "Schneider", "Error", "importSchneiderZoning - Unknown HACT: %s" % _nwkid, _nwkid, _context
                    )
                    continue

                self.SchneiderZone[zone]["Thermostat"]["HACT"][_nwkid] = {"IEEE": hact}
    # At that stage we have imported all informations
    self.log.logging("Schneider", "Debug", "importSchneiderZoning - Zone Information: %s " % self.SchneiderZone)


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
    """[summary]

    Arguments:
        NWKID {int} -- id of the device
        EP {[type]} -- endpoint of the device you want to manipulate
        ClusterID {[type]} -- cluster of the device you want to manipulate
        attr {[type]} -- attribute of the device you want to manipulate
        defaultValue {[type]} -- default value to use if there is no existing value

    Keyword Arguments:
        newValue {[type]} -- value to erase the existing value (if none then the existing value is untouched)

    Returns:
        [type] -- the value that the attribute will have once the function is finished
                    if no existing value -> defaultValue
                    if there is an existing value and newValue = None -> existing value
                    ifthere is an  existing value and newValue != none -> newValue
    """
    self.log.logging(
        "Schneider",
        "Debug",
        "schneider_find_attribute_or_set NWKID:%s, EP:%s, ClusterID:%s, attr:%s ,defaultValue:%s, newValue:%s"
        % (NWKID, EP, ClusterID, attr, defaultValue, newValue),
        NWKID,
    )
    if "Model" in self.ListOfDevices[NWKID] and  self.ListOfDevices[NWKID]["Model"] in ( "iTRV",):
        EP = '01'   # Indeed iTRV request on Ep 0x02, but we store all on Ep 0x01

    found = newValue
    if EP not in self.ListOfDevices[NWKID]["Ep"]:
        self.ListOfDevices[NWKID]["Ep"][EP] = {}
    if ClusterID not in self.ListOfDevices[NWKID]["Ep"][EP]:
        self.ListOfDevices[NWKID]["Ep"][EP][ClusterID] = {}
    if not isinstance(self.ListOfDevices[NWKID]["Ep"][EP][ClusterID], dict):
        self.ListOfDevices[NWKID]["Ep"][EP][ClusterID] = {}
    if attr not in self.ListOfDevices[NWKID]["Ep"][EP][ClusterID]:
        self.ListOfDevices[NWKID]["Ep"][EP][ClusterID][attr] = {}
    if (
        "Ep" in self.ListOfDevices[NWKID]
        and EP in self.ListOfDevices[NWKID]["Ep"]
        and ClusterID in self.ListOfDevices[NWKID]["Ep"][EP]
        and attr in self.ListOfDevices[NWKID]["Ep"][EP][ClusterID]
    ):
        if self.ListOfDevices[NWKID]["Ep"][EP][ClusterID][attr] == {}:
            if newValue is None:
                self.log.logging(
                    "Schneider",
                    "Debug",
                    "schneider_find_attribute_or_set: could not find value, setting default value  %s" % defaultValue,
                    NWKID,
                )
                self.ListOfDevices[NWKID]["Ep"][EP][ClusterID][attr] = defaultValue
            else:
                self.log.logging(
                    "Schneider",
                    "Debug",
                    "schneider_find_attribute_or_set: could not find value, setting new value  %s" % newValue,
                    NWKID,
                )
                self.ListOfDevices[NWKID]["Ep"][EP][ClusterID][attr] = newValue

        self.log.logging(
            "Schneider",
            "Debug",
            "schneider_find_attribute_or_set : found value %s" % (self.ListOfDevices[NWKID]["Ep"][EP][ClusterID][attr]),
            NWKID,
        )
        found = self.ListOfDevices[NWKID]["Ep"][EP][ClusterID][attr]
        if newValue is not None:
            self.log.logging(
                "Schneider", "Debug", "schneider_find_attribute_or_set : setting new value %s" % newValue, NWKID
            )
            self.ListOfDevices[NWKID]["Ep"][EP][ClusterID][attr] = newValue
    return found

AttributesConfigFast = {
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
AttributesConfigNormal = {
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

def schneider_bms_change_reporting(self, NWKID, srcEp, fast):
    
    if fast:
        schneider_UpdateConfigureReporting(self, NWKID, srcEp, "0702", AttributesConfigFast)
    else:
        schneider_UpdateConfigureReporting(self, NWKID, srcEp, "0702", AttributesConfigNormal)


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
    schneider_UpdateConfigureReporting(self, NwkId, EndPoint, "0201", AttributesConfig)

    AttributesConfig = {
        "0001": {"DataType": "30", "MinInterval": "001E", "MaxInterval": "0258", "TimeOut": "0000", "Change": "00"}
    }

    schneider_UpdateConfigureReporting(self, NwkId, EndPoint, "0204", AttributesConfig)

    self.ListOfDevices[NwkId]["Schneider"]["ReportingMode"] = "Normal"

 
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

        if "ConfigureReporting" not in self.DeviceConf[_modelName]:
            return

        if ClusterId not in self.DeviceConf[_modelName]["ConfigureReporting"]:
            return

        if "Attributes" not in self.DeviceConf[_modelName]["ConfigureReporting"][ClusterId]:
            return

        AttributesConfig = self.DeviceConf[self.ListOfDevices[NwkId]["Model"]]["ConfigureReporting"][ClusterId][
            "Attributes"
        ]

    cluster_list = {
        ClusterId: { "Attributes": AttributesConfig}
    }
    
    ListOfAttributesToConfigure = AttributesConfig.keys()
    self.log.logging( "Schneider", "Debug", "schneider_UpdateConfigureReporting - ClusterId: %s ClusterList: %s ListOfAttribute: %s" %(
        ClusterId, str(cluster_list), str(ListOfAttributesToConfigure)))
    self.configureReporting.prepare_and_send_configure_reporting(
        NwkId, Ep, cluster_list, ClusterId, "00", "00", "0000", ListOfAttributesToConfigure)
    



# Wiser New Version
def wiser_home_lockout_thermostat(self, NwkId, mode):

    self.log.logging("Schneider", "Debug", "wiser_home_lockout_thermostat -- mode: %s" % (mode))
    mode = int(mode)
    if mode not in (0, 1):
        return
    write_attribute(
        self, NwkId, ZIGATE_EP, "01", "0204", "0000", "00", "0001", "30", "%02x" % mode, ackIsDisabled=False
    )


def change_setpoint_for_time(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, data):
    # sourcery skip: merge-comparisons, merge-duplicate-blocks, remove-redundant-if, remove-redundant-slice-index
    # Command 0x80: 0301 2e09 7800
    #               0301 d007 1e00   ( 20° for 30 minutes)
    #               0301 7206 1e00   ( 16.5° for 30 minutes)
    #               0300 ff0f 0000   ( cancel last boost )
    #               0300 ff0f 0000

    #               0201 5a0a 3c00   ( 26.5 for 60' )
    #               0202 ca08 3c00   ( 22.5 for 60 )
    #               0202 ca08 3c00

    action = data[2:4] + data[0:2]
    setpoint = int(data[6:8] + data[4:6], 16)
    duration = int(data[10:12] + data[8:10], 16)

    EPout = srcEp
    if "Model" in self.ListOfDevices[srcNWKID] and self.ListOfDevices[srcNWKID]["Model"] in ("iTRV"):
        EPout = "01"

    if action == "0102":  # Increase temp for CCTFR6100
        self.log.logging(
            "Schneider", "Debug", "change_setpoint_for_time -- Setpoint to %s for %s min" % (setpoint, duration)
        )
        override_setpoint(self, srcNWKID, EPout, setpoint, duration)
        schneider_update_ThermostatDevice(self, Devices, srcNWKID, EPout, ClusterID, setpoint)

    elif action == "0103":
        # Set setpoint On
        self.log.logging(
            "Schneider", "Debug", "change_setpoint_for_time -- Setpoint to %s for %s min" % (setpoint, duration)
        )
        override_setpoint(self, srcNWKID, EPout, setpoint, duration)
        schneider_update_ThermostatDevice(self, Devices, srcNWKID, EPout, ClusterID, setpoint)


    elif action == "0202":  # Decrease temp for CCTFR6100
        self.log.logging(
            "Schneider", "Debug", "change_setpoint_for_time -- Setpoint to %s for %s min" % (setpoint, duration)
        )
        override_setpoint(self, srcNWKID, EPout, setpoint, duration)
        schneider_update_ThermostatDevice(self, Devices, srcNWKID, EPout, ClusterID, setpoint)

    elif action == "0300":
        # Disable setpoint
        self.log.logging("Schneider", "Debug", "change_setpoint_for_time -- Cancel setpoint")
        if (
            "Schneider" in self.ListOfDevices[srcNWKID]
            and "ThermostatOverride" in self.ListOfDevices[srcNWKID]["Schneider"]
        ):
            # previous_setpoint = self.ListOfDevices[srcNWKID]["Schneider"]["ThermostatOverride"]["CurrentSetpoint"]
            schneider_update_ThermostatDevice(self, Devices, srcNWKID, EPout, "0201", setpoint)
            del self.ListOfDevices[srcNWKID]["Schneider"]["ThermostatOverride"]

    else:
        self.log.logging(
            "Schneider",
            "Error",
            "change_setpoint_for_time -- Unknown action: %s setpoint: %s duration: %s" % (action, setpoint, duration),
        )


def check_end_of_override_setpoint(self, Devices, NwkId, Ep):

    if (
        "Schneider" in self.ListOfDevices[NwkId]
        and "ThermostatOverride" in self.ListOfDevices[NwkId]["Schneider"]
        and "OverrideStartTime" in self.ListOfDevices[NwkId]["Schneider"]["ThermostatOverride"]
        and "OverrideDuration" in self.ListOfDevices[NwkId]["Schneider"]["ThermostatOverride"]
        and "CurrentSetpoint" in self.ListOfDevices[NwkId]["Schneider"]["ThermostatOverride"]
    ):
        if (
            time()
            > self.ListOfDevices[NwkId]["Schneider"]["ThermostatOverride"]["OverrideStartTime"]
            + self.ListOfDevices[NwkId]["Schneider"]["ThermostatOverride"]["OverrideDuration"]
        ):
            schneider_update_ThermostatDevice(
                self,
                Devices,
                NwkId,
                Ep,
                "0201",
                self.ListOfDevices[NwkId]["Schneider"]["ThermostatOverride"]["CurrentSetpoint"],
            )
            del self.ListOfDevices[NwkId]["Schneider"]["ThermostatOverride"]


def override_setpoint(self, NwkId, Ep, override, duration):

    if "Schneider" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Schneider"] = {}
    if "ThermostatOverride" not in self.ListOfDevices[NwkId]["Schneider"]:
        self.ListOfDevices[NwkId]["Schneider"]["ThermostatOverride"] = {}

    # Get current Setpoint
    current_setpoint = schneider_find_attribute(self, NwkId, Ep, "0201", "0012")
    if current_setpoint == {}:
        current_setpoint = 2000

    self.ListOfDevices[NwkId]["Schneider"]["ThermostatOverride"]["CurrentSetpoint"] = current_setpoint
    self.ListOfDevices[NwkId]["Schneider"]["ThermostatOverride"]["OverrideSetpoint"] = override
    self.ListOfDevices[NwkId]["Schneider"]["ThermostatOverride"]["OverrideDuration"] = duration * 60
    self.ListOfDevices[NwkId]["Schneider"]["ThermostatOverride"]["OverrideStartTime"] = time()


def iTRV_open_window_detection(self, NwkId, enable=False):

    self.log.logging("Schneider", "Debug", "iTRV_open_window_detection enable: %s" % enable)

    manuf_id = "105e"
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0201

    Hattribute = "%04x" % 0xE013
    data_type = "20"  # Bool
    data = "04" if enable else "00"
    self.log.logging(
        "Schneider", "Debug", "iTRV_open_window_detection Schneider %s Write Attribute: 0xe013" % (NwkId,), nwkid=NwkId
    )
    write_attribute(
        self, NwkId, ZIGATE_EP, "01", cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )

    Hattribute = "%04x" % 0xE014
    data_type = "21"  # 16Uint
    data = "%04x" % 600 if enable else "00"
    self.log.logging(
        "Schneider", "Debug", "iTRV_open_window_detection Schneider %s Write Attribute: 0xe013" % (NwkId,), nwkid=NwkId
    )
    write_attribute(
        self, NwkId, ZIGATE_EP, "01", cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )

    Hattribute = "%04x" % 0xE015
    data_type = "21"  # 16Uint
    if enable:
        data = "%04x" % 120
    else:
        data = "00"
    self.log.logging(
        "Schneider", "Debug", "iTRV_open_window_detection Schneider %s Write Attribute: 0xe013" % (NwkId,), nwkid=NwkId
    )
    write_attribute(
        self, NwkId, ZIGATE_EP, "01", cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled=False
    )

def iTRV_local_temperature(self, NwkId):
    self.log.logging("Schneider", "Debug", "iTRV_local_temperature for: %s" % NwkId)
    room_temperature = get_local_temperature_from_wiserroom( self, NwkId, get_wiserroom(self, NwkId))
    self.log.logging("Schneider", "Debug", "iTRV_local_temperature for: %s room temp: %s" % (NwkId, room_temperature))
    if room_temperature is None:
        return 0x8000
    return room_temperature

def get_wiserroom(self, NwkId):
    self.log.logging("Schneider", "Debug", "get_wiserroom for: %s" % (NwkId,))
    if "Param" in self.ListOfDevices[ NwkId ] and  "WiserRoomNumber" in self.ListOfDevices[ NwkId ]["Param"]:
        self.log.logging("Schneider", "Debug", "get_wiserroom for: %s is room: %s" % (NwkId,self.ListOfDevices[ NwkId ]["Param"]["WiserRoomNumber"]))
        return self.ListOfDevices[ NwkId ]["Param"]["WiserRoomNumber"]
    return None

def get_local_temperature_from_wiserroom( self, NwkId, room=None):
    
    self.log.logging("Schneider", "Debug", "get_local_temperature_from_wiserroom for: %s and room: %s" % (NwkId,room))
    if room is None:
        return None
    
    for x in list(self.ListOfDevices):
        if x == NwkId:
            continue
        if "Param" not in self.ListOfDevices[x]:
            continue
        if "WiserRoomNumber" not in self.ListOfDevices[x]["Param"]:
            continue
        if self.ListOfDevices[x]["Param"]["WiserRoomNumber"] != room:
            continue
        
        # We have a device which belongs to the same WiserRoomNumber
        self.log.logging("Schneider", "Debug", "get_local_temperature_from_wiserroom for: %s and room: %s potential candidat: %s" % (NwkId,room, x))
        # Is that a Temperature Sensor ?
        if "Model" in self.ListOfDevices[x] and self.ListOfDevices[x]["Model"] in ( "iTRV", ):
            # This is an iTRV skip it, we don't want to use the local sensor of an eTRV
            continue
        
        for y in self.ListOfDevices[x]["Ep"]:
            if "0402" not in self.ListOfDevices[x]["Ep"][y]:
                continue
            if "0000" not in self.ListOfDevices[x]["Ep"][y]["0402"]:
                continue
            self.log.logging("Schneider", "Debug", "get_local_temperature_from_wiserroom for: %s and room: %s confirmed candidat: %s with temp: %s" % (
                NwkId,room, x, self.ListOfDevices[x]["Ep"][y]["0402"]["0000"]))
            return self.ListOfDevices[x]["Ep"][y]["0402"]["0000"]

    return None
