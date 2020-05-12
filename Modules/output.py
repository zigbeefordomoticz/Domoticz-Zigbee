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

from Modules.zigateConsts import ZLL_DEVICES, MAX_LOAD_ZIGATE, CLUSTERS_LIST, MAX_READATTRIBUTES_REQ, LEGRAND_REMOTES, ADDRESS_MODE, CFG_RPT_ATTRIBUTESbyCLUSTERS, SIZE_DATA_TYPE, ZIGATE_EP
from Modules.tools import getClusterListforEP, mainPoweredDevice
from Modules.logging import loggingOutput
from Modules.schneider_wiser import schneider_setpoint
from Modules.basicOutputs import write_attribute

def write_attribute_when_awake( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data):

    if 'WriteAttribute' not in self.ListOfDevices[key]:
        self.ListOfDevices[key]['WriteAttribute'] = {} 
    if  EPout not in self.ListOfDevices[key]['WriteAttribute']:
        self.ListOfDevices[key]['WriteAttribute'][EPout] = {} 
    if  clusterID not in self.ListOfDevices[key]['WriteAttribute'][EPout]:
        self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID] = {} 
    if  attribute not in self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID]:
        self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute] = {} 
    
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['Phase'] = 'waiting'
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['Stamp'] = int(time())
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['Status'] = ''
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['DataType'] = data_type
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['EPin'] = EPin
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['EPout'] = EPout
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['manuf_id'] = manuf_id
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['manuf_spec'] = manuf_spec
    self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['data'] = data

    loggingOutput( self, 'Debug', "write_attribute_when_awake for %s/%s - >%s<" %(key, EPout, data), key)

def callBackForWriteAttributeIfNeeded(self, key):

    if 'WriteAttribute' in self.ListOfDevices[key]:
        for EPout in list (self.ListOfDevices[key]['WriteAttribute']):
            for clusterID in list (self.ListOfDevices[key]['WriteAttribute'][EPout]):
                for attribute in list (self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID]):
                    if self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['Phase'] =='waiting':
                        loggingOutput( self, 'Debug', "device awake let's write attribute for %s/%s" %(key, EPout), key)
                        self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['Phase'] = 'requested'
                        self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['Stamp'] = int(time())
                        data_type = self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['DataType'] 
                        EPin = self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['EPin']
                        EPout = self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['EPout']
                        manuf_id = self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['manuf_id']
                        manuf_spec = self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['manuf_spec']
                        data = self.ListOfDevices[key]['WriteAttribute'][EPout][clusterID][attribute]['data']
                        write_attribute (self,key,EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data)

def setPIRoccupancyTiming( self, key ):

    manuf_spec = "00"
    manuf_id = "0000"

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0406" in self.ListOfDevices[key]['Ep'][tmpEp]: 
            EPout=tmpEp
            cluster_id = "0406"

            for attribute, dataint in ( ( '0010', 5), ('0011', 10) ):
                data_type = "21" # uint16
                data = '%04x' %dataint

                loggingOutput( self, 'Debug', "setPIRoccupancyTiming for %s/%s - Attribute %s: %s" %(key, EPout, attribute, data), key)
                write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)

            ReadAttributeRequest_0406(self, key)

def setPowerOn_OnOff( self, key, OnOffMode=0xff):

    # OSRAM/LEDVANCE
    # 0xfc0f --> Command 0x01
    # 0xfc01 --> Command 0x01

    # Tested on Ikea Bulb without any results !
    POWERON_MODE = ( 0x00, # Off
            0x01, # On
            0xfe # Previous state
            )

    if 'Manufacturer' in self.ListOfDevices[key]:
        manuf_spec = "01"
        manuf_id = self.ListOfDevices[key]['Manufacturer']
    else:
        manuf_spec = "00"
        manuf_id = "0000"

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0006" in self.ListOfDevices[key]['Ep'][tmpEp]: 
            EPout=tmpEp
            cluster_id = "0006"
            attribute = "4003"
            data_type = "30" # 
            data = "ff"
            if OnOffMode in POWERON_MODE:
                data = "%02x" %OnOffMode
            else:
                data = "%02x" %0xff
            loggingOutput( self, 'Debug', "set_PowerOn_OnOff for %s/%s - OnOff: %s" %(key, EPout, OnOffMode), key)
            write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
            ReadAttributeRequest_0006_400x( self, key)

        #if '0008' in self.ListOfDevices[key]['Ep'][tmpEp]:
        #    EPout=tmpEp
        #    cluster_id = "0008"
        #    attribute = "4000"
        #    data_type = "20" # 
        #    data = "ff"
        #    if OnOffMode in POWERON_MODE:
        #        data = "%02x" %OnOffMode
        #    else:
        #        data = "%02x" %0xff
        #        data = "%02x" %0xff
        #    loggingOutput( self, 'Log', "set_PowerOn_OnOff for %s/%s - OnOff: %s" %(key, EPout, OnOffMode), key)
        #    retreive_ListOfAttributesByCluster( self, key, EPout, '0008')

        #if '0300' in self.ListOfDevices[key]['Ep'][tmpEp]:
        #    EPout=tmpEp
        #    cluster_id = "0300"
        #    attribute = "4010"
        #    data_type = "21" # 
        ##    data = "ffff"
        #    if OnOffMode in POWERON_MODE:
        #        data = "%04x" %OnOffMode
        #    else:
        #        data = "%04x" %0xffff
        #        data = "%02x" %0xff
        #    loggingOutput( self, 'Log', "set_PowerOn_OnOff for %s/%s - OnOff: %s" %(key, EPout, OnOffMode), key)
        #    retreive_ListOfAttributesByCluster( self, key, EPout, '0300')
   
