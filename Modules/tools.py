#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module : z_tools.py


    Description: Zigate toolbox
"""
import binascii
import time
import datetime
import struct
import json

import Domoticz

from Classes.AdminWidgets import AdminWidgets
from Modules.database import WriteDeviceList


def is_hex(s):

    hex_digits = set("0123456789abcdefABCDEF")
    return all(char in hex_digits for char in s)


def returnlen(taille, value):
    while len(value) < taille:
        value = "0" + value
    return str(value)


def Hex_Format(taille, value):
    value = hex(int(value))[2:]
    if len(value) > taille:
        return "f" * taille
    while len(value) < taille:
        value = "0" + value
    return str(value)


def voltage2batteryP(voltage, volt_max, volt_min):

    if voltage > volt_max:
        ValueBattery = 100

    elif voltage < volt_min:
        ValueBattery = 0

    else:
        ValueBattery = 100 - round(((volt_max - (voltage)) / (volt_max - volt_min)) * 100)

    return round(ValueBattery)


def IEEEExist(self, IEEE):
    # check in ListOfDevices for an existing IEEE
    return IEEE != "" and IEEE in self.IEEE2NWK


def NwkIdExist(self, Nwkid):
    return Nwkid in self.ListOfDevices


def getSaddrfromIEEE(self, IEEE):
    # Return Short Address if IEEE found.

    if IEEE != "":
        for sAddr in list(self.ListOfDevices.keys()):
            if self.ListOfDevices[sAddr]["IEEE"] == IEEE:
                return sAddr
    return ""


def getListOfEpForCluster(self, NwkId, SearchCluster):
    """
    NwkId: Device
    Cluster: Cluster for which we are looking for Ep

    return List of Ep where Cluster is found and at least ClusterType is not empty. (If ClusterType is empty, this
    indicate that there is no Widget associated and all informations in Ep are not used)
    In case ClusterType exists and not empty at Global Level, then just return the list of Ep for which Cluster is found
    """

    EpList = []
    if NwkId not in self.ListOfDevices:
        return EpList

    oldFashion = (
        "ClusterType" in self.ListOfDevices[NwkId]
        and self.ListOfDevices[NwkId]["ClusterType"] != {}
        and self.ListOfDevices[NwkId]["ClusterType"] != ""
    )
    for Ep in list(self.ListOfDevices[NwkId]["Ep"].keys()):
        if SearchCluster not in self.ListOfDevices[NwkId]["Ep"][Ep]:
            # Domoticz.Log("---- Cluster %s on %s" %( SearchCluster, str(self.ListOfDevices[NwkId]['Ep'][Ep] ) ))
            continue

        if oldFashion:
            EpList.append(Ep)
        else:
            if (
                "ClusterType" in self.ListOfDevices[NwkId]["Ep"][Ep]
                and self.ListOfDevices[NwkId]["Ep"][Ep]["ClusterType"] != {}
                and self.ListOfDevices[NwkId]["Ep"][Ep]["ClusterType"] != ""
            ):
                EpList.append(Ep)
            # else:
            #    Domoticz.Log("------------> Skiping Cluster: %s Clustertype not found in %s" %(  SearchCluster, str(self.ListOfDevices[ NwkId]['Ep'][Ep]) ) )

    # Domoticz.Log("----------> NwkId: %s Ep: %s Cluster: %s oldFashion: %s EpList: %s" %( NwkId, Ep, SearchCluster, oldFashion, EpList))
    return EpList


def getEPforClusterType(self, NWKID, ClusterType):

    EPlist = []
    for EPout in list(self.ListOfDevices[NWKID]["Ep"].keys()):
        if "ClusterType" in self.ListOfDevices[NWKID]["Ep"][EPout]:
            for key in self.ListOfDevices[NWKID]["Ep"][EPout]["ClusterType"]:
                if self.ListOfDevices[NWKID]["Ep"][EPout]["ClusterType"][key].find(ClusterType) >= 0:
                    EPlist.append(str(EPout))
                    break
    return EPlist


def getClusterListforEP(self, NWKID, Ep):

    ClusterList = [
        cluster
        for cluster in ["fc00", "0500", "0502", "0406", "0400", "0402", "0001"]
        if cluster in self.ListOfDevices[NWKID]["Ep"][Ep]
    ]

    if self.ListOfDevices[NWKID]["Ep"][Ep]:
        for cluster in list(self.ListOfDevices[NWKID]["Ep"][Ep].keys()):
            if cluster not in ("ClusterType", "Type", "ColorMode") and cluster not in ClusterList:
                ClusterList.append(cluster)
    return ClusterList


def getEpForCluster(self, nwkid, ClusterId):
    """
    Return the Ep or a list of Ep associated to the ClusterId
    If not found return Ep: 01
    """

    EPout = [
        tmpEp
        for tmpEp in list(self.ListOfDevices[nwkid]["Ep"].keys())
        if ClusterId in self.ListOfDevices[nwkid]["Ep"][tmpEp]
    ]

    if not EPout:
        return EPout

    if len(self.ListOfDevices[nwkid]["Ep"]) == 1:
        return [self.ListOfDevices[nwkid]["Ep"].keys()]

    return EPout


def DeviceExist(self, Devices, lookupNwkId, lookupIEEE=""):
    """
    DeviceExist
        check if the Device is existing in the ListOfDevice.
        lookupNwkId Mandatory field
        lookupIEEE Optional
    Return
        True if object found
        False if not found
    """
    ieee_from_nwkid = None

    # Validity check
    if lookupNwkId == "":
        return False

    found = False
    # 1- Check if found in ListOfDevices
    #   Verify that Status is not 'UNKNOWN' otherwise condider not found
    if lookupNwkId in self.ListOfDevices and "Status" in self.ListOfDevices[lookupNwkId]:
        if "IEEE" in self.ListOfDevices[lookupNwkId]:
            ieee_from_nwkid = self.ListOfDevices[lookupNwkId]["IEEE"]

        # Found, let's check the Status
        if self.ListOfDevices[lookupNwkId]["Status"] != "UNKNOWN":
            found = True

    # 2- We might have found it with the lookupNwkId
    # If we didnt find it, we should check if this is not a new ShortId
    if lookupIEEE:
        if lookupIEEE not in self.IEEE2NWK:
            if not found:
                return found

            # We are in situation where we found the device in ListOfDevices but not in IEEE2NWK.
            # this is not expected

            Domoticz.Error(
                "DeviceExist - Found %s some inconsistency Inputs: %s %s instead of %s"
                % (found, lookupNwkId, lookupIEEE, ieee_from_nwkid)
            )
            return found

        # We found IEEE, let's get the Short Address
        exitsingNwkId = self.IEEE2NWK[lookupIEEE]
        if exitsingNwkId == lookupNwkId:
            # Everything fine, we have found it
            # and this is the same ShortId as the one existing
            return True

        if exitsingNwkId not in self.ListOfDevices:
            # Should not happen
            # We have an entry in IEEE2NWK, but no corresponding
            # in ListOfDevices !!
            # Let's cleanup
            del self.IEEE2NWK[lookupIEEE]
            return False

        #   if 'Status' not in self.ListOfDevices[ exitsingNwkId ]:
        #       # Should not happen
        #       # That seems not correct
        #       # We might have to do some cleanup here !
        #       # Cleanup
        #       # Delete the entry in IEEE2NWK as it will be recreated in Decode004d
        #       del self.IEEE2NWK[ lookupIEEE ]
        #       # Delete the all Data Structure
        #       del self.ListOfDevices[ exitsingNwkId ]
        #       return False

        if self.ListOfDevices[exitsingNwkId]["Status"] in ("004d", "0045", "0043", "8045", "8043", "UNKNOW"):
            # We are in the discovery/provisioning process,
            # and the device got a new Short Id
            # we need to restart from the begiging and remove all existing datastructutre.
            # In case we receive asynchronously messages (which should be possible), they must be
            # droped in the corresponding Decodexxx function
            # Delete the entry in IEEE2NWK as it will be recreated in Decode004d
            del self.IEEE2NWK[lookupIEEE]
            # Delete the all Data Structure
            del self.ListOfDevices[exitsingNwkId]
            Domoticz.Status(
                "DeviceExist - Device %s changed its ShortId: from %s to %s during provisioning. Restarting !"
                % (lookupIEEE, exitsingNwkId, lookupNwkId)
            )
            return False

        # At that stage, we have found an entry for the IEEE, but doesn't match
        # the coming Short Address lookupNwkId.
        # Most likely , device has changed its NwkId
        found = True
        reconnectNWkDevice(self, lookupNwkId, lookupIEEE, exitsingNwkId)

        # Let's send a Notfification
        devName = ""
        for x in list(Devices.keys()):
            if Devices[x].DeviceID == lookupIEEE:
                devName = Devices[x].Name
                break
        self.adminWidgets.updateNotificationWidget(
            Devices, "Reconnect %s with %s/%s" % (devName, lookupNwkId, lookupIEEE)
        )

    return found


def reconnectNWkDevice(self, new_NwkId, IEEE, old_NwkId):
    # We got a new Network ID for an existing IEEE. So just re-connect.
    # - mapping the information to the new new_NwkId
    if old_NwkId not in self.ListOfDevices:
        return
    if old_NwkId == new_NwkId:
        return

    self.ListOfDevices[new_NwkId] = dict(self.ListOfDevices[old_NwkId])
    self.IEEE2NWK[IEEE] = new_NwkId

    if "ZDeviceName" in self.ListOfDevices[new_NwkId]:
        devName = self.ListOfDevices[new_NwkId]["ZDeviceName"]

    # MostLikely exitsingKey(the old NetworkID) is not needed any more
    if removeNwkInList(self, old_NwkId) is None:
        Domoticz.Error(
            "reconnectNWkDevice - something went wrong in the reconnect New NwkId: %s Old NwkId: %s IEEE: %s"
            % (new_NwkId, old_NwkId, IEEE)
        )

    if self.groupmgt:
        # We should check if this belongs to a group
        self.groupmgt.update_due_to_nwk_id_change(old_NwkId, new_NwkId)

    if self.ListOfDevices[new_NwkId]["Status"] in ("Left", "Leave"):
        Domoticz.Log(
            "reconnectNWkDevice - Update Status from %s to 'inDB' for NetworkID : %s"
            % (self.ListOfDevices[new_NwkId]["Status"], new_NwkId)
        )
        self.ListOfDevices[new_NwkId]["Status"] = "inDB"
        self.ListOfDevices[new_NwkId]["Heartbeat"] = "0"

    # We will also reset ReadAttributes
    if self.pluginconf.pluginConf["enableReadAttributes"]:
        if "ReadAttributes" in self.ListOfDevices[new_NwkId]:
            del self.ListOfDevices[new_NwkId]["ReadAttributes"]
        if "ConfigureReporting" in self.ListOfDevices[new_NwkId]:
            del self.ListOfDevices[new_NwkId]["ConfigureReporting"]
        self.ListOfDevices[new_NwkId]["Heartbeat"] = "0"

    WriteDeviceList(self, 0)
    Domoticz.Status("NetworkID: %s is replacing %s for object: %s" % (new_NwkId, old_NwkId, IEEE))
    return


def removeNwkInList(self, NWKID):
    # Sanity check
    safe = None
    if "IEEE" in self.ListOfDevices[NWKID]:
        for x in list(self.ListOfDevices.keys()):
            if x == NWKID:
                continue
            if "IEEE" in self.ListOfDevices[x] and self.ListOfDevices[x]["IEEE"] == self.ListOfDevices[NWKID]["IEEE"]:
                safe = x
                break

    if safe:
        del self.ListOfDevices[NWKID]
        Domoticz.Status("self.ListOfDevices[%s] removed! substitued by self.ListOfDevices[%s]" % (NWKID, safe))
    else:
        Domoticz.Error("self.ListOfDevices[%s] removed! but no substitution !!!" % (NWKID))

    return safe


def removeDeviceInList(self, Devices, IEEE, Unit):
    # Most likely call when a Device is removed from Domoticz
    # This is a tricky one, as you might have several Domoticz devices attached to this IoT and so you must remove only the corredpoing part.
    # Must seach in the NwkID dictionnary and remove only the corresponding device entry in the ClusterType.
    # In case there is no more ClusterType , then the full entry can be removed

    if IEEE not in self.IEEE2NWK:
        return

    key = self.IEEE2NWK[IEEE]
    ID = Devices[Unit].ID

    Domoticz.Log("removeDeviceInList - request to remove Device: %s with IEEE: %s " % (key, IEEE))

    if (
        "ClusterTye" in self.ListOfDevices[key]
    ):  # We are in the old fasho V. 3.0.x Where ClusterType has been migrated from Domoticz
        if str(ID) in self.ListOfDevices[key]["ClusterType"]:
            Domoticz.Log("removeDeviceInList - removing : %s in %s" % (ID, str(self.ListOfDevices[key]["ClusterType"])))
            del self.ListOfDevices[key]["ClusterType"][ID]  # Let's remove that entry
    else:
        for tmpEp in list(self.ListOfDevices[key]["Ep"].keys()):
            # Search this DeviceID in ClusterType
            if (
                "ClusterType" in self.ListOfDevices[key]["Ep"][tmpEp]
                and str(ID) in self.ListOfDevices[key]["Ep"][tmpEp]["ClusterType"]
            ):
                Domoticz.Log(
                    "removeDeviceInList - removing : %s with Ep: %s in - %s"
                    % (ID, tmpEp, str(self.ListOfDevices[key]["Ep"][tmpEp]["ClusterType"]))
                )
                del self.ListOfDevices[key]["Ep"][tmpEp]["ClusterType"][str(ID)]

    # Finaly let's see if there is any Devices left in this .
    emptyCT = True
    if "ClusterType" in self.ListOfDevices[key]:  # Empty or Doesn't exist
        Domoticz.Log("removeDeviceInList - exitsing Global 'ClusterTpe'")
        if self.ListOfDevices[key]["ClusterType"] != {}:
            emptyCT = False
    for tmpEp in list(self.ListOfDevices[key]["Ep"].keys()):
        if "ClusterType" in self.ListOfDevices[key]["Ep"][tmpEp]:
            Domoticz.Log("removeDeviceInList - exitsing Ep 'ClusterTpe'")
            if self.ListOfDevices[key]["Ep"][tmpEp]["ClusterType"] != {}:
                emptyCT = False

    if emptyCT:
        del self.ListOfDevices[key]
        del self.IEEE2NWK[IEEE]

        self.adminWidgets.updateNotificationWidget(
            Devices, "Device fully removed %s with IEEE: %s" % (Devices[Unit].Name, IEEE)
        )
        Domoticz.Status("Device %s with IEEE: %s fully removed from the system." % (Devices[Unit].Name, IEEE))
        return True
    return False


def initDeviceInList(self, Nwkid):
    if Nwkid in self.ListOfDevices or Nwkid == "":
        return

    self.ListOfDevices[Nwkid] = {
        "Version": "3",
        "ZDeviceName": "",
        "Status": "004d",
        "SQN": "",
        "Ep": {},
        "Heartbeat": "0",
        "RIA": "0",
        "LQI": {},
        "Battery": {},
        "Model": "",
        "ForceAckCommands": [],
        "MacCapa": {},
        "IEEE": {},
        "Type": {},
        "ProfileID": {},
        "ZDeviceID": {},
        "App Version": "",
        "Attributes List": {},
        "DeviceType": "",
        "HW Version": "",
        "Last Cmds": [],
        "LogicalType": "",
        "Manufacturer": "",
        "Manufacturer Name": "",
        "NbEp": "",
        "PowerSource": "",
        "ReadAttributes": {},
        "ReceiveOnIdle": "",
        "Stack Version": "",
        "Stamp": {},
        "ZCL Version": "",
        "Health": "",
    }


def timeStamped(self, key, Type):
    if key not in self.ListOfDevices:
        return
    if "Stamp" not in self.ListOfDevices[key]:
        self.ListOfDevices[key]["Stamp"] = {"LasteSeen": {}, "Time": {}, "MsgType": {}}
    self.ListOfDevices[key]["Stamp"]["time"] = time.time()
    self.ListOfDevices[key]["Stamp"]["Time"] = datetime.datetime.fromtimestamp(time.time()).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    self.ListOfDevices[key]["Stamp"]["MsgType"] = "%4x" % (Type)


def get_and_inc_SQN(self, key):

    # Get the latest SQN from ListOfDevice and Increment by 1.
    # In case of overflow manage it

    if (
        (key not in self.ListOfDevices)
        or ("SQN" not in self.ListOfDevices[key])
        or (self.ListOfDevices[key]["SQN"] == {})
        or (self.ListOfDevices[key]["SQN"] == "")
    ):
        _new_sqn = 0x00
    else:
        _new_sqn = int(self.ListOfDevices[key]["SQN"], 16) + 1
        if _new_sqn > 0xFF:
            _new_sqn = 0x00

    # self.ListOfDevices[key]['SQN']= '%2x' %_new_sqn
    return "%02x" % _new_sqn


def updSQN(self, key, newSQN):

    if key not in self.ListOfDevices:
        return
    if newSQN == {}:
        return
    if newSQN is None:
        return

    # Domoticz.Log("-->SQN updated %s from %s to %s" %(key, self.ListOfDevices[key]['SQN'], newSQN))
    self.ListOfDevices[key]["SQN"] = newSQN
    return


def updLQI(self, key, LQI):

    if key not in self.ListOfDevices:
        return

    if "LQI" not in self.ListOfDevices[key]:
        self.ListOfDevices[key]["LQI"] = {}

    if LQI == "00":
        return

    if is_hex(LQI):  # Check if the LQI is Correct

        self.ListOfDevices[key]["LQI"] = int(LQI, 16)

        if "RollingLQI" not in self.ListOfDevices[key]:
            self.ListOfDevices[key]["RollingLQI"] = []

        if len(self.ListOfDevices[key]["RollingLQI"]) > 10:
            del self.ListOfDevices[key]["RollingLQI"][0]
        self.ListOfDevices[key]["RollingLQI"].append(int(LQI, 16))

    return


#### Those functions will be use with the new DeviceConf structutre
def getTypebyCluster(self, Cluster):
    clustersType = {
        "0405": "Humi",
        "0406": "Motion",
        "0400": "Lux",
        "0403": "Baro",
        "0402": "Temp",
        "0006": "Switch",
        "0500": "Door",
        "0012": "XCube",
        "000c": "XCube",
        "0008": "LvlControl",
        "0300": "ColorControl",
    }

    if Cluster == "" or Cluster is None:
        return ""

    if Cluster in clustersType:
        return clustersType[Cluster]

    return ""


def getListofClusterbyModel(self, Model, InOut):
    """
    Provide the list of clusters attached to Ep In
    """
    listofCluster = []
    if InOut == "" or InOut is None:
        return listofCluster
    if InOut not in ["Epin", "Epout"]:
        Domoticz.Error("getListofClusterbyModel - Argument error : " + Model + " " + InOut)
        return ""

    if Model in self.DeviceConf and InOut in self.DeviceConf[Model]:
        for ep in list(self.DeviceConf[Model][InOut].keys()):
            seen = ""
            for cluster in sorted(self.DeviceConf[Model][InOut][ep]):
                if cluster in ("ClusterType", "Type", "ColorMode") or cluster == seen:
                    continue
                listofCluster.append(cluster)
                seen = cluster
    return listofCluster


def getListofInClusterbyModel(self, Model):
    return getListofClusterbyModel(self, Model, "Epin")


def getListofOutClusterbyModel(self, Model):
    return getListofClusterbyModel(self, Model, "Epout")


def getListofTypebyModel(self, Model):
    """
    Provide a list of Tuple ( Ep, Type ) for a given Model name if found. Else return an empty list
        Type is provided as a list of Type already.
    """
    EpType = []
    if Model in self.DeviceConf:
        for ep in list(self.DeviceConf[Model]["Epin"].keys()):
            if "Type" in self.DeviceConf[Model]["Epin"][ep]:
                EpinType = (ep, getListofType(self.DeviceConf[Model]["Epin"][ep]["Type"]))
                EpType.append(EpinType)
    return EpType


def getModelbyZDeviceIDProfileID(self, ZDeviceID, ProfileID):
    """
    Provide a Model for a given ZdeviceID, ProfileID
    """
    for model in list(self.DeviceConf.keys()):
        if self.DeviceConf[model]["ProfileID"] == ProfileID and self.DeviceConf[model]["ZDeviceID"] == ZDeviceID:
            return model
    return ""


def getListofType(self, Type):
    """
    For a given DeviceConf Type "Plug/Power/Meters" return a list of Type [ 'Plug', 'Power', 'Meters' ]
    """

    if Type == "" or Type is None:
        return ""
    retList = []
    retList = Type.split("/")
    return retList


def hex_to_rgb(value):
    """Return (red, green, blue) for the color given as #rrggbb."""
    value = value.lstrip("#")
    lv = len(value)
    return tuple(int(value[i : i + lv // 3], 16) for i in range(0, lv, lv // 3))


def hex_to_xy(h):
    """ convert hex color to xy tuple """
    return rgb_to_xy(hex_to_rgb(h))


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % rgb


def rgb_to_xy(rgb):
    """ convert rgb tuple to xy tuple """
    red, green, blue = rgb
    r = ((red + 0.055) / (1.0 + 0.055)) ** 2.4 if (red > 0.04045) else (red / 12.92)
    g = ((green + 0.055) / (1.0 + 0.055)) ** 2.4 if (green > 0.04045) else (green / 12.92)
    b = ((blue + 0.055) / (1.0 + 0.055)) ** 2.4 if (blue > 0.04045) else (blue / 12.92)
    X = r * 0.664511 + g * 0.154324 + b * 0.162028
    Y = r * 0.283881 + g * 0.668433 + b * 0.047685
    Z = r * 0.000088 + g * 0.072310 + b * 0.986039
    cx = 0
    cy = 0
    if (X + Y + Z) != 0:
        cx = X / (X + Y + Z)
        cy = Y / (X + Y + Z)
    return (cx, cy)


def xy_to_rgb(x, y, brightness=1):

    x = 0.313
    y = 0.329

    x = float(x)
    y = float(y)
    z = 1.0 - x - y

    Y = brightness
    X = (Y / y) * x
    Z = (Y / y) * z

    r = X * 1.656492 - Y * 0.354851 - Z * 0.255038
    g = -X * 0.707196 + Y * 1.655397 + Z * 0.036152
    b = X * 0.051713 - Y * 0.121364 + Z * 1.011530

    r = 12.92 * r if r <= 0.0031308 else (1.0 + 0.055) * pow(r, (1.0 / 2.4)) - 0.055
    g = 12.92 * g if g <= 0.0031308 else (1.0 + 0.055) * pow(g, (1.0 / 2.4)) - 0.055
    b = 12.92 * b if b <= 0.0031308 else (1.0 + 0.055) * pow(b, (1.0 / 2.4)) - 0.055

    return {"r": round(r * 255, 3), "g": round(g * 255, 3), "b": round(b * 255, 3)}


def rgb_to_hsl(rgb):
    """ convert rgb tuple to hls tuple """
    r, g, b = rgb
    r = float(r / 255)
    g = float(g / 255)
    b = float(b / 255)
    high = max(r, g, b)
    low = min(r, g, b)
    h, s, l = ((high + low) / 2,) * 3

    if high == low:
        h = 0.0
        s = 0.0
    else:
        d = high - low
        s = d / (2 - high - low) if l > 0.5 else d / (high + low)
        h = {
            r: (g - b) / d + (6 if g < b else 0),
            g: (b - r) / d + 2,
            b: (r - g) / d + 4,
        }[high]
        h /= 6

    return h, s, l


def decodeMacCapa(inMacCapa):

    maccap = int(inMacCapa, 16)
    alternatePANCOORDInator = maccap & 0b00000001
    deviceType = (maccap & 0b00000010) >> 1
    powerSource = (maccap & 0b00000100) >> 2
    receiveOnIddle = (maccap & 0b00001000) >> 3
    securityCap = (maccap & 0b01000000) >> 6
    allocateAddress = (maccap & 0b10000000) >> 7

    MacCapa = []
    if alternatePANCOORDInator:
        MacCapa.append("Able to act Coordinator")
    if deviceType:
        MacCapa.append("Full-Function Device")
    else:
        MacCapa.append("Reduced-Function Device")
    if powerSource:
        MacCapa.append("Main Powered")
    if receiveOnIddle:
        MacCapa.append("Receiver during Idle")
    if securityCap:
        MacCapa.append("High security")
    else:
        MacCapa.append("Standard security")
    if allocateAddress:
        MacCapa.append("NwkAddr should be allocated")
    else:
        MacCapa.append("NwkAddr need to be allocated")
    return MacCapa


def ReArrangeMacCapaBasedOnModel(self, nwkid, inMacCapa):
    """
    Function to check if the MacCapa should not be updated based on Model.
    As they are some bogous Devices which tell they are Main Powered and they are not !

    Return the old or the revised MacCapa and eventually fix some Attributes
    """

    if nwkid not in self.ListOfDevices:
        Domoticz.Error("%s not known !!!" % nwkid)
        return inMacCapa

    if "Model" not in self.ListOfDevices[nwkid]:
        return inMacCapa

    # Convert battery annouced devices to main powered / Make sure that you do the reverse n NetworkMap
    if self.ListOfDevices[nwkid]["Model"] in ("TI0001", "TS0011", "TS0013", "TS0601-switch", "TS0601-2Gangs-switch"):
        # Livol Switch, must be converted to Main Powered
        # Patch some status as Device Annouced doesn't provide much info
        self.ListOfDevices[nwkid]["LogicalType"] = "Router"
        self.ListOfDevices[nwkid]["DevideType"] = "FFD"
        self.ListOfDevices[nwkid]["MacCapa"] = "8e"
        self.ListOfDevices[nwkid]["PowerSource"] = "Main"
        return "8e"

    # Convert Main Powered device to Battery
    if self.ListOfDevices[nwkid]["Model"] in (
        "lumi.remote.b686opcn01",
        "lumi.remote.b486opcn01",
        "lumi.remote.b286opcn01",
        "lumi.remote.b686opcn01-bulb",
        "lumi.remote.b486opcn01-bulb",
        "lumi.remote.b286opcn01-bulb",
        "lumi.remote.b686opcn01",
    ):
        # Aqara Opple Switch, must be converted to Battery Devices
        self.ListOfDevices[nwkid]["MacCapa"] = "80"
        self.ListOfDevices[nwkid]["PowerSource"] = "Battery"
        if "Capability" in self.ListOfDevices[nwkid] and "Main Powered" in self.ListOfDevices[nwkid]["Capability"]:
            self.ListOfDevices[nwkid]["Capability"].remove("Main Powered")
        return "80"

    if self.ListOfDevices[nwkid]["MacCapa"] == "80" and (
        self.ListOfDevices[nwkid]["PowerSource"] == "" or "PowerSource" not in self.ListOfDevices[nwkid]
    ):
        # This is needed for VOC_Sensor from Nextrum for instance. (Looks like the device do not provide Node Descriptor )
        self.ListOfDevices[nwkid]["PowerSource"] = "Battery"

    return inMacCapa


def mainPoweredDevice(self, nwkid):
    """
    return True is it is Main Powered device
    return False if it is not Main Powered
    """

    if nwkid not in self.ListOfDevices:
        Domoticz.Log("mainPoweredDevice - Unknown Device: %s" % nwkid)
        return False

    mainPower = False
    if "MacCapa" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["MacCapa"] != {}:
        mainPower = ("8e" == self.ListOfDevices[nwkid]["MacCapa"]) or ("84" == self.ListOfDevices[nwkid]["MacCapa"])

    if not mainPower and "PowerSource" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["PowerSource"] != {}:
        mainPower = "Main" == self.ListOfDevices[nwkid]["PowerSource"]

    # We need to take in consideration that Livolo is reporting a MacCapa of 0x80
    # That Aqara Opple are reporting MacCap 0x84 while they are Battery devices
    if "Model" in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]["Model"] in (
            "lumi.remote.b686opcn01",
            "lumi.remote.b486opcn01",
            "lumi.remote.b286opcn01",
            "lumi.remote.b686opcn01-bulb",
            "lumi.remote.b486opcn01-bulb",
            "lumi.remote.b286opcn01-bulb",
        ):
            mainPower = False

        if self.ListOfDevices[nwkid]["Model"] in ("TI0001", "TS0011", "TS0601-switch", "TS0601-2Gangs-switch"):
            mainPower = True

    return mainPower


def loggingMessages(self, msgtype, sAddr=None, ieee=None, LQI=None, SQN=None):

    if not self.pluginconf.pluginConf["logFORMAT"]:
        return
    if sAddr == ieee == None:
        return
    _debugMatchId = self.pluginconf.pluginConf["debugMatchId"].lower()
    if sAddr is None:
        # Get sAddr from IEEE
        sAddr = ""
        if ieee in self.IEEE2NWK:
            sAddr = self.IEEE2NWK[ieee]
    if ieee is None:
        # Get ieee from sAddr
        ieee = ""
        if sAddr in self.ListOfDevices:
            ieee = self.ListOfDevices[sAddr]["IEEE"]
    if _debugMatchId not in ["ffff", sAddr]:
        # If not matching _debugMatchId
        return

    zdevname = ""
    if sAddr in self.ListOfDevices and "ZDeviceName" in self.ListOfDevices[sAddr]:
        zdevname = self.ListOfDevices[sAddr]["ZDeviceName"]

    Domoticz.Log(
        "Device activity for | %4s | %14s | %4s | %16s | %3s | 0x%02s |"
        % (msgtype, zdevname, sAddr, ieee, int(LQI, 16), SQN)
    )


def lookupForIEEE(self, nwkid, reconnect=False):
    # """
    # Purpose of this function is to search a Nwkid in the Neighbours table and find an IEEE
    # """

    # Domoticz.Log("lookupForIEEE - looking for %s in Neighbourgs table" %nwkid)
    for key in list(self.ListOfDevices.keys()):
        if "Neighbours" not in self.ListOfDevices[key]:
            continue
        if len(self.ListOfDevices[key]["Neighbours"]) == 0:
            continue
        # We are interested only on the last one
        lastScan = self.ListOfDevices[key]["Neighbours"][-1]
        for item in lastScan["Devices"]:
            if nwkid not in item:
                continue
            if "_IEEE" not in item[nwkid]:
                continue
            ieee = item[nwkid]["_IEEE"]
            old_NwkId = "none"
            if ieee not in self.IEEE2NWK:
                continue

            old_NwkId = self.IEEE2NWK[ieee]
            if old_NwkId not in self.ListOfDevices:
                Domoticz.Log(
                    "lookupForIEEE found an inconsitency %s nt existing but pointed by %s, cleanup" % (old_NwkId, ieee)
                )
                del self.IEEE2NWK[ieee]
                continue

            if reconnect:
                reconnectNWkDevice(self, nwkid, ieee, old_NwkId)
            Domoticz.Log(
                "lookupForIEEE found IEEE %s for %s in %s known as %s  Neighbourg table" % (ieee, nwkid, old_NwkId, key)
            )
            return ieee
    return None


def lookupForParentDevice(self, nwkid=None, ieee=None):

    """
    Purpose is to find a router to which this device is connected to.
    the IEEE will be returned if found otherwise None
    """

    if nwkid is None and ieee is None:
        return None

    # Got Short Address in Input
    if nwkid and ieee is None:
        if nwkid not in self.ListOfDevices:
            return
        if "IEEE" in self.ListOfDevices[nwkid]:
            ieee = self.ListOfDevices[nwkid]["IEEE"]

    # Got IEEE in Input
    if ieee and nwkid is None:
        if ieee not in self.IEEE2NWK:
            return
        nwkid = self.IEEE2NWK[nwkid]

    if mainPoweredDevice(self, nwkid):
        return ieee

    for PotentialRouter in list(self.ListOfDevices.keys()):
        if "Neighbours" not in self.ListOfDevices[PotentialRouter]:
            continue
        if len(self.ListOfDevices[PotentialRouter]["Neighbours"]) == 0:
            continue
        # We are interested only on the last one
        lastScan = self.ListOfDevices[PotentialRouter]["Neighbours"][-1]

        for item in lastScan["Devices"]:
            if nwkid not in item:
                continue
            # found and PotentialRouter is one router
            if "IEEE" not in self.ListOfDevices[PotentialRouter]:
                # This is problematic, let's try an other candidate
                continue

            return self.ListOfDevices[PotentialRouter]["IEEE"]

    # Nothing found
    return None


def checkAttribute(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID):

    if MsgClusterId not in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]:
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId] = {}

    if not isinstance(self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId], dict):
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId] = {}

    if MsgAttrID not in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId]:
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId][MsgAttrID] = {}


def checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, Value):

    checkAttribute(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID)

    self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId][MsgAttrID] = Value


def getAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID):

    if MsgSrcAddr not in self.ListOfDevices:
        return None
    if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]["Ep"]:
        return None
    if MsgClusterId not in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]:
        return None
    if not isinstance(self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId], dict):
        return None
    if MsgAttrID not in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId]:
        return None
    return self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId][MsgAttrID]


# Function to manage 0x8002 payloads
def retreive_cmd_payload_from_8002(Payload):

    ManufacturerCode = None
    fcf = Payload[0:2]

    GlobalCommand = is_golbalcommand(fcf)
    if GlobalCommand is None:
        Domoticz.Error("Strange payload: %s" % Payload)
        return (None, None, None, None, None)

    if is_manufspecific_8002_payload(fcf):
        ManufacturerCode = Payload[2:6]
        Sqn = Payload[6:8]
        Command = Payload[8:10]
        Data = Payload[10:]
    else:
        Sqn = Payload[2:4]
        Command = Payload[4:6]
        Data = Payload[6:]

    # Domoticz.Log("retreive_cmd_payload_from_8002 ======> Payload: %s " %Data)
    return (GlobalCommand, Sqn, ManufacturerCode, Command, Data)


def is_golbalcommand(fcf):
    if not is_hex(fcf) or len(fcf) != 2:
        return None
    return (int(fcf, 16) & 0b00000011) == 0


