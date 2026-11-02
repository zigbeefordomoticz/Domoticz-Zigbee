#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Green Power devices on the Domoticz side (Modules/greenPower.py) and the
start-up consistency check (Modules/database.py checkListOfDevice2Devices).

Covers:
  remove_green_power_device   store record dropped, flush requested, zigpy
                              REMOVE-DEVICE sent once and nothing else (no
                              ZDO Leave); unknown GPD; ZiGate mode
  green_power_widget_removed  other widgets left → GPD kept; last widget →
                              GPD removed
  green_power_widget_command  logged, nothing sent
  checkListOfDevice2Devices   a GPD widget is not reported as unknown

Modules.greenPower and Modules.database import the real Modules.* package,
which conflicts with the stubs tests/conftest.py installs for the rest of the
session. The checks are therefore executed in a subprocess, as in
test_command_departed_device.py.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GP_IEEE = "000000000155a3b2"

PREAMBLE = textwrap.dedent(
    """
    import sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    sys.modules["DomoticzEx"] = domoticz

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)
    import Modules.database as database
    import Modules.greenPower as gp
    from Classes.PluginStore import PluginStore
    from Modules.greenPowerStore import GP_STORE_NAME, GP_STORE_VERSION

    GP_IEEE = "%s"

    class Log:
        def __init__(self):
            self.records = []
        def logging(self, module, level, message, *args, **kwargs):
            self.records.append((level, str(message)))
        def levels(self):
            return [lvl for lvl, _ in self.records]
        def text(self):
            return " ".join(m for _, m in self.records)

    class Link:
        def __init__(self):
            self.sent = []
        def sendData(self, cmd, datas, *args, **kwargs):
            self.sent.append((cmd, datas))

    def make_plugin(mode="zigpy"):
        p = types.SimpleNamespace()
        p.log = Log()
        p.zigbee_communication = mode
        p.ControllerLink = Link()
        p.flush_list_of_devices = False
        p.IEEE2NWK = {}
        p.ListOfDevices = {}
        store = PluginStore(GP_STORE_NAME, GP_STORE_VERSION)
        store.set(GP_IEEE, {"ieee": GP_IEEE, "nwk": "a3b2", "security_key": "00" * 16})
        p.PluginStores = {GP_STORE_NAME: store}
        return p

    def make_devices(*units):
        return {GP_IEEE: types.SimpleNamespace(Units={u: types.SimpleNamespace(Name="GP switch %%d" %% u, ID=100 + u) for u in units})}
    """ % GP_IEEE
)


def _run(snippet):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(snippet)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, "stdout:\n%s\nstderr:\n%s" % (result.stdout, result.stderr)
    return result.stdout


def test_remove_drops_the_record_and_asks_zigpy_only():
    _run(
        """
        p = make_plugin()

        assert gp.remove_green_power_device(p, GP_IEEE) is True

        assert GP_IEEE not in p.PluginStores[GP_STORE_NAME]
        assert p.flush_list_of_devices is True
        assert p.ControllerLink.sent == [("REMOVE-DEVICE", {"Param1": int(GP_IEEE, 16)})]
        assert "00" * 16 not in p.log.text()
        """
    )


def test_remove_of_an_unknown_device_does_nothing():
    _run(
        """
        p = make_plugin()

        assert gp.remove_green_power_device(p, "0000000001020304") is False

        assert p.ControllerLink.sent == [] and p.flush_list_of_devices is False
        """
    )


def test_remove_in_zigate_mode_sends_nothing():
    _run(
        """
        p = make_plugin(mode="native")

        assert gp.remove_green_power_device(p, GP_IEEE) is True

        assert GP_IEEE not in p.PluginStores[GP_STORE_NAME]
        assert p.ControllerLink.sent == []
        """
    )


def test_device_kept_while_other_widgets_remain():
    _run(
        """
        p = make_plugin()

        assert gp.is_green_power_device_id(p, GP_IEEE)
        gp.green_power_widget_removed(p, make_devices(1, 2), GP_IEEE, 1)

        assert GP_IEEE in p.PluginStores[GP_STORE_NAME]
        assert p.ControllerLink.sent == []
        assert "Error" not in p.log.levels()
        """
    )


def test_device_removed_with_its_last_widget():
    _run(
        """
        p = make_plugin()

        # Domoticz still lists the unit being removed when onDeviceRemoved() runs
        gp.green_power_widget_removed(p, make_devices(2), GP_IEEE, 2)

        assert GP_IEEE not in p.PluginStores[GP_STORE_NAME]
        assert p.ControllerLink.sent == [("REMOVE-DEVICE", {"Param1": int(GP_IEEE, 16)})]
        assert "GP switch 2" in p.log.text()
        """
    )


def test_command_is_logged_and_nothing_sent():
    _run(
        """
        p = make_plugin()

        gp.green_power_widget_command(p, GP_IEEE, 1, "On")

        assert p.ControllerLink.sent == []
        assert p.log.levels() == ["Log"]
        """
    )


def test_not_a_green_power_device():
    _run(
        """
        p = make_plugin()
        assert not gp.is_green_power_device_id(p, "00158d0002c63af3")
        assert not gp.is_green_power_device_id(types.SimpleNamespace(), GP_IEEE)
        """
    )


def test_consistency_check_knows_green_power_widgets():
    _run(
        """
        p = make_plugin()
        p.ListOfDomoticzWidget = {
            101: {"DeviceID": GP_IEEE, "Name": "GP switch 1"},
            102: {"DeviceID": "00158d0002c63af3", "Name": "Lost plug"},
        }

        database.checkListOfDevice2Devices(p, {})

        text = p.log.text()
        assert "GP switch 1 not found" not in text
        assert "Lost plug not found in the plugin" in text
        assert "Error" not in p.log.levels()
        """
    )
