

from Modules.zigbeeVersionTable import ZNP_MODEL


# ZNP
def znp_extract_versioning_for_plugin(self, znp_model, znp_manuf):
    # CC1352/CC2652, Z-Stack 3.30+ (build 20211217)
    ZNP_330 = "CC1352/CC2652, Z-Stack 3.30+"
    ZNP_30X = "CC2531, Z-Stack 3.0.x"

    self.log.logging("TransportZigpy", "Debug", "extract_versioning_for_plugin Model: %s Manuf: %s" % (znp_model, znp_manuf))

    firmware_branch = next((ZNP_MODEL[x] for x in ZNP_MODEL if znp_model[:len(x)] == x), "99")

    firmware_major_version = znp_model[znp_model.find("build") + 8: -5]
    firmware_version = znp_model[znp_model.find("build") + 10: -1]
    build = znp_model[znp_model.find("Z-Stack"):]

    self.log.logging("TransportZigpy", "Debug", "extract_versioning_for_plugin %s %s %s %s" % (firmware_branch, firmware_major_version, firmware_version, build))
    return firmware_branch, firmware_major_version, firmware_version, build


# Bellows

def bellows_extract_versioning_for_plugin(self, brd_manuf, brd_name, version):
    self.log.logging("TransportZigpy", "Log", "bellows_extract_versioning_for_plugin Manuf: %s Name: %s Version: %s" % (brd_manuf, brd_name, version))
    
    firmware_branch = "98"  # Not found in the Table.
    
    if brd_manuf and brd_manuf.lower() == 'elelabs':
        if 'elu01' in brd_name.lower():
            firmware_branch = "31"
        elif 'elr02' in brd_name.lower():
            firmware_branch = "30"

    # 6.10.3.0 build 297
    firmware_major_version = "%02d" % int(version[:2].replace('.', ''))
    firmware_version = "%04d" % int(version[2:8].replace(' ', '').replace('.', ''))

    return firmware_branch, firmware_major_version, firmware_version

# deConz
def deconz_extract_versioning_for_plugin(self, deconz_model, deconz_manuf, version):
    self.log.logging("TransportZigpy", "Debug", "deconz_extract_versioning_for_plugin Manuf: %s Name: %s Version: %s" % (deconz_manuf, deconz_model, "0x%08x" % version))

    model_mapping = {
        "conbee ii": "40",
        "raspbee ii": "41",
        "raspbee": "42",
        "conbee": "43"
    }

    deconz_version = "0x%08x" % version
    return model_mapping.get(deconz_model.lower(), "97"), deconz_version