#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: badz & pipiche38
#
import traceback
import asyncio
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
from serial import SerialException

LOGGER = logging.getLogger(__name__)




class App_deconz(zigpy_deconz.zigbee.application.ControllerApplication):
    async def new(self, config: dict, auto_form: bool = False, start_radio: bool = True) -> zigpy.application.ControllerApplication:
        LOGGER.debug("new")

    async def _load_db(self) -> None:
        LOGGER.debug("_load_db")

    async def startup(self, pluginconf, callBackHandleMessage, callBackUpdDevice=None, callBackGetDevice=None, callBackBackup=None, auto_form=False, force_form=False, log=None, permit_to_join_timer=None):
        LOGGER.debug("startup in AppDeconz")
        self.log = log
        self.pluginconf = pluginconf
        self.permit_to_join_timer = permit_to_join_timer
        self.callBackFunction = callBackHandleMessage
        self.callBackGetDevice = callBackGetDevice
        self.callBackUpdDevice = callBackUpdDevice
        self.callBackBackup = callBackBackup

        await asyncio.sleep( 2 )

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

        # deConz doesn't have such capabilities to provided list of paired devices.
        # LOGGER.debug("startup Network Info: %s" %str(network_info))
        # self.callBackFunction(build_plugin_8015_frame_content( self, network_info))

        # Trigger Version payload to plugin
        deconz_model = self.get_device(nwk=t.NWK(0x0000)).model
        deconz_manuf = self.get_device(nwk=t.NWK(0x0000)).manufacturer
        LOGGER.debug("startup in AppDeconz - Model: %s Manuf: %s" %(
            deconz_model, deconz_manuf))
        
        deconz_version = "%08x" %self.version
        deconz_major = deconz_version[:4]
        deconz_minor = deconz_version[4:8]
        LOGGER.debug("startup in AppDeconz - build 8010 %s %08x %s" %(
            deconz_version, self.version, deconz_major + deconz_minor))
        
        if deconz_model == "ConBee II":
            self.callBackFunction(build_plugin_8010_frame_content("40", deconz_major, deconz_minor))
        elif deconz_model == "RaspBee II":
            self.callBackFunction(build_plugin_8010_frame_content("41", deconz_major, deconz_minor))
        elif deconz_model == "RaspBee":
            self.callBackFunction(build_plugin_8010_frame_content("42", deconz_major, deconz_minor))
        elif deconz_model == "ConBee":
            self.callBackFunction(build_plugin_8010_frame_content("43", deconz_major, deconz_minor))
            
        else:
            LOGGER.info("Unknow Zigbee CIE from %s %s" %( deconz_manuf, deconz_model))
            self.callBackFunction(build_plugin_8010_frame_content("99", deconz_major, deconz_minor))


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
            LOGGER.info("Deconz Configuration: %s", self.config)
            await self.start_network()
        except Exception:
            LOGGER.error("Couldn't start application")
            await self.shutdown()
            raise

        if self.config[zigpy.config.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup ( await self.backups.create_backup() )

    async def shutdown(self) -> None:
        """Shutdown controller."""
        if self.config[zigpy.config.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup ( await self.backups.create_backup() )


    async def register_endpoints(self):
        await self._register_endpoints()  


    async def _register_endpoints(self):
        """
        Registers all necessary endpoints.
        The exact order in which this method is called depends on the radio module.
        """

        LOGGER.info("Adding Endpoint 0x%x" %0x01)
        await self.add_endpoint(
            zdo_types.SimpleDescriptor(
                endpoint=1,
                profile=zigpy.profiles.zha.PROFILE_ID,
                device_type=zigpy.profiles.zha.DeviceType.IAS_CONTROL,
                device_version=0b0000,
                input_clusters=[
                    zigpy.zcl.clusters.general.Basic.cluster_id,
                    zigpy.zcl.clusters.general.OnOff.cluster_id,
                    zigpy.zcl.clusters.general.Time.cluster_id,
                    zigpy.zcl.clusters.general.Ota.cluster_id,
                    zigpy.zcl.clusters.security.IasAce.cluster_id,
                ],
                output_clusters=[
                    zigpy.zcl.clusters.general.PowerConfiguration.cluster_id,
                    zigpy.zcl.clusters.general.PollControl.cluster_id,
                    zigpy.zcl.clusters.security.IasZone.cluster_id,
                    zigpy.zcl.clusters.security.IasWd.cluster_id,
                ],
            )
        )

        LOGGER.info("Adding Endpoint 0x%x" %0x02)
        await self.add_endpoint(
            zdo_types.SimpleDescriptor(
                endpoint=2,
                profile=zigpy.profiles.zll.PROFILE_ID,
                device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                device_version=0b0000,
                input_clusters=[zigpy.zcl.clusters.general.Basic.cluster_id],
                output_clusters=[],
            )
        )

        # Livolo Switch 0x08
        if "Livolo" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["Livolo"]:
            LOGGER.info("Adding Endpoint 0x%x" %0x08)
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=0x08,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=[
                        zigpy.zcl.clusters.general.Basic.cluster_id,
                        zigpy.zcl.clusters.general.OnOff.cluster_id,
                        ],
                    output_clusters=[
                        zigpy.zcl.clusters.security.IasZone.cluster_id,
                        ],
                )
            )

        # Wiser Legacy 0x0b
        if "Wiser" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["Wiser"]:
            LOGGER.info("Adding Endpoint 0x%x" %0x0b)
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=0x0b,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=[
                        zigpy.zcl.clusters.general.Basic.cluster_id,
                        ],
                    output_clusters=[
                        ],
                )
            )

        # Orvibo 0x0a
        if "Orvibo" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["Orvibo"]:
            LOGGER.info("Adding Endpoint 0x%x" %0x0a)
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=0x0a,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=[
                        zigpy.zcl.clusters.general.Basic.cluster_id,
                        ],
                    output_clusters=[
                        ],
                )
            )

        # Terncy 0x6e
        if "Terncy" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["Terncy"]:
            LOGGER.info("Adding Endpoint 0x%x" %0x6e)
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=0x6e,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=[
                        zigpy.zcl.clusters.general.Basic.cluster_id,
                        ],
                    output_clusters=[
                        ],
                )
            )

        # Konke 0x15
        if "Konke" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["Konke"]:
            LOGGER.info("Adding Endpoint 0x%x" %0x15)
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=0x15,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=[
                        zigpy.zcl.clusters.general.Basic.cluster_id,
                        zigpy.zcl.clusters.general.OnOff.cluster_id,
                        ],
                    output_clusters=[
                        zigpy.zcl.clusters.security.IasZone.cluster_id,
                        ],
                )
            )

        # Wiser2 (new generation 0x03)
        if "Wiser2" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["Wiser2"]:
            LOGGER.info("Adding Endpoint 0x%x" %0x03)
            await self.add_endpoint(
                zdo_types.SimpleDescriptor(
                    endpoint=0x03,
                    profile=zigpy.profiles.zha.PROFILE_ID,
                    device_type=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    device_version=0b0000,
                    input_clusters=[
                        zigpy.zcl.clusters.general.Basic.cluster_id,
                        ],
                    output_clusters=[
                        ],
                )
            )
        
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
        
        LOGGER.debug("AppDeconz get_device raise KeyError ieee: %s nwk: %s !!" %( ieee, nwk))
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
            LOGGER.debug("AppDeconz get_device  nwk: %s returned %s" %( nwk, dev))
        except KeyError:
            LOGGER.debug("AppDeconz get_device raise KeyError nwk: %s !!" %( nwk))
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
        
        if sender is None or profile is None or cluster is None:
            # drop the paquet 
            return

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

    async def coordinator_backup( self ):
        if self.config[zigpy.config.CONF_NWK_BACKUP_ENABLED]:
            self.callBackBackup ( await self.backups.create_backup() )
