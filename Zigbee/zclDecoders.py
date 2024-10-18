# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#


import struct
from distutils.command.build import build
from os import stat

from Modules.tools import (is_direction_to_client, is_direction_to_server,
                           retreive_cmd_payload_from_8002)
from Modules.zigateConsts import (SIZE_DATA_TYPE, ZIGATE_EP, composite_value,
                                  discrete_value)
from Zigbee.encoder_tools import decode_endian_data, encapsulate_plugin_frame
from Zigbee.zclRawCommands import zcl_raw_default_response


def is_duplicate_zcl_frame(self, Nwkid, ClusterId, Sqn):

    if self.zigbee_communication != "zigpy":
        return False
    if Nwkid not in self.ListOfDevices:
        return False

    if "ZCL-IN-SQN" not in self.ListOfDevices[ Nwkid ]:
        self.ListOfDevices[ Nwkid ]["ZCL-IN-SQN"] = {}
    if ClusterId not in self.ListOfDevices[ Nwkid ]["ZCL-IN-SQN"]:
        self.ListOfDevices[ Nwkid ]["ZCL-IN-SQN"][ ClusterId ] = Sqn
        return False
    if Sqn == self.ListOfDevices[ Nwkid ]["ZCL-IN-SQN"][ ClusterId ]:
        return True
    self.ListOfDevices[ Nwkid ]["ZCL-IN-SQN"][ ClusterId ] = Sqn
    return False
    
def zcl_decoders(self, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Payload, frame):
    # We are receiving an ZCL message

    fcf = Payload[:2]
    default_response_disable, GlobalCommand, Sqn, ManufacturerCode, Command, Data = retreive_cmd_payload_from_8002(Payload)
    if self.zigbee_communication == "zigpy" and not default_response_disable:
        if self.pluginconf.pluginConf["enableZclDuplicatecheck"] and self.zigbee_communication == "zigpy" and is_duplicate_zcl_frame(self, SrcNwkId, ClusterId, Sqn):
            self.log.logging("zclDecoder", "Debug", "zcl_decoders Duplicate frame [%s] %s" %(Sqn, Payload))
            return None

        # Let's answer , Since 7.1.12 zigpy is handling the default response, so no need to do it
        #self.log.logging("zclDecoder", "Debug", "zcl_decoders sending a default response for command %s" %(Command))
        #zcl_raw_default_response( self, SrcNwkId, ZIGATE_EP, SrcEndPoint, ClusterId, Command, Sqn, command_status="00", manufcode=ManufacturerCode, orig_fcf=fcf )

    self.log.logging("zclDecoder", "Debug", "zcl_decoders Zcl.ddr: %s GlobalCommand: %s Sqn: %s ManufCode: %s Command: %s Data: %s Payload: %s" %(
        default_response_disable, GlobalCommand, Sqn, ManufacturerCode, Command, Data, Payload))

    if GlobalCommand:
        return buildframe_foundation_cluster( self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Data )

    if ClusterId == "0003":
        return buildframe_for_cluster_0003(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data )

    if ClusterId == "0004":
        return buildframe_for_cluster_0004(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data )

    if ClusterId == "0005" and Command == "05":  # Only Recall Scene supported
        return buildframe_for_cluster_0005(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data )

    if ClusterId == "0006":
        return buildframe_80x5_message(self, "8095", frame, Sqn, SrcNwkId, SrcEndPoint,TargetEp, ClusterId, ManufacturerCode, Command, Data)

    if ClusterId == "0008":
        return buildframe_80x5_message(self, "8085", frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Command, Data)

    if ClusterId == "0019":
        return buildframe_for_cluster_0019(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)
        
    if ClusterId == "0020":
        return buildframe_for_cluster_0020(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)

    if ClusterId == "0500" and is_direction_to_server(fcf) and Command == "00":
        return buildframe_0400_cmd(self, "0400", frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Command, Data)

    if ClusterId == "0500" and is_direction_to_client(fcf) and Command == "00":
        return buildframe_8401_cmd(self, "8401", frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Command, Data)

    if ClusterId == "0500" and is_direction_to_client(fcf) and Command == "01":
        return buildframe_8400_cmd(self, "8400", frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Command, Data)
    
    if ClusterId == "0501":
        # Handle in inRawAPS
        return frame

    # Do not log a message as this will be handled by the inRawAPS and delegated. (or we don't know those)
    if (
        ClusterId in ( "ef00", "ff00")
        or ( ClusterId == "fc00" and ManufacturerCode == "100b")
        or ( ClusterId == "ffac" and ManufacturerCode == "113c")
        or ( ClusterId == "e001" )  # TS011F Plug does every 24 hours
        ):
        return frame

    self.log.logging( "zclDecoder", "Log", "zcl_decoders Unknown Command: %s NwkId: %s Ep: %s Cluster: %s Payload: %s - GlobalCommand: %s, Sqn: %s, ManufacturerCode: %s" % (
        Command, SrcNwkId, SrcEndPoint, ClusterId, Data, GlobalCommand, Sqn, ManufacturerCode, ), )

    return frame


