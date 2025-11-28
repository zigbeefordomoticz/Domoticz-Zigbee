# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#


import struct
from os import stat

from Modules.tools import (get_deviceconf_parameter_value,
                           is_direction_to_client, is_direction_to_server,
                           retreive_cmd_payload_from_8002)
from Modules.zigateConsts import (SIZE_DATA_TYPE, ZIGATE_EP, composite_value,
                                  discrete_value)
from Zigbee.encoder_tools import decode_endian_data, encapsulate_plugin_frame
from Zigbee.zclRawCommands import zcl_raw_default_response


def is_duplicate_zcl_frame(self, nwkid, cluster_id, sqn, default_response_disable=False):
    """
    Checks if a given Zigbee ZCL frame is a duplicate based on its sequence number.

    This function prevents processing duplicate ZCL frames by maintaining a history 
    of received sequence numbers per cluster for each device.

    Parameters:
        nwkid (int): The network ID of the Zigbee device.
        cluster_id (int): The cluster ID associated with the frame.
        sqn (int): The sequence number of the received frame.
        default_response_disable (bool): Flag indicating if default response is disabled.

    Returns:
        bool: True if the frame is a duplicate, False otherwise.
    """
    if self.zigbee_communication != "zigpy":
        # No check for zigate
        return False
    if nwkid not in self.ListOfDevices:
        # The device is not yet known
        return False
    if "Model" not in self.ListOfDevices[nwkid]:
        return False
    if not default_response_disable:
        # ????
        return False

    if (
        not get_deviceconf_parameter_value(self, self.ListOfDevices[nwkid]["Model"], "enableZclDuplicatecheck", return_default=False)
        or not self.pluginconf.pluginConf.get("enableZclDuplicatecheck", False)
    ):
        # We have disabled the ZCL SQN duplicate check
        return False

    zcl_sqn = self.ListOfDevices.setdefault(nwkid, {}).setdefault("ZCL-IN-SQN", {})

    if sqn != "00" and sqn == zcl_sqn.get(cluster_id):
        self.log.logging("zclDecoder", "Log", f"Duplicate frame {nwkid} sqn: {sqn} sqn_clusters{zcl_sqn} cluster_id: {cluster_id} default_response_disable: {default_response_disable}", nwkid)
        return True  # Duplicate frame detected

    zcl_sqn[cluster_id] = sqn  # Store new sequence number

    return False


def send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufcode, status="00"):
    if self.zigbee_communication != "zigpy":
        # No check for zigate
        return False

    self.log.logging(
        "zclDecoder",
        "Debug",
        (
            f"FCF: {fcf} DisableDefResp: {disable_default_response} "
            f"SrcNWK: {src_nwk_id} SrcEP: {src_endpoint} ClusterID: {cluster_id} "
            f"Command: {command} SQN: {int(sqn, 16)}/0x{sqn} ManufCode: {manufcode} Status: {status}"
        ),
        src_nwk_id,
    )

    if not disable_default_response:
        self.log.logging("zclDecoder", "Debug",f"zcl_decoders sending a default response {disable_default_response} for command {command}", src_nwk_id)
        zcl_raw_default_response(self, src_nwk_id, ZIGATE_EP, src_endpoint, cluster_id, command, sqn, command_status="00", manufcode=manufcode, orig_fcf=fcf)


