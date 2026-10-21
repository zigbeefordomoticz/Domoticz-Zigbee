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
PluginStore — a named, versioned set of keyed plugin records persisted next
to ListOfDevices, for data that must not live in ListOfDevices.

Persistence is a PersistedDocument (Classes/PersistedDocument.py):

- JSON file ``<pluginData>/<name>-<HardwareID>.json``;
- Domoticz configuration record ``PluginStore-<name>``;
- payload ``{"FormatVersion": int, "TimeStamp": float, "Records": {key: record}}``,
  records JSON serialisable;
- the engine's rules: most recent copy wins, never written unless loaded,
  read-only when unreadable or newer, upgrade callable for older versions,
  atomic file write, content never logged.

On top of it, the store:

- reads and changes records under a lock and hands out copies, as decoders
  (forwarder thread) and flushes (Domoticz thread) run concurrently;
- writes only when something changed since the last flush.
"""

import copy
import threading
from pathlib import Path

from Classes.PersistedDocument import EnvelopeCodec, PersistedDocument

STORE_CONFIG_PREFIX = "PluginStore-"
STORE_CONTENT_KEY = "Records"


def store_file_path(name):
    return lambda plugin: Path(plugin.pluginconf.pluginConf["pluginData"]) / ("%s-%s.json" % (name, plugin.HardwareID))


class PluginStore:

    def __init__(self, name, version, upgrade=None):
        """
        Args:
            name:    Store name, used for the file and the Domoticz record.
            version: Record format version this plugin writes and reads.
            upgrade: Optional callable(records, from_version) -> records,
                     applied when an older version is loaded.
        """
        self.name = name
        self._document = PersistedDocument(
            "PluginStore %s" % name,
            version,
            file_path=store_file_path(name),
            config_key=STORE_CONFIG_PREFIX + name,
            codec=EnvelopeCodec(STORE_CONTENT_KEY),
            upgrade=upgrade,
        )
        self._records = {}
        self._lock = threading.RLock()
        self._dirty = False

    @property
    def writable(self):
        return self._document.writable

    # ── Records ─────────────────────────────────────────────────────────────

    def __contains__(self, key):
        with self._lock:
            return key in self._records

    def __len__(self):
        with self._lock:
            return len(self._records)

    def keys(self):
        with self._lock:
            return list(self._records)

    def get(self, key, default=None):
        with self._lock:
            if key not in self._records:
                return default
            return copy.deepcopy(self._records[key])

    def set(self, key, record):
        with self._lock:
            self._records[key] = copy.deepcopy(record)
            self._dirty = True

    def update(self, key, fields):
        """Merge fields into an existing record. Returns False if there is none."""
        with self._lock:
            if key not in self._records:
                return False
            self._records[key].update(copy.deepcopy(fields))
            self._dirty = True
            return True

    def delete(self, key):
        with self._lock:
            if self._records.pop(key, None) is not None:
                self._dirty = True

    def snapshot(self):
        with self._lock:
            return copy.deepcopy(self._records)

    # ── Persistence ─────────────────────────────────────────────────────────

    def load(self, plugin):
        """Load the most recent copy. Returns True when the store is writable."""
        records = self._document.load(plugin)
        with self._lock:
            self._records = records if records is not None else {}
            # An upgraded store is saved in the new format at the next flush
            self._dirty = self._document.upgraded
        return self.writable

    def flush(self, plugin, force=False):
        """Write the store if it changed since the last flush (or force)."""
        if not self.writable or not (self._dirty or force):
            return

        with self._lock:
            records = copy.deepcopy(self._records)
            self._dirty = False

        if not self._document.save(plugin, records):
            # Retry at the next flush
            self._dirty = True
