# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import struct

from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import (build_fcf, fcf_direction, get_and_inc_ZCL_SQN,
                           is_ack_tobe_disabled)
from Zigbee.encoder_tools import decode_endian_data

DEFAULT_ACK_MODE = False

# General Command Frame

def zcl_raw_reset_device(self, nwkid, epin, epout):
    """
    Sends a raw ZCL reset device command to a Zigbee device to reset it.

    The raw command contains the frame control, sequence number, command, 
    and payload required for the ZCL reset device command. It is sent directly
    without additional ZCL framing.

    Args:
     nwkid: The network ID of the device to reset.
     epin: The endpoint ID to send the command from. 
     epout: The endpoint ID to send the command to.

    Returns: 
     The sequence number used in the command.
    """
    
    self.log.logging("zclCommand", "Debug", "zcl_raw_reset_device %s" % nwkid)
    frame_control_field = "%02x" %0b0001_0001
    cmd = "00"
    cluster = "0000"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = frame_control_field + sqn + cmd
    zcl_command_formated_logging( self, "Reset Device (Raw)", nwkid, epout, sqn, cluster)
    raw_APS_request(self, nwkid, epout, cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=epin, ackIsDisabled=False)
    return sqn


# Read Attributes Command
def rawaps_read_attribute_req(self, nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, Attr, ackIsDisabled=DEFAULT_ACK_MODE, groupaddrmode=False):
    self.log.logging("zclCommand", "Debug", "rawaps_read_attribute_req %s %s %s %s %s %s %s %s" % (nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, Attr))
    zcl_command_formated_logging( self, "Read_Attribute_Req (Raw)", nwkid, EpOut, Cluster, direction, manufacturer_spec, manufacturer, Attr, ackIsDisabled, groupaddrmode)

    cmd = "00"  # Read Attribute Command Identifier

    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x00)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #

    cluster_frame = 0b00010000
    if manufacturer_spec == "01":
        cluster_frame += 0b00000100

    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = fcf
    if manufacturer_spec == "01":
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(manufacturer, 16)))[0]
    payload += sqn + cmd
    idx = 0
    while idx < len(Attr):
        attribute = Attr[idx : idx + 4]
        idx += 4
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(attribute, 16)))[0]
    if not groupaddrmode:
        raw_APS_request(self, nwkid, EpOut, Cluster, "0104", payload, zigate_ep=EpIn, ackIsDisabled=ackIsDisabled)
    else:
        raw_APS_request(self, nwkid, EpOut, Cluster, "0104", payload, zigate_ep=EpIn, groupaddrmode=True, ackIsDisabled=ackIsDisabled)
        
    return sqn


# Write Attributes
def rawaps_write_attribute_req(self, nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "rawaps_write_attribute_req %s %s %s %s %s %s %s %s %s" % (nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data))
    zcl_command_formated_logging( self, "Write_Attribute_Req (Raw)", nwkid, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled)
    
    cmd = "02"

    cluster_frame = 0b00010000  # The frame type sub-field SHALL be set to indicate a global command (0b00)
    if (
        manuf_spec == "01"
    ):  # The manufacturer specific sub-field SHALL be set to 0 if this command is being used to Write Attributes defined for any cluster in the ZCL or 1 if this command is being used to write manufacturer specific attributes
        cluster_frame += 0b00000100
    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = fcf
    if manuf_spec == "01":
        payload += "%04x" %struct.unpack(">H", struct.pack("H", int(manuf_id, 16)))[0]
    payload += sqn + cmd
    payload += "%04x" % struct.unpack(">H", struct.pack("H", int(attribute, 16)))[0]  # Attribute Id
    payload += data_type  # Attribute Data Type
    if data_type not in ( "41", "42"):
        payload += decode_endian_data(data, data_type)
    else:
        payload += data
    self.log.logging("zclCommand", "Debug", "rawaps_write_attribute_req ==== payload: %s" % (payload))

    raw_APS_request(self, nwkid, EPout, cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=EPin, ackIsDisabled=ackIsDisabled)
    return sqn


# Write Attributes No Response
def zcl_raw_write_attributeNoResponse(self, nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "zcl_raw_write_attributeNoResponse %s %s %s %s %s %s %s %s %s" % (nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data))
    zcl_command_formated_logging( self, "Write_Attribute_No_Response (Raw)", nwkid, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled)

    cmd = "05"

    cluster_frame = 0b00010000  # The frame type sub-field SHALL be set to indicate a global command (0b00)
    if (
        manuf_spec == "01"
    ):  # The manufacturer specific sub-field SHALL be set to 0 if this command is being used to Write Attributes defined for any cluster in the ZCL or 1 if this command is being used to write manufacturer specific attributes
        cluster_frame += 0b00000100
    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = fcf
    if manuf_spec == "01":
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(manuf_id, 16)))[0]
    payload += sqn + cmd
    payload += "%04x" % struct.unpack(">H", struct.pack("H", int(attribute, 16)))[0]  # Attribute Id
    payload += data_type  # Attribute Data Type
    if data_type not in ( "41", "42"):
            payload += decode_endian_data(data, data_type)
    else:
        payload += data
    
    self.log.logging("zclCommand", "Debug", "rawaps_write_attribute_req ==== payload: %s" % (payload))

    raw_APS_request(self, nwkid, EPout, cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=EPin, ackIsDisabled=ackIsDisabled)
    return sqn
    
