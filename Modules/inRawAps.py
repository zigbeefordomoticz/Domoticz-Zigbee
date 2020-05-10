#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import Domoticz

from Modules.schneider_wiser import schneiderReadRawAPS
from Modules.legrand_netatmo import legrandReadRawAPS
from Modules.orvibo import orviboReadRawAPS
from Modules.lumi import lumiReadRawAPS
from Modules.philips import philipsReadRawAPS

## Requires Zigate firmware > 3.1d

def inRawAps( self, Devices, srcnwkid, srcep, cluster, dstnwkid, dstep, payload):

    """
    This function is called by Decode8002
    """

    CALLBACK_TABLE = {
        # Manuf : ( callbackDeviceAwake_xxxxx function )
        '105e' : schneiderReadRawAPS ,
        '1021' : legrandReadRawAPS ,
        '115f' : lumiReadRawAPS,
        '100b' : philipsReadRawAPS,
        }

    CALLBACK_TABLE2 = {
        # Manufacturer Name
        '欧瑞博': orviboReadRawAPS,
        'Legrand': legrandReadRawAPS,
        'Schneider': schneiderReadRawAPS,
        'LUMI': lumiReadRawAPS,
        'Philips' : philipsReadRawAPS,
    }

    #Domoticz.Log("inRawAps - NwkId: %s Ep: %s, Cluster: %s, dstNwkId: %s, dstEp: %s, Payload: %s" \
    #        %(srcnwkid, srcep, cluster, dstnwkid, dstep, payload))

    if srcnwkid not in self.ListOfDevices:
        return
    if 'Manufacturer' not in self.ListOfDevices[srcnwkid]:
        return
    
    manuf = manuf_name = ''

    if 'Manufacturer Name' in self.ListOfDevices[srcnwkid]:
        manuf_name = self.ListOfDevices[srcnwkid][ 'Manufacturer Name']

    manuf = self.ListOfDevices[srcnwkid]['Manufacturer']
    #Domoticz.Log("  - Manuf: %s" %manuf)
    #Domoticz.Log("  - Manuf: %s" %manuf_name)

    if manuf in CALLBACK_TABLE:
        #Domoticz.Log("Found in CALLBACK_TABLE")
        func = CALLBACK_TABLE[ manuf ]
        func( self, Devices, srcnwkid, srcep, cluster, dstnwkid, dstep, payload)
    elif manuf_name in CALLBACK_TABLE2:
        #Domoticz.Log("Found in CALLBACK_TABLE2")
        func = CALLBACK_TABLE2[manuf_name]
        func( self, Devices, srcnwkid, srcep, cluster, dstnwkid, dstep, payload)

    return
