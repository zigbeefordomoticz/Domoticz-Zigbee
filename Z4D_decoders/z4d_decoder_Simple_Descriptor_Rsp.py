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


from Modules.pairingProcess import request_next_Ep
from Modules.tools import updLQI, updSQN, is_duplicate_sqn
from Modules.zigateConsts import ZCL_CLUSTERS_LIST
from Modules.zigbeeController import receiveZigateEpDescriptor


def Decode8043(self, Devices, MsgData, MsgLQI):
    """Decode and process a 0x8043 Simple Descriptor Response message."""

    # Extract initial fields
    MsgDataSQN, MsgDataStatus, MsgDataShAddr, MsgDataLength = extract_basic_fields(self, MsgData)

    self.log.logging([ "Pairing", "Input"], 'Debug', 'Decode8043 - Received SQN: %s Addr: %s Len: %s Status: %s Data: %s' %(
        MsgDataSQN, MsgDataShAddr, MsgDataLength, MsgDataStatus, MsgData))

    if is_duplicate_sqn(self, MsgDataShAddr, MsgDataSQN):
        self.log.logging([ "Pairing", "Input"], 'Debug', f'Decode8043 - Duplicate SQN: {MsgDataSQN} for device {MsgDataShAddr}')
        return

    # Update SQN
    updSQN(self, MsgDataShAddr, MsgDataSQN)

    if should_skip_message(self, MsgDataLength, MsgDataStatus):
        return

    if not is_valid_device(self, MsgDataShAddr):
        return

    device_status = self.ListOfDevices[MsgDataShAddr].get('Status')
    inDB_status = device_status == 'inDB'

    # Pairing of existing paired device
    already_paired = device_status in ( "erasePDM", "provREQ", "Leave", "inDB")

    self.log.logging([ "Pairing", "Input"], 'Debug', f'Decode8043 - Db Status: {device_status}, inDB_status: {inDB_status}, already_paired: {already_paired}')

    # Update LQI
    updLQI(self, MsgDataShAddr, MsgLQI)

    # Special case for Zigate
    if MsgDataShAddr == '0000':
        # This is a special case for Zigbee coordinator
        receiveZigateEpDescriptor(self, MsgData)
        return

    # Extract more fields
    MsgDataEp = MsgData[10:12]
    MsgDataProfile = MsgData[12:16]
    MsgDataDeviceId = MsgData[16:20]
    MsgDataBField = MsgData[20:22]
    MsgDataInClusterCount = MsgData[22:24]

    # Handle special DeviceID 0xE15E
    if handle_special_device(self, MsgDataShAddr, MsgDataEp, MsgDataProfile, MsgDataDeviceId):
        return

    # Update basic device info (ProfileID, DeviceID, Version)
    update_device_basic_info(self, MsgDataShAddr, MsgDataEp, MsgDataProfile, MsgDataDeviceId, MsgDataBField, inDB_status, MsgLQI)

    # Handle In Clusters
    idx = 24
    idx = handle_in_cluster(self, MsgDataShAddr, MsgDataEp, MsgDataInClusterCount, MsgData, idx, inDB_status)

    # Handle Out Clusters
    idx = handle_out_cluster(self, MsgDataShAddr, MsgDataEp, MsgData, idx, inDB_status)

    # Update Status and Heartbeat if pairing
    if request_next_Ep(self, MsgDataShAddr) and not already_paired:
        self.ListOfDevices[MsgDataShAddr]['Status'] = '8043'
        self.ListOfDevices[MsgDataShAddr]['Heartbeat'] = '0'

    self.log.logging('Pairing', 'Debug', 'Decode8043 - Processed %s, final result: %s' %(
        MsgDataShAddr, str(self.ListOfDevices[MsgDataShAddr])))


def extract_basic_fields(self, MsgData):
    """Extract basic fields from the 0x8043 message."""
    return MsgData[:2], MsgData[2:4], MsgData[4:8], MsgData[8:10]


def is_valid_device(self, MsgDataShAddr):
    """Check if the device address exists in the known devices list."""
    if MsgDataShAddr not in self.ListOfDevices:
        self.log.logging([ "Pairing", "Input"], 'Log', f'Decode8043 receives a message from a non existing device {MsgDataShAddr}')
        return False
    return True