def zcl_raw_default_response( self, nwkid, EPin, EPout, cluster, response_to_command, sqn, command_status="00", manufcode=None, orig_fcf=None):
    self.log.logging("zclCommand", "Debug", f"zcl_raw_default_response {nwkid} {EPin} {EPout} {cluster} {sqn} for command {response_to_command} with Status: {command_status}, Manufcode: {manufcode}, OrigFCF: {orig_fcf}")

    if "disableZCLDefaultResponse" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["disableZCLDefaultResponse"]:
        return
    zcl_command_formated_logging( self, "Default_Response (Raw)", nwkid, EPout, cluster, response_to_command, sqn, command_status, manufcode, orig_fcf)
    
    if response_to_command == "0b":
        # Never return a default response to a default response
        return
    cmd = "0b"
    if orig_fcf is None:
        frame_control_field = "%02x" %0b00000000  # The frame type sub-field SHALL be set to indicate a global command (0b00)
    else:
        # The frame control field SHALL be specified as follows. The frame type sub-field SHALL be set to indicate
        # a global command (0b00). The manufacturer specific sub-field SHALL be set to 0 if this command is being
        # sent in response to a command defined for any cluster in the ZCL or 1 if this command is being sent in
        # response to a manufacturer specific command.
        zcl_frame_type = "0"
        zcl_manuf_specific = "1" if (manufcode and manufcode != "0000") else "0"
        zcl_target_direction = "%02x" %( not fcf_direction( orig_fcf ))
        zcl_disabled_default = "1"
        frame_control_field = build_fcf(zcl_frame_type, zcl_manuf_specific, zcl_target_direction, zcl_disabled_default)
    
    payload = frame_control_field 
    if manufcode and manufcode != "0000":
        payload += manufcode[2:4] + manufcode[:2]
    payload += sqn + cmd + response_to_command + command_status
    self.log.logging("zclCommand", "Debug", f"zcl_raw_default_response ==== payload: {payload}")

    raw_APS_request(self, nwkid, EPout, cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=EPin, highpriority=True, ackIsDisabled=is_ack_tobe_disabled(self, nwkid))
    return sqn
    
    
# Configure Reporting
def zcl_raw_configure_reporting_requestv2(self, nwkid, epin, epout, cluster, direction, manufacturer_spec, manufacturer, attribute_reporting_configuration, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "zcl_raw_configure_reporting_requestv2 %s %s %s %s %s %s %s %s" % (nwkid, epin, epout, cluster, direction, manufacturer_spec, manufacturer, attribute_reporting_configuration))
    zcl_command_formated_logging( self, "Configure_Reporting_Req (Raw)", nwkid, epout, cluster, direction, manufacturer_spec, manufacturer, attribute_reporting_configuration, ackIsDisabled)

    cmd = "06"  # Configure Reporting Command Identifier

    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x00)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #

    cluster_frame = 0b00010000
    if manufacturer_spec == "01":
        cluster_frame += 0b00000100

    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = fcf
    if manufacturer_spec == "01":
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(manufacturer, 16)))[0]
    payload += sqn + cmd

    self.log.logging("zclCommand", "Debug", "zcl_raw_configure_reporting_requestv2  payload: %s" % payload)
    for x in attribute_reporting_configuration:
        self.log.logging("zclCommand", "Debug", "zcl_configure_reporting_requestv2 record: %s" % str(x))
        payload += direction
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(x["Attribute"], 16)))[0]
        payload += x["DataType"]
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(x["minInter"], 16)))[0]
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(x["maxInter"], 16)))[0]
        if "rptChg" in x:
            payload += decode_endian_data(x["rptChg"], x["DataType"])

    # payload +=  "%04x" % struct.unpack(">H", struct.pack("H",int(x['timeOut'],16)))[0]
    self.log.logging("zclCommand", "Debug", "zcl_raw_configure_reporting_requestv2  payload: %s" % payload)

    raw_APS_request(self, nwkid, epout, cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=epin, ackIsDisabled=ackIsDisabled)
    return sqn

def zcl_raw_read_report_config_request(self,nwkid, epin, epout, cluster, manuf_specific, manuf_code, attribute_list, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "zcl_raw_read_report_config_request %s %s %s %s %s %s %s" % (
        nwkid, epin, epout, cluster, manuf_specific, manuf_code, attribute_list))
    zcl_command_formated_logging( self, "Read_Report_Configure_Req (Raw)", nwkid, epout, cluster, manuf_specific, manuf_code, attribute_list, ackIsDisabled)

    cmd = "08"  # 
    cluster_frame = 0b00000000
    if manuf_specific == "01":
        cluster_frame += 0b00000100

    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    if attribute_list:
        payload = fcf
        if manuf_specific == "01":
            payload += "%04x" % struct.unpack(">H", struct.pack("H", int(manuf_code, 16)))[0]
        payload += sqn + cmd

        for attribute in attribute_list:
            payload += "00" + "%04x" % struct.unpack(">H", struct.pack("H", attribute))[0]

        raw_APS_request(self, nwkid, epout, cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=epin, ackIsDisabled=ackIsDisabled)
    return sqn

