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

import Domoticz
import Modules.output
import struct
import Modules.domoticz

from Modules.logging import loggingSchneider
from Modules.zigateConsts import ZIGATE_EP,MAX_LOAD_ZIGATE

SCHNEIDER_BASE_EP = '0b'


def pollingSchneider( self, key ):

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

    loggingSchneider( self, 'Debug', "callbackDeviceAwake_Schneider - Nwkid: %s, EndPoint: %s cluster: %s" \
            %(NwkId, EndPoint, cluster),NwkId )
    if cluster == '0201':
        callbackDeviceAwake_Schneider_SetPoints( self, NwkId, EndPoint, cluster)

    return

def callbackDeviceAwake_Schneider_SetPoints( self, NwkId, EndPoint, cluster):

    # Schneider Wiser Valve Thermostat is a battery device, which receive commands only when it has sent a Report Attribute
    if 'Model' in self.ListOfDevices[NwkId]:
        if self.ListOfDevices[NwkId]['Model'] == 'EH-ZB-VACT':
            now = time()
            # Manage SetPoint
            if '0201' in self.ListOfDevices[NwkId]['Ep'][EndPoint]:
                if '0012' in self.ListOfDevices[NwkId]['Ep'][EndPoint]['0201']:
                    if 'Schneider' not in self.ListOfDevices[NwkId]:
                        self.ListOfDevices[NwkId]['Schneider'] = {}
                    if 'Target SetPoint' in self.ListOfDevices[NwkId]['Schneider']:
                        if self.ListOfDevices[NwkId]['Schneider']['Target SetPoint'] and self.ListOfDevices[NwkId]['Schneider']['Target SetPoint'] != int( self.ListOfDevices[NwkId]['Ep'][EndPoint]['0201']['0012'] ):
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


    return

