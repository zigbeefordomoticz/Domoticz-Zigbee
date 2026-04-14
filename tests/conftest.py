"""
Shared fixtures and module stubs for Z4D decoder tests.

Stubs are installed in a session-scoped autouse fixture — NOT at module level.
This ensures pre-existing test files (test_domoticzAbstractLayer, etc.) can
do their own module-level real imports during pytest collection, before any
fixtures run.  sys.modules.setdefault() guarantees real modules already loaded
at collection time are never overridden.
"""

import sys
import types
from unittest.mock import MagicMock
import pytest


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_stub(name, **attrs):
    """Return a minimal stub module with the given attributes."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


# ─── Stub definitions ─────────────────────────────────────────────────────────

_STUBS = {
    "Modules.tools": dict(
        timeStamped=MagicMock(name="timeStamped"),
        updLQI=MagicMock(name="updLQI"),
        updSQN=MagicMock(name="updSQN"),
        zigpy_plugin_sanity_check=MagicMock(name="zigpy_plugin_sanity_check", return_value=False),
        DeviceExist=MagicMock(name="DeviceExist", return_value=True),
        is_duplicate_sqn=MagicMock(name="is_duplicate_sqn", return_value=False),
        getSaddrfromIEEE=MagicMock(name="getSaddrfromIEEE"),
        loggingMessages=MagicMock(name="loggingMessages"),
        ReArrangeMacCapaBasedOnModel=MagicMock(name="ReArrangeMacCapaBasedOnModel", return_value="8e"),
        decodeMacCapa=MagicMock(name="decodeMacCapa", return_value=[]),
        checkAndStoreAttributeValue=MagicMock(name="checkAndStoreAttributeValue"),
        extract_info_from_8085=MagicMock(name="extract_info_from_8085"),
        get_deviceconf_parameter_value=MagicMock(name="get_deviceconf_parameter_value", return_value=None),
        get_device_config_param=MagicMock(name="get_device_config_param", return_value=None),
        get_isqn_datastruct=MagicMock(name="get_isqn_datastruct"),
        get_list_isqn_attr_datastruct=MagicMock(name="get_list_isqn_attr_datastruct", return_value=[]),
        lookupForIEEE=MagicMock(name="lookupForIEEE"),
        mainPoweredDevice=MagicMock(name="mainPoweredDevice", return_value=False),
        retreive_cmd_payload_from_8002=MagicMock(
            name="retreive_cmd_payload_from_8002",
            return_value=(False, False, "00", "0000", "00", ""),
        ),
        set_request_phase_datastruct=MagicMock(name="set_request_phase_datastruct"),
        set_status_datastruct=MagicMock(name="set_status_datastruct"),
    ),
    "Modules.basicOutputs": dict(
        handle_unknow_device=MagicMock(name="handle_unknow_device"),
        send_default_response=MagicMock(name="send_default_response"),
        getListofAttribute=MagicMock(name="getListofAttribute"),
        setTimeServer=MagicMock(name="setTimeServer"),
    ),
    "Modules.domoTools": dict(
        lastSeenUpdate=MagicMock(name="lastSeenUpdate"),
        timedOutDevice=MagicMock(name="timedOutDevice"),
    ),
    "Modules.domoMaj": dict(
        MajDomoDevice=MagicMock(name="MajDomoDevice"),
    ),
    "Modules.errorCodes": dict(
        DisplayStatusCode=MagicMock(name="DisplayStatusCode", return_value="Success"),
    ),
    "Modules.pairingProcess": dict(
        interview_state_8045=MagicMock(name="interview_state_8045"),
        request_next_Ep=MagicMock(name="request_next_Ep", return_value=False),
    ),
    "Modules.zigbeeController": dict(
        receiveZigateEpList=MagicMock(name="receiveZigateEpList"),
        receiveZigateEpDescriptor=MagicMock(name="receiveZigateEpDescriptor"),
        initLODZigate=MagicMock(name="initLODZigate"),
    ),
    "Modules.deviceAnnoucement": dict(
        device_annoucementv2=MagicMock(name="device_annoucementv2"),
    ),
    "Modules.pluginDbAttributes": dict(
        STORE_CONFIGURE_REPORTING="Configure Reporting",
    ),
    "Modules.domoticzAbstractLayer": dict(
        is_device_ieee_in_domoticz_db=MagicMock(name="is_device_ieee_in_domoticz_db", return_value=False),
    ),
    "Modules.legrand_netatmo": dict(
        rejoin_legrand_reset=MagicMock(name="rejoin_legrand_reset"),
        legrand_motion_8085=MagicMock(name="legrand_motion_8085"),
        legrand_remote_switch_8085=MagicMock(name="legrand_remote_switch_8085"),
        legrand_motion_8095=MagicMock(name="legrand_motion_8095"),
        legrand_remote_switch_8095=MagicMock(name="legrand_remote_switch_8095"),
    ),
    "Modules.zigateConsts": dict(
        ADDRESS_MODE={"short": 2, "ieee": 3, "group": 4},
        ZCL_CLUSTERS_LIST={"0006": "On/Off", "0300": "Color Control"},
        LEGRAND_REMOTE_MOTION=[],
        LEGRAND_REMOTE_SWITCHS=[],
        ZIGBEE_COMMAND_IDENTIFIER={},
    ),
    "Modules.zigbeeVersionTable": dict(
        FIRMWARE_BRANCH={
            "03": "ZiGate", "04": "ZiGate OptiPDM", "05": "ZiGate V2",
            "11": "ZiGate via Zigpy", "20": "Zigpy", "98": "Untested", "99": "Untested",
        },
        set_display_firmware_version=MagicMock(name="set_display_firmware_version"),
    ),
    "Classes.ZigateTransport.sqnMgmt": dict(
        TYPE_APP_ZCL="zcl",
        TYPE_APP_ZDP="zdp",
        sqn_get_internal_sqn_from_app_sqn=MagicMock(name="sqn_get_internal_sqn_from_app_sqn", return_value=1),
        sqn_get_internal_sqn_from_aps_sqn=MagicMock(name="sqn_get_internal_sqn_from_aps_sqn", return_value=1),
    ),
    "Zigbee.zdpCommands": dict(
        zdp_NWK_address_request=MagicMock(name="zdp_NWK_address_request"),
    ),
    "Modules.sendZigateCommand": dict(
        raw_APS_request=MagicMock(name="raw_APS_request"),
    ),
    "Modules.networkmap": dict(),
    "Modules.networkenergy": dict(),
    "Modules.OTA": dict(
        OTA_process_block_request=MagicMock(name="OTA_process_block_request"),
        OTA_process_page_request=MagicMock(name="OTA_process_page_request"),
        OTA_upgrade_end_request=MagicMock(name="OTA_upgrade_end_request"),
    ),
    "Modules.ikeaTradfri": dict(
        ikea_motion_sensor_8095=MagicMock(name="ikea_motion_sensor_8095"),
        ikea_remote_control_80A7=MagicMock(name="ikea_remote_control_80A7"),
        ikea_remote_control_8085=MagicMock(name="ikea_remote_control_8085"),
        ikea_remote_control_8095=MagicMock(name="ikea_remote_control_8095"),
        ikea_remote_switch_8085=MagicMock(name="ikea_remote_switch_8085"),
        ikea_remote_switch_8095=MagicMock(name="ikea_remote_switch_8095"),
        ikea_remoteN2_control_80A7=MagicMock(name="ikea_remoteN2_control_80A7"),
        ikea_wireless_dimer_8085=MagicMock(name="ikea_wireless_dimer_8085"),
    ),
    "Modules.lumi": dict(
        AqaraOppleDecoding=MagicMock(name="AqaraOppleDecoding"),
    ),
    "Modules.callback": dict(
        callbackDeviceAwake=MagicMock(name="callbackDeviceAwake"),
    ),
    "Modules.inRawAps": dict(
        inRawAps=MagicMock(name="inRawAps"),
    ),
    "Modules.zb_tables_management": dict(
        mgmt_rtg_rsp=MagicMock(name="mgmt_rtg_rsp"),
        store_NwkAddr_Associated_Devices=MagicMock(name="store_NwkAddr_Associated_Devices"),
    ),
    "Modules.basicInputs": dict(
        read_attribute_response=MagicMock(name="read_attribute_response"),
    ),
    "Modules.livolo": dict(
        livolo_read_attribute_request=MagicMock(name="livolo_read_attribute_request"),
    ),
    "Modules.schneider_wiser": dict(
        wiser_read_attribute_request=MagicMock(name="wiser_read_attribute_request"),
        schneider_multiple_read_attribute_request=MagicMock(name="schneider_multiple_read_attribute_request"),
    ),
    "Modules.timeServer": dict(
        timeserver_read_attribute_request=MagicMock(name="timeserver_read_attribute_request"),
        timeserver_multiple_read_attribute_request=MagicMock(name="timeserver_multiple_read_attribute_request"),
    ),
    "Modules.pluzzy": dict(
        pluzzyDecode8102=MagicMock(name="pluzzyDecode8102"),
    ),
    "Modules.readClusters": dict(
        ReadCluster=MagicMock(name="ReadCluster"),
    ),
}


# ─── Session fixture: install stubs at execution time, not collection time ────

@pytest.fixture(scope="session", autouse=True)
def _z4d_stubs():
    """
    Install module stubs before any test runs.

    Placing this in a session fixture (not at module level) means pytest's
    collection phase runs first.  Any test file that does a module-level
    ``import Modules.xyz`` (e.g. test_domoticzAbstractLayer.py) will have
    loaded the real module into sys.modules before we touch anything.
    setdefault() then leaves those real modules alone while filling in
    stubs for everything the decoder tests need.
    """
    for name, attrs in _STUBS.items():
        sys.modules.setdefault(name, _make_stub(name, **attrs))


# ─── Shared plugin fixture ────────────────────────────────────────────────────

@pytest.fixture
def plugin():
    """Fresh mock plugin object for every decoder test."""
    p = MagicMock()
    p.log = MagicMock()
    p.log.logging = MagicMock()
    p.ListOfDevices = {}
    p.IEEE2NWK = {}
    p.configureReporting = MagicMock()
    p.groupmgt = MagicMock()
    p.iaszonemgt = MagicMock()
    p.networkmap = MagicMock()
    p.ControllerLink = MagicMock()
    p.pluginconf = MagicMock()
    p.pluginconf.pluginConf = {
        "coordinatorCmd": False,
        "deviceOffWhenTimeOut": False,
        "LQIthreshold": 0,
        "channel": "15",
        "LegrandCompatibilityMode": False,
    }
    p.ControllerIEEE = ""
    p.ControllerNWKID = ""
    p.ControllerData = {}
    p.pluginParameters = {}
    p.startZigateNeeded = False
    p.currentChannel = 15
    p.internalError = 0
    p.ErasePDMDone = False
    p.Ping = {}
    p.permitTojoin = {"Duration": 0, "Starttime": 0}
    p.adminWidgets = MagicMock()
    p.webserver = None
    p.zigbee_communication = "native"
    p.HardwareID = 1
    p.FirmwareBranch = "03"
    p.FirmwareMajorVersion = "03"
    p.FirmwareVersion = "031d"
    p.ZiGateModel = 1
    p.PDMready = False
    p.PluzzyFirmware = False
    p.statistics = MagicMock()
    p.statistics._clusterOK = 0
    p.OTA = None
    return p
