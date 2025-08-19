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
import contextlib
import functools
import json
import queue
import random
import sys
import time
import traceback
from pathlib import Path
from threading import Thread

import zigpy.config
import zigpy.device
import zigpy.types as t
import zigpy.zcl
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

ERROR_TASK_CREATION_FAILED = 0xB6
SEMAPHORE_TIMEOUT = 240  # seconds
REQUEST_TIMEOUT = 8   # This is a given time for the request to be sent
WAITING_TIME_BETWEEN_REQUESTS = 0.0
MAX_CONCURRENT_REQUESTS_PER_DEVICE = 1
VERIFY_KEY_DELAY = 6


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
    self.log.logging("TransportZigpy", "Debug", "start_zigpy_thread - Starting Zigpy thread")

    # Set appropriate event loop policy for Windows compatibility
    if sys.platform == "win32" and (3, 8, 0) <= sys.version_info < (3, 9, 0):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Start the Zigpy thread if it's not already running
    if not hasattr(self, 'zigpy_thread') or not self.zigpy_thread or not self.zigpy_thread.is_alive():
        setup_zigpy_thread(self)
    else:
        self.log.logging("TransportZigpy", "Warning", "start_zigpy_thread - Zigpy thread is already running.")


def setup_zigpy_thread(self):
    """Setup and start the Zigpy thread."""
    self.log.logging("TransportZigpy", "Debug", "setup_zigpy_thread - Initializing Zigpy thread")

    # Create and start a new thread
    self.zigpy_thread = Thread(name=f"ZigpyCom_{self.hardwareid}", target=zigpy_thread_function, args=(self,))
    self.zigpy_thread.daemon = True
    self.zigpy_thread.start()
    self.log.logging("TransportZigpy", "Debug", "setup_zigpy_thread - Zigpy thread started")


def zigpy_thread_function(self):
    """Initialize and run the Zigpy event loop for Zigbee communication."""
    self.log.logging("TransportZigpy", "Log", "zigpyThread starting with a random sleep")

    # Adding a random delay to stagger thread start times
    time.sleep(random.uniform(0.5, 3.5))

    # Create a new event loop for this thread
    zigpy_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(zigpy_loop)

    # Enable debug mode if specified in configuration
    if self.pluginconf.pluginConf.get("EventLoopInstrumentation", False):
        zigpy_loop.set_debug(True)

    self.log.logging("TransportZigpy", "Debug", f"zigpyThread EventLoop: {zigpy_loop}")

    try:
        # Run the Zigpy task asynchronously
        zigpy_loop.run_until_complete(start_zigpy_task(self, channel=0, extended_pan_id=0))

    except asyncio.CancelledError:
        # Handle cancellation gracefully if the loop is stopped externally
        self.log.logging("TransportZigpy", "Warning", "zigpy_thread was cancelled.")

    except RuntimeError as e:
        # Handle cases like "Cannot run the event loop while another loop is running"
        self.log.logging("TransportZigpy", "Error", f"zigpy_thread encountered a runtime error: {e}")

    except Exception as e:
        # Log any errors encountered during execution
        self.log.logging("TransportZigpy", "Error", f"zigpy_thread error when starting: {e}")

    finally:
        # Ensure the event loop is closed
        if not zigpy_loop.is_closed():
            zigpy_loop.close()
            self.log.logging("TransportZigpy", "Log", "Event loop closed successfully in zigpy_thread.")
        else:
            self.log.logging("TransportZigpy", "Log", "Event loop was already closed in zigpy_thread.")
            
        self.log.logging("TransportZigpy", "Log", "++ Zigpy thread stopped. [2/3]")


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

    try:
        await radio_start(self, self.statistics, self.pluginconf, self.use_of_zigpy_persistent_db, self._radiomodule, self._serialPort, set_channel=channel, set_extendedPanId=extended_pan_id),

    except Exception as e:
        self.log.logging("TransportZigpy", "Error", f"start_zigpy_task error in radio_start: {e}")
        
    # Run forever
    self.writer_queue = queue.Queue()  # We MUST use queue and not asyncio.Queue, because it is not compatible with the Domoticz framework

    try:
        await worker_loop(self)

    except asyncio.CancelledError:
        # Handle cancellation gracefully if the loop is stopped externally
        self.log.logging("TransportZigpy", "Error", "start_zigpy_task worker_loop(self) was cancelled.")

    except RuntimeError as e:
        # Handle cases like "Cannot run the event loop while another loop is running"
        self.log.logging("TransportZigpy", "Error", f"start_zigpy_task worker_loop(self) encountered a runtime error: {e}")
        
    except Exception as e:
        # Log any errors encountered during execution
        self.log.logging("TransportZigpy", "Error", f"start_zigpy_task worker_loop(self) error: {e}")

    # We exit the worker_loop, shutdown time
    try:
        self.log.logging("TransportZigpy", "Debug", "Shutting down zigpy thread...")
        if self.app:
            await self.app.shutdown()

    except Exception as e:
        self.log.logging("TransportZigpy", "Error", f"start_zigpy_task shutdown(self) error: {e}")
        self.log.logging("TransportZigpy", "Error", f" {str(traceback.format_exc())}")

        self.log.logging("TransportZigpy", "Log", "Disconnecting communication")
        await self.app.disconnect()

    #await asyncio.gather(task, return_exceptions=False)
    await asyncio.sleep(1)

    await _shutdown_remaining_task(self)

    self.log.logging("TransportZigpy", "Debug", "start_zigpy_task - exiting zigpy thread")


