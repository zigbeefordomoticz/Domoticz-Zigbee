# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#


import Domoticz
import json

from Modules.tools import Hex_Format, rgb_to_xy, rgb_to_hsl
from Modules.zigateConsts import ADDRESS_MODE, MAX_LOAD_ZIGATE, ZIGATE_EP

# from Classes.AdminWidgets import AdminWidgets


def create_domoticz_group_device(self, GroupName, GroupId):
    ' Create Device for just created group in Domoticz. '

    def free_unit(self, Devices):
        for x in range(1, 255):
            if x not in Devices:
                return x


    if GroupName == '' or GroupId == '':
        Domoticz.Error("createDomoticzGroupDevice - Invalid Group Name: %s or GroupdID: %s" %(GroupName, GroupId))
        return

    for x in self.Devices:
        if self.Devices[x].DeviceID == GroupId:
            Domoticz.Error("createDomoticzGroupDevice - existing group %s" %(self.Devices[x].Name))
            return

    Type_, Subtype_, SwitchType_ = self._bestGroupWidget( GroupId)

    unit = self.FreeUnit( self.Devices )
    self.logging( 'Debug', "createDomoticzGroupDevice - Unit: %s" %unit)
    myDev = Domoticz.Device(DeviceID = str(GroupId), Name = str(GroupName), Unit = unit, Type = Type_, Subtype = Subtype_, Switchtype = SwitchType_)
    myDev.Create()
    ID = myDev.ID
    if ID == -1:
        Domoticz.Error('createDomoticzGroupDevice - failed to create Group device.')

def unit_for_widget( self, GroupId):

    for x in self.Devices:
        if self.Devices[x].DeviceID == GroupId:

            return x

def update_domoticz_group_device_widget_name( self, GroupName, GroupId ):

    if GroupName == '' or GroupId == '':
        Domoticz.Error("_updateDomoGroupDeviceWidget - Invalid Group Name: %s or GroupdID: %s" %(GroupName, GroupId))
        return

    unit = unit_for_widget( self, GroupId )

    nValue = self.Devices[unit].nValue
    sValue = self.Devices[unit].sValue
    self.Devices[unit].Update( nValue, sValue, Name = GroupName)

    # Update Group Structure
    self.ListOfGroups[GroupId]['Name'] = GroupName

def update_domoticz_group_device_widget( self, GroupName, GroupId ):

    if GroupName == '' or GroupId == '':
        Domoticz.Error("updateDomoticzGroupDeviceWidget - Invalid Group Name: %s or GroupdID: %s" %(GroupName, GroupId))

    unit = unit_for_widget( self, GroupId )

    Type_, Subtype_, SwitchType_ = self._bestGroupWidget( GroupId)

    if Type_ != self.Devices[unit].Type or Subtype_ != self.Devices[unit].SubType or SwitchType_ != self.Devices[unit].SwitchType:
        self.logging( 'Debug', "updateDomoticzGroupDeviceWidget - Update Type:%s, Subtype:%s, Switchtype:%s" %(Type_, Subtype_, SwitchType_))
        self.Devices[unit].Update( 0, 'Off', Type = Type_, Subtype = Subtype_, Switchtype = SwitchType_)

