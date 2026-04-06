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


class DomoticzAPIClient:

    def __init__(self, base_url, pluginconf, log):
        self.base_url = base_url.rstrip('/')
        self.pluginconf = pluginconf
        self.log = log

        self.username = None
        self.password = None
        self.auth_header = None
        self.url_ready = None

        # 🧠 Cache
        self._cache = {}
        self._cache_lock = threading.Lock()

        self._parse_url()

    # ------------------------------------------------------
    def logging(self, level, msg):
        self.log.logging("DZapi", level, msg)

    # ------------------------------------------------------
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

        self.logging("Debug", f"API URL ready: {self.url_ready}")
        if self.username:
            self.logging("Debug", f"Auth enabled for user: {self.username}")

    # ------------------------------------------------------
    # 🧠 Cache helpers
    # ------------------------------------------------------
    def _get_cache(self, key):
        with self._cache_lock:
            entry = self._cache.get(key)
            if not entry:
                return None

            ts, data = entry
            if time.time() - ts > CACHE_TIMEOUT:
                self.logging("Debug", f"Cache expired for {key}")
                del self._cache[key]
                return None

            self.logging("Debug", f"Cache HIT for {key}")
            return data

    def _set_cache(self, key, data):
        with self._cache_lock:
            self._cache[key] = (time.time(), data)
            self.logging("Debug", f"Cache SET for {key}")

    def invalidate_cache(self, key_prefix=None):
        with self._cache_lock:
            if key_prefix is None:
                self._cache.clear()
                self.logging("Debug", "Cache cleared بالكامل")
            else:
                keys_to_delete = [k for k in self._cache if k.startswith(key_prefix)]
                for k in keys_to_delete:
                    del self._cache[k]
                self.logging("Debug", f"Cache cleared for prefix {key_prefix}")

    # ------------------------------------------------------
    # 🌐 Unified HTTP GET with cache
    # ------------------------------------------------------
    def get(self, query, retry=3, timeout=10, use_cache=True):
        url = self.url_ready + query

        # 🔹 Cache lookup
        if use_cache:
            cached = self._get_cache(url)
            if cached is not None:
                return cached

        ssl_context = None
        if url.lower().startswith("https") and not self.pluginconf.pluginConf["CheckSSLCertificateValidity"]:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        while retry:
            try:
                request = urllib.request.Request(url)

                if self.auth_header:
                    request.add_header("Authorization", f"Basic {self.auth_header}")

                self.logging("Debug", f"GET {url}")

                with urllib.request.urlopen(request, context=ssl_context, timeout=timeout) as response:
                    data = json.loads(response.read())

                    if use_cache:
                        self._set_cache(url, data)

                    return data

            except urllib.error.HTTPError as e:
                reason = f"HTTP {e.code} {e.reason}"
            except urllib.error.URLError as e:
                reason = f"URL error {e.reason}"
            except socket.timeout:
                reason = "timeout"

            self.logging("Error", f"{url} failed: {reason} (retrying)")
            retry -= 1
            time.sleep(1)

        self.logging("Error", f"{url} failed after retries")
        return None
    
# ==========================================================
# ⚙️ Preferences
# ==========================================================
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


# ==========================================================
# 🧱 Hardware
# ==========================================================
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


# ==========================================================
# 📟 Device Status
# ==========================================================
class DomoticzDB_DeviceStatus:

    def __init__(self, api_client):
        self.api = api_client

    def get_device_status(self, device_id):
        return self.api.get(f"type=command&param=getdevices&rid={device_id}")

    def _extract_value(self, device_id, attribute):
        result = self.get_device_status(device_id)
        if not result or "result" not in result:
            return 0

        devices = result["result"]
        if not devices:
            return 0

        return devices[0].get(attribute, 0)

    def retrieve_baro_adjustment(self, device_id):
        return self._extract_value(device_id, "AddjValue2")

    def retrieve_temp_adjustment(self, device_id):
        return self._extract_value(device_id, "AddjValue")

    def retrieve_motion_timeout(self, device_id):
        return self._extract_value(device_id, "AddjValue")