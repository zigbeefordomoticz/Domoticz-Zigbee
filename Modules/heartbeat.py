#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_heartbeat.py

    Description: Manage all actions done during the onHeartbeat() call

"""

import Domoticz
import binascii
import time
import datetime
import struct
import json

from Modules.output import  sendZigateCmd,  \
        processConfigureReporting, identifyEffect, setXiaomiVibrationSensitivity, \
        bindDevice, rebind_Clusters, getListofAttribute, \
        setPowerOn_OnOff, \
        ReadAttributeRequest_Ack,  \
        ReadAttributeRequest_0000, ReadAttributeRequest_0001, ReadAttributeRequest_0006, ReadAttributeRequest_0008, \
        ReadAttributeRequest_000C, ReadAttributeRequest_0102, ReadAttributeRequest_0201, ReadAttributeRequest_0204, ReadAttributeRequest_0300,  \
        ReadAttributeRequest_0400, ReadAttributeRequest_0402, ReadAttributeRequest_0403, ReadAttributeRequest_0405, \
        ReadAttributeRequest_0406, ReadAttributeRequest_0500, ReadAttributeRequest_0502, ReadAttributeRequest_0702

from Modules.tools import removeNwkInList, loggingPairing, loggingHeartbeat
from Modules.domoticz import CreateDomoDevice
from Modules.consts import HEARTBEAT, MAX_LOAD_ZIGATE

from Classes.IAS import IAS_Zone_Management
from Classes.Transport import ZigateTransport
from Classes.AdminWidgets import AdminWidgets
from Classes.NetworkMap import NetworkMap

READ_ATTRIBUTES_REQUEST = {
    # Cluster : ( ReadAttribute function, Frequency )
    '0000' : ( ReadAttributeRequest_0000, 'polling0000' ),
    '0001' : ( ReadAttributeRequest_0001, 'polling0001' ),
    '0006' : ( ReadAttributeRequest_0006, 'pollingONOFF' ),
    '0008' : ( ReadAttributeRequest_0008, 'pollingLvlControl' ),
    '000C' : ( ReadAttributeRequest_000C, 'polling000C' ),
    '0102' : ( ReadAttributeRequest_0102, 'polling0102' ),
    '0201' : ( ReadAttributeRequest_0201, 'polling0201' ),
    '0204' : ( ReadAttributeRequest_0204, 'polling0204' ),
    '0300' : ( ReadAttributeRequest_0300, 'polling0300' ),
    '0400' : ( ReadAttributeRequest_0400, 'polling0400' ),
    '0402' : ( ReadAttributeRequest_0402, 'polling0402' ),
    '0403' : ( ReadAttributeRequest_0403, 'polling0403' ),
    '0405' : ( ReadAttributeRequest_0405, 'polling0405' ),
    '0406' : ( ReadAttributeRequest_0406, 'polling0406' ),
    '0500' : ( ReadAttributeRequest_0500, 'polling0500' ),
    '0502' : ( ReadAttributeRequest_0502, 'polling0502' ),
    '0702' : ( ReadAttributeRequest_0702, 'polling0702' ),
    }

# Ordered List - Important for binding
CLUSTERS_LIST = [ 'fc00',  # Private cluster Philips Hue - Required for Remote
        '0500',            # IAS Zone
        '0502',            # IAS WD Zone
        '0406',            # Occupancy Sensing
        '0402',            # Temperature Measurement
        '0400',            # Illuminance Measurement
        '0001',            # Power Configuration
        '0102',            # Windows Covering / SHutter
        '0403',            # Measurement: Pression atmospherique
        '0405',            # Relative Humidity Measurement
        '0702',            # Smart Energy Metering
        '0006',            # On/Off
        '0008',            # Level Control
        '0201',            # Thermostat
        '0204',            # Thermostat UI
        '0300',            # Colour Control
        '0000',            # Basic
        'fc01',            # Private cluster 0xFC01 to manage some Legrand Netatmo stuff
        'ff02'             # Used by Xiaomi devices for battery informations.
        ]

def processKnownDevices( self, Devices, NWKID ):

    if self.CommiSSionning: # We have a commission in progress, skip it.
        return

    intHB = int( self.ListOfDevices[NWKID]['Heartbeat'])
    _mainPowered = False

    if 'PowerSource' in self.ListOfDevices[NWKID]:
        if (self.ListOfDevices[NWKID]['PowerSource']) == 'Main':
            _mainPowered = True

    if 'MacCapa' in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]['MacCapa'] == '8e': # Not a Main Powered 
            _mainPowered = True

    # On regular basis, try to collect as much information as possible from Main Powered devices
    if  _mainPowered and \
            ( self.HeartbeatCount % ( 300 // HEARTBEAT)) == 0 :
        if 'Attributes List' not in  self.ListOfDevices[NWKID]:
            for iterEp in self.ListOfDevices[NWKID]['Ep']:
                for iterCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                    if iterCluster in ( 'Type', 'ClusterType', 'ColorMode' ): continue
                    if self.busy  or len(self.ZigateComm._normalQueue) > MAX_LOAD_ZIGATE:
                        loggingHeartbeat( self, 'Debug', 'processKnownDevices - skip ReadAttribute for now ... system too busy (%s/%s) for %s' 
                                %(self.busy, len(self.ZigateComm._normalQueue), NWKID), NWKID)
                        break # Will do at the next round
                    getListofAttribute( self, NWKID, iterEp, iterCluster)

        if 'Manufacturer' not in self.ListOfDevices[NWKID] or \
                'DeviceType' not in self.ListOfDevices[NWKID] or \
                'LogicalType' not in self.ListOfDevices[NWKID] or \
                'PowerSource' not in self.ListOfDevices[NWKID] or \
                'ReceiveOnIdle' not in self.ListOfDevices[NWKID]:
            if not self.busy and  len(self.ZigateComm._normalQueue) <= MAX_LOAD_ZIGATE:
                loggingHeartbeat( self, 'Debug', 'processKnownDevices - skip ReadAttribute for now ... system too busy (%s/%s) for %s' 
                        %(self.busy, len(self.ZigateComm._normalQueue), NWKID), NWKID)
                Domoticz.Status("Requesting Node Descriptor for %s" %NWKID)
                sendZigateCmd(self,"0042", str(NWKID) )         # Request a Node Descriptor

    if _mainPowered and \
            ( self.pluginconf.pluginConf['enableReadAttributes'] or self.pluginconf.pluginConf['resetReadAttributes'] ) and ( intHB % (30 // HEARTBEAT)) == 0 :
        now = int(time.time())   # Will be used to trigger ReadAttributes
        for tmpEp in self.ListOfDevices[NWKID]['Ep']:    
            if tmpEp == 'ClusterType': continue
            for Cluster in READ_ATTRIBUTES_REQUEST:
                if Cluster in ( 'Type', 'ClusterType', 'ColorMode' ): continue
                if Cluster not in self.ListOfDevices[NWKID]['Ep'][tmpEp]:
                    continue
                if Cluster in ( '0000' ) and (intHB != ( 120 // HEARTBEAT)):
                    continue    # Just does it at plugin start
                if self.busy  or len(self.ZigateComm._normalQueue) > MAX_LOAD_ZIGATE:
                    loggingHeartbeat( self, 'Debug', 'processKnownDevices - skip ReadAttribute for now ... system too busy (%s/%s) for %s' 
                            %(self.busy, len(self.ZigateComm._normalQueue), NWKID), NWKID)
                    if intHB != 0:
                        self.ListOfDevices[NWKID]['Heartbeat'] = str( intHB - 1 ) # So next round it trigger again
                    break # Will do at the next round

                func = READ_ATTRIBUTES_REQUEST[Cluster][0]

                # For now it is a bid hack, but later we might put all parameters 
                if READ_ATTRIBUTES_REQUEST[Cluster][1] in self.pluginconf.pluginConf:
                    timing =  self.pluginconf.pluginConf[ READ_ATTRIBUTES_REQUEST[Cluster][1] ]
                else:
                    Domoticz.Error("processKnownDevices - missing timing attribute for Cluster: %s - %s" %(Cluster,  READ_ATTRIBUTES_REQUEST[Cluster][1]))
                    continue

                if 'ReadAttributes' not in self.ListOfDevices[NWKID]:
                    self.ListOfDevices[NWKID]['ReadAttributes'] = {}
                    self.ListOfDevices[NWKID]['ReadAttributes']['Ep'] = {}
                if 'TimeStamps' in self.ListOfDevices[NWKID]['ReadAttributes']:
                    _idx = tmpEp + '-' + str(Cluster)
                    if _idx in self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps']:
                        loggingHeartbeat( self, 'Debug', "processKnownDevices - processing %s with cluster %s TimeStamps: %s, Timing: %s , Now: %s "
                                %(NWKID, Cluster, self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps'][_idx], timing, now), NWKID)
                        if self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps'][_idx] != {}:
                            if now < (self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps'][_idx] + timing):
                                continue

                loggingHeartbeat( self, 'Debug', "%s/%s It's time to Request ReadAttribute for %s" %( NWKID, tmpEp, Cluster ), NWKID)
                func(self, NWKID )

    # Checking current state of the this Nwk
    if 'Health' not in self.ListOfDevices[NWKID]:
        self.ListOfDevices[NWKID]['Health'] = ''
    if 'Stamp' not in self.ListOfDevices[NWKID]:
        self.ListOfDevices[NWKID]['Stamp'] = {}
        self.ListOfDevices[NWKID]['Stamp']['LastSeen'] = 0
        self.ListOfDevices[NWKID]['Health'] = 'unknown'
    if 'LastSeen' not in self.ListOfDevices[NWKID]['Stamp']:
        self.ListOfDevices[NWKID]['Stamp']['LastSeen'] = 0
        self.ListOfDevices[NWKID]['Health'] = 'unknown'
    if int(time.time()) > (self.ListOfDevices[NWKID]['Stamp']['LastSeen'] + 86400) : # Age is above 24 hours
        if self.ListOfDevices[NWKID]['Health'] == 'Live':
            Domoticz.Error("Device Health - Nwkid: %s,Ieee: %s , Model: %s seems to be out of the network" \
                %(NWKID, self.ListOfDevices[NWKID]['IEEE'], self.ListOfDevices[NWKID]['Model']))
            self.ListOfDevices[NWKID]['Health'] = 'Not seen last 24hours'
    
def writeDiscoveryInfos( self ):

        if self.pluginconf.pluginConf['capturePairingInfos']:
            for dev in self.DiscoveryDevices:
                if 'IEEE' in self.DiscoveryDevices[dev]:
                    _filename = self.pluginconf.pluginConf['pluginReports'] + 'PairingInfos-' + '%02d' %self.HardwareID + '-%s' %self.DiscoveryDevices[dev]['IEEE'] + '.json'
                else:
                    _filename = self.pluginconf.pluginConf['pluginReports'] + 'PairingInfos-' + '%02d' %self.HardwareID + '-%s' %dev + '.json'

                with open ( _filename, 'wt') as json_file:
                    json.dump(self.DiscoveryDevices[dev],json_file, indent=2, sort_keys=True)

def processNotinDBDevices( self, Devices, NWKID , status , RIA ):

    # Starting V 4.1.x
    # 0x0043 / List of EndPoints is requested at the time we receive the End Device Annocement
    # 0x0045 / EndPoint Description is requested at the time we recice the List of EPs.
    # In case Model is defined and is in DeviceConf, we will short cut the all process and go to the Widget creation
    if status == 'UNKNOW':
        return
    
    HB_ = int(self.ListOfDevices[NWKID]['Heartbeat'])
    loggingPairing( self, 'Debug', "processNotinDBDevices - NWKID: %s, Status: %s, RIA: %s, HB_: %s " %(NWKID, status, RIA, HB_))
    if self.pluginconf.pluginConf['capturePairingInfos']:
        if NWKID not in self.DiscoveryDevices:
            self.DiscoveryDevices[NWKID] = {}
        self.DiscoveryDevices[NWKID]['CaptureProcess'] = {}
        self.DiscoveryDevices[NWKID]['CaptureProcess']['Status'] = status
        self.DiscoveryDevices[NWKID]['CaptureProcess']['RIA'] = RIA
        self.DiscoveryDevices[NWKID]['CaptureProcess']['HB_'] = HB_
        if 'Steps' not in self.DiscoveryDevices[NWKID]['CaptureProcess']:
            self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'] = []

    if status not in ( '004d', '0043', '0045', '8045', '8043') and 'Model' in self.ListOfDevices[NWKID]:
        return

    knownModel = False
    if self.ListOfDevices[NWKID]['Model'] != {}:
        Domoticz.Status("[%s] NEW OBJECT: %s Model Name: %s" %(RIA, NWKID, self.ListOfDevices[NWKID]['Model']))
        # Let's check if this Model is known
        if 'Model' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Model'] in self.DeviceConf:
                knownModel = True
                if not self.pluginconf.pluginConf['capturePairingInfos']:
                    status = 'createDB' # Fast track
                else:
                    self.ListOfDevices[NWKID]['RIA']=str( RIA + 1 )

    waitForDomoDeviceCreation = False
    if status == "8043": # We have at least receive 1 EndPoint
        reqColorModeAttribute = False
        self.ListOfDevices[NWKID]['RIA']=str( RIA + 1 )

        # Did we receive the Model Name
        if 'Model' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Model'] == {} or self.ListOfDevices[NWKID]['Model'] == '':
                Domoticz.Status("[%s] NEW OBJECT: %s Request Model Name" %(RIA, NWKID))
                ReadAttributeRequest_0000(self, NWKID )    # Reuest Model Name
                                                           # And wait 1 cycle
            else: 
                Domoticz.Status("[%s] NEW OBJECT: %s Model Name: %s" %(RIA, NWKID, self.ListOfDevices[NWKID]['Model']))
                # Let's check if this Model is known
                if knownModel:
                    status = 'createDB' # Fast track

        if 'Manufacturer' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Manufacturer'] == {}:
                Domoticz.Status("[%s] NEW OBJECT: %s Request Node Descriptor" %(RIA, NWKID))
                if self.pluginconf.pluginConf['capturePairingInfos']:
                    self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( '0042' )
                sendZigateCmd(self,"0042", str(NWKID))     # Request a Node Descriptor
            else:
                loggingHeartbeat( self, 'Debug', "[%s] NEW OBJECT: %s Model Name: %s" %(RIA, NWKID, self.ListOfDevices[NWKID]['Manufacturer']), NWKID)

        for iterEp in self.ListOfDevices[NWKID]['Ep']:
            #IAS Zone
            if '0500' in self.ListOfDevices[NWKID]['Ep'][iterEp] or \
                    '0502'  in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                # We found a Cluster 0x0500 IAS. May be time to start the IAS Zone process
                Domoticz.Status("[%s] NEW OBJECT: %s 0x%04s - IAS Zone controler setting" \
                        %( RIA, NWKID, status))
                if self.pluginconf.pluginConf['capturePairingInfos']:
                    self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'IAS-ENROLL' )
                self.iaszonemgt.IASZone_triggerenrollement( NWKID, iterEp)
                if '0502'  in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                    Domoticz.Status("[%s] NEW OBJECT: %s 0x%04s - IAS WD enrolment" \
                        %( RIA, NWKID, status))
                    if self.pluginconf.pluginConf['capturePairingInfos']:
                        self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'IASWD-ENROLL' )
                    self.iaszonemgt.IASWD_enroll( NWKID, iterEp)

        for iterEp in self.ListOfDevices[NWKID]['Ep']:
            # ColorMode
            if '0300' in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                if 'ColorInfos' in self.ListOfDevices[NWKID]:
                    if 'ColorMode' in self.ListOfDevices[NWKID]['ColorInfos']:
                        waitForDomoDeviceCreation = False
                        reqColorModeAttribute = False
                        break
                    else:
                        waitForDomoDeviceCreation = True
                        reqColorModeAttribute = True
                        break
                else:
                    waitForDomoDeviceCreation = True
                    reqColorModeAttribute = True
                    reqColorModeAttribute = True
                    break
        if reqColorModeAttribute:
            self.ListOfDevices[NWKID]['RIA']=str(RIA + 1 )
            Domoticz.Status("[%s] NEW OBJECT: %s Request Attribute for Cluster 0x0300 to get ColorMode" %(RIA,NWKID))
            if self.pluginconf.pluginConf['capturePairingInfos']:
                self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'RA_0300' )
            ReadAttributeRequest_0300(self, NWKID )
            if  self.ListOfDevices[NWKID]['RIA'] < '2':
                return
    # end if status== "8043"

    # Timeout management
    if (status == "004d" or status == "0045") and HB_ > 2 and status != 'createDB' and not knownModel: 
        Domoticz.Status("[%s] NEW OBJECT: %s TimeOut in %s restarting at 0x004d" %(RIA, NWKID, status))
        self.ListOfDevices[NWKID]['RIA']=str( RIA + 1 )
        self.ListOfDevices[NWKID]['Heartbeat']="0"
        self.ListOfDevices[NWKID]['Status']="0045"
        if 'Model' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Model'] == {}:
                Domoticz.Status("[%s] NEW OBJECT: %s Request Model Name" %(RIA, NWKID))
                if self.pluginconf.pluginConf['capturePairingInfos']:
                    self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'RA_0000' )
                ReadAttributeRequest_0000(self, NWKID )    # Reuest Model Name
        if self.pluginconf.pluginConf['capturePairingInfos']:
            self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( '0045' )
        sendZigateCmd(self,"0045", str(NWKID))
        return

    if (status == "8045" or status == "0043") and HB_ > 1 and status != 'createDB':
        Domoticz.Status("[%s] NEW OBJECT: %s TimeOut in %s restarting at 0x0043" %(RIA, NWKID, status))
        self.ListOfDevices[NWKID]['RIA']=str( RIA + 1 )
        self.ListOfDevices[NWKID]['Heartbeat'] = "0"
        self.ListOfDevices[NWKID]['Status'] = "0043"
        if 'Model' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Model'] == {}:
                Domoticz.Status("[%s] NEW OBJECT: %s Request Model Name" %(RIA, NWKID))
                if self.pluginconf.pluginConf['capturePairingInfos']:
                    self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'RA_0000' )
                ReadAttributeRequest_0000(self, NWKID )    # Reuest Model Name
        for iterEp in self.ListOfDevices[NWKID]['Ep']:
            Domoticz.Status("[%s] NEW OBJECT: %s Request Simple Descriptor for Ep: %s" %( '-', NWKID, iterEp))
            if self.pluginconf.pluginConf['capturePairingInfos']:
                self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( '0043' )
            sendZigateCmd(self,"0043", str(NWKID)+str(iterEp))
        return

    if knownModel and RIA > 3 and status != 'UNKNOW' and status != 'inDB':
        # We have done several retry to get Ep ...
        Domoticz.Log("processNotinDB - Try several times to get all informations, let's use the Model now" +str(NWKID) )
        status = 'createDB'

    elif self.ListOfDevices[NWKID]['RIA'] > '4' and status != 'UNKNOW' and status != 'inDB':  # We have done several retry
        Domoticz.Status("[%s] NEW OBJECT: %s Not able to get all needed attributes on time" %(RIA, NWKID))
        self.ListOfDevices[NWKID]['Status']="UNKNOW"
        Domoticz.Log("processNotinDB - not able to find response from " +str(NWKID) + " stop process at " +str(status) )
        Domoticz.Log("processNotinDB - RIA: %s waitForDomoDeviceCreation: %s, capturePairingInfos: %s Model: %s " \
                %( self.ListOfDevices[NWKID]['RIA'], waitForDomoDeviceCreation, self.pluginconf.pluginConf['capturePairingInfos'], self.ListOfDevices[NWKID]['Model']))
        Domoticz.Log("processNotinDB - Collected Infos are : %s" %(str(self.ListOfDevices[NWKID])))
        self.adminWidgets.updateNotificationWidget( Devices, 'Unable to collect all informations for enrollment of this devices. See Logs' )
        self.CommiSSionning = False
        if self.pluginconf.pluginConf['capturePairingInfos']:
            self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'UNKNOW' )
        writeDiscoveryInfos( self )
        return

    if status in ( 'createDB', '8043' ):
        #We will try to create the device(s) based on the Model , if we find it in DeviceConf or against the Cluster
        if status == '8043' and self.ListOfDevices[NWKID]['RIA'] < '3':     # Let's take one more chance to get Model
            Domoticz.Log("Too early, let's try to get the Model")
            return
        loggingPairing( self, 'Debug', "[%s] NEW OBJECT: %s Trying to create Domoticz device(s)" %(RIA, NWKID))
        IsCreated=False
        # Let's check if the IEEE is not known in Domoticz
        for x in Devices:
            if self.ListOfDevices[NWKID].get('IEEE'):
                if Devices[x].DeviceID == str(self.ListOfDevices[NWKID]['IEEE']):
                    if self.pluginconf.pluginConf['capturePairingInfos'] == 1:
                        Domoticz.Log("processNotinDBDevices - Devices already exist. "  + Devices[x].Name + " with " + str(self.ListOfDevices[NWKID]) )
                        Domoticz.Log("processNotinDBDevices - ForceCreationDevice enable, we continue")
                    else:
                        IsCreated = True
                        Domoticz.Error("processNotinDBDevices - Devices already exist. "  + Devices[x].Name + " with " + str(self.ListOfDevices[NWKID]) )
                        Domoticz.Error("processNotinDBDevices - Please cross check the consistency of the Domoticz and Plugin database.")
                        break

        if IsCreated == False:
            loggingPairing( self, 'Debug', "processNotinDBDevices - ready for creation: %s" %self.ListOfDevices[NWKID])
            if self.pluginconf.pluginConf['capturePairingInfos']:
                self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'CR-DOMO' )
            CreateDomoDevice(self, Devices, NWKID)

            # Post creation widget
            if NWKID not in self.ListOfDevices:
                Domoticz.Error("processNotinDBDevices - %s doesn't exist in Post creation widget" %NWKID)
                return
            if 'Ep' not in self.ListOfDevices[NWKID]:
                Domoticz.Error("processNotinDBDevices - %s doesn't have Ep in Post creation widget" %NWKID)
                return
                
            if 'ConfigSource' in self.ListOfDevices[NWKID]:
                loggingPairing( self, 'Debug', "Device: %s - Config Source: %s Ep Details: %s" \
                        %(NWKID,self.ListOfDevices[NWKID]['ConfigSource'],str(self.ListOfDevices[NWKID]['Ep'])))

            # Binding devices
            for iterBindCluster in CLUSTERS_LIST:      # Bining order is important
                for iterEp in self.ListOfDevices[NWKID]['Ep']:
                    if iterBindCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                        Domoticz.Log('Request a Bind for %s/%s on Cluster %s' %(NWKID, iterEp, iterBindCluster))
                        if self.pluginconf.pluginConf['capturePairingInfos']:
                            self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'BIND_' + iterEp + '_' + iterBindCluster )
                        bindDevice( self, self.ListOfDevices[NWKID]['IEEE'], iterEp, iterBindCluster)

            # 2 Enable Configure Reporting for any applicable cluster/attributes
            if self.pluginconf.pluginConf['capturePairingInfos']:
                self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'PR-CONFIG' )
            processConfigureReporting( self, NWKID )  

            for iterReadAttrCluster in CLUSTERS_LIST:
                for iterEp in self.ListOfDevices[NWKID]['Ep']:
                    if iterReadAttrCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                        if iterReadAttrCluster in READ_ATTRIBUTES_REQUEST:
                            if self.pluginconf.pluginConf['capturePairingInfos']:
                                self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'RA_' + iterEp + '_' + iterReadAttrCluster )
                            func = READ_ATTRIBUTES_REQUEST[iterReadAttrCluster][0]
                            func( self, NWKID)

            # Identify for ZLL compatible devices
            # Search for EP to be used 
            ep = '01'
            for ep in self.ListOfDevices[NWKID]['Ep']:
                if ep in ( '01', '03', '06', '09' ):
                    break
            identifyEffect( self, NWKID, ep , effect='Blink' )

            for iterEp in self.ListOfDevices[NWKID]['Ep']:
                loggingPairing( self, 'Debug', 'looking for List of Attributes ep: %s' %iterEp)
                for iterCluster in  self.ListOfDevices[NWKID]['Ep'][iterEp]:
                    if iterCluster in ( 'Type', 'ClusterType', 'ColorMode' ): 
                        continue
                    if self.pluginconf.pluginConf['capturePairingInfos']:
                        self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'LST-ATTR_' + iterEp + '_' + iterCluster )
                    getListofAttribute( self, NWKID, iterEp, iterCluster)

            # Set the sensitivity for Xiaomi Vibration
            if  self.ListOfDevices[NWKID]['Model'] == 'lumi.vibration.aq1':
                 Domoticz.Status('processNotinDBDevices - set viration Aqara %s sensitivity to %s' \
                        %(NWKID, self.pluginconf.pluginConf['vibrationAqarasensitivity']))
                 setXiaomiVibrationSensitivity( self, NWKID, sensitivity = self.pluginconf.pluginConf['vibrationAqarasensitivity'])

            self.adminWidgets.updateNotificationWidget( Devices, 'Successful creation of Widget for :%s DeviceID: %s' \
                    %(self.ListOfDevices[NWKID]['Model'], NWKID))
            self.CommiSSionning = False
            if self.pluginconf.pluginConf['capturePairingInfos']:
                self.DiscoveryDevices[NWKID]['CaptureProcess']['ListOfDevice'] = dict( self.ListOfDevices[NWKID] )

            writeDiscoveryInfos( self )

        #end if ( self.ListOfDevices[NWKID]['Status']=="8043" or self.ListOfDevices[NWKID]['Model']!= {} )
    #end ( self.pluginconf.storeDiscoveryFrames == 0 and status != "UNKNOW" and status != "DUP")  or (  self.pluginconf.storeDiscoveryFrames == 1 and status == "8043" )
    

def processListOfDevices( self , Devices ):
    # Let's check if we do not have a command in TimeOut
    self.ZigateComm.checkTOwaitFor()

    entriesToBeRemoved = []
    for NWKID in list(self.ListOfDevices):
        if NWKID in ('ffff', '0000'): continue
        # If this entry is empty, then let's remove it .
        if len(self.ListOfDevices[NWKID]) == 0:
            loggingHeartbeat( self, 'Debug', "Bad devices detected (empty one), remove it, adr:" + str(NWKID), NWKID)
            entriesToBeRemoved.append( NWKID )
            continue
            
        status = self.ListOfDevices[NWKID]['Status']
        RIA = int(self.ListOfDevices[NWKID]['RIA'])
        self.ListOfDevices[NWKID]['Heartbeat']=str(int(self.ListOfDevices[NWKID]['Heartbeat'])+1)

        if status == "failDB":
            entriesToBeRemoved.append( NWKID )

        ########## Known Devices 
        if status == "inDB" and not self.busy: 
            processKnownDevices( self , Devices, NWKID )

        if status == "Left":
            # Device has sent a 0x8048 message annoucing its departure (Leave)
            # Most likely we should receive a 0x004d, where the device come back with a new short address
            # For now we will display a message in the log every 1'
            # We might have to remove this entry if the device get not reconnected.
            if (( int(self.ListOfDevices[NWKID]['Heartbeat']) % 36 ) and  int(self.ListOfDevices[NWKID]['Heartbeat']) != 0) == 0:
                Domoticz.Log("processListOfDevices - Device: " +str(NWKID) + " is in Status = 'Left' for " +str(self.ListOfDevices[NWKID]['Heartbeat']) + "HB" )
                # Let's check if the device still exist in Domoticz
                for Unit in Devices:
                    if self.ListOfDevices[NWKID]['IEEE'] == Devices[Unit].DeviceID:
                        loggingHeartbeat( self, 'Debug', "processListOfDevices - %s  is still connected cannot remove. NwkId: %s IEEE: %s " \
                                %(Devices[Unit].Name, NWKID, self.ListOfDevices[NWKID]['IEEE']), NWKID)
                        fnd = True
                        break
                else: #We browse the all Devices and didn't find any IEEE.
                    if 'IEEE' in self.ListOfDevices[NWKID]:
                        Domoticz.Log("processListOfDevices - No corresponding device in Domoticz for %s/%s" %( NWKID, str(self.ListOfDevices[NWKID]['IEEE'])))
                    else:
                        Domoticz.Log("processListOfDevices - No corresponding device in Domoticz for %s" %( NWKID))
                    fnd = False

                if not fnd:
                    # Not devices found in Domoticz, so we are safe to remove it from Plugin
                    if self.ListOfDevices[NWKID]['IEEE'] in self.IEEE2NWK:
                        Domoticz.Status("processListOfDevices - Removing %s / %s from IEEE2NWK." %(self.ListOfDevices[NWKID]['IEEE'], NWKID))
                        del self.IEEE2NWK[self.ListOfDevices[NWKID]['IEEE']]
                    Domoticz.Status("processListOfDevices - Removing the entry %s from ListOfDevice" %(NWKID))
                    removeNwkInList( self, NWKID)

        elif status != "inDB" and status != "UNKNOW":
            # Discovery process 0x004d -> 0x0042 -> 0x8042 -> 0w0045 -> 0x8045 -> 0x0043 -> 0x8043
            processNotinDBDevices( self , Devices, NWKID, status , RIA )
    #end for key in ListOfDevices
    
    for iter in entriesToBeRemoved:
        if 'IEEE' in self.ListOfDevices[iter]:
            _ieee = self.ListOfDevices[iter]['IEEE']
            del _ieee
        del self.ListOfDevices[iter]

    if self.CommiSSionning or self.busy:
        loggingHeartbeat( self, 'Debug', "Skip LQI, ConfigureReporting and Networkscan du to Busy state: Busy: %s, Enroll: %s" %(self.busy, self.CommiSSionning))
        return  # We don't go further as we are Commissioning a new object and give the prioirty to it

    if ( self.HeartbeatCount % (60 // HEARTBEAT)) == 0:
        # Trigger Conifre Reporting to eligeable decices
        processConfigureReporting( self )

    if self.HeartbeatCount > ( 5 * 60 // HEARTBEAT):
        # Network Topology
        if self.networkmap:
            phase = self.networkmap.NetworkMapPhase()
            if phase == 1:
                Domoticz.Log("Start NetworkMap process")
                self.start_scan( )
            elif phase == 2:
                if self.ZigateComm.loadTransmit() < 2 :
                     self.networkmap.continue_scan( )

    if self.HeartbeatCount > ( 3 * 60 // HEARTBEAT):
        # Network Energy Level
        if self.networkenergy:
            if self.ZigateComm.loadTransmit() < 2:
                self.networkenergy.do_scan()

    return True


