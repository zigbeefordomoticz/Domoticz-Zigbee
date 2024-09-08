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

"""
    Module : z_tools.py


    Description: Zigate toolbox
"""

import datetime
import os.path
import time
from pathlib import Path

from Modules.database import WriteDeviceList
from Modules.pluginDbAttributes import STORE_CONFIGURE_REPORTING
from Modules.zigateConsts import HEARTBEAT
from Modules.domoticzAbstractLayer import domo_read_Device_Idx, domo_read_Name

HEX_DIGIT = "0123456789abcdefABCDEF"
INT_DIGIT = "0123456789"

def is_hex(s):
    return all(char in HEX_DIGIT for char in s)

def is_int(s):
    return all(char in INT_DIGIT for char in s)

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

def str_round(value, n):
    return "{:.{n}f}".format(value, n=int(n))

def voltage2batteryP(voltage, volt_max, volt_min):
    if isinstance( voltage, str):
        voltage = int(voltage)

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
    
    # In case ReadAttributesEp is defined in Conf file, then we will restrict to only those Ep.
    readattributeslistofep = []
    if NwkId in self.ListOfDevices and "Model" in self.ListOfDevices[ NwkId ] and self.ListOfDevices[ NwkId ]["Model"] not in ( "", {} ):
        _model = self.ListOfDevices[ NwkId ]["Model"]
        if ( _model in self.DeviceConf and "ReadAttributesEp" in self.DeviceConf[_model]):
            readattributeslistofep = self.DeviceConf[_model]["ReadAttributesEp"]


    EpList = []
    if NwkId not in self.ListOfDevices:
        return EpList

    oldFashion = ( "ClusterType" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["ClusterType"] not in ({}, "") )
    for Ep in list(self.ListOfDevices[NwkId]["Ep"].keys()):
        if SearchCluster not in self.ListOfDevices[NwkId]["Ep"][Ep]:
            continue

        if oldFashion:
            EpList.append(Ep)
            
        elif ( 
            "ClusterType" in self.ListOfDevices[NwkId]["Ep"][Ep] 
            and self.ListOfDevices[NwkId]["Ep"][Ep]["ClusterType"] not in ( {}, "") 
            and ( not readattributeslistofep or Ep in readattributeslistofep)  
        ):
            EpList.append(Ep)
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


def getEpForCluster(self, nwkid, ClusterId, strict=False):
    """
    Return the Ep or a list of Ep associated to the ClusterId
    If not found return Ep: 01
    If strict is True, then None will return if there is no Cluster found
    """

    EPlist = []
    for x in list(self.ListOfDevices[nwkid]["Ep"].keys() ):
        if x in EPlist:
            continue
        if ClusterId in self.ListOfDevices[nwkid]["Ep"][x]:
            EPlist.append( str(x) )
    if strict and not EPlist:
        return None
    return EPlist


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
    #   Verify that Status is not 'UNKNOW' otherwise condider not found
    if lookupNwkId in self.ListOfDevices and "Status" in self.ListOfDevices[lookupNwkId]:
        if "IEEE" in self.ListOfDevices[lookupNwkId]:
            ieee_from_nwkid = self.ListOfDevices[lookupNwkId]["IEEE"]

        # Found, let's check the Status
        if self.ListOfDevices[lookupNwkId]["Status"] != "UNKNOW":
            found = True

    # 2- We might have found it with the lookupNwkId
    # If we didnt find it, we should check if this is not a new ShortId
    if lookupIEEE:
        if lookupIEEE not in self.IEEE2NWK:
            if not found:
                return found
            # We are in situation where we found the device in ListOfDevices but not in IEEE2NWK.
            # this is not expected
            self.log.logging("PluginTools", "Error", "DeviceExist - Found %s some inconsistency Inputs: %s %s instead of %s" % (
                found, lookupNwkId, lookupIEEE, ieee_from_nwkid))
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
            self.log.logging("PluginTools", "Error", "DeviceExist - Found inconsistency ! Not Device %s not found, while looking for %s (%s)" % (
                exitsingNwkId, lookupIEEE, lookupNwkId))
            return False

        if 'Status' not in self.ListOfDevices[ exitsingNwkId ]:
            # Should not happen
            # That seems not correct
            # We might have to do some cleanup here !
            # Cleanup
            # Delete the entry in IEEE2NWK as it will be recreated in Decode004d
            del self.IEEE2NWK[ lookupIEEE ]
            # Delete the all Data Structure
            del self.ListOfDevices[ exitsingNwkId ]
            self.log.logging("PluginTools", "Error", "DeviceExist - Found inconsistency ! Not 'Status' attribute for Device %s, while looking for %s (%s)" % (
                exitsingNwkId, lookupIEEE, lookupNwkId))
            return False

        if self.ListOfDevices[exitsingNwkId]["Status"] in ("004d", "0045", "0043", "8045", "8043", "UNKNOWN", "UNKNOW", ):
            # We are in the discovery/provisioning process,
            # and the device got a new Short Id
            # we need to restart from the beginning and remove all existing datastructures.
            # In case we receive asynchronously messages (which should be possible), they must be
            # dropped in the corresponding Decodexxx function
            # Delete the entry in IEEE2NWK as it will be recreated in Decode004d
            del self.IEEE2NWK[lookupIEEE]
            # Delete the all Data Structure
            del self.ListOfDevices[exitsingNwkId]
            self.log.logging("PluginTools", "Status", "DeviceExist - Device %s changed its ShortId: from %s to %s during provisioning. Restarting !" % (
                lookupIEEE, exitsingNwkId, lookupNwkId))
            return False

        # At that stage, we have found an entry for the IEEE, but doesn't match
        # the coming Short Address lookupNwkId.
        # Most likely , device has changed its NwkId
        found = True
        reconnectNWkDevice(self, lookupNwkId, lookupIEEE, exitsingNwkId)

        self.adminWidgets.updateNotificationWidget( Devices, "Reconnect %s %s with %s" % (lookupNwkId, lookupIEEE, exitsingNwkId))

    return found


