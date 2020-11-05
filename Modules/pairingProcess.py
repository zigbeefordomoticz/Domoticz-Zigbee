#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: pairingProcess.py

    Description: Manage all actions done during the onHeartbeat() call

"""

import Domoticz
import binascii
import time
import datetime
import struct
import json


from Classes.LoggingManagement import LoggingManagement

from Modules.schneider_wiser import schneider_wiser_registration
#
from Modules.bindings import unbindDevice, bindDevice, rebind_Clusters
from Modules.basicOutputs import  sendZigateCmd, identifyEffect, getListofAttribute

        
from Modules.readAttributes import READ_ATTRIBUTES_REQUEST, \
        ReadAttributeRequest_0000, ReadAttributeRequest_0300

from Modules.lumi import enableOppleSwitch, setXiaomiVibrationSensitivity
from Modules.livolo import livolo_bind
from Modules.orvibo import OrviboRegistration
from Modules.configureReporting import processConfigureReporting
from Modules.profalux import profalux_fake_deviceModel
from Modules.domoCreate import CreateDomoDevice
from Modules.tools import reset_cluster_datastruct
from Modules.zigateConsts import CLUSTERS_LIST
from Modules.casaia import casaia_AC201_pairing

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
    self.log.logging( "Pairing", 'Debug', "processNotinDBDevices - NWKID: %s, Status: %s, RIA: %s, HB_: %s " %(NWKID, status, RIA, HB_))
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

    self.ListOfDevices[NWKID]['PairingInProgress'] = True
    knownModel = False
    if self.ListOfDevices[NWKID]['Model'] != {} and self.ListOfDevices[NWKID]['Model'] != '':
        Domoticz.Status("[%s] NEW OBJECT: %s Model Name: %s" %(RIA, NWKID, self.ListOfDevices[NWKID]['Model']))
        # Let's check if this Model is known
        if self.ListOfDevices[NWKID]['Model'] in self.DeviceConf:
            knownModel = True
            if not self.pluginconf.pluginConf['capturePairingInfos']:
                status = 'createDB' # Fast track
            else:
                self.ListOfDevices[NWKID]['RIA']=str( RIA + 1 )

        # https://zigate.fr/forum/topic/livolo-compatible-zigbee/#postid-596
        if self.ListOfDevices[NWKID]['Model'] == 'TI0001':
            livolo_bind( self, NWKID, '06')

    waitForDomoDeviceCreation = False
    if status == "8043": # We have at least receive 1 EndPoint
        reqColorModeAttribute = False
        self.ListOfDevices[NWKID]['RIA']=str( RIA + 1 )

        # Did we receive the Model Name
        skipModel = False

        if not skipModel or 'Model' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Model'] == {} or self.ListOfDevices[NWKID]['Model'] == '':
                self.log.logging( "Pairing", 'Debug', "[%s] NEW OBJECT: %s Request Model Name" %(RIA, NWKID))
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
                self.log.logging( "Pairing", 'Debug', "[%s] NEW OBJECT: %s Manufacturer: %s" %(RIA, NWKID, self.ListOfDevices[NWKID]['Manufacturer']), NWKID)

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
            if  int(self.ListOfDevices[NWKID]['RIA'],10) < 2:
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
                self.log.logging( "Pairing", 'Debug', "[%s] NEW OBJECT: %s Request Model Name" %(RIA, NWKID))
                if self.pluginconf.pluginConf['capturePairingInfos']:
                    self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'RA_0000' )
                ReadAttributeRequest_0000(self, NWKID , fullScope=False)    # Request Model Name
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
                self.log.logging( "Pairing", 'Debug', "[%s] NEW OBJECT: %s Request Model Name" %(RIA, NWKID))
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
        self.log.logging( "Pairing", 'Debug', "processNotinDB - Try several times to get all informations, let's use the Model now" +str(NWKID) )
        status = 'createDB'

    elif int(self.ListOfDevices[NWKID]['RIA'],10) > 4 and status != 'UNKNOW' and status != 'inDB':  # We have done several retry
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
        if 'Model' in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]['Model'] == {} or self.ListOfDevices[NWKID]['Model'] == '':
            if status == '8043' and int(self.ListOfDevices[NWKID]['RIA'],10) < 3:     # Let's take one more chance to get Model
                self.log.logging( "Pairing", 'Debug', "Too early, let's try to get the Model")
                return

        # Let's check if we have to disable the widget creation
        if 'Model' in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]['Model'] != {} and \
            self.ListOfDevices[NWKID]['Model'] in self.DeviceConf and \
            'CreateWidgetDomoticz' in self.DeviceConf[ self.ListOfDevices[NWKID]['Model'] ]:
            if not self.DeviceConf[ self.ListOfDevices[NWKID]['Model'] ]['CreateWidgetDomoticz']:
                self.ListOfDevices[NWKID]['Status'] = 'notDB'
                self.ListOfDevices[NWKID]['PairingInProgress'] = False
                self.CommiSSionning = False
                return

        # Let's check if we have a profalux device, and if that is a remote. In such case, just drop this
        if 'Manufacturer' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Manufacturer'] == '1110':
                if self.ListOfDevices[NWKID]['ZDeviceID'] == '0201': # Remote
                    self.ListOfDevices[NWKID]['Status'] = 'notDB'
                    self.ListOfDevices[NWKID]['PairingInProgress'] = False
                    self.CommiSSionning = False
                    return

        # Check once more if we have received the Model Name
        if 'ConfigSource' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['ConfigSource'] != 'DeviceConf':
                if 'Model' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Model'] in self.DeviceConf:
                        self.ListOfDevices[NWKID]['ConfigSource'] = 'DeviceConf'
        else:
            if 'Model' in self.ListOfDevices[NWKID]:
                if self.ListOfDevices[NWKID]['Model'] in self.DeviceConf:
                    self.ListOfDevices[NWKID]['ConfigSource'] = 'DeviceConf'


        self.log.logging( "Pairing", 'Debug', "[%s] NEW OBJECT: %s Trying to create Domoticz device(s)" %(RIA, NWKID))
        IsCreated=False
        # Let's check if the IEEE is not known in Domoticz
        for x in Devices:
            if self.ListOfDevices[NWKID].get('IEEE'):
                if Devices[x].DeviceID == str(self.ListOfDevices[NWKID]['IEEE']):
                    IsCreated = True
                    Domoticz.Error("processNotinDBDevices - Devices already exist. "  + Devices[x].Name + " with " + str(self.ListOfDevices[NWKID]) )
                    Domoticz.Error("processNotinDBDevices - Please cross check the consistency of the Domoticz and Plugin database.")
                    break

        if not IsCreated:
            self.log.logging( "Pairing", 'Debug', "processNotinDBDevices - ready for creation: %s , Model: %s " %(self.ListOfDevices[NWKID], self.ListOfDevices[NWKID]['Model']))

            # Purpose of this call is to patch Model and Manufacturer Name in case of Profalux
            # We do it just before calling CreateDomoDevice
            if 'Manufacturer' in self.ListOfDevices[NWKID]:
                if self.ListOfDevices[NWKID]['Manufacturer'] == '1110':
                    profalux_fake_deviceModel( self, NWKID)

            if self.pluginconf.pluginConf['capturePairingInfos']:
                self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'CR-DOMO' )
            CreateDomoDevice(self, Devices, NWKID)

            #Don't know why we need as this seems very weird
            if NWKID not in self.ListOfDevices:
                Domoticz.Error("processNotinDBDevices - %s doesn't exist in Post creation widget" %NWKID)
                self.CommiSSionning = False
                return
            if 'Ep' not in self.ListOfDevices[NWKID]:
                Domoticz.Error("processNotinDBDevices - %s doesn't have Ep in Post creation widget" %NWKID)
                self.CommiSSionning = False
                return

            ######
            ###### Post processing : work done after Domoticz Widget creation
            ######    
            if 'ConfigSource' in self.ListOfDevices[NWKID]:
                self.log.logging( "Pairing", 'Debug', "Device: %s - Config Source: %s Ep Details: %s" \
                        %(NWKID,self.ListOfDevices[NWKID]['ConfigSource'],str(self.ListOfDevices[NWKID]['Ep'])))

            # Bindings ....
            cluster_to_bind = CLUSTERS_LIST

            # Checking if anything must be done before Bindings, and if we have to take some specific bindings
            if 'Model' in self.ListOfDevices[NWKID]:
                if self.ListOfDevices[NWKID]['Model'] != {}:
                    _model = self.ListOfDevices[NWKID]['Model']
                    if _model in self.DeviceConf:
                        # Check if we have to unbind clusters
                        if 'ClusterToUnbind' in self.DeviceConf[ _model ]:
                            for iterEp, iterUnBindCluster in self.DeviceConf[ _model ]['ClusterToUnbind']:
                                unbindDevice( self, self.ListOfDevices[NWKID]['IEEE'], iterEp, iterUnBindCluster)
    
                        # Check if we have specific clusters to Bind                     
                        if 'ClusterToBind' in self.DeviceConf[ _model ]:
                            cluster_to_bind = self.DeviceConf[ _model ]['ClusterToBind']             
                            self.log.logging( "Pairing", 'Debug', '%s Binding cluster based on Conf: %s' %(NWKID,  str(cluster_to_bind)) )

            # Binding devices
            for iterEp in self.ListOfDevices[NWKID]['Ep']:
                for iterBindCluster in cluster_to_bind:      # Binding order is important
                    if iterBindCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                        if self.pluginconf.pluginConf['capturePairingInfos']:
                            self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'BIND_' + iterEp + '_' + iterBindCluster )

                        self.log.logging( "Pairing", 'Debug', 'Request a Bind for %s/%s on Cluster %s' %(NWKID, iterEp, iterBindCluster) )
                        # If option enabled, unbind
                        if self.pluginconf.pluginConf['doUnbindBind']:
                            unbindDevice( self, self.ListOfDevices[NWKID]['IEEE'], iterEp, iterBindCluster)
                        # Finaly binding
                        bindDevice( self, self.ListOfDevices[NWKID]['IEEE'], iterEp, iterBindCluster)

            # Just after Binding Enable Opple with Magic Word
            if  self.ListOfDevices[NWKID]['Model'] in ('lumi.remote.b686opcn01', 'lumi.remote.b486opcn01', 'lumi.remote.b286opcn01',
                                                'lumi.remote.b686opcn01-bulb', 'lumi.remote.b486opcn01-bulb', 'lumi.remote.b286opcn01-bulb'):
                Domoticz.Log("---> Calling enableOppleSwitch %s" %NWKID)
                enableOppleSwitch( self, NWKID)
    
            # 2 Enable Configure Reporting for any applicable cluster/attributes
            if self.pluginconf.pluginConf['capturePairingInfos']:
                self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'PR-CONFIG' )

            processConfigureReporting( self, NWKID )  

            # 3 Read attributes
            for iterEp in self.ListOfDevices[NWKID]['Ep']:
                # Let's scan each Endpoint cluster and check if there is anything to read
                for iterReadAttrCluster in CLUSTERS_LIST:
                    if iterReadAttrCluster not in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                        continue
                    if iterReadAttrCluster not in READ_ATTRIBUTES_REQUEST:
                        continue
                    if self.pluginconf.pluginConf['capturePairingInfos']:
                        self.DiscoveryDevices[NWKID]['CaptureProcess']['Steps'].append( 'RA_' + iterEp + '_' + iterReadAttrCluster )
                    #if iterReadAttrCluster == '0000':
                    #    reset_cluster_datastruct( self, 'ReadAttributes', NWKID, iterEp, iterReadAttrCluster  )
                    func = READ_ATTRIBUTES_REQUEST[iterReadAttrCluster][0]
                    func( self, NWKID)

            #4. IAS Enrollment
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
                # In case of Schneider Wiser, let's do the Registration Process
                if 'Manufacturer' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Manufacturer'] == '105e':
                        schneider_wiser_registration( self, Devices, NWKID )

            # In case of Orvibo Scene controller let's Registration
            if 'Manufacturer Name' in self.ListOfDevices[NWKID]:
                if self.ListOfDevices[NWKID][ 'Manufacturer Name'] == '欧瑞博':
                    OrviboRegistration( self, NWKID )
                    
            # Identify for ZLL compatible devices
            # Search for EP to be used 
            ep = '01'
            for ep in self.ListOfDevices[NWKID]['Ep']:
                if ep in ( '01', '03', '06', '09' ):
                    break
            identifyEffect( self, NWKID, ep , effect='Blink' )

            for iterEp in self.ListOfDevices[NWKID]['Ep']:
                self.log.logging( "Pairing", 'Debug', 'looking for List of Attributes ep: %s' %iterEp)
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
            if self.groupmgt and self.pluginconf.pluginConf['allowGroupMembership'] and 'Model' in self.ListOfDevices[NWKID]:
                Domoticz.Log("Creation Group")
                if self.ListOfDevices[NWKID]['Model'] in self.DeviceConf:
                    if 'GroupMembership' in self.DeviceConf[ self.ListOfDevices[NWKID]['Model'] ]:
                        for groupToAdd in self.DeviceConf[ self.ListOfDevices[NWKID]['Model'] ]['GroupMembership']:
                            if len( groupToAdd ) == 2:
                                self.groupmgt.addGroupMemberShip( NWKID, groupToAdd[0], groupToAdd[1] )
                            else:
                                Domoticz.Error("Uncorrect GroupMembership definition %s" %str(self.DeviceConf[ self.ListOfDevices[NWKID]['Model'] ]['GroupMembership']))

            if 'Model' in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]['Model'] in ( 'AC201A', ):
                casaia_AC201_pairing( self, NWKID)
                
                
            # Reset HB in order to force Read Attribute Status
            self.ListOfDevices[NWKID]['Heartbeat'] = 0

            writeDiscoveryInfos( self )
            self.ListOfDevices[NWKID]['PairingInProgress'] = False
            
        #end if ( self.ListOfDevices[NWKID]['Status']=="8043" or self.ListOfDevices[NWKID]['Model']!= {} )
    #end ( self.pluginconf.storeDiscoveryFrames == 0 and status != "UNKNOW" and status != "DUP")  or (  self.pluginconf.storeDiscoveryFrames == 1 and status == "8043" )
