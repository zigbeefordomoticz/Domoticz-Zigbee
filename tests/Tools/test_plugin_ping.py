#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Tools/plugin-ping.py

Coverage:
  - check_zigbee_plugin_alive – HTTP 200 → True, non-200 → False, ConnectionError → False,
                                Timeout → False, silent mode suppresses output
"""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Stub 'requests' before loading the module so the import doesn't fail in
# environments that don't have the package installed.
_requests_stub = types.ModuleType("requests")
_requests_stub.get = MagicMock()
_requests_stub.ConnectionError = ConnectionError
_requests_stub.Timeout = TimeoutError
sys.modules.setdefault("requests", _requests_stub)

SCRIPT_PATH = Path(__file__).parents[2] / "Tools" / "plugin-ping.py"

spec = importlib.util.spec_from_file_location("plugin_ping", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

check_zigbee_plugin_alive = mod.check_zigbee_plugin_alive


class TestCheckZigbeePluginAlive:
    def _mock_response(self, status_code: int):
        r = MagicMock()
        r.status_code = status_code
        return r

    def test_200_returns_true(self, capsys):
        with patch("requests.get", return_value=self._mock_response(200)):
            assert check_zigbee_plugin_alive("127.0.0.1", "9440") is True
        assert "alive" in capsys.readouterr().out

    def test_non_200_returns_false(self, capsys):
        with patch("requests.get", return_value=self._mock_response(503)):
            assert check_zigbee_plugin_alive("127.0.0.1", "9440") is False
        assert "not alive" in capsys.readouterr().out

    def test_connection_error_returns_false(self, capsys):
        with patch("requests.get", side_effect=ConnectionError):
            assert check_zigbee_plugin_alive("127.0.0.1", "9440") is False

    def test_timeout_returns_false(self, capsys):
        with patch("requests.get", side_effect=TimeoutError):
            assert check_zigbee_plugin_alive("127.0.0.1", "9440") is False

    def test_silent_mode_no_output_on_success(self, capsys):
        with patch("requests.get", return_value=self._mock_response(200)):
            check_zigbee_plugin_alive("127.0.0.1", "9440", silent=True)
        assert capsys.readouterr().out == ""

    def test_silent_mode_no_output_on_failure(self, capsys):
        with patch("requests.get", return_value=self._mock_response(404)):
            check_zigbee_plugin_alive("127.0.0.1", "9440", silent=True)
        assert capsys.readouterr().out == ""

    def test_correct_url_called(self):
        import requests
        with patch("requests.get", return_value=self._mock_response(200)) as mock_get:
            check_zigbee_plugin_alive("192.168.1.10", "9441")
        mock_get.assert_called_once_with(
            "http://192.168.1.10:9441/rest-z4d/1/plugin-ping", timeout=1
        )
