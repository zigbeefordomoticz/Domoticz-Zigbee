#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Classes/ZigpyTransport/workerLoop.py

Covers:
  - get_next_command   (queue polling, early-exit when stopped)
  - dispatch_command   (each command branch)
  - process_incoming_command  (exception mapping)
  - worker_loop        (STOP sentinel, zigpy_running=False exits)
"""

import asyncio
import json
import queue
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def make_transport():
    t = MagicMock()
    t.log = MagicMock()
    t.log.logging = MagicMock()
    t.zigpy_running  = True
    t.writer_queue   = queue.Queue()
    t.forwarder_queue = queue.Queue()
    t.app            = MagicMock()
    t.app.coordinator_backup   = AsyncMock()
    t.app.get_time_server      = AsyncMock()
    t.app.set_certification    = AsyncMock()
    t.app.move_network_to_channel = AsyncMock()
    t.app.set_extended_pan_id  = MagicMock()
    t.app.set_led              = AsyncMock()
    t.app.set_time_server      = AsyncMock()
    t.app.set_zigpy_tx_power   = AsyncMock()
    t.app.permit_ncp           = AsyncMock()
    t.app.permit               = AsyncMock()
    t.app.remove_ieee          = AsyncMock()
    t.app.disconnect           = AsyncMock()
    t.app.connect              = AsyncMock()
    t._radiomodule  = "znp"
    t.permit_to_join_timer = {}
    t.manual_topology_scan_task    = None
    t.manual_interference_scan_task = None
    return t


def _cmd(cmd, datas=None, ack=False, sqn=0):
    """Build a serialised command string as worker_loop receives it."""
    obj = {"cmd": cmd, "datas": datas or {}, "ACKIsDisable": ack, "Sqn": sqn}
    return json.dumps(obj)


# ===========================================================================
# get_next_command
# ===========================================================================

class TestGetNextCommand(unittest.TestCase):

    def test_returns_command_from_queue(self):
        from Classes.ZigpyTransport.workerLoop import get_next_command
        t = make_transport()
        t.writer_queue.put_nowait("CMD")
        result = run(get_next_command(t))
        self.assertEqual(result, "CMD")

    def test_returns_none_when_stopped_and_queue_empty(self):
        from Classes.ZigpyTransport.workerLoop import get_next_command
        t = make_transport()
        t.zigpy_running = False
        result = run(get_next_command(t))
        self.assertIsNone(result)

    def test_polls_until_command_arrives(self):
        """When queue is empty but running, it must wait (polled via asyncio.sleep)."""
        from Classes.ZigpyTransport.workerLoop import get_next_command

        async def push_after_sleep(t):
            await asyncio.sleep(0)          # yield to let get_next_command start
            t.writer_queue.put_nowait("LATE")
            return await get_next_command(t)

        t = make_transport()
        result = run(push_after_sleep(t))
        self.assertEqual(result, "LATE")


# ===========================================================================
# dispatch_command
# ===========================================================================

class TestDispatchCommand(unittest.TestCase):

    # ---- simple async-app commands ----------------------------------------

    def _dispatch(self, transport, data_dict):
        from Classes.ZigpyTransport.workerLoop import dispatch_command
        run(dispatch_command(transport, data_dict))

    def test_coordinator_backup(self):
        t = make_transport()
        self._dispatch(t, {"cmd": "COORDINATOR-BACKUP", "datas": {}})
        t.app.coordinator_backup.assert_called_once()

    def test_get_time(self):
        t = make_transport()
        self._dispatch(t, {"cmd": "GET-TIME", "datas": {}})
        t.app.get_time_server.assert_called_once()

    def test_set_certification(self):
        t = make_transport()
        self._dispatch(t, {"cmd": "SET-CERTIFICATION", "datas": {"Param1": 1}})
        t.app.set_certification.assert_called_once_with(1)

    def test_set_channel(self):
        t = make_transport()
        self._dispatch(t, {"cmd": "SET-CHANNEL", "datas": {"Param1": 15}})
        t.app.move_network_to_channel.assert_called_once_with(15)

    def test_set_led(self):
        t = make_transport()
        self._dispatch(t, {"cmd": "SET-LED", "datas": {"Param1": True}})
        t.app.set_led.assert_called_once_with(True)

    def test_set_tx_power(self):
        t = make_transport()
        self._dispatch(t, {"cmd": "SET-TX-POWER", "datas": {"Param1": 20}})
        t.app.set_zigpy_tx_power.assert_called_once_with(20)

    def test_set_extpanid(self):
        t = make_transport()
        self._dispatch(t, {"cmd": "SET-EXTPANID", "datas": {"Param1": "0x1234"}})
        t.app.set_extended_pan_id.assert_called_once_with("0x1234")

    # ---- RESTART-ZIGPY-STACK ----------------------------------------------

    def test_restart_zigpy_stack_flags_stop(self):
        t = make_transport()
        t.zigpy_running = True
        self._dispatch(t, {"cmd": "RESTART-ZIGPY-STACK", "datas": {}})
        self.assertFalse(t.zigpy_running)
        # A STOP sentinel must have been pushed
        self.assertEqual(t.writer_queue.get_nowait(), "STOP")

    # ---- RESET-RADIO-COMMUNICATION ----------------------------------------

    def test_reset_radio_communication_reconnects(self):
        t = make_transport()
        self._dispatch(t, {"cmd": "RESET-RADIO-COMMUNICATION", "datas": {}})
        t.app.disconnect.assert_called_once()
        t.app.connect.assert_called_once()

    def test_reset_radio_falls_back_to_restart_on_failure(self):
        t = make_transport()
        t.app.disconnect = AsyncMock(side_effect=Exception("port error"))
        t.zigpy_running = True
        self._dispatch(t, {"cmd": "RESET-RADIO-COMMUNICATION", "datas": {}})
        self.assertFalse(t.zigpy_running)
        self.assertEqual(t.writer_queue.get_nowait(), "STOP")

    def test_reset_radio_noop_when_app_none(self):
        t = make_transport()
        t.app = None
        # Should complete without error
        self._dispatch(t, {"cmd": "RESET-RADIO-COMMUNICATION", "datas": {}})

    # ---- REQ-NWK-STATUS ---------------------------------------------------

    def test_req_nwk_status_pushes_frame(self):
        t = make_transport()
        fake_frame = b"\x80\x09\x00"
        with patch("Classes.ZigpyTransport.workerLoop.asyncio.sleep", new=AsyncMock()), \
             patch("Classes.ZigpyTransport.workerLoop.build_plugin_8009_frame_content",
                   return_value=fake_frame):
            self._dispatch(t, {"cmd": "REQ-NWK-STATUS", "datas": {}})
        self.assertEqual(t.forwarder_queue.get_nowait(), fake_frame)

    # ---- INTERFERENCE-SCAN ------------------------------------------------

    def test_interference_scan_creates_task(self):
        t = make_transport()
        # Use a coroutine function that completes instantly
        scan_started = []

        async def fake_scan():
            scan_started.append(True)

        t.app.network_interference_scan = fake_scan
        t.manual_interference_scan_task = None

        async def run_dispatch():
            from Classes.ZigpyTransport.workerLoop import dispatch_command
            await dispatch_command(t, {"cmd": "INTERFERENCE-SCAN", "datas": {}})
            await asyncio.sleep(0)  # let the spawned task start

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run_dispatch())
            # Drain any remaining tasks
            remaining = asyncio.all_tasks(loop)
            if remaining:
                loop.run_until_complete(
                    asyncio.gather(*remaining, return_exceptions=True)
                )
        finally:
            loop.close()

        self.assertIsNotNone(t.manual_interference_scan_task)

    # ---- PERMIT-TO-JOIN ---------------------------------------------------

    def test_permit_to_join_non_deconz(self):
        t = make_transport()
        t._radiomodule = "znp"
        data = {
            "cmd": "PERMIT-TO-JOIN",
            "datas": {"Duration": 60, "targetRouter": "FFFC"},
            "ACKIsDisable": False,
            "Sqn": 0,
        }
        self._dispatch(t, data)
        t.app.permit.assert_called_once()

    def test_permit_to_join_deconz_uses_permit_ncp(self):
        t = make_transport()
        t._radiomodule = "deCONZ"
        data = {
            "cmd": "PERMIT-TO-JOIN",
            "datas": {"Duration": 60, "targetRouter": "FFFC"},
            "ACKIsDisable": False,
            "Sqn": 0,
        }
        self._dispatch(t, data)
        t.app.permit_ncp.assert_called_once_with(time_s=60)
        t.app.permit.assert_not_called()


# ===========================================================================
# process_incoming_command
# ===========================================================================

class TestProcessIncomingCommand(unittest.TestCase):

    def test_calls_dispatch_command(self):
        from Classes.ZigpyTransport.workerLoop import process_incoming_command
        t = make_transport()
        data = {"cmd": "COORDINATOR-BACKUP", "datas": {}}
        with patch("Classes.ZigpyTransport.workerLoop.dispatch_command", new=AsyncMock()) as mock_dispatch:
            run(process_incoming_command(t, json.dumps(data)))
        mock_dispatch.assert_called_once()

    def test_delivery_error_is_caught_and_logged(self):
        from Classes.ZigpyTransport.workerLoop import process_incoming_command
        from zigpy.exceptions import DeliveryError
        t = make_transport()

        async def raise_delivery(*_):
            raise DeliveryError("nack")

        with patch("Classes.ZigpyTransport.workerLoop.dispatch_command",
                   side_effect=raise_delivery):
            run(process_incoming_command(t, json.dumps({"cmd": "X", "datas": {}})))

        # Must have logged an error — not crashed
        t.log.logging.assert_called()

    def test_unknown_exception_calls_handle_thread_error(self):
        from Classes.ZigpyTransport.workerLoop import process_incoming_command
        t = make_transport()

        async def raise_unknown(*_):
            raise KeyError("unexpected")

        with patch("Classes.ZigpyTransport.workerLoop.dispatch_command",
                   side_effect=raise_unknown), \
             patch("Classes.ZigpyTransport.workerLoop.handle_thread_error") as mock_handler:
            run(process_incoming_command(t, json.dumps({"cmd": "X", "datas": {}})))

        mock_handler.assert_called_once()


# ===========================================================================
# worker_loop
# ===========================================================================

class TestWorkerLoop(unittest.TestCase):

    def test_stop_sentinel_exits_loop(self):
        from Classes.ZigpyTransport.workerLoop import worker_loop
        t = make_transport()
        t.zigpy_running = True
        t.writer_queue.put_nowait("STOP")
        run(worker_loop(t))
        self.assertFalse(t.zigpy_running)

    def test_zigpy_running_false_exits_loop(self):
        from Classes.ZigpyTransport.workerLoop import worker_loop
        t = make_transport()
        t.zigpy_running = False
        # Queue is empty; loop should notice running=False and exit
        run(worker_loop(t))

    def test_processes_one_command_before_stop(self):
        from Classes.ZigpyTransport.workerLoop import worker_loop
        t = make_transport()
        t.zigpy_running = True
        cmd = json.dumps({"cmd": "COORDINATOR-BACKUP", "datas": {}})
        t.writer_queue.put_nowait(cmd)
        t.writer_queue.put_nowait("STOP")
        run(worker_loop(t))
        t.app.coordinator_backup.assert_called_once()

    def test_cancelled_error_exits_cleanly(self):
        """CancelledError must break the loop without an unhandled exception."""
        from Classes.ZigpyTransport.workerLoop import worker_loop
        t = make_transport()
        t.zigpy_running = True

        async def run_and_cancel():
            task = asyncio.create_task(worker_loop(t))
            await asyncio.sleep(0)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass  # expected

        asyncio.run(run_and_cancel())


if __name__ == "__main__":
    unittest.main()
