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

from Classes.LoggingManagement import LoggingManagement

from Modules.actuators import actuators
from Modules.tools import Hex_Format, rgb_to_xy, rgb_to_hsl
from Modules.basicOutputs import sendZigateCmd
from Modules.thermostats import thermostat_Setpoint, thermostat_Mode
from Modules.livolo import livolo_OnOff
from Modules.tuyaTRV import ( tuya_trv_mode , tuya_trv_onoff)
from Modules.tuyaSiren import ( tuya_siren_alarm, tuya_siren_humi_alarm, tuya_siren_temp_alarm )
from Modules.tuya import ( tuya_energy_onoff, tuya_dimmer_onoff, tuya_dimmer_dimmer, tuya_curtain_lvl, tuya_curtain_openclose, tuya_window_cover_calibration, tuya_switch_command, tuya_watertimer_command)

from Modules.legrand_netatmo import  legrand_fc40, cable_connected_mode
from Modules.schneider_wiser import schneider_EHZBRTS_thermoMode, schneider_hact_fip_mode, schneider_set_contract, schneider_temp_Setcurrent, schneider_hact_heater_type
from Modules.profalux import profalux_stop, profalux_MoveToLiftAndTilt
from Modules.domoTools import UpdateDevice_v2, RetreiveSignalLvlBattery, RetreiveWidgetTypeList
from Classes.IAS import IAS_Zone_Management
from Modules.zigateConsts import THERMOSTAT_LEVEL_2_MODE, ZIGATE_EP
from Modules.widgets import SWITCH_LVL_MATRIX
from Modules.cmdsDoorLock import cluster0101_lock_door, cluster0101_unlock_door
from Modules.fanControl import change_fan_mode

from Modules.casaia import casaia_swing_OnOff, casaia_setpoint, casaia_system_mode , casaia_ac201_fan_control

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
    ( 241,  6,  7): ('ColorControlRGBWZ',),
    ( 241,  1,  7): ('ColorControlRGBW', ),

    ( 244, 62, 18): ('Switch Selector',), 
    ( 244, 73,  0): ('Switch', '' 'LivoloSWL', 'LivoloSWR' , 'SwitchButton', 'Water', 'Plug'),
    ( 244, 73,  5): ('Smoke',),
    ( 244, 73,  7): ('LvlControl',),
    ( 244, 73,  9): ('Button',),
    ( 244, 73, 13): ('BSO',),
    ( 244, 73, 15): ('VenetianInverted', 'Venetian'),
    ( 244, 73, 16): ('BlindInverted','WindowCovering'),

}

ACTIONATORS = [ 'Switch', 'Plug', 'SwitchAQ2', 'Smoke', 'DSwitch', 'LivoloSWL', 'LivoloSWR', 'Toggle',
            'Venetian', 'VenetianInverted', 'WindowCovering', 'BSO', 'BSO-Orientation', 'BSO-Volet',
            'LvlControl', 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl', 'ColorControlRGBWZ', 'ColorControlRGBW',
            'ThermoSetpoint', 'ThermoMode', 'ACMode', 'ThermoMode_2', 'ThermoModeEHZBRTS', 'FanControl', 'PAC-SWITCH', 'ACMode_2', 'ACSwing','TempSetCurrent', 'AlarmWD',
            'FIP', 'HACTMODE','LegranCableMode', 'ContractPower','HeatingSwitch', 'DoorLock' , 'TuyaSiren', 'TuyaSirenHumi', 'TuyaSirenTemp', 'ThermoOnOff',
            'ShutterCalibration' ]
            
