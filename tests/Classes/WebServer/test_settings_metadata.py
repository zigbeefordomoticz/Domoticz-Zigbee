"""
Settings metadata for the WebUI Settings page.

The SETTINGS table is read with ast from Classes/PluginConf.py rather than
imported: importing Classes.PluginConf pulls real Modules.* in and breaks the
conftest stubs of unrelated tests.
"""

import ast
import unittest
from pathlib import Path

from Classes.WebServer.settings_metadata import (check_numeric_setting,
                                                 setting_metadata)

PLUGINCONF = Path(__file__).resolve().parents[3] / "Classes" / "PluginConf.py"
KNOWN_UNITS = {"s", "h", "ds", "dBm"}
UI_SECTIONS_SKIPPED = ("VerboseLogging", "Reserved", "PluginTransport")


def load_settings_table():
    tree = ast.parse(PLUGINCONF.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "SETTINGS":
            return ast.literal_eval(node.value)
    raise AssertionError("SETTINGS not found in Classes/PluginConf.py")


SETTINGS = load_settings_table()
ALL = {param: definition for theme in SETTINGS.values() for param, definition in theme["param"].items()}


def shown_settings():
    for theme, content in SETTINGS.items():
        if theme in UI_SECTIONS_SKIPPED:
            continue
        for param, definition in content["param"].items():
            if not definition["hidden"]:
                yield theme, param, definition


class TestSettingMetadata(unittest.TestCase):
    def test_only_known_keys_are_forwarded(self):
        definition = {"type": "int", "default": 30, "restart": 0, "hidden": False, "Advanced": False,
                      "Group": "MotionSelectors", "Unit": "s", "Min": 0, "Max": 3600, "Step": 1, "ZigpyRadio": ""}
        self.assertEqual(
            setting_metadata(definition),
            {"Group": "MotionSelectors", "Unit": "s", "Min": 0, "Max": 3600, "Step": 1},
        )

    def test_definition_without_metadata(self):
        self.assertEqual(setting_metadata({"type": "bool", "default": 0}), {})


class TestCheckNumericSetting(unittest.TestCase):
    INT = {"type": "int", "Min": 0, "Max": 3600}
    FLOAT = {"type": "float", "Min": 0, "Max": 5}

    def test_int_in_range(self):
        self.assertEqual(check_numeric_setting(self.INT, 45), (True, 45))

    def test_int_sent_as_text_or_float(self):
        self.assertEqual(check_numeric_setting(self.INT, "45"), (True, 45))
        self.assertEqual(check_numeric_setting(self.INT, 45.0), (True, 45))

    def test_int_not_whole(self):
        self.assertFalse(check_numeric_setting(self.INT, 4.5)[0])

    def test_int_out_of_range(self):
        self.assertFalse(check_numeric_setting(self.INT, -1)[0])
        self.assertFalse(check_numeric_setting(self.INT, 3601)[0])

    def test_float_sent_as_text_by_an_older_webui(self):
        self.assertEqual(check_numeric_setting(self.FLOAT, "0.75"), (True, 0.75))

    def test_not_a_number(self):
        for value in ("abc", "", None, "nan", "inf"):
            with self.subTest(value=value):
                self.assertFalse(check_numeric_setting(self.FLOAT, value)[0])

    def test_no_range_means_any_number(self):
        self.assertEqual(check_numeric_setting({"type": "int"}, -12), (True, -12))

    def test_other_types_untouched(self):
        self.assertEqual(check_numeric_setting({"type": "hex"}, "1a2b"), (True, "1a2b"))
        self.assertEqual(check_numeric_setting({"type": "url"}, "https://x/y.json"), (True, "https://x/y.json"))
        self.assertEqual(check_numeric_setting({"type": "int"}, True), (True, True))


class TestSettingsTableConsistency(unittest.TestCase):
    def test_every_shown_setting_has_a_group(self):
        missing = [f"{theme}/{param}" for theme, param, definition in shown_settings() if "Group" not in definition]
        self.assertEqual(missing, [])

    def test_depends_on_names_a_bool_setting(self):
        for param, definition in ALL.items():
            parent = definition.get("DependsOn")
            if parent is None:
                continue
            with self.subTest(param=param):
                self.assertIn(parent, ALL)
                self.assertEqual(ALL[parent]["type"], "bool")
                self.assertNotEqual(parent, param)

    def test_default_within_range(self):
        for param, definition in ALL.items():
            if definition["type"] not in ("int", "float"):
                continue
            with self.subTest(param=param):
                if "Min" in definition:
                    self.assertGreaterEqual(definition["default"], definition["Min"])
                if "Max" in definition:
                    self.assertLessEqual(definition["default"], definition["Max"])
                if "Min" in definition and "Max" in definition:
                    self.assertLess(definition["Min"], definition["Max"])

    def test_range_only_on_numbers(self):
        for param, definition in ALL.items():
            if any(key in definition for key in ("Unit", "Min", "Max", "Step")):
                with self.subTest(param=param):
                    self.assertIn(definition["type"], ("int", "float"))

    def test_units_are_known(self):
        for param, definition in ALL.items():
            if "Unit" in definition:
                with self.subTest(param=param):
                    self.assertIn(definition["Unit"], KNOWN_UNITS)

    def test_restart_is_a_level(self):
        for param, definition in ALL.items():
            with self.subTest(param=param):
                self.assertIs(type(definition["restart"]), int)
                self.assertIn(definition["restart"], (0, 1, 2, 3))

    def test_metadata_keys_have_the_right_type(self):
        for param, definition in ALL.items():
            with self.subTest(param=param):
                for key in ("Danger", "OneShot"):
                    if key in definition:
                        self.assertIs(definition[key], True)
                for key in ("Group", "DependsOn"):
                    if key in definition:
                        self.assertIsInstance(definition[key], str)

    def test_one_shot_resets(self):
        one_shots = sorted(param for param, definition in ALL.items() if definition.get("OneShot"))
        self.assertEqual(one_shots, ["resetConfigureReporting", "resetOTAUpdate", "resetReadAttributes"])

    def test_repositories_are_urls(self):
        for param in ("ZigbeeOTA_Repository", "IkeaTradfri_Repository", "Sonoff_Repository"):
            with self.subTest(param=param):
                self.assertEqual(ALL[param]["type"], "url")
                self.assertTrue(ALL[param]["default"].startswith("http"))


if __name__ == "__main__":
    unittest.main()
