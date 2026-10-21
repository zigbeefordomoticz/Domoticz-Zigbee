#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Classes/ZigpyTransport/greenPower.py, the 9exx frame builders in
plugin_encoders.py and their decoders in Z4D_decoders/z4d_decoder_Green_Power.py.

Covers:
  GreenPowerListener          – zigpy events on a real GreenPowerDevice → 9exx frames,
                                Zigbee devices ignored, handler errors logged
  register_green_power_listener – only with zigpy Green Power, only once
  9e00 / 9e01 / 9e02          – encoder → extract_message_infos → decoder round trip
  loggable_plugin_frame       – the 9e00 payload (security key) is never logged
"""

import importlib
import json
import sys
from unittest.mock import MagicMock

import pytest

zigpy_device = pytest.importorskip("zigpy.device")

pytestmark = pytest.mark.skipif(
    not hasattr(zigpy_device, "GreenPowerDevice"), reason="requires zigpy with GreenPowerDevice (>= 2.3.0)"
)

import zigpy.types as t  # noqa: E402

from Classes.ZigpyTransport.greenPower import (  # noqa: E402
    GreenPowerListener, register_green_power_listener)
from Zigbee.encoder_tools import loggable_plugin_frame  # noqa: E402

SRC_ID = 0x0155A3B2
IEEE_HEX = "000000000155a3b2"  # synthetic IEEE: SrcID + GP marker
ALIAS_HEX = "a3b2"
KEY = bytes(range(16))


@pytest.fixture
def gp_types():
    return importlib.import_module("zigpy.zgp.types")


@pytest.fixture
def app():
    app = MagicMock()
    app.frames = []
    app.callBackFunction = app.frames.append
    return app


@pytest.fixture
def decoder():
    sys.modules.pop("Z4D_decoders.z4d_decoder_Green_Power", None)
    return importlib.import_module("Z4D_decoders.z4d_decoder_Green_Power")


@pytest.fixture
def helpers():
    sys.modules.pop("Z4D_decoders.z4d_decoder_helpers", None)
    return importlib.import_module("Z4D_decoders.z4d_decoder_helpers")


def make_gpd(app, gp_types, frame_counter=1234, lqi=180):
    dev = zigpy_device.GreenPowerDevice(app, application_id=gp_types.ApplicationID.SrcID, src_id=SRC_ID)
    dev.device_id = gp_types.DeviceID.OnOffSwitch
    dev.commands = [gp_types.GPDCommandID(0x20), gp_types.GPDCommandID(0x21)]
    dev.security_level = gp_types.SecurityLevel.Encrypted
    dev.security_key_type = gp_types.SecurityKeyType.IndividualKey
    dev.security_key = t.KeyData(KEY)
    dev.frame_counter = frame_counter
    dev.lqi = lqi
    return dev


def press(dev, command_id=0x20, endpoint_id=None, command=None):
    dev.emit("gp_command_received", zigpy_device.GreenPowerCommandReceived(
        device_ieee=str(dev.ieee), endpoint_id=endpoint_id, command_id=command_id, command=command))


def msg_types(app):
    return [frame[2:6] for frame in app.frames]


def logged_text(app):
    return " ".join(str(a) for c in app.log.logging.call_args_list for a in c.args)


# ─── Listener ────────────────────────────────────────────────────────────────

class TestListener:

    def test_new_device_sends_its_record_then_its_commands(self, app, gp_types):
        listener = GreenPowerListener(app)
        dev = make_gpd(app, gp_types)

        listener.device_initialized(dev)
        press(dev)

        assert msg_types(app) == ["9e00", "9e01"]

    def test_removed_device_commands_are_no_longer_sent(self, app, gp_types):
        listener = GreenPowerListener(app)
        dev = make_gpd(app, gp_types)
        listener.device_initialized(dev)

        listener.device_removed(dev)
        press(dev)

        assert msg_types(app) == ["9e00", "9e02"]

    def test_recommissioned_device_replaces_the_old_object(self, app, gp_types):
        listener = GreenPowerListener(app)
        old = make_gpd(app, gp_types)
        listener.device_initialized(old)
        new = make_gpd(app, gp_types, frame_counter=5000)

        listener.device_reinterviewed(new)
        press(old)
        press(new)

        assert msg_types(app) == ["9e00", "9e00", "9e01"]
        # No command payload: the frame counter of the new object ends the frame data
        assert app.frames[2][12:-4].endswith("%08x" % 5000)

    def test_zigbee_devices_are_ignored(self, app):
        listener = GreenPowerListener(app)
        dev = zigpy_device.ZigbeeDevice(app, t.EUI64.convert("01:02:03:04:05:06:07:08"), 0x1234)

        listener.device_initialized(dev)
        listener.device_reinterviewed(dev)
        listener.device_removed(dev)

        assert app.frames == []

    def test_handler_error_is_logged_not_raised(self, app, gp_types):
        listener = GreenPowerListener(app)
        app.callBackFunction = MagicMock(side_effect=RuntimeError("queue gone"))

        listener.device_initialized(make_gpd(app, gp_types))

        assert any(c.args[1] == "Error" and "queue gone" in c.args[2] for c in app.log.logging.call_args_list)

    def test_record_key_is_not_logged(self, app, gp_types):
        listener = GreenPowerListener(app)
        listener.device_initialized(make_gpd(app, gp_types))

        assert KEY.hex() not in logged_text(app)


class TestRegistration:

    def test_not_registered_without_green_power(self):
        app = MagicMock(spec=["add_listener", "log"])

        register_green_power_listener(app)

        app.add_listener.assert_not_called()

    def test_registered_once(self, app):
        app.z4d_gp_listener = None

        register_green_power_listener(app)
        register_green_power_listener(app)

        app.add_listener.assert_called_once_with(app.z4d_gp_listener)
        assert isinstance(app.z4d_gp_listener, GreenPowerListener)


# ─── Frames: encoder → plugin decoder ────────────────────────────────────────

class TestFrames:

    def test_9e00_record_round_trip(self, app, gp_types, helpers, decoder):
        GreenPowerListener(app).device_initialized(make_gpd(app, gp_types))

        msg_type, msg_data, msg_lqi = helpers.extract_message_infos(MagicMock(), app.frames[0])
        record = decoder.decode_gp_record(msg_data)

        assert (msg_type, msg_lqi) == ("9e00", "b4")
        assert record["v"] == decoder.GP_FRAME_VERSION
        assert record["ieee"] == IEEE_HEX
        assert record["nwk"] == ALIAS_HEX
        assert record["application_id"] == 0
        assert record["src_id"] == SRC_ID
        assert record["device_id"] == int(gp_types.DeviceID.OnOffSwitch)
        assert record["commands"] == [0x20, 0x21]
        assert record["security_level"] == int(gp_types.SecurityLevel.Encrypted)
        assert record["security_key_type"] == int(gp_types.SecurityKeyType.IndividualKey)
        assert record["security_key"] == KEY.hex()
        assert record["frame_counter"] == 1234
        assert record["recommissioned"] is False

    def test_9e01_command_round_trip(self, app, gp_types, helpers, decoder):
        dev = make_gpd(app, gp_types, frame_counter=0x01020304)
        listener = GreenPowerListener(app)
        listener.device_initialized(dev)
        command = t.uint8_t(0x7F)

        press(dev, command_id=0x22, endpoint_id=None, command=command)

        msg_type, msg_data, msg_lqi = helpers.extract_message_infos(MagicMock(), app.frames[1])
        assert msg_type == "9e01"
        assert decoder.decode_gp_command(msg_data) == {
            "ieee": IEEE_HEX, "nwk": ALIAS_HEX, "endpoint": "00", "command_id": "22",
            "frame_counter": 0x01020304, "payload": "7f",
        }

    def test_9e02_removed_round_trip(self, app, gp_types, helpers):
        dev = make_gpd(app, gp_types)
        GreenPowerListener(app).device_removed(dev)

        msg_type, msg_data, _ = helpers.extract_message_infos(MagicMock(), app.frames[0])

        assert (msg_type, msg_data) == ("9e02", IEEE_HEX + ALIAS_HEX)

    def test_decoder_logs_no_key(self, app, gp_types, helpers, decoder):
        GreenPowerListener(app).device_initialized(make_gpd(app, gp_types))
        _, msg_data, msg_lqi = helpers.extract_message_infos(MagicMock(), app.frames[0])
        plugin = MagicMock()

        decoder.Decode9E00(plugin, {}, msg_data, msg_lqi)

        text = " ".join(str(a) for c in plugin.log.logging.call_args_list for a in c.args)
        assert "commissioned" in text and IEEE_HEX in text
        assert KEY.hex() not in text

    def test_decoder_rejects_unknown_record_version(self, decoder):
        plugin = MagicMock()
        msg_data = json.dumps({"v": 99}).encode().hex()

        decoder.Decode9E00(plugin, {}, msg_data, "00")

        assert plugin.log.logging.call_args.args[1] == "Error"


# ─── Log masking ─────────────────────────────────────────────────────────────

class TestLoggableFrame:

    def test_9e00_payload_masked(self, app, gp_types):
        GreenPowerListener(app).device_initialized(make_gpd(app, gp_types))
        frame = app.frames[0]
        # In the frame the key is hex text inside hex-encoded JSON
        key_in_frame = KEY.hex().encode().hex()
        assert key_in_frame in frame

        logged = loggable_plugin_frame(frame)

        assert logged.startswith("019e00") and logged.endswith("<masked>")
        assert key_in_frame not in logged

    def test_other_frames_unchanged(self):
        assert loggable_plugin_frame("019e010004ffabcd0003") == "019e010004ffabcd0003"
        assert loggable_plugin_frame("STOP") == "STOP"
