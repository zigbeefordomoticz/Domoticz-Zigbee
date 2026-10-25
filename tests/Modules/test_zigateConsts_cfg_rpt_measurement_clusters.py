#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression test for issue #2151: the fallback Configure Reporting table
CFG_RPT_ATTRIBUTESbyCLUSTERS declared MeasuredValue (0x0000) as uint8 on the
Pressure (0x0403) and Flow (0x0404) Measurement clusters. Pressure
MeasuredValue is int16 (0x29), Flow MeasuredValue is uint16 (0x21). Firmware
that validates the data type answers 0x8d INVALID_DATA_TYPE and reporting is
never set up.

The table must agree with Conf/ZclDefinitions/<cluster>.json, and each
reportable change must be as wide as its data type, because the frame builders
copy "Change" verbatim.

Run with:
    python -m pytest tests/Modules/test_zigateConsts_cfg_rpt_measurement_clusters.py -v
"""

import json
from pathlib import Path

import pytest

from Modules.zigateConsts import CFG_RPT_ATTRIBUTESbyCLUSTERS, SIZE_DATA_TYPE

ZCL_DEFINITIONS = Path(__file__).resolve().parents[2] / "Conf" / "ZclDefinitions"

CLUSTERS = ("0403", "0404")

RECORDS = [
    (cluster, attribute)
    for cluster in CLUSTERS
    for attribute in sorted(CFG_RPT_ATTRIBUTESbyCLUSTERS[cluster]["Attributes"])
]


def _zcl_attributes(cluster):
    with open(ZCL_DEFINITIONS / f"{cluster}.json", encoding="utf-8") as handle:
        return json.load(handle)["Attributes"]


@pytest.mark.parametrize("cluster, datatype", [("0403", "29"), ("0404", "21")])
def test_measured_value_datatype(cluster, datatype):
    assert CFG_RPT_ATTRIBUTESbyCLUSTERS[cluster]["Attributes"]["0000"]["DataType"] == datatype


@pytest.mark.parametrize("cluster, attribute", RECORDS)
def test_datatype_matches_zcl_definition(cluster, attribute):
    record = CFG_RPT_ATTRIBUTESbyCLUSTERS[cluster]["Attributes"][attribute]
    assert record["DataType"].lower() == _zcl_attributes(cluster)[attribute]["DataType"].lower()


@pytest.mark.parametrize("cluster, attribute", RECORDS)
def test_reportable_change_width_matches_datatype(cluster, attribute):
    record = CFG_RPT_ATTRIBUTESbyCLUSTERS[cluster]["Attributes"][attribute]
    assert len(record["Change"]) == SIZE_DATA_TYPE[record["DataType"]] * 2


@pytest.mark.parametrize("attribute", ["0000", "0001", "0002"])
def test_flow_zcl_definition_is_uint16(attribute):
    assert _zcl_attributes("0404")[attribute]["DataType"] == "21"
