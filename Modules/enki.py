#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
from Modules.basicOutputs import set_poweron_afteroffon
from Modules.readAttributes import ReadAttributeRequest_0006_400x

ENKI_POWERON_MODE = {0x00: "Off", 0x01: "On", 0xFF: "Previous state"}  # Off  # On  # Previous state


def enki_set_poweron_after_offon(self, mode):
    # call from WebServer

    if mode not in ENKI_POWERON_MODE:
        self.log.logging("Enki", "Error", "enki_set_poweron_after_offon - Unknown mode: %s" % mode)

    for nwkid in self.ListOfDevices:
        enki_set_poweron_after_offon_device(self, mode, nwkid)


def enki_set_poweron_after_offon_device(self, mode, nwkid):
    if "Manufacturer" not in self.ListOfDevices[nwkid]:
        return
    if self.ListOfDevices[nwkid]["Manufacturer"] != "1277":
        return
    # We have a Enki device
    if "01" not in self.ListOfDevices[nwkid]["Ep"]:
        return
    if "0006" not in self.ListOfDevices[nwkid]["Ep"]["01"]:
        return
    if "4003" not in self.ListOfDevices[nwkid]["Ep"]["01"]["0006"]:
        self.log.logging("Enki", "Debug", "enki_set_poweron_after_offon Device: %s do not have a Set Power Attribute !" % nwkid)
        ReadAttributeRequest_0006_400x(self, nwkid)
        return

    # At that stage, we have a Philips device with Cluster 0006 and the right attribute
    self.log.logging("Enki", "Debug", "enki_set_poweron_after_offon - Set PowerOn after OffOn of %s to %s" % (
        nwkid, ENKI_POWERON_MODE[mode]) )
    set_poweron_afteroffon(self, nwkid, OnOffMode=mode)
    ReadAttributeRequest_0006_400x(self, nwkid)
