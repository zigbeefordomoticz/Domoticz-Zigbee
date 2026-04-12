#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import types
import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_stub_module(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


def ensure_package(name):
    """Ensure a module behaves like a package."""
    if name not in sys.modules:
        mod = types.ModuleType(name)
        mod.__path__ = []
        sys.modules[name] = mod


# ---------------------------------------------------------------------------
# Fixture: stub all external dependencies BEFORE importing Modules.input
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def stub_external_modules():
    DECODER_SPECS = [
    ("Z4D_decoders.z4d_decoder_Active_Ep_Rsp",       {"Decode8045": MagicMock(name="Decode8045")}),
    ("Z4D_decoders.z4d_decoder_Attr_Discovery_Rsp",  {"Decode8140": MagicMock(name="Decode8140")}),
    ("Z4D_decoders.z4d_decoder_bindings",             {"Decode8030": MagicMock(), "Decode8031": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Complex_Descriptor_Rsp", {"Decode8034": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_config_reporting",     {"Decode8120": MagicMock(), "Decode8122": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Data_Indication",      {"Decode8002": MagicMock(name="Decode8002")}),
    ("Z4D_decoders.z4d_decoder_Default_Req",          {"Decode7000": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Default_Rsp",          {"Decode8101": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Device_Annoucement",   {"Decode004D": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Discovery_Rsp",        {"Decode804B": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_groups",               {"Decode8060": MagicMock(), "Decode8061": MagicMock(),
                                                        "Decode8062": MagicMock(), "Decode8063": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_helpers",              {"extract_message_infos": MagicMock(name="extract_message_infos")}),
    ("Z4D_decoders.z4d_decoder_IAS",                  {"Decode0400": MagicMock(), "Decode8046": MagicMock(),
                                                        "Decode8400": MagicMock(), "Decode8401": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_IEEE_addr_req",        {"Decode0041": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_IEEE_Addr_Rsp",        {"Decode8041": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Leave_Notification",   {"Decode8048": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Leave_Rsp",            {"Decode8047": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Node_Desc_req",        {"Decode0042": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Node_Desc_Rsp",        {"Decode8042": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_NWK_addr_req",         {"Decode0040": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Nwk_Addr_Rsp",        {"Decode8040": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Nwk_Map_Rsp",         {"Decode804E": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Nwk_Scan_Rsp",        {"Decode804A": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Nwk_Status",          {"Decode8009": MagicMock(), "Decode8024": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_OTA_Rsp",             {"Decode8501": MagicMock(), "Decode8502": MagicMock(),
                                                       "Decode8503": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Power_Descriptor_Rsp", {"Decode8044": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Pwr_Mgt_Rsp",         {"Decode8806": MagicMock(), "Decode8807": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Read_Attribute_Request", {"Decode0100": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Read_Attribute_Rsp",  {"Decode8100": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Read_Report_Attribute_Rsp", {"Decode8102": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Remotes",             {"Decode80A7": MagicMock(), "Decode8085": MagicMock(),
                                                       "Decode8095": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Rte_Discovery_Performed", {"Decode8701": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Scenes",              {"Decode80A5": MagicMock(), "Decode80A6": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Simple_Descriptor_Rsp", {"Decode8043": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_User_Desc_Notify",    {"Decode802B": MagicMock(), "Decode802C": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Write_Attribute_Request", {"Decode0110": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Wrt_Attribute_Rsp",   {"Decode8110": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Zigate_Active_Devices_List", {"Decode8015": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Zigate_Authenticate_Rsp", {"Decode8028": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Zigate_Clusters",     {"Decode8003": MagicMock(), "Decode8004": MagicMock(),
                                                       "Decode8005": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Zigate_Cmd_Rsp",      {"Decode8000_v2": MagicMock(name="Decode8000_v2"),
                                                       "Decode8011": MagicMock(name="Decode8011")}),
    ("Z4D_decoders.z4d_decoder_Zigate_Firmware_Version", {"Decode8010": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Zigate_Heartbeat",    {"Decode8008": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Zigate_Pairing",      {"Decode8014": MagicMock(), "Decode8049": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Zigate_PDM",          {"Decode0302": MagicMock(), "Decode8006": MagicMock(),
                                                       "Decode8007": MagicMock()}),
    ("Z4D_decoders.z4d_decoder_Zigate_Time_Srv",     {"Decode8017": MagicMock()}),
    ("Zigbee.decode8002",                             {"decode8002_and_process": MagicMock(name="decode8002_and_process")}),
    
        ("Z4D_decoders.z4d_decoder_Active_Ep_Rsp", {"Decode8045": MagicMock()}),
        ("Z4D_decoders.z4d_decoder_Attr_Discovery_Rsp", {"Decode8140": MagicMock()}),
        ("Z4D_decoders.z4d_decoder_Data_Indication", {"Decode8002": MagicMock()}),
        ("Z4D_decoders.z4d_decoder_Zigate_Cmd_Rsp", {
            "Decode8000_v2": MagicMock(),
            "Decode8011": MagicMock(),
        }),
        ("Z4D_decoders.z4d_decoder_helpers", {
            "extract_message_infos": MagicMock()
        }),
        ("Zigbee.decode8002", {
            "decode8002_and_process": MagicMock()
        }),
    ]

    for mod_name, attrs in DECODER_SPECS:
        parts = mod_name.split(".")

        # Build package hierarchy (but DO NOT override "Modules")
        for i in range(1, len(parts)):
            pkg = ".".join(parts[:i])
            if pkg != "Modules":
                ensure_package(pkg)

        sys.modules[mod_name] = make_stub_module(mod_name, **attrs)

    yield


# ---------------------------------------------------------------------------
# Fixture: import module under test
# ---------------------------------------------------------------------------

@pytest.fixture
def input_module():
    import importlib
    mod = importlib.import_module("Modules.input")
    return mod


# ---------------------------------------------------------------------------
# Fixture: plugin mock
# ---------------------------------------------------------------------------

@pytest.fixture
def plugin(input_module):
    p = MagicMock()
    p.Ping = {"Nb Ticks": 5}
    p.log = MagicMock()
    p.log.logging = MagicMock()

    # Default extract_message_infos
    input_module.extract_message_infos.return_value = ("8045", "payload", "ff")

    return p


VALID_DATA = "01aabbccdd03"
INVALID_DATA = "02aabbccdd04"


# ---------------------------------------------------------------------------
# Tests: zigbee_receive_message
# ---------------------------------------------------------------------------

def test_none_data_returns(input_module, plugin):
    input_module.zigbee_receive_message(plugin, {}, None)
    plugin.log.logging.assert_not_called()


def test_valid_frame_no_error(input_module, plugin, monkeypatch):
    monkeypatch.setattr(input_module, "_decode_message", MagicMock())

    input_module.zigbee_receive_message(plugin, {}, VALID_DATA)

    assert not any(c.args[1] == "Error" for c in plugin.log.logging.call_args_list)


@pytest.mark.parametrize("data", [
    "02aabbccdd03",
    "01aabbccdd04",
    INVALID_DATA,
])
def test_invalid_frame_logs_error(input_module, plugin, data):
    input_module.zigbee_receive_message(plugin, {}, data)
    plugin.log.logging.assert_called_once()
    assert "Error" in plugin.log.logging.call_args.args


def test_valid_frame_resets_ping(input_module, plugin, monkeypatch):
    plugin.Ping["Nb Ticks"] = 99
    monkeypatch.setattr(input_module, "_decode_message", MagicMock())

    input_module.zigbee_receive_message(plugin, {}, VALID_DATA)

    assert plugin.Ping["Nb Ticks"] == 0


def test_invalid_frame_does_not_reset_ping(input_module, plugin):
    plugin.Ping["Nb Ticks"] = 99

    input_module.zigbee_receive_message(plugin, {}, INVALID_DATA)

    assert plugin.Ping["Nb Ticks"] == 99


# ---------------------------------------------------------------------------
# Tests: 8002 unwrapping
# ---------------------------------------------------------------------------

def test_8002_unwrap_success(input_module, plugin, monkeypatch):
    input_module.extract_message_infos.side_effect = [
        ("8002", "outer", "aa"),
        ("8045", "inner", "bb"),
    ]

    input_module.decode8002_and_process.return_value = "01inner03"

    mock_dispatch = MagicMock()
    monkeypatch.setattr(input_module, "_decode_message", mock_dispatch)

    input_module.zigbee_receive_message(plugin, {}, VALID_DATA)

    mock_dispatch.assert_called_once()
    assert mock_dispatch.call_args.args[1] == "8045"


def test_8002_unwrap_failure(input_module, plugin, monkeypatch):
    input_module.extract_message_infos.side_effect = [
        ("8002", "outer", "aa"),
    ]

    input_module.decode8002_and_process.return_value = None

    mock_dispatch = MagicMock()
    monkeypatch.setattr(input_module, "_decode_message", mock_dispatch)

    input_module.zigbee_receive_message(plugin, {}, VALID_DATA)

    mock_dispatch.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: _decode_message
# ---------------------------------------------------------------------------

def test_dispatch_known_type(input_module, plugin):
    input_module.DECODERS["8045"].reset_mock()

    input_module._decode_message(plugin, "8045", {}, "raw", "data", "ff")

    input_module.DECODERS["8045"].assert_called_once()


def test_dispatch_8011(input_module, plugin):
    input_module.Decode8011.reset_mock()

    input_module._decode_message(plugin, "8011", {}, "raw", "data", "ff")

    input_module.Decode8011.assert_called_once()


def test_dispatch_8002_raw(input_module, plugin):
    input_module.Decode8002.reset_mock()

    input_module._decode_message(plugin, "8002", {}, "full", "data", "ff")

    input_module.Decode8002.assert_called_once()


def test_unknown_type_logs_error(input_module, plugin):
    input_module._decode_message(plugin, "ffff", {}, "raw", "data", "ff")

    plugin.log.logging.assert_called()
    assert "Error" in plugin.log.logging.call_args.args


def test_decoder_exception_is_caught(input_module, plugin):
    decoder = input_module.DECODERS["8045"]
    decoder.side_effect = RuntimeError("boom")

    input_module._decode_message(plugin, "8045", {}, "raw", "data", "ff")

    plugin.log.logging.assert_called()

    decoder.side_effect = None


# ---------------------------------------------------------------------------
# Tests: DECODERS integrity
# ---------------------------------------------------------------------------

def test_8002_not_in_decoders(input_module):
    assert "8002" not in input_module.DECODERS


def test_8011_not_in_decoders(input_module):
    assert "8011" not in input_module.DECODERS


def test_decoder_keys_format(input_module):
    import re
    pattern = re.compile(r"^[0-9a-f]{4}$")

    for key in input_module.DECODERS:
        assert pattern.match(key)


def test_decoder_values_callable(input_module):
    for decoder in input_module.DECODERS.values():
        assert callable(decoder)


def test_8139_alias(input_module):
    assert input_module.DECODERS["8139"] is input_module.DECODERS["8140"]