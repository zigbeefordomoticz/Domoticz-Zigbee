#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#


import Domoticz
import json


from WebServer.headerResponse import setupHeadersResponse, prepResponseMessage
import os
from time import time
  
def rest_zGroup_lst_avlble_dev( self, verb, data, parameters):

    _response = prepResponseMessage( self ,setupHeadersResponse(  ))

    if verb != 'GET':
        return _response

    device_lst = []
    _device =  {}
    _widget = {}
    _device['_NwkId'] = '0000'
    _device['WidgetList'] = []

    _widget['_ID'] =  ''
    _widget['Name'] =  ''
    _widget['IEEE'] =  '0000000000000000'
    _widget['Ep'] =  '01'
    _widget['ZDeviceName'] =  'Zigate (Coordinator)'

    if self.zigatedata and 'IEEE' in self.zigatedata:
        _widget['IEEE'] =  self.zigatedata['IEEE'] 
        _device['_NwkId'] = self.zigatedata['Short Address']

    _device['WidgetList'].append( _widget )
    device_lst.append( _device )

    for x in self.ListOfDevices:
        if x == '0000':  
            continue

        if 'MacCapa' not in self.ListOfDevices[x]:
            self.logging( 'Debug', "rest_zGroup_lst_avlble_dev - no 'MacCapa' info found for %s!!!!" %x)
            continue

        IkeaRemote = False
        if (
            'Type' in self.ListOfDevices[x]
            and self.ListOfDevices[x]['Type'] == 'Ikea_Round_5b'
        ):
            IkeaRemote = True

        if not (self.ListOfDevices[x]['MacCapa'] == '8e' or IkeaRemote):
            self.logging( 'Debug', "rest_zGroup_lst_avlble_dev - %s not a Main Powered device. " %x)
            continue

        if (
            'Ep' in self.ListOfDevices[x]
            and 'ZDeviceName' in self.ListOfDevices[x]
            and 'IEEE' in self.ListOfDevices[x]
        ):
            _device = {'_NwkId': x, 'WidgetList': []}
            for ep in self.ListOfDevices[x]['Ep']:
                if (
                    'Type' in self.ListOfDevices[x]
                    and self.ListOfDevices[x]['Type'] == 'Ikea_Round_5b'
                    and ep == '01'
                    and 'ClusterType' in self.ListOfDevices[x]['Ep']['01']
                ):
                    widgetID = ''
                    for iterDev in self.ListOfDevices[x]['Ep']['01']['ClusterType']:
                        if self.ListOfDevices[x]['Ep']['01']['ClusterType'][iterDev] == 'Ikea_Round_5b':
                            widgetID = iterDev
                            for widget in self.Devices:
                                if self.Devices[widget].ID == int(widgetID):
                                    _widget = {
                                        '_ID': self.Devices[widget].ID,
                                        'Name': self.Devices[widget].Name,
                                        'IEEE': self.ListOfDevices[x]['IEEE'],
                                        'Ep': ep,
                                        'ZDeviceName': self.ListOfDevices[x][
                                            'ZDeviceName'
                                        ],
                                    }

                                    if _widget not in _device['WidgetList']:
                                        _device['WidgetList'].append( _widget )
                                    break
                            if _device not in device_lst:
                                device_lst.append( _device )
                    continue # Next Ep

                if not (
                    '0004' in self.ListOfDevices[x]['Ep'][ep]
                    or 'ClusterType' in self.ListOfDevices[x]['Ep'][ep]
                    and 'ClusterType' in self.ListOfDevices[x]
                    or '0006' in self.ListOfDevices[x]['Ep'][ep]
                    or '0008' in self.ListOfDevices[x]['Ep'][ep]
                    or '0102' in self.ListOfDevices[x]['Ep'][ep]
                ):
                    continue

                if 'ClusterType' in self.ListOfDevices[x]['Ep'][ep]:
                    clusterType= self.ListOfDevices[x]['Ep'][ep]['ClusterType']
                    for widgetID in clusterType:
                        if clusterType[widgetID] not in ( 'LvlControl', 'Switch', 'Plug', 
                            "SwitchAQ2", "DSwitch", "Button", "DButton", 'LivoloSWL', 'LivoloSWR',
                            'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl',
                            'VenetianInverted', 'Venetian', 'WindowCovering' ):
                            continue

                        for widget in self.Devices:
                            if self.Devices[widget].ID == int(widgetID):
                                _widget = {}
                                _widget['_ID'] =  self.Devices[widget].ID 
                                _widget['Name'] =  self.Devices[widget].Name 
                                _widget['IEEE'] =  self.ListOfDevices[x]['IEEE'] 
                                _widget['Ep'] =  ep 
                                _widget['ZDeviceName'] =  self.ListOfDevices[x]['ZDeviceName'] 
                                if _widget not in _device['WidgetList']:
                                    _device['WidgetList'].append( _widget )

                elif 'ClusterType' in self.ListOfDevices[x]:
                    clusterType = self.ListOfDevices[x]['ClusterType']

                    for widgetID in clusterType:
                        if clusterType[widgetID] not in ( 'LvlControl', 'Switch', 'Plug', 
                            "SwitchAQ2", "DSwitch", "Button", "DButton", 'LivoloSWL', 'LivoloSWR',
                            'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl',
                            'VenetianInverted', 'Venetian', 'WindowCovering' ):
                            continue

                        for widget in self.Devices:
                            if self.Devices[widget].ID == int(widgetID):
                                _widget = {}
                                _widget['_ID'] =  self.Devices[widget].ID 
                                _widget['Name'] =  self.Devices[widget].Name 
                                _widget['IEEE'] =  self.ListOfDevices[x]['IEEE'] 
                                _widget['Ep'] =  ep 
                                _widget['ZDeviceName'] =  self.ListOfDevices[x]['ZDeviceName'] 
                                if _widget not in _device['WidgetList']:
                                    _device['WidgetList'].append( _widget )

        if _device not in device_lst:
            device_lst.append( _device )
    self.logging( 'Debug', "Response: %s" %device_lst)
    _response["Data"] = json.dumps( device_lst, sort_keys=True )
    return _response

