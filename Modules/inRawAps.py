#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import Domoticz
import struct

from Modules.tools import retreive_cmd_payload_from_8002
from Modules.pollControl import receive_poll_cluster

from Modules.domoMaj import MajDomoDevice

from Modules.schneider_wiser import schneiderReadRawAPS
from Modules.legrand_netatmo import legrandReadRawAPS
from Modules.livolo import livoloReadRawAPS
from Modules.orvibo import orviboReadRawAPS
from Modules.lumi import lumiReadRawAPS
from Modules.philips import philipsReadRawAPS
from Modules.tuya import tuyaReadRawAPS

from Modules.casaia import CASAIA_MANUF_CODE, casaiaReadRawAPS


## Requires Zigate firmware > 3.1d

def inRawAps( self, Devices, srcnwkid, srcep, cluster, dstnwkid, dstep, Sqn, ManufacturerCode, Command, Data, payload):

    """
    This function is called by Decode8002
    """

    CALLBACK_TABLE = {
        # Manuf : ( callbackDeviceAwake_xxxxx function )
        '105e' : schneiderReadRawAPS ,
        '1021' : legrandReadRawAPS ,
        '115f' : lumiReadRawAPS,
        '100b' : philipsReadRawAPS,
        '1002' : tuyaReadRawAPS,
        CASAIA_MANUF_CODE: casaiaReadRawAPS,
        }

    CALLBACK_TABLE2 = {
        # Manufacturer Name
        'LIVOLO': livoloReadRawAPS,
        '欧瑞博': orviboReadRawAPS,
        'Legrand': legrandReadRawAPS,
        'Schneider': schneiderReadRawAPS,
        'LUMI': lumiReadRawAPS,
        'Philips' : philipsReadRawAPS,
        '_TZE200_ckud7u2l' : tuyaReadRawAPS ,
        'OWON': casaiaReadRawAPS,
    }

    if srcnwkid not in self.ListOfDevices:
        return

    if cluster == '0020': # Poll Control ( Not implemented in firmware )
        #Domoticz.Log("Cluster 0020 -- POLL CLUSTER")
        receive_poll_cluster( self, srcnwkid, srcep, cluster, dstnwkid, dstep, Sqn, ManufacturerCode, Command, Data )
        return

    if cluster == '0019': # OTA Cluster
        #Domoticz.Log("Cluster 0019 -- OTA CLUSTER")

        if Command == '01': 
            # Query Next Image Request
            Domoticz.Log("Cluster 0019 -- OTA CLUSTER Command 01")
            #fieldcontrol = Data[0:2]
            manufcode = '%04x' %struct.unpack('H',struct.pack('>H',int(Data[2:6],16)))[0] 
            imagetype = '%04x' %struct.unpack('H',struct.pack('>H',int(Data[6:10],16)))[0] 
            currentVersion = '%08x' %struct.unpack('I',struct.pack('>I',int(Data[10:18],16)))[0]
    
            Domoticz.Log("Cluster 0019 -- OTA CLUSTER Command 01Device %s Request OTA with current ManufCode: %s ImageType: %s Version: %s"
                %(srcnwkid ,manufcode, imagetype, currentVersion  ))

            if 'OTA' not in self.ListOfDevices[ srcnwkid ]:
                self.ListOfDevices[ srcnwkid ]['OTA'] = {}
            self.ListOfDevices[ srcnwkid ]['OTA']['ManufacturerCode'] = manufcode
            self.ListOfDevices[ srcnwkid ]['OTA']['ImageType'] = imagetype
            self.ListOfDevices[ srcnwkid ]['OTA']['CurrentImageVersion'] = currentVersion

            return

    if cluster == '0501': # IAS ACE
        # "00"
        # "01" Arm Day (Home Zones Only) - Command Arm 0x00 - Payload 0x01
        # "02" Emergency - Command Emergency 0x02
        # "03" Arm All Zones - Command Arm 0x00 - Payload Arm all Zone 0x03
        # "04" Disarm - Command 0x00 - Payload Disarm 0x00

        if Command == '00' and Data[0:2] == '00':
            # Disarm 
            MajDomoDevice( self, Devices, srcnwkid, srcep, "0006", '04')

        elif Command == '00' and Data[0:2] == '01':
            # Command Arm Day (Home Zones Only) 
            MajDomoDevice( self, Devices, srcnwkid, srcep, "0006", '01')


        elif Command == '00' and Data[0:2] == '03':
            # Arm All Zones
            MajDomoDevice( self, Devices, srcnwkid, srcep, "0006", '03')

        elif Command == '02':
            # Emergency
            MajDomoDevice( self, Devices, srcnwkid, srcep, "0006", '02')

        return

    if 'Manufacturer' not in self.ListOfDevices[srcnwkid]:
        return
    
    manuf = manuf_name = ''

    if 'Manufacturer Name' in self.ListOfDevices[srcnwkid]:
        manuf_name = self.ListOfDevices[srcnwkid][ 'Manufacturer Name']

    manuf = self.ListOfDevices[srcnwkid]['Manufacturer']

    if manuf in CALLBACK_TABLE:
        #Domoticz.Log("Found in CALLBACK_TABLE")
        func = CALLBACK_TABLE[ manuf ]
        func( self, Devices, srcnwkid, srcep, cluster, dstnwkid, dstep, payload)

    elif manuf_name in CALLBACK_TABLE2:
        #Domoticz.Log("Found in CALLBACK_TABLE2")
        func = CALLBACK_TABLE2[manuf_name]
        func( self, Devices, srcnwkid, srcep, cluster, dstnwkid, dstep, payload)

    else:
        Domoticz.Log("inRawAps %s/%s Cluster %s Manuf: %s Command: %s Data: %s Payload: %s"
            %(srcnwkid, srcep, cluster,  ManufacturerCode, Command, Data, payload))
