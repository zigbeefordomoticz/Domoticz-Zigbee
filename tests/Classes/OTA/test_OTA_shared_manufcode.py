"""
test_OTA_shared_manufcode.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the OTA_CODES shared-manufacturer-code handling.

A Zigbee manufacturer code is not unique across vendors: 0x1037 is shipped by
Eurotronic, LiXee and Lumi, 0x1015 by Develco and frient. While each of those
vendors had its own OTA_CODES entry:

  - the ManufCode -> Folder reverse lookup in notify_ota_firmware_available()
    returned whichever entry came first in the dict, so a LiXee device was told
    its firmware belonged in EUROTRONICS/;
  - the "same ImageType, another brand" guard in ota_scan_folder() keys on the
    brand, so two images sharing a manufacturer code and an image type shadowed
    each other and only the first brand scanned kept its firmware.

One generic entry now owns each shared code, and "Folder" may list several
folders so the former per-vendor folders keep being scanned.

Classes.OTA is imported inside a fixture against locally stubbed dependencies,
and sys.modules is restored on teardown so neither the conftest stubs nor the
other test modules are disturbed.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_shared_manufcode.py -v
"""

import collections
import importlib
import sys
import types
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


# ─── the table's invariant ────────────────────────────────────────────────────

def test_each_manufacturer_code_is_owned_by_one_entry(ota_module):
    """The reverse lookup only has a single answer if no code is declared twice."""
    counts = collections.Counter(entry["ManufCode"] for entry in ota_module.OTA_CODES.values())
    duplicates = {"0x%04X" % code: n for code, n in counts.items() if n > 1}

    assert not duplicates, "manufacturer codes declared by more than one entry: %s" % duplicates


def test_shared_codes_are_owned_by_a_generic_entry(ota_module):
    by_code = {entry["ManufCode"]: (brand, entry) for brand, entry in ota_module.OTA_CODES.items()}

    brand, entry = by_code[0x1037]
    assert ota_module.ota_brand_folders(entry) == ["GENERIC-1037", "EUROTRONICS", "LIXEE", "LUMI"]
    assert brand == "Eurotronic-LiXee-Lumi"

    brand, entry = by_code[0x1015]
    assert ota_module.ota_brand_folders(entry) == ["GENERIC-1015", "DEVELCO"]
    assert brand == "Develco-frient"


def test_every_entry_declares_the_fields_the_scan_reads(ota_module):
    for brand, entry in ota_module.OTA_CODES.items():
        assert isinstance(entry["Enabled"], bool), brand
        folders = ota_module.ota_brand_folders(entry)
        assert folders, brand
        assert all(isinstance(f, str) and f for f in folders), brand


# ─── ota_brand_folders ────────────────────────────────────────────────────────

def test_ota_brand_folders_accepts_a_single_name(ota_module):
    assert ota_module.ota_brand_folders({"Folder": "DANFOSS"}) == ["DANFOSS"]


def test_ota_brand_folders_copies_the_list(ota_module):
    entry = {"Folder": ["GENERIC-1037", "LIXEE"]}
    folders = ota_module.ota_brand_folders(entry)
    folders.append("MUTATED")

    assert entry["Folder"] == ["GENERIC-1037", "LIXEE"]


# ─── ota_scan_folder ──────────────────────────────────────────────────────────

def _headers(manuf_code, image_type, image_version):
    return {
        "manufacturer_code": manuf_code,
        "image_type": image_type,
        "image_version": image_version,
        "image_size": 1024,
    }


@pytest.fixture
def scanner(ota_module, monkeypatch):
    """Drive ota_scan_folder() against an in-memory firmware tree.

    `tree` maps a folder name to {filename: headers}; only those folders exist.
    """
    def _run(tree, ota_codes=None):
        self = MagicMock()
        self.log = MagicMock()
        self.ListOfImages = {}
        self.pluginconf.pluginConf = {"pluginOTAFirmware": "/fw"}

        def _folder_of(path):
            return path[len("/fw/"):]

        monkeypatch.setattr(ota_module, "exists", lambda path: _folder_of(path) in tree)
        monkeypatch.setattr(ota_module, "listdir", lambda path: sorted(tree[_folder_of(path)]))
        monkeypatch.setattr(ota_module, "isfile", lambda path: True)
        monkeypatch.setattr(ota_module, "join", lambda *parts: "/".join(parts))
        monkeypatch.setattr(
            ota_module,
            "ota_extract_image_headers",
            lambda _self, subfolder, image: (
                tree[subfolder][image]["image_type"],
                tree[subfolder][image],
                b"\x00" * 16,
            ),
        )
        if ota_codes is not None:
            monkeypatch.setattr(ota_module, "OTA_CODES", ota_codes)

        ota_module.ota_scan_folder(self)
        return self.ListOfImages

    return _run


