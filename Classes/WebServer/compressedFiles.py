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

"""Compressed copies of the WebUI files, kept in memory so that each file is compressed once, not at each request."""

import gzip
import os
import threading
import zlib
from collections import OrderedDict

# Level 9 costs about 40 % more CPU than level 6 on the WebUI bundle, for less than 0.5 % in size
COMPRESSION_LEVEL = 6

# The whole WebUI is about 2.5 MB compressed. The files of a replaced WebUI (their names hold a hash of the content)
# are never asked again: they are the least recently used, and the first to go.
MAX_CACHE_SIZE = 8 * 1024 * 1024

# Already compressed formats: gzip would cost CPU and save nothing
COMPRESSED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".woff", ".woff2", ".gz", ".br", ".zip"}


def is_compressible(filename):
    return os.path.splitext(str(filename))[1].lower() not in COMPRESSED_EXTENSIONS


def compress(body, encoding):
    if encoding == "gzip":
        return gzip.compress(body, COMPRESSION_LEVEL)
    # "deflate" as already sent by sendresponse.py: raw deflate, without the zlib header
    compressor = zlib.compressobj(COMPRESSION_LEVEL, zlib.DEFLATED, -zlib.MAX_WBITS)
    return compressor.compress(body) + compressor.flush()


def file_signature(stat):
    """What tells two versions of a file apart.

    Not only "is it more recent": restoring a previous WebUI can bring back an older modification time. And index.html
    keeps its size from one build to the next, as only the hashes in the bundle names change. The change time
    (st_ctime) is set by the system at each write or replacement, whatever modification time is restored.
    """
    return stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size, stat.st_ino


class CompressedFiles:
    """The file is checked (os.stat) at each request: the WebUI can be updated while the plugin is running."""

    def __init__(self, max_size=MAX_CACHE_SIZE):
        self.max_size = max_size
        self.size = 0
        self._entries = OrderedDict()   # (filename, encoding) -> (signature, compressed body), least recently used first
        self._lock = threading.Lock()   # each WebUI connection has its own thread

    def get(self, filename, encoding):
        """Return the compressed content of the file, from memory when the file is unchanged."""
        key = (os.path.abspath(filename), encoding)
        signature = file_signature(os.stat(filename))

        with self._lock:
            entry = self._entries.get(key)
            if entry and entry[0] == signature:
                self._entries.move_to_end(key)
                return entry[1]

        # Not under the lock: the other files must not wait for a large one to be compressed
        with open(filename, mode="rb") as file:
            signature = file_signature(os.fstat(file.fileno()))
            content = file.read()
            unchanged = file_signature(os.fstat(file.fileno())) == signature
        body = compress(content, encoding)

        if unchanged:
            # A file written while being read is answered, but not kept
            self._store(key, signature, body)
        return body

    def _store(self, key, signature, body):
        with self._lock:
            self._remove(key)
            if len(body) > self.max_size:
                return
            while self._entries and self.size + len(body) > self.max_size:
                self._remove(next(iter(self._entries)))
            self._entries[key] = (signature, body)
            self.size += len(body)

    def _remove(self, key):
        entry = self._entries.pop(key, None)
        if entry:
            self.size -= len(entry[1])
