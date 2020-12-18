# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz

import queue
from threading import Thread
from Classes.Transport.tools import handle_thread_error
from Classes.Transport.instrumentation import time_spent

def start_forwarder_thread( self ):
    
    if self.forwarder_thread is None:
        self.forwarder_thread = Thread( name="ZiGateForwarder",  target=forwarder_thread,  args=(self,))
        self.forwarder_thread.start()

def forwarder_thread( self ):
    self.logging_receive('Status', "ZigateTransport: thread_processing_and_sending Thread start.")

    while self.running:
        frame = None
        # Sending messages ( only 1 at a time )
        try:
            self.logging_receive( 'Log', "Waiting for next message")
            message = self.forwarder_queue.get( )
            

            if message == 'STOP':
                break

            forward_message( self, message )

        except queue.Empty:
            # Empty Queue, timeout.
            pass

        except Exception as e:
            Domoticz.Error("Error while receiving a ZiGate command: %s" %e)
            handle_thread_error( self, e, 0, 0, frame)

    self.logging_receive('Status',"ZigateTransport: thread_processing_and_sending Thread stop.")

@time_spent( True )
def forward_message( self, message ):

    self.logging_receive( 'Log', "Receive a message to forward: %s" %(message))
    self.statistics._data += 1
    self.F_out(  message )
    self.logging_receive( 'Log', "message forwarded!!!!")    