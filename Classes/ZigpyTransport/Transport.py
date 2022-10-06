# coding: utf-8 -*-
#
# Author: pipiche38
#

import json
import time
from queue import PriorityQueue, Queue
from threading import Thread

import zigpy.application
import zigpy.types as t
from Classes.ZigateTransport.sqnMgmt import sqn_init_stack
from Classes.ZigpyTransport.forwarderThread import (forwarder_thread,
                                                    start_forwarder_thread,
                                                    stop_forwarder_thread)
from Classes.ZigpyTransport.zigpyThread import (start_zigpy_thread,
                                                stop_zigpy_thread,
                                                zigpy_thread)


class ZigpyTransport(object):
    def __init__(self, ControllerData, pluginParameters, pluginconf, F_out, zigpy_upd_device, zigpy_get_device, zigpy_backup_available, log, statistics, hardwareid, radiomodule, serialPort):
        self.zigbee_communication = "zigpy"
        self.pluginParameters = pluginParameters
        self.pluginconf = pluginconf
        self.F_out = F_out  # Function to call to bring the decoded Frame at plugin
        self.ZigpyUpdDevice = zigpy_upd_device
        self.ZigpyGetDevice = zigpy_get_device
        self.ZigpyBackupAvailable = zigpy_backup_available
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
        
        self.log.logging("Transport", "Log", "ZigpyTransport __init__")
        
        # Initialise SQN Management
        sqn_init_stack(self)

        self.app: zigpy.application.ControllerApplication | None = None
        
        self.writer_queue = Queue()
        self.forwarder_queue = Queue()
        self.zigpy_loop = None
        self.zigpy_thread = None
        self.forwarder_thread = None

    def open_cie_connection(self):
        start_zigpy_thread(self)
        start_forwarder_thread(self)

    def re_connect_cie(self):
        pass

    def close_cie_connection(self):
        pass

    def thread_transport_shutdown(self):
        self.log.logging("Transport", "Status", "Shuting down co-routine")
        stop_zigpy_thread(self)
        stop_forwarder_thread(self)

        self.zigpy_thread.join()
        self.forwarder_thread.join()

    def sendData(self, cmd, datas, sqn=None, highpriority=False, ackIsDisabled=False, waitForResponseIn=False, NwkId=None):
        _queue = self.loadTransmit()
        if _queue > self.statistics._MaxLoad:
            self.statistics._MaxLoad = _queue

        if self.pluginconf.pluginConf["debugzigateCmd"]:
            self.log.logging(
                "Transport",
                "Log",
                "sendData       - [%s] %s %s %s Queue Length: %s"
                % (sqn, cmd, datas, NwkId, _queue),
            )

        self.log.logging("Transport", "Debug", "===> sendData - Cmd: %s Datas: %s" % (cmd, datas))
        message = {"cmd": cmd, "datas": datas, "NwkId": NwkId, "TimeStamp": time.time(), "ACKIsDisable": ackIsDisabled, "Sqn": sqn}
        self.writer_queue.put(str(json.dumps(message)))

    def receiveData(self, message):
        self.log.logging("Transport", "Debug", "===> receiveData for Forwarded - Message %s" % (message))
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
        _queue = sum(self._currently_waiting_requests_list[device] + 1 for device in list(self._currently_waiting_requests_list) if self._concurrent_requests_semaphores_list[device].locked())
        _ret_value = max(_queue - 1, 0) + self.writer_queue.qsize()
        self.log.logging("Transport", "Debug", "Load: PluginQueue: %3s ZigpyQueue: %3s => %s" %(self.writer_queue.qsize(), _queue, _ret_value ))
        return _ret_value
