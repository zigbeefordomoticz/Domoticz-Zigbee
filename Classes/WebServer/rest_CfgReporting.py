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
    if self.configureReporting is None or verb != "GET" or len(parameters) != 1:
        self.logging("Error", f"rest_cfgrpt_ondemand incorrect request {verb} {data} {parameters}")
        return _response

    if parameters[0] not in self.ListOfDevices:
        self.logging("Error", "rest_cfgrpt_ondemand requested on %s doesn't exist" % parameters[0])
        return _response

    self.configureReporting.cfg_reporting_on_demand( parameters[0] )
    self.logging("Debug", f"rest_cfgrpt_ondemand requested on {parameters[0]}")

    _response["Data"] = json.dumps({"status": "Configure Reporting requested"}, )
    return _response


def rest_cfgrpt_ondemand_with_config(self, verb, data, parameters ):

    # wget --method=PUT \
    #      --body-data='{ 
    #                       "Nwkid": nwkid, 
    #                       "Clusters": {
    #                                       "0006": {
    #                                                  "Attributes": { 
    #                                                                   "0000": { "Min": "000A", "Max": "0C30", "Change": "01" },
    #                                                                   "0001": { "Min": "000A", "Max": "0C30", "Change": "01" }
    #                                                  },
    #                                       "0008": {
    #                                                  "Attributes": { 
    #                                                                   "0000": { "Min": "000A", "Max": "0C30", "Change": "01" },
    #                                                                   "0001": { "Min": "000A", "Max": "0C30", "Change": "01" }
    #                                                  }
    #                                      }
    #                       }
    #                    }' \
    #     http://127.0.0.1:9442/rest-zigate/1/cfgrpt-ondemand-config

    self.logging("Debug", f"rest_cfgrpt_ondemand_with_config  {verb} {data} {parameters}")
    
    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None

    if verb not in ("GET", "PUT", "DELETE"):
        # Only Put command with a Valid JSON is allow
        self.logging("Error", f"rest_cfgrpt_ondemand_with_config incorrect request only PUT allowed {verb} {data} {parameters}")
        return _response

    if self.configureReporting is None:
        self.logging("Debug", f"rest_cfgrpt_ondemand_with_config configureReporting not ready yet !!!{verb} {data} {parameters}")
        return _response

    if verb == "PUT":
        return rest_cfgrpt_ondemand_with_config_put(self, verb, data, parameters , _response)
    
    if verb == "DELETE":
        return rest_cfgrpt_ondemand_with_config_delete(self, verb, data, parameters , _response)

    if verb == "GET":
        return rest_cfgrpt_ondemand_with_config_get(self, verb, data, parameters , _response)
       
        
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
    _response["Data"] = json.dumps( cfg_rpt_record )
    
    return _response

def rest_cfgrpt_ondemand_with_config_put(self, verb, data, parameters , _response):
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

    nwkid = data[ "NwkId"]
    cluster_list = data[ "Clusters" ]

    if nwkid not in self.ListOfDevices:
        self.logging("Error", f"rest_cfgrpt_ondemand_with_config unknown devices NwkId: {nwkid} !!! ")
        return _response

    if "ParamConfigureReporting" in self.ListOfDevices[ nwkid ]:
        self.logging("Debug", f"rest_cfgrpt_ondemand_with_config will override Config Reporting for {nwkid} !!! ")

    # Sanity check on the cluster list
    error_found = False
    for x in cluster_list:
        if "Attributes" not in cluster_list[ x ]:
            self.logging("Error", f"rest_cfgrpt_ondemand_with_config missing 'Attributes' in  {cluster_list[ x ]} !!! ")
            error_found = True
            continue
        for y in cluster_list[ x ][ "Attributes" ]:
            if "Min" not in cluster_list[ x ][ "Attributes" ][ y ]:
                self.logging("Error", f"rest_cfgrpt_ondemand_with_config missing 'Min' in  {cluster_list[ x ][ 'Attributes' ][ y ]} !!! ")
                error_found = True
                continue

            if "Max" not in cluster_list[ x ][ "Attributes" ][ y ]:
                self.logging("Error", f"rest_cfgrpt_ondemand_with_config missing 'Max' in  {cluster_list[ x ][ 'Attributes' ][ y ]} !!! ")
                error_found = True
                continue

            if "Change" not in cluster_list[ x ][ "Attributes" ][ y ]:
                self.logging("Error", f"rest_cfgrpt_ondemand_with_config missing 'Change' in  {cluster_list[ x ][ 'Attributes' ][ y ]} !!! ")
                error_found = True
                continue

    if error_found:
        action = {"Name": "Configure reporting record NOT updated - error found, please check logs", "TimeStamp": int(time.time())}
    else:
        self.ListOfDevices[ nwkid ][ "ParamConfigureReporting" ] = cluster_list
        action = {"Name": "Configure reporting record updated", "TimeStamp": int(time.time())}

    _response["Data"] = json.dumps(action, sort_keys=True)
    return _response



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
