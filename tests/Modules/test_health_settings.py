#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Modules/health_settings.py

Coverage:
  - device_health_timeout  - device parameter precedence over the plugin setting,
                             fallback on absent / zero / malformed values
  - is_health_timed_out    - which Health states are candidates, the never-seen
                             device, the threshold boundary, the disabled check
  - HEALTH_DEVICE_PARAMETERS - shape expected by rest_Device_Settings_Help and
                             sanity_check_of_param

The module under test is imported directly: it has no plugin dependency, so no
stubbing is needed and nothing leaks into sys.modules for the other test files.
"""

import pytest

from Modules.health_settings import (HEALTH_DEVICE_PARAMETERS,
                                     HEALTH_STALE_CANDIDATES,
                                     HEALTH_UNDETERMINED,
                                     device_health_timeout,
                                     is_health_timed_out)

PLUGIN_DEFAULT = 21200


def _device(health="Live", last_seen=1000, param=None):
    device = {"Health": health, "Stamp": {"LastSeen": last_seen, "LastPing": 0}}
    if param is not None:
        device["Param"] = param
    return device


# ── device_health_timeout ─────────────────────────────────────────────────────

class TestDeviceHealthTimeout:
    def test_no_param_falls_back_on_plugin_setting(self):
        assert device_health_timeout(_device(), PLUGIN_DEFAULT) == PLUGIN_DEFAULT

    def test_empty_param_falls_back_on_plugin_setting(self):
        assert device_health_timeout(_device(param={}), PLUGIN_DEFAULT) == PLUGIN_DEFAULT

    def test_zero_param_is_off_and_falls_back(self):
        """0 means "no device override", not "no check" - the documented behaviour."""
        assert device_health_timeout(_device(param={"HealthTimeOut": 0}), PLUGIN_DEFAULT) == PLUGIN_DEFAULT

    def test_device_param_supersedes_plugin_setting(self):
        assert device_health_timeout(_device(param={"HealthTimeOut": 600}), PLUGIN_DEFAULT) == 600

    def test_device_param_as_string_is_accepted(self):
        """Values coming back from the REST endpoint or a JSON config may be strings."""
        assert device_health_timeout(_device(param={"HealthTimeOut": "600"}), PLUGIN_DEFAULT) == 600

    @pytest.mark.parametrize("bad", ["", "abc", None, -1, [], {}])
    def test_malformed_device_param_falls_back(self, bad):
        assert device_health_timeout(_device(param={"HealthTimeOut": bad}), PLUGIN_DEFAULT) == PLUGIN_DEFAULT

    def test_plugin_setting_of_zero_disables_the_check(self):
        assert device_health_timeout(_device(), 0) == 0

    def test_device_param_still_wins_when_plugin_setting_is_zero(self):
        assert device_health_timeout(_device(param={"HealthTimeOut": 600}), 0) == 600

    @pytest.mark.parametrize("bad", [None, "", "abc", -5])
    def test_malformed_plugin_setting_is_treated_as_off(self, bad):
        assert device_health_timeout(_device(), bad) == 0


# ── is_health_timed_out ──────────────────────────────────────────────────────

class TestIsHealthTimedOut:
    def test_live_device_silent_for_longer_than_timeout(self):
        assert is_health_timed_out(_device(last_seen=1000), 100, now=1101) is True

    def test_live_device_seen_recently(self):
        assert is_health_timed_out(_device(last_seen=1000), 100, now=1050) is False

    def test_boundary_is_not_timed_out(self):
        """Exactly at LastSeen + timeout is still considered seen."""
        assert is_health_timed_out(_device(last_seen=1000), 100, now=1100) is False

    @pytest.mark.parametrize("health", HEALTH_UNDETERMINED)
    def test_undetermined_health_is_a_candidate(self, health):
        """A plugin start resets Health, but the persisted LastSeen is still usable."""
        assert is_health_timed_out(_device(health=health, last_seen=1000), 100, now=1101) is True

    @pytest.mark.parametrize("health", ["Not Reachable", "Disabled", "TimedOut", "Not seen last 24hours"])
    def test_other_health_states_are_left_alone(self, health):
        assert is_health_timed_out(_device(health=health, last_seen=1000), 100, now=99999) is False

    def test_already_flagged_device_does_not_re_trigger(self):
        """Guarantees the caller logs once, not on every heartbeat."""
        device = _device(last_seen=1000)
        assert is_health_timed_out(device, 100, now=1101) is True
        device["Health"] = "Not seen last 24hours"
        assert is_health_timed_out(device, 100, now=1102) is False

    def test_timeout_of_zero_disables_the_check(self):
        assert is_health_timed_out(_device(last_seen=1000), 0, now=99999) is False

    @pytest.mark.parametrize("last_seen", [0, None, "", "abc"])
    def test_never_seen_device_is_not_flagged(self, last_seen):
        """No reference point to measure silence from - left to the ping logic."""
        assert is_health_timed_out(_device(last_seen=last_seen), 100, now=99999) is False

    def test_missing_stamp_is_not_flagged(self):
        assert is_health_timed_out({"Health": "Live"}, 100, now=99999) is False

    def test_missing_health_is_not_flagged(self):
        """An entry without Health at all is not a device checkHealth has prepared."""
        assert is_health_timed_out({"Stamp": {"LastSeen": 1000}}, 100, now=99999) is False


# ── declaration consumed by the WebServer and sanity_check_of_param ──────────

class TestHealthDeviceParameters:
    def test_health_timeout_is_declared(self):
        assert "HealthTimeOut" in HEALTH_DEVICE_PARAMETERS

    def test_declaration_carries_a_description(self):
        """rest_device_settings_help reads setting_info["description"] for non-callables."""
        assert HEALTH_DEVICE_PARAMETERS["HealthTimeOut"]["description"]

    def test_declaration_has_no_callable(self):
        """A plugin side parameter writes nothing to the device, so sanity_check_of_param
        must find no callable to apply."""
        setting = HEALTH_DEVICE_PARAMETERS["HealthTimeOut"]
        assert not callable(setting)
        assert "callable" not in setting

    def test_live_is_a_stale_candidate(self):
        assert "Live" in HEALTH_STALE_CANDIDATES


# ── vocabulary guard ─────────────────────────────────────────────────────────

class TestHealthUndetermined:
    """HEALTH_UNDETERMINED is the contract between the places that write "I have no
    evidence about this device" and the places that read it.

    checkHealth() derives _checkHealth from it, and that flag is what makes
    pingDevices() probe a device at once instead of waiting out pingDevicesFeq.
    Dropping a spelling here silently stops the post-restart ping sweep, with no
    test failure anywhere else - hence this guard.
    """

    def test_unknown_is_undetermined(self):
        """Written by database.CheckDeviceList, command.mgtCommand, heartbeat,
        WebServer and GrpDomoticz when a device has to be probed again."""
        assert "unknown" in HEALTH_UNDETERMINED

    def test_empty_string_is_still_undetermined(self):
        """Kept so a device entry built before the "unknown" rename, or by a path
        not covered here, is still probed rather than silently ignored."""
        assert "" in HEALTH_UNDETERMINED
