"""
Shared fixtures for the Classes.OTA unit tests.

Classes.OTA is imported once per test module against locally stubbed
dependencies (the same stubs the older test_OTA_*.py files declare for
themselves), and sys.modules is restored on teardown so neither the
top-level conftest stubs nor the other test modules are disturbed.

Fixtures:
    ota_module  the imported Classes.OTA module
    radio       fresh mocks for every outbound call of Classes.OTA
                (zcl_raw_*, sendZigateCmd), patched per test
    ota         an OTAManagement built by its real __init__: no internet,
                an empty firmware folder under tmp_path, zigpy (raw) mode,
                and one OTA-capable device "1234" in ListOfDevices
    install_image(brand, filename, image_bytes)
                write a firmware file into the brand's folder and rescan

The frame and firmware-file builders live in ota_builders.py.
"""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest
from ota_builders import DEVICE_EP, DEVICE_IEEE, DEVICE_NWKID


def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


_OTA_DEPS = {
    "Modules.sendZigateCommand": dict(sendZigateCmd=MagicMock(name="sendZigateCmd")),
    "Modules.tools": dict(get_device_nickname=MagicMock(name="get_device_nickname", return_value="Bulb")),
    "Modules.zigateConsts": dict(ADDRESS_MODE={"short": 2, "ieee": 3, "group": 4}, ZIGATE_EP="01"),
    "Zigbee.zclRawCommands": dict(
        zcl_raw_default_response=MagicMock(name="zcl_raw_default_response"),
        zcl_raw_ota_image_block_response_abort=MagicMock(name="zcl_raw_ota_image_block_response_abort"),
        zcl_raw_ota_image_block_response_success=MagicMock(name="zcl_raw_ota_image_block_response_success"),
        zcl_raw_ota_image_notify=MagicMock(name="zcl_raw_ota_image_notify"),
        zcl_raw_ota_query_next_image_response=MagicMock(name="zcl_raw_ota_query_next_image_response"),
        zcl_raw_ota_upgrade_end_response=MagicMock(name="zcl_raw_ota_upgrade_end_response"),
    ),
}

_RADIO_CALLS = (
    "zcl_raw_default_response",
    "zcl_raw_ota_image_block_response_abort",
    "zcl_raw_ota_image_block_response_success",
    "zcl_raw_ota_image_notify",
    "zcl_raw_ota_query_next_image_response",
    "zcl_raw_ota_upgrade_end_response",
    "sendZigateCmd",
)


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
def radio(ota_module, monkeypatch):
    """Fresh mocks for every outbound call, so call counts never leak between tests."""
    mocks = types.SimpleNamespace()
    for name in _RADIO_CALLS:
        mock = MagicMock(name=name)
        monkeypatch.setattr(ota_module, name, mock)
        setattr(mocks, name, mock)
    return mocks


@pytest.fixture
def ota(ota_module, radio, tmp_path):
    pluginconf = MagicMock()
    pluginconf.pluginConf = {
        "pluginOTAFirmware": str(tmp_path / "OTAFirmware"),
        "pluginLogs": str(tmp_path),
        "ControllerInRawMode": True,
        "internetAccess": False,
    }
    list_of_devices = {
        DEVICE_NWKID: {
            "IEEE": DEVICE_IEEE,
            "ZDeviceName": "Bulb",
            "Manufacturer": "117c",
            "Ep": {DEVICE_EP: {"0019": {}}},
        }
    }
    o = ota_module.OTAManagement(
        "zigpy",              # zigbee_communication
        pluginconf,
        {},                   # DeviceConf
        MagicMock(),          # adminWidgets
        MagicMock(),          # ZigateComm
        str(tmp_path),        # HomeDirectory
        1,                    # hardwareID
        {},                   # Devices
        list_of_devices,
        {DEVICE_IEEE: DEVICE_NWKID},
        MagicMock(),          # log
        {},                   # PluginHealth
        MagicMock(),          # readZclClusters
        False,                # internet_available
        False,                # pairing_in_progress
    )
    return o


@pytest.fixture
def install_image(ota, ota_module, tmp_path):
    """Write a firmware file into the folder of `brand` and rescan the firmware folders."""

    def _install(brand, filename, image_bytes, folder=None):
        folder = folder or ota_module.ota_brand_folders(ota_module.OTA_CODES[brand])[0]
        directory = tmp_path / "OTAFirmware" / folder
        directory.mkdir(parents=True, exist_ok=True)
        (directory / filename).write_bytes(image_bytes)
        ota_module.ota_scan_folder(ota)
        return ota.ListOfImages["Brands"][brand].get(filename)

    return _install