def is_manufspecific_8002_payload(fcf):
    return ((int(fcf, 16) & 0b00000100) >> 2) == 1


def build_fcf(frame_type, manuf_spec, direction, disabled_default):
    fcf = 0b00000000 | int(frame_type, 16)
    if int(manuf_spec, 16):
        fcf |= 0b100
    if int(direction, 16):
        fcf |= 0b1000
    if int(disabled_default, 16):
        fcf |= 0b10000
    # Domoticz.Log("build_fcf FrameType: %s Manuf: %s Direction: %s DisabledDefault: %s ==> 0x%02x/%s" %(
    #    frame_type, manuf_spec, direction, disabled_default, fcf, bin(fcf)))
    return "%02x" % fcf


# Functions to manage Device Attributes infos ( ConfigureReporting)
def check_datastruct(self, DeviceAttribute, key, endpoint, clusterId):
    # Make sure all tree exists
    if key not in self.ListOfDevices:
        return None
    if DeviceAttribute not in self.ListOfDevices[key]:
        self.ListOfDevices[key][DeviceAttribute] = {}
    if "Ep" not in self.ListOfDevices[key][DeviceAttribute]:
        self.ListOfDevices[key][DeviceAttribute]["Ep"] = {}
    if endpoint not in self.ListOfDevices[key][DeviceAttribute]["Ep"]:
        self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint] = {}
    if clusterId not in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint]:
        self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId] = {}
    if not isinstance(self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId], dict):
        self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId] = {}
    if "TimeStamp" not in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]:
        self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["TimeStamp"] = 0
    if "iSQN" not in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]:
        self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"] = {}
    if "Attributes" not in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]:
        self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["Attributes"] = {}
    if "ZigateRequest" not in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]:
        self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"] = {}
    return True


