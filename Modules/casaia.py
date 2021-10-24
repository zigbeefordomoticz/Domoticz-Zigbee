#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author:  pipiche38
#   French translation: @martial83
#

import Domoticz

from Classes.LoggingManagement import LoggingManagement
from Modules.basicOutputs import write_attribute, sendZigateCmd, raw_APS_request
from Modules.tools import (
    retreive_cmd_payload_from_8002,
    is_ack_tobe_disabled,
    checkAndStoreAttributeValue,
    get_and_inc_SQN,
)
from Modules.zigateConsts import ZIGATE_EP

from Modules.domoMaj import MajDomoDevice

import struct
import json
import os

CASAIA_MANUF_CODE = "113c"
CASAIA_MANUF_CODE_BE = "3c11"
CASAIA_AC201_CLUSTER = "ffad"
CASAIA_AC211_CLUSTER = "ffac"
CASAIA_CONFIG_FILENAME = "Casa.ia.json"

DEVICE_TYPE = "00"
DEVICE_ID = "01"

# Pairing
# Hub               Device
# Cmd Data          Cmd Data
# 0x00 00    --->
#            <---   0x00 0001ffff02ffff03ffff04ffff05ffff
# 0x11 00    --->
#            <---   0x11 000000
# 0x12 000000 --->
#             <---  0x12 0000000000
# 0x06 000000 --->
#             <---  0x06 0000000000


# Sending IR Code
# 0x01 00014d03 -->
#
AC201_COMMAND = {
    "Off": "010000",  # Ok 6/11
    "On": "010100",  # Ok 6/11
    "Cool": "010300",  # Ok 6/11
    "Heat": "010400",  # Ok 6/11
    "Fan": "010700",  # Ok 7/11
    "Dry": "010800",  # Ok 7/11
    "HeatSetpoint": "02",  # Heat Setpoint Ok 7/11
    "CoolSetpoint": "03",  # Cool Setpoint Ok 7/11
    "FanLow": "040100",  # Ok 6/11
    "FanMedium": "040200",  # Ok 6/11
    "FanHigh": "040300",  # Ok 6/11
    "FanAuto": "040500",  # Ok 6/11
}


def pollingCasaia(self, NwkId):
    # This fonction is call if enabled to perform any Manufacturer specific polling action
    # The frequency is defined in the pollingSchneider parameter (in number of seconds)
    if "Model" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Model"] == "AC201A":
        self.log.logging("CasaIA", "Debug", "pollingCasaia %s" % (NwkId), NwkId)
        AC201_read_AC_status_request(self, NwkId)
    return False


def callbackDeviceAwake_Casaia(self, Devices, NwkId, EndPoint, cluster):
    # This is fonction is call when receiving a message from a Manufacturer battery based device.
    # The function is called after processing the readCluster part

    self.log.logging(
        "CasaIA", "Debug", "callbackDeviceAwake_Casaia %s/%s cluster: %s" % (NwkId, EndPoint, cluster), NwkId
    )


def casaiaReadRawAPS(self, Devices, NwkId, srcEp, ClusterId, dstNWKID, dstEP, MsgPayload):

    self.log.logging(
        "CasaIA",
        "Debug",
        "casaiaReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s"
        % (NwkId, srcEp, ClusterId, dstNWKID, dstEP, MsgPayload),
        NwkId,
    )

    if NwkId not in self.ListOfDevices:
        self.log.logging(
            "CasaIA",
            "Error",
            "%s not found in Database" % NwkId,
            NwkId,
            {"Error code": "CASAIA-READRAW-01", "ListOfDevices": self.ListOfDevices},
        )
        return

    if "Model" not in self.ListOfDevices[NwkId]:
        return
    _Model = self.ListOfDevices[NwkId]["Model"]
    (
        GlobalCommand,
        Sqn,
        ManufacturerCode,
        Command,
        Data,
    ) = retreive_cmd_payload_from_8002(MsgPayload)
    if ClusterId == CASAIA_AC201_CLUSTER:
        # AC201
        if Command == "00":
            AC201_read_multi_pairing_response(self, Devices, NwkId, srcEp, Data)

        elif Command == "02":
            AC201_read_AC_status_response(self, Devices, NwkId, srcEp, Data)

        elif Command in ["11", "12"]:
            AC201_read_learned_data_group_status_request(self, NwkId)

    elif ClusterId == CASAIA_AC211_CLUSTER:
        # AC211
        if Command == "00":
            AC211_ReadPairingCodeResponse(self, Devices, NwkId, srcEp, Data)

        elif Command == "01":
            AC211_ReadLearnedStatesResponse(self, Devices, NwkId, srcEp, Data)


