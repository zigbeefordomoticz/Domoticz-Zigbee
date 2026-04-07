#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Implementation of Zigbee for Domoticz plugin. 
# # # This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee 
# 
# (C) 2015-2024 # # Initial authors: badz & pipiche38 
#
# SPDX-License-Identifier: GPL-3.0 license
import base64
import json
import socket
import ssl
import time
import threading
import urllib.request
import urllib.parse


CACHE_TIMEOUT = (15 * 60) + 15  # seconds
MAX_RETRY = 1
GET_TIMEOUT = 2 

import base64
import json
import socket
import ssl
import time
import threading
import urllib.request
import urllib.parse
import queue

CACHE_TIMEOUT = (15 * 60) + 15
GET_TIMEOUT = 2
MAX_CACHE_SIZE = 256

TRACKED_ATTRIBUTES = {
    "AddjValue",
    "AddjValue2",
}

class DomoticzAPIClient:

    def __init__(self, base_url, pluginconf, log):
        self.base_url = base_url.rstrip('/')
        self.pluginconf = pluginconf
        self.log = log

        self.username = None
        self.password = None
        self.auth_header = None
        self.url_ready = None

        # Cache
        self._cache = {}
        self._cache_lock = threading.Lock()
        
        # Deduplicate
        self._inflight = set()
        self._inflight_lock = threading.Lock()

        # Async worker
        self._stop_event = threading.Event()
        self._queue = queue.Queue()
        self._worker = threading.Thread(target=self._worker_loop, name="DomoticzAPI", daemon=False)
        self._worker.start()

        self._parse_url()

    def stop(self):
        self.logging("Debug", "Stopping API worker thread")

        self._stop_event.set()

        # Wake up thread if blocked
        try:
            self._queue.put_nowait((None, None))
        except Exception:
            pass

        self._worker.join(timeout=2)

        if self._worker.is_alive():
            self.logging("Error", "Worker did not stop cleanly")
        else:
            self.logging("Debug", "Worker stopped")
        
    def logging(self, level, msg):
        self.log.logging("DZapi", level, msg)


    def _parse_url(self):
        parsed = urllib.parse.urlparse(self.base_url)

        self.username = parsed.username
        self.password = parsed.password

        netloc = parsed.hostname
        if parsed.port:
            netloc += f":{parsed.port}"

        if self.username and self.password:
            self.auth_header = base64.b64encode(
                f"{self.username}:{self.password}".encode()
            ).decode()

        self.url_ready = f"{parsed.scheme}://{netloc}/json.htm?"


    def _normalize_query(self, query):
        params = urllib.parse.parse_qsl(query, keep_blank_values=True)
        return urllib.parse.urlencode(sorted(params))


    def _get_cache(self, key):
        with self._cache_lock:
            entry = self._cache.get(key)
            if not entry:
                return None

            ts, data = entry
            if time.time() - ts > CACHE_TIMEOUT:
                return None

            return data


    def _set_cache(self, key, data):
        with self._cache_lock:
            if len(self._cache) >= MAX_CACHE_SIZE:
                self._cache.pop(next(iter(self._cache)))

            self._cache[key] = (time.time(), data)


    def get(self, query, use_cache=True, priority=False):
        cache_key = self._normalize_query(query)

        # 1. Return cache immediately
        if use_cache:
            cached = self._get_cache(cache_key)
            if cached is not None:
                return cached

        # 2. Schedule background fetch
        self._enqueue(query, cache_key, priority)

        # 3. Return None (or stale cache if you want)
        return None


    def _enqueue(self, query, cache_key, priority):

        if self._stop_event.is_set():
            return

        with self._inflight_lock:
            if cache_key in self._inflight:
                # Already scheduled → skip
                return

            self._inflight.add(cache_key)

        try:
            if priority:
                self._queue.queue.appendleft((query, cache_key))
            else:
                self._queue.put_nowait((query, cache_key))
        except Exception:
            # Rollback if enqueue fails
            with self._inflight_lock:
                self._inflight.discard(cache_key)


    def _worker_loop(self):
        while not self._stop_event.is_set():
            try:
                query, cache_key = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if query is None:
                continue

            try:
                url = self.url_ready + query
                data = self._do_request(url)

                if data:
                    self._set_cache(cache_key, data)

            except Exception as e:
                self.logging("Error", f"Worker error: {repr(e)}")

            finally:
                with self._inflight_lock:
                    self._inflight.discard(cache_key)


    def _do_request(self, url):
        ssl_context = None
        if url.lower().startswith("https") and not self.pluginconf.pluginConf["CheckSSLCertificateValidity"]:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        try:
            request = urllib.request.Request(url)

            if self.auth_header:
                request.add_header("Authorization", f"Basic {self.auth_header}")

            with urllib.request.urlopen(request, context=ssl_context, timeout=GET_TIMEOUT) as response:
                return json.loads(response.read())

        except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout, json.JSONDecodeError) as e:
            self.logging("Error", f"{url} failed: {repr(e)}")
            return None


class DomoticzDeviceCache:

    def __init__(self, api_client):
        self.api = api_client
        self.devices = {}
        self.last_refresh = 0

    def refresh(self):
        result = self.api.get("type=command&param=getdevices", priority=True)

        if not result or "result" not in result:
            return

        filtered_devices = {}

        for d in result["result"]:
            idx = str(d.get("idx"))
            if not idx:
                continue

            # Keep only relevant attributes
            filtered = {
                attr: d.get(attr)
                for attr in TRACKED_ATTRIBUTES
                if attr in d
            }

            if filtered:
                filtered_devices[idx] = filtered

        self.devices = filtered_devices
        self.last_refresh = time.time()
        

    def get_device(self, device_id):
        return self.devices.get(str(device_id))


    def get_value(self, device_id, attribute, default=None):
        device = self.devices.get(str(device_id))
        if not device:
            return default

        return device.get(attribute, default)
          

class DomoticzDB_Preferences:

    def __init__(self, api_client):
        self.api = api_client
        self.preferences = {}
        self.load()

    def load(self):
        result = self.api.get("type=command&param=getsettings")
        if result:
            self.preferences = result

    def retrieve_accept_new_hardware(self):
        return self.preferences.get("AcceptNewHardware")

    def retrieve_web_credentials(self):
        return (
            self.preferences.get("WebUserName", ""),
            self.preferences.get("WebPassword", "")
        )


class DomoticzDB_Hardware:

    def __init__(self, api_client, hardware_id):
        self.api = api_client
        self.hardware_id = str(hardware_id)
        self.hardware = {}
        self.load()

    def load(self):
        result = self.api.get("type=command&param=gethardware")
        if not result or "result" not in result:
            return

        self.hardware = {
            str(x["idx"]): x for x in result["result"]
        }

    def get_loglevel_value(self):
        hw = self.hardware.get(self.hardware_id, {})
        return hw.get("LogLevel", 7)

    def is_multi_instance(self):
        count = sum(
            1 for x in self.hardware.values()
            if "Zigate" in x.get("Extra", "")
        )
        return count > 1


class DomoticzDB_DeviceStatus:

    def __init__(self, device_cache):
        self.cache = device_cache

    def retrieve_baro_adjustment(self, device_id):
        return self.cache.get_value(device_id, "AddjValue2", 0)

    def retrieve_temp_adjustment(self, device_id):
        return self.cache.get_value(device_id, "AddjValue", 0)

    def retrieve_motion_timeout(self, device_id):
        return self.cache.get_value(device_id, "AddjValue", 0)