
# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz
import struct 
from Modules.tools import retreive_cmd_payload_from_8002
from Modules.zigateConsts import ADDRESS_MODE, SIZE_DATA_TYPE


def zdp_decoders( self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame):
    #self.logging_8002( 'Debug', "zdp_decoders NwkId: %s Ep: %s Cluster: %s Payload: %s" %(SrcNwkId, SrcEndPoint, ClusterId , Payload))
    Domoticz.Log("===> zdp_decoders %s %s %s %s" %(SrcNwkId, SrcEndPoint, ClusterId, Payload))
    
    if ClusterId == "0000":
        # NWK_addr_req
        return frame
    
    if  ClusterId == "0001":
        # IEEE_addr_req
        return frame
    
    if ClusterId == "0002":
        # Node_Desc_req
        return frame
    
    if ClusterId == "0003":
        # Power_Desc_req
        return frame
    
    if ClusterId == "0013":
        return buildframe_device_annoucement( self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
    
    if ClusterId == "8000":
        # NWK_addr_rsp
        return buildframe_nwk_address_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)

    if ClusterId == "8001":
        # IEEE_addr_rsp
        return buildframe_ieee_address_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)

    
    if ClusterId == "8002":
        # Node_Desc_rsp 
        return buildframe_node_descriptor_response( self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
    
    if ClusterId == "8003":
        # Power_Desc_rsp
        return buildframe_power_description_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
 
    
    if ClusterId == "8004":
        return buildframe_simple_descriptor_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
    
    if ClusterId == "8005":
        return buildframe_active_endpoint_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
    
    if ClusterId == "8006":
        # Match_Desc_rsp
        return buildframe_match_description_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)

    
    if ClusterId == "8010":
        # Complex_Desc_rsp
        return buildframe_complex_description_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)

    
    if ClusterId == "8011":
        # User_Desc_rsp
        return buildframe_user_description_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)

    
    if ClusterId == "8021":
        return buildframe_bind_response_command(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
    
    if ClusterId == "8022":
        return buildframe_unbind_response_command(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
        
    if ClusterId == "8030":
        # Mgmt_NWK_Disc_rsp
        return buildframe_management_nwk_discovery_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
        
    if ClusterId == "8031":
        # Mgmt_Lqi_rsp
        return buildframe_management_lqi_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
        
    if ClusterId == "8032":
        # Mgmt_Rtg_rsp
        return buildframe_routing_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
        
    if ClusterId == "8033":
        # handle directly as raw in Modules/inputs/Decode8002
        return frame        

    if ClusterId == "8034":
        # Mgmt_Leave_rsp
        return buildframe_leave_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
        
    if ClusterId == "8035":
        # Mgmt_Direct_Join_rsp
        return buildframe_direct_join_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
        
    if ClusterId == "8036":
        # Mgmt_Permit_Joining_rsp
        return buildframe_permit_join_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
        
    if ClusterId == "8038":
        # Mgmt_NWK_Update_notify
        return buildframe_management_nwk_update_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame)
    
    return frame
    
def buildframe_device_annoucement( self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame):
    # Device Annoucement
    #    if len(MsgData) > 22:  # Firmware 3.1b
    #        RejoinFlag = MsgData[22:24]
    #
    #    NwkId = MsgData[0:4]
    #    Ieee = MsgData[4:20]
    #    MacCapa = MsgData[20:22]
    # Reception Data indication, Source Address: 1735 Destination Address: fffd ProfilID: 0000 ClusterID: 0013 Message 
    # Payload: 81/3517/a1c786feff9ffd90/8e

    sqn = Payload[:2]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[2:6], 16)))[0]
    ieee = "%016x" %struct.unpack("Q", struct.pack(">Q", int(Payload[6:22], 16)))[0]
    maccapa = Payload[22:24]

    #self.logging_8002( 'Debug', "buildframe_device_annoucement sqn: %s nwkid: %s ieee: %s maccapa: %s" %(sqn,nwkid , ieee , maccapa ))

    buildPayload = nwkid + ieee + maccapa

    newFrame = "01"  # 0:2
    newFrame += "004d"  # 2:6   MsgType
    newFrame += "%04x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame

def buildframe_node_descriptor_response( self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame):
    # sequence = MsgData[0:2]
    # status = MsgData[2:4]
    # addr = MsgData[4:8]
    # manufacturer = MsgData[8:12]
    # max_rx = MsgData[12:16]
    # max_tx = MsgData[16:20]
    # # server_mask = MsgData[20:24]
    # # descriptor_capability = MsgData[24:26]
    # mac_capability = MsgData[26:28]
    # max_buffer = MsgData[28:30]
    # bit_field = MsgData[30:34]

    #  2c 00 3517   0140/8e/7c11/52/5200/002c/5200/00

    sqn = Payload[:2]
    status = Payload[2:4]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[4:8], 16)))[0]
    bitfield_16 = Payload[8:12]
    mac_capa_8 = Payload[12:14]
    manuf_code_16 = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[14:18], 16)))[0]
    max_buf_size_8 = Payload[18:20]
    max_in_size_16 = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[20:24], 16)))[0]
    server_mask_16 = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[24:28], 16)))[0]
    max_out_size_16 = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[28:32], 16)))[0]
    descriptor_capability_field_8 = Payload[32:34]

    #self.logging_8002( 'Debug', "buildframe_node_descriptor_response sqn: %s nwkid: %s Manuf: %s MacCapa: %s" %(sqn,nwkid , manuf_code_16 , mac_capa_8 ))

    buildPayload = sqn + status + nwkid + manuf_code_16 + max_in_size_16 + max_out_size_16
    buildPayload += server_mask_16 + descriptor_capability_field_8 + mac_capa_8 + max_buf_size_8 + bitfield_16

    newFrame = "01"  # 0:2
    newFrame += "8042"  # 2:6   MsgType
    newFrame += "%04x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame
    
