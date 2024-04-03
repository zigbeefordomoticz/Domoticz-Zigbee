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

import asyncio
import asyncio.events
import binascii
import contextlib
import json
import queue
import sys
import time
import traceback
from pathlib import Path
from threading import Thread
from typing import Any, Optional

import serial
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
from zigpy.exceptions import (APIException, ControllerException, DeliveryError,
                              InvalidResponse)
from zigpy_znp.exceptions import (CommandNotRecognized, InvalidCommandResponse,
                                  InvalidFrame)

from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_0302_frame_content, build_plugin_8009_frame_content,
    build_plugin_8011_frame_content,
    build_plugin_8043_frame_list_node_descriptor,
    build_plugin_8045_frame_list_controller_ep)
from Classes.ZigpyTransport.tools import handle_thread_error
from Modules.macPrefix import DELAY_FOR_VERY_KEY, casaiaPrefix_zigpy
from Modules.tools import print_stack

MAX_ATTEMPS_REQUEST = 3
WAITING_TIME_BETWEEN_ATTEMPS = 0.250
MAX_CONCURRENT_REQUESTS_PER_DEVICE = 1
VERIFY_KEY_DELAY = 6
WAITING_TIME_BETWEEN_ATTEMPTS = 0.250


def stop_zigpy_thread(self):
    """ will send a STOP message to the writer_queue in order to stop the thread """
    self.log.logging("TransportZigpy", "Debug", "stop_zigpy_thread - Stopping zigpy thread")
    self.writer_queue.put_nowait("STOP")
    self.zigpy_running = False


def start_zigpy_thread(self):
    self.log.logging("TransportZigpy", "Debug", "start_zigpy_thread - Starting zigpy thread (1)")
    if sys.platform == "win32" and (3, 8, 0) <= sys.version_info < (3, 9, 0):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    setup_zigpy_thread(self)


def setup_zigpy_thread(self):
    self.log.logging("TransportZigpy", "Debug", "setup_zigpy_thread - Starting zigpy thread (1)")
    self.zigpy_loop = get_or_create_eventloop()
    
    if self.zigpy_loop:
        self.log.logging("TransportZigpy", "Debug", "setup_zigpy_thread - Starting zigpy thread")
        
        self.zigpy_thread = Thread(name=f"ZigpyCom_{self.hardwareid}", target=zigpy_thread, args=(self,))
        self.log.logging("TransportZigpy", "Debug", "setup_zigpy_thread - zigpy thread setup done")
        
        self.zigpy_thread.start()
        self.log.logging("TransportZigpy", "Debug", "setup_zigpy_thread - zigpy thread started")


def get_or_create_eventloop():
    loop = None
    try:
        loop = asyncio.get_event_loop()

    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
     
    asyncio.set_event_loop( loop )
    return loop   


def zigpy_thread(self):
    self.zigpy_loop.run_until_complete(start_zigpy_task(self, channel=0, extended_pan_id=0))
    self.zigpy_loop.close()


async def start_zigpy_task(self, channel, extended_pan_id):
    self.log.logging("TransportZigpy", "Debug", "start_zigpy_task - Starting zigpy thread")
    self.zigpy_running = True
    
    self.log.logging("TransportZigpy", "Debug", f"===> channel      : {self.pluginconf.pluginConf['channel']}")
    self.log.logging("TransportZigpy", "Debuf", f"===> extendedPANID: {self.pluginconf.pluginConf['extendedPANID']}")

    if "channel" in self.pluginconf.pluginConf:
        channel = int(self.pluginconf.pluginConf["channel"])
        self.log.logging("TransportZigpy", "Debug", f"===> channel: {channel}")

    if "extendedPANID" in self.pluginconf.pluginConf:
        if isinstance( self.pluginconf.pluginConf["extendedPANID"], str):
            extended_pan_id = int(self.pluginconf.pluginConf["extendedPANID"], 16)
        else:
            extended_pan_id = self.pluginconf.pluginConf["extendedPANID"]

        self.log.logging("TransportZigpy", "Debug", f"===> extendedPanId: 0x{extended_pan_id:X}")

    self.log.logging( "TransportZigpy", "Debug", f"start_zigpy_task -extendedPANID {self.pluginconf.pluginConf['extendedPANID']} {extended_pan_id}", )

    task = asyncio.create_task(
        radio_start(self, self.pluginconf, self.use_of_zigpy_persistent_db, self._radiomodule, self._serialPort, set_channel=channel, set_extendedPanId=extended_pan_id),
        name=f"radio_start-{self._radiomodule}-{self._serialPort}"
    )
    await asyncio.gather(task, return_exceptions=False)
    await asyncio.sleep(1)

    await _shutdown_remaining_task(self)

    self.log.logging("TransportZigpy", "Debug", "start_zigpy_task - exiting zigpy thread")


