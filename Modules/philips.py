#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import Domoticz

from datetime import datetime
from time import time

from Modules.basicOutputs import set_poweron_afteroffon, write_attribute, raw_APS_request
from Modules.readAttributes import (
    ReadAttributeRequest_0006_0000,
    ReadAttributeRequest_0008_0000,
    ReadAttributeRequest_0006_400x,
    ReadAttributeRequest_0406_philips_0030,
)
from Modules.tools import retreive_cmd_payload_from_8002, is_ack_tobe_disabled
from Modules.zigateConsts import ZIGATE_EP

from Classes.LoggingManagement import LoggingManagement

PHILIPS_POWERON_MODE = {0x00: "Off", 0x01: "On", 0xFF: "Previous state"}  # Off  # On  # Previous state


def pollingPhilips(self, key):
    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """

    # if  ( self.busy or self.ZigateComm.loadTransmit() > MAX_LOAD_ZIGATE):
    #    return True

    ReadAttributeRequest_0006_0000(self, key)
    ReadAttributeRequest_0008_0000(self, key)

    return False


def callbackDeviceAwake_Philips(self, Devices, NwkId, EndPoint, cluster):
    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part
    """

    Domoticz.Log("callbackDeviceAwake_Legrand - Nwkid: %s, EndPoint: %s cluster: %s" % (NwkId, EndPoint, cluster))


def default_response_for_philips_hue_reporting_attribute(self, Nwkid, srcEp, cluster, sqn):

    fcf = "10"
    cmd = "0b"
    cmd_reporting_attribute = "0a"
    status = "00"
    payload = fcf + sqn + cmd + cmd_reporting_attribute + "00"
    raw_APS_request(self, Nwkid, srcEp, cluster, "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=False)
    self.log.logging("Philips", "Log", "default_response_for_philips_hue_reporting_attribute - %s/%s " % (Nwkid, srcEp))


def philipsReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):

    # Zigbee Command:
    # 0x00: Read Attributes
    # 0x01: Read Attributes Response
    # 0x02: Write Attributes
    # 0x03:
    # 0x04: Write Attributes Response
    # 0x06: Configure Reporting
    # 0x0A: Report Attributes
    # 0x0C: Discover Attributes
    # 0x0D: Discover Attributes Response

    if srcNWKID not in self.ListOfDevices:
        return

    self.log.logging(
        "Philips",
        "Debug",
        "philipsReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s"
        % (srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload),
        srcNWKID,
    )

    # Motion
    # Nwkid: 329c/02 Cluster: 0001, Command: 07 Payload: 00
    # Nwkid: 329c/02 Cluster: 0001, Command: 0a Payload: 21002050

    if "Model" not in self.ListOfDevices[srcNWKID]:
        return

    _ModelName = self.ListOfDevices[srcNWKID]["Model"]

    GlobalCommand, sqn, ManufacturerCode, cmd, data = retreive_cmd_payload_from_8002(MsgPayload)

    if _ModelName == "RWL021" and cmd == "00" and ClusterID == "fc00":
        # This is handle by the firmware
        return

    self.log.logging(
        "Philips",
        "Log",
        "philipsReadRawAPS - Nwkid: %s/%s Cluster: %s, GlobalCommand: %s sqn: %s, Command: %s Payload: %s"
        % (srcNWKID, srcEp, ClusterID, GlobalCommand, sqn, cmd, data),
    )


def philips_set_pir_occupancySensibility(self, nwkid, level):

    if level in (0, 1, 2):
        write_attribute(
            self, nwkid, ZIGATE_EP, "02", "0406", "100b", "01", "0030", "20", "%02x" % level, ackIsDisabled=True
        )
        ReadAttributeRequest_0406_philips_0030(self, nwkid)


def philips_set_poweron_after_offon(self, mode):
    # call from WebServer

    if mode not in PHILIPS_POWERON_MODE:
        Domoticz.Error("philips_set_poweron_after_offon - Unknown mode: %s" % mode)

    for nwkid in self.ListOfDevices:
        philips_set_poweron_after_offon_device(self, mode, nwkid)


def philips_set_poweron_after_offon_device(self, mode, nwkid):

    if "Manufacturer" not in self.ListOfDevices[nwkid]:
        return
    if self.ListOfDevices[nwkid]["Manufacturer"] != "100b":
        return
    # We have a Philips device
    if "0b" not in self.ListOfDevices[nwkid]["Ep"]:
        return
    if "0006" not in self.ListOfDevices[nwkid]["Ep"]["0b"]:
        return
    if "4003" not in self.ListOfDevices[nwkid]["Ep"]["0b"]["0006"]:
        Domoticz.Log("philips_set_poweron_after_offon Device: %s do not have a Set Power Attribute !" % nwkid)
        ReadAttributeRequest_0006_400x(self, nwkid)
        return

    # At that stage, we have a Philips device with Cluster 0006 and the right attribute
    self.log.logging(
        "Philips",
        "Debug",
        "philips_set_poweron_after_offon - Set PowerOn after OffOn of %s to %s" % (nwkid, PHILIPS_POWERON_MODE[mode]),
    )
    set_poweron_afteroffon(self, nwkid, OnOffMode=mode)
    ReadAttributeRequest_0006_400x(self, nwkid)
