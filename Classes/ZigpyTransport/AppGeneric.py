#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: badz & pipiche38
#

import binascii
import contextlib
import logging
import time

import zigpy.application
import zigpy.backups
import zigpy.config as zigpy_conf
import zigpy.device
import zigpy.exceptions
import zigpy.types as t
from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_8002_frame_content, build_plugin_8014_frame_content,
    build_plugin_8047_frame_content, build_plugin_8048_frame_content)
from zigpy.backups import NetworkBackup

LOGGER = logging.getLogger(__name__)

async def _load_db(self) -> None:
    pass

async def initialize(self, *, auto_form: bool = False, force_form: bool = False):
    """
    Starts the network on a connected radio, optionally forming one with random
    settings if necessary.
    """
    self.log.logging("TransportZigpy", "Debug", "AppGeneric:initialize auto_form: %s force_form: %s Class: %s" %( auto_form, force_form, type(self)))

    if "autoRestore" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["autoRestore"]:
        # In case of a fresh coordinator, let's load the latest backup
        _retreived_backup = _retreive_backup( self )
        if _retreived_backup:
            LOGGER.info("Last backup retreived: %s" % zigpy.backups.NetworkBackup( _retreived_backup ))
            self.backups.add_backup( backup = NetworkBackup.from_dict( _retreived_backup ))

    if force_form:

        with contextlib.suppress(Exception):
            if "autoRestore" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["autoRestore"]:
                self.log.logging( "Zigpy", "Status","Restoring the most recent network backup")
                await self.backups.restore_backup(self.backups.backups[-1])
            else:
                await super(type(self),self).form_network()

    try:
        await self.load_network_info(load_devices=False)

    except zigpy.exceptions.NetworkNotFormed:
        LOGGER.info("Network is not formed")

        if not auto_form:
            raise

        self.log.logging( "Zigpy", "Status","Forming a new network")
        await super(type(self),self).form_network()

        if not self.backups.backups:
            # Form a new network if we have no backup
            self.log.logging( "Zigpy", "Status","Forming a new network")
            await self.form_network()
        else:
            # Otherwise, restore the most recent backup
            self.log.logging( "Zigpy", "Status","Restoring the most recent network backup")
            await self.backups.restore_backup(self.backups.backups[-1])

        await self.load_network_info(load_devices=True)

    LOGGER.debug("Network info: %s", self.state.network_info)
    LOGGER.debug("Node info   : %s", self.state.node_info)

    await self.start_network()
    

def get_device(self, ieee=None, nwk=None):
    # LOGGER.debug("get_device nwk %s ieee %s" % (nwk, ieee))
    # self.callBackGetDevice is set to zigpy_get_device(self, nwkid = None, ieee=None)
    # will return None if not found
    # will return (nwkid, ieee) if found ( nwkid and ieee are numbers)
    dev = None
    try:
        dev = super(type(self),self).get_device(ieee, nwk)
        # We have found in Zigpy db.
        # We might have to check that the plugin and zigpy Dbs are in sync
        # Let's check if the tupple (dev.ieee, dev.nwk ) are aligned with plugin Db
        _update_nkdids_if_needed(self, dev.ieee, dev.nwk )
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

    LOGGER.debug("AppZnp get_device raise KeyError ieee: %s nwk: %s !!" %( ieee, nwk))
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
        LOGGER.debug("New device 0x%04x (%s) joined the network", nwk, ieee)

    if dev.nwk != nwk:
        dev.nwk = nwk
        _update_nkdids_if_needed(self, ieee, dev.nwk )
        LOGGER.debug("Device %s changed id (0x%04x => 0x%04x)", ieee, dev.nwk, nwk)


def _update_nkdids_if_needed( self, ieee, new_nwkid ):
    _ieee = "%016x" % t.uint64_t.deserialize(ieee.serialize())[0]
    _nwk = new_nwkid.serialize()[::-1].hex()
    self.callBackUpdDevice(_ieee, _nwk)

def get_device_ieee(self, nwk):
    # Call from the plugin to retreive the ieee
    # we assumed nwk as an hex string
    try:
        dev = super(type(self),self).get_device( nwk=int(nwk,16))
        LOGGER.debug("AppZnp get_device  nwk: %s returned %s" %( nwk, dev))
    except KeyError:
        LOGGER.debug("AppZnp get_device raise KeyError nwk: %s !!" %( nwk))
        return None
    if dev.ieee:
        return "%016x" % t.uint64_t.deserialize(dev.ieee.serialize())[0]
    return None

def handle_leave(self, nwk, ieee):
    self.log.logging("TransportZigpy", "Debug","handle_leave (0x%04x %s)" %(nwk, ieee))
    plugin_frame = build_plugin_8048_frame_content(self, ieee)
    self.callBackFunction(plugin_frame)
    super(type(self),self).handle_leave(nwk, ieee)

def get_zigpy_version(self):
    # This is a fake version number. This is just to inform the plugin that we are using ZNP over Zigpy
    LOGGER.debug("get_zigpy_version ake version number. !!")
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
        #self.super().handle_message(sender, profile, cluster, src_ep, dst_ep, message)
        super(type(self),self).handle_message(sender, profile, cluster, src_ep, dst_ep, message)

    if cluster == 0x8036:
        # This has been handle via on_zdo_mgmt_permitjoin_rsp()
        self.log.logging("TransportZigpy", "Debug", "handle_message 0x8036: %s Profile: %04x Cluster: %04x srcEp: %02x dstEp: %02x message: %s" %(
            str(sender.nwk), profile, cluster, src_ep, dst_ep, binascii.hexlify(message).decode("utf-8")))
        self.callBackFunction( build_plugin_8014_frame_content(self, str(sender), binascii.hexlify(message).decode("utf-8") ) )
        super(type(self),self).handle_message(sender, profile, cluster, src_ep, dst_ep, message)
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


def _retreive_backup( self ):
    from Modules.zigpyBackup import handle_zigpy_retreive_last_backup
    
    LOGGER.debug("Retreiving last backup")
    return handle_zigpy_retreive_last_backup( self )
