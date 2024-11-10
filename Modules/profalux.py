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

"""
    Module: profalux.py

    Description: 

"""


from Modules.pluginDbAttributes import STORE_CONFIGURE_REPORTING
from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import get_and_inc_ZCL_SQN
from Modules.zigateConsts import ZIGATE_EP
from Zigbee.zclCommands import zcl_configure_reporting_requestv2


def profalux_fake_deviceModel(self, nwkid):

    """
    This method is called when in pairing process and the Manufacturer code is Profalux ( 0x1110 )
    The purpose will be to create a fake Model Name in order to use the Certified Device Conf
    """

    if nwkid not in self.ListOfDevices:
        return

    if "ZDeviceID" not in self.ListOfDevices[nwkid]:
        return

    if "ProfileID" not in self.ListOfDevices[nwkid]:
        return

    if "MacCapa" not in self.ListOfDevices[nwkid]:
        return

    if "Manufacturer" not in self.ListOfDevices[nwkid]:
        return

    if "Model" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Model"] in ( "MOT-C1Z06C", "MOT-C1Z06F", ):
        # No needs as we have a model Name ;-)
        return
    
    if self.ListOfDevices[nwkid]["Manufacturer"] != "1110":
        return

    self.ListOfDevices[nwkid]["Manufacturer Name"] = "Profalux"

    location = ""
    if (
        "Ep" in self.ListOfDevices[nwkid]
        and "01" in self.ListOfDevices[nwkid]["Ep"]
        and "0000" in self.ListOfDevices[nwkid]["Ep"]["01"]
        and "0010" in self.ListOfDevices[nwkid]["Ep"]["01"]["0000"]
    ):
        location = self.ListOfDevices[nwkid]["Ep"]["01"]["0000"]["0010"]

    if self.ListOfDevices[nwkid]["MacCapa"] == "8e" and self.ListOfDevices[nwkid]["ZDeviceID"] == "0200":

        # Main Powered device => Volet or BSO
        self.ListOfDevices[nwkid]["Model"] = "VoletBSO-Profalux"

        if location in ("BSO", "bso", "Bso"):
            # We found a BSO in attrbute 0010
            self.ListOfDevices[nwkid]["Model"] = "BSO-Profalux"

        elif location in ("VOLET", "volet", "Volet"):
            # We found a VR
            self.ListOfDevices[nwkid]["Model"] = "Volet-Profalux"

        self.log.logging(
            "Profalux",
            "Debug",
            "++++++ Model Name for %s forced to : %s due to location: %s"
            % (nwkid, self.ListOfDevices[nwkid]["Model"], location),
            nwkid,
        )

    elif self.ListOfDevices[nwkid]["MacCapa"] == "80":

        # Batterie Device => Remote command
        self.ListOfDevices[nwkid]["Model"] = "Telecommande-Profalux"

        self.log.logging(
            "Profalux",
            "Debug",
            "++++++ Model Name for %s forced to : %s" % (nwkid, self.ListOfDevices[nwkid]["Model"]),
            nwkid,
        )


def checkAndTriggerConfigReporting(self, NwkId):

    self.log.logging("Profalux", "Debug", "-- -- checkAndTriggerConfigReporting for %s" % NwkId)
    if STORE_CONFIGURE_REPORTING not in self.ListOfDevices[NwkId]:
        configureReportingForprofalux(self, NwkId)
        return
    if "01" not in self.ListOfDevices[NwkId][STORE_CONFIGURE_REPORTING]["Ep"]:
        configureReportingForprofalux(self, NwkId)
        return
    if "fc21" not in self.ListOfDevices[NwkId][STORE_CONFIGURE_REPORTING]["Ep"]["01"]:
        configureReportingForprofalux(self, NwkId)
        return
    if self.ListOfDevices[NwkId][STORE_CONFIGURE_REPORTING]["Ep"]["01"]["fc21"] == {}:
        configureReportingForprofalux(self, NwkId)
        return