def thermostat_Setpoint_SPZB(  self, key, setpoint):

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0x4003
    data_type = "29" # Int16
    loggingOutput( self, 'Debug', "setpoint: %s" %setpoint, nwkid=key)
    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    loggingOutput( self, 'Debug', "setpoint: %s" %setpoint, nwkid=key)
    Hdata = "%04x" %setpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingOutput( self, 'Debug', "thermostat_Setpoint_SPZB - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,Hdata,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

def thermostat_Setpoint( self, key, setpoint):

    loggingOutput( self, 'Debug', "thermostat_Setpoint - for %s with value %s" %(key,setpoint), nwkid=key)

    if 'Model' in self.ListOfDevices[key]:
        if self.ListOfDevices[key]['Model'] != {}:
            if self.ListOfDevices[key]['Model'] == 'SPZB0001':
                loggingOutput( self, 'Debug', "thermostat_Setpoint - calling SPZB for %s with value %s" %(key,setpoint), nwkid=key)
                thermostat_Setpoint_SPZB( self, key, setpoint)

            elif self.ListOfDevices[key]['Model'] in ( 'EH-ZB-RTS', 'EH-ZB-HACT', 'EH-ZB-VACT' ):
                loggingOutput( self, 'Debug', "thermostat_Setpoint - calling Schneider for %s with value %s" %(key,setpoint), nwkid=key)
                schneider_setpoint(self, key, setpoint)
                return

    loggingOutput( self, 'Debug', "thermostat_Setpoint - standard for %s with value %s" %(key,setpoint), nwkid=key)
    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0x0012
    data_type = "29" # Int16
    loggingOutput( self, 'Debug', "setpoint: %s" %setpoint, nwkid=key)
    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    loggingOutput( self, 'Debug', "setpoint: %s" %setpoint, nwkid=key)
    Hdata = "%04x" %setpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingOutput( self, 'Debug', "thermostat_Setpoint - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,Hdata,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

    ReadAttributeRequest_0201(self, key)

def thermostat_eurotronic_hostflag( self, key, action):

    HOSTFLAG_ACTION = {
            'turn_display':0x000002,
            'boost':       0x000004,
            'clear_off':   0x000010,
            'set_off_mode':0x000020,
            'child_lock':  0x000080
            }

    if action not in HOSTFLAG_ACTION:
        loggingOutput( self, 'Log', "thermostat_eurotronic_hostflag - unknown action %s" %action)
        return

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    attribute = "%04x" %0x4008
    data_type = "22" # U24
    data = "%06x" %HOSTFLAG_ACTION[action]
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
    loggingOutput( self, 'Debug', "thermostat_eurotronic_hostflag - for %s with value %s / cluster: %s, attribute: %s type: %s action: %s"
            %(key,data,cluster_id,attribute,data_type, action), nwkid=key)

def thermostat_Calibration( self, key, calibration):

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    attribute = "%04x" %0x0010
    data_type = "20" # Int8
    data = "%02x" %calibration
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
    loggingOutput( self, 'Debug', "thermostat_Calibration - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,attribute,data_type), nwkid=key)

def configHeatSetpoint( self, key ):

    ddhostflags = 0xFFFFEB

def thermostat_Mode( self, key, mode ):

    SYSTEM_MODE = { 'Off' : 0x00 ,
            'Auto' : 0x01 ,
            'Reserved' : 0x02,
            'Cool' : 0x03,
            'Heat' :  0x04,
            'Emergency Heating' : 0x05,
            'Pre-cooling' : 0x06,
            'Fan only' : 0x07 }


    if mode not in SYSTEM_MODE:
        Domoticz.Error("thermostat_Mode - unknown system mode: %s" %mode)
        return

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    attribute = "%04x" %0x001C
    data_type = "30" # Enum8
    data = "%02x" %SYSTEM_MODE[mode]

    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
    loggingOutput( self, 'Debug', "thermostat_Mode - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,attribute,data_type), nwkid=key)

def Thermostat_LockMode( self, key, lockmode):


    LOCK_MODE = { 'unlocked':0x00,
            'templock':0x02,
            'off':0x04,
            'off':0x05
            }

    if lockmode not in LOCK_MODE:
        return

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0204
    Hattribute = "%04x" %0x0001
    data_type = "30" # Int16
    loggingOutput( self, 'Debug', "lockmode: %s" %lockmode, nwkid=key)
    lockmode = LOCK_MODE[lockmode]
    Hdata = "%02x" %lockmode
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0204" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingOutput( self, 'Debug', "Thermostat_LockMode - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,Hdata,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)
