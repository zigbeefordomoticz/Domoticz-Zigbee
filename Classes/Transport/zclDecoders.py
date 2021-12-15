# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz
import struct 
from Modules.tools import retreive_cmd_payload_from_8002
from Modules.zigateConsts import ADDRESS_MODE, SIZE_DATA_TYPE


def zcl_decoders( self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame):
    #self.logging_8002( 'Debug', "zcl_decoders NwkId: %s Ep: %s Cluster: %s Payload: %s" %(SrcNwkId, SrcEndPoint, ClusterId , Payload))

    if len(Payload) < 8:
        return frame

    GlobalCommand, Sqn, ManufacturerCode, Command, Data = retreive_cmd_payload_from_8002(Payload)
    if not GlobalCommand:
        # This is not a Global Command (Read Attribute, Write Attribute and so on)
        return frame

    # self.logging_8002( 'Debug', "decode8002_and_process Sqn: %s/%s ManufCode: %s Command: %s Data: %s " %(int(Sqn,16), Sqn , ManufacturerCode, Command, Data))
    if Command == "00":  # Read Attribute
        return buildframe_read_attribute_request(frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, ManufacturerCode, Data)

    if Command == "01":  # Read Attribute response
        return buildframe_read_attribute_response(frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data)

    if Command == "02":  # Write Attributes
        return buildframe_write_attribute_request(frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, ManufacturerCode, Data)
 
    if Command == "04":  # Write Attribute response
        return buildframe_write_attribute_response(frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data)

    if Command == "06":  # Configure Reporting
        return frame

    if Command == "07":  # Configure Reporting Response
        return buildframe_configure_reporting_response(frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data)

    if Command == "0a":  # Report attributes
        return buildframe_report_attribute_response(frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data)
    
    if Command == "0b":  #
        return frame

    if Command == "0d":  # Discover Attributes Response
        return buildframe_discover_attribute_response(frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data)

    #self.logging_8002(
    #    "Log",
    #    "decode8002_and_process Unknown Command: %s NwkId: %s Ep: %s Cluster: %s Payload: %s - GlobalCommand: %s, Sqn: %s, ManufacturerCode: %s"
    #    % (
    #        Command,
    #        SrcNwkId,
    #        SrcEndPoint,
    #        ClusterId,
    #        Data,
    #        GlobalCommand,
    #        Sqn,
    #        ManufacturerCode,
    #    ),
    #)

    return frame



def buildframe_discover_attribute_response(frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data):
    
    # Domoticz.Log("buildframe_discover_attribute_response - Data: %s" %Data)
    discovery_complete = Data[0:2]
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
    # Domoticz.Log("buildframe_discover_attribute_response - %s   %s %s %s %s %s" %(
    #    discovery_complete , Attribute_type , Attribute ,SrcNwkId , SrcEndPoint , ClusterId))
    newFrame = "01"  # 0:2
    newFrame += "8140"  # 2:6   MsgType
    newFrame += "%4x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame


def buildframe_read_attribute_request(frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, ManufacturerCode, Data):

    if len(Data) % 4 != 0:
        # Domoticz.Log("Most Likely Livolo Frame : %s (%s)" %(Data, len(Data)))
        return frame

    ManufSpec = "00"
    ManufCode = "0000"
    if ManufacturerCode:
        ManufSpec = "01"
        ManufCode = ManufacturerCode

    buildPayload = Sqn + SrcNwkId + SrcEndPoint + "01" + ClusterId + "01" + ManufSpec + ManufCode
    idx = nbAttribute = 0
    payloadOfAttributes = ""
    while idx < len(Data):
        nbAttribute += 1
        Attribute = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[idx : idx + 4], 16)))[0]
        idx += 4
        payloadOfAttributes += Attribute

    buildPayload += "%02x" % (nbAttribute) + payloadOfAttributes
    newFrame = "01"  # 0:2
    newFrame += "0100"  # 2:6   MsgType
    newFrame += "%4x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame


