#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: actuators.py

    Description: actuators to end objects

"""

import json

from Modules.basicOutputs import set_poweron_afteroffon
from Modules.readAttributes import ReadAttributeRequest_0006_400x
from Modules.thermostats import thermostat_Setpoint
from Modules.tools import Hex_Format, rgb_to_hsl, rgb_to_xy, get_deviceconf_parameter_value
from Modules.zigateConsts import ZIGATE_EP
from Zigbee.zclCommands import (zcl_identify_send, zcl_identify_trigger_effect,
                                zcl_level_move_to_level,
                                zcl_move_hue_and_saturation,
                                zcl_move_to_colour,
                                zcl_move_to_colour_temperature,
                                zcl_move_to_level_with_onoff,
                                zcl_move_to_level_without_onoff,
                                zcl_onoff_off_noeffect,
                                zcl_onoff_off_witheffect, zcl_onoff_on,
                                zcl_onoff_stop, zcl_toggle,
                                zcl_window_covering_level,
                                zcl_window_covering_off,
                                zcl_window_covering_on,
                                zcl_window_covering_percentage,
                                zcl_window_covering_stop)
from Modules.tuya import tuya_color_control_command_fe


def lightning_percentage_to_analog( percentage_value ):
    """convert a percentage value (0-100) into an analog value ( 0-255)

    Args:
        percentage_value (int): a value from 0 to 100, which represent a % 

    Returns:
        _type_: a value from 1 to 254
    """
    if percentage_value > 99:
        return 254
    elif percentage_value < 1:
        return 1
    return round((percentage_value * 255) / 100)


def actuators(self, action, nwkid, epout, DeviceType, cmd=None, value=None, color=None):

    self.log.logging(
        "Command",
        "Log",
        "actuators - Action: %s on %s/%s with %s %s %s %s" % (action, nwkid, epout, DeviceType, cmd, value, color),
        nwkid,
    )

    if nwkid not in self.ListOfDevices:
        self.log.logging("Command", "Error", "actuators - Unknown device: %s" % (nwkid), nwkid, self.ListOfDevices)
        return
    if epout not in self.ListOfDevices[nwkid]["Ep"]:
        self.log.logging(
            "Command",
            "Error",
            "actuators - Unknown Ep: %s for device: %s" % (epout, nwkid),
            nwkid,
            self.ListOfDevices[nwkid]["Ep"],
        )
        return

    if action == "On":
        actuator_on(self, nwkid, epout, DeviceType)
    elif action == "Off":
        actuator_off(self, nwkid, epout, DeviceType)
    elif action == "Stop":
        actuator_off(self, nwkid, epout, DeviceType)
    elif action == "Toggle":
        zcl_toggle(self, nwkid, epout)
    elif action == "SetLevel" and value is not None:
        actuator_setlevel(self, nwkid, epout, value, DeviceType)
    elif action == "SetColor" and value is not None and color is not None:
        actuator_setcolor(self, nwkid, epout, value, color)
    elif action == "Identify":
        actuator_identify(self, nwkid, epout)
    elif action == "IdentifyEffect":
        actuator_identify(self, nwkid, epout, value)
    elif action == "PowerStateAfterOffOn":
        set_poweron_afteroffon(self, nwkid, OnOffMode=value)
        ReadAttributeRequest_0006_400x(self, nwkid)
    else:
        self.log.logging(
            "Command",
            "Error",
            "actuators - Command: %s not yet implemented: %s/%s %s %s" % (action, nwkid, epout, value, color),
            nwkid,
            {"action": action, "epout": epout, "value": value, "color": color},
        )


def actuator_stop(self, nwkid, EPout, DeviceType):

    if DeviceType == "WindowCovering":
        zcl_window_covering_stop(self, nwkid, EPout)

    else:
        zcl_onoff_stop( self, nwkid, EPout)

def actuator_off(self, nwkid, EPout, DeviceType, effect=None):
    self.log.logging("Command", "Debug", "actuator_off %s %s %s %s" % ( nwkid, EPout, DeviceType, effect))

    if DeviceType == "AlarmWD":
        self.iaszonemgt.alarm_off(nwkid, EPout)

    elif DeviceType == "LivoloSWL":
        zcl_move_to_level_without_onoff(self, nwkid, EPout, "01", "0001")

    elif DeviceType == "LivoloSWR":
        zcl_move_to_level_without_onoff(self, nwkid, EPout, "01", "0002")

    elif DeviceType == "WindowCovering":
        zcl_window_covering_off(self, nwkid, EPout)

    elif effect is not None:
        zcl_onoff_off_witheffect(self, nwkid, EPout, effect)
    else:
        zcl_onoff_off_noeffect(self, nwkid, EPout)

def actuator_on(self, nwkid, EPout, DeviceType):

    if DeviceType == "LivoloSWL":
        # Level = 108 / 0x6C for On
        zcl_move_to_level_without_onoff(self, nwkid, EPout, "6C", "0001")

    elif DeviceType == "LivoloSWR":
        zcl_move_to_level_without_onoff(self, nwkid, EPout, "6C", "0002")

    elif DeviceType == "WindowCovering":
        zcl_window_covering_on(self, nwkid, EPout)
    else:
        zcl_onoff_on(self, nwkid, EPout)

def actuator_setlevel(self, nwkid, EPout, value, DeviceType, transition="0010", withOnOff=True):

    if DeviceType == "ThermoMode":
        actuator_setthermostat(self, nwkid, EPout, value)
    elif DeviceType == "ThermoSetpoint":
        actuator_setpoint(self, nwkid, EPout, value)
    elif DeviceType == "AlarmWD":
        actuator_setalarm(self, nwkid, EPout, value)
    elif DeviceType == "WindowCovering":
        # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
        if value == 0:
            value = 1
        elif value >= 100:
            value = 99
        self.log.logging(
            "Command",
            "Log",
            "WindowCovering - Lift Percentage Command - %s/%s value: 0x%s %s" % (nwkid, EPout, value, value),
        )
        value = "%02x" % value
        zcl_window_covering_percentage(self, nwkid, EPout, value)
    else:
        value = Hex_Format(2, lightning_percentage_to_analog( value ))
        self.log.logging("Command", "Debug", "---------- actuator_setlevel Set Level: %s" % (value), nwkid)
        
        if withOnOff:
            zcl_move_to_level_with_onoff( self, nwkid, EPout, "01", value, transition)   
        else:
            zcl_move_to_level_without_onoff( self, nwkid, EPout, value, transition)  

def actuator_setthermostat(self, nwkid, ep, value):

    self.log.logging("Command", "Log", "ThermoMode - requested value: %s" % value)
    #'Off' : 0x00 ,
    #'Auto' : 0x01 ,
    #'Reserved' : 0x02,
    #'Cool' : 0x03,
    #'Heat' :  0x04,
    #'Emergency Heating' : 0x05,
    #'Pre-cooling' : 0x06,
    #'Fan only' : 0x07

def actuator_setpoint(self, nwkid, ep, value):
    value = int(float(value) * 100)
    self.log.logging("Command", "Log", "Calling thermostat_Setpoint( %s, %s) " % (nwkid, value))
    thermostat_Setpoint(self, nwkid, value)

def actuator_setalarm(self, nwkid, EPout, value):

    self.log.logging("Command", "Log", "Alarm WarningDevice - value: %s" % value)
    if value == 0:  # Stop
        self.iaszonemgt.alarm_off(nwkid, EPout)
    elif value == 10:  # Alarm
        self.iaszonemgt.alarm_on(nwkid, EPout)
    elif value == 20:  # Siren
        self.iaszonemgt.siren_only(nwkid, EPout)
    elif value == 30:  # Strobe
        self.iaszonemgt.strobe_only(nwkid, EPout)
    elif value == 40:  # Armed - Squawk
        self.iaszonemgt.write_IAS_WD_Squawk(nwkid, EPout, "armed")
    elif value == 50:  # Disarmed
        self.iaszonemgt.write_IAS_WD_Squawk(nwkid, EPout, "disarmed")

def get_all_transition_mode( self, Nwkid):

    transitionMoveLevel = transitionRGB = transitionMoveLevel = transitionHue = transitionTemp = "0000"
    if "Param" in self.ListOfDevices[Nwkid]:
        if "moveToColourTemp" in self.ListOfDevices[Nwkid]["Param"]:
            transitionTemp = "%04x" % int(self.ListOfDevices[Nwkid]["Param"]["moveToColourTemp"])
        if "moveToColourRGB" in self.ListOfDevices[Nwkid]["Param"]:
            transitionRGB = "%04x" % int(self.ListOfDevices[Nwkid]["Param"]["moveToColourRGB"])
        if "moveToLevel" in self.ListOfDevices[Nwkid]["Param"]:
            transitionMoveLevel = "%04x" % int(self.ListOfDevices[Nwkid]["Param"]["moveToLevel"])
        if "moveToHueSatu" in self.ListOfDevices[Nwkid]["Param"]:
            transitionHue = "%04x" % int(self.ListOfDevices[Nwkid]["Param"]["moveToHueSatu"])
    return transitionMoveLevel , transitionRGB , transitionMoveLevel ,transitionHue , transitionTemp

def rgb_to_hsv(r, g, b):
    r, g, b = r/255.0, g/255.0, b/255.0
    mx = max(r, g, b)
    mn = min(r, g, b)
    df = mx-mn
    if mx == mn:
        h = 0
    elif mx == r:
        h = (60 * ((g-b)/df) + 360) % 360
    elif mx == g:
        h = (60 * ((b-r)/df) + 120) % 360
    elif mx == b:
        h = (60 * ((r-g)/df) + 240) % 360
    s = 0 if mx == 0 else (df/mx)*100
    v = mx*100
    return int(h), int(s), int(v)

def actuator_setcolor(self, nwkid, EPout, value, Color):
    
    Hue_List = json.loads(Color)
    self.log.logging("Command", "Debug", "-----> Hue_List: %s" % str(Hue_List), nwkid)

    # Color
    #    ColorMode m;
    #    uint8_t t;     // Range:0..255, Color temperature (warm / cold ratio, 0 is coldest, 255 is warmest)
    #    uint8_t r;     // Range:0..255, Red level
    #    uint8_t g;     // Range:0..255, Green level
    #    uint8_t b;     // Range:0..255, Blue level
    #    uint8_t cw;    // Range:0..255, Cold white level
    #    uint8_t ww;    // Range:0..255, Warm white level (also used as level for monochrome white)
    #
    
    # First manage level
    # if Hue_List['m'] or Hue_List['m'] != 9998 or manage_level:
    transitionMoveLevel = "0000"
    if ( "Param" in self.ListOfDevices[nwkid] and "moveToLevel" in self.ListOfDevices[nwkid]["Param"] ):
        transitionMoveLevel = "%04x" % int(self.ListOfDevices[nwkid]["Param"]["moveToLevel"])

    #if Hue_List["m"] or Hue_List["m"] != 9998:
    #    value = lightning_percentage_to_analog( value )
    #    self.log.logging("Command", "Debug", "---------- Set Level: %s" % (value), nwkid)
    #    actuator_setlevel(self, nwkid, EPout, value, "Light", transitionMoveLevel)


    force_color_command = get_deviceconf_parameter_value(self, self.ListOfDevices[nwkid]["Model"], "FORCE_COLOR_COMMAND", return_default=None)
    #if force_color_command == "MovetoHueandSaturation":
    #    #     "FORCE_COLOR_COMMAND": "MovetoHueandSaturation",
    #    transitionMoveLevel , transitionRGB , _ , _ , _ = get_all_transition_mode( self, nwkid)
    #    r = int(Hue_List["r"])
    #    g = int(Hue_List["g"])
    #    b = int(Hue_List["b"])
    #    hue, saturation, brightness = rgb_to_hsv( r, g, b )
    #    self.log.logging("Command", "Debug", "MovetoHueandSaturation (%s,%s,%s) Set Hue X: %s Saturation: %s Brightness: %s" % (
    #        r, g, b, hue, saturation, brightness), nwkid)
    #    zcl_move_hue_and_saturation(self, nwkid, EPout, Hex_Format(2, hue), Hex_Format(2, saturation), transitionRGB)

    # ColorModeTemp = 2   // White with color temperature. Valid fields: t
    if Hue_List["m"] == 2:
        handle_color_mode_2(self, nwkid, EPout, Hue_List)

    elif Hue_List["m"] == 3 and force_color_command == "MovetoHueandSaturation":
        handle_color_mode_9998( self, nwkid, EPout, Hue_List)
        
    # ColorModeRGB = 3    // Color. Valid fields: r, g, b.
    elif Hue_List["m"] == 3:
        handle_color_mode_3(self, nwkid, EPout, Hue_List)

    # ColorModeCustom = 4, // Custom (color + white). Valid fields: r, g, b, cw, ww, depending on device capabilities
    elif Hue_List["m"] == 4:
        handle_color_mode_4(self, nwkid, EPout, Hue_List )
 
    # With saturation and hue, not seen in domoticz but present on zigate, and some device need it
    elif Hue_List["m"] == 9998:
        handle_color_mode_9998( self, nwkid, EPout, Hue_List)
     
def handle_color_mode_2(self, nwkid, EPout, Hue_List):
    # Value is in mireds (not kelvin)
    # Correct values are from 153 (6500K) up to 588 (1700K)
    # t is 0 > 255
    TempKelvin = int(((255 - int(Hue_List["t"])) * (6500 - 1700) / 255) + 1700)
    TempMired = 1000000 // TempKelvin
    self.log.logging( "Command", "Debug", "handle_color_mode_2 Set Temp Kelvin: %s-%s" % (TempMired, Hex_Format(4, TempMired)), nwkid )
    transitionMoveLevel , transitionRGB , transitionMoveLevel , transitionHue , transitionTemp = get_all_transition_mode( self, nwkid)
    zcl_move_to_colour_temperature( self, nwkid, EPout, Hex_Format(4, TempMired), transitionTemp)
    if get_deviceconf_parameter_value(self, self.ListOfDevices[nwkid]["Model"], "TUYA_Color_Control_Command_fe", return_default=None):
        tuya_color_control_command_fe( self, nwkid, "00")

            
def handle_color_mode_3(self, nwkid, EPout, Hue_List):
    x, y = rgb_to_xy((int(Hue_List["r"]), int(Hue_List["g"]), int(Hue_List["b"])))
    # Convert 0>1 to 0>FFFF
    x = int(x * 65536)
    y = int(y * 65536)
    #strxy = Hex_Format(4, x) + Hex_Format(4, y)
    self.log.logging("Command", "Debug", "handle_color_mode_3 Set Temp X: %s Y: %s" % (x, y), nwkid)
    transitionMoveLevel , transitionRGB , transitionMoveLevel , transitionHue , transitionTemp = get_all_transition_mode( self, nwkid)
    zcl_move_to_colour(self, nwkid, EPout, Hex_Format(4, x), Hex_Format(4, y), transitionRGB)
    
def handle_color_mode_4(self, nwkid, EPout, Hue_List ):
    # Gledopto GL_008
    # Color: {"b":43,"cw":27,"g":255,"m":4,"r":44,"t":227,"ww":215}
    self.log.logging("Command", "Log", "Not fully implemented device color 4", nwkid)
    transitionMoveLevel , transitionRGB , transitionMoveLevel , transitionHue , transitionTemp = get_all_transition_mode( self, nwkid)
    # Process White color
    cw = int(Hue_List["cw"])  # 0 < cw < 255 Cold White
    ww = int(Hue_List["ww"])  # 0 < ww < 255 Warm White
    if cw != 0 and ww != 0:
        TempKelvin = int((255 - ww) * (6500 - 1700) / 255 + 1700)
        TempMired = 1000000 // TempKelvin
        self.log.logging( "Command", "Log", "handle_color_mode_4 Set Temp Kelvin: %s-%s" % (
            TempMired, Hex_Format(4, TempMired)), nwkid )
        zcl_move_to_colour_temperature( self, nwkid, EPout, Hex_Format(4, TempMired), transitionTemp)
        if get_deviceconf_parameter_value(self, self.ListOfDevices[nwkid]["Model"], "TUYA_Color_Control_Command_fe", return_default=None):
            tuya_color_control_command_fe( self, nwkid, "00")


    # Process Colour
    _h, _s, _l = rgb_to_hsl((int(Hue_List["r"]), int(Hue_List["g"]), int(Hue_List["b"])))
    saturation = _s * 100  # 0 > 100
    saturation = int(saturation * 254 // 100)
    hue = _h * 360  # 0 > 360
    hue = int(hue * 254 // 360)
    
    self.log.logging("Command", "Log", "handle_color_mode_4 Set Hue X: %s Saturation: %s" % (
        hue, saturation), nwkid)
    zcl_move_hue_and_saturation(self, nwkid, EPout, Hex_Format(2, hue), Hex_Format(2, saturation), transitionRGB)
    if get_deviceconf_parameter_value(self, self.ListOfDevices[nwkid]["Model"], "TUYA_Color_Control_Command_fe", return_default=None):
        tuya_color_control_command_fe( self, nwkid, "01")
    
def handle_color_mode_9998( self, nwkid, EPout, Hue_List):
    transitionMoveLevel , transitionRGB , transitionMoveLevel , transitionHue , transitionTemp = get_all_transition_mode( self, nwkid)    
    _h, _s, _l = rgb_to_hsl((int(Hue_List["r"]), int(Hue_List["g"]), int(Hue_List["b"])))
    saturation = _s * 100  # 0 > 100
    saturation = int(saturation * 254 // 100)
    hue = _h * 360  # 0 > 360
    hue = int(hue * 254 // 360)
    
    self.log.logging("Command", "Debug", "handle_color_mode_9998 Set Hue X: %s Saturation: %s" % (hue, saturation), nwkid)
    zcl_move_hue_and_saturation(self, nwkid, EPout, Hex_Format(2, hue), Hex_Format(2, saturation), transitionRGB)
    if get_deviceconf_parameter_value(self, self.ListOfDevices[nwkid]["Model"], "TUYA_Color_Control_Command_fe", return_default=None):
        tuya_color_control_command_fe( self, nwkid, "01")

    value = int(_l * 254 // 100)
    OnOff = "01"
    self.log.logging( "Command", "Debug", "handle_color_mode_9998 Set Level: %s instead of Level: %s" % (value, value), nwkid)
    actuator_setlevel(self, nwkid, EPout, value, "Light", transitionMoveLevel)

def actuator_identify(self, nwkid, ep, value=None):

    if value is None:
        duration = 15

        self.log.logging(
            "Command",
            "Log",
            "identifySend - send an Identify Message to: %s for %04x seconds" % (nwkid, duration),
            nwkid=nwkid,
        )
        zcl_identify_send( self, nwkid, ep, "%04x" % (duration))
    else:

        self.log.logging("Command", "Log", "value: %s" % value)
        self.log.logging("Command", "Log", "Type: %s" % type(value))

        color = 0x00  # Default
        if value is None or value == 0:
            value = 0x00  # Blink
            if "Manufactuer Name" in self.ListOfDevices and self.ListOfDevices["Manufacturer Name"] == "Legrand":
                value = 0x00  # Flashing
                color = 0x03  # Blue

        zcl_identify_trigger_effect( self, nwkid, ep, "%02x" % value, "%02x" % color)