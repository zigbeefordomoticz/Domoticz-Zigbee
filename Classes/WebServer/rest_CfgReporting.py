#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import json
import time

import Domoticz
from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.pluginDbAttributes import STORE_READ_CONFIGURE_REPORTING, STORE_CONFIGURE_REPORTING, STORE_CUSTOM_CONFIGURE_REPORTING

from Modules.zigateConsts import SIZE_DATA_TYPE, analog_value


def rest_cfgrpt_ondemand(self, verb, data, parameters):
    # Trigger a Cfg Reporting on a specific Device

    _response = prepResponseMessage(self, setupHeadersResponse())
    if self.ControllerData and self.configureReporting is None or verb != "GET" or len(parameters) != 1:
        self.logging("Error", f"rest_cfgrpt_ondemand incorrect request {verb} {data} {parameters}")
        return _response

    if self.ControllerData and parameters[0] not in self.ListOfDevices:
        self.logging("Error", "rest_cfgrpt_ondemand requested on %s doesn't exist" % parameters[0])
        return _response

    if self.ControllerData:
        self.configureReporting.check_and_redo_configure_reporting_if_needed( parameters[0] )
        
    self.logging("Debug", f"rest_cfgrpt_ondemand requested on {parameters[0]}")

    _response["Data"] = json.dumps({"status": "Configure Reporting requested"}, )
    return _response


def rest_cfgrpt_ondemand_with_config(self, verb, data, parameters ):


    self.logging("Debug", f"rest_cfgrpt_ondemand_with_config  {verb} {data} {parameters}")
    
    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None

    if verb not in ("GET", "PUT", "DELETE"):
        # Only Put command with a Valid JSON is allow
        self.logging("Error", f"rest_cfgrpt_ondemand_with_config incorrect request only PUT allowed {verb} {data} {parameters}")
        return _response

    if self.ControllerData and self.configureReporting is None:
        self.logging("Debug", f"rest_cfgrpt_ondemand_with_config configureReporting not ready yet !!!{verb} {data} {parameters}")
        return _response

    if verb == "PUT":
        if self.ControllerData:
            return rest_cfgrpt_ondemand_with_config_put(self, verb, data, parameters , _response)
        return fake_cfgrpt_ondemand_with_config_put(self, verb, data, parameters , _response)
    
    if verb == "DELETE":
        return rest_cfgrpt_ondemand_with_config_delete(self, verb, data, parameters , _response)

    if verb == "GET":
        if self.ControllerData:
            return rest_cfgrpt_ondemand_with_config_get(self, verb, data, parameters , _response)
        return fake_cfgrpt_ondemand_with_config_get(self, verb, data, parameters , _response)
       
        
def rest_cfgrpt_ondemand_with_config_delete(self, verb, data, parameters , _response):
    self.logging("Debug", f"rest_cfgrpt_ondemand_with_config_delete  {verb} {data} {parameters}")

    if len(parameters) != 1:
        self.logging("Error", f"rest_cfgrpt_ondemand_with_config_delete incorrect request existing parameters !!! {verb} {data} {parameters}")
        return _response
    
    deviceId = parameters[0]
    if deviceId not in self.ListOfDevices:
        self.logging("Error", f"rest_cfgrpt_ondemand_with_config_delete unknown devices NwkId: {deviceId} !!! ")
        return _response
    
    if STORE_CUSTOM_CONFIGURE_REPORTING in self.ListOfDevices[ deviceId ]:
        del self.ListOfDevices[ deviceId ][ STORE_CUSTOM_CONFIGURE_REPORTING ]
        
    if STORE_READ_CONFIGURE_REPORTING in self.ListOfDevices[ deviceId ]:
        del self.ListOfDevices[ deviceId ][ STORE_READ_CONFIGURE_REPORTING ]
        
    if STORE_CONFIGURE_REPORTING in self.ListOfDevices[ deviceId ]:
        del self.ListOfDevices[ deviceId ][ STORE_CONFIGURE_REPORTING ]

    action = {"Name": "Reset Configure reporting records removed", "TimeStamp": int(time.time())}
    _response["Data"] = json.dumps(action, sort_keys=True)
    return _response


def rest_cfgrpt_ondemand_with_config_get(self, verb, data, parameters , _response):
    
    self.logging("Debug", f"rest_cfgrpt_ondemand_with_config_get  {verb} {data} {parameters}")
    deviceId = parameters[0]
    cfg_rpt_record = get_cfg_rpt_record( self, deviceId )

    self.logging("Debug", f"rest_cfgrpt_ondemand_with_config_get  {cfg_rpt_record}")
    _response["Data"] = convert_to_json( self, cfg_rpt_record )
    
    return _response

