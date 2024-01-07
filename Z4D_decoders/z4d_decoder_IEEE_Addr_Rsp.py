from Modules.basicOutputs import handle_unknow_device
from Modules.domoTools import lastSeenUpdate
from Modules.errorCodes import DisplayStatusCode
from Modules.tools import (DeviceExist, loggingMessages, timeStamped,
                           zigpy_plugin_sanity_check)


def Decode8041(self, Devices, MsgData, MsgLQI):
    MsgSequenceNumber = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    MsgIEEE = MsgData[4:20]
    if MsgDataStatus != '00':
        self.log.logging('Input', 'Debug', 'Decode8041 - Reception of IEEE Address response for %s with status %s' % (MsgIEEE, MsgDataStatus))
        return
    
    MsgShortAddress = MsgData[20:24]
    extendedResponse = False
    
    if len(MsgData) > 24:
        extendedResponse = True
        MsgNumAssocDevices = MsgData[24:26]
        MsgStartIndex = MsgData[26:28]
        MsgDeviceList = MsgData[28:]
        
    if extendedResponse:
        self.log.logging('Input', 'Debug', 'Decode8041 - IEEE Address response, Sequence number: %s Status: %s IEEE: %s  NwkId: %s nbAssociated Devices: %s StartIdx: %s DeviceList: %s' % (MsgSequenceNumber, DisplayStatusCode(MsgDataStatus), MsgIEEE, MsgShortAddress, MsgNumAssocDevices, MsgStartIndex, MsgDeviceList))

    if MsgShortAddress == '0000' and self.ControllerIEEE and (MsgIEEE != self.ControllerIEEE):
        self.log.logging('Input', 'Error', 'Decode8041 - Receive an IEEE: %s with a NwkId: %s something wrong !!!' % (MsgIEEE, MsgShortAddress))
        return

    elif self.ControllerIEEE and MsgIEEE == self.ControllerIEEE and (MsgShortAddress != '0000'):
        self.log.logging('Input', 'Log', 'Decode8041 - Receive an IEEE: %s with a NwkId: %s something wrong !!!' % (MsgIEEE, MsgShortAddress))
        return

    if MsgShortAddress in self.ListOfDevices and 'IEEE' in self.ListOfDevices[MsgShortAddress] and (self.ListOfDevices[MsgShortAddress]['IEEE'] == MsgShortAddress):
        self.log.logging('Input', 'Debug', 'Decode8041 - Receive an IEEE: %s with a NwkId: %s' % (MsgIEEE, MsgShortAddress))
        timeStamped(self, MsgShortAddress, 32833)
        loggingMessages(self, '8041', MsgShortAddress, MsgIEEE, MsgLQI, MsgSequenceNumber)
        lastSeenUpdate(self, Devices, NwkId=MsgShortAddress)
        return

    if MsgIEEE in self.IEEE2NWK:
        self.log.logging('Input', 'Debug', 'Decode8041 - Receive an IEEE: %s with a NwkId: %s, will try to reconnect' % (MsgIEEE, MsgShortAddress))

        if not DeviceExist(self, Devices, MsgShortAddress, MsgIEEE):
            if not zigpy_plugin_sanity_check(self, MsgShortAddress):
                handle_unknow_device(self, MsgShortAddress)
            self.log.logging('Input', 'Log', 'Decode8041 - Not able to reconnect (unknown device) %s %s' % (MsgIEEE, MsgShortAddress))
            return

        timeStamped(self, MsgShortAddress, 32833)
        loggingMessages(self, '8041', MsgShortAddress, MsgIEEE, MsgLQI, MsgSequenceNumber)
        lastSeenUpdate(self, Devices, NwkId=MsgShortAddress)
        return

    self.log.logging('Input', 'Log', 'WARNING - Decode8041 - Receive an IEEE: %s with a NwkId: %s, not known by the plugin' % (MsgIEEE, MsgShortAddress))