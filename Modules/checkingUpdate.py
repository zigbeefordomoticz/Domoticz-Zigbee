#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2026 by pipiche38
#
# Initial authors: pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
checkingUpdate — Plugin and firmware version checks via DNS TXT records.

Public API
----------
start_version_check_worker(self, zigbee_communication, branch, zigate_model)
    Start the long-lived worker thread.  Call once from onStart after
    internet availability has been determined.  The worker queries DNS
    immediately, then repeats every VERSION_CHECK_INTERVAL seconds.

stop_version_check_worker(timeout=10)
    Signal the worker to stop and block until it exits (or timeout expires).
    Call from onStop before the interpreter tears down.

check_plugin_version_against_dns(self, zigbee_communication, branch, zigate_model) -> tuple
    Synchronous DNS query; returns (plugin_version, firm_major, firm_minor).
    Intended for direct use in tests; the worker calls this internally.

is_plugin_update_available(self, currentVersion, availVersion) -> bool
is_zigate_firmware_available(self, ...) -> bool
    Comparison helpers; safe to read after the worker has updated
    self.pluginParameters.

is_internet_available() -> bool
    Lightweight connectivity probe (no self required).

Design notes
------------
- A single persistent thread (rather than one thread per heartbeat) avoids
  repeated Resolver construction.  dns.resolver.Resolver() triggers
  PyThread_allocate_lock → PyGILState_Ensure; in Python 3.13 this causes a
  fatal _PyThreadState_Attach crash when executed on the Domoticz plugin
  callback thread.  Running DNS I/O in a dedicated thread and caching the
  Resolver instance sidesteps both problems.
- The worker sleeps between checks using threading.Event.wait(timeout=…) so
  onStop can interrupt the sleep immediately rather than waiting out the full
  interval.