def best_group_widget( self, GroupId):

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
            'ColorControlFull': ( 241, 7, 7 ),
            }

    code = 0
    _ikea_colormode = None
    color_widget = None
    widget_style = None
    widget = WIDGET_STYLE['ColorControlFull']    # If not match, will create a RGBWWZ widget

    for NwkId, devEp, iterIEEE in self.ListOfGroups[GroupId]['Devices']:
        if NwkId == '0000':
            continue

        self.logging( 'Log', "bestGroupWidget - Group: %s processing %s" %(GroupId, NwkId))
        if NwkId not in self.ListOfDevices:
            # We have some inconsistency !
            continue

        if 'ClusterType' not in self.ListOfDevices[NwkId]['Ep'][devEp]:
            continue

        for iterClusterType in self.ListOfDevices[NwkId]['Ep'][devEp]['ClusterType']:
            if self.ListOfDevices[NwkId]['Ep'][devEp]['ClusterType'][iterClusterType] in WIDGETS:
                WidgetId = self.ListOfDevices[NwkId]['Ep'][devEp]['ClusterType'][iterClusterType]
                if code <= WIDGETS[WidgetId]:
                    code = WIDGETS[WidgetId]
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
                            if WidgetId in [ 'ColorControlWW', 'ColorControlRGB', ]:
                                widget = WIDGET_STYLE[ WidgetId ]
                                _ikea_colormode = WidgetId

                        elif color_widget == WidgetId:
                            continue

                        elif (WidgetId == 'ColorControlWW' and color_widget == 'ColorControlRGB') or \
                                ( color_widget == 'ColorControlWW' and WidgetId == 'ColorControlRGB' ) :
                            code = 4
                            color_widget = 'ColorControlRGBWW'
                            widget = WIDGET_STYLE[ color_widget ]
                            _ikea_colormode = color_widget

                        elif WidgetId == 'ColorControl':
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

        self.logging( 'Debug', " --  --  --  --  --  --  -- - - processing %s code: %s widget: %s, color_widget: %s _ikea_colormode: %s " 
                %(NwkId, code, widget, color_widget, _ikea_colormode))

    if color_widget:
        self.ListOfGroups[GroupId]['WidgetStyle'] = color_widget

    elif widget_style:
        self.ListOfGroups[GroupId]['WidgetStyle'] = widget_style

    else:
        self.ListOfGroups[GroupId]['WidgetStyle'] = ''

    if self.ListOfGroups[GroupId]['WidgetStyle'] in  ( 'Switch', 'Plug' ):
        self.ListOfGroups[GroupId]['Cluster'] = '0006'

    elif self.ListOfGroups[GroupId]['WidgetStyle'] in ( 'LvlControl' ):
        self.ListOfGroups[GroupId]['Cluster'] = '0008'

    elif self.ListOfGroups[GroupId]['WidgetStyle'] in ( 'ColorControlWW', 'ColorControlRGB', 'ColorControlRGB', 'ColorControlRGBWW', 'ColorControl', 'ColorControlFull'):
        self.ListOfGroups[GroupId]['Cluster'] = '0300'

    elif self.ListOfGroups[GroupId]['WidgetStyle'] in ( 'Venetian', 'WindowCovering', 'VenetianInverted'):
        self.ListOfGroups[GroupId]['Cluster'] = '0102'

    else:
        self.ListOfGroups[GroupId]['Cluster'] = ''

    # This will be used when receiving left/right click , to know if it is RGB or WW
    if 'Tradfri Remote' in self.ListOfGroups[GroupId]:
        self.ListOfGroups[GroupId]['Tradfri Remote']['Color Mode'] = _ikea_colormode

    self.logging( 'Log', "_bestGroupWidget - %s Code: %s, Color_Widget: %s, widget: %s, WidgetStyle: %s" %( GroupId, code, color_widget, widget, self.ListOfGroups[GroupId]['WidgetStyle']))
    return widget

