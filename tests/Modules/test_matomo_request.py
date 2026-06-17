#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Modules.matomo_request.

Pure-logic functions (classify_*, clean_*, get_clientid, …) are tested
directly.  Functions that hit the network or filesystem are tested via
unittest.mock.patch.  Functions that depend on the plugin object use the
local `plugin` fixture defined below.
"""

import hashlib
import sys
import time
import types
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Stub helpers
# ---------------------------------------------------------------------------

def _ensure_attr(module_name, **attrs):
    """Add attributes to a stub (or create one) without replacing existing modules."""
    mod = sys.modules.get(module_name)
    if mod is None:
        mod = types.ModuleType(module_name)
        sys.modules[module_name] = mod
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


# ---------------------------------------------------------------------------
# Module fixture: wire stubs then import matomo_request fresh
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def matomo():
    """Import Modules.matomo_request with all external deps stubbed."""
    _ensure_attr(
        "Modules.tools",
        how_many_devices=MagicMock(name="how_many_devices", return_value=(2, 3)),
    )
    _ensure_attr(
        "distro",
        name=MagicMock(return_value="Raspberry Pi OS"),
        version=MagicMock(return_value="11"),
    )

    sys.modules.pop("Modules.matomo_request", None)
    import Modules.matomo_request as m
    return m


# ---------------------------------------------------------------------------
# Plugin fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def plugin():
    p = MagicMock()
    p.log = MagicMock()
    p.log.logging = MagicMock()
    p.ListOfDevices = {"0000": {"IEEE": "aabbccddeeff0011"}}
    p.pluginParameters = {
        "DomoticzVersion": "2023.1",
        "CoordinatorModel": "ZiGate",
        "PluginVersion": "8.1.0",
        "DisplayFirmwareVersion": "3.1d",
        "CertifiedDbVersion": "10.0",
    }
    p.statistics = MagicMock()
    p.statistics._start = time.time() - 86400
    return p


# ---------------------------------------------------------------------------
# get_clientid
# ---------------------------------------------------------------------------

class TestGetClientId:
    def test_mode_hashed_returns_sha256(self, matomo, plugin):
        result = matomo.get_clientid(plugin, mode='hashed')
        expected = hashlib.sha256("aabbccddeeff0011".encode()).hexdigest()
        assert result == expected

    def test_mode_formated_returns_colon_separated_mac(self, matomo, plugin):
        result = matomo.get_clientid(plugin, mode='formated')
        assert result == "aa:bb:cc:dd:ee:ff:00:11"

    def test_default_mode_returns_sha256(self, matomo, plugin):
        expected = hashlib.sha256("aabbccddeeff0011".encode()).hexdigest()
        assert matomo.get_clientid(plugin) == expected

    def test_returns_none_when_no_device_0000(self, matomo, plugin):
        plugin.ListOfDevices = {}
        assert matomo.get_clientid(plugin) is None

    def test_returns_none_when_ieee_missing(self, matomo, plugin):
        plugin.ListOfDevices = {"0000": {}}
        assert matomo.get_clientid(plugin) is None

    def test_hash_is_deterministic(self, matomo, plugin):
        assert matomo.get_clientid(plugin, mode='hashed') == matomo.get_clientid(plugin, mode='hashed')


# ---------------------------------------------------------------------------
# classify_uptime
# ---------------------------------------------------------------------------

class TestClassifyUptime:
    @pytest.mark.parametrize("seconds,expected", [
        (0,            "1 day"),
        (86400,        "1 day"),
        (86401,        "2 days"),
        (2 * 86400,    "2 days"),
        (6 * 86400,    "1 week"),
        (7 * 86400,    "1 week"),
        (13 * 86400,   "2 weeks"),
        (28 * 86400,   "4 weeks"),
        (30 * 86400,   "1 month"),
        (180 * 86400,  "6 months"),
        (181 * 86400,  "Beyond 6 months"),
        (999 * 86400,  "Beyond 6 months"),
    ])
    def test_boundaries(self, matomo, seconds, expected):
        assert matomo.classify_uptime(seconds) == expected


# ---------------------------------------------------------------------------
# classify_nwk_size
# ---------------------------------------------------------------------------

class TestClassifyNwkSize:
    @pytest.mark.parametrize("value,expected", [
        (0,   "unknown"),
        (1,   "Micro"),
        (4,   "Micro"),
        (5,   "Small"),
        (9,   "Small"),
        (10,  "Medium"),
        (24,  "Medium"),
        (25,  "Large"),
        (49,  "Large"),
        (50,  "Very Large"),
        (74,  "Very Large"),
        (75,  "Xtra Large"),
        (200, "Xtra Large"),
    ])
    def test_size_categories(self, matomo, value, expected):
        assert matomo.classify_nwk_size(value) == expected


# ---------------------------------------------------------------------------
# clean_custom_dimension_value
# ---------------------------------------------------------------------------

class TestCleanCustomDimensionValue:
    def test_allowed_characters_pass_through(self, matomo):
        assert matomo.clean_custom_dimension_value("abc ABC 1.2_3-4") == "abc ABC 1.2_3-4"

    def test_disallowed_characters_replaced_with_space(self, matomo):
        result = matomo.clean_custom_dimension_value("hello@world!")
        assert "@" not in result
        assert "!" not in result

    def test_multiple_spaces_collapsed(self, matomo):
        assert matomo.clean_custom_dimension_value("a   b") == "a b"

    def test_leading_trailing_spaces_stripped(self, matomo):
        assert matomo.clean_custom_dimension_value("  hello  ") == "hello"

    def test_empty_string(self, matomo):
        assert matomo.clean_custom_dimension_value("") == ""

    def test_version_string(self, matomo):
        result = matomo.clean_custom_dimension_value("8.1.006")
        assert result == "8.1.006"

    def test_colon_replaced(self, matomo):
        result = matomo.clean_custom_dimension_value("python: 3.11.2")
        assert ":" not in result


# ---------------------------------------------------------------------------
# get_ronelabs_model_custom_definition
# ---------------------------------------------------------------------------

class TestGetRonelabsModel:
    def test_returns_first_line_when_file_exists(self, matomo, tmp_path):
        model_file = tmp_path / "modelinfo"
        model_file.write_text("RoneLabs Pi\nignored line\n")
        with patch.object(matomo.os.path, "exists", return_value=True):
            with patch("builtins.open", return_value=model_file.open()):
                result = matomo.get_ronelabs_model_custom_definition()
        assert result == "RoneLabs Pi"

    def test_returns_none_when_file_missing(self, matomo):
        with patch.object(matomo.os.path, "exists", return_value=False):
            assert matomo.get_ronelabs_model_custom_definition() is None


# ---------------------------------------------------------------------------
# get_raspberry_pi_model
# ---------------------------------------------------------------------------

class TestGetRaspberryPiModel:
    def test_returns_content_when_file_exists(self, matomo, tmp_path):
        model_file = tmp_path / "model"
        model_file.write_text("Raspberry Pi 4 Model B Rev 1.4\x00")
        with patch.object(matomo.os.path, "exists", return_value=True):
            with patch("builtins.open", return_value=model_file.open("r")):
                result = matomo.get_raspberry_pi_model()
        assert "Raspberry Pi" in result

    def test_returns_none_when_file_missing(self, matomo):
        with patch.object(matomo.os.path, "exists", return_value=False):
            assert matomo.get_raspberry_pi_model() is None


# ---------------------------------------------------------------------------
# get_uptime_category
# ---------------------------------------------------------------------------

class TestGetUptimeCategory:
    def test_recent_start_returns_1_day(self, matomo):
        start = time.time() - 3600  # 1 hour ago
        assert matomo.get_uptime_category(start) == "1 day"

    def test_old_start_returns_beyond_6_months(self, matomo):
        start = time.time() - 200 * 86400
        assert matomo.get_uptime_category(start) == "Beyond 6 months"


# ---------------------------------------------------------------------------
# get_network_size_items
# ---------------------------------------------------------------------------

class TestGetNetworkSizeItems:
    def test_uses_how_many_devices(self, matomo, plugin):
        with patch.object(matomo, "how_many_devices", return_value=(10, 15)):
            result = matomo.get_network_size_items(plugin)
        assert result == "Large"

    def test_zero_devices_returns_unknown(self, matomo, plugin):
        with patch.object(matomo, "how_many_devices", return_value=(0, 0)):
            result = matomo.get_network_size_items(plugin)
        assert result == "unknown"


# ---------------------------------------------------------------------------
# get_architecture_model
# ---------------------------------------------------------------------------

class TestGetArchitectureModel:
    def test_returns_string_with_python_version(self, matomo, plugin):
        result = matomo.get_architecture_model(plugin)
        assert result is not None
        assert "python:" in result

    def test_returns_none_and_logs_on_exception(self, matomo, plugin):
        with patch("platform.python_version", side_effect=RuntimeError("boom")):
            result = matomo.get_architecture_model(plugin)
        assert result is None
        plugin.log.logging.assert_called()


# ---------------------------------------------------------------------------
# get_distribution
# ---------------------------------------------------------------------------

class TestGetDistribution:
    def test_returns_name_and_version(self, matomo, plugin):
        distro_stub = sys.modules["distro"]
        distro_stub.name = MagicMock(return_value="Ubuntu")
        distro_stub.version = MagicMock(return_value="22.04")
        result = matomo.get_distribution(plugin)
        assert result == "Ubuntu 22.04"

    def test_returns_none_and_logs_on_exception(self, matomo, plugin):
        distro_stub = sys.modules["distro"]
        distro_stub.name = MagicMock(side_effect=Exception("distro error"))
        result = matomo.get_distribution(plugin)
        assert result is None
        plugin.log.logging.assert_called()


# ---------------------------------------------------------------------------
# fetch_data_with_timeout
# ---------------------------------------------------------------------------

class TestFetchDataWithTimeout:
    def test_calls_urlopen_with_encoded_params(self, matomo, plugin):
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_open.return_value.close = MagicMock()
            matomo.fetch_data_with_timeout(plugin, "http://example.com", {"idsite": 9, "rec": 1})
        mock_open.assert_called_once()
        url_called = mock_open.call_args[0][0]
        assert "idsite=9" in url_called
        assert "rec=1" in url_called

    def test_exception_is_caught_and_logged(self, matomo, plugin):
        with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
            matomo.fetch_data_with_timeout(plugin, "http://example.com", {})
        plugin.log.logging.assert_called()

    def test_exception_with_no_log_does_not_raise(self, matomo, plugin):
        plugin.log = None
        with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
            matomo.fetch_data_with_timeout(plugin, "http://example.com", {})


# ---------------------------------------------------------------------------
# send_matomo_request
# ---------------------------------------------------------------------------

class TestSendMatomoRequest:
    def test_aborts_when_client_id_is_none(self, matomo, plugin):
        plugin.ListOfDevices = {}
        with patch.object(matomo, "fetch_data_with_timeout") as mock_fetch:
            matomo.send_matomo_request(plugin, "TestAction")
        mock_fetch.assert_not_called()

    def test_sends_request_with_basic_payload(self, matomo, plugin):
        with patch.object(matomo, "fetch_data_with_timeout") as mock_fetch:
            matomo.send_matomo_request(plugin, "TestAction")
        mock_fetch.assert_called_once()
        _, url, payload = mock_fetch.call_args[0]
        assert payload["action_name"] == "TestAction"
        assert payload["idsite"] == matomo.SITE_ID
        assert "uid" in payload

    def test_event_params_added_to_payload(self, matomo, plugin):
        with patch.object(matomo, "fetch_data_with_timeout") as mock_fetch:
            matomo.send_matomo_request(
                plugin, "EvtAction",
                event_category="Plugin", event_action="Started", event_name="Plugin Started",
            )
        payload = mock_fetch.call_args[0][2]
        assert payload["e_c"] == "Plugin"
        assert payload["e_a"] == "Started"
        assert payload["e_n"] == "Plugin Started"

    def test_event_name_omitted_when_not_provided(self, matomo, plugin):
        with patch.object(matomo, "fetch_data_with_timeout") as mock_fetch:
            matomo.send_matomo_request(
                plugin, "EvtAction",
                event_category="Plugin", event_action="Started",
            )
        payload = mock_fetch.call_args[0][2]
        assert "e_n" not in payload

    def test_custom_dimensions_merged_into_payload(self, matomo, plugin):
        dims = {"dimension1": "2023.1", "dimension3": "8.1.0"}
        with patch.object(matomo, "fetch_data_with_timeout") as mock_fetch:
            matomo.send_matomo_request(plugin, "TestAction", custom_dimension=dims)
        payload = mock_fetch.call_args[0][2]
        assert payload["dimension1"] == "2023.1"
        assert payload["dimension3"] == "8.1.0"

    def test_custom_variable_serialized_as_json(self, matomo, plugin):
        cvar = {"1": ["os", "linux"]}
        with patch.object(matomo, "fetch_data_with_timeout") as mock_fetch:
            matomo.send_matomo_request(plugin, "TestAction", custom_variable=cvar)
        payload = mock_fetch.call_args[0][2]
        import json
        assert json.loads(payload["cvar"]) == cvar

    def test_non_serializable_custom_variable_logs_error_and_returns(self, matomo, plugin):
        with patch.object(matomo, "fetch_data_with_timeout") as mock_fetch:
            matomo.send_matomo_request(plugin, "TestAction", custom_variable={"bad": object()})
        mock_fetch.assert_not_called()
        plugin.log.logging.assert_called()


# ---------------------------------------------------------------------------
# populate_custom_dimensions
# ---------------------------------------------------------------------------

class TestPopulateCustomDimensions:
    def test_all_plugin_params_populate_dimensions(self, matomo, plugin):
        with patch.object(matomo, "get_distribution", return_value="Ubuntu 22.04"), \
             patch.object(matomo, "get_architecture_model", return_value="python: 3.11"), \
             patch.object(matomo, "get_ronelabs_model_custom_definition", return_value=None), \
             patch.object(matomo, "get_raspberry_pi_model", return_value=None), \
             patch.object(matomo, "get_network_size_items", return_value="Small"):
            dims = matomo.populate_custom_dimensions(plugin)
        assert "dimension1" in dims  # DomoticzVersion
        assert "dimension2" in dims  # CoordinatorModel
        assert "dimension3" in dims  # PluginVersion
        assert "dimension4" in dims  # DisplayFirmwareVersion
        assert "dimension5" in dims  # Network size
        assert "dimension6" in dims  # CertifiedDbVersion

    def test_missing_plugin_param_skips_dimension(self, matomo, plugin):
        plugin.pluginParameters = {}
        with patch.object(matomo, "get_distribution", return_value=None), \
             patch.object(matomo, "get_architecture_model", return_value=None), \
             patch.object(matomo, "get_ronelabs_model_custom_definition", return_value=None), \
             patch.object(matomo, "get_raspberry_pi_model", return_value=None), \
             patch.object(matomo, "get_network_size_items", return_value="unknown"):
            dims = matomo.populate_custom_dimensions(plugin)
        assert "dimension1" not in dims
        assert "dimension2" not in dims

    def test_ronelab_model_adds_dimension10_and_dimension12(self, matomo, plugin):
        with patch.object(matomo, "get_distribution", return_value=None), \
             patch.object(matomo, "get_architecture_model", return_value=None), \
             patch.object(matomo, "get_ronelabs_model_custom_definition", return_value="RoneLabs X1"), \
             patch.object(matomo, "get_raspberry_pi_model", return_value=None), \
             patch.object(matomo, "get_network_size_items", return_value="Small"):
            dims = matomo.populate_custom_dimensions(plugin)
        assert dims.get("dimension10") == "RoneLabs X1"
        assert "dimension12" in dims

    def test_pi_model_adds_dimension11(self, matomo, plugin):
        with patch.object(matomo, "get_distribution", return_value=None), \
             patch.object(matomo, "get_architecture_model", return_value=None), \
             patch.object(matomo, "get_ronelabs_model_custom_definition", return_value=None), \
             patch.object(matomo, "get_raspberry_pi_model", return_value="Raspberry Pi 4 Model B"), \
             patch.object(matomo, "get_network_size_items", return_value="Small"):
            dims = matomo.populate_custom_dimensions(plugin)
        assert "dimension11" in dims
