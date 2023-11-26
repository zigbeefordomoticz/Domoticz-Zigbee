def Decode8102(self, Devices, MsgData, MsgLQI):
    MsgSQN = MsgData[:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSrcEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]
    MsgAttrID = MsgData[12:16]
    MsgAttStatus = MsgData[16:18]
    MsgAttType = MsgData[18:20]
    MsgAttSize = MsgData[20:24]
    MsgClusterData = MsgData[24:]
    self.log.logging('Input', 'Debug', 'Decode8102 - Attribute Reports: [%s:%s] MsgSQN: %s ClusterID: %s AttributeID: %s Status: %s Type: %s Size: %s ClusterData: >%s<' % (MsgSrcAddr, MsgSrcEp, MsgSQN, MsgClusterId, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr)
    if self.PluzzyFirmware:
        self.log.logging('Input', 'Log', 'Patching payload:', MsgSrcAddr)
        _type = MsgAttStatus
        _status = MsgAttType
        _size = MsgAttSize
        _newsize = '00' + _size[:2]
        _newdata = MsgAttSize[2:4] + MsgClusterData
        self.log.logging('Input', 'Log', ' MsgAttStatus: %s -> %s' % (MsgAttStatus, _status), MsgSrcAddr)
        self.log.logging('Input', 'Log', ' MsgAttType: %s -> %s' % (MsgAttType, _type), MsgSrcAddr)
        self.log.logging('Input', 'Log', ' MsgAttSize: %s -> %s' % (MsgAttSize, _newsize), MsgSrcAddr)
        self.log.logging('Input', 'Log', ' MsgClusterData: %s -> %s' % (MsgClusterData, _newdata), MsgSrcAddr)
        MsgAttStatus = _status
        MsgAttType = _type
        MsgAttSize = _newsize
        MsgClusterData = _newdata
        MsgData = MsgSQN + MsgSrcAddr + MsgSrcEp + MsgClusterId + MsgAttrID + MsgAttStatus + MsgAttType + MsgAttSize + MsgClusterData
        pluzzyDecode8102(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData, MsgLQI)
    timeStamped(self, MsgSrcAddr, 33026)
    loggingMessages(self, '8102', MsgSrcAddr, None, MsgLQI, MsgSQN)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    updLQI(self, MsgSrcAddr, MsgLQI)
    i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSQN, TYPE_APP_ZCL)
    self.statistics._clusterOK += 1
    scan_attribute_reponse(self, Devices, MsgSQN, i_sqn, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgData, '8102')
    callbackDeviceAwake(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId)