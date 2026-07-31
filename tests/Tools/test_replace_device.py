#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Unit tests for Tools/replace_device.py.

Run with:
    python -m pytest tests/Tools/test_replace_device.py -v

The suite covers four areas:
  * DeviceList.txt parsing / writing / lookup helpers
  * the type-based ClusterType remapping logic (build_remap / apply_remap_*)
  * the Domoticz SQLite helpers (load/delete/repoint) against a temp database
  * the "is the database still in use?" guard (inode match + domoticz process),
    including the Docker-style case where the holder sees the file under a
    different path (simulated with a hard link, i.e. a different path / same inode)
"""

import ctypes
import ctypes.util
import os
import sqlite3
import subprocess  # nosec B404 - used to spawn controlled local helper processes
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

from Tools import replace_device as rd


HAS_PROC = Path("/proc").is_dir()


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #
def make_device(ieee, ep_cluster_types, model="TempSensorX"):
    """
    Build a minimal ListOfDevices-style device dict.

    ``ep_cluster_types`` maps an endpoint label to its ClusterType dict, e.g.
    ``{"01": {"100": "Temp", "101": "Hum"}}``.
    """
    ep = {}
    for ep_id, cluster_type in ep_cluster_types.items():
        ep[ep_id] = {"0402": {}, "ClusterType": dict(cluster_type)}
    return {"IEEE": ieee, "Model": model, "Ep": ep}


class DeviceListHelpersTests(unittest.TestCase):
    """load_devicelist_txt / write_devicelist_txt / find_device_by_ieee."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _path(self, name="DeviceList-3.txt"):
        return Path(self.tmp) / name

    def test_load_parses_nwkid_and_dict(self):
        path = self._path()
        path.write_text(
            "aaaa : {'IEEE': '00124b00aaaaaaaa', 'Model': 'X', 'Ep': {'01': {}}}\n"
            "\n"  # blank lines must be ignored
            "bbbb : {'IEEE': '00124b00bbbbbbbb', 'Model': 'Y', 'Ep': {'01': {}}}\n"
        )
        devices = rd.load_devicelist_txt(path)
        self.assertEqual([nwk for nwk, _ in devices], ["aaaa", "bbbb"])
        self.assertEqual(devices[0][1]["IEEE"], "00124b00aaaaaaaa")
        self.assertEqual(devices[1][1]["Model"], "Y")

    def test_write_then_load_roundtrip(self):
        path = self._path()
        devices = [
            ("aaaa", make_device("00124b00aaaaaaaa", {"01": {"100": "Temp"}})),
            ("bbbb", make_device("00124b00bbbbbbbb", {"01": {"200": "Temp"}})),
        ]
        rd.write_devicelist_txt(path, devices)
        reloaded = rd.load_devicelist_txt(path)
        self.assertEqual(reloaded, devices)

    def test_load_preserves_non_ascii_payload(self):
        # Real DeviceList rows carry raw byte strings (e.g. lumi fcc0 blobs).
        path = self._path()
        path.write_text("19a0 : {'IEEE': '00124b00cccccccc', 'raw': '\\x01!|\\n'}\n")
        devices = rd.load_devicelist_txt(path)
        self.assertEqual(devices[0][1]["raw"], "\x01!|\n")

    def test_find_device_by_ieee_is_case_insensitive(self):
        devices = [
            ("aaaa", make_device("00124b00aaaaaaaa", {"01": {"100": "Temp"}})),
            ("bbbb", make_device("00124b00bbbbbbbb", {"01": {"200": "Temp"}})),
        ]
        found = rd.find_device_by_ieee(devices, "00124B00BBBBBBBB")
        self.assertIsNotNone(found)
        self.assertEqual(found[0], "bbbb")

    def test_find_device_by_ieee_missing_returns_none(self):
        devices = [("aaaa", make_device("00124b00aaaaaaaa", {"01": {"100": "Temp"}}))]
        self.assertIsNone(rd.find_device_by_ieee(devices, "ffffffffffffffff"))


