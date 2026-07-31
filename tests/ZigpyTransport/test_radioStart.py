#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Classes/ZigpyTransport/radioStart.py

Covers:
  - _import_class              (dotted-path importer)
  - ezsp_configuration_setup   (config dict structure + optional flags)
  - znp_configuration_setup
  - deconz_configuration_setup
  - blz_configuration_setup
  - optional_configuration_setup
  - radio_start                (unknown module, missing app)
  - start_zigpy_task           (radio_start timeout, extendedPANID parsing)
"""

import asyncio
import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

# NOTE: zigpy.config is intentionally NOT imported at module level.
# Module-level imports of external packages run at collection time, before
# any fixture has had a chance to patch sys.modules.  All zigpy imports
# happen inside test methods or helpers so that the session-scoped
# _radio_stubs fixture always runs first.


def _zc():
    """Lazy accessor for zigpy.config — deferred past pytest collection time."""
    import zigpy.config  # noqa: PLC0415
    return zigpy.config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def make_transport():
    t = MagicMock()
    t.log = MagicMock()
    t.log.logging = MagicMock()
    t.app          = None
    t.hardwareid   = 1
    t.zigpy_running = False
    t.writer_queue  = MagicMock()
    t._radiomodule  = "znp"
    t._serialPort   = "/dev/ttyUSB0"
    t._serialPort_communication_specifics = {}
    t.use_of_zigpy_persistent_db = False
    t.pluginParameters = {"Mode3": "False"}
    t.pluginconf = MagicMock()
    t.pluginconf.pluginConf = {
        "channel":                       "15",
        "extendedPANID":                 "0x0000000000000000",
        "zigpySourceRouting":            False,
        "ZigpyAutoTopology":             False,
        "ForceAPSAck":                   False,
        "enableZigpyPersistentInFile":   False,
        "enableZigpyPersistentInMemory": False,
        "autoBackup":                    None,
        "EzspAllowUnsecuredRejoins":     False,
        "BellowsNoMoreEndDeviceChildren": False,
        "TXpower_set":                   None,
    }
    t.statistics = MagicMock()
    return t


def _make_radio_conf(extra_keys=None):
    """Return a minimal radio-specific config module stub."""
    mod = types.SimpleNamespace()
    mod.CONF_EZSP_CONFIG    = "ezsp_config"
    mod.CONF_EZSP_POLICIES  = "ezsp_policies"
    mod.CONF_ZNP_CONFIG     = "znp_config"
    if extra_keys:
        for k, v in extra_keys.items():
            setattr(mod, k, v)
    return mod


# ===========================================================================
# _import_class
# ===========================================================================

class TestImportClass(unittest.TestCase):

    def test_imports_known_stdlib_class(self):
        from Classes.ZigpyTransport.radioStart import _import_class
        cls = _import_class("queue.Queue")
        import queue
        self.assertIs(cls, queue.Queue)

    def test_imports_zigpy_class(self):
        from Classes.ZigpyTransport.radioStart import _import_class
        import zigpy.types
        cls = _import_class("zigpy.types.EUI64")
        self.assertIs(cls, zigpy.types.EUI64)

    def test_raises_on_missing_module(self):
        from Classes.ZigpyTransport.radioStart import _import_class
        with self.assertRaises(Exception):
            _import_class("nonexistent_module_xyz.SomeClass")


# ===========================================================================
# ezsp_configuration_setup
# ===========================================================================

class TestEzspConfigurationSetup(unittest.TestCase):

    def test_returns_dict_with_device_path(self):
        from Classes.ZigpyTransport.radioStart import ezsp_configuration_setup
        t = make_transport()
        rc = _make_radio_conf()
        config = ezsp_configuration_setup(t, rc, "/dev/ttyUSB0", {})
        self.assertEqual(
            config[_zc().CONF_DEVICE][_zc().CONF_DEVICE_PATH],
            "/dev/ttyUSB0"
        )

    def test_default_baudrate_is_115200(self):
        from Classes.ZigpyTransport.radioStart import ezsp_configuration_setup
        t = make_transport()
        rc = _make_radio_conf()
        config = ezsp_configuration_setup(t, rc, "/dev/ttyUSB0", {})
        self.assertEqual(
            config[_zc().CONF_DEVICE][_zc().CONF_DEVICE_BAUDRATE],
            115200
        )

    def test_custom_baudrate_from_serial_specifics(self):
        from Classes.ZigpyTransport.radioStart import ezsp_configuration_setup
        t = make_transport()
        rc = _make_radio_conf()
        config = ezsp_configuration_setup(t, rc, "/dev/ttyUSB0", {"Baudrate": 57600})
        self.assertEqual(
            config[_zc().CONF_DEVICE][_zc().CONF_DEVICE_BAUDRATE],
            57600
        )

    def test_software_flow_control_mapped_to_none(self):
        from Classes.ZigpyTransport.radioStart import ezsp_configuration_setup
        t = make_transport()
        rc = _make_radio_conf()
        config = ezsp_configuration_setup(t, rc, "/dev/ttyUSB0",
                                          {"FlowControl": "software"})
        self.assertIsNone(
            config[_zc().CONF_DEVICE][_zc().CONF_DEVICE_FLOW_CONTROL]
        )

    def test_handle_unknown_devices_is_true(self):
        from Classes.ZigpyTransport.radioStart import ezsp_configuration_setup
        t = make_transport()
        rc = _make_radio_conf()
        config = ezsp_configuration_setup(t, rc, "/dev/ttyUSB0", {})
        self.assertTrue(config.get("handle_unknown_devices"))

    def test_trust_center_policy_set_when_unsecured_rejoins_enabled(self):
        from Classes.ZigpyTransport.radioStart import ezsp_configuration_setup
        t = make_transport()
        t.pluginconf.pluginConf["EzspAllowUnsecuredRejoins"] = True
        rc = _make_radio_conf()
        config = ezsp_configuration_setup(t, rc, "/dev/ttyUSB0", {})
        self.assertEqual(config["ezsp_policies"]["TRUST_CENTER_POLICY"], 0x0003)

    def test_max_end_device_children_set_when_flag_enabled(self):
        from Classes.ZigpyTransport.radioStart import ezsp_configuration_setup
        t = make_transport()
        t.pluginconf.pluginConf["BellowsNoMoreEndDeviceChildren"] = True
        rc = _make_radio_conf()
        config = ezsp_configuration_setup(t, rc, "/dev/ttyUSB0", {})
        self.assertEqual(config["ezsp_config"]["CONFIG_MAX_END_DEVICE_CHILDREN"], 0)

    def test_tx_power_set_when_configured(self):
        from Classes.ZigpyTransport.radioStart import ezsp_configuration_setup
        t = make_transport()
        t.pluginconf.pluginConf["TXpower_set"] = "10"
        rc = _make_radio_conf()
        config = ezsp_configuration_setup(t, rc, "/dev/ttyUSB0", {})
        self.assertEqual(
            config[_zc().CONF_NWK][_zc().CONF_NWK_TX_POWER],
            10
        )


# ===========================================================================
# znp_configuration_setup
# ===========================================================================

class TestZnpConfigurationSetup(unittest.TestCase):

    def test_returns_dict_with_device_path(self):
        from Classes.ZigpyTransport.radioStart import znp_configuration_setup
        t = make_transport()
        rc = _make_radio_conf()
        config = znp_configuration_setup(t, rc, "/dev/ttyUSB1", {})
        self.assertEqual(
            config[_zc().CONF_DEVICE][_zc().CONF_DEVICE_PATH],
            "/dev/ttyUSB1"
        )

    def test_tx_power_added_when_configured(self):
        from Classes.ZigpyTransport.radioStart import znp_configuration_setup
        t = make_transport()
        t.pluginconf.pluginConf["TXpower_set"] = "5"
        rc = _make_radio_conf()
        config = znp_configuration_setup(t, rc, "/dev/ttyUSB0", {})
        self.assertEqual(config["znp_config"]["tx_power"], 5)


# ===========================================================================
# deconz_configuration_setup
# ===========================================================================

class TestDeconzConfigurationSetup(unittest.TestCase):

    def test_returns_dict_with_device_path(self):
        from Classes.ZigpyTransport.radioStart import deconz_configuration_setup
        t = make_transport()
        rc = _make_radio_conf()
        config = deconz_configuration_setup(t, rc, "/dev/ttyUSB2", {})
        self.assertEqual(
            config[_zc().CONF_DEVICE][_zc().CONF_DEVICE_PATH],
            "/dev/ttyUSB2"
        )

    def test_has_nwk_and_ota_keys(self):
        from Classes.ZigpyTransport.radioStart import deconz_configuration_setup
        t = make_transport()
        rc = _make_radio_conf()
        config = deconz_configuration_setup(t, rc, "/dev/ttyUSB2", {})
        self.assertIn(_zc().CONF_NWK, config)
        self.assertIn(_zc().CONF_OTA, config)


# ===========================================================================
# blz_configuration_setup
# ===========================================================================

class TestBlzConfigurationSetup(unittest.TestCase):

    def test_default_baudrate_is_2mbps(self):
        from Classes.ZigpyTransport.radioStart import blz_configuration_setup
        t = make_transport()
        config = blz_configuration_setup(t, None, "/dev/ttyUSB0", {})
        self.assertEqual(
            config[_zc().CONF_DEVICE][_zc().CONF_DEVICE_BAUDRATE],
            2_000_000
        )

    def test_custom_baudrate_overrides_default(self):
        from Classes.ZigpyTransport.radioStart import blz_configuration_setup
        t = make_transport()
        config = blz_configuration_setup(t, None, "/dev/ttyUSB0",
                                         {"Baudrate": 115200})
        self.assertEqual(
            config[_zc().CONF_DEVICE][_zc().CONF_DEVICE_BAUDRATE],
            115200
        )


# ===========================================================================
# optional_configuration_setup
# ===========================================================================

class TestOptionalConfigurationSetup(unittest.TestCase):

    def _base_config(self):
        return {
            _zc().CONF_DEVICE: {},
            _zc().CONF_NWK:    {},
            _zc().CONF_OTA:    {},
        }

    def test_extended_pan_id_set_when_nonzero(self):
        from Classes.ZigpyTransport.radioStart import optional_configuration_setup
        t = make_transport()
        config = self._base_config()
        rc = _make_radio_conf()
        optional_configuration_setup(t, config, rc, set_extendedPanId=0xDEADBEEF, set_channel=0)
        self.assertIn(_zc().CONF_NWK_EXTENDED_PAN_ID, config[_zc().CONF_NWK])

    def test_extended_pan_id_not_set_when_zero(self):
        from Classes.ZigpyTransport.radioStart import optional_configuration_setup
        t = make_transport()
        config = self._base_config()
        rc = _make_radio_conf()
        optional_configuration_setup(t, config, rc, set_extendedPanId=0, set_channel=0)
        self.assertNotIn(_zc().CONF_NWK_EXTENDED_PAN_ID, config[_zc().CONF_NWK])

    def test_channel_set_when_nonzero(self):
        from Classes.ZigpyTransport.radioStart import optional_configuration_setup
        t = make_transport()
        config = self._base_config()
        rc = _make_radio_conf()
        optional_configuration_setup(t, config, rc, set_extendedPanId=0, set_channel=15)
        self.assertEqual(config[_zc().CONF_NWK][_zc().CONF_NWK_CHANNEL], 15)

    def test_channel_not_set_when_zero(self):
        from Classes.ZigpyTransport.radioStart import optional_configuration_setup
        t = make_transport()
        config = self._base_config()
        rc = _make_radio_conf()
        optional_configuration_setup(t, config, rc, set_extendedPanId=0, set_channel=0)
        self.assertNotIn(_zc().CONF_NWK_CHANNEL, config[_zc().CONF_NWK])

    def test_ota_disabled(self):
        from Classes.ZigpyTransport.radioStart import optional_configuration_setup
        t = make_transport()
        config = self._base_config()
        optional_configuration_setup(t, config, None, set_extendedPanId=0, set_channel=0)
        self.assertFalse(config[_zc().CONF_OTA][_zc().CONF_OTA_ENABLED])

    def test_topology_scan_disabled_by_default(self):
        from Classes.ZigpyTransport.radioStart import optional_configuration_setup
        t = make_transport()
        config = self._base_config()
        optional_configuration_setup(t, config, None, set_extendedPanId=0, set_channel=0)
        self.assertFalse(config[_zc().CONF_TOPO_SCAN_ENABLED])

    def test_watchdog_enabled(self):
        from Classes.ZigpyTransport.radioStart import optional_configuration_setup
        t = make_transport()
        config = self._base_config()
        optional_configuration_setup(t, config, None, set_extendedPanId=0, set_channel=0)
        self.assertTrue(config[_zc().CONF_WATCHDOG_ENABLED])

    def test_persistent_db_in_file(self):
        from Classes.ZigpyTransport.radioStart import optional_configuration_setup
        t = make_transport()
        t.pluginconf.pluginConf["enableZigpyPersistentInFile"] = True
        t.pluginconf.pluginConf["pluginData"] = "/tmp/zigbee"
        config = self._base_config()
        optional_configuration_setup(t, config, None, set_extendedPanId=0, set_channel=0)
        self.assertIn(_zc().CONF_DATABASE, config)
        self.assertIn("zigpy_persistent_01.db", config[_zc().CONF_DATABASE])

    def test_persistent_db_in_memory(self):
        from Classes.ZigpyTransport.radioStart import optional_configuration_setup
        t = make_transport()
        t.pluginconf.pluginConf["enableZigpyPersistentInMemory"] = True
        config = self._base_config()
        optional_configuration_setup(t, config, None, set_extendedPanId=0, set_channel=0)
        self.assertEqual(config.get(_zc().CONF_DATABASE), ":memory:")

    def test_auto_backup_enabled(self):
        from Classes.ZigpyTransport.radioStart import optional_configuration_setup
        t = make_transport()
        t.pluginconf.pluginConf["autoBackup"] = 3600
        config = self._base_config()
        optional_configuration_setup(t, config, None, set_extendedPanId=0, set_channel=0)
        self.assertTrue(config.get(_zc().CONF_NWK_BACKUP_ENABLED))
        self.assertEqual(config.get(_zc().CONF_NWK_BACKUP_PERIOD), 3600)

    def test_auto_backup_disabled_when_none(self):
        from Classes.ZigpyTransport.radioStart import optional_configuration_setup
        t = make_transport()
        t.pluginconf.pluginConf["autoBackup"] = None
        config = self._base_config()
        optional_configuration_setup(t, config, None, set_extendedPanId=0, set_channel=0)
        self.assertFalse(config.get(_zc().CONF_NWK_BACKUP_ENABLED))


# ===========================================================================
# radio_start — unknown module
# ===========================================================================

class TestRadioStartUnknownModule(unittest.TestCase):

    def test_unknown_radiomodule_logs_error_and_returns(self):
        from Classes.ZigpyTransport.radioStart import radio_start
        t = make_transport()
        t._radiomodule = "unknown"
        run(radio_start(t, t.statistics, t.pluginconf, False, "unknown",
                        "/dev/ttyUSB0"))
        errors = [c for c in t.log.logging.call_args_list if c.args[1] == "Error"]
        self.assertTrue(errors)


# ===========================================================================
# start_zigpy_task — radio_start timeout
# ===========================================================================

class TestStartZigpyTaskTimeout(unittest.TestCase):

    def test_radio_start_timeout_clears_app_and_returns(self):
        from Classes.ZigpyTransport.radioStart import start_zigpy_task

        async def slow_radio_start(*args, **kwargs):
            await asyncio.sleep(9999)

        t = make_transport()
        t.pluginconf.pluginConf["extendedPANID"] = "0x1234567890ABCDEF"
        t.pluginconf.pluginConf["channel"]       = "15"
        t.app = AsyncMock()

        with patch("Classes.ZigpyTransport.radioStart.radio_start",
                   side_effect=slow_radio_start), \
             patch("Classes.ZigpyTransport.radioStart.asyncio.wait_for",
                   side_effect=asyncio.TimeoutError):
            run(start_zigpy_task(t, channel=0, extended_pan_id=0))

        # After timeout, app must be nulled
        self.assertIsNone(t.app)

    def test_extended_pan_id_parsed_from_hex_string(self):
        """extendedPANID as a hex string must be parsed to int."""
        from Classes.ZigpyTransport.radioStart import start_zigpy_task

        received_pan_id = []

        async def capture_radio_start(transport, *args, set_channel=0,
                                      set_extendedPanId=0, **kwargs):
            received_pan_id.append(set_extendedPanId)

        t = make_transport()
        t.pluginconf.pluginConf["extendedPANID"] = "0xDEADBEEFDEADBEEF"
        t.pluginconf.pluginConf["channel"]       = "15"

        with patch("Classes.ZigpyTransport.radioStart.radio_start",
                   side_effect=capture_radio_start), \
             patch("Classes.ZigpyTransport.radioStart.worker_loop", new=AsyncMock()):
            run(start_zigpy_task(t, channel=0, extended_pan_id=0))

        self.assertEqual(received_pan_id[0], 0xDEADBEEFDEADBEEF)


if __name__ == "__main__":
    unittest.main()
