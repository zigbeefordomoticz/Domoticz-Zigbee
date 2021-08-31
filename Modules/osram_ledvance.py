#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author:  pipiche38
#   French translation: @martial83
#
"""
    Module: osram_ledvance.py

    Description: Widget management

"""

from Classes.LoggingManagement import LoggingManagement

from Modules.basicOutputs import write_attribute
from Modules.readAttributes import ReadAttributeRequest_0006_400x
from Modules.tools import is_ack_tobe_disabled


def setPowerOn_OnOff(self, key, OnOffMode=0xFF):

    # OSRAM/LEDVANCE
    # 0xfc0f --> Command 0x01
    # 0xfc01 --> Command 0x01

    # Tested on Ikea Bulb without any results !
    POWERON_MODE = (0x00, 0x01, 0xFE)  # Off  # On  # Previous state

    if "Manufacturer" in self.ListOfDevices[key]:
        manuf_spec = "01"
        manuf_id = self.ListOfDevices[key]["Manufacturer"]
    else:
        manuf_spec = "00"
        manuf_id = "0000"

    EPin = "01"
    EPout = "01"
    for tmpEp in self.ListOfDevices[key]["Ep"]:
        if "0006" in self.ListOfDevices[key]["Ep"][tmpEp]:
            EPout = tmpEp
            cluster_id = "0006"
            attribute = "4003"
            data_type = "30"  #
            data = "ff"
            data = "%02x" % OnOffMode if OnOffMode in POWERON_MODE else "%02x" % 255
            self.log.logging(
                "Output", "Debug", "set_PowerOn_OnOff for %s/%s - OnOff: %s" % (key, EPout, OnOffMode), key
            )
            write_attribute(
                self,
                key,
                "01",
                EPout,
                cluster_id,
                manuf_id,
                manuf_spec,
                attribute,
                data_type,
                data,
                ackIsDisabled=is_ack_tobe_disabled(self, key),
            )
            ReadAttributeRequest_0006_400x(self, key)

        # if '0008' in self.ListOfDevices[key]['Ep'][tmpEp]:
        #    EPout=tmpEp
        #    cluster_id = "0008"
        #    attribute = "4000"
        #    data_type = "20" #
        #    data = "ff"
        #    if OnOffMode in POWERON_MODE:
        #        data = "%02x" %OnOffMode
        #    else:
        #        data = "%02x" %0xff
        #        data = "%02x" %0xff
        #    self.log.logging( "Output", 'Log', "set_PowerOn_OnOff for %s/%s - OnOff: %s" %(key, EPout, OnOffMode), key)
        #    retreive_ListOfAttributesByCluster( self, key, EPout, '0008')

        # if '0300' in self.ListOfDevices[key]['Ep'][tmpEp]:
        #    EPout=tmpEp
        #    cluster_id = "0300"
        #    attribute = "4010"
        #    data_type = "21" #
        ##    data = "ffff"
        #    if OnOffMode in POWERON_MODE:
        #        data = "%04x" %OnOffMode
        #    else:
        #        data = "%04x" %0xffff
        #        data = "%02x" %0xff
        #    self.log.logging( "Output", 'Log', "set_PowerOn_OnOff for %s/%s - OnOff: %s" %(key, EPout, OnOffMode), key)
        #    retreive_ListOfAttributesByCluster( self, key, EPout, '0300')
