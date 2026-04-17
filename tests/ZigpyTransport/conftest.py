#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared fixtures for ZigpyTransport test suite.

Provides a factory for the ZigpyTransport-like mock object that all modules
receive as `self`.  Individual test files extend it with module-specific
attributes where needed.

Also stubs optional radio-driver packages (zigpy_znp, bellows, zigpy_deconz,
zigpy_blz) that are not installed in the CI/test environment.  Stubs are
installed in a session-scoped autouse fixture so they exist before any test
imports a ZigpyTransport module.
"""

import asyncio
import queue
import sys
import types

import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Optional radio-driver stubs (not installed in test env)
# ---------------------------------------------------------------------------

def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


class _FakeZnpException(Exception):
    pass


_RADIO_STUBS = {
    # zigpy_znp ---------------------------------------------------------------
    "zigpy_znp": _make_stub("zigpy_znp"),
    "zigpy_znp.config": _make_stub(
        "zigpy_znp.config",
        CONF_ZNP_CONFIG="znp_config",
    ),
    "zigpy_znp.exceptions": _make_stub(
        "zigpy_znp.exceptions",
        CommandNotRecognized=type("CommandNotRecognized", (Exception,), {}),
        InvalidCommandResponse=type("InvalidCommandResponse", (Exception,), {}),
        InvalidFrame=type("InvalidFrame", (Exception,), {}),
    ),
    # bellows / ezsp ----------------------------------------------------------
    "bellows": _make_stub("bellows"),
    "bellows.config": _make_stub(
        "bellows.config",
        CONF_EZSP_CONFIG="ezsp_config",
        CONF_EZSP_POLICIES="ezsp_policies",
    ),
    "bellows.exception": _make_stub("bellows.exception"),
    # zigpy_deconz ------------------------------------------------------------
    "zigpy_deconz": _make_stub("zigpy_deconz"),
    "zigpy_deconz.config": _make_stub("zigpy_deconz.config"),
    # zigpy_blz ---------------------------------------------------------------
    "zigpy_blz": _make_stub("zigpy_blz"),
    "zigpy_blz.config": _make_stub("zigpy_blz.config"),
}


@pytest.fixture(scope="session", autouse=True)
def _radio_stubs():
    """
    Install radio-driver stubs and patch missing zigpy types before any test
    imports a ZigpyTransport module.

    zigpy==0.42.0 (test environment) pre-dates ZigbeePacket, PacketPriority,
    TransmitOptions, AddrModeAddress, and SerializableBytes.  Stub them so the
    SUT can be imported without errors.
    """
    for name, mod in _RADIO_STUBS.items():
        sys.modules.setdefault(name, mod)

    # Patch newer zigpy.types symbols that are absent in 0.42.x ---------------
    import zigpy.types as zt
    import enum as _enum

    if not hasattr(zt, "PacketPriority"):
        class PacketPriority(_enum.IntEnum):
            NORMAL = 0
            HIGH   = 1
        zt.PacketPriority = PacketPriority

    if not hasattr(zt, "TransmitOptions"):
        class TransmitOptions(_enum.IntFlag):
            NONE = 0
            ACK  = 1
        zt.TransmitOptions = TransmitOptions

    if not hasattr(zt, "AddrModeAddress"):
        class AddrModeAddress:
            def __init__(self, addr_mode=None, address=None):
                self.addr_mode = addr_mode
                self.address   = address
        zt.AddrModeAddress = AddrModeAddress

    if not hasattr(zt, "ZigbeePacket"):
        class ZigbeePacket:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        zt.ZigbeePacket = ZigbeePacket

    if not hasattr(zt, "SerializableBytes"):
        zt.SerializableBytes = bytes

    # Patch missing zigpy.config constants (absent in 0.42.x) ----------------
    import zigpy.config as zc

    _MISSING_CONF = {
        "CONF_DEVICE_BAUDRATE":       "baudrate",
        "CONF_DEVICE_FLOW_CONTROL":   "flow_control",
        "CONF_SOURCE_ROUTING":        "source_routing",
        "CONF_OTA_ENABLED":           "ota_enabled",
        "CONF_WATCHDOG_ENABLED":      "watchdog_enabled",
        "CONF_MAX_CONCURRENT_REQUESTS": "max_concurrent_requests",
        "CONF_NWK_TX_POWER":          "tx_power",
        "CONF_NWK_BACKUP_ENABLED":    "network_backup_enabled",
        "CONF_NWK_BACKUP_PERIOD":     "network_backup_period",
        "CONF_STARTUP_ENERGY_SCAN":   "startup_energy_scan",
    }
    for attr, value in _MISSING_CONF.items():
        if not hasattr(zc, attr):
            setattr(zc, attr, value)


def make_transport(loop=None):
    """
    Return a minimal ZigpyTransport-like mock with all attributes expected by
    supervisor.py, workerLoop.py, zigpySend.py, radioStart.py and zigpyThread.py.

    `loop` is the asyncio event loop to attach; a fresh one is created if omitted.
    """
    transport = MagicMock()

    # ----- logging -----
    transport.log = MagicMock()
    transport.log.logging = MagicMock()

    # ----- event loop -----
    transport.zigpy_loop = loop  # set to a real loop in async tests

    # ----- lifecycle flags -----
    transport.zigpy_running         = False
    transport._zigpy_stop_requested = False
    transport._shutdown_event       = asyncio.Event() if loop is None else None

    # ----- supervisor bookkeeping -----
    transport._restart_count       = 0
    transport._consecutive_failures = 0
    transport._restart_timestamps  = []
    transport._stack_health        = "STARTING"
    transport._last_heartbeat      = None
    transport._last_activity       = None

    # ----- radio / app -----
    transport.app         = None
    transport._radiomodule = "znp"
    transport._serialPort  = "/dev/ttyUSB0"
    transport._serialPort_communication_specifics = {}
    transport.hardwareid   = 1
    transport.use_of_zigpy_persistent_db = False

    # ----- queues -----
    transport.writer_queue    = queue.Queue()
    transport.forwarder_queue = queue.Queue()

    # ----- concurrency tracking -----
    transport._concurrent_requests_semaphores_list = {}
    transport._currently_waiting_requests_list     = {}
    transport._currently_not_reachable             = []

    # ----- plugin config -----
    transport.pluginconf = MagicMock()
    transport.pluginconf.pluginConf = {
        "channel":                      "15",
        "extendedPANID":                "0x0000000000000000",
        "zigpySourceRouting":           False,
        "ZigpyAutoTopology":            False,
        "ForceAPSAck":                  False,
        "enableZigpyPersistentInFile":  False,
        "enableZigpyPersistentInMemory": False,
        "autoBackup":                   None,
        "EzspAllowUnsecuredRejoins":    False,
        "BellowsNoMoreEndDeviceChildren": False,
        "TXpower_set":                  None,
    }
    transport.pluginParameters = {"Mode3": "False"}

    # ----- statistics -----
    transport.statistics         = MagicMock()
    transport.statistics._sent   = 0
    transport.statistics._ackKO  = 0
    transport.statistics._APSAck = 0
    transport.statistics._APSNck = 0

    # ----- scan tasks -----
    transport.manual_topology_scan_task    = None
    transport.manual_interference_scan_task = None

    # ----- plugin restart callback -----
    transport.restart_plugin = MagicMock()

    # ----- thread handle (for zigpyThread tests) -----
    transport.zigpy_thread = None

    return transport


@pytest.fixture
def transport():
    """Fresh ZigpyTransport-like mock for each test."""
    return make_transport()