def buildframe_foundation_cluster( self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Data ):
    self.log.logging("zclDecoder", "Debug", "zcl_decoders Sqn: %s/%s ManufCode: %s Command: %s Data: %s " % (int(Sqn, 16), Sqn, ManufacturerCode, Command, Data))
    if Command == "00":  # Read Attribute
        return buildframe_read_attribute_request(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Data)

    if Command == "01":  # Read Attribute response
        return buildframe_read_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)

    if Command == "02":  # Write Attributes
        return buildframe_write_attribute_request(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Data)

    if Command == "04":  # Write Attribute response
        return buildframe_write_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)

    if Command == "06":  # Configure Reporting
        return frame

    if Command == "07":  # Configure Reporting Response
        return buildframe_configure_reporting_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)
    
    if Command == '09':  # Read Configure Reporting Response
        return buildframe_read_configure_reporting_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)

    if Command == "0a":  # Report attributes
        return buildframe_report_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)

    if Command == "0b":  # Default Response
        return frame

    if Command == "0d":  # Discover Attributes Response
        return buildframe_discover_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)


def buildframe_discover_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    # 01 0000f0010023020023030021040023050021060030070021080021090021fdff21
    self.log.logging("zclDecoder", "Debug", "buildframe_discover_attribute_response - Data: %s" % Data)
    
    discovery_complete = Data[:2]
    buildPayload = "f7" + discovery_complete
    buildPayload += SrcNwkId + SrcEndPoint + ClusterId
    
    idx = 2
    while idx < len( Data ) and len(Data[idx:]) >= 6:
        Attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
        idx += 4
        Attribute_type = Data[idx : idx + 2]
        idx += 2
        buildPayload += Attribute + Attribute_type
    
    return encapsulate_plugin_frame("8140", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_read_attribute_request(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_read_attribute_request - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data))
    if len(Data) % 4 != 0:
        self.log.logging("zclDecoder", "Debug", "Most Likely Livolo Frame : %s (%s)" % (Data, len(Data)))
        return frame

    ManufSpec = "00"
    ManufCode = "0000"
    if ManufacturerCode:
        ManufSpec = "01"
        ManufCode = ManufacturerCode

    buildPayload = Sqn + SrcNwkId + SrcEndPoint + TargetEp + ClusterId + "01" + ManufSpec + ManufCode
    idx = nbAttribute = 0
    payloadOfAttributes = ""
    while idx < len(Data) and len(Data[idx:]) >= 4:
        nbAttribute += 1
        Attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
        idx += 4
        payloadOfAttributes += Attribute

    buildPayload += "%02x" % (nbAttribute) + payloadOfAttributes
    return encapsulate_plugin_frame("0100", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_write_attribute_request(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_write_attribute_request - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data))

    ManufSpec = "00"
    ManufCode = "0000"
    if ManufacturerCode:
        ManufSpec = "01"
        ManufCode = ManufacturerCode

    buildPayload = Sqn + SrcNwkId + SrcEndPoint + TargetEp + ClusterId + "01" + ManufSpec + ManufCode
    idx = nbAttribute = 0
    payloadOfAttributes = ""
    while idx < len(Data) and len(Data[idx:]) >= 8:
        nbAttribute += 1
        Attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
        idx += 4

        DType = Data[idx : idx + 2]
        idx += 2
        
        idx, size, value = extract_value_size(self, Data, idx, DType )
        if value is None and idx is None:
            decoding_error(self, "buildframe_write_attribute_request", Sqn, SrcNwkId, SrcEndPoint, ClusterId, Attribute, DType, idx=idx, buildPayload=buildPayload, frame=frame, Data=Data)
            return frame

        lenData = "%04x" % (size // 2)
        payloadOfAttributes += Attribute + DType + lenData + value
        idx += size

    buildPayload += "%02x" % (nbAttribute) + payloadOfAttributes
    return encapsulate_plugin_frame("0110", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_write_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_write_attribute_response - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data))

    # This is based on assumption that we only Write 1 attribute at a time
    buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId + "0000" + Data
    return encapsulate_plugin_frame("8110", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_read_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_read_attribute_response - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data))

    nbAttribute = 0
    idx = 0
    buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId
    # Len of remaining Data is either 8 for response with Status/Type/Value or 6 for response with only Status (exemple "86" attribute doesn't exist in cluster)
    #  while idx < len(Data) and len(Data[idx:]) >= 8:
    while idx < len(Data) and len(Data[idx:]) >= 6:
        nbAttribute += 1
        Attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
        idx += 4
        Status = Data[idx : idx + 2]
        idx += 2
        if Status != "00":
            buildPayload += Attribute + Status
            continue
        
        DType = Data[idx : idx + 2]
        idx += 2
        idx, size, value = extract_value_size(self, Data, idx, DType )
        if value is None and idx is None:
            decoding_error(self, "buildframe_read_attribute_response", Sqn, SrcNwkId, SrcEndPoint, ClusterId, Attribute, DType, idx=idx, buildPayload=buildPayload, frame=frame, Data=Data)
            return frame

        lenData = "%04x" % (size // 2)
        buildPayload += Attribute + Status + DType + lenData + value
        idx += size

    return encapsulate_plugin_frame("8100", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_report_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_report_attribute_response - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data))

    buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId
    nbAttribute = 0
    idx = 0
    while idx < len(Data) and len(Data[idx:]) >= 8:
        # We need to make sure that the remaining is still able to contain Attribute, Data Type and Value
        nbAttribute += 1
        Attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
        idx += 4
        DType = Data[idx : idx + 2]
        idx += 2
        idx, size, value = extract_value_size(self, Data, idx, DType )
        if value is None and idx is None:
            decoding_error(self, "buildframe_report_attribute_response", Sqn, SrcNwkId, SrcEndPoint, ClusterId, Attribute, DType, idx=idx, buildPayload=buildPayload, frame=frame, Data=Data)
            return frame

        lenData = "%04x" % (size // 2)
        buildPayload += Attribute + "00" + DType + lenData + value
        idx += size

    return encapsulate_plugin_frame("8102", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_configure_reporting_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_configure_reporting_response - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data))

    if len(Data) == 2:
        # The response tells that all Attributes have been correctly configured
        # in that case Data == Status as Direction and Attribute are omitted.
        nbAttribute = 1
        buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId + Data
    else:
        # The response details the status per attribute
        idx = 0
        nbAttribute = 0
        buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId
        while idx < len(Data) and len(Data[idx:]) >= 8:
            nbAttribute += 1
            Status = Data[idx : idx + 2]
            idx += 2
            Direction = Data[idx : idx + 2]
            idx += 2
            Attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
            idx += 4
            buildPayload += Attribute + Status

    return encapsulate_plugin_frame("8120", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_read_configure_reporting_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_read_configure_reporting_response - %s %s %s Data: %s" % (
        SrcNwkId, SrcEndPoint, ClusterId, Data))
  
    buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId  
    
    idx = 0
    while idx < len(Data) and len(Data[idx:]) >= 8:
        status = Data[idx:idx + 2]
        buildPayload += status
        idx += 2
        direction = Data[idx:idx + 2]
        buildPayload += direction
        idx += 2
        attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
        buildPayload += attribute
        idx += 4

        DataType = MinInterval = MaxInterval = Change = None
        if status == "00":
            DataType = Data[idx:idx + 2]
            buildPayload += DataType
            idx += 2
            MinInterval = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
            buildPayload += MinInterval
            idx += 4
            MaxInterval = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
            buildPayload += MaxInterval
            idx += 4
            
            if composite_value( int(DataType,16) ) or discrete_value(int(DataType, 16)):
                pass
        
            elif DataType in SIZE_DATA_TYPE:
                size = SIZE_DATA_TYPE[DataType] * 2
                Change = decode_endian_data(Data[idx : idx + size], DataType)
                buildPayload += Change
                idx += size
                
            if direction == "01":
                timeout = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
                buildPayload += timeout
                idx += 1
                                      
            self.log.logging("zclDecoder", "Debug", "buildframe_read_configure_reporting_response - NwkId: %s Ep: %s Cluster: %s Attribute: %s Status: %s DataType: %s Min: %s Max: %s Change: %s" % (
                SrcNwkId, SrcEndPoint, ClusterId, attribute, status, DataType, MinInterval, MaxInterval, Change))

    return encapsulate_plugin_frame("8122", buildPayload, frame[len(frame) - 4 : len(frame) - 2])    
    
