#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
"""
    Module: mgmt_rtpg.py
 
    Description: 

"""


from sqlite3 import Timestamp
import struct
import time
from datetime import datetime

import Domoticz

from Modules.basicOutputs import mgt_binding_table_req, mgt_routing_req
from Modules.tools import get_device_nickname

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

TABLE_TO_REPORT = {
    "RoutingTable": mgt_routing_req,
    "BindingTable": mgt_binding_table_req,
}

CLUSTER_TO_TABLE = {
    "8032": "RoutingTable",
    "8033": "BindingTable"
}


def start_new_table_scan(self, nwkid, tablename):

    if tablename not in self.ListOfDevices[nwkid]:
        self.log.logging("NetworkMap", "Debug", "start_new_table_scan not found %s/%s" %(nwkid, tablename))
        self.ListOfDevices[nwkid][tablename] = []
    if not isinstance(self.ListOfDevices[nwkid][tablename], list):
        self.log.logging("NetworkMap", "Debug", "start_new_table_scan not a list, cleanup %s/%s" %( nwkid, tablename))
        del self.ListOfDevices[nwkid][tablename]
        self.ListOfDevices[nwkid][tablename] = []
    table_entry_cleanup( self, nwkid, tablename)
        
    time_stamp = None  
    if "0000" in self.ListOfDevices and "TopologyStartTime" in self.ListOfDevices["0000"]:
        time_stamp = self.ListOfDevices["0000"]["TopologyStartTime"]
        
    self.log.logging("NetworkMap", "Debug", "start_new_table_scan %s/%s/%s" %( nwkid, tablename, time_stamp))
    _create_empty_entry(self, nwkid, tablename, time_stamp)

def table_entry_cleanup( self, nwkid, tablename):
    max_report_per_table = 4
    if "numTopologyReports" in self.pluginconf.pluginConf:
        max_report_per_table = self.pluginconf.pluginConf["numTopologyReports"]

    if len(self.ListOfDevices[nwkid][tablename]) > max_report_per_table:
        how_many_to_remove = len(self.ListOfDevices[nwkid][tablename]) - max_report_per_table
        if how_many_to_remove > 0:
            idx = 0
            while idx != how_many_to_remove:
                self.log.logging("NetworkMap", "Debug", "start_new_table_scan remove older entry %s/%s" %(nwkid, tablename))
                del self.ListOfDevices[nwkid][tablename][0]
                idx += 1

def _create_empty_entry(self, nwkid, tablename, time_stamp=None):

    time_stamp = time_stamp or int(time.time())
    new_entry = {
        "Devices": [], 
        "SQN": 0, 
        "Status": "", 
        "TimeStamp": time_stamp,
        "Time": time_stamp
    }
    if time_stamp:
        for x in self.ListOfDevices[nwkid][tablename]:
            if "TimeStamp" in x and x["TimeStamp"] == time_stamp:
                return

    self.ListOfDevices[nwkid][tablename].append( new_entry )
 
def get_table_entry(self, nwkid, tablename, time_stamp=None):
    
    if time_stamp is None:
        return get_latest_table_entry(self, nwkid, tablename)

    # Need to find timestamp in device Entry
    if tablename not in self.ListOfDevices[nwkid]:
        return []
    if not isinstance(self.ListOfDevices[nwkid][tablename], list):
        return []
    for x in self.ListOfDevices[nwkid][tablename]:
        if x["Time"] == int(time_stamp):
            self.log.logging("NetworkMap", "Debug", "get_table_entry: found Time %s for %s/%s ==> %s" %( time_stamp, nwkid, tablename, str(x)))
            return x.copy()
        
    self.log.logging("NetworkMap", "Debug", "get_table_entry: nothing found  Time %s for %s/%s" %( time_stamp, nwkid, tablename))
    return []
        
def get_device_table_entry(self, nwkid, tablename, time_stamp=None):
    
    table_entry = get_table_entry(self, nwkid, tablename, time_stamp)
    self.log.logging("NetworkMap", "Debug", "get_device_table_entry: %s/%s %s==> %s" %(nwkid, tablename, str(table_entry), time_stamp))
    return table_entry["Devices"] if "Devices" in table_entry else []
    
