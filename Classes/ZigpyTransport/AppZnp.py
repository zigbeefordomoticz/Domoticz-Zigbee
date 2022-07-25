#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: badz & pipiche38
#

import binascii
import logging
from typing import Any, Optional
import time

import zigpy.appdb
import zigpy.config
import zigpy.device
import zigpy.exceptions
import zigpy.group
import zigpy.ota
import zigpy.quirks
import zigpy.state
import zigpy.topology
import zigpy.util
import zigpy.zcl
import zigpy.zdo
import zigpy.zdo.types as zdo_types
import zigpy_znp.commands as c
import zigpy_znp.commands.util
import zigpy_znp.config as conf
import zigpy_znp.types as t
import zigpy_znp.zigbee.application
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_8002_frame_content, build_plugin_8010_frame_content,
    build_plugin_8014_frame_content, build_plugin_8015_frame_content,
    build_plugin_8047_frame_content, build_plugin_8048_frame_content)
from Modules.zigbeeVersionTable import ZNP_MODEL
from zigpy.zcl import clusters
from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)

LOGGER = logging.getLogger(__name__)

class App_znp(zigpy_znp.zigbee.application.ControllerApplication):
    async def new(cls, config: dict, auto_form: bool = False, start_radio: bool = True) -> zigpy.application.ControllerApplication:
        logging.debug("new")

    async def _load_db(self) -> None:
        logging.debug("_load_db")

    async def startup(self, pluginconf, callBackHandleMessage, callBackUpdDevice=None, callBackGetDevice=None, auto_form=False, force_form=False, log=None, permit_to_join_timer=None):
        # If set to != 0 (default) extended PanId will be use when forming the network.
        # If set to !=0 (default) channel will be use when formin the network
        self.log = log
        self.pluginconf = pluginconf
        self.permit_to_join_timer = permit_to_join_timer
        self.callBackFunction = callBackHandleMessage
        self.callBackUpdDevice = callBackUpdDevice
        self.callBackGetDevice = callBackGetDevice
        self.znp_config[conf.CONF_MAX_CONCURRENT_REQUESTS] = 2

        try:
            await self._startup( auto_form=True )
        except Exception:
            await self.shutdown()
            raise
        if force_form:
            await super().form_network()

        # Populate and get the list of active devices.
        # This will allow the plugin if needed to update the IEEE -> NwkId
        await self.load_network_info( load_devices=True )
        network_info = self.state.network_info
        self.callBackFunction(build_plugin_8015_frame_content( self, network_info))
        
        # Trigger Version payload to plugin
        znp_model = self.get_device(nwk=t.NWK(0x0000)).model
        znp_manuf = self.get_device(nwk=t.NWK(0x0000)).manufacturer
        FirmwareBranch, FirmwareMajorVersion, FirmwareVersion = extract_versioning_for_plugin( znp_model, znp_manuf)
        self.callBackFunction(build_plugin_8010_frame_content(FirmwareBranch, FirmwareMajorVersion, FirmwareVersion))

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
            LOGGER.info("ZNP Configuration: %s", self.config)
            await self.start_network()
        except Exception:
            LOGGER.error("Couldn't start application")
            await self.shutdown()
            raise

    async def register_endpoints(self):
        await super().register_endpoints()  

        LIST_ENDPOINT = [0x0b , 0x0a , 0x6e, 0x15, 0x08, 0x03]  # WISER, ORVIBO , TERNCY, KONKE, LIVOLO, WISER2
        for controller_ep in LIST_ENDPOINT:
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=controller_ep,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=[zigpy.zcl.clusters.general.Basic.cluster_id,],
                    output_clusters=[],
                )
            )

    def device_initialized(self, device):
            self.log.logging("TransportZigpy", "Log","device_initialized (0x%04x %s)" %(device.nwk, device.ieee))
            super().device_initialized(device)
            
    def get_device(self, ieee=None, nwk=None):
        # logging.debug("get_device nwk %s ieee %s" % (nwk, ieee))
        # self.callBackGetDevice is set to zigpy_get_device(self, nwkid = None, ieee=None)
        # will return None if not found
        # will return (nwkid, ieee) if found ( nwkid and ieee are numbers)
        dev = None
        try:
            dev = super().get_device(ieee, nwk)
            # We have found in Zigpy db.
            # We might have to check that the plugin and zigpy Dbs are in sync
            # Let's check if the tupple (dev.ieee, dev.nwk ) are aligned with plugin Db
            self._update_nkdids_if_needed( dev.ieee, dev.nwk )
            
        except KeyError:
            # Not found in zigpy Db, let see if we can get it into the Plugin Db
            if self.callBackGetDevice:
                if nwk is not None:
                    nwk = nwk.serialize()[::-1].hex()
                if ieee is not None:
                    ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
                zfd_dev = self.callBackGetDevice(ieee, nwk)
                if zfd_dev is not None:
                    (nwk, ieee) = zfd_dev
                    dev = self.add_device(t.EUI64(t.uint64_t(ieee).serialize()),nwk)

        if dev is not None:
            return dev
        
        logging.debug("AppZnp get_device raise KeyError ieee: %s nwk: %s !!" %( ieee, nwk))
        raise KeyError

    def handle_join(self, nwk: t.NWK, ieee: t.EUI64, parent_nwk: t.NWK) -> None:
        """
        Called when a device joins or announces itself on the network.
        """
        ieee = t.EUI64(ieee)
        try:
            dev = self.get_device(ieee)
            time.sleep(1.0)
            LOGGER.info("Device 0x%04x (%s) joined the network", nwk, ieee)
        except KeyError:
            time.sleep(1.0)
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
        
                  
    def handle_leave(self, nwk, ieee):
        self.log.logging("TransportZigpy", "Debug","handle_leave (0x%04x %s)" %(nwk, ieee))
        plugin_frame = build_plugin_8048_frame_content(self, ieee)
        self.callBackFunction(plugin_frame)
        super().handle_leave(nwk, ieee)

    def get_zigpy_version(self):
        # This is a fake version number. This is just to inform the plugin that we are using ZNP over Zigpy
        logging.debug("get_zigpy_version ake version number. !!")
        return self.version

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

        if cluster == 0x8036:
            # This has been handle via on_zdo_mgmt_permitjoin_rsp()
            self.log.logging("TransportZigpy", "Debug", "handle_message 0x8036: %s Profile: %04x Cluster: %04x srcEp: %02x dstEp: %02x message: %s" %(
                str(sender.nwk), profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8")))
            self.callBackFunction( build_plugin_8014_frame_content(self, str(sender), binascii.hexlify(message).decode("utf-8") ) )
            super().handle_message(sender, profile, cluster, src_ep, dst_ep, message)
            return

        if cluster == 0x8034:
            # This has been handle via on_zdo_mgmt_leave_rsp()
            self.log.logging("TransportZigpy", "Debug", "handle_message 0x8036: %s Profile: %04x Cluster: %04x srcEp: %02x dstEp: %02x message: %s" %(
                str(sender.nwk), profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8")))
            self.callBackFunction( build_plugin_8047_frame_content(self, str(sender), binascii.hexlify(message).decode("utf-8")) )
            return

        addr = None
        if sender.nwk is not None:
            addr_mode = 0x02
            addr = sender.nwk.serialize()[::-1].hex()
            if profile and cluster:
                self.log.logging(
                    "TransportZigpy",
                    "Debug",
                    "handle_message device 1: %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s lqi: %s" % (
                        str(sender), profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8"), sender.lqi)),

        elif sender.ieee is not None:
            addr = "%016x" % t.uint64_t.deserialize(sender.ieee.serialize())[0]
            addr_mode = 0x03
            if profile and cluster:
                self.log.logging(
                    "TransportZigpy",
                    "Debug",
                    "handle_message device 1: %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s lqi: %s" % (
                        str(sender), profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8"), sender.lqi)),

        if sender.lqi is None:
            sender.lqi = 0x00

        if src_ep == dst_ep == 0x00:
            profile = 0x0000

        if profile and cluster:
            self.log.logging(
                "TransportZigpy",
                "Debug",
                "handle_message device 2: %s Profile: %04x Cluster: %04x sEP: %s dEp: %s message: %s lqi: %s" % (
                    str(addr), profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8"), sender.lqi),
            )

        if addr:
            plugin_frame = build_plugin_8002_frame_content(self, addr, profile, cluster, src_ep, dst_ep, message, sender.lqi, src_addrmode=addr_mode)
            self.log.logging("TransportZigpy", "Debug", "handle_message Sender: %s frame for plugin: %s" % (addr, plugin_frame))
            self.callBackFunction(plugin_frame)
        else:
            self.log.logging(
                "TransportZigpy",
                "Error",
                "handle_message - Issue with sender is %s %s" % (sender.nwk, sender.ieee),
            )

        return

    async def set_zigpy_tx_power(self, power):
        self.log.logging("TransportZigpy", "Debug", "set_tx_power %s" %power)
        await self.set_tx_power(dbm=power)

    async def set_led(self, mode):
        if mode == 1:
            await self._set_led_mode(led=0xFF, mode=zigpy_znp.commands.util.LEDMode.ON)
        else:
            await self._set_led_mode(led=0xFF, mode=zigpy_znp.commands.util.LEDMode.OFF)

    async def set_certification(self, mode):
        self.log.logging("TransportZigpy", "Debug", "set_certification not implemented yet")

    async def get_time_server(self):
        self.log.logging("TransportZigpy", "Debug", "get_time_server not implemented yet")

    async def set_time_server(self, newtime):
        self.log.logging("TransportZigpy", "Debug", "set_time_server not implemented yet")

    async def get_firmware_version(self):
        return self.znp.version

    async def erase_pdm(self):
        pass

    async def set_extended_pan_id(self,extended_pan_ip):
        self.confif[conf.CONF_NWK][conf.CONF_NWK_EXTENDED_PAN_ID] = extended_pan_ip
        self.startup(self.callBackHandleMessage,self.callBackGetDevice,auto_form=True,force_form=True,log=self.log)

    async def set_channel(self,channel):
        self.confif[conf.CONF_NWK][conf.CONF_NWK_EXTENDED_PAN_ID] = channel
        self.startup(self.callBackHandleMessage,self.callBackGetDevice,auto_form=True,force_form=True,log=self.log)

    async def remove_ieee(self, ieee):
        await self.remove( ieee )

def extract_versioning_for_plugin( znp_model, znp_manuf):
    
    ZNP_330 = "CC1352/CC2652, Z-Stack 3.30+"
    ZNP_30X = "CC2531, Z-Stack 3.0.x"
    
    for x in ZNP_MODEL:
        if znp_model[:len(x)] == x:
            FirmwareBranch = ZNP_MODEL[x]
            break
    else:
        # Not found in the Table.
        FirmwareBranch = "99"
        
    year = znp_model[ znp_model.find("build") + 6 : -5 ]
    FirmwareMajorVersion = "%02d" %int(znp_model[ znp_model.find("build") + 8 : -5 ])
    FirmwareVersion = "%04d" %int(znp_model[ znp_model.find("build") + 10: -1])
        
    return FirmwareBranch, FirmwareMajorVersion, FirmwareVersion
