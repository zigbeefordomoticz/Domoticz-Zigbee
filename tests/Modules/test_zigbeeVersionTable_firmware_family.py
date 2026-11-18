#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the coordinator firmware family label (Modules/zigbeeVersionTable.py):
firmware_family() and set_display_firmware_version().

The label is "<family> - <minor version>" and is reported as the Firmware
dimension of the plugin analytics. Unrecognised coordinators report the
branches 97/98/99 ("Unknown deConz / Silicon Labs / ZNP"), which used to
give "UNK"; the family now comes from the Coordinator Model parameter (Mode1).
"""

import unittest
from types import SimpleNamespace

# Claim the real module during collection: the root tests/conftest.py installs
# a stub for Modules.zigbeeVersionTable for decoder tests, and whichever import
# happens first wins (see tests/ZigpyTransport/test_plugin_encoders_firmware.py).
import Modules.zigbeeVersionTable  # noqa: F401


class TestFirmwareFamily(unittest.TestCase):

    def family(self, branch, mode1=None):
        from Modules.zigbeeVersionTable import firmware_family
        return firmware_family(branch, mode1)

    def test_branch_ranges(self):
        for branch, expected in (("00", "Zigate"), ("11", "Zigate"), ("20", "Znp"), ("22", "Znp"),
                                 ("32", "Ezsp"), ("33", "Ezsp"), ("40", "deCONZ"), ("43", "deCONZ"),
                                 ("50", "BLZ")):
            with self.subTest(branch=branch):
                self.assertEqual(self.family(branch, "ZigpyZNP"), expected)

    def test_branch_wins_over_mode1(self):
        self.assertEqual(self.family("32", "ZigpyZNP"), "Ezsp")

    def test_unknown_branches_use_mode1(self):
        self.assertEqual(self.family("98", "ZigpyEZSP"), "Ezsp")
        self.assertEqual(self.family("99", "ZigpyZNP"), "Znp")
        self.assertEqual(self.family("97", "ZigpydeCONZ"), "deCONZ")

    def test_unreadable_branch_uses_mode1(self):
        for branch in (None, "", "xx"):
            with self.subTest(branch=branch):
                self.assertEqual(self.family(branch, "ZigpyBLZ"), "BLZ")

    def test_zigate_modes(self):
        for mode1 in ("V1", "V2", "ZigpyZiGate"):
            with self.subTest(mode1=mode1):
                self.assertEqual(self.family("98", mode1), "Zigate")

    def test_nothing_known(self):
        self.assertEqual(self.family("98", None), "UNK")
        self.assertEqual(self.family(None, "Something"), "UNK")


class TestSetDisplayFirmwareVersion(unittest.TestCase):

    def run_with(self, controller_data, mode1):
        from Modules.zigbeeVersionTable import set_display_firmware_version
        plugin = SimpleNamespace(ControllerData=controller_data, pluginParameters={"Mode1": mode1})
        set_display_firmware_version(plugin)
        return plugin.pluginParameters["DisplayFirmwareVersion"]

    def test_known_branch(self):
        self.assertEqual(self.run_with({"Branch Version": "20", "Minor Version": "20220219"}, "ZigpyZNP"),
                         "Znp - 20220219")

    def test_unknown_silicon_labs(self):
        self.assertEqual(self.run_with({"Branch Version": "98", "Minor Version": "7.4.4.0 build 0"}, "ZigpyEZSP"),
                         "Ezsp - 7.4.4.0 build 0")

    def test_blz(self):
        self.assertEqual(self.run_with({"Branch Version": "50", "Minor Version": "1.0"}, "ZigpyBLZ"), "BLZ - 1.0")


if __name__ == "__main__":
    unittest.main()
