

from Modules.zigbeeVersionTable import ZNP_MODEL


# ZNP
def znp_extract_versioning_for_plugin( self, znp_model, znp_manuf):
    # CC1352/CC2652, Z-Stack 3.30+ (build 20211217)
    ZNP_330 = "CC1352/CC2652, Z-Stack 3.30+"
    ZNP_30X = "CC2531, Z-Stack 3.0.x"

    self.log.logging("TransportZigpy", "Log","extract_versioning_for_plugin Model: %s Manuf: %s" %( znp_model, znp_manuf))
                 
    FirmwareBranch = next((ZNP_MODEL[x] for x in ZNP_MODEL if znp_model[: len(x)] == x), "99")

    FirmwareMajorVersion = znp_model[ znp_model.find("build") + 8 : -5 ]
    FirmwareVersion = znp_model[ znp_model.find("build") + 10: -1]
    build = znp_model[ znp_model.find("Z-Stack"): ]

    self.log.logging("TransportZigpy", "Log","extract_versioning_for_plugin %s %s %s %s" %(FirmwareBranch, FirmwareMajorVersion, FirmwareVersion, build))
    return FirmwareBranch, FirmwareMajorVersion, FirmwareVersion, build


# Bellows
def bellows_extract_versioning_for_plugin( self, brd_manuf, brd_name, version):
    
    self.log.logging("TransportZigpy", "Log","bellows_extract_versioning_for_plugin Manuf: %s Name: %s Version: %s" %( brd_manuf, brd_name, version))
    FirmwareBranch = "98"   # Not found in the Table.
    if brd_manuf == 'Elelabs':
        if 'ELU01' in brd_name:
            FirmwareBranch = "31"
        elif 'ELR02' in brd_name:
            FirmwareBranch = "30" 
            
    # 6.10.3.0 build 297    
    FirmwareMajorVersion = (version[: 2])
    FirmwareMajorVersion = "%02d" %int(FirmwareMajorVersion.replace('.',''))
    FirmwareVersion = version[ 2:8]
    FirmwareVersion = FirmwareVersion.replace(' ','')
    FirmwareVersion = "%04d" %int(FirmwareVersion.replace('.',''))
        
    return FirmwareBranch, FirmwareMajorVersion, FirmwareVersion


# deConz
def deconz_extract_versioning_for_plugin( self, deconz_model, deconz_manuf, version):
    self.log.logging("TransportZigpy", "Log","deconz_extract_versioning_for_plugin Manuf: %s Name: %s Version: %s" %( deconz_manuf, deconz_model, version))
        
    deconz_version = "0x%08x" %version
    
    if deconz_model == "ConBee II":
        return "40", deconz_version
        
    elif deconz_model == "RaspBee II":
        return "41", deconz_version
    
    elif deconz_model == "RaspBee":
        return "42", deconz_version
    
    elif deconz_model == "ConBee":
        return "43", deconz_version

    return "97", deconz_version