def fake_cfgrpt_ondemand_with_config_get(self, verb, data, parameters , _response):
    cluster_list = [{"ClusterId": "0702", "Attributes": [{"Attribute": "0000", "Infos": [{"DataType": "25", "MinInterval": "0005", "MaxInterval": "012C", "TimeOut": "0000", "Change": "0000000000000001"}]}]}, {"ClusterId": "0b04", "Attributes": [{"Attribute": "0505", "Infos": [{"DataType": "21", "MinInterval": "0001", "MaxInterval": "0005", "TimeOut": "0000", "Change": "0001"}]}, {"Attribute": "0508", "Infos": [{"DataType": "21", "MinInterval": "0001", "MaxInterval": "012C", "TimeOut": "0000", "Change": "0001"}]}, {"Attribute": "050b", "Infos": [{"DataType": "29", "MinInterval": "0001", "MaxInterval": "0005", "TimeOut": "0000", "Change": "0001"}]}]}]
    _response["Data"] = json.dumps(  cluster_list )
    return _response


def rest_cfgrpt_ondemand_with_config_put(self, verb, data, parameters , _response):
    # wget --method=PUT \
    #      --body-data='{ 
    #               "Nwkid": nwkid, 
    #               "Clusters":
    #                    [
    #                        {
    #                            "ClusterId": "0006", 
    #                            "Attributes": [
    #                                {
    #                                    "Attribute": "0000", 
    #                                    "Infos": [{"DataType": "10"}, {"MinInterval": "0001"}, {"MaxInterval": "012C"}, {"TimeOut": "0FFF"}, {"Change": "01"}]}]}, 
    #                        {
    #                            "ClusterId": "0702", 
    #                            "Attributes": [
    #                                {
    #                                    "Attribute": "0000", 
    #                                    "Infos": [{"DataType": "25"}, {"MinInterval": "FFFF"}, {"MaxInterval": "0000"}, {"TimeOut": "0000"}, {"Change": "000000000000000a"}]}]},
    #                        {
    #                            "ClusterId": "0b04", 
    #                            "Attributes": [
    #                                {
    #                                    "Attribute": "0505", 
    #                                    "Infos": [{"DataType": "21"}, {"MinInterval": "0005"}, {"MaxInterval": "012C"}, {"TimeOut": "0000"}, {"Change": "000a"}]}, 
    #                                {
    #                                    "Attribute": "0508", 
    #                                    "Infos": [{"DataType": "21"}, {"MinInterval": "0005"}, {"MaxInterval": "012C"}, {"TimeOut": "0000"}, {"Change": "000a"}]},
    #                                {
    #                                    "Attribute": "050b", "Infos": [{"DataType": "29"}, {"MinInterval": "0005"}, {"MaxInterval": "012C"}, {"TimeOut": "0000"}, {"Change": "000a"}]}]}]
    #                    }' \
    #     http://127.0.0.1:9442/rest-zigate/1/cfgrpt-ondemand-config

    # Put the device specific configure reporting to the device infos
    self.logging("Debug", f"rest_cfgrpt_ondemand_with_config_put  {verb} {data} {parameters}")
    if data is None:
        self.logging("Error", f"rest_cfgrpt_ondemand_with_config incorrect request no data !!! {verb} {data} {parameters}")
        return _response
    if len(parameters) != 0:
        self.logging("Error", f"rest_cfgrpt_ondemand_with_config incorrect request existing parameters !!! {verb} {data} {parameters}")
        return _response
    # We receive a JSON 
    data = data.decode("utf8")
    data = json.loads(data)
    if "Nwkid" not in data and "Clusters" not in data:
        self.logging("Error", f"rest_cfgrpt_ondemand_with_config missing infos in data %s !!! {verb} {data} {parameters}")
        return _response
    nwkid = data[ "Nwkid"]
    cluster_config_reporting = {}
    cluster_list = data[ "Clusters" ]
    if nwkid not in self.ListOfDevices:
        self.logging("Error", f"rest_cfgrpt_ondemand_with_config unknown devices NwkId: {nwkid} !!! ")
        return _response

    if STORE_CUSTOM_CONFIGURE_REPORTING in self.ListOfDevices[ nwkid ]:
        self.logging("Debug", f"rest_cfgrpt_ondemand_with_config will override Config Reporting for {nwkid} !!! ")

    # Sanity check on the cluster list
    self.logging("Debug", f"rest_cfgrpt_ondemand_with_config_put  let's do the work on {cluster_list} for {nwkid}")
    for cluster_info in cluster_list:
        if "ClusterId" not in cluster_info:
            continue
        cluster_config_reporting[ cluster_info["ClusterId"] ] = {}
        if "Attributes" not in cluster_info:
            continue
        cluster_config_reporting[ cluster_info["ClusterId"] ]["Attributes"] = {}
        attributes_list = cluster_info[ "Attributes"]
        
        for attribute in attributes_list:
            if "Attribute" not in attribute:
                continue
            cluster_config_reporting[ cluster_info["ClusterId"] ]["Attributes"][ attribute[ "Attribute"] ] = {}
            # All data are sent by the Frontend in hex. We need to make sure they are store in the proper format
            for info in attribute["Infos"]:
                if "MinInterval" in info:
                    cluster_config_reporting[ cluster_info["ClusterId"] ]["Attributes"][ attribute[ "Attribute"] ]["MinInterval"] = "%04x" %int(info["MinInterval"],16)
                if "MaxInterval" in info:
                    cluster_config_reporting[ cluster_info["ClusterId"] ]["Attributes"][ attribute[ "Attribute"] ]["MaxInterval"] = "%04x" % int(info["MaxInterval"],16)
                if "TimeOut" in info:
                    cluster_config_reporting[ cluster_info["ClusterId"] ]["Attributes"][ attribute[ "Attribute"] ]["TimeOut"] = "%04x" %int(info["TimeOut"],16)
                if "DataType" in info:
                    cluster_config_reporting[ cluster_info["ClusterId"] ]["Attributes"][ attribute[ "Attribute"] ]["DataType"] = "%02x" % int(info["DataType"],16)
                    if "Change" in info and analog_value(int(info["DataType"], 16)):
                        cluster_config_reporting[ cluster_info["ClusterId"] ]["Attributes"][ attribute[ "Attribute"] ]["Change"] = datatype_formating( self, info["Change"], info["DataType"] )
                        
    self.ListOfDevices[ nwkid ][ STORE_CUSTOM_CONFIGURE_REPORTING ] = cluster_config_reporting
    action = {"Name": "Configure reporting record updated", "TimeStamp": int(time.time())}

    _response["Data"] = json.dumps(action, sort_keys=True)
    return _response