def schneider_wiser_registration( self, Devices, key ):
    """
    This method is called during the pairing/discovery process.
    Purpose is to do some initialisation (write) on the coming device.
    """

    loggingSchneider( self, 'Debug', "schneider_wiser_registration for device %s" %key)
    
    # nwkid might have changed so we need to reload the zoning
    self.SchneiderZone = None
    importSchneiderZoning (self)
    
    EPout = SCHNEIDER_BASE_EP

    if 'Model' not in self.ListOfDevices[key]:
        Domoticz.Error("Undefined Model, registration !!!")
        return

    # Set Commissioning as Done
    manuf_id = "105e"
    manuf_spec = "01"
    cluster_id = "%04x" %0x0000
    Hattribute = "%04x" %0xe050
    data_type = "10" # Bool
    data = "%02x" %True
    loggingSchneider( self, 'Debug', "Schneider Write Attribute %s with value %s / Endpoint : %s, cluster: %s, attribute: %s type: %s"
            %(key,data,EPout,cluster_id,Hattribute,data_type), nwkid=key)
    Modules.output.write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)

    if self.ListOfDevices[key]['Model'] == 'EH-ZB-RTS': # Thermostat
        # Set Language
        manuf_id = "105e"
        manuf_spec = "01"
        cluster_id = "%04x" %0x0000
        Hattribute = "%04x" %0x5011
        data_type = "42" # String
        data = '656e'  # 'en'
        loggingSchneider( self, 'Debug', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
                %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
        Modules.output.write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)

        cluster_id = "%04x" %0x0201
        Hattribute = "%04x" %0x0012
        default_temperature = 2000
        setpoint = schneider_find_attribute_and_set(self,key,EPout,cluster_id,Hattribute,default_temperature)
        schneiderUpdateThermostatDevice(self, Devices, key, EPout, cluster_id, setpoint)

        loggingSchneider( self, 'Debug', "Schneider set default value Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)


    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-VACT'): # Thermostatic Valve
        cluster_id = "%04x" %0x0201
        manuf_id = "0000"
        manuf_spec = "00"
        # Set 0x01 to 0x0201/0xe013 : ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_THRESHOLD
        Hattribute = "%04x" %0xe013
        data_type = "20"
        # 0x00  After a first Pairing
        # 0x04  After a restart of the Hub or when changing battery of Valve
        data = '00'  
        loggingSchneider( self, 'Debug', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
                %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
        Modules.output.write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)

    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-HACT', 'EH-ZB-VACT' ): # Actuator, Valve
        # Set no Calibration
        manuf_id = "0000"
        manuf_spec = "00"
        cluster_id = "%04x" %0x0201
        # Set 0x00 to 0x0201/0x0010
        Hattribute = "%04x" %0x0010
        data_type = "28" 
        data = '00'  
        loggingSchneider( self, 'Debug', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
                %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
        Modules.output.write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)

    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-HACT', 'EH-ZB-VACT'): # Actuator 
        # ATTRIBUTE_THERMOSTAT_ZONE_MODE
        cluster_id = "%04x" %0x0201
        manuf_id = "105e"
        manuf_spec = "01"
        # Set 0x01 to 0x0201/0xe010
        Hattribute = "%04x" %0xe010
        data_type = "30"
        # 0x01 User Mode Manual
        # 0x02 User Mode Schedule
        # 0x03 User Mode Manual Energy Saver
        data = '01'  
        loggingSchneider( self, 'Debug', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
                %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
        Modules.output.write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)

    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-HACT' ): # Actuator
        # ATTRIBUTE_THERMOSTAT_HACT_CONFIG
        cluster_id = "%04x" %0x0201
        manuf_id = "105e"
        manuf_spec = "01"
        # Set 0x01 to 0x0201/0xe011
        Hattribute = "%04x" %0xe011
        data_type = "18"
        data = '03'   # By default register as CONVENTIONEL mode
                      # E attente pour @hairv en FIP
        loggingSchneider( self, 'Debug', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
        Modules.output.write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)


    if self.ListOfDevices[key]['Model'] == 'EH-ZB-BMS': # Thermostat
        cluster_id = "%04x" %0x0009
        value = '00'
        loggingSchneider( self, 'Debug', "Schneider update Alarm Domoticz device Attribute %s Endpoint:%s / cluster: %s to %s"
                %(key,EPout,cluster_id,value), nwkid=key)
        Modules.domoticz.MajDomoDevice(self, Devices, key, EPout, cluster_id, value)


    # Write Location to 0x0000/0x5000 for all devices
    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0000
    Hattribute = "%04x" %0x0010
    data_type = "42"
    data = 'Zigate zone'.encode('utf-8').hex()  # Zigate zone 
    loggingSchneider( self, 'Debug', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
    Modules.output.write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)

    #if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-VACT' ): # Valve
    #    setpoint = 2000
    #    if 'Schneider' in self.ListOfDevices[key]:
    #        if 'Target SetPoint' in self.ListOfDevices[key]['Schneider']:
    #            if self.ListOfDevices[key]['Schneider']['Target SetPoint'] is not Null:
    #                setpoint = self.ListOfDevices[key]['Schneider']['Target SetPoint']
    #
    #    schneider_setpoint( self, key, setpoint)
    #    self.ListOfDevices[key]['Heartbeat'] = 0

    if self.ListOfDevices[key]['Model'] in ( 'EH-ZB-LMACT'): # Pilotage Chaffe eau
        Modules.output.sendZigateCmd(self, "0092","02" + key + ZIGATE_EP + EPout + "01")
        Modules.output.sendZigateCmd(self, "0092","02" + key + ZIGATE_EP + EPout + "00")
        self.ListOfDevices[key]['Heartbeat'] = 0

def schneider_thermostat_behaviour( self, key, mode ):
    """
    Allow switching between Conventionel and FIP mode
    Set 0x0201/0xe011
    HAC into Fil Pilot FIP 0x03, in Covential Mode 0x00
    """

    MODE = { 'conventionel': 0x00, 'setpoint' : 0x02, 'FIP': 0x03 }

    loggingSchneider( self, 'Debug', "schneider_thermostat_behaviour for device %s requesting mode: %s" %(key, mode))
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
    loggingSchneider( self, 'Debug', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
    Modules.output.write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)
    # Reset Heartbeat in order to force a ReadAttribute when possible
    self.ListOfDevices[key]['Heartbeat'] = 0

def schneider_fip_mode( self, key, mode):

    # APS Data: 0x00 0x0b 0x01 0x02 0x04 0x01 0x0b 0x45 0x11 0xc1 0xe1 0x00 0x01 0x03

    MODE = { 'Confort': 0x00,
            'Confort -1': 0x01,
            'Confort -2': 0x02,
            'Eco': 0x03,
            'Frost Protection': 0x04,
            'Off': 0x05 }

    loggingSchneider( self, 'Debug', "schneider_fip_mode for device %s requesting mode: %s" %(key, mode))

    if mode not in MODE:
        Domoticz.Error("schneider_fip_mode - %s unknown mode: %s" %mode)

    # determine which Endpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    # Make sure that we are in FIP Mode
    setFIPModeRequired = True
    if EPout in self.ListOfDevices[ key ]['Ep']:
        if '0201' in  self.ListOfDevices[ key ]['Ep'][EPout]:
            if 'e011' in  self.ListOfDevices[ key ]['Ep'][EPout]['0201']:
                if self.ListOfDevices[ key ]['Ep'][EPout]['0201'] == '83':
                    setFIPModeRequired = False

    if setFIPModeRequired:
        schneider_thermostat_behaviour( self, key, 'FIP')

    cluster_frame = '11'
    sqn = '00'
    if 'SQN' in self.ListOfDevices[key]:
        if self.ListOfDevices[key]['SQN'] != {} and self.ListOfDevices[key]['SQN'] != '':
            sqn = '%02x' %(int(self.ListOfDevices[key]['SQN'],16) + 1)
    cmd = 'e1'

    zone_mode = '01' # Heating
    fipmode = '%02X' %MODE[ mode ]
    prio = '01' # Prio

    payload = cluster_frame + sqn + cmd + zone_mode + fipmode + prio + 'ff'

    Modules.output.raw_APS_request( self, key, EPout, '0201', '0104', payload, zigate_ep=ZIGATE_EP)
    self.ListOfDevices[key]['Heartbeat'] = 0


def schneider_check_and_set_bind (self, key):
    loggingSchneider(self, 'Debug', "schneider_check_and_set_bind : %s " %key )

    Cluster_bind1 = '0201'
    Cluster_bind2 = '0402'
    if self.SchneiderZone is not None:
        for zone in self.SchneiderZone:
            if self.SchneiderZone[ zone ]['Thermostat']['NWKID'] == key :
                for hact in self.SchneiderZone[ zone ]['Thermostat']['HACT']:
                    srcIeee = self.SchneiderZone[ zone ]['Thermostat']['IEEE']
                    targetIeee = self.SchneiderZone[ zone ]['Thermostat']['HACT'][hact]['IEEE']
                    loggingSchneider(self, 'Debug', "schneider_check_and_set_bind : self.ListOfDevices[key]  %s " %self.ListOfDevices[key]  )

                    if 'ZoneBinded' in self.ListOfDevices[key] and \
                        hact in self.ListOfDevices[key]['ZoneBinded'] and \
                        Cluster_bind1 in self.ListOfDevices[key]['ZoneBinded'][hact] and \
                        Cluster_bind2 in self.ListOfDevices[key]['ZoneBinded'][hact] :
                            continue
                    if 'ZoneBinded' not in self.ListOfDevices[key]:
                        self.ListOfDevices[key]['ZoneBinded'] = {}
                    if hact not in self.ListOfDevices[key]['ZoneBinded']:
                        self.ListOfDevices[key]['ZoneBinded'][hact] = {}
                    self.ListOfDevices[key]['ZoneBinded'][hact][Cluster_bind1] = 'Done'
                    self.ListOfDevices[key]['ZoneBinded'][hact][Cluster_bind2] = 'Done'
                    datas =  str(srcIeee)+str(SCHNEIDER_BASE_EP)+str(Cluster_bind1)+str("03")+str(targetIeee)+str(SCHNEIDER_BASE_EP)
                    Modules.output.sendZigateCmd(self, "0030", datas )
                    datas =  str(targetIeee)+str(SCHNEIDER_BASE_EP)+str(Cluster_bind1)+str("03")+str(srcIeee)+str(SCHNEIDER_BASE_EP)
                    Modules.output.sendZigateCmd(self, "0030", datas )

                    datas =  str(srcIeee)+str(SCHNEIDER_BASE_EP)+str(Cluster_bind2)+str("03")+str(targetIeee)+str(SCHNEIDER_BASE_EP)
                    Modules.output.sendZigateCmd(self, "0030", datas )
                    datas =  str(targetIeee)+str(SCHNEIDER_BASE_EP)+str(Cluster_bind2)+str("03")+str(srcIeee)+str(SCHNEIDER_BASE_EP)
                    Modules.output.sendZigateCmd(self, "0030", datas )


def schneider_setpoint_thermostat( self, key, setpoint):

    # SetPoint is in centidegrees

    EPout = SCHNEIDER_BASE_EP
    ClusterID = '0201'
    attr = '0012'
    NWKID = key
    schneider_find_attribute_and_set (self,NWKID,EPout,ClusterID,attr,setpoint,setpoint)
    if EPout not in self.ListOfDevices[NWKID]['Ep']:
        self.ListOfDevices[NWKID]['Ep'][EPout] = {}
    if ClusterID not in self.ListOfDevices[NWKID]['Ep'][EPout]:
        self.ListOfDevices[NWKID]['Ep'][EPout][ClusterID] = {}
    if not isinstance( self.ListOfDevices[NWKID]['Ep'][EPout][ClusterID] , dict):
        self.ListOfDevices[NWKID]['Ep'][EPout][ClusterID] = {}
    if attr not in self.ListOfDevices[NWKID]['Ep'][EPout][ClusterID]:
        self.ListOfDevices[NWKID]['Ep'][EPout][ClusterID][attr] = {}
    if 'Ep' in self.ListOfDevices[NWKID]:
        if EPout in self.ListOfDevices[NWKID]['Ep']:
            if ClusterID in self.ListOfDevices[NWKID]['Ep'][EPout]:
                if attr in self.ListOfDevices[NWKID]['Ep'][EPout][ClusterID]:
                    self.ListOfDevices[NWKID]['Ep'][EPout][ClusterID][attr] = setpoint
    importSchneiderZoning(self)

    if self.SchneiderZone is not None:
        schneider_check_and_set_bind (self, key)
        for zone in self.SchneiderZone:
            loggingSchneider(self, 'Debug', "schneider_setpoint - Zone Information: %s " %zone )
            if self.SchneiderZone[ zone ]['Thermostat']['NWKID'] == NWKID :
                loggingSchneider( self, 'Debug', "schneider_setpoint - found %s " %zone )
                for hact in self.SchneiderZone[ zone ]['Thermostat']['HACT']:
                    loggingSchneider( self, 'Debug', "schneider_setpoint - found hact %s " %hact )
                    schneider_setpoint_actuator(self, hact, setpoint)


def schneider_setpoint_actuator( self, key, setpoint):
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

    if 'SQN' in self.ListOfDevices[key]:
        if self.ListOfDevices[key]['SQN'] != {} and self.ListOfDevices[key]['SQN'] != '':
            sqn = '%02x' % (int(self.ListOfDevices[key]['SQN'],16) + 1)
    cmd = 'e0'

    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    if 'Schneider' not in self.ListOfDevices[key]:
        self.ListOfDevices[key]['Schneider'] = {}
    self.ListOfDevices[key]['Schneider']['Target SetPoint'] = setpoint
    self.ListOfDevices[key]['Schneider']['TimeStamp SetPoint'] = int(time())

    # Make sure that we are in FIP Mode
    setSetpointModeRequired = True
    if EPout in self.ListOfDevices[ key ]['Ep']:
        if '0201' in  self.ListOfDevices[ key ]['Ep'][EPout]:
            if 'e011' in  self.ListOfDevices[ key ]['Ep'][EPout]['0201']:
                if self.ListOfDevices[ key ]['Ep'][EPout]['0201'] == '82': # 02 becomes 82 , 00 becomes, 03 becomes 83
                    setSetpointModeRequired = False

    if setSetpointModeRequired:
        schneider_thermostat_behaviour( self, key, 'setpoint')

    setpoint = '%04X' %setpoint
    zone = '01'

    payload = cluster_frame + sqn + cmd + '00' + zone + setpoint[2:4] + setpoint[0:2] + 'ff'

    Modules.output.raw_APS_request( self, key, EPout, '0201', '0104', payload, zigate_ep=ZIGATE_EP)
    self.ListOfDevices[key]['Heartbeat'] = 0


def schneider_setpoint( self, key, setpoint):

    if 'Model' in self.ListOfDevices[key]:
        if self.ListOfDevices[key]['Model'] == 'EH-ZB-RTS':
            schneider_setpoint_thermostat(self, key, setpoint)
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
    if 'SQN' in self.ListOfDevices[key]:
        if self.ListOfDevices[key]['SQN'] != {} and self.ListOfDevices[key]['SQN'] != '':
            sqn = '%02x' % (int(self.ListOfDevices[key]['SQN'],16) + 1)
    cmd = '0a'

    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    setpoint = '%04X' %setpoint

    payload = cluster_frame + sqn + cmd + attr + dataType + setpoint[2:4] + setpoint[0:2] 

    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0402" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    Modules.output.raw_APS_request( self, key, EPout, '0402', '0104', payload, zigate_ep=ZIGATE_EP)
    self.ListOfDevices[key]['Heartbeat'] = 0



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


    loggingSchneider( self, 'Debug', "schneider_EHZBRTS_thermoMode - %s Mode: %s" %(key, mode), key)


    if mode not in EHZBRTS_THERMO_MODE:
        Domoticz.Error("Unknow Thermostat Mode %s for %s" %(mode, key))
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

    loggingSchneider( self, 'Debug', "Schneider EH-ZB-RTS Thermo Mode  %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,Hattribute,data_type), nwkid=key)
    Modules.output.write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, data)
    self.ListOfDevices[key]['Heartbeat'] = 0

def schneiderRenforceent( self, NWKID):
    
    rescheduleAction = False
    if 'Model' in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]['Model'] == 'EH-ZB-VACT':
            pass
    if 'Schneider Wiser' in self.ListOfDevices[NWKID]:
        if 'HACT Mode' in self.ListOfDevices[NWKID]['Schneider Wiser']:
            if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                schneider_thermostat_behaviour( self, NWKID, self.ListOfDevices[NWKID]['Schneider Wiser']['HACT Mode'])
            else:
                rescheduleAction = True
        if 'HACT FIP Mode' in self.ListOfDevices[NWKID]['Schneider Wiser']:
            if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                schneider_fip_mode( self, NWKID,  self.ListOfDevices[NWKID]['Schneider Wiser']['HACT FIP Mode'])
            else:
                rescheduleAction = True

    return rescheduleAction

