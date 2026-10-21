#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Which devices the plugin hands to zigpy's device table at startup.

A device the plugin has recorded as gone from the network is pre-loaded into
zigpy today, which then asks it for its neighbour and routing tables in every
topology scan and pays the full retry cost for an answer that cannot come.
Found on a real mesh: 0xE079 had left, the plugin had it as "Leave", and it was
still being interrogated scan after scan.
"""

import collections.abc

import pytest

from Modules.zigpy_preload import (DEPARTED_STATUSES,
                                   device_has_left_the_network)


class DeviceRecord(collections.abc.MutableMapping):
    """A ListOfDevices entry as the plugin really holds it.

    ListOfDevices is a ThreadSafeDeviceDict, so its entries are Mappings and not
    dicts. A predicate written against dict would still pass a test using plain
    dicts and fail in the field, so the record type is reproduced here.
    """

    def __init__(self, data):
        self._data = dict(data)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)


@pytest.mark.parametrize("status", DEPARTED_STATUSES)
def test_a_departed_device_is_recognised(status):
    assert device_has_left_the_network({"Status": status}) is True


def test_a_device_that_announced_its_departure_has_left():
    # 0xE079 on the mesh this was found on: it left, and the plugin recorded it
    device = {"Status": "Leave", "IEEE": "540f57fffe2b231a", "Model": "TS0601"}

    assert device_has_left_the_network(device) is True


def test_a_device_removed_down_to_its_last_widget_has_left():
    # Modules/tools_device_lifecycle.py sets this once no widget is left
    assert device_has_left_the_network({"Status": "Removed"}) is True


@pytest.mark.parametrize("status", ["inDB", "notDB", "UNKNOW", "provREQ", "erasePDM", "004d", "0045", "8011", "CreateDB", ""])
def test_every_other_state_stays_in_the_pre_load(status):
    # An unfinished pairing is not evidence that the device is gone, and a
    # device missing from zigpy's table is one the plugin cannot talk to.
    assert device_has_left_the_network({"Status": status}) is False


def test_a_record_with_no_status_stays_in_the_pre_load():
    assert device_has_left_the_network({"IEEE": "00158d0002c63af3"}) is False


def test_a_record_that_is_not_a_mapping_stays_in_the_pre_load():
    # The pre-load is not the place to decide a malformed record means departed
    assert device_has_left_the_network(None) is False
    assert device_has_left_the_network("Leave") is False


def test_the_real_record_type_reads_the_same_as_a_dict():
    # ListOfDevices entries are ThreadSafeDeviceDict values, not dicts
    assert device_has_left_the_network(DeviceRecord({"Status": "Leave"})) is True
    assert device_has_left_the_network(DeviceRecord({"Status": "inDB"})) is False


def test_health_is_not_what_decides():
    # A Lumi LED that never answers Mgmt_Lqi_req is still on the network, and
    # the plugin hears it: it must stay in zigpy's table. Only the lifecycle
    # Status says a device is gone.
    lumi_led = {"Status": "inDB", "Health": "Not seen last 24hours"}

    assert device_has_left_the_network(lumi_led) is False
