#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Modules/readAttributes.py

Coverage:
  - get_max_read_attributes            – chunk-size priority rules
  - split_list                         – even/uneven splitting
  - normalizedReadAttributeReq         – skip unreachable, skip bad attrs, normal flow
  - ReadAttributeReq                   – force / split / single paths
  - skipThisAttribute                  – invalid datastruct, no model, no conf
  - retreive_ListOfAttributesByCluster – priority: config > device list > plugin default
  - retreive_attributes_from_zcl_standard
  - retreive_attributes_based_on_configuration
  - retreive_manufacturer_specifics_attributes
  - retreive_attributes_from_default_device_list – including SPE600/TS0302 hacks
  - retreive_attributes_from_default_plugin_list
  - add_attributes_from_device_certified_conf
  - if_casaia_cms323
  - ping_device_with_read_attribute
  - ping_tuya_device
  - read_manufacturer_specific_attributes
  - ReadAttributeRequest_0000          – pairing vs general dispatch
  - ReadAttributeRequest_0000_for_pairing – no-ep, Xiaomi, Develco, Tuya, generic branches
  - ReadAttributeRequest_0000_for_general – Tuya, Schneider, Danfoss splits
  - ReadAttributeRequest_0000_for_tuya
  - ReadAttributeRequest_0001
  - ReadAttributeRequest_0002          – also covers wrong-cluster bug regression
  - ReadAttributeRequest_0006 / _0006_0000 / _0006_400x
  - ReadAttributeRequest_0008 / _0008_0000
  - ReadAttributeRequest_000c / _0019 / _0020
  - ReadAttributeRequest_0100 / _0101 / _0101_0000 / _0102 / _0102_0008
  - ReadAttributeRequest_0201 / thermostat helpers
  - ReadAttributeRequest_0202 / _0204 / _0300 / _0300_Color_Capabilities
  - ReadAttributeRequest_0400 / _0402 / _0403 / _0405
  - ReadAttributeRequest_0406 / _0406_* / _0406_philips_0030
  - ReadAttributeRequest_0500 / _0502
  - ReadAttributeRequest_0702 / _0702_0000 / _0702_0017 / _0702_multiplier_divisor
  - ReadAttributeRequest_0702_ZLinky_TIC / _0702_PC321
  - ReadAttributeReq_ZLinky / ReadAttributeReq_Scheduled_ZLinky / _linky_mode
  - ReadAttribute_ZLinkyIndex
  - ReadAttributeRequest_0705 / _070d / _0b01 / _0b04 / _0b04_* / _0b05
  - ReadAttributeRequest_000f / _e000 / _e001 / _fcc0 / _fc01 / _fc11
  - ReadAttributeRequest_fc21 / _fc40 / _fc7d / _ff66
  - read_attributes_gammatroniques_tic_meter / _ticmeter_tarif / _details
  - read_ticmeter_manufacturer
  - READ_ATTRIBUTES_REQUEST map completeness