def reconnectNWkDevice(self, new_NwkId, IEEE, old_NwkId):
    # We got a new Network ID for an existing IEEE. So just re-connect.
    # - mapping the information to the new new_NwkId
    if old_NwkId not in self.ListOfDevices:
        return False
    if old_NwkId == new_NwkId:
        return True

    if new_NwkId == "0000" or old_NwkId == "0000":
        self.log.logging("PluginTools", "Log", "reconnectNWkDevice - Looks like we have an IEEE matching a Coordinator nwkid , this is not possible by definition New: %s Old: %s IEEE: %s !!!" % (
            new_NwkId, old_NwkId, IEEE))
        return False
    
    self.ListOfDevices[new_NwkId] = dict(self.ListOfDevices[old_NwkId])
    self.IEEE2NWK[IEEE] = new_NwkId

    if "ZDeviceName" in self.ListOfDevices[new_NwkId]:
        devName = self.ListOfDevices[new_NwkId]["ZDeviceName"]

    # MostLikely exitsingKey(the old NetworkID) is not needed any more
    if removeNwkInList(self, old_NwkId) is None:
        self.log.logging("PluginTools", "Error", "reconnectNWkDevice - something went wrong in the reconnect New NwkId: %s Old NwkId: %s IEEE: %s" % (
            new_NwkId, old_NwkId, IEEE))

    if self.groupmgt:
        # We should check if this belongs to a group
        self.groupmgt.update_due_to_nwk_id_change(old_NwkId, new_NwkId)
        
    self.ListOfDevices[new_NwkId]["PreviousStatus"] = self.ListOfDevices[new_NwkId]["Status"]
    if self.ListOfDevices[new_NwkId]["Status"] in ( "Leave", ):
        self.ListOfDevices[new_NwkId]["Status"] = "inDB"
        self.ListOfDevices[new_NwkId]["Heartbeat"] = "0"
        self.log.logging("PluginTools", "Status", "reconnectNWkDevice - Update Status from %s to 'inDB' for NetworkID : %s" % (
            self.ListOfDevices[new_NwkId]["Status"], new_NwkId))

    # We will also reset ReadAttributes
    if self.pluginconf.pluginConf["enableReadAttributes"]:
        if "ReadAttributes" in self.ListOfDevices[new_NwkId]:
            del self.ListOfDevices[new_NwkId]["ReadAttributes"]
        if STORE_CONFIGURE_REPORTING in self.ListOfDevices[new_NwkId]:
            del self.ListOfDevices[new_NwkId][STORE_CONFIGURE_REPORTING]
        self.ListOfDevices[new_NwkId]["Heartbeat"] = "0"

    WriteDeviceList(self, 0)
    self.log.logging("PluginTools", "Status", "NetworkID: %s is replacing %s for object: %s" % (new_NwkId, old_NwkId, IEEE))
    return True


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
    return safe


def removeDeviceInList(self, Devices, IEEE, Unit):
    # Most likely call when a Device is removed from Domoticz
    # This is a tricky one, as you might have several Domoticz devices attached to this IoT and so you must remove only the corredpoing part.
    # Must seach in the NwkID dictionnary and remove only the corresponding device entry in the ClusterType.
    # In case there is no more ClusterType , then the full entry can be removed

    if IEEE not in self.IEEE2NWK:
        return

    nwkid = self.IEEE2NWK[IEEE]
    ID = domo_read_Device_Idx(self, Devices, IEEE, Unit,)
    widget_name = domo_read_Name( self, Devices, IEEE, Unit, )
    if ( "ClusterTye" in self.ListOfDevices[nwkid] ):  
        # We are in the old fasho V. 3.0.x Where ClusterType has been migrated from Domoticz
        if str(ID) in self.ListOfDevices[nwkid]["ClusterType"]:
            del self.ListOfDevices[nwkid]["ClusterType"][ID]  # Let's remove that entry
            self.log.logging("PluginTools", "Log", "removeDeviceInList - removing : %s in %s" % (ID, str(self.ListOfDevices[nwkid]["ClusterType"])))
            
    else:
        for tmpEp in list(self.ListOfDevices[nwkid]["Ep"].keys()):
            # Search this DeviceID in ClusterType
            if (
                "ClusterType" in self.ListOfDevices[nwkid]["Ep"][tmpEp]
                and str(ID) in self.ListOfDevices[nwkid]["Ep"][tmpEp]["ClusterType"]
            ):
                del self.ListOfDevices[nwkid]["Ep"][tmpEp]["ClusterType"][str(ID)]
                self.log.logging("PluginTools", "Log", "removeDeviceInList - removing : %s with Ep: %s in - %s" % (
                    ID, tmpEp, str(self.ListOfDevices[nwkid]["Ep"][tmpEp]["ClusterType"])) )

    # Finaly let's see if there is any Devices left in this .
    emptyCT = True
    if "ClusterType" in self.ListOfDevices[nwkid]:  # Empty or Doesn't exist
        self.log.logging("PluginTools", "Log", "removeDeviceInList - existing Global 'ClusterTpe'")
        if self.ListOfDevices[nwkid]["ClusterType"] != {}:
            emptyCT = False
    for tmpEp in list(self.ListOfDevices[nwkid]["Ep"].keys()):
        if "ClusterType" in self.ListOfDevices[nwkid]["Ep"][tmpEp]:
            self.log.logging("PluginTools", "Log", "removeDeviceInList - existing Ep 'ClusterTpe'")
            if self.ListOfDevices[nwkid]["Ep"][tmpEp]["ClusterType"] != {}:
                emptyCT = False

    if emptyCT:
        #del self.ListOfDevices[key]
        #del self.IEEE2NWK[IEEE]
        self.ListOfDevices[nwkid]["Status"] = "Removed"

        self.adminWidgets.updateNotificationWidget(
            Devices, "Device fully removed %s with IEEE: %s" % (widget_name, IEEE)
        )
        self.log.logging("PluginTools", "Status", "Device %s with IEEE: %s fully removed from the system." % (widget_name, IEEE))
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