def zcl_decoders(self, src_nwk_id, src_endpoint, target_ep, cluster_id, payload, frame):
    """
    Decodes ZCL messages, checks for duplicates, and processes specific cluster commands.

    Parameters:
        src_nwk_id (int): Source network ID.
        src_endpoint (int): Source endpoint.
        target_ep (int): Target endpoint.
        cluster_id (str): Cluster ID of the message.
        payload (str): The payload data of the message.
        frame (str): The frame data of the message.

    Returns:
        Processed frame data or None if the frame is a duplicate or unhandled.
    """
    
    fcf = payload[:2]  # Extract frame control field
    disable_default_response, global_command, sqn, manufacturer_code, command, data = retreive_cmd_payload_from_8002(payload)

    # Check for duplicate ZCL frames
    if is_duplicate_zcl_frame(self, src_nwk_id, cluster_id, sqn, disable_default_response):
        self.log.logging("zclDecoder", "Log", f"Duplicate frame found [{sqn}] {payload}", src_nwk_id)
        return None

    # Log ZCL message details
    self.log.logging(
        "zclDecoder",
        "Debug",
        (
            f"SrcNWK: {src_nwk_id} SrcEP: {src_endpoint} TargetEP: {target_ep} ClusterID: {cluster_id}  "
            f"FCF: {fcf} DisableDefaultRsp: {disable_default_response} GlobalCommand: {global_command} "
            f"Sqn: {sqn} ManufCode: {manufacturer_code} Command: {command} Data: {data} "
            f"Payload: {payload} Frame: {frame}"
        ),
        src_nwk_id,
    )

    if global_command:
        return buildframe_foundation_cluster(self, fcf, disable_default_response, command, frame, sqn, src_nwk_id, src_endpoint, target_ep, cluster_id, manufacturer_code, data)

    if cluster_id == "0003":
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return buildframe_for_cluster_0003(self, command, frame, sqn, src_nwk_id, src_endpoint, target_ep, cluster_id, data )

    if cluster_id == "0004":
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return buildframe_for_cluster_0004(self, command, frame, sqn, src_nwk_id, src_endpoint, target_ep, cluster_id, data )

    if cluster_id == "0005" and command == "05":  # Only Recall Scene supported
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return buildframe_for_cluster_0005(self, command, frame, sqn, src_nwk_id, src_endpoint, target_ep, cluster_id, data )

    if cluster_id == "0006":
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return buildframe_80x5_message(self, "8095", frame, sqn, src_nwk_id, src_endpoint,target_ep, cluster_id, manufacturer_code, command, data)

    if cluster_id == "0008":
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return buildframe_80x5_message(self, "8085", frame, sqn, src_nwk_id, src_endpoint, target_ep, cluster_id, manufacturer_code, command, data)

    if cluster_id == "0019":
        if manufacturer_code not in {"1021", }:  # By pass Default Response as of Legrand GW
            send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return buildframe_for_cluster_0019(self, command, frame, sqn, src_nwk_id, src_endpoint, target_ep, cluster_id, data)

    if cluster_id == "0020":
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return buildframe_for_cluster_0020(self, command, frame, sqn, src_nwk_id, src_endpoint, target_ep, cluster_id, data)

    if cluster_id == "0500" and is_direction_to_server(fcf) and command == "00":
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return buildframe_0400_cmd(self, "0400", frame, sqn, src_nwk_id, src_endpoint, target_ep, cluster_id, manufacturer_code, command, data)

    if cluster_id == "0500" and is_direction_to_client(fcf) and command == "00":
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return buildframe_8401_cmd(self, "8401", frame, sqn, src_nwk_id, src_endpoint, target_ep, cluster_id, manufacturer_code, command, data)

    if cluster_id == "0500" and is_direction_to_client(fcf) and command == "01":
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return buildframe_8400_cmd(self, "8400", frame, sqn, src_nwk_id, src_endpoint, target_ep, cluster_id, manufacturer_code, command, data)

    if cluster_id == "0501":
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        # Handle in inRawAPS
        return frame

    # Frames handled by inRawAPS (no logging needed)
    if (
        cluster_id in {"ef00", "ff00"}
        or (command == "80" and cluster_id == "0201" and manufacturer_code == "105e")  # Schneider Electric
        or (cluster_id == "fc00" and manufacturer_code == "100b")
        or (cluster_id == "ffac" and manufacturer_code == "113c")
        or cluster_id == "e001"  # TS011F Plug does this every 24 hours
    ):
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return frame

    # Log unknown commands
    self.log.logging("zclDecoder", "Log",
                     f"Unknown Command: {command} NwkId: {src_nwk_id} Ep: {src_endpoint} Cluster: {cluster_id} "
                     f"Payload: {data} - GlobalCommand: {global_command}, Sqn: {sqn}, ManufacturerCode: {manufacturer_code}", src_nwk_id)

    return frame

