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
#

"""
    Module: domoTools.py
    Description: Tools to manage Domoticz widget inetractions
"""


import time

from Modules.domoticzAbstractLayer import (
    device_touch_api, domo_read_BatteryLevel, domo_read_Color,
    domo_read_Device_Idx, domo_read_LastUpdate, domo_read_Name,
    domo_read_nValue_sValue, domo_read_Options, domo_read_TimedOut,
    domo_update_api, domoticz_log_api, is_domoticz_extended,
    retreive_widgetid_from_deviceId_unit, timeout_widget_api,
    update_battery_api)
from Modules.switchSelectorWidgets import SWITCH_SELECTORS
from Modules.tools import (is_domoticz_touch,
                           is_domoticz_update_SuppressTriggers, lookupForIEEE)

DELAY_BETWEEN_TOUCH = 120

def RetreiveWidgetTypeList(self, Devices, device_id_ieee, NwkId, DeviceUnit=None):
    """
    Return a list of tuple ( EndPoint, WidgetType, DeviceId)
    If DeviceUnit provides we have to return the WidgetType matching this Device Unit.

    """
    self.log.logging("Widget", "Debug", f"RetreiveWidgetTypeList DeviceId: {device_id_ieee} Unit {DeviceUnit}" , NwkId)
    # Let's retreive All Widgets entries for the entire entry.
    to_return_list = []
    if DeviceUnit:
        Widget_Idx = str(retreive_widgetid_from_deviceId_unit(self, Devices, device_id_ieee, DeviceUnit))
        self.log.logging("Widget", "Debug", f"RetreiveWidgetTypeList Looking for Device Idx {Widget_Idx}" , NwkId)

    if "ClusterType" not in self.ListOfDevices[NwkId] or self.ListOfDevices[NwkId]["ClusterType"] in ( "", {}):
        for iterEp in self.ListOfDevices[NwkId]["Ep"]:
            if "ClusterType" in self.ListOfDevices[NwkId]["Ep"][iterEp]:
                device_cluster_type_list = self.ListOfDevices[NwkId]["Ep"][iterEp]["ClusterType"]
                self.log.logging("Widget", "Debug", f"RetreiveWidgetTypeList 'ClusterType': {device_cluster_type_list}", NwkId,)
                
                if DeviceUnit:
                    if Widget_Idx in device_cluster_type_list:
                        self.log.logging("Widget", "Debug", f"RetreiveWidgetTypeList {Widget_Idx} found", NwkId,)
                        WidgetType = device_cluster_type_list[Widget_Idx]
                        to_return_list.append((iterEp, Widget_Idx, WidgetType))
                        self.log.logging("Widget", "Debug", f"RetreiveWidgetTypeList returning {to_return_list}", NwkId,)
                        return to_return_list

                else:
                    for Widget_Idx in device_cluster_type_list:
                        WidgetType = device_cluster_type_list[Widget_Idx]
                        to_return_list.append((iterEp, Widget_Idx, WidgetType))

        self.log.logging("Widget", "Debug", f"RetreiveWidgetTypeList returning {to_return_list}", NwkId,)
        return to_return_list

    # we are on the old fashion with Type at the global level like for the ( Xiaomi lumi.remote.n286acn01 )
    # In that case we don't need a match with the incoming Ep as the correct one is the Widget EndPoint
    self.log.logging( "Widget", "Debug", "------> OldFashion 'ClusterType': %s" % self.ListOfDevices[NwkId]["ClusterType"], NwkId )
    if DeviceUnit:
        if Widget_Idx in self.ListOfDevices[NwkId]["ClusterType"]:
            WidgetType = self.ListOfDevices[NwkId]["ClusterType"][Widget_Idx]
            to_return_list.append(("00", Widget_Idx, WidgetType))
            return to_return_list
    else:
        for Widget_Idx in self.ListOfDevices[NwkId]["ClusterType"]:
            WidgetType = self.ListOfDevices[NwkId]["ClusterType"][Widget_Idx]
            to_return_list.append(("00", Widget_Idx, WidgetType))

    self.log.logging("Widget", "Debug", f"RetreiveWidgetTypeList returning {to_return_list}", NwkId,)
    return to_return_list


