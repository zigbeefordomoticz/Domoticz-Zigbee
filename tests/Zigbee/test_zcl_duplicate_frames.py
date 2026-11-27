#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the filter of the copies of a ZCL frame (issue #2332).

The frames go through the real zcl_decoders and zcl_raw_default_response, only the
radio (raw_APS_request) is replaced. Zigbee.zclDecoders imports the real Modules.*
package, which conflicts with the stubs tests/conftest.py installs for the session,
so the checks run in a subprocess.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

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

    # Modules.domoMaj cannot be imported on its own: it is only reached through a
    # circular import that plugin.py resolves. No test here updates a widget.
    domo_maj = types.ModuleType("Modules.domoMaj")
    domo_maj.__getattr__ = lambda name: MagicMock(name=name)
    sys.modules["Modules.domoMaj"] = domo_maj

    import Zigbee.zclDecoders as decoders
    import Zigbee.zclDuplicateFrames as duplicates
    import Zigbee.zclRawCommands as raw

    NWKID, EP = "f096", "01"
    FRAME = "018002003cff0001040300010102c57702000018c00a" + "2803"

    # Report Attributes: FCF 08, TSN 36, Basic 0x0001 = 0x46
    REPORT = "08360a01002046"
    REPORT_NO_DR = "18" + REPORT[2:]
    # Tuya data report: FCF 09, TSN f4
    TUYA_REPORT = "09f402001201020004000000e1"


    class Plugin(types.SimpleNamespace):
        def __init__(self, enabled=True, communication="zigpy"):
            super().__init__(
                log=MagicMock(),
                ListOfDevices={NWKID: {"Model": "TS0601"}, "71f4": {}},
                pluginconf=types.SimpleNamespace(pluginConf={"enableZclDuplicatecheck": enabled, "trackZclClustersOut": False}),
                zigbee_communication=communication,
                DeviceConf={},
                zcl_recent_frames={},
            )
            self.clock = 1000.0
            self.sent = []
            self.decoded = []

        def receive(self, payload, cluster="0000", nwkid=NWKID, ep=EP, after=0.0):
            \"\"\"One frame received, 'after' seconds after the previous one. True if it was decoded.\"\"\"
            self.clock += after
            # Decoded frames log one "SrcNWK: ..." Debug line just after the filter
            before = self.decode_count()
            with (
                patch.object(duplicates.time, "monotonic", lambda: self.clock),
                patch.object(raw, "raw_APS_request", lambda _s, nwk, ep, cl, prof, data, **kw: self.sent.append((nwk, ep, cl, data))),
                patch.object(raw, "is_ack_tobe_disabled", return_value=False),
            ):
                frame = decoders.zcl_decoders(self, nwkid, ep, "01", cluster, payload, FRAME)
            decoded = self.decode_count() > before
            assert decoded or frame is None
            return decoded

        def decode_count(self):
            return sum(
                1 for call in self.log.logging.call_args_list
                if call.args[0] == "zclDecoder" and call.args[2].startswith("SrcNWK:")
            )
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


def test_copy_is_dropped_and_gets_the_default_response_again():
    _run(
        """
        p = Plugin()
        assert p.receive(REPORT)
        assert not p.receive(REPORT, after=0.2)
        assert p.sent == [(NWKID, EP, "0000", "10360b0a00")] * 2, p.sent
        """
    )


def test_each_copy_is_dropped_and_answered():
    # f096 sent the TSN f4 three times
    _run(
        """
        p = Plugin()
        assert p.receive(TUYA_REPORT, "ef00")
        assert not p.receive(TUYA_REPORT, "ef00", after=0.2)
        assert not p.receive(TUYA_REPORT, "ef00", after=0.24)
        assert p.sent == [(NWKID, EP, "ef00", "10f40b0200")] * 3, p.sent
        """
    )


def test_copy_without_default_response_gets_none():
    _run(
        """
        p = Plugin()
        assert p.receive(REPORT_NO_DR)
        assert not p.receive(REPORT_NO_DR, after=0.2)
        assert p.sent == []
        """
    )


def test_copy_of_a_frame_without_answer_gets_none():
    # Unknown cluster command with DDR=0: no Default Response today, none for the copy
    _run(
        """
        p = Plugin()
        assert p.receive("092a0900", "fc11")
        assert not p.receive("092a0900", "fc11", after=0.2)
        assert p.sent == []
        """
    )


def test_default_response_of_a_module_is_sent_again():
    # TY_DEFAULT_RESPONSE: Modules.tuya answers a frame with DDR=1
    _run(
        """
        p = Plugin()
        report = "19" + TUYA_REPORT[2:]
        assert p.receive(report, "ef00")
        assert p.sent == []
        with patch.object(raw, "raw_APS_request"), patch.object(raw, "is_ack_tobe_disabled", return_value=False):
            raw.zcl_raw_default_response(p, NWKID, "01", EP, "ef00", "02", "f4", command_status="00", manufcode=None, orig_fcf="19")
        assert not p.receive(report, "ef00", after=0.2)
        assert p.sent == [(NWKID, EP, "ef00", "10f40b0200")], p.sent
        """
    )


def test_manufacturer_specific_default_response_is_sent_again():
    _run(
        """
        p = Plugin()
        report = "0c5f11360a01002046"
        assert p.receive(report, "fcc0")
        assert not p.receive(report, "fcc0", after=0.2)
        assert len(p.sent) == 2 and p.sent[0] == p.sent[1], p.sent
        assert p.sent[0][3] == "145f11360b0a00", p.sent
        """
    )


