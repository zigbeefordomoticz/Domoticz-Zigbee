#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_logging_thread_filter.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the per-thread debug filter
(Classes/LoggingManagement.py: THREAD_GROUP, _rebuild_thread_filter, _should_log_debug).

The ThreadCommunication / ThreadForwarder / ThreadWriter / ThreadDomoticz settings keep
only the debug lines logged from the threads of that group. The filter compares thread
names exactly, so a name in THREAD_GROUP that no thread carries does not just fail to
match: once its setting is on, the filter is not empty and every debug line is dropped.
These tests hold that each name in THREAD_GROUP is one a plugin thread is really given.

Run with:
    pytest tests/Classes/test_logging_thread_filter.py -v
"""

import re
import unittest
from pathlib import Path
from types import SimpleNamespace

# tests/conftest.py installs the DomoticzEx fake at import time, before collection
import Classes.LoggingManagement as lm  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIRS = ("Classes", "Modules", "Zigbee")
HARDWARE_ID = 3


def _thread_names_in_source():
    """Return the name prefixes passed to Thread(name=...) in the plugin source.

    'ZigpyForwarder_%s' % x and f"ZigpyCommunication_{x}" both give the part before
    the HardwareID: 'ZigpyForwarder_' and 'ZigpyCommunication_'.
    """
    pattern = re.compile(r"""name\s*=\s*f?["']([A-Za-z]+_?)(?:%s|\{)""")
    names = set()
    for folder in SOURCE_DIRS:
        for path in (REPO_ROOT / folder).rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "Thread(" in text:
                names.update(pattern.findall(text))
    return names


def _make_log(settings):
    config = {
        (thread % HARDWARE_ID if "%s" in thread else thread): group
        for group, threads in lm.THREAD_GROUP.items()
        for thread in threads
    }
    return SimpleNamespace(
        threadLogConfig=config,
        _thread_filter=set(),
        pluginconf=SimpleNamespace(pluginConf=settings),
    )


class TestThreadGroupNames(unittest.TestCase):

    def test_every_name_is_given_to_a_thread(self):
        in_source = _thread_names_in_source()
        self.assertIn("ZigpyCommunication_", in_source, "the source scan found no thread name")
        for group, threads in lm.THREAD_GROUP.items():
            for thread in threads:
                if "%s" not in thread:
                    continue
                with self.subTest(group=group, thread=thread):
                    self.assertIn(thread.split("%s")[0], in_source)


class TestShouldLogDebug(unittest.TestCase):

    def test_no_filter_keeps_every_thread(self):
        log = _make_log({})
        lm._rebuild_thread_filter(log)
        self.assertTrue(lm._should_log_debug(log, "ZigpyForwarder_3"))

    def test_communication_keeps_the_zigpy_thread(self):
        log = _make_log({"ThreadCommunication": 1})
        lm._rebuild_thread_filter(log)
        self.assertTrue(lm._should_log_debug(log, f"ZigpyCommunication_{HARDWARE_ID}"))
        self.assertFalse(lm._should_log_debug(log, f"ZigpyForwarder_{HARDWARE_ID}"))
        self.assertFalse(lm._should_log_debug(log, "MainThread"))

    def test_forwarder_keeps_the_forwarder_threads(self):
        log = _make_log({"ThreadForwarder": 1})
        lm._rebuild_thread_filter(log)
        self.assertTrue(lm._should_log_debug(log, f"ZigpyForwarder_{HARDWARE_ID}"))
        self.assertTrue(lm._should_log_debug(log, f"ZiGateForwarder_{HARDWARE_ID}"))
        self.assertFalse(lm._should_log_debug(log, f"ZigpyCommunication_{HARDWARE_ID}"))

    def test_another_instance_is_not_kept(self):
        log = _make_log({"ThreadCommunication": 1})
        lm._rebuild_thread_filter(log)
        self.assertFalse(lm._should_log_debug(log, f"ZigpyCommunication_{HARDWARE_ID + 1}"))


if __name__ == "__main__":
    unittest.main()
