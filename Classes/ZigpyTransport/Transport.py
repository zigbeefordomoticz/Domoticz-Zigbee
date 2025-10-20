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

import json
import threading
import time

import zigpy.application

from Classes.ZigateTransport.sqnMgmt import sqn_init_stack
from Classes.ZigpyTransport.forwarderThread import (start_forwarder_thread,
                                                    stop_forwarder_thread)
from Classes.ZigpyTransport.instrumentation import (
    instrument_log_command_open, instrument_sendData, open_capture_rx_frames)
from Classes.ZigpyTransport.zigpyThread import (
    _cleanup_unused_concurrency_state, start_zigpy_thread, stop_zigpy_thread)


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
        self.running = True
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

        self.use_of_zigpy_persistent_db = self.pluginconf.pluginConf["enableZigpyPersistentInFile"] or self.pluginconf.pluginConf["enableZigpyPersistentInMemory"]

   
    def open_cie_connection(self):
        self.log.logging("Transport", "Log", f"Radio model {self._radiomodule} Serial Port: {self._serialPort}, Communication specifics: {self._serialPort_communication_specifics}")

        start_zigpy_thread(self)
        start_forwarder_thread(self)


    def re_connect_cie(self):
        pass


    def close_cie_connection(self):
        pass


    def thread_transport_shutdown(self):
        self.log.logging("Transport", "Debug", "Starting Zigpy transport shutdown sequence")

        # --- Stop Zigpy Thread ---
        try:
                self.log.logging("Transport", "Debug", "Stopping zigpy thread")
                stop_zigpy_thread(self)
                self.log.logging("Transport", "Debug", "Zigpy thread stop requested")
        except Exception as e:
            self.log.logging("Transport", "Error", f"Error stopping zigpy thread: {e}")

        # --- Stop Forwarder Thread ---
        try:
                stop_forwarder_thread(self)
                self.log.logging("Transport", "Debug", "Zigpy forwarder stop requested")
        except Exception as e:
            self.log.logging("Transport", "Error", f"Error stopping zigpy forwarder thread: {e}")

        # --- Join Zigpy Thread ---
        try:
            thread = getattr(self, "zigpy_thread", None)
            if thread is not None:
                self.log.logging("Transport", "Debug", "Joining zigpy thread (timeout 120s)")
                thread.join(timeout=120)
                if thread.is_alive():
                    self.log.logging("Transport", "Error", "Zigpy thread did not terminate within 120 seconds")
                    active_threads = threading.enumerate()
                    thread_info = [(t.name, t.ident, t.is_alive()) for t in active_threads]
                    self.log.logging("Transport", "Error", f"Active threads: {thread_info}")
                else:
                    self.log.logging("Transport", "Debug", "Zigpy thread join completed")
            else:
                self.log.logging("Transport", "Log", "Zigpy thread not found or not started")
        except Exception as e:
            self.log.logging("Transport", "Error", f"Error joining zigpy thread: {e}")

        # --- Join Forwarder Thread ---
        try:
            thread = getattr(self, "forwarder_thread", None)
            if thread is not None:
                self.log.logging("Transport", "Debug", "Joining zigpy forwarder thread (timeout 5s)")
                thread.join(timeout=5)
                if thread.is_alive():
                    self.log.logging("Transport", "Error", "Forwarder thread did not terminate within 5 seconds")
                else:
                    self.log.logging("Transport", "Debug", "Forwarder join completed")
            else:
                self.log.logging("Transport", "Log", "Forwarder thread not found or not started")
        except Exception as e:
            self.log.logging("Transport", "Error", f"Error joining forwarder thread: {e}")

        # --- Summary ---
        self.log.logging("Transport", "Status", "Zigpy transport threads shutdown attempted")


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

    def loadTransmit(self):
        if self.writer_queue is None:
            return 0

        # Periodic cleanup check
        now = time.monotonic()
        if self._periodic_reset is None or now - self._periodic_reset > 3600:
            self._periodic_reset = now
            _cleanup_unused_concurrency_state(self)

        _queue = sum(
            self._currently_waiting_requests_list.get(device, 0) + 1
            for device in list(self._currently_waiting_requests_list)
            if self._concurrent_requests_semaphores_list.get(device) and self._concurrent_requests_semaphores_list[device].locked()
        )
        
        return max(_queue - 1, 0) + self.writer_queue.qsize()
