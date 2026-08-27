#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Classes/ZigpyTransport/zigpyThread.py

Covers:
  - stop_zigpy_thread   (flags, queue sentinel, shutdown_event, task cancellation)
  - start_zigpy_thread  (thread creation guard, Windows policy, already-running warning)
  - setup_zigpy_thread  (thread name, daemon flag, start called)
  - cleanup_unused_concurrency_state re-export (backward-compat with Transport.py)
  - _is_benign_startup_get_device_keyerror  (issue #2010 KeyError fingerprinting)
  - _coordinator_registered                 ("Green" check, no timing guesswork)
  - _zigpy_loop_exception_handler           (suppress-vs-passthrough decision)
"""

import asyncio
import queue
import sys
import threading
import traceback
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


# ===========================================================================
# Helpers for the issue #2010 exception-handling tests
# ===========================================================================

def _raise_keyerror_from(filename, funcname, args=()):
    """
    Raise (and return, via except) a KeyError whose innermost traceback
    frame looks exactly like AppGeneric.get_device()'s `raise KeyError` —
    i.e. a function named `funcname` defined in a file called `filename` —
    without needing the real module on disk. Used to test the traceback
    fingerprinting in _is_benign_startup_get_device_keyerror() precisely.
    """
    args_repr = ", ".join(repr(a) for a in args)
    src = f"def {funcname}():\n    raise KeyError({args_repr})\n"
    code = compile(src, filename, "exec")
    ns = {}
    exec(code, ns)  # nosec - test-only, source is a fixed literal built above
    try:
        ns[funcname]()
    except KeyError as exc:
        return exc
    raise AssertionError("KeyError was not raised")  # pragma: no cover


def make_fake_app(coordinator_ieee="00:12:4b:00:19:38:6d:d0", registered=False):
    """A minimal stand-in for AppZnp/AppBellows/AppDeconz/AppBlz with just
    enough shape for _coordinator_registered(): .state.node_info.ieee and
    .devices (dict-like membership)."""
    app = MagicMock()
    app.state.node_info.ieee = coordinator_ieee
    app.devices = {coordinator_ieee: MagicMock()} if registered else {}
    return app


# ===========================================================================
# _is_benign_startup_get_device_keyerror
# ===========================================================================

class TestIsBenignStartupGetDeviceKeyError(unittest.TestCase):

    def test_true_for_bare_keyerror_from_appgeneric_get_device(self):
        from Classes.ZigpyTransport.zigpyThread import \
            _is_benign_startup_get_device_keyerror
        exc = _raise_keyerror_from(
            "/home/pi/domoticz/plugins/Domoticz-Zigbee/Classes/ZigpyTransport/AppGeneric.py",
            "get_device",
        )
        self.assertTrue(_is_benign_startup_get_device_keyerror(exc))

    def test_false_when_keyerror_has_args(self):
        """A `raise KeyError("some_key")` is a different, informative error —
        not the bare control-flow KeyError get_device() raises — so it must
        not be swallowed."""
        from Classes.ZigpyTransport.zigpyThread import \
            _is_benign_startup_get_device_keyerror
        exc = _raise_keyerror_from(
            "/home/pi/domoticz/plugins/Domoticz-Zigbee/Classes/ZigpyTransport/AppGeneric.py",
            "get_device",
            args=("some_key",),
        )
        self.assertFalse(_is_benign_startup_get_device_keyerror(exc))

    def test_false_for_keyerror_from_unrelated_function(self):
        from Classes.ZigpyTransport.zigpyThread import \
            _is_benign_startup_get_device_keyerror
        exc = _raise_keyerror_from(
            "/home/pi/domoticz/plugins/Domoticz-Zigbee/Modules/tools.py",
            "some_other_function",
        )
        self.assertFalse(_is_benign_startup_get_device_keyerror(exc))

    def test_false_for_get_device_in_a_different_file(self):
        """Matching must be scoped to AppGeneric.py specifically, not any
        function merely named get_device()."""
        from Classes.ZigpyTransport.zigpyThread import \
            _is_benign_startup_get_device_keyerror
        exc = _raise_keyerror_from(
            "/home/pi/domoticz/plugins/Domoticz-Zigbee/Classes/ZigpyTransport/AppZnp.py",
            "get_device",
        )
        self.assertFalse(_is_benign_startup_get_device_keyerror(exc))

    def test_false_for_non_keyerror_exception(self):
        from Classes.ZigpyTransport.zigpyThread import \
            _is_benign_startup_get_device_keyerror
        try:
            raise ValueError("nope")
        except ValueError as exc:
            self.assertFalse(_is_benign_startup_get_device_keyerror(exc))


# ===========================================================================
# _coordinator_registered
# ===========================================================================

class TestCoordinatorRegistered(unittest.TestCase):

    def test_false_when_app_is_none(self):
        from Classes.ZigpyTransport.zigpyThread import _coordinator_registered
        t = make_transport()
        t.app = None
        self.assertFalse(_coordinator_registered(t))

    def test_false_when_coordinator_not_yet_in_devices_table(self):
        from Classes.ZigpyTransport.zigpyThread import _coordinator_registered
        t = make_transport()
        t.app = make_fake_app(registered=False)
        self.assertFalse(_coordinator_registered(t))

    def test_true_once_coordinator_is_in_devices_table(self):
        from Classes.ZigpyTransport.zigpyThread import _coordinator_registered
        t = make_transport()
        t.app = make_fake_app(registered=True)
        self.assertTrue(_coordinator_registered(t))

    def test_false_when_node_info_not_yet_available(self):
        """Very early in startup, self.app.state.node_info(.ieee) may not
        exist yet at all — must be treated as not-registered, not raise."""
        from Classes.ZigpyTransport.zigpyThread import _coordinator_registered
        t = make_transport()
        t.app = MagicMock()
        del t.app.state.node_info.ieee  # AttributeError on access
        self.assertFalse(_coordinator_registered(t))

    def test_re_arms_on_fresh_app_after_reconnect(self):
        """Each supervisor restart cycle installs a brand new App instance
        (see radioStart.py `self.app = App(config)`) with an empty device
        table -- the check must re-evaluate against whatever self.app
        currently is, not cache a stale answer."""
        from Classes.ZigpyTransport.zigpyThread import _coordinator_registered
        t = make_transport()
        t.app = make_fake_app(registered=True)
        self.assertTrue(_coordinator_registered(t))

        # Radio reconnects: supervisor swaps in a fresh, not-yet-registered App
        t.app = make_fake_app(registered=False)
        self.assertFalse(_coordinator_registered(t))


# ===========================================================================
# _zigpy_loop_exception_handler
# ===========================================================================

class TestZigpyLoopExceptionHandler(unittest.TestCase):

    def _benign_exc(self):
        return _raise_keyerror_from(
            "/home/pi/domoticz/plugins/Domoticz-Zigbee/Classes/ZigpyTransport/AppGeneric.py",
            "get_device",
        )

    def test_suppresses_benign_keyerror_during_startup_race(self):
        from Classes.ZigpyTransport.zigpyThread import \
            _zigpy_loop_exception_handler
        t = make_transport()
        t.app = make_fake_app(registered=False)
        loop = MagicMock()
        context = {"message": "Task exception was never retrieved", "exception": self._benign_exc()}

        _zigpy_loop_exception_handler(t, loop, context)

        loop.default_exception_handler.assert_not_called()
        debug_calls = [c for c in t.log.logging.call_args_list if c.args[1] == "Debug"]
        self.assertTrue(debug_calls)

    def test_passes_through_once_coordinator_is_registered(self):
        """Same exact exception shape, but the coordinator is now known
        ('Green') -- must behave exactly like before the fix, including
        during normal runtime device pairing."""
        from Classes.ZigpyTransport.zigpyThread import \
            _zigpy_loop_exception_handler
        t = make_transport()
        t.app = make_fake_app(registered=True)
        loop = MagicMock()
        context = {"message": "Task exception was never retrieved", "exception": self._benign_exc()}

        _zigpy_loop_exception_handler(t, loop, context)

        loop.default_exception_handler.assert_called_once_with(context)

    def test_passes_through_unrelated_exception_regardless_of_registration(self):
        from Classes.ZigpyTransport.zigpyThread import \
            _zigpy_loop_exception_handler
        t = make_transport()
        t.app = make_fake_app(registered=False)
        loop = MagicMock()
        try:
            raise ValueError("some real bug")
        except ValueError as exc:
            context = {"message": "Task exception was never retrieved", "exception": exc}

        _zigpy_loop_exception_handler(t, loop, context)

        loop.default_exception_handler.assert_called_once_with(context)

    def test_passes_through_when_context_has_no_exception(self):
        from Classes.ZigpyTransport.zigpyThread import \
            _zigpy_loop_exception_handler
        t = make_transport()
        t.app = make_fake_app(registered=False)
        loop = MagicMock()
        context = {"message": "some non-exception loop warning"}

        _zigpy_loop_exception_handler(t, loop, context)

        loop.default_exception_handler.assert_called_once_with(context)

    def test_does_not_suppress_keyerror_with_args_even_during_startup(self):
        from Classes.ZigpyTransport.zigpyThread import \
            _zigpy_loop_exception_handler
        t = make_transport()
        t.app = make_fake_app(registered=False)
        loop = MagicMock()
        exc = _raise_keyerror_from(
            "/home/pi/domoticz/plugins/Domoticz-Zigbee/Classes/ZigpyTransport/AppGeneric.py",
            "get_device",
            args=("unexpected",),
        )
        context = {"message": "Task exception was never retrieved", "exception": exc}

        _zigpy_loop_exception_handler(t, loop, context)

        loop.default_exception_handler.assert_called_once_with(context)


if __name__ == "__main__":
    unittest.main()