def schneiderSendReadAttributesResponse(self, NWKID, EPout, ClusterID, sqn, rawAttr):
    loggingSchneider( self, 'Debug', "Schneider send attributes: nwkid %s ep: %s , clusterId: %s, sqn: %s,data: %s" \
            %(NWKID, EPout, ClusterID, sqn, rawAttr ), NWKID)

    attr = rawAttr[2:4] + rawAttr[0:2]
    data = ''
    dataType = ''
    payload = ''
    if attr == 'e010':
        dataType = '30'
        data = '01'
    elif attr == '0015': #min setpoint temp
        dataType = '29'
        data = '0032' #0.5 degree
    elif attr == '0016': #max setpoint temp
        dataType = '29'
        data = '0DAC' #35.00 degree
    elif attr == '0012': #occupied setpoint temp
        dataType = '29'
        value = schneider_find_attribute_and_set(self,NWKID, EPout, ClusterID,attr, 2000)
        data = '%04X' %value

    cmd = "01"
    status = "00"
    cluster_frame = "18"

    loggingSchneider( self, 'Debug', "Schneider send attributes: nwkid %s ep: %s , clusterId: %s, sqn: %s, attr: %s, dataType: %s, data: %s" \
            %(NWKID, EPout, ClusterID, sqn, attr, dataType, data ), NWKID)

    if dataType == '29':
        payload = cluster_frame + sqn + cmd + rawAttr + status + dataType + data[2:4] + data[0:2]
    elif dataType == '30':
        payload = cluster_frame + sqn + cmd + rawAttr + status + dataType + data

    loggingSchneider( self, 'Debug', "Schneider calls raw_APS_request payload %s" \
            %(payload), NWKID)

    Modules.output.raw_APS_request( self, NWKID, EPout, ClusterID, '0104', payload, zigate_ep=ZIGATE_EP)