def is_time_to_perform_work(self, DeviceAttribute, key, endpoint, clusterId, now, timeoutperiod):
    # Based on a timeout period return True or False.
    if key not in self.ListOfDevices:
        Domoticz.Log("Unknown Key: %s" % key)
        return False
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        Domoticz.Log("check_datastruct responded to None Key: %s !!" % key)
        return False
    return now >= (self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["TimeStamp"] + timeoutperiod)


def set_timestamp_datastruct(self, DeviceAttribute, key, endpoint, clusterId, now):
    if key not in self.ListOfDevices:
        return
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["TimeStamp"] = now


def get_list_isqn_attr_datastruct(self, DeviceAttribute, key, endpoint, clusterId):
    if key not in self.ListOfDevices:
        return []
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return []
    return [x for x in list(self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"].keys())]


def set_request_datastruct(
    self,
    DeviceAttribute,
    key,
    endpoint,
    clusterId,
    AttributeId,
    datatype,
    EPin,
    EPout,
    manuf_id,
    manuf_spec,
    data,
    ackIsDisabled,
    phase,
):
    if key not in self.ListOfDevices:
        return
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return
    if AttributeId not in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"]:
        self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId] = {}

    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]["Status"] = phase
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
        "DataType"
    ] = datatype
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]["EPin"] = EPin
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]["EPout"] = EPout
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
        "manuf_id"
    ] = manuf_id
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
        "manuf_spec"
    ] = manuf_spec
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]["data"] = data
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
        "ackIsDisabled"
    ] = ackIsDisabled