def fake_cfgrpt_ondemand_with_config_put(self, verb, data, parameters , _response):
    action = {"Name": "Configure reporting record updated", "TimeStamp": int(time.time())}
    _response["Data"] = json.dumps(action, sort_keys=True)
    return _response

def convert_to_json( self, data ):
    # {"0006": {"Attributes": {"0000": {"DataType": "10", "MinInterval": "0001", "MaxInterval": "012C", "TimeOut": "0FFF", "Change": "01"}}}, 
    #  "0702": {"Attributes": {"0000": {"DataType": "25", "MinInterval": "FFFF", "MaxInterval": "0000", "TimeOut": "0000", "Change": "000000000000000a"}}}, 
    #  "0b04": {"Attributes": {"0505": {"DataType": "21", "MinInterval": "0005", "MaxInterval": "012C", "TimeOut": "0000", "Change": "000a"},
    #                          "0508": {"DataType": "21", "MinInterval": "0005", "MaxInterval": "012C", "TimeOut": "0000", "Change": "000a"}, 
    #                          "050b": {"DataType": "29", "MinInterval": "0005", "MaxInterval": "012C", "TimeOut": "0000", "Change": "000a"}}}}
    self.logging("Debug", f"convert_to_json Data {data}")
    cluster_list = []

    for cluster in data:
        cluster_info = {"ClusterId": cluster, "Attributes": []}
        for attribute in data[ cluster ]["Attributes"]:
            infos = {item: data[cluster]["Attributes"][attribute][item] for item in data[cluster]["Attributes"][attribute]}
            attributes_info = {"Attribute": attribute, "Infos": [ infos ] }
            cluster_info[ "Attributes"].append( attributes_info )

        cluster_list.append( cluster_info )
    return json.dumps(  cluster_list )

               
def get_cfg_rpt_record(self, NwkId):

    if STORE_CUSTOM_CONFIGURE_REPORTING in self.ListOfDevices[NwkId]:
        return self.ListOfDevices[NwkId][ STORE_CUSTOM_CONFIGURE_REPORTING ]

    if (
        "Model" in self.ListOfDevices[NwkId]
        and self.ListOfDevices[NwkId]["Model"] != {}
        and self.ListOfDevices[NwkId]["Model"] in self.DeviceConf
        and "ConfigureReporting" in self.DeviceConf[self.ListOfDevices[NwkId]["Model"]]
    ):
        return self.DeviceConf[ self.ListOfDevices[NwkId]["Model"]]["ConfigureReporting" ]

def datatype_formating( self, value, type):
    
    if type not in SIZE_DATA_TYPE:
            
        return value

    if SIZE_DATA_TYPE[ type ] == 1:
        return "%02x" %int( value, 16)
    if SIZE_DATA_TYPE[ type ] == 2:
        return "%04x" %int( value, 16)
    if SIZE_DATA_TYPE[ type ] == 3:
        return "%06x" %int( value, 16)
    if SIZE_DATA_TYPE[ type ] == 4:
        return "%08x" %int( value, 16)
    if SIZE_DATA_TYPE[ type ] == 5:
        return "%010x" %int( value, 16)
    if SIZE_DATA_TYPE[ type ] == 6:
        return "%012x" %int( value, 16)
    if SIZE_DATA_TYPE[ type ] == 7:
        return "%014x" %int( value, 16)
    if SIZE_DATA_TYPE[ type ] == 8:
        return "%016x" %int( value, 16)

    self.logging("Error", f"datatype_formating  unknown Data type {type} for value {value}")
    return value

        
