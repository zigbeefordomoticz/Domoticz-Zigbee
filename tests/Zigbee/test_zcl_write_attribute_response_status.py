#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the Write Attributes Response, from zcl_decoders to Decode8110.

Before this, foundation_cluster_write_attribute_response put a "0000" placeholder
after the cluster id, where Decode8110 reads the status, so every response decoded
in zigpy mode reported status 00, even a rejected write (INVALID_VALUE from a
Eurotronic Spirit for 0x4003, field report 2026-11-22).

The incoming payloads are serialised by zigpy, so the layout under test does not
come from the code under test.

Zigbee.zclDecoders imports the real Modules.* package, which conflicts with the
stubs tests/conftest.py installs for the session, so the checks run in a
subprocess (as in test_zcl_scene_responses.py).
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import sys, types
    from unittest.mock import MagicMock, patch

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)

    import Zigbee.zclDecoders as decoders
    import Z4D_decoders.z4d_decoder_Wrt_Attribute_Rsp as wrt
    from zigpy.zcl import foundation

    NWKID, EP, CLUSTER = "4d43", "01", "0201"
    FRAME = "0180020022ff00010402010101024d43020000180104007403"

    def plugin(firmware="0000"):
        p = types.SimpleNamespace()
        p.log = MagicMock()
        p.ListOfDevices = {NWKID: {"Model": "SPZB0001"}}
        p.pluginconf = types.SimpleNamespace(pluginConf={})
        p.zigbee_communication = "zigpy"
        p.FirmwareVersion = firmware
        p.DeviceConf = {}
        return p

    def response(*records):
        return foundation.WriteAttributesResponse(list(records)).serialize().hex()

    def decode(data):
        with patch.object(decoders, "zcl_raw_default_response"):
            # FCF 18: server to client, disable default response; Sqn 01; command 04
            return decoders.zcl_decoders(plugin(), NWKID, EP, "01", CLUSTER, "18" + "01" + "04" + data, FRAME)

    def fields(frame):
        return frame[2:6], frame[12:12 + int(frame[6:10], 16)]

    def decoded_status(frame, firmware="0000"):
        \"\"\"Status and attribute Decode8110 hands to Decode8110_raw.\"\"\"
        msgtype, msgdata = fields(frame)
        assert msgtype == "8110", frame
        with patch.object(wrt, "Decode8110_raw") as raw:
            wrt.Decode8110(plugin(firmware), {}, msgdata, "74")
        args = raw.call_args.args
        return args[6], args[7]
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


def test_success_reports_00():
    _run(
        """
        data = response(foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS))
        assert data == "00", data
        frame = decode(data)
        assert fields(frame)[1] == "01" + NWKID + EP + CLUSTER + "00", frame
        assert decoded_status(frame) == ("00", None)
        """
    )


def test_rejected_write_reports_the_device_status():
    _run(
        """
        data = response(foundation.WriteAttributesStatusRecord(foundation.Status.INVALID_VALUE, 0x4003))
        assert data == "870340", data
        frame = decode(data)
        # Sqn | Nwkid | Ep | Cluster | Status | AttributeId (big endian)
        assert fields(frame)[1] == "01" + NWKID + EP + CLUSTER + "87" + "4003", frame
        assert decoded_status(frame) == ("87", None)
        """
    )


def test_several_rejected_attributes_report_the_first_status():
    _run(
        """
        data = response(
            foundation.WriteAttributesStatusRecord(foundation.Status.READ_ONLY, 0x0000),
            foundation.WriteAttributesStatusRecord(foundation.Status.UNSUPPORTED_ATTRIBUTE, 0x4003),
        )
        frame = decode(data)
        assert fields(frame)[1] == "01" + NWKID + EP + CLUSTER + "88" + "0000", frame
        assert decoded_status(frame) == ("88", None)
        """
    )


def test_payload_never_takes_the_24_character_zigate_layout():
    # Decode8110 reads a 24-character payload with ZiGate firmware offsets.
    # A built payload is 14 (success) or 18 (rejected) characters long.
    _run(
        """
        for record in (
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS),
            foundation.WriteAttributesStatusRecord(foundation.Status.INVALID_VALUE, 0x4003),
        ):
            msgdata = fields(decode(response(record)))[1]
            assert len(msgdata) in (14, 18), msgdata
            assert decoded_status(decode(response(record)), firmware="031c")[0] == msgdata[12:14]
        """
    )


def test_empty_data_keeps_status_00():
    _run(
        """
        frame = decoders.foundation_cluster_write_attribute_response(plugin(), FRAME, "01", NWKID, EP, "01", CLUSTER, "")
        assert fields(frame)[1] == "01" + NWKID + EP + CLUSTER + "00", frame
        """
    )
