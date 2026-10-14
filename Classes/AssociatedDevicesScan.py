#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2026
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
    Class: AssociatedDevicesScan

    Description: Collects the Associated Devices table of every coordinator and
        router, as the second half of a zigpy topology scan.

        zigpy's topology scan collects two tables, Neighbors (Mgmt_Lqi_req) and
        Routes (Mgmt_Rtg_req). The Zigbee specification also exposes the
        associated device list -- a router's children -- but only through the
        extended address response (NWK_addr_req with RequestType 0x01), which
        zigpy never asks for. The plugin already owns that request, its decoder
        and its paging, so it collects the third table itself and files it with
        the zigpy scan it belongs to.

        This runs *after* zigpy's scan has finished, never alongside it: zigpy
        paces itself with a 1.0-1.5 s sleep after every request precisely to
        avoid flooding the mesh, and two scanners interrogating the same routers
        at once would undo that and make a timeout impossible to attribute.

        No thread and no event loop of its own: it is a state machine ticked
        from the plugin heartbeat, one request in flight at a time, which is the
        same shape as Classes/NetworkMap.py.
"""

import time
from collections.abc import Mapping

from Modules.associated_devices import (EXTENDED_REQUEST_TYPE, is_last_page,
                                        nodes_to_scan, split_device_list)
from Modules.zigateConsts import MAX_LOAD_ZIGATE

# Phases, mirroring NetworkMap's _NetworkMapPhase
PHASE_IDLE = 0
PHASE_RUNNING = 1

# Heartbeats to wait for one node before giving up on it. HEARTBEAT is 5 s, so
# 2 ticks is the 10 s NetworkMap allows itself for an LQI request (LQIticks < 2).
NODE_TICK_BUDGET = 2

# Ceiling for the whole collection, as a multiple of what the node list should
# need. A node whose pages never stop, or a radio that stops answering without
# the transport noticing, must not keep the scan -- and the report -- pending
# forever.
SCAN_BUDGET_FACTOR = 3

STATUS_REQUIRED = "ScanRequired"
STATUS_WAITING = "WaitingResponse"
STATUS_RECEIVED = "Received"
STATUS_TIMEDOUT = "TimedOut"


class AssociatedDevicesScan:

    def __init__(self, PluginConf, ZigateComm, ListOfDevices, DeviceConfig, log,
                 send_request, on_completed=None):
        self.pluginconf = PluginConf
        self.ControllerLink = ZigateComm
        self.ListOfDevices = ListOfDevices
        # DeviceConf, not DeviceConfig: every ZDP request issued here goes
        # through raw_APS_request() -> device_listening_on_iddle(), which reads
        # self.DeviceConf. Getting the name wrong broke the first ZDP request of
        # a scan with an AttributeError that escaped as an HTTP status 0.
        self.DeviceConf = DeviceConfig
        self.log = log

        # zdp_NWK_address_request, handed in rather than imported: importing
        # Zigbee.zdpCommands pulls the real Modules.* chain into whatever imports
        # this class, which breaks unrelated tests through the stubs
        # tests/conftest.py installs. Passing it keeps this state machine
        # testable in the ordinary pytest session.
        self.send_request = send_request

        # Called with the collected {nwkid: [children]} when the collection
        # completes, or with None when it is abandoned. Injected rather than
        # imported so this class never reaches ZigpyTopology, and so stays
        # importable -- and testable -- without zigpy installed.
        self.on_completed = on_completed

        self.phase = PHASE_IDLE
        self.nodes = {}
        self.collected = {}
        self.current = None
        self.node_ticks = 0
        self.scan_ticks = 0
        self.scan_budget = 0
        self.started_at = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def in_progress(self):
        """True while this collection is the reason a scan is still running."""
        return self.phase == PHASE_RUNNING

    def start_scan(self):
        """Begin asking. Returns False when there is nothing to ask."""
        self.nodes = {nwkid: STATUS_REQUIRED for nwkid in nodes_to_scan(self.ListOfDevices)}
        self.collected = {}
        self.current = None
        self.node_ticks = 0
        self.scan_ticks = 0
        self.scan_budget = SCAN_BUDGET_FACTOR * (NODE_TICK_BUDGET + 1) * max(len(self.nodes), 1)
        self.started_at = time.time()

        if not self.nodes:
            self.logging("Debug", "start_scan - no coordinator or router to ask")
            self.phase = PHASE_IDLE
            return False

        self.logging("Status", "Z4D starts collecting Associated Devices from %s node(s)" % len(self.nodes))
        self.phase = PHASE_RUNNING
        return True

    def continue_scan(self):
        """One heartbeat of the collection."""
        if self.phase != PHASE_RUNNING:
            return

        if self.ControllerLink.loadTransmit() >= MAX_LOAD_ZIGATE:
            # Queue is busy; wait without spending the node's budget on it.
            self.logging("Debug", "continue_scan - deferring, transmit queue is loaded")
            return

        self.scan_ticks += 1
        if self.scan_ticks > self.scan_budget:
            self.abort("budget of %s ticks exhausted" % self.scan_budget)
            return

        if self.current is not None:
            self.node_ticks += 1
            if self.node_ticks < NODE_TICK_BUDGET:
                return
            self.logging("Debug", "continue_scan - %s did not answer" % self.current)
            self.nodes[self.current] = STATUS_TIMEDOUT
            self.current = None

        # Loop rather than one node per tick: a node that cannot be asked at all
        # must not cost a heartbeat. Each turn either sends a request and
        # returns, or takes one node out of STATUS_REQUIRED, so this terminates.
        while True:
            next_nwkid = next((nwkid for nwkid, status in self.nodes.items() if status == STATUS_REQUIRED), None)
            if next_nwkid is None:
                self.finish()
                return
            if self._request(next_nwkid):
                return

    def _request(self, nwkid):
        """Ask one node. False when it could not be asked at all."""
        device = self.ListOfDevices.get(nwkid) or {}
        ieee = device.get("IEEE") if isinstance(device, Mapping) else None
        if not ieee:
            # Nothing to address the request with. NWK_addr_req asks by IEEE.
            self.logging("Debug", "_request - %s has no IEEE recorded, skipping" % nwkid)
            self.nodes[nwkid] = STATUS_TIMEDOUT
            return False

        self.logging("Debug", "_request - asking %s for its associated devices" % nwkid)
        self.nodes[nwkid] = STATUS_WAITING
        self.current = nwkid
        self.node_ticks = 0
        self.send_request(self, nwkid, ieee, u8RequestType=EXTENDED_REQUEST_TYPE, u8StartIndex="00")
        return True

    def finish(self):
        answered = sum(1 for status in self.nodes.values() if status == STATUS_RECEIVED)
        children = sum(len(devices) for devices in self.collected.values())
        self.logging(
            "Status",
            "Associated Devices collected: %s of %s node(s) answered, %s child(ren) reported in %s s"
            % (answered, len(self.nodes), children, int(time.time() - (self.started_at or time.time()))),
        )
        self._report(dict(self.collected))

    def abort(self, reason):
        """Give up, and let the scan be filed without this table.

        Reporting None rather than what was collected so far is deliberate: a
        table listed in a scan is a table the backend asked for in full. Half of
        one would read as routers with no children, which is a different claim.
        """
        if self.phase == PHASE_IDLE:
            return
        self.logging("Log", "Associated Devices collection abandoned (%s)" % reason)
        self._report(None)

    def _report(self, associated_devices):
        self.phase = PHASE_IDLE
        self.current = None
        self.nodes = {}
        self.collected = {}
        if self.on_completed:
            self.on_completed(associated_devices)

    # ------------------------------------------------------------------
    # Response, handed over by Decode8040()
    # ------------------------------------------------------------------
    def response_received(self, nwkid, num_assoc_devices, start_index, device_list):
        """One extended address response, for a node this scan asked.

        Returns False for a response this scan did not ask for -- the TopologyV2
        scan issues the same request and must keep working on its own.
        """
        if self.phase != PHASE_RUNNING or nwkid not in self.nodes:
            return False

        children = split_device_list(device_list)
        self.collected.setdefault(nwkid, [])
        for child in children:
            if child not in self.collected[nwkid]:
                self.collected[nwkid].append(child)

        if not is_last_page(num_assoc_devices, start_index, len(children)):
            # Decode8040() has already asked for the next page. Give the node a
            # fresh budget for it rather than timing it out mid-list.
            self.logging("Debug", "response_received - %s has more associated devices to come" % nwkid)
            self.node_ticks = 0
            return True

        self.logging(
            "Debug", "response_received - %s reported %s associated device(s)" % (nwkid, len(self.collected[nwkid]))
        )
        self.nodes[nwkid] = STATUS_RECEIVED
        if self.current == nwkid:
            self.current = None
        return True

    def logging(self, logType, message):
        self.log.logging("NetworkMap", logType, message)
