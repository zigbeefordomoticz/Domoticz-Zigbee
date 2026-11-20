#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.WebServer.rest_GreenPower: Green Power devices (GPD) in
the WebUI.

  /zgp-device-raw   the store content, one entry per GPD, never the
                    security key; one GPD by IEEE; {} for an unknown one
  provisioning      the /rcv-nw-hrdwr entries of the GPDs commissioned since
                    pairing was opened: NwkId only until the widgets exist,
                    then once with ProvisionStatus inDB and the widget names;
                    Unexpected when no widget came; Failed when the GPD left
                    the store meanwhile

The module imports Modules.greenPowerStore only (stdlib), so no subprocess.
"""

import copy
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from Classes.WebServer.rest_GreenPower import (GP_PROVISIONING_TIMEOUT,
                                               gp_provisioning_entries,
                                               rest_zgp_device_raw)

IEEE = "00000000c220bd02"
KEY = "00112233445566778899aabbccddeeff"
COMMISSIONED = 1_700_000_000


class FakeStore:
    def __init__(self, records):
        self.records = records

    def get(self, key, default=None):
        return copy.deepcopy(self.records.get(key, default))

    def snapshot(self):
        return copy.deepcopy(self.records)


class FakeWebServer:
    def __init__(self, records):
        self.PluginStores = {"GreenPowerDevices": FakeStore(records)}
        self.GreenPowerInPairingMode = {}
        self.ListOfDomoticzWidget = {
            41: {"Name": "GreenPower-OnOff_Switch-00000000c220bd02-01"},
        }
        self.pluginconf = SimpleNamespace(pluginConf={"enableKeepalive": False})


def gp_record(**fields):
    record = {
        "ieee": "00:00:00:00:c2:20:bd:02",
        "nwk": "bd02",
        "src_id": 3256925442,
        "device_id": 2,
        "manufacturer_id": None,
        "model_id": None,
        "commands": [],
        "security_level": 2,
        "security_key_type": 4,
        "security_key": KEY,
        "frame_counter": 692,
        "Commissioned": COMMISSIONED,
        "LastSeen": COMMISSIONED,
        "LQI": 255,
    }
    record.update(fields)
    return record


WITH_WIDGET = {"Model": "GreenPower-OnOff", "Ep": {"01": {"ClusterType": {"41": "Switch"}}}}


def get_raw(webserver, parameters=()):
    response = rest_zgp_device_raw(webserver, "GET", None, list(parameters))
    return response, json.loads(response["Data"])


# ─── /zgp-device-raw ────────────────────────────────────────────────────────

def test_raw_lists_every_gpd_without_its_security_key():
    webserver = FakeWebServer({IEEE: gp_record(**WITH_WIDGET)})

    response, payload = get_raw(webserver)

    assert response["Headers"]["Content-Type"] == "application/json; charset=utf-8"
    assert len(payload) == 1
    entry = payload[0]
    assert entry["IEEE"] == IEEE
    assert entry["nwk"] == "bd02"
    assert entry["frame_counter"] == 692
    assert entry["WidgetList"] == ["GreenPower-OnOff_Switch-00000000c220bd02-01"]
    assert "security_key" not in entry
    assert KEY not in response["Data"]


def test_raw_answers_one_gpd_by_ieee_and_nothing_for_an_unknown_one():
    webserver = FakeWebServer({IEEE: gp_record()})

    _, payload = get_raw(webserver, [IEEE.upper()])
    assert payload["IEEE"] == IEEE
    assert "security_key" not in payload

    _, payload = get_raw(webserver, ["0000000000000001"])
    assert payload == {}


def test_raw_is_an_empty_list_without_a_store():
    webserver = FakeWebServer({})
    webserver.PluginStores = {}

    _, payload = get_raw(webserver)

    assert payload == []


def test_raw_keeps_the_store_untouched():
    records = {IEEE: gp_record()}
    webserver = FakeWebServer(records)

    get_raw(webserver)

    assert records[IEEE]["security_key"] == KEY


# ─── Provisioning entries ───────────────────────────────────────────────────

def test_nothing_queued_answers_nothing():
    assert gp_provisioning_entries(FakeWebServer({IEEE: gp_record(**WITH_WIDGET)})) == []


def test_a_gpd_without_widget_yet_is_still_joining():
    webserver = FakeWebServer({IEEE: gp_record()})
    webserver.GreenPowerInPairingMode[IEEE] = (COMMISSIONED, "bd02")

    entries = gp_provisioning_entries(webserver, now=COMMISSIONED + 5)

    assert entries == [{"NwkId": "bd02", "IEEE": IEEE, "GreenPower": True}]
    assert IEEE in webserver.GreenPowerInPairingMode


def test_a_gpd_with_its_widget_is_reported_once_as_in_db():
    webserver = FakeWebServer({IEEE: gp_record(**WITH_WIDGET)})
    webserver.GreenPowerInPairingMode[IEEE] = (COMMISSIONED, "bd02")

    entries = gp_provisioning_entries(webserver, now=COMMISSIONED + 5)

    assert entries == [{
        "NwkId": "bd02",
        "GreenPower": True,
        "IEEE": IEEE,
        "ProfileId": "a1e0",
        "ProfileIdDesc": "Green Power",
        "ZDeviceID": "02",
        "ZDeviceIDDesc": "On/Off Switch",
        "Model": "GreenPower-OnOff",
        "PluginCertified": "no",
        "Ep": [],
        "WidgetList": ["GreenPower-OnOff_Switch-00000000c220bd02-01"],
        "ProvisionStatus": "inDB",
        "ProvisionStatusDesc": "inDB",
    }]
    assert gp_provisioning_entries(webserver, now=COMMISSIONED + 10) == []


def test_a_certified_model_is_reported_as_certified():
    webserver = FakeWebServer({IEEE: gp_record(**dict(WITH_WIDGET, Model="Sunricher-ZGP2801K2-DIM"))})
    webserver.GreenPowerInPairingMode[IEEE] = (COMMISSIONED, "bd02")

    (entry,) = gp_provisioning_entries(webserver, now=COMMISSIONED + 5)

    assert entry["PluginCertified"] == "yes"


def test_a_gpd_that_gets_no_widget_ends_as_unexpected():
    webserver = FakeWebServer({IEEE: gp_record(device_id=0xFE)})
    webserver.GreenPowerInPairingMode[IEEE] = (COMMISSIONED, "bd02")

    (entry,) = gp_provisioning_entries(webserver, now=COMMISSIONED + GP_PROVISIONING_TIMEOUT + 1)

    assert entry["ProvisionStatus"] == "Unexpected"
    assert entry["ZDeviceIDDesc"] == "Manufacturer specific"
    assert entry["WidgetList"] == []
    assert webserver.GreenPowerInPairingMode == {}


def test_a_gpd_removed_meanwhile_is_failed():
    webserver = FakeWebServer({})
    webserver.GreenPowerInPairingMode[IEEE] = (COMMISSIONED, "bd02")

    (entry,) = gp_provisioning_entries(webserver, now=COMMISSIONED + 5)

    assert entry["ProvisionStatus"] == "Failed"
    assert entry["IEEE"] == IEEE
    assert entry["NwkId"] == "bd02"
    assert webserver.GreenPowerInPairingMode == {}


@pytest.mark.parametrize("device_id,expected", [(None, "Unknown"), (0x99, "Unknown"), (0x03, "Level Control Switch")])
def test_device_type_description(device_id, expected):
    webserver = FakeWebServer({IEEE: gp_record(device_id=device_id, **WITH_WIDGET)})
    webserver.GreenPowerInPairingMode[IEEE] = (COMMISSIONED, "bd02")

    (entry,) = gp_provisioning_entries(webserver, now=COMMISSIONED + 5)

    assert entry["ZDeviceIDDesc"] == expected


# ─── /rcv-nw-hrdwr ──────────────────────────────────────────────────────────

@pytest.fixture
def rest_provisioning(monkeypatch):
    # tests/conftest.py stubs some of these with only the names other tests need:
    # rest_Provisioning gets complete fakes, and is imported afresh against them
    for name in ("Modules.basicOutputs", "Modules.domoticzAbstractLayer", "Modules.pluginDbAttributes",
                 "Modules.sendZigateCommand", "Modules.zigateConsts"):
        monkeypatch.setitem(sys.modules, name, MagicMock())
    monkeypatch.delitem(sys.modules, "Classes.WebServer.rest_Provisioning", raising=False)
    module = importlib.import_module("Classes.WebServer.rest_Provisioning")
    # Undone first: the copy bound to the fakes leaves sys.modules after the test
    monkeypatch.setitem(sys.modules, "Classes.WebServer.rest_Provisioning", module)
    return module


def test_rcv_nw_hrdwr_answers_a_gpd_when_no_zigbee_device_joined(rest_provisioning):
    rest_rcv_nw_hrdwr = rest_provisioning.rest_rcv_nw_hrdwr

    webserver = FakeWebServer({IEEE: gp_record(**WITH_WIDGET)})
    webserver.GreenPowerInPairingMode[IEEE] = (COMMISSIONED, "bd02")
    webserver.ControllerData = {"Firmware Version": "8.0.2.0"}
    webserver.DevicesInPairingMode = []
    webserver.ListOfDevices = {}

    response = rest_rcv_nw_hrdwr(webserver, "GET", None, [])

    (entry,) = json.loads(response["Data"])["NewDevices"]
    assert entry["IEEE"] == IEEE
    assert entry["ProvisionStatus"] == "inDB"
    assert KEY not in response["Data"]


# ─── /zgp-pairing ───────────────────────────────────────────────────────────

def get_pairing(webserver, parameters=()):
    from Classes.WebServer.rest_GreenPower import rest_zgp_pairing

    response = rest_zgp_pairing(webserver, "GET", None, list(parameters))
    return json.loads(response["Data"])


def test_pairing_feed_with_setting_channel_and_events():
    from Modules.greenPowerFeed import HEARD_WINDOW_OPEN, GreenPowerFeed

    webserver = FakeWebServer({})
    webserver.pluginconf.pluginConf["GreenPowerEnable"] = 1
    webserver.ControllerData = {"Channel": 11}
    webserver.GreenPowerFeed = GreenPowerFeed()
    webserver.GreenPowerFeed.window("opened", 240)
    webserver.GreenPowerFeed.heard(IEEE, 0xE0, HEARD_WINDOW_OPEN, None, -64, 212)

    payload = get_pairing(webserver)

    assert payload["GreenPowerEnable"] is True
    assert payload["Channel"] == 11
    assert payload["Window"]["State"] == "opened"
    assert payload["Seq"] == 2
    assert [e["Event"] for e in payload["Events"]] == ["window", "heard"]
    assert [e["Event"] for e in get_pairing(webserver, ["1"])["Events"]] == ["heard"]


def test_pairing_feed_without_feed_or_controller():
    webserver = FakeWebServer({})

    payload = get_pairing(webserver, ["not-a-number"])

    assert payload == {"Window": {"State": None, "Until": None, "Remaining": 0}, "Model": None, "Seq": 0, "Events": [],
                       "GreenPowerEnable": False, "Channel": None}


# ─── PUT /zgp-pairing, GET /zgp-models ──────────────────────────────────────

REPO_CONF = Path(__file__).resolve().parents[3] / "Conf"


@pytest.fixture
def gp_webserver():
    from Modules.greenPowerFeed import GreenPowerFeed
    from Modules.greenPowerModels import load_gp_models

    webserver = FakeWebServer({})
    webserver.log = MagicMock()
    webserver.zigbee_communication = "zigpy"
    webserver.ControllerLink = MagicMock()
    webserver.GreenPowerFeed = GreenPowerFeed()
    load_gp_models(webserver, REPO_CONF)
    return webserver


def put_pairing(webserver, body):
    from Classes.WebServer.rest_GreenPower import rest_zgp_pairing

    raw = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    response = rest_zgp_pairing(webserver, "PUT", raw, [])
    return response, json.loads(response["Data"])


def test_put_opens_green_power_only_with_the_picked_type(gp_webserver):
    response, payload = put_pairing(gp_webserver, {"Duration": 240, "Model": "GreenPower-OnOff-Dim"})

    assert response["Status"] == "200 OK"
    assert payload == {"Duration": 240, "Model": "GreenPower-OnOff-Dim"}
    gp_webserver.ControllerLink.sendData.assert_called_once_with("PERMIT-GP", {"Duration": 240})
    gp_webserver.GreenPowerFeed.window("opened", 240)
    assert gp_webserver.GreenPowerFeed.pairing_model() == "GreenPower-OnOff-Dim"


def test_put_without_type_is_automatic(gp_webserver):
    _, payload = put_pairing(gp_webserver, {"Duration": 240, "Model": None})

    assert payload["Model"] is None
    assert gp_webserver.GreenPowerFeed.pairing_model() is None


def test_put_zero_closes_and_forgets_the_type(gp_webserver):
    put_pairing(gp_webserver, {"Duration": 240, "Model": "GreenPower-OnOff"})

    put_pairing(gp_webserver, {"Duration": 0, "Model": "GreenPower-OnOff"})

    gp_webserver.ControllerLink.sendData.assert_called_with("PERMIT-GP", {"Duration": 0})
    assert gp_webserver.GreenPowerFeed.pairing_model() is None


@pytest.mark.parametrize("body", [
    b"{not json",
    [240],
    {"Model": "GreenPower-OnOff"},
    {"Duration": "240"},
    {"Duration": True},
    {"Duration": 255},
    {"Duration": -1},
    {"Duration": 240, "Model": "No-Such-Type"},
])
def test_put_refuses_a_bad_request(gp_webserver, body):
    response, payload = put_pairing(gp_webserver, body)

    assert response["Status"] == "400 BAD REQUEST"
    assert "BE_Error" in payload
    gp_webserver.ControllerLink.sendData.assert_not_called()


def test_put_needs_zigpy(gp_webserver):
    gp_webserver.zigbee_communication = "native"

    response, _ = put_pairing(gp_webserver, {"Duration": 240})

    assert response["Status"] == "400 BAD REQUEST"
    gp_webserver.ControllerLink.sendData.assert_not_called()


def test_models_list(gp_webserver):
    from Classes.WebServer.rest_GreenPower import rest_zgp_models

    payload = json.loads(rest_zgp_models(gp_webserver, "GET", None, [])["Data"])

    assert [m["Name"] for m in payload][:2] == ["GreenPower-OnOff", "GreenPower-OnOff-Dim"]
    assert payload[1]["Widgets"] == ["GenericLvlControl"]
