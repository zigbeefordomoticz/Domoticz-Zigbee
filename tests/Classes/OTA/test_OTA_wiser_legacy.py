"""
test_OTA_wiser_legacy.py
~~~~~~~~~~~~~~~~~~~~~~~~
Schneider Electric Wiser Heat legacy devices (Model "EH-ZB-*") take only the
firmware files Schneider's OTADEF.xml lists for their model, and those files go
to no other device.

The legacy files share manufacturer code 0x105E with the current Wiser range,
and the image type does not tell one model from another. The images below are
synthetic and use the worst case: every stack (SNP) file has the same image
type, the HACT and LMACT application files have the same image type, and a
current Wiser file uses that image type too.

Run with:
    python -m pytest tests/Classes/OTA/test_OTA_wiser_legacy.py -v
"""

import pytest
from ota_builders import DEVICE_EP, DEVICE_NWKID, make_ota_image, query_next_image

SCHNEIDER = 0x105E
SNP_TYPE = 0x0001
APP_TYPE = 0x0002
NO_IMAGE_AVAILABLE = 0x98

SNP_HACT = "EH_ZB_SNP_R_04_01_14_HACT.zigbee"
SNP_LACT = "EH_ZB_SNP_R_04_01_14_LACT.zigbee"
APP_HACT = "EH_HAC_R_04_01_02.zigbee"
APP_LACT = "EH_LAC_R_04_01_02.zigbee"
BMS_APP = "CTC.R.03.00.10.zigbee"
CURRENT_WISER = "105E-0002-00050000.zigbee"

# Payloads tell the files apart in the image size
FILES = {
    SNP_HACT: (SNP_TYPE, 0x00040114, 100),
    SNP_LACT: (SNP_TYPE, 0x00040114, 110),
    APP_HACT: (APP_TYPE, 0x00040102, 120),
    APP_LACT: (APP_TYPE, 0x00040102, 130),
    BMS_APP: (APP_TYPE, 0x00030010, 140),
    CURRENT_WISER: (APP_TYPE, 0x00050000, 150),
}


@pytest.fixture
def wiser_files(ota, install_image):
    for file_name, (image_type, version, size) in FILES.items():
        install_image("Schneider", file_name, make_ota_image(manuf_code=SCHNEIDER, image_type=image_type, version=version, payload=b"\x55" * size))
    return ota.ListOfImages["Brands"]["Schneider"]


def _model(ota, model, nwkid=DEVICE_NWKID):
    ota.ListOfDevices[nwkid]["Model"] = model


def _query(ota, image_type, version=0x00010000, nwkid=DEVICE_NWKID):
    ota.query_next_image_request(nwkid, DEVICE_EP, "2a", query_next_image(SCHNEIDER, image_type, version))


def _offered(radio, images):
    """File name offered by the single Query Next Image Response, or None for NO_IMAGE_AVAILABLE."""
    radio.zcl_raw_ota_query_next_image_response.assert_called_once()
    args = radio.zcl_raw_ota_query_next_image_response.call_args.args[5:]
    if args == (NO_IMAGE_AVAILABLE,):
        return None
    status, manuf, image_type, version, size = args
    assert (status, manuf) == (0x00, SCHNEIDER)
    return next(name for name, image in images.items() if (image["ImageType"], image["originalVersion"], image["intSize"]) == (image_type, version, size))


# ─── helpers ──────────────────────────────────────────────────────────────────

def test_otadef_table(ota_module):
    files = ota_module.WISER_LEGACY_OTA_FILES
    assert files["EH-ZB-RTS"] == ("EH_ZB_SNP_R_04_01_14_RTS.zigbee", "EH_RTS_R_04_01_00.zigbee")
    assert files["EH-ZB-SPD-V2"] == ("EH_PZA_R_03_02_64.zigbee", "EH_PMA_R_03_00_26.zigbee")
    assert files["EH-ZB-BMS"] == ("EH_ZB_SNP_R_04_01_14_BMS.zigbee", "CTC.R.03.00.10.zigbee")
    assert files["EH-ZB-UIO"] == ("EH_UIO_R_04_01_18.zigbee",)
    assert "EH-ZB-NANO" not in files


@pytest.mark.parametrize("file_name, legacy", [
    ("EH_HAC_R_04_01_02.zigbee", True),
    ("eh_hac_r_04_01_02.zigbee", True),
    ("EH_UNLISTED_R_05_00_00.zigbee", True),
    ("CTC.R.03.00.10.zigbee", True),
    ("105E-0002-00050000.zigbee", False),
    ("bulb.ota", False),
])
def test_is_wiser_legacy_file(ota_module, file_name, legacy):
    assert ota_module.is_wiser_legacy_file(file_name) is legacy


# ─── folder scan ──────────────────────────────────────────────────────────────

def test_every_legacy_file_is_kept_though_they_share_the_image_type(wiser_files):
    assert set(wiser_files) == set(FILES)


def test_two_current_files_of_one_type_still_keep_the_highest_version(ota, install_image, wiser_files):
    install_image("Schneider", "105E-0002-00060000.zigbee", make_ota_image(manuf_code=SCHNEIDER, image_type=APP_TYPE, version=0x00060000))

    loaded = set(ota.ListOfImages["Brands"]["Schneider"])
    assert "105E-0002-00060000.zigbee" in loaded
    assert CURRENT_WISER not in loaded
    assert {SNP_HACT, SNP_LACT, APP_HACT, APP_LACT, BMS_APP} <= loaded


