#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

"""
<plugin key="Zigate" name="Zigate plugin" author="zaraki673 & pipiche38" version="beta-4.3" wikilink="https://www.domoticz.com/wiki/Zigate" externallink="https://github.com/sasu-drooz/Domoticz-Zigate/wiki">
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
                <li> Model USB or PI:</li>
            <ul style="list-style-type:square">
                <li> Serial Port: this is the serial port where your USB Zigate is connected. (The plugin will provide you the list of possible ports)</li>
                </ul>
            <li> Software Reset: This allow you to do a soft reset of the Zigate (no lost of data). Can be use if have change the Channel number in PluginConf.txt</li>
                <li> Rescan for Group Membership. In case you have added a new device, or remove some, you might want to have the plugin re-scanning the all devices for Group membership.</li>
            <li> Permit join time: This is the time you want to allow the Zigate to accept new Hardware. Please consider also to set Accept New Hardware in Domoticz settings. </li>
            <li> Erase Persistent Data: This will erase the Zigate memory and you will delete all pairing information. After that you'll have to re-pair each devices. This is not removing any data from Domoticz nor the plugin database.</li>
    </ul>
    <h3> Support </h3>
    Please use first the Domoticz forums in order to qualify your issue. Select the ZigBee or Zigate topic.
    </description>
    <params>
        <param field="Mode1" label="Zigate Model" width="75px">
            <options>
                <option label="USB" value="USB" default="true" />
                <option label="PI" value="PI" />
                <option label="Wifi" value="Wifi"/>
                <option label="None" value="None"/>
            </options>
        </param>
        <param field="Address" label="IP" width="150px" required="true" default="0.0.0.0"/>
        <param field="Port" label="Port" width="150px" required="true" default="9999"/>
        <param field="SerialPort" label="Serial Port" width="150px" required="true" default="/dev/ttyUSB0"/>
        <param field="Mode4" label="Software Reset" width="75px" required="true" default="False" >
            <options>
                <option label="True" value="True"/>
                <option label="False" value="False" default="true" />
            </options>
        </param>
        <param field="Mode5" label="Rescann for group membership" width="75px" required="true" default="False" >
            <options>
                <option label="True" value="True"/>
                <option label="False" value="False" default="true" />
            </options>
        </param>
        <param field="Mode2" label="Permit join time on start (0 disable join; 1-254 up to 254 sec ; 255 enable join all the time) " width="75px" required="true" default="254" />

        <param field="Mode3" label="Erase Persistent Data ( !!! full devices setup need !!! ) " width="75px">
            <options>
                <option label="True" value="True"/>
                <option label="False" value="False" default="true" />
            </options>
        </param>
        <param field="Mode6" label="Verbors and Debuging" width="150px">
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
import binascii
import time
import struct
import json
import queue
import sys

from Modules.tools import removeDeviceInList
from Modules.output import sendZigateCmd, removeZigateDevice, ZigatePermitToJoin, start_Zigate, setExtendedPANID
from Modules.input import ZigateRead
from Modules.heartbeat import processListOfDevices
from Modules.database import importDeviceConf, LoadDeviceList, checkListOfDevice2Devices, checkListOfDevice2Devices, WriteDeviceList
from Modules.domoticz import ResetDevice
from Modules.command import mgtCommand
from Modules.LQI import LQIdiscovery
from Modules.consts import HEARTBEAT, CERTIFICATION, MAX_LOAD_ZIGATE
from Modules.txPower import set_TxPower

from Classes.APS import APSManagement
from Classes.IAS import IAS_Zone_Management
from Classes.PluginConf import PluginConf
from Classes.Transport import ZigateTransport
from Classes.TransportStats import TransportStatistics
from Classes.GroupMgt import GroupsManagement
from Classes.AdminWidgets import AdminWidgets
from Classes.OTA import OTAManagement

# from Classes.WebServer import WebServer

class BasePlugin:
    enabled = False

    def __init__(self):
        self.ListOfDevices = {}  # {DevicesAddresse : { status : status_de_detection, data : {ep list ou autres en fonctions du status}}, DevicesAddresse : ...}
        self.DiscoveryDevices = {}
        self.IEEE2NWK = {}
        self.LQI = {}
        self.zigatedata = {}

        self.ZigateComm = None
        self.transport = None         # USB or Wifi
        self._ReqRcv = bytearray()
        self.permitTojoin = {}
        self.permitTojoin['duration'] = 0
        self.permitTojoin['Starttime'] = 0
        self.groupmgt = None
        self.groupmgt_NotStarted = True
        self.CommiSSionning = False    # This flag is raised when a Device Annocement is receive, in order to give priority to commissioning

        self.APS = None

        self.busy = False    # This flag is raised when a Device Annocement is receive, in order to give priority to commissioning
        self.homedirectory = None
        self.HardwareID = None
        self.Key = None
        self.DomoticzVersion = None
        self.StartupFolder = None
        self.domoticzdb_DeviceStatus = None      # Object allowing direct access to Domoticz DB DeviceSatus
        self.domoticzdb_Hardware = None         # Object allowing direct access to Domoticz DB Hardware
        self.adminWidgets = None   # Manage AdminWidgets object
        self.DeviceListName = None
        self.pluginconf = None     # PlugConf object / all configuration parameters
        self.pluginParameters = None

        self.OTA = None

        self.Ping = {}
        self.connectionState = None
        self.LQISource = None
        self.initdone = None
        self.statistics = None
        self.iaszonemgt = None      # Object to manage IAS Zone
        self.HBcount = 0
        self.HeartbeatCount = 0
        self.currentChannel = None  # Curent Channel. Set in Decode8009/Decode8024
        self.ZigateIEEE = None       # Zigate IEEE. Set in CDecode8009/Decode8024
        self.ZigateNWKID = None       # Zigate NWKID. Set in CDecode8009/Decode8024
        self.FirmwareVersion = None
        self.FirmwareMajorVersion = None
        self.mainpowerSQN = None    # Tracking main Powered SQN
        self.ForceCreationDevice = None   # 

        self.DomoticzMajor = None
        self.DomoticzMinor = None

        return

    def onStart(self):

        Domoticz.Status("Zigate plugin beta-4.3.0 started")
        self.pluginParameters = Parameters

        Domoticz.Log("Debug: %s" %int(Parameters["Mode6"]))
        if Parameters["Mode6"] != "0":
            Domoticz.Debugging(int(Parameters["Mode6"]))
            DumpConfigToLog()

        self.busy = True
        Domoticz.Status("Python Version - %s" %sys.version)
        assert sys.version_info >= (3, 4)

        Domoticz.Status("Switching Hearbeat to %s s interval" %HEARTBEAT)
        Domoticz.Heartbeat( HEARTBEAT )

        Domoticz.Status("DomoticzVersion: %s" %Parameters["DomoticzVersion"])
        Domoticz.Status("DomoticzHash: %s" %Parameters["DomoticzHash"])
        Domoticz.Status("DomoticzBuildTime: %s" %Parameters["DomoticzBuildTime"])
        self.DomoticzVersion = Parameters["DomoticzVersion"]
        self.homedirectory = Parameters["HomeFolder"]
        self.HardwareID = (Parameters["HardwareID"])
        self.Key = (Parameters["Key"])
        self.transport = Parameters["Mode1"]

        # Import PluginConf.txt
        major, minor = Parameters["DomoticzVersion"].split('.')
        self.DomoticzMajor = int(major)
        self.DomoticzMinor = int(minor)
        if self.DomoticzMajor > 4 or ( self.DomoticzMajor == 4 and self.DomoticzMinor >= 10355):
            # This is done here and not global, as on Domoticz V4.9700 it is not compatible with Threaded modules
            from Classes.DomoticzDB import DomoticzDB_DeviceStatus, DomoticzDB_Hardware, DomoticzDB_Preferences

            Domoticz.Debug("Startup Folder: %s" %Parameters["StartupFolder"])
            Domoticz.Debug("Home Folder: %s" %Parameters["HomeFolder"])
            Domoticz.Debug("User Data Folder: %s" %Parameters["UserDataFolder"])
            Domoticz.Debug("Web Root Folder: %s" %Parameters["WebRoot"])
            Domoticz.Debug("Database: %s" %Parameters["Database"])
            self.StartupFolder = Parameters["StartupFolder"]
            _dbfilename = Parameters["Database"]
            Domoticz.Status("Opening DomoticzDB in raw")
            Domoticz.Debug("   - DeviceStatus table")
            self.domoticzdb_DeviceStatus = DomoticzDB_DeviceStatus( _dbfilename, self.HardwareID  )
            Domoticz.Debug("   - Hardware table")
            self.domoticzdb_Hardware = DomoticzDB_Hardware( _dbfilename, self.HardwareID  )
        else:
            Domoticz.Status("The current Domoticz version doesn't support the plugin to enable a number of features")
            Domoticz.Status(" switching to Domoticz V 4.10355 and above would help")

        Domoticz.Status("load PluginConf" )
        self.pluginconf = PluginConf(Parameters["HomeFolder"], self.HardwareID)

        # Create the adminStatusWidget if needed
        self.adminWidgets = AdminWidgets( self.pluginconf, Devices, self.ListOfDevices, self.HardwareID )
        self.adminWidgets.updateStatusWidget( Devices, 'Startup')
        
        self.DeviceListName = "DeviceList-" + str(Parameters['HardwareID']) + ".txt"
        Domoticz.Status("Plugin Database: %s" %self.DeviceListName)

        if  self.pluginconf.pluginConf['allowStoreDiscoveryFrames'] == 1 :
            self.DiscoveryDevices = {}

        # Initialise APS Object
        if self.pluginconf.pluginConf['enableAPSFailureLoging'] or self.pluginconf.pluginConf['enableAPSFailureReporting']:
            self.APS = APSManagement( self.ListOfDevices , Devices, self.pluginconf)

        #Import DeviceConf.txt
        importDeviceConf( self ) 

        if type(self.DeviceConf) is not dict:
            Domoticz.Error("DeviceConf initialisatio failure!!! %s" %type(self.DeviceConf))
            return

        #Import DeviceList.txt Filename is : DeviceListName
        Domoticz.Status("load ListOfDevice" )
        if LoadDeviceList( self ) == 'Failed' :
            Domoticz.Error("Something wennt wrong during the import of Load of Devices ...")
            Domoticz.Error("Please cross-check your log ... You must be on V3 of the DeviceList and all DeviceID in Domoticz converted to IEEE")
            return            
        
        Domoticz.Debug("ListOfDevices : " )
        for e in self.ListOfDevices.items(): Domoticz.Debug(" "+str(e))
        Domoticz.Debug("IEEE2NWK      : " )
        for e in self.IEEE2NWK.items(): Domoticz.Debug("  "+str(e))

        # Check proper match against Domoticz Devices
        checkListOfDevice2Devices( self, Devices )

        Domoticz.Debug("ListOfDevices after checkListOfDevice2Devices: " +str(self.ListOfDevices) )
        Domoticz.Debug("IEEE2NWK after checkListOfDevice2Devices     : " +str(self.IEEE2NWK) )

        # Create Statistics object
        self.statistics = TransportStatistics(self.pluginconf)

        # Check update for web GUI
        # CheckForUpdate( self )

        # Connect to Zigate only when all initialisation are properly done.
        if  self.transport == "USB":
            self.ZigateComm = ZigateTransport( self.transport, self.statistics, self.APS, self.pluginconf, self.processFrame,\
                    serialPort=Parameters["SerialPort"] )
        elif  self.transport == "PI":
            Domoticz.Status("Switch PiZigate in RUN mode")
            import os

            GPIO_CMD = '/usr/bin/gpio'

            if os.path.isfile( GPIO_CMD ):
                Domoticz.Log(".")
                os.system( GPIO_CMD + " mode 2 out")
                Domoticz.Log(".")
                os.system( GPIO_CMD + " write 2 1")
                Domoticz.Log(".")
                os.system( GPIO_CMD + " mode 0 down")
                Domoticz.Log(".")
                os.system( GPIO_CMD + " mode 0 up")
            else:
                Domoticz.Error("%s command missing. Make sure to install wiringPi package" %GPIO_CMD)

            self.ZigateComm = ZigateTransport( self.transport, self.statistics, self.APS, self.pluginconf, self.processFrame,\
                    serialPort=Parameters["SerialPort"] )
        elif  self.transport == "Wifi":
            self.ZigateComm = ZigateTransport( self.transport, self.statistics, self.APS, self.pluginconf, self.processFrame,\
                    wifiAddress= Parameters["Address"], wifiPort=Parameters["Port"] )
        elif self.transport == "None":
            Domoticz.Status("Transport mode set to None, no communication.")
            return
        else :
            Domoticz.Error("Unknown Transport comunication protocol : "+str(self.transport) )
            return

        Domoticz.Debug("Establish Zigate connection" )
        self.ZigateComm.openConn()
        self.busy = False
        return

    def onStop(self):
        Domoticz.Status("onStop called")

        if self.domoticzdb_DeviceStatus:
            self.domoticzdb_DeviceStatus.closeDB()

        if self.domoticzdb_Hardware:
            self.domoticzdb_Hardware.closeDB()
 
        major, minor = Parameters["DomoticzVersion"].split('.')
        major = int(major)
        minor = int(minor)
        if major > 4 or ( major == 4 and minor >= 10355):
            import threading
            for thread in threading.enumerate():
                if (thread.name != threading.current_thread().name):
                    Domoticz.Log("'"+thread.name+"' is running, it must be shutdown otherwise Domoticz will abort on plugin exit.")

        #self.ZigateComm.closeConn()
        WriteDeviceList(self, 0)
        self.statistics.printSummary()
        self.statistics.writeReport()
        self.adminWidgets.updateStatusWidget( Devices, 'No Communication')

    def onDeviceRemoved( self, Unit ) :
        Domoticz.Debug("onDeviceRemoved called" )
        # Let's check if this is End Node, or Group related.
        if Devices[Unit].DeviceID in self.IEEE2NWK:
            # Command belongs to a end node
            Domoticz.Log("onDeviceRemoved - removing End Device")
            removeDeviceInList( self, Devices, Devices[Unit].DeviceID , Unit)

            if self.pluginconf.pluginConf['allowRemoveZigateDevice'] == 1:
                IEEE = Devices[Unit].DeviceID
                removeZigateDevice( self, IEEE )
                Domoticz.Log("onDeviceRemoved - removing Device %s -> %s in Zigate" %(Devices[Unit].Name, IEEE))

            Domoticz.Debug("ListOfDevices :After REMOVE " + str(self.ListOfDevices))
            return

        if self.pluginconf.pluginConf['enablegroupmanagement'] and self.groupmgt:
            if Devices[Unit].DeviceID in self.groupmgt.ListOfGroups:
                Domoticz.Log("onDeviceRemoved - removing Group of Devices")
                # Command belongs to a Zigate group
                self.groupmgt.processRemoveGroup( Unit, Devices[Unit].DeviceID )

        # We might evaluate teh removal of the physical device from Zigate.
        # Could be done if a Flag is enabled in the PluginConf.txt.
        
    def onConnect(self, Connection, Status, Description):

        Domoticz.Debug("onConnect called with status: %s" %Status)
        def decodeConnection( connection ):

            decoded = {}
            for i in connection.strip().split(','):
                label, value = i.split(': ')
                label = label.strip().strip("'")
                value = value.strip().strip("'")
                decoded[label] = value
            return decoded

        Domoticz.Debug("onConnect %s called with status: %s and Desc: %s" %( Connection, Status, Description))

        decodedConnection = decodeConnection ( str(Connection) )
        if 'Protocol' in decodedConnection:
            if decodedConnection['Protocol'] in ( 'HTTP', 'HTTPS') : # We assumed that is the Web Server 
                if self.pluginconf.pluginConf['enableWebServer']:
                    self.webserver.onConnect( Connection, Status, Description)
                return

        self.busy = True

        if Status != 0:
            Domoticz.Error("Failed to connect ("+str(Status)+")")
            Domoticz.Debug("Failed to connect ("+str(Status)+") with error: "+Description)
            self.connectionState = 0
            self.ZigateComm.reConn()
            self.adminWidgets.updateStatusWidget( Devices, 'No Communication')
            return

        Domoticz.Debug("Connected successfully")
        if self.connectionState is None:
            self.adminWidgets.updateStatusWidget( Devices, 'Starting the plugin up')
        elif self.connectionState == 0:
            Domoticz.Status("Reconnected after failure")
            self.adminWidgets.updateStatusWidget( Devices, 'Reconnected after failure')

        self.connectionState = 1
        self.Ping['Status'] = None
        self.Ping['TimeStamp'] = None
        self.Ping['Permit'] = None
        self.Ping['Nb Ticks'] = 1

        sendZigateCmd(self, "0010", "") # Get Firmware version

        if Parameters["Mode3"] == "True": # Erase PDM
            if self.domoticzdb_Hardware:
                self.domoticzdb_Hardware.disableErasePDM()
            Domoticz.Status("Erase Zigate PDM")
            sendZigateCmd(self, "0012", "")
            if self.pluginconf.pluginConf['extendedPANID'] is not None:
                Domoticz.Status("ZigateConf - Setting extPANID : 0x%016x" %( self.pluginconf.pluginConf['extendedPANID']) )
                setExtendedPANID(self, self.pluginconf.pluginConf['extendedPANID'])

            start_Zigate( self )

        if Parameters["Mode4"] == "True": # Software Non-Factory Reseet
            Domoticz.Status("Software reset")
            sendZigateCmd(self, "0011", "" ) # Software Reset
            start_Zigate( self )

        if Parameters['Mode2'].isdigit(): # Permit to join
            self.permitToJoin = int(Parameters['Mode2'])
            if self.permitToJoin != 0:
                Domoticz.Log("Configure Permit To Join")
                self.Ping['Permit'] = None
                ZigatePermitToJoin(self, self.permitToJoin)
                if Settings["AcceptNewHardware"] != "1":
                    Domoticz.Error("Pairing devices will most-likely failed, because Accept New Hardware in Domoticz settings is disabled!")
            else:
                self.permitToJoin = 0
                self.Ping['Permit'] = None
                ZigatePermitToJoin(self, 0)

        sendZigateCmd(self, "0009", "") # Request Network state
        sendZigateCmd(self, "0015", "") # Request List of Active Device

        # Create IAS Zone object
        self.iaszonemgt = IAS_Zone_Management( self.ZigateComm , self.ListOfDevices)

        if (self.pluginconf.pluginConf)['logLQI'] != 0 :
            LQIdiscovery( self ) 

        self.busy = False

        return True

    def onMessage(self, Connection, Data):
        #Domoticz.Debug("onMessage called on Connection " + " Data = '" +str(Data) + "'")
        if isinstance(Data, dict):
            if self.pluginconf.pluginConf['enableWebServer']:
                self.webserver.onMessage( Connection, Data)
            return

        if len(Data) == 0:
            Domoticz.Log("onMessage - empty message received on %s" %Connection)

        self.Ping['Nb Ticks'] = 0
        self.ZigateComm.onMessage(Data)

    def processFrame( self, Data ):

        ZigateRead( self, Devices, Data )

    def onCommand(self, Unit, Command, Level, Color):

        Domoticz.Debug("onCommand - unit: %s, command: %s, level: %s, color: %s" %(Unit, Command, Level, Color))

        # Let's check if this is End Node, or Group related.
        if Devices[Unit].DeviceID in self.IEEE2NWK:
            # Command belongs to a end node
            mgtCommand( self, Devices, Unit, Command, Level, Color )

        elif self.pluginconf.pluginConf['enablegroupmanagement'] and self.groupmgt:
            #if Devices[Unit].DeviceID in self.groupmgt.ListOfGroups:
            #    # Command belongs to a Zigate group
            Domoticz.Log("Command: %s/%s/%s to Group: %s" %(Command,Level,Color, Devices[Unit].DeviceID))
            self.groupmgt.processCommand( Unit, Devices[Unit].DeviceID, Command, Level, Color )

        elif Devices[Unit].DeviceID.find('Zigate-01-') != -1:
            Domoticz.Log("onCommand - Command adminWidget: %s " %Command)
            self.adminWidgets.handleCommand( self, Command)

        else:
            Domoticz.Error("onCommand - Unknown device or GrpMgr not enabled %s, unit %s , id %s" \
                    %(Devices[Unit].Name, Unit, Devices[Unit].DeviceID))

        return

    def onDisconnect(self, Connection):

        Domoticz.Debug("onDisconnect: %s" %Connection)
        def decodeConnection( connection ):

            decoded = {}
            for i in connection.strip().split(','):
                label, value = i.split(': ')
                label = label.strip().strip("'")
                value = value.strip().strip("'")
                decoded[label] = value
            return decoded

        decodedConnection = decodeConnection ( str(Connection) )

        if 'Protocol' in decodedConnection:
            if decodedConnection['Protocol'] in ( 'HTTP', 'HTTPS') : # We assumed that is the Web Server 
                if self.pluginconf.pluginConf['enableWebServer']:
                    self.webserver.onDisconnect( Connection )
                return

        self.connectionState = 0
        self.adminWidgets.updateStatusWidget( Devices, 'Plugin stop')
        Domoticz.Status("onDisconnect called")

    def onHeartbeat(self):
        
        busy_ = False
        Domoticz.Debug("onHeartbeat - busy = %s" %self.busy)

        self.HeartbeatCount += 1

        # Ig ZigateIEEE not known, try to get it during the first 10 HB
        if self.ZigateIEEE is None and self.HeartbeatCount in ( 2, 4) and self.transport != 'None':
            sendZigateCmd(self, "0009","")
        elif self.ZigateIEEE is None and self.HeartbeatCount == 5 and self.transport != 'None':
            start_Zigate( self )
            return

        if self.FirmwareVersion is None and self.transport != 'None':
            Domoticz.Log("FirmwareVersion not ready")
            if self.HeartbeatCount in ( 4, 8 ): # Try to get Firmware version once more time.
                Domoticz.Log("Try to get Firmware version once more %s" %self.HeartbeatCount)
                sendZigateCmd(self, "0010", "") # Get Firmware version
            elif self.HeartbeatCount > 10:
                Domoticz.Error("Plugin is not started ...")
                Domoticz.Error(" - Communication issue with the Zigate")
                Domoticz.Error(" - restart once the plugin, and if this remain the same")
                Domoticz.Error(" - unplug/plug the zigate")
            return


        if not self.initdone:
            # We can now do what must be done when we known the Firmware version
            self.initdone = True

            # Ceck Firmware version
            if self.FirmwareVersion and self.FirmwareVersion.lower() < '030f':
                Domoticz.Status("You are not on the latest firmware version, please consider to upgrade")

            if self.FirmwareVersion and self.FirmwareVersion.lower() == '030e':
                Domoticz.Status("You are not on the latest firmware version, This version is known to have problem loosing Xiaomi devices, please consider to upgrae")

            if self.FirmwareVersion and self.FirmwareVersion.lower() == '030f' and self.FirmwareMajorVersion == '0002':
                Domoticz.Error("You are not running on the Official 3.0f version (it was a pre-3.0f)")
        
            if self.FirmwareVersion and self.FirmwareVersion.lower() > '030f':
                Domoticz.Error("Firmware %s is not yet supported" %self.FirmwareVersion.lower())

            if self.FirmwareVersion and self.FirmwareVersion.lower() >= '030f' and self.FirmwareMajorVersion >= '0003' and self.transport != 'None':
                if self.pluginconf.pluginConf['blueLedOff']:
                    Domoticz.Log("Switch Blue Led off")
                    sendZigateCmd(self, "0018","00")

                if self.pluginconf.pluginConf['TXpower_set'] and self.transport != 'None':
                    set_TxPower( self, self.pluginconf.pluginConf['TXpower_set'] )

                if self.pluginconf.pluginConf['Certification'] in CERTIFICATION and self.transport != 'None':
                    Domoticz.Log("Zigate set to Certification : %s" %CERTIFICATION[self.pluginconf.pluginConf['Certification']])
                    sendZigateCmd(self, '0019', '%02x' %self.pluginconf.pluginConf['Certification'])

                if self.groupmgt_NotStarted and self.pluginconf.pluginConf['enablegroupmanagement']:
                    Domoticz.Status("Start Group Management")
                    self.groupmgt = GroupsManagement( self.pluginconf, self.adminWidgets, self.ZigateComm, Parameters["HomeFolder"], 
                            self.HardwareID, Parameters["Mode5"], Devices, self.ListOfDevices, self.IEEE2NWK )
                    self.groupmgt_NotStarted = False

            # In case we have Transport = None , let's check if we have to active Group management or not.
            if self.transport == 'None' and self.groupmgt_NotStarted and self.pluginconf.pluginConf['enablegroupmanagement']:
                    Domoticz.Status("Start Group Management")
                    self.groupmgt = GroupsManagement( self.pluginconf, self.adminWidgets, self.ZigateComm, Parameters["HomeFolder"], 
                            self.HardwareID, Parameters["Mode5"], Devices, self.ListOfDevices, self.IEEE2NWK )
                    self.groupmgt._load_GroupList()
                    self.groupmgt_NotStarted = False


            if self.pluginconf.pluginConf['enableWebServer']:
                from Classes.WebServer import WebServer
                Domoticz.Status("Start Web Server connection")
                self.webserver = WebServer( self.pluginParameters, self.pluginconf, self.statistics, self.adminWidgets, self.ZigateComm, Parameters["HomeFolder"], \
                                        self.HardwareID, self.groupmgt, Devices, self.ListOfDevices, self.IEEE2NWK , self.permitTojoin )

            Domoticz.Status("Plugin with Zigate firmware %s correctly initialized" %self.FirmwareVersion)
            if self.pluginconf.pluginConf['allowOTA']:
                self.OTA = OTAManagement( self.pluginconf, self.adminWidgets, self.ZigateComm, Parameters["HomeFolder"],
                            self.HardwareID, Devices, self.ListOfDevices, self.IEEE2NWK)

            if self.FirmwareVersion and self.FirmwareVersion >= "030d":
                if (self.HeartbeatCount % ( 3600 // HEARTBEAT ) ) == 0  and self.transport != 'None':
                    sendZigateCmd(self, "0009","")

        if self.transport == 'None':
            return
        # Memorize the size of Devices. This is will allow to trigger a backup of live data to file, if the size change.
        prevLenDevices = len(Devices)

        # Manage all entries in  ListOfDevices (existing and up-coming devices)
        processListOfDevices( self , Devices )

        # IAS Zone Management
        self.iaszonemgt.IAS_heartbeat( )

        # Reset Motion sensors
        ResetDevice( self, Devices, "Motion",5)

        # Write the ListOfDevice in HBcount % 200 ( 3' ) or immediatly if we have remove or added a Device
        if len(Devices) != prevLenDevices:
            Domoticz.Debug("Devices size has changed , let's write ListOfDevices on disk")
            WriteDeviceList(self, 0)       # write immediatly
        else:
            WriteDeviceList(self, ( 90 * 5) )

        if self.CommiSSionning:
            self.adminWidgets.updateStatusWidget( Devices, 'Enrollment')
            return

        # Group Management
        if self.groupmgt: 
            self.groupmgt.hearbeatGroupMgt()
            if self.groupmgt.stillWIP:
                busy_ = True

        # OTA upgrade
        if self.OTA:
            self.OTA.heartbeat()
            
        # Hearbeat - Ping Zigate every minute to check connectivity
        # If fails then try to reConnect
        if self.pluginconf.pluginConf['Ping']:
            pingZigate( self )
            self.Ping['Nb Ticks'] += 1

        if len(self.ZigateComm._normalQueue) > MAX_LOAD_ZIGATE:
            busy_ = True

        if busy_:
            self.adminWidgets.updateStatusWidget( Devices, 'Busy')
        elif not self.connectionState:
            self.adminWidgets.updateStatusWidget( Devices, 'No Communication')
        else:
            self.adminWidgets.updateStatusWidget( Devices, 'Ready')

        self.busy = busy_
        return True


def pingZigate( self ):

    """
    Ping Zigate to check if it is alive.
    Do it only if no messages have been received during the last period

    'Nb Ticks' is set to 0 every time a message is received from Zigate
    'Nb Ticks' is incremented at every heartbeat
    """

    # Frequency is set to below 4' as regards to the TCP timeout with Wifi-Zigate
    PING_CHECK_FREQ =  240

    Domoticz.Debug("pingZigate - [%s] Nb Ticks: %s Status: %s TimeStamp: %s" \
            %(self.HeartbeatCount, self.Ping['Nb Ticks'], self.Ping['Status'], self.Ping['TimeStamp']))

    if self.Ping['Nb Ticks'] == 0: # We have recently received a message, Zigate is up and running
        self.Ping['Status'] = 'Receive'
        self.connectionState = 1
        Domoticz.Debug("pingZigate - We have receive a message in the cycle ")
        return                     # Most likely between the cycle.

    if self.Ping['Status'] == 'Sent':
        delta = int(time.time()) - self.Ping['TimeStamp']
        Domoticz.Log("pingZigate - WARNING: Ping sent but no response yet from Zigate. Status: %s  - Ping: %s sec" %(self.Ping['Status'], delta))
        if delta > 56: # Seems that we have lost the Zigate communication
            Domoticz.Error("pingZigate - no Heartbeat with Zigate, try to reConnect")
            self.adminWidgets.updateNotificationWidget( Devices, 'Ping: Connection with Zigate Lost')
            self.connectionState = 0
            self.Ping['TimeStamp'] = int(time.time())
            self.ZigateComm.reConn()
        else:
            if ((self.Ping['Nb Ticks'] % 3) == 0):
                sendZigateCmd( self, "0014", "" ) # Request status
        return

    # If we are more than PING_CHECK_FREQ without any messages, let's check
    if  self.Ping['Nb Ticks'] <  ( PING_CHECK_FREQ  //  HEARTBEAT):
        self.connectionState = 1
        Domoticz.Debug("pingZigate - We have receive a message less than %s sec  ago " %PING_CHECK_FREQ)
        return

    if 'Status' not in self.Ping:
        Domoticz.Log("pingZigate - Unknown Status, Ticks: %s  Send a Ping" %self.Ping['Nb Ticks'])
        sendZigateCmd( self, "0014", "" ) # Request status
        self.Ping['Status'] = 'Sent'
        self.Ping['TimeStamp'] = int(time.time())
        return

    if self.Ping['Status'] == 'Receive':
        if self.connectionState == 0:
        #    self.adminWidgets.updateStatusWidget( self, Devices, 'Ping: Reconnected after failure')
            Domoticz.Status("pingZigate - SUCCESS - Reconnected after failure")
        Domoticz.Debug("pingZigate - Status: %s Send a Ping, Ticks: %s" %(self.Ping['Status'], self.Ping['Nb Ticks']))
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
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
        Domoticz.Debug("Device Options: " + str(Devices[x].Options))
    return


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