def schneiderUpdateThermostatDevice (self, Devices, NWKID, srcEp, ClusterID, setpoint):

    # Check if nwkid is the ListOfDevices
    loggingSchneider( self, 'Debug', "schneiderUpdateThermostatDevice nwkid : %s, setpoint: %s" \
            %(NWKID, setpoint), NWKID)
    if NWKID not in self.ListOfDevices:
        return

    # Look for TargetSetPoint
    domoTemp = round(setpoint/100,1)
    Modules.domoticz.MajDomoDevice(self, Devices, NWKID, srcEp, ClusterID, domoTemp, '0012')

    if 'Ep' in self.ListOfDevices[NWKID]:
        if srcEp in self.ListOfDevices[NWKID]['Ep']:
            if ClusterID in self.ListOfDevices[NWKID]['Ep'][srcEp]:
                if '0012' in self.ListOfDevices[NWKID]['Ep'][srcEp][ClusterID]:
                    self.ListOfDevices[NWKID]['Ep'][srcEp][ClusterID]['0012'] = setpoint
    loggingSchneider( self, 'Debug', "Schneider updateThermostat setpoint:%s  , domoTemp : %s" \
            %(setpoint, domoTemp), NWKID)

def schneiderAlarmReceived (self, Devices, NWKID, srcEp, ClusterID, start, payload):
    """
    Function called when a command is received from the schneider device to alert about over consumption
    """

    #if (start): # force fast reporting
    #    Modules.configureReporting.processConfigureReporting (self, key)
    #else: # do normal reporting
    #    Modules.configureReporting.processConfigureReporting (self, key)

    AlertCode = payload [0:2] # uint8
    AlertClusterId = payload [4:6]  + payload [2:4]# uint16
    loggingSchneider( self, 'Debug', "Schneider schneiderAlarmReceived start:%s, AlertCode: %s, AlertClusterID: %s" \
            %(start, AlertCode,AlertClusterId), NWKID)

    cluster_id = "%04x" %0x0009
    if (start):
        value = '04'
    else:
        value = '00'

    loggingSchneider( self, 'Debug', "Schneider update Alarm Domoticz device Attribute %s Endpoint:%s / cluster: %s to %s"
            %(NWKID,srcEp,cluster_id,value), NWKID)
    Modules.domoticz.MajDomoDevice(self, Devices, NWKID, srcEp, cluster_id, value)

