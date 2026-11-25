#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zigpy_request when the link to the coordinator goes down.

All the requests pending at that time fail together. They used to log one Error each, with
the full traceback, and a single outage could fill the 20 entries of the error history.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import zigpy.config
import zigpy.exceptions
import zigpy.types as t

from Classes.ZigpyTransport import zigpySend


class NcpFailure(Exception):
    """As in bellows.ash: not a zigpy exception."""


class ControllerError(zigpy.exceptions.ControllerException):
    """As in bellows.exception."""


DEVICE = SimpleNamespace(nwk=t.NWK(0xDB06), ieee=t.EUI64.convert("00:11:22:33:44:55:66:77"), lqi=200)


class Transport:
    def __init__(self):
        self.lines = []
        self.log = SimpleNamespace(logging=self._logging)
        self._radio_down_requests = 0
        self.new_app()

    def _logging(self, module, level, message, nwkid=None, context=None):
        self.lines.append((level, message, nwkid, context))

    def new_app(self):
        self.app = MagicMock()
        self.app.restarting = False
        self.app.config = {zigpy.config.CONF_SOURCE_ROUTING: False}
        self.app.state.node_info = SimpleNamespace(nwk=t.NWK(0x0000), ieee=DEVICE.ieee)

    def send(self, exception=None):
        async def send_packet(packet):
            if exception:
                raise exception
        self.app.send_packet = send_packet
        return asyncio.run(zigpySend.zigpy_request(
            self, DEVICE, 0x0104, 0x0006, 1, 1, 250, bytes.fromhex("11fa00")))

    def at(self, level):
        return [line for line in self.lines if line[0] == level]


def test_one_error_per_outage():
    transport = Transport()
    transport.app.restarting = True  # set by connection_lost()
    transport.send(NcpFailure("ERROR_EXCEEDED_MAXIMUM_ACK_TIMEOUT_COUNT"))
    for _ in range(13):
        transport.send(ControllerError("ApplicationController is not running"))

    (error,) = transport.at("Error")
    _, message, nwkid, context = error
    assert "db06" in message and "NcpFailure" in message
    assert "Traceback" not in message
    assert nwkid == "db06"
    assert context["Error code"] == "ZIGPY-SEND-01"


def test_details_of_each_request_stay_in_debug():
    transport = Transport()
    transport.app.restarting = True
    transport.send(NcpFailure("x"))
    transport.send(ControllerError("y"))
    details = [line for line in transport.at("Debug") if "Error sending packet" in line[1]]
    assert len(details) == 2
    assert all("Traceback" in line[1] for line in details)


def test_controller_error_alone_is_a_radio_down():
    transport = Transport()
    transport.send(ControllerError("ApplicationController is not running"))
    transport.send(ControllerError("ApplicationController is not running"))
    assert len(transport.at("Error")) == 1


def test_outage_reported_again_after_the_link_is_back():
    transport = Transport()
    transport.send(ControllerError("down"))
    transport.send(ControllerError("down"))
    transport.new_app()  # supervisor restart
    transport.send()

    (status,) = transport.at("Status")
    assert "2 request(s)" in status[1]
    assert transport._radio_down_requests == 0

    transport.send(ControllerError("down"))
    assert len(transport.at("Error")) == 2


def test_no_status_line_without_an_outage():
    transport = Transport()
    transport.send()
    assert not transport.at("Status")


def test_unexpected_failure_with_the_radio_up_is_still_an_error_each_time():
    transport = Transport()
    transport.send(RuntimeError("boom"))
    transport.send(RuntimeError("boom"))
    errors = transport.at("Error")
    assert len(errors) == 2
    assert all("Traceback" in line[1] for line in errors)
    assert transport._radio_down_requests == 0


@pytest.mark.parametrize("exception", [NcpFailure("x"), ControllerError("y")])
def test_result_is_unchanged(exception):
    transport = Transport()
    transport.app.restarting = True
    assert transport.send(exception) == (zigpy.exceptions.DeliveryError, f"ZCL FAILURE: {exception}")


@pytest.mark.parametrize("exception", [zigpy.exceptions.DeliveryError("no"), asyncio.TimeoutError("late")])
def test_device_failures_are_not_a_radio_down(exception):
    transport = Transport()
    transport.send(exception)
    assert not transport.at("Error")
    assert transport._radio_down_requests == 0


def test_app_replaced_during_the_send():
    transport = Transport()

    async def send_packet(packet):
        transport.app = None  # _prepare_for_restart()
        raise NcpFailure("x")

    transport.app.restarting = True
    transport.app.send_packet = send_packet
    asyncio.run(zigpySend.zigpy_request(
        transport, DEVICE, 0x0104, 0x0006, 1, 1, 250, bytes.fromhex("11fa00")))
    assert len(transport.at("Error")) == 1
