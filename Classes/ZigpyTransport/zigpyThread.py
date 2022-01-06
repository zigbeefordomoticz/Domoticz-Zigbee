import asyncio
import binascii
import json
import logging
import queue
import time
import traceback
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
from Classes.ZigpyTransport.AppZigate import App_zigate
from Classes.ZigpyTransport.AppZnp import App_znp
from Classes.ZigpyTransport.nativeCommands import (NATIVE_COMMANDS_MAPPING,
                                                   native_commands)
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_0302_frame_content, build_plugin_8009_frame_content,
    build_plugin_8011_frame_content,
    build_plugin_8043_frame_list_node_descriptor,
    build_plugin_8045_frame_list_controller_ep)
from Classes.ZigpyTransport.tools import handle_thread_error
from zigpy.exceptions import DeliveryError, InvalidResponse
from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)
from zigpy_znp.exceptions import (CommandNotRecognized, InvalidCommandResponse,
                                  InvalidFrame)


def start_zigpy_thread(self):
    self.log.logging("TransportZigpy", "Debug", "start_zigpy_thread - Starting zigpy thread")
    self.zigpy_thread.start()


def stop_zigpy_thread(self):
    self.log.logging("TransportZigpy", "Debug", "stop_zigpy_thread - Stopping zigpy thread")
    self.writer_queue.put((0, "STOP"))
    self.zigpy_running = False


def zigpy_thread(self):
    self.log.logging("TransportZigpy", "Debug", "zigpy_thread - Starting zigpy thread")
    self.zigpy_running = True
    extendedPANID = 0
    channel = 0
    if "channel" in self.pluginconf.pluginConf:
        channel = int(self.pluginconf.pluginConf["channel"])
    if "extendedPANID" in self.pluginconf.pluginConf:
        extendedPANID = int(self.pluginconf.pluginConf["extendedPANID"])
    asyncio.run(radio_start(self, self._radiomodule, self._serialPort, set_channel=channel, set_extendedPanId=extendedPANID ))


def callBackGetDevice(nwk, ieee):
    return None


async def radio_start(self, radiomodule, serialPort, auto_form=False, set_channel=0, set_extendedPanId=0):

    self.log.logging("TransportZigpy", "Debug", "In radio_start")

    conf = {CONF_DEVICE: {"path": serialPort}}
    if radiomodule == "zigate":
        self.app = App_zigate(conf)

    elif radiomodule == "znp":
        self.app = App_znp(conf)

    await self.app.startup(self.receiveData, callBackGetDevice=self.ZigpyGetDevice, auto_form=True, log=self.log, set_channel=set_channel, set_extendedPanId=set_extendedPanId)

    # Send Network information to plugin, in order to poplulate various objetcs
    self.forwarder_queue.put(build_plugin_8009_frame_content(self, radiomodule))

    # Send Controller Active Node and Node Descriptor
    self.forwarder_queue.put(build_plugin_8045_frame_list_controller_ep(self,))

    self.log.logging("TransportZigpy", "Debug", "Active Endpoint List:  %s" % str(self.app.get_device(nwk = t.NWK(0x0000)).endpoints.keys()))
    for epid, ep in self.app.get_device(nwk = t.NWK(0x0000)).endpoints.items():
        if epid == 0:
            continue
        self.log.logging("TransportZigpy", "Debug", "Simple Descriptor:  %s" % ep )
        self.forwarder_queue.put(build_plugin_8043_frame_list_node_descriptor(self, epid, ep))
        
    self.log.logging ("TransportZigpy", "Debug", "Controller Model %s" % self.app.get_device(nwk = t.NWK(0x0000)).model)
    self.log.logging ("TransportZigpy", "Debug", "Controller Manufacturer %s" % self.app.get_device(nwk = t.NWK(0x0000)).manufacturer)
    # Let send a 0302 to simulate an Off/on
    self.forwarder_queue.put(build_plugin_0302_frame_content(self,))
    
    # Run forever
    await worker_loop(self)

    await self.app.shutdown()
    self.log.logging("TransportZigpy", "Debug", "Exiting co-rounting radio_start")


    