# Discover Attributes
def zcl_raw_attribute_discovery_request(self, nwkid, epin, epout, cluster, start_attribute, manuf_specific, manuf_code, ackIsDisabled):
    
    self.log.logging("zclCommand", "Debug", "zcl_raw_attribute_discovery_request %s %s %s %s %s %s %s" % (
        nwkid, epin, epout, cluster, manuf_specific, manuf_code, start_attribute))
    zcl_command_formated_logging( self, "Attribute_Discovery_Req (Raw)", nwkid, epout, cluster, start_attribute, manuf_specific, manuf_code, ackIsDisabled)

    cmd = "0c"  # 
    cluster_frame = 0b00
    if manuf_specific == "01":
        cluster_frame += 0b00000100
    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = fcf
    if manuf_specific == "01":
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(manuf_code, 16)))[0]
    payload += sqn + cmd
    # Start attribute
    payload += "%04x" % struct.unpack(">H", struct.pack("H", int(start_attribute, 16)))[0]
    
    # nb Attribute
    payload += "%02x" %0xff
    
    self.log.logging("zclCommand", "Debug", "zcl_raw_attribute_discovery_request  payload: %s" % payload)

    raw_APS_request(self, nwkid, epout, cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=epin, ackIsDisabled=ackIsDisabled)

    
# Cluster 0003: Identify

def zcl_raw_identify(self, nwkid, epin, epout, command, identify_time=None, identify_effect=None, identify_variant=None, groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):

    self.log.logging("zclCommand", "Debug", "zcl_raw_identify %s %s %s %s %s %s %s %s %s" % (nwkid, epin, epout, command, identify_time, identify_effect, identify_variant, groupaddrmode, ackIsDisabled))
    zcl_command_formated_logging( self, "Identify_Send (Raw)", nwkid, epout, "0003", command, identify_time, identify_effect, identify_variant, groupaddrmode, ackIsDisabled)

    IDENTIFY_COMMAND = {
        "Identify": 0x00,
        "IdentifyQuery": 0x01,
        "TriggerEffect": 0x40
    }
    
    Cluster = "0003"
    
    if command not in IDENTIFY_COMMAND:
        return
    if command == 'Identify' and identify_time is None:
        return
    if command == 'TriggerEffect' and identify_effect is None and identify_variant is None:
        return
    
    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x01)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #
    cluster_frame = 0b00010001
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + "%02x" % IDENTIFY_COMMAND[command] 
    
    if command == 'Identify' and identify_time:
        payload += identify_time
    elif command == 'TriggerEffect' and identify_effect and identify_variant:
        payload += identify_effect + identify_variant

    raw_APS_request(self, nwkid, epout, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=epin, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)
    return sqn
    
    
# Cluster 0004: Groups

def zcl_raw_add_group_membership(self, nwkid, epin, epout, GrpId, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "zcl_raw_add_group_membership %s %s %s %s" % (nwkid, epin, epout, GrpId))
    zcl_command_formated_logging( self, "Add_Group_Membership (Raw)", nwkid, epout, "0004", GrpId, ackIsDisabled)
    
    cmd = "00"
    cluster = "0004"
    cluster_frame = 0b00010001
    
    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = fcf
    payload += sqn + cmd + "%04x" % (struct.unpack(">H", struct.pack("H", int(GrpId, 16)))[0]) + "00"
    raw_APS_request(self, nwkid, epout, cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=epin, ackIsDisabled=ackIsDisabled)
    return sqn
    

def zcl_raw_check_group_member_ship(self, nwkid, epin, epout, GrpId, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "zcl_raw_check_group_member_ship %s %s %s %s" % (nwkid, epin, epout, GrpId))
    zcl_command_formated_logging( self, "Check_Group_Membership (Raw)", nwkid, epout, "0004", GrpId, ackIsDisabled)
    
    cmd = "01"
    cluster = "0004"
    cluster_frame = 0b00010001

    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = fcf
    payload += sqn + cmd + "%04x" % (struct.unpack(">H", struct.pack("H", int(GrpId, 16)))[0])
    raw_APS_request(self, nwkid, epout, cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=epin, ackIsDisabled=ackIsDisabled)
    return sqn


def zcl_raw_look_for_group_member_ship(self, nwkid, epin, epout, nbgroup, group_list, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "zcl_raw_look_for_group_member_ship %s %s %s %s %s" % (nwkid, epin, epout, nbgroup, group_list))
    zcl_command_formated_logging( self, "Look_Group_Membership (Raw)", nwkid, epout, "0004", nbgroup, group_list, ackIsDisabled)
    
    cmd = "02"
    cluster = "0004"
    cluster_frame = 0b00010001

    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = fcf
    
    payload += sqn + cmd + nbgroup  

    idx = 0
    while idx < int(nbgroup,16) * 4:
        payload += decode_endian_data( group_list[ idx : idx + 4 ], "21")
        idx += 4

    raw_APS_request(self, nwkid, epout, cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=epin, ackIsDisabled=ackIsDisabled)
    return sqn


def zcl_raw_remove_group_member_ship(self, nwkid, epin, epout, GrpId, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "zcl_raw_remove_group_member_ship %s %s %s %s" % (nwkid, epin, epout, GrpId))
    zcl_command_formated_logging( self, "Remove_Group_Membership (Raw)", nwkid, epout, "0004", GrpId, ackIsDisabled)
    
    cmd = "03"
    cluster = "0004"
    cluster_frame = 0b00010001

    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = fcf
    payload += sqn + cmd + "%04x" % (struct.unpack(">H", struct.pack("H", int(GrpId, 16)))[0])
    raw_APS_request(self, nwkid, epout, cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=epin, ackIsDisabled=ackIsDisabled)
    return sqn


