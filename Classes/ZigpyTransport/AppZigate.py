#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: badz & pipiche38
#

import binascii
import datetime
import logging
from typing import Any, Optional

import Domoticz
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
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_004D_frame_content, build_plugin_8002_frame_content,
    build_plugin_8010_frame_content, build_plugin_8048_frame_content)
from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)

LOGGER = logging.getLogger(__name__)


class App_zigate(zigpy_zigate.zigbee.application.ControllerApplication):
    @classmethod
    async def new(cls, config: dict, auto_form: bool = False, start_radio: bool = True) -> zigpy.application.ControllerApplication:
        LOGGER.debug("new")

    async def _load_db(self) -> None:
        LOGGER.debug("_load_db")

    async def startup(self, HardwareID, pluginconf, callBackHandleMessage, callBackUpdDevice=None, callBackGetDevice=None, callBackBackup=None, auto_form=False, force_form=False, log=None, permit_to_join_timer=None):
        self.callBackFunction = callBackHandleMessage
        self.callBackGetDevice = callBackGetDevice
        self.callBackUpdDevice = callBackUpdDevice
        self.pluginconf = pluginconf
        self.log = log
        self.HardwareID = HardwareID
        
        try:
            await self._startup( auto_form=True )
        except Exception:
            await self.shutdown()
            raise
        if force_form:
            await super().form_network()

        version_str = await self._api.version_str()
        version_intmajor, version_intminor = await self._api.version_int()
        self.log.logging("TransportZigpy", "Debug", "App - version_str: %s" % (version_str ))
        self.log.logging("TransportZigpy", "Debug", "App - version_int: %s / %s" % (version_intmajor, version_intminor ))
        
        Model = "11"  # Zigpy
        FirmwareMajorVersion = "%02x" %version_intmajor
        FirmwareVersion = "%04x" % version_intminor
        
        self.callBackFunction(build_plugin_8010_frame_content(Model, FirmwareMajorVersion, FirmwareVersion))

    async def _startup(self, *, auto_form: bool = False):
        """
        Starts a network, optionally forming one with random settings if necessary.
        """
        await self.connect()
        try:
            try:
                await self.load_network_info(load_devices=False)
            except zigpy.exceptions.NetworkNotFormed:
                LOGGER.info("Network is not formed")
                if not auto_form:
                    raise
                LOGGER.info("Forming a new network")
                await self.form_network()
            LOGGER.debug("Network info: %s", self.state.network_info)
            LOGGER.debug("Node info: %s", self.state.node_info)
            LOGGER.info("Zigate Configuration: %s", self.config)
            await self.start_network()
        except Exception:
            LOGGER.error("Couldn't start application")
            await self.shutdown()
            raise
        
    # Only needed if the device require simple node descriptor from the coordinator
    async def register_endpoint(self, endpoint=1):
        await super().add_endpoint(endpoint)

    def get_device(self, ieee=None, nwk=None):
        # LOGGER.debug("get_device nwk %s ieee %s" % (nwk, ieee))
        # self.callBackGetDevice is set to zigpy_get_device(self, nwkid = None, ieee=None)
        # will return None if not found
        # will return (nwkid, ieee) if found ( nwkid and ieee are numbers)
        self.log.logging("TransportZigpy", "Debug", "App - get_device ieee:%s nwk:%s " % (ieee,nwk ))

        dev = None
        try:
            dev = super().get_device(ieee, nwk)
            self._update_nkdids_if_needed( dev.ieee, dev.nwk )
            
        except KeyError:
            if self.callBackGetDevice:
                if nwk is not None:
                    nwk = nwk.serialize()[::-1].hex()
                if ieee is not None:
                    ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
                self.log.logging("TransportZigpy", "Debug", "App - get_device calling callBackGetDevice %s (%s) %s (%s)" % (ieee,type(ieee),nwk, type(nwk)))
                zfd_dev = self.callBackGetDevice(ieee, nwk)
                if zfd_dev is not None:
                    (nwk, ieee) = zfd_dev
                    dev = self.add_device(t.EUI64(t.uint64_t(ieee).serialize()),nwk)

        if dev is not None:
            # LOGGER.debug("found device dev: %s" % (str(dev)))
            self.log.logging("TransportZigpy", "Debug", "App - get_device found device: %s" % dev)
            return dev
        
        LOGGER.debug("AppZigate get_device raise KeyError ieee: %s nwk: %s !!" %( ieee, nwk))
        raise KeyError

    def handle_join(self, nwk: t.NWK, ieee: t.EUI64, parent_nwk: t.NWK) -> None:
        """
        Called when a device joins or announces itself on the network.
        """
        ieee = t.EUI64(ieee)
        try:
            dev = self.get_device(ieee)
            LOGGER.info("Device 0x%04x (%s) joined the network", nwk, ieee)
        except KeyError:
            dev = self.add_device(ieee, nwk)
            LOGGER.info("New device 0x%04x (%s) joined the network", nwk, ieee)

        if dev.nwk != nwk:
            dev.nwk = nwk
            self._update_nkdids_if_needed( ieee, dev.nwk )
            LOGGER.debug("Device %s changed id (0x%04x => 0x%04x)", ieee, dev.nwk, nwk)

    def _update_nkdids_if_needed( self, ieee, new_nwkid ):
        _ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
        _nwk = new_nwkid.serialize()[::-1].hex()
        self.callBackUpdDevice(_ieee, _nwk)

    def get_device_ieee(self, nwk):
        # Call from the plugin to retreive the ieee
        # we assumed nwk as an hex string
        try:
            dev = super().get_device( nwk=int(nwk,16))
            LOGGER.debug("AppZigate get_device  nwk: %s returned %s" %( nwk, dev))
        except KeyError:
            LOGGER.debug("AppZigate get_device raise KeyError nwk: %s !!" %( nwk))
            return None  
        if dev.ieee:
            return "%016x" % t.uint64_t.deserialize(dev.ieee.serialize())[0]
        return None         


    def handle_leave(self, nwk, ieee):
        self.log.logging("TransportZigpy", "Debug","handle_leave (0x%04x %s)" %(nwk, ieee))

        plugin_frame = build_plugin_8048_frame_content(self, ieee)
        self.callBackFunction(plugin_frame)
        super().handle_leave(nwk, ieee)

    def handle_message(
        self,
        sender: zigpy.device.Device,
        profile: int,
        cluster: int,
        src_ep: int,
        dst_ep: int,
        message: bytes,
    ) -> None:

        if sender.nwk == 0x0000:
            self.log.logging("TransportZigpy", "Debug", "handle_message from Controller Sender: %s Profile: %04x Cluster: %04x srcEp: %02x dstEp: %02x message: %s" %(
                str(sender.nwk), profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8")))
            super().handle_message(sender, profile, cluster, src_ep, dst_ep, message)


        if sender.nwk is not None:
            addr_mode = 0x02
            addr = sender.nwk.serialize()[::-1].hex()
            self.log.logging(
                "TransportZigpy",
                "Debug",
                "handle_message device 1: %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s lqi: %s" % (
                    str(sender), profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8"), sender.lqi)),


        elif sender.ieee is not None:
            addr = "%016x" % t.uint64_t.deserialize(sender.ieee.serialize())[0]
            addr_mode = 0x03
            self.log.logging(
                "TransportZigpy",
                "Debug",
                "handle_message device 1: %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s lqi: %s" % (
                    str(sender), profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8"), sender.lqi)),

        if sender.lqi is None:
            sender.lqi = 0x00

        if src_ep == dst_ep == 0x00:
            profile = 0x0000

        if addr:
            plugin_frame = build_plugin_8002_frame_content(self, addr, profile, cluster, src_ep, dst_ep, message, sender.lqi, src_addrmode=addr_mode)
            self.log.logging("TransportZigpy", "Debug", "handle_message Sender: %s frame for plugin: %s" % (addr, plugin_frame))
            self.callBackFunction(plugin_frame)
        else:
            self.log.logging(
                "TransportZigpy",
                "Error",
                "handle_message Sender unkown device : %s addr: %s addr_mode: %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s" % (
                    str(sender), addr, addr_mode, profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8")),
            )

        return None

    async def set_zigpy_tx_power(self, power):
        await self._api.set_tx_power(power)

    async def set_led(self, mode):
        await self._api.set_led(mode)

    async def set_certification(self, mode):
        await self._api.set_certification(mode)

    async def get_time_server(self):
        await self._api.get_time_server()

    async def set_time_server(self, newtime):
        await self._api.set_time()

    async def get_firmware_version(self):
        pass

    async def erase_pdm(self):
        await self._api.erase_persistent_data()

    async def soft_reset(self):
        await self._api.reset()


    async def set_extended_pan_id(self):
        pass      

    async def set_channel(self):
        pass        

    async def remove_ieee(self, ieee):
        pass
