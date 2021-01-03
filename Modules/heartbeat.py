#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: heartbeat.py

    Description: Manage all actions done during the onHeartbeat() call

"""

import Domoticz
import binascii
import time
import datetime
import struct
import json

from Modules.actuators import actuators
from Modules.basicOutputs import  sendZigateCmd,identifyEffect, getListofAttribute
from Modules.readAttributes import READ_ATTRIBUTES_REQUEST, ping_device_with_read_attribute, \
        ReadAttributeRequest_0000, ReadAttributeRequest_0001, ReadAttributeRequest_0006, ReadAttributeRequest_0008, ReadAttributeRequest_0006_0000, ReadAttributeRequest_0006_400x, ReadAttributeRequest_0008_0000,\
        ReadAttributeRequest_0100, ReadAttributeRequest_0101_0000,\
        ReadAttributeRequest_000C, ReadAttributeRequest_0102, ReadAttributeRequest_0102_0008, ReadAttributeRequest_0201, ReadAttributeRequest_0201_0012, ReadAttributeRequest_0204, ReadAttributeRequest_0300,  \
        ReadAttributeRequest_0400, ReadAttributeRequest_0402, ReadAttributeRequest_0403, ReadAttributeRequest_0405, \
        ReadAttributeRequest_0406, ReadAttributeRequest_0500, ReadAttributeRequest_0502, ReadAttributeRequest_0702, ReadAttributeRequest_000f, ReadAttributeRequest_fc01, ReadAttributeRequest_fc21
from Modules.configureReporting import processConfigureReporting
from Modules.legrand_netatmo import  legrandReenforcement
from Modules.blitzwolf import pollingBlitzwolfPower
from Modules.schneider_wiser import schneiderRenforceent, pollingSchneider
from Modules.casaia import pollingCasaia
from Modules.philips import pollingPhilips
from Modules.gledopto import pollingGledopto
from Modules.lumi import setXiaomiVibrationSensitivity
from Modules.tools import removeNwkInList, mainPoweredDevice, ReArrangeMacCapaBasedOnModel, is_time_to_perform_work, getListOfEpForCluster
from Modules.domoTools import timedOutDevice
from Modules.zigateConsts import HEARTBEAT, MAX_LOAD_ZIGATE, CLUSTERS_LIST, LEGRAND_REMOTES, LEGRAND_REMOTE_SHUTTER, LEGRAND_REMOTE_SWITCHS, ZIGATE_EP
from Modules.pairingProcess import processNotinDBDevices
#from Classes.IAS import IAS_Zone_Management
#from Classes.Transport import ZigateTransport
##from Classes.AdminWidgets import AdminWidgets
#from Classes.NetworkMap import NetworkMap
#from Classes.LoggingManagement import LoggingManagement

# Read Attribute trigger: Every 10"
# Configure Reporting trigger: Every 15
# Network Topology start: 15' after plugin start
# Network Energy start: 30' after plugin start
# Legrand re-enforcement: Every 5'

READATTRIBUTE_FEQ =    10 // HEARTBEAT # 10seconds ... 
QUIET_AFTER_START =    60 // HEARTBEAT # Quiet periode after a plugin start
CONFIGURERPRT_FEQ =    30 // HEARTBEAT
LEGRAND_FEATURES =    300 // HEARTBEAT
SCHNEIDER_FEATURES =  300 // HEARTBEAT
NETWORK_TOPO_START =  900 // HEARTBEAT
NETWORK_ENRG_START = 1800 // HEARTBEAT




def attributeDiscovery( self, NwkId ):

        rescheduleAction = False
        # If Attributes not yet discovered, let's do it

        if 'ConfigSource' not in self.ListOfDevices[NwkId]:
            return False

        if self.ListOfDevices[NwkId]['ConfigSource'] == 'DeviceConf':
            return False

        if 'Attributes List' in self.ListOfDevices[NwkId]:
            return False

        for iterEp in self.ListOfDevices[NwkId]['Ep']:
            if iterEp == 'ClusterType': 
                continue
            for iterCluster in self.ListOfDevices[NwkId]['Ep'][iterEp]:
                if iterCluster in ( 'Type', 'ClusterType', 'ColorMode' ): 
                    continue
                if not self.busy and self.ZigateComm.loadTransmit() <= MAX_LOAD_ZIGATE:
                    getListofAttribute( self, NwkId, iterEp, iterCluster)
                else:
                    rescheduleAction = True

        return rescheduleAction

def pollingManufSpecificDevices( self, NwkId):

        POLLING_TABLE_SPECIFICS = {
            '100b':             ( 'Philips',        'pollingPhilips',        pollingPhilips ),
            'Philips':          ( 'Philips',        'pollingPhilips',        pollingPhilips),
            'GLEDOPTO':         ( 'Gledopto',       'pollingGledopto',       pollingGledopto ),
            '105e':             ( 'Schneider',      'pollingSchneider',      pollingSchneider),
            'Schneider':        ( 'Schneider',      'pollingSchneider',      pollingSchneider),
            '_TZ3000_g5xawfcq': ( 'BlitzwolfPower', 'pollingBlitzwolfPower', pollingBlitzwolfPower, ),
            'OWON':             ( 'CasaiaAC201',    'pollingCasaiaAC201',    pollingCasaia, )
        }

        rescheduleAction = False

        devManufCode = devManufName = ''
        if 'Manufacturer' in self.ListOfDevices[NwkId]:
            devManufCode = self.ListOfDevices[NwkId]['Manufacturer']
        if 'Manufacturer Name' in self.ListOfDevices[NwkId]:
            devManufName = self.ListOfDevices[NwkId]['Manufacturer Name']

        brand = func = param = None
        if devManufCode in POLLING_TABLE_SPECIFICS:
            brand, param , func =  POLLING_TABLE_SPECIFICS[ devManufCode ]
        if brand is None and devManufName in POLLING_TABLE_SPECIFICS:
            brand, param , func =  POLLING_TABLE_SPECIFICS[ devManufName ]        

        if brand is None:
            return False

        _HB = int(self.ListOfDevices[NwkId]['Heartbeat'])
        _FEQ = self.pluginconf.pluginConf[ param ] // HEARTBEAT

        if _FEQ and (( _HB % _FEQ ) == 0):
            self.log.logging( "Heartbeat", 'Debug', "++ pollingManufSpecificDevices -  %s Found: %s - %s %s %s" \
                %(NwkId, brand, devManufCode, devManufName, param), NwkId)       
            rescheduleAction = ( rescheduleAction or func( self, NwkId) )

        return rescheduleAction

def pollingDeviceStatus( self, NwkId):
        # """
        # Purpose is to trigger ReadAttrbute 0x0006 and 0x0008 on attribute 0x0000 if applicable
        # """

        if self.busy or self.ZigateComm.loadTransmit() > MAX_LOAD_ZIGATE:
            return True
        self.log.logging( "Heartbeat", 'Debug', "--------> pollingDeviceStatus Device %s" %NwkId, NwkId)
        if len(getListOfEpForCluster( self, NwkId, '0006' )) != 0: 
            ReadAttributeRequest_0006_0000( self, NwkId)
            self.log.logging( "Heartbeat", 'Debug', "++ pollingDeviceStatus -  %s  for ON/OFF" \
                %(NwkId), NwkId)

        if len(getListOfEpForCluster( self, NwkId, '0008' )) != 0: 
            ReadAttributeRequest_0008_0000( self, NwkId)
            self.log.logging( "Heartbeat", 'Debug', "++ pollingDeviceStatus -  %s  for LVLControl" \
                %(NwkId), NwkId)

        if len(getListOfEpForCluster( self, NwkId, '0102' )) != 0: 
            ReadAttributeRequest_0102_0008( self, NwkId)
            self.log.logging( "Heartbeat", 'Debug', "++ pollingDeviceStatus -  %s  for WindowCovering" \
                %(NwkId), NwkId)

        if len(getListOfEpForCluster( self, NwkId, '0101' )) != 0: 
            ReadAttributeRequest_0101_0000( self, NwkId)
            self.log.logging( "Heartbeat", 'Debug', "++ pollingDeviceStatus -  %s  for DoorLock" \
                %(NwkId), NwkId)

        if len(getListOfEpForCluster( self, NwkId, '0201' )) != 0: 
            ReadAttributeRequest_0201_0012( self, NwkId)
            self.log.logging( "Heartbeat", 'Debug', "++ pollingDeviceStatus -  %s  for Thermostat" \
                %(NwkId), NwkId)
        return False

