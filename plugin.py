#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
<plugin key="Zigate" name="Zigbee for domoticz plugin (zigpy enabled)" author="pipiche38" version="6.2">
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
        <param field="Mode1" label="Coordinator Model" width="75px" required="true" default="None">
            <description><br/><h3>Zigbee Coordinator definition</h3><br/>Select the Zigbee radio Coordinator version : ZiGate (V1), ZiGate+ (V2), Texas Instrument ZNP, or Silicon Labs EZSP</description>
            <options>
                <option label="ZiGate"  value="V1"/>
                <option label="ZiGate+" value="V2"/>
                <option label="Texas Instruments ZNP (via zigpy)" value="ZigpyZNP"/>
                <option label="Silicon Labs EZSP (via zigpy)" value="ZigpyEZSP"/>
                <option label="ConBee/RasBee (via zigpy)" value="ZigpydeCONZ"/>
                <option label="ZiGate ZNP (via zigpy ** for developpers only **)" value="ZigpyZiGate"/>
            </options>
        </param>
        <param field="Mode2" label="Coordinator Type" width="75px" required="true" default="None">
            <description><br/>Select the Radio Coordinator connection type : USB, DIN, Pi, TCPIP (Wifi, Ethernet)</description>
            <options>
                <option label="USB"   value="USB" />
                <option label="DIN"   value="DIN" />
                <option label="PI"    value="PI" />
                <option label="TCPIP" value="Wifi"/>
                <option label="None"  value="None"/>
            </options>
        </param>
        <param field="SerialPort" label="Serial Port" width="150px" required="true" default="/dev/ttyUSB0" >
            <description><br/>Set the serial port where the Radio Coordinator is connected (/dev/ttyUSB0 for example)</description>
        </param>
        <param field="Address" label="IP" width="150px" required="true" default="0.0.0.0">
            <description><br/>Set the Radio Coordinator IP adresse (0.0.0.0 if not applicable)</description>
        </param>
        <param field="Port" label="Port" width="150px" required="true" default="9999">
            <description><br/>Set the Radio Coordinator Port (9999 by default)</description>
        </param>
        <param field="Mode5" label="API base url <br/>(http://username:password@127.0.0.1:port)" width="250px" default="http://127.0.0.1:8080" required="true" >
            <description>
                <br/><h3>Domoticz Json/API base ( http://127.0.0.1:8080 should be the default)</h3>In case Domoticz listen to an other port change 8080 by what ever is the port, 
                and if you have setup an authentication please add the username:password</description>
        </param>
        <param field="Mode4" label="WebUI port" width="75px" required="true" default="9440" >
            <description><br/><h3>Plugin definition</h3><br/>Set the plugin Dashboard port (9440 by default, None to disable)<br/>
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
                            <option label="None" value="2"  default="true"/>
                </options>
        </param>
            
    </params>
</plugin>
"""

import pathlib
import sys

from pkg_resources import DistributionNotFound

import Domoticz

try:
    from Domoticz import Devices, Images, Parameters, Settings
except ImportError:
    pass

import gc
import json
import os
import threading
import time

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
from Modules.basicOutputs import (ZigatePermitToJoin, leaveRequest,
                                  setExtendedPANID, setTimeServer,
                                  start_Zigate, zigateBlueLed)
from Modules.casaia import restart_plugin_reset_ModuleIRCode
from Modules.checkingUpdate import (checkFirmwareUpdate, checkPluginUpdate,
                                    checkPluginVersion)
from Modules.command import mgtCommand
from Modules.database import (LoadDeviceList, WriteDeviceList,
                              checkDevices2LOD, checkListOfDevice2Devices,
                              importDeviceConfV2)
from Modules.domoCreate import how_many_slot_available
from Modules.domoTools import ResetDevice
from Modules.heartbeat import processListOfDevices
from Modules.input import ZigateRead
from Modules.piZigate import switchPiZigate_mode
from Modules.restartPlugin import restartPluginViaDomoticzJsonApi
from Modules.schneider_wiser import wiser_thermostat_monitoring_heating_demand
from Modules.tools import (chk_and_update_IEEE_NWKID, get_device_nickname,
                           how_many_devices, lookupForIEEE, night_shift_jobs,
                           removeDeviceInList)
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

#from zigpy_zigate.config import CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA, SCHEMA_DEVICE
#from Classes.ZigpyTransport.Transport import ZigpyTransport
#import asyncio


VERSION_FILENAME = ".hidden/VERSION"

TEMPO_NETWORK = 2  # Start HB totrigget Network Status
TIMEDOUT_START = 10  # Timeoud for the all startup
TIMEDOUT_FIRMWARE = 5  # HB before request Firmware again
TEMPO_START_ZIGATE = 1  # Nb HB before requesting a Start_Zigate

STARTUP_TIMEOUT_DELAY_FOR_WARNING = 60
STARTUP_TIMEOUT_DELAY_FOR_STOP = 120
ZNP_STARTUP_TIMEOUT_DELAY_FOR_WARNING = 110
ZNP_STARTUP_TIMEOUT_DELAY_FOR_STOP = 160

REQUIRES = ["aiohttp", "aiosqlite>=0.16.0", "crccheck", "pycryptodome", "voluptuous"]

class BasePlugin:
    enabled = False

    def __init__(self):

        self.ListOfDevices = (
            {}
        )  # {DevicesAddresse : { status : status_de_detection, data : {ep list ou autres en fonctions du status}}, DevicesAddresse : ...}
        self.DiscoveryDevices = {}  # Used to collect pairing information
        self.IEEE2NWK = {}
        self.ControllerData = {}
        self.DeviceConf = {}  # Store DeviceConf.txt, all known devices configuration

        # Objects from Classe
        self.configureReporting = None
        self.ControllerLink= None
        self.groupmgt = None
        self.networkmap = None
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
        self.DomoticzMajor = None
        self.DomoticzMinor = None

        self.WebUsername = None
        self.WebPassword = None

        self.PluzzyFirmware = False
        self.pluginVersion = {}

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
        self.pythonModuleVersion = {}

    def onStart(self):
        Domoticz.Log("Zigbee for Domoticz plugin started!")
        assert sys.version_info >= (3, 4)  # nosec
        
        if check_requirements( self ):
            self.onStop()
            return

        if check_requirements( self ):
            self.onStop()
            return

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

        if Parameters["Mode5"] == "" or "http://" not in Parameters["Mode5"]:
            Domoticz.Error("Please cross-check the Domoticz Hardware settingi for the plugin instance. >%s< You must set the API base URL" %Parameters["Mode5"])
            self.onStop()

        # Set plugin heartbeat to 1s
        Domoticz.Heartbeat(1)

        # Copy the Domoticz.Parameters to a variable accessible in the all objetc
        self.pluginParameters = dict(Parameters)

        # Open VERSION file in .hidden
        with open(Parameters["HomeFolder"] + VERSION_FILENAME, "rt") as versionfile:
            try:
                _pluginversion = json.load(versionfile)
            except Exception as e:
                Domoticz.Error("Error when opening: %s -- %s" % (Parameters["HomeFolder"] + VERSION_FILENAME, e))
                self.onStop()
                return

        self.pluginParameters["PluginBranch"] = _pluginversion["branch"]
        self.pluginParameters["PluginVersion"] = _pluginversion["version"]
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
        
        if not get_domoticz_version( self ):
            return


        # Import PluginConf.txt
        Domoticz.Log("load PluginConf")
        self.pluginconf = PluginConf(
            self.zigbee_communication, self.VersionNewFashion, self.DomoticzMajor, self.DomoticzMinor, Parameters["HomeFolder"], self.HardwareID
        )

        # Create Domoticz Sub menu
        if "DomoticzCustomMenu" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["DomoticzCustomMenu"] :
            install_Z4D_to_domoticz_custom_ui( )

        # Create the adminStatusWidget if needed
        self.PluginHealth["Flag"] = 4
        self.PluginHealth["Txt"] = "Startup"

        if self.log is None:
            Domoticz.Log("Starting LoggingManagement thread")
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
        self.log.logging(
            "Plugin",
            "Status",
            "Zigbee for Domoticz (z4d) plugin %s-%s started"
            % (self.pluginParameters["PluginBranch"], self.pluginParameters["PluginVersion"]),
        )

        # Debuging information
        debuging_information(self, "Debug")
         
        self.StartupFolder = Parameters["StartupFolder"]

        self.domoticzdb_DeviceStatus = DomoticzDB_DeviceStatus( Parameters["Mode5"], self.pluginconf, self.HardwareID, self.log )

        self.log.logging("Plugin", "Debug", "   - Hardware table")
        self.domoticzdb_Hardware = DomoticzDB_Hardware( Parameters["Mode5"], self.pluginconf, self.HardwareID, self.log, self.pluginParameters )
        
        if (
            self.zigbee_communication 
            and self.zigbee_communication == "zigpy" 
            and ( self.pluginconf.pluginConf["forceZigpy_noasyncio"] or self.domoticzdb_Hardware.multiinstances_z4d_plugin_instance())
        ):
            self.log.logging("Plugin", "Status", "Multi instances plugin detected. Enable zigpy workaround")
            sys.modules["_asyncio"] = None
        
        if "LogLevel" not in self.pluginParameters:
            log_level = self.domoticzdb_Hardware.get_loglevel_value()
            if log_level:
                self.pluginParameters["LogLevel"] = log_level
                self.log.logging("Plugin", "Debug", "LogLevel: %s" % self.pluginParameters["LogLevel"])
                
        self.log.logging("Plugin", "Debug", "   - Preferences table")
        
        self.domoticzdb_Preferences = DomoticzDB_Preferences(Parameters["Mode5"], self.pluginconf, self.log)
        self.WebUsername, self.WebPassword = self.domoticzdb_Preferences.retreiveWebUserNamePassword()
        # Domoticz.Status("Domoticz Website credentials %s/%s" %(self.WebUsername, self.WebPassword))

        self.adminWidgets = AdminWidgets(self.pluginconf, Devices, self.ListOfDevices, self.HardwareID)
        self.adminWidgets.updateStatusWidget(Devices, "Startup")

        self.DeviceListName = "DeviceList-" + str(Parameters["HardwareID"]) + ".txt"
        self.log.logging("Plugin", "Log", "Plugin Database: %s" % self.DeviceListName)


        # Import Certified Device Configuration
        importDeviceConfV2(self)

        # if type(self.DeviceConf) is not dict:
        if not isinstance(self.DeviceConf, dict):
            self.log.logging("Plugin", "Error", "DeviceConf initialisation failure!!! %s" % type(self.DeviceConf))
            self.onStop()
            return
            

        # Import DeviceList.txt Filename is : DeviceListName
        self.log.logging("Plugin", "Status", "load ListOfDevice")
        if LoadDeviceList(self) == "Failed":
            self.log.logging("Plugin", "Error", "Something wennt wrong during the import of Load of Devices ...")
            self.log.logging(
                "Plugin",
                "Error",
                "Please cross-check your log ... You must be on V3 of the DeviceList and all DeviceID in Domoticz converted to IEEE",
            )
            self.onStop()
            return
            

        self.log.logging("Plugin", "Debug", "ListOfDevices : ")
        for e in self.ListOfDevices.items():
            self.log.logging("Plugin", "Debug", " " + str(e))

        self.log.logging("Plugin", "Debug", "IEEE2NWK      : ")
        for e in self.IEEE2NWK.items():
            self.log.logging("Plugin", "Debug", "  " + str(e))

        # Check proper match against Domoticz Devices
        checkListOfDevice2Devices(self, Devices)
        checkDevices2LOD(self, Devices)

        self.log.logging("Plugin", "Debug", "ListOfDevices after checkListOfDevice2Devices: " + str(self.ListOfDevices))
        self.log.logging("Plugin", "Debug", "IEEE2NWK after checkListOfDevice2Devices     : " + str(self.IEEE2NWK))

        # Create Statistics object
        self.statistics = TransportStatistics(self.pluginconf)

        # Connect to Zigate only when all initialisation are properly done.
        self.log.logging("Plugin", "Status", "Transport mode: %s" % self.transport)
        if self.transport in ("USB", "DIN", "V2-DIN", "V2-USB"):
            from Classes.ZigateTransport.Transport import ZigateTransport
            
            check_python_modules_version( self )
            
            self.zigbee_communication = "native"
            self.pluginParameters["Zigpy"] = False
            self.ControllerLink= ZigateTransport(
                self.HardwareID,
                self.DomoticzBuild,
                self.DomoticzMajor,
                self.DomoticzMinor,
                self.transport,
                self.statistics,
                self.pluginconf,
                self.processFrame,
                self.log,
                serialPort=Parameters["SerialPort"],
            )

        elif self.transport in ("PI", "V2-PI"):
            from Classes.ZigateTransport.Transport import ZigateTransport
            check_python_modules_version( self )
            self.pluginconf.pluginConf["ControllerInRawMode"] = False
            switchPiZigate_mode(self, "run")
            self.zigbee_communication = "native"
            self.pluginParameters["Zigpy"] = False
            self.ControllerLink= ZigateTransport(
                self.HardwareID,
                self.DomoticzBuild,
                self.DomoticzMajor,
                self.DomoticzMinor,
                self.transport,
                self.statistics,
                self.pluginconf,
                self.processFrame,
                self.log,
                serialPort=Parameters["SerialPort"],
            )

        elif self.transport in ("Wifi", "V2-Wifi"):
            from Classes.ZigateTransport.Transport import ZigateTransport
            check_python_modules_version( self )
            self.pluginconf.pluginConf["ControllerInRawMode"] = False
            self.zigbee_communication = "native"
            self.pluginParameters["Zigpy"] = False
            self.ControllerLink= ZigateTransport(
                self.HardwareID,
                self.DomoticzBuild,
                self.DomoticzMajor,
                self.DomoticzMinor,
                self.transport,
                self.statistics,
                self.pluginconf,
                self.processFrame,
                self.log,
                wifiAddress=Parameters["Address"],
                wifiPort=Parameters["Port"],
            )

        elif self.transport == "None":
            from Classes.ZigateTransport.Transport import ZigateTransport
            self.pluginconf.pluginConf["ControllerInRawMode"] = False
            self.pluginParameters["Zigpy"] = False
            self.log.logging("Plugin", "Status", "Transport mode set to None, no communication.")
            self.FirmwareVersion = "031c"
            self.PluginHealth["Firmware Update"] = {"Progress": "75 %", "Device": "1234"}

        elif self.transport == "ZigpyZiGate":
            # Zigpy related modules
            import zigpy
            import zigpy_zigate
            from Classes.ZigpyTransport.Transport import ZigpyTransport
            from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH,
                                             CONFIG_SCHEMA, SCHEMA_DEVICE)
            self.pythonModuleVersion["zigpy"] = (zigpy.__version__)
            self.pythonModuleVersion["zigpy_zigate"] = (zigpy_zigate.__version__)
            check_python_modules_version( self )
            self.zigbee_communication = "zigpy"
            self.pluginParameters["Zigpy"] = True
            self.log.logging("Plugin", "Status", "Start Zigpy Transport on zigate")
            self.ControllerLink= ZigpyTransport( self.ControllerData, self.pluginParameters, self.pluginconf, self.processFrame, self.zigpy_chk_upd_device, self.zigpy_get_device, self.zigpy_backup_available, self.log, self.statistics, self.HardwareID, "zigate", Parameters["SerialPort"]) 
            self.ControllerLink.open_cie_connection()
            self.pluginconf.pluginConf["ControllerInRawMode"] = True
            
        elif self.transport == "ZigpyZNP":
            import zigpy
            import zigpy_znp
            from Classes.ZigpyTransport.Transport import ZigpyTransport
            from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH,
                                             CONFIG_SCHEMA, SCHEMA_DEVICE)
            self.pythonModuleVersion["zigpy"] = (zigpy.__version__)
            self.pythonModuleVersion["zigpy_znp"] = (zigpy_znp.__version__)
            check_python_modules_version( self )
            self.zigbee_communication = "zigpy"
            self.pluginParameters["Zigpy"] = True
            self.log.logging("Plugin", "Status", "Start Zigpy Transport on ZNP")
            
            self.ControllerLink= ZigpyTransport( self.ControllerData, self.pluginParameters, self.pluginconf,self.processFrame, self.zigpy_chk_upd_device, self.zigpy_get_device, self.zigpy_backup_available, self.log, self.statistics, self.HardwareID, "znp", Parameters["SerialPort"])  
            self.ControllerLink.open_cie_connection()
            self.pluginconf.pluginConf["ControllerInRawMode"] = True
            
        elif self.transport == "ZigpydeCONZ":
            import zigpy
            import zigpy_deconz
            from Classes.ZigpyTransport.Transport import ZigpyTransport
            from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH,
                                             CONFIG_SCHEMA, SCHEMA_DEVICE)
            self.pythonModuleVersion["zigpy"] = (zigpy.__version__)
            self.pythonModuleVersion["zigpy_deconz"] = (zigpy_deconz.__version__)
            check_python_modules_version( self )
            self.pluginParameters["Zigpy"] = True
            self.log.logging("Plugin", "Status","Start Zigpy Transport on deCONZ")            
            self.ControllerLink= ZigpyTransport( self.ControllerData, self.pluginParameters, self.pluginconf,self.processFrame, self.zigpy_chk_upd_device, self.zigpy_get_device, self.zigpy_backup_available, self.log, self.statistics, self.HardwareID, "deCONZ", Parameters["SerialPort"])  
            self.ControllerLink.open_cie_connection()
            self.pluginconf.pluginConf["ControllerInRawMode"] = True
            
        elif self.transport == "ZigpyEZSP":
            import bellows
            import zigpy
            from Classes.ZigpyTransport.Transport import ZigpyTransport
            from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH,
                                             CONFIG_SCHEMA, SCHEMA_DEVICE)
            self.pythonModuleVersion["zigpy"] = (zigpy.__version__)
            self.pythonModuleVersion["zigpy_ezsp"] = (bellows.__version__)
            check_python_modules_version( self )
            self.zigbee_communication = "zigpy"
            self.pluginParameters["Zigpy"] = True
            self.log.logging("Plugin", "Status","Start Zigpy Transport on EZSP")
            self.ControllerLink= ZigpyTransport( self.ControllerData, self.pluginParameters, self.pluginconf,self.processFrame, self.zigpy_chk_upd_device, self.zigpy_get_device, self.zigpy_backup_available, self.log, self.statistics, self.HardwareID, "ezsp", Parameters["SerialPort"])  
            self.ControllerLink.open_cie_connection()
            self.pluginconf.pluginConf["ControllerInRawMode"] = True
          
        else:
            self.log.logging("Plugin", "Error", "Unknown Transport comunication protocol : %s" % str(self.transport))
            self.onStop()
            return
            

        if self.transport not in ("ZigpyZNP", "ZigpydeCONZ", "ZigpyEZSP", "ZigpyZiGate", "None" ):
            self.log.logging("Plugin", "Debug", "Establish Zigate connection")
            self.ControllerLink.open_cie_connection()

        # IAS Zone Management
        if self.iaszonemgt is None:
            # Create IAS Zone object
            # Domoticz.Log("Init IAS_Zone_management ZigateComm: %s" %self.ControllerLink)
            self.iaszonemgt = IAS_Zone_Management(self.pluginconf, self.ControllerLink, self.ListOfDevices, self.IEEE2NWK, self.DeviceConf, self.log, self.zigbee_communication, self.FirmwareVersion)

            # Starting WebServer
        if self.webserver is None:
            if Parameters["Mode4"].isdigit():
                start_web_server(self, Parameters["Mode4"], Parameters["HomeFolder"])
            else:
                self.log.logging(
                    "Plugin", "Error", "WebServer disabled du to Parameter Mode4 set to %s" % Parameters["Mode4"]
                )

        self.log.logging("Plugin", "Status", "Domoticz Widgets usage is at %s %% (%s units free)" % (
            round( ( ( 255 - how_many_slot_available( Devices )) / 255 ) * 100, 1 ), how_many_slot_available( Devices ) ))
        self.busy = False

    def onStop(self):  # sourcery skip: class-extract-method
        Domoticz.Log("onStop()")
        uninstall_Z4D_to_domoticz_custom_ui()

        if self.pluginconf and self.log:
            self.log.logging("Plugin", "Log", "onStop called")
            self.log.logging("Plugin", "Log", "onStop calling (1) domoticzDb DeviceStatus closed")
            
        if self.pluginconf and self.log:
            self.log.logging("Plugin", "Log", "onStop calling (3) Transport off")
            
        if self.pluginconf and self.ControllerLink:
            self.ControllerLink.thread_transport_shutdown()
            self.ControllerLink.close_cie_connection()

        if self.pluginconf and self.log:
            self.log.logging("Plugin", "Log", "onStop calling (4) WebServer off")
            
        if self.pluginconf and self.webserver:
            self.webserver.onStop()
            
        if self.pluginconf and self.log:
            self.log.logging("Plugin", "Log", "onStop called (4) WebServer off")
            
        if self.pluginconf and self.log:
            self.log.logging("Plugin", "Log", "onStop calling (5) Plugin Database saved")
          
        if self.pluginconf:
            WriteDeviceList(self, 0)
        
        if self.pluginconf and self.log:
            self.log.logging("Plugin", "Log", "onStop called (5) Plugin Database saved")

        if self.pluginconf and self.statistics:
            self.statistics.printSummary()
            self.statistics.writeReport()

        if self.pluginconf and self.log:
            self.log.logging("Plugin", "Log", "onStop calling (6) Close Logging Management")
            self.log.closeLogFile()
            self.log.logging("Plugin", "Log", "onStop called (6) Close Logging Management")

        for thread in threading.enumerate():
            if thread.name != threading.current_thread().name:
                Domoticz.Log( "'" + thread.name + "' is running, it must be shutdown otherwise Domoticz will abort on plugin exit.")

        self.PluginHealth["Flag"] = 3
        self.PluginHealth["Txt"] = "No Communication"
        if self.adminWidgets:
            self.adminWidgets.updateStatusWidget(Devices, "No Communication")

    def onDeviceRemoved(self, Unit):
        if self.log:
            self.log.logging("Plugin", "Debug", "onDeviceRemoved called")

        # Let's check if this is End Node, or Group related.
        if Devices[Unit].DeviceID in self.IEEE2NWK:
            IEEE = Devices[Unit].DeviceID
            NwkId = self.IEEE2NWK[IEEE]

            # Command belongs to a end node
            self.log.logging("Plugin", "Status", "onDeviceRemoved - removing End Device")
            fullyremoved = removeDeviceInList(self, Devices, Devices[Unit].DeviceID, Unit)

            # We might have to remove also the Device from Groups
            if fullyremoved and self.groupmgt:
                self.groupmgt.RemoveNwkIdFromAllGroups(NwkId)

            # We should call this only if All Widgets have been remved !
            if fullyremoved:
                # Let see if enabled if we can fully remove this object from Zigate
                if self.pluginconf.pluginConf["allowRemoveZigateDevice"]:
                    IEEE = Devices[Unit].DeviceID
                    # sending a Leave Request to device, so the device will send a leave
                    leaveRequest(self, ShortAddr=NwkId, IEEE=IEEE)

                    # for a remove in case device didn't send the leave
                    if self.ControllerIEEE:
                        #sendZigateCmd(self, "0026", self.ControllerIEEE + IEEE)
                        zigate_remove_device(self, str(self.ControllerIEEE), str(IEEE) )
                        self.log.logging(
                            "Plugin",
                            "Status",
                            "onDeviceRemoved - removing Device %s -> %s from coordinator" % (Devices[Unit].Name, IEEE),
                        )
                    else:
                        self.log.logging(
                            "Plugin",
                            "Error",
                            "onDeviceRemoved - too early, coordinator and plugin initialisation not completed",
                        )
                else:
                    self.log.logging(
                        "Plugin",
                        "Status",
                        "onDeviceRemoved - device entry %s from coordinator not removed. You need to enable 'allowRemoveZigateDevice' parameter. Do consider that it works only for main powered devices."
                        % Devices[Unit].DeviceID,
                    )

            self.log.logging("Plugin", "Debug", "ListOfDevices :After REMOVE " + str(self.ListOfDevices))
            return

        if self.groupmgt and Devices[Unit].DeviceID in self.groupmgt.ListOfGroups:
            self.log.logging("Plugin", "Status", "onDeviceRemoved - removing Group of Devices")
            # Command belongs to a Zigate group
            self.groupmgt.FullRemoveOfGroup(Unit, Devices[Unit].DeviceID)

    def onConnect(self, Connection, Status, Description):

        self.log.logging("Plugin", "Debug", "onConnect called with status: %s" % Status)
        self.log.logging(
            "Plugin", "Debug", "onConnect %s called with status: %s and Desc: %s" % (Connection, Status, Description)
        )

        decodedConnection = decodeConnection(str(Connection))
        if "Protocol" in decodedConnection and decodedConnection["Protocol"] in (
            "HTTP",
            "HTTPS",
        ):  # We assumed that is the Web Server
            if self.webserver:
                self.webserver.onConnect(Connection, Status, Description)
            return

        self.busy = True

        if Status != 0:
            self.log.logging("Plugin", "Error", "Failed to connect (" + str(Status) + ")")
            self.log.logging("Plugin", "Debug", "Failed to connect (" + str(Status) + ") with error: " + Description)
            self.connectionState = 0
            self.ControllerLink.re_conn()
            self.PluginHealth["Flag"] = 3
            self.PluginHealth["Txt"] = "No Communication"
            self.adminWidgets.updateStatusWidget(Devices, "No Communication")
            return

        self.log.logging("Plugin", "Debug", "Connected successfully")
        if self.connectionState is None:
            self.PluginHealth["Flag"] = 2
            self.PluginHealth["Txt"] = "Starting Up"
            self.adminWidgets.updateStatusWidget(Devices, "Starting the plugin up")
        elif self.connectionState == 0:
            self.log.logging("Plugin", "Status", "Reconnected after failure")
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
        if isinstance(Data, dict):
            if self.webserver:
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
        ZigateRead(self, Devices, Data)
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

        # model = manuf = None
        #if nwkid in self.ListOfDevices and "Model" in self.ListOfDevices[ nwkid ] and self.ListOfDevices[ nwkid ]["Model"] not in ( "", {} ):
        #    model = self.ListOfDevices[ nwkid ]["Model"]
        #if nwkid in self.ListOfDevices and "Manufacturer" in self.ListOfDevices[ nwkid ] and self.ListOfDevices[ nwkid ]["Manufacturer"] not in ( "", {} ):
        #    manuf = self.ListOfDevices[ nwkid ]["Manufacturer"]

        self.log.logging("TransportZigpy", "Debug", "zigpy_get_device( %s, %s returns %04x %016x" %( sieee, snwkid, int(nwkid,16), int(ieee,16) ))
        return int(nwkid,16) ,int(ieee,16)

    def zigpy_backup_available(self, backups):
        handle_zigpy_backup(self, backups)


    def onCommand(self, Unit, Command, Level, Color):
        self.log.logging(
            "Plugin", "Debug", "onCommand - unit: %s, command: %s, level: %s, color: %s" % (Unit, Command, Level, Color)
        )

        # Let's check if this is End Node, or Group related.
        if Devices[Unit].DeviceID in self.IEEE2NWK:
            # Command belongs to a end node
            mgtCommand(self, Devices, Unit, Command, Level, Color)

        elif self.groupmgt:
            # if Devices[Unit].DeviceID in self.groupmgt.ListOfGroups:
            #    # Command belongs to a Zigate group
            if self.log:
                self.log.logging(
                    "Plugin",
                    "Debug",
                    "Command: %s/%s/%s to Group: %s" % (Command, Level, Color, Devices[Unit].DeviceID),
                )
            self.groupmgt.processCommand(Unit, Devices[Unit].DeviceID, Command, Level, Color)

        elif Devices[Unit].DeviceID.find("Zigate-01-") != -1:
            if self.log:
                self.log.logging("Plugin", "Debug", "onCommand - Command adminWidget: %s " % Command)
            self.adminWidgets.handleCommand(self, Command)

        else:
            self.log.logging(
                "Plugin",
                "Error",
                "onCommand - Unknown device or GrpMgr not enabled %s, unit %s , id %s"
                % (Devices[Unit].Name, Unit, Devices[Unit].DeviceID),
            )

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

        if not self.VersionNewFashion or self.pluginconf is None:
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
        _check_plugin_version( self )

        if self.transport == "None":
            return

        # Memorize the size of Devices. This is will allow to trigger a backup of live data to file, if the size change.
        prevLenDevices = len(Devices)

        do_python_garbage_collection( self )

        # Manage all entries in  ListOfDevices (existing and up-coming devices)
        processListOfDevices(self, Devices)

        # Check and Update Heating demand for Wiser if applicable (this will be check in the call)
        wiser_thermostat_monitoring_heating_demand(self, Devices)
        # Group Management
        if self.groupmgt:
            self.groupmgt.hearbeat_group_mgt()

        # Write the ListOfDevice every 5 minutes or immediatly if we have remove or added a Device
        if len(Devices) == prevLenDevices:
            WriteDeviceList(self, ( (5 * 60) // HEARTBEAT) )
            
        else:
            self.log.logging("Plugin", "Debug", "Devices size has changed , let's write ListOfDevices on disk")
            WriteDeviceList(self, 0)  # write immediatly
            networksize_update(self)

        
        # Update the NetworkDevices attributes if needed , once by day
        build_list_of_device_model(self)

        _trigger_coordinator_backup( self )

        if self.CommiSSionning:
            self.PluginHealth["Flag"] = 2
            self.PluginHealth["Txt"] = "Enrollment in Progress"
            self.adminWidgets.updateStatusWidget(Devices, "Enrollment")

            # Maintain trend statistics
            self.statistics._Load = self.ControllerLink.loadTransmit()
            self.statistics.addPointforTrendStats(self.HeartbeatCount)
            return

        # Reset Motion sensors
        ResetDevice(self, Devices, "Motion", 5)

        # OTA upgrade
        if self.OTA:
            self.OTA.heartbeat()

        # Check PermitToJoin
        _check_permit_to_joint_status(self)

        if self.HeartbeatCount % (3600 // HEARTBEAT) == 0:
            self.log.loggingCleaningErrorHistory()
            zigate_get_time(self)
            #sendZigateCmd(self, "0017", "")

        self.busy = _check_if_busy(self)
        return True

def networksize_update(self):
    self.log.logging("Plugin", "Debug", "Devices size has changed , let's write ListOfDevices on disk")
    routers, enddevices = how_many_devices(self)
    self.pluginParameters["NetworkSize"] = "Total: %s | Routers: %s | End Devices: %s" %(
        routers + enddevices, routers, enddevices)

def build_list_of_device_model(self, force=False):
    
    if not force and ( self.internalHB % (23 * 3600 // HEARTBEAT) != 0):
        return
    
    self.pluginParameters["NetworkDevices"] = {}
    for x in self.ListOfDevices:
        manufcode = manufname = modelname = None
        if "Manufacturer" in self.ListOfDevices[x]:
            manufcode = self.ListOfDevices[x]["Manufacturer"]
            if manufcode in ( "", {}):
                continue
            if manufcode not in self.pluginParameters["NetworkDevices"]:
                self.pluginParameters["NetworkDevices"][ manufcode ] = {}

        if manufcode and "Manufacturer Name" in self.ListOfDevices[x]:
            manufname = self.ListOfDevices[x]["Manufacturer Name"]
            if manufname in ( "", {} ):
                manufname = "unknow"
            if manufname not in self.pluginParameters["NetworkDevices"][ manufcode ]:
                self.pluginParameters["NetworkDevices"][ manufcode ][ manufname ] = []

        if manufcode and manufname and "Model" in self.ListOfDevices[x]:
            modelname = self.ListOfDevices[x]["Model"]
            if modelname in ( "", {} ):
                continue
            if modelname not in self.pluginParameters["NetworkDevices"][ manufcode ][ manufname ]:
                self.pluginParameters["NetworkDevices"][ manufcode ][ manufname ].append( modelname )
                if modelname not in self.DeviceConf:
                    unknown_device_model(self, x, modelname,manufcode, manufname )


def get_domoticz_version( self ):
    lst_version = Parameters["DomoticzVersion"].split(" ")
    if len(lst_version) == 1:
        # No Build
        major, minor = lst_version[0].split(".")
        self.DomoticzBuild = 0
        self.DomoticzMajor = int(major)
        self.DomoticzMinor = int(minor)
        # Domoticz.Log("Major: %s Minor: %s" %(int(major), int(minor)))
        self.VersionNewFashion = True

        if self.DomoticzMajor < 2020:
            # Old fashon Versioning
            Domoticz.Error(
                "Domoticz version %s %s %s not supported, please upgrade to a more recent"
                % (Parameters["DomoticzVersion"], major, minor)
            )
            self.VersionNewFashion = False
            self.onStop()
            return False

    elif len(lst_version) != 3:
        Domoticz.Error(
            "Domoticz version %s unknown not supported, please upgrade to a more recent"
            % (Parameters["DomoticzVersion"])
        )
        self.VersionNewFashion = False
        self.onStop()
        return False

    else:
        major, minor = lst_version[0].split(".")
        build = lst_version[2].strip(")")
        self.DomoticzBuild = int(build)
        self.DomoticzMajor = int(major)
        self.DomoticzMinor = int(minor)
        self.VersionNewFashion = True
        
    return True


def unknown_device_model(self, NwkId, Model, ManufCode, ManufName ):
    
    if 'logUnknownDeviceModel' in self.pluginconf.pluginConf and not self.pluginconf.pluginConf["logUnknownDeviceModel"]:
        return
    if 'Log_UnknowDeviceFlag' in self.ListOfDevices[ NwkId ] and self.ListOfDevices[ NwkId ]['Log_UnknowDeviceFlag'] + ( 24 * 3600) < time.time():
        return

    device_name = get_device_nickname( self, NwkId=NwkId)
    if device_name is None:
        device_name = ""

    self.log.logging("Plugin", "Status", "We have detected a working device %s (%s) Model: %s not certified on the plugin. " %(
        get_device_nickname( self, NwkId=NwkId),
        NwkId,
        Model,
    ))
    self.log.logging("Plugin", "Status", "--- can you to create an Issue https://github.com/zigbeefordomoticz/Domoticz-Zigbee/issues/new?assignees=&labels=Device+Integration&template=certified-device-model.md&title=%5BModel+Certification%5D")
    self. log.logging("Plugin", "Status", "--- Provide as much inputs as you can but at least Product and Brand name, URL of a web site where you did the purchase" )
    self. log.logging("Plugin", "Status", "-------------------- Please copy-paste the here after information -------------------- ")

    self. log.logging("Plugin", "Status", "%s" %(json.dumps(self.ListOfDevices[ NwkId ], sort_keys=False)))
    
    self. log.logging("Plugin", "Status", "-------------------- End of Copy-Paste -------------------- ")
    
    self.ListOfDevices[ NwkId ]['Log_UnknowDeviceFlag'] = time.time()
        

def decodeConnection(connection):

    decoded = {}
    for i in connection.strip().split(","):
        label, value = i.split(": ")
        label = label.strip().strip("'")
        value = value.strip().strip("'")
        decoded[label] = value
    return decoded


def zigateInit_Phase1(self):
    """
    Mainly managed Erase PDM if required
    """
    self.log.logging("Plugin", "Debug", "zigateInit_Phase1 PDMDone: %s" % (self.ErasePDMDone))
    # Check if we have to Erase PDM.
    if self.zigbee_communication == "native" and Parameters["Mode3"] == "True" and not self.ErasePDMDone and not self.ErasePDMinProgress:  # Erase PDM
        zigate_erase_eeprom(self)
        self.log.logging("Plugin", "Status", "Erase coordinator PDM")
        #sendZigateCmd(self, "0012", "")
        self.PDMready = False
        self.startZigateNeeded = 1
        self.HeartbeatCount = 1
        update_DB_device_status_to_reinit( self )
        return
    elif self.zigbee_communication == "zigpy" and Parameters["Mode3"] == "True" and not self.ErasePDMDone and not self.ErasePDMinProgress: 
        self.log.logging("Plugin", "Status", "Form a new network requested")
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
        self.log.logging(
            "Plugin",
            "Status",
            "coordinator set to Certification : %s/%s -> %s" % (
                self.pluginconf.pluginConf["CertificationCode"], 
                self.pluginconf.pluginConf["Certification"], 
                CERTIFICATION[self.pluginconf.pluginConf["CertificationCode"]],))
        #sendZigateCmd(self, "0019", "%02x" % self.pluginconf.pluginConf["CertificationCode"])
        zigate_set_certificate(self, "%02x" % self.pluginconf.pluginConf["CertificationCode"] )


        # Create Configure Reporting object
        if self.configureReporting is None:
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
                self.ControllerIEEE
            )
        if self.configureReporting:
            self.webserver.update_configureReporting(self.configureReporting )

    # Enable Group Management
    if self.groupmgt is None and self.pluginconf.pluginConf["enablegroupmanagement"]:
        self.log.logging("Plugin", "Status", "Start Group Management")
        start_GrpManagement(self, Parameters["HomeFolder"])

    # Create Network Energy object and trigger one scan
    if self.networkenergy is None:
        self.networkenergy = NetworkEnergy(
            self.zigbee_communication, self.pluginconf, self.ControllerLink, self.ListOfDevices, Devices, self.HardwareID, self.log
        )
        # if len(self.ListOfDevices) > 1:
        #   self.log.logging( 'Plugin', 'Status', "Trigger a Energy Level Scan")
        #   self.networkenergy.start_scan()

    if self.networkenergy:
        self.webserver.update_networkenergy(self.networkenergy)

        # Create Network Map object and trigger one scan
    if self.networkmap is None:
        self.networkmap = NetworkMap(
            self.zigbee_communication ,self.pluginconf, self.ControllerLink, self.ListOfDevices, Devices, self.HardwareID, self.log
        )
    if self.networkmap:
        self.webserver.update_networkmap(self.networkmap)

    # In case we have Transport = None , let's check if we have to active Group management or not. (For Test and Web UI Dev purposes
    if self.transport == "None" and self.groupmgt is None and self.pluginconf.pluginConf["enablegroupmanagement"]:
        start_GrpManagement(self, Parameters["HomeFolder"])

    # Enable Over The Air Upgrade if applicable
    if self.OTA is None and self.pluginconf.pluginConf["allowOTA"]:
        start_OTAManagement(self, Parameters["HomeFolder"])

    networksize_update(self)
    build_list_of_device_model(self, force=True)

    # Request to resend the IRCode with the next command of Casaia/Owon ACxxxx
    restart_plugin_reset_ModuleIRCode(self, nwkid=None)

    if self.FirmwareMajorVersion == "03": 
        self.log.logging(
            "Plugin", "Status", "Plugin with Zigate, firmware %s correctly initialized" % self.FirmwareVersion
        )
    elif self.FirmwareMajorVersion == "04":
        self.log.logging(
            "Plugin", "Status", "Plugin with Zigate (OptiPDM), firmware %s correctly initialized" % self.FirmwareVersion
        )
    elif self.FirmwareMajorVersion == "05":
        self.log.logging(
            "Plugin", "Status", "Plugin with Zigate+, firmware %s correctly initialized" % self.FirmwareVersion
        )

    elif int(self.FirmwareBranch) >= 20:
        self.log.logging(
            "Plugin", "Status", "Plugin with Zigpy, Coordinator %s firmware %s correctly initialized" % (
                self.pluginParameters["CoordinatorModel"], self.pluginParameters["DisplayFirmwareVersion"]))



    # If firmware above 3.0d, Get Network State
    if (self.HeartbeatCount % (3600 // HEARTBEAT)) == 0 and self.transport != "None":
        zigate_get_nwk_state(self)

    if self.iaszonemgt and self.ControllerIEEE:
        self.iaszonemgt.setZigateIEEE(self.ControllerIEEE)

def check_firmware_level(self):
    # Check Firmware version
    if int(self.FirmwareVersion.lower(),16) == 0x2100:
        self.log.logging("Plugin", "Status", "Firmware for Pluzzy devices")
        self.PluzzyFirmware = True
        return True

    if int(self.FirmwareVersion.lower(),16) < 0x031d:
        self.log.logging("Plugin", "Error", "Firmware level not supported, please update ZiGate firmware")
        return False

    if int(self.FirmwareVersion, 16) > 0x0321:
        self.log.logging("Plugin", "Error", "WARNING: Firmware %s is not yet supported" % self.FirmwareVersion.lower())
        self.pluginconf.pluginConf["forceAckOnZCL"] = False
        return True

    if int(self.FirmwareVersion.lower(),16) >= 0x031e:
        self.pluginconf.pluginConf["forceAckOnZCL"] = False
        return True

    return False


def start_GrpManagement(self, homefolder):
    self.groupmgt = GroupsManagement(
        self.zigbee_communication,
        self.VersionNewFashion,
        self.DomoticzMajor,
        self.DomoticzMinor,
        self.pluginconf,
        self.ControllerLink,
        self.adminWidgets,
        Parameters["HomeFolder"],
        self.HardwareID,
        Devices,
        self.ListOfDevices,
        self.IEEE2NWK,
        self.DeviceConf, 
        self.log,
    )
    if self.groupmgt and self.ControllerIEEE:
        self.groupmgt.updateZigateIEEE(self.ControllerIEEE)

    if self.groupmgt:
        self.webserver.update_groupManagement(self.groupmgt)
        if self.pluginconf.pluginConf["zigatePartOfGroup0000"]:
            # Add Zigate NwkId 0x0000 Ep 0x01 to GroupId 0x0000
            self.groupmgt.addGroupMemberShip("0000", "01", "0000")

        if self.pluginconf.pluginConf["zigatePartOfGroupTint"]:
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
    )
    if self.OTA:
        self.webserver.update_OTA(self.OTA)


def start_web_server(self, webserver_port, webserver_homefolder):

    self.log.logging("Plugin", "Status", "Start Web Server connection")
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
        self.ListOfDevices,
        self.IEEE2NWK,
        self.DeviceConf,
        self.permitTojoin,
        self.WebUsername,
        self.WebPassword,
        self.PluginHealth,
        webserver_port,
        self.log,
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
            restartPluginViaDomoticzJsonApi(self, stop=True, url_base_api=Parameters["Mode5"])

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
            self.log.logging("Plugin", "Status", "pingZigate - SUCCESS - Reconnected after failure")
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


def update_DB_device_status_to_reinit( self ):

    # This function is called because the ZiGate will be reset, and so it is expected that all devices will be reseted and repaired

    for x in self.ListOfDevices:
        if 'Status' in self.ListOfDevices[ x ] and self.ListOfDevices[ x ]['Status'] == 'inDB':
            self.ListOfDevices[ x ]['Status'] = 'erasePDM'

def check_python_modules_version( self ):
    
    MODULES_VERSION = {
        "zigpy": "0.50.2",
        "zigpy_znp": "0.8.2",
        "zigpy_deconz": "0.18.1",
        "zigpy_zigate": "0.8.1.zigbeefordomoticz",
        "zigpy_ezsp": "0.33.1",
        }

    flag = True

    for x in self.pythonModuleVersion:
        if x not in MODULES_VERSION:
            self.log.logging("Plugin", "Error", "A python module has been loaded and is unknown : %s" %x)
            flag = False
            continue
        
        self.log.logging("Plugin", "Debug", "Python module %s loaded with version %s - %s" %( x, self.pythonModuleVersion[ x ], MODULES_VERSION[ x]))   
        if self.pythonModuleVersion[ x ] != MODULES_VERSION[ x]:
            self.log.logging("Plugin", "Error", "The python module %s loaded in not compatible as we are expecting this level %s" %(
                x, MODULES_VERSION[ x] ))
            flag = False
            
    return flag
  
def check_requirements( self ):

    from pathlib import Path

    import pkg_resources

    _filename = pathlib.Path( Parameters[ "HomeFolder"] + "requirements.txt" )

    Domoticz.Status("Checking Python modules %s" %_filename)
    requirements = pkg_resources.parse_requirements(_filename.open())
    for requirements in requirements:
        req = str(requirements)
        try:
            pkg_resources.require(req)
        except DistributionNotFound:
            Domoticz.Error("Looks like %s python module is not installed. Make sure to install the required python3 module" %req)
            Domoticz.Error("Use the command:")
            Domoticz.Error("sudo pip3 install -r requirements.txt")
            return True
    return False          
                     
def debuging_information(self, mode):
    self.log.logging("Plugin", mode, "Is GC enabled: %s" % gc.isenabled())
    self.log.logging("Plugin", mode, "DomoticzVersion: %s" % Parameters["DomoticzVersion"])
    for x in self.pluginParameters:
        self.log.logging("Plugin", mode, "Parameters[%s] %s" % (x, self.pluginParameters[x]))

    self.log.logging("Plugin", mode, "Debug: %s" % Parameters["Mode6"])
    self.log.logging("Plugin", mode, "Python Version - %s" % sys.version)
    self.log.logging("Plugin", mode, "DomoticzVersion: %s" % Parameters["DomoticzVersion"])
    self.log.logging("Plugin", mode, "DomoticzHash: %s" % Parameters["DomoticzHash"])
    self.log.logging("Plugin", mode, "DomoticzBuildTime: %s" % Parameters["DomoticzBuildTime"])
    self.log.logging("Plugin", mode, "Startup Folder: %s" % Parameters["StartupFolder"])
    self.log.logging("Plugin", mode, "Home Folder: %s" % Parameters["HomeFolder"])
    self.log.logging("Plugin", mode, "User Data Folder: %s" % Parameters["UserDataFolder"])
    self.log.logging("Plugin", mode, "Web Root Folder: %s" % Parameters["WebRoot"])
    self.log.logging("Plugin", mode, "Database: %s" % Parameters["Database"])
    self.log.logging("Plugin", mode, "Opening DomoticzDB in raw")
    self.log.logging("Plugin", mode, "   - DeviceStatus table")
    
global _plugin  # pylint: disable=global-variable-not-assigned
_plugin = BasePlugin()


def onStart():
    global _plugin  # pylint: disable=global-variable-not-assigned
    _plugin.onStart()


def onStop():
    global _plugin  # pylint: disable=global-variable-not-assigned
    _plugin.onStop()


def onDeviceRemoved(Unit):
    global _plugin  # pylint: disable=global-variable-not-assigned
    _plugin.onDeviceRemoved(Unit)


def onConnect(Connection, Status, Description):
    global _plugin  # pylint: disable=global-variable-not-assigned
    _plugin.onConnect(Connection, Status, Description)


def onMessage(Connection, Data):
    global _plugin  # pylint: disable=global-variable-not-assigned
    _plugin.onMessage(Connection, Data)


def onCommand(Unit, Command, Level, Hue):
    global _plugin  # pylint: disable=global-variable-not-assigned
    _plugin.onCommand(Unit, Command, Level, Hue)


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

    custom_file = Parameters['StartupFolder'] + 'www/templates/' + f"{Parameters['Name']}" + '.html'
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

def do_python_garbage_collection( self ):
    # Garbage collector ( experimental for now)
    if self.internalHB % (3600 // HEARTBEAT) == 0:
        self.log.logging("Plugin", "Debug", "Garbage Collection status: %s" % str(gc.get_count()))
        self.log.logging("Plugin", "Debug", "Garbage Collection triggered: %s" % str(gc.collect()))

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
        ) = checkPluginVersion(self.zigbee_communication, self.pluginParameters["PluginBranch"], self.FirmwareMajorVersion)
        self.pluginParameters["FirmwareUpdate"] = False
        self.pluginParameters["PluginUpdate"] = False

        if checkPluginUpdate(self.pluginParameters["PluginVersion"], self.pluginParameters["available"]):
            if "beta" in self.pluginParameters["PluginBranch"] :
                log_mode = "Error"
            else:
                log_mode = "Status"
            self.log.logging("Plugin", log_mode, "There is a newer plugin version available on gitHub. Current %s Available %s" %(
                self.pluginParameters["PluginVersion"], self.pluginParameters["available"]))
            self.pluginParameters["PluginUpdate"] = True
        if checkFirmwareUpdate(
            self.FirmwareMajorVersion,
            self.FirmwareVersion,
            self.pluginParameters["available-firmMajor"],
            self.pluginParameters["available-firmMinor"],
        ):
            self.log.logging("Plugin", "Status", "There is a newer Zigate Firmware version available")
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
        self.log.logging( "Plugin", "Error", "[%3s] I have hard time to get Coordinator Version. Mostlikly there is a communication issue" % (self.internalHB), )
        
    if (
        ( self.transport == "ZigpyZNP" and self.internalHB > ZNP_STARTUP_TIMEOUT_DELAY_FOR_STOP )
        or ( self.transport != "ZigpyZNP" and self.internalHB > STARTUP_TIMEOUT_DELAY_FOR_STOP) 
    ):
        debuging_information(self, "Log")
        self.log.logging("Plugin", "Error", "[   ] Stopping the plugin and lease do check the Coordinator connectivity.")
        restartPluginViaDomoticzJsonApi(self, stop=True, url_base_api=Parameters["Mode5"])

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
                    self.log.logging( "Plugin", "Status", "ZigateConf - Setting extPANID : 0x%016x" % (self.pluginconf.pluginConf["extendedPANID"]), )
                    setExtendedPANID(self, self.pluginconf.pluginConf["extendedPANID"])

                start_Zigate(self)
                self.startZigateNeeded = False
            return False

        if not self.InitPhase2:
            zigateInit_Phase2(self)
            return False
        
    return True
