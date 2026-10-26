#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Zigbee.zclDecoders.buildframe_for_cluster_8501: the Image Block
Request (cluster 0x0019, command 0x03) turned into the 8501 plugin frame that
Classes.OTA.ota_image_block_request reads.

Reference: Zigbee Cluster Library rev 8 (07-5123-08)
    11.13.6  Image Block Request: field control, manufacturer code, image type,
             file version, file offset, maximum data size, then the optional
             Request Node Address (field control bit 0, IEEE, 8 bytes) and
             Minimum Block Period (bit 1, 2 bytes, ms), in that order

Regression guarded here: the Minimum Block Period was read only when the payload
had exactly its length, so it was lost (read as 0) when the client also sent its
IEEE address, and the IEEE address was never passed on.

Zigbee.zclDecoders imports the real Modules.* package, which conflicts with the
stubs tests/conftest.py installs for the session, so the decoder runs in a
subprocess.
"""

import json
import struct
import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

IEEE = 0x00158D0000ABCDEF


def _request(field_control, ieee=None, min_block_period=None):
    """ZCL payload of an Image Block Request, little-endian as on the air."""
    data = struct.pack("<BHHLLB", field_control, 0x117C, 0x2203, 0x01020304, 0x00000400, 0x30)
    if ieee is not None:
        data += struct.pack("<Q", ieee)
    if min_block_period is not None:
        data += struct.pack("<H", min_block_period)
    return data.hex()


CASES = {
    "no_optional_field": _request(0x00),
    "ieee_only": _request(0x01, ieee=IEEE),
    "min_block_period_only": _request(0x02, min_block_period=1500),
    "ieee_and_min_block_period": _request(0x03, ieee=IEEE, min_block_period=1500),
    # bit 1 set, field missing: nothing read past the payload
    "min_block_period_truncated": _request(0x02),
}


@pytest.fixture(scope="module")
def frames():
    snippet = textwrap.dedent(
        """
        import json, sys, types
        for name in ("Domoticz", "DomoticzEx"):
            sys.modules[name] = types.ModuleType(name)
        import Zigbee.zclDecoders as decoders

        class Log:
            def logging(self, *args, **kwargs):
                pass

        class Plugin:
            log = Log()
            ListOfDevices = {}

        out = {}
        for name, data in json.loads(sys.argv[1]).items():
            frame = "018002003cff00" + data + "2803"
            out[name] = decoders.buildframe_for_cluster_8501(Plugin(), "03", frame, "10", "1234", "01", "01", "0019", data)
        print(json.dumps(out))
        """
    )
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", snippet, json.dumps(CASES)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return json.loads(result.stdout)


def _fields(frame):
    """The 8501 payload, sliced as Classes.OTA.ota_image_block_request does."""
    payload = frame[12:-4]
    return {
        "nwkid": payload[10:14],
        "ieee": payload[14:30],
        "offset": int(payload[30:38], 16),
        "version": int(payload[38:46], 16),
        "image_type": int(payload[46:50], 16),
        "manuf_code": int(payload[50:54], 16),
        "min_block_period": int(payload[54:58], 16),
        "max_data_size": int(payload[58:60], 16),
        "field_control": int(payload[60:62], 16),
        "length": len(payload),
    }


@pytest.mark.parametrize(
    "case, ieee, min_block_period",
    [
        ("no_optional_field", "0000000000000000", 0),
        ("ieee_only", "%016x" % IEEE, 0),
        ("min_block_period_only", "0000000000000000", 1500),
        ("ieee_and_min_block_period", "%016x" % IEEE, 1500),
        ("min_block_period_truncated", "0000000000000000", 0),
    ],
)
def test_optional_fields_follow_the_field_control_bits(frames, case, ieee, min_block_period):
    fields = _fields(frames[case])

    assert (fields["ieee"], fields["min_block_period"]) == (ieee, min_block_period)


@pytest.mark.parametrize("case", list(CASES))
def test_mandatory_fields_and_frame_layout(frames, case):
    fields = _fields(frames[case])

    assert (fields["nwkid"], fields["offset"], fields["version"]) == ("1234", 0x400, 0x01020304)
    assert (fields["image_type"], fields["manuf_code"], fields["max_data_size"]) == (0x2203, 0x117C, 0x30)
    # Classes.OTA.ota_image_block_request accepts a 62-character payload (60 without field control)
    assert fields["length"] == 62
