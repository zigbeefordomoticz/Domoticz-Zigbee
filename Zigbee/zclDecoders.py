# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#


import struct
from Modules.tools import retreive_cmd_payload_from_8002, is_direction_to_client, is_direction_to_server
from Zigbee.encoder_tools import encapsulate_plugin_frame, decode_endian_data
from Modules.zigateConsts import ADDRESS_MODE, SIZE_DATA_TYPE


def zcl_decoders(self, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Payload, frame):

    fcf = Payload[:2]
    GlobalCommand, Sqn, ManufacturerCode, Command, Data = retreive_cmd_payload_from_8002(Payload)
    self.log.logging("zclDecoder", "Debug", "zcl_decoders GlobalCommand: %s Sqn: %s ManufCode: %s Command: %s Data: %s Payload: %s" %(
        GlobalCommand, Sqn, ManufacturerCode, Command, Data, Payload))

    if GlobalCommand:
        return buildframe_foundation_cluster( self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Data )

    if ClusterId == "0003":
        return buildframe_for_cluster_0003(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data )

    if ClusterId == "0004":
        return buildframe_for_cluster_0004(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data )

    if ClusterId == "0006":
        # Remote report
        return buildframe_80x5_message(self, "8095", frame, Sqn, SrcNwkId, SrcEndPoint,TargetEp, ClusterId, ManufacturerCode, Command, Data)

    if ClusterId == "0008":
        # Remote report
        return buildframe_80x5_message(self, "8085", frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Command, Data)

    if ClusterId == "0019":
        # OTA Upgrade
        OTA_UPGRADE_COMMAND = {
            "00": "Image Notify",
            "01": "Query Next Image Request",
            "02": "Query Next Image response",
            "03": "Image Block Request",  # 8501
            "04": "Image Page request",
            "05": "Image Block Response",
            "06": "Upgrade End Request",  # 8503
            "07": "Upgrade End response",
            "08": "Query Device Specific File Request",
            "09": "Query Device Specific File response",
        }
        if Command in OTA_UPGRADE_COMMAND:
            self.log.logging("zclDecoder", "Log", "zcl_decoders OTA Upgrade Command %s/%s data: %s" % (Command, OTA_UPGRADE_COMMAND[Command], Data))
            return frame

    if ClusterId == "0500" and is_direction_to_server(fcf) and Command == "00":
        return buildframe_0400_cmd(self, "0400", frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Command, Data)

    if ClusterId == "0500" and is_direction_to_client(fcf) and Command == "00":
        return buildframe_8401_cmd(self, "8401", frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Command, Data)

    if ClusterId == "0500" and is_direction_to_client(fcf) and Command == "01":
        return buildframe_8400_cmd(self, "8400", frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Command, Data)
    
    self.log.logging(
        "zclDecoder",
        "Log",
        "zcl_decoders Unknown Command: %s NwkId: %s Ep: %s Cluster: %s Payload: %s - GlobalCommand: %s, Sqn: %s, ManufacturerCode: %s"
        % (
            Command,
            SrcNwkId,
            SrcEndPoint,
            ClusterId,
            Data,
            GlobalCommand,
            Sqn,
            ManufacturerCode,
        ),
    )

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

    if Command == "0a":  # Report attributes
        return buildframe_report_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)

    if Command == "0b":  #
        return frame

    if Command == "0d":  # Discover Attributes Response
        return buildframe_discover_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)