# Cluster Specific commands

# Cluster 0x0003 - Identify

def buildframe_for_cluster_0003(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data ):
    if Command == "00":  # Identify
        self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_0003 - Identify command Time: %s" % Data[:4])
        return None

    if Command == "01":  # Identify Query
        self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_0003 - Identify Query ")
        return None

    if Command == "40":  # Trigger effect
        self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_0003 - Trigger Effect: %s   %s" % ( Data[:2], Data[2:4]))
        return None


# Cluster 0x0004 - Groups

def buildframe_for_cluster_0004(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    if Command == "00":
        return buildframe_8060_add_group_member_ship_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)
    if Command == "01":
        return buildframe_8061_check_group_member_ship_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)
    if Command == "02":
        return buildframe8062_look_for_group_member_ship_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)
    if Command == "03":
        return buildframe8063_remove_group_member_ship_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)


def buildframe_8060_add_group_member_ship_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    #MsgSequenceNumber = MsgData[0:2]
    #MsgEP = MsgData[2:4]
    #MsgClusterID = MsgData[4:8]
    #MsgStatus = MsgData[8:10]
    #MsgGroupID = MsgData[10:14]
    #MsgSrcAddr = MsgData[14:18]
    self.log.logging("zclDecoder", "Debug", "buildframe_8060_add_group_member_ship_response - Data: %s" % Data)
        
    buildPayload = Sqn + SrcEndPoint + "0004" + Data[:2] + decode_endian_data(Data[2:6], "21") + SrcNwkId
    return encapsulate_plugin_frame("8060", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_8061_check_group_member_ship_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    #MsgSequenceNumber = MsgData[0:2]
    #MsgEP = MsgData[2:4]
    #MsgClusterID = MsgData[4:8]
    #MsgStatus = MsgData[8:10]
    #MsgGroupID = MsgData[10:14]
    #MsgSrcAddr = MsgData[14:18]
    self.log.logging("zclDecoder", "Debug", "buildframe_8061_check_group_member_ship_response - Data: %s" % Data)
    status = Data[:2]
    groupid = decode_endian_data(Data[2:6], "21")
    self.log.logging("zclDecoder", "Debug", "buildframe_8061_    GroupId: %s Status: %s" %( groupid, status))
    

    buildPayload = Sqn + SrcEndPoint + "0004" + status + groupid + SrcNwkId
    return encapsulate_plugin_frame("8061", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe8062_look_for_group_member_ship_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    #MsgSequenceNumber = MsgData[0:2]
    #MsgEP = MsgData[2:4]
    #MsgClusterID = MsgData[4:8]
    #MsgCapacity = MsgData[8:10]
    #MsgGroupCount = MsgData[10:12]
    #MsgListOfGroup = MsgData[12 : lenMsgData - 4]
    #MsgSrcAddr = MsgData[lenMsgData - 4 : lenMsgData]
    self.log.logging("zclDecoder", "Debug", "buildframe8062_look_for_group_member_ship_response - Data: %s" % Data)

    if len(Data) < 4:
        self.log.logging("zclDecoder", "Debug", "buildframe8062_look_for_group_member_ship_response - Uncomplete Data: %s" % Data)
        self.log.logging("zclDecoder", "Debug", "   Sqn %s, SrcNwkId %s, SrcEndPoint %s, TargetEp %s, ClusterId %s frame %s" %(
            Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, frame))
        return frame
    
    capacity = Data[:2]
    group_count = Data[2:4]
    
    self.log.logging("zclDecoder", "Debug", "buildframe8062_ Group Count: %s" %group_count)
    group_list = ""
    idx = 0
    while idx < int(group_count,16) * 4:
        self.log.logging("zclDecoder", "Debug", "buildframe8062_ GroupId: %s" %decode_endian_data( Data[ 4 + idx : (4 + idx) + 4 ], "21"))
        group_list += decode_endian_data( Data[ 4 + idx : (4 + idx) + 4 ], "21")
        idx += 4
        
    buildPayload = Sqn + SrcEndPoint + "0004" + capacity + group_count + group_list + SrcNwkId
    return encapsulate_plugin_frame("8062", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe8063_remove_group_member_ship_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    # MsgSequenceNumber = MsgData[0:2]
    # MsgEP = MsgData[2:4]
    # MsgClusterID = MsgData[4:8]
    # MsgStatus = MsgData[8:10]
    # MsgGroupID = MsgData[10:14]
    # MsgSrcAddr = MsgData[14:18]
    self.log.logging("zclDecoder", "Debug", "buildframe8063_remove_group_member_ship_response - Data: %s" % Data)
# SrcNwkId is not passed ----> Causes a false Error in GrpResponses.py function remove_group_member_ship_response
#    buildPayload = Sqn + SrcEndPoint + "0004" + Data[:2] + decode_endian_data( Data[ 2:6 ], "21")
    buildPayload = Sqn + SrcEndPoint + "0004" + Data[:2] + decode_endian_data( Data[ 2:6 ], "21") + SrcNwkId
    return encapsulate_plugin_frame("8063", buildPayload, frame[len(frame) - 4 : len(frame) - 2])

# Cluster 0x0005 - Scenes

def buildframe_for_cluster_0005(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    if Command == "05":  # Recall Scene
        GroupID = decode_endian_data(Data[:4], "09")
        SceneID = Data[4:6]
        TransitionTime = 'ffff'

        if len(Data) == 10:
            TransitionTime = decode_endian_data(Data[6:10],"21")

        buildPayload = Sqn + SrcEndPoint + ClusterId + "02" + SrcNwkId + Command + GroupID + SceneID + TransitionTime
        return encapsulate_plugin_frame("80a5", buildPayload, frame[len(frame) - 4 : len(frame) - 2])   
    
    return frame
             

# Cluster 0x0006

def buildframe_80x5_message(self, MsgType, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Command, Data):
    # sourcery skip: assign-if-exp
    # handle_message Sender: 0x0EC8 frame for plugin: 0180020011ff00010400060101020ec8020000112401b103

    self.log.logging("zclDecoder", "Debug", "======> Building %s message : Cluster: %s Command: >%s< Data: >%s< (Frame: %s)" % (MsgType, ClusterId, Command, Data, frame))

    # It looks like the ZiGate firmware was adding _unknown (which is not part of the norm)
    unknown_ = "02"   # Seems coming from ZiGate firmware !!!
    buildPayload = Sqn + SrcEndPoint + ClusterId + unknown_ + SrcNwkId + Command + Data

    return encapsulate_plugin_frame(MsgType, buildPayload, frame[len(frame) - 4 : len(frame) - 2])


# Cluster: 0x0019
def buildframe_for_cluster_0019(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    # OTA Upgrade
    OTA_UPGRADE_COMMAND = {
        "00": "Image Notify",
        "01": "Query Next Image Request",
        "02": "Query Next Image response",
        "03": "Image Block Request",  # 8501
        "04": "Image Page request",   # 8502
        "05": "Image Block Response",
        "06": "Upgrade End Request",  # 8503
        "07": "Upgrade End response",
        "08": "Query Device Specific File Request",
        "09": "Query Device Specific File response",
    }
    if Command == "03":
        # Image Block request,
        return buildframe_for_cluster_8501(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)
    
    if Command == "04":
        # Image Page request
        self.log.logging("zclDecoder", "Log", "Image Page request from '%s' for which no tests have been done so far. Please contact us" %SrcNwkId)
        return buildframe_for_cluster_8502(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)
        
    if Command == "06":
        return buildframe_for_cluster_8503(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)
        
    elif Command in OTA_UPGRADE_COMMAND:
        self.log.logging("zclDecoder", "Debug", "zcl_decoders OTA Upgrade Command %s/%s data: %s" % (Command, OTA_UPGRADE_COMMAND[Command], Data))
        return frame
    return frame


def buildframe_for_cluster_8501(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):

    self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_8501 Building %s message : Cluster: %s Command: >%s< Data: >%s< (Frame: %s)" % (
        '8501', ClusterId, Command, Data, frame))

    FieldControl = decode_endian_data(Data[:2], "20")
    ManufCode = decode_endian_data(Data[2:6], "21")
    ImageType = decode_endian_data(Data[6:10], "21")
    ImageVersion = decode_endian_data(Data[10:18], "23")
    ImageOffset = decode_endian_data(Data[18:26], "23")
    MaxDataSize = decode_endian_data(Data[26:28], "20")
    if len(Data) == 32:
        MinBlockPeriod = decode_endian_data(Data[28:32], "21")
    else:
        MinBlockPeriod = '0000'

    self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_8501 %s %s %s %s %s %s %s " % ( 
        FieldControl, ManufCode, ImageType, ImageVersion, ImageOffset, MaxDataSize, MinBlockPeriod))  

    IEEE = "0000000000000000"
    buildPayload = Sqn + SrcEndPoint + ClusterId + "02" + SrcNwkId + IEEE 
    buildPayload += ImageOffset + ImageVersion + ImageType + ManufCode + MinBlockPeriod + MaxDataSize + FieldControl
    self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_8501 payload: %s" %buildPayload)
    return encapsulate_plugin_frame("8501", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_for_cluster_8502(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_8503 Building %s message : Cluster: %s Command: >%s< Data: >%s< (Frame: %s)" % (
        '8502', ClusterId, Command, Data, frame))

    FieldControl = decode_endian_data(Data[:2], "20")
    ManufCode = decode_endian_data(Data[2:6], "21")
    ImageType = decode_endian_data(Data[6:10], "21")
    ImageVersion = decode_endian_data(Data[10:18], "23")
    ImageOffset = decode_endian_data(Data[18:26], "23")
    MaxDataSize = decode_endian_data(Data[26:28], "20")
    Pagesize = decode_endian_data(Data[28:32], "21")
    ResponseSpacing = decode_endian_data(Data[32:36], "21")
    
    RequestNodeAddress = ""
    if len(Data) > 36:
        RequestNodeAddress = decode_endian_data(Data[36:52], "0F")
        
    buildPayload = Sqn + SrcEndPoint + ClusterId + "02" + SrcNwkId
    buildPayload += ImageOffset + ImageVersion + ImageType + ManufCode + MaxDataSize + Pagesize + ResponseSpacing + FieldControl + RequestNodeAddress
    
    self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_8502 payload: %s" %buildPayload)
    return encapsulate_plugin_frame("8502", buildPayload, frame[len(frame) - 4 : len(frame) - 2])
    
    
def buildframe_for_cluster_8503(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):

    self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_8503 Building %s message : Cluster: %s Command: >%s< Data: >%s< (Frame: %s)" % (
        '8503', ClusterId, Command, Data, frame))

    status = decode_endian_data(Data[:2], "20")
    ManufCode = decode_endian_data(Data[2:6], "21")
    ImageType = decode_endian_data(Data[6:10], "21")
    ImageVersion = decode_endian_data(Data[10:18], "23")

    self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_8503 %s %s %s %s" % ( 
        status, ManufCode, ImageType, ImageVersion ))  

    buildPayload = Sqn + SrcEndPoint + ClusterId + "02" + SrcNwkId + ImageVersion + ImageType + ManufCode + status
    return encapsulate_plugin_frame("8503", buildPayload, frame[len(frame) - 4 : len(frame) - 2])
 
