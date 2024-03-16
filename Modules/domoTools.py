#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: domoTools.py
    Description: Tools to manage Domoticz widget inetractions
"""


import time

from Modules.domoticzAbstractLayer import (device_touch_api, domo_update_api,
                                           domoticz_log_api,
                                           timeout_widget_api)
from Modules.switchSelectorWidgets import SWITCH_SELECTORS
from Modules.tools import (is_domoticz_touch,
                           is_domoticz_update_SuppressTriggers, lookupForIEEE)


def RetreiveWidgetTypeList(self, Devices, NwkId, DeviceUnit=None):
    """
    Return a list of tuple ( EndPoint, WidgetType, DeviceId)
    If DeviceUnit provides we have to return the WidgetType matching this Device Unit.

    """

    # Let's retreive All Widgets entries for the entire entry.
    ClusterTypeList = []
    if DeviceUnit:
        WidgetId = str(Devices[DeviceUnit].ID)
        self.log.logging("Widget", "Debug", "------> Looking for %s" % WidgetId, NwkId)

    if (
        "ClusterType" in self.ListOfDevices[NwkId]
        and self.ListOfDevices[NwkId]["ClusterType"] != ""
        and self.ListOfDevices[NwkId]["ClusterType"] != {}
    ):
        # we are on the old fashion with Type at the global level like for the ( Xiaomi lumi.remote.n286acn01 )
        # In that case we don't need a match with the incoming Ep as the correct one is the Widget EndPoint
        self.log.logging(
            "Widget", "Debug", "------> OldFashion 'ClusterType': %s" % self.ListOfDevices[NwkId]["ClusterType"], NwkId
        )
        if DeviceUnit:
            if WidgetId in self.ListOfDevices[NwkId]["ClusterType"]:
                WidgetType = self.ListOfDevices[NwkId]["ClusterType"][WidgetId]
                ClusterTypeList.append(("00", WidgetId, WidgetType))
                return ClusterTypeList
        else:
            for WidgetId in self.ListOfDevices[NwkId]["ClusterType"]:
                WidgetType = self.ListOfDevices[NwkId]["ClusterType"][WidgetId]
                ClusterTypeList.append(("00", WidgetId, WidgetType))

    for iterEp in self.ListOfDevices[NwkId]["Ep"]:
        if "ClusterType" in self.ListOfDevices[NwkId]["Ep"][iterEp]:
            self.log.logging(
                "Widget",
                "Debug",
                "------> 'ClusterType': %s" % self.ListOfDevices[NwkId]["Ep"][iterEp]["ClusterType"],
                NwkId,
            )
            if DeviceUnit:
                if WidgetId in self.ListOfDevices[NwkId]["Ep"][iterEp]["ClusterType"]:
                    WidgetType = self.ListOfDevices[NwkId]["Ep"][iterEp]["ClusterType"][WidgetId]
                    ClusterTypeList.append((iterEp, WidgetId, WidgetType))
                    return ClusterTypeList
            else:
                for WidgetId in self.ListOfDevices[NwkId]["Ep"][iterEp]["ClusterType"]:
                    WidgetType = self.ListOfDevices[NwkId]["Ep"][iterEp]["ClusterType"][WidgetId]
                    ClusterTypeList.append((iterEp, WidgetId, WidgetType))

    return ClusterTypeList


def RetreiveSignalLvlBattery(self, NwkID):

    # Takes the opportunity to update LQI and Battery
    if NwkID not in self.ListOfDevices:
        return ("", "")

    return ( get_signal_level(self, NwkID), get_battery_level(self, NwkID))

def get_signal_level(self, NwkID):
    
    SignalLevel = ""
    if "LQI" in self.ListOfDevices[NwkID]:
        SignalLevel = self.ListOfDevices[NwkID]["LQI"]

    DomoticzRSSI = 12  # Unknown

    # La ZiGate+ USB n'a pas d'amplificateur contrairement à la V1. 
    # Le LQI max de la ZiGate+ (V2) est de 170. Cependant, 
    # la ZiGate+ est moins sensible aux perturbations.
    # D'après les tests, la portée entre la v1 et la v2 est sensiblement identique même si le LQI n'est pas gérer de la même manière.
    # La ZiGate v1 par exemple a des pertes de paquets à partir de 50-60 en LQI alors que sur la v2 elle commence à perdre des paquets à 25 LQI.
    if self.ZiGateModel and self.ZiGateModel == 2:
        SEUIL1 = 15
        SEUIL2 = 35
        SEUIL3 = 120
    else:
        SEUIL1 = 30
        SEUIL2 = 75
        SEUIL3 = 180

    if isinstance(SignalLevel, int):
        # rssi = round((SignalLevel * 11) / 255)
        DomoticzRSSI = 0
        if SignalLevel >= SEUIL3:
            #  SEUIL3 < ZiGate LQI < 255 -> 11
            DomoticzRSSI = 11
        elif SignalLevel >= SEUIL2:
            # SEUIL2 <= ZiGate LQI <= SEUIL3 --> 4 - 10 ( 6 )
            gamme = SEUIL3 - SEUIL2
            SignalLevel = SignalLevel - SEUIL2
            DomoticzRSSI = 4 + round((SignalLevel * 6) / gamme)
        elif SignalLevel >= SEUIL1:
            # SEUIL1 < ZiGate LQI < SEUIL2 --> 1 - 3 ( 3 )
            gamme = SEUIL2 - SEUIL1
            SignalLevel = SignalLevel - SEUIL1
            DomoticzRSSI = 1 + round((SignalLevel * 3) / gamme)

    return DomoticzRSSI

    
def get_battery_level(self, NwkID):

    if "Battery" in self.ListOfDevices[NwkID] and self.ListOfDevices[NwkID]["Battery"] not in ( {}, ):
        self.log.logging(
            "Widget",
            "Debug",
            "------>  From Battery NwkId: %s Battery: %s Type: %s"
            % (NwkID, self.ListOfDevices[NwkID]["Battery"], type(self.ListOfDevices[NwkID]["Battery"])),
            NwkID,
        )
        if isinstance(self.ListOfDevices[NwkID]["Battery"], (float)):
            return int(round((self.ListOfDevices[NwkID]["Battery"])))
        if isinstance(self.ListOfDevices[NwkID]["Battery"], (int)):
            return self.ListOfDevices[NwkID]["Battery"]
    elif (
        "IASBattery" in self.ListOfDevices[NwkID]
        and isinstance(self.ListOfDevices[NwkID]["IASBattery"], int)
    ):
        self.log.logging(
            "Widget",
            "Debug",
            "------>  From IASBattery NwkId: %s Battery: %s Type: %s"
            % (NwkID, self.ListOfDevices[NwkID]["IASBattery"], type(self.ListOfDevices[NwkID]["IASBattery"])),
            NwkID,
        )

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


def ResetDevice(self, Devices):
    #
    # Reset all Devices from the ClusterType Motion after 30s
    #
    self.log.logging( "Widget", "Debug", "ResetDevice")

    now = time.time()
    
    for unit in list(Devices):
        TimedOutMotion = self.pluginconf.pluginConf["resetMotiondelay"]
        TimedOutSwitchButton = self.pluginconf.pluginConf["resetSwitchSelectorPushButton"]
        if unit not in Devices:
            continue
        Ieee = Devices[unit].DeviceID
        if Ieee not in self.IEEE2NWK:
            # Unknown !
            continue

        LUpdate = Devices[unit].LastUpdate
        try:
            LUpdate = time.mktime(time.strptime(LUpdate, "%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            self.log.logging( "Widget", "Error", "Something wrong to decode Domoticz LastUpdate %s for Unit: %s Ieee: %s" % (LUpdate, unit, Ieee), )
            continue

        # Look for the corresponding Widget
        NWKID = self.IEEE2NWK[Ieee]
        if NWKID not in self.ListOfDevices:
            # If the NwkId is not found, it may have switch, let's check
            ieee_retreived_from_nwkid = lookupForIEEE(self, NWKID, True)
            if ieee_retreived_from_nwkid is None or Ieee != ieee_retreived_from_nwkid:
                # self.log.logging( "Widget", "Error", "ResetDevice inconsistency %s/%s not in plugin db: %s, Ieee: %s" %(
                #     NWKID, Ieee, self.ListOfDevices.keys(), str(self.IEEE2NWK) ), NWKID)
                continue

        if "Param" in self.ListOfDevices[NWKID]:
            if "resetMotiondelay" in self.ListOfDevices[NWKID]["Param"]:
                TimedOutMotion = int(self.ListOfDevices[NWKID]["Param"]["resetMotiondelay"])
            if "resetSwitchSelectorPushButton" in self.ListOfDevices[NWKID]["Param"]:
                TimedOutSwitchButton = self.ListOfDevices[NWKID]["Param"]["resetSwitchSelectorPushButton"]

        ID = Devices[unit].ID
        WidgetType = ""
        WidgetType = WidgetForDeviceId(self, NWKID, ID)
        if WidgetType == "":
            continue

        SignalLevel, BatteryLvl = RetreiveSignalLvlBattery(self, NWKID)

        if TimedOutMotion and WidgetType in ("Motion", "Vibration"):
            resetMotion(self, Devices, NWKID, WidgetType, unit, SignalLevel, BatteryLvl, now, LUpdate, TimedOutMotion)

        elif TimedOutSwitchButton and WidgetType in SWITCH_SELECTORS:
            if "ForceUpdate" in SWITCH_SELECTORS[WidgetType] and SWITCH_SELECTORS[WidgetType]["ForceUpdate"]:
                resetSwitchSelectorPushButton( self, Devices, NWKID, WidgetType, unit, SignalLevel, BatteryLvl, now, LUpdate, TimedOutSwitchButton, )
    self.log.logging( "Widget", "Debug", "ResetDevice end")

def resetMotion(self, Devices, NwkId, WidgetType, unit, SignalLevel, BatteryLvl, now, lastupdate, TimedOut):
    self.log.logging( "Widget", "Debug", "resetMotion %s %s %s" %( NwkId, WidgetType, unit))
    if Devices[unit].nValue == 0 and Devices[unit].sValue == "Off":
        # Nothing to Reset
        return
    if self.domoticzdb_DeviceStatus:
        from Classes.DomoticzDB import DomoticzDB_DeviceStatus

        # Let's check if we have a Device TimeOut specified by end user
        if self.domoticzdb_DeviceStatus.retreiveTimeOut_Motion(Devices[unit].ID) > 0:
            return

    if (now - lastupdate) >= TimedOut:  
        Devices[unit].Update(nValue=0, sValue="Off")
        self.log.logging( "Widget", "Debug", "Last update of the devices %s %s was %s ago" % (unit, WidgetType, (now - lastupdate)), NwkId, )


def resetSwitchSelectorPushButton( self, Devices, NwkId, WidgetType, unit, SignalLevel, BatteryLvl, now, lastupdate, TimedOut ):
    self.log.logging( "Widget", "Debug", "resetSwitchSelectorPushButton %s %s %s" %( NwkId, WidgetType, unit))

    if Devices[unit].nValue == 0:
        return
    if (now - lastupdate) < TimedOut:
        return
    # Domoticz.Log("Options: %s" %Devices[unit].Options)
    nValue = 0
    sValue = "0"
    if "LevelOffHidden" in Devices[unit].Options and Devices[unit].Options["LevelOffHidden"] == "false":
        sValue = "00"
    Devices[unit].Update(nValue=nValue, sValue=sValue)

    self.log.logging( "Widget", "Debug", "Last update of the devices %s WidgetType: %s was %s ago" % (unit, WidgetType, (now - lastupdate)), NwkId, )
    # Domoticz.Log(" Update nValue: %s sValue: %s" %(nValue, sValue))

def UpdateDevice_v2(self, Devices, Unit, nValue, sValue, BatteryLvl, SignalLvl, Color_="", ForceUpdate_=False):

    if Unit not in Devices:
        self.log.logging("Widget", "Error", "Droping Update to Device due to Unit %s not found" % Unit)
        return
    if Devices[Unit].DeviceID not in self.IEEE2NWK:
        self.log.logging("Widget", "Error", "Droping Update to Device due to DeviceID %s not found in IEEE2NWK %s" % (
            Devices[Unit].DeviceID, str(self.IEEE2NWK)) )
        return

    self.log.logging( "Widget", "Debug", "UpdateDevice_v2 %s:%s:%s   %3s:%3s:%5s (%15s)" % (
        nValue, sValue, Color_, BatteryLvl, SignalLvl, ForceUpdate_, Devices[Unit].Name), self.IEEE2NWK[Devices[Unit].DeviceID], )

    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if Unit not in Devices:
        return

    if (
        (Devices[Unit].nValue != int(nValue))
        or (Devices[Unit].sValue != sValue)
        or (Color_ != "" and Devices[Unit].Color != Color_)
        or ForceUpdate_
        or Devices[Unit].BatteryLevel != int(BatteryLvl)
        or Devices[Unit].TimedOut
        ):

        DeviceID_ = None    # This is required when we will use The Extended Framework
        if (
            self.pluginconf.pluginConf["forceSwitchSelectorPushButton"]
            and ForceUpdate_
            and (Devices[Unit].nValue == int(nValue))
            and (Devices[Unit].sValue == sValue)
            ):

            # Due to new version of Domoticz which do not log in case we Update the same value
            nReset = 0
            sReset = "0"
            if "LevelOffHidden" in Devices[Unit].Options:
                LevelOffHidden = Devices[Unit].Options["LevelOffHidden"]
                if LevelOffHidden == "false":
                    sReset = "00"
            domo_update_api(self, Devices, DeviceID_, Unit, nReset, sReset)

        domo_update_api(self, Devices, DeviceID_, Unit, nValue, sValue, SignalLevel=SignalLvl, BatteryLevel=BatteryLvl, TimedOut=0, Color=Color_,)

        if self.pluginconf.pluginConf["logDeviceUpdate"]:
            self.log.logging( "Widget", "Log", "UpdateDevice - (%15s) %s:%s" % (Devices[Unit].Name, nValue, sValue))
            domoticz_log_api( "UpdateDevice - (%15s) %s:%s" % (Devices[Unit].Name, nValue, sValue))
        self.log.logging( "Widget", "Debug", "--->  [Unit: %s] %s:%s:%s %s:%s %s (%15s)" % (
            Unit, nValue, sValue, Color_, BatteryLvl, SignalLvl, ForceUpdate_, Devices[Unit].Name), self.IEEE2NWK[Devices[Unit].DeviceID], )

def Update_Battery_Device( self, Devices, NwkId, BatteryLvl, ):

    if not is_domoticz_update_SuppressTriggers( self ):
        return

    if NwkId not in self.ListOfDevices:
        return
    if "IEEE" not in self.ListOfDevices[NwkId]:
        return
    ieee = self.ListOfDevices[NwkId]["IEEE"]

    for device_unit in Devices:
        if Devices[device_unit].DeviceID != ieee:
            continue
        self.log.logging( "Widget", "Debug", "Update_Battery_Device Battery: now: %s prev: %s (%15s)" % (
            BatteryLvl, Devices[device_unit].BatteryLevel, Devices[device_unit].Name), )

        if Devices[device_unit].BatteryLevel == int(BatteryLvl):
            continue

        self.log.logging( "Widget", "Debug", "Update_Battery_Device Battery: %s  (%15s)" % (BatteryLvl, Devices[device_unit].Name) )
        Devices[device_unit].Update(
            nValue=Devices[device_unit].nValue,
            sValue=Devices[device_unit].sValue,
            BatteryLevel=int(BatteryLvl),
            SuppressTriggers=True,
        )


def timedOutDevice(self, Devices, Unit=None, NwkId=None, MarkTimedOut=True):

    self.log.logging( "Widget", "Debug", "timedOutDevice unit %s nwkid: %s MarkTimedOut: %s" % (
        Unit, NwkId, MarkTimedOut), NwkId, )

    _Unit = _nValue = _sValue = None

    if Unit:
        DeviceID = None
        if MarkTimedOut and not Devices[Unit].TimedOut:
            timeout_widget_api(self, Devices, DeviceID, Unit, 1)

        elif not MarkTimedOut and Devices[Unit].TimedOut:
            timeout_widget_api(self, Devices, DeviceID, Unit, 0)

    elif NwkId:
        if NwkId not in self.ListOfDevices:
            return
        if "IEEE" not in self.ListOfDevices[NwkId]:
            return
        _IEEE = self.ListOfDevices[NwkId]["IEEE"]
        if self.ListOfDevices[NwkId]["Health"] == "Disabled":
            return
        
        self.ListOfDevices[NwkId]["Health"] = "TimedOut" if MarkTimedOut else "Live"
        for x in list(Devices):
            if Devices[x].DeviceID != _IEEE:
                continue
            if Devices[x].TimedOut:
                if MarkTimedOut:
                    continue
                timeout_widget_api(self, Devices, _IEEE, x, 0)
                self.log.logging( "Widget", "Debug", "reset timedOutDevice unit %s nwkid: %s " % (
                    Devices[x].Name, NwkId), NwkId, )

            elif MarkTimedOut:
                timeout_widget_api(self, Devices, _IEEE, x, 1)
                self.log.logging( "Widget", "Debug", "timedOutDevice unit %s nwkid: %s " % (
                    Devices[x].Name, NwkId), NwkId, )


def lastSeenUpdate(self, Devices, Unit=None, NwkId=None):

    # Purpose is here just to touch the device and update the Last Seen
    # It might required to call Touch everytime we receive a message from the device and not only when update is requested.

    if Unit:
        # self.log.logging( "Widget", "Debug2", "Touch unit %s" %( Devices[Unit].Name ))
        if not is_domoticz_touch(self):
            self.log.logging( "Widget", "Log", "Not the good Domoticz level for lastSeenUpdate %s %s %s" % (
                self.VersionNewFashion, self.DomoticzMajor, self.DomoticzMinor), NwkId, )
            return
        # Extract NwkId from Device Unit
        IEEE = Devices[Unit].DeviceID
        if Devices[Unit].TimedOut:
            timedOutDevice(self, Devices, Unit=Unit, MarkTimedOut=0)
        else:
            device_touch_api( self, Devices, IEEE, Unit)
        if NwkId is None and "IEEE" in self.IEEE2NWK:
            NwkId = self.IEEE2NWK[IEEE]

    if NwkId:
        if NwkId not in self.ListOfDevices:
            return
        if "IEEE" not in self.ListOfDevices[NwkId]:
            return
        if "Stamp" not in self.ListOfDevices[NwkId]:
            self.ListOfDevices[NwkId]["Stamp"] = {"Time": {}, "MsgType": {}, "LastSeen": 0}
        if "LastSeen" not in self.ListOfDevices[NwkId]["Stamp"]:
            self.ListOfDevices[NwkId]["Stamp"]["LastSeen"] = 0
        if "ErrorManagement" in self.ListOfDevices[NwkId]:
            self.ListOfDevices[NwkId]["ErrorManagement"] = 0
        if "Health" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Health"] not in ( "Disabled", ):
            self.ListOfDevices[NwkId]["Health"] = "Live"

        self.ListOfDevices[NwkId]["Stamp"]["LastSeen"] = int(time.time())
        _IEEE = self.ListOfDevices[NwkId]["IEEE"]
        if not is_domoticz_touch(self):
            self.log.logging( "Widget", "Log", "Not the good Domoticz level for Touch %s %s %s" % (
                self.VersionNewFashion, self.DomoticzMajor, self.DomoticzMinor), NwkId, )
            return
        for x in list(Devices):
            if x in Devices and Devices[x].DeviceID == _IEEE:
                if Devices[x].TimedOut:
                    timedOutDevice(self, Devices, Unit=x, MarkTimedOut=0)
                else:
                    device_touch_api( self, Devices, _IEEE, x)


def GetType(self, Addr, Ep):
    Type = ""
    self.log.logging(
        "Widget",
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
            self.log.logging("Widget", "Debug", "Ep: %s found in DeviceConf" % Ep)
            if "Type" in self.DeviceConf[_Model]["Ep"][Ep]:
                self.log.logging("Widget", "Debug", " 'Type' entry found inf DeviceConf")
                if self.DeviceConf[_Model]["Ep"][Ep]["Type"] != "":
                    self.log.logging(
                        "Widget",
                        "Debug",
                        "GetType - Found Type in DeviceConf : %s" % self.DeviceConf[_Model]["Ep"][Ep]["Type"],
                        Addr,
                    )
                    Type = self.DeviceConf[_Model]["Ep"][Ep]["Type"]
                    Type = str(Type)
                else:
                    self.log.logging(
                        "Widget", "Debug" "GetType - Found EpEmpty Type in DeviceConf for %s/%s" % (Addr, Ep), Addr
                    )
            else:
                self.log.logging(
                    "Widget", "Debug" "GetType - EpType not found in DeviceConf for %s/%s" % (Addr, Ep), Addr
                )
        else:
            Type = self.DeviceConf[_Model]["Type"]
            self.log.logging(
                "Widget", "Debug", "GetType - Found Type in DeviceConf for %s/%s: %s " % (Addr, Ep, Type), Addr
            )
    else:
        self.log.logging(
            "Widget",
            "Debug",
            "GetType - Model:  >%s< not found with Ep: %s in DeviceConf. Continue with ClusterSearch"
            % (self.ListOfDevices[Addr]["Model"], Ep),
            Addr,
        )
        self.log.logging("Widget", "Debug", "        - List of Entries: %s" % str(self.DeviceConf.keys()), Addr)
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
                self.log.logging("Widget", "Debug", "GetType - Found Livolo based on Manufacturer", Addr)
                return "LivoloSWL/LivoloSWR"

        # Finaly Chec on Cluster
        for cluster in self.ListOfDevices[Addr]["Ep"][Ep]:
            if cluster in ("Type", "ClusterType", "ColorMode"):
                continue

            self.log.logging("Widget", "Debug", "GetType - check Type for Cluster : " + str(cluster))

            if Type != "" and Type[:1] != "/":
                Type += "/"

            Type += TypeFromCluster(self, cluster, create_=True, ModelName=_Model)
            self.log.logging("Widget", "Debug", "GetType - Type will be set to : " + str(Type))

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

        self.log.logging("Widget", "Debug", "GetType - ClusterSearch return : %s" % Type, Addr)

    self.log.logging("Widget", "Debug", "GetType returning: %s" % Type, Addr)

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
    "PWFactor": "PWFactor"
}

def TypeFromCluster(self, cluster, create_=False, ProfileID_="", ZDeviceID_="", ModelName=""):

    self.log.logging(
        "Widget",
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


def remove_bad_cluster_type_entry(self, NwkId, Ep, clusterID, WidgetId ):
    
    if NwkId not in self.ListOfDevices:
        return
    if "Ep" not in self.ListOfDevices[ NwkId ]:
        return
    if (
        Ep in self.ListOfDevices[NwkId]["Ep"] 
        and "ClusterType" in self.ListOfDevices[NwkId]["Ep"][Ep] 
        and WidgetId in self.ListOfDevices[NwkId]["Ep"][Ep]["ClusterType"]
    ):
        del self.ListOfDevices[ NwkId ][ "Ep"][ Ep ][ "ClusterType" ][ WidgetId ]
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