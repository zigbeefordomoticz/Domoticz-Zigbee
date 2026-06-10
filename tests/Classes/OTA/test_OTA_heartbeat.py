"""
test_OTA_heartbeat.py
~~~~~~~~~~~~~~~~~~~~
Unit tests for the OTA heartbeat state machine.

Regression test for the infinite Image Notify loop: when a device never
engages with the advertised firmware (e.g. it queries for an image type we
do not have), the heartbeat must stop re-notifying and reset the OTA state
after OTA_MAX_NOTIFY_RETRY attempts, instead of re-advertising forever
(which also kept refreshing NotifiedTimeStamp so the timeout never fired).

Classes.OTA is imported inside a fixture, against locally stubbed
dependencies, and sys.modules is restored on teardown so neither the
conftest stubs nor the other test modules are disturbed.

Run with:
    python -m pytest tests/Classes/test_OTA_heartbeat.py -v
"""

import importlib
import sys
import time
import types
from unittest.mock import MagicMock

import pytest


def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


# Direct imports of Classes/OTA.py, stubbed so the import does not drag in
# the Domoticz framework.
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


@pytest.fixture
def ota(ota_module):
    """OTAManagement instance without running __init__ (no radio, no I/O)."""
    o = object.__new__(ota_module.OTAManagement)
    o.log = MagicMock()
    o.ControllerLink = MagicMock()
    o.pluginconf = MagicMock()
    o.pluginconf.pluginConf = {}
    o.ImageLoaded = {
        "ImageVersion": 0x004445FF,
        "image_type": 0x0011,
        "manufacturer_code": 0x1021,
        "LoadedTimeStamp": time.time(),
        "Notified": True,
        "NotifiedTimeStamp": time.time(),
    }
    o.ListInUpdate = {
        "FileName": "fake.zigbee",
        "Status": None,
        "intImageType": 0x0011,
        "intImageVersion": 0x004445FF,
        "ImageVersion": "004445ff",
        "Process": None,
        "NwkId": "1234",
        "Ep": "01",
        "intManufCode": 0x1021,
        "LastBlockSent": 0,
        "AuthorizedForUpdate": ["1234"],
        "Retry": 0,
    }
    return o


def test_notification_retries_are_bounded(ota_module, ota):
    """The state machine must reset after OTA_MAX_NOTIFY_RETRY notifications."""
    max_retry = ota_module.OTA_MAX_NOTIFY_RETRY

    for iteration in range(1, max_retry + 5):
        ota.heartbeat()
        if ota.ListInUpdate["NwkId"] is None:
            break
    else:
        pytest.fail("OTA state machine never reset: infinite Image Notify loop")

    assert iteration == max_retry
    # Image Notify goes out via ControllerLink.sendData on each retry
    assert ota.ControllerLink.sendData.call_count == max_retry
    # State fully cleared so a new update can be started without a plugin restart
    assert ota.ListInUpdate["Status"] is None
    assert ota.ListInUpdate["Retry"] == 0
    assert "1234" not in ota.ListInUpdate["AuthorizedForUpdate"]


def test_no_reset_while_transfer_in_progress(ota_module, ota):
    """A healthy ongoing transfer must not be reset by the notify timeout."""
    # Once blocks flow, prepare_and_send_block/update_list_in_update set this state
    ota.ListInUpdate["Status"] = "Transfer Progress"
    ota.ListInUpdate["LastBlockSent"] = time.time()
    ota.ListInUpdate["Retry"] = 0
    ota.ImageLoaded["NotifiedTimeStamp"] = 0

    for _ in range(ota_module.OTA_MAX_NOTIFY_RETRY + 5):
        ota.heartbeat()

    assert ota.ListInUpdate["NwkId"] == "1234"
    assert ota.ListInUpdate["Status"] == "Transfer Progress"
    ota.ControllerLink.sendData.assert_not_called()


def test_idle_heartbeat_does_nothing(ota):
    ota.ListInUpdate["NwkId"] = None

    ota.heartbeat()

    ota.ControllerLink.sendData.assert_not_called()