async def _shutdown_remaining_task(self):
    """Cleanup tasks tied to the service's shutdown."""

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    [task.cancel() for task in tasks]
    
    self.log.logging("TransportZigpy", "Debug", f"Cancelling {len(tasks)} outstanding tasks")
    
    await asyncio.gather(*tasks, return_exceptions=True)
    await asyncio.sleep(1)
    

async def radio_start(self, pluginconf, use_of_zigpy_persistent_db, radiomodule, serialPort, auto_form=False, set_channel=0, set_extendedPanId=0):

    self.log.logging("TransportZigpy", "Debug", "In radio_start %s" %radiomodule)

    try:
        if radiomodule == "ezsp":
            import bellows.config as conf

            from Classes.ZigpyTransport.AppBellows import App_bellows as App

            config = ezsp_configuration_setup(self, conf, serialPort)

            self.log.logging("TransportZigpy", "Status", "Started radio %s port: %s" %( radiomodule, serialPort))

        elif radiomodule =="znp":
            import zigpy_znp.config as conf

            from Classes.ZigpyTransport.AppZnp import App_znp as App

            config = znp_configuration_setup(self, conf, serialPort)

            self.log.logging("TransportZigpy", "Status", "Started radio znp port: %s" %(serialPort))

        elif radiomodule =="deCONZ":
            import zigpy_deconz.config as conf

            from Classes.ZigpyTransport.AppDeconz import App_deconz as App

            config = deconz_configuration_setup(self, conf, serialPort)

            self.log.logging("TransportZigpy", "Status", "Started radio deconz port: %s" %(serialPort))

        else:
            self.log.logging( "TransportZigpy", "Error", "Wrong radiomode: %s" % (radiomodule), )

    except Exception as e:
            self.log.logging("TransportZigpy", "Error", "Error while starting Radio: %s on port %s with %s" %( radiomodule, serialPort, e))
            self.log.logging("TransportZigpy", "Error", "%s" %traceback.format_exc())       


    optional_configuration_setup(self, config, conf, set_extendedPanId, set_channel)

    try:
        if radiomodule in ["znp", "deCONZ"]:
            self.app = App(config)

        elif radiomodule == "ezsp":
            self.app = App(conf.CONFIG_SCHEMA(config))

        else:
            self.log.logging( "TransportZigpy", "Error", "Wrong radiomode: %s" % (radiomodule), )
            return
        
    except Exception as e:
            self.log.logging( "TransportZigpy", "Error", "Error while starting radio %s on port: %s - Error: %s" %( radiomodule, serialPort, e) )
            return

    if self.pluginParameters["Mode3"] == "True":
        self.log.logging( "TransportZigpy", "Status", "Coordinator initialisation requested  Channel %s(0x%02x) ExtendedPanId: 0x%016x" % (
            set_channel, set_channel, set_extendedPanId), )
        new_network = True

    else:
        new_network = False

    if self.use_of_zigpy_persistent_db and self.app:
        self.log.logging( "TransportZigpy", "Status", "Use of zigpy Persistent Db")
        await self.app._load_db()

    await _radio_startup(self, pluginconf, use_of_zigpy_persistent_db, new_network, radiomodule)
    self.log.logging( "TransportZigpy", "Debug", "Exiting co-rounting radio_start")


