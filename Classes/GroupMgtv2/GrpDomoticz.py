# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import json

from Classes.GroupMgtv2.GrpCommands import set_kelvin_color, set_rgb_color, set_hue_saturation
from Classes.GroupMgtv2.GrpDatabase import update_due_to_nwk_id_change
from Modules.tools import Hex_Format, rgb_to_xy, rgb_to_hsl
from Modules.zigateConsts import ADDRESS_MODE, ZIGATE_EP, LEGRAND_REMOTES


from Classes.AdminWidgets import AdminWidgets

WIDGET_STYLE = {
    "Plug": (244, 73, 0),
    "Switch": (244, 73, 0),
    "LvlControl": (244, 73, 7),
    "BlindPercentInverted": (244, 73, 16),
    "WindowCovering": (244, 73, 16),
    "Venetian": (244, 73, 15),
    "VenetianInverted": (244, 73, 15),
    "ColorControlWW": (241, 8, 7),
    "ColorControlRGB": (241, 2, 7),
    "ColorControlRGBWW": (241, 4, 7),
    "ColorControlFull": (241, 7, 7),
}


def unit_for_widget(self, GroupId):

    for x in self.Devices:
        if self.Devices[x].DeviceID == GroupId:
            return x
    return None


def free_unit(Devices):
    for x in range(1, 255):
        if x not in Devices:
            return x


def create_domoticz_group_device(self, GroupName, GroupId):
    " Create Device for just created group in Domoticz. "

    if GroupName == "" or GroupId == "":
        self.logging(
            "Error", "createDomoticzGroupDevice - Invalid Group Name: %s or GroupdID: %s" % (GroupName, GroupId)
        )
        return

    for x in self.Devices:
        if self.Devices[x].DeviceID == GroupId:
            # self.logging( 'Error',"createDomoticzGroupDevice - existing group %s" %(self.Devices[x].Name))
            return

    Type_, Subtype_, SwitchType_ = best_group_widget(self, GroupId)

    unit = free_unit(self.Devices)
    self.logging("Debug", "createDomoticzGroupDevice - Unit: %s" % unit)
    myDev = Domoticz.Device(
        DeviceID=str(GroupId), Name=str(GroupName), Unit=unit, Type=Type_, Subtype=Subtype_, Switchtype=SwitchType_
    )
    myDev.Create()
    ID = myDev.ID
    if ID == -1:
        self.logging("Error", "createDomoticzGroupDevice - failed to create Group device.")
        return

    self.ListOfGroups[GroupId]["WidgetType"] = unit


def LookForGroupAndCreateIfNeeded(self, GroupId):

    if GroupId not in self.ListOfGroups:
        return

    if unit_for_widget(self, GroupId):
        # Group Exist and has a valid unit
        update_domoticz_group_device_widget(self, GroupId)
        return

    if "GroupName" not in self.ListOfGroups[GroupId]:
        self.ListOfGroups[GroupId]["GroupName"] = "Zigate Group %s" % GroupId

    GroupName = self.ListOfGroups[GroupId]["GroupName"]
    create_domoticz_group_device(self, GroupName, GroupId)
    update_domoticz_group_device_widget(self, GroupId)


def update_domoticz_group_device_widget_name(self, GroupName, GroupId):

    if GroupName == "" or GroupId == "":
        self.logging(
            "Error",
            "update_domoticz_group_device_widget_name - Invalid Group Name: %s or GroupdID: %s" % (GroupName, GroupId),
        )
        return

    unit = unit_for_widget(self, GroupId)
    if unit is None:
        self.logging(
            "Debug",
            "update_domoticz_group_device_widget_name - no unit found for GroupId: %s" % self.ListOfGroups[GroupId],
        )
        return

    nValue = self.Devices[unit].nValue
    sValue = self.Devices[unit].sValue
    self.Devices[unit].Update(nValue, sValue, Name=GroupName)

    # Update Group Structure
    self.ListOfGroups[GroupId]["Name"] = GroupName


