# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz
import binascii
import datetime

from Classes.Transport.decode8002 import decode8002_and_process
from Classes.Transport.decode8000 import decode8000
from Classes.Transport.decode8012 import decode8012_8702
from Classes.Transport.decode8011 import decode8011
from Classes.Transport.tools import ( release_command, get_isqn_from_ListOfCommands, STANDALONE_MESSAGE, CMD_PDM_ON_HOST)
from Classes.Transport.handleFirmware31c import decode8011_31c
from Classes.Transport.instrumentation import time_spent_process_frame

from Modules.zigateConsts import MAX_SIMULTANEOUS_ZIGATE_COMMANDS
from Modules.errorCodes import ZCL_EXTENDED_ERROR_CODES

@time_spent_process_frame( )
def process_frame(self, decoded_frame):

    #self.logging_receive( 'Debug', "process_frame - receive frame: %s" %decoded_frame)

    # Sanity Check
    if decoded_frame == '' or decoded_frame is None or len(decoded_frame) < 12:
        return

    i_sqn = None
    MsgType = decoded_frame[2:6]
    MsgLength = decoded_frame[6:10]
    MsgCRC = decoded_frame[10:12]

    #self.logging_receive( 'Debug', "process_frame - MsgType: %s MsgLenght: %s MsgCrc: %s" %( MsgType, MsgLength, MsgCRC))

    # Payload
    MsgData = None
    if len(decoded_frame) < 18:
        return

    MsgData = decoded_frame[12:len(decoded_frame) - 4]

    if MsgType == '0302': # PDM loaded, ZiGate ready (after an internal error, but also after an ErasePDM)
        self.logging_receive( 'Debug', "process_frame - PDM loaded, ZiGate ready: %s MsgData %s" % (MsgType, MsgData))
        for x in list(self.ListOfCommands):
            if self.ListOfCommands[x]['cmd'] == '0012':
                release_command( self, x)
        # This could be also linked to a Reboot of the ZiGate firmware. In such case, it might be important to release Semaphore
        # Must be sent above in order to issue a rejoin_legrand_reset() if needed
        #rejoin_legrand_reset(self)
        return

    if MsgType in CMD_PDM_ON_HOST:
        # Manage PDM on Host commands
        self.logging_receive( 'Debug', "process_frame - CMD_PDM_ON_HOST MsgType: %s MsgData %s" % (MsgType, MsgData))  
        return

    if MsgType in ( '8035', ):
        # Internal ZiGate Message, just drop
        self.logging_receive( 'Debug', "process_frame - ZiGate internal Message MsgType: %s MsgData %s" % (MsgType, MsgData))  
        return        

    if int(MsgType, 16) in STANDALONE_MESSAGE:
        self.logging_receive( 'Debug', "process_frame - STANDALONE_MESSAGE MsgType: %s MsgLength: %s MsgCRC: %s" % (MsgType, MsgLength, MsgCRC))    
        self.forwarder_queue.put( decoded_frame)
        return


    if MsgType == '8001':
        #Async message
        self.logging_receive( 'Debug', "process_frame - MsgType: %s " %( MsgType))
        NXP_log_message(self, decoded_frame)
        return

    if MsgType == '9999':
        # Async message
        self.logging_receive( 'Debug', "process_frame - MsgType: %s MsgData: %s" %( MsgType, MsgData))
        NXP_Extended_Error_Code( self, MsgData)
        return

    if MsgType == '8000': # Command Ack
        self.logging_receive( 'Debug', "process_frame - MsgType: %s MsgData: %s decode and forward" %( MsgType, MsgData))
        decode8000( self, decoded_frame)
        self.forwarder_queue.put( decoded_frame)
        return

    if MsgType in ( '8012', '8702'): # Transmission Akc for no-ack commands
        self.logging_receive( 'Debug', "process_frame - MsgType: %s MsgData: %s decode" %( MsgType, MsgData))
        if self.firmware_with_8012:
            decode8012_8702( self, decoded_frame)
        return

    if self.firmware_with_aps_sqn and MsgType == '8011': # Command Ack (from target device)
        self.logging_receive( 'Debug', "process_frame - MsgType: %s MsgData: %s decode and forward" %( MsgType, MsgData))
        decode8011( self, decoded_frame)
        self.forwarder_queue.put( decoded_frame)
        return

    if not self.firmware_with_aps_sqn and MsgType == '8011':
        decode8011_31c( self, decoded_frame)
        self.forwarder_queue.put( decoded_frame)
        return

    if MsgType == '8701':
        self.logging_receive( 'Debug', "process_frame - MsgType: %s No action" %( MsgType))
        # Async message
        # Route Discovery, we don't handle it
        return


    if MsgType == "8002" and MsgData:
        # Data indication
        self.statistics._data += 1
        self.logging_receive( 'Debug', "process_frame - 8002 MsgType: %s MsgLength: %s MsgCRC: %s" % (MsgType, MsgLength, MsgCRC))  
        self.forwarder_queue.put( decode8002_and_process( self, decoded_frame ) )
        return

    # Forward the message to plugin for further processing
    self.statistics._data += 1
    self.forwarder_queue.put( decoded_frame)

# Extended Error Code:
def NXP_Extended_Error_Code( self, MsgData):

    StatusMsg = ''
    if  MsgData in ZCL_EXTENDED_ERROR_CODES:
        StatusMsg = ZCL_EXTENDED_ERROR_CODES[MsgData]

    #if self.pluginconf.pluginConf['trackError']:
    #    _context = {
    #        'Error code': 'TRANS-PROTO-01',
    #        'ExtendedErrorCode': MsgData,
    #        'ExtendedError': StatusMsg,
    #        'nPDU': self.npdu,
    #        'aPDU': self.apdu
    #    }
    #    self.logging_receive_error( "NXP_Extended_Error_Code - Extended Error Code: [%s] %s" %( MsgData, StatusMsg), context=_context)
    
    self.logging_receive( 'Log',"NXP_Extended_Error_Code - Extended Error Code: [%s] %s" %( MsgData, StatusMsg))

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
                self.logging_send( 'Error',"Error while writing to ZiGate log file %s" %logfilename)
    except IOError:
        self.logging_send( 'Error',"Error while Opening ZiGate log file %s" %logfilename)