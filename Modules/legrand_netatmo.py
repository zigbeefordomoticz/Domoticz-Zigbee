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
    Module: z_output.py

    Description: All communications towards Zigate

"""

import struct
from time import time

from Modules.basicOutputs import (read_attribute, write_attribute,
                                  write_attributeNoResponse)
from Modules.bindings import bindDevice, unbindDevice
from Modules.domoMaj import MajDomoDevice
from Modules.readAttributes import (ReadAttributeRequest_0b04_050b,
                                    ReadAttributeRequest_0001,
                                    ReadAttributeRequest_0006_0000,
                                    ReadAttributeRequest_fc01,
                                    ReadAttributeRequest_fc40)
from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import (extract_info_from_8085, get_and_inc_ZCL_SQN,
                           get_deviceconf_parameter_value,
                           is_ack_tobe_disabled,
                           retreive_cmd_payload_from_8002)
from Modules.zigateConsts import (HEARTBEAT, LEGRAND_REMOTES, MAX_LOAD_ZIGATE,
                                  ZIGATE_EP)

DIMMER_WO_NEUTRAL = "Dimmer switch wo neutral"
CONNECTED_OUTLET = "Connected outlet"
MOBILE_OUTLET = "Mobile outlet"
SHUTTER_SWITCH = "Shutter switch with neutral"
MICROMODULE_SWITCH = "Micromodule switch"
LEGRAND_FILPILOTE = "LegrandFilPilote"

ENABLE_LED_IN_DARK = "EnableLedInDark"
ENABLE_DIMMER = "EnableDimmer"
ENABLE_LED_IF_ON = "EnableLedIfOn"
ENABLE_LED_SHUTTER = "EnableLedShutter"


LEGRAND_CLUSTER_FC01 = {
    DIMMER_WO_NEUTRAL: { ENABLE_LED_IN_DARK: "0001", ENABLE_DIMMER: "0000", ENABLE_LED_IF_ON: "0002"},
    CONNECTED_OUTLET: { ENABLE_LED_IF_ON: "0002"},
    MOBILE_OUTLET: { ENABLE_LED_IF_ON: "0002"},
    SHUTTER_SWITCH: { ENABLE_LED_SHUTTER: "0001"},
    MICROMODULE_SWITCH: {"None": "None"},
}

LEGRAND_REFRESH_TIME = 10815   # (3 * 3600) + 15
LEGRAND_COMMAND_NAME = (LEGRAND_FILPILOTE, ENABLE_LED_IN_DARK, ENABLE_DIMMER, ENABLE_LED_IF_ON, ENABLE_LED_SHUTTER)

GENERIC_LEGRAND_CLUSTER_FC01 = {
    "DIMMER": { ENABLE_LED_IN_DARK: "0001", ENABLE_DIMMER: "0000", ENABLE_LED_IF_ON: "0002"},
    "CONNECTED_OUTLET": { ENABLE_LED_IF_ON: "0002"},
    "MOBILE_OUTLET": { ENABLE_LED_IF_ON: "0002"},
    "SHUTTER": { ENABLE_LED_SHUTTER: "0001"},
    "MICROMODULE": {"None": "None"},
}

def get_legrand_cluster_fc01_features(self, nwkid):
    
    model_name = self.ListOfDevices[nwkid].get("Model", "")
    fc01_functions = get_deviceconf_parameter_value(self, model_name, "FC01_FUNCTIONALITIES", return_default=None)
    
    self.log.logging( "Legrand", "Debug", f"get_legrand_cluster_fc01_features '{model_name}' {fc01_functions}'", nwkid)

    if fc01_functions is None:
        self.log.logging( "Legrand", "Debug", f"get_legrand_cluster_fc01_features old way: '{fc01_functions}'", nwkid)
        return LEGRAND_CLUSTER_FC01.get(model_name, "")

    self.log.logging( "Legrand", "Debug", f"get_legrand_cluster_fc01_features new way: '{fc01_functions}'", nwkid)

    return GENERIC_LEGRAND_CLUSTER_FC01[ fc01_functions ]

def pollingLegrand(self, key):

    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """
    return False


