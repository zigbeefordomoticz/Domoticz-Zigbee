import Domoticz
import time

from Modules.basicOutputs import mgt_routing_req
from Modules.tools import is_hex

STATUS_CODE = {"00": "Success", "84": "Not Supported (132)"}

STATUS_OF_ROUTE = {
    0x00: "Active (0)",
    0x01: "Discovery underway (1)",
    0x02: "Discovery Failed (2)",
    0x03: "Inactive (3)",
    0x04: "Validation underway (4)",
    0x05: "RESERVED (5)",
    0x06: "RESERVED (6)",
    0x07: "RESERVED (7)",
}


def mgmt_rtg(self, nwkid):
    if "RoutingTable" not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]["RoutingTable"] = {}
        self.ListOfDevices[nwkid]["RoutingTable"]["Devices"] = []
        self.ListOfDevices[nwkid]["RoutingTable"]["SQN"] = 0
        self.ListOfDevices[nwkid]["RoutingTable"]["TimeStamp"] = time.time()
        mgt_routing_req(self, nwkid, "00")
        return

    if "TimeStamp" not in self.ListOfDevices[nwkid]["RoutingTable"]:
        self.ListOfDevices[nwkid]["RoutingTable"]["TimeStamp"] = time.time()
        mgt_routing_req(self, nwkid, "00")
        return

    if (
        "Status" in self.ListOfDevices[nwkid]["RoutingTable"]
        and self.ListOfDevices[nwkid]["RoutingTable"]["Status"] != STATUS_CODE["00"]
    ):
        return

    feq = self.pluginconf.pluginConf["RoutingTableRequestFeq"]
    if time.time() > self.ListOfDevices[nwkid]["RoutingTable"]["TimeStamp"] + feq:
        mgt_routing_req(self, nwkid, "00")
        return


def mgmt_rtg_rsp(
    self,
    srcnwkid,
    MsgSourcePoint,
    MsgClusterID,
    dstnwkid,
    MsgDestPoint,
    MsgPayload,
):

    if len(MsgPayload) < 10:
        Domoticz.Log("mgmt_rtg_rsp - Short message receive - NwkId: %s Ep: %s Cluster: %s Target: %s Ep: %s Payload: %s" %(
        srcnwkid,
        MsgSourcePoint,
        MsgClusterID,
        dstnwkid,
        MsgDestPoint,
        MsgPayload,   
        ))
        return


    # Domoticz.Log("mgmt_rtg_rsp - len: %s Data: %s" % (len(MsgPayload), MsgPayload))
    Sqn = MsgPayload[0:2]
    Status = MsgPayload[2:4]
    RoutingTableSize = MsgPayload[4:6]
    RoutingTableIndex = MsgPayload[6:8]
    RoutingTableListCount = MsgPayload[8:10]
    RoutingTableListRecord = MsgPayload[10:]            

    if "RoutingTable" not in self.ListOfDevices[srcnwkid]:
        self.ListOfDevices[srcnwkid]["RoutingTable"] = {}
        self.ListOfDevices[srcnwkid]["RoutingTable"]["Devices"] = []
        self.ListOfDevices[srcnwkid]["RoutingTable"]["SQN"] = 0

    if RoutingTableIndex == "00":
        self.ListOfDevices[srcnwkid]["RoutingTable"]["Devices"] = []

    self.ListOfDevices[srcnwkid]["RoutingTable"]["TimeStamp"] = time.time()
    self.ListOfDevices[srcnwkid]["RoutingTable"]["RoutingTableSize"] = int(RoutingTableSize, 16)
    if Status in STATUS_CODE:
        self.ListOfDevices[srcnwkid]["RoutingTable"]["Status"] = STATUS_CODE[Status]
    else:
        self.ListOfDevices[srcnwkid]["RoutingTable"]["Status"] = Status

    # Domoticz.Log("mgmt_rtg_rsp %s/%s Status: %s RoutingTableSize: %s RoutingTableIndex: %s RoutingTableIndex: %s RoutingTableListCount: %s" %(
    #    srcnwkid, MsgSourcePoint, Status, RoutingTableSize, RoutingTableIndex, RoutingTableIndex, RoutingTableListCount ))

    if Status != "00":
        return
    idx = 0
    if len(RoutingTableListRecord) % 10 != 0:
        # Domoticz.Log("Incorrect lenght RoutingListRecord: %s" %RoutingTableListRecord)
        return
    while idx < len(RoutingTableListRecord):

        target_nwkid = RoutingTableListRecord[idx + 2 : idx + 4] + RoutingTableListRecord[idx : idx + 2]
        target_bitfields = RoutingTableListRecord[idx + 4 : idx + 6]
        next_hop = RoutingTableListRecord[idx + 8 : idx + 10] + RoutingTableListRecord[idx + 6 : idx + 8]
        idx += 10

        device_status = int(target_bitfields, 16) & 0b00000111
        device_memory_constraint = (int(target_bitfields, 16) & 0b00001000) >> 3
        many_to_one = (int(target_bitfields, 16) & 0b00010000) >> 4
        route_record_required = (int(target_bitfields, 16) & 0b00100000) >> 5

        routing_record = {}
        routing_record[target_nwkid] = {}
        if device_status in STATUS_OF_ROUTE:
            routing_record[target_nwkid]["Status"] = STATUS_OF_ROUTE[device_status]
        else:
            routing_record[target_nwkid]["Status"] = "Unknown (%s)" % device_status
        routing_record[target_nwkid]["MemoryConstrained"] = device_memory_constraint
        routing_record[target_nwkid]["ManyToOne"] = many_to_one
        routing_record[target_nwkid]["RouteRecordRequired"] = route_record_required
        routing_record[target_nwkid]["NextHopNwkId"] = next_hop

        self.ListOfDevices[srcnwkid]["RoutingTable"]["Devices"].append(routing_record)

        # Domoticz.Log("------------ Destination Address: %s Status: %s Memory Constrained: %s Many-to-one: %s Route record required: %s Next-hop address: %s" %(
        #    target_nwkid, device_status, device_memory_constraint, many_to_one, route_record_required, next_hop ))

    if int(RoutingTableIndex, 16) + int(RoutingTableListCount, 16) < int(RoutingTableSize, 16):
        # Domoticz.Log("------------  - Next Index for %s RoutingTableIndex: %s RoutingTableListCount: %s RoutingTableSize: %s" %(
        #    (srcnwkid, RoutingTableIndex,RoutingTableListCount, RoutingTableSize )))
        mgt_routing_req(self, srcnwkid, "%02x" % (int(RoutingTableIndex, 16) + int(RoutingTableListCount, 16)))
