FIRMWARE_BRANCH = {
    "00": "Production",
    "01": "Beta",
    "11": "ZiGate (znp)",
    "20": "CC1352/CC2652, Z-Stack 3.30+ (znp)",
    "21": "CC2531, Z-Stack 3.0.x (znp)",
    "22": "CC2531, Z-Stack Home 1.2 (znp",
    "30": "Elelabs, ELR02x",
    "31": "Elelabs, ELU01x",
    
    "99": "Unknown"
}

ZNP_MODEL = {
    "CC1352/CC2652, Z-Stack 3.30+": "20",
    "CC2531, Z-Stack 3.0.x":        "21",
    "CC2531, Z-Stack Home 1.2":     "22",
    "Elelabs, ELR02x":              "30",
    "Elelabs, ELU01x":              "31",
}


def set_display_firmware_version( self ):

    if 0 <= int(self.ControllerData["Branch Version"]) < 20:   
        self.pluginParameters["DisplayFirmwareVersion"] = "Zig - %s" % self.ControllerData["Minor Version"] 
        
    elif 20 <= int(self.ControllerData["Branch Version"]) < 30:
        # ZNP
        self.pluginParameters["DisplayFirmwareVersion"] = "Znp - (....%s)" % self.ControllerData["Minor Version"] 

    elif 30 <= int(self.ControllerData["Branch Version"]) < 40:   
        # Silicon Labs
        self.pluginParameters["DisplayFirmwareVersion"] = "Ezsp - %s.%s" %(
            self.ControllerData["Major Version"] , self.ControllerData["Minor Version"] )
        
    else:
        self.pluginParameters["DisplayFirmwareVersion"] = "UNK - %s" % self.ControllerData["Minor Version"] 

