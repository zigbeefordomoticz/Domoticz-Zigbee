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
    Module: health_settings.py

    Description: How long a device may stay silent before the plugin stops
    believing it is alive.

    The decision is kept free of any plugin dependency so that it can be unit
    tested on its own: everything it needs is passed in by checkHealth().
"""

# Health values carrying no evidence that the device is gone. A plugin start
# resets Health to "" (see Modules/database.py, CheckDeviceList) and checkHealth()
# sets "unknown" when a device has no usable Stamp, so both have to be considered
# alongside "Live" - otherwise a device that went silent while the plugin was
# down would stay unflagged until it reports once, even though the persisted
# LastSeen already tells us it is stale.
HEALTH_UNDETERMINED = ("", "unknown")

# States from which a device may be flagged as not seen any more. "Not Reachable",
# "Disabled" and an already flagged device are deliberately left alone.
HEALTH_STALE_CANDIDATES = ("Live",) + HEALTH_UNDETERMINED

HEALTH_DEVICE_PARAMETERS = {
    "HealthTimeOut": {
        "description": (
            "Number of seconds without any message from this device after which its Health is "
            "flagged as not seen any more. Overrides the plugin wide HealthTimeOut setting; "
            "leave it unset or at 0 to follow that setting."
        )
    },
}


def _as_positive_int(value):
    """Return value as a positive int, or 0 when it is unusable."""

    try:
        value = int(value)
    except (TypeError, ValueError):
        return 0

    return value if value > 0 else 0


def device_health_timeout(device, plugin_timeout):
    """Return the number of seconds of silence tolerated for this device.

    The device "HealthTimeOut" parameter wins when set to a usable non-zero value,
    so a very quiet device (a battery sensor reporting a couple of times a day)
    can depart from the plugin wide setting without having to relax it for every
    device. An absent, zero or malformed parameter falls back on plugin_timeout,
    which is itself allowed to be 0 to switch the check off altogether.
    """

    device_timeout = _as_positive_int(device.get("Param", {}).get("HealthTimeOut", 0))

    return device_timeout or _as_positive_int(plugin_timeout)


def is_health_timed_out(device, timeout, now):
    """Return True when nothing has been received from this device for longer than timeout.

    timeout is the already resolved value from device_health_timeout(), so the
    caller can report it without resolving it twice.
    """

    if not timeout:
        return False

    if device.get("Health") not in HEALTH_STALE_CANDIDATES:
        return False

    # A device we have never heard of has no reference point to measure silence
    # from; leave it to the pairing and ping logic rather than flagging it here.
    last_seen = _as_positive_int(device.get("Stamp", {}).get("LastSeen", 0))
    if not last_seen:
        return False

    return now > (last_seen + timeout)
