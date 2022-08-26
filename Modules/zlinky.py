
from Modules.pluginDbAttributes import STORE_CONFIGURE_REPORTING

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
        # Let check if we have in the Cluster infos
        if "Ep" not in self.ListOfDevices[ nwkid ]:
            return "ZLinky_TIC"
        if "01" not in self.ListOfDevices[ nwkid ]["Ep"]:
            return "ZLinky_TIC"
        if "ff66" not in self.ListOfDevices[ nwkid ]["Ep"]["01"]:
            return "ZLinky_TIC"
        if "0300" not in self.ListOfDevices[ nwkid ]["Ep"]["01"]["ff66"]:
            return "ZLinky_TIC"
        if self.ListOfDevices[ nwkid ]["Ep"]["01"]["ff66"]["0300"] not in ZLINKY_MODE:
            return "ZLinky_TIC"

        mode = self.ListOfDevices[ nwkid ]["Ep"]["01"]["ff66"]["0300"]
        return ZLINKY_MODE[ mode ]["Conf"]

    if 'PROTOCOL Linky' not in self.ListOfDevices[ nwkid ]['ZLinky']:
        return "ZLinky_TIC"

    if self.ListOfDevices[ nwkid ]['ZLinky']['PROTOCOL Linky'] not in ZLINKY_MODE:
        return "ZLinky_TIC"

    return ZLINKY_MODE[ self.ListOfDevices[ nwkid ]['ZLinky']['PROTOCOL Linky'] ]["Conf"]
    

def update_zlinky_device_model_if_needed( self, nwkid ):
    
    if "Model" not in self.ListOfDevices[ nwkid ]:
        return

    zlinky_conf = linky_device_conf(self, nwkid)

    if self.ListOfDevices[ nwkid ]["model"] != zlinky_conf:
        self.logging( "ZLinky", "Status", "Adjusting ZLinky model from %s to %s" %(
            self.ListOfDevices[ nwkid ]["model"],
            zlinky_conf 
        ))
        
        # Looks like we have to update the Model in order to use the right attributes
        self.ListOfDevices[ nwkid ]["model"] = zlinky_conf

        # Read Attribute has to be redone from scratch
        if "ReadAttributes" in self.ListOfDevices[nwkid]:
            del self.ListOfDevices[nwkid]["ReadAttributes"]

        if 'ZLinky' in self.ListOfDevices[ nwkid ]:
            del self.ListOfDevices[ nwkid ]['ZLinky']

        # Configure Reporting to be done
        if STORE_CONFIGURE_REPORTING in self.ListOfDevices[nwkid]:
            del self.ListOfDevices[nwkid][STORE_CONFIGURE_REPORTING]

        if self.configureReporting:
            self.configureReporting.check_configuration_reporting_for_device( nwkid, force=True)