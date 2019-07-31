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

from Modules.tools import Hex_Format, rgb_to_xy, rgb_to_hsl, loggingCommand
from Modules.output import sendZigateCmd, thermostat_Setpoint, livolo_OnOff
from Modules.domoticz import UpdateDevice_v2
from Classes.IAS import IAS_Zone_Management


def mgtCommand( self, Devices, Unit, Command, Level, Color ) :

    loggingCommand( self, 'Debug', "mgtCommand called for Devices[%s].Name: %s SwitchType: %s Command: %s Level: %s Color: %s" %(Unit , Devices[Unit].Name, Devices[Unit].SwitchType, Command, Level, Color ))

    # As we can have a new Short address, we need to retreive it from self.ListOfDevices
    if Devices[Unit].DeviceID in self.IEEE2NWK:
        NWKID = self.IEEE2NWK[Devices[Unit].DeviceID]
    else :
        Domoticz.Error("mgtCommand - something strange the Device " +str(Devices[Unit].Name) + " DeviceID : " +str(Devices[Unit].DeviceID) + " is unknown from the Plugin")
        return
    loggingCommand( self, 'Debug', "mgtCommand - NWKID = " +str(NWKID) , NWKID)

    if self.ListOfDevices[NWKID]['RSSI'] != '' :
        SignalLevel = self.ListOfDevices[NWKID]['RSSI']
    else : SignalLevel = 15
    if self.ListOfDevices[NWKID]['Battery'] != '' :
        BatteryLevel = self.ListOfDevices[NWKID]['Battery']
    else : BatteryLevel = 255


    # Determine the possible ClusterType for that Device
    DeviceTypeList = []
    newFashon = True
    if 'ClusterType' in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]['ClusterType'] != {}:
            DeviceTypeList.append(self.ListOfDevices[NWKID]['ClusterType'][str(Devices[Unit].ID)])
            newFashon = False
    if newFashon:
        for tmpEp in self.ListOfDevices[NWKID]['Ep'] :
            if 'ClusterType' in self.ListOfDevices[NWKID]['Ep'][tmpEp]:
                for key in self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'] :
                    if str(Devices[Unit].ID) == str(key) :
                        loggingCommand( self, 'Debug', "mgtCommand : found Device : " +str(key) + " in Ep " +str(tmpEp) + " " +str(self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'][key])  , NWKID)
                        DeviceTypeList.append(str(self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'][key]))
    
    if len(DeviceTypeList) == 0 :    # No match with ClusterType
        Domoticz.Error("mgtCommand - no ClusterType found !  "  +str(self.ListOfDevices[NWKID]) )
        return

    loggingCommand( self, 'Debug', "mgtCommand - List of TypeName : " +str(DeviceTypeList) , NWKID)
    # We have list of DeviceType, let's see which one are matching Command style

    ClusterSearch = ''
    DeviceType = ''
    for tmpDeviceType in DeviceTypeList :
        if tmpDeviceType in ( "Switch", "Plug", "SwitchAQ2", "Smoke", "DSwitch", "Button", "DButton", 'LivoloSWL', 'LivoloSWR'):
            ClusterSearch="0006"
            DeviceType = tmpDeviceType
        if tmpDeviceType == "WindowCovering":
            ClusterSearch = '0102'
            DeviceType = tmpDeviceType
        if tmpDeviceType =="LvlControl" :
            ClusterSearch="0008"
            DeviceType = tmpDeviceType
        if tmpDeviceType in ( 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl') :
            ClusterSearch="0300"
            DeviceType = tmpDeviceType
        if tmpDeviceType == 'ThermoSetpoint':
            ClusterSearch = '0201'
            DeviceType = tmpDeviceType
        if tmpDeviceType == 'Motion':
            ClusterSearch = '0406'
            DeviceType = tmpDeviceType
        if tmpDeviceType == "AlarmWD":
            ClusterSearch = '0502'
            DeviceType = tmpDeviceType

    if DeviceType == '': 
        Domoticz.Log("mgtCommand - Look you are trying to action a non commandable device Device %s has available Type %s " %( Devices[Unit].Name, DeviceTypeList ))
        return

    loggingCommand( self, 'Debug', "mgtCommand - DeviceType : " +str(DeviceType) , NWKID)

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
                            loggingCommand( self, 'Debug', "mgtCommand : Found Ep " +str(tmpEp) + " for Device " +str(key) + " Cluster " +str(ClusterSearch) , NWKID)
                            EPout = tmpEp


    loggingCommand( self, 'Debug', "EPout = " +str(EPout) , NWKID)
    if 'Health' in self.ListOfDevices[NWKID]:
        # If Health is Not Reachable, let's give it a chance to be updated
        if self.ListOfDevices[NWKID]['Health'] == 'Not Reachable':
            self.ListOfDevices[NWKID]['Health'] = ''

    if Command == "Off" :
        self.ListOfDevices[NWKID]['Heartbeat'] = 0  # Let's force a refresh of Attribute in the next Heartbeat
        if EPout == '06': # Mostlikely a Livolo Device
            if DeviceType == 'LivoloSWL':
                livolo_OnOff( self, NWKID , EPout, 'Left', 'Off')
            elif DeviceType == 'LivoloSWR':
                livolo_OnOff( self, NWKID , EPout, 'Right', 'Off')

        if DeviceType == "WindowCovering":
            # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
            sendZigateCmd(self, "00FA","02" + NWKID + "01" + EPout + "01")
        else:
            sendZigateCmd(self, "0092","02" + NWKID + "01" + EPout + "00")

        if DeviceType == "AlarmWD":
            Domoticz.Log("Alarm WarningDevice - value: %s" %Level)
            self.iaszonemgt.alarm_off( NWKID, EPout)

        if Devices[Unit].SwitchType == 16 :
            UpdateDevice_v2(self, Devices, Unit, 0, "0",BatteryLevel, SignalLevel)
        else :
            UpdateDevice_v2(self, Devices, Unit, 0, "Off",BatteryLevel, SignalLevel)

    if Command == "On" :
        self.ListOfDevices[NWKID]['Heartbeat'] = 0  # Let's force a refresh of Attribute in the next Heartbeat

        if EPout == '06': # Mostlikely a Livolo Device
            if DeviceType == 'LivoloSWL':
                livolo_OnOff( self, NWKID , EPout, 'Left', 'On')
            elif DeviceType == 'LivoloSWR':
                livolo_OnOff( self, NWKID , EPout, 'Right', 'On')

        if DeviceType == "WindowCovering":
            # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
            sendZigateCmd(self, "00FA","02" + NWKID + "01" + EPout + "00")
        else:
            sendZigateCmd(self, "0092","02" + NWKID + "01" + EPout + "01")
        if Devices[Unit].SwitchType == 16 :
            UpdateDevice_v2(self, Devices, Unit, 1, "100",BatteryLevel, SignalLevel)
        else:
            UpdateDevice_v2(self, Devices, Unit, 1, "On",BatteryLevel, SignalLevel)

    if Command == "Set Level" :
        #Level is normally an integer but may be a floating point number if the Unit is linked to a thermostat device
        #There is too, move max level, mode = 00/01 for 0%/100%
        
        self.ListOfDevices[NWKID]['Heartbeat'] = 0  # Let's force a refresh of Attribute in the next Heartbeat
        if DeviceType == 'ThermoSetpoint':
            value = int(float(Level)*100)
            Domoticz.Log("Calling thermostat_Setpoint( %s, %s) " %(NWKID, value))
            thermostat_Setpoint( self, NWKID, value )
            return

        elif DeviceType == 'ThermoMode':
            Domoticz.Log("ThermoMode - requested value: %s" %value)
            #'Off' : 0x00 ,
            #'Auto' : 0x01 ,
            #'Reserved' : 0x02,
            #'Cool' : 0x03,
            #'Heat' :  0x04,
            #'Emergency Heating' : 0x05,
            #'Pre-cooling' : 0x06,
            #'Fan only' : 0x07 
            if value == 0:
                value = 'off'
                thermostat_Mode( self, NWKID, value)

        elif  DeviceType == "WindowCovering":
            # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
            value = '%02x' %Level
            Domoticz.Log("WindowCovering - Go To Lift Percentage Command - %s/%s Level: 0x%s" %(NWKID, EPout, value))
            sendZigateCmd(self, "00FA","02" + NWKID + "01" + EPout + "05" + value)

        elif DeviceType == "AlarmWD":
            Domoticz.Log("Alarm WarningDevice - value: %s" %Level)
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
            sendZigateCmd(self, "0081","02" + NWKID + EPin + EPout + OnOff + value + "0010")

        if Devices[Unit].SwitchType == 16 :
            UpdateDevice_v2(self, Devices, Unit, 2, str(Level) ,BatteryLevel, SignalLevel) 
        else:
            # A bit hugly, but '1' instead of '2' is needed for the ColorSwitch dimmer to behave correctky
            UpdateDevice_v2(self, Devices, Unit, 1, str(Level) ,BatteryLevel, SignalLevel) 

    if Command == "Set Color" :
        loggingCommand( self, 'Debug', "onCommand - Set Color - Level = " + str(Level) + " Color = " + str(Color) , NWKID)
        self.ListOfDevices[NWKID]['Heartbeat'] = 0  # Let's force a refresh of Attribute in the next Heartbeat
        Hue_List = json.loads(Color)
        
        #Color 
        #    ColorMode m;
        #    uint8_t t;     // Range:0..255, Color temperature (warm / cold ratio, 0 is coldest, 255 is warmest)
        #    uint8_t r;     // Range:0..255, Red level
        #    uint8_t g;     // Range:0..255, Green level
        #    uint8_t b;     // Range:0..255, Blue level
        #    uint8_t cw;    // Range:0..255, Cold white level
        #    uint8_t ww;    // Range:0..255, Warm white level (also used as level for monochrome white)
        #

        self.ListOfDevices[NWKID]['Heartbeat'] = 0  # As we update the Device, let's restart and do the next pool in 5'

        #First manage level
        OnOff = '01' # 00 = off, 01 = on
        value=Hex_Format(2,round(1+Level*254/100)) #To prevent off state
        sendZigateCmd(self, "0081","02" + NWKID + EPin + EPout + OnOff + value + "0000")

        #Now color
        #ColorModeNone = 0   // Illegal
        #ColorModeNone = 1   // White. Valid fields: none
        if Hue_List['m'] == 1:
            ww = int(Hue_List['ww']) # Can be used as level for monochrome white
            #TODO : Jamais vu un device avec ca encore
            loggingCommand( self, 'Debug', "Not implemented device color 1", NWKID)
        #ColorModeTemp = 2   // White with color temperature. Valid fields: t
        if Hue_List['m'] == 2:
            #Value is in mireds (not kelvin)
            #Correct values are from 153 (6500K) up to 588 (1700K)
            # t is 0 > 255
            TempKelvin = int(((255 - int(Hue_List['t']))*(6500-1700)/255)+1700);
            TempMired = 1000000 // TempKelvin
            sendZigateCmd(self, "00C0","02" + NWKID + EPin + EPout + Hex_Format(4,TempMired) + "0000")
        #ColorModeRGB = 3    // Color. Valid fields: r, g, b.
        elif Hue_List['m'] == 3:
            x, y = rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
            #Convert 0>1 to 0>FFFF
            x = int(x*65536)
            y = int(y*65536)
            strxy = Hex_Format(4,x) + Hex_Format(4,y)
            sendZigateCmd(self, "00B7","02" + NWKID + EPin + EPout + strxy + "0000")
        #ColorModeCustom = 4, // Custom (color + white). Valid fields: r, g, b, cw, ww, depending on device capabilities
        elif Hue_List['m'] == 4:
            ww = int(Hue_List['ww'])
            cw = int(Hue_List['cw'])
            x, y = rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))    
            #TODO, Pas trouve de device avec ca encore ...
            loggingCommand( self, 'Debug', "Not implemented device color 2", NWKID)
        #With saturation and hue, not seen in domoticz but present on zigate, and some device need it
        elif Hue_List['m'] == 9998:
            h,l,s = rgb_to_hsl((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
            saturation = s * 100   #0 > 100
            hue = h *360           #0 > 360
            hue = int(hue*254//360)
            saturation = int(saturation*254//100)
            value = int(l * 254//100)
            OnOff = '01'
            sendZigateCmd(self, "00B6","02" + NWKID + EPin + EPout + Hex_Format(2,hue) + Hex_Format(2,saturation) + "0000")
            sendZigateCmd(self, "0081","02" + NWKID + EPin + EPout + OnOff + Hex_Format(2,value) + "0010")

        #Update Device
        UpdateDevice_v2(self, Devices, Unit, 1, str(value) ,BatteryLevel, SignalLevel, str(Color))
