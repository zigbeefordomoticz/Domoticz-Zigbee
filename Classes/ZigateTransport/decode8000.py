# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import time

from Classes.ZigateTransport.isFinal import is_final_step
from Classes.ZigateTransport.sqnMgmt import (TYPE_APP_ZCL, TYPE_APP_ZDP,
                                             sqn_add_external_sqn)
from Classes.ZigateTransport.tools import (CMD_PDM_ON_HOST, ZIGATE_COMMANDS,
                                           get_isqn_from_ListOfCommands,
                                           print_listofcommands,
                                           release_command, update_xPDU)


def decode8000(self, decoded_frame):

    MsgData = decoded_frame[12 : len(decoded_frame) - 4]

    Status = MsgData[0:2]
    sqn_app = MsgData[2:4]
    PacketType = MsgData[4:8]

    if PacketType == "":
        return None

    sqn_aps, type_sqn, apdu, npdu = get_sqn_pdus(self, MsgData)

    # Look for isqn
    isqn = get_isqn_from_ListOfCommands(self, PacketType)
    if isqn is None:
        context = {
            "Error code": "TRANS-8000-01",
            "EncodedData": str(MsgData),
            "PacketType": PacketType,
            "Status": Status,
            "sqn_app": sqn_app,
            "sqn_aps": sqn_aps,
            "sqn_typ": type_sqn,
        }
        self.logging_8000("Error", "decode8000 - cannot get isqn for MsgType %s" % (PacketType), _context=context)
        return

    print_listofcommands(self, isqn)

    # Sanity Check
    if int(self.ListOfCommands[isqn]["cmd"], 16) != int(PacketType, 16):
        context = {
            "Error code": "TRANS-8000-02",
            "EncodedData": str(MsgData),
            "PacketType": PacketType,
            "Status": Status,
            "sqn_app": sqn_app,
            "sqn_aps": sqn_aps,
            "sqn_typ": type_sqn,
        }
        self.logging_8000( "Error",
            "decode8000 - command miss-match %s vs. %s" % (self.ListOfCommands[isqn]["cmd"], PacketType),
            _context=context,
        )
        return

    # self.logging_send('Debug', "--> decode8000 - Status: %s PacketType: %s sqn_app:%s sqn_aps: %s type_sqn: %s"
    #    % (Status, PacketType, sqn_app, sqn_aps, type_sqn))

    if int(PacketType, 16) in CMD_PDM_ON_HOST:
        release_command(self, isqn)
        return None

    report_timing_8000(self, isqn)

    if Status != "00":
        self.statistics._ackKO += 1
        # Migh check here is retry can be done !
        release_command(self, isqn)
        return

    # Status is '00' -> Valid command sent !
    self.statistics._ack += 1

    # is there any followup to be done ?
    if is_final_step(self, isqn, 0x8000):
        release_command(self, isqn)
        return

    # We should expect 0x8011 or 0x8012 or 0x8702 or a message (if we are firmware 31c)
    # Update isqn
    self.ListOfCommands[isqn]["SQN_APP"] = sqn_app
    self.ListOfCommands[isqn]["SQN_APS"] = sqn_aps
    self.ListOfCommands[isqn]["SQN_TYP"] = type_sqn
    update_isqn(self, int(PacketType, 16), isqn, sqn_app, sqn_aps, type_sqn)
    self.ListOfCommands[isqn]["Status"] = "8000"

    print_listofcommands(self, isqn)


def update_isqn(self, cmd, isqn, sqn_app, sqn_aps, type_sqn):

    if ZIGATE_COMMANDS[cmd]["Layer"] == "ZCL":
        sqn_add_external_sqn(self, isqn, sqn_app, TYPE_APP_ZCL, sqn_aps)

    elif ZIGATE_COMMANDS[cmd]["Layer"] == "ZDP":
        sqn_add_external_sqn(self, isqn, sqn_app, TYPE_APP_ZDP, sqn_aps)


def get_sqn_pdus(self, MsgData):
    sqn_aps = None
    type_sqn = None
    apdu = npdu = None

    if len(MsgData) == 8:
        # Firmware 31a
        self.firmware_compatibility_mode = True
        self.firmware_with_aps_sqn = False
        self.firmware_with_8012 = False

    elif len(MsgData) >= 12:
        # New Firmware 3.1d (get aps sqn)
        type_sqn = MsgData[8:10]
        sqn_aps = MsgData[10:12]

        if len(MsgData) == 16:
            # Firmware 31e
            npdu = MsgData[12:14]
            apdu = MsgData[14:16]
            update_xPDU(self, npdu, apdu)

            if not self.firmware_with_8012:
                self.firmware_compatibility_mode = False
                self.firmware_with_aps_sqn = True
                self.firmware_with_8012 = True
                self.logging_8000("Status", "==> Transport Mode switch to full mode")

        elif not self.firmware_with_aps_sqn:
            self.firmware_compatibility_mode = False
            self.firmware_with_aps_sqn = True
            self.logging_8000("Status", "==> Transport Mode switch to: half mode ( no 8012)")

    return (sqn_aps, type_sqn, apdu, npdu)


def report_timing_8000(self, isqn):
    # Statistics on ZiGate reacting time to process the command
    timing = 0
    if self.pluginconf.pluginConf["ZiGateReactTime"]:
        if isqn in self.ListOfCommands and "TimeStamp" in self.ListOfCommands[isqn]:
            TimeStamp = self.ListOfCommands[isqn]["TimeStamp"]
            timing = int((time.time() - TimeStamp) * 1000)
            self.statistics.add_timing8000(timing)
        if self.statistics._averageTiming8000 != 0 and timing >= (3 * self.statistics._averageTiming8000):
            self.logging_8000(
                "Log",
                "--> decode8000 - Zigate round trip 0x8000 time seems long. %s ms for %s %s SendingQueue: %s"
                % (timing, self.ListOfCommands[isqn]["cmd"], self.ListOfCommands[isqn]["datas"], self.loadTransmit()),
            )
