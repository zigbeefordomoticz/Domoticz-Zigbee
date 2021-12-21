
import asyncio
import binascii
import json
import logging
import queue
from typing import Any, Optional

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
from zigpy.exceptions import DeliveryError, InvalidResponse
from Classes.ZigpyTransport.AppZigate import App_zigate
from Classes.ZigpyTransport.AppZnp import App_znp
from Classes.ZigpyTransport.nativeCommands import (NATIVE_COMMANDS_MAPPING,
                                                   native_commands)
from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)
from Classes.ZigpyTransport.tools import handle_thread_error

LOGGER = logging.getLogger(__name__)
    

def start_zigpy_thread(self):
    self.log.logging("TransportWrter",  "Debug","start_zigpy_thread - Starting zigpy thread")
    self.zigpy_thread.start()

def stop_zigpy_thread(self):
    self.log.logging("TransportWrter",  "Debug","stop_zigpy_thread - Stopping zigpy thread")
    self.writer_queue.put( (0, "STOP") )
    self.zigpy_running = False
    
def zigpy_thread(self):
    self.log.logging("TransportWrter",  "Debug","zigpy_thread - Starting zigpy thread")
    self.zigpy_running = True
    asyncio.run( radio_start (self, self._radiomodule, self._serialPort) )  

def callBackGetDevice (nwk,ieee):
    return None

async def radio_start(self, radiomodule, serialPort, auto_form=False ):

    self.log.logging("TransportWrter",  "Debug","In radio_start")
    #if self.log:
    #    self.log.enable_zigpy_login()
    #logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',datefmt='%Y-%m-%d:%H:%M:%S',level=logging.DEBUG)
    
    # Import the radio library
    conf = {CONF_DEVICE: {"path": serialPort}}
    if radiomodule == 'zigate':
        self.app = App_zigate (conf) 
        
    elif radiomodule == 'znp':
        self.app = App_znp (conf) 

    await self.app.startup (self.receiveData, callBackGetDevice=self.ZigpyGetDevice, auto_form=True, log=self.log)  
    self.version = None

    self.FirmwareBranch = "00"  # 00 Production, 01 Development 
    self.FirmwareMajorVersion = "04" # 03 PDM Legcay, 04 PDM Opti, 05 PDM V2
    self.FirmwareVersion = "0320"
    self.running = True
    
    self.log.logging("TransportWrter",  "Debug","PAN ID:               0x%04x" %self.app.pan_id)
    self.log.logging("TransportWrter",  "Debug","Extended PAN ID:      0x%s" %self.app.extended_pan_id)
    self.log.logging("TransportWrter",  "Debug","Channel:              %d" %self.app.channel)
    self.log.logging("TransportWrter",  "Debug","Device IEEE:          %s" %self.app.ieee)
    self.log.logging("TransportWrter",  "Debug","Device NWK:           0x%04x" %self.app.nwk)

    #await self.app.permit_ncp(time_s=240)

    # Run forever
    await worker_loop(self)

    await self.app.shutdown()
    self.log.logging("TransportWrter",  "Debug","Exiting co-rounting radio_start")

async def worker_loop(self):
    self.log.logging("TransportWrter", "Debug", "worker_loop - ZigyTransport: worker_loop start.")

    while self.zigpy_running:
        # self.log.logging("TransportWrter",  'Debug', "Waiting for next command Qsize: %s" %self.writer_queue.qsize())
        if self.writer_queue is None:
            break
        try:
            prio, entry = self.writer_queue.get(False)
            
        except queue.Empty:
            await asyncio.sleep(.250)
            continue

        if entry == "STOP":
            break

        if self.writer_queue.qsize() > self.statistics._MaxLoad:
            self.statistics._MaxLoad = self.writer_queue.qsize()

        data = json.loads(entry)
        self.log.logging("TransportWrter", "Debug","got command %s" %data)

        try:
            if data["cmd"] == "PERMIT-TO-JOIN":
                duration = data["datas"]["Duration"] 
                if duration == 0xff:
                    duration = 0xfe
                await self.app.permit(time_s=duration)
            elif data["cmd"] == "SET-TX-POWER":
                await self.app.set_tx_power (data["datas"]["Param1"])
            elif data["cmd"] == "SET-LED":
                await self.app.set_led  (data["datas"]["Param1"])
            elif data["cmd"] == "SET-CERTIFICATION":
                await self.app.set_certification  (data["datas"]["Param1"])
            elif data["cmd"] == "GET-TIME":
                await self.app.get_time_server()
            elif data["cmd"] == "SET-TIME":
                await self.app.set_time_server( data["datas"]["Param1"] )
            elif   data["cmd"] in NATIVE_COMMANDS_MAPPING:
                await native_commands(self, data["cmd"], data["datas"] )
            elif data["cmd"] == "RAW-COMMAND":
                await process_raw_command( self, data["datas"], data["ACKIsDisable"])

        except DeliveryError:
            self.log.logging("TransportWrter", "Error", "DeliveryError: Not able to execute the zigpy command: %s data: %s" %(
                data["cmd"], data["datas"]))
            
        except InvalidResponse:
            self.log.logging("TransportWrter", "Error", "InvalidResponse: Not able to execute the zigpy command: %s data: %s" %(
                data["cmd"], data["datas"]))

        except Exception as e:
            self.log.logging("TransportWrter", "Error", "Error while receiving a Plugin command: %s" % e)
            handle_thread_error(self, e, data)
        
        # Wait .5s to reduce load on Zigate
        #await asyncio.sleep(0.10)

    self.log.logging("TransportWrter", "Debug", "ZigyTransport: writer_thread Thread stop.")

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
    
    self.statistics._sent += 1
    self.log.logging("TransportWrter", "Debug", "ZigyTransport: process_raw_command ready to request NwkId: %04x Cluster: %04x Seq: %02x Payload: %s AddrMode: %02x EnableAck: %s" %(
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