def zcl_raw_remove_all_groups(self, nwkid, epin, epout, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "zcl_raw_remove_group_member_ship %s %s %s" % (nwkid, epin, epout))
    zcl_command_formated_logging( self, "Remove_All_Group_Membership (Raw)", nwkid, epout, "0004", ackIsDisabled)
    
    cmd = "05"
    cluster = "0004"
    cluster_frame = 0b00010001

    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = fcf
    payload += sqn + cmd
    raw_APS_request(self, nwkid, epout, cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=epin, ackIsDisabled=ackIsDisabled)
    return sqn


def zcl_raw_send_group_member_ship_identify(self, nwkid, epin, epout, GrpId, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "zcl_raw_send_group_member_ship_identify %s %s %s %s" % (nwkid, epin, epout, GrpId))
    zcl_command_formated_logging( self, "Send_Group_Membership_Identify (Raw)", nwkid, epout, "0004", GrpId, ackIsDisabled)

    cmd = "06"
    cluster = "0004"
    cluster_frame = 0b00010001

    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = fcf
    payload += sqn + cmd + "%04x" % (struct.unpack(">H", struct.pack("H", int(GrpId, 16)))[0])
    raw_APS_request(self, nwkid, epout, cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=epin, ackIsDisabled=ackIsDisabled)
    return sqn



# Cluster 0006: On/Off
######################
def raw_zcl_zcl_onoff(self, nwkid, EPIn, EpOut, command, effect=None, groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "raw_zcl_zcl_onoff %s %s %s %s %s %s" % (nwkid, EPIn, EpOut, command, effect, groupaddrmode))
    zcl_command_formated_logging( self, "On/Off (Raw)", nwkid, EpOut, "0006", command, effect, groupaddrmode, ackIsDisabled)

    Cluster = "0006"
    ONOFF_COMMANDS = {
        "Off": 0x00,
        "On": 0x01,
        "Toggle": 0x02,
        "OffWithEffect": 0x40,
        "OnWithRecallGlobalScene": 0x41,
        "OnWithTimedOff": 0x42,
    }
    if command not in ONOFF_COMMANDS:
        return

    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x01)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #
    cluster_frame = 0b00010001

    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + "%02x" % ONOFF_COMMANDS[command] 
    if command == "OffWithEffect":
        # Effect is a 2 uint8, so there is no need to convert to little indian
        payload += effect
    
    raw_APS_request(self, nwkid, EpOut, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=EPIn, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)
    return sqn


# Cluster 0008: Level Control
#############################


def zcl_raw_level_move_to_level(self, nwkid, EPIn, EPout, command, level="00", move_mode="00", rate="FF", step_mode="00", step_size="01", transition="0010", groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "zcl_raw_level_move_to_level %s %s %s %s %s %s %s %s %s %s" % (nwkid, EPIn, EPout, command, level, move_mode, rate, step_mode, step_size, transition))
    zcl_command_formated_logging( self, "Level (Raw)", nwkid, EPout, "0008", command, level, move_mode, rate, step_mode, step_size, transition, groupaddrmode, ackIsDisabled)

    Cluster = "0008"
    LEVEL_COMMANDS = {"MovetoLevel": 0x00, "Move": 0x01, "Step": 0x02, "Stop": 0x03, "MovetoLevelWithOnOff": 0x04, "MoveWithOnOff": 0x05, "StepWithOnOff": 0x06, "Stop2": 0x07}
    if command not in LEVEL_COMMANDS:
        return

    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x01)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #
    cluster_frame = 0b00010001 

    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + "%02x" % LEVEL_COMMANDS[command]
    if command in ("MovetoLevel", "MovetoLevelWithOnOff"):
        payload += level + "%04x" % (struct.unpack(">H", struct.pack("H", int(transition, 16)))[0])
    elif command == ("Move", "MoveWithOnOff"):
        payload += move_mode + rate
    elif command == ("Step", "StepWithOnOff"):
        payload += step_mode + step_size + "%04x" % (struct.unpack(">H", struct.pack("H", int(transition, 16)))[0])

    raw_APS_request(self, nwkid, EPout, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=EPIn, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)
    return sqn


# Cluster 0019: OTA

# All OTA Upgrade cluster commands SHALL be sent with APS retry option, hence, require APS acknowledgement; unless stated otherwise.

# OTA Upgrade cluster commands, the frame control value SHALL follow the description below:
# Frame type is 0x01: 
#   commands are cluster specific (not a global command). Manufacturer specific is 0x00: commands are not manufacturer specific.
# Direction: 
#   SHALL be either 0x00 (client->server) or 0x01 (server->client) depending on the com- mands.
# Disable default response is 0x00 
#   for all OTA request commands sent from client to server: 
#   default re- sponse command SHALL be sent when the server receives OTA Upgrade cluster request commands that 
#   it does not support or in case an error case happens. A detailed explanation of each error case along with 
#   its recommended action is described for each OTA cluster command.
# Disable default response is 0x01
#   for all OTA response commands (sent from server to client) and for 
#   broadcast/multicast Image Notify command: default response command is not sent when the client re- ceives 
#   a valid OTA Upgrade cluster response commands or when it receives broadcast or multicast Im- age Notify command. 
#   However, if a client receives invalid OTA Upgrade cluster response command, a default response SHALL be sent. 
#   A detailed explanation of each error case along with its recom- mended action is described for each OTA cluster command.