# Cluster 0x0020
# Pool Control

def buildframe_for_cluster_0020(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):

    if Command == "00":  # Check-in Command
        # respond with a Check-in Response command indicating that the server SHOULD or SHOULD not begin fast poll mode.
        # Will be handle via receive_poll_cluster() call from inRawAPS
        # Let's return the Data Indication
        return frame
    
    return frame
    

# Cluster 0x0500
# Cmd : 0x00 Zone Enroll Response  -> 0400
#     : 0x01 Initiate Normal Operation Mode
#     : 0x02 Initiate Test mode


def buildframe_0400_cmd(self, MsgType, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Command, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_0400_cmd - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data))

    # Zone Enroll Response
    enroll_response_code = Data[:2]
    zone_id = Data[2:4]
    buildPayload = Sqn + SrcNwkId + SrcEndPoint + enroll_response_code + zone_id
    return encapsulate_plugin_frame(MsgType, buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_8400_cmd(self, MsgType, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Command, Data):
    # IAS Zone Enroll request
    self.log.logging("zclDecoder", "Debug", "buildframe_8400_cmd - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data))
    zonetype = decode_endian_data( Data[:4], '31')
    ManufacturerCode = decode_endian_data( Data[4:8], '21' )
    buildPayload = Sqn + zonetype + ManufacturerCode + SrcNwkId + SrcEndPoint
    return encapsulate_plugin_frame(MsgType, buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_8401_cmd(self, MsgType, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Command, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_8401_cmd - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data))
    # Zone status change

    zone_status = decode_endian_data(Data[:4], "19")
    extended_status = Data[4:6]
    zoneid = Data[6:8]
    delay = decode_endian_data(Data[8:12], "21")
    
    buildPayload = Sqn + SrcEndPoint + ClusterId + "02" + SrcNwkId 
    buildPayload += zone_status + extended_status + zoneid + delay
    
    
    return encapsulate_plugin_frame(MsgType, buildPayload, frame[len(frame) - 4 : len(frame) - 2])


# Helpers
def extract_value( Data, DType, idx, size):
    data = Data[idx : idx + size]
    if DType in ( "43",):
        return decode_endian_data(data, DType, size)
        
    return decode_endian_data(data, DType)


def extract_value_size(self, Data, idx, DType ):

    if DType in ("41", "42"):  # ZigBee_OctedString = 0x41, ZigBee_CharacterString = 0x42
        size = int(Data[idx : idx + 2], 16) * 2
        idx += 2
        if len(Data[idx:]) >= size:
            value = extract_value( Data, DType, idx, size)
            return idx, size, value
        value = extract_value( Data, DType, idx, len(Data[idx:]))
        idx += size
        return idx, size, value

    if DType in ("43", ):  # Long Octet 
        size = (struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0] ) * 2
        idx += 4
        value = extract_value( Data, DType, idx, size) if size > 0 else ""
        idx += size
        return idx, size, value

    if DType in ("48", "4c"):
        # Today found for attribute 0xff02 Xiaomi, just take all data
        nbElement = Data[idx + 2 : idx + 4] + Data[idx : idx + 2]
        idx += 4
        size = len(Data) - idx
        value = extract_value( Data, DType, idx, size)
        return idx, size, value
    
    if DType in SIZE_DATA_TYPE:
        size = SIZE_DATA_TYPE[DType] * 2
        value = extract_value( Data, DType, idx, size)
        return idx, size, value

    return None, None, None


def decoding_error(self, source, sqn, nwkid, ep, cluster, attribute, DType, idx=None, buildPayload=None, frame=None, Data=None):
    _context = {
        "Sqn": sqn,
        "NwkId": nwkid,
        "Ep": ep,
        "Cluster": cluster,
        "Attribute": attribute,
        "DType": DType,
        "BuildPayload": buildPayload,
        "Frame": frame,
        "Data": Data,
        "Idx": idx,
    }
    self.log.logging("zclDecoder", "Error", "%s - decoding_error - %s %s %s %s %s %s %s %s %s %s" % (
        source, sqn, nwkid, ep, cluster, attribute, DType, idx, buildPayload, frame, Data ), nwkid=nwkid, context=_context)
