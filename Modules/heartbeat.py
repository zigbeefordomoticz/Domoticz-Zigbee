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
import queue

from Modules.output import  sendZigateCmd,  \
        processConfigureReporting, identifyEffect, setXiaomiVibrationSensitivity, NwkMgtUpdReq, \
        bindDevice, getListofAttribute, \
        ReadAttributeRequest_Ack,  \
        ReadAttributeRequest_0000, ReadAttributeRequest_0001, ReadAttributeRequest_0006, ReadAttributeRequest_0008, \
        ReadAttributeRequest_000C, ReadAttributeRequest_0201, ReadAttributeRequest_0300,  \
        ReadAttributeRequest_0400, ReadAttributeRequest_0402, ReadAttributeRequest_0403, ReadAttributeRequest_0405, \
        ReadAttributeRequest_0406, ReadAttributeRequest_0702

from Modules.tools import removeNwkInList
from Modules.domoticz import CreateDomoDevice
from Modules.LQI import LQIcontinueScan
from Modules.consts import HEARTBEAT

from Classes.IAS import IAS_Zone_Management
from Classes.Transport import ZigateTransport
from Classes.AdminWidgets import AdminWidgets


def processKnownDevices( self, Devices, NWKID ):

    if self.CommiSSionning: # We have a commission in progress, skip it.
        return

    intHB = int( self.ListOfDevices[NWKID]['Heartbeat'])
    # Checking Time stamps
    if (intHB == 2) or intHB % ( 1800 // HEARTBEAT) == 0:
        if  'PowerSource' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['PowerSource'] == 'Battery': 
                if 'Stamp' in self.ListOfDevices[NWKID]:
                    if 'Time' in self.ListOfDevices[NWKID]['Stamp']:
                        lastShow = time.mktime(time.strptime(self.ListOfDevices[NWKID]['Stamp']['Time'],'%Y-%m-%d %H:%M:%S'))
                        delta = int(time.time() - lastShow)
             
                        if delta > 7200:
                            IEEE = self.ListOfDevices[NWKID]['IEEE']
                            unit = [x for x in Devices if Devices[x].DeviceID == IEEE ]
                            if len(unit) > 1:
                                unit = unit[0]
                                Domoticz.Log("%s - Last Update from Battery device was: %s --> %s ago (More than 2 hours) %s" \
                                    %( Devices[unit].Name, self.ListOfDevices[NWKID]['Stamp']['Time'], 
                                    datetime.datetime.fromtimestamp(delta).strftime('%H:%M:%S'), delta))

    # Check if Node Descriptor was run ( this could not be the case on early version)

    if  self.HeartbeatCount == ( 28 // HEARTBEAT):
        if 'PowerSource' not in self.ListOfDevices[NWKID]:  # Looks like PowerSource is not 
                                                            # available, let's request a Node Descriptor
            sendZigateCmd(self,"0042", str(NWKID) )         # Request a Node Descriptor

    if  self.HeartbeatCount == ( 56 // HEARTBEAT):
        if 'PowerSource' in self.ListOfDevices[NWKID]:
            if (self.ListOfDevices[NWKID]['PowerSource']) == 'Main':
                if 'Attributes List' not in  self.ListOfDevices[NWKID]:
                    for iterEp in self.ListOfDevices[NWKID]['Ep']:
                        for iterCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                            if iterCluster in ( 'Type', 'ClusterType', 'ColorMode' ): continue
                            getListofAttribute( self, NWKID, iterEp, iterCluster)

    # Ping each device, even the battery one. It will make at least the route up-to-date
    #if ( intHB % ( 3000 // HEARTBEAT)) == 0:
    #    ReadAttributeRequest_Ack(self, NWKID)

    READ_ATTRIBUTES_REQUEST = {  
        # Cluster : ( ReadAttribute function, Frequency )
        '0000' : ( ReadAttributeRequest_0000, 43200 ),
        '0001' : ( ReadAttributeRequest_0001, 43200 ),
        '0006' : ( ReadAttributeRequest_0006, 900 ),
        '0008' : ( ReadAttributeRequest_0008, 900 ),
        '000C' : ( ReadAttributeRequest_000C, 3600 ),
        '0201' : ( ReadAttributeRequest_0201, 900 ),
        '0300' : ( ReadAttributeRequest_0300, 900 ),
        '0400' : ( ReadAttributeRequest_0400, 900 ),
        '0402' : ( ReadAttributeRequest_0402, 900 ),
        '0403' : ( ReadAttributeRequest_0403, 900 ),
        '0405' : ( ReadAttributeRequest_0405, 900 ),
        '0406' : ( ReadAttributeRequest_0406, 900 ),
        '0702' : ( ReadAttributeRequest_0702, 900 ),
        }

    now = int(time.time())   # Will be used to trigger ReadAttributes
    if ( intHB % (30 // HEARTBEAT)) == 0 :
        for tmpEp in self.ListOfDevices[NWKID]['Ep']:    
            if tmpEp == 'ClusterType': continue
            for Cluster in READ_ATTRIBUTES_REQUEST:
                if Cluster not in self.ListOfDevices[NWKID]['Ep'][tmpEp]:
                    continue

                if Cluster in ( '0000' ) and (intHB != ( 120 // HEARTBEAT)):
                    continue    # Just does it at plugin start

                if 'PowerSource' in self.ListOfDevices[NWKID]:
                    if (self.ListOfDevices[NWKID]['PowerSource']) != 'Main':
                        continue

                if 'MacCapa' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['MacCapa'] != '8e': # Not a Main Powered 
                        continue

                if self.busy  or len(self.ZigateComm._normalQueue) > 2:
                    Domoticz.Debug('processKnownDevices - skip ReadAttribute for now ... system too busy (%s/%s) for %s' 
                            %(self.busy, len(self.ZigateComm._normalQueue), NWKID))
                    break # Will do at the next round

                func = READ_ATTRIBUTES_REQUEST[Cluster][0]
                timing = READ_ATTRIBUTES_REQUEST[Cluster][1]
                if 'ReadAttributes' not in self.ListOfDevices[NWKID]:
                    self.ListOfDevices[NWKID]['ReadAttributes'] = {}
                    self.ListOfDevices[NWKID]['ReadAttributes']['Ep'] = {}
                if 'TimeStamps' in self.ListOfDevices[NWKID]['ReadAttributes'] :
                    _idx = tmpEp + '-' + str(Cluster)
                    if _idx in self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps']:
                        Domoticz.Debug("processKnownDevices - processing %s with cluster %s TimeStamps: %s, Timing: %s , Now: %s "
                                %(NWKID, Cluster, self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps'][_idx], timing, now))
                        if self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps'][_idx] != {}:
                            if now > (self.ListOfDevices[NWKID]['ReadAttributes']['TimeStamps'][_idx] + timing):
                                Domoticz.Debug("processKnownDevices - %s It's time to Request ReadAttribute for %s/%s" %( NWKID, tmpEp, Cluster ))
                                func(self, NWKID )
                        else:
                            Domoticz.Debug("processKnownDevices - 1: %s Request ReadAttribute for %s/%s" %( NWKID, tmpEp, Cluster ))
                            func(self, NWKID )
                    else:
                        Domoticz.Debug("processKnownDevices - 2: %s Request ReadAttribute for %s/%s" %( NWKID, tmpEp, Cluster ))
                        func(self, NWKID )
                else:
                    Domoticz.Debug("processKnownDevices - 3: %s Request ReadAttribute for %s/%s" %( NWKID, tmpEp, Cluster ))
                    func(self, NWKID )
    
def processNotinDBDevices( self, Devices, NWKID , status , RIA ):

    # Starting V 4.1.x
    # 0x0043 / List of EndPoints is requested at the time we receive the End Device Annocement
    # 0x0045 / EndPoint Description is requested at the time we recice the List of EPs.
    # In case Model is defined and is in DeviceConf, we will short cut the all process and go to the Widget creation
    if status == 'UNKNOW':
        return

    HB_ = int(self.ListOfDevices[NWKID]['Heartbeat'])
    Domoticz.Debug("processNotinDBDevices - NWKID: %s, Status: %s, RIA: %s, HB_: %s " %(NWKID, status, RIA, HB_))
    Domoticz.Status("[%s] NEW OBJECT: %s Model Name: %s" %(RIA, NWKID, self.ListOfDevices[NWKID]['Model']))

    if status in ( '004d', '0043', '0045', '8045', '8043') and 'Model' in self.ListOfDevices[NWKID]:
        Domoticz.Status("[%s] NEW OBJECT: %s Model Name: %s" %(RIA, NWKID, self.ListOfDevices[NWKID]['Model']))
        if self.ListOfDevices[NWKID]['Model'] != {}:
            Domoticz.Status("[%s] NEW OBJECT: %s Model Name: %s" %(RIA, NWKID, self.ListOfDevices[NWKID]['Model']))
            # Let's check if this Model is known
            if 'Model' in self.ListOfDevices[NWKID]:
                if self.ListOfDevices[NWKID]['Model'] in self.DeviceConf:
                    if not self.pluginconf.allowStoreDiscoveryFrames:
                        status = 'createDB' # Fast track
    else:
        return

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
                if self.ListOfDevices[NWKID]['Model'] in self.DeviceConf:
                    status = 'createDB' # Fast track

        if 'Manufacturer' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Manufacturer'] == {}:
                Domoticz.Status("[%s] NEW OBJECT: %s Request Node Descriptor" %(RIA, NWKID))
                sendZigateCmd(self,"0042", str(NWKID))     # Request a Node Descriptor
            else:
                Domoticz.Debug("[%s] NEW OBJECT: %s Model Name: %s" %(RIA, NWKID, self.ListOfDevices[NWKID]['Manufacturer']))

        for iterEp in self.ListOfDevices[NWKID]['Ep']:
            #IAS Zone
            if '0500' in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                # We found a Cluster 0x0500 IAS. May be time to start the IAS Zone process
                Domoticz.Status("[%s] NEW OBJECT: %s 0x%04s - IAS Zone controler setting" \
                        %( RIA, NWKID, status))
                self.iaszonemgt.IASZone_triggerenrollement( NWKID, iterEp)

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
            ReadAttributeRequest_0300(self, NWKID )
            if  self.ListOfDevices[NWKID]['RIA'] < '2':
                return
    # end if status== "8043"

    # Timeout management
    if (status == "004d" or status == "0045") and HB_ > 2 and status != 'createDB':
        Domoticz.Status("[%s] NEW OBJECT: %s TimeOut in %s restarting at 0x004d" %(RIA, NWKID, status))
        self.ListOfDevices[NWKID]['RIA']=str( RIA + 1 )
        self.ListOfDevices[NWKID]['Heartbeat']="0"
        self.ListOfDevices[NWKID]['Status']="0045"
        if 'Model' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Model'] == {}:
                Domoticz.Status("[%s] NEW OBJECT: %s Request Model Name" %(RIA, NWKID))
                ReadAttributeRequest_0000(self, NWKID )    # Reuest Model Name
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
                ReadAttributeRequest_0000(self, NWKID )    # Reuest Model Name
        for iterEp in self.ListOfDevices[NWKID]['Ep']:
            Domoticz.Status("[%s] NEW OBJECT: %s Request Simple Descriptor for Ep: %s" %( '-', NWKID, iterEp))
            sendZigateCmd(self,"0043", str(NWKID)+str(iterEp))
        return

    if self.ListOfDevices[NWKID]['RIA'] > '4' and status != 'UNKNOW' and status != 'inDB':  # We have done several retry
        Domoticz.Status("[%s] NEW OBJECT: %s Not able to get all needed attributes on time" %(RIA, NWKID))
        self.ListOfDevices[NWKID]['Status']="UNKNOW"
        Domoticz.Log("processNotinDB - not able to find response from " +str(NWKID) + " stop process at " +str(status) )
        Domoticz.Log("processNotinDB - RIA: %s waitForDomoDeviceCreation: %s, allowStoreDiscoveryFrames: %s Model: %s " \
                %( self.ListOfDevices[NWKID]['RIA'], waitForDomoDeviceCreation, self.pluginconf.allowStoreDiscoveryFrames, self.ListOfDevices[NWKID]['Model']))
        Domoticz.Log("processNotinDB - Collected Infos are : %s" %(str(self.ListOfDevices[NWKID])))
        self.adminWidgets.updateNotificationWidget( Devices, 'Unable to collect all informations for enrollment of this devices. See Logs' )
        self.CommiSSionning = False
        return

    if status in ( 'createDB', '8043' ):
        #We will try to create the device(s) based on the Model , if we find it in DeviceConf or against the Cluster

        if status == '8043' and self.ListOfDevices[NWKID]['RIA'] < '3':     # Let's take one more chance to get Model
            Domoticz.Log("Too early, let's try to get the Model")
            return

        Domoticz.Status("[%s] NEW OBJECT: %s Trying to create Domoticz device(s)" %(RIA, NWKID))

        IsCreated=False
        # Let's check if the IEEE is not known in Domoticz
        for x in Devices:
            if self.ListOfDevices[NWKID].get('IEEE'):
                if Devices[x].DeviceID == str(self.ListOfDevices[NWKID]['IEEE']):
                    if self.pluginconf.allowForceCreationDomoDevice == 1:
                        Domoticz.Log("processNotinDBDevices - Devices already exist. "  + Devices[x].Name + " with " + str(self.ListOfDevices[NWKID]) )
                        Domoticz.Log("processNotinDBDevices - ForceCreationDevice enable, we continue")
                    else:
                        IsCreated = True
                        Domoticz.Error("processNotinDBDevices - Devices already exist. "  + Devices[x].Name + " with " + str(self.ListOfDevices[NWKID]) )
                        Domoticz.Error("processNotinDBDevices - Please cross check the consistency of the Domoticz and Plugin database.")
                        break

        if IsCreated == False:
            Domoticz.Debug("processNotinDBDevices - ready for creation: %s" %self.ListOfDevices[NWKID])
            CreateDomoDevice(self, Devices, NWKID)

            # Post creation widget
            Domoticz.Log("Device: %s - Config Source: %s Ep Details: %s" %(NWKID,self.ListOfDevices[NWKID]['ConfigSource'],str(self.ListOfDevices[NWKID]['Ep'])))

            # Binding devices
            CLUSTERS_LIST = [ 'fc00', '0500', '0406', '0402', '0400', '0001', 
                    '0403', '0405', '0500', '0702', '0006', '0008', '0201', '0300', '0000' ]

            READ_ATTRIBUTES_MATRIX = {
                    # Cluster : ( ReadAttribute function, Frequency )
                    '0406' : ( ReadAttributeRequest_0406, 900 ),
                    '0402' : ( ReadAttributeRequest_0402, 900 ),
                    '0400' : ( ReadAttributeRequest_0400, 900 ),
                    '0001' : ( ReadAttributeRequest_0001, 900 ),
                    '0403' : ( ReadAttributeRequest_0403, 900 ),
                    '0405' : ( ReadAttributeRequest_0405, 900 ),
                    }
#
#            for iterBindCluster in CLUSTERS_LIST:      # Bining order is important
#                for iterEp in self.ListOfDevices[NWKID]['Ep']:
#                    if iterBindCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
#                        Domoticz.Log('Request a Bind for %s/%s on Cluster %s' %(NWKID, iterEp, iterBindCluster))
#                        bindDevice( self, self.ListOfDevices[NWKID]['IEEE'], iterEp, iterBindCluster)

            # 2 Enable Configure Reporting for any applicable cluster/attributes
            processConfigureReporting( self, NWKID )  

            for iterReadAttrCluster in CLUSTERS_LIST:
                if iterReadAttrCluster in READ_ATTRIBUTES_MATRIX:
                    func = READ_ATTRIBUTES_MATRIX[iterReadAttrCluster][0]
                    func( self, NWKID)

            # Identify for ZLL compatible devices
            # Search for EP to be used 
            ep = '01'
            for ep in self.ListOfDevices[NWKID]['Ep']:
                if ep in ( '01', '03', '06', '09' ):
                    break
            identifyEffect( self, NWKID, ep , effect='Blink' )

            for iterEp in self.ListOfDevices[NWKID]['Ep']:
                Domoticz.Debug('looking for List of Attributes ep: %s' %iterEp)
                for iterCluster in  self.ListOfDevices[NWKID]['Ep'][iterEp]:
                    if iterCluster in ( 'Type', 'ClusterType', 'ColorMode' ): 
                        continue
                    getListofAttribute( self, NWKID, iterEp, iterCluster)

            # Set the sensitivity for Xiaomi Vibration
            if  self.ListOfDevices[NWKID]['Model'] == 'lumi.vibration.aq1':
                 Domoticz.Status('processNotinDBDevices - set viration Aqara %s sensitivity to %s' \
                        %(NWKID, self.pluginconf.vibrationAqarasensitivity))
                 setXiaomiVibrationSensitivity( self, NWKID, sensitivity = self.pluginconf.vibrationAqarasensitivity)

            self.adminWidgets.updateNotificationWidget( Devices, 'Successful creation of Widget for :%s DeviceID: %s' \
                    %(self.ListOfDevices[NWKID]['Model'], NWKID))
            self.CommiSSionning = False

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
            Domoticz.Debug("Bad devices detected (empty one), remove it, adr:" + str(NWKID))
            entriesToBeRemoved.append( NWKID )
            continue
            
        status = self.ListOfDevices[NWKID]['Status']
        RIA = int(self.ListOfDevices[NWKID]['RIA'])
        self.ListOfDevices[NWKID]['Heartbeat']=str(int(self.ListOfDevices[NWKID]['Heartbeat'])+1)

        if status == "failDB":
            entriesToBeRemoved.append( NWKID )

        ########## Known Devices 
        if status == "inDB": 
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
                        Domoticz.Debug("processListOfDevices - %s  is still connected cannot remove. NwkId: %s IEEE: %s " \
                                %(Devices[Unit].Name, NWKID, self.ListOfDevices[NWKID]['IEEE']))
                        fnd = True
                        break
                else: #We browse the all Devices and didn't find any IEEE.
                    if 'IEEE' in self.ListOfDevices[NWKID]:
                        Domoticz.Log("processListOfDevices - No corresponding device in Domoticz for %s/%s" %( NWKID, str(self.ListOfDevices[NWKID]['IEEE'])))
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
        del self.ListOfDevices[iter]

    if self.CommiSSionning:
        return  # We don't go further as we are Commissioning a new object and give the prioirty to it

    # LQI Scanner
    #    - LQI = 0 - no scanning at all otherwise delay the scan by n x HEARTBEAT
    if self.pluginconf.logLQI != 0 and \
            self.HeartbeatCount > (( 120 + self.pluginconf.logLQI) // HEARTBEAT):
        if self.ZigateComm.loadTransmit() < 5 :
            LQIcontinueScan( self, Devices )

    if ( self.HeartbeatCount % (60 // HEARTBEAT)) == 0:
        # Trigger Conifre Reporting to eligeable decices
        processConfigureReporting( self )
    
    if self.pluginconf.networkScan != 0 and \
            (self.HeartbeatCount == ( 120 // HEARTBEAT ) or (self.HeartbeatCount % ((300+self.pluginconf.networkScan ) // HEARTBEAT )) == 0) :
        NwkMgtUpdReq( self, ['11','12','13','14','15','16','17','18','19','20','21','22','23','24','25','26'] , mode='scan')

    return True
