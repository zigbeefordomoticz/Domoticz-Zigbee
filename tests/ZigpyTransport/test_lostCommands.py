#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Classes/ZigpyTransport/lostCommands.py and its three call sites

Covers:
  - which commands are reported: orders to a device or a group, not reads, replies or network management
  - one Warning per lost order, naming the device
  - nothing at a plugin stop, never an exception
  - _prepare_for_restart, start_zigpy_task, worker_loop
"""

import asyncio
import json
import queue
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def make_transport():
    t = MagicMock()
    t.app = None
    t.zigpy_running = True
    t._zigpy_stop_requested = False
    t.writer_queue = queue.Queue()
    t.ZigpyGetDeviceName = lambda nwkid: {"a1b2": "Thermostat"}.get(nwkid, "0x%s" % nwkid)
    return t


def raw(payload, cluster=0x0006, nwkid=0xA1B2, ep=1, mode=0x02, profile=0x0104, function="some_function"):
    """A RAW-COMMAND as sendData() puts it in the queue."""
    return json.dumps({
        "cmd": "RAW-COMMAND",
        "datas": {
            "Function": function, "Profile": profile, "Cluster": cluster, "TargetNwk": nwkid, "TargetEp": ep,
            "SrcEp": 1, "Sqn": 0, "payload": payload, "AddressMode": mode, "timestamp": 0,
        },
        "NwkId": nwkid, "TimeStamp": 0, "ACKIsDisable": False, "Sqn": 0,
    })


ON = raw("110a01")
SETPOINT = raw("100b02120029d007", cluster=0x0201)
READ = raw("100c000000")


def warnings(transport):
    return [c.args for c in transport.log.logging.call_args_list if c.args[1] == "Warning"]


class TestWhichCommandsAreReported(unittest.TestCase):

    def _reported(self, command):
        from Classes.ZigpyTransport.lostCommands import report_lost_command
        t = make_transport()
        report_lost_command(t, command)
        return len(warnings(t)) == 1

    def test_orders(self):
        for label, command in (
            ("on", ON),
            ("write attribute", SETPOINT),
            ("write attribute undivided", raw("100b03120029d007", cluster=0x0201)),
            ("write attribute no response", raw("100b05120029d007", cluster=0x0201)),
            ("manufacturer specific write", raw("145f110b020040290100", cluster=0x0201)),
            ("manufacturer specific cluster command", raw("055f110be0", cluster=0x0201)),
            ("IAS warning", raw("110a0014b4000000", cluster=0x0502)),
            ("Tuya data point", raw("110a000001020200040000000a", cluster=0xEF00)),
            ("no ack", raw("110a00", mode=0x07)),
            ("group", raw("110a01", mode=0x01)),
        ):
            with self.subTest(label):
                self.assertTrue(self._reported(command))

    def test_not_orders(self):
        for label, command in (
            ("read attribute", READ),
            ("manufacturer specific read", raw("045f110b000040", cluster=0x0201)),
            ("configure reporting", raw("100b06000000200a0058020100")),
            ("read reporting configuration", raw("100b08000000")),
            ("default response", raw("180b0b0100")),
            ("read attribute response to the device", raw("180b0107000023", cluster=0x000A)),
            ("OTA image block response", raw("190b0500", cluster=0x0019)),
            ("Tuya data query", raw("110b03", cluster=0xEF00)),
            ("ZDP request", raw("0011", cluster=0x0005, profile=0x0000)),
            ("ZDP request looking like a cluster command", raw("110a01", cluster=0x0005, profile=0x0000)),
            ("not a raw command", json.dumps({"cmd": "GET-TIME", "datas": None})),
            ("STOP", "STOP"),
        ):
            with self.subTest(label):
                self.assertFalse(self._reported(command))


class TestWarning(unittest.TestCase):

    def _warning(self, command):
        from Classes.ZigpyTransport.lostCommands import report_lost_command
        t = make_transport()
        report_lost_command(t, command)
        return warnings(t)[0]

    def test_names_the_device(self):
        _, _, message, nwkid = self._warning(raw("110a01", ep=2, function="zcl_onoff_on"))
        self.assertIn("Thermostat (a1b2/02)", message)
        self.assertIn("zcl_onoff_on", message)
        self.assertIn("Cluster: 0006", message)
        self.assertEqual(nwkid, "a1b2")

    def test_device_without_a_name(self):
        self.assertIn("0x00ff (00ff/01)", self._warning(raw("110a01", nwkid=0x00FF))[2])

    def test_group(self):
        _, _, message, nwkid = self._warning(raw("110a01", nwkid=0x0003, mode=0x01))
        self.assertIn("group 0003", message)
        self.assertEqual(nwkid, "0003")


class TestNeverInTheWay(unittest.TestCase):

    def test_nothing_at_a_plugin_stop(self):
        from Classes.ZigpyTransport.lostCommands import report_lost_command
        t = make_transport()
        t._zigpy_stop_requested = True
        report_lost_command(t, ON)
        self.assertEqual(warnings(t), [])

    def test_unreadable_commands_do_not_raise(self):
        from Classes.ZigpyTransport.lostCommands import report_lost_command
        t = make_transport()
        for command in ("not json", "{}", "[]", None, raw(""), raw("zz"), raw("11"), raw(None)):
            with self.subTest(command):
                report_lost_command(t, command)

    def test_no_queue_yet(self):
        from Classes.ZigpyTransport.lostCommands import report_lost_commands
        t = make_transport()
        t.writer_queue = None
        report_lost_commands(t)
        self.assertEqual(warnings(t), [])

    def test_a_bad_command_does_not_hide_the_next_one(self):
        from Classes.ZigpyTransport.lostCommands import report_lost_commands
        t = make_transport()
        for command in ("not json", "STOP", ON):
            t.writer_queue.put_nowait(command)
        report_lost_commands(t)
        self.assertEqual(len(warnings(t)), 1)
        self.assertTrue(t.writer_queue.empty())


class TestCallSites(unittest.TestCase):

    def test_prepare_for_restart(self):
        from Classes.ZigpyTransport.supervisor import _prepare_for_restart
        t = make_transport()
        old_queue = t.writer_queue
        for command in ("STOP", ON, READ, SETPOINT):
            t.writer_queue.put_nowait(command)

        run(_prepare_for_restart(t))

        self.assertEqual(len(warnings(t)), 2)
        self.assertIsNot(t.writer_queue, old_queue)
        self.assertTrue(t.writer_queue.empty())

    def test_start_zigpy_task_while_the_radio_starts(self):
        from Classes.ZigpyTransport.radioStart import start_zigpy_task
        t = make_transport()
        t.pluginconf.pluginConf = {"channel": "15", "extendedPANID": "0x1234567890ABCDEF"}
        queue_seen_by_the_worker = []

        async def radio_start(transport, *args, **kwargs):
            transport.writer_queue.put_nowait(ON)

        async def worker_loop(transport):
            queue_seen_by_the_worker.append(transport.writer_queue.qsize())

        with patch("Classes.ZigpyTransport.radioStart.radio_start", side_effect=radio_start), \
             patch("Classes.ZigpyTransport.radioStart.worker_loop", side_effect=worker_loop), \
             patch("Classes.ZigpyTransport.radioStart.asyncio.sleep", new=AsyncMock()):
            run(start_zigpy_task(t, channel=0, extended_pan_id=0))

        self.assertEqual(len(warnings(t)), 1)
        self.assertEqual(queue_seen_by_the_worker, [0])  # not replayed

    def test_worker_loop_stopped_with_a_command_in_hand(self):
        from Classes.ZigpyTransport import workerLoop
        t = make_transport()

        async def next_command(transport):
            transport.zigpy_running = False  # connection_lost() meanwhile
            return ON

        with patch.object(workerLoop, "get_next_command", side_effect=next_command), \
             patch.object(workerLoop, "process_incoming_command", new=AsyncMock()) as process:
            run(workerLoop.worker_loop(t))

        process.assert_not_called()
        self.assertEqual(len(warnings(t)), 1)


if __name__ == "__main__":
    unittest.main()
