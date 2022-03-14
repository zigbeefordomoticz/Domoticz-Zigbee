#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
Class PluginConf

Description: Import the PluginConf.txt file and initialized each of the available parameters in this file
Parameters not define in the PluginConf.txt file will be set to their default value.

"""

import json
import os.path
import time

import Domoticz
from Modules.tools import getConfigItem, is_domoticz_db_available, is_hex, setConfigItem

SETTINGS = {
    "Services": {
        "Order": 1,
        "param": {
            "enablegroupmanagement": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": False,
            },
            "enableReadAttributes": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 1,
                "hidden": True,
                "Advanced": True,
            },
            "internetAccess": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": False,
            },
            "allowOTA": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 1,
                "hidden": True,
                "Advanced": False,
            },
            "pingDevices": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": True,
            },
            "PluginAnalytics": {
                "type": "bool",
                "default": -1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
   
            }
        },
    },
    "GroupManagement": {
        "Order": 2,
        "param": {
            "GroupOnBattery": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "OnIfOneOn": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "forceGroupDeviceRefresh": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "reComputeGroupState": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "allowGroupMembership": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": True,
                "hidden": False,
                "Advanced": True,
            },
            "zigatePartOfGroupTint": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": True,
            },
            "zigatePartOfGroup0000": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": True,
            },
        },
    },
    "DomoticzEnvironment": {
        "Order": 3,
        "param": {
            "port": {
                "type": "str",
                "default": "8080",
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            }
        },
    },
    "Provisioning": {
        "Order": 3,
        "param": {
            "Livolo": {"type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": False},
            "enableSchneiderWiser": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "breakConfigureReporting": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
        },
    },
    "WebInterface": {
        "Order": 4,
        "param": {
            "Sibling": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "Lang": {
                "type": "str",
                "default": "en-US",
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "numTopologyReports": {
                "type": "int",
                "default": 4,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "numEnergyReports": {
                "type": "int",
                "default": 4,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "enableGzip": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "enableDeflate": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "enableChunk": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "enableKeepalive": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "enableCache": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
        },
    },
    # Device Management
    "DeviceManagement": {
        "Order": 6,
        "param": {
            "deviceOffWhenTimeOut": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "forcePollingAfterAction": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "forcePassiveWidget": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "allowForceCreationDomoDevice": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "resetPluginDS": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "resetConfigureReporting": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": True,
            },
            "reenforceConfigureReporting": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "resetReadAttributes": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": True,
            },
            "resetMotiondelay": {
                "type": "int",
                "default": 30,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "resetSwitchSelectorPushButton": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "forceSwitchSelectorPushButton": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "doUnbindBind": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "allowReBindingClusters": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
        },
    },
    # Zigate Configuration
    "CoordinatorConfiguration": {
        "Order": 7,
        "param": {
            "blueLedOnOff": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "pingDevicesFeq": {
                "type": "int",
                "default": 3600,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "resetPermit2Join": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "Ping": {"type": "bool", "default": 1, "current": None, "restart": 0, "hidden": False, "Advanced": True},
            "allowRemoveZigateDevice": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "eraseZigatePDM": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "Certification": {
                "type": "list",
                "list": {"CE regulation": "CE", "FCC regulation": "FCC"},
                "default": "CE",
                "current": None,
                "restart": True,
                "hidden": False,
                "Advanced": False,
            },
            "CertificationCode": {
                "type": "int",
                "default": 1,
                "current": None,
                "restart": 1,
                "hidden": True,
                "Advanced": False,
            },
            "channel": {
                "type": "list",
                "list": {
                    "default": 0,
                    "11": 11,
                    "12": 12,
                    "13": 13,
                    "14": 14,
                    "15": 15,
                    "16": 16,
                    "17": 17,
                    "18": 18,
                    "19": 19,
                    "20": 20,
                    "21": 21,
                    "22": 22,
                    "23": 23,
                    "24": 24,
                    "25": 25,
                    "26": 26,
                },
                "default": "0",
                "current": None,
                "restart": 2,
                "hidden": False,
                "Advanced": False,
            },
            "TXpower_set": {
                "type": "list",
                "list": {"0dbM": 0, "-9 dbM": 1, "-20dbM": 2, "-32dbM": 3},
                "default": 0,
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": True,
            },
            "extendedPANID": {
                "type": "hex",
                "default": 0,
                "current": None,
                "restart": 3,
                "hidden": False,
                "Advanced": True,
            },
            "forceClosingAllNodes": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": True,
            },
        },
    },
    # Command Transitionin tenth of seconds
    "CommandTransition": {
        "Order": 8,
        "param": {
            "GrpfadingOff": {
                "type": "list",
                "list": {"default": 0, "50% fade, 12s to off": 1, "20% dim up, 1s off": 2, "No fade": 255},
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "GrpmoveToHueSatu": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "GrpmoveToColourTemp": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "GrpmoveToColourRGB": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "GrpmoveToLevel": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
        },
    },
    # Plugin Transport
    "PluginTransport": {
        "Order": 9,
        "param": {
            "disableAckOnZCL": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "waitForResponse": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "byPassDzConnection": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 1,
                "hidden": True,
                "Advanced": True,
            },
            "SerialReadV2": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "forceFullSeqMode": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "RawReadAttribute": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "RawWritAttribute": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "writerTimeOut": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
        },
    },
    # Plugin Directories
    "PluginConfiguration": {
        "Order": 10,
        "param": {
            "numDeviceListVersion": {
                "type": "int",
                "default": 12,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "filename": {
                "type": "path",
                "default": "",
                "current": None,
                "restart": 1,
                "hidden": True,
                "Advanced": True,
            },
            "pluginHome": {
                "type": "path",
                "default": "",
                "current": None,
                "restart": 1,
                "hidden": True,
                "Advanced": True,
            },
            "homedirectory": {
                "type": "path",
                "default": "",
                "current": None,
                "restart": 1,
                "hidden": True,
                "Advanced": True,
            },
            "pluginData": {
                "type": "path",
                "default": "",
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": True,
            },
            "pluginConfig": {
                "type": "path",
                "default": "",
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": True,
            },
            "pluginOTAFirmware": {
                "type": "path",
                "default": "",
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": True,
            },
            "pluginReports": {
                "type": "path",
                "default": "",
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": True,
            },
            "pluginWWW": {
                "type": "path",
                "default": "",
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": True,
            },
            "pluginLogs": {
                "type": "path",
                "default": "",
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": True,
            },
        },
    },
    # Verbose
    "VerboseLogging": {
        "Order": 11,
        "param": {
            "debugMatchId": {
                "type": "str",
                "default": "ffff",
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "debugLQI": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "logDeviceUpdate": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "enablePluginLogging": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": False,
            },
            "loggingBackupCount": {
                "type": "int",
                "default": 7,
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": False,
            },
            "loggingMaxMegaBytes": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 1,
                "hidden": False,
                "Advanced": False,
            },
            "logThreadName": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugzigateCmd": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "trackTransportError": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "ZiGateReactTime": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "showTimeOutMsg": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "NXPExtendedErrorCode": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugInput": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugBasicOutput": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugBinding": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugConfigureReporting": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugWriteAttributes": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugReadAttributes": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugThermostats": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransport": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransport8000": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransport8002": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransport8011": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransport8012": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransportWrter": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransportFrwder": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransportRder": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransportProto": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransportTcpip": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransportSerial": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransportZigpy": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransportZigpyZigate": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransportZigpyZNP": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransportZigpyEZSP": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTransportPluginEncoder": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugCluster": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugHeartbeat": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugWidget": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugPlugin": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugDatabase": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugCommand": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugPairing": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugNetworkMap": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugNetworkEnergy": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugGroups": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugOTA": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugIAS": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugDZDB": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugWebServer": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugLegrand": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugLumi": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugLivolo": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTuya": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugProfalux": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugSchneider": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugCasaIA": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugPhilips": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugPDM": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debuginRawAPS": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugoutRawAPS": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugTiming": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "logFORMAT": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "debugDanfoss": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugzdpCommand": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugzclCommand": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugzdpDecoder": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugzclDecoder": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugzigateCommand": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugThreadForwarder": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugThreadDomoticz": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugThreadWriter": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "debugThreadCommunication": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
        },
    },
    # Others
    "Others": {
        "Order": 13,
        "param": {
            "TradfriKelvinStep": {
                "type": "int",
                "default": 51,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": False,
            },
            "AqaraOppleBulbMode": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "reenforcementWiser": {
                "type": "int",
                "default": 300,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "LegrandCompatibilityMode": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
        },
    },
    "Patching": {
        "Order": 14,
        "param": {
            "Bug566": {"type": "bool", "default": 0, "current": None, "restart": 0, "hidden": False, "Advanced": True}
        },
    },
    # Experimental
    "Experimental": {
        "Order": 15,
        "param": {
            "ControllerInHybridMode": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "ControllerInRawMode": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "nPDUaPDUThreshold": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "forceAckOnZCL": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "RoutingTableRequestFeq": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "BindingTableRequestFeq": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "doManyToOneRoute": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "DropBadAnnoucement": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "expJsonDatabase": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "useDomoticzDatabase": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": False,
                "Advanced": True,
            },
            "XiaomiLeave": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "rebindLivolo": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "allowAutoPairing": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "disabledDefaultResponseFirmware": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 1,
                "hidden": True,
                "Advanced": True,
            },
        },
    },
    "Reserved": {
        "Order": 99,
        "param": {
            # Just for compatibility keep it but hidden ( move to Custom device 'Param' section)
            "AnnoucementV0": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "AnnoucementV1": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "AnnoucementV2": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "pollingPhilips": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "pollingGledopto": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "pollingSchneider": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "pollingBlitzwolfPower": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "pollingLumiPower": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "pollingCasaiaAC201": {
                "type": "int",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "PhilipsPowerOnAfterOffOn": {
                "type": "list",
                "list": {"Off": 0, "On": 1, "Previous": 255},
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "EnkiPowerOnAfterOffOn": {
                "type": "list",
                "list": {"Off": 0, "On": 1, "Previous": 255},
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "IkeaPowerOnAfterOffOn": {
                "type": "list",
                "list": {"Off": 0, "On": 1, "Previous": 255},
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            # Polling
            "polling0000": {
                "type": "int",
                "default": 86400,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0001": {
                "type": "int",
                "default": 86400,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0002": {
                "type": "int",
                "default": 86400,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "pollingONOFF": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "pollingLvlControl": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling000C": {
                "type": "int",
                "default": 3600,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0019": {
                "type": "int",
                "default": 86400,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0100": {
                "type": "int",
                "default": 3600,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0020": {
                "type": "int",
                "default": 3600,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0101": {
                "type": "int",
                "default": 3600,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0102": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0201": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0202": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0204": {
                "type": "int",
                "default": 86400,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0300": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0400": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0402": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0403": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0405": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0406": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0500": {
                "type": "int",
                "default": 86400,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0502": {
                "type": "int",
                "default": 86400,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0702": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0b04": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling0b05": {
                "type": "int",
                "default": 86400,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "polling000f": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "pollingfc01": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "pollingfc21": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "pollingfc40": {
                "type": "int",
                "default": 900,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": True,
            },
            "EnableLedIfOn": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "EnableLedInDark": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "EnableLedShutter": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "EnableDimmer": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "InvertShutter": {
                "type": "bool",
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "EnableReleaseButton": {
                "type": "bool",
                "default": 0,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
            "LegrandPowerOnAfterOffOn": {
                "type": "list",
                "list": {"Off": 0, "On": 1, "Previous": 255},
                "default": 1,
                "current": None,
                "restart": 0,
                "hidden": True,
                "Advanced": False,
            },
        },
    },
}


class PluginConf:
    def __init__(self, zigbee_communication, VersionNewFashion, DomoticzMajor, DomoticzMinor, homedir, hardwareid):

        self.pluginConf = {}
        self.homedir = homedir
        self.hardwareid = hardwareid
        self.pluginConf["pluginHome"] = homedir
        self.VersionNewFashion = VersionNewFashion
        self.DomoticzMajor = DomoticzMajor
        self.DomoticzMinor = DomoticzMinor
        self.zigbee_communitation = zigbee_communication 

        setup_folder_parameters(self, homedir)

        self.pluginConf["filename"] = self.pluginConf["pluginConfig"] + "PluginConf-%02d.json" % hardwareid
        if os.path.isfile(self.pluginConf["filename"]):
            _load_Settings(self)

        else:
            _load_oldfashon(self, homedir, hardwareid)

        if self.zigbee_communitation == "zigpy":
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
        # serialize json format the pluginConf '
        # Only the arameters which are different than default '

        self.pluginConf["filename"] = self.pluginConf["pluginConfig"] + "PluginConf-%02d.json" % self.hardwareid
        pluginConfFile = self.pluginConf["filename"]
        write_pluginConf = {}
        for theme in SETTINGS:
            for param in SETTINGS[theme]["param"]:
                if self.pluginConf[param] != SETTINGS[theme]["param"][param]["default"]:
                    if SETTINGS[theme]["param"][param]["type"] == "hex":
                        write_pluginConf[param] = "%X" % self.pluginConf[param]
                    else:
                        write_pluginConf[param] = self.pluginConf[param]

        with open(pluginConfFile, "wt") as handle:
            json.dump(write_pluginConf, handle, sort_keys=True, indent=2)

        if is_domoticz_db_available(self) and self.pluginConf["useDomoticzDatabase"]:
            setConfigItem(Key="PluginConf", Value={"TimeStamp": time.time(), "b64Settings": write_pluginConf})


def _load_Settings(self):
    # deserialize json format of pluginConf'
    # load parameters '

    dz_timestamp = 0
    if is_domoticz_db_available(self):
        _domoticz_pluginConf = getConfigItem(Key="PluginConf")
        if "TimeStamp" in _domoticz_pluginConf:
            dz_timestamp = _domoticz_pluginConf["TimeStamp"]
            _domoticz_pluginConf = _domoticz_pluginConf["b64Settings"]
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
    if is_domoticz_db_available(self) and self.pluginConf["useDomoticzDatabase"]:
        Domoticz.Log("PluginConf Loaded from Dz: %s from Json: %s" % (len(_domoticz_pluginConf), len(_pluginConf)))
        if _domoticz_pluginConf:
            for x in _pluginConf:
                if x not in _domoticz_pluginConf:
                    Domoticz.Error("-- %s is missing in Dz" % x)
                elif _pluginConf[x] != _domoticz_pluginConf[x]:
                    Domoticz.Error(
                        "++ %s is different in Dz: %s from Json: %s" % (x, _domoticz_pluginConf[x], _pluginConf[x])
                    )


def _load_oldfashon(self, homedir, hardwareid):
    # Import PluginConf.txt
    # Migration
    self.pluginConf["filename"] = self.pluginConf["pluginConfig"] + "PluginConf-%02d.txt" % hardwareid
    if not os.path.isfile(self.pluginConf["filename"]):
        self.pluginConf["filename"] = self.pluginConf["pluginConfig"] + "PluginConf-%d.txt" % hardwareid
        if not os.path.isfile(self.pluginConf["filename"]):
            self.pluginConf["filename"] = self.pluginConf["pluginConfig"] + "PluginConf.txt"
            if not os.path.isfile(self.pluginConf["filename"]):
                self.write_Settings()
                return

    tmpPluginConf = ""
    if not os.path.isfile(self.pluginConf["filename"]):
        return
    with open(self.pluginConf["filename"], "r") as myPluginConfFile:
        tmpPluginConf += myPluginConfFile.read().replace("\n", "")

    PluginConf = {}
    _import_oldfashon_param(self, tmpPluginConf, self.pluginConf["filename"])


def _import_oldfashon_param(self, tmpPluginConf, filename):
    try:
        PluginConf = eval(tmpPluginConf)
    except SyntaxError:
        Domoticz.Error("Syntax Error in %s, all plugin parameters set to default" % filename)
    except (NameError, TypeError, ZeroDivisionError):
        Domoticz.Error("Error while importing %s, all plugin parameters set to default" % filename)
    else:
        for theme in SETTINGS:
            for param in SETTINGS[theme]["param"]:
                if PluginConf.get(param):
                    if SETTINGS[theme]["param"][param]["type"] == "hex":
                        if is_hex(PluginConf.get(param)):
                            self.pluginConf[param] = int(PluginConf[param], 16)
                        else:
                            Domoticz.Error(
                                "Wrong parameter type for %s, keeping default %s"
                                % (param, self.pluginConf[param]["default"])
                            )
                            self.pluginConf[param] = self.pluginConf[param]["default"]

                    elif SETTINGS[theme]["param"][param]["type"] in ("bool", "int"):
                        if PluginConf.get(param).isdigit():
                            self.pluginConf[param] = int(PluginConf[param])
                        else:
                            Domoticz.Error(
                                "Wrong parameter type for %s, keeping default %s"
                                % (param, self.pluginConf[param]["default"])
                            )
                            self.pluginConf[param] = self.pluginConf[param]["default"]
                    elif SETTINGS[theme]["param"][param]["type"] == ("path", "str"):
                        self.pluginConf[param] = PluginConf[param]

    self.write_Settings()


def _path_check(self):

    for theme in SETTINGS:
        for param in SETTINGS[theme]["param"]:
            if SETTINGS[theme]["param"][param]["type"] == "path" and not os.path.exists(self.pluginConf[param]):
                Domoticz.Error("Cannot access path: %s" % self.pluginConf[param])


def _param_checking(self):
    # Let's check the Type
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
    for theme in SETTINGS:
        for param in SETTINGS[theme]["param"]:
            if param == "pluginHome":
                continue
            if param == "homedirectory":
                self.pluginConf[param] = homedir
            elif param == "pluginConfig":
                self.pluginConf[param] = self.pluginConf["pluginHome"] + "Conf/"
            elif param == "pluginData":
                self.pluginConf[param] = self.pluginConf["pluginHome"] + "Data/"
            elif param == "pluginLogs":
                self.pluginConf[param] = self.pluginConf["pluginHome"] + "Logs/"
            elif param == "pluginOTAFirmware":
                self.pluginConf[param] = self.pluginConf["pluginHome"] + "OTAFirmware/"
            elif param == "pluginReports":
                self.pluginConf[param] = self.pluginConf["pluginHome"] + "Reports/"
            elif param == "pluginWWW":
                self.pluginConf[param] = self.pluginConf["pluginHome"] + "www/"
            else:
                self.pluginConf[param] = SETTINGS[theme]["param"][param]["default"]