def checkHealth( self, NwkId):
    
        # Checking current state of the this Nwk
        if 'Health' not in self.ListOfDevices[NwkId]:
            self.ListOfDevices[NwkId]['Health'] = ''

        if 'Stamp' not in self.ListOfDevices[NwkId]:
            self.ListOfDevices[NwkId]['Stamp'] = {}
            self.ListOfDevices[NwkId]['Stamp']['LastPing'] = 0
            self.ListOfDevices[NwkId]['Stamp']['LastSeen'] = 0
            self.ListOfDevices[NwkId]['Health'] = 'unknown'

        if 'LastSeen' not in self.ListOfDevices[NwkId]['Stamp']:
            self.ListOfDevices[NwkId]['Stamp']['LastSeen'] = 0
            self.ListOfDevices[NwkId]['Health'] = 'unknown'

        if int(time.time()) > (self.ListOfDevices[NwkId]['Stamp']['LastSeen'] + 21200) : # Age is above 6 hours
            if self.ListOfDevices[NwkId]['Health'] == 'Live':
                if 'ZDeviceName' in self.ListOfDevices[NwkId]:
                    Domoticz.Error("Device Health - %s Nwkid: %s,Ieee: %s , Model: %s seems to be out of the network" \
                        %(self.ListOfDevices[NwkId]['ZDeviceName'], NwkId, self.ListOfDevices[NwkId]['IEEE'], self.ListOfDevices[NwkId]['Model']))
                else:
                    Domoticz.Error("Device Health - Nwkid: %s,Ieee: %s , Model: %s seems to be out of the network" \
                        %(NwkId, self.ListOfDevices[NwkId]['IEEE'], self.ListOfDevices[NwkId]['Model']))
                self.ListOfDevices[NwkId]['Health'] = 'Not seen last 24hours'

        # If device flag as Not Reachable, don't do anything
        if 'Health' in self.ListOfDevices[NwkId]:
            if self.ListOfDevices[NwkId]['Health'] == 'Not Reachable':
                return False

        return True

