# coding: utf-8 -*-
#
# Author: pipiche38
#

import asyncio
import asyncio.events
import binascii
import contextlib
import json
import queue
import sys
import time
import traceback
from threading import Thread
from typing import Any, Optional

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
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_0302_frame_content, build_plugin_8009_frame_content,
    build_plugin_8011_frame_content,
    build_plugin_8043_frame_list_node_descriptor,
    build_plugin_8045_frame_list_controller_ep)
from Classes.ZigpyTransport.tools import handle_thread_error
from Modules.macPrefix import DELAY_FOR_VERY_KEY, casaiaPrefix_zigpy
from Modules.tools import print_stack
from zigpy.exceptions import (APIException, ControllerException, DeliveryError,
                              InvalidResponse)
from zigpy_znp.exceptions import (CommandNotRecognized, InvalidCommandResponse,
                                  InvalidFrame)

MAX_CONCURRENT_REQUESTS_PER_DEVICE = 1
CREATE_TASK = True
WAITING_TIME_BETWEEN_COMMANDS = 0.250

def start_zigpy_thread(self):

    if sys.platform == "win32" and (3, 8, 0) <= sys.version_info < (3, 9, 0):
        asyncio.set_event_loop_policy( asyncio.WindowsSelectorEventLoopPolicy() )
            
    self.zigpy_loop = get_or_create_eventloop()
    if self.zigpy_loop:
        self.log.logging("TransportZigpy", "Debug", "start_zigpy_thread - Starting zigpy thread")
        self.zigpy_thread = Thread(name="ZigpyCom_%s" % self.hardwareid, target=zigpy_thread, args=(self,))
        self.log.logging("TransportZigpy", "Debug", "start_zigpy_thread - zigpy thread setup done")
        self.zigpy_thread.start()
        self.log.logging("TransportZigpy", "Debug", "start_zigpy_thread - zigpy thread started")

def stop_zigpy_thread(self):
    self.log.logging("TransportZigpy", "Debug", "stop_zigpy_thread - Stopping zigpy thread")
    self.writer_queue.put("STOP")
    self.zigpy_running = False

def zigpy_thread(self):
    self.log.logging("TransportZigpy", "Debug", "zigpy_thread - Starting zigpy thread")
    self.zigpy_running = True
    extendedPANID = 0
    channel = 0
    if "channel" in self.pluginconf.pluginConf:
        channel = int(self.pluginconf.pluginConf["channel"])
        self.log.logging("TransportZigpy", "Debug", "===> channel: %s" % channel)
    if "extendedPANID" in self.pluginconf.pluginConf:
        extendedPANID = self.pluginconf.pluginConf["extendedPANID"]
        self.log.logging("TransportZigpy", "Debug", "===> extendedPanId: 0x%X" % extendedPANID)

    self.log.logging(
        "TransportZigpy",
        "Debug",
        "zigpy_thread -extendedPANID %s %d" % (self.pluginconf.pluginConf["extendedPANID"], extendedPANID),
    )
    
    task = radio_start(self, self.pluginconf, self._radiomodule, self._serialPort, set_channel=channel, set_extendedPanId=extendedPANID)

    self.zigpy_loop.run_until_complete(task)
    self.zigpy_loop.run_until_complete(asyncio.sleep(1))

    self.log.logging("TransportZigpy", "Debug", "Check and cancelled any left task (if any)")
    for not_yet_finished_task in list(asyncio.all_tasks(self.zigpy_loop)):
        try:
            self.log.logging("TransportZigpy", "Debug", "         - not yet finished %s" %not_yet_finished_task.get_name())
            not_yet_finished_task.cancel()
        except AttributeError:
            continue
        
    self.zigpy_loop.run_until_complete(asyncio.sleep(1))

    self.zigpy_loop.close()

    self.log.logging("TransportZigpy", "Debug", "zigpy_thread - exiting zigpy thread")

def get_or_create_eventloop():
    loop = None
    try:
        loop = asyncio.get_event_loop()

    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            asyncio.new_event_loop()
     
    asyncio.set_event_loop( loop )
    return loop   
    
