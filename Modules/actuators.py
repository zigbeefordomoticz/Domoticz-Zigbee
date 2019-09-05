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

from Modules.tools import Hex_Format, rgb_to_xy, rgb_to_hsl, loggingCommand
from Modules.output import sendZigateCmd, thermostat_Setpoint

def actuators( self, action, nwkid, epout, DeviceType, cmd=None, value=None, color=None):

    loggingCommand( self, 'Log', "actuators - Action: %s on %s/%s with %s %s %s %s" 
            %(action , nwkid, epout, DeviceType, cmd, value, color))

    if nwkid not in self.ListOfDevices:
        Domoticz.Error("actuators - Unknown device: %s" %(nwkid))
        return
    if epout not in self.ListOfDevices[nwkid]['Ep']:
        Domoticz.Error("actuators - Unknown Ep: %s for device: %s" %(epout,nwkid))
        return

    if cmd == 'On':
        actuator_on( self, nwkid, epout, DeviceType )
    elif cmd == 'Off':
        actuator_off( self, nwkid, epout, DeviceType)
    elif cmd == 'Stop':
        actuator_off( self, nwkid, epout, DeviceType)
    elif cmd == 'Toggle':
        actuator_off( self, nwkid, epout, DeviceType)
    elif cmd == 'SetLevel' and value is not None:
        actuator_setlevel( self, nwkid, epout, value, DeviceType)
    elif cmd == 'SetColor' and value is not None and color is not None:
        actuator_setcolor( self, nwkid, epout, value, color)
    else:
        Domoticz.Error("actuators - Command: %s error: %s/%s %s %s" %(cmd, nwkid, epout, value, color))


def actuator_toggle( self, nwkid, ep, DeviceType):

    # To be implemented
    sendZigateCmd(self, "0092","02" + NWKID + "01" + EPout + "02")
    return

def actuator_stop( self, nwkid, ep, DeviceType):

    if DeviceType == "WindowCovering":
        # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
        Domoticz.Log("Sending STOP to Zigate .. Queue: %s" %(self.ZigateComm.zigateSendingFIFO))
        sendZigateCmd(self, "00FA","02" + NWKID + "01" + EPout + "02")
    else:
        sendZigateCmd(self, "0083","02" + NWKID + "01" + EPout )

def actuator_off(  self, nwkid, ep, DeviceType):

    if DeviceType == 'LivoloSWL':
        sendZigateCmd(self, "0081","02" + nwkid + '01' + EPout + '00' + '01' + '0001')

    elif DeviceType == 'LivoloSWR':
        sendZigateCmd(self, "0081","02" + nwkid + '01' + EPout + '00' + '01' + '0002')

    elif DeviceType == "WindowCovering":
        # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
        sendZigateCmd(self, "00FA","02" + NWKID + "01" + EPout + "01")

    elif DeviceType == "AlarmWD":
        Domoticz.Log("Alarm WarningDevice - value: %s" %Level)
        self.iaszonemgt.alarm_off( NWKID, EPout)

    else:
        sendZigateCmd(self, "0092","02" + NWKID + "01" + EPout + "00")

def actuator_on(  self, nwkid, ep, DeviceType):

    if DeviceType == 'LivoloSWL':
        # Level = 108 / 0x6C for On
        sendZigateCmd(self, "0081","02" + nwkid + '01' + EPout + '00' + '6C' + '0001')
    elif DeviceType == 'LivoloSWR':
        sendZigateCmd(self, "0081","02" + nwkid + '01' + EPout + '00' + '6C' + '0002')

    elif DeviceType == "WindowCovering":
        # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
        sendZigateCmd(self, "00FA","02" + NWKID + "01" + EPout + "00")

    else:
        sendZigateCmd(self, "0092","02" + NWKID + "01" + EPout + "01")

def actuator_setlevel( self, nwkid, ep, value, DeviceType):

    if DeviceType == 'ThermoMode':
        actuator_setthermostat(self, nwkid, ep, value)
    elif DeviceType == 'ThermoSetpoint':
        actuator_setpoint(self, nwkid, ep, value)
    elif DeviceType == "AlarmWD":
        actuator_setalarm( self, nwkid, ep, value)
    elif  DeviceType == "WindowCovering":
        # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
        if Level == 0:
            Level = 1
        elif Level >= 100:
            Level = 99
        value = '%02x' %Level
        Domoticz.Log("WindowCovering - Lift Percentage Command - %s/%s Level: 0x%s %s" %(NWKID, EPout, value, Level))
        sendZigateCmd(self, "00FA","02" + NWKID + "01" + EPout + "05" + value)
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
    if value == 0:
        value = 'off'
        thermostat_Mode( self, NWKID, value)


def actuator_setpoint(  self, nwkid, ep, value ):
    value = int(float(Level)*100)
    Domoticz.Log("Calling thermostat_Setpoint( %s, %s) " %(NWKID, value))
    thermostat_Setpoint( self, NWKID, value )

def actuator_setalarm( self, nwkid, ep, value ):

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

def actuator_setcolor( self, nwkid, ep, value, Color ):
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