def zcl_raw_ota_image_notify(self, nwkid, EPIn, EPout, PayloadType, QueryJitter, ManufCode, Imagetype, FileVersion ):
    # 505
    self.log.logging("zclCommand", "Debug", "zcl_raw_ota_image_notify %s %s %s %s %s %s %s %s" % (nwkid, EPIn, EPout, PayloadType, QueryJitter, ManufCode, Imagetype, FileVersion))
    zcl_command_formated_logging( self, "OTA_Image_Notify (Raw)", nwkid, EPout, "0019", PayloadType, QueryJitter, ManufCode, Imagetype, FileVersion)

    cluster_frame = 0b00001001    # Cluster Specific / Server to Client / disable Default Response
    Command = "00"
    ManufCode = "%04x" % (struct.unpack(">H", struct.pack("H", int(ManufCode, 16)))[0])
    Imagetype = "%04x" % (struct.unpack(">H", struct.pack("H", int(Imagetype, 16)))[0])
    FileVersion = "%08x" % struct.unpack(">I", struct.pack("I", int(FileVersion, 16)))[0]
    
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + Command + PayloadType + QueryJitter + ManufCode + Imagetype + FileVersion
    raw_APS_request(self, nwkid, EPout, "0019", "0104", payload, zigpyzqn=sqn, zigate_ep=EPIn, ackIsDisabled=False)
    return sqn

def zcl_raw_ota_query_next_image_response(self, sqn, nwkid, EPIn, EPout, status, ManufCode=None, Imagetype=None, FileVersion=None, imagesize=None ):
    self.log.logging("zclCommand", "Debug", "zcl_raw_ota_query_next_image_response %s %s %s %s %s %s %s %s" % (nwkid, EPIn, EPout, status, ManufCode, Imagetype, FileVersion, imagesize))
    zcl_command_formated_logging( self, "OTA_Query_Next_Image_Resp (Raw)", nwkid, EPout, "0019", status, ManufCode, Imagetype, FileVersion, imagesize)
    
    Command = "02"
    cluster_frame = 0b00011001    # Cluster Specific / Server to Client / With Default Response
    payload = "%02x" % cluster_frame + sqn + Command + status
    if status == "00":
        ManufCode = "%04x" % (struct.unpack(">H", struct.pack("H", int(ManufCode, 16)))[0])
        Imagetype = "%04x" % (struct.unpack(">H", struct.pack("H", int(Imagetype, 16)))[0])
        FileVersion = "%08x" % struct.unpack(">I", struct.pack("I", int(FileVersion, 16)))[0]
        imagesize = "%08x" % struct.unpack(">I", struct.pack("I", int(imagesize, 16)))[0]
    
        payload += ManufCode + Imagetype + FileVersion + imagesize
    raw_APS_request(self, nwkid, EPout, "0019", "0104", payload, zigpyzqn=sqn, zigate_ep=EPIn, ackIsDisabled=False)
    return sqn

def zcl_raw_ota_image_block_response_success(self, sqn, nwkid, EPIn, EPout, status, ManufCode, Imagetype, FileVersion, fileoffset, datasize, imagedata , ackIsDisabled=False):
    self.log.logging("zclCommand", "Debug", "zcl_raw_ota_image_block_response_success %s %s %s %s %s %s %s %s %s %s" % (nwkid, EPIn, EPout, status, ManufCode, Imagetype, FileVersion, fileoffset, datasize, len(imagedata)))
    zcl_command_formated_logging( self, "OTA_Image_Block_Response_Success (Raw)", nwkid, EPout, "0019", status, ManufCode, Imagetype, FileVersion, fileoffset, datasize, imagedata , ackIsDisabled)
    
    # "0502"
    Command = "05"
    cluster_frame = 0b00011001    # Cluster Specific / Server to Client / With Default Response
    ManufCode = "%04x" % (struct.unpack(">H", struct.pack("H", int(ManufCode, 16)))[0])
    Imagetype = "%04x" % (struct.unpack(">H", struct.pack("H", int(Imagetype, 16)))[0])
    FileVersion = "%08x" % struct.unpack(">I", struct.pack("I", int(FileVersion, 16)))[0]
    fileoffset = "%08x" % struct.unpack(">I", struct.pack("I", int(fileoffset, 16)))[0]

    payload = "%02x" % cluster_frame + sqn + Command + status + ManufCode + Imagetype + FileVersion + fileoffset + datasize + imagedata
    raw_APS_request(self, nwkid, EPout, "0019", "0104", payload, zigpyzqn=sqn, zigate_ep=EPIn, ackIsDisabled=ackIsDisabled)
    return sqn

def zcl_raw_ota_image_block_response_wait_for_data( self, nwkid, EPIn, EPout, waitforstatus, currenttime, requesttime, minblockperiod):
    zcl_command_formated_logging( self, "OTA_Image_Block_Response_Wait_for_Data (Raw)", nwkid, EPout, "0019", waitforstatus, currenttime, requesttime, minblockperiod)
    
    Command = "05"
    cluster_frame = 0b00011001    # Cluster Specific / Server to Client / With Default Response
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + Command + waitforstatus + currenttime + requesttime + minblockperiod
    raw_APS_request(self, nwkid, EPout, "0019", "0104", payload, zigpyzqn=sqn, zigate_ep=EPIn, ackIsDisabled=False)
    return sqn

