#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the context Zigbee.zclDecoders.decoding_error attaches to a ZCL
decoding error.

An error log is often the only thing we get from a user, so a decoding error has
to be readable on its own: the device Model, because that is what names the
certified configuration involved, and the offset decoding stopped at.

Regressions guarded here:
- the Model was absent, so every report meant asking the user for a second file
  to turn a NwkId into a device;
- "Idx" was the None that extract_value_size() returns when it cannot size a
  value, passed straight back by the call sites, so the field was always null;
- one log line of the module was not passing its nwkid and could not be filtered
  per device.

Zigbee.zclDecoders imports the real Modules.* package, which conflicts with the
stubs tests/conftest.py installs for the session, so the decoder calls run in a
subprocess.
"""

import ast
import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DECODER_SOURCE = REPO_ROOT / "Zigbee" / "zclDecoders.py"

# Attribute 0x0000 carrying data type 0x13 - reserved in the ZCL specification, so
# it is in no SIZE_DATA_TYPE table and can never be sized. Using a type that stays
# undecodable keeps these tests independent of any later decoding change.
#
# Each decoder lays its records out differently, hence a different offset for the
# value the decoder gives up on:
#   write request / report response:  attribute | type | value
#   read response:                    attribute | status | type | value
DECODERS = {
    "foundation_cluster_write_attribute_request": ("0000" + "13" + "1234", 6),
    "foundation_cluster_read_attribute_response": ("0000" + "00" + "13" + "1234", 8),
    "foundation_cluster_report_attribute_response": ("0000" + "13" + "1234", 6),
}

DEVICE_LISTS = {
    "known_model": {"c577": {"Model": "TS0505B"}},
    "no_model_key": {"c577": {}},
    "empty_model": {"c577": {"Model": ""}},
    "unknown_device": {},
}


@pytest.fixture(scope="module")
def decoded():
    snippet = textwrap.dedent(
        """
        import json, sys, types
        for name in ("Domoticz", "DomoticzEx"):
            sys.modules[name] = types.ModuleType(name)
        import Zigbee.zclDecoders as decoders

        decoder_data, device_lists = json.loads(sys.argv[1])

        class Log:
            def __init__(self):
                self.errors = []

            def logging(self, module, logType, message, nwkid=None, context=None):
                if logType == "Error":
                    self.errors.append({"message": message, "nwkid": nwkid, "context": context})

        class Plugin:
            def __init__(self, devices):
                self.log = Log()
                self.ListOfDevices = devices

        out = {}
        for decoder_name, data in decoder_data.items():
            decoder = getattr(decoders, decoder_name)
            frame = "018002003cff0001040300010102c57702000018c00a" + data + "2803"
            # the write request is the one decoder taking a manufacturer code
            args = ("c0", "c577", "01", "01", "0300", None, data) if "write" in decoder_name else (
                "c0", "c577", "01", "01", "0300", data)
            out[decoder_name] = {}
            for name, devices in device_lists.items():
                plugin = Plugin(devices)
                returned = decoder(plugin, frame, *args)
                out[decoder_name][name] = {
                    "errors": plugin.log.errors, "frame_dropped": returned == frame}
        print(json.dumps(out))
        """
    )
    inputs = [{name: data for name, (data, _) in DECODERS.items()}, DEVICE_LISTS]
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, json.dumps(inputs)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout)


@pytest.mark.parametrize("decoder", list(DECODERS))
@pytest.mark.parametrize("case", list(DEVICE_LISTS))
def test_one_error_is_reported_per_undecodable_attribute(decoded, decoder, case):
    assert len(decoded[decoder][case]["errors"]) == 1
    assert decoded[decoder][case]["frame_dropped"] is True


@pytest.mark.parametrize("decoder", list(DECODERS))
@pytest.mark.parametrize(
    "case, expected_model",
    [
        ("known_model", "TS0505B"),
        # a device we know nothing about must still produce a readable error
        ("no_model_key", "unknown"),
        ("empty_model", "unknown"),
        ("unknown_device", "unknown"),
    ],
)
def test_error_context_names_the_model(decoded, decoder, case, expected_model):
    error = decoded[decoder][case]["errors"][0]

    assert error["context"]["Model"] == expected_model
    # the log line is what users paste, so it carries the Model too
    assert expected_model in error["message"]
    assert error["nwkid"] == "c577"


@pytest.mark.parametrize("decoder", list(DECODERS))
@pytest.mark.parametrize("case", list(DEVICE_LISTS))
def test_error_context_reports_where_decoding_stopped(decoded, decoder, case):
    data, value_offset = DECODERS[decoder]
    context = decoded[decoder][case]["errors"][0]["context"]

    assert context["Idx"] == value_offset
    assert context["Attribute"] == "0000"
    assert context["DType"] == "13"
    assert context["Data"] == data


def test_every_zcl_decoder_log_line_carries_its_nwkid():
    """A log line without a nwkid cannot be filtered per device."""
    tree = ast.parse(DECODER_SOURCE.read_text())
    without_nwkid = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "logging"):
            continue
        if not (isinstance(func.value, ast.Attribute) and func.value.attr == "log"):
            continue
        # logging(module, logType, message, nwkid=None, context=None)
        if len(node.args) < 4 and not any(keyword.arg == "nwkid" for keyword in node.keywords):
            without_nwkid.append(node.lineno)

    assert without_nwkid == [], f"self.log.logging() without a nwkid at lines {without_nwkid}"
