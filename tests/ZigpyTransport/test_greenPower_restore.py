#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for restore_green_power_devices() and gp_device_from_record()
(Classes/ZigpyTransport/greenPower.py): the GPDs of the plugin's Green Power
device store handed back to zigpy at startup.

Covers:
  round trip      GreenPowerDevice → 9e00 → store record → GreenPowerDevice,
                  every field zigpy persists comes back
  registration    zigpy DB listener and the plugin listener attached, no 9e00
                  sent at restore, presses of a restored GPD reach the plugin
  known GPD       (zigpy file database) kept; frame counter raised, never lowered
  conflicts       a Zigbee device on the IEEE is left alone (Error with code)
  bad record      Error with code, key not logged, other records restored
  manager         green_power.startup() awaited after the devices are in place,
                  also when the store cannot be read
  zigpy without Green Power: nothing done

The app is a MagicMock with a real devices dict; the devices are real zigpy
GreenPowerDevice objects.
"""

import asyncio
import importlib
import sys
from unittest.mock import MagicMock

import pytest

zigpy_device = pytest.importorskip("zigpy.device")
zigpy_application = pytest.importorskip("zigpy.application")

pytestmark = pytest.mark.skipif(
    not hasattr(zigpy_application.ControllerApplication, "permit_gp"),
    reason="requires zigpy with the Green Power manager (>= 2.4.0)",
)

import zigpy.types as t  # noqa: E402

from Classes.ZigpyTransport.greenPower import (  # noqa: E402
    GreenPowerListener, gp_device_from_record, restore_green_power_devices)
from Modules.greenPowerStore import gp_device_record  # noqa: E402

SRC_ID = 0x0155A3B2
IEEE_HEX = "000000000155a3b2"
OTHER_SRC_ID = 0x01020304
OTHER_IEEE_HEX = "0000000001020304"
KEY = bytes(range(16))


@pytest.fixture
def gp_types():
    return importlib.import_module("zigpy.zgp.types")


@pytest.fixture
def helpers():
    sys.modules.pop("Z4D_decoders.z4d_decoder_helpers", None)
    return importlib.import_module("Z4D_decoders.z4d_decoder_helpers")


@pytest.fixture
def decoder():
    sys.modules.pop("Z4D_decoders.z4d_decoder_Green_Power", None)
    return importlib.import_module("Z4D_decoders.z4d_decoder_Green_Power")


@pytest.fixture
def app():
    app = MagicMock()
    app.frames = []
    app.callBackFunction = app.frames.append
    app.devices = {}
    app.records = []
    app.callBackGetAllGpDevices = lambda: app.records
    app.startup_saw = []

    async def gp_startup():
        app.startup_saw.append(sorted(str(ieee) for ieee in app.devices))

    app.green_power = MagicMock()
    app.green_power.startup = gp_startup
    app.z4d_gp_listener = GreenPowerListener(app)
    return app


def make_gpd(app, gp_types, src_id=SRC_ID, frame_counter=1234):
    dev = zigpy_device.GreenPowerDevice(app, application_id=gp_types.ApplicationID.SrcID, src_id=src_id)
    dev.device_id = gp_types.DeviceID.OnOffSwitch
    dev.gpd_manufacturer_id = t.uint16_t(0x1234)
    dev.gpd_model_id = t.uint16_t(0x0042)
    dev.commands = [gp_types.GPDCommandID(0x20), gp_types.GPDCommandID(0x21)]
    dev.server_cluster_ids = [t.uint16_t(0x0006)]
    dev.client_cluster_ids = [t.uint16_t(0x0008)]
    dev.mac_seq_num_capability = True
    dev.rx_on_capability = False
    dev.fixed_location = True
    dev.security_level = gp_types.SecurityLevel.Encrypted
    dev.security_key_type = gp_types.SecurityKeyType.IndividualKey
    dev.security_key = t.KeyData(KEY)
    dev.frame_counter = frame_counter
    dev.lqi = 180
    return dev


def store_record(app, helpers, decoder, dev, now=1_700_000_000):
    """The record the plugin stores for dev, through the real 9e00 frame."""
    sender = MagicMock()
    sender.frames = []
    sender.callBackFunction = sender.frames.append
    GreenPowerListener(sender).device_initialized(dev)
    _, msg_data, msg_lqi = helpers.extract_message_infos(MagicMock(), sender.frames[0])
    return gp_device_record(decoder.decode_gp_record(msg_data), now, int(msg_lqi, 16))


def restore(app):
    asyncio.run(restore_green_power_devices(app))


def logged(app):
    return [(c.args[1], c.args[2], c.args[4] if len(c.args) > 4 else None) for c in app.log.logging.call_args_list]


def errors(app):
    return [(msg, ctx) for level, msg, ctx in logged(app) if level == "Error"]


class TestRoundTrip:

    def test_every_persisted_field_comes_back(self, app, gp_types, helpers, decoder):
        original = make_gpd(MagicMock(), gp_types)
        record = store_record(app, helpers, decoder, original)

        rebuilt = gp_device_from_record(app, record)

        assert isinstance(rebuilt, zigpy_device.GreenPowerDevice)
        assert rebuilt.ieee == original.ieee and rebuilt.nwk == original.nwk
        for field in ("application_id", "src_id", "device_id", "gpd_manufacturer_id", "gpd_model_id", "commands",
                      "server_cluster_ids", "client_cluster_ids", "switch_configuration", "mac_seq_num_capability",
                      "rx_on_capability", "fixed_location", "security_key", "security_key_type", "security_level",
                      "frame_counter"):
            assert getattr(rebuilt, field) == getattr(original, field), field
        assert rebuilt.last_seen == 1_700_000_000


class TestRestore:

    def test_restored_devices_are_registered_without_commissioning_frame(self, app, gp_types, helpers, decoder):
        app.records = [store_record(app, helpers, decoder, make_gpd(MagicMock(), gp_types))]

        restore(app)

        dev = app.devices[t.EUI64.convert(":".join(IEEE_HEX[i:i + 2] for i in range(0, 16, 2)))]
        assert isinstance(dev, zigpy_device.GreenPowerDevice)
        app._dblistener.register_gp_device_events.assert_called_once_with(dev)
        assert app.frames == []
        assert errors(app) == []
        assert any(level == "Status" and "1 device(s) restored" in msg for level, msg, _ in logged(app))

    def test_presses_of_a_restored_device_reach_the_plugin(self, app, gp_types, helpers, decoder):
        app.records = [store_record(app, helpers, decoder, make_gpd(MagicMock(), gp_types))]
        restore(app)
        dev = next(iter(app.devices.values()))

        dev.emit("gp_command_received", zigpy_device.GreenPowerCommandReceived(
            device_ieee=str(dev.ieee), endpoint_id=None, command_id=0x20, command=None))

        assert [frame[2:6] for frame in app.frames] == ["9e01"]

    def test_manager_started_after_the_devices_are_in_place(self, app, gp_types, helpers, decoder):
        app.records = [store_record(app, helpers, decoder, make_gpd(MagicMock(), gp_types)),
                       store_record(app, helpers, decoder, make_gpd(MagicMock(), gp_types, src_id=OTHER_SRC_ID))]

        restore(app)

        assert len(app.startup_saw) == 1 and len(app.startup_saw[0]) == 2

    def test_empty_store_still_starts_the_manager(self, app):
        restore(app)

        assert app.startup_saw == [[]]
        assert logged(app) == []


class TestKnownDevice:

    def _known(self, app, gp_types, helpers, decoder, zigpy_counter, store_counter):
        known = make_gpd(app, gp_types, frame_counter=zigpy_counter)
        app.devices[known.ieee] = known
        app.records = [store_record(app, helpers, decoder, make_gpd(MagicMock(), gp_types, frame_counter=store_counter))]
        restore(app)
        return known

    def test_kept_and_counter_raised(self, app, gp_types, helpers, decoder):
        known = self._known(app, gp_types, helpers, decoder, zigpy_counter=10, store_counter=50)

        assert app.devices[known.ieee] is known
        assert known.frame_counter == 50

    def test_counter_never_lowered(self, app, gp_types, helpers, decoder):
        known = self._known(app, gp_types, helpers, decoder, zigpy_counter=50, store_counter=10)

        assert known.frame_counter == 50


class TestConflictsAndBadRecords:

    def test_zigbee_device_on_the_ieee_is_left_alone(self, app, gp_types, helpers, decoder):
        record = store_record(app, helpers, decoder, make_gpd(MagicMock(), gp_types))
        zigbee = MagicMock(spec=zigpy_device.Device)
        ieee = gp_device_from_record(app, record).ieee
        app.devices[ieee] = zigbee
        app.records = [record]

        restore(app)

        assert app.devices[ieee] is zigbee
        assert [ctx for _, ctx in errors(app)] == [{"Error code": "GPSTORE-RESTORE-02"}]

    def test_bad_record_logged_without_key_others_restored(self, app, gp_types, helpers, decoder):
        bad = store_record(app, helpers, decoder, make_gpd(MagicMock(), gp_types))
        bad["application_id"] = 99  # not an ApplicationID
        good = store_record(app, helpers, decoder, make_gpd(MagicMock(), gp_types, src_id=OTHER_SRC_ID))
        app.records = [bad, good]

        restore(app)

        assert len(app.devices) == 1
        assert [ctx for _, ctx in errors(app)] == [{"Error code": "GPSTORE-RESTORE-01"}]
        text = " ".join(str(c.args) for c in app.log.logging.call_args_list)
        assert KEY.hex() not in text

    def test_unreadable_store_logged_and_manager_started(self, app):
        def broken():
            raise RuntimeError("store")
        app.callBackGetAllGpDevices = broken

        restore(app)

        assert [ctx for _, ctx in errors(app)] == [{"Error code": "GPSTORE-RESTORE-04"}]
        assert app.startup_saw == [[]]


class TestWithoutGreenPower:

    def test_nothing_done(self, app):
        app.green_power = None
        app.callBackGetAllGpDevices = MagicMock()

        restore(app)

        app.callBackGetAllGpDevices.assert_not_called()
        assert app.devices == {}


class TestRemoval:
    """REMOVE-DEVICE → App_*.remove_ieee() → zigpy remove(): a GPD is unpaired, never sent a Leave."""

    def test_zigpy_remove_unpairs_and_reports_9e02(self, app, gp_types, helpers, decoder):
        app.records = [store_record(app, helpers, decoder, make_gpd(MagicMock(), gp_types))]
        restore(app)
        dev = next(iter(app.devices.values()))
        unpaired = []

        async def unpair(device):
            unpaired.append(device)

        app.green_power.unpair = unpair
        app.listener_event = lambda name, *args: getattr(app.z4d_gp_listener, name)(*args)

        asyncio.run(zigpy_application.ControllerApplication.remove(app, dev.ieee))

        assert app.devices == {}
        assert unpaired == [dev]
        assert [frame[2:6] for frame in app.frames] == ["9e02"]
        # No ZDO Leave / Mgmt_Leave: nothing is sent to a GPD itself
        app.request.assert_not_called()
