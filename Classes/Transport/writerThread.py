# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#


import Domoticz
import queue
import socket
import select
import time
from threading import Thread

from Modules.tools import is_hex

from Classes.Transport.tools import handle_thread_error, release_command

def start_writer_thread( self ):

    if self.writer_thread is None:
        self.writer_thread = Thread( name="ZiGateWriter_%s" %self.hardwareid,  target=writer_thread,  args=(self,))
        self.writer_thread.start()

def writer_thread( self ):
    logging_writer( self, 'Status', "ZigateTransport: writer_thread Thread start.")

    while self.running:
        frame = None
        # Sending messages ( only 1 at a time )
        try:
            #logging_writer( self,  'Debug', "Waiting for next command Qsize: %s" %self.writer_queue.qsize())
            command = self.writer_queue.get( )

            #logging_writer( self,  'Debug', "New command received:  %s" %(command))
            if isinstance( command, dict ) and 'cmd' in command and 'datas' in command and 'ackIsDisabled' in command and 'waitForResponseIn' in command and 'InternalSqn' in command:
                if self.writer_queue.qsize() > self.statistics._MaxLoad:
                    self.statistics._MaxLoad = self.writer_queue.qsize()
                self.statistics._Load = self.writer_queue.qsize()

                wait_for_semaphore( self , command)

                send_ok = thread_sendData( self, command['cmd'], command['datas'], command['ackIsDisabled'], command['waitForResponseIn'], command['InternalSqn'])
                logging_writer( self,  'Debug', "Command sent!!!! %s send_ok: %s" %(command, send_ok))
                if send_ok in ('PortClosed', 'SocketClosed'):
                    # Exit
                    break

                # ommand sent, if needed wait in order to reduce throughput and load on ZiGate
                limit_throuput(self, command)

            elif command == 'STOP':
                break

            else:
                logging_writer( self,  'Error', "Hops ... Don't known what to do with that %s" %command)

        except queue.Empty:
            # Empty Queue, timeout.
            pass

        except Exception as e:
            logging_writer( self,  'Error',"Error while receiving a ZiGate command: %s" %e)
            handle_thread_error( self, e, 0, 0, frame)

    logging_writer( self, 'Status',"ZigateTransport: writer_thread Thread stop.")

def limit_throuput(self, command):
    # Purpose is to have a regulate the load on ZiGate.
    # It is important for non 31e firmware, as we don't have all elements to regulate the flow
    # 
    # It takes on an USB ZiGate around 70ms for a full turn around time between the commande sent and the 0x8011 received

    if self.firmware_compatibility_mode:
        # We are in firmware 31a where we control the flow is only on 0x8000
        logging_writer( self, 'Debug',"Firmware 31a limit_throuput regulate to 250ms")
        time.sleep(0.250)

    elif not self.firmware_with_aps_sqn and not self.firmware_with_8012 and not command['ackIsDisabled']:
        # Firmware 31c
        logging_writer( self, 'Debug',"Firmware 31c limit_throuput regulate to 250ms")
        time.sleep(0.250)

    elif self.firmware_with_aps_sqn and not self.firmware_with_8012 and command['ackIsDisabled']:
        # We are in firmware 31d where we don't have 8012 flow control for ackIsDisabled commands
        logging_writer( self, 'Debug',"Firmware 31d limit_throuput regulate to 100ms")
        time.sleep(0.100)

    elif (
        not self.firmware_with_aps_sqn
        or not self.firmware_with_8012
        or command['ackIsDisabled']
    ):
        logging_writer( self, 'Log',"limit_throuput no regulation %s %s %s %s" %(
            self.firmware_compatibility_mode, self.firmware_with_aps_sqn, self.firmware_with_8012, command['ackIsDisabled'] ))

def wait_for_semaphore( self , command ):
        # Now we will block on Semaphore to serialize and limit the number of concurent commands on ZiGate
        # By using the Semaphore Timeout , we will make sure that the Semaphore is not acquired for ever.
        # However, if the Sem is relaed due to Timeout, we will not be notified !
        timeout_cmd = 8.0
        if self.firmware_compatibility_mode:
            timeout_cmd = 4.0

        if self.force_dz_communication or self.pluginconf.pluginConf['writerTimeOut']:
            logging_writer( self,  'Debug', "Waiting for a write slot . Semaphore %s TimeOut of 8s" %(self.semaphore_gate._value))
            block_status = self.semaphore_gate.acquire( blocking = True, timeout = timeout_cmd) # Blocking until 8s
        else:
            logging_writer( self,  'Debug', "Waiting for a write slot . Semaphore %s ATTENTION NO TIMEOUT FOR TEST PURPOSES" %(self.semaphore_gate._value))
            block_status = self.semaphore_gate.acquire( blocking = True, timeout = None) # Blocking  

        logging_writer( self,  'Debug', "============= semaphore %s given with status %s ============== Len: ListOfCmd %s - %s writerQueueSize: %s" %(
            self.semaphore_gate._value, block_status, len(self.ListOfCommands), str(self.ListOfCommands.keys()), self.writer_queue.qsize( ) ))

        if self.pluginconf.pluginConf['writerTimeOut'] and not block_status:
            semaphore_timeout( self, command )

