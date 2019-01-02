#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

"""
<plugin key="Zigate" name="Zigate plugin" author="zaraki673 & pipiche38" version="dev groupmgt" wikilink="http://www.domoticz.com/wiki/Zigate" externallink="https://github.com/sasu-drooz/Domoticz-Zigate/wiki">
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

import z_tools
import z_output
import z_input
import z_heartbeat
import z_database
import z_domoticz
import z_command
import z_LQI
import z_consts
import z_adminWidget
import z_WebGui

from z_IAS import IAS_Zone_Management
from z_PluginConf import PluginConf
from z_Transport import ZigateTransport
from z_TransportStats import TransportStatistics
from z_GroupMgt import GroupsManagement

class BasePlugin:
    enabled = False

    def __init__(self):
        self.ListOfDevices = {}  # {DevicesAddresse : { status : status_de_detection, data : {ep list ou autres en fonctions du status}}, DevicesAddresse : ...}
        self.ZigateComm = None
        self._ReqRcv = bytearray()
        self.permitTojoin = None
        self.groupmgt = None
        self.groupmgt_NotStarted = True
        self.CommiSSionning = False    # This flag is raised when a Device Annocement is receive, in order to give priority to commissioning
        self.busy = False    # This flag is raised when a Device Annocement is receive, in order to give priority to commissioning
        self.Ping = {}
        self.connectionState = None
        self.DiscoveryDevices = {}
        self.IEEE2NWK = {}
        self.LQI = {}
        self.LQISource = ''
        self.DeviceListName = ''
        self.homedirectory = ''
        self.HardwareID = ''
        self.transport = ''         # USB or Wifi
        self.pluginconf = None     # PlugConf object / all configuration parameters
        self.statistics = None
        self.iaszonemgt = None      # Object to manage IAS Zone
        self.Key = ''
        self.HBcount=0
        self.HeartbeatCount = 0
        self.currentChannel = None  # Curent Channel. Set in Decode8009/Decode8024
        self.ZigateIEEE = None       # Zigate IEEE. Set in CDecode8009/Decode8024
        self.ZigateNWKID = None       # Zigate NWKID. Set in CDecode8009/Decode8024
        self.FirmwareVersion = None
        self.mainpowerSQN = None    # Tracking main Powered SQN
        self.ForceCreationDevice = None   # Allow to force devices even if they are not in the Plugin Database. Could be usefull after the Firmware update where you have your devices in domoticz

        return

    def onStart(self):
        Domoticz.Status("onStart called - Zigate plugin V Dev Group Management")
        self.busy = True
        z_adminWidget.updateStatusWidget( self, Devices, 'Startup')

        Domoticz.Heartbeat( z_consts.HEARTBEAT )

        if Parameters["Mode6"] != "0":
            Domoticz.Debugging(int(Parameters["Mode6"]))
            DumpConfigToLog()
        
        self.homedirectory = Parameters["HomeFolder"]
        self.HardwareID = (Parameters["HardwareID"])
        self.Key = (Parameters["Key"])
        self.transport = Parameters["Mode1"]


        Domoticz.Status("DomoticzVersion: %s" %Parameters["DomoticzVersion"])
        Domoticz.Status("DomoticzHash: %s" %Parameters["DomoticzHash"])
        Domoticz.Status("DomoticzBuildTime: %s" %Parameters["DomoticzBuildTime"])
        self.DomoticzVersion = Parameters["DomoticzVersion"]
        # Import PluginConf.txt
        if Parameters["DomoticzVersion"] >= '4.10267':
            Domoticz.Status("Home Folder: %s" %Parameters["HomeFolder"])
            Domoticz.Status("Startup Folder: %s" %Parameters["StartupFolder"])
            self.StartupFolder = Parameters["StartupFolder"]

        Domoticz.Status("load PluginConf" )
        self.pluginconf = PluginConf(Parameters["HomeFolder"], self.HardwareID)
        

        self.DeviceListName = self.pluginconf.pluginData + "DeviceList-" + str(Parameters['HardwareID']) + ".txt"
        Domoticz.Status("Plugin Database: %s" %self.DeviceListName)

        plugconf = self.pluginconf
        if  plugconf.allowStoreDiscoveryFrames == 1 :
            self.DiscoveryDevices = {}

        #Import DeviceConf.txt
        z_database.importDeviceConf( self ) 

        #Import DeviceList.txt Filename is : DeviceListName
        Domoticz.Status("load ListOfDevice" )
        if z_database.LoadDeviceList( self ) == 'Failed' :
            Domoticz.Error("Something wennt wrong during the import of Load of Devices ...")
            Domoticz.Error("Please cross-check your log ... You must be on V3 of the DeviceList and all DeviceID in Domoticz converted to IEEE")
            return            
        
        Domoticz.Log("ListOfDevices : " )
        for e in self.ListOfDevices.items(): Domoticz.Log(" "+str(e))
        Domoticz.Debug("IEEE2NWK      : " )
        for e in self.IEEE2NWK.items(): Domoticz.Debug("  "+str(e))

        # Check proper match against Domoticz Devices
        z_database.checkListOfDevice2Devices( self, Devices )

        Domoticz.Debug("ListOfDevices after checkListOfDevice2Devices: " +str(self.ListOfDevices) )
        Domoticz.Debug("IEEE2NWK after checkListOfDevice2Devices     : " +str(self.IEEE2NWK) )

        # Create Statistics object
        self.statistics = TransportStatistics()

        # Check update for web GUI
        z_WebGui.CheckForUpdate( self )

        # Create the adminStatusWidget if needed
        z_adminWidget.initializeZigateWidgets( self, Devices)

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

        Domoticz.Log("Establish Zigate connection" )
        self.ZigateComm.openConn()
        self.busy = False
        return

    def onStop(self):
        Domoticz.Status("onStop called")
        #self.ZigateComm.closeConn()
        z_database.WriteDeviceList(self, Parameters["HomeFolder"], 0)
        if self.groupmgt and self.FirmwareVersion >= '030f':
            self.groupmgt.storeListOfGroups()
        self.statistics.printSummary()
        z_adminWidget.updateStatusWidget( self, Devices, 'No Communication')

    def onDeviceRemoved( self, Unit ) :
        Domoticz.Status("onDeviceRemoved called" )
        # Let's check if this is End Node, or Group related.
        if Devices[Unit].DeviceID in self.IEEE2NWK:
            # Command belongs to a end node
            Domoticz.Log("onDeviceRemoved - removing End Device")
            z_tools.removeDeviceInList( self, Devices, Devices[Unit].DeviceID , Unit)
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
            Domoticz.Log("Connected successfully")

            if self.connectionState is None:
                z_adminWidget.updateStatusWidget( self, Devices, 'Starting the plugin up')
            elif self.connectionState == 0:
                Domoticz.Status("Reconnected after failure")
                z_adminWidget.updateStatusWidget( self, Devices, 'Reconnected after failure')
            self.connectionState = 1
            self.Ping['Status'] = None
            self.Ping['TimeStamp'] = None
            self.Ping['Permit'] = None

            if Parameters["Mode3"] == "True":
                ################### ZiGate - ErasePD ##################
                Domoticz.Status("Erase Zigate PDM")
                z_output.sendZigateCmd(self, "0012", "")
                Domoticz.Status("Software reset")
                z_output.sendZigateCmd(self, "0011", "") # Software Reset
                z_output.ZigateConf(self, Parameters["Mode2"])
            else :
                if Parameters["Mode4"] == "True":
                    Domoticz.Status("Software reset")
                    z_output.sendZigateCmd(self, "0011", "" ) # Software Reset
                    z_output.ZigateConf(self, Parameters["Mode2"])
                else:
                    z_output.ZigateConf_light(self, Parameters["Mode2"])
        else:
            Domoticz.Error("Failed to connect ("+str(Status)+")")
            Domoticz.Debug("Failed to connect ("+str(Status)+") with error: "+Description)
            self.connectionState = 0
            self.ZigateComm.reConn()
            z_adminWidget.updateStatusWidget( self, Devices, 'No Communication')


        # Create IAS Zone object
        self.iaszonemgt = IAS_Zone_Management( self.ZigateComm , self.ListOfDevices)

        if (self.pluginconf).logLQI != 0 :
            z_LQI.LQIdiscovery( self ) 

        self.busy = False
        return True

    def onMessage(self, Connection, Data):
        #Domoticz.Debug("onMessage called on Connection " + " Data = '" +str(Data) + "'")
        self.ZigateComm.onMessage(Data)

    def processFrame( self, Data ):
        z_input.ZigateRead( self, Devices, Data )

    def onCommand(self, Unit, Command, Level, Color):

        # Let's check if this is End Node, or Group related.
        if Devices[Unit].DeviceID in self.IEEE2NWK:
            # Command belongs to a end node
            z_command.mgtCommand( self, Devices, Unit, Command, Level, Color )

        elif self.pluginconf.enablegroupmanagement and self.groupmgt:
            if Devices[Unit].DeviceID in self.groupmgt.ListOfGroups:
                # Command belongs to a Zigate group
                self.groupmgt.processCommand( Unit, Devices[Unit].DeviceID, Command, Level, Color )
                Domoticz.Log("Command: %s/%s/%s to Group: %s" %(Command,Level,Color, Devices[Unit].DeviceID))

        elif Devices[Unit].Name.find('Zigate-01-'):
            Domoticz.Log("onCommand - Command adminWidget: %s " %Command)
            z_adminWidget.handleCommand( self, Command)

    def onDisconnect(self, Connection):
        self.connectionState = 0
        z_adminWidget.updateStatusWidget( self, Devices, 'Plugin stop')
        Domoticz.Status("onDisconnect called")

    def onHeartbeat(self):
        
        self.HeartbeatCount += 1

        if self.groupmgt_NotStarted and self.pluginconf.enablegroupmanagement and self.FirmwareVersion:
            # Check if we are with Firmware above 30f
            if self.FirmwareVersion >= '030f':
                Domoticz.Log("Start Group Management")
                self.groupmgt = GroupsManagement( self.ZigateComm, Parameters["HomeFolder"], 
                      self.HardwareID, Devices, self.ListOfDevices, self.IEEE2NWK )
                self.groupmgt_NotStarted = False
            else:
                Domoticz.Error("Cannot start Group Management due to low firmware level. Need >= 3.0f")

        # Ig ZigateIEEE not known, try to get it during the first 10 HB
        if self.ZigateIEEE is None and self.HeartbeatCount in ( 2, 4, 6, 8, 10):   
            z_output.sendZigateCmd(self, "0009","")

        if self.FirmwareVersion == "030d" or self.FirmwareVersion == "030e":
            if (self.HeartbeatCount % ( 3600 // z_consts.HEARTBEAT ) ) == 0 :
                z_output.sendZigateCmd(self, "0009","")
        
        prevLenDevices = len(Devices)
        # Manage all entries in  ListOfDevices (existing and up-coming devices)
        z_heartbeat.processListOfDevices( self , Devices )

        # IAS Zone Management
        self.iaszonemgt.IAS_heartbeat( )

        # Reset Motion sensors
        z_domoticz.ResetDevice( self, Devices, "Motion",5)

        # Write the ListOfDevice in HBcount % 200 ( 3' ) or immediatly if we have remove or added a Device
        if len(Devices) != prevLenDevices:
            Domoticz.Log("Devices size has changed , let's write ListOfDevices on disk")
            z_database.WriteDeviceList(self, Parameters["HomeFolder"], 0)       # write immediatly
        else:
            z_database.WriteDeviceList(self, Parameters["HomeFolder"], ( 90 * 5) )

        if self.CommiSSionning:
            z_adminWidget.updateStatusWidget( self, Devices, 'Enrolment')
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
        if ( self.HeartbeatCount % ( 60 // z_consts.HEARTBEAT)) == 0 :
            Domoticz.Debug("Ping")
            now = time.time()
            if 'Status' in self.Ping:
                if self.Ping['Status'] == 'Sent':
                    delta = now - self.Ping['TimeStamps']
                    Domoticz.Debug("processKnownDevices - Ping: %s" %delta)
                    if delta > 50:
                        Domoticz.Log("Ping - no Heartbeat with Zigate")
                        z_adminWidget.updateNotificationWidget( self, Devices, 'Ping: Connection with Zigate Lost')
                        self.connectionState = 0
                        self.ZigateComm.reConn()
                    else:
                        if self.connectionState == 0:
                            z_adminWidget.updateStatusWidget( self, Devices, 'Ping: Reconnected after failure')
                            self.connectionState = 1
                else:
                    if self.connectionState == 0:
                        z_adminWidget.updateStatusWidget( self, Devices, 'Ping: Reconnected after failure')
                    z_output.sendZigateCmd( self, "0014", "" ) # Request status
                    self.connectionState = 1
                    self.Ping['Status'] = 'Sent'
                    self.Ping['TimeStamps'] = now
            else:
                z_output.sendZigateCmd( self, "0014", "" ) # Request status
                self.Ping['Status'] = 'Sent'
                self.Ping['TimeStamps'] = now

        if busy_:
            z_adminWidget.updateStatusWidget( self, Devices, 'Busy')
        elif not self.connectionState:
            z_adminWidget.updateStatusWidget( self, Devices, 'No Communication')
        else:
            z_adminWidget.updateStatusWidget( self, Devices, 'Ready')

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