def buildframe_foundation_cluster(self, fcf, disable_default_response, command, frame, sqn, src_nwk_id, src_endpoint, TargetEp, cluster_id, manufacturer_code, data):
    """
    Processes ZCL foundation cluster commands and builds the appropriate frame.

    Parameters:
        command (str): The ZCL command identifier.
        frame (str): The full message frame.
        sqn (str): Sequence number.
        src_nwk_id (int): Source network ID.
        src_endpoint (int): Source endpoint.
        target_ep (int): Target endpoint.
        cluster_id (str): Cluster ID.
        manufacturer_code (str): Manufacturer code.
        data (str): Payload data.

    Returns:
        Processed frame data or None if not handled.
    """
    self.log.logging(
        "zclDecoder",
        "Debug",
        (
            f"FCF: {fcf} DisableDefaultRsp: {disable_default_response} "
            f"Command: {command} Frame: {frame} SQN: {int(sqn, 16)}/0x{sqn} "
            f"SrcNWK: {src_nwk_id} SrcEP: {src_endpoint} TargetEP: {TargetEp} "
            f"ClusterID: {cluster_id} ManufCode: {manufacturer_code} Data: {data}"
        ),
        src_nwk_id,
    )

    if command == "00":  # Read Attribute
        return foundation_cluster_read_attribute_request(self, frame, sqn, src_nwk_id, src_endpoint, TargetEp, cluster_id, manufacturer_code, data)

    if command == "01":  # Read Attribute response
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return foundation_cluster_read_attribute_response(self, frame, sqn, src_nwk_id, src_endpoint, TargetEp, cluster_id, data)

    if command == "02":  # Write Attributes
        return foundation_cluster_write_attribute_request(self, frame, sqn, src_nwk_id, src_endpoint, TargetEp, cluster_id, manufacturer_code, data)

    if command == "04":  # Write Attribute response
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return foundation_cluster_write_attribute_response(self, frame, sqn, src_nwk_id, src_endpoint, TargetEp, cluster_id, data)

    if command == "06":  # Configure Reporting
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return frame

    if command == "07":  # Configure Reporting Response
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return foundation_cluster_configure_reporting_response(self, frame, sqn, src_nwk_id, src_endpoint, TargetEp, cluster_id, data)

    if command == '09':  # Read Configure Reporting Response
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return foundation_cluster_read_configure_reporting_response(self, frame, sqn, src_nwk_id, src_endpoint, TargetEp, cluster_id, data)

    if command == "0a":  # Report attributes
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return foundation_cluster_report_attribute_response(self, frame, sqn, src_nwk_id, src_endpoint, TargetEp, cluster_id, data)

    if command == "0b":  # Default Response
        return frame

    if command == "0d":  # Discover Attributes Response
        send_default_rsp( self, fcf, disable_default_response, src_nwk_id, src_endpoint, cluster_id, command, sqn, manufacturer_code, status="00")
        return foundation_cluster_discover_attribute_response(self, frame, sqn, src_nwk_id, src_endpoint, TargetEp, cluster_id, data)


def foundation_cluster_discover_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
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


def foundation_cluster_read_attribute_request(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_read_attribute_request - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data), SrcNwkId)
    if len(Data) % 4 != 0:
        self.log.logging("zclDecoder", "Debug", "Most Likely Livolo Frame : %s (%s)" % (Data, len(Data)), SrcNwkId)
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


def foundation_cluster_write_attribute_request(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_write_attribute_request - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data), SrcNwkId)

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


