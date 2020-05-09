#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_command.py

    Description: Implement the onCommand() 

"""

import Domoticz
import binascii
import time
import struct
import json

from Modules.actuators import actuators
from Modules.tools import Hex_Format, rgb_to_xy, rgb_to_hsl
from Modules.logging import loggingCommand
from Modules.output import sendZigateCmd, thermostat_Setpoint, thermostat_Mode
from Modules.livolo import livolo_OnOff
from Modules.legrand_netatmo import  legrand_fc40
from Modules.schneider_wiser import schneider_EHZBRTS_thermoMode, schneider_fip_mode, schneider_set_contract, schneider_temp_Setcurrent, schneider_thermostat_behaviour

from Modules.domoticz import UpdateDevice_v2
from Classes.IAS import IAS_Zone_Management
from Modules.zigateConsts import THERMOSTAT_LEVEL_2_MODE, ZIGATE_EP
from Modules.widgets import SWITCH_LVL_MATRIX

def debugDevices( self, Devices, Unit):

    Domoticz.Log("Device Name: %s" %Devices[Unit].Name)
    Domoticz.Log("       DeviceId: %s" %Devices[Unit].DeviceID)
    Domoticz.Log("       Type: %s" %Devices[Unit].Type)
    Domoticz.Log("       Subtype: %s" %Devices[Unit].SubType)
    Domoticz.Log("       SwitchType: %s" %Devices[Unit].SwitchType)
    Domoticz.Log("       Options: %s" %Devices[Unit].Options)
    Domoticz.Log("       LastLevel: %s" %Devices[Unit].LastLevel)
    Domoticz.Log("       LastUpdate: %s" %Devices[Unit].LastUpdate)

# Matrix between Domoticz Type, Subtype, SwitchType and Plugin DeviceType
# Type, Subtype, Switchtype
DEVICE_SWITCH_MATRIX = {
    ( 242,  1,   ): ('ThermoSetpoint', 'TempSetCurrent'),

    ( 241,  2,  7): ('ColorControlRGB',),
    ( 241,  4,  7): ('ColorControlRGBWW',),
    ( 241,  7,  7): ('ColorControlFull',),
    ( 241,  8,  7): ('ColorControlWW',),

    ( 244, 62, 18): ('Switch Selector',), 
    ( 244, 73,  0): ('Switch', '' 'LivoloSWL', 'LivoloSWR' , 'SwitchButton', 'Water', 'Plug'),
    ( 244, 73,  5): ('Smoke',),
    ( 244, 73,  7): ('LvlControl',),
    ( 244, 73,  9): ('Button',),
    ( 244, 73, 13): ('BSO',),
    ( 244, 73, 15): ('VenetianInverted', 'Venetian'),
    ( 244, 73, 16): ('BlindInverted','WindowCovering'),

}

ACTIONATORS = ( 'Switch', 'Plug', 'SwitchAQ2', 'Smoke', 'DSwitch', 'Button', 'DButton', 'LivoloSWL', 'LivoloSWR', 'Toggle',
                'Venetian', 'VenetianInverted', 'WindowCovering', 'BSO',
                'LvlControl', 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl',
                'ThermoSetpoint', 'ThermoMode', 'ThermoModeEHZBRTS', 'TempSetCurrent', 'AlarmWD'
                'LegrandFilPilote', 'FIP', 'HACTMODE','ContractPower'
)

def mgtCommand( self, Devices, Unit, Command, Level, Color ) :

    if Devices[Unit].DeviceID not in self.IEEE2NWK:
        Domoticz.Error("mgtCommand - something strange the Device %s DeviceID: %s Unknown" %(Devices[Unit].Name, Devices[Unit].DeviceID))
        return

    NWKID = self.IEEE2NWK[Devices[Unit].DeviceID]
    loggingCommand( self, 'Debug', "mgtCommand (%s) Devices[%s].Name: %s Command: %s Level: %s Color: %s" 
        %(NWKID, Unit , Devices[Unit].Name, Command, Level, Color ), NWKID)
  
    deviceType = Devices[Unit].Type
    deviceSubType = Devices[Unit].SubType
    deviceSwitchType = Devices[Unit].SwitchType

    if ( deviceType, deviceSubType, deviceSwitchType ) in DEVICE_SWITCH_MATRIX:
        domoticzType = DEVICE_SWITCH_MATRIX[ ( deviceType, deviceSubType, deviceSwitchType ) ] 
        loggingCommand( self, "Debug", "--------->   DeviceType: %s" %str( domoticzType ), NWKID)

    # SignalLvl max is 12
    SignalLevel = self.ListOfDevices[NWKID]['RSSI']
    rssi = 12
    if isinstance(SignalLevel, int):
        rssi = round((SignalLevel * 12) / 255)
        loggingCommand( self, "Debug", "--------->   RSSI level %s " %rssi)
  
    # Battery Level 255 means Main Powered device
    BatteryLevel = self.ListOfDevices[NWKID]['Battery']
    if isinstance(BatteryLevel, float):
        # Looks like sometime we got a float instead of int.
        # in that case convert to int
        loggingCommand( self, "Debug", "--------->   BatteryLvl rounded")
        BatteryLevel = round( BatteryLevel)

    if BatteryLevel == '' or (not isinstance(BatteryLevel, int)):
        loggingCommand( self, "Debug", "--------->   BatteryLvl set to 255" )
        BatteryLevel = 255

    # Now we have to identify the Endpoint, DeviceType to be use for that command
    # inputs are : Device.ID
    # For each Ep of this Device we should find an entry ClusterType where is store Device.ID and DeviceType

    DeviceTypeList = []
    ClusterTypeList = []
    pragmaTypeV3 = True
    if 'ClusterType' in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]['ClusterType'] != {}:
            DeviceTypeList.append( self.ListOfDevices[NWKID]['ClusterType'][str(Devices[Unit].ID)])
            ClusterTypeList.append( ('00', self.ListOfDevices[NWKID]['ClusterType'][str(Devices[Unit].ID)]) )
            pragmaTypeV3 = False
    if pragmaTypeV3:
        for tmpEp in self.ListOfDevices[NWKID]['Ep'] :
            if 'ClusterType' in self.ListOfDevices[NWKID]['Ep'][tmpEp]:
                for key in self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'] :
                    if str(Devices[Unit].ID) == str(key) :
                        loggingCommand( self, "Debug", "--------->   ++ found ( %s, %s)" %( tmpEp, self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'][key] ))
                        #loggingCommand( self, 'Debug', "mgtCommand : found Device : " +str(key) + " in Ep " +str(tmpEp) + " " +str(self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'][key])  , NWKID)
                        DeviceTypeList.append(str(self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'][key]))
                        ClusterTypeList.append( ( tmpEp, self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'][key]) )
    
    if len(DeviceTypeList) == 0 :    # No match with ClusterType
        # Should not happen. We didn't find any Widget references in the Device ClusterType!
        Domoticz.Error("mgtCommand - no ClusterType found !  "  +str(self.ListOfDevices[NWKID]) )
        return

    loggingCommand( self, 'Debug', "--------->   ClusterType founds: %s" %( ClusterTypeList), NWKID)

    actionable = False
    if len(ClusterTypeList) == 1 and ClusterTypeList[0][0] != '00':
        # One element found, we have Endpoint and DevicetypeÒ
        EPout , DeviceType = ClusterTypeList[0]
        loggingCommand( self, "Debug", "--------->   EPOut: %s DeviceType: %s" %( EPout , DeviceType), NWKID)
        # Sanity Check
        forceUpdateDev = False
        if DeviceType in SWITCH_LVL_MATRIX:
            if 'ForceUpdate' in SWITCH_LVL_MATRIX[DeviceType ]:
                forceUpdateDev = SWITCH_LVL_MATRIX[DeviceType ]['ForceUpdate']
        if DeviceType not in ACTIONATORS:
            Domoticz.Log("mgtCommand - You are trying to action a non commandable device Device %s has available Type %s " %( Devices[Unit].Name, DeviceTypeList ))
            return
    
    else:
        # THIS PART OF CODE SHOULD BE REMOVED. I DON'T EXPECT TO REACH That
        Domoticz.Error("THIS IS A CASE PIPICHE IS LOOKING FOR")
        loggingCommand( self, 'Error', "mgtCommand (%s) Devices[%s].Name: %s SwitchType: %s Command: %s Level: %s Color: %s" 
        %(NWKID, Unit , Devices[Unit].Name, deviceSwitchType, Command, Level, Color ), NWKID)
        loggingCommand( self, 'Error', "--------->   ClusterType founds: %s" %( ClusterTypeList), NWKID)
        # We have list of DeviceType, let's see which one are matching Command style

        ClusterSearch = ''
        DeviceType = ''
        forceUpdateDev = False
        for tmpDeviceType in DeviceTypeList :
            if tmpDeviceType in ( 'Button', 'Button_3', 'SwitchIKEA' , 'SwitchAQ2', 'SwitchAQ3', 'DButton', 'Toggle'):
                forceUpdateDev = True

            if tmpDeviceType in ( "Switch", "Plug", "SwitchAQ2", "Smoke", "DSwitch", "Button", "DButton", 'LivoloSWL', 'LivoloSWR', 'Toggle'):
                ClusterSearch="0006"
                DeviceType = tmpDeviceType
            if tmpDeviceType in ( 'Venetian', 'VenetianInverted', "WindowCovering"):
                ClusterSearch = '0102'
                DeviceType = tmpDeviceType
            if tmpDeviceType == 'BSO':
                ClusterSearch = 'fc21'
                DeviceType = tmpDeviceType
            if tmpDeviceType =="LvlControl" :
                ClusterSearch="0008"
                DeviceType = tmpDeviceType
            if tmpDeviceType in ( 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl') :
                ClusterSearch="0300"
                DeviceType = tmpDeviceType
            if tmpDeviceType in ( 'ThermoSetpoint', 'ThermoMode', 'ThermoModeEHZBRTS'):
                ClusterSearch = '0201'
                DeviceType = tmpDeviceType
            if tmpDeviceType == 'TempSetCurrent' :
                ClusterSearch = '0402'
                DeviceType = tmpDeviceType
            if tmpDeviceType == 'Motion':
                ClusterSearch = '0406'
                DeviceType = tmpDeviceType
            if tmpDeviceType == "AlarmWD":
                ClusterSearch = '0502'
                DeviceType = tmpDeviceType
            if tmpDeviceType in ( 'LegrandFilPilote', 'FIP', 'HACTMODE','ContractPower'):
                DeviceType = tmpDeviceType

        if DeviceType == '' and self.pluginconf.pluginConf['forcePassiveWidget']:
            if tmpDeviceType in ( "DButton_3", "SwitchAQ3") :
                loggingCommand( self, 'Debug', "mgtCommand - forcePassiveWidget")
                ClusterSearch="0006"
                DeviceType = "Switch"

        if DeviceType == '':
            Domoticz.Log("mgtCommand - Look you are trying to action a non commandable device Device %s has available Type %s " %( Devices[Unit].Name, DeviceTypeList ))
            return

        loggingCommand( self, 'Debug', "--------->   DeviceType : " +str(DeviceType) , NWKID)

        # A ce stade ClusterSearch est connu
        EPin="01"
        EPout="01"  # If we don't have a cluster search, or if we don't find an EPout for a cluster search, then lets use EPout=01
        # We have now the DeviceType, let's look for the corresponding EP
        if 'ClusterType' in self.ListOfDevices[NWKID]:
            for tmpEp in self.ListOfDevices[NWKID]['Ep'] :
                if ClusterSearch in self.ListOfDevices[NWKID]['Ep'][tmpEp] : #switch cluster
                    EPout=tmpEp
        else :
            for tmpEp in self.ListOfDevices[NWKID]['Ep'] :
                if ClusterSearch in self.ListOfDevices[NWKID]['Ep'][tmpEp] : #switch cluster
                    if 'ClusterType' in self.ListOfDevices[NWKID]['Ep'][tmpEp]:
                        for key in self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'] :
                            if str(Devices[Unit].ID) == str(key) :
                                loggingCommand( self, 'Debug', "--------->   Found Ep " +str(tmpEp) + " for Device " +str(key) + " Cluster " +str(ClusterSearch) , NWKID)
                                EPout = tmpEp

        loggingCommand( self, 'Debug', "--------->   Ready to process Command %s DeviceType: %s ClusterSearch: %s NwkId: %s EPin: %s EPout: %s"
           %(Command, DeviceType, ClusterSearch, NWKID, EPin, EPout   ),NWKID )  

    profalux = False
    if 'Manufacturer' in self.ListOfDevices[NWKID]:
        profalux = ( self.ListOfDevices[NWKID]['Manufacturer'] == '1110' and self.ListOfDevices[NWKID]['ZDeviceID'] in ('0200', '0202') )

    if 'Health' in self.ListOfDevices[NWKID]:
        # If Health is Not Reachable, let's give it a chance to be updated
        if self.ListOfDevices[NWKID]['Health'] == 'Not Reachable':
            self.ListOfDevices[NWKID]['Health'] = ''

    self.ListOfDevices[NWKID]['Heartbeat'] = 0  # Let's force a refresh of Attribute in the next Heartbeat
    if Command == 'Stop':  # Manage the Stop command. For known seen only on BSO and Windowcoering
        loggingCommand( self, 'Debug', "mgtCommand : Stop for Device: %s EPout: %s Unit: %s DeviceType: %s" %(NWKID, EPout, Unit, DeviceType), NWKID)
        if DeviceType == 'BSO':
            from Modules.profalux import profalux_stop
            profalux_stop( self, NWKID)

        elif DeviceType in ( "WindowCovering", "VenetianInverted", "Venetian"):
            # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "02")
            UpdateDevice_v2(self, Devices, Unit, 2, "50", BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            self.ListOfDevices[NWKID]['Heartbeat'] = 0  # Let's force a refresh of Attribute in the next Heartbeat

    if Command == "Off" :  # Manage the Off command. 
        loggingCommand( self, 'Debug', "mgtCommand : Off for Device: %s EPout: %s Unit: %s DeviceType: %s" %(NWKID, EPout, Unit, DeviceType), NWKID)
        if DeviceType == 'LivoloSWL':
            livolo_OnOff( self, NWKID , EPout, 'Left', 'Off')
            UpdateDevice_v2(self, Devices, Unit, 0, "Off",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        elif DeviceType == 'LivoloSWR':
            livolo_OnOff( self, NWKID , EPout, 'Right', 'Off')
            UpdateDevice_v2(self, Devices, Unit, 0, "Off",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        elif DeviceType == 'ThermoModeEHZBRTS':
            loggingCommand( self, 'Debug', "MajDomoDevice EHZBRTS Schneider Thermostat Mode Off", NWKID )
            schneider_EHZBRTS_thermoMode( self, NWKID, 0 )
            UpdateDevice_v2(self, Devices, Unit, 0, "Off",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        elif DeviceType == 'BSO':
            from Modules.profalux import profalux_MoveWithOnOff
            profalux_MoveWithOnOff( self, NWKID, 0x00 )

        elif DeviceType == "WindowCovering":
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "01") # Blind inverted (On, for Close)

        elif DeviceType == "VenetianInverted":
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "01") # Venetian Inverted/Blind (On, for Close)

        elif DeviceType == "Venetian":
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "00") # Venetian /Blind (Off, for Close)
                
        elif DeviceType == "AlarmWD":
            Domoticz.Log("Alarm WarningDevice - value: %s" %Level)
            self.iaszonemgt.alarm_off( NWKID, EPout)

        else:
            if profalux: # Profalux are define as LvlControl but should be managed as Blind Inverted
                sendZigateCmd(self, "0081","02" + NWKID + ZIGATE_EP + EPout + '01' + '%02X' %0 + "0000")
            else:
                sendZigateCmd(self, "0092","02" + NWKID + ZIGATE_EP + EPout + "00")
        
            if 'Model' in self.ListOfDevices[NWKID]: # Making a trick for the GLEDOPTO LED STRIP.
                if self.ListOfDevices[NWKID]['Model'] == 'GLEDOPTO' and EPout == '0a':
                    # When switching off the WW channel, make sure to switch Off the RGB channel
                    sendZigateCmd(self, "0092","02" + NWKID + ZIGATE_EP + '0b' + "00")

        # Update Devices
        if Devices[Unit].SwitchType in (13,14,15,16):
            UpdateDevice_v2(self, Devices, Unit, 0, "0",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
        else :
            UpdateDevice_v2(self, Devices, Unit, 0, "Off",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)

    if Command == "On" :
        loggingCommand( self, 'Debug', "mgtCommand : On for Device: %s EPout: %s Unit: %s DeviceType: %s" %(NWKID, EPout, Unit, DeviceType), NWKID)

        if DeviceType == 'LivoloSWL':
            livolo_OnOff( self, NWKID , EPout, 'Left', 'On')
            UpdateDevice_v2(self, Devices, Unit, 1, "On",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        elif DeviceType == 'LivoloSWR':
            livolo_OnOff( self, NWKID , EPout, 'Right', 'On')
            UpdateDevice_v2(self, Devices, Unit, 1, "On",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        elif DeviceType == 'BSO':
            from Modules.profalux import profalux_MoveWithOnOff
            profalux_MoveWithOnOff( self, NWKID, 0x01 )

        elif DeviceType == "WindowCovering":
            # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "00") # Blind inverted (Off, for Open)

        elif DeviceType == "VenetianInverted":
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "00") # Venetian inverted/Blind (Off, for Open)

        elif DeviceType == "Venetian":
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + '01') # Venetian/Blind (On, for Open)

        else:
            if profalux:
                sendZigateCmd(self, "0081","02" + NWKID + ZIGATE_EP + EPout + '01' + '%02X' %255 + "0000")
            else:
                sendZigateCmd(self, "0092","02" + NWKID + ZIGATE_EP + EPout + "01")

        if Devices[Unit].SwitchType in (13,14,15,16):
            UpdateDevice_v2(self, Devices, Unit, 1, "100",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
        else:
            UpdateDevice_v2(self, Devices, Unit, 1, "On",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)

    if Command == "Set Level" :
        #Level is normally an integer but may be a floating point number if the Unit is linked to a thermostat device
        #There is too, move max level, mode = 00/01 for 0%/100%
        loggingCommand( self, 'Debug', "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
            %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
        
        if DeviceType == 'ThermoSetpoint':
            loggingCommand( self, 'Debug', "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
                %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            value = int(float(Level)*100)
            thermostat_Setpoint( self, NWKID, value )
            Level = round(float(Level),2)
            # Normalize SetPoint value with 2 digits
            Round = lambda x, n: eval('"%.' + str(int(n)) + 'f" % ' + repr(x))
            Level = Round( float(Level), 2 )
            UpdateDevice_v2(self, Devices, Unit, 0, str(Level),BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        if DeviceType == 'TempSetCurrent':
            loggingCommand( self, 'Debug', "mgtCommand : Set Temp for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
                %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            value = int(float(Level)*100)
            schneider_temp_Setcurrent( self, NWKID, value )
            Level = round(float(Level),2)
            # Normalize SetPoint value with 2 digits
            Round = lambda x, n: eval('"%.' + str(int(n)) + 'f" % ' + repr(x))
            Level = Round( float(Level), 2 )
            UpdateDevice_v2(self, Devices, Unit, 0, str(Level),BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        elif DeviceType == 'ThermoMode':
            loggingCommand( self, 'Log', "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
                %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            loggingCommand( self, 'Debug', "ThermoMode - requested Level: %s" %Level, NWKID)
            if Level in THERMOSTAT_LEVEL_2_MODE:
                loggingCommand( self, 'Debug', " - Set Thermostat Mode to : %s / %s" %( Level, THERMOSTAT_LEVEL_2_MODE[Level]), NWKID)
                thermostat_Mode( self, NWKID, THERMOSTAT_LEVEL_2_MODE[Level] )

        elif DeviceType == 'ThermoModeEHZBRTS':
            loggingCommand( self, 'Debug', "MajDomoDevice EHZBRTS Schneider Thermostat Mode %s" %Level, NWKID)
            schneider_EHZBRTS_thermoMode( self, NWKID, Level)
            UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        elif DeviceType == 'HACTMODE':
            loggingCommand( self, 'Debug', "mgtCommand : Set Level for HACT Mode: %s EPout: %s Unit: %s DeviceType: %s Level: %s" %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            if 'Schneider Wiser' not in self.ListOfDevices[NWKID]:
                self.ListOfDevices[NWKID]['Schneider Wiser'] ={}
            if Level == 10: # Conventional
                UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
                self.ListOfDevices[NWKID]['Schneider Wiser']['HACT Mode'] = 'conventionel'
                schneider_thermostat_behaviour( self, NWKID, 'conventionel')

            elif Level == 20: # setpoint
                UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
                self.ListOfDevices[NWKID]['Schneider Wiser']['HACT Mode'] = 'setpoint'
                schneider_thermostat_behaviour( self, NWKID, 'setpoint')

            elif Level == 30: # Fil Pilote
                UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
                self.ListOfDevices[NWKID]['Schneider Wiser']['HACT Mode'] = 'FIP'
                schneider_thermostat_behaviour( self, NWKID, 'FIP')

            else:
                Domoticz.Error("Unknown mode %s for HACTMODE for device %s" %( Level, NWKID))
            return

        elif DeviceType == 'ContractPower':
            loggingCommand( self, 'Debug', "mgtCommand : Set Level for ContractPower Mode: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
                %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            CONTRACT_MODE = {
                10: 3,
                20: 6,
                30: 9,
                40: 12,
                50: 15,
                }
            if 'Schneider Wiser' not in self.ListOfDevices[NWKID]:
                self.ListOfDevices[NWKID]['Schneider Wiser'] ={}
            if Level in CONTRACT_MODE:
                loggingCommand( self, 'Log', "mgtCommand : -----> Contract Power : %s - %s KVA" %(Level, CONTRACT_MODE[ Level ]), NWKID)
                if 'Model' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Model'] == 'EH-ZB-BMS':
                        self.ListOfDevices[NWKID]['Schneider Wiser']['Contract Power'] = CONTRACT_MODE[ Level ]
                        schneider_set_contract( self, NWKID, EPout, CONTRACT_MODE[ Level ] )
                        UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        elif DeviceType == 'FIP':
            FIL_PILOT_MODE = {
                10: 'Confort',
                20: 'Confort -1',
                30: 'Confort -2',
                40: 'Eco',
                50: 'Frost Protection',
                60: 'Off',
                }
            loggingCommand( self, 'Log', "mgtCommand : Set Level for FIP: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
                %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            if 'Schneider Wiser' not in self.ListOfDevices[NWKID]:
                self.ListOfDevices[NWKID]['Schneider Wiser'] ={}
            if Level in FIL_PILOT_MODE:
                loggingCommand( self, 'Log', "mgtCommand : -----> Fil Pilote mode: %s - %s" %(Level, FIL_PILOT_MODE[ Level ]), NWKID)
                if 'Model' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Model'] == 'EH-ZB-HACT':
                        self.ListOfDevices[NWKID]['Schneider Wiser']['HACT FIP Mode'] = FIL_PILOT_MODE[ Level ]
                        schneider_fip_mode( self, NWKID,  FIL_PILOT_MODE[ Level ] )
                        UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        elif DeviceType == 'LegrandFilPilote':
            FIL_PILOTE_MODE = {
                10: 'Confort',
                20: 'Confort -1',
                30: 'Confort -2',
                40: 'Eco',
                50: 'Hors Gel',
                60: 'Off',
                }

            loggingCommand( self, 'Log', "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
                %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            if Level in FIL_PILOTE_MODE:
                loggingCommand( self, 'Log', "mgtCommand : -----> Fil Pilote mode: %s - %s" %(Level, FIL_PILOTE_MODE[ Level ]), NWKID)
                legrand_fc40( self, FIL_PILOTE_MODE[ Level ])
                UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        elif DeviceType == 'BSO':
            from Modules.profalux import profalux_MoveToLiftAndTilt
            orientation = (Level * 90 ) // 100
            if orientation > 90: 
                orientation = 90
            profalux_MoveToLiftAndTilt( self, NWKID, tilt=orientation)

        elif DeviceType == "WindowCovering": # Blind Inverted
            if Level == 0:
                Level = 1
            elif Level >= 100:
                Level = 99
            value = '%02x' %Level
            loggingCommand( self, 'Debug', "WindowCovering - Lift Percentage Command - %s/%s Level: 0x%s %s" %(NWKID, EPout, value, Level), NWKID)
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "05" + value)

        elif DeviceType == "Venetian":
            if Level == 0:
                Level = 1
            elif Level >= 100:
                Level = 99
            value = '%02x' %Level
            loggingCommand( self, 'Debug', "Venetian blind - Lift Percentage Command - %s/%s Level: 0x%s %s" %(NWKID, EPout, value, Level), NWKID)
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "05" + value)

        elif DeviceType == "VenetianInverted":
            Level = 100 - Level
            if Level == 0:
                Level = 1
            elif Level >= 100:
                Level = 99
            value = '%02x' %Level
            loggingCommand( self, 'Debug', "VenetianInverted blind - Lift Percentage Command - %s/%s Level: 0x%s %s" %(NWKID, EPout, value, Level), NWKID)
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "05" + value)

        elif DeviceType == "AlarmWD":
            loggingCommand( self, 'Debug', "Alarm WarningDevice - value: %s" %Level)
            if Level == 0: # Stop
                self.iaszonemgt.alarm_off( NWKID, EPout)
            elif Level == 10: # Alarm
                self.iaszonemgt.alarm_on(  NWKID, EPout)
            elif Level == 20: # Siren
                self.iaszonemgt.siren_only( NWKID, EPout)
            elif Level == 30: # Strobe
                self.iaszonemgt.strobe_only( NWKID, EPout)
            elif Level == 40: # Armed - Squawk
                self.iaszonemgt.write_IAS_WD_Squawk( NWKID, EPout, 'armed')
            elif Level == 50: # Disarmed
                self.iaszonemgt.write_IAS_WD_Squawk( NWKID, EPout, 'disarmed')

        elif DeviceType == 'Toggle':
            loggingCommand( self, 'Debug', "Toggle switch - value: %s" %Level)
            if Level == 10: # Off
                actuators( self, NWKID, EPout, 'Off', 'Switch')
            elif Level == 20: # On
                actuators( self, NWKID, EPout, 'On', 'Switch')
            elif Level == 30: # Toggle
                actuators( self, NWKID, EPout, 'Toggle', 'Switch')

        else:
            OnOff = '01' # 00 = off, 01 = on
            if Level == 100: 
                value = 255
            elif Level == 0: 
                value = 0
            else:
                value = round( (Level*255)/100)
                if Level > 0 and value == 0: 
                    value = 1

            value=Hex_Format(2, value)
            if profalux:
                sendZigateCmd(self, "0081","02" + NWKID + ZIGATE_EP + EPout + OnOff + value + "0000")
            else:
                sendZigateCmd(self, "0081","02" + NWKID + ZIGATE_EP + EPout + OnOff + value + "0010")

        if Devices[Unit].SwitchType in (13,14,15,16):
            UpdateDevice_v2(self, Devices, Unit, 2, str(Level) ,BatteryLevel, SignalLevel) 
        else:
            # A bit hugly, but '1' instead of '2' is needed for the ColorSwitch dimmer to behave correctky
            UpdateDevice_v2(self, Devices, Unit, 1, str(Level) ,BatteryLevel, SignalLevel) 

    if Command == "Set Color" :
        loggingCommand( self, 'Debug', "mgtCommand : Set Color for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s Color: %s" %(NWKID, EPout, Unit, DeviceType, Level, Color), NWKID)
        Hue_List = json.loads(Color)
        loggingCommand( self, 'Debug', "-----> Hue_List: %s" %str(Hue_List), NWKID)

        #Color 
        #    ColorMode m;
        #    uint8_t t;     // Range:0..255, Color temperature (warm / cold ratio, 0 is coldest, 255 is warmest)
        #    uint8_t r;     // Range:0..255, Red level
        #    uint8_t g;     // Range:0..255, Green level
        #    uint8_t b;     // Range:0..255, Blue level
        #    uint8_t cw;    // Range:0..255, Cold white level
        #    uint8_t ww;    // Range:0..255, Warm white level (also used as level for monochrome white)
        #

        #First manage level
        if Hue_List['m'] != 9998:
            # In case of m ==3, we will do the Setlevel
            OnOff = '01' # 00 = off, 01 = on
            value=Hex_Format(2,round(1+Level*254/100)) #To prevent off state
            loggingCommand( self, 'Debug', "---------- Set Level: %s" %(value), NWKID)
            sendZigateCmd(self, "0081","02" + NWKID + ZIGATE_EP + EPout + OnOff + value + "0000")

        #Now color
        #ColorModeNone = 0   // Illegal
        #ColorModeNone = 1   // White. Valid fields: none
        if Hue_List['m'] == 1:
            ww = int(Hue_List['ww']) # Can be used as level for monochrome white
            #TODO : Jamais vu un device avec ca encore
            loggingCommand( self, 'Log', "Not implemented device color 1", NWKID)

        #ColorModeTemp = 2   // White with color temperature. Valid fields: t
        if Hue_List['m'] == 2:
            #Value is in mireds (not kelvin)
            #Correct values are from 153 (6500K) up to 588 (1700K)
            # t is 0 > 255
            TempKelvin = int(((255 - int(Hue_List['t']))*(6500-1700)/255)+1700)
            TempMired = 1000000 // TempKelvin
            loggingCommand( self, 'Debug', "---------- Set Temp Kelvin: %s-%s" %(TempMired, Hex_Format(4,TempMired)), NWKID)
            sendZigateCmd(self, "00C0","02" + NWKID + ZIGATE_EP + EPout + Hex_Format(4,TempMired) + "0000")

        #ColorModeRGB = 3    // Color. Valid fields: r, g, b.
        elif Hue_List['m'] == 3:
            x, y = rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
            #Convert 0>1 to 0>FFFF
            x = int(x*65536)
            y = int(y*65536)
            strxy = Hex_Format(4,x) + Hex_Format(4,y)
            loggingCommand( self, 'Debug', "---------- Set Temp X: %s Y: %s" %(x, y), NWKID)
            sendZigateCmd(self, "00B7","02" + NWKID + ZIGATE_EP + EPout + strxy + "0000")

        #ColorModeCustom = 4, // Custom (color + white). Valid fields: r, g, b, cw, ww, depending on device capabilities
        elif Hue_List['m'] == 4:
            #Gledopto GL_008
            # Color: {"b":43,"cw":27,"g":255,"m":4,"r":44,"t":227,"ww":215}
            loggingCommand( self, 'Log', "Not fully implemented device color 4", NWKID)

            # Process White color
            cw = int(Hue_List['cw'])   # 0 < cw < 255 Cold White
            ww = int(Hue_List['ww'])   # 0 < ww < 255 Warm White
            if cw != 0 and ww != 0:
                TempKelvin = int(((255 - int(ww))*(6500-1700)/255)+1700)
                TempMired = 1000000 // TempKelvin
                loggingCommand( self, 'Log', "---------- Set Temp Kelvin: %s-%s" %(TempMired, Hex_Format(4,TempMired)), NWKID)
                sendZigateCmd(self, "00C0","02" + NWKID + ZIGATE_EP + EPout + Hex_Format(4,TempMired) + "0000")
            else:
                # How to powerOff the WW/CW channel ?
                pass

            # Process Colour
            h,l,s = rgb_to_hsl((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
            saturation = s * 100   #0 > 100
            hue = h *360           #0 > 360
            hue = int(hue*254//360)
            saturation = int(saturation*254//100)
            loggingCommand( self, 'Log', "---------- Set Hue X: %s Saturation: %s" %(hue, saturation), NWKID)
            sendZigateCmd(self, "00B6","02" + NWKID + ZIGATE_EP + EPout + Hex_Format(2,hue) + Hex_Format(2,saturation) + "0000")

            value = int(l * 254//100)
            OnOff = '01'
            loggingCommand( self, 'Debug', "---------- Set Level: %s instead of Level: %s" %(value, Level), NWKID)
            #sendZigateCmd(self, "0081","02" + NWKID + ZIGATE_EP + EPout + OnOff + Hex_Format(2,value) + "0000")

        #With saturation and hue, not seen in domoticz but present on zigate, and some device need it
        elif Hue_List['m'] == 9998:
            h,l,s = rgb_to_hsl((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
            saturation = s * 100   #0 > 100
            hue = h *360           #0 > 360
            hue = int(hue*254//360)
            saturation = int(saturation*254//100)
            loggingCommand( self, 'Debug', "---------- Set Hue X: %s Saturation: %s" %(hue, saturation), NWKID)
            sendZigateCmd(self, "00B6","02" + NWKID + ZIGATE_EP + EPout + Hex_Format(2,hue) + Hex_Format(2,saturation) + "0000")

            value = int(l * 254//100)
            OnOff = '01'
            loggingCommand( self, 'Debug', "---------- Set Level: %s instead of Level: %s" %(value, Level), NWKID)
            sendZigateCmd(self, "0081","02" + NWKID + ZIGATE_EP + EPout + OnOff + Hex_Format(2,value) + "0000")

        #Update Device
        self.ListOfDevices[NWKID]['Heartbeat'] = 0  # Let's force a refresh of Attribute in the next Heartbeat
        UpdateDevice_v2(self, Devices, Unit, 1, str(Level) ,BatteryLevel, SignalLevel, str(Color))
