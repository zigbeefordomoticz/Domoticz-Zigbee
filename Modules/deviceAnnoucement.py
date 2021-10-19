import Domoticz
from time import time

from Modules.tools import (
    loggingMessages,
    decodeMacCapa,
    # ReArrangeMacCapaBasedOnModel,
    timeStamped,
    IEEEExist,
    DeviceExist,
    initDeviceInList,
    mainPoweredDevice,
)
from Modules.domoTools import lastSeenUpdate
from Modules.readAttributes import ReadAttributeRequest_0000, READ_ATTRIBUTES_REQUEST
from Modules.bindings import rebind_Clusters, reWebBind_Clusters
from Modules.pairingProcess import zigbee_provision_device, interview_state_004d
from Modules.schneider_wiser import schneider_wiser_registration, PREFIX_MACADDR_WIZER_LEGACY
from Modules.basicOutputs import sendZigateCmd
from Modules.livolo import livolo_bind
from Modules.legrand_netatmo import legrand_refresh_battery_remote
from Modules.lumi import enableOppleSwitch, setXiaomiVibrationSensitivity
from Modules.casaia import casaia_AC201_pairing
from Modules.tuyaSiren import tuya_sirene_registration
from Modules.tuyaTRV import tuya_eTRV_registration, TUYA_eTRV_MODEL
from Modules.zigateConsts import CLUSTERS_LIST

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

    RejoinFlag = None
    if len(MsgData) > 22:  # Firmware 3.1b
        RejoinFlag = MsgData[22:24]

    NwkId = MsgData[0:4]
    Ieee = MsgData[4:20]
    MacCapa = MsgData[20:22]

    newDeviceForPlugin = not IEEEExist(self, Ieee)

    self.log.logging(
        "Input",
        "Debug",
        "Decode004D V2 - Device Annoucement: NwkId: %s Ieee: %s MacCap: %s ReJoin: %s LQI: %s NewDevice: %s" % (NwkId, Ieee, MacCapa, RejoinFlag, MsgLQI, newDeviceForPlugin),
        NwkId,
    )

    now = time()
    if newDeviceForPlugin:
        if RejoinFlag and self.pluginconf.pluginConf["DropBadAnnoucement"]:
            self.log.logging(
                "Input",
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
                "Input",
                "Debug",
                "------------ > Adding a new device %s %s )" % (NwkId, Ieee),
                NwkId,
            )
        return

    # Existing Device
    # self.log.logging(  "Input", "Debug", "------------ > Existing device ShortId New: %s ShortId Old: %s" % (NwkId, self.IEEE2NWK[Ieee]), NwkId, )

    if RejoinFlag:
        # Just make sure to use the NwkId currently in the plugin DB and not the new one if exists
        # Looks like on 31c with Xiaomi, we got only that one , and not the True DeviceAnnoucement!
        store_annoucement(self, self.IEEE2NWK[Ieee], RejoinFlag, now)
        self.log.logging(
            "Input",
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
            "Input",
            "Error",
            "Something wrong on Device %s %s pairing process. (aborting)" % (NwkId, Ieee),
            NwkId,
        )
        return

    # When reaching that point Nwkid should have been created
    if NwkId not in self.ListOfDevices:
        self.log.logging(
            "Input",
            "Error",
            "Device Annoucement: NwkId: %s Ieee: %s MacCap: %s - Error has device seems not to be created !!!" % (NwkId, Ieee, MacCapa),
            NwkId,
        )
        return

    reseted_device = False

    if NwkId in self.ListOfDevices and "Status" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Status"] in ("erasePDM", "provREQ", "Left"):
        reseted_device = True
        if "Bind" in self.ListOfDevices[NwkId]:
            del self.ListOfDevices[NwkId]["Bind"]
        if "ConfigureReporting" in self.ListOfDevices[NwkId]:
            del self.ListOfDevices[NwkId]["ConfigureReporting"]
        if "ReadAttributes" in self.ListOfDevices[NwkId]:
            del self.ListOfDevices[NwkId]["ReadAttributes"]
        if "Neighbours" in self.ListOfDevices[NwkId]:
            del self.ListOfDevices[NwkId]["Neighbours"]
        if "IAS" in self.ListOfDevices[NwkId]:
            del self.ListOfDevices[NwkId]["IAS"]
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
        self.log.logging("Input", "Status", message, NwkId)
        self.adminWidgets.updateNotificationWidget(Devices, message)

    # We are receiving the Real Device Annoucement. what to do
    if "Announced" not in self.ListOfDevices[NwkId]:
        # As exemple this is what happen when you switch Off and the On an Ikea Bulb, a Legrand remote switch.
        # No Re Join flag.
        # This is a known device
        # Do nothing, except for legrand we request battery level (as it is never repored)
        self.log.logging("Input", "Debug", "------------ > No Rejoin Flag seen, droping", NwkId)
        timeStamped(self, NwkId, 0x004D)
        lastSeenUpdate(self, Devices, NwkId=NwkId)

        legrand_refresh_battery_remote(self, NwkId)

        if reseted_device:
            zigbee_provision_device(self, Devices, NwkId, 0, "inDB")

        return

    # Annouced is in the ListOfDevices[NwkId]
    if "TimeStamp" in self.ListOfDevices[NwkId]["Announced"] and (now < (self.ListOfDevices[NwkId]["Announced"]["TimeStamp"] + DELAY_BETWEEN_2_DEVICEANNOUCEMENT )):
        # If the TimeStamp is > DELAY_BETWEEN_2_DEVICEANNOUCEMENT, the Data are invalid and we will do process this.
        if "Rejoin" in self.ListOfDevices[NwkId]["Announced"] and self.ListOfDevices[NwkId]["Announced"]["Rejoin"] in ("01", "02") and self.ListOfDevices[NwkId]["Status"] != "Left":
            self.log.logging(
                "Input",
                "Debug",
                "------------ > Rejoin Flag was set to 0x01 or 0x02, droping",
                NwkId,
            )
            timeStamped(self, NwkId, 0x004D)
            lastSeenUpdate(self, Devices, NwkId=NwkId)

            legrand_refresh_battery_remote(self, NwkId)

            if reseted_device:
                zigbee_provision_device(self, Devices, NwkId, 0, "inDB")

            if self.ListOfDevices[NwkId]["Model"] in ("TS0601-sirene"):
                tuya_sirene_registration(self, NwkId)
            elif self.ListOfDevices[NwkId]["Model"] in (TUYA_eTRV_MODEL):
                tuya_eTRV_registration(self, NwkId, False)
            del self.ListOfDevices[NwkId]["Announced"]
            return
    else:
        # Most likely we receive a Device Annoucement which has not relation with the JoinFlag we have .
        if RejoinFlag:
            self.log.logging(
                "Input",
                "Error",
                "Decode004D - Unexpected %s %s %s" % (NwkId, Ieee, RejoinFlag),
                NwkId,
            )

    for ep in list(self.ListOfDevices[NwkId]["Ep"].keys()):
        if "0004" in self.ListOfDevices[NwkId]["Ep"][ep] and self.groupmgt:
            self.groupmgt.ScanDevicesForGroupMemberShip(
                [
                    NwkId,
                ]
            )
            break

    # This should be the first one, let's take the information and drop it
    self.log.logging(
        "Input",
        "Debug",
        "------------ > Finally do the existing device and rebind if needed",
    )
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
        "Input",
        "Debug",
        "Decode004D - Already known device %s infos: %s, " % (NwkId, self.ListOfDevices[NwkId]),
        NwkId,
    )

    # If this is a rejoin after a leave, let's update the Status

    if self.ListOfDevices[NwkId]["Status"] == "Left":
        self.log.logging("Input", "Debug", "Decode004D -  %s Status from Left to inDB" % (NwkId), NwkId)
        self.ListOfDevices[NwkId]["Status"] = "inDB"

    timeStamped(self, NwkId, 0x004D)
    lastSeenUpdate(self, Devices, NwkId=NwkId)
    self.ListOfDevices[NwkId]["PairingInProgress"] = True
    # If we reach this stage we are in a case of a Device Reset, or
    # we have no evidence and so will do the same
    # Reset the device Hearbeat, This should allow to trigger Read Request
    zigbee_provision_device(self, Devices, NwkId, 0, "inDB")

    self.configureReporting.processConfigureReporting(NWKID=NwkId)

    self.ListOfDevices[NwkId]["PairingInProgress"] = False

    # Let's check if this is a Schneider Wiser


