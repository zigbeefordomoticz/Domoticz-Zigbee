# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#


import struct
from Zigbee.encoder_tools import encapsulate_plugin_frame

def is_duplicate_zdp_frame(self, Nwkid, ClusterId, Sqn):
    
    if self.zigbee_communication != "zigpy":
        return False
    if Nwkid not in self.ListOfDevices:
        return False
    if Nwkid == "0000":
        return False
    if "ZDP-IN-SQN" not in self.ListOfDevices[ Nwkid ]:
        self.ListOfDevices[ Nwkid ]["ZDP-IN-SQN"] = {}
    if ClusterId not in self.ListOfDevices[ Nwkid ]["ZDP-IN-SQN"]:
        self.ListOfDevices[ Nwkid ]["ZDP-IN-SQN"][ ClusterId ] = Sqn
        return False
    if Sqn == self.ListOfDevices[ Nwkid ]["ZDP-IN-SQN"][ ClusterId ]:
        return True
    self.ListOfDevices[ Nwkid ]["ZDP-IN-SQN"][ ClusterId ] = Sqn
    return False


def zdp_decoders(self, SrcNwkId, SrcEndPoint, TargetEp, ClusterId, Payload, frame):
    # self.logging_8002( 'Debug', "zdp_decoders NwkId: %s Ep: %s Cluster: %s Payload: %s" %(SrcNwkId, SrcEndPoint, ClusterId , Payload))
    self.log.logging("zdpDecoder", "Debug", "===> zdp_decoders %s %s %s %s" % (SrcNwkId, SrcEndPoint, ClusterId, Payload))

    if ClusterId == "0000":
        # NWK_addr_req
        return buildframe_NWK_addr_req(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "0001":
        # IEEE_addr_req
        return buildframe_IEEE_addr_req(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "0002":
        # Node_Desc_req
        return buildframe_Node_Desc_req(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "0003":
        # Power_Desc_req
        self.log.logging("zdpDecoder", "Debug", "Power_Desc_req NOT IMPLEMENTED YET")
        return frame

    if ClusterId == "0036":
        self.log.logging("zdpDecoder", "Debug", "Mgmt_Permit_Joining_req NOT IMPLEMENTED %s" %Payload)
        return None

    if ClusterId == "0013":
        return buildframe_device_annoucement(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8000":
        # NWK_addr_rsp
        return buildframe_nwk_address_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8001":
        # IEEE_addr_rsp
        return buildframe_ieee_address_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8002":
        # Node_Desc_rsp
        return buildframe_node_descriptor_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8003":
        # Power_Desc_rsp
        return buildframe_power_description_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8004":
        return buildframe_simple_descriptor_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8005":
        return buildframe_active_endpoint_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8006":
        # Match_Desc_rsp
        return buildframe_match_description_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8010":
        # Complex_Desc_rsp
        return buildframe_complex_description_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8011":
        # User_Desc_rsp
        return buildframe_user_description_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8021":
        return buildframe_bind_response_command(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8022":
        return buildframe_unbind_response_command(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8030":
        # Mgmt_NWK_Disc_rsp
        return buildframe_management_nwk_discovery_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8031":
        # Mgmt_Lqi_rsp
        return buildframe_management_lqi_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId in ( "8032", "8033"):
        # handle directly as raw in Modules/inputs/Decode8002
        # Mgmt_Rtg_rsp and Mgmt_Bind_rsp
        return frame

    if ClusterId == "8034":
        # Mgmt_Leave_rsp
        return buildframe_leave_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8035":
        # Mgmt_Direct_Join_rsp
        return buildframe_direct_join_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8036":
        # Mgmt_Permit_Joining_rsp
        return buildframe_permit_join_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8038":
        # Mgmt_NWK_Update_notify
        return buildframe_management_nwk_update_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    return frame


def buildframe_NWK_addr_req(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Debug", "buildframe_NWK_addr_req nwkid: %s Ep: %s Payload: %s" % (SrcNwkId, SrcEndPoint, Payload))
    sqn = Payload[:2]
    ieee = "%016x" % struct.unpack("Q", struct.pack(">Q", int(Payload[2:18], 16)))[0]
    u8RequestType = Payload[18:20]
    u8StartIndex = Payload[20:22]
    buildPayload = sqn + SrcNwkId + SrcEndPoint + ieee + u8RequestType + u8StartIndex
    return encapsulate_plugin_frame("0040", buildPayload, frame[len(frame) - 4 : len(frame) - 2])

    
def buildframe_IEEE_addr_req(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Debug", "buildframe_IEEE_addr_req nwkid: %s Ep: %s Payload: %s" % (SrcNwkId, SrcEndPoint, Payload))
    sqn = Payload[:2]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[2:6], 16)))[0]
    u8RequestType = Payload[6:8]
    u8StartIndex = Payload[8:10]
    buildPayload = sqn + SrcNwkId + SrcEndPoint + nwkid + u8RequestType + u8StartIndex
    return encapsulate_plugin_frame("0041", buildPayload, frame[len(frame) - 4 : len(frame) - 2])
    
def buildframe_Node_Desc_req(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Debug", "buildframe_Node_Desc_req nwkid: %s Ep: %s Payload: %s" % (SrcNwkId, SrcEndPoint, Payload))
    sqn = Payload[:2]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[2:6], 16)))[0]
    buildPayload = sqn + SrcNwkId + SrcEndPoint + nwkid
    return encapsulate_plugin_frame("0042", buildPayload, frame[len(frame) - 4 : len(frame) - 2])
    
def buildframe_device_annoucement(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    # Device Annoucement

    if len(Payload) != 24:
        self.log.logging("zdpDecoder", "Error", "buildframe_device_annoucement not a Device Annoucement frame %s" % (Payload))
        return frame
        
        
    sqn = Payload[:2]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[2:6], 16)))[0]
    ieee = "%016x" % struct.unpack("Q", struct.pack(">Q", int(Payload[6:22], 16)))[0]
    maccapa = Payload[22:24]

    self.log.logging("zdpDecoder", "Debug", "buildframe_device_annoucement sqn: %s nwkid: %s ieee: %s maccapa: %s" % (sqn, nwkid, ieee, maccapa))

    buildPayload = nwkid + ieee + maccapa
    return encapsulate_plugin_frame("004d", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_node_descriptor_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    sqn = Payload[:2]
    status = Payload[2:4]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[4:8], 16)))[0]
    self.log.logging("zdpDecoder", "Debug", "buildframe_node_descriptor_response for %s with status %s nwkid: %s SrcNwkId: %s Payload: %s" %(
        nwkid, status, nwkid, SrcNwkId, Payload ))    
    
    if status != "00":
        # Error
        # 0x80  Invalid request Type
        # 0x81  Device not found
        # 0x89  No Descriptor
        self.log.logging("zdpDecoder", "Debug", "buildframe_node_descriptor_response for %s with status %s" %(nwkid, status))
        buildPayload = sqn + status + nwkid
    else:
        bitfield_16 = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[8:12], 16)))[0]
        mac_capa_8 = Payload[12:14]
        manuf_code_16 = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[14:18], 16)))[0]
        max_buf_size_8 = Payload[18:20]
        max_in_size_16 = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[20:24], 16)))[0]
        server_mask_16 = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[24:28], 16)))[0]
        max_out_size_16 = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[28:32], 16)))[0]
        descriptor_capability_field_8 = Payload[32:34]
        self.log.logging("zdpDecoder", "Debug", "buildframe_node_descriptor_response sqn: %s nwkid: %s Manuf: %s MacCapa: %s" % (
            sqn, nwkid, manuf_code_16, mac_capa_8))
        buildPayload = sqn + status + nwkid + manuf_code_16 + max_in_size_16 + max_out_size_16
        buildPayload += server_mask_16 + descriptor_capability_field_8 + mac_capa_8 + max_buf_size_8 + bitfield_16

    return encapsulate_plugin_frame("8042", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_active_endpoint_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    # Active End Point Response
    sqn = Payload[:2]
    status = Payload[2:4]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[4:8], 16)))[0]
    if status != "00":
        buildPayload = sqn + status + nwkid
    else:
        nbEp = Payload[8:10]
        ep_list = Payload[10:]
        buildPayload = sqn + status + nwkid + nbEp + ep_list

    self.log.logging("zdpDecoder", "Debug", "buildframe_active_endpoint_response sqn: %s status: %s nwkid: %s nbEp: %s epList: %s" % (
        sqn, status, nwkid, nbEp, ep_list))
    return encapsulate_plugin_frame("8045", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_simple_descriptor_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    # Node Descriptor Response
    sqn = Payload[:2]
    status = Payload[2:4]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[4:8], 16)))[0]
    length = Payload[8:10]
    if status != "00":
        buildPayload = sqn + status + nwkid + length
    else:
        SimpleDescriptor = Payload[10:]
        ep = SimpleDescriptor[:2]
        profileId = "%04x" % struct.unpack("H", struct.pack(">H", int(SimpleDescriptor[2:6], 16)))[0]
        deviceId = "%04x" % struct.unpack("H", struct.pack(">H", int(SimpleDescriptor[6:10], 16)))[0]
        deviceVers = SimpleDescriptor[10:11]
        reserved = SimpleDescriptor[11:12]
        inputCnt = SimpleDescriptor[12:14]
        buildPayload = sqn + status + nwkid + length + ep + profileId + deviceId + deviceVers + reserved + inputCnt

        idx = 14
        for x in range(int(inputCnt, 16)):
            buildPayload += "%04x" % struct.unpack("H", struct.pack(">H", int(SimpleDescriptor[idx + (4 * x) : idx + (4 * x) + 4], 16)))[0]

        idx = 14 + (4 * int(inputCnt, 16))
        outputCnt = SimpleDescriptor[idx : idx + 2]
        buildPayload += outputCnt
        idx += 2
        for x in range(int(outputCnt, 16)):
            buildPayload += "%04x" % struct.unpack("H", struct.pack(">H", int(SimpleDescriptor[idx + (4 * x) : idx + (4 * x) + 4], 16)))[0]

    self.log.logging("zdpDecoder", "Debug", "buildframe_simple_descriptor_response - New payload %s" % (buildPayload))
    return encapsulate_plugin_frame("8043", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_bind_response_command(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    # 2d00
    # 01/8002/001e/ff/000000/8021/0000/02/2e0b/0200009900/7e/03
    sqn = Payload[:2]
    status = Payload[2:4]
    self.log.logging("zdpDecoder", "Debug", "buildframe_bind_response_command sqn: %s nwkid: %s Ep: %s Status %s" % (sqn, SrcNwkId, SrcEndPoint, status))
    buildPayload = sqn + status + "02" + SrcNwkId
    return encapsulate_plugin_frame("8030", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_nwk_address_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    NWKAddrAssocDevList = ""
    sqn = Payload[:2]
    status = Payload[2:4]
    ieee = "%016x" % struct.unpack("Q", struct.pack(">Q", int(Payload[4:20], 16)))[0]
    if status != "00":
        buildPayload = sqn + status + ieee
        return encapsulate_plugin_frame("8040", buildPayload, frame[len(frame) - 4 : len(frame) - 2])   

    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[20:24], 16)))[0]
    self.log.logging("zdpDecoder", "Debug", "buildframe_nwk_address_response sqn: %s status: %s ieee: %s nwkid: %s" %( sqn, status, ieee, nwkid))
    NumAssocDev = Payload[24:26] if len(Payload) > 24 else ""
    StartIndex = Payload[26:28] if len(Payload) > 26 else ""
    if len(Payload) > 28:
        NWKAddrAssocDevList = ""
        idx = 28
        for _ in range(int(NumAssocDev,16)):
            NWKAddrAssocDevList += "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[idx:idx + 4], 16)))[0]
            idx += 4
    buildPayload = sqn + status + ieee + nwkid + NumAssocDev + StartIndex + NWKAddrAssocDevList
    return encapsulate_plugin_frame("8040", buildPayload, frame[len(frame) - 4 : len(frame) - 2])    

