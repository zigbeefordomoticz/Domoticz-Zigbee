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
import pathlib
import re
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
# add_visit_dimensions / visit-scope copies in populate_custom_dimensions
# ---------------------------------------------------------------------------

class TestVisitDimensions:
    """Visit-scope dimensions 13-17 mirror the main action-scope ones."""

    def test_copies_and_chipset(self, matomo):
        dims = {"dimension1": "2026.4", "dimension3": "9.1.009", "dimension4": "Ezsp - 7.4.4.0 build 0",
                "dimension5": "Medium", "dimension6": "11.623"}
        matomo.add_visit_dimensions(dims)
        assert dims["dimension13"] == "9.1.009"
        assert dims["dimension14"] == "Ezsp"
        assert dims["dimension15"] == "2026.4"
        assert dims["dimension16"] == "11.623"
        assert dims["dimension17"] == "Medium"

    def test_missing_values_are_not_invented(self, matomo):
        dims = {"dimension3": "9.1.009"}
        matomo.add_visit_dimensions(dims)
        assert dims == {"dimension3": "9.1.009", "dimension13": "9.1.009"}

    def test_chipset_without_version_part(self, matomo):
        dims = {"dimension4": "Znp"}
        matomo.add_visit_dimensions(dims)
        assert dims["dimension14"] == "Znp"

    def test_snapshot_carries_visit_dimensions(self, matomo, plugin):
        plugin.pluginParameters["DisplayFirmwareVersion"] = "Znp - 20220219"
        with patch.object(matomo, "get_distribution", return_value=None), \
             patch.object(matomo, "get_architecture_model", return_value=None), \
             patch.object(matomo, "get_python_and_machine", return_value=("", "")), \
             patch.object(matomo, "get_ronelabs_model_custom_definition", return_value=None), \
             patch.object(matomo, "get_raspberry_pi_model", return_value=None), \
             patch.object(matomo, "is_container", return_value=False), \
             patch.object(matomo, "get_network_size_items", return_value="Small"):
            dims = matomo.populate_custom_dimensions(plugin)
        assert dims["dimension13"] == dims["dimension3"]
        assert dims["dimension14"] == "Znp"
        assert dims["dimension15"] == dims["dimension1"]
        assert dims["dimension16"] == dims["dimension6"]
        assert dims["dimension17"] == "Small"
        assert dims["dimension18"] == "ZiGate"
        assert dims["dimension22"] == "No device tree"
        for absent in ("dimension19", "dimension20", "dimension21"):
            assert absent not in dims