def casaia_swing_OnOff(self, NwkId, OnOff):

    if OnOff not in ("00", "01"):
        return
    EPout = get_ffad_endpoint(self, NwkId)

    write_attribute(
        self,
        NwkId,
        ZIGATE_EP,
        EPout,
        "0201",
        CASAIA_MANUF_CODE,
        "01",
        "fd00",
        "10",
        OnOff,
        ackIsDisabled=is_ack_tobe_disabled(self, NwkId),
    )
    self.log.logging("CasaIA", "Debug", "swing_OnOff ++++ %s/%s OnOff: %s" % (NwkId, EPout, OnOff), NwkId)


def casaia_setpoint(self, NwkId, setpoint):

    if "Model" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Model"] == "AC201A":
        self.log.logging("CasaIA", "Debug", "casaia_setpoint %s SetPoint: %s" % (NwkId, setpoint), NwkId)
        if str(check_hot_cold_setpoint(self, NwkId)) == "Heat":
            write_AC201_status_request(self, NwkId, "HeatSetpoint", setpoint)
        elif str(check_hot_cold_setpoint(self, NwkId)) == "Cool":
            write_AC201_status_request(self, NwkId, "CoolSetpoint", setpoint)
        else:
            AC201_read_AC_status_request(self, NwkId)


def casaia_system_mode(self, NwkId, Action):

    if "Model" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Model"] == "AC201A":
        self.log.logging("CasaIA", "Debug", "casaia_system_mode %s Action: %s" % (NwkId, Action), NwkId)
        write_AC201_status_request(self, NwkId, Action)


def casaia_pairing(self, NwkId):

    if "Model" in self.ListOfDevices[NwkId]:
        if self.ListOfDevices[NwkId]["Model"] == "AC201A":
            casaia_AC201_pairing(self, NwkId)

        elif self.ListOfDevices[NwkId]["Model"] in ("AC211", "AC221"):
            casaia_AC211_pairing(self, NwkId)


def casaia_check_irPairing(self, NwkId):

    if "CASA.IA" not in self.ListOfDevices[NwkId]:
        self.log.logging(
            "CasaIA",
            "Error",
            "casaia_check_irPairing - %s No CASA.IA Attributes" % NwkId,
            NwkId,
            {"Error code": "CASAIA-CHKPAIRING-01"},
        )
        AC201_read_AC_status_request(self, NwkId)
        return None

    if DEVICE_ID not in self.ListOfDevices[NwkId]["CASA.IA"]:
        self.log.logging(
            "CasaIA",
            "Error",
            "casaia_check_irPairing - %s No DEVICE_ID Attributes" % NwkId,
            NwkId,
            {"Error code": "CASAIA-CHKPAIRING-02"},
        )
        AC201_read_AC_status_request(self, NwkId)
        return None

    if "IRCode" not in self.ListOfDevices[NwkId]["CASA.IA"][DEVICE_ID]:
        self.log.logging(
            "CasaIA",
            "Error",
            "casaia_check_irPairing - %s No IRCode Attributes" % NwkId,
            NwkId,
            {"Error code": "CASAIA-CHKPAIRING-03"},
        )
        AC201_read_AC_status_request(self, NwkId)
        return None

    if self.ListOfDevices[NwkId]["CASA.IA"][DEVICE_ID]["IRCode"] in (0x0, 0xFFFF):
        self.log.logging(
            "CasaIA",
            "Error",
            "casaia_check_irPairing - %s IRCode %s not in place"
            % (NwkId, self.ListOfDevices[NwkId]["CASA.IA"][DEVICE_ID]["IRCode"]),
            NwkId,
            {"Error code": "CASAIA-CHKPAIRING-04"},
        )
        return None

    if "ModuleIRCode" in self.ListOfDevices[NwkId]["CASA.IA"][DEVICE_ID] and int(
        self.ListOfDevices[NwkId]["CASA.IA"][DEVICE_ID]["ModuleIRCode"], 16
    ) == int(self.ListOfDevices[NwkId]["CASA.IA"][DEVICE_ID]["IRCode"], 16):
        return True

    if "ModuleIRCode" not in self.ListOfDevices[NwkId]["CASA.IA"][DEVICE_ID]:
        AC201_read_AC_status_request(self, NwkId)
        AC201_read_multi_pairing_code_request(self, NwkId)

    if "Model" in self.ListOfDevices[NwkId]:
        if self.ListOfDevices[NwkId]["Model"] == "AC201A":
            casaia_ac201_ir_pairing(self, NwkId)
            AC201_read_AC_status_request(self, NwkId)

        elif self.ListOfDevices[NwkId]["Model"] in ("AC211", "AC221"):
            casaia_ac211_ir_pairing(self, NwkId)
            AC201_read_AC_status_request(self, NwkId)

    return None