def ezsp_configuration_setup(self, conf, serialPort):
    config = {
        conf.CONF_DEVICE: { "path": serialPort, "baudrate": 115200}, 
        conf.CONF_NWK: {},
        conf.CONF_EZSP_CONFIG: {},
        "handle_unknown_devices": True,
    }
    
    if "BellowsNoMoreEndDeviceChildren" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["BellowsNoMoreEndDeviceChildren"]:
        self.log.logging("TransportZigpy", "Status", "Set The maximum number of end device children that Coordinater will support to 0")
        config[conf.CONF_EZSP_CONFIG]["CONFIG_MAX_END_DEVICE_CHILDREN"] = 0
        
    if self.pluginconf.pluginConf["TXpower_set"]:
        self.log.logging("TransportZigpy", "Status", "Enables boost power mode and the alternate transmitter output.")
        config[conf.CONF_EZSP_CONFIG]["CONFIG_TX_POWER_MODE"] = 0x3
        
    return config


def znp_configuration_setup(self, conf, serialPort):
        
    config = {
        conf.CONF_DEVICE: {"path": serialPort, "baudrate": 115200}, 
        conf.CONF_NWK: {},
        conf.CONF_ZNP_CONFIG: { },
    }
    if specific_endpoints(self):
        config[ conf.CONF_ZNP_CONFIG][ "prefer_endpoint_1" ] = False
    
    if "TXpower_set" in self.pluginconf.pluginConf:
        config[conf.CONF_ZNP_CONFIG]["tx_power"] = int(self.pluginconf.pluginConf["TXpower_set"])
        
    return config


def deconz_configuration_setup(self, conf, serialPort):
    return {
        conf.CONF_DEVICE: {"path": serialPort, "baudrate": 115200},
        conf.CONF_NWK: {},
        # zigpy.config.CONF_STARTUP_ENERGY_SCAN: False
    }


def optional_configuration_setup(self, config, conf, set_extendedPanId, set_channel):

    # Enable or not Source Routing based on zigpySourceRouting setting
    config[zigpy.config.CONF_SOURCE_ROUTING] = bool( self.pluginconf.pluginConf["zigpySourceRouting"] )

    # Disable zigpy conf topo scan by default
    config[zigpy.config.CONF_TOPO_SCAN_ENABLED] = False

    # Config Zigpy db. if not defined, there is no persistent Db.
    if "enableZigpyPersistentInFile" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["enableZigpyPersistentInFile"]:
        data_folder = Path( self.pluginconf.pluginConf["pluginData"] )
        config[zigpy.config.CONF_DATABASE] = str(data_folder / ("zigpy_persistent_%02d.db"% self.hardwareid) )
        config[zigpy.config.CONF_TOPO_SCAN_ENABLED] = True
        config[zigpy.config.CONF_TOPO_SCAN_PERIOD] = 4 * 60  # 4 Hours

    elif "enableZigpyPersistentInMemory" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["enableZigpyPersistentInMemory"]:
        config[zigpy.config.CONF_DATABASE] = ":memory:"
        config[zigpy.config.CONF_TOPO_SCAN_ENABLED] = True
        config[zigpy.config.CONF_TOPO_SCAN_PERIOD] = 4 * 60  # 4 Hours

    # Manage coordinator auto backup
    if "autoBackup" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["autoBackup"]:
        config[zigpy.config.CONF_NWK_BACKUP_ENABLED] = True
        config[zigpy.config.CONF_NWK_BACKUP_PERIOD] = self.pluginconf.pluginConf["autoBackup"]
    else:
        config[zigpy.config.CONF_NWK_BACKUP_ENABLED] = False

    if set_extendedPanId != 0:
        config[conf.CONF_NWK][conf.CONF_NWK_EXTENDED_PAN_ID] = "%s" % ( t.EUI64(t.uint64_t(set_extendedPanId).serialize()) )

    if set_channel != 0:
        config[conf.CONF_NWK][conf.CONF_NWK_CHANNEL] = set_channel

    # Do we do energy scan at startup. By default it is set to False. Plugin might override it in the case of low number of devices.
    if "EnergyScanAtStatup" in self.pluginconf.pluginConf and not self.pluginconf.pluginConf["EnergyScanAtStatup"]:
        config[zigpy.config.CONF_STARTUP_ENERGY_SCAN] = False


