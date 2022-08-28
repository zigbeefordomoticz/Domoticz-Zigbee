
from Modules.pluginDbAttributes import STORE_CONFIGURE_REPORTING, STORE_READ_CONFIGURE_REPORTING

ZLINK_CONF_MODEL = (
    "ZLinky_TIC",
    "ZLinky_TIC-historique-mono" , "ZLinky_TIC-historique-tri",
    "ZLinky_TIC-standard-mono", "ZLinky_TIC-standard-tri",
    "ZLinky_TIC-standard-mono-prod", "ZLinky_TIC-standard-tri-prod"
    )

ZLINKY_MODE = {
    0: { "Mode": ('historique', 'mono'), "Conf": "ZLinky_TIC-historique-mono" },
    1: { "Mode": ('standard', 'mono'), "Conf": "ZLinky_TIC-standard-mono" },
    2: { "Mode": ('historique', 'tri'), "Conf": "ZLinky_TIC-historique-tri" },
    3: { "Mode": ('standard', 'tri'), "Conf": "ZLinky_TIC-standard-tri" },
    5: { "Mode": ('standard', 'mono prod'), "Conf": "ZLinky_TIC-standard-mono-prod" },
    7: { "Mode": ('standard', 'tri prod'), "Conf": "ZLinky_TIC-standard-tri-prod" },
}

ZLinky_TIC_COMMAND = {
    # Mode Historique
    "0000": "OPTARIF",
    "0001": "DEMAIN",
    "0002": "HHPHC",
    "0003": "PPOT",
    "0004": "PEJP",
    "0005": "ADPS",
    "0006": "ADIR1",
    "0007": "ADIR2",
    "0008": "ADIR3",

    # Mode standard
    "0200": "LTARF",
    "0201": "NTARF",
    "0202": "DATE",
    "0203": "EASD01",
    "0204": "EASD02",
    "0205": "EASD03",
    "0206": "EASD04",
    "0207": "SINSTI",
    "0208": "SMAXIN",
    "0209": "SMAXIN-1",
    "0210": "CCAIN",
    "0211": "CCAIN-1",
    "0212": "SMAXN-1",
    "0213": "SMAXN2-1",
    "0214": "SMAXN3-1",
    "0215": "MSG1",
    "0216": "MSG2",
    "0217": "STGE",
    "0218": "DPM1",
    "0219": "FPM1",
    "0220": "DPM2",
    "0221": "FPM2",
    "0222": "DPM3",
    "0223": "FPM3",
    "0224": "RELAIS",
    "0225": "NJOURF",
    "0226": "NJOURF+1",
    "0227": "PJOURF+1",
    "0228": "PPOINTE1",
    "0300": "PROTOCOL Linky"
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

    if self.ListOfDevices[ nwkid ]["Model"] != zlinky_conf:
        self.log.logging( "ZLinky", "Status", "Adjusting ZLinky model from %s to %s" %(
            self.ListOfDevices[ nwkid ]["Model"],
            zlinky_conf 
        ))
        
        # Looks like we have to update the Model in order to use the right attributes
        self.ListOfDevices[ nwkid ]["Model"] = zlinky_conf

        # Read Attribute has to be redone from scratch
        if "ReadAttributes" in self.ListOfDevices[nwkid]:
            del self.ListOfDevices[nwkid]["ReadAttributes"]

        if 'ZLinky' in self.ListOfDevices[ nwkid ]:
            del self.ListOfDevices[ nwkid ]['ZLinky']

        # Configure Reporting to be done
        if STORE_CONFIGURE_REPORTING in self.ListOfDevices[nwkid]:
            del self.ListOfDevices[nwkid][STORE_CONFIGURE_REPORTING]

        if STORE_READ_CONFIGURE_REPORTING in self.ListOfDevices[nwkid]:
            del self.ListOfDevices[nwkid][STORE_READ_CONFIGURE_REPORTING]
            
        if self.configureReporting:
            self.configureReporting.check_configuration_reporting_for_device( nwkid, force=True)
            
        if "Heartbeat" in self.ListOfDevices[nwkid]:
            self.ListOfDevices[nwkid]["Heartbeat"] = "0"