def pingRetryDueToBadHealth( self, NwkId):

        now = int(time.time())
        # device is on Non Reachable state
        self.log.logging( "Heartbeat", 'Debug', "--------> ping Retry Check %s" %NwkId, NwkId)
        if 'pingDeviceRetry' not in self.ListOfDevices[NwkId]:
                self.ListOfDevices[NwkId]['pingDeviceRetry'] = {'Retry': 0, 'TimeStamp': now}
        if self.ListOfDevices[NwkId]['pingDeviceRetry']['Retry'] == 0:
            return

        if 'Retry' in self.ListOfDevices[NwkId]['pingDeviceRetry'] and 'TimeStamp' not in self.ListOfDevices[NwkId]['pingDeviceRetry']:
            # This could be due to a previous version without TimeStamp
            self.ListOfDevices[NwkId]['pingDeviceRetry']['Retry'] = 0
            self.ListOfDevices[NwkId]['pingDeviceRetry']['TimeStamp'] = now

        lastTimeStamp = self.ListOfDevices[NwkId]['pingDeviceRetry']['TimeStamp']
        retry = self.ListOfDevices[NwkId]['pingDeviceRetry']['Retry']

        self.log.logging( "Heartbeat", 'Debug', "--------> ping Retry Check %s Retry: %s Gap: %s" %(NwkId, retry, now - lastTimeStamp), NwkId)
        # Retry #1
        if retry == 0:
            # First retry in the next cycle if possible
            if self.ZigateComm.loadTransmit() == 0 and now > ( lastTimeStamp + 30 ): # 30s
                self.log.logging( "Heartbeat", 'Debug', "--------> ping Retry 1 Check %s" %NwkId, NwkId)
                self.ListOfDevices[NwkId]['pingDeviceRetry']['Retry'] += 1
                self.ListOfDevices[NwkId]['pingDeviceRetry']['TimeStamp'] = now
                submitPing( self, NwkId)
                return

        # Retry #2
        if retry == 1:
            # Second retry in the next 30"
            if self.ZigateComm.loadTransmit() == 0 and now > ( lastTimeStamp + 120 ): # 30 + 120s
                # Let's retry
                self.log.logging( "Heartbeat", 'Debug', "--------> ping Retry 2 Check %s" %NwkId, NwkId)
                self.ListOfDevices[NwkId]['pingDeviceRetry']['Retry'] += 1
                self.ListOfDevices[NwkId]['pingDeviceRetry']['TimeStamp'] = now
                submitPing( self, NwkId)
                return

        # Retry #3
        if retry == 2:
            # Last retry after 5 minutes
            if self.ZigateComm.loadTransmit() == 0 and now > ( lastTimeStamp + 300): # 30 + 120 + 300
                # Let's retry
                self.log.logging( "Heartbeat", 'Debug', "--------> ping Retry 3 (last) Check %s" %NwkId, NwkId)
                self.ListOfDevices[NwkId]['pingDeviceRetry']['Retry'] += 1
                self.ListOfDevices[NwkId]['pingDeviceRetry']['TimeStamp'] = now
                submitPing( self, NwkId)

