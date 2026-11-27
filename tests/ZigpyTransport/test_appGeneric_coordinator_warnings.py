#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The coordinator is not reported at start as a duplicate, nor as a device that was not pre-loaded.

Importing AppGeneric pulls in modules tests/conftest.py stubs for the rest of the session, so each
scenario runs in a subprocess, as in test_appGeneric_initialize.py.
"""

import importlib.util
import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("zigpy") is None, reason="requires the real zigpy package"
)

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import json, logging, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import zigpy.types as t
    import Classes.ZigpyTransport.AppGeneric as AG

    records = []

    class Handler(logging.Handler):
        def emit(self, record):
            records.append([record.levelname, record.getMessage()])

    AG.LOGGER.addHandler(Handler())
    AG.LOGGER.setLevel(logging.DEBUG)
    """
)


def run(body):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(body)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


IEEE = "0011223344556677"

PRELOAD = """
    ieee = t.EUI64(t.uint64_t(int("{ieee}", 16)).serialize())
    dev = types.SimpleNamespace(ieee=ieee, nwk={zigpy_nwk}, node_desc=MagicMock())
    app = types.SimpleNamespace(
        devices={{ieee: dev}}, log=MagicMock(),
        callBackGetAllDevices=lambda: [(int("{ieee}", 16), {plugin_nwk}, {{}})],
    )
    AG._preload_devices_from_plugin_db(app)
    print(json.dumps([level for level, m in records if "already exists" in m]))
"""

GET_DEVICE = """
    class Base:
        def get_device(self, ieee=None, nwk=None):
            raise KeyError

    class App(Base):
        log = MagicMock()
        def callBackGetDevice(self, ieee, nwk):
            return {found}

    try:
        AG.get_device(App(), {args})
        raised = False
    except KeyError:
        raised = True
    print(json.dumps([raised, [level for level, m in records if "get_device miss" in m]]))
"""

BY_IEEE = f'ieee=t.EUI64(t.uint64_t(int("{IEEE}", 16)).serialize())'


def test_coordinator_already_in_the_table_is_not_a_warning():
    assert run(PRELOAD.format(ieee=IEEE, zigpy_nwk=0, plugin_nwk=0)) == ["DEBUG"]


@pytest.mark.parametrize("zigpy_nwk, plugin_nwk", [(0x1A2B, 0x1A2B), (0x0000, 0x1A2B), (0x1A2B, 0x0000)])
def test_any_other_device_already_in_the_table_is_still_a_warning(zigpy_nwk, plugin_nwk):
    assert run(PRELOAD.format(ieee=IEEE, zigpy_nwk=zigpy_nwk, plugin_nwk=plugin_nwk)) == ["WARNING"]


@pytest.mark.parametrize("args", [BY_IEEE, "nwk=t.NWK(0x0000)"])
def test_coordinator_miss_is_silent_and_still_raises(args):
    assert run(GET_DEVICE.format(found=f'(0x0000, int("{IEEE}", 16))', args=args)) == [True, []]


@pytest.mark.parametrize("args", [BY_IEEE, "nwk=t.NWK(0x1A2B)"])
def test_known_device_miss_is_still_a_warning(args):
    assert run(GET_DEVICE.format(found=f'(0x1A2B, int("{IEEE}", 16))', args=args)) == [True, ["WARNING"]]


def test_unknown_device_miss_is_silent():
    assert run(GET_DEVICE.format(found="None", args=BY_IEEE)) == [True, []]
