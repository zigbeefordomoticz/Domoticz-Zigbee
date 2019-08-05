#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_consts.py

    Description: All Constants

"""

HEARTBEAT = 5
MAX_LOAD_ZIGATE = 2

CERTIFICATION = {
        0x01:'CE',
        0x02:'FCC'}

CERTIFICATION_CODE = {
        'CE': 0x01,
        'FCC': 0x02 }

# SQN 1st UINT8 except for 0x8000 where it is the 2nd Uint8
SQN_ANSWERS = ( 0x8401, 0x8000, 0x802B, 0x802C, 0x8030, 0x8031, 0x8034, 
        0x8040, 0x8041, 0x8042, 0x8043, 0x8044, 0x8045, 0x8047, 0x804A,
        0x804B, 0x804E, 0x8060, 0x8061, 0x8062, 0x8063, 0x80A0, 0x80A1,
        0x80A2, 0x80A3, 0x80A4, 0x80A6, 0x8100, 0x8101, 0x8002, 0x8110,
        0x8120 )

ADDRESS_MODE = { 'bound':0x00, 
        'group':0x01, # Group
        'short':0x02, # Short address
        'ieee':0x03 # IEEE
        }

PROFILE_ID = {
        0xc05e : 'ZLL', # ZigBee Light Link
        0x104  : 'ZHA', # ZigBee Home Automation
        0x105  : 'ZBA', # ZigBee Building Automation
        0x107  : 'ZTS', # ZigBee Telecom Services
        0x108  : 'ZHC', # ZigBee Health Care
        0x109  : 'ZSE', # ZigBee Smart Energy
        0x10A  : 'ZRS'  # ZigBee Retail Services
        }

# Used maninly for Attributes Read/Write

ZHA_DATA_TYPE = {
    '''
    decodeAttribute( Attribute Type, Attribute Data )
    Will return an int converted in str, which is the decoding of Attribute Data base on Attribute Type
    Here after are the DataType and their DataType code
    ZigBee_NoData = 0x00, ZigBee_8BitData = 0x08, ZigBee_16BitData = 0x09, ZigBee_24BitData = 0x0a,
    ZigBee_32BitData = 0x0b, ZigBee_40BitData = 0x0c, ZigBee_48BitData = 0x0d, ZigBee_56BitData = 0x0e,
    ZigBee_64BitData = 0x0f, ZigBee_Boolean = 0x10, ZigBee_8BitBitMap = 0x18, ZigBee_16BitBitMap = 0x19,
    ZigBee_24BitBitMap = 0x1a, ZigBee_32BitBitMap = 0x1b, ZigBee_40BitBitMap = 0x1c, ZigBee_48BitBitMap = 0x1d,
    ZigBee_56BitBitMap = 0x1e, ZigBee_64BitBitMap = 0x1f, ZigBee_8BitUint = 0x20, ZigBee_16BitUint = 0x21,
    ZigBee_24BitUint = 0x22, ZigBee_32BitUint = 0x23, ZigBee_40BitUint = 0x24, ZigBee_48BitUint = 0x25,
    ZigBee_56BitUint = 0x26, ZigBee_64BitUint = 0x27, ZigBee_8BitInt = 0x28, ZigBee_16BitInt = 0x29,
    ZigBee_24BitInt = 0x2a, ZigBee_32BitInt = 0x2b, ZigBee_40BitInt = 0x2c, ZigBee_48BitInt = 0x2d,
    ZigBee_56BitInt = 0x2e, ZigBee_64BitInt = 0x2f, ZigBee_8BitEnum = 0x30, ZigBee_16BitEnum = 0x31,
    ZigBee_OctedString = 0x41, ZigBee_CharacterString = 0x42, ZigBee_LongOctedString = 0x43, ZigBee_LongCharacterString = 0x44,
    ZigBee_TimeOfDay = 0xe0, ZigBee_Date = 0xe1, ZigBee_UtcTime = 0xe2, ZigBee_ClusterId = 0xe8,
    ZigBee_AttributeId = 0xe9, ZigBee_BACNetOId = 0xea, ZigBee_IeeeAddress = 0xf0, ZigBee_128BitSecurityKey = 0xf1
    '''

        'nodata': 0x00,  # Bytestream 
        'bool'  : 0x10,
        '8bmap' : 0x16,
        'uint8' : 0x20,  # B
        'uchar' : 0x20,  # B
        'Uint16': 0x21,  # H
        'Uint24': 0x22,  # I
        'Uint32': 0x23,
        'Uint48': 0x25,
        'int8'  : 0x28,  # b
        'int16' : 0x29,  # h
        'int24' : 0x2a,  # i
        'int32' : 0x2b,
        'int48' : 0x2d,
        'enum8' : 0x30,  # b
        'enum16': 0x31,
        'Xfloat': 0x39,  # f
        'string': 0x42   # s
             }


ZLL_DEVICES = {
        # https://www.nxp.com/docs/en/user-guide/JN-UG-3091.pdf
        0x0000: 'On/Off Light', 
        0x0010: 'On/Off Plug',
        0x0100: 'Dimmable Light',
        0x0110: 'Dimmabe Plug',
        0x0200: 'Colour Light',
        0x0210: 'Extended Colour Light',
        0x0220: 'Colour Temperature Light',
        0x0800: 'Colour Controller',
        0x0810: 'Colour Scene Controller',
        0x0820: 'Non-Colour Controller',
        0x0830: 'Non-Colour Scene Controller',
        0x0840: 'Control Bridge',
        0x0850: 'On/Off sensor'}



# https://www.nxp.com/docs/en/user-guide/JN-UG-3076.pdf
ZHA_DEVICES = {
        # Generic Devices
        0x0000: 'On/Off Switch',
        0x0001: 'levelControlSwitch',
        0x0002: 'On/Off Output',
        0x0003: 'levelControllableOutput',
        0x0004: 'sceneSelector',
        0x0005: 'configurationTool',
        0x0006: 'Remote Control',
        0x0007: 'configurationTool',
        0x0008: 'rangeExtender',
        0x0009: 'mainsPowerOutlet',
        0x000A: 'Door Lock',
        0x000B: 'Door Lock Controller',
        0x000C: 'Smart Plug',

        # Lighting Devices
        0x0100: 'On/Off Light',
        0x0101: 'Dimmable Light',
        0x0102: 'Colour Dimable Light',
        0x0103: 'On/Off Light Switch',
        0x0104: 'Dimmer Switch',
        0x0105: 'Colour Dimmer Switch',
        0x0106: 'Light Sensor',
        0x0107: 'Occupancy Sensor',
        0x010C: 'White Color Temperature Light',
        0x010D: 'Extended Color Light',

        # HVAC Devices
        0x0301: 'Thermostat',

        # Intruder Alam System (IAS) Devices
        0x0400: 'IAS Control and Indicating Equipment',
        0x0401: 'IAS Ancillary Control Equipment',
        0x0402: 'IAS Zone',
        0x0403: 'IAS Warning Device'
        }

#Color Attributes
COLOR_TEMPERATURE = 0x0007
ENHANCED_CURRENT_HUE = 0x4000
CURRENT_SAT = 0x0001
CURRENT_X = 0x0003
CURRENT_Y = 0x0004
COLOR_MODE = 0x0008
COLOR_LOOP_ACTIVE = 0x4002

COLOUR_MODE_HUE_SAT = 0x00
COLOUR_MODE_XY = 0x01
COLOUR_MODE_TEMP = 0x02

# ProfileID versus Color mode
BULB_ACTIONS = {
    0x0105 : ('HUE',),
    0x010D : ('COLOR' , 'HUE', 'TEMP'),
    0x0210 : ('COLOR' , 'HUE', 'TEMP'),
    0x0102 : ('TEMP',),
    0x010C : ('TEMP',),
    0x0220 : ('TEMP',),
    0x0200 : ('HUE', 'COLOR')
}

# Possible Widget SubType 
DOMOTICZ_LED_DIMMERS = { 'RGB_W'   : 1,  # RGB + white, either RGB or white can be lit
                         'RGB'     : 2,  # RGB
                         'White'   : 3,  # Monochrome White
                         'RGB_CW_W': 4,  # RGB + cold white + warm white, either RGB or white can be lit
                         'RGB_W_Z' : 6,  # Like RGBW, but allows combining RGB and white
                         'RGB_CW_WW_Z' : 7, # Like RGBWW, but allows combining RGB and white
                         'CW_WW'   : 8  # Cold white + Warm white
                       }

DOMOTICZ_COLOR_MODE = {
    0 : 'Illegal',
    1 : 'White',
    2 : 'White with color temperature',
    3 : 'Color RGB',
    4 : 'Custom Color + White',
    9998: 'With saturation and hue'
}


ZCL_CLUSTERS_LIST = {
        '0000': 'Basic',
        '0001': 'Power Configuration',
        '0003': 'Identify',
        '0004': 'Groups',
        '0005': 'Scenes',
        '0006': 'On/Off',
        '0007': 'On/Off Switch Configuration',
        '0008': 'Level Control',
        '0009': 'Alarms',
        '000A': 'Time',
        '000C': 'Analog Input (basic)',
        '000D': 'Analog Output (basic)',
        '000E': 'Analog Value (basic)',
        '000F': 'Binary Input (Basic)',
        '0010': 'Binary Output (Basic)',
        '0011': 'Binary Value (Basic)',
        '0012': 'Multistate Input (Basic)',
        '0013': 'Multistate Output (Basic)',
        '0014': 'Multistate Value (Basic)',
        '0015': 'Commissioning',
        '0019': 'Over-the-Air Upgrade',
        '0100': 'Shade Configuration',
        '0101': 'Door Lock',
        '0102': 'Window Covering',
        '0201': 'Thermostat',
        '0202': 'Fan Control',
        '0204': 'Thermostat User Interface Configuration',
        '0300': 'Colour Control',
        '0400': 'Illuminance Measurement',
        '0401': 'Illuminance Level Sensing',
        '0402': 'Temperature Measurement',
        '0405': 'Relative Humidity Measurement',
        '0406': 'Occupancy Sensing',
        '0500': 'IAS Zone',
        '0501': 'IAS ACE (Ancillary Control Equipment)',
        '0502': 'IAS WD (Warning Device)',
        '1000': 'Touchlink'
        }


