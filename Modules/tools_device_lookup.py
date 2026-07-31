#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""Device lookup helpers extracted from tools.py"""


def IEEEExist(self, ieee):
    """Check if the given IEEE address exists in the IEEE2NWK mapping."""
    return bool(ieee) and ieee in self.IEEE2NWK


def NwkIdExist(self, nwk_id):
    """Check if the given NwkId exists in ListOfDevices."""
    return nwk_id in self.ListOfDevices


def getSaddrfromIEEE(self, ieee):
    """Return the short address (sAddr) for a given IEEE, if found."""
    if not ieee:
        return ""

    return next(
        (
            saddr
            for saddr, device in self.ListOfDevices.items()
            if device.get("IEEE") == ieee
        ),
        "",
    )


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
    from Modules.tools_device_lifecycle import remap_device_nwkid

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
        existing_nwkid = self.IEEE2NWK[lookupIEEE]
        if existing_nwkid == lookupNwkId:
            # Everything fine, we have found it
            # and this is the same ShortId as the one existing
            return True

        if existing_nwkid not in self.ListOfDevices:
            # Should not happen
            # We have an entry in IEEE2NWK, but no corresponding
            # in ListOfDevices !!
            # Let's cleanup
            del self.IEEE2NWK[lookupIEEE]
            self.log.logging("PluginTools", "Error", "DeviceExist - Found inconsistency ! Not Device %s not found, while looking for %s (%s)" % (
                existing_nwkid, lookupIEEE, lookupNwkId))
            return False

        if 'Status' not in self.ListOfDevices[ existing_nwkid ]:
            # Should not happen
            # That seems not correct
            # We might have to do some cleanup here !
            # Cleanup
            # Delete the entry in IEEE2NWK as it will be recreated in Decode004d
            del self.IEEE2NWK[ lookupIEEE ]
            # Delete the all Data Structure
            del self.ListOfDevices[ existing_nwkid ]
            self.log.logging("PluginTools", "Error", "DeviceExist - Found inconsistency ! Not 'Status' attribute for Device %s, while looking for %s (%s)" % (
                existing_nwkid, lookupIEEE, lookupNwkId))
            return False

        if self.ListOfDevices[existing_nwkid]["Status"] in ("004d", "0045", "0043", "8045", "8043", "UNKNOWN", "UNKNOW", ):
            # We are in the discovery/provisioning process,
            # and the device got a new Short Id
            # we need to restart from the beginning and remove all existing datastructures.
            # In case we receive asynchronously messages (which should be possible), they must be
            # dropped in the corresponding Decodexxx function
            # Delete the entry in IEEE2NWK as it will be recreated in Decode004d
            del self.IEEE2NWK[lookupIEEE]
            # Delete the all Data Structure
            del self.ListOfDevices[existing_nwkid]
            self.log.logging("PluginTools", "Status", "DeviceExist - Device %s changed its ShortId: from %s to %s during provisioning. Restarting !" % (
                lookupIEEE, existing_nwkid, lookupNwkId))
            return False

        # At that stage, we have found an entry for the IEEE, but doesn't match
        # the coming Short Address lookupNwkId.
        # Most likely , device has changed its NwkId
        found = True
        remap_device_nwkid(self, lookupNwkId, lookupIEEE, existing_nwkid)

        self.adminWidgets.updateNotificationWidget( Devices, "Reconnect %s %s with %s" % (lookupNwkId, lookupIEEE, existing_nwkid))

    return found


def lookupForIEEE(self, nwkid, reconnect=False):
    # """
    # Purpose of this function is to search a Nwkid in the Neighbours table and find an IEEE
    # This is used when receiving a message from an unknown device !
    # """
    from Modules.tools_device_lifecycle import remap_device_nwkid

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
                remap_device_nwkid(self, nwkid, ieee, old_NwkId)
                self.log.logging("PluginTools", "Status", "lookupForIEEE found a matching IEEE: %s in the Router Neighbours %s with Nwkid: %s (old Nwkid was %s)" %(
                    ieee, key, nwkid, old_NwkId))
            return ieee
    return None


def lookupForParentDevice(self, nwkid=None, ieee=None):

    """
    Purpose is to find a router to which this device is connected to.
    the IEEE will be returned if found otherwise None
    """
    from Modules.tools_mac_capa import mainPoweredDevice

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
        nwkid = self.IEEE2NWK[ieee]

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


def getListOfEpForCluster(self, NwkId, SearchCluster):
    """
    NwkId: Device
    Cluster: Cluster for which we are looking for Ep

    return List of Ep where Cluster is found and at least ClusterType is not empty. (If ClusterType is empty, this
    indicate that there is no Widget associated and all informations in Ep are not used)
    In case ClusterType exists and not empty at Global Level, then just return the list of Ep for which Cluster is found
    """
    from Modules.tools_device_lifecycle import is_fake_ep

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
        # check that is not a Fake Ep
        if is_fake_ep(self, NwkId, Ep):
            continue

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

    ClusterList = []
    device = self.ListOfDevices.get(NWKID, {}).get("Ep", {}).get(Ep, {})
    ClusterList.extend( [cluster for cluster in device if cluster not in {"ClusterType", "Type", "ColorMode"} and cluster not in ClusterList] )
    return ClusterList


def getEpForCluster(self, nwkid, ClusterId, strict=False):
    """
    Retrieve a list of Endpoints (Ep) associated with a given ClusterId for a specific device.

    Args:
        nwkid (str): Network ID of the device.
        ClusterId (str or int): The cluster ID to search for.
        strict (bool): If True, returns None when no matching endpoint is found.
                       If False (default), returns an empty list.

    Returns:
        list[str] or None:
            - A list of endpoint strings (e.g., ['01', '02']) that include the ClusterId.
            - None if strict is True and no endpoint is found.
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