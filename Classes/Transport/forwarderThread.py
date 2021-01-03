# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz

import queue
from threading import Thread
from Classes.Transport.tools import handle_thread_error
from Classes.Transport.instrumentation import time_spent_forwarder

def start_forwarder_thread( self ):
    
    if self.forwarder_thread is None:
        self.forwarder_thread = Thread( name="ZiGateForwarder_%s" %self.hardwareid,  target=forwarder_thread,  args=(self,))
        self.forwarder_thread.start()

def forwarder_thread( self ):
    logging_forwarder( self,'Status', "ZigateTransport: thread_processing_and_sending Thread start.")

    while self.running:
        message = None
        # Sending messages ( only 1 at a time )
        try:
            logging_forwarder( self, 'Debug', "Waiting for next message")
            message = self.forwarder_queue.get()
            if message == 'STOP':
                break
            forward_message( self, message )

        except queue.Empty:
            # Empty Queue, timeout.
            pass

        except Exception as e:
            _context = {
                'Error code': 'TRANS-FWD-01',
                'Error': e,
                'Message': message,
            }
            self.logging_error( "forwarder_thread - Error while receiving a ZiGate command", context=_context)

            handle_thread_error( self, e, 0, 0, message)

    logging_forwarder( self,'Status',"ZigateTransport: thread_processing_and_sending Thread stop.")

@time_spent_forwarder( )
def forward_message( self, message ):

    logging_forwarder( self, 'Debug', "Receive a message to forward: %s" %(message))
    self.statistics._data += 1
    self.F_out(  message )
    logging_forwarder( self, 'Debug', "message forwarded!!!!")

def logging_forwarder(self, logType, message, NwkId = None, _context=None):
    # Log all activties towards ZiGate
    self.log.logging('TransportFrwder', logType, message, context = _context)