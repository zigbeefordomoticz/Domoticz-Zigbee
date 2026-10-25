#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression test for issue #2085: the fallback Configure Reporting table
CFG_RPT_ATTRIBUTESbyCLUSTERS declared BatteryVoltage (0x0020) as int16 and
BatteryPercentageRemaining (0x0021) as uint16 on the Power Configuration
cluster (0x0001). Both are uint8 (0x20). Firmware that validates the data type
answers 0x8d INVALID_DATA_TYPE and battery reporting is never set up.

The table must agree with Conf/ZclDefinitions/0001.json, and each reportable
change must be as wide as its data type, because the frame builders copy
"Change" verbatim.

Run with:
    python -m pytest tests/Modules/test_zigateConsts_cfg_rpt_power_cluster.py -v
"""

import json
from pathlib import Path

import pytest

from Modules.zigateConsts import CFG_RPT_ATTRIBUTESbyCLUSTERS, SIZE_DATA_TYPE

ZCL_DEFINITION = Path(__file__).resolve().parents[2] / "Conf" / "ZclDefinitions" / "0001.json"

POWER_ATTRIBUTES = CFG_RPT_ATTRIBUTESbyCLUSTERS["0001"]["Attributes"]


@pytest.fixture(scope="module")
def zcl_attributes():
    with open(ZCL_DEFINITION, encoding="utf-8") as handle:
        return json.load(handle)["Attributes"]


@pytest.mark.parametrize("attribute", ["0020", "0021"])
def test_battery_attributes_are_uint8(attribute):
    assert POWER_ATTRIBUTES[attribute]["DataType"] == "20"


@pytest.mark.parametrize("attribute", sorted(POWER_ATTRIBUTES))
def test_datatype_matches_zcl_definition(attribute, zcl_attributes):
    assert POWER_ATTRIBUTES[attribute]["DataType"].lower() == zcl_attributes[attribute]["DataType"].lower()


@pytest.mark.parametrize("attribute", sorted(POWER_ATTRIBUTES))
def test_reportable_change_width_matches_datatype(attribute):
    record = POWER_ATTRIBUTES[attribute]
    assert len(record["Change"]) == SIZE_DATA_TYPE[record["DataType"]] * 2
