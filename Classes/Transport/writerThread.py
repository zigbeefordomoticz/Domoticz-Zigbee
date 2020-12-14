# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import binascii
import struct

import time
import os

from datetime import datetime

from Classes.LoggingManagement import LoggingManagement

from Modules.tools import is_hex, retreive_cmd_payload_from_8002, is_manufspecific_8002_payload
from Modules.zigateConsts import ZIGATE_RESPONSES, ZIGATE_COMMANDS, ADDRESS_MODE, SIZE_DATA_TYPE
from Modules.sqnMgmt import sqn_init_stack, sqn_generate_new_internal_sqn, sqn_add_external_sqn, sqn_get_internal_sqn_from_aps_sqn, sqn_get_internal_sqn_from_app_sqn, TYPE_APP_ZCL, TYPE_APP_ZDP
from Modules.errorCodes import ZCL_EXTENDED_ERROR_CODES

import serial
import select
import socket

from threading import Thread, Lock, Event
import multiprocessing

import queue
from binascii import unhexlify, hexlify

STANDALONE_MESSAGE = []
PDM_COMMANDS = ('8300', '8200', '8201', '8204', '8205', '8206', '8207', '8208')
CMD_PDM_ON_HOST = []
CMD_ONLY_STATUS = []
CMD_WITH_ACK = []
CMD_NWK_2NDBytes = {}
CMD_WITH_RESPONSE = {}
RESPONSE_SQN = []

NB_SEND_PER_SECONDE = 5
MAX_THROUGHPUT = 1 / NB_SEND_PER_SECONDE

#BAUDS = 460800
BAUDS = 115200


def start_writer_thread( self ):

    if self.Thread_process_and_send is None:
        self.Thread_process_and_send = Thread( name="ZiGateWriter",  target=ZigateTransport.writer_thread,  args=(self,))
        self.Thread_process_and_send.start()

def writer_thread( self ):
    self.logging_send('Status', "ZigateTransport: writer_thread Thread start.")

    while self.running:
        frame = None
        # Sending messages ( only 1 at a time )
        try:
            self.logging_send( 'Log', "Waiting for next command")
            message = self.Thread_process_and_sendQueue.get( )
            self.logging_send( 'Log', "Command to be send to ZiGate: %s" %message)
            
            if isinstance( message, dict ) and 'cmd' in message and 'datas' in message and 'ackIsDisabled' in message and 'waitForResponseIn' in message:
                    self.thread_sendData( message['cmd'], message['datas'], message['ackIsDisabled'], message['waitForResponseIn'])
                    self.logging_send( 'Log', "Command sent!!!!")

            elif message == 'STOP':
                break

            else:
                Domoticz.Error("Hops ... Don't known what to do with that %s" %message)

        except queue.Empty:
            # Empty Queue, timeout.
            pass

        except Exception as e:
            Domoticz.Error("Error while receiving a ZiGate message: %s" %e)
            handle_error_in_thread( self, e, 0, 0, frame)

    self.logging_send('Status',"ZigateTransport: writer_thread Thread stop.")