def pingDevices( self, NwkId, health, checkHealthFlag, mainPowerFlag):

    if 'pingDeviceRetry' in self.ListOfDevices[NwkId]:
            self.log.logging( "Heartbeat", 'Debug', "------> pinDevices %s health: %s, checkHealth: %s, mainPower: %s, retry: %s" 
            %(NwkId,health, checkHealthFlag, mainPowerFlag, self.ListOfDevices[NwkId]['pingDeviceRetry']['Retry']) , NwkId)
    else:
        self.log.logging( "Heartbeat", 'Debug', "------> pinDevices %s health: %s, checkHealth: %s, mainPower: %s" 
                %(NwkId,health, checkHealthFlag, mainPowerFlag) , NwkId)

    if not mainPowerFlag:
        return

    if not health:
        pingRetryDueToBadHealth(self, NwkId)
        return
    
    if 'LastPing' not in self.ListOfDevices[NwkId]['Stamp']:
        self.ListOfDevices[NwkId]['Stamp']['LastPing'] = 0
    
    lastPing = self.ListOfDevices[NwkId]['Stamp']['LastPing']
    lastSeen = self.ListOfDevices[NwkId]['Stamp']['LastSeen']
    now = int(time.time())

    if checkHealthFlag and now > (lastPing + 60) and self.ZigateComm.loadTransmit() == 0:
        submitPing( self, NwkId)
        return

    self.log.logging( "Heartbeat", 'Debug', "------> pinDevice %s time: %s LastPing: %s LastSeen: %s Freq: %s" \
            %(NwkId, now, lastPing, lastSeen, self.pluginconf.pluginConf['pingDevicesFeq'] ), NwkId) 

    if ( now > ( lastPing + self.pluginconf.pluginConf['pingDevicesFeq'] )) and \
                ( now > ( lastSeen + self.pluginconf.pluginConf['pingDevicesFeq'] )) and \
                    self.ZigateComm.loadTransmit() == 0:

        self.log.logging( "Heartbeat", 'Debug', "------> pinDevice %s time: %s LastPing: %s LastSeen: %s Freq: %s" \
            %(NwkId, now, lastPing, lastSeen, self.pluginconf.pluginConf['pingDevicesFeq'] ), NwkId) 
        
        submitPing( self, NwkId)

def submitPing( self, NwkId):
    # Pinging devices to check they are still Alive
    self.log.logging( "Heartbeat", 'Debug', "------------> call readAttributeRequest %s" %NwkId, NwkId)
    self.ListOfDevices[NwkId]['Stamp']['LastPing'] = int(time.time())
    ping_device_with_read_attribute( self, NwkId)

