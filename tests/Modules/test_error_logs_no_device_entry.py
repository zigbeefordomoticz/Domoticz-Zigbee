#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_error_logs_no_device_entry.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
No Error log carries the device database, or a whole device entry, in its message or context.

An Error is stored in the error history, which users attach to public issues. A device entry
holds what must not go there (IAS_KEYPAD has the PIN codes of an alarm keypad). An Error about
a device passes its nwkid: the logger adds what identifies the device.

Checked on the source: importing the real modules here would break unrelated tests through
the conftest stubs.

Run with:
    pytest tests/Modules/test_error_logs_no_device_entry.py -v
"""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = sorted(
    path for folder in ("Classes", "Modules", "Zigbee", "DevicesModules", "Z4D_decoders")
    for path in (ROOT / folder).rglob("*.py")
) + [ROOT / "plugin.py"]


def whole_device_data(tree):
    """The expressions of the tree whose value is ListOfDevices, or a whole entry of it."""
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    found = []

    def is_taken_apart(node):
        # X[...], X.attribute, "x in X", len(X): something about X, not X
        parent = parents.get(node)
        if isinstance(parent, ast.Subscript):
            return parent.value is node
        if isinstance(parent, ast.Call):
            return isinstance(parent.func, ast.Name) and parent.func.id == "len"
        return isinstance(parent, (ast.Attribute, ast.Compare))

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Attribute) and node.attr == "ListOfDevices"):
            continue
        parent = parents.get(node)
        value = node
        if isinstance(parent, ast.Subscript) and parent.value is node:
            value = parent  # ListOfDevices[nwkid]
        elif isinstance(parent, ast.Attribute) and parent.attr == "get":
            value = parents[parent]  # ListOfDevices.get(nwkid)
        if not is_taken_apart(value):
            found.append(ast.unparse(value))
    return found


def error_data(tree):
    """The Error log calls, and the dicts assigned to a variable used as a context."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if "log" in ast.unparse(node.func).lower() and any(
                    isinstance(arg, ast.Constant) and arg.value == "Error" for arg in node.args):
                yield node
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            if "context" in ast.unparse(node.targets[0]).lower():
                yield node.value


class TestErrorLogsCarryNoDeviceEntry(unittest.TestCase):

    def test_no_error_carries_the_database_or_an_entry(self):
        found = [
            "%s:%s %s" % (path.relative_to(ROOT), node.lineno, whole)
            for path in SOURCES
            for node in error_data(ast.parse(path.read_text(encoding="utf-8")))
            for whole in whole_device_data(node)
        ]
        self.assertEqual(found, [])

    def test_the_sources_are_read(self):
        # The check above would pass on nothing
        calls = sum(1 for path in SOURCES for _ in error_data(ast.parse(path.read_text(encoding="utf-8"))))
        self.assertGreater(calls, 500)


class TestTheCheckItself(unittest.TestCase):

    def found(self, source):
        return whole_device_data(ast.parse(source))

    def test_what_is_refused(self):
        for source in ("f({'x': self.ListOfDevices})", "f(self.ListOfDevices)", "f(str(self.ListOfDevices[nwkid]))",
                       "f('%s' % self.ListOfDevices[nwkid])", "f(f'{self.ListOfDevices[nwkid]}')",
                       "f(self.ListOfDevices.get(nwkid, {}))"):
            with self.subTest(source=source):
                self.assertEqual(len(self.found(source)), 1)

    def test_what_is_allowed(self):
        for source in ("f(len(self.ListOfDevices))", "f(nwkid in self.ListOfDevices)", "f(self.ListOfDevices[nwkid]['Status'])",
                       "f(self.ListOfDevices.get(nwkid, {}).get('Status'))", "f(self.ListOfDevices.keys())",
                       "f(sorted(self.ListOfDevices[nwkid].keys()))"):
            with self.subTest(source=source):
                self.assertEqual(self.found(source), [])


class TestErrorCodes(unittest.TestCase):
    """The codes given to the Errors changed with this check: each used once."""

    def test_each_code_is_used_once(self):
        text = "".join(path.read_text(encoding="utf-8") for path in SOURCES)
        for code in ("CFGR0001", "PAIR0001", "PAIR0002", "PAIR0003", "CMND0001", "CMND0002"):
            with self.subTest(code=code):
                self.assertEqual(text.count('"%s"' % code), 1)


if __name__ == "__main__":
    unittest.main()
