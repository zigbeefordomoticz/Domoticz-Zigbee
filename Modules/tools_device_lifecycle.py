#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""Device lifecycle helpers extracted from tools.py"""
import copy

from Modules.database import PLUGIN_DATABASE_RECORD_VERSION, WriteDeviceList
from Modules.domoticzAbstractLayer import domo_read_Device_Idx, domo_read_Name
from Modules.pluginDbAttributes import STORE_CONFIGURE_REPORTING


DEFAULT_DEVICE_SETUP = {
    "Version": PLUGIN_DATABASE_RECORD_VERSION,
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


def initialize_device_record(self, nwkid: str) -> None:
    """
    Initialize a new entry in the ListOfDevices for the given Nwkid.

    This sets up a default structure for a Zigbee device if it does not
    already exist in the device list and the nwkid is valid (non-empty).

    Parameters:
        nwkid (str): The network ID (short address) of the device.

    Returns:
        None
    """
    if not nwkid:
        return
    
    if nwkid in self.ListOfDevices:
        return

    self.ListOfDevices[nwkid] = copy.deepcopy(DEFAULT_DEVICE_SETUP)


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
    if ( "ClusterType" in self.ListOfDevices[nwkid] ): 
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