def decode004d_new_devicev2(self, Devices, NwkId, MsgIEEE, MsgMacCapa, MsgData, MsgLQI, now):
    # New Device coming for provisioning
    # Decode Device Capabiities
    deviceMacCapa = list(decodeMacCapa(MsgMacCapa))

    # There is a dilem here as Livolo and Schneider Wiser share the same IEEE prefix.
    if self.pluginconf.pluginConf["Livolo"]:
        PREFIX_MACADDR_LIVOLO = "00124b00"
        if MsgIEEE[0 : len(PREFIX_MACADDR_LIVOLO)] == PREFIX_MACADDR_LIVOLO:
            livolo_bind(self, NwkId, "06")

    # New device comming. The IEEE is not known
    self.log.logging("Input", "Debug", "Decode004D - New Device %s %s" % (NwkId, MsgIEEE), NwkId)

    # I wonder if this code makes sense ? ( PP 02/05/2020 ), This should not happen!
    if MsgIEEE in self.IEEE2NWK:
        Domoticz.Error("Decode004d - New Device %s %s already exist in IEEE2NWK" % (NwkId, MsgIEEE))
        self.log.logging(
            "Pairing",
            "Debug",
            "Decode004d - self.IEEE2NWK[MsgIEEE] = %s with Status: %s"
            % (
                self.IEEE2NWK[MsgIEEE],
                self.ListOfDevices[self.IEEE2NWK[MsgIEEE]]["Status"],
            ),
        )
        if self.ListOfDevices[self.IEEE2NWK[MsgIEEE]]["Status"] != "inDB":
            self.log.logging(
                "Input",
                "Debug",
                "Decode004d - receiving a new Device Announced for a device in processing, drop it",
                NwkId,
            )
        return

    # 1- Create the entry in IEEE -
    self.IEEE2NWK[MsgIEEE] = NwkId

    # This code should not happen !( PP 02/05/2020 )
    if IEEEExist(self, MsgIEEE):
        # we are getting a dupplicate. Most-likely the Device is existing and we have to reconnect.
        if not DeviceExist(self, Devices, NwkId, MsgIEEE):
            self.log.logging(
                "Pairing",
                "Error",
                "Decode004d - Paranoia .... NwkID: %s, IEEE: %s -> %s " % (NwkId, MsgIEEE, str(self.ListOfDevices[NwkId])),
            )
            return

    # 2- Create the Data Structutre
    initDeviceInList(self, NwkId)
    self.log.logging("Pairing", "Debug", "Decode004d - Looks like it is a new device sent by Zigate")
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

    self.log.logging("Pairing", "Log", "--> Adding device %s in self.DevicesInPairingMode" % NwkId)
    if NwkId not in self.DevicesInPairingMode:
        self.DevicesInPairingMode.append(NwkId)
    self.log.logging("Pairing", "Log", "--> %s" % str(self.DevicesInPairingMode))

    self.log.logging(
        "Input",
        "Debug",
        "Decode004D - %s Infos: %s" % (NwkId, self.ListOfDevices[NwkId]),
        NwkId,
    )
    interview_state_004d(self, NwkId, RIA=None, status=None)

    timeStamped(self, NwkId, 0x004D)
    lastSeenUpdate(self, Devices, NwkId=NwkId)