def configureReportingForprofalux(self, NwkId):

    self.log.logging("Profalux", "Debug", "-- -- -- configureReportingForprofalux for %s" % NwkId)
    if NwkId not in self.ListOfDevices:
        return

    attribute_reporting_configuration = {}
    attribute_reporting_record = {
        "Attribute": "0001",
        "DataType": "20",
        "minInter": "0000",
        "maxInter": "0000",
        "rptChg": "00",
        "timeOut": "0000",
    }
    attribute_reporting_configuration.append(attribute_reporting_record)

    #datas = "02" + NwkId + ZIGATE_EP + "01" + "fc21" + "00" + "01" + "1110" + "01" + attrList
    #zcl_configure_reporting_request(self, NwkId, ZIGATE_EP, "01", "fc21", "00", "01", "1110", "01", attrList)
    
    i_sqn = zcl_configure_reporting_requestv2(
        self,
        NwkId,
        ZIGATE_EP,
        "01",
        "fc21",
        "00",
        "01",
        "1110",
        attribute_reporting_configuration,
    )

    #sendZigateCmd(self, "0120", datas)
    #self.log.logging("Profalux", "Debug", "-- -- -- configureReportingForprofalux for %s data: %s" % (NwkId, datas))


def profalux_stop(self, nwkid):

    # determine which Endpoint
    EPout = "01"
    for tmpEp in self.ListOfDevices[nwkid]["Ep"]:
        if "0008" in self.ListOfDevices[nwkid]["Ep"][tmpEp]:
            EPout = tmpEp

    cluster_frame = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    cmd = "03"  # Ask the Tilt Blind to stop moving

    payload = cluster_frame + sqn + cmd
    raw_APS_request(self, nwkid, EPout, "0008", "0104", payload, zigate_ep=ZIGATE_EP)
    self.log.logging("Profalux", "Debug", "profalux_stop ++++ %s/%s payload: %s" % (nwkid, EPout, payload), nwkid)


def profalux_MoveToLevelWithOnOff(self, nwkid, level):

    # determine which Endpoint
    EPout = "01"
    for tmpEp in self.ListOfDevices[nwkid]["Ep"]:
        if "0008" in self.ListOfDevices[nwkid]["Ep"][tmpEp]:
            EPout = tmpEp

    cluster_frame = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    cmd = "04"  # Ask the Tilt Blind to go to a certain Level

    payload = cluster_frame + sqn + cmd + "%02x" % level
    raw_APS_request(self, nwkid, EPout, "0008", "0104", payload, zigate_ep=ZIGATE_EP)
    self.log.logging(
        "Profalux",
        "Debug",
        "profalux_MoveToLevelWithOnOff ++++ %s/%s Level: %s payload: %s" % (nwkid, EPout, level, payload),
        nwkid,
    )


def profalux_MoveWithOnOff(self, nwkid, OnOff):

    if OnOff not in [0x00, 0x01]:
        return

    # determine which Endpoint
    EPout = "01"
    for tmpEp in self.ListOfDevices[nwkid]["Ep"]:
        if "0008" in self.ListOfDevices[nwkid]["Ep"][tmpEp]:
            EPout = tmpEp

    cluster_frame = "11"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    cmd = "05"  # Ask the Tilt Blind to open or Close

    payload = cluster_frame + sqn + cmd + "%02x" % OnOff
    raw_APS_request(self, nwkid, EPout, "0008", "0104", payload, zigate_ep=ZIGATE_EP)
    self.log.logging(
        "Profalux",
        "Debug",
        "profalux_MoveWithOnOff ++++ %s/%s OnOff: %s payload: %s" % (nwkid, EPout, OnOff, payload),
        nwkid,
    )