async def _shutdown_remaining_task(self):
    """Cleanup tasks tied to the service's shutdown."""
    # Get all tasks except the current one
    tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
    
    if not tasks:
        self.log.logging("TransportZigpy", "Debug", "No outstanding tasks to cancel")
        return

    # Log the number of tasks being cancelled
    self.log.logging("TransportZigpy", "Debug", f"Cancelling {len(tasks)} outstanding tasks")

    # Cancel all tasks
    for task in tasks:
        if not task.done():  # Only cancel tasks that are not already done
            task.cancel()

    # Wait for tasks to complete or handle exceptions
    try:
        await asyncio.gather(*tasks, return_exceptions=True)

    except asyncio.CancelledError:
        # Ignore CancelledError as it's expected during task cancellation
        pass

    except Exception as e:
        self.log.logging("TransportZigpy", "Error", f"Error during task shutdown: {e}")

    self.log.logging("TransportZigpy", "Debug", "Task cleanup completed")
    

async def radio_start(self, statistics, pluginconf, use_of_zigpy_persistent_db, radiomodule, serialPort, auto_form=False, set_channel=0, set_extendedPanId=0):

    self.log.logging("TransportZigpy", "Debug", "In radio_start %s" %radiomodule)
    config = None

    serial_specifics = self._serialPort_communication_specifics or {}
    
    try:
        if radiomodule == "ezsp":
            import bellows.config as radio_specific_conf

            from Classes.ZigpyTransport.AppBellows import App_bellows as App
            config = ezsp_configuration_setup(self, radio_specific_conf, serialPort, serial_specifics)

        elif radiomodule =="znp":
            import zigpy_znp.config as radio_specific_conf

            from Classes.ZigpyTransport.AppZnp import App_znp as App
            config = znp_configuration_setup(self, radio_specific_conf, serialPort, serial_specifics)

        elif radiomodule =="deCONZ":
            import zigpy_deconz.config as radio_specific_conf

            from Classes.ZigpyTransport.AppDeconz import App_deconz as App
            config = deconz_configuration_setup(self, radio_specific_conf, serialPort, serial_specifics)

        elif radiomodule == "blz":
            radio_specific_conf = {}
            from Classes.ZigpyTransport.AppBlz import App_blz as App
            config = blz_configuration_setup(self, radio_specific_conf, serialPort, serial_specifics)

        else:
            self.log.logging( "TransportZigpy", "Error", "Wrong radiomode: %s" % (radiomodule), )
            return

        self.log.logging("TransportZigpy", "Status", "++ Started radio %s port: %s config %s" %( radiomodule, serialPort, config))

    except Exception as e:
        self.log.logging("TransportZigpy", "Error", "Error while starting Radio: %s on port %s with %s" %( radiomodule, serialPort, e))
        self.log.logging("TransportZigpy", "Error", "%s" %traceback.format_exc())       

    optional_configuration_setup(self, config, radio_specific_conf, set_extendedPanId, set_channel)

    try:
        if radiomodule in ["znp", "deCONZ", "ezsp", "blz"]:
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


def ezsp_configuration_setup(self, bellows_conf, serialPort, serial_specifics):
    """Setup configuration for EZSP radio module."""
    config = {
        zigpy.config.CONF_DEVICE: {
            zigpy.config.CONF_DEVICE_PATH: serialPort,
            zigpy.config.CONF_DEVICE_BAUDRATE: serial_specifics.get("Baudrate", 115200),
            zigpy.config.CONF_DEVICE_FLOW_CONTROL: serial_specifics.get("FlowControl", None)
        },
        zigpy.config.CONF_NWK: {
        },
        bellows_conf.CONF_EZSP_CONFIG: {
        },
        # configure automatic behaviors in the NCP (Network Co-Processor)
        bellows_conf.CONF_EZSP_POLICIES: {
        },
        zigpy.config.CONF_OTA: {
        },
        "handle_unknown_devices": True,
    }

    if self.pluginconf.pluginConf.get("EzspAllowUnsecuredRejoins"):
        self.log.logging( "TransportZigpy", "Status", "++ Allow Unsecure Rejoins for Aqara devices ...")
        # “If a device tries to rejoin without a secure link key, still let it in.”
        config[bellows_conf.CONF_EZSP_POLICIES]["TRUST_CENTER_POLICY"] = 0x0003   # ALLOW_UNSECURED_REJOINS|ALLOW_JOINS
          
    if self.pluginconf.pluginConf.get("BellowsNoMoreEndDeviceChildren"):
        self.log.logging("TransportZigpy", "Status", "++ Set The maximum number of end device children that Coordinater will support to 0")
        config[bellows_conf.CONF_EZSP_CONFIG]["CONFIG_MAX_END_DEVICE_CHILDREN"] = 0

    if self.pluginconf.pluginConf.get("TXpower_set"):
        self.log.logging("TransportZigpy", "Status", "++ Enables boost power mode and the alternate transmitter output.")
        config[bellows_conf.CONF_EZSP_CONFIG]["CONFIG_TX_POWER_MODE"] = 0x3

    return config