def test_default_response_disabled_by_setting():
    _run(
        """
        p = Plugin()
        p.pluginconf.pluginConf["disableZCLDefaultResponse"] = True
        assert p.receive(REPORT)
        assert not p.receive(REPORT, after=0.2)
        assert p.sent == []
        """
    )


def test_setting_off_decodes_and_answers_each_copy():
    _run(
        """
        p = Plugin(enabled=False)
        assert p.receive(REPORT)
        assert p.receive(REPORT, after=0.2)
        assert len(p.sent) == 2
        assert p.zcl_recent_frames == {}
        """
    )


def test_not_used_with_a_native_zigate():
    _run(
        """
        p = Plugin(communication="native")
        assert p.receive(REPORT)
        assert p.receive(REPORT, after=0.2)
        assert p.zcl_recent_frames == {}
        """
    )


def test_remote_pressed_twice_gives_two_events():
    _run(
        """
        p = Plugin()
        assert p.receive("014102", "0006")               # Toggle, TSN 41
        assert p.receive("014202", "0006", after=0.15)   # Toggle, TSN 42
        assert not p.receive("014202", "0006", after=0.2)
        """
    )


def test_sequence_number_always_00_is_never_a_copy():
    _run(
        """
        p = Plugin()
        assert p.receive("010002", "0006")
        assert p.receive("010002", "0006", after=0.5)
        """
    )


def test_not_a_copy_when_anything_differs():
    _run(
        """
        p = Plugin()
        assert p.receive(REPORT)
        assert p.receive(REPORT, nwkid="71f4", after=0.1)
        assert p.receive(REPORT, ep="02", after=0.1)
        assert p.receive(REPORT, cluster="0001", after=0.1)
        assert p.receive(REPORT[:-2] + "47", after=0.1)
        assert p.receive("08370a" + REPORT[6:], after=0.1)
        """
    )


def test_window_starts_at_the_first_frame():
    _run(
        """
        p = Plugin()
        assert p.receive(REPORT)
        assert not p.receive(REPORT, after=2.9)
        assert p.receive(REPORT, after=0.2)       # 3.1 s after the first frame
        assert not p.receive(REPORT, after=0.2)   # copy of the previous one
        """
    )


def test_only_the_frames_of_the_window_are_kept():
    _run(
        """
        p = Plugin()
        for sqn in range(1, 200):
            p.receive("08%02x0a01002046" % sqn, after=0.1)
        assert len(p.zcl_recent_frames) <= 31, len(p.zcl_recent_frames)
        """
    )


def test_nothing_is_stored_in_the_device_record():
    _run(
        """
        p = Plugin()
        p.receive(REPORT)
        p.receive(REPORT, after=0.2)
        assert p.ListOfDevices[NWKID] == {"Model": "TS0601"}
        """
    )


def test_unknown_device_is_not_filtered():
    _run(
        """
        p = Plugin()
        assert p.receive(REPORT, nwkid="abcd")
        assert p.receive(REPORT, nwkid="abcd", after=0.2)
        assert p.zcl_recent_frames == {}
        """
    )


@pytest.mark.parametrize("cluster, payload", [
    ("000a", "0017000700"),       # Read Attributes (Time)
    ("0000", "00170205002003"),    # Write Attributes
    ("0000", "00170605002003"),    # Configure Reporting
    ("0019", "0117010004101100"),  # OTA Query Next Image
    ("0019", "01170300041011"),    # OTA Image Block Request
    ("0020", "091700"),            # Poll Control Check-in
    ("0500", "0917010d001510"),    # IAS Zone Enroll Request
    ("0501", "01170000000000"),    # IAS ACE Arm
    ("0501", "011707"),            # IAS ACE Get Panel Status
    ("ef00", "0917240008"),        # Tuya time synchronisation
    ("ef00", "0917250008"),        # Tuya gateway status
    ("ed00", "0117020000"),        # Zosung IR, code data request
    ("fc01", "1d2110170a0000"),    # Legrand
    ("0004", "01170000100000"),    # Add Group, from a client
])
def test_frame_with_a_response_of_its_own_is_never_a_copy(cluster, payload):
    _run(
        f"""
        p = Plugin()
        payload = {payload!r}
        # What follows the filter is not under test: stop there
        for _ in range(2):
            _, _, sqn, _, command, _ = decoders.retreive_cmd_payload_from_8002(payload)
            assert not decoders.is_duplicate_zcl_frame(p, NWKID, EP, {cluster!r}, payload, sqn, command)
        assert p.zcl_recent_frames == {{}}
        """
    )


@pytest.mark.parametrize("cluster, payload", [
    ("0500", "091700210000000000"),  # Zone Status Change Notification
    ("0501", "011702"),              # IAS ACE Emergency: no response
    ("0004", "091700001000"),        # Add Group Response
    ("0201", "08170400"),            # Write Attributes Response
    ("ef00", "0917110340"),          # Tuya MCU version
    ("0006", "011702"),              # Toggle
])
def test_frame_without_a_response_of_its_own_is_filtered(cluster, payload):
    _run(
        f"""
        p = Plugin()
        payload = {payload!r}
        _, _, sqn, _, command, _ = decoders.retreive_cmd_payload_from_8002(payload)
        assert not decoders.is_duplicate_zcl_frame(p, NWKID, EP, {cluster!r}, payload, sqn, command)
        assert decoders.is_duplicate_zcl_frame(p, NWKID, EP, {cluster!r}, payload, sqn, command)
        """
    )
