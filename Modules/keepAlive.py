#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2026
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Keep-Alive cluster (0x0025) server, as specified in ZCL revision 8, section 3.18.

zigpy advertises this cluster on the coordinator's endpoint 1. A device that supports it
reads both attributes regularly to check that the Trust Center is there, and rejoins the
network when the reads stay without answer.

The Read Attributes Response must be APS encrypted (section 3.18.4): zigpySend does it for
this cluster, see APS_ENCRYPTED_CLUSTERS.

Debug flag "KeepAlive": the read received (Decode0100), the answer (here), the result of the
send (zigpySend), and the values a device reports on this cluster (Conf/ZclDefinitions/0025.json).
"""

from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import is_ack_tobe_disabled
from Modules.zigateConsts import ZIGATE_EP

STATUS_SUCCESS = "00"
STATUS_UNSUPPORTED_ATTRIBUTE = "86"

DATA_TYPE_UINT8 = "20"
DATA_TYPE_UINT16 = "21"

# Attribute -> (data type, size in bytes, value). The values are the ZCL defaults, also answered by zigpy.
KEEP_ALIVE_ATTRIBUTES = {
    "0000": (DATA_TYPE_UINT8, 1, 10),     # TCKeepAliveBase, minutes
    "0001": (DATA_TYPE_UINT16, 2, 300),   # TCKeepAliveJitter, seconds
}


def encode_keep_alive_record(attribute):
    """One Read Attributes Response record: attribute id (LE), status, then type and value (LE) on success."""
    attribute_le = attribute[2:4] + attribute[:2]
    if attribute not in KEEP_ALIVE_ATTRIBUTES:
        return attribute_le + STATUS_UNSUPPORTED_ATTRIBUTE
    data_type, size, value = KEEP_ALIVE_ATTRIBUTES[attribute]
    return attribute_le + STATUS_SUCCESS + data_type + value.to_bytes(size, "little").hex()


def keep_alive_read_attribute_request(self, nwkid, src_ep, sqn, cluster_id, attributes):
    """
    Answer a Read Attributes request on cluster 0x0025, all attributes in one response.

    attributes is the concatenation of the requested attribute ids (big-endian hex). Every
    request is answered, even with a sequence number already seen: the values never change,
    and a device that repeats a read is one that did not get the answer.
    """
    payload = "18" + sqn + "01"  # Profile-wide, Server to Client, Disable Default Response / Read Attributes Response
    for idx in range(0, len(attributes), 4):
        payload += encode_keep_alive_record(attributes[idx:idx + 4])

    ack_is_disabled = is_ack_tobe_disabled(self, nwkid)
    self.log.logging(
        ["Input", "KeepAlive"], "Debug",
        f"keep_alive_read_attribute_request - {nwkid}/{src_ep} sqn: {sqn} attributes: {attributes} response: {payload} ackIsDisabled: {ack_is_disabled}",
        nwkid,
    )

    raw_APS_request(self, nwkid, src_ep, cluster_id, "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=ack_is_disabled)
