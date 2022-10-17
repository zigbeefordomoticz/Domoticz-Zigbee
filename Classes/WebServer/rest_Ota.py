#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import json
from time import time

import Domoticz
from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.bindings import webBind, webUnBind
from Modules.zigateConsts import ZCL_CLUSTERS_ACT

MATRIX_MANUFACTURER_NAME = {
    "117c": "IKEA of Sweden",
    "1246": "Danfoss",
    "1189": "LEDVANCE",
    "bbaa": "OSRAM",
    "110C": "OSRAM",
    "1021": "Legrand",
    "100b": "Philips",
    "105e": "Schneider Electric",
    "1078": "Computime",
    "1037": "LiXee",
    "1037": "Eurotronics",
    "1286": "Sonoff",
}

def rest_ota_firmware_list(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None

    if self.OTA and verb == "GET" and len(parameters) == 0:
        if len(self.ControllerData) == 0:
            _response["Data"] = fake_rest_ota_firmware_list()
            return _response

        _response["Data"] = json.dumps(self.OTA.restapi_list_of_firmware(), sort_keys=True)

    return _response


def fake_rest_ota_firmware_list():

    return json.dumps(
        [
            {
                "Ikea": [
                    {
                        "ApplicationBuild": "09",
                        "ApplicationRelease": "76",
                        "FileName": "10035534-2.1-TRADFRI-bulb-ws-gu10-2.3.050.ota.ota.signed",
                        "ImageType": "2203",
                        "ManufCode": "117c",
                        "StackBuild": "33",
                        "StackRelease": "06",
                        "Version": "76090633",
                    },
                    {
                        "ApplicationBuild": "06",
                        "ApplicationRelease": "73",
                        "FileName": "10038562-2.1-TRADFRI-sy5882-bulb-ws-2.0.029.ota.ota.signed",
                        "ImageType": "4204",
                        "ManufCode": "117c",
                        "StackBuild": "25",
                        "StackRelease": "96",
                        "Version": "73069625",
                    },
                    {
                        "ApplicationBuild": "06",
                        "ApplicationRelease": "76",
                        "FileName": "159701-2.1-TRADFRI-wireless-dimmer-2.3.028.ota.ota.signed",
                        "ImageType": "11c2",
                        "ManufCode": "117c",
                        "StackBuild": "33",
                        "StackRelease": "86",
                        "Version": "76068633",
                    },
                    {
                        "ApplicationBuild": "06",
                        "ApplicationRelease": "74",
                        "FileName": "10043101-3.1-TRADFRI-dimmer-2.1.024.ota.ota.signed",
                        "ImageType": "11ca",
                        "ManufCode": "117c",
                        "StackBuild": "33",
                        "StackRelease": "46",
                        "Version": "74064633",
                    },
                    {
                        "ApplicationBuild": "05",
                        "ApplicationRelease": "75",
                        "FileName": "10005778-10.1-TRADFRI-onoff-shortcut-control-2.2.010.ota.ota.signed",
                        "ImageType": "11c5",
                        "ManufCode": "117c",
                        "StackBuild": "33",
                        "StackRelease": "06",
                        "Version": "75050633",
                    },
                    {
                        "ApplicationBuild": "06",
                        "ApplicationRelease": "73",
                        "FileName": "10039874-1.0-TRADFRI-motion-sensor-2-2.0.022.ota.ota.signed",
                        "ImageType": "11c8",
                        "ManufCode": "117c",
                        "StackBuild": "25",
                        "StackRelease": "26",
                        "Version": "73062625",
                    },
                    {
                        "ApplicationBuild": "05",
                        "ApplicationRelease": "76",
                        "FileName": "159699-5.1-TRADFRI-remote-control-2.3.014.ota.ota.signed",
                        "ImageType": "11c1",
                        "ManufCode": "117c",
                        "StackBuild": "33",
                        "StackRelease": "46",
                        "Version": "76054633",
                    },
                    {
                        "ApplicationBuild": "09",
                        "ApplicationRelease": "76",
                        "FileName": "10046695-1.1-TRADFRI-light-unified-w-2.3.050.ota.ota.signed",
                        "ImageType": "4103",
                        "ManufCode": "117c",
                        "StackBuild": "33",
                        "StackRelease": "06",
                        "Version": "76090633",
                    },
                    {
                        "ApplicationBuild": "09",
                        "ApplicationRelease": "76",
                        "FileName": "159695-2.1-TRADFRI-bulb-ws-1000lm-2.3.050.ota.ota.signed",
                        "ImageType": "2202",
                        "ManufCode": "117c",
                        "StackBuild": "33",
                        "StackRelease": "06",
                        "Version": "76090633",
                    },
                    {
                        "ApplicationBuild": "09",
                        "ApplicationRelease": "76",
                        "FileName": "10040611-3.2-TRADFRI-sy5882-unified-2.3.050.ota.ota.signed",
                        "ImageType": "4205",
                        "ManufCode": "117c",
                        "StackBuild": "33",
                        "StackRelease": "06",
                        "Version": "76090633",
                    },
                    {
                        "ApplicationBuild": "25",
                        "ApplicationRelease": "65",
                        "FileName": "159700-TRADFRI-motion-sensor-1.2.214.ota.ota.signed",
                        "ImageType": "11c4",
                        "ManufCode": "117c",
                        "StackBuild": "74",
                        "StackRelease": "45",
                        "Version": "65254574",
                    },
                    {
                        "ApplicationBuild": "06",
                        "ApplicationRelease": "73",
                        "FileName": "191100-4.1-TRADFRI-sy5882-driver-ws-2.0.029.ota.ota.signed",
                        "ImageType": "4203",
                        "ManufCode": "117c",
                        "StackBuild": "25",
                        "StackRelease": "96",
                        "Version": "73069625",
                    },
                    {
                        "ApplicationBuild": "09",
                        "ApplicationRelease": "76",
                        "FileName": "10035514-2.1-TRADFRI-bulb-ws-2.3.050.ota.ota.signed",
                        "ImageType": "2201",
                        "ManufCode": "117c",
                        "StackBuild": "33",
                        "StackRelease": "06",
                        "Version": "76090633",
                    },
                    {
                        "ApplicationBuild": "26",
                        "ApplicationRelease": "65",
                        "FileName": "159698-TRADFRI-driver-lp-1.2.224.ota.ota.signed",
                        "ImageType": "4201",
                        "ManufCode": "117c",
                        "StackBuild": "75",
                        "StackRelease": "45",
                        "Version": "65264575",
                    },
                    {
                        "ApplicationBuild": "06",
                        "ApplicationRelease": "73",
                        "FileName": "10005777-6.1-TRADFRI-control-outlet-2.0.024.ota.ota.signed",
                        "ImageType": "1101",
                        "ManufCode": "117c",
                        "StackBuild": "25",
                        "StackRelease": "46",
                        "Version": "73064625",
                    },
                    {
                        "ApplicationBuild": "25",
                        "ApplicationRelease": "65",
                        "FileName": "159696-TRADFRI-bulb-w-1000lm-1.2.214.ota.ota.signed",
                        "ImageType": "2101",
                        "ManufCode": "117c",
                        "StackBuild": "74",
                        "StackRelease": "45",
                        "Version": "65254574",
                    },
                    {
                        "ApplicationBuild": "04",
                        "ApplicationRelease": "75",
                        "FileName": "10037603-3.1-TRADFRI-signal-repeater-2.2.005.ota.ota.signed",
                        "ImageType": "1102",
                        "ManufCode": "117c",
                        "StackBuild": "33",
                        "StackRelease": "56",
                        "Version": "75045633",
                    },
                    {
                        "ApplicationBuild": "04",
                        "ApplicationRelease": "75",
                        "FileName": "10037585-5.1-TRADFRI-connected-blind-2.2.009.ota.ota.signed",
                        "ImageType": "1187",
                        "ManufCode": "117c",
                        "StackBuild": "33",
                        "StackRelease": "96",
                        "Version": "75049633",
                    },
                    {
                        "ApplicationBuild": "28",
                        "ApplicationRelease": "65",
                        "FileName": "159495-TRADFRI-transformer-1.2.245.ota.ota.signed",
                        "ImageType": "4101",
                        "ManufCode": "117c",
                        "StackBuild": "74",
                        "StackRelease": "55",
                        "Version": "65285574",
                    },
                    {
                        "ApplicationBuild": "26",
                        "ApplicationRelease": "65",
                        "FileName": "159697-TRADFRI-driver-hp-1.2.224.ota.ota.signed",
                        "ImageType": "4202",
                        "ManufCode": "117c",
                        "StackBuild": "75",
                        "StackRelease": "45",
                        "Version": "65264575",
                    },
                    {
                        "ApplicationBuild": "05",
                        "ApplicationRelease": "66",
                        "FileName": "10035515-TRADFRI-bulb-cws-1.3.013.ota.ota.signed",
                        "ImageType": "2801",
                        "ManufCode": "117c",
                        "StackBuild": "74",
                        "StackRelease": "35",
                        "Version": "66053574",
                    },
                    {
                        "ApplicationBuild": "09",
                        "ApplicationRelease": "76",
                        "FileName": "10047227-1.2-TRADFRI-cv-cct-unified-2.3.050.ota.ota.signed",
                        "ImageType": "4206",
                        "ManufCode": "117c",
                        "StackBuild": "33",
                        "StackRelease": "06",
                        "Version": "76090633",
                    },
                ],
                "Legrand": [
                    {
                        "ApplicationBuild": "26",
                        "ApplicationRelease": "53",
                        "FileName": "NLV-34.fw",
                        "ImageType": "0013",
                        "ManufCode": "1021",
                        "StackBuild": "05",
                        "StackRelease": "42",
                        "Version": "53264205",
                    }
                ],
                "Schneider": [
                    {
                        "ApplicationBuild": "08",
                        "ApplicationRelease": "a5",
                        "FileName": "EH_ZB_SNP_R_04_01_14_VACT.zigbee",
                        "ImageType": "0001",
                        "ManufCode": "105e",
                        "StackBuild": "10",
                        "StackRelease": "01",
                        "Version": "a5080110",
                    },
                    {
                        "ApplicationBuild": "08",
                        "ApplicationRelease": "a5",
                        "FileName": "EH_VAC_R_04_00_02.zigbee",
                        "ImageType": "0002",
                        "ManufCode": "105e",
                        "StackBuild": "04",
                        "StackRelease": "00",
                        "Version": "a5080004",
                    },
                ],
            }
        ],
        sort_keys=True,
    )


def rest_ota_devices_for_manufcode(self, verb, data, parameters):

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None

    if self.OTA is None or verb != "GET" or len(parameters) != 1:
        return _response

    if len(self.ControllerData) == 0:
        _response["Data"] = fake_rest_ota_devices_for_manufcode()
        return _response

    manuf_code = parameters[0]
    device_list = []
    for x in self.ListOfDevices:
        if "Manufacturer" not in self.ListOfDevices[x] and "Manufacturer Name" not in self.ListOfDevices[x]:
            continue

        compatible = False
        if (
            manuf_code in MATRIX_MANUFACTURER_NAME
            and "Manufacturer Name" in self.ListOfDevices[x]
            and MATRIX_MANUFACTURER_NAME[manuf_code] == self.ListOfDevices[x]["Manufacturer Name"]
        ):
            compatible = True

        if not compatible and self.ListOfDevices[x]["Manufacturer"] != manuf_code:
            continue

        Domoticz.Log("Found device: %s" % x)

        device_list.append(get_device_informations(self, x))
    _response["Data"] = json.dumps(device_list, sort_keys=True)
    return _response


def get_device_informations(self, Nwkid):
    time_update = LastImageVersion = LastImageType = ""
    ep = "01"
    for y in self.ListOfDevices[Nwkid]["Ep"]:
        if "0019" in self.ListOfDevices[Nwkid]["Ep"][y]:
            ep = y
            break
    device_name = model_name = swbuild_3 = swbuild_1 = ""
    if "ZDeviceName" in self.ListOfDevices[Nwkid] and self.ListOfDevices[Nwkid]["ZDeviceName"] != {}:
        device_name = self.ListOfDevices[Nwkid]["ZDeviceName"]
    if "Model" in self.ListOfDevices[Nwkid] and self.ListOfDevices[Nwkid]["Model"] != {}:
        model_name = self.ListOfDevices[Nwkid]["Model"]
    if "SWBUILD_3" in self.ListOfDevices[Nwkid] and self.ListOfDevices[Nwkid]["SWBUILD_3"] != {}:
        swbuild_3 = self.ListOfDevices[Nwkid]["SWBUILD_3"]
    if "SWBUILD_1" in self.ListOfDevices[Nwkid] and self.ListOfDevices[Nwkid]["SWBUILD_1"] != {}:
        swbuild_1 = self.ListOfDevices[Nwkid]["SWBUILD_1"]
    if "OTA" in self.ListOfDevices[Nwkid]:
        prev_ts = 0

        for ts in self.ListOfDevices[Nwkid]["OTA"]:
            if ts > prev_ts:
                time_update = self.ListOfDevices[Nwkid]["OTA"][ts]["Time"]
                LastImageVersion = self.ListOfDevices[Nwkid]["OTA"][ts]["Version"]
                LastImageType = self.ListOfDevices[Nwkid]["OTA"][ts]["Type"]

    return {
        "Nwkid": Nwkid,
        "Ep": ep,
        "DeviceName": device_name,
        "SWBUILD_1": swbuild_3,
        "SWBUILD_3": swbuild_1,
        "LastUpdate": time_update,
        "LastUpdateVersion": LastImageVersion,
        "LastImageType": LastImageType,
    }


def fake_rest_ota_devices_for_manufcode():
    return json.dumps(
        [
            {"DeviceName": "Chambre", "Ep": "01", "Nwkid": "6d8c", "SWBUILD_1": "20151006091c090", "SWBUILD_3": ""},
            {"DeviceName": "Bureau", "Ep": "0b", "Nwkid": "fd8e", "SWBUILD_1": "", "SWBUILD_3": "2.2.005"},
            {"DeviceName": "Placard", "Ep": "07", "Nwkid": "6e87", "SWBUILD_1": "09-30-2018", "SWBUILD_3": ""},
            {"DeviceName": "Tracteur", "Ep": "01", "Nwkid": "775e", "SWBUILD_1": "2.3.050", "SWBUILD_3": "1.2.214"},
            {
                "DeviceName": "Patatte",
                "Ep": "06",
                "Nwkid": "45ef",
                "SWBUILD_1": "20160331",
                "SWBUILD_3": "",
                "LastUpdate": "2020-06-08 10:02:54",
                "LastUpdateVersion": "02015120",
                "LastImageType": "0027",
            },
            {"DeviceName": "Boum", "Ep": "01", "Nwkid": "2812", "SWBUILD_1": "SNP.R.04.01.14", "SWBUILD_3": ""},
        ],
        sort_keys=True,
    )


def rest_ota_firmware_update(self, verb, data, parameter):

    # wget --method=PUT --body-data='{
    # 	"NwkId": "0a90",
    # 	"Ep": "0b",
    # 	"Brand": "Schneider",
    # 	"FileName": "EH_ZB_SNP_R_04_01_14_VACT.zigbee"
    # }' http://127.0.0.1:9440/rest-zigate/1/ota-firmware-update
    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None

    if self.OTA is None:
        # OTA is not enabled!
        return _response

    if verb != "PUT":
        # Only Put command with a Valid JSON is allow
        return _response

    if data is None:
        return _response

    if len(parameter) != 0:
        return _response

    # We receive a JSON with a list of NwkId to be scaned
    data = data.decode("utf8")

    self.logging("Debug", "rest_ota_firmware_update - Data received  %s " % (data))

    data = json.loads(data)
    self.logging("Debug", "rest_ota_firmware_update - Trigger OTA upgrade  %s " % (data))

    # Check
    for x in data:
        if "Brand" not in x or "FileName" not in x or "NwkId" not in x or "Ep" not in x or "ForceUpdate" not in x:
            self.logging("Error", "rest_ota_firmware_update - Missing key parameters  %s " % (data))
            _response["Data"] = json.dumps({"Error": "Missing attributes"}, sort_keys=True)
            return _response

    self.logging("Debug", "rest_ota_firmware_update - data: %s" % (data))

    if self.OTA:
        self.OTA.restapi_firmware_update(data)

    action = {"Name": "OTA requested.", "TimeStamp": int(time())}
    _response["Data"] = json.dumps(action, sort_keys=True)
    return _response