def test_two_vendors_sharing_a_code_both_load(ota_module, scanner):
    """The case that used to drop one image: same code, same image type, two folders.

    Only the newer image survives - they are indistinguishable to the protocol -
    but it is now chosen on version rather than on which folder was scanned first.
    """
    images = scanner({
        "EUROTRONICS": {"euro.ota": _headers(0x1037, 0x0101, 0x00000001)},
        "LIXEE": {"zlinky.ota": _headers(0x1037, 0x0101, 0x00000009)},
    })

    brand = "Eurotronic-LiXee-Lumi"
    assert images["ImageType"][0x0101] == brand
    assert list(images["Brands"][brand]) == ["zlinky.ota"]
    assert images["Brands"][brand]["zlinky.ota"]["originalVersion"] == 0x00000009


def test_distinct_image_types_under_a_shared_code_all_load(ota_module, scanner):
    """The common case: one code, different image types per vendor, nothing dropped."""
    images = scanner({
        "EUROTRONICS": {"euro.ota": _headers(0x1037, 0x0101, 0x00000001)},
        "LIXEE": {"zlinky.ota": _headers(0x1037, 0x0202, 0x00000002)},
        "LUMI": {"lumi.ota": _headers(0x1037, 0x0303, 0x00000003)},
    })

    brand = "Eurotronic-LiXee-Lumi"
    assert set(images["Brands"][brand]) == {"euro.ota", "zlinky.ota", "lumi.ota"}
    assert {0x0101, 0x0202, 0x0303} <= set(images["ImageType"])


def test_legacy_per_vendor_folders_are_still_scanned(ota_module, scanner):
    """Firmware an existing installation left in LIXEE/ must not disappear."""
    images = scanner({"LIXEE": {"zlinky.ota": _headers(0x1037, 0x0202, 0x00000002)}})

    entry = images["Brands"]["Eurotronic-LiXee-Lumi"]["zlinky.ota"]
    assert entry["Directory"] == "/fw/LIXEE"
    assert entry["intManufCode"] == 0x1037


def test_image_keeps_the_directory_it_was_found_in(ota_module, scanner):
    """Each image records its own folder, so the loader reads the right path."""
    images = scanner({
        "GENERIC-1037": {"new.ota": _headers(0x1037, 0x0101, 0x00000001)},
        "LUMI": {"old.ota": _headers(0x1037, 0x0202, 0x00000002)},
    })

    brand = images["Brands"]["Eurotronic-LiXee-Lumi"]
    assert brand["new.ota"]["Directory"] == "/fw/GENERIC-1037"
    assert brand["old.ota"]["Directory"] == "/fw/LUMI"


def test_missing_folders_are_skipped(ota_module, scanner):
    """A generic entry lists folders a given installation will not have."""
    images = scanner({"GENERIC-1015": {"develco.ota": _headers(0x1015, 0x0404, 0x00000004)}})

    assert list(images["Brands"]["Develco-frient"]) == ["develco.ota"]


def test_readme_and_precious_markers_are_not_parsed_as_firmware(ota_module, scanner):
    images = scanner({
        "GENERIC-1037": {
            "README.md": _headers(0x1037, 0x0101, 0x00000001),
            ".precious": _headers(0x1037, 0x0102, 0x00000001),
            "real.ota": _headers(0x1037, 0x0103, 0x00000001),
        }
    })

    assert list(images["Brands"]["Eurotronic-LiXee-Lumi"]) == ["real.ota"]


def test_disabled_entry_is_not_scanned(ota_module, scanner):
    images = scanner(
        {"LIXEE": {"zlinky.ota": _headers(0x1037, 0x0202, 0x00000002)}},
        ota_codes={"Off": {"Folder": ["LIXEE"], "ManufCode": 0x1037, "ManufName": "x", "Enabled": False}},
    )

    assert images["Brands"] == {}