def RetreiveSignalLvlBattery(self, NwkID):

    # Takes the opportunity to update LQI and Battery
    if NwkID not in self.ListOfDevices:
        return ("", "")

    return ( get_signal_level(self, NwkID), get_battery_level(self, NwkID))


def get_signal_level(self, NwkID):
    SignalLevel = self.ListOfDevices[NwkID].get("LQI", "")

    DomoticzRSSI = 12  # Unknown
    
    # La ZiGate+ USB n'a pas d'amplificateur contrairement à la V1. 
    # Le LQI max de la ZiGate+ (V2) est de 170. Cependant, 
    # la ZiGate+ est moins sensible aux perturbations.
    # D'après les tests, la portée entre la v1 et la v2 est sensiblement identique même si le LQI n'est pas gérer de la même manière.
    # La ZiGate v1 par exemple a des pertes de paquets à partir de 50-60 en LQI alors que sur la v2 elle commence à perdre des paquets à 25 LQI.

    SEUIL1, SEUIL2, SEUIL3 = (15, 35, 120) if self.ZiGateModel and self.ZiGateModel == 2 else (30, 75, 180)

    if isinstance(SignalLevel, int):
        if SignalLevel >= SEUIL3:
            DomoticzRSSI = 11
            
        elif SignalLevel >= SEUIL2:
            gamme = SEUIL3 - SEUIL2
            DomoticzRSSI = 4 + round((SignalLevel - SEUIL2) * 6 / gamme)
            
        elif SignalLevel >= SEUIL1:
            gamme = SEUIL2 - SEUIL1
            DomoticzRSSI = 1 + round((SignalLevel - SEUIL1) * 3 / gamme)

    return DomoticzRSSI

    
def get_battery_level(self, NwkID):
    battery_info = self.ListOfDevices[NwkID].get("Battery", {})

    if battery_info and battery_info != {}:
        #self.log.logging( "Widget", "Debug", f"------>  From Battery NwkId: {NwkID} Battery: {battery_info} Type: {type(battery_info)}", NwkID, )
        if isinstance(battery_info, (float)):
            return int(round(battery_info))
        if isinstance(battery_info, (int)):
            return battery_info
    elif "IASBattery" in self.ListOfDevices[NwkID] and isinstance(self.ListOfDevices[NwkID]["IASBattery"], int):
        #self.log.logging( "Widget", "Debug", f"------>  From IASBattery NwkId: {NwkID} Battery: {self.ListOfDevices[NwkID]['IASBattery']} Type: {type(self.ListOfDevices[NwkID]['IASBattery'])}", NwkID, )
        return self.ListOfDevices[NwkID]["IASBattery"]

    return 255
    
    
def WidgetForDeviceId(self, NwkId, DeviceId):

    WidgetType = ""
    for tmpEp in self.ListOfDevices[NwkId]["Ep"]:
        if (
            "ClusterType" in self.ListOfDevices[NwkId]["Ep"][tmpEp]
            and str(DeviceId) in self.ListOfDevices[NwkId]["Ep"][tmpEp]["ClusterType"]
        ):
            WidgetType = self.ListOfDevices[NwkId]["Ep"][tmpEp]["ClusterType"][str(DeviceId)]

    if (
        WidgetType == ""
        and "ClusterType" in self.ListOfDevices[NwkId]
        and str(DeviceId) in self.ListOfDevices[NwkId]["ClusterType"]
    ):
        WidgetType = self.ListOfDevices[NwkId]["ClusterType"][str(DeviceId)]

    return WidgetType


def browse_and_reset_devices_if_needed(self, Devices):
    self.log.logging("WidgetReset", "Debug", "browse_and_reset_devices_if_needed")

    for widget_idx in list(self.ListOfDomoticzWidget):
        widget_info = self.ListOfDomoticzWidget[ widget_idx ]
        unit_key = widget_info[ "Unit" ]
        device_ieee = widget_info[ "DeviceID" ]
        if device_ieee not in self.IEEE2NWK:
            continue

        nwkid = self.IEEE2NWK[device_ieee]
        WidgetType = WidgetForDeviceId(self, nwkid, widget_idx)
        if WidgetType in ( "Motion", "Vibration", SWITCH_SELECTORS):
            reset_device_ieee_unit_if_needed( self, Devices, device_ieee, unit_key, nwkid, WidgetType, widget_idx, time.time())


