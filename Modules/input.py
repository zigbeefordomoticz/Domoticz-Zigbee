#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_input.py

    Description: manage inputs from Zigate

"""

import binascii
import struct
import time
from datetime import datetime

import Domoticz
from Classes.ZigateTransport.sqnMgmt import (TYPE_APP_ZCL, TYPE_APP_ZDP,
                                             sqn_get_internal_sqn_from_app_sqn,
                                             sqn_get_internal_sqn_from_aps_sqn)
from Zigbee.decode8002 import decode8002_and_process

from Modules.basicInputs import read_attribute_response
from Modules.basicOutputs import (getListofAttribute, send_default_response,
                                  setTimeServer, unknown_device_nwkid)
from Modules.callback import callbackDeviceAwake
from Modules.deviceAnnoucement import device_annoucementv2
from Modules.domoMaj import MajDomoDevice
from Modules.domoTools import lastSeenUpdate, timedOutDevice
from Modules.errorCodes import DisplayStatusCode
from Modules.ikeaTradfri import (ikea_motion_sensor_8095,
                                 ikea_remote_control_8085,
                                 ikea_remote_control_8095,
                                 ikea_remote_switch_8085,
                                 ikea_remote_switch_8095,
                                 ikea_wireless_dimer_8085)
from Modules.inRawAps import inRawAps
from Modules.legrand_netatmo import (legrand_motion_8085, legrand_motion_8095,
                                     legrand_remote_switch_8085,
                                     legrand_remote_switch_8095,
                                     rejoin_legrand_reset)
from Modules.livolo import livolo_read_attribute_request
from Modules.lumi import AqaraOppleDecoding
from Modules.mgmt_rtg import mgmt_rtg_rsp
from Modules.pairingProcess import interview_state_8045, request_next_Ep
from Modules.pluzzy import pluzzyDecode8102
from Modules.readClusters import ReadCluster
from Modules.schneider_wiser import wiser_read_attribute_request
from Modules.sendZigateCommand import raw_APS_request
from Modules.timeServer import timeserver_read_attribute_request
from Modules.tools import (DeviceExist, ReArrangeMacCapaBasedOnModel,
                           checkAndStoreAttributeValue, decodeMacCapa,
                           extract_info_from_8085, get_isqn_datastruct,
                           get_list_isqn_attr_datastruct, getSaddrfromIEEE,
                           is_fake_ep, loggingMessages, lookupForIEEE,
                           mainPoweredDevice, retreive_cmd_payload_from_8002,
                           set_request_phase_datastruct, set_status_datastruct,
                           timeStamped, updLQI, updSQN)
from Modules.zigateConsts import (ADDRESS_MODE, LEGRAND_REMOTE_MOTION,
                                  LEGRAND_REMOTE_SWITCHS, ZCL_CLUSTERS_LIST, ZIGATE_EP,
                                  ZIGBEE_COMMAND_IDENTIFIER)
from Modules.zigbeeController import (initLODZigate, receiveZigateEpDescriptor,
                                      receiveZigateEpList)
from Modules.zigbeeVersionTable import FIRMWARE_BRANCH
from Zigbee.zclCommands import zcl_ias_zone_enroll_response
from Modules.zigbeeVersionTable import set_display_firmware_version


def ZigateRead(self, Devices, Data):

    DECODERS = {
        "004d": Decode004D,
        "0040": Decode0040,
        "0041": Decode0041,
        "0042": Decode0042,
        "0100": Decode0100,
        "0110": Decode0110,
        "0302": Decode0302,
        "0400": Decode0400,
        "8000": Decode8000_v2,
        "8002": Decode8002,
        "8003": Decode8003,
        "8004": Decode8004,
        "8005": Decode8005,
        "8006": Decode8006,
        "8007": Decode8007,
        "8008": Decode8008,
        "8009": Decode8009,
        "8010": Decode8010,
        # "8011": Decode8011,
        "8014": Decode8014,
        "8015": Decode8015,
        "8017": Decode8017,
        "8024": Decode8024,
        "8028": Decode8028,
        "802b": Decode802B,
        "802c": Decode802C,
        "8030": Decode8030,
        "8031": Decode8031,
        "8034": Decode8034,
        "8040": Decode8040,
        "8041": Decode8041,
        "8042": Decode8042,
        "8043": Decode8043,
        "8044": Decode8044,
        "8045": Decode8045,
        "8046": Decode8046,
        "8047": Decode8047,
        "8048": Decode8048,
        "8049": Decode8049,
        "804a": Decode804A,
        "804b": Decode804B,
        "804e": Decode804E,
        "8060": Decode8060,
        "8061": Decode8061,
        "8062": Decode8062,
        "8063": Decode8063,
        "8085": Decode8085,
        "8095": Decode8095,
        "80a6": Decode80A6,
        "80a7": Decode80A7,
        "8100": Decode8100,
        "8101": Decode8101,
        "8102": Decode8102,
        "8110": Decode8110,
        "8120": Decode8120,
        "8122": Decode8122,
        "8139": Decode8140,
        "8140": Decode8140,
        "8400": Decode8400,
        "8401": Decode8401,
        "8501": Decode8501,
        "8503": Decode8503,
        "8701": Decode8701,
        "8806": Decode8806,
        "8807": Decode8807,
        "7000": Decode7000,
    }
    # Not used
    # NOT_IMPLEMENTED = ("00d1", "8029", "80a0", "80a1", "80a2", "80a3", "80a4")

    # self.log.logging( "Input", 'Debug', "ZigateRead - decoded data: " + Data + " lenght: " + str(len(Data)) )

    if Data is None:
       return

    FrameStart = Data[0:2]
    FrameStop = Data[len(Data) - 2 : len(Data)]
    if FrameStart != "01" and FrameStop != "03":
        Domoticz.Error(
            "ZigateRead received a non-zigate frame Data: "
            + str(Data)
            + " FS/FS = "
            + str(FrameStart)
            + "/"
            + str(FrameStop)
        )
        return


    MsgType, MsgData, MsgLQI = extract_messge_infos( Data)
    self.Ping["Nb Ticks"] = 0  # We receive a valid packet 
    
    self.log.logging(
        "Input",
        "Debug",
        "ZigateRead - MsgType: %s,  Data: %s, LQI: %s" % (MsgType, MsgData, int(MsgLQI, 16)),
    )

    if MsgType == "8002":
        # Let's try to see if we can decode it, and then get a new MsgType
        decoded_frame = decode8002_and_process( self, Data)
        if decoded_frame is None:
            return
        MsgType, MsgData, MsgLQI = extract_messge_infos( decoded_frame)

    if MsgType in DECODERS:
        _decoding = DECODERS[MsgType]
        _decoding(self, Devices, MsgData, MsgLQI)
        
    elif MsgType == "8002":
        Decode8002(self, Devices, Data, MsgData, MsgLQI)
        
    elif MsgType == "8011":
        Decode8011(self, Devices, MsgData, MsgLQI)
        
    else:
        self.log.logging(
            "Input",
            "Error",
            "ZigateRead - Decoder not found for %s" % (MsgType),
        )

def extract_messge_infos( Data):
    FrameStart = Data[:2]
    FrameStop = Data[len(Data) - 2 : len(Data)]
    if FrameStart != "01" and FrameStop != "03":
        Domoticz.Error("ZigateRead received a non-zigate frame Data: " + str(Data) + " FS/FS = " + str(FrameStart) + "/" + str(FrameStop))
        return None, None, None
    MsgType = Data[2:6]
    MsgType = MsgType.lower()
    #MsgLength = Data[6:10]
    #MsgCRC = Data[10:12]
    if len(Data) > 12:
        # We have Payload: data + rssi
        MsgData = Data[12 : len(Data) - 4]
        MsgLQI = Data[len(Data) - 4 : len(Data) - 2]
    else:
        MsgData = ""
        MsgLQI = "00"
    return MsgType, MsgData, MsgLQI

def Decode0040(self, Devices, MsgData, MsgLQI):  # NWK_addr_req
    self.log.logging("Input", "Log", "Decode0040 - NWK_addr_req: %s" % MsgData)
    # sqn + ieee + u8RequestType + u8StartIndex
    sqn = MsgData[:2]
    srcNwkId = MsgData[2:6]
    srcEp = MsgData[6:8]
    ieee = MsgData[8:24]
    reqType = MsgData[24:26]
    startIndex = MsgData[26:28]
    
    controller_ieee = "%016x" % struct.unpack("Q", struct.pack(">Q", int(self.ControllerIEEE, 16)))[0]
    controller_nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(self.ControllerNWKID, 16)))[0]
    # we should answer: sqn + status + ieee + nwkid + NumAssocDev + StartIndex + NWKAddrAssocDevList
    Cluster = "8000"
    if ieee == self.ControllerIEEE:
        status = "00"
        payload = sqn + status + controller_ieee + controller_nwkid + "00"
    else:
        status = "81"  # Device not found
        payload = sqn + status + ieee
    self.log.logging("Input", "Log", "Decode0040 - response payload: %s" %payload)
    raw_APS_request( self, srcNwkId, "00", Cluster, "0000", payload, zigpyzqn=sqn, zigate_ep="00", )
    

def Decode0041(self, Devices, MsgData, MsgLQI):  # IEEE_addr_req
    self.log.logging("Input", "Log", "Decode0041 - IEEE_addr_req: %s" % MsgData)
    # sqn + nwkid + u8RequestType + u8StartIndex
    sqn = MsgData[:2]
    srcNwkId = MsgData[2:6]
    srcEp = MsgData[6:8]
    nwkid = MsgData[8:12]
    reqType = MsgData[12:14]
    startIndex = MsgData[14:16]
    
    # we should answer: sqn + status + ieee + nwkid + NumAssocDev + StartIndex + NWKAddrAssocDevList
    Cluster = "8001"
    if nwkid == self.ControllerNWKID:
        status = "00"
        controller_ieee = "%016x" % struct.unpack("Q", struct.pack(">Q", int(self.ControllerIEEE, 16)))[0]
        controller_nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(self.ControllerNWKID, 16)))[0]
        payload = sqn + status + controller_ieee + controller_nwkid + "00"
    else:
        status = "81"  # Device not found
        payload = sqn + status + srcNwkId
    raw_APS_request( self, srcNwkId, "00", Cluster, "0000", payload, zigpyzqn=sqn, zigate_ep="00", )
    self.log.logging("Input", "Log", "Decode0041 - response payload: %s" %payload)

    
def Decode0042(self, Devices, MsgData, MsgLQI):  # Node_Desc_req
    self.log.logging("Input", "Log", "Decode0042 - Node_Desc_req: %s" % MsgData)
    #  sqn + SrcNwkId + SrcEndPoint + nwkid
    #  01 / 0012/ 4b0021600542000000
    sqn = MsgData[:2]
    srcNwkId = MsgData[2:6]
    srcEp = MsgData[6:8]
    nwkid = MsgData[8:12]

    # we should answer:
    # buildPayload = sqn + status + nwkid + manuf_code_16 + max_in_size_16 + max_out_size_16
    # buildPayload += server_mask_16 + descriptor_capability_field_8 + mac_capa_8 + max_buf_size_8 + bitfield_16
    Cluster = "8002"
    if nwkid != "0000":
        status = "80"  # Invalid request Type
        payload = sqn + status + nwkid
            
    elif "0000" not in self.ListOfDevices:
        status = "81"  # Device not found
        payload = sqn + status + nwkid
        
    elif "Manufacturer" not in self.ListOfDevices[ "0000" ]:
        status = "89"  # No Descriptor
        payload = sqn + status + nwkid
    
    else:
        status = "00"
        controllerManufacturerCode = self.ListOfDevices[ "0000" ]["Manufacturer"]
        controllerManufacturerCode = '0007'
        self.log.logging("Input", "Log", "Decode0042 - Overwrite Manuf Code: %s" % controllerManufacturerCode)
        
        manuf_code16 = "%04x" % struct.unpack("H", struct.pack(">H", int(controllerManufacturerCode, 16)))[0]
        max_in_size16 = "%04x" % struct.unpack("H", struct.pack(">H", int(self.ListOfDevices[ "0000" ]["Max Rx"], 16)))[0] 
        max_out_size16 = "%04x" % struct.unpack("H", struct.pack(">H", int(self.ListOfDevices[ "0000" ]["Max Tx"], 16)))[0] 
        server_mask16 = "%04x" % struct.unpack("H", struct.pack(">H", int(self.ListOfDevices[ "0000" ]["server_mask"], 16)))[0]
        descriptor_capability8 = self.ListOfDevices[ "0000" ]["descriptor_capability"]
        mac_capa8 = self.ListOfDevices[ "0000" ]["macapa"]
        max_buf_size8 = self.ListOfDevices[ "0000" ]["Max Buffer Size"]
        bitfield16 = "%04x" % struct.unpack("H", struct.pack(">H", int(self.ListOfDevices[ "0000" ]["bitfield"], 16)))[0]
        
        payload = sqn + status + nwkid + manuf_code16 + max_in_size16 + max_out_size16 + server_mask16 + descriptor_capability8
        payload += mac_capa8 + max_buf_size8 + bitfield16
    self.log.logging("Input", "Log", "Decode0042 - response payload: %s" %payload)
    raw_APS_request( self, srcNwkId, "00", Cluster, "0000", payload, zigpyzqn=sqn, zigate_ep="00", )
    
def Decode0100(self, Devices, MsgData, MsgLQI):  # Read Attribute request

    MsgSqn = MsgData[:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSrcEp = MsgData[6:8]
    MsgDstEp = MsgData[8:10]

    updLQI(self, MsgSrcAddr, MsgLQI)
    timeStamped(self, MsgSrcAddr, 0x0100)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)

    if MsgSrcAddr not in self.ListOfDevices:
        return

    # Livolo case, where livolo provide Switch status update via a Malformed read Attribute request
    if ("Model" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Model"] == "TI0001") or (
        "Manufacturer Name" in self.ListOfDevices[MsgSrcAddr]
        and self.ListOfDevices[MsgSrcAddr]["Manufacturer Name"] == "LIVOLO"
    ):
        self.log.logging(
            "Input",
            "Debug",
            "Decode0100 - (Livolo) Read Attribute Request %s/%s Data %s" % (MsgSrcAddr, MsgSrcEp, MsgData),
        )
        livolo_read_attribute_request(self, Devices, MsgSrcAddr, MsgSrcEp, MsgData[30:32])
        return

    # Handling the Standard Read Attribute Request
    MsgClusterId = MsgData[10:14]
    MsgDirection = MsgData[14:16]
    MsgManufSpec = MsgData[16:18]
    MsgManufCode = MsgData[18:22]
    nbAttribute = MsgData[22:24]

    self.log.logging(
        "Input",
        "Debug",
        "Decode0100 - Mode: %s NwkId: %s SrcEP: %s DstEp: %s ClusterId: %s Direction: %s ManufSpec: %s ManufCode: %s nbAttribute: %s"
        % (
            MsgSqn,
            MsgSrcAddr,
            MsgSrcEp,
            MsgDstEp,
            MsgClusterId,
            MsgDirection,
            MsgManufSpec,
            MsgManufCode,
            nbAttribute,
        ),
    )

    updSQN(self, MsgSrcAddr, MsgSqn)
    manuf = manuf_name = ""
    # model = ""
    # if "Model" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Model"] not in ("", {}):
    #     model = self.ListOfDevices[MsgSrcAddr]["Model"]
    if "Manufacturer Name" in self.ListOfDevices[MsgSrcAddr]:
        manuf_name = self.ListOfDevices[MsgSrcAddr]["Manufacturer Name"]
    if "Manufacturer" in self.ListOfDevices[MsgSrcAddr]:
        manuf = self.ListOfDevices[MsgSrcAddr]["Manufacturer"]

    for idx in range(24, len(MsgData), 4):
        Attribute = MsgData[idx : idx + 4]
        if MsgClusterId == "000a":
            # Cluster TimeServer
            self.log.logging(
                "Input",
                "Debug",
                "Decode0100 - Received Time Server Cluster %s/%s Idx: %s  Attribute: %s"
                % (MsgSrcAddr, MsgSrcEp, idx, Attribute),
            )
            timeserver_read_attribute_request(
                self,
                MsgSqn,
                MsgSrcAddr,
                MsgSrcEp,
                MsgClusterId,
                MsgManufSpec,
                MsgManufCode,
                Attribute,
            )

        elif MsgClusterId == "0201" and (
            manuf == "105e" or manuf_name == "Schneider" or manuf_name == "Schneider Electric"
        ):
            # Cluster Thermostat for Wiser
            wiser_read_attribute_request(self, MsgSrcAddr, MsgSrcEp, MsgSqn, MsgClusterId, Attribute)
            self.log.logging(
                "Schneider",
                "Debug",
                "Decode0100 - Mode: %s NwkId: %s SrcEP: %s DstEp: %s ClusterId: %s Direction: %s ManufSpec: %s ManufCode: %s nbAttribute: %s"
                % (
                    MsgSqn,
                    MsgSrcAddr,
                    MsgSrcEp,
                    MsgDstEp,
                    MsgClusterId,
                    MsgDirection,
                    MsgManufSpec,
                    MsgManufCode,
                    nbAttribute,
                ),
            )
        if MsgClusterId == "0000" and Attribute == "f000" and manuf_name in ("1021", "Legrand" ):
            if self.pluginconf.pluginConf["LegrandCompatibilityMode"]:
                operation_time = time() - self.statistics._start
                read_attribute_response(self, MsgSrcAddr, MsgSrcEp, MsgSqn, MsgClusterId, "00", "23", Attribute, operation_time, manuf_code=MsgManufCode)
        else:
            self.log.logging(
                "Input",
                "Log",
                "Decode0100 - Read Attribute Request %s/%s Cluster %s Attribute %s"
                % (MsgSrcAddr, MsgSrcEp, MsgClusterId, Attribute),
            )


def Decode0110(self, Devices, MsgData, MsgLQI):  # Write Attribute request

    self.log.logging("Input", "Log", "Decode0110 - message: %s" % MsgData)
    MsgSqn = MsgData[0:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSrcEp = MsgData[6:8]
    MsgDstEp = MsgData[8:10]
    MsgClusterId = MsgData[10:14]
    MsgDirection = MsgData[14:16]
    MsgManufFlag = MsgData[16:18]
    MsgManufCode = MsgData[18:22]
    nbAttribute = MsgData[22:24]

    updLQI(self, MsgSrcAddr, MsgLQI)
    timeStamped(self, MsgSrcAddr, 0x0110)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)

    for idx in range(24, len(MsgData), 4):
        Attribute = MsgData[idx : idx + 4]
        idx += 4
        DataType = MsgData[idx : idx + 2]
        idx += 2
        lendata = MsgData[idx : idx + 4]
        idx += 4
        DataValue = MsgData[idx : idx + int(lendata) * 2]

        self.log.logging(
            "Input",
            "Log",
            "Decode0110 - Sqn: %s NwkId: %s Ep: %s Cluster: %s Manuf: %s Attribute: %s Type: %s Value: %s"
            % (MsgSqn, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgManufCode, Attribute, DataType, DataValue),
        )


def Decode0302(self, Devices, MsgData, MsgLQI):  # PDM Load

    # Must be sent above in order to issue a rejoin_legrand_reset() if needed
    self.log.logging("Input", "Debug", "Decode0302 - PDM Load")
    rejoin_legrand_reset(self)


def Decode0400(self, Devices, MsgData, MsgLQI):  # Enrolment Request Response

    self.log.logging("Input", "Log", "Decode0400 - message: %s" % MsgData)
    # 02 0000 01 01 00 00
    # 02 0000 04 01 00 00
    # 02 426b 04 01 00 5c
    if len(MsgData) != 14:
        return

    # Enrolment Request Response
    sqn = MsgData[0:2]
    SrcAddress = MsgData[2:6]
    SrcEndPoint = MsgData[6:8]
    EnrollResponseCode = MsgData[10:12]
    ZoneId = MsgData[12:14]

    self.log.logging(
        "Input",
        "Log",
        "Decode0400 - Source Address: %s Source Ep: %s EnrollmentResponseCode: %s ZoneId: %s"
        % (SrcAddress, SrcEndPoint, EnrollResponseCode, ZoneId),
    )

    if self.iaszonemgt:
        self.iaszonemgt.receiveIASenrollmentRequestResponse(SrcAddress, SrcEndPoint, EnrollResponseCode, ZoneId)


# Responses
def Decode8000_v2(self, Devices, MsgData, MsgLQI):  # Status

    if len(MsgData) < 8:
        self.log.logging("Input", "Log", "Decode8000 - uncomplete message: %s" % MsgData)
        return

    Status = MsgData[0:2]
    sqn_app = MsgData[2:4]
    dsqn_app = int(sqn_app, 16)
    PacketType = MsgData[4:8]
    type_sqn = sqn_aps = None
    dsqn_aps = 0
    npdu = apdu = None

    if len(MsgData) >= 12:
        # New Firmware 3.1d (get aps sqn)
        type_sqn = MsgData[8:10]
        sqn_aps = MsgData[10:12]
        dsqn_aps = int(sqn_aps, 16)
        if len(MsgData) == 16:
            # Debuging infos
            npdu = MsgData[12:14]
            apdu = MsgData[14:16]

    if self.pluginconf.pluginConf["debugzigateCmd"]:
        i_sqn = None
        if PacketType in ("0100", "0120", "0110"):
            i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, sqn_app, TYPE_APP_ZCL)

        if i_sqn:
            self.log.logging(
                "Input",
                "Log",
                "Decod8000 Received         [%s] PacketType:  %s TypeSqn: %s sqn_app: %s/%s sqn_aps: %s/%s Status: [%s] npdu: %s apdu: %s "
                % (i_sqn, PacketType, type_sqn, sqn_app, dsqn_app, sqn_aps, dsqn_aps, Status, npdu, apdu),
            )
        else:
            self.log.logging(
                "Input",
                "Log",
                "Decod8000 Received         [  ] PacketType:  %s TypeSqn: %s sqn_app: %s/%s sqn_aps: %s/%s Status: [%s] npdu: %s apdu: %s "
                % (PacketType, type_sqn, sqn_app, dsqn_app, sqn_aps, dsqn_aps, Status, npdu, apdu),
            )

    STATUS_CODE = {
        "00": "Success",
        "01": "Incorrect Parameters",
        "02": "Unhandled Command",
        "03": "Command Failed",
        "04": "Busy",
        "05": "Stack Already Started",
        "14": "E_ZCL_ERR_ZBUFFER_FAIL",
        "15": "E_ZCL_ERR_ZTRANSMIT_FAIL",
    }

    if Status in STATUS_CODE:
        Status = STATUS_CODE[Status]
    elif int(Status, 16) >= 128 and int(Status, 16) <= 244:
        Status = "ZigBee Error Code " + DisplayStatusCode(Status)

    # Handling PacketType
    SPECIFIC_PACKET_TYPE = {
        "0012": "Erase Persistent Data cmd status",
        "0024": "Start Network status",
        "0026": "Remove Device cmd status",
        "0044": "request Power Descriptor status",
    }
    if PacketType in SPECIFIC_PACKET_TYPE:
        self.log.logging("Input", "Log", SPECIFIC_PACKET_TYPE[PacketType] + Status)

    # if PacketType == "0012":
    #    # Let's trigget a zigate_Start
    #    # self.startZigateNeeded = self.HeartbeatCount
    #    # if self.HeartbeatCount == 0:
    #    #    self.startZigateNeeded = 1
    #    pass

    # Group Management
    if PacketType in ("0060", "0061", "0062", "0063", "0064", "0065") and self.groupmgt:
        self.groupmgt.statusGroupRequest(MsgData)

    if MsgData[0:2] != "00":
        self.log.logging(
            "Input",
            "Error",
            "Decode8000 - PacketType: %s TypeSqn: %s sqn_app: %s sqn_aps: %s Status: [%s] "
            % (PacketType, type_sqn, sqn_app, sqn_aps, Status),
        )
        # Hack to reboot Zigate
        if MsgData[0:2] not in ("01", "02", "03", "04", "05"):
            self.internalError += 1
            # if self.internalError > 4:
            #    self.internalError = 0
            #    sendZigateCmd(self, "0011", "" ) # Software Reset
            #    zigate_soft_reset(self)
            #    self.log.logging(  "Input", "Error", "TOO MUCH ERRORS - ZIGATE RESET requested")
    else:
        self.internalError = 0


def Decode8001(self, Decode, MsgData, MsgLQI):  # Reception log Level

    LOG_FILE = "ZiGate"

    MsgLogLvl = MsgData[0:2]
    log_message = binascii.unhexlify(MsgData[2:]).decode("utf-8")
    logfilename = (
        self.pluginconf.pluginConf["pluginLogs"] + "/" + LOG_FILE + "_" + "%02d" % self.HardwareID + "_" + ".log"
    )
    try:

        with open(logfilename, "at", encoding="utf-8") as file:
            try:
                file.write(
                    "%s %s %s" % (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]), MsgLogLvl, log_message)
                    + "\n"
                )
            except IOError:
                Domoticz.Error("Error while writing to ZiGate log file %s" % logfilename)
    except IOError:
        Domoticz.Error("Error while Opening ZiGate log file %s" % logfilename)

    
    

def Decode8002(self, Devices, MsgData, MsgLQI):  # Data indication
    # MsgLogLvl = MsgData[0:2]
    MsgProfilID = MsgData[2:6]
    MsgClusterID = MsgData[6:10]
    MsgSourcePoint = MsgData[10:12]
    MsgDestPoint = MsgData[12:14]
    MsgSourceAddressMode = MsgData[14:16]

    # Domoticz.Log("Decode8002 - MsgLogLvl: %s , MsgProfilID: %s, MsgClusterID: %s MsgSourcePoint: %s, MsgDestPoint: %s, MsgSourceAddressMode: %s" \
    #        %(MsgLogLvl, MsgProfilID, MsgClusterID, MsgSourcePoint, MsgDestPoint, MsgSourceAddressMode))

    if int(MsgSourceAddressMode, 16) in [
        ADDRESS_MODE["short"],
        ADDRESS_MODE["group"],
    ]:
        MsgSourceAddress = MsgData[16:20]  # uint16_t
        MsgDestinationAddressMode = MsgData[20:22]
        if int(MsgDestinationAddressMode, 16) in [
            ADDRESS_MODE["short"],
            ADDRESS_MODE["group"],
        ]:
            # Short Address
            MsgDestinationAddress = MsgData[22:26]  # uint16_t
            MsgPayload = MsgData[26 : len(MsgData)]

        elif int(MsgDestinationAddressMode, 16) == ADDRESS_MODE["ieee"]:  # uint32_t
            # IEEE
            MsgDestinationAddress = MsgData[22:38]  # uint32_t
            MsgPayload = MsgData[38 : len(MsgData)]

        else:
            self.log.logging(
                "Input",
                "Log",
                "Decode8002 - Unexpected Destination ADDR_MOD: %s, drop packet %s"
                % (MsgDestinationAddressMode, MsgData),
            )
            return

    elif int(MsgSourceAddressMode, 16) == ADDRESS_MODE["ieee"]:
        MsgSourceAddress = MsgData[16:32]  # uint32_t
        MsgDestinationAddressMode = MsgData[32:34]
        if int(MsgDestinationAddressMode, 16) in [
            ADDRESS_MODE["short"],
            ADDRESS_MODE["group"],
        ]:
            MsgDestinationAddress = MsgData[34:38]  # uint16_t
            MsgPayload = MsgData[38 : len(MsgData)]

        elif int(MsgDestinationAddressMode, 16) == ADDRESS_MODE["ieee"]:
            # IEEE
            MsgDestinationAddress = MsgData[34:40]  # uint32_t
            MsgPayload = MsgData[40 : len(MsgData)]
        else:
            self.log.logging(
                "Input",
                "Log",
                "Decode8002 - Unexpected Destination ADDR_MOD: %s, drop packet %s"
                % (MsgDestinationAddressMode, MsgData),
            )
            return

    else:
        self.log.logging(
            "Input",
            "Log",
            "Decode8002 - Unexpected Source ADDR_MOD: %s, drop packet %s" % (MsgSourceAddressMode, MsgData),
        )
        return

    self.log.logging(
        "Input",
        "Debug",
        "Reception Data indication, Source Address: "
        + MsgSourceAddress
        + " Destination Address: "
        + MsgDestinationAddress
        + " ProfilID: "
        + MsgProfilID
        + " ClusterID: "
        + MsgClusterID
        + " Message Payload: "
        + MsgPayload,
        MsgSourceAddress,
    )

    # Let's check if this is an Schneider related APS. In that case let's process
    srcnwkid = dstnwkid = None
    if len(MsgDestinationAddress) != 4:
        Domoticz.Error("not handling IEEE address")
        return

    srcnwkid = MsgSourceAddress
    dstnwkid = MsgDestinationAddress

    if srcnwkid not in self.ListOfDevices:
        self.log.logging(
            "Input",
            "Debug",
            "Decode8002 - Unknown NwkId: %s Ep: %s Cluster: %s Payload: %s" % (srcnwkid, MsgSourcePoint, MsgClusterID, MsgPayload),)
        return

    timeStamped(self, srcnwkid, 0x8002)
    lastSeenUpdate(self, Devices, NwkId=srcnwkid)
    updLQI(self, srcnwkid, MsgLQI)

    if MsgClusterID in ("8032", "8033"):
        # Routing table: Mgmt_Rtg_rsp
        mgmt_rtg_rsp(
            self,
            srcnwkid,
            MsgSourcePoint,
            MsgClusterID,
            dstnwkid,
            MsgDestPoint,
            MsgPayload,
        )
        return

    if MsgProfilID != "0104":
        # Not handle
        self.log.logging(
            "inRawAPS",
            "Debug",
            "Decode8002 - NwkId: %s Ep: %s Cluster: %s Payload: %s"
            % (srcnwkid, MsgSourcePoint, MsgClusterID, MsgPayload),
            srcnwkid,
        )
        return

    (
        GlobalCommand,
        Sqn,
        ManufacturerCode,
        Command,
        Data,
    ) = retreive_cmd_payload_from_8002(MsgPayload)

    if "SQN" in self.ListOfDevices[srcnwkid] and Sqn == self.ListOfDevices[srcnwkid]["SQN"]:
        self.log.logging(
            "inRawAPS",
            "Debug",
            "Decode8002 - Duplicate message drop NwkId: %s Ep: %s Cluster: %s GlobalCommand: %5s Command: %s Data: %s"
            % (
                srcnwkid,
                MsgSourcePoint,
                MsgClusterID,
                GlobalCommand,
                Command,
                Data,
            ),
            srcnwkid,
        )
        return

    updSQN(self, srcnwkid, Sqn)

    if GlobalCommand and int(Command, 16) in ZIGBEE_COMMAND_IDENTIFIER:
        self.log.logging(
            "inRawAPS",
            "Debug",
            "Decode8002 - NwkId: %s Ep: %s Cluster: %s GlobalCommand: %5s Command: %s (%33s) Data: %s"
            % (
                srcnwkid,
                MsgSourcePoint,
                MsgClusterID,
                GlobalCommand,
                Command,
                ZIGBEE_COMMAND_IDENTIFIER[int(Command, 16)],
                Data,
            ),
            srcnwkid,
        )
    else:
        self.log.logging(
            "inRawAPS",
            "Debug",
            "Decode8002 - NwkId: %s Ep: %s Cluster: %s GlobalCommand: %5s Command: %s Data: %s"
            % (
                srcnwkid,
                MsgSourcePoint,
                MsgClusterID,
                GlobalCommand,
                Command,
                Data,
            ),
            srcnwkid,
        )

    updLQI(self, srcnwkid, MsgLQI)

    if MsgClusterID == "0005" and MsgPayload[0:2] == "05":
        # Scene Control
        # 057c11630701010d00
        cmd = MsgPayload[8:10]
        direction = MsgPayload[10:12]

        data = Sqn + MsgSourcePoint + MsgClusterID + cmd + direction + "000000" + srcnwkid

        self.log.logging(
            "inRawAPS",
            "Debug",
            "Decode8002 - Sqn: %s NwkId %s Ep %s Cluster %s Cmd %s Direction %s"
            % (
                Sqn,
                srcnwkid,
                MsgClusterID,
                MsgClusterID,
                cmd,
                direction,
            ),
            srcnwkid,
        )
        Decode80A7(self, Devices, data, MsgLQI)
        return

    # Send for processing to the Brand specifics
    if "Manufacturer" not in self.ListOfDevices[srcnwkid] and "Manufacturer Name" not in self.ListOfDevices[srcnwkid]:
        return

    if (
        "Manufacturer" in self.ListOfDevices[srcnwkid]
        and self.ListOfDevices[srcnwkid]["Manufacturer"] in ("", {})
        and "Manufacturer Name" in self.ListOfDevices[srcnwkid]
        and self.ListOfDevices[srcnwkid]["Manufacturer Name"] in ("", {})
    ):
        return

    inRawAps(
        self,
        Devices,
        srcnwkid,
        MsgSourcePoint,
        MsgClusterID,
        dstnwkid,
        MsgDestPoint,
        Sqn,
        GlobalCommand,
        ManufacturerCode,
        Command,
        Data,
        MsgPayload,
    )
    callbackDeviceAwake(self, Devices, srcnwkid, MsgSourcePoint, MsgClusterID)


def Decode8003(self, Devices, MsgData, MsgLQI):  # Device cluster list
    # MsgLen = len(MsgData)

    MsgSourceEP = MsgData[0:2]
    MsgProfileID = MsgData[2:6]
    MsgClusterID = MsgData[6 : len(MsgData)]

    clusterLst = [MsgClusterID[idx : idx + 4] for idx in range(0, len(MsgClusterID), 4)]
    self.ControllerData["Cluster List"] = clusterLst
    self.log.logging(
        "Input",
        "Status",
        "Device Cluster list, EP source: "
        + MsgSourceEP
        + " ProfileID: "
        + MsgProfileID
        + " Cluster List: "
        + str(clusterLst),
    )


def Decode8004(self, Devices, MsgData, MsgLQI):  # Device attribut list
    # MsgLen = len(MsgData)

    MsgSourceEP = MsgData[0:2]
    MsgProfileID = MsgData[2:6]
    MsgClusterID = MsgData[6:10]
    MsgAttributList = MsgData[10 : len(MsgData)]

    attributeLst = [MsgAttributList[idx : idx + 4] for idx in range(0, len(MsgAttributList), 4)]

    self.ControllerData["Device Attributs List"] = attributeLst
    self.log.logging(
        "Input",
        "Status",
        "Device Attribut list, EP source: "
        + MsgSourceEP
        + " ProfileID: "
        + MsgProfileID
        + " ClusterID: "
        + MsgClusterID
        + " Attribut List: "
        + str(attributeLst),
    )


def Decode8005(self, Devices, MsgData, MsgLQI):  # Command list
    # MsgLen = len(MsgData)

    MsgSourceEP = MsgData[0:2]
    MsgProfileID = MsgData[2:6]
    MsgClusterID = MsgData[6:10]
    MsgCommandList = MsgData[10 : len(MsgData)]

    commandLst = [MsgCommandList[idx : idx + 4] for idx in range(0, len(MsgCommandList), 4)]

    self.ControllerData["Device Attributs List"] = commandLst
    self.log.logging(
        "Input",
        "Status",
        "Command list, EP source: "
        + MsgSourceEP
        + " ProfileID: "
        + MsgProfileID
        + " ClusterID: "
        + MsgClusterID
        + " Command List: "
        + str(commandLst),
    )


def Decode8006(self, Devices, MsgData, MsgLQI):  # Non “Factory new” Restart

    self.log.logging("Input", "Log", "Decode8006 - MsgData: %s" % (MsgData))

    Status = MsgData[0:2]
    if Status == "00":
        Status = "STARTUP"
    elif Status == "01" or Status != "02" and Status == "06":
        Status = "RUNNING"
    elif Status == "02":
        Status = "NFN_START"
    # self.startZigateNeeded = self.HeartbeatCount
    # if self.HeartbeatCount == 0:
    #    self.startZigateNeeded = 1
    self.log.logging("Input", "Status", "Non 'Factory new' Restart status: %s" % (Status))


def Decode8007(self, Devices, MsgData, MsgLQI):  # “Factory new” Restart

    self.log.logging("Input", "Debug", "Decode8007 - MsgData: %s" % (MsgData))

    Status = MsgData[0:2]
    if Status == "00":
        Status = "STARTUP"
    elif Status == "01" or Status != "02" and Status == "06":
        Status = "RUNNING"
    elif Status == "02":
        Status = "NFN_START"
    # self.startZigateNeeded = self.HeartbeatCount
    # if self.HeartbeatCount == 0:
    #    self.startZigateNeeded = 1
    self.log.logging("Input", "Status", "'Factory new' Restart status: %s" % (Status))


def Decode8008(self, Devices, MsgData, MsgLQI):  # ZiGate Heartbeat ( ZiGate V2 firmware 320)

    self.log.logging("Input", "Log", "Decode8008: heartbeat:" + MsgData)


def Decode8009(self, Devices, MsgData, MsgLQI):  # Network State response (Firm v3.0d)
    # MsgLen = len(MsgData)
    addr = MsgData[0:4]
    extaddr = MsgData[4:20]
    PanID = MsgData[20:24]
    extPanID = MsgData[24:40]
    Channel = MsgData[40:42]
    self.log.logging(
        "Input",
        "Debug",
        "Decode8009: Network state - Address:"
        + addr
        + " extaddr:"
        + extaddr
        + " PanID: "
        + PanID
        + " Channel: "
        + str(int(Channel, 16)),
    )

    if (
        "0000" in self.ListOfDevices
        and "CheckChannel" in self.ListOfDevices["0000"]
        and self.ListOfDevices["0000"]["CheckChannel"] != 0
    ):
        if self.ListOfDevices["0000"]["CheckChannel"] == int(Channel, 16):
            del self.ListOfDevices["0000"]["CheckChannel"]

    if self.ControllerIEEE != extaddr:
        # In order to update the first time
        self.adminWidgets.updateNotificationWidget(Devices, "Zigate IEEE: %s" % extaddr)

    self.pluginParameters["CoordinatorIEEE"] = extaddr
    self.ControllerIEEE = extaddr
    self.ControllerNWKID = addr

    if self.ControllerNWKID != "0000":
        Domoticz.Error("Zigate not correctly initialized")
        return

    # At that stage IEEE is set to 0x0000 which is correct for the Coordinator
    if extaddr not in self.IEEE2NWK and self.IEEE2NWK != addr:
        initLODZigate(self, addr, extaddr)

    if self.currentChannel != int(Channel, 16):
        self.adminWidgets.updateNotificationWidget(Devices, "Zigate Channel: %s" % str(int(Channel, 16)))

    # Let's check if this is a first initialisation, and then we need to update the Channel setting
    if (
        "startZigateNeeded" not in self.ControllerData
        and not self.startZigateNeeded
        and str(int(Channel, 16)) != self.pluginconf.pluginConf["channel"]
    ):
        Domoticz.Status(
            "Updating Channel in Plugin Configuration from: %s to: %s"
            % (self.pluginconf.pluginConf["channel"], int(Channel, 16))
        )
        self.pluginconf.pluginConf["channel"] = str(int(Channel, 16))
        self.pluginconf.write_Settings()

    self.currentChannel = int(Channel, 16)

    if self.iaszonemgt:
        # Domoticz.Log("Update IAS Zone - IEEE: %s" %extaddr)
        self.iaszonemgt.setZigateIEEE(extaddr)

    if self.groupmgt:
        self.groupmgt.updateZigateIEEE(extaddr)

    if self.webserver:
        self.webserver.setZigateIEEE(extaddr)

    self.log.logging(
        "Input",
        "Status",
        "Zigbee Coordinator ieee: %s , short addr: %s" % (self.ControllerIEEE, self.ControllerNWKID),
    )

    # from https://github.com/fairecasoimeme/ZiGate/issues/15 , if PanID == 0 -> Network is done
    if str(PanID) == "0":
        self.log.logging("Input", "Status", "Network state DOWN ! ")
        self.adminWidgets.updateNotificationWidget(Devices, "Network down PanID = 0")
        self.adminWidgets.updateStatusWidget(Devices, "No Connection")
    else:
        self.log.logging(
            "Input",
            "Status",
            "Network state UP, PANID: %s extPANID: 0x%s Channel: %s" % (PanID, extPanID, int(Channel, 16)),
        )

    self.ControllerData["IEEE"] = extaddr
    self.ControllerData["Short Address"] = addr
    self.ControllerData["Channel"] = int(Channel, 16)
    self.ControllerData["PANID"] = PanID
    self.ControllerData["Extended PANID"] = extPanID
    self.pluginParameters["CoordinatorIEEE"] = extaddr
    
def Decode8010(self, Devices, MsgData, MsgLQI):  # Reception Version list
    # MsgLen = len(MsgData)
    # 00 05 0321
    self.FirmwareBranch = MsgData[:2] 
       

    if '0000' not in self.ListOfDevices:
        self.ListOfDevices['0000'] = {}
    if 'Model' not in self.ListOfDevices[ '0000' ]:
        self.ListOfDevices[ '0000' ]['Model'] = {}
        
    self.log.logging("Input", "Debug", "Decode8010 - Reception Version list:%s Branch: %s Major: %s Version: %s" % (
        MsgData, self.FirmwareBranch, self.FirmwareMajorVersion, self.FirmwareVersion))
    
    if self.FirmwareBranch in FIRMWARE_BRANCH:
        if int(self.FirmwareBranch) == 99:
            self.log.logging("Input", "Error", "Untested Zigbee adapater model, please report to the Zigbee for Domoticz team")
            self.pluginParameters["CoordinatorModel"] = "Unknown model"
           
        elif int(self.FirmwareBranch) == 11:
            #Zigpy-Zigate
            self.FirmwareMajorVersion = MsgData[2:4]
            self.FirmwareVersion = MsgData[4:8]

            self.log.logging("Input", "Status", "%s" %FIRMWARE_BRANCH[ self.FirmwareBranch ])
            self.ControllerData["Controller firmware"] = FIRMWARE_BRANCH[ self.FirmwareBranch ]
            # the Build date is coded into "20" + "%02d" %int(FirmwareMajorVersion,16) + "%04d" %int(FirmwareVersion,16)
            if int(self.FirmwareMajorVersion,16) == 0x03:
                version =  "Zigpy-zigate, Zigate V1 (legacy) %04x" %( int(self.FirmwareVersion,16))
                self.pluginParameters["CoordinatorModel"] = "Zigate V1 (legacy)"
                self.pluginParameters["CoordinatorFirmwareVersion"] = "%04x" %( int(self.FirmwareVersion,16))
                
            elif int(self.FirmwareMajorVersion,16) == 0x04:
                version =  "Zigpy-zigate, Zigate V1 (OptiPDM) %04x" %( int(self.FirmwareVersion,16))
                self.pluginParameters["CoordinatorModel"] = "Zigate V1 (OptiPDM)"
                self.pluginParameters["CoordinatorFirmwareVersion"] = "%04x" %( int(self.FirmwareVersion,16))
                
            elif int(self.FirmwareMajorVersion,16) == 0x05:
                version =  "Zigpy-zigate, Zigate V2 %04x" %( int(self.FirmwareVersion,16))
                self.pluginParameters["CoordinatorModel"] = "Zigate V2"
                self.pluginParameters["CoordinatorFirmwareVersion"] = "%04x" %( int(self.FirmwareVersion,16))

            else:
                self.log.logging("Input", "Status", "%04x" %int(self.FirmwareMajorVersion,16))
                version =""

        elif int(self.FirmwareBranch) >= 20:
            # Zigpy-Znp
            if len(MsgData) > 8:
                self.FirmwareMajorVersion = MsgData[2:6]
                self.FirmwareVersion = MsgData[6:10]
            else:
                self.FirmwareMajorVersion = MsgData[2:4]
                self.FirmwareVersion = MsgData[4:8]

            self.log.logging("Input", "Status", "%s" %FIRMWARE_BRANCH[ self.FirmwareBranch ])
            # the Build date is coded into "20" + "%02d" %int(FirmwareMajorVersion,16) + "%04d" %int(FirmwareVersion,16)
            self.ListOfDevices[ '0000' ]['Model'] = FIRMWARE_BRANCH[ self.FirmwareBranch ]
            self.pluginParameters["CoordinatorModel"] = FIRMWARE_BRANCH[ self.FirmwareBranch ]
            self.pluginParameters["CoordinatorFirmwareVersion"] = "%04x" %( int(self.FirmwareVersion,16))

        # Zigate Native version
        elif self.FirmwareMajorVersion == "03":
            self.FirmwareMajorVersion = MsgData[2:4]
            self.FirmwareVersion = MsgData[4:8]

            self.log.logging("Input", "Status", "ZiGate Classic PDM (legacy)")
            self.ZiGateModel = 1
            self.ListOfDevices[ '0000' ]['Model'] = 'ZiGate Classic PDM (legacy)'
            self.pluginParameters["CoordinatorModel"] = 'ZiGate Classic PDM (legacy)'
            self.pluginParameters["CoordinatorFirmwareVersion"] = "%04x" %( int(self.FirmwareVersion,16))

        elif self.FirmwareMajorVersion == "04":
            self.FirmwareMajorVersion = MsgData[2:4]
            self.FirmwareVersion = MsgData[4:8]

            self.log.logging("Input", "Status", "ZiGate Classic PDM (OptiPDM)")
            self.ZiGateModel = 1
            self.ListOfDevices[ '0000' ]['Model'] = 'ZiGate Classic PDM (OptiPDM)'
            self.pluginParameters["CoordinatorModel"] = 'ZiGate Classic PDM (OptiPDM)'
            self.pluginParameters["CoordinatorFirmwareVersion"] = "%04x" %( int(self.FirmwareVersion,16))

        elif self.FirmwareMajorVersion == "05":
            self.FirmwareMajorVersion = MsgData[2:4]
            self.FirmwareVersion = MsgData[4:8]

            self.log.logging("Input", "Status", "ZiGate+ (V2)")
            self.ListOfDevices[ '0000' ]['Model'] = 'ZiGate+ (V2)'
            self.ZiGateModel = 2
            self.pluginParameters["CoordinatorModel"] = 'ZiGate+ (V2)'
            self.pluginParameters["CoordinatorFirmwareVersion"] = "%04x" %( int(self.FirmwareVersion,16))

        else:
            self.FirmwareMajorVersion = MsgData[2:4]
            self.FirmwareVersion = MsgData[4:8]
  
        self.log.logging("Input", "Status", "Installer Version Number: %s" % self.FirmwareVersion)
        self.log.logging("Input", "Status", "Branch Version: ==> %s <==" % FIRMWARE_BRANCH[self.FirmwareBranch])
        self.ControllerData["Firmware Version"] = "Branch: %s Major: %s Version: %s" % (
            self.FirmwareBranch,
            self.FirmwareMajorVersion,
            self.FirmwareVersion,
        )
        self.ControllerData["Branch Version"] = self.FirmwareBranch
        self.ControllerData["Major Version"] = self.FirmwareMajorVersion
        self.ControllerData["Minor Version"] = self.FirmwareVersion
 
        set_display_firmware_version( self )
               
        if self.pluginconf.pluginConf["RoutingTableRequestFeq"] and self.ZiGateModel != 2:
            self.pluginconf.pluginConf["RoutingTableRequestFeq"] = 0

    if self.webserver:
        self.webserver.update_firmware(self.FirmwareVersion)
        self.ControllerLink.update_ZiGate_HW_Version(self.ZiGateModel)

    if self.groupmgt:
        self.groupmgt.update_firmware(self.FirmwareVersion)

    if self.ControllerLink:
        self.ControllerLink.update_ZiGate_Version(self.FirmwareVersion, self.FirmwareMajorVersion)

    if self.log:
        self.log.loggingUpdateFirmware(self.FirmwareVersion, self.FirmwareMajorVersion)


    self.PDMready = True


def Decode8011(self, Devices, MsgData, MsgLQI, TransportInfos=None):

    # APP APS ACK
    self.log.logging("Input", "Debug2", "Decode8011 - APS ACK: %s" % MsgData)

    MsgLen = len(MsgData)
    MsgStatus = MsgData[0:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSEQ = MsgData[12:14] if MsgLen > 12 else None
    i_sqn = sqn_get_internal_sqn_from_aps_sqn(self.ControllerLink, MsgSEQ)

    if MsgSrcAddr not in self.ListOfDevices:
        return

    updLQI(self, MsgSrcAddr, MsgLQI)
    _powered = mainPoweredDevice(self, MsgSrcAddr)

    if self.pluginconf.pluginConf["debugzigateCmd"]:
        if MsgSEQ:
            self.log.logging(
                "Input",
                "Log",
                "Decod8011 Received [%s] for Nwkid: %s with status: %s e_sqn: 0x%02x/%s"
                % (i_sqn, MsgSrcAddr, MsgStatus, int(MsgSEQ, 16), int(MsgSEQ, 16)),
                MsgSrcAddr,
            )
        else:
            self.log.logging(
                "Input",
                "Log",
                "Decod8011 Received [%s] for Nwkid: %s with status: %s" % (i_sqn, MsgSrcAddr, MsgStatus),
                MsgSrcAddr,
            )

    if MsgSrcAddr not in self.ListOfDevices:
        return

    if MsgStatus == "00":
        timeStamped(self, MsgSrcAddr, 0x8011)
        lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
        if "Health" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Health"] != "Live":
            self.log.logging(
                "Input",
                "Log",
                "Receive an APS Ack from %s, let's put the device back to Live" % MsgSrcAddr,
                MsgSrcAddr,
            )
            self.ListOfDevices[MsgSrcAddr]["Health"] = "Live"
        return

    if MsgSrcAddr not in self.ListOfDevices:
        return

    if not _powered:
        return

    # Handle only NACK for main powered devices
    timedOutDevice(self, Devices, NwkId=MsgSrcAddr)
    set_health_state(self, MsgSrcAddr, MsgData[8:12], MsgStatus)


def set_health_state(self, MsgSrcAddr, ClusterId, Status):
    if "Health" not in self.ListOfDevices[MsgSrcAddr]:
        return
    if self.ListOfDevices[MsgSrcAddr]["Health"] != "Not Reachable":
        self.ListOfDevices[MsgSrcAddr]["Health"] = "Not Reachable"

    if "ZDeviceName" in self.ListOfDevices[MsgSrcAddr]:
        MsgClusterId = ClusterId
        if self.ListOfDevices[MsgSrcAddr]["ZDeviceName"] not in [
            {},
            "",
        ]:
            self.log.logging(
                "Input",
                "Log",
                "Receive NACK from %s (%s) clusterId: %s Status: %s"
                % (
                    self.ListOfDevices[MsgSrcAddr]["ZDeviceName"],
                    MsgSrcAddr,
                    MsgClusterId,
                    Status,
                ),
                MsgSrcAddr,
            )
        else:
            self.log.logging(
                "Input",
                "Log",
                "Receive NACK from %s clusterId: %s Status: %s" % (MsgSrcAddr, MsgClusterId, Status),
                MsgSrcAddr,
            )

    if self.pluginconf.pluginConf["deviceOffWhenTimeOut"]:
        for x in self.ListOfDevices[MsgSrcAddr]["Ep"]:
            if (
                "0006" in self.ListOfDevices[MsgSrcAddr]["Ep"][x]
                and "0000" in self.ListOfDevices[MsgSrcAddr]["Ep"][x]["0006"]
            ):
                self.ListOfDevices[MsgSrcAddr]["Ep"][x]["0006"]["0000"] = "00"


def Decode8012(self, Devices, MsgData, MsgLQI):
    """
    confirms that a data packet sent by the local node has been successfully
    passed down the stack to the MAC layer and has made its first hop towards
    its destination (an acknowledgment has been received from the next hop node).
    """
    return


def Decode8014(self, Devices, MsgData, MsgLQI):  # "Permit Join" status response

    # MsgLen = len(MsgData)
    Status = MsgData[:2]
    timestamp = int(time.time())

    self.log.logging("Input", "Debug", "Decode8014 - Permit Join status: %s" % (Status == "01"), "ffff")

    if "Permit" not in self.Ping:
        self.Ping["Permit"] = None

    prev = self.Ping["Permit"]

    _to_notify = (self.Ping["Permit"] is None) or (self.permitTojoin["Starttime"] >= timestamp - 240)

    if Status == "00":
        if prev != "Off":
            self.log.logging("Input", "Status", "Accepting new Hardware: Disable (Off)")
        self.permitTojoin["Duration"] = 0
        self.Ping["Permit"] = "Off"
        self.permitTojoin["Starttime"] = timestamp

    elif Status == "01":
        self.Ping["Permit"] = "On"
        if self.permitTojoin["Duration"] == 0:
            # In case 'Duration' is unknown or set to 0 and then, we have a Permit to Join, we are most-likely in the case of
            # a restart of the plugin.
            # We will make the assumption that Duration will be 255. In case that is not the case, during the next Ping,
            # we will receive a permit Off
            self.permitTojoin["Duration"] = 254
            self.permitTojoin["Starttime"] = timestamp
        if prev != "On":
            self.log.logging("Input", "Status", "Accepting new Hardware: Enable (On)")
    else:
        Domoticz.Error("Decode8014 - Unexpected value " + str(MsgData))

    self.log.logging(
        "Input",
        "Debug",
        "---> self.permitTojoin['Starttime']: %s" % self.permitTojoin["Starttime"],
        "ffff",
    )
    self.log.logging(
        "Input",
        "Debug",
        "---> self.permitTojoin['Duration']: %s" % self.permitTojoin["Duration"],
        "ffff",
    )
    self.log.logging("Input", "Debug", "---> Current time                  : %s" % timestamp, "ffff")
    self.log.logging("Input", "Debug", "---> self.Ping['Permit']  (prev)   : %s" % prev, "ffff")
    self.log.logging(
        "Input",
        "Debug",
        "---> self.Ping['Permit']  (new )   : %s" % self.Ping["Permit"],
        "ffff",
    )
    self.log.logging(
        "Input",
        "Debug",
        "---> _to_notify                    : %s" % _to_notify,
        "ffff",
    )

    self.Ping["TimeStamp"] = int(time.time())
    self.Ping["Status"] = "Receive"

    self.log.logging("Input", "Debug", "Ping - received", "ffff")


def Decode8017(self, Devices, MsgData, MsgLQI):  # Get Time

    ZigateTime = MsgData[0:8]

    EPOCTime = datetime(2000, 1, 1)
    UTCTime = int((datetime.now() - EPOCTime).total_seconds())
    ZigateTime = struct.unpack("I", struct.pack("I", int(ZigateTime, 16)))[0]
    self.log.logging(
        "Input",
        "Debug",
        "UTC time is: %s, Zigate Time is: %s with deviation of: %s " % (UTCTime, ZigateTime, UTCTime - ZigateTime),
    )
    if abs(UTCTime - ZigateTime) > 5:  # If Deviation is more than 5 sec then reset Time
        setTimeServer(self)


def Decode8015(self, Devices, MsgData, MsgLQI):  # Get device list ( following request device list 0x0015 )
    # id: 2bytes
    # addr: 4bytes
    # ieee: 8bytes
    # power_type: 2bytes - 0 Battery, 1 AC Power
    # rssi: 2 bytes - Signal Strength between 1 - 255
    numberofdev = len(MsgData)
    self.log.logging(
        "Input",
        "Status",
        "Number of devices recently active in Zigate = %s" % (str(round(numberofdev / 26))),
    )
    for idx in range(0, len(MsgData), 26):
        saddr = MsgData[idx + 2 : idx + 6]
        ieee = MsgData[idx + 6 : idx + 22]

        if int(ieee, 16) == 0:
            continue

        DevID = MsgData[idx : idx + 2]
        power = MsgData[idx + 22 : idx + 24]
        rssi = MsgData[idx + 24 : idx + 26]

        if DeviceExist(self, Devices, saddr, ieee):
            nickName = modelName = ""
            if "ZDeviceName" in self.ListOfDevices[saddr] and self.ListOfDevices[saddr]["ZDeviceName"] != {}:
                nickName = "( " + self.ListOfDevices[saddr]["ZDeviceName"] + " ) "
            if "Model" in self.ListOfDevices[saddr] and self.ListOfDevices[saddr]["Model"] != {}:
                modelName = self.ListOfDevices[saddr]["Model"]
            self.log.logging(
                "Input",
                "Status",
                "[%02d] DevID: %s Network addr: %s IEEE: %s LQI: %03d power: %s Model: %s %s"
                % (round(idx / 26), DevID, saddr, ieee, int(rssi, 16), power, modelName, nickName),
            )

            self.ListOfDevices[saddr]["LQI"] = int(rssi, 16) if rssi != "00" else 0
            self.log.logging(
                "Input",
                "Debug",
                "Decode8015: LQI set to %s / %s for %s" % (self.ListOfDevices[saddr]["LQI"], str(int(rssi, 16)), saddr),
            )
        else:
            self.log.logging(
                "Input",
                "Status",
                "[%02d] DevID: %s Network addr: %s IEEE: %s LQI: %03d power: %s not found in plugin database!"
                % (
                    round(idx / 26),
                    DevID,
                    saddr,
                    ieee,
                    int(rssi, 16),
                    power,
                ),
            )

    self.log.logging("Input", "Debug", "Decode8015 - IEEE2NWK      : " + str(self.IEEE2NWK))


def Decode8024(self, Devices, MsgData, MsgLQI):  # Network joined / formed

    MsgLen = len(MsgData)
    MsgDataStatus = MsgData[0:2]

    Domoticz.Log("Decode8024: Status: %s" % MsgDataStatus)

    if MsgDataStatus == "00":
        self.log.logging("Input", "Status", "Start Network - Success")
        Status = "Success"
    elif MsgDataStatus == "01":
        self.log.logging("Input", "Status", "Start Network - Formed new network")
        Status = "Success"
    elif MsgDataStatus == "02":
        self.log.logging("Input", "Status", "Start Network: Error invalid parameter.")
        Status = "Start Network: Error invalid parameter."
    elif MsgDataStatus == "04":
        self.log.logging(
            "Input",
            "Status",
            "Start Network: Node is on network. ZiGate is already in network so network is already formed",
        )
        Status = "Start Network: Node is on network. ZiGate is already in network so network is already formed"
    elif MsgDataStatus == "06":
        self.log.logging(
            "Input",
            "Status",
            "Start Network: Commissioning in progress. If network forming is already in progress",
        )
        Status = "Start Network: Commissioning in progress. If network forming is already in progress"
    else:
        Status = DisplayStatusCode(MsgDataStatus)
        self.log.logging(
            "Input",
            "Log",
            "Start Network: Network joined / formed Status: %s" % (MsgDataStatus),
        )

    if MsgLen != 24:
        self.log.logging(
            "Input",
            "Debug",
            "Decode8024 - uncomplete frame, MsgData: %s, Len: %s out of 24, data received: >%s<"
            % (MsgData, MsgLen, MsgData),
        )
        return

    MsgShortAddress = MsgData[2:6]
    MsgExtendedAddress = MsgData[6:22]
    MsgChannel = MsgData[22:24]

    if MsgExtendedAddress != "" and MsgShortAddress != "" and MsgShortAddress == "0000":
        # Let's check if this is a first initialisation, and then we need to update the Channel setting
        if (
            "startZigateNeeded" not in self.ControllerData
            and not self.startZigateNeeded
            and str(int(MsgChannel, 16)) != self.pluginconf.pluginConf["channel"]
        ):
            Domoticz.Status(
                "Updating Channel in Plugin Configuration from: %s to: %s"
                % (self.pluginconf.pluginConf["channel"], int(MsgChannel, 16))
            )
            self.pluginconf.pluginConf["channel"] = str(int(MsgChannel, 16))
            self.pluginconf.write_Settings()

        self.currentChannel = int(MsgChannel, 16)
        self.ControllerIEEE = MsgExtendedAddress
        self.ControllerNWKID = MsgShortAddress
        self.pluginParameters["CoordinatorIEEE"] = MsgExtendedAddress
        if self.iaszonemgt:
            self.iaszonemgt.setZigateIEEE(MsgExtendedAddress)

        if self.groupmgt:
            self.groupmgt.updateZigateIEEE(MsgExtendedAddress)

        self.ControllerData["IEEE"] = MsgExtendedAddress
        self.ControllerData["Short Address"] = MsgShortAddress
        self.ControllerData["Channel"] = int(MsgChannel, 16)

        self.log.logging(
            "Input",
            "Status",
            "Zigate details IEEE: %s, NetworkID: %s, Channel: %s, Status: %s: %s"
            % (
                MsgExtendedAddress,
                MsgShortAddress,
                int(MsgChannel, 16),
                MsgDataStatus,
                Status,
            ),
        )
    else:
        Domoticz.Error(
            "Zigate initialisation failed IEEE: %s, Nwkid: %s, Channel: %s"
            % (MsgExtendedAddress, MsgShortAddress, MsgChannel)
        )


def Decode8028(self, Devices, MsgData, MsgLQI):  # Authenticate response
    # MsgLen = len(MsgData)

    MsgGatewayIEEE = MsgData[0:16]
    MsgEncryptKey = MsgData[16:32]
    MsgMic = MsgData[32:40]
    MsgNodeIEEE = MsgData[40:56]
    MsgActiveKeySequenceNumber = MsgData[56:58]
    MsgChannel = MsgData[58:60]
    MsgShortPANid = MsgData[60:64]
    MsgExtPANid = MsgData[64:80]

    self.log.logging(
        "Input",
        "Log",
        "ZigateRead - MsgType 8028 - Authenticate response, Gateway IEEE: "
        + MsgGatewayIEEE
        + " Encrypt Key: "
        + MsgEncryptKey
        + " Mic: "
        + MsgMic
        + " Node IEEE: "
        + MsgNodeIEEE
        + " Active Key Sequence number: "
        + MsgActiveKeySequenceNumber
        + " Channel: "
        + MsgChannel
        + " Short PAN id: "
        + MsgShortPANid
        + "Extended PAN id: "
        + MsgExtPANid,
    )


def Decode802B(self, Devices, MsgData, MsgLQI):  # User Descriptor Notify
    # MsgLen = len(MsgData)

    MsgSequenceNumber = MsgData[0:2]
    MsgDataStatus = MsgData[2:4]
    MsgNetworkAddressInterest = MsgData[4:8]

    self.log.logging(
        "Input",
        "Log",
        "ZigateRead - MsgType 802B - User Descriptor Notify, Sequence number: "
        + MsgSequenceNumber
        + " Status: "
        + DisplayStatusCode(MsgDataStatus)
        + " Network address of interest: "
        + MsgNetworkAddressInterest,
    )


def Decode802C(self, Devices, MsgData, MsgLQI):  # User Descriptor Response
    # MsgLen = len(MsgData)

    MsgSequenceNumber = MsgData[0:2]
    MsgDataStatus = MsgData[2:4]
    MsgNetworkAddressInterest = MsgData[4:8]
    MsgLenght = MsgData[8:10]
    MsgMData = MsgData[10 : len(MsgData)]

    self.log.logging(
        "Input",
        "Log",
        "ZigateRead - MsgType 802C - User Descriptor Notify, Sequence number: "
        + MsgSequenceNumber
        + " Status: "
        + DisplayStatusCode(MsgDataStatus)
        + " Network address of interest: "
        + MsgNetworkAddressInterest
        + " Lenght: "
        + MsgLenght
        + " Data: "
        + MsgMData,
    )


def Decode8030(self, Devices, MsgData, MsgLQI):  # Bind response

    MsgLen = len(MsgData)
    self.log.logging("Input", "Debug", "Decode8030 - Msgdata: %s, MsgLen: %s" % (MsgData, MsgLen))

    MsgSequenceNumber = MsgData[0:2]
    MsgDataStatus = MsgData[2:4]

    if MsgLen < 10:
        return

    MsgSrcAddrMode = MsgData[4:6]

    if int(MsgSrcAddrMode, 16) == ADDRESS_MODE["short"]:
        MsgSrcAddr = MsgData[6:10]
        nwkid = MsgSrcAddr
        self.log.logging("Input", "Debug", "Decode8030 - Bind reponse for %s" % (MsgSrcAddr), MsgSrcAddr)

    elif int(MsgSrcAddrMode, 16) == ADDRESS_MODE["ieee"]:
        MsgSrcAddr = MsgData[6:14]
        self.log.logging("Input", "Debug", "Decode8030 - Bind reponse for %s" % (MsgSrcAddr))
        if MsgSrcAddr not in self.IEEE2NWK:
            Domoticz.Error("Decode8030 - Do no find %s in IEEE2NWK" % MsgSrcAddr)
            return
        nwkid = self.IEEE2NWK[MsgSrcAddr]

    elif int(MsgSrcAddrMode, 16) == 0:
        # Most likely Firmware 3.1a
        MsgSrcAddr = MsgData[8:12]
        nwkid = MsgSrcAddr

    else:
        Domoticz.Error("Decode8030 - Unknown addr mode %s in %s" % (MsgSrcAddrMode, MsgData))
        return

    i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSequenceNumber, TYPE_APP_ZDP)
    self.log.logging(
        "Input",
        "Debug",
        "Decode8030 - Bind response, Device: %s Status: %s MsgSequenceNumber: 0x%s/%3s i_sqn: %s"
        % (
            MsgSrcAddr,
            MsgDataStatus,
            MsgSequenceNumber,
            int(MsgSequenceNumber, 16),
            i_sqn,
        ),
        MsgSrcAddr,
    )

    if nwkid in self.ListOfDevices:
        if "Bind" in self.ListOfDevices[nwkid]:
            for Ep in list(self.ListOfDevices[nwkid]["Bind"]):
                if Ep not in self.ListOfDevices[nwkid]["Ep"]:
                    # Bad hack - Root cause not identify. Suspition of back and fourth move between stable and beta branch
                    Domoticz.Error(
                        "Decode8030 --> %s Found an inconstitent Ep: %s in %s"
                        % (nwkid, Ep, str(self.ListOfDevices[nwkid]["Bind"]))
                    )
                    del self.ListOfDevices[nwkid]["Bind"][Ep]
                    continue

                for cluster in list(self.ListOfDevices[nwkid]["Bind"][Ep]):
                    if (
                        self.ListOfDevices[nwkid]["Bind"][Ep][cluster]["Phase"] == "requested"
                        and "i_sqn" in self.ListOfDevices[nwkid]["Bind"][Ep][cluster]
                        and self.ListOfDevices[nwkid]["Bind"][Ep][cluster]["i_sqn"] == i_sqn
                    ):

                        self.log.logging(
                            "Input",
                            "Debug",
                            "Decode8030 - Set bind request to binded: nwkid %s ep: %s cluster: %s"
                            % (nwkid, Ep, cluster),
                            MsgSrcAddr,
                        )
                        self.ListOfDevices[nwkid]["Bind"][Ep][cluster]["Stamp"] = int(time.time())
                        self.ListOfDevices[nwkid]["Bind"][Ep][cluster]["Phase"] = "binded"
                        self.ListOfDevices[nwkid]["Bind"][Ep][cluster]["Status"] = MsgDataStatus
                        return

        if "WebBind" in self.ListOfDevices[nwkid]:
            for Ep in list(self.ListOfDevices[nwkid]["WebBind"]):
                if Ep not in self.ListOfDevices[nwkid]["Ep"]:
                    # Bad hack - Root cause not identify. Suspition of back and fourth move between stable and beta branch
                    Domoticz.Error(
                        "Decode8030 --> %s Found an inconstitent Ep: %s in %s"
                        % (nwkid, Ep, str(self.ListOfDevices[nwkid]["WebBind"]))
                    )
                    del self.ListOfDevices[nwkid]["WebBind"][Ep]
                    continue

                for cluster in list(self.ListOfDevices[nwkid]["WebBind"][Ep]):
                    for destNwkid in list(self.ListOfDevices[nwkid]["WebBind"][Ep][cluster]):
                        if destNwkid in (
                            "Stamp",
                            "Target",
                            "TargetIEEE",
                            "SourceIEEE",
                            "TargetEp",
                            "Phase",
                            "Status",
                        ):  # delete old mechanism
                            Domoticz.Error("---> delete  destNwkid: %s" % (destNwkid))
                            del self.ListOfDevices[nwkid]["WebBind"][Ep][cluster][destNwkid]

                        if (
                            self.ListOfDevices[nwkid]["WebBind"][Ep][cluster][destNwkid]["Phase"] == "requested"
                            and "i_sqn" in self.ListOfDevices[nwkid]["WebBind"][Ep][cluster][destNwkid]
                            and self.ListOfDevices[nwkid]["WebBind"][Ep][cluster][destNwkid]["i_sqn"] == i_sqn
                        ):

                            self.log.logging(
                                "Input",
                                "Debug",
                                "Decode8030 - Set WebBind request to binded: nwkid %s ep: %s cluster: %s destNwkid: %s"
                                % (nwkid, Ep, cluster, destNwkid),
                                MsgSrcAddr,
                            )
                            self.ListOfDevices[nwkid]["WebBind"][Ep][cluster][destNwkid]["Stamp"] = int(time.time())
                            self.ListOfDevices[nwkid]["WebBind"][Ep][cluster][destNwkid]["Phase"] = "binded"
                            self.ListOfDevices[nwkid]["WebBind"][Ep][cluster][destNwkid]["Status"] = MsgDataStatus
                            return


def Decode8031(self, Devices, MsgData, MsgLQI):  # Unbind response
    MsgLen = len(MsgData)
    self.log.logging("Input", "Debug", "Decode8031 - Msgdata: %s" % (MsgData))

    MsgSequenceNumber = MsgData[0:2]
    MsgDataStatus = MsgData[2:4]

    if MsgLen < 10:
        return

    MsgSrcAddrMode = MsgData[4:6]
    if int(MsgSrcAddrMode, 16) == ADDRESS_MODE["short"]:
        MsgSrcAddr = MsgData[6:10]
        nwkid = MsgSrcAddr
        self.log.logging("Input", "Debug", "Decode8031 - UnBind reponse for %s" % nwkid, nwkid)
    elif int(MsgSrcAddrMode, 16) == ADDRESS_MODE["ieee"]:
        MsgSrcAddr = MsgData[6:14]
        self.log.logging("Input", "Debug", "Decode8031 - UnBind reponse for %s" % (MsgSrcAddr))
        if MsgSrcAddr in self.IEEE2NWK:
            nwkid = self.IEEE2NWK[MsgSrcAddr]
            Domoticz.Error("Decode8031 - Do no find %s in IEEE2NWK" % MsgSrcAddr)
    else:
        Domoticz.Error("Decode8031 - Unknown addr mode %s in %s" % (MsgSrcAddrMode, MsgData))
        return

    self.log.logging(
        "Input",
        "Debug",
        "Decode8031 - UnBind response, Device: %s SQN: %s Status: %s" % (MsgSrcAddr, MsgSequenceNumber, MsgDataStatus),
        MsgSrcAddr,
    )

    if MsgDataStatus != "00":
        self.log.logging(
            "Input",
            "Debug",
            "Decode8031 - Unbind response SQN: %s status [%s] - %s"
            % (MsgSequenceNumber, MsgDataStatus, DisplayStatusCode(MsgDataStatus)),
            MsgSrcAddr,
        )


def Decode8034(self, Devices, MsgData, MsgLQI):  # Complex Descriptor response
    # MsgLen = len(MsgData)
    # MsgSequenceNumber = MsgData[0:2]

    MsgDataStatus = MsgData[2:4]
    MsgNetworkAddressInterest = MsgData[4:8]
    # MsgLenght = MsgData[8:10]
    MsgXMLTag = MsgData[10:12]
    MsgCountField = MsgData[12:14]
    MsgFieldValues = MsgData[14 : len(MsgData)]

    self.log.logging(
        "Input",
        "Log",
        "Decode8034 - Complex Descriptor for: %s xmlTag: %s fieldCount: %s fieldValue: %s, Status: %s"
        % (
            MsgNetworkAddressInterest,
            MsgXMLTag,
            MsgCountField,
            MsgFieldValues,
            MsgDataStatus,
        ),
    )


def Decode8040(self, Devices, MsgData, MsgLQI):  # Network Address response
    # MsgLen = len(MsgData)

    MsgSequenceNumber = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    MsgIEEE = MsgData[4:20]
    if MsgDataStatus == "00":
        MsgShortAddress = MsgData[20:24]
        MsgNumAssocDevices = MsgData[24:26]
        MsgStartIndex = MsgData[26:28]
        MsgDeviceList = MsgData[28 : len(MsgData)]

    if MsgDataStatus != "00":
        self.log.logging(
            "Input",
            "Log",
            "Decode8040 - Reception of Node Descriptor for %s with status %s" %(MsgIEEE, MsgDataStatus))
        return

    self.log.logging(
        "Input",
        "Status",
        "Network Address response, Sequence number: "
        + MsgSequenceNumber
        + " Status: "
        + DisplayStatusCode(MsgDataStatus)
        + " IEEE: "
        + MsgIEEE
        + " Short Address: "
        + MsgShortAddress
        + " number of associated devices: "
        + MsgNumAssocDevices
        + " Start Index: "
        + MsgStartIndex
        + " Device List: "
        + MsgDeviceList,
    )

    if MsgShortAddress in self.ListOfDevices:
        self.log.logging(
            "Input", "Debug", "Decode 8041 - Receive an IEEE: %s with a NwkId: %s" % (MsgIEEE, MsgShortAddress)
        )
        return

    # We might check if we didn't have a change in the IEEE <-> NwkId
    if MsgIEEE in self.IEEE2NWK:
        # Looks like the device was known with a different NwkId
        # hoping that we can reconnect to an existing Device
        self.log.logging(
            "Input",
            "Log",
            "Decode 8041 - Receive an IEEE: %s with a NwkId: %s, will try to reconnect" % (MsgIEEE, MsgShortAddress),
        )
        if not DeviceExist(self, Devices, MsgShortAddress, MsgIEEE):
            self.log.logging("Input", "Log", "Decode 8041 - Not able to reconnect (unknown device)")
            return

    timeStamped(self, MsgShortAddress, 0x8041)
    loggingMessages(self, "8041", MsgShortAddress, MsgIEEE, MsgLQI, MsgSequenceNumber)
    lastSeenUpdate(self, Devices, NwkId=MsgShortAddress)


def Decode8041(self, Devices, MsgData, MsgLQI):  # IEEE Address response
    # MsgLen = len(MsgData)

    MsgSequenceNumber = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    MsgIEEE = MsgData[4:20]
    if MsgDataStatus == "00":
        MsgShortAddress = MsgData[20:24]
        MsgNumAssocDevices = MsgData[24:26]
        MsgStartIndex = MsgData[26:28]
        MsgDeviceList = MsgData[28 : len(MsgData)]

    if MsgDataStatus != "00":
        self.log.logging(
            "Input",
            "Log",
            "Decode8041 - Reception of Node Descriptor for %s with status %s" %(MsgIEEE, MsgDataStatus))

        return

    self.log.logging(
        "Input",
        "Log",
        "Decode8041 - IEEE Address response, Sequence number: "
        + MsgSequenceNumber
        + " Status: "
        + DisplayStatusCode(MsgDataStatus)
        + " IEEE: "
        + MsgIEEE
        + " Short Address: "
        + MsgShortAddress
        + " number of associated devices: "
        + MsgNumAssocDevices
        + " Start Index: "
        + MsgStartIndex
        + " Device List: "
        + MsgDeviceList,
    )

    if MsgShortAddress in self.ListOfDevices:
        self.log.logging(
            "Input", "Debug", "Decode 8041 - Receive an IEEE: %s with a NwkId: %s" % (MsgIEEE, MsgShortAddress)
        )
        return

    # We might check if we didn't have a change in the IEEE <-> NwkId
    if MsgIEEE in self.IEEE2NWK:
        # Looks like the device was known with a different NwkId
        # hoping that we can reconnect to an existing Device
        self.log.logging(
            "Input",
            "Log",
            "Decode 8041 - Receive an IEEE: %s with a NwkId: %s, will try to reconnect" % (MsgIEEE, MsgShortAddress),
        )
        if not DeviceExist(self, Devices, MsgShortAddress, MsgIEEE):
            self.log.logging("Input", "Log", "Decode 8041 - Not able to reconnect (unknown device)")
            return

    timeStamped(self, MsgShortAddress, 0x8041)
    loggingMessages(self, "8041", MsgShortAddress, MsgIEEE, MsgLQI, MsgSequenceNumber)
    lastSeenUpdate(self, Devices, NwkId=MsgShortAddress)


def Decode8042(self, Devices, MsgData, MsgLQI):  # Node Descriptor response
    # MsgLen = len(MsgData)

    sequence = MsgData[:2]
    status = MsgData[2:4]
    addr = MsgData[4:8]
    if status == "00":
        manufacturer = MsgData[8:12]
        max_rx = MsgData[12:16]
        max_tx = MsgData[16:20]
        server_mask = MsgData[20:24]
        descriptor_capability = MsgData[24:26]
        mac_capability = MsgData[26:28]
        max_buffer = MsgData[28:30]
        bit_field = MsgData[30:34]


    if status != "00":
        self.log.logging(
            "Input",
            "Log",
            "Decode8042 - Reception of Node Descriptor for %s with status %s" %(addr, status))
        return
            
    self.log.logging(
        "Input",
        "Debug",
        "Decode8042 - Reception Node Descriptor for: "
        + addr + " SEQ: " + sequence + " Status: " + status + " manufacturer:" + manufacturer 
        + " mac_capability: " + str(mac_capability) + " bit_field: " + str(bit_field),
        addr,
    )
                
    if addr == "0000" and addr not in self.ListOfDevices:
        self.ListOfDevices[ addr ] = {}
        self.ListOfDevices[ addr ]["Ep"] = {}

    if addr not in self.ListOfDevices:
        self.log.logging(
            "Input",
            "Log",
            "Decode8042 receives a message from a non existing device %s" % addr,
        )
        return

    updLQI(self, addr, MsgLQI)

    self.ListOfDevices[addr]["Max Buffer Size"] = max_buffer
    self.ListOfDevices[addr]["Max Rx"] = max_rx
    self.ListOfDevices[addr]["Max Tx"] = max_tx
    self.ListOfDevices[addr]["macapa"] = mac_capability
    self.ListOfDevices[addr]["bitfield"] = bit_field
    self.ListOfDevices[addr]["server_mask"] = server_mask
    self.ListOfDevices[addr]["descriptor_capability"] = descriptor_capability

    mac_capability = ReArrangeMacCapaBasedOnModel(self, addr, mac_capability)
    capabilities = decodeMacCapa(mac_capability)

    if "Able to act Coordinator" in capabilities:
        AltPAN = 1
    else:
        AltPAN = 0

    if "Main Powered" in capabilities:
        PowerSource = "Main"
    else:
        PowerSource = "Battery"

    if "Full-Function Device" in capabilities:
        DeviceType = "FFD"
    else:
        DeviceType = "RFD"

    if "Receiver during Idle" in capabilities:
        ReceiveonIdle = "On"
    else:
        ReceiveonIdle = "Off"

    self.log.logging(
        "Input", "Debug", "Decode8042 - Alternate PAN Coordinator = " + str(AltPAN), addr
    )  # 1 if node is capable of becoming a PAN coordinator
    self.log.logging(
        "Input", "Debug", "Decode8042 - Receiver on Idle = " + str(ReceiveonIdle), addr
    )  # 1 if the device does not disable its receiver to
    # conserve power during idle periods.
    self.log.logging(
        "Input", "Debug", "Decode8042 - Power Source = " + str(PowerSource), addr
    )  # 1 if the current power source is mains power.
    self.log.logging(
        "Input", "Debug", "Decode8042 - Device type  = " + str(DeviceType), addr
    )  # 1 if this node is a full function device (FFD).

    bit_fieldL = int(bit_field[2:4], 16)
    bit_fieldH = int(bit_field[0:2], 16)
    
    self.log.logging(
        "Input", "Debug", "Decode8042 - bit_fieldL  = %s bit_fieldH = %s" %(bit_fieldL,bit_fieldH)) 

    LogicalType = bit_fieldL & 0x00F
    if LogicalType == 0:
        LogicalType = "Coordinator"
    elif LogicalType == 1:
        LogicalType = "Router"
    elif LogicalType == 2:
        LogicalType = "End Device"
    self.log.logging(
        "Input",
        "Debug",
        "Decode8042 - bit_field = " + str(bit_fieldL) + ": " + str(bit_fieldH),
        addr,
    )
    self.log.logging("Input", "Debug", "Decode8042 - Logical Type = " + str(LogicalType), addr)

    if "Manufacturer" not in self.ListOfDevices[addr] or self.ListOfDevices[addr]["Manufacturer"] in ("", {}):
        self.ListOfDevices[addr]["Manufacturer"] = manufacturer

    if ("Status" not in self.ListOfDevices[addr]) or (self.ListOfDevices[addr]["Status"] != "inDB"):
        self.ListOfDevices[addr]["Manufacturer"] = manufacturer
        self.ListOfDevices[addr]["DeviceType"] = str(DeviceType)
        self.ListOfDevices[addr]["LogicalType"] = str(LogicalType)
        self.ListOfDevices[addr]["PowerSource"] = str(PowerSource)
        self.ListOfDevices[addr]["ReceiveOnIdle"] = str(ReceiveonIdle)


def Decode8043(self, Devices, MsgData, MsgLQI):  # Reception Simple descriptor response
    # MsgLen = len(MsgData)

    MsgDataSQN = MsgData[0:2]
    MsgDataStatus = MsgData[2:4]
    MsgDataShAddr = MsgData[4:8]
    MsgDataLenght = MsgData[8:10]
    self.log.logging(
        "Input",
        "Debug",
        "Decode8043 - Received SQN: %s Addr: %s Len: %s Status: %s Data: %s" % (MsgDataSQN, MsgDataShAddr, MsgDataLenght, MsgDataStatus, MsgData),
    )

    if "SQN" in self.ListOfDevices[MsgDataShAddr] and MsgDataSQN == self.ListOfDevices[MsgDataShAddr]["SQN"]:
        return
    
    if int(MsgDataLenght, 16) == 0:
        return
    if MsgDataStatus != '00':
        return

    MsgDataEp = MsgData[10:12]
    MsgDataProfile = MsgData[12:16]
    MsgDataEp = MsgData[10:12]
    MsgDataProfile = MsgData[12:16]
    MsgDataDeviceId = MsgData[16:20]
    MsgDataBField = MsgData[20:22]
    MsgDataInClusterCount = MsgData[22:24]

    updSQN(self, MsgDataShAddr, MsgDataSQN)
    updLQI(self, MsgDataShAddr, MsgLQI)

    if MsgDataShAddr == "0000":  # Ep list for Zigate
        receiveZigateEpDescriptor(self, MsgData)
        return

    if MsgDataShAddr not in self.ListOfDevices:
        Domoticz.Error("Decode8043 - receive message for non existing device")
        return

    if int(MsgDataProfile, 16) == 0xC05E and int(MsgDataDeviceId, 16) == 0xE15E:
        # ZLL Commissioning EndPoint / Jaiwel
        self.log.logging(
            "Input",
            "Log",
            "Decode8043 - Received ProfileID: %s, ZDeviceID: %s - skip" % (MsgDataProfile, MsgDataDeviceId),
        )
        if MsgDataEp in self.ListOfDevices[MsgDataShAddr]["Ep"]:
            del self.ListOfDevices[MsgDataShAddr]["Ep"][MsgDataEp]
        if "NbEp" in self.ListOfDevices[MsgDataShAddr]:
            if self.ListOfDevices[MsgDataShAddr]["NbEp"] > "1":
                self.ListOfDevices[MsgDataShAddr]["NbEp"] = int(self.ListOfDevices[MsgDataShAddr]["NbEp"]) - 1
        return

    self.log.logging(
        "Input",
        "Status",
        "[%s] NEW OBJECT: %s Simple Descriptor Response EP: 0x%s LQI: %s"
        % ("-", MsgDataShAddr, MsgDataEp, int(MsgLQI, 16)),
    )

    # Endpoint V2 (ProfileID and ZDeviceID)
    if "Epv2" not in self.ListOfDevices[MsgDataShAddr]:
        # This should not happen. We are receiving 0x8043 while not 0x8045
        self.ListOfDevices[MsgDataShAddr]["Epv2"] = {}

    if MsgDataEp not in self.ListOfDevices[MsgDataShAddr]["Epv2"]:
        self.ListOfDevices[MsgDataShAddr]["Epv2"][MsgDataEp] = {}

    self.ListOfDevices[MsgDataShAddr]["Epv2"][MsgDataEp]["ProfileID"] = MsgDataProfile
    self.ListOfDevices[MsgDataShAddr]["Epv2"][MsgDataEp]["ZDeviceID"] = MsgDataDeviceId

    # Endpoint V1
    if "ProfileID" in self.ListOfDevices[MsgDataShAddr]:
        if self.ListOfDevices[MsgDataShAddr]["ProfileID"] != MsgDataProfile:
            # self.log.logging( "Input", 'Log',"Decode8043 - Overwrite ProfileID %s with %s from Ep: %s " \
            #        %( self.ListOfDevices[MsgDataShAddr]['ProfileID'] , MsgDataProfile, MsgDataEp))
            pass
    self.ListOfDevices[MsgDataShAddr]["ProfileID"] = MsgDataProfile
    self.log.logging(
        "Input",
        "Status",
        "[%s]    NEW OBJECT: %s ProfileID %s" % ("-", MsgDataShAddr, MsgDataProfile),
    )

    if "ZDeviceID" in self.ListOfDevices[MsgDataShAddr]:
        if self.ListOfDevices[MsgDataShAddr]["ZDeviceID"] != MsgDataDeviceId:
            # self.log.logging( "Input", 'Log',"Decode8043 - Overwrite ZDeviceID %s with %s from Ep: %s " \
            #        %( self.ListOfDevices[MsgDataShAddr]['ZDeviceID'] , MsgDataDeviceId, MsgDataEp))
            pass
    self.ListOfDevices[MsgDataShAddr]["ZDeviceID"] = MsgDataDeviceId
    self.log.logging(
        "Input",
        "Status",
        "[%s]    NEW OBJECT: %s ZDeviceID %s" % ("-", MsgDataShAddr, MsgDataDeviceId),
    )

    # Decode Bit Field
    # Device version: 4 bits (bits 0-4)
    # eserved: 4 bits (bits4-7)
    DeviceVersion = int(MsgDataBField, 16) & 0x00001111
    self.ListOfDevices[MsgDataShAddr]["ZDeviceVersion"] = "%04x" % DeviceVersion
    self.log.logging(
        "Input",
        "Status",
        "[%s]    NEW OBJECT: %s Application Version %s"
        % ("-", MsgDataShAddr, self.ListOfDevices[MsgDataShAddr]["ZDeviceVersion"]),
    )

    configSourceAvailable = False
    if "ConfigSource" in self.ListOfDevices[MsgDataShAddr]:
        if self.ListOfDevices[MsgDataShAddr]["ConfigSource"] == "DeviceConf":
            configSourceAvailable = True

    # Decoding Cluster IN
    self.log.logging(
        "Input",
        "Status",
        "[%s]    NEW OBJECT: %s Cluster IN Count: %s" % ("-", MsgDataShAddr, MsgDataInClusterCount),
    )
    idx = 24
    i = 1
    if int(MsgDataInClusterCount, 16) > 0:
        while i <= int(MsgDataInClusterCount, 16):
            MsgDataCluster = MsgData[idx + ((i - 1) * 4) : idx + (i * 4)]
            if not configSourceAvailable:
                self.ListOfDevices[MsgDataShAddr]["ConfigSource"] = "8043"
                if MsgDataEp not in self.ListOfDevices[MsgDataShAddr]["Ep"]:
                    self.ListOfDevices[MsgDataShAddr]["Ep"][MsgDataEp] = {}
                if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]["Ep"][MsgDataEp]:
                    self.ListOfDevices[MsgDataShAddr]["Ep"][MsgDataEp][MsgDataCluster] = {}
            else:
                self.log.logging(
                    "Pairing",
                    "Debug",
                    "[%s]    NEW OBJECT: %s we keep DeviceConf info" % ("-", MsgDataShAddr),
                )

            # Endpoint V2
            if MsgDataEp not in self.ListOfDevices[MsgDataShAddr]["Epv2"]:
                self.ListOfDevices[MsgDataShAddr]["Epv2"][MsgDataEp] = {}
            if "ClusterIn" not in self.ListOfDevices[MsgDataShAddr]["Epv2"][MsgDataEp]:
                self.ListOfDevices[MsgDataShAddr]["Epv2"][MsgDataEp]["ClusterIn"] = {}
            if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]["Epv2"][MsgDataEp]["ClusterIn"]:
                self.ListOfDevices[MsgDataShAddr]["Epv2"][MsgDataEp]["ClusterIn"][MsgDataCluster] = {}

            if MsgDataCluster in ZCL_CLUSTERS_LIST:
                self.log.logging(
                    "Input",
                    "Status",
                    "[%s]       NEW OBJECT: %s Cluster In %s: %s (%s)"
                    % (
                        "-",
                        MsgDataShAddr,
                        i,
                        MsgDataCluster,
                        ZCL_CLUSTERS_LIST[MsgDataCluster],
                    ),
                )
            else:
                self.log.logging(
                    "Input",
                    "Status",
                    "[%s]       NEW OBJECT: %s Cluster In %s: %s" % ("-", MsgDataShAddr, i, MsgDataCluster),
                )
            i = i + 1

    # Decoding Cluster Out
    idx = 24 + int(MsgDataInClusterCount, 16) * 4
    MsgDataOutClusterCount = MsgData[idx : idx + 2]

    self.log.logging(
        "Input",
        "Status",
        "[%s]    NEW OBJECT: %s Cluster OUT Count: %s" % ("-", MsgDataShAddr, MsgDataOutClusterCount),
    )
    idx += 2
    i = 1

    if int(MsgDataOutClusterCount, 16) > 0:
        while i <= int(MsgDataOutClusterCount, 16):
            MsgDataCluster = MsgData[idx + ((i - 1) * 4) : idx + (i * 4)]
            if not configSourceAvailable:
                if MsgDataEp not in self.ListOfDevices[MsgDataShAddr]["Ep"]:
                    self.ListOfDevices[MsgDataShAddr]["Ep"][MsgDataEp] = {}
                if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]["Ep"][MsgDataEp]:
                    self.ListOfDevices[MsgDataShAddr]["Ep"][MsgDataEp][MsgDataCluster] = {}
            else:
                self.log.logging(
                    "Input",
                    "Debug",
                    "[%s]    NEW OBJECT: %s we keep DeviceConf info" % ("-", MsgDataShAddr),
                    MsgDataShAddr,
                )

            # Endpoint V2
            if MsgDataEp not in self.ListOfDevices[MsgDataShAddr]["Epv2"]:
                self.ListOfDevices[MsgDataShAddr]["Epv2"][MsgDataEp] = {}
            if "ClusterOut" not in self.ListOfDevices[MsgDataShAddr]["Epv2"][MsgDataEp]:
                self.ListOfDevices[MsgDataShAddr]["Epv2"][MsgDataEp]["ClusterOut"] = {}
            if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]["Epv2"][MsgDataEp]["ClusterOut"]:
                self.ListOfDevices[MsgDataShAddr]["Epv2"][MsgDataEp]["ClusterOut"][MsgDataCluster] = {}

            if MsgDataCluster in ZCL_CLUSTERS_LIST:
                self.log.logging(
                    "Input",
                    "Status",
                    "[%s]       NEW OBJECT: %s Cluster Out %s: %s (%s)"
                    % (
                        "-",
                        MsgDataShAddr,
                        i,
                        MsgDataCluster,
                        ZCL_CLUSTERS_LIST[MsgDataCluster],
                    ),
                )
            else:
                self.log.logging(
                    "Input",
                    "Status",
                    "[%s]       NEW OBJECT: %s Cluster Out %s: %s" % ("-", MsgDataShAddr, i, MsgDataCluster),
                )

            MsgDataCluster = ""
            i = i + 1

    # Let's check if there is any other Ep to be disxcovered
    if request_next_Ep(self, MsgDataShAddr):
        if self.ListOfDevices[MsgDataShAddr]["Status"] != "inDB":
            self.ListOfDevices[MsgDataShAddr]["Status"] = "8043"
            self.ListOfDevices[MsgDataShAddr]["Heartbeat"] = "0"

    self.log.logging(
        "Pairing",
        "Debug",
        "Decode8043 - Processed " + MsgDataShAddr + " end results is: " + str(self.ListOfDevices[MsgDataShAddr]),
    )


def Decode8044(self, Devices, MsgData, MsgLQI):  # Power Descriptior response
    # MsgLen = len(MsgData)
    SQNum = MsgData[0:2]
    Status = MsgData[2:4]
    bit_fields = MsgData[4:8]

    # Not Short address, nor IEEE. Hard to relate to a device !

    power_mode = bit_fields[0]
    power_source = bit_fields[1]
    current_power_source = bit_fields[2]
    current_power_level = bit_fields[3]

    self.log.logging(
        "Input",
        "Debug",
        "Decode8044 - SQNum = "
        + SQNum
        + " Status = "
        + Status
        + " Power mode = "
        + power_mode
        + " power_source = "
        + power_source
        + " current_power_source = "
        + current_power_source
        + " current_power_level = "
        + current_power_level,
    )


def Decode8045(self, Devices, MsgData, MsgLQI):  # Reception Active endpoint response
    # MsgLen = len(MsgData)

    MsgDataSQN = MsgData[0:2]
    MsgDataStatus = MsgData[2:4]
    MsgDataShAddr = MsgData[4:8]
    MsgDataEpCount = MsgData[8:10]

    MsgDataEPlist = MsgData[10 : len(MsgData)]

    self.log.logging(
        "Pairing",
        "Debug",
        "Decode8045 - Reception Active endpoint response: SQN: "
        + MsgDataSQN
        + ", Status "
        + DisplayStatusCode(MsgDataStatus)
        + ", short Addr "
        + MsgDataShAddr
        + ", List "
        + MsgDataEpCount
        + ", Ep list "
        + MsgDataEPlist,
    )

    # Special Case, where we build the Zigate list of clusters
    if MsgDataShAddr == "0000":
        receiveZigateEpList(self, MsgDataEpCount, MsgDataEPlist)
        return

    if not DeviceExist(self, Devices, MsgDataShAddr):
        # Pas sur de moi, mais si le device n'existe pas, je vois pas pkoi on continuerait
        Domoticz.Error("Decode8045 - KeyError: MsgDataShAddr = " + MsgDataShAddr)
        return

    if self.ListOfDevices[MsgDataShAddr]["Status"] == "inDB":
        # This should not happen
        return

    self.ListOfDevices[MsgDataShAddr]["Status"] = "8045"

    updSQN(self, MsgDataShAddr, MsgDataSQN)
    updLQI(self, MsgDataShAddr, MsgLQI)

    for i in range(0, 2 * int(MsgDataEpCount, 16), 2):
        tmpEp = MsgDataEPlist[i : i + 2]
        if not self.ListOfDevices[MsgDataShAddr]["Ep"].get(tmpEp):
            self.ListOfDevices[MsgDataShAddr]["Ep"][tmpEp] = {}

        # Endpoint v2, we store ProfileId, ZDeviceId, Cluster In and Cluster Out
        if not self.ListOfDevices[MsgDataShAddr].get("Epv2"):
            self.ListOfDevices[MsgDataShAddr]["Epv2"] = {}
        if not self.ListOfDevices[MsgDataShAddr]["Epv2"].get(tmpEp):
            self.ListOfDevices[MsgDataShAddr]["Epv2"][tmpEp] = {}
            self.ListOfDevices[MsgDataShAddr]["Epv2"][tmpEp]["ClusterIn"] = {}
            self.ListOfDevices[MsgDataShAddr]["Epv2"][tmpEp]["ClusterOut"] = {}
            self.ListOfDevices[MsgDataShAddr]["Epv2"][tmpEp]["ProfileID"] = {}
            self.ListOfDevices[MsgDataShAddr]["Epv2"][tmpEp]["ZDeviceID"] = {}

        self.log.logging(
            "Input",
            "Status",
            "[%s] NEW OBJECT: %s Active Endpoint Response Ep: %s LQI: %s"
            % ("-", MsgDataShAddr, tmpEp, int(MsgLQI, 16)),
        )
        if self.ListOfDevices[MsgDataShAddr]["Status"] != "8045":
            self.log.logging(
                "Input",
                "Log",
                "[%s] NEW OBJECT: %s/%s receiving 0x8043 while in status: %s"
                % ("-", MsgDataShAddr, tmpEp, self.ListOfDevices[MsgDataShAddr]["Status"]),
            )
    self.ListOfDevices[MsgDataShAddr]["NbEp"] = str(int(MsgDataEpCount, 16))  # Store the number of EPs

    interview_state_8045(self, MsgDataShAddr, RIA=None, status=None)

    self.log.logging(
        "Pairing",
        "Debug",
        "Decode8045 - Device: "
        + str(MsgDataShAddr)
        + " updated ListofDevices with "
        + str(self.ListOfDevices[MsgDataShAddr]["Ep"]),
    )


def Decode8046(self, Devices, MsgData, MsgLQI):  # Match Descriptor response
    # MsgLen = len(MsgData)

    MsgDataSQN = MsgData[0:2]
    MsgDataStatus = MsgData[2:4]
    MsgDataShAddr = MsgData[4:8]
    MsgDataLenList = MsgData[8:10]
    MsgDataMatchList = MsgData[10 : len(MsgData)]

    updSQN(self, MsgDataShAddr, MsgDataSQN)
    updLQI(self, MsgDataShAddr, MsgLQI)
    self.log.logging(
        "Input",
        "Log",
        "Decode8046 - Match Descriptor response: SQN: "
        + MsgDataSQN
        + ", Status "
        + DisplayStatusCode(MsgDataStatus)
        + ", short Addr "
        + MsgDataShAddr
        + ", Lenght list  "
        + MsgDataLenList
        + ", Match list "
        + MsgDataMatchList,
    )


def Decode8047(self, Devices, MsgData, MsgLQI):  # Management Leave response
    # MsgLen = len(MsgData)
    # MsgSequenceNumber = MsgData[0:2]

    MsgDataStatus = MsgData[2:4]

    self.log.logging(
        "Input",
        "Status",
        "Decode8047 - Leave response, LQI: %s Status: %s - %s"
        % (int(MsgLQI, 16), MsgDataStatus, DisplayStatusCode(MsgDataStatus)),
    )


def device_leave_annoucement(self, Devices, MsgExtAddress):
    devName = ""
    for x in Devices:
        if Devices[x].DeviceID == MsgExtAddress:
            devName = Devices[x].Name
            break
    self.adminWidgets.updateNotificationWidget(Devices, "Leave indication from %s for %s " % (MsgExtAddress, devName))


def Decode8048(self, Devices, MsgData, MsgLQI):  # Leave indication
    # MsgLen = len(MsgData)

    MsgExtAddress = MsgData[0:16]
    MsgDataStatus = MsgData[16:18]

    loggingMessages(self, "8048", None, MsgExtAddress, int(MsgLQI, 16), None)

    if (
        MsgExtAddress not in self.IEEE2NWK
    ):  # Most likely this object has been removed and we are receiving the confirmation.
        device_leave_annoucement(self, Devices, MsgExtAddress)
        return

    sAddr = getSaddrfromIEEE(self, MsgExtAddress)

    if sAddr not in self.ListOfDevices:
        return

    timeStamped(self, sAddr, 0x8048)

    if self.ListOfDevices[sAddr]["Status"] == "Removed":
        if sAddr in self.ListOfDevices:
            del self.ListOfDevices[sAddr]
        if MsgExtAddress in self.IEEE2NWK:
            del self.IEEE2NWK[MsgExtAddress]
    
    elif self.ListOfDevices[sAddr]["Status"] == "inDB":
        self.ListOfDevices[sAddr]["Status"] = "Left"
        self.ListOfDevices[sAddr]["Heartbeat"] = 0
        # Domoticz.Status("Calling leaveMgt to request a rejoin of %s/%s " %( sAddr, MsgExtAddress))
        # leaveMgtReJoin( self, sAddr, MsgExtAddress )

    elif self.ListOfDevices[sAddr]["Status"] in ( "004d", "0043", "8043", "0045", "8045", ):
        if MsgExtAddress in self.IEEE2NWK:
            del self.IEEE2NWK[MsgExtAddress]
        del self.ListOfDevices[sAddr]
        self.log.logging(
            "Input",
            "Log",
            "Removing this not completly provisionned device due to a leave ( %s , %s )" % (sAddr, MsgExtAddress),
        )

    elif self.ListOfDevices[sAddr]["Status"] == "Left":
        # This is bugy, as I should then remove the device in Domoticz
        # self.log.logging( "Input", 'Log',"--> Removing: %s" %str(self.ListOfDevices[sAddr]))
        # del self.ListOfDevices[sAddr]
        # del self.IEEE2NWK[MsgExtAddress]

        # Will set to Leave in order to protect Domoticz Widget, Just need to make sure that we can reconnect at a point of time
        self.ListOfDevices[sAddr]["Status"] = "Leave"
        self.ListOfDevices[sAddr]["Heartbeat"] = 0
        Domoticz.Error(
            "Receiving a leave from %s/%s while device is %s status"
            % (sAddr, MsgExtAddress, self.ListOfDevices[sAddr]["Status"])
        )

    zdevname = ""
    if sAddr in self.ListOfDevices and "ZDeviceName" in self.ListOfDevices[sAddr]:
        zdevname = self.ListOfDevices[sAddr]["ZDeviceName"]
    self.log.logging(
        "Input",
        "Status",
        "%s (%s/%s) send a Leave indication and will be outside of the network. LQI: %s"
        % (zdevname, sAddr, MsgExtAddress, int(MsgLQI, 16)),
    )

    self.log.logging(
        "Input",
        "Debug",
        "Leave indication from IEEE: %s , Status: %s " % (MsgExtAddress, MsgDataStatus),
        sAddr,
    )
    updLQI(self, sAddr, MsgLQI)


def Decode8049(self, Devices, MsgData, MsgLQI):  # E_SL_MSG_PERMIT_JOINING_RESPONSE

    self.log.logging("Input", "Debug", "Decode8049 - MsgData: %s" % MsgData)
    # SQN = MsgData[0:2]
    Status = MsgData[2:4]

    if Status == "00":
        self.log.logging("Input", "Status", "Pairing Command correctly exectued")


def Decode804A(self, Devices, MsgData, MsgLQI):  # Management Network Update response

    if self.networkenergy:
        self.networkenergy.NwkScanResponse(MsgData)


def Decode804B(self, Devices, MsgData, MsgLQI):  # System Server Discovery response
    # MsgLen = len(MsgData)

    MsgSequenceNumber = MsgData[0:2]
    MsgDataStatus = MsgData[2:4]
    MsgServerMask = MsgData[4:8]

    self.log.logging(
        "Input",
        "Log",
        "ZigateRead - MsgType 804B - System Server Discovery response, Sequence number: "
        + MsgSequenceNumber
        + " Status: "
        + DisplayStatusCode(MsgDataStatus)
        + " Server Mask: "
        + MsgServerMask,
    )


def Decode804E(self, Devices, MsgData, MsgLQI):

    self.log.logging("Input", "Debug", "Decode804E - Receive message")
    if self.networkmap:
        self.networkmap.LQIresp(MsgData)


# Group response
# Implemented in GroupMgtv2.GrupManagement.py
def Decode8060(self, Devices, MsgData, MsgLQI):

    self.groupmgt.add_group_member_ship_response(MsgData)


def Decode8061(self, Devices, MsgData, MsgLQI):

    self.groupmgt.check_group_member_ship_response(MsgData)


def Decode8062(self, Devices, MsgData, MsgLQI):

    self.groupmgt.look_for_group_member_ship_response(MsgData)


def Decode8063(self, Devices, MsgData, MsgLQI):

    self.groupmgt.remove_group_member_ship_response(MsgData)


# Reponses SCENE
def Decode80A0(self, Devices, MsgData, MsgLQI):  # View Scene response
    # MsgLen = len(MsgData)

    MsgSequenceNumber = MsgData[0:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgDataStatus = MsgData[8:10]
    MsgGroupID = MsgData[10:14]
    # MsgSceneID = MsgData[14:16]
    # MsgSceneTransitonTime = MsgData[16:20]
    # MSgSceneNameLength = MsgData[20:22]
    # MSgSceneNameLengthMax = MsgData[22:24]
    # <scene name data: data each element is uint8_t>
    # <extensions length: uint16_t>
    # <extensions max length: uint16_t>
    # <extensions data: data each element is uint8_t>

    self.log.logging(
        "Input",
        "Log",
        "ZigateRead - MsgType 80A0 - View Scene response, Sequence number: "
        + MsgSequenceNumber
        + " EndPoint: "
        + MsgEP
        + " ClusterID: "
        + MsgClusterID
        + " Status: "
        + DisplayStatusCode(MsgDataStatus)
        + " Group ID: "
        + MsgGroupID,
    )


def Decode80A1(self, Devices, MsgData, MsgLQI):  # Add Scene response
    # MsgLen = len(MsgData)

    MsgSequenceNumber = MsgData[0:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgDataStatus = MsgData[8:10]
    MsgGroupID = MsgData[10:14]
    MsgSceneID = MsgData[14:16]

    self.log.logging(
        "Input",
        "Log",
        "ZigateRead - MsgType 80A1 - Add Scene response, Sequence number: "
        + MsgSequenceNumber
        + " EndPoint: "
        + MsgEP
        + " ClusterID: "
        + MsgClusterID
        + " Status: "
        + DisplayStatusCode(MsgDataStatus)
        + " Group ID: "
        + MsgGroupID
        + " Scene ID: "
        + MsgSceneID,
    )


def Decode80A2(self, Devices, MsgData, MsgLQI):  # Remove Scene response
    # MsgLen = len(MsgData)

    MsgSequenceNumber = MsgData[0:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgDataStatus = MsgData[8:10]
    MsgGroupID = MsgData[10:14]
    MsgSceneID = MsgData[14:16]

    self.log.logging(
        "Input",
        "Log",
        "ZigateRead - MsgType 80A2 - Remove Scene response, Sequence number: "
        + MsgSequenceNumber
        + " EndPoint: "
        + MsgEP
        + " ClusterID: "
        + MsgClusterID
        + " Status: "
        + DisplayStatusCode(MsgDataStatus)
        + " Group ID: "
        + MsgGroupID
        + " Scene ID: "
        + MsgSceneID,
    )


def Decode80A3(self, Devices, MsgData, MsgLQI):  # Remove All Scene response
    # MsgLen = len(MsgData)

    MsgSequenceNumber = MsgData[0:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgDataStatus = MsgData[8:10]
    MsgGroupID = MsgData[10:14]

    self.log.logging(
        "Input",
        "Log",
        "ZigateRead - MsgType 80A3 - Remove All Scene response, Sequence number: "
        + MsgSequenceNumber
        + " EndPoint: "
        + MsgEP
        + " ClusterID: "
        + MsgClusterID
        + " Status: "
        + DisplayStatusCode(MsgDataStatus)
        + " Group ID: "
        + MsgGroupID,
    )


def Decode80A4(self, Devices, MsgData, MsgLQI):  # Store Scene response
    # MsgLen = len(MsgData)

    MsgSequenceNumber = MsgData[0:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgDataStatus = MsgData[8:10]
    MsgGroupID = MsgData[10:14]
    MsgSceneID = MsgData[14:16]

    self.log.logging(
        "Input",
        "Log",
        "ZigateRead - MsgType 80A4 - Store Scene response, Sequence number: "
        + MsgSequenceNumber
        + " EndPoint: "
        + MsgEP
        + " ClusterID: "
        + MsgClusterID
        + " Status: "
        + DisplayStatusCode(MsgDataStatus)
        + " Group ID: "
        + MsgGroupID
        + " Scene ID: "
        + MsgSceneID,
    )


def Decode80A6(self, Devices, MsgData, MsgLQI):  # Scene Membership response
    MsgSrcAddr = MsgData[len(MsgData) - 4 : len(MsgData)]

    # MsgSequenceNumber = MsgData[0:2]
    MsgEP = MsgData[2:4]
    MsgClusterID = MsgData[4:8]
    MsgDataStatus = MsgData[8:10]
    MsgCapacity = int(MsgData[10:12], 16)
    MsgGroupID = MsgData[12:16]
    MsgSceneCount = int(MsgData[16:18], 16)

    self.log.logging(
        "Input",
        "Log",
        "Decode80A6 - Scene Membership response - MsgSrcAddr: %s MsgEP: %s MsgGroupID: %s MsgClusterID: %s MsgDataStatus: %s MsgCapacity: %s MsgSceneCount: %s"
        % (
            MsgSrcAddr,
            MsgEP,
            MsgGroupID,
            MsgClusterID,
            MsgDataStatus,
            MsgCapacity,
            MsgSceneCount,
        ),
    )
    if MsgDataStatus != "00":
        self.log.logging(
            "Input",
            "Log",
            "Decode80A6 - Scene Membership response - MsgSrcAddr: %s MsgEP: %s MsgClusterID: %s MsgDataStatus: %s"
            % (MsgSrcAddr, MsgEP, MsgClusterID, MsgDataStatus),
        )
        return

    if MsgSceneCount > MsgCapacity:
        self.log.logging(
            "Input",
            "Log",
            "Decode80A6 - Scene Membership response MsgSceneCount %s > MsgCapacity %s" % (MsgSceneCount, MsgCapacity),
        )
        return

    MsgSceneList = MsgData[18 : 18 + MsgSceneCount * 2]
    if len(MsgData) > 18 + MsgSceneCount * 2:
        MsgSrcAddr = MsgData[18 + MsgSceneCount * 2 : (18 + MsgSceneCount * 2) + 4]
    MsgScene = []
    for idx in range(0, MsgSceneCount, 2):
        scene = MsgSceneList[idx : idx + 2]
        if scene not in MsgScene:
            MsgScene.append(scene)
    self.log.logging("Input", "Log", "           - Scene List: %s" % (str(MsgScene)))


# Reponses Attributs
def Decode8100(self, Devices, MsgData, MsgLQI):
    # Read Attribute Response (in case there are several Attribute call several time read_report_attributes)

    MsgSQN = MsgData[0:2]
    i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSQN, TYPE_APP_ZCL)

    MsgSrcAddr = MsgData[2:6]
    timeStamped(self, MsgSrcAddr, 0x8100)
    loggingMessages(self, "8100", MsgSrcAddr, None, MsgLQI, MsgSQN)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    updLQI(self, MsgSrcAddr, MsgLQI)
    MsgSrcEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]

    self.statistics._clusterOK += 1
    scan_attribute_reponse(self, Devices, MsgSQN, i_sqn, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgData, "8100")
    callbackDeviceAwake(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId)


def Decode8101(self, Devices, MsgData, MsgLQI):  # Default Response
    MsgDataSQN = MsgData[0:2]
    MsgDataEp = MsgData[2:4]
    MsgClusterId = MsgData[4:8]
    MsgDataCommand = MsgData[8:10]
    MsgDataStatus = MsgData[10:12]
    self.log.logging(
        "Input",
        "Debug",
        "Decode8101 - Default response - SQN: %s, EP: %s, ClusterID: %s , DataCommand: %s, - Status: [%s] %s"
        % (
            MsgDataSQN,
            MsgDataEp,
            MsgClusterId,
            MsgDataCommand,
            MsgDataStatus,
            DisplayStatusCode(MsgDataStatus),
        ),
    )


def Decode8102(self, Devices, MsgData, MsgLQI):  # Attribute Reports

    MsgSQN = MsgData[0:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSrcEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]
    MsgAttrID = MsgData[12:16]
    MsgAttStatus = MsgData[16:18]
    MsgAttType = MsgData[18:20]
    MsgAttSize = MsgData[20:24]
    MsgClusterData = MsgData[24 : len(MsgData)]

    self.log.logging(
        "Input",
        "Debug",
        "Decode8102 - Attribute Reports: [%s:%s] MsgSQN: %s ClusterID: %s AttributeID: %s Status: %s Type: %s Size: %s ClusterData: >%s<"
        % (
            MsgSrcAddr,
            MsgSrcEp,
            MsgSQN,
            MsgClusterId,
            MsgAttrID,
            MsgAttStatus,
            MsgAttType,
            MsgAttSize,
            MsgClusterData,
        ),
        MsgSrcAddr,
    )

    if self.PluzzyFirmware:
        self.log.logging("Input", "Log", "Patching payload:", MsgSrcAddr)
        _type = MsgAttStatus
        _status = MsgAttType
        _size = MsgAttSize
        # _data = MsgClusterData

        _newsize = "00" + _size[0:2]
        _newdata = MsgAttSize[2:4] + MsgClusterData

        self.log.logging("Input", "Log", " MsgAttStatus: %s -> %s" % (MsgAttStatus, _status), MsgSrcAddr)
        self.log.logging("Input", "Log", " MsgAttType: %s -> %s" % (MsgAttType, _type), MsgSrcAddr)
        self.log.logging("Input", "Log", " MsgAttSize: %s -> %s" % (MsgAttSize, _newsize), MsgSrcAddr)
        self.log.logging(
            "Input",
            "Log",
            " MsgClusterData: %s -> %s" % (MsgClusterData, _newdata),
            MsgSrcAddr,
        )

        MsgAttStatus = _status
        MsgAttType = _type
        MsgAttSize = _newsize
        MsgClusterData = _newdata
        MsgData = (
            MsgSQN
            + MsgSrcAddr
            + MsgSrcEp
            + MsgClusterId
            + MsgAttrID
            + MsgAttStatus
            + MsgAttType
            + MsgAttSize
            + MsgClusterData
        )
        pluzzyDecode8102(
            self,
            MsgSrcAddr,
            MsgSrcEp,
            MsgClusterId,
            MsgAttrID,
            MsgAttStatus,
            MsgAttType,
            MsgAttSize,
            MsgClusterData,
            MsgLQI,
        )

    timeStamped(self, MsgSrcAddr, 0x8102)
    loggingMessages(self, "8102", MsgSrcAddr, None, MsgLQI, MsgSQN)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    updLQI(self, MsgSrcAddr, MsgLQI)
    i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSQN, TYPE_APP_ZCL)

    self.statistics._clusterOK += 1
    scan_attribute_reponse(self, Devices, MsgSQN, i_sqn, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgData, "8102")

    callbackDeviceAwake(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId)


def scan_attribute_reponse(self, Devices, MsgSQN, i_sqn, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgData, msgtype):

    idx = 12
    while idx < len(MsgData):
        MsgAttrID = MsgAttStatus = MsgAttType = MsgAttSize = MsgClusterData = ""
        MsgAttrID = MsgData[idx : idx + 4]
        idx += 4
        MsgAttStatus = MsgData[idx : idx + 2]
        idx += 2
        if MsgAttStatus == "00":
            MsgAttType = MsgData[idx : idx + 2]
            idx += 2
            MsgAttSize = MsgData[idx : idx + 4]
            idx += 4
            size = int(MsgAttSize, 16) * 2
            MsgClusterData = MsgData[idx : idx + size]
            idx += size
        else:
            self.log.logging(
                "Input",
                "Debug",
                "scan_attribute_reponse - %s idx: %s Read Attribute Response: [%s:%s] status: %s -> %s"
                % (msgtype, idx, MsgSrcAddr, MsgSrcEp, MsgAttStatus, MsgData[idx:]),
            )

            # If the frame is coming from firmware we get only one attribute at a time, with some dumy datas
            if len(MsgData[idx:]) == 6:
                # crap, lets finish it
                # Domoticz.Log("Crap Data: %s len: %s" %(MsgData[idx:], len(MsgData[idx:])))
                idx += 6
        self.log.logging(
            "Input",
            "Debug",
            "scan_attribute_reponse - %s idx: %s Read Attribute Response: [%s:%s] ClusterID: %s MsgSQN: %s, i_sqn: %s, AttributeID: %s Status: %s Type: %s Size: %s ClusterData: >%s<"
            % (
                msgtype,
                idx,
                MsgSrcAddr,
                MsgSrcEp,
                MsgClusterId,
                MsgSQN,
                i_sqn,
                MsgAttrID,
                MsgAttStatus,
                MsgAttType,
                MsgAttSize,
                MsgClusterData,
            ),
            MsgSrcAddr,
        )
        read_report_attributes(
            self,
            Devices,
            msgtype,
            MsgSQN,
            MsgSrcAddr,
            MsgSrcEp,
            MsgClusterId,
            MsgAttrID,
            MsgAttStatus,
            MsgAttType,
            MsgAttSize,
            MsgClusterData,
        )


def read_report_attributes(
    self,
    Devices,
    MsgType,
    MsgSQN,
    MsgSrcAddr,
    MsgSrcEp,
    MsgClusterId,
    MsgAttrID,
    MsgAttStatus,
    MsgAttType,
    MsgAttSize,
    MsgClusterData,
):

    if DeviceExist(self, Devices, MsgSrcAddr):
        debug_LQI(self, MsgSrcAddr, MsgClusterId, MsgAttrID, MsgClusterData, MsgSrcEp)

        self.log.logging(
            "Input",
            "Debug2",
            "Decode8102: Attribute Report from "
            + str(MsgSrcAddr)
            + " SQN = "
            + str(MsgSQN)
            + " ClusterID = "
            + str(MsgClusterId)
            + " AttrID = "
            + str(MsgAttrID)
            + " Attribute Data = "
            + str(MsgClusterData),
            MsgSrcAddr,
        )

        if "Health" in self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]["Health"] = "Live"

        updSQN(self, MsgSrcAddr, str(MsgSQN))
        lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)

        ReadCluster(
            self,
            Devices,
            MsgType,
            MsgSQN,
            MsgSrcAddr,
            MsgSrcEp,
            MsgClusterId,
            MsgAttrID,
            MsgAttStatus,
            MsgAttType,
            MsgAttSize,
            MsgClusterData,
            Source=MsgType,
        )
        return

    # This device is unknown, and we don't have the IEEE to check if there is a device coming with a new sAddr
    # Will request in the next hearbeat to for a IEEE request
    ieee = lookupForIEEE(self, MsgSrcAddr, True)
    if ieee:
        self.log.logging("Input", "Debug", "Found IEEE for short address: %s is %s" % (MsgSrcAddr, ieee))
        if MsgSrcAddr in self.UnknownDevices:
            self.UnknownDevices.remove(MsgSrcAddr)
    else:
        # If we didn't find it, let's trigger a NetworkMap scan if not one in progress
        unknown_device_nwkid(self, MsgSrcAddr)
        self.log.logging(
            "Input",
            "Log",
            "Decode8102 - Receiving a message from unknown device: [%s:%s] ClusterID: %s AttributeID: %s Status: %s Type: %s Size: %s ClusterData: >%s<"
            % (
                MsgSrcAddr,
                MsgSrcEp,
                MsgClusterId,
                MsgAttrID,
                MsgAttStatus,
                MsgAttType,
                MsgAttSize,
                MsgClusterData,
            ),
            MsgSrcAddr,
        )


def isZDeviceName(self, MsgSrcAddr):

    return "ZDeviceName" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["ZDeviceName"] not in [
        "",
        {},
    ]


def debug_LQI(self, MsgSrcAddr, MsgClusterId, MsgAttrID, MsgClusterData, MsgSrcEp):
    if (
        self.pluginconf.pluginConf["debugLQI"]
        and self.ListOfDevices[MsgSrcAddr]["LQI"] <= self.pluginconf.pluginConf["debugLQI"]
    ):
        if isZDeviceName(self, MsgSrcAddr):
            self.log.logging(
                "Input",
                "Log",
                "Decode8102 - LQI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)%s"
                % (
                    self.ListOfDevices[MsgSrcAddr]["LQI"],
                    MsgClusterId,
                    MsgAttrID,
                    MsgClusterData,
                    MsgSrcAddr,
                    MsgSrcEp,
                    self.ListOfDevices[MsgSrcAddr]["ZDeviceName"],
                ),
            )
        else:
            self.log.logging(
                "Input",
                "Log",
                "Decode8102 - LQI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)"
                % (
                    self.ListOfDevices[MsgSrcAddr]["LQI"],
                    MsgClusterId,
                    MsgAttrID,
                    MsgClusterData,
                    MsgSrcAddr,
                    MsgSrcEp,
                ),
            )
    else:
        self.log.logging(
            "Input",
            "Debug",
            "Decode8102 - LQI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)"
            % (
                self.ListOfDevices[MsgSrcAddr]["LQI"],
                MsgClusterId,
                MsgAttrID,
                MsgClusterData,
                MsgSrcAddr,
                MsgSrcEp,
            ),
        )


def Decode8110(self, Devices, MsgData, MsgLQI):

    if not self.FirmwareVersion:
        return

    MsgSrcAddr = MsgData[2:6]
    # Coming from Data Indication
    MsgSQN = MsgData[0:2]
    MsgSrcEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]
    if len(MsgData) != 24:
        MsgAttrStatus = MsgData[12:14]
        MsgAttrID = None
    elif int(self.FirmwareVersion, 16) < int("31d", 16):
        MsgAttrID = MsgData[12:16]
        MsgAttrStatus = MsgData[16:18]
    else:
        # Firmware >= 31d
        # MsgUnkn1 = MsgData[12:14]
        MsgAttrStatus = MsgData[14:16]
        MsgAttrID = None

    Decode8110_raw(
        self,
        Devices,
        MsgSQN,
        MsgSrcAddr,
        MsgSrcEp,
        MsgClusterId,
        MsgAttrStatus,
        MsgAttrID,
        MsgLQI,
    )


def Decode8110_raw(
    self,
    Devices,
    MsgSQN,
    MsgSrcAddr,
    MsgSrcEp,
    MsgClusterId,
    MsgAttrStatus,
    MsgAttrID,
    MsgLQI,
):  # Write Attribute response

    i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSQN, TYPE_APP_ZCL)
    self.log.logging(
        "Input",
        "Debug",
        "Decode8110 - WriteAttributeResponse - MsgSQN: %s,  MsgSrcAddr: %s, MsgSrcEp: %s, MsgClusterId: %s MsgAttrID: %s Status: %s"
        % (MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus),
        MsgSrcAddr,
    )

    timeStamped(self, MsgSrcAddr, 0x8110)
    updSQN(self, MsgSrcAddr, MsgSQN)
    updLQI(self, MsgSrcAddr, MsgLQI)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)

    if self.FirmwareVersion and int(self.FirmwareVersion, 16) >= int("31d", 16) and MsgAttrID:
        set_status_datastruct(
            self,
            "WriteAttributes",
            MsgSrcAddr,
            MsgSrcEp,
            MsgClusterId,
            MsgAttrID,
            MsgAttrStatus,
        )
        set_request_phase_datastruct(
            self,
            "WriteAttributes",
            MsgSrcAddr,
            MsgSrcEp,
            MsgClusterId,
            MsgAttrID,
            "fullfilled",
        )
        if MsgAttrStatus != "00":
            self.log.logging(
                "Input",
                "Log",
                "Decode8110 - Write Attribute Respons response - ClusterID: %s/%s, MsgSrcAddr: %s, MsgSrcEp:%s , Status: %s"
                % (MsgClusterId, MsgAttrID, MsgSrcAddr, MsgSrcEp, MsgAttrStatus),
                MsgSrcAddr,
            )
        return

    # We got a global status for all attributes requested in this command
    # We need to find the Attributes related to the i_sqn
    i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSQN, TYPE_APP_ZCL)
    self.log.logging("Input", "Debug", "------- - i_sqn: %0s e_sqn: %s" % (i_sqn, MsgSQN))

    for matchAttributeId in list(
        get_list_isqn_attr_datastruct(self, "WriteAttributes", MsgSrcAddr, MsgSrcEp, MsgClusterId)
    ):
        if (
            get_isqn_datastruct(
                self,
                "WriteAttributes",
                MsgSrcAddr,
                MsgSrcEp,
                MsgClusterId,
                matchAttributeId,
            )
            != i_sqn
        ):
            continue

        self.log.logging("Input", "Debug", "------- - Sqn matches for Attribute: %s" % matchAttributeId)
        set_status_datastruct(
            self,
            "WriteAttributes",
            MsgSrcAddr,
            MsgSrcEp,
            MsgClusterId,
            matchAttributeId,
            MsgAttrStatus,
        )
        set_request_phase_datastruct(
            self,
            "WriteAttributes",
            MsgSrcAddr,
            MsgSrcEp,
            MsgClusterId,
            matchAttributeId,
            "fullfilled",
        )
        if MsgAttrStatus != "00":
            self.log.logging(
                "Input",
                "Debug",
                "Decode8110 - Write Attribute Response response - ClusterID: %s/%s, MsgSrcAddr: %s, MsgSrcEp:%s , Status: %s"
                % (MsgClusterId, matchAttributeId, MsgSrcAddr, MsgSrcEp, MsgAttrStatus),
                MsgSrcAddr,
            )

    if MsgClusterId == "0500":
        self.iaszonemgt.receiveIASmessages(MsgSrcAddr, MsgSrcEp, 3, MsgAttrStatus)


def Decode8120(self, Devices, MsgData, MsgLQI):  # Configure Reporting response

    self.log.logging("Input", "Debug", "Decode8120 - Configure reporting response: %s" % MsgData)
    if len(MsgData) < 14:
        Domoticz.Error("Decode8120 - uncomplet message %s " % MsgData)
        return

    MsgSQN = MsgData[0:2]
    MsgSrcAddr = MsgData[2:6]
    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Error("Decode8120 - receiving Configure reporting response from unknow  %s" % MsgSrcAddr)
        return

    timeStamped(self, MsgSrcAddr, 0x8120)
    updSQN(self, MsgSrcAddr, MsgSQN)
    updLQI(self, MsgSrcAddr, MsgLQI)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)

    MsgSrcEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]

    if len(MsgData) == 14:
        # Global answer. Need i_sqn to get match
        MsgStatus = MsgData[12:14]
        Decode8120_attribute(self, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, None, MsgStatus)
    else:
        idx = 12
        while idx < len(MsgData):
            MsgAttributeId = MsgData[idx : idx + 4]
            idx += 4
            MsgStatus = MsgData[idx : idx + 2]
            idx += 4
            Decode8120_attribute(
                self,
                MsgSQN,
                MsgSrcAddr,
                MsgSrcEp,
                MsgClusterId,
                MsgAttributeId,
                MsgStatus,
            )


def Decode8120_attribute(self, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttributeId, MsgStatus):

    self.log.logging(
        "Input",
        "Debug",
        "Decode8120 --> SQN: [%s], SrcAddr: %s, SrcEP: %s, ClusterID: %s, Attribute: %s Status: %s"
        % (MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttributeId, MsgStatus),
        MsgSrcAddr,
    )

    self.configureReporting.read_configure_reporting_response(
        MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttributeId, MsgStatus
    )


def Decode8122(self, Devices, MsgData, MsgLQI):  # Read Configure Report response

    self.configureReporting.read_report_configure_response(MsgData, MsgLQI)


def Decode8139(self, Devices, MsgData, MsgLQI):
    # E_SL_MSG_ATTRIBUTE_DISCOVERY_INDIVIDUAL_RESPONSE
    #   ZNC_BUF_U8_UPD   ( &au8LinkTxBuffer [0],         psEvent->uMessage.sAttributeDiscoveryResponse.bDiscoveryComplete,    u16Length );
    #   ZNC_BUF_U8_UPD   ( &au8LinkTxBuffer [u16Length], psEvent->uMessage.sAttributeDiscoveryResponse.eAttributeDataType,    u16Length );
    #   ZNC_BUF_U16_UPD  ( &au8LinkTxBuffer [u16Length], psEvent->uMessage.sAttributeDiscoveryResponse.u16AttributeEnum,      u16Length );
    #   ZNC_BUF_U16_UPD  ( &au8LinkTxBuffer [u16Length],  psEvent->pZPSevent->uEvent.sApsDataIndEvent.uSrcAddress.u16Addr,    u16Length );
    #   ZNC_BUF_U8_UPD   ( &au8LinkTxBuffer [u16Length],  psEvent->pZPSevent->uEvent.sApsDataIndEvent.u8SrcEndpoint,          u16Length );
    #   ZNC_BUF_U16_UPD  ( &au8LinkTxBuffer [u16Length],  psEvent->psClusterInstance->psClusterDefinition->u16ClusterEnum,    u16Length );
    bDiscoveryComplete = MsgData[0:2]
    eAttributeDataType = MsgData[2:4]
    u16AttributeEnum = MsgData[4:8]
    uSrcAddress = MsgData[8:12]
    u8SrcEndpoint = MsgData[12:14]
    u16ClusterEnum = MsgData[14:18]
    self.log.logging(
        "Input",
        "Log",
        "Decode8139 - %s/%s Complete: %s Cluster: %s Attribute Type: %s Attribute: %s"
        % (uSrcAddress, u8SrcEndpoint, bDiscoveryComplete, u16ClusterEnum, eAttributeDataType, u16AttributeEnum),
    )


def Decode8140(self, Devices, MsgData, MsgLQI):  # Attribute Discovery response
    MsgComplete = MsgData[0:2]
    MsgAttType = MsgData[2:4]
    MsgAttID = MsgData[4:8]

    if MsgComplete == "01" and MsgAttType == "00" and MsgAttID == "0000":
        return

    if len(MsgData) > 8:
        MsgSrcAddr = MsgData[8:12]
        MsgSrcEp = MsgData[12:14]
        MsgClusterID = MsgData[14:18]

        self.log.logging(
            "Input",
            "Debug",
            "Decode8140 - Attribute Discovery Response - %s/%s - Cluster: %s - Attribute: %s - Attribute Type: %s Complete: %s"
            % (MsgSrcAddr, MsgSrcEp, MsgClusterID, MsgAttID, MsgAttType, MsgComplete),
            MsgSrcAddr,
        )

        if MsgSrcAddr not in self.ListOfDevices:
            return

        if "Attributes List" not in self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]["Attributes List"] = {}
            self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"] = {}
        if "Ep" not in self.ListOfDevices[MsgSrcAddr]["Attributes List"]:
            self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"] = {}
        if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"]:
            self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"][MsgSrcEp] = {}
        if MsgClusterID not in self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"][MsgSrcEp]:
            self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"][MsgSrcEp][MsgClusterID] = {}

        if (
            MsgAttID in self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"][MsgSrcEp][MsgClusterID]
            and self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"][MsgSrcEp][MsgClusterID][MsgAttID] == MsgAttType
        ):
            return

        self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"][MsgSrcEp][MsgClusterID][MsgAttID] = MsgAttType

        if MsgComplete != "01":
            next_start = "%04x" % (int(MsgAttID, 16) + 1)
            getListofAttribute(
                self,
                MsgSrcAddr,
                MsgSrcEp,
                MsgClusterID,
                start_attribute=next_start,
            )


def Decode8141(self, Devices, MsgData, MsgLQI):  # Attribute Discovery Extended response
    MsgComplete = MsgData[0:2]
    MsgAttType = MsgData[2:4]
    MsgAttID = MsgData[4:8]
    MsgAttFlag = MsgData[8:10]

    self.log.logging(
        "Input",
        "Log",
        "Decode8141 - Attribute Discovery Extended Response - MsgComplete: %s AttType: %s Attribute: %s Flag: %s"
        % (MsgComplete, MsgAttType, MsgAttID, MsgAttFlag),
    )

    if len(MsgData) > 10:
        MsgSrcAddr = MsgData[10:14]
        MsgSrcEp = MsgData[14:16]
        MsgClusterID = MsgData[16:20]

        self.log.logging(
            "Input",
            "Log",
            "Decode8141 - Attribute Discovery Extended Response - %s/%s - Cluster: %s - Attribute: %s - Attribute Type: %s Flag: %s Complete: %s"
            % (MsgSrcAddr, MsgSrcEp, MsgClusterID, MsgAttID, MsgAttType, MsgAttFlag, MsgComplete),
            MsgSrcAddr,
        )

        if MsgSrcAddr not in self.ListOfDevices:
            return

        if "Attributes List" not in self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"] = {}
            self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]["Ep"] = {}
        if "Ep" not in self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]:
            self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]["Ep"] = {}
        if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]["Ep"]:
            self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]["Ep"][MsgSrcEp] = {}
        if MsgClusterID not in self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]["Ep"][MsgSrcEp]:
            self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]["Ep"][MsgSrcEp][MsgClusterID] = {}
        if MsgAttID not in self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]["Ep"][MsgSrcEp][MsgClusterID]:
            self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]["Ep"][MsgSrcEp][MsgClusterID][MsgAttID] = {}

        self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]["Ep"][MsgSrcEp][MsgClusterID][MsgAttID][
            "Type"
        ] = MsgAttType
        self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]["Ep"][MsgSrcEp][MsgClusterID][MsgAttID]["Read"] = (
            int(MsgAttFlag, 16) & 0b00000001
        )
        self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]["Ep"][MsgSrcEp][MsgClusterID][MsgAttID]["Write"] = (
            int(MsgAttFlag, 16) & 0b00000010
        ) >> 1
        self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]["Ep"][MsgSrcEp][MsgClusterID][MsgAttID][
            "Reportable"
        ] = (int(MsgAttFlag, 16) & 0b00000100) >> 2
        self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]["Ep"][MsgSrcEp][MsgClusterID][MsgAttID]["Scene"] = (
            int(MsgAttFlag, 16) & 0b00001000
        ) >> 3
        self.ListOfDevices[MsgSrcAddr]["Attributes List Extended"]["Ep"][MsgSrcEp][MsgClusterID][MsgAttID]["Global"] = (
            int(MsgAttFlag, 16) & 0b00010000
        ) >> 4


# IAS Zone
def Decode8400(self, Devices, MsgData, MsgLQI):
    # IAS Zone Enroll Request
    sqn = MsgData[:2]
    zonetype = MsgData[2:6]
    manufacturercode = MsgData[6:10]
    nwkid = MsgData[10:14]
    ep = MsgData[14:16]
    self.log.logging(
        "Input",
        "Log",
        "Decode8400 - IAS Zone Enroll Request NwkId: %s/%s Sqn: %s ZoneType: %s Manuf: %s"
        % (nwkid, ep, sqn, zonetype, manufacturercode),
    )

    zcl_ias_zone_enroll_response(self, nwkid, ZIGATE_EP, ep, "00", "00", sqn=sqn, ackIsDisabled=False)
        
        
def Decode8401(self, Devices, MsgData, MsgLQI):  # Reception Zone status change notification

    self.log.logging(
        "Input",
        "Debug",
        "Decode8401 - Reception Zone status change notification: " + MsgData,
    )
    MsgSQN = MsgData[0:2]  # sequence number: uint8_t
    MsgEp = MsgData[2:4]  # endpoint: uint8_t
    MsgClusterId = MsgData[4:8]  # cluster id: uint16_t
    MsgSrcAddrMode = MsgData[8:10]  # src address mode: uint8_t
    if MsgSrcAddrMode == "02":
        MsgSrcAddr = MsgData[10:14]  # src address: uint64_t or uint16_t based on address mode
        MsgZoneStatus = MsgData[14:18]  # zone status: uint16_t
        MsgExtStatus = MsgData[18:20]  # extended status: uint8_t
        MsgZoneID = MsgData[20:22]  # zone id: uint8_t
        MsgDelay = MsgData[22:26]  # delay: data each element uint16_t
    elif MsgSrcAddrMode == "03":
        MsgSrcAddr = MsgData[10:26]  # src address: uint64_t or uint16_t based on address mode
        MsgZoneStatus = MsgData[26:30]  # zone status: uint16_t
        MsgExtStatus = MsgData[30:32]  # extended status: uint8_t
        MsgZoneID = MsgData[32:34]  # zone id: uint8_t
        MsgDelay = MsgData[34:38]  # delay: data each element uint16_t
    else:
        self.log.logging(
            "Input",
            "Error",
            "Decode8401 - Reception Zone status change notification but incorrect Address Mode: "
            + MsgSrcAddrMode
            + " with MsgData "
            + MsgData,
        )
        return

    # 0  0  0    0  1    1    1  2  2
    # 0  2  4    8  0    4    8  0  2
    # 5a 02 0500 02 0ffd 0010 00 ff 0001
    # 5d 02 0500 02 0ffd 0011 00 ff 0001

    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)

    if MsgSrcAddr not in self.ListOfDevices:
        Domoticz.Error("Decode8401 - unknown IAS device %s from plugin" % MsgSrcAddr)
        return
    if "Health" in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]["Health"] = "Live"

    timeStamped(self, MsgSrcAddr, 0x8401)
    updSQN(self, MsgSrcAddr, MsgSQN)
    updLQI(self, MsgSrcAddr, MsgLQI)

    if MsgSrcAddr not in self.ListOfDevices:
        self.log.logging(
            "Input",
            "Log",
            "Decode8401 - receive a message for an unknown device %s: %s" % (MsgSrcAddr, MsgData),
            MsgSrcAddr,
        )
        return

    Model = ""
    if "Model" in self.ListOfDevices[MsgSrcAddr]:
        Model = self.ListOfDevices[MsgSrcAddr]["Model"]

    self.log.logging(
        "Input",
        "Debug",
        "Decode8401 - MsgSQN: %s MsgSrcAddr: %s MsgEp:%s MsgClusterId: %s MsgZoneStatus: %s MsgExtStatus: %s MsgZoneID: %s MsgDelay: %s"
        % (
            MsgSQN,
            MsgSrcAddr,
            MsgEp,
            MsgClusterId,
            MsgZoneStatus,
            MsgExtStatus,
            MsgZoneID,
            MsgDelay,
        ),
        MsgSrcAddr,
    )
    if Model == "PST03A-v2.2.5":
        Decode8401_PST03Av225(self, Devices, MsgSrcAddr, MsgEp, Model, MsgZoneStatus)
        return

    if MsgSrcAddr not in self.ListOfDevices:
        return

    alarm1 = int(MsgZoneStatus, 16) & 1
    alarm2 = (int(MsgZoneStatus, 16) >> 1) & 1
    tamper = (int(MsgZoneStatus, 16) >> 2) & 1
    battery = (int(MsgZoneStatus, 16) >> 3) & 1
    suprrprt = (int(MsgZoneStatus, 16) >> 4) & 1
    restrprt = (int(MsgZoneStatus, 16) >> 5) & 1
    trouble = (int(MsgZoneStatus, 16) >> 6) & 1
    acmain = (int(MsgZoneStatus, 16) >> 7) & 1
    test = (int(MsgZoneStatus, 16) >> 8) & 1
    battdef = (int(MsgZoneStatus, 16) >> 9) & 1

    if "Ep" not in self.ListOfDevices[MsgSrcAddr]:
        return
    if MsgEp not in self.ListOfDevices[MsgSrcAddr]["Ep"]:
        return

    if "0500" not in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEp]:
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEp]["0500"] = {}
    if not isinstance(self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEp]["0500"], dict):
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEp][MsgClusterId]["0500"] = {}
    if "0002" not in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEp]["0500"]:
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEp]["0500"]["0002"] = {}

    self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEp]["0500"][
        "0002"
    ] = "alarm1: %s, alaram2: %s, tamper: %s, battery: %s, Support Reporting: %s, restore Reporting: %s, trouble: %s, acmain: %s, test: %s, battdef: %s" % (
        alarm1,
        alarm2,
        tamper,
        battery,
        suprrprt,
        restrprt,
        trouble,
        acmain,
        test,
        battdef,
    )

    self.log.logging(
        "Input",
        "Debug",
        "IAS Zone for device:%s  - %s" % (MsgSrcAddr, self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEp]["0500"]["0002"]),
        MsgSrcAddr,
    )

    self.log.logging(
        "Input",
        "Debug",
        "Decode8401 MsgZoneStatus: %s " % MsgZoneStatus[2:4],
        MsgSrcAddr,
    )
    value = MsgZoneStatus[2:4]

    if self.ListOfDevices[MsgSrcAddr]["Model"] in (
        "3AFE14010402000D",
        "3AFE28010402000D",
        "MOSZB-140",
        "TS0202",
        "TS0202-_TZ3210_jijr1sss",
    ):  # Konke Motion Sensor, Devlco/Frient Motion
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0406", "%02d" % alarm1)
    elif self.ListOfDevices[MsgSrcAddr]["Model"] in (
        "lumi.sensor_magnet",
        "lumi.sensor_magnet.aq2",
        "lumi.sensor_magnet.acn001",
        "lumi.magnet.acn001",
    ):  # Xiaomi Door sensor
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0006", "%02d" % alarm1)
    elif Model not in ("RC-EF-3.0", "RC-EM"):
        MajDomoDevice(
            self,
            Devices,
            MsgSrcAddr,
            MsgEp,
            MsgClusterId,
            "%02d" % (alarm1 or alarm2),
        )

    # if self.ListOfDevices[MsgSrcAddr]["Model"] in (  'MOSZB-140',):
    #    # Tamper is inverse
    #    tamper = not tamper

    if tamper:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0009", "01")
    else:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0009", "00")

    if battery:
        self.log.logging(
            "Input",
            "Log",
            "Decode8401 Low Battery or defective battery: Device: %s %s/%s" % (MsgSrcAddr, battdef, battery),
            MsgSrcAddr,
        )
        self.ListOfDevices[MsgSrcAddr]["IASBattery"] = 1
    else:
        self.ListOfDevices[MsgSrcAddr]["IASBattery"] = 100  # set to 100%

    if "IAS" in self.ListOfDevices[MsgSrcAddr] and "ZoneStatus" in self.ListOfDevices[MsgSrcAddr]["IAS"]:
        if not isinstance(self.ListOfDevices[MsgSrcAddr]["IAS"]["ZoneStatus"], dict):
            self.ListOfDevices[MsgSrcAddr]["IAS"]["ZoneStatus"] = {}

        self.ListOfDevices[MsgSrcAddr]["IAS"]["ZoneStatus"]["alarm1"] = alarm1
        self.ListOfDevices[MsgSrcAddr]["IAS"]["ZoneStatus"]["alarm2"] = alarm2
        self.ListOfDevices[MsgSrcAddr]["IAS"]["ZoneStatus"]["tamper"] = tamper
        self.ListOfDevices[MsgSrcAddr]["IAS"]["ZoneStatus"]["battery"] = battery
        self.ListOfDevices[MsgSrcAddr]["IAS"]["ZoneStatus"]["Support Reporting"] = suprrprt
        self.ListOfDevices[MsgSrcAddr]["IAS"]["ZoneStatus"]["Restore Reporting"] = restrprt
        self.ListOfDevices[MsgSrcAddr]["IAS"]["ZoneStatus"]["trouble"] = trouble
        self.ListOfDevices[MsgSrcAddr]["IAS"]["ZoneStatus"]["acmain"] = acmain
        self.ListOfDevices[MsgSrcAddr]["IAS"]["ZoneStatus"]["test"] = test
        self.ListOfDevices[MsgSrcAddr]["IAS"]["ZoneStatus"]["battdef"] = battdef
        self.ListOfDevices[MsgSrcAddr]["IAS"]["ZoneStatus"]["GlobalInfos"] = self.ListOfDevices[MsgSrcAddr]["Ep"][
            MsgEp
        ]["0500"]["0002"]
        self.ListOfDevices[MsgSrcAddr]["IAS"]["ZoneStatus"]["TimeStamp"] = int(time.time())


def Decode8401_PST03Av225(self, Devices, MsgSrcAddr, MsgEp, Model, MsgZoneStatus):

    # CLD CLD
    # bit 3, battery status (0=Ok 1=to replace)
    iData = int(MsgZoneStatus, 16) & 8 >> 3  # Set batery level
    self.ListOfDevices[MsgSrcAddr]["IASBattery"] = "100" if iData == 0 else "0"
    if MsgEp == "02":
        iData = int(MsgZoneStatus, 16) & 1  # For EP 2, bit 0 = "door/window status"
        # bit 0 = 1 (door is opened) ou bit 0 = 0 (door is closed)
        value = "%02d" % iData
        self.log.logging(
            "Input",
            "Debug",
            "Decode8401 - PST03A-v2.2.5 door/windows status: " + value,
            MsgSrcAddr,
        )
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0500", value)
        # Nota: tamper alarm on EP 2 are discarded
    elif MsgEp == "01":
        iData = int(MsgZoneStatus, 16) & 1  # For EP 1, bit 0 = "movement"
        # bit 0 = 1 ==> movement
        if iData == 1:
            value = "%02d" % iData
            self.log.logging(
                "Input",
                "Debug",
                "Decode8401 - PST03A-v2.2.5 mouvements alarm",
                MsgSrcAddr,
            )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0406", value)
        # bit 2 = 1 ==> tamper (device disassembly)
        iData = (int(MsgZoneStatus, 16) & 4) >> 2
        if iData == 1:
            value = "%02d" % iData
            self.log.logging(
                "Input",
                "Debug",
                "Decode8401 - PST03A-V2.2.5  tamper alarm",
                MsgSrcAddr,
            )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, "0006", value)
    else:
        self.log.logging(
            "Input",
            "Debug",
            "Decode8401 - PST03A-v2.2.5, unknow EndPoint: " + MsgEp,
            MsgSrcAddr,
        )
    return


# OTA and Remote decoding kindly authorized by https://github.com/ISO-B
def Decode8501(self, Devices, MsgData, MsgLQI):  # OTA image block request
    "BLOCK_REQUEST  0x8501  ZiGate will receive this command when device asks OTA firmware"

    if self.OTA:
        self.OTA.ota_request_firmware(MsgData)


def Decode8503(self, Devices, MsgData, MsgLQI):  # OTA image block request
    # 'UPGRADE_END_REQUEST    0x8503  Device will send this when it has received last part of firmware'

    if self.OTA:
        self.OTA.ota_request_firmware_completed(MsgData)


# Router Discover
def Decode8701(self, Devices, MsgData, MsgLQI):  # Reception Router Disovery Confirm Status

    MsgLen = len(MsgData)
    self.log.logging("Input", "Debug", "Decode8701 - MsgData: %s MsgLen: %s" % (MsgData, MsgLen))

    if MsgLen < 4:
        return

    # This is the reverse of what is documented. Suspecting that we got a BigEndian uint16 instead of 2 uint8
    NwkStatus = MsgData[0:2]
    Status = MsgData[2:4]
    MsgSrcAddr = ""
    MsgSrcIEEE = ""

    if MsgLen >= 8:
        MsgSrcAddr = MsgData[4:8]
        if MsgSrcAddr in self.ListOfDevices:
            MsgSrcIEEE = self.ListOfDevices[MsgSrcAddr]["IEEE"]

    if NwkStatus != "00":
        self.log.logging(
            "Input",
            "Log",
            "Decode8701 - Route discovery has been performed for %s, status: %s - %s Nwk Status: %s - %s "
            % (
                MsgSrcAddr,
                Status,
                DisplayStatusCode(Status),
                NwkStatus,
                DisplayStatusCode(NwkStatus),
            ),
        )

    self.log.logging(
        "Input",
        "Debug",
        "Decode8701 - Route discovery has been performed for %s %s, status: %s Nwk Status: %s "
        % (MsgSrcAddr, MsgSrcIEEE, Status, NwkStatus),
    )


# Réponses APS
def Decode8702(self, Devices, MsgData, MsgLQI):  # Reception APS Data confirm fail
    # Nothing to do as handled in transport.py
    return


# Device Announce
def Decode004D(self, Devices, MsgData, MsgLQI):  # Reception Device announce

    device_annoucementv2(self, Devices, MsgData, MsgLQI)


# Remote
def Decode8085(self, Devices, MsgData, MsgLQI):
    "Remote button pressed"

    MsgSQN = MsgData[:2]
    MsgEP = MsgData[2:4]
    MsgClusterId = MsgData[4:8]
    unknown_ = MsgData[8:10]
    MsgSrcAddr = MsgData[10:14]
    MsgCmd = MsgData[14:16]

    updLQI(self, MsgSrcAddr, MsgLQI)
    self.log.logging( "Input", 'Debug', "Decode8085 - MsgData: %s"  %MsgData, MsgSrcAddr)
    self.log.logging(
        "Input",
        "Debug",
        "Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s "
        % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_),
        MsgSrcAddr,
    )

    if MsgSrcAddr not in self.ListOfDevices:
        return

    if self.ListOfDevices[MsgSrcAddr]["Status"] != "inDB":
        return

    if check_duplicate_sqn(self, MsgSrcAddr, MsgEP, MsgClusterId, MsgSQN):
        return

    updSQN(self, MsgSrcAddr, MsgSQN)
    updLQI(self, MsgSrcAddr, MsgLQI)
    timeStamped(self, MsgSrcAddr, 0x8085)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)

    if "Model" not in self.ListOfDevices[MsgSrcAddr]:
        Domoticz.Log("Decode8085 - No Model Name !")
        return

    _ModelName = self.ListOfDevices[MsgSrcAddr]["Model"]

    if _ModelName in ("TRADFRI remote control", "Remote Control N2"):
        # 5 Butons remote
        ikea_remote_control_8085(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_)

    elif _ModelName in ("ROM001",):
        # ZigateRead - MsgType: 8095, MsgLength: 000b, MsgCRC: 19, Data: 00010006029b6e400000, LQI: 183
        # Apr 19 14:19:59 rasp domoticz[31994]: 2021-04-19 14:19:59.194  DIN3-Zigate: (DIN3-Zigate) Decode8095 - SQN: 00, Addr: 9b6e, Ep: 01, Cluster: 0006, Cmd: 40, Unknown: 02
        self.log.logging("Input", "Debug", "Decode8085 - Philips Hue ROM001  MsgCmd: %s" % MsgCmd, MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0008", "move")

    elif _ModelName in (
        "TRADFRI onoff switch",
        "TRADFRI on/off switch",
        "TRADFRI SHORTCUT Button",
        "TRADFRI openclose remote",
        "TRADFRI open/close remote",
    ):
        # Ikea Switch On/Off
        ikea_remote_switch_8085(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_)

    elif _ModelName == "RC 110":
        if MsgClusterId != "0008":
            self.log.logging(
                "Input",
                "Log",
                "Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s"
                % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_),
            )
            self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)
            return

        step_mod, up_down, step_size, transition = extract_info_from_8085(MsgData)

        self.log.logging(
            "Input",
            "Log",
            "Decode8085 - INNR RC 110 step_mod: %s direction: %s, size: %s, transition: %s"
            % (step_mod, up_down, step_size, transition),
            MsgSrcAddr,
        )

        TYPE_ACTIONS = {
            None: "",
            "01": "move",
            "02": "click",
            "03": "stop",
            "04": "move_to",
        }
        DIRECTION = {None: "", "00": "up", "01": "down"}
        SCENES = {
            None: "",
            "02": "scene1",
            "34": "scene2",
            "66": "scene3",
            "99": "scene4",
            "c2": "scene5",
            "fe": "scene6",
        }

        if TYPE_ACTIONS[step_mod] in ("click", "move"):
            selector = TYPE_ACTIONS[step_mod] + DIRECTION[up_down]
        elif TYPE_ACTIONS[step_mod] in "move_to":
            selector = SCENES[up_down]
        elif TYPE_ACTIONS[step_mod] in "stop":
            selector = TYPE_ACTIONS[step_mod]
        else:
            return

        self.log.logging(
            "Input",
            "Debug",
            "Decode8085 - INNR RC 110 selector: %s" % selector,
            MsgSrcAddr,
        )
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, selector)
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = selector

    elif _ModelName == "TRADFRI wireless dimmer":
        ikea_wireless_dimer_8085(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, MsgData)

    elif _ModelName in LEGRAND_REMOTE_SWITCHS:
        legrand_remote_switch_8085(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, MsgData)

    elif _ModelName in LEGRAND_REMOTE_MOTION:
        legrand_motion_8085(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, MsgData)
        step_mod, up_down, step_size, transition = extract_info_from_8085(MsgData)
        self.log.logging(
            "Input",
            "Log",
            "Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s step_mode: %s up_down: %s step_size: %s transition: %s"
            % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, step_mod, up_down, step_size, transition),
            MsgSrcAddr,
        )

    elif _ModelName == "Lightify Switch Mini":

        # OSRAM Lightify Switch Mini
        # Force Ep 03 to update Domoticz Widget

        step_mod, up_down, step_size, transition = extract_info_from_8085(MsgData)

        self.log.logging(
            "Input",
            "Log",
            "Decode8085 - OSRAM Lightify Switch Mini %s/%s: Mod %s, UpDown %s Size %s Transition %s"
            % (MsgSrcAddr, MsgEP, step_mod, up_down, step_size, transition),
        )

        if MsgCmd == "04":  # Appui court boutton central
            self.log.logging(
                "Input",
                "Log",
                "Decode8085 - OSRAM Lightify Switch Mini %s/%s Central button" % (MsgSrcAddr, MsgEP),
            )
            MajDomoDevice(self, Devices, MsgSrcAddr, "03", MsgClusterId, "02")

        elif MsgCmd == "05":  # Appui Long Top button
            self.log.logging(
                "Input",
                "Log",
                "Decode8085 - OSRAM Lightify Switch Mini %s/%s Long press Up button" % (MsgSrcAddr, MsgEP),
            )
            MajDomoDevice(self, Devices, MsgSrcAddr, "03", MsgClusterId, "03")

        elif MsgCmd == "01":  # Appui Long Botton button
            self.log.logging(
                "Input",
                "Log",
                "Decode8085 - OSRAM Lightify Switch Mini %s/%s Long press Down button" % (MsgSrcAddr, MsgEP),
            )
            MajDomoDevice(self, Devices, MsgSrcAddr, "03", MsgClusterId, "04")

        elif MsgCmd == "03":  # Release
            self.log.logging(
                "Input",
                "Log",
                "Decode8085 - OSRAM Lightify Switch Mini %s/%s release" % (MsgSrcAddr, MsgEP),
            )

        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)

    elif _ModelName in (
        "lumi.remote.b686opcn01-bulb",
        "lumi.remote.b486opcn01-bulb",
        "lumi.remote.b286opcn01-bulb",
    ):
        AqaraOppleDecoding(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, _ModelName, MsgData)

    elif _ModelName == "tint-Remote-white":
        #                           Command   Mode   Step   Transtition Time
        # Dim-:      0001 0008 02 e471  02        01     2b     000a
        # Dim+:      0001 0008 02 e471  02        00     2b     000a
        # Move down: 0001 0008 02 e471  01        0164
        # Stop     : 0101 0008 02 e471  03
        # Move Up  : 0001 0008 02 e471  05
        # Stop     : 0101 0008 02 e471  03
        if MsgCmd == "02":  # Command
            MsgMode = MsgData[16:18]
            if MsgMode == "01":  # Dim -
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "04")
            elif MsgMode == "00":  # Dim +
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "05")

        if MsgCmd == "01":  # Move Down
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "06")

        if MsgCmd == "05":  # Move Up
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "07")

        if MsgCmd == "03":  # Stop
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "08")

    elif "Manufacturer" in self.ListOfDevices[MsgSrcAddr]:
        if self.ListOfDevices[MsgSrcAddr]["Manufacturer"] == "1110":  # Profalux
            self.log.logging("Input", "Log", "MsgData: %s" % MsgData)

            TYPE_ACTIONS = {None: "", "03": "stop", "05": "move"}
            DIRECTION = {None: "", "00": "up", "01": "down"}

            step_mod, up_down, step_size, transition = extract_info_from_8085(MsgData)

            self.log.logging("Input", "Log", "step_mod: %s" % step_mod)

            if step_mod in TYPE_ACTIONS:
                Domoticz.Error("Decode8085 - Profalux Remote, unknown Action: %s" % step_mod)

            selector = None

            if TYPE_ACTIONS[step_mod] in ("move"):
                selector = TYPE_ACTIONS[step_mod] + DIRECTION[up_down]
            elif TYPE_ACTIONS[step_mod] in ("stop"):
                selector = TYPE_ACTIONS[step_mod]
            else:
                Domoticz.Error(
                    "Decode8085 - Profalux remote Unknown state for %s step_mod: %s up_down: %s"
                    % (MsgSrcAddr, step_mod, up_down)
                )

            self.log.logging(
                "Input",
                "Debug",
                "Decode8085 - Profalux remote selector: %s" % selector,
                MsgSrcAddr,
            )
            if selector:
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, selector)

    elif _ModelName == "TS1001":

        step_mod, up_down, step_size, transition = extract_info_from_8085(MsgData)
        self.log.logging(
            "Input",
            "Log",
            "Decode8085 - Lidl Remote SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s step_mod: %s step_size: %s up_down: %s"
            % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, step_mod, step_size, up_down),
        )

    else:
        self.log.logging(
            "Input",
            "Log",
            "Decode8085 - Model: %s SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s "
            % (_ModelName, MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_),
        )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)


def Decode8095(self, Devices, MsgData, MsgLQI):
    "Remote button pressed ON/OFF"

    MsgSQN = MsgData[:2]
    MsgEP = MsgData[2:4]
    MsgClusterId = MsgData[4:8]
    unknown_ = MsgData[8:10]
    MsgSrcAddr = MsgData[10:14]
    MsgCmd = MsgData[14:16]
    MsgPayload = MsgData[16 : len(MsgData)] if len(MsgData) > 16 else None
    updLQI(self, MsgSrcAddr, MsgLQI)
    self.log.logging( "Input", 'Debug', "Decode8095 - MsgData: %s"  %MsgData, MsgSrcAddr)

    self.log.logging(
        "Input",
        "Debug",
        "Decode8095 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Payload: %s Unknown: %s "
        % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgPayload, unknown_),
        MsgSrcAddr,
    )

    if MsgSrcAddr not in self.ListOfDevices:
        return

    if self.ListOfDevices[MsgSrcAddr]["Status"] != "inDB":
        return

    if check_duplicate_sqn(self, MsgSrcAddr, MsgEP, MsgClusterId, MsgSQN):
        return

    updSQN(self, MsgSrcAddr, MsgSQN)
    updLQI(self, MsgSrcAddr, MsgLQI)
    timeStamped(self, MsgSrcAddr, 0x8095)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)

    if "Model" not in self.ListOfDevices[MsgSrcAddr]:
        return

    _ModelName = self.ListOfDevices[MsgSrcAddr]["Model"]

    if _ModelName in ("TRADFRI remote control", "Remote Control N2"):
        # Ikea Remote 5 buttons round.
        # ( cmd, directioni, cluster )
        # ( 0x02, 0x0006) - click middle button - Action Toggle On/Off Off/on
        ikea_remote_control_8095(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_)

    elif _ModelName in ("ROM001",):
        # ZigateRead - MsgType: 8085, MsgLength: 000d, MsgCRC: 43, Data: 0a010008029b6e02011e0009, LQI: 171
        # Decode8085 - SQN: 0a, Addr: 9b6e, Ep: 01, Cluster: 0008, Cmd: 02, Unknown: 02
        # ZigateRead - MsgType: 8085, MsgLength: 000d, MsgCRC: 64, Data: 0b010008029b6e0201380009, LQI: 171
        # Decode8085 - SQN: 0b, Addr: 9b6e, Ep: 01, Cluster: 0008, Cmd: 02, Unknown: 02
        self.log.logging("Input", "Debug", "Decode8095 - Philips Hue ROM001  MsgCmd: %s" % MsgCmd, MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0008", "toggle")

    elif _ModelName == "TRADFRI motion sensor":
        # Ikea Motion Sensor
        ikea_motion_sensor_8095(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_)

    elif _ModelName in (
        "TRADFRI onoff switch",
        "TRADFRI on/off switch",
        "TRADFRI SHORTCUT Button",
        "TRADFRI openclose remote",
        "TRADFRI open/close remote",
    ):
        # Ikea Switch On/Off
        ikea_remote_switch_8095(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_)

    elif _ModelName == "RC 110":
        # INNR RC 110 Remote command

        ONOFF_TYPE = {"40": "onoff_with_effect", "00": "off", "01": "on"}
        delayed_all_off = effect_variant = None
        if len(MsgData) >= 16:
            delayed_all_off = MsgData[16:18]
        if len(MsgData) >= 18:
            effect_variant = MsgData[18:20]

        if MsgCmd in ONOFF_TYPE and ONOFF_TYPE[MsgCmd] in ("on", "off"):
            self.log.logging(
                "Input",
                "Log",
                "Decode8095 - RC 110 ON/Off Command from: %s/%s Cmd: %s Delayed: %s Effect: %s"
                % (MsgSrcAddr, MsgEP, MsgCmd, delayed_all_off, effect_variant),
                MsgSrcAddr,
            )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd)
            self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)
        else:
            self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)
            self.log.logging(
                "Input",
                "Log",
                "Decode8095 - RC 110 Unknown Command: %s for %s/%s, Cmd: %s, Unknown: %s "
                % (MsgCmd, MsgSrcAddr, MsgEP, MsgCmd, unknown_),
                MsgSrcAddr,
            )

    elif _ModelName in LEGRAND_REMOTE_SWITCHS:
        # Legrand remote switch
        legrand_remote_switch_8095(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_)

    elif _ModelName in LEGRAND_REMOTE_MOTION:
        legrand_motion_8095(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_)
        self.log.logging(
            "Input",
            "Log",
            "Decode8095 - Legrand: %s/%s, Cmd: %s, Unknown: %s " % (MsgSrcAddr, MsgEP, MsgCmd, unknown_),
            MsgSrcAddr,
        )
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0406", unknown_)

    elif _ModelName == "Lightify Switch Mini":
        #        OSRAM Lightify Switch Mini

        # All messages are redirected to 1 Ep in order to process them easyly
        if MsgCmd in ("00", "01"):  # On
            self.log.logging(
                "Input",
                "Log",
                "Decode8095 - OSRAM Lightify Switch Mini: %s/%s, Cmd: %s, Unknown: %s "
                % (MsgSrcAddr, MsgEP, MsgCmd, unknown_),
                MsgSrcAddr,
            )
            MajDomoDevice(self, Devices, MsgSrcAddr, "03", MsgClusterId, MsgCmd)
            self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)
        else:
            self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)
            self.log.logging(
                "Input",
                "Log",
                "Decode8095 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s "
                % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_),
                MsgSrcAddr,
            )

    elif _ModelName in ("lumi.remote.b686opcn01-bulb", "lumi.remote.b486opcn01-bulb", "lumi.remote.b286opcn01-bulb"):
        AqaraOppleDecoding(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, _ModelName, MsgData)

    elif _ModelName == "WB01":
        # 0x02 -> 1 Click
        # 0x01 -> 2 Click
        # 0x00 -> Long Click
        if MsgCmd == "00":
            WidgetSelector = "03"
        elif MsgCmd == "01":
            WidgetSelector = "02"
        elif MsgCmd == "02":
            WidgetSelector = "01"
        else:
            return
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0006", WidgetSelector)

    elif _ModelName == "KF204":  # CASA IA
        # Decode8095 - SQN: 07, Addr: ad12, Ep: 02, Cluster: 0006, Cmd: 00, Unknown: 02 ( Button X)
        # Decode8095 - SQN: 08, Addr: ad12, Ep: 02, Cluster: 0006, Cmd: 01, Unknown: 02 ( Button 0)
        if MsgCmd == "00":
            MajDomoDevice(self, Devices, MsgSrcAddr, "01", "0006", "02")
        elif MsgCmd == "01":
            MajDomoDevice(self, Devices, MsgSrcAddr, "01", "0006", "01")

    elif _ModelName in ("TS0041", "TS0043", "TS0044", "TS0042", "TS004F", "TS004F-_TZ3000_xabckq1v"):  # Tuya remote
        self.log.logging(
            "Input",
            "Debug",
            "Decode8095 - Tuya %s  Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, MsgPayload: %s "
            % (_ModelName, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgPayload),
            MsgSrcAddr,
        )
        if MsgCmd[:2] == "fd" and MsgPayload:
            if MsgPayload == "00":
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0006", "01")  # Click
                checkAndStoreAttributeValue(self, MsgSrcAddr, MsgEP, MsgClusterId, "0000", MsgPayload)
            elif MsgPayload == "01":
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0006", "02")  # Double Click
                checkAndStoreAttributeValue(self, MsgSrcAddr, MsgEP, MsgClusterId, "0000", MsgPayload)
            elif MsgPayload == "02":
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0006", "03")  # Long Click
                checkAndStoreAttributeValue(self, MsgSrcAddr, MsgEP, MsgClusterId, "0000", MsgPayload)
            elif MsgPayload == "03":
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0006", "04")  # Long Click
                checkAndStoreAttributeValue(self, MsgSrcAddr, MsgEP, MsgClusterId, "0000", MsgPayload)

    elif _ModelName == "TS1001":  # Tuya Lidl
        self.log.logging(
            "Input",
            "Log",
            "Decode8095 - Lidl Remote SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s"
            % (
                MsgSQN,
                MsgSrcAddr,
                MsgEP,
                MsgClusterId,
                MsgCmd,
                unknown_,
            ),
        )

    else:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0006", str(int(MsgCmd, 16)))
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)
        self.log.logging(
            "Input",
            "Log",
            "Decode8095 - Model: %s SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s "
            % (_ModelName, MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_),
            MsgSrcAddr,
        )


def Decode80A7(self, Devices, MsgData, MsgLQI):
    "Remote button pressed (LEFT/RIGHT)"

    MsgSQN = MsgData[:2]
    MsgEP = MsgData[2:4]
    MsgClusterId = MsgData[4:8]
    MsgCmd = MsgData[8:10]
    MsgDirection = MsgData[10:12]
    unkown_ = MsgData[12:18]
    MsgSrcAddr = MsgData[18:22]

    # Ikea Remote 5 buttons round.
    #  ( cmd, directioni, cluster )
    #  ( 0x07, 0x00, 0005 )  Click right button
    #  ( 0x07, 0x01, 0005 )  Click left button

    TYPE_DIRECTIONS = {"00": "right", "01": "left", "02": "middle"}
    TYPE_ACTIONS = {"07": "click", "08": "hold", "09": "release"}
    self.log.logging( "Input", 'Debug', "Decode80A7 - MsgData: %s"  %MsgData, MsgSrcAddr)
    self.log.logging(
        "Input",
        "Debug",
        "Decode80A7 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Direction: %s, Unknown_ %s"
        % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_),
        MsgSrcAddr,
    )
    if MsgSrcAddr not in self.ListOfDevices:
        return
    if self.ListOfDevices[MsgSrcAddr]["Status"] != "inDB":
        return

    updLQI(self, MsgSrcAddr, MsgLQI)

    check_duplicate_sqn(self, MsgSrcAddr, MsgEP, MsgClusterId, MsgSQN)

    timeStamped(self, MsgSrcAddr, 0x80A7)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    if "Model" not in self.ListOfDevices[MsgSrcAddr]:
        return

    if MsgClusterId == "0005" and MsgDirection not in TYPE_DIRECTIONS:
        # Might be in the case of Release Left or Right
        self.log.logging(
            "Input",
            "Log",
            "Decode80A7 - Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Direction: %s, Unknown_ %s"
            % (MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_),
        )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, Direction: %s, %s" % (
            MsgCmd,
            MsgDirection,
            unkown_,
        )

    elif MsgClusterId == "0005" and MsgCmd in TYPE_ACTIONS:
        selector = TYPE_DIRECTIONS[MsgDirection] + "_" + TYPE_ACTIONS[MsgCmd]
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", selector)
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = selector
        self.log.logging("Input", "Debug", "Decode80A7 - selector: %s" % selector, MsgSrcAddr)

        if self.groupmgt and TYPE_DIRECTIONS[MsgDirection] in (
            "right",
            "left",
        ):
            self.groupmgt.manageIkeaTradfriRemoteLeftRight(MsgSrcAddr, TYPE_DIRECTIONS[MsgDirection])
    else:
        self.log.logging(
            "Input",
            "Log",
            "Decode80A7 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Direction: %s, Unknown_ %s"
            % (
                MsgSQN,
                MsgSrcAddr,
                MsgEP,
                MsgClusterId,
                MsgCmd,
                MsgDirection,
                unkown_,
            ),
        )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, Direction: %s, %s" % (
            MsgCmd,
            MsgDirection,
            unkown_,
        )


def Decode8806(self, Devices, MsgData, MsgLQI):

    ATTENUATION_dBm = {
        "JN516x": {0: 0, 52: -9, 40: -20, 32: -32},
        "JN516x M05": {0: 9.5, 52: -3, 40: -15, 31: -26},
    }

    self.log.logging("Input", "Debug", "Decode8806 - MsgData: %s" % MsgData)

    TxPower = MsgData[0:2]
    self.ControllerData["Tx-Power"] = TxPower

    if int(TxPower, 16) in ATTENUATION_dBm["JN516x"]:
        self.ControllerData["Tx-Attenuation"] = ATTENUATION_dBm["JN516x"][int(TxPower, 16)]
        self.log.logging(
            "Input",
            "Status",
            "TxPower Attenuation: %s dBm" % ATTENUATION_dBm["JN516x"][int(TxPower, 16)],
        )
    else:
        self.log.logging("Input", "Status", "Confirming Set TxPower: %s" % int(TxPower, 16))


def Decode8807(self, Devices, MsgData, MsgLQI):

    ATTENUATION_dBm = {
        "JN516x": {0: 0, 52: -9, 40: -20, 32: -32},
        "JN516x M05": {0: 9.5, 52: -3, 40: -15, 31: -26},
    }

    Domoticz.Debug("Decode8807 - MsgData: %s" % MsgData)

    TxPower = MsgData[0:2]
    self.ControllerData["Tx-Power"] = TxPower
    if int(TxPower, 16) in ATTENUATION_dBm["JN516x"]:
        self.ControllerData["Tx-Attenuation"] = ATTENUATION_dBm["JN516x"][int(TxPower, 16)]
        self.log.logging(
            "Input",
            "Status",
            "Get TxPower Attenuation: %s dBm" % ATTENUATION_dBm["JN516x"][int(TxPower, 16)],
        )
    else:
        self.log.logging("Input", "Status", "Get TxPower: %s" % int(TxPower, 16))


def Decode7000(self, Devices, MsgData, MsgLQI):
    #  ZNC_BUF_U16_UPD ( &au8LinkTxBuffer [0],          pZPSevent->uEvent.sApsDataIndEvent.uSrcAddress.u16Addr,     u16Length );
    #  ZNC_BUF_U8_UPD  ( &au8LinkTxBuffer [u16Length],  pZPSevent->uEvent.sApsDataIndEvent.u8SrcEndpoint,     u16Length );
    #  ZNC_BUF_U16_UPD ( &au8LinkTxBuffer [u16Length],  pZPSevent->uEvent.sApsDataIndEvent.u16ClusterId,     u16Length );
    #  ZNC_BUF_U8_UPD  ( &au8LinkTxBuffer [u16Length],  sZCL_HeaderParams.bDirection,          u16Length );
    #  ZNC_BUF_U8_UPD  ( &au8LinkTxBuffer [u16Length],  sZCL_HeaderParams.bDisableDefaultResponse,     u16Length );
    #  ZNC_BUF_U8_UPD  ( &au8LinkTxBuffer [u16Length],  sZCL_HeaderParams.bManufacturerSpecific,     u16Length );
    #  ZNC_BUF_U8_UPD  ( &au8LinkTxBuffer [u16Length],  sZCL_HeaderParams.eFrameType,     u16Length );
    #  ZNC_BUF_U16_UPD ( &au8LinkTxBuffer [u16Length],  sZCL_HeaderParams.u16ManufacturerCode,     u16Length );
    #  ZNC_BUF_U8_UPD  ( &au8LinkTxBuffer [u16Length],  sZCL_HeaderParams.u8CommandIdentifier,     u16Length );
    #  ZNC_BUF_U8_UPD  ( &au8LinkTxBuffer [u16Length],  sZCL_HeaderParams.u8TransactionSequenceNumber,     u16Length );

    uSrcAddress = MsgData[0:4]
    u8SrcEndpoint = MsgData[4:6]
    u16ClusterId = MsgData[6:10]
    bDirection = MsgData[10:12]
    bDisableDefaultResponse = MsgData[12:14]
    bManufacturerSpecific = MsgData[14:16]
    eFrameType = MsgData[16:18]
    u16ManufacturerCode = MsgData[18:22]
    u8CommandIdentifier = MsgData[22:24]
    u8TransactionSequenceNumber = MsgData[24:26]

    if uSrcAddress not in self.ListOfDevices:
        return

    self.log.logging(
        "Input",
        "Debug",
        "Decode7000 - Default Response Notification [%s] %s/%s Cluster: %s DefaultReponse: %s ManufSpec: %s ManufCode: %s Command: %s Direction: %s FrameType: %s"
        % (
            u8TransactionSequenceNumber,
            uSrcAddress,
            u8SrcEndpoint,
            u16ClusterId,
            bDisableDefaultResponse,
            bManufacturerSpecific,
            u16ManufacturerCode,
            u8CommandIdentifier,
            bDirection,
            eFrameType,
        ),
    )

    if bDisableDefaultResponse == "00":  # If Default Response required
        send_default_response(
            self,
            uSrcAddress,
            u8SrcEndpoint,
            u16ClusterId,
            bDirection,
            bDisableDefaultResponse,
            bManufacturerSpecific,
            u16ManufacturerCode,
            eFrameType,
            u8CommandIdentifier,
            u8TransactionSequenceNumber,
        )


def check_duplicate_sqn(self, Nwkid, Ep, Cluster, Sqn):
    if "Ep" in self.ListOfDevices[Nwkid] and Ep in self.ListOfDevices[Nwkid]["Ep"]:
        if Cluster not in self.ListOfDevices[Nwkid]["Ep"][Ep]:
            self.ListOfDevices[Nwkid]["Ep"][Ep][Cluster] = {}
        if not isinstance(self.ListOfDevices[Nwkid]["Ep"][Ep][Cluster], dict):
            self.ListOfDevices[Nwkid]["Ep"][Ep][Cluster] = {}
        if "0000" not in self.ListOfDevices[Nwkid]["Ep"][Ep][Cluster]:
            self.ListOfDevices[Nwkid]["Ep"][Ep][Cluster]["0000"] = {}

    return Sqn != "00" and "SQN" in self.ListOfDevices[Nwkid] and Sqn == self.ListOfDevices[Nwkid]["SQN"]
