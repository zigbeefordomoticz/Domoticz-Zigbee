#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
<plugin key="Zigate" name="Zigate plugin" author="zaraki673 & pipiche38" version="5.1" wikilink="https://www.domoticz.com/wiki/Zigate" externallink="https://github.com/pipiche38/Domoticz-Zigate/wiki">
    <description>
        <h2> Plugin ZiGate for Domoticz </h2><br/>
            The aim of the plugin is to bridge a ZiGate to the DomoticZ software. <br/>
            This will allow you to manage all your devices through widgets created on the Domoticz side.<br/>
            On top we have build a specific User Interface which is accessible over your browser to help you 
            in the configuration of the plugin and to customize some behaviour of the Zigate Hardware.<br/>

            <br/><h3> Sources of information </h3><br/>
                Please use first the Domoticz forums in order to qualify your issue. Select the ZigBee or Zigate topic.
                <ul style="list-style-type:square">
                    <li>&<a href="https://zigbee.blakadder.com/zigate.html">List of Supported Devices (zigbee.blakadder.com)</a></li>
                    <li>&<a href="https://github.com/pipiche38/Domoticz-Zigate-Wiki">Plugin Wiki</a></li>
                    <li>&<a href="https://www.domoticz.com/forum/viewforum.php?f=68">English Forum</a></li>
                    <li>&<a href="https://easydomoticz.com/forum/viewforum.php?f=28">Forum en Français</a></li>

                </ul><br/>

            <h3> Configuration </h3><br/>
                You can use the following parameter to interact with the Zigate:<br/>
                <ul style="list-style-type:square">
                    <li> Model: Wifi</li>
                        <ul style="list-style-type:square">
                            <li> IP : For Wifi Zigate, the IP address. </li>
                            <li> Port: For Wifi Zigate,  port number. </li>
                        </ul>
                    <li> Model USB ,  PI or DIN:</li>
                        <ul style="list-style-type:square">
                            <li> Serial Port: this is the serial port where your USB or DIN Zigate is connected. <br/>
                            (The plugin will provide you the list of possible ports)</li>
                        </ul>
                    <br/>
                    <h4>IMPORTANT</h4>
                    Initialize ZiGate with plugin: This is a required step, with a new ZiGate or if you have done an Erase EEPROM. <br/>
                    This will for instance create a new ZigBee Network. <br/>
                    Be aware this will erase the Zigate memory and you will delete all pairing information. <br/>
                    After that you'll have to re-pair each devices. This is not removing any data from Domoticz nor the plugin database.
                </ul>


    </description>
    <params>
        <param field="Mode1" label="Zigate Model" width="75px" required="true" default="None">
            <options>
                <option label="ZiGate"  value="V1"/>
                <option label="ZiGate+" value="V2"/>
            </options>
        </param>
        <param field="Mode2" label="Zigate Communication" width="75px" required="true" default="None">
            <options>
                <option label="USB"   value="USB" />
                <option label="DIN"   value="DIN" />
                <option label="PI"    value="PI" />
                <option label="TCPIP" value="Wifi"/>
                <option label="None"  value="None"/>
            </options>
        </param>
        <param field="Address" label="IP" width="150px" required="true" default="0.0.0.0"/>
        <param field="Port" label="Port" width="150px" required="true" default="9999"/>
        <param field="SerialPort" label="Serial Port" width="150px" required="true" default="/dev/ttyUSB0"/>

        <param field="Mode3" label="Initialize ZiGate (Erase Memory) " width="75px" required="true" default="False" >
            <options>
                <option label="True" value="True"/>
                <option label="False" value="False" default="true" />
            </options>
        </param>

        <param field="Mode4" label="Listening port for Web Admin GUI (put None to disable)" width="75px" required="true" default="9440" />

        <param field="Mode6" label="Verbors and Debuging" width="150px" required="true" default="None">
            <options>
                        <option label="None" value="2"  default="true"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz

try:
    from Domoticz import Devices, Images, Parameters, Settings
except ImportError:
    pass

from datetime import datetime
import time
import json
import sys
import threading
import gc

