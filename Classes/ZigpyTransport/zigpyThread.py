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
import serial_asyncio as pyserial_asyncio
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
from Modules.macPrefix import DELAY_FOR_VERY_KEY

MAX_ATTEMPS_REQUEST = 3
WAITING_TIME_BETWEEN_ATTEMPS = 0.250
MAX_CONCURRENT_REQUESTS_PER_DEVICE = 1
VERIFY_KEY_DELAY = 6
WAITING_TIME_BETWEEN_ATTEMPTS = 0.250


def stop_zigpy_thread(self):
    """ will send a STOP message to the writer_queue in order to stop the thread """
    self.log.logging("TransportZigpy", "Debug", "stop_zigpy_thread - Stopping zigpy thread")
    if self.writer_queue:
        self.writer_queue.put_nowait("STOP")
    self.zigpy_running = False

    # Make sure top the manualy started task
    if self.manual_topology_scan_task:
        self.manual_topology_scan_task.cancel()

    if self.manual_interference_scan_task:
        self.manual_interference_scan_task.cancel()


def start_zigpy_thread(self):
    self.log.logging("TransportZigpy", "Debug", "start_zigpy_thread - Starting zigpy thread")
    if sys.platform == "win32" and (3, 8, 0) <= sys.version_info < (3, 9, 0):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    setup_zigpy_thread(self)


def setup_zigpy_thread(self):
    self.log.logging("TransportZigpy", "Debug", "setup_zigpy_thread - Starting zigpy thread")
    self.zigpy_thread = Thread(name=f"ZigpyCom_{self.hardwareid}", target=zigpy_thread, args=(self,))
    self.zigpy_thread.start()

    self.log.logging("TransportZigpy", "Debug", "setup_zigpy_thread - zigpy thread started")


def zigpy_thread(self):
    self.zigpy_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(self.zigpy_loop)

    if self.pluginconf.pluginConf["EventLoopInstrumentation"]:
        self.zigpy_loop.set_debug(enabled=True)

    self.log.logging("TransportZigpy", "Log", "zigpyThread EventLoop : %s" %self.zigpy_loop)
    try:
        self.zigpy_loop.run_until_complete(start_zigpy_task(self, channel=0, extended_pan_id=0))
    except Exception as e:
        self.log.logging("TransportZigpy", "Error", "zigpy_thread error when starting %s" %e)

    finally:
        self.zigpy_loop.close()


async def start_zigpy_task(self, channel, extended_pan_id):
    self.log.logging("TransportZigpy", "Debug", "start_zigpy_task - Starting zigpy thread")
    self.zigpy_running = True
    
    if "channel" in self.pluginconf.pluginConf:
        channel = int(self.pluginconf.pluginConf["channel"])

    if "extendedPANID" in self.pluginconf.pluginConf:
        if isinstance( self.pluginconf.pluginConf["extendedPANID"], str):
            extended_pan_id = int(self.pluginconf.pluginConf["extendedPANID"], 16)
        else:
            extended_pan_id = self.pluginconf.pluginConf["extendedPANID"]

    self.log.logging( "TransportZigpy", "Debug", f"start_zigpy_task -extendedPANID {self.pluginconf.pluginConf['extendedPANID']} {extended_pan_id}", )

    await radio_start(self, self.statistics, self.pluginconf, self.use_of_zigpy_persistent_db, self._radiomodule, self._serialPort, set_channel=channel, set_extendedPanId=extended_pan_id),

    # Run forever
    self.writer_queue = queue.Queue()  # We MUST use queue and not asyncio.Queue, because it is not compatible with the Domoticz framework

    await worker_loop(self)

    # We exit the worker_loop, shutdown time
    await self.app.shutdown()

    #await asyncio.gather(task, return_exceptions=False)
    await asyncio.sleep(1)

    await _shutdown_remaining_task(self)

    self.log.logging("TransportZigpy", "Debug", "start_zigpy_task - exiting zigpy thread")


