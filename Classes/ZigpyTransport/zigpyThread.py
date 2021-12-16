
import asyncio
import binascii
import json
import logging
import queue
from typing import Any, Optional

import Domoticz
import zigpy.appdb
import zigpy.config
import zigpy.device
import zigpy.exceptions
import zigpy.group
import zigpy.ota
import zigpy.quirks
import zigpy.state
import zigpy.topology
import zigpy.types as t
import zigpy.util
import zigpy.zcl
import zigpy.zdo
import zigpy.zdo.types as zdo_types
import zigpy_zigate
import zigpy_zigate.zigbee.application
import zigpy_znp.zigbee.application
from Classes.ZigpyTransport.AppZigate import App_zigate
from Classes.ZigpyTransport.AppZnp import App_znp
from Classes.ZigpyTransport.nativeCommands import (NATIVE_COMMANDS_MAPPING,
                                                   native_commands)
from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)

LOGGER = logging.getLogger(__name__)
    

def start_zigpy_thread(self):
    Domoticz.Log("start_zigpy_thread - Starting zigpy thread")
    self.zigpy_thread.start()

def stop_zigpy_thread(self):
    Domoticz.Log("stop_zigpy_thread - Stopping zigpy thread")
    self.writer_queue.put( (0, "STOP") )
    self.zigpy_running = False
    
def zigpy_thread(self):
    Domoticz.Log("zigpy_thread - Starting zigpy thread")
    self.zigpy_running = True
    asyncio.run( radio_start (self, self._radiomodule, self._serialPort) )  

