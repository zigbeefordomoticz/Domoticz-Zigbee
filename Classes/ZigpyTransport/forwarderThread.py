#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""Forwarder thread helpers for ZigpyTransport.

This module provides helpers to start and stop a dedicated forwarder thread
that forwards messages from an internal queue to the external output
function `self.F_out` owned by the transport instance (passed in as ``self``).

Functions exposed:
- start_forwarder_thread(self): create and start the forwarder thread if not running.
- stop_forwarder_thread(self): request a graceful stop of the forwarder thread.
- forwarder_thread(self): the thread worker that reads from the queue and forwards messages.
- forward_message(self, message): forward a single message via ``self.F_out``.

Notes:
- The implementation stores thread and queue objects on the provided ``self``
    object: ``self.forwarder_thread`` and ``self.forwarder_queue``.
- The module relies on the transport instance to provide logging methods,
    a statistics object, and an ``F_out`` callable to actually send messages.
"""

import queue
from threading import Thread

from Classes.ZigpyTransport.instrumentation import time_spent_forwarder
from Classes.ZigpyTransport.tools import handle_thread_error


def start_forwarder_thread(self):
    """Start the forwarder thread for this transport instance.

    Ensures a named thread (stored as ``self.forwarder_thread``) is created and
    started if it is not already running. The thread function used is
    :func:`forwarder_thread` and the thread will be named using the
    transport's ``hardwareid`` to aid debugging.

    Side effects:
    - sets ``self.forwarder_thread`` to the created Thread object
    - leaves queue and running flags to be created by the worker thread

    Logging is emitted to indicate success or if the thread is already
    running.
    """
    self.log.logging("TransportFrwder", "Debug", "start_forwarder_thread.")
    
    # Start the Zigpy thread if it's not already running
    if not hasattr(self, 'forwarder_thread') or not self.forwarder_thread or not self.forwarder_thread.is_alive():
        self.forwarder_thread = Thread(name="ZigpyForwarder_%s" % self.hardwareid, target=forwarder_thread, args=(self,))
        self.forwarder_thread.daemon = False
        self.forwarder_thread.start()
    else:
        self.log.logging("TransportFrwder", "Error", "start_forwarder_thread - ZigpyForwarder thread is already running.")

    self.log.logging(["TransportFrwder", "StopProcess"], "Debug", f"Thread object: ZigpyForwarder_{self.hardwareid} {self.forwarder_thread}, alive={self.forwarder_thread.is_alive() if self.forwarder_thread else 'N/A'}")
    self.log.logging(["TransportFrwder", "StopProcess"], "Debug", f"Thread ident : ZigpyForwarder_{self.hardwareid} {self.forwarder_thread.ident if self.forwarder_thread else 'N/A'}")
    self.log.logging(["TransportFrwder", "StopProcess"], "Debug", f"Thread daemon: ZigpyForwarder_{self.hardwareid} {self.forwarder_thread.daemon if self.forwarder_thread else 'N/A'}")

def stop_forwarder_thread(self):
    """Request a graceful shutdown of the forwarder thread.

    This will set the running flag on the transport instance so the worker
    loop can exit, and will enqueue a stop sentinel (currently the string
    "STOP") to wake the worker if it is blocked on queue.get().

    The function logs the shutdown request. Note: callers should ensure the
    thread is joined if they require synchronous shutdown.
    """
    self.log.logging(["TransportFrwder", "StopProcess"], "Debug", "stop_forwarder_thread()")
    self.forwarder_running = False

    # Enqueue stop sentinel to wake the forwarder thread if blocked.
    self.forwarder_queue.put("STOP")
    self.log.logging(["TransportFrwder", "StopProcess"], "Debug", "stop_forwarder_thread() - STOP sent!")


def forwarder_thread(self):
    """Worker function run inside the forwarder Thread.

    This function initializes the per-instance queue (``self.forwarder_queue``)
    and the running flag (``self.forwarder_running``) and then enters a loop
    reading messages from the queue and forwarding them via
    :func:`forward_message`.

    Behavior details:
    - Uses ``queue.Queue.get(timeout=1.0)`` so the loop periodically wakes to
      check the running flag and shutdown condition.
    - Treats the string ``"STOP"`` as a sentinel to break the loop.
    - Skips ``None`` or empty messages to avoid processing invalid payloads.
    - Increments ``self.statistics._received`` for each message dequeued.
    - Any exceptions during queue handling are routed to
      :func:`handle_thread_error` and logged; the thread will then continue
      or exit depending on the error and flags.

    This function is intended to be used as the Thread target and will store
    the queue object and running flag on the ``self`` instance.
    """
    self.log.logging(["TransportFrwder", "StopProcess"], "Debug", "ZigpyTransport: Forwarded Thread start.")

    self.forwarder_queue = queue.Queue()
    self.forwarder_running = True

    while self.forwarder_running:
        message = None
        # Sending messages ( only 1 at a time )
        try:
            self.log.logging(["TransportFrwder",], "Debug", "Waiting for next message")
            message = self.forwarder_queue.get(timeout=1.0)

            if not self.forwarder_running:
                self.log.logging(["TransportFrwder", "StopProcess"], "Log", f"Forwarder thread stop in progress via self.forwarder_running: {self.forwarder_running}...")
                break

            if message is None or len(message) == 0:
                continue

            if message == "STOP":
                self.log.logging(["TransportFrwder", "StopProcess"], "Log", f"Forwarder thread stop in progress via message: {message}...")
                break

            self.statistics._received += 1
            self.log.logging(["TransportFrwder",], "Debug", "Message to forward: %s" % message)
            forward_message(self, message)

        except queue.Empty:
            # Empty Queue, timeout.
            continue
        except Exception as e:
            self.log.logging(["TransportFrwder", ], "Error", "forwarder_thread - Error while receiving a Coordinator command")
            handle_thread_error(self, e, message)

    self.log.logging(["TransportFrwder", "StopProcess"], "Status", "++ Forwarder thread stopped. [1/3]")


@time_spent_forwarder()
def forward_message(self, message):
        """Forward a single message using the transport's output callable.

        This function is decorated with the ``time_spent_forwarder`` instrumentation
        and is responsible for the actual hand-off to ``self.F_out``. It also
        updates ``self.statistics._data`` to reflect forwarded payloads and
        emits debug logging before and after the hand-off.

        Parameters
        - message: the payload dequeued by :func:`forwarder_thread` to be sent.

        Notes
        - Exceptions propagated from ``self.F_out`` are not explicitly caught here
            so callers (the worker loop) can handle them via their exception
            handling strategy.
        """
        self.log.logging("TransportFrwder", "Debug", "Receive a message to forward: %s" % (str(message)))
        self.statistics._data += 1
        self.F_out(message)
        self.log.logging("TransportFrwder", "Debug", "message forwarded!!!!")
