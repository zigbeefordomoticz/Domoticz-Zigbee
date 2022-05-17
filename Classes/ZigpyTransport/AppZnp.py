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
import zigpy.zdo.types as zdo_t
import zigpy_znp.commands as c
import zigpy_znp.commands.util
import zigpy_znp.config as conf
import zigpy_znp.types as t
import zigpy_znp.zigbee.application

import asyncio
import async_timeout
from zigpy_znp.types.nvids import OsalNvIds
import zigpy_znp.const as const
from zigpy_znp.api import ZNP
from zigpy_znp.zigbee.device import ZNPCoordinator

from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_8002_frame_content, build_plugin_8010_frame_content,
    build_plugin_8014_frame_content, build_plugin_8015_frame_content,
    build_plugin_8047_frame_content, build_plugin_8048_frame_content)
from Modules.zigbeeVersionTable import ZNP_MODEL
from zigpy.zcl import clusters
from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)

STARTUP_TIMEOUT = 5

LOGGER = logging.getLogger(__name__)

class App_znp(zigpy_znp.zigbee.application.ControllerApplication):
    async def new(cls, config: dict, auto_form: bool = False, start_radio: bool = True) -> zigpy.application.ControllerApplication:
        logging.debug("new")

    async def _load_db(self) -> None:
        logging.debug("_load_db")

    async def startup(self, callBackHandleMessage, callBackGetDevice=None, auto_form=False, force_form=False, log=None, permit_to_join_timer=None):
        # If set to != 0 (default) extended PanId will be use when forming the network.
        # If set to !=0 (default) channel will be use when formin the network
        self.log = log
        self.permit_to_join_timer = permit_to_join_timer
        self.callBackFunction = callBackHandleMessage
        self.callBackGetDevice = callBackGetDevice
        self.znp_config[conf.CONF_MAX_CONCURRENT_REQUESTS] = 2

        try:
            await self._startup(
                auto_form=auto_form,
                force_form=force_form,
                read_only=False,
            )
        except Exception:
            await self.shutdown()
            raise


        # Populate and get the list of active devices.
        # This will allow the plugin if needed to update the IEEE -> NwkId
        await self.load_network_info( load_devices=True )
        network_info = self._znp.network_info
        self.callBackFunction(build_plugin_8015_frame_content( self, network_info))
        
        # Trigger Version payload to plugin
        znp_model = self.get_device(nwk=t.NWK(0x0000)).model
        znp_manuf = self.get_device(nwk=t.NWK(0x0000)).manufacturer
        FirmwareBranch, FirmwareMajorVersion, FirmwareVersion = extract_versioning_for_plugin( znp_model, znp_manuf)
        self.callBackFunction(build_plugin_8010_frame_content(FirmwareBranch, FirmwareMajorVersion, FirmwareVersion))


    async def _startup(self, auto_form=False, force_form=False, read_only=False):
        assert self._znp is None  # nosec

        znp = ZNP(self.config)
        await znp.connect()

        # We only assign `self._znp` after it has successfully connected
        self._znp = znp
        self._znp.set_application(self)

        if not read_only and not force_form:
            await self._migrate_nvram()

        self._bind_callbacks()

        # Next, read out the NVRAM item that Zigbee2MQTT writes when it has configured
        # a device to make sure that our network settings will not be reset.
        if self._znp.version == 1.2:
            configured_nv_item = OsalNvIds.HAS_CONFIGURED_ZSTACK1
        else:
            configured_nv_item = OsalNvIds.HAS_CONFIGURED_ZSTACK3

        try:
            configured_value = await self._znp.nvram.osal_read(
                configured_nv_item, item_type=t.uint8_t
            )
        except KeyError:
            is_configured = False
        else:
            is_configured = configured_value == const.ZSTACK_CONFIGURE_SUCCESS

        if force_form:
            LOGGER.info("Forming a new network")
            await self.form_network()
        elif not is_configured:
            if not auto_form:
                raise RuntimeError("Cannot start application, network is not formed")
            if read_only:
                raise RuntimeError(
                    "Cannot start application, network is not formed and read-only"
                )

            LOGGER.info("ZNP is not configured, forming a new network")

            # Network formation requires multiple resets so it will write the NVRAM
            # settings itself
            await self.form_network()
        else:
            # Issue a reset first to make sure we aren't permitting joins
            await self._znp.reset()

            LOGGER.info("ZNP is already configured, not forming a new network")

            if not read_only:
                await self._write_stack_settings(reset_if_changed=True)

        # At this point the device state should the same, regardless of whether we just
        # formed a new network or are restoring one
        if self.znp_config[conf.CONF_TX_POWER] is not None:
            await self.set_tx_power(dbm=self.znp_config[conf.CONF_TX_POWER])

        # Both versions of Z-Stack use this callback
        started_as_coordinator = self._znp.wait_for_response(
            c.ZDO.StateChangeInd.Callback(State=t.DeviceState.StartedAsCoordinator)
        )

        if self._znp.version == 1.2:
            # Z-Stack Home 1.2 has a simple startup sequence
            await self._znp.request(
                c.ZDO.StartupFromApp.Req(StartDelay=100),
                RspState=c.zdo.StartupState.RestoredNetworkState,
            )
        else:
            # Z-Stack 3 uses the BDB subsystem
            bdb_commissioning_done = self._znp.wait_for_response(
                c.AppConfig.BDBCommissioningNotification.Callback(
                    partial=True, RemainingModes=c.app_config.BDBCommissioningMode.NONE
                )
            )

            # According to the forums, this is the correct startup sequence, including
            # the formation failure error
            await self._znp.request_callback_rsp(
                request=c.AppConfig.BDBStartCommissioning.Req(
                    Mode=c.app_config.BDBCommissioningMode.NwkFormation
                ),
                RspStatus=t.Status.SUCCESS,
                callback=c.AppConfig.BDBCommissioningNotification.Callback(
                    partial=True,
                    Status=c.app_config.BDBCommissioningStatus.NetworkRestored,
                ),
            )

            await bdb_commissioning_done

        # The startup sequence should not take forever
        async with async_timeout.timeout(STARTUP_TIMEOUT):
            await started_as_coordinator

        self._version_rsp = await self._znp.request(c.SYS.Version.Req())

        # The CC2531 running Z-Stack Home 1.2 overrides the LED setting if it is changed
        # before the coordinator has started.
        if self.znp_config[conf.CONF_LED_MODE] is not None:
            await self._set_led_mode(led=0xFF, mode=self.znp_config[conf.CONF_LED_MODE])

        await self.load_network_info()
        await self._register_endpoints()

        # Receive a callback for every known ZDO command
        for cluster_id in zdo_t.ZDOCmd:
            # Ignore outgoing ZDO requests, only receive announcements and responses
            if cluster_id.name.endswith(("_req", "_set")):
                continue

            await self._znp.request(c.ZDO.MsgCallbackRegister.Req(ClusterId=cluster_id))

        # Setup the coordinator as a zigpy device and initialize it to request node info
        self.devices[self.ieee] = ZNPCoordinator(self, self.ieee, self.nwk)
        self.zigpy_device.zdo.add_listener(self)
        await self.zigpy_device.schedule_initialize()

        # Now that we know what device we are, set the max concurrent requests
        if self.znp_config[conf.CONF_MAX_CONCURRENT_REQUESTS] == "auto":
            max_concurrent_requests = 16 if self._znp.nvram.align_structs else 2
        else:
            max_concurrent_requests = self.znp_config[conf.CONF_MAX_CONCURRENT_REQUESTS]

        self._concurrent_requests_semaphore = asyncio.Semaphore(max_concurrent_requests)

        LOGGER.info("Network settings")
        LOGGER.info("  Model: %s", self.zigpy_device.model)
        LOGGER.info("  Z-Stack version: %s", self._znp.version)
        LOGGER.info("  Z-Stack build id: %s", self._zstack_build_id)
        LOGGER.info("  Max concurrent requests: %s", max_concurrent_requests)
        LOGGER.info("  Channel: %s", self.channel)
        LOGGER.info("  PAN ID: 0x%04X", self.pan_id)
        LOGGER.info("  Extended PAN ID: %s", self.extended_pan_id)
        LOGGER.info("  Device IEEE: %s", self.ieee)
        LOGGER.info("  Device NWK: 0x%04X", self.nwk)
        LOGGER.debug(
            "  Network key: %s",
            ":".join(
                f"{c:02x}" for c in self.state.network_information.network_key.key
            ),
        )

        if self.state.network_information.network_key.key == const.Z2M_NETWORK_KEY:
            LOGGER.warning(
                "Your network is using the insecure Zigbee2MQTT network key!"
            )

        self._watchdog_task = asyncio.create_task(self._watchdog_loop())

    async def _register_endpoints(self) -> None:
        LIST_ENDPOINT = [0x0b , 0x0a , 0x6e, 0x15, 0x08, 0x03]  # WISER, ORVIBO , TERNCY, KONKE, LIVOLO, WISER2
        await super()._register_endpoints()

        for endpoint in LIST_ENDPOINT:
            await self._znp.request(
                c.AF.Register.Req(
                    Endpoint=endpoint,
                    ProfileId=zigpy.profiles.zha.PROFILE_ID,
                    DeviceId=zigpy.profiles.zll.DeviceType.CONTROLLER,
                    DeviceVersion=0b0000,
                    LatencyReq=c.af.LatencyReq.NoLatencyReqs,
                    InputClusters=[clusters.general.Basic.cluster_id],
                    OutputClusters=[],
                ),
                RspStatus=t.Status.SUCCESS,
            )

    def get_device(self, ieee=None, nwk=None):
        # logging.debug("get_device nwk %s ieee %s" % (nwk, ieee))
        # self.callBackGetDevice is set to zigpy_get_device(self, nwkid = None, ieee=None)
        # will return None if not found
        # will return (nwkid, ieee) if found ( nwkid and ieee are numbers)
        self.log.logging("TransportZigpy", "Debug", "AppZnp - get_device ieee:%s nwk:%s " % (ieee,nwk ))