def update_domoticz_group_device_widget(self, GroupId):

    self.logging("Debug", "update_domoticz_group_device_widget GroupId: %s" % GroupId)
    if GroupId == "":
        self.logging("Error", "update_domoticz_group_device_widget - Invalid GroupdID: %s" % (GroupId))

    unit = unit_for_widget(self, GroupId)
    if unit is None:
        self.logging(
            "Debug", "update_domoticz_group_device_widget - no unit found for GroupId: %s" % self.ListOfGroups[GroupId]
        )
        return

    Type_, Subtype_, SwitchType_ = best_group_widget(self, GroupId)

    self.logging(
        "Debug",
        "      Looking to update Unit: %s from %s %s %s to %s %s %s"
        % (
            unit,
            self.Devices[unit].Type,
            self.Devices[unit].SubType,
            self.Devices[unit].SwitchType,
            Type_,
            Subtype_,
            SwitchType_,
        ),
    )

    nValue = self.Devices[unit].nValue
    sValue = self.Devices[unit].sValue
    if (
        Type_ != self.Devices[unit].Type
        or Subtype_ != self.Devices[unit].SubType
        or SwitchType_ != self.Devices[unit].SwitchType
    ):
        self.logging(
            "Debug",
            "update_domoticz_group_device_widget - Update Type:%s, Subtype:%s, Switchtype:%s"
            % (Type_, Subtype_, SwitchType_),
        )
        self.Devices[unit].Update(nValue, sValue, Type=Type_, Subtype=Subtype_, Switchtype=SwitchType_)


