#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Modules/restartPlugin.py

When the coordinator does not answer after the start timeout, plugin.py
restarts the plugin through the Domoticz JSON API. When that call failed (for
instance curl rc=60 on a self-signed HTTPS "API base url", easydomoticz forum
t=14838), it was retried on every heartbeat, i.e. every second, with an error
that did not say why. Attempts are now spaced by STARTUP_RESTART_RETRY_DELAY,
and the error carries curl's own message and a hint for the setting.
"""

import subprocess  # nosec B404
from unittest.mock import patch

import Modules.restartPlugin as restartPlugin


def test_restart_attempt_due_first_heartbeat_past_threshold_then_every_delay():
    due = [hb for hb in range(0, 1000) if restartPlugin.restart_attempt_due(hb, 100, retry_delay=300)]
    assert due == [101, 401, 701]


def test_restart_attempt_never_due_before_threshold():
    assert not any(restartPlugin.restart_attempt_due(hb, 180) for hb in range(0, 181))


def _gethardware_failure(returncode, output):
    errors = []
    error = subprocess.CalledProcessError(returncode, ["curl"], output=output)
    with patch.object(restartPlugin.os.path, "isfile", return_value=True), \
         patch.object(restartPlugin.subprocess, "check_output", side_effect=error) as check_output, \
         patch.object(restartPlugin, "domoticz_error_api", side_effect=errors.append):
        result = restartPlugin.restartPluginViaDomoticzJsonApi(None, url_base_api="https://127.0.0.1:443")
    return result, errors, check_output.call_args.args[0]


def test_self_signed_certificate_error_is_actionable():
    result, errors, cmd = _gethardware_failure(60, b"curl: (60) SSL certificate problem: self-signed certificate\n")
    assert result is False
    assert "-sS" in cmd, cmd
    assert len(errors) == 1, errors
    assert "rc=60" in errors[0] and "self-signed certificate" in errors[0], errors
    assert "http://127.0.0.1:8080" in errors[0], errors


def test_unknown_curl_error_has_no_hint():
    result, errors, _ = _gethardware_failure(28, b"curl: (28) Operation timed out\n")
    assert result is False
    assert errors == ["Domoticz gethardware call failed (rc=28): b'curl: (28) Operation timed out\\n'"], errors