async def radio_start(self, pluginconf, radiomodule, serialPort, auto_form=False, set_channel=0, set_extendedPanId=0):

    self.log.logging("TransportZigpy", "Debug", "In radio_start %s" %radiomodule)

    if radiomodule == "ezsp":
        self.log.logging("TransportZigpy", "Debug", "Starting radio %s port: %s" %( radiomodule, serialPort))
        import bellows.config as conf
        from Classes.ZigpyTransport.AppBellows import App_bellows
        config = {
            conf.CONF_DEVICE: { "path": serialPort, "baudrate": 115200}, 
            conf.CONF_NWK: {},
            conf.CONF_EZSP_CONFIG: {
            },
            "topology_scan_enabled": False,
            "handle_unknown_devices": True,
            "source_routing": True         # If enable bellows is doing source routing, if not then it is ezsp taking care 
                                            # https://github.com/zigpy/bellows/issues/493#issuecomment-1239892344
            }
        
        if "BellowsNoMoreEndDeviceChildren" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["BellowsNoMoreEndDeviceChildren"]:
            config[conf.CONF_EZSP_CONFIG]["CONFIG_MAX_END_DEVICE_CHILDREN"] = 0
            
        if "BellowsSourceRouting" in self.pluginconf.pluginConf:
            config["source_routing"] = bool( self.pluginconf.pluginConf["BellowsSourceRouting"] )
            
        self.log.logging("TransportZigpy", "Status", "Started radio %s port: %s" %( radiomodule, serialPort))

    elif radiomodule =="zigate":
        self.log.logging("TransportZigpy", "Status", "Starting radio %s port: %s" %( radiomodule, serialPort))
        try:
            import zigpy_zigate.config as conf
            from Classes.ZigpyTransport.AppZigate import App_zigate
            config = {
                conf.CONF_DEVICE: {"path": serialPort,}, 
                conf.CONF_NWK: {},
                "topology_scan_enabled": False,
                }
            self.log.logging("TransportZigpy", "Status", "Started radio %s port: %s" %( radiomodule, serialPort))
        except Exception as e:
            self.log.logging("TransportZigpy", "Error", "Error while starting Radio: %s on port %s with %s" %( radiomodule, serialPort, e))
            self.log.logging("%s" %traceback.format_exc())

    elif radiomodule =="znp":
        self.log.logging("TransportZigpy", "Status", "Starting radio %s port: %s" %( radiomodule, serialPort))
        try:
            import zigpy_znp.config as conf
            from Classes.ZigpyTransport.AppZnp import App_znp
            config = {
                conf.CONF_DEVICE: {"path": serialPort,}, 
                conf.CONF_NWK: {},
                conf.CONF_ZNP_CONFIG: {},
                "topology_scan_enabled": False,
                }
            self.log.logging("TransportZigpy", "Status", "Started radio %s port: %s" %( radiomodule, serialPort))
        except Exception as e:
            self.log.logging("TransportZigpy", "Error", "Error while starting Radio: %s on port %s with %s" %( radiomodule, serialPort, e))
            self.log.logging("%s" %traceback.format_exc())

    elif radiomodule =="deCONZ":
        self.log.logging("TransportZigpy", "Status", "Starting radio %s port: %s" %( radiomodule, serialPort))
        try:
            import zigpy_deconz.config as conf
            from Classes.ZigpyTransport.AppDeconz import App_deconz
            config = {
                conf.CONF_DEVICE: {"path": serialPort}, 
                conf.CONF_NWK: {},
                "topology_scan_enabled": False,
                }
            self.log.logging("TransportZigpy", "Status", "Started radio %s port: %s" %( radiomodule, serialPort))
        except Exception as e:
            self.log.logging("TransportZigpy", "Error", "Error while starting Radio: %s on port %s with %s" %( radiomodule, serialPort, e))
            self.log.logging("%s" %traceback.format_exc())

    if "autoBackup" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["autoBackup"]:
        config[zigpy.config.CONF_NWK_BACKUP_ENABLED] = True
        config[zigpy.config.CONF_NWK_BACKUP_PERIOD] = self.pluginconf.pluginConf["autoBackup"]
    else:
        config[zigpy.config.CONF_NWK_BACKUP_ENABLED] = False
   
    if "TXpower_set" in self.pluginconf.pluginConf:
        if radiomodule == "znp":
            config[conf.CONF_ZNP_CONFIG]["tx_power"] = int(self.pluginconf.pluginConf["TXpower_set"])
        else:
            config["tx_power"] = int(self.pluginconf.pluginConf["TXpower_set"])

    if set_extendedPanId != 0:
        config[conf.CONF_NWK][conf.CONF_NWK_EXTENDED_PAN_ID] = "%s" % (
            t.EUI64(t.uint64_t(set_extendedPanId).serialize())
        )
    if set_channel != 0:
        config[conf.CONF_NWK][conf.CONF_NWK_CHANNEL] = set_channel

    # Ready for starting the Radio module
    try:
        if radiomodule == "zigate":
            self.app = App_zigate(config)
        elif radiomodule == "znp":
                self.app = App_znp(config)
        elif radiomodule == "deCONZ":
                self.app = App_deconz(config)
        elif radiomodule == "ezsp":
                self.app = App_bellows(conf.CONFIG_SCHEMA(config))  
        else:
            self.log.logging( "TransportZigpy", "Error", "Wrong radiomode: %s" % (radiomodule), )
            return
    except Exception as e:
            self.log.logging( "TransportZigpy", "Error", "Error while starting radio %s on port: %s - Error: %s" %( radiomodule, serialPort, e) )

    self.log.logging("TransportZigpy", "Debug", "4- %s" %radiomodule) 
    if self.pluginParameters["Mode3"] == "True":
        self.log.logging( "TransportZigpy", "Status", "Coordinator initialisation requested  Channel %s(0x%02x) ExtendedPanId: 0x%016x" % (
            set_channel, set_channel, set_extendedPanId), )
        new_network = True
    else:
        new_network = False

    try:
        await self.app.startup(
            self.hardwareid,
            pluginconf,
            callBackHandleMessage=self.receiveData,
            callBackUpdDevice=self.ZigpyUpdDevice,
            callBackGetDevice=self.ZigpyGetDevice,
            callBackBackup=self.ZigpyBackupAvailable,
            auto_form=True,
            force_form=new_network,
            log=self.log,
            permit_to_join_timer=self.permit_to_join_timer,
        )
    except Exception as e:
        self.log.logging( "TransportZigpy", "Error", "Error at startup %s" %e)
        #print_stack( self )
        
    if new_network:
        # Assume that the new network has been created
        self.log.logging( "TransportZigpy", "Status", "Assuming new network formed")
        self.ErasePDMDone = True  

    display_network_infos(self)
    self.ControllerData["Network key"] = ":".join( f"{c:02x}" for c in self.app.state.network_information.network_key.key )
    
    post_coordinator_startup(self, radiomodule)
    
    # Run forever
    await worker_loop(self)

    await self.app.shutdown()
    self.log.logging( "TransportZigpy", "Debug", "Exiting co-rounting radio_start")


