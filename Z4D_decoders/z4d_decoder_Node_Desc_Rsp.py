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

from Modules.tools import ReArrangeMacCapaBasedOnModel, decodeMacCapa, updLQI


def Decode8042(self, Devices, MsgData, MsgLQI):
    """
    Decode an 8042 Node Descriptor response and update device information.

    Args:
        Devices (dict): Dictionary of devices managed by the system.
        MsgData (str): The raw message data received from the network.
        MsgLQI (str): Link Quality Indicator (LQI) of the received message.

    This method parses the node descriptor data and updates the device records with 
    relevant information such as manufacturer, capabilities, and logical type.
    """
    sequence = MsgData[:2]
    status = MsgData[2:4]
    addr = MsgData[4:8]

    # Handle invalid status codes
    if status != '00':
        self.log.logging(
            'Input', 'Debug',
            f"Decode8042 - Reception of Node Descriptor for {addr} with status {status}"
        )
        return

    # Extract descriptor details
    manufacturer = MsgData[8:12]
    max_rx = MsgData[12:16]
    max_tx = MsgData[16:20]
    server_mask = MsgData[20:24]
    descriptor_capability = MsgData[24:26]
    mac_capability = MsgData[26:28]
    max_buffer = MsgData[28:30]
    bit_field = MsgData[30:34]

    self.log.logging(
        'Input', 'Debug',
        f"Decode8042 - Reception Node Descriptor for: {addr}, SEQ: {sequence}, "
        f"Status: {status}, Manufacturer: {manufacturer}, MAC Capability: {mac_capability}, Bit Field: {bit_field}",
        addr
    )

    # Initialize device record if not present
    if addr == '0000' and addr not in self.ListOfDevices:
        self.ListOfDevices[addr] = {'Ep': {}}
    if addr not in self.ListOfDevices:
        self.log.logging(
            'Input', 'Log',
            f"Decode8042 received a message from a non-existing device {addr}"
        )
        return

    # Update device details
    updLQI(self, addr, MsgLQI)
    self.ListOfDevices[addr].update({
        '_rawNodeDescriptor': MsgData[8:],
        'Max Buffer Size': max_buffer,
        'Max Rx': max_rx,
        'Max Tx': max_tx,
        'macapa': mac_capability,
        'bitfield': bit_field,
        'server_mask': server_mask,
        'descriptor_capability': descriptor_capability,
    })

    # Rearrange MAC capability and decode capabilities
    mac_capability = ReArrangeMacCapaBasedOnModel(self, addr, mac_capability)
    capabilities = decodeMacCapa(mac_capability)

    # Determine device properties
    AltPAN = 'Able to act Coordinator' in capabilities
    PowerSource = 'Main' if 'Main Powered' in capabilities else 'Battery'
    DeviceType = 'FFD' if 'Full-Function Device' in capabilities else 'RFD'
    ReceiveOnIdle = 'On' if 'Receiver during Idle' in capabilities else 'Off'

    # Log device properties
    self.log.logging('Input', 'Debug', f"Decode8042 - Alternate PAN Coordinator = {AltPAN}", addr)
    self.log.logging('Input', 'Debug', f"Decode8042 - Receiver on Idle = {ReceiveOnIdle}", addr)
    self.log.logging('Input', 'Debug', f"Decode8042 - Power Source = {PowerSource}", addr)
    self.log.logging('Input', 'Debug', f"Decode8042 - Device Type = {DeviceType}", addr)

    # Parse bit fields to determine logical type
    bit_fieldL = int(bit_field[2:4], 16)
    bit_fieldH = int(bit_field[:2], 16)
    LogicalType = ['Coordinator', 'Router', 'End Device'][bit_fieldL & 15] if (bit_fieldL & 15) < 3 else 'Unknown'

    self.log.logging('Input', 'Debug', f"Decode8042 - bit_field = {bit_fieldL}:{bit_fieldH}", addr)
    self.log.logging('Input', 'Debug', f"Decode8042 - Logical Type = {LogicalType}", addr)

    # Update or initialize device attributes
    device_record = self.ListOfDevices[addr]
    device_record.setdefault('Manufacturer', manufacturer)
    if device_record.get('Status') != 'inDB':
        device_record.update(
            {
                'Manufacturer': manufacturer,
                'DeviceType': DeviceType,
                'LogicalType': str(LogicalType),
                'PowerSource': PowerSource,
                'ReceiveOnIdle': ReceiveOnIdle,
            }
        )
