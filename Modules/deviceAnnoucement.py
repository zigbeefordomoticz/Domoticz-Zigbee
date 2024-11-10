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
    Module: deviceAnnoucement.py

    Description: 

"""


from time import time

from Modules.casaia import restart_plugin_reset_ModuleIRCode
from Modules.domoTools import lastSeenUpdate
from Modules.legrand_netatmo import legrand_refresh_battery_remote
from Modules.livolo import livolo_bind
from Modules.manufacturer_code import (PREFIX_MAC_LEN,
                                       PREFIX_MACADDR_LIVOLO)
from Modules.pairingProcess import (handle_device_specific_needs,
                                    interview_state_004d,
                                    zigbee_provision_device)
from Modules.pluginDbAttributes import STORE_CONFIGURE_REPORTING

from Modules.tools import (DeviceExist, IEEEExist, decodeMacCapa,
                           initDeviceInList, mainPoweredDevice, timeStamped)
from Modules.tuyaConst import TUYA_eTRV_MODEL
from Modules.tuyaSiren import tuya_sirene_registration
from Modules.tuyaTRV import tuya_eTRV_registration
from Zigbee.zdpCommands import zdp_node_descriptor_request


DELAY_BETWEEN_2_DEVICEANNOUCEMENT = 20

# V2
def device_annoucementv2(self, Devices, MsgData, MsgLQI):
    # There are 2 types of Device Annoucement the plugin can received from firmware >= 31a
    # (1) Device Annoucement with a JoinFlags and LQI set to 00. This one could be issued from:
    #     - device association (but transaction key not yet exchanged)
    #     - Rejoin request (for an already paired devices )
    #
    # (2) Device Annoucement with a valid LQI and not JoinFlag (shorter message)
    #     - Real Device Annoucement on which the plugin should trigger a discovery (if unknown )
    #     - Real Device Annoucement for Devices which do not send a Rejoin Request

    # The RejoinNetwork parameter indicating the method used to join the network. 
    # The parameter is 0x00 if the device joined through association.
    # The parameter is 0x01 if the device joined directly or rejoined using orphaning. 
    # The parameter is 0x02 if the device used NWK rejoin.

    # Decoding what we receive

    RejoinFlag = MsgData[22:24] if len(MsgData) > 22 else None
    NwkId = MsgData[:4]
    Ieee = MsgData[4:20]
    MacCapa = MsgData[20:22]

    newDeviceForPlugin = not IEEEExist(self, Ieee)

    self.log.logging(
        "DeviceAnnoucement",
        "Debug",
        "Decode004D V2 - Device Annoucement: NwkId: %s Ieee: %s MacCap: %s ReJoin: %s LQI: %s NewDevice: %s" % (NwkId, Ieee, MacCapa, RejoinFlag, MsgLQI, newDeviceForPlugin),
        NwkId,
    )

    now = time()
    if newDeviceForPlugin:
        if RejoinFlag and self.pluginconf.pluginConf["DropBadAnnoucement"]:
            self.log.logging(
                "DeviceAnnoucement",
                "Debug",
                "------------ > Adding Device Droping rejoin flag! %s %s %s)" % (NwkId, Ieee, RejoinFlag),
                NwkId,
            )
            return
        # Device do not exist, Rejoin Flag do not exist. This is the real Device Announcement, let's go
        if not DeviceExist(self, Devices, NwkId, Ieee):
            # We can create the device in Plugin Db, and start the Discovery process
            decode004d_new_devicev2(self, Devices, NwkId, Ieee, MacCapa, MsgData, MsgLQI, now)
            if "Announced" in self.ListOfDevices[NwkId]:
                del self.ListOfDevices[NwkId]["Announced"]
            self.log.logging(
                "DeviceAnnoucement",
                "Debug",
                "------------ > Adding a new device %s %s )" % (NwkId, Ieee),
                NwkId,
            )
        return

    # Existing Device
    if Ieee in self.IEEE2NWK:
        self.log.logging(  
            "DeviceAnnoucement", 
            "Debug", 
            "------------ > Existing device ShortId New: %s ShortId Old: %s" % (
                NwkId, self.IEEE2NWK[Ieee]), 
            NwkId, 
        )

    if RejoinFlag:
        # Just make sure to use the NwkId currently in the plugin DB and not the new one if exists
        # Looks like on 31c with Xiaomi, we got only that one , and not the True DeviceAnnoucement!
        store_annoucement(self, self.IEEE2NWK[Ieee], RejoinFlag, now)
        self.log.logging(
            "DeviceAnnoucement",
            "Debug",
            "------------ > Store device Rejoin Flag: %s droping" % RejoinFlag,
            NwkId,
        )
        return

    # Let's call DeviceExist. If needed it will reconnect with a new ShortId.
    if not DeviceExist(self, Devices, NwkId, Ieee):
        # Something wrong happen , most-likely the ShortId changed during the provisioning and we cannot handle that.
        # All Data structutre have been cleaned during the DeviceExist call.
        self.log.logging(
            "DeviceAnnoucement",
            "Error",
            "Something wrong on Device %s %s pairing process. (aborting)" % (NwkId, Ieee),
            NwkId,
        )
        return

    # When reaching that point Nwkid should have been created
    if NwkId not in self.ListOfDevices:
        self.log.logging(
            "DeviceAnnoucement",
            "Error",
            "Device Annoucement: NwkId: %s Ieee: %s MacCap: %s - Error has device seems not to be created !!!" % (NwkId, Ieee, MacCapa),
            NwkId,
        )
        return

    reseted_device = False
    self.log.logging("DeviceAnnoucement", "Debug", "device_annoucementv2 - Nwkid: %s Status: %s" %(NwkId,self.ListOfDevices[NwkId]["Status"] ), NwkId)
    if (
        ( "Status" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Status"] in ("Removed", "erasePDM", "provREQ", "Leave") ) 
        or ( "PreviousStatus" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["PreviousStatus"] in ("Removed", "erasePDM", "provREQ", "Leave") )
    ):
        self.log.logging("DeviceAnnoucement", "Debug", "--> Device reset, removing key Attributes", NwkId)
        reseted_device = True
        if "Bind" in self.ListOfDevices[NwkId]:
            del self.ListOfDevices[NwkId]["Bind"]
        if STORE_CONFIGURE_REPORTING in self.ListOfDevices[NwkId]:
            del self.ListOfDevices[NwkId][STORE_CONFIGURE_REPORTING]
        if "ReadAttributes" in self.ListOfDevices[NwkId]:
            del self.ListOfDevices[NwkId]["ReadAttributes"]
        if "Neighbours" in self.ListOfDevices[NwkId]:
            del self.ListOfDevices[NwkId]["Neighbours"]
        if "IAS" in self.ListOfDevices[NwkId]:
            del self.ListOfDevices[NwkId]["IAS"]
            for x in self.ListOfDevices[NwkId]["Ep"]:
                if "0500" in self.ListOfDevices[NwkId]["Ep"][ x ]:
                    del self.ListOfDevices[NwkId]["Ep"][ x ]["0500"]
                    self.ListOfDevices[NwkId]["Ep"][ x ]["0500"] = {}
                if "0502" in self.ListOfDevices[NwkId]["Ep"][ x ]:
                    del self.ListOfDevices[NwkId]["Ep"][ x ]["0502"]
                    self.ListOfDevices[NwkId]["Ep"][ x ]["0502"] = {}

        if "WriteAttributes" in self.ListOfDevices[NwkId]:
            del self.ListOfDevices[NwkId]["WriteAttributes"]

        self.ListOfDevices[NwkId]["Status"] = "inDB"

    if "ZDeviceName" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["ZDeviceName"] not in ("", {}):
        message = "Device Annoucement: %s NwkId: %s Ieee: %s MacCap: %s" % (
            self.ListOfDevices[NwkId]["ZDeviceName"],
            NwkId,
            Ieee,
            MacCapa,
        )
    else:
        message = "Device Annoucement: NwkId: %s Ieee: %s MacCap: %s" % (NwkId, Ieee, MacCapa)

    if mainPoweredDevice(self, NwkId) or self.ListOfDevices[NwkId]["Status"] != "inDB":
        self.log.logging("DeviceAnnoucement", "Status", message, NwkId)
        self.adminWidgets.updateNotificationWidget(Devices, message)

    # We are receiving the Real Device Annoucement. what to do
    if "Announced" not in self.ListOfDevices[NwkId]:
        # As exemple this is what happen when you switch Off and the On an Ikea Bulb, a Legrand remote switch.
        # No Re Join flag.
        # This is a known device
        # Do nothing, except for legrand we request battery level (as it is never repored)
        self.log.logging("DeviceAnnoucement", "Debug", "------------ > No Rejoin Flag seen, droping", NwkId)
        timeStamped(self, NwkId, 0x004D)
        lastSeenUpdate(self, Devices, NwkId=NwkId)

        legrand_refresh_battery_remote(self, NwkId)
        # CasaIA ( AC221, CAC221 )
        restart_plugin_reset_ModuleIRCode(self, NwkId)

        if mainPoweredDevice(self, NwkId):
            enforce_configure_reporting( self, NwkId)
            read_attributes_if_needed( self, NwkId)
            zdp_node_descriptor_request(self, NwkId)

        if reseted_device:
            self.log.logging("DeviceAnnoucement", "Debug", "--> Device reset, redoing provisioning", NwkId)
            # IAS Enrollment if required
            self.iaszonemgt.IAS_device_enrollment(NwkId)
            zigbee_provision_device(self, Devices, NwkId, 0, "inDB")
        return

    # Annouced is in the ListOfDevices[NwkId]
    if "TimeStamp" in self.ListOfDevices[NwkId]["Announced"] and (now < (self.ListOfDevices[NwkId]["Announced"]["TimeStamp"] + DELAY_BETWEEN_2_DEVICEANNOUCEMENT )):
        # If the TimeStamp is > DELAY_BETWEEN_2_DEVICEANNOUCEMENT, the Data are invalid and we will do process this.
        if "Rejoin" in self.ListOfDevices[NwkId]["Announced"] and self.ListOfDevices[NwkId]["Announced"]["Rejoin"] in ("01", "02") and self.ListOfDevices[NwkId]["Status"] != "Leave":
            self.log.logging(
                "DeviceAnnoucement",
                "Debug",
                "------------ > Rejoin Flag was set to 0x01 or 0x02, droping",
                NwkId,
            )
            timeStamped(self, NwkId, 0x004D)
            lastSeenUpdate(self, Devices, NwkId=NwkId)

            legrand_refresh_battery_remote(self, NwkId)
            if mainPoweredDevice(self, NwkId):
                enforce_configure_reporting( self, NwkId)
            restart_plugin_reset_ModuleIRCode(self, NwkId)
            read_attributes_if_needed( self, NwkId)
            zdp_node_descriptor_request(self, NwkId)

            if reseted_device:
                # IAS Enrollment if required
                self.iaszonemgt.IAS_device_enrollment(NwkId)
                zigbee_provision_device(self, Devices, NwkId, 0, "inDB")

            if self.ListOfDevices[NwkId]["Model"] in ("TS0601-sirene"):
                tuya_sirene_registration(self, NwkId)
                
            elif self.ListOfDevices[NwkId]["Model"] in (TUYA_eTRV_MODEL):
                tuya_eTRV_registration(self, NwkId, tuya_data_request=False)
                
            handle_device_specific_needs(self, Devices, NwkId)
            
            del self.ListOfDevices[NwkId]["Announced"]
            return
        
    elif RejoinFlag:
        # Most likely we receive a Device Annoucement which has not relation with the JoinFlag we have .
        self.log.logging(
            "Input",
            "Error",
            "Decode004D - Unexpected %s %s %s" % (NwkId, Ieee, RejoinFlag),
            NwkId,
        )

    for ep in list(self.ListOfDevices[NwkId]["Ep"].keys()):
        if "0004" in self.ListOfDevices[NwkId]["Ep"][ep] and self.groupmgt:
            self.groupmgt.ScanDevicesForGroupMemberShip( [ NwkId, ] )
            break

    # This should be the first one, let's take the information and drop it
    self.log.logging(
        "DeviceAnnoucement",
        "Debug",
        "------------ > Finally do the existing device and rebind if needed",
    )
    if reseted_device:
        # IAS Enrollment if required
        self.iaszonemgt.IAS_device_enrollment(NwkId)

    decode004d_existing_devicev2(self, Devices, NwkId, Ieee, MacCapa, MsgLQI, now)

    if "Announced" in self.ListOfDevices[NwkId]:
        del self.ListOfDevices[NwkId]["Announced"]


def decode004d_existing_devicev2(self, Devices, NwkId, MsgIEEE, MsgMacCapa, MsgLQI, now):
    # ############
    # Device exist, Reconnection has been done by DeviceExist()
    #

    # If needed fix MacCapa
    # deviceMacCapa = list(decodeMacCapa(ReArrangeMacCapaBasedOnModel(self, NwkId, MsgMacCapa)))

    self.log.logging(
        "DeviceAnnoucement",
        "Debug",
        "Decode004D - Already known device %s infos: %s, " % (NwkId, self.ListOfDevices[NwkId]),
        NwkId,
    )

    # If this is a rejoin after a leave, let's update the Status

    if self.ListOfDevices[NwkId]["Status"] == "Leave":
        self.log.logging("DeviceAnnoucement", "Debug", "Decode004D -  %s Status from Left to inDB" % (NwkId), NwkId)
        self.ListOfDevices[NwkId]["Status"] = "inDB"

    timeStamped(self, NwkId, 0x004D)
    lastSeenUpdate(self, Devices, NwkId=NwkId)
    self.ListOfDevices[NwkId]["PairingInProgress"] = True
    # If we reach this stage we are in a case of a Device Reset, or
    # we have no evidence and so will do the same
    # Reset the device Hearbeat, This should allow to trigger Read Request
    zigbee_provision_device(self, Devices, NwkId, 0, "inDB")

    self.configureReporting.processConfigureReporting(NwkId=NwkId)

    self.ListOfDevices[NwkId]["PairingInProgress"] = False

    # Let's check if this is a Schneider Wiser


def decode004d_new_devicev2(self, Devices, NwkId, MsgIEEE, MsgMacCapa, MsgData, MsgLQI, now):
    # New Device coming for provisioning
    # Decode Device Capabiities
    deviceMacCapa = list(decodeMacCapa(MsgMacCapa))

    # There is a dilem here as Livolo and Schneider Wiser share the same IEEE prefix.
    if (
        self.pluginconf.pluginConf["Livolo"]
        and MsgIEEE[: PREFIX_MAC_LEN] == PREFIX_MACADDR_LIVOLO
    ):
        livolo_bind(self, NwkId, "06")

    # New device comming. The IEEE is not known
    self.log.logging("DeviceAnnoucement", "Debug", "Decode004D - New Device %s %s" % (NwkId, MsgIEEE), NwkId)

    # I wonder if this code makes sense ? ( PP 02/05/2020 ), This should not happen!
    if MsgIEEE in self.IEEE2NWK:
        self.log.logging("DeviceAnnoucement", "Error", "Decode004d - New Device %s %s already exist in IEEE2NWK" % (NwkId, MsgIEEE))
        self.log.logging(
            "DeviceAnnoucement",
            "Debug",
            "Decode004d - self.IEEE2NWK[MsgIEEE] = %s with Status: %s"
            % (
                self.IEEE2NWK[MsgIEEE],
                self.ListOfDevices[self.IEEE2NWK[MsgIEEE]]["Status"],
            ),
        )
        if self.ListOfDevices[self.IEEE2NWK[MsgIEEE]]["Status"] != "inDB":
            self.log.logging(
                "DeviceAnnoucement",
                "Debug",
                "Decode004d - receiving a new Device Announced for a device in processing, drop it",
                NwkId,
            )
        return

    # 1- Create the entry in IEEE -
    self.IEEE2NWK[MsgIEEE] = NwkId

    # This code should not happen !( PP 02/05/2020 )
    if IEEEExist(self, MsgIEEE) and not DeviceExist(
        self, Devices, NwkId, MsgIEEE
    ):
        self.log.logging( "DeviceAnnoucement", "Error", "Decode004d - Paranoia .... NwkID: %s, IEEE: %s -> %s " % (
            NwkId, MsgIEEE, str(self.ListOfDevices[NwkId])), )
        return

    # 2- Create the Data Structutre
    initDeviceInList(self, NwkId)
    self.log.logging("DeviceAnnoucement", "Debug", "Decode004d - Looks like it is a new device sent by Zigate")
    self.CommiSSionning = True
    self.ListOfDevices[NwkId]["MacCapa"] = MsgMacCapa
    self.ListOfDevices[NwkId]["Capability"] = deviceMacCapa
    self.ListOfDevices[NwkId]["IEEE"] = MsgIEEE
    if "Announced" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Announced"] = {}
    self.ListOfDevices[NwkId]["Announced"]["TimeStamp"] = now

    if "Main Powered" in self.ListOfDevices[NwkId]["Capability"]:
        self.ListOfDevices[NwkId]["PowerSource"] = "Main"
    if "Full-Function Device" in self.ListOfDevices[NwkId]["Capability"]:
        self.ListOfDevices[NwkId]["LogicalType"] = "Router"
        self.ListOfDevices[NwkId]["DeviceType"] = "FFD"
    if "Reduced-Function Device" in self.ListOfDevices[NwkId]["Capability"]:
        self.ListOfDevices[NwkId]["LogicalType"] = "End Device"
        self.ListOfDevices[NwkId]["DeviceType"] = "RFD"

    self.log.logging("DeviceAnnoucement", "Log", "--> Adding device %s in self.DevicesInPairingMode" % NwkId)
    if self.webserver:
        self.webserver.add_element_to_devices_in_pairing_mode( NwkId)
        self.log.logging("DeviceAnnoucement", "Log", "--> %s" % str(self.webserver.DevicesInPairingMode))

    self.log.logging( "DeviceAnnoucement", "Debug", "Decode004D - %s Infos: %s" % (
        NwkId, self.ListOfDevices[NwkId]), NwkId, )
    

    interview_state_004d(self, NwkId, RIA=None, status=None)

    timeStamped(self, NwkId, 0x004D)
    lastSeenUpdate(self, Devices, NwkId=NwkId)


# Common
def store_annoucement(self, NwkId, MsgRejoinFlag, now):
    # ['Announced']['Rejoin'] = Rejoin Flag

    # ['Announced']['TimeStamp'] = When it has been provided
    if NwkId not in self.ListOfDevices:
        self.log.logging("DeviceAnnoucement", "Error", "store_annoucement - Unknown NwkId %s in Db: %s" % (NwkId, self.ListOfDevices.keys()))
        return

    if "Announced" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Announced"] = {}
    if not isinstance(self.ListOfDevices[NwkId]["Announced"], dict):
        self.ListOfDevices[NwkId]["Announced"] = {}

    if MsgRejoinFlag:
        self.ListOfDevices[NwkId]["Announced"]["Rejoin"] = MsgRejoinFlag

    self.ListOfDevices[NwkId]["Announced"]["TimeStamp"] = now


def read_attributes_if_needed( self, NwkId):
    # We receive a Device Annoucement
    # Let's check the status for a Switch or LvlControl
    if not mainPoweredDevice(self, NwkId):
        return
    # Will be forcing Read Attribute (if forcePollingAfterAction is enabled -default-)
    self.log.logging( "DeviceAnnoucement", "Debug", "read_attributes_if_needed %s" %NwkId)
    self.ListOfDevices[NwkId]["Heartbeat"] = "0"

def enforce_configure_reporting( self, NwkId):
    self.log.logging("DeviceAnnoucement", "Log", "Forcing a check of configure reporting after Device Annoucement on Main Powered device %s" %NwkId)
    if self.configureReporting:
        self.configureReporting.check_configuration_reporting_for_device( NwkId, force=True)