def get_request_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId):
    # Return all arguments to make the WriteAttribute
    if key not in self.ListOfDevices:
        return None
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return None
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"]:
        return (
            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
                "DataType"
            ],
            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]["EPin"],
            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]["EPout"],
            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
                "manuf_id"
            ],
            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
                "manuf_spec"
            ],
            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]["data"],
            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
                "ackIsDisabled"
            ],
        )
    return None


def set_request_phase_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId, phase):
    if key not in self.ListOfDevices:
        return
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"]:
        self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId][
            "Status"
        ] = phase


def get_list_waiting_request_datastruct(self, DeviceAttribute, key, endpoint, clusterId):
    # Return a list of Attributes which are waiting to be writeAttrbutes
    if key not in self.ListOfDevices:
        return []
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return []
    return [
        x
        for x in list(self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"].keys())
        if self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][x]["Status"]
        == "waiting"
    ]


def set_isqn_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId, isqn):
    if key not in self.ListOfDevices:
        return
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return
    if isqn is not None:
        self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"][AttributeId] = isqn


def get_isqn_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId):
    if key not in self.ListOfDevices:
        return None
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return None
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"]:
        return self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"][AttributeId]
    return None


def set_status_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId, status):
    if key not in self.ListOfDevices:
        return
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return
    self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["Attributes"][AttributeId] = status
    clean_old_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId)


