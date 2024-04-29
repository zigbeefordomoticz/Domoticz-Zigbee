#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

# Cluster 0xef00
# Commands
#   Direction: Coordinator -> Device 0x00 SetPoint
#   Direction: Device -> Coordinator 0x01
#   Direction: Device -> Coordinator 0x02 Setpoint command response

TUYA_MANUF_CODE = "1002"

TS0002_RELAY_SWITCH_MANUF = ( "_TZ3000_zmy4lslw", "_TZ3000_01gpyda5", "_TZ3000_bvrlqyj7", "_TZ3000_7ed9cqgi", )
TS0003_RELAY_SWITCH_MANUF = ( "_TZ3000_odzoiovu", )

#   "_TZE200_i48qyn9s" : tuyaReadRawAPS ,

TS011F_MANUF_NAME = ("_TZ3000_wamqdr3f", "_TZ3000_ksw8qtmt", "_TZ3000_amdymr7l" )
TS0041_MANUF_NAME = ("_TZ3000_xkwalgne", "_TZ3000_peszejy7", "_TZ3000_8kzqqzu4", "_TZ3000_tk3s5tyg")

# Tuya Smart Lock
# TY0A01
TUYA_SMART_DOOR_LOCK_MODEL = ( "TY0A01", )
TUYA_SMART_DOOR_LOCK_MANUF = ( "_TYST12_qcdc4vui", )

# TS0601
TUYA_WATER_TIMER = ("_TZE200_htnnfasr", "_TZE200_akjefhj5", "_TZE200_81isopgh",)
TUYA_ENERGY_MANUFACTURER = (
    "_TZE200_fsb6zw01",
    "_TZE200_byzdayie",
    "_TZE200_ewxhg6o9"
)
TUYA_GARAGE_DOOR = ( "_TZE200_nklqjk62", )
TUYA_SMARTAIR_MANUFACTURER = (
    "_TZE200_8ygsuhe1",
    "_TZE200_yvx5lh6k",
    "_TZE200_dwcarsat",
)

TUYA_MOTION = (
    "_TZE200_bh3n6gk8",
    '_TZE200_3towulqd', 
    '_TZE200_1ibpyhdc'
)

TUYA_TEMP_HUMI = ( 
    "_TZE200_qyflbnbj",
    "_TZE200_bjawzodf", 
    "_TZE200_bq5c8xfe", 
    "_TZE200_qoy0ekbd",
    "_TZE200_whkgqxse"
)

TUYA_SIREN_MANUFACTURER = (
    "_TZE200_d0yu2xgi",
    "_TYST11_d0yu2xgi",
)
TUYA_SIREN_MODEL = (
    "TS0601",
    "0yu2xgi",
)

TUYA_DIMMER_MANUFACTURER = (
    "_TZE200_dfxkcots", 
    )

TUYA_2GANGS_DIMMER_MANUFACTURER = (
    "_TZE200_e3oitdyu",
)
TUYA_SWITCH_MANUFACTURER = ( "_TZE200_7tdtqgwv", "_TZE200_oisqyl4o", "_TZE200_amp6tsvy", )
TUYA_2GANGS_SWITCH_MANUFACTURER = ("_TZE200_g1ib5ldv",)
TUYA_3GANGS_SWITCH_MANUFACTURER = ("_TZE200_oisqyl4o",)

TUYA_SMART_ALLIN1 = ( "_TZ3210_jijr1sss", )
TUYA_CURTAIN_MAUFACTURER = (
    "_TZE200_cowvfni3",
    "_TZE200_wmcdj3aq",
    "_TZE200_fzo2pocs",
    "_TZE200_nogaemzt",
    "_TZE200_5zbp6j0u",
    "_TZE200_fdtjuw7u",
    "_TZE200_bqcqqjpb",
    "_TZE200_zpzndjez",
    "_TYST11_cowvfni3",
    "_TYST11_wmcdj3aq",
    "_TYST11_fzo2pocs",
    "_TYST11_nogaemzt",
    "_TYST11_5zbp6j0u",
    "_TYST11_fdtjuw7u",
    "_TYST11_bqcqqjpb",
    "_TYST11_zpzndjez",
    "_TZE200_rddyvrci",
    "_TZE200_nkoabg8w",
    "_TZE200_xuzcvlku",
    "_TZE200_4vobcgd3",
    "_TZE200_pk0sfzvr",
    "_TYST11_xu1rkty3",
    "_TZE200_zah67ekd",
)

