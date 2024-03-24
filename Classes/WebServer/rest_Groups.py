#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license


import json
from time import time

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.domoticzAbstractLayer import (
    domo_browse_widgets, domo_read_Device_Idx, domo_read_Name,
    domoticz_error_api, retreive_widgetid_from_deviceId_unit)

LIST_CLUSTERTYPE_FOR_GROUPS = ( 
    "LvlControl", "Switch", "Plug",
    "SwitchAQ2", "DSwitch", "Button", "DButton",
    "LivoloSWL", "LivoloSWR",
    "ColorControlRGB", "ColorControlWW", "ColorControlRGBWW", "ColorControlFull", "ColorControl",
    "VenetianInverted", "Venetian",
    "WindowCovering",
    "Curtain", "CurtainInverted",
    "VanneInverted", "Vanne",
    "BlindInverted", "Blind",
    "BSO-Volet", "BSO-Orientation",
    "FanControl", "CAC221ACMode",
)


  
def rest_zGroup_lst_avlble_dev(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())

    if verb != "GET":
        return _response

    device_lst = [ _coordinator_infos(self) ]

    for nwkid in self.ListOfDevices:
        if nwkid == "0000":
            # Done just before entering in the loop
            continue

        if not _is_ikea_round_remote_or_battery_enabled_or_main_powered(self, nwkid):
            self.logging("Debug", "rest_zGroup_lst_avlble_dev - %s not a Main Powered device." % nwkid)
            continue

        if not is_ready_for_widget_infos(self, nwkid):
            self.logging("Debug", "rest_zGroup_lst_avlble_dev - %s not all infos available skiping." % nwkid)
            continue
        
        device_entry = self.ListOfDevices[nwkid]
        device_entry_endpoints = self.ListOfDevices[nwkid]["Ep"]

        _device = {"_NwkId": nwkid, "WidgetList": []}
        for ep in device_entry_endpoints:
            if _is_ikea_round_remote(self, nwkid, ep):
                widgetID = ""
                for iterDev in device_entry_endpoints["01"]["ClusterType"]:
                    if device_entry_endpoints["01"]["ClusterType"][iterDev] == "Ikea_Round_5b":
                        widgetID = iterDev
                        widget = _build_device_widgetList_infos( self, widgetID, ep, self.ListOfDevices[nwkid]["ZDeviceName"] )
                        _device["WidgetList"].extend( widget )
                if _device not in device_lst:
                    device_lst.append(_device)

                continue  # Next Ep, as we can have only 1 Ikea round per group

            if is_cluster_not_for_group( self, nwkid, ep):
                continue

            if "ClusterType" in device_entry_endpoints[ep]:
                clusterType = device_entry_endpoints[ep]["ClusterType"]
                for widgetID in clusterType:
                    if clusterType[widgetID] not in LIST_CLUSTERTYPE_FOR_GROUPS:
                        continue

                    widget = _build_device_widgetList_infos( self, widgetID, ep, self.ListOfDevices[nwkid]["ZDeviceName"] )
                    _device["WidgetList"].extend( widget )

        if "ClusterType" in device_entry:
            clusterType = device_entry["ClusterType"]

            for widgetID in clusterType:
                if clusterType[widgetID] not in LIST_CLUSTERTYPE_FOR_GROUPS:
                    continue

                widget = _build_device_widgetList_infos( self, widgetID, ep, self.ListOfDevices[nwkid]["ZDeviceName"] )
                _device["WidgetList"].extend( widget)

        if _device not in device_lst:
            device_lst.append(_device)

    self.logging("Debug", "Response: %s" % device_lst)
    _response["Data"] = json.dumps(device_lst, sort_keys=True)

    return _response


def is_ready_for_widget_infos(self, nwkid):
    return "Ep" in self.ListOfDevices[nwkid] and "ZDeviceName" in self.ListOfDevices[nwkid] and "IEEE" in self.ListOfDevices[nwkid]


def _is_ikea_round_remote_or_battery_enabled_or_main_powered(self, nwkid):
    """ Check if Main Powered, GroupOnBattery is enabled or we have an Ikea Round 5B """
    return (
        "MacCapa" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["MacCapa"] == "8e"
        or self.pluginconf.pluginConf["GroupOnBattery"]
        or "Type" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Type"] == "Ikea_Round_5b"
    )


def _is_ikea_round_remote(self, nwkid, ep):
    return "Type" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Type"] == "Ikea_Round_5b" and ep == "01" and "ClusterType" in self.ListOfDevices[nwkid]["Ep"]["01"]


def _coordinator_infos(self):
    _device = {"_NwkId": "0000", "WidgetList": []}
    _widget = {
        "_ID": "",
        "Name": "",
        "IEEE": "0000000000000000",
        "Ep": "01",
        "ZDeviceName": "Zigate (Coordinator)",
    }
    _device["WidgetList"].append(_widget)
    if self.ControllerData and "IEEE" in self.ControllerData:
        _widget["IEEE"] = self.ControllerData["IEEE"]
        _device["_NwkId"] = self.ControllerData["Short Address"]

    return _device