def best_group_widget(self, GroupId):

    # WIDGETS = {
    #        'Plug':1,                 # ( 244, 73, 0)
    #        'Switch':1,               # ( 244, 73, 0)
    #        'LvlControl':2,           # ( 244, 73, 7)
    #        'ColorControlWW':3,       # ( 241, 8, 7) - Cold white + warm white
    #        'ColorControlRGB':3,      # ( 241, 2, 7) - RGB
    #        'ColorControlRGBWW':4,    # ( 241, 4, 7) - RGB + cold white + warm white, either RGB or white can be lit
    #        'ColorControl':5,         # ( 241, 7, 7) - Like RGBWW, but allows combining RGB and white
    #        'ColorControlFull':5,     # ( 241, 7, 7) - Like RGBWW, but allows combining RGB and white
    #        'Venetian': 10,           # ( 244, 73, 15) # Shade, Venetian
    #        'VenetianInverted': 11,   # ( 244, 73, 15)
    #        'WindowCovering': 12,     # ( 244, 73, 16)  # Venetian Blind EU
    #        'BlindPercentInverted': 12,     # ( 244, 73, 16)  # Venetian Blind EU
    #        }

    GroupWidgetType = None

    self.logging("Debug", "best_group_widget Device - %s" % str(self.ListOfGroups[GroupId]["Devices"]))
    for NwkId, devEp, iterIEEE in self.ListOfGroups[GroupId]["Devices"]:
        # We will scan each Device in the Group and try to indentify which Widget is associated to it
        # Based on the list of Widget will try to identified the Most Features
        self.logging("Debug", "best_group_widget Device - %s  %s  %s" % (NwkId, devEp, iterIEEE))
        if NwkId == "0000":
            continue

        self.logging("debug", "bestGroupWidget - Group: %s processing %s" % (GroupId, NwkId))
        if NwkId not in self.ListOfDevices:
            # We have some inconsistency !
            continue

        if "ClusterType" not in self.ListOfDevices[NwkId]["Ep"][devEp]:
            # No widget associated
            continue

        for DomoDeviceUnit in self.ListOfDevices[NwkId]["Ep"][devEp]["ClusterType"]:
            WidgetType = self.ListOfDevices[NwkId]["Ep"][devEp]["ClusterType"][DomoDeviceUnit]
            self.logging("Debug", "------------ GroupWidget: %s WidgetType: %s" % (GroupWidgetType, WidgetType))

            if GroupWidgetType is None and WidgetType in WIDGET_STYLE:
                GroupWidgetType = WidgetType
                continue

            if WidgetType == GroupWidgetType:
                continue

            if WidgetType == "Switch" and GroupWidgetType == "Plug":
                GroupWidgetType = "Switch"
                continue

            if WidgetType == "LvlControl" and GroupWidgetType in ("Plug", "Switch"):
                GroupWidgetType = WidgetType
                continue

            if WidgetType == "ColorControlWW" and GroupWidgetType in ("Plug", "Switch", "LvlControl"):
                GroupWidgetType = WidgetType
                continue

            if WidgetType == "ColorControlRGB" and GroupWidgetType in ("Plug", "Switch", "LvlControl"):
                GroupWidgetType = WidgetType
                continue

            if (WidgetType == "ColorControlRGB" and GroupWidgetType in ("ColorControlWW")) or (
                WidgetType == "ColorControlWW" and GroupWidgetType in ("ColorControlRGB")
            ):
                GroupWidgetType = "ColorControlRGBWW"
                continue

            if WidgetType in ("ColorControl", "ColorControlFull"):
                GroupWidgetType = WidgetType
                continue

            if WidgetType in ("Venetian", "VenetianInverted", "WindowCovering", "BlindPercentInverted"):
                GroupWidgetType = WidgetType

    if GroupWidgetType is None:
        GroupWidgetType = "ColorControlFull"

    self.ListOfGroups[GroupId]["WidgetStyle"] = GroupWidgetType
    # This will be used when receiving left/right click , to know if it is RGB or WW

    if "Tradfri Remote" in self.ListOfGroups[GroupId]:
        self.ListOfGroups[GroupId]["Tradfri Remote"]["Color Mode"] = GroupWidgetType

    # Update Cluster, based on WidgetStyle
    if self.ListOfGroups[GroupId]["WidgetStyle"] in ("Switch", "Plug"):
        self.ListOfGroups[GroupId]["Cluster"] = "0006"

    elif self.ListOfGroups[GroupId]["WidgetStyle"] in ("LvlControl"):
        self.ListOfGroups[GroupId]["Cluster"] = "0008"

    elif self.ListOfGroups[GroupId]["WidgetStyle"] in (
        "ColorControlWW",
        "ColorControlRGB",
        "ColorControlRGB",
        "ColorControlRGBWW",
        "ColorControl",
        "ColorControlFull",
    ):
        self.ListOfGroups[GroupId]["Cluster"] = "0300"

    elif self.ListOfGroups[GroupId]["WidgetStyle"] in ("Venetian", "WindowCovering", "VenetianInverted"):
        self.ListOfGroups[GroupId]["Cluster"] = "0102"

    else:
        self.ListOfGroups[GroupId]["Cluster"] = ""

    self.logging(
        "Debug",
        "best_group_widget for GroupId: %s Found WidgetType: %s Widget: %s"
        % (GroupId, GroupWidgetType, WIDGET_STYLE.get(GroupWidgetType, WIDGET_STYLE["ColorControlFull"])),
    )

    return WIDGET_STYLE.get(GroupWidgetType, WIDGET_STYLE["ColorControlFull"])