def foundation_cluster_write_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_write_attribute_response - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data), SrcNwkId)

    # This is based on assumption that we only Write 1 attribute at a time
    buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId + "0000" + Data
    return encapsulate_plugin_frame("8110", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def foundation_cluster_read_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_read_attribute_response - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data), SrcNwkId)

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


def foundation_cluster_report_attribute_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_report_attribute_response - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data), SrcNwkId)

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


def foundation_cluster_configure_reporting_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_configure_reporting_response - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data), SrcNwkId)

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


def foundation_cluster_read_configure_reporting_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_read_configure_reporting_response - %s %s %s Data: %s" % (
        SrcNwkId, SrcEndPoint, ClusterId, Data), SrcNwkId)
  
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
                SrcNwkId, SrcEndPoint, ClusterId, attribute, status, DataType, MinInterval, MaxInterval, Change), SrcNwkId)

    return encapsulate_plugin_frame("8122", buildPayload, frame[len(frame) - 4 : len(frame) - 2])    
    
# Cluster Specific commands

# Cluster 0x0003 - Identify

def buildframe_for_cluster_0003(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data ):
    if Command == "00":  # Identify
        self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_0003 - Identify command Time: %s" % Data[:4], SrcNwkId)
        return None

    if Command == "01":  # Identify Query
        self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_0003 - Identify Query ", SrcNwkId)
        return None

    if Command == "40":  # Trigger effect
        self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_0003 - Trigger Effect: %s   %s" % ( Data[:2], Data[2:4]), SrcNwkId)
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
    self.log.logging("zclDecoder", "Debug", "buildframe_8060_add_group_member_ship_response - Data: %s" % Data, SrcNwkId)
        
    buildPayload = Sqn + SrcEndPoint + "0004" + Data[:2] + decode_endian_data(Data[2:6], "21") + SrcNwkId
    return encapsulate_plugin_frame("8060", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_8061_check_group_member_ship_response(self, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    #MsgSequenceNumber = MsgData[0:2]
    #MsgEP = MsgData[2:4]
    #MsgClusterID = MsgData[4:8]
    #MsgStatus = MsgData[8:10]
    #MsgGroupID = MsgData[10:14]
    #MsgSrcAddr = MsgData[14:18]
    self.log.logging("zclDecoder", "Debug", "buildframe_8061_check_group_member_ship_response - Data: %s" % Data, SrcNwkId)
    status = Data[:2]
    groupid = decode_endian_data(Data[2:6], "21")
    self.log.logging("zclDecoder", "Debug", "buildframe_8061_    GroupId: %s Status: %s" %( groupid, status), SrcNwkId)
    

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
    self.log.logging("zclDecoder", "Debug", "buildframe8062_look_for_group_member_ship_response - Data: %s" % Data, SrcNwkId)

    if len(Data) < 4:
        self.log.logging("zclDecoder", "Debug", "buildframe8062_look_for_group_member_ship_response - Uncomplete Data: %s" % Data, SrcNwkId)
        self.log.logging("zclDecoder", "Debug", "   Sqn %s, SrcNwkId %s, SrcEndPoint %s, TargetEp %s, ClusterId %s frame %s" %(
            Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, frame))
        return frame
    
    capacity = Data[:2]
    group_count = Data[2:4]
    
    self.log.logging("zclDecoder", "Debug", "buildframe8062_ Group Count: %s" %group_count, SrcNwkId)
    group_list = ""
    idx = 0
    while idx < int(group_count,16) * 4:
        self.log.logging("zclDecoder", "Debug", "buildframe8062_ GroupId: %s" %decode_endian_data( Data[ 4 + idx : (4 + idx) + 4 ], "21"), SrcNwkId)
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
    self.log.logging("zclDecoder", "Debug", "buildframe8063_remove_group_member_ship_response - Data: %s" % Data, SrcNwkId)
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

    self.log.logging("zclDecoder", "Debug", "======> Building %s message : Cluster: %s Command: >%s< Data: >%s< (Frame: %s)" % (MsgType, ClusterId, Command, Data, frame), SrcNwkId)

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
        self.log.logging("zclDecoder", "Log", "Image Page request from '%s' for which no tests have been done so far. Please contact us" %SrcNwkId, SrcNwkId)
        return buildframe_for_cluster_8502(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)
        
    if Command == "06":
        return buildframe_for_cluster_8503(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data)
        
    elif Command in OTA_UPGRADE_COMMAND:
        self.log.logging("zclDecoder", "Debug", "zcl_decoders OTA Upgrade Command %s/%s data: %s" % (Command, OTA_UPGRADE_COMMAND[Command], Data), SrcNwkId)
        return frame
    return frame


def buildframe_for_cluster_8501(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):

    self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_8501 Building %s message : Cluster: %s Command: >%s< Data: >%s< (Frame: %s)" % (
        '8501', ClusterId, Command, Data, frame), SrcNwkId)

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
        FieldControl, ManufCode, ImageType, ImageVersion, ImageOffset, MaxDataSize, MinBlockPeriod), SrcNwkId)  

    IEEE = "0000000000000000"
    buildPayload = Sqn + SrcEndPoint + ClusterId + "02" + SrcNwkId + IEEE 
    buildPayload += ImageOffset + ImageVersion + ImageType + ManufCode + MinBlockPeriod + MaxDataSize + FieldControl
    self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_8501 payload: %s" %buildPayload, SrcNwkId)
    return encapsulate_plugin_frame("8501", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_for_cluster_8502(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_8503 Building %s message : Cluster: %s Command: >%s< Data: >%s< (Frame: %s)" % (
        '8502', ClusterId, Command, Data, frame), SrcNwkId)

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
    
    self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_8502 payload: %s" %buildPayload, SrcNwkId)
    return encapsulate_plugin_frame("8502", buildPayload, frame[len(frame) - 4 : len(frame) - 2])
    
    
