#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Polling of the devices after a restart of the Zigbee stack (Modules/stackRestartPolling.py).

The module has no plugin dependency and is imported directly. The last test runs the real heartbeat in a
subprocess: importing it here would pull modules tests/conftest.py stubs for the rest of the session.
"""

import json
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from Modules.stackRestartPolling import (DEVICES_PER_HEARTBEAT,
                                         poll_devices_after_stack_restart)

REPO_ROOT = Path(__file__).resolve().parents[2]


def make_plugin(nb_devices=3, force_polling=1):
    devices = {"%04x" % (0x1000 + i): {"Status": "inDB", "Health": "Live"} for i in range(nb_devices)}
    return SimpleNamespace(
        ControllerLink=SimpleNamespace(stack_starts=0),
        ListOfDevices={"0000": {"Status": "inDB"}, "ffff": {"Status": "inDB"}, **devices},
        pluginconf=SimpleNamespace(pluginConf={"forcePollingAfterAction": force_polling}),
        log=MagicMock(),
        stack_starts_seen=0,
        devices_to_poll_after_restart=[],
    )


class Radio:
    def __init__(self):
        self.polled = []
        self.busy = False

    def poll(self, plugin, nwkid):
        if self.busy:
            return True
        self.polled.append(nwkid)
        return False


def heartbeat(plugin, radio, candidate=lambda plugin, nwkid: True):
    poll_devices_after_stack_restart(plugin, candidate, radio.poll)


def restart(plugin):
    plugin.ControllerLink.stack_starts += 1


@pytest.fixture
def started():
    """ A plugin whose first stack start has been seen """
    plugin, radio = make_plugin(), Radio()
    restart(plugin)
    heartbeat(plugin, radio)
    return plugin, radio


def test_first_start_is_not_a_restart(started):
    plugin, radio = started
    assert radio.polled == []
    plugin.log.logging.assert_not_called()


def test_first_start_after_failed_attempts_is_not_a_restart():
    """ No heartbeat reached the polling before the second start: nothing was shown as running meanwhile """
    plugin, radio = make_plugin(), Radio()
    plugin.ControllerLink.stack_starts = 2
    heartbeat(plugin, radio)
    assert radio.polled == []


def test_restart_polls_each_device_once(started):
    plugin, radio = started
    restart(plugin)
    for _ in range(3):
        heartbeat(plugin, radio)
    assert radio.polled == ["1000", "1001", "1002"]
    assert [c.args[1] for c in plugin.log.logging.call_args_list] == ["Status"]


def test_every_restart_polls_again(started):
    plugin, radio = started
    for _ in range(2):
        restart(plugin)
        heartbeat(plugin, radio)
    assert radio.polled == ["1000", "1001", "1002"] * 2


def test_a_second_restart_during_the_polling_starts_it_over():
    plugin, radio = make_plugin(nb_devices=DEVICES_PER_HEARTBEAT + 2), Radio()
    restart(plugin)
    heartbeat(plugin, radio)
    restart(plugin)
    heartbeat(plugin, radio)
    restart(plugin)
    radio.polled.clear()
    for _ in range(3):
        heartbeat(plugin, radio)
    assert len(radio.polled) == DEVICES_PER_HEARTBEAT + 2


def test_only_the_candidates_are_polled(started):
    plugin, radio = started
    restart(plugin)
    heartbeat(plugin, radio, candidate=lambda plugin, nwkid: nwkid == "1001")
    assert radio.polled == ["1001"]


def test_setting_off_polls_nothing():
    plugin, radio = make_plugin(force_polling=0), Radio()
    restart(plugin)
    heartbeat(plugin, radio)
    restart(plugin)
    heartbeat(plugin, radio)
    assert radio.polled == []


def test_a_few_devices_per_heartbeat():
    plugin, radio = make_plugin(nb_devices=2 * DEVICES_PER_HEARTBEAT + 1), Radio()
    restart(plugin)
    heartbeat(plugin, radio)
    restart(plugin)
    counts = []
    for _ in range(4):
        heartbeat(plugin, radio)
        counts.append(len(radio.polled))
    assert counts == [DEVICES_PER_HEARTBEAT, 2 * DEVICES_PER_HEARTBEAT] + [2 * DEVICES_PER_HEARTBEAT + 1] * 2


def test_busy_delays_and_loses_no_device(started):
    plugin, radio = started
    restart(plugin)
    radio.busy = True
    heartbeat(plugin, radio)
    assert radio.polled == []
    radio.busy = False
    heartbeat(plugin, radio)
    assert radio.polled == ["1000", "1001", "1002"]


def test_not_reachable_is_polled_once_it_is_back(started):
    plugin, radio = started
    plugin.ListOfDevices["1001"]["Health"] = "Not Reachable"
    restart(plugin)
    for _ in range(3):
        heartbeat(plugin, radio)
    assert radio.polled == ["1000", "1002"]
    plugin.ListOfDevices["1001"]["Health"] = "Live"
    heartbeat(plugin, radio)
    heartbeat(plugin, radio)
    assert radio.polled == ["1000", "1002", "1001"]


def test_not_reachable_devices_do_not_use_up_the_heartbeat():
    plugin, radio = make_plugin(nb_devices=DEVICES_PER_HEARTBEAT + 1), Radio()
    for nwkid in list(plugin.ListOfDevices)[2:-1]:
        plugin.ListOfDevices[nwkid]["Health"] = "Not Reachable"
    restart(plugin)
    heartbeat(plugin, radio)
    restart(plugin)
    heartbeat(plugin, radio)
    assert radio.polled == ["%04x" % (0x1000 + DEVICES_PER_HEARTBEAT)]


def test_removed_left_and_disabled_devices_are_dropped(started):
    plugin, radio = started
    restart(plugin)
    radio.busy = True
    heartbeat(plugin, radio)
    del plugin.ListOfDevices["1000"]
    plugin.ListOfDevices["1001"]["Status"] = "Leave"
    plugin.ListOfDevices["1002"]["Health"] = "Disabled"
    radio.busy = False
    heartbeat(plugin, radio)
    assert radio.polled == []
    assert plugin.devices_to_poll_after_restart == []


def test_an_exception_does_not_come_back_at_each_heartbeat(started):
    plugin, radio = started
    restart(plugin)

    def poll(plugin, nwkid):
        if nwkid == "1000":
            raise KeyError("Model")
        return radio.poll(plugin, nwkid)

    with pytest.raises(KeyError):
        poll_devices_after_stack_restart(plugin, lambda *_: True, poll)
    poll_devices_after_stack_restart(plugin, lambda *_: True, poll)
    assert radio.polled == ["1001", "1002"]


# ── The real heartbeat, down to the Read Attribute requests ───────────────────

HEARTBEAT_SCRIPT = textwrap.dedent(
    """
    import json, sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import Modules.command  # as plugin.py does, before the heartbeat
    import Modules.heartbeat as hb
    import Modules.readAttributes as ra

    reads = []
    ra.ReadAttributeReq = lambda self, addr, EpIn, EpOut, Cluster, attributes, **kw: reads.append([addr, Cluster, attributes])
    hb.hr_process_device = lambda *a: None
    hb.check_and_reset_device_if_needed = lambda *a: None

    def device(clusters, maccapa="8e", model="", **kw):
        return {"Status": "inDB", "Health": "Live", "Model": model, "MacCapa": maccapa, "IEEE": "", "Param": {},
                "Ep": {"01": {"ClusterType": {"1": "Switch"}, **{c: {} for c in clusters}}}} | kw

    # Not a MagicMock: the heartbeat drains request queues, and a mocked queue is never empty
    plugin = types.SimpleNamespace(
        log=MagicMock(), busy=False, pairing_in_progress=False, HeartbeatCount=1,
        adminWidgets=None, groupmgt=None, networkmap=None, networkenergy=None,
        widget_creation_requests={},
        green_power_requests=types.SimpleNamespace(widgets=set(), store_flush=False),
        pluginconf=types.SimpleNamespace(pluginConf={"forcePollingAfterAction": 1}),
        DeviceConf={"PollingBattery": {"PollingEnabled": 1}},
        ControllerLink=types.SimpleNamespace(stack_starts=1, loadTransmit=lambda: 0),
        stack_starts_seen=0, devices_to_poll_after_restart=[],
    )
    plugin.ListOfDevices = {
        "0000": device(["0006"]),
        "aa01": device(["0000", "0006", "0008"]),
        "aa02": device(["0102"]),
        "aa03": device(["0006"], maccapa="80"),
        "aa04": device(["0201"], maccapa="80", model="PollingBattery"),
        "aa05": device(["0000", "0402"]),
        "aa06": device(["0006"], Health="Not Reachable"),
        "aa07": device(["0006"], Status="failDB_NoUnit"),
        "aa08": device(["0006"]),
    }
    plugin.ListOfDevices["aa08"]["Ep"]["01"]["ClusterType"] = {}  # no widget
    plugin.ListOfDevices["aa04"]["Ep"]["01"]["0201"] = {"0012": 2000}

    out = {}
    hb.processListOfDevices(plugin, {})
    out["first start"] = list(reads)
    hb.processListOfDevices(plugin, {})
    plugin.ControllerLink.stack_starts = 2
    plugin.pairing_in_progress = True
    hb.processListOfDevices(plugin, {})
    out["pairing"] = list(reads)
    plugin.pairing_in_progress = False
    hb.processListOfDevices(plugin, {})
    out["restart"] = list(reads)
    hb.processListOfDevices(plugin, {})
    out["next heartbeat"] = list(reads)
    out["status"] = [c.args[2] for c in plugin.log.logging.call_args_list if c.args[1] == "Status"]
    print(json.dumps(out))
    """
)


def test_heartbeat_reads_the_devices_after_a_restart():
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", HEARTBEAT_SCRIPT],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout.strip().splitlines()[-1])

    assert out["first start"] == []
    assert out["pairing"] == []
    # Mains-powered and PollingEnabled devices only, nothing for a device without a state to read or a widget
    assert out["restart"] == [
        ["aa01", "0006", [0]], ["aa01", "0008", [0]], ["aa02", "0102", [8]], ["aa04", "0201", [18]],
    ]
    assert out["next heartbeat"] == out["restart"]
    assert out["status"] == ["Zigbee stack restarted, reading the state of 3 device(s)"]
