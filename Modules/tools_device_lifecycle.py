#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""Device lifecycle helpers extracted from tools.py"""
import copy

from Modules.database import PLUGIN_DATABASE_RECORD_VERSION, request_flush_plugin_listofdevices
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


def remap_device_nwkid(self, new_NwkId: str, IEEE: str, old_NwkId: str) -> bool:
    # We got a new Network ID for an existing IEEE. So just re-connect.
    # - mapping the information to the new new_NwkId
    if old_NwkId not in self.ListOfDevices:
        return False
    if old_NwkId == new_NwkId:
        return True

    if new_NwkId == "0000" or old_NwkId == "0000":
        self.log.logging("PluginTools", "Log", "remap_device_nwkid - Looks like we have an IEEE matching a Coordinator nwkid , this is not possible by definition New: %s Old: %s IEEE: %s !!!" % (
            new_NwkId, old_NwkId, IEEE))
        return False
    
    self.ListOfDevices[new_NwkId] = dict(self.ListOfDevices[old_NwkId])
    self.IEEE2NWK[IEEE] = new_NwkId

    if "ZDeviceName" in self.ListOfDevices[new_NwkId]:
        devName = self.ListOfDevices[new_NwkId]["ZDeviceName"]

    # MostLikely exitsingKey(the old NetworkID) is not needed any more
    if drop_stale_nwkid(self, old_NwkId) is None:
        self.log.logging("PluginTools", "Error", "remap_device_nwkid - something went wrong in the reconnect New NwkId: %s Old NwkId: %s IEEE: %s" % (
            new_NwkId, old_NwkId, IEEE))

    if self.groupmgt:
        # We should check if this belongs to a group
        self.groupmgt.update_due_to_nwk_id_change(old_NwkId, new_NwkId)
        
    self.ListOfDevices[new_NwkId]["PreviousStatus"] = self.ListOfDevices[new_NwkId]["Status"]
    if self.ListOfDevices[new_NwkId]["Status"] in ( "Leave", ):
        self.ListOfDevices[new_NwkId]["Status"] = "inDB"
        self.ListOfDevices[new_NwkId]["Heartbeat"] = "0"
        self.log.logging("PluginTools", "Status", "remap_device_nwkid - Update Status from %s to 'inDB' for NetworkID : %s" % (
            self.ListOfDevices[new_NwkId]["PreviousStatus"], new_NwkId))

    # We will also reset ReadAttributes
    if self.pluginconf.pluginConf["enableReadAttributes"]:
        if "ReadAttributes" in self.ListOfDevices[new_NwkId]:
            del self.ListOfDevices[new_NwkId]["ReadAttributes"]
        if STORE_CONFIGURE_REPORTING in self.ListOfDevices[new_NwkId]:
            del self.ListOfDevices[new_NwkId][STORE_CONFIGURE_REPORTING]
        self.ListOfDevices[new_NwkId]["Heartbeat"] = "0"

    request_flush_plugin_listofdevices(self)
    self.log.logging("PluginTools", "Status", "NetworkID: %s is replacing %s for object: %s" % (new_NwkId, old_NwkId, IEEE))
    return True


def drop_stale_nwkid(self, nwkid: str) -> str | None:
    """Remove nwkid from ListOfDevices only if its IEEE is reachable via another entry.
    
    Returns the surviving nwkid, or None if removal was unsafe.
    """
    device = self.ListOfDevices.get(nwkid)
    if not device:
        return None
    
    ieee = device.get("IEEE")
    if not ieee:
        return None

    surviving = next(
        (x for x in self.ListOfDevices
         if x != nwkid and self.ListOfDevices[x].get("IEEE") == ieee),
        None
    )

    if surviving:
        del self.ListOfDevices[nwkid]
    
    return surviving


def unregister_domoticz_widget(self, Devices, IEEE: str, Unit: int) -> bool:
    """Remove a Domoticz widget binding from a device's ClusterType.
    
    If no widget bindings remain on the device, mark it as 'Removed'.
    Returns True if the device was fully removed, False otherwise.
    """
    if IEEE not in self.IEEE2NWK:
        return False

    nwkid = self.IEEE2NWK[IEEE]
    device = self.ListOfDevices.get(nwkid)
    if not device:
        return False

    widget_id = str(domo_read_Device_Idx(self, Devices, IEEE, Unit))
    widget_name = domo_read_Name(self, Devices, IEEE, Unit)

    # Legacy v3.0.x: global ClusterType (not per-endpoint)
    if "ClusterType" in device:
        if widget_id in device["ClusterType"]:
            del device["ClusterType"][widget_id]
            self.log.logging("PluginTools", "Log",
                "unregister_domoticz_widget - removed widget %s from global ClusterType: %s"
                % (widget_id, device["ClusterType"]))

    # Current: per-endpoint ClusterType
    else:
        for ep in list(device.get("Ep", {}).keys()):
            ct = device["Ep"][ep].get("ClusterType", {})
            if widget_id in ct:
                del ct[widget_id]
                self.log.logging("PluginTools", "Log",
                    "unregister_domoticz_widget - removed widget %s from Ep %s ClusterType: %s"
                    % (widget_id, ep, ct))

    # Check if any widget bindings remain across all ClusterTypes
    def _has_bindings() -> bool:
        if device.get("ClusterType"):
            return True
        return any(
            device["Ep"][ep].get("ClusterType")
            for ep in device.get("Ep", {})
        )

    if _has_bindings():
        return False

    # No bindings left — mark device as fully removed
    device["Status"] = "Removed"
    self.adminWidgets.updateNotificationWidget(
        Devices, "Device fully removed %s with IEEE: %s" % (widget_name, IEEE)
    )
    self.log.logging("PluginTools", "Status",
        "Device %s with IEEE: %s fully removed from the system." % (widget_name, IEEE))
    return True


