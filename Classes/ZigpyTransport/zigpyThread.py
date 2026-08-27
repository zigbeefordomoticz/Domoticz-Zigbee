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

"""
zigpyThread.py — Thread entry-point for the Zigpy stack.

This is a thin orchestration layer.  It creates the OS thread, boots an
asyncio event loop inside it, and hands control to the supervisor.

All non-trivial logic lives in the modules imported below:

    supervisor.py   — HA-grade restart supervisor, watchdog, heartbeat
    radioStart.py   — radio config, app startup, post-startup frames
    workerLoop.py   — writer-queue consumer, command dispatch
    zigpySend.py    — Zigbee send helpers, concurrency limiting

Public entry points consumed by Transport.py:
    start_zigpy_thread(self)
    stop_zigpy_thread(self)
    cleanup_unused_concurrency_state(self)   # re-exported from zigpySend
"""

import time
from threading import Thread
import asyncio
import random
import sys
import traceback
from functools import partial

from Classes.ZigpyTransport.supervisor import _cleanup, _supervisor
from Classes.ZigpyTransport.zigpySend import \
    cleanup_unused_concurrency_state  # noqa: F401  (re-export for Transport.py)

from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_0302_frame_content, build_plugin_8009_frame_content,
    build_plugin_8011_frame_content,
    build_plugin_8043_frame_list_node_descriptor,
    build_plugin_8045_frame_list_controller_ep)
from Classes.ZigpyTransport.tools import handle_thread_error
from Modules.macPrefix import DELAY_FOR_VERY_KEY

ERROR_TASK_CREATION_FAILED = 0xB6
SEMAPHORE_TIMEOUT = 60  # seconds
REQUEST_TIMEOUT = 8   # This is a given time for the request to be sent
WAITING_TIME_BETWEEN_REQUESTS = .100
MAX_CONCURRENT_REQUESTS_PER_DEVICE = 1
VERIFY_KEY_DELAY = 6

# ---------------------------------------------------------------------------
# Event loop exception handling
# ---------------------------------------------------------------------------

def _is_benign_startup_get_device_keyerror(exc):
    """
    True if `exc` is the bare KeyError that AppGeneric.get_device() raises
    (shared by every radio backend) when the *coordinator's own* self-lookup
    (self._device, keyed by self.state.node_info.ieee — see zigpy/application.py
    _device property) misses because the coordinator has not been registered
    into zigpy's device table yet.

    This is unrelated to remote devices joining/pairing: handle_join() — the
    actual mechanism that registers a newly-paired device — calls get_device()
    synchronously and catches KeyError inline in its own try/except, so it
    never reaches this handler regardless of timing. Only the coordinator's
    self-lookup, performed internally by zigpy/zigpy_znp from fire-and-forget
    tasks that nobody awaits, surfaces here as an unretrieved task exception.

    get_device() already logs a diagnostic Warning for this case before
    raising, so the resulting "Task exception was never retrieved" ERROR
    traceback adds no information — see issue #2010.
    """
    if not isinstance(exc, KeyError) or exc.args:
        return False
    tb = traceback.extract_tb(exc.__traceback__)
    return bool(tb) and tb[-1].name == "get_device" and tb[-1].filename.endswith("AppGeneric.py")


def _coordinator_registered(self):
    """
    True once the coordinator itself is present in zigpy's device table,
    i.e. once self.app.get_device(ieee=self.app.state.node_info.ieee) — the
    exact self-lookup zigpy/zigpy_znp perform internally as self._device —
    would succeed.

    This is the literal condition whose absence causes the benign startup
    KeyError storm, so checking it directly (instead of guessing a grace
    period) degrades gracefully for exactly as long as the race actually
    lasts — no longer. It also re-arms itself naturally on every radio
    reconnect, since each cycle gets a brand new App instance with an empty
    device table (see radioStart.py, `self.app = App(config)`).
    """
    app = getattr(self, "app", None)
    if app is None:
        return False
    try:
        node_ieee = app.state.node_info.ieee
    except AttributeError:
        return False
    return node_ieee is not None and node_ieee in app.devices