# Model Specifics
#####################################################################################
def casaia_AC211_pairing(self, NwkId):
    # Call during the Zigbee pairing process
    self.log.logging("CasaIA", "Debug", "casaia_AC211_pairing %s" % (NwkId), NwkId)

    # 0x00
    AC211_ReadPairingCodeRequest(self, NwkId)

    # 0x01
    AC211_ReadLearnedStatesRequest(self, NwkId)

    # 0x20
    casaia_check_irPairing(self, NwkId)

    # 0x00
    AC211_ReadPairingCodeRequest(self, NwkId)


def casaia_ac211_ir_pairing(self, NwkId):
    self.log.logging("CasaIA", "Debug", "casaia_ac211_ir_pairing %s" % (NwkId), NwkId)
    pac_code = get_pac_code(self, self.ListOfDevices[NwkId]["IEEE"])
    self.log.logging("CasaIA", "Debug", "casaia_ac211_ir_pairing %s IRCode: %s" % (NwkId, pac_code), NwkId)
    if pac_code and int(pac_code, 16) not in (0x0000, 0xFFFF):
        AC211_WritePairingCodeRequest(self, NwkId, pac_code)


def casaia_AC201_pairing(self, NwkId):
    # Call during the Zigbee pairing process
    self.log.logging("CasaIA", "Debug", "casaia_AC201_pairing %s" % (NwkId), NwkId)

    # Read Existing Pairing Infos: Command 0x00
    AC201_read_multi_pairing_code_request(self, NwkId)

    # In case we have already the IRCode
    casaia_check_irPairing(self, NwkId)

    # Read Current AC Status
    AC201_read_AC_status_request(self, NwkId)


def casaia_ac201_ir_pairing(self, NwkId):
    self.log.logging("CasaIA", "Debug", "casaia_ac201_ir_pairing %s" % (NwkId), NwkId)
    pac_code = get_pac_code(self, self.ListOfDevices[NwkId]["IEEE"])
    self.log.logging("CasaIA", "Debug", "casaia_ac201_ir_pairing %s IRCode: %s" % (NwkId, pac_code), NwkId)
    if pac_code and int(pac_code, 16) not in (0x0, 0xFFFF):
        AC201_write_multi_pairing_code_request(self, NwkId, pac_code)
    else:
        self.log.logging(
            "Casaia",
            "Error",
            "casaia_ac201_ir_pairing - %s IRCode %s not in place" % (NwkId, pac_code),
            NwkId,
            {"Error code": "CASAIA-ACPAIRING-01"},
        )


def casaia_ac201_fan_control(self, NwkId, Level):

    if Level == 10:
        casaia_system_mode(self, NwkId, "FanAuto")
        # UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
    elif Level == 20:
        casaia_system_mode(self, NwkId, "FanLow")
        # UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
    elif Level == 30:
        casaia_system_mode(self, NwkId, "FanMedium")
        # UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
    elif Level == 40:
        casaia_system_mode(self, NwkId, "FanHigh")
        # UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)


## 0xFFAC Client to Server
#####################################################################################
def AC211_ReadPairingCodeRequest(self, NwkId):
    # Command  0x00
    # determine which Endpoint
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_and_inc_SQN(self, NwkId)
    cluster_frame = "01"
    device_type = DEVICE_TYPE  # Device type
    cmd = "00"
    payload = cluster_frame + sqn + cmd + device_type
    raw_APS_request(self, NwkId, EPout, "ffac", "0104", payload, zigate_ep=ZIGATE_EP)
    self.log.logging(
        "CasaIA", "Debug", "AC211_read_multi_pairing_code_request ++++ %s payload: %s" % (NwkId, payload), NwkId
    )