def get_latest_table_entry(self, nwkid, tablename):
    
    if tablename not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid][tablename] = []
        _create_empty_entry(self, nwkid, tablename)
        
    if not isinstance(self.ListOfDevices[nwkid][tablename], list):
        del self.ListOfDevices[nwkid][tablename]
        self.ListOfDevices[nwkid][tablename] = []
        _create_empty_entry(self, nwkid, tablename)
    
    if len(self.ListOfDevices[nwkid][tablename]) > 0:
        return self.ListOfDevices[nwkid][tablename][(len(self.ListOfDevices[nwkid][tablename] ) - 1)]
    return []

def update_merge_new_device_to_last_entry(self, nwkid, tablename, record ):
    
    new_routing_record = get_latest_table_entry(self, nwkid, tablename)["Devices"]
    if isinstance( record, dict):
        for x in record:
            if x not in new_routing_record:
                new_routing_record.append( { x: record[ x ]} )
        del get_latest_table_entry(self, nwkid, tablename)["Devices"]
        get_latest_table_entry(self, nwkid, tablename)["Devices"] = new_routing_record.copy()
        
    elif isinstance( record, str):
        get_latest_table_entry(self, nwkid, tablename)["Devices"].append( record )
    else:
        self.log.logging("NetworkMap", "Error", "===> unkown ????")

def get_list_of_timestamps( self, nwkid, tablename):
    # We force to retreive ALL timestamps from all Devices with Neigbourgs so cleanip is possible
    timestamp = []
    for tablename in ("RoutingTable", "AssociatedDevices", "Neighbours" ):
        for nwkid in self.ListOfDevices:
            if tablename not in self.ListOfDevices[nwkid]:
                continue

            if not isinstance(self.ListOfDevices[nwkid][tablename], list):
                continue

            for x in self.ListOfDevices[nwkid][tablename]:
                #if isinstance(x["Time"], int) and not is_timestamp_current_topology_in_progress(self, x["Time"]):
                if isinstance(x["Time"], int) and int(x["Time"]) not in timestamp and not is_timestamp_current_topology_in_progress(self, x["Time"]):
                    timestamp.append( int(x["Time"]))

    self.log.logging("NetworkMap", "Debug", "get_list_of_timestamps_Table return --> %s -> %s" %(tablename, timestamp))
    return timestamp


def is_timestamp_current_topology_in_progress( self, timestamp=None):
    if timestamp:
        return "TopologyStartTime" in self.ListOfDevices["0000"] and self.ListOfDevices["0000"]["TopologyStartTime"] == timestamp
    if "TopologyStartTime" in self.ListOfDevices["0000"]:
        return self.ListOfDevices["0000"]["TopologyStartTime"]
    
def remove_entry_from_all_tables( self, time_stamp ):

    if "TopologyStartTime" in self.ListOfDevices["0000"]:
        self.log.logging("NetworkMap", "Error", "remove_entry_from_all_tables cannot remove table while a scan is in progress")
        return
   
    for x in self.ListOfDevices:
        for table in ( "Neighbours", "AssociatedDevices", "RoutingTable"):
            if table in self.ListOfDevices[ x ]:
                remove_table_entry(self, x, table, time_stamp)

    
def remove_table_entry(self, nwkid, tablename, time_stamp):
    
    self.log.logging("NetworkMap", "Debug", "remove_table_entry %s %s %s" %(nwkid, tablename, time_stamp))
    self.log.logging("NetworkMap", "Debug", "remove_table_entry %s" %str(self.ListOfDevices[nwkid][tablename]) )

    if not isinstance(self.ListOfDevices[nwkid][tablename], list):
        return
    one_more_time = True
    while one_more_time:
        one_more_time = False
        for idx in range(len(self.ListOfDevices[nwkid][tablename])):
            self.log.logging("NetworkMap", "Debug", "remove_table_entry idx: %s" %idx)
            if ( 
                "Time" in self.ListOfDevices[nwkid][tablename][ idx ]
                and self.ListOfDevices[nwkid][tablename][ idx ]["Time"] == int(time_stamp)
            ):
                self.log.logging("NetworkMap", "Debug", "remove_table_entry %s / %s" %( nwkid, tablename))
                del self.ListOfDevices[nwkid][tablename][ idx ]
                one_more_time = True
                break

 
  
