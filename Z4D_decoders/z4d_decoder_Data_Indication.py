from Modules.callback import callbackDeviceAwake
from Modules.domoTools import lastSeenUpdate
from Modules.inRawAps import inRawAps
from Modules.tools import (retreive_cmd_payload_from_8002, timeStamped, updLQI,
                           updSQN)
from Modules.zb_tables_management import mgmt_rtg_rsp
from Modules.zigateConsts import ADDRESS_MODE, ZIGBEE_COMMAND_IDENTIFIER
from Z4D_decoders.z4d_decoder_Remotes import Decode80A7


def Decode8002(self, Devices, MsgData, MsgLQI):
    if len(MsgData) < 22:
        self.log.logging('Input', 'Error', 'Invalid frame %s too short' % MsgData)
        return
    
    MsgProfilID = MsgData[2:6]
    MsgClusterID = MsgData[6:10]
    MsgSourcePoint = MsgData[10:12]
    MsgDestPoint = MsgData[12:14]
    MsgSourceAddressMode = MsgData[14:16]
    
    if int(MsgSourceAddressMode, 16) in [ADDRESS_MODE['short'], ADDRESS_MODE['group']]:
        MsgSourceAddress = MsgData[16:20]
        MsgDestinationAddressMode = MsgData[20:22]
        
        if int(MsgDestinationAddressMode, 16) in [ADDRESS_MODE['short'], ADDRESS_MODE['group']]:
            if len(MsgData) < 26:
                self.log.logging('Input', 'Error', 'Invalid frame %s too short' % MsgData)
                return
            
            MsgDestinationAddress = MsgData[22:26]
            MsgPayload = MsgData[26:]
            
        elif int(MsgDestinationAddressMode, 16) == ADDRESS_MODE['ieee']:
            if len(MsgData) < 38:
                self.log.logging('Input', 'Error', 'Invalid frame %s too short' % MsgData)
                return
            
            MsgDestinationAddress = MsgData[22:38]
            MsgPayload = MsgData[38:]
            
        else:
            self.log.logging('Input', 'Log', 'Decode8002 - Unexpected Destination ADDR_MOD: %s, drop packet %s' % (MsgDestinationAddressMode, MsgData))
            return
        
    elif int(MsgSourceAddressMode, 16) == ADDRESS_MODE['ieee']:
        if len(MsgData) < 38:
            self.log.logging('Input', 'Error', 'Invalid frame %s too short' % MsgData)
            return
        
        MsgSourceAddress = MsgData[16:32]
        MsgDestinationAddressMode = MsgData[32:34]
        if int(MsgDestinationAddressMode, 16) in [ADDRESS_MODE['short'], ADDRESS_MODE['group']]:
            MsgDestinationAddress = MsgData[34:38]
            MsgPayload = MsgData[38:]
            
        elif int(MsgDestinationAddressMode, 16) == ADDRESS_MODE['ieee']:
            if len(MsgData) < 40:
                self.log.logging('Input', 'Error', 'Invalid frame %s too short' % MsgData)
                return
            
            MsgDestinationAddress = MsgData[34:40]
            MsgPayload = MsgData[40:]
            
        else:
            self.log.logging('Input', 'Log', 'Decode8002 - Unexpected Destination ADDR_MOD: %s, drop packet %s' % (MsgDestinationAddressMode, MsgData))
            return
        
    else:
        self.log.logging('Input', 'Log', 'Decode8002 - Unexpected Source ADDR_MOD: %s, drop packet %s' % (MsgSourceAddressMode, MsgData))
        return
    
    if len(MsgPayload) < 4:
        self.log.logging('Input', 'Error', 'Invalid frame %s, Payload %s too short' % (MsgData, MsgPayload))
        return
    
    self.log.logging('Input', 'Debug', 'Reception Data indication, Source Address: ' + MsgSourceAddress + ' Destination Address: ' + MsgDestinationAddress + ' ProfilID: ' + MsgProfilID + ' ClusterID: ' + MsgClusterID + ' Message Payload: ' + MsgPayload, MsgSourceAddress)
    srcnwkid = dstnwkid = None
    
    if len(MsgDestinationAddress) != 4:
        self.log.logging('Input', 'Error', 'not handling IEEE address')
        return
    
    srcnwkid = MsgSourceAddress
    dstnwkid = MsgDestinationAddress
    if srcnwkid not in self.ListOfDevices:
        self.log.logging('Input', 'Debug', 'Decode8002 - Unknown NwkId: %s Ep: %s Cluster: %s Payload: %s' % (srcnwkid, MsgSourcePoint, MsgClusterID, MsgPayload))
        return
    
    timeStamped(self, srcnwkid, 32770)
    lastSeenUpdate(self, Devices, NwkId=srcnwkid)
    updLQI(self, srcnwkid, MsgLQI)
    if MsgClusterID in ('8032', '8033'):
        mgmt_rtg_rsp(self, srcnwkid, MsgSourcePoint, MsgClusterID, dstnwkid, MsgDestPoint, MsgPayload)
        return
    
    if MsgProfilID != '0104':
        self.log.logging('inRawAPS', 'Debug', 'Decode8002 - NwkId: %s Ep: %s Cluster: %s Payload: %s' % (srcnwkid, MsgSourcePoint, MsgClusterID, MsgPayload), srcnwkid)
        return
    
    (default_response, GlobalCommand, Sqn, ManufacturerCode, Command, Data) = retreive_cmd_payload_from_8002(MsgPayload)
    if 'SQN' in self.ListOfDevices[srcnwkid] and Sqn == self.ListOfDevices[srcnwkid]['SQN']:
        self.log.logging('inRawAPS', 'Debug', 'Decode8002 - Duplicate message drop NwkId: %s Ep: %s Cluster: %s GlobalCommand: %5s Command: %s Data: %s' % (srcnwkid, MsgSourcePoint, MsgClusterID, GlobalCommand, Command, Data), srcnwkid)
        return
    
    updSQN(self, srcnwkid, Sqn)
    if GlobalCommand and int(Command, 16) in ZIGBEE_COMMAND_IDENTIFIER:
        self.log.logging('inRawAPS', 'Debug', 'Decode8002 - NwkId: %s Ep: %s Cluster: %s GlobalCommand: %5s Command: %s (%33s) Data: %s' % (srcnwkid, MsgSourcePoint, MsgClusterID, GlobalCommand, Command, ZIGBEE_COMMAND_IDENTIFIER[int(Command, 16)], Data), srcnwkid)
        
    else:
        self.log.logging('inRawAPS', 'Debug', 'Decode8002 - NwkId: %s Ep: %s Cluster: %s GlobalCommand: %5s Command: %s Data: %s' % (srcnwkid, MsgSourcePoint, MsgClusterID, GlobalCommand, Command, Data), srcnwkid)
        
    updLQI(self, srcnwkid, MsgLQI)
    
    if MsgClusterID == '0005' and MsgPayload[:2] == '05':
        cmd = MsgPayload[8:10]
        direction = MsgPayload[10:12]
        data = Sqn + MsgSourcePoint + MsgClusterID + cmd + direction + '000000' + srcnwkid
        self.log.logging('inRawAPS', 'Debug', 'Decode8002 - Sqn: %s NwkId %s Ep %s Cluster %s Cmd %s Direction %s' % (Sqn, srcnwkid, MsgClusterID, MsgClusterID, cmd, direction), srcnwkid)
        Decode80A7(self, Devices, data, MsgLQI)
        return
    
    if 'Manufacturer' not in self.ListOfDevices[srcnwkid] and 'Manufacturer Name' not in self.ListOfDevices[srcnwkid]:
        return
    
    if 'Manufacturer' in self.ListOfDevices[srcnwkid] and self.ListOfDevices[srcnwkid]['Manufacturer'] in ('', {}) and ('Manufacturer Name' in self.ListOfDevices[srcnwkid]) and (self.ListOfDevices[srcnwkid]['Manufacturer Name'] in ('', {})):
        return
    
    inRawAps(self, Devices, srcnwkid, MsgSourcePoint, MsgClusterID, dstnwkid, MsgDestPoint, Sqn, GlobalCommand, ManufacturerCode, Command, Data, MsgPayload)
    callbackDeviceAwake(self, Devices, srcnwkid, MsgSourcePoint, MsgClusterID)