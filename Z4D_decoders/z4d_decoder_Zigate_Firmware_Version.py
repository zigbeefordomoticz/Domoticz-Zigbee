
from Modules.zigbeeVersionTable import (FIRMWARE_BRANCH, set_display_firmware_version)


    
    
def Decode8010(self, Devices, MsgData, MsgLQI):
    MsgLen = len(MsgData)
    self.FirmwareBranch = MsgData[:2]

    if MsgLen == 8:
        self.FirmwareMajorVersion = MsgData[2:4]
        self.FirmwareVersion = MsgData[4:8]

    else:
        self.log.logging('Input', 'Debug', f'Decode8010 {MsgData}')
        self.FirmwareMajorVersion = MsgData[:2]
        FirmwareMinorVersion = MsgData[4:8]
        self.FirmwareVersion = MsgData[8:]
        self.log.logging('Input', 'Debug', f'Decode8010 Major: {self.FirmwareMajorVersion} Minor: {FirmwareMinorVersion} Full: {self.FirmwareVersion}')

    default_device_key = '0000'
    if default_device_key not in self.ListOfDevices:
        self.ListOfDevices[default_device_key] = {'Model': {}}

    self.log.logging('Input', 'Debug', f'Decode8010 - Reception Version list: {MsgData} len: {MsgLen} Branch: {self.FirmwareBranch} Major: {self.FirmwareMajorVersion} Version: {self.FirmwareVersion}')

    if self.FirmwareBranch in FIRMWARE_BRANCH:
        firmware_branch_int = int(self.FirmwareBranch)

        if firmware_branch_int in {98, 99}:
            self.log.logging('Input', 'Status', 'Untested Zigbee adapter model. If this is a Sonoff USB Dongle E that is a known issue, otherwise, please report to the Zigbee for Domoticz team')
            self.pluginParameters['CoordinatorModel'] = FIRMWARE_BRANCH[self.FirmwareBranch]

        elif firmware_branch_int == 11:
            HandleFirmwareBranch11(self)

        elif firmware_branch_int >= 20:
            HandleFirmwareBranch20(self)

        else:
            self.log.logging('Input', 'Status', f'{FIRMWARE_BRANCH[self.FirmwareBranch]}')
            version = ''

        self.log.logging('Input', 'Status', f'Installer Version Number: {self.FirmwareVersion}')
        self.log.logging('Input', 'Status', f'Branch Version: ==> {FIRMWARE_BRANCH[self.FirmwareBranch]} <==')
        UpdateControllerData(self)

    set_display_firmware_version( self )
    update_firmware_version_to_objects( self )
    self.PDMready = True


def update_firmware_version_to_objects( self ):
    
    if self.webserver:
        self.webserver.update_firmware(self.FirmwareVersion)
        self.ControllerLink.update_ZiGate_HW_Version(self.ZiGateModel)

    if self.groupmgt:
        self.groupmgt.update_firmware(self.FirmwareVersion)

    if self.ControllerLink:
        self.ControllerLink.update_ZiGate_Version(self.FirmwareVersion, self.FirmwareMajorVersion)

    if self.networkmap:
        self.networkmap.update_firmware(self.FirmwareVersion)

    if self.log:
        self.log.loggingUpdateFirmware(self.FirmwareVersion, self.FirmwareMajorVersion)


def HandleFirmwareBranch11(self):
    self.log.logging('Input', 'Status', f'{FIRMWARE_BRANCH[self.FirmwareBranch]}')
    self.ControllerData['Controller firmware'] = FIRMWARE_BRANCH[self.FirmwareBranch]

    major_version_int = int(self.FirmwareMajorVersion, 16)
    version = ''

    if major_version_int == 3:
        version = self.HandleVersion('Zigpy-zigate, Zigate V1 (legacy)')
    elif major_version_int == 4:
        version = self.HandleVersion('Zigpy-zigate, Zigate V1 (OptiPDM)')
    elif major_version_int == 5:
        version = self.HandleVersion('Zigpy-zigate, Zigate V2')

    self.log.logging('Input', 'Status', f'{self.FirmwareMajorVersion}')
    self.log.logging('Input', 'Status', f'{version}')


def HandleVersion(self, model):
    version = f'{model} %04x' % int(self.FirmwareVersion, 16)
    self.pluginParameters['CoordinatorModel'] = model
    self.pluginParameters['CoordinatorFirmwareVersion'] = '%04x' % int( self.FirmwareVersion, 16 )
    return version


def HandleFirmwareBranch20(self):
    self.log.logging('Input', 'Status', f'{FIRMWARE_BRANCH[self.FirmwareBranch]}')
    self.ListOfDevices['0000']['Model'] = FIRMWARE_BRANCH[self.FirmwareBranch]
    self.pluginParameters['CoordinatorModel'] = FIRMWARE_BRANCH[self.FirmwareBranch]
    self.pluginParameters['CoordinatorFirmwareVersion'] = self.FirmwareVersion


def UpdateControllerData(self):
    self.ControllerData['Firmware Version'] = f'Branch: {self.FirmwareBranch} Major: {self.FirmwareMajorVersion} Version: {self.FirmwareVersion}'
    self.ControllerData['Branch Version'] = self.FirmwareBranch
    self.ControllerData['Major Version'] = self.FirmwareMajorVersion
    self.ControllerData['Minor Version'] = self.FirmwareVersion
