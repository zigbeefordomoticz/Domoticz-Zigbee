#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Regression tests for the widget index race (ListOfDomoticzWidget).

Field report on 9.1.010: GET zgroup-list-available-device raised KeyError: 1374 in
retrieve_widgetid_from_deviceId_unit. The WebUI threads read ListOfDomoticzWidget while
the Domoticz thread rebuilds it (load_list_of_domoticz_widget, after every widget
creation and removal). The readers iterated the keys, a snapshot, then indexed each key
in a separate call: a key gone in between raised KeyError. The rebuild also emptied the
index before refilling it, so a reader could find nothing at all.

The fix:
- readers take one items() snapshot of (idx, widget) pairs
  (retrieve_widgetid_from_deviceId_unit, WebServer.rest_Device);
- the rebuild builds the new index aside and swaps it in under the index lock;
- _build_device_widgetList_infos looks the widget up by its idx instead of scanning
  every widget, each with its own scan of the index.

The code under test imports the real Modules.* package, which conflicts with the stubs
tests/conftest.py installs for the session, so the scenarios run in a subprocess.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

SNIPPET = textwrap.dedent(
    """
    import json, sys, threading, types
    from unittest.mock import MagicMock
    for name in ("Domoticz", "DomoticzEx"):
        mod = types.ModuleType(name)
        mod.Log = mod.Debug = mod.Error = mod.Status = MagicMock()
        sys.modules[name] = mod

    from Classes.ThreadSafeDeviceDict import ThreadSafeDeviceDict
    from Classes.WebServer.rest_Groups import _build_device_widgetList_infos
    from Classes.WebServer.WebServer import WebServer
    from Modules.domoticzAbstractLayer import (load_list_of_domoticz_widget,
                                               retrieve_widgetid_from_deviceId_unit)

    GHOST = 9999

    class Unit:
        def __init__(self, idx, name):
            self.ID, self.Name = idx, name
            self.SwitchType = self.SubType = 0
            self.nValue, self.sValue = 1, "On"
            self.SignalLevel, self.BatteryLevel = 12, 255

    class Device:
        def __init__(self, units):
            self.Units, self.TimedOut = units, 0

    def make_devices(count, first_idx=1000):
        return {
            "%016x" % n: Device({1: Unit(first_idx + n, "Widget %d" % n)})
            for n in range(count)
        }

    class StaleKeysIndex(ThreadSafeDeviceDict):
        # Iteration hands out a key removed since: what a reader saw when the
        # Domoticz thread rebuilt the index between the key snapshot and the lookup.
        def __iter__(self):
            return iter([GHOST] + list(super().__iter__()))

    def plugin(devices, index):
        return types.SimpleNamespace(
            Devices=devices,
            ListOfDomoticzWidget=index,
            log=types.SimpleNamespace(logging=MagicMock()),
            logging=MagicMock(),
            pluginconf=types.SimpleNamespace(pluginConf={}),
        )

    def outcome(func):
        try:
            return {"ok": func()}
        except Exception as e:
            return {"raised": type(e).__name__}

    results = {}

    # --- retrieve_widgetid_from_deviceId_unit with a key gone from the index ---
    devices = make_devices(3)
    stale = StaleKeysIndex()
    load_list_of_domoticz_widget(plugin(devices, stale), devices)
    results["retrieve_with_stale_key"] = outcome(
        lambda: retrieve_widgetid_from_deviceId_unit(plugin(devices, stale), devices, "%016x" % 2, 1))

    # --- the rebuild keeps the same object: WebServer and GroupManagement hold it ---
    index = ThreadSafeDeviceDict({GHOST: {"DeviceID": "gone", "Unit": 1}})
    before = id(index)
    load_list_of_domoticz_widget(plugin(devices, index), devices)
    results["rebuild_same_object"] = id(index) == before
    results["rebuild_keys"] = sorted(index.keys())
    load_list_of_domoticz_widget(plugin(None, index), None)
    results["rebuild_devices_none_empties"] = len(index)

    # --- a reader running against the rebuild loop always finds the widget ---
    devices = make_devices(300)
    index = ThreadSafeDeviceDict()
    load_list_of_domoticz_widget(plugin(devices, index), devices)
    stop = threading.Event()

    def rebuild_loop():
        while not stop.is_set():
            load_list_of_domoticz_widget(plugin(devices, index), devices)

    writer = threading.Thread(target=rebuild_loop)
    writer.start()
    misses = errors = 0
    try:
        for _ in range(300):
            try:
                if retrieve_widgetid_from_deviceId_unit(plugin({}, index), {}, "%016x" % 299, 1) != 1299:
                    misses += 1
            except KeyError:
                errors += 1
    finally:
        stop.set()
        writer.join()
    results["concurrent"] = {"misses": misses, "errors": errors}

    # --- _build_device_widgetList_infos: direct lookup by idx ---
    devices = make_devices(3)
    index = ThreadSafeDeviceDict()
    load_list_of_domoticz_widget(plugin(devices, index), devices)
    results["build_found"] = outcome(lambda: _build_device_widgetList_infos(plugin(devices, index), "1001", "0b", "Lamp"))
    results["build_unknown_idx"] = outcome(lambda: _build_device_widgetList_infos(plugin(devices, index), "4242", "01", "Lamp"))
    results["build_not_a_number"] = outcome(lambda: _build_device_widgetList_infos(plugin(devices, index), "abc", "01", "Lamp"))
    gone = dict(devices)
    gone.pop("%016x" % 1)
    results["build_gone_from_devices"] = outcome(lambda: _build_device_widgetList_infos(plugin(gone, index), "1001", "01", "Lamp"))

    # --- WebServer.rest_Device with a key gone from the index ---
    devices = make_devices(3)
    stale = StaleKeysIndex()
    load_list_of_domoticz_widget(plugin(devices, stale), devices)
    web = plugin(devices, stale)

    def rest_device(parameters):
        response = WebServer.rest_Device(web, "GET", None, parameters)
        return json.loads(response["Data"])

    results["rest_device_all"] = outcome(lambda: sorted(w["ID"] for w in rest_device([])))
    results["rest_device_one"] = outcome(lambda: rest_device(["%016x" % 1])["ID"])
    results["rest_device_many"] = outcome(lambda: sorted(w["ID"] for w in rest_device(["%016x" % 0, "%016x" % 2])))

    print(json.dumps(results))
    """
)