def zcl_raw_ota_image_block_response_abort(self, nwkid, EPIn, EPout, abortstatus):
    zcl_command_formated_logging( self, "OTA_Image_Block_Response_Abort (Raw)", nwkid, EPout, "0019", abortstatus)
    
    Command = "05"
    cluster_frame = 0b00011001    # Cluster Specific / Server to Client / With Default Response
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + Command + abortstatus
    raw_APS_request(self, nwkid, EPout, "0019", "0104", payload, zigpyzqn=sqn, zigate_ep=EPIn, ackIsDisabled=False)
    return sqn   
                                             
def zcl_raw_ota_upgrade_end_response(self, sqn, nwkid, EPIn, EPout, ManufCode, Imagetype, FileVersion, currenttime, upgradetime):
    # "0504"
    self.log.logging("zclCommand", "Debug", "zcl_raw_ota_upgrade_end_response %s %s %s %s %s %s %s %s" % (nwkid, EPIn, EPout, ManufCode, Imagetype, FileVersion, currenttime, upgradetime))
    zcl_command_formated_logging( self, "OTA_Upgrade_End_Response (Raw)", nwkid, EPout, "0019", ManufCode, Imagetype, FileVersion, currenttime, upgradetime)
    
    Command = "07"
    cluster_frame = 0b00011001   # Cluster Specific / Server to Client / With Default Response
    ManufCode = "%04x" % (struct.unpack(">H", struct.pack("H", int(ManufCode, 16)))[0])
    Imagetype = "%04x" % (struct.unpack(">H", struct.pack("H", int(Imagetype, 16)))[0])
    FileVersion = "%08x" % struct.unpack(">I", struct.pack("I", int(FileVersion, 16)))[0]
    currenttime = "%08x" % struct.unpack(">I", struct.pack("I", int(currenttime, 16)))[0]
    upgradetime = "%08x" % struct.unpack(">I", struct.pack("I", int(upgradetime, 16)))[0]

    payload = "%02x" % cluster_frame + sqn + Command + ManufCode + Imagetype + FileVersion + currenttime + upgradetime
    raw_APS_request(self, nwkid, EPout, "0019", "0104", payload, zigpyzqn=sqn, zigate_ep=EPIn, ackIsDisabled=False)
    return sqn

def zcl_raw_ota_query_device_specific_file_response(self, nwkid, EPIn, EPout, status, ManufCode, Imagetype, FileVersion, imagesize):
    zcl_command_formated_logging( self, "OTA_Query_Device_Specific_File_Response (Raw)", nwkid, EPout, "0019", status, ManufCode, Imagetype, FileVersion, imagesize)
    
    Command = "09"
    ManufCode = "%04x" % (struct.unpack(">H", struct.pack("H", int(ManufCode, 16)))[0])
    Imagetype = "%04x" % (struct.unpack(">H", struct.pack("H", int(Imagetype, 16)))[0])
    FileVersion = "%08x" % struct.unpack(">I", struct.pack("I", int(FileVersion, 16)))[0]
    imagesize = "%08x" % struct.unpack(">I", struct.pack("I", int(imagesize, 16)))[0]

    cluster_frame = 0b00011001    # Cluster Specific / Server to Client / With Default Response
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + Command + status + ManufCode + Imagetype + FileVersion +imagesize
    raw_APS_request(self, nwkid, EPout, "0019", "0104", payload, zigpyzqn=sqn, zigate_ep=EPIn, ackIsDisabled=False)
    return sqn

# Cluster 0102: Window Covering
################################


def zcl_raw_window_covering(self, nwkid, EPIn, EPout, command, level="00", percentage="00", groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "zcl_raw_window_covering %s %s %s %s %s" % (nwkid, EPout, command, level, percentage))
    zcl_command_formated_logging( self, "Window_Covering (Raw)", nwkid, EPout, "0102", command, level, percentage, groupaddrmode, ackIsDisabled)

    Cluster = "0102"
    WINDOW_COVERING_COMMANDS = {"Up": 0x00, "Down": 0x01, "Stop": 0x02, "GoToLiftValue": 0x04, "GoToLiftPercentage": 0x05, "GoToTiltValue": 0x07, "GoToTiltPercentage": 0x08}
    if command not in WINDOW_COVERING_COMMANDS:
        self.log.logging("zclCommand", "Error", "zcl_raw_window_covering UNKNOW COMMAND drop it %s %s %s %s %s" % (nwkid, EPout, command, level, percentage))
        return

    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x01)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #
    cluster_frame = 0b00010001

    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + "%02x" % WINDOW_COVERING_COMMANDS[command]
    if command in ( "GoToLiftValue", "GoToTiltValue"):
        payload += level
    elif command in ( "GoToLiftPercentage", "GoToTiltPercentage"):
        payload += percentage

    self.log.logging("zclCommand", "Debug", "zcl_raw_window_covering payload %s %s" % (nwkid, payload))
    raw_APS_request(self, nwkid, EPout, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=EPIn, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)
    return sqn


# Cluster 0300: Color


