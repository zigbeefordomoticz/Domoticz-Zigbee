#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#


import Domoticz
import json


from WebServer.headerResponse import setupHeadersResponse, prepResponseMessage


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
                    _dev['Ep'] = "01"
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
            self.restart_needed['RestartNeeded'] = True
            data = data.decode('utf8')
            data = json.loads(data)
            self.logging( 'Debug', "data: %s" %data)
            for item in data:
                self.logging( 'Debug', "item: %s" %item)
                if '_GroupId' not in item:
                    self.logging( 'Debug', "--->Adding Group: ")
                    # Define a GroupId 
                    for x in range( 0x0001, 0x0999):
                        grpid = '%04d' %x
                        if grpid not in ListOfGroups:
                            break
                    else:
                        Domoticz.Error("Out of GroupId")
                        continue
                    ListOfGroups[grpid] = {}
                    ListOfGroups[grpid]['Name'] = item['GroupName']
                    ListOfGroups[grpid]['Devices'] = []
                else:
                    if item['_GroupId'] not in ListOfGroups:
                        Domoticz.Error("zGroup REST API - unknown GroupId: %s" %grpid)
                        continue
                    grpid = item['_GroupId']

                grp_lst.append( grpid ) # To memmorize the list of Group
                #Update Group
                self.logging( 'Debug', "--->Checking Group: %s" %grpid)
                if item['GroupName'] != ListOfGroups[grpid]['Name']:
                    # Update the GroupName
                    self.logging( 'Debug', "------>Updating Group from :%s to : %s" %( ListOfGroups[grpid]['Name'], item['GroupName']))
                    self.groupmgt._updateDomoGroupDeviceWidgetName( item['GroupName'], grpid )

                newdev = []
                if 'devicesSelected' not in item:
                    continue
                if 'GroupName' in item:
                    if item['GroupName'] == '':
                        continue
                for devselected in item['devicesSelected']:
                    if 'IEEE' in devselected:
                        ieee = devselected['IEEE']
                    elif '_NwkId' in devselected:
                        nwkid = devselected['_NwkId']
                        if nwkid != '0000' and nwkid not in self.ListOfDevices:
                            Domoticz.Error("Not able to find nwkid: %s" %(nwkid))
                            continue
                        if 'IEEE' not in self.ListOfDevices[nwkid]:
                            Domoticz.Error("Not able to find IEEE for %s - no IEEE entry in %s" %(nwkid, self.ListOfDevices[nwkid]))
                            continue
                        ieee = self.ListOfDevices[nwkid]['IEEE']
                    else: 
                        Domoticz.Error("Not able to find IEEE for %s" %(_dev))
                        continue
                    self.logging( 'Debug', "------>Checking device : %s/%s" %(devselected['_NwkId'], devselected['Ep']))
                    # Check if this is not an Ikea Tradfri Remote
                    nwkid = devselected['_NwkId']
                    _tradfri_remote = False
                    if 'Ep' in self.ListOfDevices[nwkid]:
                        if '01' in self.ListOfDevices[nwkid]['Ep']:
                            if 'ClusterType' in self.ListOfDevices[nwkid]['Ep']['01']:
                                for iterDev in self.ListOfDevices[nwkid]['Ep']['01']['ClusterType']:
                                    if self.ListOfDevices[nwkid]['Ep']['01']['ClusterType'][iterDev] == 'Ikea_Round_5b':
                                        # We should not process it through the group.
                                        self.logging( 'Debug', "------>Not processing Ikea Tradfri as part of Group. Will enable the Left/Right actions")
                                        ListOfGroups[grpid]['Tradfri Remote'] = {}
                                        ListOfGroups[grpid]['Tradfri Remote']['Device Addr'] = nwkid
                                        ListOfGroups[grpid]['Tradfri Remote']['Device Id'] = iterDev
                                        _tradfri_remote = True
                    if _tradfri_remote:
                        continue
                    # Process the rest
                    for itemDevice in ListOfGroups[grpid]['Devices']:
                        if len(itemDevice) == 2:
                            _dev, _ep = itemDevice
                            _ieee = self.ListOfDevices[dev]['IEEE']
                        elif len(itemDevice) == 3:
                            _dev, _ep, _ieee = itemDevice

                        if _dev == devselected['_NwkId'] and _ep == devselected['Ep']:
                            if (ieee, _ep) not in newdev:
                                self.logging( 'Debug', "------>--> %s to be added to group %s" %( (ieee, _ep), grpid))
                                newdev.append( (ieee, _ep) )
                            else:
                                self.logging( 'Debug', "------>--> %s already in %s" %( (ieee, _ep), newdev))
                            break
                    else:
                        if (ieee, devselected['Ep']) not in newdev:
                            self.logging( 'Debug', "------>--> %s to be added to group %s" %( (ieee, devselected['Ep']), grpid))
                            newdev.append( (ieee, devselected['Ep']) )
                        else:
                            self.logging( 'Debug', "------>--> %s already in %s" %( (_dev, _ep), newdev))
                # end for devselecte

                if 'coordinatorInside' in item:
                    if item['coordinatorInside']:
                        if 'IEEE' in self.zigatedata:
                            ieee_zigate = self.zigatedata['IEEE']
                            if ( ieee_zigate, '01') not in newdev:
                                self.logging( 'Debug', "------>--> %s to be added to group %s" %( (ieee_zigate, '01'), grpid))
                                newdev.append( (ieee_zigate, _ep) )

                self.logging( 'Debug', "--->Devices Added: %s" %newdev)
                ListOfGroups[grpid]['Imported'] = list( newdev )
                self.logging( 'Debug', "--->Grp: %s - tobe Imported: %s" %(grpid, ListOfGroups[grpid]['Imported']))

            # end for item / next group
            # Finaly , we need to check if AnyGroup have been removed !
            self.logging( 'Debug', "Group to be removed")
            Domoticz.Log("ListOfGroups: %s" %ListOfGroups)
            for grpid in ListOfGroups:
                if grpid not in grp_lst:
                    self.logging( 'Debug', "--->Group %s has to be removed" %grpid)
                    if 'Imported' in ListOfGroups[grpid]:
                        del ListOfGroups[grpid]['Imported']
                    ListOfGroups[grpid]['Imported'] = []

            self.logging( 'Debug', "Group to be worked out")
            for grpid in ListOfGroups:
                self.logging( 'Debug', "Group: %s" %grpid)
                if 'Imported' in ListOfGroups[grpid]:
                    for dev in ListOfGroups[grpid]['Imported']:
                        self.logging( 'Debug', "---> %s to be imported" %str(dev))

            self.groupmgt.write_jsonZigateGroupConfig()
        # end if len()
    # end if Verb=

    return _response