# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#


import struct
from Zigbee.encoder_tools import encapsulate_plugin_frame


def zdp_decoders(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    # self.logging_8002( 'Debug', "zdp_decoders NwkId: %s Ep: %s Cluster: %s Payload: %s" %(SrcNwkId, SrcEndPoint, ClusterId , Payload))
    self.log.logging("zdpDecoder", "Debug", "===> zdp_decoders %s %s %s %s" % (SrcNwkId, SrcEndPoint, ClusterId, Payload))

    if ClusterId == "0000":
        # NWK_addr_req
        self.log.logging("zdpDecoder", "Error", "NWK_addr_req NOT IMPLEMENTED YET")
        return frame

    if ClusterId == "0001":
        # IEEE_addr_req
        self.log.logging("zdpDecoder", "Error", "IEEE_addr_req NOT IMPLEMENTED YET")
        return frame

    if ClusterId == "0002":
        # Node_Desc_req
        self.log.logging("zdpDecoder", "Error", "Node_Desc_req NOT IMPLEMENTED YET")
        return frame

    if ClusterId == "0003":
        # Power_Desc_req
        self.log.logging("zdpDecoder", "Error", "Power_Desc_req NOT IMPLEMENTED YET")
        return frame

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

    if ClusterId == "8032":
        # Mgmt_Rtg_rsp
        return buildframe_routing_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame)

    if ClusterId == "8033":
        # handle directly as raw in Modules/inputs/Decode8002
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


def buildframe_device_annoucement(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    # Device Annoucement

    sqn = Payload[:2]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[2:6], 16)))[0]
    ieee = "%016x" % struct.unpack("Q", struct.pack(">Q", int(Payload[6:22], 16)))[0]
    maccapa = Payload[22:24]

    self.log.logging("zdpDecoder", "Debug", "buildframe_device_annoucement sqn: %s nwkid: %s ieee: %s maccapa: %s" % (sqn, nwkid, ieee, maccapa))

    buildPayload = nwkid + ieee + maccapa
    return encapsulate_plugin_frame("004d", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_node_descriptor_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    # decode8002_and_process ProfileId: b7ca 0000 01/8002/003c/ff/0000008002000002b7ca020000/0300cab701408e66117f50000000500000/b1/03
    # decode8002_and_process return ZDP frame:    01/8042/0022/ff/03-00-b7ca-1166005000500000008e7f0140/b1/03

    # 01408e66117f50000000500000

    sqn = Payload[:2]
    status = Payload[2:4]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[4:8], 16)))[0]

    bitfield_16 = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[8:12], 16)))[0]
    mac_capa_8 = Payload[12:14]

    manuf_code_16 = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[14:18], 16)))[0]
    max_buf_size_8 = Payload[18:20]
    max_in_size_16 = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[20:24], 16)))[0]
    server_mask_16 = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[24:28], 16)))[0]
    max_out_size_16 = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[28:32], 16)))[0]
    descriptor_capability_field_8 = Payload[32:34]

    self.log.logging("zdpDecoder", "Debug", "buildframe_node_descriptor_response sqn: %s nwkid: %s Manuf: %s MacCapa: %s" % (sqn, nwkid, manuf_code_16, mac_capa_8))

    buildPayload = sqn + status + nwkid + manuf_code_16 + max_in_size_16 + max_out_size_16
    buildPayload += server_mask_16 + descriptor_capability_field_8 + mac_capa_8 + max_buf_size_8 + bitfield_16

    return encapsulate_plugin_frame("8042", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_active_endpoint_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    # Active End Point Response
    sqn = Payload[:2]
    status = Payload[2:4]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[4:8], 16)))[0]
    nbEp = Payload[8:10]
    ep_list = Payload[10:]

    self.log.logging("zdpDecoder", "Debug", "buildframe_active_endpoint_response sqn: %s status: %s nwkid: %s nbEp: %s epList: %s" % (sqn, status, nwkid, nbEp, ep_list))

    buildPayload = sqn + status + nwkid + nbEp + ep_list
    return encapsulate_plugin_frame("8045", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_simple_descriptor_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    # Node Descriptor Response

    if len(Payload) < 14:
        self.log.logging("zdpDecoder", "Error", "buildframe_simple_descriptor_response - Payload too short: %s from %s" % (Payload, frame))
        return
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
    self.log.logging("zdpDecoder", "Error", "buildframe_nwk_address_response NOT IMPLEMENTED YET")
    return frame


def buildframe_ieee_address_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Error", "buildframe_nwk_address_response NOT IMPLEMENTED YET")
    return frame


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
    self.log.logging("zdpDecoder", "Debug", "buildframe_management_lqi_response")
    #07/00/0f00029e96eba7565e4d4129f7c2dbfdfeff23a460120201aa9e96eba7565e4d41ec9a6ad0773cdf8ccf04120201aa
    sqn = Payload[:2]
    status = Payload[2:4]
    NeighborTableEntries = Payload[4:6]
    StartIndex = Payload[6:8]
    NeighborTableListCount = Payload[8:10]
    NeighborTableList = Payload[10:]

    buildPayload = sqn + status + NeighborTableEntries + NeighborTableListCount + StartIndex
    idx = 10
    for _ in range(int(NeighborTableListCount, 16)):
        ExtendedPanId = "%016x" % struct.unpack("Q", struct.pack(">Q", int(Payload[idx: idx+16], 16)))[0]
        idx += 16
        Extendedaddress = "%016x" % struct.unpack("Q", struct.pack(">Q", int(Payload[idx: idx+16], 16)))[0]
        idx += 16
        Networkaddress = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[idx: idx+4], 16)))[0]
        idx += 4
        bitfield1 = Payload[idx:idx+2]
        idx +=2
        bitfield2 = Payload[idx:idx+2]
        idx += 2
        depth =  Payload[idx:idx+2]
        idx += 2
        lqi = Payload[idx:idx+2]
        idx += 2
        buildPayload += Networkaddress + ExtendedPanId + Extendedaddress + depth + lqi + bitfield1

    return encapsulate_plugin_frame("804E", buildPayload, frame[len(frame) - 4 : len(frame) - 2])



def buildframe_routing_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Error", "buildframe_routing_response NOT IMPLEMENTED YET")
    return frame


def buildframe_leave_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Debug", "buildframe_leave_response")
    sqn = Payload[:2]
    status = Payload[2:4]
    buildPayload = sqn + status
    return encapsulate_plugin_frame("804E", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_direct_join_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Error", "buildframe_direct_join_response NOT USED in Plugin")
    sqn = Payload[:2]
    status = Payload[2:4]
    buildPayload = sqn + status
    #return encapsulate_plugin_frame("804E", buildPayload, frame[len(frame) - 4 : len(frame) - 2])
    return frame


def buildframe_permit_join_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Error", "buildframe_permit_join_response NOT IMPLEMENTED YET")
    sqn = Payload[:2]
    status = Payload[2:4]
    buildPayload = sqn + status
    return encapsulate_plugin_frame("8014", buildPayload, frame[len(frame) - 4 : len(frame) - 2])


def buildframe_management_nwk_update_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload, frame):
    self.log.logging("zdpDecoder", "Error", "buildframe_management_nwk_update_response NOT IMPLEMENTED YET")
    return frame