def profalux_MoveToLiftAndTilt(self, nwkid, level=None, tilt=None):

    def getLevel(self, nwkid):
        # Initialize level to None
        level = None

        # Retrieve nested dictionary values
        ep = self.ListOfDevices.get(nwkid, {}).get("Ep", {}).get("01", {}).get("0008", {})

        # Check and convert the level if available
        level_value = ep.get("0000")
        if level_value is not None:
            level = int(level_value, 16) if isinstance(level_value, str) else level_value
        return level

    def getTilt(self, nwkid):
        tilt = 45

        device = self.ListOfDevices.get(nwkid, {})
        param = device.get("Param", {})
        if "profaluxOrientBSO" in param:
            tilt = param["profaluxOrientBSO"]

        ep = device.get("Ep", {}).get("01", {}).get("fc21", {})
        tilt_value = ep.get("0001")
        if tilt_value is not None and isinstance(tilt_value, str):
            tilt_value = int(tilt_value, 16)

        return tilt_value


    def setLevel(self, nwkid, level):
        device = self.ListOfDevices[nwkid]
        ep = device.setdefault("Ep", {})
        ep_01 = ep.setdefault("01", {})
        ep_01_0008 = ep_01.setdefault("0008", {})
        ep_01_0008["0000"] = level


    def setTilt(self, nwkid, tilt):
        device = self.ListOfDevices[nwkid]
        ep = device.setdefault("Ep", {})
        ep_01 = ep.setdefault("01", {})
        ep_fc21 = ep_01.setdefault("fc21", {})
        ep_fc21["0001"] = f"{tilt:02x}"

    # Begin
    self.log.logging(
        "Profalux", "Debug", "profalux_MoveToLiftAndTilt Nwkid: %s Level: %s Tilt: %s" % (nwkid, level, tilt)
    )
    if level is None and tilt is None:
        return

    # Disabled until 3.1c
    # checkAndTriggerConfigReporting( self, nwkid)
    if level is None:
        level = getLevel(self, nwkid)

    if tilt is None:
        tilt = getTilt(self, nwkid)

    self.log.logging(
        "Profalux",
        "Debug",
        "profalux_MoveToLiftAndTilt after update Nwkid: %s Level: %s Tilt: %s" % (nwkid, level, tilt),
    )

    # determine which Endpoint
    EPout = "01"

    # Cluster Frame:
    #  Frame Type: Cluster Command (1)
    #  Manufacturer Specific True
    #  Command Direction: Client to Server (0)
    #  Disable default response: false
    #  Reserved : 0x00
    cluster_frame = "05"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    cmd = "10"  # Propriatary Command: Ask the Tilt Blind to go to a Certain Position and Orientate to a certain angle

    # compute option 0x01 level, 0x02 tilt, 0x03 level + tilt
    if level is not None and tilt is not None:
        option = 0x03
    elif tilt is not None:
        option = 0x02
        level = 0x00
    elif level is not None:
        option = 0x01
        tilt = 0x00

    setTilt(self, nwkid, tilt)
    setLevel(self, nwkid, level)

    # payload: 11 45 10 03 55 2d ffff
    # Option Parameter uint8   Bit0 Ask for lift action, Bit1 Ask fr a tilt action
    # Lift Parameter   uint8   Lift value between 1 to 254
    # Tilt Parameter   uint8   Tilt value between 0 and 90
    # Transition Time  uint16  Transition Time between current and asked position

    ManfufacturerCode = "1110"

    payload = (
        cluster_frame
        + ManfufacturerCode[2:4]
        + ManfufacturerCode[0:2]
        + sqn
        + cmd
        + "%02x" % option
        + "%02x" % level
        + "%02x" % tilt
        + "FFFF"
    )
    self.log.logging(
        "Profalux",
        "Debug",
        "profalux_MoveToLiftAndTilt %s ++++ %s %s/%s level: %s tilt: %s option: %s payload: %s"
        % (cluster_frame, sqn, nwkid, EPout, level, tilt, option, payload),
        nwkid,
    )
    raw_APS_request(self, nwkid, "01", "0008", "0104", payload, zigate_ep=ZIGATE_EP)
