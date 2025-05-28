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
SYSTEM_MODE_ATTRIBUTE = "001c"
THERMOSTAT_CALIBRATION = "0010"
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

    eps = self.ListOfDevices.get(NwkId, {}).get("Ep", {})
    EPout = next((ep for ep, clusters in eps.items() if THERMOSTAT_CLUSTER in clusters), "01")
    ep = self.ListOfDevices.get(NwkId, {}).get("Ep", {}).get(EPout, {})
    thermostat_cluster = ep.get(THERMOSTAT_CLUSTER, {})

    if model_name == "Aidoo Zigbee":
        # Airzone - Aidoo Zigbee thermostat
        self.log.logging(["Thermostats","Schneider"], "Debug", "thermostat_Setpoint - Aidoo Zigbee for %s with value %s on Heating and Cooling" % (NwkId, setpoint), nwkid=NwkId)
        write_thermostat_setpoint(self, NwkId, EPout, setpoint, OCCUPIED_HEATING_SETPOINT)
        write_thermostat_setpoint(self, NwkId, EPout, setpoint, OCCUPIED_COOLING_SETPOINT)
        return

    if thermostat_cluster.get(SYSTEM_MODE_ATTRIBUTE) == 0x03:
        # If the thermostat cluster has the attribute 001c set to 0x03, it means it's a cooling thermostat
        # and we should use the cooling setpoint instead of the heating setpoint.
        self.log.logging(["Thermostats","Schneider"], "Debug", "thermostat_Setpoint - Cool Setpoint for %s with value %s" % (NwkId, setpoint), nwkid=NwkId)
        write_thermostat_setpoint(self, NwkId, EPout, setpoint, OCCUPIED_COOLING_SETPOINT)
        return

    # For other thermostats, we will use the heating setpoint by default.
    self.log.logging(["Thermostats","Schneider"], "Debug", "thermostat_Setpoint - Heating Setpoint for %s with value %s" % (NwkId, setpoint), nwkid=NwkId)
    write_thermostat_setpoint(self, NwkId, EPout, setpoint, OCCUPIED_HEATING_SETPOINT)
    return


def write_thermostat_setpoint(self, NwkId, EPout, setpoint, Hattribute):
    """Write a thermostat setpoint value to a Zigbee device."""

    cluster_id = THERMOSTAT_CLUSTER
    manuf_id = "0000"
    manuf_spec = "00"
    data_type = "29"  # Int16

    # Round to nearest 0.5°C step
    rounded_setpoint = round(setpoint * 2) / 2
    self.log.logging(["Thermostats", "Schneider"], "Debug", f"setpoint (original): {setpoint}, (rounded): {rounded_setpoint}", nwkid=NwkId)

    # Format as 16-bit signed integer (in deci-degrees
    Hdata = f"{int(rounded_setpoint):04x}"  # Ensure a 4-character hex format

    # Patch for ZiGate V2 firmware < 0x0320
    if self.zigbee_communication == "native" and self.ZiGateModel == 2 and int(self.FirmwareVersion, 16) < 0x0320:
        self.log.logging(["Thermostats", "Schneider"], "Debug", f"--- ZiGate Model: {self.ZiGateModel}  Version: {self.FirmwareVersion}")
        Hdata = Hdata[2:] + Hdata[:2]
        self.log.logging(["Thermostats", "Schneider"], "Debug", f"Patched Hdata: {Hdata}")

    self.log.logging(["Thermostats", "Schneider"], "Debug",
                     f"thermostat_Setpoint - for {NwkId} with value 0x{Hdata} / cluster: {cluster_id}, "
                     f"attribute: {Hattribute}, type: {data_type}", nwkid=NwkId)

    # Write attribute to Zigbee device
    write_attribute(self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

    # Trigger read back to confirm write
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
    """
    Set the thermostat calibration offset.
    The offset is in deci-degrees (-25 to 25), which maps to -2.5°C to 2.5°C.
    The Zigbee payload expects an int8 value in two’s complement if negative.
    """

    # Fetch calibration from device Param if not explicitly passed
    if calibration is None:
        calibration_value = self.ListOfDevices.get(NwkId, {}).get("Param", {}).get("Calibration")
        if isinstance(calibration_value, (int, float)):
            calibration = int(calibration_value * 10)
        else:
            calibration = 0
 
    # Sanity check: must be between -25 and 25 deci-degrees
    if not -25 <= calibration <= 25:
        self.log.logging("Thermostats", "Error",
                         f"thermostat_Calibration - Invalid offset for {NwkId}: {calibration}")
        calibration = 0

    if calibration < 0:
        # in two’s complement form
        calibration = abs((-calibration - pow(2, 32)) & 0xFFFFFFFF)
        self.log.logging( "Thermostats", "Debug", "thermostat_Calibration - 2 complement form of Calibration offset on %s off %s" % (
            NwkId, calibration), )

    # Initialize nested dict if needed
    device = self.ListOfDevices.setdefault(NwkId, {})
    thermostat = device.setdefault("Thermostat", {})

    # Avoid unnecessary update if value hasn't changed
    existing_cal = thermostat.get("Calibration")
    if existing_cal is not None and calibration == int(existing_cal * 10):
        return  # No update needed

    self.log.logging("Thermostats", "Debug",
                     f"thermostat_Calibration - Setting new offset for {NwkId}: {calibration}")

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
    attribute = SYSTEM_MODE_ATTRIBUTE
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
