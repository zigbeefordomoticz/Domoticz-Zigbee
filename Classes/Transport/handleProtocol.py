# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#


def process_frame(self, decode_frame):
    
    # Sanity Check
    if decode_frame == '' or decode_frame is None or len(decode_frame) < 12:
        return

    i_sqn = None
    MsgType = decode_frame[2:6]
    MsgLength = decode_frame[6:10]
    MsgCRC = decode_frame[10:12]

    if MsgType == '8701':
        # Route Discovery, we don't handle it
        return

    # We receive an async message, just forward it to plugin
    if int(MsgType, 16) in STANDALONE_MESSAGE:
        self.logging_receive( 'Debug', "process_frame - STANDALONE_MESSAGE MsgType: %s MsgLength: %s MsgCRC: %s" % (MsgType, MsgLength, MsgCRC))    
        # Send to Queue for F_OUT()
        return

    # Payload
    MsgData = None
    if len(decode_frame) < 18:
        return

    MsgData = decode_frame[12:len(decode_frame) - 4]

    if MsgType in ( '8000', '8012', '8702', '8011'):
        # Protocol Management with 31d and 31e
        pass


    if MsgData and MsgType == "8002":
        # Data indication
        self.logging_receive( 'Debug', "process_frame - 8002 MsgType: %s MsgLength: %s MsgCRC: %s" % (MsgType, MsgLength, MsgCRC))  
        self.Thread_proc_recvQueue_and_process.put( process8002( self, frame ) )
        return


    # We reach that stage: Got a message not 0x8000/0x8011/0x8701/0x8202 an not a standolone message
    # But might be a 0x8102 ( as firmware 3.1c and below are reporting Read Attribute response and Report Attribute with the same MsgType)
    if not self.firmware_with_aps_sqn:
        MsgZclSqn = MsgData[0:2]
        MsgNwkId = MsgData[2:6]
        MsgEp = MsgData[6:8]
        MsgClusterId = MsgData[8:12]
        # Old Fashion Protocol Managemet. We are waiting for a Command Response before sending the next command

        return

    # Forward the message to plugin for further processing

# Extended Error Code:
def handle_9999( self, MsgData):

    StatusMsg = ''
    if  MsgData in ZCL_EXTENDED_ERROR_CODES:
        StatusMsg = ZCL_EXTENDED_ERROR_CODES[MsgData]

    if self.pluginconf.pluginConf['trackError']:
        self.logging_send( 'Log', "handle_9999 - Last PDUs infos ( n: %s a: %s) Extended Error Code: [%s] %s" %(self.npdu, self.apdu, MsgData, StatusMsg))