def buildframe_write_attribute_request(frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, ManufacturerCode, Data):
    
    ManufSpec = "00"
    ManufCode = "0000"
    if ManufacturerCode:
        ManufSpec = "01"
        ManufCode = ManufacturerCode

    buildPayload = Sqn + SrcNwkId + SrcEndPoint + "01" + ClusterId + "01" + ManufSpec + ManufCode
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
        elif DType in ( "48", "4c"):
            nbElement = Data[idx + 2 : idx + 4] + Data[idx : idx + 2]
            idx += 4
            # Today found for attribute 0xff02 Xiaomi, just take all data
            size = len(Data) - idx

        elif DType in ("41", "42"):  # ZigBee_OctedString = 0x41, ZigBee_CharacterString = 0x42
            size = int(Data[idx : idx + 2], 16) * 2
            idx += 2
        else:
            Domoticz.Error(
                "buildframe_read_attribute_response - Unknown DataType size: >%s< vs. %s "
                % (DType, str(SIZE_DATA_TYPE))
            )
            Domoticz.Error(
                "buildframe_read_attribute_response - ClusterId: %s Attribute: %s Data: %s"
                % (ClusterId, Attribute, Data)
            )
            return frame

        data = Data[idx : idx + size]
        idx += size
        value = decode_endian_data(data, DType)
        lenData = "%04x" % (size // 2)
        payloadOfAttributes += Attribute +  DType + lenData + value

    buildPayload += "%02x" % (nbAttribute) + payloadOfAttributes
    newFrame = "01"  # 0:2
    newFrame += "0110"  # 2:6   MsgType - Write Attribute request
    newFrame += "%4x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame

    
    
def buildframe_write_attribute_response(frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data):

    # This is based on assumption that we only Write 1 attribute at a time
    buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId + "0000" + Data
    newFrame = "01"  # 0:2
    newFrame += "8110"  # 2:6   MsgType
    newFrame += "%4x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame


def decode_endian_data(data, datatype):
    if datatype in ("10", "18", "20", "28", "30"):
        return data

    if datatype in ("09", "19", "21", "29", "31"):
        return "%04x" % struct.unpack(">H", struct.pack("H", int(data, 16)))[0]

    if datatype in ("22", "2a"):
        return "%06x" % struct.unpack(">I", struct.pack("I", int(data, 16)))[0]

    if datatype in ("23", "2b", "39"):
        return "%08x" % struct.unpack(">i", struct.pack("I", int(data, 16)))[0]

    if datatype in ("00", "41", "42", "4c", "48"):
        return data

    return data


def buildframe_read_attribute_response(frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data):

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
            elif DType in ( "48", "4c"):
                nbElement = Data[idx + 2 : idx + 4] + Data[idx : idx + 2]
                idx += 4
                # Today found for attribute 0xff02 Xiaomi, just take all data
                size = len(Data) - idx

            elif DType in ("41", "42"):  # ZigBee_OctedString = 0x41, ZigBee_CharacterString = 0x42
                size = int(Data[idx : idx + 2], 16) * 2
                idx += 2
            else:
                Domoticz.Error(
                    "buildframe_read_attribute_response - Unknown DataType size: >%s< vs. %s "
                    % (DType, str(SIZE_DATA_TYPE))
                )
                Domoticz.Error(
                    "buildframe_read_attribute_response - ClusterId: %s Attribute: %s Data: %s"
                    % (ClusterId, Attribute, Data)
                )
                return frame

            data = Data[idx : idx + size]
            idx += size
            value = decode_endian_data(data, DType)
            lenData = "%04x" % (size // 2)
            buildPayload += Attribute + Status + DType + lenData + value
        else:
            # Status != 0x00
            buildPayload += Attribute + Status

    newFrame = "01"  # 0:2
    newFrame += "8100"  # 2:6   MsgType
    newFrame += "%4x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame


def buildframe_report_attribute_response(frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data):
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

        elif DType in ( "48", "4c"):
            # Today found for attribute 0xff02 Xiaomi, just take all data
            nbElement = Data[idx + 2 : idx + 4] + Data[idx : idx + 2]
            idx += 4
            size = len(Data) - idx

        elif DType in ("41", "42"):  # ZigBee_OctedString = 0x41, ZigBee_CharacterString = 0x42
            size = int(Data[idx : idx + 2], 16) * 2
            idx += 2

        elif DType == "00":
            Domoticz.Error(
                "buildframe_report_attribute_response %s/%s Cluster: %s nbAttribute: %s Attribute: %s DType: %s idx: %s frame: %s"
                % (SrcNwkId, SrcEndPoint, ClusterId, nbAttribute, Attribute, DType, idx, frame)
            )
            return frame

        else:
            Domoticz.Error(
                "buildframe_report_attribute_response - Unknown DataType size: >%s< vs. %s "
                % (DType, str(SIZE_DATA_TYPE))
            )
            Domoticz.Error(
                "buildframe_report_attribute_response - NwkId: %s ClusterId: %s Attribute: %s Frame: %s"
                % (SrcNwkId, ClusterId, Attribute, frame)
            )
            return frame

        data = Data[idx : idx + size]
        idx += size
        value = decode_endian_data(data, DType)
        lenData = "%04x" % (size // 2)
        buildPayload += Attribute + "00" + DType + lenData + value

    newFrame = "01"  # 0:2
    newFrame += "8102"  # 2:6   MsgType
    newFrame += "%4x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame


def buildframe_configure_reporting_response(frame, Sqn, SrcNwkId, SrcEndPoint, ClusterId, Data):

    if len(Data) == 2:
        nbAttribute = 1
        buildPayload = Sqn + SrcNwkId + SrcEndPoint + ClusterId + Data
    else:
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
        return frame

    newFrame = "01"  # 0:2
    newFrame += "8120"  # 2:6   MsgType
    newFrame += "%4x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame
