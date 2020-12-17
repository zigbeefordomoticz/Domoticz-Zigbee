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
from Classes.Transport.handleFirmware31c import check_and_process_others_31c


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

    if MsgType == '0302': # PDM loaded, ZiGate ready
        self.logging_receive( 'Log', "process_frame - PDM loaded, ZiGate ready: %s MsgData %s" % (MsgType, MsgData)) 
        # Must be sent above in order to issue a rejoin_legrand_reset() if needed
        #rejoin_legrand_reset(self)
        return

    if MsgType in CMD_PDM_ON_HOST:
        # Manage PDM on Host commands
        self.logging_receive( 'Log', "process_frame - CMD_PDM_ON_HOST MsgType: %s MsgData %s" % (MsgType, MsgData))  
        return

    if MsgType == '8001':
        #Async message
        self.logging_receive( 'Log', "process_frame - MsgType: %s " %( MsgType))
        NXP_log_message(self, decoded_frame)
        return

    if MsgType == '9999':
        # Async message
        self.logging_receive( 'Log', "process_frame - MsgType: %s MsgData: %s" %( MsgType, MsgData))
        NXP_Extended_Error_Code( self, decoded_frame)
        return

    if MsgType == '8000': # Command Ack
        self.logging_receive( 'Log', "process_frame - MsgType: %s MsgData: %s decode and forwarde" %( MsgType, MsgData))
        decode8000( self, decoded_frame)
        self.forwarder_queue.put( decoded_frame)
        return

    if MsgType in ( '8012', '8702'): # Transmission Akc for no-ack commands
        self.logging_receive( 'Log', "process_frame - MsgType: %s MsgData: %s decode" %( MsgType, MsgData))
        if self.firmware_with_8012:
            decode8012_8702( self, decoded_frame)
        return

    if MsgType == '8011': # Command Ack (from target device)
        self.logging_receive( 'Log', "process_frame - MsgType: %s MsgData: %s decode and forward" %( MsgType, MsgData))
        decode8011( self, decoded_frame)
        self.forwarder_queue.put( decoded_frame)
        return

    if MsgType in ( '8010', ):
        self.logging_receive( 'Log', "process_frame - MsgType: %s Forward and release" %( MsgType))
        self.forwarder_queue.put( decoded_frame)
        release_command( self, get_isqn_from_ListOfCommands( self, MsgType))
        return

    if MsgType == '8701':
        self.logging_receive( 'Log', "process_frame - MsgType: %s No action" %( MsgType))
        # Async message
        # Route Discovery, we don't handle it
        return

    if not self.firmware_with_aps_sqn and MsgType in ( '8100', '8110', '8102'):
        # We are in a 31c and below firmware.
        # we will release next command only when receiving expected response for a command
        check_and_process_others_31c(self, MsgType, MsgData)
        self.forwarder_queue.put( decoded_frame)
        return

    if MsgType == "8002" and MsgData:
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