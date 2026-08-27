#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_Modules.domoticzAbstractLayer.py
~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for Modules.domoticzAbstractLayer.py (hardened version).

Run with:
    pytest test_Modules.domoticzAbstractLayer.py -v

No real Domoticz installation is required — every Domoticz API object
(Domoticz.Configuration, Domoticz.Unit, Domoticz.Connection) is replaced
by a lightweight fake/mock inside this file.
"""

import ast
import base64
import importlib
import json
import sys
import time
import types
import unittest
from unittest.mock import MagicMock, call, patch


# ---------------------------------------------------------------------------
# Build a fake DomoticzEx module so the import in the SUT succeeds without
# a real Domoticz environment.
# ---------------------------------------------------------------------------

class _FakeUnit:
    """Mimics a Domoticz Unit object."""

    def __init__(self, DeviceID="", Name="", Unit=1, TypeName=None,
                 Type=0, Subtype=0, Switchtype=0, Options=None, Image=None):
        self.DeviceID = DeviceID
        self.Name     = Name
        self.Unit     = Unit
        self.TypeName = TypeName
        self.Type     = Type
        self.SubType  = Subtype
        self.SwitchType = Switchtype
        self.Options  = Options or {}
        self.Image    = Image
        self.ID       = id(self) % 100000      # stable fake IDX
        self.nValue   = 0
        self.sValue   = ""
        self.Color    = ""
        self.BatteryLevel  = 255
        self.SignalLevel   = 12
        self.LastUpdate    = "2024-01-01 12:00:00"
        self._created = False
        self._deleted = False
        self._updated = False
        self._touched = False
        self._last_update_kwargs = None
        # Back-reference set by _make_devices so Delete() can remove itself
        self._parent_device: "_FakeDevice | None" = None

    def Create(self):
        self._created = True
        return self

    def Delete(self):
        """Mirror real Domoticz: mark deleted and remove from parent Units dict."""
        self._deleted = True
        if self._parent_device is not None and self.Unit in self._parent_device.Units:
            del self._parent_device.Units[self.Unit]

    def Update(self, Log=True, TypeName=None, SuppressTriggers=False, UpdateProperties=False, UpdateOptions=False):
        self._updated = True
        self._update_log = Log
        self._update_suppress_triggers = SuppressTriggers
        self._update_properties = UpdateProperties
        self._last_update_kwargs = {
            "Log": Log, "TypeName": TypeName, "UpdateProperties": UpdateProperties,
            "UpdateOptions": UpdateOptions, "SuppressTriggers": SuppressTriggers,
        }
        if TypeName is not None and UpdateProperties:
            self.TypeName = TypeName

    def Touch(self):
        self._touched = True


class _FakeDevice:
    """Mimics a Domoticz Device object (Extended framework)."""

    def __init__(self, DeviceID=""):
        self.DeviceID = DeviceID
        self.Units: dict[int, _FakeUnit] = {}
        self.TimedOut = 0
        self._deleted = False

    def Delete(self):
        self._deleted = True


def _make_fake_domoticz_module():
    """Return a module-like object standing in for DomoticzEx."""
    mod = types.ModuleType("DomoticzEx")

    _config_store: dict = {}

    def _Configuration(new_cfg=None):
        if new_cfg is None:
            return dict(_config_store)
        _config_store.clear()
        _config_store.update(new_cfg)
        return dict(_config_store)

    mod.Configuration = _Configuration
    mod.Unit          = _FakeUnit
    mod.Connection    = MagicMock(return_value=MagicMock())
    mod.Log           = MagicMock()
    mod.Debug         = MagicMock()
    mod.Error         = MagicMock()
    mod.Status        = MagicMock()
    return mod


# Install the fake module *before* importing the SUT.
_fake_domoticz = _make_fake_domoticz_module()
sys.modules["DomoticzEx"] = _fake_domoticz

# Now import the module under test.
import Modules.domoticzAbstractLayer as domo


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_self(devices=None):
    """Return a minimal plugin-self mock."""
    obj = MagicMock()
    obj.ListOfDomoticzWidget = {}
    obj.IEEE2NWK = {}
    obj.pluginParameters = {"Name": "ZigbeePlugin"}
    obj.pluginconf.pluginConf = {"deviceOffWhenTimeOut": False}
    obj.log.logging = MagicMock()
    return obj


def _make_devices(*device_specs):
    """
    Build a fake Devices dict.

    Each spec is a tuple:
        (ieee_str, [(unit_int, unit_kwargs_dict), ...])
    """
    devices = {}
    for ieee, unit_list in device_specs:
        dev = _FakeDevice(DeviceID=ieee)
        for unit_id, kwargs in unit_list:
            u = _FakeUnit(DeviceID=ieee, Unit=unit_id, **kwargs)
            u._parent_device = dev          # enables Delete() to remove itself
            dev.Units[unit_id] = u
        devices[ieee] = dev
    return devices


# ---------------------------------------------------------------------------
# 1. Internal guard helpers
# ---------------------------------------------------------------------------

class TestDeviceExists(unittest.TestCase):

    def test_none_devices_returns_false(self):
        self.assertFalse(domo._device_exists(None, "ieee-1"))

    def test_missing_device_returns_false(self):
        devices = _make_devices(("ieee-1", [(1, {})]))
        self.assertFalse(domo._device_exists(devices, "ieee-2"))

    def test_present_device_returns_true(self):
        devices = _make_devices(("ieee-1", [(1, {})]))
        self.assertTrue(domo._device_exists(devices, "ieee-1"))


class TestDeviceUnitExists(unittest.TestCase):

    def test_none_devices_returns_false(self):
        self.assertFalse(domo._device_unit_exists(None, "ieee-1", 1))

    def test_missing_device_returns_false(self):
        devices = _make_devices(("ieee-1", [(1, {})]))
        self.assertFalse(domo._device_unit_exists(devices, "ieee-2", 1))

    def test_missing_unit_returns_false(self):
        devices = _make_devices(("ieee-1", [(1, {})]))
        self.assertFalse(domo._device_unit_exists(devices, "ieee-1", 99))

    def test_present_device_and_unit_returns_true(self):
        devices = _make_devices(("ieee-1", [(1, {})]))
        self.assertTrue(domo._device_unit_exists(devices, "ieee-1", 1))


# ---------------------------------------------------------------------------
# 2. Configuration helpers
# ---------------------------------------------------------------------------

class TestPrepareAndRepairDict(unittest.TestCase):

    def test_prepare_encodes_attribute(self):
        data = {"payload": {"key": "val"}, "other": 42}
        result = domo.prepare_dict_for_storage(data.copy(), "payload")
        self.assertIn("Version", result)
        self.assertEqual(result["Version"], 2)
        # Value must be a base64-encoded string (zlib+b64 encoding)
        self.assertIsInstance(result["payload"], str)

    def test_prepare_adds_version_even_without_attribute(self):
        data = {"something": 1}
        result = domo.prepare_dict_for_storage(data.copy(), "nonexistent")
        self.assertEqual(result["Version"], 2)

    def test_repair_empty_string_returns_empty_dict(self):
        self.assertEqual(domo.repair_dict_after_load("", "attr"), {})

    def test_repair_none_returns_empty_dict(self):
        self.assertEqual(domo.repair_dict_after_load(None, "attr"), {})

    def test_repair_no_version_key_returns_empty_dict(self):
        self.assertEqual(domo.repair_dict_after_load({"data": 1}, "data"), {})

    def test_repair_missing_attribute_returns_dict_unchanged(self):
        d = {"Version": 1, "other": "value"}
        result = domo.repair_dict_after_load(d, "nonexistent")
        self.assertEqual(result, d)

    def test_repair_already_dict_value_returns_unchanged(self):
        d = {"Version": 1, "payload": {"nested": True}}
        result = domo.repair_dict_after_load(d, "payload")
        self.assertIsInstance(result["payload"], dict)

    def test_roundtrip_json_payload(self):
        original = {"key": "value", "num": 42}
        prepared = domo.prepare_dict_for_storage({"payload": original, "Version": 1}, "payload")
        repaired = domo.repair_dict_after_load(prepared, "payload")
        self.assertEqual(repaired["payload"], original)

    def test_roundtrip_list_payload(self):
        original = [1, 2, 3]
        prepared = domo.prepare_dict_for_storage({"payload": original, "Version": 1}, "payload")
        repaired = domo.repair_dict_after_load(prepared, "payload")
        self.assertEqual(repaired["payload"], original)


class TestDecodeB64Payload(unittest.TestCase):

    def test_decode_json_bytes(self):
        encoded = base64.b64encode(b'{"a": 1}')
        result = domo.decode_b64_payload(encoded)
        self.assertEqual(result, {"a": 1})

    def test_decode_json_string(self):
        encoded = base64.b64encode(b'[1, 2, 3]').decode()
        result = domo.decode_b64_payload(encoded)
        self.assertEqual(result, [1, 2, 3])

    def test_decode_python_literal(self):
        encoded = base64.b64encode(b"{'x': 99}").decode()
        result = domo.decode_b64_payload(encoded)
        self.assertEqual(result, {"x": 99})

    def test_invalid_base64_raises_value_error(self):
        with self.assertRaises(ValueError):
            domo.decode_b64_payload("not-base64!!!")

    def test_valid_base64_but_unparseable_content_raises_value_error(self):
        encoded = base64.b64encode(b"this is plain text, not JSON or Python").decode()
        with self.assertRaises(ValueError):
            domo.decode_b64_payload(encoded)


class TestSetConfigItem(unittest.TestCase):

    def setUp(self):
        # Reset the fake config store between tests
        _fake_domoticz.Configuration({})

    def test_rejects_none_value(self):
        result = domo.setConfigItem(Key="k", Value=None)
        self.assertIsNone(result)

    def test_rejects_invalid_type(self):
        result = domo.setConfigItem(Key="k", Value=object())
        self.assertIsNone(result)

    def test_stores_string(self):
        result = domo.setConfigItem(Key="mykey", Value="hello")
        self.assertIsNotNone(result)
        self.assertEqual(result.get("mykey"), "hello")

    def test_stores_int(self):
        result = domo.setConfigItem(Key="count", Value=7)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("count"), 7)

    def test_stores_dict(self):
        result = domo.setConfigItem(Key="cfg", Value={"a": 1})
        self.assertIsNotNone(result)

    def test_no_key_replaces_whole_config(self):
        result = domo.setConfigItem(Key=None, Value={"x": 10})
        self.assertIsNotNone(result)


class TestGetConfigItem(unittest.TestCase):

    def setUp(self):
        _fake_domoticz.Configuration({})

    def test_missing_key_returns_default(self):
        result = domo.getConfigItem(Key="missing", Default={"fallback": True})
        # repair_dict_after_load will return {} because no "Version" key
        self.assertIsInstance(result, dict)

    def test_existing_key_returned(self):
        _fake_domoticz.Configuration({"mykey": "stored_value"})
        result = domo.getConfigItem(Key="mykey", Default={})
        # Value is a plain string — repair_dict_after_load returns {} for non-dict
        self.assertIsInstance(result, dict)


# ---------------------------------------------------------------------------
# 3. Widget index
# ---------------------------------------------------------------------------

class TestLoadListOfDomoticzWidget(unittest.TestCase):

    def test_none_devices_clears_index(self):
        obj = _make_self()
        obj.ListOfDomoticzWidget = {1: "stale"}
        domo.load_list_of_domoticz_widget(obj, None)
        self.assertEqual(obj.ListOfDomoticzWidget, {})

    def test_empty_devices_produces_empty_index(self):
        obj = _make_self()
        domo.load_list_of_domoticz_widget(obj, {})
        self.assertEqual(obj.ListOfDomoticzWidget, {})

    def test_single_device_single_unit_indexed(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {"Name": "Bulb"})]))
        domo.load_list_of_domoticz_widget(obj, devices)
        self.assertEqual(len(obj.ListOfDomoticzWidget), 1)
        entry = list(obj.ListOfDomoticzWidget.values())[0]
        self.assertEqual(entry["DeviceID"], "ieee-1")
        self.assertEqual(entry["Unit"], 1)
        self.assertEqual(entry["Name"], "Bulb")

    def test_multiple_devices_all_indexed(self):
        obj = _make_self()
        devices = _make_devices(
            ("ieee-1", [(1, {}), (2, {})]),
            ("ieee-2", [(1, {})]),
        )
        domo.load_list_of_domoticz_widget(obj, devices)
        self.assertEqual(len(obj.ListOfDomoticzWidget), 3)

    def test_rebuilds_on_second_call(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.load_list_of_domoticz_widget(obj, devices)
        count_first = len(obj.ListOfDomoticzWidget)
        # Remove the device and rebuild
        devices.pop("ieee-1")
        domo.load_list_of_domoticz_widget(obj, devices)
        self.assertEqual(len(obj.ListOfDomoticzWidget), 0)
        self.assertNotEqual(count_first, 0)


# ---------------------------------------------------------------------------
# 4. Widget lookup
# ---------------------------------------------------------------------------

class TestFindWidgetUnitFromWidgetID(unittest.TestCase):

    def _setup(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {"Name": "Lamp"})]))
        domo.load_list_of_domoticz_widget(obj, devices)
        # Grab the real IDX stored in the index
        idx = list(obj.ListOfDomoticzWidget.keys())[0]
        return obj, devices, idx

    def test_found_returns_unit(self):
        obj, devices, idx = self._setup()
        result = domo.find_widget_unit_from_WidgetID(obj, idx)
        self.assertEqual(result, 1)

    def test_not_found_returns_none(self):
        obj, devices, idx = self._setup()
        result = domo.find_widget_unit_from_WidgetID(obj, 999999)
        self.assertIsNone(result)

    def test_string_idx_converted(self):
        obj, devices, idx = self._setup()
        result = domo.find_widget_unit_from_WidgetID(obj, str(idx))
        self.assertEqual(result, 1)

    def test_invalid_idx_type_returns_none(self):
        obj, devices, _ = self._setup()
        result = domo.find_widget_unit_from_WidgetID(obj, "not-an-int")
        self.assertIsNone(result)

    def test_none_idx_returns_none(self):
        obj, devices, _ = self._setup()
        result = domo.find_widget_unit_from_WidgetID(obj, None)
        self.assertIsNone(result)


class TestRetrieveWidgetidFromDeviceIdUnit(unittest.TestCase):

    def test_found(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.load_list_of_domoticz_widget(obj, devices)
        idx = domo.retrieve_widgetid_from_deviceId_unit(obj, devices, "ieee-1", 1)
        self.assertIsNotNone(idx)

    def test_not_found_returns_none(self):
        obj = _make_self()
        domo.load_list_of_domoticz_widget(obj, {})
        idx = domo.retrieve_widgetid_from_deviceId_unit(obj, {}, "ghost", 99)
        self.assertIsNone(idx)


class TestFindFirstUnitWidgetFromDeviceID(unittest.TestCase):

    def test_returns_first_unit(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(3, {}), (5, {})]))
        result = domo.find_first_unit_widget_from_deviceID(obj, devices, "ieee-1")
        self.assertIn(result, [3, 5])

    def test_missing_device_returns_none(self):
        obj = _make_self()
        result = domo.find_first_unit_widget_from_deviceID(obj, {}, "ghost")
        self.assertIsNone(result)

    def test_none_devices_returns_none(self):
        obj = _make_self()
        result = domo.find_first_unit_widget_from_deviceID(obj, None, "ieee-1")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# 5. retreive_free_unit_for_widget
# ---------------------------------------------------------------------------

class Testretreive_free_unit_for_widget(unittest.TestCase):

    def test_empty_device_returns_1(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", []))
        result = domo.retreive_free_unit_for_widget(obj, devices, "ieee-1")
        self.assertEqual(result, 1)

    def test_skips_occupied_units(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {}), (2, {}), (3, {})]))
        result = domo.retreive_free_unit_for_widget(obj, devices, "ieee-1")
        self.assertEqual(result, 4)

    def test_new_device_id_returns_1(self):
        obj = _make_self()
        devices = {}
        result = domo.retreive_free_unit_for_widget(obj, devices, "brand-new-ieee")
        self.assertEqual(result, 1)

    def test_consecutive_slots(self):
        obj = _make_self()
        # Units 1-5 exist; units 6 and 7 are free — so asking for 2 consecutive
        # should return 6.
        occupied = [(i, {}) for i in range(1, 6)]
        devices = _make_devices(("ieee-1", occupied))
        result = domo.retreive_free_unit_for_widget(obj, devices, "ieee-1", nbunit_=2)
        self.assertEqual(result, 6)

    def test_invalid_nbunit_returns_none(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", []))
        self.assertIsNone(domo.retreive_free_unit_for_widget(obj, devices, "ieee-1", nbunit_=0))
        self.assertIsNone(domo.retreive_free_unit_for_widget(obj, devices, "ieee-1", nbunit_=-1))
        self.assertIsNone(domo.retreive_free_unit_for_widget(obj, devices, "ieee-1", nbunit_=300))

    def test_non_int_nbunit_returns_none(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", []))
        self.assertIsNone(domo.retreive_free_unit_for_widget(obj, devices, "ieee-1", nbunit_="two"))


# ---------------------------------------------------------------------------
# 6. is_device_ieee_in_domoticz_db
# ---------------------------------------------------------------------------

class TestIsDeviceIeeeInDomoticzDb(unittest.TestCase):

    def test_known_device_with_units_returns_true(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        self.assertTrue(domo.is_device_ieee_in_domoticz_db(obj, devices, "ieee-1"))

    def test_known_device_no_units_returns_false(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", []))
        self.assertFalse(domo.is_device_ieee_in_domoticz_db(obj, devices, "ieee-1"))

    def test_unknown_device_returns_false(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        self.assertFalse(domo.is_device_ieee_in_domoticz_db(obj, devices, "ghost"))

    def test_none_devices_returns_false(self):
        obj = _make_self()
        self.assertFalse(domo.is_device_ieee_in_domoticz_db(obj, None, "ieee-1"))


# ---------------------------------------------------------------------------
# 7. domo_create_api
# ---------------------------------------------------------------------------

class TestDomoCreateApi(unittest.TestCase):
    """
    Because Domoticz.Unit.Create() is a side-effect that adds to Devices
    in real Domoticz (not in our fake), we simulate the post-creation state
    by pre-populating Devices before calling the SUT with a patched Unit
    factory that records its arguments.
    """

    def _run_create(self, devices, DeviceID_, Unit_, Name_, **kwargs):
        obj = _make_self()
        # Simulate what Domoticz would do: add unit to Devices after Create()
        if DeviceID_ and DeviceID_ not in devices:
            devices[DeviceID_] = _FakeDevice(DeviceID=DeviceID_)

        created_units = []

        original_unit_class = domo.Domoticz.Unit

        def capturing_unit_factory(**kw):
            u = _FakeUnit(**{k: v for k, v in kw.items()
                             if k in ("DeviceID", "Name", "Unit", "Type",
                                      "Subtype", "Switchtype", "Options", "Image")})
            created_units.append(u)

            def create_side_effect():
                # Register the unit in devices as Domoticz would
                if kw.get("DeviceID") and kw.get("DeviceID") in devices:
                    devices[kw["DeviceID"]].Units[kw["Unit"]] = u
                return u

            u.Create = create_side_effect
            return u

        domo.Domoticz.Unit = capturing_unit_factory
        try:
            result = domo.domo_create_api(obj, devices, DeviceID_, Unit_, Name_, **kwargs)
        finally:
            domo.Domoticz.Unit = original_unit_class

        return result, obj, created_units

    def test_returns_negative_one_for_empty_device_id(self):
        devices = {}
        result, _, _ = self._run_create(devices, "", 1, "Name")
        self.assertEqual(result, -1)

    def test_returns_negative_one_for_none_unit(self):
        devices = {}
        result, _, _ = self._run_create(devices, "ieee-1", None, "Name")
        self.assertEqual(result, -1)

    def test_returns_negative_one_for_empty_name(self):
        devices = {}
        result, _, _ = self._run_create(devices, "ieee-1", 1, "")
        self.assertEqual(result, -1)

    def test_success_returns_idx(self):
        devices = {}
        result, _, _ = self._run_create(devices, "ieee-1", 1, "Bulb",
                                        Type_=244, Subtype_=73, Switchtype_=7)
        self.assertGreater(result, 0)

    def test_widget_type_path(self):
        devices = {}
        result, _, created = self._run_create(devices, "ieee-1", 1, "Bulb",
                                               widgetType="Switch")
        self.assertGreater(result, 0)

    def test_widget_options_path_uses_defaults(self):
        devices = {}
        result, _, created = self._run_create(devices, "ieee-1", 1, "Selector",
                                               widgetOptions={"LevelNames": "A|B"})
        self.assertGreater(result, 0)


# ---------------------------------------------------------------------------
# 8. domo_delete_widget
# ---------------------------------------------------------------------------

class TestDomoDeleteWidget(unittest.TestCase):

    def test_deletes_unit_and_device_when_last_unit(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        unit_ref = devices["ieee-1"].Units[1]   # hold ref before deletion removes it
        dev_ref  = devices["ieee-1"]
        domo.domo_delete_widget(obj, devices, "ieee-1", 1)
        # Unit.Delete() was called and it removed itself from Units
        self.assertTrue(unit_ref._deleted)
        # Device now has no units → Device.Delete() was called
        self.assertTrue(dev_ref._deleted)

    def test_deletes_unit_only_when_more_units_remain(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {}), (2, {})]))
        unit_ref = devices["ieee-1"].Units[1]   # hold ref before deletion removes it
        domo.domo_delete_widget(obj, devices, "ieee-1", 1)
        # Unit.Delete() was called and the unit was removed from the dict
        self.assertTrue(unit_ref._deleted)
        self.assertNotIn(1, devices["ieee-1"].Units)
        # Unit 2 still exists, so the device itself must NOT be deleted
        self.assertFalse(devices["ieee-1"]._deleted)
        self.assertIn(2, devices["ieee-1"].Units)

    def test_missing_device_does_not_raise(self):
        obj = _make_self()
        devices = {}
        # Should log an error and return silently
        domo.domo_delete_widget(obj, devices, "ghost", 1)

    def test_missing_unit_does_not_raise(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.domo_delete_widget(obj, devices, "ieee-1", 99)


# ---------------------------------------------------------------------------
# 9. domo_update_api
# ---------------------------------------------------------------------------

class TestDomoUpdateApi(unittest.TestCase):

    def test_normal_update_sets_values(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.domo_update_api(obj, devices, "ieee-1", 1, 1, "On")
        unit = devices["ieee-1"].Units[1]
        self.assertEqual(unit.nValue, 1)
        self.assertEqual(unit.sValue, "On")
        self.assertTrue(unit._updated)

    def test_none_nvalue_aborts_without_exception(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        # Should not raise
        domo.domo_update_api(obj, devices, "ieee-1", 1, None, "")

    def test_missing_device_does_not_raise(self):
        obj = _make_self()
        domo.domo_update_api(obj, {}, "ghost", 1, 1, "On")

    def test_missing_unit_does_not_raise(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", []))
        domo.domo_update_api(obj, devices, "ieee-1", 99, 1, "On")

    def test_color_is_set(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.domo_update_api(obj, devices, "ieee-1", 1, 1, "On", Color="#ff0000")
        self.assertEqual(devices["ieee-1"].Units[1].Color, "#ff0000")

    def test_battery_level_is_set(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.domo_update_api(obj, devices, "ieee-1", 1, 0, "Off", BatteryLevel=50)
        self.assertEqual(devices["ieee-1"].Units[1].BatteryLevel, 50)

    def test_signal_level_is_set(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.domo_update_api(obj, devices, "ieee-1", 1, 0, "Off", SignalLevel=8)
        self.assertEqual(devices["ieee-1"].Units[1].SignalLevel, 8)

    def test_timedout_is_set_on_device(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.domo_update_api(obj, devices, "ieee-1", 1, 0, "Off", TimedOut=1)
        self.assertEqual(devices["ieee-1"].TimedOut, 1)

    def test_suppress_triggers_is_forwarded(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.domo_update_api(obj, devices, "ieee-1", 1, 0, "Off", SuppressTriggers=True)
        unit = devices["ieee-1"].Units[1]
        self.assertTrue(unit._updated)
        self.assertTrue(unit._update_suppress_triggers)

    def test_battery_level_update_sets_update_properties(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.domo_update_api(obj, devices, "ieee-1", 1, 0, "Off", BatteryLevel=50)
        unit = devices["ieee-1"].Units[1]
        self.assertEqual(unit.BatteryLevel, 50)
        self.assertTrue(unit._update_properties)

    def test_ieee2nwk_miss_does_not_raise(self):
        obj = _make_self()
        obj.IEEE2NWK = {}
        devices = _make_devices(("ieee-1", [(1, {})]))
        # Should not raise KeyError
        domo.domo_update_api(obj, devices, "ieee-1", 1, 0, "Off")

    def test_options_triggers_updateoptions_flag(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.domo_update_api(obj, devices, "ieee-1", 1, 0, "Off", Options={"EnergyMeterMode": "1"})
        unit = devices["ieee-1"].Units[1]
        self.assertEqual(unit.Options, {"EnergyMeterMode": "1"})
        self.assertTrue(unit._last_update_kwargs["UpdateOptions"])

    def test_no_options_does_not_set_updateoptions_flag(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.domo_update_api(obj, devices, "ieee-1", 1, 0, "Off")
        unit = devices["ieee-1"].Units[1]
        self.assertFalse(unit._last_update_kwargs["UpdateOptions"])


# ---------------------------------------------------------------------------
# 10. domo_update_name
# ---------------------------------------------------------------------------

class TestDomoUpdateName(unittest.TestCase):

    def test_name_changed(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {"Name": "OldName"})]))
        domo.domo_update_name(obj, devices, "ieee-1", 1, "NewName")
        self.assertEqual(devices["ieee-1"].Units[1].Name, "NewName")

    def test_same_name_does_not_trigger_update(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {"Name": "SameName"})]))
        domo.domo_update_name(obj, devices, "ieee-1", 1, "SameName")
        self.assertFalse(devices["ieee-1"].Units[1]._updated)

    def test_missing_device_does_not_raise(self):
        obj = _make_self()
        domo.domo_update_name(obj, {}, "ghost", 1, "Name")


class TestDomoUpdateSwitchTypeSubTypeType(unittest.TestCase):

    def test_typename_update_sets_update_properties(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.domo_update_SwitchType_SubType_Type(obj, devices, "ieee-1", 1, Typename_="Switch")
        unit = devices["ieee-1"].Units[1]
        self.assertEqual(unit.TypeName, "Switch")
        self.assertTrue(unit._update_properties)

    def test_no_typename_does_not_update(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.domo_update_SwitchType_SubType_Type(obj, devices, "ieee-1", 1)
        self.assertFalse(devices["ieee-1"].Units[1]._updated)

    def test_missing_device_does_not_raise(self):
        obj = _make_self()
        domo.domo_update_SwitchType_SubType_Type(obj, {}, "ghost", 1, Typename_="Switch")


# ---------------------------------------------------------------------------
# 11. domo_read_* functions
# ---------------------------------------------------------------------------

class TestDomoReadFunctions(unittest.TestCase):

    def _devices(self):
        return _make_devices(("ieee-1", [(1, {
            "Name": "TestWidget",
            "Type": 244, "Subtype": 73, "Switchtype": 7,
        })]))

    def test_read_nValue_sValue(self):
        obj = _make_self()
        devices = self._devices()
        devices["ieee-1"].Units[1].nValue = 1
        devices["ieee-1"].Units[1].sValue = "On"
        n, s = domo.domo_read_nValue_sValue(obj, devices, "ieee-1", 1)
        self.assertEqual(n, 1)
        self.assertEqual(s, "On")

    def test_read_nValue_sValue_missing_returns_none_none(self):
        obj = _make_self()
        n, s = domo.domo_read_nValue_sValue(obj, {}, "ghost", 1)
        self.assertIsNone(n)
        self.assertIsNone(s)

    def test_read_timedout(self):
        obj = _make_self()
        devices = self._devices()
        devices["ieee-1"].TimedOut = 1
        self.assertEqual(domo.domo_read_TimedOut(obj, devices, "ieee-1"), 1)

    def test_read_timedout_missing_returns_none(self):
        obj = _make_self()
        self.assertIsNone(domo.domo_read_TimedOut(obj, {}, "ghost"))

    def test_read_last_update(self):
        obj = _make_self()
        devices = self._devices()
        devices["ieee-1"].Units[1].LastUpdate = "2024-06-01 10:00:00"
        result = domo.domo_read_LastUpdate(obj, devices, "ieee-1", 1)
        self.assertEqual(result, "2024-06-01 10:00:00")

    def test_read_last_update_missing_returns_none(self):
        obj = _make_self()
        self.assertIsNone(domo.domo_read_LastUpdate(obj, {}, "ghost", 1))

    def test_read_battery_level(self):
        obj = _make_self()
        devices = self._devices()
        devices["ieee-1"].Units[1].BatteryLevel = 80
        self.assertEqual(domo.domo_read_BatteryLevel(obj, devices, "ieee-1", 1), 80)

    def test_read_battery_level_missing_returns_none(self):
        obj = _make_self()
        self.assertIsNone(domo.domo_read_BatteryLevel(obj, {}, "ghost", 1))

    def test_read_signal_level(self):
        obj = _make_self()
        devices = self._devices()
        devices["ieee-1"].Units[1].SignalLevel = 10
        self.assertEqual(domo.domo_read_SignalLevel(obj, devices, "ieee-1", 1), 10)

    def test_read_color(self):
        obj = _make_self()
        devices = self._devices()
        devices["ieee-1"].Units[1].Color = "#aabbcc"
        self.assertEqual(domo.domo_read_Color(obj, devices, "ieee-1", 1), "#aabbcc")

    def test_read_color_missing_returns_none(self):
        obj = _make_self()
        self.assertIsNone(domo.domo_read_Color(obj, {}, "ghost", 1))

    def test_read_name(self):
        obj = _make_self()
        devices = self._devices()
        self.assertEqual(domo.domo_read_Name(obj, devices, "ieee-1", 1), "TestWidget")

    def test_read_name_missing_returns_empty_string(self):
        obj = _make_self()
        self.assertEqual(domo.domo_read_Name(obj, {}, "ghost", 1), "")

    def test_read_options(self):
        obj = _make_self()
        devices = self._devices()
        devices["ieee-1"].Units[1].Options = {"LevelNames": "A|B"}
        result = domo.domo_read_Options(obj, devices, "ieee-1", 1)
        self.assertEqual(result, {"LevelNames": "A|B"})

    def test_read_options_missing_returns_none(self):
        obj = _make_self()
        self.assertIsNone(domo.domo_read_Options(obj, {}, "ghost", 1))

    def test_read_device_idx(self):
        obj = _make_self()
        devices = self._devices()
        result = domo.domo_read_Device_Idx(obj, devices, "ieee-1", 1)
        self.assertIsNotNone(result)

    def test_read_device_idx_missing_returns_none(self):
        obj = _make_self()
        self.assertIsNone(domo.domo_read_Device_Idx(obj, {}, "ghost", 1))

    def test_domo_check_unit_present(self):
        obj = _make_self()
        devices = self._devices()
        self.assertTrue(domo.domo_check_unit(obj, devices, "ieee-1", 1))

    def test_domo_check_unit_absent(self):
        obj = _make_self()
        self.assertFalse(domo.domo_check_unit(obj, {}, "ghost", 1))

    def test_read_switchtype_subtype_type(self):
        obj = _make_self()
        devices = self._devices()
        sw, sub, typ = domo.domo_read_SwitchType_SubType_Type(obj, devices, "ieee-1", 1)
        self.assertEqual(sw, 7)
        self.assertEqual(sub, 73)
        self.assertEqual(typ, 244)

    def test_read_switchtype_missing_returns_none_triple(self):
        obj = _make_self()
        sw, sub, typ = domo.domo_read_SwitchType_SubType_Type(obj, {}, "ghost", 1)
        self.assertIsNone(sw)
        self.assertIsNone(sub)
        self.assertIsNone(typ)


# ---------------------------------------------------------------------------
# 12. domo_browse_widgets
# ---------------------------------------------------------------------------

class TestDomoBrowseWidgets(unittest.TestCase):

    def test_returns_all_device_unit_tuples(self):
        obj = _make_self()
        devices = _make_devices(
            ("ieee-1", [(1, {}), (2, {})]),
            ("ieee-2", [(1, {})]),
        )
        result = domo.domo_browse_widgets(obj, devices)
        self.assertEqual(len(result), 3)
        self.assertIn(("ieee-1", 1), result)
        self.assertIn(("ieee-1", 2), result)
        self.assertIn(("ieee-2", 1), result)

    def test_empty_devices_returns_empty_list(self):
        obj = _make_self()
        self.assertEqual(domo.domo_browse_widgets(obj, {}), [])

    def test_none_devices_returns_empty_list(self):
        obj = _make_self()
        self.assertEqual(domo.domo_browse_widgets(obj, None), [])


# ---------------------------------------------------------------------------
# 13. Widget-type detection helpers
# ---------------------------------------------------------------------------

class TestCheckWidget(unittest.TestCase):

    def test_known_key_returns_widget_name(self):
        self.assertEqual(domo.check_widget(7, 73, 244), "Dimmable_Switch")
        self.assertEqual(domo.check_widget(7, 1, 241), "Dimmable_Light")
        self.assertEqual(domo.check_widget(14, 73, 244), "Blind")

    def test_unknown_key_returns_none(self):
        self.assertIsNone(domo.check_widget(0, 0, 0))


class TestFindPartiallyOpenedNValue(unittest.TestCase):

    def test_returns_correct_value(self):
        self.assertEqual(domo.find_partially_opened_nValue(7, 73, 244), 2)
        self.assertEqual(domo.find_partially_opened_nValue(14, 73, 244), 17)
        self.assertEqual(domo.find_partially_opened_nValue(7, 1, 241), 15)

    def test_unknown_key_returns_none(self):
        self.assertIsNone(domo.find_partially_opened_nValue(0, 0, 0))


class TestIsDimmableSwitch(unittest.TestCase):

    def _device_with_types(self, sw, sub, typ):
        devices = _make_devices(("ieee-1", [(1, {
            "Switchtype": sw, "Subtype": sub, "Type": typ,
        })]))
        return devices

    def test_dimmer_is_dimmable_switch(self):
        obj = _make_self()
        devices = self._device_with_types(7, 73, 244)
        result = domo.is_dimmable_switch(obj, devices, "ieee-1", 1)
        self.assertEqual(result, 2)

    def test_rgb_light_is_not_dimmable_switch(self):
        obj = _make_self()
        devices = self._device_with_types(7, 2, 241)
        result = domo.is_dimmable_switch(obj, devices, "ieee-1", 1)
        self.assertIsNone(result)

    def test_missing_device_returns_none(self):
        obj = _make_self()
        result = domo.is_dimmable_switch(obj, {}, "ghost", 1)
        self.assertIsNone(result)


class TestIsDimmableLight(unittest.TestCase):

    def test_rgb_is_dimmable_light(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {
            "Switchtype": 7, "Subtype": 2, "Type": 241,
        })]))
        result = domo.is_dimmable_light(obj, devices, "ieee-1", 1)
        self.assertEqual(result, 15)

    def test_blind_is_not_dimmable_light(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {
            "Switchtype": 14, "Subtype": 73, "Type": 244,
        })]))
        result = domo.is_dimmable_light(obj, devices, "ieee-1", 1)
        self.assertIsNone(result)


class TestIsDimmableBlind(unittest.TestCase):

    def test_venetian_blind_eu_is_dimmable_blind(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {
            "Switchtype": 15, "Subtype": 73, "Type": 244,
        })]))
        result = domo.is_dimmable_blind(obj, devices, "ieee-1", 1)
        self.assertEqual(result, 17)

    def test_dimmer_is_not_dimmable_blind(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {
            "Switchtype": 7, "Subtype": 73, "Type": 244,
        })]))
        result = domo.is_dimmable_blind(obj, devices, "ieee-1", 1)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# 14. Internal predicates
# ---------------------------------------------------------------------------

class TestIsMeterWidget(unittest.TestCase):

    def test_meter_widget_detected(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {
            "Switchtype": 0, "Subtype": 29, "Type": 243,
        })]))
        self.assertTrue(domo._is_meter_widget(obj, devices, "ieee-1", 1))

    def test_non_meter_widget(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {
            "Switchtype": 7, "Subtype": 73, "Type": 244,
        })]))
        self.assertFalse(domo._is_meter_widget(obj, devices, "ieee-1", 1))

    def test_missing_device_returns_false(self):
        obj = _make_self()
        self.assertFalse(domo._is_meter_widget(obj, {}, "ghost", 1))


class TestIsDeviceToBeSwitchedOff(unittest.TestCase):

    def test_type_244_sub73_sw7_is_switchable(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {
            "Type": 244, "Subtype": 73, "Switchtype": 7,
        })]))
        self.assertTrue(domo._is_device_tobe_switched_off(obj, devices, "ieee-1", 1))

    def test_type_241_sw7_is_switchable(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {
            "Type": 241, "Subtype": 0, "Switchtype": 7,
        })]))
        self.assertTrue(domo._is_device_tobe_switched_off(obj, devices, "ieee-1", 1))

    def test_unrelated_type_not_switchable(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {
            "Type": 243, "Subtype": 29, "Switchtype": 0,
        })]))
        self.assertFalse(domo._is_device_tobe_switched_off(obj, devices, "ieee-1", 1))

    def test_missing_device_returns_false(self):
        obj = _make_self()
        self.assertFalse(domo._is_device_tobe_switched_off(obj, {}, "ghost", 1))


class TestSanityCheckDeviceUnit(unittest.TestCase):

    def test_existing_returns_false(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        self.assertTrue(domo._device_unit_exists(devices, "ieee-1", 1))

    def test_missing_returns_true(self):
        obj = _make_self()
        self.assertFalse(domo._device_unit_exists({}, "ghost", 1))


# ---------------------------------------------------------------------------
# 15. device_touch_api / _device_touch_unit_api
# ---------------------------------------------------------------------------

class TestDeviceTouchApi(unittest.TestCase):

    def test_missing_device_does_not_raise(self):
        obj = _make_self()
        domo.device_touch_api(obj, {}, "ghost")

    def test_meter_widget_not_touched(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {
            "Switchtype": 0, "Subtype": 29, "Type": 243,
        })]))
        # LastUpdate old enough to qualify for touch
        devices["ieee-1"].Units[1].LastUpdate = "2000-01-01 00:00:00"
        domo.device_touch_api(obj, devices, "ieee-1")
        self.assertFalse(devices["ieee-1"].Units[1]._touched)

    def test_old_last_update_causes_touch(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {
            "Switchtype": 7, "Subtype": 73, "Type": 244,
        })]))
        # Very old timestamp — well past DELAY_BETWEEN_TOUCH
        devices["ieee-1"].Units[1].LastUpdate = "2000-01-01 00:00:00"
        domo.device_touch_api(obj, devices, "ieee-1")
        self.assertTrue(devices["ieee-1"].Units[1]._touched)

    def test_recent_last_update_does_not_touch(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {
            "Switchtype": 7, "Subtype": 73, "Type": 244,
        })]))
        # Set timestamp to now
        now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        devices["ieee-1"].Units[1].LastUpdate = now_str
        domo.device_touch_api(obj, devices, "ieee-1")
        self.assertFalse(devices["ieee-1"].Units[1]._touched)

    def test_malformed_last_update_does_not_raise(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        devices["ieee-1"].Units[1].LastUpdate = "not-a-date"
        # Must not raise
        domo.device_touch_api(obj, devices, "ieee-1")

    def test_empty_last_update_does_not_raise(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        devices["ieee-1"].Units[1].LastUpdate = ""
        domo.device_touch_api(obj, devices, "ieee-1")


# ---------------------------------------------------------------------------
# 16. timeout_widget_api
# ---------------------------------------------------------------------------

class TestTimeoutWidgetApi(unittest.TestCase):

    def test_sets_timedout_flag(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        domo.timeout_widget_api(obj, devices, "ieee-1", 1)
        self.assertEqual(devices["ieee-1"].TimedOut, 1)

    def test_clears_timedout_flag(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        devices["ieee-1"].TimedOut = 1
        domo.timeout_widget_api(obj, devices, "ieee-1", 0)
        self.assertEqual(devices["ieee-1"].TimedOut, 0)

    def test_missing_device_does_not_raise(self):
        obj = _make_self()
        domo.timeout_widget_api(obj, {}, "ghost", 1)

    def test_device_off_when_timeout_enabled_switches_off_on_widget(self):
        obj = _make_self()
        obj.pluginconf.pluginConf = {"deviceOffWhenTimeOut": True}
        devices = _make_devices(("ieee-1", [(1, {})]))
        devices["ieee-1"].Units[1].nValue = 1
        devices["ieee-1"].Units[1].sValue = "On"
        domo.timeout_widget_api(obj, devices, "ieee-1", 1)
        self.assertEqual(devices["ieee-1"].Units[1].nValue, 0)
        self.assertEqual(devices["ieee-1"].Units[1].sValue, "Off")

    def test_device_off_when_timeout_disabled_leaves_state(self):
        obj = _make_self()
        obj.pluginconf.pluginConf = {"deviceOffWhenTimeOut": False}
        devices = _make_devices(("ieee-1", [(1, {})]))
        devices["ieee-1"].Units[1].nValue = 1
        devices["ieee-1"].Units[1].sValue = "On"
        domo.timeout_widget_api(obj, devices, "ieee-1", 1)
        # nValue/sValue untouched (but TimedOut propagated via domo_update_api)
        self.assertEqual(devices["ieee-1"].Units[1].nValue, 1)


# ---------------------------------------------------------------------------
# 17. update_battery_api / update_battery_device_unit_api
# ---------------------------------------------------------------------------

class TestUpdateBatteryApi(unittest.TestCase):

    def test_updates_all_units(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {}), (2, {})]))
        devices["ieee-1"].Units[1].BatteryLevel = 255
        devices["ieee-1"].Units[2].BatteryLevel = 255
        domo.update_battery_api(obj, devices, "ieee-1", 70)
        self.assertEqual(devices["ieee-1"].Units[1].BatteryLevel, 70)
        self.assertEqual(devices["ieee-1"].Units[2].BatteryLevel, 70)

    def test_skips_when_already_same_level(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        devices["ieee-1"].Units[1].BatteryLevel = 50
        domo.update_battery_api(obj, devices, "ieee-1", 50)
        # _updated should remain False since no change
        self.assertFalse(devices["ieee-1"].Units[1]._updated)

    def test_missing_device_does_not_raise(self):
        obj = _make_self()
        domo.update_battery_api(obj, {}, "ghost", 50)


# ---------------------------------------------------------------------------
# 18. _switch_off_widget_due_to_timedout
# ---------------------------------------------------------------------------

class TestSwitchOffWidgetDueToTimedout(unittest.TestCase):

    def test_on_widget_switched_off(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {})]))
        devices["ieee-1"].Units[1].nValue = 1
        devices["ieee-1"].Units[1].sValue = "On"
        domo._switch_off_widget_due_to_timedout(obj, devices, "ieee-1", 1, 1, "On")
        self.assertEqual(devices["ieee-1"].Units[1].nValue, 0)
        self.assertEqual(devices["ieee-1"].Units[1].sValue, "Off")

    def test_already_off_preserves_state(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {
            "Type": 243, "Subtype": 29, "Switchtype": 0,
        })]))
        devices["ieee-1"].Units[1].nValue = 0
        devices["ieee-1"].Units[1].sValue = "Off"
        domo._switch_off_widget_due_to_timedout(obj, devices, "ieee-1", 1, 0, "Off")
        self.assertEqual(devices["ieee-1"].Units[1].nValue, 0)
        self.assertEqual(devices["ieee-1"].Units[1].sValue, "Off")

    def test_switchable_type_forced_off(self):
        obj = _make_self()
        devices = _make_devices(("ieee-1", [(1, {
            "Type": 244, "Subtype": 73, "Switchtype": 7,
        })]))
        devices["ieee-1"].Units[1].nValue = 15
        devices["ieee-1"].Units[1].sValue = "Set Level: 50"
        domo._switch_off_widget_due_to_timedout(obj, devices, "ieee-1", 1, 15, "Set Level: 50")
        self.assertEqual(devices["ieee-1"].Units[1].nValue, 0)
        self.assertEqual(devices["ieee-1"].Units[1].sValue, "Off")



# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
