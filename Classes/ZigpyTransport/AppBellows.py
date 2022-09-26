#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: badz & pipiche38
#

import binascii
import logging
from typing import Any, Optional

#import bellows.commands as c
#import bellows.commands.util
import bellows.config as conf
import bellows.ezsp as ezsp
import bellows.ezsp.v4.types as t
import bellows.zigbee.application
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
from bellows.exception import ControllerError, EzspError
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_8002_frame_content, build_plugin_8010_frame_content,
    build_plugin_8014_frame_content, build_plugin_8015_frame_content,
    build_plugin_8047_frame_content, build_plugin_8048_frame_content)
from Modules.zigbeeVersionTable import ZNP_MODEL
from zigpy.types import Addressing, KeyData
from zigpy.zcl import clusters
from zigpy_zigate.config import (CONF_DEVICE, CONF_DEVICE_PATH, CONFIG_SCHEMA,
                                 SCHEMA_DEVICE)

LOGGER = logging.getLogger(__name__)

class App_bellows(bellows.zigbee.application.ControllerApplication):
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
        #self.bellows_config[conf.CONF_MAX_CONCURRENT_REQUESTS] = 2

        if force_form:
            auto_form = False
        await super().startup(auto_form=auto_form)
        if force_form:
            await self._ezsp.leaveNetwork()
            await super().form_network()

        # Populate and get the list of active devices.
        # This will allow the plugin if needed to update the IEEE -> NwkId
        await self.load_network_info( load_devices=False ) # load_devices shows nothing for now
        network_info = self.state.network_information
        self.callBackFunction(build_plugin_8015_frame_content( self, network_info))
        
        # Trigger Version payload to plugin
        try:
            brd_manuf, brd_name, version = await self._ezsp.get_board_info()
            logging.debug("EZSP Radio manufacturer: %s", brd_manuf)
            logging.debug("EZSP Radio board name: %s", brd_name)
            logging.debug("EmberZNet version: %s" %version)
        except EzspError as exc:
            logging.error("EZSP Radio does not support getMfgToken command: %s" %str(exc))

        FirmwareBranch, FirmwareMajorVersion, FirmwareVersion = extract_versioning_for_plugin(brd_manuf, brd_name, version)
        self.callBackFunction(build_plugin_8010_frame_content(FirmwareBranch, FirmwareMajorVersion, FirmwareVersion))

    # Only needed if the device require simple node descriptor from the coordinator
    async def register_endpoint(self, endpoint=1):
        await super().add_endpoint(endpoint)

    def get_device(self, ieee=None, nwk=None):
        # logging.debug("get_device nwk %s ieee %s" % (nwk, ieee))
        # self.callBackGetDevice is set to zigpy_get_device(self, nwkid = None, ieee=None)
        # will return None if not found
        # will return (nwkid, ieee) if found ( nwkid and ieee are numbers)
        self.log.logging("TransportZigpy", "Debug", "Appbellows - get_device ieee:%s nwk:%s " % (ieee,nwk ))