def processKnownDevices( self, Devices, NWKID ):
    # Begin   
    # Normalize Hearbeat value if needed
    intHB = int( self.ListOfDevices[NWKID]['Heartbeat'])
    if intHB > 0xffff:
        intHB -= 0xfff0
        self.ListOfDevices[NWKID]['Heartbeat'] = str(intHB)

    # Hack bad devices
    ReArrangeMacCapaBasedOnModel( self, NWKID, self.ListOfDevices[NWKID]['MacCapa'])
 
    # Check if this is a Main powered device or Not. Source of information are: MacCapa and PowerSource
    _mainPowered = mainPoweredDevice( self, NWKID)
    _checkHealth = self.ListOfDevices[NWKID]['Health'] == ''
    health = checkHealth( self, NWKID)
 
    # Pinging devices to check they are still Alive
    if self.pluginconf.pluginConf['pingDevices']:
        pingDevices( self, NWKID, health, _checkHealth, _mainPowered)

    # Check if we are in the process of provisioning a new device. If so, just stop
    if self.CommiSSionning:
        return

    # If device flag as Not Reachable, don't do anything
    if not health:
        self.log.logging( "Heartbeat", 'Debug', "processKnownDevices -  %s stop here due to Health %s" \
                %(NWKID, self.ListOfDevices[NWKID]['Health']), NWKID)
        return
        
    # If we reach this step, the device health is Live
    if 'pingDeviceRetry' in self.ListOfDevices[NWKID]: 
        self.log.logging( "Heartbeat", 'Log', "processKnownDevices -  %s recover from Non Reachable" %NWKID, NWKID) 
        del self.ListOfDevices[NWKID]['pingDeviceRetry']

    model = ''
    if 'Model' in self.ListOfDevices[ NWKID ]:
        model = self.ListOfDevices[ NWKID ]['Model']

    enabledEndDevicePolling = False
    if model in self.DeviceConf and 'PollingEnabled' in self.DeviceConf[ model ] and self.DeviceConf[ model ]['PollingEnabled']:
        enabledEndDevicePolling = True

    ## Starting this point, it is ony relevant for Main Powered Devices. 
    # Some battery based end device with ZigBee 30 use polling and can receive commands.
    # We should authporized them for Polling After Action, in order to get confirmation.
    if not _mainPowered and not enabledEndDevicePolling:
       return

    # Action not taken, must be reschedule to next cycle
    rescheduleAction = False

    if self.pluginconf.pluginConf['forcePollingAfterAction'] and (intHB == 1): # HB has been reset to 0 as for a Group command
        # intHB is 1 as if it has been reset, we get +1 in ProcessListOfDevices
        self.log.logging( "Heartbeat", 'Debug', "processKnownDevices -  %s due to intHB %s" %(NWKID, intHB), NWKID)
        rescheduleAction = (rescheduleAction or pollingDeviceStatus( self, NWKID))
        # Priority on getting the status, nothing more to be done!
        return

    # Polling Manufacturer Specific devices ( Philips, Gledopto  ) if applicable
    rescheduleAction = (rescheduleAction or pollingManufSpecificDevices( self, NWKID))

    _doReadAttribute = False
    if self.pluginconf.pluginConf['enableReadAttributes'] or self.pluginconf.pluginConf['resetReadAttributes']:
        if ( intHB % READATTRIBUTE_FEQ ) == 0:
            _doReadAttribute = True

    # Do we need to force ReadAttribute at plugin startup ?
    # If yes, best is probably to have ResetReadAttribute to 1
    if _doReadAttribute:
        self.log.logging( "Heartbeat", 'Debug', "processKnownDevices -  %s intHB: %s _mainPowered: %s doReadAttr: %s" \
                %(NWKID, intHB, _mainPowered, _doReadAttribute ), NWKID)

        # Read Attributes if enabled
        now = int(time.time())   # Will be used to trigger ReadAttributes
        for tmpEp in self.ListOfDevices[NWKID]['Ep']:    
            if tmpEp == 'ClusterType': 
                continue

            for Cluster in READ_ATTRIBUTES_REQUEST:
                if Cluster in ( 'Type', 'ClusterType', 'ColorMode' ): 
                    continue
                if Cluster not in self.ListOfDevices[NWKID]['Ep'][tmpEp]:
                    continue

                if 'Model' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Model'] == 'lumi.ctrl_neutral1' and tmpEp != '02': # All Eps other than '02' are blacklisted
                        continue
                    if  self.ListOfDevices[NWKID]['Model'] == 'lumi.ctrl_neutral2' and tmpEp not in ( '02' , '03' ):
                        continue

                if  (self.busy  or self.ZigateComm.loadTransmit() > MAX_LOAD_ZIGATE):
                    self.log.logging( "Heartbeat", 'Debug', '--  -  %s skip ReadAttribute for now ... system too busy (%s/%s)' 
                            %(NWKID, self.busy, self.ZigateComm.loadTransmit()), NWKID)
                    rescheduleAction = True
                    continue # Do not break, so we can keep all clusters on the same states
   
                func = READ_ATTRIBUTES_REQUEST[Cluster][0]
                # For now it is a hack, but later we might put all parameters 
                if READ_ATTRIBUTES_REQUEST[Cluster][1] in self.pluginconf.pluginConf:
                    timing =  self.pluginconf.pluginConf[ READ_ATTRIBUTES_REQUEST[Cluster][1] ]
                else:
                    Domoticz.Error("processKnownDevices - missing timing attribute for Cluster: %s - %s" \
                            %(Cluster,  READ_ATTRIBUTES_REQUEST[Cluster][1]))
                    continue
 
                # Let's check the timing
                if not is_time_to_perform_work(self, 'ReadAttributes', NWKID, tmpEp, Cluster, now, timing ):
                    continue

                self.log.logging( "Heartbeat", 'Debug', "-- -  %s/%s and time to request ReadAttribute for %s" \
                        %( NWKID, tmpEp, Cluster ), NWKID)

                func(self, NWKID )

    if ( intHB % 900) == 0:
        # Checking PowerOn after OnOff setting ( 0x4003 )
        if 'Manufacturer Name' in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]['Manufacturer Name'] in ( 'Philips', 'IKEA of Sweden', 'Legrand'):
            for ep in self.ListOfDevices[NWKID]['Ep']:
                if '0006' in self.ListOfDevices[NWKID]['Ep'][ep]:
                    if '4003' not in self.ListOfDevices[NWKID]['Ep'][ep]['0006']:
                        ReadAttributeRequest_0006_400x( self, NWKID )

    # Reenforcement of Legrand devices options if required
    if ( self.HeartbeatCount % LEGRAND_FEATURES ) == 0 :
        rescheduleAction = ( rescheduleAction or legrandReenforcement( self, NWKID))

    # Call Schneider Reenforcement if needed
    if self.pluginconf.pluginConf['reenforcementWiser'] and \
            ( self.HeartbeatCount % self.pluginconf.pluginConf['reenforcementWiser'] ) == 0 :
        rescheduleAction = ( rescheduleAction or schneiderRenforceent(self, NWKID))

    # Do Attribute Disocvery if needed
    if not enabledEndDevicePolling and ( intHB % 1800) == 0:
        rescheduleAction = ( rescheduleAction or attributeDiscovery( self, NWKID ) )

    # If corresponding Attributes not present, let's do a Request Node Description
    if not enabledEndDevicePolling and ( intHB % 1800) == 0:
        req_node_descriptor = False
        if 'Manufacturer' not in self.ListOfDevices[NWKID] or \
                'DeviceType' not in self.ListOfDevices[NWKID] or \
                'LogicalType' not in self.ListOfDevices[NWKID] or \
                'PowerSource' not in self.ListOfDevices[NWKID] or \
                'ReceiveOnIdle' not in self.ListOfDevices[NWKID]:
            req_node_descriptor = True
        if 'Manufacturer'  in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Manufacturer'] == '':
                req_node_descriptor = True
    
        if req_node_descriptor and not self.busy and  self.ZigateComm.loadTransmit() <= MAX_LOAD_ZIGATE:
            self.log.logging( "Heartbeat", 'Debug', '-- - skip ReadAttribute for now ... system too busy (%s/%s) for %s' 
                    %(self.busy, self.ZigateComm.loadTransmit(), NWKID), NWKID)
            Domoticz.Status("Requesting Node Descriptor for %s" %NWKID)

            sendZigateCmd(self,"0042", str(NWKID), ackIsDisabled = True )         # Request a Node Descriptor

    if rescheduleAction and intHB != 0: # Reschedule is set because Zigate was busy or Queue was too long to process
        self.ListOfDevices[NWKID]['Heartbeat'] = str( intHB - 1 ) # So next round it trigger again

    return

