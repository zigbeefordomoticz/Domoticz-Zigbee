#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_logging_plugin_identity.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the plugin identity recorded in the error history
(Classes/LoggingManagement.py: loggingUpdatePluginVersion / loggingError).

plugin.py hands loggingUpdatePluginVersion what plugin_identity() builds - the version,
the revision of the checkout and the certified database version - and every error session
stored from then on is stamped with it. That is what the WebUI error page shows, and what
tells which code produced a recorded error.

The identity is a free text string here: nothing parses it back, it is dumped to the
WebUI as it stands. What these tests hold is that it reaches the stored entries, and that
it is never written over a session recorded by an earlier run of the plugin.

Run with:
    pytest tests/Classes/test_logging_plugin_identity.py -v
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

# tests/conftest.py installs the DomoticzEx fake at import time, before collection
import Classes.LoggingManagement as lm  # noqa: E402

IDENTITY = "stable9-9.1.007 (commit 1801805 on integration/release-9.1.008, Certified DB 10.607)"
START_TIME = 1791140376


def _make_log(history=None, start_time=START_TIME):
    """Return a LoggingManagement-like object carrying only what the SUT reads."""
    return SimpleNamespace(
        LogErrorHistory=history if history is not None else {},
        _startTime=start_time,
        PluginVersion=None,
        FirmwareVersion="8.0.2.0 build 397",
        FirmwareMajorVersion="30",
        _newError=False,
        ListOfDevices={},
        PluginHealth={"Txt": "Ready"},
        permitTojoin={"Duration": 0, "Starttime": START_TIME},
        pluginconf=SimpleNamespace(pluginConf={"enablePluginLogging": False}),
    )


class TestLoggingUpdatePluginVersion(unittest.TestCase):

    def test_identity_is_held_for_the_sessions_to_come(self):
        log = _make_log()
        lm.LoggingManagement.loggingUpdatePluginVersion(log, IDENTITY)
        self.assertEqual(log.PluginVersion, IDENTITY)

    def test_identity_back_fills_the_session_already_open(self):
        # The history is loaded before the identity is known, so the running session
        # is stamped after the fact
        history = {"LastLog": 2, "2": {"StartTime": START_TIME, "PluginVersion": "stable9-9.1.007"}}
        log = _make_log(history)
        lm.LoggingManagement.loggingUpdatePluginVersion(log, IDENTITY)
        self.assertEqual(history["2"]["PluginVersion"], IDENTITY)

    def test_a_session_of_an_earlier_run_is_left_alone(self):
        # Its errors were produced by another revision, which is the whole point of storing one
        history = {"LastLog": 2, "2": {"StartTime": START_TIME - 3600, "PluginVersion": "stable9-9.1.006"}}
        log = _make_log(history)
        lm.LoggingManagement.loggingUpdatePluginVersion(log, IDENTITY)
        self.assertEqual(history["2"]["PluginVersion"], "stable9-9.1.006")

    def test_empty_history_is_not_stamped(self):
        log = _make_log({})
        lm.LoggingManagement.loggingUpdatePluginVersion(log, IDENTITY)
        self.assertEqual(log.LogErrorHistory, {})

    def test_history_without_a_start_time_is_not_stamped(self):
        # Entries written by an older version of the plugin
        history = {"LastLog": 1, "1": {"PluginVersion": "stable9-9.1.006"}}
        log = _make_log(history)
        lm.LoggingManagement.loggingUpdatePluginVersion(log, IDENTITY)
        self.assertEqual(history["1"]["PluginVersion"], "stable9-9.1.006")


class TestErrorSessionCarriesTheIdentity(unittest.TestCase):
    """The stored error sessions are what the WebUI error page reads."""

    def _record_an_error(self, log):
        with patch.object(lm, "domoticz_error_api"), \
             patch.object(lm, "loggingWriteErrorHistory"), \
             patch.object(lm, "loggingBuildContext", return_value={"Message": "boom"}):
            lm.loggingError(log, "MainThread", "boom", "Modules", None, None)

    def test_first_error_of_a_run_is_stamped_with_the_identity(self):
        log = _make_log({})
        lm.LoggingManagement.loggingUpdatePluginVersion(log, IDENTITY)
        self._record_an_error(log)
        self.assertEqual(log.LogErrorHistory["0"]["PluginVersion"], IDENTITY)

    def test_a_new_run_opens_its_own_session_with_its_own_identity(self):
        # A restart on an upgraded plugin: the previous session keeps the revision it ran
        history = {
            "LastLog": 0,
            "0": {"LastLog": 0, "StartTime": START_TIME - 3600, "PluginVersion": "stable9-9.1.006 (commit 9546837)"},
        }
        log = _make_log(history)
        lm.LoggingManagement.loggingUpdatePluginVersion(log, IDENTITY)
        self._record_an_error(log)

        self.assertEqual(history["0"]["PluginVersion"], "stable9-9.1.006 (commit 9546837)")
        self.assertEqual(history["1"]["PluginVersion"], IDENTITY)

    def test_an_error_without_an_identity_is_still_recorded(self):
        # loggingUpdatePluginVersion is called right after the logger is built, but an
        # error raised in between must not be lost over a missing version string
        log = _make_log({})
        self._record_an_error(log)
        self.assertIsNone(log.LogErrorHistory["0"]["PluginVersion"])
        self.assertEqual(log.LogErrorHistory["0"]["StartTime"], START_TIME)


if __name__ == "__main__":
    unittest.main()
