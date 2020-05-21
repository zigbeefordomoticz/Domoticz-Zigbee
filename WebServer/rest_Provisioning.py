#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import Domoticz
from time import time
import json

from Modules.zigateConsts import  ZCL_CLUSTERS_LIST ,PROFILE_ID, ZHA_DEVICES, ZLL_DEVICES
from Modules.basicOutputs import ZigatePermitToJoin, sendZigateCmd, start_Zigate, setExtendedPANID, zigateBlueLed
from WebServer.headerResponse import setupHeadersResponse, prepResponseMessage


def rest_new_hrdwr( self, verb, data, parameters):

    """
    This is call to Enable/Disable a Provisioning process. As a toggle you will enable the provisioning or disable it
    it will return either Enable or Disable
    """
    _response = prepResponseMessage( self ,setupHeadersResponse(  ))

    if verb != 'GET':
        return _response

    data = {}
    if len(parameters) != 1:
        Domoticz.Error("rest_new_hrdwr - unexpected parameter %s " %parameters)
        _response["Data"] = { "unexpected parameter %s " %parameters}
        return _response

    if parameters[0] not in ( 'enable', 'cancel', 'disable' ):
        Domoticz.Error("rest_new_hrdwr - unexpected parameter %s " %parameters[0])
        _response["Data"] = { "unexpected parameter %s " %parameters[0] }
        return _response

    if parameters[0] == 'enable':
        Domoticz.Log("Enable Assisted pairing")
        if len(self.DevicesInPairingMode):
            del self.DevicesInPairingMode
            self.DevicesInPairingMode = []
        if not self.zigatedata:
            # Seems we are in None mode - Testing for ben
            self.fakeDevicesInPairingMode = 0

        if self.permitTojoin['Duration'] != 255 and self.pluginparameters['Mode1'] != 'None':
            ZigatePermitToJoin(self, ( 4 * 60 ))

        _response["Data"] = { "start pairing mode at %s " %int(time()) }
        return _response

    if parameters[0] in ( 'cancel', 'disable'):
        Domoticz.Log("Disable Assisted pairing")
        if len(self.DevicesInPairingMode) != 0:
            del self.DevicesInPairingMode
            self.DevicesInPairingMode = []

        if not self.zigatedata:
            # Seems we are in None mode - Testing for ben
            self.fakeDevicesInPairingMode = 0

        if not (
            self.permitTojoin['Duration'] == 255
            or self.pluginparameters['Mode1'] == 'None'
        ):
            ZigatePermitToJoin(self, 0)

        _response["Data"] = { "stop pairing mode at %s " %int(time()) }
        return _response


