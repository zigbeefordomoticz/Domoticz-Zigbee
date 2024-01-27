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


from Modules.zigbeeVersionTable import ZNP_MODEL


# ZNP
def znp_extract_versioning_for_plugin( self, znp_model, znp_manuf):
    # CC1352/CC2652, Z-Stack 3.30+ (build 20211217)
    ZNP_330 = "CC1352/CC2652, Z-Stack 3.30+"
    ZNP_30X = "CC2531, Z-Stack 3.0.x"

    self.log.logging("TransportZigpy", "Log", "extract_versioning_for_plugin Model: %s Manuf: %s" %( znp_model, znp_manuf))
                 
    FirmwareBranch = next((ZNP_MODEL[x] for x in ZNP_MODEL if znp_model[: len(x)] == x), "99")

    FirmwareMajorVersion = znp_model[ znp_model.find("build") + 8 : -5 ]
    FirmwareVersion = znp_model[ znp_model.find("build") + 10: -1]
    build = znp_model[ znp_model.find("Z-Stack"): ]

    self.log.logging("TransportZigpy", "Log","extract_versioning_for_plugin %s %s %s %s" %(FirmwareBranch, FirmwareMajorVersion, FirmwareVersion, build))
    return FirmwareBranch, FirmwareMajorVersion, FirmwareVersion, build


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

# deConz
def deconz_extract_versioning_for_plugin(self, deconz_model, deconz_manuf, version):
    self.log.logging("TransportZigpy", "Debug", "deconz_extract_versioning_for_plugin Manuf: %s Name: %s Version: %s" % (deconz_manuf, deconz_model, "0x%08x" % version))

    model_mapping = {
        "conbee": "40",
        "conbee ii": "40",
        "raspbee ii": "41",
        "raspbee": "42",
        "conbee iii": "43"
    }

    deconz_version = "0x%08x" % version
    return model_mapping.get(deconz_model.lower(), "97"), deconz_version


# ZNP - for zigpy libs with watchdog
# def znp_extract_versioning_for_plugin(self, znp_model, znp_manuf, version):
#     #NodeInfo(nwk=0x0000, 
#     # ieee=00:12:4b:00:2a:1a:a7:35, 
#     # logical_type=<LogicalType.Coordinator: 0>, 
#     # model='CC2652', 
#     # manufacturer='Texas Instruments', 
#     # version='Z-Stack 20210708')
#     
#     self.log.logging("TransportZigpy", "Debug", "extract_versioning_for_plugin Model: %s Manuf: %s Version: %s" % (znp_model, znp_manuf, version))
# 
#     # It is assumed that the build is always on the right side in version
#     build = (''.join(char for char in reversed(version) if char.isdigit()))[::-1]
#     if "Z-Stack Home" in version:
#         firmware_branch = firmware_major_version = 22
#         firmware_version = "Z-Stack Home " + "(build %s)" %build
#         
#     if "Z-Stack 3.0.x" in version:
#         firmware_branch = firmware_major_version = 21
#         firmware_version = "Z-Stack 3.0.x " + "(build %s)" %build
#     else:
#         firmware_branch = firmware_major_version = ZNP_MODEL[ znp_model ]
#         firmware_version = "Z-Stack 3.30+ " + "(build %s)" %build
# 
#     self.log.logging("TransportZigpy", "Debug", "extract_versioning_for_plugin %s %s %s %s" % (
#         firmware_branch, firmware_major_version, firmware_version, build))
#     return firmware_branch, firmware_version, build
# 
# 
