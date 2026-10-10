#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Modules/domoCreate.py:widget_creation_context and for the nwkid/context
now carried by widget-creation failures.

Domoticz.Unit().Create() never raises and never tells us why it refused, so a
widget-creation error is only diagnosable from what we record alongside it. These
tests pin the shape of that context, and that it stays JSON-serializable - the
error history is persisted with json.dumps() and one unserializable value costs
the whole file.
"""

import importlib
import json
import sys
import types
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
def domoCreate_module(monkeypatch):
    """Import Modules.domoCreate and neutralise its Domoticz-facing dependencies.

    The stubs below only fill in a dependency that is *absent*; another test module
    may already have imported the real one. The collaborators are therefore patched
    on Modules.domoCreate itself (it does `from ... import name`, so the name lives
    in its own namespace), which makes the test independent of whether the
    dependency behind it is real or stubbed - and of pytest's collection order.
    """
    _ensure_stub("DomoticzEx", Configuration=MagicMock(return_value={}), Unit=MagicMock(),
                 Device=MagicMock(), Connection=MagicMock(), Log=MagicMock(),
                 Debug=MagicMock(), Error=MagicMock(), Status=MagicMock())
    _ensure_stub("Modules.domoticzAbstractLayer",
                 retreive_free_unit_for_widget=MagicMock(), domo_create_api=MagicMock(),
                 get_unit_counts=MagicMock(), build_widget_reuse_pool=MagicMock())
    _ensure_stub("Modules.domoTools",
                 GetType=MagicMock(), remove_all_widgets=MagicMock(),
                 subtypeRGB_FromProfile_Device_IDs=MagicMock(),
                 subtypeRGB_FromProfile_Device_IDs_onEp2=MagicMock(),
                 update_domoticz_widget=MagicMock())
    _ensure_stub("Modules.switchSelectorWidgets", SWITCH_SELECTORS={})
    _ensure_stub("Modules.tools",
                 get_deviceconf_parameter_value=MagicMock(return_value=None),
                 is_domoticz_new_blind=MagicMock(return_value=False))

    mod = importlib.import_module("Modules.domoCreate")

    monkeypatch.setattr(mod, "domo_create_api", MagicMock())
    monkeypatch.setattr(mod, "retreive_free_unit_for_widget", MagicMock())
    monkeypatch.setattr(mod, "build_widget_reuse_pool", MagicMock(return_value={}))
    monkeypatch.setattr(mod, "get_unit_counts",
                        MagicMock(return_value={"allocated": 0, "free": 254}))
    return mod


class _FakeDomoticzDevice:
    def __init__(self, units):
        self.Units = {u: MagicMock() for u in units}


def _make_self(device=None, nwkid="abcd"):
    obj = MagicMock()
    obj.ListOfDevices = {} if device is None else {nwkid: device}
    # Both are created lazily on the real plugin instance, but a MagicMock would
    # auto-create them as Mocks instead of letting getattr() return the default.
    obj.widget_reuse_pool = {}
    obj.widget_creation_retries = {}
    return obj


# The field case from the forum report: a Tuya TS0041 whose Button_3 widget
# Domoticz refused to create.
def _ts0041():
    return {
        "IEEE": "a4c138e090a23a63",
        "Model": "TS0041",
        "ZDeviceName": "Interrupteur salon",
        "Status": "failDB_NoHardware",
        "Heartbeat": "120",
        "Type": "Button_3",
        "Ep": {"01": {"Type": "Button_3", "ClusterType": {}}},
    }


# ---------------------------------------------------------------------------
# widget_creation_context
# ---------------------------------------------------------------------------

class TestWidgetCreationContext:

    def test_identifies_the_device(self, domoCreate_module):
        obj = _make_self(_ts0041())

        context = domoCreate_module.widget_creation_context(obj, {}, "abcd")

        assert context["NwkId"] == "abcd"
        assert context["IEEE"] == "a4c138e090a23a63"
        assert context["Model"] == "TS0041"
        assert context["ZDeviceName"] == "Interrupteur salon"
        assert context["Status"] == "failDB_NoHardware"
        assert context["Heartbeat"] == "120"

    def test_reports_the_widget_types_expected_per_endpoint(self, domoCreate_module):
        obj = _make_self(_ts0041())

        context = domoCreate_module.widget_creation_context(obj, {}, "abcd")

        assert context["ExpectedTypes"] == {"01": "Button_3"}
        assert context["DeviceType"] == "Button_3"

    def test_endpoints_without_a_type_are_skipped(self, domoCreate_module):
        device = _ts0041()
        device["Ep"] = {"01": {"Type": "Switch"}, "02": {}, "03": {"Type": ""}}
        obj = _make_self(device)

        context = domoCreate_module.widget_creation_context(obj, {}, "abcd")

        assert context["ExpectedTypes"] == {"01": "Switch"}

    def test_non_dict_endpoint_does_not_raise(self, domoCreate_module):
        device = _ts0041()
        device["Ep"] = {"01": "corrupted"}
        obj = _make_self(device)

        context = domoCreate_module.widget_creation_context(obj, {}, "abcd")

        assert context["ExpectedTypes"] == {}

    def test_reports_domoticz_unit_allocation(self, domoCreate_module):
        obj = _make_self(_ts0041())
        devices = {"a4c138e090a23a63": _FakeDomoticzDevice([1, 2, 5])}
        domoCreate_module.get_unit_counts.return_value = {"allocated": 3, "free": 251}

        context = domoCreate_module.widget_creation_context(obj, devices, "abcd")

        assert context["Domoticz"]["allocated"] == 3
        assert context["Domoticz"]["free"] == 251
        assert context["Domoticz"]["units"] == [1, 2, 5]

    def test_units_empty_when_domoticz_does_not_know_the_device(self, domoCreate_module):
        obj = _make_self(_ts0041())
        domoCreate_module.get_unit_counts.return_value = {"allocated": 0, "free": 254}

        context = domoCreate_module.widget_creation_context(obj, {}, "abcd")

        assert context["Domoticz"]["units"] == []

    def test_no_domoticz_section_without_an_ieee(self, domoCreate_module):
        device = _ts0041()
        device["IEEE"] = ""
        obj = _make_self(device)

        context = domoCreate_module.widget_creation_context(obj, {}, "abcd")

        assert "Domoticz" not in context
        assert context["IEEE"] == ""

    def test_reusable_units_reported_when_a_pool_exists(self, domoCreate_module):
        obj = _make_self(_ts0041())
        obj.widget_reuse_pool = {3: {"ID": 77}, 1: {"ID": 42}}

        context = domoCreate_module.widget_creation_context(obj, {}, "abcd")

        assert context["ReusableUnits"] == [1, 3]

    def test_reusable_units_absent_when_pool_is_empty(self, domoCreate_module):
        obj = _make_self(_ts0041())

        assert "ReusableUnits" not in domoCreate_module.widget_creation_context(obj, {}, "abcd")

    def test_extra_keyword_arguments_are_merged(self, domoCreate_module):
        obj = _make_self(_ts0041())

        context = domoCreate_module.widget_creation_context(
            obj, {}, "abcd", Reason="Domoticz refused the creation",
            Ep="01", WidgetType="Button_3", Unit=1)

        assert context["Reason"] == "Domoticz refused the creation"
        assert context["Ep"] == "01"
        assert context["WidgetType"] == "Button_3"
        assert context["Unit"] == 1

    def test_unknown_nwkid_yields_a_context_rather_than_raising(self, domoCreate_module):
        obj = _make_self()

        context = domoCreate_module.widget_creation_context(obj, {}, "ffff", Ep="01")

        assert context["NwkId"] == "ffff"
        assert context["Reason"] == "NwkId not in ListOfDevices"
        assert context["Ep"] == "01"

    def test_missing_fields_fall_back_rather_than_reporting_empty(self, domoCreate_module):
        # Model can legitimately be {} in ListOfDevices, not just "".
        obj = _make_self({"IEEE": "a4c138e090a23a63", "Model": {}, "Ep": {}})

        context = domoCreate_module.widget_creation_context(obj, {}, "abcd")

        assert context["Model"] == "unknown"
        assert context["Status"] == "unknown"
        assert context["ZDeviceName"] == ""
        assert context["Heartbeat"] == "0"

    def test_context_is_json_serializable(self, domoCreate_module):
        obj = _make_self(_ts0041())
        obj.widget_reuse_pool = {1: {"ID": 42}}
        devices = {"a4c138e090a23a63": _FakeDomoticzDevice([1])}

        context = domoCreate_module.widget_creation_context(
            obj, devices, "abcd", Reason="Domoticz refused the creation", Unit=1)

        # json.dumps() is exactly what persists the error history.
        assert json.loads(json.dumps(context))["Model"] == "TS0041"

    def test_context_does_not_alias_the_device_entry(self, domoCreate_module):
        device = _ts0041()
        obj = _make_self(device)

        context = domoCreate_module.widget_creation_context(obj, {}, "abcd")
        context["ExpectedTypes"]["02"] = "injected"

        assert set(device["Ep"]) == {"01"}


# ---------------------------------------------------------------------------
# Failure sites now identify the device
# ---------------------------------------------------------------------------

class TestCreateDomoticzWidgetErrorReporting:

    def _run(self, domoCreate_module, monkeypatch, create_result):
        obj = _make_self(_ts0041())
        obj.pluginParameters = {"Name": "zigbeeusb"}
        domoCreate_module.retreive_free_unit_for_widget.return_value = 1
        domoCreate_module.domo_create_api.return_value = create_result
        monkeypatch.setattr(domoCreate_module, "deviceName",
                            MagicMock(return_value="TS0041_Button_3-a4c138e090a23a63-01"))
        monkeypatch.setattr(domoCreate_module, "_try_reuse_widget", MagicMock(return_value=None))

        result = domoCreate_module.createDomoticzWidget(
            obj, {}, "abcd", "a4c138e090a23a63", "01", "Button_3",
            widgetOptions={"LevelNames": "Off|Click"})
        return obj, result

    def test_domo_create_api_receives_the_nwkid(self, domoCreate_module, monkeypatch):
        self._run(domoCreate_module, monkeypatch, 42)

        assert domoCreate_module.domo_create_api.call_args.kwargs["nwkid"] == "abcd"

    def test_refusal_logs_one_error_with_nwkid_and_context(self, domoCreate_module, monkeypatch):
        obj, result = self._run(domoCreate_module, monkeypatch, -1)

        assert result is None
        assert obj.ListOfDevices["abcd"]["Status"] == "failDB_NoHardware"

        errors = [c for c in obj.log.logging.call_args_list if c.args[1] == "Error"]
        assert len(errors) == 1

        _, _, message, nwkid, context = errors[0].args
        assert nwkid == "abcd"
        assert context["Reason"] == "Domoticz refused the creation"
        assert context["Unit"] == 1
        assert context["Ep"] == "01"
        assert context["WidgetType"] == "Button_3"
        assert context["Model"] == "TS0041"
        # The message must name the device, not only the unit.
        assert "abcd" in message and "Button_3" in message

    def test_no_free_unit_logs_its_own_reason(self, domoCreate_module, monkeypatch):
        obj = _make_self(_ts0041())
        domoCreate_module.retreive_free_unit_for_widget.return_value = None
        monkeypatch.setattr(domoCreate_module, "_try_reuse_widget", MagicMock(return_value=None))

        result = domoCreate_module.createDomoticzWidget(
            obj, {}, "abcd", "a4c138e090a23a63", "01", "Button_3", widgetType="Switch")

        assert result is None
        assert obj.ListOfDevices["abcd"]["Status"] == "failDB_NoUnit"

        errors = [c for c in obj.log.logging.call_args_list if c.args[1] == "Error"]
        assert len(errors) == 1
        assert errors[0].args[3] == "abcd"
        assert errors[0].args[4]["Reason"] == "no free Domoticz unit"


class TestSwitchSelectorDoesNotDuplicateTheError:

    def test_selector_failure_adds_no_second_error(self, domoCreate_module, monkeypatch):
        obj = _make_self(_ts0041())
        monkeypatch.setitem(
            domoCreate_module.SWITCH_SELECTORS, "Button_3",
            {"LevelNames": "Off|Click|Double Click|Long Click", "SelectorStyle": 1})
        monkeypatch.setattr(domoCreate_module, "createDomoticzWidget", MagicMock(return_value=None))

        result = domoCreate_module.create_switch_selector_widget(
            obj, {}, "abcd", "a4c138e090a23a63", "01", "Button_3")

        # Still None, so CreateDomoDevice's "neither helper recognized it" branch
        # (which tests for False) is unaffected.
        assert result is None
        assert [c for c in obj.log.logging.call_args_list if c.args[1] == "Error"] == []


class TestRetryFailedWidgetCreation:

    def test_retry_message_names_the_device(self, domoCreate_module, monkeypatch):
        obj = _make_self(_ts0041())
        monkeypatch.setattr(domoCreate_module, "CreateDomoDevice", MagicMock())

        domoCreate_module.retry_failed_widget_creation(obj, {}, "abcd")

        message = obj.log.logging.call_args.args[2]
        assert "failDB_NoHardware" in message
        assert "Interrupteur salon" in message
        assert "TS0041" in message
        assert "a4c138e090a23a63" in message
        domoCreate_module.CreateDomoDevice.assert_called_once_with(obj, {}, "abcd")

    def test_retry_message_tolerates_a_bare_entry(self, domoCreate_module, monkeypatch):
        obj = _make_self({"Status": "failDB_NoUnit"})
        monkeypatch.setattr(domoCreate_module, "CreateDomoDevice", MagicMock())

        domoCreate_module.retry_failed_widget_creation(obj, {}, "abcd")

        message = obj.log.logging.call_args.args[2]
        assert "unnamed" in message and "unknown" in message

    def test_retry_reports_the_attempt_number(self, domoCreate_module, monkeypatch):
        obj = _make_self(_ts0041())
        monkeypatch.setattr(domoCreate_module, "CreateDomoDevice", MagicMock())

        domoCreate_module.retry_failed_widget_creation(obj, {}, "abcd")

        assert "attempt 1 of 2" in obj.log.logging.call_args.args[2]


# ---------------------------------------------------------------------------
# Retry budget
# ---------------------------------------------------------------------------

class TestRetryBudget:
    """The retry must stop after WIDGET_CREATION_MAX_RETRIES.

    The heartbeat keeps scheduling a retry every 5 minutes for as long as the
    device stays in a failDB_* state, so without a budget the same error is
    reprinted for the whole session. Domoticz logs the actual refusal reason on
    its own side and never returns it, so retrying cannot clear the cause.
    """

    def _retry(self, mod, obj, times):
        for _ in range(times):
            mod.retry_failed_widget_creation(obj, {}, "abcd")

    def test_creation_is_attempted_only_up_to_the_budget(self, domoCreate_module, monkeypatch):
        create = MagicMock()
        monkeypatch.setattr(domoCreate_module, "CreateDomoDevice", create)
        obj = _make_self(_ts0041())

        self._retry(domoCreate_module, obj, 10)

        assert create.call_count == domoCreate_module.WIDGET_CREATION_MAX_RETRIES

    def test_budget_default_is_two(self, domoCreate_module):
        assert domoCreate_module.WIDGET_CREATION_MAX_RETRIES == 2

    def test_giving_up_is_reported_exactly_once(self, domoCreate_module, monkeypatch):
        monkeypatch.setattr(domoCreate_module, "CreateDomoDevice", MagicMock())
        obj = _make_self(_ts0041())

        self._retry(domoCreate_module, obj, 20)

        errors = [c for c in obj.log.logging.call_args_list if c.args[1] == "Error"]
        assert len(errors) == 1
        assert "giving up for this session" in errors[0].args[2]

    def test_giving_up_names_the_device_and_the_way_out(self, domoCreate_module, monkeypatch):
        monkeypatch.setattr(domoCreate_module, "CreateDomoDevice", MagicMock())
        obj = _make_self(_ts0041())

        self._retry(domoCreate_module, obj, 3)

        error = [c for c in obj.log.logging.call_args_list if c.args[1] == "Error"][0]
        message = error.args[2]
        assert "Interrupteur salon" in message and "a4c138e090a23a63" in message
        # The user must be told what actually unblocks it.
        assert "restart the plugin" in message and "recreate widgets" in message
        assert error.args[3] == "abcd"
        assert error.args[4]["Reason"] == "retry budget exhausted"

    def test_device_is_not_dropped_when_giving_up(self, domoCreate_module, monkeypatch):
        monkeypatch.setattr(domoCreate_module, "CreateDomoDevice", MagicMock())
        obj = _make_self(_ts0041())

        self._retry(domoCreate_module, obj, 5)

        # Losing the entry would lose Ep/Cluster/ClusterType - the whole reason
        # failDB_NoHardware is treated as recoverable rather than terminal.
        assert obj.ListOfDevices["abcd"]["Status"] == "failDB_NoHardware"
        assert obj.ListOfDevices["abcd"]["Ep"] == {"01": {"Type": "Button_3", "ClusterType": {}}}

    def test_budget_is_per_device(self, domoCreate_module, monkeypatch):
        create = MagicMock()
        monkeypatch.setattr(domoCreate_module, "CreateDomoDevice", create)
        obj = _make_self(_ts0041())
        obj.ListOfDevices["ef01"] = dict(_ts0041(), IEEE="a4c138e090a23a64")

        self._retry(domoCreate_module, obj, 10)
        for _ in range(10):
            domoCreate_module.retry_failed_widget_creation(obj, {}, "ef01")

        assert create.call_count == 2 * domoCreate_module.WIDGET_CREATION_MAX_RETRIES

    def test_success_restores_a_full_budget(self, domoCreate_module, monkeypatch):
        obj = _make_self(_ts0041())

        def succeed(_self, _devices, nwkid):
            _self.ListOfDevices[nwkid]["Status"] = "inDB"

        monkeypatch.setattr(domoCreate_module, "CreateDomoDevice", MagicMock(side_effect=succeed))
        domoCreate_module.retry_failed_widget_creation(obj, {}, "abcd")

        assert obj.widget_creation_retries == {}

    def test_reset_grants_a_new_budget_for_one_device(self, domoCreate_module, monkeypatch):
        create = MagicMock()
        monkeypatch.setattr(domoCreate_module, "CreateDomoDevice", create)
        obj = _make_self(_ts0041())

        self._retry(domoCreate_module, obj, 10)
        domoCreate_module.reset_widget_creation_retries(obj, "abcd")
        self._retry(domoCreate_module, obj, 10)

        assert create.call_count == 2 * domoCreate_module.WIDGET_CREATION_MAX_RETRIES

    def test_reset_without_a_nwkid_clears_every_device(self, domoCreate_module, monkeypatch):
        monkeypatch.setattr(domoCreate_module, "CreateDomoDevice", MagicMock())
        obj = _make_self(_ts0041())
        obj.widget_creation_retries = {"abcd": 2, "ef01": 1}

        domoCreate_module.reset_widget_creation_retries(obj)

        assert obj.widget_creation_retries == {}

    def test_giving_up_is_reported_again_after_a_reset(self, domoCreate_module, monkeypatch):
        monkeypatch.setattr(domoCreate_module, "CreateDomoDevice", MagicMock())
        obj = _make_self(_ts0041())

        self._retry(domoCreate_module, obj, 5)
        domoCreate_module.reset_widget_creation_retries(obj, "abcd")
        self._retry(domoCreate_module, obj, 5)

        errors = [c for c in obj.log.logging.call_args_list if c.args[1] == "Error"]
        assert len(errors) == 2

    def test_counter_is_created_lazily_on_a_plain_object(self, domoCreate_module, monkeypatch):
        # The real plugin instance has no widget_creation_retries attribute until
        # the first recoverable failure; startup must not have to create it.
        monkeypatch.setattr(domoCreate_module, "CreateDomoDevice", MagicMock())

        class Plugin:
            def __init__(self):
                self.ListOfDevices = {"abcd": _ts0041()}
                self.log = MagicMock()

        obj = Plugin()
        assert not hasattr(obj, "widget_creation_retries")

        domoCreate_module.retry_failed_widget_creation(obj, {}, "abcd")

        assert obj.widget_creation_retries == {"abcd": 1}


# ---------------------------------------------------------------------------
# Deferred widget creation (WebUI requests)
# ---------------------------------------------------------------------------

class TestRequestWidgetCreation:
    """The WebUI endpoints run in their own thread and must not touch the
    Domoticz API; they record a request that the heartbeat carries out."""

    def test_request_is_queued_not_executed(self, domoCreate_module, monkeypatch):
        create = MagicMock()
        monkeypatch.setattr(domoCreate_module, "CreateDomoDevice", create)
        obj = _make_self(_ts0041())
        obj.widget_creation_requests = {}

        domoCreate_module.request_widget_creation(obj, "abcd", "from the WebUI")

        create.assert_not_called()
        assert obj.widget_creation_requests["abcd"]["reason"] == "from the WebUI"
        assert obj.widget_creation_requests["abcd"]["remove_existing_widgets"] is False

    def test_remove_flag_is_recorded(self, domoCreate_module):
        obj = _make_self(_ts0041())
        obj.widget_creation_requests = {}

        domoCreate_module.request_widget_creation(
            obj, "abcd", "model changed", remove_existing_widgets=True)

        assert obj.widget_creation_requests["abcd"]["remove_existing_widgets"] is True

    def test_queue_is_created_lazily_on_a_plain_object(self, domoCreate_module):
        class Plugin:
            def __init__(self):
                self.log = MagicMock()

        obj = Plugin()
        assert not hasattr(obj, "widget_creation_requests")

        domoCreate_module.request_widget_creation(obj, "abcd", "from the WebUI")

        assert "abcd" in obj.widget_creation_requests

    def test_repeated_requests_are_deduplicated(self, domoCreate_module):
        obj = _make_self(_ts0041())
        obj.widget_creation_requests = {}

        domoCreate_module.request_widget_creation(obj, "abcd", "first")
        domoCreate_module.request_widget_creation(obj, "abcd", "second")

        assert len(obj.widget_creation_requests) == 1
        assert obj.widget_creation_requests["abcd"]["reason"] == "second"

    def test_a_later_weaker_request_does_not_drop_the_removal(self, domoCreate_module):
        obj = _make_self(_ts0041())
        obj.widget_creation_requests = {}

        domoCreate_module.request_widget_creation(
            obj, "abcd", "model changed", remove_existing_widgets=True)
        domoCreate_module.request_widget_creation(obj, "abcd", "recreate")

        assert obj.widget_creation_requests["abcd"]["remove_existing_widgets"] is True


class TestProcessWidgetCreationRequests:

    def _prepare(self, mod, monkeypatch, device=None):
        obj = _make_self(device if device is not None else _ts0041())
        obj.widget_creation_requests = {}
        create = MagicMock()
        remove = MagicMock()
        overwrite = MagicMock()
        monkeypatch.setattr(mod, "CreateDomoDevice", create)
        monkeypatch.setattr(mod, "remove_all_widgets", remove)
        monkeypatch.setattr(mod, "over_write_type_from_deviceconf", overwrite)
        return obj, create, remove, overwrite

    def test_nothing_queued_is_a_no_op(self, domoCreate_module, monkeypatch):
        obj, create, _, _ = self._prepare(domoCreate_module, monkeypatch)

        domoCreate_module.process_widget_creation_requests(obj, {})

        create.assert_not_called()

    def test_missing_queue_attribute_is_a_no_op(self, domoCreate_module, monkeypatch):
        obj, create, _, _ = self._prepare(domoCreate_module, monkeypatch)
        del obj.widget_creation_requests

        class Plugin:
            log = MagicMock()

        domoCreate_module.process_widget_creation_requests(Plugin(), {})
        create.assert_not_called()

    def test_queued_request_is_carried_out(self, domoCreate_module, monkeypatch):
        obj, create, remove, overwrite = self._prepare(domoCreate_module, monkeypatch)
        devices = {}
        domoCreate_module.request_widget_creation(obj, "abcd", "from the WebUI")

        domoCreate_module.process_widget_creation_requests(obj, devices)

        overwrite.assert_called_once_with(obj, devices, "abcd")
        create.assert_called_once_with(obj, devices, "abcd")
        remove.assert_not_called()
        assert obj.ListOfDevices["abcd"]["Status"] == "CreateDB"

    def test_queue_is_drained(self, domoCreate_module, monkeypatch):
        obj, create, _, _ = self._prepare(domoCreate_module, monkeypatch)
        domoCreate_module.request_widget_creation(obj, "abcd", "from the WebUI")

        domoCreate_module.process_widget_creation_requests(obj, {})
        domoCreate_module.process_widget_creation_requests(obj, {})

        assert obj.widget_creation_requests == {}
        assert create.call_count == 1

    def test_removal_is_performed_before_creation(self, domoCreate_module, monkeypatch):
        obj, create, remove, _ = self._prepare(domoCreate_module, monkeypatch)
        order = []
        remove.side_effect = lambda *a: order.append("remove")
        create.side_effect = lambda *a: order.append("create")
        domoCreate_module.request_widget_creation(
            obj, "abcd", "model changed", remove_existing_widgets=True)

        domoCreate_module.process_widget_creation_requests(obj, {})

        assert order == ["remove", "create"]

    def test_several_devices_are_all_served(self, domoCreate_module, monkeypatch):
        obj, create, _, _ = self._prepare(domoCreate_module, monkeypatch)
        obj.ListOfDevices["ef01"] = dict(_ts0041(), IEEE="a4c138e090a23a64")
        domoCreate_module.request_widget_creation(obj, "abcd", "one")
        domoCreate_module.request_widget_creation(obj, "ef01", "two")

        domoCreate_module.process_widget_creation_requests(obj, {})

        assert sorted(c.args[2] for c in create.call_args_list) == ["abcd", "ef01"]

    def test_request_for_a_vanished_device_is_dropped(self, domoCreate_module, monkeypatch):
        obj, create, _, _ = self._prepare(domoCreate_module, monkeypatch)
        domoCreate_module.request_widget_creation(obj, "dead", "from the WebUI")

        domoCreate_module.process_widget_creation_requests(obj, {})

        create.assert_not_called()
        assert obj.widget_creation_requests == {}
        warnings = [c for c in obj.log.logging.call_args_list if c.args[1] == "Warning"]
        assert len(warnings) == 1

    def test_user_request_grants_a_fresh_retry_budget(self, domoCreate_module, monkeypatch):
        # A device the retry budget has given up on must become eligible again
        # when the user explicitly asks for a recreation.
        obj, create, _, _ = self._prepare(domoCreate_module, monkeypatch)
        obj.widget_creation_retries = {"abcd": domoCreate_module.WIDGET_CREATION_MAX_RETRIES + 1}
        domoCreate_module.request_widget_creation(obj, "abcd", "from the WebUI")

        domoCreate_module.process_widget_creation_requests(obj, {})

        assert "abcd" not in obj.widget_creation_retries
