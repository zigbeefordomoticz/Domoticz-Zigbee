#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the Danfoss Ally external room sensor path in Modules/danfoss.py

Coverage:
  - danfoss_write_external_sensor_temp
      * half-degree quantisation into centi-degrees before the range check
      * accepts the device-documented 7..30 C band (700..3000 in attribute 0x4015)
      * rejects anything below / above that band instead of encoding it
      * regression: a negative or very large reading must never reach
        write_attribute, because "%04x" on such a value yields a malformed
        ("-1388") or over-long ("c350" -> 5 nibbles for bigger ones) hex payload
        which blows up when the frame is assembled in the zigpy thread
      * endpoint hosting cluster 0201 is the one written to
  - danfoss_room_sensor_polling
      * a bogus sensor reading is dropped from the room average instead of
        poisoning it
      * the 4..40 C plausibility band boundaries
      * when every sensor in the room is bogus, nothing is written at all
      * a DanfossCovered thermostat is still excluded from the average
      * the "Found temp" trace names the *sensor* that reported, not the eTRV
      * the plausibility band (4..40) is wider than the band the device
        accepts (7..30), so a reading in between is averaged in and then
        rejected one layer down
"""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest

ZIGATE_EP = "01"

ETRV = "1234"        # the Danfoss Ally eTRV being fed an external temperature
SENSOR_A = "5678"    # a temperature sensor in the same room
SENSOR_B = "9abc"    # a second temperature sensor in the same room
ROOM = "1"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


@pytest.fixture(scope="module")
def danfoss():
    """Import Modules.danfoss with all external deps stubbed out."""
    _write_attribute = MagicMock(name="write_attribute")
    _read_attribute = MagicMock(name="read_attribute", return_value="isqn-01")
    _raw_APS_request = MagicMock(name="raw_APS_request")
    _build_fcf = MagicMock(name="build_fcf", return_value="11")
    _get_sqn = MagicMock(name="get_and_inc_ZCL_SQN", return_value="01")
    _is_ack = MagicMock(name="is_ack_tobe_disabled", return_value=False)

    def _list_of_ep_for_cluster(self, nwkid, cluster):
        """Behave like the real helper: every Ep of nwkid exposing cluster."""
        eps = self.ListOfDevices.get(nwkid, {}).get("Ep", {})
        return [ep for ep in eps if cluster in eps[ep]]

    _getListOfEp = MagicMock(name="getListOfEpForCluster", side_effect=_list_of_ep_for_cluster)

    stubs = {
        "Modules.basicOutputs": _make_stub(
            "Modules.basicOutputs",
            raw_APS_request=_raw_APS_request,
            read_attribute=_read_attribute,
            write_attribute=_write_attribute,
        ),
        "Modules.tools": _make_stub(
            "Modules.tools",
            build_fcf=_build_fcf,
            get_and_inc_ZCL_SQN=_get_sqn,
            getListOfEpForCluster=_getListOfEp,
            is_ack_tobe_disabled=_is_ack,
        ),
        "Modules.zigateConsts": _make_stub("Modules.zigateConsts", ZIGATE_EP=ZIGATE_EP),
    }

    saved = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)

    sys.modules.pop("Modules.danfoss", None)
    module = importlib.import_module("Modules.danfoss")

    module._mock_write_attribute = _write_attribute
    module._mock_read_attribute = _read_attribute
    module._mock_getListOfEp = _getListOfEp

    yield module

    for name, old in saved.items():
        if old is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old
    sys.modules.pop("Modules.danfoss", None)


@pytest.fixture(autouse=True)
def _reset_mocks(danfoss):
    danfoss._mock_write_attribute.reset_mock()
    danfoss._mock_read_attribute.reset_mock()
    danfoss._mock_getListOfEp.reset_mock()


def _plugin():
    """Minimal mock plugin holding a single Danfoss eTRV in ROOM."""
    p = MagicMock()
    p.log = MagicMock()
    p.log.logging = MagicMock()
    p.ListOfDevices = {
        ETRV: {
            "Model": "eTRV0100",
            "Param": {"DanfossRoom": ROOM},
            "Ep": {"01": {"0201": {}}},
        }
    }
    return p


def _add_sensor(p, nwkid, temp, room=ROOM, ep="01", covered=False, cluster="0402"):
    """Register a temperature sensor reporting `temp` degrees in `room`."""
    param = {"DanfossRoom": room}
    if covered:
        param["DanfossCovered"] = "T"
    p.ListOfDevices[nwkid] = {
        "Model": "TempSensor",
        "Param": param,
        "Ep": {ep: {cluster: {"0000": temp}}},
    }
    return p


def _logged(p, level, needle):
    """True when a logging call at `level` carries `needle` in its message."""
    return any(
        len(c.args) >= 3 and c.args[1] == level and needle in str(c.args[2])
        for c in p.log.logging.call_args_list
    )


def _written_payload(danfoss):
    """The Hdata argument of the single write_attribute call."""
    assert danfoss._mock_write_attribute.call_count == 1
    return danfoss._mock_write_attribute.call_args.args[9]


# ── danfoss_write_external_sensor_temp – accepted range ──────────────────────

class TestWriteExternalSensorTempAccepted:

    @pytest.mark.parametrize("temp, expected_hdata", [
        (7.0, "02bc"),     # low boundary of the band the device documents
        (20.0, "07d0"),
        (21.0, "0834"),
        (30.0, "0bb8"),    # high boundary
    ])
    def test_in_range_temp_is_written(self, danfoss, temp, expected_hdata):
        p = _plugin()
        danfoss.danfoss_write_external_sensor_temp(p, ETRV, temp)

        assert _written_payload(danfoss) == expected_hdata
        assert danfoss._mock_read_attribute.call_count == 1
        assert not _logged(p, "Error", "out of range")

    @pytest.mark.parametrize("temp, expected_hdata", [
        (20.2, "07d0"),    # rounds down to 20.0
        (20.3, "0802"),    # rounds up to 20.5
        (20.8, "0834"),    # rounds up to 21.0
    ])
    def test_value_is_quantised_to_the_half_degree(self, danfoss, temp, expected_hdata):
        """The device takes centi-degrees, but only in 0.5 C steps."""
        p = _plugin()
        danfoss.danfoss_write_external_sensor_temp(p, ETRV, temp)
        assert _written_payload(danfoss) == expected_hdata

    def test_payload_is_always_four_nibbles(self, danfoss):
        """A malformed-length payload is what used to break the zigpy thread."""
        p = _plugin()
        danfoss.danfoss_write_external_sensor_temp(p, ETRV, 25.0)
        assert len(_written_payload(danfoss)) == 4

    def test_writes_to_the_endpoint_hosting_cluster_0201(self, danfoss):
        p = _plugin()
        p.ListOfDevices[ETRV]["Ep"] = {"01": {"0402": {}}, "02": {"0201": {}}}

        danfoss.danfoss_write_external_sensor_temp(p, ETRV, 20.0)

        # write_attribute(self, NwkId, EPin, EPout, cluster_id, ...)
        args = danfoss._mock_write_attribute.call_args.args
        assert args[3] == "02"          # EPout
        assert args[4] == "0201"        # cluster


# ── danfoss_write_external_sensor_temp – rejected range ──────────────────────

class TestWriteExternalSensorTempRejected:

    @pytest.mark.parametrize("temp", [
        0.0,        # no reading at all
        3.5,
        6.5,        # just under the 7 C boundary, once quantised
        30.5,       # just over the 30 C boundary, once quantised
        40.0,
    ])
    def test_out_of_range_temp_is_not_written(self, danfoss, temp):
        p = _plugin()
        danfoss.danfoss_write_external_sensor_temp(p, ETRV, temp)

        assert danfoss._mock_write_attribute.call_count == 0
        assert danfoss._mock_read_attribute.call_count == 0
        assert _logged(p, "Error", "out of range external sensor temp")

    @pytest.mark.parametrize("temp", [-40.0, -0.5, 327.6, 500.0])
    def test_bogus_reading_never_reaches_the_encoder(self, danfoss, temp):
        """
        Regression: the guard used to read

            if 700 < external_temperature > 3000 and external_temperature < 700:

        which is a contradiction — `700 < t and t > 3000 and t < 700` can never
        be true — so *every* reading was encoded, including the ones a sensor
        emits when its battery is dying. "%04x" then produced "-1388" for a
        negative value or a five-nibble string for a very large one, and the
        malformed frame raised in the zigpy thread.
        """
        p = _plugin()
        danfoss.danfoss_write_external_sensor_temp(p, ETRV, temp)

        assert danfoss._mock_write_attribute.call_count == 0
        assert _logged(p, "Error", "out of range external sensor temp")


# ── danfoss_room_sensor_polling ──────────────────────────────────────────────

class TestRoomSensorPolling:

    def test_no_param_no_write(self, danfoss):
        p = _plugin()
        del p.ListOfDevices[ETRV]["Param"]
        danfoss.danfoss_room_sensor_polling(p, ETRV)
        assert danfoss._mock_write_attribute.call_count == 0

    def test_no_danfoss_room_no_write(self, danfoss):
        p = _plugin()
        p.ListOfDevices[ETRV]["Param"] = {}
        danfoss.danfoss_room_sensor_polling(p, ETRV)
        assert danfoss._mock_write_attribute.call_count == 0

    def test_single_sensor_in_room_is_written(self, danfoss):
        p = _add_sensor(_plugin(), SENSOR_A, 20.0)
        danfoss.danfoss_room_sensor_polling(p, ETRV)
        assert _written_payload(danfoss) == "07d0"

    def test_two_sensors_are_averaged(self, danfoss):
        p = _add_sensor(_plugin(), SENSOR_A, 20.0)
        _add_sensor(p, SENSOR_B, 22.0)
        danfoss.danfoss_room_sensor_polling(p, ETRV)
        assert _written_payload(danfoss) == "0834"   # 21.0 C

    def test_sensor_from_another_room_is_ignored(self, danfoss):
        p = _add_sensor(_plugin(), SENSOR_A, 20.0)
        _add_sensor(p, SENSOR_B, 29.0, room="2")
        danfoss.danfoss_room_sensor_polling(p, ETRV)
        assert _written_payload(danfoss) == "07d0"   # 20.0 C, SENSOR_B excluded

    def test_covered_thermostat_is_excluded_from_the_average(self, danfoss):
        p = _add_sensor(_plugin(), SENSOR_A, 20.0)
        _add_sensor(p, SENSOR_B, 29.0, covered=True)
        danfoss.danfoss_room_sensor_polling(p, ETRV)
        assert _written_payload(danfoss) == "07d0"

    def test_sensor_without_cluster_0402_is_skipped(self, danfoss):
        p = _add_sensor(_plugin(), SENSOR_A, 20.0)
        _add_sensor(p, SENSOR_B, 29.0, cluster="0403")
        danfoss.danfoss_room_sensor_polling(p, ETRV)
        assert _written_payload(danfoss) == "07d0"

    def test_sensor_without_attribute_0000_is_skipped(self, danfoss):
        p = _add_sensor(_plugin(), SENSOR_A, 20.0)
        _add_sensor(p, SENSOR_B, 29.0)
        p.ListOfDevices[SENSOR_B]["Ep"]["01"]["0402"] = {}
        danfoss.danfoss_room_sensor_polling(p, ETRV)
        assert _written_payload(danfoss) == "07d0"


class TestRoomSensorPollingPlausibilityBand:

    @pytest.mark.parametrize("temp", [4.0, 7.0, 20.0, 40.0])
    def test_plausible_reading_is_kept(self, danfoss, temp):
        p = _add_sensor(_plugin(), SENSOR_A, temp)
        danfoss.danfoss_room_sensor_polling(p, ETRV)
        assert not _logged(p, "Error", "out of range external sensor from")

    @pytest.mark.parametrize("temp", [-40.0, 0.0, 3.9, 40.1, 85.0, 327.6])
    def test_implausible_reading_is_dropped(self, danfoss, temp):
        p = _add_sensor(_plugin(), SENSOR_A, temp)
        danfoss.danfoss_room_sensor_polling(p, ETRV)

        assert _logged(p, "Error", "out of range external sensor from")
        assert danfoss._mock_write_attribute.call_count == 0

    def test_bogus_sensor_does_not_poison_the_room_average(self, danfoss):
        """
        A dying sensor reporting 100 C alongside a healthy one at 21 C used to
        drag the average to 60.5 C, which the write guard then throws away —
        losing the healthy reading too. The bogus sample must be dropped first.
        """
        p = _add_sensor(_plugin(), SENSOR_A, 100.0)
        _add_sensor(p, SENSOR_B, 21.0)

        danfoss.danfoss_room_sensor_polling(p, ETRV)

        assert _written_payload(danfoss) == "0834"   # 21.0 C, the healthy sensor
        assert _logged(p, "Error", "out of range external sensor from")

    def test_every_sensor_bogus_writes_nothing(self, danfoss):
        p = _add_sensor(_plugin(), SENSOR_A, 100.0)
        _add_sensor(p, SENSOR_B, -50.0)

        danfoss.danfoss_room_sensor_polling(p, ETRV)

        assert danfoss._mock_write_attribute.call_count == 0

    def test_plausible_but_not_device_acceptable_is_rejected_one_layer_down(self, danfoss):
        """
        The polling band (4..40 C) is wider than the band attribute 0x4015
        accepts (7..30 C), so 5 C survives the average and is then refused by
        danfoss_write_external_sensor_temp. Documents the two bands differing.
        """
        p = _add_sensor(_plugin(), SENSOR_A, 5.0)

        danfoss.danfoss_room_sensor_polling(p, ETRV)

        assert not _logged(p, "Error", "out of range external sensor from")
        assert _logged(p, "Error", "out of range external sensor temp")
        assert danfoss._mock_write_attribute.call_count == 0


class TestRoomSensorPollingTrace:

    def test_found_temp_trace_names_the_reporting_sensor(self, danfoss):
        """
        The trace used to print the eTRV's own nwkid as the source of the
        reading, which made a room with several sensors unreadable in the log.
        """
        p = _add_sensor(_plugin(), SENSOR_A, 20.0)

        danfoss.danfoss_room_sensor_polling(p, ETRV)

        found = [
            str(c.args[2])
            for c in p.log.logging.call_args_list
            if len(c.args) >= 3 and "Found temp" in str(c.args[2])
        ]
        assert len(found) == 1
        assert "from Nwkid: %s" % SENSOR_A in found[0]