def znp_configuration_setup(self, znp_conf, serialPort, serial_specifics):
    """Setup configuration for ZNP radio module."""
    config = {
        zigpy.config.CONF_DEVICE: {
            zigpy.config.CONF_DEVICE_PATH: serialPort,
            zigpy.config.CONF_DEVICE_BAUDRATE: serial_specifics.get("Baudrate", 115200),
            zigpy.config.CONF_DEVICE_FLOW_CONTROL: serial_specifics.get("FlowControl", None)
        },
        zigpy.config.CONF_NWK: {
        },
        znp_conf.CONF_ZNP_CONFIG: {
        },
        zigpy.config.CONF_OTA: {
        },
    }
    if specific_endpoints(self):
        config[ znp_conf.CONF_ZNP_CONFIG][ "prefer_endpoint_1" ] = False
    
    if "TXpower_set" in self.pluginconf.pluginConf:
        config[znp_conf.CONF_ZNP_CONFIG]["tx_power"] = int(self.pluginconf.pluginConf["TXpower_set"])
        
    return config


def deconz_configuration_setup(self, deconz_conf, serialPort, serial_specifics):
    """Setup configuration for deCONZ radio module."""
    return {
        zigpy.config.CONF_DEVICE: {
            zigpy.config.CONF_DEVICE_PATH: serialPort, 
            zigpy.config.CONF_DEVICE_BAUDRATE: serial_specifics.get("Baudrate", 115200),
            zigpy.config.CONF_DEVICE_FLOW_CONTROL: serial_specifics.get("FlowControl", None)
        },
        zigpy.config.CONF_NWK: {
        },
        zigpy.config.CONF_OTA: {
        },
    }


def blz_configuration_setup(self, blz_conf, serialPort, serial_specifics):
    """Setup configuration for deCONZ radio module."""
    return {
        zigpy.config.CONF_DEVICE: {
            zigpy.config.CONF_DEVICE_PATH: serialPort, 
            zigpy.config.CONF_DEVICE_BAUDRATE: serial_specifics.get("Baudrate", 2000000),
            zigpy.config.CONF_DEVICE_FLOW_CONTROL: serial_specifics.get("FlowControl", None)
        },
        zigpy.config.CONF_NWK: {
        },
        zigpy.config.CONF_OTA: {
        },
    }


def optional_configuration_setup(self, config, radio_conf, set_extendedPanId, set_channel):

    # In case we have to set the Extended PAN Id
    if set_extendedPanId != 0:
        config[zigpy.config.CONF_NWK][zigpy.config.CONF_NWK_EXTENDED_PAN_ID] = "%s" % ( t.EUI64(t.uint64_t(set_extendedPanId).serialize()) )

    # In case we have to force the Channel
    if radio_conf and set_channel != 0:
        config[zigpy.config.CONF_NWK][zigpy.config.CONF_NWK_CHANNEL] = set_channel

    # Enable or not Source Routing based on zigpySourceRouting setting
    config[zigpy.config.CONF_SOURCE_ROUTING] = bool( self.pluginconf.pluginConf["zigpySourceRouting"] )
    
    # Disable Zigpy OTA
    config[zigpy.config.CONF_OTA][zigpy.config.CONF_OTA_ENABLED] = False
    
    # Disable zigpy conf topo scan by default
    config[zigpy.config.CONF_TOPO_SCAN_ENABLED] = False

    # Enable Zigpy Watchdog by default
    config[zigpy.config.CONF_WATCHDOG_ENABLED] = True
    
    # Config Zigpy db. if not defined, there is no persistent Db.
    if self.pluginconf.pluginConf.get("enableZigpyPersistentInFile"):
        data_folder = Path( self.pluginconf.pluginConf["pluginData"] )
        config[zigpy.config.CONF_DATABASE] = str(data_folder / ("zigpy_persistent_%02d.db"% self.hardwareid) )
        config[zigpy.config.CONF_TOPO_SCAN_ENABLED] = True
        config[zigpy.config.CONF_TOPO_SCAN_PERIOD] = 12 * 60  # 12 Hours

    elif self.pluginconf.pluginConf.get("enableZigpyPersistentInMemory"):
        config[zigpy.config.CONF_DATABASE] = ":memory:"
        config[zigpy.config.CONF_TOPO_SCAN_ENABLED] = True
        config[zigpy.config.CONF_TOPO_SCAN_PERIOD] = 12 * 60  # 12 Hours

    # Manage coordinator auto backup
    if self.pluginconf.pluginConf.get("autoBackup"):
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
    self.log.logging( "TransportZigpy", "Status", f"  PAN ID:                0x{self.app.state.network_info.pan_id:04X}")
    self.log.logging( "TransportZigpy", "Status", f"  Extended PAN ID:       {self.app.state.network_info.extended_pan_id}")
    self.log.logging( "TransportZigpy", "Status", f"  Channel:               {self.app.state.network_info.channel}")
    self.log.logging( "TransportZigpy", "Status", f"  Channel mask:          {list(self.app.state.network_info.channel_mask)}")
    self.log.logging( "TransportZigpy", "Status", f"  NWK update ID:         {self.app.state.network_info.nwk_update_id}")
    self.log.logging( "TransportZigpy", "Status", f"  Device IEEE:           {self.app.state.node_info.ieee}")
    self.log.logging( "TransportZigpy", "Status", f"  Device NWK:            0x{self.app.state.node_info.nwk:04X}")
    self.log.logging( "TransportZigpy", "Status", "  Network key:           " + ":".join( f"{c:02x}" for c in self.app.state.network_information.network_key.key ))
    self.log.logging( "TransportZigpy", "Status", f"  Network key sequence:  {self.app.state.network_info.network_key.seq}")
    self.log.logging( "TransportZigpy", "Status", f"  Network key counter:   {self.app.state.network_info.network_key.tx_counter}")


