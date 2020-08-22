#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_output.py

    Description: All communications towards Zigate

"""

import Domoticz
import binascii
import struct
import json

from datetime import datetime
from time import time

from Modules.zigateConsts import MAX_LOAD_ZIGATE, ZIGATE_EP, HEARTBEAT, LEGRAND_REMOTES
from Modules.tools import retreive_cmd_payload_from_8002
from Modules.logging import loggingLegrand
from Modules.readAttributes import ReadAttributeRequest_0001, ReadAttributeRequest_fc01

from Modules.basicOutputs import raw_APS_request, send_zigatecmd_zcl_noack, write_attribute, write_attributeNoResponse

LEGRAND_CLUSTER_FC01 = {
        'Dimmer switch wo neutral':  { 'EnableLedInDark': '0001'  , 'EnableDimmer': '0000'   , 'EnableLedIfOn': '0002' },
        'Connected outlet': { 'EnableLedIfOn': '0002' },
        'Mobile outlet': { 'EnableLedIfOn': '0002' },
        'Shutter switch with neutral': { 'EnableLedShutter': '0001' },
        'Micromodule switch': { 'None': 'None' },
        'Cable outlet': { 'LegrandFilPilote': '0000' } }

def pollingLegrand( self, key ):

    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """
    return False


def callbackDeviceAwake_Legrand(self, NwkId, EndPoint, cluster):

    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part
    """

    #Domoticz.Log("callbackDeviceAwake_Legrand - Nwkid: %s, EndPoint: %s cluster: %s" \
    #        %(NwkId, EndPoint, cluster))

    return


def legrandReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):
    
    loggingLegrand( self, 'Debug',"legrandReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s" \
            %(srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload))

    # At Device Annoucement 0x00 and 0x05 are sent by device

    GlobalCommand, Sqn, ManufacturerCode, Command, Data = retreive_cmd_payload_from_8002( MsgPayload )
    loggingLegrand( self, 'Debug'," NwkId: %s/%s Cluster: %s Command: %s Data: %s" %( srcNWKID, srcEp, ClusterID, Command, Data))

    if ClusterID == '0102' and Command == '00': # No data (Cluster 0x0102)
        pass

    elif ClusterID == '0102' and Command == '01': # No data (Cluster 0x0102)
        pass

    elif ClusterID == 'fc01' and Command == '04': # Write Attribute Responsee
        
        pass


    elif ClusterID == 'fc01' and Command == '05':
        # Get _Ieee of Shutter Device
        _ieee = '%08x' %struct.unpack('q',struct.pack('>Q',int(Data[0:16],16)))[0] 

    elif ClusterID == 'fc01' and Command == '09':
        # IEEE of End Device (remote  )
        _ieee = '%08x' %struct.unpack('q',struct.pack('>Q',int(Data[0:16],16)))[0] 

        _count = Data[16:18] 
        loggingLegrand( self, 'Debug',"---> Decoding cmd 0x09 Ieee: %s Count: %s" %(_ieee, _count))
        if _count == '01':
            LegrandGroupMemberShip = 'fefe'
        elif _count == '02':
            LegrandGroupMemberShip = 'fdfe'
        sendFC01Command( self, Sqn, srcNWKID, srcEp, ClusterID, '0c', LegrandGroupMemberShip + _count)

    elif ClusterID == 'fc01' and Command == '0a': 
        LegrandGroupMemberShip = Data[0:4]
        _ieee = '%08x' %struct.unpack('q',struct.pack('>Q',int(Data[4:20],16)))[0]   # IEEE of Device
        _code = Data[20:24]
        loggingLegrand( self, 'Debug',"---> Decoding cmd: 0x0a Group: %s, Ieee: %s Code: %s" %(LegrandGroupMemberShip, _ieee, _code))
        status = '00'
        #_ieee = '%08x' %struct.unpack('q',struct.pack('>Q',int(ieee,16)))[0]
        _ieee = '4fa5820000740400' # IEEE du Dimmer
        sendFC01Command( self, Sqn, srcNWKID, srcEp, ClusterID, '10', status + _code + _ieee )


def sendFC01Command( self, sqn, nwkid, ep, ClusterID, cmd, data):

    loggingLegrand( self, 'Debug',"sendFC01Command Cmd: %s Data: %s" %(cmd, data))

    if cmd == '00':
        # Read Attribute received
        attribute = data[2:4] + data[0:2]

        if ClusterID == '0000' and attribute == 'f000':
            # Respond to Time Of Operation
            cmd = "01"
            
            status = "00"
            cluster_frame = "1c"           
            dataType = '23' #Uint32
            PluginTimeOfOperation = '%08X' %(self.HeartbeatCount * HEARTBEAT) # Time since the plugin started

            payload = cluster_frame + sqn + cmd + attribute + status + dataType + PluginTimeOfOperation[6:8] + PluginTimeOfOperation[4:6] + PluginTimeOfOperation[0:2] + PluginTimeOfOperation[2:4]
            raw_APS_request( self, nwkid, ep, ClusterID, '0104', payload, zigate_ep=ZIGATE_EP)

            loggingLegrand( self, 'Log', "loggingLegrand - Nwkid: %s/%s Cluster: %s, Command: %s Payload: %s" \
                %(nwkid,ep , ClusterID, cmd, data ))
            return

    if cmd == '0c':
            
            manufspec = '2110' # Legrand Manuf Specific : 0x1021
            status = "00"
            cluster_frame = "1d"           
            dataType = '23' #Uint32

            payload = cluster_frame + manufspec + sqn + cmd + data
            raw_APS_request( self, nwkid, ep, ClusterID, '0104', payload, zigate_ep=ZIGATE_EP)

            loggingLegrand( self, 'Log', "loggingLegrand - Nwkid: %s/%s Cluster: %s, Command: %s Payload: %s" \
                %(nwkid,ep , ClusterID, cmd, data ))

            return


def rejoin_legrand_reset( self ):  
 
    # Check if we have any Legrand devices if so send teh Reset to the Air
    for x in self.ListOfDevices:
        if ( 'Manufacturer' in self.ListOfDevices[x] and self.ListOfDevices[x]['Manufacturer'] == '1021' ):
            break
        if ( 'Manufacturer Name' in self.ListOfDevices[x] and self.ListOfDevices[x]['Manufacturer Name'] == 'Legrand' ):
            break
    else:
        # No Legrand devices found
        return

    #Send a Write Attributes no responses
    Domoticz.Status("Detected Legrand IEEE, broadcast Write Attribute 0x0000/0xf000")
    write_attributeNoResponse( self, 'ffff', ZIGATE_EP, '01', '0000', '1021', '01', 'f000', '23', '00000000')


def legrand_fc01( self, nwkid, command, OnOff):

    # EnableLedInDark -> enable to detect the device in dark 
    # EnableDimmer -> enable/disable dimmer
    # EnableLedIfOn -> enable Led with device On

    loggingLegrand( self, 'Debug', "legrand_fc01 Nwkid: %s Cmd: %s OnOff: %s " %(nwkid, command, OnOff), nwkid)

    LEGRAND_REFRESH_TIME = ( 3 * 3600) + 15

    LEGRAND_COMMAND_NAME = ( 'LegrandFilPilote', 'EnableLedInDark', 'EnableDimmer', 'EnableLedIfOn', 'EnableLedShutter')

    if nwkid not in self.ListOfDevices:
        return
    if command not in LEGRAND_COMMAND_NAME:
        Domoticz.Error("Unknown Legrand command %s" %command)
        return
    if 'Model' not in self.ListOfDevices[nwkid]:
        return
    if self.ListOfDevices[nwkid]['Model'] == {} or self.ListOfDevices[nwkid]['Model'] == '':
        return
    if self.ListOfDevices[nwkid]['Model'] not in LEGRAND_CLUSTER_FC01:
        loggingLegrand( self, 'Error', "%s is not an Legrand known model: %s" %( nwkid, self.ListOfDevices[nwkid]['Model']), nwkid)
        return
    if 'Legrand' not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]['Legrand'] = {}
    for cmd in LEGRAND_COMMAND_NAME:
        if cmd not in self.ListOfDevices[nwkid]['Legrand']:
            self.ListOfDevices[nwkid]['Legrand'][ cmd ] = 0xff

    if command == 'EnableLedInDark' and command in LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ]:
        if self.FirmwareVersion and self.FirmwareVersion.lower() <= '031c' and time() < self.ListOfDevices[nwkid]['Legrand']['EnableLedInDark'] + LEGRAND_REFRESH_TIME:
            return
        if self.FirmwareVersion and self.FirmwareVersion.lower() <= '031c':
            self.ListOfDevices[nwkid]['Legrand']['EnableLedInDark'] = int(time())
        data_type = "10" # Bool
        if OnOff == 'On': 
            Hdata = '01' # Enable Led in Dark
        elif OnOff == 'Off': 
            Hdata = '00' # Disable led in dark
        else: Hdata = '00'
        loggingLegrand( self, 'Debug', "--------> %s  Nwkid: %s  data_type: %s Hdata: %s " %( command, nwkid, data_type, Hdata), nwkid)
        
    elif command == 'EnableLedShutter' and command in LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ]:
        if self.FirmwareVersion and self.FirmwareVersion.lower() <= '031c' and time() < self.ListOfDevices[nwkid]['Legrand']['EnableLedShutter'] + LEGRAND_REFRESH_TIME:
            return
        if self.FirmwareVersion and self.FirmwareVersion.lower() <= '031c':
            self.ListOfDevices[nwkid]['Legrand']['EnableLedShutter'] = int(time())
        data_type = "10" # Bool
        if OnOff == 'On': 
            Hdata = '01' # Enable Led in Dark
        elif OnOff == 'Off': 
            Hdata = '00' # Disable led in dark
        else: Hdata = '00'
        loggingLegrand( self, 'Debug', "--------> %s  Nwkid: %s  data_type: %s Hdata: %s " %( command, nwkid, data_type, Hdata), nwkid)
        
    elif command == 'EnableDimmer' and command in LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ]:
        if self.FirmwareVersion and self.FirmwareVersion.lower() <= '031c' and time() < self.ListOfDevices[nwkid]['Legrand']['EnableDimmer'] + LEGRAND_REFRESH_TIME:
            return
        if self.FirmwareVersion and self.FirmwareVersion.lower() <= '031c':
            self.ListOfDevices[nwkid]['Legrand']['EnableDimmer'] = int(time())
        data_type = "09" #16-bit Data
        if OnOff == 'On': 
            Hdata = '0101' # Enable Dimmer
        elif OnOff == 'Off': 
            Hdata = '0100' # Disable Dimmer
        else: Hdata = '0000'
        loggingLegrand( self, 'Debug', "--------> %s  Nwkid: %s  data_type: %s Hdata: %s " %( command, nwkid, data_type, Hdata), nwkid)

    elif command == 'LegrandFilPilote' and command in LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ]:
        if self.FirmwareVersion and self.FirmwareVersion.lower() <= '031c' and time() < self.ListOfDevices[nwkid]['Legrand']['LegrandFilPilote'] + LEGRAND_REFRESH_TIME:
            return
        if self.FirmwareVersion and self.FirmwareVersion.lower() <= '031c':
            self.ListOfDevices[nwkid]['Legrand']['LegrandFilPilote'] = int(time())
        data_type = "09" #  16-bit Data
        if OnOff == 'On': 
            Hdata = '0001' # Enable 
        elif OnOff == 'Off': 
            Hdata = '0002' # Disable
        else: Hdata = '0000'
        loggingLegrand( self, 'Debug', "--------> %s  Nwkid: %s  data_type: %s Hdata: %s " %( command, nwkid, data_type, Hdata), nwkid)

    elif command == 'EnableLedIfOn' and command in LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ]:
        if self.FirmwareVersion and self.FirmwareVersion.lower() <= '031c' and time() < self.ListOfDevices[nwkid]['Legrand']['EnableLedIfOn'] + LEGRAND_REFRESH_TIME:
            return
        if self.FirmwareVersion and self.FirmwareVersion.lower() <= '031c':
            self.ListOfDevices[nwkid]['Legrand']['EnableLedIfOn'] = int(time())
        data_type = "10" # Bool
        if OnOff == 'On': 
            Hdata = '01' # Enable Led when On
        elif OnOff == 'Off': 
            Hdata = '00' # Disable led when On 
        else: Hdata = '00'
        loggingLegrand( self, 'Debug', "--------> %s  Nwkid: %s  data_type: %s Hdata: %s " %( command, nwkid, data_type, Hdata), nwkid)
    else:
        return

    Hattribute = LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ][command]
    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0xfc01

    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "fc01" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingLegrand( self, 'Debug', "legrand %s OnOff - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(command, nwkid,Hdata,cluster_id,Hattribute,data_type), nwkid=nwkid)
    write_attribute( self, nwkid, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

def legrand_fc40( self, nwkid, Mode ):
    # With the permission of @Thorgal789 who did the all reverse enginnering of this cluster

    CABLE_OUTLET_MODE = { 
            'Confort': 0x00,
            'Confort -1' : 0x01,
            'Confort -2' : 0x02,
            'Eco': 0x03,
            'Hors-gel' : 0x04,
            'Off': 0x05
            }

    if Mode not in CABLE_OUTLET_MODE:
        return
    Hattribute = '0000'
    data_type = '30' # 8bit Enum
    Hdata = CABLE_OUTLET_MODE[ Mode ]
    manuf_id = "1021" #Legrand Code
    manuf_spec = "01" # Manuf specific flag
    cluster_id = "%04x" %0xfc40

    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "fc40" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingLegrand( self, 'Debug', "legrand %s Set Fil pilote mode - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %( Mode, nwkid,Hdata,cluster_id,Hattribute,data_type), nwkid=nwkid)
    write_attribute( self, nwkid, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

def legrand_dimOnOff( self, OnOff):
    '''
    Call from Web
    '''

    loggingLegrand( self, 'Debug', "legrand_dimOnOff %s" %OnOff)
    for NWKID in self.ListOfDevices:
        if (
            'Manufacturer Name' in self.ListOfDevices[NWKID]
            and self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Legrand'
            and 'Model' in self.ListOfDevices[NWKID]
            and self.ListOfDevices[NWKID]['Model'] != {}
            and self.ListOfDevices[NWKID]['Model']
            in ('Dimmer switch wo neutral',)
        ):
            if 'Legrand' in self.ListOfDevices[NWKID]:
                self.ListOfDevices[NWKID]['Legrand']['EnableDimmer'] = 0
            legrand_fc01( self, NWKID, 'EnableDimmer', OnOff)
            if self.FirmwareVersion >= '31d':
                del self.ListOfDevices[NWKID]['Legrand']['EnableDimmer'] 
                ReadAttributeRequest_fc01(self, NWKID)
                        #else:
                        #    Domoticz.Error("legrand_ledOnOff not a matching device, skip it .... %s " %self.ListOfDevices[NWKID]['Model'])

def legrand_ledIfOnOnOff( self, OnOff):
    '''
    Call from Web 
    '''

    loggingLegrand( self, 'Debug', "legrand_ledIfOnOnOff %s" %OnOff)
    for NWKID in self.ListOfDevices:
        if (
            'Manufacturer Name' in self.ListOfDevices[NWKID]
            and self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Legrand'
            and 'Model' in self.ListOfDevices[NWKID]
            and self.ListOfDevices[NWKID]['Model'] != {}
            and self.ListOfDevices[NWKID]['Model']
            in (
                'Connected outlet',
                'Mobile outlet',
                'Dimmer switch wo neutral',
                'Shutter switch with neutral',
                'Micromodule switch',
            )
        ):
            if 'Legrand' in self.ListOfDevices[NWKID]:
                self.ListOfDevices[NWKID]['Legrand']['EnableLedIfOn'] = 0
            legrand_fc01( self, NWKID, 'EnableLedIfOn', OnOff)
            if self.FirmwareVersion >= '31d':
                del self.ListOfDevices[NWKID]['Legrand']['EnableLedIfOn'] 
                ReadAttributeRequest_fc01(self, NWKID)
                        #else:
                        #    Domoticz.Error("legrand_ledOnOff not a matching device, skip it .... %s " %self.ListOfDevices[NWKID]['Model'])

def legrand_ledShutter( self, OnOff):
    '''
    Call from Web 
    '''
    loggingLegrand( self, 'Debug', "legrand_ledShutter %s" %OnOff)

    for NWKID in self.ListOfDevices:
        if (
            'Manufacturer Name' in self.ListOfDevices[NWKID]
            and self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Legrand'
            and 'Model' in self.ListOfDevices[NWKID]
            and self.ListOfDevices[NWKID]['Model'] != {}
            and self.ListOfDevices[NWKID]['Model']
            in ('Shutter switch with neutral')
        ):
            if 'Legrand' in self.ListOfDevices[NWKID]:
                self.ListOfDevices[NWKID]['Legrand']['EnableLedShutter'] = 0
            legrand_fc01( self, NWKID, 'EnableLedShutter', OnOff)
            if self.FirmwareVersion >= '31d':
                self.ListOfDevices[NWKID]['Legrand']['EnableLedShutter']
                ReadAttributeRequest_fc01(self, NWKID)
                        #else:
                        #    Domoticz.Error("legrand_ledInDark not a matching device, skip it .... %s " %self.ListOfDevices[NWKID]['Model'])

def legrand_ledInDark( self, OnOff):
    '''
    Call from Web 
    '''

    loggingLegrand( self, 'Debug', "legrand_ledInDark %s" %OnOff)
    for NWKID in self.ListOfDevices:
        if (
            'Manufacturer Name' in self.ListOfDevices[NWKID]
            and self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Legrand'
            and 'Model' in self.ListOfDevices[NWKID]
            and self.ListOfDevices[NWKID]['Model'] != {}
            and self.ListOfDevices[NWKID]['Model']
            in (
                'Connected outlet',
                'Mobile outlet',
                'Dimmer switch wo neutral',
                'Shutter switch with neutral',
                'Micromodule switch',
            )
        ):
            if 'Legrand' in self.ListOfDevices[NWKID]:
                self.ListOfDevices[NWKID]['Legrand']['EnableLedInDark'] = 0
            legrand_fc01( self, NWKID, 'EnableLedInDark', OnOff)
            if self.FirmwareVersion >= '31d':
                del self.ListOfDevices[NWKID]['Legrand']['EnableLedInDark']
                ReadAttributeRequest_fc01(self, NWKID)
                        #else:
                        #    Domoticz.Error("legrand_ledInDark not a matching device, skip it .... %s " %self.ListOfDevices[NWKID]['Model'])

def legrandReenforcement( self, NWKID):

    if 'Health' in self.ListOfDevices[NWKID]['Health'] and  self.ListOfDevices[NWKID]['Health'] == 'Not Reachable':
        return False
        
    if 'Manufacturer Name' not in self.ListOfDevices[NWKID]:
        return False

    if self.ListOfDevices[NWKID]['Manufacturer Name'] != 'Legrand':
        return False

    if 'Legrand' not in self.ListOfDevices[NWKID]:
        self.ListOfDevices[NWKID]['Legrand'] = {}
        self.ListOfDevices[NWKID]['Legrand']['EnableDimmer'] = 0xff
        self.ListOfDevices[NWKID]['Legrand']['EnableLedIfOn'] = 0xff
        self.ListOfDevices[NWKID]['Legrand']['EnableLedShutter'] = 0xff
        self.ListOfDevices[NWKID]['Legrand']['EnableLedInDark'] = 0xff
        self.ListOfDevices[NWKID]['Legrand']['LegrandFilPilote'] = 0xff
   
    if 'Model' not in self.ListOfDevices[NWKID]:
        return False

    model = self.ListOfDevices[NWKID]['Model']
    if model not in LEGRAND_CLUSTER_FC01:
        return False

    for cmd in  LEGRAND_CLUSTER_FC01[ model ]:
        if cmd == 'None':
            continue

        if self.busy or self.ZigateComm.loadTransmit() > MAX_LOAD_ZIGATE:
            return True

        if cmd not in self.ListOfDevices[NWKID]['Legrand']:
            self.ListOfDevices[NWKID]['Legrand'][ cmd ] = 0xff

        if self.pluginconf.pluginConf[ cmd ] != self.ListOfDevices[NWKID]['Legrand'][ cmd ]:
            if self.pluginconf.pluginConf[ cmd ]:
                legrand_fc01( self, NWKID, cmd , 'On')
            else:
                legrand_fc01( self, NWKID, cmd, 'Off')

    return False

def legrand_refresh_battery_remote( self, nwkid):

    if 'Model' not in self.ListOfDevices[ nwkid ]:
        return
    if self.ListOfDevices[ nwkid ]['Model'] not in LEGRAND_REMOTES:
        return
    if ( 'BatteryUpdateTime' in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]['BatteryUpdateTime'] + 3600 > time() ):
        return
    ReadAttributeRequest_0001( self,  nwkid) 