def reconcile_ieee_nwkid(self, nwkid: str, ieee: str) -> None:
    """Detect and correct a NWK ID change for a known IEEE address.
    
    Called when an IEEE is seen under a new NWK ID. Guards against
    coordinator address, unknown IEEE, and already-consistent state
    before delegating to remap_device_nwkid.
    """
    # Already consistent — IEEE and NWK ID both known and matching
    if ieee in self.IEEE2NWK and self.IEEE2NWK[ieee] == nwkid and nwkid in self.ListOfDevices:
        return  # Fully consistent, nothing to do

    # New NWK ID already exists in the device list — nothing to remap
    if nwkid in self.ListOfDevices:
        return

    # Never remap the coordinator
    if nwkid == "0000":
        return

    # Never remap if this IEEE belongs to the controller
    if self.ControllerIEEE and self.ControllerIEEE == ieee:
        return

    # IEEE unknown — nothing to remap from
    if ieee not in self.IEEE2NWK:
        return

    old_nwkid = self.IEEE2NWK[ieee]
    self.log.logging("PluginTools", "Log",
        "reconcile_ieee_nwkid - NWK ID changed for IEEE %s: %s → %s"
        % (ieee, old_nwkid, nwkid))
    remap_device_nwkid(self, nwkid, ieee, old_nwkid)

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
                        remap_device_nwkid(self, new_nwkid, ieee, old_nwkid)
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
    return remap_device_nwkid(self, nwkid, ieee, self.IEEE2NWK[ ieee ])

def loggingMessages(
    self,
    msgtype: str,
    sAddr: str | None = None,
    ieee: str | None = None,
    LQI: str | None = None,
    SQN: str | None = None,
) -> None:
    """Log a formatted device activity line, gated by enableStructuredDeviceTrace and debugMatchId.

    Requires at least one of sAddr or ieee to identify the device.
    LQI and SQN are expected as hex strings (e.g. '0x1F', '42').
    """
    if not self.pluginconf.pluginConf.get("enableStructuredDeviceTrace"):
        return

    # Resolve missing address from the other
    if sAddr is None and ieee in self.IEEE2NWK:
        sAddr = self.IEEE2NWK.get(ieee, "")
    if ieee is None and sAddr in self.ListOfDevices:
        ieee = self.ListOfDevices[sAddr].get("IEEE", "") if sAddr in self.ListOfDevices else ""

    _debug_match = self.pluginconf.pluginConf["MatchingNwkId"].lower()
    if _debug_match not in ("ffff", sAddr):
        return

    zdevname = ""
    if sAddr in self.ListOfDevices:
        zdevname = self.ListOfDevices[sAddr].get("ZDeviceName", "")

    lqi_int = int(LQI, 16) if LQI else 0
    sqn_str = SQN or ""

    self.log.logging(
        "PluginTools", "Log",
        "Device activity for | %4s | %16s | %4s | %16s | %3d | 0x%02s |"
        % (msgtype, zdevname, sAddr, ieee, lqi_int, sqn_str)
    )
    

def _get_device_conf(self, nwkid: str) -> dict | None:
    """Return the DeviceConf entry for a device, or None if unavailable."""
    device = self.ListOfDevices.get(nwkid)
    if not device:
        return None
    model = device.get("Model")
    return self.DeviceConf.get(model) if model else None


def is_fake_ep(self, nwkid: str, ep: str) -> bool:
    """Return True if the endpoint is declared as a FakeEp in DeviceConf."""
    conf = _get_device_conf(self, nwkid)
    if conf is None:
        return False
    fake_eps = conf.get("FakeEp")
    return fake_eps is not None and ep in fake_eps


def is_bind_ep(self, nwkid: str, ep: str) -> bool:
    """Return True if the endpoint is allowed for binding.
    
    Defaults to True when no bindEp restriction is configured.
    """
    conf = _get_device_conf(self, nwkid)
    if conf is None:
        return True  # No config → no restriction
    bind_eps = conf.get("bindEp")
    return bind_eps is None or ep in bind_eps