#        self.log.logging("TransportZigpy", "Debug", "Appbellows - get_device current_list%s  " % (self.devices ))

        dev = None
        try:
            dev = super().get_device(ieee, nwk)
            
        except KeyError:
            if self.callBackGetDevice:
                if nwk is not None:
                    nwk = nwk.serialize()[::-1].hex()
                if ieee is not None:
                    ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
                self.log.logging("TransportZigpy", "Debug", "Appbellows - get_device calling callBackGetDevice %s (%s) %s (%s)" % (ieee,type(ieee),nwk, type(nwk)))
                zfd_dev = self.callBackGetDevice(ieee, nwk)
                if zfd_dev is not None:
                    (nwk, ieee) = zfd_dev
                    dev = self.add_device(t.EmberEUI64(t.uint64_t(ieee).serialize()),nwk)

        if dev is not None:
            # logging.debug("found device dev: %s" % (str(dev)))
            self.log.logging("TransportZigpy", "Debug", "Appbellows - get_device found device: %s" % dev)
            return dev
        
        logging.debug("get_device raise KeyError ieee: %s nwk: %s !!" %( ieee, nwk))
        raise KeyError

    def handle_join(self, nwk: t.EmberNodeId, ieee: t.EmberEUI64, parent_nwk: t.EmberNodeId) -> None:
        """
        Called when a device joins or announces itself on the network.
        """

        ieee = t.EmberEUI64(ieee)

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

    def get_zigpy_version(self):
        # This is a fake version number. This is just to inform the plugin that we are using bellows over Zigpy
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
        dst_addressing: Addressing,
    ) -> None:
        if sender.nwk == 0x0000:
            self.log.logging("TransportZigpy", "Debug", "handle_message from Controller Sender: %s Profile: %04x Cluster: %04x srcEp: %02x dstEp: %02x message: %s" %(
                str(sender.nwk), profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8")))
            super().handle_message(sender, profile, cluster, src_ep, dst_ep, message, dst_addressing=dst_addressing)

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
        # EmberConfigTxPowerMode - EZSP_CONFIG_TX_POWER_MODE in EzspConfigId
        # 0x00: Normal mode
        # 0x01: Enable boost power mode
        # 0x02: Enable the alternate transmitter output.
        # 0x03: Both 0x01 & 0x02
        if power > 0:
            await self.setConfigurationValue(t.EzspConfigId.CONFIG_TX_POWER_MODE,1)    
            self.log.logging("TransportZigpy", "Debug", "set_tx_power: boost power mode")
        else:
            await self.setConfigurationValue(t.EzspConfigId.CONFIG_TX_POWER_MODE,0)
            self.log.logging("TransportZigpy", "Debug", "set_tx_power: normal mode")

    async def set_led(self, mode):
        self.log.logging("TransportZigpy", "Debug", "set_led not available on EZSP")
#        if mode == 1:
#            await self._set_led_mode(led=0xFF, mode=bellows.commands.util.LEDMode.ON)
#        else:
#            await self._set_led_mode(led=0xFF, mode=bellows.commands.util.LEDMode.OFF)

    async def set_certification(self, mode):
        self.log.logging("TransportZigpy", "Debug", "set_certification not implemented yet")

    async def get_time_server(self):
        self.log.logging("TransportZigpy", "Debug", "get_time_server not implemented yet")

    async def set_time_server(self, newtime):
        self.log.logging("TransportZigpy", "Debug", "set_time_server not implemented yet")

    async def get_firmware_version(self):
        return self.bellows.version

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


    # MUST BE REMOVED WHEN INTEGRATED IN BELLOWS
    async def load_network_info(self, *, load_devices=False) -> None:
        ezsp = self._ezsp

        # (status,) = await ezsp.networkInit()
        # assert status == t.EmberStatus.SUCCESS

        status, node_type, nwk_params = await ezsp.getNetworkParameters()
        assert status == t.EmberStatus.SUCCESS

        node_info = self.state.node_information
        (node_info.nwk,) = await ezsp.getNodeId()
        (node_info.ieee,) = await ezsp.getEui64()
        node_info.logical_type = node_type.zdo_logical_type

        network_info = self.state.network_information
        network_info.extended_pan_id = nwk_params.extendedPanId
        network_info.pan_id = nwk_params.panId
        network_info.nwk_update_id = nwk_params.nwkUpdateId
        network_info.nwk_manager_id = nwk_params.nwkManagerId
        network_info.channel = nwk_params.radioChannel
        network_info.channel_mask = nwk_params.channels

        (status, security_level) = await ezsp.getConfigurationValue(
            ezsp.types.EzspConfigId.CONFIG_SECURITY_LEVEL
        )
        assert status == t.EmberStatus.SUCCESS
        network_info.security_level = security_level

        # Network key
        (status, key) = await ezsp.getKey(ezsp.types.EmberKeyType.CURRENT_NETWORK_KEY)
        assert status == t.EmberStatus.SUCCESS
        network_info.network_key = ezsp_key_to_zigpy_key(key, ezsp)

        # Security state
        (status, state) = await ezsp.getCurrentSecurityState()
        assert status == t.EmberStatus.SUCCESS

        # TCLK
        (status, key) = await ezsp.getKey(ezsp.types.EmberKeyType.TRUST_CENTER_LINK_KEY)
        assert status == t.EmberStatus.SUCCESS
        network_info.tc_link_key = ezsp_key_to_zigpy_key(key, ezsp)

        if (
            state.bitmask
            & ezsp.types.EmberCurrentSecurityBitmask.TRUST_CENTER_USES_HASHED_LINK_KEY
        ):
            network_info.stack_specific = {
                "ezsp": {"hashed_tclk": network_info.tc_link_key.key.serialize().hex()}
            }
            network_info.tc_link_key.key = KeyData(b"ZigBeeAlliance09")

        if not load_devices:
            return

        network_info.key_table = []

        for idx in range(0, 192):
            (status, key) = await ezsp.getKeyTableEntry(idx)

            if status == t.EmberStatus.INDEX_OUT_OF_RANGE:
                break
            elif status == t.EmberStatus.TABLE_ENTRY_ERASED:
                continue

            assert status == t.EmberStatus.SUCCESS

            network_info.key_table.append(
                bellows.zigbee.util.ezsp_key_to_zigpy_key(key, ezsp)
            )

        network_info.children = []
        network_info.nwk_addresses = {}

        for idx in range(0, 255 + 1):
            (status, nwk, eui64, node_type) = await ezsp.getChildData(idx)

            if status == t.EmberStatus.NOT_JOINED:
                continue

            network_info.children.append(eui64)
            network_info.nwk_addresses[eui64] = nwk

        for idx in range(0, 255 + 1):
            (nwk,) = await ezsp.getAddressTableRemoteNodeId(idx)
            (eui64,) = await ezsp.getAddressTableRemoteEui64(idx)

            # Ignore invalid NWK entries
            if nwk in EmberDistinguishedNodeId.__members__.values():
                continue

            network_info.nwk_addresses[eui64] = nwk
            
def ezsp_key_to_zigpy_key(key, ezsp):
    zigpy_key = zigpy.state.Key()
    zigpy_key.key = key.key

    if key.bitmask & ezsp.types.EmberKeyStructBitmask.KEY_HAS_SEQUENCE_NUMBER:
        zigpy_key.seq = key.sequenceNumber

    if key.bitmask & ezsp.types.EmberKeyStructBitmask.KEY_HAS_OUTGOING_FRAME_COUNTER:
        zigpy_key.tx_counter = key.outgoingFrameCounter

    if key.bitmask & ezsp.types.EmberKeyStructBitmask.KEY_HAS_INCOMING_FRAME_COUNTER:
        zigpy_key.rx_counter = key.incomingFrameCounter

    if key.bitmask & ezsp.types.EmberKeyStructBitmask.KEY_HAS_PARTNER_EUI64:
        zigpy_key.partner_ieee = key.partnerEUI64

    return zigpy_key


def zigpy_key_to_ezsp_key(zigpy_key, ezsp):
    key = ezsp.types.EmberKeyStruct()
    key.key = zigpy_key.key
    key.bitmask = ezsp.types.EmberKeyStructBitmask(0)

    if zigpy_key.seq is not None:
        key.seq = zigpy_key.seq
        key.bitmask |= ezsp.types.EmberKeyStructBitmask.KEY_HAS_SEQUENCE_NUMBER

    if zigpy_key.tx_counter is not None:
        key.outgoingFrameCounter = zigpy_key.tx_counter
        key.bitmask |= ezsp.types.EmberKeyStructBitmask.KEY_HAS_OUTGOING_FRAME_COUNTER

    if zigpy_key.rx_counter is not None:
        key.outgoingFrameCounter = zigpy_key.rx_counter
        key.bitmask |= ezsp.types.EmberKeyStructBitmask.KEY_HAS_INCOMING_FRAME_COUNTER

    if zigpy_key.partner_ieee is not None:
        key.partnerEUI64 = zigpy_key.partner_ieee
        key.bitmask |= ezsp.types.EmberKeyStructBitmask.KEY_HAS_PARTNER_EUI64

    return key

def extract_versioning_for_plugin( brd_manuf, brd_name, version):
    FirmwareBranch = "99" # Not found in the Table.
    if brd_manuf == 'Elelabs':
        if 'ELU01' in brd_name:
            FirmwareBranch = "31"
        elif 'ELR02' in brd_name:
            FirmwareBranch = "30" 
            
    # 6.10.3.0 build 297    
    FirmwareMajorVersion = (version[: 2])
    FirmwareMajorVersion = "%02d" %int(FirmwareMajorVersion.replace('.',''))
    FirmwareVersion = version[ 2:8]
    FirmwareVersion = FirmwareVersion.replace(' ','')
    FirmwareVersion = "%04d" %int(FirmwareVersion.replace('.',''))
        
    return FirmwareBranch, FirmwareMajorVersion, FirmwareVersion
   

from bellows.types import basic


class EmberDistinguishedNodeId(basic.enum16):
    """A distinguished network ID that will never be assigned to any node"""

    # This value is used when getting the remote node ID from the address or binding
    # tables. It indicates that the address or binding table entry is currently in use
    # and network address discovery is underway.
    DISCOVERY_ACTIVE = 0xFFFC

    # This value is used when getting the remote node ID from the address or binding
    # tables. It indicates that the address or binding table entry is currently in use
    # but the node ID corresponding to the EUI64 in the table is currently unknown.
    UNKNOWN = 0xFFFD

    # This value is used when setting or getting the remote node ID in the address table
    # or getting the remote node ID from the binding table. It indicates that the
    # address or binding table entry is not in use.
    TABLE_ENTRY_UNUSED = 0xFFFF