async def _shutdown_remaining_task(self):
    """Cleanup tasks tied to the service's shutdown."""
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    [task.cancel() for task in tasks]
    
    self.log.logging("TransportZigpy", "Log", f"Cancelling {len(tasks)} outstanding tasks")
    
    await asyncio.gather(*tasks, return_exceptions=True)
    await asyncio.sleep(1)
    

async def radio_start(self, statistics, pluginconf, use_of_zigpy_persistent_db, radiomodule, serialPort, auto_form=False, set_channel=0, set_extendedPanId=0):

    self.log.logging("TransportZigpy", "Debug", "In radio_start %s" %radiomodule)

    try:
        if radiomodule == "ezsp":
            import bellows.config as radio_specific_conf
            from Classes.ZigpyTransport.AppBellows import App_bellows as App

            config = ezsp_configuration_setup(self, radio_specific_conf, serialPort)
            self.log.logging("TransportZigpy", "Status", "++ Started radio %s port: %s" %( radiomodule, serialPort))

        elif radiomodule =="znp":
            import zigpy_znp.config as radio_specific_conf

            from Classes.ZigpyTransport.AppZnp import App_znp as App

            config = znp_configuration_setup(self, radio_specific_conf, serialPort)
            self.log.logging("TransportZigpy", "Status", "++ Started radio znp port: %s" %(serialPort))

        elif radiomodule =="deCONZ":
            import zigpy_deconz.config as radio_specific_conf

            from Classes.ZigpyTransport.AppDeconz import App_deconz as App

            config = deconz_configuration_setup(self, radio_specific_conf, serialPort)
            self.log.logging("TransportZigpy", "Status", "++ Started radio deconz port: %s" %(serialPort))

        else:
            self.log.logging( "TransportZigpy", "Error", "Wrong radiomode: %s" % (radiomodule), )

    except Exception as e:
            self.log.logging("TransportZigpy", "Error", "Error while starting Radio: %s on port %s with %s" %( radiomodule, serialPort, e))
            self.log.logging("TransportZigpy", "Error", "%s" %traceback.format_exc())       

    optional_configuration_setup(self, config, radio_specific_conf, set_extendedPanId, set_channel)

    try:
        if radiomodule in ["znp", "deCONZ", "ezsp"]:
            self.app = App(config)

        else:
            self.log.logging( "TransportZigpy", "Error", "Wrong radiomode: %s" % (radiomodule), )
            return

    except Exception as e:
            self.log.logging( "TransportZigpy", "Error", "Error while starting radio %s on port: %s - Error: %s" %( radiomodule, serialPort, e) )
            return

    if self.pluginParameters["Mode3"] == "True":
        self.log.logging( "TransportZigpy", "Status", "++ Coordinator initialisation requested Channel %s(0x%02x) ExtendedPanId: 0x%016x" % (
            set_channel, set_channel, set_extendedPanId), )
        new_network = True

    else:
        new_network = False

    if self.use_of_zigpy_persistent_db and self.app:
        self.log.logging( "TransportZigpy", "Status", "++ Use of Zigpy Persistent Db")
        await self.app._load_db()

    await _radio_startup(self, statistics, pluginconf, use_of_zigpy_persistent_db, new_network, radiomodule)
    self.log.logging( "TransportZigpy", "Debug", "Exiting co-rounting radio_start")


def ezsp_configuration_setup(self, bellows_conf, serialPort):
    config = {
        zigpy.config.CONF_DEVICE: { zigpy.config.CONF_DEVICE_PATH: serialPort, zigpy.config.CONF_DEVICE_BAUDRATE: 115200},
        zigpy.config.CONF_NWK: {},
        bellows_conf.CONF_EZSP_CONFIG: {},
        zigpy.config.CONF_OTA: {},
        "handle_unknown_devices": True,
    }

    if "BellowsNoMoreEndDeviceChildren" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["BellowsNoMoreEndDeviceChildren"]:
        self.log.logging("TransportZigpy", "Status", "++ Set The maximum number of end device children that Coordinater will support to 0")
        config[bellows_conf.CONF_EZSP_CONFIG]["CONFIG_MAX_END_DEVICE_CHILDREN"] = 0

    if self.pluginconf.pluginConf["TXpower_set"]:
        self.log.logging("TransportZigpy", "Status", "++ Enables boost power mode and the alternate transmitter output.")
        config[bellows_conf.CONF_EZSP_CONFIG]["CONFIG_TX_POWER_MODE"] = 0x3

    return config


