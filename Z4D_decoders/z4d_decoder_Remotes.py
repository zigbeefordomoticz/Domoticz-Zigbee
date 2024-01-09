

from Modules.basicOutputs import handle_unknow_device
from Modules.domoMaj import MajDomoDevice
from Modules.domoTools import lastSeenUpdate
from Modules.ikeaTradfri import (ikea_motion_sensor_8095,
                                 ikea_remote_control_80A7,
                                 ikea_remote_control_8085,
                                 ikea_remote_control_8095,
                                 ikea_remote_switch_8085,
                                 ikea_remote_switch_8095,
                                 ikea_remoteN2_control_80A7,
                                 ikea_wireless_dimer_8085)
from Modules.legrand_netatmo import (legrand_motion_8085, legrand_motion_8095,
                                     legrand_remote_switch_8085,
                                     legrand_remote_switch_8095)
from Modules.lumi import AqaraOppleDecoding
from Modules.tools import (checkAndStoreAttributeValue, extract_info_from_8085,
                           get_deviceconf_parameter_value, timeStamped, updLQI,
                           updSQN, zigpy_plugin_sanity_check)
from Modules.zigateConsts import LEGRAND_REMOTE_MOTION, LEGRAND_REMOTE_SWITCHS
from Z4D_decoders.z4d_decoder_helpers import check_duplicate_sqn


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

    remote_scene_mapping_data = get_deviceconf_parameter_value(self, _ModelName, 'REMOTE_SCENE_MAPPING')
    if remote_scene_mapping_data:
        return scene_mapping(self, Devices, remote_scene_mapping_data, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_ )

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

    remote_scene_mapping_data = get_deviceconf_parameter_value(self, _ModelName, 'REMOTE_SCENE_MAPPING')
    if remote_scene_mapping_data:
        return scene_mapping(self, Devices, remote_scene_mapping_data, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_ )

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
        
def Decode80A7(self, Devices, MsgData, MsgLQI):
    """Remote button pressed (LEFT/RIGHT)"""
    MsgSQN = MsgData[:2]
    MsgEP = MsgData[2:4]
    MsgClusterId = MsgData[4:8]
    MsgCmd = MsgData[8:10]
    MsgDirection = MsgData[10:12]
    unkown_ = MsgData[12:18]
    MsgSrcAddr = MsgData[18:22]
    _ModelName = self.ListOfDevices[MsgSrcAddr]['Model']
    if MsgSrcAddr not in self.ListOfDevices:
        if not zigpy_plugin_sanity_check(self, MsgSrcAddr):
            handle_unknow_device(self, MsgSrcAddr)
        return
    if self.ListOfDevices[MsgSrcAddr]['Status'] != 'inDB':
        if not zigpy_plugin_sanity_check(self, MsgSrcAddr):
            handle_unknow_device(self, MsgSrcAddr)
        return
    updLQI(self, MsgSrcAddr, MsgLQI)
    check_duplicate_sqn(self, MsgSrcAddr, MsgEP, MsgClusterId, MsgSQN)
    timeStamped(self, MsgSrcAddr, 32935)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)

    remote_scene_mapping_data = get_deviceconf_parameter_value(self, _ModelName, 'REMOTE_SCENE_MAPPING')
    if remote_scene_mapping_data:
        return scene_mapping(self, Devices, remote_scene_mapping_data, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unkown_, MsgDirection )

    if _ModelName in ('TRADFRI remote control',):
        ikea_remote_control_80A7(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_)
    elif _ModelName in ('Remote Control N2',):
        ikea_remoteN2_control_80A7(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_)
    else:
        self.log.logging('Input', 'Log', 'Decode80A7 - SQN: %s, Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Direction: %s, Unknown_ %s' % (MsgSQN, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_))
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgEP][MsgClusterId]['0000'] = 'Cmd: %s, Direction: %s, %s' % (MsgCmd, MsgDirection, unkown_)


def scene_mapping(self, Devices, remote_scene_mapping_data, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd=None, unknown_=None, MsgDirection=None):
    """Implementation based on Device JSON configuration."""

    self.log.logging('Input', 'Log', f"scene_mapping {MsgSrcAddr} {MsgEP} {MsgClusterId} {MsgCmd} {unknown_} {MsgDirection} {remote_scene_mapping_data}")

    matching_criteria = f"{MsgCmd}_{unknown_}_{MsgDirection}" if MsgDirection is not None else f"{MsgCmd}_{unknown_}"

    cluster_mapping = remote_scene_mapping_data.get(MsgClusterId, {})
    device_mapping = cluster_mapping.get(matching_criteria, None)

    self.log.logging('Input', 'Log', f"   mapping found ( {MsgCmd} {unknown_} {MsgDirection}) -> {device_mapping}")

    if device_mapping:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, device_mapping)
