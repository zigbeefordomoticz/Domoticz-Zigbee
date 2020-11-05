#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""

<plugin key="Zigate" name="Zigate plugin" author="zaraki673 & pipiche38" version="4.11" wikilink="https://www.domoticz.com/wiki/Zigate" externallink="https://github.com/pipiche38/Domoticz-Zigate/wiki">
    <description>
        <h2> Plugin Zigate for Domoticz </h2><br/>
    <h3> Short description </h3>
           This plugin allow Domoticz to access to the Zigate (Zigbee) worlds of devices.<br/>
    <h3> Configuration </h3>
          You can use the following parameter to interact with the Zigate:<br/>
    <ul style="list-style-type:square">
            <li> Model: Wifi</li>
            <ul style="list-style-type:square">
                <li> IP : For Wifi Zigate, the IP address. </li>
                <li> Port: For Wifi Zigate,  port number. </li>
                </ul>
                <li> Model USB ,  PI or DIN:</li>
            <ul style="list-style-type:square">
                <li> Serial Port: this is the serial port where your USB or DIN Zigate is connected. (The plugin will provide you the list of possible ports)</li>
                </ul>
            <li> Initialize ZiGate with plugin: This is a required step, with a new ZiGate or if you have done an Erase EEPROM. This will for instance create a new ZigBee Network. Be aware this will erase the Zigate memory and you will delete all pairing information. After that you'll have to re-pair each devices. This is not removing any data from Domoticz nor the plugin database.</li>
    </ul>
    <h3> Support </h3>
    Please use first the Domoticz forums in order to qualify your issue. Select the ZigBee or Zigate topic.
    </description>
    <params>
        <param field="Mode1" label="Zigate Model" width="75px" required="true" default="None">
            <options>
                <option label="USB" value="USB" default="true" />
                <option label="DIN" value="DIN" />
                <option label="PI" value="PI" />
                <option label="Wifi" value="Wifi"/>
                <option label="None" value="None"/>
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
                        <option label="None" value="0"  default="true"/>
                        <option label="Plugin Verbose" value="2"/>
                        <option label="Domoticz Plugin" value="4"/>
                        <option label="Domoticz Devices" value="8"/>
                        <option label="Domoticz Connections" value="16"/>
                        <option label="Verbose+Plugin+Devices" value="14"/>
                        <option label="Verbose+Plugin+Devices+Connections" value="30"/>
                        <option label="Domoticz Framework - All (useless but in case)" value="-1"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
from datetime import datetime
import time
import struct
import json
import queue
import sys
import threading

from Modules.piZigate import switchPiZigate_mode
from Modules.tools import removeDeviceInList
from Modules.basicOutputs import sendZigateCmd, removeZigateDevice, start_Zigate, setExtendedPANID, setTimeServer, leaveRequest, zigateBlueLed, ZigatePermitToJoin
from Modules.input import ZigateRead
from Modules.heartbeat import processListOfDevices
from Modules.database import importDeviceConf, importDeviceConfV2, LoadDeviceList, checkListOfDevice2Devices, checkDevices2LOD, WriteDeviceList
from Modules.domoTools import ResetDevice
from Modules.command import mgtCommand
from Modules.zigateConsts import HEARTBEAT, CERTIFICATION, MAX_LOAD_ZIGATE, MAX_FOR_ZIGATE_BUZY
from Modules.txPower import set_TxPower, get_TxPower
from Modules.checkingUpdate import checkPluginVersion, checkPluginUpdate, checkFirmwareUpdate
from Modules.restartPlugin import restartPluginViaDomoticzJsonApi

#from Classes.APS import APSManagement
from Classes.IAS import IAS_Zone_Management
from Classes.PluginConf import PluginConf
from Classes.Transport import ZigateTransport
from Classes.TransportStats import TransportStatistics
from Classes.LoggingManagement import LoggingManagement

from GroupMgtv2.GroupManagement import GroupsManagement
from Classes.AdminWidgets import AdminWidgets
from Classes.OTA import OTAManagement

from WebServer.WebServer import WebServer

from Classes.NetworkMap import NetworkMap
from Classes.NetworkEnergy import NetworkEnergy


VERSION_FILENAME = '.hidden/VERSION'

TEMPO_NETWORK = 2    # Start HB totrigget Network Status
TIMEDOUT_START = 10  # Timeoud for the all startup
TIMEDOUT_FIRMWARE = 5 # HB before request Firmware again
TEMPO_START_ZIGATE = 1 # Nb HB before requesting a Start_Zigate




