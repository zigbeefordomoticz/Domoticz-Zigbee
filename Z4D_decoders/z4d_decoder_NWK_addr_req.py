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

from Modules.sendZigateCommand import raw_APS_request


def Decode0040(self, Devices, MsgData, MsgLQI):
    """
    Decode a NWK address request (0040) and prepare a response.

    Args:
        Devices (dict): The list of devices.
        MsgData (str): The received message data.
        MsgLQI (str): The Link Quality Indicator for the message.

    This function processes a NWK address request message, prepares the appropriate
    response, and sends the response back.
    """
    # Log incoming message details
    self.log.logging('Input', 'Debug', 'Decode0040 - NWK_addr_req: %s' % MsgData)

    # Extract relevant fields from MsgData
    sqn = MsgData[:2]
    srcNwkId = MsgData[2:6]
    srcEp = MsgData[6:8]
    ieee = MsgData[8:24]
    reqType = MsgData[24:26]
    startIndex = MsgData[26:28]

    # Log the extracted fields
    self.log.logging('Input', 'Debug', f"      source req nwkid: {srcNwkId}")
    self.log.logging('Input', 'Debug', f"      request IEEE    : {ieee}")
    self.log.logging('Input', 'Debug', f"      request Type    : {reqType}")
    self.log.logging('Input', 'Debug', f"      request Idx     : {startIndex}")

    # Define the cluster ID for the request
    Cluster = '8000'

    # Prepare the payload based on the IEEE address
    if ieee == self.ControllerIEEE:
        controller_ieee = f'{int(self.ControllerIEEE, 16):016x}'
        controller_nwkid = f'{int(self.ControllerNWKID, 16):04x}'
        status = '00'
        payload = sqn + status + controller_ieee + controller_nwkid + '00'
    elif ieee in self.IEEE2NWK:
        device_ieee = f'{int(ieee, 16):016x}'
        device_nwkid = f'{int(self.IEEE2NWK[ieee], 16):04x}'
        status = '00'
        payload = sqn + status + device_ieee + device_nwkid + '00'
    else:
        status = '81'
        payload = sqn + status + ieee

    # Log the response payload
    self.log.logging('Input', 'Debug', f'Decode0040 - response payload: {payload}')

    # Send the response back using raw APS request
    raw_APS_request(self, srcNwkId, '00', Cluster, '0000', payload, zigpyzqn=sqn, zigate_ep='00')