#        self.log.logging("TransportZigpy", "Debug", "AppZnp - get_device current_list%s  " % (self.devices ))

        dev = None
        try:
            dev = super().get_device(ieee, nwk)
            
        except KeyError:
            if self.callBackGetDevice:
                if nwk is not None:
                    nwk = nwk.serialize()[::-1].hex()
                if ieee is not None:
                    ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
                self.log.logging("TransportZigpy", "Debug", "AppZnp - get_device calling callBackGetDevice %s (%s) %s (%s)" % (ieee,type(ieee),nwk, type(nwk)))
                zfd_dev = self.callBackGetDevice(ieee, nwk)
                if zfd_dev is not None:
                    (nwk, ieee) = zfd_dev
                    dev = self.add_device(t.EUI64(t.uint64_t(ieee).serialize()),nwk)

        if dev is not None:
            # logging.debug("found device dev: %s" % (str(dev)))
            self.log.logging("TransportZigpy", "Debug", "AppZnp - get_device found device: %s" % dev)
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
            #logging.debug("handle_join waiting 1s for zigbee initialisation")
            time.sleep(1.0)
            LOGGER.debug("Device 0x%04x (%s) joined the network", nwk, ieee)
        except KeyError:
            #logging.debug("handle_join waiting 1s for zigbee initialisation")
            time.sleep(1.0)
            dev = self.add_device(ieee, nwk)
            LOGGER.debug("New device 0x%04x (%s) joined the network", nwk, ieee)

        if dev.nwk != nwk:
            LOGGER.debug("Device %s changed id (0x%04x => 0x%04x)", ieee, dev.nwk, nwk)
            dev.nwk = nwk
            
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
        if sender is None or profile is None or cluster is None:
            self.log.logging("TransportZigpy", "Error", "handle_message sender: %s profile: %s cluster: %s sep: %s dep: %s message: %s" %(
                str(sender.nwk), profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8")))
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