def znp_configuration_setup(self, znp_conf, serialPort):
        
    config = {
        zigpy.config.CONF_DEVICE: {"path": serialPort, "baudrate": 115200}, 
        zigpy.config.CONF_NWK: {},
        znp_conf.CONF_ZNP_CONFIG: { },
        zigpy.config.CONF_OTA: {},
    }
    if specific_endpoints(self):
        config[ znp_conf.CONF_ZNP_CONFIG][ "prefer_endpoint_1" ] = False
    
    if "TXpower_set" in self.pluginconf.pluginConf:
        config[znp_conf.CONF_ZNP_CONFIG]["tx_power"] = int(self.pluginconf.pluginConf["TXpower_set"])
        
    return config


def deconz_configuration_setup(self, deconz_conf, serialPort):
    return {
        zigpy.config.CONF_DEVICE: {"path": serialPort, "baudrate": 115200},
        zigpy.config.CONF_NWK: {},
        zigpy.config.CONF_OTA: {},
    }


def optional_configuration_setup(self, config, conf, set_extendedPanId, set_channel):

    # In case we have to set the Extended PAN Id
    if set_extendedPanId != 0:
        config[conf.CONF_NWK][conf.CONF_NWK_EXTENDED_PAN_ID] = "%s" % ( t.EUI64(t.uint64_t(set_extendedPanId).serialize()) )

    # In case we have to force the Channel
    if set_channel != 0:
        config[conf.CONF_NWK][conf.CONF_NWK_CHANNEL] = set_channel

    # Enable or not Source Routing based on zigpySourceRouting setting
    config[zigpy.config.CONF_SOURCE_ROUTING] = bool( self.pluginconf.pluginConf["zigpySourceRouting"] )
    
    # Disable Zigpy OTA
    config[zigpy.config.CONF_OTA][zigpy.config.CONF_OTA_ENABLED] = False
    
    # Disable zigpy conf topo scan by default
    config[zigpy.config.CONF_TOPO_SCAN_ENABLED] = False

    # Config Zigpy db. if not defined, there is no persistent Db.
    if "enableZigpyPersistentInFile" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["enableZigpyPersistentInFile"]:
        data_folder = Path( self.pluginconf.pluginConf["pluginData"] )
        config[zigpy.config.CONF_DATABASE] = str(data_folder / ("zigpy_persistent_%02d.db"% self.hardwareid) )
        config[zigpy.config.CONF_TOPO_SCAN_ENABLED] = True
        config[zigpy.config.CONF_TOPO_SCAN_PERIOD] = 12 * 60  # 12 Hours

    elif "enableZigpyPersistentInMemory" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["enableZigpyPersistentInMemory"]:
        config[zigpy.config.CONF_DATABASE] = ":memory:"
        config[zigpy.config.CONF_TOPO_SCAN_ENABLED] = True
        config[zigpy.config.CONF_TOPO_SCAN_PERIOD] = 12 * 60  # 12 Hours

    # Manage coordinator auto backup
    if "autoBackup" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["autoBackup"]:
        config[zigpy.config.CONF_NWK_BACKUP_ENABLED] = True
        config[zigpy.config.CONF_NWK_BACKUP_PERIOD] = self.pluginconf.pluginConf["autoBackup"]
    else:
        config[zigpy.config.CONF_NWK_BACKUP_ENABLED] = False

    # Do we do energy scan at startup. By default it is set to False. Plugin might override it in the case of low number of devices.
    if "EnergyScanAtStatup" in self.pluginconf.pluginConf and not self.pluginconf.pluginConf["EnergyScanAtStatup"]:
        config[zigpy.config.CONF_STARTUP_ENERGY_SCAN] = False