def AC211_ReadLearnedStatesRequest(self, NwkId):
    # Command 0x01
    cmd = "01"
    payload = cmd
    ffac_send_manuf_specific_cmd(self, NwkId, payload)
    self.log.logging("CasaIA", "Debug", "AC211_command_01_request ++++ %s payload: %s" % (NwkId, payload), NwkId)


def AC211_EnterSearchModeRequest(self, NwkId, parameter):
    # Command 0x40
    cmd = "40"
    payload = cmd + "%04x" % struct.unpack("H", struct.pack(">H", int(parameter)))[0]
    ffac_send_manuf_specific_cmd(self, NwkId, payload)
    self.log.logging("CasaIA", "Debug", "AC211_command_40_request ++++ %s payload: %s" % (NwkId, payload), NwkId)


def AC211_WritePairingCodeRequest(self, NwkId, pairing_code_value):
    # Command 0x20
    pairing_code = "%04x" % struct.unpack("H", struct.pack(">H", int(pairing_code_value)))[0]
    cmd = "20"
    payload = cmd + pairing_code
    ffac_send_manuf_specific_cmd(self, NwkId, payload)
    self.log.logging("CasaIA", "Debug", "AC211_WritePairingCodeRequest ++++ %s payload: %s" % (NwkId, payload), NwkId)


## 0xFFAD Client to Server
#####################################################################################
def AC201_read_multi_pairing_code_request(self, NwkId):
    # Command  0x00
    # determine which Endpoint
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_and_inc_SQN(self, NwkId)

    cluster_frame = "01"
    device_type = DEVICE_TYPE  # Device type
    cmd = "00"

    payload = cluster_frame + sqn + cmd + device_type
    raw_APS_request(self, NwkId, EPout, "ffad", "0104", payload, zigate_ep=ZIGATE_EP)
    self.log.logging(
        "CasaIA", "Debug", "AC201_read_multi_pairing_code_request ++++ %s payload: %s" % (NwkId, payload), NwkId
    )


def AC201_write_multi_pairing_code_request(self, NwkId, pairing_code_value):
    # Command 0x01
    device_type = DEVICE_TYPE
    device_id = DEVICE_ID

    pairing_code = "%04x" % struct.unpack("H", struct.pack(">H", int(pairing_code_value)))[0]
    cmd = "01"
    payload = cmd + device_type + device_id + pairing_code
    ffad_send_manuf_specific_cmd(self, NwkId, payload)
    self.log.logging(
        "CasaIA", "Debug", "AC201_write_multi_pairing_code_request ++++ %s payload: %s" % (NwkId, payload), NwkId
    )


def AC201_read_AC_status_request(self, NwkId):
    # Command 0x02

    self.log.logging("CasaIA", "Debug", "AC201_read_AC_status_request NwkId: %s" % (NwkId), NwkId)
    device_type = DEVICE_TYPE
    device_id = DEVICE_ID
    cmd = "02"
    payload = cmd + device_type + device_id
    ffad_send_manuf_specific_cmd(self, NwkId, payload)
    self.log.logging("CasaIA", "Debug", "AC201_read_AC_status_request ++++ %s payload: %s" % (NwkId, payload), NwkId)


def write_AC201_status_request(self, NwkId, Action, setpoint=None):
    # Command 0x03

    self.log.logging(
        "CasaIA",
        "Debug",
        "write_AC201_status_request NwkId: %s Action: %s Setpoint: %s" % (NwkId, Action, setpoint),
        NwkId,
    )

    if casaia_check_irPairing(self, NwkId) is None:
        return

    if Action not in AC201_COMMAND:
        self.log.logging(
            "CasaIA",
            "Error",
            "write_AC201_status_request - %s Unknow action: %s" % (NwkId, Action),
            NwkId,
            {"Error code": "CASAIA-AC201STREQ-01"},
        )
        return
    if Action in ("HeatSetpoint", "CoolSetpoint") and setpoint is None:
        self.log.logging(
            "CasaIA",
            "Error",
            "write_AC201_status_request - %s Setpoint without a setpoint value !" % (NwkId),
            NwkId,
            {"Error code": "CASAIA-AC201STREQ-02"},
        )
        return

    # Command 0x03
    device_type = "00"  # Device type
    device_id = DEVICE_ID
    command = AC201_COMMAND[Action]
    if Action in ("HeatSetpoint", "CoolSetpoint"):
        command += "%04x" % struct.unpack("H", struct.pack(">H", setpoint))[0]

    cmd = "03"
    payload = cmd + device_type + device_id + command

    ffad_send_manuf_specific_cmd(self, NwkId, payload)
    self.log.logging("CasaIA", "Debug", "write_AC201_status_request ++++ %s payload: %s" % (NwkId, payload), NwkId)
    AC201_read_AC_status_request(self, NwkId)