TUYA_CURTAIN_MODEL = (
    "owvfni3",
    "mcdj3aq",
    "zo2pocs",
    "ogaemzt",
    "zbp6j0u",
    "dtjuw7u",
    "qcqqjpb",
    "pzndjez",
)

TUYA_THERMOSTAT_MANUFACTURER = (
    "_TZE200_aoclfnxz",
    "_TYST11_zuhszj9s",
    "_TYST11_jeaxp72v",
    "_TZE200_dzuqwsyg"    # https://www.domoticz.com/forum/viewtopic.php?p=290066#p290066
)
#TUYA_eTRV1_MANUFACTURER = (
#    "_TZE200_kfvq6avy",
#    "_TZE200_ckud7u2l",
#    "_TYST11_KGbxAXL2",
#    "_TYST11_ckud7u2l",
#)

TUYA_SMOKE_MANUFACTURER = (
    "_TZE200_ntcy3xu1",
)

# https://github.com/zigpy/zigpy/discussions/653#discussioncomment-314395
TUYA_eTRV1_MANUFACTURER = (
    "_TYST11_zivfvd7h",
    "_TZE200_zivfvd7h",
    "_TYST11_kfvq6avy",
    "_TZE200_kfvq6avy",
    "_TYST11_jeaxp72v",
    "_TZE200_cwnjrr72",
)
TUYA_eTRV2_MANUFACTURER = (
    "_TZE200_ckud7u2l",
    "_TYST11_ckud7u2l",
    "_TZE200_ckud7u2l",
    "_TZE200_ywdxldoj",
    "_TZE200_do5qy8zo",
    "_TZE200_cwnjrr72",
    "_TZE200_pvvbommb",
    "_TZE200_9sfg7gm0", 
    "_TZE200_2atgpdho", 
    "_TZE200_cpmgn2cf",
    "_TZE200_8thwkzxl",
    "_TZE200_4eeyebrt",
    "_TZE200_8whxpsiw",
    "_TZE200_xby0s3ta", 
    "_TZE200_7fqkphoq",
    "_TZE200_gd4rvykv", 
)
TUYA_eTRV3_MANUFACTURER = (
    "_TZE200_c88teujp",
    "_TYST11_KGbxAXL2",
    "_TYST11_zuhszj9s",
    "_TZE200_azqp6ssj",
    "_TZE200_yw7cahqs",
    "_TZE200_9gvruqf5",
    "_TZE200_zuhszj9s",
    "_TZE200_2ekuz3dz",
)
TUYA_eTRV4_MANUFACTURER = (
    "_TZE200_b6wax7g0",  
)

TUYA_eTRV5_MANUFACTURER = (
    "_TZE200_7yoranx2",   # model: 'TV01-ZB',           vendor: 'Moes'
    "_TZE200_e9ba97vf",   # MODEL : 'TV01-ZB',          vendor: 'Moes'
    "_TZE200_hue3yfsn",   # MODEL : 'TV02-Zigbee',      vendor: 'TuYa'
    "_TZE200_husqqvux",   # MODEL : 'TSL-TRV-TV01ZG',   vendor: 'Tesla Smart
    "_TZE200_kly8gjlz",   # 
    "_TZE200_lnbfnyxd",   # MODEL : 'TSL-TRV-TV01ZG',   vendor: 'Tesla Smart'
    '_TZE200_kds0pmmv',   # MODEL : 'TV01-ZB',          vendor: 'Moes'
    "_TZE200_mudxchsu",   # MODEL : 'TV05-ZG curve',    vendor: 'TuYa'
    "_TZE200_kds0pmmv",   # MODEL : 'TV01-ZB',          vendor: 'Moes'
    "_TZE200_lllliz3p",   # MODEL : 'TV02-Zigbee',      vendor: 'TuYa'
)