async def _radio_startup(self, statistics, pluginconf, use_of_zigpy_persistent_db, new_network, radiomodule):
    
    try:
        await self.app.startup(
            self.statistics,
            self.hardwareid,
            pluginconf,
            use_of_zigpy_persistent_db,
            callBackHandleMessage=self.receiveData,
            callBackUpdDevice=self.ZigpyUpdDevice,
            callBackGetDevice=self.ZigpyGetDevice,
            callBackBackup=self.ZigpyBackupAvailable,
            callBackRestartPlugin=self.restart_plugin,
            captureRxFrame=self.captureRxFrame,
            auto_form=True,
            force_form=new_network,
            log=self.log,
            permit_to_join_timer=self.permit_to_join_timer,
        )
    except Exception as e:
        self.log.logging( "TransportZigpy", "Error", "Error at startup %s" %e)
        
    if new_network:
        # Assume that the new network has been created
        self.log.logging( "TransportZigpy", "Status", "++ Assuming new network formed")
        self.ErasePDMDone = True  

    display_network_infos(self)
    self.ControllerData["Network key"] = ":".join( f"{c:02x}" for c in self.app.state.network_information.network_key.key )
    
    post_coordinator_startup(self, radiomodule)
    

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
    self.log.logging( "TransportZigpy", "Status", "++ Network settings")
    self.log.logging( "TransportZigpy", "Status", "++   Device IEEE        : %s" %self.app.state.node_info.ieee)
    self.log.logging( "TransportZigpy", "Status", "++   Device NWK         : 0x%04X" %self.app.state.node_info.nwk)
    self.log.logging( "TransportZigpy", "Status", "++   Network Update Id  : 0x%04X" %self.app.state.network_info.nwk_update_id)
    self.log.logging( "TransportZigpy", "Status", "++   PAN ID             : 0x%04X" %self.app.state.network_info.pan_id)
    self.log.logging( "TransportZigpy", "Status", "++   Extended PAN ID    : %s" %self.app.state.network_info.extended_pan_id)
    self.log.logging( "TransportZigpy", "Status", "++   Channel            : %s" %self.app.state.network_info.channel)
    self.log.logging( "TransportZigpy", "Debug", "++   Network key: " + ":".join( f"{c:02x}" for c in self.app.state.network_information.network_key.key ))


async def worker_loop(self):
    self.log.logging("TransportZigpy", "Debug", "worker_loop - ZigyTransport: worker_loop start.")

    while self.zigpy_running:
        command_to_send = await get_next_command(self)

        if command_to_send is None:
            continue

        if command_to_send == "STOP":
            # Shutting down
            self.log.logging("TransportZigpy", "Debug", "worker_loop - Shutting down ... exit.")
            self.zigpy_running = False
            break

        await process_incoming_command(self, command_to_send),


async def process_incoming_command(self, command_to_send):
    data = json.loads(command_to_send)
    try:
        await dispatch_command(self, data)

    except (DeliveryError, APIException, ControllerException, InvalidFrame, 
            CommandNotRecognized, ValueError, InvalidResponse, 
            InvalidCommandResponse, asyncio.TimeoutError, RuntimeError) as e:
        log_exception(self, type(e).__name__, e, data.get("cmd", ""), data.get("datas", ""))
        if isinstance(e, (APIException, ControllerException)):
            await asyncio.sleep(1.0)

    except Exception as e:
        self.log.logging("TransportZigpy", "Error", f"Error while receiving a Plugin command: >{e}<")
        handle_thread_error(self, e, data)