from Modules.piZigate import switchPiZigate_mode
from Modules.tools import removeDeviceInList
from Modules.basicOutputs import (
    sendZigateCmd,
    removeZigateDevice,
    start_Zigate,
    setExtendedPANID,
    setTimeServer,
    leaveRequest,
    zigateBlueLed,
    ZigatePermitToJoin,
    disable_firmware_default_response,
    do_Many_To_One_RouteRequest,
)
from Modules.input import ZigateRead
from Modules.heartbeat import processListOfDevices
from Modules.database import (
    importDeviceConf,
    importDeviceConfV2,
    LoadDeviceList,
    checkListOfDevice2Devices,
    checkDevices2LOD,
    WriteDeviceList,
)
from Modules.domoTools import ResetDevice
from Modules.command import mgtCommand
from Modules.zigateConsts import HEARTBEAT, CERTIFICATION, MAX_LOAD_ZIGATE, MAX_FOR_ZIGATE_BUZY
from Modules.txPower import set_TxPower, get_TxPower
from Modules.checkingUpdate import checkPluginVersion, checkPluginUpdate, checkFirmwareUpdate
from Modules.restartPlugin import restartPluginViaDomoticzJsonApi
from Modules.schneider_wiser import wiser_thermostat_monitoring_heating_demand

# from Classes.APS import APSManagement
from Classes.IAS import IAS_Zone_Management
from Classes.PluginConf import PluginConf
from Classes.Transport.Transport import ZigateTransport
from Classes.TransportStats import TransportStatistics
from Classes.LoggingManagement import LoggingManagement

from Classes.GroupMgtv2.GroupManagement import GroupsManagement
from Classes.AdminWidgets import AdminWidgets
from Classes.OTA import OTAManagement

from Classes.WebServer.WebServer import WebServer

from Classes.NetworkMap import NetworkMap
from Classes.NetworkEnergy import NetworkEnergy

from Classes.DomoticzDB import DomoticzDB_DeviceStatus, DomoticzDB_Hardware, DomoticzDB_Preferences


VERSION_FILENAME = ".hidden/VERSION"

TEMPO_NETWORK = 2  # Start HB totrigget Network Status
TIMEDOUT_START = 10  # Timeoud for the all startup
TIMEDOUT_FIRMWARE = 5  # HB before request Firmware again
TEMPO_START_ZIGATE = 1  # Nb HB before requesting a Start_Zigate