def update_domoticz_group_device(self, GroupId):
    """
    Update the Group status On/Off and Level , based on the attached devices
    """

    #####
    if GroupId not in self.ListOfGroups:
        self.logging("Error", "update_domoticz_group_device - unknown group: %s" % GroupId)
        return

    if "Devices" not in self.ListOfGroups[GroupId]:
        self.logging(
            "Debug", "update_domoticz_group_device - no Devices for that group: %s" % self.ListOfGroups[GroupId]
        )
        return

    unit = unit_for_widget(self, GroupId)
    if unit is None:
        self.logging(
            "Debug", "update_domoticz_group_device - no unit found for GroupId: %s" % self.ListOfGroups[GroupId]
        )
        return

    Cluster = None
    if "Cluster" in self.ListOfGroups[GroupId]:
        Cluster = self.ListOfGroups[GroupId]["Cluster"]

    countOn = countOff = 0
    if self.pluginconf.pluginConf["OnIfOneOn"]:
        # If one device is on, then the group is on. If all devices are off, then the group is off
        nValue = 0
        sValue = level = None
    else:
        # If ALL devices are on, then the group is On, otherwise it remains Off (Philips behaviour)
        nValue = 1
        sValue = level = None

    for NwkId, Ep, IEEE in self.ListOfGroups[GroupId]["Devices"]:
        if NwkId not in self.ListOfDevices:
            return
        if Ep not in self.ListOfDevices[NwkId]["Ep"]:
            return
        if "Model" in self.ListOfDevices[NwkId]:
            if self.ListOfDevices[NwkId]["Model"] in ("TRADFRI remote control", "Remote Control N2"):
                continue
            if self.ListOfDevices[NwkId]["Model"] in LEGRAND_REMOTES:
                continue

        # Cluster ON/OFF
        if Cluster and Cluster in ("0006", "0008", "0300") and "0006" in self.ListOfDevices[NwkId]["Ep"][Ep]:
            if "0000" in self.ListOfDevices[NwkId]["Ep"][Ep]["0006"]:
                if str(self.ListOfDevices[NwkId]["Ep"][Ep]["0006"]["0000"]).isdigit():
                    if int(self.ListOfDevices[NwkId]["Ep"][Ep]["0006"]["0000"]) != 0:
                        countOn += 1
                    else:
                        countOff += 1

        # Cluster Level Control
        if Cluster and Cluster in ("0008", "0300") and "0008" in self.ListOfDevices[NwkId]["Ep"][Ep]:
            if "0000" in self.ListOfDevices[NwkId]["Ep"][Ep]["0008"]:
                if (
                    self.ListOfDevices[NwkId]["Ep"][Ep]["0008"]["0000"] != ""
                    and self.ListOfDevices[NwkId]["Ep"][Ep]["0008"]["0000"] != {}
                ):
                    if level is None:
                        level = int(self.ListOfDevices[NwkId]["Ep"][Ep]["0008"]["0000"], 16)
                    else:
                        level = round((level + int(self.ListOfDevices[NwkId]["Ep"][Ep]["0008"]["0000"], 16)) / 2)

        # Cluster Window Covering
        if Cluster and Cluster == "0102" and "0102" in self.ListOfDevices[NwkId]["Ep"][Ep]:
            if "0008" in self.ListOfDevices[NwkId]["Ep"][Ep]["0102"]:
                if (
                    self.ListOfDevices[NwkId]["Ep"][Ep]["0102"]["0008"] != ""
                    and self.ListOfDevices[NwkId]["Ep"][Ep]["0102"]["0008"] != {}
                ):
                    if level is None:
                        level = int(self.ListOfDevices[NwkId]["Ep"][Ep]["0102"]["0008"])
                    else:
                        level = round((level + int(self.ListOfDevices[NwkId]["Ep"][Ep]["0102"]["0008"])) / 2)

                    nValue, sValue = ValuesForVenetian(level)

        self.logging(
            "Debug",
            "update_domoticz_group_device - Processing: Group: %s %s/%s On: %s, Off: %s level: %s"
            % (GroupId, NwkId, Ep, countOn, countOff, level),
        )

    if self.pluginconf.pluginConf["OnIfOneOn"]:
        if countOn > 0:
            nValue = 1
    else:
        if countOff > 0:
            nValue = 0
    self.logging(
        "Debug",
        "update_domoticz_group_device - Processing: Group: %s ==  > nValue: %s, level: %s" % (GroupId, nValue, level),
    )

    # At that stage
    # nValue == 0 if Off
    # nValue == 1 if Open/On
    # level is None, so we use nValue/sValue
    # level is not None; so we have a LvlControl
    if sValue is None and level:
        if self.Devices[unit].SwitchType not in (13, 14, 15, 16):
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
            if nValue == 0:  # we are in an Off mode
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

    elif sValue is None:
        if nValue == 0:
            sValue = "Off"

        else:
            sValue = "On"

    self.logging(
        "Debug",
        "update_domoticz_group_device - Processing: Group: %s ==  > from %s:%s to %s:%s"
        % (GroupId, self.Devices[unit].nValue, self.Devices[unit].sValue, nValue, sValue),
    )
    if nValue != self.Devices[unit].nValue or sValue != self.Devices[unit].sValue:
        self.logging("Log", "UpdateGroup  - (%15s) %s:%s" % (self.Devices[unit].Name, nValue, sValue))
        self.Devices[unit].Update(nValue, sValue)


