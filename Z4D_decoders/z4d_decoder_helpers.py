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


def scan_attribute_reponse(self, Devices, MsgSQN, i_sqn, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgData, msgtype):

    self.log.logging(
        "Input",
        "Debug",
        "scan_attribute_reponse - Sqn: %s i_sqn: %s Nwkid: %s Ep: %s Cluster: %s MsgData: %s Type: %s"
        % (
            MsgSQN, i_sqn, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgData, msgtype
        ),
        MsgSrcAddr,
    )

    idx = 12
    while idx < len(MsgData):
        MsgAttrID = MsgAttStatus = MsgAttType = MsgAttSize = MsgClusterData = ""
        MsgAttrID = MsgData[idx : idx + 4]
        idx += 4
        MsgAttStatus = MsgData[idx : idx + 2]
        idx += 2
        if MsgAttStatus == "00":
            MsgAttType = MsgData[idx : idx + 2]
            idx += 2
            MsgAttSize = MsgData[idx : idx + 4]
            idx += 4
            size = int(MsgAttSize, 16) * 2
            if size > 0:
                MsgClusterData = MsgData[idx : idx + size]
                idx += size
        else:
            self.log.logging(
                "Input",
                "Debug",
                "scan_attribute_reponse - %s idx: %s Read Attribute Response: [%s:%s] status: %s -> %s"
                % (msgtype, idx, MsgSrcAddr, MsgSrcEp, MsgAttStatus, MsgData[idx:]),
            )

            # If the frame is coming from firmware we get only one attribute at a time, with some dumy datas
            if len(MsgData[idx:]) == 6:
                # crap, lets finish it
                # Domoticz.Log("Crap Data: %s len: %s" %(MsgData[idx:], len(MsgData[idx:])))
                idx += 6
        self.log.logging( "Input", "Debug", "scan_attribute_reponse - %s idx: %s Read Attribute Response: [%s:%s] ClusterID: %s MsgSQN: %s, i_sqn: %s, AttributeID: %s Status: %s Type: %s Size: %s ClusterData: >%s<" % (
            msgtype, idx, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgSQN, i_sqn, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData, ), MsgSrcAddr, )
        read_report_attributes( self, Devices, msgtype, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData, )


def read_report_attributes( self, Devices, MsgType, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttStatus, MsgAttType, MsgAttSize, MsgClusterData, ):

    if DeviceExist(self, Devices, MsgSrcAddr):
        debug_LQI(self, MsgSrcAddr, MsgClusterId, MsgAttrID, MsgClusterData, MsgSrcEp)

        self.log.logging(
            "Input",
            "Debug2",
            "Decode8102: Attribute Report from "
            + str(MsgSrcAddr)
            + " SQN = "
            + str(MsgSQN)
            + " ClusterID = "
            + str(MsgClusterId)
            + " AttrID = "
            + str(MsgAttrID)
            + " Attribute Data = "
            + str(MsgClusterData),
            MsgSrcAddr,
        )

        if "Health" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Health"] not in ( "Disabled",):
            self.ListOfDevices[MsgSrcAddr]["Health"] = "Live"

        updSQN(self, MsgSrcAddr, str(MsgSQN))
        lastSeenUpdate(self, Devices, NwkId=MsgSrcAddr)

        ReadCluster(
            self,
            Devices,
            MsgType,
            MsgSQN,
            MsgSrcAddr,
            MsgSrcEp,
            MsgClusterId,
            MsgAttrID,
            MsgAttStatus,
            MsgAttType,
            MsgAttSize,
            MsgClusterData,
            Source=MsgType,
        )
        return
    # Device not found, let's try to find it, or trigger a scan
    handle_unknow_device( self, MsgSrcAddr)

   
    
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
