#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_send_request: one send per request, whatever its outcome, and what is done of the result.

These hold on the previous _send_and_retry as well: its loop never sent a second time.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import zigpy.config
import zigpy.exceptions
import zigpy.types as t

from Classes.ZigpyTransport import zigpySend

# The previous name lets this file run against the code before the retry loop was removed
send_request = getattr(zigpySend, "_send_request", None) or zigpySend._send_and_retry

IEEE = "00:11:22:33:44:55:66:77"
DEVICE = SimpleNamespace(nwk=t.NWK(0xDB06), ieee=t.EUI64.convert(IEEE), lqi=200)
DELIVERY_ERROR = zigpy.exceptions.DeliveryError


class NcpFailure(Exception):
    """As in bellows.ash: not a zigpy exception."""


def make_transport():
    transport = MagicMock()
    transport.app.config = {zigpy.config.CONF_SOURCE_ROUTING: False}
    transport.app.state.node_info = SimpleNamespace(nwk=t.NWK(0x0000), ieee=DEVICE.ieee)
    transport.app.restarting = False
    transport.pluginconf.pluginConf = {"DelayAfterCommandSent": 0}
    transport._radio_down_requests = 0
    transport._currently_not_reachable = []
    transport.statistics = SimpleNamespace(_ackKO=0, _reTx=0, _TOdata=0, _APSAck=0, _APSNck=0)
    return transport


def send(outcome=None, cluster=0x0006, ack_is_disable=False, transport=None):
    """Returns (number of sends, result, 0x8011 statuses, priorities, transport)"""
    transport = transport or make_transport()
    priorities, statuses = [], []

    async def send_packet(packet):
        priorities.append(packet.priority)
        if outcome:
            raise outcome

    transport.app.send_packet = send_packet
    with patch.object(zigpySend, "build_plugin_8011_frame_content",
                      lambda self, nwkid, cluster, sequence, status, lqi: statuses.append(status)):
        result = asyncio.run(send_request(
            transport, "function", DEVICE, 0x0104, cluster, "db06", 1, 1, 250,
            bytes.fromhex("11fa00"), False, IEEE, ack_is_disable, False, 0))
    return len(priorities), result, statuses, priorities, transport


OUTCOMES = [
    (None, 0x00, 0x00),
    (asyncio.TimeoutError("late"), asyncio.TimeoutError, -1),
    (DELIVERY_ERROR("no"), DELIVERY_ERROR, -1),
    (NcpFailure("0x51"), DELIVERY_ERROR, -1),
    (zigpy.exceptions.ControllerException("not running"), DELIVERY_ERROR, -1),
]


@pytest.mark.parametrize("outcome, expected_result, expected_status", OUTCOMES)
def test_one_send_and_one_status_with_ack(outcome, expected_result, expected_status):
    sends, result, statuses, _, _ = send(outcome)
    assert sends == 1
    assert result == expected_result
    assert statuses == [expected_status]


@pytest.mark.parametrize("outcome, expected_result, expected_status", OUTCOMES)
def test_one_send_and_no_status_without_ack(outcome, expected_result, expected_status):
    sends, result, statuses, _, _ = send(outcome, ack_is_disable=True)
    assert sends == 1
    assert result == expected_result
    assert statuses == []


def test_cancelled_send_reports_nothing():
    sends, result, statuses, _, transport = send(asyncio.CancelledError())
    assert (sends, result, statuses) == (1, -1, [])
    assert transport._currently_not_reachable == []


def test_failure_before_the_send():
    transport = make_transport()
    transport.app.config = {zigpy.config.CONF_SOURCE_ROUTING: True}
    transport.app.build_source_route_to = MagicMock(side_effect=ValueError("no route"))
    sends, result, statuses, _, _ = send(transport=transport)
    assert (sends, result, statuses) == (0, 0xB6, [0xB6])
    assert transport.statistics._ackKO == 1


@pytest.mark.parametrize("cluster, priority", [
    (0x0006, t.PacketPriority.NORMAL),
    (0x0019, t.PacketPriority.LOW),
])
def test_priority(cluster, priority):
    assert send(cluster=cluster)[3] == [priority]