async def worker_loop(self):
    self.log.logging("TransportZigpy", "Debug", "worker_loop - ZigyTransport: worker_loop start.")

    while self.zigpy_running:
        # self.log.logging("TransportZigpy",  'Debug', "Waiting for next command Qsize: %s" %self.writer_queue.qsize())
        if self.writer_queue is None:
            break
        
        prio, entry = await get_next_command( self ) 
        if entry is None:
            continue
        elif entry == "STOP":
            # Shutding down
            break

        data = json.loads(entry)
        self.log.logging("TransportZigpy", "Debug", "got a command %s" % data["cmd"], )

        if self.pluginconf.pluginConf["ZiGateReactTime"]:
            t_start = 1000 * time.time()
            
        try:
            await dispatch_command( self, data)

        except DeliveryError as e:
            log_exception(self, DeliveryError, e, data["cmd"], data["datas"])

        except InvalidFrame as e:
            log_exception(self, InvalidFrame, e, data["cmd"], data["datas"])

        except CommandNotRecognized as e:
            log_exception(self, CommandNotRecognized, e, data["cmd"], data["datas"])

        except InvalidResponse as e:
            log_exception(self, InvalidResponse, e, data["cmd"], data["datas"])
            
        except InvalidCommandResponse as e:
            log_exception(self, InvalidCommandResponse, e, data["cmd"], data["datas"])


        except asyncio.TimeoutError as e:
            log_exception(self, asyncio.TimeoutError, e, data["cmd"], data["datas"])
            
        except RuntimeError as e:
            log_exception(self, RuntimeError, e, data["cmd"], data["datas"])

        except Exception as e:
            self.log.logging("TransportZigpy", "Error", "Error while receiving a Plugin command: >%s<" % e)
            handle_thread_error(self, e, data)

        if self.pluginconf.pluginConf["ZiGateReactTime"]:
            t_end = 1000 * time.time()
            t_elapse = int(t_end - t_start)
            self.statistics.add_timing_zigpy(t_elapse)
            if t_elapse > 1000:
                self.log.logging(
                    "TransportZigpy",
                    "Log",
                    "process_raw_command (zigpyThread) spend more than 1s (%s ms) frame: %s" % (t_elapse, data),
                )


    self.log.logging("TransportZigpy", "Debug", "ZigyTransport: writer_thread Thread stop.")

async def get_next_command( self ):
    try:
        prio, entry = self.writer_queue.get(False)
    except queue.Empty:
        await asyncio.sleep(0.100)
        return None, None
    return prio, entry

async def dispatch_command(self, data):

    if data["cmd"] == "PERMIT-TO-JOIN":
        duration = data["datas"]["Duration"]
        if duration == 0xFF:
            duration = 0xFE
        await self.app.permit(time_s=duration)
    elif data["cmd"] == "SET-TX-POWER":
        await self.app.set_tx_power(data["datas"]["Param1"])
    elif data["cmd"] == "SET-LED":
        await self.app.set_led(data["datas"]["Param1"])
    elif data["cmd"] == "SET-CERTIFICATION":
        await self.app.set_certification(data["datas"]["Param1"])
    elif data["cmd"] == "GET-TIME":
        await self.app.get_time_server()
    elif data["cmd"] == "SET-TIME":
        await self.app.set_time_server( data["datas"]["Param1"] )
    elif data["cmd"] == "SET-EXTPANID":
        self.app.set_extended_pan_id(data["datas"]["Param1"])
    elif data["cmd"] == "SET-CHANNEL":
        self.app.set_channel(data["datas"]["Param1"])
    elif   data["cmd"] in NATIVE_COMMANDS_MAPPING:
        await native_commands(self, data["cmd"], data["datas"] )
    elif data["cmd"] == "RAW-COMMAND":
        self.log.logging( "TransportZigpy", "Debug", "RAW-COMMAND: %s" %properyly_display_data( data["datas"]) )
        await process_raw_command(self, data["datas"], AckIsDisable=data["ACKIsDisable"], Sqn=data["Sqn"])

