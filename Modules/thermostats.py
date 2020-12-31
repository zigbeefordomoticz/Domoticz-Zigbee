#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz

from Classes.LoggingManagement import LoggingManagement

from Modules.readAttributes import ReadAttributeRequest_0201
from Modules.basicOutputs import write_attribute
from Modules.schneider_wiser import schneider_setpoint
from Modules.tuya import tuya_setpoint
from Modules.casaia import casaia_setpoint, casaia_check_irPairing
 
def thermostat_Setpoint_SPZB(  self, NwkId, setpoint):

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0x4003
    data_type = "29" # Int16
    self.log.logging( "Thermostats", 'Debug', "setpoint: %s" %setpoint, nwkid=NwkId)
    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    self.log.logging( "Thermostats", 'Debug', "setpoint: %s" %setpoint, nwkid=NwkId)
    Hdata = "%04x" %setpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[NwkId]['Ep']:
        if "0201" in self.ListOfDevices[NwkId]['Ep'][tmpEp]:
            EPout= tmpEp

    self.log.logging( "Thermostats", 'Debug', "thermostat_Setpoint_SPZB - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(NwkId,Hdata,cluster_id,Hattribute,data_type), nwkid=NwkId)
    write_attribute( self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

def thermostat_Setpoint( self, NwkId, setpoint):

    self.log.logging( "Thermostats", 'Debug', "thermostat_Setpoint - for %s with value %s" %(NwkId,setpoint), nwkid=NwkId)

    if 'Model' in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]['Model'] != {}:
        if self.ListOfDevices[NwkId]['Model'] == 'SPZB0001':
            # Eurotronic
            self.log.logging( "Thermostats", 'Debug', "thermostat_Setpoint - calling SPZB for %s with value %s" %(NwkId,setpoint), nwkid=NwkId)
            thermostat_Setpoint_SPZB( self, NwkId, setpoint)

        elif self.ListOfDevices[NwkId]['Model'] in ( 'EH-ZB-RTS', 'EH-ZB-HACT', 'EH-ZB-VACT' ):
            # Schneider
            self.log.logging( "Thermostats", 'Debug', "thermostat_Setpoint - calling Schneider for %s with value %s" %(NwkId,setpoint), nwkid=NwkId)
            schneider_setpoint(self, NwkId, setpoint)
            return

        elif self.ListOfDevices[NwkId]['Model'] in ( 'TS0601', 'ivfvd7h', 'fvq6avy' , 'eaxp72v'):
            # Tuya
            self.log.logging( "Thermostats", 'Log', "thermostat_Setpoint - calling Tuya for %s with value %s" %(NwkId, setpoint), nwkid=NwkId)
            tuya_setpoint(self, NwkId, setpoint)
            return

        elif self.ListOfDevices[NwkId]['Model'] in ( 'AC201A', ):
            casaia_setpoint(self, NwkId, setpoint)
            return

    self.log.logging( "Thermostats", 'Debug', "thermostat_Setpoint - standard for %s with value %s" %(NwkId,setpoint), nwkid=NwkId)

    EPout = '01'
    for tmpEp in self.ListOfDevices[NwkId]['Ep']:
        if "0201" in self.ListOfDevices[NwkId]['Ep'][tmpEp]:
            EPout= tmpEp

    # Heat setpoint by default
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0x0012

    if cluster_id in self.ListOfDevices[NwkId]['Ep'][EPout]:
        if '001c' in self.ListOfDevices[NwkId]['Ep'][EPout][cluster_id]:
            if self.ListOfDevices[NwkId]['Ep'][EPout][cluster_id]['001c'] == 0x03:
                # Cool Setpoint
                Hattribute = "%04x" %0x0011

    manuf_id = "0000"
    manuf_spec = "00"
    
    data_type = "29" # Int16
    self.log.logging( "Thermostats", 'Debug', "setpoint: %s" %setpoint, nwkid=NwkId)
    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    self.log.logging( "Thermostats", 'Debug', "setpoint: %s" %setpoint, nwkid=NwkId)
    Hdata = "%04x" %setpoint
    EPout = '01'

    self.log.logging( "Thermostats", 'Debug', "thermostat_Setpoint - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(NwkId,Hdata,cluster_id,Hattribute,data_type), nwkid=NwkId)
    write_attribute( self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

    ReadAttributeRequest_0201(self, NwkId)

def thermostat_eurotronic_hostflag( self, NwkId, action):

    HOSTFLAG_ACTION = {
            'turn_display':0x000002,
            'boost':       0x000004,
            'clear_off':   0x000010,
            'set_off_mode':0x000020,
            'child_lock':  0x000080
            }

    if action not in HOSTFLAG_ACTION:
        self.log.logging( "Thermostats", 'Log', "thermostat_eurotronic_hostflag - unknown action %s" %action)
        return

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    attribute = "%04x" %0x4008
    data_type = "22" # U24
    data = "%06x" %HOSTFLAG_ACTION[action]
    EPout = '01'
    for tmpEp in self.ListOfDevices[NwkId]['Ep']:
        if "0201" in self.ListOfDevices[NwkId]['Ep'][tmpEp]:
            EPout= tmpEp
    write_attribute( self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
    self.log.logging( "Thermostats", 'Debug', "thermostat_eurotronic_hostflag - for %s with value %s / cluster: %s, attribute: %s type: %s action: %s"
            %(NwkId,data,cluster_id,attribute,data_type, action), nwkid=NwkId)

def thermostat_Calibration( self, NwkId, calibration):

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    attribute = "%04x" %0x0010
    data_type = "28" # Int8
    data = "%02x" %calibration
    EPout = '01'
    for tmpEp in self.ListOfDevices[NwkId]['Ep']:
        if "0201" in self.ListOfDevices[NwkId]['Ep'][tmpEp]:
            EPout= tmpEp
    write_attribute( self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
    self.log.logging( "Thermostats", 'Debug', "thermostat_Calibration - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(NwkId,data,cluster_id,attribute,data_type), nwkid=NwkId)

def configHeatSetpoint( self, NwkId ):

    ddhostflags = 0xFFFFEB

def thermostat_Mode( self, NwkId, mode ):

    SYSTEM_MODE = { 
        'Off' : 0x00 ,
        'Auto' : 0x01 ,
        'Reserved' : 0x02,
        'Cool' : 0x03,
        'Heat' :  0x04,
        'Emergency Heating' : 0x05,
        'Pre-cooling' : 0x06,
        'Fan Only' : 0x07 ,
        'Dry': 0x08,
        'Sleep': 0x09}

    if mode not in SYSTEM_MODE:
        Domoticz.Error("thermostat_Mode - unknown system mode: %s" %mode)
        return

    if 'Model' in self.ListOfDevices[ NwkId ] and self.ListOfDevices[ NwkId ]['Model'] in ( 'AC211', ):
        casaia_check_irPairing( self, NwkId)

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    attribute = "%04x" %0x001C
    data_type = "30" # Enum8
    data = "%02x" %SYSTEM_MODE[mode]

    EPout = '01'
    for tmpEp in self.ListOfDevices[NwkId]['Ep']:
        if "0201" in self.ListOfDevices[NwkId]['Ep'][tmpEp]:
            EPout= tmpEp

    write_attribute( self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
    self.log.logging( "Thermostats", 'Debug', "thermostat_Mode - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(NwkId,data,cluster_id,attribute,data_type), nwkid=NwkId)

def Thermostat_LockMode( self, NwkId, lockmode):


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
    self.log.logging( "Thermostats", 'Debug', "lockmode: %s" %lockmode, nwkid=NwkId)
    lockmode = LOCK_MODE[lockmode]
    Hdata = "%02x" %lockmode
    EPout = '01'
    for tmpEp in self.ListOfDevices[NwkId]['Ep']:
        if "0204" in self.ListOfDevices[NwkId]['Ep'][tmpEp]:
            EPout= tmpEp

    self.log.logging( "Thermostats", 'Debug', "Thermostat_LockMode - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(NwkId,Hdata,cluster_id,Hattribute,data_type), nwkid=NwkId)
    write_attribute( self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)
