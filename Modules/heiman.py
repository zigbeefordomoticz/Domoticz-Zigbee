



from Modules.domoMaj import MajDomoDevice



def heimanReadRawAPS(self, Devices, nwkId, srcEp, clusterId, targetNwkId, targetEp, payLoad):

    if nwkId not in self.ListOfDevices:
        return

    self.log.logging( "Heiman", "Debug", "heimanReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, Payload: %s" % (
        nwkId, srcEp, clusterId, payLoad), nwkId, )

    if clusterId == "fc80":
        # Heiman Specific Scenes Controller
        # 050b1218f3 Go Out
        # 050b1217f2 Sleep
        # 050b1215f1 Home 
        # 050b1207f0 Movie/Theatre

        command = payLoad[8:10]
        
    self.log.logging( "Heiman", "Debug", "heimanReadRawAPS - Nwkid: %s Ep: %s, command found: %s" % (
        nwkId, srcEp, command), nwkId, )

    if int(command, 16) in {0xF0, 0xF1, 0xF2, 0xF3, 0xF4}:
        self.log.logging( "Heiman", "Debug", "heimanReadRawAPS - Nwkid: %s Ep: %s, command found: %s UNKNOW" % (
            nwkId, srcEp, command), nwkId, )
        MajDomoDevice(self, Devices, nwkId, "01", "fc80", int(command,16))
    else:
        self.log.logging( "Heiman", "Error", "heimanReadRawAPS - Nwkid: %s Ep: %s, command found: %s UNKNOW" % (
            nwkId, srcEp, command), nwkId, )
 