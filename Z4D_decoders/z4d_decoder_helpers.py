from Modules.pluginDbAttributes import STORE_CONFIGURE_REPORTING
from Zigbee.zdpCommands import zdp_NWK_address_request


def extract_message_infos(self, data):
    frame_start = data[:2]
    frame_stop = data[len(data) - 2:]

    if frame_start != "01" and frame_stop != "03":
        self.log.logging("Input", "Error", f"ZigateRead received a non-zigate frame Data: {data} FS/FS = {frame_start}/{frame_stop}")
        return None, None, None

    msg_type = data[2:6].lower()

    if len(data) > 12:
        # We have Payload: data + rssi
        msg_data = data[12: -4]
        msg_lqi = data[-4: -2]
    else:
        msg_data = ""
        msg_lqi = "00"

    return msg_type, msg_data, msg_lqi


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
            self.log.logging( "Input", "Log", "Receive NACK from %s (%s) clusterId: %s Status: %s" % (
                self.ListOfDevices[MsgSrcAddr]["ZDeviceName"], MsgSrcAddr, MsgClusterId, Status, ), MsgSrcAddr, )
        else:
            self.log.logging( "Input", "Log", "Receive NACK from %s clusterId: %s Status: %s" % (
                MsgSrcAddr, MsgClusterId, Status), MsgSrcAddr, )

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
    

def device_leave_announcement(self, devices, msg_ext_address):
    dev_name = next((device.Name for device in devices.values() if device.DeviceID == msg_ext_address), "")
    self.adminWidgets.updateNotificationWidget(devices, f"Leave indication from {msg_ext_address} for {dev_name}")


def device_reset(self, nwk_id):
    if nwk_id not in self.ListOfDevices:
        return

    attributes_to_reset = ["Bind", STORE_CONFIGURE_REPORTING, "ReadAttributes", "Neighbours", "IAS", "WriteAttributes"]

    for attribute in attributes_to_reset:
        if attribute in self.ListOfDevices[nwk_id]:
            if attribute == "IAS":
                for x in self.ListOfDevices[nwk_id]["Ep"]:
                    for ias_attribute in ["0500", "0502"]:
                        if ias_attribute in self.ListOfDevices[nwk_id]["Ep"][x]:
                            del self.ListOfDevices[nwk_id]["Ep"][x][ias_attribute]
                            self.ListOfDevices[nwk_id]["Ep"][x][ias_attribute] = {}
            del self.ListOfDevices[nwk_id][attribute]

    
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
            self.log.logging( "Input", "Log", "Decode8102 - LQI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)%s" % (
                self.ListOfDevices[MsgSrcAddr]["LQI"], MsgClusterId, MsgAttrID, MsgClusterData, MsgSrcAddr, MsgSrcEp, self.ListOfDevices[MsgSrcAddr]["ZDeviceName"], ), )
        else:
            self.log.logging( "Input", "Log", "Decode8102 - LQI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)" % (
                self.ListOfDevices[MsgSrcAddr]["LQI"], MsgClusterId, MsgAttrID, MsgClusterData, MsgSrcAddr, MsgSrcEp, ), )
    else:
        self.log.logging( "Input", "Debug", "Decode8102 - LQI: %3s Received Cluster:%s Attribute: %4s Value: %4s from (%4s/%2s)" % (
            self.ListOfDevices[MsgSrcAddr]["LQI"], MsgClusterId, MsgAttrID, MsgClusterData, MsgSrcAddr, MsgSrcEp, ), )


def check_duplicate_sqn(self, nwk_id, ep, cluster, sqn):
    """
    This function is useful for checking the uniqueness of sequence numbers associated with specific network devices, 
    ensuring data integrity and preventing duplicates in a network application.
    """
    if "Ep" not in self.ListOfDevices.get(nwk_id, {}) or ep not in self.ListOfDevices[nwk_id]["Ep"]:
        return False
    
    ep_cluster = self.ListOfDevices[nwk_id]["Ep"][ep]
    if cluster not in ep_cluster or not isinstance(ep_cluster[cluster], dict):
        ep_cluster[cluster] = {}

    if "0000" not in ep_cluster[cluster]:
        ep_cluster[cluster]["0000"] = {}

    return sqn != "00" and "SQN" in self.ListOfDevices.get(nwk_id, {}) and sqn == self.ListOfDevices[nwk_id]["SQN"]


def set_health_after_message_received(self, Nwkid):
    device = self.ListOfDevices.get(Nwkid, {})
    
    if "Health" not in device:
        device["Health"] = "Live"
    
    if device.get("Health") == "Disabled":
        return
    
    if device.get("Status") != "inDB":
        device["Status"] = "inDB"