async def get_next_command(self):
    """Get the next command in the writer Queue."""
    while True:
        try:
            return self.writer_queue.get_nowait()

        except queue.Empty:
            await asyncio.sleep(0.100)

        except Exception as e:
            self.log.logging("TransportZigpy", "Log", f"Error in get_next_command: {e}")
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
        self.manual_interference_scan_task = asyncio.create_task( self.app.network_interference_scan(), name="INTERFERENCE-SCAN")

    elif cmd == "ZIGPY-TOPOLOGY-SCAN":
        self.manual_topology_scan_task = asyncio.create_task( self.app.start_topology_scan(), name="ZIGPY-TOPOLOGY-SCAN")


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

    log.logging("TransportZigpy", "Status", f"++ opening zigbee network for {duration} secondes on specific router {target_router}")

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

    extended_timeout = not data.get("RxOnIdle", False) and not self.pluginconf.pluginConf["PluginRetrys"]
    self.log.logging("TransportZigpy", "Debug", f"process_raw_command: extended_timeout {extended_timeout}")

    delay = data.get("Delay", None)
    self.log.logging("TransportZigpy", "Debug", f"process_raw_command: process_raw_command ready to request Function: {Function} NwkId: {NwkId}/{dEp} Cluster: {Cluster} Seq: {sequence} Payload: {payload.hex()} AddrMode: {addressmode} AckIsDisable: {AckIsDisable} EnableAck: {not AckIsDisable}, Sqn: {Sqn}, Delay: {delay}, Extended_TO: {extended_timeout}")

    destination, transport_needs = _get_destination(self, NwkId, addressmode, Profile, Cluster, sEp, dEp, sequence, payload)

    if destination is None:
        return

    if transport_needs == "Broadcast":
        self.log.logging("TransportZigpy", "Debug", f"process_raw_command Broadcast: {NwkId}")
        result, msg = await _broadcast_command(self, Profile, Cluster, sEp, dEp, sequence, payload)

    elif addressmode == 0x01:
        result, msg = await _multicast_command(self, NwkId, Profile, Cluster, sEp, sequence, payload)

    elif transport_needs == "Unicast":
        result, msg = await _unicast_command(self, destination, Profile, Cluster, sEp, dEp, sequence, payload, AckIsDisable, delay, extended_timeout, Function, Sqn)

    self.log.logging("TransportZigpy", "Debug", f"ZigyTransport: process_raw_command completed NwkId: {destination} result: {result} msg: {msg}")


async def _broadcast_command(self, Profile, Cluster, sEp, dEp, sequence, payload):
    result, msg = await self.app.broadcast(Profile, Cluster, sEp, dEp, 0x0, 0x0, sequence, payload)
    await asyncio.sleep(2 * WAITING_TIME_BETWEEN_ATTEMPTS)
    return result, msg


async def _multicast_command(self, NwkId, Profile, Cluster, sEp, sequence, payload):
    destination = int(NwkId, 16)
    self.log.logging("TransportZigpy", "Debug", f"process_raw_command Multicast: {destination}")
    result, msg = await self.app.mrequest(destination, Profile, Cluster, sEp, sequence, payload)
    await asyncio.sleep(2 * WAITING_TIME_BETWEEN_ATTEMPTS)
    return result, msg