TUYA_eTRV_MANUFACTURER = (
    "_TYST11_2dpplnsn",
    "_TZE200_wlosfena",
    "_TZE200_fhn3negr",
    "_TZE200_qc4fpmcn",
)


TUYA_eTRV_MODEL = (
    "TS0601",
    "TS0601-eTRV",
    "TS0601-eTRV1",
    "TS0601-eTRV2",
    "TS0601-eTRV3",
    "TS0601-eTRV5",
    "TS0601-_TZE200_b6wax7g0",      # BRT-100  MOES by Tuya
    "TS0601-_TZE200_chyvmhay",      # Lidl Valve
    "TS0601-thermostat",
    "TS0601-_TZE200_dzuqwsyg",      # Tuya Thermostat with Cooling & Fan control (mapped to "TS0601-thermostat-Coil")
    "uhszj9s",
    "GbxAXL2",
    "88teujp",
    "kud7u2l",
    "eaxp72v",
    "fvq6avy",
    "ivfvd7h",
)

eTRV_MODELS = {
    # Thermostat
    "TS0601-thermostat": "TS0601-thermostat",
    "TS0601-_TZE200_dzuqwsyg": "TS0601-thermostat-Coil",
    
    # Siterwell GS361A-H04
    "ivfvd7h": "TS0601-eTRV1",
    "fvq6avy": "TS0601-eTRV1",
    "eaxp72v": "TS0601-eTRV1",
    "TS0601-eTRV1": "TS0601-eTRV1",
    
    # Moes HY368 / HY369
    "kud7u2l": "TS0601-eTRV2",
    "TS0601-eTRV2": "TS0601-eTRV2",
    
    # Saswell SEA802 / SEA801 Zigbee versions
    "88teujp": "TS0601-eTRV3",
    "GbxAXL2": "TS0601-eTRV3",
    "uhszj9s": "TS0601-eTRV3",
    "TS0601-eTRV3": "TS0601-eTRV3",
    
    # 
    "TS0601-eTRV5": "TS0601-eTRV5",
    # MOES BRT-100
    "TS0601-_TZE200_b6wax7g0": "TS0601-_TZE200_b6wax7g0",
    
    # Lidl Valve
    "TS0601-_TZE200_chyvmhay": "TS0601-_TZE200_chyvmhay"
    
}

TUYA_TS0601_MODEL_NAME = TUYA_eTRV_MODEL + TUYA_CURTAIN_MODEL + TUYA_SIREN_MODEL + TUYA_SMOKE_MANUFACTURER + TUYA_TEMP_HUMI + TUYA_MOTION
TUYA_MANUFACTURER_NAME = (
    TUYA_ENERGY_MANUFACTURER
    + TS011F_MANUF_NAME
    + TS0041_MANUF_NAME
    + TUYA_SIREN_MANUFACTURER
    + TUYA_DIMMER_MANUFACTURER
    + TUYA_SWITCH_MANUFACTURER
    + TUYA_2GANGS_SWITCH_MANUFACTURER
    + TUYA_3GANGS_SWITCH_MANUFACTURER
    + TUYA_CURTAIN_MAUFACTURER
    + TUYA_THERMOSTAT_MANUFACTURER
    + TUYA_eTRV1_MANUFACTURER
    + TUYA_eTRV2_MANUFACTURER
    + TUYA_eTRV3_MANUFACTURER
    + TUYA_eTRV4_MANUFACTURER
    + TUYA_eTRV5_MANUFACTURER
    + TUYA_eTRV_MANUFACTURER
    + TUYA_SMARTAIR_MANUFACTURER
    + TUYA_WATER_TIMER
    + TUYA_SMART_ALLIN1
    + TUYA_GARAGE_DOOR
    + TUYA_SMOKE_MANUFACTURER
    + TUYA_TEMP_HUMI
    + TUYA_MOTION
    + TUYA_SMART_DOOR_LOCK_MANUF
)
