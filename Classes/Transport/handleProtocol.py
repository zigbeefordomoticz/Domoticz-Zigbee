# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz
import binascii
import datetime

from Classes.Transport.decode8002 import decode8002_and_process
from Classes.Transport.tools import ( STANDALONE_MESSAGE, PDM_COMMANDS,CMD_PDM_ON_HOST,CMD_ONLY_STATUS,CMD_WITH_ACK,CMD_NWK_2NDBytes,CMD_WITH_RESPONSE,RESPONSE_SQN,)
from Modules.errorCodes import ZCL_EXTENDED_ERROR_CODES

def process_frame(self, decoded_frame):

    self.logging_receive( 'Log', "process_frame - receive frame: %s" %decoded_frame)

    # Sanity Check
    if decoded_frame == '' or decoded_frame is None or len(decoded_frame) < 12:
        return

    i_sqn = None
    MsgType = decoded_frame[2:6]
    MsgLength = decoded_frame[6:10]
    MsgCRC = decoded_frame[10:12]

    self.logging_receive( 'Log', "process_frame - MsgType: %s MsgLenght: %s MsgCrc: %s" %( MsgType, MsgLength, MsgCRC))

    if MsgType == '8701':
        # Route Discovery, we don't handle it
        return

    # We receive an async message, just forward it to plugin
    if int(MsgType, 16) in STANDALONE_MESSAGE:
        self.logging_receive( 'Log', "process_frame - STANDALONE_MESSAGE MsgType: %s MsgLength: %s MsgCRC: %s" % (MsgType, MsgLength, MsgCRC))    
        self.forwarder_queue.put( decoded_frame)
        return

    # Payload
    MsgData = None
    if len(decoded_frame) < 18:
        return

    MsgData = decoded_frame[12:len(decoded_frame) - 4]

    if MsgType == '8001':
        NXP_log_message(self, MsgData)
        return

    elif MsgType == '9999':
        NXP_Extended_Error_Code( self, MsgData)
        return

    if MsgType in ( '8000', '8012', '8702', '8011'):
        # Protocol Management with 31d and 31e
        self.semaphore_gate.release()
        return

    if MsgData and MsgType == "8002":
        # Data indication
        self.logging_receive( 'Log', "process_frame - 8002 MsgType: %s MsgLength: %s MsgCRC: %s" % (MsgType, MsgLength, MsgCRC))  
        self.forwarder_queue.put( decode8002_and_process( self, decoded_frame ) )
        return


    # Forward the message to plugin for further processing
    self.forwarder_queue.put( decoded_frame)

# Extended Error Code:
def NXP_Extended_Error_Code( self, MsgData):

    StatusMsg = ''
    if  MsgData in ZCL_EXTENDED_ERROR_CODES:
        StatusMsg = ZCL_EXTENDED_ERROR_CODES[MsgData]

    if self.pluginconf.pluginConf['trackError']:
        self.logging_send( 'Log', "NXP_Extended_Error_Code - Last PDUs infos ( n: %s a: %s) Extended Error Code: [%s] %s" %(self.npdu, self.apdu, MsgData, StatusMsg))

def NXP_log_message(self, MsgData):  # Reception log Level

    LOG_FILE = "ZiGate"

    MsgLogLvl = MsgData[0:2]
    log_message = binascii.unhexlify(MsgData[2:]).decode('utf-8')
    logfilename =  self.pluginconf.pluginConf['pluginLogs'] + "/" + LOG_FILE + '_' + '%02d' %self.HardwareID + "_" + ".log"
    try:
        with open( logfilename , 'at', encoding='utf-8') as file:
            try:
                file.write( "%s %s %s" %(str(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]), MsgLogLvl,log_message) + "\n")
            except IOError:
                Domoticz.Error("Error while writing to ZiGate log file %s" %logfilename)
    except IOError:
        Domoticz.Error("Error while Opening ZiGate log file %s" %logfilename)