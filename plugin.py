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

"""
<plugin key="Zigate" name="Zigbee for domoticz plugin (zigpy enabled)" author="pipiche38" version="7.1">
    <description>
        <h1> Plugin Zigbee for domoticz</h1><br/>
            <br/><h2> Informations</h2><br/>
                <ul style="list-style-type:square">
                    <li>&Documentations : &<a href="https://github.com/pipiche38/Domoticz-Zigate-Wiki/blob/master/en-eng/Home.md">English wiki</a>|<a href="https://github.com/pipiche38/Domoticz-Zigate-Wiki/blob/master/fr-fr/Home.md">Wiki Français</a></li>
                    <li>&Forums : &<a href="https://www.domoticz.com/forum/viewforum.php?f=68">English (www.domoticz.com)</a>|<a href="https://easydomoticz.com/forum/viewforum.php?f=28">Français (www.easydomoticz.com)</a></li>
                    <li>&List of supported devices : &<a href="https://zigbee.blakadder.com/z4d.html">www.zigbee.blakadder.com</a></li>
                </ul>
            <br/><h2>Parameters</h2>
    </description>
    <params>
        <param field="Mode1" label="Coordinator Model" width="200px" required="true" default="None">
            <description><br/><h3>Zigbee Coordinator definition</h3><br/>Select the Zigbee radio Coordinator version : ZiGate (V1), ZiGate+ (V2), Texas Instrument ZNP, Silicon Labs EZSP or ConBee/RasBee</description>
            <options>
                <option label="ZiGate"  value="V1"/>
                <option label="ZiGate+" value="V2"/>
                <option label="Texas Instruments ZNP (via zigpy)" value="ZigpyZNP"/>
                <option label="Silicon Labs EZSP (via zigpy)" value="ZigpyEZSP"/>
                <option label="Conbee/Rasbee I, II, III (via zigpy)" value="ZigpydeCONZ"/>
            </options>
        </param>
        <param field="Mode2" label="Coordinator Type" width="75px" required="true" default="None">
            <description><br/>Select the Radio Coordinator connection type : USB, DIN, Pi, TCPIP (Wifi, Ethernet) or Socket. In case of Socket use the IP to put the remote ip</description>
            <options>
                <option label="USB"   value="USB" />
                <option label="DIN"   value="DIN" />
                <option label="PI"    value="PI" />
                <option label="TCPIP" value="Wifi"/>
                <option label="Socket" value="Socket"/>
                <option label="None"  value="None"/>
            </options>
        </param>
        <param field="SerialPort" label="Serial Port" width="200px" required="true" default="/dev/ttyUSB0" >
            <description><br/>Set the serial port where the Radio Coordinator is connected (/dev/ttyUSB0 for example)</description>
        </param>
        <param field="Address" label="IP" width="150px" required="true" default="0.0.0.0">
            <description><br/>Set the Radio Coordinator IP adresse (0.0.0.0 if not applicable)</description>
        </param>
        <param field="Port" label="Port" width="75px" required="true" default="9999">
            <description><br/>Set the Radio Coordinator Port (9999 by default)</description>
        </param>
        <param field="Mode5" label="API base url <br/>(http://username:password@127.0.0.1:port)" width="250px" default="http://127.0.0.1:8080" required="true" >
            <description>
                <br/><h3>Domoticz Json/API base ( http://127.0.0.1:8080 should be the default)</h3>In case Domoticz listen to an other port change 8080 by what ever is the port, 
                and if you have setup an authentication please add the username:password</description>
        </param>
        <param field="Mode4" label="WebUI port" width="150px" required="true" default="9440" >
            <description><br/><h3>Plugin definition</h3><br/>Set the plugin Dashboard port (9440 by default, None to disable)<br/>
            In case you would like to restrict the interface and to secure the access to the dashboard , you can also add use the format IP:PORT ( 127.0.0.1:9440)<br/> 
            To access the plugin WebUI, replace your DomoticZ port (8080 by default) in your web adress by your WebUI port (9440 by default).</description>
        </param>
        <param field="Mode3" label="Initialize Coordinator" width="75px" required="true" default="False" >
            <description><br/><h3>Coordinator initialization</h3>Required step only with a new Coordinator or if you want to create a new Zigbee network.<br/>
            This can be usefull if you want to use a specific Extended PanId requires for Wiser (legacy) devices.
            Be aware : this will reset the Coordinator and all paired devices will be lost. After that, you'll have to re-pair each devices.<br/>
            This is not removing any data from DomoticZ nor the plugin database.</description>
            <options>
                <option label="True" value="True"/>
                <option label="False" value="False" default="true" />
            </options>
        </param>
        <param field="Mode6" label="Debugging" width="150px"  default="None" required="true">
            <description><br/><h3>Plugin debug</h3>This debugging option has been moved to the WebUI > Tools > Debug<br/></description>
                <options>
                    <option label="None" value="0"  default="true" />
                    <option label="Python Only" value="2"/>
                    <option label="Basic Debugging" value="62"/>
                    <option label="Basic+Messages" value="126"/>
                    <option label="Connections Only" value="16"/>
                    <option label="Connections+Queue" value="144"/>
                    <option label="All" value="-1"/>
                </options>
        </param>
            
    </params>
</plugin>
"""


#import DomoticzEx as Domoticz
import Domoticz

try:
    #from DomoticzEx import Devices, Images, Parameters, Settings
    from Domoticz import Devices, Images, Parameters, Settings
except ImportError:
    pass

import gc
import json
import os
import os.path
import pathlib
import sys
import threading
import time

import z4d_certified_devices

from Classes.AdminWidgets import AdminWidgets
from Classes.ConfigureReporting import ConfigureReporting
from Classes.DomoticzDB import (DomoticzDB_DeviceStatus, DomoticzDB_Hardware,
                                DomoticzDB_Preferences)
from Classes.GroupMgtv2.GroupManagement import GroupsManagement
from Classes.IAS import IAS_Zone_Management
from Classes.LoggingManagement import LoggingManagement
from Classes.NetworkEnergy import NetworkEnergy
from Classes.NetworkMap import NetworkMap
from Classes.OTA import OTAManagement
from Classes.PluginConf import PluginConf
from Classes.TransportStats import TransportStatistics
from Classes.WebServer.WebServer import WebServer
from Classes.ZigpyTopology import ZigpyTopology
from Modules.basicOutputs import (ZigatePermitToJoin, leaveRequest,
                                  setExtendedPANID, setTimeServer,
                                  start_Zigate, zigateBlueLed)
from Modules.casaia import restart_plugin_reset_ModuleIRCode
from Modules.checkingUpdate import (check_plugin_version_against_dns,
                                    is_internet_available,
                                    is_plugin_update_available,
                                    is_zigate_firmware_available)
from Modules.command import domoticz_command
from Modules.database import (LoadDeviceList, WriteDeviceList,
                              checkDevices2LOD, checkListOfDevice2Devices,
                              import_local_device_conf)
from Modules.domoticzAbstractLayer import (domo_read_Name,
                                           find_legacy_DeviceID_from_unit,
                                           how_many_legacy_slot_available,
                                           is_domoticz_extended,
                                           load_list_of_domoticz_widget)
from Modules.heartbeat import processListOfDevices
from Modules.input import zigbee_receive_message
from Modules.matomo_request import (matomo_coordinator_initialisation,
                                    matomo_plugin_analytics_infos,
                                    matomo_plugin_restart,
                                    matomo_plugin_shutdown,
                                    matomo_plugin_started)
from Modules.paramDevice import initialize_device_settings
from Modules.piZigate import switchPiZigate_mode
from Modules.pluginHelpers import (check_firmware_level,
                                   check_python_modules_version,
                                   check_requirements, decodeConnection,
                                   get_domoticz_version,
                                   list_all_modules_loaded, networksize_update,
                                   update_DB_device_status_to_reinit)
from Modules.profalux import profalux_fake_deviceModel
from Modules.readZclClusters import load_zcl_cluster
from Modules.restartPlugin import restartPluginViaDomoticzJsonApi
from Modules.schneider_wiser import wiser_thermostat_monitoring_heating_demand
from Modules.tools import (build_list_of_device_model,
                           chk_and_update_IEEE_NWKID, lookupForIEEE,
                           night_shift_jobs, removeDeviceInList)
from Modules.txPower import set_TxPower
from Modules.zigateCommands import (zigate_erase_eeprom,
                                    zigate_get_firmware_version,
                                    zigate_get_list_active_devices,
                                    zigate_get_nwk_state, zigate_get_time,
                                    zigate_remove_device,
                                    zigate_set_certificate, zigate_set_mode)
from Modules.zigateConsts import CERTIFICATION, HEARTBEAT, MAX_FOR_ZIGATE_BUZY
from Modules.zigpyBackup import handle_zigpy_backup
from Zigbee.zdpCommands import zdp_get_permit_joint_status

VERSION_FILENAME = ".hidden/VERSION"

TEMPO_NETWORK = 2  # Start HB totrigget Network Status
TIMEDOUT_START = 10  # Timeoud for the all startup
TIMEDOUT_FIRMWARE = 5  # HB before request Firmware again
TEMPO_START_ZIGATE = 1  # Nb HB before requesting a Start_Zigate

STARTUP_TIMEOUT_DELAY_FOR_WARNING = 60
STARTUP_TIMEOUT_DELAY_FOR_STOP = 120
ZNP_STARTUP_TIMEOUT_DELAY_FOR_WARNING = 110
ZNP_STARTUP_TIMEOUT_DELAY_FOR_STOP = 160