def _zigpy_loop_exception_handler(self, loop, context):
    """
    Custom asyncio exception handler for the Zigpy event loop.

    Downgrades the known-benign, self-healing coordinator-self-lookup
    KeyError described in _is_benign_startup_get_device_keyerror() to a
    Debug log line, but only while _coordinator_registered() is still
    False, i.e. only for the duration of the actual startup race. As soon
    as the coordinator is registered ("Green"), and for the entire runtime
    afterwards — including normal device pairing — behaviour reverts to
    unchanged: any exception, including this same KeyError shape should it
    ever occur for an unrelated reason, is passed through to asyncio's
    default handler.
    """
    exc = context.get("exception")
    if (
        exc is not None
        and _is_benign_startup_get_device_keyerror(exc)
        and not _coordinator_registered(self)
    ):
        self.log.logging(
            "TransportZigpy", "Debug",
            f"Suppressed benign startup get_device KeyError (device not yet pre-loaded): {context.get('message')}",
        )
        return

    loop.default_exception_handler(context)


# ---------------------------------------------------------------------------
# Thread lifecycle
# ---------------------------------------------------------------------------

def stop_zigpy_thread(self):
    """
    Requests a clean shutdown of the Zigpy thread.

    Sets _zigpy_stop_requested so the supervisor exits its restart loop
    without scheduling another run.  Also interrupts any in-progress cycle
    immediately by signalling the current _shutdown_event from the calling
    (Domoticz) thread via call_soon_threadsafe, and enqueues a STOP sentinel
    so worker_loop exits cleanly if it is still processing commands.
    """
    self.log.logging(["TransportZigpy", "StopProcess"], "Debug", "stop_zigpy_thread - Stopping zigpy thread")

    # Tell the supervisor not to restart after the current run ends.
    self._zigpy_stop_requested = True
    self.zigpy_running = False

    # Wake up the current run-cycle immediately (thread-safe: called from outside the loop).
    if self.zigpy_loop and self._shutdown_event:
        self.zigpy_loop.call_soon_threadsafe(self._shutdown_event.set)

    # Also push a STOP sentinel so worker_loop exits without waiting for a command.
    if self.writer_queue:
        self.writer_queue.put_nowait("STOP")

    # Cancel any manually-started long-running tasks.
    if self.manual_topology_scan_task:
        self.manual_topology_scan_task.cancel()

    if self.manual_interference_scan_task:
        self.manual_interference_scan_task.cancel()


def start_zigpy_thread(self):
    """
    Starts the Zigpy thread if it is not already running.

    Sets the appropriate event loop policy for Windows compatibility and
    initializes the thread via setup_zigpy_thread if necessary.
    """
    self.log.logging("TransportZigpy", "Debug", "start_zigpy_thread - Starting Zigpy thread")

    # Set appropriate event loop policy for Windows compatibility
    if sys.platform == "win32" and (3, 8, 0) <= sys.version_info < (3, 9, 0):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Start the Zigpy thread if it's not already running
    if not hasattr(self, 'zigpy_thread') or not self.zigpy_thread or not self.zigpy_thread.is_alive():
        setup_zigpy_thread(self)
    else:
        self.log.logging("TransportZigpy", "Warning", "start_zigpy_thread - Zigpy thread is already running.")

    self.log.logging(["Transport", "StopProcess"], "Debug", f"Thread object: ZigpyCommunication_{self.hardwareid} {self.zigpy_thread}, alive={self.zigpy_thread.is_alive() if self.zigpy_thread else 'N/A'}")
    self.log.logging(["Transport", "StopProcess"], "Debug", f"Thread ident : ZigpyCommunication_{self.hardwareid} {self.zigpy_thread.ident if self.zigpy_thread else 'N/A'}")
    self.log.logging(["Transport", "StopProcess"], "Debug", f"Thread daemon: ZigpyCommunication_{self.hardwareid} {self.zigpy_thread.daemon if self.zigpy_thread else 'N/A'}")


