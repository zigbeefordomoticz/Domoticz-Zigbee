# coding: utf-8 -*-
#
# Author: pipiche38
#

import asyncio
import binascii
import json
import queue
import time
import traceback
import contextlib
from typing import Any, Optional

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
from Classes.ZigpyTransport.AppZigate import App_zigate
from Classes.ZigpyTransport.AppZnp import App_znp
from Classes.ZigpyTransport.AppDeconz import App_deconz
from Classes.ZigpyTransport.AppBellows import App_bellows
from Classes.ZigpyTransport.nativeCommands import NATIVE_COMMANDS_MAPPING, native_commands
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_0302_frame_content,
    build_plugin_8009_frame_content,
    build_plugin_8011_frame_content,
    build_plugin_8043_frame_list_node_descriptor,
    build_plugin_8045_frame_list_controller_ep,
)
from Classes.ZigpyTransport.tools import handle_thread_error
from zigpy.exceptions import DeliveryError, InvalidResponse
from zigpy_znp.exceptions import CommandNotRecognized, InvalidCommandResponse, InvalidFrame

MAX_CONCURRENT_REQUESTS_PER_DEVICE = 1
CREATE_TASK = True

def start_zigpy_thread(self):
    self.zigpy_loop = get_or_create_eventloop()
    self.log.logging("TransportZigpy", "Debug", "start_zigpy_thread - Starting zigpy thread")
    self.zigpy_thread.start()


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

    task = radio_start(self, self._radiomodule, self._serialPort, set_channel=channel, set_extendedPanId=extendedPANID)
 
    self.zigpy_loop.run_until_complete(task)
    self.zigpy_loop.run_until_complete(asyncio.sleep(1))

    self.log.logging("TransportZigpy", "Debug", "Check and cancelled any left task (if any)")
    for not_yet_finished_task  in  asyncio.all_tasks(self.zigpy_loop):
        self.log.logging("TransportZigpy", "Debug", "         - not yet finished %s" %not_yet_finished_task.get_name())
        not_yet_finished_task.cancel()
    self.zigpy_loop.run_until_complete(asyncio.sleep(1))

    self.zigpy_loop.close()

    self.log.logging("TransportZigpy", "Debug", "zigpy_thread - exiting zigpy thread")

def get_or_create_eventloop():
    try:
        loop = asyncio.get_event_loop()

    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            asyncio.new_event_loop()
     
    asyncio.set_event_loop( loop )
    return loop   
    
async def radio_start(self, radiomodule, serialPort, auto_form=False, set_channel=0, set_extendedPanId=0):

    self.log.logging("TransportZigpy", "Debug", "In radio_start %s" %radiomodule)
    
    if radiomodule == "ezsp":
        import bellows.config as conf
        config = {conf.CONF_DEVICE: {"path": serialPort, "baudrate": 115200}, conf.CONF_NWK: {}}
        
    elif radiomodule =="zigate":
        import zigpy_zigate.config as conf
        config = {conf.CONF_DEVICE: {"path": serialPort, "baudrate": 115200}, conf.CONF_NWK: {}}
        
    elif radiomodule =="znp":
        import zigpy_znp.config as conf
        config = {conf.CONF_DEVICE: {"path": serialPort, "baudrate": 115200}, conf.CONF_NWK: {}}
        
    elif radiomodule =="deCONZ":
        import zigpy_deconz.config as conf
        config = {conf.CONF_DEVICE: {"path": serialPort}, conf.CONF_NWK: {}}
        
    if set_extendedPanId != 0:
        config[conf.CONF_NWK][conf.CONF_NWK_EXTENDED_PAN_ID] = "%s" % (
            t.EUI64(t.uint64_t(set_extendedPanId).serialize())
        )
    if set_channel != 0:
        config[conf.CONF_NWK][conf.CONF_NWK_CHANNEL] = set_channel

    if radiomodule == "zigate":
        self.app = App_zigate(config)
        
    elif radiomodule == "znp":
        self.app = App_znp(config)
        
    elif radiomodule == "deCONZ":
        self.app = App_deconz(conf.CONFIG_SCHEMA(config))
        
    elif radiomodule == "ezsp":
        self.app = App_bellows(conf.CONFIG_SCHEMA(config))

    if self.pluginParameters["Mode3"] == "True":
        self.log.logging(
            "TransportZigpy",
            "Status",
            "Form a New Network with Channel: %s(0x%02x) ExtendedPanId: 0x%016x"
            % (set_channel, set_channel, set_extendedPanId),
        )
        self.ErasePDMDone = True
        new_network = True
    else:
        new_network = False

    await self.app.startup(
        self.receiveData,
        callBackGetDevice=self.ZigpyGetDevice,
        auto_form=True,
        force_form=new_network,
        log=self.log,
        permit_to_join_timer=self.permit_to_join_timer,
    )

    # Send Network information to plugin, in order to poplulate various objetcs
    self.forwarder_queue.put(build_plugin_8009_frame_content(self, radiomodule))

    # Send Controller Active Node and Node Descriptor
    self.forwarder_queue.put(
        build_plugin_8045_frame_list_controller_ep(
            self,
        )
    )

    self.log.logging(
        "TransportZigpy",
        "Debug",
        "Active Endpoint List:  %s" % str(self.app.get_device(nwk=t.NWK(0x0000)).endpoints.keys()),
    )
    for epid, ep in self.app.get_device(nwk=t.NWK(0x0000)).endpoints.items():
        if epid == 0:
            continue
        self.log.logging("TransportZigpy", "Debug", "Simple Descriptor:  %s" % ep)
        self.forwarder_queue.put(build_plugin_8043_frame_list_node_descriptor(self, epid, ep))

    self.log.logging("TransportZigpy", "Debug", "Controller Model %s" % self.app.get_device(nwk=t.NWK(0x0000)).model)
    self.log.logging(
        "TransportZigpy", "Debug", "Controller Manufacturer %s" % self.app.get_device(nwk=t.NWK(0x0000)).manufacturer
    )

    # Let send a 0302 to simulate an Off/on
    self.forwarder_queue.put(
        build_plugin_0302_frame_content(
            self,
        )
    )

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

        entry = await get_next_command(self)
        if entry is None:
            continue
        elif entry == "STOP":
            # Shutding down
            break

        data = json.loads(entry)
        self.log.logging(
            "TransportZigpy",
            "Debug",
            "got a command %s" % data["cmd"],
        )

        if self.pluginconf.pluginConf["ZiGateReactTime"]:
            t_start = 1000 * time.time()

        try:
            await dispatch_command(self, data)

        except DeliveryError as e:
            # This could be relevant to APS NACK after retry
            # Request failed after 5 attempts: <Status.MAC_NO_ACK: 233>
            # status_code = int(e[34+len("Status."):].split(':')[1][:-1])
            log_exception(self, "DeliveryError", e, data["cmd"], data["datas"])

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

    self.log.logging("TransportZigpy", "Debug", "ZigyTransport: writer_thread Thread stop.")


