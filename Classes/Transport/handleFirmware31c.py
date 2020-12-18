# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
from Modules.zigateConsts import ZIGATE_COMMANDS
from Classes.Transport.tools import get_response_from_command, CMD_WITH_RESPONSE, release_command, print_listofcommands
from Classes.Transport.sqnMgmt import TYPE_APP_ZCL, TYPE_APP_ZDP


def check_and_process_others_31c(self, MsgType, MsgData):
    
    MsgZclSqn = MsgData[0:2]
    MsgNwkId = MsgData[2:6]
    MsgEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]

    self.statistics._data += 1
    # There is a probability that we get an ASYNC message, which is not related to a Command request.
    # In that case we should just process this message.

    # For now we assume that we do only one command at a time, so either it is an Async message,
    # or it is related to the command

    if len(self.ListOfCommands) == 0:
        # No command send, this is a async message, just release
        return

    isqn = self.ListOfCommands.keys()[0]

    print_listofcommands( self, isqn )
    
    cmd_in_pipe = self.ListOfCommands[ isqn ]['cmd']
    exp_response = get_response_from_command(  cmd_in_pipe )

    if exp_response is None:
        self.logging_receive('Log', "check_and_process_others_31c  - Command not found in ZIGATE_COMMANDS %s" %cmd_in_pipe)
        return
    
    if int(MsgType, 16) != exp_response:
        self.logging_receive('Log', "check_and_process_others_31c  - Async incoming PacketType")
        return 

    release_command( self, isqn)