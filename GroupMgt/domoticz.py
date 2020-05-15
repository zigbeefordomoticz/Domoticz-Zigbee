#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#


import Domoticz
import json

from Modules.tools import Hex_Format, rgb_to_xy, rgb_to_hsl
from Modules.zigateConsts import ADDRESS_MODE, MAX_LOAD_ZIGATE, ZIGATE_EP

#from Classes.AdminWidgets import AdminWidgets


def deviceChangeNetworkID( self, old_nwkid, new_nwkid):
    """
    this method is call whenever a device get a new NetworkId.
    We then if this device is own by a group to update the networkid.
    """
    _updatedGroupFileNeeded = False
    for iterGrp in self.ListOfGroups:
        _updatedDevice = False
        self.logging( 'Debug', "deviceChangeNetworkID - ListOfGroups[%s]['Devices']: %s" %(iterGrp, self.ListOfGroups[iterGrp]['Devices']))
        old_listDev = list(self.ListOfGroups[iterGrp]['Devices'])
        new_listDev = []
        for iterList in old_listDev:
            if iterList[0] == old_nwkid:
                _updatedDevice = True
                new_listDev.append( (new_nwkid, iterList[1] ) )
            else:
                new_listDev.append( iterList )

        if _updatedDevice:
            self.logging( 'Status', "GroupMgr - Update needed for group %s, from device List %s to %s" %( iterGrp, str(self.ListOfGroups[iterGrp]['Devices']), str(new_listDev)))
            del self.ListOfGroups[iterGrp]['Devices']
            self.ListOfGroups[iterGrp]['Devices'] = new_listDev
            _updatedGroupFileNeeded = True

    if _updatedGroupFileNeeded:
        # Store Group in report under json format
        self._write_GroupList()

        json_filename = self.groupListReport
        with open( json_filename, 'wt') as json_file:
            json_file.write('\n')
            json.dump( self.ListOfGroups, json_file, indent=4, sort_keys=True)


# Domoticz relaed
def _createDomoGroupDevice(self, groupname, group_nwkid):
    ' Create Device for just created group in Domoticz. '

    def FreeUnit(self, Devices):
        '''
        FreeUnit
        Look for a Free Unit number.
        '''
        FreeUnit = ""
        for x in range(1, 255):
            if x not in Devices:
                self.logging( 'Debug', "FreeUnit - device " + str(x) + " available")
                return x
        else:
            self.logging( 'Debug', "FreeUnit - device " + str(len(Devices) + 1))
            return len(Devices) + 1


    if groupname == '' or group_nwkid == '':
        Domoticz.Error("createDomoGroupDevice - Invalid Group Name: %s or GroupdID: %s" %(groupname, group_nwkid))

    for x in self.Devices:
        if self.Devices[x].DeviceID == group_nwkid:
            Domoticz.Error("_createDomoGroupDevice - existing group %s" %(self.Devices[x].Name))
            return

    Type_, Subtype_, SwitchType_ = self._bestGroupWidget( group_nwkid)

    unit = self.FreeUnit( self.Devices )
    self.logging( 'Debug', "_createDomoGroupDevice - Unit: %s" %unit)
    myDev = Domoticz.Device(DeviceID=str(group_nwkid), Name=str(groupname), Unit=unit, Type=Type_, Subtype=Subtype_, Switchtype=SwitchType_)
    myDev.Create()
    ID = myDev.ID
    if ID == -1:
        Domoticz.Error('CreateDomoGroupDevice - failed to create Group device.')
    else:
        self.adminWidgets.updateNotificationWidget(
            self.Devices, 'Groups %s created' % groupname
        )

def _updateDomoGroupDeviceWidgetName( self, groupname, group_nwkid ):

    if groupname == '' or group_nwkid == '':
        Domoticz.Error("_updateDomoGroupDeviceWidget - Invalid Group Name: %s or GroupdID: %s" %(groupname, group_nwkid))

    unit = 0
    for x in self.Devices:
        if self.Devices[x].DeviceID == group_nwkid:
            unit = x
            break
    else:
        Domoticz.Error("_updateDomoGroupDeviceWidget - Group doesn't exist %s / %s" %(groupname, group_nwkid))

    nValue = self.Devices[unit].nValue
    sValue = self.Devices[unit].sValue
    self.Devices[unit].Update( nValue, sValue, Name=groupname)

    # Update Group Structure
    self.ListOfGroups[group_nwkid]['Name'] = groupname

    # Write it in the Pickle file
    self._write_GroupList()