def thread_sendData(self, cmd, datas, ackIsDisabled=False, waitForResponseIn=False):

    waitForResponse = False
    if waitForResponseIn  or self.pluginconf.pluginConf['waitForResponse']:
        waitForResponse = True
    #self.logging_send('Debug2',"   -> waitForResponse: %s waitForResponseIn: %s" %(waitForResponse, waitForResponseIn))

    # If ackIsDisabled is True, it means that usally a Ack is expected ( ZIGATE_COMMANDS), but here it has been disabled via Address Mode
    #self.logging_send('Debug2', "sendData - %s %s ackDisabled: %s FIFO: %s" %
    #                 (cmd, datas, ackIsDisabled, len(self.zigateSendQueue)))
    if datas is None:
        datas = ''

    if datas != '' and not is_hex(datas):
        _context = {
            'Error code': 'TRANS-SENDDATA-01',
            'Cmd': cmd,
            'Datas': datas,
            'ackIsDisabled': ackIsDisabled,
            'waitForResponseIn': waitForResponseIn,
        }
        self.logging_send_error( "sendData", context=_context)
        return None

    # Check if the Cmd/Data is not yet in the pipe
    alreadyInQueue = False
    for x in list(self.ListOfCommands.keys()):
        if (x in self.ListOfCommands and 'Status'  in self.ListOfCommands[x] and self.ListOfCommands[x]['Status'] not in ('', 'TO-SEND', 'QUEUED')):
            continue

        if (x in self.ListOfCommands and 'Cmd' in self.ListOfCommands[x] and self.ListOfCommands[x]['Cmd'] != cmd):
            continue

        if ( x in self.ListOfCommands and 'Datas'  in self.ListOfCommands[x] and self.ListOfCommands[x]['Datas'] != datas ):
            continue

        self.logging_send( 'Log', "Cmd: %s Data: %s already in queue. drop that command" % (cmd, datas))
        alreadyInQueue = True
        return None

    # Let's move on, create an internal Sqn for tracking
    InternalSqn = sqn_generate_new_internal_sqn(self)
    if InternalSqn in self.ListOfCommands:
        # Unexpected !
        _context = {
            'Error code': 'TRANS-SENDDATA-02',
            'Cmd': cmd,
            'Datas': datas,
            'ackIsDisabled': ackIsDisabled,
            'waitForResponseIn': waitForResponseIn,
            'iSQN': InternalSqn
        }
        self.logging_send_error( "sendData", context=_context)
        return None

    store_ISQN_infos( self, InternalSqn, cmd, datas, ackIsDisabled, waitForResponse )
    printListOfCommands(self, 'from sendData', InternalSqn)
    send_data_internal(self, InternalSqn)
    return InternalSqn



def store_ISQN_infos( self, InternalSqn, cmd, datas, ackIsDisabled, waitForResponse ):
    self.ListOfCommands[InternalSqn] = {}
    self.ListOfCommands[InternalSqn]['Cmd'] = cmd
    self.ListOfCommands[InternalSqn]['Datas'] = datas
    self.ListOfCommands[InternalSqn]['ReTransmit'] = 0
    self.ListOfCommands[InternalSqn]['Status'] = ''
    self.ListOfCommands[InternalSqn]['ReceiveTimeStamp'] = str((datetime.now()).strftime("%m/%d/%Y, %H:%M:%S"))
    self.ListOfCommands[InternalSqn]['SentTimeStamp'] = None
    self.ListOfCommands[InternalSqn]['PDMCommand'] = False

    self.ListOfCommands[InternalSqn]['ResponseExpected'] = False    # Means that there is an Expected Response for that Command
    self.ListOfCommands[InternalSqn]['MessageResponse'] = None      # Is the expected MsgType in response for the command
    self.ListOfCommands[InternalSqn]['Expected8011'] = False        # Expected ACK
    self.ListOfCommands[InternalSqn]['WaitForResponse'] = False     # Used in Zigbee31d to wait for a Response
    self.ListOfCommands[InternalSqn]['Expected8012'] = False        # Used as of 31e
    self.ListOfCommands[InternalSqn]['StatusTimeStamp'] = None

    self.ListOfCommands[InternalSqn]['APP_SQN'] = None
    self.ListOfCommands[InternalSqn]['APS_SQN'] = None
    self.ListOfCommands[InternalSqn]['TYP_SQN'] = None

    hexCmd = int(cmd, 16)
    if hexCmd in CMD_PDM_ON_HOST:
        self.ListOfCommands[InternalSqn]['PDMCommand'] = True

    if self.firmware_with_8012 and ackIsDisabled and ZIGATE_COMMANDS[hexCmd]['8012']:
        self.ListOfCommands[InternalSqn]['Expected8012']  = True

    if not ackIsDisabled and hexCmd in CMD_WITH_ACK:
        self.ListOfCommands[InternalSqn]['Expected8011'] = True

    if (not ackIsDisabled or waitForResponse) and hexCmd in CMD_WITH_RESPONSE and hexCmd in RESPONSE_SQN:
        self.ListOfCommands[InternalSqn]['MessageResponse'] = CMD_WITH_RESPONSE[hexCmd]
        self.ListOfCommands[InternalSqn]['ResponseExpected'] = True


    if not self.firmware_with_aps_sqn:
        # We are on firmware <= 31c
        # 0110 and 0113 are always set with Ack. Overwriten by the firmware
        if hexCmd in (0x0110, 0x0113):
            self.logging_send(
                'Debug', "-- > Patching %s to Ack due to firmware 31c" % hexCmd)
            self.ListOfCommands[InternalSqn]['MessageResponse'] = CMD_WITH_RESPONSE[hexCmd]
            self.ListOfCommands[InternalSqn]['ResponseExpected'] = True
            self.ListOfCommands[InternalSqn]['Expected8011'] = True
            self.ListOfCommands[InternalSqn]['WaitForResponse'] = True

    if hexCmd == 0x0530 and self.FirmwareVersion and int(self.FirmwareVersion,16) <= 0x031d:
        # Starting 0x031e Firmware, the RAW APS command can use address mode to request ACK/NO-ACK
        # below this firmware it is always NO-ACK
        self.ListOfCommands[InternalSqn]['Expected8011'] = False

    # Ack to force Waiting for the Expected Response
    if self.pluginconf.pluginConf['forceFullSeqMode'] and self.ListOfCommands[InternalSqn]['ResponseExpected'] and (not ackIsDisabled or waitForResponse):
        self.ListOfCommands[InternalSqn]['WaitForResponse'] = True

    self.logging_send('Debug', "sendData - %s %s ackDisabled: %s FIFO: %s ResponseExpected: %s WaitForResponse: %s MessageResponse: 0x%s" 
        %(cmd, datas, ackIsDisabled, len(self.zigateSendQueue), 
        self.ListOfCommands[InternalSqn]['ResponseExpected'], 
        self.ListOfCommands[InternalSqn]['WaitForResponse'],
        self.ListOfCommands[InternalSqn]['MessageResponse']))


