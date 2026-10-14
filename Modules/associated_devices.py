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
    Module: associated_devices.py

    Description: Which nodes an Associated Devices collection should ask, and
        how to read the answer.

        The associated device list is not a Mgmt_* table. It rides on the
        extended address response: NWK_addr_req / IEEE_addr_req with
        RequestType 0x01, answered with NumAssocDev, StartIndex and
        NWKAddrAssocDevList. It is the only Zigbee mechanism that reports a
        sleepy end device's parent without talking to the end device -- the
        parent answers for it -- which is what makes battery devices visible in
        a topology report.

        Kept free of any plugin dependency on purpose: the collector that uses
        it (Classes/AssociatedDevicesScan.py) reaches plugin.py and the
        transport, neither of which can be imported under the test harness, so
        the decisions worth testing live here instead.
"""

from collections.abc import Mapping

COORDINATOR_NWKID = "0000"

# What the plugin records for a node that is gone. Asking one costs a full
# per-node timeout budget and can never produce an answer.
DEPARTED_STATUSES = ("Leave", "Removed")

# Modules/tools_mac_capa.py::decodeMacCapa() spellings
FULL_FUNCTION_DEVICE = "Full-Function Device"
REDUCED_FUNCTION_DEVICE = "Reduced-Function Device"

# MAC capability bit 1, the one that says full-function
MAC_CAPA_DEVICE_TYPE = 0b00000010

# The extended address response, the only RequestType that carries the list
EXTENDED_REQUEST_TYPE = "01"


def node_can_have_children(nwkid, device):
    """Whether this node is worth asking for its associated devices.

    Only a coordinator or a router parents children, so only those are asked.
    An end device answers nothing, and on this scan a node that says nothing
    costs the whole per-node timeout budget.

    Note this is the *only* gate: unlike NetworkMap, which checked is_a_router()
    and then checked Capability again for the request type, there is one
    decision here and the request type never disagrees with it.

    `Capability` -- the MAC capability the device announced, decoded once at
    pairing -- comes first and is believed in both directions. It is the device's
    own word about itself, and it gets the lying models right with no model list:
    Livolo (0x80) and Aqara Opple (0x84) both decode to reduced-function, which
    is why NetworkMap.is_a_router() had to exclude TI0001/TS0011/TS0601 by name.

    LogicalType is deliberately *not* read first. ReArrangeMacCapaBasedOnModel()
    sets TI0001/TS06xx to Router while mainPoweredDevice() sets the same models
    to End Device, so whichever ran last wins and the field cannot be trusted on
    its own. It is only consulted when the device never announced a capability.
    """
    if nwkid == COORDINATOR_NWKID:
        # The coordinator record is built by initLODZigate() with no Capability
        # and no Status, and its children are the ones no router can report.
        return True

    if not isinstance(device, Mapping):
        return False

    if device.get("Status") != "inDB":
        # Not onboarded, or gone. DEPARTED_STATUSES is covered by this, and so
        # is a device still half way through pairing.
        return False

    capability = device.get("Capability")
    if isinstance(capability, (list, tuple)):
        if FULL_FUNCTION_DEVICE in capability:
            return True
        if REDUCED_FUNCTION_DEVICE in capability:
            return False

    return _router_without_announced_capability(device)


def _router_without_announced_capability(device):
    """Last resort, for a device the plugin has never heard announce itself."""
    if device.get("LogicalType") in ("Coordinator", "Router"):
        return True

    if device.get("DeviceType") == "FFD":
        return True

    return bool(_mac_capa_bits(device.get("MacCapa")) & MAC_CAPA_DEVICE_TYPE)


def _mac_capa_bits(mac_capa):
    """MacCapa as an int. It is stored as a hex string, and has been seen empty."""
    if isinstance(mac_capa, int):
        return mac_capa
    if not isinstance(mac_capa, str) or not mac_capa.strip():
        return 0
    try:
        return int(mac_capa, 16)
    except ValueError:
        return 0


def nodes_to_scan(list_of_devices):
    """Every node to ask, coordinator first.

    Coordinator first because it is the node most likely to parent the end
    devices nothing else reports, so it answers before any budget is spent.
    """
    candidates = [
        nwkid
        for nwkid in sorted(list_of_devices)
        if nwkid != COORDINATOR_NWKID and node_can_have_children(nwkid, list_of_devices.get(nwkid))
    ]
    if COORDINATOR_NWKID in list_of_devices:
        return [COORDINATOR_NWKID] + candidates
    return candidates


def is_last_page(num_assoc_devices, start_index, devices_in_page):
    """Whether the response just decoded completes the node's list.

    Paging is driven by the decoder, not by the collector: Decode8040() asks for
    the next page itself through Network_Address_response_request_next_index()
    when the list is short. So the collector must not treat the first response
    as the answer -- it has to wait for the page that closes the list, which is
    this condition.

    A node reporting more devices than it ever sends would page forever; `>=`
    rather than `==` stops on the first page that reaches the count.
    """
    if not isinstance(num_assoc_devices, int) or not isinstance(start_index, int):
        return True
    return start_index + devices_in_page >= num_assoc_devices


def split_device_list(device_list):
    """The NWKAddrAssocDevList payload as a list of 4-character NWK ids.

    The payload arrives as the concatenated hex the decoder built, already
    byte-swapped per entry. A trailing fragment shorter than one address is
    dropped rather than reported as a node.
    """
    if not isinstance(device_list, str):
        return []
    return [device_list[idx:idx + 4] for idx in range(0, len(device_list) - 3, 4)]


def notify_associated_devices_scan(self, nwkid, num_assoc_devices, start_index, device_list):
    """Hand one extended address response to the collector, if one is running.

    Called from the decoder, which answers both the TopologyV2 scan and the
    Associated Devices collection with the same response. The collector ignores
    a response for a node it did not ask, so the TopologyV2 path is unaffected
    whether or not a collection is in progress.
    """
    scan = getattr(self, "associated_devices_scan", None)
    if scan is None:
        return False
    return scan.response_received(nwkid, num_assoc_devices, start_index, device_list)
