#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

"""
<plugin key="Zigate" name="Zigate plugin" author="zaraki673 & pipiche38" version="pre-4.1" wikilink="http://www.domoticz.com/wiki/Zigate" externallink="https://github.com/sasu-drooz/Domoticz-Zigate/wiki">
    <params>
        <param field="Mode1" label="Model" width="75px">
            <options>
                <option label="USB" value="USB" default="true" />
                <option label="Wifi" value="Wifi"/>
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
        <param field="Mode3" label="Erase Persistent Data ( !!! full devices setup need !!! ) " width="75px">
            <options>
                <option label="True" value="True"/>
                <option label="False" value="False" default="true" />
            </options>
        </param>
        <param field="Mode6" label="Verbors and Debuging" width="150px">
            <options>
                        <option label="None" value="0"  default="true"/>
                        <option label="Verbose" value="2"/>
                        <option label="Domoticz Framework - Basic" value="62"/>
                        <option label="Domoticz Framework - Basic+Messages" value="126"/>
                        <option label="Domoticz Framework - Connections Only" value="16"/>
                        <option label="Domoticz Framework - Connections+Queue" value="144"/>
                        <option label="Domoticz Framework - All" value="-1"/>
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
from Modules.output import sendZigateCmd, ZigateConf, ZigateConf_light, removeZigateDevice, ZigatePermitToJoin
from Modules.input import ZigateRead
from Modules.heartbeat import processListOfDevices
from Modules.database import importDeviceConf, LoadDeviceList, checkListOfDevice2Devices, checkListOfDevice2Devices, WriteDeviceList
from Modules.domoticz import ResetDevice
from Modules.command import mgtCommand
from Modules.LQI import LQIdiscovery
from Modules.consts import HEARTBEAT, CERTIFICATION

from Classes.IAS import IAS_Zone_Management
from Classes.PluginConf import PluginConf
from Classes.Transport import ZigateTransport
from Classes.TransportStats import TransportStatistics
from Classes.GroupMgt import GroupsManagement
from Classes.AdminWidgets import AdminWidgets
from Classes.DomoticzDB import DomoticzDB_DeviceStatus, DomoticzDB_Hardware, DomoticzDB_Preferences

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
        self.permitTojoin = None
        self.groupmgt = None
        self.groupmgt_NotStarted = True
        self.CommiSSionning = False    # This flag is raised when a Device Annocement is receive, in order to give priority to commissioning

        self.busy = False    # This flag is raised when a Device Annocement is receive, in order to give priority to commissioning
        self.homedirectory = None
        self.HardwareID = None
        self.Key = None
        self.DomoticzVersion = None
        self.StartupFolder = None
        self.domoticzdb_DeviceStatus = None      # Object allowing direct access to Domoticz DB DeviceSatus
        self.domoticzdb_Hardware = None         # Object allowing direct access to Domoticz DB Hardware
        self.domoticzdb_Preferences = None         # Object allowing direct access to Domoticz DB Preferences
        self.adminWidgets = None   # Manage AdminWidgets object
        self.DeviceListName = None
        self.pluginconf = None     # PlugConf object / all configuration parameters

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

        return

    def onStart(self):

        Domoticz.Status("Zigate plugin (pre 4.1.x) started")

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
        major = int(major)
        minor = int(minor)
        if major > 4 or ( major == 4 and minor >= 10355):
            Domoticz.Status("Startup Folder: %s" %Parameters["StartupFolder"])
            Domoticz.Status("Home Folder: %s" %Parameters["HomeFolder"])
            Domoticz.Status("User Data Folder: %s" %Parameters["UserDataFolder"])
            Domoticz.Status("Web Root Folder: %s" %Parameters["WebRoot"])
            Domoticz.Status("Database: %s" %Parameters["Database"])
            self.StartupFolder = Parameters["StartupFolder"]
            _dbfilename = Parameters["Database"]
        else:
            Domoticz.Status("The current Domoticz version doesn't support the plugin to enable a number of features")
            Domoticz.Status(" switching to Domoticz V 4.10355 and above would help")
            _dbfilename = Parameters["HomeFolder"] + '../../domoticz.db'

        Domoticz.Status("Opening DomoticzDB in raw")
        Domoticz.Status("   - DeviceStatus table")
        self.domoticzdb_DeviceStatus = DomoticzDB_DeviceStatus( _dbfilename, self.HardwareID  )
        Domoticz.Status("   - Hardware table")
        self.domoticzdb_Hardware = DomoticzDB_Hardware( _dbfilename, self.HardwareID  )
        Domoticz.Status("   - Preference table")
        self.domoticzdb_Preferences = DomoticzDB_Preferences( _dbfilename  )
        Domoticz.Status("   - Preference table")
        self.domoticzdb_Preferences = DomoticzDB_Preferences( _dbfilename )

        Domoticz.Status("load PluginConf" )
        self.pluginconf = PluginConf(Parameters["HomeFolder"], self.HardwareID)

        # Create the adminStatusWidget if needed
        self.adminWidgets = AdminWidgets( self.pluginconf, Devices, self.ListOfDevices, self.HardwareID )
        self.adminWidgets.updateStatusWidget( Devices, 'Startup')
        
        self.DeviceListName = "DeviceList-" + str(Parameters['HardwareID']) + ".txt"
        Domoticz.Status("Plugin Database: %s" %self.DeviceListName)

        plugconf = self.pluginconf
        if  plugconf.allowStoreDiscoveryFrames == 1 :
            self.DiscoveryDevices = {}

        #Import DeviceConf.txt
        importDeviceConf( self ) 

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
        self.statistics = TransportStatistics()

        # Check update for web GUI
        # CheckForUpdate( self )

        # Connect to Zigate only when all initialisation are properly done.
        if  self.transport == "USB":
            self.ZigateComm = ZigateTransport( self.transport, self.statistics, self.pluginconf, self.processFrame,\
                    serialPort=Parameters["SerialPort"] )
        elif  self.transport == "Wifi":
            self.ZigateComm = ZigateTransport( self.transport, self.statistics, self.pluginconf, self.processFrame,\
                    wifiAddress= Parameters["Address"], wifiPort=Parameters["Port"] )
        else :
            Domoticz.Error("Unknown Transport comunication protocol : "+str(self.transport) )
            return

        Domoticz.Debug("Establish Zigate connection" )
        self.ZigateComm.openConn()
        self.busy = False
        return

    def onStop(self):
        Domoticz.Status("onStop called")
        #self.ZigateComm.closeConn()
        WriteDeviceList(self, 0)
        self.statistics.printSummary()
        self.adminWidgets.updateStatusWidget( Devices, 'No Communication')

    def onDeviceRemoved( self, Unit ) :
        Domoticz.Status("onDeviceRemoved called" )
        # Let's check if this is End Node, or Group related.
        if Devices[Unit].DeviceID in self.IEEE2NWK:
            # Command belongs to a end node
            Domoticz.Log("onDeviceRemoved - removing End Device")
            removeDeviceInList( self, Devices, Devices[Unit].DeviceID , Unit)

            if self.pluginconf.allowRemoveZigateDevice == 1:
                IEEE = Devices[Unit].DeviceID
                removeZigateDevice( self, IEEE )
                Domoticz.Log("onDeviceRemoved - removing Device %s -> %s in Zigate" %(Devices[Unit].Name, IEEE))

            Domoticz.Debug("ListOfDevices :After REMOVE " + str(self.ListOfDevices))
            return

        if self.pluginconf.enablegroupmanagement and self.groupmgt:
            if Devices[Unit].DeviceID in self.groupmgt.ListOfGroups:
                Domoticz.Log("onDeviceRemoved - removing Group of Devices")
                # Command belongs to a Zigate group
                self.groupmgt.processRemoveGroup( Unit, Devices[Unit].DeviceID )

        # We might evaluate teh removal of the physical device from Zigate.
        # Could be done if a Flag is enabled in the PluginConf.txt.
        
    def onConnect(self, Connection, Status, Description):

        Domoticz.Debug("onConnect called with status: %s" %Status)
        self.busy = True

        if Status == 0:
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
            self.Ping['Rx Message'] = 1

            if Parameters["Mode3"] == "True":
                if self.domoticzdb_Hardware:
                    self.domoticzdb_Hardware.disableErasePDM()
                ################### ZiGate - ErasePD ##################
                Domoticz.Status("Erase Zigate PDM")
                sendZigateCmd(self, "0012", "")
                Domoticz.Status("Software reset")
                sendZigateCmd(self, "0011", "") # Software Reset
                ZigateConf(self)
            else :
                if Parameters["Mode4"] == "True":
                    Domoticz.Status("Software reset")
                    sendZigateCmd(self, "0011", "" ) # Software Reset
                    ZigateConf(self)
                else:
                    ZigateConf_light(self)
        else:
            Domoticz.Error("Failed to connect ("+str(Status)+")")
            Domoticz.Debug("Failed to connect ("+str(Status)+") with error: "+Description)
            self.connectionState = 0
            self.ZigateComm.reConn()
            self.adminWidgets.updateStatusWidget( Devices, 'No Communication')



        # Create IAS Zone object
        self.iaszonemgt = IAS_Zone_Management( self.ZigateComm , self.ListOfDevices)

        if (self.pluginconf).logLQI != 0 :
            LQIdiscovery( self ) 

        self.busy = False

        return True

    def onMessage(self, Connection, Data):
        #Domoticz.Debug("onMessage called on Connection " + " Data = '" +str(Data) + "'")
        self.Ping['Rx Message'] = 0
        self.ZigateComm.onMessage(Data)

    def processFrame( self, Data ):
        ZigateRead( self, Devices, Data )

    def onCommand(self, Unit, Command, Level, Color):

        if  not self.connectionState:
            Domoticz.Error("onCommand receive, but no connection to Zigate")
            return

        # Let's check if this is End Node, or Group related.
        if Devices[Unit].DeviceID in self.IEEE2NWK:
            # Command belongs to a end node
            mgtCommand( self, Devices, Unit, Command, Level, Color )

        elif self.pluginconf.enablegroupmanagement and self.groupmgt:
            #if Devices[Unit].DeviceID in self.groupmgt.ListOfGroups:
            #    # Command belongs to a Zigate group
            self.groupmgt.processCommand( Unit, Devices[Unit].DeviceID, Command, Level, Color )
            Domoticz.Log("Command: %s/%s/%s to Group: %s" %(Command,Level,Color, Devices[Unit].DeviceID))

        elif Devices[Unit].DeviceID.find('Zigate-01-'):
            Domoticz.Log("onCommand - Command adminWidget: %s " %Command)
            self.adminWidgets.handleCommand( self, Command)

    def onDisconnect(self, Connection):
        self.connectionState = 0
        self.adminWidgets.updateStatusWidget( Devices, 'Plugin stop')
        Domoticz.Status("onDisconnect called")

    def onHeartbeat(self):
        
        if not self.connectionState:
            Domoticz.Error("onHeartbeat receive, but no connection to Zigate")
            return

        self.HeartbeatCount += 1

        if self.FirmwareVersion is None:
            Domoticz.Log("FirmwareVersion not ready")
            if self.HeartbeatCount in ( 2, 6 ): # Try to get Firmware version once more time.
                Domoticz.Log("Try to get Firmware version once more %s" %self.HeartbeatCount)
                sendZigateCmd(self, "0010", "") # Get Firmware version
            return

        if not self.initdone:
            # We can now do what must be done when we known the Firmware version
            self.initdone = True

            if self.domoticzdb_Preferences:
                PermitToJoin = self.domoticzdb_Preferences.retreiveAcceptNewHardware()
                Domoticz.Debug("   - Permit to Join : %s" %PermitToJoin)
            else:
                Domoticz.Error("Unable to set Permit to Join. Unitialized object")
     
            # Ceck Firmware version
            if self.FirmwareVersion.lower() < '030f':
                Domoticz.Status("You are not on the latest firmware version, please consider to upgrade")

            if self.FirmwareVersion.lower() == '030e':
                Domoticz.Status("You are not on the latest firmware version, This version is known to have problem loosing Xiaomi devices, please consider to upgrae")

            if self.FirmwareVersion.lower() == '030f' and self.FirmwareMajorVersion == '0002':
                Domoticz.Status("You are not running on the Official 3.0f version (it was a pre-3.0f)")

            if self.FirmwareVersion.lower() >= '030f' and self.FirmwareMajorVersion >= '0003':
                if self.pluginconf.blueLedOff:
                    Domoticz.Status("Switch Blue Led off")
                    sendZigateCmd(self, "0018","00")

                if PermitToJoin:
                    Domoticz.Status("Enable Permit To Join")
                    self.Ping['Permit'] = None
                    ZigatePermitToJoin(self, True)
                else: 
                    Domoticz.Status("Disable Permit To Join")
                    self.Ping['Permit'] = None
                    ZigatePermitToJoin(self, False)

                if self.pluginconf.TXpower:
                    attr_tx_power = '%02x' %self.pluginconf.TXpower_set
                    sendZigateCmd(self, "0806", attr_tx_power)
                    Domoticz.Status("Zigate switch to Power Mode value: 0x%s" %attr_tx_power)

                if self.pluginconf.Certification in CERTIFICATION:
                    Domoticz.Status("Zigate set to Certification : %s" %CERTIFICATION[self.pluginconf.Certification])
                    sendZigateCmd(self, '0019', '%02x' %self.pluginconf.Certification)

                if self.groupmgt_NotStarted and self.pluginconf.enablegroupmanagement:
                    Domoticz.Status("Start Group Management")
                    self.groupmgt = GroupsManagement( self.pluginconf, self.adminWidgets, self.ZigateComm, Parameters["HomeFolder"], 
                        self.HardwareID, Devices, self.ListOfDevices, self.IEEE2NWK )
                    self.groupmgt_NotStarted = False

            Domoticz.Status("Plugin with Zigate firmware %s correctly initialized" %self.FirmwareVersion)

            if self.FirmwareVersion >= "030d":
                if (self.HeartbeatCount % ( 3600 // HEARTBEAT ) ) == 0 :
                    sendZigateCmd(self, "0009","")
        else:
            # Init done, let's do the recurring stuff

            if  ( self.HeartbeatCount % ( 300 // HEARTBEAT ) ) == 0:
                Domoticz.Debug("Check if we have enable Accept new Hardware Devices)")
                PermitToJoin = self.domoticzdb_Preferences.retreiveAcceptNewHardware()
                Domoticz.Debug("   - Permit to Join : %s , status is: %s" %(PermitToJoin, self.Ping['Permit']))
                if PermitToJoin and self.Ping['Permit'] == 'Off':
                    self.Ping['Permit'] = None
                    ZigatePermitToJoin(self, True)
                if not PermitToJoin and self.Ping['Permit'] == 'On':
                    self.Ping['Permit'] = None
                    ZigatePermitToJoin(self, False)

        # Ig ZigateIEEE not known, try to get it during the first 10 HB
        if self.ZigateIEEE is None and self.HeartbeatCount in ( 2, 4, 6, 8, 10):   
            sendZigateCmd(self, "0009","")

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

        busy_ = False
        # Group Management
        
        if self.groupmgt: 
            self.groupmgt.hearbeatGroupMgt()
            if self.groupmgt.stillWIP:
                busy_ = True
            
        if self.busy  or len(self.ZigateComm._normalQueue) > 3:
            busy_ = True

        # Hearbeat - Ping Zigate every minute to check connectivity
        # If fails then try to reConnect
        if self.pluginconf.Ping:
            if ( self.HeartbeatCount % ( (5 * 60) // HEARTBEAT)) == 0 :
                Domoticz.Debug("Ping")
                if self.Ping['Rx Message']: # 'Rx Message' is set to 0 when receiving a Message.
                                            # Looks like we didn't receive messages
                    if  self.Ping['Rx Message'] > ( 60 //  HEARTBEAT ):
                        Domoticz.Log("Ping - We didn't receive any messages since 60s")
                        # This is now about 1' or more that we didn't receive any messages.
                        # Let's try to ping Zigate in order to force a message
                        now = time.time()
                        if 'Status' in self.Ping:
                            if self.Ping['Status'] == 'Sent':
                                delta = now - self.Ping['TimeStamps']
                                Domoticz.Debug("processKnownDevices - Ping: %s" %delta)
                                if delta > 60: # Seems that we have lost the Zigate communication
                                    Domoticz.Log("Ping - no Heartbeat with Zigate")
                                    self.adminWidgets.updateNotificationWidget( Devices, 'Ping: Connection with Zigate Lost')
                                    self.connectionState = 0
                                    self.ZigateComm.reConn()
                                #else:
                                #    if self.connectionState == 0:
                                #        self.adminWidgets.updateStatusWidget( self, Devices, 'Ping: Reconnected after failure')
                                #        self.connectionState = 1
                            else:
                                #if self.connectionState == 0:
                                #    self.adminWidgets.updateStatusWidget( self, Devices, 'Ping: Reconnected after failure')
                                Domoticz.Log("Ping - Send a Ping")
                                sendZigateCmd( self, "0014", "" ) # Request status
                                self.connectionState = 1
                                self.Ping['Status'] = 'Sent'
                                self.Ping['TimeStamps'] = now
                        else:
                            Domoticz.Log("Ping - Send a Ping")
                            sendZigateCmd( self, "0014", "" ) # Request status
                            self.Ping['Status'] = 'Sent'
                            self.Ping['TimeStamps'] = now
                    else:
                        # We receive a message less than a minute ago
                        Domoticz.Debug("Ping - We have receive a message less than 1' ago ")
                else:
                    # We receive a message inside the HEARTBEAT
                    Domoticz.Debug("Ping - We have receive a message in between 2 Heartbeat")

            self.Ping['Rx Message'] += 1
        # Endif Ping enabled

        if busy_:
            self.adminWidgets.updateStatusWidget( Devices, 'Busy')
        elif not self.connectionState:
            self.adminWidgets.updateStatusWidget( Devices, 'No Communication')
        else:
            self.adminWidgets.updateStatusWidget( Devices, 'Ready')

        self.busy = False
        return True


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