# Used by zcl/zdpRawCommands
def get_and_inc_ZDP_SQN(self, key):
    return get_and_increment_generic_SQN(self, key, "ZDPSQN")


def get_and_inc_ZCL_SQN(self, key):
    return get_and_increment_generic_SQN(self, key, "ZCLSQN")


def get_and_inc_TUYA_POLLING_SQN(self, key):
    return get_and_increment_generic_SQN(self, key, "TUYA_POLLING_SQN")


def get_and_increment_generic_SQN(self, nwkid, sqn_type):
    if nwkid not in self.ListOfDevices: 
        return "%02x" %0x00

    if sqn_type not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid][ sqn_type ] = "%02x" %0x00
        return self.ListOfDevices[nwkid][ sqn_type ]

    if self.ListOfDevices[nwkid][ sqn_type ] in ( '', {}):
        self.ListOfDevices[nwkid][ sqn_type ] = "%02x" %0x00
        return self.ListOfDevices[nwkid][ sqn_type ]

    self.ListOfDevices[nwkid][ sqn_type ] = "%02x" %( ( int(self.ListOfDevices[nwkid][ sqn_type ],16) + 1) % 256)
    return self.ListOfDevices[nwkid][ sqn_type ]


def updSQN(self, key, newSQN):
    if key in self.ListOfDevices and newSQN:
        self.ListOfDevices[key]["SQN"] = newSQN


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


def upd_RSSI(self, nwkid, rssi_value):
    # Ensure the device exists in the dictionary
    if nwkid not in self.ListOfDevices:
        return
    
    # Update RSSI value directly
    self.ListOfDevices[nwkid]["RSSI"] = rssi_value

    # Initialize RollingRSSI list if it doesn't exist
    self.ListOfDevices[nwkid].setdefault("RollingRSSI", [])

    # Add RSSI to RollingRSSI list
    self.ListOfDevices[nwkid]["RollingRSSI"].append(rssi_value)

    # Keep RollingRSSI list size at most 10 elements
    self.ListOfDevices[nwkid]["RollingRSSI"] = self.ListOfDevices[nwkid]["RollingRSSI"][-10:]


# Those functions will be use with the new DeviceConf structutre

def is_fake_ep( self, nwkid, ep):
    
    return (
        "Model" in self.ListOfDevices[nwkid]
        and self.ListOfDevices[nwkid]["Model"] in self.DeviceConf
        and "FakeEp" in self.DeviceConf[self.ListOfDevices[nwkid]["Model"]]
        and ep in self.DeviceConf[self.ListOfDevices[nwkid]["Model"]]["FakeEp"]
    )

def is_bind_ep( self, nwkid, ep):
    return (
        "Model" not in self.ListOfDevices[nwkid]
        or self.ListOfDevices[nwkid]["Model"] not in self.DeviceConf
        or "bindEp" not in self.DeviceConf[self.ListOfDevices[nwkid]["Model"]]
        or ep in self.DeviceConf[self.ListOfDevices[nwkid]["Model"]]["bindEp"]
    )
    