def get_status_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId):
    if key not in self.ListOfDevices:
        return None
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return None
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["Attributes"]:
        return self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["Attributes"][AttributeId]
    return None


def is_attr_unvalid_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId):
    lastStatus = get_status_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId)
    if lastStatus is None:
        return False
    if lastStatus in ("86", "8c"):
        return True
    return lastStatus != "00"


def reset_attr_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId):
    if key not in self.ListOfDevices:
        return
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["Attributes"]:
        del self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["Attributes"][AttributeId]
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"]:
        del self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"][AttributeId]
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"]:
        del self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["ZigateRequest"][AttributeId]


def reset_cluster_datastruct(self, DeviceAttribute, key, endpoint, clusterId):
    if key not in self.ListOfDevices:
        return
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return
    if clusterId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint]:
        del self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]


def reset_datastruct(self, DeviceAttribute, key):
    if key not in self.ListOfDevices:
        return
    if DeviceAttribute in self.ListOfDevices[key]:
        del self.ListOfDevices[key][DeviceAttribute]
    self.ListOfDevices[key][DeviceAttribute] = {}


def clean_old_datastruct(self, DeviceAttribute, key, endpoint, clusterId, AttributeId):
    if key not in self.ListOfDevices:
        return False
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return False
    if AttributeId in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]:
        del self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId][AttributeId]
    if "TimeStamp" in self.ListOfDevices[key][DeviceAttribute]:
        del self.ListOfDevices[key][DeviceAttribute]["TimeStamp"]


