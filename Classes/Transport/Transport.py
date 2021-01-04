# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import threading
import Domoticz
import socket
import serial
import queue
import time

from threading import Semaphore
from queue import PriorityQueue, SimpleQueue, Queue

from Classes.Transport.sqnMgmt import sqn_init_stack, sqn_generate_new_internal_sqn
from Classes.Transport.readerThread import open_zigate_and_start_reader, shutdown_reader_thread
from Classes.Transport.writerThread import start_writer_thread
from Classes.Transport.forwarderThread import start_forwarder_thread
from Classes.Transport.tools import initialize_command_protocol_parameters, waiting_for_end_thread, stop_waiting_on_queues
from Classes.Transport.readDecoder import decode_and_split_message

from Modules.zigateConsts import MAX_SIMULTANEOUS_ZIGATE_COMMANDS
class ZigateTransport(object):

    def __init__(self, hardwareid, DomoticzBuild, DomoticzMajor, DomoticzMinor, transport, statistics, pluginconf, F_out, log, serialPort=None, wifiAddress=None, wifiPort=None):
        # Call back function to send back to plugin
        self.F_out = F_out  # Function to call to bring the decoded Frame at plugin

        # Logging
        self.log = log

        # Line management for 0x8001 message
        self.newline_required = True

        # Statistics
        self.statistics = statistics
        self.pluginconf = pluginconf

        # Communication/Transport link attributes
        self.hardwareid = hardwareid
        self._connection = None  # connection handle
        self._ReqRcv = bytearray()  # on going receive buffer
        self._transp = None  # Transport mode USB or Wifi
        self._serialPort = None  # serial port in case of USB
        self._wifiAddress = None  # ip address in case of Wifi
        self._wifiPort = None  # wifi port

        # Monitoring ZiGate PDUs
        self.apdu = None
        self.npdu = None
        
        # Semaphore to manage when to send a commande to ZiGate
        self.semaphore_gate = Semaphore( value = MAX_SIMULTANEOUS_ZIGATE_COMMANDS)

        # Running flag for Thread. Switch to False to stop the Threads
        self.running = True

        # Management of Commands sent to ZiGate
        self.ListOfCommands = {}

        # Writer
        #self.writer_queue = SimpleQueue()
        self.writer_list_in_queue = []
        self.writer_queue = Queue()
        self.writer_thread = None

        # Reader
        self.reader_thread = None

        # Forwarder
        #self.forwarder_queue = SimpleQueue()
        self.forwarder_queue = Queue()
        self.forwarder_thread = None

        # Firmware Management
        self.FirmwareVersion = None
        self.FirmwareMajorVersion = None

        self.firmware_compatibility_mode = False  # 31a and below
        self.firmware_with_aps_sqn = False  # Available from 31d
        self.firmware_with_8012 = False     # Available from 31e
        self.PDMCommandOnly = False

        #DomoticzVersion: 2020.2 (build 12741) is minimum Dz version where full multithread is possible

        if ( DomoticzMajor < 2020 or (DomoticzMajor == 2020 and ( DomoticzMinor < 2 or ( DomoticzMinor == 2 and DomoticzBuild < 12741)))):
            # we will force the Dz communication mecanism.
            Domoticz.Status("ZiGate plugin start with limited capabilities due to Domoticz version below 2020.2 (Build 12741)")
            self.force_dz_communication = True
        else:
            # All ok
            self.force_dz_communication = False


        # Initialise SQN Management
        sqn_init_stack(self)

        # Initialise Command Protocol Parameters
        initialize_command_protocol_parameters( )

        if transport in ( "USB", "DIN", "V2", "PI"):
            self._transp = transport
            self._serialPort = serialPort
        elif str(transport) == "Wifi":
            self._transp = transport
            self._wifiAddress = wifiAddress
            self._wifiPort = wifiPort
        else:
            Domoticz.Error("Unknown Transport Mode: %s" % transport)
            self._transp = 'None'


    def update_ZiGate_Version ( self, FirmwareVersion, FirmwareMajorVersion):
        self.FirmwareVersion = FirmwareVersion
        self.FirmwareMajorVersion = FirmwareMajorVersion

    def thread_transport_shutdown( self ):
        self.running = False

    def pdm_lock_status(self):
        return self.PDMCommandOnly


    def loadTransmit(self):
        # Provide the Load of the Sending Queue
        return self.writer_queue.qsize()

    def sendData(self, cmd, datas, ackIsDisabled=False, waitForResponseIn=False):
        # We receive a send Message command from above ( plugin ), 
        # send it to the sending queue

        if ( cmd, datas ) in self.writer_list_in_queue:
            self.logging_send('Log',"sendData - Warning %s/%s already in queue this command is dropped" %(cmd, datas))
            return None
        self.writer_list_in_queue.append(  (cmd, datas) )

        InternalSqn = sqn_generate_new_internal_sqn(self)
        message = {
            'cmd': cmd,
            'datas': datas,
            'ackIsDisabled': ackIsDisabled,
            'waitForResponseIn': waitForResponseIn,
            'InternalSqn': InternalSqn,
            'TimeStamp': time.time()
        }
        try:
            self.writer_queue.put( message )
        except queue.Full:
            self.logging_send('Error',"sendData - writer_queue Full")

        except Exception as e:
            self.logging_send('Error',"sendData - Error: %s" %e)
        
        return InternalSqn

    def on_message( self, data ):
        # Message sent via Domoticz .
        decode_and_split_message(self, data)


    # Transport / Opening / Closing Communication
    def set_connection(self):
        if self._connection is not None:
            del self._connection
            self._connection = None

        open_connection( self )

    def open_conn(self):
        if not self._connection:
            self.set_connection()
        if (not self.pluginconf.pluginConf['byPassDzConnection'] or self.force_dz_communication) and self._connection:
            self._connection.Connect()
        Domoticz.Status("Connection open: %s" % self._connection)

    def close_conn(self):
        Domoticz.Status("Connection close: %s" % self._connection)

        self.running = False # It will shutdown the Thread 

        if self.pluginconf.pluginConf['byPassDzConnection'] and not self.force_dz_communication:
            shutdown_reader_thread( self )
            waiting_for_end_thread( self )

        else:
            stop_waiting_on_queues( self )
            waiting_for_end_thread( self )
            self._connection.Disconnect()

        self._connection = None

    def re_conn(self):
        Domoticz.Status("Reconnection: %s" % self._connection)
        if self.pluginconf.pluginConf['byPassDzConnection'] and not self.force_dz_communication:
            if self._connection:
                self._connection.close()
                time.sleep(1.0)
        else:
            if self._connection.Connected():
                self.close_conn()

        self.open_conn()

    # Login mecanism
    def logging_send(self, logType, message, NwkId = None, _context=None):
        # Log all activties towards ZiGate
        self.log.logging('TransportTx', logType, message, context = _context)

    def logging_receive(self, logType, message, nwkid=None, _context=None):
        # Log all activities received from ZiGate
        self.log.logging('TransportRx', logType, message, nwkid=nwkid, context = _context)

    def transport_error_context( self, context):
        if context is None:
            context = {}
        context['Queues'] = {
            'ListOfCommands': dict.copy(self.ListOfCommands),
            'writeQueue': str(self.writer_queue.queue),
            'forwardQueue': str(self.forwarder_queue.queue),
            'SemaphoreValue': self.semaphore_gate._value,
            }
        context['Firmware'] = {
            'dzCommunication': self.force_dz_communication,
            'with_aps_sqn': self.firmware_with_aps_sqn ,
            'with_8012': self.firmware_with_8012,
            'nPDU': self.npdu,
            'aPDU': self.apdu,
            }
        context['Sqn Management'] = {
            'sqn_ZCL': self.sqn_zcl,
            'sqn_ZDP': self.sqn_zdp,
            'sqn_APS': self.sqn_aps,
            'current_SQN': self.current_sqn,
            }
        context['inMessage'] = {
            'ReqRcv': str(self._ReqRcv),
        }
        context['Thread'] = {
            'byPassDzCommunication': self.pluginconf.pluginConf['byPassDzConnection'],
            'ThreadName': threading.current_thread().name
        }
        return context

    def logging_receive_error( self, message, Nwkid=None, context=None):
        self.logging_receive('Error', message,  Nwkid, self.transport_error_context( context))


    def logging_send_error( self, message, Nwkid=None, context=None):
        self.logging_send('Error', message,  Nwkid, self.transport_error_context( context))