def send_data_internal(self, InternalSqn):
    #
    # in charge of sending Data. Call by sendZigateCmd
    # If nothing in the waiting queue, will call _send_data and it will be sent straight to Zigate

    if InternalSqn not in self.ListOfCommands:
        # Unexpected
        Domoticz.Error("send_data_internal - unexpected 1 %s not in ListOfCommands: %s" %
                        (InternalSqn, str(self.ListOfCommands.keys())))
        return
    self.logging_send('Debug', "--- send_data_internal - %s FIFO: %s" %
                        (InternalSqn, len(self.zigateSendQueue)))

    sendNow = True
    # PDM Management.
    # When PDM traffic is ongoing we cannot interupt, so we need to FIFO all other commands until the PDMLock is released
    if self.pdm_lock_status() and self.ListOfCommands[InternalSqn]['Cmd'] not in PDM_COMMANDS:
        # Only PDM related command can go , all others will be dropped.
        Domoticz.Log("PDM not yet ready, FIFO command %s %s" % (
            self.ListOfCommands[InternalSqn]['Cmd'], self.ListOfCommands[InternalSqn]['Datas']))
        sendNow = False


    if self._waitFor8000Queue or self._waitFor8012Queue or self._waitFor8011Queue or self._waitForCmdResponseQueue:
        sendNow = False

    self.logging_send('Debug', "--- before sending - Command: %s  Q(0x8000): %s Q(8012): %s Q(Ack/Nack): %s Q(Response): %s sendNow: %s"
        % (self.ListOfCommands[InternalSqn]['Cmd'],  len(self._waitFor8000Queue), len(self._waitFor8012Queue), len(self._waitFor8011Queue), len(self._waitForCmdResponseQueue), sendNow))

    if not sendNow:
        # Put in FIFO
        self.logging_send( 'Debug', "--- send_data_internal - put in waiting queue")
        self.ListOfCommands[InternalSqn]['Status'] = 'QUEUED'
        self.ListOfCommands[InternalSqn]['StatusTimeStamp'] = str((datetime.now()).strftime("%m/%d/%Y, %H:%M:%S"))
        _add_cmd_to_send_queue(self, InternalSqn)
        return

    # Sending Command
    if not self.ListOfCommands[InternalSqn]['PDMCommand']:
        # Limit throughtput
        if (( time.time() - self.lastsent_time) < MAX_THROUGHPUT):
            return
        load_queues_before_sending( self, InternalSqn )

    # Go!
    if self.pluginconf.pluginConf["debugzigateCmd"]:
        self.logging_send('Log', "+++ send_data_internal ready (queues set) - Command: %s  Q(0x8000): %s Q(8012): %s Q(Ack/Nack): %s Q(Response): %s sendNow: %s"
            % (self.ListOfCommands[InternalSqn]['Cmd'], len(self._waitFor8000Queue), len(self._waitFor8012Queue), len(self._waitFor8011Queue), len(self._waitForCmdResponseQueue), sendNow))

    printListOfCommands( self, 'after correction before sending', InternalSqn )

    _send_data(self, InternalSqn)