def buildframe_discover_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):

    self.log.logging("zclDecoder", "Debug", "buildframe_discover_attribute_response - Data: %s" % Data)
    discovery_complete = Data[:2]
    if discovery_complete == "01":
        Attribute_type = "00"
        Attribute = "0000"
    else:
        # It is assumed that only one attribute at a time is requested (this is not the standard)
        idx = 2
        Attribute_type = Data[idx : idx + 2]
        idx += 2
        Attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
        idx += 4

    buildPayload = discovery_complete + Attribute_type + Attribute + SrcNwkId + SrcEndPoint + ClusterId
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
    while idx < len(Data):
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
    while idx < len(Data):
        nbAttribute += 1
        Attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
        idx += 4

        DType = Data[idx : idx + 2]
        idx += 2
        if DType in SIZE_DATA_TYPE:
            size = SIZE_DATA_TYPE[DType] * 2
        elif DType in ("48", "4c"):
            nbElement = Data[idx + 2 : idx + 4] + Data[idx : idx + 2]
            idx += 4
            # Today found for attribute 0xff02 Xiaomi, just take all data
            size = len(Data) - idx

        elif DType in ("41", "42"):  # ZigBee_OctedString = 0x41, ZigBee_CharacterString = 0x42
            size = int(Data[idx : idx + 2], 16) * 2
            idx += 2
        else:
            self.log.logging("zclDecoder", "Error", "buildframe_write_attribute_request - Unknown DataType size: >%s< vs. %s " % (DType, str(SIZE_DATA_TYPE)))
            self.log.logging("zclDecoder", "Error", "buildframe_write_attribute_request - ClusterId: %s Attribute: %s Data: %s" % (ClusterId, Attribute, Data))
            return frame

        data = Data[idx : idx + size]
        idx += size
        value = decode_endian_data(data, DType)
        lenData = "%04x" % (size // 2)
        payloadOfAttributes += Attribute + DType + lenData + value

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
    while idx < len(Data):
        nbAttribute += 1
        Attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
        idx += 4
        Status = Data[idx : idx + 2]
        idx += 2
        if Status == "00":
            DType = Data[idx : idx + 2]
            idx += 2
            if DType in SIZE_DATA_TYPE:
                size = SIZE_DATA_TYPE[DType] * 2
                data = Data[idx : idx + size]
                idx += size
                value = decode_endian_data(data, DType)
                lenData = "%04x" % (size // 2)

            elif DType in ("48", "4c"):
                nbElement = Data[idx + 2 : idx + 4] + Data[idx : idx + 2]
                idx += 4
                # Today found for attribute 0xff02 Xiaomi, just take all data
                size = len(Data) - idx
                data = Data[idx : idx + size]
                idx += size
                value = decode_endian_data(data, DType)
                lenData = "%04x" % (size // 2)

            elif DType in ("41", "42"):  # ZigBee_OctedString = 0x41, ZigBee_CharacterString = 0x42
                size = int(Data[idx : idx + 2], 16) * 2
                idx += 2
                data = Data[idx : idx + size]
                idx += size
                value = decode_endian_data(data, DType, size)
                lenData = "%04x" % (size // 2)

            else:
                self.log.logging("zclDecoder", "Error", "buildframe_read_attribute_response - Unknown DataType size: >%s< vs. %s " % (DType, str(SIZE_DATA_TYPE)))
                self.log.logging("zclDecoder", "Error", "buildframe_read_attribute_response - ClusterId: %s Attribute: %s Data: %s" % (ClusterId, Attribute, Data))
                return frame

            buildPayload += Attribute + Status + DType + lenData + value
        else:
            # Status != 0x00
            buildPayload += Attribute + Status

    return encapsulate_plugin_frame("8100", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_report_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_report_attribute_response - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data))

    buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId
    nbAttribute = 0
    idx = 0
    while idx < len(Data):
        nbAttribute += 1
        Attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
        idx += 4
        DType = Data[idx : idx + 2]
        idx += 2
        if DType in SIZE_DATA_TYPE:
            size = SIZE_DATA_TYPE[DType] * 2

        elif DType in ("48", "4c"):
            # Today found for attribute 0xff02 Xiaomi, just take all data
            nbElement = Data[idx + 2 : idx + 4] + Data[idx : idx + 2]
            idx += 4
            size = len(Data) - idx

        elif DType in ("41", "42"):  # ZigBee_OctedString = 0x41, ZigBee_CharacterString = 0x42
            size = int(Data[idx : idx + 2], 16) * 2
            idx += 2

        elif DType == "00":
            self.log.logging(
                "zclDecoder", "Error", "buildframe_report_attribute_response %s/%s Cluster: %s nbAttribute: %s Attribute: %s DType: %s idx: %s frame: %s" % (SrcNwkId, SrcEndPoint, ClusterId, nbAttribute, Attribute, DType, idx, frame)
            )
            return frame

        else:
            self.log.logging("zclDecoder", "Error", "buildframe_report_attribute_response - Unknown DataType size: >%s< vs. %s " % (DType, str(SIZE_DATA_TYPE)))
            self.log.logging("zclDecoder", "Error", "buildframe_report_attribute_response - NwkId: %s ClusterId: %s Attribute: %s Frame: %s" % (SrcNwkId, ClusterId, Attribute, frame))
            return frame

        data = Data[idx : idx + size]
        idx += size
        value = decode_endian_data(data, DType)
        lenData = "%04x" % (size // 2)
        buildPayload += Attribute + "00" + DType + lenData + value

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
        while idx < len(Data):
            nbAttribute += 1
            Status = Data[idx : idx + 2]
            idx += 2
            Direction = Data[idx : idx + 2]
            idx += 2
            Attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
            idx += 4
            buildPayload += Attribute + Status

    return encapsulate_plugin_frame("8120", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


# Cluster Specific commands

# Cluster 0x0003 - Identify

def buildframe_for_cluster_0003(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data ):
    if Command == "00":  # Identify
        self.log.logging("zclDecoder", "Log", "buildframe_for_cluster_0003 - Identify command Time: %s" % Data[:4])
        return None

    if Command == "01":  # Identify Query
        self.log.logging("zclDecoder", "Log", "buildframe_for_cluster_0003 - Identify Query ")
        return None

    if Command == "40":  # Trigger effect
        self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_0003 - Trigger Effect: %s   %s" % ( Data[:2], Data[2:4]))
        return None


# Cluster 0x0004 - Groups

def buildframe_for_cluster_0004(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data ):
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

    capacity = Data[:2]
    group_count = Data[2:4]
    
    self.log.logging("zclDecoder", "Debug", "buildframe8062_ Group Count: %s" %group_count)
    group_list = ""
    idx = 0
    while  idx < int(group_count,16) * 4:
        self.log.logging("zclDecoder", "Debug", "buildframe8062_ GroupId: %s" %decode_endian_data( Data[ 4 + idx : (4 + idx) + 4 ], "21"))
        group_list += decode_endian_data( Data[ 4 + idx : (4 + idx) + 4 ], "21")
        idx += 4
        
    buildPayload = Sqn + SrcEndPoint + "0004" + capacity + group_count + group_list + SrcNwkId
    return encapsulate_plugin_frame("8062", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe8063_remove_group_member_ship_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    #MsgSequenceNumber = MsgData[0:2]
    #MsgEP = MsgData[2:4]
    #MsgClusterID = MsgData[4:8]
    #MsgStatus = MsgData[8:10]
    #MsgGroupID = MsgData[10:14]
    #MsgSrcAddr = MsgData[14:18]
    self.log.logging("zclDecoder", "Debug", "buildframe8063_remove_group_member_ship_response - Data: %s" % Data)
    
    buildPayload = Sqn + SrcEndPoint + "0004" + Data[:2] + decode_endian_data( Data[ 2:6 ], "21")
    return encapsulate_plugin_frame("8063", buildPayload, frame[len(frame) - 4 : len(frame) - 2])




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