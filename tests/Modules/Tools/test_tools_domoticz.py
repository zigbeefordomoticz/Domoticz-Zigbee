#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Modules/tools_domoticz.py

Coverage:
  - is_domoticz_db_available    – old fashion, major < 2021, 2021 minor < 1, 2021.1+ OK
  - is_domoticz_below_20xx      – boundary tests for 2020, 2021, 2022, 2023, 2024
  - is_domoticz_above_2022      – boundary
  - is_domoticz_above_2022_2    – exact 2022.2, 2022.1, above 2022
  - is_domoticz_2023 / 2024     – exact match
  - is_domoticz_above_2023/2024 – boundary
  - is_domoticz_new_API         – below 2023 False, 2023.1 build < 15326 False,
                                   2023.1 build >= 15326 True, 2023.2 True, 2024+ True
  - is_domoticz_latest_typename – below 2024 False, 2024 minor<=4 build<15956 False,
                                   2024 build>=15956 True
  - is_domoticz_new_blind       – delegates to above_2022_2
  - is_domoticz_update_SuppressTriggers – above 2022 True, below 2021 False, special 2021.1
  - is_domoticz_touch           – VersionNewFashion True, major>=2022, legacy major==4
  - get_device_config_param     – found, missing device, missing Param, missing key
"""

import pytest
from unittest.mock import MagicMock

from Modules.tools_domoticz import (
    get_device_config_param,
    is_domoticz_2023,
    is_domoticz_2024,
    is_domoticz_above_2022,
    is_domoticz_above_2022_2,
    is_domoticz_above_2023,
    is_domoticz_above_2024,
    is_domoticz_below_2020,
    is_domoticz_below_2021,
    is_domoticz_below_2022,
    is_domoticz_below_2023,
    is_domoticz_below_2024,
    is_domoticz_db_available,
    is_domoticz_latest_typename,
    is_domoticz_new_API,
    is_domoticz_new_blind,
    is_domoticz_touch,
    is_domoticz_update_SuppressTriggers,
)


def _p(major, minor=0, build=0, new_fashion=True):
    p = MagicMock()
    p.DomoticzMajor = major
    p.DomoticzMinor = minor
    p.DomoticzBuild = build
    p.VersionNewFashion = new_fashion
    p.ListOfDevices = {}
    return p


# ---------------------------------------------------------------------------
# is_domoticz_db_available
# ---------------------------------------------------------------------------

class TestIsDomoticzDbAvailable:
    def test_old_fashion_false(self):
        assert is_domoticz_db_available(_p(2022, new_fashion=False)) is False

    def test_below_2021_false(self):
        assert is_domoticz_db_available(_p(2020)) is False

    def test_2021_minor_0_false(self):
        assert is_domoticz_db_available(_p(2021, minor=0)) is False

    def test_2021_minor_1_true(self):
        assert is_domoticz_db_available(_p(2021, minor=1)) is True

    def test_2022_true(self):
        assert is_domoticz_db_available(_p(2022)) is True


# ---------------------------------------------------------------------------
# below / above year helpers
# ---------------------------------------------------------------------------

class TestYearBoundaries:
    @pytest.mark.parametrize("major,expected", [(2019, True), (2020, False)])
    def test_below_2020(self, major, expected):
        assert is_domoticz_below_2020(_p(major)) is expected

    @pytest.mark.parametrize("major,expected", [(2020, True), (2021, False)])
    def test_below_2021(self, major, expected):
        assert is_domoticz_below_2021(_p(major)) is expected

    @pytest.mark.parametrize("major,expected", [(2021, True), (2022, False)])
    def test_below_2022(self, major, expected):
        assert is_domoticz_below_2022(_p(major)) is expected

    @pytest.mark.parametrize("major,expected", [(2022, True), (2023, False)])
    def test_below_2023(self, major, expected):
        assert is_domoticz_below_2023(_p(major)) is expected

    @pytest.mark.parametrize("major,expected", [(2023, True), (2024, False)])
    def test_below_2024(self, major, expected):
        assert is_domoticz_below_2024(_p(major)) is expected

    @pytest.mark.parametrize("major,expected", [(2022, False), (2023, True)])
    def test_above_2022(self, major, expected):
        assert is_domoticz_above_2022(_p(major)) is expected

    @pytest.mark.parametrize("major,expected", [(2023, False), (2024, True)])
    def test_above_2023(self, major, expected):
        assert is_domoticz_above_2023(_p(major)) is expected

    @pytest.mark.parametrize("major,expected", [(2024, False), (2025, True)])
    def test_above_2024(self, major, expected):
        assert is_domoticz_above_2024(_p(major)) is expected


# ---------------------------------------------------------------------------
# is_domoticz_above_2022_2
# ---------------------------------------------------------------------------

class TestAbove20222:
    def test_2022_minor_1_false(self):
        assert is_domoticz_above_2022_2(_p(2022, minor=1)) is False

    def test_2022_minor_2_true(self):
        assert is_domoticz_above_2022_2(_p(2022, minor=2)) is True

    def test_2023_true(self):
        assert is_domoticz_above_2022_2(_p(2023)) is True

    def test_2021_false(self):
        assert is_domoticz_above_2022_2(_p(2021)) is False


# ---------------------------------------------------------------------------
# is_domoticz_2023 / 2024
# ---------------------------------------------------------------------------

class TestExactYear:
    def test_2023_match(self):
        assert is_domoticz_2023(_p(2023)) is True
        assert is_domoticz_2023(_p(2022)) is False

    def test_2024_match(self):
        assert is_domoticz_2024(_p(2024)) is True
        assert is_domoticz_2024(_p(2023)) is False


# ---------------------------------------------------------------------------
# is_domoticz_new_API
# ---------------------------------------------------------------------------

class TestNewAPI:
    def test_below_2023_false(self):
        assert is_domoticz_new_API(_p(2022)) is False

    def test_2023_minor_1_build_below_threshold(self):
        assert is_domoticz_new_API(_p(2023, minor=1, build=15325)) is False

    def test_2023_minor_1_build_at_threshold(self):
        assert is_domoticz_new_API(_p(2023, minor=1, build=15326)) is True

    def test_2023_minor_2_true(self):
        assert is_domoticz_new_API(_p(2023, minor=2)) is True

    def test_2024_true(self):
        assert is_domoticz_new_API(_p(2024)) is True


# ---------------------------------------------------------------------------
# is_domoticz_latest_typename
# ---------------------------------------------------------------------------

class TestLatestTypename:
    def test_below_2024_false(self):
        assert is_domoticz_latest_typename(_p(2023)) is False

    def test_2024_minor_4_build_below_threshold(self):
        assert is_domoticz_latest_typename(_p(2024, minor=4, build=15955)) is False

    def test_2024_minor_5_true(self):
        assert is_domoticz_latest_typename(_p(2024, minor=5)) is True

    def test_2024_build_at_threshold_true(self):
        assert is_domoticz_latest_typename(_p(2024, minor=0, build=15956)) is True


# ---------------------------------------------------------------------------
# is_domoticz_new_blind / is_domoticz_update_SuppressTriggers / is_domoticz_touch
# ---------------------------------------------------------------------------

class TestMiscVersionChecks:
    def test_new_blind_delegates_to_above_2022_2(self):
        assert is_domoticz_new_blind(_p(2022, minor=2)) is True
        assert is_domoticz_new_blind(_p(2022, minor=1)) is False

    def test_suppress_triggers_above_2022_true(self):
        assert is_domoticz_update_SuppressTriggers(_p(2023)) is True

    def test_suppress_triggers_below_2021_false(self):
        assert is_domoticz_update_SuppressTriggers(_p(2020)) is False

    def test_suppress_triggers_2021_1_build_below_13374_false(self):
        assert is_domoticz_update_SuppressTriggers(_p(2021, minor=1, build=13373)) is False

    def test_suppress_triggers_2021_1_build_at_13374_true(self):
        assert is_domoticz_update_SuppressTriggers(_p(2021, minor=1, build=13374)) is True

    def test_touch_new_fashion(self):
        assert is_domoticz_touch(_p(2019, new_fashion=True)) is True

    def test_touch_major_2022(self):
        assert is_domoticz_touch(_p(2022, new_fashion=False)) is True

    def test_touch_legacy_major4(self):
        p = _p(4, minor=10547, new_fashion=False)
        assert is_domoticz_touch(p) is True

    def test_touch_legacy_major4_below_minor(self):
        p = _p(4, minor=10546, new_fashion=False)
        assert is_domoticz_touch(p) is False


# ---------------------------------------------------------------------------
# get_device_config_param
# ---------------------------------------------------------------------------

class TestGetDeviceConfigParam:
    def test_returns_value(self):
        p = _p(2024)
        p.ListOfDevices = {"1234": {"Param": {"mykey": "myval"}}}
        assert get_device_config_param(p, "1234", "mykey") == "myval"

    def test_missing_device_returns_none(self):
        p = _p(2024)
        p.ListOfDevices = {}
        assert get_device_config_param(p, "dead", "key") is None

    def test_missing_param_section_returns_none(self):
        p = _p(2024)
        p.ListOfDevices = {"1234": {}}
        assert get_device_config_param(p, "1234", "key") is None

    def test_missing_key_returns_none(self):
        p = _p(2024)
        p.ListOfDevices = {"1234": {"Param": {}}}
        assert get_device_config_param(p, "1234", "nokey") is None
