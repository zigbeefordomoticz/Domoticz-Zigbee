#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_logging_error_context.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the JSON sanitation of the error-history context, and of the device record it holds
(Classes/LoggingManagement.py: json_safe / device_infos / loggingBuildContext).

The error history is persisted with json.dumps(); a value it cannot serialize
aborts the write and used to cost the whole history. Device entries legitimately
hold non-JSON values - RollingLQI is a collections.deque set by
Modules/tools_sqn.py - so anything reachable from the context must be sanitized.

Run with:
    pytest tests/Classes/test_logging_error_context.py -v
"""

import ast
import json
import sys
import threading
import unittest
from collections import deque
from pathlib import Path
from unittest.mock import MagicMock, patch

# Classes.LoggingManagement imports Modules.domoticzAbstractLayer, which does
# `import DomoticzEx as Domoticz`. tests/conftest.py installs the DomoticzEx fake at
# import time, before collection, so it is already in place here.
import Classes.LoggingManagement as lm  # noqa: E402
from Classes.ThreadSafeDeviceDict import ThreadSafeDeviceDict  # noqa: E402


def _make_log(list_of_devices=None):
    """Return a LoggingManagement-like object carrying only what the SUT reads."""
    obj = MagicMock()
    obj.ListOfDevices = list_of_devices if list_of_devices is not None else {}
    obj.PluginHealth = {"Txt": "Ready"}
    obj.permitTojoin = {"Duration": 0, "Starttime": 1791140376}
    return obj


def _assert_json_round_trip(testcase, value):
    """json.dumps must accept it, exactly as loggingWriteErrorHistory does."""
    try:
        return json.loads(json.dumps(value))
    except TypeError as e:
        testcase.fail("not JSON serializable: %s" % e)


# ---------------------------------------------------------------------------
# json_safe
# ---------------------------------------------------------------------------

class TestJsonSafeScalars(unittest.TestCase):

    def test_scalars_are_passed_through_unchanged(self):
        for value in ("text", 42, 3.5, True, False, None):
            self.assertEqual(lm.json_safe(value), value)

    def test_bytes_are_rendered_as_hex(self):
        self.assertEqual(lm.json_safe(b"\x01\xab"), "01ab")
        self.assertEqual(lm.json_safe(bytearray(b"\xff")), "ff")

    def test_exception_is_rendered_with_its_type(self):
        self.assertEqual(lm.json_safe(ValueError("boom")), "ValueError: boom")

    def test_unknown_object_falls_back_to_repr(self):
        class Opaque:
            def __repr__(self):
                return "<opaque>"

        self.assertEqual(lm.json_safe(Opaque()), "<opaque>")


class TestJsonSafeContainers(unittest.TestCase):

    def test_deque_becomes_a_list(self):
        self.assertEqual(lm.json_safe(deque([1, 2, 3], maxlen=10)), [1, 2, 3])

    def test_tuple_set_frozenset_become_lists(self):
        self.assertEqual(lm.json_safe((1, 2)), [1, 2])
        self.assertEqual(sorted(lm.json_safe({1, 2})), [1, 2])
        self.assertEqual(sorted(lm.json_safe(frozenset((1, 2)))), [1, 2])

    def test_nested_deque_inside_dict_is_converted(self):
        result = lm.json_safe({"RollingLQI": deque([250, 240], maxlen=10)})
        self.assertEqual(result, {"RollingLQI": [250, 240]})

    def test_deque_nested_under_several_levels_is_converted(self):
        source = {"Ep": {"01": {"History": deque([1], maxlen=5)}}}
        self.assertEqual(lm.json_safe(source), {"Ep": {"01": {"History": [1]}}})

    def test_non_string_dict_keys_are_stringified(self):
        result = lm.json_safe({(1, 2): "tuple-key"})
        self.assertEqual(result, {"(1, 2)": "tuple-key"})
        _assert_json_round_trip(self, result)

    def test_int_and_bool_dict_keys_are_kept(self):
        # json.dumps accepts these natively and renders them as strings.
        result = lm.json_safe({1: "a", True: "b", None: "c"})
        self.assertEqual(result, {1: "a", True: "b", None: "c"})
        _assert_json_round_trip(self, result)

    def test_result_does_not_alias_the_source(self):
        source = {"Ep": {"01": ["ClusterType"]}}
        result = lm.json_safe(source)
        result["Ep"]["01"].append("mutated")
        self.assertEqual(source["Ep"]["01"], ["ClusterType"])


class TestJsonSafeGuards(unittest.TestCase):

    def test_self_referencing_dict_does_not_recurse_forever(self):
        source = {"name": "loop"}
        source["self"] = source
        _assert_json_round_trip(self, lm.json_safe(source))

    def test_self_referencing_list_does_not_recurse_forever(self):
        source = [1]
        source.append(source)
        _assert_json_round_trip(self, lm.json_safe(source))

    def test_depth_guard_keeps_values_within_the_limit(self):
        # One dict per level, well under JSON_SAFE_MAX_DEPTH.
        source = {"a": {"b": {"c": "leaf"}}}
        self.assertEqual(lm.json_safe(source), source)


class TestJsonSafeLiveContainers(unittest.TestCase):
    """The context is built in the logging thread, from containers the other threads write to."""

    def test_a_key_added_meanwhile_does_not_raise(self):
        class Growing:
            # repr() is called while the dict is walked: what another thread could do then
            def __repr__(self):
                source["added"] = 1
                return "<growing>"

        source = {"first": Growing(), "second": 2}
        self.assertEqual(lm.json_safe(source), {"first": "<growing>", "second": 2})

    def test_an_item_added_meanwhile_does_not_raise(self):
        class Growing:
            def __repr__(self):
                source.append(1)
                return "<growing>"

        source = deque([Growing(), 2], maxlen=10)
        self.assertEqual(lm.json_safe(source), ["<growing>", 2])

    def test_thread_safe_dict_is_rendered_as_a_dict(self):
        self.assertEqual(lm.json_safe(ThreadSafeDeviceDict({"Ep": {"01": {}}})), {"Ep": {"01": {}}})

    def test_a_dict_written_by_another_thread(self):
        source = {str(n): n for n in range(500)}
        stop = threading.Event()

        def writer():
            n = 0
            while not stop.is_set():
                source["k%s" % n] = n
                source.pop("k%s" % (n - 20), None)
                n += 1

        interval = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)
        thread = threading.Thread(target=writer, daemon=True)
        thread.start()
        try:
            for _ in range(50):
                lm.json_safe(source)
        finally:
            stop.set()
            thread.join(5)
            sys.setswitchinterval(interval)


# ---------------------------------------------------------------------------
# loggingBuildContext
# ---------------------------------------------------------------------------

class TestLoggingBuildContext(unittest.TestCase):

    def _device_infos(self, device):
        context = lm.loggingBuildContext(
            _make_log({"abcd": device}), "MainThread 1040", "WidgetCreation",
            "Domoticz widget creation failed.", "abcd")
        return _assert_json_round_trip(self, context)["DeviceInfos"]

    def test_device_infos_identify_the_device(self):
        # ZDeviceName, Model and Manufacturer are what the WebUI error page reads
        infos = self._device_infos({
            "IEEE": "a4c138e090a23a63", "ZDeviceName": "Hall button", "Model": "TS0041",
            "Manufacturer": "1002", "Status": "inDB", "Battery": 87, "Param": {"Disabled": 0},
        })
        self.assertEqual(infos, {
            "IEEE": "a4c138e090a23a63", "ZDeviceName": "Hall button", "Model": "TS0041",
            "Manufacturer": "1002", "Status": "inDB", "Battery": 87, "Param": {"Disabled": 0},
        })

    def test_device_infos_list_the_clusters_and_widgets_of_each_endpoint(self):
        infos = self._device_infos({"Ep": {"01": {
            "Type": "Button/Temp", "ClusterType": {"1234": "Button"},
            "0402": {"0000": "2150"}, "0006": {"0000": "01"},
        }}})
        self.assertEqual(infos["Ep"], {"01": {
            "Clusters": ["0006", "0402"], "Type": "Button/Temp", "ClusterType": {"1234": "Button"}}})

    def test_device_infos_hold_nothing_that_is_not_named(self):
        # IAS_KEYPAD has the PIN codes of an alarm keypad
        infos = self._device_infos({
            "Model": "keypad", "IAS_KEYPAD": {"Last": {"PIN": "fake-pin"}},
            "RollingLQI": deque([250], maxlen=10), "Neighbours": [{"_NwkId": "1234"}],
        })
        self.assertEqual(infos, {"Model": "keypad"})

    def test_device_infos_of_a_thread_safe_registry_are_a_dict(self):
        registry = ThreadSafeDeviceDict({"abcd": {"Model": "TS0041", "Ep": {"01": {"0006": {}}}}})
        context = lm.loggingBuildContext(
            _make_log(registry), "MainThread 1040", "WidgetCreation", "failed", "abcd")
        self.assertEqual(context["DeviceInfos"]["Model"], "TS0041")
        self.assertEqual(context["DeviceInfos"]["Ep"]["01"]["Clusters"], ["0006"])

    def test_device_infos_of_a_damaged_entry_do_not_raise(self):
        for device in ({"Ep": {}}, {"Ep": "text"}, {"Ep": {"01": None}}, {"Ep": {"01": {}}}, {}):
            with self.subTest(device=device):
                self.assertIsInstance(self._device_infos(device), dict)

    def test_no_device_infos_when_the_entry_is_not_a_record(self):
        context = lm.loggingBuildContext(
            _make_log({"abcd": None}), "MainThread 1040", "WidgetCreation", "failed", "abcd")
        self.assertNotIn("DeviceInfos", context)

    def test_device_infos_snapshot_is_detached_from_live_entry(self):
        devices = {"abcd": {"Ep": {"01": {"ClusterType": {}}}}}
        obj = _make_log(devices)

        context = lm.loggingBuildContext(
            obj, "MainThread 1040", "WidgetCreation", "failed", "abcd")
        context["DeviceInfos"]["Ep"]["01"]["ClusterType"]["12345"] = "Switch"

        self.assertEqual(devices["abcd"]["Ep"]["01"]["ClusterType"], {})

    def test_no_device_infos_when_nwkid_is_unknown(self):
        obj = _make_log({"abcd": {"Model": "TS0041"}})

        context = lm.loggingBuildContext(
            obj, "MainThread 1040", "WidgetCreation", "failed", None)

        self.assertNotIn("DeviceInfos", context)
        self.assertIsNone(context["nwkid"])
        _assert_json_round_trip(self, context)

    def test_caller_context_is_sanitized(self):
        obj = _make_log()

        context = lm.loggingBuildContext(
            obj, "MainThread 1040", "WidgetCreation", "failed", None,
            context={"Unit": 1, "Exception": RuntimeError("nope"),
                     "Allocated": deque([1, 2], maxlen=4)})

        restored = _assert_json_round_trip(self, context)
        self.assertEqual(restored["context"]["Unit"], 1)
        self.assertEqual(restored["context"]["Exception"], "RuntimeError: nope")
        self.assertEqual(restored["context"]["Allocated"], [1, 2])

    def test_non_dict_caller_context_is_stringified(self):
        obj = _make_log()

        context = lm.loggingBuildContext(
            obj, "MainThread 1040", "WidgetCreation", "failed", None,
            context="plain reason")

        self.assertEqual(context["context"], "plain reason")

    def test_expected_envelope_keys_are_present(self):
        obj = _make_log()

        context = lm.loggingBuildContext(
            obj, "MainThread 1040", "WidgetCreation", "failed", "abcd")

        for key in ("Time", "PermitToJoin", "PluginHealth", "Thread",
                    "nwkid", "Module", "message"):
            self.assertIn(key, context)
        self.assertEqual(context["PluginHealth"], "Ready")
        self.assertEqual(context["Thread"], "MainThread 1040")


# ---------------------------------------------------------------------------
# The registry the logger reads
# ---------------------------------------------------------------------------

class TestListOfDevicesOfTheLogger(unittest.TestCase):
    """
    LoadDeviceList() replaces the registry the logger was given when it was created: without
    an update it looks the devices up in an empty one, and no error has its DeviceInfos.
    """

    def test_the_updated_registry_is_the_one_read(self):
        obj = _make_log({})
        lm.LoggingManagement.loggingUpdateListOfDevices(obj, {"abcd": {"Model": "TS0041"}})
        context = lm.loggingBuildContext(obj, "MainThread 1040", "Input", "failed", "abcd")
        self.assertEqual(context["DeviceInfos"], {"Model": "TS0041"})

    def test_on_start_updates_it_right_after_the_load(self):
        # Importing plugin.py would pull the whole plugin in: checked on the source
        source = (Path(__file__).resolve().parents[2] / "plugin.py").read_text(encoding="utf-8")
        plugin_class = next(node for node in ast.parse(source).body if isinstance(node, ast.ClassDef))
        on_start = next(node for node in plugin_class.body if getattr(node, "name", None) == "onStart")
        calls = [(node.lineno, ast.unparse(node)) for node in ast.walk(on_start) if isinstance(node, ast.Call)]
        loaded = [line for line, call in calls if call == "LoadDeviceList(self)"]
        updated = [line for line, call in calls if call == "self.log.loggingUpdateListOfDevices(self.ListOfDevices)"]
        next_step = [line for line, call in calls if call == "load_plugin_stores(self)"]
        self.assertEqual((len(loaded), len(updated), len(next_step)), (1, 1, 1))
        self.assertTrue(loaded[0] < updated[0] < next_step[0])


# ---------------------------------------------------------------------------
# loggingWriteErrorHistory
# ---------------------------------------------------------------------------

class TestLoggingWriteErrorHistory(unittest.TestCase):
    """A serialization failure must not destroy the file already on disk."""

    def _make_writer(self, tmpdir, history):
        obj = MagicMock()
        obj.HardwareID = 1
        obj.pluginconf.pluginConf = {"pluginLogs": str(tmpdir)}
        obj.LogErrorHistory = history
        return obj

    def test_history_is_written(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            obj = self._make_writer(tmpdir, {"0": {"0": {"message": "ok"}}})
            lm.loggingWriteErrorHistory(obj)

            target = Path(tmpdir) / (lm.LOG_ERROR_HISTORY + "01.json")
            self.assertEqual(json.loads(target.read_text()),
                             {"0": {"0": {"message": "ok"}}})

    def test_unserializable_history_leaves_previous_file_intact(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / (lm.LOG_ERROR_HISTORY + "01.json")
            target.write_text('{"0": {"0": {"message": "previous"}}}\n')

            # A raw deque bypassing json_safe: the write must bail out, not truncate.
            obj = self._make_writer(tmpdir, {"0": {"0": deque([1], maxlen=2)}})
            with patch.object(lm, "domoticz_error_api") as reported:
                lm.loggingWriteErrorHistory(obj)

            self.assertEqual(json.loads(target.read_text()),
                             {"0": {"0": {"message": "previous"}}})
            reported.assert_called_once()
            self.assertIn("Unable to serialize", reported.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