class ClusterTypeIntrospectionTests(unittest.TestCase):
    """iter_cluster_types / collect_widget_types, modern and legacy layouts."""

    def test_collect_per_endpoint(self):
        device = make_device("ieee", {"01": {"100": "Temp", "101": "Hum"}, "02": {"110": "Switch"}})
        entries = rd.collect_widget_types(device)
        self.assertEqual(
            sorted(entries),
            sorted([("01", "100", "Temp"), ("01", "101", "Hum"), ("02", "110", "Switch")]),
        )

    def test_collect_legacy_global_cluster_type(self):
        # Some old Xiaomi devices keep a top-level (global) ClusterType, ep "00".
        device = {"IEEE": "ieee", "ClusterType": {"7": "Switch"}, "Ep": {"01": {}}}
        entries = rd.collect_widget_types(device)
        self.assertIn(("00", "7", "Switch"), entries)

    def test_empty_cluster_types_yield_nothing(self):
        device = {"IEEE": "ieee", "Ep": {"01": {"ClusterType": {}}, "02": {}}}
        self.assertEqual(rd.collect_widget_types(device), [])


class BuildRemapTests(unittest.TestCase):
    """The heart of the tool: matching new widget Idx to old ones by type."""

    def test_identical_structure_maps_one_to_one(self):
        old = make_device("old", {"01": {"100": "Temp", "101": "Hum"}})
        new = make_device("new", {"01": {"200": "Temp", "201": "Hum"}})
        remap, matched_old, unmatched_new, unmatched_old, notes = rd.build_remap(old, new)
        self.assertEqual(remap, {"200": "100", "201": "101"})
        self.assertEqual(matched_old, {"100", "101"})
        self.assertEqual(unmatched_new, [])
        self.assertEqual(unmatched_old, [])
        self.assertEqual(notes, [])

    def test_same_endpoint_takes_precedence_for_duplicate_types(self):
        old = make_device("old", {"01": {"100": "Temp"}, "02": {"110": "Temp"}})
        new = make_device("new", {"01": {"200": "Temp"}, "02": {"210": "Temp"}})
        remap, _matched, unmatched_new, unmatched_old, notes = rd.build_remap(old, new)
        self.assertEqual(remap, {"200": "100", "210": "110"})
        self.assertEqual(unmatched_new, [])
        self.assertEqual(unmatched_old, [])
        self.assertEqual(notes, [])  # no cross-endpoint fallback needed

    def test_cross_endpoint_fallback_records_a_note(self):
        old = make_device("old", {"01": {"100": "Temp"}})
        new = make_device("new", {"02": {"200": "Temp"}})
        remap, _matched, unmatched_new, unmatched_old, notes = rd.build_remap(old, new)
        self.assertEqual(remap, {"200": "100"})
        self.assertEqual(unmatched_new, [])
        self.assertEqual(unmatched_old, [])
        self.assertEqual(len(notes), 1)
        self.assertIn("endpoints differ", notes[0])

    def test_unmatched_new_widget_is_reported_and_not_mapped(self):
        old = make_device("old", {"01": {"100": "Temp"}})
        new = make_device("new", {"01": {"200": "Temp", "202": "Lux"}})
        remap, _matched, unmatched_new, unmatched_old, _notes = rd.build_remap(old, new)
        self.assertEqual(remap, {"200": "100"})
        self.assertEqual(unmatched_new, [("01", "202", "Lux")])
        self.assertEqual(unmatched_old, [])

    def test_unmatched_old_widget_is_reported(self):
        old = make_device("old", {"01": {"100": "Temp", "102": "Batt"}})
        new = make_device("new", {"01": {"200": "Temp"}})
        remap, matched_old, _unmatched_new, unmatched_old, _notes = rd.build_remap(old, new)
        self.assertEqual(remap, {"200": "100"})
        self.assertEqual(matched_old, {"100"})
        self.assertEqual(unmatched_old, [("01", "102", "Batt")])