def deviceconf_device(self, nwkid):
    
    if (
        "Model" in self.ListOfDevices[nwkid ]
        and self.ListOfDevices[nwkid]["Model"] in self.DeviceConf
    ):
        return self.DeviceConf[ self.ListOfDevices[nwkid]["Model"] ]
    else:
        return {}
    
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
        self.log.logging("PluginTools", "Error", "getListofClusterbyModel - Argument error : " + Model + " " + InOut)
        return ""

    if Model in self.DeviceConf and InOut in self.DeviceConf[Model]:
        for ep in list(self.DeviceConf[Model][InOut].keys()):
            seen = ""
            for cluster in sorted(self.DeviceConf[Model][InOut][ep]):
                if cluster in ("ClusterType", "Type", "ColorMode", seen):
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
                EpinType = (ep, getListofType(self, self.DeviceConf[Model]["Epin"][ep]["Type"]))
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
    var_h, var_s, var_l = ((high + low) / 2,) * 3

    if high == low:
        var_h = 0.0
        var_s = 0.0
    else:
        d = high - low
        var_s = d / (2 - high - low) if var_l > 0.5 else d / (high + low)
        var_h = {
            r: (g - b) / d + (6 if g < b else 0),
            g: (b - r) / d + 2,
            b: (r - g) / d + 4,
        }[high]
        var_h /= 6

    return var_h, var_s, var_l


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
        self.log.logging("PluginTools", "Error", "%s not known !!!" % nwkid)
        return inMacCapa

    if "Model" not in self.ListOfDevices[nwkid]:
        return inMacCapa

    # Convert battery annouced devices to main powered / Make sure that you do the reverse n NetworkMap
    if (
        get_deviceconf_parameter_value(self, self.ListOfDevices[nwkid]["Model"], "MainPoweredDevice")
        or self.ListOfDevices[nwkid]["Model"] in ("TI0001", "TS0011", "TS0013", "TS0601-switch", "TS0601-2Gangs-switch", )
    ):
        # Livol Switch, must be converted to Main Powered
        # Patch some status as Device Annouced doesn't provide much info
        self.ListOfDevices[nwkid]["LogicalType"] = "Router"
    # Not DevideType but DeviceType    
    #    self.ListOfDevices[nwkid]["DevideType"] = "FFD"
        self.ListOfDevices[nwkid]["DeviceType"] = "FFD"
        self.ListOfDevices[nwkid]["MacCapa"] = "8e"
        self.ListOfDevices[nwkid]["PowerSource"] = "Main"
        return "8e"

    # Convert Main Powered device to Battery
    if (
        get_deviceconf_parameter_value(self, self.ListOfDevices[nwkid]["Model"], "BatteryPoweredDevice")
        or self.ListOfDevices[nwkid]["Model"] in ( "lumi.remote.b686opcn01", "lumi.remote.b486opcn01", "lumi.remote.b286opcn01", "lumi.remote.b686opcn01-bulb", "lumi.remote.b486opcn01-bulb", "lumi.remote.b286opcn01-bulb", "lumi.remote.b686opcn01",)
    ):
        # Aqara Opple Switch, must be converted to Battery Devices
        self.ListOfDevices[nwkid]["MacCapa"] = "80"
        self.ListOfDevices[nwkid]["PowerSource"] = "Battery"
        if "Capability" in self.ListOfDevices[nwkid] and "Main Powered" in self.ListOfDevices[nwkid]["Capability"]:
            self.ListOfDevices[nwkid]["Capability"].remove("Main Powered")
        return "80"

    if "MacCapa" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["MacCapa"] == "80" and (
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
        self.log.logging("PluginTools", "Debug", "mainPoweredDevice - Unknown Device: %s" % nwkid)
        return False

    model_name = ""
    if "Model" in self.ListOfDevices[nwkid]:
        model_name = self.ListOfDevices[nwkid]["Model"]

    mainPower = False
    if "MacCapa" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["MacCapa"] != {}:
        mainPower = self.ListOfDevices[nwkid]["MacCapa"] in ["8e", "84"]

    # These are Model annouced as Main Power and are not
    if (
        get_deviceconf_parameter_value(self, model_name, "BatteryPoweredDevice")
        or model_name in (
            "lumi.remote.b686opcn01",
            "lumi.remote.b486opcn01",
            "lumi.remote.b286opcn01",
            "lumi.remote.b686opcn01-bulb",
            "lumi.remote.b486opcn01-bulb",
            "lumi.remote.b286opcn01-bulb",
        )
    ):
        mainPower = False

    # These are device annouced as Battery, but are Main Powered ( some time without neutral)
    if (
        get_deviceconf_parameter_value(self, model_name, "MainPoweredDevice")
        or model_name in ("TI0001", "TS0011", "TS0601-switch", "TS0601-2Gangs-switch", "ZBMINI-L",)
    ):
        mainPower = True
        self.ListOfDevices[nwkid]["LogicalType"] = "End Device"
    # Not DevideType but DeviceType    
    #    self.ListOfDevices[nwkid]["DevideType"] = "RFD"
        self.ListOfDevices[nwkid]["DeviceType"] = "RFD"

    if not mainPower and "PowerSource" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["PowerSource"] != {}:
        mainPower = self.ListOfDevices[nwkid]["PowerSource"] == "Main"

    # We need to take in consideration that Livolo is reporting a MacCapa of 0x80
    # That Aqara Opple are reporting MacCap 0x84 while they are Battery devices

    return mainPower


def loggingMessages(self, msgtype, sAddr=None, ieee=None, LQI=None, SQN=None):

    if not self.pluginconf.pluginConf["logFORMAT"]:
        return
    if sAddr == ieee and sAddr is None:
        return
    _debugMatchId = self.pluginconf.pluginConf["debugMatchId"].lower()
    if sAddr is None:
        sAddr = self.IEEE2NWK[ieee] if ieee in self.IEEE2NWK else ""
    if ieee is None:
        ieee = self.ListOfDevices[sAddr]["IEEE"] if sAddr in self.ListOfDevices else ""
    if _debugMatchId not in ["ffff", sAddr]:
        # If not matching _debugMatchId
        return

    zdevname = ""
    if sAddr in self.ListOfDevices and "ZDeviceName" in self.ListOfDevices[sAddr]:
        zdevname = self.ListOfDevices[sAddr]["ZDeviceName"]

    self.log.logging("PluginTools", "Log", "Device activity for | %4s | %14s | %4s | %16s | %3s | 0x%02s |" % (
        msgtype, zdevname, sAddr, ieee, int(LQI, 16), SQN) )

def try_to_reconnect_via_neighbours(self, old_nwkid):
    
    # We receive a message from a known NwkId but got a NACK. 
    # Let see if we don't have a wrong NwkId

    if old_nwkid == "0000":
        return None
    
    if "IEEE" not in self.ListOfDevices[ old_nwkid ]:
        return None
    ieee = self.ListOfDevices[ old_nwkid ]["IEEE"]

    for key in list(self.ListOfDevices.keys()):
        if "Neighbours" not in self.ListOfDevices[key]:
            continue
        if len(self.ListOfDevices[key]["Neighbours"]) == 0:
            continue
        # We are interested only on the last one
        lastScan = self.ListOfDevices[key]["Neighbours"][-1]
        for item in lastScan["Devices"]:
            if not isinstance(item, dict):
                continue
            for x in item:
                if "_IEEE" not in item[x]:
                    continue
                if item[x]["_IEEE"] == ieee:
                    new_nwkid = x
                    if new_nwkid != old_nwkid:
                        reconnectNWkDevice(self, new_nwkid, ieee, old_nwkid)
                        self.log.logging("PluginTools", "Log", "try_to_reconnect_via_neighbours found %s as replacement of %s" % (new_nwkid, old_nwkid))
                    return new_nwkid

def chk_and_update_IEEE_NWKID(self, nwkid, ieee):
    if ieee in self.IEEE2NWK and nwkid in self.ListOfDevices:
        return
    if nwkid in self.ListOfDevices:
        return
    if self.ControllerIEEE and self.ControllerIEEE == ieee:
        return
    if nwkid == "0000":
        return
    if ieee not in self.IEEE2NWK:
        return

    old_nwkid = self.IEEE2NWK[ ieee ]
    self.log.logging("PluginTools", "Log", "chk_and_update_IEEE_NWKID - update %s %s -> %s" %(ieee, old_nwkid, nwkid))
    reconnectNWkDevice(self, nwkid, ieee, old_nwkid)
        
def lookupForIEEE(self, nwkid, reconnect=False):
    # """
    # Purpose of this function is to search a Nwkid in the Neighbours table and find an IEEE
    # This is used when receiving a message from an unknown device !
    # """

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
                del self.IEEE2NWK[ieee]
                self.log.logging("PluginTools", "Error", "lookupForIEEE found an inconsitency %s not existing but pointed by %s, cleanup" % (
                    old_NwkId, ieee) )
                continue

            if reconnect:
                reconnectNWkDevice(self, nwkid, ieee, old_NwkId)
                self.log.logging("PluginTools", "Status", "lookupForIEEE found a matching IEEE: %s in the Router Neighbours %s with Nwkid: %s (old Nwkid was %s)" %(
                    ieee, key, nwkid, old_NwkId))
            return ieee
    return None

def zigpy_plugin_sanity_check(self, nwkid):
    if self.zigbee_communication and self.zigbee_communication != "zigpy":
        return False
    ieee = self.ControllerLink.get_device_ieee( nwkid )
    if ieee is None:
        return False
    if ieee not in self.IEEE2NWK:
        return False
    if self.IEEE2NWK[ ieee ] == nwkid and nwkid in self.ListOfDevices:
        if "Status" in self.ListOfDevices[ nwkid ] and self.ListOfDevices[ nwkid ]["Status"] in ( 'Leave', ):
            # the device is alive and ieee/nwkid is correct
            self.log.logging("PluginTools", "Status", "zigpy_plugin_sanity_check - Update Status from %s to 'inDB' for NetworkID : %s" % (
                self.ListOfDevices[nwkid]["Status"], nwkid), nwkid)
            self.ListOfDevices[ nwkid ]["Status"] = 'inDB'
            self.ListOfDevices[nwkid]["Heartbeat"] = "0"
        return True
    # we have a disconnect as IEEE is not pointing to the right nwkid
    return reconnectNWkDevice(self, nwkid, ieee, self.IEEE2NWK[ ieee ])

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

    if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]["Ep"]:
        self.ListOfDevices[MsgSrcAddr]["Ep"][ MsgSrcEp ] = {}
    if MsgClusterId not in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]:
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId] = {}

    if not isinstance(self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId], dict):
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId] = {}

    if MsgAttrID not in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId]:
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId][MsgAttrID] = {}


def checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, Value):
    checkAttribute(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID)
    self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId][MsgAttrID] = Value


def store_battery_percentage_time_stamp( self, MsgSrcAddr):
    self.ListOfDevices[MsgSrcAddr]["BatteryPercentage_TimeStamp"] = time.time()


def store_battery_voltage_time_stamp( self, MsgSrcAddr):
    self.ListOfDevices[MsgSrcAddr]["BatteryVoltage_TimeStamp"] = time.time()


def checkValidValue(self, MsgSrcAddr, AttType, Data ):
    if int(AttType, 16) == 0xE2 and Data == "ffffffff":
        return False
    return self.ListOfDevices[MsgSrcAddr][ "Model" ] != "lumi.airmonitor.acn01" or Data not in ["8000", "0000"]

def getAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID):

    if MsgSrcAddr not in self.ListOfDevices:
        self.log.logging("PluginTools", "Debug", "getAttributeValue - Unknown %s" % (MsgSrcAddr))
        return None
    if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]["Ep"]:
        self.log.logging("PluginTools", "Debug", "getAttributeValue - Unknown %s/%s" % (MsgSrcAddr, MsgSrcEp))
        return None
    if MsgClusterId not in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]:
        self.log.logging("PluginTools", "Debug", "getAttributeValue - Unknown %s/%s %s" % (MsgSrcAddr, MsgSrcEp, MsgClusterId))
        return None
    if not isinstance(self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId], dict):
        self.log.logging("PluginTools", "Debug", "getAttributeValue - Not dict %s/%s %s" % (MsgSrcAddr, MsgSrcEp, MsgClusterId))
        return None
    if MsgAttrID not in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId]:
        self.log.logging("PluginTools", "Debug", "getAttributeValue - Unknown %s/%s %s %s" % (MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID))
        return None
    return self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId][MsgAttrID]


