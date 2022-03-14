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
import zigpy_deconz
import zigpy_deconz.zigbee.application
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_8002_frame_content, build_plugin_8010_frame_content,
    build_plugin_8014_frame_content, build_plugin_8015_frame_content,
    build_plugin_8047_frame_content, build_plugin_8048_frame_content)
from zigpy_deconz.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)

LOGGER = logging.getLogger(__name__)




class App_deconz(zigpy_deconz.zigbee.application.ControllerApplication):
    async def new(cls, config: dict, auto_form: bool = False, start_radio: bool = True) -> zigpy.application.ControllerApplication:
        logging.debug("new")

    async def _load_db(self) -> None:
        logging.debug("_load_db")

    async def startup(self, callBackHandleMessage, callBackGetDevice=None, auto_form=False, force_form=False, log=None, permit_to_join_timer=None ):
        logging.debug("startup in AppDeconz")
        self.log = log
        self.permit_to_join_timer = permit_to_join_timer
        self.callBackFunction = callBackHandleMessage
        self.callBackGetDevice = callBackGetDevice

        logging.debug("startup in AppDeconz - super()")
        await super().startup(auto_form=auto_form)
        if force_form:
            logging.debug("startup in AppDeconz - form new network")
            await super().form_network()

        # Populate and get the list of active devices.
        # This will allow the plugin if needed to update the IEEE -> NwkId
        #await self.load_network_info( load_devices=True )
        #network_info = self.state.network_information

        #logging.debug("startup %s" %network_info) 
        #self.callBackFunction(build_plugin_8015_frame_content( self, network_info))

        # Trigger Version payload to plugin

        deconz_model = self.get_device(nwk=t.NWK(0x0000)).model
        deconz_manuf = self.get_device(nwk=t.NWK(0x0000)).manufacturer

        deconz_version = "%08x" %self.version
        deconz_major = deconz_version[:4]
        deconz_minor = deconz_version[4:8]
        logging.debug("startup in AppDeconz - build 8010 %s %08x %s" %(
            deconz_version, self.version, deconz_major + deconz_minor))
        if deconz_model == "ConBee II":
            self.callBackFunction(build_plugin_8010_frame_content("40", deconz_major, deconz_minor))
        elif deconz_model == "RaspBee II":
            self.callBackFunction(build_plugin_8010_frame_content("41", deconz_major, deconz_minor))
        else:
            self.callBackFunction(build_plugin_8010_frame_content("99", deconz_major, deconz_minor))
            

    def get_device(self, ieee=None, nwk=None):
        # logging.debug("get_device nwk %s ieee %s" % (nwk, ieee))
        # self.callBackGetDevice is set to zigpy_get_device(self, nwkid = None, ieee=None)
        # will return None if not found
        # will return (nwkid, ieee) if found ( nwkid and ieee are numbers)
        self.log.logging("TransportZigpy", "Debug", "App - get_device ieee:%s nwk:%s " % (ieee,nwk ))

        dev = None
        try:
            dev = super().get_device(ieee, nwk)
            
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
            # logging.debug("found device dev: %s" % (str(dev)))
            self.log.logging("TransportZigpy", "Debug", "App - get_device found device: %s" % dev)
            return dev
        
        logging.debug("get_device raise KeyError ieee: %s nwk: %s !!" %( ieee, nwk))
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
            LOGGER.debug("Device %s changed id (0x%04x => 0x%04x)", ieee, dev.nwk, nwk)
            dev.nwk = nwk

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
        pass
        #await self._api.set_tx_power(power)

    async def set_led(self, mode):
        pass
        #await self._api.set_led(mode)

    async def set_certification(self, mode):
        pass
        #await self._api.set_certification(mode)

    async def get_time_server(self):
        pass
        #await self._api.get_time_server()

    async def set_time_server(self, newtime):
        pass
        #await self._api.set_time()

    async def get_firmware_version(self):
        pass

    async def erase_pdm(self):
        pass

    async def soft_reset(self):
        pass

    async def set_extended_pan_id(self, extended_pan_ip): 
        pass 

    async def set_channel(self):
        pass        

    async def remove_ieee(self, ieee):
        pass
