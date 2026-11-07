#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Modules/greenPowerModels.py, the Green Power device types of
Conf/ZGPmodel:

  shipped files   every Conf/ZGPmodel/*.json loads, with widget types the
                  Green Power widget layer can create
  loading         a broken file is logged as an Error with its code and left out
  list            the WebUI list follows Order
  commands        a GPD command id maps to [cluster, value], or to nothing
"""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from Modules.greenPowerModels import (gp_model_command, gp_model_list,
                                      load_gp_models)

REPO_CONF = Path(__file__).resolve().parents[2] / "Conf"


def plugin():
    return SimpleNamespace(log=MagicMock())


def errors(p):
    return [c.args for c in p.log.logging.call_args_list if c.args[1] == "Error"]


def write(folder, name, content):
    (folder / "ZGPmodel").mkdir(exist_ok=True)
    (folder / "ZGPmodel" / name).write_text(content if isinstance(content, str) else json.dumps(content))


GOOD = {"Description": "x", "Ep": {"01": {"Type": "Switch"}}, "Commands": {"20": ["0006", "00"]}}


def test_shipped_types_all_load():
    p = plugin()

    models = load_gp_models(p, REPO_CONF)

    assert {"GreenPower-OnOff", "GreenPower-OnOff-Dim"} <= set(models)
    assert len(models) == len(list((REPO_CONF / "ZGPmodel").glob("*.json")))
    assert errors(p) == []


def _real_switch_selectors():
    # Other tests replace Modules.switchSelectorWidgets in sys.modules: read the file itself
    spec = importlib.util.spec_from_file_location("_switch_selectors", REPO_CONF.parent / "Modules" / "switchSelectorWidgets.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SWITCH_SELECTORS


def test_shipped_widget_types_are_known():
    SWITCH_SELECTORS = _real_switch_selectors()

    simple = ("Switch",)  # SIMPLE_WIDGET entries used by the shipped types
    for name, conf in load_gp_models(plugin(), REPO_CONF).items():
        for ep_conf in conf["Ep"].values():
            assert ep_conf["Type"] in simple or ep_conf["Type"] in SWITCH_SELECTORS, (name, ep_conf["Type"])


def test_list_follows_order(tmp_path):
    p = plugin()
    write(tmp_path, "B.json", dict(GOOD, Order=1))
    write(tmp_path, "A.json", dict(GOOD, Order=2))
    load_gp_models(p, tmp_path)

    assert [m["Name"] for m in gp_model_list(p)] == ["B", "A"]
    assert gp_model_list(p)[0] == {"Name": "B", "Description": "x", "Order": 1, "Widgets": ["Switch"]}


@pytest.mark.parametrize("content,code", [
    ("{not json", "GPMODEL-LOAD-01"),
    ({"Commands": {"20": ["0006", "00"]}}, "GPMODEL-LOAD-02"),
    ({"Ep": {"1": {"Type": "Switch"}}, "Commands": {"20": ["0006", "00"]}}, "GPMODEL-LOAD-02"),
    ({"Ep": {"01": {"Type": "Switch"}}, "Commands": {"0x20": ["0006", "00"]}}, "GPMODEL-LOAD-02"),
    ({"Ep": {"01": {"Type": "Switch"}}, "Commands": {"20": ["6", "00"]}}, "GPMODEL-LOAD-02"),
    ({"Ep": {"01": {"Type": "Switch"}}, "Commands": {}}, "GPMODEL-LOAD-02"),
])
def test_broken_file_is_an_error_and_left_out(tmp_path, content, code):
    p = plugin()
    write(tmp_path, "Broken.json", content)
    write(tmp_path, "Good.json", GOOD)

    models = load_gp_models(p, tmp_path)

    assert list(models) == ["Good"]
    (args,) = errors(p)
    assert args[4] == {"Error code": code, "File": "Broken.json"}


def test_no_folder_no_types(tmp_path):
    p = plugin()

    assert load_gp_models(p, tmp_path) == {}
    assert gp_model_list(p) == []


def test_command_mapping():
    p = plugin()
    load_gp_models(p, REPO_CONF)

    assert gp_model_command(p, "GreenPower-OnOff-Dim", 0x35) == ("0008", "moveup")
    assert gp_model_command(p, "GreenPower-OnOff-Dim", 0x34) == ("0008", "stop")
    assert gp_model_command(p, "GreenPower-OnOff-Dim", 0x22) is None
    assert gp_model_command(p, "Unknown", 0x20) is None