# Function to manage 0x8002 payloads
def retreive_cmd_payload_from_8002(Payload):

    ManufacturerCode = None
    if len(Payload) < 2:
        return (None, None, None, None, None, None)
    
    fcf = Payload[:2]

    try:
        GlobalCommand = is_globalcommand(fcf)
        zbee_zcl_ddr = disable_default_response(fcf)
    except Exception as e:
        return (None, None, None, None, None, None)
                  
    if GlobalCommand is None:
        return (None, None, None, None, None, None)

    if len(Payload) < 6:
        return (None, None, None, None, None, None)

    if is_manufspecific_8002_payload(fcf):
        ManufacturerCode = Payload[4:6] + Payload[2:4]
        Sqn = Payload[6:8]
        Command = Payload[8:10]
        Data = Payload[10:]
    else:
        Sqn = Payload[2:4]
        Command = Payload[4:6]
        Data = Payload[6:]

    return (zbee_zcl_ddr, GlobalCommand, Sqn, ManufacturerCode, Command, Data)

def fcf_direction(fcf):
    # If direction = 1 Server to Client
    # If direction = 0 Client to Server

    if not is_hex(fcf) or len(fcf) != 2:
        return None
    return (int(fcf, 16) & 0x08) >> 3

def disable_default_response(fcf):
    return (int(fcf,16) & 0x10) >> 4

def is_direction_to_client(fcf):
    return fcf_direction(fcf) == 0x1

def is_direction_to_server(fcf):
    return fcf_direction(fcf) == 0x0

def is_globalcommand(fcf):
    return None if not is_hex(fcf) or len(fcf) != 2 else (int(fcf, 16) & 0b00000011) == 0

def frame_type(fcf):
    return (int(fcf, 16) & 0b00000011)
    
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
    return "%02x" % fcf

