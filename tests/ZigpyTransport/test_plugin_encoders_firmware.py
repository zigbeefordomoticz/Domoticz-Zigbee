#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the 0x8010 (firmware version) frame pipeline:

  - Classes/ZigpyTransport/firmwareversionHelper.py
      bellows_extract_versioning_for_plugin
      blz_extract_versioning_for_plugin
      deconz_extract_versioning_for_plugin
      znp_extract_versioning_for_plugin
  - Classes/ZigpyTransport/plugin_encoders.py
      build_plugin_8010_frame_content

Regression coverage for the startup crash reported against a CC2531
("Z-Stack Home" firmware): znp_extract_versioning_for_plugin returned an
int for firmware_branch/firmware_major_version on two branches, and
build_plugin_8010_frame_content concatenated Branch/Major/Version/
full_version with `+`, raising
    TypeError: unsupported operand type(s) for +: 'int' and 'str'

Every *_extract_versioning_for_plugin() must always return str for
Branch/Major/Version, and build_plugin_8010_frame_content() must be
robust even if a caller ever passes a non-str value again.

Imports of the SUT are done inside each test (not at module level) so the
session-scoped zigpy/radio stub fixture in conftest.py installs first.
"""

import unittest
from unittest.mock import MagicMock

# Claim the real module during collection: the root tests/conftest.py installs
# a stub for Modules.zigbeeVersionTable (without ZNP_MODEL) for decoder tests
# that don't need the real table. sys.modules.setdefault() in that fixture
# means whichever import happens first wins, so import it for real here.
import Modules.zigbeeVersionTable  # noqa: F401


def make_self():
    m = MagicMock()
    m.log = MagicMock()
    m.log.logging = MagicMock()
    return m


class TestBuildPlugin8010FrameContent(unittest.TestCase):
    """encapsulate_plugin_frame boundary: must never raise on mixed types."""

    def test_all_strings(self):
        from Classes.ZigpyTransport.plugin_encoders import build_plugin_8010_frame_content

        frame = build_plugin_8010_frame_content("21", "000000", "0297", "")
        # 01 + 8010 + length(4) + ff + payload + lqi(00) + 03
        payload = "21" + "000000" + "0297" + ""
        expected = "01" + "8010" + ("%04x" % len(payload)) + "ff" + payload + "00" + "03"
        self.assertEqual(frame, expected)

    def test_int_branch_does_not_raise(self):
        from Classes.ZigpyTransport.plugin_encoders import build_plugin_8010_frame_content

        # Regression: firmware_branch used to be returned as int on some
        # znp code paths, crashing this concatenation at startup.
        frame = build_plugin_8010_frame_content(22, "000000", "Z-Stack Home (build 20210708)", "")
        self.assertIn("22", frame)

    def test_int_major_and_version_do_not_raise(self):
        from Classes.ZigpyTransport.plugin_encoders import build_plugin_8010_frame_content

        frame = build_plugin_8010_frame_content("21", 0, 297, "")
        self.assertIn("210297", frame)

    def test_none_full_version_does_not_raise(self):
        from Classes.ZigpyTransport.plugin_encoders import build_plugin_8010_frame_content

        frame = build_plugin_8010_frame_content("21", "00", "0297", None)
        self.assertTrue(frame.startswith("018010"))
        self.assertIn("None", frame)


class TestZnpExtractVersioning(unittest.TestCase):
    """All three branches must return str for branch/major_version."""

    def test_zstack_home_branch(self):
        from Classes.ZigpyTransport.firmwareversionHelper import znp_extract_versioning_for_plugin

        branch, version, build = znp_extract_versioning_for_plugin(
            make_self(), "CC2531", "Texas Instruments", "Z-Stack Home 1.2.2a 20210708"
        )
        self.assertIsInstance(branch, str)
        self.assertEqual(branch, "22")
        self.assertIsInstance(version, str)
        self.assertIsInstance(build, str)

    def test_zstack_3_0_x_branch(self):
        from Classes.ZigpyTransport.firmwareversionHelper import znp_extract_versioning_for_plugin

        branch, version, build = znp_extract_versioning_for_plugin(
            make_self(), "CC2531", "Texas Instruments", "Z-Stack 3.0.x 20210708"
        )
        self.assertIsInstance(branch, str)
        self.assertEqual(branch, "21")
        self.assertIsInstance(version, str)
        self.assertIsInstance(build, str)

    def test_zstack_3_30_plus_branch_uses_znp_model_table(self):
        from Classes.ZigpyTransport.firmwareversionHelper import znp_extract_versioning_for_plugin

        branch, version, build = znp_extract_versioning_for_plugin(
            make_self(), "CC2652", "Texas Instruments", "Z-Stack 20210708"
        )
        self.assertIsInstance(branch, str)
        self.assertEqual(branch, "20")  # ZNP_MODEL["CC2652"]
        self.assertIsInstance(version, str)
        self.assertIsInstance(build, str)

    def test_znp_result_feeds_build_plugin_8010_without_raising(self):
        from Classes.ZigpyTransport.firmwareversionHelper import znp_extract_versioning_for_plugin
        from Classes.ZigpyTransport.plugin_encoders import build_plugin_8010_frame_content

        self_mock = make_self()
        for model, version in (
            ("CC2531", "Z-Stack Home 1.2.2a 20210708"),
            ("CC2531", "Z-Stack 3.0.x 20210708"),
            ("CC2652", "Z-Stack 20210708"),
        ):
            branch, firmware_version, build = znp_extract_versioning_for_plugin(
                self_mock, model, "Texas Instruments", version
            )
            # Mirrors AppZnp.py's actual call
            frame = build_plugin_8010_frame_content(branch, "000000", firmware_version, "")
            self.assertTrue(frame.startswith("018010"))


class TestBellowsExtractVersioning(unittest.TestCase):
    def test_returns_all_strings(self):
        from Classes.ZigpyTransport.firmwareversionHelper import bellows_extract_versioning_for_plugin

        branch, major, version = bellows_extract_versioning_for_plugin(
            make_self(), "Silicon Labs", "Some Board", "6.10.3.0 build 297"
        )
        self.assertIsInstance(branch, str)
        self.assertIsInstance(major, str)
        self.assertIsInstance(version, str)

    def test_known_board_branches(self):
        from Classes.ZigpyTransport.firmwareversionHelper import bellows_extract_versioning_for_plugin

        self_mock = make_self()
        branch, _, _ = bellows_extract_versioning_for_plugin(self_mock, "Elelabs", "ELU01x", "6.10.3.0 build 297")
        self.assertEqual(branch, "31")

        branch, _, _ = bellows_extract_versioning_for_plugin(self_mock, "Elelabs", "ELR02x", "6.10.3.0 build 297")
        self.assertEqual(branch, "30")

        branch, _, _ = bellows_extract_versioning_for_plugin(self_mock, None, "ZBDongle-E", "6.10.3.0 build 297")
        self.assertEqual(branch, "32")

        branch, _, _ = bellows_extract_versioning_for_plugin(self_mock, None, "Dongle Plus MG24", "6.10.3.0 build 297")
        self.assertEqual(branch, "33")

        branch, _, _ = bellows_extract_versioning_for_plugin(self_mock, None, "Unknown Board", "6.10.3.0 build 297")
        self.assertEqual(branch, "98")

    def test_bellows_result_feeds_build_plugin_8010_without_raising(self):
        from Classes.ZigpyTransport.firmwareversionHelper import bellows_extract_versioning_for_plugin
        from Classes.ZigpyTransport.plugin_encoders import build_plugin_8010_frame_content

        branch, major, version = bellows_extract_versioning_for_plugin(
            make_self(), "Elelabs", "ELU01x", "6.10.3.0 build 297"
        )
        # Mirrors AppBellows.py's actual call
        frame = build_plugin_8010_frame_content(branch, major, version, "6.10.3.0 build 297")
        self.assertTrue(frame.startswith("018010"))


class TestDeconzExtractVersioning(unittest.TestCase):
    def test_returns_strings_for_known_model(self):
        from Classes.ZigpyTransport.firmwareversionHelper import deconz_extract_versioning_for_plugin

        branch, version = deconz_extract_versioning_for_plugin(make_self(), "ConBee II", "dresden elektronik", 0x26580700)
        self.assertIsInstance(branch, str)
        self.assertEqual(branch, "40")
        self.assertIsInstance(version, str)

    def test_unknown_model_defaults_to_97(self):
        from Classes.ZigpyTransport.firmwareversionHelper import deconz_extract_versioning_for_plugin

        branch, _ = deconz_extract_versioning_for_plugin(make_self(), "Some Unknown Stick", "dresden elektronik", 0x1)
        self.assertEqual(branch, "97")

    def test_deconz_result_feeds_build_plugin_8010_without_raising(self):
        from Classes.ZigpyTransport.firmwareversionHelper import deconz_extract_versioning_for_plugin
        from Classes.ZigpyTransport.plugin_encoders import build_plugin_8010_frame_content

        branch, version = deconz_extract_versioning_for_plugin(make_self(), "RaspBee", "dresden elektronik", 0x12345678)
        # Mirrors AppDeconz.py's actual call
        frame = build_plugin_8010_frame_content(branch, "00", "0000", version)
        self.assertTrue(frame.startswith("018010"))


class TestBlzExtractVersioning(unittest.TestCase):
    def test_returns_expected_branch(self):
        from Classes.ZigpyTransport.firmwareversionHelper import blz_extract_versioning_for_plugin

        branch, version = blz_extract_versioning_for_plugin(make_self(), "model", "manuf", "1.0.0")
        self.assertEqual(branch, "50")
        self.assertEqual(version, "1.0.0")

    def test_blz_result_feeds_build_plugin_8010_without_raising_even_with_int_version(self):
        from Classes.ZigpyTransport.firmwareversionHelper import blz_extract_versioning_for_plugin
        from Classes.ZigpyTransport.plugin_encoders import build_plugin_8010_frame_content

        # Defensive: even if a future caller passes a non-str version,
        # build_plugin_8010_frame_content must not raise.
        branch, version = blz_extract_versioning_for_plugin(make_self(), "model", "manuf", 100)
        frame = build_plugin_8010_frame_content(branch, "00", "0000", version)
        self.assertTrue(frame.startswith("018010"))


if __name__ == "__main__":
    unittest.main()
