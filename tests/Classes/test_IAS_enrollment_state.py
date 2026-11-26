#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the IAS enrollment state of an endpoint (Classes/IAS.py).

An endpoint is taken as enrolled only when the device reports ZoneState 0x01, not when the
plugin sends its Zone Enroll Response: the response can be lost (seen on a HEIMAN water
sensor, the plugin then believed it enrolled and never enrolled it again).

Coverage:
  - Enroll Request answered (expected and spontaneous): the Ep waits for the device
  - ZoneState 0x01 makes the Ep and the device enrolled
  - ZoneState 0x00 after the response restarts the enrollment (CIE address write)
  - a device enrolled earlier keeps its status when it asks again, the response is still sent

The real Modules.* package conflicts with the stubs tests/conftest.py installs
for the rest of the session. The checks are therefore executed in a subprocess,
fully isolated from the pytest session.
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

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)
    import Modules.readAttributes  # noqa: F401  (same reason)
    import Classes.IAS as ias

    for _name in ("zcl_ias_zone_enroll_response", "zcl_read_attribute", "zcl_write_attribute",
                  "bindDevice", "zdp_simple_descriptor_request"):
        setattr(ias, _name, MagicMock(name=_name))

    NWKID = "9d5a"

    def manager(ias_record=None):
        device = {"IEEE": "ec1bbdfffee4cedd", "Ep": {"01": {"0500": {}}}, "Model": "WaterSensor-EF-3.0"}
        if ias_record is not None:
            device["IAS"] = ias_record
        devices = {NWKID: device}
        log = MagicMock()
        mgr = ias.IAS_Zone_Management(MagicMock(), MagicMock(), devices, {}, {}, log, "zigpy",
                                      None, {}, False, "00124b0000000001")
        for _name in ("zcl_ias_zone_enroll_response", "zcl_read_attribute", "zcl_write_attribute"):
            getattr(ias, _name).reset_mock()
        return mgr, devices[NWKID]

    def waiting_for_request():
        return {"Auto-Enrollment": {"Status": "Enrollment In Progress",
                                    "Ep": {"01": {"Status": "Wait for Enrollment request"}}}}

    def zone_state(value):
        # Read Attributes Response on 0x0500, as Read_Attribute_Rsp passes it: sqn, NwkId, Ep, cluster, then
        # ZoneState (0x0000): status 00, type 0x30, size 1, value
        return "01" + NWKID + "01" + "0500" + "0000" + "00" + "30" + "0001" + value

    def ep_status(device):
        return device["IAS"]["Auto-Enrollment"]["Ep"]["01"]["Status"]
    """
)


def _run(body):
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(body)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_expected_enroll_request_waits_for_the_device():
    _run(
        """
        mgr, device = manager(waiting_for_request())
        mgr.IAS_zone_enroll_request(NWKID, "01", "002a", "16")
        ias.zcl_ias_zone_enroll_response.assert_called_once()
        assert ep_status(device) == ias.ENROLL_RESPONSE_SENT
        assert not ias.is_device_enrollment_completed(mgr, NWKID)
        """
    )


def test_spontaneous_enroll_request_waits_for_the_device():
    _run(
        """
        mgr, device = manager()
        mgr.IAS_zone_enroll_request(NWKID, "01", "002a", "16")
        ias.zcl_ias_zone_enroll_response.assert_called_once()
        assert ep_status(device) == ias.ENROLL_RESPONSE_SENT
        assert not ias.is_device_enrollment_completed(mgr, NWKID)
        """
    )


def test_zone_state_enrolled_completes_the_enrollment():
    _run(
        """
        mgr, device = manager(waiting_for_request())
        mgr.IAS_zone_enroll_request(NWKID, "01", "002a", "16")
        mgr.IAS_CIE_service_discovery_response(NWKID, "01", zone_state("01"))
        assert ep_status(device) == "Enrolled"
        assert device["IAS"]["Auto-Enrollment"]["Status"] == "Enrolled"
        assert ias.is_device_enrollment_completed(mgr, NWKID)
        """
    )


def test_lost_enroll_response_restarts_the_enrollment():
    _run(
        """
        mgr, device = manager(waiting_for_request())
        mgr.IAS_zone_enroll_request(NWKID, "01", "002a", "16")
        ias.zcl_write_attribute.reset_mock()
        # The device did not get the response: it still reports ZoneState 0x00
        mgr.IAS_CIE_service_discovery_response(NWKID, "01", zone_state("00"))
        assert ep_status(device) == "set IAS CIE Address"
        ias.zcl_write_attribute.assert_called_once()
        assert ias.zcl_write_attribute.call_args.args[4] == "0500"
        assert not ias.is_device_enrollment_completed(mgr, NWKID)
        """
    )


def test_enrolled_device_asking_again_keeps_its_status():
    _run(
        """
        record = {"Auto-Enrollment": {"Status": "Enrolled", "Ep": {"01": {"Status": "Enrolled"}}}}
        mgr, device = manager(record)
        mgr.IAS_zone_enroll_request(NWKID, "01", "002a", "17")
        ias.zcl_ias_zone_enroll_response.assert_called_once()
        assert ep_status(device) == "Enrolled"

        # Enrolled by an earlier version, on another Ep than the one asking: answered, no error
        record = {"Auto-Enrollment": {"Status": "Enrolled", "Ep": {"02": {"Status": "Enrolled2"}}}}
        mgr, device = manager(record)
        mgr.IAS_zone_enroll_request(NWKID, "01", "002a", "18")
        ias.zcl_ias_zone_enroll_response.assert_called_once()
        assert "01" not in device["IAS"]["Auto-Enrollment"]["Ep"]
        """
    )