async def _radio_startup(self, pluginconf, use_of_zigpy_persistent_db, new_network, radiomodule):
    
    try:
        await self.app.startup(
            self.hardwareid,
            pluginconf,
            use_of_zigpy_persistent_db,
            callBackHandleMessage=self.receiveData,
            callBackUpdDevice=self.ZigpyUpdDevice,
            callBackGetDevice=self.ZigpyGetDevice,
            callBackBackup=self.ZigpyBackupAvailable,
            captureRxFrame=self.captureRxFrame,
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


def post_coordinator_startup(self, radiomodule):
    # Send Network information to plugin, in order to poplulate various objetcs
    self.forwarder_queue.put(build_plugin_8009_frame_content(self, radiomodule))

    # Send Controller Active Node and Node Descriptor
    self.forwarder_queue.put( build_plugin_8045_frame_list_controller_ep( self, ) )

    self.log.logging( "TransportZigpy", "Debug", "Active Endpoint List:  %s" % str(self.app.get_device(nwk=t.NWK(0x0000)).endpoints.keys()), )
    for epid, ep in self.app.get_device(nwk=t.NWK(0x0000)).endpoints.items():
        if epid != 0 and ep.status == 0x00:
            self.log.logging( "TransportZigpy", "Debug", "Simple Descriptor:  %s" % ep)
            self.forwarder_queue.put(build_plugin_8043_frame_list_node_descriptor(self, epid, ep))

    self.log.logging( "TransportZigpy", "Debug", "Controller Model %s" % self.app.get_device(nwk=t.NWK(0x0000)).model )
    self.log.logging( "TransportZigpy", "Debug", "Controller Manufacturer %s" % self.app.get_device(nwk=t.NWK(0x0000)).manufacturer )
    # Let send a 0302 to simulate an Off/on
    self.forwarder_queue.put( build_plugin_0302_frame_content( self, ) )

    
def display_network_infos(self):
    self.log.logging( "TransportZigpy", "Status", "Network settings")
    self.log.logging( "TransportZigpy", "Status", "  Device IEEE: %s" %self.app.state.node_info.ieee)
    self.log.logging( "TransportZigpy", "Status", "  Device NWK: 0x%04X" %self.app.state.node_info.nwk)
    self.log.logging( "TransportZigpy", "Status", "  Network Update Id: 0x%04X" %self.app.state.network_info.nwk_update_id)
    
    self.log.logging( "TransportZigpy", "Status", "  PAN ID: 0x%04X" %self.app.state.network_info.pan_id)
    self.log.logging( "TransportZigpy", "Status", "  Extended PAN ID: %s" %self.app.state.network_info.extended_pan_id)

    self.log.logging( "TransportZigpy", "Status", "  Channel: %s" %self.app.state.network_info.channel)
    self.log.logging( "TransportZigpy", "Debug", "  Network key: " + ":".join( f"{c:02x}" for c in self.app.state.network_information.network_key.key ))


async def worker_loop(self):
    self.log.logging("TransportZigpy", "Debug", "worker_loop - ZigyTransport: worker_loop start.")

    self.writer_queue = queue.Queue()

    while self.zigpy_running and self.writer_queue is not None:
        self.log.logging("TransportZigpy", "Debug", "wait for command")
        command_to_send = await get_next_command(self)
        self.log.logging("TransportZigpy", "Debug", f"got an entry {command_to_send} ({type(command_to_send)})")

        if command_to_send is None:
            continue
        elif command_to_send == "STOP":
            # Shutting down
            self.log.logging("TransportZigpy", "Debug", "worker_loop - Shutting down ... exit.")
            self.zigpy_running = False
            break

        data = json.loads(command_to_send)
        self.log.logging("TransportZigpy", "Debug", f"got a command {data['cmd']} ({type(data['cmd'])})")

        if self.pluginconf.pluginConf["ZiGateReactTime"]:
            t_start = 1000 * time.time()

        try:
            await dispatch_command(self, data)

        except (DeliveryError, APIException, ControllerException, InvalidFrame, 
                CommandNotRecognized, ValueError, InvalidResponse, 
                InvalidCommandResponse, asyncio.TimeoutError, RuntimeError) as e:
            log_exception(self, type(e).__name__, e, data["cmd"], data["datas"])
            if isinstance(e, (APIException, ControllerException)):
                await asyncio.sleep(1.0)

        except Exception as e:
            self.log.logging("TransportZigpy", "Error", f"Error while receiving a Plugin command: >{e}<")
            handle_thread_error(self, e, data)

        if self.pluginconf.pluginConf["ZiGateReactTime"]:
            t_end = 1000 * time.time()
            t_elapse = int(t_end - t_start)
            self.statistics.add_timing_zigpy(t_elapse)
            if t_elapse > 1000:
                self.log.logging( "TransportZigpy", "Log", "process_raw_command (zigpyThread) spend more than 1s (%s ms) frame: %s" % (t_elapse, data), )


async def get_next_command(self):
    """ Get the next command in the writer Queue """
    while True:
        try:
            return self.writer_queue.get_nowait()

        except queue.Empty:
            await asyncio.sleep(0.100)

        except Exception as e:
            self.log.logging( "TransportZigpy", "Log", f"Error in get_next_command: {e}")
            return None


async def dispatch_command(self, data):
    cmd = data["cmd"]
    datas = data["datas"]

    if cmd == "COORDINATOR-BACKUP":
        await self.app.coordinator_backup()

    elif cmd == "GET-TIME":
        await self.app.get_time_server()

    elif cmd == "PERMIT-TO-JOIN":
        await _permit_to_joint(self, data)

    elif cmd == "RAW-COMMAND":
        self.log.logging("TransportZigpy", "Debug", f"RAW-COMMAND: {properyly_display_data(datas)}")
        await process_raw_command(self, datas, AckIsDisable=data["ACKIsDisable"], Sqn=data["Sqn"])

    elif cmd == "REMOVE-DEVICE":
        ieee = datas["Param1"]
        await self.app.remove_ieee(t.EUI64(t.uint64_t(ieee).serialize()))

    elif cmd == "REQ-NWK-STATUS":
        await asyncio.sleep(10)
        self.forwarder_queue.put(build_plugin_8009_frame_content(self, self._radiomodule))

    elif cmd == "SET-CERTIFICATION":
        await self.app.set_certification(datas["Param1"])

    elif cmd == "SET-CHANNEL":
        await self.app.move_network_to_channel(datas["Param1"])

    elif cmd == "SET-EXTPANID":
        self.app.set_extended_pan_id(datas["Param1"])

    elif cmd == "SET-LED":
        await self.app.set_led(datas["Param1"])

    elif cmd == "SET-TIME":
        await self.app.set_time_server(datas["Param1"])

    elif cmd == "SET-TX-POWER":
        await self.app.set_zigpy_tx_power(datas["Param1"])
        
    elif cmd == "INTERFERENCE-SCAN":
        await self.app.network_interference_scan()

    elif cmd == "ZIGPY-TOPOLOGY-SCAN":
        await self.app.start_topology_scan()


async def _permit_to_joint(self, data):
    log = self.log
    radiomodule = self._radiomodule
    app = self.app
    permit_to_join_timer = self.permit_to_join_timer

    log.logging("TransportZigpy", "Debug", f"PERMIT-TO-JOIN: {data}")

    duration = data["datas"]["Duration"]
    target_router = data["datas"]["targetRouter"]
    target_router = None if target_router == "FFFC" else t.EUI64(t.uint64_t(target_router).serialize())
    duration = 0xFE if duration == 0xFF else duration

    permit_to_join_timer["Timer"] = time.time()
    permit_to_join_timer["Duration"] = duration

    log.logging("TransportZigpy", "Status", f"PERMIT-TO-JOIN: duration: {duration} for Radio: {self._radiomodule} for node: {target_router}")

    if radiomodule == "deCONZ":
        return await app.permit_ncp(time_s=duration)

    log.logging("TransportZigpy", "Debug", f"Calling app.permit(time_s={duration}, node={target_router})")
    await app.permit(time_s=duration, node=target_router)
    log.logging("TransportZigpy", "Debug", f"Returning from app.permit(time_s={duration}, node={target_router})")


async def process_raw_command(self, data, AckIsDisable=False, Sqn=None):
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
    
    # extended_timeout managed the retry at zigpy level ( instruct the radio to use slower APS retries )
    # If the device is not listening on Idle ( end device ), enable the retry
    # However if PluginRetrys enabled, then we disable the slower APS retry as the plugin will do.
    extended_timeout = not data.get("RxOnIdle", False) and not self.pluginconf.pluginConf["PluginRetrys"]
    self.log.logging( "TransportZigpy", "Debug", f"process_raw_command: extended_timeout {extended_timeout}")
                     
    delay = data["Delay"] if "Delay" in data else None
    self.log.logging( "TransportZigpy", "Debug", "process_raw_command: process_raw_command ready to request Function: %s NwkId: %04x/%s Cluster: %04x Seq: %02x Payload: %s AddrMode: %02x EnableAck: %s, Sqn: %s, Delay: %s, Extended_TO: %s" % (
        Function, int(NwkId, 16), dEp, Cluster, sequence, binascii.hexlify(payload).decode("utf-8"), addressmode, not AckIsDisable, Sqn, delay,extended_timeout ), )

    destination, transport_needs = _get_destination(self, NwkId, addressmode, Profile, Cluster, sEp, dEp, sequence, payload)
    
    if destination is None:
        return
    
    if transport_needs == "Broadcast":
        self.log.logging("TransportZigpy", "Debug", "process_raw_command Broadcast: %s" % NwkId)
        result, msg = await self.app.broadcast( Profile, Cluster, sEp, dEp, 0x0, 0x0, sequence, payload, )
        await asyncio.sleep( 2 * WAITING_TIME_BETWEEN_ATTEMPTS)

    elif addressmode == 0x01:
        # Group Mode
        destination = int(NwkId, 16)
        self.log.logging("TransportZigpy", "Debug", "process_raw_command Multicast: %s" % destination)
        result, msg = await self.app.mrequest(destination, Profile, Cluster, sEp, sequence, payload)
        await asyncio.sleep( 2 * WAITING_TIME_BETWEEN_ATTEMPTS)

    elif transport_needs == "Unicast":
        self.log.logging( "TransportZigpy", "Debug", "process_raw_command Unicast destination: %s Profile: %s Cluster: %s sEp: %s dEp: %s Seq: %s Payload: %s" % (
            destination, Profile, Cluster, sEp, dEp, sequence, payload))

        if self.pluginconf.pluginConf["ForceAPSAck"]:
            self.log.logging( "TransportZigpy", "Debug", "    Forcing Ack by setting AckIsDisable = False and so ack_is_disable == False" ) 
            AckIsDisable = False

        try:
            task = asyncio.create_task(
                transport_request( self, Function,destination, Profile, Cluster, sEp, dEp, sequence, payload, ack_is_disable=AckIsDisable, use_ieee=False, delay=delay, extended_timeout=extended_timeout),
                name=f"transport_request-{Function}-{destination}-{Cluster}-{Sqn}"
                )
            self.statistics._sent += 1

        except (asyncio.TimeoutError, asyncio.exceptions.TimeoutError) as e:
            self.log.logging("TransportZigpy", "Log", f"process_raw_command: TimeoutError {destination} {Profile} {Cluster} {payload}")
            error_msg = "%s" % e
            result = 0xB6

        except (asyncio.CancelledError, asyncio.exceptions.CancelledError) as e:
            self.log.logging("TransportZigpy", "Log", f"process_raw_command: CancelledError {destination} {Profile} {Cluster} {payload}")
            error_msg = "%s" % e
            result = 0xB6
            
        except AttributeError as e:
            self.log.logging("TransportZigpy", "Log", f"process_raw_command: AttributeError {Profile} {type(Profile)} {Cluster} {type(Cluster)}")
            error_msg = "%s" % e
            result = 0xB6

        except DeliveryError as e:
            # This could be relevant to APS NACK after retry
            # Request failed after 5 attempts: <Status.MAC_NO_ACK: 233>
            self.log.logging("TransportZigpy", "Debug", "process_raw_command - DeliveryError : %s" % e)
            error_msg = "%s" % e
            result = int(e.status) if hasattr(e, 'status') else 0xB6

    if result:
        self.log.logging( "TransportZigpy", "Debug", "ZigyTransport: process_raw_command completed NwkId: %s result: %s msg: %s" % (destination, result, error_msg), )
        return


def _get_destination(self, NwkId, addressmode, Profile, Cluster, sEp, dEp, sequence, payload):

    if int(NwkId, 16) >= 0xFFFB:  
        # Broadcast
        return int(NwkId, 16), "Broadcast"

    elif addressmode == 0x01:
        # Group
        return int(NwkId, 16), "Multicast"

    elif addressmode in (0x02, 0x07):
        # 0x02 Short address
        # 0x07 Short address with No Ack (Zigate)
        try:
            destination = self.app.get_device(nwk=t.NWK(int(NwkId, 16)))

        except KeyError:
            self.log.logging( "TransportZigpy", "Error", f"_get_destination unable to get destination. Nwkid {NwkId} AddrMode {addressmode}")
            destination = None

        return destination, "Unicast"

    elif addressmode in (0x03, 0x08):
        # 0x03 IEEE
        # 0x08 IEEE with No Ack (Zigate)
        return self.app.get_device(nwk=t.NWK(int(NwkId, 16))), "Unicast"    


def push_APS_ACK_NACKto_plugin(self, nwkid, result, lqi):
    # Looks like Zigate return an int, while ZNP returns a status.type
    self.log.logging("TransportZigpy", "Debug", f"push_APS_ACK_NACK to_plugin - {nwkid} - Result: {result} LQI: {lqi}")
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
    radiomodule = self._radiomodule
    if radiomodule in {"zigate", "deCONZ", "ezsp"}:
        return True

    if radiomodule == "znp":
        app = self.app
        return app._znp is not None

    return False


async def transport_request(self, Function, destination, Profile, Cluster, sEp, dEp, sequence, payload, ack_is_disable=False, use_ieee=False, delay=None, extended_timeout=False):
    """Send a zigbee message based on different arguments

    Args:
        destination (_type_): Destination network address
        Profile (_type_): Zigbee Profile ID ( 0x000 or 0X0104)
        Cluster (_type_): Cluster to be use
        sEp (_type_): Source endpoint
        dEp (_type_): Destination endpoint
        sequence (_type_): sequence number
        payload (_type_): zigbee payload (based on profile id and cluster)
        ack_is_disable (bool, optional): is ACK disable. Defaults to False.
        use_ieee (bool, optional): for usage of IEEE. Defaults to False.
        delay (_type_, optional): delay in seconds. Defaults to None.
        extended_timeout (bool, optional): Is extended timeout needed. Defaults to False.
    """

    _nwkid = destination.nwk.serialize()[::-1].hex()
    _ieee = str(destination.ieee)

    if not check_transport_readiness(self):
        return

    if Profile == 0x0000 and Cluster == 0x0005 and _ieee and _ieee[:8] in DELAY_FOR_VERY_KEY:
        self.log.logging("TransportZigpy", "Log", "Waiting 6 seconds for CASA.IA Confirm Key")
        delay = VERIFY_KEY_DELAY

    if delay:
        self.log.logging("TransportZigpy", "Debug", f"transport_request: delay for {delay} seconds")
        await asyncio.sleep(delay)

    async with _limit_concurrency(self, destination, sequence):

        if _ieee in self._currently_not_reachable and self._currently_waiting_requests_list[_ieee]:
            self.log.logging("TransportZigpy", "Debug", f"transport_request: Request {sequence} skipped NwkId: {_nwkid} not reachable - {_ieee} {str(self._currently_not_reachable)} {self._currently_waiting_requests_list[_ieee]}", _nwkid)
            return

        await _send_and_retry(self, Function, destination, Profile, Cluster, _nwkid, sEp, dEp, sequence, payload, use_ieee, _ieee,ack_is_disable, extended_timeout )


async def _send_and_retry(self, Function, destination, Profile, Cluster, _nwkid, sEp, dEp, sequence, payload, use_ieee, _ieee,ack_is_disable, extended_timeout ):

    max_retry = MAX_ATTEMPS_REQUEST if self.pluginconf.pluginConf["PluginRetrys"] else 1

    for attempt in range(1, (max_retry + 1)):
        try:
            self.log.logging("TransportZigpy", "Debug", f"_send_and_retry: {_ieee} {Profile} {Cluster} - Expect_Reply: {ack_is_disable} extended_timeout: {extended_timeout} Attempts: {attempt}/{max_retry}")
            result, msg = await self.app.request(destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=not ack_is_disable, use_ieee=use_ieee, extended_timeout=extended_timeout)

        except (asyncio.exceptions.CancelledError, asyncio.CancelledError, asyncio.exceptions.TimeoutError, asyncio.TimeoutError, AttributeError, asyncio.exceptions.CancelledError, asyncio.exceptions.TimeoutError, DeliveryError) as e:
            self.log.logging("TransportZigpy", "Log", f"{Function} {_ieee}/0x{_nwkid} 0x{Profile} 0x{Cluster}:16 Ack: {ack_is_disable} RETRY: {attempt}/{max_retry} - {e}")

            if attempt < max_retry:
                # Slow down the throughput when too many commands. Try not to overload the coordinators
                multi = 1.5 if self._currently_waiting_requests_list[_ieee] else 1
                await asyncio.sleep(multi * WAITING_TIME_BETWEEN_ATTEMPTS)
                continue

            # Stop here as we have exceed the max retrys
            result = int(e.status) if hasattr(e, 'status') else 0xB6
            handle_transport_result(self, Function, sequence, result, ack_is_disable, _ieee, _nwkid, destination.lqi)
            break

        else:
            # Success
            handle_transport_result(self, Function, sequence, result, ack_is_disable, _ieee, _nwkid, destination.lqi)
            self.log.logging("TransportZigpy", "Debug", f"transport_request: result: {result}")
            break


def handle_transport_result(self, Function, sequence, result, ack_is_disable, _ieee, _nwkid, lqi):
    self.log.logging("TransportZigpy", "Debug", f"handle_transport_result - {Function} - {_nwkid} - Ack: {ack_is_disable} Result: {result}")
    #if not ack_is_disable:
    push_APS_ACK_NACKto_plugin(self, _nwkid, result, lqi)

    if result == 0x00 and _ieee in self._currently_not_reachable:
        self._currently_not_reachable.remove(_ieee)
        self.log.logging("TransportZigpy", "Debug", f"handle_transport_result -removing {_ieee} to not_reachable queue")

    elif result != 0x00 and _ieee not in self._currently_not_reachable:
        # Mark the ieee has not reachable.
        self.log.logging("TransportZigpy", "Debug", f"handle_transport_result -adding {_ieee} to not_reachable queue")
        self._currently_not_reachable.append(_ieee)


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

    start_time = time.monotonic()
    was_locked = self._concurrent_requests_semaphores_list[_ieee].locked()

    if was_locked:
        self._currently_waiting_requests_list[_ieee] += 1
        self.log.logging( "TransportZigpy", "Debug", "Max concurrency reached for %s, delaying request %s (%s enqueued)" % (
            _nwkid, sequence, self._currently_waiting_requests_list[_ieee]), _nwkid, )

    try:
        async with self._concurrent_requests_semaphores_list[_ieee]:
            if was_locked:
                self.log.logging( "TransportZigpy", "Debug", "Previously delayed request %s is now running, " "delayed by %0.2f seconds for %s" % (
                    sequence, (time.monotonic() - start_time), _nwkid), _nwkid, )
            yield

    finally:
        if was_locked:
            self._currently_waiting_requests_list[_ieee] -= 1


def specific_endpoints(self):
    supported_plugins = ["Terncy", "Konke", "Wiser", "Orvibo", "Livolo", "Wiser2"]

    return any(
        plugin in self.pluginconf.pluginConf
        and self.pluginconf.pluginConf[plugin]
        for plugin in supported_plugins
    )
