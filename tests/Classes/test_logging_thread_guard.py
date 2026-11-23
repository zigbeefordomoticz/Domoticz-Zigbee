#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_logging_thread_guard.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the logging thread surviving a line it cannot process
(Classes/LoggingManagement.py: logging_thread / _catch_error_event).

The thread writes every line of the plugin. An exception leaving its loop used to end it:
every later line, of any level, was queued and never written until the plugin restarted.

Run with:
    pytest tests/Classes/test_logging_thread_guard.py -v
"""

import threading
import unittest
from queue import PriorityQueue
from types import SimpleNamespace
from unittest.mock import patch

# tests/conftest.py installs the DomoticzEx fake at import time, before collection
import Classes.LoggingManagement as lm  # noqa: E402


def _line(counter, logType, message):
    return [counter, "MainThread", "1040", "Input", logType, message, "None", None]


def _make_log():
    return SimpleNamespace(
        logging_running=True,
        logging_queue=PriorityQueue(),
        _logging_failures=set(),
        # Processing an Error line against this history raises KeyError
        LogErrorHistory={"LastLog": 7},
        _startTime=1791140376,
        _newError=False,
        reload_debug_settings=False,
        pluginconf=SimpleNamespace(pluginConf={"enablePluginLogging": False, "logThreadName": False}),
    )


class _Run(unittest.TestCase):

    def run_thread(self, log, lines):
        """Process the lines, then QUIT. Fails when the thread does not get to QUIT."""
        for line in lines:
            log.logging_queue.put(line)
        with patch.object(lm, "domoticz_error_api") as self.error, \
             patch.object(lm, "domoticz_log_api") as self.log, \
             patch.object(lm, "domoticz_status_api") as self.status:
            # QUIT is [0, "QUIT"] and would jump the queue: stop on the last line instead
            lines_left = [len(lines)]
            director = lm.process_logging_event

            def counted(_self, line):
                lines_left[0] -= 1
                if not lines_left[0]:
                    _self.logging_running = False
                director(_self, line)

            with patch.object(lm, "process_logging_event", counted):
                thread = threading.Thread(target=lm.logging_thread, args=(log,), daemon=True)
                thread.start()
                thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(lines_left[0], 0, "lines left unprocessed")

    def errors(self):
        return [call.args[0] for call in self.error.call_args_list]

    def logs(self):
        return [call.args[0] for call in self.log.call_args_list]


class TestLoggingThreadGuard(_Run):

    def test_the_lines_after_a_failure_are_written(self):
        with patch.object(lm, "_debug_logging_filtering", side_effect=ValueError("boom")), \
             patch.object(lm, "_should_log_debug", return_value=True), \
             patch.object(lm, "_is_to_be_logged", return_value=True):
            self.run_thread(_make_log(), [_line(1, "Debug", "one"), _line(2, "Log", "two")])
        self.assertIn("two", self.logs())

    def test_a_failure_names_the_line_and_the_cause(self):
        with patch.object(lm, "loggingDirector", side_effect=ValueError("boom")):
            self.run_thread(_make_log(), [_line(1, "Log", "one")])
        report = [text for text in self.errors() if "logging failed" in text]
        self.assertEqual(len(report), 1)
        for expected in ("Log line of Input", "MainThread", "ValueError: boom"):
            self.assertIn(expected, report[0])

    def test_one_cause_is_reported_once(self):
        def failing(*_args):
            raise ValueError("boom")

        with patch.object(lm, "loggingDirector", failing):
            self.run_thread(_make_log(), [_line(n, "Log", "line %s" % n) for n in range(1, 6)])
        self.assertEqual(len(self.errors()), 1)

    def test_another_cause_is_reported_too(self):
        failures = [ValueError("first"), KeyError("second")]

        with patch.object(lm, "loggingDirector", side_effect=failures):
            self.run_thread(_make_log(), [_line(1, "Log", "one"), _line(2, "Log", "two")])
        self.assertEqual(len(self.errors()), 2)

    def test_every_failed_line_still_reaches_domoticz(self):
        with patch.object(lm, "loggingDirector", side_effect=ValueError("boom")):
            self.run_thread(_make_log(), [_line(1, "Log", "one"), _line(2, "Status", "two"), _line(3, "Warning", "three")])
        for message in ("one", "two", "three"):
            self.assertIn(message, self.logs())

    def test_a_failed_error_is_not_shown_twice(self):
        with patch.object(lm, "loggingBuildContext", side_effect=ValueError("boom")):
            self.run_thread(_make_log(), [_line(1, "Error", "broken")])
        self.assertEqual(self.errors().count("broken"), 1)
        self.assertNotIn("broken", self.logs())

    def test_an_inconsistent_history_does_not_stop_the_thread(self):
        self.run_thread(_make_log(), [_line(1, "Error", "broken"), _line(2, "Log", "after")])
        self.assertIn("broken", self.errors())
        self.assertIn("after", self.logs())

    def test_a_failing_report_does_not_stop_the_thread(self):
        log = _make_log()
        with patch.object(lm, "loggingDirector", side_effect=ValueError("boom")), \
             patch.object(lm.traceback, "extract_tb", side_effect=RuntimeError("nested")):
            self.run_thread(log, [_line(1, "Log", "one"), _line(2, "Log", "two")])


class TestQuit(unittest.TestCase):

    def test_quit_still_ends_the_thread(self):
        log = _make_log()
        log.logging_queue.put([0, "QUIT"])
        with patch.object(lm, "domoticz_log_api"):
            thread = threading.Thread(target=lm.logging_thread, args=(log,), daemon=True)
            thread.start()
            thread.join(5)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
