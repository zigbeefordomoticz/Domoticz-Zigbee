#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Modules.tuya.tuyaReadRawAPS - the decoder of the Tuya
TS0601 / 0xEF00 manufacturer specific cluster.

The tests focus on the command demultiplexing and datapoint parsing logic.
``tuya_response`` (the per-model dispatcher) is replaced by a MagicMock so we
can assert exactly which (dp, datatype, data) tuples were extracted from each
frame, independently of any device specific handling.
"""

import sys
import types
import importlib

import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_stub(name, **attrs):
    """Ensure sys.modules[name] exists and carries the given attributes.

    Existing modules/stubs (e.g. those installed by conftest) are augmented
    rather than replaced, so we don't clobber fixtures shared with other tests.
    """
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    for k, v in attrs.items():
        if not hasattr(mod, k):
            setattr(mod, k, v)
    return mod


# ---------------------------------------------------------------------------
# Fixture: stub Modules.tuya dependencies and import it fresh
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tuya_module():
    stubs = {
        "Modules.basicOutputs": dict(
            raw_APS_request=MagicMock(name="raw_APS_request"),
            read_attribute=MagicMock(name="read_attribute"),
            write_attribute=MagicMock(name="write_attribute"),
        ),
        "Modules.bindings": dict(bindDevice=MagicMock(name="bindDevice")),
        "Modules.domoMaj": dict(MajDomoDevice=MagicMock(name="MajDomoDevice")),
        "Modules.domoTools": dict(Update_Battery_Device=MagicMock(name="Update_Battery_Device")),
        "Modules.tools": dict(
            build_fcf=MagicMock(name="build_fcf"),
            checkAndStoreAttributeValue=MagicMock(name="checkAndStoreAttributeValue"),
            get_and_inc_ZCL_SQN=MagicMock(name="get_and_inc_ZCL_SQN", return_value="aa"),
            get_device_config_param=MagicMock(name="get_device_config_param", return_value=None),
            get_deviceconf_parameter_value=MagicMock(name="get_deviceconf_parameter_value", return_value=None),
            is_ack_tobe_disabled=MagicMock(name="is_ack_tobe_disabled", return_value=False),
            updSQN=MagicMock(name="updSQN"),
        ),
        "Modules.tuyaConst": dict(
            TUYA_MANUF_CODE="1002",
            TUYA_SMART_DOOR_LOCK_MODEL=(),
            TUYA_eTRV_MODEL=(),
        ),
        "Modules.tuyaSiren": dict(
            tuya_siren2_response=MagicMock(name="tuya_siren2_response"),
            tuya_siren_response=MagicMock(name="tuya_siren_response"),
        ),
        "Modules.tuyaTools": dict(
            get_next_tuya_transactionId=MagicMock(name="get_next_tuya_transactionId"),
            get_tuya_attribute=MagicMock(name="get_tuya_attribute"),
            store_tuya_attribute=MagicMock(name="store_tuya_attribute"),
            tuya_cmd=MagicMock(name="tuya_cmd"),
        ),
        "Modules.tuyaTRV": dict(tuya_eTRV_response=MagicMock(name="tuya_eTRV_response")),
        "Modules.tuyaTS011F": dict(tuya_read_cluster_e001=MagicMock(name="tuya_read_cluster_e001")),
        "Modules.tuyaTS0601": dict(ts0601_response=MagicMock(name="ts0601_response", return_value=False)),
        "Modules.zigateConsts": dict(
            ONOFF_CLUSTER="0006",
            WINDOWS_COVERING_CLUSTER="0102",
            ZIGATE_EP="01",
        ),
        "Zigbee.zclDecoders": dict(zcl_raw_default_response=MagicMock(name="zcl_raw_default_response")),
    }
    for name, attrs in stubs.items():
        _ensure_stub(name, **attrs)

    sys.modules.pop("Modules.tuya", None)
    mod = importlib.import_module("Modules.tuya")
    yield mod
    sys.modules.pop("Modules.tuya", None)


# ---------------------------------------------------------------------------
# Fixture: plugin mock + patched collaborators
# ---------------------------------------------------------------------------

NWKID = "1234"
SRC_EP = "01"
DST_NWK = "0000"
DST_EP = "01"


@pytest.fixture
def plugin(tuya_module):
    p = MagicMock()
    p.log = MagicMock()
    p.log.logging = MagicMock()
    p.ListOfDevices = {NWKID: {"Model": "TS0601-test"}}
    # zigpy + parameter disabled => no default response on the decode tests
    p.zigbee_communication = "zigpy"
    p.FirmwareVersion = "031f"
    return p


@pytest.fixture
def captured(tuya_module, monkeypatch):
    """Replace the per-model dispatcher and side-effecting collaborators with
    mocks so each test can assert on what tuyaReadRawAPS extracted/called."""
    tuya_response = MagicMock(name="tuya_response")
    tuya_default_response = MagicMock(name="tuya_default_response")
    send_timesync = MagicMock(name="send_timesynchronisation")
    store_attr = MagicMock(name="store_tuya_attribute")
    raw_aps = MagicMock(name="raw_APS_request")

    monkeypatch.setattr(tuya_module, "tuya_response", tuya_response)
    monkeypatch.setattr(tuya_module, "tuya_default_response", tuya_default_response)
    monkeypatch.setattr(tuya_module, "send_timesynchronisation", send_timesync)
    monkeypatch.setattr(tuya_module, "store_tuya_attribute", store_attr)
    monkeypatch.setattr(tuya_module, "raw_APS_request", raw_aps)
    monkeypatch.setattr(tuya_module, "get_deviceconf_parameter_value", MagicMock(return_value=False))
    monkeypatch.setattr(tuya_module, "get_and_inc_ZCL_SQN", MagicMock(return_value="aa"))

    return types.SimpleNamespace(
        tuya_response=tuya_response,
        tuya_default_response=tuya_default_response,
        send_timesync=send_timesync,
        store_attr=store_attr,
        raw_aps=raw_aps,
    )


def _call(tuya_module, plugin, payload):
    tuya_module.tuyaReadRawAPS(
        plugin, MagicMock(name="Devices"), NWKID, SRC_EP, "ef00", DST_NWK, DST_EP, payload
    )


def _dp_calls(mock):
    """Return list of (dp, datatype, data) extracted from tuya_response calls."""
    out = []
    for c in mock.call_args_list:
        # tuya_response(self, Devices, Model, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)
        out.append((c.args[8], c.args[9], c.args[10]))
    return out


# ---------------------------------------------------------------------------
# Guard clauses
# ---------------------------------------------------------------------------

def test_unknown_nwkid_returns(tuya_module, plugin, captured):
    _call(tuya_module, plugin, "09010200000102000400000046")
    plugin.ListOfDevices.clear()
    _call(tuya_module, plugin, "09010200000102000400000046")
    # First call decoded (device known), second short-circuited
    assert captured.tuya_response.call_count == 1


def test_e001_cluster_routed(tuya_module, plugin):
    tuya_module.tuyaReadRawAPS(
        plugin, MagicMock(), NWKID, SRC_EP, "e001", DST_NWK, DST_EP, "0011"
    )
    tuya_module.tuya_read_cluster_e001.assert_called_once()


def test_non_ef00_cluster_ignored(tuya_module, plugin, captured):
    tuya_module.tuyaReadRawAPS(
        plugin, MagicMock(), NWKID, SRC_EP, "0006", DST_NWK, DST_EP, "09010200000102000400000046"
    )
    captured.tuya_response.assert_not_called()


def test_payload_too_short_returns(tuya_module, plugin, captured):
    _call(tuya_module, plugin, "0901")
    captured.tuya_response.assert_not_called()


# ---------------------------------------------------------------------------
# Datapoint parsing for 0x01 / 0x02 / 0x05 / 0x06
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cmd", ["01", "02", "05", "06"])
def test_single_datapoint(tuya_module, plugin, captured, cmd):
    # fcf sqn cmd status transid | dp dt len(2B) data
    payload = "09" + "01" + cmd + "00" + "00" + "01" + "02" + "0004" + "00000046"
    _call(tuya_module, plugin, payload)
    assert _dp_calls(captured.tuya_response) == [(1, 2, "00000046")]


@pytest.mark.parametrize("cmd", ["01", "02", "05", "06"])
def test_multiple_datapoints(tuya_module, plugin, captured, cmd):
    dp1 = "01" + "02" + "0004" + "00000046"   # dp1, 4-byte value
    dp2 = "02" + "01" + "0001" + "01"         # dp2, bool
    payload = "09" + "01" + cmd + "00" + "00" + dp1 + dp2
    _call(tuya_module, plugin, payload)
    assert _dp_calls(captured.tuya_response) == [
        (1, 2, "00000046"),
        (2, 1, "01"),
    ]


def test_cmd05_active_status_report_is_decoded(tuya_module, plugin, captured):
    """Regression: 0x05 (activeStatusReport) used to fall into UNMANAGED."""
    payload = "09" + "01" + "05" + "00" + "00" + "12" + "04" + "0001" + "03"
    _call(tuya_module, plugin, payload)
    assert _dp_calls(captured.tuya_response) == [(0x12, 0x04, "03")]


def test_cmd06_multiple_datapoints_decoded(tuya_module, plugin, captured):
    """Regression: 0x06 previously decoded only a single, mis-parsed DP."""
    dp1 = "65" + "02" + "0004" + "0000000a"
    dp2 = "66" + "02" + "0004" + "00000014"
    payload = "09" + "01" + "06" + "00" + "00" + dp1 + dp2
    _call(tuya_module, plugin, payload)
    assert _dp_calls(captured.tuya_response) == [
        (0x65, 2, "0000000a"),
        (0x66, 2, "00000014"),
    ]


def test_truncated_trailing_fragment_ignored(tuya_module, plugin, captured):
    # One valid DP followed by a 2-char fragment that cannot form a header.
    payload = "09" + "01" + "02" + "00" + "00" + "01" + "02" + "0004" + "00000046" + "07"
    _call(tuya_module, plugin, payload)
    # The complete DP is decoded; the partial fragment does not raise.
    assert _dp_calls(captured.tuya_response) == [(1, 2, "00000046")]


# ---------------------------------------------------------------------------
# Manufacturer specific frame (FCF bit 2 set)
# ---------------------------------------------------------------------------

def test_manufacturer_specific_frame_offsets(tuya_module, plugin, captured):
    # fcf=0x0d (manuf bit set), manuf code 0x0001 on the wire as little-endian "0100"
    # fcf manuf  sqn cmd status transid | dp dt len data
    payload = "0d" + "0100" + "01" + "02" + "00" + "00" + "04" + "02" + "0004" + "00000014"
    _call(tuya_module, plugin, payload)
    assert _dp_calls(captured.tuya_response) == [(4, 2, "00000014")]


def test_manufacturer_code_forwarded_to_default_response(tuya_module, plugin, captured):
    # native + firmware < 0x031E forces a Tuya default response
    plugin.zigbee_communication = "native"
    plugin.FirmwareVersion = "031d"
    payload = "0d" + "0100" + "01" + "02" + "00" + "00" + "04" + "02" + "0004" + "00000014"
    _call(tuya_module, plugin, payload)
    captured.tuya_default_response.assert_called_once()
    # signature: (self, NwkId, srcEp, ClusterID, cmd, sqn, fcf, manuf_code)
    args = captured.tuya_default_response.call_args.args
    assert args[7] == "0001"   # logical/big-endian manufacturer code


# ---------------------------------------------------------------------------
# Other commands
# ---------------------------------------------------------------------------

def test_mcu_version_response(tuya_module, plugin, captured):
    # fcf sqn cmd transid(uint16) version(uint8)
    payload = "09" + "6c" + "11" + "02f8" + "40"
    _call(tuya_module, plugin, payload)
    captured.store_attr.assert_called_once()
    args = captured.store_attr.call_args.args
    assert args[1] == NWKID and args[2] == "TUYA_MCU_VERSION_RSP" and args[3] == "40"
    captured.tuya_response.assert_not_called()


def test_time_synchronisation(tuya_module, plugin, captured):
    payload = "09" + "01" + "24" + "0008"
    _call(tuya_module, plugin, payload)
    captured.send_timesync.assert_called_once()
    assert captured.send_timesync.call_args.args[-1] == "0008"


def test_gateway_status_triggers_response(tuya_module, plugin, captured):
    payload = "09" + "01" + "25" + "01"
    _call(tuya_module, plugin, payload)
    captured.raw_aps.assert_called_once()
    captured.tuya_response.assert_not_called()


@pytest.mark.parametrize("cmd", ["0b", "10", "23"])
def test_noop_commands(tuya_module, plugin, captured, cmd):
    payload = "09" + "01" + cmd + "0000"
    _call(tuya_module, plugin, payload)
    captured.tuya_response.assert_not_called()
    captured.store_attr.assert_not_called()


def test_unmanaged_command_logged(tuya_module, plugin, captured):
    payload = "09" + "01" + "7f" + "0000"
    _call(tuya_module, plugin, payload)
    captured.tuya_response.assert_not_called()
    assert any(
        c.args[1] == "Log" for c in plugin.log.logging.call_args_list
    )

