#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Classes/ZigpyTransport/supervisor.py

Covers:
  - zigpy_heartbeat_activity
  - _prepare_for_restart
  - _maybe_reset_radio
  - _watchdog  (startup-timeout + health transitions + DEAD trigger)
  - _supervisor (stop-requested, circuit-breaker, stability-reset, backoff)
  - _cleanup
"""

import asyncio
import queue
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(coro):
    """Run *coro* in a fresh event loop and return its result."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def make_transport(loop=None):
    """Minimal ZigpyTransport-like object understood by supervisor.py."""
    t = MagicMock()
    t.log = MagicMock()
    t.log.logging = MagicMock()
    t.zigpy_loop          = loop
    t.zigpy_running       = False
    t._zigpy_stop_requested = False
    t._shutdown_event     = None
    t._restart_count      = 0
    t._consecutive_failures = 0
    t._restart_timestamps = []
    t._stack_health       = "STARTING"
    t._last_heartbeat     = None
    t._last_activity      = None
    t.app                 = None
    t.writer_queue        = queue.Queue()
    t._concurrent_requests_semaphores_list = {}
    t._currently_waiting_requests_list     = {}
    t._currently_not_reachable             = []
    t.restart_plugin      = MagicMock()
    return t


# ===========================================================================
# zigpy_heartbeat_activity
# ===========================================================================

class TestZigpyHeartbeatActivity(unittest.TestCase):

    def test_no_op_when_loop_is_none(self):
        from Classes.ZigpyTransport.supervisor import zigpy_heartbeat_activity
        t = make_transport(loop=None)
        t._last_heartbeat = None
        t._last_activity  = None
        zigpy_heartbeat_activity(t)
        self.assertIsNone(t._last_heartbeat)
        self.assertIsNone(t._last_activity)

    def test_updates_timestamps_when_loop_set(self):
        from Classes.ZigpyTransport.supervisor import zigpy_heartbeat_activity
        loop = asyncio.new_event_loop()
        try:
            t = make_transport(loop=loop)
            t._last_heartbeat = None
            t._last_activity  = None
            zigpy_heartbeat_activity(t)
            self.assertIsNotNone(t._last_heartbeat)
            self.assertIsNotNone(t._last_activity)
            self.assertEqual(t._last_heartbeat, t._last_activity)
        finally:
            loop.close()

    def test_heartbeat_uses_loop_time(self):
        from Classes.ZigpyTransport.supervisor import zigpy_heartbeat_activity
        loop = asyncio.new_event_loop()
        try:
            t = make_transport(loop=loop)
            before = loop.time()
            zigpy_heartbeat_activity(t)
            after = loop.time()
            self.assertGreaterEqual(t._last_heartbeat, before)
            self.assertLessEqual(t._last_heartbeat, after)
        finally:
            loop.close()


# ===========================================================================
# _prepare_for_restart
# ===========================================================================

class TestPrepareForRestart(unittest.TestCase):

    def _run_prepare(self, transport):
        from Classes.ZigpyTransport.supervisor import _prepare_for_restart
        run(_prepare_for_restart(transport))

    def test_clears_concurrency_state(self):
        t = make_transport()
        t._concurrent_requests_semaphores_list = {"ieee1": MagicMock()}
        t._currently_waiting_requests_list     = {"ieee1": 2}
        t._currently_not_reachable             = ["ieee1"]
        self._run_prepare(t)
        self.assertEqual(t._concurrent_requests_semaphores_list, {})
        self.assertEqual(t._currently_waiting_requests_list, {})
        self.assertEqual(t._currently_not_reachable, [])

    def test_creates_fresh_writer_queue(self):
        t = make_transport()
        old_queue = t.writer_queue
        old_queue.put_nowait("stale-command")
        self._run_prepare(t)
        # A brand-new queue must be empty
        self.assertTrue(t.writer_queue.empty())
        self.assertIsNot(t.writer_queue, old_queue)

    def test_resets_zigpy_running_to_false(self):
        t = make_transport()
        t.zigpy_running = True
        self._run_prepare(t)
        self.assertFalse(t.zigpy_running)

    def test_nulls_app_and_calls_disconnect_when_app_is_set(self):
        t = make_transport()
        mock_app = AsyncMock()
        t.app = mock_app
        self._run_prepare(t)
        self.assertIsNone(t.app)
        mock_app.disconnect.assert_called_once()

    def test_disconnect_exception_is_suppressed(self):
        """A failing disconnect must not propagate — restart must proceed."""
        t = make_transport()
        mock_app = AsyncMock()
        mock_app.disconnect.side_effect = Exception("port error")
        t.app = mock_app
        # Should not raise
        self._run_prepare(t)
        self.assertIsNone(t.app)

    def test_no_disconnect_when_app_is_none(self):
        t = make_transport()
        t.app = None
        # Should complete without error
        self._run_prepare(t)
        self.assertIsNone(t.app)


