#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_IAS.py

    Description: IAS Zone management

"""


import Domoticz

import z_output


ZONE_TYPE = { 0x0000: 'standard',
        0x000D: 'motion',
        0x0015: 'contact', 
        0x0028: 'fire',
        0x002A: 'water',
        0x002B: 'gas',
        0x002C: 'personal',
        0x002D: 'vibration',
        0x010F: 'remote_control',
        0x0115: 'key_fob',
        0x021D: 'key_pad',
        0x0225: 'standar_warning',
        0xFFFF:'invalid' }

ENROLL_RESPONSE_CODE =  0x00

ZONE_ID = 0x00

def setIASzoneControlerIEEE( self, key, Epout ):

    Domoticz.Log("setIASzoneControlerIEEE for %s allow: %s" %(key, Epout))

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0500
    attribute = "%04x" %0x0010
    data_type = "F0" # ZigBee_IeeeAddress = 0xf0
    data = str(self.ZigateIEEE)
    z_output.write_attribute( self, key, "01", Epout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)

def readConfirmEnroll( self, key, Epout ):

    cluster_id = "%04x" %0x0500
    attribute = 0x0000
    z_output.ReadAttributeReq( self, key, "01", Epout, cluster_id , attribute )


def IASZone_enroll_response_( self, nwkid, epout ):
    '''2.the CIE sends a ‘enroll’ message to the IAS Zone device'''

    Domoticz.Log("IASZone_enroll_response for %s" %nwkid)
    addr_mode = "02"
    enroll_rsp_code =   "%02x" %ENROLL_RESPONSE_CODE
    zoneid = "%02x" %ZONE_ID

    datas = addr_mode + nwkid + "01" + epout + enroll_rsp_code + zoneid
    z_output.sendZigateCmd( self, "0400", datas)
    return

def IASZone_enroll_response_zoneID( self, nwkid, epout ):
    '''4.the CIE sends again a ‘response’ message to the IAS Zone device with ZoneID'''

    Domoticz.Log("IASZone_enroll_response for %s" %nwkid)
    addr_mode = "02"
    enroll_rsp_code =   "%02x" %ENROLL_RESPONSE_CODE
    zoneid = "%02x" %ZONE_ID

    datas = addr_mode + nwkid + "01" + epout + enroll_rsp_code + zoneid
    z_output.sendZigateCmd( self, "0400", datas)
    return


def IASZone_attributes( self, nwkid, epout):

    cluster_id = "%04x" %0x0500
    attribute = [ 0x0000, 0x0001, 0x0002 ]
    z_output.ReadAttributeReq( self, key, "01", Epout, cluster_id , attribute )



