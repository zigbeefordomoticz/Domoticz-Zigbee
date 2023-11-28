import time

from Modules.basicInputs import read_attribute_response
from Modules.basicOutputs import handle_unknow_device
from Modules.domoTools import lastSeenUpdate
from Modules.livolo import livolo_read_attribute_request
from Modules.schneider_wiser import wiser_read_attribute_request
from Modules.timeServer import timeserver_read_attribute_request
from Modules.tools import (timeStamped, updLQI, updSQN,
                           zigpy_plugin_sanity_check)


def Decode0100(self, Devices, MsgData, MsgLQI):
    MsgSqn = MsgData[:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSrcEp = MsgData[6:8]
    MsgDstEp = MsgData[8:10]
    updLQI(self, MsgSrcAddr, MsgLQI)
    timeStamped(self, MsgSrcAddr, 256)
    lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)
    if MsgSrcAddr not in self.ListOfDevices:
        if not zigpy_plugin_sanity_check(self, MsgSrcAddr):
            handle_unknow_device(self, MsgSrcAddr)
        return
    if 'Model' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Model'] == 'TI0001' or ('Manufacturer Name' in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]['Manufacturer Name'] == 'LIVOLO'):
        self.log.logging('Input', 'Debug', 'Decode0100 - (Livolo) Read Attribute Request %s/%s Data %s' % (MsgSrcAddr, MsgSrcEp, MsgData))
        livolo_read_attribute_request(self, Devices, MsgSrcAddr, MsgSrcEp, MsgData[30:32])
        return
    MsgClusterId = MsgData[10:14]
    MsgDirection = MsgData[14:16]
    MsgManufSpec = MsgData[16:18]
    MsgManufCode = MsgData[18:22]
    nbAttribute = MsgData[22:24]
    self.log.logging('Input', 'Debug', 'Decode0100 - Mode: %s NwkId: %s SrcEP: %s DstEp: %s ClusterId: %s Direction: %s ManufSpec: %s ManufCode: %s nbAttribute: %s' % (MsgSqn, MsgSrcAddr, MsgSrcEp, MsgDstEp, MsgClusterId, MsgDirection, MsgManufSpec, MsgManufCode, nbAttribute))
    updSQN(self, MsgSrcAddr, MsgSqn)
    manuf = manuf_name = ''
    if 'Manufacturer Name' in self.ListOfDevices[MsgSrcAddr]:
        manuf_name = self.ListOfDevices[MsgSrcAddr]['Manufacturer Name']
    if 'Manufacturer' in self.ListOfDevices[MsgSrcAddr]:
        manuf = self.ListOfDevices[MsgSrcAddr]['Manufacturer']
    for idx in range(24, len(MsgData), 4):
        Attribute = MsgData[idx:idx + 4]
        if MsgClusterId == '000a':
            self.log.logging('Input', 'Debug', 'Decode0100 - Received Time Server Cluster %s/%s Idx: %s  Attribute: %s' % (MsgSrcAddr, MsgSrcEp, idx, Attribute))
            timeserver_read_attribute_request(self, MsgSqn, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgManufSpec, MsgManufCode, Attribute)
        elif MsgClusterId == '0201' and (manuf == '105e' or manuf_name == 'Schneider' or manuf_name == 'Schneider Electric'):
            wiser_read_attribute_request(self, MsgSrcAddr, MsgSrcEp, MsgSqn, MsgClusterId, Attribute)
            self.log.logging('Schneider', 'Debug', 'Decode0100 - Sqn: %s NwkId: %s SrcEP: %s DstEp: %s ClusterId: %s Direction: %s ManufSpec: %s ManufCode: %s nbAttribute: %s' % (MsgSqn, MsgSrcAddr, MsgSrcEp, MsgDstEp, MsgClusterId, MsgDirection, MsgManufSpec, MsgManufCode, nbAttribute))
        elif MsgClusterId == '0000' and Attribute == 'f000' and (manuf_name in ('1021', 'Legrand')):
            self.log.logging('Legrand', 'Debug', 'Decode0100 - Sqn: %s NwkId: %s SrcEP: %s DstEp: %s ClusterId: %s Direction: %s ManufSpec: %s ManufCode: %s nbAttribute: %s' % (MsgSqn, MsgSrcAddr, MsgSrcEp, MsgDstEp, MsgClusterId, MsgDirection, MsgManufSpec, MsgManufCode, nbAttribute))
            if self.pluginconf.pluginConf['LegrandCompatibilityMode']:
                operation_time = int(time.time() - self.statistics._start)
                self.log.logging('Legrand', 'Debug', '------> Operation time: %s' % operation_time, MsgSrcAddr)
                read_attribute_response(self, MsgSrcAddr, MsgSrcEp, MsgSqn, MsgClusterId, '00', '23', Attribute, '%08x' % operation_time, manuf_code=MsgManufCode)
        elif MsgClusterId == '0000' and Attribute == '0000':
            read_attribute_response(self, MsgSrcAddr, MsgSrcEp, MsgSqn, MsgClusterId, '00', '20', Attribute, '%02x' % 3, manuf_code=MsgManufCode)
        else:
            self.log.logging('Input', 'Log', 'Decode0100 - Read Attribute Request %s/%s Cluster %s Attribute %s' % (MsgSrcAddr, MsgSrcEp, MsgClusterId, Attribute))