# ------------------- V1 -------------------
def device_annoucementv1(self, Devices, MsgData, MsgLQI):

    NwkId = MsgData[0:4]
    MsgIEEE = MsgData[4:20]
    MsgMacCapa = MsgData[20:22]
    MsgRejoinFlag = None
    newShortId = False

    if len(MsgData) > 22:  # Firmware 3.1b
        MsgRejoinFlag = MsgData[22:24]

    self.log.logging(
        "Input",
        "Debug",
        "Decode004D - Device Annoucement: NwkId: %s Ieee: %s MacCap: %s ReJoin: %s LQI: %s" % (NwkId, MsgIEEE, MsgMacCapa, MsgRejoinFlag, MsgLQI),
        NwkId,
    )

    if IEEEExist(self, MsgIEEE):
        # This device is known
        newShortId = self.IEEE2NWK[MsgIEEE] != NwkId
        self.log.logging(
            "Input",
            "Debug",
            "------>  Known device: NwkId: %s Ieee: %s MacCap: %s ReJoin: %s LQI: %s newShortId: %s" % (NwkId, MsgIEEE, MsgMacCapa, MsgRejoinFlag, MsgLQI, newShortId),
            NwkId,
        )

        if self.FirmwareVersion and int(self.FirmwareVersion, 16) > 0x031B and MsgRejoinFlag is None:
            # Device does exist, we will rely on ZPS_EVENT_NWK_NEW_NODE_HAS_JOINED in order to have the JoinFlag
            self.log.logging(
                "Input",
                "Debug",
                "------> Droping no rejoin flag! %s %s )" % (NwkId, MsgIEEE),
                NwkId,
            )
            timeStamped(self, NwkId, 0x004D)
            lastSeenUpdate(self, Devices, NwkId=NwkId)
            return

        if NwkId in self.ListOfDevices and self.ListOfDevices[NwkId]["Status"] in (
            "004d",
            "0045",
            "0043",
            "8045",
            "8043",
        ):
            # In case we receive a Device Annoucement we are alreday doing the provisioning.
            # Same IEEE and same Short Address.
            # We will drop the message, as there is no reason to process it.
            self.log.logging(
                "Input",
                "Debug",
                "------> Droping (provisioning in progress) Status: %s" % self.ListOfDevices[NwkId]["Status"],
                NwkId,
            )
            return

    now = time()
    loggingMessages(self, "004D", NwkId, MsgIEEE, int(MsgLQI, 16), None)

    # Test if Device Exist, if Left then we can reconnect, otherwise initialize the ListOfDevice for this entry
    if DeviceExist(self, Devices, NwkId, MsgIEEE):
        decode004d_existing_devicev1(
            self,
            Devices,
            NwkId,
            MsgIEEE,
            MsgMacCapa,
            MsgRejoinFlag,
            newShortId,
            MsgLQI,
            now,
        )
    else:
        self.log.logging(
            "Pairing",
            "Status",
            "Device Announcement Addr: %s, IEEE: %s LQI: %s" % (NwkId, MsgIEEE, int(MsgLQI, 16)),
        )
        decode004d_new_devicev1(self, Devices, NwkId, MsgIEEE, MsgMacCapa, MsgRejoinFlag, MsgData, MsgLQI, now)