# ─── autoServeOTA ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("model, image_type, expected", [
    ("EH-ZB-HACT", SNP_TYPE, SNP_HACT),
    ("EH-ZB-HACT", APP_TYPE, APP_HACT),
    ("EH-ZB-LMACT", SNP_TYPE, SNP_LACT),
    ("EH-ZB-LMACT", APP_TYPE, APP_LACT),
    ("EH-ZB-BMS", APP_TYPE, BMS_APP),
    ("CCTFR6400", APP_TYPE, CURRENT_WISER),
    ("CCTFR6400", SNP_TYPE, None),
    ("EH-ZB-RTS", APP_TYPE, None),          # its files are not in the folder
    ("EH-ZB-FUTURE", APP_TYPE, None),       # EH-ZB model without a file in OTADEF.xml
    ("", APP_TYPE, None),                   # model not known yet
])
def test_auto_serve_offers_only_the_files_of_the_model(ota, radio, request_of, wiser_files, model, image_type, expected):
    ota.pluginconf.pluginConf["autoServeOTA"] = True
    _model(ota, model)

    _query(ota, image_type)

    assert _offered(radio, wiser_files) == expected
    request = request_of(DEVICE_NWKID)
    assert (request["FileName"] if request else None) == expected


def test_legacy_device_already_up_to_date_is_not_offered_a_current_wiser_file(ota, radio, wiser_files):
    ota.pluginconf.pluginConf["autoServeOTA"] = True
    _model(ota, "EH-ZB-HACT")

    _query(ota, APP_TYPE, version=FILES[APP_HACT][1])

    assert _offered(radio, wiser_files) is None


def test_unlisted_eh_file_is_offered_to_no_device(ota, radio, install_image):
    install_image("Schneider", "EH_UNLISTED_R_05_00_00.zigbee", make_ota_image(manuf_code=SCHNEIDER, image_type=APP_TYPE, version=0x00050000))
    ota.pluginconf.pluginConf["autoServeOTA"] = True

    for model in ("EH-ZB-HACT", "CCTFR6400"):
        radio.zcl_raw_ota_query_next_image_response.reset_mock()
        _model(ota, model)
        _query(ota, APP_TYPE)
        assert _offered(radio, ota.ListOfImages["Brands"]["Schneider"]) is None


def test_other_brands_still_served_to_a_device_without_model(ota, radio, install_image):
    image = install_image("Ikea", "bulb.ota", make_ota_image(manuf_code=0x117C, image_type=0x2203, version=0x01020304))
    ota.pluginconf.pluginConf["autoServeOTA"] = True

    ota.query_next_image_request(DEVICE_NWKID, DEVICE_EP, "2a", query_next_image(0x117C, 0x2203, 0x01000000))

    assert radio.zcl_raw_ota_query_next_image_response.call_args.args[5:] == (0x00, 0x117C, 0x2203, 0x01020304, image["intSize"])


# ─── WebUI pick ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("model, file_name, status", [
    ("EH-ZB-HACT", APP_HACT, "Queued"),
    ("EH-ZB-HACT", APP_LACT, "Rejected"),
    ("EH-ZB-HACT", CURRENT_WISER, "Rejected"),
    ("EH-ZB-BMS", BMS_APP, "Queued"),
    ("CCTFR6400", CURRENT_WISER, "Queued"),
    ("CCTFR6400", APP_HACT, "Rejected"),
    ("CCTFR6400", BMS_APP, "Rejected"),
    ("", CURRENT_WISER, "Rejected"),
])
def test_webui_pick_of_a_file_for_another_model_is_rejected(ota_module, ota, wiser_files, model, file_name, status):
    _model(ota, model)

    result = ota_module.firmware_update(ota, "Schneider", file_name, DEVICE_NWKID, DEVICE_EP)

    assert result["Status"] == status
    if status == "Rejected":
        assert result["Reason"] == "This firmware is not for this device model"
        assert ota.ota_requests == {}


def test_webui_pick_serves_the_picked_file(ota_module, ota, radio, wiser_files):
    _model(ota, "EH-ZB-LMACT")
    assert ota_module.firmware_update(ota, "Schneider", APP_LACT, DEVICE_NWKID, DEVICE_EP)["Status"] == "Queued"

    _query(ota, APP_TYPE)

    assert _offered(radio, wiser_files) == APP_LACT


# ─── ZiGate: header of the request's file ─────────────────────────────────────

def test_zigate_gets_the_header_of_the_requested_file(ota_module, ota, wiser_files, monkeypatch):
    loaded = []
    monkeypatch.setattr(ota_module, "_update_image_loaded_info", lambda self, header, force_version: loaded.append(header))
    _model(ota, "EH-ZB-LMACT")

    ota_module.firmware_update(ota, "Schneider", APP_LACT, DEVICE_NWKID, DEVICE_EP)

    assert loaded and loaded[-1] is wiser_files[APP_LACT]["Decoded Header"]


# ─── REST: files a device is never offered ────────────────────────────────────

@pytest.mark.parametrize("model, excluded", [
    ("EH-ZB-HACT", sorted(set(FILES) - {SNP_HACT, APP_HACT})),
    ("EH-ZB-BMS", sorted(set(FILES) - {BMS_APP})),
    ("CCTFR6400", sorted({SNP_HACT, SNP_LACT, APP_HACT, APP_LACT, BMS_APP})),
    ("", sorted(FILES)),
])
def test_restapi_excluded_files(ota, wiser_files, model, excluded):
    _model(ota, model)

    assert ota.restapi_excluded_files(DEVICE_NWKID, "105e") == excluded


def test_restapi_excluded_files_of_another_manufacturer_code(ota, wiser_files):
    _model(ota, "EH-ZB-HACT")

    assert ota.restapi_excluded_files(DEVICE_NWKID, "117c") == []
    assert ota.restapi_excluded_files(DEVICE_NWKID, "not hex") == []