def post_coordinator_startup(self, radiomodule):
    # Send Network information to plugin, in order to poplulate various objetcs
    self.forwarder_queue.put(build_plugin_8009_frame_content(self, radiomodule))

    # Send Controller Active Node and Node Descriptor
    self.forwarder_queue.put( build_plugin_8045_frame_list_controller_ep( self, ) )

    self.log.logging( "TransportZigpy", "Debug", "Active Endpoint List:  %s" % str(self.app.get_device(nwk=t.NWK(0x0000)).endpoints.keys()), )
    for epid, ep in self.app.get_device(nwk=t.NWK(0x0000)).endpoints.items():
        if epid == 0:
            continue
        self.log.logging( "TransportZigpy", "Debug", "Simple Descriptor:  %s" % ep)
        self.forwarder_queue.put(build_plugin_8043_frame_list_node_descriptor(self, epid, ep))

    self.log.logging( "TransportZigpy", "Debug", "Controller Model %s" % self.app.get_device(nwk=t.NWK(0x0000)).model )
    self.log.logging( "TransportZigpy", "Debug", "Controller Manufacturer %s" % self.app.get_device(nwk=t.NWK(0x0000)).manufacturer )
    # Let send a 0302 to simulate an Off/on
    self.forwarder_queue.put( build_plugin_0302_frame_content( self, ) )
   
    
