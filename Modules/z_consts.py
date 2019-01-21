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
PROFILE_ID = 0x0104
ZHA_DEVICES = {
        # Generic Devices
        0x0000: 'On/Off Switch',
        0x0002: 'On/Off Output',
        0x0006: 'Remote Control',
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
