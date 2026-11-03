"""
test_OTA_index.py
~~~~~~~~~~~~~~~~~
Unit tests for the online firmware indexes (checkFirmwareAgainstZigbeeOTARepository):
convert_ikea_format_to_list, convert_sonoff_format_to_list,
check_ota_availability_from_index, notify_ota_firmware_available,
loading_zigbee_ota_index and _load_json_from_url.

Tests marked xfail(strict=True) document a defect found by the OTA review
of 2026-10-25.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_index.py -v
"""

import io
import json
import urllib.error
from unittest.mock import MagicMock

import pytest
from ota_builders import DEVICE_NWKID


def _entry(version, image_type=0x2203, manuf_code=0x117C):
    return {"manufacturerCode": manuf_code, "imageType": image_type, "fileVersion": version, "url": "https://example.invalid/%08x" % version}


# ─── vendor formats ───────────────────────────────────────────────────────────

def test_convert_ikea_format(ota_module):
    ikea = [
        {"fw_file_version_MSB": 0x0102, "fw_file_version_LSB": 0x0304, "fw_manufacturer_id": 0x117C,
         "fw_image_type": 0x2203, "fw_binary_url": "https://example.invalid/bulb.ota"},
        {"fw_type": 3, "fw_binary_url": "https://example.invalid/gateway.bin"},   # gateway entry, no version
    ]

    assert ota_module.convert_ikea_format_to_list(ikea) == [
        {"fileVersion": 0x01020304, "manufacturerCode": 0x117C, "imageType": 0x2203, "url": "https://example.invalid/bulb.ota"}
    ]


def test_convert_sonoff_format(ota_module):
    sonoff = [{"fw_file_version": 0x1000, "fw_manufacturer_id": 0x1286, "fw_image_type": 0x0001, "fw_binary_url": "https://example.invalid/s.ota"}]

    assert ota_module.convert_sonoff_format_to_list(sonoff) == [
        {"fileVersion": 0x1000, "manufacturerCode": 0x1286, "imageType": 0x0001, "url": "https://example.invalid/s.ota"}
    ]


# ─── lookup ───────────────────────────────────────────────────────────────────

def test_lookup_without_an_index(ota_module, ota):
    ota.zigbee_ota_index = None

    assert ota_module.check_ota_availability_from_index(ota, 0x117C, 0x2203, 0x01000000) is None


def test_lookup_returns_a_newer_matching_image_only(ota_module, ota):
    ota.zigbee_ota_index = [_entry(0x00FF0000), _entry(0x02000000, image_type=0x4204), _entry(0x02000000, manuf_code=0x100B), _entry(0x02000000)]

    assert ota_module.check_ota_availability_from_index(ota, 0x117C, 0x2203, 0x01000000) == _entry(0x02000000)
    assert ota_module.check_ota_availability_from_index(ota, 0x117C, 0x2203, 0x02000000) == {}


def test_lookup_reports_the_newest_version(ota_module, ota):
    ota.zigbee_ota_index = [_entry(0x02000000), _entry(0x03000000)]

    assert ota_module.check_ota_availability_from_index(ota, 0x117C, 0x2203, 0x01000000)["fileVersion"] == 0x03000000


def test_notify_records_the_update_on_the_device(ota_module, ota):
    ota_module.notify_ota_firmware_available(ota, DEVICE_NWKID, 0x117C, 0x2203, 0x01000000, _entry(0x02000000))

    assert ota.ListOfDevices[DEVICE_NWKID]["OTAUpdate"] == {
        0x2203: {"currentversion": str(0x01000000), "newestversion": str(0x02000000), "url": "https://example.invalid/02000000"}
    }


def test_notify_for_an_unknown_device_only_logs(ota_module, ota):
    ota_module.notify_ota_firmware_available(ota, "ffff", 0x117C, 0x2203, 0x01000000, _entry(0x02000000))

    assert "ffff" not in ota.ListOfDevices


# ─── loading ──────────────────────────────────────────────────────────────────

def test_index_is_not_loaded_without_internet(ota_module, ota, monkeypatch):
    load = MagicMock(return_value=[])
    monkeypatch.setattr(ota_module, "_load_json_from_url", load)
    ota.internet_available = False

    ota_module.loading_zigbee_ota_index(ota)

    load.assert_not_called()
    assert ota.zigbee_ota_index is None


def test_index_merges_the_three_sources(ota_module, ota, monkeypatch):
    ota.internet_available = True
    ota.pluginconf.pluginConf.update(
        internetAccess=True, ZigbeeOTA_Repository="koenkk", IkeaTradfri_Repository="ikea", Sonoff_Repository="sonoff"
    )
    sources = {
        "koenkk": [_entry(0x02000000)],
        "ikea": [{"fw_file_version_MSB": 1, "fw_file_version_LSB": 2, "fw_manufacturer_id": 0x117C, "fw_image_type": 0x4204, "fw_binary_url": "u"}],
        "sonoff": [{"fw_file_version": 3, "fw_manufacturer_id": 0x1286, "fw_image_type": 1, "fw_binary_url": "v"}],
    }
    monkeypatch.setattr(ota_module, "_load_json_from_url", lambda self, url: sources[url])

    ota_module.loading_zigbee_ota_index(ota)

    assert [entry["imageType"] for entry in ota.zigbee_ota_index] == [0x2203, 0x4204, 1]


def _http_error(code):
    return urllib.error.HTTPError("https://example.invalid", code, "error", {}, None)


def test_load_json_from_url(ota_module, ota, monkeypatch):
    urlopen = MagicMock(return_value=io.BytesIO(json.dumps([1, 2]).encode()))
    monkeypatch.setattr(ota_module.urllib.request, "urlopen", urlopen)

    assert ota_module._load_json_from_url(ota, "https://example.invalid") == [1, 2]


def test_load_json_from_url_fails_fast_on_404(ota_module, ota, monkeypatch):
    urlopen = MagicMock(side_effect=_http_error(404))
    sleep = MagicMock()
    monkeypatch.setattr(ota_module.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(ota_module.time, "sleep", sleep)

    assert ota_module._load_json_from_url(ota, "https://example.invalid") == []
    assert urlopen.call_count == 1
    sleep.assert_not_called()


def test_load_json_from_url_retries_on_503(ota_module, ota, monkeypatch):
    urlopen = MagicMock(side_effect=_http_error(503))
    sleep = MagicMock()
    monkeypatch.setattr(ota_module.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(ota_module.time, "sleep", sleep)

    assert ota_module._load_json_from_url(ota, "https://example.invalid", retries=3) == []
    assert urlopen.call_count == 3
    assert sleep.call_count == 2


@pytest.mark.parametrize("retry_after, expected_delay", [("12", 12.0), ("120", 30.0), ("Wed, 21 Oct 2026 07:28:00 GMT", 1.0)])
def test_load_json_from_url_honours_retry_after(ota_module, ota, monkeypatch, retry_after, expected_delay):
    """A numeric Retry-After is used (capped at 30 s); an HTTP-date keeps the 1 s backoff."""
    error = urllib.error.HTTPError("https://example.invalid", 429, "Too Many Requests", {"Retry-After": retry_after}, None)
    urlopen = MagicMock(side_effect=[error, io.BytesIO(b"[]")])
    sleep = MagicMock()
    monkeypatch.setattr(ota_module.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(ota_module.time, "sleep", sleep)
    monkeypatch.setattr(ota_module.random, "uniform", lambda a, b: 0.0)

    assert ota_module._load_json_from_url(ota, "https://example.invalid") == []
    sleep.assert_called_once_with(expected_delay)
