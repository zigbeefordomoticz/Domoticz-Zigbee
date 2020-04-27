#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: zigateConst.py

    Description: All Constants

"""

# Zigate Endpoint number (by default Zigate works on 01
ZIGATE_EP = '01'

# Heartbeat of plugin set to 5s
HEARTBEAT = 5

# Number of Max Command to be submitted to Zigate
MAX_LOAD_ZIGATE = 4

# Threshold before switching to Busy state. If we have or more than MAX_FOR_ZIGATE_BUZY in the FIFO queue
MAX_FOR_ZIGATE_BUZY = 4

# If there is a need to read more than 4 Attributes at a time, then breakdown the request into several.
MAX_READATTRIBUTES_REQ = 4   # Number of Attributes to be requested via 0x0100

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
        'group':0x01,     # Group
        'short':0x02,     # Short address
        'ieee':0x03,      # IEEE
        'broadcast': 0x04 # Broadcast
        }

PROFILE_ID = {
        0x0104  : 'ZHA', # ZigBee Home Automation
        0x0105  : 'ZBA', # ZigBee Building Automation
        0x0107  : 'ZTS', # ZigBee Telecom Services
        0x0108  : 'ZHC', # ZigBee Health Care
        0x0109  : 'ZSE', # ZigBee Smart Energy
        0x010A  : 'ZRS', # ZigBee Retail Services
        # Propriatory profile
        0xc05e : 'ZLL', # ZigBee Light Link
        0xc2df : '???', # Seen on Centrallite micro door
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
        'data16': 0x09,  # 16bit Data
        'bool'  : 0x10,
        '8bmap' : 0x18,
        '16bmap': 0x19,
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

SIZE_DATA_TYPE = {
        """ 
        For each Data Type, provide the length in number of bytes
        """

        '09': 2,    # 16bit data
        '10': 1,    # Bool
        '18': 1,    # 8bitmap
        '16': 2,    # 16bitmap
        '20': 1,    # uint8
        '21': 2,    # uint16
        '22': 3,    # Uint24
        '23': 4,    # Uint32
        '25': 6,    # Uint48
        '28': 1,    # int8
        '29': 2,    # int16
        '2a': 3,    # int24
        '2b': 4,    # int32
        '2d': 6,    # int48
        '30': 1,    # enum8
        '31': 2,    # enum16
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
        0x000D: 'Consumption Awareness Device',

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

        # Closures
        0x0200: 'Shade',
        0x0201: 'Shade Controller',
        0x0202: 'Window Covering Device',
        0x0203: 'Window Covering Controller',

        # HVAC Devices
        0x0300: 'Heating/Cooling Unit',
        0x0301: 'Thermostat',
        0x0302: 'Temperature Sensor',
        0x0304: 'Pump',
        0x0305: 'Pressure Sensor',
        0x0306: 'Flow Sensor',

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
DOMOTICZ_LED_DIMMERS = { 
        'RGB_W'   : 1,  # RGB + white, either RGB or white can be lit
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

ZCL_CLUSTERS_ACT = {
        '0006', '0008', '0102', '0201', '0201', '0402' }

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
        '000a': 'Time',
        '000c': 'Analog Input (basic)',
        '000d': 'Analog Output (basic)',
        '000e': 'Analog Value (basic)',
        '000f': 'Binary Input (Basic)',
        '0010': 'Binary Output (Basic)',
        '0011': 'Binary Value (Basic)',
        '0012': 'Multistate Input (Basic)',
        '0013': 'Multistate Output (Basic)',
        '0014': 'Multistate Value (Basic)',
        '0015': 'Commissioning',
        '0019': 'Over-the-Air Upgrade',
        '0020': 'Poll Control',
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
        '0403': 'Pressure measurement',
        '0405': 'Relative Humidity Measurement',
        '0406': 'Occupancy Sensing',
        '0500': 'IAS Zone',
        '0501': 'IAS ACE (Ancillary Control Equipment)',
        '0502': 'IAS WD (Warning Device)',
        '0b04': 'Electrical Measurement',
        '0b05': 'Diagnostics',
        '1000': 'Touchlink'
        }

# Zigate Commands, with there sequence of response ( Status + Data)
ZIGATE_COMMANDS = {
        0x0009: {'Sequence': (0x8000, 0x8009), 'Command': 'Get Network State (Firm v3.0d)', 'NwkId 2nd Bytes': False },
        0x0010: {'Sequence': ( ), 'Command': 'Get Version' , 'NwkId 2nd Bytes': False },
        0x0011: {'Sequence': (0x8000,), 'Command': 'Reset' , 'NwkId 2nd Bytes': False },
        0x0012: {'Sequence': (0x8000,), 'Command': 'Erase Persistent Data' , 'NwkId 2nd Bytes': False },
        0x0013: {'Sequence': (0x8000,), 'Command': 'ZLO/ZLL “Factory New” Reset' , 'NwkId 2nd Bytes': False },
        0x0014: {'Sequence': (0x8000, 0x8014), 'Command': 'Permit Join' , 'NwkId 2nd Bytes': False },
        0x0015: {'Sequence': (0x8000, 0x8015), 'Command': 'Get devices list' , 'NwkId 2nd Bytes': False },
        0x0016: {'Sequence': (0x8000,), 'Command': 'Set Time server (v3.0f)' , 'NwkId 2nd Bytes': False },
        0x0017: {'Sequence': (0x8000, 0x8017), 'Command': 'GetTime server (v3.0f)' , 'NwkId 2nd Bytes': False },
        0x0018: {'Sequence': (0x8000,), 'Command': 'SetLed (v3.0f)' , 'NwkId 2nd Bytes': False },
        0x0019: {'Sequence': (0x8000,), 'Command': 'Set Certification (v3.0f)' , 'NwkId 2nd Bytes': False },
        0x0020: {'Sequence': (0x8000,), 'Command': 'Set Expended PANID' , 'NwkId 2nd Bytes': False },
        0x0021: {'Sequence': (0x8000,), 'Command': 'Set Channel Mask' , 'NwkId 2nd Bytes': False },
        0x0022: {'Sequence': (0x8000,), 'Command': 'Set Security State + Key' , 'NwkId 2nd Bytes': False },
        0x0023: {'Sequence': (0x8000,), 'Command': 'Set device Type' , 'NwkId 2nd Bytes': False },
        0x0024: {'Sequence': (0x8000, 0x8024), 'Command': 'Start Network' , 'NwkId 2nd Bytes': False },
        0x0025: {'Sequence': (0x8000,), 'Command': 'Start Network Scan' , 'NwkId 2nd Bytes': False },
        0x0026: {'Sequence': (0x8000,), 'Command': 'Remove Device' , 'NwkId 2nd Bytes': False },
        0x0027: {'Sequence': (0x8000,), 'Command': 'Enable Permissions Controlled Joins' , 'NwkId 2nd Bytes': False },
        0x0028: {'Sequence': (0x8000, 0x8028), 'Command': 'Authenticate Device' , 'NwkId 2nd Bytes': False },
        0x0029: {'Sequence': (0x8000,), 'Command': 'Out of Band Commissioning Data Request' , 'NwkId 2nd Bytes': False },
        0x002B: {'Sequence': (0x8000, 0x802B), 'Command': 'User Descriptor Set' , 'NwkId 2nd Bytes': False },
        0x002C: {'Sequence': (0x8000, 0x802C), 'Command': 'User Descritpor Request' , 'NwkId 2nd Bytes': False },
        0x0531: {'Sequence': (0x8000, 0x8530), 'Command': 'Complex Descriptor request' , 'NwkId 2nd Bytes': False },
        0x0030: {'Sequence': (0x8000, 0x8030), 'Command': 'Bind' , 'NwkId 2nd Bytes': False },
        0x0031: {'Sequence': (0x8000, 0x8031), 'Command': 'Unbind' , 'NwkId 2nd Bytes': False },
        0x0040: {'Sequence': (0x8000, 0x8040), 'Command': 'Network Address request' , 'NwkId 2nd Bytes': False },
        0x0041: {'Sequence': (0x8000, 0x8041), 'Command': 'IEEE Address request' , 'NwkId 2nd Bytes': False },
        0x0042: {'Sequence': (0x8000, 0x8042), 'Command': 'Node Descriptor request' , 'NwkId 2nd Bytes': False },
        0x0043: {'Sequence': (0x8000, 0x8043), 'Command': 'Simple Descriptor request' , 'NwkId 2nd Bytes': False },
        0x0044: {'Sequence': (0x8000, 0x7044), 'Command': 'Power Descriptor request' , 'NwkId 2nd Bytes': False },
        0x0045: {'Sequence': (0x8000, 0x8045), 'Command': 'Active Endpoint request' , 'NwkId 2nd Bytes': False },
        0x0046: {'Sequence': (0x8000, 0x8046), 'Command': 'Match Descriptor request' , 'NwkId 2nd Bytes': False },
        #0x0047: {'Sequence': (0x8000, 0x8047), 'Command': 'Management Leave request' , 'NwkId 2nd Bytes': False },
        0x0047: {'Sequence': (0x8000,), 'Command': 'Management Leave request' , 'NwkId 2nd Bytes': False },
        0x0049: {'Sequence': (0x8000,), 'Command': 'Permit Joining request' , 'NwkId 2nd Bytes': False },
        0x004A: {'Sequence': (0x8000, 0x804A), 'Command': 'Management Network Update request' , 'NwkId 2nd Bytes': False },
        0x004B: {'Sequence': (0x8000, 0x804B), 'Command': 'System Server Discovery request' , 'NwkId 2nd Bytes': False },
        0x004E: {'Sequence': (0x8000, 0x804E), 'Command': 'Management LQI request' , 'NwkId 2nd Bytes': False },

        # Group
        0x0060:{'Sequence': (0x8000, 0x8060), 'Command': 'Group Add' , 'NwkId 2nd Bytes': True },
        0x0061:{'Sequence': (0x8000, 0x8061), 'Command': 'Group View' , 'NwkId 2nd Bytes': True },
        0x0062:{'Sequence': (0x8000, 0x8062), 'Command': 'Get Group membership' , 'NwkId 2nd Bytes': True },
        0x0063:{'Sequence': (0x8000, 0x8063), 'Command': 'Group Remove' , 'NwkId 2nd Bytes': True },
        0x0064:{'Sequence': (0x8000,), 'Command': 'Remove all Groups' , 'NwkId 2nd Bytes': True },
        0x0065:{'Sequence': (0x8000,), 'Command': 'Group Add by Identify' , 'NwkId 2nd Bytes': True },
        
        # Identify
        0x0070: {'Sequence': (0x8000,), 'Command': 'Identify Send' , 'NwkId 2nd Bytes': True },
        0x0071: {'Sequence': (0x8000,), 'Command': 'Identify Query' , 'NwkId 2nd Bytes': True },

        # Action Move
        0x0080: {'Sequence': (0x8000,), 'Command': 'Move to Level' , 'NwkId 2nd Bytes': True },
        0x0081: {'Sequence': (0x8000,), 'Command': 'Move to Level with/without on/off' , 'NwkId 2nd Bytes': True },
        0x0082: {'Sequence': (0x8000,), 'Command': 'Move Step' , 'NwkId 2nd Bytes': True },
        0x0083: {'Sequence': (0x8000,), 'Command': 'Move Stop Move' , 'NwkId 2nd Bytes': True },
        0x0084: {'Sequence': (0x8000,), 'Command': 'Move Stop with On Off' , 'NwkId 2nd Bytes': True },

        # Action ON/OFF
        0x0092: {'Sequence': (0x8000,), 'Command': 'Action ON/OFF' , 'NwkId 2nd Bytes': True },
        0x0093: {'Sequence': (0x8000,), 'Command': 'On/off timed send' , 'NwkId 2nd Bytes': True },
        0x0094: {'Sequence': (0x8000,), 'Command': 'On/off with effects send' , 'NwkId 2nd Bytes': True },

        # Scene


        # Action Hue
        0x00B0: {'Sequence': (0x8000, 0x8002), 'Command': 'Move to Hue' , 'NwkId 2nd Bytes': True },
        0x00B1: {'Sequence': (0x8000, 0x8002), 'Command': 'Move Hue' , 'NwkId 2nd Bytes': True },
        0x00B2: {'Sequence': (0x8000, 0x8002), 'Command': 'Step Hue' , 'NwkId 2nd Bytes': True },
        0x00B3: {'Sequence': (0x8000, 0x8002), 'Command': 'Move to saturation' , 'NwkId 2nd Bytes': True },
        0x00B4: {'Sequence': (0x8000, 0x8002), 'Command': 'Move saturation' , 'NwkId 2nd Bytes': True },
        0x00B5: {'Sequence': (0x8000, 0x8002), 'Command': 'Step saturation' , 'NwkId 2nd Bytes': True },
        0x00B6: {'Sequence': (0x8000, 0x8002), 'Command': 'Move to hue and saturation' , 'NwkId 2nd Bytes': True },
        0x00B7: {'Sequence': (0x8000, 0x8002), 'Command': 'Move to colour' , 'NwkId 2nd Bytes': True },
        0x00B8: {'Sequence': (0x8000, 0x8002), 'Command': 'Move colour' , 'NwkId 2nd Bytes': True },
        0x00B9: {'Sequence': (0x8000, 0x8002), 'Command': 'Step Colour' , 'NwkId 2nd Bytes': True },
        0x00BA: {'Sequence': (0x8000, 0x8002), 'Command': 'Enhaced Move to Hue' , 'NwkId 2nd Bytes': True },
        0x00BB: {'Sequence': (0x8000, 0x8002), 'Command': 'Enhanced Move Hue' , 'NwkId 2nd Bytes': True },
        0x00BC: {'Sequence': (0x8000, 0x8002), 'Command': 'Enhanced Step Hue' , 'NwkId 2nd Bytes': True },
        0x00BD: {'Sequence': (0x8000, 0x8002), 'Command': 'Enhanced Move to hue and saturation' , 'NwkId 2nd Bytes': True },
        0x00BE: {'Sequence': (0x8000, 0x8002), 'Command': 'Colour Loop Set' , 'NwkId 2nd Bytes': True },
        0x00BF: {'Sequence': (0x8000, 0x8002), 'Command': 'Stop Move Step' , 'NwkId 2nd Bytes': True },

        # Action Color
        0x00C0: {'Sequence': (0x8000, 0x8002), 'Command': 'Move to colour temperature' , 'NwkId 2nd Bytes': True },
        0x00C1: {'Sequence': (0x8000, 0x8002), 'Command': 'Move colour temperature' , 'NwkId 2nd Bytes': True },
        0x00C2: {'Sequence': (0x8000, 0x8002), 'Command': 'Step colour temperature' , 'NwkId 2nd Bytes': True },

        # Action Touchlink
        0x00D0: {'Sequence': (0x8000,), 'Command': 'Initiate Touchlink' , 'NwkId 2nd Bytes': True },
        0x00D2: {'Sequence': (0x8000,), 'Command': 'Touch link factory reset target' , 'NwkId 2nd Bytes': True },

        # Identify Trigger Effect
        0x00E0: {'Sequence': (0x8000, 0x8002), 'Command': 'Identify Trigger Effect' , 'NwkId 2nd Bytes': True },

        # Action Lock/Unlock Door
        0x00F0: {'Sequence': (0x8000, 0x8002), 'Command': 'Lock Unlock door' , 'NwkId 2nd Bytes': True },

        # Windows Covering
        0x00FA: {'Sequence': (0x8000, 0x8002), 'Command': 'Windows covering (v3.0f)' , 'NwkId 2nd Bytes': True },

        # Action Attribute
        ##0x0100: {'Sequence': (0x8000, 0x8100), 'Command': 'Read Attribute Request' , 'NwkId 2nd Bytes': True },
        0x0100: {'Sequence': (0x8000,), 'Command': 'Read Attribute Request' , 'NwkId 2nd Bytes': True },
        0x0110: {'Sequence': (0x8000, 0x8110), 'Command': 'Write Attribute Request' , 'NwkId 2nd Bytes': True },
        0x0111: {'Sequence': (0x8000, 0x8002), 'Command': 'IAS WD mode' , 'NwkId 2nd Bytes': True },
        0x0112: {'Sequence': (0x8000, 0x8002), 'Command': 'IAS WD Squawk' , 'NwkId 2nd Bytes': True },
        0x0120: {'Sequence': (0x8000, 0x8120), 'Command': 'Configure Reporting Request' , 'NwkId 2nd Bytes': True },
        0x0140: {'Sequence': (0x8000, 0x8140), 'Command': 'Attribute Discovery request' , 'NwkId 2nd Bytes': False },

        # Miscaleneous
        0x0530: {'Sequence': (0x8000,), 'Command': 'Raw APS Data Request' , 'NwkId 2nd Bytes': False },
        0x0806: {'Sequence': (0x8000,), 'Command': 'AHI Control' , 'NwkId 2nd Bytes': False },

        # PDM response
        0x8200 : {'Sequence': ( ),'Command': 'PDM Save Request', 'NwkId 2nd Bytes': False },
        0x8201 : {'Sequence': ( ),'Command': 'PDM Load Request', 'NwkId 2nd Bytes': False },
        0x8202 : {'Sequence': ( ),'Command': 'PDM ', 'NwkId 2nd Bytes': False },
        0x8203 : {'Sequence': ( ),'Command': 'PDM ', 'NwkId 2nd Bytes': False },
        0x8204 : {'Sequence': ( ),'Command': 'PDM Create Bitmap', 'NwkId 2nd Bytes': False },
        0x8205 : {'Sequence': ( ),'Command': 'PDM Delete Bitmap', 'NwkId 2nd Bytes': False },
        0x8206 : {'Sequence': ( ),'Command': 'PDM Get Bitmap', 'NwkId 2nd Bytes': False },
        0x8207 : {'Sequence': ( ),'Command': 'PDM Inc Bitmap', 'NwkId 2nd Bytes': False },
        0x8208 : {'Sequence': ( ),'Command': 'PDM Existance Request', 'NwkId 2nd Bytes': False },
        0x8300 : {'Sequence': ( ),'Command': 'Ack PDM Hosts Available', 'NwkId 2nd Bytes': False }
    }

# Zigate command to be retransmited by Transport if expected Data not received
RETRANSMIT_COMMAND = (
            # ON/OFF
            0x0092, 0x0093, 0x0094,
            # Level Control
            0x0080, 0x0081, 0x0082, 0x0083, 0x0084
            )

# ZIGATE REPONSES not related to a Zigate command
ZIGATE_RESPONSES = {
        0x0400: 'IAS Zone enroll response',
        0x8401: 'Zone status change notification',
        0x8001: 'Log Message',
        0x8003: '',
        0x8004: '',
        0x8005: '',
        0x8006: 'Non Factory new Restart',
        0x8007: 'Factory New Restart',
        0x8011: '',
        0x8048: 'Leave Indication',
        0x8085: 'Level Update',
        0x8095: 'ON/OFF Update',
        0x8101: 'Default response',
        0x8102: 'Report Individual Attribute response',
        0x8701: 'Router Disocver',
        0x8702: 'APS Data Confirm Fail',
        0x004D: 'Device Annouce' 
        }

# Used in output/thermostat_Mode
SYSTEM_MODE = { 'Off' : 0x00 ,
        'Auto' : 0x01 ,
        'Reserved' : 0x02,
        'Cool' : 0x03,
        'Heat' :  0x04,
        'Emergency Heating' : 0x05,
        'Pre-cooling' : 0x06,
        'Fan only' : 0x07 }

# Used in onCommand
THERMOSTAT_LEVEL_2_MODE = {
    0 : 'Off',
    10: 'Auto',
    20: 'Cool',
    30: 'Heat',
    40: 'Emergency Heating',
    }

THERMOSTAT_MODE_2_LEVEL = {
        0x00: '00', # Off
        0x01: '10', # Auto
        0x03: '20', # Cool
        0x04: '30', # Heat
        0x05: '40'  # Force Heat
        }

# Ordered List - Important for binding
CLUSTERS_LIST = [ 
        'fc00',  # Private cluster Philips Hue - Required for Remote
        '0500',            # IAS Zone
        '0406',            # Occupancy Sensing
        '0400',            # Illuminance Measurement
        '0402',            # Temperature Measurement
        '0001',            # Power Configuration
        '0019',            # OTA 
        '0009',            # Alarm
        '000f',            # Binary Input (Basic)
        '0100',            # Shade Configuration
        '0102',            # Windows Covering / SHutter
        '0403',            # Measurement: Pression atmospherique
        '0405',            # Relative Humidity Measurement
        '0702',            # Smart Energy Metering
        '0006',            # On/Off
        '0502',            # IAS WD Zone
        '0008',            # Level Control
        '0201',            # Thermostat
        '0204',            # Thermostat UI
        '0300',            # Colour Control
        '0000',            # Basic
        '0b04',             # Electrical Meansurement
        'ff02',             # Used by Xiaomi devices for battery informations.
        'fc21'              # Cluster Profalux PFX
        ]

LEGRAND_REMOTES = ( 'Remote switch', 'Double gangs remote switch', 'Shutters central remote switch')
LEGRAND_REMOTE_SWITCHS = ( 'Remote switch', 'Double gangs remote switch')
LEGRAND_REMOTE_SHUTTER = ( 'Shutters central remote switch', )


CFG_RPT_ATTRIBUTESbyCLUSTERS = {
    # 0xFFFF sable reporting- # 6460   - 6 hours # 0x0E10 - 3600s A hour # 0x0708 - 30' # 0x0384 - 15' # 0x012C - 5' # 0x003C - 1'
    # Datatype   
    #   10 - Boolean - 8bit #   18 - 8bitmap #   19 - 16bitmap #   20 - BbitUint #   21 - 16bitUint #   25 - 48bitUnint #   29 - 16BitInt
    #   2a - 24bitInt #   30 - 8bitenum #   31 - 16bitenum

    # Power Cluster
    '0001': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'012C', 'MaxInterval':'FFFE', 'TimeOut':'0000','Change':'0001'},
                             '0020': {'DataType': '29', 'MinInterval':'0E10', 'MaxInterval':'0E10', 'TimeOut':'0000','Change':'0001'},
                             '0021': {'DataType': '21', 'MinInterval':'0E10', 'MaxInterval':'0E10', 'TimeOut':'0000','Change':'01'}}},

    # On/Off Cluster
    '0006': {'Attributes': { '0000': {'DataType': '10', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0000','Change':'01'}}},

    # Level Control Cluster
    '0008': {'Attributes': { '0000': {'DataType': '20', 'MinInterval':'0005', 'MaxInterval':'012C', 'TimeOut':'0000','Change':'05'}}},

    # Windows Covering
    '0102': {'Attributes': { '0003': {'DataType': '21', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0000','Change':'0001'},
                             '0004': {'DataType': '21', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0000','Change':'0001'},
                             '0008': {'DataType': '20', 'MinInterval':'0001', 'MaxInterval':'0384', 'TimeOut':'0000','Change':'01'},
                             '0009': {'DataType': '20', 'MinInterval':'0001', 'MaxInterval':'0384', 'TimeOut':'0000','Change':'01'}}},
 
    # Thermostat
    '0201': {'Attributes': { '0000': {'DataType': '29', 'MinInterval':'012C', 'MaxInterval':'012C', 'TimeOut':'0000','Change':'0001'},
                             '0008': {'DataType': '29', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0000','Change':'0001'},
                             '0012': {'DataType': '29', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0000','Change':'0001'},
                             '0014': {'DataType': '29', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0000','Change':'0001'}}},

    # Colour Control
    '0300': {'Attributes': { '0003': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0000','Change':'0001', 'ZDeviceID':{ "010D", "0210", "0200"}}, # Color X
                             '0004': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0000','Change':'0001', 'ZDeviceID':{ "010D", "0210", "0200"}}, # Color Y
                             '0007': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0000','Change':'0001', 'ZDeviceID':{ "0102", "010D", "0210", "0220"}}, # Color Temp
                             '0008': {'DataType': '30', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0000','Change':'01', 'ZDeviceID':{ }}}}, # Color Mode
 
    # Illuminance Measurement
    '0400': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'0005', 'MaxInterval':'012C', 'TimeOut':'0000','Change':'000F'}}},

    # Temperature
    '0402': {'Attributes': { '0000': {'DataType': '29', 'MinInterval':'000A', 'MaxInterval':'012C', 'TimeOut':'0000','Change':'0001'}}},
 
    # Pression Atmo
    '0403': {'Attributes': { '0000': {'DataType': '20', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0000','Change':'01'},
                             '0010': {'DataType': '29', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0000','Change':'0001'}}},
    # Humidity
    '0405': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0000','Change':'0001'}}},

    # Occupancy Sensing
    '0406': {'Attributes': { '0000': {'DataType': '18', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0000','Change':'01'},
 
    # Sensitivy for HUE Motion
                             '0030': {'DataType': '20', 'MinInterval':'0005', 'MaxInterval':'1C20', 'TimeOut':'0000','Change':'01'}}},
 
    # IAS ZOne
    '0500': {'Attributes': { '0000': {'DataType': '30', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0000','Change':'01'},
                             '0001': {'DataType': '31', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0000','Change':'0001'},
                             '0002': {'DataType': '19', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0000','Change':'0001'}}},

    # IAS Warning Devices
    '0502': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0000','Change':'0001'}}},


    # Power
    '0702': {'Attributes': { 
                            '0000': {'DataType': '25', 'MinInterval':'FFFF', 'MaxInterval':'0000', 'TimeOut':'0000','Change': '000000000000000a'},
                            '0400': {'DataType': '2a', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0000','Change': '0000000a'}}},

    # Electrical Measurement
    '0b04': {'Attributes': {
                            '0505': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0000','Change':'0001'},
                            '0508': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0000','Change':'0001'},
                            '050b': {'DataType': '29', 'MinInterval':'0005', 'MaxInterval':'012C', 'TimeOut':'0000','Change':'0001'}}}
}