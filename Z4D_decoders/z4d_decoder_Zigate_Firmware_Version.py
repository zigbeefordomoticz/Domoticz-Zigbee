
from Modules.zigbeeVersionTable import (FIRMWARE_BRANCH, set_display_firmware_version)


def Decode8010(self, Devices, MsgData, MsgLQI):  # Reception Firmware Version
    MsgLen = len(MsgData)
    self.FirmwareBranch = MsgData[:2] 
    if len(MsgData) == 8:
        # Zigate Firmware
        _zigate_firmware(self, MsgData)

    else:
        # Zigpy 20/21/1217/20211217
        zigpy_firmware(self, MsgData)

    self.ListOfDevices.setdefault('0000', {'Model': {}})

    self.log.logging("Input", "Debug", "Decode8010 - Reception Version list:%s len: %s Branch: %s Major: %s Version: %s" % (
        MsgData, MsgLen, self.FirmwareBranch, self.FirmwareMajorVersion, self.FirmwareVersion))

    if self.FirmwareBranch in FIRMWARE_BRANCH:
        handle_firmware_branch(self)
        _update_controller_data(self)
        set_display_firmware_version( self )

    _update_additional_components(self)

    self.PDMready = True
    

def _zigate_firmware(self, MsgData):
    self.FirmwareMajorVersion = MsgData[2:4]
    self.FirmwareVersion = MsgData[4:8]


def zigpy_firmware(self, MsgData):
    self.log.logging("Input", "Debug", "Decode8010 %s" %MsgData)
    
    self.FirmwareMajorVersion = MsgData[:2]
    FirmwareMinorVersion = MsgData[4:8]
    self.FirmwareVersion = MsgData[8:]
    
    self.log.logging("Input", "Debug", "Decode8010 Major: %s Minor: %s Full: %s" %(
        self.FirmwareMajorVersion, FirmwareMinorVersion, self.FirmwareVersion ))
   

def handle_firmware_branch(self):
    if int(self.FirmwareBranch) in {98, 99}:
        _handle_untested_adapter( self)

    elif int(self.FirmwareBranch) == 11:
        _handle_zigate_via_zigpy(self)

    elif int(self.FirmwareBranch) >= 20:
        _handle_zigpy(self)
        
    elif self.FirmwareMajorVersion == "03":
        _handle_zigate_pdm_legacy( self )
            
    elif self.FirmwareMajorVersion == "04":   
        _handle_zigate_opti_pdm( self)

    elif self.FirmwareMajorVersion == "05":
        _handle_zigate_v2(self)
        
    else:
        _handle_untested_adapter( self)


def _handle_untested_adapter(self):
    self.log.logging(
        "Input",
        "Status",
        "Untested Zigbee adapter model. If this is a Sonoff USB Dongle E that is a known issue, otherwise please report to the Zigbee for Domoticz team"
    )
    self.pluginParameters["CoordinatorModel"] = FIRMWARE_BRANCH[self.FirmwareBranch]
    self.pluginParameters["CoordinatorFirmwareVersion"] = self.FirmwareVersion


def _handle_zigpy(self):
    self.log.logging("Input", "Status", "%s" % FIRMWARE_BRANCH[self.FirmwareBranch])
    
    self.ListOfDevices['0000']['Model'] = FIRMWARE_BRANCH[self.FirmwareBranch]
    
    self.pluginParameters["CoordinatorModel"] = FIRMWARE_BRANCH[self.FirmwareBranch]
    self.pluginParameters["CoordinatorFirmwareVersion"] = self.FirmwareVersion

    # Additional branches can be added here

def _handle_zigate_via_zigpy(self):
    #Zigpy-Zigate
    self.log.logging("Input", "Status", "%s" %FIRMWARE_BRANCH[ self.FirmwareBranch ])
    
    self.ControllerData["Controller firmware"] = FIRMWARE_BRANCH[ self.FirmwareBranch ]

    # the Build date is coded into "20" + "%02d" %int(FirmwareMajorVersion,16) + "%04d" %int(FirmwareVersion,16)
    if int(self.FirmwareMajorVersion,16) == 0x03:
        _extracted_from_handle_zigate_via_zigpy_7( self, "Zigpy-zigate, Zigate V1 (legacy) %04x", "Zigate V1 (legacy)" )

    elif int(self.FirmwareMajorVersion,16) == 0x04:
        _extracted_from_handle_zigate_via_zigpy_7( self, "Zigpy-zigate, Zigate V1 (OptiPDM) %04x", "Zigate V1 (OptiPDM)" )

    elif int(self.FirmwareMajorVersion,16) == 0x05:
        _extracted_from_handle_zigate_via_zigpy_7( self, "Zigpy-zigate, Zigate V2 %04x", "Zigate V2" )

    else:
        self.log.logging("Input", "Status", "%04x" %int(self.FirmwareMajorVersion,16))
        version =""


def _extracted_from_handle_zigate_via_zigpy_7(self, arg0, arg1):
    version = arg0 % ( int(self.FirmwareVersion,16))
    
    self.pluginParameters["CoordinatorModel"] = arg1
    self.pluginParameters["CoordinatorFirmwareVersion"] = "%04x" %( int(self.FirmwareVersion,16))
    
    
def _handle_zigate_pdm_legacy( self):
    self.log.logging("Input", "Status", "ZiGate Classic PDM (legacy)")

    self.ZiGateModel = 1
    self.ListOfDevices[ '0000' ]['Model'] = 'ZiGate Classic PDM (legacy)'
    self.pluginParameters["CoordinatorModel"] = 'ZiGate Classic PDM (legacy)'
    self.pluginParameters["CoordinatorFirmwareVersion"] = "%04x" %( int(self.FirmwareVersion,16))


def _handle_zigate_opti_pdm( self):
    self.log.logging("Input", "Status", "ZiGate Classic PDM (OptiPDM)")

    self.ZiGateModel = 1
    self.ListOfDevices[ '0000' ]['Model'] = 'ZiGate Classic PDM (OptiPDM)'
    self.pluginParameters["CoordinatorModel"] = 'ZiGate Classic PDM (OptiPDM)'
    self.pluginParameters["CoordinatorFirmwareVersion"] = "%04x" %( int(self.FirmwareVersion,16))


def _handle_zigate_v2(self):
    self.log.logging("Input", "Status", "ZiGate+ (V2)")

    self.ListOfDevices[ '0000' ]['Model'] = 'ZiGate+ (V2)'
    self.ZiGateModel = 2
    self.pluginParameters["CoordinatorModel"] = 'ZiGate+ (V2)'
    self.pluginParameters["CoordinatorFirmwareVersion"] = "%04x" %( int(self.FirmwareVersion,16))


def _update_controller_data(self):
    self.log.logging("Input", "Status", "Installer Version Number: %s" % self.FirmwareVersion)

    self.log.logging("Input", "Status", "Branch Version: ==> %s <==" % FIRMWARE_BRANCH[self.FirmwareBranch])
    self.ControllerData["Firmware Version"] = "Branch: %s Major: %s Version: %s" % (
        self.FirmwareBranch,
        self.FirmwareMajorVersion,
        self.FirmwareVersion,
    )
    self.ControllerData["Branch Version"] = self.FirmwareBranch
    self.ControllerData["Major Version"] = self.FirmwareMajorVersion
    self.ControllerData["Minor Version"] = self.FirmwareVersion


def _update_additional_components(self):

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