class ApplyRemapTests(unittest.TestCase):
    def test_apply_replaces_matched_idx_and_keeps_unmatched(self):
        new = make_device("new", {"01": {"200": "Temp", "202": "Lux"}})
        rd.apply_remap_to_new_device(new, {"200": "100"})
        # Matched 200 -> 100, unmatched 202 left as is. Types preserved.
        self.assertEqual(new["Ep"]["01"]["ClusterType"], {"100": "Temp", "202": "Lux"})

    def test_apply_handles_legacy_global_cluster_type(self):
        new = {"IEEE": "new", "ClusterType": {"200": "Switch"}, "Ep": {"01": {}}}
        rd.apply_remap_to_new_device(new, {"200": "7"})
        self.assertEqual(new["ClusterType"], {"7": "Switch"})


class DatabaseHelperTests(unittest.TestCase):
    """load_widgets / history_tables / delete_widget / repoint_widget."""

    OLD = "00124b00aaaaaaaa"
    NEW = "00124b00bbbbbbbb"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = Path(self.tmp) / "domoticz.db"
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        c.execute("CREATE TABLE DeviceStatus (ID INTEGER PRIMARY KEY, HardwareID INT, DeviceID TEXT, Unit INT, Name TEXT)")
        c.execute("CREATE TABLE Temperature (ID INTEGER PRIMARY KEY, DeviceRowID INT, Temperature REAL)")
        c.execute("CREATE TABLE Temperature_Calendar (ID INTEGER PRIMARY KEY, DeviceRowID INT, Temp_Avg REAL)")
        c.execute("CREATE TABLE Users (ID INTEGER PRIMARY KEY, Username TEXT)")  # no DeviceRowID
        # old device (history bearing) + new device (fresh) + a foreign hardware widget
        c.execute("INSERT INTO DeviceStatus VALUES (100,3,?,1,'Temp-' || ? || '-01')", (self.OLD, self.OLD))
        c.execute("INSERT INTO DeviceStatus VALUES (101,3,?,2,'Hum-' || ? || '-01')", (self.OLD, self.OLD))
        c.execute("INSERT INTO DeviceStatus VALUES (200,3,?,5,'Temp-' || ? || '-01')", (self.NEW, self.NEW))
        c.execute("INSERT INTO DeviceStatus VALUES (900,7,'00124b00dddddddd',1,'Other-hw')")
        for v in range(5):
            c.execute("INSERT INTO Temperature (DeviceRowID, Temperature) VALUES (100, ?)", (20 + v,))
        c.execute("INSERT INTO Temperature_Calendar (DeviceRowID, Temp_Avg) VALUES (100, 21.0)")
        c.execute("INSERT INTO Temperature (DeviceRowID, Temperature) VALUES (200, 99)")
        conn.commit()
        conn.close()

    def _conn(self):
        return sqlite3.connect(self.db)

    def test_load_widgets_groups_by_ieee_and_filters_hardware(self):
        conn = self._conn()
        try:
            widgets = rd.load_widgets(conn, 3)
        finally:
            conn.close()
        self.assertEqual({i for i, _u, _n in widgets[self.OLD]}, {100, 101})
        self.assertEqual({i for i, _u, _n in widgets[self.NEW]}, {200})
        self.assertNotIn("00124b00dddddddd", widgets)  # different HardwareID

    def test_history_tables_detects_devicerowid_tables_only(self):
        conn = self._conn()
        try:
            tables = rd.history_tables(conn)
        finally:
            conn.close()
        self.assertIn("Temperature", tables)
        self.assertIn("Temperature_Calendar", tables)
        self.assertNotIn("Users", tables)
        self.assertNotIn("DeviceStatus", tables)

    def test_delete_widget_removes_status_and_history(self):
        conn = self._conn()
        try:
            tables = rd.history_tables(conn)
            deleted = rd.delete_widget(conn, 100, tables)
            conn.commit()
            c = conn.cursor()
            self.assertEqual(c.execute("SELECT count(*) FROM DeviceStatus WHERE ID=100").fetchone()[0], 0)
            self.assertEqual(c.execute("SELECT count(*) FROM Temperature WHERE DeviceRowID=100").fetchone()[0], 0)
        finally:
            conn.close()
        self.assertEqual(deleted["Temperature"], 5)
        self.assertEqual(deleted["Temperature_Calendar"], 1)
        self.assertEqual(deleted["DeviceStatus"], 1)

    def test_repoint_widget_changes_deviceid_and_name(self):
        conn = self._conn()
        try:
            new_name = rd.repoint_widget(conn, 100, self.OLD, self.NEW)
            conn.commit()
            c = conn.cursor()
            device_id, name = c.execute("SELECT DeviceID, Name FROM DeviceStatus WHERE ID=100").fetchone()
            # History rows are keyed by Idx (100) and therefore untouched.
            hist = c.execute("SELECT count(*) FROM Temperature WHERE DeviceRowID=100").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(device_id, self.NEW)
        self.assertEqual(name, "Temp-%s-01" % self.NEW)
        self.assertEqual(new_name, "Temp-%s-01" % self.NEW)
        self.assertEqual(hist, 5)