def rest_rescan_group( self, verb, data, parameters):
    
    self.groupmgt.ScanAllDevicesForGroupMemberShip( )

    _response = prepResponseMessage( self ,setupHeadersResponse())
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
    action = {}
    if verb != 'GET':
        return _response

    self.groupmgt.ScanAllDevicesForGroupMemberShip( )
    action['Name'] = 'Full Scan'
    action['TimeStamp'] = int(time())

    _response["Data"] = json.dumps( action , sort_keys=True )

    return _response

def rest_scan_devices_for_group( self, verb, data, parameter):
    # wget --method=PUT --body-data='[ "0000", "0001", "0002", "0003" ]' http://127.0.0.1:9442/rest-zigate/1/ScanDeviceForGrp
    
    _response = prepResponseMessage( self ,setupHeadersResponse(  ))
    _response["Data"] = None
    if self.groupmgt is None:
        # Group is not enabled!
        return _response

    if verb != 'PUT':
        # Only Put command with a Valid JSON is allow
        return _response

    if data is None:
        return _response

    if len(parameter) != 0:
        return _response 

    # We receive a JSON with a list of NwkId to be scaned
    data = data.decode('utf8')
    data = json.loads(data)
    self.logging( 'Debug', "rest_scan_devices_for_group - Trigger GroupMemberShip scan for devices: %s " %(data))
    self.groupmgt.ScanDevicesForGroupMemberShip( data )
    action = {'Name': 'Scan of device requested.', 'TimeStamp': int(time())}
    _response["Data"] = json.dumps( action , sort_keys=True )
    return _response

