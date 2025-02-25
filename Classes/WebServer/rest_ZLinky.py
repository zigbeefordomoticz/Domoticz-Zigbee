#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

import json

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.tools import get_device_nickname
from Modules.zlinky import ZLINKY_MODE

ZLINKY_INDEXES = [ 
    "BASE", "EAST",  
    "EASF01", "HCHC", "EJPHN", "BBRHCJB", 
    "EASF02", "HCHP", "EJPHPM", "BBRHCJW", 
    "EASF03", "BBRHCJW", 
    "EASF04", "BBRHPJW", 
    "EASF05", "BBRHCJR", 
    "EASF06", "BBRHPJR", "EASF07", "EASF08", "EASF09", "EASF10",
    "EASD01", "EASD02", "EASD03", "EASD04", ]
ZLINKY_PARAMETERS = {
    # Historique
    0: ( 
        "ADC0", "BASE", "OPTARIF", "ISOUSC", "IMAX", "PTEC", "DEMAIN", "HHPHC", "PEJP", "ADPS",
        ),
    2: ( 
        "ADC0", "BASE", "OPTARIF", "ISOUSC", "IMAX",
        "IMAX1", "IMAX2", "IMAX3", "PMAX", "PTEC", "DEMAIN", "HHPHC", "PPOT", "PEJP", "ADPS", "ADIR1", "ADIR2", "ADIR3" 
    ),
    
    # Standard
    1: (
        "ADSC", "NGTF", "LTARF", "NTARF", "DATE", "EAST", "EASF01", "EASF02", "EASF03", "EASF04", "EASF05", 
        "EASF06", "EASF07", "EASF08", "EASF09", "EASF10", "EASD01", "EASD02", "EASD03", "EASD04", "URMS1",
        "PREF", "PCOUP",
        "MSG1", "MSG2", "PRM", "STGE", "DPM1", "FPM1", "DPM2", "FPM2", "DPM3", "FPM3", "RELAIS", "NJOURF", "NJOURF+1", "PJOURF+1", "PPOINTE1",
    ),
    
    3: (
        "ADSC", "NGTF", "LTARF", "NTARF", "DATE", "EAST", "EASF01", "EASF02", "EASF03", "EASF04", "EASF05", 
        "EASF06", "EASF07", "EASF08", "EASF09", "EASF10", "EASD01", "EASD02", "EASD03", "EASD04", "URMS1",
        "URMS2", "URMS3", "PREF", "PCOUP",
        "MSG1", "MSG2", "PRM", "STGE", "DPM1", "FPM1", "DPM2", "FPM2", "DPM3", "FPM3", "RELAIS", "NJOURF", "NJOURF+1", "PJOURF+1", "PPOINTE1",
        ),

    5: (
        "ADSC", "NGTF", "LTARF", "NTARF", "DATE", "EAST", "EASF01", "EASF02", "EASF03", "EASF04", "EASF05", 
        "EASF06", "EASF07", "EASF08", "EASF09", "EASF10", "EASD01", "EASD02", "EASD03", "EASD04", "EAIT", "URMS1",
        "PREF", "PCOUP", "SINSTI", "SMAXIN", "SMAXIN-1", "CCAIN", "CCAIN-1", "SMAXN-1", "SMAXN2-1", "SMAXN3-1", 
        "MSG1", "MSG2", "PRM", "STGE", "DPM1", "FPM1", "DPM2", "FPM2", "DPM3", "FPM3", "RELAIS", "NJOURF", "NJOURF+1", "PJOURF+1", "PPOINTE1",
    ),

    7: (
        "ADSC", "NGTF", "LTARF", "NTARF", "DATE", "EAST", "EASF01", "EASF02", "EASF03", "EASF04", "EASF05", 
        "EASF06", "EASF07", "EASF08", "EASF09", "EASF10", "EASD01", "EASD02", "EASD03", "EASD04", "EAIT", "URMS1",
        "URMS2", "URMS3", "PREF", "PCOUP",
        "SINSTI", "SMAXIN", "SMAXIN-1", "CCAIN", "CCAIN-1", "SMAXN-1", "SMAXN2-1", "SMAXN3-1", 
        "MSG1", "MSG2", "PRM", "STGE", "DPM1", "FPM1", "DPM2", "FPM2", "DPM3", "FPM3", "RELAIS", "NJOURF", "NJOURF+1", "PJOURF+1", "PPOINTE1",
        ),
    
}

