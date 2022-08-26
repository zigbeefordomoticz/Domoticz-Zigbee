import json

import Domoticz
from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)
from Modules.tools import get_device_nickname
from Modules.zlinky import ZLINKY_MODE

ZLINKY_PARAMETERS = {
    0: ( 
        "ADC0", "BASE", "OPTARIF", "ISOUSC", "IMAX", "PTEC", "DEMAIN", "HHPHC", "PEJP", "ADPS", 
        ),
    2: ( 
        "ADC0", "BASE", "OPTARIF", "ISOUSC", "IMAX",
        "IMAX1", "IMAX2", "IMAX3", "PMAX", "PTEC", "DEMAIN", "HHPHC", "PPOT", "PEJP", "ADPS", "ADIR1", "ADIR2", "ADIR3" 
    ),
    
    1: (
        "ADSC", "NGTF", "LTARF", "NTARF", "DATE", "EAST", "EASF01", "EASF02", "EASF03", "EASF04", "EASF05", 
        "EASF06", "EASF07", "EASF08", "EASF09", "EASF10", "EASD01", "EASD02", "EASD03", "EASD04", "URMS1",
        "PREF", "STGE", "PCOUP",
        "MSG1", "MSG2", "PRM", "STGE", "DPM1", "FPM1", "DPM2", "FPM2", "DPM3", "FPM3", "RELAIS", "NJOURF", "NJOURF+1", "PJOURF+1", "PPOINTE1",
    ),
    
    3: (
        "ADSC", "NGTF", "LTARF", "NTARF", "DATE", "EAST", "EASF01", "EASF02", "EASF03", "EASF04", "EASF05", 
        "EASF06", "EASF07", "EASF08", "EASF09", "EASF10", "EASD01", "EASD02", "EASD03", "EASD04", "URMS1",
        "URMS2", "URMS3", "PREF", "STGE", "PCOUP",
        "MSG1", "MSG2", "PRM", "STGE", "DPM1", "FPM1", "DPM2", "FPM2", "DPM3", "FPM3", "RELAIS", "NJOURF", "NJOURF+1", "PJOURF+1", "PPOINTE1",
        ),

    5: (
        "ADSC", "NGTF", "LTARF", "NTARF", "DATE", "EAST", "EASF01", "EASF02", "EASF03", "EASF04", "EASF05", 
        "EASF06", "EASF07", "EASF08", "EASF09", "EASF10", "EASD01", "EASD02", "EASD03", "EASD04", "EAIT", "URMS1",
        "PREF", "STGE", "PCOUP", "SINSTI", "SMAXIN", "SMAXIN-1", "CCAIN", "CCAIN-1", "SMAXN-1", "SMAXN2-1", "SMAXN3-1", 
        "MSG1", "MSG2", "PRM", "STGE", "DPM1", "FPM1", "DPM2", "FPM2", "DPM3", "FPM3", "RELAIS", "NJOURF", "NJOURF+1", "PJOURF+1", "PPOINTE1",
    ),

    7: (
        "ADSC", "NGTF", "LTARF", "NTARF", "DATE", "EAST", "EASF01", "EASF02", "EASF03", "EASF04", "EASF05", 
        "EASF06", "EASF07", "EASF08", "EASF09", "EASF10", "EASD01", "EASD02", "EASD03", "EASD04", "EAIT", "URMS1",
        "URMS2", "URMS3", "PREF", "STGE", "PCOUP",
        "SINSTI", "SMAXIN", "SMAXIN-1", "CCAIN", "CCAIN-1", "SMAXN-1", "SMAXN2-1", "SMAXN3-1", 
        "MSG1", "MSG2", "PRM", "STGE", "DPM1", "FPM1", "DPM2", "FPM2", "DPM3", "FPM3", "RELAIS", "NJOURF", "NJOURF+1", "PJOURF+1", "PPOINTE1",
        ),
    
}

ZLINK_TARIF_MODE_EXCLUDE = {
    "BASE": ( "PTECT", "DEMAIN", "HCHP","HCHC", "EJPHN", "EJPHPM", "BBRHCJB", "BBRHPJB", "BBRHCJW", "BBRHPJW", "BBRHCJR", "BBRHPJR" ),
    "HC": ( "DEMAIN", "EJPHN", "EJPHPM", "BBRHCJB", "BBRHPJB", "BBRHCJW", "BBRHPJW", "BBRHCJR", "BBRHPJR" ),
    "EJP": ( "DEMAIN", "HCHP","HCHC", "BBRHPJB", "BBRHCJW", "BBRHPJW", "BBRHCJR", "BBRHPJR"),
    "BBR": ( "HCHP","HCHC", "EJPHN", "EJPHPM",)
}




def rest_zlinky(self, verb, data, parameters): 

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None

    # find if we have a ZLinky
    zlinky = []

    for nwkid in self.ListOfDevices:
        if 'ZLinky' not in self.ListOfDevices[ nwkid ]:
            continue
        if "PROTOCOL Linky" not in self.ListOfDevices[ nwkid ]['ZLinky']:
            return
        if "OPTARIF" not in self.ListOfDevices[ nwkid ]['ZLinky']:
            return

        tarif = "BASE"
        for _tarif in ZLINK_TARIF_MODE_EXCLUDE:
            if _tarif in self.ListOfDevices[ nwkid ]['ZLinky'][ "OPTARIF"]:
                tarif = _tarif
                break

        linky_mode = self.ListOfDevices[ nwkid ]["ZLinky"]["PROTOCOL Linky"]
        device = {
            'Nwkid': nwkid,
            'ZDeviceName': get_device_nickname( self, NwkId=nwkid),
            "PROTOCOL Linky": linky_mode,
            'Parameters': []
        }
        for y in ZLINKY_PARAMETERS[ linky_mode ]:
            if y not in self.ListOfDevices[ nwkid ]["ZLinky"]:
                continue
            if y in ZLINK_TARIF_MODE_EXCLUDE[ tarif ]:
                continue
    
            attr_value = self.ListOfDevices[ nwkid ]["ZLinky"][ y ]
            device["Parameters"].append( { y: attr_value } )
            
        zlinky.append( device )
        
    if verb == "GET" and len(parameters) == 0:
        if len(self.ControllerData) == 0:
            _response["Data"] = json.dumps(fake_zlinky_histo_mono(), sort_keys=True)
            return _response

        _response["Data"] = json.dumps(zlinky, sort_keys=True)

    return _response


def fake_zlinky_histo_mono():

    return [
        {
            "Nwkid": "5f21",
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
