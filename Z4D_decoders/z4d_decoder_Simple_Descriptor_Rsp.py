from Modules.pairingProcess import request_next_Ep
from Modules.tools import updLQI, updSQN
from Modules.zigateConsts import ZCL_CLUSTERS_LIST
from Modules.zigbeeController import receiveZigateEpDescriptor


def Decode8043(self, Devices, MsgData, MsgLQI):
    """Decode and process 0x8043 message."""
    MsgDataSQN = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    MsgDataShAddr = MsgData[4:8]
    MsgDataLenght = MsgData[8:10]
    self.log.logging('Input', 'Debug', 'Decode8043 - Received SQN: %s Addr: %s Len: %s Status: %s Data: %s' % (MsgDataSQN, MsgDataShAddr, MsgDataLenght, MsgDataStatus, MsgData))
    if MsgDataShAddr not in self.ListOfDevices:
        self.log.logging('Input', 'Log', 'Decode8043 receives a message from a non existing device %s' % MsgDataShAddr)
        return
    if 'SQN' in self.ListOfDevices[MsgDataShAddr] and MsgDataSQN == self.ListOfDevices[MsgDataShAddr]['SQN']:
        return
    inDB_status = self.ListOfDevices[MsgDataShAddr].get('Status', None) == 'inDB'
    if int(MsgDataLenght, 16) == 0:
        return
    if MsgDataStatus != '00':
        return
    MsgDataEp = MsgData[10:12]
    MsgDataProfile = MsgData[12:16]
    MsgDataEp = MsgData[10:12]
    MsgDataProfile = MsgData[12:16]
    MsgDataDeviceId = MsgData[16:20]
    MsgDataBField = MsgData[20:22]
    MsgDataInClusterCount = MsgData[22:24]
    updSQN(self, MsgDataShAddr, MsgDataSQN)
    updLQI(self, MsgDataShAddr, MsgLQI)
    if MsgDataShAddr == '0000':
        receiveZigateEpDescriptor(self, MsgData)
        return
    if MsgDataShAddr not in self.ListOfDevices:
        self.log.logging('Input', 'Error', 'Decode8043 - receive message for non existing device')
        return
    if int(MsgDataProfile, 16) == 49246 and int(MsgDataDeviceId, 16) == 57694:   # DeviceID: 0xE15E
        self.log.logging('Input', 'Log', 'Decode8043 - Received ProfileID: %s, ZDeviceID: %s - skip' % (MsgDataProfile, MsgDataDeviceId))
        if MsgDataEp in self.ListOfDevices[MsgDataShAddr]['Ep']:
            del self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp]
        if 'NbEp' in self.ListOfDevices[MsgDataShAddr] and int(self.ListOfDevices[MsgDataShAddr]['NbEp']) > 1:
            self.ListOfDevices[MsgDataShAddr]['NbEp'] = int(self.ListOfDevices[MsgDataShAddr]['NbEp']) - 1
        return
    if not inDB_status:
        self.log.logging('Input', 'Status', '[%s] NEW OBJECT: %s Simple Descriptor Response EP: 0x%s LQI: %s' % ('-', MsgDataShAddr, MsgDataEp, int(MsgLQI, 16)))
    if 'Epv2' not in self.ListOfDevices[MsgDataShAddr]:
        self.ListOfDevices[MsgDataShAddr]['Epv2'] = {}
    if MsgDataEp not in self.ListOfDevices[MsgDataShAddr]['Epv2']:
        self.ListOfDevices[MsgDataShAddr]['Epv2'][MsgDataEp] = {}
    self.ListOfDevices[MsgDataShAddr]['Epv2'][MsgDataEp]['ProfileID'] = MsgDataProfile
    self.ListOfDevices[MsgDataShAddr]['Epv2'][MsgDataEp]['ZDeviceID'] = MsgDataDeviceId
    if 'ProfileID' in self.ListOfDevices[MsgDataShAddr]:
        if self.ListOfDevices[MsgDataShAddr]['ProfileID'] != MsgDataProfile:
            pass
    self.ListOfDevices[MsgDataShAddr]['ProfileID'] = MsgDataProfile
    if not inDB_status:
        self.log.logging('Input', 'Status', '[%s]    NEW OBJECT: %s ProfileID %s' % ('-', MsgDataShAddr, MsgDataProfile))
    if 'ZDeviceID' in self.ListOfDevices[MsgDataShAddr]:
        if self.ListOfDevices[MsgDataShAddr]['ZDeviceID'] != MsgDataDeviceId:
            pass
    self.ListOfDevices[MsgDataShAddr]['ZDeviceID'] = MsgDataDeviceId
    if not inDB_status:
        self.log.logging('Input', 'Status', '[%s]    NEW OBJECT: %s ZDeviceID %s' % ('-', MsgDataShAddr, MsgDataDeviceId))
    DeviceVersion = int(MsgDataBField, 16) & 4369
    self.ListOfDevices[MsgDataShAddr]['ZDeviceVersion'] = '%04x' % DeviceVersion
    if not inDB_status:
        self.log.logging('Input', 'Status', '[%s]    NEW OBJECT: %s Application Version %s' % ('-', MsgDataShAddr, self.ListOfDevices[MsgDataShAddr]['ZDeviceVersion']))
    configSourceAvailable = False
    if 'ConfigSource' in self.ListOfDevices[MsgDataShAddr] and self.ListOfDevices[MsgDataShAddr]['ConfigSource'] == 'DeviceConf':
        configSourceAvailable = True
    if not inDB_status:
        self.log.logging('Input', 'Status', '[%s]    NEW OBJECT: %s Cluster IN Count: %s' % ('-', MsgDataShAddr, MsgDataInClusterCount))
    idx = 24
    i = 1
    if int(MsgDataInClusterCount, 16) > 0:
        while i <= int(MsgDataInClusterCount, 16):
            MsgDataCluster = MsgData[idx + (i - 1) * 4:idx + i * 4]
            self.log.logging('Input', 'Debug', '[%s]    NEW OBJECT: %s Extracted cluster: %s' % ('-', MsgDataShAddr, MsgDataCluster))
            if not configSourceAvailable:
                self.ListOfDevices[MsgDataShAddr]['ConfigSource'] = '8043'
                if MsgDataEp not in self.ListOfDevices[MsgDataShAddr]['Ep']:
                    self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] = {}
                if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp]:
                    self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster] = {}
            else:
                self.log.logging('Pairing', 'Debug', '[%s]    NEW OBJECT: %s we keep DeviceConf info' % ('-', MsgDataShAddr))
            if MsgDataEp not in self.ListOfDevices[MsgDataShAddr]['Epv2']:
                self.ListOfDevices[MsgDataShAddr]['Epv2'][MsgDataEp] = {}
            if 'ClusterIn' not in self.ListOfDevices[MsgDataShAddr]['Epv2'][MsgDataEp]:
                self.ListOfDevices[MsgDataShAddr]['Epv2'][MsgDataEp]['ClusterIn'] = {}
            if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Epv2'][MsgDataEp]['ClusterIn']:
                self.ListOfDevices[MsgDataShAddr]['Epv2'][MsgDataEp]['ClusterIn'][MsgDataCluster] = {}
            if not inDB_status:
                if MsgDataCluster in ZCL_CLUSTERS_LIST:
                    self.log.logging('Input', 'Status', '[%s]       NEW OBJECT: %s Cluster In %s: %s (%s)' % ('-', MsgDataShAddr, i, MsgDataCluster, ZCL_CLUSTERS_LIST[MsgDataCluster]))
                else:
                    self.log.logging('Input', 'Status', '[%s]       NEW OBJECT: %s Cluster In %s: %s' % ('-', MsgDataShAddr, i, MsgDataCluster))
            i += 1
    idx = 24 + int(MsgDataInClusterCount, 16) * 4
    MsgDataOutClusterCount = MsgData[idx:idx + 2]
    if not inDB_status:
        self.log.logging('Input', 'Status', '[%s]    NEW OBJECT: %s Cluster OUT Count: %s' % ('-', MsgDataShAddr, MsgDataOutClusterCount))
    idx += 2
    i = 1
    if int(MsgDataOutClusterCount, 16) > 0:
        while i <= int(MsgDataOutClusterCount, 16):
            MsgDataCluster = MsgData[idx + (i - 1) * 4:idx + i * 4]
            if not configSourceAvailable:
                if MsgDataEp not in self.ListOfDevices[MsgDataShAddr]['Ep']:
                    self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp] = {}
                if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp]:
                    self.ListOfDevices[MsgDataShAddr]['Ep'][MsgDataEp][MsgDataCluster] = {}
            else:
                self.log.logging('Input', 'Debug', '[%s]    NEW OBJECT: %s we keep DeviceConf info' % ('-', MsgDataShAddr), MsgDataShAddr)
            if MsgDataEp not in self.ListOfDevices[MsgDataShAddr]['Epv2']:
                self.ListOfDevices[MsgDataShAddr]['Epv2'][MsgDataEp] = {}
            if 'ClusterOut' not in self.ListOfDevices[MsgDataShAddr]['Epv2'][MsgDataEp]:
                self.ListOfDevices[MsgDataShAddr]['Epv2'][MsgDataEp]['ClusterOut'] = {}
            if MsgDataCluster not in self.ListOfDevices[MsgDataShAddr]['Epv2'][MsgDataEp]['ClusterOut']:
                self.ListOfDevices[MsgDataShAddr]['Epv2'][MsgDataEp]['ClusterOut'][MsgDataCluster] = {}
            if not inDB_status:
                if MsgDataCluster in ZCL_CLUSTERS_LIST:
                    self.log.logging('Input', 'Status', '[%s]       NEW OBJECT: %s Cluster Out %s: %s (%s)' % ('-', MsgDataShAddr, i, MsgDataCluster, ZCL_CLUSTERS_LIST[MsgDataCluster]))
                else:
                    self.log.logging('Input', 'Status', '[%s]       NEW OBJECT: %s Cluster Out %s: %s' % ('-', MsgDataShAddr, i, MsgDataCluster))
            MsgDataCluster = ''
            i += 1
    if request_next_Ep(self, MsgDataShAddr) and (not inDB_status):
        self.ListOfDevices[MsgDataShAddr]['Status'] = '8043'
        self.ListOfDevices[MsgDataShAddr]['Heartbeat'] = '0'
    self.log.logging('Pairing', 'Debug', 'Decode8043 - Processed ' + MsgDataShAddr + ' end results is: ' + str(self.ListOfDevices[MsgDataShAddr]))