async def worker_loop(self):
    self.log.logging("TransportZigpy", "Debug", "worker_loop - ZigyTransport: worker_loop start.")

    try:
        while self.zigpy_running:
            try:
                # Fetch the next command to process, waits if queue is empty
                command_to_send = await get_next_command(self)

                # Break the loop if no command was retrieved due to an error
                if command_to_send is None:
                    continue

                # Handle the stop command and exit the loop gracefully
                if command_to_send == "STOP":
                    self.log.logging("TransportZigpy", "Debug", "worker_loop - Shutting down ... exit.")
                    self.zigpy_running = False
                    break

                # Process the received command
                await process_incoming_command(self, command_to_send)

            except asyncio.CancelledError:
                # Gracefully handle cancellation
                self.log.logging("TransportZigpy", "Debug", "worker_loop - Task was cancelled.")
                break

            except Exception as e:
                # Log unexpected exceptions but continue processing other commands
                self.log.logging("TransportZigpy", "Error", f"Unexpected error in worker_loop: {e}")

    finally:
        # Final cleanup if needed
        self.log.logging("TransportZigpy", "Debug", "worker_loop - Exiting loop and cleaning up resources.")


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
    delayAfterSent = datas.get("delayAfterSent", 0) if datas else 0

    if cmd == "COORDINATOR-BACKUP":
        await self.app.coordinator_backup()

    elif cmd == "GET-TIME":
        await self.app.get_time_server()

    elif cmd == "PERMIT-TO-JOIN":
        await _permit_to_joint(self, data)

    elif cmd == "RAW-COMMAND":
        self.log.logging("TransportZigpy", "Debug", f"RAW-COMMAND: {properyly_display_data(datas)}")
        await process_raw_command(self, datas, AckIsDisable=data["ACKIsDisable"], Sqn=data["Sqn"], delayAfterSent=delayAfterSent)

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


async def process_raw_command(self, data, AckIsDisable=False, Sqn=None, delayAfterSent=0):
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
    extended_timeout = False if AckIsDisable else data.get("RxOnIdle", False)
    delayAfterSent= delayAfterSent
    delay = data.get("Delay", None)

    self.log.logging("TransportZigpy", "Debug", f"process_raw_command: process_raw_command ready to request Function: {Function} NwkId: {NwkId}/{dEp} Cluster: {Cluster} Seq: {sequence} Payload: {payload.hex()} AddrMode: {addressmode} AckIsDisable: {AckIsDisable} Sqn: {Sqn}, Delay: {delay}, delayAfterSent {delayAfterSent}, Extended_TO: {extended_timeout}")

    destination, transport_needs = _get_destination(self, NwkId, addressmode, Profile, Cluster, sEp, dEp, sequence, payload)

    if destination is None:
        return

    if transport_needs == "Broadcast":
        self.log.logging("TransportZigpy", "Debug", f"process_raw_command Broadcast: {NwkId}")
        result, msg = await _broadcast_command(self, Profile, Cluster, sEp, dEp, sequence, payload)

    elif addressmode == 0x01:
        result, msg = await _multicast_command(self, NwkId, Profile, Cluster, sEp, sequence, payload)

    elif transport_needs == "Unicast":
        result, msg = await _unicast_command(self, destination, Profile, Cluster, sEp, dEp, sequence, payload, AckIsDisable, delay, extended_timeout, Function, Sqn, delayAfterSent)

    self.log.logging("TransportZigpy", "Debug", f"ZigyTransport: process_raw_command completed NwkId: {destination} result: {result} msg: {msg}")


async def _broadcast_command(self, Profile, Cluster, sEp, dEp, sequence, payload):
    result, msg = await self.app.broadcast(Profile, Cluster, sEp, dEp, 0x0, 0x0, sequence, payload)
    await asyncio.sleep(2 * WAITING_TIME_BETWEEN_REQUESTS)
    return result, msg


