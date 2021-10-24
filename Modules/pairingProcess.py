#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: pairingProcess.py

    Description: Manage all actions done during the onHeartbeat() call

"""

import Domoticz
import json


from Classes.LoggingManagement import LoggingManagement

from Modules.schneider_wiser import schneider_wiser_registration, wiser_home_lockout_thermostat, PREFIX_MACADDR_WIZER_LEGACY, WISER_LEGACY_MODEL_NAME_PREFIX

from Modules.bindings import unbindDevice, bindDevice, rebind_Clusters, reWebBind_Clusters
from Modules.basicOutputs import sendZigateCmd, identifyEffect, getListofAttribute, write_attribute, read_attribute

from Modules.readAttributes import READ_ATTRIBUTES_REQUEST, ReadAttributeRequest_0000, ReadAttributeRequest_0300

from Modules.lumi import enableOppleSwitch, setXiaomiVibrationSensitivity
from Modules.livolo import livolo_bind
from Modules.orvibo import OrviboRegistration
from Modules.profalux import profalux_fake_deviceModel
from Modules.domoCreate import CreateDomoDevice
from Modules.tools import get_and_inc_SQN, getListOfEpForCluster, is_fake_ep
from Modules.zigateConsts import CLUSTERS_LIST
from Modules.casaia import casaia_pairing
from Modules.thermostats import thermostat_Calibration
from Modules.tuya import tuya_registration
from Modules.tuyaSiren import tuya_sirene_registration
from Modules.tuyaTools import tuya_TS0121_registration
from Modules.tuyaTRV import tuya_eTRV_registration, TUYA_eTRV_MODEL
from Modules.pollControl import poll_set_long_poll_interval


def processNotinDBDevices(self, Devices, NWKID, status, RIA):

    # Starting V 4.1.x
    # 0x0043 / List of EndPoints is requested at the time we receive the End Device Annocement
    # 0x0045 / EndPoint Description is requested at the time we recice the List of EPs.
    # In case Model is defined and is in DeviceConf, we will short cut the all process and go to the Widget creation
    if status in ("UNKNOW", "erasePDM", "provREQ"):
        return

    HB_ = int(self.ListOfDevices[NWKID]["Heartbeat"])
    self.log.logging(
        "Pairing",
        "Debug",
        "processNotinDBDevices - NWKID: %s, Status: %s, RIA: %s, HB_: %s " % (NWKID, status, RIA, HB_),
    )

    if status not in ("004d", "0043", "0045", "8045", "8043") and "Model" in self.ListOfDevices[NWKID]:
        return

    if "PairingInProgress" not in self.ListOfDevices[NWKID] or not self.ListOfDevices[NWKID]["PairingInProgress"]:
        self.ListOfDevices[NWKID]["PairingInProgress"] = True

    knownModel = False
    if self.ListOfDevices[NWKID]["Model"] not in ({}, ""):
        self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s Model Name: %s" % (RIA, NWKID, self.ListOfDevices[NWKID]["Model"]))
        # Let's check if this Model is known
        if self.ListOfDevices[NWKID]["Model"] in self.DeviceConf:
            knownModel = True
            status = "createDB"  # Fast track

    if knownModel and self.ListOfDevices[NWKID]["Model"] == "TI0001":
        # https://zigate.fr/forum/topic/livolo-compatible-zigbee/#postid-596
        livolo_bind(self, NWKID, "06")

    if knownModel and "NoDeviceInterview" in self.DeviceConf[self.ListOfDevices[NWKID]["Model"]] and self.DeviceConf[self.ListOfDevices[NWKID]["Model"]]["NoDeviceInterview"]:
        status = "CreateDB"

    if status == "8043":  # We have at least receive 1 EndPoint
        status = interview_state_8043(self, NWKID, RIA, knownModel, status)
        if status != "CreateDB" and RIA < 2:
            return

    if knownModel and RIA > 3 and status not in ("UNKNOW", "inDB"):
        # We have done several retry to get Ep ... but we known the Model
        self.log.logging(
            "Pairing",
            "Debug",
            "processNotinDB - Try several times to get all informations, let's use the Model now " + str(NWKID),
        )
        status = "createDB"

    #if status == "8043" and request_node_descriptor( self, NWKID, RIA=None, status=None):
    #    # We have to request the node_descriptor
    #    return

    if status in ("createDB", "8043"):
        # We do a request_node_description in case of unknown.
        request_node_descriptor( self, NWKID, RIA=None, status=None)
        interview_state_createDB(self, Devices, NWKID, RIA, status)

    if status != "createDB":
        if HB_ > 2 and not knownModel and status in ("004d", "0045"):
            # We will re-request EndPoint List ( 0x0045)
            interview_state_004d(self, NWKID, RIA, status)

        elif HB_ > 1 and not knownModel and status in ("0043",):
            # We will re-request EndPoint List ( 0x0043)
            interview_state_8045(self, NWKID, RIA, status)

        elif RIA > 4 and status not in ("UNKNOW", "inDB"):  # We have done several retry
            status = interview_timeout(self, Devices, NWKID, RIA, status)


def interview_state_004d(self, NWKID, RIA=None, status=None):
    self.log.logging(
        "Pairing",
        "Debug",
        "interview_state_004d - NWKID: %s, Status: %s, RIA: %s,"
        % (
            NWKID,
            status,
            RIA,
        ),
    )
    self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s %s" % (RIA, NWKID, status))
    if RIA:
        self.ListOfDevices[NWKID]["RIA"] = str(RIA + 1)
    self.ListOfDevices[NWKID]["Heartbeat"] = "0"
    self.ListOfDevices[NWKID]["Status"] = "0045"

    MsgIEEE = None
    if "IEEE" in self.ListOfDevices[NWKID]:
        MsgIEEE = self.ListOfDevices[NWKID]["IEEE"]

    PREFIX_IEEE_XIAOMI = "00158d000"
    PREFIX_IEEE_OPPLE = "04cf8cdf3"
    if MsgIEEE and MsgIEEE[0 : len(PREFIX_IEEE_XIAOMI)] == PREFIX_IEEE_XIAOMI or MsgIEEE[0 : len(PREFIX_IEEE_OPPLE)] == PREFIX_IEEE_OPPLE:
        ReadAttributeRequest_0000(self, NWKID, fullScope=False)  # In order to request Model Name

    PREFIX_IEEE_WISER = "00124b000"
    if self.pluginconf.pluginConf["enableSchneiderWiser"] and MsgIEEE[0 : len(PREFIX_IEEE_WISER)] == PREFIX_IEEE_WISER:
        ReadAttributeRequest_0000(self, NWKID, fullScope=False)  # In order to request Model Name

    sendZigateCmd(self, "0045", str(NWKID))
    return "0045"


def interview_state_8043(self, NWKID, RIA, knownModel, status):
    self.log.logging(
        "Pairing",
        "Debug",
        "interview_state_8043 - NWKID: %s, Status: %s, RIA: %s,"
        % (
            NWKID,
            status,
            RIA,
        ),
    )

    self.ListOfDevices[NWKID]["RIA"] = str(RIA + 1)

    if knownModel:
        self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s Model Name: %s" % (RIA, NWKID, self.ListOfDevices[NWKID]["Model"]))
        return "createDB"  # Fast track

    self.log.logging("Pairing", "Debug", "[%s] NEW OBJECT: %s Request Model Name" % (RIA, NWKID))
    ReadAttributeRequest_0000(self, NWKID, fullScope=False)  # Reuest Model Name

    request_node_descriptor( self, NWKID, RIA=None, status=None)

    for iterEp in self.ListOfDevices[NWKID]["Ep"]:
        # ColorMode
        if "0300" not in self.ListOfDevices[NWKID]["Ep"][iterEp]:
            continue

        if "ColorInfos" not in self.ListOfDevices[NWKID] or "ColorMode" not in self.ListOfDevices[NWKID]["ColorInfos"]:
            self.ListOfDevices[NWKID]["RIA"] = str(RIA + 1)
            self.log.logging(
                "Pairing",
                "Status",
                "[%s] NEW OBJECT: %s Request Attribute for Cluster 0x0300 to get ColorMode" % (RIA, NWKID),
            )
            ReadAttributeRequest_0300(self, NWKID)
            break

    return status

def request_node_descriptor( self, NWKID, RIA=None, status=None):

    if "Manufacturer" in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]["Manufacturer"] in ({}, ""):
            self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s Request Node Descriptor" % (RIA, NWKID))
            sendZigateCmd(self, "0042", str(NWKID))  # Request a Node Descriptor
            return True

        self.log.logging(
            "Pairing",
            "Debug",
            "[%s] NEW OBJECT: %s Manufacturer: %s" % (RIA, NWKID, self.ListOfDevices[NWKID]["Manufacturer"]),
            NWKID,
            )
        return False

    self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s Request Node Descriptor" % (RIA, NWKID))
    sendZigateCmd(self, "0042", str(NWKID))  # Request a Node Descriptor
    return True

def interview_state_8045(self, NWKID, RIA=None, status=None):
    self.log.logging(
        "Pairing",
        "Debug",
        "interview_state_8045 - NWKID: %s, Status: %s, RIA: %s,"
        % (
            NWKID,
            status,
            RIA,
        ),
    )
    if RIA:
        self.ListOfDevices[NWKID]["RIA"] = str(RIA + 1)
    self.ListOfDevices[NWKID]["Heartbeat"] = "0"
    self.ListOfDevices[NWKID]["Status"] = "0043"

    if "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] == {}:
        self.log.logging("Pairing", "Debug", "[%s] NEW OBJECT: %s Request Model Name" % (RIA, NWKID))
        ReadAttributeRequest_0000(self, NWKID, fullScope=False)  # Reuest Model Name

    for iterEp in self.ListOfDevices[NWKID]["Ep"]:
        if is_fake_ep(self, NWKID, iterEp):
            continue

        self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s Request Simple Descriptor for Ep: %s" % ("-", NWKID, iterEp))
        sendZigateCmd(self, "0043", str(NWKID) + str(iterEp))

    return "0043"


def interview_timeout(self, Devices, NWKID, RIA, status):
    self.log.logging(
        "Pairing",
        "Debug",
        "interview_timeout - NWKID: %s, Status: %s, RIA: %s,"
        % (
            NWKID,
            status,
            RIA,
        ),
    )

    Domoticz.Error("[%s] NEW OBJECT: %s Not able to get all needed attributes on time" % (RIA, NWKID))
    self.ListOfDevices[NWKID]["Status"] = "UNKNOW"
    self.ListOfDevices[NWKID]["ConsistencyCheck"] = "Bad Pairing"
    Domoticz.Error("processNotinDB - not able to find response from " + str(NWKID) + " stop process at " + str(status))
    Domoticz.Error("processNotinDB - Collected Infos are : %s" % (str(self.ListOfDevices[NWKID])))
    self.adminWidgets.updateNotificationWidget(Devices, "Unable to collect all informations for enrollment of this devices. See Logs")
    self.CommiSSionning = False
    return "UNKNOW"


def interview_state_createDB(self, Devices, NWKID, RIA, status):
    self.log.logging(
        "Pairing",
        "Debug",
        "interview_state_createDB - NWKID: %s, Status: %s, RIA: %s,"
        % (
            NWKID,
            status,
            RIA,
        ),
    )
    # We will try to create the device(s) based on the Model , if we find it in DeviceConf or against the Cluster
    if "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] == {} or self.ListOfDevices[NWKID]["Model"] == "":
        if status == "8043" and int(self.ListOfDevices[NWKID]["RIA"], 10) < 3:  # Let's take one more chance to get Model
            self.log.logging("Pairing", "Debug", "Too early, let's try to get the Model")
            return

    # Let's check if we have to disable the widget creation
    if "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] != {} and self.ListOfDevices[NWKID]["Model"] in self.DeviceConf and "CreateWidgetDomoticz" in self.DeviceConf[self.ListOfDevices[NWKID]["Model"]]:
        if not self.DeviceConf[self.ListOfDevices[NWKID]["Model"]]["CreateWidgetDomoticz"]:
            self.ListOfDevices[NWKID]["Status"] = "notDB"
            self.ListOfDevices[NWKID]["PairingInProgress"] = False
            self.CommiSSionning = False
            return

    # Let's check if we have a profalux device, and if that is a remote. In such case, just drop this
    if "Manufacturer" in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]["Manufacturer"] == "1110":
            if self.ListOfDevices[NWKID]["ZDeviceID"] == "0201":  # Remote
                self.ListOfDevices[NWKID]["Status"] = "notDB"
                self.ListOfDevices[NWKID]["PairingInProgress"] = False
                self.CommiSSionning = False
                return

    # Check once more if we have received the Model Name
    if "ConfigSource" in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]["ConfigSource"] != "DeviceConf":
            if "Model" in self.ListOfDevices[NWKID]:
                if self.ListOfDevices[NWKID]["Model"] in self.DeviceConf:
                    self.ListOfDevices[NWKID]["ConfigSource"] = "DeviceConf"
    else:
        if "Model" in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]["Model"] in self.DeviceConf:
                self.ListOfDevices[NWKID]["ConfigSource"] = "DeviceConf"

    self.log.logging("Pairing", "Debug", "[%s] NEW OBJECT: %s Trying to create Domoticz device(s)" % (RIA, NWKID))
    IsCreated = False
    # Let's check if the IEEE is not known in Domoticz
    for x in Devices:
        if self.ListOfDevices[NWKID].get("IEEE"):
            if Devices[x].DeviceID == str(self.ListOfDevices[NWKID]["IEEE"]):
                IsCreated = True
                Domoticz.Error("processNotinDBDevices - Devices already exist. " + Devices[x].Name + " with " + str(self.ListOfDevices[NWKID]))
                Domoticz.Error("processNotinDBDevices - Please cross check the consistency of the Domoticz and Plugin database.")
                break

    if not IsCreated:
        full_provision_device(self, Devices, NWKID, RIA, status)
        return


def full_provision_device(self, Devices, NWKID, RIA, status):

    self.log.logging(
        "Pairing",
        "Debug",
        "processNotinDBDevices - ready for creation: %s , Model: %s " % (self.ListOfDevices[NWKID], self.ListOfDevices[NWKID]["Model"]),
    )

    # Purpose of this call is to patch Model and Manufacturer Name in case of Profalux
    # We do it just before calling CreateDomoDevice
    if "Manufacturer" in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]["Manufacturer"] == "1110":
            profalux_fake_deviceModel(self, NWKID)

    CreateDomoDevice(self, Devices, NWKID)
    if self.ListOfDevices[NWKID]["Status"] not in ("inDB", "failDB"):
        # Something went wrong in the Widget creation
        Domoticz.Error("processNotinDBDevices - Creat Domo Device Failed !!! for %s status: %s" % (NWKID, self.ListOfDevices[NWKID]["Status"]))
        self.ListOfDevices[NWKID]["Status"] = "UNKNOW"
        self.CommiSSionning = False
        return

    # Don't know why we need as this seems very weird
    if NWKID not in self.ListOfDevices:
        Domoticz.Error("processNotinDBDevices - %s doesn't exist in Post creation widget" % NWKID)
        self.CommiSSionning = False
        return
    if "Ep" not in self.ListOfDevices[NWKID]:
        Domoticz.Error("processNotinDBDevices - %s doesn't have Ep in Post creation widget" % NWKID)
        self.CommiSSionning = False
        return

    if "ConfigSource" in self.ListOfDevices[NWKID]:
        self.log.logging(
            "Pairing",
            "Debug",
            "Device: %s - Config Source: %s Ep Details: %s" % (NWKID, self.ListOfDevices[NWKID]["ConfigSource"], str(self.ListOfDevices[NWKID]["Ep"])),
        )

    zigbee_provision_device(self, Devices, NWKID, RIA, status)

    # Reset HB in order to force Read Attribute Status
    self.ListOfDevices[NWKID]["Heartbeat"] = 0
    self.adminWidgets.updateNotificationWidget(Devices, "Successful creation of Widget for :%s DeviceID: %s" % (self.ListOfDevices[NWKID]["Model"], NWKID))
    self.CommiSSionning = False

    self.ListOfDevices[NWKID]["PairingInProgress"] = False


def zigbee_provision_device(self, Devices, NWKID, RIA, status):
    # Bindings ....
    binding_needed_clusters_with_zigate(self, NWKID)

    reWebBind_Clusters(self, NWKID)

    # Just after Binding Enable Opple with Magic Word
    if self.ListOfDevices[NWKID]["Model"] in (
        "lumi.remote.b686opcn01",
        "lumi.remote.b486opcn01",
        "lumi.remote.b286opcn01",
        "lumi.remote.b686opcn01-bulb",
        "lumi.remote.b486opcn01-bulb",
        "lumi.remote.b286opcn01-bulb",
    ):
        self.log.logging("Pairing", "Debug", "---> Calling enableOppleSwitch %s" % NWKID)
        enableOppleSwitch(self, NWKID)

    # 2 Enable Configure Reporting for any applicable cluster/attributes
    self.log.logging("Pairing", "Debug", "Request Configure Reporting for %s" % NWKID)
    self.configureReporting.processConfigureReporting(NWKID)

    # 3 Read attributes
    device_interview(self, NWKID)

    # 4. IAS Enrollment
    handle_IAS_enrollmment_if_needed(self, NWKID, RIA, status)

    # Other stuff
    scan_device_for_group_memebership(self, NWKID)
    send_identify_effect(self, NWKID)
    request_list_of_attributes(self, NWKID)

    # Custom device parameters set
    if "Param" in self.ListOfDevices[NWKID]:
        self.log.logging("Pairing", "Debug", "Custom device parameters setting")
        self.ListOfDevices[NWKID]["CheckParam"] = True

    # 4- Create groups if required
    create_group_if_required(self, NWKID)

    # 5- Device Specifics
    handle_device_specific_needs(self, Devices, NWKID)


def binding_needed_clusters_with_zigate(self, NWKID):
    cluster_to_bind = CLUSTERS_LIST

    # if (
    #    "BindingTimeStamps" in self.ListOfDevices[NWKID]
    #    and self.ListOfDevices[NWKID]["BindingTimeStamps"] < time.time() + 60
    # ):
    #    # skip it . alreday in progress
    #    return
    # self.ListOfDevices[NWKID]["BindingTimeStamps"] = time.time()

    # Do we have to follow Certified Conf file, or look for standard mecanishm ?
    if "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] != {} and self.ListOfDevices[NWKID]["Model"] in self.DeviceConf:
        self.log.logging("Pairing", "Log", "binding_needed_clusters_with_zigate %s based on Device Configuration" % (NWKID))

        _model = self.ListOfDevices[NWKID]["Model"]
        # Check if we have to unbind clusters
        if "ClusterToUnbind" in self.DeviceConf[_model]:
            for iterEp, iterUnBindCluster in self.DeviceConf[_model]["ClusterToUnbind"]:
                unbindDevice(self, self.ListOfDevices[NWKID]["IEEE"], iterEp, iterUnBindCluster)

        # Check if we have specific clusters to Bind
        if "ClusterToBind" in self.DeviceConf[_model]:
            cluster_to_bind = self.DeviceConf[_model]["ClusterToBind"]
            self.log.logging("Pairing", "Log", "%s Binding cluster based on Conf: %s" % (NWKID, str(cluster_to_bind)))
            for x in self.DeviceConf[_model]["Ep"]:
                for y in cluster_to_bind:
                    if y not in self.DeviceConf[_model]["Ep"][x]:
                        continue
                    self.log.logging("Pairing", "Debug", "Request a Bind for %s/%s on Cluster %s" % (NWKID, x, y))
                    # If option enabled, unbind
                    if self.pluginconf.pluginConf["doUnbindBind"]:
                        unbindDevice(self, self.ListOfDevices[NWKID]["IEEE"], x, y)
                    # Finaly binding
                    bindDevice(self, self.ListOfDevices[NWKID]["IEEE"], x, y)
        return

    # Let try to bind what we beleive needs to be bind (all ClusterIn)
    if "Epv2" in self.ListOfDevices[NWKID]:
        for ep in self.ListOfDevices[NWKID]["Epv2"]:
            if "ClusterIn" in self.ListOfDevices[NWKID]["Epv2"][ep]:
                for iterBindCluster in self.ListOfDevices[NWKID]["Epv2"][ep]["ClusterIn"]:
                    self.log.logging("Pairing", "Debug", "Request a Bind for %s/%s on ClusterIn %s" % (NWKID, ep, iterBindCluster))
                    if self.pluginconf.pluginConf["doUnbindBind"]:
                        unbindDevice(self, self.ListOfDevices[NWKID]["IEEE"], ep, iterBindCluster)
                    # Finaly binding
                    bindDevice(self, self.ListOfDevices[NWKID]["IEEE"], ep, iterBindCluster)


def handle_IAS_enrollmment_if_needed(self, NWKID, RIA, status):
    if "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] == "MOSZB-140":
        # Frient trigger itself the Device Enrollment
        return

    # Search for an IAS Cluster
    for iterEp in self.ListOfDevices[NWKID]["Ep"]:

        # If not IAS cluster skip
        if "0500" not in self.ListOfDevices[NWKID]["Ep"][iterEp] and "0502" not in self.ListOfDevices[NWKID]["Ep"][iterEp]:
            continue

        self.log.logging("Pairing", "Debug", "We have found 0500 or 0502 on Ep: %s of %s" % (iterEp, NWKID))

        # IAS Zone
        # We found a Cluster 0x0500 IAS. May be time to start the IAS Zone process
        self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s 0x%04s - IAS Zone controler setting" % (RIA, NWKID, status))
        self.iaszonemgt.IASZone_triggerenrollement(NWKID, iterEp)

        if "0502" in self.ListOfDevices[NWKID]["Ep"][iterEp]:
            self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s 0x%04s - IAS WD enrolment" % (RIA, NWKID, status))
            self.iaszonemgt.IASWD_enroll(NWKID, iterEp)


def device_interview(self, NWKID):
    for iterEp in self.ListOfDevices[NWKID]["Ep"]:
        # Let's scan each Endpoint cluster and check if there is anything to read
        for iterReadAttrCluster in CLUSTERS_LIST:
            if iterReadAttrCluster not in self.ListOfDevices[NWKID]["Ep"][iterEp]:
                continue
            if iterReadAttrCluster not in READ_ATTRIBUTES_REQUEST:
                continue
            if iterReadAttrCluster == "0500":
                # Skip IAS as it is address by IAS Enrollment
                continue
            # if iterReadAttrCluster == '0000':
            #    reset_cluster_datastruct( self, 'ReadAttributes', NWKID, iterEp, iterReadAttrCluster  )
            func = READ_ATTRIBUTES_REQUEST[iterReadAttrCluster][0]
            func(self, NWKID)


def send_identify_effect(self, NWKID):
    # Identify for ZLL compatible devices
    # Search for EP to be used
    for ep in getListOfEpForCluster(self, NWKID, "0003"):
        identifyEffect(self, NWKID, ep, effect="Blink")
        # We just do once
        break


def create_group_if_required(self, NWKID):
    if self.groupmgt and self.pluginconf.pluginConf["allowGroupMembership"] and "Model" in self.ListOfDevices[NWKID]:
        self.log.logging("Pairing", "Debug", "Creation Group")
        if self.ListOfDevices[NWKID]["Model"] in self.DeviceConf:
            if "GroupMembership" in self.DeviceConf[self.ListOfDevices[NWKID]["Model"]]:
                for groupToAdd in self.DeviceConf[self.ListOfDevices[NWKID]["Model"]]["GroupMembership"]:
                    if len(groupToAdd) == 2:
                        self.groupmgt.addGroupMemberShip(NWKID, groupToAdd[0], groupToAdd[1])
                    else:
                        Domoticz.Error("Uncorrect GroupMembership definition %s" % str(self.DeviceConf[self.ListOfDevices[NWKID]["Model"]]["GroupMembership"]))

    if self.groupmgt and "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] == "tint-Remote-white":
        # Tint Remote manage 4 groups and we will create with ZiGate attached.
        self.groupmgt.addGroupMemberShip("0000", "01", "4003")
        self.groupmgt.addGroupMemberShip("0000", "01", "4004")
        self.groupmgt.addGroupMemberShip("0000", "01", "4005")
        self.groupmgt.addGroupMemberShip("0000", "01", "4006")


def handle_device_specific_needs(self, Devices, NWKID):

    # In case of Orvibo Scene controller let's Registration
    if "Manufacturer Name" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Manufacturer Name"] == "欧瑞博":
        OrviboRegistration(self, NWKID)

    if "Model" not in self.ListOfDevices[NWKID]:
        return

    # In case of Schneider Wiser, let's do the Registration Process
    MsgIEEE = self.ListOfDevices[NWKID]["IEEE"]
    if self.ListOfDevices[NWKID]["Model"] in ("Wiser2-Thermostat",):
        wiser_home_lockout_thermostat(self, NWKID, 0)

    elif MsgIEEE[0 : len(PREFIX_MACADDR_WIZER_LEGACY)] == PREFIX_MACADDR_WIZER_LEGACY and WISER_LEGACY_MODEL_NAME_PREFIX in self.ListOfDevices[NWKID]["Model"]:
        schneider_wiser_registration(self, Devices, NWKID)

    elif self.ListOfDevices[NWKID]["Model"] in (
        "AC201A",
        "AC211",
        "AC221",
    ):
        self.log.logging("Pairing", "Debug", "CasaIA registration needed")
        casaia_pairing(self, NWKID)

    elif self.ListOfDevices[NWKID]["Model"] in ("TS0601-sirene",):
        self.log.logging("Pairing", "Debug", "Tuya Sirene registration needed")
        tuya_sirene_registration(self, NWKID)

    elif self.ListOfDevices[NWKID]["Model"] in (TUYA_eTRV_MODEL):
        self.log.logging("Pairing", "Debug", "Tuya eTRV registration needed")
        tuya_eTRV_registration(self, NWKID, device_reset=True)

    elif self.ListOfDevices[NWKID]["Model"] in ("TS0121",):
        self.log.logging("Pairing", "Debug", "Tuya TS0121 registration needed")
        tuya_TS0121_registration(self, NWKID)

    elif self.ListOfDevices[NWKID]["Model"] in (
        "TS0601-Energy",
        "TS0601-switch",
        "TS0601-2Gangs-switch",
        "TS0601-SmartAir",
    ):
        self.log.logging("Pairing", "Debug", "Tuya general registration needed")
        tuya_registration(self, NWKID, device_reset=True)

    elif self.ListOfDevices[NWKID]["Model"] in ("TS0601-Parkside-Watering-Timer",):
        self.log.logging("Pairing", "Debug", "Tuya Water Sensor Parkside registration needed")
        tuya_registration(self, NWKID, device_reset=True, parkside=True)

    # Set the sensitivity for Xiaomi Vibration
    elif self.ListOfDevices[NWKID]["Model"] == "lumi.vibration.aq1":
        self.log.logging(
            "Pairing",
            "Status",
            "processNotinDBDevices - set viration Aqara %s sensitivity to %s" % (NWKID, self.pluginconf.pluginConf["vibrationAqarasensitivity"]),
        )
        setXiaomiVibrationSensitivity(self, NWKID, sensitivity=self.pluginconf.pluginConf["vibrationAqarasensitivity"])

    # Set Calibration for Thermostat
    elif self.ListOfDevices[NWKID]["Model"] == "SPZB0001":
        thermostat_Calibration(self, NWKID, 0x00)


def scan_device_for_group_memebership(self, NWKID):
    for ep in self.ListOfDevices[NWKID]["Ep"]:
        if "0004" in self.ListOfDevices[NWKID]["Ep"][ep] and self.groupmgt:
            self.groupmgt.ScanDevicesForGroupMemberShip(
                [
                    NWKID,
                ]
            )
            break


def request_list_of_attributes(self, NWKID):
    for iterEp in self.ListOfDevices[NWKID]["Ep"]:
        self.log.logging("Pairing", "Debug", "looking for List of Attributes ep: %s" % iterEp)
        for iterCluster in self.ListOfDevices[NWKID]["Ep"][iterEp]:
            if iterCluster in ("Type", "ClusterType", "ColorMode"):
                continue
            if "ConfigSource" in self.ListOfDevices[NWKID]:
                if self.ListOfDevices[NWKID]["ConfigSource"] != "DeviceConf":
                    getListofAttribute(self, NWKID, iterEp, iterCluster)
