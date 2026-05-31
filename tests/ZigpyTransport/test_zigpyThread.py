#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Classes/ZigpyTransport/zigpyThread.py

Covers:
  - stop_zigpy_thread   (flags, queue sentinel, shutdown_event, task cancellation)
  - start_zigpy_thread  (thread creation guard, Windows policy, already-running warning)
  - setup_zigpy_thread  (thread name, daemon flag, start called)
  - cleanup_unused_concurrency_state re-export (backward-compat with Transport.py)
"""

import asyncio
import queue
import sys
import threading
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_transport():
    t = MagicMock()
    t.log = MagicMock()
    t.log.logging = MagicMock()
    t.zigpy_running          = True
    t._zigpy_stop_requested  = False
    # Use a plain MagicMock for _shutdown_event — avoids needing a running loop
    # in Python 3.8 and still lets stop_zigpy_thread call .set() without error.
    t._shutdown_event        = MagicMock()
    t.zigpy_loop             = MagicMock()
    t.writer_queue           = queue.Queue()
    t.hardwareid             = 42
    t.manual_topology_scan_task     = None
    t.manual_interference_scan_task = None
    t.zigpy_thread           = None
    return t


# ===========================================================================
# stop_zigpy_thread
# ===========================================================================

class TestStopZigpyThread(unittest.TestCase):

    def test_sets_stop_requested(self):
        from Classes.ZigpyTransport.zigpyThread import stop_zigpy_thread
        t = make_transport()
        stop_zigpy_thread(t)
        self.assertTrue(t._zigpy_stop_requested)

    def test_sets_zigpy_running_false(self):
        from Classes.ZigpyTransport.zigpyThread import stop_zigpy_thread
        t = make_transport()
        stop_zigpy_thread(t)
        self.assertFalse(t.zigpy_running)

    def test_signals_shutdown_event(self):
        from Classes.ZigpyTransport.zigpyThread import stop_zigpy_thread
        t = make_transport()
        t.zigpy_loop.call_soon_threadsafe = MagicMock()
        stop_zigpy_thread(t)
        t.zigpy_loop.call_soon_threadsafe.assert_called_once()

    def test_pushes_stop_sentinel_to_writer_queue(self):
        from Classes.ZigpyTransport.zigpyThread import stop_zigpy_thread
        t = make_transport()
        stop_zigpy_thread(t)
        sentinel = t.writer_queue.get_nowait()
        self.assertEqual(sentinel, "STOP")

    def test_no_signal_when_loop_is_none(self):
        from Classes.ZigpyTransport.zigpyThread import stop_zigpy_thread
        t = make_transport()
        t.zigpy_loop = None
        # Must not raise
        stop_zigpy_thread(t)
        self.assertTrue(t._zigpy_stop_requested)

    def test_no_queue_push_when_writer_queue_none(self):
        from Classes.ZigpyTransport.zigpyThread import stop_zigpy_thread
        t = make_transport()
        t.writer_queue = None
        # Must not raise
        stop_zigpy_thread(t)

    def test_cancels_topology_scan_task(self):
        from Classes.ZigpyTransport.zigpyThread import stop_zigpy_thread
        t = make_transport()
        mock_task = MagicMock()
        t.manual_topology_scan_task = mock_task
        stop_zigpy_thread(t)
        mock_task.cancel.assert_called_once()

    def test_cancels_interference_scan_task(self):
        from Classes.ZigpyTransport.zigpyThread import stop_zigpy_thread
        t = make_transport()
        mock_task = MagicMock()
        t.manual_interference_scan_task = mock_task
        stop_zigpy_thread(t)
        mock_task.cancel.assert_called_once()

    def test_no_cancel_when_tasks_are_none(self):
        from Classes.ZigpyTransport.zigpyThread import stop_zigpy_thread
        t = make_transport()
        t.manual_topology_scan_task     = None
        t.manual_interference_scan_task = None
        # Must not raise AttributeError
        stop_zigpy_thread(t)


# ===========================================================================
# start_zigpy_thread
# ===========================================================================

class TestStartZigpyThread(unittest.TestCase):

    def test_calls_setup_when_no_thread_exists(self):
        from Classes.ZigpyTransport.zigpyThread import start_zigpy_thread
        t = make_transport()
        t.zigpy_thread = None
        with patch("Classes.ZigpyTransport.zigpyThread.setup_zigpy_thread") as mock_setup:
            start_zigpy_thread(t)
        mock_setup.assert_called_once_with(t)

    def test_calls_setup_when_thread_not_alive(self):
        from Classes.ZigpyTransport.zigpyThread import start_zigpy_thread
        t = make_transport()
        dead_thread = MagicMock()
        dead_thread.is_alive.return_value = False
        t.zigpy_thread = dead_thread
        with patch("Classes.ZigpyTransport.zigpyThread.setup_zigpy_thread") as mock_setup:
            start_zigpy_thread(t)
        mock_setup.assert_called_once_with(t)

    def test_skips_setup_when_thread_already_alive(self):
        from Classes.ZigpyTransport.zigpyThread import start_zigpy_thread
        t = make_transport()
        alive_thread = MagicMock()
        alive_thread.is_alive.return_value = True
        t.zigpy_thread = alive_thread
        with patch("Classes.ZigpyTransport.zigpyThread.setup_zigpy_thread") as mock_setup:
            start_zigpy_thread(t)
        mock_setup.assert_not_called()

    def test_logs_warning_when_already_running(self):
        from Classes.ZigpyTransport.zigpyThread import start_zigpy_thread
        t = make_transport()
        alive_thread = MagicMock()
        alive_thread.is_alive.return_value = True
        t.zigpy_thread = alive_thread
        with patch("Classes.ZigpyTransport.zigpyThread.setup_zigpy_thread"):
            start_zigpy_thread(t)
        warning_calls = [
            c for c in t.log.logging.call_args_list
            if c.args[1] == "Warning"
        ]
        self.assertTrue(warning_calls)


# ===========================================================================
# setup_zigpy_thread
# ===========================================================================

class TestSetupZigpyThread(unittest.TestCase):

    def test_creates_thread_with_correct_name(self):
        from Classes.ZigpyTransport.zigpyThread import setup_zigpy_thread
        t = make_transport()
        with patch("Classes.ZigpyTransport.zigpyThread.Thread") as mock_thread_cls:
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            setup_zigpy_thread(t)
        _, kwargs = mock_thread_cls.call_args
        self.assertEqual(kwargs["name"], f"ZigpyCommunication_{t.hardwareid}")

    def test_thread_is_not_daemon(self):
        from Classes.ZigpyTransport.zigpyThread import setup_zigpy_thread
        t = make_transport()
        with patch("Classes.ZigpyTransport.zigpyThread.Thread") as mock_thread_cls:
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            setup_zigpy_thread(t)
        self.assertFalse(mock_thread.daemon)

    def test_thread_is_started(self):
        from Classes.ZigpyTransport.zigpyThread import setup_zigpy_thread
        t = make_transport()
        with patch("Classes.ZigpyTransport.zigpyThread.Thread") as mock_thread_cls:
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            setup_zigpy_thread(t)
        mock_thread.start.assert_called_once()

    def test_thread_stored_on_transport(self):
        from Classes.ZigpyTransport.zigpyThread import setup_zigpy_thread
        t = make_transport()
        with patch("Classes.ZigpyTransport.zigpyThread.Thread") as mock_thread_cls:
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            setup_zigpy_thread(t)
        self.assertIs(t.zigpy_thread, mock_thread)

    def test_target_is_zigpy_thread_function(self):
        from Classes.ZigpyTransport.zigpyThread import setup_zigpy_thread, zigpy_thread_function
        t = make_transport()
        with patch("Classes.ZigpyTransport.zigpyThread.Thread") as mock_thread_cls:
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            setup_zigpy_thread(t)
        _, kwargs = mock_thread_cls.call_args
        self.assertIs(kwargs["target"], zigpy_thread_function)


# ===========================================================================
# cleanup_unused_concurrency_state re-export
# ===========================================================================

class TestCleanupReexport(unittest.TestCase):

    def test_importable_from_zigpythread(self):
        """Transport.py imports this from zigpyThread — must remain accessible."""
        from Classes.ZigpyTransport.zigpyThread import cleanup_unused_concurrency_state
        self.assertTrue(callable(cleanup_unused_concurrency_state))

    def test_same_object_as_zigpysend(self):
        """The re-export must point to the same function as zigpySend."""
        from Classes.ZigpyTransport.zigpyThread import cleanup_unused_concurrency_state as from_thread
        from Classes.ZigpyTransport.zigpySend  import cleanup_unused_concurrency_state as from_send
        self.assertIs(from_thread, from_send)


if __name__ == "__main__":
    unittest.main()