def update_domoticz_group_device( self, GroupId):
    """
    Update the Group status On/Off and Level , based on the attached devices
    """

    if GroupId not in self.ListOfGroups:
        Domoticz.Error("updateDomoGroupDevice - unknown group: %s" %GroupId)
        return

    if 'Devices' not in self.ListOfGroups[GroupId]:
        self.logging( 'Debug', "updateDomoGroupDevice - no Devices for that group: %s" %self.ListOfGroups[GroupId])
        return

    unit = unit_for_widget(self, GroupId )

    # If one device is on, then the group is on. If all devices are off, then the group is off
    nValue = 0
    level = None

    for NwkId, Ep, IEEE in self.ListOfGroups[GroupId]['Devices']:
        if NwkId not in self.ListOfDevices:
            return
        if Ep not in self.ListOfDevices[NwkId]['Ep']:
            return

        # Cluster ON/OFF
        if '0006' in self.ListOfDevices[NwkId]['Ep'][Ep]:
            if '0000' in self.ListOfDevices[NwkId]['Ep'][Ep]['0006']:
                if str(self.ListOfDevices[NwkId]['Ep'][Ep]['0006']['0000']).isdigit():
                    if int(self.ListOfDevices[NwkId]['Ep'][Ep]['0006']['0000']) != 0:
                        nValue = 1

        # Cluster Level Control
        if '0008' in self.ListOfDevices[NwkId]['Ep'][Ep]:
            if '0000' in self.ListOfDevices[NwkId]['Ep'][Ep]['0008']:
                if self.ListOfDevices[NwkId]['Ep'][Ep]['0008']['0000'] != '' and self.ListOfDevices[NwkId]['Ep'][Ep]['0008']['0000'] != {}:
                    if level is None:
                        level = int(self.ListOfDevices[NwkId]['Ep'][Ep]['0008']['0000'], 16)
                    else:
                        level = round(( level +  int(self.ListOfDevices[NwkId]['Ep'][Ep]['0008']['0000'], 16)) / 2)

        # Cluster Window Covering
        if '0102' in self.ListOfDevices[NwkId]['Ep'][Ep]:
            if '0008' in self.ListOfDevices[NwkId]['Ep'][Ep]['0102']:
                if self.ListOfDevices[NwkId]['Ep'][Ep]['0102']['0008'] != '' and self.ListOfDevices[NwkId]['Ep'][Ep]['0102']['0008'] != {}:
                   if level is None:
                       level = int(self.ListOfDevices[NwkId]['Ep'][Ep]['0102']['0008'], 16)
                   else:
                       level = round(( level +  int(self.ListOfDevices[NwkId]['Ep'][Ep]['0102']['0008'], 16)) / 2)

        self.logging( 'Debug', "updateDomoGroupDevice - Processing: Group: %s %s/%s nValue: %s, level: %s" %(GroupId, NwkId, Ep, nValue, level))


    self.logging( 'Debug', "updateDomoGroupDevice - Processing: Group: %s ==  > nValue: %s, level: %s" %(GroupId, nValue, level))
    # At that stage
    # nValue == 0 if Off
    # nValue == 1 if Open/On
    # level is None, so we use nValue/sValue
    # level is not None; so we have a LvlControl
    if level:
        if self.Devices[unit].SwitchType not in ( 13, 14, 15, 16):
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

    self.logging( 'Debug', "updateDomoGroupDevice - Processing: Group: %s ==  > nValue: %s, sValue: %s" %(GroupId, nValue, sValue))
    if nValue != self.Devices[unit].nValue or sValue != self.Devices[unit].sValue:
        self.logging( 'Log', "UpdateGroup  - (%15s) %s:%s" %( self.Devices[unit].Name, nValue, sValue ))
        self.Devices[unit].Update( nValue, sValue)

def remove_domoticz_group_device(self, GroupId):
    ' User has removed the Domoticz Device corresponding to this group'

    if GroupId not in self.ListOfGroups:
        Domoticz.Error("_removeDomoGroupDevice - unknown group: %s" %GroupId)
        return

    unit = unit_for_widget(self, GroupId )

    self.logging( 'Debug', "_removeDomoGroupDevice - removing Domoticz Widget %s" %self.Devices[unit].Name)
    self.adminWidgets.updateNotificationWidget( self.Devices, 'Groups %s deleted' %self.Devices[unit].Name)
    self.Devices[unit].Delete()

def process_remove_group( self, unit, GroupId):
    pass

