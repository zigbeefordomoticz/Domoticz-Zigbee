#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_configure_reporting_mismatch_retry.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Regression test for the infinite "Z4D detects misconfigured reporting" loop:
when a device acknowledges (Status 00) a Configure Reporting request but keeps
reporting back a different Min/Max/Change (firmware silently clamps or ignores
the request), check_and_redo_configure_reporting_if_needed() used to re-send a
Configure Reporting (and possibly re-bind) on every ~1 minute heartbeat call,
forever. It must now give up permanently after MAX_CFG_RPT_MISMATCH_RETRY
consecutive attempts (no more resends until the next plugin restart), while
still resuming immediately if the device reports back a matching
configuration in the meantime.

Classes.ConfigureReporting is imported inside a module-scoped fixture, against
locally stubbed dependencies, and sys.modules is restored on teardown so
neither the conftest stubs nor other test modules are disturbed (same pattern
as tests/Classes/OTA/test_OTA_heartbeat.py).

Run with:
    python -m pytest tests/Classes/ConfigureReporting/test_configure_reporting_mismatch_retry.py -v
"""

import importlib
import sys
import time
import types
from unittest.mock import MagicMock

import pytest


def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


NWKID = "35fd"
EP = "01"
CLUSTER = "0b04"
ATTR = "050b"

# Direct imports of Classes/ConfigureReporting.py, stubbed so the import does
# not drag in the Domoticz framework (Modules.tools -> ... -> DomoticzEx).
_CR_DEPS = {
    "Classes.ZigateTransport.sqnMgmt": dict(
        TYPE_APP_ZCL="zcl",
        sqn_get_internal_sqn_from_app_sqn=MagicMock(name="sqn_get_internal_sqn_from_app_sqn", return_value=1),
    ),
    "Modules.bindings": dict(
        bindDevice=MagicMock(name="bindDevice"),
        unbindDevice=MagicMock(name="unbindDevice"),
    ),
    "Modules.tools": dict(
        check_datastruct=__import__("Modules.tools_datastruct", fromlist=["check_datastruct"]).check_datastruct,
        deviceconf_device=MagicMock(name="deviceconf_device", return_value=True),
        get_device_config_param=MagicMock(name="get_device_config_param", return_value=None),
        get_isqn_datastruct=MagicMock(name="get_isqn_datastruct"),
        get_list_isqn_attr_datastruct=MagicMock(name="get_list_isqn_attr_datastruct", return_value=[]),
        get_list_isqn_int_attr_datastruct=MagicMock(name="get_list_isqn_int_attr_datastruct", return_value=[]),
        getClusterListforEP=MagicMock(name="getClusterListforEP", return_value=[]),
        is_ack_tobe_disabled=MagicMock(name="is_ack_tobe_disabled", return_value=False),
        is_attr_unvalid_datastruct=MagicMock(name="is_attr_unvalid_datastruct", return_value=False),
        is_bind_ep=MagicMock(name="is_bind_ep", return_value=True),
        is_fake_ep=MagicMock(name="is_fake_ep", return_value=False),
        is_time_to_perform_work=MagicMock(name="is_time_to_perform_work", return_value=True),
        mainPoweredDevice=MagicMock(name="mainPoweredDevice", return_value=True),
        reset_attr_datastruct=MagicMock(name="reset_attr_datastruct"),
        set_isqn_datastruct=MagicMock(name="set_isqn_datastruct"),
        set_status_datastruct=MagicMock(name="set_status_datastruct"),
        set_timestamp_datastruct=MagicMock(name="set_timestamp_datastruct"),
    ),
    "Zigbee.zclCommands": dict(
        zcl_configure_reporting_requestv2=MagicMock(name="zcl_configure_reporting_requestv2"),
        zcl_read_report_config_request=MagicMock(name="zcl_read_report_config_request"),
    ),
}



# These have no heavy dependencies of their own, but other test modules (via the
# session-wide conftest.py stubs) may have already installed incomplete stand-ins
# for them under a different value/shape. Force a fresh real import for both.
_CR_REAL_MODULES = ["Modules.pluginDbAttributes", "Modules.zigateConsts"]


@pytest.fixture(scope="module")
def cr_module():
    deps_and_self = list(_CR_DEPS) + ["Classes.ConfigureReporting"] + _CR_REAL_MODULES
    saved = {name: sys.modules.pop(name, None) for name in deps_and_self}
    for name, attrs in _CR_DEPS.items():
        sys.modules[name] = _make_stub(name, **attrs)

    module = importlib.import_module("Classes.ConfigureReporting")
    yield module

    for name in deps_and_self:
        sys.modules.pop(name, None)
    for name, mod in saved.items():
        if mod is not None:
            sys.modules[name] = mod


@pytest.fixture
def cr(cr_module):
    """ConfigureReporting instance without running __init__ (no radio, no I/O)."""
    o = object.__new__(cr_module.ConfigureReporting)
    o.log = MagicMock()
    o.DeviceConf = {}
    o.ListOfDevices = {
        NWKID: {
            "Ep": {EP: {CLUSTER: {}}},
            # Custom override so retreive_configuration_reporting_definition() returns
            # a small, fully controlled desired configuration.
            "ParamConfigureReporting": {
                CLUSTER: {
                    "Attributes": {
                        ATTR: {"DataType": "10", "MinInterval": "003c", "MaxInterval": "012c"},
                    }
                }
            },
            # "ConfigureReporting": non-empty so we skip the "never configured yet" branch.
            "ConfigureReporting": {"Ep": {EP: {CLUSTER: {"TimeStamp": 0, "iSQN": {}, "Attributes": {}, "ZigateRequest": {}}}}},
            # Device currently reports back a mismatched MaxInterval (same shape as the
            # real-world report: attribute 050b, MaxInterval '044c' != desired '012C').
            "ReadConfigureReporting": {
                "TimeStamp": time.time(),
                "Ep": {
                    EP: {
                        CLUSTER: {
                            ATTR: {"DataType": "10", "MinInterval": "003c", "MaxInterval": "044c"},
                        }
                    }
                },
            },
        }
    }
    return o


def test_mismatch_retries_are_bounded(cr_module, cr, monkeypatch):
    """Configure Reporting must not be re-sent forever for a persistently mismatched device."""
    sent = []
    monkeypatch.setattr(cr_module, "configure_reporting_for_one_cluster", lambda *a, **k: sent.append(a))

    max_retry = cr_module.MAX_CFG_RPT_MISMATCH_RETRY
    for _ in range(max_retry + 10):
        cr.check_and_redo_configure_reporting_if_needed(NWKID)

    assert len(sent) == max_retry


def test_gives_up_permanently_until_restart(cr_module, cr, monkeypatch):
    """After MAX_CFG_RPT_MISMATCH_RETRY, no more attempts are ever sent again for this run."""
    sent = []
    monkeypatch.setattr(cr_module, "configure_reporting_for_one_cluster", lambda *a, **k: sent.append(a))

    max_retry = cr_module.MAX_CFG_RPT_MISMATCH_RETRY
    for _ in range(max_retry + 3):
        cr.check_and_redo_configure_reporting_if_needed(NWKID)
    assert len(sent) == max_retry

    # No amount of extra heartbeats (or elapsed wall-clock time) brings it back
    for _ in range(50):
        cr.check_and_redo_configure_reporting_if_needed(NWKID)
    assert len(sent) == max_retry

    # A plugin restart clears the counter and gives the device a fresh round of attempts
    from Modules.tools_datastruct import reset_mismatch_retry_datastruct
    reset_mismatch_retry_datastruct(cr, "ConfigureReporting", NWKID)

    cr.check_and_redo_configure_reporting_if_needed(NWKID)

    assert len(sent) == max_retry + 1


def test_retry_state_clears_once_device_matches(cr_module, cr, monkeypatch):
    """Once the device reports back a matching configuration, the backoff counter is dropped."""
    monkeypatch.setattr(cr_module, "configure_reporting_for_one_cluster", MagicMock())

    cr.check_and_redo_configure_reporting_if_needed(NWKID)
    cluster_state = cr.ListOfDevices[NWKID]["ConfigureReporting"]["Ep"][EP][CLUSTER]
    assert "MismatchRetry" in cluster_state

    # Device now reports back the desired MaxInterval
    cr.ListOfDevices[NWKID]["ReadConfigureReporting"]["Ep"][EP][CLUSTER][ATTR]["MaxInterval"] = "012c"

    cr.check_and_redo_configure_reporting_if_needed(NWKID)

    assert "MismatchRetry" not in cluster_state


def test_allow_configure_reporting_retry_logs_give_up_once(cr_module):
    o = object.__new__(cr_module.ConfigureReporting)
    o.log = MagicMock()
    o.ListOfDevices = {NWKID: {}}

    max_retry = cr_module.MAX_CFG_RPT_MISMATCH_RETRY
    results = [cr_module._allow_configure_reporting_retry(o, NWKID, EP, CLUSTER) for _ in range(max_retry)]

    assert all(results)
    # The "giving up" Status log fires exactly once, on the attempt that hits the cap
    assert o.log.logging.call_count == 1

    # Further calls are permanently denied and do not log again
    for _ in range(10):
        assert cr_module._allow_configure_reporting_retry(o, NWKID, EP, CLUSTER) is False
    assert o.log.logging.call_count == 1


def test_clear_configure_reporting_retry_removes_state(cr_module):
    o = object.__new__(cr_module.ConfigureReporting)
    o.log = MagicMock()
    o.ListOfDevices = {NWKID: {}}
    cr_module._allow_configure_reporting_retry(o, NWKID, EP, CLUSTER)
    assert "MismatchRetry" in o.ListOfDevices[NWKID]["ConfigureReporting"]["Ep"][EP][CLUSTER]

    cr_module._clear_configure_reporting_retry(o, NWKID, EP, CLUSTER)

    assert "MismatchRetry" not in o.ListOfDevices[NWKID]["ConfigureReporting"]["Ep"][EP][CLUSTER]


def test_clear_configure_reporting_retry_unknown_device_no_crash(cr_module):
    o = object.__new__(cr_module.ConfigureReporting)
    o.log = MagicMock()
    o.ListOfDevices = {}
    cr_module._clear_configure_reporting_retry(o, "dead", EP, CLUSTER)