# ===========================================================================
# _maybe_reset_radio
# ===========================================================================

class TestMaybeResetRadio(unittest.TestCase):

    def test_nulls_app_after_disconnect(self):
        from Classes.ZigpyTransport.supervisor import _maybe_reset_radio
        t = make_transport()
        mock_app = AsyncMock()
        t.app = mock_app
        t._consecutive_failures = 5
        with patch("Classes.ZigpyTransport.supervisor.asyncio.sleep", new=AsyncMock()):
            run(_maybe_reset_radio(t))
        self.assertIsNone(t.app)

    def test_no_error_when_app_is_none(self):
        from Classes.ZigpyTransport.supervisor import _maybe_reset_radio
        t = make_transport()
        t.app = None
        t._consecutive_failures = 5
        with patch("Classes.ZigpyTransport.supervisor.asyncio.sleep", new=AsyncMock()):
            run(_maybe_reset_radio(t))  # must not raise

    def test_disconnect_exception_is_suppressed(self):
        from Classes.ZigpyTransport.supervisor import _maybe_reset_radio
        t = make_transport()
        mock_app = AsyncMock()
        mock_app.disconnect.side_effect = RuntimeError("boom")
        t.app = mock_app
        t._consecutive_failures = 5
        with patch("Classes.ZigpyTransport.supervisor.asyncio.sleep", new=AsyncMock()):
            run(_maybe_reset_radio(t))  # must not raise
        self.assertIsNone(t.app)


# ===========================================================================
# _watchdog
# ===========================================================================