def update_device_list_attribute( self, GroupId, cluster, value):

    if GroupId not in self.ListOfGroups:
        return

    # search for all Devices in the group
    for iterItem in self.ListOfGroups[GroupId]['Devices']:
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
            Domoticz.Error("_updateDeviceListAttribute - Device: %s of Group: %s not in the list anymore" %(iterDev, GroupId))
            continue

        if iterEp not in self.ListOfDevices[iterDev]['Ep']:
            Domoticz.Error("_updateDeviceListAttribute - Not existing Ep: %s for Device: %s in Group: %s" %(iterEp, iterDev, GroupId))
            continue

        if 'ClusterType' not in self.ListOfDevices[iterDev]['Ep'][iterEp] and 'ClusterType' not in self.ListOfDevices[iterDev]:
            Domoticz.Error("_updateDeviceListAttribute - No Widget attached to Device: %s/%s in Group: %s" %(iterDev, iterEp, GroupId))
            continue

        if cluster not in self.ListOfDevices[iterDev]['Ep'][iterEp]:
            self.logging( 'Debug', "_updateDeviceListAttribute - Cluster: %s doesn't exist for Device: %s/%s in Group: %s" %(cluster, iterDev, iterEp, GroupId))
            continue

        if cluster not in self.ListOfDevices[iterDev]['Ep'][iterEp]:
            self.ListOfDevices[iterDev]['Ep'][iterEp][cluster] = {}
        if not isinstance( self.ListOfDevices[iterDev]['Ep'][iterEp][cluster] , dict):
            self.ListOfDevices[iterDev]['Ep'][iterEp][cluster] = {}
        if '0000' not in self.ListOfDevices[iterDev]['Ep'][iterEp][cluster]:
            self.ListOfDevices[iterDev]['Ep'][iterEp][cluster]['0000'] = {}

        self.ListOfDevices[iterDev]['Ep'][iterEp][cluster]['0000'] = value
        self.logging( 'Debug', "_updateDeviceListAttribute - Updating Device: %s/%s of Group: %s Cluster: %s to value: %s" %(iterDev, iterEp, GroupId, cluster, value))

    return