# Routing Table    
def mgmt_rtg(self, nwkid, table):
    
    self.log.logging("NetworkMap", "Debug", "=======> mgmt_rtg: %s %s" %(nwkid, table))
    if nwkid not in self.ListOfDevices:
        return
    
    if (
        table == "BindingTable"
        and "Param" in self.ListOfDevices[nwkid] and "BindingTableRequest" in self.ListOfDevices[nwkid]["Param"]
        and self.ListOfDevices[nwkid]["Param"][ "BindingTableRequest"] == 0
    ):
        return
    
    if table not in TABLE_TO_REPORT:
        self.log.logging("NetworkMap", "Error", "=======> mgmt_rtg: %s %s not found in TABLE_TO_REPORT" %(nwkid, table))
        return

    func = TABLE_TO_REPORT[ table ]
    if table not in self.ListOfDevices[nwkid]:
        # Create a new entry
        start_new_table_scan(self, nwkid, table)
        func(self, nwkid, "00")
        return

    if not get_latest_table_entry(self, nwkid, table):
        # Not yet a Table.add()
        start_new_table_scan(self, nwkid, table)
        func(self, nwkid, "00")
        return

    if "TimeStamp" not in get_latest_table_entry(self, nwkid, table):
        get_latest_table_entry(self, nwkid, table)["TimeStamp"] = time.time()
        func(self, nwkid, "00")
        return

    if (
        "Status" in get_latest_table_entry(self, nwkid, table)
        and get_latest_table_entry(self, nwkid, table)["Status"] not in ( "", STATUS_CODE["00"])
    ):
        return
    
    start_new_table_scan(self, nwkid, table)
    func(self, nwkid, "00")
    return

def mgmt_rtg_rsp( self, srcnwkid, MsgSourcePoint, MsgClusterID, dstnwkid, MsgDestPoint, MsgPayload, ):

    self.log.logging("NetworkMap", "Debug", "mgmt_rtg_rsp - NwkId: %s Ep: %s Cluster: %s Target: %s Ep: %s Payload: %s" %(
        srcnwkid,
        MsgSourcePoint,
        MsgClusterID,
        dstnwkid,
        MsgDestPoint,
        MsgPayload,   
    ))

    if len(MsgPayload) < 10:
        self.log.logging("NetworkMap", "Debug", "mgmt_rtg_rsp - Short message receive - NwkId: %s Ep: %s Cluster: %s Target: %s Ep: %s Payload: %s" %(
            srcnwkid,
            MsgSourcePoint,
            MsgClusterID,
            dstnwkid,
            MsgDestPoint,
            MsgPayload,   
        ))
        return


    if MsgClusterID == "8032":
        mgmt_routingtable_response( self, srcnwkid, MsgSourcePoint, MsgClusterID, dstnwkid, MsgDestPoint, MsgPayload )
    elif MsgClusterID == "8033":
        mgmt_bindingtable_response( self, srcnwkid, MsgSourcePoint, MsgClusterID, dstnwkid, MsgDestPoint, MsgPayload )
    else:
        self.log.logging("NetworkMap", "Error", "mgmt_rtg_rsp - unknown Cluster %s" %MsgClusterID)
        return

