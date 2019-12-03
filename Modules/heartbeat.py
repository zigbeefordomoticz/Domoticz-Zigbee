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

from Modules.actuators import actuators
from Modules.output import  sendZigateCmd,  \
        processConfigureReporting, identifyEffect, setXiaomiVibrationSensitivity, \
        unbindDevice, bindDevice, rebind_Clusters, getListofAttribute, \
        livolo_bind, \
        legrand_fc01, \
        setPowerOn_OnOff, \
        scene_membership_request, \
        schneider_thermostat, \
        ReadAttributeRequest_Ack,  ReadAttributeRequest_0000_basic, \
        ReadAttributeRequest_0000, ReadAttributeRequest_0001, ReadAttributeRequest_0006, ReadAttributeRequest_0008, \
        ReadAttributeRequest_0100, \
        ReadAttributeRequest_000C, ReadAttributeRequest_0102, ReadAttributeRequest_0201, ReadAttributeRequest_0204, ReadAttributeRequest_0300,  \
        ReadAttributeRequest_0400, ReadAttributeRequest_0402, ReadAttributeRequest_0403, ReadAttributeRequest_0405, \
        ReadAttributeRequest_0406, ReadAttributeRequest_0500, ReadAttributeRequest_0502, ReadAttributeRequest_0702, ReadAttributeRequest_000f, ReadAttributeRequest_fc01

from Modules.tools import removeNwkInList, loggingPairing, loggingHeartbeat, mainPoweredDevice
from Modules.domoticz import CreateDomoDevice
from Modules.zigateConsts import HEARTBEAT, MAX_LOAD_ZIGATE, CLUSTERS_LIST, LEGRAND_REMOTES, LEGRAND_REMOTE_SHUTTER, LEGRAND_REMOTE_SWITCHS

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
    '0100' : ( ReadAttributeRequest_0100, 'polling0100' ),
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
    '000f' : ( ReadAttributeRequest_000f, 'polling000f' ),
    #'fc01' : ( ReadAttributeRequest_fc01, 'pollingfc01' ),
    }

#READ_ATTR_COMMANDS = ( '0006', '0008', '0102' )
# For now, we just look for On/Off state
READ_ATTR_COMMANDS = ( '0006', )

# Read Attribute trigger: Every 10"
# Configure Reporting trigger: Every 15
# Network Topology start: 15' after plugin start
# Network Energy start: 30' after plugin start
# Legrand re-enforcement: Every 5'

READATTRIBUTE_FEQ =    10 // HEARTBEAT # 10seconds ... 
CONFIGURERPRT_FEQ =    30 // HEARTBEAT
LEGRAND_FEATURES =    300 // HEARTBEAT
NETWORK_TOPO_START =  900 // HEARTBEAT
NETWORK_ENRG_START = 1800 // HEARTBEAT