def process_command( self, unit, NwkId, Command, Level, Color_ ) :

    self.logging( 'Debug', "processCommand - unit: %s, NwkId: %s, cmd: %s, level: %s, color: %s" %(unit, NwkId, Command, Level, Color_))

    if NwkId not in self.ListOfGroups:
        return

    for iterDevice in self.ListOfGroups[NwkId]['Devices']:
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
            Domoticz.Error("processCommand - Looks like device %s [%s] does not exist anymore and you expect to be part of group %s" %(iterDev, iterIEEE, NwkId))

    EPin = EPout = '01'

    if 'Cluster' in self.ListOfGroups[ NwkId ]:
        # new fashon
        if self.ListOfGroups[ NwkId ]['Cluster'] == '0102': # Venetian store
            zigate_cmd = "00FA"
            if Command == 'Off' :
                zigate_param = '00'
                nValue = 1
                sValue = 'Off'
                self._updateDeviceListAttribute( NwkId, '0102', zigate_param)

            if Command == 'On' :
                zigate_param = '01'
                nValue = 0
                sValue = 'Off'
                self._updateDeviceListAttribute( NwkId, '0102', zigate_param)

            if Command == 'Stop':
                zigate_param = '02'
                nValue = 2
                sValue = '50'
                self._updateDeviceListAttribute( NwkId, '0102', zigate_param)

            self.Devices[unit].Update(nValue = int(nValue), sValue = str(sValue))
            self._updateDeviceListAttribute( NwkId, '0102', zigate_param)
            datas = "%02d" %ADDRESS_MODE['group'] + NwkId + ZIGATE_EP + EPout + zigate_param
            self.logging( 'Debug', "Group Command: %s" %datas)
            self.ZigateComm.sendData( zigate_cmd, datas)
            return

    # Old Fashon
    if Command == 'Off' :
        zigate_cmd = "0092"
        zigate_param = '00'
        nValue = 0
        sValue = 'Off'
        self.Devices[unit].Update(nValue = int(nValue), sValue = str(sValue))
        self._updateDeviceListAttribute( NwkId, '0006', '00')
        self.updateDomoGroupDevice( NwkId)
        #datas = "01" + NwkId + EPin + EPout + zigate_param
        datas = "%02d" %ADDRESS_MODE['group'] + NwkId + ZIGATE_EP + EPout + zigate_param
        self.logging( 'Debug', "Command: %s" %datas)
        self.ZigateComm.sendData( zigate_cmd, datas)

    if Command == 'On' :
        zigate_cmd = "0092"
        zigate_param = '01'
        nValue = '1'
        sValue = 'On'
        self.Devices[unit].Update(nValue = int(nValue), sValue = str(sValue))
        self._updateDeviceListAttribute( NwkId, '0006', '01')

        self.updateDomoGroupDevice( NwkId)
        #datas = "01" + NwkId + EPin + EPout + zigate_param
        datas = "%02d" %ADDRESS_MODE['group'] + NwkId + ZIGATE_EP + EPout + zigate_param
        self.logging( 'Debug', "Command: %s" %datas)
        self.ZigateComm.sendData( zigate_cmd, datas)


    if Command == 'Set Level':
        # Level: % value of move
        # Converted to value , raw value from 0 to 255
        # sValue is just a string of Level
        zigate_cmd = "0081"
        OnOff = "01"
        #value = int(Level*255//100)
        value = '%02X' %int(Level*255//100)
        zigate_param = OnOff + value + "0010"
        nValue = '1'
        sValue = str(Level)
        self.Devices[unit].Update(nValue = int(nValue), sValue = str(sValue))
        self._updateDeviceListAttribute( NwkId, '0008', value)
        datas = "%02d" %ADDRESS_MODE['group'] + NwkId + ZIGATE_EP + EPout + zigate_param
        self.logging( 'Debug', "Command: %s" %datas)
        self.ZigateComm.sendData( zigate_cmd, datas)
        self.updateDomoGroupDevice( NwkId)

    if Command == "Set Color" :
        Hue_List = json.loads(Color_)
        #First manage level
        OnOff = '01' # 00 = off, 01 = on
        value = '%02X' %round(1+Level*254/100)
        #value = Hex_Format(2, round(1+Level*254/100)) #To prevent off state
        zigate_cmd = "0081"
        zigate_param = OnOff + value + "0000"
        datas = "%02d" %ADDRESS_MODE['group'] + NwkId + ZIGATE_EP + EPout + zigate_param
        self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd, datas))
        self._updateDeviceListAttribute( NwkId, '0008', value)
        self.ZigateComm.sendData( zigate_cmd, datas)

        if Hue_List['m'] == 1:
            ww = int(Hue_List['ww']) # Can be used as level for monochrome white
            self.logging( 'Debug', "Not implemented device color 1")
        #ColorModeTemp = 2   // White with color temperature. Valid fields: t
        if Hue_List['m'] == 2:
            self.set_Kelvin_Color( ADDRESS_MODE['group'], NwkId, EPin, EPout, int(Hue_List['t']))

        #ColorModeRGB = 3    // Color. Valid fields: r, g, b.
        elif Hue_List['m'] == 3:
            self.set_RGB_color( ADDRESS_MODE['group'], NwkId, EPin, EPout, \
                    int(Hue_List['r']), int(Hue_List['g']), int(Hue_List['b']))

        #ColorModeCustom = 4, // Custom (color + white). Valid fields: r, g, b, cw, ww, depending on device capabilities
        elif Hue_List['m'] == 4:
            ww = int(Hue_List['ww'])
            cw = int(Hue_List['cw'])
            x, y = rgb_to_xy((int(Hue_List['r']), int(Hue_List['g']), int(Hue_List['b'])))
            self.logging( 'Debug', "Not implemented device color 2")

        #With saturation and hue, not seen in domoticz but present on zigate, and some device need it
        elif Hue_List['m'] == 9998:
            h, l, s = rgb_to_hsl((int(Hue_List['r']), int(Hue_List['g']), int(Hue_List['b'])))
            saturation = s * 100   #0 > 100
            hue = h *360           #0 > 360
            hue = int(hue*254//360)
            saturation = int(saturation*254//100)
            Level = l
            value = '%02X' %round(1+Level*254/100)
            #value = Hex_Format(2, round(1+Level*254/100)) #To prevent off state

            OnOff = '01'
            zigate_cmd = "00B6"
            zigate_param = Hex_Format(2, hue) + Hex_Format(2, saturation) + "0000"
            datas = "%02d" %ADDRESS_MODE['group'] + NwkId + ZIGATE_EP + EPout + zigate_param
            self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd, datas))
            self.ZigateComm.sendData( zigate_cmd, datas)
            zigate_cmd = "0081"
            zigate_param = OnOff + value + "0010"
            datas = "%02d" %ADDRESS_MODE['group'] + NwkId + ZIGATE_EP + EPout + zigate_param
            self.logging( 'Debug', "Command: %s - data: %s" %(zigate_cmd, datas))
            self.ZigateComm.sendData( zigate_cmd, datas)
            self._updateDeviceListAttribute( NwkId, '0008', value)

        #Update Device
        nValue = 1
        sValue = str(Level)
        self.Devices[unit].Update(nValue = int(nValue), sValue = str(sValue), Color = Color_)