def display_network_infos(self):
    self.log.logging( "TransportZigpy", "Status", "Network settings")
    self.log.logging( "TransportZigpy", "Status", "  Channel: %s" %self.app.channel)
    self.log.logging( "TransportZigpy", "Status", "  PAN ID: 0x%04X" %self.app.pan_id)
    self.log.logging( "TransportZigpy", "Status", "  Extended PAN ID: %s" %self.app.extended_pan_id)
    self.log.logging( "TransportZigpy", "Status", "  Device IEEE: %s" %self.app.ieee)
    self.log.logging( "TransportZigpy", "Status", "  Device NWK: 0x%04X" %self.app.nwk)
    self.log.logging( "TransportZigpy", "Debug", "  Network key: " + ":".join( f"{c:02x}" for c in self.app.state.network_information.network_key.key ))
 

async def worker_loop(self):
    self.log.logging("TransportZigpy", "Debug", "worker_loop - ZigyTransport: worker_loop start.")

    while self.zigpy_running and self.writer_queue is not None:
        entry = await get_next_command(self)
        if entry is None:
            continue
        elif entry == "STOP":
            # Shutding down
            self.log.logging("TransportZigpy", "Log", "worker_loop - Shutting down ... exit.")
            self.zigpy_running = False
            break

        data = json.loads(entry)
        self.log.logging( "TransportZigpy", "Debug", "got a command %s" % data["cmd"], )

        if self.pluginconf.pluginConf["ZiGateReactTime"]:
            t_start = 1000 * time.time()

        try:
            await dispatch_command(self, data)

        except DeliveryError as e:
            # This could be relevant to APS NACK after retry
            # Request failed after 5 attempts: <Status.MAC_NO_ACK: 233>
            # status_code = int(e[34+len("Status."):].split(':')[1][:-1])
            log_exception(self, "DeliveryError", e, data["cmd"], data["datas"])

        except APIException as e:
            log_exception(self, "APIException", e, data["cmd"], data["datas"])
            await asyncio.sleep( 1.0)

        except ControllerException as e:
            log_exception(self, "ControllerException", e, data["cmd"], data["datas"])
            await asyncio.sleep( 1.0)

        except InvalidFrame as e:
            log_exception(self, "InvalidFrame", e, data["cmd"], data["datas"])

        except CommandNotRecognized as e:
            log_exception(self, "CommandNotRecognized", e, data["cmd"], data["datas"])

        except InvalidResponse as e:
            log_exception(self, "InvalidResponse", e, data["cmd"], data["datas"])

        except InvalidCommandResponse as e:
            log_exception(self, "InvalidCommandResponse", e, data["cmd"], data["datas"])

        except asyncio.TimeoutError as e:
            log_exception(self, "asyncio.TimeoutError", e, data["cmd"], data["datas"])

        except RuntimeError as e:
            log_exception(self, "RuntimeError", e, data["cmd"], data["datas"])

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

    self.log.logging("TransportZigpy", "Log", "worker_loop: Exiting Worker loop. Semaphore : %s" %len(self._concurrent_requests_semaphores_list))

    if self._concurrent_requests_semaphores_list:
        for x in self._concurrent_requests_semaphores_list:
            self.log.logging("TransportZigpy", "Log", "worker_loop:      Semaphore[%s] " %x)

async def get_next_command(self):
    try:
        entry = self.writer_queue.get(False)
    except queue.Empty:
        await asyncio.sleep(0.100)
        return None
    return entry

