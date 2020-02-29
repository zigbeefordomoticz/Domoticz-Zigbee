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

from Modules.tools import loggingOutput
from Modules.output import raw_APS_request, write_attribute


def legrand_fake_read_attribute_response( self, nwkid ):

    cluster_frame = '11'
    sqn = '00'
    payload = cluster_frame + sqn + '0100F0002311000000'
    raw_APS_request( self, nwkid, '01', '0000', '0104', payload)


def rejoin_legrand( self, nwkid):

    if nwkid not in self.ListOfDevices:
        return

    manuf_id = '1021'
    manuf_spec = "01"
    cluster_id = '0000'
    Hattribute = 'f000'
    data_type = '23'
    Hdata = '00000000'

    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "fc01" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingOutput( self, 'Debug', "Write Attributes No Response ")

    # Overwrite nwkid with 'ffff' in order to make a broadcast
    write_attribute( self, 'ffff', "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

    # To be use if the Write Attribute is not conclusive
    cluster_frame = '14'
    sqn = '00'
    payload = cluster_frame + sqn + '0500f02300000000'
    raw_APS_request( self, 'ffff', '01', '0000', '0104', payload)


def legrand_fc01( self, nwkid, command, OnOff):

            # EnableLedInDark -> enable to detect the device in dark 
            # EnableDimmer -> enable/disable dimmer
            # EnableLedIfOn -> enable Led with device On

    LEGRAND_REFRESH_TIME = ( 3 * 3600) + 15
    LEGRAND_CLUSTER_FC01 = {
            'Dimmer switch w/o neutral':  { 'EnableLedInDark': '0001'  , 'EnableDimmer': '0000'   , 'EnableLedIfOn': '0002' },
            'Connected outlet': { 'EnableLedIfOn': '0002' },
            'Mobile outlet': { 'EnableLedIfOn': '0002' },
            'Shutter switch with neutral': { 'EnableLedIfOn': '0001' },
            'Micromodule switch': { 'None': 'None' },
            'Cable outlet': { 'FilPilote': '0000' } }

    if nwkid not in self.ListOfDevices:
        return

    if command not in ( 'FilPilote', 'EnableLedInDark', 'EnableDimmer', 'EnableLedIfOn'):
        Domoticz.Error("Unknown Legrand command %s" %command)
        return

    if 'Model' not in self.ListOfDevices[nwkid]:
        return

    if self.ListOfDevices[nwkid]['Model'] == {} or self.ListOfDevices[nwkid]['Model'] == '':
        return

    if self.ListOfDevices[nwkid]['Model'] not in LEGRAND_CLUSTER_FC01:
        loggingOutput( self, 'Error', "%s is not an Legrand known model: %s" %( nwkid, self.ListOfDevices[nwkid]['Model']), nwkid)
        return

    if 'Legrand' not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]['Legrand'] = {}
        self.ListOfDevices[nwkid]['Legrand']['FilPilote'] = 0
        self.ListOfDevices[nwkid]['Legrand']['EnableLedInDark'] = 0
        self.ListOfDevices[nwkid]['Legrand']['EnableDimmer'] = 0
        self.ListOfDevices[nwkid]['Legrand']['EnableLedIfOn'] = 0

    if command == 'EnableLedInDark' and command in LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ]:
        if time() < self.ListOfDevices[nwkid]['Legrand']['EnableLedInDark'] + LEGRAND_REFRESH_TIME:
            return
            
        self.ListOfDevices[nwkid]['Legrand']['EnableLedInDark'] = int(time())

        data_type = "10" # Bool
        if OnOff == 'On': Hdata = '01' # Enable Led in Dark
        elif OnOff == 'Off': Hdata = '00' # Disable led in dark
        else: Hdata = '00'
        
    elif command == 'EnableDimmer' and command in LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ]:
        if time() < self.ListOfDevices[nwkid]['Legrand']['EnableDimmer'] + LEGRAND_REFRESH_TIME:
            return

        self.ListOfDevices[nwkid]['Legrand']['EnableDimmer'] = int(time())
        data_type = "09" #  16-bit Data
        if OnOff == 'On': Hdata = '0101' # Enable Dimmer
        elif OnOff == 'Off': Hdata = '0100' # Disable Dimmer
        else: Hdata = '0000'

    elif command == 'FilPilote' and command in LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ]:
        if time() < self.ListOfDevices[nwkid]['Legrand']['FilPilote'] + LEGRAND_REFRESH_TIME:
            return

        self.ListOfDevices[nwkid]['Legrand']['FilPilote'] = int(time())
        data_type = "09" #  16-bit Data
        if OnOff == 'On': Hdata = '0001' # Enable 
        elif OnOff == 'Off': Hdata = '0002' # Disable
        else: Hdata = '0000'

    elif command == 'EnableLedIfOn' and command in LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ]:
        if time() < self.ListOfDevices[nwkid]['Legrand']['EnableLedIfOn'] + LEGRAND_REFRESH_TIME:
            return

        self.ListOfDevices[nwkid]['Legrand']['EnableLedIfOn'] = int(time())
        data_type = "10" # Bool
        if OnOff == 'On': Hdata = '01' # Enable Led when On
        elif OnOff == 'Off': Hdata = '00' # Disable led when On 
        else: Hdata = '00'
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

    loggingOutput( self, 'Debug', "legrand %s OnOff - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(command, nwkid,Hdata,cluster_id,Hattribute,data_type), nwkid=nwkid)
    write_attribute( self, nwkid, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)


def legrand_fc40( self, Mode ):
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

    loggingOutput( self, 'Debug', "legrand %s Set Fil pilote mode - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(command, nwkid,Hdata,cluster_id,Hattribute,data_type), nwkid=nwkid)
    write_attribute( self, nwkid, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)



def legrand_dimOnOff( self, OnOff):
    '''
    Call from Web
    '''

    for NWKID in self.ListOfDevices:
        if 'Manufacturer Name' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Legrand':
                if 'Model' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Model'] != {}:
                        if self.ListOfDevices[NWKID]['Model'] in ( 'Dimmer switch w/o neutral', ):
                            legrand_fc01( self, NWKID, 'EnableDimmer', OnOff)
                        #else:
                        #    Domoticz.Error("legrand_ledOnOff not a matching device, skip it .... %s " %self.ListOfDevices[NWKID]['Model'])

def legrand_ledIfOnOnOff( self, OnOff):
    '''
    Call from Web 
    '''

    for NWKID in self.ListOfDevices:
        if 'Manufacturer Name' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Legrand':
                if 'Model' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Model'] != {}:
                        if self.ListOfDevices[NWKID]['Model'] in ( 'Connected outlet', 'Mobile outlet', 'Dimmer switch w/o neutral', 'Shutter switch with neutral', 'Micromodule switch' ):
                            legrand_fc01( self, NWKID, 'EnableLedIfOn', OnOff)
                        #else:
                        #    Domoticz.Error("legrand_ledOnOff not a matching device, skip it .... %s " %self.ListOfDevices[NWKID]['Model'])

def legrand_ledInDark( self, OnOff):
    '''
    Call from Web 
    '''

    for NWKID in self.ListOfDevices:
        if 'Manufacturer Name' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Legrand':
                if 'Model' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Model'] != {}:
                        if self.ListOfDevices[NWKID]['Model'] in ( 'Connected outlet', 'Mobile outlet', 'Dimmer switch w/o neutral', 'Shutter switch with neutral', 'Micromodule switch' ):
                            legrand_fc01( self, NWKID, 'EnableLedInDark', OnOff)
                        #else:
                        #    Domoticz.Error("legrand_ledInDark not a matching device, skip it .... %s " %self.ListOfDevices[NWKID]['Model'])


