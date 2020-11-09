#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38 & badz
#
"""
    Module: schneider_wiser.py

    Description: 

"""

from time import time
import json
import os.path
import struct

import Domoticz

from Classes.LoggingManagement import LoggingManagement

from Modules.domoMaj import MajDomoDevice
from Modules.basicOutputs import sendZigateCmd, raw_APS_request, write_attribute, read_attribute, ZigatePermitToJoin
from Modules.configureReporting import prepare_and_send_configure_reporting, send_configure_reporting_attributes_set

from Modules.bindings import webBind, WebBindStatus

from Modules.readAttributes import ReadAttributeRequest_0201, ReadAttributeRequest_0001, ReadAttributeRequest_0702, ReadAttributeRequest_0000
from Modules.writeAttributes import write_attribute_when_awake

from Modules.zigateConsts import ZIGATE_EP,MAX_LOAD_ZIGATE, HEARTBEAT
from Modules.tools import getAttributeValue, retreive_cmd_payload_from_8002, is_ack_tobe_disabled

SCHNEIDER_BASE_EP = '0b'


def pollingSchneider( self, key ):
    # sourcery skip: inline-immediately-returned-variable

    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """

    rescheduleAction = False

    return rescheduleAction


def callbackDeviceAwake_Schneider(self, NwkId, EndPoint, cluster):

    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part
    """

    self.log.logging( "Schneider", 'Debug', "callbackDeviceAwake_Schneider - Nwkid: %s, EndPoint: %s cluster: %s" \
            %(NwkId, EndPoint, cluster),NwkId )
    if cluster == '0201':
        callbackDeviceAwake_Schneider_SetPoints( self, NwkId, EndPoint, cluster)
    #if 'Model' in self.ListOfDevices[NwkId]:
    #    if self.ListOfDevices[NwkId]['Model'] in ('EH-ZB-HACT','EH-ZB-BMS', 'EH-ZB-SPD', 'EH-ZB-LMACT', 'EH-ZB-SPD-V2'):
    #        if getAttributeValue(self, NwkId, EndPoint, '0702', '0301') == None or getAttributeValue(self, NwkId, EndPoint, '0702', '0302') == None:
               # ReadAttributeRequest_0702(self, NwkId)
    #           pass

    #if 'Model' in self.ListOfDevices[NwkId]:
    #    if self.ListOfDevices[NwkId]['Model'] in ('EH-ZB-RTS','EH-ZB-VACT', 'EH-ZB-BMS'):
    #        if (int(self.ListOfDevices[NwkId]['Heartbeat'],10) % 3600) == 0:
    #            ReadAttributeRequest_0001(self, NwkId)

    if 'Model' in self.ListOfDevices[NwkId] and \
        self.ListOfDevices[NwkId]['Model'] == 'EH-ZB-VACT' and  \
            'Schneider' in self.ListOfDevices[ NwkId ] and \
                'ReportingMode' in self.ListOfDevices[ NwkId ]['Schneider'] and \
                    self.ListOfDevices[ NwkId ]['Schneider']['ReportingMode'] == 'Fast' and \
                        (self.ListOfDevices[ NwkId ]['Schneider']['Registration'] + ( 14 * 60)) <= time():

        Domoticz.Log("%s/%s Switching Reporting to NORMAL mode" %(NwkId, EndPoint))
        vact_config_reporting_normal(self, NwkId, EndPoint)


def callbackDeviceAwake_Schneider_SetPoints( self, NwkId, EndPoint, cluster):

    # Schneider Wiser Valve Thermostat is a battery device, which receive commands only when it has sent a Report Attribut
    if 'Model' not in self.ListOfDevices[NwkId]:
        return
    if self.ListOfDevices[NwkId]['Model'] != 'EH-ZB-VACT':
        return
    if '0201' not in self.ListOfDevices[NwkId]['Ep'][EndPoint]:
        return

    # Manage SetPoint
    now = time()
    if '0012' in self.ListOfDevices[NwkId]['Ep'][EndPoint]['0201']:
        if 'Schneider' not in self.ListOfDevices[NwkId]:
            self.ListOfDevices[NwkId]['Schneider'] = {}
        if 'Target SetPoint' in self.ListOfDevices[NwkId]['Schneider']:
            if  self.ListOfDevices[NwkId]['Schneider']['Target SetPoint'] and \
                self.ListOfDevices[NwkId]['Schneider']['Target SetPoint'] != int( self.ListOfDevices[NwkId]['Ep'][EndPoint]['0201']['0012'] ):
                # Protect against overloading Zigate
                if now > self.ListOfDevices[NwkId]['Schneider']['TimeStamp SetPoint'] + 15:
                    schneider_setpoint( self, NwkId, self.ListOfDevices[NwkId]['Schneider']['Target SetPoint'] )
    # Manage Zone Mode
    if 'e010' in self.ListOfDevices[NwkId]['Ep'][EndPoint]['0201']:
        if 'Target Mode' in self.ListOfDevices[NwkId]['Schneider']:
            EHZBRTS_THERMO_MODE = { 0: 0x00, 10: 0x01, 20: 0x02, 30: 0x03, 40: 0x04, 50: 0x05, 60: 0x06, }
            if self.ListOfDevices[NwkId]['Schneider']['Target Mode'] is not None:
                if EHZBRTS_THERMO_MODE[self.ListOfDevices[NwkId]['Schneider']['Target Mode']] == int(self.ListOfDevices[NwkId]['Ep'][EndPoint]['0201']['e010'],16):
                    self.ListOfDevices[NwkId]['Schneider']['Target Mode'] = None
                    self.ListOfDevices[NwkId]['Schneider']['TimeStamp Mode'] = None
                else:
                    if now > self.ListOfDevices[NwkId]['Schneider']['TimeStamp Mode'] + 15:
                        schneider_EHZBRTS_thermoMode( self, NwkId, self.ListOfDevices[NwkId]['Schneider']['Target Mode'] )