def decode004d_existing_devicev1(self, Devices, MsgSrcAddr, MsgIEEE, MsgMacCapa, MsgRejoinFlag, newShortId, MsgLQI, now):
    # ############
    # Device exist, Reconnection has been done by DeviceExist()
    #

    # If needed fix MacCapa
    # deviceMacCapa = list(decodeMacCapa(ReArrangeMacCapaBasedOnModel(self, MsgSrcAddr, MsgMacCapa)))

    self.log.logging(
        "Input",
        "Debug",
        "Decode004D - Already known device %s infos: %s, Change ShortID: %s " % (MsgSrcAddr, self.ListOfDevices[MsgSrcAddr], newShortId),
        MsgSrcAddr,
    )
    if "Announced" not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]["Announced"] = {}
    if not isinstance(self.ListOfDevices[MsgSrcAddr]["Announced"], dict):
        self.ListOfDevices[MsgSrcAddr]["Announced"] = {}

    self.ListOfDevices[MsgSrcAddr]["Announced"]["Rejoin"] = str(MsgRejoinFlag)
    self.ListOfDevices[MsgSrcAddr]["Announced"]["newShortId"] = newShortId

    if MsgRejoinFlag in ("01", "02") and self.ListOfDevices[MsgSrcAddr]["Status"] != "Left":
        self.log.logging(
            "Input",
            "Debug",
            "--> drop packet for %s due to  Rejoining network as %s, LQI: %s" % (MsgSrcAddr, MsgRejoinFlag, int(MsgLQI, 16)),
            MsgSrcAddr,
        )
        if "Announced" not in self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]["Announced"] = {}
        self.ListOfDevices[MsgSrcAddr]["Announced"]["TimeStamp"] = now

        timeStamped(self, MsgSrcAddr, 0x004D)
        lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
        legrand_refresh_battery_remote(self, MsgSrcAddr)
        return

    # If we got a recent Annoucement in the last DELAY_BETWEEN_2_DEVICEANNOUCEMENT secondes, then we drop the new one
    if "Announced" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Status"] != "Left":
        if "TimeStamp" in self.ListOfDevices[MsgSrcAddr]["Announced"]:
            if now < self.ListOfDevices[MsgSrcAddr]["Announced"]["TimeStamp"] + DELAY_BETWEEN_2_DEVICEANNOUCEMENT:
                # Looks like we have a duplicate Device Announced in less than DELAY_BETWEEN_2_DEVICEANNOUCEMENT
                self.log.logging(
                    "Input",
                    "Debug",
                    "Decode004D - Duplicate Device Annoucement for %s -> Drop" % (MsgSrcAddr),
                    MsgSrcAddr,
                )
                return

    if MsgSrcAddr in self.ListOfDevices:
        if "ZDeviceName" in self.ListOfDevices[MsgSrcAddr]:
            self.log.logging(
                "Pairing",
                "Status",
                "Device Announcement: %s(%s, %s) Join Flag: %s LQI: %s ChangeShortID: %s "
                % (
                    self.ListOfDevices[MsgSrcAddr]["ZDeviceName"],
                    MsgSrcAddr,
                    MsgIEEE,
                    MsgRejoinFlag,
                    int(MsgLQI, 16),
                    newShortId,
                ),
            )
        else:
            self.log.logging(
                "Pairing",
                "Status",
                "Device Announcement Addr: %s, IEEE: %s Join Flag: %s LQI: %s ChangeShortID: %s" % (MsgSrcAddr, MsgIEEE, MsgRejoinFlag, int(MsgLQI, 16), newShortId),
            )

    if "Announced" not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]["Announced"] = {}
    self.ListOfDevices[MsgSrcAddr]["Announced"]["TimeStamp"] = now
    # If this is a rejoin after a leave, let's update the Status

    if self.ListOfDevices[MsgSrcAddr]["Status"] == "Left":
        self.log.logging(
            "Input",
            "Debug",
            "Decode004D -  %s Status from Left to inDB" % (MsgSrcAddr),
            MsgSrcAddr,
        )
        self.ListOfDevices[MsgSrcAddr]["Status"] = "inDB"

    timeStamped(self, MsgSrcAddr, 0x004D)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)

    # If we reach this stage we are in a case of a Device Reset, or
    # we have no evidence and so will do the same
    # Reset the device Hearbeat, This should allow to trigger Read Request
    self.ListOfDevices[MsgSrcAddr]["Heartbeat"] = 0

    for tmpep in list(self.ListOfDevices[MsgSrcAddr]["Ep"].keys()):
        if "0500" in self.ListOfDevices[MsgSrcAddr]["Ep"][tmpep]:
            # We found a Cluster 0x0500 IAS. May be time to start the IAS Zone process
            self.log.logging(
                "Input",
                "Debug",
                "Decode004D - IAS Zone controler setting %s" % (MsgSrcAddr),
                MsgSrcAddr,
            )
            self.iaszonemgt.IASZone_triggerenrollement(MsgSrcAddr, tmpep)
            if "0502" in self.ListOfDevices[MsgSrcAddr]["Ep"][tmpep]:
                self.log.logging(
                    "Input",
                    "Debug",
                    "Decode004D - IAS WD enrolment %s" % (MsgSrcAddr),
                    MsgSrcAddr,
                )
                self.iaszonemgt.IASWD_enroll(MsgSrcAddr, tmpep)
            break

    if self.pluginconf.pluginConf["allowReBindingClusters"]:
        self.log.logging(
            "Input",
            "Debug",
            "Decode004D - Request rebind clusters for %s" % (MsgSrcAddr),
            MsgSrcAddr,
        )
        rebind_Clusters(self, MsgSrcAddr)
        reWebBind_Clusters(self, MsgSrcAddr)

    if self.ListOfDevices[MsgSrcAddr]["Model"] in (
        "lumi.remote.b686opcn01",
        "lumi.remote.b486opcn01",
        "lumi.remote.b286opcn01",
        "lumi.remote.b686opcn01-bulb",
        "lumi.remote.b486opcn01-bulb",
        "lumi.remote.b286opcn01-bulb",
    ):
        self.log.logging("Input", "Log", "---> Calling enableOppleSwitch %s" % MsgSrcAddr, MsgSrcAddr)
        enableOppleSwitch(self, MsgSrcAddr)

    # As we are redo bind, we need to redo the Configure Reporting
    if "ConfigureReporting" in self.ListOfDevices[MsgSrcAddr]:
        del self.ListOfDevices[MsgSrcAddr]["ConfigureReporting"]

    self.configureReporting.processConfigureReporting(NWKID=MsgSrcAddr)

    # Let's take the opportunity to trigger some request/adjustement / NOT SURE IF THIS IS GOOD/IMPORTANT/NEEDED
    self.log.logging(
        "Input",
        "Debug",
        "Decode004D - Request attribute 0x0000 %s" % (MsgSrcAddr),
        MsgSrcAddr,
    )
    ReadAttributeRequest_0000(self, MsgSrcAddr)
    sendZigateCmd(self, "0042", str(MsgSrcAddr), ackIsDisabled=True)

    # Let's check if this is a Schneider Wiser
    if MsgIEEE[0 : len(PREFIX_MACADDR_WIZER_LEGACY)] == PREFIX_MACADDR_WIZER_LEGACY:
        if "Manufacturer" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Manufacturer"] == "105e":
            schneider_wiser_registration(self, Devices, MsgSrcAddr)


