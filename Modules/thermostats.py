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


from Modules.basicOutputs import write_attribute
from Modules.casaia import casaia_check_irPairing, casaia_setpoint
from Modules.danfoss import thermostat_Setpoint_Danfoss
from Modules.readAttributes import (
    ReadAttributeRequest_0201, ReadAttributeRequest_thermostat_cool_setpoint,
    ReadAttributeRequest_thermostat_unoccupied_heat_setpoint)
from Modules.schneider_wiser import (schneider_hact_heater_type_wiser2,
                                     schneider_setpoint)
from Modules.tuyaConst import TUYA_eTRV_MODEL
from Modules.tuyaTRV import tuya_setpoint
from Modules.tuyaTS0601 import ts0601_actuator, ts0601_extract_data_point_infos

THERMOSTAT_CLUSTER = "0201"
OCCUPIED_COOLING_SETPOINT = "0011"
OCCUPIED_HEATING_SETPOINT = "0012"
UNOCCUPIED_COOLING_SETPOINT = "0013"
UNOCCUPIED_HEATING_SETPOINT = "0014"



def thermostat_Setpoint_SPZB(self, NwkId, setpoint):

    manuf_id = "1037"
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0201
    Hattribute = "%04x" % 0x4003
    data_type = "29"  # Int16
    self.log.logging("Thermostats", "Debug", "setpoint: %s" % setpoint, nwkid=NwkId)
    setpoint = int((setpoint * 2) / 2)  # Round to 0.5 degrees
    self.log.logging("Thermostats", "Debug", "setpoint: %s" % setpoint, nwkid=NwkId)
    Hdata = "%04x" % setpoint
    EPout = "01"
    for tmpEp in self.ListOfDevices[NwkId]["Ep"]:
        if THERMOSTAT_CLUSTER in self.ListOfDevices[NwkId]["Ep"][tmpEp]:
            EPout = tmpEp

    self.log.logging(
        "Thermostats",
        "Debug",
        "thermostat_Setpoint_SPZB - for %s with value %s / cluster: %s, attribute: %s type: %s"
        % (NwkId, Hdata, cluster_id, Hattribute, data_type),
        nwkid=NwkId,
    )
    write_attribute(self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)


def thermostat_unoccupied_heat_setpoint(self, nwkid, unoccupied_heating_setpoint):
    self.log.logging(
        ["Thermostats"], "Debug",
        f"thermostat_unoccupied_heat_setpoint - for {nwkid} with value {unoccupied_heating_setpoint}",
        nwkid=nwkid
    )

    EPout = next((ep for ep, attrs in self.ListOfDevices[nwkid]["Ep"].items() if THERMOSTAT_CLUSTER in attrs), "01")

    cluster_id = THERMOSTAT_CLUSTER
    Hattribute = UNOCCUPIED_HEATING_SETPOINT
    manuf_id, manuf_spec, data_type = "0000", "00", "29"  # Int16

    unoccupied_heating_setpoint = round(unoccupied_heating_setpoint * 2) / 2  # Ensure rounding to 0.5 degrees
    Hdata = f"{int(unoccupied_heating_setpoint):04x}"  # Format as a 4-char hex string

    self.log.logging(
        ["Thermostats"], "Debug",
        f"thermostat_unoccupied_heat_setpoint - for {nwkid} with value 0x{Hdata} / "
        f"cluster: {cluster_id}, attribute: {Hattribute}, type: {data_type}",
        nwkid=nwkid
    )

    write_attribute(self, nwkid, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)
    ReadAttributeRequest_thermostat_unoccupied_heat_setpoint(self, nwkid)


def thermostat_cool_setpoint(self, nwkid, cool_setpoint):
    self.log.logging(
        ["Thermostats"], "Debug",
        f"thermostat_cool_setpoint - for {nwkid} with value {cool_setpoint}",
        nwkid=nwkid
    )

    cluster_id = THERMOSTAT_CLUSTER
    Hattribute = OCCUPIED_COOLING_SETPOINT
    manuf_id, manuf_spec, data_type = "0000", "00", "29"  # Int16

    cool_setpoint = round(cool_setpoint * 2) / 2  # Round to nearest 0.5 degrees
    Hdata = f"{int(cool_setpoint):04x}"  # Ensure a 4-character hex format

    # Find the appropriate endpoint dynamically
    EPout = next(
        (ep for ep, attrs in self.ListOfDevices[nwkid]["Ep"].items() if THERMOSTAT_CLUSTER in attrs),
        "01"
    )

    self.log.logging(
        ["Thermostats"], "Debug",
        f"thermostat_cool_setpoint - for {nwkid} with value 0x{Hdata} / "
        f"cluster: {cluster_id}, attribute: {Hattribute}, type: {data_type}",
        nwkid=nwkid
    )

    write_attribute(self, nwkid, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)
    ReadAttributeRequest_thermostat_cool_setpoint(self, nwkid)


