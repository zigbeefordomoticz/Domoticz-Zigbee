#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Green Power device widgets (Modules/greenPowerWidgets.py), end to end through
the real widget code, against a fake DomoticzEx:

  configuration  certified match, most specific first (DeviceID + Manufacturer
                 + Model > DeviceID + Manufacturer > DeviceID); built-in
                 fallback from the declared commands, or from the Device ID
                 when none declared; unknown GPD → no widget
  creation       queued, carried out from the heartbeat: a Switch with the
                 Zigbee path's definition (SIMPLE_WIDGET), ClusterType kept in
                 the store record; nothing created twice; certified NickName used
  update         Off / On / Toggle → the Switch through maj_domo_widgets()
                 (NwkId None): nValue/sValue written, no ListOfDevices entry
                 created, the Zigbee device holding the GPD's alias NwkId untouched

The real Modules.* package conflicts with the stubs tests/conftest.py installs
for the rest of the session, so the checks run in a subprocess, as in
test_command_departed_device.py.
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

    class FakeUnit:
        next_id = 100
        def __init__(self, DeviceID=None, Name=None, Unit=None, TypeName=None, Type=None, Subtype=None, Switchtype=None, Options=None, Image=None):
            self.DeviceID, self.Name, self.Unit = DeviceID, Name, Unit
            self.TypeName, self.Type, self.Subtype, self.Switchtype = TypeName, Type, Subtype, Switchtype
            # Read-back names of a DomoticzEx unit (constructor: Subtype / Switchtype)
            self.SubType, self.SwitchType = Subtype, Switchtype
            self.Options = Options or {}
            self.nValue, self.sValue, self.Color, self.BatteryLevel, self.SignalLevel = 0, "", "", 255, 12
            self.ID = None
            self.updates = 0
        def Create(self):
            FakeUnit.next_id += 1
            self.ID = FakeUnit.next_id
            DEVICES.setdefault(self.DeviceID, types.SimpleNamespace(Units={}, TimedOut=0, DeviceID=self.DeviceID)).Units[self.Unit] = self
        def Update(self, *args, **kwargs):
            self.updates += 1
        def Delete(self):
            pass

    DEVICES = {}
    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Unit = FakeUnit
    domoticz.Configuration = MagicMock(return_value={})
    sys.modules["DomoticzEx"] = domoticz

    # Import order as in the plugin: Modules.domoMaj only imports cleanly once Modules.readAttributes
    # is loaded (pre-existing cycle domoMaj → linky → readAttributes → tuya → domoMaj)
    import Modules.tools  # noqa: F401
    import Modules.readAttributes  # noqa: F401
    import Modules.greenPowerWidgets as gpw
    from Classes.PluginStore import PluginStore
    from Modules.greenPowerStore import GP_STORE_NAME, GP_STORE_VERSION, request_gp_widget_creation

    GP_IEEE = "000000000155a3b2"
    ALIAS = "a3b2"

    class Log:
        def __init__(self):
            self.records = []
        def logging(self, module, level, message, *args, **kwargs):
            self.records.append((level, str(message), args[1] if len(args) > 1 else kwargs.get("context")))
        def errors(self):
            return [(m, c) for lvl, m, c in self.records if lvl == "Error"]
        def text(self):
            return " ".join(m for _, m, _ in self.records)

    def gp_record(**fields):
        record = {"ieee": GP_IEEE, "nwk": ALIAS, "application_id": 0, "src_id": 0x0155A3B2, "device_id": 0x02,
                  "manufacturer_id": None, "model_id": None, "commands": [0x20, 0x21, 0x22],
                  "security_key": "00" * 16, "frame_counter": 1}
        record.update(fields)
        return record

    def make_plugin(record=None, device_conf=None):
        p = types.SimpleNamespace()
        p.log = Log()
        p.pluginParameters = {"Name": "Zigbee"}
        p.pluginconf = types.SimpleNamespace(pluginConf={"forceSwitchSelectorPushButton": 0, "logDeviceUpdate": 0})
        p.IEEE2NWK = {}
        p.ListOfDevices = {}
        p.ListOfDomoticzWidget = {}
        p.DeviceConf = device_conf or {}
        p.groupmgt = None
        p.pairing_in_progress = False
        p.ZiGateModel = None
        p.flush_list_of_devices = False
        store = PluginStore(GP_STORE_NAME, GP_STORE_VERSION)
        store.set(GP_IEEE, record or gp_record())
        p.PluginStores = {GP_STORE_NAME: store}
        return p

    def commission(p):
        request_gp_widget_creation(p, GP_IEEE)
        gpw.process_gp_widget_creation_requests(p, DEVICES)

    def stored(p):
        return p.PluginStores[GP_STORE_NAME].get(GP_IEEE)

    def the_unit():
        units = DEVICES[GP_IEEE].Units
        assert len(units) == 1, units
        return next(iter(units.values()))
    """
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


# ─── Configuration ──────────────────────────────────────────────────────────

def test_certified_match_most_specific_first():
    _run(
        """
        conf = {
            "GP-OnOff": {"GreenPower": {"DeviceID": "02"}, "Ep": {}},
            "Vendor-Any": {"GreenPower": {"DeviceID": "02", "ManufacturerID": "107d"}, "Ep": {}},
            "Vendor-Model": {"GreenPower": {"DeviceID": "02", "ManufacturerID": "107D", "ModelID": "0042"}, "Ep": {}},
            "Other": {"GreenPower": {"DeviceID": "07"}, "Ep": {}},
            "Zigbee": {"Ep": {}},
        }
        p = make_plugin(device_conf=conf)

        assert gpw.find_gp_device_config(p, gp_record(manufacturer_id=0x107D, model_id=0x42))[0] == "Vendor-Model"
        assert gpw.find_gp_device_config(p, gp_record(manufacturer_id=0x107D, model_id=0x43))[0] == "Vendor-Any"
        assert gpw.find_gp_device_config(p, gp_record(manufacturer_id=0x1234))[0] == "GP-OnOff"
        """
    )


def test_builtin_fallback_from_commands_or_device_id():
    _run(
        """
        p = make_plugin()

        name, conf = gpw.find_gp_device_config(p, gp_record(device_id=0x07, commands=[0x22]))
        assert name == "GreenPower-OnOff" and conf["Ep"]["01"]["Type"] == "Switch"

        # Declared no command: standard set of the On/Off switch Device ID
        assert gpw.find_gp_device_config(p, gp_record(commands=[]))[0] == "GreenPower-OnOff"

        # Nothing the first version knows
        assert gpw.find_gp_device_config(p, gp_record(device_id=0x30, commands=[0xA0])) == (None, None)
        """
    )


# ─── Creation ───────────────────────────────────────────────────────────────

def test_switch_created_from_the_heartbeat_with_the_zigbee_definition():
    _run(
        """
        from Modules.domoCreate import SIMPLE_WIDGET
        p = make_plugin()

        commission(p)

        unit = the_unit()
        switch = SIMPLE_WIDGET["Switch"]
        assert (unit.Type, unit.Subtype) == (switch["Type"], switch["Subtype"])
        # domo_create_api() leaves out a 0 Switchtype, for a Zigbee Switch too (Domoticz default: On/Off)
        assert unit.Switchtype in (None, switch["Switchtype"])
        assert unit.Name == "Zigbee - GreenPower-OnOff_Switch-%s-01" % GP_IEEE
        record = stored(p)
        assert record["Model"] == "GreenPower-OnOff"
        assert record["Ep"] == {"01": {"ClusterType": {str(unit.ID): "Switch"}}}
        assert p.flush_list_of_devices is True
        assert p.ListOfDevices == {} and p.log.errors() == []
        assert not getattr(p, "gp_widget_creation_requests")
        """
    )


def test_widgets_never_created_twice():
    _run(
        """
        p = make_plugin()
        commission(p)

        commission(p)

        assert len(DEVICES[GP_IEEE].Units) == 1
        """
    )


def test_certified_nickname_used():
    _run(
        """
        conf = {"PTM-Test": {"GreenPower": {"DeviceID": "02"}, "NickName": "GPSwitch", "Ep": {"01": {"0006": "", "Type": "Switch"}}}}
        p = make_plugin(device_conf=conf)

        commission(p)

        assert the_unit().Name.endswith("GPSwitch_Switch-%s-01" % GP_IEEE)
        assert stored(p)["Model"] == "PTM-Test"
        """
    )


def test_unknown_gpd_gets_no_widget():
    _run(
        """
        p = make_plugin(gp_record(device_id=0x30, commands=[0xA0]))

        commission(p)

        assert GP_IEEE not in DEVICES
        assert "unknown model" in p.log.text()
        assert p.log.errors() == []
        """
    )


def test_unsupported_widget_type_is_an_error_with_code():
    _run(
        """
        conf = {"GP-Odd": {"GreenPower": {"DeviceID": "02"}, "Ep": {"01": {"Type": "NoSuchWidget"}}}}
        p = make_plugin(device_conf=conf)

        commission(p)

        assert [c for _, c in p.log.errors()] == [{"Error code": "GPWIDGET-TYPE-01", "WidgetType": "NoSuchWidget"}]
        """
    )


# ─── Update ─────────────────────────────────────────────────────────────────

def test_on_off_toggle_update_the_switch():
    _run(
        """
        p = make_plugin()
        commission(p)
        unit = the_unit()

        gpw.update_gp_widgets(p, DEVICES, GP_IEEE, 0x21)
        assert (unit.nValue, unit.sValue) == (1, "On")

        gpw.update_gp_widgets(p, DEVICES, GP_IEEE, 0x20)
        assert (unit.nValue, unit.sValue) == (0, "Off")

        gpw.update_gp_widgets(p, DEVICES, GP_IEEE, 0x22)
        assert (unit.nValue, unit.sValue) == (1, "On")
        gpw.update_gp_widgets(p, DEVICES, GP_IEEE, 0x22)
        assert (unit.nValue, unit.sValue) == (0, "Off")

        assert unit.BatteryLevel == 255
        assert p.ListOfDevices == {} and p.log.errors() == []
        """
    )


def test_zigbee_device_on_the_alias_nwkid_untouched():
    _run(
        """
        p = make_plugin()
        commission(p)
        zigbee = {"IEEE": "00158d0002c63af3", "Ep": {"01": {"ClusterType": {}}}, "Battery": 42, "LQI": 200}
        p.ListOfDevices[ALIAS] = dict(zigbee)
        p.IEEE2NWK["00158d0002c63af3"] = ALIAS

        gpw.update_gp_widgets(p, DEVICES, GP_IEEE, 0x21)

        assert the_unit().BatteryLevel == 255  # not the Zigbee device's 42
        assert p.ListOfDevices[ALIAS] == zigbee
        """
    )


def test_command_without_translation_or_widget_does_nothing():
    _run(
        """
        p = make_plugin()

        gpw.update_gp_widgets(p, DEVICES, GP_IEEE, 0x21)  # no widget yet
        commission(p)
        gpw.update_gp_widgets(p, DEVICES, GP_IEEE, 0x10)  # scenes: not in the first version

        assert (the_unit().nValue, the_unit().updates) == (0, 0)
        assert p.log.errors() == []
        """
    )
