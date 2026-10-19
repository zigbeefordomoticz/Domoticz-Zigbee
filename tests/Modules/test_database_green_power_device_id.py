#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Modules/database.py — fixing_green_power_device_id() (#2119)

The last Simple Descriptor decoded used to set the device level ProfileID and
ZDeviceID, so devices with a Green Power proxy endpoint (f2) were recorded as
a1e0 / 0061. At load, the values are copied back from the best application
endpoint in Epv2.

Like test_database_json_export_local_devices.py, the checks run in a
subprocess against the real (unstubbed) plugin modules.
"""

from tests.Modules.test_database_json_export_local_devices import _run


def test_green_power_ids_restored_from_application_endpoint():
    _run(
        """
        devices = {"1234": {
            "ProfileID": "a1e0", "ZDeviceID": "0061",
            "Epv2": {"0b": {"ProfileID": "0104", "ZDeviceID": "0210"}, "f2": {"ProfileID": "a1e0", "ZDeviceID": "0061"}},
        }}
        p = make_plugin(".", devices)
        database.fixing_green_power_device_id(p, "1234")
        assert (devices["1234"]["ProfileID"], devices["1234"]["ZDeviceID"]) == ("0104", "0210"), devices
        assert devices["1234"]["Epv2"]["f2"] == {"ProfileID": "a1e0", "ZDeviceID": "0061"}
        """
    )


def test_application_profile_preferred_over_vendor_then_lowest_endpoint():
    _run(
        """
        devices = {"1234": {
            "ProfileID": "A1E0", "ZDeviceID": "0061",
            "Epv2": {
                "01": {"ProfileID": "c0c9", "ZDeviceID": "0001"},
                "03": {"ProfileID": "0104", "ZDeviceID": "0302"},
                "02": {"ProfileID": "0104", "ZDeviceID": "0051"},
                "f2": {"ProfileID": "a1e0", "ZDeviceID": "0061"},
            },
        }}
        p = make_plugin(".", devices)
        database.fixing_green_power_device_id(p, "1234")
        assert (devices["1234"]["ProfileID"], devices["1234"]["ZDeviceID"]) == ("0104", "0051"), devices
        """
    )


def test_vendor_profile_used_when_no_application_profile():
    _run(
        """
        devices = {"1234": {
            "ProfileID": "a1e0", "ZDeviceID": "0061",
            "Epv2": {"01": {"ProfileID": "c0c9", "ZDeviceID": "0001"}, "f2": {"ProfileID": "a1e0", "ZDeviceID": "0061"}},
        }}
        p = make_plugin(".", devices)
        database.fixing_green_power_device_id(p, "1234")
        assert (devices["1234"]["ProfileID"], devices["1234"]["ZDeviceID"]) == ("c0c9", "0001"), devices
        """
    )


def test_untouched_when_not_green_power_or_nothing_better():
    _run(
        """
        devices = {
            "aaaa": {"ProfileID": "c0c9", "ZDeviceID": "0001", "Epv2": {"02": {"ProfileID": "0104", "ZDeviceID": "0051"}}},
            "bbbb": {"ProfileID": "a1e0", "ZDeviceID": "0061", "Epv2": {"f2": {"ProfileID": "a1e0", "ZDeviceID": "0061"}}},
            "cccc": {"ProfileID": "a1e0", "ZDeviceID": "0061"},
            "dddd": {"ProfileID": "a1e0", "ZDeviceID": "0061", "Epv2": {"01": {"ClusterIn": {}}, "zz": {"ProfileID": "0104", "ZDeviceID": "0100"}}},
            "eeee": {"ProfileID": {}, "ZDeviceID": {}, "Epv2": {"01": {"ProfileID": "0104", "ZDeviceID": "0100"}}},
        }
        before = json.dumps(devices, sort_keys=True)
        p = make_plugin(".", devices)
        for nwkid in devices:
            database.fixing_green_power_device_id(p, nwkid)
        assert json.dumps(devices, sort_keys=True) == before, devices
        assert p.log.records == [], p.log.records
        """
    )
