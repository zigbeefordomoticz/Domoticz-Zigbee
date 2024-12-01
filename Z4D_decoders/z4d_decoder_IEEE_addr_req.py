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

import struct

from Modules.sendZigateCommand import raw_APS_request


def Decode0041(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', f"Decode0041 - IEEE_addr_req: {MsgData} {self.ControllerNWKID} {self.ControllerIEEE}")
    
    if not self.ControllerIEEE or self.ControllerNWKID in (None, "ffff"):
        return

    # Parse message data
    sqn, srcNwkId, srcEp, nwkid, reqType, startIndex = ( MsgData[:2], MsgData[2:6], MsgData[6:8], MsgData[8:12], MsgData[12:14], MsgData[14:16] )

    # Log parsed details
    self.log.logging('Input', 'Debug', f"      source req SrcNwkId: {srcNwkId} NwkId: {nwkid} Type: {reqType} Idx: {startIndex}")
    
    Cluster = '8001'
    status, payload = _generate_response_payload(self, nwkid, sqn)
    
    self.log.logging('Input', 'Debug', f"Decode0041 - response payload: {payload}")
    raw_APS_request(self, srcNwkId, '00', Cluster, '0000', payload, zigpyzqn=sqn, zigate_ep='00')


def _generate_response_payload(self, nwkid, sqn):
    """Generate the response payload based on the requested nwkid."""
    if nwkid == self.ControllerNWKID:
        status = '00'
        ieee = _format_ieee(self, self.ControllerIEEE)
        nwk_id = _format_nwkid(self, self.ControllerNWKID)
        payload = sqn + status + ieee + nwk_id + '00'
    elif nwkid in self.ListOfDevices:
        status = '00'
        ieee = _format_ieee(self, self.ListOfDevices[nwkid]['IEEE'])
        nwk_id = _format_nwkid(self, self.ControllerNWKID)
        payload = sqn + status + ieee + nwk_id + '00'
    else:
        status = '81'
        payload = sqn + status + nwkid
    return status, payload


def _format_ieee(self, ieee):
    """Format the IEEE address to 16-character hex string."""
    return f"{int(ieee, 16):016x}"


def _format_nwkid(self, nwkid):
    """Format the NWK ID to 4-character hex string."""
    return f"{int(nwkid, 16):04x}"
