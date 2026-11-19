#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Modules/database.py — drop_entries_without_ieee()

A device list entry with Status "inDB" and no IEEE made checkDevices2LOD()
raise KeyError: 'IEEE' in onStart, before the radio was started: the plugin
then only logged "Hard time getting Coordinator Version". Such entries are now
dropped at load, with an Error naming the entry.

Like test_database_json_export_local_devices.py, the checks run in a
subprocess against the real (unstubbed) plugin modules.
"""

from tests.Modules.test_database_json_export_local_devices import _run


def test_entries_without_ieee_are_dropped_with_an_error():
    _run(
        """
        devices = {
            "0000": {"IEEE": "00124b0000000000", "Status": "", "Version": "3"},
            "1234": {"IEEE": "00158d0000000001", "Status": "inDB", "Model": "lumi.sensor"},
            "abcd": {"Status": "inDB", "Model": "TS0601"},
            "beef": {"IEEE": "", "Status": "inDB"},
        }
        calls = []
        p = make_plugin(".", devices)
        p.log.logging = lambda module, level, message, nwkid=None, context=None: calls.append((level, nwkid, context))

        database.drop_entries_without_ieee(p, "Domoticz")

        assert sorted(devices) == ["0000", "1234"], devices
        errors = [c for c in calls if c[0] == "Error"]
        assert [c[1] for c in errors] == ["abcd", "beef"], calls
        assert errors[0][2]["Error code"] == "DATABASE-NOIEEE-01", errors
        assert errors[0][2]["Source"] == "Domoticz", errors
        assert errors[0][2]["Status"] == "inDB" and errors[0][2]["Model"] == "TS0601", errors
        """
    )


def test_check_devices_to_lod_runs_after_the_drop():
    _run(
        """
        devices = {
            "1234": {"IEEE": "00158d0000000001", "Status": "inDB"},
            "abcd": {"Status": "inDB"},
        }
        p = make_plugin(".", devices)
        widget = types.SimpleNamespace(DeviceID="00158d0000000001")

        database.drop_entries_without_ieee(p, "DeviceList-1.txt")
        database.checkDevices2LOD(p, {"00158d0000000001": widget})

        assert devices == {"1234": {"IEEE": "00158d0000000001", "Status": "inDB", "ConsistencyCheck": "ok"}}, devices
        """
    )


def test_nothing_logged_when_every_entry_has_an_ieee():
    _run(
        """
        devices = {"1234": {"IEEE": "00158d0000000001", "Status": "inDB"}}
        p = make_plugin(".", devices)
        database.drop_entries_without_ieee(p, "Domoticz")
        assert list(devices) == ["1234"] and p.log.records == [], (devices, p.log.records)
        """
    )