def update_domoticz_group_name(self, GrpId, NewGrpName):

    unit = unit_for_widget(self, GrpId)
    if unit is None:
        self.logging("Debug", "update_domoticz_group_name - no unit found for GroupId: %s" % self.ListOfGroups[GrpId])
        return

    nValue = self.Devices[unit].nValue
    sValue = self.Devices[unit].sValue

    self.logging("Debug", "update_domoticz_group_name Update GroupId: %s to Name: %s" % (GrpId, NewGrpName))
    self.Devices[unit].Update(nValue, sValue, Name=NewGrpName)
    return


def ValuesForVenetian(level):
    nValue = 2
    if level > 0 and level < 100:
        nValue = 2
    elif level == 0:
        nValue = 0
    elif level == 100:
        nValue = 1
    sValue = "%s" % level
    return (nValue, sValue)


def remove_domoticz_group_device(self, GroupId):
    " User has removed the Domoticz Device corresponding to this group"

    unit = unit_for_widget(self, GroupId)
    if unit is None and GroupId in self.ListOfGroups:
        self.logging(
            "Debug", "remove_domoticz_group_device - no unit found for GroupId: %s" % self.ListOfGroups[GroupId]
        )
        return

    if unit in self.Devices:
        self.Devices[unit].Delete()


def update_device_list_attribute(self, GroupId, cluster, value):

    if GroupId not in self.ListOfGroups:
        return

    # search for all Devices in the group
    for iterItem in self.ListOfGroups[GroupId]["Devices"]:
        if len(iterItem) == 3:
            iterDev, iterEp, iterIEEE = iterItem

        elif len(iterItem) == 2:
            iterDev, iterEp = iterItem
            if iterDev in self.ListOfDevices:
                iterIEEE = self.ListOfDevices[iterDev]["IEEE"]

            else:
                self.logging("Error", "Unknown device %s, it is recommended to do a full rescan of Groups" % iterDev)
                continue
        else:
            continue

        if iterDev == "0000":
            continue

        if iterDev not in self.ListOfDevices:
            iterDev = check_and_fix_missing_device(self, GroupId, iterDev, iterIEEE)
            if iterDev is None:
                self.logging(
                    "Error",
                    "update_device_list_attribute - Device: %s of Group: %s not in the list anymore"
                    % (iterDev, GroupId),
                )
                continue

        if iterEp not in self.ListOfDevices[iterDev]["Ep"]:
            self.logging(
                "Error",
                "update_device_list_attribute - Not existing Ep: %s for Device: %s in Group: %s"
                % (iterEp, iterDev, GroupId),
            )
            continue

        if (
            "ClusterType" not in self.ListOfDevices[iterDev]["Ep"][iterEp]
            and "ClusterType" not in self.ListOfDevices[iterDev]
        ):
            self.logging(
                "Error",
                "update_device_list_attribute - No Widget attached to Device: %s/%s in Group: %s"
                % (iterDev, iterEp, GroupId),
            )
            continue

        if cluster not in self.ListOfDevices[iterDev]["Ep"][iterEp]:
            self.logging(
                "Debug",
                "update_device_list_attribute - Cluster: %s doesn't exist for Device: %s/%s in Group: %s"
                % (cluster, iterDev, iterEp, GroupId),
            )
            continue

        if cluster not in self.ListOfDevices[iterDev]["Ep"][iterEp]:
            self.ListOfDevices[iterDev]["Ep"][iterEp][cluster] = {}
        if not isinstance(self.ListOfDevices[iterDev]["Ep"][iterEp][cluster], dict):
            self.ListOfDevices[iterDev]["Ep"][iterEp][cluster] = {}

        if cluster == "0102":
            if "0008" not in self.ListOfDevices[iterDev]["Ep"][iterEp][cluster]:
                self.ListOfDevices[iterDev]["Ep"][iterEp][cluster]["0008"] = {}
            self.ListOfDevices[iterDev]["Ep"][iterEp][cluster]["0008"] = value
        else:
            if "0000" not in self.ListOfDevices[iterDev]["Ep"][iterEp][cluster]:
                self.ListOfDevices[iterDev]["Ep"][iterEp][cluster]["0000"] = {}
            self.ListOfDevices[iterDev]["Ep"][iterEp][cluster]["0000"] = value

        self.logging(
            "Debug",
            "update_device_list_attribute - Updating Device: %s/%s of Group: %s Cluster: %s to value: %s"
            % (iterDev, iterEp, GroupId, cluster, value),
        )

    return


