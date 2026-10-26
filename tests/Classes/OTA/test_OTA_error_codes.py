"""
test_OTA_error_codes.py
~~~~~~~~~~~~~~~~~~~~~~~
The OTA logging rules (OTA review 2026-10-25), checked on the source:

- every logging(self, "Error", ...) in Classes/OTA.py passes a context;
- every "Error code" used in Classes/OTA.py and Classes/WebServer/rest_Ota.py
  is declared in OTA_ERROR_CODES;
- the codes are "OTA" + 4 digits, each declared once.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_error_codes.py -v
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OTA_SOURCE = ROOT / "Classes" / "OTA.py"
REST_SOURCE = ROOT / "Classes" / "WebServer" / "rest_Ota.py"
CODE_IN_SOURCE = re.compile(r'"Error code":\s*"(OTA\d{4})"')


def test_codes_are_well_formed_and_described(ota_module):
    for code, description in ota_module.OTA_ERROR_CODES.items():
        assert re.fullmatch(r"OTA\d{4}", code), code
        assert description


def test_codes_are_declared_once():
    declared = re.findall(r'^\s*"(OTA\d{4})":', OTA_SOURCE.read_text(), re.MULTILINE)

    assert len(declared) == len(set(declared))


def test_every_code_used_is_declared(ota_module):
    used = set(CODE_IN_SOURCE.findall(OTA_SOURCE.read_text())) | set(CODE_IN_SOURCE.findall(REST_SOURCE.read_text()))

    assert used, "no error code found: the pattern no longer matches the source"
    assert used <= set(ota_module.OTA_ERROR_CODES), sorted(used - set(ota_module.OTA_ERROR_CODES))


def test_every_error_log_passes_a_context():
    tree = ast.parse(OTA_SOURCE.read_text())
    missing = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "logging"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == "Error"
        and len(node.args) < 5
        and not any(keyword.arg == "context" for keyword in node.keywords)
    ]

    assert not missing, f"Error logged without a context at Classes/OTA.py lines {missing}"