- In embedded Python (CPython hosted inside Domoticz's C++ process) daemon
  threads are unreliable because termination is tied to CPython's main-thread
  detection, which does not map to the C++ host thread.  We therefore use a
  non-daemon thread and join it explicitly on shutdown.
- Version comparison uses integer tuples, not lexicographic string ordering,
  so "1.10.0" > "1.9.0" is handled correctly.
"""

import socket
import threading
import urllib.error
import urllib.request

import dns.resolver

# ---------------------------------------------------------------------------
# DNS record names
# ---------------------------------------------------------------------------

PLUGIN_TXT_RECORD = "zigate_plugin.pipiche.net"

ZIGATE_DNS_RECORDS = {
    "03": "zigatev1.pipiche.net",
    "04": "zigatev1optipdm.pipiche.net",
    "05": "zigatev2.pipiche.net",
}

DNS_TIMEOUT  = 5   # seconds per nameserver attempt (matches OS resolver default)
DNS_LIFETIME = 15  # seconds total budget — allows trying up to 3 nameservers
VERSION_CHECK_INTERVAL = 12 * 3600  # seconds between periodic re-checks

def initialize_version_checker(self):
    """Initialize the version checker subsystem.

    This is called once from plugin.py onStart after internet availability has
    been determined.  It performs any necessary setup before the worker thread
    is launched.

    Currently this function does not perform any actions, but it serves as a
    placeholder for future initialization logic and ensures a clear separation
    of concerns between plugin startup and version checking setup.
    """
    
    self.resolver_lock = threading.Lock()
    self.dns_resolver: dns.resolver.Resolver | None = None
    self.worker_lock = threading.Lock()
    self.worker_thread: threading.Thread | None = None
    self.stop_event = threading.Event()
 
    
# ---------------------------------------------------------------------------
# Worker lifecycle — called from plugin.py onStart / onStop
# ---------------------------------------------------------------------------

def start_version_check_worker(self, zigbee_communication, branch, zigate_model):
    """Start the DNS version-check worker thread.

    The worker queries DNS once immediately, then sleeps for
    VERSION_CHECK_INTERVAL seconds before repeating.  The sleep is
    interruptible: stop_version_check_worker() wakes it instantly.

    Safe to call multiple times — a second call is a no-op if the thread is
    already running.

    Args:
        self: Plugin instance (.log, .pluginParameters, .internet_available,
              .FirmwareMajorVersion, .FirmwareVersion).
        zigbee_communication: "native" or "zigpy".
        branch: Branch label to look up in the DNS TXT record.
        zigate_model: Zigate hardware model key (only used for "native").
    """
    with self.worker_lock:
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
        self.stop_event.clear()
        self.worker_thread = threading.Thread( name="VersionCheck", target=_worker_loop, args=(self, zigbee_communication, branch, zigate_model) )
        self.worker_thread.daemon = False
        self.worker_thread.start()


def stop_version_check_worker(self, timeout=10):
    """Signal the worker to stop and wait for it to exit.

    Should be called from onStop before the embedded interpreter tears down.
    Uses a timeout so shutdown is never stalled indefinitely; if the thread
    is still alive after timeout it will appear in onStop's thread audit log.

    Args:
        timeout: Maximum seconds to wait for the thread to finish.
    """
    self.stop_event.set()
    with self.worker_lock:
        thread = self.worker_thread
    if thread is not None and thread.is_alive():
        thread.join(timeout=timeout)


# ---------------------------------------------------------------------------
# Worker loop
# ---------------------------------------------------------------------------

def _worker_loop(self, zigbee_communication, branch, zigate_model):
    """Long-lived loop: check DNS immediately then every VERSION_CHECK_INTERVAL seconds."""
    try:
        while not self.stop_event.is_set():
            _run_version_check(self, zigbee_communication, branch, zigate_model)
            # Interruptible sleep: wakes immediately when stop_version_check_worker() fires.
            self.stop_event.wait(timeout=VERSION_CHECK_INTERVAL)
    finally:
        with self.worker_lock:
            self.worker_thread = None


def _run_version_check(self, zigbee_communication, branch, zigate_model):
    """Perform one DNS version check and update self.pluginParameters."""
    try:
        available, firm_major, firm_minor = check_plugin_version_against_dns(
            self, zigbee_communication, branch, zigate_model
        )
        self.pluginParameters.update({
            "available":          available,
            "available-firmMajor": firm_major,
            "available-firmMinor": firm_minor,
            "FirmwareUpdate":     False,
            "PluginUpdate":       False,
        })
        
        if is_plugin_update_available(self, self.pluginParameters["PluginVersion"], available):
            self.log.logging(
                "Plugin", "Status",
                "Z4D found a recent plugin version (%s) on gitHub. You are on (%s) ***"
                % (available, self.pluginParameters["PluginVersion"]),
            )
            self.pluginParameters["PluginUpdate"] = True

        if is_zigate_firmware_available(
            self, self.FirmwareMajorVersion, self.FirmwareVersion, firm_major, firm_minor
        ):
            self.log.logging("Plugin", "Status", "Z4D finds a newer Zigate Firmware version")
            self.pluginParameters["FirmwareUpdate"] = True

    except Exception as e:
        self.log.logging("Plugin", "Error", "Version check failed: %s" % e)


# ---------------------------------------------------------------------------
# Synchronous DNS version check
# ---------------------------------------------------------------------------

def check_plugin_version_against_dns(self, zigbee_communication, branch, zigate_model):
    """Query DNS TXT records and return available version information.

    Args:
        self: Plugin instance.
        zigbee_communication: "native" or "zigpy".
        branch: Branch label to look up ("stable", "beta", …).
        zigate_model: Zigate model key (e.g. "03", "04", "05"); ignored for zigpy.

    Returns:
        tuple: (plugin_version_str, firmware_major_int, firmware_minor_int)
               Returns (0, 0, 0) when the record is unreachable or unsupported.
    """
    self.log.logging(
        "DNS", "Debug",
        "check_plugin_version_against_dns zigbee_communication=%s branch=%s zigate_model=%s"
        % (zigbee_communication, branch, zigate_model),
    )

    plugin_txt = _query_txt(self, PLUGIN_TXT_RECORD)
    if plugin_txt is None:
        self.log.logging(
            "DNS", "Error",
            "Unable to retrieve plugin version TXT record — is Internet access available?",
        )
        return (0, 0, 0)

    plugin_info = _parse_txt_record(plugin_txt)
    self.log.logging("DNS", "Debug", "Plugin version DNS TXT: %s" % plugin_info)

    if zigbee_communication == "zigpy":
        if branch not in plugin_info:
            self.log.logging(
                "DNS", "Error",
                "Branch '%s' not found in DNS TXT record — unsupported version." % branch,
            )
            return (0, 0, 0)
        return (plugin_info[branch], 0, 0)

    if zigbee_communication == "native":
        return _resolve_native_versions(self, plugin_info, branch, zigate_model)

    self.log.logging("DNS", "Error", "Unknown zigbee_communication value: %s" % zigbee_communication)
    return (0, 0, 0)


def _resolve_native_versions(self, plugin_info, branch, zigate_model):
    """Return (plugin_version, firm_major, firm_minor) for native Zigate communication."""
    firmware_record = ZIGATE_DNS_RECORDS.get(zigate_model)
    if firmware_record is None:
        self.log.logging(
            "DNS", "Error",
            "No DNS record configured for Zigate model '%s'." % zigate_model,
        )
        return (0, 0, 0)

    firmware_txt = _query_txt(self, firmware_record)
    firmware_info = _parse_txt_record(firmware_txt)
    self.log.logging("DNS", "Debug", "Firmware version DNS TXT: %s" % firmware_info)

    if branch not in plugin_info or "firmMajor" not in firmware_info or "firmMinor" not in firmware_info:
        self.log.logging(
            "DNS", "Error",
            "Incomplete DNS TXT data for branch='%s', model='%s'." % (branch, zigate_model),
        )
        return (0, 0, 0)

    return (
        plugin_info[branch],
        int(firmware_info["firmMajor"], 16),
        int(firmware_info["firmMinor"], 16),
    )


# ---------------------------------------------------------------------------
# DNS query helpers
# ---------------------------------------------------------------------------

def _get_resolver(self):
    """Return the cached dns.resolver.Resolver, creating it on first call.

    Protected by self.resolver_lock so construction happens exactly once even
    if called from multiple threads simultaneously.
    """
    with self.resolver_lock:
        if self.dns_resolver is None:
            self.dns_resolver = dns.resolver.Resolver()
        return self.dns_resolver


def _query_txt(self, record, timeout=DNS_TIMEOUT, lifetime=DNS_LIFETIME):
    """Query a DNS TXT record and return its content as a single string.

    Tries UDP first, falls back to TCP on any DNS exception.  Sets
    self.internet_available to False on timeout so subsequent checks skip
    the DNS query until connectivity is re-confirmed.

    Args:
        self: Plugin instance.
        record: Fully-qualified DNS name to query.
        timeout: Per-nameserver timeout in seconds.
        lifetime: Total resolution budget in seconds (covers all nameservers
                  and retries); must be > timeout to allow a second nameserver.

    Returns:
        Semicolon-joined TXT strings, or None on any failure.
    """
    if not self.internet_available:
        return None

    resolver = _get_resolver(self)
    resolver.timeout = timeout
    resolver.lifetime = lifetime

    resolve_fn = _pick_resolve_fn(resolver)

    for use_tcp in (False, True):
        try:
            answers = resolve_fn(record, "TXT", tcp=use_tcp)
            self.log.logging("DNS", "Debug", "%s resolved via %s" % (record, "TCP" if use_tcp else "UDP"))
            return _decode_txt_answers(answers)
        except dns.resolver.Timeout:
            self.internet_available = False
            self.log.logging("DNS", "Error", "DNS timeout resolving %s" % record)
            return None
        except dns.exception.DNSException:
            if not use_tcp:
                continue  # retry with TCP
            self.log.logging("DNS", "Error", "DNS error resolving %s" % record)
        except Exception as e:
            self.log.logging("DNS", "Error", "Unexpected error resolving %s: %s" % (record, e))
            return None

    return None


def _pick_resolve_fn(resolver):
    """Return resolver.resolve (dnspython ≥2) or resolver.query (dnspython 1.x)."""
    return getattr(resolver, "resolve", None) or resolver.query


def _decode_txt_answers(answers):
    """Decode a DNS TXT answer rrset into a semicolon-joined string."""
    parts = []
    for rdata in answers:
        strings = getattr(rdata, "strings", None)
        if strings:
            parts.append("".join(s.decode("utf-8", "ignore") for s in strings))
        else:
            parts.append(rdata.to_text().strip('"'))
    return ";".join(parts) if parts else None


# ---------------------------------------------------------------------------
# TXT record parser
# ---------------------------------------------------------------------------

def _parse_txt_record(txt_record):
    """Parse a semicolon-separated key=value DNS TXT record into a dict.

    Example input:  "stable=8.1.005;beta=8.2.001"
    Example output: {"stable": "8.1.005", "beta": "8.2.001"}

    Returns an empty dict for None or empty input.
    """
    if not txt_record:
        return {}
    result = {}
    for item in txt_record.split(";"):
        item = item.strip()
        if "=" not in item:
            continue
        key, _, value = item.partition("=")
        result[key.strip()] = value.strip().strip('"')
    return result


# ---------------------------------------------------------------------------
# Version comparison helpers
# ---------------------------------------------------------------------------

def _parse_version(version_str):
    """Convert "X.Y.Z" to an integer tuple (X, Y, Z) for correct comparison.

    Returns None if the string is not in the expected format.
    """
    try:
        parts = version_str.split(".")
        return None if len(parts) != 3 else tuple(int(p) for p in parts)
    except (AttributeError, ValueError):
        return None


def is_plugin_update_available(self, currentVersion, availVersion):
    """Return True if availVersion is newer than currentVersion.

    Both arguments must be "X.Y.Z" strings.  Comparison is done on integer
    tuples so "1.10.0" > "1.9.0" is handled correctly.

    Returns False (no update) when either version cannot be parsed or
    availVersion is the sentinel value 0.
    """
    if availVersion == 0:
        return False

    current = _parse_version(currentVersion)
    avail = _parse_version(str(availVersion))
    if current is None or avail is None:
        self.log.logging(
            "DNS", "Error",
            "Cannot compare versions: current=%s avail=%s" % (currentVersion, availVersion),
        )
        return False

    if avail > current:
        self.log.logging(
            "DNS", "Status",
            "Zigbee4Domoticz plugin: upgrade available: %s" % availVersion,
        )
        return True

    return False


def is_zigate_firmware_available(self, currentMajorVersion, currentFirmwareVersion, availfirmMajor, availfirmMinor):
    """Return True if a newer Zigate firmware version is available.

    Args:
        self: Plugin instance.
        currentMajorVersion: Current major version integer (informational).
        currentFirmwareVersion: Current firmware version as a hex string (e.g. "0x1234").
        availfirmMajor: Available major firmware version integer from DNS.
        availfirmMinor: Available minor firmware version integer from DNS.

    Returns:
        bool: True if availfirmMinor > current firmware integer value.
    """
    self.log.logging(
        "DNS", "Debug",
        "is_zigate_firmware_available currentMajor=%s currentFW=%s availMajor=%s availMinor=%s"
        % (currentMajorVersion, currentFirmwareVersion, availfirmMajor, availfirmMinor),
    )
    if not availfirmMinor or not currentFirmwareVersion:
        return False
    try:
        if availfirmMinor > int(currentFirmwareVersion, 16):
            self.log.logging("DNS", "Debug", "Zigate firmware update available")
            return True
    except (ValueError, TypeError) as e:
        self.log.logging("DNS", "Error", "Firmware version comparison failed: %s" % e)
    return False


# ---------------------------------------------------------------------------
# Internet connectivity probe
# ---------------------------------------------------------------------------

def is_internet_available():
    """Return True if an outbound HTTPS connection to google.com succeeds.

    Uses a 3-second timeout.  Called once at plugin startup; the result is
    cached in self.internet_available and re-evaluated on DNS timeout.
    """
    try:
        with urllib.request.urlopen("https://www.google.com", timeout=3) as response:
            return response.status == 200
    except (urllib.error.URLError, socket.timeout):
        return False