def AC201_read_learned_data_group_status_request(self, NwkId):
    # Command 0x11
    EPout = get_ffad_endpoint(self, NwkId)
    sqn = get_and_inc_SQN(self, NwkId)
    device_type = "00"  # Device type
    cluster_frame = "05"
    cmd = "11"
    payload = cluster_frame + CASAIA_MANUF_CODE_BE + sqn + cmd + device_type
    raw_APS_request(self, NwkId, EPout, "ffad", "0104", payload, zigate_ep=ZIGATE_EP)
    self.log.logging(
        "CasaIA",
        "Debug",
        "AC201_read_learned_data_group_status_request ++++ %s/%s payload: %s" % (NwkId, EPout, payload),
        NwkId,
    )


def AC201_read_learned_data_group_name_request(self, NwkId):
    # Command 0x12
    device_type = DEVICE_TYPE
    group_bitmap = "0000"

    cmd = "12"
    payload = cmd + device_type + group_bitmap
    ffad_send_manuf_specific_cmd(self, NwkId, payload)

    self.log.logging(
        "CasaIA", "Debug", "AC201_read_learned_data_group_name_request ++++ %s payload: %s" % (NwkId, payload), NwkId
    )


def AC201_command_mysterious(self, NwkId, magic):
    # Command 0x06

    cmd = "06"
    payload = cmd + magic
    ffad_send_manuf_specific_cmd(self, NwkId, payload)

    self.log.logging("CasaIA", "Debug", "AC201_command_mysterious ++++ %s payload: %s" % (NwkId, payload), NwkId)


## 0xFFAC Server to Client
#####################################################################################
def AC211_ReadPairingCodeResponse(self, Devices, NwkId, Ep, payload):
    # Command 0x00
    # ffff
    self.log.logging("CasaIA", "Debug", "AC211_read_multi_pairing_response %s payload: %s" % (NwkId, payload), NwkId)
    pairing_code = payload[0:4]
    store_casaia_attribute(self, NwkId, "ModuleIRCode", pairing_code, device_id=DEVICE_ID)


def AC211_ReadLearnedStatesResponse(self, Devices, NwkId, Ep, payload):
    # Command 0x01
    # 00
    self.log.logging("CasaIA", "Debug", "AC211_command_01_response %s payload: %s" % (NwkId, payload), NwkId)
    value = payload[0:2]
    store_casaia_attribute(self, NwkId, "LearnedState", value, device_id=DEVICE_ID)


## 0xFFAD Server to Client
#####################################################################################
def AC201_read_multi_pairing_response(self, Devices, NwkId, Ep, payload):
    # Command 0x00
    # 00 01 ffff 02 ffff 03 ffff 04 ffff 05 ffff
    self.log.logging("CasaIA", "Debug", "read_multi_pairing_response %s payload: %s" % (NwkId, payload), NwkId)

    device_type = payload[0:2]
    store_casaia_attribute(self, NwkId, "DeviceType", device_type)
    idx = 2
    while idx < len(payload):
        device_id = payload[idx : idx + 2]
        idx += 2
        pairing_code = payload[idx : idx + 4]
        store_casaia_attribute(self, NwkId, "ModuleIRCode", pairing_code, device_id=device_id)
        idx += 4


