from Modules.basicOutputs import getListofAttribute, handle_unknow_device
from Modules.tools import zigpy_plugin_sanity_check


def Decode8140(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode8140 - Attribute Discovery Response - Data: %s LQI: %s' % (MsgData, MsgLQI))
    if MsgData[:2] == 'f7':
        return zigpy_Decode8140(self, Devices, MsgData[2:], MsgLQI)

    MsgComplete = MsgData[:2]
    MsgAttType = MsgData[2:4]
    MsgAttID = MsgData[4:8]

    if MsgComplete == '01' and MsgAttType == '00' and (MsgAttID == '0000'):
        return

    if len(MsgData) <= 8:
        return
    
    MsgSrcAddr = MsgData[8:12]
    MsgSrcEp = MsgData[12:14]
    MsgClusterID = MsgData[14:18]
    self.log.logging('Input', 'Debug', 'Decode8140 - Attribute Discovery Response - %s/%s - Cluster: %s - Attribute: %s - Attribute Type: %s Complete: %s' % (MsgSrcAddr, MsgSrcEp, MsgClusterID, MsgAttID, MsgAttType, MsgComplete), MsgSrcAddr)
    if MsgSrcAddr not in self.ListOfDevices:
        if not zigpy_plugin_sanity_check(self, MsgSrcAddr):
            handle_unknow_device(self, MsgSrcAddr)
        return

    if 'Attributes List' not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]['Attributes List'] = {'Ep': {}}
    if 'Ep' not in self.ListOfDevices[MsgSrcAddr]['Attributes List']:
        self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep'] = {}
    if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep']:
        self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep'][MsgSrcEp] = {}
    if MsgClusterID not in self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep'][MsgSrcEp]:
        self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep'][MsgSrcEp][MsgClusterID] = {}
    if MsgAttID in self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep'][MsgSrcEp][MsgClusterID] and self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep'][MsgSrcEp][MsgClusterID][MsgAttID] == MsgAttType:
        return

    self.ListOfDevices[MsgSrcAddr]['Attributes List']['Ep'][MsgSrcEp][MsgClusterID][MsgAttID] = MsgAttType
    
    if MsgComplete != '01':
        next_start = '%04x' % (int(MsgAttID, 16) + 1)
        getListofAttribute(self, MsgSrcAddr, MsgSrcEp, MsgClusterID, start_attribute=next_start)
            
            
def zigpy_Decode8140(self, Devices, MsgData, MsgLQI):
    
    MsgComplete = MsgData[:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSrcEp = MsgData[6:8]
    MsgClusterID = MsgData[8:12]
    
    if "Attributes List" not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]["Attributes List"] = {"Ep": {}}
        
    if "Ep" not in self.ListOfDevices[MsgSrcAddr]["Attributes List"]:
        self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"] = {}
        
    if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"]:
        self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"][MsgSrcEp] = {}
        
    if MsgClusterID not in self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"][MsgSrcEp]:
        self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"][MsgSrcEp][MsgClusterID] = {}

    idx = 12
    while idx < len( MsgData ):
        Attribute = MsgData[idx : idx + 4]
        idx += 4
        Attribute_type = MsgData[idx : idx + 2]
        idx += 2
        self.ListOfDevices[MsgSrcAddr]["Attributes List"]["Ep"][MsgSrcEp][MsgClusterID][Attribute] = Attribute_type

    if MsgComplete != "01":
        next_start = "%04x" % (int(Attribute, 16) + 1)
        getListofAttribute( self, MsgSrcAddr, MsgSrcEp, MsgClusterID, start_attribute=next_start, )
