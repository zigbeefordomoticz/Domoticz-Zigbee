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

"""
workerLoop.py — Writer-queue consumer and command dispatcher.

Pulls JSON-encoded commands from self.writer_queue, parses them, and
dispatches to the appropriate handler.  Special commands that affect
the supervisor lifecycle (RESTART-ZIGPY-STACK, RESET-RADIO-COMMUNICATION)
are also handled here.

Public entry point: worker_loop(self)
"""

import asyncio
import json
import queue
import time

import zigpy.types as t
from zigpy.exceptions import (APIException, ControllerException, DeliveryError,
                               InvalidResponse)
from zigpy_znp.exceptions import (CommandNotRecognized, InvalidCommandResponse,
                                   InvalidFrame)

from Classes.ZigpyTransport.plugin_encoders import build_plugin_8009_frame_content
from Classes.ZigpyTransport.tools import handle_thread_error
from Classes.ZigpyTransport.zigpySend import (log_exception, process_raw_command,
                                               properyly_display_data)


# ---------------------------------------------------------------------------
# Worker loop
# ---------------------------------------------------------------------------

async def worker_loop(self):
    """
    Main worker loop for processing commands from the writer_queue.

    Runs while zigpy_running is True, fetches commands, dispatches them,
    and handles exceptions. Exits on "STOP" command or cancellation.
    """
    self.log.logging("TransportZigpy", "Debug", "worker_loop - ZigyTransport: worker_loop start.")

    try:
        while self.zigpy_running:
            try:
                command_to_send = await get_next_command(self)

                if command_to_send is None:
                    continue

                if command_to_send == "STOP" or not self.zigpy_running:
                    self.log.logging(["TransportZigpy", "StopProcess"], "Debug",
                                     "worker_loop - Shutting down ... exit.")
                    self.zigpy_running = False
                    break

                await process_incoming_command(self, command_to_send)

            except asyncio.CancelledError:
                self.log.logging("TransportZigpy", "Debug", "worker_loop - Task was cancelled.")
                break

            except Exception as e:
                self.log.logging("TransportZigpy", "Error",
                                 f"Unexpected error in worker_loop: {e}")

    finally:
        self.log.logging(["TransportZigpy", "StopProcess"], "Debug",
                         "TransportZigpy - Exiting loop and cleaning up resources.")


async def process_incoming_command(self, command_to_send):
    """
    Parses one JSON command string and dispatches to the appropriate handler.

    Catches and logs known Zigbee exceptions without crashing the loop.
    """
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
        self.log.logging("TransportZigpy", "Error",
                         f"Error while receiving a Plugin command: >{e}<")
        handle_thread_error(self, e, data)


async def get_next_command(self):
    """
    Asynchronously retrieves the next command from the writer_queue.

    Polls at 100 ms intervals when empty; returns None if zigpy_running
    is False or on any unexpected error.
    """
    while True:
        try:
            return self.writer_queue.get_nowait()

        except queue.Empty:
            if not self.zigpy_running:
                return None
            await asyncio.sleep(0.100)

        except Exception as e:
            self.log.logging("TransportZigpy", "Log", f"Error in get_next_command: {e}")
            return None


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------

async def dispatch_command(self, data):
    """
    Dispatches a parsed command dict to the appropriate handler.

    Handles: COORDINATOR-BACKUP, GET-TIME, PERMIT-TO-JOIN, RAW-COMMAND,
    REMOVE-DEVICE, REQ-NWK-STATUS, SET-*, INTERFERENCE-SCAN,
    ZIGPY-TOPOLOGY-SCAN, RESTART-ZIGPY-STACK, RESET-RADIO-COMMUNICATION.
    """
    cmd  = data["cmd"]
    datas = data["datas"]
    delayAfterSent = datas.get("delayAfterSent", 0) if datas else 0

    if cmd == "COORDINATOR-BACKUP":
        await self.app.coordinator_backup()

    elif cmd == "GET-TIME":
        await self.app.get_time_server()

    elif cmd == "PERMIT-TO-JOIN":
        await _permit_to_joint(self, data)

    elif cmd == "RAW-COMMAND":
        self.log.logging("TransportZigpy", "Debug",
                         f"RAW-COMMAND: {properyly_display_data(datas)}")
        await process_raw_command(self, datas, AckIsDisable=data["ACKIsDisable"],
                                  Sqn=data["Sqn"], delayAfterSent=delayAfterSent)

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
        self.manual_interference_scan_task = asyncio.create_task(
            self.app.network_interference_scan(), name="INTERFERENCE-SCAN"
        )

    elif cmd == "ZIGPY-TOPOLOGY-SCAN":
        self.manual_topology_scan_task = asyncio.create_task(
            self.app.start_topology_scan(), name="ZIGPY-TOPOLOGY-SCAN"
        )

    elif cmd == "RESTART-ZIGPY-STACK":
        # Graceful stack restart: exit worker_loop → start_zigpy_task exits →
        # supervisor restarts the full stack.  Does NOT restart the Domoticz plugin.
        self.log.logging("TransportZigpy", "Log",
                         "RESTART-ZIGPY-STACK: graceful stack restart requested")
        self.zigpy_running = False
        self.writer_queue.put_nowait("STOP")

    elif cmd == "RESET-RADIO-COMMUNICATION":
        # Soft reset: disconnect and reconnect the transport layer only.
        # The zigpy stack (network state, device table) is preserved.
        # Falls back to a full stack restart if reconnect fails.
        self.log.logging("TransportZigpy", "Log",
                         "RESET-RADIO-COMMUNICATION: transport reconnect requested")
        if self.app:
            try:
                await asyncio.wait_for(self.app.disconnect(), timeout=10.0)
                await asyncio.sleep(2)
                await asyncio.wait_for(self.app.connect(), timeout=15.0)
                self.log.logging("TransportZigpy", "Status",
                                 "RESET-RADIO-COMMUNICATION: radio communication reset complete")
            except Exception as e:
                self.log.logging("TransportZigpy", "Error",
                                 f"RESET-RADIO-COMMUNICATION failed ({e}) — falling back to full stack restart")
                self.zigpy_running = False
                self.writer_queue.put_nowait("STOP")


# ---------------------------------------------------------------------------
# PERMIT-TO-JOIN helper
# ---------------------------------------------------------------------------

async def _permit_to_joint(self, data):
    """
    Handles the PERMIT-TO-JOIN command to open the network for device joining.

    Sets the permit timer and calls the app's permit method, with special
    handling for deCONZ which uses permit_ncp instead.
    """
    log = self.log
    radiomodule = self._radiomodule
    app = self.app
    permit_to_join_timer = self.permit_to_join_timer

    log.logging("TransportZigpy", "Debug", f"PERMIT-TO-JOIN: {data}")

    duration     = data["datas"]["Duration"]
    target_router = data["datas"]["targetRouter"]
    target_router = None if target_router == "FFFC" else t.EUI64(t.uint64_t(target_router).serialize())
    duration = 0xFE if duration == 0xFF else duration

    permit_to_join_timer["Timer"]    = time.time()
    permit_to_join_timer["Duration"] = duration

    log.logging("TransportZigpy", "Status",
                f"++ opening zigbee network for {duration} secondes on specific router {target_router}")

    if radiomodule == "deCONZ":
        return await app.permit_ncp(time_s=duration)

    log.logging("TransportZigpy", "Debug",
                f"Calling app.permit(time_s={duration}, node={target_router})")
    await app.permit(time_s=duration, node=target_router)
    log.logging("TransportZigpy", "Debug",
                f"Returning from app.permit(time_s={duration}, node={target_router})")
