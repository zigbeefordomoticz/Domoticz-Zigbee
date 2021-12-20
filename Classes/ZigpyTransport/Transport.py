


from queue import Queue, PriorityQueue

import time
import json
import zigpy.application
import zigpy.types as t

from threading import Thread
from Classes.Transport.forwarderThread import forwarder_thread
import Domoticz

from Classes.ZigpyTransport.zigpyThread import zigpy_thread, start_zigpy_thread, stop_zigpy_thread
from Classes.ZigpyTransport.forwarderThread import forwarder_thread, start_forwarder_thread, stop_forwarder_thread
from Classes.Transport.sqnMgmt import (sqn_init_stack)
class ZigpyTransport(object): 
    def __init__( self, F_out, zigpy_get_device, log, statistics, hardwareid, radiomodule, serialPort):
        self.zigbee_communitation = "zigpy"
        
        self.F_out = F_out  # Function to call to bring the decoded Frame at plugin
        self.ZigpyGetDevice = zigpy_get_device
        self.log = log
        self.statistics = statistics
        self.hardwareid = hardwareid
        self._radiomodule = radiomodule
        self._serialPort = serialPort
        
        self.version = None
        self.Firmwareversion = None
        self.ZigateIEEE = None
        self.ZigateNWKID = None
        self.ZigateExtendedPanId = None
        self.ZigatePANId = None
        self.ZigateChannel = None
        self.FirmwareBranch = None
        self.FirmwareMajorVersion = None
        self.FirmwareVersion = None    
        self.running = True
        
        # Initialise SQN Management
        sqn_init_stack(self)

        self.app : zigpy.application.ControllerApplication | None = None 
        self.writer_queue = PriorityQueue()
        self.forwarder_queue = Queue()
        self.zigpy_thread = Thread(name="ZigpyCom_%s" % self.hardwareid, target=zigpy_thread, args=(self,))
        self.forwarder_thread = Thread( name="ZigpyForwarder_%s" % self.hardwareid, target=forwarder_thread, args=(self,) )

    def open_zigate_connection(self): 
        start_zigpy_thread( self )
        start_forwarder_thread( self )

    def re_connect_zigate(self):
        pass
    
    def close_zigate_connection(self):
        pass
    
    def thread_transport_shutdown(self):
        Domoticz.Log("Shuting down co-routine")
        stop_zigpy_thread(self)
        stop_forwarder_thread(self)

        self.zigpy_thread.join()
        self.forwarder_thread.join()

    def sendData(self, cmd, datas, highpriority=False, ackIsDisabled=False, waitForResponseIn=False, NwkId=None):
        Domoticz.Log("===> sendData - Cmd: %s Datas: %s" %(cmd, datas))            
        message = {
            "cmd": cmd,
            "datas": datas,
            "NwkId": NwkId,
            "TimeStamp": time.time(),
            "ACKIsDisable": ackIsDisabled
            }
        self.writer_queue.put((99, str(json.dumps(message))))        

    def pdm_lock_status(self):
        return False
    
    def get_zigate_firmware_version(self):
        return { 'Branch': self.FirmwareBranch,  'Model': self.FirmwareMajorVersion, 'Firmware':self.FirmwareVersion}
 
    def get_zigate_ieee(self):
        return "%016x" %t.uint64_t.deserialize(self.app.ieee.serialize())[0]
        #return str(self.app.ieee).replace(':','') 
    def get_zigate_nwkid(self):
        return "%04x" %self.app.nwk
    def get_zigate_extented_panId(self):
        return "%16x" %t.uint64_t.deserialize(self.app.extended_pan_id.serialize())[0] 
    def get_zigate_panId(self):
        return "%04x" %self.app.pan_id
    def get_zigate_channel(self):
        return self.app.channel

    def get_writer_queue(self):
        return self.writer_queue.qsize()
    
    def get_forwarder_queue(self):
        return self.forwarder_queue.qsize()
    
    def loadTransmit(self):
        # Provide the Load of the Sending Queue
        return self.writer_queue.qsize()

    def logging_transport(self, logType, message, NwkId=None, _context=None):
        self.log.logging("Transport", logType, message, context=_context)

    def logging_8002(self, logType, message, NwkId=None, _context=None):
        self.log.logging("Transport8002", logType, message, context=_context)

    def logging_forwarded(self, logType, message, NwkId=None, _context=None):
        self.log.logging("TransportFrwder", logType, message, context=_context)

    def logging_writer(self, logType, message, NwkId=None, _context=None):
        self.log.logging("TransportWrter", logType, message, context=_context)