def get_cluster_attribute_value( self, key, endpoint, clusterId, AttributeId):
    if (
        key not in self.ListOfDevices
        or "Ep" not in self.ListOfDevices[key]
        or endpoint not in self.ListOfDevices[key]["Ep"]
        or clusterId not in self.ListOfDevices[key]["Ep"][ endpoint ]
        or AttributeId not in self.ListOfDevices[key]["Ep"][ endpoint ][ clusterId ]
    ):
        return None
    return self.ListOfDevices[key]["Ep"][ endpoint ][ clusterId ][ AttributeId]


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
        return False
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
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
    return list(list(self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"].keys()))

def get_list_isqn_int_attr_datastruct(self, DeviceAttribute, key, endpoint, clusterId):
    if key not in self.ListOfDevices:
        return []
    if check_datastruct(self, DeviceAttribute, key, endpoint, clusterId) is None:
        return []
    return [int(x, 16) for x in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"].keys()]

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
    return True if lastStatus in ("86", "8c") else lastStatus != "00"


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


def is_domoticz_db_available(self):
    #  Domoticz 2021.1 build 13495

    if not self.VersionNewFashion:
        self.log.logging("PluginTools", "Debug", "is_domoticz_db_available: %s due to Fashion" % False)
        return False

    if self.DomoticzMajor < 2021:
        self.log.logging("PluginTools", "Debug", "is_domoticz_db_available: %s due to Major" % False)
        return False

    if self.DomoticzMajor == 2021 and self.DomoticzMinor < 1:
        self.log.logging("PluginTools", "Debug", "is_domoticz_db_available: %s due to Minor" % False)
        return False

    return True

def get_device_nickname(self, NwkId=None, Ieee=None):
    if Ieee:
        NwkId = self.IEEE2NWK.get(Ieee, NwkId)

    return self.ListOfDevices.get(NwkId, {}).get('ZDeviceName', "")

    
def extract_info_from_8085(MsgData):
    step_mod = MsgData[14:16]
    up_down = MsgData[16:18] if len(MsgData) >= 18 else None
    step_size = MsgData[18:20] if len(MsgData) >= 20 else None
    transition = MsgData[20:22] if len(MsgData) >= 22 else None

    return (step_mod, up_down, step_size, transition)


def how_many_devices(self):
    routers = enddevices = 0
    
    for x in self.ListOfDevices:
        if "DeviceType" in self.ListOfDevices[x] and self.ListOfDevices[x]["DeviceType"] == "FFD":
            routers += 1
            continue
        
        if "LogicalType" in self.ListOfDevices[x] and self.ListOfDevices[x]["LogicalType"] == "Router":
            routers += 1
            continue
        
        if "LogicalType" in self.ListOfDevices[x] and self.ListOfDevices[x]["LogicalType"] == "End Device":
            enddevices += 1
            continue
        
        if "DeviceType" in self.ListOfDevices[x] and self.ListOfDevices[x]["DeviceType"] == "RFD":
            enddevices += 1
            continue

        if "MacCapa" in self.ListOfDevices[x] and self.ListOfDevices[x]["MacCapa"] == "8e":
            routers += 1
            continue

        if "MacCapa" in self.ListOfDevices[x] and self.ListOfDevices[x]["MacCapa"] == "80":
            enddevices += 1
            continue

    return routers, enddevices


def get_deviceconf_parameter_value(self, model, attribute, return_default=None):
    """ Retrieve Configuration Attribute from Config file"""
    
    return self.DeviceConf.get(model, {}).get(attribute, return_default)


def night_shift_jobs( self ):
    # If NighShift not enable, then alwasy return True
    # Otherwise return True only if between midnight and 6am

    if not self.pluginconf.pluginConf["NightShift"]:
        #self.log.logging("PluginTools", "Debug", "Always On" )
        return True

    current = datetime.datetime.now().time()

    # Check against first part of the night
    start = datetime.time(23, 0,0)
    end = datetime.time(23,59,59)

    if start <= current <= end:
        self.log.logging("PluginTools", "Debug", "Inside of Night Shift period %s %s %s" %( start, current, end))
        return True

    # Check against the second part of the night
    start = datetime.time(0, 0,0)
    end = datetime.time(6,0,0)
    if start <= current <= end:
        self.log.logging("PluginTools", "Debug","Inside of Night Shift period %s %s %s" %( start, current, end))
        return True

    self.log.logging("PluginTools", "Debug", "Outside of Night Shift period %s %s %s" %( start, current, end))
    return False


def print_stack( self ):
    
    try:
        import inspect
    except Exception as e:
        self.log.logging( "PluginTools", "Error", "Cannot import python module inspect")
        return
    
    for x in inspect.stack():
        self.log.logging( "PluginTools", "Error", "[{:40}| {}:{}".format(x.function, x.filename, x.lineno))



def helper_copyfile(source, dest, move=True):

    try:
        import shutil

        if move:
            shutil.move(source, dest)
        else:
            shutil.copy(source, dest)
    except Exception:
        with open(source, "r") as src, open(dest, "wt") as dst:
            for line in src:
                dst.write(line)


def helper_versionFile(source, nbversion):

    source = str(source)
    if nbversion == 0:
        return

    if nbversion == 1:
        helper_copyfile(source, source + "-%02d" % 1)
    else:
        for version in range(nbversion - 1, 0, -1):
            _fileversion_n = source + "-%02d" % version
            if not os.path.isfile(_fileversion_n):
                continue

            _fileversion_n1 = source + "-%02d" % (version + 1)
            helper_copyfile(_fileversion_n, _fileversion_n1)

        # Last one
        helper_copyfile(source, source + "-%02d" % 1, move=False)

def build_list_of_device_model(self, force=False):
    
    if not force and ( self.internalHB % (23 * 3600 // HEARTBEAT) != 0):
        return

    self.pluginParameters["NetworkDevices"] = {}
    for x in self.ListOfDevices:
        if x == "0000":
            continue

        manufcode = manufname = modelname = None
        if "Model" in self.ListOfDevices[x]:
            modelname = self.ListOfDevices[x]["Model"]

        self.ListOfDevices[ x ]["CertifiedDevice"] = modelname in self.DeviceConf

        if "Manufacturer" in self.ListOfDevices[x]:
            manufcode = self.ListOfDevices[x]["Manufacturer"]
            if manufcode in ( "", {}):
                continue
            if manufcode not in self.pluginParameters["NetworkDevices"]:
                self.pluginParameters["NetworkDevices"][ manufcode ] = {}

        if manufcode and "Manufacturer Name" in self.ListOfDevices[x]:
            manufname = self.ListOfDevices[x]["Manufacturer Name"]
            if manufname in ( "", {} ):
                manufname = "unknown"
                
            if manufname not in self.pluginParameters["NetworkDevices"][ manufcode ]:
                self.pluginParameters["NetworkDevices"][ manufcode ][ manufname ] = []

        if manufcode and manufname and modelname:
            if modelname in ( "", {} ):
                continue
            if modelname not in self.pluginParameters["NetworkDevices"][ manufcode ][ manufname ]:
                self.pluginParameters["NetworkDevices"][ manufcode ][ manufname ].append( modelname )
                if modelname not in self.DeviceConf:
                    unknown_device_model(self, x, modelname,manufcode, manufname )


def unknown_device_model(self, NwkId, Model, ManufCode, ManufName ):
    
    self.log.logging("Plugin", "Debug", "unknown_device_model NwkId: %s Model: %s ManufCode: %s ManufName: %s" %(
        NwkId, Model, ManufCode, ManufName))
    
    if 'logUnknownDeviceModel' not in self.pluginconf.pluginConf or not self.pluginconf.pluginConf["logUnknownDeviceModel"]:
        return
    
    if 'Log_UnknowDeviceFlag' in self.ListOfDevices[ NwkId ] and (self.ListOfDevices[ NwkId ]['Log_UnknowDeviceFlag'] + ( 24 * 3600)) < time.time() :
        return
    
    if 'Status' in self.ListOfDevices[ NwkId ] and self.ListOfDevices[ NwkId ]['Status'] == 'notDB':
        return
           
    device_name = get_device_nickname( self, NwkId=NwkId)

    self.log.logging("Plugin", "Log", "We have detected a working device %s (%s) Model: %s not optimized with the plugin. " %( 
        get_device_nickname( self, NwkId=NwkId), NwkId, Model, ))
    self.log.logging("Plugin", "Log", "")
    self.log.logging("Plugin", "Log", " --- Please follow the link https://zigbeefordomoticz.github.io/wiki/en-eng/Problem_Dealing-with-none-optimized-device.html")         
    self.log.logging("Plugin", "Log", " --- Thanks the Zigbee for Domoticz plugin team")
    self.log.logging("Plugin", "Log", "")
    
    self.ListOfDevices[ NwkId ]['Log_UnknowDeviceFlag'] = time.time()

def is_domoticz_bellow_2020(self):
    return self.DomoticzMajor < 2020

def is_domoticz_bellow_2021(self):
    return self.DomoticzMajor < 2021

def is_domoticz_below_2022(self):
    return self.DomoticzMajor < 2022

def is_domoticz_below_2023(self):
    return self.DomoticzMajor < 2023

def is_domoticz_above_2022(self):
    return self.DomoticzMajor > 2022

def is_domoticz_above_2022_2(self):
    if self.DomoticzMajor > 2022:
        return True
    return self.DomoticzMajor == 2022 and self.DomoticzMinor >= 2

def is_domoticz_2023(self):
    if self.DomoticzMajor == 2023:
        return True
    
def is_domoticz_above_2023(self):
    return self.DomoticzMajor > 2023


def is_domoticz_bellow_2024(self):
    return self.DomoticzMajor < 2024


def is_domoticz_2024(self):
    return self.DomoticzMajor == 2024


def is_domoticz_above_2024(self):
    return self.DomoticzMajor > 2024

def is_domoticz_new_API(self):

    'is_domoticz_new_API() False True 1 15356'
    self.log.logging("PluginTools", "Debug", "is_domoticz_new_API() %s %s %s %s" %(
        is_domoticz_below_2023(self), is_domoticz_2023(self), self.DomoticzMinor, self.DomoticzBuild))
    
    if is_domoticz_below_2023(self):
        return False
    
    if is_domoticz_2023(self):
        return ( self.DomoticzMinor > 1 or ( self.DomoticzMinor == 1 and self.DomoticzBuild >= 15326 ))
        
    # Domoticz 2024 !
    return True

def is_domoticz_latest_typename(self):
    """Checks if the Domoticz binary includes the latest typename."""

    # If Domoticz version is below 2024, it's not the latest typename.
    if is_domoticz_bellow_2024(self):
        return False

    # If DomoticzMinor is greater than 4 or DomoticzBuild is 15956 or higher, it's the latest typename.
    if self.DomoticzMinor > 4 or self.DomoticzBuild >= 15956:
        return True

    # Otherwise, it's not the latest typename.
    return False


def is_domoticz_new_blind(self):
    return is_domoticz_above_2022_2(self)


def is_domoticz_update_SuppressTriggers( self ):
    
    if is_domoticz_above_2022:
        return True
    
    if is_domoticz_bellow_2021:
        return False

    if self.DomoticzMajor == 2021 and self.DomoticzMinor == 1 and self.DomoticzBuild < 13374:
        return False
    
    return True


def is_domoticz_touch(self):
    """Checks if the Domoticz version supports touch."""

    # If VersionNewFashion flag is set or DomoticzMajor is 2022 or higher, it supports touch.
    if self.VersionNewFashion or self.DomoticzMajor >= 2022:
        return True

    # If DomoticzMajor is 4 and DomoticzMinor is 10547 or higher, it supports touch.
    return self.DomoticzMajor == 4 and self.DomoticzMinor >= 10547


def get_device_config_param(self, NwkId, config_parameter):
    """Retrieve config_parameter from the Param section in Config or Device"""

    # Log debug information
    self.log.logging("Input", "Debug", f"get_device_config_param: {NwkId} Config: {config_parameter}")

    # Get the device dictionary for the given NwkId, defaulting to None if not found
    device = self.ListOfDevices.get(NwkId)

    # If device dictionary does not exist, return None
    if not device:
        return None

    # Get the "Param" section dictionary from the device, defaulting to None if not found
    param_section = device.get("Param")

    # If "Param" section dictionary does not exist, return None
    if not param_section:
        return None

    # Get the value of config_parameter from the "Param" section, defaulting to None if not found
    param_value = param_section.get(config_parameter)

    # Log debug information
    self.log.logging("Input", "Debug", f"get_device_config_param: {NwkId} Config: {config_parameter} return {param_value}")

    # Return the value of config_parameter
    return param_value