def schneider_set_contract( self, key, EPout, kva):
    """
    Configure the schneider device to report an alarm when consumption is above a threshold in miliamps
    """

    POWER_FACTOR = 0.92
    max_real_power_in_kwh = kva * 1000 * POWER_FACTOR
    max_real_amps = max_real_power_in_kwh / 235
    max_real_amps_before_tripping = max_real_amps * 110 / 100
    max_real_milli_amps_before_tripping = round (max_real_amps_before_tripping * 1000)
    loggingSchneider( self, 'Debug', "schneider_set_contract for device %s %s requesting max_real_milli_amps_before_tripping: %s milliamps"
        %(key,EPout, max_real_milli_amps_before_tripping))

    ClusterId = '0702' # Simple Metering
    ManufacturerID = '0000'
    ManufacturerSpecfic = '00'
    AttributeID = '5121' # Max Current
    DataType = '22' # 24 bits unsigned integer
    data = "%06x" %max_real_milli_amps_before_tripping
    Modules.output.write_attribute_when_awake(self, key, ZIGATE_EP, EPout,ClusterId,ManufacturerID,ManufacturerSpecfic,AttributeID,DataType,data)

    AttributeID = '7003' # Contract Name
    DataType = '42' # String
    data = 'BASE'.encode('utf-8').hex()  # BASE
    Modules.output.write_attribute_when_awake(self, key, ZIGATE_EP, EPout,ClusterId,ManufacturerID,ManufacturerSpecfic,AttributeID,DataType,data)

def schneiderReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):
    """
    Function called when raw APS indication are received for a schneider device - it then decide how to handle it
    """

    loggingSchneider( self, 'Debug', "Schneider read raw APS nwkid: %s ep: %s , clusterId: %s, dstnwkid: %s, dstep: %s, payload: %s" \
            %(srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload), srcNWKID)

    fcf = MsgPayload[0:2] # uint8
    sqn = MsgPayload[2:4] # uint8
    cmd = MsgPayload[4:6] # uint8
    data = MsgPayload[6:] # all the rest

    loggingSchneider( self, 'Debug', "         -- FCF: %s, SQN: %s, CMD: %s, Data: %s" \
            %( fcf, sqn, cmd, data), srcNWKID)

    if ClusterID == '0201' : # Thermostat cluster
        if cmd == '00': #read attributes
            loggingSchneider( self, 'Debug','Schneider cmd 0x00',srcNWKID)
            schneiderSendReadAttributesResponse(self, srcNWKID, srcEp, ClusterID, sqn, data)
        if cmd == 'e0': # command to change setpoint from thermostat
            sTemp = data [4:8]
            setpoint = struct.unpack('h',struct.pack('>H',int(sTemp,16)))[0]
            schneiderUpdateThermostatDevice(self, Devices, srcNWKID, srcEp, ClusterID, setpoint)
    elif ClusterID == '0009': # Alarm cluster
        if cmd == '00': #start of alarm
            loggingSchneider( self, 'Debug','Schneider cmd 0x00',srcNWKID)
            schneiderAlarmReceived (self, Devices, srcNWKID, srcEp, ClusterID, True, data)
        elif cmd == '50': #end of alarm
            loggingSchneider( self, 'Debug','Schneider cmd 0x50',srcNWKID)
            schneiderAlarmReceived (self, Devices, srcNWKID, srcEp, ClusterID, False, data)

    return

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

    self.SchneiderZone = {}
    self.SchneiderZoningFilename = self.pluginconf.pluginConf['pluginConfig'] + SCHNEIDER_ZONING

    if not os.path.isfile( self.SchneiderZoningFilename ) :
        loggingSchneider(self, 'Debug', "importSchneiderZoning - Nothing to import from %s" %self.SchneiderZoningFilename)
        return

    with open( self.SchneiderZoningFilename, 'rt') as handle:
        SchneiderZoning = json.load( handle)

    for zone in SchneiderZoning:
        if 'ieee_thermostat' not in SchneiderZoning[zone]:
            # Missing Thermostat
            loggingSchneider( self, 'Error', "importSchneiderZoning - Missing Thermostat entry in %s" %SchneiderZoning[zone])
            continue

        if SchneiderZoning[zone]['ieee_thermostat'] not in self.IEEE2NWK:
            # Thermostat IEEE not known!
            loggingSchneider(self,  'Error', "importSchneiderZoning - Thermostat IEEE %s do not exist" %SchneiderZoning[zone]['ieee_thermostat'])
            continue
        
        self.SchneiderZone[ zone ] = {}
        self.SchneiderZone[ zone ]['Thermostat'] = {}

        self.SchneiderZone[ zone ]['Thermostat']['IEEE'] = SchneiderZoning[zone]['ieee_thermostat']
        self.SchneiderZone[ zone ]['Thermostat']['NWKID'] = self.IEEE2NWK[ SchneiderZoning[zone]['ieee_thermostat'] ]
        self.SchneiderZone[ zone ]['Thermostat']['HACT'] = {}
        
        if 'actuator' not in SchneiderZoning[zone]:
            # We just have a simple Thermostat
            loggingSchneider(self,  'Debug', "importSchneiderZoning - No actuators for this Zone: %s" %zone)
            continue

        for hact in SchneiderZoning[zone]['actuator']:
            _nwkid = self.IEEE2NWK[ hact ]
            if hact not in self.IEEE2NWK:
                # Unknown in IEEE2NWK
                loggingSchneider(self,  'Error', "importSchneiderZoning - Unknown HACT: %s" %hact)
                continue

            if self.IEEE2NWK[ hact ] not in self.ListOfDevices:
                # Unknown in ListOfDevices
                loggingSchneider(self,  'Error', "importSchneiderZoning - Unknown HACT: %s" %_nwkid)
                continue
            
            self.SchneiderZone[ zone ]['Thermostat']['HACT'][ _nwkid ] = {}
            self.SchneiderZone[ zone ]['Thermostat']['HACT'][ _nwkid ]['IEEE'] = hact

    # At that stage we have imported all informations
    loggingSchneider(self, 'Debug', "importSchneiderZoning - Zone Information: %s " %self.SchneiderZone )