def AC201_read_AC_status_response(self, Devices, NwkId, Ep, payload):
    # Command 0x02

    self.log.logging("CasaIA", "Debug", "read_AC_status_response %s payload: %s" % (NwkId, payload), NwkId)

    status = payload[0:2]
    device_type = payload[2:4]
    device_id = payload[4:6]
    pairing_code = struct.unpack("H", struct.pack(">H", int(payload[6:10], 16)))[0]
    current_temp = struct.unpack("H", struct.pack(">H", int(payload[10:14], 16)))[0]
    system_mode = payload[14:16]
    heat_setpoint = struct.unpack("H", struct.pack(">H", int(payload[16:20], 16)))[0]
    cool_stepoint = struct.unpack("H", struct.pack(">H", int(payload[20:24], 16)))[0]
    fan_mode = payload[24:26]

    self.log.logging(
        "CasaIA",
        "Debug",
        "read_AC_status_response Status: %s device_type: %s device_id: %s pairing_code: %s current_temp: %s system_mode: %s heat_setpoint: %s cool_setpoint: %s fan_mode: %s"
        % (
            status,
            device_type,
            device_id,
            pairing_code,
            current_temp,
            system_mode,
            heat_setpoint,
            cool_stepoint,
            fan_mode,
        ),
        NwkId,
    )

    store_casaia_attribute(self, NwkId, "DeviceType", device_type)
    store_casaia_attribute(self, NwkId, "ModuleIRCode", str(pairing_code), device_id=device_id)
    store_casaia_attribute(self, NwkId, "DeviceStatus", status, device_id=device_id)
    store_casaia_attribute(self, NwkId, "CurrentTemp", current_temp, device_id=device_id)
    store_casaia_attribute(self, NwkId, "SystemMode", system_mode, device_id=device_id)
    store_casaia_attribute(self, NwkId, "HeatSetpoint", heat_setpoint, device_id=device_id)
    store_casaia_attribute(self, NwkId, "CoolSetpoint", cool_stepoint, device_id=device_id)
    store_casaia_attribute(self, NwkId, "FanMode", fan_mode, device_id=device_id)

    # Update Current Temperature Widget
    temp = round(current_temp / 100, 1)
    self.log.logging(
        "CasaIA", "Debug", "read_AC_status_response Status: %s request Update Temp: %s" % (NwkId, temp), NwkId
    )
    MajDomoDevice(self, Devices, NwkId, Ep, "0402", temp)

    # Update Fan Mode
    self.log.logging(
        "CasaIA", "Debug", "read_AC_status_response Status: %s request Update Fan Mode: %s" % (NwkId, fan_mode), NwkId
    )
    if system_mode == "00":
        MajDomoDevice(self, Devices, NwkId, Ep, "0202", "00")
    else:
        MajDomoDevice(self, Devices, NwkId, Ep, "0202", fan_mode)

    # Update SetPoint
    if str(check_hot_cold_setpoint(self, NwkId)) == "Heat":
        setpoint = str(round(heat_setpoint / 100, 1))
        self.log.logging(
            "CasaIA",
            "Debug",
            "read_AC_status_response Status: %s request Update Setpoint: %s" % (NwkId, setpoint),
            NwkId,
        )
        MajDomoDevice(self, Devices, NwkId, Ep, "0201", setpoint, Attribute_="0012")

    elif str(check_hot_cold_setpoint(self, NwkId)) == "Cool":
        setpoint = str(round(cool_stepoint / 100, 1))
        self.log.logging(
            "CasaIA",
            "Debug",
            "read_AC_status_response Status: %s request Update Setpoint: %s" % (NwkId, setpoint),
            NwkId,
        )
        MajDomoDevice(self, Devices, NwkId, Ep, "0201", setpoint, Attribute_="0012")

    # Update System Mode
    self.log.logging(
        "CasaIA",
        "Debug",
        "read_AC_status_response Status: %s request Update System Mode: %s" % (NwkId, system_mode),
        NwkId,
    )
    MajDomoDevice(self, Devices, NwkId, Ep, "0201", system_mode, Attribute_="001c")


def AC201_read_learned_data_group_status_request_response(self, Devices, NwkId, srcEp, payload):
    # Command 0x11
    device_type = payload[0:2]
    status = payload[2:6]


def AC201_read_learned_data_group_name_request_response(self, Devices, NwkId, srcEp, payload):
    # Cmmand 0x12
    device_type = payload[0:2]
    group_bitmap = payload[2:6]
    status = payload[6:8]
    group_num = payload[8:10]
    group_name = payload[10:34]
    store_casaia_attribute(self, NwkId, "GroupBitmap", group_bitmap)
    store_casaia_attribute(self, NwkId, "GroupNum", group_num)
    store_casaia_attribute(self, NwkId, "GroupName", group_name)


## Internal


def check_hot_cold_setpoint(self, NwkId):
    system_mode = get_casaia_attribute(self, NwkId, "SystemMode", device_id=DEVICE_ID)
    if system_mode == "04":
        return "Heat"
    if system_mode == "03":
        return "Cool"
    return None