async def _unicast_command(self, destination, Profile, Cluster, sEp, dEp, sequence, payload, AckIsDisable, delay, extended_timeout, Function, Sqn):
    self.log.logging("TransportZigpy", "Debug", f"process_raw_command Unicast destination: {destination} Profile: {Profile} Cluster: {Cluster} sEp: {sEp} dEp: {dEp} Seq: {sequence} Payload: {payload.hex()}")
    AckIsDisable = False if self.pluginconf.pluginConf["ForceAPSAck"] else AckIsDisable

    try:
        task = asyncio.create_task(
            transport_request(self, Function, destination, Profile, Cluster, sEp, dEp, sequence, payload, ack_is_disable=AckIsDisable, use_ieee=False, delay=delay, extended_timeout=extended_timeout),
            name=f"_unicast_command-{Function}-{destination}-{Cluster}-{Sqn}"
        )

    except (asyncio.TimeoutError, asyncio.exceptions.TimeoutError) as e:
        self.log.logging("TransportZigpy", "Log", f"process_raw_command: TimeoutError {destination} {Profile} {Cluster} {payload}")
        error_msg = str(e)
        result = 0xB6
        self.statistics._TOdata += 1

    except (asyncio.CancelledError, asyncio.exceptions.CancelledError) as e:
        self.log.logging("TransportZigpy", "Log", f"process_raw_command: CancelledError {destination} {Profile} {Cluster} {payload}")
        error_msg = str(e)
        result = 0xB6
        self.statistics._ackKO += 1

    except AttributeError as e:
        self.log.logging("TransportZigpy", "Log", f"process_raw_command: AttributeError {Profile} {type(Profile)} {Cluster} {type(Cluster)}")
        error_msg = str(e)
        result = 0xB6
        self.statistics._ackKO += 1

    except DeliveryError as e:
        self.log.logging("TransportZigpy", "Debug", f"process_raw_command - DeliveryError : {e}")
        error_msg = str(e)
        result = int(e.status) if hasattr(e, 'status') else 0xB6
        self.statistics._ackKO += 1

    else:
        self.statistics._sent += 1
        result = None
        error_msg = ""

    return result, error_msg


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


def measure_execution_time(func):
    async def wrapper(self, Function, destination, Profile, Cluster, sEp, dEp, sequence, payload, ack_is_disable, use_ieee, delay, extended_timeout):
        t_start = None
        if self.pluginconf.pluginConf.get("ZigpyReactTime", False):
            t_start = int(1000 * time.time())

        try:
            await func(self, Function, destination, Profile, Cluster, sEp, dEp, sequence, payload, ack_is_disable, use_ieee, delay, extended_timeout)

        finally:
            if t_start:
                t_end = int(1000 * time.time())
                t_elapse = t_end - t_start
                self.statistics.add_timing_zigpy(t_elapse)  
                self.log.logging("TransportZigpy", "Log", f"| (transport_request) | {t_elapse} | {Function} | {sequence} | {ack_is_disable} | {destination.nwk} | {destination.ieee} | {destination.model} | {destination.manufacturer_id} | {destination.is_initialized} | {destination.rssi} | {destination.lqi} |")
    return wrapper


@measure_execution_time
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


async def _send_and_retry(self, Function, destination, Profile, Cluster, _nwkid, sEp, dEp, sequence, payload, use_ieee, _ieee, ack_is_disable, extended_timeout):

    max_retry = MAX_ATTEMPS_REQUEST if self.pluginconf.pluginConf["PluginRetrys"] else 1
  
    for attempt in range(1, (max_retry + 1)):
        try:
            self.log.logging("TransportZigpy", "Debug", f"_send_and_retry: {_ieee} {Profile:X} {Cluster:X} - AckIsDisable: {ack_is_disable} extended_timeout: {extended_timeout} Attempts: {attempt}/{max_retry}")
            result, _ = await zigpy_request(self, destination, Profile, Cluster, sEp, dEp, sequence, payload, ack_is_disable=ack_is_disable, use_ieee=use_ieee, extended_timeout=extended_timeout)

        except (asyncio.exceptions.TimeoutError, asyncio.exceptions.CancelledError, AttributeError, DeliveryError) as e:
            error_log_message = f"Warning while submitting - {Function} {_ieee}/0x{_nwkid} 0x{Profile:X} 0x{Cluster:X} payload: {payload} AckIsDisable: {ack_is_disable} Retry: {attempt}/{max_retry} with exception ({e})"
            self.log.logging("TransportZigpy", "Log", error_log_message)

            if await _retry_or_not(self, attempt, max_retry, Function, sequence, ack_is_disable, _ieee, _nwkid, destination, e):
                self.statistics._reTx += 1
                if isinstance(e, asyncio.exceptions.TimeoutError):
                    self.statistics._TOdata += 1
                continue
            else:
                self.statistics._ackKO += 1
                break

        except Exception as error:
            # Any other exception 
            error_log_message = f"_send_and_retry - Unexpected Exception - {Function} {_ieee}/0x{_nwkid} 0x{Profile:X} 0x{Cluster:X} payload: {payload} AckIsDisable: {ack_is_disable} RETRY: {attempt}/{max_retry} ({error})"
            self.log.logging("TransportZigpy", "Error", error_log_message)
            result = 0xB6

        else:
            # Success
            handle_transport_result(self, Function, sequence, result, ack_is_disable, _ieee, _nwkid, destination.lqi)
            self.log.logging("TransportZigpy", "Debug", f"_send_and_retry: result: {result}")
            break