def open_connection( self ):

    if self._transp in ["USB", "DIN", "PI", "V2"]:
        if self._serialPort.find('/dev/') == -1 and self._serialPort.find('COM') != -1:
            return
        Domoticz.Status("Connection Name: Zigate, Transport: Serial, Address: %s" % (self._serialPort))
        if self.pluginconf.pluginConf['byPassDzConnection'] and not self.force_dz_communication:
            open_zigate_and_start_reader( self, 'serial' )
        else:
            self._connection = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None", Address=self._serialPort, Baud=115200)
        start_writer_thread( self )
        start_forwarder_thread( self )

    elif self._transp == "Wifi":
        Domoticz.Status("Connection Name: Zigate, Transport: TCP/IP, Address: %s:%s" %
                        (self._serialPort, self._wifiPort))
        if self.pluginconf.pluginConf['byPassDzConnection'] and not self.force_dz_communication:
            open_zigate_and_start_reader( self, 'tcpip' )
        else:
            self._connection = Domoticz.Connection(Name="Zigate", Transport="TCP/IP", Protocol="None ", Address=self._wifiAddress, Port=self._wifiPort)
        start_writer_thread( self )
        start_forwarder_thread( self )

    else:
        Domoticz.Error("Unknown Transport Mode: %s" % self._transp)