def thermostat_Setpoint(self, NwkId, setpoint):

    self.log.logging(["Thermostats","Schneider"], "Debug", "thermostat_Setpoint - for %s with value %s" % (NwkId, setpoint), nwkid=NwkId)

    model_name = self.ListOfDevices[NwkId].get("Model")

    if model_name in ("AC211", "AC221", "CAC221"):
        casaia_check_irPairing(self, NwkId)

    if model_name is not None:
        if ts0601_extract_data_point_infos( self, model_name):
            ts0601_actuator(self, NwkId, "calibration")
            ts0601_actuator( self, NwkId, "setpoint", setpoint)
            return

        if model_name == "SPZB0001":
            # Eurotronic
            self.log.logging( ["Thermostats","Schneider"], "Debug", "thermostat_Setpoint - calling SPZB for %s with value %s" % (
                NwkId, setpoint), nwkid=NwkId, )
            thermostat_Calibration(self, NwkId)
            thermostat_Setpoint_SPZB(self, NwkId, setpoint)
            return

        if model_name in ("EH-ZB-RTS", "EH-ZB-HACT", "EH-ZB-VACT", "Wiser2-Thermostat", "iTRV", ):
            # Schneider
            self.log.logging( ["Thermostats","Schneider"], "Debug", "thermostat_Setpoint - calling Schneider for %s with value %s" % (
                NwkId, setpoint), nwkid=NwkId, )
            schneider_setpoint(self, NwkId, setpoint)
            return

        if model_name in ("CCTFR6700", ):
            # Schneider CCTFR6700, we do the work on Schneider, but we will continue with the write attribute
            self.log.logging( ["Thermostats","Schneider"], "Debug", "thermostat_Setpoint - calling Schneider for %s with value %s" % (
                NwkId, setpoint), nwkid=NwkId, )

            type_heater = self.ListOfDevices[NwkId].get("Schneider",{}).get('HeaterType')
            self.log.logging( ["Thermostats","Schneider"], "Debug", "thermostat_Setpoint - CCTFR6700 - heating type >%s<" % (type_heater), nwkid=NwkId, )

            if type_heater in ("fip", "conventional"):
                schneider_hact_heater_type_wiser2(self, NwkId, type_heater)
            schneider_setpoint(self, NwkId, setpoint)

        if model_name in (TUYA_eTRV_MODEL):
            # Tuya
            self.log.logging( ["Thermostats","Schneider"], "Debug", "thermostat_Setpoint - calling Tuya for %s with value %s" % (
                NwkId, setpoint), nwkid=NwkId, )
            tuya_setpoint(self, NwkId, setpoint)
            return

        if model_name in ("AC201A",):
            casaia_setpoint(self, NwkId, setpoint)
            return

        if (
            model_name in ("eTRV0100", "eT093WRO")
            and "Param" in self.ListOfDevices[NwkId]
            and "DanfossSetPointType" in self.ListOfDevices[NwkId]["Param"]
            and int(self.ListOfDevices[NwkId]["Param"]["DanfossSetPointType"])
        ):
            thermostat_Calibration(self, NwkId)
            thermostat_Setpoint_Danfoss(self, NwkId, setpoint)
            ReadAttributeRequest_0201(self, NwkId)
            return

    self.log.logging(["Thermostats","Schneider"], "Debug", "thermostat_Setpoint - standard for %s with value %s" % (NwkId, setpoint), nwkid=NwkId)

    EPout = "01"
    for tmpEp in self.ListOfDevices[NwkId]["Ep"]:
        if THERMOSTAT_CLUSTER in self.ListOfDevices[NwkId]["Ep"][tmpEp]:
            EPout = tmpEp

    # Heat setpoint by default
    cluster_id = THERMOSTAT_CLUSTER
    Hattribute = OCCUPIED_HEATING_SETPOINT

    if (
        cluster_id in self.ListOfDevices[NwkId]["Ep"][EPout]
        and "001c" in self.ListOfDevices[NwkId]["Ep"][EPout][cluster_id]
        and self.ListOfDevices[NwkId]["Ep"][EPout][cluster_id]["001c"] == 0x03
    ):
        # Cool Setpoint
        Hattribute = OCCUPIED_COOLING_SETPOINT

    manuf_id = "0000"
    manuf_spec = "00"

    data_type = "29"  # Int16
    self.log.logging(["Thermostats","Schneider"], "Debug", "setpoint: %s" % setpoint, nwkid=NwkId)
    setpoint = int((setpoint * 2) / 2)  # Round to 0.5 degrees
    self.log.logging(["Thermostats","Schneider"], "Debug", "setpoint: %s" % setpoint, nwkid=NwkId)

    Hdata = "%04x" % setpoint

    if self.zigbee_communication == "native" and self.ZiGateModel == 2 and int(self.FirmwareVersion, 16) < 0x0320:
        # Bug on ZiGate V2 - firmware 0x320 fix it
        self.log.logging(["Thermostats","Schneider"], "Debug", "---Zigate Model: %s  Version: %s" % (self.ZiGateModel, self.FirmwareVersion))
        Hdata = Hdata[2:4] + Hdata[:2]
        self.log.logging(["Thermostats","Schneider"], "Debug", "Patch Hdata  %s" % Hdata)

    EPout = "01"
    self.log.logging( ["Thermostats","Schneider"], "Debug", "thermostat_Setpoint - for %s with value 0x%s / cluster: %s, attribute: %s type: %s" % (
        NwkId, Hdata, cluster_id, Hattribute, data_type), nwkid=NwkId, )
    write_attribute(self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

    ReadAttributeRequest_0201(self, NwkId)


def thermostat_eurotronic_hostflag(self, NwkId, action):

    HOSTFLAG_ACTION = {
        "turn_display": 0x000002,
        "boost": 0x000004,
        "clear_off": 0x000010,
        "set_off_mode": 0x000020,
        "child_lock": 0x000080,
    }

    if action not in HOSTFLAG_ACTION:
        self.log.logging("Thermostats", "Log", "thermostat_eurotronic_hostflag - unknown action %s" % action)
        return

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" % 0x0201
    attribute = "%04x" % 0x4008
    data_type = "22"  # U24
    data = "%06x" % HOSTFLAG_ACTION[action]
    EPout = "01"
    for tmpEp in self.ListOfDevices[NwkId]["Ep"]:
        if THERMOSTAT_CLUSTER in self.ListOfDevices[NwkId]["Ep"][tmpEp]:
            EPout = tmpEp
    write_attribute(self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
    self.log.logging(
        "Thermostats",
        "Debug",
        "thermostat_eurotronic_hostflag - for %s with value %s / cluster: %s, attribute: %s type: %s action: %s"
        % (NwkId, data, cluster_id, attribute, data_type, action),
        nwkid=NwkId,
    )


def thermostat_Calibration(self, NwkId, calibration=None):
    # Calibration is an int8 representing a temperature offset (in the range -2.5°C to 2.5°C)
    # from 0xE7 ( -2.5 ) to 0x19 ( +2.5 )
    # that can be added to or subtracted from the displayed temperature

    if (
        "Param" in self.ListOfDevices[NwkId]
        and "Calibration" in self.ListOfDevices[NwkId]["Param"]
        and isinstance(self.ListOfDevices[NwkId]["Param"]["Calibration"], (float, int))
    ):
        calibration = int(10 * self.ListOfDevices[NwkId]["Param"]["Calibration"])

    if calibration is None:
        calibration = 0

    if calibration < -25 or calibration > 25:
        self.log.logging( "Thermostats", "Error", "thermostat_Calibration - Wrong Calibration offset on %s off %s" % (
            NwkId, calibration), )
        calibration = 0

    if calibration < 0:
        # in two’s complement form
        calibration = abs((-calibration - pow(2, 32)) & 0xFFFFFFFF)
        self.log.logging( "Thermostats", "Debug", "thermostat_Calibration - 2 complement form of Calibration offset on %s off %s" % (
            NwkId, calibration), )

    if "Thermostat" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Thermostat"] = {}

    if (
        "Calibration" in self.ListOfDevices[NwkId]["Thermostat"]
        and calibration == 10 * self.ListOfDevices[NwkId]["Thermostat"]["Calibration"]
    ):
        return

    self.log.logging("Thermostats", "Debug", "thermostat_Calibration - Set Thermostat offset on %s off %s" % (NwkId, calibration))

    self.ListOfDevices[NwkId]["Thermostat"]["Calibration"] = calibration

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" % 0x0201
    attribute = "%04x" % 0x0010
    data_type = "28"  # Int8
    data = "%02x" % calibration
    EPout = "01"
    for tmpEp in self.ListOfDevices[NwkId]["Ep"]:
        if THERMOSTAT_CLUSTER in self.ListOfDevices[NwkId]["Ep"][tmpEp]:
            EPout = tmpEp

    write_attribute(self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
    self.log.logging( "Thermostats", "Debug", "thermostat_Calibration - for %s with value %s / cluster: %s, attribute: %s type: %s" % (
        NwkId, data, cluster_id, attribute, data_type), nwkid=NwkId, )


def configHeatSetpoint(self, NwkId):

    ddhostflags = 0xFFFFEB


def thermostat_Mode(self, NwkId, mode):

    SYSTEM_MODE = {
        "Off": 0x00,
        "Auto": 0x01,
        "Reserved": 0x02,
        "Cool": 0x03,
        "Heat": 0x04,
        "Emergency Heating": 0x05,
        "Pre-cooling": 0x06,
        "Fan Only": 0x07,
        "Dry": 0x08,
        "Sleep": 0x09,
    }

    if mode not in SYSTEM_MODE:
        self.log.logging("Thermostats", "Error", "thermostat_Mode - unknown system mode: %s" % mode)
        return

    model_name = self.ListOfDevices[NwkId].get("Model", "")
    if model_name in ("AC211", "AC221", "CAC221"):
        casaia_check_irPairing(self, NwkId)

    manuf_id = "0000"
    manuf_spec = "00"

    # Find the Ep we should send the request
    ep_out = next( ( ep for ep in self.ListOfDevices[NwkId]["Ep"] if THERMOSTAT_CLUSTER in self.ListOfDevices[NwkId]["Ep"][ep] ), "01", )
    cluster_id = "%04x" % 0x0201
    attribute = "%04x" % 0x001C
    data_type = "30"  # Enum8
    data = "%02x" % SYSTEM_MODE[mode]

    # Set the Mode
    write_attribute(self, NwkId, "01", ep_out, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
    self.log.logging( "Thermostats", "Debug", "thermostat_Mode - for %s with value %s / cluster: %s, attribute: %s type: %s" % (
        NwkId, data, cluster_id, attribute, data_type), nwkid=NwkId, )

    if model_name in ("TAFFETAS2 D1.00P1.01Z1.00"):
        self.log.logging(
            "Thermostats",
            "Debug",
            "thermostat_Mode - for %s with value %s / cluster: %s, attribute: %s type: %s"
            % (NwkId, data, cluster_id, attribute, data_type),
            nwkid=NwkId,
        )

    if model_name in ( "CCRFR6700", ) and mode == "Heat":
        # Set the Control Sequence Of operation to Heating
        cluster_id = "%04x" % 0x0201
        attribute = "%04x" % 0x001B  # Control Sequence Of operation
        data_type = "30"  # Enum8
        data = "%02x" % 0x02   # Heating Only

        write_attribute(self, NwkId, "01", ep_out, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)


def Thermostat_LockMode(self, NwkId, lockmode):

    LOCK_MODE = {"unlocked": 0x00, "templock": 0x02, "off": 0x04, "off-2": 0x05}

    if lockmode not in LOCK_MODE:
        return

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" % 0x0204
    Hattribute = "%04x" % 0x0001
    data_type = "30"  # Int16
    self.log.logging("Thermostats", "Debug", "lockmode: %s" % lockmode, nwkid=NwkId)
    lockmode = LOCK_MODE[lockmode]
    Hdata = "%02x" % lockmode
    EPout = "01"
    for tmpEp in self.ListOfDevices[NwkId]["Ep"]:
        if "0204" in self.ListOfDevices[NwkId]["Ep"][tmpEp]:
            EPout = tmpEp

    self.log.logging(
        "Thermostats",
        "Debug",
        "Thermostat_LockMode - for %s with value %s / cluster: %s, attribute: %s type: %s"
        % (NwkId, Hdata, cluster_id, Hattribute, data_type),
        nwkid=NwkId,
    )
    write_attribute(self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)


    write_attribute(self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)
