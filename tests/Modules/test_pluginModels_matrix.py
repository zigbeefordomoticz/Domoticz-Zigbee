#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Modules/pluginModels.py - PLUGIN_MODELS_MATRIX integrity and
check_found_plugin_model() matching.

Coverage:
  - Every "PluginModelName" in the matrix is a usable DeviceConf key. The key
    is the config file name *without* its ".json" extension, so a
    PluginModelName carrying a ".json" suffix can never match a DeviceConf
    entry: the device ends up with a bogus Model and no configuration at all.
    The two SONOFF 66666 entries used to read "66666-temphumi.json" /
    "66666-motion.json".
  - "Manufacturer", "ManufId" and "DeviceID" are matched with the `not in`
    operator. A plain string there degrades the exact match into a substring
    match, so these keys must be sequences of strings, not strings.
  - check_found_plugin_model() resolves the SONOFF 66666 family on ZDeviceID
    (0302 -> temp/humi, 0402 -> motion), which is the one discriminator that
    cannot be expressed as an `Identifier` tuple in a device config file.

Modules.pluginModels only imports Modules.tuyaConst (plain data), so it can be
imported directly without conflicting with the stubs installed by
tests/conftest.py.
"""

import types
import unittest

from Modules.pluginModels import PLUGIN_MODELS_MATRIX, check_found_plugin_model

# Keys whose value is compared with `x in <value>` and must therefore be a
# sequence of strings rather than a bare string.
SEQUENCE_KEYS = ("Model", "Manufacturer", "ManufId", "DeviceID")


class _Log:
    def __init__(self):
        self.records = []

    def logging(self, module, level, message, *args, **kwargs):
        self.records.append((level, message))


def _plugin():
    return types.SimpleNamespace(log=_Log(), ModelManufMapping={})


class TestPluginModelsMatrixIntegrity(unittest.TestCase):
    def test_plugin_model_name_is_never_a_filename(self):
        """A PluginModelName is a DeviceConf key, never a file name."""
        for entry in PLUGIN_MODELS_MATRIX:
            name = entry.get("PluginModelName")
            self.assertIsInstance(name, str, entry)
            self.assertFalse(
                name.lower().endswith(".json"),
                f"PluginModelName {name!r} carries a '.json' suffix and can "
                f"never match a DeviceConf key",
            )

    def test_matching_keys_are_sequences_not_strings(self):
        """Manufacturer / ManufId / DeviceID must not be bare strings."""
        for entry in PLUGIN_MODELS_MATRIX:
            for key in SEQUENCE_KEYS:
                if key not in entry:
                    continue
                self.assertNotIsInstance(
                    entry[key],
                    str,
                    f"{key} is a bare string in {entry!r}: `not in` would do a "
                    f"substring match instead of an exact match",
                )

    def test_every_entry_declares_a_plugin_model_name(self):
        for entry in PLUGIN_MODELS_MATRIX:
            self.assertIn("PluginModelName", entry)


class TestCheckFoundPluginModel(unittest.TestCase):
    def test_sonoff_66666_temphumi_resolved_on_device_id(self):
        self.assertEqual(
            check_found_plugin_model(
                _plugin(), "66666", manufacturer_name="eWeLink", device_id="0302"
            ),
            "66666-temphumi",
        )

    def test_sonoff_66666_motion_resolved_on_device_id(self):
        self.assertEqual(
            check_found_plugin_model(
                _plugin(), "66666", manufacturer_name="eWeLink", device_id="0402"
            ),
            "66666-motion",
        )

    def test_sonoff_66666_unknown_device_id_keeps_reported_model(self):
        """An unlisted ZDeviceID must fall back to the bare model name."""
        self.assertEqual(
            check_found_plugin_model(
                _plugin(), "66666", manufacturer_name="eWeLink", device_id="0100"
            ),
            "66666",
        )

    def test_manufacturer_is_matched_exactly_not_as_substring(self):
        """'eWe' must not match the 'eWeLink' entry."""
        self.assertEqual(
            check_found_plugin_model(
                _plugin(), "66666", manufacturer_name="eWe", device_id="0302"
            ),
            "66666",
        )

    def test_tuya_ts011f_plug_resolved_on_manufacturer(self):
        self.assertEqual(
            check_found_plugin_model(
                _plugin(), "TS011F", manufacturer_name="_TZ3000_cehuw1lw"
            ),
            "TS011F-plug",
        )

    def test_unknown_model_is_returned_unchanged(self):
        self.assertEqual(
            check_found_plugin_model(
                _plugin(), "NoSuchModel", manufacturer_name="NoSuchManuf"
            ),
            "NoSuchModel",
        )

    def test_empty_dict_identifiers_are_normalised(self):
        """Domoticz stores unknown fields as {}; they must behave as None."""
        self.assertEqual(
            check_found_plugin_model(
                _plugin(), "66666", manufacturer_name={}, manufacturer_code={}, device_id={}
            ),
            "66666-temphumi",
        )


if __name__ == "__main__":
    unittest.main()