def buildframe_ieee_address_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging(
        "zdpDecoder", 
        "Debug", 
        "buildframe_ieee_address_response SrcNwkId: %s Payload: %s  frame: %s len: %s" %( SrcNwkId, Payload, frame, len(Payload)))

    
    if len(Payload) != 24 and len(Payload) <= 26:
        # Expected len are:
        #  24 we have SQN, Status, Ieee, Nwkid
        #  28 or more we have SQN, Status, Ieee, Nwkid, NumAssociated Device, Start Index, associated device list

        self.log.logging(
            "zdpDecoder", 
            "Debug", 
            "buildframe_ieee_address_response Drop as unconsistent message SrcNwkId: %s Payload: %s  frame: %s len: %s" %( 
                SrcNwkId, Payload, frame, len(Payload)))
        return None
    

    sqn = Payload[:2]
    status = Payload[2:4]
    ieee = "%016x" % struct.unpack("Q", struct.pack(">Q", int(Payload[4:20], 16)))[0]
    if status != "00":
        buildPayload = sqn + status + ieee
        return encapsulate_plugin_frame("8041", buildPayload, frame[len(frame) - 4 : len(frame) - 2])    

    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[20:24], 16)))[0]
    self.log.logging(
        "zdpDecoder", 
        "Debug", 
        "buildframe_ieee_address_response sqn: %s status: %s ieee: %s nwkid: %s" %( sqn, status, ieee, nwkid))
    NWKAddrAssocDevList = ""
    NumAssocDev = Payload[24:26] if len(Payload) > 24 else ""
    StartIndex = Payload[26:28] if len(Payload) > 26 else ""
    if len(Payload) > 28:
        NWKAddrAssocDevList = ""
        idx = 28
        for _ in range(int(NumAssocDev,16)):
            NWKAddrAssocDevList += "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[idx:idx + 4], 16)))[0]
            idx += 4
    buildPayload = sqn + status + ieee + nwkid + NumAssocDev + StartIndex + NWKAddrAssocDevList
    return encapsulate_plugin_frame("8041", buildPayload, frame[len(frame) - 4 : len(frame) - 2])    
    