class BasePlugin:
    enabled = False

    def __init__(self):

        self.internet_available = None
        self.ListOfDevices = (
            {}
        )  # {DevicesAddresse : { status : status_de_detection, data : {ep list ou autres en fonctions du status}}, DevicesAddresse : ...}
        self.DiscoveryDevices = {}  # Used to collect pairing information
        self.IEEE2NWK = {}
        self.ControllerData = {}
        self.DeviceConf = {}  # Store DeviceConf.txt, all known devices configuration
        self.ModelManufMapping = {}
        self.readZclClusters = {}
        self.ListOfDomoticzWidget = {}

        # Objects from Classe
        self.configureReporting = None
        self.ControllerLink= None
        self.groupmgt = None
        self.networkmap = None
        self.zigpy_topology = None
        self.networkenergy = None
        self.domoticzdb_DeviceStatus = None  # Object allowing direct access to Domoticz DB DeviceSatus
        self.domoticzdb_Hardware = None  # Object allowing direct access to Domoticz DB Hardware
        self.domoticzdb_Preferences = None  # Object allowing direct access to Domoticz DB Preferences
        self.adminWidgets = None  # Manage AdminWidgets object
        self.pluginconf = None  # PlugConf object / all configuration parameters
        self.OTA = None
        self.statistics = None
        self.iaszonemgt = None  # Object to manage IAS Zone
        self.webserver = None
        self.transport = None  # USB or Wifi
        self.log = None
        self.zigpy_backup = None
        # self._ReqRcv = bytearray()

        self.UnknownDevices = []  # List of unknown Device NwkId
        self.permitTojoin = {"Duration": 0, "Starttime": 0}
        self.CommiSSionning = (
            False  # This flag is raised when a Device Annocement is receive, in order to give priority to commissioning
        )

        self.busy = (
            False  # This flag is raised when a Device Annocement is receive, in order to give priority to commissioning
        )
        self.homedirectory = None
        self.HardwareID = None
        self.Key = None
        self.DomoticzVersion = None
        self.StartupFolder = None
        self.DeviceListName = None
        self.pluginParameters = None

        self.PluginHealth = {}
        self.Ping = {}
        self.Ping["Nb Ticks"] = self.Ping["Status"] = self.Ping["TimeStamp"] = None
        self.connectionState = None

        self.HBcount = 0
        self.HeartbeatCount = 0
        self.internalHB = 0

        self.currentChannel = None  # Curent Channel. Set in Decode8009/Decode8024
        self.ControllerIEEE = None  # Zigate IEEE. Set in CDecode8009/Decode8024
        self.ControllerNWKID = None  # Zigate NWKID. Set in CDecode8009/Decode8024
        self.ZiGateModel = None  # V1 or V2
        self.FirmwareVersion = None
        self.FirmwareMajorVersion = None
        self.FirmwareBranch = None
        self.mainpowerSQN = None  # Tracking main Powered SQN
        # self.ForceCreationDevice = None   #

        self.VersionNewFashion = None
        self.DomoticzBuild = None
        self.DomoticzMajor = None
        self.DomoticzMinor = None

        self.WebUsername = None
        self.WebPassword = None

        self.PluzzyFirmware = False
        self.pluginVersion = {}
        self.z4d_certified_devices_version = None

        self.loggingFileHandle = None
        self.level = 0

        self.PDM = None
        self.PDMready = False

        self.InitPhase3 = False
        self.InitPhase2 = False
        self.InitPhase1 = False
        self.ErasePDMDone = False
        self.ErasePDMinProgress = False
        self.startZigateNeeded = False

        self.SchneiderZone = None  # Manage Zone for Wiser Thermostat and HACT
        self.CasaiaPAC = None  # To manage Casa IA PAC configuration

        self.internalError = 0  # Use to count the number of repeat 0x8000 error

        self.MajDomoDevice_timing_cnt = (
            self.MajDomoDevice_timing_cumul
        ) = self.MajDomoDevice_timing_avrg = self.MajDomoDevice_timing_max = 0
        self.ReadCluster_timing_cnt = (
            self.ReadCluster_timing_cumul
        ) = self.ReadCluster_timing_avrg = self.ReadCluster_timing_max = 0
        self.ZigateRead_timing_cnt = (
            self.ZigateRead_timing_cumul
        ) = self.ZigateRead_timing_avrg = self.ZigateRead_timing_max = 0
        
        # Zigpy
        self.zigbee_communication = None  # "zigpy" or "native"
        #self.pythonModuleVersion = {}
        
        self.device_settings = {}
        initialize_device_settings(self)

    def onStart(self):
        Domoticz.Status( "Welcome to Zigbee for Domoticz (Z4D) plugin.")
        
        _current_python_version_major = sys.version_info.major
        _current_python_version_minor = sys.version_info.minor

        Domoticz.Status( "Z4D requires python3.9 or above and you are running %s.%s" %(
            _current_python_version_major, _current_python_version_minor))
    
        assert sys.version_info >= (3, 9)  # nosec

        if Parameters["Mode1"] == "V1" and Parameters["Mode2"] in ( "USB", "DIN", "PI", "Wifi", ):
            self.transport = Parameters["Mode2"]
            self.zigbee_communication = "native"

        elif Parameters["Mode1"] == "V2" and Parameters["Mode2"] in ( "USB", "DIN", "PI", "Wifi", ):
            self.transport = "V2-" + Parameters["Mode2"]
            self.zigbee_communication = "native"

        elif Parameters["Mode2"] == "None":
            self.zigbee_communication = "native"
            self.transport = "None"

        elif Parameters["Mode1"] in ( "ZigpyZiGate", "ZigpyZNP", "ZigpydeCONZ", "ZigpyEZSP"):
            self.transport = Parameters["Mode1"]
            self.zigbee_communication = "zigpy"

        else:
            Domoticz.Error(
                "Please cross-check the plugin starting parameters Mode1: %s Mode2: %s and make sure you have restarted Domoticz after updating the plugin"
                % (Parameters["Mode1"] == "V1", Parameters["Mode2"])
            )
            self.onStop()
            return

        if (
            Parameters["Mode5"] == "" 
            or ( "http://" not in Parameters["Mode5"].lower() and "https://" not in Parameters["Mode5"].lower() )
        ):
            Domoticz.Error("Please cross-check the Domoticz Hardware setting for the plugin instance. >%s< You must set the API base URL" %Parameters["Mode5"])
            self.onStop()

        # Set plugin heartbeat to 1s
        Domoticz.Heartbeat(1)

        # Copy the Domoticz.Parameters to a variable accessible in the all objetc
        self.pluginParameters = dict(Parameters)

        # Open VERSION file in .hidden
        version_filename = pathlib.Path(Parameters["HomeFolder"]) / VERSION_FILENAME
        with open( version_filename, "rt") as versionfile:
            try:
                _pluginversion = json.load(versionfile)
            except Exception as e:
                Domoticz.Error("Error when opening: %s -- %s" % (Parameters["HomeFolder"] + VERSION_FILENAME, e))
                self.onStop()
                return

        self.z4d_certified_devices_version = z4d_certified_devices.__version__

        self.pluginParameters["PluginBranch"] = _pluginversion["branch"]
        self.pluginParameters["PluginVersion"] = _pluginversion["version"]
        self.pluginParameters["CertifiedDbVersion"] = z4d_certified_devices.__version__
        self.pluginParameters["TimeStamp"] = 0
        self.pluginParameters["available"] = None
        self.pluginParameters["available-firmMajor"] = None
        self.pluginParameters["available-firmMinor"] = None
        self.pluginParameters["FirmwareVersion"] = None
        self.pluginParameters["FirmwareUpdate"] = None
        self.pluginParameters["PluginUpdate"] = None

        self.busy = True

        self.DomoticzVersion = Parameters["DomoticzVersion"]
        self.homedirectory = Parameters["HomeFolder"]
        self.HardwareID = Parameters["HardwareID"]
        self.Key = Parameters["Key"]
        
        if not get_domoticz_version( self, Parameters["DomoticzVersion"] ):
            return

        # Import PluginConf.txt
        Domoticz.Log("Z4D loading PluginConf")
        self.pluginconf = PluginConf(
            self.zigbee_communication, self.VersionNewFashion, self.DomoticzMajor, self.DomoticzMinor, Parameters["HomeFolder"], self.HardwareID
        )

        if self.internet_available is None:
            self.internet_available = is_internet_available()

        if self.internet_available:
            if check_requirements( Parameters[ "HomeFolder"] ):
                # Check_requirements() return True if requirements not meet.
                self.onStop()
                return

        # Create Domoticz Sub menu
        if "DomoticzCustomMenu" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["DomoticzCustomMenu"] :
            install_Z4D_to_domoticz_custom_ui( )

        # Create the adminStatusWidget if needed
        self.PluginHealth["Flag"] = 4
        self.PluginHealth["Txt"] = "Startup"

        if self.log is None:
            self.log = LoggingManagement(
                self.pluginconf,
                self.PluginHealth,
                self.HardwareID,
                self.ListOfDevices,
                self.permitTojoin,
            )
            self.log.loggingUpdatePluginVersion(
                str(self.pluginParameters["PluginBranch"] + "-" + self.pluginParameters["PluginVersion"])
            )
            self.log.openLogFile()

        # We can use from now the self.log.logging()
        self.log.logging( "Plugin", "Status", "Z4D starting with %s-%s" % (
            self.pluginParameters["PluginBranch"], self.pluginParameters["PluginVersion"]), )

        if ( _current_python_version_major , _current_python_version_minor) <= ( 3, 7):
            self.log.logging( "Plugin", "Error", "** Please do consider upgrading to a more recent python3 version %s.%s is not supported anymore **" %(
                _current_python_version_major , _current_python_version_minor))

        # Debuging information
        debuging_information(self, "Debug")
         
        if not self.pluginconf.pluginConf[ "PluginAnalytics" ]:
            self.pluginconf.pluginConf[ "PluginAnalytics" ] = -1
 
        self.StartupFolder = Parameters["StartupFolder"]

        self.domoticzdb_DeviceStatus = DomoticzDB_DeviceStatus( 
            Parameters["Mode5"], 
            self.pluginconf, 
            self.HardwareID, 
            self.log,
            self.DomoticzBuild,
            self.DomoticzMajor,
            self.DomoticzMinor,
        )

        self.log.logging("Plugin", "Debug", "   - Hardware table")
        self.domoticzdb_Hardware = DomoticzDB_Hardware(
            Parameters["Mode5"], 
            self.pluginconf, 
            self.HardwareID, 
            self.log, 
            self.pluginParameters ,
            self.DomoticzBuild,
            self.DomoticzMajor,
            self.DomoticzMinor,
            )
        
        if (
            self.zigbee_communication 
            and self.zigbee_communication == "zigpy" 
            and ( self.pluginconf.pluginConf["forceZigpy_noasyncio"] or self.domoticzdb_Hardware.multiinstances_z4d_plugin_instance())
            ):
            # https://github.com/python/cpython/issues/91375
            self.log.logging("Plugin", "Status", "Z4D Multi-instances detected. Enable workaround")
            sys.modules["_asyncio"] = None

        if "LogLevel" not in self.pluginParameters:
            log_level = self.domoticzdb_Hardware.get_loglevel_value()
            if log_level:
                self.pluginParameters["LogLevel"] = log_level
                self.log.logging("Plugin", "Debug", "LogLevel: %s" % self.pluginParameters["LogLevel"])
                
        self.log.logging("Plugin", "Debug", "   - Preferences table")
        
        self.domoticzdb_Preferences = DomoticzDB_Preferences(
            Parameters["Mode5"], 
            self.pluginconf, 
            self.log,
            self.DomoticzBuild,
            self.DomoticzMajor,
            self.DomoticzMinor,
            )
        self.WebUsername, self.WebPassword = self.domoticzdb_Preferences.retreiveWebUserNamePassword()

        self.adminWidgets = AdminWidgets( self.log , self.pluginconf, self.pluginParameters, self.ListOfDomoticzWidget, Devices, self.ListOfDevices, self.HardwareID, self.IEEE2NWK)
        self.adminWidgets.updateStatusWidget(Devices, "Starting up")

        self.DeviceListName = "DeviceList-" + str(Parameters["HardwareID"]) + ".txt"
        self.log.logging("Plugin", "Log", "Z4D Database found: %s" % self.DeviceListName)
        
        z4d_certified_devices_pathname = os.path.dirname( z4d_certified_devices.__file__ ) + "/"
        self.log.logging("Plugin", "Log", "Z4D Certified devices database %s" %z4d_certified_devices_pathname)

        # Import Zcl Cluster definitions
        load_zcl_cluster(self)
        
        # Import Certified Device Configuration
        import_local_device_conf(self)
        z4d_certified_devices.z4d_import_device_configuration(self, z4d_certified_devices_pathname )
        
        # if type(self.DeviceConf) is not dict:
        if not isinstance(self.DeviceConf, dict):
            self.log.logging("Plugin", "Error", "DeviceConf initialisation failure!!! %s" % type(self.DeviceConf))
            self.onStop()
            return
        
        # Initialize List of Domoticz Widgets
        load_list_of_domoticz_widget(self, Devices)
        
        # Import DeviceList.txt Filename is : DeviceListName
        self.log.logging("Plugin", "Status", "Z4D loading database")
        if LoadDeviceList(self) == "Failed":

            self.log.logging("Plugin", "Error", "Something wennt wrong during the import of Load of Devices ...")
            self.log.logging(
                "Plugin",
                "Error",
                "Please cross-check your log ... You must be on V3 of the DeviceList and all DeviceID in Domoticz converted to IEEE",
            )
            self.onStop()
            return

        # Log ListOfDevices dictionary
        self.log.logging("Plugin", "Debug", "ListOfDevices:")
        for key, value in self.ListOfDevices.items():
            self.log.logging("Plugin", "Debug", f" {key}: {value}")

        # Log IEEE2NWK dictionary
        self.log.logging("Plugin", "Debug", "IEEE2NWK:")
        for key, value in self.IEEE2NWK.items():
            self.log.logging("Plugin", "Debug", f" {key}: {value}")

        # Check proper match against Domoticz Devices
        checkListOfDevice2Devices(self, Devices)
        checkDevices2LOD(self, Devices)
    
        for x in self.ListOfDevices:
            # Fixing Profalux Model is required
            if "Model" in self.ListOfDevices[x] and self.ListOfDevices[x]["Model"] in ( "", {} ):
                profalux_fake_deviceModel(self, x)

        self.log.logging("Plugin", "Debug", "ListOfDevices after checkListOfDevice2Devices: " + str(self.ListOfDevices))
        self.log.logging("Plugin", "Debug", "IEEE2NWK after checkListOfDevice2Devices     : " + str(self.IEEE2NWK))

        # Create Statistics object
        self.statistics = TransportStatistics(self.pluginconf, self.log, self.zigbee_communication)

        # Connect to Coordinator only when all initialisation are properly done.
        self.log.logging("Plugin", "Status", "Z4D configured to use transport mode: %s" % self.transport)

        if len(self.ListOfDevices) > 10:
            # Don't do Energy Scan if too many objects, as Energy scan don't make the difference between real traffic and noise
            self.pluginconf.pluginConf["EnergyScanAtStatup"] = 0

        start_zigbee_transport(self )

        if self.transport not in ("ZigpyZNP", "ZigpydeCONZ", "ZigpyEZSP", "ZigpyZiGate", "None" ):
            self.log.logging("Plugin", "Debug", "Establish Zigate connection")
            self.ControllerLink.open_cie_connection()

        # IAS Zone Management
        if self.iaszonemgt is None:
            # Create IAS Zone object
            # Domoticz.Log("Init IAS_Zone_management ZigateComm: %s" %self.ControllerLink)
            self.iaszonemgt = IAS_Zone_Management(self.pluginconf, self.ControllerLink, self.ListOfDevices, self.IEEE2NWK, self.DeviceConf, self.log, self.zigbee_communication, self.readZclClusters, self.FirmwareVersion)

        # Starting WebServer
        if self.webserver is None:
            if Parameters["Mode4"].isdigit() or ':' in Parameters["Mode4"]:
                start_web_server(self, Parameters["Mode4"], Parameters["HomeFolder"])
            else:
                self.log.logging( "Plugin", "Error", "WebServer disabled du to Parameter Mode4 set to %s" % Parameters["Mode4"] )

        if is_domoticz_extended():
            framework_status = "Extended Framework"
        else:
            framework_status = "legacy Framework"
            free_slots = how_many_legacy_slot_available(Devices)
            usage_percentage = round(((255 - free_slots) / 255) * 100, 1)
            self.log.logging("Plugin", "Status", f"Z4D Widgets usage is at {usage_percentage}% ({free_slots} units free)")

        if self.internet_available and self.pluginconf.pluginConf["MatomoOptIn"]:
            matomo_plugin_analytics_infos(self)
        self.log.logging("Plugin", "Status", f"Z4D started with {framework_status}")

        self.busy = False


    def onStop(self):
        """
        Performs cleanup actions when the plugin is stopped.

        Stops various plugin functionalities and saves plugin database.

        Returns:
            None
        """
        Domoticz.Log("onStop()")

        if self.internet_available and self.pluginconf.pluginConf["MatomoOptIn"]:
            matomo_plugin_shutdown(self)
            matomo_plugin_analytics_infos(self)

        # Flush ListOfDevices
        if self.log:
            self.log.logging("Plugin", "Log", "Flushing plugin database onto disk")
        WriteDeviceList(self, 0)  # write immediatly

        # Uninstall Z4D custom UI from Domoticz
        uninstall_Z4D_to_domoticz_custom_ui()

        # Log imported modules if configured
        if self.pluginconf and self.pluginconf.pluginConf["ListImportedModules"]:
            list_all_modules_loaded(self)

        # Log onStop event
        if self.pluginconf and self.log:
            self.log.logging("Plugin", "Log", "onStop called")

        # Close CIE connection and shutdown transport thread
        if self.pluginconf and self.ControllerLink:
            self.ControllerLink.thread_transport_shutdown()
            self.ControllerLink.close_cie_connection()

        # Stop WebServer
        if self.pluginconf and self.webserver:
            self.webserver.onStop()

        # Save plugin database
        if self.PDMready and self.pluginconf:
            WriteDeviceList(self, 0)

        # Print and save statistics if configured
        if self.PDMready and self.pluginconf and self.statistics:
            self.statistics.printSummary()
            self.statistics.writeReport()

        # Close logging management
        if self.pluginconf and self.log:
            self.log.logging("Plugin", "Log", "Closing Logging Management")
            self.log.closeLogFile()

        # Log running threads that need to be shutdown
        for thread in threading.enumerate():
            if thread.name != threading.current_thread().name:
                Domoticz.Log("'" + thread.name + "' is running, it must be shutdown otherwise Domoticz will abort on plugin exit.")

        # Update plugin health status
        self.PluginHealth["Flag"] = 3
        self.PluginHealth["Txt"] = "No Communication"

        if self.adminWidgets:
            self.adminWidgets.updateStatusWidget(Devices, "No Communication")


    def onDeviceRemoved(self, Unit):
        # def onDeviceRemoved(self, DeviceID, Unit):
        if not self.ControllerIEEE:
            self.log.logging( "Plugin", "Error", "onDeviceRemoved - too early, coordinator and plugin initialisation not completed", )

        if self.log:
            self.log.logging("Plugin", "Debug", "onDeviceRemoved called")

        if not is_domoticz_extended():
            DeviceID = find_legacy_DeviceID_from_unit(self, Devices, Unit)

        device_name = domo_read_Name( self, Devices, DeviceID, Unit, )
        
        # Let's check if this is End Node, or Group related.
        if DeviceID in self.IEEE2NWK:
            NwkId = self.IEEE2NWK[DeviceID]

            self.log.logging("Plugin", "Status", f"Removing Device {DeviceID} {device_name} in progress")
            fullyremoved = removeDeviceInList(self, Devices, DeviceID, Unit)

            # We might have to remove also the Device from Groups
            if fullyremoved:
                if self.groupmgt:
                    self.groupmgt.RemoveNwkIdFromAllGroups(NwkId)

                # sending a Leave Request to device, so the device will send a leave
                leaveRequest(self, ShortAddr=NwkId, IEEE=DeviceID)

                # for a remove in case device didn't send the leave
                zigate_remove_device(self, str(self.ControllerIEEE), str(DeviceID) )
                self.log.logging( "Plugin", "Status", f"Request device {device_name} -> {DeviceID} to be removed from coordinator" )

            self.log.logging("Plugin", "Debug", f"ListOfDevices :After REMOVE {self.ListOfDevices}")
            load_list_of_domoticz_widget(self, Devices)
            return

        if self.groupmgt and DeviceID in self.groupmgt.ListOfGroups:
            self.log.logging("Plugin", "Status", f"Request device {DeviceID} to be remove from Group(s)")
            self.groupmgt.FullRemoveOfGroup(Unit, DeviceID)


    def onConnect(self, Connection, Status, Description):

        self.log.logging( "Plugin", "Debug", "onConnect %s called with status: %s and Desc: %s" % (Connection, Status, Description) )

        decodedConnection = decodeConnection(str(Connection))
        if "Protocol" in decodedConnection and decodedConnection["Protocol"] in ( "HTTP", "HTTPS", ):  # We assumed that is the Web Server
            if self.webserver:
                self.webserver.onConnect(Connection, Status, Description)
            return

        self.busy = True

        if Status != 0:
            _onConnect_status_error(self, Status, Description)
            return

        self.log.logging("Plugin", "Debug", "Connected successfully")
        if self.connectionState is None:
            self.PluginHealth["Flag"] = 2
            self.PluginHealth["Txt"] = "Starting Up"
            self.adminWidgets.updateStatusWidget(Devices, "Starting the plugin up")

        elif self.connectionState == 0:
            self.log.logging("Plugin", "Status", "Z4D reconnected after failure")
            self.PluginHealth["Flag"] = 2
            self.PluginHealth["Txt"] = "Reconnecting after failure"

        self.connectionState = 1
        self.Ping["Status"] = None
        self.Ping["TimeStamp"] = None
        self.Ping["Permit"] = None
        self.Ping["Nb Ticks"] = 1

        return True


    def onMessage(self, Connection, Data):
        # self.log.logging( 'Plugin', 'Debug', "onMessage called on Connection " + " Data = '" +str(Data) + "'")
        if self.webserver and isinstance(Data, dict):
            self.webserver.onMessage(Connection, Data)
            return

        if len(Data) == 0:
            self.log.logging("Plugin", "Error", "onMessage - empty message received on %s" % Connection)

        self.Ping["Nb Ticks"] = 0
        self.connectionState = 1
        self.ControllerLink.on_message(Data)


    def processFrame(self, Data):
        if not self.VersionNewFashion:
            return
        self.connectionState = 1
        # start_time = int(time.time() *1000)
        zigbee_receive_message(self, Devices, Data)
        # stop_time = int(time.time() *1000)
        # Domoticz.Log("### Completion: %s is %s ms" %(Data, ( stop_time - start_time)))


    def zigpy_chk_upd_device(self, ieee, nwkid ):
        chk_and_update_IEEE_NWKID(self, nwkid, ieee)


    def zigpy_get_device(self, ieee=None, nwkid=None):
        # allow to inter-connect zigpy world and plugin
        self.log.logging("TransportZigpy", "Debug", "zigpy_get_device( %s, %s)" %( ieee, nwkid))

        sieee = ieee
        snwkid = nwkid
        
        if nwkid and nwkid not in self.ListOfDevices and ieee and ieee in self.IEEE2NWK:
            # Most likely we have a new Nwkid, let see if we can reconnect
            lookupForIEEE(self, nwkid, reconnect=True)

        if nwkid and nwkid in self.ListOfDevices and 'IEEE' in self.ListOfDevices[ nwkid ]:
            ieee = self.ListOfDevices[ nwkid ]['IEEE']
        elif ieee and ieee in self.IEEE2NWK:
            nwkid = self.IEEE2NWK[ ieee ]
        else:
            self.log.logging("TransportZigpy", "Debug", "zigpy_get_device( %s(%s), %s(%s)) NOT FOUND" %( sieee, type(sieee), snwkid, type(snwkid) ))
            return None

        self.log.logging("TransportZigpy", "Debug", "zigpy_get_device( %s, %s returns %04x %016x" %( sieee, snwkid, int(nwkid,16), int(ieee,16) ))
        return int(nwkid,16) ,int(ieee,16)


    def zigpy_backup_available(self, backups):
        handle_zigpy_backup(self, backups)


    def restart_plugin(self):
        """ This is used as a call back function for zigpy connection_lost handling"""
        error_message = "Connection lost with coordinator, restarting plugin"
        self.log.logging("Plugin", "Error", error_message)
        self.adminWidgets.updateNotificationWidget(Devices, error_message)
        if self.internet_available and self.pluginconf.pluginConf["MatomoOptIn"]:
            matomo_plugin_restart(self)

        restartPluginViaDomoticzJsonApi(self, stop=False, url_base_api=Parameters["Mode5"])

    #def onCommand(self, DeviceID, Unit, Command, Level, Color):
    def onCommand(self, Unit, Command, Level, Color):
        if (  self.ControllerLink is None or not self.VersionNewFashion or self.pluginconf is None or not self.log ):
            self.log.logging( "Command", "Log", "onCommand - Not yet ready, plugin not fully started, we drop the command")
            return

        self.log.logging( "Command", "Debug", "onCommand - unit: %s, command: %s, level: %s, color: %s" % (Unit, Command, Level, Color) )

        if not is_domoticz_extended():
            DeviceID = find_legacy_DeviceID_from_unit(self, Devices, Unit)
        
        # Let's check if this is End Node, or Group related.
        if DeviceID in self.IEEE2NWK:
            # Command belongs to a end node
            domoticz_command(self, Devices, DeviceID, Unit, self.IEEE2NWK[ DeviceID], Command, Level, Color)

        elif self.groupmgt and DeviceID in self.groupmgt.ListOfGroups:
            # Command belongs to a Zigate group
            self.log.logging( "Command", "Log", "Command: %s/%s/%s to Group: %s" % (Command, Level, Color, DeviceID), )
            self.groupmgt.processCommand(Unit, DeviceID, Command, Level, Color)

        elif DeviceID.find("Zigate-01-") != -1:
            self.log.logging("Command", "Debug", "onCommand - Command adminWidget: %s " % Command)
            self.adminWidgets.handleCommand(self, Command)

        else:
            self.log.logging( "Command", "Error", "onCommand - Unknown device or GrpMgr not enabled %s, unit %s , id %s" % (domo_read_Name( self, Devices, DeviceID, Unit, ), Unit, DeviceID), )


    def onDisconnect(self, Connection):

        self.log.logging("Plugin", "Debug", "onDisconnect: %s" % Connection)
        decodedConnection = decodeConnection(str(Connection))

        if "Protocol" in decodedConnection and decodedConnection["Protocol"] in (
            "HTTP",
            "HTTPS",
        ):  # We assumed that is the Web Server
            if self.webserver:
                self.webserver.onDisconnect(Connection)
            return

        self.connectionState = 0
        self.PluginHealth["Flag"] = 0
        self.PluginHealth["Txt"] = "Shutdown"
        self.adminWidgets.updateStatusWidget(Devices, "Plugin stop")
        self.log.logging("Plugin", "Status", "onDisconnect called")


    def onHeartbeat(self):

        if not self.VersionNewFashion or self.pluginconf is None or self.log is None:
            # Not yet ready
            return
        
        self.internalHB += 1

        if self.PDMready:
            if (self.internalHB % HEARTBEAT) != 0:
                return
            self.HeartbeatCount += 1
            
        # Quiet a bad hack. In order to get the needs for ZigateRestart
        # from WebServer
        if "startZigateNeeded" in self.ControllerData and self.ControllerData["startZigateNeeded"]:
            self.startZigateNeeded = self.HeartbeatCount
            del self.ControllerData["startZigateNeeded"]

        # Starting PDM on Host firmware version, we have to wait that Zigate is fully initialized ( PDM loaded into memory from Host).
        # We wait for self.zigateReady which is set to True in th pdmZigate module
        if not _coordinator_ready(self):
            return

        if self.transport != "None":
            self.log.logging(
                "Plugin",
                "Debug",
                "onHeartbeat - busy = %s, Health: %s, startZigateNeeded: %s/%s, InitPhase1: %s InitPhase2: %s, InitPhase3: %s PDM_LOCK: %s ErasePDMinProgress: %s ErasePDMDone: %s"
                % ( self.busy, self.PluginHealth, self.startZigateNeeded, self.HeartbeatCount, self.InitPhase1, self.InitPhase2, self.InitPhase3, self.ControllerLink.pdm_lock_status(), self.ErasePDMinProgress, self.ErasePDMDone, ),
            )

        if not _post_readiness_startup_completed( self ):
            return

        if self.transport != "None" and not self.InitPhase3:
            zigateInit_Phase3(self)
            return

        # Checking Version
        if self.internet_available:
            _check_plugin_version( self )

            if self.pluginconf.pluginConf["MatomoOptIn"] and self.HeartbeatCount % ( (9 * 3600) // HEARTBEAT) == 0:
                matomo_plugin_analytics_infos(self)

        if self.transport == "None":
            return

        # Memorize the size of Devices. This is will allow to trigger a backup of live data to file, if the size change.
        prevLenDevices = len(Devices)

        # Manage all entries in  ListOfDevices (existing and up-coming devices)
        processListOfDevices(self, Devices)

        # Check and Update Heating demand for Wiser if applicable (this will be check in the call)
        wiser_thermostat_monitoring_heating_demand(self, Devices)
        # Group Management
        if self.groupmgt:
            self.groupmgt.hearbeat_group_mgt()

        # Write the ListOfDevice every 15 minutes or immediatly if we have remove or added a Device
        if len(Devices) == prevLenDevices:
            WriteDeviceList(self, ( (15 * 60) // HEARTBEAT) )

        else:
            self.log.logging("Plugin", "Debug", "Devices size has changed , let's write ListOfDevices on disk")
            WriteDeviceList(self, 0)  # write immediatly
            networksize_update(self)
  
        _trigger_coordinator_backup( self )

        if self.CommiSSionning:
            self.PluginHealth["Flag"] = 2
            self.PluginHealth["Txt"] = "Enrollment in Progress"
            self.adminWidgets.updateStatusWidget(Devices, "Enrollment")

            # Maintain trend statistics
            self.statistics._Load = self.ControllerLink.loadTransmit()
            self.statistics.addPointforTrendStats(self.HeartbeatCount)
            return

        # OTA upgrade
        if self.OTA:
            self.OTA.heartbeat()

        # Check PermitToJoin
        _check_permit_to_joint_status(self)

        if self.HeartbeatCount % (3600 // HEARTBEAT) == 0:
            self.log.loggingCleaningErrorHistory()
            zigate_get_time(self)
            #sendZigateCmd(self, "0017", "")

        if self.zigbee_communication == "zigpy" and self.pluginconf.pluginConf["ZigpyTopologyReport"] and self.zigpy_topology and self.HeartbeatCount % (60 // HEARTBEAT) == 0:
            retreive_zigpy_topology_data(self)

        self.busy = _check_if_busy(self)
        return True


def _onConnect_status_error(self, Status, Description):
    self.log.logging("Plugin", "Error", "Failed to connect (" + str(Status) + ")")
    self.log.logging("Plugin", "Debug", "Failed to connect (" + str(Status) + ") with error: " + Description)
    self.connectionState = 0
    self.ControllerLink.re_conn()
    self.PluginHealth["Flag"] = 3
    self.PluginHealth["Txt"] = "No Communication"
    self.adminWidgets.updateStatusWidget(Devices, "No Communication")


def retreive_zigpy_topology_data(self):
    # Determine sync period based on existing data
    if self.zigpy_topology is None:
        return
    
    if self.zigpy_topology.is_zigpy_topology_in_progress():
        # Scan in progress
        self.zigpy_topology.new_scan_detected = True
        return

    is_manual_scan = self.ListOfDevices["0000"].get("ZigpyTopologyRequested", False)
    if self.zigpy_topology.new_scan_detected and ( self.pluginconf.pluginConf["ZigpyTopologyReportAutoBackup"] or is_manual_scan):
        # Scan is completed. Time for a backup
        self.zigpy_topology.save_topology_report()
        self.zigpy_topology.new_scan_detected = False
        self.ListOfDevices["0000"]["ZigpyTopologyRequested"] = False
        return
    
    # coordinator_data = self.ListOfDevices.get("0000", {})
    # if "ZigpyNeighbors" in coordinator_data and "ZigpyRoutes" in coordinator_data:
    #     return
    # self.zigpy_topology.copy_zigpy_infos_to_plugin()
    # coordinator_data = self.ListOfDevices.get("0000", {})
    # if "ZigpyNeighbors" not in coordinator_data and "ZigpyRoutes" not in coordinator_data:
    #     self.log.logging("Plugin", "Log", "onHeartbeat request zigpy topology scan as not data available")
    #     self.ControllerLink.sendData("ZIGPY-TOPOLOGY-SCAN", {})


def start_zigbee_transport(self ):
    
    if self.transport in ("USB", "DIN", "V2-DIN", "V2-USB"):
        check_python_modules_version( self  )
        _start_native_usb_zigate(self)

    elif self.transport in ("PI", "V2-PI"):
        _start_native_pi_zigate(self)

    elif self.transport in ("Wifi", "V2-Wifi"):
        _start_native_wifi_zigate(self)

    elif self.transport == "None":
        _start_fake_coordinator(self)

    elif self.transport == "ZigpyZNP":
        _start_zigpy_ZNP(self)
        
    elif self.transport == "ZigpydeCONZ":
        _start_zigpy_deConz(self)
                
    elif self.transport == "ZigpyEZSP":
        _start_zigpy_EZSP(self) 
        
    else:
        self.log.logging("Plugin", "Error", "Unknown Transport comunication protocol : %s" % str(self.transport))
        self.onStop()
        return


def _start_fake_coordinator(self):
        from Classes.ZigateTransport.Transport import ZigateTransport
        self.pluginconf.pluginConf["ControllerInRawMode"] = False
        self.pluginParameters["Zigpy"] = False
        self.log.logging("Plugin", "Status", "Transport mode set to None, no communication.")
        self.FirmwareVersion = "031c"
        self.PluginHealth["Firmware Update"] = {"Progress": "75 %", "Device": "1234"}
    

def _start_native_usb_zigate(self):
    _start_native_zigate(self, serialPort=Parameters["SerialPort"])


def _start_native_pi_zigate(self):
    switchPiZigate_mode(self, "run")
    _start_native_zigate(self, serialPort=Parameters["SerialPort"])


def _start_native_wifi_zigate(self):
    _start_native_zigate(self, wifiAddress=Parameters["Address"], wifiPort=Parameters["Port"])


def _start_native_zigate(self, serialPort=None, wifiAddress=None, wifiPort=None):
    from Classes.ZigateTransport.Transport import ZigateTransport
    check_python_modules_version(self )
    self.pluginconf.pluginConf["ControllerInRawMode"] = False
    self.zigbee_communication = "native"
    self.pluginParameters["Zigpy"] = False
    
    kwargs = {
        "HardwareID": self.HardwareID,
        "DomoticzBuild": self.DomoticzBuild,
        "DomoticzMajor": self.DomoticzMajor,
        "DomoticzMinor": self.DomoticzMinor,
        "transport": self.transport,
        "statistics": self.statistics,
        "pluginconf": self.pluginconf,
        "processFrame": self.processFrame,
        "log": self.log,
    }
    if serialPort:
        kwargs["serialPort"] = serialPort
    if wifiAddress:
        kwargs["wifiAddress"] = wifiAddress
    if wifiPort:
        kwargs["wifiPort"] = wifiPort

    self.ControllerLink = ZigateTransport(**kwargs)   
        

def _start_zigpy_ZNP(self):
    import zigpy
    import zigpy_znp
    from zigpy.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                              SCHEMA_DEVICE)

    from Classes.ZigpyTransport.Transport import ZigpyTransport

    #self.pythonModuleVersion["zigpy"] = (zigpy.__version__)
    # https://github.com/zigpy/zigpy-znp/issues/205
    #self.pythonModuleVersion["zigpy_znp"] = import_version( 'zigpy-znp' )
    
    check_python_modules_version( self )
    self.zigbee_communication = "zigpy"
    self.pluginParameters["Zigpy"] = True
    self.log.logging("Plugin", "Status", "Z4D starting ZNP")
    
    self.ControllerLink= ZigpyTransport(
        self.ControllerData, self.pluginParameters, self.pluginconf,self.processFrame, self.zigpy_chk_upd_device, self.zigpy_get_device, self.zigpy_backup_available, self.restart_plugin, self.log, self.statistics, self.HardwareID, "znp", Parameters["SerialPort"]
        )
    self.ControllerLink.open_cie_connection()
    self.pluginconf.pluginConf["ControllerInRawMode"] = True
    

def _start_zigpy_deConz(self):
    import zigpy
    import zigpy_deconz
    from zigpy.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                              SCHEMA_DEVICE)

    from Classes.ZigpyTransport.Transport import ZigpyTransport

    #self.pythonModuleVersion["zigpy"] = (zigpy.__version__)
    #self.pythonModuleVersion["zigpy_deconz"] = (zigpy_deconz.__version__)
    check_python_modules_version( self )
    self.pluginParameters["Zigpy"] = True
    self.log.logging("Plugin", "Status","Z4D starting deConz")            
    self.ControllerLink= ZigpyTransport(
        self.ControllerData, self.pluginParameters, self.pluginconf,self.processFrame, self.zigpy_chk_upd_device, self.zigpy_get_device, self.zigpy_backup_available, self.restart_plugin, self.log, self.statistics, self.HardwareID, "deCONZ", Parameters["SerialPort"]
        )
    self.ControllerLink.open_cie_connection()
    self.pluginconf.pluginConf["ControllerInRawMode"] = True
    

def _start_zigpy_EZSP(self):
    import bellows
    import zigpy
    from zigpy.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                              SCHEMA_DEVICE)

    from Classes.ZigpyTransport.Transport import ZigpyTransport

    #self.pythonModuleVersion["zigpy"] = (zigpy.__version__)
    #self.pythonModuleVersion["zigpy_ezsp"] = (bellows.__version__)
    check_python_modules_version( self )
    self.zigbee_communication = "zigpy"
    self.pluginParameters["Zigpy"] = True
    self.log.logging("Plugin", "Status","Z4D starting EZSP")

    if Parameters["Mode2"] == "Socket":
        SerialPort = "socket://" + Parameters["IP"] + ':' + Parameters["Port"]
        self.transport += "Socket"
    else:
        SerialPort = Parameters["SerialPort"]

    SerialPort = Parameters["SerialPort"]
    
    self.ControllerLink= ZigpyTransport(
        self.ControllerData, self.pluginParameters, self.pluginconf,self.processFrame, self.zigpy_chk_upd_device, self.zigpy_get_device, self.zigpy_backup_available, self.restart_plugin, self.log, self.statistics, self.HardwareID, "ezsp", SerialPort
        )
    self.ControllerLink.open_cie_connection()
    self.pluginconf.pluginConf["ControllerInRawMode"] = True
    
    
def zigateInit_Phase1(self):
    """
    Mainly managed Erase PDM if required
    """
    self.log.logging("Plugin", "Debug", "zigateInit_Phase1 PDMDone: %s" % (self.ErasePDMDone))
    # Check if we have to Erase PDM.
    if self.zigbee_communication == "native" and Parameters["Mode3"] == "True" and not self.ErasePDMDone and not self.ErasePDMinProgress:  # Erase PDM
        zigate_erase_eeprom(self)
        if self.internet_available and self.pluginconf.pluginConf["MatomoOptIn"]:
            matomo_coordinator_initialisation(self)
        self.log.logging("Plugin", "Status", "Z4D has erase the Zigate PDM")
        #sendZigateCmd(self, "0012", "")
        self.PDMready = False
        self.startZigateNeeded = 1
        self.HeartbeatCount = 1
        update_DB_device_status_to_reinit( self )
        return
    elif self.zigbee_communication == "zigpy" and Parameters["Mode3"] == "True" and not self.ErasePDMDone and not self.ErasePDMinProgress: 
        self.log.logging("Plugin", "Status", "Z4D requests to form a new network")
        if self.internet_available and self.pluginconf.pluginConf["MatomoOptIn"]:
            matomo_coordinator_initialisation(self)

        self.ErasePDMinProgress = True
        update_DB_device_status_to_reinit( self )
        return

    self.busy = False
    self.InitPhase1 = True
    return True


def zigateInit_Phase2(self):
    """
    Make sure that all setup is in place
    """
    if self.FirmwareVersion is None or self.ControllerIEEE is None or self.ControllerNWKID == "ffff":
        if self.FirmwareVersion is None:
            # Ask for Firmware Version
            #sendZigateCmd(self, "0010", "")
            zigate_get_firmware_version(self)
        if self.ControllerIEEE is None or self.ControllerNWKID == "ffff":
            # Request Network State
            zigate_get_nwk_state(self)
            #sendZigateCmd(self, "0009", "")

        if self.HeartbeatCount > TIMEDOUT_FIRMWARE:
            self.log.logging(
                "Plugin",
                "Error",
                "We are having difficulties to start coordinator. Basically we are not receiving what we expect from CIE",
            )
            self.log.logging("Plugin", "Error", "Plugin is not started ...")
        return

    # Set Time server to HOST time
    if self.zigbee_communication == "native":
        setTimeServer(self)
    
    # Make sure Zigate is in Standard mode
    if self.zigbee_communication == "native":
        zigate_set_mode(self, 0x00)

    # If applicable, put Zigate in NO Pairing Mode
    self.Ping["Permit"] = None
    if self.pluginconf.pluginConf["resetPermit2Join"]:
        ZigatePermitToJoin(self, 0)
    else:
        zdp_get_permit_joint_status(self)
        #sendZigateCmd(self, "0014", "")  # Request Permit to Join status

    # Request List of Active Devices
    if self.zigbee_communication == "native":
        zigate_get_list_active_devices(self)
    #sendZigateCmd(self, "0015", "")

    # Ready for next phase
    self.InitPhase2 = True


def zigateInit_Phase3(self):

    # We can now do what must be done when we known the Firmware version
    if self.FirmwareVersion is None:
        return

    if self.transport != "None" and Parameters["Mode3"] == "True" and self.ErasePDMDone and self.domoticzdb_Hardware:
        self.log.logging("Plugin", "Debug", "let's update Mode3 is needed")
        self.domoticzdb_Hardware.disableErasePDM( self.WebUsername, self.WebPassword)

    if self.InitPhase3:
        return

    self.InitPhase3 = True

    self.pluginParameters["FirmwareVersion"] = self.FirmwareVersion

    if self.transport != "None" and self.zigbee_communication == "native" and not check_firmware_level(self):
        self.log.logging("Plugin", "Debug", "Firmware not ready")
        return

    if self.pluginconf.pluginConf["blueLedOnOff"]:
        zigateBlueLed(self, True)
    else:
        zigateBlueLed(self, False)

    # Set the TX Power
    if self.ZiGateModel == 1:
        set_TxPower(self, self.pluginconf.pluginConf["TXpower_set"])

    # Set Certification Code
    if self.pluginconf.pluginConf["CertificationCode"] in CERTIFICATION:
        self.log.logging( "Plugin", "Status", "Z4D coordinator set to Certification : %s/%s -> %s" % (
            self.pluginconf.pluginConf["CertificationCode"], self.pluginconf.pluginConf["Certification"], CERTIFICATION[self.pluginconf.pluginConf["CertificationCode"]],))
        #sendZigateCmd(self, "0019", "%02x" % self.pluginconf.pluginConf["CertificationCode"])
        zigate_set_certificate(self, "%02x" % self.pluginconf.pluginConf["CertificationCode"] )


        # Create Configure Reporting object
        if self.configureReporting is None:
            self.log.logging("Plugin", "Status", "Z4D starts Configure Reporting handling")
            self.configureReporting = ConfigureReporting(
                self.zigbee_communication,
                self.pluginconf,
                self.DeviceConf,
                self.ControllerLink,
                self.ListOfDevices,
                Devices,
                self.log,
                self.busy,
                self.FirmwareVersion,
                self.IEEE2NWK,
                self.ControllerIEEE,
                self.readZclClusters
            )
        if self.configureReporting:
            self.webserver.update_configureReporting(self.configureReporting )

    # Enable Group Management
    if self.groupmgt is None and self.pluginconf.pluginConf["enablegroupmanagement"]:
        self.log.logging("Plugin", "Status", "Z4D starts Group Management")
        start_GrpManagement(self, Parameters["HomeFolder"])

    # Create Network Energy object
    if self.networkenergy is None:
        self.networkenergy = NetworkEnergy(
            self.zigbee_communication, self.pluginconf, self.ControllerLink, self.ListOfDevices, Devices, self.HardwareID, self.log
        )

    if self.networkenergy:
        self.webserver.update_networkenergy(self.networkenergy)

        # Create Network Map object
    if self.networkmap is None:
        self.networkmap = NetworkMap(
            self.zigbee_communication ,self.pluginconf, self.ControllerLink, self.ListOfDevices, Devices, self.HardwareID, self.log
        )
    
    if self.zigpy_topology is None:
        self.zigpy_topology = ZigpyTopology(
            self.zigbee_communication ,self.pluginconf, self.ControllerLink, self.ListOfDevices, self.IEEE2NWK, Devices, self.HardwareID, self.log
        )

    if self.networkmap:
        self.webserver.update_networkmap(self.networkmap)

    # Enable Over The Air Upgrade if applicable
    if self.OTA is None and self.pluginconf.pluginConf["allowOTA"]:
        self.log.logging("Plugin", "Status", "Z4D starts Over-The-Air Management")
        start_OTAManagement(self, Parameters["HomeFolder"])

    networksize_update(self)
    build_list_of_device_model(self, force=True)

    # Request to resend the IRCode with the next command of Casaia/Owon ACxxxx
    restart_plugin_reset_ModuleIRCode(self, nwkid=None)

    firmware_messages = {
        "03": "Z4D with Zigate coordinator, firmware %s communication confirmed",
        "04": "Z4D with Zigate coordinator, OptiPDM firmware %s communication confirmed",
        "05": "Z4D with Zigate+ coordinator, firmware %s communication confirmed"
    }

    # Check if firmware major version exists in the dictionary
    if self.FirmwareMajorVersion in firmware_messages:
        message = firmware_messages[self.FirmwareMajorVersion] % self.FirmwareVersion
        self.log.logging("Plugin", "Status", message)

    elif int(self.FirmwareBranch) >= 20:
        message = "Z4D with Zigpy, coordinator %s, firmware %s communication confirmed." % (
            self.pluginParameters["CoordinatorModel"], self.pluginParameters["CoordinatorFirmwareVersion"])
        self.log.logging("Plugin", "Status", message)

    # If firmware above 3.0d, Get Network State
    if (self.HeartbeatCount % (3600 // HEARTBEAT)) == 0 and self.transport != "None":
        zigate_get_nwk_state(self)

    if self.iaszonemgt and self.ControllerIEEE:
        self.iaszonemgt.setZigateIEEE(self.ControllerIEEE)
    
    if self.internet_available and self.pluginconf.pluginConf["MatomoOptIn"]:
        matomo_plugin_started(self)


def start_GrpManagement(self, homefolder):
    
    self.groupmgt = GroupsManagement(
        self.zigbee_communication,
        self.VersionNewFashion,
        self.DomoticzMajor,
        self.DomoticzMinor,
        self.DomoticzBuild,
        self.pluginconf,
        self.ControllerLink,
        self.adminWidgets,
        Parameters["HomeFolder"],
        self.HardwareID,
        Devices,
        self.ListOfDevices,
        self.IEEE2NWK,
        self.ListOfDomoticzWidget,
        self.DeviceConf, 
        self.log,
        self.readZclClusters,
        self.pluginParameters,
    )
    if self.groupmgt and self.ControllerIEEE:
        self.groupmgt.updateZigateIEEE(self.ControllerIEEE)

    if self.groupmgt:
        self.webserver.update_groupManagement(self.groupmgt)
        if self.zigbee_communication != "zigpy" and self.pluginconf.pluginConf["zigatePartOfGroup0000"]:
            # Add Zigate NwkId 0x0000 Ep 0x01 to GroupId 0x0000
            self.groupmgt.addGroupMemberShip("0000", "01", "0000")

        if self.zigbee_communication != "zigpy" and self.pluginconf.pluginConf["zigatePartOfGroupTint"]:
            # Tint Remote manage 4 groups and we will create with ZiGate attached.
            self.groupmgt.addGroupMemberShip("0000", "01", "4003")
            self.groupmgt.addGroupMemberShip("0000", "01", "4004")
            self.groupmgt.addGroupMemberShip("0000", "01", "4005")
            self.groupmgt.addGroupMemberShip("0000", "01", "4006")


def start_OTAManagement(self, homefolder):
    self.OTA = OTAManagement(
        self.zigbee_communication,
        self.pluginconf,
        self.DeviceConf,
        self.adminWidgets,
        self.ControllerLink,
        homefolder,
        self.HardwareID,
        Devices,
        self.ListOfDevices,
        self.IEEE2NWK,
        self.log,
        self.PluginHealth,
        self.readZclClusters,
        self.internet_available
    )
    if self.OTA:
        self.webserver.update_OTA(self.OTA)


def start_web_server(self, webserver_port, webserver_homefolder):
 
    self.log.logging("Plugin", "Status", "Z4D starts WebUI")
    self.webserver = WebServer(
        self.zigbee_communication,
        self.ControllerData,
        self.pluginParameters,
        self.pluginconf,
        self.statistics,
        self.adminWidgets,
        self.ControllerLink,
        webserver_homefolder,
        self.HardwareID,
        Devices,
        self.ListOfDomoticzWidget, 
        self.ListOfDevices,
        self.IEEE2NWK,
        self.DeviceConf,
        self.permitTojoin,
        self.WebUsername,
        self.WebPassword,
        self.PluginHealth,
        webserver_port,
        self.log,
        self.transport,
        self.ModelManufMapping,
        self.DomoticzMajor,
        self.DomoticzMinor,
        self.readZclClusters,
        self.device_settings
    )
    if self.FirmwareVersion:
        self.webserver.update_firmware(self.FirmwareVersion)


def pingZigate(self):

    """
    Ping Zigate to check if it is alive.
    Do it only if no messages have been received during the last period

    'Nb Ticks' is set to 0 every time a message is received from Zigate
    'Nb Ticks' is incremented at every heartbeat
    """
    if self.zigbee_communication != "native":
        return
    
    # Frequency is set to below 4' as regards to the TCP timeout with Wifi-Zigate
    PING_CHECK_FREQ = ((5 * 60) / 2) - 7

    self.log.logging(
        "Plugin",
        "Debug",
        "pingZigate - [%s] Nb Ticks: %s Status: %s TimeStamp: %s"
        % (self.HeartbeatCount, self.Ping["Nb Ticks"], self.Ping["Status"], self.Ping["TimeStamp"]),
    )

    if self.Ping["Nb Ticks"] == 0:  # We have recently received a message, Zigate is up and running
        self.Ping["Status"] = "Receive"
        self.connectionState = 1
        self.log.logging("Plugin", "Debug", "pingZigate - We have receive a message in the cycle ")
        return  # Most likely between the cycle.

    if self.Ping["Status"] == "Sent":
        delta = int(time.time()) - self.Ping["TimeStamp"]
        self.log.logging(
            "Plugin",
            "Log",
            "pingZigate - WARNING: Ping sent but no response yet from Zigate. Status: %s  - Ping: %s sec"
            % (self.Ping["Status"], delta),
        )
        if delta > 56:  # Seems that we have lost the Zigate communication

            self.log.logging("Plugin", "Error", "pingZigate - no Heartbeat with Zigate, try to reConnect")
            self.adminWidgets.updateNotificationWidget(Devices, "Ping: Connection with Zigate Lost")
            # self.connectionState = 0
            # self.Ping['TimeStamp'] = int(time.time())
            # self.ControllerLink.re_conn()
            restartPluginViaDomoticzJsonApi(self, stop=False, url_base_api=Parameters["Mode5"])

        elif (self.Ping["Nb Ticks"] % 3) == 0:
            zdp_get_permit_joint_status(self)
            #sendZigateCmd(self, "0014", "")  # Request status
        return

    # If we are more than PING_CHECK_FREQ without any messages, let's check
    if self.Ping["Nb Ticks"] and self.Ping["Nb Ticks"] < (PING_CHECK_FREQ // HEARTBEAT):
        self.connectionState = 1
        self.log.logging(
            "Plugin", "Debug", "pingZigate - We have receive a message less than %s sec  ago " % PING_CHECK_FREQ
        )
        return

    if "Status" not in self.Ping:
        self.log.logging("Plugin", "Log", "pingZigate - Unknown Status, Ticks: %s  Send a Ping" % self.Ping["Nb Ticks"])
        zdp_get_permit_joint_status(self)
        #sendZigateCmd(self, "0014", "")  # Request status
        self.Ping["Status"] = "Sent"
        self.Ping["TimeStamp"] = int(time.time())
        return

    if self.Ping["Status"] == "Receive":
        if self.connectionState == 0:
            # self.adminWidgets.updateStatusWidget( self, Devices, 'Ping: Reconnected after failure')
            self.log.logging("Plugin", "Status", "Z4D - reconnected after failure")
        self.log.logging(
            "Plugin",
            "Debug",
            "pingZigate - Status: %s Send a Ping, Ticks: %s" % (self.Ping["Status"], self.Ping["Nb Ticks"]),
        )
        zdp_get_permit_joint_status(self)
        #sendZigateCmd(self, "0014", "")  # Request status
        self.connectionState = 1
        self.Ping["Status"] = "Sent"
        self.Ping["TimeStamp"] = int(time.time())
    else:
        self.log.logging("Plugin", "Error", "pingZigate - unknown status : %s" % self.Ping["Status"])

                
def debuging_information(self, mode):
    """
    Logs debugging information based on the provided mode.

    Args:
        mode (str): Logging mode.

    Returns:
        None
    """
    debug_info = {
        "Is GC enabled": gc.isenabled(),
        "DomoticzVersion": Parameters["DomoticzVersion"],
        "Debug": Parameters["Mode6"],
        "Python Version": sys.version,
        "DomoticzHash": Parameters["DomoticzHash"],
        "DomoticzBuildTime": Parameters["DomoticzBuildTime"],
        "Startup Folder": Parameters["StartupFolder"],
        "Home Folder": Parameters["HomeFolder"],
        "User Data Folder": Parameters["UserDataFolder"],
        "Web Root Folder": Parameters["WebRoot"],
        "Database": Parameters["Database"]
    }

    # Log debug information
    for info_name, info_value in debug_info.items():
        self.log.logging("Plugin", mode, "%s: %s" % (info_name, info_value))

 
global _plugin  # pylint: disable=global-variable-not-assigned
_plugin = BasePlugin()


def onStart():
    global _plugin  # pylint: disable=global-variable-not-assigned
    _plugin.onStart()


def onStop():
    global _plugin  # pylint: disable=global-variable-not-assigned
    _plugin.onStop()


#def onDeviceRemoved(DeviceID, Unit):
def onDeviceRemoved( Unit):
    global _plugin  # pylint: disable=global-variable-not-assigned
    #_plugin.onDeviceRemoved(DeviceID, Unit)
    _plugin.onDeviceRemoved( Unit)


def onConnect(Connection, Status, Description):
    global _plugin  # pylint: disable=global-variable-not-assigned
    _plugin.onConnect(Connection, Status, Description)


def onMessage(Connection, Data):
    global _plugin  # pylint: disable=global-variable-not-assigned
    _plugin.onMessage(Connection, Data)


#def onCommand(DeviceID, Unit, Command, Level, Color):
def onCommand(Unit, Command, Level, Color):
    global _plugin
    #_plugin.onCommand(DeviceID, Unit, Command, Level, Color)
    _plugin.onCommand( Unit, Command, Level, Color)


def onDisconnect(Connection):
    global _plugin  # pylint: disable=global-variable-not-assigned
    _plugin.onDisconnect(Connection)


def onHeartbeat():
    global _plugin  # pylint: disable=global-variable-not-assigned
    _plugin.onHeartbeat()


# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Log("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Log("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Log("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Log("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Log("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Log("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Log("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Log("Device LastLevel: " + str(Devices[x].LastLevel))
        Domoticz.Log("Device Options: " + str(Devices[x].Options))


def DumpHTTPResponseToLog(httpDict):
    if isinstance(httpDict, dict):
        Domoticz.Log("HTTP Details (" + str(len(httpDict)) + "):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                Domoticz.Log("--->'" + x + " (" + str(len(httpDict[x])) + "):")
                for y in httpDict[x]:
                    Domoticz.Log("------->'" + y + "':'" + str(httpDict[x][y]) + "'")
            else:
                Domoticz.Log("--->'" + x + "':'" + str(httpDict[x]) + "'")


def install_Z4D_to_domoticz_custom_ui():

    line1 = '<iframe id="%s"' %Parameters['Name'] + 'style="width:100%;height:800px;overflow:scroll;">\n'
    line2 = '</iframe>\n'
    line3 = '\n'
    line4 = '<script>\n'
    line5 = 'document.getElementById(\'%s\').src' %Parameters['Name'] + ' = "http://" + location.hostname + ":%s/z4d/";\n' %Parameters['Mode4']
    #line5 = 'document.getElementById(\'%s\').src' %Parameters['Name'] + ' = location.protocol + "/z4d/";\n' 
    line6 = '</script>\n'

    _startupfolder = pathlib.Path( Parameters['StartupFolder'] )
    custom_file = _startupfolder / 'www/templates' / f"{Parameters['Name']}.html"
    Domoticz.Log(f"Installing plugin custom page {custom_file} ")

    try:
        with open( custom_file, "wt") as z4d_html_file:
            z4d_html_file.write( line1 )
            z4d_html_file.write( line2 )
            z4d_html_file.write( line3 )
            z4d_html_file.write( line4 )
            z4d_html_file.write( line5 )
            z4d_html_file.write( line6 )
    except Exception as e:
        Domoticz.Error('Error during installing plugin custom page')
        Domoticz.Error(repr(e))


def uninstall_Z4D_to_domoticz_custom_ui():

    custom_file = Parameters['StartupFolder'] + 'www/templates/' + f"{Parameters['Name']}" + '.html'
    try:
        if os.path.exists(custom_file ):
            os.remove(custom_file )

    except Exception as e:
        Domoticz.Error('Error during installing plugin custom page')
        Domoticz.Error(repr(e))


def _check_if_busy(self):
    busy_ = self.ControllerLink.loadTransmit() >= MAX_FOR_ZIGATE_BUZY
    # Maintain trend statistics
    self.statistics._Load = self.ControllerLink.loadTransmit()
    self.statistics.addPointforTrendStats(self.HeartbeatCount)

    if busy_:
        self.PluginHealth["Flag"] = 2
        self.PluginHealth["Txt"] = "Busy"
        self.adminWidgets.updateStatusWidget(Devices, "Busy")

    elif not self.connectionState:
        self.PluginHealth["Flag"] = 3
        self.PluginHealth["Txt"] = "No Communication"
        self.adminWidgets.updateStatusWidget(Devices, "No Communication")

    else:
        self.PluginHealth["Flag"] = 1
        self.PluginHealth["Txt"] = "Ready"
        self.adminWidgets.updateStatusWidget(Devices, "Ready")


def _check_permit_to_joint_status(self):
    if (
        self.permitTojoin["Duration"] != 255
        and self.permitTojoin["Duration"] != 0
        and int(time.time()) >= (self.permitTojoin["Starttime"] + self.permitTojoin["Duration"])
    ):
        zdp_get_permit_joint_status(self)
        #sendZigateCmd(self, "0014", "")  # Request status
        self.permitTojoin["Duration"] = 0

    # Heartbeat - Ping Zigate every minute to check connectivity
    # If fails then try to reConnect
    if self.pluginconf.pluginConf["Ping"] and self.zigbee_communication == "native":
        pingZigate(self)
        self.Ping["Nb Ticks"] += 1


def _trigger_coordinator_backup( self ):
    if (
        self.zigbee_communication
        and self.zigbee_communication == "zigpy"
        and "autoBackup" in self.pluginconf.pluginConf 
        and self.pluginconf.pluginConf["autoBackup"] 
        and night_shift_jobs( self ) 
        and self.internalHB % (24 * 3600 // HEARTBEAT) == 0
        and self.ControllerLink
    ):
        self.ControllerLink.sendData( "COORDINATOR-BACKUP", {})


def _check_plugin_version( self ):
    self.pluginParameters["TimeStamp"] = int(time.time())
    if self.transport != "None" and self.pluginconf.pluginConf["internetAccess"] and (
        self.pluginParameters["available"] is None or self.HeartbeatCount % (12 * 3600 // HEARTBEAT) == 0
    ):
        (
            self.pluginParameters["available"],
            self.pluginParameters["available-firmMajor"],
            self.pluginParameters["available-firmMinor"],
        ) = check_plugin_version_against_dns(self, self.zigbee_communication, self.pluginParameters["PluginBranch"], self.FirmwareMajorVersion)
        self.pluginParameters["FirmwareUpdate"] = False
        self.pluginParameters["PluginUpdate"] = False

        if is_plugin_update_available(self, self.pluginParameters["PluginVersion"], self.pluginParameters["available"]):
            self.log.logging("Plugin", "Status", "Z4D found a recent plugin version (%s) on gitHub. You are on (%s) ***" %(
                self.pluginParameters["available"], self.pluginParameters["PluginVersion"] ))
            self.pluginParameters["PluginUpdate"] = True
        if is_zigate_firmware_available(
            self,
            self.FirmwareMajorVersion,
            self.FirmwareVersion,
            self.pluginParameters["available-firmMajor"],
            self.pluginParameters["available-firmMinor"],
        ):
            self.log.logging("Plugin", "Status", "Z4D found a newer Zigate Firmware version")
            self.pluginParameters["FirmwareUpdate"] = True


def _coordinator_ready( self ):
    self.log.logging( "Plugin", "Debug", "_coordinator_ready transport: %s PDMready: %s" %(self.transport, self.PDMready)) 
    if self.transport == "None" or self.PDMready:
        return True

    if (
        (
            ( self.transport == "ZigpyZNP" and self.internalHB > ZNP_STARTUP_TIMEOUT_DELAY_FOR_WARNING ) 
            or ( self.transport != "ZigpyZNP" and self.internalHB > STARTUP_TIMEOUT_DELAY_FOR_WARNING ) 
        ) 
        and (self.internalHB % 10) == 0
    ):
        self.log.logging( "Plugin", "Error", "[%3s] I have hard time to get Coordinator Version. Most likely there is a communication issue" % (self.internalHB), )
        
    if (
        ( self.transport == "ZigpyZNP" and self.internalHB > ZNP_STARTUP_TIMEOUT_DELAY_FOR_STOP )
        or ( self.transport != "ZigpyZNP" and self.internalHB > STARTUP_TIMEOUT_DELAY_FOR_STOP) 
    ):
        debuging_information(self, "Log")
        # (#1371) we cannot stop the plugin as it will disable the hardware and generate side effect. So we will try for ever
        restartPluginViaDomoticzJsonApi(self, stop=False, url_base_api=Parameters["Mode5"])

    if (self.internalHB % 10) == 0:
        self.log.logging( "Plugin", "Debug", "[%s] PDMready: %s requesting Get version" % (self.internalHB, self.PDMready) )
        zigate_get_firmware_version(self)
        #sendZigateCmd(self, "0010", "")
        return False
    
    return False
    
    
def _post_readiness_startup_completed( self ):
    if self.transport != "None" and (self.startZigateNeeded or not self.InitPhase1 or not self.InitPhase2):
        # Require Transport
        # Perform erasePDM if required
        if not self.InitPhase1:
            zigateInit_Phase1(self)
            return False

        # Check if Restart is needed ( After an ErasePDM or a Soft Reset
        if self.startZigateNeeded:
            if self.HeartbeatCount > self.startZigateNeeded + TEMPO_START_ZIGATE:
                # Need to check if and ErasePDM has been performed.
                # In case case, we have to set the extendedPANID
                # ErasePDM has been requested, we are in the next Loop.
                if self.ErasePDMDone and self.pluginconf.pluginConf["extendedPANID"] is not None:
                    self.log.logging( "Plugin", "Status", "Z4D - Setting extPANID : 0x%016x" % (self.pluginconf.pluginConf["extendedPANID"]), )
                    setExtendedPANID(self, self.pluginconf.pluginConf["extendedPANID"])

                start_Zigate(self)
                self.startZigateNeeded = False
            return False

        if not self.InitPhase2:
            zigateInit_Phase2(self)
            return False
        
    return True
