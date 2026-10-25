#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.WebServer.rest_Ota, the OTA endpoints of the WebUI.

- get_device_informations() feeds the device list of Admin > Firmware
  (GET /ota-firmware-device-list/<ManufCode>).
- rest_ota_firmware_update() is PUT /ota-firmware-update.

Tests marked xfail(strict=True) document a defect found by the OTA review
of 2026-10-25.
"""

import json
import sys
import types
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def rest_ota(monkeypatch):
    """Import Classes.WebServer.rest_Ota fresh; stubs are undone after the test."""
    stubs = {
        "Modules.bindings": dict(webBind=MagicMock(name="webBind"), webUnBind=MagicMock(name="webUnBind")),
        "Modules.domoticzAbstractLayer": dict(
            domoticz_error_api=MagicMock(name="domoticz_error_api"),
            domoticz_log_api=MagicMock(name="domoticz_log_api"),
            domoticz_status_api=MagicMock(name="domoticz_status_api"),
        ),
        "Modules.zigateConsts": dict(ZCL_CLUSTERS_ACT={}),
    }
    for name, attrs in stubs.items():
        if name not in sys.modules:
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
        for attr, value in attrs.items():
            if not hasattr(sys.modules[name], attr):
                monkeypatch.setattr(sys.modules[name], attr, value, raising=False)

    monkeypatch.delitem(sys.modules, "Classes.WebServer.rest_Ota", raising=False)
    import Classes.WebServer.rest_Ota as module
    yield module
    sys.modules.pop("Classes.WebServer.rest_Ota", None)


@pytest.fixture
def webserver():
    ws = MagicMock()
    ws.pluginconf.pluginConf = {"enableKeepalive": False}
    ws.ListOfDevices = {
        "1234": {
            "ZDeviceName": "Bulb",
            "Model": "TRADFRI bulb",
            "SWBUILD_1": "build-1",
            "SWBUILD_3": "build-3",
            "Ep": {"01": {"0006": {}}, "02": {"0019": {}}},
            "OTAUpgrade": {
                "1700000000": {"Time": "2023-11-14 22:13:20", "Version": "01000000", "Type": "2203"},
                "1760000000": {"Time": "2025-10-09 10:53:20", "Version": "01020304", "Type": "2203"},
            },
        }
    }
    return ws


# ─── device list ──────────────────────────────────────────────────────────────

def test_device_information_picks_the_ota_endpoint(rest_ota, webserver):
    info = rest_ota.get_device_informations(webserver, "1234")

    assert info["Nwkid"] == "1234"
    assert info["Ep"] == "02"
    assert info["DeviceName"] == "Bulb"


def test_device_information_software_builds(rest_ota, webserver):
    info = rest_ota.get_device_informations(webserver, "1234")

    assert (info["SWBUILD_1"], info["SWBUILD_3"]) == ("build-1", "build-3")


def test_device_information_last_upgrade(rest_ota, webserver):
    info = rest_ota.get_device_informations(webserver, "1234")

    assert (info["LastUpdate"], info["LastUpdateVersion"], info["LastImageType"]) == ("2025-10-09 10:53:20", "01020304", "2203")


def test_device_information_uses_the_webui_field_names(rest_ota, webserver):
    info = rest_ota.get_device_informations(webserver, "1234")

    assert (info["OTALastTime"], info["OTAVersion"], info["OTAType"]) == ("2025-10-09 10:53:20", "01020304", "2203")


def test_device_information_reports_what_the_device_queried(rest_ota, webserver):
    webserver.ListOfDevices["1234"]["OTAClient"] = {"ManufacturerCode": 0x117C, "ImageType": 0x2203, "CurrentImageVersion": 0x01000000}

    info = rest_ota.get_device_informations(webserver, "1234")

    assert (info["ImageType"], info["CurrentFileVersion"]) == ("2203", "01000000")


def test_device_information_of_a_device_never_upgraded(rest_ota, webserver):
    for key in ("OTAUpgrade", "SWBUILD_1", "SWBUILD_3"):
        del webserver.ListOfDevices["1234"][key]

    info = rest_ota.get_device_informations(webserver, "1234")

    assert info["LastUpdate"] == info["OTALastTime"] == info["ImageType"] == info["SWBUILD_1"] == ""


def test_device_information_falls_back_to_the_legacy_ota_key(rest_ota, webserver):
    webserver.ListOfDevices["1234"]["OTA"] = webserver.ListOfDevices["1234"].pop("OTAUpgrade")

    assert rest_ota.get_device_informations(webserver, "1234")["LastUpdateVersion"] == "01020304"


# ─── PUT /ota-firmware-update ─────────────────────────────────────────────────

def _put(rest_ota, webserver, body):
    return rest_ota.rest_ota_firmware_update(webserver, "PUT", json.dumps(body).encode("utf8"), [])


def _request(nwkid):
    return {"NwkId": nwkid, "Ep": "01", "Brand": "Ikea", "FileName": "bulb.ota", "ForceUpdate": False}


def test_update_request_is_handed_to_the_ota_manager(rest_ota, webserver):
    response = _put(rest_ota, webserver, [_request("1234")])

    webserver.OTA.restapi_firmware_update.assert_called_once_with([_request("1234")])
    assert json.loads(response["Data"])["Name"] == "OTA requested."


def test_update_request_with_a_missing_key_is_rejected(rest_ota, webserver):
    body = [_request("1234")]
    del body[0]["ForceUpdate"]

    response = _put(rest_ota, webserver, body)

    webserver.OTA.restapi_firmware_update.assert_not_called()
    assert json.loads(response["Data"]) == {"Error": "Missing attributes"}


def test_update_request_reports_success_whatever_the_ota_manager_did(rest_ota, webserver):
    """Pins today's behaviour (issue #2169): the OTA manager drops a list of
    several devices, yet the WebUI is told "OTA requested." and shows a success toast."""
    webserver.OTA.restapi_firmware_update.return_value = None

    response = _put(rest_ota, webserver, [_request("1234"), _request("5678")])

    assert json.loads(response["Data"])["Name"] == "OTA requested."


def test_update_request_needs_put(rest_ota, webserver):
    response = rest_ota.rest_ota_firmware_update(webserver, "GET", None, [])

    assert response["Data"] is None
    webserver.OTA.restapi_firmware_update.assert_not_called()