def _updateDomoGroupDeviceWidget( self, groupname, group_nwkid ):

    if groupname == '' or group_nwkid == '':
        Domoticz.Error("_updateDomoGroupDeviceWidget - Invalid Group Name: %s or GroupdID: %s" %(groupname, group_nwkid))

    unit = 0
    for x in self.Devices:
        if self.Devices[x].DeviceID == group_nwkid:
            unit = x
            break
    else:
        Domoticz.Error("_updateDomoGroupDeviceWidget - Group doesn't exist %s / %s" %(groupname, group_nwkid))

    Type_, Subtype_, SwitchType_ = self._bestGroupWidget( group_nwkid)

    if Type_ != self.Devices[unit].Type or Subtype_ != self.Devices[unit].SubType or SwitchType_ != self.Devices[unit].SwitchType :
        self.logging( 'Debug', "_updateDomoGroupDeviceWidget - Update Type:%s, Subtype:%s, Switchtype:%s" %(Type_, Subtype_, SwitchType_))
        self.Devices[unit].Update( 0, 'Off', Type=Type_, Subtype=Subtype_, Switchtype=SwitchType_)

def _bestGroupWidget( self, group_nwkid):

    WIDGETS = {
            'Plug':1,                 # ( 244, 73, 0)
            'Switch':1,               # ( 244, 73, 0)
            'LvlControl':2,           # ( 244, 73, 7)
            'ColorControlWW':3,       # ( 241, 8, 7) - Cold white + warm white
            'ColorControlRGB':3,      # ( 241, 2, 7) - RGB
            'ColorControlRGBWW':4,    # ( 241, 4, 7) - RGB + cold white + warm white, either RGB or white can be lit
            'ColorControl':5,         # ( 241, 7, 7) - Like RGBWW, but allows combining RGB and white
            'ColorControlFull':5,     # ( 241, 7, 7) - Like RGBWW, but allows combining RGB and white
            'Venetian': 10,           # ( 244, 73, 15) # Shade, Venetian
            'VenetianInverted': 11,   # ( 244, 73, 15)
            'WindowCovering': 12,     # ( 244, 73, 16)  # Venetian Blind EU 
            'BlindPercentInverted': 12,     # ( 244, 73, 16)  # Venetian Blind EU 
            }

    WIDGET_STYLE = {
            'Plug': ( 244, 73, 0 ),
            'Switch': ( 244, 73, 0 ),
            'LvlControl' : ( 244, 73, 7 ),
            'BlindPercentInverted': ( 244, 73, 16 ),
            'WindowCovering': ( 244, 73, 16 ),
            'Venetian': ( 244, 73, 15 ),
            'VenetianInverted': ( 244, 73, 15 ),
            'ColorControlWW': ( 241, 8, 7 ),
            'ColorControlRGB': ( 241, 2, 7 ),
            'ColorControlRGBWW': ( 241, 4, 7),
            'ColorControlFull': ( 241, 7,7 ),
            }

    code = 0
    _ikea_colormode = None
    color_widget = None
    widget_style = None
    widget = WIDGET_STYLE['ColorControlFull']    # If not match, will create a RGBWWZ widget

    for devNwkid, devEp, iterIEEE in self.ListOfGroups[group_nwkid]['Devices']:
        if devNwkid == '0000': 
            continue

        self.logging( 'Log', "bestGroupWidget - Group: %s processing %s" %(group_nwkid,devNwkid))
        if devNwkid not in self.ListOfDevices:
            continue

        if 'ClusterType' not in self.ListOfDevices[devNwkid]['Ep'][devEp]:
            continue

        for iterClusterType in self.ListOfDevices[devNwkid]['Ep'][devEp]['ClusterType']:
            if self.ListOfDevices[devNwkid]['Ep'][devEp]['ClusterType'][iterClusterType] in WIDGETS:
                devwidget = self.ListOfDevices[devNwkid]['Ep'][devEp]['ClusterType'][iterClusterType]
                if code <= WIDGETS[devwidget]:
                    code = WIDGETS[devwidget]
                    # Blind/ Venetian
                    if code == 10:
                        widget = WIDGET_STYLE['Venetian']
                        widget_style =  'Venetian'

                    elif code == 12:
                        widget = WIDGET_STYLE['WindowCovering']
                        widget_style =  'WindowCovering'

                    if code == 1:
                        widget = WIDGET_STYLE['Switch']
                        widget_style =  'Switch'

                    elif code == 2: 
                        # Let's check if this is not a Blind Percentage Inverted
                        for _dev in self.Devices:
                            if self.Devices[_dev].ID == int(iterClusterType):
                                if self.Devices[ _dev ].SwitchType == 16: # BlindPercentInverted
                                    widget = WIDGET_STYLE['BlindPercentInverted']
                                    widget_style =  'BlindPercentInverted'

                                else:
                                    widget = WIDGET_STYLE['LvlControl']
                                    widget_style =  'LvlControl'

                                break

                        else:
                            Domoticz.Error ('Device not found')
                            widget = WIDGET_STYLE['LvlControl']
                            widget_style =  'LvlControl'

                    elif code == 3:
                        if color_widget is None:
                            if devwidget in [
                                'ColorControlWW',
                                'ColorControlRGB',
                            ]:
                                widget = WIDGET_STYLE[ devwidget ]
                                _ikea_colormode = devwidget

                        elif color_widget == devwidget:
                            continue

                        elif (devwidget == 'ColorControlWW' and color_widget == 'ColorControlRGB') or \
                                ( color_widget == 'ColorControlWW' and devwidget == 'ColorControlRGB' ) :
                            code = 4
                            color_widget = 'ColorControlRGBWW'
                            widget = WIDGET_STYLE[ color_widget ]
                            _ikea_colormode = color_widget

                        elif devwidget == 'ColorControl':
                            code = 5
                            color_widget = 'ColorControlFull'
                            widget = WIDGET_STYLE[ color_widget ]
                            _ikea_colormode = color_widget

                    elif code == 4: 
                        color_widget = 'ColorControlRGBWW'
                        widget = WIDGET_STYLE[ color_widget ]
                        _ikea_colormode = color_widget

                    elif code == 5:
                        color_widget = 'ColorControlFull'
                        widget = WIDGET_STYLE[ color_widget ]
                        _ikea_colormode = color_widget

                pre_code = code

        self.logging( 'Debug', "--------------- - processing %s code: %s widget: %s, color_widget: %s _ikea_colormode: %s " 
                %(devNwkid, code, widget, color_widget, _ikea_colormode))

    if color_widget:
        self.ListOfGroups[group_nwkid]['WidgetStyle'] = color_widget

    elif widget_style:
        self.ListOfGroups[group_nwkid]['WidgetStyle'] = widget_style

    else:
        self.ListOfGroups[group_nwkid]['WidgetStyle'] = ''

    if self.ListOfGroups[group_nwkid]['WidgetStyle'] in  ( 'Switch', 'Plug' ):
        self.ListOfGroups[group_nwkid]['Cluster'] = '0006'

    elif self.ListOfGroups[group_nwkid]['WidgetStyle'] in ( 'LvlControl' ):
        self.ListOfGroups[group_nwkid]['Cluster'] = '0008'

    elif self.ListOfGroups[group_nwkid]['WidgetStyle'] in ( 'ColorControlWW', 'ColorControlRGB', 'ColorControlRGB', 'ColorControlRGBWW', 'ColorControl', 'ColorControlFull'):
        self.ListOfGroups[group_nwkid]['Cluster'] = '0300'

    elif self.ListOfGroups[group_nwkid]['WidgetStyle'] in ( 'Venetian', 'WindowCovering', 'VenetianInverted'):
        self.ListOfGroups[group_nwkid]['Cluster'] = '0102'

    else:
        self.ListOfGroups[group_nwkid]['Cluster'] = ''

    # This will be used when receiving left/right click , to know if it is RGB or WW
    if 'Tradfri Remote' in self.ListOfGroups[group_nwkid]:
        self.ListOfGroups[group_nwkid]['Tradfri Remote']['Color Mode'] = _ikea_colormode

    self.logging( 'Log', "_bestGroupWidget - %s Code: %s, Color_Widget: %s, widget: %s, WidgetStyle: %s" %( group_nwkid, code, color_widget, widget, self.ListOfGroups[group_nwkid]['WidgetStyle']))
    return widget