def mgmt_routingtable_response( self, srcnwkid, MsgSourcePoint, MsgClusterID, dstnwkid, MsgDestPoint, MsgPayload, ):

    Sqn = MsgPayload[:2]
    Status = MsgPayload[2:4]
    RoutingTableSize = MsgPayload[4:6]
    RoutingTableIndex = MsgPayload[6:8]
    RoutingTableListCount = MsgPayload[8:10]
    RoutingTableListRecord = MsgPayload[10:]     

    self.log.logging("NetworkMap", "Debug", "mgmt_routingtable_response %s - %s %s %s %s %s" %(
        srcnwkid,
        Status,
        RoutingTableSize,
        RoutingTableIndex,
        RoutingTableListCount, 
        RoutingTableListRecord  ,  
    ))
    get_latest_table_entry(self, srcnwkid, "RoutingTable")["TimeStamp"] = time.time()
    get_latest_table_entry(self, srcnwkid, "RoutingTable")[ "RoutingTable" + "TableSize"] = int(RoutingTableSize, 16)
    if Status in STATUS_CODE:
        get_latest_table_entry(self, srcnwkid, "RoutingTable")["Status"] = STATUS_CODE[Status]
    else:
        get_latest_table_entry(self, srcnwkid, "RoutingTable")["Status"] = Status

    if Status != "00":
        return
    if len(RoutingTableListRecord) % 10 != 0:
        return
    for idx in range(0, len(RoutingTableListRecord), 10):
        target_nwkid = RoutingTableListRecord[idx + 2 : idx + 4] + RoutingTableListRecord[idx : idx + 2]
        target_bitfields = RoutingTableListRecord[idx + 4 : idx + 6]
        next_hop = RoutingTableListRecord[idx + 8 : idx + 10] + RoutingTableListRecord[idx + 6 : idx + 8]
        device_status = int(target_bitfields, 16) & 0b00000111
        device_memory_constraint = (int(target_bitfields, 16) & 0b00001000) >> 3
        many_to_one = (int(target_bitfields, 16) & 0b00010000) >> 4
        route_record_required = (int(target_bitfields, 16) & 0b00100000) >> 5

        routing_record = {
            target_nwkid: {
                'Status': STATUS_OF_ROUTE[device_status] if device_status in STATUS_OF_ROUTE else "Unknown (%s)" % device_status
            }
        }
        
        if device_status not in ( 0x02, 0x03, 0x05, 0x06, 0x07):
            routing_record[target_nwkid]["MemoryConstrained"] = device_memory_constraint
            routing_record[target_nwkid]["ManyToOne"] = many_to_one
            routing_record[target_nwkid]["RouteRecordRequired"] = route_record_required
            routing_record[target_nwkid]["NextHopNwkId"] = next_hop
            self.log.logging("NetworkMap", "Debug", "---- new entry: %s" %routing_record)
            update_merge_new_device_to_last_entry(self, srcnwkid, "RoutingTable", routing_record )
        else:
            self.log.logging("NetworkMap", "Debug", "---- drop this entry due to status %s -> %s %s " %( srcnwkid, target_nwkid, device_status))
                
    if int(RoutingTableIndex, 16) + int(RoutingTableListCount, 16) < int(RoutingTableSize, 16):
        self.log.logging("NetworkMap", "Debug", "mgmt_routingtable_response requesting Routing Table for %s Idx %s" %(
            srcnwkid, "%02x" % (int(RoutingTableIndex, 16) + int(RoutingTableListCount, 16))
        ))
        mgt_routing_req(self, srcnwkid, "%02x" % (int(RoutingTableIndex, 16) + int(RoutingTableListCount, 16)))

# Network device Associated
def store_NwkAddr_Associated_Devices( self, nwkid, Index, device_associated_list):
    self.log.logging("NetworkMap", "Debug", "          store_NwkAddr_Associated_Devices - %s %s" %( nwkid, device_associated_list))

    timestamp = is_timestamp_current_topology_in_progress( self)
    
    if Index == 0:
        start_new_table_scan(self, nwkid, "AssociatedDevices")
        
    idx = 0
    while idx < len(device_associated_list):
        device_id = device_associated_list[idx:idx + 4]
        update_merge_new_device_to_last_entry(self, nwkid, "AssociatedDevices", str(device_id) )
        idx += 4
        
        
# Binding Table
def mgtm_binding(self, nwkid, table):

    self.log.logging("NetworkMap", "Debug", "=======> mgtm_binding: %s %s" %(nwkid, table))
    if nwkid not in self.ListOfDevices:
        return

    if table != "BindingTable":
        self.log.logging("NetworkMap", "Error", "=======> mgtm_binding: %s %s not supported !!" %(nwkid, table))
        return

    if "BindingTable" not in self.ListOfDevices[ nwkid ]:
        create_BindTable_structutre( self, nwkid )

    if isinstance( self.ListOfDevices[ nwkid ]["BindingTable"], list):
        create_BindTable_structutre( self, nwkid )

    if (
        "TimeStamp" in self.ListOfDevices[nwkid]["BindingTable"] 
        and self.ListOfDevices[nwkid]["BindingTable"]["TimeStamp"] < ( time.time() + ( 24 * 3600 ))
    ):
        return

    if "Devices" in get_BindTable_entry(self, nwkid):
        del get_BindTable_entry(self, nwkid)["Devices"]
        get_BindTable_entry(self, nwkid)["Devices"] = []
        self.log.logging("NetworkMap", "Debug", "=======> mgtm_binding performing the initial request: %s %s" %(nwkid, table))
    mgt_binding_table_req(self, nwkid, "00")

def create_BindTable_structutre( self, nwkid ):
        self.ListOfDevices[ nwkid ]["BindingTable"] = {
            "SQN": 0,
            "Status": "Requested",
            "TimeStamp": time.time(),
            "BindingTableSize": 0,
            "Devices": []
        }

