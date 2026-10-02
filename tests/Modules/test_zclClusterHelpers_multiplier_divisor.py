#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Modules/zclClusterHelpers.py multiplier / divisor handling

Coverage:
  - compute_electrical_measurement_conso() (0x0b04) and compute_metering_conso()
    (0x0702) read the multiplier/divisor attributes from ListOfDevices "Ep".
    The generic ZCL path stores them as int, but the raw path stores the
    received hex string. int() on such a string either raised ValueError
    ("000a") and aborted the measurement, or silently mis-decoded it as decimal
    ("0010" -> 10 instead of 16).
  - Unusable values (unexpected type) fall back to 1 and are logged; 0 is
    still replaced by 1.

Modules.zclClusterHelpers imports the real Modules.* package, which conflicts
with the stubs tests/conftest.py installs for the rest of the session. The
checks are therefore executed in a subprocess, fully isolated from the pytest
session.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.zclClusterHelpers as zch

    zch.ReadAttributeRequest_0702_multiplier_divisor = MagicMock()

    class Log:
        def __init__(self):
            self.records = []
        def logging(self, module, level, message, *args, **kwargs):
            self.records.append((level, message))

    def make_plugin(cluster, attributes):
        p = types.SimpleNamespace()
        p.log = Log()
        p.DeviceConf = {}
        p.ListOfDevices = {"1234": {"Model": "x", "Ep": {"01": {cluster: attributes}}}}
        return p

    def elec(attributes, attr_id="050b", raw=100):
        p = make_plugin("0b04", attributes)
        return zch.compute_electrical_measurement_conso(p, "1234", "01", "0b04", attr_id, raw), p

    def metering(attributes, raw=100):
        p = make_plugin("0702", dict(attributes, **{"0300": "Unitless"}))
        return zch.compute_metering_conso(p, "1234", "01", "0702", "0000", raw), p
    """
)


def _run(snippet):
    """Execute `snippet` against the real (unstubbed) plugin modules."""
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(snippet)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return result.stdout.strip()


def test_electrical_measurement_int_values_unchanged():
    _run(
        """
        value, p = elec({"0604": 2, "0605": 10})
        assert value == 20.0, value
        value, p = elec({})
        assert value == 100, value
        """
    )


def test_electrical_measurement_hex_string_values():
    _run(
        """
        value, p = elec({"0604": "0001", "0605": "000a"})   # used to raise ValueError
        assert value == 10.0, value
        value, p = elec({"0604": "0001", "0605": "0010"})   # used to give 10.0 (decimal decode)
        assert value == 6.25, value
        """
    )


def test_electrical_measurement_zero_and_unexpected_values():
    _run(
        """
        value, p = elec({"0604": 0, "0605": "0000"})
        assert value == 100, value
        value, p = elec({"0604": 1, "0605": "zz"})
        assert value == 100, value
        assert any(lvl == "Log" and "0605" in m for lvl, m in p.log.records), p.log.records
        value, p = elec({"0604": {}, "0605": 4})
        assert value == 25.0, value
        """
    )


def test_metering_hex_string_values():
    _run(
        """
        value, p = metering({"0301": 1, "0302": 1000})
        assert value == 0.1, value
        value, p = metering({"0301": "0001", "0302": "03e8"})  # used to raise ValueError
        assert value == 0.1, value
        """
    )
