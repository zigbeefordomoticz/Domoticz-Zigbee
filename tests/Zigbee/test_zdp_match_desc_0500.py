#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the Match Descriptor exchange on cluster 0x0500, from the request
(Zigbee/zdpRawCommands.py) to the write of the IAS CIE address (Classes/IAS.py).

Coverage:
  - the response to our request leads to one write per listed endpoint
  - a response with another SQN, or from another device, leads to none
  - a copy of the response, or one received too late, leads to none
  - two requests to the same device can both be answered
  - the request is known before it is sent
  - requests without a response do not pile up

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
    from unittest.mock import MagicMock, patch

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Modules.tools  # noqa: F401  (import order as in the plugin, avoids a circular import)
    import Modules.readAttributes  # noqa: F401  (same reason)
    import Classes.IAS as ias
    import Zigbee.zdpRawCommands as zdp
    from Z4D_decoders.z4d_decoder_IAS import Decode8046
    from Zigbee.zdpDecoders import buildframe_match_description_response

    NWKID = "abcd"

    p = types.SimpleNamespace()
    p.log = MagicMock()
    p.pluginconf = types.SimpleNamespace(pluginConf=MagicMock())
    p.ControllerLink = MagicMock()
    p.ListOfDevices = {NWKID: {}, "1234": {}}
    p.iaszonemgt = ias.IAS_Zone_Management(
        p.pluginconf, p.ControllerLink, p.ListOfDevices, {}, {}, p.log, "zigpy", "00", None, False, "00124b0000000001")

    clock = [1000.0]
    ias.time = types.SimpleNamespace(time=lambda: clock[0])

    def request(nwkid=NWKID):
        with patch.object(zdp, "raw_APS_request") as raw_aps:
            sqn = zdp.zdp_raw_match_desc_req_0500(p, nwkid)
        payload = raw_aps.call_args.args[5]
        assert payload[:2] == sqn
        return sqn

    def response(sqn, endpoints, nwkid=NWKID):
        # Over the air frame, as the device sends it
        payload = sqn + "00" + nwkid[2:] + nwkid[:2] + "%02x" % len(endpoints) + "".join(endpoints)
        frame = buildframe_match_description_response(p, nwkid, "00", "8006", payload, "01" + "0" * 20 + "8003")
        with patch.object(ias, "zcl_write_attribute") as write:
            Decode8046(p, {}, frame[12:-4], "80")
        return [(c.args[1], c.args[3], c.args[4], c.args[7]) for c in write.call_args_list]

    def cie_write(*endpoints, nwkid=NWKID):
        return [(nwkid, ep, "0500", "0010") for ep in endpoints]
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


def test_response_to_our_request_writes_every_endpoint():
    _run(
        """
        assert response(request(), ["01"]) == cie_write("01")
        assert response(request(), ["01", "02"]) == cie_write("01", "02")
        assert response(request(), ["01", "02", "03"]) == cie_write("01", "02", "03")
        assert response(request(), []) == []
        """
    )


def test_response_to_another_request_is_ignored():
    _run(
        """
        assert response("55", ["01"]) == []
        sqn = request()
        assert response("%02x" % (int(sqn, 16) + 1), ["01"]) == []
        assert response(sqn, ["01"], nwkid="1234") == []
        assert response(sqn, ["01"]) == cie_write("01")
        """
    )


def test_copy_of_a_response_is_ignored():
    _run(
        """
        sqn = request()
        assert response(sqn, ["01"]) == cie_write("01")
        assert response(sqn, ["01"]) == []
        """
    )


def test_late_response_is_ignored():
    _run(
        """
        sqn = request()
        clock[0] += ias.MATCH_DESC_REQUEST_LIFETIME
        assert response(sqn, ["01"]) == cie_write("01")
        sqn = request()
        clock[0] += ias.MATCH_DESC_REQUEST_LIFETIME + 1
        assert response(sqn, ["01"]) == []
        """
    )


def test_two_requests_to_the_same_device():
    _run(
        """
        first, second = request(), request()
        assert first != second
        assert response(first, ["01"]) == cie_write("01")
        assert response(second, ["01"]) == cie_write("01")
        """
    )


def test_request_is_known_before_it_is_sent():
    _run(
        """
        seen = []
        with patch.object(zdp, "raw_APS_request", side_effect=lambda *a, **k: seen.extend(p.iaszonemgt.match_desc_requests)):
            sqn = zdp.zdp_raw_match_desc_req_0500(p, NWKID)
        assert seen == [(NWKID, sqn)]
        """
    )


def test_unanswered_requests_do_not_pile_up():
    _run(
        """
        for _ in range(10):
            request()
            clock[0] += ias.MATCH_DESC_REQUEST_LIFETIME + 1
        assert len(p.iaszonemgt.match_desc_requests) == 1
        """
    )


def test_request_without_ias_manager():
    _run(
        """
        p.iaszonemgt = None
        assert request() == "01"
        """
    )
