#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

from Modules.basicOutputs import write_attribute
from Modules.domoMaj import MajDomoDevice
from Modules.tools import is_ack_tobe_disabled
from Modules.zigateConsts import ZIGATE_EP


def pollingOrvibo(self, key):

    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """
    return False


def callbackDeviceAwake_Orvibo(self, Devices, NwkId, EndPoint, cluster):

    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part
    """

    return


def orviboReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):

    if srcNWKID not in self.ListOfDevices:
        self.log.logging("Orvibo", "Error", "%s not found in Database" %srcNWKID)
        return
    if "Model" not in self.ListOfDevices[srcNWKID]:
        return

    _Model = self.ListOfDevices[srcNWKID]["Model"]
    if ClusterID != "0017":
        self.log.logging("Orvibo", "Error", "orviboReadRawAPS - unexpected ClusterId %s for NwkId: %s" % (ClusterID, srcNWKID))
        return

    FrameControlFiled = MsgPayload[:2]

    if FrameControlFiled == "19":
        sqn = MsgPayload[2:4]
        cmd = MsgPayload[4:6]
        data = MsgPayload[6:]

    if cmd == "08":
        button = data[:2]
        action = data[4:6]

        BUTTON_MAP = {
            # d0d2422bbf3a4982b31ea843bfedb559
            "d0d2422bbf3a4982b31ea843bfedb559": {
                "01": 1,  # Top
                "02": 2,  # Middle
                "03": 3,  # Bottom
            },
            # Interupteur Autocolalant /
            "3c4e4fc81ed442efaf69353effcdfc5f": {
                "03": 10,  # Top Left,
                "0b": 20,  # Middle Left
                "07": 30,  # Top Right
                "0f": 40,  # Mddle Right
            },
        }

        ACTIONS_MAP = {
            "00": 1,  # Click
            "02": 2,  # Long Click
            "03": 3,  # Release
        }

        self.log.logging("Orvibo", "Debug", "button: %s, action: %s" %(button, action))

        if action in ACTIONS_MAP and button in BUTTON_MAP[_Model]:
            selector = BUTTON_MAP[_Model][button] + ACTIONS_MAP[action]
            self.log.logging("Orvibo", "Debug", "---> Selector: %s" %selector)
            MajDomoDevice(self, Devices, srcNWKID, "01", "0006", selector)


def OrviboRegistration(self, nwkid):

    cluster = "0000"
    attribute = "0099"
    datatype = "20"
    value = "01"

    EPout = "01"
    for tmpEp in self.ListOfDevices[nwkid]["Ep"]:
        if "0000" in self.ListOfDevices[nwkid]["Ep"][tmpEp]:
            EPout = tmpEp

    # Set Commissioning as Done
    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "0000"
    Hattribute = "0099"
    data_type = "20"  # Bool
    data = "01"

    self.log.logging("Orvibo", "Debug", "Orvibo registration for %s" % nwkid)
    write_attribute(
        self,
        nwkid,
        ZIGATE_EP,
        EPout,
        cluster_id,
        manuf_id,
        manuf_spec,
        Hattribute,
        data_type,
        data,
        ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
    )
