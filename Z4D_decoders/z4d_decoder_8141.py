def Decode8141(self, Devices, MsgData, MsgLQI):
    MsgComplete = MsgData[:2]
    MsgAttType = MsgData[2:4]
    MsgAttID = MsgData[4:8]
    MsgAttFlag = MsgData[8:10]
    self.log.logging('Input', 'Log', 'Decode8141 - Attribute Discovery Extended Response - MsgComplete: %s AttType: %s Attribute: %s Flag: %s' % (MsgComplete, MsgAttType, MsgAttID, MsgAttFlag))
    if len(MsgData) > 10:
        MsgSrcAddr = MsgData[10:14]
        MsgSrcEp = MsgData[14:16]
        MsgClusterID = MsgData[16:20]
        self.log.logging('Input', 'Log', 'Decode8141 - Attribute Discovery Extended Response - %s/%s - Cluster: %s - Attribute: %s - Attribute Type: %s Flag: %s Complete: %s' % (MsgSrcAddr, MsgSrcEp, MsgClusterID, MsgAttID, MsgAttType, MsgAttFlag, MsgComplete), MsgSrcAddr)
        if MsgSrcAddr not in self.ListOfDevices:
            if not zigpy_plugin_sanity_check(self, MsgSrcAddr):
                handle_unknow_device(self, MsgSrcAddr)
            return
        if 'Attributes List' not in self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]['Attributes List Extended'] = {'Ep': {}}
        if 'Ep' not in self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']:
            self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']['Ep'] = {}
        if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']['Ep']:
            self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']['Ep'][MsgSrcEp] = {}
        if MsgClusterID not in self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']['Ep'][MsgSrcEp]:
            self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']['Ep'][MsgSrcEp][MsgClusterID] = {}
        if MsgAttID not in self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']['Ep'][MsgSrcEp][MsgClusterID]:
            self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']['Ep'][MsgSrcEp][MsgClusterID][MsgAttID] = {}
        self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']['Ep'][MsgSrcEp][MsgClusterID][MsgAttID]['Type'] = MsgAttType
        self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']['Ep'][MsgSrcEp][MsgClusterID][MsgAttID]['Read'] = int(MsgAttFlag, 16) & 1
        self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']['Ep'][MsgSrcEp][MsgClusterID][MsgAttID]['Write'] = (int(MsgAttFlag, 16) & 2) >> 1
        self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']['Ep'][MsgSrcEp][MsgClusterID][MsgAttID]['Reportable'] = (int(MsgAttFlag, 16) & 4) >> 2
        self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']['Ep'][MsgSrcEp][MsgClusterID][MsgAttID]['Scene'] = (int(MsgAttFlag, 16) & 8) >> 3
        self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']['Ep'][MsgSrcEp][MsgClusterID][MsgAttID]['Global'] = (int(MsgAttFlag, 16) & 16) >> 4