def should_skip_message(self, MsgDataLength, MsgDataStatus):
    """Determine if the message should be skipped based on length and status."""
    return int(MsgDataLength, 16) == 0 or MsgDataStatus != '00'


def handle_special_device(self, MsgDataShAddr, MsgDataEp, MsgDataProfile, MsgDataDeviceId):
    """Handle special case for DeviceID 0xE15E (e.g., specific endpoint to skip)."""
    self.log.logging([ "Pairing", "Input"], 'Debug', f'Entering handle_special_device with args: MsgDataShAddr={MsgDataShAddr}, MsgDataEp={MsgDataEp}, MsgDataProfile={MsgDataProfile}, MsgDataDeviceId={MsgDataDeviceId}')

    if int(MsgDataProfile, 16) == 0xC05E and int(MsgDataDeviceId, 16) == 0xE15E:
        self.log.logging([ "Pairing", "Input"], 'Log', 'Decode8043 - Received ProfileID: %s, ZDeviceID: %s - skip' %(
            MsgDataProfile, MsgDataDeviceId))
        if MsgDataEp in self.ListOfDevices[MsgDataShAddr]['Ep']:
            del self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp]
        if 'NbEp' in self.ListOfDevices[MsgDataShAddr] and int(self.ListOfDevices[MsgDataShAddr]['NbEp']) > 1:
            self.ListOfDevices[MsgDataShAddr]['NbEp'] = int(self.ListOfDevices[MsgDataShAddr]['NbEp']) - 1
        return True
    return False


def update_device_basic_info(self, MsgDataShAddr, MsgDataEp, MsgDataProfile, MsgDataDeviceId, MsgDataBField, inDB_status, MsgLQI):
    """Update basic information about the device."""
    self.log.logging([ "Pairing", "Input"], 'Debug', f'Entering update_device_basic_info with args: MsgDataShAddr={MsgDataShAddr}, MsgDataEp={MsgDataEp}, MsgDataProfile={MsgDataProfile}, MsgDataDeviceId={MsgDataDeviceId}, MsgDataBField={MsgDataBField}, inDB_status={inDB_status}, MsgLQI={MsgLQI}')

    device = self.ListOfDevices.get(MsgDataShAddr)
    if device is None:
        # Handle the case where the device is not in ListOfDevices
        self.log.logging([ "Pairing", "Input"], 'Error', f'Device {MsgDataShAddr} not found in ListOfDevices.')
        return

    # Ensure 'Epv2' exists
    device.setdefault('Epv2', {})

    # Ensure MsgDataEp exists within 'Epv2'
    device['Epv2'].setdefault(MsgDataEp, {})

    device['Epv2'][MsgDataEp]['ProfileID'] = MsgDataProfile
    device['Epv2'][MsgDataEp]['ZDeviceID'] = MsgDataDeviceId

    # Global ProfileID
    current_profile = device.get('ProfileID')
    if current_profile != MsgDataProfile:
        device['ProfileID'] = MsgDataProfile
        if not inDB_status:
            self.log.logging("Pairing", "Status", f'[-] NEW OBJECT: {MsgDataShAddr} Ep: {MsgDataEp} ProfileID {MsgDataProfile}')

    # Global ZDeviceID
    current_device_id = device.get('ZDeviceID')
    if current_device_id != MsgDataDeviceId:
        device['ZDeviceID'] = MsgDataDeviceId
        if not inDB_status:
            self.log.logging("Pairing", "Status", f'[-] NEW OBJECT: {MsgDataShAddr} Ep: {MsgDataEp} ZDeviceID {MsgDataDeviceId}')

    # Application Version (ZDeviceVersion)
    DeviceVersion = int(MsgDataBField, 16) & 0x1111
    device['ZDeviceVersion'] = '%04x' % DeviceVersion
    if not inDB_status:
        self.log.logging([ "Pairing", "Input"], 'Status', f'[%s]    NEW OBJECT: %s Ep: {MsgDataEp} Application Version %s' % (
            '-', MsgDataShAddr, device['ZDeviceVersion']))