def thread_sendData(self, cmd, datas, ackIsDisabled, waitForResponseIn, isqn ):
    logging_writer( self, 'Debug', "thread_sendData")
    if datas is None:
        datas = ''

    # Check if Datas are hex
    if datas != '' and not is_hex(datas):
        _context = {
            'Error code': 'TRANS-SENDDATA-01',
            'Cmd': cmd,
            'Datas': datas,
            'ackIsDisabled': ackIsDisabled,
            'waitForResponseIn': waitForResponseIn,
            'InternalSqn': isqn
        }
        self.logging_error( "sendData", context=_context)
        return 'BadData'

    self.ListOfCommands[ isqn ] = {
        'cmd': cmd,
        'datas': datas,
        'ackIsDisabled': ackIsDisabled,
        'waitForResponseIn': waitForResponseIn,
        'Status': 'SENT',
        'TimeStamp': time.time(),
        'Semaphore': self.semaphore_gate._value
    }
    self.statistics._sent += 1
    return write_to_zigate( self, self._connection, bytes.fromhex(  encode_message( cmd, datas)) )

def encode_message( cmd, datas):

    if datas == "":
        length = "0000"
        checksumCmd = get_checksum(cmd, length, "0")
        strchecksum = '0' + checksumCmd if len(checksumCmd) == 1 else checksumCmd
        return ( "01" + zigate_encode(cmd) + zigate_encode(length) + zigate_encode(strchecksum) + "03" )

    length = '%04x' % (len(datas)//2)
    checksumCmd = get_checksum(cmd, length, datas)
    strchecksum = '0' + checksumCmd if len(checksumCmd) == 1 else checksumCmd
    return ( "01" + zigate_encode(cmd) + zigate_encode(length) + zigate_encode(strchecksum) + zigate_encode(datas) + "03" )

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

def write_to_zigate( self, serialConnection, encoded_data ):
    logging_writer( self, 'Debug', "write_to_zigate")

    if self.pluginconf.pluginConf['byPassDzConnection'] and not self.force_dz_communication:
        return native_write_to_zigate( self, serialConnection, encoded_data)
    else:
        return domoticz_write_to_zigate( self, encoded_data)


def domoticz_write_to_zigate( self, encoded_data):
    self._connection.Send(encoded_data, 0)
    return True

def native_write_to_zigate( self, serialConnection, encoded_data):

    if self._transp == "Wifi":
        
        tcpipConnection = self._connection
        tcpiConnectionList = [ tcpipConnection ]
        inputSocket  = outputSocket = [ tcpipConnection ]
        if inputSocket == outputSocket == -1:
            return 'SocketClosed'

        readable, writable, exceptional = select.select(inputSocket, outputSocket, inputSocket)
        if writable:
            try:
                tcpipConnection.send( encoded_data )
            except socket.OSError as e:
                logging_writer( self,  'Error',"Socket %s error %s" %(tcpipConnection, e))
                return 'SocketError'

        elif exceptional:
            logging_writer( self,  'Error',"We have detected an error .... on %s" %inputSocket)
            return 'WifiError'

        return True

    # Serial
    try:
        if serialConnection.is_open:
            nb_write = serialConnection.write( encoded_data )
            if nb_write != len( encoded_data ):
                _context = {
                    'Error code': 'TRANS-WRTZGTE-01',
                    'EncodedData': str(encoded_data),
                    'NbWrite': nb_write,
                }
                self.logging_error(  "write_to_zigate", context=_context)
        else:
            _context = {
                'Error code': 'TRANS-WRTZGTE-02',
                'EncodedData': str(encoded_data),
                'serialConnection': str(serialConnection)
            }
            self.logging_error(  "write_to_zigate port is closed!", context=_context)    
            return 'PortClosed'        

    except TypeError as e:
        #Disconnect of USB->UART occured
        logging_writer( self,  'Error',"write_to_zigate - error while writing %s" %(e))
        return False

    return True

def semaphore_timeout( self, current_command ):
    # Semaphore has been Release due to Timeout
    # In that case we should release the pending command in ListOfCommands
    if len(self.ListOfCommands) == 2:
        if list(self.ListOfCommands.keys())[0] == current_command['InternalSqn']:
            # We remove element [1]
            isqn_to_be_removed = list(self.ListOfCommands.keys())[1]
        else:
            # We remove element [0]
            isqn_to_be_removed = list(self.ListOfCommands.keys())[0]

        _context = {
            'Error code': 'TRANS-SEMAPHORE-01',
            'ListofCmds': dict.copy(self.ListOfCommands),
            'IsqnCurrent': current_command['InternalSqn'],
            'IsqnToRemove': isqn_to_be_removed
        }
        if not self.force_dz_communication:
            self.logging_error( "writerThread Timeout ", context=_context)
        release_command( self, isqn_to_be_removed) 
        return

    # We need to find which Command is in Timeout
    _context = {
        'Error code': 'TRANS-SEMAPHORE-02',
        'ListofCmds': dict.copy(self.ListOfCommands),
        'IsqnCurrent': current_command['InternalSqn'],
        'IsqnToRemove': [],
    }
    for x in list(self.ListOfCommands):
        if x == current_command['InternalSqn']:
            # On going command, this one is the one accepted via the Timeout
            continue
        if time.time() + 8 >= self.ListOfCommands[x]['TimeStamp']:
            # This command has at least 8s life and can be removed
            release_command( self, x)
            _context['IsqnToRemove'].append( x )

    if not self.force_dz_communication:
        self.logging_error( "writerThread Timeout ", context=_context)

def logging_writer(self, logType, message, NwkId = None, _context=None):
    # Log all activties towards ZiGate
    self.log.logging('TransportWrter', logType, message, context = _context)