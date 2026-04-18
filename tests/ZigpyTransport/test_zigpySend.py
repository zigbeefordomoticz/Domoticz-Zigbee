#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Classes/ZigpyTransport/zigpySend.py

Covers:
  - properyly_display_data         (formatting helper)
  - log_exception                  (structured logging)
  - check_transport_readiness      (per-radio readiness)
  - cleanup_unused_concurrency_state
  - handle_transport_result        (reachability + ACK/NACK forwarding)
  - push_APS_ACK_NACKto_plugin     (0x8011 frame forwarding)
  - _get_destination               (address-mode routing)
  - send_broadcast_command         (app.broadcast wrapper)
  - send_multicast_command         (app.mrequest wrapper)
"""

import asyncio
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
    t.app         = MagicMock()
    t._radiomodule = "znp"
    t.forwarder_queue = queue.Queue()
    t.statistics  = MagicMock()
    t.statistics._APSAck = 0
    t.statistics._APSNck = 0
    t.statistics._sent   = 0
    t.statistics._ackKO  = 0
    t._concurrent_requests_semaphores_list = {}
    t._currently_waiting_requests_list     = {}
    t._currently_not_reachable             = []
    t.pluginconf  = MagicMock()
    t.pluginconf.pluginConf = {"ForceAPSAck": False}
    return t


# ===========================================================================
# properyly_display_data
# ===========================================================================

class TestProperlyDisplayData(unittest.TestCase):

    def test_returns_string(self):
        from Classes.ZigpyTransport.zigpySend import properyly_display_data
        result = properyly_display_data({"key": 255})
        self.assertIsInstance(result, str)

    def test_formats_known_keys_as_hex(self):
        from Classes.ZigpyTransport.zigpySend import properyly_display_data
        # "Profile" and "Cluster" are formatted as 4-digit hex; "TargetEp" as 2-digit hex
        result = properyly_display_data({"Profile": 0x0104, "TargetEp": 0x01})
        self.assertIn("0104", result)
        self.assertIn("01", result)

    def test_handles_empty_dict(self):
        from Classes.ZigpyTransport.zigpySend import properyly_display_data
        result = properyly_display_data({})
        self.assertIsInstance(result, str)

    def test_non_int_values_are_included(self):
        from Classes.ZigpyTransport.zigpySend import properyly_display_data
        result = properyly_display_data({"name": "hello"})
        self.assertIn("hello", result)


# ===========================================================================
# log_exception
# ===========================================================================

class TestLogException(unittest.TestCase):

    def test_logs_at_error_level(self):
        from Classes.ZigpyTransport.zigpySend import log_exception
        t = make_transport()
        log_exception(t, "DeliveryError", Exception("boom"), "RAW-COMMAND", {})
        calls = t.log.logging.call_args_list
        levels = [c.args[1] for c in calls]
        self.assertIn("Error", levels)

    def test_includes_exception_name_in_output(self):
        from Classes.ZigpyTransport.zigpySend import log_exception
        t = make_transport()
        log_exception(t, "TimeoutError", Exception("timeout"), "SEND", {})
        all_text = " ".join(str(c) for c in t.log.logging.call_args_list)
        self.assertIn("TimeoutError", all_text)


# ===========================================================================
# check_transport_readiness
# ===========================================================================

class TestCheckTransportReadiness(unittest.TestCase):

    def test_ezsp_always_ready(self):
        from Classes.ZigpyTransport.zigpySend import check_transport_readiness
        t = make_transport()
        t._radiomodule = "ezsp"
        self.assertTrue(check_transport_readiness(t))

    def test_deconz_always_ready(self):
        from Classes.ZigpyTransport.zigpySend import check_transport_readiness
        t = make_transport()
        t._radiomodule = "deCONZ"
        self.assertTrue(check_transport_readiness(t))

    def test_blz_always_ready(self):
        from Classes.ZigpyTransport.zigpySend import check_transport_readiness
        t = make_transport()
        t._radiomodule = "blz"
        self.assertTrue(check_transport_readiness(t))

    def test_znp_ready_when_znp_handle_set(self):
        from Classes.ZigpyTransport.zigpySend import check_transport_readiness
        t = make_transport()
        t._radiomodule = "znp"
        t.app._znp = MagicMock()  # non-None
        self.assertTrue(check_transport_readiness(t))

    def test_znp_not_ready_when_znp_handle_none(self):
        from Classes.ZigpyTransport.zigpySend import check_transport_readiness
        t = make_transport()
        t._radiomodule = "znp"
        t.app._znp = None
        self.assertFalse(check_transport_readiness(t))

    def test_unknown_radio_returns_false(self):
        from Classes.ZigpyTransport.zigpySend import check_transport_readiness
        t = make_transport()
        t._radiomodule = "unknown_radio"
        self.assertFalse(check_transport_readiness(t))


# ===========================================================================
# cleanup_unused_concurrency_state
# ===========================================================================

class TestCleanupUnusedConcurrencyState(unittest.TestCase):

    def _make_semaphore(self, value):
        """Return an asyncio.Semaphore created inside a temporary event loop."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self._create_semaphore(value))
        finally:
            loop.close()

    @staticmethod
    async def _create_semaphore(value):
        return asyncio.Semaphore(value)

    def test_removes_idle_entries(self):
        from Classes.ZigpyTransport.zigpySend import (
            cleanup_unused_concurrency_state,
            MAX_CONCURRENT_REQUESTS_PER_DEVICE,
        )
        t = make_transport()
        ieee = "aa:bb:cc:dd:ee:ff:00:11"
        sem = self._make_semaphore(MAX_CONCURRENT_REQUESTS_PER_DEVICE)
        t._concurrent_requests_semaphores_list = {ieee: sem}
        t._currently_waiting_requests_list     = {ieee: 0}
        cleanup_unused_concurrency_state(t)
        self.assertNotIn(ieee, t._concurrent_requests_semaphores_list)

    def test_keeps_entries_with_waiting_requests(self):
        from Classes.ZigpyTransport.zigpySend import (
            cleanup_unused_concurrency_state,
            MAX_CONCURRENT_REQUESTS_PER_DEVICE,
        )
        t = make_transport()
        ieee = "aa:bb:cc:dd:ee:ff:00:11"
        sem = self._make_semaphore(MAX_CONCURRENT_REQUESTS_PER_DEVICE)
        t._concurrent_requests_semaphores_list = {ieee: sem}
        t._currently_waiting_requests_list     = {ieee: 2}  # still waiting
        cleanup_unused_concurrency_state(t)
        self.assertIn(ieee, t._concurrent_requests_semaphores_list)

    def test_empty_state_is_noop(self):
        from Classes.ZigpyTransport.zigpySend import cleanup_unused_concurrency_state
        t = make_transport()
        # Should not raise
        cleanup_unused_concurrency_state(t)
        self.assertEqual(t._concurrent_requests_semaphores_list, {})


