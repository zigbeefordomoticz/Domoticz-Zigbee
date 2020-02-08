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
import Modules.output

from Modules.tools import loggingOutput


def schneider_wiser_registration( self, key ):
    """
    This method is called during the pairing/discovery process.
    Purpose is to do some initialisation (write) on the coming device.
    """

    loggingOutput( self, 'Log', "schneider_wiser_registration for device %s" %key)

    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0000" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    # Set Boolean flag to 0xE050
    manuf_id = "105e"
    manuf_spec = "01"
    cluster_id = "%04x" %0x0000
    Hattribute = "%04x" %0xe050
    data_type = "10" # Bool
    data = "%02x" %True
    loggingOutput( self, 'Log', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
    Modules.output.write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)

    if 'Model' not in self.ListOfDevices[key]:
        Domoticz.Error("Undefined Model, registration !!!")
        return

    # Thermostat
    if self.ListOfDevices[key]['Model'] == 'EH-ZB-RTS':
        #  Wite Attribute 0x42 Value = 'en'
        manuf_id = "105e"
        manuf_spec = "01"
        cluster_id = "%04x" %0x0000
        Hattribute = "%04x" %0x5011
        data_type = "42" # String
        data = '656e'  # 'en'
        loggingOutput( self, 'Log', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
                %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
        Modules.output.write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)

    # Write attribute for Actuator
    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-HACT' ):

        manuf_id = "0000"
        manuf_spec = "00"
        cluster_id = "%04x" %0x0201
        # Set 0x00 to 0x0201/0x0010
        Hattribute = "%04x" %0x0010
        data_type = "28" 
        data = '00'  
        loggingOutput( self, 'Log', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
                %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
        Modules.output.write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)

        # Set 0x01 to 0x0201/0xe010
        cluster_id = "%04x" %0x0201
        manuf_id = "105e"
        manuf_spec = "01"
        Hattribute = "%04x" %0xe010
        data_type = "30"
        data = '01'  
        loggingOutput( self, 'Log', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
                %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
        Modules.output.write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)

        # Set 0x01 to 0x0201/0xe011
        cluster_id = "%04x" %0x0201
        manuf_id = "105e"
        manuf_spec = "01"
        Hattribute = "%04x" %0xe011
        data_type = "18"
        data = '00'   # By default register as CONVENTIONEL mode
        loggingOutput( self, 'Log', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
        Modules.output.write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)

    # Write Location to 0x0000/0x5000 for all devices
    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0000
    Hattribute = "%04x" %0x0010
    data_type = "42"
    data = '5A6967617465205A6F6E65'  # Zigate zone
    loggingOutput( self, 'Log', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
    Modules.output.write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)

def schneider_thermostat_behaviour( self, key, mode ):
    """
    Allow switching between Conventionel and FIP mode
    Set 0x0201/0xe011
    HAC into Fil Pilot FIP 0x03, in Covential Mode 0x00
    """

    MODE = { 'conventionel': 0x00, 'FIP': 0x03 }

    loggingOutput( self, 'Log', "schneider_thermostat_behaviour for device %s requesting mode: %s" %(key, mode))
    if mode not in MODE:
        Domoticz.Error("schneider_thermostat_behaviour - %s unknown mode %s" %(key, mode))
        return

    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0000" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp
    manuf_id = "105e"
    manuf_spec = "01"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0xe011
    data_type = "18"
    data = '%02X' %MODE[ mode ]
    loggingOutput( self, 'Log', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
    Modules.output.write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)
    Modules.output.ReadAttributeRequest_0201(self, key)

def schneider_fip_mode( self, key, mode):

    # APS Data: 0x00 0x0b 0x01 0x02 0x04 0x01 0x0b 0x45 0x11 0xc1 0xe1 0x00 0x01 0x03

    MODE = { 'Confort': 0x00,
            'Confort -1': 0x01,
            'Confort -2': 0x02,
            'Eco': 0x03,
            'Frost Protection': 0x04,
            'Off': 0x05 }

    if mode not in MODE:
        Domoticz.Error("schneider_fip_mode - %s unknown mode: %s" %mode)

    # determine which Endpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    # Make sure that we are in FIP Mode
    setFIPModeRequired = True
    if 'EPOut' in self.ListOfDevices[ key ]['Ep']:
        if '0201' in  self.ListOfDevices[ key ]['Ep'][EPOut]:
            if 'e011' in  self.ListOfDevices[ key ]['Ep'][EPOut]['0201']:
                if self.ListOfDevices[ key ]['Ep'][EPOut]['0201'] == '03':
                    setFIPModeRequired = False

    if setFIPModeRequired:
        schneider_thermostat_behaviour( self, key, 'FIP')

    cluster_frame = '11'
    sqn = '00'
    cmd = 'e1'

    zone_mode = '01' # Heating
    fipmode = '%02X' %MODE[ mode ]
    prio = '01' # Prio

    payload = cluster_frame + sqn + cmd + zone_mode + fipmode + prio + 'ff'

    Domoticz.Log("schneider_fip_mode - Nwkid: %s Fip Mode: %s ==> Payload: %s" %(key, fipmode, payload))
    Modules.output.raw_APS_request( self, key, EPout, '0201', '0104', payload, zigate_ep='01')


def schneider_setpoint( self, key, setpoint):

    # SetPoint 21°C ==> 2100 => 0x0834
    # APS Data: 0x00 0x0b 0x01 0x02 0x04 0x01 0x0b 0x45 0x11 0xc1 0xe0 0x00 0x01 0x34 0x08 0xff
    #                                                                            |---------------> LB HB Setpoint
    #                                                             |--|---------------------------> Command 0xe0
    #                                                        |--|--------------------------------> SQN
    #                                                   |--|-------------------------------------> Cluster Frame

    cluster_frame = '11'
    sqn = '00'
    cmd = 'e0'

    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    setpoint = '%04X' %setpoint
    length = '01' # 1 attribute

    payload = cluster_frame + sqn + cmd + '00' + length + setpoint[2:4] + setpoint[0:2] + 'ff'

    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    Domoticz.Log("schneider_setpoint - %s %s ==> Payload: %s" %(key, setpoint, payload))
    Modules.output.raw_APS_request( self, key, EPout, '0201', '0104', payload, zigate_ep='01')


def schneider_EHZBRTS_thermoMode( self, key, mode):


    # Attribute 0x0201 / 0xE010 ==> 0x01 ==> Mode Manuel   / Data Type 0x30
    #                               0x02 ==> Mode Programme
    #                               0x03 ==> Mode Economie
    #                               0x06 ==> Mode Vacances
    
    EHZBRTS_THERMO_MODE = { 0: 0x00,
            10: 0x01,
            20: 0x02,
            30: 0x03,
            40: 0x04,
            50: 0x05,
            60: 0x06,
            }


    Domoticz.Log("schneider_EHZBRTS_thermoMode - %s Mode: %s" %(key, mode))


    if mode not in EHZBRTS_THERMO_MODE:
        Domoticz.Error("Unknow Thermostat Mode %s for %s" %(mode, key))
        return

    manuf_id = "105e"
    manuf_spec = "01"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0xe010
    data_type = "30" # Uint8
    data = "%02x" %EHZBRTS_THERMO_MODE[ mode ]

    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingOutput( self, 'Log', "Schneider EH-ZB-RTS Thermo Mode  %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
    Modules.output.write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)
