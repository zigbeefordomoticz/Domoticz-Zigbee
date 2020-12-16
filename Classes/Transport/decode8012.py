# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

from Classes.Transport.tools import release_command, update_xPDU, print_listofcommands
from Classes.Transport.sqnMgmt import sqn_get_internal_sqn_from_aps_sqn
from Classes.Transport.isFinal import is_final_step

def decode8012_8702( self, decoded_frame):
    MsgType = decoded_frame[2:6]
    MsgData = decoded_frame[12:len(decoded_frame) - 4]
    MsgStatus = MsgData[0:2]
    unknown2 = MsgData[4:8]
    MsgDataDestMode = MsgData[6:8]

    MsgSQN = MsgAddr = None
    if MsgDataDestMode == '01':  # IEEE
        MsgAddr = MsgData[8:24]
        MsgSQN = MsgData[24:26]
        nPDU = MsgData[26:28]
        aPDU = MsgData[28:30]
    elif MsgDataDestMode in  ('02', '03'):  # Short Address/Group
        MsgAddr = MsgData[8:12]
        MsgSQN = MsgData[12:14]
        nPDU = MsgData[14:16]
        aPDU = MsgData[16:18]
    else:
        self.logging_receive( 'Log', "decode8012_8702 - wrong address mode %s" %MsgDataDestMode)
        return None

    update_xPDU( self, nPDU, aPDU)

    isqn = sqn_get_internal_sqn_from_aps_sqn(self, MsgSQN)
    
    if isqn is None:
        self.logging_receive( 'Log', "decode8012_8702 - 0x8012 not for us eSqn: %s" %(MsgSQN))
        return

    if isqn not in self.ListOfCommands:
        self.logging_receive( 'Log', "decode8012_8702 - 0x8012 not for us eSqn: %s " %(MsgSQN))
        return

    print_listofcommands( self, isqn )

    if MsgType == '8702':
        release_command( self, isqn)
        return

    self.ListOfCommands[ isqn ]['Status'] = '8012'
    if is_final_step( self, isqn, 0x8012):
        release_command( self, isqn)