async def _multicast_command(self, NwkId, Profile, Cluster, sEp, sequence, payload):
    destination = int(NwkId, 16)
    self.log.logging("TransportZigpy", "Debug", f"process_raw_command Multicast: {destination}")
    result, msg = await self.app.mrequest(destination, Profile, Cluster, sEp, sequence, payload)
    await asyncio.sleep(2 * WAITING_TIME_BETWEEN_REQUESTS)
    return result, msg


async def _unicast_command(self, destination, Profile, Cluster, sEp, dEp, sequence, payload, AckIsDisable, delay, extended_timeout, Function, Sqn, delayAfterSent):
    """
    Sends a unicast command to a Zigbee device.

    Args:
        destination (str): The destination address of the Zigbee device.
        Profile (int): The Zigbee profile ID.
        Cluster (int): The Zigbee cluster ID.
        sEp (int): Source endpoint.
        dEp (int): Destination endpoint.
        sequence (int): Sequence number for the command.
        payload (bytes): The command payload.
        AckIsDisable (bool): Whether to disable APS acknowledgments.
        delay (float): Delay before sending the command.
        extended_timeout (float): Timeout for the task.
        Function (str): Function identifier for the command.
        Sqn (int): Sequence number for task naming.
        delayAfterSent (float): Delay after sending the command.

    Returns:
        tuple: (result, error_msg)
            - result (int): Status code (0x00 for success, error code for failure).
            - error_msg (str): Error message if the task creation fails.
    """

    payload_hex = payload.hex()[:100] + "..." if len(payload.hex()) > 100 else payload.hex()
    self.log.logging("TransportZigpy", "Debug", f"process_raw_command Unicast destination: {destination} Profile: {Profile} Cluster: {Cluster} sEp: {sEp} dEp: {dEp} Seq: {sequence} Payload: {payload_hex}")

    AckIsDisable = False if self.pluginconf.pluginConf["ForceAPSAck"] else AckIsDisable

    try:
        task = asyncio.create_task(
            transport_request(self, Function, destination, Profile, Cluster, sEp, dEp, sequence, payload, ack_is_disable=AckIsDisable, use_ieee=False, delay=delay, extended_timeout=extended_timeout, delayAfterSent=delayAfterSent),
            name=f"_unicast_command-{Function}-{destination}-{Cluster}-{Sqn}"
        )

        # Add callback to log task completion
        def task_done_callback(task):
            async def async_callback():
                async with asyncio.Lock():  # Now valid in async context
                    if task.exception():
                        self.log.logging("TransportZigpy", "Debug", f"_unicast_command - Task {task.get_name()} failed with exception: {task.exception()}")
                        self.statistics._ackKO += 1
                    else:
                        self.log.logging("TransportZigpy", "Debug", f"_unicast_command - Task {task.get_name()} completed successfully")

            # Schedule the async callback in the event loop
            asyncio.create_task(async_callback())

        task.add_done_callback(task_done_callback)

    except (TypeError, ValueError, RuntimeError) as e:
        self.log.logging("TransportZigpy", "Error", f"process_raw_command: Error creating task: {e}\n{traceback.format_exc()}")
        async with asyncio.Lock():
            self.statistics._ackKO += 1
        return ERROR_TASK_CREATION_FAILED, str(e)

    async with asyncio.Lock():
        self.statistics._sent += 1

    return 0x00, ""


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


def push_APS_ACK_NACKto_plugin(self, nwkid, Cluster, sequence, result, lqi):
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
    self.forwarder_queue.put(build_plugin_8011_frame_content(self, nwkid, Cluster, sequence, result, lqi))


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
    if radiomodule in {"zigate", "deCONZ", "ezsp", "blz"}:
        return True

    if radiomodule == "znp":
        app = self.app
        return app._znp is not None

    return False


def measure_execution_time(func):
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        t_start = None
        if getattr(self, "pluginconf", None) and self.pluginconf.pluginConf.get("ZigpyReactTime", False):
            t_start = time.time()

        try:
            result = await func(self, *args, **kwargs)
            return result
        finally:
            if t_start:
                t_end = time.time()
                t_elapse = round((t_end - t_start) * 1000)  # milliseconds

                if hasattr(self, "statistics"):
                    self.statistics.add_timing_zigpy(t_elapse)

                if hasattr(self, "log"):
                    # Safely extract info from known kwargs or fallback
                    Function = kwargs.get("Function", args[0] if len(args) > 0 else "Unknown")
                    sequence = kwargs.get("sequence", args[6] if len(args) > 6 else "N/A")
                    ack_is_disable = kwargs.get("ack_is_disable", args[7] if len(args) > 7 else False)
                    destination = kwargs.get("destination", args[1] if len(args) > 1 else None)

                    nwk = getattr(destination.nwk, "hex", lambda: "??")() if destination else "??"
                    ieee = getattr(destination, "ieee", "??")
                    model = getattr(destination, "model", "??")
                    mfr = getattr(destination, "manufacturer_id", "??")
                    init = getattr(destination, "is_initialized", "??")
                    rssi = getattr(destination, "rssi", "??")
                    lqi = getattr(destination, "lqi", "??")

                    self.log.logging(
                        "TransportZigpy", "Log",
                        f"| (transport_request) | {t_elapse}ms | {Function} | {sequence} | {ack_is_disable} | {nwk} | {ieee} | {model} | {mfr} | {init} | {rssi} | {lqi} |"
                    )
    return wrapper


