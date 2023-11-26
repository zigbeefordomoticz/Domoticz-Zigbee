
from Modules.basicOutputs import handle_unknow_device
from Modules.tools import zigpy_plugin_sanity_check


        
def Decode8141(self, Devices, MsgData, MsgLQI):
    MsgComplete = MsgData[:2]
    MsgAttType = MsgData[2:4]
    MsgAttID = MsgData[4:8]
    MsgAttFlag = MsgData[8:10]

    self.log.logging('Input', 'Log', f'Decode8141 - Attribute Discovery Extended Response - MsgComplete: {MsgComplete} AttType: {MsgAttType} Attribute: {MsgAttID} Flag: {MsgAttFlag}')

    if len(MsgData) > 10:
        MsgSrcAddr = MsgData[10:14]
        MsgSrcEp = MsgData[14:16]
        MsgClusterID = MsgData[16:20]

        self.log.logging('Input', 'Log', f'Decode8141 - Attribute Discovery Extended Response - MsgComplete: {MsgComplete} AttType: {MsgAttType} Attribute: {MsgAttID} Flag: {MsgAttFlag}')

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

        att_info = self.ListOfDevices[MsgSrcAddr]['Attributes List Extended']['Ep'][MsgSrcEp][MsgClusterID][MsgAttID]
        att_info['Type'] = MsgAttType
        att_info['Read'] = int(MsgAttFlag, 16) & 1
        att_info['Write'] = (int(MsgAttFlag, 16) & 2) >> 1
        att_info['Reportable'] = (int(MsgAttFlag, 16) & 4) >> 2
        att_info['Scene'] = (int(MsgAttFlag, 16) & 8) >> 3
        att_info['Global'] = (int(MsgAttFlag, 16) & 16) >> 4
