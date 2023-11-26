def Decode8139(self, Devices, MsgData, MsgLQI):
    bDiscoveryComplete = MsgData[:2]
    eAttributeDataType = MsgData[2:4]
    u16AttributeEnum = MsgData[4:8]
    uSrcAddress = MsgData[8:12]
    u8SrcEndpoint = MsgData[12:14]
    u16ClusterEnum = MsgData[14:18]
    self.log.logging('Input', 'Log', 'Decode8139 - %s/%s Complete: %s Cluster: %s Attribute Type: %s Attribute: %s' % (uSrcAddress, u8SrcEndpoint, bDiscoveryComplete, u16ClusterEnum, eAttributeDataType, u16AttributeEnum))