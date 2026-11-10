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


# compute_metering_conso() asks the device for 0x0300/0x0301/0x0302 only when a
# value is still needed for the attribute being decoded. It used to re-read on
# every report when the model overrode the Summation pair but not the Power pair
# (certified TS011F-plug), and when the device answered 0x86 Unsupported Attribute.
READ_CHECK = """
def read_count(conf, stored, statuses=None, attr_id="0000"):
    zch.ReadAttributeRequest_0702_multiplier_divisor.reset_mock()
    p = make_plugin("0702", dict(stored))
    p.ListOfDevices["1234"]["Model"] = "TS011F-plug"
    if conf is not None:
        p.DeviceConf = {"TS011F-plug": conf}
    if statuses:
        p.ListOfDevices["1234"]["ReadAttributes"] = {"Ep": {"01": {"0702": {
            "TimeStamp": 0, "iSQN": {}, "Attributes": dict(statuses), "ZigateRequest": {}}}}}
    zch.compute_metering_conso(p, "1234", "01", "0702", attr_id, 100)
    return zch.ReadAttributeRequest_0702_multiplier_divisor.call_count

TS011F = {"MeteringUnit": "Unitless", "SummationMeteringMultiplier": 10, "SummationMeteringDivisor": 1}
UNSUPPORTED = {"0300": "00", "0301": "86", "0302": "86"}
"""


def _run_read_check(snippet):
    return _run(READ_CHECK + textwrap.dedent(snippet))


def test_metering_no_read_when_overrides_cover_the_attribute():
    _run_read_check(
        """
        # Summation report, Summation pair overridden: nothing to read, Power pair irrelevant
        assert read_count(TS011F, {"0300": "kW"}) == 0
        assert read_count(TS011F, {}) == 0
        # Same configuration, Power report: the Power pair is not overridden and not stored
        assert read_count(TS011F, {"0300": "kW"}, attr_id="0400") == 1
        """
    )


def test_metering_no_read_after_unsupported_attribute():
    _run_read_check(
        """
        # Field case (TS011F _TZ3000_ynmowqk2): 0x0301/0x0302 answered 0x86
        assert read_count(TS011F, {"0300": "kW"}, UNSUPPORTED, attr_id="0400") == 0
        assert read_count(None, {"0300": "kW"}, UNSUPPORTED) == 0
        # Any error status is final, as for normalizedReadAttributeReq, which skips such attributes
        assert read_count(None, {"0300": "kW"}, {"0301": "86", "0302": "c3"}) == 0
        """
    )


def test_metering_read_until_values_are_known():
    _run_read_check(
        """
        # No configuration, nothing stored, never asked: read
        assert read_count(None, {}) == 1
        assert read_count(None, {"0300": 0}) == 1
        # Everything stored: no read
        assert read_count(None, {"0300": 0, "0301": 1, "0302": 1000}) == 0
        # Other attribute id (PC321 per-phase power): no override applies, stored values are needed
        assert read_count(TS011F, {"0300": 0, "0301": 1, "0302": 1000}, attr_id="2000") == 0
        assert read_count(TS011F, {"0300": 0}, attr_id="2000") == 1
        """
    )