def zcl_raw_move_color(self, nwkid, EPIn, EPout, command, temperature=None, hue=None, saturation=None, colorX=None, colorY=None, transition="0010", groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):

    self.log.logging("zclCommand", "Debug", "zcl_raw_move_color %s %s %s %s %s %s %s %s %s %s %s" % (nwkid, EPIn, EPout, command, temperature, hue, saturation, colorX, colorY, transition, ackIsDisabled))
    zcl_command_formated_logging( self, "Move_Color (Raw)", nwkid, EPout, "0300", command, temperature, hue, saturation, colorX, colorY, transition, groupaddrmode, ackIsDisabled)

    COLOR_COMMANDS = {
        # "MovetoHue": 0x00,
        # "MoveHue": 0x01,
        # "StepHue": 0x02,
        # "MovetoSaturation": 0x03,
        # "MoveSaturation": 0x04,
        # "StepSaturation": 0x05,
        "MovetoHueandSaturation": 0x06,  # zcl_move_hue_and_saturation(self, nwkid, EPout, hue, saturation, transition="0010", ackIsDisabled=DEFAULT_ACK_MODE)
        "MovetoColor": 0x07,  # zcl_move_to_colour(self, nwkid, EPout, colorX, colorY, transition="0010", ackIsDisabled=DEFAULT_ACK_MODE)
        # "MoveColor": 0x08,
        # "StepColor": 0x09,
        "MovetoColorTemperature": 0x0A,  # zcl_move_to_colour_temperature( self, nwkid, EPout, temperature, transition="0010", ackIsDisabled=DEFAULT_ACK_MODE)
        # "EnhancedMovetoHue": 0x40,
        # "EnhancedMoveHue": 0x41,
        # "EnhancedStepHue": 0x42,
        # "EnhancedMovetoHueandSaturation": 0x43,
        # "ColorLoopSet": 0x44,
        # "StopMoveStep": 0x47,
        # "MoveCOlorTemperature": 0x4b,
        # "StepColorTemperature": 0x4c
    }

    Cluster = "0300"
    if command not in COLOR_COMMANDS:
        self.log.logging("zclCommand", "Debug", "zcl_raw_move_color command %s not implemented yet!!" % command)
        return

    cluster_frame = 0b00010001
    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    payload = "%02x" % cluster_frame + sqn + "%02x" % COLOR_COMMANDS[command]

    if command == "MovetoHueandSaturation" and hue and saturation:
        payload += hue
        payload += saturation
        payload += "%04x" % (struct.unpack(">H", struct.pack("H", int(transition, 16)))[0])

    elif command == "MovetoColor" and colorX and colorY:
        payload += "%04x" % (struct.unpack(">H", struct.pack("H", int(colorX, 16)))[0])
        payload += "%04x" % (struct.unpack(">H", struct.pack("H", int(colorY, 16)))[0])
        payload += "%04x" % (struct.unpack(">H", struct.pack("H", int(transition, 16)))[0])

    elif command == "MovetoColorTemperature" and temperature:
        payload += "%04x" % (struct.unpack(">H", struct.pack("H", int(temperature, 16)))[0])
        payload += "%04x" % (struct.unpack(">H", struct.pack("H", int(transition, 16)))[0])

    raw_APS_request(self, nwkid, EPout, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=EPIn, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)
    return sqn


# Cluster 0500: IAS

# Cluster 0500 ( 0x0400 )


def zcl_raw_ias_zone_enroll_response(self, nwkid, EPin, EPout, response_code, zone_id, sqn, groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "zcl_raw_ias_zone_enroll_response %s %s %s %s %s %s" % (nwkid, EPin, EPout, response_code, zone_id, sqn))
    zcl_command_formated_logging( self, "IAS_Enroll_Response (Raw)", nwkid, EPout, "0500", response_code, zone_id, sqn, groupaddrmode, ackIsDisabled)
    
    Cluster = "0500"
    cmd = "00"
    cluster_frame = 0b00010001
    if sqn is None:
        sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + cmd + response_code + zone_id
    raw_APS_request(self, nwkid, EPout, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=EPin, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)
    return sqn


def zcl_raw_ias_initiate_normal_operation_mode(self, nwkid, EPin, EPout, groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):
    zcl_command_formated_logging( self, "IAS_Initiate_Normal_Operation_Mode (Raw)", nwkid, EPout, "0500", groupaddrmode, ackIsDisabled)

    cmd = "01"
    Cluster = "0500"
    cluster_frame = 0b00010001
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + cmd
    raw_APS_request(self, nwkid, EPout, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=EPin, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)
    return sqn


def zcl_raw_ias_initiate_test_mode(self, nwkid, EPin, EPout, duration="01", current_zone_sensitivy_level="01", groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):
    zcl_command_formated_logging( self, "IAS_Initiate_Test_Mode (Raw)", nwkid, EPout, "0500", duration, current_zone_sensitivy_level, groupaddrmode, ackIsDisabled)

    cmd = "02"
    Cluster = "0500"
    cluster_frame = 0b00010001
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + cmd + duration + current_zone_sensitivy_level
    raw_APS_request(self, nwkid, EPout, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=EPin, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)
    return sqn


# Cluster 0501 IAS ACE ( 0x0111, 0x0112)


IAS_ACE_COMMANDS = {
    "Arm": 0x00,
    #'Bypass': 0x01,
    #'Emergency': 0x02,
    #'Fire': 0x03,
    #'Panic': 0x04,
    #'GetZoneID Map': 0x05,
    #'GetZoneInformation': 0x06,
    #'GetPanelStatus': 0x07,
    #'GetBypassedZoneList': 0x08,
    #'GetZoneStatus': 0x09
}


def zcl_raw_ias_ace_commands_arm(self, EPin, EPout, nwkid, arm_mode, arm_code, zone_id, groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):
    zcl_command_formated_logging( self, "IAS_ACE (Raw)", nwkid, EPout, "0501", arm_mode, arm_code, zone_id, groupaddrmode, ackIsDisabled)

    cmd = IAS_ACE_COMMANDS["Arm"]
    Cluster = "0501"
    cluster_frame = 0b00010001
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    payload = "%02x" % cluster_frame + sqn + cmd + "%02x" % arm_mode + "%02x" % arm_code + "%02x" % zone_id
    raw_APS_request(self, nwkid, EPout, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=EPin, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)
    return sqn


