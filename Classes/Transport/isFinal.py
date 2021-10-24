# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz


from Modules.zigateConsts import ZIGATE_COMMANDS, ADDRESS_MODE
from Classes.Transport.tools import CMD_ONLY_STATUS, CMD_NWK_2NDBytes

# These are ZiGate commands which doesn't have Ack/Nack with firmware up to 3.1c
CMD_NOACK_ZDP = (
    0x0030,
    0x0031,
    0x0040,
    0x0041,
    0x0042,
    0x0043,
    0x0044,
    0x0045,
    0x0046,
    0x0047,
    0x0049,
    0x004A,
    0x004B,
    0x004E,
    0x0530,
    0x0531,
    0x0532,
    0x0533,
)


def is_final_step(self, isqn, step):

    cmd = int(self.ListOfCommands[isqn]["cmd"], 16)
    # Step is 0x8000
    if step == 0x8000 and (self.ListOfCommands[isqn]["cmd"] in CMD_ONLY_STATUS or self.firmware_nosqn):
        return True

    if self.firmware_compatibility_mode:
        if self.ListOfCommands[isqn]["ackIsDisabled"]:
            return True
        if step == 0x8000 and cmd in (0x0100, 0x0110):
            # with firmware 31a we just sync on Response of 0100 -> 8102 and 0110 -> 8110
            return False
        return True

    if is_nowait_cmd(self, isqn, cmd):
        return True

    if step == 0x8012 and not self.firmware_compatibility_mode:
        return is_final_step_8012(self, isqn, cmd)

    if not self.firmware_with_8012 and is_ackIsDisabled(self, isqn, cmd):
        # If we are in a firmware below 31d (included) there is no 0x8012.
        # If we have a command sent with no-ack (like address mode 0x07),
        # then we will assumed that once 0x8000 is received, we can move to next command.
        return True

    if not self.firmware_with_8012 and is_group_cmd(self, isqn, cmd):
        # This is a Group command. There is no Ack expected.
        return True

    if not is_8012_expected_after_8000(self, isqn, cmd) and not is_8011_expected_after_8000(self, isqn, cmd):
        return True

    # self.logging_receive( 'Debug', "is_final_step - returning False by default Cmd: 0x%04x - %s %s %s %s" %
    #    (
    #    cmd,
    #    self.firmware_with_8012,
    #    is_8012_expected_after_8000( self, isqn, cmd ),
    #    is_8011_expected_after_8000( self, isqn, cmd ),
    #    is_8011_expected_after_8012( self, isqn, cmd )
    #    ))
    return False


def is_final_step_8012(self, isqn, cmd):
    if cmd in ZIGATE_COMMANDS:
        if is_group_cmd(self, isqn, cmd):
            return True
        return is_8011_expected_after_8012(self, isqn, cmd)
    # self.logging_receive( 'Debug', "is_final_step_8012 - returning False by default Cmd: 0x%04d" %cmd)
    return False


def is_8011_expected_after_8000(self, isqn, cmd):
    if cmd in ZIGATE_COMMANDS:
        return ZIGATE_COMMANDS[cmd]["Ack"]
    # self.logging_receive( 'Debug', "is_8011_expected_after_8000 - returning False by default Cmd: 0x%04d" %cmd)
    return False


def is_8012_expected_after_8000(self, isqn, cmd):
    if cmd in ZIGATE_COMMANDS:
        return ZIGATE_COMMANDS[cmd]["8012"]
    # self.logging_receive( 'Debug', "is_8012_expected_after_8000 - returning False by default Cmd: 0x%04d" %cmd)
    return False


def is_8011_expected_after_8012(self, isqn, cmd):
    expAck = ZIGATE_COMMANDS[cmd]["Ack"]
    ackIsDisabled = self.ListOfCommands[isqn]["ackIsDisabled"]
    return bool(ackIsDisabled or not expAck)


def is_ackIsDisabled(self, isqn, cmd):

    # In firmware 31c and below, 0x0110 is always with Ack
    if not self.firmware_with_aps_sqn and cmd in (0x0110,):
        return False

    # In firmware 31d and below 0x0530 is always without Ack
    if not self.firmware_with_8012 and cmd in (0x0530,):
        return True

    return bool(self.ListOfCommands[isqn]["ackIsDisabled"])


def is_group_cmd(self, isqn, cmd):
    return cmd in CMD_NWK_2NDBytes and self.ListOfCommands[isqn]["datas"][0:2] == "01"


def is_nowait_cmd(self, isqn, cmd):
    if cmd not in CMD_NWK_2NDBytes:
        if cmd == 0x004E and self.ListOfCommands[isqn]["datas"][0:4] == "0000":
            return True
        if cmd == 0x0049 and self.ListOfCommands[isqn]["datas"][0:4] == "FFFC":
            return True

    if cmd in CMD_NWK_2NDBytes:
        if (
            self.ListOfCommands[isqn]["datas"][0:2] == "%02x" % ADDRESS_MODE["group"]
            and self.ListOfCommands[isqn]["datas"][2:6] == "0000"
        ):
            return True
        if self.ListOfCommands[isqn]["datas"][2:6] == "0000":
            return True
        if not self.firmware_with_aps_sqn and cmd == 0x0110:
            return True
    if not self.firmware_with_aps_sqn and cmd in CMD_NOACK_ZDP:
        return True
