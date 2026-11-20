#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the Green Power device store fed by the 9exx decoders
(Z4D_decoders/z4d_decoder_Green_Power.py, Modules/greenPowerStore.py).

Covers:
  9e00  commissioned          record stored (zigpy fields + plugin fields),
                              flush requested at the next heartbeat
  9e00  commissioned again    key and frame counter replaced, first
                              commissioning time kept
  9e00  store not loaded      Error with an error code, nothing raised
  9e01  command               frame counter / LastSeen / LQI updated, no
                              flush requested (periodic flush)
  9e01  unknown GPD           logged, store unchanged
  9e02  removed               record dropped, flush requested
  no log line carries the security key

The frames are built by the real encoder from a zigpy GreenPowerDevice.
The store is an in-memory stand-in with PluginStore's record API; the
persistence itself is covered by tests/Classes/test_PluginStore.py and
tests/Modules/test_database_plugin_stores.py.
"""

import copy
import importlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

zigpy_device = pytest.importorskip("zigpy.device")

pytestmark = pytest.mark.skipif(
    not hasattr(zigpy_device, "GreenPowerDevice"), reason="requires zigpy with GreenPowerDevice"
)

import zigpy.types as t  # noqa: E402

from Classes.ZigpyTransport.greenPower import GreenPowerListener  # noqa: E402

SRC_ID = 0x0155A3B2
IEEE_HEX = "000000000155a3b2"
ALIAS_HEX = "a3b2"
KEY = bytes(range(16))
NEW_KEY = bytes(range(16, 32))


class FakeStore:
    """PluginStore record API, in memory."""

    def __init__(self):
        self.records = {}

    def __contains__(self, key):
        return key in self.records

    def get(self, key, default=None):
        return copy.deepcopy(self.records.get(key, default))

    def set(self, key, record):
        self.records[key] = copy.deepcopy(record)

    def update(self, key, fields):
        if key not in self.records:
            return False
        self.records[key].update(copy.deepcopy(fields))
        return True

    def delete(self, key):
        self.records.pop(key, None)

    def snapshot(self):
        return copy.deepcopy(self.records)


@pytest.fixture
def gp_types():
    return importlib.import_module("zigpy.zgp.types")


@pytest.fixture
def widget_updates(monkeypatch):
    """Stands in for Modules.greenPowerWidgets (tested in tests/Modules/test_greenPower_widgets.py)."""
    calls = []
    monkeypatch.setitem(sys.modules, "Modules.greenPowerWidgets", SimpleNamespace(
        update_gp_widgets=lambda self, Devices, ieee, command_id: calls.append((ieee, command_id))))
    return calls


@pytest.fixture
def decoder(widget_updates):
    sys.modules.pop("Z4D_decoders.z4d_decoder_Green_Power", None)
    return importlib.import_module("Z4D_decoders.z4d_decoder_Green_Power")


@pytest.fixture
def helpers():
    sys.modules.pop("Z4D_decoders.z4d_decoder_helpers", None)
    return importlib.import_module("Z4D_decoders.z4d_decoder_helpers")


@pytest.fixture
def gp_store_module():
    return importlib.import_module("Modules.greenPowerStore")


@pytest.fixture
def plugin(gp_store_module):
    store = FakeStore()
    return SimpleNamespace(
        log=MagicMock(),
        PluginStores={gp_store_module.GP_STORE_NAME: store},
        store=store,
        flush_list_of_devices=False,
    )


@pytest.fixture
def transport():
    app = MagicMock()
    app.frames = []
    app.callBackFunction = app.frames.append
    return app


def make_gpd(app, gp_types, key=KEY, frame_counter=1234, lqi=180):
    dev = zigpy_device.GreenPowerDevice(app, application_id=gp_types.ApplicationID.SrcID, src_id=SRC_ID)
    dev.device_id = gp_types.DeviceID.OnOffSwitch
    dev.commands = [gp_types.GPDCommandID(0x20), gp_types.GPDCommandID(0x21)]
    dev.security_level = gp_types.SecurityLevel.Encrypted
    dev.security_key_type = gp_types.SecurityKeyType.IndividualKey
    dev.security_key = t.KeyData(key)
    dev.frame_counter = frame_counter
    dev.lqi = lqi
    return dev


def decode_last(helpers, decoder, plugin, transport):
    msg_type, msg_data, msg_lqi = helpers.extract_message_infos(MagicMock(), transport.frames[-1])
    {"9e00": decoder.Decode9E00, "9e01": decoder.Decode9E01, "9e02": decoder.Decode9E02}[msg_type](plugin, {}, msg_data, msg_lqi)


def press(dev, frame_counter, command_id=0x20):
    dev.frame_counter = frame_counter
    dev.emit("gp_command_received", zigpy_device.GreenPowerCommandReceived(
        device_ieee=str(dev.ieee), endpoint_id=None, command_id=command_id, command=None))


def logged_text(plugin):
    return " ".join(str(a) for c in plugin.log.logging.call_args_list for a in c.args)


def logged_levels(plugin):
    return [c.args[1] for c in plugin.log.logging.call_args_list]


class TestCommissioning:

    def test_commissioned_device_is_stored(self, decoder, helpers, plugin, transport, gp_types, gp_store_module):
        GreenPowerListener(transport).device_initialized(make_gpd(transport, gp_types))

        decode_last(helpers, decoder, plugin, transport)

        record = plugin.store.records[IEEE_HEX]
        assert set(gp_store_module.GP_DEVICE_FIELDS) <= set(record)
        assert record["ieee"] == IEEE_HEX and record["nwk"] == ALIAS_HEX and record["src_id"] == SRC_ID
        assert record["commands"] == [0x20, 0x21]
        assert record["security_key"] == KEY.hex()
        assert record["frame_counter"] == 1234
        assert record["LQI"] == 180
        assert record["Commissioned"] == record["LastSeen"] > 0
        # Frame-only fields are not stored
        assert "v" not in record and "recommissioned" not in record
        assert plugin.flush_list_of_devices is True

    def test_commissioned_again_replaces_key_and_counter_keeps_first_time(self, decoder, helpers, plugin, transport, gp_types):
        listener = GreenPowerListener(transport)
        listener.device_initialized(make_gpd(transport, gp_types))
        decode_last(helpers, decoder, plugin, transport)
        plugin.store.records[IEEE_HEX]["Commissioned"] = 1000

        listener.device_reinterviewed(make_gpd(transport, gp_types, key=NEW_KEY, frame_counter=5, lqi=90))
        decode_last(helpers, decoder, plugin, transport)

        record = plugin.store.records[IEEE_HEX]
        assert record["security_key"] == NEW_KEY.hex()
        assert record["frame_counter"] == 5
        assert record["LQI"] == 90
        assert record["Commissioned"] == 1000
        assert record["LastSeen"] > 1000

    def test_store_not_loaded_is_an_error_with_code(self, decoder, helpers, transport, gp_types):
        plugin = SimpleNamespace(log=MagicMock(), flush_list_of_devices=False)
        GreenPowerListener(transport).device_initialized(make_gpd(transport, gp_types))

        decode_last(helpers, decoder, plugin, transport)

        error = plugin.log.logging.call_args
        assert error.args[1] == "Error"
        assert error.args[4] == {"Error code": "GPSTORE-9E00-01"}
        assert plugin.flush_list_of_devices is False

    def test_security_key_never_logged(self, decoder, helpers, plugin, transport, gp_types):
        listener = GreenPowerListener(transport)
        dev = make_gpd(transport, gp_types)
        listener.device_initialized(dev)
        decode_last(helpers, decoder, plugin, transport)
        press(dev, 1235)
        decode_last(helpers, decoder, plugin, transport)

        assert KEY.hex() not in logged_text(plugin)


class TestCommand:

    def test_command_updates_counter_without_immediate_flush(self, decoder, helpers, plugin, transport, gp_types):
        listener = GreenPowerListener(transport)
        dev = make_gpd(transport, gp_types)
        listener.device_initialized(dev)
        decode_last(helpers, decoder, plugin, transport)
        plugin.flush_list_of_devices = False
        plugin.store.records[IEEE_HEX]["LastSeen"] = 1000

        press(dev, 0x01020304)
        decode_last(helpers, decoder, plugin, transport)

        record = plugin.store.records[IEEE_HEX]
        assert record["frame_counter"] == 0x01020304
        assert record["LastSeen"] > 1000
        assert plugin.flush_list_of_devices is False

    def test_command_from_unknown_device_is_logged(self, decoder, helpers, plugin, transport, gp_types):
        listener = GreenPowerListener(transport)
        dev = make_gpd(transport, gp_types)
        listener.attach(dev)

        press(dev, 7)
        decode_last(helpers, decoder, plugin, transport)

        assert plugin.store.records == {}
        assert "not in the Green Power device store" in logged_text(plugin)
        assert "Error" not in logged_levels(plugin)


class TestRemoval:

    def test_removed_device_is_dropped_and_flushed(self, decoder, helpers, plugin, transport, gp_types):
        listener = GreenPowerListener(transport)
        dev = make_gpd(transport, gp_types)
        listener.device_initialized(dev)
        decode_last(helpers, decoder, plugin, transport)
        plugin.flush_list_of_devices = False

        listener.device_removed(dev)
        decode_last(helpers, decoder, plugin, transport)

        assert IEEE_HEX not in plugin.store
        assert plugin.flush_list_of_devices is True

    def test_removal_of_unknown_device_requests_no_flush(self, decoder, helpers, plugin, transport, gp_types):
        GreenPowerListener(transport).device_removed(make_gpd(transport, gp_types))

        decode_last(helpers, decoder, plugin, transport)

        assert plugin.flush_list_of_devices is False


class TestHandOverToZigpy:

    def test_stored_records_handed_over_as_copies(self, decoder, helpers, plugin, transport, gp_types, gp_store_module):
        GreenPowerListener(transport).device_initialized(make_gpd(transport, gp_types))
        decode_last(helpers, decoder, plugin, transport)

        records = gp_store_module.gp_devices_for_zigpy(plugin)

        assert [r["ieee"] for r in records] == [IEEE_HEX]
        records[0]["frame_counter"] = 0
        assert plugin.store.records[IEEE_HEX]["frame_counter"] == 1234

    def test_no_store_hands_over_nothing(self, gp_store_module):
        assert gp_store_module.gp_devices_for_zigpy(SimpleNamespace()) == []


class TestWidgets:

    def test_commissioning_queues_widget_creation(self, decoder, helpers, plugin, transport, gp_types):
        GreenPowerListener(transport).device_initialized(make_gpd(transport, gp_types))

        decode_last(helpers, decoder, plugin, transport)

        assert plugin.gp_widget_creation_requests == {IEEE_HEX}

    def test_commissioning_is_shown_on_the_provisioning_page(self, decoder, helpers, plugin, transport, gp_types):
        plugin.webserver = MagicMock()
        GreenPowerListener(transport).device_initialized(make_gpd(transport, gp_types))

        decode_last(helpers, decoder, plugin, transport)

        plugin.webserver.add_green_power_device_in_pairing_mode.assert_called_once_with(IEEE_HEX, IEEE_HEX[-4:])

    def test_commissioned_again_keeps_its_widgets(self, decoder, helpers, plugin, transport, gp_types):
        listener = GreenPowerListener(transport)
        listener.device_initialized(make_gpd(transport, gp_types))
        decode_last(helpers, decoder, plugin, transport)
        plugin.store.records[IEEE_HEX].update({"Model": "GreenPower-OnOff", "Ep": {"01": {"ClusterType": {"7": "Switch"}}}})

        listener.device_reinterviewed(make_gpd(transport, gp_types, key=NEW_KEY))
        decode_last(helpers, decoder, plugin, transport)

        record = plugin.store.records[IEEE_HEX]
        assert record["Ep"] == {"01": {"ClusterType": {"7": "Switch"}}} and record["Model"] == "GreenPower-OnOff"
        assert record["security_key"] == NEW_KEY.hex()

    def test_command_updates_the_widgets(self, decoder, helpers, plugin, transport, gp_types, widget_updates):
        dev = make_gpd(transport, gp_types)
        GreenPowerListener(transport).device_initialized(dev)
        decode_last(helpers, decoder, plugin, transport)

        press(dev, 1235, command_id=0x21)
        decode_last(helpers, decoder, plugin, transport)

        assert widget_updates == [(IEEE_HEX, 0x21)]

    def test_command_from_unknown_device_updates_nothing(self, decoder, helpers, plugin, transport, gp_types, widget_updates):
        dev = make_gpd(transport, gp_types)
        GreenPowerListener(transport).attach(dev)

        press(dev, 7)
        decode_last(helpers, decoder, plugin, transport)

        assert widget_updates == []
