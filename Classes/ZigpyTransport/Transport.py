# coding: utf-8 -*-
#
# Author: pipiche38
#

import json
import time

import zigpy.application
import zigpy.types as t

from Classes.ZigateTransport.sqnMgmt import sqn_init_stack
from Classes.ZigpyTransport.forwarderThread import (start_forwarder_thread,
                                                    stop_forwarder_thread)
from Classes.ZigpyTransport.instrumentation import (
    instrument_log_command_open, instrument_sendData, open_capture_rx_frames)
from Classes.ZigpyTransport.zigpyThread import (start_zigpy_thread,
                                                stop_zigpy_thread)


class ZigpyTransport(object):
    def __init__(self, ControllerData, pluginParameters, pluginconf, F_out, zigpy_upd_device, zigpy_get_device, zigpy_backup_available, restart_plugin, log, statistics, hardwareid, radiomodule, serialPort):
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
        start_zigpy_thread(self)
        start_forwarder_thread(self)

    def re_connect_cie(self):
        pass

    def close_cie_connection(self):
        pass

    def thread_transport_shutdown(self):
        self.log.logging("Transport", "Debug", "Shuting down co-routine")
        stop_zigpy_thread(self)
        stop_forwarder_thread(self)

        self.zigpy_thread.join()
        self.forwarder_thread.join()

    def sendData(self, cmd, datas, sqn=None, highpriority=False, ackIsDisabled=False, waitForResponseIn=False, NwkId=None):
        
        if self.writer_queue is None:
            return

        _queue = self.loadTransmit()
        if _queue > self.statistics._MaxLoad:
            self.statistics._MaxLoad = _queue

        if self.pluginconf.pluginConf["coordinatorCmd"]:
            self.log.logging(
                "Transport",
                "Log",
                "sendData       - [%s] %s %s %s Queue Length: %s"
                % (sqn, cmd, datas, NwkId, _queue),
            )

        self.log.logging("Transport", "Debug", "===> sendData - Cmd: %s Datas: %s" % (cmd, datas))

        message = {"cmd": cmd, "datas": datas, "NwkId": NwkId, "TimeStamp": time.time(), "ACKIsDisable": ackIsDisabled, "Sqn": sqn}
        self.writer_queue.put_nowait(json.dumps(message))
        instrument_sendData( self, cmd, datas, sqn, message["TimeStamp"], highpriority, ackIsDisabled, waitForResponseIn, NwkId )
        

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
        # Provide the Load of the Sending Queue
        #for device in list(self._currently_waiting_requests_list):
        #    _queue += self._currently_waiting_requests_list[device]
        #return self.writer_queue.qsize()
        if self.writer_queue is None:
            return 0
        _queue = sum(self._currently_waiting_requests_list[device] + 1 for device in list(self._currently_waiting_requests_list) if self._concurrent_requests_semaphores_list[device].locked())
        _ret_value = max(_queue - 1, 0) + self.writer_queue.qsize()
        self.log.logging("Transport", "Debug", "Load: PluginQueue: %3s ZigpyQueue: %3s => %s" %(self.writer_queue.qsize(), _queue, _ret_value ))
        return _ret_value