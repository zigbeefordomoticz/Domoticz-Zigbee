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
import struct
import json
import queue

import z_output
import z_tools
import z_domoticz
import z_LQI
import z_consts

from z_IAS import IAS_Zone_Management


def processKnownDevices( self, NWKID ):

    # Check if Node Descriptor was run ( this could not be the case on early version)
    intHB = int( self.ListOfDevices[NWKID]['Heartbeat'])
    if  intHB == ( 28 // z_consts.HEARTBEAT):
        if not self.ListOfDevices[NWKID].get('PowerSource'):    # Looks like PowerSource is not available, let's request a Node Descriptor
            z_output.sendZigateCmd(self,"0042", str(NWKID) )    # Request a Node Descriptor

    if ( intHB % ( 60 // z_consts.HEARTBEAT) ) == 0 or ( intHB == ( 24 // z_consts.HEARTBEAT)):
        if  'PowerSource' in self.ListOfDevices[NWKID]:        # Let's check first that the field exist, if not it will be requested at Heartbeat == 12 (see above)
            if self.ListOfDevices[NWKID]['PowerSource'] == 'Main':    #  Only for device receiving req on idle
                for tmpEp in self.ListOfDevices[NWKID]['Ep']:    # Request ReadAttribute based on Cluster 
                    if "0702" in self.ListOfDevices[NWKID]['Ep'][tmpEp]:    # Cluster Metering
                        z_output.ReadAttributeRequest_0702(self, NWKID )
                    #if "0008" in self.ListOfDevices[NWKID]['Ep'][tmpEp]:    # Cluster LvlControl
                    #    z_output.ReadAttributeRequest_0008(self, NWKID )
                    #if "000C" in self.ListOfDevices[NWKID]['Ep'][tmpEp]:    # Cluster Xiaomi
                    #    z_output.ReadAttributeRequest_000C(self, NWKID )
                    #if "0006" in self.ListOfDevices[NWKID]['Ep'][tmpEp]:    # Cluster On/off
                    #    z_output.ReadAttributeRequest_0006(self, NWKID )
                    #if "0000" in self.ListOfDevices[NWKID]['Ep'][tmpEp]:    # Cluster Power
                    #    z_output.ReadAttributeRequest_0000(self, NWKID )
                    #if "0001" in self.ListOfDevices[NWKID]['Ep'][tmpEp]:    # Cluster Power
                    #    z_output.ReadAttributeRequest_0001(self, NWKID )
                    #if "0300" in self.ListOfDevices[NWKID]['Ep'][tmpEp]:    # Color Temp
                    #    z_output.ReadAttributeRequest_0300(self, NWKID )
                    pass

    
def processNotinDBDevices( self, Devices, NWKID , status , RIA ):
    HB_ = int(self.ListOfDevices[NWKID]['Heartbeat'])

    # 0x004d is a device annoucement.  Usally we get Network Address (short address) and IEEE
    if status == "004d" and self.ListOfDevices[NWKID]['Heartbeat']:
        Domoticz.Status("[%s] NEW OBJECT: %s (re)Starting process" %(RIA, NWKID))
        # We should check if the device has not been already created via IEEE
        if z_tools.IEEEExist( self, self.ListOfDevices[NWKID]['IEEE'] ) == False:
            self.ListOfDevices[NWKID]['Heartbeat'] = "0"
            self.ListOfDevices[NWKID]['Status'] = "0045"
            z_output.sendZigateCmd(self,"0045", str(NWKID))             # Request list of EPs
            return
        else:
            for dup in self.ListOfDevices:
                if self.ListOfDevices[NWKID]['IEEE'] == self.ListOfDevices[dup]['IEEE'] and self.ListOfDevices[dup]['Status'] == "inDB":
                    Domoticz.Error("onHearbeat - Device: " + str(NWKID) + "already known under IEEE: " +str(self.ListOfDevices[NWKID]['IEEE'] ) 
                                        + " Duplicate of " + str(dup) )
                    Domoticz.Error("onHearbeat - Please check the consistency of the plugin database and domoticz database.")
                    self.ListOfDevices[NWKID]['Status']="DUP"
                    self.ListOfDevices[NWKID]['Heartbeat']="0"
                    self.ListOfDevices[NWKID]['RIA']="99"
                    break
            return

    # 0x8045 is providing the list of active EPs we will so request EP descriptor for each of them
    if status == "8045": # Status is set in Decode8045 (z_input)
        Domoticz.Status("[%s] NEW OBJECT: %s Ox8045 received Infos" %(RIA, NWKID))
        self.ListOfDevices[NWKID]['Heartbeat'] = "0"
        self.ListOfDevices[NWKID]['Status'] = "0043"
        for cle in self.ListOfDevices[NWKID]['Ep']:
            Domoticz.Status("[%s] NEW OBJECT: %s Request Simple Descriptor for Ep: %s" %( RIA, NWKID, cle))
            z_output.sendZigateCmd(self,"0043", str(NWKID)+str(cle))    
        if 'Model' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Model'] == {}:
                Domoticz.Status("[%s] NEW OBJECT: %s Request Attributes for Cluster 0x0000" %(RIA, NWKID))
                z_output.ReadAttributeRequest_0000(self, NWKID )      # Basic Cluster readAttribute Request
        if 'Manufacturer' in self.ListOfDevices[NWKID]:
            Domoticz.Status("[%s] NEW OBJECT: %s Request Node Descriptor" %(RIA, NWKID))
            if self.ListOfDevices[NWKID]['Manufacturer'] == {}:
                z_output.sendZigateCmd(self,"0042", str(NWKID))     # Request a Node Descriptor
        Domoticz.Status("[%s] NEW OBJECT: %s Request Attributes for Cluster 0x0001" %(RIA, NWKID))
        z_output.ReadAttributeRequest_0001(self, NWKID )            # Basic Cluster readAttribute Request
        return

    # In case we received 0x8043, we might want to check if there is a 0x0300 cluster. 
    # In that case, that is a Color Bulbe and we might want to ReadAttribute in ordert o discover what is the ColorMode .
    waitForDomoDeviceCreation = 0
    if status == "8043":
        Domoticz.Status("[%s] NEW OBJECT: %s Ox8043 received Infos" %(RIA, NWKID))
        waitForDomoDeviceCreation = 0
        reqColorModeAttribute = 0

        for iterEp in self.ListOfDevices[NWKID]['Ep']:
            if '0300' not in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                continue
            else:
                if 'ColorInfos' in self.ListOfDevices[NWKID]:
                    if 'ColorMode' in self.ListOfDevices[NWKID]['ColorInfos']:
                        waitForDomoDeviceCreation = 0
                        reqColorModeAttribute = 0
                        break
                    else:
                        waitForDomoDeviceCreation = 1
                        reqColorModeAttribute = 1
                        break
                else:
                    waitForDomoDeviceCreation = 1
                    reqColorModeAttribute = 1
                    break
        if reqColorModeAttribute == 1:
            self.ListOfDevices[NWKID]['RIA']=str(int(self.ListOfDevices[NWKID]['RIA'])+1)
            Domoticz.Status("[%s] NEW OBJECT: %s Request Attribute for Cluster 0x0300 to get ColorMode" %(RIA,NWKID))
            z_output.ReadAttributeRequest_0300(self, NWKID )

    # Timeout management
    if (status == "004d" or status == "0045") and HB_ > 2:
        Domoticz.Status("[%s] NEW OBJECT: %s TimeOut in %s restarting at 0x004d" %(RIA, NWKID, status))
        self.ListOfDevices[NWKID]['RIA']=str(int(self.ListOfDevices[NWKID]['RIA'])+1)
        self.ListOfDevices[NWKID]['Heartbeat']="0"
        self.ListOfDevices[NWKID]['Status']="004d"
        return

    if (status == "8045" or status == "0043") and HB_ > 2:
        Domoticz.Status("[%s] NEW OBJECT: %s TimeOut in %s restarting at 0x0043" %(RIA, NWKID, status))
        self.ListOfDevices[NWKID]['RIA']=str(int(self.ListOfDevices[NWKID]['RIA'])+1)
        self.ListOfDevices[NWKID]['Heartbeat']="0"
        self.ListOfDevices[NWKID]['Status']="0043"
        return

    if status != "UNKNOW" and self.ListOfDevices[NWKID]['RIA'] > "6":  # We have done several retry
        Domoticz.Status("[%s] NEW OBJECT: %s Not able to get all needed attributes on time" %(RIA, NWKID))
        self.ListOfDevices[NWKID]['Status']="UNKNOW"
        Domoticz.Log("processNotinDB - not able to find response from " +str(NWKID) + " stop process at " +str(status) )
        Domoticz.Log("processNotinDB - RIA: %s waitForDomoDeviceCreation: %s, allowStoreDiscoveryFrames: %s Model: %s " %( self.ListOfDevices[NWKID]['RIA'], waitForDomoDeviceCreation, self.pluginconf.allowStoreDiscoveryFrames, self.ListOfDevices[NWKID]['Model']))

    # https://github.com/sasu-drooz/Domoticz-Zigate/wiki/ProfileID---ZDeviceID

    # If we are in status = 0x8043 we have received EPs descriptors
    # If we have Model we might be able to identify the device with it's model
    # In case where self.pluginconf.storeDiscoveryFrames is set (1) then we force the full process and so wait for 0x8043
    if ( waitForDomoDeviceCreation != 1 and  self.pluginconf.allowStoreDiscoveryFrames == 0 and status != "UNKNOW" and status != "DUP") or \
            ( waitForDomoDeviceCreation != 1 and self.pluginconf.allowStoreDiscoveryFrames == 1 and status == "8043" ):
        if ( self.ListOfDevices[NWKID]['Status']=="8043" or self.ListOfDevices[NWKID]['Model']!= {} ):
            #We will try to create the device(s) based on the Model , if we find it in DeviceConf or against the Cluster
            Domoticz.Status("[%s] NEW OBJECT: %s Trying to create Domoticz device(s)" %(RIA, NWKID))


            IsCreated=False
            x=0
            # Let's check if the IEEE is not known in Domoticz
            for x in Devices:
                if self.ListOfDevices[NWKID].get('IEEE'):
                    if Devices[x].DeviceID == str(self.ListOfDevices[NWKID]['IEEE']):
                        if self.pluginconf.allowForceCreationDomoDevice == 1:
                            Domoticz.Log("processNotinDBDevices - Devices already exist. "  + Devices[x].Name + " with " + str(self.ListOfDevices[NWKID]) )
                            Domoticz.Error("processNotinDBDevices - ForceCreationDevice enable, we continue")
                        else:
                            IsCreated = True
                            Domoticz.Error("processNotinDBDevices - Devices already exist. "  + Devices[x].Name + " with " + str(self.ListOfDevices[NWKID]) )
                            Domoticz.Error("processNotinDBDevices - Please cross check the consistency of the Domoticz and Plugin database.")
                            break

            if IsCreated == False:
                Domoticz.Log("processNotinDBDevices - ready for creation: %s" %self.ListOfDevices[NWKID])
                z_domoticz.CreateDomoDevice(self, Devices, NWKID)

                # Post creation widget


                # 1 Enable Configure Reporting for any applicable cluster/attributes
                z_output.processConfigureReporting( self, NWKID )  

                # Identify for ZLL compatible devices
                # Search for EP to be used 
                ep = '01'
                for ep in self.ListOfDevices[NWKID]['Ep']:
                    if ep in ( '01', '03', '09' ):
                        break
                z_output.identifyEffect( self, NWKID, ep , effect='Blink' )

                # IAS Zone / Mostlikley Status is 0x8053, but it could also be Model set and we have populated the information from DeviceConf
                if 'Ep' in self.ListOfDevices[NWKID]:
                    for iterEp in self.ListOfDevices[NWKID]['Ep']:
                        if '0500' in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                            # We found a Cluster 0x0500 IAS. May be time to start the IAS Zone process
                            Domoticz.Status("[%s] NEW OBJECT: %s 0x%04x - IAS Zone controler setting" %( RIA, NWKID, int(status,16)))
                            self.iaszonemgt.IASZone_triggerenrollement( NWKID, iterEp)
    
                # Set the sensitivity for Xiaomi Vibration
                if  self.ListOfDevices[NWKID]['Model'] == 'lumi.vibration.aq1':
                     Domoticz.Status('processNotinDBDevices - set viration Aqara %s sensitivity to %s' \
                            %(NWKID, self.pluginconf.vibrationAqarasensitivity))
                     z_output.setXiaomiVibrationSensitivity( self, NWKID, sensitivity = self.pluginconf.vibrationAqarasensitivity)

        #end if ( self.ListOfDevices[NWKID]['Status']=="8043" or self.ListOfDevices[NWKID]['Model']!= {} )
    #end ( self.pluginconf.storeDiscoveryFrames == 0 and status != "UNKNOW" and status != "DUP")  or (  self.pluginconf.storeDiscoveryFrames == 1 and status == "8043" )
    

def processListOfDevices( self , Devices ):
    # Let's check if we do not have a command in TimeOut
    self.ZigateComm.checkTOwaitFor()

    for NWKID in list(self.ListOfDevices):
        # If this entry is empty, then let's remove it .
        if len(self.ListOfDevices[NWKID]) == 0:
            Domoticz.Debug("Bad devices detected (empty one), remove it, adr:" + str(NWKID))
            del self.ListOfDevices[NWKID]
            continue
            
        status=self.ListOfDevices[NWKID]['Status']
        RIA=int(self.ListOfDevices[NWKID]['RIA'])
        self.ListOfDevices[NWKID]['Heartbeat']=str(int(self.ListOfDevices[NWKID]['Heartbeat'])+1)

        ########## Known Devices 
        if status == "inDB": 
            processKnownDevices( self , NWKID )

        if status == "Left":
            # Device has sent a 0x8048 message annoucing its departure (Leave)
            # Most likely we should receive a 0x004d, where the device come back with a new short address
            # For now we will display a message in the log every 1'
            # We might have to remove this entry if the device get not reconnected.
            if (( int(self.ListOfDevices[NWKID]['Heartbeat']) % 36 ) and  int(self.ListOfDevices[NWKID]['Heartbeat']) != 0) == 0:
                Domoticz.Log("processListOfDevices - Device: " +str(NWKID) + " is in Status = 'Left' for " +str(self.ListOfDevices[NWKID]['Heartbeat']) + "HB" )
                # Let's check if the device still exist in Domoticz
                fnd = True
                for Unit in Devices:
                    if self.ListOfDevices[NWKID]['IEEE'] == Devices[Unit].DeviceID:
                        Domoticz.Debug("processListOfDevices - %s  is still connected cannot remove. NwkId: %s IEEE: %s " \
                                %(Devices[Unit].Name, NWKID, self.ListOfDevices[NWKID]['IEEE']))
                        fnd = True
                        break
                else: #We browse the all Devices and didn't find any IEEE.
                    Domoticz.Log("processListOfDevices - No corresponding device in Domoticz for %s " %( NWKID, self.ListOfDevices[NWKID]['IEEE']))
                    fnd = False

                if not fnd:
                    # Not devices found in Domoticz, so we are safe to remove it from Plugin
                    if self.ListOfDevices[NWKID]['IEEE'] in self.IEEE2NWK:
                        Domoticz.Log("processListOfDevices - Removing %s / %s from IEEE2NWK." %(self.ListOfDevices[NWKID]['IEEE'], NWKID))
                        del self.IEEE2NWK[self.ListOfDevices[NWKID]['IEEE']]
                    Domoticz.Log("processListOfDevices - Removing the entry %s from ListOfDevice" %(NWKID))
                    z_tools.removeNwkInList( self, NWKID)

        elif status != "inDB" and status != "UNKNOW":
            # Discovery process 0x004d -> 0x0042 -> 0x8042 -> 0w0045 -> 0x8045 -> 0x0043 -> 0x8043
            processNotinDBDevices( self , Devices, NWKID, status , RIA )
    #end for key in ListOfDevices

    # LQI Scanner
    #    - LQI = 0 - no scanning at all otherwise delay the scan by n x z_consts.HEARTBEAT
    
    if self.pluginconf.logLQI != 0 and \
            self.HeartbeatCount > (( 120 + self.pluginconf.logLQI) // z_consts.HEARTBEAT):
        if self.ZigateComm.loadTransmit() < 5 :
            z_LQI.LQIcontinueScan( self )

    if self.HeartbeatCount == 4:
        # Trigger Conifre Reporting to eligeable decices
        z_output.processConfigureReporting( self )
    
    if self.pluginconf.networkScan != 0 and \
            (self.HeartbeatCount == ( 120 // z_consts.HEARTBEAT ) or (self.HeartbeatCount % ((300+self.pluginconf.networkScan ) // z_consts.HEARTBEAT )) == 0) :
        z_output.NwkMgtUpdReq( self, ['11','12','13','14','15','16','17','18','19','20','21','22','23','24','25','26'] , mode='scan')


    return True