def buildframe_power_description_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Error", "buildframe_power_description_response NOT IMPLEMENTED YET")
    return frame


def buildframe_match_description_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Error", "buildframe_match_description_response NOT IMPLEMENTED YET")
    return frame


def buildframe_complex_description_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Error", "buildframe_match_description_response NOT IMPLEMENTED YET")
    return frame


def buildframe_user_description_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Error", "buildframe_user_description_response NOT IMPLEMENTED YET")
    return frame


def buildframe_unbind_response_command(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Error", "buildframe_unbind_response_command NOT IMPLEMENTED YET")
    return frame


def buildframe_management_nwk_discovery_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Error", "buildframe_management_nwk_discovery_response NOT IMPLEMENTED YET")
    return frame


def buildframe_management_lqi_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    if len(Payload) < 10:
        self.log.logging("zdpDecoder", "Error", "buildframe_management_lqi_response not a Mgt LQI Resp frame %s" % (Payload))
        return frame

    self.log.logging("zdpDecoder", "Debug", "buildframe_management_lqi_response")
    sqn = Payload[:2]
    status = Payload[2:4]
    
    if status != "00":
        buildPayload = sqn + status
    else:
        NeighborTableEntries = Payload[4:6]
        StartIndex = Payload[6:8]
        NeighborTableListCount = Payload[8:10]
        NeighborTableList = Payload[10:]

        buildPayload = sqn + status + NeighborTableEntries + NeighborTableListCount + StartIndex
        idx = 10
        for _ in range(int(NeighborTableListCount, 16)):
            ExtendedPanId = "%016x" % struct.unpack("Q", struct.pack(">Q", int(Payload[idx: idx + 16], 16)))[0]
            idx += 16
            Extendedaddress = "%016x" % struct.unpack("Q", struct.pack(">Q", int(Payload[idx: idx + 16], 16)))[0]
            idx += 16
            Networkaddress = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[idx: idx + 4], 16)))[0]
            idx += 4

            bitfield1 = int(Payload[idx:idx + 2],16)
            idx +=2

            bitfield2 = int(Payload[idx:idx + 2],16)
            idx += 2

            depth = Payload[idx:idx + 2]
            idx += 2
            lqi = Payload[idx:idx + 2]
            idx += 2

            # bitfield1 + bitfield2 joing in NXP stack
            devicetype = bitfield1 & 0x03
            rxonwhenidle = ( bitfield1 & 0x0C) >> 2
            relationship = ( bitfield1 & 0x70) >> 4
            permitjoining = bitfield2 & 0x03
            _bitmap = 0
            _bitmap += ( devicetype )
            _bitmap += ( permitjoining << 2)
            _bitmap += ( relationship << 4 )
            _bitmap += ( rxonwhenidle << 6 )

            buildPayload += Networkaddress + ExtendedPanId + Extendedaddress + depth + lqi + "%02x" %_bitmap
            self.log.logging("zdpDecoder", "Debug", "buildframe_management_lqi_response deviceType: %s" % devicetype)
            self.log.logging("zdpDecoder", "Debug", "buildframe_management_lqi_response rxonwhenidle: %s" % rxonwhenidle)
            self.log.logging("zdpDecoder", "Debug", "buildframe_management_lqi_response relationship: %s" % relationship)
            self.log.logging("zdpDecoder", "Debug", "buildframe_management_lqi_response permitjoining: %s" % permitjoining)
            self.log.logging("zdpDecoder", "Debug", "buildframe_management_lqi_response _bitmap: %s %s" % (_bitmap, bin(_bitmap)))
        
        
    return encapsulate_plugin_frame("804E", buildPayload, frame[len(frame) - 4 : len(frame) - 2])