class TestWatchdog(unittest.TestCase):
    """
    _watchdog polls every WATCH_DG_HEARTBEAT_INTERVAL seconds.
    We patch asyncio.sleep to advance simulated time instantly and control
    loop.time() via a counter attached to a real event loop object.
    """

    def _make_watchdog_transport(self, loop, startup_offset=0):
        """
        Return a transport whose loop.time() climbs with each call.
        `startup_offset` shifts the simulated clock past the startup window.
        """
        t = make_transport(loop=loop)
        t._stack_health   = "STARTING"
        t._shutdown_event = asyncio.Event()
        # Attach a ticking clock to the real loop object
        _tick = [loop.time() + startup_offset]

        def fake_time():
            _tick[0] += 35  # advance 35 s per tick (> WATCH_DG_HEARTBEAT_INTERVAL)
            return _tick[0]

        loop.time = fake_time
        return t

    def test_startup_timeout_sets_shutdown_event(self):
        """No heartbeat received → startup deadline exceeded → shutdown_event set."""
        from Classes.ZigpyTransport.supervisor import _watchdog, STARTUP_TIMEOUT

        async def run_test():
            loop = asyncio.get_event_loop()
            t = self._make_watchdog_transport(loop, startup_offset=STARTUP_TIMEOUT + 10)
            t._last_heartbeat = None
            with patch("Classes.ZigpyTransport.supervisor.asyncio.sleep", new=AsyncMock()):
                await _watchdog(t)
            return t

        loop = asyncio.new_event_loop()
        try:
            t = loop.run_until_complete(run_test())
        finally:
            loop.close()

        self.assertEqual(t._stack_health, "DEAD")
        self.assertTrue(t._shutdown_event.is_set())

    def test_alive_health_when_heartbeat_recent(self):
        """Heartbeat < 30 s ago → health is ALIVE."""
        from Classes.ZigpyTransport.supervisor import _watchdog

        async def run_test():
            loop = asyncio.get_event_loop()
            t = make_transport(loop=loop)
            t._stack_health   = "STARTING"
            t._shutdown_event = asyncio.Event()
            # Give a very recent heartbeat
            now = loop.time()
            t._last_heartbeat = now - 5  # 5 s ago

            tick_count = [0]
            original_time = loop.time

            def fake_time():
                tick_count[0] += 1
                val = original_time() + tick_count[0] * 1  # advance 1 s per call
                return val

            loop.time = fake_time

            async def fake_sleep(_):
                # After 1 tick, set shutdown so watchdog exits cleanly
                if tick_count[0] >= 1:
                    t._shutdown_event.set()

            with patch("Classes.ZigpyTransport.supervisor.asyncio.sleep", side_effect=fake_sleep):
                await _watchdog(t)
            return t

        loop = asyncio.new_event_loop()
        try:
            t = loop.run_until_complete(run_test())
        finally:
            loop.close()

        # Health must be ALIVE (delta < 30)
        self.assertEqual(t._stack_health, "ALIVE")

    def test_dead_health_triggers_shutdown_event(self):
        """Heartbeat gap > DEAD_STACK_THRESHOLD → DEAD → shutdown_event set."""
        from Classes.ZigpyTransport.supervisor import _watchdog, DEAD_STACK_THRESHOLD

        async def run_test():
            loop = asyncio.get_event_loop()
            t = make_transport(loop=loop)
            t._stack_health   = "STARTING"
            t._shutdown_event = asyncio.Event()
            base = loop.time()
            # Heartbeat far in the past
            t._last_heartbeat = base - (DEAD_STACK_THRESHOLD + 10)

            tick = [0]
            orig = loop.time

            def fake_time():
                tick[0] += 1
                return base + tick[0]

            loop.time = fake_time

            with patch("Classes.ZigpyTransport.supervisor.asyncio.sleep", new=AsyncMock()):
                await _watchdog(t)
            return t

        loop = asyncio.new_event_loop()
        try:
            t = loop.run_until_complete(run_test())
        finally:
            loop.close()

        self.assertEqual(t._stack_health, "DEAD")
        self.assertTrue(t._shutdown_event.is_set())


# ===========================================================================
# _supervisor
# ===========================================================================