def _convert_LastUpdate( last_update ):
    try:
        return time.mktime(time.strptime(last_update, "%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        return None


def reset_device_ieee_unit_if_needed( self, Devices, device_ieee, device_unit, nwkid, WidgetType, widget_idx, now):

    self.log.logging("WidgetReset", "Debug", f"reset_device_ieee_unit_if_needed {device_ieee} {device_unit}")
    
    last_update = _convert_LastUpdate( domo_read_LastUpdate(self, Devices, device_ieee, device_unit,) )
    if last_update is None:
        return

    TimedOutMotion, TimedOutSwitchButton = retreive_reset_delays(self, nwkid)
    
    #self.log.logging("WidgetReset", "Debug", f"reset_device_ieee_unit_if_needed {nwkid} WidgetType: {WidgetType} TimedOutMotion: {TimedOutMotion} TimedOutSwitchButton: {TimedOutSwitchButton}", nwkid)

    if WidgetType in ("Motion", "Vibration"):
        if TimedOutMotion is None or TimedOutMotion == 0:
            return
        self.log.logging("WidgetReset", "Debug", f"reset_device_ieee_unit_if_needed {nwkid} reset_motion {TimedOutMotion}", nwkid)
        SignalLevel, BatteryLvl = RetreiveSignalLvlBattery(self, nwkid)
        reset_motion(self, Devices, nwkid, WidgetType, device_ieee, device_unit, SignalLevel, BatteryLvl, widget_idx, now, last_update, TimedOutMotion)

    elif WidgetType in SWITCH_SELECTORS:
        if TimedOutSwitchButton is None or TimedOutSwitchButton == 0:
            return
        if "ForceUpdate" in SWITCH_SELECTORS[WidgetType] and SWITCH_SELECTORS[WidgetType]["ForceUpdate"]:
            self.log.logging("WidgetReset", "Debug", f"reset_device_ieee_unit_if_needed {nwkid} reset_switch_selector {TimedOutSwitchButton}", nwkid)
            SignalLevel, BatteryLvl = RetreiveSignalLvlBattery(self, nwkid)
            reset_switch_selector_PushButton( self, Devices, nwkid, WidgetType, device_ieee, device_unit, SignalLevel, BatteryLvl, now, last_update, TimedOutSwitchButton, )


def retreive_reset_delays(self, nwkid):
    TimedOutMotion = self.pluginconf.pluginConf.get("resetMotiondelay", None)
    TimedOutSwitchButton = self.pluginconf.pluginConf.get("resetSwitchSelectorPushButton", None)

    if "Param" in self.ListOfDevices.get(nwkid, {}):
        params = self.ListOfDevices[nwkid]["Param"]
        TimedOutMotion = int(params.get("resetMotiondelay", TimedOutMotion))
        TimedOutSwitchButton = params.get("resetSwitchSelectorPushButton", TimedOutSwitchButton)

    #self.log.logging("WidgetReset", "Debug", f"retreive_reset_delays {nwkid} {TimedOutMotion} {TimedOutSwitchButton}", nwkid)
    return TimedOutMotion, TimedOutSwitchButton
  

def reset_motion(self, Devices, NwkId, WidgetType, DeviceId_, Unit_, SignalLevel, BatteryLvl, ID, now, lastupdate, TimedOut):
    nValue, sValue = domo_read_nValue_sValue(self, Devices, DeviceId_, Unit_)

    if nValue == 0 and sValue == "Off" or (now - lastupdate) < TimedOut or (self.domoticzdb_DeviceStatus and self.domoticzdb_DeviceStatus.retrieve_timeout_motion(ID) > 0):
        return

    domo_update_api(self, Devices, DeviceId_, Unit_, nValue=0, sValue="Off")
    self.log.logging("WidgetReset", "Debug", "reset_motion - Last update of the device %s %s was %s ago" % (Unit_, WidgetType, (now - lastupdate)), NwkId)


def reset_switch_selector_PushButton(self, Devices, NwkId, WidgetType, DeviceId_, Unit_, SignalLevel, BatteryLvl, now, lastupdate, TimedOut):
    nValue, sValue = domo_read_nValue_sValue(self, Devices, DeviceId_, Unit_)

    #self.log.logging("WidgetReset", "Debug", f"reset_switch_selector_PushButton {NwkId} {nValue}:{sValue} ({now} - {lastupdate}) = {(now - lastupdate)} <? {TimedOut}", NwkId)
    if nValue == 0 or (now - lastupdate) < TimedOut:
        #self.log.logging("WidgetReset", "Debug", f"reset_switch_selector_PushButton {NwkId} too early or already Offs", NwkId)
        return

    options = domo_read_Options(self, Devices, DeviceId_, Unit_)
    if "LevelOffHidden" in options and options["LevelOffHidden"] == "false":
            sValue = "00"

    domo_update_api(self, Devices, DeviceId_, Unit_, nValue=0, sValue=sValue)
    self.log.logging("WidgetReset", "Debug", "reset_switch_selector_PushButton - Last update of the device %s WidgetType: %s was %s ago" % (Unit_, WidgetType, (now - lastupdate)), NwkId)


def update_domoticz_widget(self, Devices, DeviceId, Unit, nValue, sValue, BatteryLvl, SignalLvl, Color_="", ForceUpdate_=False):

    if DeviceId not in self.IEEE2NWK:
        return
    _current_battery_level = domo_read_BatteryLevel( self, Devices, DeviceId, Unit, )
    _current_TimedOut = domo_read_TimedOut( self, Devices, DeviceId, )
    _current_color = domo_read_Color( self, Devices, DeviceId, Unit, )
    _cur_nValue, cur_sValue = domo_read_nValue_sValue(self, Devices, DeviceId, Unit)
    widget_name = domo_read_Name( self, Devices, DeviceId, Unit, )

    self.log.logging( "WidgetUpdate", "Debug", "update_domoticz_widget %s:%s:%s  %3s:%3s:%5s (%15s)" % (
        nValue, sValue, Color_, BatteryLvl, SignalLvl, ForceUpdate_, widget_name), self.IEEE2NWK[ DeviceId ])
    
    update_needed = (
        _cur_nValue != int(nValue)
        or cur_sValue != sValue
        or (Color_ != "" and _current_color != Color_)
        or ForceUpdate_
        or _current_battery_level != int(BatteryLvl)
        or _current_TimedOut
    )
    
    if not update_needed:
        return
    
    force_update_conf = self.pluginconf.pluginConf["forceSwitchSelectorPushButton"] and ForceUpdate_ and _cur_nValue == int(nValue) and cur_sValue == sValue

    if force_update_conf:
        nReset = 0
        sReset = "0"
        if "LevelOffHidden" in Devices[Unit].Options and Devices[Unit].Options["LevelOffHidden"] == "false":
            sReset = "00"
        domo_update_api(self, Devices, DeviceId, Unit, nReset, sReset)

    domo_update_api(self, Devices, DeviceId, Unit, nValue, sValue, SignalLevel=SignalLvl, BatteryLevel=BatteryLvl, TimedOut=0, Color=Color_)

    if self.pluginconf.pluginConf["logDeviceUpdate"]:
        self.log.logging( "Widget", "Log", "UpdateDevice - (%15s) %s:%s" % (widget_name, nValue, sValue))
        domoticz_log_api("UpdateDevice - (%15s) %s:%s" % (widget_name, nValue, sValue))
        
    self.log.logging( "Widget", "Debug", "--->  [Unit: %s] %s:%s:%s %s:%s %s (%15s)" % (
        Unit, nValue, sValue, Color_, BatteryLvl, SignalLvl, ForceUpdate_, widget_name), DeviceId, )


def Update_Battery_Device( self, Devices, NwkId, BatteryLvl, ):

    if not is_domoticz_update_SuppressTriggers( self ):
        return

    ieee = self.ListOfDevices.get(NwkId, {}).get("IEEE")
    if ieee is None:
        return
    update_battery_api(self, Devices, ieee, int(BatteryLvl))
     

def timedOutDevice(self, Devices, NwkId=None, MarkTimedOut=True):
    self.log.logging("WidgetLevel3", "Debug", f"timedOutDevice Object {NwkId} {MarkTimedOut}")

    device_info = self.ListOfDevices.get(NwkId, {})
    if not device_info.get("IEEE") or device_info.get("Health") == "Disabled":
        return

    device_info["Health"] = "TimedOut" if MarkTimedOut else "Live"
    self.log.logging("WidgetLevel3", "Debug", f"timedOutDevice Object {NwkId} MarkTimedOut: {MarkTimedOut}")

    _IEEE = device_info["IEEE"]
    timed_out = domo_read_TimedOut(self, Devices, _IEEE)

    if MarkTimedOut and not timed_out:
        timeout_widget_api(self, Devices, _IEEE, 1)
    elif not MarkTimedOut and timed_out:
        timeout_widget_api(self, Devices, _IEEE, 0)


def lastSeenUpdate(self, Devices, NwkId=None):
    """Just touch the device widgets and if needed remove TimedOut flag"""

    now = int(time.time())

    device_data = self.ListOfDevices.get(NwkId, {})
    if not device_data or "IEEE" not in device_data:
        return

    device_data.setdefault("ErrorManagement", 0)
    health_data = device_data.get("Health")
    if health_data not in ("Disabled", ):
        device_data["Health"] = "Live"

    device_data_stamp = device_data.get( 'Stamp')
    device_data_stamp.setdefault("LastSeen", 0)
    if device_data_stamp.get("LastSeen") and now < ( int(device_data_stamp.get("LastSeen")) + DELAY_BETWEEN_TOUCH):
        self.log.logging("WidgetLevel3", "Debug", f"lastSeenUpdate Nwkid {NwkId} too early {device_data_stamp.get('LastSeen')}")     
        return

    device_data_stamp["LastSeen"] = now
    _IEEE = device_data.get("IEEE", "")

    if not is_domoticz_touch(self):
        self.log.logging("WidgetLevel3", "Debug", f"Not the good Domoticz level for Touch {self.VersionNewFashion} {self.DomoticzMajor} {self.DomoticzMinor}", NwkId)
        return
    
    self.log.logging("WidgetLevel3", "Debug", f"lastSeenUpdate Nwkid {NwkId} DeviceId {_IEEE}")

    if domo_read_TimedOut(self, Devices, _IEEE):
        timeout_widget_api(self, Devices, _IEEE, 0) 
    else:
        device_touch_api(self, Devices, _IEEE)


def GetType(self, Addr, Ep):
    Type = ""
    self.log.logging(
        "WidgetLevel3",
        "Debug",
        "GetType - Model "
        + str(self.ListOfDevices[Addr]["Model"])
        + " Profile ID : "
        + str(self.ListOfDevices[Addr]["ProfileID"])
        + " ZDeviceID : "
        + str(self.ListOfDevices[Addr]["ZDeviceID"]),
        Addr,
    )

    _Model = self.ListOfDevices[Addr]["Model"]
    if _Model != {} and _Model in list(self.DeviceConf.keys()):
        # verifie si le model a ete detecte et est connu dans le fichier DeviceConf.txt
        if Ep in self.DeviceConf[_Model]["Ep"]:
            self.log.logging("WidgetLevel3", "Debug", "Ep: %s found in DeviceConf" % Ep)
            if "Type" in self.DeviceConf[_Model]["Ep"][Ep]:
                self.log.logging("WidgetLevel3", "Debug", " 'Type' entry found inf DeviceConf")
                if self.DeviceConf[_Model]["Ep"][Ep]["Type"] != "":
                    self.log.logging(
                        "WidgetLevel3",
                        "Debug",
                        "GetType - Found Type in DeviceConf : %s" % self.DeviceConf[_Model]["Ep"][Ep]["Type"],
                        Addr,
                    )
                    Type = self.DeviceConf[_Model]["Ep"][Ep]["Type"]
                    Type = str(Type)
                else:
                    self.log.logging(
                        "WidgetLevel3", "Debug" "GetType - Found EpEmpty Type in DeviceConf for %s/%s" % (Addr, Ep), Addr
                    )
            else:
                self.log.logging(
                    "WidgetLevel3", "Debug" "GetType - EpType not found in DeviceConf for %s/%s" % (Addr, Ep), Addr
                )
        else:
            Type = self.DeviceConf[_Model]["Type"]
            self.log.logging(
                "WidgetLevel3", "Debug", "GetType - Found Type in DeviceConf for %s/%s: %s " % (Addr, Ep, Type), Addr
            )
    else:
        self.log.logging(
            "WidgetLevel3",
            "Debug",
            "GetType - Model:  >%s< not found with Ep: %s in DeviceConf. Continue with ClusterSearch"
            % (self.ListOfDevices[Addr]["Model"], Ep),
            Addr,
        )
        self.log.logging("WidgetLevel3", "Debug", "        - List of Entries: %s" % str(self.DeviceConf.keys()), Addr)
        Type = ""

        # Check ProfileID/ZDeviceD
        if "Manufacturer" in self.ListOfDevices[Addr]:
            if self.ListOfDevices[Addr]["Manufacturer"] == "117c":  # Ikea
                if self.ListOfDevices[Addr]["ProfileID"] == "c05e" and self.ListOfDevices[Addr]["ZDeviceID"] == "0830":
                    return "Ikea_Round_5b"

                if self.ListOfDevices[Addr]["ProfileID"] == "c05e" and self.ListOfDevices[Addr]["ZDeviceID"] == "0820":
                    return "Ikea_Round_OnOff"

            elif self.ListOfDevices[Addr]["Manufacturer"] == "100b":  # Philipps Hue
                pass
            elif str(self.ListOfDevices[Addr]["Manufacturer"]).find("LIVOLO") != -1:
                self.log.logging("WidgetLevel3", "Debug", "GetType - Found Livolo based on Manufacturer", Addr)
                return "LivoloSWL/LivoloSWR"

        # Finaly Chec on Cluster
        for cluster in self.ListOfDevices[Addr]["Ep"][Ep]:
            if cluster in ("Type", "ClusterType", "ColorMode"):
                continue

            self.log.logging("WidgetLevel3", "Debug", "GetType - check Type for Cluster : " + str(cluster))

            if Type != "" and Type[:1] != "/":
                Type += "/"

            Type += TypeFromCluster(self, cluster, create_=True, ModelName=_Model)
            self.log.logging("WidgetLevel3", "Debug", "GetType - Type will be set to : " + str(Type))

        # Type+=Type
        # Ne serait-il pas plus simple de faire un .split( '/' ), puis un join ('/')
        # car j'ai un peu de problème sur cette serie de replace.
        # ensuite j'ai vu également des Type avec un / à la fin !!!!!
        # Par exemple :  'Type': 'Switch/LvlControl/',
        Type = Type.replace("/////", "/")
        Type = Type.replace("////", "/")
        Type = Type.replace("///", "/")
        Type = Type.replace("//", "/")
        if Type[:-1] == "/":
            Type = Type[:-1]
        if Type[0:] == "/":
            Type = Type[1:]

        self.log.logging("WidgetLevel3", "Debug", "GetType - ClusterSearch return : %s" % Type, Addr)

    self.log.logging("WidgetLevel3", "Debug", "GetType returning: %s" % Type, Addr)

    return Type

CLUSTER_TO_TYPE = {
    "0001": "Voltage", 
    "0006": "Switch", 
    "0008": "LvlControl", 
    "0009": "Alarm", 
    "000c": "Analog", 
    "0101": "DoorLock", 
    "0102": "WindowCovering", 
    "0201": "Temp/ThermoSetpoint/ThermoMode/Valve", 
    "0202": "FanControl", 
    "0300": "ColorControl", 
    "0400": "Lux", 
    "0402": "Temp", 
    "0403": "Baro", 
    "0405": "Humi", 
    "0406": "Motion",
    "042a": "PM25", 
    "0702": "Power/Meter", 
    "0500": "Door", 
    "0502": "AlarmWD", 
    "0b04": "Power/Meter/Ampere", 
    "fc00": "LvlControl", 
    "fc21": "BSO-Orientation", 
    "rmt1": "Ikea_Round_5b", 
    "LumiLock": "LumiLock", 
    "Strenght": "Strenght",
    "Orientation": "Orientation", 
    "WaterCounter": "WaterCounter",
    "fc40": "ThermoMode", 
    "ff66": "DEMAIN",
    "fc80": "Heiman",
    "Distance": "Distance",
    "TamperSwitch": "TamperSwitch",
    "Notification": "Notification",
    "PWFactor": "PWFactor",
    "phMeter": "phMeter",
    "ec": "ec",
    "orp": "orp",
    "RainIntensity": "RainIntensity",
    "freeChlorine": "freeChlorine",
    "salinity": "salinity",
    "tds": "tds"
}

def TypeFromCluster(self, cluster, create_=False, ProfileID_="", ZDeviceID_="", ModelName=""):

    self.log.logging(
        "WidgetLevel3",
        "Debug",
        "---> ClusterSearch - Cluster: %s, ProfileID: %s, ZDeviceID: %s, create: %s"
        % (cluster, ProfileID_, ZDeviceID_, create_),
    )

    if ProfileID_ == "c05e":
        if ZDeviceID_ == "0830":
            return "Ikea_Round_5b"

        if ZDeviceID_ == "0820":
            return "Ikea_Round_OnOff"

    if cluster == "000c" and ModelName in ("lumi.sensor_cube.aqgl01", "lumi.sensor_cube",) and not create_:
        return "XCube"

    if cluster == "0012" and not create_:
        return "XCube"

    return CLUSTER_TO_TYPE[ cluster ] if cluster in CLUSTER_TO_TYPE else ""


def subtypeRGB_FromProfile_Device_IDs_onEp2(EndPoints_V2):
    ColorControlRGB = 0x02  # RGB color palette / Dimable
    ColorControlRGBWW = 0x04  # RGB + WW
    ColorControlFull = 0x07  # 3 Color palettes widget
    ColorControlWW = 0x08  # WW
    ColorControlRGBWZ = 0x06  # RGB W Z
    ColorControlRGBW = 0x01  # RGB W
    Subtype = None
    for ep in EndPoints_V2:
        if EndPoints_V2[ep]["ZDeviceID"] == "0101":  # Dimable light
            continue

        elif EndPoints_V2[ep]["ZDeviceID"] == "0102":  # Color dimable light
            Subtype = ColorControlFull
            break

        elif EndPoints_V2[ep]["ZDeviceID"] == "010c":  # White color temperature light
            Subtype = ColorControlWW
            break

        elif EndPoints_V2[ep]["ZDeviceID"] == "010d":  # Extended color light
            # ZBT-ExtendedColor /  Müller-Licht 44062 "tint white + color" (LED E27 9,5W 806lm 1.800-6.500K RGB)
            Subtype = ColorControlRGBWW
    return Subtype


def subtypeRGB_FromProfile_Device_IDs(EndPoints, Model, ProfileID, ZDeviceID, ColorInfos=None):

    # Type 0xF1    pTypeColorSwitch
    # Switchtype 7 STYPE_Dimmer
    # SubType sTypeColor_RGB_W                0x01 // RGB + white, either RGB or white can be lit
    # SubType sTypeColor_White                0x03 // Monochrome white
    # SubType sTypeColor_RGB_CW_WW            0x04 // RGB + cold white + warm white, either RGB or white can be lit
    # SubType sTypeColor_LivCol               0x05
    # SubType sTypeColor_RGB_W_Z              0x06 // Like RGBW, but allows combining RGB and white
    # The test should be done in an other way ( ProfileID for instance )
    # default: SubType sTypeColor_RGB_CW_WW_Z 0x07 // Like RGBWW, # but allows combining RGB and white

    ColorControlRGB = 0x02  # RGB color palette / Dimable
    ColorControlRGBWW = 0x04  # RGB + WW
    ColorControlFull = 0x07  # 3 Color palettes widget
    ColorControlWW = 0x08  # WW
    ColorControlRGBWZ = 0x06  # RGB W Z
    ColorControlRGBW = 0x01  # RGB W

    Subtype = None
    ZLL_Commissioning = False

    ColorMode = 0
    if ColorInfos and "ColorMode" in ColorInfos:
        ColorMode = ColorInfos["ColorMode"]

    for iterEp in EndPoints:
        if "1000" in iterEp:
            ZLL_Commissioning = True
            break

    # Device specifics section
    if Model and Model == "lumi.light.aqcn02":
        Subtype = ColorControlWW

    # Philipps Hue
    if Subtype is None and ProfileID == "a1e0" and ZDeviceID == "0061":
        Subtype = ColorControlRGBWW

    # ZLL LightLink
    if Subtype is None and ProfileID == "c05e":
        # We should Check that ZLL Commissioning is also there. Cluster 0x1000
        if ZDeviceID == "0100":  # LED1622G12.Tradfri ou phillips hue white
            pass

        elif ZDeviceID == "0200":  # ampoule Tradfri LED1624G9
            Subtype = ColorControlFull

        elif ZDeviceID == "0210":  #
            Subtype = ColorControlRGBWW

        elif ZDeviceID == "0220":  # ampoule Tradfi LED1545G12.Tradfri
            Subtype = ColorControlWW

    # Home Automation / ZHA
    if Subtype is None and ProfileID == "0104":  # Home Automation
        if ZLL_Commissioning and ZDeviceID == "0100":  # Most likely IKEA Tradfri bulb LED1622G12
            Subtype = ColorControlWW

        elif ZDeviceID == "0101":  # Dimable light
            pass

        elif ZDeviceID == "0102":  # Color dimable light
            Subtype = ColorControlFull

        elif ZDeviceID == "010c":  # White color temperature light
            Subtype = ColorControlWW

        elif ZDeviceID == "010d":  # Extended color light
            # ZBT-ExtendedColor /  Müller-Licht 44062 "tint white + color" (LED E27 9,5W 806lm 1.800-6.500K RGB)
            Subtype = ColorControlRGBWW

    if Subtype is None and ColorInfos:
        if ColorMode == 2:
            Subtype = ColorControlWW

        elif ColorMode == 1:
            Subtype = ColorControlRGB

        else:
            Subtype = ColorControlFull

    if Subtype is None:
        Subtype = ColorControlFull

    return Subtype


def remove_bad_cluster_type_entry(self, NwkId, Ep, clusterID, Widget_Idx ):
    
    if NwkId not in self.ListOfDevices:
        return
    if "Ep" not in self.ListOfDevices[ NwkId ]:
        return
    if (
        Ep in self.ListOfDevices[NwkId]["Ep"] 
        and "ClusterType" in self.ListOfDevices[NwkId]["Ep"][Ep] 
        and Widget_Idx in self.ListOfDevices[NwkId]["Ep"][Ep]["ClusterType"]
    ):
        del self.ListOfDevices[ NwkId ][ "Ep"][ Ep ][ "ClusterType" ][ Widget_Idx ]
        return True
    return False

def remove_all_widgets( self, Devices, NwkId):
    
    if 'IEEE' not in self.ListOfDevices[ NwkId ]:
        return
    ieee = self.ListOfDevices[ NwkId ]['IEEE']

    for _unit in list(Devices):
        if Devices[_unit].DeviceID == ieee:
            Devices[_unit].Delete()
        
    if "ClusterType" in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["ClusterType"] = {}
    for _ep in self.ListOfDevices[NwkId]["Ep"]:
        if "ClusterType" in self.ListOfDevices[NwkId]["Ep"][ _ep ]:
            self.ListOfDevices[NwkId]["Ep"][ _ep ]["ClusterType"] = {}
    
        
def update_model_name( self, nwkid, new_model ):
    self.ListOfDevices[ nwkid ]["Model"] = new_model