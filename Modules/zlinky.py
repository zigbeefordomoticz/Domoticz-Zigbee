

ZLINKY_MODE = {
    0: { "Mode": ('historique', 'mono'), "Conf": "ZLinky_TIC-historique-mono" },
    1: { "Mode": ('standard', 'mono'), "Conf": "ZLinky_TIC-standard-mono" },
    2: { "Mode": ('historique', 'tri'), "Conf": "ZLinky_TIC-historique-tri" },
    3: { "Mode": ('standard', 'tri'), "Conf": "ZLinky_TIC-standard-tri" },
    5: { "Mode": ('standard', 'mono prod'), "Conf": "" },
    7: { "Mode": ('standard', 'tri prod'), "Conf": "" },
}

def linky_mode( self, nwkid ):
    
    if 'ZLinky' not in self.ListOfDevices[ nwkid ]:
        return 
    
    if 'PROTOCOL Linky' not in self.ListOfDevices[ nwkid ]['ZLinky']:
        return
    
    if self.ListOfDevices[ nwkid ]['ZLinky']['PROTOCOL Linky'] in ZLINKY_MODE:
        return ZLINKY_MODE[ self.ListOfDevices[ nwkid ]['ZLinky']['PROTOCOL Linky'] ]["Mode"]

    return None

def linky_device_conf(self, nwkid):
    
    if 'ZLinky' not in self.ListOfDevices[ nwkid ]:
        return "ZLinky_TIC-historique-tri"
    
    if 'PROTOCOL Linky' not in self.ListOfDevices[ nwkid ]['ZLinky']:
        return "ZLinky_TIC-historique-tri"
    
    if self.ListOfDevices[ nwkid ]['ZLinky']['PROTOCOL Linky'] in ZLINKY_MODE:
        return ZLINKY_MODE[ self.ListOfDevices[ nwkid ]['ZLinky']['PROTOCOL Linky'] ]["Conf"]

    return "ZLinky_TIC-historique-tri"
    
