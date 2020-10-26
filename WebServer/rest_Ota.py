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

def rest_ota_firmware_list( self, verb, data, parameters):

    _response = prepResponseMessage( self ,setupHeadersResponse(  ))
    _response["Data"] = None

    if self.OTA and verb == 'GET' and len(parameters) == 0:
        _response['Data'] = json.dumps( self.OTA.restapi_list_of_firmware( ) , sort_keys=True)

    return _response    

def rest_ota_devices_for_manufcode( self, verb, data, parameters):

    _response = prepResponseMessage( self ,setupHeadersResponse(  ))
    _response["Data"] = None

    if self.OTA and verb == 'GET' and len(parameters) == 1:
        manuf_code = parameters[0]
        device_list = []
        _response["Data"] = []
        for x in self.ListOfDevices:
            if 'Manufacturer' in self.ListOfDevices[x] and self.ListOfDevices[x]['Manufacturer'] == manuf_code:
                Domoticz.Log("Found device: %s" %x)
                ep = '01'
                for y in self.ListOfDevices[x]['Ep']:
                    if '0019' in self.ListOfDevices[x]['Ep'][ y ]:
                        ep = y
                        break
                device_name = swbuild_3 = swbuild_1 = ''
                if 'ZDeviceName' in self.ListOfDevices[x] and self.ListOfDevices[x]['ZDeviceName'] != {}:
                    device_name = self.ListOfDevices[x]['ZDeviceName']
                if 'SWBUILD_3' in self.ListOfDevices[x] and self.ListOfDevices[x]['SWBUILD_3'] != {}:
                    swbuild_3 = self.ListOfDevices[x]['SWBUILD_3']
                if 'SWBUILD_1' in self.ListOfDevices[x] and self.ListOfDevices[x]['SWBUILD_1'] != {}:
                    swbuild_1 = self.ListOfDevices[x]['SWBUILD_1']

                device = {'Nwkid': x, 'Ep': ep, 'DeviceName': device_name, 'SWBUILD_1': swbuild_3,'SWBUILD_3':swbuild_1}
                device_list.append( device )
        _response["Data"] = json.dumps(  device_list , sort_keys=True )

    return _response                


def rest_ota_firmware_update( self, verb, data, parameter):

    # wget --method=PUT --body-data='{
    # 	"NwkId": "0a90",
    # 	"Ep": "0b",
    # 	"Brand": "Schneider",
    # 	"FileName": "EH_ZB_SNP_R_04_01_14_VACT.zigbee"
    # }' http://127.0.0.1:9440/rest-zigate/1/ota-firmware-update
    _response = prepResponseMessage( self ,setupHeadersResponse(  ))
    _response["Data"] = None

    if self.OTA is None:
        # OTA is not enabled!
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