# ===========================================================================
# handle_transport_result
# ===========================================================================

class TestHandleTransportResult(unittest.TestCase):

    def test_noop_when_ack_disabled(self):
        from Classes.ZigpyTransport.zigpySend import handle_transport_result
        t = make_transport()
        handle_transport_result(t, "fn", "0006", 1, 0x00,
                                ack_is_disable=True,
                                extended_timeout=False,
                                _ieee="aa:bb", _nwkid="1234", lqi=255)
        self.assertEqual(t.forwarder_queue.qsize(), 0)

    def test_success_removes_from_not_reachable(self):
        from Classes.ZigpyTransport.zigpySend import handle_transport_result
        t = make_transport()
        ieee = "aa:bb:cc:dd:ee:ff:00:11"
        t._currently_not_reachable = [ieee]
        with patch("Classes.ZigpyTransport.zigpySend.push_APS_ACK_NACKto_plugin"):
            handle_transport_result(t, "fn", "0006", 1, 0x00,
                                    ack_is_disable=False,
                                    extended_timeout=False,
                                    _ieee=ieee, _nwkid="1234", lqi=255)
        self.assertNotIn(ieee, t._currently_not_reachable)

    def test_failure_adds_to_not_reachable(self):
        from Classes.ZigpyTransport.zigpySend import handle_transport_result
        t = make_transport()
        ieee = "aa:bb:cc:dd:ee:ff:00:11"
        t._currently_not_reachable = []
        with patch("Classes.ZigpyTransport.zigpySend.push_APS_ACK_NACKto_plugin"):
            handle_transport_result(t, "fn", "0006", 1, 0x01,  # non-zero = failure
                                    ack_is_disable=False,
                                    extended_timeout=False,
                                    _ieee=ieee, _nwkid="1234", lqi=255)
        self.assertIn(ieee, t._currently_not_reachable)

    def test_duplicate_failure_not_duplicated(self):
        from Classes.ZigpyTransport.zigpySend import handle_transport_result
        t = make_transport()
        ieee = "aa:bb:cc:dd:ee:ff:00:11"
        t._currently_not_reachable = [ieee]  # already there
        with patch("Classes.ZigpyTransport.zigpySend.push_APS_ACK_NACKto_plugin"):
            handle_transport_result(t, "fn", "0006", 1, 0x01,
                                    ack_is_disable=False,
                                    extended_timeout=False,
                                    _ieee=ieee, _nwkid="1234", lqi=255)
        self.assertEqual(t._currently_not_reachable.count(ieee), 1)


# ===========================================================================
# push_APS_ACK_NACKto_plugin
# ===========================================================================

