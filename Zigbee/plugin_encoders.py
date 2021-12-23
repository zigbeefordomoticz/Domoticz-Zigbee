
import binascii

import zigpy.types as t

#import Domoticz
from Zigbee.encoder_tools import encapsulate_plugin_frame


def build_plugin_004D_frame_content(self, nwk, ieee, parent_nwk):
    # No endian decoding as it will go directly to Decode004d
    self.log.logging("TransportPluginEncoder", "Debug", "build_plugin_004D_frame_content %s %s %s" %(nwk, ieee, parent_nwk))
    
    nwk = "%04x" %nwk
    #ieee = str(ieee).replace(':','')
    #ieee = "%016x" %int(ieee,16)
    ieee = "%016x" %t.uint64_t.deserialize(ieee.serialize())[0]
    frame_payload = nwk + ieee + '00'
    
    return encapsulate_plugin_frame( "004d", frame_payload, "%02x" %0x00)

def build_plugin_8015_frame_content(self, ):
    # Get list of active devices
    pass
    
def build_plugin_8009_frame_content(self, ):
    # Get Network State
    pass
    
def build_plugin_8011_frame_content(self, nwkid, status, lqi):
    #MsgLen = len(MsgData)
    #MsgStatus = MsgData[0:2]
    #MsgSrcAddr = MsgData[2:6]
    #MsgSEQ = MsgData[12:14] if MsgLen > 12 else None
    lqi = lqi or 0x00
    frame_payload =  "06" + "%02x" %status + nwkid
    return encapsulate_plugin_frame( "8011", frame_payload, "%02x" %lqi)
    
def build_plugin_8002_frame_content(self, address, profile, cluster, src_ep, dst_ep, message, lqi=0x00, receiver=0x0000, src_addrmode=0x02, dst_addrmode=0x02):
    self.log.logging("TransportPluginEncoder", "Debug", "build_plugin_8002_frame_content %s %s %s %s %s %s %s %s %s %s" %(
        address, profile, cluster, src_ep, dst_ep, message, lqi, receiver, src_addrmode, dst_addrmode))
    
    payload = binascii.hexlify(message).decode('utf-8')
    ProfilID = "%04x" %profile
    ClusterID = "%04x" %cluster
    SourcePoint = "%02x" %src_ep
    DestPoint = "%02x" %dst_ep
    SourceAddressMode = "%02x" %src_addrmode
    if src_addrmode in ( 0x02, 0x01 ):
        SourceAddress = address
    elif src_addrmode == 0x03:
        SourceAddress = "%016x" % address
    DestinationAddressMode = "%02x" %dst_addrmode   
    DestinationAddress = "%04x" %0x0000
    Payload = payload

    self.log.logging("TransportPluginEncoder", "Debug", "==> build_plugin_8002_frame_content - SourceAddr: %s message: %s" %( SourceAddress, message))
    frame_payload = "00" + ProfilID + ClusterID + SourcePoint + DestPoint + SourceAddressMode + SourceAddress
    frame_payload += DestinationAddressMode + DestinationAddress + Payload
        
    return encapsulate_plugin_frame( "8002", frame_payload, "%02x" %lqi)