class BasePlugin:
    enabled = False

    def __init__(self):

        self.ListOfDevices = (
            {}
        )  # {DevicesAddresse : { status : status_de_detection, data : {ep list ou autres en fonctions du status}}, DevicesAddresse : ...}
        self.DevicesInPairingMode = []
        self.DiscoveryDevices = {}  # Used to collect pairing information
        self.IEEE2NWK = {}
        self.zigatedata = {}
        self.DeviceConf = {}  # Store DeviceConf.txt, all known devices configuration

        # Objects from Classe
        self.ZigateComm = None
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
        self.ZigateIEEE = None  # Zigate IEEE. Set in CDecode8009/Decode8024
        self.ZigateNWKID = None  # Zigate NWKID. Set in CDecode8009/Decode8024
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

    def onStart(self):
        Domoticz.Log("ZiGate plugin started!")
        assert sys.version_info >= (3, 4)

        if Parameters["Mode1"] == "V1" and Parameters["Mode2"] in (
            "USB",
            "DIN",
            "PI",
            "Wifi",
        ):
            self.transport = Parameters["Mode2"]
        elif Parameters["Mode1"] == "V2" and Parameters["Mode2"] in (
            "USB",
            "DIN",
            "PI",
            "Wifi",
        ):
            self.transport = "V2-" + Parameters["Mode2"]
        elif Parameters["Mode2"] == "None":
            self.transport = "None"
        else:
            Domoticz.Error(
                "Please cross-check the plugin starting parameters Mode1: %s Mode2: %s and make sure you have restarted Domoticz after updating the plugin"
                % (Parameters["Mode1"] == "V1", Parameters["Mode2"])
            )
            return

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
                return
        elif len(lst_version) != 3:
            Domoticz.Error(
                "Domoticz version %s unknown not supported, please upgrade to a more recent"
                % (Parameters["DomoticzVersion"])
            )
            self.VersionNewFashion = False
            return
        else:
            major, minor = lst_version[0].split(".")
            build = lst_version[2].strip(")")
            self.DomoticzBuild = int(build)
            self.DomoticzMajor = int(major)
            self.DomoticzMinor = int(minor)
            self.VersionNewFashion = True

        # Import PluginConf.txt
        Domoticz.Log("load PluginConf")
        self.pluginconf = PluginConf(Parameters["HomeFolder"], self.HardwareID)

        # Create the adminStatusWidget if needed
        self.PluginHealth["Flag"] = 1
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
            "Zigate plugin %s-%s started"
            % (self.pluginParameters["PluginBranch"], self.pluginParameters["PluginVersion"]),
        )

        # Debuging information
        self.log.logging("Plugin", "Debug", "Is GC enabled: %s" % gc.isenabled())
        self.log.logging("Plugin", "Debug", "DomoticzVersion: %s" % Parameters["DomoticzVersion"])
        for x in self.pluginParameters:
            self.log.logging("Plugin", "Debug", "Parameters[%s] %s" % (x, self.pluginParameters[x]))

        self.log.logging("Plugin", "Debug", "Debug: %s" % Parameters["Mode6"])
        self.log.logging("Plugin", "Debug", "Python Version - %s" % sys.version)
        self.log.logging("Plugin", "Debug", "DomoticzVersion: %s" % Parameters["DomoticzVersion"])
        self.log.logging("Plugin", "Debug", "DomoticzHash: %s" % Parameters["DomoticzHash"])
        self.log.logging("Plugin", "Debug", "DomoticzBuildTime: %s" % Parameters["DomoticzBuildTime"])
        self.log.logging("Plugin", "Debug", "Startup Folder: %s" % Parameters["StartupFolder"])
        self.log.logging("Plugin", "Debug", "Home Folder: %s" % Parameters["HomeFolder"])
        self.log.logging("Plugin", "Debug", "User Data Folder: %s" % Parameters["UserDataFolder"])
        self.log.logging("Plugin", "Debug", "Web Root Folder: %s" % Parameters["WebRoot"])
        self.log.logging("Plugin", "Debug", "Database: %s" % Parameters["Database"])
        self.log.logging("Plugin", "Debug", "Opening DomoticzDB in raw")
        self.log.logging("Plugin", "Debug", "   - DeviceStatus table")
        self.StartupFolder = Parameters["StartupFolder"]

        self.domoticzdb_DeviceStatus = DomoticzDB_DeviceStatus(
            Parameters["Database"], self.pluginconf, self.HardwareID, self.log
        )

        self.log.logging("Plugin", "Debug", "   - Hardware table")
        self.domoticzdb_Hardware = DomoticzDB_Hardware(
            Parameters["Database"], self.pluginconf, self.HardwareID, self.log
        )
        if "LogLevel" not in self.pluginParameters:
            log_level = self.domoticzdb_Hardware.get_loglevel_value()
            if log_level:
                self.pluginParameters["LogLevel"] = log_level
                self.log.logging("Plugin", "Debug", "LogLevel: %s" % self.pluginParameters["LogLevel"])
        self.log.logging("Plugin", "Debug", "   - Preferences table")
        self.domoticzdb_Preferences = DomoticzDB_Preferences(Parameters["Database"], self.pluginconf, self.log)
        self.WebUsername, self.WebPassword = self.domoticzdb_Preferences.retreiveWebUserNamePassword()
        # Domoticz.Status("Domoticz Website credentials %s/%s" %(self.WebUsername, self.WebPassword))

        self.adminWidgets = AdminWidgets(self.pluginconf, Devices, self.ListOfDevices, self.HardwareID)
        self.adminWidgets.updateStatusWidget(Devices, "Startup")

        self.DeviceListName = "DeviceList-" + str(Parameters["HardwareID"]) + ".txt"
        self.log.logging("Plugin", "Log", "Plugin Database: %s" % self.DeviceListName)

        if self.pluginconf.pluginConf["capturePairingInfos"] == 1:
            self.DiscoveryDevices = {}

        # Import Certified Device Configuration
        importDeviceConfV2(self)

        # if type(self.DeviceConf) is not dict:
        if not isinstance(self.DeviceConf, dict):
            self.log.logging("Plugin", "Error", "DeviceConf initialisation failure!!! %s" % type(self.DeviceConf))
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
            self.ZigateComm = ZigateTransport(
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
            switchPiZigate_mode(self, "run")
            self.ZigateComm = ZigateTransport(
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
            self.ZigateComm = ZigateTransport(
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
            self.log.logging("Plugin", "Status", "Transport mode set to None, no communication.")
            self.FirmwareVersion = "031c"
            self.PluginHealth["Firmware Update"] = {"Progress": "75 %", "Device": "1234"}
            return
        else:
            self.log.logging("Plugin", "Error", "Unknown Transport comunication protocol : %s" % str(self.transport))
            return

        self.log.logging("Plugin", "Debug", "Establish Zigate connection")
        self.ZigateComm.open_zigate_connection()

        # IAS Zone Management
        if self.iaszonemgt is None:
            # Create IAS Zone object
            # Domoticz.Log("Init IAS_Zone_management ZigateComm: %s" %self.ZigateComm)
            self.iaszonemgt = IAS_Zone_Management(self.pluginconf, self.ZigateComm, self.ListOfDevices, self.log)

            # Starting WebServer
        if self.webserver is None:
            if Parameters["Mode4"].isdigit():
                start_web_server(self, Parameters["Mode4"], Parameters["HomeFolder"])
            else:
                self.log.logging(
                    "Plugin", "Error", "WebServer disabled du to Parameter Mode4 set to %s" % Parameters["Mode4"]
                )

        self.busy = False

    def onStop(self):
        if self.log:
            self.log.logging("Plugin", "Log", "onStop called")
            self.log.logging("Plugin", "Log", "onStop calling (1) domoticzDb DeviceStatus closed")
        if self.domoticzdb_DeviceStatus:
            self.domoticzdb_DeviceStatus.closeDB()
        if self.log:
            self.log.logging("Plugin", "Log", "onStop called (1) domoticzDb DeviceStatus closed")

            self.log.logging("Plugin", "Log", "onStop calling (2) domoticzDb Hardware closed")
        if self.domoticzdb_Hardware:
            self.domoticzdb_Hardware.closeDB()
        if self.log:
            self.log.logging("Plugin", "Log", "onStop called (2) domoticzDb Hardware closed")

            self.log.logging("Plugin", "Log", "onStop calling (3) Transport off")
        if self.ZigateComm:
            self.ZigateComm.thread_transport_shutdown()
            self.ZigateComm.close_zigate_connection()
        if self.log:
            self.log.logging("Plugin", "Log", "onStop called (3) Transport off")

            self.log.logging("Plugin", "Log", "onStop calling (4) WebServer off")
        if self.webserver:
            self.webserver.onStop()
        if self.log:
            self.log.logging("Plugin", "Log", "onStop called (4) WebServer off")

        if self.log:
            self.log.logging("Plugin", "Log", "onStop calling (5) Plugin Database saved")
        WriteDeviceList(self, 0)
        if self.log:
            self.log.logging("Plugin", "Log", "onStop called (5) Plugin Database saved")

        self.statistics.printSummary()
        self.statistics.writeReport()

        if self.log:
            self.log.logging("Plugin", "Log", "onStop calling (6) Close Logging Management")
        if self.log:
            self.log.closeLogFile()
        self.log.logging("Plugin", "Log", "onStop called (6) Close Logging Management")

        for thread in threading.enumerate():
            if thread.name != threading.current_thread().name:
                Domoticz.Log(
                    "'"
                    + thread.name
                    + "' is running, it must be shutdown otherwise Domoticz will abort on plugin exit."
                )

        self.PluginHealth["Flag"] = 3
        self.PluginHealth["Txt"] = "No Communication"
        self.adminWidgets.updateStatusWidget(Devices, "No Communication")

    def onDeviceRemoved(self, Unit):
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
                    if self.ZigateIEEE:
                        sendZigateCmd(self, "0026", self.ZigateIEEE + IEEE)
                        self.log.logging(
                            "Plugin",
                            "Status",
                            "onDeviceRemoved - removing Device %s -> %s in Zigate" % (Devices[Unit].Name, IEEE),
                        )
                    else:
                        self.log.logging(
                            "Plugin",
                            "Error",
                            "onDeviceRemoved - too early, Zigate and plugin initialisation not completed",
                        )
                else:
                    self.log.logging(
                        "Plugin",
                        "Status",
                        "onDeviceRemoved - device entry %s from Zigate not removed. You need to enable 'allowRemoveZigateDevice' parameter. Do consider that it works only for main powered devices."
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
            self.ZigateComm.re_conn()
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
        self.ZigateComm.on_message(Data)

    def processFrame(self, Data):
        if not self.VersionNewFashion:
            return
        self.connectionState = 1
        # start_time = int(time.time() *1000)
        ZigateRead(self, Devices, Data)
        # stop_time = int(time.time() *1000)
        # Domoticz.Log("### Completion: %s is %s ms" %(Data, ( stop_time - start_time)))

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

        busy_ = False

        # Quiet a bad hack. In order to get the needs for ZigateRestart
        # from WebServer
        if "startZigateNeeded" in self.zigatedata and self.zigatedata["startZigateNeeded"]:
            self.startZigateNeeded = self.HeartbeatCount
            del self.zigatedata["startZigateNeeded"]

        # Starting PDM on Host firmware version, we have to wait that Zigate is fully initialized ( PDM loaded into memory from Host).
        # We wait for self.zigateReady which is set to True in th pdmZigate module
        if self.transport != "None" and not self.PDMready:
            if self.internalHB > 60:
                self.log.logging(
                    "Plugin",
                    "Error",
                    "[%3s] I have hard time to get ZiGate Version. Mostlikly ZiGate communication doesn't work"
                    % (self.internalHB),
                )
                self.log.logging("Plugin", "Error", "[   ] Stop the plugin and check ZiGate.")

            if (self.internalHB % 5) == 0:
                self.log.logging(
                    "Plugin", "Debug", "[%s] PDMready: %s requesting Get version" % (self.internalHB, self.PDMready)
                )
                sendZigateCmd(self, "0010", "")
            return

        if self.transport != "None":
            self.log.logging(
                "Plugin",
                "Debug",
                "onHeartbeat - busy = %s, Health: %s, startZigateNeeded: %s/%s, InitPhase1: %s InitPhase2: %s, InitPhase3: %s PDM_LOCK: %s"
                % (
                    self.busy,
                    self.PluginHealth,
                    self.startZigateNeeded,
                    self.HeartbeatCount,
                    self.InitPhase1,
                    self.InitPhase2,
                    self.InitPhase3,
                    self.ZigateComm.pdm_lock_status(),
                ),
            )

        if self.transport != "None" and (self.startZigateNeeded or not self.InitPhase1 or not self.InitPhase2):
            # Require Transport
            # Perform erasePDM if required
            if not self.InitPhase1:
                zigateInit_Phase1(self)
                return

            # Check if Restart is needed ( After an ErasePDM or a Soft Reset
            if self.startZigateNeeded:
                if self.HeartbeatCount > self.startZigateNeeded + TEMPO_START_ZIGATE:
                    # Need to check if and ErasePDM has been performed.
                    # In case case, we have to set the extendedPANID
                    # ErasePDM has been requested, we are in the next Loop.
                    if self.ErasePDMDone and self.pluginconf.pluginConf["extendedPANID"] is not None:
                        self.log.logging(
                            "Plugin",
                            "Status",
                            "ZigateConf - Setting extPANID : 0x%016x" % (self.pluginconf.pluginConf["extendedPANID"]),
                        )
                        setExtendedPANID(self, self.pluginconf.pluginConf["extendedPANID"])

                    start_Zigate(self)
                    self.startZigateNeeded = False
                return

            if not self.InitPhase2:
                zigateInit_Phase2(self)
                return

        if not self.InitPhase3:
            zigateInit_Phase3(self)
            return

        # Checking Version
        self.pluginParameters["TimeStamp"] = int(time.time())
        if self.pluginconf.pluginConf["internetAccess"] and (
            self.pluginParameters["available"] is None or self.HeartbeatCount % (12 * 3600 // HEARTBEAT) == 0
        ):
            (
                self.pluginParameters["available"],
                self.pluginParameters["available-firmMajor"],
                self.pluginParameters["available-firmMinor"],
            ) = checkPluginVersion(self.pluginParameters["PluginBranch"], self.FirmwareMajorVersion)
            self.pluginParameters["FirmwareUpdate"] = False
            self.pluginParameters["PluginUpdate"] = False

            if checkPluginUpdate(self.pluginParameters["PluginVersion"], self.pluginParameters["available"]):
                self.log.logging("Plugin", "Status", "There is a newer plugin version available on gitHub")
                self.pluginParameters["PluginUpdate"] = True
            if checkFirmwareUpdate(
                self.FirmwareMajorVersion,
                self.FirmwareVersion,
                self.pluginParameters["available-firmMajor"],
                self.pluginParameters["available-firmMinor"],
            ):
                self.log.logging("Plugin", "Status", "There is a newer Zigate Firmware version available")
                self.pluginParameters["FirmwareUpdate"] = True

        if self.transport == "None":
            return

        # Memorize the size of Devices. This is will allow to trigger a backup of live data to file, if the size change.
        prevLenDevices = len(Devices)

        # Garbage collector ( experimental for now)
        if self.internalHB % (3600 // HEARTBEAT) == 0:
            self.log.logging("Plugin", "Debug", "Garbage Collection status: %s" % str(gc.get_count()))
            self.log.logging("Plugin", "Debug", "Garbage Collection triggered: %s" % str(gc.collect()))

        # Manage all entries in  ListOfDevices (existing and up-coming devices)
        processListOfDevices(self, Devices)

        self.iaszonemgt.IAS_heartbeat()

        # Check and Update Heating demand for Wiser if applicable (this will be check in the call)
        wiser_thermostat_monitoring_heating_demand(self, Devices)
        # Group Management
        if self.groupmgt:
            self.groupmgt.hearbeat_group_mgt()

        # Write the ListOfDevice in HBcount % 200 ( 3' ) or immediatly if we have remove or added a Device
        if len(Devices) == prevLenDevices:
            WriteDeviceList(self, (90 * 5))
        else:
            self.log.logging("Plugin", "Debug", "Devices size has changed , let's write ListOfDevices on disk")
            WriteDeviceList(self, 0)  # write immediatly

        if self.CommiSSionning:
            self.PluginHealth["Flag"] = 2
            self.PluginHealth["Txt"] = "Enrollment in Progress"
            self.adminWidgets.updateStatusWidget(Devices, "Enrollment")
            # Maintain trend statistics
            self.statistics._Load = self.ZigateComm.loadTransmit()
            self.statistics.addPointforTrendStats(self.HeartbeatCount)
            return

        # Reset Motion sensors
        ResetDevice(self, Devices, "Motion", 5)

        # Send a Many-to-One-Route-request
        if self.pluginconf.pluginConf["doManyToOneRoute"] and self.HeartbeatCount % ((50 * 60) // HEARTBEAT) == 0:
            do_Many_To_One_RouteRequest(self)

        # OTA upgrade
        if self.OTA:
            self.OTA.heartbeat()

        # Check PermitToJoin
        if (
            self.permitTojoin["Duration"] != 255
            and self.permitTojoin["Duration"] != 0
            and int(time.time()) >= (self.permitTojoin["Starttime"] + self.permitTojoin["Duration"])
        ):
            sendZigateCmd(self, "0014", "")  # Request status
            self.permitTojoin["Duration"] = 0

        # Heartbeat - Ping Zigate every minute to check connectivity
        # If fails then try to reConnect
        if self.pluginconf.pluginConf["Ping"]:
            pingZigate(self)
            self.Ping["Nb Ticks"] += 1

        if self.HeartbeatCount % (3600 // HEARTBEAT) == 0:
            self.log.loggingCleaningErrorHistory()
            sendZigateCmd(self, "0017", "")

        # Update MaxLoad if needed
        self.statistics._Load = 0
        if self.ZigateComm.loadTransmit() >= MAX_FOR_ZIGATE_BUZY:
            # This mean that 4 commands are on the Queue to be executed by Zigate.
            busy_ = True
            self.statistics._Load = self.ZigateComm.loadTransmit()
        # Maintain trend statistics
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

        self.busy = busy_
        return True


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
    if Parameters["Mode3"] == "True" and not self.ErasePDMDone:  # Erase PDM
        if not self.ErasePDMDone:
            self.ErasePDMDone = True
            if self.domoticzdb_Hardware:
                self.domoticzdb_Hardware.disableErasePDM()
            self.log.logging("Plugin", "Status", "Erase Zigate PDM")
            sendZigateCmd(self, "0012", "")
            self.PDMready = False
            self.startZigateNeeded = 1
            self.HeartbeatCount = 1
            return

        # After an Erase PDM we have to do a full start of Zigate
        self.log.logging("Plugin", "Debug", "----> starZigate")
        return

    self.busy = False
    self.InitPhase1 = True
    return True


def zigateInit_Phase2(self):
    """
    Make sure that all setup is in place
    """
    if self.FirmwareVersion is None or self.ZigateIEEE is None or self.ZigateNWKID == "ffff":
        if self.FirmwareVersion is None:
            # Ask for Firmware Version
            sendZigateCmd(self, "0010", "")
        if self.ZigateIEEE is None or self.ZigateNWKID == "ffff":
            # Request Network State
            sendZigateCmd(self, "0009", "")

        if self.HeartbeatCount > TIMEDOUT_FIRMWARE:
            self.log.logging(
                "Plugin",
                "Error",
                "We are having difficulties to start Zigate. Basically we are not receiving what we expect from Zigate",
            )
            self.log.logging("Plugin", "Error", "Plugin is not started ...")
        return

    # Set Time server to HOST time
    setTimeServer(self)

    # If applicable, put Zigate in NO Pairing Mode
    self.Ping["Permit"] = None
    if self.pluginconf.pluginConf["resetPermit2Join"]:
        ZigatePermitToJoin(self, 0)
    else:
        sendZigateCmd(self, "0014", "")  # Request Permit to Join status

    # Request List of Active Devices
    sendZigateCmd(self, "0015", "")

    # Ready for next phase
    self.InitPhase2 = True


def zigateInit_Phase3(self):

    # We can now do what must be done when we known the Firmware version
    if self.FirmwareVersion is None:
        return

    self.InitPhase3 = True

    self.pluginParameters["FirmwareVersion"] = self.FirmwareVersion

    if not check_firmware_level(self):
        self.log.logging("Plugin", "Debug", "Firmware not ready")
        return

    if (
        self.transport != "None"
        and int(self.FirmwareVersion, 16) >= 0x030F
        and int(self.FirmwareMajorVersion, 16) >= 0x03
    ):
        if self.pluginconf.pluginConf["blueLedOnOff"]:
            zigateBlueLed(self, True)
        else:
            zigateBlueLed(self, False)

        # Set the TX Power
        set_TxPower(self, self.pluginconf.pluginConf["TXpower_set"])

        # Set Certification Code
        if self.pluginconf.pluginConf["CertificationCode"] in CERTIFICATION:
            self.log.logging(
                "Plugin",
                "Status",
                "Zigate set to Certification : %s" % CERTIFICATION[self.pluginconf.pluginConf["CertificationCode"]],
            )
            sendZigateCmd(self, "0019", "%02x" % self.pluginconf.pluginConf["CertificationCode"])

        # if int(self.FirmwareVersion,16) >= 0x031e :
        #    if self.pluginconf.pluginConf['disabledDefaultResponseFirmware'] :
        #        self.log.logging( 'Plugin', 'Status', "Disable Default Response in firmware")
        #        disable_firmware_default_response( self , mode='01')
        #    else:
        #        self.log.logging( 'Plugin', 'Status', "Enable Default Response in firmware")
        #        disable_firmware_default_response( self , mode='00')

        # Enable Group Management
        if self.groupmgt is None and self.pluginconf.pluginConf["enablegroupmanagement"]:
            self.log.logging("Plugin", "Status", "Start Group Management")
            start_GrpManagement(self, Parameters["HomeFolder"])
            if self.pluginconf.pluginConf["zigatePartOfGroup0000"]:
                # Add Zigate NwkId 0x0000 Ep 0x01 to GroupId 0x0000
                self.groupmgt.addGroupMemberShip("0000", "01", "0000")

            if self.pluginconf.pluginConf["zigatePartOfGroupTint"]:
                # Tint Remote manage 4 groups and we will create with ZiGate attached.
                self.groupmgt.addGroupMemberShip("0000", "01", "4003")
                self.groupmgt.addGroupMemberShip("0000", "01", "4004")
                self.groupmgt.addGroupMemberShip("0000", "01", "4005")
                self.groupmgt.addGroupMemberShip("0000", "01", "4006")

        # Create Network Map object and trigger one scan
        if self.networkmap is None:
            self.networkmap = NetworkMap(
                self.pluginconf, self.ZigateComm, self.ListOfDevices, Devices, self.HardwareID, self.log
            )
        if self.networkmap:
            self.webserver.update_networkmap(self.networkmap)

        # Create Network Energy object and trigger one scan
        if self.networkenergy is None:
            self.networkenergy = NetworkEnergy(
                self.pluginconf, self.ZigateComm, self.ListOfDevices, Devices, self.HardwareID, self.log
            )  #    if len(self.ListOfDevices) > 1:        #        self.log.logging( 'Plugin', 'Status', "Trigger a Energy Level Scan")        #        self.networkenergy.start_scan()
        if self.networkenergy:
            self.webserver.update_networkenergy(self.networkenergy)

    # In case we have Transport = None , let's check if we have to active Group management or not. (For Test and Web UI Dev purposes
    if self.transport == "None" and self.groupmgt is None and self.pluginconf.pluginConf["enablegroupmanagement"]:
        start_GrpManagement(self, Parameters["HomeFolder"])

    # Enable Over The Air Upgrade if applicable
    if self.OTA is None and self.pluginconf.pluginConf["allowOTA"]:
        start_OTAManagement(self, Parameters["HomeFolder"])

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

    # If firmware above 3.0d, Get Network State
    if self.FirmwareVersion >= "030d" and (self.HeartbeatCount % (3600 // HEARTBEAT)) == 0 and self.transport != "None":
        sendZigateCmd(self, "0009", "")


def check_firmware_level(self):
    # Check Firmware version
    if (
        self.FirmwareVersion.lower() < "030f"
        or self.FirmwareVersion.lower() == "030f"
        and self.FirmwareMajorVersion == "02"
    ):
        self.log.logging("Plugin", "Error", "Firmware level not supported, please update ZiGate firmware")
        return False

    if self.FirmwareVersion.lower() == "2100":
        self.log.logging("Plugin", "Status", "Firmware for Pluzzy devices")
        self.PluzzyFirmware = True
        return True

    if self.FirmwareVersion.lower() == "031b":
        self.log.logging(
            "Plugin",
            "Status",
            "You are not on the latest firmware version, This version is known to have problem, please consider to upgrade",
        )
        return False

    if self.FirmwareVersion.lower() in ("031a", "031c", "031d"):
        self.pluginconf.pluginConf["forceAckOnZCL"] = True

    elif self.FirmwareVersion.lower() == "031e":
        self.pluginconf.pluginConf["forceAckOnZCL"] = False

    elif int(self.FirmwareVersion, 16) > 0x0320:
        self.log.logging("Plugin", "Error", "Firmware %s is not yet supported" % self.FirmwareVersion.lower())

    return True


def start_GrpManagement(self, homefolder):
    self.groupmgt = GroupsManagement(
        self.pluginconf,
        self.ZigateComm,
        self.adminWidgets,
        Parameters["HomeFolder"],
        self.HardwareID,
        Devices,
        self.ListOfDevices,
        self.IEEE2NWK,
        self.log,
    )
    if self.groupmgt and self.ZigateIEEE:
        self.groupmgt.updateZigateIEEE(self.ZigateIEEE)
    if self.groupmgt:
        self.webserver.update_groupManagement(self.groupmgt)


def start_OTAManagement(self, homefolder):
    self.OTA = OTAManagement(
        self.pluginconf,
        self.adminWidgets,
        self.ZigateComm,
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
        self.zigatedata,
        self.pluginParameters,
        self.pluginconf,
        self.statistics,
        self.adminWidgets,
        self.ZigateComm,
        webserver_homefolder,
        self.HardwareID,
        self.DevicesInPairingMode,
        Devices,
        self.ListOfDevices,
        self.IEEE2NWK,
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
            # self.ZigateComm.re_conn()
            restartPluginViaDomoticzJsonApi(self)

        else:
            if (self.Ping["Nb Ticks"] % 3) == 0:
                sendZigateCmd(self, "0014", "")  # Request status
        return

    # If we are more than PING_CHECK_FREQ without any messages, let's check
    if self.Ping["Nb Ticks"] < (PING_CHECK_FREQ // HEARTBEAT):
        self.connectionState = 1
        self.log.logging(
            "Plugin", "Debug", "pingZigate - We have receive a message less than %s sec  ago " % PING_CHECK_FREQ
        )
        return

    if "Status" not in self.Ping:
        self.log.logging("Plugin", "Log", "pingZigate - Unknown Status, Ticks: %s  Send a Ping" % self.Ping["Nb Ticks"])
        sendZigateCmd(self, "0014", "")  # Request status
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
        sendZigateCmd(self, "0014", "")  # Request status
        self.connectionState = 1
        self.Ping["Status"] = "Sent"
        self.Ping["TimeStamp"] = int(time.time())
    else:
        self.log.logging("Plugin", "Error", "pingZigate - unknown status : %s" % self.Ping["Status"])


global _plugin
_plugin = BasePlugin()


def onStart():
    global _plugin
    _plugin.onStart()


def onStop():
    global _plugin
    _plugin.onStop()


def onDeviceRemoved(Unit):
    global _plugin
    _plugin.onDeviceRemoved(Unit)


def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)


def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)


def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)


def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)


def onHeartbeat():
    global _plugin
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
