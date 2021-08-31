# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
import Domoticz

from Modules.zigateConsts import ZIGATE_COMMANDS, MAX_SIMULTANEOUS_ZIGATE_COMMANDS
from Classes.Transport.tools import (
    get_response_from_command,
    CMD_WITH_RESPONSE,
    release_command,
    print_listofcommands,
    is_nwkid_available,
    get_nwkid_from_datas_for_zcl_command,
)
from Classes.Transport.sqnMgmt import TYPE_APP_ZCL, TYPE_APP_ZDP, sqn_get_internal_sqn_from_app_sqn


def decode8011_31c(self, msgtype, decoded_frame):

    MsgData = decoded_frame[12 : len(decoded_frame) - 4]
    MsgSQN = MsgData[0:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSrcEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]

    if len(self.ListOfCommands) == 0:
        # No command send, this is a async message, just release
        return

    if self.semaphore_gate._value == MAX_SIMULTANEOUS_ZIGATE_COMMANDS:
        return

    isqn = sqn_get_internal_sqn_from_app_sqn(self, MsgSQN, TYPE_APP_ZCL)
    self.logging_receive("Debug", "decode8011_31c -  isqn: %s from esqn: %s" % (isqn, MsgSQN))
    if isqn in self.ListOfCommands:
        cmd = int(self.ListOfCommands[isqn]["cmd"], 16)
        if is_nwkid_available(self, cmd) and get_nwkid_from_datas_for_zcl_command(self, isqn) != MsgSrcAddr:
            self.logging_receive("Debug", "decode8011_31c -  Command found ==> release %s" % (isqn))
            self.ListOfCommands[isqn]["Status"] = msgtype
            print_listofcommands(self, isqn)
            release_command(self, isqn)
            return

    for isqn in list(self.ListOfCommands.keys()):
        cmd = int(self.ListOfCommands[isqn]["cmd"], 16)
        if not is_nwkid_available(self, cmd):
            continue
        if get_nwkid_from_datas_for_zcl_command(self, isqn) != MsgSrcAddr:
            continue
        self.ListOfCommands[isqn]["Status"] = msgtype
        print_listofcommands(self, isqn)
        release_command(self, isqn)