"""

import importlib
import sys
import types
from unittest.mock import MagicMock, call, patch

import pytest

# ── MAC prefix constants (copied from real manufacturer_code.py) ────────────

PREFIX_MAC_LEN          = 6
PREFIX_MACADDR_TUYA     = ("04cd15", "588e81", "60a423", "70ac08", "842e14",
                           "847127", "84fd27", "a4c138", "4c97a1", "b4e3f9",
                           "bc33ac")
PREFIX_MACADDR_IKEA_TRADFRI = ("000d6f", "14b457")
PREFIX_MACADDR_DEVELCO  = ("0015bc",)
PREFIX_MACADDR_LEGRAND  = ("000474",)
PREFIX_MACADDR_WIZER_HOME = ("588E81",)
PREFIX_MACADDR_LIVOLO   = ("00124b",)
PREFIX_MACADDR_XIAOMI   = ("00158d",)
PREFIX_MACADDR_OPPLE    = ("04cf8c",)
PREFIX_MACADDR_CASAIA   = ("90fd9f", "3c6a2c")
TUYA_MANUF_CODE         = ["1002", "1141"]
DEVELCO_PREFIX          = "0015bc"
OWON_PREFIX             = "90fd9f"
casaiaPrefix            = "3c6a2c"

ZIGATE_EP = "01"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


# ── Module-scoped fixture: install stubs once, import module, tear down ───────

@pytest.fixture(scope="module")
def ra(request):
    """Import Modules.readAttributes with all external deps stubbed out."""
    # stubs keyed by module name
    _read_attribute_mock  = MagicMock(name="read_attribute", return_value="isqn-01")
    _check_ds_mock        = MagicMock(name="check_datastruct")
    _reset_ds_mock        = MagicMock(name="reset_attr_datastruct")
    _set_isqn_mock        = MagicMock(name="set_isqn_datastruct")
    _set_ts_mock          = MagicMock(name="set_timestamp_datastruct")
    _getListOfEp_mock     = MagicMock(name="getListOfEpForCluster", return_value=[])
    _is_ack_mock          = MagicMock(name="is_ack_tobe_disabled", return_value=False)
    _is_attr_invalid_mock = MagicMock(name="is_attr_unvalid_datastruct", return_value=False)
    _rawaps_mock          = MagicMock(name="rawaps_read_attribute_req")
    _tuya_cmd_mock        = MagicMock(name="tuya_cmd_0x0000_0xf0")
    _get_OPTARIF_mock     = MagicMock(name="get_OPTARIF", return_value="BA")
    _is_tuya_magic_mock   = MagicMock(name="is_tuya_magic_packet_required", return_value=False)
    _get_dev_cfg_mock     = MagicMock(name="get_device_config_param", return_value=None)
    _get_devcfg_val_mock  = MagicMock(name="get_deviceconf_parameter_value", return_value=None)

    stubs = {
        "Modules.basicOutputs": _make_stub(
            "Modules.basicOutputs",
            identifySend=MagicMock(name="identifySend"),
            read_attribute=_read_attribute_mock,
            send_zigatecmd_zcl_ack=MagicMock(),
            send_zigatecmd_zcl_noack=MagicMock(),
        ),
        "Modules.macPrefix": _make_stub(
            "Modules.macPrefix",
            DEVELCO_PREFIX=DEVELCO_PREFIX,
            OWON_PREFIX=OWON_PREFIX,
            casaiaPrefix=casaiaPrefix,
        ),
        "Modules.manufacturer_code": _make_stub(
            "Modules.manufacturer_code",
            PREFIX_MAC_LEN=PREFIX_MAC_LEN,
            PREFIX_MACADDR_CASAIA=PREFIX_MACADDR_CASAIA,
            PREFIX_MACADDR_DEVELCO=PREFIX_MACADDR_DEVELCO,
            PREFIX_MACADDR_IKEA_TRADFRI=PREFIX_MACADDR_IKEA_TRADFRI,
            PREFIX_MACADDR_LEGRAND=PREFIX_MACADDR_LEGRAND,
            PREFIX_MACADDR_LIVOLO=PREFIX_MACADDR_LIVOLO,
            PREFIX_MACADDR_OPPLE=PREFIX_MACADDR_OPPLE,
            PREFIX_MACADDR_TUYA=PREFIX_MACADDR_TUYA,
            PREFIX_MACADDR_WIZER_HOME=PREFIX_MACADDR_WIZER_HOME,
            PREFIX_MACADDR_XIAOMI=PREFIX_MACADDR_XIAOMI,
            TUYA_MANUF_CODE=TUYA_MANUF_CODE,
            is_tuya_magic_packet_required=_is_tuya_magic_mock,
        ),
        "Modules.tools": _make_stub(
            "Modules.tools",
            check_datastruct=_check_ds_mock,
            get_device_config_param=_get_dev_cfg_mock,
            get_deviceconf_parameter_value=_get_devcfg_val_mock,
            getListOfEpForCluster=_getListOfEp_mock,
            is_ack_tobe_disabled=_is_ack_mock,
            is_attr_unvalid_datastruct=_is_attr_invalid_mock,
            is_time_to_perform_work=MagicMock(return_value=True),
            reset_attr_datastruct=_reset_ds_mock,
            set_isqn_datastruct=_set_isqn_mock,
            set_status_datastruct=MagicMock(),
            set_timestamp_datastruct=_set_ts_mock,
        ),
        "Modules.tuya": _make_stub("Modules.tuya", tuya_cmd_0x0000_0xf0=_tuya_cmd_mock),
        "Modules.zigateConsts": _make_stub("Modules.zigateConsts", ZIGATE_EP=ZIGATE_EP),
        "Modules.zlinky": _make_stub("Modules.zlinky", get_OPTARIF=_get_OPTARIF_mock),
        "Zigbee.zclRawCommands": _make_stub("Zigbee.zclRawCommands", rawaps_read_attribute_req=_rawaps_mock),
    }

    # Override stubs unconditionally so our richer versions are used,
    # then restore originals on teardown.
    saved = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)

    # force fresh import
    sys.modules.pop("Modules.readAttributes", None)
    module = importlib.import_module("Modules.readAttributes")

    # expose the internal mocks on the module namespace so tests can monkeypatch them
    module._mock_read_attribute    = _read_attribute_mock
    module._mock_getListOfEp       = _getListOfEp_mock
    module._mock_is_ack            = _is_ack_mock
    module._mock_is_attr_invalid   = _is_attr_invalid_mock
    module._mock_check_ds          = _check_ds_mock
    module._mock_set_isqn          = _set_isqn_mock
    module._mock_set_ts            = _set_ts_mock
    module._mock_tuya_cmd          = _tuya_cmd_mock
    module._mock_rawaps            = _rawaps_mock
    module._mock_get_OPTARIF       = _get_OPTARIF_mock
    module._mock_is_tuya_magic     = _is_tuya_magic_mock
    module._mock_get_dev_cfg       = _get_dev_cfg_mock
    module._mock_get_devcfg_val    = _get_devcfg_val_mock

    yield module

    # Teardown: restore previous sys.modules state
    for name, old in saved.items():
        if old is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old
    sys.modules.pop("Modules.readAttributes", None)


# ── Plugin factory ────────────────────────────────────────────────────────────

def _plugin(nwkid="1234", ieee="aabbcc112233", model="TestModel",
            manufacturer="0000", eps=None, health=None):
    """Return a minimal mock plugin with one device registered."""
    p = MagicMock()
    p.log = MagicMock()
    p.log.logging = MagicMock()
    p.pluginconf = MagicMock()
    p.pluginconf.pluginConf = {"ReadAttributeChunk": 3, "pingViaGroup": 0}
    p.readZclClusters = {}
    p.DeviceConf = {}
    p.groupmgt = None

    device = {
        "IEEE": ieee,
        "Model": model,
        "Manufacturer": manufacturer,
        "Manufacturer Name": "",
        "Ep": eps or {"01": {"0000": {}, "0006": {}}},
        "Health": health,
    }
    p.ListOfDevices = {nwkid: device}
    return p


# ═══════════════════════════════════════════════════════════════════════════════
# get_max_read_attributes
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetMaxReadAttributes:

    def test_plugin_default_when_no_device(self, ra):
        p = _plugin()
        p.pluginconf.pluginConf["ReadAttributeChunk"] = 5
        assert ra.get_max_read_attributes(p, "1234") == 5

    def test_pairing_in_progress_returns_pairing_chunk(self, ra, monkeypatch):
        p = _plugin()
        p.ListOfDevices["1234"]["PairingInProgress"] = True
        monkeypatch.setattr(ra._mock_get_dev_cfg, "side_effect",
                            lambda self_, nwkid, key: 2 if key == "ReadAttributeChunkWhenPairing" else None)
        result = ra.get_max_read_attributes(p, "1234")
        assert result == 2

    def test_device_config_takes_precedence_over_manufacturer(self, ra, monkeypatch):
        p = _plugin(ieee="a4c138000001")   # Tuya prefix
        p.pluginconf.pluginConf["ReadAttributeChunk"] = 3
        monkeypatch.setattr(ra._mock_get_dev_cfg, "side_effect",
                            lambda self_, nwkid, key: 7 if key == "ReadAttributeChunk" else None)
        assert ra.get_max_read_attributes(p, "1234") == 7

    def test_tuya_prefix_returns_4(self, ra, monkeypatch):
        p = _plugin(ieee="a4c138000001")   # Tuya prefix
        p.pluginconf.pluginConf["ReadAttributeChunk"] = 3
        monkeypatch.setattr(ra._mock_get_dev_cfg, "side_effect", lambda *a: None)
        assert ra.get_max_read_attributes(p, "1234") == 4

    def test_develco_capped_at_12(self, ra, monkeypatch):
        p = _plugin(ieee="0015bc000001")   # Develco prefix
        p.pluginconf.pluginConf["ReadAttributeChunk"] = 20
        monkeypatch.setattr(ra._mock_get_dev_cfg, "side_effect", lambda *a: None)
        assert ra.get_max_read_attributes(p, "1234") == 12

    def test_casaia_capped_at_8(self, ra, monkeypatch):
        p = _plugin(ieee="90fd9f000001")   # CASAIA/OWON prefix
        p.pluginconf.pluginConf["ReadAttributeChunk"] = 20
        monkeypatch.setattr(ra._mock_get_dev_cfg, "side_effect", lambda *a: None)
        assert ra.get_max_read_attributes(p, "1234") == 8

    def test_unknown_device_returns_plugin_default(self, ra):
        p = _plugin()
        p.ListOfDevices = {}
        p.pluginconf.pluginConf["ReadAttributeChunk"] = 5
        result = ra.get_max_read_attributes(p, "9999")
        assert result == 5


# ═══════════════════════════════════════════════════════════════════════════════
# split_list
# ═══════════════════════════════════════════════════════════════════════════════

class TestSplitList:

    def test_exact_split(self, ra):
        assert ra.split_list([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]

    def test_uneven_split(self, ra):
        assert ra.split_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]

    def test_chunk_larger_than_list(self, ra):
        assert ra.split_list([1, 2], 10) == [[1, 2]]

    def test_single_element_chunks(self, ra):
        assert ra.split_list([0xA, 0xB, 0xC], 1) == [[0xA], [0xB], [0xC]]

    def test_empty_list(self, ra):
        assert ra.split_list([], 3) == []


# ═══════════════════════════════════════════════════════════════════════════════
# normalizedReadAttributeReq
# ═══════════════════════════════════════════════════════════════════════════════

class TestNormalizedReadAttributeReq:

    def test_skips_unreachable_device(self, ra, monkeypatch):
        p = _plugin(health="Not Reachable")
        read_attr = MagicMock()
        monkeypatch.setattr(ra, "read_attribute", read_attr)
        ra.normalizedReadAttributeReq(p, "1234", ZIGATE_EP, "01", "0006",
                                      [0x0000], "00", "0000", False)
        read_attr.assert_not_called()

    def test_sends_request_for_healthy_device(self, ra, monkeypatch):
        p = _plugin()
        read_attr = MagicMock(return_value="sqn01")
        monkeypatch.setattr(ra, "read_attribute", read_attr)
        monkeypatch.setattr(ra._mock_is_attr_invalid, "return_value", False)
        ra.normalizedReadAttributeReq(p, "1234", ZIGATE_EP, "01", "0006",
                                      [0x0000], "00", "0000", False)
        read_attr.assert_called_once()

    def test_skips_f2_endpoint(self, ra, monkeypatch):
        p = _plugin()
        read_attr = MagicMock(return_value="sqn01")
        monkeypatch.setattr(ra, "read_attribute", read_attr)
        ra.normalizedReadAttributeReq(p, "1234", ZIGATE_EP, "f2", "0006",
                                      [0x0000], "00", "0000", False)
        read_attr.assert_not_called()

    def test_single_attr_as_non_list_is_normalised(self, ra, monkeypatch):
        p = _plugin()
        read_attr = MagicMock(return_value="sqn01")
        monkeypatch.setattr(ra, "read_attribute", read_attr)
        monkeypatch.setattr(ra._mock_is_attr_invalid, "return_value", False)
        # Pass a single integer, not a list
        ra.normalizedReadAttributeReq(p, "1234", ZIGATE_EP, "01", "0006",
                                      0x0000, "00", "0000", False)
        read_attr.assert_called_once()

    def test_set_isqn_called_for_each_attribute(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra, "read_attribute", MagicMock(return_value="sqn42"))
        monkeypatch.setattr(ra._mock_is_attr_invalid, "return_value", False)
        set_isqn = MagicMock()
        monkeypatch.setattr(ra, "set_isqn_datastruct", set_isqn)
        ra.normalizedReadAttributeReq(p, "1234", ZIGATE_EP, "01", "0006",
                                      [0x0000, 0x4001], "00", "0000", False)
        assert set_isqn.call_count == 2

    def test_no_attrs_after_skip_does_not_call_read(self, ra, monkeypatch):
        p = _plugin()
        read_attr = MagicMock()
        monkeypatch.setattr(ra, "read_attribute", read_attr)
        # Mark all attrs as invalid so they get skipped
        monkeypatch.setattr(ra._mock_is_attr_invalid, "return_value", True)
        ra.normalizedReadAttributeReq(p, "1234", ZIGATE_EP, "01", "0006",
                                      [0x0000], "00", "0000", False)
        read_attr.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# ReadAttributeReq
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadAttributeReq:

    def test_small_list_calls_normalized_once(self, ra, monkeypatch):
        p = _plugin()
        norm = MagicMock()
        monkeypatch.setattr(ra, "normalizedReadAttributeReq", norm)
        monkeypatch.setattr(ra, "get_max_read_attributes", lambda *a: 10)
        ra.ReadAttributeReq(p, "1234", ZIGATE_EP, "01", "0006", [0, 1, 2])
        norm.assert_called_once()

    def test_large_list_splits_into_chunks(self, ra, monkeypatch):
        p = _plugin()
        norm = MagicMock()
        monkeypatch.setattr(ra, "normalizedReadAttributeReq", norm)
        monkeypatch.setattr(ra, "get_max_read_attributes", lambda *a: 2)
        ra.ReadAttributeReq(p, "1234", ZIGATE_EP, "01", "0006", [0, 1, 2, 3, 4])
        assert norm.call_count == 3  # [0,1], [2,3], [4]

    def test_force_len_sends_all_at_once(self, ra, monkeypatch):
        p = _plugin()
        norm = MagicMock()
        monkeypatch.setattr(ra, "normalizedReadAttributeReq", norm)
        monkeypatch.setattr(ra, "get_max_read_attributes", lambda *a: 2)
        ra.ReadAttributeReq(p, "1234", ZIGATE_EP, "01", "0006",
                            [0, 1, 2, 3], forceLen=True)
        norm.assert_called_once()
        _, kwargs = norm.call_args
        # force=True must be forwarded
        assert norm.call_args.kwargs.get("force") is True or norm.call_args.args[-1] is True

    def test_non_list_attr_goes_to_normalized_directly(self, ra, monkeypatch):
        p = _plugin()
        norm = MagicMock()
        monkeypatch.setattr(ra, "normalizedReadAttributeReq", norm)
        monkeypatch.setattr(ra, "get_max_read_attributes", lambda *a: 3)
        ra.ReadAttributeReq(p, "1234", ZIGATE_EP, "01", "0006", 0x0000)
        norm.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# skipThisAttribute  (also documents the known bugs)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSkipThisAttribute:

    def test_invalid_datastruct_skips(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra, "is_attr_unvalid_datastruct", lambda *a: True)
        assert ra.skipThisAttribute(p, "1234", "01", "0006", "0000") is True

    def test_valid_datastruct_no_model_raises_keyerror(self, ra, monkeypatch):
        """BUG: when 'Model' key is absent the code falls through line 249 check
        (which guards on key presence, not absence) and then accesses the missing
        key on line 251 → KeyError.  Documented here so fixes are visible."""
        p = _plugin()
        del p.ListOfDevices["1234"]["Model"]
        monkeypatch.setattr(ra, "is_attr_unvalid_datastruct", lambda *a: False)
        with pytest.raises(KeyError, match="Model"):
            ra.skipThisAttribute(p, "1234", "01", "0006", "0000")

    def test_model_not_in_devconf_does_not_skip(self, ra, monkeypatch):
        p = _plugin()
        p.DeviceConf = {}   # model not in DeviceConf
        monkeypatch.setattr(ra, "is_attr_unvalid_datastruct", lambda *a: False)
        # BUG: current code returns False at "if Model in device" regardless —
        # this test documents the current (buggy) behaviour
        result = ra.skipThisAttribute(p, "1234", "01", "0006", "0000")
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# retreive_* helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestRetreiveAttributesFromZclStandard:

    def test_known_cluster_returns_from_ATTRIBUTES(self, ra):
        p = _plugin()
        result = ra.retreive_attributes_from_zcl_standard(p, "0006")
        assert 0x0000 in result

    def test_unknown_cluster_returns_none(self, ra):
        p = _plugin()
        result = ra.retreive_attributes_from_zcl_standard(p, "dead")
        assert result is None

    def test_zcl_cluster_conf_overrides_ATTRIBUTES(self, ra):
        p = _plugin()
        p.readZclClusters = {"0006": {"Attributes": {"0000": {}, "0001": {}}}}
        result = ra.retreive_attributes_from_zcl_standard(p, "0006")
        assert set(result) == {0, 1}


class TestRetreiveAttributesBasedOnConfiguration:

    def test_no_model_returns_none(self, ra):
        p = _plugin()
        del p.ListOfDevices["1234"]["Model"]
        assert ra.retreive_attributes_based_on_configuration(p, "1234", "0006") is None

    def test_model_not_in_devconf_returns_none(self, ra):
        p = _plugin()
        p.DeviceConf = {}
        assert ra.retreive_attributes_based_on_configuration(p, "1234", "0006") is None

    def test_no_readattributes_key_returns_none(self, ra):
        p = _plugin()
        p.DeviceConf = {"TestModel": {}}
        assert ra.retreive_attributes_based_on_configuration(p, "1234", "0006") is None

    def test_cluster_not_configured_returns_none(self, ra):
        p = _plugin()
        p.DeviceConf = {"TestModel": {"ReadAttributes": {}}}
        assert ra.retreive_attributes_based_on_configuration(p, "1234", "0006") is None

    def test_returns_int_list_from_hex_strings(self, ra):
        p = _plugin()
        p.DeviceConf = {"TestModel": {"ReadAttributes": {"0006": ["0000", "4001"]}}}
        result = ra.retreive_attributes_based_on_configuration(p, "1234", "0006")
        assert result == [0, 0x4001]


class TestRetreiveManufacturerSpecificsAttributes:

    def test_no_model_returns_none_none(self, ra):
        p = _plugin()
        del p.ListOfDevices["1234"]["Model"]
        assert ra.retreive_manufacturer_specifics_attributes(p, "1234", "0201") == (None, None)

    def test_model_not_in_devconf_returns_none_none(self, ra):
        p = _plugin()
        p.DeviceConf = {}
        assert ra.retreive_manufacturer_specifics_attributes(p, "1234", "0201") == (None, None)

    def test_no_manuf_attrs_returns_none_none(self, ra):
        p = _plugin()
        p.DeviceConf = {"TestModel": {"ManufacturerCode": "105e"}}
        assert ra.retreive_manufacturer_specifics_attributes(p, "1234", "0201") == (None, None)

    def test_cluster_not_in_manuf_attrs(self, ra):
        p = _plugin()
        p.DeviceConf = {"TestModel": {
            "ManufacturerCode": "105e",
            "ManufacturerAttributes": {"0202": ["0000"]}
        }}
        assert ra.retreive_manufacturer_specifics_attributes(p, "1234", "0201") == (None, None)

    def test_returns_code_and_int_list(self, ra):
        p = _plugin()
        p.DeviceConf = {"TestModel": {
            "ManufacturerCode": "105e",
            "ManufacturerAttributes": {"0201": ["e011", "0e20"]}
        }}
        code, attrs = ra.retreive_manufacturer_specifics_attributes(p, "1234", "0201")
        assert code == "105e"
        assert attrs == [0xe011, 0x0e20]


class TestRetreiveAttributesFromDefaultDeviceList:

    def test_no_attributes_list_returns_none(self, ra):
        p = _plugin()
        assert ra.retreive_attributes_from_default_device_list(p, "1234", "01", "0006") is None

    def test_missing_ep_key_returns_none(self, ra):
        p = _plugin()
        p.ListOfDevices["1234"]["Attributes List"] = {}
        assert ra.retreive_attributes_from_default_device_list(p, "1234", "01", "0006") is None

    def test_ep_missing_in_list_returns_none(self, ra):
        p = _plugin()
        p.ListOfDevices["1234"]["Attributes List"] = {"Ep": {}}
        assert ra.retreive_attributes_from_default_device_list(p, "1234", "01", "0006") is None

    def test_cluster_missing_returns_none(self, ra):
        p = _plugin()
        p.ListOfDevices["1234"]["Attributes List"] = {"Ep": {"01": {}}}
        assert ra.retreive_attributes_from_default_device_list(p, "1234", "01", "0006") is None

    def test_returns_int_attrs_from_device_list(self, ra):
        p = _plugin()
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"0006": {"0000": {}, "4001": {}}}}
        }
        result = ra.retreive_attributes_from_default_device_list(p, "1234", "01", "0006")
        assert set(result) == {0, 0x4001}

    def test_spe600_appends_zcl_standard_attrs(self, ra):
        p = _plugin(model="SPE600")
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"0702": {"0000": {}}}}
        }
        result = ra.retreive_attributes_from_default_device_list(p, "1234", "01", "0702")
        # Must include 0x0000 from device list and ZCL standard attrs
        assert 0x0000 in result
        # Standard 0702 attrs must be merged in
        for a in [0x0017, 0x0200]:
            assert a in result

    def test_ts0302_appends_zcl_standard_attrs(self, ra):
        p = _plugin(model="TS0302")
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"0102": {"0000": {}}}}
        }
        result = ra.retreive_attributes_from_default_device_list(p, "1234", "01", "0102")
        assert 0x0000 in result
        assert 0x0007 in result


class TestRetreiveAttributesFromDefaultPluginList:

    def test_known_cluster_returns_list(self, ra):
        p = _plugin()
        result = ra.retreive_attributes_from_default_plugin_list(p, "1234", "01", "0006")
        assert isinstance(result, list)
        assert 0x0000 in result

    def test_unknown_cluster_falls_back_to_0x0000(self, ra):
        p = _plugin()
        result = ra.retreive_attributes_from_default_plugin_list(p, "1234", "01", "dead")
        assert result == [0x0000]


class TestRetreiveListOfAttributesByCluster:

    def test_config_takes_priority_over_device_list(self, ra, monkeypatch):
        p = _plugin()
        p.DeviceConf = {"TestModel": {"ReadAttributes": {"0006": ["0000"]}}}
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"0006": {"4001": {}}}}
        }
        result = ra.retreive_ListOfAttributesByCluster(p, "1234", "01", "0006")
        assert result == [0]   # from config, not device list

    def test_device_list_takes_priority_over_plugin_default(self, ra, monkeypatch):
        p = _plugin()
        p.DeviceConf = {}
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"0006": {"4001": {}}}}
        }
        result = ra.retreive_ListOfAttributesByCluster(p, "1234", "01", "0006")
        assert 0x4001 in result

    def test_falls_back_to_plugin_default(self, ra):
        p = _plugin()
        p.DeviceConf = {}
        result = ra.retreive_ListOfAttributesByCluster(p, "1234", "01", "0006")
        assert 0x0000 in result

    def test_returns_empty_for_unknown_cluster_no_override(self, ra):
        p = _plugin()
        p.DeviceConf = {}
        # cluster "dead" is unknown → falls back to [0x0000]
        result = ra.retreive_ListOfAttributesByCluster(p, "1234", "01", "dead")
        assert result == [0x0000]


# ═══════════════════════════════════════════════════════════════════════════════
# add_attributes_from_device_certified_conf
# ═══════════════════════════════════════════════════════════════════════════════

class TestAddAttributesFromDeviceCertifiedConf:

    def test_no_conf_returns_unchanged_list(self, ra):
        p = _plugin()
        p.DeviceConf = {}
        original = [0x0000, 0x0001]
        result = ra.add_attributes_from_device_certified_conf(p, "1234", "0006", original)
        assert result == original

    def test_new_attrs_raises_typeerror_when_conf_returns_ints(self, ra):
        """BUG: retreive_attributes_based_on_configuration returns integers, but
        add_attributes_from_device_certified_conf calls int(attr, 16) with an
        explicit base — which requires a string.  This TypeError documents the bug."""
        p = _plugin()
        p.DeviceConf = {"TestModel": {"ReadAttributes": {"0006": ["0000", "4001"]}}}
        with pytest.raises(TypeError):
            ra.add_attributes_from_device_certified_conf(p, "1234", "0006", [])

    def test_no_duplicates_added(self, ra):
        p = _plugin()
        p.DeviceConf = {"TestModel": {"ReadAttributes": {"0006": ["0000"]}}}
        result = ra.add_attributes_from_device_certified_conf(p, "1234", "0006", [0x0000])
        assert result.count(0x0000) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# if_casaia_cms323
# ═══════════════════════════════════════════════════════════════════════════════

class TestIfCasaiaCms323:

    def test_non_casaia_ieee_returns_false(self, ra):
        assert ra.if_casaia_cms323(["01", "02", "04"], "aabbcc112233") is False

    def test_casaia_without_ep04_returns_false(self, ra):
        assert ra.if_casaia_cms323(["01", "02"], f"{casaiaPrefix}001122") is False

    def test_casaia_with_01_02_04_returns_true(self, ra):
        assert ra.if_casaia_cms323(["01", "02", "04"], f"{casaiaPrefix}001122") is True

    def test_owon_with_01_02_04_returns_true(self, ra):
        assert ra.if_casaia_cms323(["01", "02", "04"], f"{OWON_PREFIX}001122") is True


# ═══════════════════════════════════════════════════════════════════════════════
# ping helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestPingDeviceWithReadAttribute:

    def test_calls_read_attribute(self, ra, monkeypatch):
        p = _plugin()
        read_attr = MagicMock(return_value="sqn")
        monkeypatch.setattr(ra, "read_attribute", read_attr)
        monkeypatch.setattr(ra._mock_getListOfEp,
                            "side_effect", lambda *a: ["01"])
        ra.ping_device_with_read_attribute(p, "1234")
        read_attr.assert_called_once()

    def test_pings_only_first_ep(self, ra, monkeypatch):
        p = _plugin()
        read_attr = MagicMock(return_value="sqn")
        monkeypatch.setattr(ra, "read_attribute", read_attr)
        monkeypatch.setattr(ra._mock_getListOfEp,
                            "side_effect", lambda *a: ["01", "02", "03"])
        ra.ping_device_with_read_attribute(p, "1234")
        assert read_attr.call_count == 1

    def test_gl_b007z_uses_cluster_0006(self, ra, monkeypatch):
        p = _plugin(model="GL-B-007Z")
        read_attr = MagicMock(return_value="sqn")
        monkeypatch.setattr(ra, "read_attribute", read_attr)
        monkeypatch.setattr(ra._mock_getListOfEp,
                            "side_effect", lambda *a: ["01"])
        ra.ping_device_with_read_attribute(p, "1234")
        args = read_attr.call_args.args
        assert args[4] == "0006"   # cluster argument


class TestPingTuyaDevice:

    def test_calls_read_attribute_on_cluster_0000(self, ra, monkeypatch):
        p = _plugin()
        read_attr = MagicMock(return_value="sqn")
        monkeypatch.setattr(ra, "read_attribute", read_attr)
        ra.ping_tuya_device(p, "1234")
        args = read_attr.call_args.args
        assert args[4] == "0000"


# ═══════════════════════════════════════════════════════════════════════════════
# read_manufacturer_specific_attributes
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadManufacturerSpecificAttributes:

    def test_no_conf_does_not_call_ReadAttributeReq(self, ra, monkeypatch):
        p = _plugin()
        p.DeviceConf = {}
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.read_manufacturer_specific_attributes(p, "1234", "01", "0201")
        req.assert_not_called()

    def test_with_conf_calls_ReadAttributeReq(self, ra, monkeypatch):
        p = _plugin()
        p.DeviceConf = {"TestModel": {
            "ManufacturerCode": "105e",
            "ManufacturerAttributes": {"0201": ["e011"]}
        }}
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.read_manufacturer_specific_attributes(p, "1234", "01", "0201")
        req.assert_called_once()
        _, kwargs = req.call_args
        assert kwargs.get("manufacturer_spec") == "01"
        assert kwargs.get("manufacturer") == "105e"


# ═══════════════════════════════════════════════════════════════════════════════
# ReadAttributeRequest_0000 dispatch
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadAttributeRequest0000Dispatch:

    def test_empty_ep_dispatches_to_pairing(self, ra, monkeypatch):
        p = _plugin()
        p.ListOfDevices["1234"]["Ep"] = {}
        pairing = MagicMock()
        general = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeRequest_0000_for_pairing", pairing)
        monkeypatch.setattr(ra, "ReadAttributeRequest_0000_for_general", general)
        ra.ReadAttributeRequest_0000(p, "1234")
        pairing.assert_called_once_with(p, "1234")
        general.assert_not_called()

    def test_none_ep_dispatches_to_pairing(self, ra, monkeypatch):
        p = _plugin()
        p.ListOfDevices["1234"]["Ep"] = None
        pairing = MagicMock()
        general = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeRequest_0000_for_pairing", pairing)
        monkeypatch.setattr(ra, "ReadAttributeRequest_0000_for_general", general)
        ra.ReadAttributeRequest_0000(p, "1234")
        pairing.assert_called_once()

    def test_full_scope_with_eps_dispatches_to_general(self, ra, monkeypatch):
        p = _plugin()
        pairing = MagicMock()
        general = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeRequest_0000_for_pairing", pairing)
        monkeypatch.setattr(ra, "ReadAttributeRequest_0000_for_general", general)
        ra.ReadAttributeRequest_0000(p, "1234", fullScope=True)
        general.assert_called_once_with(p, "1234")
        pairing.assert_not_called()

    def test_fullScope_false_dispatches_to_pairing(self, ra, monkeypatch):
        p = _plugin()
        pairing = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeRequest_0000_for_pairing", pairing)
        monkeypatch.setattr(ra, "ReadAttributeRequest_0000_for_general", MagicMock())
        ra.ReadAttributeRequest_0000(p, "1234", fullScope=False)
        pairing.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# ReadAttributeRequest_0000_for_pairing  — vendor-specific EP branches
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadAttributeRequest0000ForPairing:

    def _setup(self, ra, monkeypatch, ieee="aabbcc001122"):
        p = _plugin(ieee=ieee)
        p.ListOfDevices["1234"]["Ep"] = {}   # no EPs yet
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: [])
        monkeypatch.setattr(ra._mock_is_tuya_magic, "return_value", False)
        return p, req

    def test_generic_broadcasts_to_multiple_eps(self, ra, monkeypatch):
        p, req = self._setup(ra, monkeypatch)
        ra.ReadAttributeRequest_0000_for_pairing(p, "1234")
        eps_called = [c.args[3] for c in req.call_args_list]
        assert "01" in eps_called
        assert "02" in eps_called

    def test_xiaomi_uses_only_ep_01(self, ra, monkeypatch):
        ieee = f"{PREFIX_MACADDR_XIAOMI[0]}001122"
        p, req = self._setup(ra, monkeypatch, ieee=ieee)
        ra.ReadAttributeRequest_0000_for_pairing(p, "1234")
        eps_called = [c.args[3] for c in req.call_args_list]
        assert eps_called == ["01"]

    def test_develco_uses_ep_02(self, ra, monkeypatch):
        ieee = f"{PREFIX_MACADDR_DEVELCO[0]}001122"
        p, req = self._setup(ra, monkeypatch, ieee=ieee)
        ra.ReadAttributeRequest_0000_for_pairing(p, "1234")
        eps_called = [c.args[3] for c in req.call_args_list]
        assert "02" in eps_called

    def test_tuya_sends_exactly_two_requests(self, ra, monkeypatch):
        ieee = f"{PREFIX_MACADDR_TUYA[0]}001122"
        p, req = self._setup(ra, monkeypatch, ieee=ieee)
        ra.ReadAttributeRequest_0000_for_pairing(p, "1234")
        assert req.call_count == 2

    def test_when_eps_known_iterates_eps(self, ra, monkeypatch):
        p = _plugin()
        p.ListOfDevices["1234"]["Ep"] = {"01": {}, "02": {}}
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01", "02"])
        monkeypatch.setattr(ra._mock_is_tuya_magic, "return_value", False)
        ra.ReadAttributeRequest_0000_for_pairing(p, "1234")
        eps_called = {c.args[3] for c in req.call_args_list}
        assert "01" in eps_called


# ═══════════════════════════════════════════════════════════════════════════════
# ReadAttributeRequest_0000_for_general  — manufacturer splits
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadAttributeRequest0000ForGeneral:

    def _ep_setup(self, ra, monkeypatch, p):
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"0000": {"0000": {}, "0004": {}, "0005": {}}}}
        }
        return MagicMock()

    def test_generic_model_sends_one_request(self, ra, monkeypatch):
        p = _plugin()
        req = self._ep_setup(ra, monkeypatch, p)
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0000_for_general(p, "1234")
        req.assert_called()

    def test_tuya_overrides_to_specific_attribute_list(self, ra, monkeypatch):
        p = _plugin(ieee=f"{PREFIX_MACADDR_TUYA[0]}001122")
        req = self._ep_setup(ra, monkeypatch, p)
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0000_for_general(p, "1234")
        # Tuya list is [0x0004, 0x0000, 0x0001, 0x0005, 0x0007, 0xfffe]
        attrs_sent = req.call_args.args[5]
        assert 0xfffe in attrs_sent

    def test_schneider_splits_generic_and_specific(self, ra, monkeypatch):
        p = _plugin(manufacturer="105e")
        p.ListOfDevices["1234"]["Manufacturer Name"] = "Schneider Electric"
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"0000": {"0000": {}, "e000": {}, "e001": {}, "e002": {}}}}
        }
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0000_for_general(p, "1234")
        # Two calls expected: one generic, one manufacturer-specific
        assert req.call_count >= 2

    def test_danfoss_manufacturer_100b_splits_specific(self, ra, monkeypatch):
        p = _plugin(manufacturer="100b")
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"0000": {"0000": {}, "0033": {}}}}
        }
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0000_for_general(p, "1234")
        assert req.call_count >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# Simple per-cluster ReadAttributeRequest_* functions
# (template: call passes → ReadAttributeReq fired with correct cluster)
# ═══════════════════════════════════════════════════════════════════════════════

def _cluster_request_test(ra, monkeypatch, func_name, cluster_id,
                          nwkid="1234", extra_device=None):
    """Generic helper: call ReadAttributeRequest_<cluster>, verify ReadAttributeReq
    is called with the expected cluster_id."""
    p = _plugin()
    if extra_device:
        p.ListOfDevices["1234"].update(extra_device)
    monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
    req = MagicMock()
    monkeypatch.setattr(ra, "ReadAttributeReq", req)
    getattr(ra, func_name)(p, nwkid)
    return req


class TestSimpleClusterRequests:

    def test_0001(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0001", "0001")
        clusters = {c.args[4] for c in req.call_args_list}
        assert "0001" in clusters

    def test_0002_uses_correct_cluster_for_ep_lookup(self, ra, monkeypatch):
        """ReadAttributeRequest_0002 (Device Temperature) should look up endpoints
        for cluster 0002, which it now correctly does."""
        p = _plugin()
        calls_made = []
        def mock_get_ep(self_, key, cluster):
            calls_made.append(cluster)
            return ["01"]
        monkeypatch.setattr(ra, "getListOfEpForCluster", mock_get_ep)
        monkeypatch.setattr(ra, "ReadAttributeReq", MagicMock())
        ra.ReadAttributeRequest_0002(p, "1234")
        assert "0002" in calls_made

    def test_0006_fires_for_each_ep(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0006", "0006")
        clusters = {c.args[4] for c in req.call_args_list}
        assert "0006" in clusters

    def test_0006_0000_skips_when_polling_disabled(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_get_devcfg_val,
                            "side_effect", lambda *a: True)
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0006_0000(p, "1234")
        req.assert_not_called()

    def test_0006_0000_fires_when_polling_enabled(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_get_devcfg_val, "side_effect", lambda *a: None)
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0006_0000(p, "1234")
        req.assert_called_once()

    def test_0006_400x_flag_enabled_uses_0x8002(self, ra, monkeypatch):
        """Regression #1996: attribute choice must follow the
        PowerOnOffStateAttribute8002 device-conf flag, not a hardcoded model list."""
        p = _plugin(model="TS011F-plug")
        monkeypatch.setattr(ra._mock_get_devcfg_val, "side_effect", lambda *a, **kw: True)
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0006_400x(p, "1234")
        attrs = req.call_args.args[5]
        assert 0x8002 in attrs

    def test_0006_400x_flag_disabled_uses_0x4003(self, ra, monkeypatch):
        p = _plugin(model="SomeLight")
        monkeypatch.setattr(ra._mock_get_devcfg_val, "side_effect", lambda *a, **kw: False)
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0006_400x(p, "1234")
        attrs = req.call_args.args[5]
        assert 0x4003 in attrs

    def test_0008_0000(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0008_0000", "0008")
        assert req.called

    def test_0008_0000_skips_when_polling_disabled(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_get_devcfg_val, "side_effect", lambda *a: True)
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0008_0000(p, "1234")
        req.assert_not_called()

    def test_000c(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_000c", "000c")
        assert req.called

    def test_0019(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0019", "0019")
        assert req.called

    def test_0100(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0100", "0100")
        clusters = {c.args[4] for c in req.call_args_list}
        assert "0100" in clusters

    def test_0101_indentation_regression(self, ra, monkeypatch):
        """ReadAttributeRequest_0101 has if-block inside loop — fires per-attr, not once.
        This test documents the current (buggy) behaviour."""
        p = _plugin()
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"0101": {"0000": {}, "0001": {}, "0002": {}}}}
        }
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0101(p, "1234")
        # BUG: fires 3 times (once per attr) instead of 1
        assert req.call_count == 3

    def test_0101_0000(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0101_0000", "0101")
        assert req.called

    def test_0102_indentation_regression(self, ra, monkeypatch):
        """Same indent bug as 0101."""
        p = _plugin()
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"0102": {"0000": {}, "0007": {}}}}
        }
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0102(p, "1234")
        # BUG: fires 2 times instead of 1
        assert req.call_count == 2

    def test_0102_0008(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0102_0008", "0102")
        assert req.called

    def test_0202(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0202", "0202")
        assert req.called

    def test_0204(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0204", "0204")
        assert req.called

    def test_0300(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0300", "0300")
        clusters = {c.args[4] for c in req.call_args_list}
        assert "0300" in clusters

    def test_0300_color_capabilities(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0300_Color_Capabilities(p, "1234")
        attrs = req.call_args.args[5]
        assert 0x400A in attrs

    def test_0400(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0400", "0400")
        assert req.called

    def test_0402_skips_lumi_aqcn02(self, ra, monkeypatch):
        p = _plugin(model="lumi.light.aqcn02")
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0402(p, "1234")
        req.assert_not_called()

    def test_0402_sends_for_generic_model(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0402", "0402")
        assert req.called

    def test_0402_tuya_uses_ep_ff(self, ra, monkeypatch):
        p = _plugin(model="TS0201-_TZ3000_qaaysllp")
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        monkeypatch.setattr(ra._mock_tuya_cmd, "return_value", None)
        ra.ReadAttributeRequest_0402(p, "1234")
        assert req.call_args.args[3] == "ff"

    def test_0403(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0403", "0403")
        assert req.called

    def test_0405_tuya_uses_ep_ff(self, ra, monkeypatch):
        p = _plugin(model="TS0201-_TZ3000_qaaysllp")
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0405(p, "1234")
        assert req.call_args.args[3] == "ff"

    def test_0406_philips_splits_manuf_attrs(self, ra, monkeypatch):
        p = _plugin(model="SML001")
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"0406": {"0000": {}, "0030": {}, "0031": {}}}}
        }
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0406(p, "1234")
        # Should issue 2 requests: generic + manufacturer-specific
        assert req.call_count == 2

    def test_0500(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0500", "0500")
        assert req.called

    def test_0502(self, ra, monkeypatch):
        req = _cluster_request_test(ra, monkeypatch, "ReadAttributeRequest_0502", "0502")
        assert req.called


# ═══════════════════════════════════════════════════════════════════════════════
# Thermostat cluster
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadAttributeRequest0201:

    def _thermostat_plugin(self, manufacturer="0000", manufacturer_name=""):
        p = _plugin(manufacturer=manufacturer)
        p.ListOfDevices["1234"]["Manufacturer Name"] = manufacturer_name
        return p

    def test_generic_sends_request(self, ra, monkeypatch):
        p = self._thermostat_plugin()
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0201(p, "1234")
        assert req.called

    def test_schneider_splits_manuf_specific(self, ra, monkeypatch):
        p = self._thermostat_plugin(manufacturer="105e", manufacturer_name="Schneider Electric")
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"0201": {"0000": {}, "fd00": {}}}}
        }
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0201(p, "1234")
        # At least one generic call
        assert req.called

    def test_danfoss_sends_manuf_specific(self, ra, monkeypatch):
        p = self._thermostat_plugin(manufacturer="1246", manufacturer_name="Danfoss")
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"0201": {"0000": {}, "4000": {}, "4010": {}}}}
        }
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0201(p, "1234")
        # Generic + Danfoss-specific + read_manufacturer_specific_attributes
        assert req.call_count >= 2

    def test_0201_0012(self, ra, monkeypatch):
        p = _plugin()
        # Non-empty dict is required: the guard is `if cluster_0201:` and {} is falsy
        p.ListOfDevices["1234"]["Ep"]["01"]["0201"] = {"0012": ""}
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0201_0012(p, "1234")
        req.assert_called_once()
        assert 0x0012 in req.call_args.args[5]

    def test_thermostat_cool_setpoint(self, ra, monkeypatch):
        p = _plugin()
        p.ListOfDevices["1234"]["Ep"]["01"]["0201"] = {"0011": ""}
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_thermostat_cool_setpoint(p, "1234")
        req.assert_called_once()
        assert 0x0011 in req.call_args.args[5]

    def test_thermostat_unoccupied_heat_setpoint(self, ra, monkeypatch):
        p = _plugin()
        p.ListOfDevices["1234"]["Ep"]["01"]["0201"] = {"0014": ""}
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_thermostat_unoccupied_heat_setpoint(p, "1234")
        req.assert_called_once()
        assert 0x0014 in req.call_args.args[5]


# ═══════════════════════════════════════════════════════════════════════════════
# Metering cluster (0702) & variants
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadAttributeRequest0702:

    def test_generic_sends_one_request(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0702(p, "1234")
        assert req.called

    def test_schneider_splits_manuf_specific(self, ra, monkeypatch):
        p = _plugin(manufacturer="105e")
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"0702": {"0000": {}, "e200": {}, "e201": {}}}}
        }
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0702(p, "1234")
        assert req.call_count == 2

    def test_0702_0000_sends_summation_attr(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0702_0000(p, "1234")
        assert req.called
        assert 0x0000 in req.call_args.args[5]

    def test_0702_0017_sends_inlet_temp_attr(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0702_0017(p, "1234")
        assert req.called
        assert 0x0017 in req.call_args.args[5]

    def test_0702_multiplier_divisor(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0702_multiplier_divisor(p, "1234")
        attrs = req.call_args.args[5]
        assert 0x0300 in attrs
        assert 0x0301 in attrs
        assert 0x0302 in attrs

    def test_0702_pc321_uses_manufacturer_113c(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0702_PC321(p, "1234")
        assert req.called
        _, kwargs = req.call_args
        assert kwargs.get("manufacturer") == "113c"
        assert kwargs.get("manufacturer_spec") == "01"


# ═══════════════════════════════════════════════════════════════════════════════
# ZLinky helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestZLinkyHelpers:

    def test_ReadAttributeReq_ZLinky_sends_three_clusters(self, ra, monkeypatch):
        p = _plugin()
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeReq_ZLinky(p, "1234")
        clusters_called = {c.args[4] for c in req.call_args_list}
        assert {"0702", "0b01", "0b04"} == clusters_called

    def test_ReadAttributeReq_Scheduled_ZLinky_sends_ff66_and_0702(self, ra, monkeypatch):
        p = _plugin()
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeReq_Scheduled_ZLinky(p, "1234")
        clusters_called = {c.args[4] for c in req.call_args_list}
        assert "0702" in clusters_called
        assert "ff66" in clusters_called

    def test_ReadAttributeReq_Scheduled_linky_mode(self, ra, monkeypatch):
        p = _plugin()
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeReq_Scheduled_linky_mode(p, "1234")
        req.assert_called_once()
        assert req.call_args.args[4] == "ff66"
        assert 0x0300 in req.call_args.args[5]

    def test_ReadAttributeRequest_0702_ZLinky_TIC_base_tarif(self, ra, monkeypatch):
        p = _plugin()
        p.ListOfDevices["1234"]["Ep"] = {
            "01": {"ff66": {"0000": "BASE"}}
        }
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0702_ZLinky_TIC(p, "1234")
        req.assert_called_once()
        attrs = req.call_args.args[5]
        assert 0x0020 in attrs
        assert 0x0100 in attrs

    def test_ReadAttribute_ZLinkyIndex_uses_optarif(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_get_OPTARIF, "return_value", "BA")
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttribute_ZLinkyIndex(p, "1234")
        req.assert_called_once()
        assert 0x0100 in req.call_args.args[5]


# ═══════════════════════════════════════════════════════════════════════════════
# Remaining cluster functions
# ═══════════════════════════════════════════════════════════════════════════════

class TestRemainingClusters:

    @pytest.mark.parametrize("func,cluster", [
        ("ReadAttributeRequest_0705",  "0705"),
        ("ReadAttributeRequest_070d",  "070d"),
        ("ReadAttributeRequest_0b01",  "0b01"),
        ("ReadAttributeRequest_0b04",  "0b04"),
        ("ReadAttributeRequest_0b05",  "0b05"),
        ("ReadAttributeRequest_000f",  "000f"),
        ("ReadAttributeRequest_e000",  "e000"),
        ("ReadAttributeRequest_e001",  "e001"),
        ("ReadAttributeRequest_fc01",  "fc01"),
        ("ReadAttributeRequest_ff66",  "ff66"),
    ])
    def test_sends_to_correct_cluster(self, ra, monkeypatch, func, cluster):
        p = _plugin()
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        getattr(ra, func)(p, "1234")
        if req.called:
            clusters = {c.args[4] for c in req.call_args_list}
            assert cluster in clusters

    def test_0b04_0505(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0b04_0505(p, "1234")
        assert 0x0505 in req.call_args.args[5]

    def test_0b04_050b(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0b04_050b(p, "1234")
        assert 0x050B in req.call_args.args[5]

    def test_0b04_050b_0505_0508(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_0b04_050b_0505_0508(p, "1234")
        attrs = req.call_args.args[5]
        assert 0x0505 in attrs
        assert 0x0508 in attrs
        assert 0x050B in attrs

    def test_fc00_is_noop(self, ra):
        p = _plugin()
        # Must not raise
        result = ra.ReadAttributeRequest_fc00(p, "1234")
        assert result is None

    def test_fc11(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_fc11(p, "1234")

    def test_fc21_profalux_calls_read_attribute(self, ra, monkeypatch):
        p = _plugin(manufacturer="1110")
        p.ListOfDevices["1234"]["ZDeviceID"] = "0200"
        read_attr = MagicMock(return_value="sqn")
        monkeypatch.setattr(ra, "read_attribute", read_attr)
        ra.ReadAttributeRequest_fc21(p, "1234")
        read_attr.assert_called_once()

    def test_fc21_non_profalux_does_nothing(self, ra, monkeypatch):
        p = _plugin(manufacturer="0000")
        read_attr = MagicMock()
        monkeypatch.setattr(ra, "read_attribute", read_attr)
        ra.ReadAttributeRequest_fc21(p, "1234")
        read_attr.assert_not_called()

    def test_fc40(self, ra, monkeypatch):
        p = _plugin()
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_fc40(p, "1234")

    def test_fc7d_uses_ikea_manufacturer(self, ra, monkeypatch):
        p = _plugin()
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_fc7d(p, "1234")
        assert req.called
        _, kwargs = req.call_args
        assert kwargs.get("manufacturer") == "117c"
        assert kwargs.get("manufacturer_spec") == "01"

    def test_fcc0_skips_specific_attrs_via_raw(self, ra, monkeypatch):
        """Attributes 0x0102 etc. in fcc0 go via raw read_attribute, not ReadAttributeReq."""
        p = _plugin()
        p.ListOfDevices["1234"]["Attributes List"] = {
            "Ep": {"01": {"fcc0": {"0102": {}, "0000": {}}}}
        }
        monkeypatch.setattr(ra._mock_getListOfEp, "side_effect", lambda *a: ["01"])
        read_attr = MagicMock(return_value="sqn")
        req = MagicMock()
        monkeypatch.setattr(ra, "read_attribute", read_attr)
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.ReadAttributeRequest_fcc0(p, "1234")
        read_attr.assert_called()   # 0x0102 routed via raw
        req.assert_called()         # 0x0000 routed via ReadAttributeReq


# ═══════════════════════════════════════════════════════════════════════════════
# GammaTroniques TIC meter
# ═══════════════════════════════════════════════════════════════════════════════

class TestGammaTroniquesTICMeter:

    def test_read_attributes_gammatroniques_tic_meter_calls_manufacturer_fn(
            self, ra, monkeypatch):
        p = _plugin()
        p.ListOfDevices["1234"]["GammaTroniques"] = {"ModeTIC": 1}
        fn = MagicMock()
        monkeypatch.setattr(ra, "read_ticmeter_manufacturer", fn)
        ra.read_attributes_gammatroniques_tic_meter(p, "1234")
        fn.assert_called_once_with(p, "1234", 1, request="all")

    def test_read_attributes_ticmeter_tarif_calls_manufacturer_fn(
            self, ra, monkeypatch):
        p = _plugin()
        p.ListOfDevices["1234"]["GammaTroniques"] = {"ModeTIC": None}
        fn = MagicMock()
        monkeypatch.setattr(ra, "read_ticmeter_manufacturer", fn)
        ra.read_attributes_ticmeter_tarif(p, "1234")
        fn.assert_called_once_with(p, "1234", None, request="tariff")

    def test_read_ticmeter_manufacturer_all_mode1(self, ra, monkeypatch):
        p = _plugin()
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.read_ticmeter_manufacturer(p, "1234", tic_mode=1, request="all")
        req.assert_called_once()
        _, kwargs = req.call_args
        assert kwargs.get("maxReadAttributesByRequest") == 1

    def test_read_ticmeter_manufacturer_unknown_request_does_nothing(
            self, ra, monkeypatch):
        p = _plugin()
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.read_ticmeter_manufacturer(p, "1234", tic_mode=1, request="unknown")
        req.assert_not_called()

    def test_read_ticmeter_manufacturer_uptime(self, ra, monkeypatch):
        p = _plugin()
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.read_ticmeter_manufacturer(p, "1234", tic_mode=1, request="uptime")
        req.assert_called_once()
        attrs = req.call_args.args[5]
        assert 0x002c in attrs   # Mode TIC

    def test_read_ticmeter_manufacturer_tariff(self, ra, monkeypatch):
        p = _plugin()
        req = MagicMock()
        monkeypatch.setattr(ra, "ReadAttributeReq", req)
        ra.read_ticmeter_manufacturer(p, "1234", tic_mode=1, request="tariff")
        req.assert_called_once()
        attrs = req.call_args.args[5]
        assert 0x0000 in attrs   # Type de Contrat


# ═══════════════════════════════════════════════════════════════════════════════
# READ_ATTRIBUTES_REQUEST map completeness
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadAttributesRequestMap:

    def test_map_contains_expected_clusters(self, ra):
        expected = {
            "0000", "0001", "0002", "0006", "0008", "000c", "0019", "0020",
            "0100", "0101", "0102", "0201", "0202", "0204", "0300",
            "0400", "0402", "0403", "0405", "0406", "0500", "0502",
            "0702", "0705", "070d", "0b01", "0b04", "0b05",
            "e000", "e001", "fcc0", "fc01", "fc11", "fc21", "fc40",
            "fc7d", "ff66", "ff42",
        }
        assert expected.issubset(ra.READ_ATTRIBUTES_REQUEST.keys())

    def test_all_entries_are_callable(self, ra):
        for cluster, (func, _) in ra.READ_ATTRIBUTES_REQUEST.items():
            assert callable(func), f"Cluster {cluster}: function is not callable"

    def test_all_polling_keys_are_strings(self, ra):
        for cluster, (_, polling_key) in ra.READ_ATTRIBUTES_REQUEST.items():
            assert isinstance(polling_key, str), \
                f"Cluster {cluster}: polling key is not a string"