def buildframe_for_cluster_8503(self, Command, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Data):

    self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_8503 Building %s message : Cluster: %s Command: >%s< Data: >%s< (Frame: %s)" % (
        '8503', ClusterId, Command, Data, frame), SrcNwkId)

    status = decode_endian_data(Data[:2], "20")
    ManufCode = decode_endian_data(Data[2:6], "21")
    ImageType = decode_endian_data(Data[6:10], "21")
    ImageVersion = decode_endian_data(Data[10:18], "23")

    self.log.logging("zclDecoder", "Debug", "buildframe_for_cluster_8503 %s %s %s %s" % ( 
        status, ManufCode, ImageType, ImageVersion ), SrcNwkId)  

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
    self.log.logging("zclDecoder", "Debug", "buildframe_0400_cmd - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data), SrcNwkId)

    # Zone Enroll Response
    enroll_response_code = Data[:2]
    zone_id = Data[2:4]
    buildPayload = Sqn + SrcNwkId + SrcEndPoint + enroll_response_code + zone_id
    return encapsulate_plugin_frame(MsgType, buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_8400_cmd(self, MsgType, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Command, Data):
    # IAS Zone Enroll request
    self.log.logging("zclDecoder", "Debug", "buildframe_8400_cmd - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data), SrcNwkId)
    zonetype = decode_endian_data( Data[:4], '31')
    ManufacturerCode = decode_endian_data( Data[4:8], '21' )
    buildPayload = Sqn + zonetype + ManufacturerCode + SrcNwkId + SrcEndPoint
    return encapsulate_plugin_frame(MsgType, buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_8401_cmd(self, MsgType, frame, Sqn, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, ManufacturerCode, Command, Data):
    self.log.logging("zclDecoder", "Debug", "buildframe_8401_cmd - %s %s %s Data: %s" % (SrcNwkId, SrcEndPoint, ClusterId, Data), SrcNwkId)
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
