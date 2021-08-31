#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_output.py

    Description: All communications towards Zigate

"""

import Domoticz
import binascii
import struct
import json

from datetime import datetime
from time import time

from Classes.LoggingManagement import LoggingManagement

from Modules.basicOutputs import send_zigatecmd_zcl_noack, send_zigatecmd_zcl_ack, ieee_addr_request
from Modules.bindings import bindDevice

from Modules.zigateConsts import MAX_LOAD_ZIGATE, CFG_RPT_ATTRIBUTESbyCLUSTERS, ZIGATE_EP
from Modules.tools import (
    getClusterListforEP,
    mainPoweredDevice,
    is_ack_tobe_disabled,
    check_datastruct,
    is_time_to_perform_work,
    set_isqn_datastruct,
    set_status_datastruct,
    set_timestamp_datastruct,
    is_attr_unvalid_datastruct,
    reset_attr_datastruct,
)


MAX_ATTR_PER_REQ = 3


def processConfigureReporting(self, NWKID=None):
    """
    processConfigureReporting( self )
    Called at start of the plugin to configure Reporting of all connected object, based on their corresponding cluster

    Synopsis:
    - for each Device
        if they support Cluster we want to configure Reporting

    """

    now = int(time())
    if NWKID is None:
        if self.busy or self.ZigateComm.loadTransmit() > MAX_LOAD_ZIGATE:
            self.log.logging(
                "ConfigureReporting",
                "Debug",
                "configureReporting - skip configureReporting for now ... system too busy (%s/%s) for %s"
                % (self.busy, self.ZigateComm.loadTransmit(), NWKID),
                nwkid=NWKID,
            )
            return  # Will do at the next round
        target = list(self.ListOfDevices.keys())
        clusterlist = None
    else:
        target = []
        target.append(NWKID)

    for key in target:
        # Let's check that we can do a Configure Reporting. Only during the pairing process (NWKID is provided) or we are on the Main Power
        if key == "0000":
            continue

        if key not in self.ListOfDevices:
            Domoticz.Error("processConfigureReporting - Unknown key: %s" % key)
            continue

        if "Status" not in self.ListOfDevices[key]:
            Domoticz.Error("processConfigureReporting - no 'Status' flag for device %s !!!" % key)
            continue

        if self.ListOfDevices[key]["Status"] != "inDB":
            continue

        if NWKID is None:
            if not mainPoweredDevice(self, key):
                continue  #  Not Main Powered!

            if "Health" in self.ListOfDevices[key]:
                if self.ListOfDevices[key]["Health"] == "Not Reachable":
                    continue

            # if self.ListOfDevices[key]['Model'] != {}:
            #    if self.ListOfDevices[key]['Model'] == 'TI0001': # Livolo switch
            #        continue

        cluster_list = CFG_RPT_ATTRIBUTESbyCLUSTERS
        if "Model" in self.ListOfDevices[key]:
            if self.ListOfDevices[key]["Model"] != {}:
                if self.ListOfDevices[key]["Model"] in self.DeviceConf:
                    if "ConfigureReporting" in self.DeviceConf[self.ListOfDevices[key]["Model"]]:
                        spec_cfgrpt = self.DeviceConf[self.ListOfDevices[key]["Model"]]["ConfigureReporting"]
                        cluster_list = spec_cfgrpt
                        self.log.logging(
                            "ConfigureReporting",
                            "Debug",
                            "------> CFG_RPT_ATTRIBUTESbyCLUSTERS updated: %s --> %s" % (key, cluster_list),
                            nwkid=key,
                        )

        self.log.logging("ConfigureReporting", "Debug", "----> configurereporting - processing %s" % key, nwkid=key)

        manufacturer = "0000"
        manufacturer_spec = "00"
        direction = "00"

        for Ep in self.ListOfDevices[key]["Ep"]:
            self.log.logging(
                "ConfigureReporting", "Debug", "------> Configurereporting - processing %s/%s" % (key, Ep), nwkid=key
            )
            clusterList = getClusterListforEP(self, key, Ep)
            self.log.logging(
                "ConfigureReporting",
                "Debug",
                "------> Configurereporting - processing %s/%s ClusterList: %s" % (key, Ep, clusterList),
                nwkid=key,
            )
            for cluster in clusterList:
                if cluster in ("Type", "ColorMode", "ClusterType"):
                    continue
                if cluster not in cluster_list:
                    continue
                if "Model" in self.ListOfDevices[key]:
                    if self.ListOfDevices[key]["Model"] != {}:
                        if self.ListOfDevices[key]["Model"] == "lumi.light.aqcn02":
                            if cluster in ("0402", "0403", "0405", "0406"):
                                continue
                        if self.ListOfDevices[key]["Model"] == "lumi.remote.b686opcn01" and Ep != "01":
                            # We bind only on EP 01
                            self.log.logging(
                                "ConfigureReporting",
                                "Debug",
                                "Do not Configure Reporting lumi.remote.b686opcn01 to Zigate Ep %s Cluster %s"
                                % (Ep, cluster),
                                key,
                            )
                            continue

                # Bad Hack for now. FOR PROFALUX
                if self.ListOfDevices[key]["ProfileID"] == "0104":
                    if self.ListOfDevices[key]["ZDeviceID"] == "0201":  # Remote
                        # Do not Configure Reports Remote Command
                        self.log.logging(
                            "ConfigureReporting",
                            "Debug",
                            "----> Do not Configure Reports cluster %s for Profalux Remote command %s/%s"
                            % (cluster, key, Ep),
                            key,
                        )
                        continue

                self.log.logging(
                    "ConfigureReporting",
                    "Debug2",
                    "--------> Configurereporting - processing %s/%s - %s" % (key, Ep, cluster),
                    nwkid=key,
                )

                # Configure Reporting must be done because:
                # (1) 'ConfigureReporting' do not exist
                # (2) 'ConfigureReporting' is empty
                # (3) if reenforceConfigureReporting is enabled and it is time to do the work
                if (
                    NWKID is None
                    and "ConfigureReporting" in self.ListOfDevices[key]
                    and len(self.ListOfDevices[key]["ConfigureReporting"]) != 0
                ):
                    if self.pluginconf.pluginConf["reenforceConfigureReporting"]:
                        if not is_time_to_perform_work(self, "ConfigureReporting", key, Ep, cluster, now, (21 * 3600)):
                            self.log.logging(
                                "ConfigureReporting",
                                "Debug",
                                "--------> Not time to perform  %s/%s - %s" % (key, Ep, cluster),
                                nwkid=key,
                            )
                            continue
                    else:
                        self.log.logging(
                            "ConfigureReporting",
                            "Debug",
                            "-------> ['reenforceConfigureReporting']: %s then skip"
                            % self.pluginconf.pluginConf["reenforceConfigureReporting"],
                        )
                        continue

                if NWKID is None and (self.busy or self.ZigateComm.loadTransmit() > MAX_LOAD_ZIGATE):
                    self.log.logging(
                        "ConfigureReporting",
                        "Debug",
                        "---> configureReporting - %s skip configureReporting for now ... system too busy (%s/%s) for %s"
                        % (key, self.busy, self.ZigateComm.loadTransmit(), key),
                        nwkid=key,
                    )
                    return  # Will do at the next round

                self.log.logging(
                    "ConfigureReporting",
                    "Debug",
                    "---> configureReporting - requested for device: %s on Cluster: %s" % (key, cluster),
                    nwkid=key,
                )

                # If NWKID is not None, it means that we are asking a ConfigureReporting for a specific device
                # Which happens on the case of New pairing, or a re-join
                if NWKID is None and self.pluginconf.pluginConf["allowReBindingClusters"]:
                    ieee_addr_request(self, key)
                    # Correctif 22 Novembre. Delete only for the specific cluster and not the all Set
                    if "Bind" in self.ListOfDevices[key]:
                        if Ep in self.ListOfDevices[key]["Bind"]:
                            if cluster in self.ListOfDevices[key]["Bind"][Ep]:
                                del self.ListOfDevices[key]["Bind"][Ep][cluster]
                    if "IEEE" in self.ListOfDevices[key]:
                        self.log.logging(
                            "ConfigureReporting",
                            "Debug",
                            "---> configureReporting - requested Bind for %s on Cluster: %s" % (key, cluster),
                            nwkid=key,
                        )
                        bindDevice(self, self.ListOfDevices[key]["IEEE"], Ep, cluster)
                    else:
                        Domoticz.Error(
                            "configureReporting - inconsitency on %s no IEEE found : %s "
                            % (key, str(self.ListOfDevices[key]))
                        )

                set_timestamp_datastruct(self, "ConfigureReporting", key, Ep, cluster, int(time()))

                if "Attributes" not in cluster_list[cluster]:
                    continue

                ListOfAttributesToConfigure = []
                for attr in cluster_list[cluster]["Attributes"]:
                    # Check if the Attribute is listed in the Attributes List (provided by the Device
                    # In case Attributes List exists, we have give the list of reported attribute.
                    if cluster == "0300":
                        # We need to evaluate the Attribute on ZDevice basis
                        if self.ListOfDevices[key]["ZDeviceID"] == {}:
                            continue

                        ZDeviceID = self.ListOfDevices[key]["ZDeviceID"]
                        if "ZDeviceID" in cluster_list[cluster]["Attributes"][attr]:
                            if (
                                ZDeviceID not in cluster_list[cluster]["Attributes"][attr]["ZDeviceID"]
                                and len(cluster_list[cluster]["Attributes"][attr]["ZDeviceID"]) != 0
                            ):
                                self.log.logging(
                                    "ConfigureReporting",
                                    "Debug",
                                    "configureReporting - %s/%s skip Attribute %s for Cluster %s due to ZDeviceID %s"
                                    % (key, Ep, attr, cluster, ZDeviceID),
                                    nwkid=key,
                                )
                                continue

                    # Check against Attribute List only if the Model is not defined in the Certified Conf.
                    if (
                        "Model" in self.ListOfDevices[key]
                        and self.ListOfDevices[key]["Model"] != {}
                        and self.ListOfDevices[key]["Model"] not in self.DeviceConf
                        and "Attributes List" in self.ListOfDevices[key]
                    ):
                        if "Ep" in self.ListOfDevices[key]["Attributes List"]:
                            if Ep in self.ListOfDevices[key]["Attributes List"]["Ep"]:
                                if cluster in self.ListOfDevices[key]["Attributes List"]["Ep"][Ep]:
                                    if attr not in self.ListOfDevices[key]["Attributes List"]["Ep"][Ep][cluster]:
                                        self.log.logging(
                                            "ConfigureReporting",
                                            "Debug",
                                            "configureReporting: drop attribute %s" % attr,
                                            nwkid=key,
                                        )
                                        continue

                    if self.FirmwareVersion and int(self.FirmwareVersion, 16) <= int("31c", 16):
                        if is_attr_unvalid_datastruct(self, "ConfigureReporting", key, Ep, cluster, "0000"):
                            continue
                        reset_attr_datastruct(self, "ConfigureReporting", key, Ep, cluster, "0000")

                    if self.FirmwareVersion and int(self.FirmwareVersion, 16) > int("31c", 16):
                        if is_attr_unvalid_datastruct(self, "ConfigureReporting", key, Ep, cluster, attr):
                            continue
                        reset_attr_datastruct(self, "ConfigureReporting", key, Ep, cluster, attr)

                    # Check if we have a Manufacturer Specific Cluster/Attribute. If that is the case, we need to send what we have ,
                    # and then pile what we have until we switch back to non manufacturer specific
                    if (
                        (
                            attr
                            in (
                                "4000",
                                "4012",
                                "fd00",
                            )
                            and cluster == "0201"
                            and "Model" in self.ListOfDevices[key]
                            and self.ListOfDevices[key]["Model"] in ("eT093WRO", "eTRV0100", "AC221", "AC211")
                        )
                        or (
                            cluster == "fc21"
                            and "Manufacturer" in self.ListOfDevices[key]
                            and self.ListOfDevices[key]["Manufacturer"] == "1110"
                        )
                        or (
                            attr
                            in (
                                "0030",
                                "0031",
                            )
                            and cluster == "0406"
                            and "Manufacturer" in self.ListOfDevices[key]
                            and self.ListOfDevices[key]["Manufacturer"] == "100b"
                        )
                    ):

                        # Send what we have
                        if ListOfAttributesToConfigure:
                            prepare_and_send_configure_reporting(
                                self,
                                key,
                                Ep,
                                cluster_list,
                                cluster,
                                direction,
                                manufacturer_spec,
                                manufacturer,
                                ListOfAttributesToConfigure,
                            )

                        self.log.logging(
                            "ConfigureReporting",
                            "Debug",
                            "    Configure Reporting: Manuf Specific Attribute %s" % attr,
                            nwkid=key,
                        )
                        # Process the Attribute
                        ListOfAttributesToConfigure = []
                        manufacturer_spec = "01"
                        if self.ListOfDevices[key]["Model"] in ("eT093WRO", "eTRV0100"):
                            manufacturer = "1246"  # Danfoss
                        elif self.ListOfDevices[key]["Model"] in ("AC221", "AC211"):
                            manufacturer = "113c"
                        elif self.ListOfDevices[key]["Manufacturer"] == "1110":
                            manufacturer = "1110"
                        elif self.ListOfDevices[key]["Manufacturer"] == "100b":
                            manufacturer = "100b"

                        ListOfAttributesToConfigure.append(attr)
                        prepare_and_send_configure_reporting(
                            self,
                            key,
                            Ep,
                            cluster_list,
                            cluster,
                            direction,
                            manufacturer_spec,
                            manufacturer,
                            ListOfAttributesToConfigure,
                        )

                        # Look for the next attribute and do not assume it is Manuf Specif
                        ListOfAttributesToConfigure = []

                        manufacturer_spec = "00"
                        manufacturer = "0000"

                        continue  # Next Attribute

                    ListOfAttributesToConfigure.append(attr)
                    self.log.logging(
                        "ConfigureReporting",
                        "Debug",
                        "    Configure Reporting %s/%s Cluster %s Adding attr: %s " % (key, Ep, cluster, attr),
                        nwkid=key,
                    )
                # end of For attr

                prepare_and_send_configure_reporting(
                    self,
                    key,
                    Ep,
                    cluster_list,
                    cluster,
                    direction,
                    manufacturer_spec,
                    manufacturer,
                    ListOfAttributesToConfigure,
                )

            # End for Cluster
        # End for Ep
    # End for key


def prepare_and_send_configure_reporting(
    self, key, Ep, cluster_list, cluster, direction, manufacturer_spec, manufacturer, ListOfAttributesToConfigure
):

    # Ready to send the Command in one shoot or in several.
    attributeList = []  # List of Attribute in the this flow of Configure Reporting
    attrList = ""  # Command List ready of those attributes and their details
    attrLen = 0  # Number of Attribute

    maxAttributesPerRequest = MAX_ATTR_PER_REQ
    if self.pluginconf.pluginConf["breakConfigureReporting"]:
        maxAttributesPerRequest = 1

    for attr in ListOfAttributesToConfigure:
        attrdirection = "00"
        attrType = cluster_list[cluster]["Attributes"][attr]["DataType"]
        minInter = cluster_list[cluster]["Attributes"][attr]["MinInterval"]
        maxInter = cluster_list[cluster]["Attributes"][attr]["MaxInterval"]
        timeOut = cluster_list[cluster]["Attributes"][attr]["TimeOut"]
        chgFlag = cluster_list[cluster]["Attributes"][attr]["Change"]
        attributeList.append(attr)
        if int(attrType, 16) < 0x30 and int(attrType, 16) not in (0x18, 0x16):
            attrList += attrdirection + attrType + attr + minInter + maxInter + timeOut + chgFlag
        else:
            # Data Type above 0x30 (included) are considered as discret/analog values and the change flag is not considered.
            # in such NXP stack do not expect that information in the payload
            attrList += attrdirection + attrType + attr + minInter + maxInter + timeOut
        attrLen += 1

        # Let's check if we have to send a chunk
        if attrLen == maxAttributesPerRequest:
            send_configure_reporting_attributes_set(
                self, key, Ep, cluster, direction, manufacturer_spec, manufacturer, attrLen, attrList, attributeList
            )

            # Reset the Lenght to 0
            attrList = ""
            attrLen = 0
            del attributeList
            attributeList = []
    # end for

    # Let's check if we have some remaining to send
    if attrLen != 0:
        send_configure_reporting_attributes_set(
            self, key, Ep, cluster, direction, manufacturer_spec, manufacturer, attrLen, attrList, attributeList
        )


def send_configure_reporting_attributes_set(
    self, key, Ep, cluster, direction, manufacturer_spec, manufacturer, attrLen, attrList, attributeList
):
    # Prepare the payload
    datas = ZIGATE_EP + Ep + cluster + direction + manufacturer_spec + manufacturer
    datas += "%02x" % (attrLen) + attrList

    self.log.logging("ConfigureReporting", "Debug", "--> send_configure_reporting_attributes_set - 0120 - %s" % (datas))
    self.log.logging(
        "ConfigureReporting",
        "Debug",
        "--> send_configure_reporting_attributes_set Reporting %s/%s on cluster %s Len: %s Attribute List: %s"
        % (key, Ep, cluster, attrLen, attrList),
        nwkid=key,
    )

    if is_ack_tobe_disabled(self, key):
        i_sqn = send_zigatecmd_zcl_noack(self, key, "0120", datas)
    else:
        i_sqn = send_zigatecmd_zcl_ack(self, key, "0120", datas)

    for x in attributeList:
        set_isqn_datastruct(self, "ConfigureReporting", key, Ep, cluster, x, i_sqn)


def read_report_cpnfigure_request(
    self, nwkid, epout, cluster_id, attribute_list, manuf_specific="00", manuf_code="0000"
):

    nb_attribute = "%02x" % len(attribute_list)
    str_attribute_list = ""
    for x in attribute_list:
        str_attribute_list += "%04x" % x

    direction = "00"
    datas = (
        nwkid
        + ZIGATE_EP
        + epout
        + cluster_id
        + direction
        + nb_attribute
        + manuf_specific
        + manuf_code
        + str_attribute_list
    )

    if is_ack_tobe_disabled(self, nwkid):
        i_sqn = send_zigatecmd_zcl_noack(self, nwkid, "0122", datas)
    else:
        i_sqn = send_zigatecmd_zcl_ack(self, nwkid, "0122", datas)
