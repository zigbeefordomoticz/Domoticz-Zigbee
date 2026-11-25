#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
plugin.py gives each argument of IAS_Zone_Management to the parameter of the
same name.

plugin.py cannot be imported outside Domoticz: the call and the signature are
compared from the sources.
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _parse(filename):
    return ast.parse((REPO_ROOT / filename).read_text(encoding="utf-8"))


def _constructor_parameters():
    for node in ast.walk(_parse("Classes/IAS.py")):
        if isinstance(node, ast.ClassDef) and node.name == "IAS_Zone_Management":
            init = next(n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
            return [arg.arg for arg in init.args.args[1:]]
    raise AssertionError("IAS_Zone_Management not found in Classes/IAS.py")


def _arguments_given_by_plugin():
    calls = [
        node for node in ast.walk(_parse("plugin.py"))
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "IAS_Zone_Management"
    ]
    assert len(calls) == 1
    arguments = dict(zip(_constructor_parameters(), calls[0].args))
    arguments.update({keyword.arg: keyword.value for keyword in calls[0].keywords})
    return {parameter: ast.unparse(value) for parameter, value in arguments.items()}


@pytest.mark.parametrize(
    "parameter",
    ["pluginconf", "ListOfDevices", "IEEE2NWK", "DeviceConf", "log", "FirmwareVersion", "readZclClusters", "pairing_in_progress"],
)
def test_argument_goes_to_the_parameter_of_the_same_name(parameter):
    assert _arguments_given_by_plugin()[parameter] == f"self.{parameter}"


def test_arguments_with_another_name():
    arguments = _arguments_given_by_plugin()
    assert arguments["ZigateComm"] == "self.ControllerLink"
    assert arguments["zigbee_communitation"] == "self.zigbee_communication"
