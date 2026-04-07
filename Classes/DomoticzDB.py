#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Domoticz Zigbee Plugin API Client and Device Cache

This module provides a non-blocking, threaded Python API client for interacting with
the Domoticz JSON API. It includes:

- DomoticzAPIClient: main client handling requests, caching, and authentication.
- DomoticzDeviceCache: per-device caching with LRU eviction.
- DomoticzDB_DeviceStatus: helpers for reading device attributes.
- DomoticzDB_Preferences: access to Domoticz system preferences.
- DomoticzDB_Hardware: access to Domoticz hardware settings.

Caching is implemented both globally (API responses) and per-device to reduce
network traffic and improve performance in large installations.

Author: pipiche38
License: GPL-3.0
GitHub: https://github.com/zigbeefordomoticz/Domoticz-Zigbee
"""

import base64
import json
import queue
import socket
import ssl
import threading
import time
import urllib.parse
import urllib.request
from collections import OrderedDict

# ----------------------
# Configuration Constants
# ----------------------
CACHE_TIMEOUT = 3600           # seconds per API/device cache
GET_TIMEOUT = 5              # HTTP request timeout
MAX_CACHE_SIZE = 256         # max number of global API cache entries
TRACKED_ATTRIBUTES = {
    "AddjValue",
    "AddjValue2",
}


# ===============================
# Domoticz API Client
# ===============================
class DomoticzAPIClient:
    """
    Client for interacting with the Domoticz JSON API.

    Handles:
    - Threaded, non-blocking HTTP requests
    - Global caching of API responses with LRU eviction
    - Deduplication of inflight requests
    - Authentication (Basic Auth)
    - Registration of per-device caches

    Attributes:
        base_url (str): Base URL of Domoticz API.
        pluginconf (dict): Plugin configuration dictionary.
        log (logger-like object): Object with `logging(category, level, msg)` method.
    """

    def __init__(self, base_url, pluginconf, log):
        """
        Initializes the API client.

        Args:
            base_url (str): Domoticz server URL (may include user:pass).
            pluginconf (dict): Plugin configuration.
            log (object): Logger for debug/error messages.
        """
        self.base_url = base_url.rstrip('/')
        self.pluginconf = pluginconf
        self.log = log

        self.username = None
        self.password = None
        self.auth_header = None
        self.url_ready = None

        # Global cache
        self._cache = OrderedDict()
        self._cache_lock = threading.Lock()

        # Deduplicate inflight requests
        self._inflight = set()
        self._inflight_lock = threading.Lock()

        # Async worker thread
        self._stop_event = threading.Event()
        self._queue = queue.Queue()
        self._worker = threading.Thread(target=self._worker_loop, name="DomoticzAPI", daemon=False)
        self._worker.start()

        # Per-device caches
        self._device_caches = []

        self._parse_url()

    def stop(self):
        """Stops the worker thread cleanly."""
        self.logging("Debug", "Stopping API worker thread")
        self._stop_event.set()
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
        """Wrapper for logging through plugin logger."""
        self.log.logging("DZapi", level, msg)

    # ------------------------------
    # URL / Auth Helpers
    # ------------------------------
    def _parse_url(self):
        """Parse base URL, extract credentials, and prepare JSON endpoint URL."""
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
        """
        Normalize query string by sorting parameters.

        Args:
            query (str): URL query string.

        Returns:
            str: Canonicalized query string.
        """
        params = urllib.parse.parse_qsl(query, keep_blank_values=True)
        return urllib.parse.urlencode(sorted(params))

    # ------------------------------
    # Cache Handling
    # ------------------------------
    def _get_cache(self, query, key):
        """
        Retrieve cached API response if valid.

        Args:
            query (str): Original API query.
            key (str): Normalized cache key.

        Returns:
            dict or None: Cached JSON response or None if missing/stale.
        """
        with self._cache_lock:
            entry = self._cache.get(key)
            if not entry:
                self.logging("Debug", f"Cache MISS for key {key}")
                return None
            ts, data = entry
            if time.time() - ts > CACHE_TIMEOUT:
                self._enqueue(query, key, False)
            # Mark as recently used
            self._cache.move_to_end(key)
            self.logging("Debug", f"Cache HIT for key {key}")
            return data

    def _set_cache(self, key, data):
        """
        Set a cached response and evict oldest if full.

        Args:
            key (str): Normalized cache key.
            data (dict): JSON response to cache.
        """
        with self._cache_lock:
            if key in self._cache:
                self._cache[key] = (time.time(), data)
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= MAX_CACHE_SIZE:
                    oldest_key, _ = self._cache.popitem(last=False)
                    self.logging("Debug", f"Cache full, evicted oldest key {oldest_key}")
                self._cache[key] = (time.time(), data)

    # ------------------------------
    # Public API Access
    # ------------------------------
    def get(self, query, use_cache=True, priority=False):
        """
        Retrieve API response, optionally from cache.

        Args:
            query (str): API query string.
            use_cache (bool): If True, return cached response if available.
            priority (bool): If True, fetch immediately in queue.

        Returns:
            dict or None: Cached response or None if background fetch scheduled.
        """
        cache_key = self._normalize_query(query)
        if use_cache:
            cached = self._get_cache(query, cache_key)
            if cached is not None:
                return cached
        self._enqueue(query, cache_key, priority)
        return None

    def _enqueue(self, query, cache_key, priority=False):
        """
        Add query to worker queue if not already inflight.

        Args:
            query (str): API query string.
            cache_key (str): Normalized cache key.
            priority (bool): If True, place at front of queue.
        """
        self.logging("Debug", f"Enqueue request: {query} (cache_key={cache_key})")
        if self._stop_event.is_set():
            return
        with self._inflight_lock:
            if cache_key in self._inflight:
                return
            self._inflight.add(cache_key)
        try:
            if priority:
                self._queue.queue.appendleft((query, cache_key))
            else:
                self._queue.put((query, cache_key))
        except Exception as e:
            self.logging("Debug", f"Enqueue request error: {e}")
            with self._inflight_lock:
                self._inflight.discard(cache_key)

    # ------------------------------
    # Worker Thread
    # ------------------------------
    def _worker_loop(self):
        """Background thread fetching API requests and updating caches."""
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
                self.logging("Debug", f"_worker_loop fetched: cache_key={cache_key} data={data}")
                
                if data:
                    self._set_cache(cache_key, data)

                    # Update per-device caches if relevant
                    if "rid=" in query:
                        # getdevices for One or a list of Id
                        for cache in self._device_caches:
                            cache.update_device_from_response(data)

                    elif "result" in data:
                        # getdevices for ALL
                        for cache in self._device_caches:
                            cache.update_device_from_response(data)

            except Exception as e:
                self.logging("Error", f"Worker error: {repr(e)}")
            finally:
                with self._inflight_lock:
                    self._inflight.discard(cache_key)

    # ------------------------------
    # HTTP Request
    # ------------------------------
    def _do_request(self, url):
        """
        Perform HTTP GET request to Domoticz API.

        Args:
            url (str): Full URL to request.

        Returns:
            dict or None: Parsed JSON response or None on error.
        """
        ssl_context = None
        if url.lower().startswith("https") and not self.pluginconf.pluginConf.get("CheckSSLCertificateValidity", True):
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        try:
            self.logging("Debug", f"Performing HTTP GET: {url}")
            request = urllib.request.Request(url)
            if self.auth_header:
                request.add_header("Authorization", f"Basic {self.auth_header}")

            with urllib.request.urlopen(request, context=ssl_context, timeout=GET_TIMEOUT) as response:
                return json.load(response)

        except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout, json.JSONDecodeError) as e:
            self.logging("Error", f"{url} failed: {repr(e)}")
            return None

    # ------------------------------
    # Device Cache Registration
    # ------------------------------
    def register_device_cache(self, device_cache):
        """
        Register a per-device cache to be updated after fetches.

        Args:
            device_cache (DomoticzDeviceCache): Device cache instance.
        """
        if device_cache not in self._device_caches:
            self._device_caches.append(device_cache)
        

class DomoticzDeviceCache:
    """
    Per-device cache for Domoticz API responses.

    Maintains cached values for individual devices with:
    - Thread-safe access
    - Automatic background refresh via DomoticzAPIClient

    Attributes:
        api (DomoticzAPIClient): Reference to the main API client.
        devices (OrderedDict): Cached device attributes by device ID.
        _last_refresh (OrderedDict): Last refresh timestamp per device.
    """

    def __init__(self, api_client: DomoticzAPIClient):
        """
        Initialize a device cache.

        Args:
            api_client (DomoticzAPIClient): The API client to fetch devices from.
        """
        self.api = api_client
        self.devices = {}
        self._last_refresh = {}
        self._lock = threading.Lock()
        self.api.register_device_cache(self)
        self.api.logging("Debug", "DomoticzDeviceCache initialized")
        self.refresh()

    def dump_cache(self):
        self.api.logging("Debug", "Dumping Domoticz Cache")
        for x in self.devices:
            self.api.logging("Debug", f"devices {x} : {self.devices[x]}")

    def refresh(self):
        """
        Trigger a full refresh of all devices from Domoticz.

        This schedules a background fetch via the API client.
        """
        self.api.logging("Debug", "Refreshing all devices (full load)")
        query = "type=command&param=getdevices"
        cache_key = self.api._normalize_query(query)
        self.api._enqueue(query, cache_key, priority=True)

    def refresh_device(self, device_id):
        """
        Schedule a background refresh for a single device.

        Args:
            device_id (int or str): ID of the device to refresh.
        """
        device_id = str(device_id)
        query = f"type=command&param=getdevices&rid={device_id}"
        cache_key = self.api._normalize_query(query)
        self.api.logging("Debug", f"Scheduling background refresh for device {device_id}")
        self.api._enqueue(query, cache_key, priority=True)

    def get_value(self, device_id, attribute, default=None):
        """
        Retrieve a cached device attribute, triggering background fetch if stale.

        Args:
            device_id (int or str): ID of the device.
            attribute (str): Attribute name (e.g., "AddjValue").
            default (any): Value to return if attribute is missing.

        Returns:
            any: Cached attribute value or default if unavailable.
        """
        device_id = str(device_id)
        now = time.time()
        last = self._last_refresh.get(device_id, 0)

        if now - last > CACHE_TIMEOUT or device_id not in self.devices:
            self.api.logging("Debug", f"Device {device_id} cache expired or missing. Triggering refresh")
            self.refresh_device(device_id)
        else:
            self.api.logging("Debug", f"Cache HIT for device {device_id}")

        device = self.devices.get(device_id)
        if not device:
            self.api.logging("Debug", f"Device {device_id} not in cache yet. Returning default for {attribute}")
            return default

        val = device.get(attribute, default)
        self.api.logging("Debug", f"Returning value for device {device_id} attribute {attribute}: {val}")
        return val

    def update_device_from_response(self, data):
        """
        Update device cache from a fetched API response.

        Args:
            data (dict or list): API response containing "result" with device data.
        """
        if not data or "result" not in data:
            self.api.logging("Debug", "No result in response")
            return

        devices = data["result"]
        self.api.logging("Debug", f"{len(devices)} devices received")

        for d in devices:
            self._update_single_device(d)

    def _update_single_device(self, d):
        """
        Update or add a single device to the cache.

        Handles:
        - Filtering tracked attributes
        - LRU ordering
        - Eviction if cache is full

        Args:
            d (dict): Device data dictionary from Domoticz API.
        """
        idx = d.get("idx")
        if idx is None:
            self.api.logging("Debug", f"Device data missing idx: {d}")
            return
        idx = str(idx)

        filtered = {attr: d.get(attr) for attr in TRACKED_ATTRIBUTES if attr in d}
        if not filtered:
            self.api.logging("Debug", f"No tracked attributes in device {idx}: {d}")
            return

        with self._lock:
            self.devices[idx] = filtered
            self._last_refresh[idx] = time.time()

            self.api.logging("Debug", f"Updated cache for device {idx}: {json.dumps(filtered)}")


# ===============================
# Device Status Accessor
# ===============================
class DomoticzDB_DeviceStatus:
    """
    Convenience class for reading specific device attributes from a DomoticzDeviceCache.
    """

    def __init__(self, device_cache: DomoticzDeviceCache):
        """
        Args:
            device_cache (DomoticzDeviceCache): Reference to the device cache.
        """
        self.cache = device_cache

    def retrieve_baro_adjustment(self, device_id):
        """Retrieve barometric adjustment (AddjValue2) for a device."""
        return self.cache.get_value(device_id, "AddjValue2", 0)

    def retrieve_temp_adjustment(self, device_id):
        """Retrieve temperature adjustment (AddjValue) for a device."""
        return self.cache.get_value(device_id, "AddjValue", 0)

    def retrieve_motion_timeout(self, device_id):
        """Retrieve motion timeout (AddjValue) for a device."""
        return self.cache.get_value(device_id, "AddjValue", 0)


# ===============================
# Domoticz Preferences
# ===============================
class DomoticzDB_Preferences:
    """
    Access Domoticz system preferences.
    """

    def __init__(self, api_client: DomoticzAPIClient):
        """
        Args:
            api_client (DomoticzAPIClient): Reference to the API client.
        """
        self.api = api_client
        self.preferences = {}
        self.load()

    def load(self):
        """Fetch preferences from Domoticz."""
        result = self.api.get("type=command&param=getsettings")
        if result:
            self.preferences = result

    def retrieve_accept_new_hardware(self):
        """Return the 'AcceptNewHardware' setting."""
        return self.preferences.get("AcceptNewHardware")

    def retrieve_web_credentials(self):
        """Return web UI username and password."""
        return (
            self.preferences.get("WebUserName", ""),
            self.preferences.get("WebPassword", "")
        )


# ===============================
# Domoticz Hardware
# ===============================
class DomoticzDB_Hardware:
    """
    Access Domoticz hardware settings.
    """

    def __init__(self, api_client: DomoticzAPIClient, hardware_id):
        """
        Args:
            api_client (DomoticzAPIClient): API client.
            hardware_id (int or str): Hardware device index.
        """
        self.api = api_client
        self.hardware_id = str(hardware_id)
        self.hardware = {}
        self.load()

    def load(self):
        """Load hardware information from Domoticz."""
        result = self.api.get("type=command&param=gethardware")
        if not result or "result" not in result:
            return

        self.hardware = {str(x["idx"]): x for x in result["result"]}

    def get_loglevel_value(self):
        """Return log level for this hardware (default 7)."""
        hw = self.hardware.get(self.hardware_id, {})
        return hw.get("LogLevel", 7)

    def is_multi_instance(self):
        """
        Determine if multiple 'Zigate' instances exist.

        Returns:
            bool: True if more than one Zigate hardware exists.
        """
        count = sum(
            1 for x in self.hardware.values()
            if "Zigate" in x.get("Extra", "")
        )
        return count > 1