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
PersistedDocument — the persistence engine shared by plugin data: one JSON
document kept in a file and, optionally, in a Domoticz configuration record.

It knows nothing about the content. A caller gives:

- where it lives: a file path (callable, resolved at load/save time), a
  Domoticz configuration key, and a codec for the payload format;
- a format version and, for older versions, an upgrade callable;
- when the Domoticz record is read and written (policies, callables);
- how to log (callable), for callers that run before the plugin logger.

Rules, the same for every document:

- At load, the copy with the most recent TimeStamp wins (file or record).
- A document is written only after a successful load. A document whose
  copies cannot be read, or that was written by a newer plugin (format
  version above the supported one), stays read-only for the session.
- An older format version is upgraded with the upgrade callable, or the
  document stays read-only.
- The file is written atomically (tmp + fsync + replace), then the record.
- Content is never logged, only its size: a document may hold secrets.

EnvelopeCodec is the payload format for new documents. Existing files and
records with their own format (device list, groups, settings, coordinator
backup) get their own codec when they move onto the engine.
"""

import contextlib
import json
import os
import time

from Modules.domoticzAbstractLayer import getConfigItem, setConfigItem
from Modules.tools_domoticz import is_domoticz_db_available
from Modules.tools_files import rotate_file_versions


class EnvelopeCodec:
    """
    Payload {"FormatVersion": int, "TimeStamp": float, <content_key>: content},
    the same in the file and in the Domoticz record.

    The record goes through setConfigItem(), which compresses the content key
    (the record Attribute) and stamps its own "Version" (storage format): the
    document version is therefore kept under "FormatVersion".
    """

    def __init__(self, content_key, content_type=dict):
        self.content_key = content_key
        self.content_type = content_type

    def encode(self, version, timestamp, content):
        return {"FormatVersion": version, "TimeStamp": timestamp, self.content_key: content}

    def decode(self, payload):
        """Return (version, timestamp, content), or None if the payload is not valid."""
        if (
            isinstance(payload, dict)
            and isinstance(payload.get("FormatVersion"), int)
            and isinstance(payload.get("TimeStamp"), (int, float))
            and isinstance(payload.get(self.content_key), self.content_type)
        ):
            return payload["FormatVersion"], payload["TimeStamp"], payload[self.content_key]
        return None


def domoticz_record_read(plugin):
    return bool(plugin.pluginconf.pluginConf.get("useDomoticzDb"))


def domoticz_record_written(plugin):
    return bool(
        plugin.pluginconf.pluginConf.get("useDomoticzDb")
        and plugin.pluginconf.pluginConf.get("storeDomoticzDb")
        and is_domoticz_db_available(plugin)
    )


def plugin_log(plugin, level, message):
    plugin.log.logging("Database", level, message)


class PersistedDocument:

    def __init__(self, name, version, file_path, config_key, codec, upgrade=None, default=dict,
                 rotate_versions=True, read_record=domoticz_record_read, write_record=domoticz_record_written, log=plugin_log):
        """
        Args:
            name:            Used in log messages.
            version:         Format version this plugin reads and writes.
            file_path:       Callable(plugin) -> Path of the file.
            config_key:      Domoticz configuration key of the record.
            codec:           Payload format (encode / decode / content_key).
            upgrade:         Callable(content, from_version) -> content, for older versions.
            default:         Callable() -> content when nothing is stored yet.
            rotate_versions: Rotate versioned backups of the file at load (numDeviceListVersion).
            read_record:     Callable(plugin) -> bool, read the Domoticz record at load.
            write_record:    Callable(plugin) -> bool, write the Domoticz record at save.
            log:             Callable(plugin, level, message).
        """
        self.name = name
        self.version = version
        self._file_path = file_path
        self.config_key = config_key
        self._codec = codec
        self._upgrade = upgrade
        self._default = default
        self._rotate_versions = rotate_versions
        self._read_record = read_record
        self._write_record = write_record
        self._log = log
        self.writable = False
        self.upgraded = False

    def file_path(self, plugin):
        return self._file_path(plugin)

    def load(self, plugin):
        """
        Return the content of the most recent copy, the default content when
        nothing is stored, or None when the document cannot be used (it then
        stays read-only for the session).
        """
        self.writable = False
        self.upgraded = False
        file_path = self.file_path(plugin)

        candidates = []
        file_unreadable = False
        if os.path.isfile(file_path):
            decoded = self._read_file(plugin, file_path)
            if decoded is None:
                file_unreadable = True
            else:
                candidates.append(("file", decoded))

        if self._read_record(plugin):
            decoded = self._read_domoticz(plugin)
            if decoded is not None:
                candidates.append(("Domoticz", decoded))

        if not candidates:
            if file_unreadable:
                self._log(plugin, "Error", "%s - %s cannot be read and no other copy exists, left untouched for this session" % (self.name, file_path))
                return None
            self.writable = True
            return self._default()

        source, (stored_version, _timestamp, content) = max(candidates, key=lambda candidate: candidate[1][1])
        if stored_version > self.version:
            self._log(plugin, "Error", "%s - stored format version %s is newer than supported %s (plugin downgrade?), left untouched for this session" % (
                self.name, stored_version, self.version))
            return None

        if stored_version < self.version:
            if self._upgrade is None:
                self._log(plugin, "Error", "%s - no upgrade from format version %s to %s, left untouched for this session" % (
                    self.name, stored_version, self.version))
                return None
            content = self._upgrade(content, stored_version)
            self.upgraded = True
            self._log(plugin, "Status", "%s - upgraded from format version %s to %s" % (self.name, stored_version, self.version))

        self.writable = True
        self._log(plugin, "Status", "Z4D loads %s (%s entries) from %s" % (self.name, len(content), source))

        if self._rotate_versions and os.path.isfile(file_path):
            rotate_file_versions(file_path, plugin.pluginconf.pluginConf["numDeviceListVersion"])
        return content

    def save(self, plugin, content):
        """Write the file, then the Domoticz record. Returns False when the file was not written."""
        if not self.writable:
            return False

        payload = self._codec.encode(self.version, time.time(), content)
        if not self._write_file(plugin, payload):
            return False

        if self._write_record(plugin):
            if setConfigItem(Key=self.config_key, Attribute=self._codec.content_key, Value=payload) is None:
                self._log(plugin, "Error", "%s - write to Domoticz failed, kept in %s" % (self.name, self.file_path(plugin)))

        self._log(plugin, "Log", "%s saved, %s entries" % (self.name, len(content)))
        return True

    # ── Internals ───────────────────────────────────────────────────────────

    def _read_file(self, plugin, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError) as e:
            self._log(plugin, "Error", "%s - unable to read %s: %s" % (self.name, file_path, e))
            return None
        return self._decode(plugin, payload, file_path)

    def _read_domoticz(self, plugin):
        record = getConfigItem(Key=self.config_key, Attribute=self._codec.content_key)
        if not record:
            return None
        return self._decode(plugin, record, "Domoticz record %s" % self.config_key)

    def _decode(self, plugin, payload, origin):
        decoded = self._codec.decode(payload)
        if decoded is None:
            self._log(plugin, "Error", "%s - %s is not a valid document" % (self.name, origin))
        return decoded

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
            self._log(plugin, "Error", "%s - unable to write %s: %s" % (self.name, file_path, e))
            return False

        finally:
            with contextlib.suppress(OSError):
                if os.path.isfile(tmp_path):
                    os.remove(tmp_path)
