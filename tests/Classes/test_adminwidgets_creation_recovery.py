#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Classes/AdminWidgets.py recovery from a refused admin-widget creation.

The Z4D Status and Z4D Notifications widgets are created from AdminWidgets.__init__
and from nowhere else, and __init__ is called once from onStart. When Domoticz
refuses - "Accept new Hardware Devices" being off is the common case, observed in
the field on 2026-10-05 - the widgets used to be lost for the whole session, and the
only trace was an error carrying no context.

These tests pin the two properties that fixes that: the failure is reported once,
with a context that says which widget and what to do, and the heartbeat comes back
to it a bounded number of times.
"""

import ast
import importlib
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _ensure_stub(name, **attrs):
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    for k, v in attrs.items():
        if not hasattr(mod, k):
            setattr(mod, k, v)
    return mod


@pytest.fixture
def admin_module(monkeypatch):
    """Import Classes.AdminWidgets with its Domoticz-facing collaborators neutralised.

    Same approach as tests/Modules/test_domoCreate_widget_context.py: the stubs only
    fill in a dependency that is absent, and the collaborators are then patched on
    the Classes.AdminWidgets module object itself (it does `from ... import name`),
    so the test does not depend on whether the real module was already imported by
    another test file, nor on pytest's collection order.
    """
    _ensure_stub("DomoticzEx", Configuration=MagicMock(return_value={}), Unit=MagicMock(),
                 Device=MagicMock(), Connection=MagicMock(), Log=MagicMock(),
                 Debug=MagicMock(), Error=MagicMock(), Status=MagicMock())
    _ensure_stub("Modules.domoticzAbstractLayer",
                 retreive_free_unit_for_widget=MagicMock(), domo_create_api=MagicMock(),
                 domo_read_nValue_sValue=MagicMock(return_value=(0, "")),
                 domo_update_api=MagicMock(), domoticz_debug_api=MagicMock(),
                 domoticz_error_api=MagicMock(), domoticz_log_api=MagicMock(),
                 find_first_unit_widget_from_deviceID=MagicMock(return_value=None),
                 is_device_ieee_in_domoticz_db=MagicMock(return_value=False))

    mod = importlib.import_module("Classes.AdminWidgets")

    monkeypatch.setattr(mod, "retreive_free_unit_for_widget", MagicMock(return_value=1))
    monkeypatch.setattr(mod, "is_device_ieee_in_domoticz_db", MagicMock(return_value=False))
    monkeypatch.setattr(mod, "find_first_unit_widget_from_deviceID", MagicMock(return_value=None))
    monkeypatch.setattr(mod, "domo_read_nValue_sValue", MagicMock(return_value=(0, "")))
    monkeypatch.setattr(mod, "domo_update_api", MagicMock())
    return mod


def _make_admin_widgets(admin_module, create_results):
    """Build an AdminWidgets whose domo_create_api returns `create_results` in turn.

    __init__ creates both widgets, so a two-element list covers the startup pass.
    When the list runs out the last value is reused, which is what a persistent
    refusal looks like.
    """
    results = list(create_results)

    def _fake_create(*args, **kwargs):
        return results.pop(0) if len(results) > 1 else results[0]

    admin_module.domo_create_api = _fake_create

    log = MagicMock()
    log.logging = MagicMock()
    pluginconf = MagicMock()
    pluginconf.pluginConf = {"eraseZigatePDM": False}

    return admin_module.AdminWidgets(
        log, pluginconf, {"Name": "Zigbee for Domoticz"}, {}, {}, {}, 2, {})


def _errors(log):
    return [c for c in log.logging.call_args_list if c.args[1] == "Error"]


def _statuses(log):
    return [c for c in log.logging.call_args_list if c.args[1] == "Status"]


class TestCreationSucceeds:

    def test_nothing_is_tracked_and_nothing_is_logged_as_error(self, admin_module):
        admin = _make_admin_widgets(admin_module, [10, 11])
        assert admin.failed_admin_widgets == {}
        assert _errors(admin.log) == []

    def test_a_successful_start_says_nothing_about_recovery(self, admin_module):
        # The "Domoticz is accepting new devices again" line must only appear when
        # something had actually been failing.
        admin = _make_admin_widgets(admin_module, [10, 11])
        assert _statuses(admin.log) == []


class TestCreationRefused:

    def test_both_widgets_are_tracked(self, admin_module):
        admin = _make_admin_widgets(admin_module, [-1])
        assert set(admin.failed_admin_widgets) == {
            admin_module.ADMIN_WIDGET_STATUS, admin_module.ADMIN_WIDGET_NOTIFICATIONS}
        assert list(admin.failed_admin_widgets.values()) == [0, 0]

    def test_each_failure_is_reported_once_with_a_context(self, admin_module):
        admin = _make_admin_widgets(admin_module, [-1])
        errors = _errors(admin.log)
        assert len(errors) == 2

        for call in errors:
            context = call.args[4]
            assert context["Reason"] == "Domoticz refused the admin widget creation"
            assert context["AdminWidget"] in (
                admin_module.ADMIN_WIDGET_STATUS, admin_module.ADMIN_WIDGET_NOTIFICATIONS)
            assert context["HardwareID"] == 2
            assert context["MaxRetries"] == admin_module.ADMIN_WIDGET_MAX_RETRIES
            assert context["Request"]["Name"].startswith("Z4D ")
            assert context["Request"]["DeviceID"].startswith("Z4D-")

    def test_the_error_names_the_setting_to_check(self, admin_module):
        # The refusal reason is only ever in the Domoticz log; the plugin can at
        # least name the cause that accounts for most of them.
        admin = _make_admin_widgets(admin_module, [-1])
        for call in _errors(admin.log):
            assert "Accept new Hardware Devices" in call.args[2]

    def test_the_error_is_logged_against_no_device(self, admin_module):
        # An admin widget belongs to the plugin, not to a Zigbee device: passing a
        # nwkid here would attach somebody else's DeviceInfos to the error.
        admin = _make_admin_widgets(admin_module, [-1])
        for call in _errors(admin.log):
            assert call.args[3] is None

    def test_the_context_is_json_serializable(self, admin_module):
        # The error history is persisted with json.dumps(); one unserializable value
        # costs the whole file.
        admin = _make_admin_widgets(admin_module, [-1])
        for call in _errors(admin.log):
            json.dumps(call.args[4])


class TestRetryBudget:

    def test_a_retry_re_attempts_the_creation(self, admin_module):
        admin = _make_admin_widgets(admin_module, [-1])
        calls = []
        admin_module.domo_create_api = lambda *a, **kw: calls.append(a[2]) or -1

        admin.retry_failed_admin_widget_creation({})
        assert len(calls) == 2

    def test_a_successful_retry_clears_the_widget_and_says_so(self, admin_module):
        admin = _make_admin_widgets(admin_module, [-1])
        admin.log.logging.reset_mock()
        admin_module.domo_create_api = MagicMock(return_value=42)

        admin.retry_failed_admin_widget_creation({})

        assert admin.failed_admin_widgets == {}
        recovered = _statuses(admin.log)
        assert len(recovered) == 2
        assert all("accepting new devices again" in c.args[2] for c in recovered)

    def test_the_failure_is_not_reported_again_on_every_retry(self, admin_module):
        admin = _make_admin_widgets(admin_module, [-1])
        admin.log.logging.reset_mock()

        admin.retry_failed_admin_widget_creation({})

        # Only the give-up message may appear after the first report, and not yet.
        assert _errors(admin.log) == []

    def test_it_gives_up_after_the_budget_and_only_says_so_once(self, admin_module):
        admin = _make_admin_widgets(admin_module, [-1])
        admin.log.logging.reset_mock()

        for _ in range(10):
            admin.retry_failed_admin_widget_creation({})

        errors = _errors(admin.log)
        assert len(errors) == 2
        for call in errors:
            assert "Giving up" in call.args[2]
            assert call.args[4]["Reason"] == "admin widget retry budget exhausted"
            assert call.args[4]["Attempts"] == admin_module.ADMIN_WIDGET_MAX_RETRIES

    def test_the_number_of_attempts_is_bounded(self, admin_module):
        admin = _make_admin_widgets(admin_module, [-1])
        attempts = []
        admin_module.domo_create_api = lambda *a, **kw: attempts.append(a[2]) or -1

        for _ in range(10):
            admin.retry_failed_admin_widget_creation({})

        # Two widgets, ADMIN_WIDGET_MAX_RETRIES attempts each, and no more however
        # many heartbeats go by.
        assert len(attempts) == 2 * admin_module.ADMIN_WIDGET_MAX_RETRIES

    def test_the_give_up_message_names_a_way_out(self, admin_module):
        admin = _make_admin_widgets(admin_module, [-1])
        for _ in range(5):
            admin.retry_failed_admin_widget_creation({})

        giving_up = [c for c in _errors(admin.log) if "Giving up" in c.args[2]]
        assert giving_up
        for call in giving_up:
            assert "restart the plugin" in call.args[2]

    def test_a_widget_created_meanwhile_is_dropped_from_the_retry_list(self, admin_module):
        # Somebody else (a restart of Domoticz, a manual creation) may have made the
        # widget appear; the creator returns early and must still clear the entry.
        admin = _make_admin_widgets(admin_module, [-1])
        admin_module.is_device_ieee_in_domoticz_db = MagicMock(return_value=True)
        admin_module.find_first_unit_widget_from_deviceID = MagicMock(return_value=1)

        admin.retry_failed_admin_widget_creation({})

        assert admin.failed_admin_widgets == {}

    def test_nothing_happens_when_no_widget_ever_failed(self, admin_module):
        admin = _make_admin_widgets(admin_module, [10, 11])
        admin.log.logging.reset_mock()
        admin_module.domo_create_api = MagicMock()

        admin.retry_failed_admin_widget_creation({})

        admin_module.domo_create_api.assert_not_called()
        assert admin.log.logging.call_args_list == []


class TestRetryBudgetMatchesTheDeviceWidgetBudget:

    def test_the_two_budgets_are_the_same(self, admin_module):
        # Not a coincidence worth letting drift: a user who reads one message and
        # then the other should not be told two different numbers.
        #
        # Read out of the source rather than imported: importing Modules.domoCreate
        # here would pull the real module into a namespace this file has stubbed,
        # which is how unrelated tests get broken.
        source = ast.parse(Path("Modules/domoCreate.py").read_text(encoding="utf-8"))
        budget = [
            node.value.value
            for node in source.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name) and target.id == "WIDGET_CREATION_MAX_RETRIES"
        ]
        assert budget == [admin_module.ADMIN_WIDGET_MAX_RETRIES]


class TestHeartbeatWiring:
    """The retry is useless unless something calls it, on the right thread.

    Checked against the source rather than by running the heartbeat: importing
    Modules.heartbeat drags in most of the plugin, and what is being protected here
    is simply that the hook is still there.
    """

    def test_the_heartbeat_asks_for_the_retry_on_a_cadence(self):
        tree = ast.parse(Path("Modules/heartbeat.py").read_text(encoding="utf-8"))
        process = [
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "processListOfDevices"
        ]
        assert len(process) == 1, "processListOfDevices is gone or has moved"

        guarded = [
            node for node in process[0].body
            if isinstance(node, ast.If)
            and "retry_failed_admin_widget_creation" in ast.unparse(node)
            and "WIDGET_CREATION_RETRY" in ast.unparse(node)
        ]
        assert guarded, (
            "processListOfDevices no longer retries the admin widgets on the "
            "WIDGET_CREATION_RETRY cadence - a refused Z4D Status / Z4D Notifications "
            "widget would be lost until the plugin is restarted")


if __name__ == "__main__":
    pytest.main([__file__])