async def dispatch_command(self, data):

    if data["cmd"] == "PERMIT-TO-JOIN":
        await _permit_to_joint(self, data)
    elif data["cmd"] == "SET-TX-POWER":
        await self.app.set_zigpy_tx_power(data["datas"]["Param1"])
    elif data["cmd"] == "SET-LED":
        await self.app.set_led(data["datas"]["Param1"])
    elif data["cmd"] == "SET-CERTIFICATION":
        await self.app.set_certification(data["datas"]["Param1"])
    elif data["cmd"] == "GET-TIME":
        await self.app.get_time_server()
    elif data["cmd"] == "SET-TIME":
        await self.app.set_time_server(data["datas"]["Param1"])
    elif data["cmd"] == "SET-EXTPANID":
        self.app.set_extended_pan_id(data["datas"]["Param1"])
    elif data["cmd"] == "SET-CHANNEL":
        self.app.set_channel(data["datas"]["Param1"])
    elif data["cmd"] == "REMOVE-DEVICE":
        ieee = data["datas"]["Param1"]
        await self.app.remove_ieee(t.EUI64(t.uint64_t(ieee).serialize()))
    elif data["cmd"] == "COORDINATOR-BACKUP":
        await self.app.coordinator_backup()

    elif data["cmd"] == "REQ-NWK-STATUS":
        await asyncio.sleep(10)
        #await self.app.load_network_info()
        self.forwarder_queue.put(build_plugin_8009_frame_content(self, self._radiomodule))

    elif data["cmd"] == "RAW-COMMAND":
        self.log.logging("TransportZigpy", "Debug", "RAW-COMMAND: %s" % properyly_display_data(data["datas"]))
        await process_raw_command(self, data["datas"], AckIsDisable=data["ACKIsDisable"], Sqn=data["Sqn"])

async def _permit_to_joint(self, data):

    self.log.logging( "TransportZigpy", "Log", "PERMIT-TO-JOIN: %s" % (data), )
    duration = data["datas"]["Duration"]
    target_router = data["datas"]["targetRouter"]
    target_router = None if target_router == "FFFC" else t.EUI64(t.uint64_t(target_router).serialize())
    duration == 0xFE if duration == 0xFF else duration
    self.permit_to_join_timer["Timer"] = time.time()
    self.permit_to_join_timer["Duration"] = duration

    self.log.logging("TransportZigpy", "Log", "PERMIT-TO-JOIN: duration: %s for Radio: %s for node: %s" % (duration, self._radiomodule, target_router))

    if self._radiomodule == "deCONZ":
        return await self.app.permit_ncp( time_s=duration)
    
    self.log.logging("TransportZigpy", "Log", "Calling self.app.permit(time_s=%s, node=%s )" % (duration, target_router))
    await self.app.permit(time_s=duration, node=target_router )
    self.log.logging("TransportZigpy", "Log", "returning from the self.app.permit(time_s=%s, node=%s )" % (duration, target_router))

