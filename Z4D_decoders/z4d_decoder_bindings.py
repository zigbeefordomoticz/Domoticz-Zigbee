def Decode8030(self, Devices, MsgData, MsgLQI):
    MsgLen = len(MsgData)
    self.log.logging('Input', 'Debug', 'Decode8030 - Msgdata: %s, MsgLen: %s' % (MsgData, MsgLen))
    MsgSequenceNumber = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    if MsgLen < 10:
        return
    MsgSrcAddrMode = MsgData[4:6]
    if int(MsgSrcAddrMode, 16) == ADDRESS_MODE['short']:
        MsgSrcAddr = MsgData[6:10]
        nwkid = MsgSrcAddr
        self.log.logging('Input', 'Debug', 'Decode8030 - Bind reponse for %s' % MsgSrcAddr, MsgSrcAddr)
    elif int(MsgSrcAddrMode, 16) == ADDRESS_MODE['ieee']:
        MsgSrcAddr = MsgData[6:14]
        self.log.logging('Input', 'Debug', 'Decode8030 - Bind reponse for %s' % MsgSrcAddr)
        if MsgSrcAddr not in self.IEEE2NWK:
            self.log.logging('Input', 'Error', 'Decode8030 - Do no find %s in IEEE2NWK' % MsgSrcAddr)
            return
        nwkid = self.IEEE2NWK[MsgSrcAddr]
    elif int(MsgSrcAddrMode, 16) == 0:
        MsgSrcAddr = MsgData[8:12]
        nwkid = MsgSrcAddr
    else:
        self.log.logging('Input', 'Error', 'Decode8030 - Unknown addr mode %s in %s' % (MsgSrcAddrMode, MsgData))
        return
    i_sqn = sqn_get_internal_sqn_from_app_sqn(self.ControllerLink, MsgSequenceNumber, TYPE_APP_ZDP)
    self.log.logging('Input', 'Debug', 'Decode8030 - Bind response, Device: %s Status: %s MsgSequenceNumber: 0x%s/%3s i_sqn: %s' % (MsgSrcAddr, MsgDataStatus, MsgSequenceNumber, int(MsgSequenceNumber, 16), i_sqn), MsgSrcAddr)
    if nwkid in self.ListOfDevices:
        if 'Bind' in self.ListOfDevices[nwkid]:
            for Ep in list(self.ListOfDevices[nwkid]['Bind']):
                if Ep not in self.ListOfDevices[nwkid]['Ep']:
                    self.log.logging('Input', 'Error', 'Decode8030 --> %s Found an inconstitent Ep: %s in %s' % (nwkid, Ep, str(self.ListOfDevices[nwkid]['Bind'])))
                    del self.ListOfDevices[nwkid]['Bind'][Ep]
                    continue
                for cluster in list(self.ListOfDevices[nwkid]['Bind'][Ep]):
                    if self.ListOfDevices[nwkid]['Bind'][Ep][cluster]['Phase'] == 'requested' and 'i_sqn' in self.ListOfDevices[nwkid]['Bind'][Ep][cluster] and (self.ListOfDevices[nwkid]['Bind'][Ep][cluster]['i_sqn'] == i_sqn):
                        self.log.logging('Input', 'Debug', 'Decode8030 - Set bind request to binded: nwkid %s ep: %s cluster: %s' % (nwkid, Ep, cluster), MsgSrcAddr)
                        self.ListOfDevices[nwkid]['Bind'][Ep][cluster]['Stamp'] = int(time.time())
                        self.ListOfDevices[nwkid]['Bind'][Ep][cluster]['Phase'] = 'binded'
                        self.ListOfDevices[nwkid]['Bind'][Ep][cluster]['Status'] = MsgDataStatus
                        return
        if 'WebBind' in self.ListOfDevices[nwkid]:
            for Ep in list(self.ListOfDevices[nwkid]['WebBind']):
                if Ep not in self.ListOfDevices[nwkid]['Ep']:
                    self.log.logging('Input', 'Error', 'Decode8030 --> %s Found an inconstitent Ep: %s in %s' % (nwkid, Ep, str(self.ListOfDevices[nwkid]['WebBind'])))
                    del self.ListOfDevices[nwkid]['WebBind'][Ep]
                    continue
                for cluster in list(self.ListOfDevices[nwkid]['WebBind'][Ep]):
                    for destNwkid in list(self.ListOfDevices[nwkid]['WebBind'][Ep][cluster]):
                        if destNwkid in ('Stamp', 'Target', 'TargetIEEE', 'SourceIEEE', 'TargetEp', 'Phase', 'Status'):
                            self.log.logging('Input', 'Error', '---> delete  destNwkid: %s' % destNwkid)
                            del self.ListOfDevices[nwkid]['WebBind'][Ep][cluster][destNwkid]
                        if self.ListOfDevices[nwkid]['WebBind'][Ep][cluster][destNwkid]['Phase'] == 'requested' and 'i_sqn' in self.ListOfDevices[nwkid]['WebBind'][Ep][cluster][destNwkid] and (self.ListOfDevices[nwkid]['WebBind'][Ep][cluster][destNwkid]['i_sqn'] == i_sqn):
                            self.log.logging('Input', 'Debug', 'Decode8030 - Set WebBind request to binded: nwkid %s ep: %s cluster: %s destNwkid: %s' % (nwkid, Ep, cluster, destNwkid), MsgSrcAddr)
                            self.ListOfDevices[nwkid]['WebBind'][Ep][cluster][destNwkid]['Stamp'] = int(time.time())
                            self.ListOfDevices[nwkid]['WebBind'][Ep][cluster][destNwkid]['Phase'] = 'binded'
                            self.ListOfDevices[nwkid]['WebBind'][Ep][cluster][destNwkid]['Status'] = MsgDataStatus
                            returndef Decode8031(self, Devices, MsgData, MsgLQI):
    MsgLen = len(MsgData)
    self.log.logging('Input', 'Debug', 'Decode8031 - Msgdata: %s' % MsgData)
    MsgSequenceNumber = MsgData[:2]
    MsgDataStatus = MsgData[2:4]
    if MsgLen < 10:
        return
    MsgSrcAddrMode = MsgData[4:6]
    if int(MsgSrcAddrMode, 16) == ADDRESS_MODE['short']:
        MsgSrcAddr = MsgData[6:10]
        nwkid = MsgSrcAddr
        self.log.logging('Input', 'Debug', 'Decode8031 - UnBind reponse for %s' % nwkid, nwkid)
    elif int(MsgSrcAddrMode, 16) == ADDRESS_MODE['ieee']:
        MsgSrcAddr = MsgData[6:14]
        self.log.logging('Input', 'Debug', 'Decode8031 - UnBind reponse for %s' % MsgSrcAddr)
        if MsgSrcAddr in self.IEEE2NWK:
            nwkid = self.IEEE2NWK[MsgSrcAddr]
            self.log.logging('Input', 'Error', 'Decode8031 - Do no find %s in IEEE2NWK' % MsgSrcAddr)
    else:
        self.log.logging('Input', 'Error', 'Decode8031 - Unknown addr mode %s in %s' % (MsgSrcAddrMode, MsgData))
        return
    self.log.logging('Input', 'Debug', 'Decode8031 - UnBind response, Device: %s SQN: %s Status: %s' % (MsgSrcAddr, MsgSequenceNumber, MsgDataStatus), MsgSrcAddr)
    if MsgDataStatus != '00':
        self.log.logging('Input', 'Debug', 'Decode8031 - Unbind response SQN: %s status [%s] - %s' % (MsgSequenceNumber, MsgDataStatus, DisplayStatusCode(MsgDataStatus)), MsgSrcAddr)