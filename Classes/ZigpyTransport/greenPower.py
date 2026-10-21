#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: badz & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license
"""
greenPower.py — zigpy Green Power events to plugin frames.

zigpy (> 2.3.0, #1848) commissions Green Power devices (GPD) itself and
reports them as application events, and each accepted GPDF as a
`gp_command_received` event on the device. A GPD sends no Device_annce and
no ZCL, so packet_received() never sees one: this listener is the only way
the plugin learns about them.

Events are turned into 9exx plugin frames and handed to callBackFunction
(Transport.receiveData), which only queues them for the forwarder thread:
nothing here blocks the event loop.

    device_initialized(dev)    new GPD                → 9e00
    device_reinterviewed(dev)  GPD commissioned again → 9e00 (recommissioned)
    device_removed(dev)        GPD removed            → 9e02
    gp_command_received        GPD command            → 9e01

The application events also fire for Zigbee devices; they are ignored here.
device_joined is not used: it fires before zigpy finalises the device, and
device_initialized follows immediately with the final object.

zigpy logs listener exceptions at DEBUG only, so every handler logs its own.
"""

import traceback

import zigpy.device

from Classes.ZigpyTransport.plugin_encoders import (
    build_plugin_9e00_frame_content, build_plugin_9e01_frame_content,
    build_plugin_9e02_frame_content)

# Absent from zigpy before 2.3.0
GREEN_POWER_DEVICE = getattr(zigpy.device, "GreenPowerDevice", None)
GP_COMMAND_EVENT = "gp_command_received"


def is_green_power_device(device):
    return GREEN_POWER_DEVICE is not None and isinstance(device, GREEN_POWER_DEVICE)


class GreenPowerListener:
    """zigpy application listener for Green Power devices."""

    def __init__(self, app):
        self._app = app
        # ieee -> unsubscribe callable of the device's gp_command_received handler
        self._unsubscribe = {}

    def attach(self, device):
        """Forward the device's commands. Also used for GPDs restored at startup."""
        self.detach(device.ieee)
        self._unsubscribe[device.ieee] = device.on_event(GP_COMMAND_EVENT, lambda event: self._on_command(device, event))

    def detach(self, ieee):
        unsubscribe = self._unsubscribe.pop(ieee, None)
        if unsubscribe is not None:
            unsubscribe()

    def device_initialized(self, device):
        if not is_green_power_device(device):
            return
        try:
            self._app.log.logging("GreenPower", "Status", "Green Power device commissioned %s" % (device,))
            self.attach(device)
            self._app.callBackFunction(build_plugin_9e00_frame_content(self._app, device, recommissioned=False))
        except Exception as e:
            self._log_error("device_initialized", device, e)

    def device_reinterviewed(self, device):
        if not is_green_power_device(device):
            return
        try:
            self._app.log.logging("GreenPower", "Status", "Green Power device commissioned again %s" % (device,))
            # Replaces the handler of the previous device object
            self.attach(device)
            self._app.callBackFunction(build_plugin_9e00_frame_content(self._app, device, recommissioned=True))
        except Exception as e:
            self._log_error("device_reinterviewed", device, e)

    def device_removed(self, device):
        if not is_green_power_device(device):
            return
        try:
            self._app.log.logging("GreenPower", "Status", "Green Power device removed %s" % (device,))
            self.detach(device.ieee)
            self._app.callBackFunction(build_plugin_9e02_frame_content(self._app, device))
        except Exception as e:
            self._log_error("device_removed", device, e)

    def _on_command(self, device, event):
        try:
            self._app.log.logging("GreenPower", "Debug", "Green Power command 0x%02x from %s" % (event.command_id, device))
            self._app.callBackFunction(
                build_plugin_9e01_frame_content(self._app, device, event.endpoint_id, event.command_id, event.command)
            )
        except Exception as e:
            self._log_error("gp_command_received", device, e)

    def _log_error(self, event_name, device, error):
        self._app.log.logging("GreenPower", "Error", "Green Power %s for %s failed: %s\n%s" % (
            event_name, device, error, traceback.format_exc()))


def register_green_power_listener(app):
    """Register the listener once, when zigpy supports Green Power."""
    if getattr(app, "green_power", None) is None or getattr(app, "z4d_gp_listener", None) is not None:
        return
    app.z4d_gp_listener = GreenPowerListener(app)
    app.add_listener(app.z4d_gp_listener)
