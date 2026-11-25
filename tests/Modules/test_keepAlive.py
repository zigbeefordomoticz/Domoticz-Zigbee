#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the Keep-Alive cluster (0x0025) server in Modules/keepAlive.py, against
ZCL revision 8 section 3.18 (issue #2324: the reads were never answered).

Coverage:
  - the whole request is answered by one Read Attributes Response, with the sequence
    number of the request
  - TCKeepAliveBase is a uint8 of 10 minutes, TCKeepAliveJitter a uint16 of 300 seconds
  - an unsupported attribute gets a status-only record and does not drop the others
  - a repeated sequence number is answered again
  - the answer goes to the requesting endpoint, with the device's ack setting
"""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest

ZIGATE_EP = "01"
NWKID = "1234"
EP = "02"

BASE_RECORD = "0000" + "00" + "20" + "0a"
JITTER_RECORD = "0100" + "00" + "21" + "2c01"


def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


@pytest.fixture
def ka():
    """Import the real Modules.keepAlive with its plugin dependencies stubbed out."""
    raw_aps = MagicMock(name="raw_APS_request")
    ack = MagicMock(name="is_ack_tobe_disabled", return_value=False)
    stubs = {
        "Modules.sendZigateCommand": _make_stub("Modules.sendZigateCommand", raw_APS_request=raw_aps),
        "Modules.tools": _make_stub("Modules.tools", is_ack_tobe_disabled=ack),
        "Modules.zigateConsts": _make_stub("Modules.zigateConsts", ZIGATE_EP=ZIGATE_EP),
    }
    saved = {name: sys.modules.get(name) for name in [*stubs, "Modules.keepAlive"]}
    sys.modules.update(stubs)
    sys.modules.pop("Modules.keepAlive", None)
    module = importlib.import_module("Modules.keepAlive")
    module._raw_aps = raw_aps
    module._ack = ack

    yield module

    for name, old in saved.items():
        if old is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old


def _request(ka, attributes, sqn="05"):
    plugin = MagicMock()
    plugin.ListOfDevices = {NWKID: {"Model": "ZBMINIL2"}}
    ka.keep_alive_read_attribute_request(plugin, NWKID, EP, sqn, "0025", attributes)
    return ka._raw_aps.call_args


def test_both_attributes_in_one_response(ka):
    args, kwargs = _request(ka, "00000001")

    ka._raw_aps.assert_called_once()
    assert args[1:5] == (NWKID, EP, "0025", "0104")
    assert args[5] == "18" + "05" + "01" + BASE_RECORD + JITTER_RECORD
    assert kwargs["zigate_ep"] == ZIGATE_EP


@pytest.mark.parametrize("attribute, record", [("0000", BASE_RECORD), ("0001", JITTER_RECORD)])
def test_one_attribute(ka, attribute, record):
    args, _ = _request(ka, attribute, sqn="a7")
    assert args[5] == "18" + "a7" + "01" + record


def test_unsupported_attribute_does_not_drop_the_others(ka):
    args, _ = _request(ka, "0000fffd0001")
    assert args[5] == "180501" + BASE_RECORD + "fdff" + "86" + JITTER_RECORD


def test_a_repeated_sequence_number_is_answered_again(ka):
    _request(ka, "0000")
    _request(ka, "0000")
    assert ka._raw_aps.call_count == 2


@pytest.mark.parametrize("ack_disabled", [True, False])
def test_ack_setting_of_the_device(ka, ack_disabled):
    ka._ack.return_value = ack_disabled
    _, kwargs = _request(ka, "0000")
    assert kwargs["ackIsDisabled"] is ack_disabled
