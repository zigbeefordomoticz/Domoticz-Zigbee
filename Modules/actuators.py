#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: actuators.py

    Description: actuators to end objects

"""

import Domoticz
import json

from Modules.tools import Hex_Format, rgb_to_xy, rgb_to_hsl
from Modules.logging import loggingCommand
from Modules.output import sendZigateCmd, thermostat_Setpoint
from Modules.zigateConsts import ZIGATE_EP

def actuators( self, action, nwkid, epout, DeviceType, cmd=None, value=None, color=None):

    loggingCommand( self, 'Log', "actuators - Action: %s on %s/%s with %s %s %s %s" 
            %(action , nwkid, epout, DeviceType, cmd, value, color))

    if nwkid not in self.ListOfDevices:
        Domoticz.Error("actuators - Unknown device: %s" %(nwkid))
        return
    if epout not in self.ListOfDevices[nwkid]['Ep']:
        Domoticz.Error("actuators - Unknown Ep: %s for device: %s" %(epout,nwkid))
        return

    if action == 'On':
        actuator_on( self, nwkid, epout, DeviceType )
    elif action == 'Off':
        actuator_off( self, nwkid, epout, DeviceType)
    elif action == 'Stop':
        actuator_off( self, nwkid, epout, DeviceType)
    elif action == 'Toggle':
        actuator_toggle( self, nwkid, epout, DeviceType)
    elif action == 'SetLevel' and value is not None:
        actuator_setlevel( self, nwkid, epout, value, DeviceType)
    elif action == 'SetColor' and value is not None and color is not None:
        actuator_setcolor( self, nwkid, epout, value, color)
    elif action == 'Identify':
        actuator_identify( self, nwkid, epout)
    elif action == 'IdentifyEffect':
        actuator_identify( self, nwkid, epout, value)
    else:
        Domoticz.Error("actuators - Command: %s not yet implemented: %s/%s %s %s" %(action, nwkid, epout, value, color))


def actuator_toggle( self, nwkid, EPout, DeviceType):

    # To be implemented
    sendZigateCmd(self, "0092","02" + nwkid + ZIGATE_EP + EPout + "02")
    return

def actuator_stop( self, nwkid, EPout, DeviceType):

    if DeviceType == "WindowCovering":
        # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
        Domoticz.Log("Sending STOP to Zigate .. Queue: %s" %(self.ZigateComm.zigateSendingFIFO))
        sendZigateCmd(self, "00FA","02" + nwkid + ZIGATE_EP + EPout + "02")
    else:
        sendZigateCmd(self, "0083","02" + nwkid + ZIGATE_EP + EPout )

def actuator_off(  self, nwkid, EPout, DeviceType):

    if DeviceType == "AlarmWD":
        Domoticz.Log("Alarm WarningDevice - value: %s" %'off')
        self.iaszonemgt.alarm_off( nwkid, EPout)

    elif DeviceType == 'LivoloSWL':
        sendZigateCmd(self, "0081","02" + nwkid + ZIGATE_EP + EPout + '00' + '01' + '0001')

    elif DeviceType == 'LivoloSWR':
        sendZigateCmd(self, "0081","02" + nwkid + ZIGATE_EP + EPout + '00' + '01' + '0002')

    elif DeviceType == "WindowCovering":
        # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
        sendZigateCmd(self, "00FA","02" + nwkid + ZIGATE_EP + EPout + "01")

    else:
        sendZigateCmd(self, "0092","02" + nwkid + ZIGATE_EP + EPout + "00")

def actuator_on(  self, nwkid, EPout, DeviceType):

    if DeviceType == 'LivoloSWL':
        # Level = 108 / 0x6C for On
        sendZigateCmd(self, "0081","02" + nwkid + ZIGATE_EP + EPout + '00' + '6C' + '0001')
    elif DeviceType == 'LivoloSWR':
        sendZigateCmd(self, "0081","02" + nwkid + ZIGATE_EP + EPout + '00' + '6C' + '0002')

    elif DeviceType == "WindowCovering":
        # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
        sendZigateCmd(self, "00FA","02" + nwkid + ZIGATE_EP + EPout + "00")

    else:
        sendZigateCmd(self, "0092","02" + nwkid + ZIGATE_EP + EPout + "01")

def actuator_setlevel( self, nwkid, EPout, value, DeviceType):

    if DeviceType == 'ThermoMode':
        actuator_setthermostat(self, nwkid, EPout, value)
    elif DeviceType == 'ThermoSetpoint':
        actuator_setpoint(self, nwkid, EPout, value)
    elif DeviceType == "AlarmWD":
        actuator_setalarm( self, nwkid, EPout, value)
    elif  DeviceType == "WindowCovering":
        # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
        if value == 0:
            value = 1
        elif value >= 100:
            value = 99
        value = '%02x' %value
        Domoticz.Log("WindowCovering - Lift Percentage Command - %s/%s value: 0x%s %s" %(nwkid, EPout, value, value))
        sendZigateCmd(self, "00FA","02" + nwkid + ZIGATE_EP + EPout + "05" + value)
    else:
        OnOff = '01' # 00 = off, 01 = on
        if value == 100: 
            value = 255
        elif value == 0: 
            value = 0
        else:
            value = round( (value*255)/100)
            if value > 0 and value == 0: 
                value = 1

        value=Hex_Format(2, value)
        sendZigateCmd(self, "0081","02" + nwkid + ZIGATE_EP + EPout + OnOff + value + "0010")

def actuator_setthermostat( self, nwkid, ep, value ):

    Domoticz.Log("ThermoMode - requested value: %s" %value)
    #'Off' : 0x00 ,
    #'Auto' : 0x01 ,
    #'Reserved' : 0x02,
    #'Cool' : 0x03,
    #'Heat' :  0x04,
    #'Emergency Heating' : 0x05,
    #'Pre-cooling' : 0x06,
    #'Fan only' : 0x07 

    return


def actuator_setpoint(  self, nwkid, ep, value ):
    value = int(float(value)*100)
    Domoticz.Log("Calling thermostat_Setpoint( %s, %s) " %(nwkid, value))
    thermostat_Setpoint( self, nwkid, value )

def actuator_setalarm( self, nwkid, EPout, value ):

    Domoticz.Log("Alarm WarningDevice - value: %s" %value)
    if value == 0: # Stop
        self.iaszonemgt.alarm_off( nwkid, EPout)
    elif value == 10: # Alarm
        self.iaszonemgt.alarm_on(  nwkid, EPout)
    elif value == 20: # Siren
        self.iaszonemgt.siren_only( nwkid, EPout)
    elif value == 30: # Strobe
        self.iaszonemgt.strobe_only( nwkid, EPout)
    elif value == 40: # Armed - Squawk
        self.iaszonemgt.write_IAS_WD_Squawk( nwkid, EPout, 'armed')
    elif value == 50: # Disarmed
        self.iaszonemgt.write_IAS_WD_Squawk( nwkid, EPout, 'disarmed')

def actuator_setcolor( self, nwkid, EPout, value, Color ):
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

    self.ListOfDevices[nwkid]['Heartbeat'] = 0  # As we update the Device, let's restart and do the next pool in 5'

    #First manage level
    Domoticz.Log("----> Value: >%s<" %value)

    OnOff = '01' # 00 = off, 01 = on
    value=Hex_Format(2,round(1+value*254/100)) #To prevent off state
    sendZigateCmd(self, "0081","02" + nwkid + ZIGATE_EP + EPout + OnOff + value + "0000")

    if len(Hue_List) == 0:
        Domoticz.Log("actuator_setcolor - Unable to decode Color: %s --> %s" %(Color, Hue_List))
        return

    #Now color
    #ColorModeNone = 0   // Illegal
    #ColorModeNone = 1   // White. Valid fields: none
    if Hue_List['m'] == 1:
        ww = int(Hue_List['ww']) # Can be used as level for monochrome white
        #TODO : Jamais vu un device avec ca encore
        loggingCommand( self, 'Debug', "Not implemented device color 1", nwkid)
    #ColorModeTemp = 2   // White with color temperature. Valid fields: t
    if Hue_List['m'] == 2:
        #Value is in mireds (not kelvin)
        #Correct values are from 153 (6500K) up to 588 (1700K)
        # t is 0 > 255
        TempKelvin = int(((255 - int(Hue_List['t']))*(6500-1700)/255)+1700);
        TempMired = 1000000 // TempKelvin
        sendZigateCmd(self, "00C0","02" + nwkid + ZIGATE_EP + EPout + Hex_Format(4,TempMired) + "0000")
    #ColorModeRGB = 3    // Color. Valid fields: r, g, b.
    elif Hue_List['m'] == 3:
        x, y = rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
        #Convert 0>1 to 0>FFFF
        x = int(x*65536)
        y = int(y*65536)
        strxy = Hex_Format(4,x) + Hex_Format(4,y)
        sendZigateCmd(self, "00B7","02" + nwkid + ZIGATE_EP + EPout + strxy + "0000")
    #ColorModeCustom = 4, // Custom (color + white). Valid fields: r, g, b, cw, ww, depending on device capabilities
    elif Hue_List['m'] == 4:
        ww = int(Hue_List['ww'])
        cw = int(Hue_List['cw'])
        x, y = rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))    
        #TODO, Pas trouve de device avec ca encore ...
        loggingCommand( self, 'Debug', "Not implemented device color 2", nwkid)
    #With saturation and hue, not seen in domoticz but present on zigate, and some device need it
    elif Hue_List['m'] == 9998:
        h,l,s = rgb_to_hsl((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
        saturation = s * 100   #0 > 100
        hue = h *360           #0 > 360
        hue = int(hue*254//360)
        saturation = int(saturation*254//100)
        value = int(l * 254//100)
        OnOff = '01'
        sendZigateCmd(self, "00B6","02" + nwkid + ZIGATE_EP + EPout + Hex_Format(2,hue) + Hex_Format(2,saturation) + "0000")
        sendZigateCmd(self, "0081","02" + nwkid + ZIGATE_EP + EPout + OnOff + Hex_Format(2,value) + "0010")


def actuator_identify( self, nwkid, ep, value=None):

    duration = 15

    if value is None:

        datas = "02" + "%s"%(nwkid) + ZIGATE_EP + ep + "%04x"%(duration)
        loggingCommand( self, 'Log', "identifySend - send an Identify Message to: %s for %04x seconds" %( nwkid, duration), nwkid=nwkid)
        loggingCommand( self, 'Log', "identifySend - data sent >%s< " %(datas) , nwkid=nwkid)
        sendZigateCmd(self, "0070", datas )

    else:
    
        Domoticz.Log("value: %s" %value)
        Domoticz.Log("Type: %s" %type(value))

        color = 0x00 # Default
        if value is None or value == 0:
            value = 0x00 # Blink
            if ('Manufactuer Name' in self.ListOfDevices and self.ListOfDevices['Manufacturer Name'] == 'Legrand'):
                value = 0x00 # Flashing
                color = 0x03 # Blue

        datas = "02" + "%s"%(nwkid) + ZIGATE_EP + ep + "%02x"%value  + "%02x" %color
        loggingCommand( self, 'Log', "identifyEffect - send an Identify Effecty Message to: %s for %04x seconds" %( nwkid, duration), nwkid=nwkid)
        loggingCommand( self, 'Log', "identifyEffect - data sent >%s< " %(datas) , nwkid=nwkid)
        sendZigateCmd(self, "00E0", datas )

