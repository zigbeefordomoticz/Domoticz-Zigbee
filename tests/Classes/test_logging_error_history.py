#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_logging_error_history.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for what the error history keeps and forgets
(Classes/LoggingManagement.py: loggingError, loggingCleaningErrorHistory, open_log_history).

The history is a dict of sessions (one per plugin start), each a dict of errors. Both mix
numbered keys, the entries, with named ones ("LastLog", "PluginVersion"...). The entries used
to be told by their position, which stopped being right when "PluginVersion" became the fifth
named key: the 20th error of a session removed the plugin version, and the 7 days retention
never removed anything.

Run with:
    pytest tests/Classes/test_logging_error_history.py -v
"""

import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# tests/conftest.py installs the DomoticzEx fake at import time, before collection
import Classes.LoggingManagement as lm  # noqa: E402

START_TIME = 1791140376
IDENTITY = "stable9-9.1.011 (commit 15d5d94, Certified DB 11.627)"
NAMED_KEYS = ["LastLog", "StartTime", "FirmwareVersion", "FirmwareMajorVersion", "PluginVersion"]
DAY = 24 * 3600


def _make_log(history=None, start_time=START_TIME, version=IDENTITY):
    """Return a LoggingManagement-like object carrying only what the SUT reads."""
    return SimpleNamespace(
        LogErrorHistory=history if history is not None else {},
        _startTime=start_time,
        PluginVersion=version,
        FirmwareVersion=None,
        FirmwareMajorVersion=None,
        _newError=False,
        HardwareID=1,
        ListOfDevices={},
        PluginHealth={"Txt": "Ready"},
        permitTojoin={"Duration": 0, "Starttime": START_TIME},
        pluginconf=SimpleNamespace(pluginConf={"enablePluginLogging": False}),
    )


def _record(log, *messages):
    with patch.object(lm, "domoticz_error_api"), patch.object(lm, "loggingWriteErrorHistory"):
        for message in messages:
            lm.loggingError(log, "MainThread", message, "Input", None, None)


def _messages(session):
    return [session[key]["message"] for key in lm._numbered_keys(session)]


def _session(start_time, *ages, version=IDENTITY):
    """A session whose errors are that old, in seconds."""
    now = time.time()
    session = {
        "LastLog": len(ages) - 1,
        "StartTime": start_time,
        "FirmwareVersion": None,
        "FirmwareMajorVersion": None,
        "PluginVersion": version,
    }
    for index, age in enumerate(ages):
        session[str(index)] = {"Time": int(now - age), "message": "error %s" % index}
    return session


def _clean(log):
    lm.LoggingManagement.loggingCleaningErrorHistory(log)


class TestErrorsOfASession(unittest.TestCase):

    def test_a_full_session_keeps_its_named_keys(self):
        log = _make_log()
        _record(log, *["e%s" % n for n in range(lm.LOG_MAX_ERRORS_PER_SESSION + 7)])
        session = log.LogErrorHistory["0"]
        self.assertEqual([key for key in session if not key.isdigit()], NAMED_KEYS)
        self.assertEqual(session["PluginVersion"], IDENTITY)

    def test_a_full_session_keeps_the_newest_errors(self):
        log = _make_log()
        _record(log, *["e%s" % n for n in range(lm.LOG_MAX_ERRORS_PER_SESSION + 7)])
        kept = _messages(log.LogErrorHistory["0"])
        self.assertEqual(kept, ["e%s" % n for n in range(7, lm.LOG_MAX_ERRORS_PER_SESSION + 7)])

    def test_the_limit_is_reached_exactly(self):
        log = _make_log()
        _record(log, *["e%s" % n for n in range(lm.LOG_MAX_ERRORS_PER_SESSION)])
        self.assertEqual(len(_messages(log.LogErrorHistory["0"])), lm.LOG_MAX_ERRORS_PER_SESSION)

    def test_oldest_is_told_by_number_not_by_text(self):
        # "10" sorts before "9" as text
        log = _make_log()
        with patch.object(lm, "LOG_MAX_ERRORS_PER_SESSION", 3):
            _record(log, *["e%s" % n for n in range(12)])
        self.assertEqual(_messages(log.LogErrorHistory["0"]), ["e9", "e10", "e11"])

    def test_a_session_that_lost_its_plugin_version_still_works(self):
        # Histories written by 9.1.010 and before
        session = _session(START_TIME, *([0] * lm.LOG_MAX_ERRORS_PER_SESSION))
        del session["PluginVersion"]
        log = _make_log({"LastLog": 0, "0": session})
        _record(log, "new")
        self.assertEqual(len(_messages(session)), lm.LOG_MAX_ERRORS_PER_SESSION)
        self.assertEqual(_messages(session)[-1], "new")


class TestSessions(unittest.TestCase):

    def test_a_new_start_opens_a_session(self):
        log = _make_log({"LastLog": 0, "0": _session(START_TIME - DAY, 0)})
        _record(log, "new")
        self.assertEqual(log.LogErrorHistory["LastLog"], 1)
        self.assertEqual(_messages(log.LogErrorHistory["1"]), ["new"])

    def test_only_the_last_starts_are_kept(self):
        history = {"LastLog": 11}
        for index in range(8, 12):
            history[str(index)] = _session(START_TIME - DAY, 0)
        log = _make_log(history)
        _record(log, "a")
        log._startTime += 60
        _record(log, "b")
        self.assertEqual(lm._numbered_keys(log.LogErrorHistory), ["9", "10", "11", "12", "13"])

    def test_the_old_structure_is_not_written_into(self):
        log = _make_log({"LastLog": 0, "0": {"Time": int(time.time()), "message": "flat"}})
        _record(log, "new")
        self.assertEqual(log.LogErrorHistory["0"]["message"], "flat")
        self.assertEqual(_messages(log.LogErrorHistory["1"]), ["new"])

    def test_a_session_purged_under_the_counter_is_not_an_error(self):
        log = _make_log({"LastLog": 7})
        _record(log, "new")
        self.assertEqual(_messages(log.LogErrorHistory["8"]), ["new"])


class TestRetention(unittest.TestCase):

    def test_expired_errors_are_removed_and_the_others_kept(self):
        log = _make_log({"LastLog": 0, "0": _session(START_TIME, 9 * DAY, 8 * DAY, DAY)})
        _clean(log)
        self.assertEqual(_messages(log.LogErrorHistory["0"]), ["error 2"])
        self.assertEqual(log.LogErrorHistory["0"]["PluginVersion"], IDENTITY)

    def test_a_session_left_with_no_error_is_removed(self):
        log = _make_log({"LastLog": 1, "0": _session(START_TIME - 9 * DAY, 9 * DAY), "1": _session(START_TIME, DAY)})
        _clean(log)
        self.assertEqual(lm._numbered_keys(log.LogErrorHistory), ["1"])

    def test_nothing_left_empties_the_history(self):
        log = _make_log({"LastLog": 0, "0": _session(START_TIME, 9 * DAY)})
        _clean(log)
        self.assertEqual(log.LogErrorHistory, {})

    def test_recent_errors_are_left_alone(self):
        log = _make_log({"LastLog": 0, "0": _session(START_TIME, DAY, 0)})
        _clean(log)
        self.assertEqual(_messages(log.LogErrorHistory["0"]), ["error 0", "error 1"])

    def test_a_session_without_a_version_can_be_cleaned(self):
        # "Time" in None raised TypeError from onHeartbeat
        log = _make_log({"LastLog": 0, "0": _session(START_TIME, 9 * DAY, 0, version=None)})
        _clean(log)
        self.assertEqual(_messages(log.LogErrorHistory["0"]), ["error 1"])

    def test_the_old_structure_expires_too(self):
        log = _make_log({"LastLog": 1, "0": {"Time": int(time.time() - 9 * DAY)}, "1": _session(START_TIME, 0)})
        _clean(log)
        self.assertEqual(lm._numbered_keys(log.LogErrorHistory), ["1"])

    def test_an_empty_history_is_left_alone(self):
        log = _make_log({})
        _clean(log)
        self.assertEqual(log.LogErrorHistory, {})

    def test_errors_can_be_recorded_after_a_cleaning(self):
        log = _make_log({"LastLog": 0, "0": _session(START_TIME, 9 * DAY)})
        _clean(log)
        _record(log, "new")
        self.assertEqual(_messages(log.LogErrorHistory["0"]), ["new"])


class TestFirmwareBackFill(unittest.TestCase):

    def test_the_first_session_gets_the_firmware_too(self):
        # Its index is 0, which used to read as "no session"
        log = _make_log()
        _record(log, "before the coordinator answered")
        lm.LoggingManagement.loggingUpdateFirmware(log, "8.0.2.0 build 397", "30")
        self.assertEqual(log.LogErrorHistory["0"]["FirmwareVersion"], "8.0.2.0 build 397")
        self.assertEqual(log.LogErrorHistory["0"]["FirmwareMajorVersion"], "30")

    def test_the_session_of_an_earlier_run_is_left_alone(self):
        log = _make_log({"LastLog": 0, "0": _session(START_TIME - DAY, 0)})
        lm.LoggingManagement.loggingUpdateFirmware(log, "8.0.2.0 build 397", "30")
        self.assertIsNone(log.LogErrorHistory["0"]["FirmwareVersion"])


class TestLoading(unittest.TestCase):

    def _load(self, content):
        log = _make_log()
        with tempfile.TemporaryDirectory() as folder:
            log.pluginconf.pluginConf["pluginLogs"] = folder
            (Path(folder) / (lm.LOG_ERROR_HISTORY + "01.json")).write_text(content)
            with patch.object(lm, "domoticz_error_api") as self.error, patch.object(lm, "domoticz_status_api"):
                lm.LoggingManagement.open_log_history(log)
        return log

    def test_a_history_is_loaded(self):
        history = {"LastLog": 0, "0": _session(START_TIME, 0)}
        self.assertEqual(self._load(json.dumps(history)).LogErrorHistory, history)
        self.error.assert_not_called()

    def test_an_empty_history_is_loaded(self):
        self.assertEqual(self._load("{}").LogErrorHistory, {})
        self.error.assert_not_called()

    def test_unusable_content_is_refused_and_reported(self):
        for content in ("[]", "null", '{"LastLog": "x"}', '{"LastLog": 0, "0": null}', '{"LastLog": 0, "0": {"0": "text"}}'):
            with self.subTest(content=content):
                log = self._load(content)
                self.assertEqual(log.LogErrorHistory, {})
                self.error.assert_called_once()
                _record(log, "new")
                self.assertEqual(_messages(log.LogErrorHistory["0"]), ["new"])


if __name__ == "__main__":
    unittest.main()
