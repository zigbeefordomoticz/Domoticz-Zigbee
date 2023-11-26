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
    
    
def scan_attribute_reponse(self, Devices, MsgSQN, i_sqn, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgData, msgtype):

    self.log.logging(
        "Input",
        "Debug",
        "scan_attribute_reponse - Sqn: %s i_sqn: %s Nwkid: %s Ep: %s Cluster: %s MsgData: %s Type: %s"
        % (
            MsgSQN, i_sqn, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgData, msgtype
        ),
        MsgSrcAddr,
    )

    idx = 12
    while idx < len(MsgData):
        MsgAttrID = MsgAttStatus = MsgAttType = MsgAttSize = MsgClusterData = ""
        MsgAttrID = MsgData[idx : idx + 4]
        idx += 4
        MsgAttStatus = MsgData[idx : idx + 2]
        idx += 2
        if MsgAttStatus == "00":
            MsgAttType = MsgData[idx : idx + 2]
            idx += 2
            MsgAttSize = MsgData[idx : idx + 4]
            idx += 4
            size = int(MsgAttSize, 16) * 2
            if size > 0:
                MsgClusterData = MsgData[idx : idx + size]
                idx += size
        else:
            self.log.logging(
                "Input",
                "Debug",
                "scan_attribute_reponse - %s idx: %s Read Attribute Response: [%s:%s] status: %s -> %s"
                % (msgtype, idx, MsgSrcAddr, MsgSrcEp, MsgAttStatus, MsgData[idx:]),
            )

            # If the frame is coming from firmware we get only one attribute at a time, with some dumy datas
            if len(MsgData[idx:]) == 6:
                # crap, lets finish it
                # Domoticz.Log("Crap Data: %s len: %s" %(MsgData[idx:], len(MsgData[idx:])))
                idx += 6
        self.log.logging( "Input", "Debug", "scan_attribute_reponse - %s idx: %s Read Attribute Response: [%s:%s] ClusterID: %s MsgSQN: %s, i_sqn: %s, AttributeID: %s Status: %s Type: %s Size: %s ClusterData: >%s<" % (
            msgtype, idx, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgSQN, i_sqn, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData, ), MsgSrcAddr, )
        read_report_attributes( self, Devices, msgtype, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData, )

def read_report_attributes( self, Devices, MsgType, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData, ):

    if DeviceExist(self, Devices, MsgSrcAddr):
        debug_LQI(self, MsgSrcAddr, MsgClusterId, MsgAttrID, MsgClusterData, MsgSrcEp)

        self.log.logging(
            "Input",
            "Debug2",
            "Decode8102: Attribute Report from "
            + str(MsgSrcAddr)
            + " SQN = "
            + str(MsgSQN)
            + " ClusterID = "
            + str(MsgClusterId)
            + " AttrID = "
            + str(MsgAttrID)
            + " Attribute Data = "
            + str(MsgClusterData),
            MsgSrcAddr,
        )

        if "Health" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Health"] not in ( "Disabled",):
            self.ListOfDevices[MsgSrcAddr]["Health"] = "Live"

        updSQN(self, MsgSrcAddr, str(MsgSQN))
        lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)

        ReadCluster(
            self,
            Devices,
            MsgType,
            MsgSQN,
            MsgSrcAddr,
            MsgSrcEp,
            MsgClusterId,
            MsgAttrID,
            MsgAttStatus,
            MsgAttType,
            MsgAttSize,
            MsgClusterData,
            Source=MsgType,
        )
        return
    # Device not found, let's try to find it, or trigger a scan
    handle_unknow_device( self, MsgSrcAddr)