def processKnownDevices( self, Devices, NWKID ):

    # Normalize Hearbeat value if needed
    intHB = int( self.ListOfDevices[NWKID]['Heartbeat'])
    if intHB > 0xffff:
        intHB -= 0xfff0
        self.ListOfDevices[NWKID]['Heartbeat'] = intHB

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

    if self.CommiSSionning: # We have a commission in progress, skip it.
        return

    # If device flag as Not Reachable, don't do anything
    if 'Health' in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]['Health'] == 'Not Reachable':
            loggingHeartbeat( self, 'Debug', "processKnownDevices -  %s stop here due to Health %s" %(NWKID, self.ListOfDevices[NWKID]['Health']), NWKID)
            return
        # In case Health is unknown let's force a Read attribute.
        _checkHealth = False
        if self.ListOfDevices[NWKID]['Health'] == '':
            _checkHealth = True

    # Check if this is a Main powered device or Not. Source of information are: MacCapa and PowerSource
    _mainPowered = mainPoweredDevice( self, NWKID)

    _doReadAttribute = False
    _forceCommandCluster = False

    if (intHB == 1) and self.pluginconf.pluginConf['forcePollingAfterAction']: # Most-likely Heartbeat has been reset to 0 as for a Group command
        loggingHeartbeat( self, 'Debug', "processKnownDevices -  %s due to intHB %s" %(NWKID, intHB), NWKID)
        _forceCommandCluster = True

    ## Starting this point, it is ony relevant for Main Powered Devices.
    #  except if _forceCommandCluster has been enabled.
    if not _mainPowered and not _forceCommandCluster:
        return

    # In order to limit the load, we do it only every 15s
    if self.pluginconf.pluginConf['enableReadAttributes'] or self.pluginconf.pluginConf['resetReadAttributes']:
        if ( intHB % READATTRIBUTE_FEQ ) == 0:
            _doReadAttribute = True

    # Do we need to force ReadAttribute at plugin startup ?
    # If yes, best is probably to have ResetReadAttribute to 1
    if _doReadAttribute or _forceCommandCluster:
        loggingHeartbeat( self, 'Debug', "processKnownDevices -  %s intHB: %s _mainPowered: %s doReadAttr: %s frcRead: %s" %(NWKID, intHB, _mainPowered, _doReadAttribute, _forceCommandCluster), NWKID)
        # Read Attributes if enabled
        now = int(time.time())   # Will be used to trigger ReadAttributes
        for tmpEp in self.ListOfDevices[NWKID]['Ep']:    
            if tmpEp == 'ClusterType': continue
            for Cluster in READ_ATTRIBUTES_REQUEST:
                if Cluster in ( 'Type', 'ClusterType', 'ColorMode' ): continue
                if Cluster not in self.ListOfDevices[NWKID]['Ep'][tmpEp]:
                    continue
                if 'ReadAttributes' not in self.ListOfDevices[NWKID]:
                    self.ListOfDevices[NWKID]['ReadAttributes'] = {}
                    self.ListOfDevices[NWKID]['ReadAttributes']['Ep'] = {}

                if 'Model' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Model'] == 'TI0001':
                        # Don't do it for Livolo
                        continue
                    if self.ListOfDevices[NWKID]['Model'] == 'lumi.ctrl_neutral1' and tmpEp != '02': # All Eps other than '02' are blacklisted
                        continue
                    if  self.ListOfDevices[NWKID]['Model'] == 'lumi.ctrl_neutral2' and tmpEp not in ( '02' , '03' ):
                        continue

                if _forceCommandCluster and not _doReadAttribute:
                    # Force Majeur
                    if ( intHB == 1 and _mainPowered and Cluster in READ_ATTR_COMMANDS ) or \
                          ( intHB == 1 and not _mainPowered and Cluster == '0001') :
                        loggingHeartbeat( self, 'Debug', '-- - Force Majeur on %s/%s cluster %s' %( NWKID, tmpEp, Cluster), NWKID)

                        # Let's reset the ReadAttribute Flag
                        if 'TimeStamps' in self.ListOfDevices[NWKID]['ReadAttributes']:
                            _idx = tmpEp + '-' + str(Cluster)
                            if _idx in self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps']:
                                if self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps'][_idx] != {}:
                                    self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps'][_idx] = 0

                if  (self.busy  or len(self.ZigateComm.zigateSendingFIFO) > MAX_LOAD_ZIGATE):
                    loggingHeartbeat( self, 'Debug', '--  -  %s skip ReadAttribute for now ... system too busy (%s/%s)' 
                            %(NWKID, self.busy, len(self.ZigateComm.zigateSendingFIFO)), NWKID)
                    if intHB != 0:
                        self.ListOfDevices[NWKID]['Heartbeat'] = str( intHB - 1 ) # So next round it trigger again
                    continue # Do not break, so we can keep all clusters on the same states
   
                func = READ_ATTRIBUTES_REQUEST[Cluster][0]
  
                # For now it is a hack, but later we might put all parameters 
                if READ_ATTRIBUTES_REQUEST[Cluster][1] in self.pluginconf.pluginConf:
                    timing =  self.pluginconf.pluginConf[ READ_ATTRIBUTES_REQUEST[Cluster][1] ]
                else:
                    Domoticz.Error("processKnownDevices - missing timing attribute for Cluster: %s - %s" %(Cluster,  READ_ATTRIBUTES_REQUEST[Cluster][1]))
                    continue
 
                # Let's check the timing
                if 'TimeStamps' in self.ListOfDevices[NWKID]['ReadAttributes']:
                    _idx = tmpEp + '-' + str(Cluster)
                    if _idx in self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps']:
                        if self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps'][_idx] != {}:
                            if now < (self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps'][_idx] + timing):
                                continue
                        loggingHeartbeat( self, 'Debug', "processKnownDevices -  %s/%s with cluster %s TimeStamps: %s, Timing: %s , Now: %s "
                                %(NWKID, tmpEp, Cluster, self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps'][_idx], timing, now), NWKID)

                loggingHeartbeat( self, 'Debug', "-- -  %s/%s and time to request ReadAttribute for %s" %( NWKID, tmpEp, Cluster ), NWKID)
                func(self, NWKID )
    # if _doReadAttribute or _forceCommandCluster:

    if _mainPowered and (self.pluginconf.pluginConf['pingDevices'] or  _checkHealth):
        if int(time.time()) > (self.ListOfDevices[NWKID]['Stamp']['LastSeen'] + self.pluginconf.pluginConf['pingDevicesFeq'] ) : # Age is above 1 hours by default
            if  len(self.ZigateComm.zigateSendingFIFO) == 0:
                loggingHeartbeat( self, 'Debug', "processKnownDevices -  Ping device %s %s %s - Timing: %s %s %s" \
                    %(NWKID, self.pluginconf.pluginConf['pingDevices'], _checkHealth, int(time.time()), self.ListOfDevices[NWKID]['Stamp']['LastSeen'], self.pluginconf.pluginConf['pingDevicesFeq']), NWKID)
                ReadAttributeRequest_0000_basic( self, NWKID)

    if ( self.HeartbeatCount % LEGRAND_FEATURES ) == 0 :
        if 'Manufacturer Name' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Legrand':
                if self.pluginconf.pluginConf['EnableDimmer']:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'EnableDimmer', 'On')
                else:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'EnableDimmer', 'Off')
        
                if self.pluginconf.pluginConf['LegrandFilPilote']:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'FilPilote', 'On')
                else:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'FilPilote', 'Off')

                if self.pluginconf.pluginConf['EnableLedIfOn']:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'EnableLedIfOn', 'On')
                else:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'EnableLedIfOn', 'Off')

                if self.pluginconf.pluginConf['EnableLedInDark']:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'DetectInDark', 'On')
                else:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'DetectInDark', 'Off')

    # If Attributes not yet discovered, let's do it
    if 'ConfigSource' in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]['ConfigSource'] != 'DeviceConf':
            if 'Attributes List' not in self.ListOfDevices[NWKID]:
                for iterEp in self.ListOfDevices[NWKID]['Ep']:
                    if iterEp == 'ClusterType': continue
                    for iterCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                        if iterCluster in ( 'Type', 'ClusterType', 'ColorMode' ): continue
                        if self.busy  or len(self.ZigateComm.zigateSendingFIFO) > MAX_LOAD_ZIGATE:
                            loggingHeartbeat( self, 'Debug', '-- -- - skip ReadAttribute for now ... system too busy (%s/%s) for %s' 
                                    %(self.busy, len(self.ZigateComm.zigateSendingFIFO), NWKID), NWKID)
                            break # Will do at the next round
                        getListofAttribute( self, NWKID, iterEp, iterCluster)

    # Checking if we have to change the Power On after On/Off
    _skipPowerOn_OnOff = False
    if 'Manufacturer' in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]['Manufacturer'] == '117c':
            _skipPowerOn_OnOff = True
    if 'Manufacturer Name' in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]['Manufacturer Name'] == 'IKEA of Sweden':
            _skipPowerOn_OnOff = True

    #if not _skipPowerOn_OnOff and 'Ep' in self.ListOfDevices[NWKID]:
    #    for iterEp in self.ListOfDevices[NWKID]['Ep']:
    #        # Let's check if we have to change the PowerOn OnOff setting. ( What is the state of PowerOn after a Power On )
    #        if '0006' in self.ListOfDevices[NWKID]['Ep'][iterEp]:
    #            if '4003' in self.ListOfDevices[NWKID]['Ep'][iterEp]['0006']:
    #                if self.pluginconf.pluginConf['PowerOn_OnOff'] == int(self.ListOfDevices[NWKID]['Ep'][iterEp]['0006']['4003']):
    #                    continue
    #                if self.busy or len(self.ZigateComm.zigateSendingFIFO) > MAX_LOAD_ZIGATE:
    #                    continue
    #                loggingHeartbeat( self, 'Log', "-- - Change PowerOn OnOff for device: %s from %s -> %s" \
    #                        %(NWKID, self.ListOfDevices[NWKID]['Ep'][iterEp]['0006']['4003'], self.pluginconf.pluginConf['PowerOn_OnOff']))
    #                setPowerOn_OnOff( self, NWKID, OnOffMode=self.pluginconf.pluginConf['PowerOn_OnOff'] )

    # If corresponding Attributes not present, let's do a Request Node Description
    if 'Manufacturer' not in self.ListOfDevices[NWKID] or \
            'DeviceType' not in self.ListOfDevices[NWKID] or \
            'LogicalType' not in self.ListOfDevices[NWKID] or \
            'PowerSource' not in self.ListOfDevices[NWKID] or \
            'ReceiveOnIdle' not in self.ListOfDevices[NWKID]:
        if not self.busy and  len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
            loggingHeartbeat( self, 'Debug', '-- - skip ReadAttribute for now ... system too busy (%s/%s) for %s' 
                    %(self.busy, len(self.ZigateComm.zigateSendingFIFO), NWKID), NWKID)
            Domoticz.Status("Requesting Node Descriptor for %s" %NWKID)
            sendZigateCmd(self,"0042", str(NWKID) )         # Request a Node Descriptor


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
        if self.ListOfDevices[NWKID]['Model'] in self.DeviceConf:
            knownModel = True
            if not self.pluginconf.pluginConf['capturePairingInfos']:
                status = 'createDB' # Fast track
            else:
                self.ListOfDevices[NWKID]['RIA']=str( RIA + 1 )

        # Patch to make Livolo working
        # https://zigate.fr/forum/topic/livolo-compatible-zigbee/#postid-596
        if self.ListOfDevices[NWKID]['Model'] == 'TI0001':
            if 'MacCapa' in self.ListOfDevices[NWKID]:
                    self.ListOfDevices[NWKID]['MacCapa'] = '8e'
                    self.ListOfDevices[NWKID]['PowerSource'] = 'Main'
                    self.ListOfDevices[NWKID]['LogicalType'] = 'Router'
            livolo_bind( self, NWKID, '06')

    waitForDomoDeviceCreation = False
    if status == "8043": # We have at least receive 1 EndPoint
        reqColorModeAttribute = False
        self.ListOfDevices[NWKID]['RIA']=str( RIA + 1 )

        #for iterEp in self.ListOfDevices[NWKID]['Ep']:
        #    for iterCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
        #        if iterCluster == '0006':
        #            # Toggle
        #            actuators( self, 'On', NWKID, iterEp, 'Switch')
        #            actuators( self, 'Off', NWKID, iterEp, 'Switch')
        #            actuators( self, 'Toggle', NWKID, iterEp, 'Switch')
                    
        # Did we receive the Model Name
        skipModel = False

        if not skipModel or 'Model' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Model'] == {} or self.ListOfDevices[NWKID]['Model'] == '':
                loggingPairing( self, 'Debug', "[%s] NEW OBJECT: %s Request Model Name" %(RIA, NWKID))
                ReadAttributeRequest_0000(self, NWKID, fullScope=False )    # Reuest Model Name
                                                           # And wait 1 cycle
            else: 
                Domoticz.Status("[%s] NEW OBJECT: %s Model Name: %s" %(RIA, NWKID, self.ListOfDevices[NWKID]['Model']))
                # Let's check if this Model is known
                if knownModel:
                    status = 'createDB' # Fast track

        if 'Manufacturer' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Manufacturer'] == {} or self.ListOfDevices[NWKID]['Manufacturer'] == '':
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
                loggingPairing( self, 'Debug', "[%s] NEW OBJECT: %s Request Model Name" %(RIA, NWKID))
                if self.pluginconf.pluginConf['capturePairingInfos']:
                    self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'RA_0000' )
                ReadAttributeRequest_0000(self, NWKID , fullScope=False)    # Reuest Model Name
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
                loggingPairing( self, 'Debug', "[%s] NEW OBJECT: %s Request Model Name" %(RIA, NWKID))
                if self.pluginconf.pluginConf['capturePairingInfos']:
                    self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'RA_0000' )
                ReadAttributeRequest_0000(self, NWKID, fullScope=False )    # Reuest Model Name
        for iterEp in self.ListOfDevices[NWKID]['Ep']:
            Domoticz.Status("[%s] NEW OBJECT: %s Request Simple Descriptor for Ep: %s" %( '-', NWKID, iterEp))
            if self.pluginconf.pluginConf['capturePairingInfos']:
                self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( '0043' )
            sendZigateCmd(self,"0043", str(NWKID)+str(iterEp))
        return

    if knownModel and RIA > 3 and status != 'UNKNOW' and status != 'inDB':
        # We have done several retry to get Ep ...
        loggingPairing( self, 'Debug', "processNotinDB - Try several times to get all informations, let's use the Model now" +str(NWKID) )
        status = 'createDB'

    elif self.ListOfDevices[NWKID]['RIA'] > '4' and status != 'UNKNOW' and status != 'inDB':  # We have done several retry
        Domoticz.Error("[%s] NEW OBJECT: %s Not able to get all needed attributes on time" %(RIA, NWKID))
        self.ListOfDevices[NWKID]['Status']="UNKNOW"
        self.ListOfDevices[NWKID]['ConsistencyCheck']="Bad Pairing"
        Domoticz.Error("processNotinDB - not able to find response from " +str(NWKID) + " stop process at " +str(status) )
        Domoticz.Error("processNotinDB - RIA: %s waitForDomoDeviceCreation: %s, capturePairingInfos: %s Model: %s " \
                %( self.ListOfDevices[NWKID]['RIA'], waitForDomoDeviceCreation, self.pluginconf.pluginConf['capturePairingInfos'], self.ListOfDevices[NWKID]['Model']))
        Domoticz.Error("processNotinDB - Collected Infos are : %s" %(str(self.ListOfDevices[NWKID])))
        self.adminWidgets.updateNotificationWidget( Devices, 'Unable to collect all informations for enrollment of this devices. See Logs' )
        self.CommiSSionning = False
        if self.pluginconf.pluginConf['capturePairingInfos']:
            self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'UNKNOW' )
        writeDiscoveryInfos( self )
        return

    if status in ( 'createDB', '8043' ):
        #We will try to create the device(s) based on the Model , if we find it in DeviceConf or against the Cluster
        if status == '8043' and self.ListOfDevices[NWKID]['RIA'] < '3':     # Let's take one more chance to get Model
            loggingPairing( self, 'Debug', "Too early, let's try to get the Model")
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

            #Don't know why we need as this seems very weird
            if NWKID not in self.ListOfDevices:
                Domoticz.Error("processNotinDBDevices - %s doesn't exist in Post creation widget" %NWKID)
                return
            if 'Ep' not in self.ListOfDevices[NWKID]:
                Domoticz.Error("processNotinDBDevices - %s doesn't have Ep in Post creation widget" %NWKID)
                return

            ###### Post processing : work done after Domoticz Widget creation
                
            if 'ConfigSource' in self.ListOfDevices[NWKID]:
                loggingPairing( self, 'Debug', "Device: %s - Config Source: %s Ep Details: %s" \
                        %(NWKID,self.ListOfDevices[NWKID]['ConfigSource'],str(self.ListOfDevices[NWKID]['Ep'])))

            legrand = False
            if 'Manufacturer Name' in self.ListOfDevices[NWKID]:
                if self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Legrand':
                    legrand = True
            if 'Manufacturer' in self.ListOfDevices[NWKID]:
                if self.ListOfDevices[NWKID]['Manufacturer'] == '1021':
                    legrand = True
            schneider = False
            if 'Manufacturer Name' in self.ListOfDevices[NWKID]:
                if self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Schneider Electric':
                    schneider = True
            if 'Manufacturer' in self.ListOfDevices[NWKID]:
                if self.ListOfDevices[NWKID]['Manufacturer'] == '105e':
                    schneider = True

            # Binding devices
            cluster_to_bind = CLUSTERS_LIST

            if legrand:
                if '0003' not in cluster_to_bind:
                    cluster_to_bind.append( '0003' )
            if schneider:
                if '0003' not in cluster_to_bind:
                    cluster_to_bind.append( '0003' )

            for iterEp in self.ListOfDevices[NWKID]['Ep']:
                for iterBindCluster in cluster_to_bind:      # Binding order is important
                    if iterBindCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                        if legrand:
                            if self.ListOfDevices[NWKID]['Model'] in LEGRAND_REMOTE_SHUTTER:
                                if iterBindCluster not in ( '0001', '0003', '000f' ):
                                    continue
                            if self.ListOfDevices[NWKID]['Model'] in LEGRAND_REMOTE_SWITCHS:
                                if iterBindCluster not in ( '0001', '0003', '000f', '0006', '0008'):
                                    continue

                        if self.pluginconf.pluginConf['capturePairingInfos']:
                            self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'BIND_' + iterEp + '_' + iterBindCluster )

                        loggingPairing( self, 'Log', 'Request a Bind for %s/%s on Cluster %s' %(NWKID, iterEp, iterBindCluster) )
                        if self.pluginconf.pluginConf['doUnbindBind']:
                            unbindDevice( self, self.ListOfDevices[NWKID]['IEEE'], iterEp, iterBindCluster)
                        bindDevice( self, self.ListOfDevices[NWKID]['IEEE'], iterEp, iterBindCluster)

            # 2 Enable Configure Reporting for any applicable cluster/attributes
            if self.pluginconf.pluginConf['capturePairingInfos']:
                self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'PR-CONFIG' )

            processConfigureReporting( self, NWKID )  

            # 3 Read attributes
            for iterEp in self.ListOfDevices[NWKID]['Ep']:
                for iterReadAttrCluster in CLUSTERS_LIST:
                    if iterReadAttrCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                        if iterReadAttrCluster in READ_ATTRIBUTES_REQUEST:
                            if self.pluginconf.pluginConf['capturePairingInfos']:
                                self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'RA_' + iterEp + '_' + iterReadAttrCluster )
                            func = READ_ATTRIBUTES_REQUEST[iterReadAttrCluster][0]
                            func( self, NWKID)

            # In case of Schneider Thermostat, let's do the Write Attribute now.
            if 'Model' in self.ListOfDevices[ NWKID ]:
                if self.ListOfDevices[ NWKID ]['Model'] == 'EH-ZB-RTS':
                    schneider_thermostat( self, NWKID )

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
                    if 'ConfigSource' in self.ListOfDevices[NWKID]:
                        if self.ListOfDevices[NWKID]['ConfigSource'] != 'DeviceConf':
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

            # 4- Create groups if required
            if legrand and self.pluginconf.pluginConf['LegrandGroups'] and self.groupmgt:
                if self.ListOfDevices[NWKID]['Model'] == 'Connected outlet':
                    self.groupmgt.manageLegrandGroups( NWKID, '01', 'Plug')
                elif self.ListOfDevices[NWKID]['Model'] == 'Dimmer switch w/o neutral':
                    self.groupmgt.manageLegrandGroups( NWKID, '01', 'Switch')
                elif self.ListOfDevices[NWKID]['Model'] == 'Micromodule switch':
                    self.groupmgt.manageLegrandGroups( NWKID, '01', 'Switch')

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
        if self.ListOfDevices[NWKID]['RIA'] != '' and self.ListOfDevices[NWKID]['RIA'] != {}:
            RIA = int(self.ListOfDevices[NWKID]['RIA'])
        else:
            RIA = 0
            self.ListOfDevices[NWKID]['RIA'] = '0'
        self.ListOfDevices[NWKID]['Heartbeat']=str(int(self.ListOfDevices[NWKID]['Heartbeat'])+1)

        if status == "failDB":
            entriesToBeRemoved.append( NWKID )

        ########## Known Devices 
        if status == "inDB" and not self.busy: 
            processKnownDevices( self , Devices, NWKID )

        elif status == "Leave":
            # We should then just reconnect the element
            # Nothing to do
            pass

        elif status == "Left":
            # Device has sent a 0x8048 message annoucing its departure (Leave)
            # Most likely we should receive a 0x004d, where the device come back with a new short address
            # For now we will display a message in the log every 1'
            # We might have to remove this entry if the device get not reconnected.
            if (( int(self.ListOfDevices[NWKID]['Heartbeat']) % 36 ) and  int(self.ListOfDevices[NWKID]['Heartbeat']) != 0) == 0:
                if 'ZDeviceName' in self.ListOfDevices[NWKID]:
                    Domoticz.Log("processListOfDevices - Device: %s (%s) is in Status = 'Left' for %s HB" 
                            %(self.ListOfDevices[NWKID]['ZDeviceName'], NWKID, self.ListOfDevices[NWKID]['Heartbeat']))
                else:
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


    if ( self.HeartbeatCount % CONFIGURERPRT_FEQ ) == 0:
        # Trigger Configure Reporting to eligeable devices
        processConfigureReporting( self )

    if self.HeartbeatCount > NETWORK_TOPO_START:
        # Network Topology
        if self.networkmap:
            phase = self.networkmap.NetworkMapPhase()
            if phase == 1:
                Domoticz.Log("Start NetworkMap process")
                self.start_scan( )
            elif phase == 2:
                if self.ZigateComm.loadTransmit() < 1 : # Equal 0
                     self.networkmap.continue_scan( )

    if self.HeartbeatCount > NETWORK_ENRG_START:
        # Network Energy Level
        if self.networkenergy:
            if self.ZigateComm.loadTransmit() < 1: # Equal 0
                self.networkenergy.do_scan()


    return True


