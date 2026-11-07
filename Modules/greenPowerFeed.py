#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Green Power pairing feed: what happens while a Green Power device (GPD) is
being paired, for Admin → Provisioning (/zgp-pairing), without the logs.

A GPD gives no feedback, and some have to be stepped through the channels by
hand until they reach the network's: the first GPDF heard tells the user to
stop. Events, newest last, in memory only (the last FEED_SIZE):

    window      the commissioning window opened, closed, or was not opened
                because GreenPowerEnable is off (9e04)
    heard       a GPDF reached the network (9e03), with a hint when it tells
                why nothing gets paired
    commissioned / widgets / no-widget / removed
                the pairing steps that follow (9e00, widget creation, 9e02).
                commissioned carries the hint leave-pairing: a unidirectional
                GPD is not told it is paired, the user takes it out of its
                commissioning mode

Written from the forwarder thread (decoders) and the heartbeat (widgets),
read from the Domoticz thread (WebServer): every access holds the lock.
"""

import threading
import time
from collections import deque

FEED_SIZE = 50
GP_FEED_ATTRIBUTE = "gp_pairing_feed"

# 9e03 flags (Classes/ZigpyTransport/plugin_encoders.py GP_HEARD_*)
HEARD_KNOWN = 0x01
HEARD_WINDOW_OPEN = 0x02
HEARD_ENCRYPTED = 0x04
HEARD_VIA_PROXY = 0x08
HEARD_RSSI = 0x10

# 9e04 states (plugin_encoders.py GP_WINDOW_*)
WINDOW_STATES = {0x00: "closed", 0x01: "opened", 0x02: "disabled"}

GPD_COMMISSIONING = 0xE0
GPD_COMMISSIONING_COMMANDS = {0xE0, 0xE1, 0xE2, 0xE3}

# GPD command names (Green Power specification, as zigpy.zgp.types.GPDCommandID)
GPD_COMMAND_NAMES = {
    0x00: "Identify",
    0x20: "Off",
    0x21: "On",
    0x22: "Toggle",
    0x23: "Release",
    0x30: "Move Up",
    0x31: "Move Down",
    0x32: "Step Up",
    0x33: "Step Down",
    0x34: "Level Control Stop",
    0x35: "Move Up With On/Off",
    0x36: "Move Down With On/Off",
    0x37: "Step Up With On/Off",
    0x38: "Step Down With On/Off",
    0x60: "Press 1 of 1",
    0x61: "Release 1 of 1",
    0x62: "Press 1 of 2",
    0x63: "Release 1 of 2",
    0x64: "Press 2 of 2",
    0x65: "Release 2 of 2",
    0x66: "Short Press 1 of 1",
    0x67: "Short Press 1 of 2",
    0x68: "Short Press 2 of 2",
    0x69: "8-bit Vector Press",
    0x6A: "8-bit Vector Release",
    0xA0: "Attribute Reporting",
    0xA2: "Multi-cluster Reporting",
    0xE0: "Commissioning",
    0xE1: "Decommissioning",
    0xE2: "Success",
    0xE3: "Channel Request",
}
for _scene in range(16):
    GPD_COMMAND_NAMES[0x10 + _scene] = "Recall Scene %d" % _scene


def gp_src_id(ieee):
    """0xC220BD02 from the synthetic IEEE of a SrcID GPD (its last 8 hex digits)."""
    return "0x%s" % ieee[-8:].upper()


def heard_hint(command_id, flags):
    """
    Why a GPDF heard leads, or not, to a pairing:

        commissioning   a Commissioning while the window is open: pairing follows
        window-closed   a Commissioning while the window is closed: refused
        still-pairing   a Commissioning from a GPD already paired: it is still in
                        its commissioning mode, where some GPDs step to the next
                        channel at each press
        not-pairing     an unpaired GPD sending a normal command: it reaches the
                        network, but is not in its commissioning mode
        encrypted       an unpaired GPD's encrypted frame: nothing to read
    """
    if flags & HEARD_KNOWN:
        return "still-pairing" if command_id == GPD_COMMISSIONING else None
    if flags & HEARD_ENCRYPTED:
        return "encrypted"
    if command_id == GPD_COMMISSIONING:
        return "commissioning" if flags & HEARD_WINDOW_OPEN else "window-closed"
    if command_id not in GPD_COMMISSIONING_COMMANDS:
        return "not-pairing"
    return None


class GreenPowerFeed:
    def __init__(self, size=FEED_SIZE):
        self._lock = threading.Lock()
        self._events = deque(maxlen=size)
        self._seq = 0
        self._window = {"State": None, "Until": None}

    def add(self, event, now=None, **fields):
        with self._lock:
            self._seq += 1
            entry = {"Seq": self._seq, "Time": int(time.time() if now is None else now), "Event": event}
            entry.update(fields)
            self._events.append(entry)
            return entry

    def window(self, state, seconds, now=None):
        now = time.time() if now is None else now
        with self._lock:
            self._window = {
                "State": state,
                "Until": int(now + seconds) if state == "opened" and seconds else None,
            }
        return self.add("window", now=now, State=state, Seconds=seconds)

    def heard(self, ieee, command_id, flags, proxy, rssi, lqi, now=None):
        encrypted = bool(flags & HEARD_ENCRYPTED)
        return self.add(
            "heard",
            now=now,
            IEEE=ieee,
            SrcId=gp_src_id(ieee),
            Command=None if encrypted else "%02x" % command_id,
            CommandName=None if encrypted else GPD_COMMAND_NAMES.get(command_id, "0x%02x" % command_id),
            Known=bool(flags & HEARD_KNOWN),
            WindowOpen=bool(flags & HEARD_WINDOW_OPEN),
            Encrypted=encrypted,
            Proxy=proxy if flags & HEARD_VIA_PROXY else None,
            Rssi=rssi if flags & HEARD_RSSI else None,
            Lqi=lqi,
            Hint=heard_hint(command_id, flags),
        )

    def snapshot(self, since=0, now=None):
        """Window state and the events after `since` (a Seq), oldest first."""
        now = time.time() if now is None else now
        with self._lock:
            window = dict(self._window)
            events = [dict(e) for e in self._events if e["Seq"] > since]
            seq = self._seq
        if window["State"] == "opened" and window["Until"] is not None and now >= window["Until"]:
            # zigpy closes the window on its own when it expires
            window = {"State": "closed", "Until": None}
        return {"Window": window, "Seq": seq, "Events": events}


def gp_feed(self):
    """The plugin's Green Power pairing feed, created on first use."""
    feed = getattr(self, GP_FEED_ATTRIBUTE, None)
    if feed is None:
        feed = GreenPowerFeed()
        setattr(self, GP_FEED_ATTRIBUTE, feed)
    return feed