def buildframe_leave_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Debug", "buildframe_leave_response")
    sqn = Payload[:2]
    ieee = "%016x" % 0x0
    if SrcNwkId in self.ListOfDevices:
        ieee = self.ListOfDevices[ SrcNwkId ]["IEEE"]
    status = Payload[2:4]
    buildPayload = sqn + ieee + status
    return encapsulate_plugin_frame("8048", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_direct_join_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    if len(Payload) < 4:
        self.log.logging("zdpDecoder", "Error", "buildframe_direct_join_response not a Direct Join Resp frame %s" % (Payload))
        return frame

    self.log.logging("zdpDecoder", "Error", "buildframe_direct_join_response NOT USED in Plugin")
    sqn = Payload[:2]
    status = Payload[2:4]
    buildPayload = sqn + status
    #return encapsulate_plugin_frame("xxxx", buildPayload, frame[len(frame) - 4 : len(frame) - 2])
    return frame


def buildframe_permit_join_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    if len(Payload) < 4:
        self.log.logging("zdpDecoder", "Error", "buildframe_permit_join_response not a Permit Join Resp frame %s" % (Payload))
        return frame

    sqn = Payload[:2]
    status = Payload[2:4]
    buildPayload = status
    return encapsulate_plugin_frame("8014", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_management_nwk_update_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Debug", "buildframe_management_nwk_update_response %s %s" %( SrcNwkId, Payload))

    sqn = Payload[:2]
    status = Payload[2:4]
    scanned_channels = "%08x" % struct.unpack(">I", struct.pack("I", int(Payload[4:12], 16)))[0] 
    TotalTransmissions = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[12:16], 16)))[0]
    MsgTransmissionFailures = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[16:20], 16)))[0]
    ScannedChannelsListCount = Payload[16:18]
    EnergyValues = Payload[18:]

    self.log.logging("zdpDecoder", "Debug", "buildframe_management_nwk_update_response %s status: %s" %( SrcNwkId, status))
    self.log.logging("zdpDecoder", "Debug", "buildframe_management_nwk_update_response %s scanned_channels: %s" %( SrcNwkId, scanned_channels))
    self.log.logging("zdpDecoder", "Debug", "buildframe_management_nwk_update_response %s TotalTransmissions: %s" %( SrcNwkId, TotalTransmissions))
    self.log.logging("zdpDecoder", "Debug", "buildframe_management_nwk_update_response %s MsgTransmissionFailures: %s" %( SrcNwkId, MsgTransmissionFailures))
    self.log.logging("zdpDecoder", "Debug", "buildframe_management_nwk_update_response %s ScannedChannelsListCount: %s" %( SrcNwkId, ScannedChannelsListCount))
    self.log.logging("zdpDecoder", "Debug", "buildframe_management_nwk_update_response %s EnergyValues: %s" %( SrcNwkId, EnergyValues))
    
    if status != "00":
        buildPayload = sqn + status
    else:
        buildPayload = sqn + status + TotalTransmissions + MsgTransmissionFailures + scanned_channels + ScannedChannelsListCount + EnergyValues + SrcNwkId

    return encapsulate_plugin_frame("804A", buildPayload, frame[len(frame) - 4 : len(frame) - 2])
