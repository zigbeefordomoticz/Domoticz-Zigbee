#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: badz & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Class PluginConf

Description: Import the PluginConf.txt file and initialized each of the available parameters in this file
Parameters not define in the PluginConf.txt file will be set to their default value.

"""

import json
import os.path
import time
from pathlib import Path

import Domoticz
from Modules.domoticzAbstractLayer import getConfigItem, setConfigItem
from Modules.tools import is_domoticz_db_available, is_hex

SETTINGS = {
    "Services": {
        "Order": 1,
        "param": {
            "MatomoOptIn": {"type": "bool","default": 1,"current": None,"restart": 0,"hidden": False,"Advanced": False,},
            "enablegroupmanagement": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": False, },
            "enableReadAttributes": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": True, "Advanced": True, },
            "internetAccess": { "type": "bool", "default": 1, "current": None, "restart": 1, "hidden": False, "Advanced": False, },
            "CheckSSLCertificateValidity": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": False, },
            "allowOTA": { "type": "bool", "default": 1, "current": None, "restart": 1, "hidden": True, "Advanced": False, },
            "pingDevices": { "type": "bool", "default": 1, "current": None, "restart": 1, "hidden": False, "Advanced": True, },
            "PluginAnalytics": { "type": "bool", "default": -1, "current": None, "restart": 0, "hidden": True, "Advanced": False, },
            "DomoticzCustomMenu": { "type": "bool", "default": 1, "current": None, "restart": 1, "hidden": False, "Advanced": False, },
            "NightShift": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, }
        },
    },
    "GroupManagement": {
        "Order": 2,
        "param": {
            "GroupOnBattery": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "OnIfOneOn": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "forceGroupDeviceRefresh": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "reComputeGroupState": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "allowGroupMembership": { "type": "bool", "default": 1, "current": None, "restart": True, "hidden": False, "Advanced": True, },
            "zigatePartOfGroupTint": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "ZigpyRadio": "ezsp" },
            "zigatePartOfGroup0000": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "ZigpyRadio": "ezsp" },
            "TradfriKelvinStep": { "type": "int", "default": 51, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "pingViaGroup": { "type": "hex", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
        },
    },
    "Zigpy": {
        "Order": 4,
        "param": {    
            "Konke": {"type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, },
            "Livolo": {"type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True,},
            "Orvibo": {"type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True,},
            "Terncy": {"type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True,},
            "Wiser": {"type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, },
            "Wiser2": {"type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True,},
            "OverWriteCoordinatorIEEEOnlyOnce": {"type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "ZigpyRadio": "ezsp"},
            "autoBackup": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "autoRestore": {"type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True,},
            "ZigpyTopologyReport": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "ZigpyTopologyReportAutoBackup": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "CaptureRxFrames": {"type": "bool","default": 0,"current": None,"restart": 1,"hidden": False,"Advanced": True,},
            "CaptureTxFrames": {"type": "bool","default": 0,"current": None,"restart": 1,"hidden": False,"Advanced": True,},
            "enableZclDuplicatecheck": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": False,"Advanced": True,},
            "BackupFullDevices": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False,"ZigpyRadio": "znp" },
            "ForceAPSAck": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "EzspAllowUnsecuredRejoins": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "ZigpyRadio": "ezsp" },
            "BellowsNoMoreEndDeviceChildren": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "ZigpyRadio": "ezsp" },
            "zigpySourceRouting": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, },
            "forceZigpy_noasyncio": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "EnergyScanAtStatup": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
        }
    },
    # OTA Related parameters
    "OTA": {
        "Order": 5,
        "param": {   
            "autoServeOTA": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "EnableOTATracing": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "checkFirmwareAgainstZigbeeOTARepository": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "ZigbeeOTA_Repository":{ "type": "path", "default": "https://raw.githubusercontent.com/Koenkk/zigbee-OTA/master/index.json", "current": None, "restart": 1, "hidden": False, "Advanced": True, },
            "IkeaTradfri_Repository":{ "type": "path", "default": "http://fw.ota.homesmart.ikea.net/feed/version_info.json", "current": None, "restart": 1, "hidden": False, "Advanced": True, },
            "Sonoff_Repository":{ "type": "path", "default": "https://zigbee-ota.sonoff.tech/releases/upgrade.json", "current": None, "restart": 1, "hidden": False, "Advanced": True, },
        }  
    },
    "Provisioning": {
        "Order": 6,
        "param": {
            "TuyaMagicRead": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "LegrandCompatibilityMode": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "enableSchneiderWiser": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "ConfigureReportingChunk": { "type": "int", "default": 3, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "AqaraOppleBulbMode": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "reenforcementWiser": { "type": "int", "default": 300, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "ReadAttributeChunk": { "type": "int", "default": 3, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "ZiGateConfigureReporting": {"type": "bool","default": 1,"current": None,"restart": 0,"hidden": False,"Advanced": True,"ZigpyRadio": ""},
            "bindingDelay": {"type": "int","default": 0.75,"current": None,"restart": 0,"hidden": False,"Advanced": True},
            "pairingCommandsDelay": {"type": "int","default": 0,"current": None,"restart": 0,"hidden": False,"Advanced": True},
        },
    },
    "WebInterface": {
        "Order": 7,
        "param": {
            "TopologyV2": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "Sibling": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": True, "Advanced": True, "ZigpyRadio": "" },
            "Lang": { "type": "str", "default": "en-US", "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "numTopologyReports": { "type": "int", "default": 4, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "numEnergyReports": { "type": "int", "default": 4, "current": None, "restart": 0, "hidden": False, "Advanced": False, "ZigpyRadio": "", },
            "enableGzip": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "enableDeflate": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "enableChunk": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "enableKeepalive": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "enableCache": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
        },
    },
    # Device Management
    "DeviceManagement": {
        "Order": 8,
        "param": {
            "deviceOffWhenTimeOut": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "forcePollingAfterAction": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "forcePassiveWidget": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "allowForceCreationDomoDevice": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "ForceDeviceTimedOut_afterXhours": { "type": "int", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "resetPluginDS": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "resetConfigureReporting": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, },
            "checkConfigurationReporting": { "type": "int", "default": 75600, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "resetReadAttributes": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, },
            "resetMotiondelay": { "type": "int", "default": 30, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "resetSwitchSelectorPushButton": { "type": "int", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "forceSwitchSelectorPushButton": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "doUnbindBind": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "allowReBindingClusters": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "TrackingEraticValue": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
        },
    },
    # Zigate Configuration
    "CoordinatorConfiguration": {
        "Order": 9,
        "param": {
            "blueLedOnOff": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "pingDevicesFeq": { "type": "int", "default": 3600, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "resetPermit2Join": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, },
            "Ping": {"type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True},
            "allowRemoveZigateDevice": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": True, "Advanced": True, "ZigpyRadio": "" },
            "eraseZigatePDM": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, "ZigpyRadio": "" },
            "Certification": { "type": "list", "list": {"CE regulation": "CE", "FCC regulation": "FCC"}, "default": "CE", "current": None, "restart": True, "hidden": False, "Advanced": False, "ZigpyRadio": "" },
            "CertificationCode": { "type": "int", "default": 1, "current": None, "restart": 1, "hidden": True, "Advanced": False, "ZigpyRadio": "" },
            "channel": { 
                "type": "list",
                "list": { 
                    "default": 0, 
                    "11": 11, "12": 12, "13": 13, "14": 14, "15": 15, "16": 16, 
                    "17": 17, "18": 18, "19": 19, "20": 20, "21": 21, "22": 22, 
                    "23": 23, "24": 24, "25": 25, "26": 26, 
                    },
                "default": "0",
                "current": None,
                "restart": 2,
                "hidden": False,
                "Advanced": True,
                },
            "TXpower_set": { "type": "list", "list": {"0dbM": 0, "-9 dbM": 1, "-20dbM": 2, "-32dbM": 3}, "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, },
            "extendedPANID": { "type": "hex", "default": 0, "current": None, "restart": 3, "hidden": False, "Advanced": True, },
            "forceClosingAllNodes": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, },
        },
    },
    # Command Transitionin tenth of seconds
    "CommandTransition": {
        "Order": 10,
        "param": {
            "GrpfadingOff": { "type": "list", "list": {"default": 0, "50% fade, 12s to off": 1, "20% dim up, 1s off": 2, "No fade": 255}, "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "GrpmoveToHueSatu": { "type": "int", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": False, },
            "GrpmoveToColourTemp": { "type": "int", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "GrpmoveToColourRGB": { "type": "int", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "GrpmoveToLevel": { "type": "int", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
            "GroupLevelWithOnOff": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": False, },
        },
    },
    # Plugin Transport
    "PluginTransport": {
        "Order": 11,
        "param": {
            "disableAckOnZCL": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "waitForResponse": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "byPassDzConnection": { "type": "bool", "default": 1, "current": None, "restart": 1, "hidden": True, "Advanced": True, },
            "SerialReadV2": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "forceFullSeqMode": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "RawReadAttribute": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "RawWritAttribute": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "writerTimeOut": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
        },
    },
    # Plugin Directories
    "PluginConfiguration": {
        "Order": 12,
        "param": {
            "PosixPathUpdate": {"type": "bool","default": 1,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "storeDomoticzDb": {"type": "bool","default": 1,"current": None,"restart": 0,"hidden": False,"Advanced": True,},
            "useDomoticzDb": {"type": "bool","default": 1,"current": None,"restart": 0,"hidden": False,"Advanced": True,},
            "PluginLogMode": {"type": "list","list": { "system default": 0, "0600": 0o600, "0640": 0o640, "0644": 0o644},"default": 0,"current": None,"restart": 1,"hidden": False,"Advanced": True,},
            "numDeviceListVersion": {"type": "int","default": 12,"current": None,"restart": 0,"hidden": False,"Advanced": False,},
            "filename": { "type": "path", "default": "", "current": None, "restart": 1, "hidden": True, "Advanced": True, },
            "pluginHome": { "type": "path", "default": "", "current": None, "restart": 1, "hidden": True, "Advanced": True, },
            "homedirectory": { "type": "path", "default": "", "current": None, "restart": 1, "hidden": True, "Advanced": True, },
            "pluginData": {"type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True,},
            "pluginConfig": {"type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True,},
            "pluginOTAFirmware": {"type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True,},
            "pluginReports": {"type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True,},
            "pluginWWW": {"type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True,},
            "pluginLogs": {"type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True,},
            "SSLCertificate": {"type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True,},
            "SSLPrivateKey": {"type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True,},
        },
    },
    # Verbose
    "VerboseLogging": {
        "Order": 13,
        "param": { 
            "AbstractDz": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Barometer": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "BatteryManagement": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "BasicOutput": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Binding": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "CasaIA": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Chameleon": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Cluster": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Command": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ConfigureReporting": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "CustomDevicePolling": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Danfoss": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "DNS": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "DZDB": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            
            "GammaTroniques": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Database": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "DeviceAnnoucement": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "DeviceParameter": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Enki": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Flow": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Garbage": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True },
            "Gledopto": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Groups": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Heartbeat": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Heiman": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Humidity": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "IAS": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "IAS_ACE": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Ikea": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Illuminance": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Input": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "LQIthreshold": { "type": "int", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False },
            "Legrand": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ListImportedModules": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Livolo": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Lumi": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "MatchingNwkId": { "type": "str", "default": "ffff", "current": None, "restart": 0, "hidden": False, "Advanced": False },
            "Matomo": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "MemoryLeak": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Electric": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "NXPExtendedErrorCode": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "NetworkEnergy": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "NetworkMap": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Namron": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Occupancy": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "OTA": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Orvibo": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "PDM": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Pairing": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Philips": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "PiZigate": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Plugin": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "PluginTools": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Pluzzy": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "PollControl": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Profalux": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ZigpyDefaultLoggingInfo": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False }, 
            "Python/aiosqlite": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True }, 
            "Python/zigpy": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True }, 
            "Python/zigpy-appdb": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True }, 
            "Python/zigpy-application": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True }, 
            "Python/zigpy-backups": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True }, 
            "Python/zigpy-device": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Python/zigpy-endpoint": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True }, 
            "Python/zigpy-group": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True }, 
            "Python/zigpy-listeners": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True }, 
            "Python/zigpy-state": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True }, 
            "Python/zigpy-topology": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Python/zigpy-util": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Python/zigpy-config": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Python/zigpy-ota": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Python/zigpy-profiles": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Python/zigpy-quirks": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Python/zigpy-zcl": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True }, 
            "Python/zigpy-zdo": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Python/Classes-ZigpyTransport-AppGeneric": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },

            "ReadAttributes": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "StopProcess": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Schneider": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Sonoff": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Sunricher": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },

            "Temperature": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Thermostats": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "thermoSettings": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "thermoUISettings": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },

            "ThreadCommunication": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ThreadDomoticz": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ThreadForwarder": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ThreadWriter": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Timing": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": True, "Advanced": True },
            "TimeServer": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },

            "Transport": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Transport8000": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Transport8002": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Transport8011": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Transport8012": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "TransportError": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "TransportFrwder": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "TransportPluginEncoder": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "TransportProto": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "TransportRder": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "TransportSerial": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "TransportTcpip": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "TransportWrter": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "TransportZigpy": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Tuya": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Tuya0601": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "TuyaTS011F": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "WebUIReactTime": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "WebServer": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Widget": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "WidgetCreation": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "WidgetUpdate": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "WidgetLevel3": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "WidgetReset": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "WriteAttributes": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ZLinky": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ZclClusters": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ZiGateReactTime": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ZigpyReactTime": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Zigpy": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ZigpyBLZ": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ZigpyEZSP": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ZigpyTopology": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ZigpyZNP": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ZigpyZigate": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "ZigpydeCONZ": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "coordinatorCmd": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "enablePluginLogging": { "type": "bool", "default": 1, "current": None, "restart": 1, "hidden": False, "Advanced": False },
            "inRawAPS": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "iasSettings": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "logDeviceUpdate": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": False },
            "logFORMAT": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True },
            "logThreadName": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False },
            "loggingBackupCount": { "type": "int", "default": 7, "current": None, "restart": 1, "hidden": False, "Advanced": False },
            "loggingMaxMegaBytes": { "type": "int", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": False },
            "occupancySettings": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "onoffSettings": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "outRawAPS": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "showTimeOutMsg": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "tuyaSettings": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "trackTransportError": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False },
            "trackZclClustersIn": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False },
            "trackZclClustersOut": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False },
            "trackZdpClustersIn": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False },
            "trackZdpClustersOut": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False },
            "z4dCertifiedDevices": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "zclCommand": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "zclDecoder": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "zdpCommand": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "zdpDecoder": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "zigateCommand": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True }
        },
    },
    # Others
    "Others": {
        "Order": 14,
        "param": {
        },
    },
    "Patching": {
        "Order": 15,
        "param": {
            "Bug566": {"type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True}
        },
    },
    # Experimental
    "Experimental": {
        "Order": 16,
        "param": {
            "reconnectonIEEEaddr": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "reconnectonNWKaddr": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "disableZCLDefaultResponse": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "ControllerInHybridMode": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "ControllerInRawMode": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": False,"Advanced": True,},
            "nPDUaPDUThreshold": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,"ZigpyRadio": ""},
            "forceAckOnZCL": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "DropBadAnnoucement": {"type": "bool","default": 1,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "expJsonDatabase": {"type": "bool","default": 1,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "TryFindingIeeeOfUnknownNwkid": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "enableZigpyPersistentInFile": {"type": "bool","default": 0,"current": None,"restart": 1,"hidden": False,"Advanced": True,},
            "enableZigpyPersistentInMemory": {"type": "bool","default": 1,"current": None,"restart": 1,"hidden": False,"Advanced": True,},
            "EventLoopInstrumentation": {"type": "bool","default": 1,"current": None,"restart": 1,"hidden": False,"Advanced": True,},
        },
    },
    "Reserved": {
        "Order": 99,
        "param": {
            # Just for compatibility keep it but hidden ( move to Custom device "Param" section)
            "CheckRequirements": {"type": "bool","default": 1,"current": None,"restart": 0,"hidden": True,"Advanced": True},
            "nPDUaPDUThreshold": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,"ZigpyRadio": ""},
            "rebindLivolo": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "allowAutoPairing": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "disabledDefaultResponseFirmware": {"type": "bool","default": 0,"current": None,"restart": 1,"hidden": True,"Advanced": True,},
            "logUnknownDeviceModel": {"type": "bool","default": 1,"current": None,"restart": 0,"hidden": True,"Advanced": True,},     
            "expJsonDatabase": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "forceAckOnZCL": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "ControllerInHybridMode": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "ControllerInRawMode": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "disableZCLDefaultResponse": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "AnnoucementV0": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "AnnoucementV1": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "AnnoucementV2": {"type": "bool","default": 1,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "pollingPhilips": {"type": "int","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "pollingGledopto": {"type": "int","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "pollingSchneider": {"type": "int","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "pollingBlitzwolfPower": {"type": "int","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "pollingLumiPower": {"type": "int","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "pollingCasaiaAC201": {"type": "int","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "PhilipsPowerOnAfterOffOn": {"type": "list","list": {"Off": 0, "On": 1, "Previous": 255},"default": 1,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "EnkiPowerOnAfterOffOn": {"type": "list","list": {"Off": 0, "On": 1, "Previous": 255},"default": 1,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "IkeaPowerOnAfterOffOn": {"type": "list","list": {"Off": 0, "On": 1, "Previous": 255},"default": 1,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            # Polling
            "polling0000": {"type": "int","default": 86400,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0001": {"type": "int","default": 86400,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0002": {"type": "int","default": 86400,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "pollingONOFF": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "pollingLvlControl": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling000c": {"type": "int","default": 3600,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0019": {"type": "int","default": 86400,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0100": {"type": "int","default": 3600,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0020": {"type": "int","default": 3600,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0101": {"type": "int","default": 3600,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0102": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0201": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0202": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0204": {"type": "int","default": 86400,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0300": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0400": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0402": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0403": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0405": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0406": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0500": {"type": "int","default": 86400,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0502": {"type": "int","default": 86400,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0702": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0b01": {"type": "int","default": 86400,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0b04": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "pollingff66": {"type": "int","default": 3661,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "pollingff42": {"type": "int","default": 86400,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling0b05": {"type": "int","default": 86400,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "polling000f": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "pollingfc00": {"type": "int","default": 300,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "pollingfcc0": {"type": "int","default": 300,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "pollingfc01": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "pollingfc11": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "pollingfc21": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "pollingfc40": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "pollingfc7d": {"type": "int","default": 900,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "EnableLedIfOn": {"type": "bool","default": 1,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "EnableLedInDark": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "EnableLedShutter": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "EnableDimmer": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "InvertShutter": {"type": "bool","default": 1,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "EnableReleaseButton": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
            "LegrandPowerOnAfterOffOn": {"type": "list","list": {"Off": 0, "On": 1, "Previous": 255},"default": 1,"current": None,"restart": 0,"hidden": True,"Advanced": False,},
        },
    },
}


class PluginConf:
    def __init__(self, zigbee_communication, VersionNewFashion, DomoticzMajor, DomoticzMinor, homedir, hardwareid):

        self.pluginConf = {}
        self.homedir = homedir
        self.hardwareid = hardwareid
        self.pluginConf["pluginHome"] = homedir.rstrip("/").rstrip("\\")
        self.VersionNewFashion = VersionNewFashion
        self.DomoticzMajor = DomoticzMajor
        self.DomoticzMinor = DomoticzMinor
        self.zigbee_communication = zigbee_communication 

        setup_folder_parameters(self, homedir)

        _pluginConf = Path(self.pluginConf["pluginConfig"] )
        self.pluginConf["filename"] = str( _pluginConf / ("PluginConf-%02d.json" % hardwareid) )
        if os.path.isfile( _pluginConf / ("PluginConf-%02d.json" % hardwareid)):
            _load_Settings(self)

        else:
            _load_oldfashon(self, homedir, hardwareid)

        if self.zigbee_communication == "zigpy":
            zigpy_setup(self)
            
        # Reset eraseZigatePDM to default
        self.pluginConf["eraseZigatePDM"] = 0
        # Sanity Checks
        if self.pluginConf["TradfriKelvinStep"] < 0 or self.pluginConf["TradfriKelvinStep"] > 255:
            self.pluginConf["TradfriKelvinStep"] = 75
        if self.pluginConf["Certification"] != "FCC":
            self.pluginConf["CertificationCode"] = 0x01  # CE
        else:
            self.pluginConf["CertificationCode"] = 0x02  # FCC
        _path_check(self)
        _param_checking(self)


    def write_Settings(self):
        """ Serialize json format the pluginConf """

        _pluginConf = Path(self.pluginConf["pluginConfig"] )
        pluginConfFile = _pluginConf / ("PluginConf-%02d.json" % self.hardwareid)
        self.pluginConf["filename"] = str(pluginConfFile)

        write_pluginConf = {}
        for theme in SETTINGS:
            for param in SETTINGS[theme]["param"]:
                if self.pluginConf[param] != SETTINGS[theme]["param"][param]["default"]:
                    if SETTINGS[theme]["param"][param]["type"] == "hex":
                        if isinstance( self.pluginConf[param], str):
                            write_pluginConf[param] = "%X" % int(self.pluginConf[param],16)
                        else:
                            write_pluginConf[param] = "%X" % self.pluginConf[param]
                    else:
                        write_pluginConf[param] = self.pluginConf[param]

        with open(pluginConfFile, "wt") as handle:
            json.dump(write_pluginConf, handle, sort_keys=True, indent=2)

        if is_domoticz_db_available(self) and (self.pluginConf["useDomoticzDb"] or self.pluginConf["storeDomoticzDb"]):
            setConfigItem(Key="PluginConf", Value={"TimeStamp": time.time(), "b64Settings": write_pluginConf})


def _load_Settings(self):
    """ Load PluginConf from json file """

    dz_timestamp = 0
    if is_domoticz_db_available(self):
        _domoticz_pluginConf = getConfigItem(Key="PluginConf")
        dz_timestamp = _domoticz_pluginConf.get("TimeStamp",0)
        _domoticz_pluginConf = _domoticz_pluginConf.get("b64Settings",{})

        if dz_timestamp != 0:
            Domoticz.Log(
                "Plugin data loaded where saved on %s"
                % (time.strftime("%A, %Y-%m-%d %H:%M:%S", time.localtime(dz_timestamp)))
            )
        if not isinstance(_domoticz_pluginConf, dict):
            _domoticz_pluginConf = {}

    txt_timestamp = 0
    if os.path.isfile(self.pluginConf["filename"]):
        txt_timestamp = os.path.getmtime(self.pluginConf["filename"])
    Domoticz.Log("%s timestamp is %s" % (self.pluginConf["filename"], txt_timestamp))

    if dz_timestamp < txt_timestamp:
        Domoticz.Log("Dz PluginConf is older than Json Dz: %s Json: %s" % (dz_timestamp, txt_timestamp))
        # We should load the json file

    with open(self.pluginConf["filename"], "rt") as handle:
        _pluginConf = {}
        try:
            _pluginConf = json.load(handle)

        except json.decoder.JSONDecodeError as e:
            Domoticz.Error("poorly-formed %s, not JSON: %s" % (self.pluginConf["filename"], e))
            return

        for param in _pluginConf:
            self.pluginConf[param] = _pluginConf[param]

    # Check Load
    if is_domoticz_db_available(self) and self.pluginConf["useDomoticzDb"]:
        Domoticz.Log("PluginConf Loaded from Dz: %s from Json: %s" % (len(_domoticz_pluginConf), len(_pluginConf)))
        if _domoticz_pluginConf:
            for x in _pluginConf:
                if x not in _domoticz_pluginConf:
                    Domoticz.Error("-- %s is missing in Dz" % x)
                elif _pluginConf[x] != _domoticz_pluginConf[x]:
                    Domoticz.Error(
                        "++ %s is different in Dz: %s from Json: %s" % (x, _domoticz_pluginConf[x], _pluginConf[x])
                    )

    # Overwrite Zigpy parameters if we are running native Zigate
    if self.zigbee_communication != "zigpy":
        # Force to 0 as this parameter is only relevant to Zigpy
        self.pluginConf["ZigpyTopologyReport"] = False


def _load_oldfashon(self, homedir, hardwareid):
    """
    Locate and import legacy plugin configuration files.

    This internal method searches for a legacy `PluginConf.txt` file within the
    plugin configuration directory and imports it into the current configuration
    structure using `_import_oldfashon_param()`.

    The search order supports backward compatibility with multiple naming
    patterns derived from the `hardwareid`, such as:
      - PluginConf-<hardwareid:02d>.txt
      - PluginConf-<hardwareid:2d>.txt
      - PluginConf.txt

    If no legacy file is found, a default configuration file is created by
    calling `self.write_Settings()`.

    Parameters
    ----------
    homedir : str or Path
        Base directory for the plugin home. Currently unused but may be
        required for compatibility with earlier versions.
    hardwareid : int
        The numeric hardware identifier used to locate a matching configuration
        file (e.g., `PluginConf-01.txt`).

    Side Effects
    -------------
    - Reads and parses legacy configuration files if present.
    - Updates `self.pluginConf["filename"]` with the resolved file path.
    - May modify `self.pluginConf` contents through `_import_oldfashon_param()`.
    - Creates a default settings file if none exists.

    """
    # Locate legacy PluginConf file (supporting multiple naming variants)
    _filename = Path(self.pluginConf["pluginConfig"]) / ("PluginConf-%02d.txt" % hardwareid)
    if not os.path.isfile(_filename):
        _filename = Path(self.pluginConf["pluginConfig"]) / ("PluginConf-%2d.txt" % hardwareid)
        if not os.path.isfile(_filename):
            _filename = Path(self.pluginConf["pluginConfig"]) / "PluginConf.txt"
            if not os.path.isfile(_filename):
                self.write_Settings()
                self.pluginConf["filename"] = str(_filename)
                return

    # Read legacy configuration file content
    temp_pluginconf_data = ""
    if not os.path.isfile(_filename):
        return

    with open(_filename, "r") as myPluginConfFile:
        temp_pluginconf_data += myPluginConfFile.read().replace("\n", "")

    # Record filename and import data
    self.pluginConf["filename"] = str(_filename)
    _import_oldfashon_param(self, temp_pluginconf_data, self.pluginConf["filename"])


def _import_oldfashon_param(self, temp_pluginconf_data, filename):
    """
    Import and convert legacy plugin configuration data.

    This internal method loads old-format configuration data (previously stored
    as a Python dictionary literal) and converts it into the structured format
    expected by the current plugin version. It parses the raw configuration
    text using `eval()`, then normalizes each parameter according to its type
    definition in the global `SETTINGS` dictionary.

    The method logs detailed errors when parsing or type conversion fails, and
    falls back to default parameter values when needed.

    Parameters
    ----------
    temp_pluginconf_data : str
        Raw text content of the legacy configuration file, expected to represent
        a Python dictionary (e.g., "{'param1': 'value1', 'param2': 42}").
    filename : str
        Name or path of the file being imported, used for logging purposes.

    Side Effects
    -------------
    - Updates `self.pluginConf` in place with imported or default values.
    - Calls `self.write_Settings()` after import completion.
    - Logs errors and warnings via `Domoticz.Error()`.

    Notes
    -----
    - This method is intended for backward compatibility only and should not be
      used for new configuration files.
    - The function uses `eval()` to parse legacy data; in modern code, prefer
      `json.loads()` for safer deserialization.
    - The method validates parameter types according to `SETTINGS` definitions:
        * `"hex"` values are converted from hexadecimal string to int.
        * `"int"` and `"bool"` values are cast from string digits.
        * `"path"` and `"str"` are assigned directly.

    """
    try:
        plugin_conf_dict = eval(temp_pluginconf_data)
    except SyntaxError:
        Domoticz.Error("Syntax Error in %s, all plugin parameters set to default" % filename)
    except (NameError, TypeError, ZeroDivisionError):
        Domoticz.Error("Error while importing %s, all plugin parameters set to default" % filename)
    else:
        for theme in SETTINGS:
            for param in SETTINGS[theme]["param"]:
                if plugin_conf_dict.get(param):
                    if SETTINGS[theme]["param"][param]["type"] == "hex":
                        if is_hex(plugin_conf_dict.get(param)):
                            self.pluginConf[param] = int(plugin_conf_dict[param], 16)
                        else:
                            Domoticz.Error(
                                "Wrong parameter type for %s, keeping default %s"
                                % (param, self.pluginConf[param]["default"])
                            )
                            self.pluginConf[param] = self.pluginConf[param]["default"]

                    elif SETTINGS[theme]["param"][param]["type"] in ("bool", "int"):
                        if plugin_conf_dict.get(param).isdigit():
                            self.pluginConf[param] = int(plugin_conf_dict[param])
                        else:
                            Domoticz.Error(
                                "Wrong parameter type for %s, keeping default %s"
                                % (param, self.pluginConf[param]["default"])
                            )
                            self.pluginConf[param] = self.pluginConf[param]["default"]

                    elif SETTINGS[theme]["param"][param]["type"] in ("path", "str"):
                        self.pluginConf[param] = plugin_conf_dict[param]

    self.write_Settings()


def _path_check(self):
    """
    Validate and normalize all path-type configuration parameters.

    This internal method iterates over all parameters defined in `SETTINGS`
    and checks those with type `"path"`. It verifies that each configured path:
      - Exists on the filesystem (unless it is an SSL certificate or key).
      - Uses a normalized `Path` representation consistent with POSIX style.
      - Is not a URL (entries containing "http" are skipped).

    If the current path differs from its normalized form and
    `self.pluginConf["PosixPathUpdate"]` is enabled, the path is updated
    automatically. Otherwise, an error is logged.

    Side Effects
    -------------
    - May modify entries in `self.pluginConf` if path normalization occurs.
    - Logs messages via `Domoticz.Status()` or `Domoticz.Error()`.
    - Calls `self.write_Settings()` if any updates were made.

    Notes
    -----
    - The `SSLCertificate` and `SSLPrivateKey` paths are exempt from
      existence checks.
    - URL-based paths (those containing "http") are ignored.

    """
    update_done = False
    for theme in SETTINGS:
        for param in SETTINGS[theme]["param"]:
            if SETTINGS[theme]["param"][param]["type"] != "path":
                continue

            if "http" in self.pluginConf[param]:
                # Skip URL paths
                continue

            _path_name = Path(self.pluginConf[param])

            if (
                param not in ("SSLCertificate", "SSLPrivateKey")
                and not os.path.exists(_path_name)
            ):
                Domoticz.Error(f"Cannot access path: {_path_name}")

            if self.pluginConf[param] != str(_path_name):
                if self.pluginConf["PosixPathUpdate"]:
                    Domoticz.Status(f"Updating path from {self.pluginConf[param]} to {_path_name}")
                    self.pluginConf[param] = str(_path_name)
                    update_done = True
                else:
                    Domoticz.Error(
                        f"Updating path from {self.pluginConf[param]} to {_path_name} "
                        f"is required, but no backward compatibility"
                    )

    if update_done:
        self.write_Settings()


def _param_checking(self):
    """
    Validate and normalize plugin configuration parameters.

    This internal method compares each parameter in `self.pluginConf` against
    its definition in the global `SETTINGS` structure. If a parameter value
    differs from its default, it performs type validation and normalization:
    - Parameters defined as `"hex"` are converted from hexadecimal string
      to integer form if necessary.
    - Other parameters are left as-is.

    After normalization, the method logs the final assigned values using
    `Domoticz.Status()`.

    Side Effects
    -------------
    - May convert parameter values in `self.pluginConf` (e.g., from str → int).
    - Produces log output via `Domoticz.Status()` for each non-default value.

    Notes
    -----
    Parameters whose current value matches the default are skipped.

    """
    # Validate and normalize configuration types
    for theme in SETTINGS:
        for param in SETTINGS[theme]["param"]:
            if self.pluginConf[param] == SETTINGS[theme]["param"][param]["default"]:
                continue

            if SETTINGS[theme]["param"][param]["type"] == "hex":
                if isinstance(self.pluginConf[param], str):
                    self.pluginConf[param] = int(self.pluginConf[param], 16)
                Domoticz.Status("%s set to 0x%x" % (param, self.pluginConf[param]))
            else:
                Domoticz.Status("%s set to %s" % (param, self.pluginConf[param]))


def zigpy_setup(self):
    """
    Initialize or update Zigpy-specific configuration parameters in SETTINGS.

    This method ensures that the Zigpy-related parameter `TXpower_set` is
    correctly defined in the global `SETTINGS` structure. If found, its
    definition is overwritten with a standardized parameter schema that
    specifies type, default value, and associated metadata.

    The method does not return anything but mutates the `SETTINGS` dictionary
    in place.

    Side Effects
    -------------
    Updates the `SETTINGS` global dictionary by assigning a new configuration
    structure to the `TXpower_set` parameter.

    """
    for theme in SETTINGS:
        for param in SETTINGS[theme]["param"]:
            if param == "TXpower_set":
                SETTINGS[theme]["param"][param] = {
                    "type": "int",
                    "default": 0,
                    "current": None,
                    "restart": 0,
                    "hidden": False,
                    "Advanced": True,
                }

                               
def setup_folder_parameters(self, homedir):
    """
    Initialize and populate the plugin configuration folder paths.

    This method iterates over the predefined `SETTINGS` structure and updates
    the `self.pluginConf` dictionary with all relevant folder paths required
    by the plugin (e.g., configuration, data, logs, OTA firmware, SSL certs).

    Depending on the parameter name, paths are either derived from the given
    `homedir` argument or built relative to `pluginHome`.

    Parameters
    ----------
    homedir : str or Path
        The base home directory path for the plugin. Used to resolve the
        `homedirectory` configuration entry.

    Side Effects
    -------------
    Updates `self.pluginConf` in place, adding or overwriting keys defined
    under `SETTINGS[theme]["param"]`.

    Notes
    -----
    - The following parameters are dynamically resolved relative to
      `pluginHome`: pluginConfig, pluginData, pluginLogs, pluginOTAFirmware,
      pluginReports, pluginWWW, SSLCertificate, SSLPrivateKey.
    - Parameters not explicitly handled will be assigned their default value
      as defined in `SETTINGS`.

    """
    for theme in SETTINGS:
        for param in SETTINGS[theme]["param"]:
            if param == "pluginHome":
                continue

            if param == "homedirectory":
                self.pluginConf[param] = str(Path(homedir))

            elif param == "pluginConfig":
                self.pluginConf[param] = str(Path(self.pluginConf["pluginHome"]) / "Conf")

            elif param == "pluginData":
                self.pluginConf[param] = str(Path(self.pluginConf["pluginHome"]) / "Data")

            elif param == "pluginLogs":
                self.pluginConf[param] = str(Path(self.pluginConf["pluginHome"]) / "Logs")

            elif param == "pluginOTAFirmware":
                self.pluginConf[param] = str(Path(self.pluginConf["pluginHome"]) / "OTAFirmware")

            elif param == "pluginReports":
                self.pluginConf[param] = str(Path(self.pluginConf["pluginHome"]) / "Reports")

            elif param == "pluginWWW":
                self.pluginConf[param] = str(Path(self.pluginConf["pluginHome"]) / "www")

            elif param == "SSLCertificate":
                self.pluginConf[param] = str(Path(self.pluginConf["pluginHome"]) / "certs" / "server.crt")

            elif param == "SSLPrivateKey":
                self.pluginConf[param] = str(Path(self.pluginConf["pluginHome"]) / "certs" / "server.key")

            else:
                self.pluginConf[param] = SETTINGS[theme]["param"][param]["default"]