@measure_execution_time
async def transport_request(
    self,
    Function,
    destination,
    Profile,
    Cluster,
    sEp,
    dEp,
    sequence,
    payload,
    ack_is_disable=False,
    use_ieee=False,
    delay=None,
    extended_timeout=False,
    delayAfterSent=0
):
    """
    Send a Zigbee message using the transport layer.

    Args:
        Function (str): Operation name for logging and stats.
        destination: Zigpy device object (must have `nwk` and `ieee` attributes).
        Profile (int): Zigbee Profile ID (e.g., 0x0000 or 0x0104).
        Cluster (int): Zigbee Cluster ID.
        sEp (int): Source endpoint.
        dEp (int): Destination endpoint.
        sequence (int): Transaction sequence number.
        payload (bytes): Zigbee payload data.
        ack_is_disable (bool, optional): If True, disables waiting for ACK. Defaults to False.
        use_ieee (bool, optional): If True, uses IEEE addressing. Defaults to False.
        delay (float, optional): Optional delay (in seconds) before sending. Defaults to None.
        extended_timeout (bool, optional): Enables extended timeout. Defaults to False.
        delayAfterSent (float, optional): Delay after sending the request. Defaults to 0.

    Returns:
        int | None: Zigbee transmission result code (e.g., 0x00 for success, 0xB6 for error), or None if skipped.
    """

    _nwkid = destination.nwk.serialize()[::-1].hex()
    _ieee = str(destination.ieee)

    if not check_transport_readiness(self):
        return None

    # Optional delay for specific devices (e.g., CASA.IA)
    if Profile == 0x0000 and Cluster == 0x0005 and _ieee and _ieee[:8] in DELAY_FOR_VERY_KEY:
        self.log.logging("TransportZigpy", "Debug", f"Delaying for key verification for {_ieee}")
        delay = delay or VERIFY_KEY_DELAY  # Let VERIFY_KEY_DELAY be something like 1.0 instead of 6.0 if desired

    if delay:
        self.log.logging("TransportZigpy", "Debug", f"transport_request: delay for {delay} seconds")
        await asyncio.sleep(delay)

    async with _limit_concurrency(self, destination, sequence):
        if _ieee in self._currently_not_reachable and self._currently_waiting_requests_list.get(_ieee, 0):
            self.log.logging(
                "TransportZigpy", "Debug",
                f"transport_request: Request {sequence} skipped. Device not reachable: NwkId: {_nwkid} IEEE: {_ieee}"
            )
            return None

        result = await _send_and_retry(
            self,
            Function,
            destination,
            Profile,
            Cluster,
            _nwkid,
            sEp,
            dEp,
            sequence,
            payload,
            use_ieee,
            _ieee,
            ack_is_disable,
            extended_timeout,
            delayAfterSent
        )

    await asyncio.sleep(WAITING_TIME_BETWEEN_REQUESTS)
    return result