def processListOfDevices( self , Devices ):
    # Let's check if we do not have a command in TimeOut

    #self.ZigateComm.checkTOwaitFor()
    entriesToBeRemoved = []

    for NWKID in list( self.ListOfDevices.keys() ):
        if NWKID in ('ffff', '0000'): 
            continue

        # If this entry is empty, then let's remove it .
        if len(self.ListOfDevices[NWKID]) == 0:
            self.log.logging( "Heartbeat", 'Debug', "Bad devices detected (empty one), remove it, adr:" + str(NWKID), NWKID)
            entriesToBeRemoved.append( NWKID )
            continue
            
        status = self.ListOfDevices[NWKID]['Status']
        if self.ListOfDevices[NWKID]['RIA'] != '' and self.ListOfDevices[NWKID]['RIA'] != {}:
            RIA = int(self.ListOfDevices[NWKID]['RIA'])
        else:
            RIA = 0
            self.ListOfDevices[NWKID]['RIA'] = '0'

        self.ListOfDevices[NWKID]['Heartbeat']=str(int(self.ListOfDevices[NWKID]['Heartbeat']) + 1)

        if status == "failDB":
            entriesToBeRemoved.append( NWKID )
            continue

        ########## Known Devices 
        if status == "inDB":
            processKnownDevices( self , Devices, NWKID )

        elif status == "Leave":
            # We should then just reconnect the element
            # Nothing to do
            pass

        elif status == "Left":
            timedOutDevice( self, Devices, NwkId = NWKID)
            # Device has sentt a 0x8048 message annoucing its departure (Leave)
            # Most likely we should receive a 0x004d, where the device come back with a new short address
            # For now we will display a message in the log every 1'
            # We might have to remove this entry if the device get not reconnected.
            if (( int(self.ListOfDevices[NWKID]['Heartbeat']) % 36 ) and  int(self.ListOfDevices[NWKID]['Heartbeat']) != 0) == 0:
                if 'ZDeviceName' in self.ListOfDevices[NWKID]:
                    self.log.logging( "Heartbeat", 'Debug', "processListOfDevices - Device: %s (%s) is in Status = 'Left' for %s HB" 
                            %(self.ListOfDevices[NWKID]['ZDeviceName'], NWKID, self.ListOfDevices[NWKID]['Heartbeat']), NWKID)
                else:
                    self.log.logging( "Heartbeat", 'Debug', "processListOfDevices - Device: (%s) is in Status = 'Left' for %s HB" 
                            %( NWKID, self.ListOfDevices[NWKID]['Heartbeat']), NWKID)
                # Let's check if the device still exist in Domoticz
                for Unit in Devices:
                    if self.ListOfDevices[NWKID]['IEEE'] == Devices[Unit].DeviceID:
                        self.log.logging( "Heartbeat", 'Debug', "processListOfDevices - %s  is still connected cannot remove. NwkId: %s IEEE: %s " \
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
    
    for iterDevToBeRemoved in entriesToBeRemoved:
        if 'IEEE' in self.ListOfDevices[iterDevToBeRemoved]:
            _ieee = self.ListOfDevices[iterDevToBeRemoved]['IEEE']
            del _ieee
        del self.ListOfDevices[iterDevToBeRemoved]

    if self.CommiSSionning or self.busy:
        self.log.logging( "Heartbeat", 'Debug', "Skip LQI, ConfigureReporting and Networkscan du to Busy state: Busy: %s, Enroll: %s" %(self.busy, self.CommiSSionning))
        return  # We don't go further as we are Commissioning a new object and give the prioirty to it

    if self.pluginconf.pluginConf['reenforceConfigureReporting'] and (self.HeartbeatCount > QUIET_AFTER_START) and (( self.HeartbeatCount % CONFIGURERPRT_FEQ ) )== 0:
        # Trigger Configure Reporting to eligeable devices
        processConfigureReporting( self )

    # Network Topology management
    #if (self.HeartbeatCount > QUIET_AFTER_START) and (self.HeartbeatCount > NETWORK_TOPO_START):
    #    self.log.logging( "Heartbeat", 'Debug', "processListOfDevices Time for Network Topology")
        # Network Topology
    if self.networkmap:
        phase = self.networkmap.NetworkMapPhase()
        self.log.logging( "Heartbeat", 'Debug', "processListOfDevices checking Topology phase: %s" %phase)
        #if phase == 0:
        #    self.networkmap.start_scan( )
        if phase == 1:
            self.log.logging( "Heartbeat", 'Status', "Starting Network Topology")
            self.networkmap.start_scan( )
        elif phase == 2:
            self.log.logging( "Heartbeat", 'Debug', "processListOfDevices Topology scan is possible %s" %self.ZigateComm.loadTransmit())
            if self.ZigateComm.loadTransmit() <= MAX_LOAD_ZIGATE:
                    self.networkmap.continue_scan( )

    #if (self.HeartbeatCount > QUIET_AFTER_START) and (self.HeartbeatCount > NETWORK_ENRG_START):
    #    # Network Energy Level
    if self.networkenergy:
        if self.ZigateComm.loadTransmit() <= MAX_LOAD_ZIGATE:
            self.networkenergy.do_scan()

    self.log.logging( "Heartbeat", 'Debug', "processListOfDevices END with HB: %s, Busy: %s, Enroll: %s, Load: %s" \
        %(self.HeartbeatCount, self.busy, self.CommiSSionning, self.ZigateComm.loadTransmit() ))
    return
