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
# coding: utf-8 -*-
#
# Author: pipiche38
#

import asyncio
import json
import threading
import time

from contextlib import suppress

import zigpy.application

from Classes.ZigateTransport.sqnMgmt import sqn_init_stack
from Classes.ZigpyTransport.forwarderThread import (start_forwarder_thread,
                                                    stop_forwarder_thread)
from Classes.ZigpyTransport.instrumentation import (
    instrument_log_command_open, instrument_sendData, open_capture_rx_frames)
from Classes.ZigpyTransport.zigpyThread import (
    cleanup_unused_concurrency_state, start_zigpy_thread, stop_zigpy_thread)


class ZigpyTransport(object):
    def __init__(self, ControllerData, pluginParameters, pluginconf, F_out, zigpy_upd_device, zigpy_get_device, zigpy_backup_available, restart_plugin, log, statistics, hardwareid, radiomodule, serialPort, com_specifcs):
        self.zigbee_communication = "zigpy"
        self.pluginParameters = pluginParameters
        self.pluginconf = pluginconf
        self.F_out = F_out  # Function to call to bring the decoded Frame at plugin
        self.ZigpyUpdDevice = zigpy_upd_device
        self.ZigpyGetDevice = zigpy_get_device
        self.ZigpyBackupAvailable = zigpy_backup_available
        self.restart_plugin = restart_plugin
        self.log = log
        self.statistics = statistics
        self.hardwareid = hardwareid
        self._radiomodule = radiomodule
        self._serialPort = serialPort
        self._serialPort_communication_specifics = com_specifcs

        self.version = None
        self.Firmwareversion = None
        self.ControllerIEEE = None
        self.ControllerNWKID = None
        self.ZigateExtendedPanId = None
        self.ZigatePANId = None
        self.ZigateChannel = None
        self.FirmwareBranch = None
        self.FirmwareMajorVersion = None
        self.FirmwareVersion = None
        self.forwarder_running = None
        self.zigpy_running = True
        self.ControllerData = ControllerData

        self.permit_to_join_timer = { "Timer": None, "Duration": None}

        # Semaphore per devices
        self._concurrent_requests_semaphores_list = {}
        self._currently_waiting_requests_list = {}  
        self._currently_not_reachable = []
        self._periodic_reset = None
        
        # Initialise SQN Management
        sqn_init_stack(self)

        self.app: zigpy.application.ControllerApplication | None = None
        
        self.writer_queue = None
        self.forwarder_queue = None
        self.zigpy_loop = None
        self.zigpy_thread = None
        self.forwarder_thread = None
        
        self.captureRxFrame = None
        open_capture_rx_frames(self)

        self.structured_log_command_file_handler = None
        instrument_log_command_open( self)

        self.manual_topology_scan_task = None   # Store topology task when manual started
        self.manual_interference_scan_task = None   # Store topology task when manual started

        self.loop_latency_monitor = None   # Manage the Event loop latency monitoring if enabled
        self.use_of_zigpy_persistent_db = self.pluginconf.pluginConf["enableZigpyPersistentInFile"] or self.pluginconf.pluginConf["enableZigpyPersistentInMemory"]

   
    def open_cie_connection(self):
        self.log.logging("Transport", "Log", f"Radio model {self._radiomodule} Serial Port: {self._serialPort}, Communication specifics: {self._serialPort_communication_specifics}")

        if not self.zigpy_thread:
            start_zigpy_thread(self)
        if not self.forwarder_thread:
            start_forwarder_thread(self)

        # Log running threads. We should have only the main thread (MainThread)
        self.log.logging("Transport", "Log", "Active threads after open_cie_connection:")
        for t in threading.enumerate():
            self.log.logging("Transport", "Log", f"    - Thread {t.name}: alive={t.is_alive()}, ident={t.ident}, daemon={t.daemon}")


    def re_connect_cie(self):
        pass


    def close_cie_connection(self):
        pass


    def thread_transport_shutdown(self):
        self.log.logging(["Transport", "StopProcess"], "Debug", "Starting Zigpy transport shutdown sequence")

        # Helper to stop and join a thread with consistent logging and error handling
        def _stop_and_join(thread_attr: str, running_attr: str, stop_callable, name: str, timeout: float):
            # Attempt to signal the thread to stop
            try:
                if running_attr:
                    setattr(self, running_attr, False)
                if stop_callable:
                    self.log.logging(["Transport", "StopProcess"], "Debug", f"{name} stop requested")
                    stop_callable(self)

            except Exception as e:
                self.log.logging(["Transport", "StopProcess"], "Error", f"Error stopping {name}: {e}")

            # Grab reference then break circular reference on the instance
            try:
                thread = getattr(self, thread_attr, None)
                setattr(self, thread_attr, None)  # break self <-> thread cycle

                self.log.logging(["Transport", "StopProcess"], "Debug", f"Thread object ({name}): {thread}, alive={thread.is_alive() if thread else 'N/A'}")
                self.log.logging(["Transport", "StopProcess"], "Debug", f"Thread ident ({name}) : {thread.ident if thread else 'N/A'}")
                self.log.logging(["Transport", "StopProcess"], "Debug", f"Thread daemon ({name}): {thread.daemon if thread else 'N/A'}")

                if thread:
                    self.log.logging(["Transport", "StopProcess"], "Debug", f"Joining {name} (timeout {timeout}s)")
                    thread.join(timeout=timeout)
                    import gc
                    gc.collect()
                    if thread.is_alive():
                        self.log.logging(["Transport", "StopProcess"], "Error", f"{name} did not terminate within {timeout} seconds")
                        # Provide active thread snapshot for debugging
                        with suppress(Exception):
                            active_threads = threading.enumerate()
                            thread_info = [(t.name, t.ident, t.is_alive()) for t in active_threads]
                            self.log.logging(["Transport", "StopProcess"], "Error", f"Active threads: {thread_info}")
                    else:
                        self.log.logging(["Transport", "StopProcess"], "Debug", f"{name} join completed")
                else:
                    self.log.logging(["Transport", "StopProcess"], "Log", f"{name} not found or not started")
            except Exception as e:
                self.log.logging(["Transport", "StopProcess"], "Error", f"Error joining {name}: {e}")

        # Stop and join forwarder (short timeout)
        _stop_and_join(
            thread_attr="forwarder_thread",
            running_attr="forwarder_running",
            stop_callable=stop_forwarder_thread,
            name="Zigpy forwarder",
            timeout=5,
        )

        # Stop and join zigpy (longer timeout)
        _stop_and_join(
            thread_attr="zigpy_thread",
            running_attr="zigpy_running",
            stop_callable=stop_zigpy_thread,
            name="Zigpy thread",
            timeout=120,
        )

        # --- Summary ---
        self.log.logging(["Transport", "StopProcess"], "Status", "Zigpy transport threads shutdown attempted")


    def sendData(self, cmd, datas, sqn=None, highpriority=False, ackIsDisabled=False, waitForResponseIn=False, NwkId=None):
        """
        Send a command to the Zigbee transport writer queue.

        Args:
            cmd (str): The command identifier.
            datas (Any): The payload data to send (typically a list or dict).
            sqn (int, optional): Sequence number. Defaults to None.
            highpriority (bool, optional): Marks message as high priority for instrumentation. Defaults to False.
            ackIsDisabled (bool, optional): True if APS ACK is disabled. Defaults to False.
            waitForResponseIn (bool, optional): True if response is expected from plugin. Defaults to False.
            NwkId (str, optional): Network ID of the destination device. Defaults to None.
        """

        if self.writer_queue is None:
            return

        _queue = self.loadTransmit()
        if _queue > self.statistics._MaxLoad:
            self.statistics._MaxLoad = _queue

        if self.pluginconf.pluginConf.get("coordinatorCmd", False):
            self.log.logging( "Transport", "Log", f"sendData       - [{sqn}] {cmd} {datas} {NwkId} Queue Length: {_queue}" )

        self.log.logging( "Transport", "Debug", f"===> sendData - Cmd: {cmd} Datas: {datas}" )

        message = {
            "cmd": cmd,
            "datas": datas,
            "NwkId": NwkId,
            "TimeStamp": time.time(),
            "ACKIsDisable": ackIsDisabled,
            "Sqn": sqn
        }

        self.writer_queue.put_nowait(json.dumps(message))

        instrument_sendData(
            self,
            cmd,
            datas,
            sqn,
            message["TimeStamp"],
            highpriority,
            ackIsDisabled,
            waitForResponseIn,
            NwkId
        )
        

    def receiveData(self, message):
        self.log.logging("Transport", "Debug", "===> receiveData for Forwarded - Message %s" % (message))
        if self.forwarder_queue is None:
            return
        self.forwarder_queue.put(message)


    def get_device_ieee( self, nwkid):
        return self.app.get_device_ieee( nwkid )


    # TO be cleaned . This is to make the plugin working
    def update_ZiGate_HW_Version(self, version):
        return


    def update_ZiGate_Version(self, FirmwareVersion, FirmwareMajorVersion):
        return


    def pdm_lock_status(self):
        return False


    def get_writer_queue(self):
        return self.loadTransmit()


    def get_forwarder_queue(self):
        return self.forwarder_queue.qsize()

    def dump_transport_stats(self):
        """Log asyncio task count and semaphore state from the zigpy event loop.

        Called from the main thread; schedules a coroutine in the zigpy loop so
        that asyncio.all_tasks() is valid (it must be called from within the loop).
        """
        if self.zigpy_loop is None or self.zigpy_loop.is_closed():
            return

        async def _log_stats():
            all_tasks = asyncio.all_tasks()
            named = [(t.get_name(), t.done()) for t in all_tasks]
            pending = [n for n, done in named if not done]
            locked_sems = {
                ieee: waiting
                for ieee, waiting in self._currently_waiting_requests_list.items()
                if waiting > 0
            }
            self.log.logging(
                "TransportZigpy", "Log",
                f"ZigpyTransport stats | asyncio_tasks={len(all_tasks)} "
                f"(pending={len(pending)}) | "
                f"writer_queue≈{self.writer_queue.qsize() if self.writer_queue else 'n/a'} | "
                f"devices_with_queued_reqs={locked_sems}"
            )

        asyncio.run_coroutine_threadsafe(_log_stats(), self.zigpy_loop)

    def loadTransmit(self):
        if self.writer_queue is None:
            return 0

        # Periodic cleanup check
        now = time.monotonic()
        if self._periodic_reset is None or now - self._periodic_reset > 3600:
            self._periodic_reset = now
            cleanup_unused_concurrency_state(self)

        def _sem_locked(sem):
            # asyncio.Semaphore.locked() iterates over _waiters deque which can be
            # mutated by the event loop concurrently, raising RuntimeError.
            try:
                return sem.locked()
            except RuntimeError:
                return True  # conservative: treat as locked

        _queue = sum(
            self._currently_waiting_requests_list.get(device, 0) + 1
            for device in list(self._currently_waiting_requests_list)
            if self._concurrent_requests_semaphores_list.get(device) and _sem_locked(self._concurrent_requests_semaphores_list[device])
        )
        
        return max(_queue - 1, 0) + self.writer_queue.qsize()