def schneider_find_attribute_and_set(self, NWKID, EP, ClusterID ,attr ,defaultValue , newValue = None):

    loggingSchneider( self, 'Debug', "schneider_find_attribute_or_set NWKID:%s, EP:%s, ClusterID:%s, attr:%s ,defaultValue:%s, newValue:%s" 
                %(NWKID,EP,ClusterID,attr,defaultValue,newValue),NWKID)
    if EP not in self.ListOfDevices[NWKID]['Ep']:
        self.ListOfDevices[NWKID]['Ep'][EP] = {}
    if ClusterID not in self.ListOfDevices[NWKID]['Ep'][EP]:
        self.ListOfDevices[NWKID]['Ep'][EP][ClusterID] = {}
    if not isinstance( self.ListOfDevices[NWKID]['Ep'][EP][ClusterID] , dict):
        self.ListOfDevices[NWKID]['Ep'][EP][ClusterID] = {}
    if attr not in self.ListOfDevices[NWKID]['Ep'][EP][ClusterID]:
        self.ListOfDevices[NWKID]['Ep'][EP][ClusterID][attr] = {}
    if 'Ep' in self.ListOfDevices[NWKID]:
        if EP in self.ListOfDevices[NWKID]['Ep']:
            if ClusterID in self.ListOfDevices[NWKID]['Ep'][EP]:
                if attr in self.ListOfDevices[NWKID]['Ep'][EP][ClusterID]:
                    if self.ListOfDevices[NWKID]['Ep'][EP][ClusterID][attr] == {}:
                        if newValue is None:
                            loggingSchneider( self, 'Debug', "schneider_find_attribute_or_set: could not find value, setting default value  %s" %defaultValue,NWKID)
                            self.ListOfDevices[NWKID]['Ep'][EP][ClusterID][attr] = defaultValue
                        else:
                            loggingSchneider( self, 'Debug', "schneider_find_attribute_or_set: could not find value, setting new value  %s" %newValue,NWKID)
                            self.ListOfDevices[NWKID]['Ep'][EP][ClusterID][attr] = newValue

                    loggingSchneider( self, 'Debug', "schneider_find_attribute_or_set : found value %s"%(self.ListOfDevices[NWKID]['Ep'][EP][ClusterID][attr]),NWKID)
                    found = self.ListOfDevices[NWKID]['Ep'][EP][ClusterID][attr]
                    if newValue is not None:
                        loggingSchneider( self, 'Debug', "schneider_find_attribute_or_set : setting new value %s"%newValue,NWKID)
                        self.ListOfDevices[NWKID]['Ep'][EP][ClusterID][attr] = newValue
    return found

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
    MAX_ATTR_PER_REQ = 3

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
    for attr in AttributesConfig:
        attrdirection = "00"
        attrType = AttributesConfig[attr]['DataType']
        minInter = AttributesConfig[attr]['MinInterval']
        maxInter = AttributesConfig[attr]['MaxInterval']
        timeOut = AttributesConfig[attr]['TimeOut']
        chgFlag = AttributesConfig[attr]['Change']
        attrList += attrdirection + attrType + attr + minInter + maxInter + timeOut + chgFlag
        attrLen += 1

        # Let's check if we have to send a chunk
        if attrLen == MAX_ATTR_PER_REQ:
            # Prepare the payload
            datas =   addr_mode + NwkId + ZIGATE_EP + Ep + ClusterId + direction + manufacturer_spec + manufacturer 
            datas +=  "%02x" %(attrLen) + attrList

            Modules.output.sendZigateCmd( self, "0120", datas )

            #Reset the Lenght to 0
            attrList = ''
            attrLen = 0
    # end for 

    # Let's check if we have some remaining to send
    if attrLen != 0 :
        # Prepare the payload
        datas =   addr_mode + NwkId + ZIGATE_EP + Ep + ClusterId + direction + manufacturer_spec + manufacturer 
        datas +=  "%02x" %(attrLen) + attrList
        Modules.output.sendZigateCmd( self, "0120", datas )