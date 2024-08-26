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
    Module: tuya.py

    Description: Tuya specific

"""

from Modules.basicOutputs import raw_APS_request, write_attribute
from Modules.tools import is_ack_tobe_disabled
from Modules.tuyaConst import TUYA_MANUFACTURER_NAME
from Modules.zigateConsts import ZIGATE_EP


def tuya_manufacturer_device(self, NwkId):
    " return True if the NwkId device is a Tuya device, otherwise return False"

    manuf_name = self.ListOfDevices[NwkId]["Manufacturer Name"] if "Manufacturer Name" in self.ListOfDevices[NwkId] else ""
    if manuf_name[:3] in ( "_TY", "_TZ") or manuf_name in TUYA_MANUFACTURER_NAME:
        return True

    model_name = self.ListOfDevices[NwkId]["Model"] if "Model" in self.ListOfDevices[NwkId] else ""
    if model_name in ( '', {}):
        return False
    
    return ( model_name in self.DeviceConf and "TS0601_DP" in self.DeviceConf[model_name] )


def tuya_TS0121_registration(self, NwkId):
    self.log.logging("Tuya", "Debug", "tuya_TS0121_registration - Nwkid: %s" % NwkId)
    # (1) 3 x Write Attribute Cluster 0x0000 - Attribute 0xffde  - DT 0x20  - Value: 0x13
    EPout = "01"
    write_attribute(self, NwkId, ZIGATE_EP, EPout, "0000", "0000", "00", "ffde", "20", "13", ackIsDisabled=False)


def tuya_read_attribute(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data):
    if nwkid not in self.ListOfDevices:
        return
    transid = "%02x" % get_next_tuya_transactionId(self, nwkid)
    len_data = (len(data)) // 2
    payload = cluster_frame + sqn + cmd + "02" + transid + action + "00" + "%02x" % len_data + data

    raw_APS_request(
        self,
        nwkid,
        EPout,
        "ef00",
        "0104",
        payload,
        zigate_ep=ZIGATE_EP,
        ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
    )
    self.log.logging(["Tuya0601", "Tuya"], "Debug", "tuya_read_attribute - %s/%s cmd: %s payload: %s" % (nwkid, EPout, cmd, payload))


def tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data, action2=None, data2=None):
    self.log.logging(["Tuya0601", "Tuya"], "Debug", "tuya_cmd - %s/%s cmd: %s action: %s data: %s" % (nwkid, EPout, cmd, action, data))
    
    if nwkid not in self.ListOfDevices:
        return
    transid = "%02x" % get_next_tuya_transactionId(self, nwkid)
    len_data = (len(data)) // 2
    payload = cluster_frame + sqn + cmd + "00" + transid + action + "00" + "%02x" % len_data + data
    if action2 and data2:
        len_data2 = (len(data2)) // 2
        payload += action2 + "00" + "%02x" % len_data2 + data2
    raw_APS_request(
        self,
        nwkid,
        EPout,
        "ef00",
        "0104",
        payload,
        zigate_ep=ZIGATE_EP,
        ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
    )
    self.log.logging(["Tuya0601", "Tuya"], "Debug", "tuya_cmd - %s/%s cmd: %s payload: %s" % (nwkid, EPout, cmd, payload))


def store_tuya_attribute(self, NwkId, Attribute, Value):
    # Ensure "Tuya" key exists for the given NwkId and then store the attribute
    tuya_device_info = self.ListOfDevices.setdefault(NwkId, {}).setdefault("Tuya", {})
    tuya_device_info[Attribute] = Value


def get_tuya_attribute(self, NwkId, Attribute):
    return self.ListOfDevices.get(NwkId, {}).get("Tuya", {}).get(Attribute)


def get_next_tuya_transactionId(self, NwkId):
    tuya_info = self.ListOfDevices.setdefault(NwkId, {}).setdefault("Tuya", {})
    tuya_info["TuyaTransactionId"] = (tuya_info.get("TuyaTransactionId", 0x00) + 1) & 0xFF
    return tuya_info["TuyaTransactionId"]
