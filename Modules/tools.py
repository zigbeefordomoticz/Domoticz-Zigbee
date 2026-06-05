#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
    Module : tools.py

    Backward-compatible re-export shim.
    All functions have been moved to focused sub-modules.
    This file re-exports everything so that existing callers continue to work.
"""

# Primitives
from Modules.tools_primitives import (  # noqa: F401
    HEX_DIGIT,
    INT_DIGIT,
    Hex_Format,
    hex_to_rgb,
    hex_to_xy,
    is_hex,
    is_int,
    returnlen,
    rgb_to_hex,
    rgb_to_hsl,
    rgb_to_xy,
    str_round,
    to_little_endian,
    twos_complement,
    voltage2batteryP,
    xy_to_rgb,
)

# Device lookup
from Modules.tools_device_lookup import (  # noqa: F401
    DeviceExist,
    IEEEExist,
    NwkIdExist,
    getClusterListforEP,
    getEPforClusterType,
    getEpForCluster,
    getListOfEpForCluster,
    getSaddrfromIEEE,
    lookupForIEEE,
    lookupForParentDevice,
)

# Device lifecycle
from Modules.tools_device_lifecycle import (  # noqa: F401
    chk_and_update_IEEE_NWKID,
    initialize_device_record,
    is_bind_ep,
    is_fake_ep,
    loggingMessages,
    reconnectNWkDevice,
    removeDeviceInList,
    removeNwkInList,
    try_to_reconnect_via_neighbours,
    zigpy_plugin_sanity_check,
)

# SQN / attribute helpers
from Modules.tools_sqn import (  # noqa: F401
    checkAndStoreAttributeValue,
    checkAttribute,
    checkValidValue,
    get_and_inc_TUYA_POLLING_SQN,
    get_and_inc_ZCL_SQN,
    get_and_inc_ZDP_SQN,
    get_and_increment_generic_SQN,
    getAttributeValue,
    is_duplicate_sqn,
    store_battery_percentage_time_stamp,
    store_battery_voltage_time_stamp,
    timeStamped,
    upd_RSSI,
    updLQI,
    updSQN,
)

# FCF helpers
from Modules.tools_fcf import (  # noqa: F401
    build_fcf,
    decode_fcf,
    disable_default_response,
    extract_info_from_8085,
    fcf_direction,
    frame_type,
    is_direction_to_client,
    is_direction_to_server,
    is_globalcommand,
    is_manufspecific_8002_payload,
    retreive_cmd_payload_from_8002,
)

# Data structure helpers
from Modules.tools_datastruct import (  # noqa: F401
    check_datastruct,
    clean_old_datastruct,
    get_cluster_attribute_value,
    get_isqn_datastruct,
    get_list_isqn_attr_datastruct,
    get_list_isqn_int_attr_datastruct,
    get_list_waiting_request_datastruct,
    get_request_datastruct,
    get_status_datastruct,
    is_attr_unvalid_datastruct,
    is_time_to_perform_work,
    reset_attr_datastruct,
    reset_cluster_datastruct,
    reset_device_attribute,
    set_isqn_datastruct,
    set_request_datastruct,
    set_request_phase_datastruct,
    set_status_datastruct,
    set_timestamp_datastruct,
)

# MAC capability helpers
from Modules.tools_mac_capa import (  # noqa: F401
    ReArrangeMacCapaBasedOnModel,
    decodeMacCapa,
    device_listening_on_iddle,
    full_function_device,
    is_ack_tobe_disabled,
    mainPoweredDevice,
)

# Domoticz version helpers
from Modules.tools_domoticz import (  # noqa: F401
    get_device_config_param,
    is_domoticz_2023,
    is_domoticz_2024,
    is_domoticz_above_2022,
    is_domoticz_above_2022_2,
    is_domoticz_above_2023,
    is_domoticz_above_2024,
    is_domoticz_below_2020,
    is_domoticz_below_2021,
    is_domoticz_below_2022,
    is_domoticz_below_2023,
    is_domoticz_below_2024,
    is_domoticz_db_available,
    is_domoticz_latest_typename,
    is_domoticz_new_API,
    is_domoticz_new_blind,
    is_domoticz_touch,
    is_domoticz_update_SuppressTriggers,
)

# Model/config helpers
from Modules.tools_model import (  # noqa: F401
    build_list_of_device_model,
    deviceconf_device,
    get_device_nickname,
    get_deviceconf_parameter_value,
    getListofType,
    unknown_device_model,
)

# File/utility helpers
from Modules.tools_files import (  # noqa: F401
    helper_copyfile,
    helper_versionFile,
    how_many_devices,
    night_shift_jobs,
    print_stack,
)

MAX_ROLLING_LQI_LENGTH = 10