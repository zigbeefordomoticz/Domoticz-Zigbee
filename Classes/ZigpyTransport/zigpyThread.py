import asyncio
import binascii
import json
import logging
import queue
import time
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
    build_plugin_8009_frame_content, build_plugin_8011_frame_content)
from Classes.ZigpyTransport.tools import handle_thread_error
from zigpy.exceptions import DeliveryError, InvalidResponse
from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)
from zigpy_znp.exceptions import CommandNotRecognized, InvalidFrame


def start_zigpy_thread(self):
    self.log.logging("TransportWrter", "Debug", "start_zigpy_thread - Starting zigpy thread")
    self.zigpy_thread.start()


def stop_zigpy_thread(self):
    self.log.logging("TransportWrter", "Debug", "stop_zigpy_thread - Stopping zigpy thread")
    self.writer_queue.put((0, "STOP"))
    self.zigpy_running = False


def zigpy_thread(self):
    self.log.logging("TransportWrter", "Debug", "zigpy_thread - Starting zigpy thread")
    self.zigpy_running = True
    asyncio.run(radio_start(self, self._radiomodule, self._serialPort))


def callBackGetDevice(nwk, ieee):
    return None


async def radio_start(self, radiomodule, serialPort, auto_form=False):

    self.log.logging("TransportWrter", "Debug", "In radio_start")

    conf = {CONF_DEVICE: {"path": serialPort}}
    if radiomodule == "zigate":
        self.app = App_zigate(conf)

    elif radiomodule == "znp":
        self.app = App_znp(conf)

    await self.app.startup(self.receiveData, callBackGetDevice=self.ZigpyGetDevice, auto_form=True, log=self.log)

    # Send Network information to plugin, in order to poplulate various objetcs
    self.receiveData(build_plugin_8009_frame_content(self))

    self.log.logging("TransportWrter", "Debug", "PAN ID:               0x%04x" % self.app.pan_id)

    self.log.logging("TransportWrter", "Debug", "Extended PAN ID:      0x%s" % self.app.extended_pan_id)
    self.log.logging("TransportWrter", "Debug", "Channel:              %d" % self.app.channel)
    self.log.logging("TransportWrter", "Debug", "Device IEEE:          %s" % self.app.ieee)
    self.log.logging("TransportWrter", "Debug", "Device NWK:           0x%04x" % self.app.nwk)

    # Run forever
    await worker_loop(self)

    await self.app.shutdown()
    self.log.logging("TransportWrter", "Debug", "Exiting co-rounting radio_start")


async def worker_loop(self):
    self.log.logging("TransportWrter", "Debug", "worker_loop - ZigyTransport: worker_loop start.")

    while self.zigpy_running:
        # self.log.logging("TransportWrter",  'Debug', "Waiting for next command Qsize: %s" %self.writer_queue.qsize())
        if self.writer_queue is None:
            break
        try:
            prio, entry = self.writer_queue.get(False)

        except queue.Empty:
            await asyncio.sleep(0.250)
            continue

        if entry == "STOP":
            break

        if self.writer_queue.qsize() > self.statistics._MaxLoad:
            self.statistics._MaxLoad = self.writer_queue.qsize()

        data = json.loads(entry)
        self.log.logging("TransportWrter", "Debug", "got command %s" % data)

        try:
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
                await self.app.set_time_server(data["datas"]["Param1"])
            elif data["cmd"] in NATIVE_COMMANDS_MAPPING:
                await native_commands(self, data["cmd"], data["datas"])
            elif data["cmd"] == "RAW-COMMAND":
                await process_raw_command(self, data["datas"], AckIsDisable=data["ACKIsDisable"], Sqn=data["Sqn"])

        except DeliveryError:
            self.log.logging(
                "TransportWrter",
                "Error",
                "DeliveryError: Not able to execute the zigpy command: %s data: %s" % (data["cmd"], data["datas"]),
            )

        except InvalidFrame:
            self.log.logging(
                "TransportWrter",
                "Error",
                "InvalidFrame: Not able to execute the zigpy command: %s data: %s" % (data["cmd"], data["datas"]),
            )

        except CommandNotRecognized:
            self.log.logging(
                "TransportWrter",
                "Error",
                "CommandNotRecognized: Not able to execute the zigpy command: %s data: %s" % (data["cmd"], data["datas"]),
            )

            
        except InvalidResponse:
            self.log.logging(
                "TransportWrter",
                "Error",
                "InvalidResponse: Not able to execute the zigpy command: %s data: %s" % (data["cmd"], data["datas"]),
            )

        except RuntimeError as e:
            self.log.logging(
                "TransportWrter",
                "Error",
                "RuntimeError: %s Not able to execute the zigpy command: %s data: %s" % (e, data["cmd"], data["datas"]),
            )

        except Exception as e:
            self.log.logging("TransportWrter", "Error", "Error while receiving a Plugin command: >%s<" % e)
            handle_thread_error(self, e, data)

    self.log.logging("TransportWrter", "Debug", "ZigyTransport: writer_thread Thread stop.")


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
    NwkId = data["TargetNwk"]
    dEp = data["TargetEp"]
    sEp = data["SrcEp"]
    payload = bytes.fromhex(data["payload"])
    sequence = Sqn or self.app.get_sequence()
    addressmode = data["AddressMode"]
    enableAck = not AckIsDisable

    self.statistics._sent += 1
    self.log.logging(
        "TransportWrter",
        "Debug",
        "ZigyTransport: process_raw_command ready to request NwkId: %04x Cluster: %04x Seq: %02x Payload: %s AddrMode: %02x EnableAck: %s, Sqn: %s"
        % (NwkId, Cluster, sequence, payload, addressmode, enableAck, Sqn),
    )

    if self.pluginconf.pluginConf["ZiGateReactTime"]:
        t_start = 1000 * time.time()

    if addressmode == 0x01:
        # Group Mode
        result, msg = await self.app.mrequest(
            NwkId, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=enableAck, use_ieee=False
        )
    elif addressmode in (0x02, 0x07):
        # Short
        destination = zigpy.device.Device(self.app, None, NwkId)
        result, msg = await self.app.request(
            destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=enableAck, use_ieee=False
        )
    elif addressmode in (0x03, 0x08):
        destination = zigpy.device.Device(self.app, NwkId, None)
        result, msg = await self.app.request(
            destination, Profile, Cluster, sEp, dEp, sequence, payload, expect_reply=enableAck, use_ieee=False
        )

    if self.pluginconf.pluginConf["ZiGateReactTime"]:
        t_end = 1000 * time.time()
        t_elapse = int(t_end - t_start)
        self.statistics.add_timing_zigpy(t_elapse)
        if t_elapse > 1000:
            self.log.logging(
                "TransportWrter",
                "Log",
                "process_raw_command (zigpyThread) spend more than 1s (%s ms) frame: %s with Ack: %s"
                % (t_elapse, data, AckIsDisable),
            )

    self.log.logging(
        "TransportWrter",
        "Debug",
        "ZigyTransport: process_raw_command completed NwkId: %s result: %s msg: %s" % (destination, result, msg),
    )

    if enableAck:
        # Looks like Zigate return an int, while ZNP returns a status.type
        if not isinstance(result, int):
            result = int(result.serialize().hex(), 16)

        # Update statistics
        if result != 0x00:
            self.statistics._APSNck += 1
        else:
            self.statistics._APSAck += 1

        # Send Ack/Nack to Plugin
        self.forwarder_queue.put(
            build_plugin_8011_frame_content(self, destination.nwk.serialize()[::-1].hex(), result, destination.lqi) )