def callbackDeviceAwake_Legrand(self, Devices, NwkId, EndPoint, cluster):

    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part
    """

    return


def legrandReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):
    self.log.logging(
        "Legrand",
        "Debug",
        "legrandReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s"
        % (srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload),
    )
    # At Device Annoucement 0x00 and 0x05 are sent by device
    default_response, GlobalCommand, Sqn, ManufacturerCode, Command, Data = retreive_cmd_payload_from_8002(MsgPayload)
    self.log.logging(
        "Legrand",
        "Debug",
        " NwkId: %s/%s Cluster: %s Command: %s Data: %s" % (srcNWKID, srcEp, ClusterID, Command, Data),
    )

    if ClusterID == "0102" and Command == "00":  # No data (Cluster 0x0102)
        pass
    elif ClusterID == "0102" and Command == "01":  # No data (Cluster 0x0102)
        pass
    elif ClusterID == "fc01" and Command == "04":  # Write Attribute Responsee
        pass
    elif ClusterID == "fc01" and Command == "05":
        # Get _Ieee of Shutter Device
        _ieee = "%08x" % struct.unpack("q", struct.pack(">Q", int(Data[0:16], 16)))[0]
        assign_group_membership_to_legrand_remote(
            self,
            srcNWKID,
            srcEp,
        )

    elif ClusterID == "fc01" and Command == "09":
        # IEEE of End Device (remote  )
        _ieee = "%08x" % struct.unpack("q", struct.pack(">Q", int(Data[0:16], 16)))[0]
        leftright = Data[16:18] if len(Data) == 18 else None
        self.log.logging("Legrand", "Debug", "---> Decoding cmd 0x09 Ieee: %s leftright: %s" % (_ieee, leftright))
        assign_group_membership_to_legrand_remote(self, srcNWKID, srcEp, leftright)

    elif ClusterID == "fc01" and Command == "0a":
        LegrandGroupMemberShip = Data[:4]
        _ieee = "%08x" % struct.unpack("q", struct.pack(">Q", int(Data[4:20], 16)))[0]  # IEEE of Device
        _code = Data[20:24]
        self.log.logging(
            "Legrand",
            "Debug",
            "---> Decoding cmd: 0x0a Group: %s, Ieee: %s Code: %s" % (LegrandGroupMemberShip, _ieee, _code),
        )
        status = "00"
        _ieee = '%08x' %struct.unpack('q',struct.pack('>Q',int(ieee,16)))[0]
        send_legrand_command(self, Sqn, srcNWKID, srcEp, ClusterID, "10", status + _code + _ieee)


def assign_group_membership_to_legrand_remote(self, NwkId, Ep, leftright=None):
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    cmd = "08"
    if leftright:
        cmd = "0c"
        self.log.logging(
            "Legrand", "Debug", "assign_group_membership_to_legrand_remote %s lefright: %s" % (NwkId, leftright)
        )

    groupid = get_groupid_for_remote(self, NwkId, Ep, leftright)
    if groupid:
        LegrandGroupMemberShip = "%04x" % struct.unpack("H", struct.pack(">H", int(groupid, 16)))[0]
        if leftright:
            send_legrand_command(self, sqn, NwkId, Ep, "fc01", cmd, LegrandGroupMemberShip + leftright)
        else:
            send_legrand_command(self, sqn, NwkId, Ep, "fc01", cmd, LegrandGroupMemberShip)


def get_groupid_for_remote(self, NwkId, Ep, leftright):
    GroupId = None
    if "Legrand" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Legrand"] = {}
    if "RemoteGroup" not in self.ListOfDevices[NwkId]["Legrand"]:
        self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"] = {}
    if leftright:
        if leftright not in self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"]:
            self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"][leftright] = None
        if self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"][leftright]:
            return self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"][leftright]
    else:
        if "Single" not in self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"]:
            self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"]["Single"] = None
        if self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"]["Single"]:
            return self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"]["Single"]

    # We need to create a groupId
    if self.groupmgt:
        GroupId = self.groupmgt.get_available_grp_id(0xFEFE, 0xFE00)
        if leftright:
            self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"][leftright] = GroupId
        else:
            self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"]["Single"] = GroupId
        if GroupId:
            self.groupmgt.add_group_member_ship_from_remote(NwkId, Ep, GroupId)
    return GroupId


def send_legrand_command(self, sqn, nwkid, ep, cluster_id, cmd, data):
    """
    Handles the command processing for Legrand devices.
    """

    self.log.logging("Legrand", "Debug", f"send_legrand_command Cmd: {cmd} Data: {data}")

    if cmd == "00":
        # Read Attribute received
        attribute = data[2:4] + data[:2]

        if cluster_id == "0000" and attribute == "f000":
            # Respond to Time Of Operation
            cmd = "01"
            status = "00"
            cluster_frame = "1c"
            data_type = "23"  # Uint32

            # Compute PluginTimeOfOperation
            plugin_time_of_operation = f"{self.HeartbeatCount * HEARTBEAT:08X}"
            formatted_time = "".join(plugin_time_of_operation[i:i + 2] for i in (6, 4, 0, 2))

            payload = f"{cluster_frame}{sqn}{cmd}{attribute}{status}{data_type}{formatted_time}"
            _send_raw_aps_request(self, nwkid, ep, cluster_id, payload)
        return

    if cmd in {"08", "0c"}:
        # Assign GroupId to a single or double remote
        manuf_spec = "2110"  # Legrand Manufacturer Specific: 0x1021
        cluster_frame = "1d"  # Cluster Specific, Manufacturer Specific
        payload = f"{cluster_frame}{manuf_spec}{sqn}{cmd}{data}"
        _send_raw_aps_request(self, nwkid, ep, cluster_id, payload)
        return


def _send_raw_aps_request(self, nwkid, ep, ClusterID, payload):
    """
    Sends a raw APS request with common parameters.
    """
    raw_APS_request(
        self,
        nwkid,
        ep,
        ClusterID,
        "0104",
        payload,
        zigate_ep=ZIGATE_EP,
        ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
        highpriority=True,
    )
    self.log.logging("Legrand", "Log", f"loggingLegrand - Nwkid: {nwkid}/{ep} Cluster: {ClusterID}, Payload: {payload}")


def rejoin_legrand_reset(self):

    # Check if we have any Legrand devices if so send teh Reset to the Air
    for x in self.ListOfDevices:
        if "Manufacturer" in self.ListOfDevices[x] and self.ListOfDevices[x]["Manufacturer"] == "1021":
            break
        if "Manufacturer Name" in self.ListOfDevices[x] and self.ListOfDevices[x]["Manufacturer Name"] == "Legrand":
            break
    else:
        # No Legrand devices found
        return

    # Send a Write Attributes no responses
    self.log.logging( "Legrand", "Status", "Detected Legrand IEEE, broadcast Write Attribute 0x0000/0xf000")
    write_attributeNoResponse(self, "ffff", ZIGATE_EP, "01", "0000", "1021", "01", "f000", "23", "00000000")


def _is_refresh_time(self, nwkid, command):
    """
    Check if the command can be refreshed based on the current time and the LEGRAND_REFRESH_TIME.

    Args:
        nwkid (str): The network ID.
        command (str): The command for the Legrand device.
    
    Returns:
        bool: True if the refresh time is reached; False if not.
    """
    self.log.logging("Legrand", "Debug", f"_is_refresh_time Nwkid: {nwkid} Cmd: {command}", nwkid)
    
    if is_zigate_bellow_or_equal_31c(self):
        self.log.logging("Legrand", "Debug", f"_is_refresh_time Nwkid: {nwkid} firmware too old", nwkid)
        return True

    current_time = int(time())  # Avoid multiple calls to time()
    legrand_data = self.ListOfDevices.get(nwkid, {}).get("Legrand", {})
    last_refresh = legrand_data.get(command, 0)

    if current_time < (last_refresh + LEGRAND_REFRESH_TIME):
        # Not time to refresh
        return False

    # Time to refresh
    legrand_data[command] = current_time  # Update refresh time
    return True  


def legrand_fc01(self, nwkid, command, on_off):
    """
    Main function to handle the Legrand commands related to device attributes.

    Args:
        nwkid (str): The network ID.
        command (str): The command to process.
        on_off (int): The on/off state for the command.
    """
    if nwkid not in self.ListOfDevices:
        return

    model_name = self.ListOfDevices[nwkid].get("Model")
    if model_name is None:
        return

    self.log.logging("Legrand", "Debug", f"legrand_fc01 Nwkid: {nwkid} Cmd: {command} OnOff: {on_off}", nwkid)

    LEGRAND_COMMAND_NAME = ( LEGRAND_FILPILOTE, ENABLE_LED_IN_DARK, ENABLE_DIMMER, ENABLE_LED_IF_ON, ENABLE_LED_SHUTTER )

    # Validate command
    if command not in LEGRAND_COMMAND_NAME:
        self.log.logging("Legrand", "Error", f"Unknown Legrand command {command}")
        return

    legrand_features = get_legrand_cluster_fc01_features(self, nwkid)
    self.log.logging("Legrand", "Debug", f"legrand_fc01 Avaliable features {legrand_features}", nwkid)

    if not legrand_features:
        self.log.logging("Legrand", "Error", f"{nwkid} is not an Legrand known model: {model_name}", nwkid)
        return

    legrand_data = self.ListOfDevices.setdefault(nwkid, {}).setdefault("Legrand", {})
    for cmd in LEGRAND_COMMAND_NAME:
        legrand_data.setdefault(cmd, 0xFF)

    if command not in legrand_features:
        self.log.logging("Legrand", "Debug", f"legrand_fc01 Nwkid: {nwkid} Cmd: {command} not in legrand_features: {legrand_features}", nwkid)
        return

    # Process the command
    data_type, attr_data = _process_legrand_command(self, command, on_off)
    if not data_type or not attr_data:
        return

    self.log.logging("Legrand", "Debug", f"--------> {command} Nwkid: {nwkid} data_type: {data_type} Hdata: {attr_data}", nwkid)

    fc01_attr = legrand_features[command]
    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" % 0xFC01

    ep_out = next(
        (tmpEp for tmpEp, clusters in self.ListOfDevices[nwkid]["Ep"].items() if "fc01" in clusters),
        "01"
    )

    self.log.logging(
        "Legrand", "Debug", 
        f"legrand {command} on_off - for {nwkid} with value {attr_data} / cluster: {cluster_id}, attribute: {fc01_attr} type: {data_type}", 
        nwkid=nwkid
    )

    # Write the attribute to the device
    write_attribute(
        self, nwkid, "01", ep_out, cluster_id, manuf_id, manuf_spec, fc01_attr, data_type, attr_data,
        ackIsDisabled=is_ack_tobe_disabled(self, nwkid)
    )

    # Request to read the attribute
    ReadAttributeRequest_fc01(self, nwkid)


def _process_legrand_command(self, command, on_off):
    """
    Processes the command and prepares the corresponding data for sending to the device.

    Args:
        command (str): The command to be processed.
        on_off (int): The state to apply (1 for ON, 0 for OFF).
    
    Returns:
        data_type (str): The data type corresponding to the command.
        attr_data (str): The data formatted appropriately for the command.
    """
    # Define a dictionary for commands that use the same data format (Bool for on/off)
    bool_commands = {ENABLE_LED_IN_DARK, ENABLE_LED_SHUTTER, ENABLE_LED_IF_ON}
    self.log.logging( "Legrand", "Debug", f"_process_legrand_command {command} with value {on_off}", )

    # Handle Bool-type commands
    if command in bool_commands:
        data_type = "10"  # Bool
        attr_data = f"{on_off:02x}"  # Format on_off as 2-digit hex
        return data_type, attr_data

    # Handle ENABLE_DIMMER command (16-bit Data)
    if command == ENABLE_DIMMER:
        data_type = "09"  # 16-bit Data
        attr_data = {
            1: "0101",  # Enable Dimmer
            0: "0100",  # Disable Dimmer
        }.get(on_off, "0000")  # Default to "0000" for any other value

        return data_type, attr_data

    # Return None if command doesn't match known types
    return None, None


def cable_connected_mode(self, nwkid, Mode):

    data_type = "09"  # 16-bit Data
    Hattribute = "0000"
    Hdata = "0000"

    if Mode == "10":
        # Sortie de Cable: 0x0100
        # Radiateur sans FIP: 0x0100
        # Appareil de cuisine: 0x0100
        Hdata = "0100"  # Disable FIP

    elif Mode == "20":
        # FIP
        # Radiateur avec FIP: 0x0200 + Bind fc40 + configReporting ( fc40 / 0000 / TimeOut 600 )
        Hdata = "0200"  # Enable FIP

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" % 0xFC01

    EPout = "01"
    for tmpEp in self.ListOfDevices[nwkid]["Ep"]:
        if "fc01" in self.ListOfDevices[nwkid]["Ep"][tmpEp]:
            EPout = tmpEp

    write_attribute(
        self,
        nwkid,
        "01",
        EPout,
        cluster_id,
        manuf_id,
        manuf_spec,
        Hattribute,
        data_type,
        Hdata[2:4] + Hdata[0:2],
        ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
    )
    ReadAttributeRequest_0006_0000(self, nwkid)
    ReadAttributeRequest_0b04_050b(self, nwkid)
    ReadAttributeRequest_fc40(self, nwkid)
    # Function cable_connected_mode Cluster fc01 is not reported even if binded Attribute fc01/0000 is not refreshed after change in domoticz ---> Add Force read
    ReadAttributeRequest_fc01(self, nwkid)


def legrand_fc40(self, nwkid, Mode):
    # With the permission of @Thorgal789 who did the all reverse enginnering of this cluster

    CABLE_OUTLET_MODE = {
        "Confort": 0x00,
        "Confort -1": 0x01,
        "Confort -2": 0x02,
        "Eco": 0x03,
        "Frost Protection": 0x04,
        "Off": 0x05,
    }

    if Mode not in CABLE_OUTLET_MODE:
        self.log.logging( "Legrand", "Error", " Bad Mode : %s for %s" % (Mode, nwkid))
        return

    Hattribute = "0000"
    data_type = "30"  # 8bit Enum
    Hdata = CABLE_OUTLET_MODE[Mode]
    # manuf_id = "1021"  # Legrand Code
    # manuf_spec = "01"  # Manuf specific flag
    cluster_id = "%04x" % 0xFC40

    EPout = "01"
    for tmpEp in self.ListOfDevices[nwkid]["Ep"]:
        if "fc40" in self.ListOfDevices[nwkid]["Ep"][tmpEp]:
            EPout = tmpEp

    self.log.logging(
        "Legrand",
        "Debug",
        "legrand %s Set Fil pilote mode - for %s with value %s / cluster: %s, attribute: %s type: %s"
        % (Mode, nwkid, Hdata, cluster_id, Hattribute, data_type),
        nwkid=nwkid,
    )

    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    fcf = "15"
    # manufspec = "01"
    manufcode = "1021"
    cmd = "00"
    data = "%02x" % CABLE_OUTLET_MODE[Mode]
    payload = fcf + manufcode[2:4] + manufcode[:2] + sqn + cmd + data
    raw_APS_request(
        self,
        nwkid,
        EPout,
        "fc40",
        "0104",
        payload,
        zigate_ep=ZIGATE_EP,
        ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
    )


def legrand_Dimmer_by_nwkid(self, NwkId, on_off):
    """
    Enables or disables the dimmer functionality for a Legrand device with the given network ID.

    Args:
        NwkId (str): The network ID of the device.
        on_off (int): The state to set for the dimmer (1 for ON, 0 for OFF).
    """
    self.log.logging("Legrand", "Debug", f"legrand_Dimmer_by_nwkid - NwkId: {NwkId} OnOff: {on_off}", NwkId)

    device = self.ListOfDevices.get(NwkId, {})

    # Validate device existence and manufacturer
    if device.get("Manufacturer Name") != "Legrand" or "Model" not in device:
        return

    # Ensure the model is a dimmer
    if ENABLE_DIMMER not in get_legrand_cluster_fc01_features(self, NwkId):
        self.log.logging("Legrand", "Error", f"legrand_Dimmer_by_nwkid - NwkId: {NwkId} OnOff: {on_off} but not a dimmer {get_legrand_cluster_fc01_features(self, NwkId)}", NwkId)
        return

    # Initialize Legrand data if missing
    device.setdefault("Legrand", {})

    # Handle Zigate versioning
    if is_zigate_above_or_equal_31d(self):
        legrand_data = device["Legrand"]
        current_state = legrand_data.get(ENABLE_DIMMER)

        # If the current state matches the desired state, do nothing
        if current_state == on_off:
            self.log.logging("Legrand", "Debug", f"legrand_Dimmer_by_nwkid - {NwkId} nothing to do", NwkId)
            return

        # Send the command and update state
        legrand_fc01(self, NwkId, ENABLE_DIMMER, on_off)
        del legrand_data[ENABLE_DIMMER]

        # Enable or disable dimmer functionality
        if on_off:
            legrand_dimmer_enable(self, NwkId)
        else:
            legrand_dimmer_disable(self, NwkId)

    else:
        # For older Zigate versions, set the dimmer state to 0 before sending the command
        device["Legrand"][ENABLE_DIMMER] = 0
        legrand_fc01(self, NwkId, ENABLE_DIMMER, on_off)


def legrand_enable_Led_IfOn_by_nwkid(self, NwkId, on_off):
    """
    Enables or disables the LED indicator when the device is ON for a Legrand device with the given network ID.

    Args:
        NwkId (str): The network ID of the device.
        on_off (int): The state to set for the LED (1 for ON, 0 for OFF).
    """
    self.log.logging("Legrand", "Debug", f"legrand_enable_Led_IfOn_by_nwkid - NwkId: {NwkId} OnOff: {on_off}", NwkId)

    device = self.ListOfDevices.get(NwkId, {})

    # Validate device existence and manufacturer
    if device.get("Manufacturer Name") != "Legrand" or "Model" not in device:
        return

    # Check if the device model supports LED If On
    supported_models = {
        CONNECTED_OUTLET,
        MOBILE_OUTLET,
        DIMMER_WO_NEUTRAL,
        SHUTTER_SWITCH,
        MICROMODULE_SWITCH,
    }
    if device["Model"] not in supported_models:
        return

    # Initialize Legrand data if missing
    device.setdefault("Legrand", {})

    # Handle Zigate versioning
    if is_zigate_above_or_equal_31d(self):
        legrand_data = device["Legrand"]
        current_state = legrand_data.get(ENABLE_LED_IF_ON)

        # If the current state matches the desired state, do nothing
        if current_state == on_off:
            self.log.logging("Legrand", "Debug", f"legrand_enable_Led_IfOn_by_nwkid - {NwkId} nothing to do", NwkId)
            return

        # Send the command and update state
        legrand_fc01(self, NwkId, ENABLE_LED_IF_ON, on_off)
        del legrand_data[ENABLE_LED_IF_ON]

    else:
        # For older Zigate versions, set the LED state to 0 before sending the command
        device["Legrand"][ENABLE_LED_IF_ON] = 0
        legrand_fc01(self, NwkId, ENABLE_LED_IF_ON, on_off)


def legrand_enable_Led_InDark_by_nwkid(self, NwkId, on_off):
    """
    Enables or disables the LED in dark mode for a Legrand device with the given network ID.

    Args:
        NwkId (str): The network ID of the device.
        on_off (int): The state to set for the LED (1 for ON, 0 for OFF).
    """
    self.log.logging("Legrand", "Debug", f"legrand_enable_Led_InDark_by_nwkid - NwkId: {NwkId} OnOff: {on_off}", NwkId)

    device = self.ListOfDevices.get(NwkId, {})

    # Validate device existence and manufacturer
    if device.get("Manufacturer Name") != "Legrand" or "Model" not in device:
        return

    # Check if the device model supports the feature
    if device["Model"] not in {
        CONNECTED_OUTLET,
        MOBILE_OUTLET,
        DIMMER_WO_NEUTRAL,
        SHUTTER_SWITCH,
        MICROMODULE_SWITCH,
    }:
        return

    # Initialize "Legrand" dictionary if missing
    legrand_data = device.setdefault("Legrand", {})

    # Handle Zigate versioning
    if is_zigate_above_or_equal_31d(self):
        current_state = legrand_data.get(ENABLE_LED_IN_DARK)

        # If the current state matches the desired state, do nothing
        if current_state == on_off:
            self.log.logging("Legrand", "Debug", f"legrand_enable_Led_InDark_by_nwkid - {NwkId} nothing to do", NwkId)
            return

        # Send the command and remove the old state
        legrand_fc01(self, NwkId, ENABLE_LED_IN_DARK, on_off)
        del legrand_data[ENABLE_LED_IN_DARK]

    else:
        # For older Zigate versions, set the LED state to 0 before sending the command
        legrand_data[ENABLE_LED_IN_DARK] = 0
        legrand_fc01(self, NwkId, ENABLE_LED_IN_DARK, on_off)


def legrand_enable_Led_Shutter_by_nwkid(self, NwkId, on_off):
    """
    Enables or disables the LED shutter on the Legrand device specified by NwkId.

    Args:
        NwkId (str): The network ID of the device.
        on_off (int): The state to set for the LED shutter (1 for ON, 0 for OFF).
    """
    # Log the action
    self.log.logging( "Legrand", "Debug", f"legrand_enable_Led_Shutter_by_nwkid - NwkId: {NwkId} OnOff: {on_off}", NwkId )
    
    device = self.ListOfDevices.get(NwkId, {})

    # Check if necessary data exists for the device
    if device.get("Manufacturer Name") != "Legrand" or "Model" not in device:
        self.log.logging( "Legrand", "Debug", f"legrand_enable_Led_Shutter_by_nwkid - {NwkId} 'Legrand' or 'Model' not found", NwkId )
        return

    # Initialize Legrand data if missing
    device.setdefault("Legrand", {})

    if device["Model"] not in SHUTTER_SWITCH:
        self.log.logging( "Legrand", "Debug", f"legrand_enable_Led_Shutter_by_nwkid - {NwkId} not a shutter", NwkId )
        return

    # If the device is a version that supports Zigate >= 31d
    if is_zigate_above_or_equal_31d(self):
        legrand_data = device["Legrand"]
        current_state = legrand_data.get(ENABLE_LED_SHUTTER)
        
        self.log.logging( "Legrand", "Debug", f"legrand_enable_Led_Shutter_by_nwkid - {NwkId} current_state '{current_state}' target_state '{on_off}' ", NwkId )

        # If the state matches the desired on_off, there's nothing to do
        if current_state == on_off:
            self.log.logging( "Legrand", "Debug", f"legrand_enable_Led_Shutter_by_nwkid - {NwkId} nothing to do", NwkId )
            return

        # Set the LED shutter state
        legrand_fc01(self, NwkId, ENABLE_LED_SHUTTER, on_off)
        # Clear the state after execution
        legrand_data[ENABLE_LED_SHUTTER] = 0

    else:
        # For older Zigate versions, directly modify the Legrand data
        device["Legrand"][ENABLE_LED_SHUTTER] = 0
        legrand_fc01(self, NwkId, ENABLE_LED_SHUTTER, on_off)


def legrandReenforcement(self, NWKID):

    if "Health" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Health"] == "Not Reachable":
        return False

    if "Manufacturer Name" not in self.ListOfDevices[NWKID]:
        return False

    if self.ListOfDevices[NWKID]["Manufacturer Name"] != "Legrand":
        return False

    if "Legrand" not in self.ListOfDevices[NWKID]:
        self.ListOfDevices[NWKID]["Legrand"] = {
            'EnableDimmer': 255,
            'EnableLedIfOn': 255,
            'EnableLedShutter': 255,
            'EnableLedInDark': 255,
            'LegrandFilPilote': 255,
        }

    if "Model" not in self.ListOfDevices[NWKID]:
        return False

    model = self.ListOfDevices[NWKID]["Model"]
    if model not in LEGRAND_CLUSTER_FC01:
        return False

    for cmd in LEGRAND_CLUSTER_FC01[model]:
        if cmd == "None":
            continue

        if self.busy or self.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE:
            return True

        if cmd not in self.ListOfDevices[NWKID]["Legrand"]:
            self.ListOfDevices[NWKID]["Legrand"][cmd] = 0xFF

        if self.pluginconf.pluginConf[cmd] != self.ListOfDevices[NWKID]["Legrand"][cmd]:
            if self.pluginconf.pluginConf[cmd]:
                legrand_fc01(self, NWKID, cmd, "On")
            else:
                legrand_fc01(self, NWKID, cmd, "Off")

    return False


def legrand_refresh_battery_remote(self, nwkid):

    if "Model" not in self.ListOfDevices[nwkid]:
        return
    if self.ListOfDevices[nwkid]["Model"] not in LEGRAND_REMOTES:
        return
    if (
        "BatteryUpdateTime" in self.ListOfDevices[nwkid]
        and self.ListOfDevices[nwkid]["BatteryUpdateTime"] + 3600 > time()
    ):
        return
    ReadAttributeRequest_0001(self, nwkid, force_disable_ack=True)


def store_netatmo_attribute(self, NwkId, Attribute, Value):
    if "Legrand" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Legrand"] = {}
    self.ListOfDevices[NwkId]["Legrand"][Attribute] = Value


def legrand_dimmer_enable(self, NwkId):

    self.log.logging("Legrand", "Log", "legrand_dimmer_enable - %s " % NwkId, NwkId)

    # Bind
    if "IEEE" not in self.ListOfDevices[NwkId]:
        return
    ieee = self.ListOfDevices[NwkId]["IEEE"]
    if ieee not in self.IEEE2NWK:
        return
    bindDevice(self, ieee, "01", "0008", destaddr=None, destep="01")

    attribute_reporting_record = {
        "Attribute": "0000",
        "DataType": "20",
        "minInter": "0001",
        "maxInter": "0258",
        "timeOut": "0000",
    }

    self.configureReporting.send_configure_reporting_attributes_set(
        NwkId, ZIGATE_EP, "01", "0008", "00", "00", "0000", [ attribute_reporting_record,] )
    
    # 0x0008 / 0x00011 Change 0x01 Min: 0x00, Max 600
    attribute_reporting_record = {
        "Attribute": "0000",
        "DataType": "20",
        "minInter": "0000",
        "maxInter": "0258",
        "timeOut": "0000",
    }

    #self.configureReporting.send_configure_reporting_attributes_set(
    #    NwkId, ZIGATE_EP, "01", "0008", "00", "00", "0000", 1, "0020/0011/0000/0258/0000/01", [0x0011])
    self.configureReporting.send_configure_reporting_attributes_set(
        NwkId, ZIGATE_EP, "01", "0008", "00", "00", "0000", [attribute_reporting_record,])

    # Read Attribute 0x0008 / 0x0000 , 0x0011
    read_attribute(self, NwkId, ZIGATE_EP, "01", "0008", "00", "00", "0000", 1, "0000", ackIsDisabled=True)
    read_attribute(self, NwkId, ZIGATE_EP, "01", "0008", "00", "00", "0000", 1, "0011", ackIsDisabled=True)
    
    # Read Attribute 0x0006 / 0x0000
    read_attribute(self, NwkId, ZIGATE_EP, "01", "0006", "00", "00", "0000", 1, "0000", ackIsDisabled=True)


def legrand_dimmer_disable(self, NwkId):

    self.log.logging("Legrand", "Log", "legrand_dimmer_disable - %s " % NwkId, NwkId)
    # Unbind
    unbindDevice(self, self.ListOfDevices[NwkId]["IEEE"], "01", "0008")


def legrand_remote_switch_8095(self, Devices, MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_ ):
    if MsgCmd == "01":  # On
        self.log.logging(
            "Input",
            "Debug",
            "Decode8095 - Legrand: %s/%s, Cmd: %s, Unknown: %s " % (MsgSrcAddr, MsgEP, MsgCmd, unknown_),
            MsgSrcAddr,
        )
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd)
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)

    elif MsgCmd == "00":  # Off
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd)
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId] = {}
        self.log.logging(
            "Input",
            "Debug",
            "Decode8095 - Legrand: %s/%s, Cmd: %s, Unknown: %s " % (MsgSrcAddr, MsgEP, MsgCmd, unknown_),
            MsgSrcAddr,
        )

    elif MsgCmd == "02":  # Toggle
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "02")
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)

def legrand_remote_switch_8085(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, MsgData):

    TYPE_ACTIONS = {
        None: "",
        "01": "move",
        "02": "click",
        "03": "stop",
    }
    DIRECTION = {None: "", "00": "up", "01": "down"}

    step_mod, up_down, step_size, transition = extract_info_from_8085(MsgData)

    if TYPE_ACTIONS[step_mod] in ("click", "move"):
        selector = TYPE_ACTIONS[step_mod] + DIRECTION[up_down]
    elif TYPE_ACTIONS[step_mod] == "stop":
        selector = TYPE_ACTIONS[step_mod]
    else:
        self.log.logging( "Legrand", "Error", "Decode8085 - Unknown state for %s step_mod: %s up_down: %s" % (MsgSrcAddr, step_mod, up_down))
        return

    self.log.logging("Input", "Debug", "Decode8085 - Legrand selector: %s" % selector, MsgSrcAddr)
    if selector:
        if "Param" in self.ListOfDevices[MsgSrcAddr] and "netatmoReleaseButton" in self.ListOfDevices[MsgSrcAddr]["Param"] and self.ListOfDevices[MsgSrcAddr]["Param"]["netatmoReleaseButton"]:
            # self.log.logging( "Input", 'Log',"Receive: %s/%s %s" %(MsgSrcAddr,MsgEP,selector))
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, selector)
            self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = selector
        elif TYPE_ACTIONS[step_mod] != "stop":
            # self.log.logging( "Input", 'Log',"Receive: %s/%s %s REQUEST UPDATE" %(MsgSrcAddr,MsgEP,selector))
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, selector)
            self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = selector


def legrand_motion_8095(self, Devices, MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_ ):
    self.log.logging(
        "Input",
        "Log",
        "Decode8095 - Legrand: %s/%s, Cmd: %s, Unknown: %s " % (MsgSrcAddr, MsgEP, MsgCmd, unknown_),
        MsgSrcAddr,
    )
    MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0406", unknown_)


def legrand_motion_8085(self, Devices, MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_, MsgData):
    step_mod, up_down, step_size, transition = extract_info_from_8085(MsgData)
    self.log.logging(
        "Input",
        "Log",
        "Decode8085 - Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s step_mode: %s up_down: %s step_size: %s transition: %s"
        % (MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, step_mod, up_down, step_size, transition),
        MsgSrcAddr,
    )



def is_zigate_above_or_equal_31d(self):
    return self.zigbee_communication != "native" or (self.FirmwareVersion and int(self.FirmwareVersion, 16) >= 0x31D)

def is_zigate_below_31d(self): 
    return self.zigbee_communication == "native" and self.FirmwareVersion and int(self.FirmwareVersion, 16) < 0x31D

def is_zigate_bellow_or_equal_31c(self): 
    return self.zigbee_communication == "native" and self.FirmwareVersion and int(self.FirmwareVersion, 16) <= 0x31C


LEGRAND_DEVICE_PARAMETERS = {
    "netatmoLedIfOn": { "callable": legrand_enable_Led_IfOn_by_nwkid,"description": "Enable Led if On, valid for model  'Connected outlet', 'Mobile outlet', 'Dimmer switch wo neutral', 'Shutter switch with neutral', 'Micromodule switch'. (0 or 1)"},
    "netatmoLedInDark": { "callable": legrand_enable_Led_InDark_by_nwkid, "description": "Enable Led if On, valid for model  'Connected outlet', 'Mobile outlet', 'Dimmer switch wo neutral', 'Shutter switch with neutral', 'Micromodule switch'. (0 or 1)"},
    "netatmoLedShutter": { "callable": legrand_enable_Led_Shutter_by_nwkid, "description": "Enable Led if On, valid for model  'Connected outlet', 'Shutter switch with neutral'. (0 or 1)"},
    "netatmoEnableDimmer": { "callable": legrand_Dimmer_by_nwkid, "description": "Enable dimming for 'Dimmer switch wo neutral'. (0 or 1)"},

}