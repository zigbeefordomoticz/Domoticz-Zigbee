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
    Module: pairingProcess.py

    Description: Manage all actions done during the onHeartbeat() call

"""

import time

from Modules.basicOutputs import getListofAttribute, identifyEffect
from Modules.bindings import bindDevice, reWebBind_Clusters, unbindDevice
from Modules.casaia import casaia_pairing
from Modules.domoCreate import CreateDomoDevice
from Modules.domoticzAbstractLayer import is_device_ieee_in_domoticz_db
from Modules.domoTools import CLUSTER_TO_TYPE
from Modules.livolo import livolo_bind
from Modules.lumi import enable_click_mode_aqara, enableOppleSwitch
from Modules.manufacturer_code import (PREFIX_MAC_LEN, PREFIX_MACADDR_OPPLE,
                                       PREFIX_MACADDR_TUYA,
                                       PREFIX_MACADDR_WIZER_LEGACY,
                                       PREFIX_MACADDR_XIAOMI)
from Modules.orvibo import OrviboRegistration
from Modules.profalux import profalux_fake_deviceModel
from Modules.readAttributes import (READ_ATTRIBUTES_REQUEST, ReadAttributeReq,
                                    ReadAttributeRequest_0000,
                                    ReadAttributeRequest_0000_for_tuya,
                                    ReadAttributeRequest_0300)
from Modules.schneider_wiser import (WISER_LEGACY_MODEL_NAME_PREFIX,
                                     schneider_wiser_registration,
                                     wiser_home_lockout_thermostat)
from Modules.thermostats import thermostat_Calibration
from Modules.tools import (get_device_config_param,
                           get_deviceconf_parameter_value,
                           getListOfEpForCluster, is_fake_ep)
from Modules.tuya import (tuya_cmd_ts004F, tuya_command_f0,
                          tuya_lighting_color_control, tuya_polling,
                          tuya_registration)
from Modules.tuyaConst import TUYA_eTRV_MODEL
from Modules.tuyaSiren import tuya_sirene_registration
from Modules.tuyaTools import tuya_TS0121_registration
from Modules.tuyaTRV import tuya_eTRV_registration
from Modules.zb_tables_management import mgmt_rtg
from Modules.zigateConsts import CLUSTERS_LIST, ZIGATE_EP
from Zigbee.zdpCommands import (zdp_active_endpoint_request,
                                zdp_node_descriptor_request,
                                zdp_simple_descriptor_request)
from Zigbee.zdpRawCommands import zdp_raw_match_desc_req_0500


def processNotinDBDevices(self, Devices, NWKID, status, RIA):

    # Starting V 4.1.x
    # 0x0043 / List of EndPoints is requested at the time we receive the End Device Annocement
    # 0x0045 / EndPoint Description is requested at the time we recice the List of EPs.
    # In case Model is defined and is in DeviceConf, we will short cut the all process and go to the Widget creation
    if status in ("UNKNOW", "erasePDM", "provREQ", "notDB"):
        return

    HB_ = int(self.ListOfDevices[NWKID]["Heartbeat"])
    self.log.logging( "Pairing", "Debug", "processNotinDBDevices - NWKID: %s, Status: %s, RIA: %s, HB_: %s " % (NWKID, status, RIA, HB_), )

    if status not in ("004d", "0043", "0045", "8045", "8043") and "Model" in self.ListOfDevices[NWKID]:
        return

    if "PairingInProgress" not in self.ListOfDevices[NWKID] or not self.ListOfDevices[NWKID]["PairingInProgress"]:
        self.ListOfDevices[NWKID]["PairingInProgress"] = True

    knownModel = False
    if self.ListOfDevices[NWKID]["Model"] not in ({}, ""):
        self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s Model Name: %s" % (
            RIA, NWKID, self.ListOfDevices[NWKID]["Model"]))
        # Let's check if this Model is known
        if "Manufacturer Name" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Manufacturer Name"] not in ({}, ""):
            self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s Manufacturer Name: %s" % (
                RIA, NWKID, self.ListOfDevices[NWKID]["Manufacturer Name"]))
        if self.ListOfDevices[NWKID]["Model"] in self.DeviceConf:
            knownModel = True
            status = "CreateDB"  # Fast track

    self.log.logging("Pairing", "Debug", "[%s] NEW OBJECT: %s Model Name: %s knownModel: %s status: %s" % (RIA, NWKID, self.ListOfDevices[NWKID]["Model"], knownModel, status))

    if knownModel and self.ListOfDevices[NWKID]["Model"] == "TI0001":
        # https://zigate.fr/forum/topic/livolo-compatible-zigbee/#postid-596
        livolo_bind(self, NWKID, "06")

    if knownModel and "NoDeviceInterview" in self.DeviceConf[self.ListOfDevices[NWKID]["Model"]] and self.DeviceConf[self.ListOfDevices[NWKID]["Model"]]["NoDeviceInterview"]:
        status = "CreateDB"

    if status == "8043":  # We have at least receive 1 EndPoint
        status = interview_state_8043(self, NWKID, RIA, knownModel, status)
        if status != "CreateDB" and RIA <= 2:
            return

    if knownModel and RIA > 3 and status not in ("UNKNOW", "inDB"):
        # We have done several retry to get Ep ... but we known the Model
        self.log.logging(
            "Pairing",
            "Debug",
            "processNotinDB - Try several times to get all informations, let's use the Model now " + str(NWKID),
        )
        status = "CreateDB"

    # if status == "8043" and request_node_descriptor( self, NWKID, RIA=None, status=None):
    #    # We have to request the node_descriptor
    #    return

    if status != "CreateDB" and RIA == 4 and do_we_have_key_clusters( self, NWKID ):
        # Looks like we are ready to give up, but as we have cluster which translate into Widget, let's move
        status = "CreateDB"
        
    if status in ("CreateDB", "8043"):
        # We do a request_node_description in case of unknown.
        request_node_descriptor(self, NWKID, RIA=None, status=None)
        interview_state_createDB(self, Devices, NWKID, RIA, status)

    if status != "CreateDB":
        if HB_ > 2 and not knownModel and status in ("004d", "0045"):
            # We will re-request EndPoint List ( 0x0045)
            interview_state_004d(self, NWKID, RIA, status)

        elif HB_ > 1 and not knownModel and status in ("0043",):
            # We will re-request EndPoint List ( 0x0043)
            interview_state_8045(self, NWKID, RIA, status)

        elif RIA > 5 and status not in ("UNKNOW", "inDB"):  # We have done several retry
            status = interview_timeout(self, Devices, NWKID, RIA, status)

        else:
            self.ListOfDevices[NWKID]["RIA"] = str(RIA + 1)

def do_we_have_key_clusters( self, NWKID ):
    # We will just check if we have at least One cluster for whcih a Widget would be created
    if "Ep" not in self.ListOfDevices[NWKID]:
        return False
    for ep in list(self.ListOfDevices[NWKID]['Ep']):
        for cluster in list(self.ListOfDevices[NWKID]['Ep'][ ep ]):
            self.log.logging("Pairing", "Debug", " . Checking %s on ep %s" %( cluster, ep))
            if cluster in CLUSTER_TO_TYPE:
                return True
    return False
    
    
def interview_state_004d(self, NWKID, RIA=None, status=None):
    self.log.logging( "Pairing", "Debug", "interview_state_004d - NWKID: %s, Status: %s, RIA: %s," % ( 
        NWKID, status, RIA, ), )
    self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s %s" % (RIA, NWKID, status))

    if RIA:
        self.ListOfDevices[NWKID]["RIA"] = str(RIA + 1)
    self.ListOfDevices[NWKID]["Heartbeat"] = "0"
    self.ListOfDevices[NWKID]["Status"] = "0045"

    request_tuya_magic_read = self.pluginconf.pluginConf["TuyaMagicRead"]

    MsgIEEE = self.ListOfDevices[NWKID].get("IEEE", None)

    if ( MsgIEEE and ( MsgIEEE[: PREFIX_MAC_LEN] in PREFIX_MACADDR_XIAOMI or MsgIEEE[: PREFIX_MAC_LEN] in PREFIX_MACADDR_OPPLE ) ):
        ReadAttributeRequest_0000(self, NWKID, fullScope=False)  # In order to request Model Name

    elif ( self.pluginconf.pluginConf["enableSchneiderWiser"] and MsgIEEE[: PREFIX_MAC_LEN] in PREFIX_MACADDR_WIZER_LEGACY ):
        ReadAttributeRequest_0000(self, NWKID, fullScope=False)  # In order to request Model Name

    elif request_tuya_magic_read and ( MsgIEEE and MsgIEEE[: PREFIX_MAC_LEN] in PREFIX_MACADDR_TUYA):
        ReadAttributeRequest_0000_for_tuya( self, NWKID)

    # Check if Cluster 0500 is on this device. If so this will trigger IAS asap
    zdp_raw_match_desc_req_0500( self,NWKID )

    zdp_active_endpoint_request(self, NWKID )
    return "0045"


def interview_state_8043(self, NWKID, RIA, knownModel, status):
    # At that stage, we have at least One Ep Description
    self.log.logging( "Pairing", "Debug", "interview_state_8043 - NWKID: %s, Status: %s, RIA: %s," % ( NWKID, status, RIA, ),)

    self.ListOfDevices[NWKID]["RIA"] = str(RIA + 1)

    # IAS Enrollment if required
    self.iaszonemgt.IAS_device_enrollment(NWKID)

    if knownModel:
        self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s Model Name: %s" % (RIA, NWKID, self.ListOfDevices[NWKID]["Model"]))
        return "CreateDB"  # Fast track

    if "Model" not in self.ListOfDevices[NWKID] or self.ListOfDevices[NWKID]["Model"] in ( "", {}):
        self.log.logging("Pairing", "Debug", "[%s] NEW OBJECT: %s Request Model Name" % (RIA, NWKID))
        ReadAttributeRequest_0000(self, NWKID, fullScope=False)  # Reuest Model Name

    request_node_descriptor(self, NWKID, RIA=None, status=None)

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


def request_node_descriptor(self, NWKID, RIA=None, status=None):
    """ Trigger a Req Node Descriptor if Manufacturer not found"""

    manufacturer = self.ListOfDevices[NWKID].get("Manufacturer", "")
    model = self.ListOfDevices[NWKID].get("Model", "")
    
    if model in ( "lumi.sensor_switch",) or manufacturer not in ( "", {} ):
        self.log.logging( "Pairing", "Debug", "[%s] NEW OBJECT: %s Manufacturer: %s Model: %s" % (RIA, NWKID, manufacturer, model), NWKID, )
        return False

    self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s Request Node Descriptor" % (RIA, NWKID))
    zdp_node_descriptor_request(self, NWKID)
    return True


def interview_state_8045(self, NWKID, RIA=None, status=None):
    self.log.logging( "Pairing", "Debug", "interview_state_8045 - NWKID: %s, Status: %s, RIA: %s," % ( NWKID, status, RIA, ), )
    if RIA:
        self.ListOfDevices[NWKID]["RIA"] = str(RIA + 1)
    self.ListOfDevices[NWKID]["Heartbeat"] = "0"
    self.ListOfDevices[NWKID]["Status"] = "0043"

    if "Model" not in self.ListOfDevices[NWKID] or self.ListOfDevices[NWKID]["Model"] in ( {}, ""):
        self.log.logging("Pairing", "Debug", "[%s] NEW OBJECT: %s Request Model Name" % (RIA, NWKID))
        ReadAttributeRequest_0000(self, NWKID, fullScope=False)  # Reuest Model Name

    return "0043" if request_next_Ep(self, NWKID) else "0045"

def request_next_Ep(self, Nwkid):
    if "ReqEpv2" not in self.ListOfDevices[Nwkid]:
        self.ListOfDevices[Nwkid]["ReqEpv2"] = {}
        
    for iterEp in list(self.ListOfDevices[Nwkid]["Ep"]):
        if is_fake_ep(self, Nwkid, iterEp):
            continue

        # Skip Green Zigbee EndPoint
        if iterEp == 'f2':
            continue
        
        if iterEp in self.ListOfDevices[Nwkid]["Epv2"] and self.ListOfDevices[Nwkid]["Ep"][ iterEp ] not in ( "", {}):
            continue
        
        if iterEp in self.ListOfDevices[Nwkid]["ReqEpv2"] and self.ListOfDevices[Nwkid]["ReqEpv2"][ iterEp ] < ( time.time() + 120 ):
            continue

        # Let's request only 1 Ep, in order wait for the response and then request the next one
        self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s Request Simple Descriptor for Ep: %s" % ("-", Nwkid, iterEp))
        self.ListOfDevices[Nwkid]["ReqEpv2"][ iterEp ] = time.time()
        zdp_simple_descriptor_request(self, Nwkid, iterEp)
        return False
        
    # We have been all Ep, and so nothing else to do

    return True

   
def interview_timeout(self, Devices, NWKID, RIA, status):
    self.log.logging( "Pairing", "Debug", "interview_timeout - NWKID: %s, Status: %s, RIA: %s," % ( NWKID, status, RIA, ), )

    self.log.logging("Pairing", "Error", "[%s] NEW OBJECT: %s Not able to get all needed attributes on time" % (RIA, NWKID))
    self.ListOfDevices[NWKID]["Status"] = "UNKNOW"
    self.ListOfDevices[NWKID]["ConsistencyCheck"] = "Bad Pairing"
    self.log.logging("Pairing", "Error", "processNotinDB - not able to find response from " + str(NWKID) + " stop process at " + str(status))
    self.log.logging("Pairing", "Error", "processNotinDB - Collected Infos are : %s" % (str(self.ListOfDevices[NWKID])))
    self.adminWidgets.updateNotificationWidget(Devices, "Unable to collect all informations for enrollment of this devices. See Logs")
    self.CommiSSionning = False
    if "ReqEpv2" in self.ListOfDevices[NWKID]:
        del self.ListOfDevices[NWKID]["ReqEpv2"]

    return "UNKNOW"


def interview_state_createDB(self, Devices, NWKID, RIA, status):
    self.log.logging( "Pairing", "Debug", "interview_state_createDB - NWKID: %s, Status: %s, RIA: %s," % ( NWKID, status, RIA, ), )
    # We will try to create the device(s) based on the Model , if we find it in DeviceConf or against the Cluster
    if (
        (
            "Model" in self.ListOfDevices[NWKID]
            and self.ListOfDevices[NWKID]["Model"] in ( {}, "" )
        )
        and status == "8043"
        and int(self.ListOfDevices[NWKID]["RIA"], 10) < 3
    ):  # Let's take one more chance to get Model
        self.log.logging("Pairing", "Debug", "Too early, let's try to get the Model")
        return

    # Let's check if we have to disable the widget creation
    create_widget = get_deviceconf_parameter_value(self, self.ListOfDevices[NWKID]["Model"], "CreateWidgetDomoticz")
    if create_widget is not None and create_widget is False:
        create_device_without_Domoticz_Widgets( self, NWKID)
        return

    # Let's check if we have a profalux device, and if that is a remote. In such case, just drop this
    if (
        "Manufacturer" in self.ListOfDevices[NWKID]
        and self.ListOfDevices[NWKID]["Manufacturer"] == "1110"
        and self.ListOfDevices[NWKID]["ZDeviceID"] == "0201"
    ):  # Remote
        create_device_without_Domoticz_Widgets( self, NWKID)
        return

    # Check once more if we have received the Model Name
    if "ConfigSource" in self.ListOfDevices[NWKID]:
        if (
            self.ListOfDevices[NWKID]["ConfigSource"] != "DeviceConf"
            and "Model" in self.ListOfDevices[NWKID]
            and self.ListOfDevices[NWKID]["Model"] in self.DeviceConf
        ):
            self.ListOfDevices[NWKID]["ConfigSource"] = "DeviceConf"
    elif (
        "Model" in self.ListOfDevices[NWKID]
        and self.ListOfDevices[NWKID]["Model"] in self.DeviceConf
    ):
        self.ListOfDevices[NWKID]["ConfigSource"] = "DeviceConf"

    self.log.logging("Pairing", "Debug", "[%s] NEW OBJECT: %s Trying to create Domoticz device(s)" % (RIA, NWKID))
    IsCreated = False
    # Let's check if the IEEE is not known in Domoticz
    
    if is_device_ieee_in_domoticz_db(self, Devices, self.ListOfDevices[NWKID].get("IEEE")):
        IsCreated = True
        self.log.logging("Pairing", "Error", "There are alreday Widget(s) associated for this objet %s in Domoticz" % str(self.ListOfDevices[NWKID]) )
        return

    if not IsCreated:
        full_provision_device(self, Devices, NWKID, RIA, status)
        return

def create_device_without_Domoticz_Widgets( self, Nwkid):
        self.ListOfDevices[Nwkid]["Status"] = "notDB"
        self.ListOfDevices[Nwkid]["PairingInProgress"] = False
        self.CommiSSionning = False
        self.ListOfDevices[ Nwkid ]["CertifiedDevice"] = self.ListOfDevices[Nwkid]["Model"] in self.DeviceConf
   
def full_provision_device(self, Devices, NWKID, RIA, status):

    self.log.logging(
        "Pairing",
        "Debug",
        "processNotinDBDevices - ready for creation: %s , Model: %s " % (self.ListOfDevices[NWKID], self.ListOfDevices[NWKID]["Model"]),
    )

    # Purpose of this call is to patch Model and Manufacturer Name in case of Profalux
    # We do it just before calling CreateDomoDevice
    if ( "Manufacturer" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Manufacturer"] == "1110"):
        profalux_fake_deviceModel(self, NWKID)

    CreateDomoDevice(self, Devices, NWKID)
    if self.ListOfDevices[NWKID]["Status"] not in ("inDB", "failDB"):
        # Something went wrong in the Widget creation
        self.log.logging("Pairing", "Error","processNotinDBDevices - Creat Domo Device Failed !!! for %s status: %s" % (NWKID, self.ListOfDevices[NWKID]["Status"]))
        self.ListOfDevices[NWKID]["Status"] = "UNKNOW"
        self.CommiSSionning = False
        return

    self.ListOfDevices[ NWKID ]["PairingTime"] = time.time()
    # Don't know why we need as this seems very weird
    if NWKID not in self.ListOfDevices:
        self.log.logging("Pairing", "Error","processNotinDBDevices - %s doesn't exist in Post creation widget" % NWKID)
        self.CommiSSionning = False
        return
    if "Ep" not in self.ListOfDevices[NWKID]:
        self.log.logging("Pairing", "Error","processNotinDBDevices - %s doesn't have Ep in Post creation widget" % NWKID)
        self.CommiSSionning = False
        return

    if "ConfigSource" in self.ListOfDevices[NWKID]:
        self.log.logging( "Pairing", "Debug", "Device: %s - Config Source: %s Ep Details: %s" % (NWKID, self.ListOfDevices[NWKID]["ConfigSource"], str(self.ListOfDevices[NWKID]["Ep"])), )

    # IAS Enrollment if required
    self.iaszonemgt.IAS_device_enrollment(NWKID)

    zigbee_provision_device(self, Devices, NWKID, RIA, status)

    # Reset HB in order to force Read Attribute Status
    self.ListOfDevices[NWKID]["Heartbeat"] = 0
    self.adminWidgets.updateNotificationWidget(Devices, "Successful creation of Widget for :%s DeviceID: %s" % (self.ListOfDevices[NWKID]["Model"], NWKID))
    self.CommiSSionning = False

    self.ListOfDevices[NWKID]["PairingInProgress"] = False

    

def zigbee_provision_device(self, Devices, NWKID, RIA, status):

    modelName = self.ListOfDevices[NWKID]["Model"] if "Model" in self.ListOfDevices[NWKID] else ""
    if modelName in ("TS004F",):
        self.log.logging("Pairing", "Debug", "Tuya TS004F registration needed")
        if "Param" in self.ListOfDevices[NWKID] and "TS004FMode" in self.ListOfDevices[NWKID]["Param"]:
            tuya_cmd_ts004F(self, NWKID, self.ListOfDevices[NWKID]["Param"]["TS004FMode" ])

    # Bindings ....
    if not delay_binding_and_reporting(self, NWKID):
        binding_needed_clusters_with_zigate(self, NWKID)
        reWebBind_Clusters(self, NWKID)
        mgmt_rtg(self, NWKID, "BindingTable")

    # Just after Binding Enable Opple with Magic Word
    if modelName in (
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
    if not delay_binding_and_reporting(self, NWKID) and self.configureReporting:
        self.log.logging("Pairing", "Debug", "Request Configure Reporting for %s" % NWKID)
        self.configureReporting.processConfigureReporting(NwkId=NWKID)

    # 3 Read attributes
    device_interview(self, NWKID)

    # 4. IAS Enrollment
    #handle_IAS_enrollmment_if_needed(self, NWKID, RIA, status)

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
    
    # 6- Updating the Certified devices list
    self.ListOfDevices[ NWKID ]["CertifiedDevice"] = modelName in self.DeviceConf

    # Cleanup if needed
    if "ReqEpv2" in self.ListOfDevices[NWKID]:
        del self.ListOfDevices[NWKID]["ReqEpv2"]


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
    if "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] not in ( {}, "") and self.ListOfDevices[NWKID]["Model"] in self.DeviceConf:
        self.log.logging("Pairing", "Debug", "binding_needed_clusters_with_zigate %s based on Device Configuration" % (NWKID))
        _model = self.ListOfDevices[NWKID]["Model"]

        # Check if we have to unbind clusters
        if "ClusterToUnbind" in self.DeviceConf[_model]:
            for iterEp, iterUnBindCluster in self.DeviceConf[_model]["ClusterToUnbind"]:
                unbindDevice(self, self.ListOfDevices[NWKID]["IEEE"], iterEp, iterUnBindCluster)

        # Check if we have specific clusters to Bind
        if "ClusterToBind" in self.DeviceConf[_model]:
            cluster_to_bind = self.DeviceConf[_model]["ClusterToBind"]
            self.log.logging("Pairing", "Debug", "%s Binding cluster based on Conf: %s" % (NWKID, str(cluster_to_bind)))
            for x in self.DeviceConf[_model]["Ep"]:
                for y in cluster_to_bind:
                    if y not in self.DeviceConf[_model]["Ep"][x]:
                        continue
                    if y == "0500":
                        # Binding will be done in IAS
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
                    if iterBindCluster == "0500":
                        # Binding will be done in IAS
                        continue

                    self.log.logging("Pairing", "Debug", "Request a Bind for %s/%s on ClusterIn %s" % (NWKID, ep, iterBindCluster))
                    if self.pluginconf.pluginConf["doUnbindBind"]:
                        unbindDevice(self, self.ListOfDevices[NWKID]["IEEE"], ep, iterBindCluster)
                    # Finaly binding
                    bindDevice(self, self.ListOfDevices[NWKID]["IEEE"], ep, iterBindCluster)

def delay_binding_and_reporting(self, Nwkid):
    
    if "Model" not in self.ListOfDevices[Nwkid] or self.ListOfDevices[Nwkid]["Model"] in ( "", {}):
        return False
    _model = self.ListOfDevices[Nwkid]["Model"]
    if _model in self.DeviceConf and "DelayBindingAtPairing" in self.DeviceConf[_model] and self.DeviceConf[_model]["DelayBindingAtPairing"]:
        self.ListOfDevices[ Nwkid ]["DelayBindingAtPairing"] = int(( time.time() + int(self.DeviceConf[_model]["DelayBindingAtPairing"])))
        
        self.log.logging("Pairing", "Debug", "binding_needed_clusters_with_zigate %s Skip Binding due to >DelayBindingAtPairing<" % (Nwkid))
        return True
    return False


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
        self.iaszonemgt.IAS_device_enrollment(NWKID, iterEp)

        if "0502" in self.ListOfDevices[NWKID]["Ep"][iterEp]:
            self.log.logging("Pairing", "Status", "[%s] NEW OBJECT: %s 0x%04s - IAS WD enrolment" % (RIA, NWKID, status))
            self.iaszonemgt.IASWD_enroll(NWKID, iterEp)

def device_interview(self, Nwkid):
    self.log.logging("Pairing", "Debug", "device_interview %s" %Nwkid)
                
    for iterReadAttrCluster in get_list_of_clusters_for_device( self, Nwkid):
        # if iterReadAttrCluster == '0000':
        #    reset_cluster_datastruct( self, 'ReadAttributes', NWKID, iterEp, iterReadAttrCluster  )
        self.log.logging("Pairing", "Debug", "device_interview %s Read Attribute for cluster: %s" %(Nwkid, iterReadAttrCluster ))
        func = READ_ATTRIBUTES_REQUEST[iterReadAttrCluster][0]
        func(self, Nwkid)

def get_list_of_clusters_for_device( self, Nwkid):
    # We want to collect all clusters for this devices despite the EndPoint
    target_list_of_cluster = []
    for iterEp in self.ListOfDevices[Nwkid]["Ep"]:
        # Let's scan each Endpoint cluster and check if there is anything to read
        for iterReadAttrCluster in CLUSTERS_LIST:
            if iterReadAttrCluster not in self.ListOfDevices[Nwkid]["Ep"][iterEp]:
                continue
            if iterReadAttrCluster not in READ_ATTRIBUTES_REQUEST:
                continue
            if iterReadAttrCluster == "0500":
                # Skip IAS as it is address by IAS Enrollment
                continue
            if iterReadAttrCluster not in target_list_of_cluster:
                target_list_of_cluster.append( iterReadAttrCluster )
    return target_list_of_cluster   

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
        if (
            self.ListOfDevices[NWKID]["Model"] in self.DeviceConf
            and "GroupMembership"
            in self.DeviceConf[self.ListOfDevices[NWKID]["Model"]]
        ):
            for groupToAdd in self.DeviceConf[self.ListOfDevices[NWKID]["Model"]]["GroupMembership"]:
                if len(groupToAdd) == 2:
                    self.groupmgt.addGroupMemberShip(NWKID, groupToAdd[0], groupToAdd[1])
                else:
                    self.log.logging("Pairing", "Error","Uncorrect GroupMembership definition %s" % str(self.DeviceConf[self.ListOfDevices[NWKID]["Model"]]["GroupMembership"]))

    if self.groupmgt and "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] == "tint-Remote-white":
        # Tint Remote manage 4 groups and we will create with ZiGate attached.
        self.groupmgt.addGroupMemberShip("0000", "01", "4003")
        self.groupmgt.addGroupMemberShip("0000", "01", "4004")
        self.groupmgt.addGroupMemberShip("0000", "01", "4005")
        self.groupmgt.addGroupMemberShip("0000", "01", "4006")


def handle_device_specific_needs(self, Devices, NWKID):
    self.log.logging("Pairing", "Debug", "handle_device_specific_needs for %s" %NWKID)
    # In case of Orvibo Scene controller let's Registration
    if "Manufacturer Name" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Manufacturer Name"] == "欧瑞博":
        OrviboRegistration(self, NWKID)

    if "Model" not in self.ListOfDevices[NWKID]:
        return
    device_model = self.ListOfDevices[NWKID]["Model"]

    # Do the Magic Read Attributes
    if get_deviceconf_parameter_value(self, device_model, "TUYA_MAGIC_READ_ATTRIBUTES", return_default=False):
        ReadAttributeRequest_0000_for_tuya( self, NWKID)

    # Tuya_regitration ?
    tuya_registration_parameter = get_deviceconf_parameter_value(self, device_model, "TUYA_REGISTRATION", return_default=None)
    tuya_data_request = get_deviceconf_parameter_value(self, device_model, "TUYA_RESET_CMD", return_default=False) 
    tuya_data_request_polling = get_deviceconf_parameter_value(self, device_model, "TUYA_DATA_REQUEST_POLLING", return_default=False)
    
    self.log.logging("Pairing", "Debug", f"handle_device_specific_needs for {NWKID} tuya_registration_parameter: {tuya_registration_parameter} tuya_data_request: {tuya_data_request} tuya_data_request_polling: {tuya_data_request_polling}")

    # In case of Schneider Wiser, let's do the Registration Process
    MsgIEEE = self.ListOfDevices[NWKID]["IEEE"]
    if device_model in ("Wiser2-Thermostat",):
        wiser_home_lockout_thermostat(self, NWKID, 0)

    if get_device_config_param( self, NWKID, "AqaraMultiClick"):
        enable_click_mode_aqara( self, NWKID)

    if ( MsgIEEE[: PREFIX_MAC_LEN] in PREFIX_MACADDR_WIZER_LEGACY and WISER_LEGACY_MODEL_NAME_PREFIX in device_model ):
        self.log.logging("Pairing", "Debug", "Wiser Legacy registration needed for %s" %NWKID)
        schneider_wiser_registration(self, Devices, NWKID)

    if device_model in ( "AC201A", "AC211", "AC221", "CAC221" ):
        self.log.logging("Pairing", "Debug", "CasaIA registration needed")
        casaia_pairing(self, NWKID)

    if device_model in ("TS0601-sirene",):
        self.log.logging("Pairing", "Debug", "Tuya Sirene registration needed")
        tuya_sirene_registration(self, NWKID)

    if device_model in (TUYA_eTRV_MODEL):
        self.log.logging("Pairing", "Debug", "Tuya eTRV registration needed")
        tuya_eTRV_registration(self, NWKID, tuya_data_request=True)
        
    if tuya_registration_parameter:
        tuya_registration(self, NWKID, ty_data_request=tuya_data_request, parkside=False, tuya_registration_value=tuya_registration_parameter)

    if device_model in ("TS0121", "TS0002_relay_switch", "TS0002_relay_switch"):
        self.log.logging("Pairing", "Debug", "Tuya TS0121 registration needed")
        tuya_TS0121_registration(self, NWKID)

    if device_model in ("TS004F", "TS004F-_TZ3000_xabckq1v"):
        self.log.logging("Pairing", "Debug", "Tuya TS004F registration needed")
        if "Param" in self.ListOfDevices[NWKID] and "TS004FMode" in self.ListOfDevices[NWKID]["Param"]:
            tuya_cmd_ts004F(self, NWKID, self.ListOfDevices[NWKID]["Param"]["TS004FMode" ])
            ReadAttributeReq( self, NWKID, ZIGATE_EP, "01", "0006", [ 0x8004 ], ackIsDisabled=False, checkTime=False, )

    if device_model in ( "TS0222", "TS0002_relay_switch", "TS0003_relay_switch", 'TS0601-motion'):
        tuya_command_f0( self, NWKID )

    if tuya_data_request_polling:
        self.log.logging("Pairing", "Debug", "Tuya Tuya Polling requested")
        tuya_polling(self, NWKID)

    if device_model in (
        "TS0601-Energy",
        "TS0601-switch",
        "TS0601-2Gangs-switch",
        "TS0601-SmartAir",
        "TS130F-_TZ3000_femsaaua",
        "TS130F-_TZ3000_8kzqqzu4",
        "TS130F-_TZ3000_1dd0d5yi",
        "TS130F-_TZ3000_zirycpws",
        "TS130F-_TZ3000_fvhunhxb",
        "TS0601-temphumi",
    ):
        self.log.logging("Pairing", "Debug", "Tuya general registration needed")
        tuya_registration(self, NWKID, ty_data_request=True)

    if device_model in ("TS0601-Parkside-Watering-Timer", "TS0601-_TZE200_nklqjk62", ):
        self.log.logging("Pairing", "Debug", "Tuya Water Sensor Parkside registration needed")
        tuya_registration(self, NWKID, ty_data_request=True, parkside=True)

    if device_model in ( "TS0216", "TY0A01", ):
        # Do just the registration
        tuya_registration(self, NWKID )

    if device_model == "SPZB0001":
        thermostat_Calibration(self, NWKID, 0x00)

    if device_model == "lumi.remote.b28ac1":
        enable_click_mode_aqara( self, NWKID )
        enableOppleSwitch( self, NWKID )
    
    if get_deviceconf_parameter_value( self, self.ListOfDevices[NWKID]["Model"], "TuyaCommandF0"):
        tuya_command_f0( self, NWKID )

    if get_deviceconf_parameter_value(self, self.ListOfDevices[NWKID]["Model"], "LightingColorControl", return_default=None):
        tuya_lighting_color_control(self, NWKID)


def scan_device_for_group_memebership(self, NWKID):
    for ep in self.ListOfDevices[NWKID]["Ep"]:
        if "0004" in self.ListOfDevices[NWKID]["Ep"][ep] and self.groupmgt:
            self.groupmgt.ScanDevicesForGroupMemberShip( [ NWKID, ] )
            break


def request_list_of_attributes(self, NWKID):
    for iterEp in self.ListOfDevices[NWKID]["Ep"]:
        self.log.logging("Pairing", "Debug", "looking for List of Attributes ep: %s" % iterEp)
        for iterCluster in self.ListOfDevices[NWKID]["Ep"][iterEp]:
            if iterCluster in ("Type", "ClusterType", "ColorMode"):
                continue
            if "ConfigSource" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["ConfigSource"] != "DeviceConf":
                getListofAttribute(self, NWKID, iterEp, iterCluster)
