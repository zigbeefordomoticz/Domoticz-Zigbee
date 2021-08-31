# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import time
from Classes.Transport.tools import release_command, update_xPDU, print_listofcommands
from Classes.Transport.sqnMgmt import sqn_get_internal_sqn_from_aps_sqn
from Classes.Transport.isFinal import is_final_step


def decode8012_8702(self, decoded_frame):

    MsgType = decoded_frame[2:6]
    MsgData = decoded_frame[12 : len(decoded_frame) - 4]
    MsgStatus = MsgData[0:2]
    unknown2 = MsgData[2:6]
    MsgDataDestMode = MsgData[6:8]

    MsgSQN = MsgAddr = None
    if MsgDataDestMode == "03":  # IEEE
        MsgAddr = MsgData[8:24]
        MsgSQN = MsgData[24:26]
        nPDU = MsgData[26:28]
        aPDU = MsgData[28:30]
    elif MsgDataDestMode in ("02", "07", "01"):  # Short Address/Group
        MsgAddr = MsgData[8:12]
        MsgSQN = MsgData[12:14]
        nPDU = MsgData[14:16]
        aPDU = MsgData[16:18]
    else:
        _context = {
            "Error code": "TRANS-8012-01",
            "DecodeFrame": str(decoded_frame),
            "Status": MsgStatus,
            "AddrMode": MsgDataDestMode,
        }
        self.logging_receive_error("decode8012_8702 - wrong address mode %s" % (MsgDataDestMode), context=_context)
        return None

    update_xPDU(self, nPDU, aPDU)

    isqn = sqn_get_internal_sqn_from_aps_sqn(self, MsgSQN)
    # self.logging_receive( 'Debug', "decode8012_8702 - 0x8012 isqn: %s eSqn: %s" %(isqn, MsgSQN))

    if isqn is None:
        # self.logging_receive( 'Debug', "decode8012_8702 - 0x8012 not for us Nwkid: %s eSqn: %s" %(MsgAddr, MsgSQN))
        if self.pluginconf.pluginConf["debugzigateCmd"]:
            self.logging_receive(
                "Log",
                "Transport - [%s] - Async %s Sqn: %s Addr: %s nPdu: %s aPdu: %s"
                % (isqn, MsgType, MsgSQN, MsgAddr, nPDU, aPDU),
            )
        return

    if isqn not in self.ListOfCommands:
        # self.logging_receive( 'Debug', "decode8012_8702 - 0x8012 not for us Nwkid: %s eSqn: %s " %(MsgAddr, MsgSQN))
        if self.pluginconf.pluginConf["debugzigateCmd"]:
            self.logging_receive(
                "Log",
                "Transport - [%s] - Async %s Sqn: %s Addr: %s nPdu: %s aPdu: %s"
                % (isqn, MsgType, MsgSQN, MsgAddr, nPDU, aPDU),
            )
        return

    self.ListOfCommands[isqn]["Status"] = MsgType

    report_timing_8012(self, isqn)
    print_listofcommands(self, isqn)

    # if MsgType == '8702':
    #    release_command( self, isqn)
    #    return

    self.ListOfCommands[isqn]["Status"] = MsgType
    if is_final_step(self, isqn, 0x8012):
        release_command(self, isqn)


def report_timing_8012(self, isqn):
    # Statistics on ZiGate reacting time to process the command
    if self.pluginconf.pluginConf["ZiGateReactTime"]:
        timing = 0
        if isqn in self.ListOfCommands and "TimeStamp" in self.ListOfCommands[isqn]:
            TimeStamp = self.ListOfCommands[isqn]["TimeStamp"]
            timing = int((time.time() - TimeStamp) * 1000)
            self.statistics.add_timing8012(timing)
        if self.statistics._averageTiming8012 != 0 and timing >= (3 * self.statistics._averageTiming8012):
            self.logging_send(
                "Log",
                "Zigate round trip 0x8012 time seems long. %s ms for %s %s SendingQueue: %s"
                % (
                    timing,
                    self.ListOfCommands[isqn]["cmd"],
                    self.ListOfCommands[isqn]["datas"],
                    self.loadTransmit(),
                ),
            )