def handle_in_cluster(self, MsgDataShAddr, MsgDataEp, MsgDataInClusterCount, MsgData, idx, inDB_status):
    """Handle In Cluster list."""
    self.log.logging([ "Pairing", "Input"], 'Debug', f'Entering handle_in_cluster with args: MsgDataShAddr={MsgDataShAddr}, MsgDataEp={MsgDataEp}, MsgDataInClusterCount={MsgDataInClusterCount}, idx={idx}, inDB_status={inDB_status}')

    device = self.ListOfDevices[MsgDataShAddr]
    inClusterCount = int(MsgDataInClusterCount, 16)

    if not inDB_status:
        self.log.logging([ "Pairing", "Input"], 'Status', '[%s]    NEW OBJECT: %s Ep: %s Cluster IN Count: %s' %(
            '-', MsgDataShAddr, MsgDataEp, MsgDataInClusterCount))

    for i in range(inClusterCount):
        MsgDataCluster = MsgData[idx + i * 4: idx + (i + 1) * 4]
        if 'ConfigSource' not in device or device['ConfigSource'] != 'DeviceConf':
            device.setdefault('ConfigSource', '8043')
            device.setdefault('Ep', {}).setdefault(MsgDataEp, {})[MsgDataCluster] = {}

        device['Epv2'][MsgDataEp].setdefault('ClusterIn', {})[MsgDataCluster] = {}

        if inDB_status:
            continue

        # Log the cluster information
        cluster_name = ZCL_CLUSTERS_LIST.get(MsgDataCluster, '')
        if cluster_name:
            self.log.logging([ "Pairing", "Input"], 'Status', '[%s]       NEW OBJECT: %s Ep: %s Cluster In %d: %s (%s)' %(
                '-', MsgDataShAddr, MsgDataEp, i + 1, MsgDataCluster, cluster_name))
        else:
            self.log.logging([ "Pairing", "Input"], 'Status', '[%s]       NEW OBJECT: %s Ep: %s Cluster In %d: %s' %(
                '-', MsgDataShAddr, MsgDataEp, i + 1, MsgDataCluster))

    return idx + inClusterCount * 4


def handle_out_cluster(self, MsgDataShAddr, MsgDataEp, MsgData, idx, inDB_status):
    """Handle Out Cluster list."""
    self.log.logging([ "Pairing", "Input"], 'Debug', f'Entering handle_out_cluster with args: MsgDataShAddr={MsgDataShAddr}, MsgDataEp={MsgDataEp}, idx={idx}, inDB_status={inDB_status}')

    device = self.ListOfDevices[MsgDataShAddr]
    MsgDataOutClusterCount = MsgData[idx:idx + 2]
    outClusterCount = int(MsgDataOutClusterCount, 16)

    if not inDB_status:
        self.log.logging([ "Pairing", "Input"], 'Status', '[%s]    NEW OBJECT: %s  Ep: %s Cluster OUT Count: %s' %(
            '-', MsgDataShAddr, MsgDataEp, MsgDataOutClusterCount))

    idx += 2

    for i in range(outClusterCount):
        MsgDataCluster = MsgData[idx + i * 4: idx + (i + 1) * 4]
        if 'ConfigSource' not in device or device['ConfigSource'] != 'DeviceConf':
            device.setdefault('Ep', {}).setdefault(MsgDataEp, {})[MsgDataCluster] = {}

        device['Epv2'][MsgDataEp].setdefault('ClusterOut', {})[MsgDataCluster] = {}

        if inDB_status:
            continue

        # Log the cluster information
        cluster_name = ZCL_CLUSTERS_LIST.get(MsgDataCluster, '')
        if cluster_name:
            self.log.logging([ "Pairing", "Input"], 'Status', '[%s]       NEW OBJECT: %s  Ep: %s  Cluster Out %d: %s (%s)' %(
                '-', MsgDataShAddr, MsgDataEp, i + 1, MsgDataCluster, cluster_name))
        else:
            self.log.logging([ "Pairing", "Input"], 'Status', '[%s]       NEW OBJECT: %s  Ep: %s  Cluster Out %d: %s' %(
                '-', MsgDataShAddr, MsgDataEp, i + 1, MsgDataCluster))
    return idx + outClusterCount * 4
