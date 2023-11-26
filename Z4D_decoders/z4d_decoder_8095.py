def Decode8095(self, Devices, MsgData, MsgLQI):
    """Remote button pressed ON/OFF"""
    MsgSQN = MsgData[:2]
    MsgEP = MsgData[2:4]
    MsgClusterId = MsgData[4:8]
    unknown_ = MsgData[8:10]
    MsgSrcAddr = MsgData[10:14]
    MsgCmd = MsgData[14:16]
    MsgPayload = MsgData[16:] if len(MsgData) > 16 else None
    updLQI(self, MsgSrcAddr, MsgLQI)
    self.log.logging('Input', 'Debug', 'Decode8095 - MsgData: %s' % MsgData, MsgSrcAddr)
    if MsgSrcAddr not in self.ListOfDevices:
        if not zigpy_plugin_sanity_check(self, MsgSrcAddr):
            handle_unknow_device(self, MsgSrcAddr)
        return
    if self.ListOfDevices[MsgSrcAddr]['Status'] != 'inDB':
        if not zigpy_plugin_sanity_check(self, MsgSrcAddr):
            handle_unknow_device(self, MsgSrcAddr)
        return
    if check_duplicate_sqn(self, MsgSrcAddr, MsgEP, MsgClusterId, MsgSQN):
        return
    updSQN(self, MsgSrcAddr, MsgSQN)
    updLQI(self, MsgSrcAddr, MsgLQI)
    timeStamped(self, MsgSrcAddr, 32917)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    if 'Model' not in self.ListOfDevices[MsgSrcAddr]:
        return
    _ModelName = self.ListOfDevices[MsgSrcAddr]['Model']
    self.log.logging('Input', 'Debug', 'Decode8095 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Payload: %s Unknown: %s Model: %s' % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgPayload, unknown_, _ModelName), MsgSrcAddr)
    if _ModelName in ('TRADFRI remote control', 'Remote Control N2'):
        ikea_remote_control_8095(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_)
    elif _ModelName in ('ROM001',):
        self.log.logging('Input', 'Debug', 'Decode8095 - Philips Hue ROM001  MsgCmd: %s' % MsgCmd, MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, '0008', 'toggle')
    elif _ModelName == 'TRADFRI motion sensor':
        ikea_motion_sensor_8095(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_)
    elif _ModelName in ('TRADFRI onoff switch', 'TRADFRI on/off switch', 'TRADFRI SHORTCUT Button', 'TRADFRI openclose remote', 'TRADFRI open/close remote'):
        ikea_remote_switch_8095(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_)
    elif _ModelName == 'RC 110':
        ONOFF_TYPE = {'40': 'onoff_with_effect', '00': 'off', '01': 'on'}
        delayed_all_off = effect_variant = None
        if len(MsgData) >= 16:
            delayed_all_off = MsgData[16:18]
        if len(MsgData) >= 18:
            effect_variant = MsgData[18:20]
        if MsgCmd in ONOFF_TYPE and ONOFF_TYPE[MsgCmd] in ('on', 'off'):
            self.log.logging('Input', 'Log', 'Decode8095 - RC 110 ON/Off Command from: %s/%s Cmd: %s Delayed: %s Effect: %s' % (MsgSrcAddr, MsgEP, MsgCmd, delayed_all_off, effect_variant), MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' % (MsgCmd, unknown_)
        else:
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' % (MsgCmd, unknown_)
            self.log.logging('Input', 'Log', 'Decode8095 - RC 110 Unknown Command: %s for %s/%s, Cmd: %s, Unknown: %s ' % (MsgCmd, MsgSrcAddr, MsgEP, MsgCmd, unknown_), MsgSrcAddr)
    elif _ModelName in LEGRAND_REMOTE_SWITCHS:
        legrand_remote_switch_8095(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_)
    elif _ModelName in LEGRAND_REMOTE_MOTION:
        legrand_motion_8095(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_)
        self.log.logging('Input', 'Log', 'Decode8095 - Legrand: %s/%s, Cmd: %s, Unknown: %s ' % (MsgSrcAddr, MsgEP, MsgCmd, unknown_), MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, '0406', unknown_)
    elif _ModelName == 'Lightify Switch Mini':
        if MsgCmd in ('00', '01'):
            self.log.logging('Input', 'Log', 'Decode8095 - OSRAM Lightify Switch Mini: %s/%s, Cmd: %s, Unknown: %s ' % (MsgSrcAddr, MsgEP, MsgCmd, unknown_), MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, '03', MsgClusterId, MsgCmd)
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' % (MsgCmd, unknown_)
        else:
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' % (MsgCmd, unknown_)
            self.log.logging('Input', 'Log', 'Decode8095 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s ' % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_), MsgSrcAddr)
    elif _ModelName in ('lumi.remote.b686opcn01-bulb', 'lumi.remote.b486opcn01-bulb', 'lumi.remote.b286opcn01-bulb'):
        AqaraOppleDecoding(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, _ModelName, MsgData)
    elif _ModelName == 'WB01':
        if MsgCmd == '00':
            WidgetSelector = '03'
        elif MsgCmd == '01':
            WidgetSelector = '02'
        elif MsgCmd == '02':
            WidgetSelector = '01'
        else:
            return
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, '0006', WidgetSelector)
    elif _ModelName == 'KF204':
        if MsgCmd == '00':
            MajDomoDevice(self, Devices, MsgSrcAddr, '01', '0006', '02')
        elif MsgCmd == '01':
            MajDomoDevice(self, Devices, MsgSrcAddr, '01', '0006', '01')
    elif get_deviceconf_parameter_value(self, _ModelName, 'TUYA_REMOTE', return_default=None) or _ModelName in ('TS0041', 'TS0043', 'TS0044', 'TS0042', 'TS004F', 'TS004F-_TZ3000_xabckq1v'):
        self.log.logging('Input', 'Debug', 'Decode8095 - Tuya %s  Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, MsgPayload: %s ' % (_ModelName, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgPayload), MsgSrcAddr)
        if MsgCmd[:2] == 'fd' and MsgPayload:
            if MsgPayload == '00':
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, '0006', '01')
                checkAndStoreAttributeValue(self, MsgSrcAddr, MsgEP, MsgClusterId, '0000', MsgPayload)
            elif MsgPayload == '01':
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, '0006', '02')
                checkAndStoreAttributeValue(self, MsgSrcAddr, MsgEP, MsgClusterId, '0000', MsgPayload)
            elif MsgPayload == '02':
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, '0006', '03')
                checkAndStoreAttributeValue(self, MsgSrcAddr, MsgEP, MsgClusterId, '0000', MsgPayload)
            elif MsgPayload == '03':
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, '0006', '04')
                checkAndStoreAttributeValue(self, MsgSrcAddr, MsgEP, MsgClusterId, '0000', MsgPayload)
    elif _ModelName == 'TS1001':
        self.log.logging('Input', 'Log', 'Decode8095 - Lidl Remote SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s' % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))
    elif _ModelName in ('lumi.remote.b28ac1',):
        self.log.logging('Input', 'Log', 'Decode8095 - Lumi Remote SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s' % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))
    elif get_deviceconf_parameter_value(self, self.ListOfDevices[MsgSrcAddr]['Model'], 'HUE_RWL'):
        self.log.logging('Input', 'Log', 'Decode8095 - Model: %s SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s ' % (_ModelName, MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_), MsgSrcAddr)
        if MsgCmd == '40':
            MajDomoDevice(self, Devices, MsgSrcAddr, '02', '0006', '00')
        elif MsgCmd == '01':
            MajDomoDevice(self, Devices, MsgSrcAddr, '02', '0006', '01')
    else:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, '0006', MsgCmd)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' % (MsgCmd, unknown_)
        self.log.logging('Input', 'Log', 'Decode8095 - Model: %s SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s ' % (_ModelName, MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_), MsgSrcAddr)