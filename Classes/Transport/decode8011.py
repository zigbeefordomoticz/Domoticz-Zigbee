# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

from Classes.Transport.tools import release_command, print_listofcommands
from Classes.Transport.sqnMgmt import sqn_get_internal_sqn_from_aps_sqn

def decode8011( self, decoded_frame):

    MsgData = decoded_frame[12:len(decoded_frame) - 4]
    MsgStatus = MsgData[0:2]
    MsgSrcAddr = MsgData[2:6]
    MsgSrcEp = MsgData[6:8]
    MsgClusterId = MsgData[8:12]

    MsgSEQ = '00'
    if len(MsgData) <= 12:
        return

    MsgSEQ = MsgData[12:14]

    if MsgData is None:
        return None

    if MsgStatus == '00':
        self.statistics._APSAck += 1
    else:
        self.statistics._APSNck += 1

    if not self.firmware_with_aps_sqn:  # Firmware < 31d
        # We do not use 8011 for sync and will rely only on receiving message
        return

    isqn = sqn_get_internal_sqn_from_aps_sqn(self, MsgSEQ)

    if isqn is None:
        self.logging_receive( 'Log', "decode8011 - 0x8011 not for us eSqn: %s" %MsgSEQ)
        return

    if isqn not in self.ListOfCommands:
        self.logging_receive( 'Log', "decode8011 - 0x8011 not for us eSqn: %s iSqn: %s" %(MsgSEQ, isqn))
        return
    
    print_listofcommands( self, isqn )

    self.ListOfCommands[ isqn ]['Status'] = '8011'
    release_command( self, isqn)