async def process_raw_command(self, data, AckIsDisable=False, Sqn=None):
    # sourcery skip: replace-interpolation-with-fstring
    # data = {
    #    'Profile': int(profileId, 16),
    #    'Cluster': int(cluster, 16),
    #    'TargetNwk': int(targetaddr, 16),
    #    'TargetEp': int(dest_ep, 16),
    #    'SrcEp': int(zigate_ep, 16),
    #    'Sqn': None,
    #    'payload': payload,
    #    }
    Function = data["Function"]
    TimeStamp = data["timestamp"]
    Profile = data["Profile"]
    Cluster = data["Cluster"]
    NwkId = "%04x" % data["TargetNwk"]
    dEp = data["TargetEp"]
    sEp = data["SrcEp"]
    payload = bytes.fromhex(data["payload"])
    sequence = Sqn or self.app.get_sequence()
    addressmode = data["AddressMode"]
    result = None
    
    if "Delay" in data:
        delay = data["Delay"]
    else:
        delay = None

    self.log.logging(
        "TransportZigpy",
        "Debug",
        "ZigyTransport: process_raw_command ready to request Function: %s NwkId: %04x/%s Cluster: %04x Seq: %02x Payload: %s AddrMode: %02x EnableAck: %s, Sqn: %s, Delay: %s"
        % (
            Function,
            int(NwkId, 16),
            dEp,
            Cluster,
            sequence,
            binascii.hexlify(payload).decode("utf-8"),
            addressmode,
            not AckIsDisable,
            Sqn,
            delay,
        ),
    )

    if int(NwkId, 16) >= 0xFFFB:  # Broadcast
        destination = int(NwkId, 16)
        self.log.logging("TransportZigpy", "Debug", "process_raw_command  call broadcast destination: %s" % NwkId)
        result, msg = await self.app.broadcast( Profile, Cluster, sEp, dEp, 0x0, 0x0, sequence, payload, )
        await asyncio.sleep( WAITING_TIME_BETWEEN_COMMANDS)

    elif addressmode == 0x01:
        # Group Mode
        destination = int(NwkId, 16)
        self.log.logging("TransportZigpy", "Debug", "process_raw_command  call mrequest destination: %s" % destination)
        result, msg = await self.app.mrequest(destination, Profile, Cluster, sEp, sequence, payload)
        await asyncio.sleep( WAITING_TIME_BETWEEN_COMMANDS)

    elif addressmode in (0x02, 0x07):
        # Short is a str
        try:
            destination = self.app.get_device(nwk=t.NWK(int(NwkId, 16)))
        except KeyError:
            self.log.logging(
                "TransportZigpy",
                "Error",
                "process_raw_command device not found destination: %s Profile: %s Cluster: %s sEp: %s dEp: %s Seq: %s Payload: %s"
                % (NwkId, Profile, Cluster, sEp, dEp, sequence, payload),
            )
            return

        self.log.logging(
            "TransportZigpy",
            "Debug",
            "process_raw_command  call request destination: %s Profile: %s Cluster: %s sEp: %s dEp: %s Seq: %s Payload: %s"
            % (destination, Profile, Cluster, sEp, dEp, sequence, payload),
        )
        try:
            if CREATE_TASK:
                task = asyncio.create_task(
                    transport_request( self, destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=not AckIsDisable, use_ieee=False, delay=delay) )
            else:
                await transport_request( self, destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=not AckIsDisable, use_ieee=False, delay=delay)
                await asyncio.sleep( WAITING_TIME_BETWEEN_COMMANDS)
                
        except DeliveryError as e:
            # This could be relevant to APS NACK after retry
            # Request failed after 5 attempts: <Status.MAC_NO_ACK: 233>
            self.log.logging("TransportZigpy", "Debug", "process_raw_command - DeliveryError : %s" % e)
            msg = "%s" % e
            result = 0xB6

    elif addressmode in (0x03, 0x08):
        # Nwkid is in fact an IEEE
        destination = self.app.get_device(nwk=t.NWK(int(NwkId, 16)))
        self.log.logging("TransportZigpy", "Debug", "process_raw_command  call request destination: %s" % destination)
        if CREATE_TASK:
            task = asyncio.create_task(
                transport_request( self, destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=not AckIsDisable, use_ieee=False, delay=delay) )
        else:
            await transport_request( self, destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=not AckIsDisable, use_ieee=False, delay=delay )
            await asyncio.sleep( WAITING_TIME_BETWEEN_COMMANDS)
            
    if result:
        self.log.logging(
            "TransportZigpy",
            "Debug",
            "ZigyTransport: process_raw_command completed NwkId: %s result: %s msg: %s" % (destination, result, msg),
        )

    self.statistics._sent += 1

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

def properyly_display_data(Datas):

    log = "{"
    for x in Datas:
        value = Datas[x]
        if x in (
            "Profile",
            "Cluster",
            "TargetNwk",
        ):
            if isinstance(value, int):
                value = "%04x" % value
        elif x in ("TargetEp", "SrcEp", "Sqn", "AddressMode"):
            if isinstance(value, int):
                value = "%02x" % value
        log += "'%s' : %s," % (x, value)
    log += "}"
    return log

def log_exception(self, exception, error, cmd, data):

    context = {
        "Exception": str(exception),
        "Message code:": str(error),
        "Stack Trace": str(traceback.format_exc()),
        "Command": str(cmd),
        "Data": properyly_display_data(data),
    }

    self.log.logging(
        "TransportZigpy",
        "Error",
        "%s / %s: request() Not able to execute the zigpy command: %s data: %s"
        % (exception, error, cmd, properyly_display_data(data)),
        context=context,
    )

def check_transport_readiness(self):
    
    if self._radiomodule == "zigate":
        return True

    if self._radiomodule == "znp":
        return self.app._znp is not None
    
    if self._radiomodule == "deCONZ":
        return True

    if self._radiomodule == "ezsp":
        return True
        
