#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Modules/zclClusterHelpers.py _build_model_name()

_build_model_name() turns the model name reported by the device in the Basic
cluster into the plugin-internal model name used as a self.DeviceConf key.

Coverage:
  - A per-manufacturer configuration (a Conf/Local-Devices file named
    "<Model>-<Manufacturer Name>.json", or an 'Identifier' entry naming the
    (Model, Manufacturer Name) pair) takes precedence over the hardcoded
    PLUGIN_MODELS_MATRIX. Model '66666' used to short-circuit straight to the
    matrix, so no Conf/Local-Devices file could ever override a SONOFF 66666.
  - That short-circuit is still applied when the Manufacturer Name is unknown:
    the 66666 variants differ only by ZDeviceID (0302 temp/humi, 0402 motion),
    which the matrix alone can discriminate, so it must be given a chance
    before the generic "66666" configuration is accepted.
  - An unknown Manufacturer Name stored as {} (which several code paths do)
    no longer raises TypeError on the string concatenations.

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

    class Log:
        def logging(self, module, level, message, *args, **kwargs):
            pass

    def resolve(model, manufacturer_name="", zdevice_id=None, manuf_code="",
                device_conf=(), identifiers=()):
        p = types.SimpleNamespace()
        p.log = Log()
        p.DeviceConf = {name: {} for name in device_conf}
        p.ModelManufMapping = dict(identifiers)
        p.ListOfDevices = {
            "1234": {
                "Manufacturer Name": manufacturer_name,
                "Manufacturer": manuf_code,
                "ZDeviceID": zdevice_id,
            }
        }
        return zch._build_model_name(p, "1234", model)
    """
)


def run_checks(body):
    script = PREAMBLE + textwrap.dedent(body)
    proc = subprocess.run(  # nosec B603
        [sys.executable, "-c", script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"subprocess failed\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )
    return proc.stdout


# ── Conf/Local-Devices precedence over the hardcoded matrix ──────────────────

def test_local_devices_file_wins_over_matrix_for_tuya():
    """A <Model>-<Manufacturer>.json beats the TS011F-plug matrix entry."""
    run_checks(
        """
        got = resolve(
            "TS011F", manufacturer_name="_TZ3000_cehuw1lw",
            device_conf=("TS011F-_TZ3000_cehuw1lw", "TS011F-plug"),
        )
        assert got == "TS011F-_TZ3000_cehuw1lw", got
        """
    )


def test_matrix_applies_when_no_local_devices_file():
    run_checks(
        """
        got = resolve(
            "TS011F", manufacturer_name="_TZ3000_cehuw1lw",
            device_conf=("TS011F-plug",),
        )
        assert got == "TS011F-plug", got
        """
    )


def test_bare_model_file_does_not_beat_the_matrix():
    """A Conf/Local-Devices/TS011F.json is NOT part of the per-manufacturer chain."""
    run_checks(
        """
        got = resolve(
            "TS011F", manufacturer_name="_TZ3000_cehuw1lw",
            device_conf=("TS011F", "TS011F-plug"),
        )
        assert got == "TS011F-plug", got
        """
    )


def test_identifier_mapping_wins_over_matrix():
    run_checks(
        """
        got = resolve(
            "TS011F", manufacturer_name="_TZ3000_cehuw1lw",
            device_conf=("MyPlug", "TS011F-plug"),
            identifiers={("TS011F", "_TZ3000_cehuw1lw"): "MyPlug"},
        )
        assert got == "MyPlug", got
        """
    )


def test_concatenated_form_without_dash_is_accepted():
    run_checks(
        """
        got = resolve(
            "TS011F", manufacturer_name="_TZ3000_cehuw1lw",
            device_conf=("TS011F_TZ3000_cehuw1lw", "TS011F-plug"),
        )
        assert got == "TS011F_TZ3000_cehuw1lw", got
        """
    )


# ── model 66666: no longer immune to Conf/Local-Devices ─────────────────────

def test_sonoff_66666_can_be_overridden_by_a_local_devices_file():
    """This was impossible before: 66666 short-circuited to the matrix."""
    run_checks(
        """
        got = resolve(
            "66666", manufacturer_name="eWeLink", zdevice_id="0402",
            device_conf=("66666", "66666-eWeLink", "66666-motion"),
        )
        assert got == "66666-eWeLink", got
        """
    )


def test_sonoff_66666_can_be_overridden_by_an_identifier():
    run_checks(
        """
        got = resolve(
            "66666", manufacturer_name="eWeLink", zdevice_id="0402",
            device_conf=("66666", "MyLocalSonoff", "66666-motion"),
            identifiers={("66666", "eWeLink"): "MyLocalSonoff"},
        )
        assert got == "MyLocalSonoff", got
        """
    )


def test_sonoff_66666_still_resolved_by_the_matrix_without_a_local_file():
    run_checks(
        """
        for zdevice_id, expected in (("0302", "66666-temphumi"), ("0402", "66666-motion")):
            got = resolve(
                "66666", manufacturer_name="eWeLink", zdevice_id=zdevice_id,
                device_conf=("66666", "66666-temphumi", "66666-motion"),
            )
            assert got == expected, (zdevice_id, got)
        """
    )


def test_sonoff_66666_reaches_the_matrix_when_manufacturer_is_unknown():
    """
    The generic "66666" config must not win over the ZDeviceID discrimination
    while the Manufacturer Name has not been received yet.
    """
    run_checks(
        """
        got = resolve(
            "66666", manufacturer_name="", zdevice_id="0402",
            device_conf=("66666", "66666-temphumi", "66666-motion"),
        )
        assert got == "66666-motion", got
        """
    )


# ── Manufacturer Name stored as {} ───────────────────────────────────────────

def test_dict_manufacturer_name_does_not_raise():
    """Several code paths store an unknown Manufacturer Name as {}."""
    run_checks(
        """
        got = resolve(
            "TS011F", manufacturer_name={},
            device_conf=("TS011F", "TS011F-plug"),
        )
        assert got == "TS011F", got
        """
    )


def test_dict_manufacturer_name_still_reaches_the_matrix_for_66666():
    run_checks(
        """
        got = resolve(
            "66666", manufacturer_name={}, zdevice_id="0302",
            device_conf=("66666", "66666-temphumi"),
        )
        assert got == "66666-temphumi", got
        """
    )


# ── unknown Manufacturer Name: the bare model config is still honoured ──────

def test_bare_model_config_used_when_manufacturer_unknown():
    """
    A model name that is already a resolved variant must not be re-resolved by
    the matrix: TS0601-eTRV3 is itself listed as a TUYA TS0601 model name.
    """
    run_checks(
        """
        got = resolve("TS0601-eTRV3", manufacturer_name="", device_conf=("TS0601-eTRV3",))
        assert got == "TS0601-eTRV3", got
        """
    )


def test_unknown_model_is_returned_unchanged():
    run_checks(
        """
        got = resolve("NoSuchModel", manufacturer_name="NoSuchManuf")
        assert got == "NoSuchModel", got
        """
    )