def get_BindTable_entry(self, nwkid):
    if "BindingTable" not in self.ListOfDevices[ nwkid ]:
        create_BindTable_structutre( self, nwkid )
    if isinstance( self.ListOfDevices[ nwkid ]["BindingTable"], list):
        create_BindTable_structutre( self, nwkid )
    if "Devices" not in self.ListOfDevices[ nwkid ]["BindingTable"]:
        self.ListOfDevices[ nwkid ]["BindingTable"]["Devices"] = []
    return self.ListOfDevices[ nwkid ]["BindingTable"]

def update_merge_new_device_BindinTable(self, nwkid, record ):

    new_routing_record = get_BindTable_entry(self, nwkid)["Devices"]
    if isinstance( record, dict):
        for x in record:
            if x not in new_routing_record:
                new_routing_record.append( { x: record[ x ]} )
        del get_BindTable_entry(self, nwkid)["Devices"]
        get_BindTable_entry(self, nwkid)["Devices"] = new_routing_record.copy()
        
def mgmt_bindingtable_response( self, srcnwkid, MsgSourcePoint, MsgClusterID, dstnwkid, MsgDestPoint, MsgPayload, ):
    
    Sqn = MsgPayload[:2]
    Status = MsgPayload[2:4]
    BindingTableSize = MsgPayload[4:6]
    BindingTableIndex = MsgPayload[6:8]
    BindingTableListCount = MsgPayload[8:10]
    BindingTableListRecord = MsgPayload[10:]

    #Domoticz.Log("mgmt_bindingtable_response for %s on cluster %s: >%s< -%s" %(srcnwkid, MsgClusterID, MsgPayload, len(BindingTableListRecord)))

    get_BindTable_entry(self, srcnwkid)["TimeStamp"] = time.time()
    get_BindTable_entry(self, srcnwkid)[ "BindingTableSize"] = int(BindingTableSize, 16)
    if Status in STATUS_CODE:
        get_BindTable_entry(self, srcnwkid)["Status"] = STATUS_CODE[Status]
    else:
        get_BindTable_entry(self, srcnwkid)["Status"] = Status

    if Status != "00":
        return

    idx = 0
    while idx < len(BindingTableListRecord):
        # Source
        source_ieee = "%016x" %struct.unpack("Q", struct.pack(">Q", int( BindingTableListRecord[ idx: idx +16] , 16)))[0]
        binding_record = {source_ieee: {}}
        idx += 16

        # Source Ep
        source_ep = BindingTableListRecord[ idx : idx +2]
        binding_record[source_ieee]["sourceEp"] = source_ep
        idx += 2

        # Cluster
        cluster = "%04x" %struct.unpack("H", struct.pack(">H", int( BindingTableListRecord[ idx: idx +4] , 16)))[0]
        binding_record[source_ieee]["Cluster"] = cluster
        idx += 4

        # Address mode of Target
        addr_mode = BindingTableListRecord[ idx: idx +2 ]
        idx += 2

        if addr_mode == '03':  # IEEE
            dest_ieee = "%016x" %struct.unpack("Q", struct.pack(">Q", int( BindingTableListRecord[ idx: idx +16] , 16)))[0]
            idx += 16
            binding_record[source_ieee]["targetIEEE"] = dest_ieee
            binding_record[source_ieee]["targetNickName"] = get_device_nickname( self, Ieee=dest_ieee)

            dest_ep = BindingTableListRecord[ idx: idx + 2]
            idx += 2
            binding_record[source_ieee]["targetEp"] = dest_ep
        elif addr_mode == '02':  # Short Id
            shortid = "%04x" %struct.unpack("H", struct.pack(">H", int( BindingTableListRecord[ idx: idx +4] , 16)))[0]
            idx += 4
            binding_record[source_ieee]["targetNwkId"] = shortid
            binding_record[source_ieee]["targetNickName"] = get_device_nickname( self, NwkId=shortid)

            dest_ep = BindingTableListRecord[ idx: idx + 2]
            idx += 2
            binding_record[source_ieee]["targetEp"] = dest_ep

        elif addr_mode == '01':  # Group no EndPoint
            shortid = "%04x" %struct.unpack("H", struct.pack(">H", int( BindingTableListRecord[ idx: idx +4] , 16)))[0]
            binding_record[source_ieee]["targetGroupId"] = shortid
            idx += 4

        update_merge_new_device_BindinTable(self, srcnwkid, binding_record )

    if int(BindingTableIndex, 16) + int(BindingTableListCount, 16) < int(BindingTableSize, 16):
        mgt_binding_table_req(self, srcnwkid, "%02x" % (int(BindingTableIndex, 16) + int(BindingTableListCount, 16)))
