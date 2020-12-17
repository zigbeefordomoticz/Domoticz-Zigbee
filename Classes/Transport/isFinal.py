
# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz


from Modules.zigateConsts import ZIGATE_COMMANDS, ADDRESS_MODE
from Classes.Transport.tools import CMD_ONLY_STATUS, CMD_NWK_2NDBytes

# These are ZiGate commands which doesn't have Ack/Nack with firmware up to 3.1c
CMD_NOACK_ZDP = (0x0030, 0x0031, 0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045,
                 0x0046, 0x0047, 0x0049, 0x004A, 0x004B, 0x004E, 0x0530, 0x0531, 0x0532, 0x0533)

def is_final_step( self, isqn, step):
    # Step is 0x8000
    if step == 0x8000 and self.ListOfCommands[ isqn ]['cmd'] in CMD_ONLY_STATUS:
        return True
    cmd = int(self.ListOfCommands[ isqn ]['cmd'], 16)

    if is_nowait_cmd( self, isqn, cmd):
        return True

    if not is_8011_expected_after_8000( self, isqn, cmd ) and not is_8012_expected_after_8000( self, isqn, cmd ): 
        return True

    if step == 0x8012:
        return is_final_step_8012( self, isqn, cmd)

    self.logging_receive( 'Log', "is_final_step - returning False by default Cmd: 0x%04d" %cmd)
    return False

def is_final_step_8012(self, isqn, cmd):
    if cmd in ZIGATE_COMMANDS:
        return is_8011_expected_after_8012( self, isqn, cmd )
    self.logging_receive( 'Log', "is_final_step_8012 - returning False by default Cmd: 0x%04d" %cmd)


def is_8011_expected_after_8000( self, isqn, cmd ):
    if cmd in ZIGATE_COMMANDS:
        return ZIGATE_COMMANDS[ cmd ]['Ack']
    self.logging_receive( 'Log', "is_8011_expected_after_8000 - returning False by default Cmd: 0x%04d" %cmd)
    return False


def is_8012_expected_after_8000( self, isqn, cmd ):
    if cmd in ZIGATE_COMMANDS:
        return ZIGATE_COMMANDS[ cmd ]['8012']
    self.logging_receive( 'Log', "is_8012_expected_after_8000 - returning False by default Cmd: 0x%04d" %cmd)
    return False


def is_8011_expected_after_8012( self, isqn, cmd ):
    expAck = ZIGATE_COMMANDS[ cmd ]['Ack']
    ackIsDisabled =  self.ListOfCommands[ isqn ]['ackIsDisabled']
    return bool(ackIsDisabled or not expAck)

def is_nowait_cmd( self, isqn, cmd):
    if cmd not in CMD_NWK_2NDBytes:
        if cmd == 0x004E and self.ListOfCommands[ isqn ]['datas'][0:4] == '0000':
            return True

        if cmd == 0x0049 and self.ListOfCommands[ isqn ]['datas'][0:4] == 'FFFC':
           return True

    if cmd in CMD_NWK_2NDBytes:
        if self.ListOfCommands[ isqn ]['datas'][0:2] == '%02x' % ADDRESS_MODE['group'] and self.ListOfCommands[ isqn ]['datas'][2:6] == '0000':
            return True
            
        if self.ListOfCommands[ isqn ]['datas'][2:6] == '0000':
            return True

        if not self.firmware_with_aps_sqn and cmd == 0x0110:
            return True

    if not self.firmware_with_aps_sqn and cmd in CMD_NOACK_ZDP:
        return True