async def transport_request( self, destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=True, use_ieee=False, delay=None ):
    # sourcery skip: replace-interpolation-with-fstring    
    _nwkid = destination.nwk.serialize()[::-1].hex()
    _ieee = str(destination.ieee)
    if not check_transport_readiness:
        return

    try:
        if delay:
            await asyncio.sleep(delay)
        async with _limit_concurrency(self, destination, sequence):
            self.log.logging( "TransportZigpy", "Debug", "transport_request: _limit_concurrency %s %s" %(destination, sequence))
            if _ieee in self._currently_not_reachable and self._currently_waiting_requests_list[_ieee]:
                self.log.logging(
                    "TransportZigpy",
                    "Debug",
                    "ZigyTransport: process_raw_command Request %s skipped NwkId: %s not reachable - %s %s %s" % (
                        sequence, _nwkid, _ieee, str(self._currently_not_reachable),self._currently_waiting_requests_list[_ieee] ),
                    _nwkid,
                )
                return

            result, msg = await self.app.request( destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply, use_ieee )
            self.log.logging( "TransportZigpy", "Debug", "ZigyTransport: process_raw_command  %s %s (%s) %s (%s)" %( _ieee, Profile, type(Profile), Cluster, type(Cluster)))
            if Profile == 0x0000 and Cluster == 0x0005 and _ieee and _ieee[:8] in DELAY_FOR_VERY_KEY:
                # Most likely for the CasaIA devices which seems to have issue
                self.log.logging( "TransportZigpy", "Log", "ZigyTransport: process_raw_command waiting 6 secondes for CASA.IA Confirm Key")
                await asyncio.sleep( 6 )

            # Slow down the through put when too many commands. Try to not overload the coordinators
            multi = 1.5 if self._currently_waiting_requests_list[_ieee] else 1
            await asyncio.sleep( multi * WAITING_TIME_BETWEEN_COMMANDS)

    except DeliveryError as e:
        # This could be relevant to APS NACK after retry
        # Request failed after 5 attempts: <Status.MAC_NO_ACK: 233>
        self.log.logging("TransportZigpy", "Debug", "process_raw_command - DeliveryError : %s" % e, _nwkid)
        msg = "%s" % e
        result = 0xB6
        self._currently_not_reachable.append( _ieee )

    if expect_reply:
        push_APS_ACK_NACKto_plugin(self, _nwkid, result, destination.lqi)

    if result == 0x00 and _ieee in self._currently_not_reachable:
        self._currently_not_reachable.remove( _ieee )

    self.log.logging(
        "TransportZigpy",
        "Debug",
        "ZigyTransport: process_raw_command completed %s NwkId: %s result: %s msg: %s"
        % (sequence, _nwkid, result, msg),
        _nwkid,
    )

@contextlib.asynccontextmanager
async def _limit_concurrency(self, destination, sequence):
    """
    Async context manager that prevents devices from being overwhelmed by requests.
    Mainly a thin wrapper around `asyncio.Semaphore` that logs when it has to wait.
    """
    _ieee = str(destination.ieee)
    _nwkid = destination.nwk.serialize()[::-1].hex()

    if _ieee not in self._concurrent_requests_semaphores_list:
        self._concurrent_requests_semaphores_list[_ieee] = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS_PER_DEVICE)
        self._currently_waiting_requests_list[_ieee] = 0

    # self.log.logging(
    #         "TransportZigpy",
    #         "Debug",
    #         " limit_concurrency: %s" %repr(self._concurrent_requests_semaphores_list)
    #         )

    start_time = time.time()
    was_locked = self._concurrent_requests_semaphores_list[_ieee].locked()

    if was_locked:
        self._currently_waiting_requests_list[_ieee] += 1
        self.log.logging(
            "TransportZigpy",
            "Debug",
            "Max concurrency reached for %s, delaying request %s (%s enqueued)"
            % (_nwkid, sequence, self._currently_waiting_requests_list[_ieee]),
            _nwkid,
        )

    try:
        async with self._concurrent_requests_semaphores_list[_ieee]:
            if was_locked:
                self.log.logging(
                    "TransportZigpy",
                    "Debug",
                    "Previously delayed request %s is now running, "
                    "delayed by %0.2f seconds for %s" % (sequence, (time.time() - start_time), _nwkid),
                    _nwkid,
                )
            yield
    finally:
        if was_locked:
            self._currently_waiting_requests_list[_ieee] -= 1
