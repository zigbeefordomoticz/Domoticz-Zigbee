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
zigpySend.py — Zigbee frame transmission and per-device concurrency.

Handles everything from the point a command leaves the worker queue until
the APS ACK/NACK is forwarded back to the plugin:

  process_raw_command        — decode a RAW-COMMAND dict, pick transport type
  send_{broadcast,multicast,unicast}_command — top-level send helpers
  transport_request          — concurrency gate + retry wrapper (decorated)
  _send_and_retry            — retry loop with timeout
  zigpy_request / _mrequest / _broadcast — thin wrappers around app.send_packet
  handle_transport_result    — update reachability + forward APS status
  _limit_concurrency         — asyncio.Semaphore context manager per device
  cleanup_unused_concurrency_state — periodic GC for semaphore dicts
  push_APS_ACK_NACKto_plugin — build and forward 0x8011 frame
  properyly_display_data     — hex-formatting helper for log output
  log_exception              — structured exception logger
  check_transport_readiness  — quick radio-readiness probe
  measure_execution_time     — decorator for transport_request timing
"""

import asyncio
import contextlib
import functools
import time
import traceback

import zigpy.config
import zigpy.device
import zigpy.exceptions
import zigpy.types as t
import zigpy.zcl

from Classes.ZigpyTransport.plugin_encoders import build_plugin_8011_frame_content
from Modules.macPrefix import DELAY_FOR_VERY_KEY

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ERROR_TASK_CREATION_FAILED = 0xB6
SEMAPHORE_TIMEOUT = 240               # seconds to wait for a concurrency slot
REQUEST_TIMEOUT = 8                   # seconds to attempt a unicast send
WAITING_TIME_BETWEEN_REQUESTS = .100  # inter-request pacing
MAX_CONCURRENT_REQUESTS_PER_DEVICE = 1
VERIFY_KEY_DELAY = 6                  # extra delay for verify-key commands


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------

def _get_destination(self, NwkId, addressmode, Profile, Cluster, sEp, dEp, sequence, payload):
    """
    Determines the destination device and transport type for a command.

    Handles broadcast, multicast, and unicast based on address mode and NWK ID.

    Returns:
        tuple: (destination object or int, str transport type) or (None, None) on error.
    """
    if int(NwkId, 16) >= 0xFFFB:
        return int(NwkId, 16), "Broadcast"

    if addressmode == 0x01:
        return int(NwkId, 16), "Multicast"

    if addressmode in (0x02, 0x07):
        # 0x02 Short address / 0x07 Short address with No Ack (Zigate)
        try:
            destination = self.app.get_device(nwk=t.NWK(int(NwkId, 16)))
        except KeyError:
            self.log.logging("TransportZigpy", "Log",
                             f"_get_destination unable to get destination. Nwkid {NwkId} AddrMode {addressmode}")
            destination = None
        return destination, "Unicast"

    if addressmode in (0x03, 0x08):
        # 0x03 IEEE / 0x08 IEEE with No Ack (Zigate)
        return self.app.get_device(nwk=t.NWK(int(NwkId, 16))), "Unicast"

    self.log.logging("TransportZigpy", "Error",
                     f"_get_destination wrong address mode {addressmode} NwkId {NwkId}")
    return None, None


async def process_raw_command(self, data, AckIsDisable=False, Sqn=None, delayAfterSent=0):
    """
    Processes a raw Zigbee command and determines the transmission type.

    Extracts parameters, determines destination and transport type (broadcast,
    multicast, unicast), and calls the appropriate send function.
    """
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
    delay = data.get("Delay", None)

    self.log.logging("TransportZigpy", "Debug",
                     f"process_raw_command: ready to request Function: {Function} NwkId: {NwkId}/{dEp} "
                     f"Cluster: {Cluster} Seq: {sequence} Payload: {payload.hex()} "
                     f"AddrMode: {addressmode} AckIsDisable: {AckIsDisable} Sqn: {Sqn}, "
                     f"Delay: {delay}, delayAfterSent {delayAfterSent}, Extended_TO: {extended_timeout}")

    destination, transport_needs = _get_destination(self, NwkId, addressmode, Profile, Cluster,
                                                    sEp, dEp, sequence, payload)
    if destination is None:
        self.log.logging("TransportZigpy", "Error",
                         f"process_raw_command: unknown destination: {destination}")
        return

    handlers = {
        "Broadcast": lambda: send_broadcast_command(self, Profile, Cluster, sEp, dEp, sequence, payload),
        "Multicast": lambda: send_multicast_command(self, NwkId, Profile, Cluster, sEp, sequence, payload),
        "Unicast":   lambda: send_unicast_command(self, destination, Profile, Cluster, sEp, dEp,
                                                  sequence, payload, AckIsDisable, delay,
                                                  extended_timeout, Function, Sqn, delayAfterSent),
    }

    key = "Multicast" if addressmode == 0x01 else transport_needs
    handler = handlers.get(key)
    if handler is None:
        self.log.logging("TransportZigpy", "Error",
                         f"process_raw_command: unhandled transport '{transport_needs}' addrmode {addressmode}")
        return

    result, msg = await handler()
    self.log.logging("TransportZigpy", "Debug",
                     f"process_raw_command completed: {destination} result={result} msg={msg}")


# ---------------------------------------------------------------------------
# Send helpers
# ---------------------------------------------------------------------------

async def send_broadcast_command(self, Profile, Cluster, sEp, dEp, sequence, payload):
    """Sends a broadcast Zigbee command via app.broadcast."""
    result, msg = await self.app.broadcast(Profile, Cluster, sEp, dEp, 0x0, 0x0, sequence, payload)
    await asyncio.sleep(2 * WAITING_TIME_BETWEEN_REQUESTS)
    return result, msg


async def send_multicast_command(self, NwkId, Profile, Cluster, sEp, sequence, payload):
    """Sends a multicast Zigbee command to a group via app.mrequest."""
    destination = int(NwkId, 16)
    self.log.logging("TransportZigpy", "Debug", f"send_multicast_command Multicast: {destination}")
    result, msg = await self.app.mrequest(destination, Profile, Cluster, sEp, sequence, payload)
    await asyncio.sleep(2 * WAITING_TIME_BETWEEN_REQUESTS)
    return result, msg


async def send_unicast_command(self, destination, Profile, Cluster, sEp, dEp, sequence, payload,
                               AckIsDisable, delay, extended_timeout, Function, Sqn, delayAfterSent):
    """
    Sends a unicast command to a Zigbee device.

    Spawns an asyncio task for transport_request and returns immediately.

    Returns:
        tuple: (0x00, "") on successful task creation, or (ERROR_TASK_CREATION_FAILED, msg).
    """
    payload_hex = payload.hex()[:100] + "..." if len(payload.hex()) > 100 else payload.hex()
    AckIsDisable = False if self.pluginconf.pluginConf["ForceAPSAck"] else AckIsDisable

    self.log.logging("TransportZigpy", "Debug",
                     f"send_unicast_command Unicast destination: {destination} Profile: {Profile} "
                     f"Cluster: {Cluster} sEp: {sEp} dEp: {dEp} Seq: {sequence} Payload: {payload_hex}")

    try:
        task = asyncio.create_task(
            transport_request(self, Function, destination, Profile, Cluster, sEp, dEp, sequence,
                              payload, ack_is_disable=AckIsDisable, use_ieee=False, delay=delay,
                              extended_timeout=extended_timeout, delayAfterSent=delayAfterSent),
            name=f"send_unicast_command-{Function}-{destination}-{Cluster}-{Sqn}"
        )
    except (TypeError, ValueError, RuntimeError) as e:
        self.log.logging("TransportZigpy", "Error", f"Failed to create task: {e}")
        self.statistics._ackKO += 1
        return ERROR_TASK_CREATION_FAILED, str(e)

    task.add_done_callback(_make_unicast_callback(self))
    self.statistics._sent += 1
    return 0x00, ""


def _make_unicast_callback(self):
    """Returns a task-done callback that logs and updates statistics."""
    def callback(task):
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            self.statistics._ackKO += 1
            self.log.logging("TransportZigpy", "Debug", f"Task {task.get_name()} failed: {exc}")
        else:
            self.log.logging("TransportZigpy", "Debug", f"Task {task.get_name()} completed")
    return callback


# ---------------------------------------------------------------------------
# Low-level Zigpy packet submission
# ---------------------------------------------------------------------------

async def zigpy_request(
    self,
    device: zigpy.device.Device,
    profile: t.uint16_t,
    cluster: t.uint16_t,
    src_ep: t.uint8_t,
    dst_ep: t.uint8_t,
    sequence: t.uint8_t,
    data: bytes,
    *,
    ack_is_disable: bool = True,
    use_ieee: bool = False,
    extended_timeout: bool = False,
    priority: bool = t.PacketPriority.NORMAL,
    force_route_discovery: bool = False,
) -> tuple:
    """
    Submits a unicast Zigbee packet via app.send_packet.

    Returns:
        (Status.SUCCESS, "") on success; error tuple on failure.
    """
    self.log.logging(
        "TransportZigpy", "Debug",
        f"zigpy_request called with: device={device}, profile={profile}, cluster={cluster}, "
        f"src_ep={src_ep}, dst_ep={dst_ep}, sequence={sequence}, data={data}, "
        f"ack_is_disable={ack_is_disable}, use_ieee={use_ieee}, extended_timeout={extended_timeout}"
    )
    if self.app is None:
        self.log.logging("TransportZigpy", "Log", "zigpy_request: app is None, cannot send packet")
        return (zigpy.zcl.foundation.Status.DELIVERY_ERROR, "ZCL FAILURE: app is None")

    if use_ieee:
        src = t.AddrModeAddress(addr_mode=t.AddrMode.IEEE, address=self.app.state.node_info.ieee)
        dst = t.AddrModeAddress(addr_mode=t.AddrMode.IEEE, address=device.ieee)
    else:
        src = t.AddrModeAddress(addr_mode=t.AddrMode.NWK, address=self.app.state.node_info.nwk)
        dst = t.AddrModeAddress(addr_mode=t.AddrMode.NWK, address=device.nwk)

    source_route = (
        self.app.build_source_route_to(dest=device)
        if self.app.config[zigpy.config.CONF_SOURCE_ROUTING]
        else None
    )

    tx_options = t.TransmitOptions.NONE

    if not ack_is_disable:
        tx_options |= t.TransmitOptions.ACK

    if force_route_discovery:
        tx_options |= t.TransmitOptions.FORCE_ROUTE_DISCOVERY

    try:
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
    except (AttributeError, asyncio.CancelledError):
        return -1, None

    except asyncio.TimeoutError as e:
        self.log.logging(
            "TransportZigpy", "Debug",
            f"zigpy_request: Timeout while sending packet\n"
            f"  src={src}, src_ep={src_ep}, dst={dst}, dst_ep={dst_ep}, tsn={sequence}\n"
            f"  profile_id={profile}, cluster_id={cluster}, "
            f"data={data.hex() if isinstance(data, (bytes, bytearray)) else data}\n"
            f"  extended_timeout={extended_timeout}, source_route={source_route}, "
            f"tx_options={tx_options}, priority={priority}\n"
            f"  Exception={e}\n  Traceback:\n{traceback.format_exc()}"
        )
        return (asyncio.TimeoutError, f"ZCL FAILURE: {e}")

    except zigpy.exceptions.DeliveryError as e:
        self.log.logging(
            "TransportZigpy", "Debug",
            f"zigpy_request: Error sending packet\n"
            f"  src={src}, src_ep={src_ep}, dst={dst}, dst_ep={dst_ep}, tsn={sequence}\n"
            f"  profile_id={profile}, cluster_id={cluster}, "
            f"data={data.hex() if isinstance(data, (bytes, bytearray)) else data}\n"
            f"  extended_timeout={extended_timeout}, source_route={source_route}, "
            f"tx_options={tx_options}, priority={priority}\n"
            f"  Exception={e}\n  Traceback:\n{traceback.format_exc()}"
        )
        return (zigpy.exceptions.DeliveryError, f"ZCL FAILURE: {e}")

    except Exception as e:
        self.log.logging(
            "TransportZigpy", "Error",
            f"zigpy_request: Error sending packet\n"
            f"  src={src}, src_ep={src_ep}, dst={dst}, dst_ep={dst_ep}, tsn={sequence}\n"
            f"  profile_id={profile}, cluster_id={cluster}, "
            f"data={data.hex() if isinstance(data, (bytes, bytearray)) else data}\n"
            f"  extended_timeout={extended_timeout}, source_route={source_route}, "
            f"tx_options={tx_options}, priority={priority}\n"
            f"  Exception={e}\n  Traceback:\n{traceback.format_exc()}"
        )
        return (zigpy.exceptions.DeliveryError, f"ZCL FAILURE: {e}")

    return (zigpy.zcl.foundation.Status.SUCCESS, "")


async def zigpy_mrequest(
    self,
    group_id: t.uint16_t,
    profile: t.uint8_t,
    cluster: t.uint16_t,
    src_ep: t.uint8_t,
    sequence: t.uint8_t,
    data: bytes,
    *,
    hops: int = 0,
    non_member_radius: int = 3,
) -> tuple:
    """Submits a multicast Zigbee packet to a group."""
    await self.app.send_packet(
        t.ZigbeePacket(
            src=t.AddrModeAddress(addr_mode=t.AddrMode.NWK, address=self.app.state.node_info.nwk),
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


async def zigpy_broadcast(
    self,
    profile: t.uint16_t,
    cluster: t.uint16_t,
    src_ep: t.uint8_t,
    dst_ep: t.uint8_t,
    grpid: t.uint16_t,
    radius: int,
    sequence: t.uint8_t,
    data: bytes,
    broadcast_address: t.BroadcastAddress = t.BroadcastAddress.RX_ON_WHEN_IDLE,
) -> tuple:
    """Submits a broadcast Zigbee packet."""
    await self.app.send_packet(
        t.ZigbeePacket(
            src=t.AddrModeAddress(addr_mode=t.AddrMode.NWK, address=self.app.state.node_info.nwk),
            src_ep=src_ep,
            dst=t.AddrModeAddress(addr_mode=t.AddrMode.Broadcast, address=broadcast_address),
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


# ---------------------------------------------------------------------------
# transport_request — concurrency gate + retry wrapper
# ---------------------------------------------------------------------------

def measure_execution_time(func):
    """Decorator that optionally times and logs transport_request execution."""
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
                t_elapse = round((t_end - t_start) * 1000)

                if hasattr(self, "statistics"):
                    self.statistics.add_timing_zigpy(t_elapse)

                if hasattr(self, "log"):
                    Function = kwargs.get("Function", args[0] if len(args) > 0 else "Unknown")
                    sequence = kwargs.get("sequence", args[6] if len(args) > 6 else "N/A")
                    ack_is_disable = kwargs.get("ack_is_disable", args[7] if len(args) > 7 else False)
                    destination = kwargs.get("destination", args[1] if len(args) > 1 else None)

                    nwk  = getattr(destination.nwk, "hex", lambda: "??")() if destination else "??"
                    ieee = getattr(destination, "ieee", "??")
                    model = getattr(destination, "model", "??")
                    mfr  = getattr(destination, "manufacturer_id", "??")
                    init = getattr(destination, "is_initialized", "??")
                    rssi = getattr(destination, "rssi", "??")
                    lqi  = getattr(destination, "lqi", "??")

                    self.log.logging(
                        "TransportZigpy", "Log",
                        f"| (transport_request) | {t_elapse}ms | {Function} | {sequence} | "
                        f"{ack_is_disable} | {nwk} | {ieee} | {model} | {mfr} | {init} | {rssi} | {lqi} |"
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
    delayAfterSent=0,
):
    """
    Send a Zigbee message using the transport layer.

    Applies an optional pre-send delay, acquires the per-device concurrency
    semaphore, checks reachability, and delegates to _send_and_retry.
    """
    _nwkid = destination.nwk.serialize()[::-1].hex()
    _ieee = str(destination.ieee)

    if not check_transport_readiness(self):
        return None

    if Profile == 0x0000 and Cluster == 0x0005 and _ieee and _ieee[:8] in DELAY_FOR_VERY_KEY:
        self.log.logging("TransportZigpy", "Debug", f"Delaying for key verification for {_ieee}")
        delay = delay or VERIFY_KEY_DELAY

    if delay:
        self.log.logging("TransportZigpy", "Debug", f"transport_request: delay for {delay} seconds")
        await asyncio.sleep(delay)

    async with _limit_concurrency(self, destination, sequence):
        if _ieee in self._currently_not_reachable and self._currently_waiting_requests_list.get(_ieee, 0):
            self.log.logging(
                "TransportZigpy", "Debug",
                f"transport_request: Request {sequence} skipped. Device not reachable: "
                f"NwkId: {_nwkid} IEEE: {_ieee}"
            )
            return None

        result = await _send_and_retry(
            self, Function, destination, Profile, Cluster, _nwkid,
            sEp, dEp, sequence, payload, use_ieee, _ieee,
            ack_is_disable, extended_timeout, delayAfterSent
        )

    await asyncio.sleep(WAITING_TIME_BETWEEN_REQUESTS)
    return result


async def _send_and_retry(
    self, function, destination, profile, cluster,
    nwkid, source_ep, dest_ep, sequence, payload,
    use_ieee, ieee, ack_is_disable, extended_timeout, delay_after_sent
):
    """
    Sends a Zigbee request and optionally retries until REQUEST_TIMEOUT is reached.

    Single send if ack_is_disable is True; retry loop otherwise.
    """
    common_log_info = (
        f"{ieee}/0x{nwkid} 0x{profile:X} 0x{cluster:X} payload: {payload} "
        f"AckIsDisable: {ack_is_disable} extended_timeout: {extended_timeout}"
    )
    # OTA block responses (cluster 0x0019) use LOW priority so the watchdog
    # ping and other control traffic can always preempt them.  This mirrors
    # zigpy's own OTA manager which explicitly wraps image_block_response in
    # request_priority(PacketPriority.LOW) for the same reason.
    # Retries keep LOW priority — never escalate OTA to HIGH.
    is_ota_cluster = (cluster == 0x0019)
    packet_priority = t.PacketPriority.LOW if is_ota_cluster else t.PacketPriority.NORMAL


    async def __try_send(attempt):
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
                priority=packet_priority,
            )
        except asyncio.TimeoutError:
            self.log.logging("TransportZigpy", "Debug",
                             f"Timeout while submitting - {function} {common_log_info} Attempt: {attempt}")
            self.statistics._reTx += 1
            self.statistics._TOdata += 1
            return None  # retry

        except Exception as e:
            self.log.logging("TransportZigpy", "Log",
                             f"Warning while submitting - {function} {common_log_info} "
                             f"Attempt: {attempt} Exception: '{e}' ({type(e).__name__})")
            self.statistics._ackKO += 1
            handle_transport_result(self, function, cluster, sequence, 0xB6,
                                    ack_is_disable, extended_timeout, ieee, nwkid, destination.lqi)
            return 0xB6

        else:
            if result == -1:
                return result

            delay_after_cmd = max(delay_after_sent,
                                  self.pluginconf.pluginConf.get("DelayAfterCommandSent", 0))
            if delay_after_cmd > 0:
                self.log.logging("TransportZigpy", "Debug",
                                 f"sleeping {delay_after_cmd} as per configured!!")
                await asyncio.sleep(delay_after_cmd)

            handle_transport_result(self, function, cluster, sequence, result,
                                    ack_is_disable, extended_timeout, ieee, nwkid, destination.lqi)
            self.log.logging("TransportZigpy", "Debug", f"_send_and_retry: result: {result}")
            return result

    if ack_is_disable:
        return await __try_send(attempt=1)

    start_time = time.monotonic()
    attempt = 0
    while True:
        attempt += 1
        elapsed = time.monotonic() - start_time

        if elapsed >= REQUEST_TIMEOUT:
            self.log.logging("TransportZigpy", "Log",
                             f"_send_and_retry: {common_log_info} TIMEOUT of {REQUEST_TIMEOUT}s "
                             f"reached after {attempt - 1} attempts.")
            self.statistics._ackKO += 1
            handle_transport_result(self, function, cluster, sequence, 0xB6,
                                    ack_is_disable, extended_timeout, ieee, nwkid, destination.lqi)
            return 0xB6

        self.log.logging("TransportZigpy", "Debug",
                         f"_send_and_retry: {function} {common_log_info} "
                         f"extended_timeout: {extended_timeout} Attempt: {attempt} Elapsed: {elapsed:.2f}s")
        result = await __try_send(attempt)

        if result is not None:
            return result

        # Escalate non-OTA retries to HIGH so they recover quickly.
        # OTA retries intentionally stay at LOW to avoid starving other traffic.
        if not is_ota_cluster:
            packet_priority = t.PacketPriority.HIGH


# ---------------------------------------------------------------------------
# Transport result handling
# ---------------------------------------------------------------------------

def handle_transport_result(self, Function, Cluster, sequence, result, ack_is_disable,
                             extended_timeout, _ieee, _nwkid, lqi):
    """
    Update plugin state, forward APS ACK/NACK, and track device reachability.
    """
    if ack_is_disable:
        return

    push_APS_ACK_NACKto_plugin(self, _nwkid, Cluster, sequence, result, lqi)

    if result == 0x00:
        if _ieee in self._currently_not_reachable:
            self._currently_not_reachable.remove(_ieee)
    elif _ieee not in self._currently_not_reachable:
        self._currently_not_reachable.append(_ieee)


def push_APS_ACK_NACKto_plugin(self, nwkid, Cluster, sequence, result, lqi):
    """
    Forwards APS ACK/NACK status to the plugin via forwarder_queue (frame 0x8011).
    """
    self.log.logging("TransportZigpy", "Debug",
                     f"push_APS_ACK_NACK to_plugin - {nwkid} - Result: {result} LQI: {lqi}")
    if nwkid == "0000":
        return

    try:
        if not isinstance(result, int):
            result = int(result.serialize().hex(), 16)
        if result != 0x00:
            self.statistics._APSNck += 1
        else:
            self.statistics._APSAck += 1
    except Exception:
        result = -1
        self.statistics._APSNck += 1

    self.forwarder_queue.put(build_plugin_8011_frame_content(self, nwkid, Cluster, sequence, result, lqi))


# ---------------------------------------------------------------------------
# Per-device concurrency limiting
# ---------------------------------------------------------------------------

@contextlib.asynccontextmanager
async def _limit_concurrency(self, destination, sequence):
    """
    Async context manager that gates concurrent requests to a single device.

    At most MAX_CONCURRENT_REQUESTS_PER_DEVICE requests run simultaneously
    per IEEE address.  A waiting request times out after SEMAPHORE_TIMEOUT
    seconds and is skipped (strict mode — no error returned to caller).
    """
    ieee  = str(destination.ieee)
    nwkid = destination.nwk.serialize()[::-1].hex()

    semaphore = self._concurrent_requests_semaphores_list.setdefault(
        ieee, asyncio.Semaphore(MAX_CONCURRENT_REQUESTS_PER_DEVICE)
    )
    self._currently_waiting_requests_list.setdefault(ieee, 0)

    acquired = False
    queued   = False
    start_time = time.monotonic()

    if semaphore.locked():
        queued = True
        self._currently_waiting_requests_list[ieee] += 1
        self.log.logging(
            "TransportZigpy", "Debug",
            f"Max concurrency reached for {nwkid}, delaying request {sequence} "
            f"({self._currently_waiting_requests_list[ieee]} enqueued)",
            nwkid,
        )

    try:
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=SEMAPHORE_TIMEOUT)
            acquired = True
        except asyncio.TimeoutError:
            self.log.logging("TransportZigpy", "Log",
                             f"Timeout waiting for concurrency slot for {nwkid}, "
                             f"request {sequence} skipped", nwkid)
            return

        if queued:
            elapsed_time = time.monotonic() - start_time
            self.log.logging("TransportZigpy", "Debug",
                             f"Delayed request {sequence} now running after {elapsed_time:.2f}s "
                             f"for {nwkid}", nwkid)
        yield

    finally:
        if acquired:
            semaphore.release()
        if queued:
            self._currently_waiting_requests_list[ieee] = max(
                0, self._currently_waiting_requests_list[ieee] - 1
            )


def cleanup_unused_concurrency_state(self):
    """
    Removes semaphore entries for devices that have no pending or active requests.

    Should be called periodically (e.g. every hour) to prevent unbounded memory growth.
    """
    for ieee in list(self._concurrent_requests_semaphores_list):
        sem     = self._concurrent_requests_semaphores_list[ieee]
        waiting = self._currently_waiting_requests_list.get(ieee, 0)

        if waiting == 0 and sem._value == MAX_CONCURRENT_REQUESTS_PER_DEVICE:
            self.log.logging("TransportZigpy", "Debug",
                             f"cleanup_unused_concurrency_state: removing {ieee}")
            del self._concurrent_requests_semaphores_list[ieee]
            self._currently_waiting_requests_list.pop(ieee, None)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def check_transport_readiness(self):
    """
    Returns True if the radio is ready to accept commands.

    For ZNP, checks that the _znp handle is initialised.
    """
    radiomodule = self._radiomodule
    if radiomodule in {"zigate", "deCONZ", "ezsp", "blz"}:
        return True
    if radiomodule == "znp":
        return self.app._znp is not None
    return False


def properyly_display_data(Datas):
    """
    Formats a command data dict into a readable log string with hex values.
    """
    log = "{"
    for x in Datas:
        value = Datas[x]
        if x in ("Profile", "Cluster", "TargetNwk"):
            if isinstance(value, int):
                value = "%04x" % value
        elif x in ("TargetEp", "SrcEp", "Sqn", "AddressMode"):
            if isinstance(value, int):
                value = "%02x" % value
        log += "'%s' : %s," % (x, value)
    log += "}"
    return log


def log_exception(self, exception, error, cmd, data):
    """
    Logs a Zigbee command exception with full context and stack trace.
    """
    context = {
        "Exception":    str(exception),
        "Message code:": str(error),
        "Stack Trace":  str(traceback.format_exc()),
        "Command":      str(cmd),
        "Data":         properyly_display_data(data),
    }
    self.log.logging(
        "TransportZigpy", "Error",
        "%s / %s: request() Not able to execute the zigpy command: %s data: %s"
        % (exception, error, cmd, properyly_display_data(data)),
        context=context,
    )