async def _send_and_retry(
    self, function, destination, profile, cluster,
    nwkid, source_ep, dest_ep, sequence, payload,
    use_ieee, ieee, ack_is_disable, extended_timeout, delay_after_sent
):
    """
    Sends a Zigbee request and optionally retries the operation until a timeout is reached.

    If `ack_is_disable` is False, the function attempts to send the request only once.
    If `ack_is_disable` is True, the function retries the request until either a valid response
    is received or `REQUEST_TIMEOUT` is exceeded.

    Parameters:
        function (str): Description of the operation being performed (used for logging).
        destination: Zigbee destination object.
        profile (int): Zigbee profile ID.
        cluster (int): Zigbee cluster ID.
        nwkid (int): Network address of the destination.
        source_ep (int): Source endpoint.
        dest_ep (int): Destination endpoint.
        sequence (int): Sequence number for the request.
        payload (bytes): Payload to send.
        use_ieee (bool): Whether to address the device using IEEE address.
        ieee (str): IEEE address of the device (used for logging).
        ack_is_disable (bool): If True, ACK is disabled and retry logic is enabled.
        extended_timeout (bool): Whether to use an extended timeout for the Zigbee request.
        delay_after_sent (float): Optional delay after a successful transmission.

    Returns:
        int: The Zigbee result code (e.g., 0x00 for success, 0xB6 for timeout or fatal error).
    """
    common_log_info = f"{ieee}/0x{nwkid} 0x{profile:X} 0x{cluster:X} payload: {payload} AckIsDisable: {ack_is_disable} extended_timeout: {extended_timeout}"
    packet_priority = t.PacketPriority.NORMAL

    async def __try_send(attempt):
        """
        Sends a Zigbee request and handles exceptions.

        Returns:
            int | None: Result code if successful or handled exception; None if retry is needed.
        """
        self.log.logging("TransportZigpy", "Debug",
                         f"_send_and_retry: {function} {common_log_info} "
                         f"extended_timeout: {extended_timeout} Attempt: {attempt}")

        try:
            result, _ = await zigpy_request(
                self, destination, profile, cluster,
                source_ep, dest_ep, sequence, payload,
                ack_is_disable=ack_is_disable,
                use_ieee=use_ieee,
                extended_timeout=extended_timeout,
                priority=packet_priority
            )

        except asyncio.TimeoutError:
            msg = f"Timeout while submitting - {function} {common_log_info} Attempt: {attempt}"
            self.log.logging("TransportZigpy", "Debug", msg)
            self.statistics._reTx += 1
            self.statistics._TOdata += 1

            # Let's retry and so return None
            return None

        except Exception as e:
            msg = f"Warning while submitting - {function} {common_log_info} Attempt: {attempt} Exception: '{e}' ({type(e).__name__})"
            self.log.logging("TransportZigpy", "Log", msg)
            self.statistics._ackKO += 1

            # No retry, return 0xB6
            handle_transport_result(self, function, cluster, sequence, 0xB6, ack_is_disable, extended_timeout, ieee, nwkid, destination.lqi)
            return 0xB6

        else:
            delay_after_cmd = max(delay_after_sent, self.pluginconf.pluginConf.get("DelayAfterCommandSent", 0))
            if delay_after_cmd > 0:
                self.log.logging("TransportZigpy", "Debug", f"sleeping {delay_after_cmd} as per configured!!")
                await asyncio.sleep(delay_after_cmd)

            # Successful transmission
            handle_transport_result(self, function, cluster, sequence, result, ack_is_disable, extended_timeout, ieee, nwkid, destination.lqi)
            self.log.logging("TransportZigpy", "Debug", f"_send_and_retry: result: {result}")
            return result
   
    if ack_is_disable:
        # Single send, no retry
        return await __try_send(attempt=1)

    # Retry mode for ack_is_disable == False
    start_time = time.monotonic()
    attempt = 0

    while True:
        attempt += 1
        elapsed = time.monotonic() - start_time

        # Check if we have reached the maximum number of attempts
        if elapsed >= REQUEST_TIMEOUT:
            self.log.logging("TransportZigpy", "Log", f"_send_and_retry: {common_log_info} Prio {packet_priority} TIMEOUT of {REQUEST_TIMEOUT}s reached after {attempt - 1} attempts. ")
            self.statistics._ackKO += 1
            handle_transport_result(self, function, cluster, sequence, 0xB6, ack_is_disable, extended_timeout, ieee, nwkid, destination.lqi)
            return 0xB6

        # If we have already attempted, we use extended timeout
        if attempt > 1:
            extended_timeout = True
            packet_priority = t.PacketPriority.HIGH  # escalate on retry
            self.statistics._reTx += 1
        
        self.log.logging("TransportZigpy", "Log",
                         f"_send_and_retry: {function} {common_log_info} "
                         f"extended_timeout: {extended_timeout} Priority: {packet_priority} Attempt: {attempt} Elapsed: {elapsed:.2f}s")
        result = await __try_send(attempt)
        ok = result == zigpy.zcl.foundation.Status.SUCCESS

        if ok:
            # We exit the loop if the result is successful
            self.log.logging("TransportZigpy", "Log", f"_send_and_retry: {function} - {result}- Attempt: {attempt} Elapsed: {elapsed:.2f}s")
            return result
        
        self.log.logging("TransportZigpy", "Log",
                         f"_send_and_retry: {function} {common_log_info} "
                         f"extended_timeout: {extended_timeout} Attempt: {attempt} Elapsed: {elapsed:.2f}s")

        await asyncio.sleep(min(max(0.1 * (2 ** (attempt - 1)), 0.1), 1.0))  # Exponential backoff with a cap at 1 second


async def zigpy_request( self, device: zigpy.device.Device, profile: t.uint16_t, cluster: t.uint16_t, src_ep: t.uint8_t, dst_ep: t.uint8_t, sequence: t.uint8_t, data: bytes, *, ack_is_disable: bool = True, use_ieee: bool = False, extended_timeout: bool = False, priority: bool = t.PacketPriority.NORMAL) -> tuple[zigpy.zcl.foundation.Status, str]:
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
            priority=priority,
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


def handle_transport_result(self, Function, Cluster, sequence, result, ack_is_disable, extended_timeout, _ieee, _nwkid, lqi):
    """
    Handle the result of a Zigbee transport operation by updating plugin state,
    acknowledging APS delivery status, and tracking device reachability.

    Args:
        Function: Zigbee command/function used.
        Cluster: Zigbee cluster involved in the request.
        sequence: Sequence number of the request.
        result (int): APS ACK/NACK result (0x00 = success).
        ack_is_disable (bool): True if APS ACK was disabled in request.
        extended_timeout (bool): True if extended timeout was used.
        _ieee (str): IEEE address of the target device.
        _nwkid (str): Network ID (NWK address) of the device.
        lqi (int): Link Quality Indicator of the received response.
    """

    if ack_is_disable:
        # Cannot conclude reachability when ACK is disabled
        return

    push_APS_ACK_NACKto_plugin(self, _nwkid, Cluster, sequence, result, lqi)

    if result == 0x00:
        # Device successfully responded, remove from not reachable list
        if _ieee in self._currently_not_reachable:
            self._currently_not_reachable.remove(_ieee)

    elif _ieee not in self._currently_not_reachable:
        self._currently_not_reachable.append(_ieee)