# --------------------------------------------------------------------------- #
# "Is the database still in use?" guard
# --------------------------------------------------------------------------- #
def _spawn(code):
    """Spawn a short-lived python helper running ``code`` and return the Popen."""
    return subprocess.Popen([sys.executable, "-c", textwrap.dedent(code)])  # nosec B603


def _wait_until(predicate, timeout=5.0, interval=0.05):
    """Poll ``predicate`` until it returns truthy or the timeout elapses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return predicate()


@unittest.skipUnless(HAS_PROC, "requires /proc (Linux)")
class DatabaseInUseTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = Path(self.tmp) / "domoticz.db"
        sqlite3.connect(self.db).close()
        self._procs = []

    def tearDown(self):
        for p in self._procs:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()

    def test_clean_when_nobody_uses_it(self):
        usage = rd.check_database_in_use(self.db)
        self.assertTrue(usage["available"])
        self.assertEqual(usage["holders"], {})
        # Our own test process is never reported, even though it created the file.
        self.assertNotIn(os.getpid(), usage["holders"])

    def test_open_handle_detected_by_inode_via_different_path(self):
        # Simulate the Docker case: the holder sees the file under another path.
        # A hard link is a different path that shares the same inode.
        linked = Path(self.tmp) / "container_view.db"
        os.link(self.db, linked)
        proc = _spawn(
            """
            f = open(%r, 'rb')
            import time; time.sleep(30)
            """ % str(linked)
        )
        self._procs.append(proc)

        usage = _wait_until(lambda: rd.check_database_in_use(self.db)["holders"])
        self.assertIn(proc.pid, usage)  # detected by inode, not by path

    def test_domoticz_named_process_detected_even_without_db_handle(self):
        # The process does not open the db at all; it is flagged purely by its
        # /proc/<pid>/comm name (set via prctl), mirroring a Dockerised Domoticz
        # whose file descriptors we may not be allowed to read.
        proc = _spawn(
            """
            import ctypes, ctypes.util, time
            libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
            libc.prctl(15, b'domoticz', 0, 0, 0)   # PR_SET_NAME
            time.sleep(30)
            """
        )
        self._procs.append(proc)

        usage = _wait_until(lambda: rd.check_database_in_use(self.db)["domoticz"])
        self.assertIn(proc.pid, usage)
        self.assertEqual(usage[proc.pid], "domoticz")

    def test_no_proc_reports_unavailable(self):
        fake = mock.Mock()
        fake.is_dir.return_value = False
        with mock.patch.object(rd, "Path", return_value=fake):
            usage = rd.check_database_in_use(self.db)
        self.assertFalse(usage["available"])


if __name__ == "__main__":
    unittest.main()
