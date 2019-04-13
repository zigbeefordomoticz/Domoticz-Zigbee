#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

"""
<plugin key="Zigate" name="Zigate plugin" author="zaraki673 & pipiche38" version="4.2-beta" wikilink="https://www.domoticz.com/wiki/Zigate" externallink="https://github.com/sasu-drooz/Domoticz-Zigate/wiki">
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
        <param field="Mode1" label="Model" width="75px">
            <options>
                <option label="USB" value="USB" default="true" />
                <option label="PI" value="PI" />
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
from Modules.output import sendZigateCmd, removeZigateDevice, ZigatePermitToJoin, start_Zigate
from Modules.input import ZigateRead
from Modules.heartbeat import processListOfDevices
from Modules.database import importDeviceConf, LoadDeviceList, checkListOfDevice2Devices, checkListOfDevice2Devices, WriteDeviceList
from Modules.domoticz import ResetDevice
from Modules.command import mgtCommand
from Modules.LQI import LQIdiscovery
from Modules.consts import HEARTBEAT, CERTIFICATION
from Modules.txPower import set_TxPower

from Classes.IAS import IAS_Zone_Management
from Classes.PluginConf import PluginConf
from Classes.Transport import ZigateTransport
from Classes.TransportStats import TransportStatistics
from Classes.GroupMgt import GroupsManagement
from Classes.AdminWidgets import AdminWidgets
from Classes.OTA import OTAManagement


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
        self.adminWidgets = None   # Manage AdminWidgets object
        self.DeviceListName = None
        self.pluginconf = None     # PlugConf object / all configuration parameters

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

        Domoticz.Status("Zigate plugin 4.2-beta started")

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
        self.statistics = TransportStatistics(self.pluginconf)

        # Check update for web GUI
        # CheckForUpdate( self )

        # Connect to Zigate only when all initialisation are properly done.
        if  self.transport == "USB":
            self.ZigateComm = ZigateTransport( self.transport, self.statistics, self.pluginconf, self.processFrame,\
                    serialPort=Parameters["SerialPort"] )
        elif  self.transport == "PI":
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
        self.Ping['Rx Message'] = 1

        sendZigateCmd(self, "0010", "") # Get Firmware version

        if Parameters["Mode3"] == "True": # Erase PDM
            if self.domoticzdb_Hardware:
                self.domoticzdb_Hardware.disableErasePDM()
            Domoticz.Status("Erase Zigate PDM")
            sendZigateCmd(self, "0012", "")
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
            else:
                self.permitToJoin = 0
                self.Ping['Permit'] = None
                ZigatePermitToJoin(self, 0)

        sendZigateCmd(self, "0009", "") # Request Network state
        sendZigateCmd(self, "0015", "") # Request List of Active Device

        # Create IAS Zone object
        self.iaszonemgt = IAS_Zone_Management( self.ZigateComm , self.ListOfDevices)

        if (self.pluginconf).logLQI != 0 :
            LQIdiscovery( self ) 

        self.busy = False

        return True

    def onMessage(self, Connection, Data):
        #Domoticz.Debug("onMessage called on Connection " + " Data = '" +str(Data) + "'")
        if isinstance(Data, dict):
            Domoticz.Log("onMessage - unExpected for now")
            DumpHTTPResponseToLog(Data)
            return

        self.Ping['Rx Message'] = 0
        self.ZigateComm.onMessage(Data)

    def processFrame( self, Data ):
        ZigateRead( self, Devices, Data )

    def onCommand(self, Unit, Command, Level, Color):

        Domoticz.Debug("onCommand - unit: %s, command: %s, level: %s, color: %s" %(Unit, Command, Level, Color))
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
        self.connectionState = 0
        self.adminWidgets.updateStatusWidget( Devices, 'Plugin stop')
        Domoticz.Status("onDisconnect called")

    def onHeartbeat(self):
        
        busy_ = False
        Domoticz.Debug("onHeartbeat - busy = %s" %self.busy)

        if not self.connectionState:
            Domoticz.Error("onHeartbeat receive, but no connection to Zigate")
            return

        self.HeartbeatCount += 1

        # Ig ZigateIEEE not known, try to get it during the first 10 HB
        if self.ZigateIEEE is None and self.HeartbeatCount in ( 2, 4):   
            sendZigateCmd(self, "0009","")
        elif self.ZigateIEEE is None and self.HeartbeatCount == 5:
            start_Zigate( self )
            return

        if self.FirmwareVersion is None:
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
            if self.FirmwareVersion.lower() < '030f':
                Domoticz.Status("You are not on the latest firmware version, please consider to upgrade")

            if self.FirmwareVersion.lower() == '030e':
                Domoticz.Status("You are not on the latest firmware version, This version is known to have problem loosing Xiaomi devices, please consider to upgrae")

            if self.FirmwareVersion.lower() == '030f' and self.FirmwareMajorVersion == '0002':
                Domoticz.Error("You are not running on the Official 3.0f version (it was a pre-3.0f)")
        
            if self.FirmwareVersion.lower() > '030f':
                Domoticz.Error("Firmware %s is not yet supported" %self.FirmwareVersion.lower())

            if self.FirmwareVersion.lower() >= '030f' and self.FirmwareMajorVersion >= '0003':
                if self.pluginconf.blueLedOff:
                    Domoticz.Log("Switch Blue Led off")
                    sendZigateCmd(self, "0018","00")

                if self.pluginconf.TXpower_set:
                    set_TxPower( self, self.pluginconf.TXpower_set )

                if self.pluginconf.Certification in CERTIFICATION:
                    Domoticz.Log("Zigate set to Certification : %s" %CERTIFICATION[self.pluginconf.Certification])
                    sendZigateCmd(self, '0019', '%02x' %self.pluginconf.Certification)

                if self.groupmgt_NotStarted and self.pluginconf.enablegroupmanagement:
                    Domoticz.Status("Start Group Management")
                    self.groupmgt = GroupsManagement( self.pluginconf, self.adminWidgets, self.ZigateComm, Parameters["HomeFolder"], 
                            self.HardwareID, Parameters["Mode5"], Devices, self.ListOfDevices, self.IEEE2NWK )
                    self.groupmgt_NotStarted = False

            Domoticz.Status("Plugin with Zigate firmware %s correctly initialized" %self.FirmwareVersion)
            if self.pluginconf.allowOTA:
                self.OTA = OTAManagement( self.pluginconf, self.adminWidgets, self.ZigateComm, Parameters["HomeFolder"],
                            self.HardwareID, Devices, self.ListOfDevices, self.IEEE2NWK)

            if self.FirmwareVersion >= "030d":
                if (self.HeartbeatCount % ( 3600 // HEARTBEAT ) ) == 0 :
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
        if self.pluginconf.Ping:
            if ( self.HeartbeatCount % ( (5 * 60) // HEARTBEAT)) == 0 :
                Domoticz.Debug("Ping")
                if self.Ping['Rx Message']: # 'Rx Message' is set to 0 when receiving a Message.
                                            # Looks like we didn't receive messages
                    if  self.Ping['Rx Message'] > ( 60 //  HEARTBEAT ):
                        Domoticz.Debug("Ping - We didn't receive any messages since 60s")
                        # This is now about 1' or more that we didn't receive any messages.
                        # Let's try to ping Zigate in order to force a message
                        now = time.time()
                        if 'Status' in self.Ping:
                            if self.Ping['Status'] == 'Sent':
                                delta = now - self.Ping['TimeStamps']
                                Domoticz.Debug("processKnownDevices - Ping: %s" %delta)
                                if delta > 60: # Seems that we have lost the Zigate communication
                                    Domoticz.Error("Ping - no Heartbeat with Zigate")
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
                                Domoticz.Debug("Ping - Send a Ping")
                                sendZigateCmd( self, "0014", "" ) # Request status
                                self.connectionState = 1
                                self.Ping['Status'] = 'Sent'
                                self.Ping['TimeStamps'] = now
                        else:
                            Domoticz.Debug("Ping - Send a Ping")
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

        if len(self.ZigateComm._normalQueue) > 3:
            busy_ = True

        if busy_:
            self.adminWidgets.updateStatusWidget( Devices, 'Busy')
        elif not self.connectionState:
            self.adminWidgets.updateStatusWidget( Devices, 'No Communication')
        else:
            self.adminWidgets.updateStatusWidget( Devices, 'Ready')

        self.busy = busy_
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