def is_cluster_not_for_group( self, nwkid, ep):

    return (
        "ClusterType" not in self.ListOfDevices[nwkid]
        and "ClusterType" not in self.ListOfDevices[nwkid]["Ep"][ep]
        and "0004" not in self.ListOfDevices[nwkid]["Ep"][ep]
        and "0006" not in self.ListOfDevices[nwkid]["Ep"][ep]
        and "0008" not in self.ListOfDevices[nwkid]["Ep"][ep]
        and "0102" not in self.ListOfDevices[nwkid]["Ep"][ep]
        and "0201" not in self.ListOfDevices[nwkid]["Ep"][ep]
        and "0202" not in self.ListOfDevices[nwkid]["Ep"][ep]
    )

      
def _build_device_widgetList_infos( self, widgetID, ep, ZDeviceName ):
    self.logging("Debug", f"_build_device_widgetList_infos - for WidgetIdx {widgetID} ep {ep} Zname {ZDeviceName}")
    widget_list = []
    
    for device_ieee, unit in domo_browse_widgets(self, self.Devices): 
        widget_idx = retreive_widgetid_from_deviceId_unit(self, self.Devices, device_ieee, unit)
        if widget_idx != int(widgetID):
            continue
        widget = {
            "_ID": domo_read_Device_Idx(self,self.Devices,device_ieee,unit,),
            "Name": domo_read_Name( self, self.Devices, device_ieee, unit, ),
            "IEEE": device_ieee,
            "Ep": ep,
            "ZDeviceName": ZDeviceName,
        }
        widget_list.append( widget )
    return widget_list


def rest_rescan_group(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
    if verb != "GET":
        return _response
    if self.groupmgt:
        self.groupmgt.ScanAllDevicesForGroupMemberShip()
    else:
        domoticz_error_api("rest_rescan_group Group not enabled!!!")
    action = {"Name": "Full Scan", "TimeStamp": int(time())}
    _response["Data"] = json.dumps(action, sort_keys=True)

    return _response


def rest_scan_devices_for_group(self, verb, data, parameter):
    # wget --method=PUT --body-data='[ "0000", "0001", "0002", "0003" ]' http://127.0.0.1:9442/rest-zigate/1/ScanDeviceForGrp

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None
    if self.groupmgt is None:
        # Group is not enabled!
        return _response

    if verb != "PUT":
        # Only Put command with a Valid JSON is allow
        return _response

    if data is None:
        return _response

    if len(parameter) != 0:
        return _response

    # We receive a JSON with a list of NwkId to be scaned
    data = data.decode("utf8")
    data = json.loads(data)
    self.logging("Debug", "rest_scan_devices_for_group - Trigger GroupMemberShip scan for devices: %s " % (data))
    self.groupmgt.ScanDevicesForGroupMemberShip(data)
    action = {"Name": "Scan of device requested.", "TimeStamp": int(time())}
    _response["Data"] = json.dumps(action, sort_keys=True)
    return _response


def rest_zGroup(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())

    self.logging("Log", f"rest_zGroup {verb} {data} {parameters}")

    if verb == "GET":
        return _response if self.groupmgt is None else _zgroup_get(self, parameters)

    if verb == "PUT":
        _zgroup_put( self, data, parameters)


def _zgroup_put( self, data, parameters):
    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None
    if not self.groupmgt:
        domoticz_error_api("Looks like Group Management is not enabled")
        _response["Data"] = {}
        return _response

    ListOfGroups = self.groupmgt.ListOfGroups
    grp_lst = []
    if len(parameters) == 0:
        data = data.decode("utf8")
        _response["Data"] = {}
        self.groupmgt.process_web_request(json.loads(data))

    return _response


def _zgroup_get(self, parameters):
    self.logging("Debug", f"zgroup_get - {parameters}")
    _response = prepResponseMessage(self, setupHeadersResponse())

    ListOfGroups = self.groupmgt.ListOfGroups
    if ListOfGroups is None:
        return _response
    
    zgroup_lst = []
    for itergrp, group_info in ListOfGroups.items():
        self.logging("Debug", f"_zgroup_get - {itergrp} {group_info}")
        if len(parameters) == 1 and itergrp != parameters[0]:
            continue

        zgroup = {
            "_GroupId": itergrp,
            "GroupName": group_info.get("Name", ""),
            "Devices": [],
        }
        for itemDevice in group_info.get("Devices", []):
            if len(itemDevice) == 2:
                dev, ep = itemDevice
                ieee = self.ListOfDevices.get(dev, {}).get("IEEE", "")
            elif len(itemDevice) == 3:
                dev, ep, ieee = itemDevice
            zgroup["Devices"].append( {"_NwkId": dev, "Ep": ep, "IEEE": ieee} )

        zgroup["WidgetStyle"] = group_info.get("WidgetStyle", "")
        zgroup["Cluster"] = group_info.get("Cluster", "")
        zgroup["nValue"] = group_info.get("nValue", "")
        zgroup["sValue"] = group_info.get("sValue", "")

        if "Tradfri Remote" in group_info:
            zgroup["Devices"].append(  {"_NwkId": group_info["Tradfri Remote"]} )

        self.logging("Debug", f"Processed Group: {itergrp} {zgroup}")
    
        zgroup_lst.append(zgroup)
        
    _response["Data"] = json.dumps(zgroup_lst, sort_keys=True)
    return _response