@contextlib.asynccontextmanager
async def _limit_concurrency(self, destination, sequence):
    """
    Async context manager to limit concurrent requests to a specific Zigbee device.

    This method uses a per-device asyncio.Semaphore to ensure that no more than a fixed number
    of concurrent operations are issued to a single device at once. If the semaphore is locked,
    the request is queued and logged. A timeout is enforced to prevent indefinite blocking.

    Parameters
    ----------
    destination : zigpy.device.Device
        The target Zigbee device for which concurrency is being managed.
    sequence : int or str
        An identifier for the request, used for logging/debugging.

    Yields
    ------
    None
        Code inside the `async with` block executes once a concurrency slot is available.
        If the semaphore acquisition times out, the block still runs, but with a warning logged.

    Raises
    ------
    asyncio.TimeoutError
        Logged (but not raised) if semaphore acquisition exceeds the configured timeout.
        The caller must handle timeout behavior after the `yield` if needed.

    Notes
    -----
    - MAX_CONCURRENT_REQUESTS_PER_DEVICE defines the per-device concurrency limit.
    - SEMAPHORE_TIMEOUT defines the maximum wait time before logging a timeout warning.
    - Uses self._concurrent_requests_semaphores_list and self._currently_waiting_requests_list
      to track semaphores and pending requests by IEEE address.
    """
    ieee = str(destination.ieee)
    nwkid = destination.nwk.serialize()[::-1].hex()

    # Safely initialize semaphore and waiting counter
    if ieee not in self._concurrent_requests_semaphores_list:
        self._concurrent_requests_semaphores_list[ieee] = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS_PER_DEVICE)
    self._currently_waiting_requests_list.setdefault(ieee, 0)

    semaphore = self._concurrent_requests_semaphores_list[ieee]
    start_time = time.monotonic()
    was_locked = semaphore.locked()

    if was_locked:
        self._currently_waiting_requests_list[ieee] += 1
        self.log.logging("TransportZigpy", "Debug", f"Max concurrency reached for {nwkid}, delaying request {sequence} ({self._currently_waiting_requests_list[ieee]} enqueued)", nwkid)

    try:
        # Wait for semaphore with timeout
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=SEMAPHORE_TIMEOUT)
        except asyncio.TimeoutError:
            self.log.logging("TransportZigpy", "Warning", f"Timeout waiting for concurrency slot for {nwkid}, request {sequence} dropped", nwkid)
            yield  # Allow graceful fallback or logging outside
            return

        # Delayed request is now running
        if was_locked:
            elapsed_time = time.monotonic() - start_time
            self.log.logging("TransportZigpy", "Debug", f"Previously delayed request {sequence} is now running, delayed by {elapsed_time:.2f} seconds for {nwkid}", nwkid)

        yield

    finally:
        if semaphore.locked():
            semaphore.release()

        if was_locked:
            self._currently_waiting_requests_list[ieee] -= 1
            
        # Opportunistic cleanup
        #if ( self._currently_waiting_requests_list.get(ieee, 0) == 0 and self._concurrent_requests_semaphores_list[ieee]._value == MAX_CONCURRENT_REQUESTS_PER_DEVICE ):
        #    del self._concurrent_requests_semaphores_list[ieee]
        #    self._currently_waiting_requests_list.pop(ieee, None)


def _cleanup_unused_concurrency_state(self):
    """
    Cleans up semaphore and waiting state for inactive devices.

    This method iterates through all per-device semaphores and removes entries
    that are no longer in use. A device's concurrency state is considered unused if:
    - No requests are currently waiting (i.e., waiting count == 0)
    - All semaphore slots are released (i.e., the semaphore is not acquired by any task)

    This helps prevent unbounded memory growth when many devices are seen temporarily.

    Notes
    -----
    - This method should be called periodically (e.g., every hour) or during idle time.
    - Safe to call while other coroutines are active.
    """
    for ieee in list(self._concurrent_requests_semaphores_list):
        sem = self._concurrent_requests_semaphores_list[ieee]
        waiting = self._currently_waiting_requests_list.get(ieee, 0)

        # Only clean up if no one is waiting and all slots are released
        if waiting == 0 and sem._value == MAX_CONCURRENT_REQUESTS_PER_DEVICE:
            self.log.logging("TransportZigpy", "Debug", f"_cleanup_unused_concurrency_state {ieee} from concurrency_state", )
            
            del self._concurrent_requests_semaphores_list[ieee]
            self._currently_waiting_requests_list.pop(ieee, None)
            

def specific_endpoints(self):
    supported_plugins = ["Terncy", "Konke", "Wiser", "Orvibo", "Livolo", "Wiser2"]

    return any(
        plugin in self.pluginconf.pluginConf
        and self.pluginconf.pluginConf[plugin]
        for plugin in supported_plugins
    )