class BasePlugin:
    enabled = False

    def __init__(self):

        self.ListOfDevices = {}  # {DevicesAddresse : { status : status_de_detection, data : {ep list ou autres en fonctions du status}}, DevicesAddresse : ...}
        self.DevicesInPairingMode = []
        self.DiscoveryDevices = {} # Used to collect pairing information
        self.IEEE2NWK = {}
        self.zigatedata = {}
        self.DeviceConf = {} # Store DeviceConf.txt, all known devices configuration

        # Objects from Classe
        self.ZigateComm = None
        self.groupmgt = None
        self.networkmap = None
        self.networkenergy = None
        self.domoticzdb_DeviceStatus = None      # Object allowing direct access to Domoticz DB DeviceSatus
        self.domoticzdb_Hardware = None         # Object allowing direct access to Domoticz DB Hardware
        self.domoticzdb_Preferences = None         # Object allowing direct access to Domoticz DB Preferences
        self.adminWidgets = None   # Manage AdminWidgets object
        self.pluginconf = None     # PlugConf object / all configuration parameters
        self.OTA = None
        self.statistics = None
        self.iaszonemgt = None      # Object to manage IAS Zone
        self.webserver = None
        self.transport = None         # USB or Wifi
        self.log = None
        #self._ReqRcv = bytearray()

        self.UnknownDevices = []   # List of unknown Device NwkId
        self.permitTojoin = {}
        self.permitTojoin['Duration'] = 0
        self.permitTojoin['Starttime'] = 0
        self.CommiSSionning = False    # This flag is raised when a Device Annocement is receive, in order to give priority to commissioning

        self.busy = False    # This flag is raised when a Device Annocement is receive, in order to give priority to commissioning
        self.homedirectory = None
        self.HardwareID = None
        self.Key = None
        self.DomoticzVersion = None
        self.StartupFolder = None
        self.DeviceListName = None
        self.pluginParameters = None

        self.PluginHealth = {}
        self.Ping = {}
        self.Ping['Nb Ticks'] =  self.Ping['Status'] = self.Ping['TimeStamp'] = None
        self.connectionState = None

        self.HBcount = 0
        self.HeartbeatCount = 0
        self.internalHB = 0

        self.currentChannel = None  # Curent Channel. Set in Decode8009/Decode8024
        self.ZigateIEEE = None       # Zigate IEEE. Set in CDecode8009/Decode8024
        self.ZigateNWKID = None       # Zigate NWKID. Set in CDecode8009/Decode8024
        self.FirmwareVersion = None
        self.FirmwareMajorVersion = None
        self.mainpowerSQN = None    # Tracking main Powered SQN
        #self.ForceCreationDevice = None   # 

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

        self.SchneiderZone = None        # Manage Zone for Wiser Thermostat and HACT

    def onStart(self):
    
        Domoticz.Heartbeat( 1 )
        self.pluginParameters = dict(Parameters)

        with open( Parameters["HomeFolder"] + VERSION_FILENAME, 'rt') as versionfile:
            _pluginversion = json.load( versionfile, encoding=dict)

        self.pluginParameters['PluginBranch'] = _pluginversion['branch']
        self.pluginParameters['PluginVersion'] = _pluginversion['version']

        self.pluginParameters['TimeStamp'] = 0
        self.pluginParameters['available'] =  None
        self.pluginParameters['available-firmMajor'] =  None
        self.pluginParameters['available-firmMinor'] =  None
        self.pluginParameters['FirmwareVersion'] = None
        self.pluginParameters['FirmwareUpdate'] = None
        self.pluginParameters['PluginUpdate'] = None

        Domoticz.Status("Zigate plugin %s-%s started" %(self.pluginParameters['PluginBranch'], self.pluginParameters['PluginVersion']))

        Domoticz.Status( "Debug: %s" %int(Parameters["Mode6"]))
        if Parameters["Mode6"] != "0":
            Domoticz.Log("Debug Mode: %s, We do recommend to leave Verbors to None" %int(Parameters["Mode6"]))
            DumpConfigToLog()

        self.busy = True

        self.DomoticzVersion = Parameters["DomoticzVersion"]
        self.homedirectory = Parameters["HomeFolder"]
        self.HardwareID = (Parameters["HardwareID"])
        self.Key = (Parameters["Key"])
        self.transport = Parameters["Mode1"]

        # Import PluginConf.txt
        Domoticz.Log("DomoticzVersion: %s" %Parameters["DomoticzVersion"])
        if Parameters["DomoticzVersion"].find('build') == -1:
            self.VersionNewFashion = False
            # Old fashon Versioning
            major, minor = Parameters["DomoticzVersion"].split('.')
        else:
            self.VersionNewFashion = True
            majorminor, dummy, build = Parameters["DomoticzVersion"].split(' ')
            build = build.strip(')')
            self.DomoticzBuild = int(build)
            major, minor = majorminor.split('.')

        self.DomoticzMajor = int(major)
        self.DomoticzMinor = int(minor)


        Domoticz.Status( "load PluginConf" )
        self.pluginconf = PluginConf(Parameters["HomeFolder"], self.HardwareID)

        # Create the adminStatusWidget if needed
        self.PluginHealth['Flag'] = 1
        self.PluginHealth['Txt'] = 'Startup'
                
        if self.log == None:
            self.log = LoggingManagement(self.pluginconf, self.PluginHealth, self.HardwareID)
            self.log.openLogFile()


        self.log.logging( 'Plugin', 'Status',  "Python Version - %s" %sys.version)
        assert sys.version_info >= (3, 4)
        self.log.logging( 'Plugin', 'Status',  "DomoticzVersion: %s" %Parameters["DomoticzVersion"])
        self.log.logging( 'Plugin', 'Status',  "DomoticzHash: %s" %Parameters["DomoticzHash"])
        self.log.logging( 'Plugin', 'Status',  "DomoticzBuildTime: %s" %Parameters["DomoticzBuildTime"])

        if (not self.VersionNewFashion and (self.DomoticzMajor > 4 or ( self.DomoticzMajor == 4 and self.DomoticzMinor >= 10355))) or self.VersionNewFashion:
            # This is done here and not global, as on Domoticz V4.9700 it is not compatible with Threaded modules

            from Classes.DomoticzDB import DomoticzDB_DeviceStatus, DomoticzDB_Hardware, DomoticzDB_Preferences

            self.log.logging( 'Plugin', 'Debug', "Startup Folder: %s" %Parameters["StartupFolder"])
            self.log.logging( 'Plugin', 'Debug', "Home Folder: %s" %Parameters["HomeFolder"])
            self.log.logging( 'Plugin', 'Debug', "User Data Folder: %s" %Parameters["UserDataFolder"])
            self.log.logging( 'Plugin', 'Debug', "Web Root Folder: %s" %Parameters["WebRoot"])
            self.log.logging( 'Plugin', 'Debug', "Database: %s" %Parameters["Database"])
            self.StartupFolder = Parameters["StartupFolder"]
            _dbfilename = Parameters["Database"]

            self.log.logging( 'Plugin', 'Status', "Opening DomoticzDB in raw")
            self.log.logging( 'Plugin', 'Debug', "   - DeviceStatus table")
            self.domoticzdb_DeviceStatus = DomoticzDB_DeviceStatus( _dbfilename, self.pluginconf, self.HardwareID, self.log )

            self.log.logging( 'Plugin', 'Debug', "   - Hardware table")
            self.domoticzdb_Hardware = DomoticzDB_Hardware( _dbfilename, self.pluginconf, self.HardwareID, self.log )

            self.log.logging( 'Plugin', 'Debug', "   - Preferences table")
            self.domoticzdb_Preferences = DomoticzDB_Preferences( _dbfilename, self.pluginconf, self.log )

            self.WebUsername, self.WebPassword = self.domoticzdb_Preferences.retreiveWebUserNamePassword()
            #Domoticz.Status("Domoticz Website credentials %s/%s" %(self.WebUsername, self.WebPassword))




        self.adminWidgets = AdminWidgets( self.pluginconf, Devices, self.ListOfDevices, self.HardwareID )
        self.adminWidgets.updateStatusWidget( Devices, 'Startup')
        
        self.DeviceListName = "DeviceList-" + str(Parameters['HardwareID']) + ".txt"
        self.log.logging( 'Plugin', 'Status', "Plugin Database: %s" %self.DeviceListName)

        if  self.pluginconf.pluginConf['capturePairingInfos'] == 1 :
            self.DiscoveryDevices = {}

        importDeviceConfV2( self )
    
        #if type(self.DeviceConf) is not dict:
        if not isinstance(self.DeviceConf, dict):
            Domoticz.Error("DeviceConf initialisatio failure!!! %s" %type(self.DeviceConf))
            return

        #Import DeviceList.txt Filename is : DeviceListName
        self.log.logging( 'Plugin', 'Status', "load ListOfDevice" )
        if LoadDeviceList( self ) == 'Failed' :
            Domoticz.Error("Something wennt wrong during the import of Load of Devices ...")
            Domoticz.Error("Please cross-check your log ... You must be on V3 of the DeviceList and all DeviceID in Domoticz converted to IEEE")
            return            
        
        self.log.logging( 'Plugin', 'Debug', "ListOfDevices : " )
        for e in self.ListOfDevices.items(): 
            self.log.logging( 'Plugin', 'Debug', " "+str(e))
            
        self.log.logging( 'Plugin', 'Debug', "IEEE2NWK      : " )
        for e in self.IEEE2NWK.items(): 
            self.log.logging( 'Plugin', 'Debug', "  "+str(e))

        # Check proper match against Domoticz Devices
        checkListOfDevice2Devices( self, Devices )
        checkDevices2LOD( self, Devices )

        self.log.logging( 'Plugin', 'Debug', "ListOfDevices after checkListOfDevice2Devices: " +str(self.ListOfDevices) )
        self.log.logging( 'Plugin', 'Debug', "IEEE2NWK after checkListOfDevice2Devices     : " +str(self.IEEE2NWK) )

        # Create Statistics object
        self.statistics = TransportStatistics(self.pluginconf)

        # Create APS object to manage Transmission Errors
        #if self.pluginconf.pluginConf['enableAPSFailureLoging'] or self.pluginconf.pluginConf['enableAPSFailureReporting']:
        #    self.APS = APSManagement( self.ListOfDevices , Devices, self.pluginconf, self.log)


        # Connect to Zigate only when all initialisation are properly done.
        self.log.logging( 'Plugin', 'Status', "Transport mode: %s" %self.transport)
        if  self.transport == "USB":
            self.ZigateComm = ZigateTransport( self.transport, self.statistics, self.pluginconf, self.processFrame,\
                    self.log, serialPort=Parameters["SerialPort"] )
        elif  self.transport == "DIN":
            self.ZigateComm = ZigateTransport( self.transport, self.statistics, self.pluginconf, self.processFrame,\
                    self.log, serialPort=Parameters["SerialPort"] )
        elif  self.transport == "PI":
            switchPiZigate_mode( self, 'run' )
            self.ZigateComm = ZigateTransport( self.transport, self.statistics, self.pluginconf, self.processFrame,\
                    self.log, serialPort=Parameters["SerialPort"] )
        elif  self.transport == "Wifi":
            self.ZigateComm = ZigateTransport( self.transport, self.statistics, self.pluginconf, self.processFrame,\
                    self.log, wifiAddress= Parameters["Address"], wifiPort=Parameters["Port"] )
        elif self.transport == "None":
            self.log.logging( 'Plugin', 'Status', "Transport mode set to None, no communication.")
            self.FirmwareVersion = '031c'
            self.PluginHealth['Firmware Update'] = {}
            self.PluginHealth['Firmware Update']['Progress'] = '75 %'
            self.PluginHealth['Firmware Update']['Device'] = '1234'
            return
        else :
            Domoticz.Error("Unknown Transport comunication protocol : "+str(self.transport) )
            return

        self.log.logging( 'Plugin', 'Debug', "Establish Zigate connection" )
        self.ZigateComm.open_conn()

        # IAS Zone Management
        if self.iaszonemgt is None:
            # Create IAS Zone object
            #Domoticz.Log("Init IAS_Zone_management ZigateComm: %s" %self.ZigateComm)
            self.iaszonemgt = IAS_Zone_Management( self.pluginconf, self.ZigateComm , self.ListOfDevices, self.log)

        self.busy = False

    def onStop(self):
        self.log.logging( 'Plugin', 'Status', "onStop called")

        if self.domoticzdb_DeviceStatus:
            self.domoticzdb_DeviceStatus.closeDB()

        if self.domoticzdb_Hardware:
            self.domoticzdb_Hardware.closeDB()

        if self.ZigateComm:
            self.ZigateComm.close_conn()

        if self.webserver:
            self.webserver.onStop()

        if ( self.DomoticzMajor > 4 or self.DomoticzMajor == 4 and self.DomoticzMinor >= 10355 or self.VersionNewFashion ):
            for thread in threading.enumerate():
                if (thread.name != threading.current_thread().name):
                    Domoticz.Log("'"+thread.name+"' is running, it must be shutdown otherwise Domoticz will abort on plugin exit.")

        #self.ZigateComm.close_conn()
        WriteDeviceList(self, 0)

        self.statistics.printSummary()
        self.statistics.writeReport()
        self.PluginHealth['Flag'] = 3
        self.PluginHealth['Txt'] = 'No Communication'
        self.adminWidgets.updateStatusWidget( Devices, 'No Communication')

        self.log.closeLogFile()

    def onDeviceRemoved( self, Unit ) :

        self.log.logging( 'Plugin', 'Debug', "onDeviceRemoved called" )
        # Let's check if this is End Node, or Group related.
        if Devices[Unit].DeviceID in self.IEEE2NWK:
            IEEE = Devices[Unit].DeviceID
            NwkId = self.IEEE2NWK[ IEEE ]

            # Command belongs to a end node
            self.log.logging( 'Plugin', 'Status', "onDeviceRemoved - removing End Device")
            fullyremoved = removeDeviceInList( self, Devices, Devices[Unit].DeviceID , Unit)

            # We might have to remove also the Device from Groups
            if fullyremoved and self.groupmgt:
                self.groupmgt.RemoveNwkIdFromAllGroups( NwkId)

            # We should call this only if All Widgets have been remved !
            if fullyremoved:
                # Let see if enabled if we can fully remove this object from Zigate
                if self.pluginconf.pluginConf['allowRemoveZigateDevice']:
                    IEEE = Devices[Unit].DeviceID
                    # sending a Leave Request to device, so the device will send a leave
                    leaveRequest( self, IEEE= IEEE )

                    # for a remove in case device didn't send the leave
                    if self.ZigateIEEE:
                        sendZigateCmd(self, "0026", self.ZigateIEEE + IEEE )
                        self.log.logging( 'Plugin', 'Status', "onDeviceRemoved - removing Device %s -> %s in Zigate" %(Devices[Unit].Name, IEEE))
                    else:
                        Domoticz.Error("onDeviceRemoved - too early, Zigate and plugin initialisation not completed")
                else:
                    self.log.logging( 'Plugin', 'Status', "onDeviceRemoved - device entry %s from Zigate not removed. You need to enable 'allowRemoveZigateDevice' parameter. Do consider that it works only for main powered devices." %Devices[Unit].DeviceID)

            self.log.logging( 'Plugin', 'Debug', "ListOfDevices :After REMOVE " + str(self.ListOfDevices))
            return

        if self.groupmgt and Devices[Unit].DeviceID in self.groupmgt.ListOfGroups:
                self.log.logging( 'Plugin', 'Status', "onDeviceRemoved - removing Group of Devices")
                # Command belongs to a Zigate group
                self.groupmgt.FullRemoveOfGroup( Unit, Devices[Unit].DeviceID )

    def onConnect(self, Connection, Status, Description):

        def decodeConnection( connection ):
            decoded = {}
            for i in connection.strip().split(','):
                label, value = i.split(': ')
                label = label.strip().strip("'")
                value = value.strip().strip("'")
                decoded[label] = value
            return decoded

        self.log.logging( 'Plugin', 'Debug', "onConnect called with status: %s" %Status)
        self.log.logging( 'Plugin', 'Debug', "onConnect %s called with status: %s and Desc: %s" %( Connection, Status, Description))

        decodedConnection = decodeConnection ( str(Connection) )
        if 'Protocol' in decodedConnection:
            if decodedConnection['Protocol'] in ( 'HTTP', 'HTTPS') : # We assumed that is the Web Server 
                if self.webserver:
                    self.webserver.onConnect( Connection, Status, Description)
                return

        self.busy = True

        if Status != 0:
            Domoticz.Error("Failed to connect ("+str(Status)+")")
            self.log.logging( 'Plugin', 'Debug', "Failed to connect ("+str(Status)+") with error: "+Description)
            self.connectionState = 0
            self.ZigateComm.re_conn()
            self.PluginHealth['Flag'] = 3
            self.PluginHealth['Txt'] = 'No Communication'
            self.adminWidgets.updateStatusWidget( Devices, 'No Communication')
            return

        self.log.logging( 'Plugin', 'Debug', "Connected successfully")
        if self.connectionState is None:
            self.PluginHealth['Flag'] = 2
            self.PluginHealth['Txt'] = 'Starting Up'
            self.adminWidgets.updateStatusWidget( Devices, 'Starting the plugin up')
        elif self.connectionState == 0:
            self.log.logging( 'Plugin', 'Status', "Reconnected after failure")
            self.PluginHealth['Flag'] = 2
            self.PluginHealth['Txt'] = 'Reconnecting after failure'

        self.connectionState = 1
        self.Ping['Status'] = None
        self.Ping['TimeStamp'] = None
        self.Ping['Permit'] = None
        self.Ping['Nb Ticks'] = 1




        return True

    def onMessage(self, Connection, Data):
        #self.log.logging( 'Plugin', 'Debug', "onMessage called on Connection " + " Data = '" +str(Data) + "'")
        if isinstance(Data, dict):
            if self.webserver:
                self.webserver.onMessage( Connection, Data)
            return

        if len(Data) == 0:
            Domoticz.Error("onMessage - empty message received on %s" %Connection)

        self.Ping['Nb Ticks'] = 0
        self.ZigateComm.on_message(Data)

    def processFrame( self, Data , i_sqn, TransportInfos=None):

        #start_time = int(time.time() *1000)
        #Domoticz.Log("### Processing: %s" %Data)
        ZigateRead( self, Devices, Data, i_sqn )
        #stop_time = int(time.time() *1000)
        #Domoticz.Log("### Completion: %s is %s ms" %(Data, ( stop_time - start_time)))

    def onCommand(self, Unit, Command, Level, Color):

        self.log.logging( 'Plugin', 'Debug', "onCommand - unit: %s, command: %s, level: %s, color: %s" %(Unit, Command, Level, Color))

        # Let's check if this is End Node, or Group related.
        if Devices[Unit].DeviceID in self.IEEE2NWK:
            # Command belongs to a end node
            mgtCommand( self, Devices, Unit, Command, Level, Color )

        elif self.groupmgt:
            #if Devices[Unit].DeviceID in self.groupmgt.ListOfGroups:
            #    # Command belongs to a Zigate group
            self.log.logging( 'Plugin', 'Debug', "Command: %s/%s/%s to Group: %s" %(Command,Level,Color, Devices[Unit].DeviceID))
            self.groupmgt.processCommand( Unit, Devices[Unit].DeviceID, Command, Level, Color )

        elif Devices[Unit].DeviceID.find('Zigate-01-') != -1:
            self.log.logging( 'Plugin', 'Debug', "onCommand - Command adminWidget: %s " %Command)
            self.adminWidgets.handleCommand( self, Command)

        else:
            Domoticz.Error("onCommand - Unknown device or GrpMgr not enabled %s, unit %s , id %s" \
                    %(Devices[Unit].Name, Unit, Devices[Unit].DeviceID))

    def onDisconnect(self, Connection):

        def decodeConnection( connection ):

            decoded = {}
            for i in connection.strip().split(','):
                label, value = i.split(': ')
                label = label.strip().strip("'")
                value = value.strip().strip("'")
                decoded[label] = value
            return decoded

        self.log.logging( 'Plugin', 'Debug', "onDisconnect: %s" %Connection)
        decodedConnection = decodeConnection ( str(Connection) )

        if 'Protocol' in decodedConnection:
            if decodedConnection['Protocol'] in ( 'HTTP', 'HTTPS') : # We assumed that is the Web Server 
                if self.webserver:
                    self.webserver.onDisconnect( Connection )
                return

        self.connectionState = 0
        self.PluginHealth['Flag'] = 0
        self.PluginHealth['Txt'] = 'Shutdown'
        self.adminWidgets.updateStatusWidget( Devices, 'Plugin stop')
        self.log.logging( 'Plugin', 'Status', "onDisconnect called")

    def onHeartbeat(self):

        if self.pluginconf is None:
            return

        if self.ZigateComm:
            self.ZigateComm.check_timed_out_for_tx_queues()

        self.internalHB += 1
        if self.PDMready and (self.internalHB % HEARTBEAT) != 0:
            return
        busy_ = False
        self.HeartbeatCount += 1 

        # Quiet a bad hack. In order to get the needs for ZigateRestart
        # from WebServer
        if ( 'startZigateNeeded' in self.zigatedata and self.zigatedata['startZigateNeeded'] ):
            self.startZigateNeeded = self.HeartbeatCount
            del self.zigatedata['startZigateNeeded']

        # Starting PDM on Host firmware version, we have to wait that Zigate is fully initialized ( PDM loaded into memory from Host).
        # We wait for self.zigateReady which is set to True in th pdmZigate module
        if ( self.transport != 'None' and not self.PDMready and self.HeartbeatCount > (60 // HEARTBEAT) ):
            self.log.logging( 'Plugin', 'Error', "[%3s] I have hard time to get ZiGate Version. Mostlikly ZiGate communication doesn't work" %( self.HeartbeatCount))
            self.log.logging( 'Plugin', 'Error', "[   ] Stop the plugin and check ZiGate.")

        if self.transport != 'None' and not self.PDMready:
            self.log.logging( 'Plugin','Debug', "PDMready: %s requesting Get version" %( self.PDMready))
            sendZigateCmd(self, "0010", "")
            return

        if self.transport != 'None':
            self.log.logging( 'Plugin', 'Debug', "onHeartbeat - busy = %s, Health: %s, startZigateNeeded: %s/%s, InitPhase1: %s InitPhase2: %s, InitPhase3: %s PDM_LOCK: %s" \
                %(self.busy, self.PluginHealth, self.startZigateNeeded, self.HeartbeatCount, self.InitPhase1, self.InitPhase2, self.InitPhase3, self.ZigateComm.pdm_lock_status() ))

        if self.transport != 'None' and ( self.startZigateNeeded or not self.InitPhase1 or not self.InitPhase2):
            # Require Transport
            # Perform erasePDM if required
            if not self.InitPhase1:
                zigateInit_Phase1( self)
                return

            # Check if Restart is needed ( After an ErasePDM or a Soft Reset
            if self.startZigateNeeded:
                if ( self.HeartbeatCount > self.startZigateNeeded + TEMPO_START_ZIGATE):
                    # Need to check if and ErasePDM has been performed.
                    # In case case, we have to set the extendedPANID
                    # ErasePDM has been requested, we are in the next Loop.
                    if (
                        self.ErasePDMDone
                        and self.pluginconf.pluginConf['extendedPANID'] is not None
                    ):
                        self.log.logging( 'Plugin', 'Status', "ZigateConf - Setting extPANID : 0x%016x" %( self.pluginconf.pluginConf['extendedPANID']) )
                        setExtendedPANID(self, self.pluginconf.pluginConf['extendedPANID'])

                    start_Zigate( self )
                    self.startZigateNeeded = False
                return

            if not self.InitPhase2:
                zigateInit_Phase2(self)
                return

        if not self.InitPhase3:
            zigateInit_Phase3( self )
            return

        # Checking Version
        self.pluginParameters['TimeStamp'] = int(time.time())
        if self.pluginconf.pluginConf['internetAccess'] and \
                ( self.pluginParameters['available'] is None or self.HeartbeatCount % ( 12 * 3600 // HEARTBEAT) == 0 ):
            self.pluginParameters['available'] , self.pluginParameters['available-firmMajor'], self.pluginParameters['available-firmMinor'] = checkPluginVersion( self.pluginParameters['PluginBranch'] )
            self.pluginParameters['FirmwareUpdate'] = False
            self.pluginParameters['PluginUpdate'] = False

            if checkPluginUpdate( self.pluginParameters['PluginVersion'], self.pluginParameters['available']):
                self.log.logging( 'Plugin', 'Status', "There is a newer plugin version available on gitHub")
                self.pluginParameters['PluginUpdate'] = True
            if checkFirmwareUpdate( self.FirmwareMajorVersion, self.FirmwareVersion, self.pluginParameters['available-firmMajor'], self.pluginParameters['available-firmMinor']):
                self.log.logging( 'Plugin', 'Status', "There is a newer Zigate Firmware version available")
                self.pluginParameters['FirmwareUpdate'] = True

        if self.transport == 'None':
            return

        # Memorize the size of Devices. This is will allow to trigger a backup of live data to file, if the size change.
        prevLenDevices = len(Devices)

        # Manage all entries in  ListOfDevices (existing and up-coming devices)
        processListOfDevices( self , Devices )

        self.iaszonemgt.IAS_heartbeat( )

        # Reset Motion sensors
        ResetDevice( self, Devices, "Motion",5)

        # Write the ListOfDevice in HBcount % 200 ( 3' ) or immediatly if we have remove or added a Device
        if len(Devices) == prevLenDevices:
            WriteDeviceList(self, ( 90 * 5) )

        else:
            self.log.logging( 'Plugin', 'Debug', "Devices size has changed , let's write ListOfDevices on disk")
            WriteDeviceList(self, 0)       # write immediatly
        if self.CommiSSionning:
            self.PluginHealth['Flag'] = 2
            self.PluginHealth['Txt'] = 'Enrollment in Progress'
            self.adminWidgets.updateStatusWidget( Devices, 'Enrollment')
            # Maintain trend statistics
            self.statistics._Load = self.ZigateComm.loadTransmit()
            self.statistics.addPointforTrendStats( self.HeartbeatCount )
            return

        # Group Management
        if self.groupmgt:
            self.groupmgt.hearbeat_group_mgt()

        # OTA upgrade
        if self.OTA:
            self.OTA.heartbeat()

        # Check PermitToJoin
        if ( self.permitTojoin['Duration'] != 255 and self.permitTojoin['Duration'] != 0 and \
                 int(time.time()) >= (self.permitTojoin['Starttime'] + self.permitTojoin['Duration']) ):
            sendZigateCmd( self, "0014", "" ) # Request status
            self.permitTojoin['Duration'] = 0

        # Heartbeat - Ping Zigate every minute to check connectivity
        # If fails then try to reConnect
        if self.pluginconf.pluginConf['Ping']:
            pingZigate( self )
            self.Ping['Nb Ticks'] += 1

        if self.HeartbeatCount % ( 3600 // HEARTBEAT) == 0:
            self.log.loggingCleaningErrorHistory()
            sendZigateCmd(self,"0017", "")
            

        if self.ZigateComm.loadTransmit() >= MAX_FOR_ZIGATE_BUZY:
            # This mean that 4 commands are on the Queue to be executed by Zigate.
            busy_ = True

        if busy_:
            self.PluginHealth['Flag'] = 2
            self.PluginHealth['Txt'] = 'Busy'
            self.adminWidgets.updateStatusWidget( Devices, 'Busy')

        elif not self.connectionState:
            self.PluginHealth['Flag'] = 3
            self.PluginHealth['Txt'] = 'No Communication'
            self.adminWidgets.updateStatusWidget( Devices, 'No Communication')

        else:
            self.PluginHealth['Flag'] = 1
            self.PluginHealth['Txt'] = 'Ready'
            self.adminWidgets.updateStatusWidget( Devices, 'Ready')

        self.busy = busy_

        # Maintain trend statistics
        self.statistics._Load = 0
        if self.ZigateComm.loadTransmit() >= MAX_FOR_ZIGATE_BUZY:
            self.statistics._Load = self.ZigateComm.loadTransmit()

        self.statistics.addPointforTrendStats( self.HeartbeatCount )

        return True

def zigateInit_Phase1(self ):
    """
    Mainly managed Erase PDM if required
    """

    self.log.logging( 'Plugin', 'Debug', "zigateInit_Phase1 PDMDone: %s" %(self.ErasePDMDone))
    # Check if we have to Erase PDM.
    if Parameters["Mode3"] == "True" and not self.ErasePDMDone: # Erase PDM
        if not self.ErasePDMDone:
            self.ErasePDMDone = True
            if self.domoticzdb_Hardware:
                self.domoticzdb_Hardware.disableErasePDM()
            self.log.logging( 'Plugin', 'Status', "Erase Zigate PDM")
            sendZigateCmd(self, "0012", "")
            self.PDMready = False
            self.startZigateNeeded = 1
            self.HeartbeatCount = 1
            return

        # After an Erase PDM we have to do a full start of Zigate
        self.log.logging( 'Plugin', 'Debug', "----> starZigate")
        return

    self.busy = False
    self.InitPhase1 = True
    return True

def zigateInit_Phase2( self):
    """
    Make sure that all setup is in place
    """

    if self.FirmwareVersion is None  or self.ZigateIEEE is None or self.ZigateNWKID == 'ffff':
        if self.FirmwareVersion is None:
            # Ask for Firmware Version
            sendZigateCmd(self, "0010", "") 
        if self.ZigateIEEE is None or self.ZigateNWKID == 'ffff':
            # Request Network State
            sendZigateCmd(self, "0009", "") 

        if self.HeartbeatCount > TIMEDOUT_FIRMWARE:
            Domoticz.Error("We are having difficulties to start Zigate. Basically we are not receiving what we expect from Zigate")
            Domoticz.Error("Plugin is not started ...")
        return


    # Set Time server to HOST time
    setTimeServer( self )

    # If applicable, put Zigate in NO Pairing Mode
    self.Ping['Permit'] = None
    if self.pluginconf.pluginConf['resetPermit2Join']:
        ZigatePermitToJoin( self, 0 )
    else:
        sendZigateCmd( self, "0014", "" ) # Request Permit to Join status

    # Request List of Active Devices
    sendZigateCmd(self, "0015", "") 


    # Ready for next phase
    self.InitPhase2 = True

def zigateInit_Phase3( self ):

    # We can now do what must be done when we known the Firmware version

    if self.FirmwareVersion is None:
        return

    self.InitPhase3 = True

    self.pluginParameters['FirmwareVersion'] = self.FirmwareVersion

    # Check Firmware version
    if self.FirmwareVersion.lower() < '030f':
        self.log.logging( 'Plugin', 'Status', "You are not on the latest firmware version, please consider to upgrade")
    elif self.FirmwareVersion.lower() == '030e':
        self.log.logging( 'Plugin', 'Status', "You are not on the latest firmware version, This version is known to have problem loosing Xiaomi devices, please consider to upgrae")
    elif self.FirmwareVersion.lower() == '030f' and self.FirmwareMajorVersion == '0002':
        Domoticz.Error("You are not running on the Official 3.0f version (it was a pre-3.0f)")
    elif self.FirmwareVersion.lower() == '2100':
        self.log.logging( 'Plugin', 'Status', "Firmware for Pluzzy devices")
        self.PluzzyFirmware = True
    elif self.FirmwareVersion.lower() == '031b':
        self.log.logging( 'Plugin', 'Status', "You are not on the latest firmware version, This version is known to have problem, please consider to upgrae")


    elif int(self.FirmwareVersion,16) > 0x031d:
        Domoticz.Error("Firmware %s is not yet supported" %self.FirmwareVersion.lower())

    if self.transport != 'None' and int(self.FirmwareVersion,16) >= 0x030f and int(self.FirmwareMajorVersion,16) >= 0x0003:
        if self.pluginconf.pluginConf['blueLedOnOff']:
            zigateBlueLed( self, True)
        else:
            zigateBlueLed( self, False)

        # Set the TX Power
        set_TxPower( self, self.pluginconf.pluginConf['TXpower_set'])

        # Set Certification Code
        if self.pluginconf.pluginConf['CertificationCode'] in CERTIFICATION:
            self.log.logging( 'Plugin', 'Status', "Zigate set to Certification : %s" %CERTIFICATION[self.pluginconf.pluginConf['CertificationCode']])
            sendZigateCmd(self, '0019', '%02x' %self.pluginconf.pluginConf['CertificationCode'])

        # Enable Group Management
        if self.groupmgt is None and self.pluginconf.pluginConf['enablegroupmanagement']:
            self.log.logging( 'Plugin', 'Status', "Start Group Management")
            self.groupmgt = GroupsManagement( self.pluginconf, self.ZigateComm, self.adminWidgets, Parameters["HomeFolder"],
                    self.HardwareID, Devices, self.ListOfDevices, self.IEEE2NWK, self.log )
            if self.groupmgt and self.ZigateIEEE:
                self.groupmgt.updateZigateIEEE( self.ZigateIEEE) 

            if self.pluginconf.pluginConf['zigatePartOfGroup0000']:
                # Add Zigate NwkId 0x0000 Ep 0x01 to GroupId 0x0000
                self.groupmgt.addGroupMemberShip( '0000', '01', '0000')

        # Create Network Map object and trigger one scan
        if self.networkmap is None:
            self.networkmap = NetworkMap( self.pluginconf, self.ZigateComm, self.ListOfDevices, Devices, self.HardwareID, self.log)
     
        # Create Network Energy object and trigger one scan
        if self.networkenergy is None:
            self.networkenergy = NetworkEnergy( self.pluginconf, self.ZigateComm, self.ListOfDevices, Devices, self.HardwareID, self.log)        #    if len(self.ListOfDevices) > 1:        #        self.log.logging( 'Plugin', 'Status', "Trigger a Energy Level Scan")        #        self.networkenergy.start_scan()

    # In case we have Transport = None , let's check if we have to active Group management or not. (For Test and Web UI Dev purposes
    if self.transport == 'None' and self.groupmgt is None and self.pluginconf.pluginConf['enablegroupmanagement']:
           self.groupmgt = GroupsManagement( self.pluginconf, self.ZigateComm, self.adminWidgets, Parameters["HomeFolder"],
                   self.HardwareID, Devices, self.ListOfDevices, self.IEEE2NWK, self.log )
           if self.groupmgt and self.ZigateIEEE:
               self.groupmgt.updateZigateIEEE( self.ZigateIEEE) 

    # Enable Over The Air Upgrade if applicable
    if self.OTA is None and self.pluginconf.pluginConf['allowOTA']:
        self.OTA = OTAManagement( self.pluginconf, self.adminWidgets, self.ZigateComm, Parameters["HomeFolder"],
                    self.HardwareID, Devices, self.ListOfDevices, self.IEEE2NWK, self.log, self.PluginHealth)

    # Starting WebServer
    if self.webserver is None:
        if Parameters['Mode4'].isdigit():
            if (not self.VersionNewFashion and (self.DomoticzMajor < 4 or ( self.DomoticzMajor == 4 and self.DomoticzMinor < 10901))):
                Domoticz.Log("self.VersionNewFashion: %s" %self.VersionNewFashion)
                Domoticz.Log("self.DomoticzMajor    : %s" %self.DomoticzMajor)
                Domoticz.Log("self.DomoticzMinor    : %s" %self.DomoticzMinor)
                Domoticz.Error("ATTENTION: the WebServer part is not supported with this version of Domoticz. Please upgrade to a version greater than 4.10901")

            self.log.logging( 'Plugin', 'Status', "Start Web Server connection")
            self.webserver = WebServer( self.networkenergy, self.networkmap, self.zigatedata, self.pluginParameters, self.pluginconf, self.statistics, 
                self.adminWidgets, self.ZigateComm, Parameters["HomeFolder"], self.HardwareID, self.DevicesInPairingMode, self.groupmgt,self.OTA, Devices, 
                self.ListOfDevices, self.IEEE2NWK , self.permitTojoin , self.WebUsername, self.WebPassword, self.PluginHealth, Parameters['Mode4'], 
                self.log)
            if self.FirmwareVersion:
                self.webserver.update_firmware( self.FirmwareVersion )
        else:
            Domoticz.Error("WebServer disabled du to Parameter Mode4 set to %s" %Parameters['Mode4'])

    self.log.logging( 'Plugin', 'Status', "Plugin with Zigate firmware %s correctly initialized" %self.FirmwareVersion)

    # If firmware above 3.0d, Get Network State 
    if (
        self.FirmwareVersion >= "030d"
        and (self.HeartbeatCount % (3600 // HEARTBEAT)) == 0
        and self.transport != 'None'
        ):
        sendZigateCmd(self, "0009","")

def pingZigate( self ):

    """
    Ping Zigate to check if it is alive.
    Do it only if no messages have been received during the last period

    'Nb Ticks' is set to 0 every time a message is received from Zigate
    'Nb Ticks' is incremented at every heartbeat
    """

    # Frequency is set to below 4' as regards to the TCP timeout with Wifi-Zigate
    PING_CHECK_FREQ =  ((5 * 60 ) / 2 ) - 7

    self.log.logging( 'Plugin', 'Debug', "pingZigate - [%s] Nb Ticks: %s Status: %s TimeStamp: %s" \
            %(self.HeartbeatCount, self.Ping['Nb Ticks'], self.Ping['Status'], self.Ping['TimeStamp']))

    if self.Ping['Nb Ticks'] == 0: # We have recently received a message, Zigate is up and running
        self.Ping['Status'] = 'Receive'
        self.connectionState = 1
        self.log.logging( 'Plugin', 'Debug', "pingZigate - We have receive a message in the cycle ")
        return                     # Most likely between the cycle.

    if self.Ping['Status'] == 'Sent':
        delta = int(time.time()) - self.Ping['TimeStamp']
        self.log.logging( 'Plugin', 'Log', "pingZigate - WARNING: Ping sent but no response yet from Zigate. Status: %s  - Ping: %s sec" %(self.Ping['Status'], delta))
        if delta > 56: # Seems that we have lost the Zigate communication

            Domoticz.Error("pingZigate - no Heartbeat with Zigate, try to reConnect")
            self.adminWidgets.updateNotificationWidget( Devices, 'Ping: Connection with Zigate Lost')
            #self.connectionState = 0
            #self.Ping['TimeStamp'] = int(time.time())
            #self.ZigateComm.re_conn()
            restartPluginViaDomoticzJsonApi( self )

        else:
            if ((self.Ping['Nb Ticks'] % 3) == 0):
                sendZigateCmd( self, "0014", "" ) # Request status
        return

    # If we are more than PING_CHECK_FREQ without any messages, let's check
    if  self.Ping['Nb Ticks'] <  ( PING_CHECK_FREQ  //  HEARTBEAT):
        self.connectionState = 1
        self.log.logging( 'Plugin', 'Debug', "pingZigate - We have receive a message less than %s sec  ago " %PING_CHECK_FREQ)
        return

    if 'Status' not in self.Ping:
        self.log.logging( 'Plugin', 'Log', "pingZigate - Unknown Status, Ticks: %s  Send a Ping" %self.Ping['Nb Ticks'])
        sendZigateCmd( self, "0014", "" ) # Request status
        self.Ping['Status'] = 'Sent'
        self.Ping['TimeStamp'] = int(time.time())
        return

    if self.Ping['Status'] == 'Receive':
        if self.connectionState == 0:
            #self.adminWidgets.updateStatusWidget( self, Devices, 'Ping: Reconnected after failure')
            self.log.logging( 'Plugin', 'Status', "pingZigate - SUCCESS - Reconnected after failure")
        self.log.logging( 'Plugin', 'Debug', "pingZigate - Status: %s Send a Ping, Ticks: %s" %(self.Ping['Status'], self.Ping['Nb Ticks']))
        sendZigateCmd( self, "0014", "" ) # Request status
        self.connectionState = 1
        self.Ping['Status'] = 'Sent'
        self.Ping['TimeStamp'] = int(time.time())
    else:
        Domoticz.Error("pingZigate - unknown status : %s" %self.Ping['Status'])

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onDeviceRemoved( Unit ):
    global _plugin
    _plugin.onDeviceRemoved( Unit )

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
            Domoticz.Log(  "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Log( "Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Log( "Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Log( "Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Log( "Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Log( "Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Log( "Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Log( "Device LastLevel: " + str(Devices[x].LastLevel))
        Domoticz.Log( "Device Options: " + str(Devices[x].Options))

def DumpHTTPResponseToLog(httpDict):
    if isinstance(httpDict, dict):
        Domoticz.Log("HTTP Details ("+str(len(httpDict))+"):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                Domoticz.Log("--->'"+x+" ("+str(len(httpDict[x]))+"):")
                for y in httpDict[x]:
                    Domoticz.Log("------->'" + y + "':'" + str(httpDict[x][y]) + "'")
            else:
                Domoticz.Log("--->'" + x + "':'" + str(httpDict[x]) + "'")