def mgtCommand( self, Devices, Unit, Command, Level, Color ):

    if Devices[Unit].DeviceID not in self.IEEE2NWK:
        Domoticz.Error("mgtCommand - something strange the Device %s DeviceID: %s Unknown" %(Devices[Unit].Name, Devices[Unit].DeviceID))
        return

    NWKID = self.IEEE2NWK[Devices[Unit].DeviceID]
    self.log.logging( "Command", 'Debug', "mgtCommand (%s) Devices[%s].Name: %s Command: %s Level: %s Color: %s" 
        %(NWKID, Unit , Devices[Unit].Name, Command, Level, Color ), NWKID)
  
    deviceType = Devices[Unit].Type
    deviceSubType = Devices[Unit].SubType
    deviceSwitchType = Devices[Unit].SwitchType

    if ( deviceType, deviceSubType, deviceSwitchType ) in DEVICE_SWITCH_MATRIX:
        domoticzType = DEVICE_SWITCH_MATRIX[ ( deviceType, deviceSubType, deviceSwitchType ) ] 
        self.log.logging( "Command", "Debug", "--------->   DeviceType: %s" %str( domoticzType ), NWKID)

    SignalLevel, BatteryLevel =  RetreiveSignalLvlBattery( self, NWKID)

    # Now we have to identify the Endpoint, DeviceType to be use for that command
    # inputs are : Device.ID
    # For each Ep of this Device we should find an entry ClusterType where is store Device.ID and DeviceType

    ClusterTypeList = RetreiveWidgetTypeList( self, Devices, NWKID, Unit )

    if len(ClusterTypeList) == 0 :    # No match with ClusterType
        # Should not happen. We didn't find any Widget references in the Device ClusterType!
        Domoticz.Error("mgtCommand - no ClusterType found !  "  +str(self.ListOfDevices[NWKID]) )
        return

    self.log.logging( "Command", 'Debug', "--------->1   ClusterType founds: %s for Unit: %s" %( ClusterTypeList, Unit), NWKID)

    actionable = False
    if len(ClusterTypeList) != 1:
        Domoticz.Error("mgtCommand - Not Expected. ClusterType: %s for NwkId: %s" %(ClusterTypeList,NWKID ))
        return

    if ClusterTypeList[0][0] == '00':
        EPout = '01'

    # One element found, we have Endpoint and DevicetypeÒ
    EPout , DeviceTypeWidgetId, DeviceType = ClusterTypeList[0]

    self.log.logging( "Command", "Debug", "--------->2   EPOut: %s DeviceType: %s WidgetID: %s" %( EPout , DeviceType, DeviceTypeWidgetId ), NWKID)
    # Sanity Check
    forceUpdateDev = False
    if DeviceType in SWITCH_LVL_MATRIX and 'ForceUpdate' in SWITCH_LVL_MATRIX[DeviceType ]:
        forceUpdateDev = SWITCH_LVL_MATRIX[DeviceType ]['ForceUpdate']
    self.log.logging( "Command", "Debug", "--------->3   forceUpdateDev: %s" %forceUpdateDev, NWKID)

    if DeviceType not in ACTIONATORS and not self.pluginconf.pluginConf['forcePassiveWidget']:
        self.log.logging( "Command", "Log", "mgtCommand - You are trying to action not allowed for Device: %s Type: %s and DeviceType: %s Command: %s Level:%s" 
                %( Devices[Unit].Name, ClusterTypeList, DeviceType , Command, Level), NWKID )
        return
    self.log.logging( "Command", "Debug", "--------->4   Ready to action", NWKID)

    profalux = False
    if 'Manufacturer' in self.ListOfDevices[NWKID]:
        profalux = ( self.ListOfDevices[NWKID]['Manufacturer'] == '1110' and self.ListOfDevices[NWKID]['ZDeviceID'] in ('0200', '0202') )
    self.log.logging( "Command", "Debug", "--------->5   profalux: %s" %profalux, NWKID)
    _model_name = ''
    if 'Model' in self.ListOfDevices[NWKID]:
        _model_name = self.ListOfDevices[NWKID]['Model']
    self.log.logging( "Command", "Debug", "--------->6   Model Name: %s" %_model_name, NWKID)

    # If Health is Not Reachable, let's give it a chance to be updated
    if 'Health' in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]['Health'] == 'Not Reachable':
            self.ListOfDevices[NWKID]['Health'] = ''
    self.log.logging( "Command", "Debug", "--------->7   Health: %s" %self.ListOfDevices[NWKID]['Health'], NWKID)

    if Command == 'Stop':  # Manage the Stop command. For known seen only on BSO and Windowcoering
        self.log.logging( "Command", 'Debug', "mgtCommand : Stop for Device: %s EPout: %s Unit: %s DeviceType: %s" %(NWKID, EPout, Unit, DeviceType), NWKID)

        if DeviceType == 'LvlControl' and _model_name == 'TS0601-curtain':
            tuya_curtain_openclose( self, NWKID, EPout, '01' )

        elif profalux:
            # Profalux offer a Manufacturer command to make Stop on Cluster 0x0008
            profalux_stop( self, NWKID)

        elif DeviceType in ( "WindowCovering", "VenetianInverted", "Venetian"):
            if _model_name == 'PR412':
                profalux_stop( self, NWKID)
            else:
                # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
                sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "02")
            UpdateDevice_v2(self, Devices, Unit, 17, "0", BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
        else:
            sendZigateCmd(self, "0083","02" + NWKID + ZIGATE_EP + EPout + "02")
                    
        # Let's force a refresh of Attribute in the next Heartbeat 
        self.ListOfDevices[NWKID]['Heartbeat'] = '0'  

    if Command == 'Off':  # Manage the Off command. 
        # Let's force a refresh of Attribute in the next Heartbeat  
        self.ListOfDevices[NWKID]['Heartbeat'] = '0'  

        self.log.logging( "Command", 'Debug', "mgtCommand : Off for Device: %s EPout: %s Unit: %s DeviceType: %s modelName: %s" %(
            NWKID, EPout, Unit, DeviceType, _model_name), NWKID)

        if _model_name in ('TS0601-switch', 'TS0601-2Gangs-switch', 'TS0601-2Gangs-switch'):
            self.log.logging( "Command", 'Debug', "mgtCommand : Off for Tuya Switches Gang/EPout: %s" %EPout)
            tuya_switch_command( self, NWKID, '00', gang=int(EPout,16))
            UpdateDevice_v2(self, Devices, Unit, 0, "Off",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        if _model_name == 'TS0601-Parkside-Watering-Timer':
            self.log.logging( "Command", 'Log', "mgtCommand : On for Tuya ParkSide Water Time" )
            if ( 'Param' in self.ListOfDevices[ NWKID ] 
                and 'TimerMode' in self.ListOfDevices[ NWKID ]['Param'] 
                and self.ListOfDevices[ NWKID ]['Param']['TimerMode']
            ):
                self.log.logging( "Command", 'Log', "mgtCommand : Off for Tuya ParkSide Water Time - Timer Mode" )
                tuya_watertimer_command( self, NWKID, '00', gang=int(EPout,16))
            else:
                self.log.logging( "Command", 'Log', "mgtCommand : Off for Tuya ParkSide Water Time - OnOff Mode" )
                sendZigateCmd(self, "0092","02" + NWKID + ZIGATE_EP + EPout + "00")

        if _model_name in ('TS0601-Energy', ):
            tuya_energy_onoff( self, NWKID, '00' )
            #UpdateDevice_v2(self, Devices, Unit, 0, "Off",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        if DeviceType == 'LivoloSWL':
            livolo_OnOff( self, NWKID , EPout, 'Left', 'Off')
            UpdateDevice_v2(self, Devices, Unit, 0, "Off",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
                        
            # Let's force a refresh of Attribute in the next Heartbeat 
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType == 'LivoloSWR':
            livolo_OnOff( self, NWKID , EPout, 'Right', 'Off')
            UpdateDevice_v2(self, Devices, Unit, 0, "Off",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
                        
            # Let's force a refresh of Attribute in the next Heartbeat 
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType == 'DoorLock':
            # Widget Doorlock seems to work in the oposit
            cluster0101_unlock_door( self, NWKID)
            UpdateDevice_v2(self, Devices, Unit, 0, "Closed",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            self.ListOfDevices[NWKID]['Heartbeat'] = '0' 
            return

        if DeviceType in ( 'ThermoMode', 'ACMode'):
            self.log.logging( "Command", 'Debug', "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
                %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            
            self.log.logging( "Command", 'Debug', "ThermoMode - requested Level: %s" %Level, NWKID)
            self.log.logging( "Command", 'Debug', " - Set Thermostat Mode to : %s / %s" %( Level, THERMOSTAT_LEVEL_2_MODE[Level]), NWKID)
            thermostat_Mode( self, NWKID, 'Off' )
            UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)

            # Let's force a refresh of Attribute in the next Heartbeat  
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType == 'ThermoMode_2':
            self.log.logging( "Command", 'Debug', "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
                %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            self.log.logging( "Command", 'Debug', "ThermoMode - requested Level: %s" %Level, NWKID)
            tuya_trv_mode( self, NWKID, 0 )
            UpdateDevice_v2(self, Devices, Unit, 0, 'Off',BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        if DeviceType == 'ThermoModeEHZBRTS':
            self.log.logging( "Command", 'Debug', "MajDomoDevice EHZBRTS Schneider Thermostat Mode Off", NWKID )
            schneider_EHZBRTS_thermoMode( self, NWKID, 0 )
            UpdateDevice_v2(self, Devices, Unit, 0, "Off",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            # Let's force a refresh of Attribute in the next Heartbeat 
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType in ( 'ACMode_2', 'FanControl') :
            casaia_system_mode( self, NWKID, 'Off')
            
            #UpdateDevice_v2(self, Devices, Unit, 0, "Off",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            ## Let's force a refresh of Attribute in the next Heartbeat  
            #self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType == 'ACSwing':
            if 'Model' in self.ListOfDevices[ NWKID ] and self.ListOfDevices[ NWKID ]['Model'] == 'AC201A':
                casaia_swing_OnOff( self, NWKID, '00')
                UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
                return

        if DeviceType == 'LvlControl' and _model_name == 'TS0601-dimmer':
            tuya_dimmer_onoff( self, NWKID, EPout, '00' )
            UpdateDevice_v2(self, Devices, Unit, 0, Devices[Unit].sValue,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        if DeviceType == 'LvlControl' and _model_name == 'TS0601-curtain':
            tuya_curtain_openclose( self, NWKID, '02' )

        elif DeviceType == 'BSO-Volet' and profalux:
            profalux_MoveToLiftAndTilt( self, NWKID, level=1 )

        elif DeviceType == "TuyaSiren":
            tuya_siren_alarm( self, NWKID, 0x00)

        elif DeviceType == "TuyaSirenHumi":
            tuya_siren_humi_alarm( self, NWKID, 0x00 )
        
        elif DeviceType == "TuyaSirenTemp":
            tuya_siren_temp_alarm( self, NWKID, 0x00 )

        elif DeviceType == "WindowCovering":
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "01") # Blind inverted (On, for Close)

        elif DeviceType == "VenetianInverted":
            if 'Model' in self.ListOfDevices[NWKID] and self.ListOfDevices[ NWKID ]['Model'] == 'PR412':
                sendZigateCmd(self, "0092","02" + NWKID + ZIGATE_EP + EPout + "01")
            else:
                sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "01") # Venetian Inverted/Blind (On, for Close)

        elif DeviceType == "Venetian":
            if 'Model' in self.ListOfDevices[NWKID] and self.ListOfDevices[ NWKID ]['Model'] == 'PR412':
                sendZigateCmd(self, "0092","02" + NWKID + ZIGATE_EP + EPout + "00")
            else:
                sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "00") # Venetian /Blind (Off, for Close)
                
        elif DeviceType == "AlarmWD":
            self.iaszonemgt.alarm_off( NWKID, EPout)

        elif DeviceType == "HeatingSwitch":
            thermostat_Mode( self, NWKID, 'Off' )

        elif DeviceType == 'ThermoOnOff':
            self.log.logging( "Command", 'Debug', "ThermoOnOff - requested Off", NWKID)
            tuya_trv_onoff( self, NWKID, 0x00)
            UpdateDevice_v2(self, Devices, Unit, 0, 'Off',BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)

        elif DeviceType == 'ShutterCalibration':
            self.log.logging( "Command", 'Debug', "mgtCommand : Disable Window Cover Calibration" )
            tuya_window_cover_calibration( self, NWKID, '00')

        else:
            # Remaining Slider widget
            if profalux: # Profalux are define as LvlControl but should be managed as Blind Inverted
                sendZigateCmd(self, "0081","02" + NWKID + ZIGATE_EP + EPout + '01' + '%02X' %0 + "0000")
            else:
                if ( 'Param' in self.ListOfDevices[ NWKID ] and 
                        'fadingOff' in self.ListOfDevices[ NWKID ]['Param'] and 
                        self.ListOfDevices[ NWKID ]['Param']['fadingOff']
                    ):
                    effect = '0000'
                    if self.ListOfDevices[ NWKID ]['Param']['fadingOff'] == 1:
                        effect = '0002' # 50% dim down in 0.8 seconds then fade to off in 12 seconds
                    elif self.ListOfDevices[ NWKID ]['Param']['fadingOff'] == 2:
                        effect = '0100' # 20% dim up in 0.5s then fade to off in 1 second
                    elif self.ListOfDevices[ NWKID ]['Param']['fadingOff'] == 255:
                        effect = '0001' # No fade

                    self.log.logging( "Command", 'Debug', "mgtCommand : %s fading Off effect: %s" %(NWKID, effect))
                    # Increase brightness by 20% (if possible) in 0.5 seconds then fade to off in 1 second (default)
                    sendZigateCmd(self, "0094","02" + NWKID + ZIGATE_EP + EPout + effect )
                else:
                    sendZigateCmd(self, "0092","02" + NWKID + ZIGATE_EP + EPout + "00")
        
            # Making a trick for the GLEDOPTO LED STRIP.
            if _model_name == 'GLEDOPTO' and EPout == '0a':
                # When switching off the WW channel, make sure to switch Off the RGB channel
                sendZigateCmd(self, "0092","02" + NWKID + ZIGATE_EP + '0b' + "00")

        # Update Devices
        if Devices[Unit].SwitchType in (13,14,15,16):
            UpdateDevice_v2(self, Devices, Unit, 0, "0",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
        else :
            UpdateDevice_v2(self, Devices, Unit, 0, "Off",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
                    
        # Let's force a refresh of Attribute in the next Heartbeat 
        self.ListOfDevices[NWKID]['Heartbeat'] = '0'  

    if Command == 'On':   # Manage the On command.
        # Let's force a refresh of Attribute in the next Heartbeat  
        self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
        self.log.logging( "Command", 'Debug', "mgtCommand : On for Device: %s EPout: %s Unit: %s DeviceType: %s ModelName: %s" %(
            NWKID, EPout, Unit, DeviceType, _model_name), NWKID)

        if _model_name in ('TS0601-switch', 'TS0601-2Gangs-switch', 'TS0601-2Gangs-switch',):
            self.log.logging( "Command", 'Debug', "mgtCommand : On for Tuya Switches Gang/EPout: %s" %EPout)
                
            tuya_switch_command( self, NWKID, '01', gang=int(EPout,16))
            UpdateDevice_v2(self, Devices, Unit, 1, "On",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        if _model_name == 'TS0601-Parkside-Watering-Timer':
            self.log.logging( "Command", 'Debug', "mgtCommand : On for Tuya ParkSide Water Time" )
            if ( 'Param' in self.ListOfDevices[ NWKID ] 
                and 'TimerMode' in self.ListOfDevices[ NWKID ]['Param'] 
                and self.ListOfDevices[ NWKID ]['Param']['TimerMode']
            ):
                self.log.logging( "Command", 'Log', "mgtCommand : On for Tuya ParkSide Water Time - Timer Mode" )
                tuya_watertimer_command( self, NWKID, '01', gang=int(EPout,16))
            else:
                self.log.logging( "Command", 'Log', "mgtCommand : On for Tuya ParkSide Water Time - OnOff Mode" )
                sendZigateCmd(self, "0092","02" + NWKID + ZIGATE_EP + EPout + "01")

        if _model_name in ('TS0601-Energy', ):
            tuya_energy_onoff( self, NWKID, '01' )
            #UpdateDevice_v2(self, Devices, Unit, 1, "On",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        if DeviceType == 'LivoloSWL':
            livolo_OnOff( self, NWKID , EPout, 'Left', 'On')
            UpdateDevice_v2(self, Devices, Unit, 1, "On",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)                      
            # Let's force a refresh of Attribute in the next Heartbeat 
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType == 'LivoloSWR':
            livolo_OnOff( self, NWKID , EPout, 'Right', 'On')
            UpdateDevice_v2(self, Devices, Unit, 1, "On",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            # Let's force a refresh of Attribute in the next Heartbeat 
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType == 'DoorLock':
            cluster0101_lock_door( self, NWKID)
            UpdateDevice_v2(self, Devices, Unit, 1, "Open",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            self.ListOfDevices[NWKID]['Heartbeat'] = 0 
            return
            
        if DeviceType == 'LvlControl' and _model_name == 'TS0601-dimmer':
            tuya_dimmer_onoff( self, NWKID, EPout, '01' )
            UpdateDevice_v2(self, Devices, Unit, 1, Devices[Unit].sValue,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        if DeviceType == 'LvlControl' and _model_name == 'TS0601-curtain':
            tuya_curtain_openclose( self, NWKID, '00' )

        elif DeviceType == 'BSO-Volet' and profalux:
            # On translated into a Move to 254
            profalux_MoveToLiftAndTilt( self, NWKID, level=255 )

        elif DeviceType == "WindowCovering":
            # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "00") # Blind inverted (Off, for Open)

        elif DeviceType == "VenetianInverted":
            if 'Model' in self.ListOfDevices[NWKID] and self.ListOfDevices[ NWKID ]['Model'] == 'PR412':
                sendZigateCmd(self, "0092","02" + NWKID + ZIGATE_EP + EPout + "00")
            else:
                sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "00") # Venetian inverted/Blind (Off, for Open)

        elif DeviceType == "Venetian":
            if 'Model' in self.ListOfDevices[NWKID] and self.ListOfDevices[ NWKID ]['Model'] == 'PR412':
                sendZigateCmd(self, "0092","02" + NWKID + ZIGATE_EP + EPout + "01")
            else:
                sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + '01') # Venetian/Blind (On, for Open)

        elif DeviceType == "HeatingSwitch":
            thermostat_Mode( self, NWKID, 'Heat' )

        elif DeviceType == 'ThermoOnOff':
            tuya_trv_onoff( self, NWKID, 0X01)
            UpdateDevice_v2(self, Devices, Unit, 1, 'On',BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)

        elif DeviceType == 'ShutterCalibration':
            self.log.logging( "Command", 'Debug', "mgtCommand : Enable Window Cover Calibration" )
            tuya_window_cover_calibration( self, NWKID, '01')

        else:
            # Remaining Slider widget
            if profalux:
                sendZigateCmd(self, "0081","02" + NWKID + ZIGATE_EP + EPout + '01' + '%02X' %255 + "0000")
            else:
                sendZigateCmd(self, "0092","02" + NWKID + ZIGATE_EP + EPout + "01")

        if Devices[Unit].SwitchType in (13,14,15,16):
            UpdateDevice_v2(self, Devices, Unit, 1, "100",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
        else:
            UpdateDevice_v2(self, Devices, Unit, 1, "On",BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)

        # Let's force a refresh of Attribute in the next Heartbeat  
        self.ListOfDevices[NWKID]['Heartbeat'] = '0'  

    if Command == 'Set Level':
        #Level is normally an integer but may be a floating point number if the Unit is linked to a thermostat device
        #There is too, move max level, mode = 00/01 for 0%/100%
        self.log.logging( "Command", 'Debug', "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
            %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
        
        if DeviceType == 'ThermoSetpoint':
            self.log.logging( "Command", 'Debug', "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
                %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            value = int(float(Level)*100)
            thermostat_Setpoint( self, NWKID, value )
            Level = round(float(Level),2)
            # Normalize SetPoint value with 2 digits
            Round = lambda x, n: eval('"%.' + str(int(n)) + 'f" % ' + repr(x))
            Level = Round( float(Level), 2 )
            UpdateDevice_v2(self, Devices, Unit, 0, str(Level),BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)

            # Let's force a refresh of Attribute in the next Heartbeat  
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType == 'TempSetCurrent':
            self.log.logging( "Command", 'Debug', "mgtCommand : Set Temp for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
                %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            value = int(float(Level)*100)
            schneider_temp_Setcurrent( self, NWKID, value )
            Level = round(float(Level),2)
            # Normalize SetPoint value with 2 digits
            Round = lambda x, n: eval('"%.' + str(int(n)) + 'f" % ' + repr(x))
            Level = Round( float(Level), 2 )
            UpdateDevice_v2(self, Devices, Unit, 0, str(Level),BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)

            # Let's force a refresh of Attribute in the next Heartbeat  
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType == 'ThermoModeEHZBRTS':
            self.log.logging( "Command", 'Debug', "MajDomoDevice EHZBRTS Schneider Thermostat Mode %s" %Level, NWKID)
            schneider_EHZBRTS_thermoMode( self, NWKID, Level)
            UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)

            # Let's force a refresh of Attribute in the next Heartbeat  
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType == 'HACTMODE':
            self.log.logging( "Command", 'Debug', "mgtCommand : Set Level for HACT Mode: %s EPout: %s Unit: %s DeviceType: %s Level: %s" %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            if 'Schneider Wiser' not in self.ListOfDevices[NWKID]:
                self.ListOfDevices[NWKID]['Schneider Wiser'] ={}

            if 'HACT Mode' not in self.ListOfDevices[NWKID]['Schneider Wiser']:
                self.ListOfDevices[NWKID]['Schneider Wiser']['HACT Mode'] = ''

            if Level == 10: # Conventional
                UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
                self.ListOfDevices[NWKID]['Schneider Wiser']['HACT Mode'] = 'conventional'
                schneider_hact_heater_type( self, NWKID, 'conventional')

            elif Level == 20: # fip
                UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
                self.ListOfDevices[NWKID]['Schneider Wiser']['HACT Mode'] = 'FIP'
                schneider_hact_heater_type( self, NWKID, 'fip')

            else:
                Domoticz.Error("Unknown mode %s for HACTMODE for device %s" %( Level, NWKID))

            # Let's force a refresh of Attribute in the next Heartbeat  
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType == 'LegranCableMode':
            self.log.logging( "Command", 'Debug', "mgtCommand : Set Level for Legrand Cable Mode: %s EPout: %s Unit: %s DeviceType: %s Level: %s" %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            cable_connected_mode( self, NWKID, str(Level) )
            UpdateDevice_v2(self, Devices, Unit, int(Level), Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType == 'ContractPower':
            self.log.logging( "Command", 'Debug', "mgtCommand : Set Level for ContractPower Mode: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
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
                self.log.logging( "Command", 'Log', "mgtCommand : -----> Contract Power : %s - %s KVA" %(Level, CONTRACT_MODE[ Level ]), NWKID)
                if 'Model' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Model'] == 'EH-ZB-BMS':
                        self.ListOfDevices[NWKID]['Schneider Wiser']['Contract Power'] = CONTRACT_MODE[ Level ]
                        schneider_set_contract( self, NWKID, EPout, CONTRACT_MODE[ Level ] )
                        UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)

            # Let's force a refresh of Attribute in the next Heartbeat  
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType == 'FIP':
            FIL_PILOT_MODE = {
                10: 'Confort',
                20: 'Confort -1',
                30: 'Confort -2',
                40: 'Eco',
                50: 'Frost Protection',
                60: 'Off',
                }
            self.log.logging( "Command", 'Debug', "mgtCommand : Set Level for FIP: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
                %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            if 'Schneider Wiser' not in self.ListOfDevices[NWKID]:
                self.ListOfDevices[NWKID]['Schneider Wiser'] ={}

            if Level in FIL_PILOT_MODE:
                
                if 'Model' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Model'] == 'EH-ZB-HACT':
                        self.log.logging( "Command", 'Debug', "mgtCommand : -----> HACT -> Fil Pilote mode: %s - %s" %(Level, FIL_PILOT_MODE[ Level ]), NWKID)
                        self.ListOfDevices[NWKID]['Schneider Wiser']['HACT FIP Mode'] = FIL_PILOT_MODE[ Level ]
                        schneider_hact_fip_mode( self, NWKID,  FIL_PILOT_MODE[ Level ] )
                        UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)

                    elif self.ListOfDevices[NWKID]['Model'] == 'Cable outlet':
                        self.log.logging( "Command", 'Debug', "mgtCommand : -----> Fil Pilote mode: %s - %s" %(Level, FIL_PILOT_MODE[ Level ]), NWKID)
                        legrand_fc40( self, NWKID, FIL_PILOT_MODE[ Level ])
                        UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)


            # Let's force a refresh of Attribute in the next Heartbeat  
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType in  ('ThermoMode', ):
            self.log.logging( "Command", 'Debug', "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
                %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            self.log.logging( "Command", 'Debug', "ThermoMode - requested Level: %s" %Level, NWKID)
            if Level in THERMOSTAT_LEVEL_2_MODE:
                self.log.logging( "Command", 'Debug', " - Set Thermostat Mode to : %s / %s" %( Level, THERMOSTAT_LEVEL_2_MODE[Level]), NWKID)
                thermostat_Mode( self, NWKID, THERMOSTAT_LEVEL_2_MODE[Level] )
                UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            # Let's force a refresh of Attribute in the next Heartbeat  
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType == 'ACMode':
            ACLEVEL_TO_MODE = {
                0: 'Off',
                10: 'Cool',
                20: 'Heat',
                30: 'Dry',
                40: 'Fan Only',

            }
            self.log.logging( "Command", 'Debug', "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
                %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            self.log.logging( "Command", 'Debug', "ThermoMode - requested Level: %s" %Level, NWKID)
            if Level in ACLEVEL_TO_MODE:
                self.log.logging( "Command", 'Debug', " - Set Thermostat Mode to : %s / %s" %( Level, ACLEVEL_TO_MODE[Level]), NWKID)
                thermostat_Mode( self, NWKID, ACLEVEL_TO_MODE[Level] )
                UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            # Let's force a refresh of Attribute in the next Heartbeat  
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  
            return

        if DeviceType == 'ThermoMode_2':
            self.log.logging( "Command", 'Debug', "mgtCommand : Set Level for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s" 
                %(NWKID, EPout, Unit, DeviceType, Level), NWKID)
            self.log.logging( "Command", 'Debug', "ThermoMode_2 - requested Level: %s" %Level, NWKID)
            tuya_trv_mode( self, NWKID, Level )
            UpdateDevice_v2(self, Devices, Unit, int(Level//10), Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        if DeviceType == 'FanControl':

            if 'Model' in self.ListOfDevices[ NWKID ] and self.ListOfDevices[ NWKID ]['Model'] == 'AC201A':
                casaia_ac201_fan_control( self, NWKID, Level)
                return

            FAN_MODE = {
                0: 'Off',
                20: 'Low',
                30: 'Medium',
                40: 'High',
                10: 'Auto',
            }

            if Level in FAN_MODE:
                change_fan_mode( self, NWKID, EPout, FAN_MODE[ Level ])
            self.ListOfDevices[NWKID]['Heartbeat'] = '0' 

        if DeviceType == 'ACSwing':
            if Level == 10:
                casaia_swing_OnOff( self, NWKID, '01')
                #UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        if DeviceType == 'ACMode_2':
            if Level == 10:
                casaia_system_mode( self, NWKID, 'Cool')
                #UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            elif Level == 20:
                casaia_system_mode( self, NWKID, 'Heat')
                #UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            elif Level == 30:
                casaia_system_mode( self, NWKID, 'Dry')
                #UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            elif Level == 40:
                casaia_system_mode( self, NWKID, 'Fan')
                #UpdateDevice_v2(self, Devices, Unit, int(Level)//10, Level,BatteryLevel, SignalLevel,  ForceUpdate_=forceUpdateDev)
            return

        if DeviceType == 'BSO-Volet':
            if profalux:
                # Transform slider % into analog value
                lift = ( 255 * Level ) // 100
                if Level == 0:
                    lift = 1
                elif Level > 255:
                    lift = 255
                
                self.log.logging( "Command", 'Log', "mgtCommand : profalux_MoveToLiftAndTilt: %s BSO-Volet Lift: Level:%s Lift: %s" %(NWKID, Level, lift), NWKID)
                profalux_MoveToLiftAndTilt( self, NWKID, level=lift)

        elif DeviceType == 'BSO-Orientation':
             if profalux:
                Tilt = Level - 10
                self.log.logging( "Command", 'Log', "mgtCommand : profalux_MoveToLiftAndTilt:  %s BSO-Orientation : Level: %s Tilt: %s" %(NWKID, Level, Tilt), NWKID)
                profalux_MoveToLiftAndTilt( self, NWKID, tilt=Tilt)           

        elif DeviceType == "WindowCovering": # Blind Inverted
            if Level == 0:
                Level = 1
            elif Level >= 100:
                Level = 99
            value = '%02x' %Level
            self.log.logging( "Command", 'Debug', "WindowCovering - Lift Percentage Command - %s/%s Level: 0x%s %s" %(NWKID, EPout, value, Level), NWKID)
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "05" + value)

        elif DeviceType == "Venetian":
            if Level == 0:
                Level = 1
            elif Level >= 100:
                Level = 99
            value = '%02x' %Level
            self.log.logging( "Command", 'Debug', "Venetian blind - Lift Percentage Command - %s/%s Level: 0x%s %s" %(NWKID, EPout, value, Level), NWKID)
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "05" + value)

        elif DeviceType == "VenetianInverted":
            Level = 100 - Level
            if Level == 0:
                Level = 1
            elif Level >= 100:
                Level = 99
            value = '%02x' %Level
            self.log.logging( "Command", 'Debug', "VenetianInverted blind - Lift Percentage Command - %s/%s Level: 0x%s %s" %(NWKID, EPout, value, Level), NWKID)
            sendZigateCmd(self, "00FA","02" + NWKID + ZIGATE_EP + EPout + "05" + value)

        elif DeviceType == "AlarmWD":
            self.log.logging( "Command", 'Debug', "Alarm WarningDevice - value: %s" %Level)
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

        elif DeviceType == "TuyaSiren":
            if Level == 10:
                tuya_siren_alarm( self, NWKID, 0x01, 1)
            elif Level == 20:
                tuya_siren_alarm( self, NWKID, 0x01, 2)
            elif Level == 30:
                tuya_siren_alarm( self, NWKID, 0x01, 3)
            elif Level == 40:
                tuya_siren_alarm( self, NWKID, 0x01, 4)
            elif Level == 50:
                tuya_siren_alarm( self, NWKID, 0x01, 5)

        elif DeviceType == "TuyaSirenHumi":
            if Level == 10:
                tuya_siren_humi_alarm( self, NWKID, 0x01 )
        
        elif DeviceType == "TuyaSirenTemp":
            if Level == 10:
                tuya_siren_temp_alarm( self, NWKID, 0x01 )

        elif DeviceType == 'Toggle':
            self.log.logging( "Command", 'Debug', "Toggle switch - value: %s" %Level)
            if Level == 10: # Off
                actuators( self, NWKID, EPout, 'Off', 'Switch')
            elif Level == 20: # On
                actuators( self, NWKID, EPout, 'On', 'Switch')
            elif Level == 30: # Toggle
                actuators( self, NWKID, EPout, 'Toggle', 'Switch')

        elif _model_name == 'TS0601-dimmer':
            if Devices[Unit].nValue == 0:
                tuya_dimmer_onoff( self, NWKID, EPout, '01' )
            if Level < 1:
                # Never Switch off
                Level = 1
            tuya_dimmer_dimmer( self, NWKID, EPout, Level )

        elif _model_name == 'TS0601-curtain':
            tuya_curtain_lvl(self, NWKID, (Level))

        else:
            # Remaining Slider widget
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
                transitionMoveLevel = '0010' # Compatibility. It was 0010 before
                if 'Param' in self.ListOfDevices[ NWKID ] and 'moveToLevel' in self.ListOfDevices[ NWKID ]['Param']:
                    transitionMoveLevel = '%04x' %int(self.ListOfDevices[ NWKID ]['Param']['moveToLevel'])
                sendZigateCmd(self, "0081","02" + NWKID + ZIGATE_EP + EPout + OnOff + value + transitionMoveLevel)

        if Devices[Unit].SwitchType in (13,16):
            UpdateDevice_v2(self, Devices, Unit, 2, str(Level) ,BatteryLevel, SignalLevel) 

        elif Devices[Unit].SwitchType in ( 14, 15 ):
            if Level == 0:
                UpdateDevice_v2(self, Devices, Unit, 0, '0', BatteryLevel, SignalLevel)
            elif Level == 100:
                UpdateDevice_v2(self, Devices, Unit, 1, '1', BatteryLevel, SignalLevel)
            elif Level == 50:
                UpdateDevice_v2(self, Devices, Unit, 17, '0',BatteryLevel, SignalLevel)
            else:
                UpdateDevice_v2(self, Devices, Unit, 2, str(Level),BatteryLevel, SignalLevel)

        else:
            # A bit hugly, but '1' instead of '2' is needed for the ColorSwitch dimmer to behave correctky
            UpdateDevice_v2(self, Devices, Unit, 1, str(Level) ,BatteryLevel, SignalLevel)

        # Let's force a refresh of Attribute in the next Heartbeat  
        self.ListOfDevices[NWKID]['Heartbeat'] = '0'  

    if Command == 'Set Color':
        # RGBW --> Action on W Level (bri) setcolbrightnessvalue: ID: d9, bri: 96, color: '{m: 3, RGB: ffffff, CWWW: 0000, CT: 0}'
        #      --> Action on RGB (RGB)     setcolbrightnessvalue: ID: d9, bri: 59, color: '{m: 3, RGB: 53ff42, CWWW: 0000, CT: 0}'

        self.log.logging( "Command", 'Debug', "mgtCommand : Set Color for Device: %s EPout: %s Unit: %s DeviceType: %s Level: %s Color: %s" %(NWKID, EPout, Unit, DeviceType, Level, Color), NWKID)
        Hue_List = json.loads(Color)
        self.log.logging( "Command", 'Debug', "-----> Hue_List: %s" %str(Hue_List), NWKID)

        #Color 
        #    ColorMode m;
        #    uint8_t t;     // Range:0..255, Color temperature (warm / cold ratio, 0 is coldest, 255 is warmest)
        #    uint8_t r;     // Range:0..255, Red level
        #    uint8_t g;     // Range:0..255, Green level
        #    uint8_t b;     // Range:0..255, Blue level
        #    uint8_t cw;    // Range:0..255, Cold white level
        #    uint8_t ww;    // Range:0..255, Warm white level (also used as level for monochrome white)
        #
        #  transitionRGB = '%04x' %self.pluginconf.pluginConf['moveToColourRGB']
        #  transitionMoveLevel = '%04x' %self.pluginconf.pluginConf['moveToLevel']
        #  transitionHue = '%04x' %self.pluginconf.pluginConf['moveToHueSatu']
        #  transitionTemp = '%04x' %self.pluginconf.pluginConf['moveToColourTemp']
        transitionMoveLevel = transitionRGB = transitionMoveLevel = transitionHue = transitionTemp = '0000'
        if 'Param' in self.ListOfDevices[ NWKID ]:
            if 'moveToColourTemp' in self.ListOfDevices[ NWKID ]['Param']:
                transitionTemp = '%04x' %int(self.ListOfDevices[ NWKID ]['Param']['moveToColourTemp'])
            if 'moveToColourRGB' in self.ListOfDevices[ NWKID ]['Param']:
                transitionRGB = '%04x' %int(self.ListOfDevices[ NWKID ]['Param']['moveToColourRGB'])
            if 'moveToLevel' in self.ListOfDevices[ NWKID ]['Param']:
                transitionMoveLevel = '%04x' %int(self.ListOfDevices[ NWKID ]['Param']['moveToLevel'])
            if 'moveToHueSatu' in self.ListOfDevices[ NWKID ]['Param']:
                transitionHue = '%04x' %int(self.ListOfDevices[ NWKID ]['Param']['moveToHueSatu'])

        self.log.logging( "Command", 'Debug', "-----> Transition Timers: %s %s %s %s" %( 
            transitionRGB, transitionMoveLevel, transitionHue, transitionTemp))
        
        #manage_level = False
        #if 'Model' in self.ListOfDevices[ NWKID ] and self.ListOfDevices[ NWKID ]['Model'] == 'GL-C-007-2ID':
        #    # We have to manage Level independtly of RGB and force EpOut to 0f
        #    EPout = '0f'
        #    manage_level = True

        #First manage level
        #if Hue_List['m'] or Hue_List['m'] != 9998 or manage_level:
        if Hue_List['m'] or Hue_List['m'] != 9998:
            OnOff = '01' # 00 = off, 01 = on
            value=Hex_Format(2,round(1+Level*254/100)) #To prevent off state
            self.log.logging( "Command", 'Debug', "---------- Set Level: %s" %(value), NWKID)
            # u16TransitionTime is the time taken, in units of tenths of a second, to reach the target level 
            # (0xFFFF means use the u16OnOffTransitionTime attribute instead
            transitionONOFF = 'ffff' 
            sendZigateCmd(self, "0081","02" + NWKID + ZIGATE_EP + EPout + OnOff + value + transitionMoveLevel)
            # Let's force a refresh of Attribute in the next Heartbeat  
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  

        #Now colorgrep 
        #ColorModeNone = 0   // Illegal
        #ColorModeNone = 1   // White. Valid fields: none

        #if Hue_List['m'] == 1:
        #    ww = int(Hue_List['ww']) # Can be used as level for monochrome white
        #    #TODO : Jamais vu un device avec ca encore
        #    self.log.logging( "Command", 'Log', "Not implemented device color 1", NWKID)

        #ColorModeTemp = 2   // White with color temperature. Valid fields: t
        if Hue_List['m'] == 2:
            #Value is in mireds (not kelvin)
            #Correct values are from 153 (6500K) up to 588 (1700K)
            # t is 0 > 255
            TempKelvin = int(((255 - int(Hue_List['t']))*(6500-1700)/255)+1700)
            TempMired = 1000000 // TempKelvin
            self.log.logging( "Command", 'Debug', "---------- Set Temp Kelvin: %s-%s" %(TempMired, Hex_Format(4,TempMired)), NWKID)
            #u16TransitionTime is the time period, in tenths of a second, over which the change in hue should be implemented

            sendZigateCmd(self, "00C0","02" + NWKID + ZIGATE_EP + EPout + Hex_Format(4,TempMired) + transitionTemp)

        #ColorModeRGB = 3    // Color. Valid fields: r, g, b.
        elif Hue_List['m'] == 3:
            x, y = rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
            #Convert 0>1 to 0>FFFF
            x = int(x*65536)
            y = int(y*65536)
            strxy = Hex_Format(4,x) + Hex_Format(4,y)
            self.log.logging( "Command", 'Debug', "---------- Set Temp X: %s Y: %s" %(x, y), NWKID)
            sendZigateCmd(self, "00B7","02" + NWKID + ZIGATE_EP + EPout + strxy + transitionRGB)

        #ColorModeCustom = 4, // Custom (color + white). Valid fields: r, g, b, cw, ww, depending on device capabilities
        elif Hue_List['m'] == 4:
            #Gledopto GL_008
            # Color: {"b":43,"cw":27,"g":255,"m":4,"r":44,"t":227,"ww":215}
            self.log.logging( "Command", 'Log', "Not fully implemented device color 4", NWKID)

            # Process White color
            cw = int(Hue_List['cw'])   # 0 < cw < 255 Cold White
            ww = int(Hue_List['ww'])   # 0 < ww < 255 Warm White
            if cw != 0 and ww != 0:
                TempKelvin = int(((255 - int(ww))*(6500-1700)/255)+1700)
                TempMired = 1000000 // TempKelvin
                self.log.logging( "Command", 'Log', "---------- Set Temp Kelvin: %s-%s" %(TempMired, Hex_Format(4,TempMired)), NWKID)
                sendZigateCmd(self, "00C0","02" + NWKID + ZIGATE_EP + EPout + Hex_Format(4,TempMired) + transitionTemp)
            else:
                # How to powerOff the WW/CW channel ?
                pass

            # Process Colour
            h, s, l = rgb_to_hsl((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
            saturation = s * 100   #0 > 100
            hue = h *360           #0 > 360
            hue = int(hue*254//360)
            saturation = int(saturation*254//100)
            self.log.logging( "Command", 'Log', "---------- Set Hue X: %s Saturation: %s" %(hue, saturation), NWKID)
            sendZigateCmd(self, "00B6","02" + NWKID + ZIGATE_EP + EPout + Hex_Format(2,hue) + Hex_Format(2,saturation) + transitionRGB)

            #value = int(l * 254//100)
            #OnOff = '01'
            #self.log.logging( "Command", 'Debug', "---------- Set Level: %s instead of Level: %s" %(value, Level), NWKID)
            #sendZigateCmd(self, "0081","02" + NWKID + ZIGATE_EP + EPout + OnOff + Hex_Format(2,value) + "0000")
            # Let's force a refresh of Attribute in the next Heartbeat  
            #self.ListOfDevices[NWKID]['Heartbeat'] = '0'  

        #With saturation and hue, not seen in domoticz but present on zigate, and some device need it
        elif Hue_List['m'] == 9998:
            h, s, l = rgb_to_hsl((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
            saturation = s * 100   #0 > 100
            hue = h *360           #0 > 360
            hue = int(hue*254//360)
            saturation = int(saturation*254//100)
            self.log.logging( "Command", 'Debug', "---------- Set Hue X: %s Saturation: %s" %(hue, saturation), NWKID)
            sendZigateCmd(self, "00B6","02" + NWKID + ZIGATE_EP + EPout + Hex_Format(2,hue) + Hex_Format(2,saturation) + transitionHue)

            value = int(l * 254//100)
            OnOff = '01'
            self.log.logging( "Command", 'Debug', "---------- Set Level: %s instead of Level: %s" %(value, Level), NWKID)
            sendZigateCmd(self, "0081","02" + NWKID + ZIGATE_EP + EPout + OnOff + Hex_Format(2,value) + transitionMoveLevel)
            # Let's force a refresh of Attribute in the next Heartbeat  
            self.ListOfDevices[NWKID]['Heartbeat'] = '0'  

        UpdateDevice_v2(self, Devices, Unit, 1, str(Level) ,BatteryLevel, SignalLevel, str(Color))