class TestPushApsAckNack(unittest.TestCase):

    def test_coordinator_nwkid_is_skipped(self):
        from Classes.ZigpyTransport.zigpySend import push_APS_ACK_NACKto_plugin
        t = make_transport()
        push_APS_ACK_NACKto_plugin(t, "0000", "0006", 1, 0x00, 255)
        self.assertEqual(t.forwarder_queue.qsize(), 0)

    def test_ack_increments_statistics(self):
        from Classes.ZigpyTransport.zigpySend import push_APS_ACK_NACKto_plugin
        t = make_transport()
        with patch("Classes.ZigpyTransport.zigpySend.build_plugin_8011_frame_content",
                   return_value=b"\x80\x11"):
            push_APS_ACK_NACKto_plugin(t, "1234", "0006", 1, 0x00, 255)
        self.assertEqual(t.statistics._APSAck, 1)
        self.assertEqual(t.statistics._APSNck, 0)

    def test_nack_increments_statistics(self):
        from Classes.ZigpyTransport.zigpySend import push_APS_ACK_NACKto_plugin
        t = make_transport()
        with patch("Classes.ZigpyTransport.zigpySend.build_plugin_8011_frame_content",
                   return_value=b"\x80\x11"):
            push_APS_ACK_NACKto_plugin(t, "1234", "0006", 1, 0xA1, 255)
        self.assertEqual(t.statistics._APSNck, 1)
        self.assertEqual(t.statistics._APSAck, 0)

    def test_frame_pushed_to_forwarder_queue(self):
        from Classes.ZigpyTransport.zigpySend import push_APS_ACK_NACKto_plugin
        t = make_transport()
        frame = b"\x80\x11\x00"
        with patch("Classes.ZigpyTransport.zigpySend.build_plugin_8011_frame_content",
                   return_value=frame):
            push_APS_ACK_NACKto_plugin(t, "1234", "0006", 1, 0x00, 255)
        self.assertEqual(t.forwarder_queue.get_nowait(), frame)


# ===========================================================================
# _get_destination
# ===========================================================================

class TestGetDestination(unittest.TestCase):

    def test_broadcast_address_returns_broadcast(self):
        from Classes.ZigpyTransport.zigpySend import _get_destination
        t = make_transport()
        dest, kind = _get_destination(t, "FFFF", 0x02, 0x0104, "0006", 1, 1, 0, b"")
        self.assertEqual(kind, "Broadcast")
        self.assertEqual(dest, 0xFFFF)

    def test_addressmode_01_returns_multicast(self):
        from Classes.ZigpyTransport.zigpySend import _get_destination
        t = make_transport()
        dest, kind = _get_destination(t, "1234", 0x01, 0x0104, "0006", 1, 1, 0, b"")
        self.assertEqual(kind, "Multicast")

    def test_addressmode_02_returns_unicast(self):
        from Classes.ZigpyTransport.zigpySend import _get_destination
        import zigpy.types as zt
        t = make_transport()
        mock_device = MagicMock()
        t.app.get_device = MagicMock(return_value=mock_device)
        dest, kind = _get_destination(t, "1234", 0x02, 0x0104, "0006", 1, 1, 0, b"")
        self.assertEqual(kind, "Unicast")
        self.assertIs(dest, mock_device)

    def test_addressmode_02_device_not_found_returns_none(self):
        from Classes.ZigpyTransport.zigpySend import _get_destination
        t = make_transport()
        t.app.get_device = MagicMock(side_effect=KeyError("unknown nwk"))
        dest, kind = _get_destination(t, "1234", 0x02, 0x0104, "0006", 1, 1, 0, b"")
        self.assertEqual(kind, "Unicast")
        self.assertIsNone(dest)

    def test_invalid_addressmode_returns_none_none(self):
        from Classes.ZigpyTransport.zigpySend import _get_destination
        t = make_transport()
        dest, kind = _get_destination(t, "1234", 0xFF, 0x0104, "0006", 1, 1, 0, b"")
        self.assertIsNone(dest)
        self.assertIsNone(kind)


# ===========================================================================
# send_broadcast_command
# ===========================================================================

class TestSendBroadcastCommand(unittest.TestCase):

    def test_calls_app_broadcast_and_returns_result(self):
        from Classes.ZigpyTransport.zigpySend import send_broadcast_command
        t = make_transport()
        t.app.broadcast = AsyncMock(return_value=(0x00, "ok"))
        with patch("Classes.ZigpyTransport.zigpySend.asyncio.sleep", new=AsyncMock()):
            result, msg = run(send_broadcast_command(t, 0x0104, "0006", 1, 1, 0, b"\x01"))
        self.assertEqual(result, 0x00)
        t.app.broadcast.assert_called_once()


# ===========================================================================
# send_multicast_command
# ===========================================================================

class TestSendMulticastCommand(unittest.TestCase):

    def test_calls_app_mrequest(self):
        from Classes.ZigpyTransport.zigpySend import send_multicast_command
        t = make_transport()
        t.app.mrequest = AsyncMock(return_value=(0x00, ""))
        with patch("Classes.ZigpyTransport.zigpySend.asyncio.sleep", new=AsyncMock()):
            result, msg = run(send_multicast_command(t, "0005", 0x0104, "0006", 1, 0, b"\x01"))
        t.app.mrequest.assert_called_once()
        self.assertEqual(result, 0x00)


if __name__ == "__main__":
    unittest.main()