class TestPlatformVisitDimensions:
    """Visit-scope dimensions 18-22: coordinator, Python, CPU, OS, hardware."""

    def test_coordinator_and_os_are_copies(self, matomo):
        dims = {"dimension2": "ZBDongle-E ezsp", "dimension7": "Debian GNU Linux 12"}
        matomo.add_visit_dimensions(dims)
        assert dims["dimension18"] == "ZBDongle-E ezsp"
        assert dims["dimension21"] == "Debian GNU Linux 12"

    @pytest.mark.parametrize("model, expected", [
        ("Raspberry Pi 4 Model B Rev 1.5", "Raspberry Pi 4 Model B"),
        ("Raspberry Pi 5 Model B Rev 1.0", "Raspberry Pi 5 Model B"),
        ("Raspberry Pi Zero 2 W Rev 1.0", "Raspberry Pi Zero 2 W"),
        ("Rockchip RK3328 EVB", "Rockchip RK3328 EVB"),
        ("OpenWrt One", "OpenWrt One"),
    ])
    def test_hardware_drops_board_revision(self, matomo, model, expected):
        dims = {"dimension11": model}
        matomo.add_visit_dimensions(dims)
        assert dims["dimension22"] == expected

    def test_device_tree_nul_is_cleaned_before_the_revision_is_dropped(self, matomo, plugin):
        with patch.object(matomo, "get_raspberry_pi_model", return_value="Raspberry Pi 3 Model B Plus Rev 1.3\x00"), \
             patch.object(matomo, "get_ronelabs_model_custom_definition", return_value=None), \
             patch.object(matomo, "get_network_size_items", return_value="Small"):
            dims = matomo.populate_custom_dimensions(plugin)
        assert dims["dimension22"] == "Raspberry Pi 3 Model B Plus"

    def test_no_device_tree_no_hardware_value(self, matomo):
        dims = {"dimension7": "Ubuntu 24.04"}
        matomo.add_visit_dimensions(dims)
        assert "dimension22" not in dims

    @pytest.mark.parametrize("model, container, expected", [
        (None, True, "Container"),
        (None, False, "No device tree"),
        ("\x00", False, "No device tree"),
        ("Raspberry Pi 4 Model B Rev 1.5", False, "Raspberry Pi 4 Model B"),
        # A container which is given the device tree: the board says more
        ("Raspberry Pi 4 Model B Rev 1.5", True, "Raspberry Pi 4 Model B"),
    ])
    def test_snapshot_hardware_without_board_model(self, matomo, plugin, model, container, expected):
        with patch.object(matomo, "get_raspberry_pi_model", return_value=model), \
             patch.object(matomo, "is_container", return_value=container), \
             patch.object(matomo, "get_ronelabs_model_custom_definition", return_value=None), \
             patch.object(matomo, "get_network_size_items", return_value="Small"):
            dims = matomo.populate_custom_dimensions(plugin)
        assert dims["dimension22"] == expected

    @pytest.mark.parametrize("container", [True, False])
    def test_action_platform_stays_empty_without_board_model(self, matomo, plugin, container):
        with patch.object(matomo, "get_raspberry_pi_model", return_value=None), \
             patch.object(matomo, "is_container", return_value=container), \
             patch.object(matomo, "get_ronelabs_model_custom_definition", return_value=None), \
             patch.object(matomo, "get_network_size_items", return_value="Small"):
            dims = matomo.populate_custom_dimensions(plugin)
        assert "dimension11" not in dims

    @pytest.mark.parametrize("present, expected", [
        ("/.dockerenv", True),
        ("/run/.containerenv", True),
        ("/proc/device-tree/model", False),
    ])
    def test_is_container(self, matomo, present, expected):
        with patch.object(matomo.os.path, "exists", side_effect=lambda path: path == present):
            assert matomo.is_container() is expected

    def test_python_and_machine_values(self, matomo):
        with patch.object(matomo.platform, "python_version_tuple", return_value=("3", "11", "2")), \
             patch.object(matomo.platform, "machine", return_value="aarch64"):
            assert matomo.get_python_and_machine() == ("3.11", "aarch64")

    def test_snapshot_carries_python_and_machine(self, matomo, plugin):
        with patch.object(matomo, "get_python_and_machine", return_value=("3.13", "x86_64")), \
             patch.object(matomo, "get_raspberry_pi_model", return_value=None), \
             patch.object(matomo, "get_ronelabs_model_custom_definition", return_value=None), \
             patch.object(matomo, "get_network_size_items", return_value="Small"):
            dims = matomo.populate_custom_dimensions(plugin)
        assert dims["dimension19"] == "3.13"
        assert dims["dimension20"] == "x86_64"
        assert dims["dimension21"] == "Raspberry Pi OS 11"