async def process_raw_command(self, data, AckIsDisable=False, Sqn=None):
    # data = {
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
    NwkId = "%04x" %data["TargetNwk"]
    dEp = data["TargetEp"]
    sEp = data["SrcEp"]
    payload = bytes.fromhex(data["payload"])
    sequence = Sqn or self.app.get_sequence()
    addressmode = data["AddressMode"]

    self.statistics._sent += 1
    self.log.logging(
        "TransportZigpy",
        "Debug",
        "ZigyTransport: process_raw_command ready to request NwkId: %04x Cluster: %04x Seq: %02x Payload: %s AddrMode: %02x EnableAck: %s, Sqn: %s" % (
            int(NwkId,16), Cluster, sequence, binascii.hexlify(payload).decode("utf-8"), addressmode, not AckIsDisable, Sqn),
    )

    if int(NwkId,16) >= 0xfffb: # Broadcast
        destination = int(NwkId,16)
        self.log.logging( "TransportZigpy", "Debug", "process_raw_command  call broadcast destination: %s" %NwkId)
        result, msg = await self.app.broadcast( Profile, Cluster, sEp, dEp, 0x0, 0x30, sequence, payload, )

    elif addressmode == 0x01:
        # Group Mode
        destination = int(NwkId,16)
        self.log.logging( "TransportZigpy", "Debug", "process_raw_command  call mrequest destination: %s" %destination)
        result, msg = await self.app.mrequest(destination, Profile, Cluster, sEp, sequence, payload)
        
    elif addressmode in (0x02, 0x07):
        # Short is a str
        destination = self.app.get_device (nwk = t.NWK(int(NwkId,16)))
        self.log.logging( "TransportZigpy", "Debug", "process_raw_command  call request destination: %s Profile: %s Cluster: %s sEp: %s dEp: %s Seq: %s Payload: %s" %(
            destination, Profile, Cluster, sEp, dEp, sequence, payload))
        result, msg = await self.app.request(destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=not AckIsDisable, use_ieee=False)
        if not AckIsDisable:
            push_APS_ACK_NACKto_plugin(self, NwkId, result, destination.lqi)

    elif addressmode in (0x03, 0x08):
        # Nwkid is in fact an IEEE
        destination = self.app.get_device (nwk = t.NWK(int(NwkId,16)))
        self.log.logging( "TransportZigpy", "Debug", "process_raw_command  call request destination: %s" %destination)
        result, msg = await self.app.request(destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=not AckIsDisable, use_ieee=False)

    self.log.logging(
        "TransportZigpy",
        "Debug",
        "ZigyTransport: process_raw_command completed NwkId: %s result: %s msg: %s" % (destination, result, msg),
    )
   
    # Slow down for now
    await asyncio.sleep(0.500)

def push_APS_ACK_NACKto_plugin(self, nwkid, result, lqi):
    # Looks like Zigate return an int, while ZNP returns a status.type
    if nwkid == "0000":
        # No Ack/Nack for Controller
        return
    if not isinstance(result, int):
        result = int(result.serialize().hex(), 16)

    # Update statistics
    if result != 0x00:
        self.statistics._APSNck += 1
    else:
        self.statistics._APSAck += 1

    # Send Ack/Nack to Plugin
    self.forwarder_queue.put(build_plugin_8011_frame_content(self, nwkid, result, lqi))
    
def properyly_display_data( Datas):
    
    log = "{"
    for x in Datas:
        value = Datas[x]
        if x in ( 'Profile', 'Cluster', 'TargetNwk', ):
            if isinstance(value, int):
                value = "%04x" %value
        elif x in ( 'TargetEp', 'SrcEp', 'Sqn', 'AddressMode'):
            if isinstance(value, int):
                value = "%02x" %value
        log += "'%s' : %s," %(x,value)
    log += "}"
    return log

def log_exception(self, exception, error, cmd, data):
    
    context = {
        "Exception": str(exception),
        "Message code:": str(error),
        "Stack Trace": str(traceback.format_exc()),
        "Command": str(cmd),
        "Data": properyly_display_data( data),
    }
    
    self.log.logging(
        "TransportZigpy",
        "Error",
        "%s: request() Not able to execute the zigpy command: %s data: %s" % (error, cmd, properyly_display_data( data)), context=context)
