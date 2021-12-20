
import zigpy.types as t
import binascii
import Domoticz

def build_plugin_004D_frame_content(nwk, ieee, parent_nwk):
    # No endian decoding as it will go directly to Decode004d
    nwk = "%04x" %nwk
    #ieee = str(ieee).replace(':','')
    #ieee = "%016x" %int(ieee,16)
    ieee = "%016x" %t.uint64_t.deserialize(ieee.serialize())[0]
    frame_payload = nwk + ieee + '00'
    
    plugin_frame = "01"                                  # 0:2
    plugin_frame += "004d"                               # 2:4 MsgType 0x8002
    plugin_frame += "%04x" % ((len(frame_payload)//2)+1) # 6:10 lenghts
    plugin_frame += "%02x" % 0xff                        # 10:12 CRC set to ff but would be great to  compute it
    plugin_frame += frame_payload
    plugin_frame += "%02x" %0x00
    plugin_frame += "03"
    return plugin_frame


def build_plugin_8002_frame_content(address, profile, cluster, src_ep, dst_ep, message, lqi=0x00, receiver=0x0000, src_addrmode=0x02, dst_addrmode=0x02):
      
        payload = binascii.hexlify(message).decode('utf-8')
        ProfilID = "%04x" %profile
        ClusterID = "%04x" %cluster
        SourcePoint = "%02x" %src_ep
        DestPoint = "%02x" %dst_ep
        SourceAddressMode = "%02x" %src_addrmode
        if src_addrmode in ( 0x02, 0x01 ):
            SourceAddress = "%04x" % address
        elif src_addrmode == 0x03:
            SourceAddress = "%016x" % address
        DestinationAddressMode = "%02x" %dst_addrmode   
        DestinationAddress = "%04x" %0x0000
        Payload = payload

        Domoticz.Log("==> build_plugin_8002_frame_content - SourceAddr: %s message: %s" %( SourceAddress, message))
        frame_payload = "00" + ProfilID + ClusterID + SourcePoint + DestPoint + SourceAddressMode + SourceAddress
        frame_payload += DestinationAddressMode + DestinationAddress + Payload
        
        plugin_frame = "01"                                  # 0:2
        plugin_frame += "8002"                               # 2:4 MsgType 0x8002
        plugin_frame += "%04x" % ((len(frame_payload)//2)+1) # 6:10 lenght
        plugin_frame += "%02x" % 0xff                        # 10:12 CRC set to ff but would be great to  compute it
        plugin_frame += frame_payload
        plugin_frame += "%02x" %lqi
        plugin_frame += "03"
        return plugin_frame
