"""
test_OTA_codes_vendors.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the OTA_CODES vendor table.

A vendor missing from OTA_CODES has two visible symptoms, both reported in
zigbeefordomoticz/Domoticz-Zigbee#2065 for Innr (manufacturer code 0x1166):

  - notify_ota_firmware_available() cannot resolve the manufacturer code to a
    folder, so instead of telling the user where to store the firmware it logs
    "to get this Manufacturer supported: 4454";
  - ota_scan_folder() never scans a folder for that vendor, so even a manually
    downloaded image is never offered in the WebUI.

Adding a vendor is therefore a table entry plus a firmware folder that actually
exists, which is what these tests pin.

Classes.OTA is imported inside a fixture against locally stubbed dependencies,
and sys.modules is restored on teardown so neither the conftest stubs nor the
other test modules are disturbed.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_codes_vendors.py -v
"""

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


_OTA_DEPS = {
    "Modules.sendZigateCommand": dict(sendZigateCmd=MagicMock(name="sendZigateCmd")),
    "Modules.tools": dict(get_device_nickname=MagicMock(name="get_device_nickname")),
    "Modules.zigateConsts": dict(ADDRESS_MODE={"short": 2, "ieee": 3, "group": 4}, ZIGATE_EP="01"),
    "Zigbee.zclRawCommands": dict(
        zcl_raw_ota_image_block_response_success=MagicMock(name="zcl_raw_ota_image_block_response_success"),
        zcl_raw_ota_image_notify=MagicMock(name="zcl_raw_ota_image_notify"),
        zcl_raw_ota_query_next_image_response=MagicMock(name="zcl_raw_ota_query_next_image_response"),
        zcl_raw_ota_upgrade_end_response=MagicMock(name="zcl_raw_ota_upgrade_end_response"),
    ),
}

OTA_FIRMWARE_ROOT = Path(__file__).resolve().parents[3] / "OTAFirmware"


@pytest.fixture(scope="module")
def ota_module():
    saved = {name: sys.modules.pop(name, None) for name in list(_OTA_DEPS) + ["Classes.OTA"]}
    for name, attrs in _OTA_DEPS.items():
        sys.modules[name] = _make_stub(name, **attrs)

    module = importlib.import_module("Classes.OTA")
    yield module

    for name in list(_OTA_DEPS) + ["Classes.OTA"]:
        sys.modules.pop(name, None)
    for name, mod in saved.items():
        if mod is not None:
            sys.modules[name] = mod


def _folders(entry):
    """"Folder" is a single name, or a list of them."""
    folder = entry["Folder"]

    return [folder] if isinstance(folder, str) else list(folder)


# ─── Innr (issue 2065) ────────────────────────────────────────────────────────

def test_innr_is_declared(ota_module):
    """0x1166 is Innr, per Modules/manufacturer_code.py and Tools/read_ota_headers.py."""
    entry = ota_module.OTA_CODES["Innr"]

    assert entry["ManufCode"] == 0x1166
    assert entry["Enabled"] is True
    assert "INNR" in _folders(entry)


def test_innr_manufacturer_code_resolves_to_a_folder(ota_module):
    """The lookup notify_ota_firmware_available() performs must now find Innr.

    While it returned None the plugin logged "to get this Manufacturer
    supported: 4454" instead of naming a folder.
    """
    folder = next(
        (_folders(entry)[0] for entry in ota_module.OTA_CODES.values() if entry["ManufCode"] == 0x1166),
        None,
    )

    assert folder == "INNR"


# ─── table invariants ─────────────────────────────────────────────────────────

def test_every_declared_folder_exists(ota_module):
    """A folder that does not exist is skipped silently by ota_scan_folder()."""
    missing = [
        (brand, folder)
        for brand, entry in ota_module.OTA_CODES.items()
        for folder in _folders(entry)
        if not (OTA_FIRMWARE_ROOT / folder).is_dir()
    ]

    assert not missing, "OTA_CODES folders with no directory under OTAFirmware/: %s" % missing


def test_manufacturer_codes_are_plausible(ota_module):
    for brand, entry in ota_module.OTA_CODES.items():
        assert isinstance(entry["ManufCode"], int), brand
        assert 0 <= entry["ManufCode"] <= 0xFFFF, brand
