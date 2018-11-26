#!/usr/bin/env python3
# coding: utf-8 -*-
"""
    Module: z_command.py

    Description: Implement the onCommand() 

"""

import Domoticz
import binascii
import time
import struct
import json

import z_var          # Global variables
import z_tools
import z_output
import z_domoticz


def mgtCommand( self, Devices, Unit, Command, Level, Color ) :
    Domoticz.Debug("#########################")
    Domoticz.Debug("onCommand called for Devices[%s].Name: %s SwitchType: %s Command: %s Level: %s Color: %s" %(Unit , Devices[Unit].Name, Devices[Unit].SwitchType, Command, Level, Color ))

    # As we can have a new Short address, we need to retreive it from self.ListOfDevices
    if Devices[Unit].DeviceID in self.IEEE2NWK:
        NWKID = self.IEEE2NWK[Devices[Unit].DeviceID]
    else :
        Domoticz.Error("mgtCommand - something strange the Device " +str(Devices[Unit].Name) + " DeviceID : " +str(Devices[Unit].DeviceID) + " is unknown from the Plugin")
        return
    Domoticz.Debug("mgtCommand - NWKID = " +str(NWKID) )

    if self.ListOfDevices[NWKID]['RSSI'] != '' :
        SignalLevel = self.ListOfDevices[NWKID]['RSSI']
    else : SignalLevel = 15
    if self.ListOfDevices[NWKID]['Battery'] != '' :
        BatteryLevel = self.ListOfDevices[NWKID]['Battery']
    else : BatteryLevel = 255


    # Determine the possible ClusterType for that Device
    DeviceTypeList = []
    if 'ClusterType' in self.ListOfDevices[NWKID]:
        DeviceTypeList.append(self.ListOfDevices[NWKID]['ClusterType'][str(Devices[Unit].ID)])
    else :
        for tmpEp in self.ListOfDevices[NWKID]['Ep'] :
            if 'ClusterType' in self.ListOfDevices[NWKID]['Ep'][tmpEp]:
                for key in self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'] :
                    if str(Devices[Unit].ID) == str(key) :
                        Domoticz.Debug("mgtCommand : found Device : " +str(key) + " in Ep " +str(tmpEp) + " " +str(self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'][key])  )
                        DeviceTypeList.append(str(self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'][key]))
    
    if len(DeviceTypeList) == 0 :    # No match with ClusterType
        Domoticz.Error("mgtCommand - no ClusterType found !  "  +str(self.ListOfDevices[NWKID]) )
        return

    Domoticz.Debug("mgtCommand - List of TypeName : " +str(DeviceTypeList) )
    # We have list of DeviceType, let's see which one are matching Command style

    ClusterSearch = ''
    DeviceType = ''
    for tmpDeviceType in DeviceTypeList :
        if tmpDeviceType =="Switch" or tmpDeviceType =="Plug" or tmpDeviceType =="SwitchAQ2" or tmpDeviceType =="Smoke" or tmpDeviceType =="DSwitch" or tmpDeviceType =="Button" or tmpDeviceType =="DButton":
            ClusterSearch="0006"
            DeviceType = tmpDeviceType
        if tmpDeviceType =="LvlControl" :
            ClusterSearch="0008"
            DeviceType = tmpDeviceType
        if tmpDeviceType =="ColorControl" :
            ClusterSearch="0300"
            DeviceType = tmpDeviceType

    if DeviceType == '': 
        Domoticz.Log("mgtCommand - Look you are trying to action a non commandable device Device %s has available Type %s " %( Devices[Unit].Name, DeviceTypeList ))
        return

    Domoticz.Debug("mgtCommand - DeviceType : " +str(DeviceType) )


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
                            Domoticz.Debug("mgtCommand : Found Ep " +str(tmpEp) + " for Device " +str(key) + " Cluster " +str(ClusterSearch) )
                            EPout = tmpEp


    Domoticz.Debug("EPout = " +str(EPout) )

    if Command == "Off" :
        self.ListOfDevices[NWKID]['Heartbeat'] = 0  # Let's force a refresh of Attribute in the next Hearbeat
        z_output.sendZigateCmd(self, "0092","02" + NWKID + EPin + EPout + "00")
        if Devices[Unit].SwitchType == "16" :
            z_domoticz.UpdateDevice_v2(Devices, Unit, 0, "0",BatteryLevel, SignalLevel)
        else :
            z_domoticz.UpdateDevice_v2(Devices, Unit, 0, "Off",BatteryLevel, SignalLevel)

    if Command == "On" :
        self.ListOfDevices[NWKID]['Heartbeat'] = 0  # Let's force a refresh of Attribute in the next Hearbeat
        z_output.sendZigateCmd(self, "0092","02" + NWKID + EPin + EPout + "01")
        if Devices[Unit].SwitchType == "16" :
            z_domoticz.UpdateDevice_v2(Devices, Unit, 1, "100",BatteryLevel, SignalLevel)
        else:
            z_domoticz.UpdateDevice_v2(Devices, Unit, 1, "On",BatteryLevel, SignalLevel)

    if Command == "Set Level" :
        #Level is normally an integer but may be a floating point number if the Unit is linked to a thermostat device
        #There is too, move max level, mode = 00/01 for 0%/100%
        
        self.ListOfDevices[NWKID]['Heartbeat'] = 0  # Let's force a refresh of Attribute in the next Hearbeat
        OnOff = '01' # 00 = off, 01 = on
        value=z_tools.Hex_Format(2,round(Level*255/100)) #To prevent off state with dimmer, only available with switch
        z_output.sendZigateCmd(self, "0081","02" + NWKID + EPin + EPout + OnOff + value + "0010")
        if Devices[Unit].SwitchType == 16 :
            z_domoticz.UpdateDevice_v2(Devices, Unit, 2, str(Level) ,BatteryLevel, SignalLevel) 
        else:
            z_domoticz.UpdateDevice_v2(Devices, Unit, 1, str(Level) ,BatteryLevel, SignalLevel) # A bit hugly, but '1' instead of '2' is needed for the ColorSwitch dimmer to behave correctky

    if Command == "Set Color" :
        Domoticz.Debug("onCommand - Set Color - Level = " + str(Level) + " Color = " + str(Color) )
        self.ListOfDevices[NWKID]['Heartbeat'] = 0  # Let's force a refresh of Attribute in the next Hearbeat
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

        def rgb_to_xy(rgb):
            ''' convert rgb tuple to xy tuple '''
            red, green, blue = rgb
            r = ((red + 0.055) / (1.0 + 0.055))**2.4 if (red > 0.04045) else (red / 12.92)
            g = ((green + 0.055) / (1.0 + 0.055))**2.4 if (green > 0.04045) else (green / 12.92)
            b = ((blue + 0.055) / (1.0 + 0.055))**2.4 if (blue > 0.04045) else (blue / 12.92)
            X = r * 0.664511 + g * 0.154324 + b * 0.162028
            Y = r * 0.283881 + g * 0.668433 + b * 0.047685
            Z = r * 0.000088 + g * 0.072310 + b * 0.986039
            cx = 0
            cy = 0
            if (X + Y + Z) != 0:
                cx = X / (X + Y + Z)
                cy = Y / (X + Y + Z)
            return (cx, cy)

        def rgb_to_hsl(rgb):
            ''' convert rgb tuple to hls tuple '''
            r, g, b = rgb
            r = float(r/255)
            g = float(g/255)
            b = float(b/255)
            high = max(r, g, b)
            low = min(r, g, b)
            h, s, l = ((high + low) / 2,)*3

            if high == low:
                h = 0.0
                s = 0.0
            else:
                d = high - low
                s = d / (2 - high - low) if l > 0.5 else d / (high + low)
                h = {
                    r: (g - b) / d + (6 if g < b else 0),
                    g: (b - r) / d + 2,
                    b: (r - g) / d + 4,
                }[high]
                h /= 6

            return h, s, l

        self.ListOfDevices[NWKID]['Heartbeat'] = 0  # As we update the Device, let's restart and do the next pool in 5'

        #First manage level
        OnOff = '01' # 00 = off, 01 = on
        value=z_tools.Hex_Format(2,round(1+Level*254/100)) #To prevent off state
        z_output.sendZigateCmd(self, "0081","02" + NWKID + EPin + EPout + OnOff + value + "0000")

        #Now color
        #ColorModeNone = 0   // Illegal
        #ColorModeNone = 1   // White. Valid fields: none
        if Hue_List['m'] == 1:
            ww = int(Hue_List['ww']) # Can be used as level for monochrome white
            #TODO : Jamais vu un device avec ca encore
            Domoticz.Debug("Not implemented device color 1")    
        #ColorModeTemp = 2   // White with color temperature. Valid fields: t
        if Hue_List['m'] == 2:
            #Value is in mireds (not kelvin)
            #Correct values are from 153 (6500K) up to 588 (1700K)
            # t is 0 > 255
            TempKelvin = int(((255 - int(Hue_List['t']))*(6500-1700)/255)+1700);
            TempMired = 1000000 // TempKelvin
            z_output.sendZigateCmd(self, "00C0","02" + NWKID + EPin + EPout + z_tools.Hex_Format(4,TempMired) + "0000")
        #ColorModeRGB = 3    // Color. Valid fields: r, g, b.
        elif Hue_List['m'] == 3:
            x, y = rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
            #Convert 0>1 to 0>FFFF
            x = int(x*65536)
            y = int(y*65536)
            strxy = z_tools.Hex_Format(4,x) + z_tools.Hex_Format(4,y)
            z_output.sendZigateCmd(self, "00B7","02" + NWKID + EPin + EPout + strxy + "0000")
        #ColorModeCustom = 4, // Custom (color + white). Valid fields: r, g, b, cw, ww, depending on device capabilities
        elif Hue_List['m'] == 4:
            ww = int(Hue_List['ww'])
            cw = int(Hue_List['cw'])
            x, y = rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))    
            #TODO, Pas trouve de device avec ca encore ...
            Domoticz.Debug("Not implemented device color 2")
        #With saturation and hue, not seen in domoticz but present on zigate, and some device need it
        elif Hue_List['m'] == 9998:
            h,l,s = rgb_to_hsl((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
            saturation = s * 100   #0 > 100
            hue = h *360           #0 > 360
            hue = int(hue*254//360)
            saturation = int(saturation*254//100)
            value = int(l * 254//100)
            OnOff = '01'
            z_output.sendZigateCmd(self, "00B6","02" + NWKID + EPin + EPout + z_tools.Hex_Format(2,hue) + z_tools.Hex_Format(2,saturation) + "0000")
            z_output.sendZigateCmd(self, "0081","02" + NWKID + EPin + EPout + OnOff + z_tools.Hex_Format(2,value) + "0010")

        #Update Device
        z_domoticz.UpdateDevice_v2(Devices, Unit, 1, str(value) ,BatteryLevel, SignalLevel, str(Color))



