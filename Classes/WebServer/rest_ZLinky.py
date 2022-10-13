import json

import Domoticz
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
    "BASE": ( "PTEC", "DEMAIN", "HHPHC", "HCHP","HCHC", "PEJP", "EJPHN", "EJPHPM", "BBRHCJB", "BBRHPJB", "BBRHCJW", "BBRHPJW", "BBRHCJR", "BBRHPJR" ),
    "HC": ( "DEMAIN", "PEJP", "EJPHN", "EJPHPM", "BBRHCJB", "BBRHPJB", "BBRHCJW", "BBRHPJW", "BBRHCJR", "BBRHPJR" ),
    "EJP": ( "DEMAIN", "HHPHC", "HCHP","HCHC", "BBRHPJB", "BBRHCJW", "BBRHPJW", "BBRHCJR", "BBRHPJR"),
    "BBR": ( "HHPHC", "HCHP","HCHC", "PEJP", "EJPHN", "EJPHPM",)
}


ZLINKY_STEG_ATTRIBUTS = (
    'Contact sec ',
    'Organe de coupure ',
    'État du cache-bornes distributeur',
    'Surtension sur une des phases ',
    'Dépassement de la puissance de référence',
    'Fonctionnement producteur/consommateur',
    'Sens énergie active ',
    'Tarif en cours sur le contrat fourniture',
    'Tarif en cours sur le contrat distributeur',
    'Mode dégradée horloge',
    'État de la sortie télé-information ',
    'État de la sortie communication',
    'Statut du CPL ',
    'Synchronisation CPL ',
    'Couleur du jour',
    'Couleur du lendemain',
    'Préavis pointes mobiles ',
    'Pointe mobile ',
)
def zlinky_version_infos(self, nwkid ):

    date_build = version_build = ''
    # Retreive Build time
    if 'SWBUILD_1' in self.ListOfDevices[ nwkid ]:
        date_build = self.ListOfDevices[ nwkid ]['SWBUILD_1' ]
    # Retreive Version number
    if 'SWBUILD_3' in self.ListOfDevices[ nwkid ]:
        version_build = self.ListOfDevices[ nwkid ]['SWBUILD_3' ]
    
    return date_build, version_build
        
    



def rest_zlinky(self, verb, data, parameters): 

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None

    self.logging("Debug", "rest_zlinky - for %s %s %s" % (verb, data, parameters))  
    # find if we have a ZLinky
    zlinky = []

    for nwkid in self.ListOfDevices:
        if 'ZLinky' not in self.ListOfDevices[ nwkid ]:
            continue
        if "PROTOCOL Linky" not in self.ListOfDevices[ nwkid ]['ZLinky']:
            continue
        if "OPTARIF" not in self.ListOfDevices[ nwkid ]['ZLinky']:
            continue

        self.logging("Debug", "rest_zlinky - found %s " % (nwkid))  
        tarif = "BASE"
        for _tarif in ZLINK_TARIF_MODE_EXCLUDE:
            if _tarif in self.ListOfDevices[ nwkid ]['ZLinky'][ "OPTARIF"]:
                tarif = _tarif
                break

        linky_mode = self.ListOfDevices[ nwkid ]["ZLinky"]["PROTOCOL Linky"]
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
            if zlinky_param not in self.ListOfDevices[ nwkid ]["ZLinky"]:
                self.logging("Debug", "rest_zlinky - Exclude  %s " % (zlinky_param)) 
                continue
            if zlinky_param in ZLINK_TARIF_MODE_EXCLUDE[ tarif ]:
                self.logging("Debug", "rest_zlinky - Exclude  %s " % (zlinky_param)) 
                continue
            if zlinky_param == "STGE":
                #for x in self.ListOfDevices[ nwkid ]["ZLinky"][ "STGE"]:
                #    device["Parameters"].append( { x: self.ListOfDevices[ nwkid ]["ZLinky"]["STGE"][x] } )
                continue

            attr_value = self.ListOfDevices[ nwkid ]["ZLinky"][ zlinky_param ]
            if zlinky_param in ZLINKY_INDEXES:
                attr_value = int(attr_value) / 1000

            device["Parameters"].append( { zlinky_param: attr_value } )
            
        zlinky.append( device )
      
    self.logging("Debug", "rest_zlinky - Read to send  %s " % (zlinky))  

    if verb == "GET" and len(parameters) == 0:
        if len(self.ControllerData) == 0:
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