async def zigpy_request( self, device: zigpy.device.Device, profile: t.uint16_t, cluster: t.uint16_t, src_ep: t.uint8_t, dst_ep: t.uint8_t, sequence: t.uint8_t, data: bytes, *, ack_is_disable: bool = True, use_ieee: bool = False, extended_timeout: bool = False, ) -> tuple[zigpy.zcl.foundation.Status, str]:
    """Submit and send data out as an unicast transmission."""

    self.log.logging(
        "TransportZigpy", 
        "Debug", 
        f"zigpy_request: "
        f"zigpy_request called with: device={device}, profile={profile}, cluster={cluster}, "
        f"src_ep={src_ep}, dst_ep={dst_ep}, sequence={sequence}, data={data}, "
        f"ack_is_disable={ack_is_disable}, use_ieee={use_ieee}, extended_timeout={extended_timeout}"
    )
    if use_ieee:
        src = t.AddrModeAddress( addr_mode=t.AddrMode.IEEE, address=self.app.state.node_info.ieee )
        dst = t.AddrModeAddress(addr_mode=t.AddrMode.IEEE, address=device.ieee)
    else:
        src = t.AddrModeAddress( addr_mode=t.AddrMode.NWK, address=self.app.state.node_info.nwk )
        dst = t.AddrModeAddress(addr_mode=t.AddrMode.NWK, address=device.nwk)

    if self.app.config[zigpy.config.CONF_SOURCE_ROUTING]:
        source_route = self.app.build_source_route_to(dest=device)
    else:
        source_route = None

    tx_options = t.TransmitOptions.NONE

    if not ack_is_disable:
        tx_options |= t.TransmitOptions.ACK

    await self.app.send_packet(
        t.ZigbeePacket(
            src=src,
            src_ep=src_ep,
            dst=dst,
            dst_ep=dst_ep,
            tsn=sequence,
            profile_id=profile,
            cluster_id=cluster,
            data=t.SerializableBytes(data),
            extended_timeout=extended_timeout,
            source_route=source_route,
            tx_options=tx_options,
        )
    )

    return (zigpy.zcl.foundation.Status.SUCCESS, "")


async def zigpy_mrequest( self, group_id: t.uint16_t, profile: t.uint8_t, cluster: t.uint16_t, src_ep: t.uint8_t, sequence: t.uint8_t, data: bytes, *, hops: int = 0, non_member_radius: int = 3,):
    """Submit and send data out as a multicast transmission."""

    await self.app.send_packet(
        t.ZigbeePacket(
            src=t.AddrModeAddress( addr_mode=t.AddrMode.NWK, address=self.state.node_info.nwk ),
            src_ep=src_ep,
            dst=t.AddrModeAddress(addr_mode=t.AddrMode.Group, address=group_id),
            tsn=sequence,
            profile_id=profile,
            cluster_id=cluster,
            data=t.SerializableBytes(data),
            tx_options=t.TransmitOptions.NONE,
            radius=hops,
            non_member_radius=non_member_radius,
        )
    )

    return (zigpy.zcl.foundation.Status.SUCCESS, "")