def setup_zigpy_thread(self):
    """
    Sets up and starts the Zigpy thread.

    Creates a new Thread instance targeting zigpy_thread_function and starts it.
    The thread name includes the hardware ID for identification.
    """
    self.log.logging("TransportZigpy", "Debug", "setup_zigpy_thread - Initializing Zigpy thread")

    # Create and start a new thread
    self.zigpy_thread = Thread(name=f"ZigpyCommunication_{self.hardwareid}", target=zigpy_thread_function, args=(self,))
    self.zigpy_thread.daemon = False
    self.zigpy_thread.start()
    self.log.logging("TransportZigpy", "Debug", "setup_zigpy_thread - Zigpy thread started")


def zigpy_thread_function(self):
    """
    Entry point executed inside a dedicated OS thread for the Zigpy stack.

    This function is responsible for:
      - Creating and binding a dedicated asyncio event loop to this thread
      - Starting the asynchronous supervisor task
      - Running the event loop for the lifetime of the Zigbee stack

    Lifecycle:
        1. Apply random startup delay (staggered startup in multi-thread environments)
        2. Create a new asyncio event loop (thread-local)
        3. Store loop reference for cross-layer async operations
        4. Launch the asynchronous supervisor task
        5. Run loop until _supervisor calls loop.stop()
        6. Perform cleanup on exit

    Notes:
        - This thread owns the entire Zigbee async runtime.
        - loop.run_forever() is intentionally used for long-lived execution.
        - _shutdown_event is *not* initialised here; _supervisor creates a fresh
          asyncio.Event for every restart cycle so the loop guard cannot be
          prematurely tripped by a stale set() from a previous run.
        - External shutdown is signalled via _zigpy_stop_requested (bool) which
          stop_zigpy_thread() sets from the Domoticz thread, plus a
          call_soon_threadsafe() on the current cycle's _shutdown_event.
        - A custom exception handler is installed on the loop to downgrade
          the known-benign startup KeyError from AppGeneric.get_device()
          (see _zigpy_loop_exception_handler and issue #2010) instead of
          letting it surface as a misleading ERROR-level traceback.
    """
    self.log.logging("TransportZigpy", "Debug", "zigpyThread starting")

    time.sleep(random.uniform(0.5, 3.5))  # nosec

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    self.zigpy_loop = loop
    loop.set_exception_handler(partial(_zigpy_loop_exception_handler, self))

    # Enable debug mode if specified in configuration
    if self.pluginconf.pluginConf.get("EventLoopInstrumentation", False):
        self.zigpy_loop.set_debug(True)

    loop.create_task(_supervisor(self))

    if self.pluginconf.pluginConf.get("MonitorLoopLatency", False):
        loop_latency_monitoring(self)

    try:
        loop.run_forever()
    finally:
        _cleanup(self, loop)


def loop_latency_monitoring(self):
    """
    Monitors the latency of the event loop and logs warnings if it exceeds a threshold.

    This function should be scheduled to run periodically (e.g., every 10 seconds) to check
    the responsiveness of the event loop. If the latency exceeds a predefined threshold,
    a warning is logged to help identify potential performance issues in the Zigbee stack.
    """
    # Implementation of latency monitoring would go here
        # Always cancel any existing monitor, regardless of config
    if hasattr(self, 'loop_latency_monitor') and self.loop_latency_monitor is not None:
        self.loop_latency_monitor.cancel()
        self.loop_latency_monitor = None

    async def monitor_loop_latency(interval=1.0, threshold=3.5):
        try:
            while True:
                start = time.monotonic()
                await asyncio.sleep(interval)
                delay = time.monotonic() - start - interval
                if delay > 5:
                    self.log.logging("TransportZigpy", "Error", f"Event loop blocked for {delay:.3f}s")
                elif delay > threshold:
                    self.log.logging("TransportZigpy", "Log", f"Event loop blocked for {delay:.3f}s")
        except asyncio.CancelledError:
            self.log.logging("TransportZigpy", "Log", "Event loop monitoring stopped")
            return

    self.loop_latency_monitor = self.zigpy_loop.create_task(monitor_loop_latency())