@pytest.fixture(scope="module")
def results():
    completed = subprocess.run(  # nosec B603
        [sys.executable, "-c", SNIPPET],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


class TestRetrieveWidgetId:

    def test_key_gone_from_the_index_does_not_raise(self, results):
        """The reported KeyError: the lookup must not index a key it saw earlier."""
        assert results["retrieve_with_stale_key"] == {"ok": 1002}

    def test_reader_never_misses_during_rebuilds(self, results):
        """The rebuild is swapped in under the lock: no KeyError, no empty index seen."""
        assert results["concurrent"] == {"misses": 0, "errors": 0}


class TestLoadListOfDomoticzWidget:

    def test_rebuild_keeps_the_same_object(self, results):
        assert results["rebuild_same_object"] is True

    def test_rebuild_replaces_the_content(self, results):
        assert results["rebuild_keys"] == [1000, 1001, 1002]

    def test_devices_none_empties_the_index(self, results):
        assert results["rebuild_devices_none_empties"] == 0


class TestBuildDeviceWidgetListInfos:

    def test_found(self, results):
        assert results["build_found"] == {"ok": [{
            "_ID": 1001,
            "Name": "Widget 1",
            "IEEE": "%016x" % 1,
            "Ep": "0b",
            "ZDeviceName": "Lamp",
        }]}

    def test_unknown_idx(self, results):
        assert results["build_unknown_idx"] == {"ok": []}

    def test_widget_id_not_a_number(self, results):
        assert results["build_not_a_number"] == {"ok": []}

    def test_widget_gone_from_domoticz(self, results):
        assert results["build_gone_from_devices"] == {"ok": []}


class TestRestDevice:

    def test_all_widgets(self, results):
        assert results["rest_device_all"] == {"ok": [1000, 1001, 1002]}

    def test_one_device(self, results):
        assert results["rest_device_one"] == {"ok": 1001}

    def test_several_devices(self, results):
        assert results["rest_device_many"] == {"ok": [1000, 1002]}
