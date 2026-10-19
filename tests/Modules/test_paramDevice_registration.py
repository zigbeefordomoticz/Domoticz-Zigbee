#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Static check for Modules.paramDevice.initialize_device_settings.

Regression coverage for GitHub issue #2138: NAMRON_DEVICE_PARAMETERS was
imported but never added to the parameter groups, so any Param later added
to it would have been silently ignored. Every *_DEVICE_PARAMETERS imported
by paramDevice.py must be registered.

The check parses the source instead of importing it: paramDevice.py pulls in
most of the device modules, which would all need stubbing.
"""

import ast
from pathlib import Path

PARAM_DEVICE = Path(__file__).resolve().parents[2] / "Modules" / "paramDevice.py"

# Imported but deliberately not registered yet. Registering it changes
# behaviour (KeybadLockout is declared by certified Schneider thermostats),
# so it is left to its own change. Remove the entry when it is registered.
KNOWN_UNREGISTERED = {"THERMOSTAT_UI_DEVICE_PARAMETERS"}


def _parse():
    return ast.parse(PARAM_DEVICE.read_text(encoding="utf-8"))


def _imported_parameter_groups(tree):
    return {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if (alias.asname or alias.name).endswith("_DEVICE_PARAMETERS")
    }


def _registered_parameter_groups(tree):
    func = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "initialize_device_settings"
    )
    registered = []
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.List):
            registered.extend(elt.id for elt in node.value.elts if isinstance(elt, ast.Name))
    return registered


def test_every_imported_parameter_group_is_registered():
    tree = _parse()
    missing = _imported_parameter_groups(tree) - set(_registered_parameter_groups(tree)) - KNOWN_UNREGISTERED
    assert not missing, f"imported but not registered in initialize_device_settings: {sorted(missing)}"


def test_namron_parameters_registered():
    assert "NAMRON_DEVICE_PARAMETERS" in _registered_parameter_groups(_parse())


def test_known_unregistered_is_still_imported_and_unregistered():
    tree = _parse()
    stale = KNOWN_UNREGISTERED - (_imported_parameter_groups(tree) - set(_registered_parameter_groups(tree)))
    assert not stale, f"remove from KNOWN_UNREGISTERED: {sorted(stale)}"


def test_no_parameter_group_registered_twice():
    registered = _registered_parameter_groups(_parse())
    assert len(registered) == len(set(registered))