def rest_zGroup( self, verb, data, parameters):

    _response = prepResponseMessage( self ,setupHeadersResponse(  ))

    self.logging( 'Debug', "rest_zGroup - ListOfGroups = %s" %str(self.groupmgt))

    if verb == 'GET':
        if self.groupmgt is None:
            return _response

        ListOfGroups = self.groupmgt.ListOfGroups
        if ListOfGroups is None or len(ListOfGroups) == 0:
            return _response

        if len(parameters) == 0:
            zgroup_lst = []
            for itergrp in ListOfGroups:
                self.logging( 'Debug', "Process Group: %s" %itergrp)
                zgroup = {}
                zgroup['_GroupId'] = itergrp
                zgroup['GroupName'] = ListOfGroups[itergrp]['Name']
                zgroup['Devices'] = []
                for itemDevice in ListOfGroups[itergrp]['Devices']:
                    if len(itemDevice) == 2:
                        dev, ep = itemDevice
                        ieee = self.ListOfDevices[dev]['IEEE']

                    elif len(itemDevice) == 3:
                        dev, ep, ieee = itemDevice

                    self.logging( 'Debug', "--> add %s %s %s" %(dev, ep, ieee))
                    _dev = {}
                    _dev['_NwkId'] = dev
                    _dev['Ep'] = ep
                    _dev['IEEE'] = ieee
                    zgroup['Devices'].append( _dev )

                if 'WidgetStyle' in ListOfGroups[itergrp]:
                    zgroup['WidgetStyle'] = ListOfGroups[itergrp]['WidgetStyle']

                if 'Cluster' in ListOfGroups[itergrp]:
                    zgroup['Cluster'] = ListOfGroups[itergrp]['Cluster']

                # Let's check if we don't have an Ikea Remote in the group
                if 'Tradfri Remote' in ListOfGroups[itergrp]:
                    self.logging( 'Debug', "--> add Ikea Tradfri Remote")
                    _dev = {}
                    _dev['_NwkId'] = ListOfGroups[itergrp]["Tradfri Remote"]["Device Addr"]
                    _dev['Unit'] = ListOfGroups[itergrp]["Tradfri Remote"]['Device Id']
                    _dev['Ep'] = ListOfGroups[itergrp]["Tradfri Remote"]["Ep"]
                    _dev['Color Mode'] = ListOfGroups[itergrp]["Tradfri Remote"]["Color Mode"]
                    zgroup['Devices'].append( _dev )
                zgroup_lst.append(zgroup)
            self.logging( 'Debug', "zGroup: %s" %zgroup_lst)
            _response["Data"] = json.dumps( zgroup_lst, sort_keys=True )

        elif len(parameters) == 1:
            if parameters[0] in ListOfGroups:
                itemGroup =  parameters[0]
                zgroup = {}
                zgroup['_GroupId'] = itemGroup
                zgroup['GroupName'] = ListOfGroups[itemGroup]['Name']
                zgroup['Devices'] = {}
                for itemDevice in ListOfGroups[itemGroup]['Devices']:
                    if len(itemDevice) == 2:
                        dev, ep = itemDevice
                        _ieee = self.ListOfDevices[dev]['IEEE']

                    elif len(itemDevice) == 3:
                        dev, ep, _ieee = itemDevice

                    self.logging( 'Debug', "--> add %s %s" %(dev, ep))
                    zgroup['Devices'][dev] = ep 

                # Let's check if we don't have an Ikea Remote in the group
                if 'Tradfri Remote' in ListOfGroups[itemGroup]:
                    self.logging( 'Log', "--> add Ikea Tradfri Remote")
                    _dev = {}
                    _dev['_NwkId'] = ListOfGroups[itemGroup]["Tradfri Remote"]["Device Addr"]
                    _dev['Ep'] = "01"
                    zgroup['Devices'].append( _dev )
                _response["Data"] = json.dumps( zgroup, sort_keys=True )

        return _response

    if verb == 'PUT':
        _response["Data"] = None
        if  not self.groupmgt:
            Domoticz.Error("Looks like Group Management is not enabled")
            _response["Data"] = {}
            return _response

        ListOfGroups = self.groupmgt.ListOfGroups
        grp_lst = []
        if len(parameters) == 0:
            data = data.decode('utf8')
            _response["Data"] = {}
            self.groupmgt.process_web_request(  json.loads(data) )

        # end if len()
    # end if Verb=

    return _response