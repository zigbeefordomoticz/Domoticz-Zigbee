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
PluginStore — a named, versioned set of plugin records persisted next to
ListOfDevices, for data that must not live in ListOfDevices.

Persistence follows the device list:

- a JSON file ``<pluginData>/<name>-<HardwareID>.json``, written atomically,
  with versioned backups rotated at load (``numDeviceListVersion``);
- the Domoticz configuration record ``PluginStore-<name>`` when
  ``useDomoticzDb`` and ``storeDomoticzDb`` are set and the Domoticz
  database is available.

At load the most recent copy wins (``TimeStamp`` inside the payload).
Payload: ``{"Version": int, "TimeStamp": float, "Records": {key: record}}``.
Records must be JSON serialisable.

Safety rules:

- A store is written only after a successful load. A store whose copies
  cannot be read, or were written by a newer plugin (``Version`` above the
  supported one), stays read-only for the session: nothing overwrites it.
- Records are never logged, only counts: a store may hold secrets.
- Records are read and changed under a lock, and handed out as copies, as
  decoders (forwarder thread) and flushes (Domoticz thread) run concurrently.
- A flush writes only when something changed since the last one.
"""

import contextlib
import copy
import json
import os
import threading
import time
from pathlib import Path

from Modules.domoticzAbstractLayer import getConfigItem, setConfigItem
from Modules.tools_domoticz import is_domoticz_db_available
from Modules.tools_files import rotate_file_versions

STORE_CONFIG_PREFIX = "PluginStore-"
STORE_CONFIG_ATTRIBUTE = "Records"


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
        self.version = version
        self._upgrade = upgrade
        self._records = {}
        self._lock = threading.RLock()
        self._dirty = False
        self.writable = False

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

    def file_path(self, plugin):
        return Path(plugin.pluginconf.pluginConf["pluginData"]) / ("%s-%s.json" % (self.name, plugin.HardwareID))

    def config_key(self):
        return STORE_CONFIG_PREFIX + self.name

    def load(self, plugin):
        """Load the most recent copy. Returns True when the store is writable."""
        self.writable = False
        file_path = self.file_path(plugin)

        candidates = []
        file_unreadable = False
        if os.path.isfile(file_path):
            payload = self._read_file(plugin, file_path)
            if payload is None:
                file_unreadable = True
            else:
                candidates.append(("file", payload))

        if plugin.pluginconf.pluginConf.get("useDomoticzDb"):
            payload = self._read_domoticz(plugin)
            if payload is not None:
                candidates.append(("Domoticz", payload))

        if not candidates:
            if file_unreadable:
                plugin.log.logging("Database", "Error", "PluginStore %s - %s cannot be read and no other copy exists, store left untouched for this session" % (
                    self.name, file_path))
                return False
            # Nothing stored yet
            self._set_records({})
            self.writable = True
            return True

        source, payload = max(candidates, key=lambda candidate: candidate[1]["TimeStamp"])
        stored_version = payload["Version"]
        if stored_version > self.version:
            plugin.log.logging("Database", "Error", "PluginStore %s - stored version %s is newer than supported %s (plugin downgrade?), store left untouched for this session" % (
                self.name, stored_version, self.version))
            return False

        records = payload["Records"]
        if stored_version < self.version:
            if self._upgrade is None:
                plugin.log.logging("Database", "Error", "PluginStore %s - no upgrade from version %s to %s, store left untouched for this session" % (
                    self.name, stored_version, self.version))
                return False
            records = self._upgrade(records, stored_version)
            plugin.log.logging("Database", "Status", "PluginStore %s - upgraded from version %s to %s" % (self.name, stored_version, self.version))

        self._set_records(records)
        # An upgraded store is saved in the new format at the next flush
        self._dirty = stored_version < self.version
        self.writable = True
        plugin.log.logging("Database", "Status", "Z4D loads %s %s record(s) from %s" % (len(records), self.name, source))

        if os.path.isfile(file_path):
            rotate_file_versions(file_path, plugin.pluginconf.pluginConf["numDeviceListVersion"])
        return True

    def flush(self, plugin, force=False):
        """Write the store if it changed since the last flush (or force)."""
        if not self.writable or not (self._dirty or force):
            return

        with self._lock:
            payload = {"Version": self.version, "TimeStamp": time.time(), "Records": copy.deepcopy(self._records)}
            self._dirty = False

        if not self._write_file(plugin, payload):
            # Retry at the next flush
            self._dirty = True
            return

        if (
            plugin.pluginconf.pluginConf.get("useDomoticzDb")
            and plugin.pluginconf.pluginConf.get("storeDomoticzDb")
            and is_domoticz_db_available(plugin)
        ):
            if setConfigItem(Key=self.config_key(), Attribute=STORE_CONFIG_ATTRIBUTE, Value=payload) is None:
                plugin.log.logging("Database", "Error", "PluginStore %s - write to Domoticz failed, kept in %s" % (self.name, self.file_path(plugin)))

        plugin.log.logging("Database", "Log", "PluginStore %s flushed, %s record(s)" % (self.name, len(payload["Records"])))

    # ── Internals ───────────────────────────────────────────────────────────

    def _set_records(self, records):
        with self._lock:
            self._records = records
            self._dirty = False

    def _read_file(self, plugin, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError) as e:
            plugin.log.logging("Database", "Error", "PluginStore %s - unable to read %s: %s" % (self.name, file_path, e))
            return None
        return self._valid_payload(plugin, payload, file_path)

    def _read_domoticz(self, plugin):
        record = getConfigItem(Key=self.config_key(), Attribute=STORE_CONFIG_ATTRIBUTE)
        if not record:
            return None
        return self._valid_payload(plugin, record, "Domoticz record %s" % self.config_key())

    def _valid_payload(self, plugin, payload, origin):
        if (
            isinstance(payload, dict)
            and isinstance(payload.get("Version"), int)
            and isinstance(payload.get("TimeStamp"), (int, float))
            and isinstance(payload.get("Records"), dict)
        ):
            return payload
        plugin.log.logging("Database", "Error", "PluginStore %s - %s is not a valid store" % (self.name, origin))
        return None

    def _write_file(self, plugin, payload):
        file_path = self.file_path(plugin)
        tmp_path = file_path.with_name(file_path.name + ".tmp")
        try:
            with open(tmp_path, "wt", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, file_path)
            return True

        except (TypeError, ValueError, OSError) as e:
            plugin.log.logging("Database", "Error", "PluginStore %s - unable to write %s: %s" % (self.name, file_path, e))
            return False

        finally:
            with contextlib.suppress(OSError):
                if os.path.isfile(tmp_path):
                    os.remove(tmp_path)
