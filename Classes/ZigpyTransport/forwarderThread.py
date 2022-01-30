#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import queue
from threading import Thread
from time import sleep

from Classes.ZigpyTransport.instrumentation import time_spent_forwarder
from Classes.ZigpyTransport.tools import handle_thread_error


def start_forwarder_thread(self):
    self.forwarder_thread.start()


def stop_forwarder_thread(self):
    self.forwarder_queue.put("STOP")


def forwarder_thread(self):
    self.log.logging("TransportFrwder", "Status", "ZigpyTransport: thread_processing_and_sending Thread start.")

    while self.running:
        message = None
        # Sending messages ( only 1 at a time )
        try:
            self.log.logging("TransportFrwder", "Debug", "Waiting for next message")
            message = self.forwarder_queue.get()
            if message == "STOP":
                break
            if len(message) == 0:
                continue
            self.statistics._received += 1
            self.log.logging("TransportFrwder", "Debug", "Message to forward: %s" % message)
            forward_message(self, message)
        except queue.Empty:
            # Empty Queue, timeout.
            continue
        except Exception as e:
            self.log.logging("TransportFrwder", "Error", "forwarder_thread - Error while receiving a Coordinator command")

            handle_thread_error(self, e, message)

    self.log.logging("TransportFrwder", "Status", "ZigpyTransport: thread_processing_and_sending Thread stop.")


@time_spent_forwarder()
def forward_message(self, message):
    self.log.logging("TransportFrwder", "Debug", "Receive a message to forward: %s" % (str(message)))
    self.statistics._data += 1
    self.F_out(message)
    self.log.logging("TransportFrwder", "Debug", "message forwarded!!!!")