def buildframe_active_endpoint_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame):
    # Active End Point Response
    #    MsgDataSQN = MsgData[0:2]
    #    MsgDataStatus = MsgData[2:4]
    #    MsgDataShAddr = MsgData[4:8]
    #    MsgDataEpCount = MsgData[8:10]
    #
    #    MsgDataEPlist = MsgData[10 : len(MsgData)]

    # Reception Data indication, Source Address: 1735 Destination Address: 0000 ProfilID: 0000 ClusterID: 8005 Message 
    # Payload: 0000/3517/02/01f2
    sqn = Payload[:2]
    status = Payload[2:4]
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[4:8], 16)))[0]
    nbEp = Payload[8:10]
    ep_list = Payload[10:]

    #self.logging_8002( 'Debug', "buildframe_active_endpoint_response sqn: %s status: %s nwkid: %s nbEp: %s epList: %s" %(
    #    sqn, status, nwkid , nbEp , ep_list ))

    buildPayload = sqn + status + nwkid + nbEp + ep_list
    newFrame = "01"  # 0:2
    newFrame += "8045"  # 2:6   MsgType
    newFrame += "%04x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame

def buildframe_simple_descriptor_response(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame):
    # Node Descriptor Response
    #    MsgDataSQN = MsgData[0:2]
    #    MsgDataStatus = MsgData[2:4]
    #    MsgDataShAddr = MsgData[4:8]
    #    MsgDataLenght = MsgData[8:10]
    #
    #    if int(MsgDataLenght, 16) == 0:
    #        return
    #
    #    MsgDataEp = MsgData[10:12]
    #    MsgDataProfile = MsgData[12:16]
    #    MsgDataDeviceId = MsgData[16:20]
    #    MsgDataBField = MsgData[20:22]
    #    MsgDataInClusterCount = MsgData[22:24]

    if len(Payload) < 14:
        Domoticz.Error("buildframe_simple_descriptor_response - Payload too short: %s from %s" %(Payload,frame))
        return
    sqn = Payload[:2]
    Domoticz.Log("==> buildframe_simple_descriptor_response sqn: %s" %sqn)
    status = Payload[2:4]
    Domoticz.Log("==> buildframe_simple_descriptor_response status: %s" %status)
    nwkid = "%04x" % struct.unpack("H", struct.pack(">H", int(Payload[4:8], 16)))[0]
    Domoticz.Log("==> buildframe_simple_descriptor_response nwkid: %s" %nwkid)
    length = Payload[8:10]
    Domoticz.Log("==> buildframe_simple_descriptor_response length: %s" %length)
    if status != '00':
        buildPayload = sqn + status + nwkid + length
    else:
        SimpleDescriptor = Payload[10:]
        Domoticz.Log("==> buildframe_simple_descriptor_response SimpleDescriptor: %s" %SimpleDescriptor)
        ep = SimpleDescriptor[:2]
        Domoticz.Log("==> buildframe_simple_descriptor_response ep: %s" %ep)
        profileId = "%04x" % struct.unpack("H", struct.pack(">H", int(SimpleDescriptor[2:6], 16)))[0]
        Domoticz.Log("==> buildframe_simple_descriptor_response profileId: %s" %profileId)
        deviceId = "%04x" % struct.unpack("H", struct.pack(">H", int(SimpleDescriptor[6:10], 16)))[0]
        Domoticz.Log("==> buildframe_simple_descriptor_response deviceId: %s" %deviceId)
        deviceVers = SimpleDescriptor[10:11]
        reserved = SimpleDescriptor[11:12]
        inputCnt = SimpleDescriptor[12:14]

        #self.logging_8002( 'Debug', "buildframe_simple_descriptor_response sqn: %s status: %s nwkid: %s " %(
        #    sqn, status, nwkid ))

        buildPayload = sqn + status + nwkid + length + ep + profileId + deviceId + deviceVers + reserved + inputCnt

        idx = 14
        for x in range(int(inputCnt,16)):
            buildPayload += "%04x" % struct.unpack("H", struct.pack(">H", int(SimpleDescriptor[idx + (4 * x):idx + (4 * x) + 4], 16)))[0]

        idx = 14 + ( 4 * int(inputCnt,16) )
        outputCnt = SimpleDescriptor[idx:idx + 2]
        idx += 2
        for x in range(int(outputCnt,16)):
            buildPayload += "%04x" % struct.unpack("H", struct.pack(">H", int(SimpleDescriptor[idx+(4*x):idx+(4*x)+4], 16)))[0]

    newFrame = "01"  # 0:2
    newFrame += "8043"  # 2:6   MsgType
    newFrame += "%04x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame   

def buildframe_bind_response_command(self, SrcNwkId, SrcEndPoint, ClusterId, Payload , frame):
    # 2d00
    sqn = Payload[:2]
    status = Payload[2:4]

    #self.logging_8002( 'Debug', "buildframe_bind_response_command sqn: %s nwkid: %s Ep: %s Status %s" %(sqn, SrcNwkId , SrcEndPoint, status ))

    buildPayload = sqn + status

    newFrame = "01"  # 0:2
    newFrame += "8030"  # 2:6   MsgType
    newFrame += "%04x" % len(buildPayload)  # 6:10  Length
    newFrame += "ff"  # 10:12 CRC
    newFrame += buildPayload
    newFrame += frame[len(frame) - 4 : len(frame) - 2]  # LQI
    newFrame += "03"
    return newFrame
