#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import json
import time

import Domoticz
from Classes.WebServer.headerResponse import prepResponseMessage, setupHeadersResponse
from Modules.tools import getEpForCluster


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
        self.configureReporting.cfg_reporting_on_demand( parameters[0] )
        
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
    
    if "ParamConfigureReporting" in self.ListOfDevices[ deviceId ]:
        del self.ListOfDevices[ deviceId ][ "ParamConfigureReporting" ]

    action = {"Name": "Configure reporting record removed", "TimeStamp": int(time.time())}
    _response["Data"] = json.dumps(action, sort_keys=True)
    return _response


def rest_cfgrpt_ondemand_with_config_get(self, verb, data, parameters , _response):
    
    self.logging("Debug", f"rest_cfgrpt_ondemand_with_config_get  {verb} {data} {parameters}")
    deviceId = parameters[0]
    cfg_rpt_record = get_cfg_rpt_record( self, deviceId )

    self.logging("Debug", f"rest_cfgrpt_ondemand_with_config_get  {cfg_rpt_record}")
    _response["Data"] = convert_to_json( cfg_rpt_record )
    
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

    if "ParamConfigureReporting" in self.ListOfDevices[ nwkid ]:
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
            for info in attribute["Infos"]:
                if "MinInterval" in info:
                    cluster_config_reporting[ cluster_info["ClusterId"] ]["Attributes"][ attribute[ "Attribute"] ]["MinInterval"] = info["MinInterval"]
                if "MaxInterval" in info:
                    cluster_config_reporting[ cluster_info["ClusterId"] ]["Attributes"][ attribute[ "Attribute"] ]["MaxInterval"] = info["MaxInterval"]
                if "TimeOut" in info:
                    cluster_config_reporting[ cluster_info["ClusterId"] ]["Attributes"][ attribute[ "Attribute"] ]["TimeOut"] = info["TimeOut"]
                if "Change" in info:
                    cluster_config_reporting[ cluster_info["ClusterId"] ]["Attributes"][ attribute[ "Attribute"] ]["Change"] = info["Change"]
                if "DataType" in info:
                    cluster_config_reporting[ cluster_info["ClusterId"] ]["Attributes"][ attribute[ "Attribute"] ]["DataType"] = info["DataType"]
    self.ListOfDevices[ nwkid ][ "ParamConfigureReporting" ] = cluster_config_reporting
    action = {"Name": "Configure reporting record updated", "TimeStamp": int(time.time())}

    _response["Data"] = json.dumps(action, sort_keys=True)
    return _response


def fake_cfgrpt_ondemand_with_config_put(self, verb, data, parameters , _response):
    action = {"Name": "Configure reporting record updated", "TimeStamp": int(time.time())}
    _response["Data"] = json.dumps(action, sort_keys=True)
    return _response

def convert_to_json( data ):
    # {"0006": {"Attributes": {"0000": {"DataType": "10", "MinInterval": "0001", "MaxInterval": "012C", "TimeOut": "0FFF", "Change": "01"}}}, 
    #  "0702": {"Attributes": {"0000": {"DataType": "25", "MinInterval": "FFFF", "MaxInterval": "0000", "TimeOut": "0000", "Change": "000000000000000a"}}}, 
    #  "0b04": {"Attributes": {"0505": {"DataType": "21", "MinInterval": "0005", "MaxInterval": "012C", "TimeOut": "0000", "Change": "000a"},
    #                          "0508": {"DataType": "21", "MinInterval": "0005", "MaxInterval": "012C", "TimeOut": "0000", "Change": "000a"}, 
    #                          "050b": {"DataType": "29", "MinInterval": "0005", "MaxInterval": "012C", "TimeOut": "0000", "Change": "000a"}}}}
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

    if "ParamConfigureReporting" in self.ListOfDevices[NwkId]:
        return self.ListOfDevices[NwkId][ "ParamConfigureReporting" ]

    if (
        "Model" in self.ListOfDevices[NwkId]
        and self.ListOfDevices[NwkId]["Model"] != {}
        and self.ListOfDevices[NwkId]["Model"] in self.DeviceConf
        and "ConfigureReporting" in self.DeviceConf[self.ListOfDevices[NwkId]["Model"]]
    ):
        return self.DeviceConf[ self.ListOfDevices[NwkId]["Model"]]["ConfigureReporting" ]