def schneider_wiser_registration( self, Devices, key ):
    """
    This method is called during the pairing/discovery process.
    Purpose is to do some initialisation (write) on the coming device.
    """
    self.log.logging( "Schneider", 'Debug', "schneider_wiser_registration for device %s" %key)

    if 'Schneider' not in self.ListOfDevices[ key ]:
        self.ListOfDevices[ key ]['Schneider'] = {}
    self.ListOfDevices[ key ]['Schneider']['Registration'] = int(time())


    # nwkid might have changed so we need to reload the zoning
    self.SchneiderZone = None
    importSchneiderZoning (self)
    
    EPout = SCHNEIDER_BASE_EP

    if 'Model' not in self.ListOfDevices[key]:
        _context = {
            'Error code': 'SCHN0001',
            'Device': self.ListOfDevices[key]
        }
        self.log.logging("Schneider", 'Error', "Undefined Model, registration !!!", key, _context)
        return

    # Set Commissioning as Done 0x0000/0xe050 (Manuf Specific)
    wiser_set_commission_done( self, key, EPout)

    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-VACT'): # Thermostatic Valve
        # Config file is based on a Fast Reporting mode.
        self.ListOfDevices[ key ]['Schneider']['ReportingMode']  = 'Fast' 

    # Set 0x00 to 0x0201/0xe013 : ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_THRESHOLD
    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-VACT'): # Thermostatic Valve
        wiser_set_thermostat_window_detection(self, key, EPout, 0x00)

    # Set 0x00 to 0x0201/0x0010 : Local Temperature Calibration 
    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-HACT', 'EH-ZB-VACT' ): # Actuator, Valve
        wiser_set_calibration( self, key, EPout)

    # ATTRIBUTE_THERMOSTAT_ZONE_MODE ( 0xe010 )
    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-HACT', 'EH-ZB-VACT' ): # Actuator, Valve 
        wiser_set_zone_mode( self, key, EPout)

    # Write Location to 0x0000/0x5000 for all devices
    wiser_set_location(self, key, EPout)

    # Set Language to en
    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-RTS',): # Thermostat 
        wiser_set_lang( self, key, EPout, 'en')

    # Set default Thermostat temp
    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-RTS', 'EH-ZB-VACT'): # Thermostat
        cluster_id = "%04x" %0x0201
        Hattribute = "%04x" %0x0012
        default_temperature = 2000
        setpoint = schneider_find_attribute_and_set(self,key,EPout,cluster_id,Hattribute,default_temperature)
        schneider_update_ThermostatDevice(self, Devices, key, EPout, cluster_id, setpoint)

    # Bind thermostat if needed
    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-RTS', ): # Thermostat
        schneider_thermostat_check_and_bind (self, key)
        
    # set fip mode if nothing and dont touch if already exists
    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-HACT' ): # Actuator
        schneider_hact_heater_type (self,key,'registration')
        schneider_actuator_check_and_bind (self, key)

    # BMS: current monitoring systemlets initialize the alarm widget to 00
    if self.ListOfDevices[key]['Model'] == 'EH-ZB-BMS': 
        cluster_id = "%04x" %0x0009 
        value = '00'
        self.log.logging( "Schneider", 'Debug', "Schneider update Alarm Domoticz device Attribute %s Endpoint:%s / cluster: %s to %s"
                %(key,EPout,cluster_id,value), nwkid=key)
        MajDomoDevice(self, Devices, key, EPout, cluster_id, value)

    # Pilotage Chauffe eau
    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-LMACT'): 
        sendZigateCmd(self, "0092","02" + key + ZIGATE_EP + EPout + "00")
        sendZigateCmd(self, "0092","02" + key + ZIGATE_EP + EPout + "01")
    
    # Redo Temp
    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-VACT' ): # Actuator, Valve
        wiser_set_calibration( self, key, EPout)
    self.ListOfDevices[key]['Heartbeat'] = '0'

    # Close the Network
    #ZigatePermitToJoin( self, 0 )

def wiser_set_zone_mode( self, key, EPout): # 0x0201/0xe010
    
        # Set 0x0201/0xe010
        # 0x01 User Mode Manual
        # 0x02 User Mode Schedule
        # 0x03 User Mode Manual Energy Saver

        manuf_id = "0000"  # Not a manufacturer specific with VACT <-> HUB
        manuf_spec = "00"

        cluster_id = "%04x" %0x0201
        Hattribute = "%04x" %0xe010
        data_type = "30"
        data = '01'  
        self.log.logging( "Schneider", 'Debug', "Schneider Write Attribute (zone_mode) %s with value %s / cluster: %s, attribute: %s type: %s"
                %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
        write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled = False)