def load_queues_before_sending( self, InternalSqn ):
    # That is a Standard command (not PDM on  Host), let's process as usall
    self.ListOfCommands[InternalSqn]['Status'] = 'TO-SEND'
    self.ListOfCommands[InternalSqn]['StatusTimeStamp'] = str((datetime.now()).strftime("%m/%d/%Y, %H:%M:%S"))

    # Add to 0x8000 queue
    _add_cmd_to_wait_for8000_queue(self, InternalSqn)

    if self.ListOfCommands[InternalSqn]['Expected8012'] and self.zmode == 'zigate31e':
        # In addition to 0x8000 we have to wait 0x8012 or 0x8702
        patch_8012_for_sending( self, InternalSqn)

    if self.ListOfCommands[InternalSqn]['Expected8011'] and self.zmode in ( 'zigate31d', 'zigate31e'):
        patch_8011_for_sending(self, InternalSqn)

    if self.ListOfCommands[InternalSqn]['WaitForResponse'] and self.zmode in ( 'zigate31d', 'zigate31e'):
        patch_cmdresponse_for_sending(self, InternalSqn)

    if self.ListOfCommands[InternalSqn]['ResponseExpected'] and self.zmode == 'zigate31c':
        patch_cmdresponse_for_sending(self, InternalSqn)


def printListOfCommands(self, comment, isqn):
    self.logging_send('Debug', "=======  %s:" % comment)
    self.logging_send('Debug', "[%s]  - Cmd:              %s" % ( isqn, self.ListOfCommands[isqn]['Cmd']))
    self.logging_send('Debug', "[%s]  - Datas:            %s" % ( isqn, self.ListOfCommands[isqn]['Datas']))
    self.logging_send('Debug', "[%s]  - ReTransmit:       %s" % ( isqn, self.ListOfCommands[isqn]['ReTransmit']))
    self.logging_send('Debug', "[%s]  - Status:           %s" % ( isqn, self.ListOfCommands[isqn]['Status']))
    self.logging_send('Debug', "[%s]  - ReceiveTimeStamp: %s" % ( isqn, self.ListOfCommands[isqn]['ReceiveTimeStamp']))
    self.logging_send('Debug', "[%s]  - SentTimeStamp:    %s" % ( isqn, self.ListOfCommands[isqn]['SentTimeStamp']))
    self.logging_send('Debug', "[%s]  - PDMCommand:       %s" % ( isqn, self.ListOfCommands[isqn]['PDMCommand']))
    self.logging_send('Debug', "[%s]  - ResponseExpected: %s" % ( isqn, self.ListOfCommands[isqn]['ResponseExpected']))
    self.logging_send('Debug', "[%s]  - MessageResponse:  %s" % ( isqn, self.ListOfCommands[isqn]['MessageResponse']))
    self.logging_send('Debug', "[%s]  - ExpectedAck:      %s" % ( isqn, self.ListOfCommands[isqn]['Expected8011']))
    self.logging_send('Debug', "[%s]  - Expected8012:     %s" % ( isqn, self.ListOfCommands[isqn]['Expected8012']))
    self.logging_send('Debug', "[%s]  - WaitForResponse:  %s" % ( isqn, self.ListOfCommands[isqn]['WaitForResponse']))