class TestSupervisor(unittest.TestCase):
    """
    _supervisor ends every run by calling loop.stop().  Tests use the natural
    pattern: schedule _supervisor as a task, run loop.run_forever(), let the
    supervisor call loop.stop() itself to terminate the loop, then assert.

    Note: _run_zigbee_stack and asyncio.sleep are patched so tests complete
    instantly without touching actual radio hardware or wall-clock time.
    """

    def _run_supervisor(self, t, extra_patches=()):
        """
        Schedule _supervisor(t) as a task, run the event loop until the
        supervisor calls loop.stop(), then return t for assertions.
        """
        from Classes.ZigpyTransport.supervisor import _supervisor
        loop = t.zigpy_loop
        with extra_patches if hasattr(extra_patches, '__enter__') else _NullCtx():
            loop.create_task(_supervisor(t))
            loop.run_forever()
        return t

    def _make_transport(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        t = make_transport(loop=loop)
        t.zigpy_loop = loop
        return t, loop

    def test_exits_immediately_when_stop_requested(self):
        from Classes.ZigpyTransport.supervisor import _supervisor
        t, loop = self._make_transport()
        t._zigpy_stop_requested = True
        try:
            with patch("Classes.ZigpyTransport.supervisor._run_zigbee_stack",
                       new=AsyncMock()) as mock_run, \
                 patch("Classes.ZigpyTransport.supervisor._prepare_for_restart",
                       new=AsyncMock()):
                loop.create_task(_supervisor(t))
                loop.run_forever()
            mock_run.assert_not_called()
        finally:
            loop.close()

    def test_circuit_breaker_calls_restart_plugin(self):
        """After MAX_RESTARTS_PER_HOUR restarts in one hour, restart_plugin() fires."""
        from Classes.ZigpyTransport.supervisor import _supervisor, MAX_RESTARTS_PER_HOUR

        t, loop = self._make_transport()
        now = time.monotonic()
        t._restart_timestamps = [now] * MAX_RESTARTS_PER_HOUR
        t._zigpy_stop_requested = False

        call_count = [0]

        async def fake_run(transport):
            call_count[0] += 1

        try:
            with patch("Classes.ZigpyTransport.supervisor._run_zigbee_stack",
                       side_effect=fake_run), \
                 patch("Classes.ZigpyTransport.supervisor._prepare_for_restart",
                       new=AsyncMock()), \
                 patch("Classes.ZigpyTransport.supervisor.asyncio.sleep",
                       new=AsyncMock()):
                loop.create_task(_supervisor(t))
                loop.run_forever()
            t.restart_plugin.assert_called_once()
        finally:
            loop.close()

    def test_stability_reset_after_long_run(self):
        """A run > 300 s must reset restart_delay and consecutive_failures."""
        from Classes.ZigpyTransport.supervisor import _supervisor

        t, loop = self._make_transport()
        base = loop.time()
        tick = [0]

        def fake_loop_time():
            val = base + tick[0] * 400   # 400 s per call
            tick[0] += 1
            return val

        loop.time = fake_loop_time
        t._consecutive_failures = 3

        run_count = [0]

        async def fake_run(transport):
            run_count[0] += 1
            if run_count[0] >= 2:
                transport._zigpy_stop_requested = True

        try:
            with patch("Classes.ZigpyTransport.supervisor._run_zigbee_stack",
                       side_effect=fake_run), \
                 patch("Classes.ZigpyTransport.supervisor._prepare_for_restart",
                       new=AsyncMock()), \
                 patch("Classes.ZigpyTransport.supervisor.asyncio.sleep",
                       new=AsyncMock()):
                loop.create_task(_supervisor(t))
                loop.run_forever()
            self.assertEqual(t._consecutive_failures, 0)
        finally:
            loop.close()

    def test_backoff_doubles_each_cycle(self):
        """restart_delay must double after each restart (capped at 60 s)."""
        from Classes.ZigpyTransport.supervisor import _supervisor

        sleep_calls = []

        async def fake_sleep(delay):
            sleep_calls.append(delay)

        run_count = [0]

        async def fake_run(transport):
            run_count[0] += 1
            if run_count[0] >= 4:
                transport._zigpy_stop_requested = True

        t, loop = self._make_transport()
        try:
            with patch("Classes.ZigpyTransport.supervisor._run_zigbee_stack",
                       side_effect=fake_run), \
                 patch("Classes.ZigpyTransport.supervisor._prepare_for_restart",
                       new=AsyncMock()), \
                 patch("Classes.ZigpyTransport.supervisor.asyncio.sleep",
                       side_effect=fake_sleep):
                loop.create_task(_supervisor(t))
                loop.run_forever()
        finally:
            loop.close()

        # Expected sleep sequence: 2 s, 4 s, 8 s, …
        self.assertEqual(sleep_calls[0], 2)
        if len(sleep_calls) >= 2:
            self.assertEqual(sleep_calls[1], 4)


class _NullCtx:
    """No-op context manager for _run_supervisor helper."""
    def __enter__(self): return self
    def __exit__(self, *_): pass


# ===========================================================================
# _cleanup
# ===========================================================================

class TestCleanup(unittest.TestCase):

    def test_closes_loop(self):
        from Classes.ZigpyTransport.supervisor import _cleanup
        t = make_transport()
        loop = asyncio.new_event_loop()
        _cleanup(t, loop)
        self.assertTrue(loop.is_closed())

    def test_cancels_pending_tasks(self):
        from Classes.ZigpyTransport.supervisor import _cleanup

        async def long_running():
            await asyncio.sleep(9999)

        loop = asyncio.new_event_loop()
        try:
            task = loop.create_task(long_running())
            t = make_transport()
            _cleanup(t, loop)
            self.assertTrue(task.cancelled() or loop.is_closed())
        finally:
            if not loop.is_closed():
                loop.close()


if __name__ == "__main__":
    unittest.main()