def check_and_fix_missing_device(self, GroupId, NwkId, ieee):

    if ieee in self.IEEE2NWK:
        # Need to update the NwkId
        update_due_to_nwk_id_change(self, NwkId, self.IEEE2NWK[ieee])
        if self.IEEE2NWK[ieee] in self.ListOfDevices:
            return self.IEEE2NWK[ieee]
    return None


def processCommand(self, unit, GrpId, Command, Level, Color_):

    # Begin
    self.logging(
        "Debug",
        "processGroupCommand - unit: %s, NwkId: %s, cmd: %s, level: %s, color: %s"
        % (unit, GrpId, Command, Level, Color_),
    )

    if GrpId not in self.ListOfGroups:
        return

    # Not sure that Groups are always on EP 01 !!!!!
    EPout = "01"

    if "Cluster" in self.ListOfGroups[GrpId]:
        # new fashion
        if self.ListOfGroups[GrpId]["Cluster"] == "0102":  # Venetian store
            zigate_cmd = "00FA"
            if Command == "Off":
                zigate_param = "00"
                nValue = 0
                sValue = "Off"
                update_device_list_attribute(self, GrpId, "0102", 0)

            if Command == "On":
                zigate_param = "01"
                nValue = 1
                sValue = "Off"
                update_device_list_attribute(self, GrpId, "0102", 100)

            if Command == "Stop":
                zigate_param = "02"
                nValue = 2
                sValue = "50"
                update_device_list_attribute(self, GrpId, "0102", 50)

            self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
            datas = "%02d" % ADDRESS_MODE["group"] + GrpId + ZIGATE_EP + EPout + zigate_param
            self.logging("Debug", "Group Command: %s %s-%s" % (Command, zigate_cmd, datas))
            self.ZigateComm.sendData(zigate_cmd, datas, ackIsDisabled=True)
            resetDevicesHearttBeat(self, GrpId)
            return

    # Old Fashon
    if Command == "Off":
        if self.pluginconf.pluginConf["GrpfadingOff"]:
            if self.pluginconf.pluginConf["GrpfadingOff"] == 1:
                effect = "0002"  # 50% dim down in 0.8 seconds then fade to off in 12 seconds
            elif self.pluginconf.pluginConf["GrpfadingOff"] == 2:
                effect = "0100"  # 20% dim up in 0.5s then fade to off in 1 second
            elif self.pluginconf.pluginConf["GrpfadingOff"] == 255:
                effect = "0001"  # No fade

            zigate_cmd = "0094"
            datas = "%02d" % ADDRESS_MODE["group"] + GrpId + ZIGATE_EP + EPout + effect
        else:
            zigate_cmd = "0092"
            datas = "%02d" % ADDRESS_MODE["group"] + GrpId + ZIGATE_EP + EPout + "00"

        nValue = 0
        sValue = "Off"
        self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))

        self.logging("Debug", "Command: %s %s" % (Command, datas))
        self.ZigateComm.sendData(zigate_cmd, datas, ackIsDisabled=True)

        # Update Device
        nValue = 0
        sValue = "Off"
        self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))

        update_device_list_attribute(self, GrpId, "0006", "00")
        update_domoticz_group_device(self, GrpId)

    elif Command == "On":
        zigate_cmd = "0092"
        zigate_param = "01"
        nValue = "1"
        sValue = "On"
        self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
        update_device_list_attribute(self, GrpId, "0006", "01")
        update_domoticz_group_device(self, GrpId)

        datas = "%02d" % ADDRESS_MODE["group"] + GrpId + ZIGATE_EP + EPout + zigate_param
        self.logging("Debug", "Command: %s %s" % (Command, datas))
        self.ZigateComm.sendData(zigate_cmd, datas, ackIsDisabled=True)
        # Update Device
        nValue = 1
        sValue = "On"
        self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))

    elif Command == "Set Level":
        # Level: % value of move
        # Converted to value , raw value from 0 to 255
        # sValue is just a string of Level
        zigate_cmd = "0081"
        OnOff = "01"
        # value = int(Level*255//100)
        value = "%02X" % int(Level * 255 // 100)
        zigate_param = OnOff + value + "0010"
        nValue = "1"
        sValue = str(Level)
        self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))
        update_device_list_attribute(self, GrpId, "0008", value)

        datas = "%02d" % ADDRESS_MODE["group"] + GrpId + ZIGATE_EP + EPout + zigate_param
        self.logging("Debug", "Command: %s %s" % (Command, datas))
        self.ZigateComm.sendData(zigate_cmd, datas, ackIsDisabled=True)
        update_domoticz_group_device(self, GrpId)
        # Update Device
        nValue = 2
        sValue = str(Level)
        self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue))

    elif Command == "Set Color":
        Hue_List = json.loads(Color_)
        transitionRGB = "%04x" % self.pluginconf.pluginConf["GrpmoveToColourRGB"]
        transitionMoveLevel = "%04x" % self.pluginconf.pluginConf["GrpmoveToLevel"]
        transitionHue = "%04x" % self.pluginconf.pluginConf["GrpmoveToHueSatu"]
        transitionTemp = "%04x" % self.pluginconf.pluginConf["GrpmoveToColourTemp"]

        # First manage level
        if Hue_List["m"] != 9998:
            # In case of m ==3, we will do the Setlevel
            OnOff = "01"  # 00 = off, 01 = on
            value = Hex_Format(2, round(1 + Level * 254 / 100))  # To prevent off state
            zigate_cmd = "0081"
            zigate_param = OnOff + value + transitionMoveLevel

            datas = "%02d" % ADDRESS_MODE["group"] + GrpId + ZIGATE_EP + EPout + zigate_param
            self.logging("Debug", "Command: %s - data: %s" % (zigate_cmd, datas))
            update_device_list_attribute(self, GrpId, "0008", value)
            self.ZigateComm.sendData(zigate_cmd, datas, ackIsDisabled=True)

        if Hue_List["m"] == 1:
            ww = int(Hue_List["ww"])  # Can be used as level for monochrome white
            self.logging("Debug", "Not implemented device color 1")

        # ColorModeTemp = 2   // White with color temperature. Valid fields: t
        if Hue_List["m"] == 2:
            set_kelvin_color(
                self, ADDRESS_MODE["group"], GrpId, ZIGATE_EP, EPout, int(Hue_List["t"]), transit=transitionTemp
            )

        # ColorModeRGB = 3    // Color. Valid fields: r, g, b.
        elif Hue_List["m"] == 3:
            set_rgb_color(
                self,
                ADDRESS_MODE["group"],
                GrpId,
                ZIGATE_EP,
                EPout,
                int(Hue_List["r"]),
                int(Hue_List["g"]),
                int(Hue_List["b"]),
                transit=transitionRGB,
            )

        # ColorModeCustom = 4, // Custom (color + white). Valid fields: r, g, b, cw, ww, depending on device capabilities
        elif Hue_List["m"] == 4:
            # Gledopto GL_008
            # Color: {"b":43,"cw":27,"g":255,"m":4,"r":44,"t":227,"ww":215}
            self.logging("Log", "Not fully implemented device color 4")

            # Process White color
            cw = int(Hue_List["cw"])  # 0 < cw < 255 Cold White
            ww = int(Hue_List["ww"])  # 0 < ww < 255 Warm White
            if cw != 0 and ww != 0:
                set_kelvin_color(self, ADDRESS_MODE["group"], GrpId, ZIGATE_EP, EPout, int(ww), transit=transitionTemp)
            else:
                # How to powerOff the WW/CW channel ?
                pass

            # Process Colour
            set_hue_saturation(
                self,
                ADDRESS_MODE["group"],
                GrpId,
                ZIGATE_EP,
                EPout,
                int(Hue_List["r"]),
                int(Hue_List["g"]),
                int(Hue_List["b"]),
                transit=transitionHue,
            )

        # With saturation and hue, not seen in domoticz but present on zigate, and some device need it
        elif Hue_List["m"] == 9998:
            level = set_hue_saturation(
                self,
                ADDRESS_MODE["group"],
                GrpId,
                ZIGATE_EP,
                EPout,
                int(Hue_List["r"]),
                int(Hue_List["g"]),
                int(Hue_List["b"]),
                transit=transitionHue,
            )

            value = int(level * 254 // 100)
            OnOff = "01"
            self.logging("Debug", "---------- Set Level: %s instead of Level: %s" % (value, Level))
            self.ZigateComm.sendData(
                "0081",
                "%02d" % ADDRESS_MODE["group"]
                + GrpId
                + ZIGATE_EP
                + EPout
                + OnOff
                + Hex_Format(2, value)
                + transitionMoveLevel,
                ackIsDisabled=True,
            )

        # Update Device
        nValue = 1
        sValue = str(Level)
        self.Devices[unit].Update(nValue=int(nValue), sValue=str(sValue), Color=Color_)

    # Request to force ReadAttribute to each devices part of that group
    resetDevicesHearttBeat(self, GrpId)


def resetDevicesHearttBeat(self, GrpId):

    if not self.pluginconf.pluginConf["forceGroupDeviceRefresh"]:
        return

    for NwkId, Ep, Ieee in self.ListOfGroups[GrpId]["Devices"]:
        self.logging("Debug", "processGroupCommand - reset heartbeat for device : %s" % NwkId)
        if NwkId not in self.ListOfDevices:
            if Ieee in self.IEEE2NWK:
                NwkId = self.IEEE2NWK[Ieee]
            else:
                self.logging(
                    "Error", "resetDevicesHearttBeat - Hum Hum something wrong NwkId: %s Ieee %s" % (NwkId, Ieee)
                )

        if NwkId in self.ListOfDevices:
            # Force Read Attribute consideration in the next hearbeat
            if "Heartbeat" in self.ListOfDevices[NwkId]:
                self.ListOfDevices[NwkId]["Heartbeat"] = "0"

            # Reset Health status of corresponding device if any in Not Reachable
            if "Health" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Health"] == "Not Reachable":
                self.ListOfDevices[NwkId]["Health"] = ""
