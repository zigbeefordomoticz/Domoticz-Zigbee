def Decode8085(self, Devices, MsgData, MsgLQI):
    """Remote button pressed"""
    MsgSQN = MsgData[:2]
    MsgEP = MsgData[2:4]
    MsgClusterId = MsgData[4:8]
    unknown_ = MsgData[8:10]
    MsgSrcAddr = MsgData[10:14]
    MsgCmd = MsgData[14:16]
    updLQI(self, MsgSrcAddr, MsgLQI)
    self.log.logging('Input', 'Debug', 'Decode8085 - MsgData: %s' % MsgData, MsgSrcAddr)
    self.log.logging('Input', 'Debug', 'Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s ' % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_), MsgSrcAddr)
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
    timeStamped(self, MsgSrcAddr, 32901)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    if 'Model' not in self.ListOfDevices[MsgSrcAddr]:
        self.log.logging('Input', 'Log', 'Decode8085 - No Model Name !')
        return
    _ModelName = self.ListOfDevices[MsgSrcAddr]['Model']
    if _ModelName in ('TRADFRI remote control', 'Remote Control N2'):
        ikea_remote_control_8085(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_)
    elif _ModelName in ('ROM001',):
        self.log.logging('Input', 'Debug', 'Decode8085 - Philips Hue ROM001  MsgCmd: %s' % MsgCmd, MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, '0008', 'move')
    elif _ModelName in ('TRADFRI onoff switch', 'TRADFRI on/off switch', 'TRADFRI SHORTCUT Button', 'TRADFRI openclose remote', 'TRADFRI open/close remote'):
        ikea_remote_switch_8085(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_)
    elif _ModelName == 'RC 110':
        if MsgClusterId != '0008':
            self.log.logging('Input', 'Log', 'Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s' % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))
            self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' % (MsgCmd, unknown_)
            return
        (step_mod, up_down, step_size, transition) = extract_info_from_8085(MsgData)
        self.log.logging('Input', 'Log', 'Decode8085 - INNR RC 110 step_mod: %s direction: %s, size: %s, transition: %s' % (step_mod, up_down, step_size, transition), MsgSrcAddr)
        TYPE_ACTIONS = {None: '', '01': 'move', '02': 'click', '03': 'stop', '04': 'move_to'}
        DIRECTION = {None: '', '00': 'up', '01': 'down'}
        SCENES = {None: '', '02': 'scene1', '34': 'scene2', '66': 'scene3', '99': 'scene4', 'c2': 'scene5', 'fe': 'scene6'}
        if TYPE_ACTIONS[step_mod] in ('click', 'move'):
            selector = TYPE_ACTIONS[step_mod] + DIRECTION[up_down]
        elif TYPE_ACTIONS[step_mod] in 'move_to':
            selector = SCENES[up_down]
        elif TYPE_ACTIONS[step_mod] in 'stop':
            selector = TYPE_ACTIONS[step_mod]
        else:
            return
        self.log.logging('Input', 'Debug', 'Decode8085 - INNR RC 110 selector: %s' % selector, MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, selector)
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = selector
    elif _ModelName == 'TRADFRI wireless dimmer':
        ikea_wireless_dimer_8085(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, MsgData)
    elif _ModelName in LEGRAND_REMOTE_SWITCHS:
        legrand_remote_switch_8085(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, MsgData)
    elif _ModelName in LEGRAND_REMOTE_MOTION:
        legrand_motion_8085(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, MsgData)
        (step_mod, up_down, step_size, transition) = extract_info_from_8085(MsgData)
        self.log.logging('Input', 'Log', 'Decode8085 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s step_mode: %s up_down: %s step_size: %s transition: %s' % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, step_mod, up_down, step_size, transition), MsgSrcAddr)
    elif _ModelName == 'Lightify Switch Mini':
        (step_mod, up_down, step_size, transition) = extract_info_from_8085(MsgData)
        self.log.logging('Input', 'Log', 'Decode8085 - OSRAM Lightify Switch Mini %s/%s: Mod %s, UpDown %s Size %s Transition %s' % (MsgSrcAddr, MsgEP, step_mod, up_down, step_size, transition))
        if MsgCmd == '04':
            self.log.logging('Input', 'Log', 'Decode8085 - OSRAM Lightify Switch Mini %s/%s Central button' % (MsgSrcAddr, MsgEP))
            MajDomoDevice(self, Devices, MsgSrcAddr, '03', MsgClusterId, '02')
        elif MsgCmd == '05':
            self.log.logging('Input', 'Log', 'Decode8085 - OSRAM Lightify Switch Mini %s/%s Long press Up button' % (MsgSrcAddr, MsgEP))
            MajDomoDevice(self, Devices, MsgSrcAddr, '03', MsgClusterId, '03')
        elif MsgCmd == '01':
            self.log.logging('Input', 'Log', 'Decode8085 - OSRAM Lightify Switch Mini %s/%s Long press Down button' % (MsgSrcAddr, MsgEP))
            MajDomoDevice(self, Devices, MsgSrcAddr, '03', MsgClusterId, '04')
        elif MsgCmd == '03':
            self.log.logging('Input', 'Log', 'Decode8085 - OSRAM Lightify Switch Mini %s/%s release' % (MsgSrcAddr, MsgEP))
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' % (MsgCmd, unknown_)
    elif _ModelName in ('lumi.remote.b686opcn01-bulb', 'lumi.remote.b486opcn01-bulb', 'lumi.remote.b286opcn01-bulb'):
        AqaraOppleDecoding(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, _ModelName, MsgData)
    elif _ModelName == 'tint-Remote-white':
        if MsgCmd == '02':
            MsgMode = MsgData[16:18]
            if MsgMode == '01':
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, '04')
            elif MsgMode == '00':
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, '05')
        if MsgCmd == '01':
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, '06')
        if MsgCmd == '05':
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, '07')
        if MsgCmd == '03':
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, '08')
    elif _ModelName == 'TS1001':
        (step_mod, up_down, step_size, transition) = extract_info_from_8085(MsgData)
        self.log.logging('Input', 'Log', 'Decode8085 - Lidl Remote SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s step_mod: %s step_size: %s up_down: %s' % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, step_mod, step_size, up_down))
    elif get_deviceconf_parameter_value(self, self.ListOfDevices[MsgSrcAddr]['Model'], 'HUE_RWL'):
        self.log.logging('Input', 'Log', 'Decode8085 - Model: %s SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s ' % (_ModelName, MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_), MsgSrcAddr)
    elif 'Manufacturer' in self.ListOfDevices[MsgSrcAddr]:
        if self.ListOfDevices[MsgSrcAddr]['Manufacturer'] == '1110':
            self.log.logging('Input', 'Log', 'MsgData: %s' % MsgData)
            TYPE_ACTIONS = {None: '', '03': 'stop', '05': 'move'}
            DIRECTION = {None: '', '00': 'up', '01': 'down'}
            (step_mod, up_down, step_size, transition) = extract_info_from_8085(MsgData)
            self.log.logging('Input', 'Log', 'step_mod: %s' % step_mod)
            if step_mod in TYPE_ACTIONS:
                self.log.logging('Input', 'Error', 'Decode8085 - Profalux Remote, unknown Action: %s' % step_mod)
            selector = None
            if TYPE_ACTIONS[step_mod] in 'move':
                selector = TYPE_ACTIONS[step_mod] + DIRECTION[up_down]
            elif TYPE_ACTIONS[step_mod] in 'stop':
                selector = TYPE_ACTIONS[step_mod]
            else:
                self.log.logging('Input', 'Error', 'Decode8085 - Profalux remote Unknown state for %s step_mod: %s up_down: %s' % (MsgSrcAddr, step_mod, up_down))
            self.log.logging('Input', 'Debug', 'Decode8085 - Profalux remote selector: %s' % selector, MsgSrcAddr)
            if selector:
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, selector)
    else:
        self.log.logging('Input', 'Log', 'Decode8085 - Model: %s SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s ' % (_ModelName, MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_))
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, %s' % (MsgCmd, unknown_)