def decode004d_new_devicev1(self, Devices, MsgSrcAddr, MsgIEEE, MsgMacCapa, MsgRejoinFlag, MsgData, MsgLQI, now):
    # New Device coming for provisioning
    # Decode Device Capabiities
    deviceMacCapa = list(decodeMacCapa(MsgMacCapa))

    # There is a dilem here as Livolo and Schneider Wiser share the same IEEE prefix.
    if self.pluginconf.pluginConf["Livolo"]:
        PREFIX_MACADDR_LIVOLO = "00124b00"
        if MsgIEEE[0 : len(PREFIX_MACADDR_LIVOLO)] == PREFIX_MACADDR_LIVOLO:
            livolo_bind(self, MsgSrcAddr, "06")

    # New device comming. The IEEE is not known
    self.log.logging(
        "Input",
        "Debug",
        "Decode004D - New Device %s %s" % (MsgSrcAddr, MsgIEEE),
        MsgSrcAddr,
    )

    # I wonder if this code makes sense ? ( PP 02/05/2020 ), This should not happen!
    if MsgIEEE in self.IEEE2NWK:
        Domoticz.Error("Decode004d - New Device %s %s already exist in IEEE2NWK" % (MsgSrcAddr, MsgIEEE))
        self.log.logging(
            "Pairing",
            "Debug",
            "Decode004d - self.IEEE2NWK[MsgIEEE] = %s with Status: %s"
            % (
                self.IEEE2NWK[MsgIEEE],
                self.ListOfDevices[self.IEEE2NWK[MsgIEEE]]["Status"],
            ),
        )
        if self.ListOfDevices[self.IEEE2NWK[MsgIEEE]]["Status"] != "inDB":
            self.log.logging(
                "Input",
                "Debug",
                "Decode004d - receiving a new Device Announced for a device in processing, drop it",
                MsgSrcAddr,
            )
        return

    # 1- Create the entry in IEEE -
    self.IEEE2NWK[MsgIEEE] = MsgSrcAddr

    # This code should not happen !( PP 02/05/2020 )
    if IEEEExist(self, MsgIEEE):
        # we are getting a dupplicate. Most-likely the Device is existing and we have to reconnect.
        if not DeviceExist(self, Devices, MsgSrcAddr, MsgIEEE):
            self.log.logging(
                "Pairing",
                "Error",
                "Decode004d - Paranoia .... NwkID: %s, IEEE: %s -> %s " % (MsgSrcAddr, MsgIEEE, str(self.ListOfDevices[MsgSrcAddr])),
            )
            return

    # 2- Create the Data Structutre
    initDeviceInList(self, MsgSrcAddr)
    self.log.logging("Pairing", "Debug", "Decode004d - Looks like it is a new device sent by Zigate")
    self.CommiSSionning = True
    self.ListOfDevices[MsgSrcAddr]["MacCapa"] = MsgMacCapa
    self.ListOfDevices[MsgSrcAddr]["Capability"] = deviceMacCapa
    self.ListOfDevices[MsgSrcAddr]["IEEE"] = MsgIEEE

    if "Announced" not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]["Announced"] = {}
    self.ListOfDevices[MsgSrcAddr]["Announced"]["TimeStamp"] = now

    if "Main Powered" in self.ListOfDevices[MsgSrcAddr]["Capability"]:
        self.ListOfDevices[MsgSrcAddr]["PowerSource"] = "Main"
    if "Full-Function Device" in self.ListOfDevices[MsgSrcAddr]["Capability"]:
        self.ListOfDevices[MsgSrcAddr]["LogicalType"] = "Router"
        self.ListOfDevices[MsgSrcAddr]["DeviceType"] = "FFD"
    if "Reduced-Function Device" in self.ListOfDevices[MsgSrcAddr]["Capability"]:
        self.ListOfDevices[MsgSrcAddr]["LogicalType"] = "End Device"
        self.ListOfDevices[MsgSrcAddr]["DeviceType"] = "RFD"

    self.log.logging("Pairing", "Log", "--> Adding device %s in self.DevicesInPairingMode" % MsgSrcAddr)
    if MsgSrcAddr not in self.DevicesInPairingMode:
        self.DevicesInPairingMode.append(MsgSrcAddr)
    self.log.logging("Pairing", "Log", "--> %s" % str(self.DevicesInPairingMode))

    interview_state_004d(self, MsgSrcAddr, RIA=None, status=None)

    # PREFIX_IEEE_XIAOMI = "00158d000"
    # if MsgIEEE[0: len(PREFIX_IEEE_XIAOMI)] == PREFIX_IEEE_XIAOMI:
    #    ReadAttributeRequest_0000(self, MsgSrcAddr, fullScope=False)  # In order to request Model Name
    #
    # if self.pluginconf.pluginConf["enableSchneiderWiser"]:
    #    ReadAttributeRequest_0000(self, MsgSrcAddr, fullScope=False)  # In order to request Model Name
    #
    # self.log.logging("Pairing", "Debug", "Decode004d - Request End Point List ( 0x0045 )")
    # self.ListOfDevices[MsgSrcAddr]["Heartbeat"] = "0"
    # self.ListOfDevices[MsgSrcAddr]["Status"] = "0045"

    # sendZigateCmd(self, "0045", str(MsgSrcAddr))  # Request list of EPs
    self.log.logging(
        "Input",
        "Debug",
        "Decode004D - %s Infos: %s" % (MsgSrcAddr, self.ListOfDevices[MsgSrcAddr]),
        MsgSrcAddr,
    )
    timeStamped(self, MsgSrcAddr, 0x004D)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)


# Common
def store_annoucement(self, NwkId, MsgRejoinFlag, now):
    # ['Announced']['Rejoin'] = Rejoin Flag

    # ['Announced']['TimeStamp'] = When it has been provided
    if NwkId not in self.ListOfDevices:
        self.log.logging("Input", "Error", "store_annoucement - Unknown NwkId %s in Db: %s" % (NwkId, self.ListOfDevices.keys()))
        return

    if "Announced" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Announced"] = {}
    if not isinstance(self.ListOfDevices[NwkId]["Announced"], dict):
        self.ListOfDevices[NwkId]["Announced"] = {}

    if MsgRejoinFlag:
        self.ListOfDevices[NwkId]["Announced"]["Rejoin"] = MsgRejoinFlag

    self.ListOfDevices[NwkId]["Announced"]["TimeStamp"] = now