# Cluster 0502 IAS WD

IAS_WD_COMMANDS = {"StartWarning": "00", "Squawk": "01"}


def zcl_raw_ias_wd_command_start_warning(self, EPin, EPout, nwkid, warning_mode=0x00, strobe_mode=0x01, siren_level=0x01, warning_duration=0x0001, strobe_duty=0x00, strobe_level=0x00, groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "zcl_raw_ias_wd_command_start_warning %s %s %s %s %s %s %s" % (nwkid, warning_mode, strobe_mode, siren_level, warning_duration, strobe_duty, strobe_level))
    zcl_command_formated_logging( self, "IAS_Start_Warning (Raw)", nwkid, EPout, "0502", warning_mode, strobe_mode, siren_level, warning_duration, strobe_duty, strobe_level, groupaddrmode, ackIsDisabled)

    cmd = IAS_WD_COMMANDS["StartWarning"]
    Cluster = "0502"
    cluster_frame = 0b00010001
    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    if warning_mode == strobe_mode == 0x00:
        warning_duration = 0x00
    # Warnindg mode , Strobe, Sirene Level
    #field1 = 0x00
    #field1 = field1 & 0xF0 | (warning_mode << 4)           # bit 8-4 Warning Mode
    #field1 = field1 & 0xF7 | ((strobe_mode & 0x01) << 2)   # bit 3-2 Strobe 
    #field1 = field1 & 0xFC | (siren_level & 0x03)          # bit 1-0 Siren Level 

    payload = "%02x" % cluster_frame + sqn + cmd
    payload += "%02x" % startwarning_payload(self, nwkid, warning_mode, strobe_mode, siren_level) + "%04x" % struct.unpack(">H", struct.pack("H", warning_duration))[0] + "%02x" % (strobe_duty) + "%02x" % (strobe_level)
    raw_APS_request(self, nwkid, EPout, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=EPin, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)
    return sqn

def startwarning_payload(self, nwkid, warning_mode, strobe_mode, siren_level):
    
    if "Model" not in self.ListOfDevices[nwkid] or self.ListOfDevices[nwkid]["Model"] not in ('SIRZB-110', 'SRAC-23B-ZBSR', 'AV201029A', 'AV201024A'):
        return (warning_mode << 4) + (strobe_mode << 2) + siren_level
    if strobe_mode and not warning_mode:
        return (warning_mode << 4) + (strobe_mode << 2) + siren_level
    return warning_mode + ( (strobe_mode) << 4) + (siren_level << 6)

def zcl_raw_ias_wd_command_squawk(self, EPin, EPout, nwkid, squawk_mode, strobe, squawk_level, groupaddrmode=False, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging("zclCommand", "Debug", "zcl_raw_ias_wd_command_squawk %s %s %s %s" % (nwkid, squawk_mode, strobe, squawk_level))
    zcl_command_formated_logging( self, "IAS_Sqawk (Raw)", nwkid, EPout, "0502", squawk_mode, strobe, squawk_level, groupaddrmode, ackIsDisabled)

    cmd = IAS_WD_COMMANDS["Squawk"]
    Cluster = "0502"
    cluster_frame = 0b00010001
    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    #field1 = 0x0000
    #field1 = field1 & 0xF0 | (squawk_mode << 4)       # bit 8-4  Squawk mode
    #field1 = field1 & 0xF7 | ((strobe & 0x01) << 3)   # bit   3  Strobe 
    #field1 = field1 & 0xFC | (squawk_level & 0x03)    # bit   1  Squawk level
    field1 = squawk_payload(self, nwkid,squawk_mode,strobe, squawk_level )
    payload = "%02x" % cluster_frame + sqn + cmd + "%02x" % field1

    self.log.logging("zclCommand", "Debug", "zcl_raw_ias_wd_command_squawk %s payload: %s (field1 %s)" % (nwkid, payload, field1))
    raw_APS_request(self, nwkid, EPout, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=EPin, groupaddrmode=groupaddrmode, ackIsDisabled=ackIsDisabled)
    return sqn

def squawk_payload(self, nwkid,squawk_mode,strobe, squawk_level ):
    
    if "Model" not in self.ListOfDevices[nwkid] or self.ListOfDevices[nwkid]["Model"] not in ('SIRZB-110', 'SRAC-23B-ZBSR', 'AV201029A', 'AV201024A'):
        return (squawk_mode << 4) + (strobe << 3) + squawk_level
    return (squawk_mode) + (strobe << 4) + (squawk_level << 6)


# 

def zcl_command_formated_logging( self, command, nwkid, ep, cluster, *args):

    if not self.pluginconf.pluginConf["trackZclClustersOut"]:
        return

    cluster_description = self.readZclClusters[ cluster ]["Description"] if self.readZclClusters and cluster in self.readZclClusters else "Unknown cluster"
    
    formatted_message = "Zcl Command | %s | %s | %s | %s | %s " %(
        command, nwkid, ep, cluster, cluster_description)
    if args:
        for arg in args:
            formatted_message += "| %s" %arg
        
    self.log.logging( "zclCommand", "Log", formatted_message)
