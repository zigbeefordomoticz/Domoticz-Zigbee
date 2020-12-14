# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import socket
import serial
import queue
import time

from queue import PriorityQueue

from Classes.Transport.sqnMgmt import sqn_init_stack
from Classes.Transport.readerThread import open_zigate_and_start_reader, shutdown_reader_thread

class ZigateTransport(object):

    def __init__(self, transport, statistics, pluginconf, F_out, log, serialPort=None, wifiAddress=None, wifiPort=None):
        # Logging
        self.log = log

        # Statistics
        self.statistics = statistics
        self.pluginconf = pluginconf

        # Communication/Transport link attributes
        self._connection = None  # connection handle
        self._ReqRcv = bytearray()  # on going receive buffer
        self._transp = None  # Transport mode USB or Wifi
        self._serialPort = None  # serial port in case of USB
        self._wifiAddress = None  # ip address in case of Wifi
        self._wifiPort = None  # wifi port

        # Writer
        self.writer_prio_queue = PriorityQueue()
        self.writer_thread = None

        # Reader
        self.reader_thread = None

        # Forwarder
        self.forwarder_prio_queue = PriorityQueue()
        self.forwarder_thread = None

        # Initialise SQN Management
        sqn_init_stack(self)

        self.running = True
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

    def loadTransmit(self):
        # Provide the Load of the Sending Queue
        return self.writer_prio_queue.qsize()

    def sendData(self, cmd, datas, ackIsDisabled=False, waitForResponseIn=False):
        # We receive a send Message command from above ( plugin ), 
        # send it to the sending queue

        message = {
        'cmd': cmd,
        'datas': datas,
        'ackIsDisabled': ackIsDisabled,
        'waitForResponseIn': waitForResponseIn
        }
        self.writer_prio_queue.put( 5, message ) # Prio 5 to allow prio 1 if we have to retransmit 


    # Transport / Opening / Closing Communication
    def set_connection(self):
        if self._connection is not None:
            del self._connection
            self._connection = None

        if self._transp in ["USB", "DIN", "PI", "V2"]:
            if self._serialPort.find('/dev/') != -1 or self._serialPort.find('COM') != -1:
                Domoticz.Status("Connection Name: Zigate, Transport: Serial, Address: %s" % (self._serialPort))

                if self.pluginconf.pluginConf['MultiThreaded']:
                    open_zigate_and_start_reader( self, 'serial' )
                    self.open_serial( )
                else:
                    self._connection = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None", Address=self._serialPort, Baud=BAUDS)

        elif self._transp == "Wifi":
            Domoticz.Status("Connection Name: Zigate, Transport: TCP/IP, Address: %s:%s" %
                            (self._serialPort, self._wifiPort))
            if self.pluginconf.pluginConf['MultiThreaded']:
                open_zigate_and_start_reader( self, 'tcpip' )
                self.open_tcpip(  )
            else:
                self._connection = Domoticz.Connection(Name="Zigate", Transport="TCP/IP", Protocol="None ", Address=self._wifiAddress, Port=self._wifiPort)

        else:
            Domoticz.Error("Unknown Transport Mode: %s" % self._transp)

    def open_conn(self):
        if not self._connection:
            self.set_connection()
        if not self.pluginconf.pluginConf['MultiThreaded'] and self._connection:
            self._connection.Connect()
        Domoticz.Status("Connection open: %s" % self._connection)

    def close_conn(self):
        Domoticz.Status("Connection close: %s" % self._connection)
        self.running = False # It will shutdown the Thread 
    
        if self.pluginconf.pluginConf['MultiThreaded']:
            shutdown_reader_thread( self )

        else:
            self._connection.Disconnect()

        self._connection = None

    def re_conn(self):
        Domoticz.Status("Reconnection: %s" % self._connection)
        if self.pluginconf.pluginConf['MultiThreaded']:
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

    def logging_send_error( self, message, Nwkid=None, context=None):
        if context is None:
            context = {}
        context['Firmware'] = {
                'Firmware Version': self.FirmwareVersion,
                'Firmware Major': self.FirmwareMajorVersion
                }
        context['Queues'] = {
            '8000 Queue':     list(self._waitFor8000Queue),
            '8011 Queue':     list(self._waitFor8011Queue),
            '8012 Queue':     list(self._waitFor8012Queue),
            'Send Queue':     list(self.zigateSendQueue),
            'ListOfCommands': dict(self.ListOfCommands),
            }
        context['Firmware'] = {
            'zmode': self.zmode,
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

        message += " Error Code: %s" %context['Error code']
        self.logging_send('Error', message,  Nwkid, context)

    # Give Load indication
    def loadTransmit(self):
        # Provide the Load of the Sending Queue
        return len(self.zigateSendQueue)

