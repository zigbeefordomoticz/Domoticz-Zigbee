#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
import Domoticz
import json


from Modules.casaia import list_casaia_ac201, update_pac_entry
from WebServer.headerResponse import setupHeadersResponse, prepResponseMessage
from time import time



def rest_casa_device_list( self, verb, data, parameters):
    
    _response = prepResponseMessage( self ,setupHeadersResponse(  ))
    _response["Data"] = None

    _response['Data'] = list_casaia_ac201( self )

    if self.OTA and verb == 'GET' and len(parameters) == 0:
        if  len(self.zigatedata) == 0:
            _response['Data'] = fake_list_casaia_ac201()
            return _response  
            
        _response['Data'] = json.dumps( self.OTA.restapi_list_of_firmware( ) , sort_keys=True)
                
    return _response      


def fake_list_casaia_ac201():

    return [ 
            { 
                'NwkId': 'aef3', 
                'IEEE': '3c6a2cfffed012345', 
                'Model': 'AC201A', 
                'Name': 'Clim Bureau', 
                'IRCode': '1234' 
            },
            { 
                'NwkId': '531a', 
                'IEEE': '12345cfffed012345', 
                'Model': 'AC201A', 
                'Name': 'Clim Salon', 
                'IRCode': '0000' 
            },
            { 
                'NwkId': '47ab', 
                'IEEE': '3c6a2cfffbbb12345', 
                'Model': 'AC201A', 
                'Name': 'Clim Cave', 
                'IRCode': '461' 
            },
            { 
                'NwkId': '2755', 
                'IEEE': '3c6a2caaaed012345', 
                'Model': 'AC201A', 
                'Name': 'Clim Extérieur', 
                'IRCode': '000' 
            },
    ]



def rest_casa_device_ircode_update( self, verb, data, parameters ):
    # wget --method=PUT --body-data='[ 
    # { 
    # 	"NwkId": "0a90",
    # 	"IRCode": "1234",
    # },
    # {
    # ....
    # ]
    # ' http://127.0.0.1:9440/rest-zigate/1/ota-firmware-update

    _response = prepResponseMessage( self ,setupHeadersResponse(  ))
    _response["Data"] = None

    if verb != 'PUT':
        # Only Put command with a Valid JSON is allow
        return _response


    if data is None:
        return _response

    if len(parameters) != 0:
        return _response 

    # We receive a JSON with a list of NwkId to be scaned
    data = data.decode('utf8')

    self.logging( 'Debug', "rest_casa_device_ircode_update - Data received  %s " %(data))

    data = json.loads(data)
    self.logging( 'Debug', "rest_casa_device_ircode_update - List of Device IRCode  %s " %(data))

    for x in data:
        if 'NwkId' not in x and 'IRCode' not in x:
            continue
        if x[ 'NwkId'] in self.ListOfDevices:
            update_pac_entry(self, x[ 'NwkId'], x[ 'IRCode'])




    