ZLINK_TARIF_MODE_EXCLUDE = {
    "BASE": ( "PTEC", "DEMAIN", "HHPHC", "HCHP","HCHC", "PEJP", "EJPHN", "EJPHPM", "BBRHCJB", "BBRHPJB", "BBRHCJW", "BBRHPJW", "BBRHCJR", "BBRHPJR" ),
    "HC": ( "DEMAIN", "PEJP", "EJPHN", "EJPHPM", "BBRHCJB", "BBRHPJB", "BBRHCJW", "BBRHPJW", "BBRHCJR", "BBRHPJR" ),
    "HEURES PLEINES": ( "DEMAIN", "PEJP", "EJPHN", "EJPHPM", "BBRHCJB", "BBRHPJB", "BBRHCJW", "BBRHPJW", "BBRHCJR", "BBRHPJR" ),
    "HEURES CREUSES": ( "DEMAIN", "PEJP", "EJPHN", "EJPHPM", "BBRHCJB", "BBRHPJB", "BBRHCJW", "BBRHPJW", "BBRHCJR", "BBRHPJR" ),
    "EJP": ( "DEMAIN", "HHPHC", "HCHP","HCHC", "BBRHPJB", "BBRHCJW", "BBRHPJW", "BBRHCJR", "BBRHPJR"),
    "BBR": ( "HHPHC", "HCHP","HCHC", "PEJP", "EJPHN", "EJPHPM",)
}

def zlinky_version_infos(self, nwkid ):
    cluster_0000 = self.ListOfDevices.get(nwkid, {}).get("Ep",{}).get("01", {}).get("0000",{})
    
    date_build = cluster_0000.get("0006","")
    version_build = cluster_0000.get("4000","")
    
    self.logging("Debug", f"rest_zlinky - found date_build: {date_build} version_build {version_build}")  
    return date_build, version_build


def rest_zlinky(self, verb, data, parameters): 

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None

    self.logging( "Debug", "rest_zlinky - for %s %s %s" % (verb, data, parameters))
    # find if we have a ZLinky
    zlinky = []

    for nwkid in self.ListOfDevices:
        zlinky_datas = self.ListOfDevices[ nwkid ].get("ZLinky")
        if zlinky_datas is None:
            continue

        if "PROTOCOL Linky" not in zlinky_datas:
            continue
        if "OPTARIF" not in zlinky_datas and "LTARF" not in zlinky_datas:
            continue

        self.logging("Debug", "rest_zlinky - found %s " % (nwkid))

        tarif = "BASE"
        for _tarif in ZLINK_TARIF_MODE_EXCLUDE:
            if _tarif in zlinky_datas.get("OPTARIF",[]):
                tarif = _tarif
                break
            if _tarif in zlinky_datas.get("LTARF",[]):
                tarif = _tarif
                break

        self.logging("Debug", "rest_zlinky - Tarif %s " % (tarif))
  
        linky_mode = zlinky_datas["PROTOCOL Linky"]
        version_info = zlinky_version_infos(self, nwkid )
        
        device = {
            'Nwkid': nwkid,
            'ZDeviceName': get_device_nickname( self, NwkId=nwkid),
            "PROTOCOL Linky": linky_mode,
            'Parameters': [
                {"DateCode": version_info[0]},
                {"SWBuildID": version_info[1]},
            ]
        }
        self.logging("Debug", "rest_zlinky - Linky Mode  %s " %linky_mode)
        self.logging("Debug", "rest_zlinky - Linky Tarif %s " %tarif)
        self.logging("Debug", "rest_zlinky - Linky DateCode %s " % version_info[0])
        self.logging("Debug", "rest_zlinky - Linky Version %s " %version_info[1])

        for zlinky_param in ZLINKY_PARAMETERS[ linky_mode ]:
            if zlinky_param not in zlinky_datas:
                self.logging("Debug", "rest_zlinky - Exclude  %s " % (zlinky_param)) 
                continue

            if zlinky_param in ZLINK_TARIF_MODE_EXCLUDE[ tarif ]:
                self.logging("Debug", "rest_zlinky - Exclude  %s " % (zlinky_param)) 
                continue

            if zlinky_param == "STGE":
                for x in zlinky_datas[ "STGE"]:
                    device["Parameters"].append( { f"STGE: {x}": zlinky_datas["STGE"][x] } )
                continue

            attr_value = zlinky_datas[ zlinky_param ]
            if zlinky_param in ZLINKY_INDEXES:
                attr_value = int(attr_value) / 1000

            device["Parameters"].append( { zlinky_param: attr_value } )

        zlinky.append( device )

    self.logging("Debug", "rest_zlinky - Read to send  %s " % (zlinky))  

    if verb == "GET" and len(parameters) == 0:
        if self.fake_mode():
            _response["Data"] = json.dumps(fake_zlinky_histo_mono(), sort_keys=True)
            return _response

        _response["Data"] = json.dumps(zlinky, sort_keys=True)
    return _response


def fake_zlinky_histo_mono():

    return [
        {
            "Nwkid": "abcd",
            "PROTOCOL Linky": 0,
            "Parameters": [
                { "OPTARIF": "BASE" },
                { "DEMAIN": "" },
                { "HHPHC": 0 },
                { "PEJP": 0 },
                { "ADPS": "0" }
            ],
            "ZDeviceName": "ZLinky"
        }
    ]
