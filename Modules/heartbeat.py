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
        setPowerOn_OnOff, \
        scene_membership_request, \
        ReadAttributeRequest_0000_basic, \
        ReadAttributeRequest_0000, ReadAttributeRequest_0001, ReadAttributeRequest_0006, ReadAttributeRequest_0008, \
        ReadAttributeRequest_0100, \
        ReadAttributeRequest_000C, ReadAttributeRequest_0102, ReadAttributeRequest_0201, ReadAttributeRequest_0204, ReadAttributeRequest_0300,  \
        ReadAttributeRequest_0400, ReadAttributeRequest_0402, ReadAttributeRequest_0403, ReadAttributeRequest_0405, \
        ReadAttributeRequest_0406, ReadAttributeRequest_0500, ReadAttributeRequest_0502, ReadAttributeRequest_0702, ReadAttributeRequest_000f, ReadAttributeRequest_fc01
from Modules.legrand_netatmo import legrand_fc01
from Modules.schneider_wiser import schneider_thermostat_behaviour, schneider_fip_mode

from Modules.tools import removeNwkInList, loggingPairing, loggingHeartbeat, mainPoweredDevice
from Modules.domoticz import CreateDomoDevice, timedOutDevice
from Modules.zigateConsts import HEARTBEAT, MAX_LOAD_ZIGATE, CLUSTERS_LIST, LEGRAND_REMOTES, LEGRAND_REMOTE_SHUTTER, LEGRAND_REMOTE_SWITCHS
from Modules.pairingProcess import processNotinDBDevices

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
READ_ATTR_COMMANDS = ( '0006', '0201')

# Read Attribute trigger: Every 10"
# Configure Reporting trigger: Every 15
# Network Topology start: 15' after plugin start
# Network Energy start: 30' after plugin start
# Legrand re-enforcement: Every 5'

READATTRIBUTE_FEQ =    10 // HEARTBEAT # 10seconds ... 
CONFIGURERPRT_FEQ =    30 // HEARTBEAT
LEGRAND_FEATURES =    300 // HEARTBEAT
SCHNEIDER_FEATURES =  300 // HEARTBEAT
NETWORK_TOPO_START =  900 // HEARTBEAT
NETWORK_ENRG_START = 1800 // HEARTBEAT