def patch_cmdresponse_for_sending(self, i_sqn):

    if int(self.ListOfCommands[i_sqn]['Cmd'], 16) not in CMD_NWK_2NDBytes:
        if self.ListOfCommands[i_sqn]['Cmd'] == '004E' and self.ListOfCommands[i_sqn]['Datas'][0:4] == '0000':
            # Do not wait for LQI request to ZiGate
            self.logging_send(
                'Debug', "--- LQI request to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[i_sqn]['Expected8011'] = False
            self.ListOfCommands[i_sqn]['ResponseExpected'] = False
            self.ListOfCommands[i_sqn]['MessageResponse'] = None
            self.ListOfCommands[i_sqn]['WaitForResponse'] = False

        elif self.ListOfCommands[i_sqn]['Cmd'] == '0049' and self.ListOfCommands[i_sqn]['Datas'][0:4] == 'FFFC':
            self.logging_send(
                'Debug', "--- Permit To Join request to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[i_sqn]['Expected8011'] = False
            self.ListOfCommands[i_sqn]['ResponseExpected'] = False
            self.ListOfCommands[i_sqn]['MessageResponse'] = None
            self.ListOfCommands[i_sqn]['WaitForResponse'] = False
        
        else:
            self.logging_send('Debug', "--- Add to Queue CommandResponse Queue")
            _add_cmd_to_wait_for_cmdresponse_queue(self, i_sqn)
    else:
        if self.ListOfCommands[i_sqn]['Datas'][0:2] == '%02x' % ADDRESS_MODE['group'] and self.ListOfCommands[i_sqn]['Datas'][2:6] == '0000':
            # Do not wait for Response to Groups commands sent to Zigate
            self.logging_send(
                'Debug', "--- Group command to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[i_sqn]['Expected8011'] = False
            self.ListOfCommands[i_sqn]['ResponseExpected'] = False
            self.ListOfCommands[i_sqn]['MessageResponse'] = None
            self.ListOfCommands[i_sqn]['WaitForResponse'] = False

        elif self.ListOfCommands[i_sqn]['Datas'][2:6] == '0000':
            # Do not wait for Response to commands sent to Zigate
            self.logging_send(
                'Debug', "--- Cmmand to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[i_sqn]['Expected8011'] = False
            self.ListOfCommands[i_sqn]['ResponseExpected'] = False
            self.ListOfCommands[i_sqn]['MessageResponse'] = None
            self.ListOfCommands[i_sqn]['WaitForResponse'] = False

        elif not self.firmware_with_aps_sqn and self.ListOfCommands[i_sqn]['Cmd'] == '0110':
            #  Compatibility mode with previous Transport version do not wait for Response on command 0x0100
            self.ListOfCommands[i_sqn]['Expected8011'] = False
            self.ListOfCommands[i_sqn]['ResponseExpected'] = False
            self.ListOfCommands[i_sqn]['MessageResponse'] = None
            self.ListOfCommands[i_sqn]['WaitForResponse'] = False
            self.logging_send('Debug', "--- 31c do not block 0110 even if Ack expected %s" %
                             self.ListOfCommands[i_sqn]['Cmd'])

        else:
            self.logging_send('Debug', "--- Add to Queue CommandResponse Queue")
            _add_cmd_to_wait_for_cmdresponse_queue(self, i_sqn)

def patch_8012_for_sending( self, i_sqn):

    if int(self.ListOfCommands[i_sqn]['Cmd'], 16) not in CMD_NWK_2NDBytes:
        if self.ListOfCommands[i_sqn]['Cmd'] == '004E' and self.ListOfCommands[i_sqn]['Datas'][0:4] == '0000':
            # Do not wait for LQI request to ZiGate
            self.ListOfCommands[i_sqn]['Expected8012'] = False

        elif self.ListOfCommands[i_sqn]['Cmd'] == '0049' and self.ListOfCommands[i_sqn]['Datas'][0:4] == 'FFFC':
            self.ListOfCommands[i_sqn]['Expected8012'] = False
        
        else:
            _add_cmd_to_wait_for8012_queue(self, i_sqn)
    else:
        if self.ListOfCommands[i_sqn]['Datas'][2:6] == '0000':
            self.ListOfCommands[i_sqn]['Expected8012'] = False

        else:
            _add_cmd_to_wait_for8012_queue(self, i_sqn)

def patch_8011_for_sending(self, i_sqn):

    # These are ZiGate commands which doesn't have Ack/Nack with firmware up to 3.1c
    CMD_NOACK_ZDP = (0x0030, 0x0031, 0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045,
                     0x0046, 0x0047, 0x0049, 0x004A, 0x004B, 0x004E, 0x0530, 0x0531, 0x0532, 0x0533)

    # If ZigBeeAck mode and Ack Expected
    if not self.firmware_with_aps_sqn and int(self.ListOfCommands[i_sqn]['Cmd'], 16) in CMD_NOACK_ZDP:
        # This only apply to firmware on 31c and below
        self.logging_send(
            'Debug', "--- ZDP command no Ack/Nack with that firmware")
        self.ListOfCommands[i_sqn]['Expected8011'] = False

    elif int(self.ListOfCommands[i_sqn]['Cmd'], 16) not in CMD_NWK_2NDBytes:
        if self.ListOfCommands[i_sqn]['Cmd'] == '004E' and self.ListOfCommands[i_sqn]['Datas'][0:4] == '0000':
            # Do not wait for LQI request to ZiGate
            self.logging_send(
                'Debug', "--- LQI request to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[i_sqn]['Expected8011'] = False
        else:
            # Wait for Ack/Nack
            self.logging_send('Debug', "--- Add to Queue Ack/Nack")
            _add_cmd_to_wait_for8011_queue(self, i_sqn)
    else:
        if self.ListOfCommands[i_sqn]['Datas'][0:2] == '%02x' % ADDRESS_MODE['group']:
            # Do not wait for Ack/Nack as the command to Groups
            self.logging_send(
                'Debug', "--- Group command to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[i_sqn]['Expected8011'] = False

        elif self.ListOfCommands[i_sqn]['Datas'][2:6] == '0000':
            # Do not wait for Ack/Nack as the command is sent for ZiGate
            self.logging_send(
                'Debug', "--- Cmmand to ZiGate Do not wait for Ack/Nack")
            self.ListOfCommands[i_sqn]['Expected8011'] = False

        else:
            # Wait for Ack/Nack if NwkId != '0000' and Address Mode (ZiGate)
            self.logging_send('Debug', "--- Add to Queue Ack/Nack %s %s" %
                             (self.ListOfCommands[i_sqn]['Cmd'], self.ListOfCommands[i_sqn]['Datas']))
            _add_cmd_to_wait_for8011_queue(self, i_sqn)


def _send_data(self, InternalSqn):
    # send data to Zigate via the communication transport

    cmd = self.ListOfCommands[InternalSqn]['Cmd']
    datas = self.ListOfCommands[InternalSqn]['Datas']
    self.ListOfCommands[InternalSqn]['Status'] = 'SENT'
    self.ListOfCommands[InternalSqn]['StatusTimeStamp'] = str((datetime.now()).strftime("%m/%d/%Y, %H:%M:%S"))
    self.ListOfCommands[InternalSqn]['SentTimeStamp'] = int(time.time())
    

    if self.pluginconf.pluginConf["debugzigateCmd"]:
        self.logging_send('Log', "======================== Send to Zigate - [%s] %s %s ExpectAck: %s ExpectResponse: %s WaitForResponse: %s" % (
            InternalSqn, cmd, datas, 
            self.ListOfCommands[InternalSqn]['Expected8011'], 
            self.ListOfCommands[InternalSqn]['ResponseExpected'], 
            self.ListOfCommands[InternalSqn]['WaitForResponse']))

    if datas == "":
        length = "0000"
        checksumCmd = get_checksum(cmd, length, "0")
        strchecksum = '0' + \
            str(checksumCmd) if len(checksumCmd) == 1 else checksumCmd
        lineinput = "01" + str(zigate_encode(cmd)) + str(zigate_encode(length)) + \
                    str(zigate_encode(strchecksum)) + "03"
    else:
        #Domoticz.Log("---> datas: %s" %datas)
        length = '%04x' % (len(datas)//2)

        checksumCmd = get_checksum(cmd, length, datas)
        strchecksum = '0' + \
            str(checksumCmd) if len(checksumCmd) == 1 else checksumCmd
        lineinput = "01" + str(zigate_encode(cmd)) + str(zigate_encode(length)) + \
                    str(zigate_encode(strchecksum)) + \
            str(zigate_encode(datas)) + "03"

    # self.logging_send(  'Debug', "---  --  > _send_data - sending encoded Cmd: %s length: %s CRC: %s Data: %s" \
    #            %(str(zigate_encode(cmd)), str(zigate_encode(length)), str(zigate_encode(strchecksum)), str(zigate_encode(datas))))
    #self._connection.Send(bytes.fromhex(str(lineinput)), 0)


    #Domoticz.Log("_send_data: raw command: %s" %str(bytes.fromhex(str(lineinput))))
    if self.pluginconf.pluginConf['MultiThreaded']:
        # Recommendation @badz
        write_to_zigate( self, self._connection, bytes.fromhex(str(lineinput)) )
    else:
        self._connection.Send(bytes.fromhex(str(lineinput)), 0)
    self.statistics._sent += 1



def write_to_zigate( self, serialConnection, encoded_data ):

    if self._transp == "Wifi":
        tcpipConnection = self._connection
        tcpiConnectionList = [ tcpipConnection ]
        inputSocket  = outputSocket = [ tcpipConnection ]
        readable, writable, exceptional = select.select(inputSocket, outputSocket, inputSocket)
        if writable:
            try:
                tcpipConnection.send( encoded_data )
            except socket.OSError as e:
                Domoticz.Error("Socket %s error %s" %(tcpipConnection, e))

        elif exceptional:
            Domoticz.Error("We have detected an error .... on %s" %inputSocket)
        return

    # Serial
    try:
        nb_write = serialConnection.write( encoded_data )
        if nb_write != len( encoded_data ):
            _context = {
                'Error code': 'TRANS-WRTZGTE-01',
                'EncodedData': str(encoded_data),
                'NbWrite': nb_write,
            }
            self.logging_send_error(  "write_to_zigate", context=_context)

    except TypeError as e:
        #Disconnect of USB->UART occured
        Domoticz.Error("serial_read_from_zigate - error while writing %s" %(e))

def zigate_encode(Data):
    # The encoding is the following:
    # Let B any byte value of the message. If B is between 0x00 and 0x0f (included) then :
    #    Instead of B, a 2-byte content will be written in the encoded frame
    #    The first byte is a fixed value: 0x02
    #    The second byte is the result of B ^ 0x10

    Out = ''
    Outtmp = ''
    for c in Data:
        Outtmp += c
        if len(Outtmp) == 2:
            if Outtmp[0] == '1' and Outtmp != '10':
                if Outtmp[1] == '0':
                    Outtmp = '0200'
                Out += Outtmp
            elif Outtmp[0] == '0':
                Out += '021' + Outtmp[1]
            else:
                Out += Outtmp
            Outtmp = ""
    return Out

def get_checksum(msgtype, length, datas):
    temp = 0 ^ int(msgtype[0:2], 16)
    temp ^= int(msgtype[2:4], 16)
    temp ^= int(length[0:2], 16)
    temp ^= int(length[2:4], 16)
    chk = 0
    for i in range(0, len(datas), 2):
        temp ^= int(datas[i:i + 2], 16)
        chk = hex(temp)
    return chk[2:4]