async def zigpy_broadcast( self, profile: t.uint16_t, cluster: t.uint16_t, src_ep: t.uint8_t, dst_ep: t.uint8_t, grpid: t.uint16_t, radius: int, sequence: t.uint8_t, data: bytes, broadcast_address: t.BroadcastAddress = t.BroadcastAddress.RX_ON_WHEN_IDLE, ) -> tuple[zigpy.zcl.foundation.Status, str]:
    """Submit and send data out as an unicast transmission."""

    await self.app.send_packet(
        t.ZigbeePacket(
            src=t.AddrModeAddress( addr_mode=t.AddrMode.NWK, address=self.state.node_info.nwk ),
            src_ep=src_ep,
            dst=t.AddrModeAddress( addr_mode=t.AddrMode.Broadcast, address=broadcast_address ),
            dst_ep=dst_ep,
            tsn=sequence,
            profile_id=profile,
            cluster_id=cluster,
            data=t.SerializableBytes(data),
            tx_options=t.TransmitOptions.NONE,
            radius=radius,
        )
    )

    return (zigpy.zcl.foundation.Status.SUCCESS, "")
      
    
async def _retry_or_not(self, attempt, max_retry, Function, sequence,ack_is_disable, _ieee, _nwkid, destination , e):
    if attempt < max_retry:
        # Slow down the throughput when too many commands. Try not to overload the coordinators
        multi = 1.5 if self._currently_waiting_requests_list[_ieee] else 1
        await asyncio.sleep(multi * WAITING_TIME_BETWEEN_ATTEMPTS)
        return True

    # Stop here as we have exceed the max retrys
    result = int(e.status) if hasattr(e, 'status') else 0xB6

    handle_transport_result(self, Function, sequence, result, ack_is_disable, _ieee, _nwkid, destination.lqi)
    return False


def handle_transport_result(self, Function, sequence, result, ack_is_disable, _ieee, _nwkid, lqi):
    self.log.logging("TransportZigpy", "Debug", f"handle_transport_result - {Function} - {_nwkid} - AckIsDisable: {ack_is_disable} Result: {result}")
    if ack_is_disable:
        # As Ack is disable, we cannot conclude that the target device is in trouble.
        # this could be the coordinator itself, or the next hop.
        return
  
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
    ieee = str(destination.ieee)
    nwkid = destination.nwk.serialize()[::-1].hex()

    # Create semaphore if it doesn't exist for the given IEEE
    if ieee not in self._concurrent_requests_semaphores_list:
        self._concurrent_requests_semaphores_list[ieee] = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS_PER_DEVICE)
        self._currently_waiting_requests_list[ieee] = 0

    start_time = time.monotonic()
    was_locked = self._concurrent_requests_semaphores_list[ieee].locked()

    # Log when waiting due to max concurrency
    if was_locked:
        self._currently_waiting_requests_list[ieee] += 1
        self.log.logging("TransportZigpy", "Debug", f"Max concurrency reached for {nwkid}, delaying request {sequence} ({self._currently_waiting_requests_list[ieee]} enqueued)", nwkid)

    try:
        async with self._concurrent_requests_semaphores_list[ieee]:
            # Log when a previously delayed request starts running
            if was_locked:
                elapsed_time = time.monotonic() - start_time
                self.log.logging("TransportZigpy", "Debug", f"Previously delayed request {sequence} is now running, delayed by {elapsed_time:.2f} seconds for {nwkid}", nwkid)
            yield

    finally:
        if was_locked:
            # Decrement the waiting count if a request is processed
            self._currently_waiting_requests_list[ieee] -= 1


def specific_endpoints(self):
    supported_plugins = ["Terncy", "Konke", "Wiser", "Orvibo", "Livolo", "Wiser2"]

    return any(
        plugin in self.pluginconf.pluginConf
        and self.pluginconf.pluginConf[plugin]
        for plugin in supported_plugins
    )