class TestInstallVisitDimensions:
    """Visit-scope dimensions 23-26: firmware, RoneLabs, connection and install type."""

    def test_firmware_and_ronelabs_are_copies(self, matomo):
        dims = {"dimension4": "Ezsp - 7.4.4.0 build 0", "dimension10": "Ronelabs"}
        matomo.add_visit_dimensions(dims)
        assert dims["dimension23"] == "Ezsp - 7.4.4.0 build 0"
        assert dims["dimension24"] == "Ronelabs"

    def test_missing_firmware_and_ronelabs_are_not_sent(self, matomo):
        dims = {"dimension3": "9.1.011"}
        matomo.add_visit_dimensions(dims)
        assert "dimension23" not in dims
        assert "dimension24" not in dims

    @pytest.mark.parametrize("mode2, expected", [
        ("USB", "USB"),
        ("USB,115200,hardware", "USB"),
        ("DIN", "DIN"),
        ("PI", "PI"),
        ("Wifi", "TCPIP"),
        ("Socket", "Socket"),
        ("None", None),
        ("192.168.1.10", None),
        ("", None),
        (None, None),
    ])
    def test_connection_type(self, matomo, plugin, mode2, expected):
        plugin.pluginParameters["Mode2"] = mode2
        assert matomo.get_connection_type(plugin) == expected

    def test_every_connection_option_is_known(self, matomo):
        """The options of the Mode2 parameter in plugin.py, but None, all have a value."""
        source = (pathlib.Path(__file__).parents[2] / "plugin.py").read_text(encoding="utf-8")
        field = re.search(r'<param field="Mode2".*?</param>', source, re.S).group(0)
        options = set(re.findall(r'<option [^>]*value="([^"]*)"', field))
        assert "USB" in options and "Socket" in options
        assert {o.split(",")[0] for o in options} - {"None"} == set(matomo.CONNECTION_TYPES)

    @pytest.mark.parametrize("content, expected", [
        ([".git"], "Git"),
        ([".pypluginstore.json"], "PyPluginStore"),
        ([".git", ".pypluginstore.json"], "PyPluginStore"),
        ([], "Other"),
    ])
    def test_install_type(self, matomo, plugin, tmp_path, content, expected):
        for name in content:
            (tmp_path / name).touch()
        plugin.pluginParameters["HomeFolder"] = str(tmp_path) + "/"
        assert matomo.get_install_type(plugin) == expected

    def test_install_type_does_not_look_at_the_parent_folders(self, matomo, plugin, tmp_path):
        (tmp_path / ".git").mkdir()
        home = tmp_path / "plugins" / "Domoticz-Zigbee"
        home.mkdir(parents=True)
        plugin.pluginParameters["HomeFolder"] = str(home)
        assert matomo.get_install_type(plugin) == "Other"

    def test_install_type_without_home_folder(self, matomo, plugin):
        assert matomo.get_install_type(plugin) is None

    @pytest.mark.parametrize("mode2, home, expected", [
        ("Socket", True, ("Socket", "Other")),
        ("None", False, (None, None)),
    ])
    def test_snapshot_carries_connection_and_install(self, matomo, plugin, tmp_path, mode2, home, expected):
        plugin.pluginParameters["Mode2"] = mode2
        plugin.pluginParameters["Address"] = "192.168.1.10"
        plugin.pluginParameters["SerialPort"] = "/dev/ttyUSB0"
        if home:
            plugin.pluginParameters["HomeFolder"] = str(tmp_path)
        with patch.object(matomo, "get_raspberry_pi_model", return_value=None), \
             patch.object(matomo, "is_container", return_value=False), \
             patch.object(matomo, "get_ronelabs_model_custom_definition", return_value=None), \
             patch.object(matomo, "get_network_size_items", return_value="Small"):
            dims = matomo.populate_custom_dimensions(plugin)
        assert (dims.get("dimension25"), dims.get("dimension26")) == expected
        assert dims["dimension23"] == dims["dimension4"]
        sent = " ".join(dims.values())
        for private in ("192.168.1.10", "ttyUSB0", str(tmp_path)):
            assert private not in sent


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
# matomo_check_coordinator_change
# ---------------------------------------------------------------------------

