#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: tuya.py

    Description: Tuya specific

"""

from Modules.basicOutputs import raw_APS_request, write_attribute
from Modules.tools import is_ack_tobe_disabled
from Modules.zigateConsts import ZIGATE_EP


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
    self.log.logging("Tuya", "Debug", "tuya_read_attribute - %s/%s cmd: %s payload: %s" % (nwkid, EPout, cmd, payload))


def tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data, action2=None, data2=None):
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
    self.log.logging("Tuya", "Debug", "tuya_cmd - %s/%s cmd: %s payload: %s" % (nwkid, EPout, cmd, payload))


def store_tuya_attribute(self, NwkId, Attribute, Value):
    if "Tuya" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Tuya"] = {}
    self.ListOfDevices[NwkId]["Tuya"][Attribute] = Value


def get_tuya_attribute(self, Nwkid, Attribute):
    if "Tuya" not in self.ListOfDevices[Nwkid]:
        return None
    if Attribute not in self.ListOfDevices[Nwkid]["Tuya"]:
        return None
    return self.ListOfDevices[Nwkid]["Tuya"][Attribute]


def get_next_tuya_transactionId(self, NwkId):
    if "Tuya" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Tuya"] = {}

    if "TuyaTransactionId" not in self.ListOfDevices[NwkId]["Tuya"]:
        self.ListOfDevices[NwkId]["Tuya"]["TuyaTransactionId"] = 0x00

    self.ListOfDevices[NwkId]["Tuya"]["TuyaTransactionId"] += 1
    if self.ListOfDevices[NwkId]["Tuya"]["TuyaTransactionId"] > 0xFF:
        self.ListOfDevices[NwkId]["Tuya"]["TuyaTransactionId"] = 0x00
    return self.ListOfDevices[NwkId]["Tuya"]["TuyaTransactionId"]