def ffac_send_manuf_specific_cmd(self, NwkId, payload):

    cluster_frame = "05"
    sqn = get_and_inc_SQN(self, NwkId)
    EPout = get_ffad_endpoint(self, NwkId)

    data = cluster_frame + CASAIA_MANUF_CODE_BE + sqn
    data += payload
    raw_APS_request(self, NwkId, EPout, "ffac", "0104", data, zigate_ep=ZIGATE_EP)


def ffad_send_manuf_specific_cmd(self, NwkId, payload):

    cluster_frame = "05"
    sqn = get_and_inc_SQN(self, NwkId)
    EPout = get_ffad_endpoint(self, NwkId)

    data = cluster_frame + CASAIA_MANUF_CODE_BE + sqn
    data += payload
    raw_APS_request(self, NwkId, EPout, "ffad", "0104", data, zigate_ep=ZIGATE_EP)


def get_ffad_endpoint(self, NwkId):
    EPout = "01"
    for tmpEp in self.ListOfDevices[NwkId]["Ep"]:
        if "ffad" in self.ListOfDevices[NwkId]["Ep"][tmpEp]:
            EPout = tmpEp
    return EPout


def store_casaia_attribute(self, NwkId, Attribute, Value, device_id=None):

    if "CASA.IA" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["CASA.IA"] = {}
    if device_id:
        if device_id not in self.ListOfDevices[NwkId]["CASA.IA"]:
            self.ListOfDevices[NwkId]["CASA.IA"][device_id] = {}

        self.ListOfDevices[NwkId]["CASA.IA"][device_id][Attribute] = Value

    else:
        self.ListOfDevices[NwkId]["CASA.IA"][Attribute] = Value


def get_casaia_attribute(self, NwkId, Attribute, device_id=None):

    if "CASA.IA" not in self.ListOfDevices[NwkId]:
        self.log.logging(
            "CasaIA",
            "Debug",
            "get_casaia_attribute - %s CASA.IA not found in %s" % (NwkId, self.ListOfDevices[NwkId]),
            NwkId,
        )
        return None
    if device_id:
        if Attribute not in self.ListOfDevices[NwkId]["CASA.IA"][device_id]:
            self.log.logging(
                "CasaIA",
                "Debug",
                "get_casaia_attribute (1) - %s Attribute: %s not found in %s"
                % (NwkId, self.ListOfDevices[NwkId]["CASA.IA"][device_id]),
                NwkId,
            )
            return None
        return self.ListOfDevices[NwkId]["CASA.IA"][device_id][Attribute]
    if Attribute not in self.ListOfDevices[NwkId]["CASA.IA"]:
        self.log.logging(
            "CasaIA",
            "Debug",
            "get_casaia_attribute (2) - %s Attribute: %s not found in %s"
            % (NwkId, self.ListOfDevices[NwkId]["CASA.IA"]),
            NwkId,
        )
        return None
    return self.ListOfDevices[NwkId]["CASA.IA"][Attribute]


def open_casa_config(self):  # OK 6/11/2020

    casaiafilename = self.pluginconf.pluginConf["pluginConfig"] + "/" + CASAIA_CONFIG_FILENAME
    self.CasaiaPAC = {}
    if os.path.isfile(casaiafilename):
        with open(casaiafilename, "rt") as handle:
            try:
                self.CasaiaPAC = json.load(handle)
            except json.decoder.JSONDecodeError as e:
                res = "Failed"
                self.log.logging(
                    "CasaIA",
                    "Error",
                    "loadJsonDatabase poorly-formed %s, not JSON: %s" % (self.pluginConf["filename"], e),
                )


def get_pac_code(self, ieee):

    nwkid = self.IEEE2NWK[ieee]
    if "CASA.IA" not in self.ListOfDevices[nwkid]:
        return None

    if DEVICE_ID not in self.ListOfDevices[nwkid]["CASA.IA"]:
        return None

    if "IRCode" not in self.ListOfDevices[nwkid]["CASA.IA"][DEVICE_ID]:
        return None

    if int(self.ListOfDevices[nwkid]["CASA.IA"][DEVICE_ID]["IRCode"], 16) in (0x0, 0xFFFF):
        return None

    return self.ListOfDevices[nwkid]["CASA.IA"][DEVICE_ID]["IRCode"]