def wiser_set_location(self, key, EPout): # 0x0000/0x0010
    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0000
    Hattribute = "%04x" %0x0010
    data_type = "42"
    data = 'Zigate zone'.encode('utf-8').hex()  # Zigate zone 
    self.log.logging( "Schneider", 'Debug', "Schneider Write Attribute (zone name) %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled = False)


def wiser_set_calibration( self, key, EPout):  # 0x0201/0x0010
    #  This is used to set the Local Temperature Calibration ( specifies  the  offset  that  can  be  added/subtracted  to  the  actual displayed room temperature )
    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0x0010
    data_type = "28" 
    data = '00'  
    self.log.logging( "Schneider", 'Debug', "wiser_set_calibration Schneider Write Attribute (no Calibration) %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled = False)


def wiser_set_thermostat_window_detection(self, key, EPout, Mode): # 0x0201/0xe013
    # 0x00  After a first Pairing
    # 0x04  After 15' or a restat of the HUB

    cluster_id = "%04x" %0x0201
    manuf_id = "0000"
    manuf_spec = "00"
    Hattribute = "%04x" %0xe013
    data_type = "20"

    data = "%02x" %Mode 
    self.log.logging( "Schneider", 'Debug', "wiser_set_thermostat_window_detection - Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled = False)


def wiser_set_commission_done( self, key, EPout): # 0x0000/0xE050
    manuf_id = "105e"
    manuf_spec = "01"
    cluster_id = "%04x" %0x0000
    Hattribute = "%04x" %0xe050
    data_type = "10" # Bool
    data = "%02x" %True
    self.log.logging( "Schneider", 'Debug', "wiser_set_commission_done Schneider Write Attribute (commisionning done) %s with value %s / Endpoint : %s, cluster: %s, attribute: %s type: %s"
            %(key,data,EPout,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled = False)


def wiser_set_lang(self, key, EPout, lang='eng'): # 0x0000/0x5011
    manuf_id = "105e"
    manuf_spec = "01"
    cluster_id = "%04x" %0x0000
    Hattribute = "%04x" %0x5011
    data_type = "42" # String
    data = lang.encode('utf-8').hex()  # 'en'
    self.log.logging( "Schneider", 'Debug', "wiser_set_lang Schneider Write Attribute (Lang) %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled = False)


def wiser_set_thermostat_default_temp(self, Devices, key, EPout): # 0x0201/0x0012
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0x0012
    default_temperature = 2000
    setpoint = schneider_find_attribute_and_set(self,key,EPout,cluster_id,Hattribute,default_temperature)
    schneider_update_ThermostatDevice(self, Devices, key, EPout, cluster_id, setpoint)


def schneider_hact_heater_type( self, key, type_heater ):
    """[summary]
         allows to set the heater in "fip" or "conventional" mode
         by default it will set it to fip mode
    Arguments:
        key {[int]} -- id of the device
        type {[string]} -- type of heater "fip" of "conventional"
    """
    EPout = SCHNEIDER_BASE_EP

    attrValue = getAttributeValue (self, key, EPout, '0201', 'e011')
    if attrValue is not None:
        current_value = int(attrValue,16)
        force_update = False
    else:
        current_value = 0x82
        force_update = True

    # value received is :
    # bit 0 - mode of heating  : 0 is setpoint, 1 is fip mode
    # bit 1 - mode of heater : 0 is conventional heater, 1 is fip enabled heater
    # for validation , 0x80 is added to he value retrived from HACT

    current_value = current_value - 0x80
    if (type_heater == "conventional"):
        new_value = current_value & 0xFD # we set the bit 1 to 0 and dont touch the other ones . logical_AND 1111 1101
    elif (type_heater == "fip"):
        new_value = current_value | 2  # we set the bit 1 to 1 and dont touch the other ones . logical_OR 0000 0010
    elif (type_heater == "registration"):
        new_value = current_value

    new_value = new_value & 3 # cleanup, to remove everything else but the last two bits 
    if (current_value == new_value) and not force_update: # no change, let's get out
        return

    manuf_id = "105e"
    manuf_spec = "01"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0xe011
    data_type = "18"
    data = '%02X' %new_value
    self.log.logging( "Schneider", 'Debug', "schneider_hact_heater_type Write Attribute (heating mode) %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled = is_ack_tobe_disabled(self, key))

    if EPout in self.ListOfDevices[ key ]['Ep']:
        if '0201' in  self.ListOfDevices[ key ]['Ep'][EPout]:
            self.ListOfDevices[ key ]['Ep'][EPout]['0201']['e011'] = "%02x" %(new_value + 0x80)


def schneider_hact_heating_mode( self, key, mode ):
    """
    Allow switching between "setpoint" and "FIP" mode
    Set 0x0201/0xe011
    HAC into Fil Pilot FIP 0x03, in Covential Mode 0x00
    """

    MODE = { 'setpoint' : 0x02, 'FIP': 0x03 }

    self.log.logging("Schneider", 'Debug', "schneider_hact_heating_mode for device %s requesting mode: %s" %(key, mode))
    if mode not in MODE:
        _context = {
            'Error code': 'SCHN0002',
            'mode': mode,
            'MODE': MODE
        }
        self.log.logging("Schneider", 'Error', "schneider_hact_heating_mode - %s unknown mode %s" %(key, mode), key, _context)
        return

    EPout = SCHNEIDER_BASE_EP

    attrValue = getAttributeValue (self, key, EPout, '0201', 'e011')
    if attrValue is not None:
        current_value = int(attrValue,16)
        force_update = False
    else:
        current_value = 0x82
        force_update = True

    # value received is:
    # bit 0 - mode of heating  : 0 is setpoint, 1 is fip mode
    # bit 1 - mode of heater : 0 is conventional heater, 1 is fip enabled heater
    # for validation , 0x80 is added to he value retrived from HACT

    current_value = current_value - 0x80
    if (mode == "setpoint"):
        new_value = current_value & 0xFE # we set the bit 0 to 0 and dont touch the other ones . logical_AND 1111 1110
    elif (mode == "FIP"):
        new_value = current_value | 1  # we set the bit 0 to 1 and dont touch the other ones . logical_OR 0000 0001

    new_value = new_value & 3 # cleanup, to remove everything else but the last two bits 
    if (current_value == new_value) and not force_update: # no change, let's get out
        return

    manuf_id = "105e"
    manuf_spec = "01"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0xe011
    data_type = "18"
    data = '%02X' %new_value
    self.log.logging( "Schneider", 'Debug', "schneider_hact_heating_mode Write Attribute (heating mode) %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled = is_ack_tobe_disabled(self, key))
    # Reset Heartbeat in order to force a ReadAttribute when possible
    self.ListOfDevices[key]['Heartbeat'] = '0'
    #ReadAttributeRequest_0201(self,key)
    if EPout in self.ListOfDevices[ key ]['Ep']:
        if '0201' in  self.ListOfDevices[ key ]['Ep'][EPout]:
            self.ListOfDevices[ key ]['Ep'][EPout]['0201']['e011'] = "%02x" %(new_value + 0x80)


def schneider_hact_fip_mode( self, key, mode):
    """[summary]
        set fil pilote mode for the actuator 
    Arguments:
        key {[int]} -- id of actuator
        mode {[string]} -- 'Confort' , 'Confort -1' , 'Confort -2', 'Eco', 'Frost Protection', 'Off'
    """
    # APS Data: 0x00 0x0b 0x01 0x02 0x04 0x01 0x0b 0x45 0x11 0xc1 0xe1 0x00 0x01 0x03

    MODE = { 'Confort': 0x00,
            'Confort -1': 0x01,
            'Confort -2': 0x02,
            'Eco': 0x03,
            'Frost Protection': 0x04,
            'Off': 0x05 }

    self.log.logging( "Schneider", 'Debug', "schneider_hact_fip_mode for device %s requesting mode: %s" %(key, mode))

    if mode not in MODE:
        _context = {
            'Error code': 'SCHN0003',
            'mode': mode,
            'MODE': MODE
        }
        self.log.logging( "Schneider", 'Error', "schneider_hact_fip_mode - %s unknown mode: %s" %mode, key, _context)

    EPout = SCHNEIDER_BASE_EP

    schneider_hact_heating_mode( self, key, 'FIP')

    cluster_frame = '11'
    sqn = '00'
    if (
        'SQN' in self.ListOfDevices[key]
        and self.ListOfDevices[key]['SQN'] != {}
        and self.ListOfDevices[key]['SQN'] != ''
    ):
        sqn = '%02x' %(int(self.ListOfDevices[key]['SQN'],16) + 1)
    cmd = 'e1'

    zone_mode = '01' # Heating
    fipmode = '%02X' %MODE[ mode ]
    prio = '01' # Prio

    payload = cluster_frame + sqn + cmd + zone_mode + fipmode + prio + 'ff'

    self.log.logging( "Schneider", 'Debug', "schneider_hact_fip_mode for device %s sending command: %s , zone_monde: %s, fipmode: %s" 
            %(key, cmd, zone_mode, fipmode))

    raw_APS_request( self, key, EPout, '0201', '0104', payload, zigate_ep=ZIGATE_EP, ackIsDisabled = is_ack_tobe_disabled(self, key))
    # Reset Heartbeat in order to force a ReadAttribute when possible
    self.ListOfDevices[key]['Heartbeat'] = '0'


def schneider_thermostat_check_and_bind (self, key, forceRebind = False):
    """ bind the thermostat to the actuators based on the zoning json fie
    Arguments:
        key {[type]} -- [description]
    """
    self.log.logging( "Schneider", 'Debug', "schneider_thermostat_check_and_bind : %s " %key )

    importSchneiderZoning (self)
    if self.SchneiderZone is None:
        return

    Cluster_bind1 = '0201'
    Cluster_bind2 = '0402'
    for zone in self.SchneiderZone:
        if self.SchneiderZone[ zone ]['Thermostat']['NWKID'] != key :
            continue

        for hact in self.SchneiderZone[ zone ]['Thermostat']['HACT']:

            if hact not in self.ListOfDevices:
                continue

            srcIeee = self.SchneiderZone[ zone ]['Thermostat']['IEEE']
            targetIeee = self.SchneiderZone[ zone ]['Thermostat']['HACT'][hact]['IEEE']
            statusBind1 = WebBindStatus (self, srcIeee,SCHNEIDER_BASE_EP,targetIeee,SCHNEIDER_BASE_EP,Cluster_bind1)
            
            if (not (statusBind1 == 'requested')):
                if (statusBind1 != 'binded') or forceRebind:
                    webBind(self, srcIeee,SCHNEIDER_BASE_EP,targetIeee,SCHNEIDER_BASE_EP,Cluster_bind1)
                    webBind(self, targetIeee,SCHNEIDER_BASE_EP,srcIeee,SCHNEIDER_BASE_EP,Cluster_bind1)

            statusBind2 = WebBindStatus (self, srcIeee,SCHNEIDER_BASE_EP,targetIeee,SCHNEIDER_BASE_EP,Cluster_bind2)
            if not (statusBind2 == 'requested'):
                if (statusBind2 != 'binded') or forceRebind:
                    webBind(self, srcIeee,SCHNEIDER_BASE_EP,targetIeee,SCHNEIDER_BASE_EP,Cluster_bind2)
                    webBind(self, targetIeee,SCHNEIDER_BASE_EP,srcIeee,SCHNEIDER_BASE_EP,Cluster_bind2)


def schneider_actuator_check_and_bind (self, key, forceRebind = False):
    """[summary]
        bind the actuators to the thermostat based on the zoning json fie
    Arguments:
        key {[type]} -- [description]
    """
    self.log.logging( "Schneider", 'Debug', "schneider_actuator_check_and_bind : %s " %key )

    importSchneiderZoning (self)
    if self.SchneiderZone is None:
        return

    Cluster_bind1 = '0201'
    Cluster_bind2 = '0402'
    for zone in self.SchneiderZone:
        for hact in self.SchneiderZone[ zone ]['Thermostat']['HACT']:
            if hact != key :
                continue
            
            thermostat_key = self.SchneiderZone[ zone ]['Thermostat']['NWKID']
            if thermostat_key not in self.ListOfDevices:
                continue

            srcIeee = self.SchneiderZone[ zone ]['Thermostat']['HACT'][hact]['IEEE']
            targetIeee = self.SchneiderZone[ zone ]['Thermostat']['IEEE']
            statusBind1 = WebBindStatus (self, srcIeee,SCHNEIDER_BASE_EP,targetIeee,SCHNEIDER_BASE_EP,Cluster_bind1)
            if not (statusBind1 == 'requested'):
                if (statusBind1 != 'binded') or forceRebind:
                    webBind(self, srcIeee,SCHNEIDER_BASE_EP,targetIeee,SCHNEIDER_BASE_EP,Cluster_bind1)
                    webBind(self, targetIeee,SCHNEIDER_BASE_EP,srcIeee,SCHNEIDER_BASE_EP,Cluster_bind1)

            statusBind2 = WebBindStatus (self, srcIeee,SCHNEIDER_BASE_EP,targetIeee,SCHNEIDER_BASE_EP,Cluster_bind2)
            if not (statusBind2 == 'requested'):
                if (statusBind2 != 'binded') or forceRebind:
                    webBind(self, srcIeee,SCHNEIDER_BASE_EP,targetIeee,SCHNEIDER_BASE_EP,Cluster_bind2)
                    webBind(self, targetIeee,SCHNEIDER_BASE_EP,srcIeee,SCHNEIDER_BASE_EP,Cluster_bind2)


def schneider_setpoint_thermostat( self, key, setpoint):
    """[summary]
        called from domoticz device when user change setpoint
        update internal value about the current setpoint value of thermostat , we need it to answer the thermostat when it will ask for it
        update the actuators that are linked to this thermostat based on the zoning json file. 
        updating linked actuatorswon't apply to vact as it is a thermostat and an actuator
    Arguments:
        key {[type]} -- [description]
        setpoint {[type]} -- [description]
    """
    # SetPoint is in centidegrees

    EPout = SCHNEIDER_BASE_EP
    ClusterID = '0201'
    attr = '0012'
    NWKID = key
    
    schneider_find_attribute_and_set (self,NWKID,EPout,ClusterID,attr,setpoint,setpoint)

    importSchneiderZoning(self)
    schneider_thermostat_check_and_bind (self, NWKID)

    if self.SchneiderZone is not None:
        for zone in self.SchneiderZone:
            self.log.logging( "Schneider", 'Debug', "schneider_setpoint - Zone Information: %s " %zone )
            if self.SchneiderZone[ zone ]['Thermostat']['NWKID'] == NWKID :
                self.log.logging( "Schneider", 'Debug', "schneider_setpoint - found %s " %zone )
                for hact in self.SchneiderZone[ zone ]['Thermostat']['HACT']:
                    self.log.logging( "Schneider", 'Debug', "schneider_setpoint - found hact %s " %hact )
                    schneider_setpoint_actuator(self, hact, setpoint)
                    # Reset Heartbeat in order to force a ReadAttribute when possible
                    self.ListOfDevices[key]['Heartbeat'] = '0'
                    schneider_actuator_check_and_bind (self, hact)
                    #ReadAttributeRequest_0201(self,key)


def schneider_setpoint_actuator( self, key, setpoint):
    """[summary]
        send new setpoint to actuators via an e0 command with the new setpoint value
        it is called
        - via schneider_setpoint_thermostat when actuators are linked to a thermostat
        - or schneider awake when a vact woke up and we had a setpoint setting pending

    Arguments:
        key {[type]} -- [description]
        setpoint {[int]} -- [description]
    """
    # SetPoint 2100 (21 degree C) => 0x0834
    # APS Data: 0x00 0x0b 0x01 0x02 0x04 0x01 0x0b 0x45 0x11 0xc1 0xe0 0x00 0x01 0x34 0x08 0xff
    #                                                                            |---------------> LB HB Setpoint
    #                                                             |--|---------------------------> Command 0xe0
    #                                                        |--|--------------------------------> SQN
    #                                                   |--|-------------------------------------> Cluster Frame

    cluster_frame = '11'
    sqn = '00'

    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    if (
        'SQN' in self.ListOfDevices[key]
        and self.ListOfDevices[key]['SQN'] != {}
        and self.ListOfDevices[key]['SQN'] != ''
    ):
        sqn = '%02x' % (int(self.ListOfDevices[key]['SQN'],16) + 1)
    cmd = 'e0'

    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    if 'Schneider' not in self.ListOfDevices[key]:
        self.ListOfDevices[key]['Schneider'] = {}
    self.ListOfDevices[key]['Schneider']['Target SetPoint'] = setpoint
    self.ListOfDevices[key]['Schneider']['TimeStamp SetPoint'] = int(time())


    # Make sure that we are in setpoint Mode
    if (
        'Model' in self.ListOfDevices[key]
        and self.ListOfDevices[key]['Model'] == 'EH-ZB-HACT'
    ):
        schneider_hact_heating_mode( self, key, 'setpoint')

    setpoint = '%04X' %setpoint
    zone = '01'

    payload = cluster_frame + sqn + cmd + '00' + zone + setpoint[2:4] + setpoint[0:2] + 'ff'

    raw_APS_request( self, key, EPout, '0201', '0104', payload, zigate_ep=ZIGATE_EP, ackIsDisabled = is_ack_tobe_disabled(self, key))
    # Reset Heartbeat in order to force a ReadAttribute when possible
    self.ListOfDevices[key]['Heartbeat'] = '0'
    #ReadAttributeRequest_0201(self,key)


def schneider_setpoint( self, key, setpoint):

    if 'Model' in self.ListOfDevices[key]:
        if self.ListOfDevices[key]['Model'] == 'EH-ZB-RTS':
            schneider_setpoint_thermostat(self, key, setpoint)

        elif self.ListOfDevices[key]['Model'] == 'EH-ZB-VACT':
            schneider_setpoint_thermostat(self, key, setpoint)
            schneider_setpoint_actuator( self,key, setpoint)
        else:
            schneider_setpoint_actuator( self,key, setpoint)


def schneider_temp_Setcurrent( self, key, setpoint):
    # SetPoint 2100 (21 degree C) => 0x0834
    # APS Data: 0x00 0x0b 0x01 0x02 0x04 0x01 0x0b 0x45 0x11 0xc1 0xe0 0x00 0x01 0x34 0x08 0xff
    #                                                                            |---------------> LB HB Setpoint
    #                                                             |--|---------------------------> Command 0xe0
    #                                                        |--|--------------------------------> SQN
    #                                                   |--|-------------------------------------> Cluster Frame

    cluster_frame = '18'
    attr = '0000'
    sqn = '00'
    dataType = '29'
    if (
        'SQN' in self.ListOfDevices[key]
        and self.ListOfDevices[key]['SQN'] != {}
        and self.ListOfDevices[key]['SQN'] != ''
    ):
        sqn = '%02x' % (int(self.ListOfDevices[key]['SQN'],16) + 1)
    cmd = '0a'

    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    setpoint = '%04X' %setpoint

    payload = cluster_frame + sqn + cmd + attr + dataType + setpoint[2:4] + setpoint[0:2] 

    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0402" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    self.log.logging( "Schneider", 'Debug', "schneider_temp_Setcurrent for device %s sending command: %s , setpoint: %s" 
            %(key, cmd, setpoint))

    # In the case of VACT, the device is listening more a less every 30s to 50s, 
    # if raw_APS is not sent with ACK there is a risk to lost the command !
    disableAck = True
    if 'PowerSource' in self.ListOfDevices[ key ] and self.ListOfDevices[ key ]['PowerSource'] == 'Battery':
        disableAck = False
    read_attribute( self, key ,ZIGATE_EP , EPout ,'0201' ,'00' , '00' , '0000' , 1 , '0012', ackIsDisabled = disableAck)
    raw_APS_request( self, key, EPout, '0402', '0104', payload, zigate_ep=ZIGATE_EP, ackIsDisabled = is_ack_tobe_disabled(self, key))
    self.ListOfDevices[key]['Heartbeat'] = '0'


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


    self.log.logging("Schneider", 'Debug', "schneider_EHZBRTS_thermoMode - %s Mode: %s" %(key, mode), key)


    if mode not in EHZBRTS_THERMO_MODE:
        _context = {
            'Error code': 'SCHN0004',
            'mode': mode,
            'MODE': EHZBRTS_THERMO_MODE
        }
        self.log.logging("Schneider", 'Error', "Unknow Thermostat Mode %s for %s" %(mode, key), key, _context)
        return

    if 'Schneider' not in self.ListOfDevices[key]:
        self.ListOfDevices[key]['Schneider'] = {}
    self.ListOfDevices[key]['Schneider']['Target Mode'] = mode
    self.ListOfDevices[key]['Schneider']['TimeStamp Mode'] = int(time())

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

    self.log.logging( "Schneider", 'Debug', "Schneider EH-ZB-RTS Thermo Mode  %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)


    write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data, ackIsDisabled = is_ack_tobe_disabled(self, key))

    self.ListOfDevices[key]['Heartbeat'] = '0'


def schneiderRenforceent( self, NWKID):
    
    rescheduleAction = False
    if 'Model' in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]['Model'] == 'EH-ZB-VACT':
        return rescheduleAction

    if 'Schneider Wiser' in self.ListOfDevices[NWKID]:
        if 'HACT Mode' in self.ListOfDevices[NWKID]['Schneider Wiser']:
            if not self.busy and self.ZigateComm.loadTransmit() <= MAX_LOAD_ZIGATE:
                schneider_hact_heating_mode( self, NWKID, self.ListOfDevices[NWKID]['Schneider Wiser']['HACT Mode'])
            else:
                rescheduleAction = True
        if 'HACT FIP Mode' in self.ListOfDevices[NWKID]['Schneider Wiser']:
            if not self.busy and self.ZigateComm.loadTransmit() <= MAX_LOAD_ZIGATE:
                schneider_hact_fip_mode( self, NWKID,  self.ListOfDevices[NWKID]['Schneider Wiser']['HACT FIP Mode'])
            else:
                rescheduleAction = True

    return rescheduleAction


def schneider_thermostat_answer_attribute_request(self, NWKID, EPout, ClusterID, sqn, attr):
    """ Receive an attribute request from thermostat to know if the user has change the domoticz widget
        we answer the current temperature stored in the device

    Arguments:
        NWKID {[type]} -- [description]
        EPout {[type]} -- [description]
        ClusterID {[type]} -- [description]
        sqn {[type]} -- [description]
        rawAttr {[type]} -- [description]
    """
    self.log.logging( "Schneider", 'Debug', "Schneider receive attribute request: nwkid %s ep: %s , clusterId: %s, sqn: %s,rawAttr: %s" \
            %(NWKID, EPout, ClusterID, sqn, attr ), NWKID)

    
    data = ''
    dataType = ''
    payload = ''
    if attr == 'e010': # mode of operation
        dataType = '30'
        data = '01' # Manual
    elif attr == '0015': #min setpoint temp
        dataType = '29'
        if self.ListOfDevices[NWKID]['Model'] in ( 'EH-ZB-VACT'):
            data = '02bc' # 7 degree
        else:
            data = '0032' #0.5 degree
    elif attr == '0016': #max setpoint temp
        dataType = '29'
        if self.ListOfDevices[NWKID]['Model'] in ( 'EH-ZB-VACT'):
            data = '0bb8' #30.00 degree
        else:
            data = '0dac' #35.00 degree
    elif attr == '0012': #occupied setpoint temp
        dataType = '29'
        value = schneider_find_attribute_and_set(self,NWKID, EPout, ClusterID,attr, 2000)
        data = '%04X' %value

    cmd = "01"
    status = "00"
    cluster_frame = "18"

    self.log.logging( "Schneider", 'Debug', "schneider_thermostat_answer_attribute_request: nwkid %s ep: %s , clusterId: %s, sqn: %s, attr: %s, dataType: %s, data: %s" \
            %(NWKID, EPout, ClusterID, sqn, attr, dataType, data ), NWKID)

    if dataType == '29':
        payload = cluster_frame + sqn + cmd + attr[2:4] + attr[0:2] + status + dataType + data[2:4] + data[0:2]
    elif dataType == '30':
        payload = cluster_frame + sqn + cmd + attr[2:4] + attr[0:2] + status + dataType + data

    raw_APS_request( self, NWKID, EPout, ClusterID, '0104', payload, zigate_ep=ZIGATE_EP, ackIsDisabled = is_ack_tobe_disabled(self, NWKID))


def schneider_update_ThermostatDevice (self, Devices, NWKID, srcEp, ClusterID, setpoint):
    """ we received a new setpoint from the thermostat device , we need to update the domoticz widget

    Arguments:
        Devices {[type]} -- [description]
        NWKID {[type]} -- [description]
        srcEp {[type]} -- [description]
        ClusterID {[type]} -- [description]
        setpoint {[type]} -- [description]
    """
    # Check if nwkid is the ListOfDevices
    if NWKID not in self.ListOfDevices:
        return

    # Look for TargetSetPoint
    domoTemp = round(setpoint/100,1)

    self.log.logging( "Schneider", 'Debug', "Schneider updateThermostat setpoint:%s  , domoTemp : %s" \
            %(setpoint, domoTemp), NWKID)

    MajDomoDevice(self, Devices, NWKID, srcEp, ClusterID, domoTemp, '0012')

    # modify attribute of thermostat to store the new temperature requested
    schneider_find_attribute_and_set(self, NWKID,srcEp,ClusterID,'0012',setpoint,setpoint)

    importSchneiderZoning (self)
    if self.SchneiderZone is not None:
        for zone in self.SchneiderZone:
            if self.SchneiderZone[ zone ]['Thermostat']['NWKID'] == NWKID :
                self.log.logging( "Schneider", 'Debug', "schneider_update_ThermostatDevice - found %s " %zone )
                for hact in self.SchneiderZone[ zone ]['Thermostat']['HACT']:
                    self.log.logging( "Schneider", 'Debug', "schneider_update_ThermostatDevice - update hact setpoint mode hact nwwkid:%s " %hact )
                    schneider_hact_heating_mode(self, hact, "setpoint")


def schneiderAlarmReceived (self, Devices, NWKID, srcEp, ClusterID, start, payload):
    """
    Function called when a command is received from the schneider device to alert about over consumption
    """

    #if (start): # force fast reporting
    #    Modules.configureReporting.processConfigureReporting (self, key)
    #else: # do normal reporting
    #    Modules.configureReporting.processConfigureReporting (self, key)

    AlertCode = int(payload [0:2],16) # uint8  0x10: low voltage, 0x11 high voltage, 0x16 high current

    AlertClusterId = payload [4:6]  + payload [2:4]# uint16
    self.log.logging( "Schneider", 'Debug', "schneiderAlarmReceived start:%s, AlertCode: %s, AlertClusterID: %s" \
            %(start, AlertCode,AlertClusterId), NWKID)

    if (AlertCode == 0x16): # max current of contract reached
        cluster_id = "%04x" %0x0009
        if (start):
            value = '04'
        else:
            value = '00'

        self.log.logging( "Schneider", 'Debug', "Schneider update Alarm Domoticz device Attribute %s Endpoint:%s / cluster: %s to %s"
                %(NWKID,srcEp,cluster_id,value), NWKID)
        MajDomoDevice(self, Devices, NWKID, srcEp, cluster_id, value)
    elif (AlertCode == 0x10): # battery low
        ReadAttributeRequest_0001(self, NWKID)
    #Modules.output.ReadAttributeRequest_0702(self, NWKID)


def schneider_set_contract( self, key, EPout, kva):
    """
    Configure the schneider device to report an alarm when consumption is above a threshold in miliamps
    """

    POWER_FACTOR = 0.92
    max_real_power_in_kwh = kva * 1000 * POWER_FACTOR
    max_real_amps = max_real_power_in_kwh / 235
    max_real_amps_before_tripping = max_real_amps * 110 / 100
    max_real_milli_amps_before_tripping = round (max_real_amps_before_tripping * 1000)
    self.log.logging( "Schneider", 'Debug', "schneider_set_contract for device %s %s requesting max_real_milli_amps_before_tripping: %s milliamps"
        %(key,EPout, max_real_milli_amps_before_tripping))

    ClusterId = '0702' # Simple Metering
    ManufacturerID = '0000'
    ManufacturerSpecfic = '00'
    AttributeID = '5121' # Max Current
    DataType = '22' # 24 bits unsigned integer
    data = "%06x" %max_real_milli_amps_before_tripping
    write_attribute_when_awake(self, key, ZIGATE_EP, EPout,ClusterId,ManufacturerID,ManufacturerSpecfic,AttributeID,DataType,data)

    AttributeID = '7003' # Contract Name
    DataType = '42' # String
    data = 'BASE'.encode('utf-8').hex()  # BASE
    write_attribute_when_awake(self, key, ZIGATE_EP, EPout,ClusterId,ManufacturerID,ManufacturerSpecfic,AttributeID,DataType,data)


def schneiderReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):
    """    Function called when raw APS indication are received for a schneider device - it then decide how to handle it

    Arguments:
        Devices {[type]} -- list of devices
        srcNWKID {[type]} -- id of the device that generated the request
        srcEp {[type]} -- Endpoint of the device that generated the request
        ClusterID {[type]} -- cluster Id of the device that generated the request
        dstNWKID {[type]} -- Id of the device that should receive the request
        dstEP {[type]} -- Endpoint of the device that should receive the request
        MsgPayload {[type]} -- [description]
    """

    self.log.logging( "Schneider", 'Debug', "Schneider read raw APS nwkid: %s ep: %s , clusterId: %s, dstnwkid: %s, dstep: %s, payload: %s" \
            %(srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload), srcNWKID)

    
    GlobalCommand, Sqn, ManufacturerCode, Command, Data = retreive_cmd_payload_from_8002( MsgPayload )
    self.log.logging( "Schneider", 'Debug', "         -- SQN: %s, CMD: %s, Data: %s" \
            %(  Sqn, Command, Data), srcNWKID) 

 
    if ClusterID == '0201' : # Thermostat cluster
        if Command == '00': #read attributes
            ManufSpec = '00'
            ManufCode = '0000'
            if ManufacturerCode:
                ManufSpec = '01'
                ManufCode = ManufacturerCode

            buildPayload = Sqn + srcNWKID + srcEp + '01' + ClusterID + '01' + ManufSpec + ManufCode + '%02x' %(len(Data) // 4)
            idx = nbAttribute = 0
            while idx < len(Data):
                nbAttribute += 1
                Attribute = '%04x' %struct.unpack('H',struct.pack('>H',int(Data[idx:idx+4],16)))[0]
                idx += 4

                if self.FirmwareVersion and int(self.FirmwareVersion,16) <= 0x031c:
                    wiser_unsupported_attribute( self, srcNWKID, srcEp, Sqn, ClusterID, dstNWKID, dstEP, Attribute )

                else:
                    self.log.logging( "Schneider", 'Debug','Schneider cmd 0x00 [%s] Read Attribute Request on %s/%s' %(Sqn, ClusterID,Attribute ),srcNWKID)
                    schneider_thermostat_answer_attribute_request(self, srcNWKID, srcEp, ClusterID, Sqn, Attribute)


        if Command == 'e0': # command to change setpoint from thermostat
            sTemp = Data [4:8]
            setpoint = struct.unpack('h',struct.pack('>H',int(sTemp,16)))[0]
            schneider_update_ThermostatDevice(self, Devices, srcNWKID, srcEp, ClusterID, setpoint)

    elif ClusterID == '0009': # Alarm cluster
        if Command == '00': #start of alarm
            self.log.logging( "Schneider", 'Debug','Schneider cmd 0x00',srcNWKID)
            schneiderAlarmReceived (self, Devices, srcNWKID, srcEp, ClusterID, True, Data)
        elif Command == '50': #end of alarm
            self.log.logging( "Schneider", 'Debug','Schneider cmd 0x50',srcNWKID)
            schneiderAlarmReceived (self, Devices, srcNWKID, srcEp, ClusterID, False, Data)

def wiser_read_attribute_request( self, NwkId, Ep, Sqn, ClusterId, Attribute):

    if int(self.FirmwareVersion,16) <= 0x031c:
        # We shouldn't reach here, as the firmware itself will reject and respond.
        wiser_unsupported_attribute( self, NwkId, Ep, Sqn, ClusterId, Attribute )
    else:
        self.log.logging( "Schneider", 'Debug','Schneider cmd 0x00 [%s] Read Attribute Request on %s/%s' %(Sqn, ClusterId,Attribute ),NwkId)
        schneider_thermostat_answer_attribute_request(self, NwkId, Ep, ClusterId, Sqn, Attribute)


def wiser_unsupported_attribute( self, srcNWKID, srcEp, Sqn, ClusterID, attribute ):
    cluster_frame = '18'
    cmd = '01'
    payload = cluster_frame + Sqn + cmd + attribute[2:4] + attribute[0:2] + '86'  
    self.log.logging( "Schneider", 'Debug', "wiser_unsupported_attribute for device %s sending command: %s , attribute: %s" 
            %(srcNWKID, cmd, attribute))
    raw_APS_request( self, srcNWKID, '0b', ClusterID, '0104', payload, zigate_ep=ZIGATE_EP, ackIsDisabled = is_ack_tobe_disabled(self, srcNWKID))


def importSchneiderZoning( self ):
    """
    Import Schneider Zoning Configuration, and populate the corresponding datastructutreÒ
    {
	    "zone1": {
		"ieee_thermostat": "ieee of my thermostat",
		"actuator": ["IEEE1","IEEE2"]
	    },
	    " zone2": {
		"ieee_thermostat": "ieee of my thermostat",
		"actuator": ["IEEE1","IEEE2"]
	    }
    }
    """

    if self.SchneiderZone is not None:
        # Alreday imported. We do it only once
        return

    SCHNEIDER_ZONING = 'schneider_zoning.json'

    
    self.SchneiderZoningFilename = self.pluginconf.pluginConf['pluginConfig'] + SCHNEIDER_ZONING

    if not os.path.isfile( self.SchneiderZoningFilename ) :
        self.log.logging( "Schneider", 'Debug', "importSchneiderZoning - Nothing to import from %s" %self.SchneiderZoningFilename)
        self.SchneiderZone = None
        return

    self.SchneiderZone = {}
    with open( self.SchneiderZoningFilename, 'rt') as handle:
        SchneiderZoning = json.load( handle)

    for zone in SchneiderZoning:
        if 'ieee_thermostat' not in SchneiderZoning[zone]:
            # Missing Thermostat
            _context = {
                'Error code': 'SCHN0005',
                'zone': zone,
                'SchneiderZoning': SchneiderZoning[zone]
            }
            self.log.logging( "Schneider", 'Error', "importSchneiderZoning - Missing Thermostat entry in %s" %SchneiderZoning[zone], None, _context)
            continue

        if SchneiderZoning[zone]['ieee_thermostat'] not in self.IEEE2NWK:
            # Thermostat IEEE not known!
            _context = {
                'Error code': 'SCHN0006',
                'zone': zone,
                'SchneiderZoning[zone]':SchneiderZoning[zone]['ieee_thermostat'],
                'IEEE': self.IEEE2NWK
            }
            self.log.logging( "Schneider",  'Error', "importSchneiderZoning - Thermostat IEEE %s do not exist" %SchneiderZoning[zone]['ieee_thermostat'], None, _context)
            continue
        
        self.SchneiderZone[ zone ] = {}
        self.SchneiderZone[ zone ]['Thermostat'] = {}

        self.SchneiderZone[ zone ]['Thermostat']['IEEE'] = SchneiderZoning[zone]['ieee_thermostat']
        self.SchneiderZone[ zone ]['Thermostat']['NWKID'] = self.IEEE2NWK[ SchneiderZoning[zone]['ieee_thermostat'] ]
        self.SchneiderZone[ zone ]['Thermostat']['HACT'] = {}
        
        if 'actuator' not in SchneiderZoning[zone]:
            # We just have a simple Thermostat
            _context = {
                'Error code': 'SCHN0007',
                'zone': zone,
                'SchneiderZoning': SchneiderZoning[zone]
            }
            self.log.logging( "Schneider",  'Debug', "importSchneiderZoning - No actuators for this Zone: %s" %zone, None, _context)
            continue

        for hact in SchneiderZoning[zone]['actuator']:
            if hact in list(self.IEEE2NWK):
                _nwkid = self.IEEE2NWK[ hact ]
                if hact not in self.IEEE2NWK:
                    # Unknown in IEEE2NWK
                    _context = {
                        'Error code': 'SCHN0008',
                        'zone': zone,
                        'hact': hact,
                        'SchneiderZoning[zone]':SchneiderZoning[zone]['actuator'],
                        'IEEE': self.IEEE2NWK
                    }
                    self.log.logging( "Schneider",  'Error', "importSchneiderZoning - Unknown HACT: %s" %hact, _nwkid, _context)
                    continue

                if self.IEEE2NWK[ hact ] not in self.ListOfDevices:
                    # Unknown in ListOfDevices
                    _context = {
                        'Error code': 'SCHN0009',
                        'zone': zone,
                        'hact': hact,
                        'SchneiderZoning[zone]':SchneiderZoning[zone]['actuator']
                    }
                    self.log.logging( "Schneider",  'Error', "importSchneiderZoning - Unknown HACT: %s" %_nwkid, _nwkid, _context)
                    continue

                self.SchneiderZone[ zone ]['Thermostat']['HACT'][ _nwkid ] = {}
                self.SchneiderZone[ zone ]['Thermostat']['HACT'][ _nwkid ]['IEEE'] = hact

    # At that stage we have imported all informations
    self.log.logging( "Schneider", 'Debug', "importSchneiderZoning - Zone Information: %s " %self.SchneiderZone )


def schneider_find_attribute_and_set(self, NWKID, EP, ClusterID ,attr ,defaultValue , newValue = None):
    """[summary]

    Arguments:
        NWKID {int} -- id of the device
        EP {[type]} -- endpoint of the device you want to manipulate
        ClusterID {[type]} -- cluster of the device you want to manipulate
        attr {[type]} -- attribute of the device you want to manipulate
        defaultValue {[type]} -- default value to use if there is no existing value

    Keyword Arguments:
        newValue {[type]} -- value to erase the existing value (if none then the existing value is untouched)

    Returns:
        [type] -- the value that the attribute will have once the function is finished
                    if no existing value -> defaultValue
                    if there is an existing value and newValue = None -> existing value
                    ifthere is an  existing value and newValue != none -> newValue
    """
    self.log.logging( "Schneider", 'Debug', "schneider_find_attribute_or_set NWKID:%s, EP:%s, ClusterID:%s, attr:%s ,defaultValue:%s, newValue:%s" 
                %(NWKID,EP,ClusterID,attr,defaultValue,newValue),NWKID)
    if EP not in self.ListOfDevices[NWKID]['Ep']:
        self.ListOfDevices[NWKID]['Ep'][EP] = {}
    if ClusterID not in self.ListOfDevices[NWKID]['Ep'][EP]:
        self.ListOfDevices[NWKID]['Ep'][EP][ClusterID] = {}
    if not isinstance( self.ListOfDevices[NWKID]['Ep'][EP][ClusterID] , dict):
        self.ListOfDevices[NWKID]['Ep'][EP][ClusterID] = {}
    if attr not in self.ListOfDevices[NWKID]['Ep'][EP][ClusterID]:
        self.ListOfDevices[NWKID]['Ep'][EP][ClusterID][attr] = {}
    if (
        'Ep' in self.ListOfDevices[NWKID]
        and EP in self.ListOfDevices[NWKID]['Ep']
        and ClusterID in self.ListOfDevices[NWKID]['Ep'][EP]
        and attr in self.ListOfDevices[NWKID]['Ep'][EP][ClusterID]
    ):
        if self.ListOfDevices[NWKID]['Ep'][EP][ClusterID][attr] == {}:
            if newValue is None:
                self.log.logging( "Schneider", 'Debug', "schneider_find_attribute_or_set: could not find value, setting default value  %s" %defaultValue,NWKID)
                self.ListOfDevices[NWKID]['Ep'][EP][ClusterID][attr] = defaultValue
            else:
                self.log.logging( "Schneider", 'Debug', "schneider_find_attribute_or_set: could not find value, setting new value  %s" %newValue,NWKID)
                self.ListOfDevices[NWKID]['Ep'][EP][ClusterID][attr] = newValue

        self.log.logging( "Schneider", 'Debug', "schneider_find_attribute_or_set : found value %s"%(self.ListOfDevices[NWKID]['Ep'][EP][ClusterID][attr]),NWKID)
        found = self.ListOfDevices[NWKID]['Ep'][EP][ClusterID][attr]
        if newValue is not None:
            self.log.logging( "Schneider", 'Debug', "schneider_find_attribute_or_set : setting new value %s"%newValue,NWKID)
            self.ListOfDevices[NWKID]['Ep'][EP][ClusterID][attr] = newValue
    return found



def vact_config_reporting_normal(self, NwkId, EndPoint):
    
    AttributesConfig = {
        "0020": {"DataType": "20", "MinInterval": "0E10", "MaxInterval": "0E10", "TimeOut": "0000","Change":"01"}}
    schneider_UpdateConfigureReporting( self, NwkId, EndPoint, '0001', AttributesConfig)

    ## Set the Window Detection to 0x04
    wiser_set_thermostat_window_detection(self, NwkId, EndPoint, 0x04)  

    AttributesConfig = {
        "0012": {"DataType": "29", "MinInterval": "0258", "MaxInterval": "0258", "TimeOut": "0000","Change":"7FFF"},
        "0000": {"DataType": "29", "MinInterval": "003C", "MaxInterval": "0258", "TimeOut": "0000","Change":"0001"},
        "e030": {"DataType": "20", "MinInterval": "003C", "MaxInterval": "0258", "TimeOut": "0000","Change":"01"},
        "e031": {"DataType": "30", "MinInterval": "000A", "MaxInterval": "0258", "TimeOut": "0000","Change":"01"},
        "e012": {"DataType": "30", "MinInterval": "000A", "MaxInterval": "0258", "TimeOut": "0000","Change":"01"}}
    schneider_UpdateConfigureReporting( self, NwkId, EndPoint, '0201', AttributesConfig)

    AttributesConfig = {
        "0001": {"DataType": "30", "MinInterval": "001E", "MaxInterval": "0258", "TimeOut": "0000","Change":"00"}}

    schneider_UpdateConfigureReporting( self, NwkId, EndPoint, '0204', AttributesConfig) 

    self.ListOfDevices[ NwkId ]['Schneider']['ReportingMode']  = 'Normal'    


def schneider_UpdateConfigureReporting( self, NwkId, Ep, ClusterId = None, AttributesConfig= None):
    """
    Will send a Config reporting to a specific Endpoint of a Wiser Device. 
    It is assumed that the device is on Receive at the time we will be sending the command
    If ClusterId is not None, it will use the AttributesConfig dictionnary for the reporting config,
    otherwise it will retreive the config from the DeviceConf for this particular Model name

    AttributesConfig must have the same format:
        {
            "0000": {"DataType": "29", "MinInterval":"0258", "MaxInterval":"0258", "TimeOut":"0000","Change":"0001"},
            "0012": {"DataType": "29", "MinInterval":"0258", "MaxInterval":"0258", "TimeOut":"0000","Change":"7FFF"},
            "e030": {"DataType": "20", "MinInterval":"003C", "MaxInterval":"0258", "TimeOut":"0000","Change":"01"},
            "e031": {"DataType": "30", "MinInterval":"001E", "MaxInterval":"0258", "TimeOut":"0000","Change":"01"},
            "e012": {"DataType": "30", "MinInterval":"001E", "MaxInterval":"0258", "TimeOut":"0000","Change":"01"}
        }
    """
    MAX_ATTR_PER_REQ = 5

    if NwkId not in self.ListOfDevices:
        return

    if ClusterId is None:
        if 'Model' not in self.ListOfDevices[NwkId]:
            return

        _modelName = self.ListOfDevices[NwkId]['Model']
        if _modelName not in self.DeviceConf:
            return

        if 'ConfigureReporting' not in self.DeviceConf[ _modelName ]:
            return
        if ClusterId not in self.DeviceConf[ _modelName ]['ConfigureReporting']:
            return
        if 'Attributes' not in self.DeviceConf[ _modelName ]['ConfigureReporting'][ClusterId]:
            return

        AttributesConfig = self.DeviceConf[ self.ListOfDevices[NwkId]['Model'] ]['ConfigureReporting'][ClusterId]['Attributes']

    # We have :
    # Nwkid and Endpoint we want to configure
    # ClusterId
    # AttributesConfig
    manufacturer = "0000"
    manufacturer_spec = "00"
    direction = "00"
    
    addr_mode = "02"

    attrList = ''
    attrLen = 0
    attributeList = []             
    for attr in AttributesConfig:
        attrdirection = "00"
        attrType = AttributesConfig[attr]['DataType']
        minInter = AttributesConfig[attr]['MinInterval']
        maxInter = AttributesConfig[attr]['MaxInterval']
        timeOut =  AttributesConfig[attr]['TimeOut']
        chgFlag =  AttributesConfig[attr]['Change']
        attributeList.append( attr )
        if int(attrType, 16) < 0x30:
                attrList += attrdirection + attrType + attr + minInter + maxInter + timeOut + chgFlag
        else:
            # Data Type above 0x30 (included) are considered as discret/analog values and the change flag is not considered.
            # in such NXP stack do not expect that information in the payload
            attrList += attrdirection + attrType + attr + minInter + maxInter + timeOut
        attrLen += 1

        # Let's check if we have to send a chunk
        if attrLen == MAX_ATTR_PER_REQ:
            # Prepare the payload
            #datas =   addr_mode + NwkId + ZIGATE_EP + Ep + ClusterId + direction + manufacturer_spec + manufacturer 
            #datas +=  "%02x" %(attrLen) + attrList
            #sendZigateCmd( self, "0120", datas )
            send_configure_reporting_attributes_set( self, NwkId, Ep, ClusterId, direction, manufacturer_spec, manufacturer, attrLen, attrList , attributeList)

            #Reset the Lenght to 0
            attrList = ''
            attrLen = 0
            attributeList = []             
    # end for 

    # Let's check if we have some remaining to send
    if attrLen != 0 :
        # Prepare the payload
        #datas =   addr_mode + NwkId + SCHNEIDER_BASE_EP + Ep + ClusterId + direction + manufacturer_spec + manufacturer 
        #datas +=  "%02x" %(attrLen) + attrList
        #sendZigateCmd( self, "0120", datas )
        send_configure_reporting_attributes_set( self, NwkId, Ep, ClusterId, direction, manufacturer_spec, manufacturer, attrLen, attrList , attributeList)