class TestCheckCoordinatorChange:
    """A replaced coordinator is reported once, linking the old and new ids."""

    def run(self, matomo, plugin, reported):
        plugin.pluginconf.pluginConf = {}
        if reported is not None:
            plugin.pluginconf.pluginConf["MatomoCoordinatorReported"] = reported
        plugin.pluginconf.write_Settings.reset_mock()
        with patch.object(matomo, "fetch_data_with_timeout") as mock_fetch:
            matomo.matomo_check_coordinator_change(plugin)
        return [c.args[2] for c in mock_fetch.call_args_list]

    def test_first_start_records_without_sending(self, matomo, plugin):
        for reported in (None, ""):
            assert self.run(matomo, plugin, reported) == []
            assert plugin.pluginconf.pluginConf["MatomoCoordinatorReported"] == matomo.get_clientid(plugin)
            plugin.pluginconf.write_Settings.assert_called_once()

    def test_same_coordinator_does_nothing(self, matomo, plugin):
        assert self.run(matomo, plugin, matomo.get_clientid(plugin)) == []
        plugin.pluginconf.write_Settings.assert_not_called()

    def test_replaced_coordinator_sends_one_event(self, matomo, plugin):
        old = hashlib.sha256("0011223344556677".encode()).hexdigest()
        sent = self.run(matomo, plugin, old)
        assert len(sent) == 1
        assert sent[0]["e_c"] == "Coordinator"
        assert sent[0]["e_a"] == "Replaced"
        assert sent[0]["e_n"] == old
        assert sent[0]["uid"] == matomo.get_clientid(plugin)
        assert plugin.pluginconf.pluginConf["MatomoCoordinatorReported"] == matomo.get_clientid(plugin)

    def test_unknown_coordinator_does_nothing(self, matomo, plugin):
        plugin.ListOfDevices = {}
        assert self.run(matomo, plugin, "abc") == []
        assert plugin.pluginconf.pluginConf["MatomoCoordinatorReported"] == "abc"
        plugin.pluginconf.write_Settings.assert_not_called()


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


# ---------------------------------------------------------------------------
# matomo_reconcile_opt_in_state
# ---------------------------------------------------------------------------

class TestReconcileOptInState:
    """An opt-in change made outside the WebUI is reported once at start."""

    def run(self, matomo, plugin, opt_in, reported, internet=True):
        plugin.pluginconf.pluginConf = {"MatomoOptIn": opt_in}
        if reported is not None:
            plugin.pluginconf.pluginConf["MatomoOptInReported"] = reported
        plugin.internet_available = internet
        with patch.object(matomo, "fetch_data_with_timeout") as mock_fetch:
            matomo.matomo_reconcile_opt_in_state(plugin)
        return [c.args[2].get("e_a") for c in mock_fetch.call_args_list]

    def test_first_start_records_without_sending(self, matomo, plugin):
        for opt_in in (1, 0):
            sent = self.run(matomo, plugin, opt_in, -1)
            assert sent == []
            assert plugin.pluginconf.pluginConf["MatomoOptInReported"] == opt_in

    def test_missing_setting_counts_as_unknown(self, matomo, plugin):
        sent = self.run(matomo, plugin, 1, None)
        assert sent == []
        assert plugin.pluginconf.pluginConf["MatomoOptInReported"] == 1

    def test_unchanged_does_nothing(self, matomo, plugin):
        plugin.pluginconf.write_Settings.reset_mock()
        assert self.run(matomo, plugin, 1, 1) == []
        assert self.run(matomo, plugin, 0, 0) == []
        plugin.pluginconf.write_Settings.assert_not_called()

    def test_switched_off_outside_webui_sends_opt_out_once(self, matomo, plugin):
        assert self.run(matomo, plugin, 0, 1) == ["Opt-Out"]
        assert plugin.pluginconf.pluginConf["MatomoOptInReported"] == 0
        plugin.pluginconf.write_Settings.assert_called()

    def test_switched_on_outside_webui_sends_opt_in(self, matomo, plugin):
        assert self.run(matomo, plugin, True, 0) == ["Opt-In"]
        assert plugin.pluginconf.pluginConf["MatomoOptInReported"] == 1

    def test_no_internet_keeps_it_for_next_start(self, matomo, plugin):
        assert self.run(matomo, plugin, 0, 1, internet=False) == []
        assert plugin.pluginconf.pluginConf["MatomoOptInReported"] == 1

    def test_unknown_coordinator_keeps_it_for_next_start(self, matomo, plugin):
        plugin.ListOfDevices = {}
        assert self.run(matomo, plugin, 0, 1) == []
        assert plugin.pluginconf.pluginConf["MatomoOptInReported"] == 1
