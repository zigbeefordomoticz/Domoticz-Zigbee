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

from Classes.Transport.tools import handle_thread_error

def start_writer_thread( self ):

    if self.writer_thread is None:
        self.writer_thread = Thread( name="ZiGateWriter",  target=writer_thread,  args=(self,))
        self.writer_thread.start()

def writer_thread( self ):
    self.logging_send('Status', "ZigateTransport: thread_processing_and_sending Thread start.")

    while self.running:
        frame = None
        # Sending messages ( only 1 at a time )
        try:
            self.logging_send( 'Debug', "Waiting for next command Qsize: %s" %self.writer_queue.qsize())
            command = self.writer_queue.get( )

            self.logging_send( 'Debug', "New command received:  %s" %(command))

            if isinstance( command, dict ) and 'cmd' in command and 'datas' in command and 'ackIsDisabled' in command and 'waitForResponseIn' in command and 'InternalSqn' in command:
                if self.writer_queue.qsize() > self.statistics._MaxLoad:
                    self.statistics._MaxLoad = self.writer_queue.qsize()
                self.statistics._Load = self.writer_queue.qsize()

                self.logging_send( 'Debug', "Waiting for a write slot . Semaphore %s ATTENTION NO TIMEOUT FOR TEST PURPOSES" %(self.semaphore_gate._value))

                # Now we will block on Semaphore to serialize and limit the number of concurent commands on ZiGate
                # By using the Semaphore Timeout , we will make sure that the Semaphore is not acquired for ever.
                # However, if the Sem is relaed due to Timeout, we will not be notified !
                self.semaphore_gate.acquire( blocking = True, timeout = None) # Blocking until 8s Tiemout
                self.logging_send( 'Debug', "============= semaphore %s given ============== Len: ListOfCmd %s" %(self.semaphore_gate._value, len(self.ListOfCommands)))
        
                thread_sendData( self, command['cmd'], command['datas'], command['ackIsDisabled'], command['waitForResponseIn'], command['InternalSqn'])
                self.logging_send( 'Debug', "Command sent!!!! %s" %command)

            elif command == 'STOP':
                break

            else:
                self.logging_send( 'Error', "Hops ... Don't known what to do with that %s" %command)

        except queue.Empty:
            # Empty Queue, timeout.
            pass

        except Exception as e:
            self.logging_send( 'Error',"Error while receiving a ZiGate command: %s" %e)
            handle_thread_error( self, e, 0, 0, frame)

    self.logging_send('Status',"ZigateTransport: thread_processing_and_sending Thread stop.")


def thread_sendData(self, cmd, datas, ackIsDisabled, waitForResponseIn, isqn ):
    self.logging_send('Debug', "thread_sendData")
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
        self.logging_send_error( "sendData", context=_context)
        return None

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
    write_to_zigate( self, self._connection, bytes.fromhex(  encode_message( cmd, datas)) )

def encode_message( cmd, datas):

    if datas == "":
        length = "0000"
        checksumCmd = get_checksum(cmd, length, "0")
        strchecksum = '0' + checksumCmd if len(checksumCmd) == 1 else checksumCmd
        return ( "01" + zigate_encode(cmd) + zigate_encode(length) + zigate_encode(strchecksum) + "03" )

    else:
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
    self.logging_send('Debug', "write_to_zigate")

    if self._transp == "Wifi":
        tcpipConnection = self._connection
        tcpiConnectionList = [ tcpipConnection ]
        inputSocket  = outputSocket = [ tcpipConnection ]
        readable, writable, exceptional = select.select(inputSocket, outputSocket, inputSocket)
        if writable:
            try:
                tcpipConnection.send( encoded_data )
            except socket.OSError as e:
                self.logging_send( 'Error',"Socket %s error %s" %(tcpipConnection, e))

        elif exceptional:
            self.logging_send( 'Error',"We have detected an error .... on %s" %inputSocket)
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
        self.logging_send( 'Error',"serial_read_from_zigate - error while writing %s" %(e))