def updateDomoGroupDevice( self, group_nwkid):
    """ 
    Update the Group status On/Off and Level , based on the attached devices
    """

    if group_nwkid not in self.ListOfGroups:
        Domoticz.Error("updateDomoGroupDevice - unknown group: %s" %group_nwkid)
        return

    if 'Devices' not in self.ListOfGroups[group_nwkid]:
        self.logging( 'Debug', "updateDomoGroupDevice - no Devices for that group: %s" %self.ListOfGroups[group_nwkid])
        return

    unit = 0
    for unit in self.Devices:
        if self.Devices[unit].DeviceID == group_nwkid:
            break
    else:
        return

    # If one device is on, then the group is on. If all devices are off, then the group is off
    nValue = 0
    level = None

    
    for item in self.ListOfGroups[group_nwkid]['Devices']:
        if len(item) == 2:
            dev_nwkid, dev_ep = item
            dev_ieee = self.ListOfDevices[dev_nwkid]['IEEE']

        elif len(item) == 3:
            dev_nwkid, dev_ep, dev_ieee = item

        else:
            Domoticz.Error("Invalid item %s" %str(item))
            continue

        if dev_nwkid in self.ListOfDevices:
            if 'Ep' in  self.ListOfDevices[dev_nwkid]:
                if dev_ep in self.ListOfDevices[dev_nwkid]['Ep']:
                    if '0006' in self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]:
                        if '0000' in self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0006']:
                            if str(self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0006']['0000']).isdigit():
                                if int(self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0006']['0000']) != 0:
                                    nValue = 1
                    if '0008' in self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]:
                        if '0000' in self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008']:
                            if self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008']['0000'] != '' and self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008']['0000'] != {}:
                                if level is None:
                                    level = int(self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008']['0000'],16)
                                else:
                                    level = round(( level +  int(self.ListOfDevices[dev_nwkid]['Ep'][dev_ep]['0008']['0000'],16)) / 2)
                    self.logging( 'Debug', "updateDomoGroupDevice - Processing: Group: %s %s/%s nValue: %s, level: %s" %(group_nwkid, dev_nwkid, dev_ep, nValue, level))

    self.logging( 'Debug', "updateDomoGroupDevice - Processing: Group: %s ==> nValue: %s, level: %s" %(group_nwkid, nValue, level))
    # At that stage
    # nValue == 0 if Off
    # nValue == 1 if Open/On
    # level is None, so we use nValue/sValue
    # level is not None; so we have a LvlControl
    if level:
        if self.Devices[unit].SwitchType != 16:
            # Not a Shutter/Blind
            analogValue = level
            if analogValue >= 255:
                sValue = 100

            else:
                sValue = round((level * 100) / 255)
                if sValue > 100: 
                    sValue = 100

                if sValue == 0 and analogValue > 0:
                    sValue = 1

        else:
            # Shutter/blind
            if nValue == 0: # we are in an Off mode
                sValue = 0

            else:
                # We are on either full or not
                sValue = round((level * 100) / 255)
                if sValue >= 100: 
                    sValue = 100
                    nValue = 1

                elif sValue > 0 and sValue < 100:
                    nValue = 2

                else:
                    nValue = 0

        sValue = str(sValue)

    else:
        if nValue == 0:
            sValue = 'Off'

        else:
            sValue = 'On'

    self.logging( 'Debug', "updateDomoGroupDevice - Processing: Group: %s ==> nValue: %s, sValue: %s" %(group_nwkid, nValue, sValue))
    if nValue != self.Devices[unit].nValue or sValue != self.Devices[unit].sValue:
        self.logging( 'Log', "UpdateGroup  - (%15s) %s:%s" %( self.Devices[unit].Name, nValue, sValue ))
        self.Devices[unit].Update( nValue, sValue)

def _removeDomoGroupDevice(self, group_nwkid):
    ' User has removed the Domoticz Device corresponding to this group'

    if group_nwkid not in self.ListOfGroups:
        Domoticz.Error("_removeDomoGroupDevice - unknown group: %s" %group_nwkid)
        return

    unit = 0
    for unit in self.Devices:
        if self.Devices[unit].DeviceID == group_nwkid:
            break

    else:
        Domoticz.Error("_removeDomoGroupDevice - no Devices found in Domoticz: %s" %group_nwkid)
        return

    self.logging( 'Debug', "_removeDomoGroupDevice - removing Domoticz Widget %s" %self.Devices[unit].Name)
    self.adminWidgets.updateNotificationWidget( self.Devices, 'Groups %s deleted' %self.Devices[unit].Name)
    self.Devices[unit].Delete()
    
# Group Management methods
def processRemoveGroup( self, unit, grpid):

    # Remove all devices from the corresponding group
    if grpid not in self.ListOfGroups:
        return

    _toremove = []
    for iterDev in list(self.ListOfDevices):
        if 'GroupMgt' not in self.ListOfDevices[iterDev]:
            continue

        for iterEP in self.ListOfDevices[iterDev]['Ep']:
            if iterEP not in self.ListOfDevices[iterDev]['GroupMgt']:
                continue

            if grpid in self.ListOfDevices[iterDev]['GroupMgt'][iterEP]:
                self.logging( 'Debug', "processRemoveGroup - remove %s %s %s" 
                        %(iterDev, iterEP, grpid))
                self._removeGroup(iterDev, iterEP, grpid )
                _toremove.append( (iterDev,iterEP) )
    for removeDev, removeEp in _toremove:
        del self.ListOfDevices[removeDev]['GroupMgt'][removeEp][grpid]

    del self.ListOfGroups[grpid]

def _updateDeviceListAttribute( self, grpid, cluster, value):

    if grpid not in self.ListOfGroups:
        return

    # search for all Devices in the group
    for iterItem in self.ListOfGroups[grpid]['Devices']:
        if len(iterItem) == 3:
            iterDev,  iterEp, iterIEEE = iterItem

        elif len(iterItem) == 2:
            iterDev, iterEp = iterItem
            if iterDev in self.ListOfDevices:
                iterIEEE = self.ListOfDevices[iterDev]['IEEE']

            else:
                Domoticz.Error("Unknown device %s, it is recommended to do a full rescan of Groups" %iterDev)
                continue
        else:
            continue

        if iterDev == '0000': 
            continue

        if iterDev not in self.ListOfDevices:
            Domoticz.Error("_updateDeviceListAttribute - Device: %s of Group: %s not in the list anymore" %(iterDev,grpid))
            continue

        if iterEp not in self.ListOfDevices[iterDev]['Ep']:
            Domoticz.Error("_updateDeviceListAttribute - Not existing Ep: %s for Device: %s in Group: %s" %(iterEp, iterDev, grpid))
            continue

        if 'ClusterType' not in self.ListOfDevices[iterDev]['Ep'][iterEp] and 'ClusterType' not in self.ListOfDevices[iterDev]:
            Domoticz.Error("_updateDeviceListAttribute - No Widget attached to Device: %s/%s in Group: %s" %(iterDev,iterEp,grpid))
            continue

        if cluster not in self.ListOfDevices[iterDev]['Ep'][iterEp]:
            self.logging( 'Debug', "_updateDeviceListAttribute - Cluster: %s doesn't exist for Device: %s/%s in Group: %s" %(cluster,iterDev,iterEp,grpid))
            continue

        if cluster not in self.ListOfDevices[iterDev]['Ep'][iterEp]:
            self.ListOfDevices[iterDev]['Ep'][iterEp][cluster] = {}
        if not isinstance( self.ListOfDevices[iterDev]['Ep'][iterEp][cluster] , dict):
            self.ListOfDevices[iterDev]['Ep'][iterEp][cluster] = {}
        if '0000' not in self.ListOfDevices[iterDev]['Ep'][iterEp][cluster]:
            self.ListOfDevices[iterDev]['Ep'][iterEp][cluster]['0000'] = {}

        self.ListOfDevices[iterDev]['Ep'][iterEp][cluster]['0000'] = value
        self.logging( 'Debug', "_updateDeviceListAttribute - Updating Device: %s/%s of Group: %s Cluster: %s to value: %s" %(iterDev, iterEp, grpid, cluster, value))

    return

def processCommand( self, unit, nwkid, Command, Level, Color_ ) : 

    self.logging( 'Debug', "processCommand - unit: %s, nwkid: %s, cmd: %s, level: %s, color: %s" %(unit, nwkid, Command, Level, Color_))

    if nwkid not in self.ListOfGroups:
        return

    for iterDevice in self.ListOfGroups[nwkid]['Devices']:
        if len(iterDevice) == 2:
            iterDev, iterEp = iterDevice
            if iterDev in self.ListOfDevices:
                if 'IEEE' in self.ListOfDevices[iterDev]:
                    iterIEEE = self.ListOfDevices[iterDev]['IEEE']
        elif len(iterDevice) == 3:
            iterDev, iterEp, iterIEEE = iterDevice
        else:
            Domoticz.Error("Group - processCommand - Error unexpected item: %s" %str(iterDevice))
            return

        self.logging( 'Debug', 'processCommand - reset heartbeat for device : %s' %iterDev)
        if iterDev not in self.ListOfDevices:
            if iterIEEE in self.IEEE2NWK:
                iterDev = self.IEEE2NWK[ iterIEEE ]
                
        if iterDev in self.ListOfDevices:
            # Force Read Attribute consideration in the next hearbeat
            if 'Heartbeat' in self.ListOfDevices[iterDev]:
                self.ListOfDevices[iterDev]['Heartbeat'] = '0'

            # Reset ReadAttrinbutes, in order to force a Polling
            if 'ReadAttributes' in  self.ListOfDevices[iterDev]:
                if 'TimeStamps' in self.ListOfDevices[iterDev]['ReadAttributes']:
                    del self.ListOfDevices[iterDev]['ReadAttributes']['TimeStamps']

            # Reset Health status of corresponding device if any in Not Reachable
            if 'Health' in self.ListOfDevices[iterDev]:
                if self.ListOfDevices[iterDev]['Health'] == 'Not Reachable':
                    self.ListOfDevices[iterDev]['Health'] = ''
        else:
            Domoticz.Error("processCommand - Looks like device %s [%s] does not exist anymore and you expect to be part of group %s" %(iterDev, iterIEEE, nwkid))

    EPin = EPout = '01'

    if 'Cluster' in self.ListOfGroups[ nwkid ]:
        # new fashon
        if self.ListOfGroups[ nwkid ]['Cluster'] == '0102': # Venetian store
            zigate_cmd = "00FA"
            if Command == 'Off' :
                zigate_param = '00'
                nValue = 1
                sValue = 'Off'
                self._updateDeviceListAttribute( nwkid, '0102', zigate_param)

            if Command == 'On' :
                zigate_param = '01'
                nValue = 0
                sValue = 'Off'
                self._updateDeviceListAttribute( nwkid, '0102', zigate_param)

            if Command == 'Stop':
                zigate_param = '02'
                nValue = 2
                sValue = '50'
                self._updateDeviceListAttribute( nwkid, '0102', zigate_param)

            self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
            self._updateDeviceListAttribute( nwkid, '0102', zigate_param)
            datas = "%02d" %ADDRESS_MODE['group'] + nwkid + ZIGATE_EP + EPout + zigate_param
            self.logging( 'Debug', "Group Command: %s" %datas)
            self.ZigateComm.sendData( zigate_cmd, datas)
            return

    # Old Fashon
    if Command == 'Off' :
        zigate_cmd = "0092"
        zigate_param = '00'
        nValue = 0
        sValue = 'Off'
        self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
        self._updateDeviceListAttribute( nwkid, '0006', '00')
        self.updateDomoGroupDevice( nwkid)
        #datas = "01" + nwkid + EPin + EPout + zigate_param
        datas = "%02d" %ADDRESS_MODE['group'] + nwkid + ZIGATE_EP + EPout + zigate_param
        self.logging( 'Debug', "Command: %s" %datas)
        self.ZigateComm.sendData( zigate_cmd, datas)

    if Command == 'On' :
        zigate_cmd = "0092"
        zigate_param = '01'
        nValue = '1'
        sValue = 'On'
        self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
        self._updateDeviceListAttribute( nwkid, '0006', '01')

        self.updateDomoGroupDevice( nwkid)
        #datas = "01" + nwkid + EPin + EPout + zigate_param
        datas = "%02d" %ADDRESS_MODE['group'] + nwkid + ZIGATE_EP + EPout + zigate_param
        self.logging( 'Debug', "Command: %s" %datas)
        self.ZigateComm.sendData( zigate_cmd, datas)


    if Command == 'Set Level':
        # Level: % value of move
        # Converted to value , raw value from 0 to 255
        # sValue is just a string of Level
        zigate_cmd = "0081"
        OnOff = "01"
        #value=int(Level*255//100)
        value = '%02X' %int(Level*255//100)
        zigate_param = OnOff + value + "0010"
        nValue = '1'
        sValue = str(Level)
        self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
        self._updateDeviceListAttribute( nwkid, '0008', value)
        datas = "%02d" %ADDRESS_MODE['group'] + nwkid + ZIGATE_EP + EPout + zigate_param
        self.logging( 'Debug', "Command: %s" %datas)
        self.ZigateComm.sendData( zigate_cmd, datas)
        self.updateDomoGroupDevice( nwkid)

    if Command == "Set Color" :
        Hue_List = json.loads(Color_)
        #First manage level
        OnOff = '01' # 00 = off, 01 = on
        value = '%02X' %round(1+Level*254/100)
        #value=Hex_Format(2,round(1+Level*254/100)) #To prevent off state
        zigate_cmd = "0081"
        zigate_param = OnOff + value + "0000"
        datas = "%02d" %ADDRESS_MODE['group'] + nwkid + ZIGATE_EP + EPout + zigate_param
        self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd,datas))
        self._updateDeviceListAttribute( nwkid, '0008', value)
        self.ZigateComm.sendData( zigate_cmd, datas)

        if Hue_List['m'] == 1:
            ww = int(Hue_List['ww']) # Can be used as level for monochrome white
            self.logging( 'Debug', "Not implemented device color 1")
        #ColorModeTemp = 2   // White with color temperature. Valid fields: t
        if Hue_List['m'] == 2:
            self.set_Kelvin_Color( ADDRESS_MODE['group'], nwkid, EPin, EPout, int(Hue_List['t']))

        #ColorModeRGB = 3    // Color. Valid fields: r, g, b.
        elif Hue_List['m'] == 3:
            self.set_RGB_color( ADDRESS_MODE['group'], nwkid, EPin, EPout, \
                    int(Hue_List['r']), int(Hue_List['g']), int(Hue_List['b']))

        #ColorModeCustom = 4, // Custom (color + white). Valid fields: r, g, b, cw, ww, depending on device capabilities
        elif Hue_List['m'] == 4:
            ww = int(Hue_List['ww'])
            cw = int(Hue_List['cw'])
            x, y = rgb_to_xy((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
            self.logging( 'Debug', "Not implemented device color 2")

        #With saturation and hue, not seen in domoticz but present on zigate, and some device need it
        elif Hue_List['m'] == 9998:
            h,l,s = rgb_to_hsl((int(Hue_List['r']),int(Hue_List['g']),int(Hue_List['b'])))
            saturation = s * 100   #0 > 100
            hue = h *360           #0 > 360
            hue = int(hue*254//360)
            saturation = int(saturation*254//100)
            Level = l
            value = '%02X' %round(1+Level*254/100)
            #value=Hex_Format(2,round(1+Level*254/100)) #To prevent off state

            OnOff = '01'
            zigate_cmd = "00B6"
            zigate_param = Hex_Format(2,hue) + Hex_Format(2,saturation) + "0000"
            datas = "%02d" %ADDRESS_MODE['group'] + nwkid + ZIGATE_EP + EPout + zigate_param
            self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd,datas))
            self.ZigateComm.sendData( zigate_cmd, datas)
            zigate_cmd = "0081"
            zigate_param = OnOff + value + "0010"
            datas = "%02d" %ADDRESS_MODE['group'] + nwkid + ZIGATE_EP + EPout + zigate_param
            self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd,datas))
            self.ZigateComm.sendData( zigate_cmd, datas)
            self._updateDeviceListAttribute( nwkid, '0008', value)

        #Update Device
        nValue = 1
        sValue = str(Level)
        self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue), Color=Color_)