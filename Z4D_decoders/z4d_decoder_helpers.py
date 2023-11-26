def extract_messge_infos( self, Data):
    FrameStart = Data[:2]
    FrameStop = Data[len(Data) - 2 :]
    if FrameStart != "01" and FrameStop != "03":
        self.log.logging( "Input", "Error", "ZigateRead received a non-zigate frame Data: " + str(Data) + " FS/FS = " + str(FrameStart) + "/" + str(FrameStop))
        return None, None, None
    MsgType = Data[2:6]
    MsgType = MsgType.lower()
    #MsgLength = Data[6:10]
    #MsgCRC = Data[10:12]
    if len(Data) > 12:
        # We have Payload: data + rssi
        MsgData = Data[12 : len(Data) - 4]
        MsgLQI = Data[len(Data) - 4 : len(Data) - 2]
    else:
        MsgData = ""
        MsgLQI = "00"
    return MsgType, MsgData, MsgLQI


def set_health_state(self, MsgSrcAddr, ClusterId, Status):

    if "Health" not in self.ListOfDevices[MsgSrcAddr]:
        return
    if self.ListOfDevices[MsgSrcAddr]["Health"] == "Disabled":
        # If the device has been disabled, just drop the message
        return

    if self.ListOfDevices[MsgSrcAddr]["Health"] != "Not Reachable":
        self.ListOfDevices[MsgSrcAddr]["Health"] = "Not Reachable"

    if "ZDeviceName" in self.ListOfDevices[MsgSrcAddr]:
        MsgClusterId = ClusterId
        if self.ListOfDevices[MsgSrcAddr]["ZDeviceName"] not in [
            {},
            "",
        ]:
            self.log.logging(
                "Input",
                "Log",
                "Receive NACK from %s (%s) clusterId: %s Status: %s"
                % ( self.ListOfDevices[MsgSrcAddr]["ZDeviceName"], MsgSrcAddr, MsgClusterId, Status, ),
                MsgSrcAddr,
            )
        else:
            self.log.logging(
                "Input",
                "Log",
                "Receive NACK from %s clusterId: %s Status: %s" % (MsgSrcAddr, MsgClusterId, Status),
                MsgSrcAddr,
            )

    if self.pluginconf.pluginConf["deviceOffWhenTimeOut"]:
        for x in self.ListOfDevices[MsgSrcAddr]["Ep"]:
            if (
                "0006" in self.ListOfDevices[MsgSrcAddr]["Ep"][x]
                and "0000" in self.ListOfDevices[MsgSrcAddr]["Ep"][x]["0006"]
            ):
                self.ListOfDevices[MsgSrcAddr]["Ep"][x]["0006"]["0000"] = "00"



def Network_Address_response_request_next_index(self, nwkid, ieee, index, ActualDevicesListed):
    new_index = "%02x" %( index + ActualDevicesListed )
    self.log.logging("Input", "Debug", "          Network_Address_response_request_next_index - %s Index: %s" %( nwkid, new_index))
    zdp_NWK_address_request(self, nwkid, ieee, u8RequestType="01", u8StartIndex=new_index)
    

def device_leave_annoucement(self, Devices, MsgExtAddress):
    devName = ""
    for x in Devices:
        if Devices[x].DeviceID == MsgExtAddress:
            devName = Devices[x].Name
            break
    self.adminWidgets.updateNotificationWidget(Devices, "Leave indication from %s for %s " % (MsgExtAddress, devName))



def device_reset( self, NwkId ):
    if NwkId not in self.ListOfDevices:
        return
    
    if "Bind" in self.ListOfDevices[NwkId]:
            del self.ListOfDevices[NwkId]["Bind"]
    if STORE_CONFIGURE_REPORTING in self.ListOfDevices[NwkId]:
        del self.ListOfDevices[NwkId][STORE_CONFIGURE_REPORTING]
    if "ReadAttributes" in self.ListOfDevices[NwkId]:
        del self.ListOfDevices[NwkId]["ReadAttributes"]
    if "Neighbours" in self.ListOfDevices[NwkId]:
        del self.ListOfDevices[NwkId]["Neighbours"]
    if "IAS" in self.ListOfDevices[NwkId]:
        del self.ListOfDevices[NwkId]["IAS"]
        for x in self.ListOfDevices[NwkId]["Ep"]:
            if "0500" in self.ListOfDevices[NwkId]["Ep"][ x ]:
                del self.ListOfDevices[NwkId]["Ep"][ x ]["0500"]
                self.ListOfDevices[NwkId]["Ep"][ x ]["0500"] = {}
            if "0502" in self.ListOfDevices[NwkId]["Ep"][ x ]:
                del self.ListOfDevices[NwkId]["Ep"][ x ]["0502"]
                self.ListOfDevices[NwkId]["Ep"][ x ]["0502"] = {}

    if "WriteAttributes" in self.ListOfDevices[NwkId]:
        del self.ListOfDevices[NwkId]["WriteAttributes"]




   
    
def isZDeviceName(self, MsgSrcAddr):

    return "ZDeviceName" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["ZDeviceName"] not in [
        "",
        {},
    ]


def debug_LQI(self, MsgSrcAddr, MsgClusterId, MsgAttrID, MsgClusterData, MsgSrcEp):
    if (
        self.pluginconf.pluginConf["LQIthreshold"]
        and self.ListOfDevices[MsgSrcAddr]["LQI"] <= self.pluginconf.pluginConf["LQIthreshold"]
    ):
        if isZDeviceName(self, MsgSrcAddr):
            self.log.logging(
                "Input",
                "Log",
                "Decode8102 - LQI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)%s"
                % (
                    self.ListOfDevices[MsgSrcAddr]["LQI"],
                    MsgClusterId,
                    MsgAttrID,
                    MsgClusterData,
                    MsgSrcAddr,
                    MsgSrcEp,
                    self.ListOfDevices[MsgSrcAddr]["ZDeviceName"],
                ),
            )
        else:
            self.log.logging(
                "Input",
                "Log",
                "Decode8102 - LQI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)"
                % (
                    self.ListOfDevices[MsgSrcAddr]["LQI"],
                    MsgClusterId,
                    MsgAttrID,
                    MsgClusterData,
                    MsgSrcAddr,
                    MsgSrcEp,
                ),
            )
    else:
        self.log.logging(
            "Input",
            "Debug",
            "Decode8102 - LQI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)"
            % (
                self.ListOfDevices[MsgSrcAddr]["LQI"],
                MsgClusterId,
                MsgAttrID,
                MsgClusterData,
                MsgSrcAddr,
                MsgSrcEp,
            ),
        )

def check_duplicate_sqn(self, Nwkid, Ep, Cluster, Sqn):
    """
    This function is useful for checking the uniqueness of sequence numbers associated with specific network devices, 
    ensuring data integrity and preventing duplicates in a network application.
    """
    
    if "Ep" not in self.ListOfDevices[Nwkid] or Ep not in self.ListOfDevices[Nwkid]["Ep"]:
        return False
    
    EpCluster = self.ListOfDevices[Nwkid]["Ep"][Ep]
    if Cluster not in EpCluster:
        EpCluster[Cluster] = {}
    elif not isinstance(EpCluster[Cluster], dict):
        EpCluster[Cluster] = {}

    if "0000" not in EpCluster[Cluster]:
        EpCluster[Cluster]["0000"] = {}

    return Sqn != "00" and "SQN" in self.ListOfDevices[Nwkid] and Sqn == self.ListOfDevices[Nwkid]["SQN"]
