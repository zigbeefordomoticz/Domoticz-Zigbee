import json

import Domoticz
from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)





def rest_zlinky(self, verb, data, parameters): 

    _response = prepResponseMessage(self, setupHeadersResponse())
    _response["Data"] = None
    
    # find if we have a ZLinky
    zlinky = []
    
    for x in self.ListOfDevices:
        if 'ZLinky' not in self.ListOfDevices[ x ]:
            continue
        
        device = {
            'Nwkid': x,
            'Parameters': []
        }
        for y in self.ListOfDevices[ x ]["ZLinky"]:
            attr_name = '%s' %y
            attr_value = self.ListOfDevices[ x ]["ZLinky"][ y ]
            device["Parameters"].append( { attr_name: attr_value } )
            
        zlinky.append( device )
        
    if verb == "GET" and len(parameters) == 0:
        #if len(self.ControllerData) == 0:
        #    _response["Data"] = json.dumps(fake_list_casaia_ac201(), sort_keys=True)
        #    return _response

        _response["Data"] = json.dumps(zlinky, sort_keys=True)

    return _response