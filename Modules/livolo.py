#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_output.py

    Description: All communications towards Zigate

"""

import Domoticz
from Classes.LoggingManagement import LoggingManagement
from Zigbee.zclCommands import zcl_level_move_to_level, zcl_toggle

from Modules.domoMaj import MajDomoDevice
from Modules.tools import retreive_cmd_payload_from_8002
from Modules.zigateConsts import ZIGATE_EP

# Livolo commands.
#
# - looks like when Livolo switch is comming it is sending a Read Attribute to the Zigate on cluster 0x0001 Attributes: 0x895e, 0x1802, 0x4b00, 0x0012, 0x0021. In a malformed packet
#
# - In order to bind the Livolo do:
# (1) Send a Toggle
# (2) Move to level 108 with transition 0.1 seconds
# (3) Move to level 108 with transition 0.1 seconds
# (4) Move to level 108 with transition 0.1 seconds
#
# - When receiving 0x0001/0x0007 we must update the MacCapa attributes, accordingly to Mains (Single Phase)


def livolo_bind(self, nwkid, EPout):

    livolo_OnOff(self, nwkid, EPout, "All", "Toggle")
    livolo_OnOff(self, nwkid, EPout, "Left", "On")
    livolo_OnOff(self, nwkid, EPout, "Left", "On")
    livolo_OnOff(self, nwkid, EPout, "Left", "On")


def livolo_OnOff(self, nwkid, EPout, devunit, onoff):
    """
    Levolo On/Off command are based on Level Control cluster
    Level: 108/0x6C  -> On
    Level: 1/0x01 -> Off
    Left Unit: Timing 1
    Right Unit: Timing 2
    """

    self.log.logging("Livolo", "Debug", "livolo_OnOff - devunit: %s, onoff: %s" % (devunit, onoff), nwkid=nwkid)

    if onoff not in ("On", "Off", "Toggle"):
        return
    if devunit not in ("Left", "Right", "All"):
        return

    if onoff == "Toggle" and devunit == "All":
        self.log.logging("Livolo", "Debug", "livolo_toggle", nwkid=nwkid)
        zcl_toggle(self, nwkid, EPout)
    else:
        level_value = timing_value = None
        if onoff == "On":
            level_value = "%02x" % 108
        elif onoff == "Off":
            level_value = "%02x" % 1

        if devunit == "Left":
            timing_value = "0001"
        elif devunit == "Right":
            timing_value = "0002"

        if level_value is not None and timing_value is not None:
            self.log.logging(
                "Livolo",
                "Debug",
                "livolo_OnOff - %s/%s Level: %s, Timing: %s" % (nwkid, EPout, level_value, timing_value),
                nwkid=nwkid,
            )
            zcl_level_move_to_level( self, nwkid, EPout, "00", level_value, timing_value)
            #sendZigateCmd(self, "0081", "02" + nwkid + ZIGATE_EP + EPout + "00" + level_value + timing_value)
        else:
            Domoticz.Error("livolo_OnOff - Wrong parameters sent ! onoff: %s devunit: %s" % (onoff, devunit))


def livoloReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):

    # Domoticz.Log("livoloReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s" \
    #        %(srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload))

    # At Device Annoucement 0x00 and 0x05 are sent by device

    default_response, GlobalCmd, SQN, ManufacturerCode, Command, Data = retreive_cmd_payload_from_8002(MsgPayload)

    if Command == "00":  # Read Attribute request with On/Off status
        OnOff = Data[-2:]


def livolo_read_attribute_request(self, Devices, NwkId, Ep, Status):
    # What is expected on the Widget is:
    # Left Off: 00
    # Left On: 01
    # Right Off: 02
    # Right On: 03

    self.log.logging("Livolo", "Debug", "Decode0100 - Livolo %s/%s Data: %s" % (NwkId, Ep, Status), NwkId)

    if Status == "00":  # Left / Single - Off
        MajDomoDevice(self, Devices, NwkId, Ep, "0006", "00")
    elif Status == "01":  # Left / Single - On
        MajDomoDevice(self, Devices, NwkId, Ep, "0006", "01")

    if Status == "02":  # Right - Off
        MajDomoDevice(self, Devices, NwkId, Ep, "0006", "10")
    elif Status == "03":  # Right - On
        MajDomoDevice(self, Devices, NwkId, Ep, "0006", "11")

    self.ListOfDevices[NwkId]["Ep"][Ep]["0006"]["0000"] = Status


def livolo_onoff_status(self, Devices, nwkid, ep, onoff):

    if nwkid not in self.ListOfDevices:
        return
    if "Ep" not in self.ListOfDevices[nwkid]:
        return
    if ep not in self.ListOfDevices[nwkid]["Ep"]:
        return
    if "0006" not in self.ListOfDevices[nwkid]["Ep"][ep]:
        return
    #if onoff == "00":  # Left / Single - Off
    #    # MajDomoDevice(self, Devices, nwkid, ep, '0006', '00')
    #    pass
    #elif onoff == "01":  # Left / Single - On
    #    # MajDomoDevice(self, Devices, nwkid, ep, '0006', '01')
    #    pass
    #if onoff == "02":  # Right - Off
    #    # MajDomoDevice(self, Devices, nwkid, ep, '0006', '10')
    #    pass
    #elif onoff == "03":  # Right - On
    #    # MajDomoDevice(self, Devices, nwkid, ep, '0006', '11')
    #    pass
    # self.ListOfDevices[MsgSrcAddr]['Ep'][ep]['0006']['0000'] = MsgStatus
