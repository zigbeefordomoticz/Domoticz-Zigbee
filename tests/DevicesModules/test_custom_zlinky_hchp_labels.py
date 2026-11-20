#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the HC/HP tariff labels handled by DevicesModules.custom_zlinky.

EDF Zen Fixe sends the option tarifaire "H PLEINE-CREUSE" (dash) where other
contracts send "H PLEINE/CREUSE" (slash), and its LTARF labels carry a double
space ("HEURE  PLEINE"). Both must map to the HC/HP colors, otherwise the
plugin logs "unknown op_tarifaire" or re-reads LTARF on every counter update.
"""

import importlib
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="module")
def zlinky_module():
    pkg = types.ModuleType("DevicesModules")
    pkg.__path__ = [os.path.join(os.path.dirname(__file__), "..", "..", "DevicesModules")]
    # patch.dict restores sys.modules afterwards, so these stubs never leak
    # into other tests that import the real Modules.*.
    stubs = {
        "DevicesModules": pkg,
        "Modules.domoMaj": MagicMock(),
        "Modules.readAttributes": MagicMock(),
        "Modules.tools": MagicMock(),
        "Modules.zlinky": MagicMock(),
    }
    with patch.dict(sys.modules, stubs):
        sys.modules.pop("DevicesModules.custom_zlinky", None)
        yield importlib.import_module("DevicesModules.custom_zlinky")


@pytest.fixture
def plugin():
    return MagicMock()


@pytest.mark.parametrize("optarif", ["H PLEINE/CREUSE", "H PLEINE-CREUSE", "HEURES PLEINES"])
def test_hchp_optarif_is_known(zlinky_module, plugin, optarif):
    normalized = zlinky_module._normalize_tarif(plugin, optarif)
    assert normalized == "HC"
    assert zlinky_module._known_op_tarifaire(normalized)
    assert zlinky_module._is_hchp_standard_tarif(plugin, optarif)
    assert zlinky_module._get_corresponding_color(plugin, "0100", optarif) == "HC.."
    assert zlinky_module._get_corresponding_color(plugin, "0102", optarif) == "HP.."


@pytest.mark.parametrize("ltarf, expected", [
    ("HEURE  PLEINE", "HP.."),
    ("HEURE PLEINE", "HP.."),
    ("HEURES PLEINES", "HP.."),
    ("HEURE  CREUSE", "HC.."),
    ("HEURE CREUSE", "HC.."),
    ("HEURES CREUSES", "HC.."),
    ("HP..", "HP.."),
    ("HC..", "HC.."),
    (None, None),
])
def test_normalize_hchp_color(zlinky_module, plugin, ltarf, expected):
    assert zlinky_module._normalize_hchp_color(plugin, ltarf) == expected


def test_tempo_is_not_hchp(zlinky_module, plugin):
    assert not zlinky_module._is_hchp_standard_tarif(plugin, "BBR(")
    assert zlinky_module._is_tempo_tarif(plugin, "BBR(")


def test_zen_fixe_standard_mode_does_not_reread_ltarf(zlinky_module, plugin):
    """LTARF 'HEURE  PLEINE' matches the HP.. color: no LTARF read request."""
    zlinky_module.get_linky_mode_from_ep = MagicMock(return_value=1)  # standard mode
    zlinky_module.get_ltarf = MagicMock(return_value="HEURE  PLEINE")
    zlinky_module.ReadAttributeRequest_ff66 = MagicMock()
    zlinky_module.zlinky_color_tarif = MagicMock()

    zlinky_module._zlinky_update_color(plugin, "abcd", "H PLEINE-CREUSE", "HP..", "HP..")

    zlinky_module.ReadAttributeRequest_ff66.assert_not_called()
    zlinky_module.zlinky_color_tarif.assert_not_called()
