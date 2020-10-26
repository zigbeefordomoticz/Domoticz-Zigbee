#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import Domoticz
import json

from Modules.zigateConsts import ZCL_CLUSTERS_ACT
from Modules.bindings import webBind, webUnBind
from WebServer.headerResponse import setupHeadersResponse, prepResponseMessage
from time import time

def rest_ota_firmware_update( self, verb, data, parameter):

    # wget --method=PUT --body-data='{
    # 	"NwkId": "0a90",
    # 	"Ep": "0b",
    # 	"Brand": "Schneider",
    # 	"FileName": "EH_ZB_SNP_R_04_01_14_VACT.zigbee"
    # }' http://127.0.0.1:9440/rest-zigate/1/ota-firmware-update
    _response = prepResponseMessage( self ,setupHeadersResponse(  ))
    _response["Data"] = None
    if self.groupmgt is None:
        # Group is not enabled!
        return _response

    if verb != 'PUT':
        # Only Put command with a Valid JSON is allow
        return _response

    if data is None:
        return _response

    if len(parameter) != 0:
        return _response 

    # We receive a JSON with a list of NwkId to be scaned
    data = data.decode('utf8')

    self.logging( 'Log', "rest_ota_firmware_update - Data received  %s " %(data))

    data = json.loads(data)
    self.logging( 'Debug', "rest_ota_firmware_update - Trigger OTA upgrade  %s " %(data))

    if 'Brand' not in data or 'FileName' not in data or 'NwkId' not in data or 'Ep' not in data:
        self.logging( 'Error', "rest_ota_firmware_update - Missing key parameters  %s " %(data))
        _response["Data"] = json.dumps( {'Error': 'Missing attributes'} , sort_keys=True )
        return _response

    brand = data['Brand']
    file_name = data['FileName']
    target_nwkid = data['NwkId']
    target_ep = data['Ep']

    self.logging( 'Log', "rest_ota_firmware_update - Brand: %s FileName: %s Target %s/%s " %(brand, file_name, target_nwkid, target_ep))

    if self.OTA:
        self.OTA.restapi_firmware_update( brand, file_name, target_nwkid, target_ep)

    action = {'Name': 'OTA requested.', 'TimeStamp': int(time())}
    _response["Data"] = json.dumps( action , sort_keys=True )
    return _response