def is_ack_tobe_disabled(self, key):
    # ackDisableOrEnable
    # If Pairing in progress keep Ack
    # If Battery device keep Ack

    return (
        ("PairingInProgress" not in self.ListOfDevices[key] or not self.ListOfDevices[key]["PairingInProgress"])
        and ("PowerSource" not in self.ListOfDevices[key] or self.ListOfDevices[key]["PowerSource"] != "Battery")
        and ("MacCapa" not in self.ListOfDevices[key] or self.ListOfDevices[key]["MacCapa"] != "80")
    )


def instrument_timing(module, timing, cnt_timing, cumul_timing, aver_timing, max_timing):

    cumul_timing += timing
    cnt_timing += 1
    aver_timing = int(cumul_timing / cnt_timing)
    if timing > max_timing:
        Domoticz.Log("%s report a timing %s ms greated than the current max %s ms" % (module, timing, max_timing))
        max_timing = timing

    return cnt_timing, cumul_timing, aver_timing, max_timing


# Configuration Helpers
def setConfigItem(Key=None, Attribute="", Value=None):

    Config = {}
    if not isinstance(Value, (str, int, float, bool, bytes, bytearray, list, dict)):
        Domoticz.Error("setConfigItem - A value is specified of a not allowed type: '" + str(type(Value)) + "'")
        return Config

    if isinstance(Value, dict):
        # There is an issue that Configuration doesn't allow None value in dictionary !
        # Replace none value to 'null'
        Value = prepare_dict_for_storage(Value, Attribute)

    try:
        Config = Domoticz.Configuration()
        if Key is None:
            Config = Value  # set whole configuration if no key specified
        else:
            Config[Key] = Value

        Config = Domoticz.Configuration(Config)
    except Exception as inst:
        Domoticz.Error("setConfigItem - Domoticz.Configuration operation failed: '" + str(inst) + "'")
        return None
    return Config


def getConfigItem(Key=None, Attribute="", Default={}):
    Value = Default
    try:
        Config = Domoticz.Configuration()
        if Key is None:
            Value = Config  # return the whole configuration if no key
        else:
            Value = Config[Key]  # only return requested key if there was one
    except KeyError:
        Value = Default
    except Exception as inst:
        Domoticz.Error("getConfigItem - Domoticz.Configuration read failed: '" + str(inst) + "'")

    return repair_dict_after_load(Value, Attribute)


def prepare_dict_for_storage(dict_items, Attribute):

    from base64 import b64encode

    if Attribute in dict_items:
        dict_items[Attribute] = b64encode(str(dict_items[Attribute]).encode("utf-8"))
    dict_items["Version"] = 1
    return dict_items


def repair_dict_after_load(b64_dict, Attribute):
    if b64_dict in ("", {}):
        return {}
    if "Version" not in b64_dict:
        Domoticz.Log("repair_dict_after_load - Not supported storage")
        return {}
    if Attribute in b64_dict:
        from base64 import b64decode

        b64_dict[Attribute] = eval(b64decode(b64_dict[Attribute]))
    return b64_dict
