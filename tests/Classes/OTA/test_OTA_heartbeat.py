"""
test_OTA_heartbeat.py
~~~~~~~~~~~~~~~~~~~~
Unit tests for the OTA heartbeat state machine.

Regression test for the infinite Image Notify loop: when a device never
engages with the advertised firmware (e.g. it queries for an image type we
do not have), the heartbeat must stop re-notifying after
OTA_MAX_NOTIFY_RETRY attempts, instead of re-advertising forever.
The device then gives its transfer slot back (it stays in the queue, see
test_OTA_queue.py).

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_heartbeat.py -v
"""

import time

import pytest
from ota_builders import DEVICE_EP, DEVICE_NWKID, make_ota_image


@pytest.fixture
def notified(ota_module, ota, radio, install_image, request_of):
    install_image("Legrand", "fake.zigbee", make_ota_image(manuf_code=0x1021, image_type=0x0011, version=0x004445FF))
    assert ota_module.firmware_update(ota, "Legrand", "fake.zigbee", DEVICE_NWKID, DEVICE_EP)["Status"] == "Queued"
    radio.zcl_raw_ota_image_notify.reset_mock()
    return request_of(DEVICE_NWKID)


def test_notification_retries_are_bounded(ota_module, ota, radio, notified):
    """The device must give its slot back after OTA_MAX_NOTIFY_RETRY notifications."""
    max_retry = ota_module.OTA_MAX_NOTIFY_RETRY

    for iteration in range(1, max_retry + 5):
        ota.heartbeat()
        if notified["State"] != ota_module.OTA_NOTIFYING:
            break
    else:
        pytest.fail("OTA state machine never gave up: infinite Image Notify loop")

    assert iteration == max_retry
    assert radio.zcl_raw_ota_image_notify.call_count == max_retry
    assert notified["State"] == ota_module.OTA_WAITING
    # Slot given back: a new update can start without a plugin restart
    assert ota_module.active_ota_requests(ota) == []


def test_no_reset_while_transfer_in_progress(ota_module, ota, radio, notified):
    """A healthy ongoing transfer must not be reset by the notify timeout."""
    ota_module.start_transfer(ota, notified)

    for _ in range(ota_module.OTA_MAX_NOTIFY_RETRY + 5):
        notified["LastBlockSent"] = time.time()
        ota.heartbeat()

    assert notified["State"] == ota_module.OTA_TRANSFER
    radio.zcl_raw_ota_image_notify.assert_not_called()


def test_idle_heartbeat_does_nothing(ota, radio):
    ota.heartbeat()

    radio.zcl_raw_ota_image_notify.assert_not_called()
    assert ota.PluginHealth == {}
