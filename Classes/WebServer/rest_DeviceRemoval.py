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
DELETE /zdevice-name/<nwkid or ieee>: "Remove device" of the WebUI.

The device is asked to leave the network, then the plugin forgets it. Only for
a device without widgets: one with widgets is removed by deleting its last
widget in Domoticz (plugin.onDeviceRemoved), as for a Green Power device
(rest_GreenPower.rest_zgp_device).
"""

import json

from Modules.domoticzAbstractLayer import domo_units, domoticz_error_api
from Modules.sendZigateCommand import sendZigateCmd
from Modules.zigateCommands import zigate_remove_device


def remove_device(self, device_id, response):
    nwkid, ieee = _find_device(self, device_id)
    if nwkid is None and ieee is None:
        domoticz_error_api("rest_zDevice - Device: %s to be DELETED unknown" % device_id)
        domoticz_error_api("Device %s to be removed unknown" % device_id)
        response["Data"] = json.dumps([], sort_keys=True)
        return response

    if nwkid == "0000" or (ieee and ieee == self.ControllerIEEE):
        return _refused(response, "the coordinator cannot be removed")

    # A stale record whose IEEE now belongs to another NwkId: that device is
    # alive, it keeps its IEEE entry and its widgets, and must not leave.
    stale = bool(ieee) and self.IEEE2NWK.get(ieee, nwkid) != nwkid

    if ieee and not stale:
        widgets = domo_units(self, self.Devices, ieee)
        if widgets:
            return _refused(response, "device %s/%s has %s widget(s): delete its last widget in Domoticz to remove it" % (nwkid, ieee, len(widgets)))
        _request_to_leave(self, nwkid, ieee)
        self.IEEE2NWK.pop(ieee, None)

    if nwkid:
        self.ListOfDevices.pop(nwkid, None)

    response["Data"] = json.dumps({"Name": "Device %s/%s removed" % (nwkid, ieee)}, sort_keys=True)
    return response


def _find_device(self, device_id):
    """(nwkid, ieee) of a short address or an IEEE, (None, None) when unknown."""
    if len(device_id) == 4:
        if device_id not in self.ListOfDevices:
            return None, None
        return device_id, self.ListOfDevices[device_id].get("IEEE")

    if device_id not in self.IEEE2NWK:
        return None, None
    return self.IEEE2NWK[device_id], device_id


def _request_to_leave(self, nwkid, ieee):
    """
    Best effort: the device is often out of reach, and a sleeping one can miss
    the request. zigpy waits for the answer in its own task, and drops the
    device from its table whatever the outcome.
    """
    if self.zigbee_communication == "native":
        if "IEEE" in self.ControllerData:
            # uParrentAddress + uChildAddress (uint64)
            sendZigateCmd(self, "0026", self.ControllerData["IEEE"] + ieee)
        return

    if self.ControllerLink is None:
        return
    self.log.logging("WebServer", "Status", "Device %s/%s removed from the WebUI, asking it to leave the network" % (nwkid, ieee), nwkid)
    zigate_remove_device(self, self.ControllerIEEE, ieee)


def _refused(response, message):
    response["Status"] = "400 BAD REQUEST"
    response["Data"] = json.dumps({"BE_Error": message})
    return response
