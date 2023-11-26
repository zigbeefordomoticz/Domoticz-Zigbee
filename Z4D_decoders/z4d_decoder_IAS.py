def Decode0400(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode0400 - message: %s' % MsgData)
    if len(MsgData) != 14:
        return
    sqn = MsgData[:2]
    SrcAddress = MsgData[2:6]
    SrcEndPoint = MsgData[6:8]
    EnrollResponseCode = MsgData[10:12]
    ZoneId = MsgData[12:14]
    self.log.logging('Input', 'Log', 'Decode0400 - Source Address: %s Source Ep: %s EnrollmentResponseCode: %s ZoneId: %s' % (SrcAddress, SrcEndPoint, EnrollResponseCode, ZoneId))
    if self.iaszonemgt:
        self.iaszonemgt.IAS_zone_enroll_request_response(SrcAddress, SrcEndPoint, EnrollResponseCode, ZoneId)def Decode8046(self, Devices, MsgData, MsgLQI):
    MsgDataSQN = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    MsgDataShAddr = MsgData[4:8]
    MsgDataLenList = MsgData[8:10]
    MsgDataMatchList = MsgData[10:]
    updSQN(self, MsgDataShAddr, MsgDataSQN)
    updLQI(self, MsgDataShAddr, MsgLQI)
    self.log.logging('Input', 'Log', 'Decode8046 - Match Descriptor response: SQN: %s Status: %s Nwkid: %s Lenght: %s List: %s' % (MsgDataSQN, MsgDataStatus, MsgDataShAddr, MsgDataLenList, MsgDataMatchList))
    if MsgDataStatus == '00' and MsgDataLenList != '00' and self.iaszonemgt:
        idx = 0
        while idx < int(MsgDataLenList, 16):
            ep = MsgDataMatchList[idx:idx + 2]
            idx += 2
            self.log.logging('Input', 'Log', 'Decode8046 - Match Descriptor response Nwkid: %sfound Ep: %s Matching 0500' % (MsgDataShAddr, ep))
            self.iaszonemgt.IAS_write_CIE_after_match_descriptor(MsgDataShAddr, ep)def Decode8100(self, Devices, MsgData, MsgLQI):
    MsgSQN = MsgData[:2]
    i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSQN, TYPE_APP_ZCL)
    MsgSrcAddr = MsgData[2:6]
    timeStamped(self, MsgSrcAddr, 33024)
    loggingMessages(self, '8100', MsgSrcAddr, None, MsgLQI, MsgSQN)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    updLQI(self, MsgSrcAddr, MsgLQI)
    MsgSrcEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]
    self.statistics._clusterOK += 1
    if MsgClusterId == '0500':
        self.log.logging('Input', 'Debug', 'Read Attributed Request Response on Cluster 0x0500 for %s' % MsgSrcAddr)
        self.iaszonemgt.IAS_CIE_service_discovery_response(MsgSrcAddr, MsgSrcEp, MsgData)
    scan_attribute_reponse(self, Devices, MsgSQN, i_sqn, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgData, '8100')
    callbackDeviceAwake(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId)def Decode8400(self, Devices, MsgData, MsgLQI):
    sqn = MsgData[:2]
    zonetype = MsgData[2:6]
    manufacturercode = MsgData[6:10]
    nwkid = MsgData[10:14]
    ep = MsgData[14:16]
    self.log.logging('Input', 'Log', 'Decode8400 - IAS Zone Enroll Request NwkId: %s/%s Sqn: %s ZoneType: %s Manuf: %s' % (nwkid, ep, sqn, zonetype, manufacturercode))
    self.iaszonemgt.IAS_zone_enroll_request(nwkid, ep, zonetype, sqn)def Decode8401(self, Devices, MsgData, MsgLQI):
    self.log.logging('Input', 'Debug', 'Decode8401 - Reception Zone status change notification: ' + MsgData)
    MsgSQN = MsgData[:2]
    MsgEp = MsgData[2:4]
    MsgClusterId = MsgData[4:8]
    MsgSrcAddrMode = MsgData[8:10]
    if MsgSrcAddrMode == '02':
        MsgSrcAddr = MsgData[10:14]
        MsgZoneStatus = MsgData[14:18]
        MsgExtStatus = MsgData[18:20]
        MsgZoneID = MsgData[20:22]
        MsgDelay = MsgData[22:26]
    elif MsgSrcAddrMode == '03':
        MsgSrcAddr = MsgData[10:26]
        MsgZoneStatus = MsgData[26:30]
        MsgExtStatus = MsgData[30:32]
        MsgZoneID = MsgData[32:34]
        MsgDelay = MsgData[34:38]
    else:
        self.log.logging('Input', 'Error', 'Decode8401 - Reception Zone status change notification but incorrect Address Mode: ' + MsgSrcAddrMode + ' with MsgData ' + MsgData)
        return
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    if MsgSrcAddr not in self.ListOfDevices:
        self.log.logging('Input', 'Error', 'Decode8401 - unknown IAS device %s from plugin' % MsgSrcAddr)
        if not zigpy_plugin_sanity_check(self, MsgSrcAddr):
            handle_unknow_device(self, MsgSrcAddr)
        return
    if 'Health' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Health'] not in ('Disabled',):
        self.ListOfDevices[MsgSrcAddr]['Health'] = 'Live'
    timeStamped(self, MsgSrcAddr, 33793)
    updSQN(self, MsgSrcAddr, MsgSQN)
    updLQI(self, MsgSrcAddr, MsgLQI)
    Model = ''
    if 'Model' in self.ListOfDevices[MsgSrcAddr]:
        Model = self.ListOfDevices[MsgSrcAddr]['Model']
    self.log.logging('Input', 'Debug', 'Decode8401 - MsgSQN: %s MsgSrcAddr: %s MsgEp:%s MsgClusterId: %s MsgZoneStatus: %s MsgExtStatus: %s MsgZoneID: %s MsgDelay: %s' % (MsgSQN, MsgSrcAddr, MsgEp, MsgClusterId, MsgZoneStatus, MsgExtStatus, MsgZoneID, MsgDelay), MsgSrcAddr)
    if Model == 'PST03A-v2.2.5':
        Decode8401_PST03Av225(self, Devices, MsgSrcAddr, MsgEp, Model, MsgZoneStatus)
        return
    alarm1 = int(MsgZoneStatus, 16) & 1
    alarm2 = int(MsgZoneStatus, 16) >> 1 & 1
    tamper = int(MsgZoneStatus, 16) >> 2 & 1
    battery = int(MsgZoneStatus, 16) >> 3 & 1
    suprrprt = int(MsgZoneStatus, 16) >> 4 & 1
    restrprt = int(MsgZoneStatus, 16) >> 5 & 1
    trouble = int(MsgZoneStatus, 16) >> 6 & 1
    acmain = int(MsgZoneStatus, 16) >> 7 & 1
    test = int(MsgZoneStatus, 16) >> 8 & 1
    battdef = int(MsgZoneStatus, 16) >> 9 & 1
    if 'Ep' not in self.ListOfDevices[MsgSrcAddr]:
        return
    if MsgEp not in self.ListOfDevices[MsgSrcAddr]['Ep']:
        return
    if '0500' not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]:
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]['0500'] = {}
    if not isinstance(self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]['0500'], dict):
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp][MsgClusterId]['0500'] = {}
    if '0002' not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]['0500']:
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]['0500']['0002'] = {}
    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]['0500']['0002'] = 'alarm1: %s, alarm2: %s, tamper: %s, battery: %s, Support Reporting: %s, restore Reporting: %s, trouble: %s, acmain: %s, test: %s, battdef: %s' % (alarm1, alarm2, tamper, battery, suprrprt, restrprt, trouble, acmain, test, battdef)
    self.log.logging('Input', 'Debug', 'IAS Zone for device:%s  - %s' % (MsgSrcAddr, self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]['0500']['0002']), MsgSrcAddr)
    self.log.logging('Input', 'Debug', 'Decode8401 MsgZoneStatus: %s ' % MsgZoneStatus[2:4], MsgSrcAddr)
    value = MsgZoneStatus[2:4]
    motion_via_IAS_alarm = get_device_config_param(self, MsgSrcAddr, 'MotionViaIASAlarm1')
    self.log.logging('Input', 'Debug', 'MotionViaIASAlarm1 = %s' % motion_via_IAS_alarm)
    ias_alarm1_2_merged = get_deviceconf_parameter_value(self, Model, 'IASAlarmMerge', return_default=None)
    self.log.logging('Input', 'Debug', 'IASAlarmMerge = %s' % ias_alarm1_2_merged)
    if ias_alarm1_2_merged:
        self.log.logging('Input', 'Debug', 'IASAlarmMerge alarm1 %s alarm2 %s' % (alarm1, alarm2))
        combined_alarm = alarm2 << 1 | alarm1
        self.log.logging('Input', 'Debug', 'IASAlarmMerge combined value = %02d' % combined_alarm)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0006', '%02d' % combined_alarm)
    elif motion_via_IAS_alarm is not None and motion_via_IAS_alarm == 1:
        self.log.logging('Input', 'Debug', 'Motion detected sending to MajDomo %s/%s %s' % (MsgSrcAddr, MsgEp, alarm1 or alarm2))
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0406', '%02d' % (alarm1 or alarm2))
    elif self.ListOfDevices[MsgSrcAddr]['Model'] in ('lumi.sensor_magnet', 'lumi.sensor_magnet.aq2', 'lumi.sensor_magnet.acn001', 'lumi.magnet.acn001'):
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0006', '%02d' % alarm1)
    elif Model not in ('RC-EF-3.0', 'RC-EM'):
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, MsgClusterId, '%02d' % (alarm1 or alarm2))
    if tamper:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0009', '01')
    else:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0009', '00')
    if battery:
        self.log.logging('Input', 'Log', 'Decode8401 Low Battery or defective battery: Device: %s %s/%s' % (MsgSrcAddr, battdef, battery), MsgSrcAddr)
        self.ListOfDevices[MsgSrcAddr]['IASBattery'] = 5
    else:
        self.ListOfDevices[MsgSrcAddr]['IASBattery'] = 100
    if 'IAS' in self.ListOfDevices[MsgSrcAddr] and 'ZoneStatus' in self.ListOfDevices[MsgSrcAddr]['IAS']:
        if not isinstance(self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus'], dict):
            self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus'] = {}
        self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['alarm1'] = alarm1
        self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['alarm2'] = alarm2
        self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['tamper'] = tamper
        self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['battery'] = battery
        self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['Support Reporting'] = suprrprt
        self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['Restore Reporting'] = restrprt
        self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['trouble'] = trouble
        self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['acmain'] = acmain
        self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['test'] = test
        self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['battdef'] = battdef
        self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['GlobalInfos'] = self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEp]['0500']['0002']
        self.ListOfDevices[MsgSrcAddr]['IAS']['ZoneStatus']['TimeStamp'] = int(time.time())def Decode8401_PST03Av225(self, Devices, MsgSrcAddr, MsgEp, Model, MsgZoneStatus):
    iData = int(MsgZoneStatus, 16) & 8 >> 3
    self.ListOfDevices[MsgSrcAddr]['IASBattery'] = '100' if iData == 0 else '0'
    if MsgEp == '02':
        iData = int(MsgZoneStatus, 16) & 1
        value = '%02d' % iData
        self.log.logging('Input', 'Debug', 'Decode8401 - PST03A-v2.2.5 door/windows status: ' + value, MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0500', value)
    elif MsgEp == '01':
        iData = int(MsgZoneStatus, 16) & 1
        if iData == 1:
            value = '%02d' % iData
            self.log.logging('Input', 'Debug', 'Decode8401 - PST03A-v2.2.5 mouvements alarm', MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0406', value)
        iData = (int(MsgZoneStatus, 16) & 4) >> 2
        if iData == 1:
            value = '%02d' % iData
            self.log.logging('Input', 'Debug', 'Decode8401 - PST03A-V2.2.5  tamper alarm', MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEp, '0006', value)
    else:
        self.log.logging('Input', 'Debug', 'Decode8401 - PST03A-v2.2.5, unknown EndPoint: ' + MsgEp, MsgSrcAddr)
    returndef Decode8110_raw(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrStatus, MsgAttrID, MsgLQI):
    i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSQN, TYPE_APP_ZCL)
    self.log.logging('Input', 'Debug', 'Decode8110 - WriteAttributeResponse - MsgSQN: %s,  MsgSrcAddr: %s, MsgSrcEp: %s, MsgClusterId: %s MsgAttrID: %s Status: %s' % (MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus), MsgSrcAddr)
    timeStamped(self, MsgSrcAddr, 33040)
    updSQN(self, MsgSrcAddr, MsgSQN)
    updLQI(self, MsgSrcAddr, MsgLQI)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    if (self.zigbee_communication != 'native' or (self.FirmwareVersion and int(self.FirmwareVersion, 16) >= int('31d', 16))) and MsgAttrID:
        set_status_datastruct(self, 'WriteAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus)
        set_request_phase_datastruct(self, 'WriteAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, 'fullfilled')
        if MsgAttrStatus != '00':
            self.log.logging('Input', 'Log', 'Decode8110 - Write Attribute Respons response - ClusterID: %s/%s, MsgSrcAddr: %s, MsgSrcEp:%s , Status: %s' % (MsgClusterId, MsgAttrID, MsgSrcAddr, MsgSrcEp, MsgAttrStatus), MsgSrcAddr)
        return
    i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSQN, TYPE_APP_ZCL)
    self.log.logging('Input', 'Debug', '------- - i_sqn: %0s e_sqn: %s' % (i_sqn, MsgSQN))
    for matchAttributeId in list(get_list_isqn_attr_datastruct(self, 'WriteAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId)):
        if get_isqn_datastruct(self, 'WriteAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId, matchAttributeId) != i_sqn:
            continue
        self.log.logging('Input', 'Debug', '------- - Sqn matches for Attribute: %s' % matchAttributeId)
        set_status_datastruct(self, 'WriteAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId, matchAttributeId, MsgAttrStatus)
        set_request_phase_datastruct(self, 'WriteAttributes', MsgSrcAddr, MsgSrcEp, MsgClusterId, matchAttributeId, 'fullfilled')
        if MsgAttrStatus != '00':
            self.log.logging('Input', 'Debug', 'Decode8110 - Write Attribute Response response - ClusterID: %s/%s, MsgSrcAddr: %s, MsgSrcEp:%s , Status: %s' % (MsgClusterId, matchAttributeId, MsgSrcAddr, MsgSrcEp, MsgAttrStatus), MsgSrcAddr)
    if MsgClusterId == '0500':
        self.iaszonemgt.IAS_CIE_write_response(MsgSrcAddr, MsgSrcEp, MsgAttrStatus)