def rest_rcv_nw_hrdwr( self, verb, data, parameters):

    """
    Will return a status on the provisioning process. Either Enable or Disable and in case there is a new device provisionned
    during the period, it will return the information captured.
    """

    _response = prepResponseMessage( self ,setupHeadersResponse(  ))

    if verb != 'GET':
        return _response
        
    data = {}
    data['NewDevices'] = []

    if not self.zigatedata:
        # Seems we are in None mode - Testing for ben
        if self.fakeDevicesInPairingMode in ( 0, 1):
            # Do nothing just wait the next pool
            self.fakeDevicesInPairingMode += 1
            _response["Data"] = json.dumps( data )
            return _response

        if self.fakeDevicesInPairingMode in ( 2, 3 ):
            self.fakeDevicesInPairingMode += 1
            newdev = {}
            newdev['NwkId'] = list(self.ListOfDevices.keys())[0]
            data['NewDevices'].append( newdev )
            _response["Data"] = json.dumps( data )
            return _response

        if self.fakeDevicesInPairingMode in ( 4, 5 ):
            self.fakeDevicesInPairingMode += 1
            newdev = {}
            newdev['NwkId'] = list(self.ListOfDevices.keys())[0]
            data['NewDevices'].append( newdev )
            newdev = {}
            newdev['NwkId'] = list(self.ListOfDevices.keys())[1]
            data['NewDevices'].append( newdev )
            _response["Data"] = json.dumps( data )
            return _response

        if self.fakeDevicesInPairingMode in ( 6, 7 ):
            self.fakeDevicesInPairingMode += 1
            self.DevicesInPairingMode.append( list(self.ListOfDevices.keys())[0] )
            self.DevicesInPairingMode.append( list(self.ListOfDevices.keys())[1] )
            self.DevicesInPairingMode.append( list(self.ListOfDevices.keys())[2] )

    Domoticz.Log("Assisted Pairing: Polling: %s" %str(self.DevicesInPairingMode))
    if len(self.DevicesInPairingMode) == 0:
        Domoticz.Log("--> Empty queue")
        _response["Data"] = json.dumps( data )
        return _response

    listOfPairedDevices = list(self.DevicesInPairingMode)
    _fake = 0
    for nwkid in listOfPairedDevices:
        if not self.zigatedata:
            _fake += 1
        newdev = {}
        newdev['NwkId'] = nwkid

        Domoticz.Log("--> New device: %s" %nwkid)
        if 'Status' not in self.ListOfDevices[ nwkid ]:
            Domoticz.Error("Something went wrong as the device seems not be created")
            data['NewDevices'].append( newdev )
            continue

        if self.ListOfDevices[ nwkid ]['Status'] in ( '004d', '0045', '0043', '8045', '8043') or ( _fake == 1):
            # Pairing in progress, just return the Nwkid
            data['NewDevices'].append( newdev )
            continue

        elif self.ListOfDevices[ nwkid ]['Status'] == 'UNKNOW' or ( _fake == 2):
            Domoticz.Log("--> UNKNOW , removed %s from List" %nwkid)
            self.DevicesInPairingMode.remove( nwkid )
            newdev['ProvisionStatus'] = 'Failed'
            newdev['ProvisionStatusDesc'] = 'Failed'

        elif self.ListOfDevices[ nwkid ]['Status'] == 'inDB':
            Domoticz.Log("--> inDB , removed %s from List" %nwkid)
            self.DevicesInPairingMode.remove( nwkid )
            newdev['ProvisionStatus'] = 'inDB'
            newdev['ProvisionStatusDesc'] = 'inDB'
        else:
            Domoticz.Log("--> Unexpected , removed %s from List" %nwkid)
            self.DevicesInPairingMode.remove( nwkid )
            newdev['ProvisionStatus'] = 'Unexpected'
            newdev['ProvisionStatusDesc'] = 'Unexpected'
            Domoticz.Error('Unexpected')
            continue

        newdev['IEEE'] = 'Unknown'
        if 'IEEE' in self.ListOfDevices[ nwkid ]:
            newdev['IEEE'] = self.ListOfDevices[ nwkid ]['IEEE']

        newdev['ProfileId'] = ''
        newdev['ProfileIdDesc'] = 'Unknow'
        if 'ProfileID' in self.ListOfDevices[ nwkid ]:
            if self.ListOfDevices[ nwkid ]['ProfileID'] != {}:
                newdev['ProfileId'] = self.ListOfDevices[ nwkid ]['ProfileID']
                if int(newdev['ProfileId'],16) in PROFILE_ID:
                    newdev['ProfileIdDesc'] = PROFILE_ID[ int(newdev['ProfileId'],16) ]

        newdev['ZDeviceID'] = ''
        newdev['ZDeviceIDDesc'] = 'Unknow'
        if 'ZDeviceID' in self.ListOfDevices[ nwkid ]:
            if self.ListOfDevices[ nwkid ]['ZDeviceID'] != {}:
                newdev['ZDeviceID'] = self.ListOfDevices[ nwkid ]['ZDeviceID']
                if int(newdev['ProfileId'],16) == 0x0104: # ZHA
                    if int(newdev['ZDeviceID'],16) in ZHA_DEVICES:
                        newdev['ZDeviceIDDesc'] = ZHA_DEVICES[ int(newdev['ZDeviceID'],16) ]
                    else:
                        newdev['ZDeviceIDDesc'] = 'Unknow'
                elif int(newdev['ProfileId'],16) == 0xc05e: # ZLL
                    if int(newdev['ZDeviceID'],16) in ZLL_DEVICES:
                        newdev['ZDeviceIDDesc'] = ZLL_DEVICES[ int(newdev['ZDeviceID'],16) ]

        if 'Model' in self.ListOfDevices[ nwkid ]:
            newdev['Model'] = self.ListOfDevices[ nwkid ]['Model']

        newdev['PluginCertified'] = 'Unknow'
        if 'ConfigSource' in self.ListOfDevices[nwkid]:
            if self.ListOfDevices[nwkid]['ConfigSource'] == 'DeviceConf':
                newdev['PluginCertified'] = 'yes'
            else:
                newdev['PluginCertified'] = 'no'

        newdev['Ep'] = []
        if 'Ep' in self.ListOfDevices[ nwkid ]:
            for iterEp in  self.ListOfDevices[ nwkid ][ 'Ep' ]:
                ep = {}
                ep['Ep'] = iterEp
                ep['Clusters'] = []
                for clusterId in self.ListOfDevices[ nwkid ][ 'Ep' ][ iterEp ]:
                    if clusterId in ( 'ClusterType', 'Type', 'ColorControl' ): 
                        continue

                    cluster = {}
                    cluster['ClusterId'] = clusterId
                    if clusterId in ZCL_CLUSTERS_LIST:
                        cluster['ClusterDesc'] = ZCL_CLUSTERS_LIST[ clusterId ]
                    else:
                        cluster['ClusterDesc'] = 'Unknown'
                    ep['Clusters'].append( cluster )
                    Domoticz.Log("------> New Cluster: %s" %str(cluster))
                newdev['Ep'].append( ep )
                Domoticz.Log("----> New Ep: %s" %str(ep))
        data['NewDevices'].append( newdev )
        Domoticz.Log(" --> New Device: %s" %str(newdev))
    # for nwkid in listOfPairedDevices:
            
    _response["Data"] = json.dumps( data )
    return _response