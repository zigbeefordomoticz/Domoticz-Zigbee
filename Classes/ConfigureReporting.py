#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: ConfigureReporting.py

    Description: Configure Reporting of all connected object, based on their corresponding cluster

"""

import time

import Domoticz
from Modules.bindings import bindDevice, unbindDevice
from Modules.tools import (get_isqn_datastruct, get_list_isqn_attr_datastruct,
                           getClusterListforEP, is_ack_tobe_disabled,
                           is_attr_unvalid_datastruct, is_bind_ep, is_fake_ep,
                           is_time_to_perform_work, mainPoweredDevice,
                           reset_attr_datastruct, set_isqn_datastruct,
                           set_status_datastruct, set_timestamp_datastruct)
from Modules.zigateConsts import (MAX_LOAD_ZIGATE, ZIGATE_EP,
                                  CFG_RPT_ATTRIBUTESbyCLUSTERS)
from Zigbee.zclCommands import (zcl_configure_reporting_requestv2,
                                zcl_read_report_config_request)
from Zigbee.zdpCommands import ( zdp_NWK_address_request)

from Classes.ZigateTransport.sqnMgmt import (TYPE_APP_ZCL,
                                             sqn_get_internal_sqn_from_app_sqn)

MAX_ATTR_PER_REQ = 3
CONFIGURE_REPORT_PERFORM_TIME = 21  # Reenforce will be done each xx hours


class ConfigureReporting:
    def __init__(
        self,
        zigbee_communitation,
        PluginConf,
        DeviceConf,
        ZigateComm,
        ListOfDevices,
        Devices,
        log,
        busy,
        FirmwareVersion,
        IEEE2NWK,
        ZigateIEEE,
    ):

        self.zigbee_communication = zigbee_communitation
        self.pluginconf = PluginConf
        self.DeviceConf = DeviceConf
        self.ControllerLink = ZigateComm
        self.ListOfDevices = ListOfDevices
        self.Devices = Devices
        self.log = log
        self.busy = busy
        self.FirmwareVersion = FirmwareVersion

        # Needed for bind
        self.IEEE2NWK = IEEE2NWK
        self.ControllerIEEE = ZigateIEEE

        # Local
        self.target = []

    def logging(self, logType, message, nwkid=None, context=None):
        self.log.logging("ConfigureReporting", logType, message, nwkid, context)

    # Commands
    
    def processConfigureReporting(self, NwkId=None):

        if NwkId:
            configure_reporting_for_one_device( self, NwkId, False, )
            return
        for key in list(self.ListOfDevices.keys()):
            if self.busy or self.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE:
                self.logging(
                    "Debug",
                    f"configureReporting - skip configureReporting for now ... system too busy ({self.busy}/{self.ControllerLink.loadTransmit()}) for {NwkId}",
                    nwkid=NwkId,
                )
                return  # Will do at the next round
            configure_reporting_for_one_device(self, key, True)

    def cfg_reporting_on_demand(self, nwkid):
        # Remove Cfg Rpt tracking attributes
        if "ConfigureReporting" in self.ListOfDevices[nwkid]:
            del self.ListOfDevices[nwkid]["ConfigureReporting"]
        configure_reporting_for_one_device(self, nwkid, False)

    def prepare_and_send_configure_reporting(
        self, key, Ep, cluster_configuration, cluster, direction, manufacturer_spec, manufacturer, ListOfAttributesToConfigure
    ):

        # Create the list of Attribute reporting configuration for a specific cluster
        # Finally send the command
        self.logging("Debug", f"------ prepare_and_send_configure_reporting - key: {key} ep: {Ep} cluster: {cluster} Cfg: {cluster_configuration}", nwkid=key)

        maxAttributesPerRequest = MAX_ATTR_PER_REQ
        if self.pluginconf.pluginConf["breakConfigureReporting"]:
            maxAttributesPerRequest = 1

        attribute_reporting_configuration = []
        for attr in ListOfAttributesToConfigure:
            attrType = cluster_configuration[attr]["DataType"]
            minInter = cluster_configuration[attr]["MinInterval"]
            maxInter = cluster_configuration[attr]["MaxInterval"]
            timeOut = cluster_configuration[attr]["TimeOut"]
            chgFlag = cluster_configuration[attr]["Change"]

            if analog_value(int(attrType, 16)):
                # Analog values: For attributes with 'analog' data type (see 2.6.2), the "rptChg" has the same data type as the attribute. The sign (if any) of the reportable change field is ignored.
                attribute_reporting_record = {
                    "Attribute": attr,
                    "DataType": attrType,
                    "minInter": minInter,
                    "maxInter": maxInter,
                    "rptChg": chgFlag,
                    "timeOut": timeOut,
                }
            elif discrete_value(int(attrType, 16)):
                # Discrete value: For attributes of 'discrete' data type (see 2.6.2), "rptChg" field is omitted.
                attribute_reporting_record = {
                    "Attribute": attr,
                    "DataType": attrType,
                    "minInter": minInter,
                    "maxInter": maxInter,
                    "timeOut": timeOut,
                }
            elif composite_value(int(attrType, 16)):
                # Composite value: assumed "rptChg" is omitted
                attribute_reporting_record = {
                    "Attribute": attr,
                    "DataType": attrType,
                    "minInter": minInter,
                    "maxInter": maxInter,
                    "timeOut": timeOut,
                }
            else:
                self.logging(
                    "Error",
                    f"--------> prepare_and_send_configure_reporting - Unexpected Data Type: Cluster: {cluster} Attribut: {attr} DataType: {attrType}",
                )
                continue

            attribute_reporting_configuration.append(attribute_reporting_record)

            if len(attribute_reporting_configuration) == maxAttributesPerRequest:
                self.send_configure_reporting_attributes_set(
                    key,
                    ZIGATE_EP,
                    Ep,
                    cluster,
                    direction,
                    manufacturer_spec,
                    manufacturer,
                    attribute_reporting_configuration,
                )
                # Reset the Lenght to 0
                attribute_reporting_configuration = []

        # Send remaining records
        if attribute_reporting_configuration:
            self.send_configure_reporting_attributes_set(
                key,
                ZIGATE_EP,
                Ep,
                cluster,
                direction,
                manufacturer_spec,
                manufacturer,
                attribute_reporting_configuration,
            )

    def send_configure_reporting_attributes_set(
        self,
        key,
        ZIGATE_EP,
        Ep,
        cluster,
        direction,
        manufacturer_spec,
        manufacturer,
        attribute_reporting_configuration,
    ):
        self.logging(
            "Debug",
            f"----------> send_configure_reporting_attributes_set Reporting {key}/{Ep} on cluster {cluster} Len: {len(attribute_reporting_configuration)} Attribute List: {str(attribute_reporting_configuration)}",
            nwkid=key,
        )

        i_sqn = zcl_configure_reporting_requestv2(
            self,
            key,
            ZIGATE_EP,
            Ep,
            cluster,
            direction,
            manufacturer_spec,
            manufacturer,
            attribute_reporting_configuration,
            is_ack_tobe_disabled(self, key),
        )
        for x in attribute_reporting_configuration:
            set_isqn_datastruct(self, "ConfigureReporting", key, Ep, cluster, x["Attribute"], i_sqn)

    # Receiving messages
    def read_configure_reporting_response(self, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttributeId, MsgStatus):
        if self.FirmwareVersion and int(self.FirmwareVersion, 16) >= int("31d", 16) and MsgAttributeId:
            set_status_datastruct(
                self,
                "ConfigureReporting",
                MsgSrcAddr,
                MsgSrcEp,
                MsgClusterId,
                MsgAttributeId,
                MsgStatus,
            )
            if MsgStatus != "00":
                self.logging(
                    "Debug",
                    f"Configure Reporting response - ClusterID: {MsgClusterId}/{MsgAttributeId}, MsgSrcAddr: {MsgSrcAddr}, MsgSrcEp:{MsgSrcEp} , Status: {MsgStatus}",
                    MsgSrcAddr,
                )

            return

        # We got a global status for all attributes requested in this command
        # We need to find the Attributes related to the i_sqn
        i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSQN, TYPE_APP_ZCL)
        self.logging("Debug", "------- - i_sqn: %0s e_sqn: %s" % (i_sqn, MsgSQN))

        for matchAttributeId in list(get_list_isqn_attr_datastruct(self, "ConfigureReporting", MsgSrcAddr, MsgSrcEp, MsgClusterId)):
            if (
                get_isqn_datastruct(
                    self,
                    "ConfigureReporting",
                    MsgSrcAddr,
                    MsgSrcEp,
                    MsgClusterId,
                    matchAttributeId,
                )
                != i_sqn
            ):
                continue

            self.logging("Debug", f"------- - Sqn matches for Attribute: {matchAttributeId}")

            set_status_datastruct(
                self,
                "ConfigureReporting",
                MsgSrcAddr,
                MsgSrcEp,
                MsgClusterId,
                matchAttributeId,
                MsgStatus,
            )
            if MsgStatus != "00":
                self.logging(
                    "Debug",
                    f"Configure Reporting response - ClusterID: {MsgClusterId}/{matchAttributeId}, MsgSrcAddr: {MsgSrcAddr}, MsgSrcEp:{MsgSrcEp} , Status: {MsgStatus}",
                    MsgSrcAddr,
                )

    def read_report_configure_response(self, MsgData, MsgLQI):  # Read Configure Report response
        MsgSQN = MsgData[:2]
        MsgNwkId = MsgData[2:6]
        MsgEp = MsgData[6:8]
        MsgClusterId = MsgData[8:12]
        MsgStatus = MsgData[12:14]

        if MsgStatus != "00":

            return

        MsgAttributeDataType = MsgData[14:16]
        MsgAttribute = MsgData[16:20]
        MsgMaximumReportingInterval = MsgData[20:24]
        MsgMinimumReportingInterval = MsgData[24:28]

        self.logging(
            "Log",
            f"Read Configure Reporting response - NwkId: {MsgNwkId} Ep: {MsgEp} Cluster: {MsgClusterId} Attribute: {MsgAttribute} DataType: {MsgAttributeDataType} Max: {MsgMaximumReportingInterval} Min: {MsgMinimumReportingInterval}",
            MsgNwkId,
        )

    def retreive_configuration_reporting_definition(self, NwkId):
    
        if "ParamConfigureReporting" in self.ListOfDevices[NwkId]:
            return self.ListOfDevices[NwkId][ "ParamConfigureReporting" ]

        if (
            "Model" in self.ListOfDevices[NwkId]
            and self.ListOfDevices[NwkId]["Model"] != {}
            and self.ListOfDevices[NwkId]["Model"] in self.DeviceConf
            and "ConfigureReporting" in self.DeviceConf[self.ListOfDevices[NwkId]["Model"]]
        ):
            return self.DeviceConf[self.ListOfDevices[NwkId]["Model"]]["ConfigureReporting"]
        
        return CFG_RPT_ATTRIBUTESbyCLUSTERS


####

def configure_reporting_for_one_device(self, key, batchMode):
    self.logging("Debug", f"configure_reporting_for_one_device - key: {key} batchMode: {batchMode}", nwkid=key)
    # Let's check that we can do a Configure Reporting. Only during the pairing process (NWKID is provided) or we are on the Main Power
    if key == "0000":
        return

    if key not in self.ListOfDevices:
        self.logging("Debug", f"processConfigureReporting - Unknown key: {key}", nwkid=key)
        return

    if "Status" not in self.ListOfDevices[key]:
        self.logging("Debug", "processConfigureReporting - no 'Status' flag for device %s !!!" % key, nwkid=key)
        return

    if self.ListOfDevices[key]["Status"] != "inDB":
        return

    if batchMode and not mainPoweredDevice(self, key):
        return  # Not Main Powered!

    if batchMode and "Health" in self.ListOfDevices[key] and self.ListOfDevices[key]["Health"] == "Not Reachable":
        return

    cfgrpt_configuration = self.retreive_configuration_reporting_definition( key)

    self.logging("Debug", f"configure_reporting_for_one_device - processing {key} with {cfgrpt_configuration}", nwkid=key)

    for Ep in self.ListOfDevices[key]["Ep"]:
        configure_reporting_for_one_endpoint(self, key, Ep, batchMode, cfgrpt_configuration)


def configure_reporting_for_one_endpoint(self, key, Ep, batchMode, cfgrpt_configuration):
    self.logging("Debug", f"-- configure_reporting_for_one_endpoint - key: {key} ep: {Ep} batchMode: {batchMode} Cfg: {cfgrpt_configuration}", nwkid=key)
    
    if is_fake_ep(self, key, Ep):
        self.logging("Debug", f"--> configure_reporting_for_one_endpoint - Fake Ep {key}/{Ep} skiping", nwkid=key)
        return

    if not is_bind_ep(self, key, Ep):
        self.logging("Debug", f"--> configure_reporting_for_one_endpoint - Not Binding ep {key}/{Ep} skiping", nwkid=key)
        return

    clusterList = getClusterListforEP(self, key, Ep)
    self.logging("Debug", f"--> configure_reporting_for_one_endpoint - processing {key}/{Ep} ClusterList: {clusterList}", nwkid=key)

    now = time.time()
    for cluster in clusterList:
        if cluster not in cfgrpt_configuration:
            self.logging("Debug", f"----> configure_reporting_for_one_endpoint - processing {key}/{Ep} {cluster} not in {clusterList}", nwkid=key)
            continue

        if not do_we_have_to_do_the_work(self, key, Ep, cluster):
            self.logging("Debug", f"----> configure_reporting_for_one_endpoint - Not Binding ep {key}/{Ep} skiping", nwkid=key)
            continue

        # Configure Reporting must be done because:
        # (1) 'ConfigureReporting' do not exist
        # (2) 'ConfigureReporting' is empty
        # (3) if reenforceConfigureReporting is enabled and it is time to do the work
        if batchMode and "ConfigureReporting" in self.ListOfDevices[key] and len(self.ListOfDevices[key]["ConfigureReporting"]) != 0:
            if self.pluginconf.pluginConf["reenforceConfigureReporting"]:
                if not is_time_to_perform_work(
                    self,
                    "ConfigureReporting",
                    key,
                    Ep,
                    cluster,
                    now,
                    (CONFIGURE_REPORT_PERFORM_TIME * 3600),
                ):
                    self.logging("Debug", f"----> configure_reporting_for_one_endpoint Not time to perform  {key}/{Ep} - {cluster}", nwkid=key)

                    continue
            else:
                self.logging(
                    "Debug",
                    "----> configure_reporting_for_one_endpoint ['reenforceConfigureReporting']: %s then skip" % self.pluginconf.pluginConf["reenforceConfigureReporting"],
                )
                continue

        if batchMode and (self.busy or self.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE):
            self.logging(
                "Debug",
                f"----> configure_reporting_for_one_endpoint - {key} skip configureReporting for now ... system too busy ({self.busy}/{self.ControllerLink.loadTransmit()}) for {key}",
                nwkid=key,
            )

            return  # Will do at the next round

        self.logging("Debug", f"----> configure_reporting_for_one_endpoint - requested for device: {key} on Cluster: {cluster}", nwkid=key)

        # If NWKID is not None, it means that we are asking a ConfigureReporting for a specific device
        # Which happens on the case of New pairing, or a re-join
        do_rebind_if_needed(self, key, Ep, batchMode, cluster)

        if "Attributes" not in cfgrpt_configuration[ cluster ]:
            self.logging("Debug", f"----> configure_reporting_for_one_endpoint - for device: {key} on Cluster: {cluster} no Attributes key on {cfgrpt_configuration[ cluster ]}", nwkid=key)
            continue
        
        set_timestamp_datastruct(self, "ConfigureReporting", key, Ep, cluster, time.time())
        configure_reporting_for_one_cluster(self, key, Ep, cluster, cfgrpt_configuration[cluster]["Attributes"])


def configure_reporting_for_one_cluster(self, key, Ep, cluster, cluster_configuration):
    self.logging("Debug", f"---- configure_reporting_for_one_cluster - key: {key} ep: {Ep} cluster: {cluster} Cfg: {cluster_configuration}", nwkid=key)

    manufacturer = "0000"
    manufacturer_spec = "00"
    direction = "00"

    ListOfAttributesToConfigure = []
    for attr in cluster_configuration:
        # Check if the Attribute is listed in the Attributes List (provided by the Device
        # In case Attributes List exists, we have give the list of reported attribute.
        if cluster == "0300":
            # We need to evaluate the Attribute on ZDevice basis
            if self.ListOfDevices[key]["ZDeviceID"] == {}:
                continue

            ZDeviceID = self.ListOfDevices[key]["ZDeviceID"]
            if "ZDeviceID" in cluster_configuration[attr] and (
                ZDeviceID not in cluster_configuration[attr]["ZDeviceID"] and len(cluster_configuration[attr]["ZDeviceID"]) != 0
            ):
                self.logging(
                    "Debug",
                    f"------> configure_reporting_for_one_cluster - {key}/{Ep} skip Attribute {attr} for Cluster {cluster} due to ZDeviceID {ZDeviceID}",
                    nwkid=key,
                )
                continue

        # Check against Attribute List only if the Model is not defined in the Certified Conf.
        if not is_valid_attribute(self, key, Ep, cluster, attr):
            continue

        if is_tobe_skip(self, key, Ep, cluster, attr):
            continue

        # Check if we have a Manufacturer Specific Cluster/Attribute. If that is the case, we need to send what we have ,
        # and then pile what we have until we switch back to non manufacturer specific
        manufacturer_code = manufacturer_specific_attribute(self, key, cluster, attr, cluster_configuration[attr])
        if manufacturer_code:
            # Send what we have
            if ListOfAttributesToConfigure:
                self.prepare_and_send_configure_reporting(
                    key,
                    Ep,
                    cluster_configuration,
                    cluster,
                    direction,
                    manufacturer_spec,
                    manufacturer,
                    ListOfAttributesToConfigure,
                )

            self.logging("Debug", f"------> configure_reporting_for_one_cluster Reporting: Manuf Specific Attribute {attr}", nwkid=key)

            # Process the Attribute
            ListOfAttributesToConfigure = []
            manufacturer_spec = "01"

            ListOfAttributesToConfigure.append(attr)
            self.prepare_and_send_configure_reporting(
                key,
                Ep,
                cluster_configuration,
                cluster,
                direction,
                manufacturer_spec,
                manufacturer_code,
                ListOfAttributesToConfigure,
            )

            # Look for the next attribute and do not assume it is Manuf Specif
            ListOfAttributesToConfigure = []

            manufacturer_spec = "00"
            manufacturer = "0000"

            continue  # Next Attribute

        ListOfAttributesToConfigure.append(attr)
        self.logging("Debug", f"------> configure_reporting_for_one_cluster  {key}/{Ep} Cluster {cluster} Adding attr: {attr} ", nwkid=key)

        self.prepare_and_send_configure_reporting(
            key,
            Ep,
            cluster_configuration,
            cluster,
            direction,
            manufacturer_spec,
            manufacturer,
            ListOfAttributesToConfigure,
        )


def read_report_configure_request(self, nwkid, epout, cluster_id, attribute_list, manuf_specific="00", manuf_code="0000"):

    nb_attribute = "%02x" % len(attribute_list)
    str_attribute_list = "".join("%04x" % x for x in attribute_list)
    direction = "00"
    # datas = nwkid + ZIGATE_EP + epout + cluster_id + direction + nb_attribute + manuf_specific + manuf_code + str_attribute_list

    zcl_read_report_config_request(
        self,
        nwkid,
        ZIGATE_EP,
        epout,
        cluster_id,
        direction,
        manuf_specific,
        manuf_code,
        nb_attribute,
        str_attribute_list,
        is_ack_tobe_disabled(self, nwkid),
    )


def do_rebind_if_needed(self, nwkid, Ep, batchMode, cluster):
    if batchMode and self.pluginconf.pluginConf["allowReBindingClusters"]:
        lookup_ieee = self.ListOfDevices[nwkid]["IEEE"]
        zdp_NWK_address_request(self, "fffc", lookup_ieee, )
        # Correctif 22 Novembre. Delete only for the specific cluster and not the all Set
        if (
            "Bind" in self.ListOfDevices[nwkid]
            and Ep in self.ListOfDevices[nwkid]["Bind"]
            and cluster in self.ListOfDevices[nwkid]["Bind"][Ep]
        ):
            del self.ListOfDevices[nwkid]["Bind"][Ep][cluster]
        if "IEEE" in self.ListOfDevices[nwkid]:
            self.logging("Debug", f"---> configureReporting - requested Bind for {nwkid} on Cluster: {cluster}", nwkid=nwkid)
            if self.pluginconf.pluginConf["doUnbindBind"]:
                unbindDevice(self, self.ListOfDevices[nwkid]["IEEE"], Ep, cluster)
            bindDevice(self, self.ListOfDevices[nwkid]["IEEE"], Ep, cluster)
        else:
            self.logging("Error", f"configureReporting - inconsitency on {nwkid} no IEEE found : {str(self.ListOfDevices[nwkid])} ")


def do_we_have_to_do_the_work(self, NwkId, Ep, cluster):

    if cluster in ("Type", "ColorMode", "ClusterType"):
        return False
    if "Model" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Model"] != {}:
        if self.ListOfDevices[NwkId]["Model"] == "lumi.light.aqcn02" and cluster in (
            "0402",
            "0403",
            "0405",
            "0406",
        ):
            return False

        if self.ListOfDevices[NwkId]["Model"] == "lumi.remote.b686opcn01" and Ep != "01":
            # We bind only on EP 01
            self.logging("Debug", f"Do not Configure Reporting lumi.remote.b686opcn01 to Zigate Ep {Ep} Cluster {cluster}", NwkId)

            return False

    # Bad Hack for now. FOR PROFALUX
    if self.ListOfDevices[NwkId]["ProfileID"] == "0104" and self.ListOfDevices[NwkId]["ZDeviceID"] == "0201":  # Remote
        # Do not Configure Reports Remote Command
        self.logging("Debug", f"----> Do not Configure Reports cluster {cluster} for Profalux Remote command {NwkId}/{Ep}", NwkId)

        return False
    return True


def is_valid_attribute(self, nwkid, Ep, cluster, attr):
    if (
        (
            "Model" in self.ListOfDevices[nwkid]
            and self.ListOfDevices[nwkid]["Model"] != {}
            and self.ListOfDevices[nwkid]["Model"] not in self.DeviceConf
            and "Attributes List" in self.ListOfDevices[nwkid]
        )
        and "Ep" in self.ListOfDevices[nwkid]["Attributes List"]
        and Ep in self.ListOfDevices[nwkid]["Attributes List"]["Ep"]
        and cluster in self.ListOfDevices[nwkid]["Attributes List"]["Ep"][Ep]
        and attr not in self.ListOfDevices[nwkid]["Attributes List"]["Ep"][Ep][cluster]
    ):
        self.logging("Debug", f"configureReporting: drop attribute {attr}", nwkid=nwkid)
        return False
    return True


def is_tobe_skip(self, nwkid, Ep, Cluster, attr):
    
    if self.FirmwareVersion and int(self.FirmwareVersion, 16) <= int("31c", 16):
        if is_attr_unvalid_datastruct(self, "ConfigureReporting", nwkid, Ep, Cluster, "0000"):
            return True
        reset_attr_datastruct(self, "ConfigureReporting", nwkid, Ep, Cluster, "0000")

    if self.FirmwareVersion and int(self.FirmwareVersion, 16) > int("31c", 16):
        if is_attr_unvalid_datastruct(self, "ConfigureReporting", nwkid, Ep, Cluster, attr):
            return True
        reset_attr_datastruct(self, "ConfigureReporting", nwkid, Ep, Cluster, attr)
    return False


def manufacturer_specific_attribute(self, key, cluster, attr, cfg_attribute):

    # Return False if the attribute is not a manuf specific, otherwise return the Manufacturer code
    if "ManufSpecific" in cfg_attribute:
        self.logging(
            "Log",
            f'manufacturer_specific_attribute - NwkId: {key} found attribute: {attr} Manuf Specific, return ManufCode: {cfg_attribute["ManufSpecific"]}',
        )

        return cfg_attribute["ManufSpecific"]

    if (
        attr
        in (
            "4000",
            "4012",
        )
        and cluster == "0201"
        and "Model" in self.ListOfDevices[key]
        and self.ListOfDevices[key]["Model"] in ("eT093WRO", "eTRV0100")
    ):
        return "1246"

    if (
        attr in ("fd00",)
        and cluster == "0201"
        and "Model" in self.ListOfDevices[key]
        and self.ListOfDevices[key]["Model"] in ("AC221", "AC211")
    ):
        return "113c"

    if cluster == "fc21" and "Manufacturer" in self.ListOfDevices[key] and self.ListOfDevices[key]["Manufacturer"] == "1110":
        return "1110"

    if (
        attr
        in (
            "0030",
            "0031",
        )
        and cluster == "0406"
        and "Manufacturer" in self.ListOfDevices[key]
        and self.ListOfDevices[key]["Manufacturer"] == "100b"
    ):
        return "100b"


def discrete_value(data_type):
    return data_type in (
        0x08,
        0x09,
        0x0A,
        0x0B,
        0x0C,
        0x0D,
        0x0E,
        0x0F,
        0x10,
        0x18,
        0x19,
        0x1A,
        0x1B,
        0x1C,
        0x1D,
        0x1E,
        0x1F,
        0x30,
        0x31,
        0xE8,
        0xE9,
        0xEA,
        0xF0,
        0xF1,
    )


def analog_value(data_type):
    return data_type in (
        0x20,
        0x21,
        0x22,
        0x23,
        0x24,
        0x25,
        0x26,
        0x27,
        0x28,
        0x29,
        0x2A,
        0x2B,
        0x2C,
        0x2D,
        0x2E,
        0x2F,
        0x38,
        0x39,
        0x3A,
        0xE0,
        0xE1,
        0xE2,
    )


def composite_value(data_type):
    return data_type in (
        0x41,
        0x42,
        0x43,
        0x44,
        0x48,
        0x4C,
        0x50,
        0x51,
    )
