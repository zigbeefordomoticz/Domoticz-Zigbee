#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the Green Power pairing feed, transport side to feed:

  report_gp_packet   a GPDF zigpy received → 9e03, only while the window is
                     open or from a GPD not commissioned; flags (known,
                     window, encrypted, proxy, rssi); never raises
  report_gp_window   → 9e04
  9e03 / 9e04        encoder → extract_message_infos → decoder → feed entry
"""

import importlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

zigpy_device = pytest.importorskip("zigpy.device")

pytestmark = pytest.mark.skipif(
    not hasattr(zigpy_device, "GreenPowerDevice"), reason="requires zigpy with GreenPowerDevice (>= 2.3.0)"
)

import zigpy.types as t  # noqa: E402

from Classes.ZigpyTransport.greenPower import (  # noqa: E402
    report_gp_packet, report_gp_window)
from Classes.ZigpyTransport.plugin_encoders import (  # noqa: E402
    GP_WINDOW_DISABLED, GP_WINDOW_OPENED)
from Modules.greenPowerFeed import GreenPowerFeed  # noqa: E402

SRC_ID = 0xC220BD02
IEEE_HEX = "00000000c220bd02"


@pytest.fixture
def zgp():
    return importlib.import_module("zigpy.zgp.types")


@pytest.fixture
def app():
    app = MagicMock()
    app.frames = []
    app.callBackFunction = app.frames.append
    app.devices = {}
    app.green_power = SimpleNamespace(is_commissioning=True)
    return app


@pytest.fixture
def decoder():
    sys.modules.pop("Z4D_decoders.z4d_decoder_Green_Power", None)
    return importlib.import_module("Z4D_decoders.z4d_decoder_Green_Power")


@pytest.fixture
def helpers():
    sys.modules.pop("Z4D_decoders.z4d_decoder_helpers", None)
    return importlib.import_module("Z4D_decoders.z4d_decoder_helpers")


@pytest.fixture
def plugin():
    return SimpleNamespace(log=MagicMock(), gp_pairing_feed=GreenPowerFeed())


def gpdf(zgp, command_id, **fields):
    values = dict(
        application_id=zgp.ApplicationID.SrcID, src_id=SRC_ID, command_id=zgp.GPDCommandID(command_id),
        security_level=zgp.SecurityLevel.NoSecurity, security_status=zgp.SecurityStatus.NoSecurity,
        lqi=212, rssi=-64,
    )
    values.update(fields)
    return t.ZigbeeGpPacket(**values)


def commissioned(app, zgp):
    ieee = importlib.import_module("zigpy.zgp.util").synthetic_ieee(SRC_ID)
    app.devices[ieee] = zigpy_device.GreenPowerDevice(app, application_id=zgp.ApplicationID.SrcID, src_id=SRC_ID)


def decoded(helpers, decoder, plugin, frame):
    msg_type, msg_data, msg_lqi = helpers.extract_message_infos(MagicMock(), frame)
    getattr(decoder, "Decode%s" % msg_type.upper())(plugin, None, msg_data, msg_lqi)
    return plugin.gp_pairing_feed.snapshot()["Events"][-1]


# ─── What is reported ────────────────────────────────────────────────────────

def test_commissioning_heard_while_the_window_is_open(app, zgp, helpers, decoder, plugin):
    report_gp_packet(app, gpdf(zgp, 0xE0))

    entry = decoded(helpers, decoder, plugin, app.frames[0])
    assert entry["Event"] == "heard"
    assert entry["IEEE"] == IEEE_HEX
    assert entry["SrcId"] == "0xC220BD02"
    assert (entry["Command"], entry["CommandName"]) == ("e0", "Commissioning")
    assert (entry["Known"], entry["WindowOpen"], entry["Encrypted"]) == (False, True, False)
    assert (entry["Rssi"], entry["Lqi"], entry["Proxy"]) == (-64, 212, None)
    assert entry["Hint"] == "commissioning"


def test_commissioning_heard_while_the_window_is_closed(app, zgp, helpers, decoder, plugin):
    app.green_power.is_commissioning = False

    report_gp_packet(app, gpdf(zgp, 0xE0))

    assert decoded(helpers, decoder, plugin, app.frames[0])["Hint"] == "window-closed"


def test_unpaired_switch_sending_a_normal_command(app, zgp, helpers, decoder, plugin):
    # On the network's channel, but not in its commissioning mode
    app.green_power.is_commissioning = False

    report_gp_packet(app, gpdf(zgp, 0x34))

    entry = decoded(helpers, decoder, plugin, app.frames[0])
    assert entry["CommandName"] == "Level Control Stop"
    assert entry["Hint"] == "not-pairing"


def test_encrypted_frame_shows_no_command(app, zgp, helpers, decoder, plugin):
    report_gp_packet(app, gpdf(zgp, 0x21, security_level=zgp.SecurityLevel.Encrypted,
                               security_status=zgp.SecurityStatus.Unprocessed))

    entry = decoded(helpers, decoder, plugin, app.frames[0])
    assert (entry["Command"], entry["CommandName"], entry["Encrypted"], entry["Hint"]) == (None, None, True, "encrypted")


def test_frame_tunneled_by_a_proxy(app, zgp, helpers, decoder, plugin):
    report_gp_packet(app, gpdf(zgp, 0xE0, gpp_short_addr=t.NWK(0x1A2B), rssi=None, lqi=None))

    entry = decoded(helpers, decoder, plugin, app.frames[0])
    assert (entry["Proxy"], entry["Rssi"], entry["Lqi"]) == ("1a2b", None, 0)


def test_paired_switch_is_reported_while_pairing_only(app, zgp, helpers, decoder, plugin):
    commissioned(app, zgp)

    report_gp_packet(app, gpdf(zgp, 0x21))
    assert decoded(helpers, decoder, plugin, app.frames[0])["Known"] is True

    app.green_power.is_commissioning = False
    report_gp_packet(app, gpdf(zgp, 0x21))
    assert len(app.frames) == 1


def test_payload_is_never_forwarded(app, zgp):
    # A Commissioning payload carries the GPD key
    report_gp_packet(app, gpdf(zgp, 0xE0, payload=t.SerializableBytes(bytes.fromhex("0281f2") + bytes(16))))

    assert "0281f2" not in app.frames[0]


def test_a_failure_is_logged_never_raised(app, zgp):
    app.callBackFunction = MagicMock(side_effect=RuntimeError("queue gone"))

    report_gp_packet(app, gpdf(zgp, 0xE0))

    assert app.log.logging.call_args.args[1] == "Error"


# ─── Window ──────────────────────────────────────────────────────────────────

def test_window_round_trip(app, helpers, decoder, plugin):
    report_gp_window(app, GP_WINDOW_OPENED, 240)

    entry = decoded(helpers, decoder, plugin, app.frames[0])
    assert (entry["Event"], entry["State"], entry["Seconds"]) == ("window", "opened", 240)
    assert plugin.gp_pairing_feed.snapshot()["Window"]["State"] == "opened"


def test_window_not_opened_because_green_power_is_off(app, helpers, decoder, plugin):
    report_gp_window(app, GP_WINDOW_DISABLED, 240)

    assert decoded(helpers, decoder, plugin, app.frames[0])["State"] == "disabled"