def build_plugin_frame_content(sender, profile, cluster, src_ep, dst_ep, message, receiver=0x0000, src_addrmode=0x02, dst_addrmode=0x02):
        payload = binascii.hexlify(message).decode('utf-8')
        ProfilID = "%04x" %profile
        ClusterID = "%04x" %cluster
        SourcePoint = "%02x" %src_ep
        DestPoint = "%02x" %dst_ep
        SourceAddressMode = "%02x" %src_addrmode
        SourceAddress = "%04x" %sender.nwk
        DestinationAddressMode = "%02x" %dst_addrmode   
        DestinationAddress = "%04x" %0x0000
        Payload = payload

        frame_payload = "00" + ProfilID + ClusterID + SourcePoint + DestPoint + SourceAddressMode + SourceAddress
        frame_payload += DestinationAddressMode + DestinationAddress + Payload
        
        plugin_frame = "01"                                  # 0:2
        plugin_frame += "8002"                               # 2:4 MsgType 0x8002
        plugin_frame += "%04x" % ((len(frame_payload)//2)+1) # 6:10 lenght
        plugin_frame += "%02x" % 0xff                        # 10:12 CRC set to ff but would be great to  compute it
        plugin_frame += frame_payload
        plugin_frame += "%02x" %sender.lqi
        plugin_frame += "03"
        
        return plugin_frame

async def radio_start(self, radiomodule, serialPort, auto_form=False ):

    Domoticz.Log("In radio_start")
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',datefmt='%Y-%m-%d:%H:%M:%S',level=logging.DEBUG)
    
    # Import the radio library
    conf = {CONF_DEVICE: {"path": serialPort}}
    if radiomodule == 'zigate':
        self.app = App_zigate (conf) 
        
    elif radiomodule == 'znp':
        self.app = App_znp (conf) 

    await self.app.startup(True)  
    self.version = None

    self.FirmwareBranch = "00"  # 00 Production, 01 Development 
    self.FirmwareMajorVersion = "04" # 03 PDM Legcay, 04 PDM Opti, 05 PDM V2
    self.FirmwareVersion = "0320"
    self.running = True
    
    Domoticz.Log("PAN ID:               0x%04x" %self.app.pan_id)
    Domoticz.Log("Extended PAN ID:      0x%08x" %self.app.extended_pan_id)
    Domoticz.Log("Channel:              %d" %self.app.channel)
    Domoticz.Log("Device IEEE:          %s" %self.app.ieee)
    Domoticz.Log("Device NWK:           0x%04x" %self.app.nwk)

    #await self.app.permit_ncp(time_s=240)

    # Run forever
    Domoticz.Log("Starting work loop")
    
    # Set Call_handler to send message back to F_OUT
    self.app.set_callback_message ( self.F_out )

    await worker_loop(self)

    Domoticz.Log("Exiting work loop")

    await self.app.shutdown()
    Domoticz.Log("Exiting co-rounting radio_start")

async def worker_loop(self):
    self.logging_writer("Status", "worker_loop - ZigyTransport: worker_loop start.")
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',datefmt='%Y-%m-%d:%H:%M:%S',level=logging.DEBUG)
    
    while self.zigpy_running:        
        # self.logging_writer( 'Debug', "Waiting for next command Qsize: %s" %self.writer_queue.qsize())
        if self.writer_queue is None:
            break
        try:
            prio, entry = self.writer_queue.get(False)
        except queue.Empty:
            await asyncio.sleep(.5)
            continue
            
        if entry == "STOP":
            break
        
        if self.writer_queue.qsize() > self.statistics._MaxLoad:
            self.statistics._MaxLoad = self.writer_queue.qsize()
    
        data = json.loads(entry)
        
        try:
            if data["cmd"] == "PERMIT-TO-JOIN":
                duration = data["datas"]["Duration"] 
                if duration == 0xff:
                    duration = 0xfe
                await self.app.permit(time_s=duration)

            elif   data["cmd"] in NATIVE_COMMANDS_MAPPING:
                await native_commands(self, data["cmd"], data["datas"] )

            elif data["cmd"] == "RAW-COMMAND":
                await process_raw_command( self, data["datas"], data["ACKIsDisable"])

        except Exception as e:
            self.logging_writer("Error", "Error while receiving a ZiGate command: %s" % e)
            handle_thread_error(self, e, 0, 0, "None")

        
    self.logging_writer("Status", "ZigyTransport: writer_thread Thread stop.")

async def process_raw_command( self, data, AckIsDisable=False):
    #data = {
    #    'Profile': int(profileId, 16),
    #    'Cluster': int(cluster, 16),
    #    'TargetNwk': int(targetaddr, 16),
    #    'TargetEp': int(dest_ep, 16),
    #    'SrcEp': int(zigate_ep, 16),
    #    'Sqn': None,
    #    'payload': payload,
    #    }
    Profile = data["Profile"]
    Cluster = data["Cluster"]
    NwkId = data["TargetNwk"]
    dEp = data["TargetEp"]
    sEp = data["SrcEp"]
    payload = bytes.fromhex(data["payload"])
    sequence = self.app.get_sequence()
    addressmode = data["AddressMode"]
    enableAck = not AckIsDisable
    
    self.logging_writer("Log", "ZigyTransport: process_raw_command ready to request %04x %04x %02x %s %02x %s" %(
        NwkId, Cluster, sequence, payload, addressmode, enableAck ))
    if addressmode == 0x01:
        # Group Mode
        await self.app.mrequest( NwkId, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=enableAck, use_ieee=False)
    elif addressmode in (0x02,0x07):
        # Short
        destination = zigpy.device.Device(self.app, None, NwkId)
        await self.app.request( destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=enableAck, use_ieee=False)
    elif addressmode in ( 0x03, 0x08):
        destination = zigpy.device.Device(self.app, NwkId, None)
        await self.app.request( destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=enableAck, use_ieee=False)

def handle_thread_error(self, e, nb_in, nb_out, data):
    trace = []
    tb = e.__traceback__
    self.logging_transport("Error","'%s' failed '%s'" % (tb.tb_frame.f_code.co_name, str(e)))
    while tb is not None:
        trace.append(
            {"Module": tb.tb_frame.f_code.co_filename, "Function": tb.tb_frame.f_code.co_name, "Line": tb.tb_lineno}
        )
        self.logging_transport("Error",
            "----> Line %s in '%s', function %s"
            % (
                tb.tb_lineno,
                tb.tb_frame.f_code.co_filename,
                tb.tb_frame.f_code.co_name,
            )
        )
        tb = tb.tb_next

    context = {
        "Error Code": "TRANS-THREADERROR-01",
        "Type:": str(type(e).__name__),
        "Message code:": str(e),
        "Stack Trace": str(trace),
        "nb_in": nb_in,
        "nb_out": nb_out,
        "Data": str(data),
    }
    self.logging_transport("Error", "handle_error_in_thread ", _context=context)