async def get_next_command(self):
    try:
        entry = self.writer_queue.get(False)
    except queue.Empty:
        await asyncio.sleep(0.100)
        return None
    return entry


async def dispatch_command(self, data):

    if data["cmd"] == "PERMIT-TO-JOIN":
        self.log.logging(
            "TransportZigpy",
            "Debug",
            "PERMIT-TO-JOIN: %s duration: %s" % (data["datas"]["targetRouter"], data["datas"]["Duration"]),
        )
        duration = data["datas"]["Duration"]
        target_router = data["datas"]["targetRouter"]
        target_router = None if target_router == "FFFC" else t.EUI64(t.uint64_t(target_router).serialize())
        duration == 0xFE if duration == 0xFF else duration
        self.permit_to_join_timer["Timer"] = time.time()
        self.permit_to_join_timer["Duration"] = duration 

        if target_router is None:
            self.log.logging("TransportZigpy", "Debug", "PERMIT-TO-JOIN: duration: %s for Radio: %s" % (duration, self._radiomodule))
            if self._radiomodule == "deCONZ":
                await self.app.permit_ncp( time_s=duration)
            else:
                await self.app.permit(time_s=duration)            
        else:
            self.log.logging(
                "TransportZigpy", "Debug", "PERMIT-TO-JOIN: duration: %s target: %s" % (duration, target_router))
            if self._radiomodule == "deCONZ":
                await self.app.permit_ncp( time_s=duration)  
            else:
                await self.app.permit(time_s=duration, node=target_router)
                


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

    elif data["cmd"] == "REQ-NWK-STATUS":
        await asyncio.sleep(10)
        #await self.app.load_network_info()
        self.forwarder_queue.put(build_plugin_8009_frame_content(self, self._radiomodule))

    elif data["cmd"] == "RAW-COMMAND":
        self.log.logging("TransportZigpy", "Debug", "RAW-COMMAND: %s" % properyly_display_data(data["datas"]))
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

    self.log.logging(
        "TransportZigpy",
        "Debug",
        "ZigyTransport: process_raw_command ready to request Function: %s NwkId: %04x/%s Cluster: %04x Seq: %02x Payload: %s AddrMode: %02x EnableAck: %s, Sqn: %s"
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
        ),
    )

    if int(NwkId, 16) >= 0xFFFB:  # Broadcast
        destination = int(NwkId, 16)
        self.log.logging("TransportZigpy", "Debug", "process_raw_command  call broadcast destination: %s" % NwkId)
        result, msg = await self.app.broadcast( Profile, Cluster, sEp, dEp, 0x0, 0x0, sequence, payload, )

    elif addressmode == 0x01:
        # Group Mode
        destination = int(NwkId, 16)
        self.log.logging("TransportZigpy", "Debug", "process_raw_command  call mrequest destination: %s" % destination)
        result, msg = await self.app.mrequest(destination, Profile, Cluster, sEp, sequence, payload)

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
                asyncio.create_task(
                    transport_request( self, destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=not AckIsDisable, use_ieee=False, ) )
            else:
                await transport_request( self, destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=not AckIsDisable, use_ieee=False, )
                
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
            asyncio.create_task(
                transport_request( self, destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=not AckIsDisable, use_ieee=False, ) )
        else:
            await transport_request( self, destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=not AckIsDisable, use_ieee=False, )

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
        
async def transport_request( self, destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=True, use_ieee=False ):
    _nwkid = destination.nwk.serialize()[::-1].hex()
    _ieee = str(destination.ieee)
    if not check_transport_readiness:
        return

    try:
        async with _limit_concurrency(self, destination, sequence):
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
            if self._currently_waiting_requests_list[_ieee]:
                await asyncio.sleep(0.250)

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
