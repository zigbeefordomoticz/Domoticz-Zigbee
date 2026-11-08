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

import ast
import json
import os.path
import time
from pathlib import Path

import DomoticzEx as Domoticz

from Modules.domoticzAbstractLayer import getConfigItem, setConfigItem
from Modules.tools import is_hex

SETTINGS = {
    "Services": {
        "Order": 1,
        "param": {
            "MatomoOptIn": { "type": "bool","default": 1,"current": None,"restart": 0,"hidden": False,"Advanced": False, "Group": "Internet", "DependsOn": "internetAccess", },
            "enablegroupmanagement": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": False, "Group": "Features", },
            "enableNativeScenes": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": False, "Group": "Features", },
            "enableReadAttributes": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": True, "Advanced": True, },
            "internetAccess": { "type": "bool", "default": 1, "current": None, "restart": 1, "hidden": False, "Advanced": False, "Group": "Internet", },
            "CheckSSLCertificateValidity": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "Domoticz", },
            "allowOTA": { "type": "bool", "default": 1, "current": None, "restart": 1, "hidden": True, "Advanced": False, },
            "pingDevices": { "type": "bool", "default": 1, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "DevicePing", },
            "pingDevicesFeq": { "type": "int", "default": 3600, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "DevicePing", "Unit": "s", "Min": 300, "Max": 86400, "Step": 60, "DependsOn": "pingDevices", },
            "PluginAnalytics": { "type": "bool", "default": -1, "current": None, "restart": 0, "hidden": True, "Advanced": False, },
            "DomoticzCustomMenu": { "type": "bool", "default": 1, "current": None, "restart": 1, "hidden": False, "Advanced": False, "Group": "Domoticz", },
            "NightShift": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "Features", }
        },
    },
    "GroupManagement": {
        "Order": 2,
        "param": {
            "GroupOnBattery": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "GroupState", "DependsOn": "enablegroupmanagement", },
            "OnIfOneOn": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "GroupState", "DependsOn": "enablegroupmanagement", },
            "forceGroupDeviceRefresh": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "GroupState", "DependsOn": "enablegroupmanagement", },
            "reComputeGroupState": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "GroupState", "DependsOn": "enablegroupmanagement", },
            "allowGroupMembership": { "type": "bool", "default": 1, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "Membership", "DependsOn": "enablegroupmanagement", },
            "zigatePartOfGroupTint": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "ZigpyRadio": "ezsp", "Group": "Membership", "DependsOn": "enablegroupmanagement", },
            "zigatePartOfGroup0000": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "ZigpyRadio": "ezsp", "Group": "Membership", "DependsOn": "enablegroupmanagement", },
            "TradfriKelvinStep": { "type": "int", "default": 51, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "Remotes", "Min": 1, "Max": 255, "Step": 1, "DependsOn": "enablegroupmanagement", },
            "pingViaGroup": { "type": "hex", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "Remotes", "DependsOn": "enablegroupmanagement", },
        },
    },
    "Zigpy": {
        "Order": 4,
        "param": {    
            "Konke": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "ManufacturerQuirks", },
            "Livolo": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "ManufacturerQuirks", },
            "Orvibo": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "ManufacturerQuirks", },
            "Terncy": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "ManufacturerQuirks", },
            "Wiser": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "ManufacturerQuirks", },
            "Wiser2": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "ManufacturerQuirks", },
            "OverWriteCoordinatorIEEEOnlyOnce": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "ZigpyRadio": "ezsp", "Group": "Radio", "Danger": True, },
            "autoBackup": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "Backup", },
            "autoRestore": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "Backup", "DependsOn": "autoBackup", },
            "ZigpyTopologyReport": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "Topology", },
            "ZigpyTopologyReportAutoBackup": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "Topology", "DependsOn": "ZigpyTopologyReport", },
            "ZigpyTopologyAssociatedDevices": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "Topology", "DependsOn": "ZigpyTopologyReport", },
            "ZigpyAutoTopology": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "Topology", },
            "MonitorLoopLatency": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "Diagnostics", },
            "CaptureRxFrames": { "type": "bool","default": 0,"current": None,"restart": 1,"hidden": False,"Advanced": True, "Group": "Diagnostics", },
            "CaptureTxFrames": { "type": "bool","default": 0,"current": None,"restart": 1,"hidden": False,"Advanced": True, "Group": "Diagnostics", },
            "enableZclDuplicatecheck": { "type": "bool","default": 0,"current": None,"restart": 0,"hidden": False,"Advanced": True, "Group": "Diagnostics", },
            "ForceAPSAck": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "EzspAllowUnsecuredRejoins": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "ZigpyRadio": "ezsp", "Group": "Radio", },
            "BellowsNoMoreEndDeviceChildren": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "ZigpyRadio": "ezsp", "Group": "Radio", },
            "zigpySourceRouting": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "Radio", },
            "GreenPowerEnable": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, "GreenPowerOnly": True, "Group": "GreenPower", },
            "forceZigpy_noasyncio": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "EnergyScanAtStatup": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
        }
    },
    # OTA Related parameters
    "OTA": {
        "Order": 5,
        "param": {   
            "autoServeOTA": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "FirmwareUpdates", },
            "EnableOTATracing": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "FirmwareUpdates", },
            "checkFirmwareAgainstZigbeeOTARepository": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "FirmwareUpdates", "DependsOn": "internetAccess", },
            "ZigbeeOTA_Repository": { "type": "url", "default": "https://raw.githubusercontent.com/Koenkk/zigbee-OTA/master/index.json", "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "Repositories", "DependsOn": "internetAccess", },
            "IkeaTradfri_Repository": { "type": "url", "default": "http://fw.ota.homesmart.ikea.net/feed/version_info.json", "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "Repositories", "DependsOn": "internetAccess", },
            "Sonoff_Repository": { "type": "url", "default": "https://zigbee-ota.sonoff.tech/releases/upgrade.json", "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "Repositories", "DependsOn": "internetAccess", },
        }  
    },
    "Provisioning": {
        "Order": 6,
        "param": {
            "TuyaMagicRead": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "ManufacturerModes", },
            "LegrandCompatibilityMode": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "ManufacturerModes", },
            "enableSchneiderWiser": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "ManufacturerModes", },
            "ConfigureReportingChunk": { "type": "int", "default": 3, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "PairingPace", "Min": 1, "Max": 7, "Step": 1, },
            "AqaraOppleBulbMode": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "ManufacturerModes", },
            "reenforcementWiser": { "type": "int", "default": 300, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "ReadAttributeChunk": { "type": "int", "default": 3, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "PairingPace", "Min": 1, "Max": 7, "Step": 1, },
            "ReadAttributeChunkWhenPairing": { "type": "int", "default": 3, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "PairingPace", "Min": 1, "Max": 7, "Step": 1, },
            "ZiGateConfigureReporting": { "type": "bool","default": 1,"current": None,"restart": 0,"hidden": False,"Advanced": True,"ZigpyRadio": "", "Group": "ManufacturerModes", },
            "bindingDelay": { "type": "float","default": 0.75,"current": None,"restart": 0,"hidden": False,"Advanced": True, "Group": "PairingPace", "Unit": "s", "Min": 0, "Max": 5, "Step": 0.05, },
            "pairingCommandsDelay": { "type": "float","default": 0.0,"current": None,"restart": 0,"hidden": False,"Advanced": True, "Group": "PairingPace", "Unit": "s", "Min": 0, "Max": 5, "Step": 0.05, },
        },
    },
    "WebInterface": {
        "Order": 7,
        "param": {
            "TopologyV2": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "WebInterface", },
            "Sibling": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": True, "Advanced": True, "ZigpyRadio": "" },
            "Lang": { "type": "str", "default": "en-US", "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "WebInterface", },
            "numTopologyReports": { "type": "int", "default": 4, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "WebInterface", "Min": 1, "Max": 20, "Step": 1, },
            "numEnergyReports": { "type": "int", "default": 4, "current": None, "restart": 0, "hidden": True, "Advanced": False, "ZigpyRadio": "", },
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
            "deviceOffWhenTimeOut": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "Health", },
            "forcePollingAfterAction": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "WidgetsLogging", },
            "forcePassiveWidget": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "WidgetsLogging", },
            "allowForceCreationDomoDevice": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "ForceDeviceTimedOut_afterXhours": { "type": "int", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "Health", "Unit": "h", "Min": 0, "Max": 720, "Step": 1, },
            "HealthTimeOut": { "type": "int", "default": 21600, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "Health", "Unit": "s", "Min": 0, "Max": 604800, "Step": 60, },
            "resetPluginDS": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, },
            "resetConfigureReporting": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "OneTimeResets", "OneShot": True, },
            "checkConfigurationReporting": { "type": "int", "default": 75600, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "ReportingBinding", "Unit": "s", "Min": 0, "Max": 604800, "Step": 60, },
            "resetReadAttributes": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "OneTimeResets", "OneShot": True, },
            "resetMotiondelay": { "type": "int", "default": 30, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "MotionSelectors", "Unit": "s", "Min": 0, "Max": 3600, "Step": 1, },
            "resetOTAUpdate": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "OneTimeResets", "OneShot": True, },
            "resetSwitchSelectorPushButton": { "type": "int", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "MotionSelectors", "Unit": "s", "Min": 0, "Max": 3600, "Step": 1, },
            "forceSwitchSelectorPushButton": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "MotionSelectors", },
            "doUnbindBind": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "ReportingBinding", },
            "allowReBindingClusters": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "ReportingBinding", },
            "TrackingEraticValue": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "WidgetsLogging", },
        },
    },
    # Zigate Configuration
    "CoordinatorConfiguration": {
        "Order": 9,
        "param": {
            "blueLedOnOff": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "Coordinator", },
            "resetPermit2Join": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "Coordinator", },
            "Ping": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True, "Group": "Coordinator", "ZigpyRadio": "", },
            "allowRemoveZigateDevice": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": True, "Advanced": True, "ZigpyRadio": "" },
            "eraseZigatePDM": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, "ZigpyRadio": "" },
            "Certification": { "type": "list", "list": {"CE regulation": "CE", "FCC regulation": "FCC"}, "default": "CE", "current": None, "restart": 1, "hidden": False, "Advanced": False, "ZigpyRadio": "", "Group": "Radio", "Danger": True, },
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
                "Group": "Radio",
                "Danger": True,
                },
            "TXpower_set": { "type": "list", "list": {"0dbM": 0, "-9 dbM": 1, "-20dbM": 2, "-32dbM": 3}, "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "Radio", "Danger": True, },
            "extendedPANID": { "type": "hex", "default": 0, "current": None, "restart": 3, "hidden": False, "Advanced": True, "Group": "Radio", "Danger": True, },
            "forceClosingAllNodes": { "type": "bool", "default": 0, "current": None, "restart": 1, "hidden": False, "Advanced": True, "Group": "Coordinator", },
        },
    },
    # Command Transitionin tenth of seconds
    "CommandTransition": {
        "Order": 10,
        "param": {
            "GrpfadingOff": { "type": "list", "list": {"default": 0, "50% fade, 12s to off": 1, "20% dim up, 1s off": 2, "No fade": 255}, "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "GroupTransitions", "DependsOn": "enablegroupmanagement", },
            "GrpmoveToHueSatu": { "type": "int", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": False, "DependsOn": "enablegroupmanagement", },
            "GrpmoveToColourTemp": { "type": "int", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "GroupTransitions", "Unit": "ds", "Min": 0, "Max": 65535, "Step": 1, "DependsOn": "enablegroupmanagement", },
            "GrpmoveToColourRGB": { "type": "int", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "GroupTransitions", "Unit": "ds", "Min": 0, "Max": 65535, "Step": 1, "DependsOn": "enablegroupmanagement", },
            "GrpmoveToLevel": { "type": "int", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "GroupTransitions", "Unit": "ds", "Min": 0, "Max": 65535, "Step": 1, "DependsOn": "enablegroupmanagement", },
            "GroupLevelWithOnOff": { "type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": False, "Group": "GroupTransitions", "DependsOn": "enablegroupmanagement", },
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
            "storeDomoticzDb": { "type": "bool","default": 1,"current": None,"restart": 0,"hidden": False,"Advanced": True, "Group": "Storage", },
            "useDomoticzDb": { "type": "bool","default": 1,"current": None,"restart": 0,"hidden": False,"Advanced": True, "Group": "Storage", },
            "PluginLogMode": { "type": "list","list": { "system default": 0, "0600": 0o600, "0640": 0o640, "0644": 0o644},"default": 0,"current": None,"restart": 1,"hidden": False,"Advanced": True, "Group": "Storage", },
            "numDeviceListVersion": { "type": "int","default": 12,"current": None,"restart": 0,"hidden": False,"Advanced": True, "Group": "Storage", "Min": 1, "Max": 50, "Step": 1, },
            "filename": { "type": "path", "default": "", "current": None, "restart": 1, "hidden": True, "Advanced": True, },
            "pluginHome": { "type": "path", "default": "", "current": None, "restart": 1, "hidden": True, "Advanced": True, },
            "homedirectory": { "type": "path", "default": "", "current": None, "restart": 1, "hidden": True, "Advanced": True, },
            "pluginData": { "type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True, "Group": "Folders", "Danger": True, },
            "pluginConfig": { "type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True, "Group": "Folders", "Danger": True, },
            "pluginOTAFirmware": { "type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True, "Group": "Folders", "Danger": True, },
            "pluginReports": { "type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True, "Group": "Folders", "Danger": True, },
            "pluginWWW": { "type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True, "Group": "Folders", "Danger": True, },
            "pluginLogs": { "type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True, "Group": "Folders", "Danger": True, },
            "SSLCertificate": { "type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True, "Group": "HTTPS", "Danger": True, },
            "SSLPrivateKey": { "type": "path","default": "","current": None,"restart": 1,"hidden": False,"Advanced": True, "Group": "HTTPS", "Danger": True, },
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
            "DZapi": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            
            "GammaTroniques": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Database": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "DeviceAnnoucement": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "DeviceParameter": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Enki": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Flow": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "Garbage": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True },
            "Gledopto": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "GreenPower": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True, "GreenPowerOnly": True },
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
            "ReadAttributeMaxAttributes": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
            "StopProcess": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },

            "Scene": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
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
            "TransportZigpyStack": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
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
            "ZosungIR": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
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
            "enableStructuredDeviceTrace": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
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
            "zclDefaultResponse": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True },
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
            "Bug566": { "type": "bool", "default": 0, "current": None, "restart": 0, "hidden": True, "Advanced": True, }
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
            "ControllerInRawMode": { "type": "bool","default": 0,"current": None,"restart": 0,"hidden": False,"Advanced": True, "Group": "Experimental", },
            "nPDUaPDUThreshold": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,"ZigpyRadio": ""},
            "forceAckOnZCL": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "DropBadAnnoucement": {"type": "bool","default": 1,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "expJsonDatabase": {"type": "bool","default": 1,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            "TryFindingIeeeOfUnknownNwkid": {"type": "bool","default": 0,"current": None,"restart": 0,"hidden": True,"Advanced": True,},
            #"enableZigpyPersistentInFile": {"type": "bool","default": 0,"current": None,"restart": 1,"hidden": False,"Advanced": True,},
            "enableZigpyPersistentInMemory": { "type": "bool","default": 1,"current": None,"restart": 1,"hidden": False,"Advanced": True, "Group": "Experimental", },
            "EventLoopInstrumentation": { "type": "bool","default": 1,"current": None,"restart": 1,"hidden": False,"Advanced": True, "Group": "Experimental", },
            "DomoticzDB_Stats": { "type": "bool","default": 1,"current": None,"restart": 0,"hidden": False,"Advanced": True, "Group": "Experimental", },
            "ZigpyTransport_Stats": { "type": "bool","default": 1,"current": None,"restart": 0,"hidden": False,"Advanced": True, "Group": "Experimental", },
            "EnableTraceMalloc": { "type": "bool","default": 0,"current": None,"restart": 0,"hidden": False,"Advanced": True, "Group": "Experimental", },
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

        initialize_plugin_conf(self, homedir)

        load_settings(self)

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
        pluginconf_filename = Path(self.pluginConf["pluginConfig"] ) / ("PluginConf-%02d.json" % self.hardwareid)
        
        self.pluginConf["filename"] = str(pluginconf_filename)

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

        with open(pluginconf_filename, "wt") as handle:
            json.dump(write_pluginConf, handle, sort_keys=True, indent=2)

        if self.pluginConf["useDomoticzDb"] or self.pluginConf["storeDomoticzDb"]:
            setConfigItem(Key="PluginConf", Attribute="b64-settings", Value={"TimeStamp": time.time(), "b64-settings": write_pluginConf})


def loading_settings_from_domoticz(self):
    dz_timestamp = 0
    domoticz_settings = {}

    try:
        # The TimeStamp is stored in the record, next to the settings
        domoticz_record = getConfigItem(Key="PluginConf", Attribute="b64-settings",)
        domoticz_settings = domoticz_record.get("b64-settings",{})
        dz_timestamp = domoticz_record.get("TimeStamp",0) if domoticz_settings else 0

    except Exception as e:
        Domoticz.Error("Cannot load PluginConf from Domoticz DB: %s" % e)

    if not isinstance(domoticz_settings, dict):
        domoticz_settings = {}
        dz_timestamp = 0

    return dz_timestamp, domoticz_settings


def loading_settings_from_json(self):

    pluginconf_filename = Path(self.pluginConf["pluginConfig"] ) / ("PluginConf-%02d.json" % self.hardwareid)
    if not os.path.isfile(pluginconf_filename):
        return 0, {}

    with open(pluginconf_filename, "rt") as handle:
        
        try:
            txt_timestamp = os.path.getmtime(pluginconf_filename)
            settings = json.load(handle)
            return txt_timestamp, settings

        except json.decoder.JSONDecodeError as e:
            Domoticz.Error("poorly-formed %s, not JSON: %s" % (pluginconf_filename, e))
            
    return 0, {}


def load_settings(self):
    """ Load PluginConf from json file """
    
    Domoticz.Log("load_settings")
    dz_timestamp = txt_timestamp = 0
    domoticz_pluginConf = txt_pluginconf = {}
    
    if self.pluginConf["useDomoticzDb"] or self.pluginConf["storeDomoticzDb"]:
        dz_timestamp, domoticz_pluginConf = loading_settings_from_domoticz(self)

    txt_timestamp, txt_pluginconf = loading_settings_from_json(self)

    conf_settings = domoticz_pluginConf if dz_timestamp >= txt_timestamp else txt_pluginconf

    for param in conf_settings:
        self.pluginConf[param] = conf_settings[param]

    # Overwrite Zigpy parameters if we are running native Zigate
    if self.zigbee_communication != "zigpy":
        # Force to 0 as this parameter is only relevant to Zigpy
        self.pluginConf["ZigpyTopologyReport"] = False
        # Second half of a zigpy topology scan; nothing runs it on a native ZiGate,
        # where the TopologyV2 scan collects the same table on its own.
        self.pluginConf["ZigpyTopologyAssociatedDevices"] = False
    
    if dz_timestamp >= txt_timestamp:
        Domoticz.Status("Z4D loads pluginconf from Domoticz Db: %s" % len(self.pluginConf))
    else:
        Domoticz.Status("Z4D loads pluginconf from Json File: %s" % len(self.pluginConf))


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
                    Domoticz.Status(f"Z4D updates path from {self.pluginConf[param]} to {_path_name}")
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
                    # zigpy takes the power in dBm, 0 keeps the radio's own (Modules/txPower.py)
                    "Unit": "dBm",
                    "Group": "Radio",
                    "Danger": True,
                }

                               
def initialize_plugin_conf(self, homedir):
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