def processKnownDevices( self, Devices, NWKID ):

    # Normalize Hearbeat value if needed
    intHB = int( self.ListOfDevices[NWKID]['Heartbeat'])
    if intHB > 0xffff:
        intHB -= 0xfff0
        self.ListOfDevices[NWKID]['Heartbeat'] = intHB

    # Check if this is a Main powered device or Not. Source of information are: MacCapa and PowerSource
    _mainPowered = mainPoweredDevice( self, NWKID)

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
    if int(time.time()) > (self.ListOfDevices[NWKID]['Stamp']['LastSeen'] + 21200) : # Age is above 6 hours
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

    _doReadAttribute = False
    _forceCommandCluster = False

    if (intHB == 1) and self.pluginconf.pluginConf['forcePollingAfterAction']: # Most-likely Heartbeat has been reset to 0 as for a Group command
        loggingHeartbeat( self, 'Debug', "processKnownDevices -  %s due to intHB %s" %(NWKID, intHB), NWKID)
        _forceCommandCluster = True

    ## Starting this point, it is ony relevant for Main Powered Devices.
    #  except if _forceCommandCluster has been enabled.
    if not _mainPowered and not _forceCommandCluster:
        return

    # Action not taken, must be reschedule to next cycle
    rescheduleAction = False

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
                    #if self.ListOfDevices[NWKID]['Model'] == 'TI0001':
                    #    # Don't do it for Livolo
                    #    continue
                    if self.ListOfDevices[NWKID]['Model'] == 'lumi.ctrl_neutral1' and tmpEp != '02': # All Eps other than '02' are blacklisted
                        continue
                    if  self.ListOfDevices[NWKID]['Model'] == 'lumi.ctrl_neutral2' and tmpEp not in ( '02' , '03' ):
                        continue

                if _forceCommandCluster and not _doReadAttribute:
                    # Force Majeur
                    if ( intHB == 1 and _mainPowered and Cluster in READ_ATTR_COMMANDS ) or \
                          ( intHB == 1 and not _mainPowered and Cluster in ( '0001', '0201') ) :
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
                    rescheduleAction = True
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
    
    if _mainPowered and (self.pluginconf.pluginConf['pingDevices'] or  _checkHealth):
        if int(time.time()) > (self.ListOfDevices[NWKID]['Stamp']['LastSeen'] + self.pluginconf.pluginConf['pingDevicesFeq'] ) : # Age is above 1 hours by default
            if  len(self.ZigateComm.zigateSendingFIFO) == 0:
                loggingHeartbeat( self, 'Debug', "processKnownDevices -  Ping device %s %s %s - Timing: %s %s %s" \
                    %(NWKID, self.pluginconf.pluginConf['pingDevices'], _checkHealth, int(time.time()), self.ListOfDevices[NWKID]['Stamp']['LastSeen'], self.pluginconf.pluginConf['pingDevicesFeq']), NWKID)
                #sendZigateCmd(self ,'0041', '02' + NWKID + '00' + '01' )
                ReadAttributeRequest_0000_basic( self, NWKID)

    if ( self.HeartbeatCount % LEGRAND_FEATURES ) == 0 :
        if 'Manufacturer Name' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Legrand':
                if self.pluginconf.pluginConf['EnableDimmer']:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'EnableDimmer', 'On')
                    else:
                        rescheduleAction = True
                else:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'EnableDimmer', 'Off')
                    else:
                        rescheduleAction = True
        
                if self.pluginconf.pluginConf['LegrandFilPilote']:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'FilPilote', 'On')
                    else:
                        rescheduleAction = True
                else:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'FilPilote', 'Off')
                    else:
                        rescheduleAction = True

                if self.pluginconf.pluginConf['EnableLedIfOn']:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'EnableLedIfOn', 'On')
                    else:
                        rescheduleAction = True
                else:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'EnableLedIfOn', 'Off')
                    else:
                        rescheduleAction = True

                if self.pluginconf.pluginConf['EnableLedInDark']:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'EnableLedInDark', 'On')
                    else:
                        rescheduleAction = True
                else:
                    if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                        legrand_fc01( self, NWKID, 'EnableLedInDark', 'Off')
                    else:
                        rescheduleAction = True

    if ( self.HeartbeatCount % SCHNEIDER_FEATURES ) == 0 :
        if 'Schneider Wiser' in self.ListOfDevices[NWKID]:
            if 'HACT Mode' in self.ListOfDevices[NWKID]['Schneider Wiser']:
                if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                    schneider_thermostat_behaviour( self, NKWID, self.ListOfDevices[NWKID]['Schneider Wiser']['HACT Mode'])
                else:
                    rescheduleAction = True
            if 'HACT FIP Mode' in self.ListOfDevices[NWKID]['Schneider Wiser']:
                if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                    schneider_fip_mode( self, NWKID,  self.ListOfDevices[NWKID]['Schneider Wiser']['HACT FIP Mode'])
                else:
                    rescheduleAction = True

    # If Attributes not yet discovered, let's do it
    if 'ConfigSource' in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]['ConfigSource'] != 'DeviceConf':
            if 'Attributes List' not in self.ListOfDevices[NWKID]:
                for iterEp in self.ListOfDevices[NWKID]['Ep']:
                    if iterEp == 'ClusterType': continue
                    for iterCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                        if iterCluster in ( 'Type', 'ClusterType', 'ColorMode' ): continue
                        if not self.busy and len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
                            loggingHeartbeat( self, 'Debug', '-- -- - skip ReadAttribute for now ... system too busy (%s/%s) for %s' 
                                    %(self.busy, len(self.ZigateComm.zigateSendingFIFO), NWKID), NWKID)
                            getListofAttribute( self, NWKID, iterEp, iterCluster)
                        else:
                            rescheduleAction = True

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
    if ( intHB % 1800) == 0:
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
    
        if req_node_descriptor and not self.busy and  len(self.ZigateComm.zigateSendingFIFO) <= MAX_LOAD_ZIGATE:
            loggingHeartbeat( self, 'Debug', '-- - skip ReadAttribute for now ... system too busy (%s/%s) for %s' 
                    %(self.busy, len(self.ZigateComm.zigateSendingFIFO), NWKID), NWKID)
            Domoticz.Status("Requesting Node Descriptor for %s" %NWKID)
            sendZigateCmd(self,"0042", str(NWKID) )         # Request a Node Descriptor

    if rescheduleAction and intHB != 0: # Reschedule is set because Zigate was busy or Queue was too long to process
        self.ListOfDevices[NWKID]['Heartbeat'] = str( intHB - 1 ) # So next round it trigger again

    return

def processListOfDevices( self , Devices ):
    # Let's check if we do not have a command in TimeOut

    self.ZigateComm.checkTOwaitFor()
    entriesToBeRemoved = []

    for NWKID in list( self.ListOfDevices.keys() ):
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
            timedOutDevice( self, Devices, NwkId = NWKID)
            # Device has sentt a 0x8048 message annoucing its departure (Leave)
            # Most likely we should receive a 0x004d, where the device come back with a new short address
            # For now we will display a message in the log every 1'
            # We might have to remove this entry if the device get not reconnected.
            if (( int(self.ListOfDevices[NWKID]['Heartbeat']) % 36 ) and  int(self.ListOfDevices[NWKID]['Heartbeat']) != 0) == 0:
                if 'ZDeviceName' in self.ListOfDevices[NWKID]:
                    loggingHeartbeat( self, 'Debug', "processListOfDevices - Device: %s (%s) is in Status = 'Left' for %s HB" 
                            %(self.ListOfDevices[NWKID]['ZDeviceName'], NWKID, self.ListOfDevices[NWKID]['Heartbeat']), NWKID)
                else:
                    loggingHeartbeat( self, 'Debug', "processListOfDevices - Device: (%s) is in Status = 'Left' for %s HB" 
                            %( NWKID, self.ListOfDevices[NWKID]['Heartbeat']), NWKID)
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


