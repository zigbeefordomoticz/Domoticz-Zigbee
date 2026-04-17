#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared fixtures for ZigpyTransport test suite.

Provides a factory for the ZigpyTransport-like mock object that all modules
receive as `self`.  Individual test files extend it with module-specific
attributes where needed.

Also stubs optional radio-driver packages (zigpy_znp, bellows, zigpy_deconz,
zigpy_blz) AND the zigpy core package when it is not installed in the test
environment.  Stubs are installed in a session-scoped autouse fixture so they
exist before any test imports a ZigpyTransport module.
"""

import asyncio
import enum as _enum
import importlib.util
import queue
import sys
import types

import pytest
from unittest.mock import MagicMock


# True when zigpy is present in the Python environment
_HAS_ZIGPY = importlib.util.find_spec("zigpy") is not None


# ---------------------------------------------------------------------------
# Module stub factory
# ---------------------------------------------------------------------------

def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


def _make_package_stub(name, **attrs):
    """Like _make_stub but marks the module as a package (has __path__)."""
    mod = _make_stub(name, **attrs)
    mod.__path__ = []   # required for Python to treat it as a package
    mod.__package__ = name
    return mod


# ---------------------------------------------------------------------------
# zigpy core stubs
# Used only when zigpy is NOT installed (sys.modules.setdefault is a no-op
# when the real package is already present).
# ---------------------------------------------------------------------------

# -- zigpy.exceptions -------------------------------------------------------
_zigpy_exceptions_stub = _make_stub(
    "zigpy.exceptions",
    APIException=type("APIException", (Exception,), {}),
    ControllerException=type("ControllerException", (Exception,), {}),
    DeliveryError=type("DeliveryError", (Exception,), {}),
    InvalidResponse=type("InvalidResponse", (Exception,), {}),
    NetworkNotFormed=type("NetworkNotFormed", (Exception,), {}),
    NetworkSettingsInconsistent=type("NetworkSettingsInconsistent", (Exception,), {}),
)

# -- zigpy.types ------------------------------------------------------------

class _EUI64Stub(bytes):
    """Minimal EUI64 stand-in: accepts hex strings and byte sequences."""
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, b"\x00" * 8)
    def __repr__(self):
        return "EUI64Stub()"


class _PacketPriority(_enum.IntEnum):
    NORMAL = 0
    HIGH   = 1


class _TransmitOptions(_enum.IntFlag):
    NONE = 0
    ACK  = 1


class _BroadcastAddress(_enum.IntEnum):
    """Minimal BroadcastAddress stand-in — only the values the SUT references."""
    ALL_DEVICES                  = 0xFFFF
    ALL_ROUTERS_AND_COORDINATOR  = 0xFFFC
    ALL_SLEEPY_END_DEVICES       = 0xFFFF
    RX_ON_WHEN_IDLE              = 0xFFFD
    RESERVED_FFFE                = 0xFFFE


class _AddrMode(_enum.IntEnum):
    """Minimal AddrMode stand-in."""
    NWK       = 0x02
    IEEE      = 0x03
    Group     = 0x01
    Broadcast = 0xFF


class _AddrModeAddress:
    def __init__(self, addr_mode=None, address=None):
        self.addr_mode = addr_mode
        self.address   = address


class _ZigbeePacket:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _uint64_t(int):
    """int subclass with zigpy-compatible serialize() → 8-byte little-endian."""
    def serialize(self):
        return int(self).to_bytes(8, "little")


_zigpy_types_stub = _make_stub(
    "zigpy.types",
    EUI64=_EUI64Stub,
    PacketPriority=_PacketPriority,
    TransmitOptions=_TransmitOptions,
    BroadcastAddress=_BroadcastAddress,
    AddrMode=_AddrMode,
    AddrModeAddress=_AddrModeAddress,
    ZigbeePacket=_ZigbeePacket,
    SerializableBytes=bytes,
    # Integer types referenced by SUT signatures
    NWK=int,
    uint8_t=int,
    uint16_t=int,
    uint32_t=int,
    uint64_t=_uint64_t,
)

# -- zigpy.config -----------------------------------------------------------
_zigpy_config_stub = _make_stub(
    "zigpy.config",
    # Core keys present in every zigpy version
    CONF_DEVICE="device",
    CONF_DEVICE_PATH="path",
    CONF_NWK="network",
    CONF_OTA="ota",
    CONF_DATABASE="database",
    CONF_NWK_EXTENDED_PAN_ID="extended_pan_id",
    CONF_NWK_CHANNEL="channel",
    # Keys added in newer zigpy versions (also patched below if absent on real zigpy)
    CONF_DEVICE_BAUDRATE="baudrate",
    CONF_DEVICE_FLOW_CONTROL="flow_control",
    CONF_SOURCE_ROUTING="source_routing",
    CONF_OTA_ENABLED="ota_enabled",
    CONF_TOPO_SCAN_ENABLED="topology_scan_enabled",
    CONF_TOPO_SCAN_PERIOD="topology_scan_period",
    CONF_WATCHDOG_ENABLED="watchdog_enabled",
    CONF_MAX_CONCURRENT_REQUESTS="max_concurrent_requests",
    CONF_NWK_TX_POWER="tx_power",
    CONF_NWK_BACKUP_ENABLED="network_backup_enabled",
    CONF_NWK_BACKUP_PERIOD="network_backup_period",
    CONF_STARTUP_ENERGY_SCAN="startup_energy_scan",
)

# -- zigpy.device -----------------------------------------------------------
_zigpy_device_stub = _make_stub(
    "zigpy.device",
    Device=MagicMock,
)

# -- zigpy.zcl --------------------------------------------------------------
_zigpy_zcl_stub = _make_stub("zigpy.zcl")

# -- zigpy (top-level package) ----------------------------------------------
_zigpy_pkg_stub = _make_package_stub(
    "zigpy",
    types=_zigpy_types_stub,
    config=_zigpy_config_stub,
    exceptions=_zigpy_exceptions_stub,
    device=_zigpy_device_stub,
    zcl=_zigpy_zcl_stub,
)


# ---------------------------------------------------------------------------
# Radio-driver stubs (never installed in CI/test env)
# ---------------------------------------------------------------------------

_RADIO_STUBS = {
    # zigpy_znp -------------------------------------------------------------
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

    # bellows / ezsp --------------------------------------------------------
    "bellows": _make_stub("bellows"),
    "bellows.config": _make_stub(
        "bellows.config",
        CONF_EZSP_CONFIG="ezsp_config",
        CONF_EZSP_POLICIES="ezsp_policies",
    ),
    "bellows.exception": _make_stub("bellows.exception"),

    # zigpy_deconz ----------------------------------------------------------
    "zigpy_deconz": _make_stub("zigpy_deconz"),
    "zigpy_deconz.config": _make_stub("zigpy_deconz.config"),

    # zigpy_blz -------------------------------------------------------------
    "zigpy_blz": _make_stub("zigpy_blz"),
    "zigpy_blz.config": _make_stub("zigpy_blz.config"),
}


# ---------------------------------------------------------------------------
# Missing constants on real zigpy 0.42.x  (also present in stub above)
# ---------------------------------------------------------------------------

_MISSING_CONF = {
    "CONF_DEVICE_BAUDRATE":         "baudrate",
    "CONF_DEVICE_FLOW_CONTROL":     "flow_control",
    "CONF_SOURCE_ROUTING":          "source_routing",
    "CONF_OTA_ENABLED":             "ota_enabled",
    "CONF_TOPO_SCAN_ENABLED":       "topology_scan_enabled",
    "CONF_TOPO_SCAN_PERIOD":        "topology_scan_period",
    "CONF_WATCHDOG_ENABLED":        "watchdog_enabled",
    "CONF_MAX_CONCURRENT_REQUESTS": "max_concurrent_requests",
    "CONF_NWK_TX_POWER":            "tx_power",
    "CONF_NWK_BACKUP_ENABLED":      "network_backup_enabled",
    "CONF_NWK_BACKUP_PERIOD":       "network_backup_period",
    "CONF_STARTUP_ENERGY_SCAN":     "startup_energy_scan",
}

_MISSING_TYPES = {
    "PacketPriority":    _PacketPriority,
    "TransmitOptions":   _TransmitOptions,
    "BroadcastAddress":  _BroadcastAddress,
    "AddrMode":          _AddrMode,
    "AddrModeAddress":   _AddrModeAddress,
    "ZigbeePacket":      _ZigbeePacket,
    "SerializableBytes": bytes,
    "uint64_t":          _uint64_t,
}


# ---------------------------------------------------------------------------
# Session-scoped fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _radio_stubs():
    """
    Ensure all zigpy and radio-driver symbols are importable before any test
    module is collected.

    Strategy
    --------
    * When zigpy is **not installed** we inject a complete set of stubs into
      ``sys.modules`` so that every ``import zigpy.*`` inside the SUT resolves
      to our lightweight stand-ins.
    * When zigpy **is installed** we leave ``sys.modules`` alone for zigpy
      itself (using ``setdefault`` for the real submodules would silently
      replace them before they're first imported) and only patch attributes
      that are missing from older releases (e.g. zigpy==0.42.x).
    * Radio-driver packages (zigpy_znp, bellows, …) are always stubbed via
      ``setdefault`` because they are never installed in the test environment.
    """
    # 1. Install radio-driver stubs (safe: these packages are never present) ---
    for name, mod in _RADIO_STUBS.items():
        sys.modules.setdefault(name, mod)

    # 2. When zigpy is absent, install full zigpy stubs ----------------------
    if not _HAS_ZIGPY:
        _ZIGPY_CORE_STUBS = {
            "zigpy":            _zigpy_pkg_stub,
            "zigpy.types":      _zigpy_types_stub,
            "zigpy.config":     _zigpy_config_stub,
            "zigpy.exceptions": _zigpy_exceptions_stub,
            "zigpy.device":     _zigpy_device_stub,
            "zigpy.zcl":        _zigpy_zcl_stub,
        }
        for name, mod in _ZIGPY_CORE_STUBS.items():
            sys.modules.setdefault(name, mod)
        # Nothing more to patch — stubs already have all needed symbols
        return

    # 3. zigpy IS installed — patch any symbols absent in old releases ---------
    import zigpy.types as zt

    for attr, cls in _MISSING_TYPES.items():
        if not hasattr(zt, attr):
            setattr(zt, attr, cls)

    import zigpy.config as zc

    for attr, value in _MISSING_CONF.items():
        if not hasattr(zc, attr):
            setattr(zc, attr, value)


# ---------------------------------------------------------------------------
# Transport mock factory (used by individual test modules)
# ---------------------------------------------------------------------------

def make_transport(loop=None):
    """
    Return a minimal ZigpyTransport-like mock with all attributes expected by
    supervisor.py, workerLoop.py, zigpySend.py, radioStart.py and zigpyThread.py.

    ``loop`` is the asyncio event loop to attach; a fresh one is created if
    omitted (only relevant for supervisor tests that need a real loop).
    """
    transport = MagicMock()

    # ----- logging -----
    transport.log = MagicMock()
    transport.log.logging = MagicMock()

    # ----- event loop -----
    transport.zigpy_loop = loop

    # ----- lifecycle flags -----
    transport.zigpy_running         = False
    transport._zigpy_stop_requested = False
    transport._shutdown_event       = asyncio.Event() if loop is None else None

    # ----- supervisor bookkeeping -----
    transport._restart_count        = 0
    transport._consecutive_failures = 0
    transport._restart_timestamps   = []
    transport._stack_health         = "STARTING"
    transport._last_heartbeat       = None
    transport._last_activity        = None

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
        "channel":                        "15",
        "extendedPANID":                  "0x0000000000000000",
        "zigpySourceRouting":             False,
        "ZigpyAutoTopology":              False,
        "ForceAPSAck":                    False,
        "enableZigpyPersistentInFile":    False,
        "enableZigpyPersistentInMemory":  False,
        "autoBackup":                     None,
        "EzspAllowUnsecuredRejoins":      False,
        "BellowsNoMoreEndDeviceChildren": False,
        "TXpower_set":                    None,
    }
    transport.pluginParameters = {"Mode3": "False"}

    # ----- statistics -----
    transport.statistics         = MagicMock()
    transport.statistics._sent   = 0
    transport.statistics._ackKO  = 0
    transport.statistics._APSAck = 0
    transport.statistics._APSNck = 0

    # ----- scan tasks -----
    transport.manual_topology_scan_task     = None
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
