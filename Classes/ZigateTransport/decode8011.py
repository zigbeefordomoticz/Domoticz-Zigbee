# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import time

from Classes.ZigateTransport.sqnMgmt import sqn_get_internal_sqn_from_aps_sqn
from Classes.ZigateTransport.tools import print_listofcommands, release_command


def decode8011(self, decoded_frame):

    MsgData = decoded_frame[12 : len(decoded_frame) - 4]
    if MsgData is None:
        return None

    MsgStatus = MsgData[0:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSrcEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]

    MsgSEQ = "00"
    if len(MsgData) <= 12:
        return

    MsgSEQ = MsgData[12:14]

    if MsgStatus == "00":
        self.statistics._APSAck += 1

    else:
        self.statistics._APSNck += 1
        self.last_nwkid_failure = MsgSrcAddr

    if not self.firmware_with_aps_sqn:  # Firmware < 31d
        # We do not use 8011 for sync and will rely only on receiving message
        return

    isqn = sqn_get_internal_sqn_from_aps_sqn(self, MsgSEQ)

    if isqn is None:
        # self.logging_8011( 'Debug', "decode8011 - 0x8011 not for us NwkId: %s eSqn: %s" %(MsgSrcAddr, MsgSEQ))
        return

    if isqn not in self.ListOfCommands:
        # self.logging_8011( 'Debug', "decode8011 - 0x8011 not for us Nwkid: %s eSqn: %s iSqn: %s" %(MsgSrcAddr, MsgSEQ, isqn))
        return

    self.ListOfCommands[isqn]["Status"] = "8011"
    report_timing_8011(self, isqn)
    print_listofcommands(self, isqn)

    release_command(self, isqn)


def report_timing_8011(self, isqn):
    # Statistics on ZiGate reacting time to process the command
    if self.pluginconf.pluginConf["ZiGateReactTime"]:
        timing = 0
        if isqn in self.ListOfCommands and "TimeStamp" in self.ListOfCommands[isqn]:
            TimeStamp = self.ListOfCommands[isqn]["TimeStamp"]
            timing = int((time.time() - TimeStamp) * 1000)
            self.statistics.add_timing8011(timing)
        if self.statistics._averageTiming8011 != 0 and timing >= (3 * self.statistics._averageTiming8011):
            self.logging_8011(
                "Log",
                "Zigate round trip 0x8011 time seems long. %s ms for %s %s SendingQueue: %s"
                % (
                    timing,
                    self.ListOfCommands[isqn]["cmd"],
                    self.ListOfCommands[isqn]["datas"],
                    self.loadTransmit(),
                ),
            )
