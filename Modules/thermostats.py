#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz

from Modules.logging import loggingThermostats
from Modules.readAttributes import ReadAttributeRequest_0201
from Modules.basicOutputs import write_attribute
from Modules.schneider_wiser import schneider_setpoint
 
def thermostat_Setpoint_SPZB(  self, key, setpoint):

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0x4003
    data_type = "29" # Int16
    loggingThermostats( self, 'Debug', "setpoint: %s" %setpoint, nwkid=key)
    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    loggingThermostats( self, 'Debug', "setpoint: %s" %setpoint, nwkid=key)
    Hdata = "%04x" %setpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingThermostats( self, 'Debug', "thermostat_Setpoint_SPZB - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,Hdata,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

def thermostat_Setpoint( self, key, setpoint):

    loggingThermostats( self, 'Debug', "thermostat_Setpoint - for %s with value %s" %(key,setpoint), nwkid=key)

    if ( 'Model' in self.ListOfDevices[key] and self.ListOfDevices[key]['Model'] != {} ):
        if self.ListOfDevices[key]['Model'] == 'SPZB0001':
            loggingThermostats( self, 'Debug', "thermostat_Setpoint - calling SPZB for %s with value %s" %(key,setpoint), nwkid=key)
            thermostat_Setpoint_SPZB( self, key, setpoint)

        elif self.ListOfDevices[key]['Model'] in ( 'EH-ZB-RTS', 'EH-ZB-HACT', 'EH-ZB-VACT' ):
            loggingThermostats( self, 'Debug', "thermostat_Setpoint - calling Schneider for %s with value %s" %(key,setpoint), nwkid=key)
            schneider_setpoint(self, key, setpoint)
            return

    loggingThermostats( self, 'Debug', "thermostat_Setpoint - standard for %s with value %s" %(key,setpoint), nwkid=key)
    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0x0012
    data_type = "29" # Int16
    loggingThermostats( self, 'Debug', "setpoint: %s" %setpoint, nwkid=key)
    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    loggingThermostats( self, 'Debug', "setpoint: %s" %setpoint, nwkid=key)
    Hdata = "%04x" %setpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingThermostats( self, 'Debug', "thermostat_Setpoint - for %s with value %s / cluster: %s, attribute: %s type: %s"
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
        loggingThermostats( self, 'Log', "thermostat_eurotronic_hostflag - unknown action %s" %action)
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
    loggingThermostats( self, 'Debug', "thermostat_eurotronic_hostflag - for %s with value %s / cluster: %s, attribute: %s type: %s action: %s"
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
    loggingThermostats( self, 'Debug', "thermostat_Calibration - for %s with value %s / cluster: %s, attribute: %s type: %s"
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
    loggingThermostats( self, 'Debug', "thermostat_Mode - for %s with value %s / cluster: %s, attribute: %s type: %s"
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
    loggingThermostats( self, 'Debug', "lockmode: %s" %lockmode, nwkid=key)
    lockmode = LOCK_MODE[lockmode]
    Hdata = "%02x" %lockmode
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0204" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingThermostats( self, 'Debug', "Thermostat_LockMode - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,Hdata,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)
