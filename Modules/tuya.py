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
    Module: tuya.py

    Descripti
    on: Tuya specific

"""

import struct
import time
from datetime import datetime, timedelta, timezone

from Modules.basicOutputs import raw_APS_request, write_attribute
from Modules.bindings import bindDevice
from Modules.domoMaj import MajDomoDevice
from Modules.domoTools import Update_Battery_Device
from Modules.tools import (build_fcf, checkAndStoreAttributeValue,
                           get_and_inc_ZCL_SQN,
                           get_device_config_param,
                           get_deviceconf_parameter_value,
                           is_ack_tobe_disabled, updSQN)
from Modules.tuyaConst import (TUYA_MANUF_CODE, TUYA_SMART_DOOR_LOCK_MODEL,
                               TUYA_eTRV_MODEL)
from Modules.tuyaSiren import tuya_siren2_response, tuya_siren_response
from Modules.tuyaTools import (get_next_tuya_transactionId, get_tuya_attribute,
                               store_tuya_attribute, tuya_cmd)
from Modules.tuyaTRV import tuya_eTRV_response
from Modules.tuyaTS011F import tuya_read_cluster_e001
from Modules.tuyaTS0601 import ts0601_response
from Modules.zigateConsts import ZIGATE_EP
from Zigbee.zclDecoders import zcl_raw_default_response


# Tuya TRV Commands
# https://medium.com/@dzegarra/zigbee2mqtt-how-to-add-support-for-a-new-tuya-based-device-part-2-5492707e882d

# Tuya Doc: https://developer.tuya.com/en/docs/iot/access-standard-zigbee?id=Kaiuyf28lqebl


# Data Types:
#   0x00: raw
#   0x01: bool
#   0x02: 4 byte value
#   0x03: string
#   0x04: enum8 ( 0x00-0xff)
#   0x05: bitmap ( 1,2, 4 bytes) as bits


def is_tuya_switch_relay(self, nwkid):
    model = self.ListOfDevices[nwkid].get("Model", "")
    return model in ( "TS0601-switch", "TS0601-2Gangs-switch", "TS0601-Energy", )


def tuya_registration(self, nwkid, ty_data_request=False, parkside=False, tuya_registration_value=None):
    if "Model" not in self.ListOfDevices[nwkid]:
            return
    _ModelName = self.ListOfDevices[nwkid]["Model"]

    self.log.logging("Tuya", "Debug", "tuya_registration - Nwkid: %s Model: %s" % (nwkid, _ModelName))

    # (1) 3 x Write Attribute Cluster 0x0000 - Attribute 0xffde  - DT 0x20  - Value: 0x13 ( 19 Decimal)
    #  It looks like for Lidl Watering switch the Value is 0x0d ( 13 in decimal )
    EPout = "01"
    self.log.logging("Tuya", "Debug", "tuya_registration - Nwkid: %s ----- 0x13 in 0x0000/0xffde" % nwkid)
    if parkside:
        write_attribute(self, nwkid, ZIGATE_EP, EPout, "0000", "0000", "00", "ffde", "20", "0d", ackIsDisabled=False)

    # if tuya_registration_value:
    #     write_attribute(self, nwkid, ZIGATE_EP, EPout, "0000", TUYA_MANUF_CODE, "01", "ffde", "20", "%02x" %tuya_registration_value, ackIsDisabled=False)
    if tuya_registration_value:
        write_attribute(self, nwkid, ZIGATE_EP, EPout, "0000", "0000", "00", "ffde", "20", "%02x" %tuya_registration_value, ackIsDisabled=False)

    elif _ModelName == "TS0216":
        # Heiman like siren
        # Just do the Regitsration
        write_attribute(self, nwkid, ZIGATE_EP, EPout, "0000", TUYA_MANUF_CODE, "01", "ffde", "20", "13", ackIsDisabled=False)
        return
    
    elif _ModelName in ('TS0002-relay-switch', 'TS0601-motion', ):

        write_attribute(self, nwkid, ZIGATE_EP, EPout, "0000", "0000", "00", "ffde", "20", "13", ackIsDisabled=False)
        tuya_cmd_0x0000_0xf0(self, nwkid)
        return
    
    else:
        write_attribute(self, nwkid, ZIGATE_EP, EPout, "0000", "0000", "00", "ffde", "20", "13", ackIsDisabled=False)

    if get_deviceconf_parameter_value(self, self.ListOfDevices[nwkid]["Model"], "TUYA_CMD_FE", return_default=None):
        tuya_cmd_0x0000_0xf0(self, nwkid)
    
    # (3) Cmd 0x03 on Cluster 0xef00  (Cluster Specific) / Tuya TY_DATA_QUERY 
    # (https://developer.tuya.com/en/docs/iot/tuya-zigbee-universal-docking-access-standard?id=K9ik6zvofpzql#subtitle-6-Private%20cluster)
    if ty_data_request:
        tuya_data_request(self, nwkid, EPout)

    # Gw->Zigbee gateway query MCU version
    self.log.logging("Tuya", "Debug", "tuya_registration - Nwkid: %s Request MCU Version Cmd: 10" % nwkid)
    if _ModelName in ( "TS0601-_TZE200_nklqjk62", ):
        payload = "11" + get_and_inc_ZCL_SQN(self, nwkid) + "10" + "000e"
    else:
        payload = "11" + get_and_inc_ZCL_SQN(self, nwkid) + "10" + "0002"
    raw_APS_request( self, nwkid, EPout, "ef00", "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=is_ack_tobe_disabled(self, nwkid), )


def tuya_cmd_ts004F(self, NwkId, mode):
    TS004F_MODE = {
        'Scene': 0x01,   # Scene controller
        'Dimmer': 0x00,  # Remote dimming
    }
    # By default set to 0x00
    if mode not in TS004F_MODE:
        return
    
    write_attribute(self, NwkId, ZIGATE_EP, "01", "0006", "0000", "00", "8004", "30", '%02x' %TS004F_MODE[ mode ], ackIsDisabled=False)
    
    ieee = self.ListOfDevices[ NwkId ]['IEEE']
    cluster = "0006"
    bindDevice(self, ieee, "01", cluster, destaddr=None, destep="01")
    bindDevice(self, ieee, "02", cluster, destaddr=None, destep="01")
    bindDevice(self, ieee, "03", cluster, destaddr=None, destep="01")
    bindDevice(self, ieee, "04", cluster, destaddr=None, destep="01")


def tuya_cmd_0x0000_0xf0(self, NwkId):
    # Seen at pairing of a WGH-JLCZ02 / TS011F and TS0201 and TS0601 (MOES BRT-100)

    payload = "11" + get_and_inc_ZCL_SQN(self, NwkId) + "fe"
    raw_APS_request( self, NwkId, '01', "0000", "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=is_ack_tobe_disabled(self, NwkId), )
    self.log.logging("Tuya", "Debug", "tuya_cmd_0x0000_0xf0 - Nwkid: %s reset device Cmd: fe" % NwkId)


def tuya_polling_control(self, Nwkid, WidgetType, Level):
    # Mapping Level to Polling modes
    polling_modes = {
        "PollingControl": {
            0: "Off",
            10: "Slow Polling",
            20: "Fast Polling",
        },
        "PollingControlV2": {
            0: "Off",
            10: "2/day",
            20: "20/day",
            30: "96/day",
            40: "Fast Polling",
        }
    }

    self.log.logging("Tuya", "Log", f"tuya_polling_control - Nwkid: {Nwkid}/01 Level {Level}")

    # Set default Tuya device info and polling mode
    tuya_device_info = self.ListOfDevices.setdefault(Nwkid, {}).setdefault("Tuya", {})
    if WidgetType not in polling_modes:
        self.log.logging("Tuya", "Error", f"tuya_polling_control - Unexpected WidgetType {WidgetType} !!!")
        return

    tuya_device_info["Polling"] = polling_modes[ WidgetType ].get(Level, tuya_device_info.get("Polling", "Normal Polling"))

    self.log.logging("Tuya", "Log", f"tuya_polling_control - Nwkid: {Nwkid}/01 Polling Mode {tuya_device_info['Polling']}")


def tuya_polling_values(self, nwkid, device_model, tuya_device_info):
    # This is based on command 0x03, which query ALL datapoint
    tuya_data_query = get_deviceconf_parameter_value(self, device_model, "TUYA_DATA_REQUEST", return_default=0)
    # Retrieve the polling interval configuration for TUYA_DATA_REQUEST_POLLING which query only the data point which have changed
    tuya_data_request_polling = get_deviceconf_parameter_value(self, device_model, "TUYA_DATA_REQUEST_POLLING", return_default=0)

    if not tuya_data_query and not tuya_data_request_polling:
        return 0, 0, 0, 0, 0

    # 3 consecutives polling by default
    tuya_data_request_polling_additional = get_deviceconf_parameter_value(self, device_model, "TUYA_DATA_REQUEST_POLLING_ADDITIONAL", return_default=3)

    # Each consecutive polling must be separated by 15s by default
    tuya_elapse_time_consecutive_polling = get_deviceconf_parameter_value(self, device_model, "TUYA_DATA_REQUEST_POLLING_CONSECUTIVE_ELAPSE", return_default=15)

    additional_polls = tuya_device_info.get("AdditionalPolls", tuya_data_request_polling_additional)

    polling_status = tuya_device_info.setdefault("Polling", "Off")

    current_battery_level = get_tuya_attribute(self, nwkid, "Battery")
    if isinstance(current_battery_level, str) and current_battery_level.isdigit():
        current_battery_level = int(current_battery_level)

    # Usall default is 300s ( 5 minutes )
    if current_battery_level and current_battery_level < 30:
        # TODO needs to update Widget
        polling_status = "2/day"

    elif current_battery_level and current_battery_level < 50:
        # TODO needs to update Widget
        polling_status = "20/day"

    # Polling methods
    if polling_status == "Off":
        # No polling , just exit
        return 0, 0, 0, 0, 0

    elif polling_status == "Fast Polling":
        # Force polling to every 15s
        tuya_data_request_polling = 10
        tuya_data_query = 60  # A query ( 0x03 ) every minutes
        tuya_data_request_polling_additional = 0
        tuya_elapse_time_consecutive_polling = 5

    elif polling_status == "2/day":
        #  2/jour  -> 43200 secondes ( 12 heures)
        tuya_data_request_polling = 43200
        tuya_data_query = 43200  # A query ( 0x03 ) every minutes
        tuya_data_request_polling_additional = 0
        tuya_elapse_time_consecutive_polling = 5

    elif polling_status == "20/day":
        # 20/jours ->  4320 secondes ( 1h 12 minutes)
        tuya_data_request_polling = 4320
        tuya_data_query = 4320  # A query ( 0x03 ) every minutes
        tuya_data_request_polling_additional = 0
        tuya_elapse_time_consecutive_polling = 5

    elif polling_status == "96/day":
        # 96/jour  ->   900 secondes ( 15 minutes)
        tuya_data_request_polling = 900
        tuya_data_query = 3600  # A query ( 0x03 ) every minutes
        tuya_data_request_polling_additional = 0
        tuya_elapse_time_consecutive_polling = 5

    self.log.logging("Tuya", "Debug", f"tuya_polling - Nwkid: {nwkid}/01 tuya_data_request_polling {tuya_data_request_polling}")
    self.log.logging("Tuya", "Debug", f"tuya_polling - Nwkid: {nwkid}/01 tuya_data_query {tuya_data_query}")
    self.log.logging("Tuya", "Debug", f"tuya_polling - Nwkid: {nwkid}/01 tuya_data_request_polling_additional {tuya_data_request_polling_additional}")
    self.log.logging("Tuya", "Debug", f"tuya_polling - Nwkid: {nwkid}/01 tuya_elapse_time_consecutive_polling {tuya_elapse_time_consecutive_polling}")

    return tuya_data_query, tuya_data_request_polling, tuya_data_request_polling_additional, tuya_elapse_time_consecutive_polling, additional_polls


def tuya_polling(self, nwkid):
    """Some Tuya devices, requirea specific polling"""

    device_model = self.ListOfDevices.get(nwkid, {}).get("Model")
    if device_model is None:
        return False

    # Retrieve the device information
    tuya_device_info = self.ListOfDevices.setdefault(nwkid, {}).setdefault("Tuya", {})

    tuya_data_query, tuya_data_request_polling, tuya_data_request_polling_additional, tuya_elapse_time_consecutive_polling,additional_polls = tuya_polling_values(self, nwkid, device_model, tuya_device_info)

    if not tuya_data_request_polling and not tuya_data_query:
        return False

    self.log.logging("Tuya", "Debug", f"tuya_polling - Nwkid: {nwkid}/01 AdditionalPolls {additional_polls}")

    if tuya_data_query and should_poll(self, nwkid, tuya_device_info, "LastTuyaDataQuery", polling_interval=tuya_data_query):
        self.log.logging("Tuya", "Debug", f"tuya_polling - tuya_data_request 0x03 Nwkid: {nwkid}/01 time for polling")
        tuya_data_request(self, nwkid, "01")
        return True

    if tuya_data_request_polling and should_poll(self, nwkid, tuya_device_info, "LastTuyaDataRequest", polling_interval=tuya_data_request_polling, additional_polls=additional_polls, tuya_data_request_polling_additional=tuya_data_request_polling_additional, tuya_elapse_time_consecutive_polling=tuya_elapse_time_consecutive_polling):
        # If the current time is greater than or equal to the next polling time, it will proceed with polling
        self.log.logging("Tuya", "Log", f"tuya_polling - tuya_data_request_poll 0x00 dp 69 dt 02 - Nwkid: {nwkid}/01 time for polling with {additional_polls}")
        tuya_data_request_poll(self, nwkid, "01")
        return True

    if get_tuya_attribute(self, nwkid, "backlight_level") not in ( 0, "00000000"):
        self.log.logging("Tuya", "Debug", "tuya_polling - backlight_level: %s" %get_tuya_attribute(self, nwkid, "backlight_level"))
        tuya_data_request_end_poll(self, nwkid, "01")

    # No polling done
    return False


def should_poll(self, nwkid, tuya_device_info, tuya_last_poll_attribute, polling_interval, additional_polls=0, tuya_data_request_polling_additional=0, tuya_elapse_time_consecutive_polling=15):
    """" Check if it is time for a poll. Because it is time, or because we have additional poll to be made."""

    # Log the polling interval value
    self.log.logging("Tuya", "Debug", f"should_poll - Nwkid: {nwkid}/01 tuya_data_request_polling {polling_interval} additional_polls: {additional_polls} tuya_data_request_polling_additional: {tuya_data_request_polling_additional} tuya_elapse_time_consecutive_polling: {tuya_elapse_time_consecutive_polling}")

    # Retrieve the last polling time and additional polls
    last_poll_time = tuya_device_info.get(tuya_last_poll_attribute, 0)

    # Calculate the next polling time
    next_poll_time = last_poll_time + polling_interval
    consecutive_elapse_time = last_poll_time + tuya_elapse_time_consecutive_polling
    
    # Get the current time
    current_time = int(time.time())

    # Log the last polling time and the next polling time for comparison
    self.log.logging("Tuya", "Debug", f"should_poll - Nwkid: {nwkid}/01 device_last_poll current time {current_time}")
    self.log.logging("Tuya", "Debug", f"             - Nwkid: {nwkid}/01 device_last_poll last_poll_time: {last_poll_time}")
    self.log.logging("Tuya", "Debug", f"             - Nwkid: {nwkid}/01 tuya_data_request_polling next_poll_time: {next_poll_time}")
    self.log.logging("Tuya", "Debug", f"             - Nwkid: {nwkid}/01 tuya_data_request_polling consecutive_elapse_time: {consecutive_elapse_time}")

    # We do the check that we do not overload and respect the consecutive_elapse_time
    if current_time < consecutive_elapse_time:
        # We need at least 6 secondes between each poll - so all data are correctly sent and the device is ready to take a new request
        self.log.logging("Tuya", "Debug", f"should_poll - Nwkid: {nwkid}/01 skip as last request was less that {tuya_elapse_time_consecutive_polling} s ago")
        return False

    # Check if the current time is less than the next polling time
    if current_time < next_poll_time:
        if additional_polls <= 0:
            return False

        self.log.logging("Tuya", "Debug", f"should_poll - Nwkid: {nwkid}/01 additional poll {additional_polls}")
        # If within additional polls window, decrement the counter and allow polling
        self.ListOfDevices[nwkid]["Tuya"][ tuya_last_poll_attribute ] = current_time
        self.ListOfDevices[nwkid]["Tuya"]["AdditionalPolls"] = additional_polls - 1
        return True

    # If the current time is greater than or equal to the next polling time, proceed with polling logic
    # Update the last polling time and reset the additional polls counter
    self.log.logging("Tuya", "Debug", f"should_poll - Nwkid: {nwkid}/01 We are entering in a new cycle")
    self.ListOfDevices[nwkid]["Tuya"][ tuya_last_poll_attribute ] = current_time
    self.ListOfDevices[nwkid]["Tuya"]["AdditionalPolls"] = tuya_data_request_polling_additional

    return True


def tuya_data_request_poll(self, nwkid, epout):
    self.log.logging("Tuya", "Debug", "tuya_data_request_poll - Nwkid: %s tuya polling Cmd: 00" % nwkid) 
    # Cmd 0x00 - 01/46/6902/0004/00000001/
    # Cmd 0x00 - 00/d7/6902/0004/00000001/

    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "6902"
    data = "00000001"

    self.log.logging("Tuya", "Debug", f"tuya_data_request_poll - Nwkid: {nwkid} epout: {epout} sqn: {sqn} cluster_frame: {cluster_frame} cmd: {cmd} action: {action} data: {data}")
    tuya_cmd(self, nwkid, epout, cluster_frame, sqn, cmd, action, data, action2=None, data2=None)


def tuya_data_request_end_poll(self, nwkid, epout):
    self.log.logging("Tuya", "Debug", "tuya_data_request_poll - Nwkid: %s tuya polling Cmd: 00" % nwkid) 
    # Cmd 0x00 - 01/46/6902/0004/00000001/
    # Cmd 0x00 - 00/d7/6902/0004/00000001/

    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "6902"
    data = "00000000"

    self.log.logging("Tuya", "Debug", f"tuya_data_request_poll - Nwkid: {nwkid} epout: {epout} sqn: {sqn} cluster_frame: {cluster_frame} cmd: {cmd} action: {action} data: {data}")
    tuya_cmd(self, nwkid, epout, cluster_frame, sqn, cmd, action, data, action2=None, data2=None)


def tuya_data_request(self, nwkid, epout):
    # TY_DATA_QUERY 	
    # 0x03 	The gateway sends a query to the Zigbee device for all the current information. 
    # The query does not contain a ZCL payload. We recommend that you set a reporting policy 
    # on the Zigbee device to avoid reporting all data in one task.
    
    cluster_frame = "11"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cmd = "03"  # TY_DATA_QUERY
    payload = cluster_frame + sqn + cmd

    self.log.logging("Tuya", "Log", f"tuya_data_request - Nwkid: {nwkid} epout: {epout} sqn: {sqn} cluster_frame: {cluster_frame} cmd: {cmd}")
    raw_APS_request( self, nwkid, epout, "ef00", "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=False )
    self.log.logging("Tuya", "Debug", "tuya_data_request - Nwkid: %s TUYA_DATA_QUERY Cmd: 03 done!" % nwkid)


def callbackDeviceAwake_Tuya(self, Devices, NwkId, EndPoint, cluster):
    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part
    """
    self.log.logging( "Tuya", "Debug", "callbackDeviceAwake_Tuya - Nwkid: %s, EndPoint: %s cluster: %s" % (NwkId, EndPoint, cluster))


def tuyaReadRawAPS(self, Devices, NwkId, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):

    if NwkId not in self.ListOfDevices:
        return

    if ClusterID == "e001":
        return tuya_read_cluster_e001(self, Devices, NwkId, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload)

    if ClusterID != "ef00" or "Model" not in self.ListOfDevices[NwkId]:
        return

    _ModelName = self.ListOfDevices[NwkId].get("Model", "")

    if len(MsgPayload) < 6:
        self.log.logging("Tuya", "Debug2", "tuyaReadRawAPS - MsgPayload %s too short" % (MsgPayload), NwkId)
        return
    
    fcf = MsgPayload[:2]  # uint8
    sqn = MsgPayload[2:4]  # uint8
    updSQN(self, NwkId, sqn)

    cmd = MsgPayload[4:6]  # uint8
    # Send a Default Response ( why might check the FCF eventually )
    if self.zigbee_communication == "native" and self.FirmwareVersion and int(self.FirmwareVersion, 16) < 0x031E:
        #tuya_send_default_response(self, NwkId, srcEp, sqn, cmd, fcf)
        tuya_default_response(self, NwkId, srcEp, ClusterID, cmd, sqn, fcf)
    elif self.zigbee_communication == "zigpy" and cmd == "02" and get_deviceconf_parameter_value(self, _ModelName, "TY_DEFAULT_RESPONSE", return_default=False):
        tuya_default_response(self, NwkId, srcEp, ClusterID, cmd, sqn, fcf)


    # https://developer.tuya.com/en/docs/iot/tuya-zigbee-module-uart-communication-protocol?id=K9ear5khsqoty
    self.log.logging( "Tuya", "Debug", "tuyaReadRawAPS - %s/%s fcf: %s sqn: %s cmd: %s Payload: %s" % (
        NwkId, srcEp, fcf, sqn, cmd, MsgPayload ), NwkId, )
    
    # 0c/02/0004/00000046
    # 0d/02/0004/00000014
    # 11/02/0004/0000001e0
    # 90/40/001/00

    if cmd in ( "01", "02",):  # TY_DATA_RESPONE, TY_DATA_REPORT
        status = MsgPayload[6:8]  # uint8
        self.log.logging( "Tuya", "Debug", "    status: %s" % ( status ), NwkId, )

        transid = MsgPayload[8:10]  # uint8
        self.log.logging( "Tuya", "Debug", "    TransId: %s" % ( transid ), NwkId, )
        idx = 10
        while idx < len(MsgPayload):
            self.log.logging( "Tuya", "Debug", "    working on remaining payload %s idx: %s" % ( MsgPayload[idx:], idx ), NwkId, )
            
            dp = int(MsgPayload[idx:idx + 2], 16)
            idx += 2
            
            datatype = int(MsgPayload[idx:idx + 2], 16)
            idx += 2
            
            len_data = 2 * int(MsgPayload[idx:idx + 4], 16)
            idx += 4
            
            data = MsgPayload[idx:idx + len_data]
            idx += len_data
            
            self.log.logging( "Tuya", "Debug", "tuyaReadRawAPS - command %s dp: %s dt: %s len: %s data: %s idx: %s" % (
                cmd, dp, datatype, len_data, data, idx ), NwkId, )
            tuya_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)
            
    elif cmd == "06":  # TY_DATA_SEARCH
        status = MsgPayload[6:8]  # uint8
        transid = MsgPayload[8:10]  # uint8
        dp = int(MsgPayload[10:12], 16)
        datatype = int(MsgPayload[12:14], 16)
        fn = MsgPayload[14:16]
        len_data = MsgPayload[16:18]
        data = MsgPayload[18:]
        self.log.logging(
            "Tuya",
            "Debug2",
            "tuyaReadRawAPS - command %s MsgPayload %s/ Data: %s" % (cmd, MsgPayload, MsgPayload[6:]),
            NwkId,
        )
        tuya_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)
        
    elif cmd == "0b":  # ??
        pass
    
    elif cmd == "10":  # ???
        pass

    elif cmd == "11":  # MCU_VERSION_RSP ( Return version or actively report version )
        # Model: TS0601-switch UNMANAGED Nwkid: 92d9/01 fcf: 09 sqn: 6c cmd: 11 data: 02f840
        try:
            transid = MsgPayload[6:10]  # uint16
            version = MsgPayload[10:12]  # int8
            store_tuya_attribute(self, NwkId, "TUYA_MCU_VERSION_RSP", version)
        except Exception as e:
            self.log.logging( "Tuya", "Error", "tuyaReadRawAPS - MCU_VERSION_RSP error on Payload: %s reason %s" % (MsgPayload,e))

    elif cmd == "23":  # TUYA_REPORT_LOG
        pass

    elif cmd == "24":  # Time Synchronisation
        send_timesynchronisation(self, NwkId, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload[6:])

    elif cmd == "25":  # CHECK_ZIGBEE_GATEWAY_STATUS_CMD 
        # 0x00: The gateway is not connected to the internet.
        # 0x01: The gateway is connected to the internet.
        # 0x02: The request timed out after three seconds.
        in_payload = MsgPayload[6:]
        self.log.logging( "Tuya", "Debug", "tuyaReadRawAPS - Model: %s CHECK_ZIGBEE_GATEWAY_STATUS_CMD Nwkid: %s/%s fcf: %s sqn: %s cmd: %s data: %s" % (
            _ModelName, NwkId, srcEp, fcf, sqn, cmd, MsgPayload[6:]), NwkId, )

        sqn_out = get_and_inc_ZCL_SQN(self, NwkId)
        EPout = "01"
        cluster_frame = "11"
        cmd = "25"  # Command
        payload = cluster_frame + sqn_out + cmd + in_payload + "01"
        raw_APS_request(self, NwkId, srcEp, "ef00", "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=False)

    
    else:
        self.log.logging( "Tuya", "Log", "tuyaReadRawAPS - Model: %s UNMANAGED Nwkid: %s/%s fcf: %s sqn: %s cmd: %s data: %s" % (
            _ModelName, NwkId, srcEp, fcf, sqn, cmd, MsgPayload[6:]), NwkId, )


def tuya_default_response(self, SrcNwkId, SrcEndPoint, ClusterID, Command, Sqn, fcf):
    self.log.logging( "Tuya", "Debug", "tuya_default_response -  %s/%s %s %s %s %s" %(
        SrcNwkId, SrcEndPoint, ClusterID, Command, Sqn, fcf ))
    zcl_raw_default_response( self, SrcNwkId, ZIGATE_EP, SrcEndPoint, ClusterID, Command, Sqn, command_status="00", manufcode=None, orig_fcf=fcf )


def tuya_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):

    self.log.logging( "Tuya", "Debug", "tuya_response - Model: %s Nwkid: %s/%s dp: %02x dt: %02x data: %s" % (
        _ModelName, NwkId, srcEp, dp, datatype, data), NwkId, )
    self.log.logging( "Tuya0601", "Debug", "tuya_response - Model: %s Nwkid: %s/%s dp: %02x dt: %02x data: %s" % (
        _ModelName, NwkId, srcEp, dp, datatype, data), NwkId, )

    if ts0601_response(self, Devices, _ModelName, NwkId, srcEp, dp, datatype, data):
        # This is a generic a new fashion to handle the Tuya TS0601 Data Point.
        return

    if _ModelName in ( "TS0202-_TZ3210_jijr1sss",):
        tuya_smart_motion_all_in_one(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)
        
    elif _ModelName in ("TS0601-switch", "TS0601-2Gangs-switch", "TS0601-2Gangs-switch"):
        tuya_switch_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName in ("TS0601-Parkside-Watering-Timer"):
        tuya_watertimer_response(
            self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data )

    elif _ModelName == "TS0601-SmartAir":
        tuya_smartair_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName == "TS0601-curtain":
        tuya_curtain_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName == "TS0601-_TZE200_nklqjk62":
        tuya_garage_door_response( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)
        
    elif _ModelName in ("TS0601-thermostat", "TS0601-_TZE200_dzuqwsyg", ):
        tuya_eTRV_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName in (TUYA_eTRV_MODEL):
        tuya_eTRV_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName in ( "TS0601-sirene", ):
        tuya_siren_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName in ( "TS0601-_TZE200_t1blo2bj", ):
        tuya_siren2_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName in ( "TS0601-dimmer", "TS0601-2Gangs-dimmer"):
        tuya_dimmer_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName == "TS0601-Energy":
        tuya_energy_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName == "TS0601-smoke":
        tuya_smoke_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)

    elif _ModelName == "TS0601-temphumi":
        tuya_temphumi_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)
 
    elif _ModelName == "TS0601-motion":
        tuya_motion_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)
 
    elif _ModelName in TUYA_SMART_DOOR_LOCK_MODEL:
        tuya_smart_door_lock(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data)  
        
    else:
        attribute_name = "UnknowDp_0x%02x_Dt_0x%02x" % (dp, datatype)
        store_tuya_attribute(self, NwkId, attribute_name, data)
        self.log.logging(
            "Tuya",
            "Log",
            "tuya_response - Model: %s UNMANAGED Nwkid: %s/%s dp: %02x data type: %s data: %s"
            % (_ModelName, NwkId, srcEp, dp, datatype, data),
            NwkId,
        )


def send_timesynchronisation(self, NwkId, srcEp, ClusterID, dstNWKID, dstEP, serial_number):

    # Request: cmd: 0x24  Data: 0x0008
    # 0008 600d8029 600d8e39
    # Request: cmd: 0x24 Data: 0x0053
    # 0053 60e9ba1f  60e9d63f
    if NwkId not in self.ListOfDevices:
        return
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    field1, field2, field3 = "0d", "80", "29"

    EPOCTime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    UTCTime_in_sec = int((now - EPOCTime).total_seconds())
    LOCALtime_in_sec = int((utc_to_local(now) - EPOCTime).total_seconds())

    utctime = f"{UTCTime_in_sec:08x}"
    localtime = f"{LOCALtime_in_sec:08x}"
    self.log.logging( "Tuya", "Debug", f"send_timesynchronisation - {NwkId}/{srcEp} UTC: {UTCTime_in_sec} Local: {LOCALtime_in_sec}", )

    payload = f"11{sqn}24{serial_number}{utctime}{localtime}"
    raw_APS_request(self, NwkId, srcEp, "ef00", "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=False)
    self.log.logging("Tuya", "Debug", f"send_timesynchronisation - {NwkId}/{srcEp}")


def utc_to_local(dt):
    # https://stackoverflow.com/questions/4563272/convert-a-python-utc-datetime-to-a-local-datetime-using-only-python-standard-lib
    if time.localtime().tm_isdst:
        return dt - timedelta(seconds=time.altzone)

    return dt - timedelta(seconds=time.timezone)


def tuya_send_default_response(self, Nwkid, srcEp, sqn, cmd, orig_fcf, force_disabled_default=False):
    if Nwkid not in self.ListOfDevices:
        return

    orig_fcf = int(orig_fcf, 16)
    frame_type = "%02x" % (0b00000011 & orig_fcf)
    manuf_spec = "%02x" % ((0b00000100 & orig_fcf) >> 2)
    direction = "%02x" % (not ((0b00001000 & orig_fcf) >> 3))
    disabled_default = "%02x" % ((0b00010000 & orig_fcf) >> 4)

    if disabled_default == "01":
        return

    if force_disabled_default:
        disabled_default = "01"

    fcf = build_fcf("00", manuf_spec, direction, disabled_default)

    payload = fcf + sqn + "0b"
    if manuf_spec == "01":
        payload += TUYA_MANUF_CODE[2:4] + TUYA_MANUF_CODE[:2]
    payload += cmd + "00"
    raw_APS_request(
        self,
        Nwkid,
        srcEp,
        "ef00",
        "0104",
        payload,
        zigate_ep=ZIGATE_EP,
        highpriority=True,
        ackIsDisabled=is_ack_tobe_disabled(self, Nwkid),
    )
    self.log.logging(
        "Tuya",
        "Debug",
        "tuya_send_default_response - %s/%s fcf: 0x%s ManufSpec: 0x%s Direction: 0x%s DisableDefault: 0x%s"
        % (Nwkid, srcEp, fcf, manuf_spec, direction, disabled_default),
    )


# Tuya TS0601 - Switch 1, 2, 3 Gangs
def tuya_switch_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    if dp == 0x01:
        # Switch 1 ( Right in case of 2gangs)
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_switch_response - Dp 0x01 Nwkid: %s/%s decodeDP: %04x data: %s" % (NwkId, srcEp, dp, data),
            NwkId,
        )
        MajDomoDevice(self, Devices, NwkId, "01", "0006", data)

    elif dp == 0x02:
        # Switch 2  (Left in case of 2 Gangs)
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_switch_response - Dp 0x02 Nwkid: %s/%s decodeDP: %04x data: %s" % (NwkId, srcEp, dp, data),
            NwkId,
        )
        MajDomoDevice(self, Devices, NwkId, "02", "0006", data)

    elif dp == 0x03:
        # Switch 3
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_switch_response - Dp 0x03 Nwkid: %s/%s decodeDP: %04x data: %s" % (NwkId, srcEp, dp, data),
            NwkId,
        )
        MajDomoDevice(self, Devices, NwkId, "03", "0006", data)

    elif dp == 0x0D:
        # All switches
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_switch_response - Dp 0x03 Nwkid: %s/%s decodeDP: %04x data: %s" % (NwkId, srcEp, dp, data),
            NwkId,
        )
        MajDomoDevice(self, Devices, NwkId, "01", "0006", data)
        MajDomoDevice(self, Devices, NwkId, "02", "0006", data)
        MajDomoDevice(self, Devices, NwkId, "03", "0006", data)

    elif dp == 0x0E:  # Relay Status
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_switch_response - Dp 0x0e Nwkid: %s/%s decodeDP: %04x data: %s" % (NwkId, srcEp, dp, data),
            NwkId,
        )
        store_tuya_attribute(self, NwkId, "RelayStatus", int(data, 16))

    elif dp == 0x0F:  # Light Indicator
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_switch_response - Dp 0x0f Nwkid: %s/%s decodeDP: %04x data: %s" % (NwkId, srcEp, dp, data),
            NwkId,
        )
        store_tuya_attribute(self, NwkId, "LightIndicator", int(data, 16))

    else:
        attribute_name = "UnknowDp_0x%02x_Dt_0x%02x" % (dp, datatype)
        store_tuya_attribute(self, NwkId, attribute_name, data)
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_switch_response - Unknown attribut Nwkid: %s/%s decodeDP: %04x data: %s" % (NwkId, srcEp, dp, data),
            NwkId,
        )

    #  Decode8002 - NwkId: b1ed Ep: 01 Cluster: ef00 GlobalCommand: False Command: 01 Data: 004c 0101 0001 00
    #  raw_APS_request - ackIsDisabled: False Addr: b1ed Ep: 01 Cluster: ef00 ProfileId: 0104 Payload: 006b0b0100
    #  tuya_send_default_response - b1ed/01 fcf: 0x00 ManufSpec: 0x00 Direction: 0x00 DisableDefault: 0x00
    #  tuya_response - Model: TS0601-2Gangs-switch Nwkid: b1ed/01 dp: 01 data: 00
    #  tuya_switch_response - Dp 0x01 Nwkid: b1ed/01 decodeDP: 0001 data: 00

    #  Decode8002 - NwkId: b1ed Ep: 01 Cluster: ef00 GlobalCommand: False Command: 01 Data: 004d 0201 0001 00
    #  raw_APS_request - ackIsDisabled: False Addr: b1ed Ep: 01 Cluster: ef00 ProfileId: 0104 Payload: 006c0b0100
    #  tuya_send_default_response - b1ed/01 fcf: 0x00 ManufSpec: 0x00 Direction: 0x00 DisableDefault: 0x00
    #  tuya_response - Model: TS0601-2Gangs-switch Nwkid: b1ed/01 dp: 02 data: 00
    #  tuya_switch_response - Dp 0x02 Nwkid: b1ed/01 decodeDP: 0002 data: 00


def tuya_switch_command(self, NwkId, onoff, gang=0x01):

    self.log.logging(
        "Tuya", "Debug", "tuya_switch_command - %s OpenClose: %s on gang: %s" % (NwkId, onoff, gang), NwkId
    )
    # determine which Endpoint
    if gang not in (0x01, 0x02, 0x03):
        self.log.logging("Tuya", "Error", "tuya_switch_command - Unexpected Gang: %s" % gang)
        return
    if onoff not in ("00", "01"):
        self.log.logging("Tuya", "Error", "tuya_switch_command - Unexpected OnOff: %s" % onoff)
        return

    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "%02x01" % gang  # Data Type 0x01 - Bool
    data = onoff
    self.log.logging("Tuya", "Debug", "tuya_switch_command - action: %s data: %s" % (action, data))
    tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_energy_childLock(self, NwkId, lock=0x01):
    # 0012 1d 01 0001 00 Child Unlock
    # 0011 1d 01 0001 01 Child Lock

    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "1d01"
    data = "%02x" % lock
    self.log.logging("tuyaSettings", "Debug", "tuya_energy_childLock - action: %s data: %s" % (action, data))
    tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_switch_indicate_light(self, NwkId, light=0x01):
    # 0005 0f 04 0001 00 -- Indicate Off
    # 0004 0f 04 0001 01 -- Indicate Switch ( On when On)
    # 0006 0f 04 0001 02 -- Indicate Position (on when Off )
    self.log.logging("tuyaSettings", "Debug", "tuya_switch_indicate_light - %s Light: %s" % (NwkId, light), NwkId)
    # determine which Endpoint
    if light not in (0x00, 0x01, 0x02):
        self.log.logging("tuyaSettings", "Error", "tuya_switch_indicate_light - Unexpected light: %s" % light)
        return
        
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "0f04"
    data = "%02x" % light
    self.log.logging("tuyaSettings", "Debug", "tuya_switch_indicate_light - action: %s data: %s" % (action, data))
    tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_switch_relay_status(self, NwkId, gang=0x01, status=0xFF):
    # 00070 e04 0001 02  -- Remember last status
    # 00080 e04 0001 01  -- On
    # 00090 e04 0001 00  -- Off
    self.log.logging("Tuya", "Debug", "tuya_switch_relay_status - %s Light: %s" % (NwkId, status), NwkId)
    # determine which Endpoint
    if status not in (0x00, 0x01, 0x02, 0xFF):
        self.log.logging("Tuya", "Error", "tuya_switch_relay_status - Unexpected light: %s" % status)
        return

    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "0e04"
    data = "%02x" % status
    self.log.logging("Tuya", "Debug", "tuya_switch_relay_status - action: %s data: %s" % (action, data))
    tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_watertimer_command(self, NwkId, onoff, gang=0x01):

    self.log.logging(
        "Tuya", "Debug", "tuya_switch_command - %s OpenClose: %s on gang: %s" % (NwkId, onoff, gang), NwkId
    )
    # determine which Endpoint
    if gang not in (0x01, 0x02, 0x03):
        self.log.logging("Tuya", "Error", "tuya_switch_command - Unexpected Gang: %s" % gang)
        return
    if onoff not in ("00", "01"):
        self.log.logging("Tuya", "Error", "tuya_switch_command - Unexpected OnOff: %s" % onoff)
        return

    EPout = "01"
    cluster_frame = "11"
    cmd = "00"  # Command

    if onoff == "01":
        sqn = get_and_inc_ZCL_SQN(self, NwkId)
        action = "0b02"
        data = "0000012c"
        tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)

    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    action = "%02x01" % gang  # Data Type 0x01 - Bool
    data = onoff
    self.log.logging("Tuya", "Debug", "tuya_switch_command - action: %s data: %s" % (action, data))
    tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_watertimer_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):

    self.log.logging(
        "Tuya",
        "Debug",
        "tuya_watertimer_response - Model: %s Nwkid: %s/%s dp: %02x data type: %02x data: %s"
        % (_ModelName, NwkId, srcEp, dp, datatype, data),
        NwkId,
    )

    if dp == 0x01:
        # Openned
        # tuya_response - Model: TS0601-Parkside-Watering-Timer Nwkid: a82e/01 dp: 06 data type: 2 data: 00000001
        # tuya_response - Model: TS0601-Parkside-Watering-Timer Nwkid: a82e/01 dp: 01 data type: 1 data: 010502000400000001

        # tuya_response - Model: TS0601-Parkside-Watering-Timer Nwkid: a82e/01 dp: 06 data type: 2 data: 00000001
        # tuya_response - Model: TS0601-Parkside-Watering-Timer Nwkid: a82e/01 dp: 01 data type: 1 data: 010502000400000001

        # Closing via Button
        # tuya_response - Model: TS0601-Parkside-Watering-Timer Nwkid: a82e/01 dp: 01 data type: 1 data: 000502000400000001

        # tuya_response - Model: TS0601-Parkside-Watering-Timer Nwkid: a82e/01 dp: 06 data type: 2 data: 00000000
        # tuya_response - Model: TS0601-Parkside-Watering-Timer Nwkid: a82e/01 dp: 01 data type: 1 data: 000502000400000001

        store_tuya_attribute(self, NwkId, "Valve 0x01", data)
        if datatype == 0x01:   # Bool
            self.log.logging(
                "Tuya",
                "Debug",
                "tuya_watertimer_response - Model: %s Nwkid: %s/%s dp: %02x data type: %02x data: %s reporting to Domoticz"
                % (_ModelName, NwkId, srcEp, dp, datatype, data),
                NwkId,
            )

            MajDomoDevice(self, Devices, NwkId, "01", "0006", data)

    elif dp == 0x05:  #
        store_tuya_attribute(self, NwkId, "Valve 0x05", data)

    elif dp == 0x06 and datatype == 0x02:  # Valve State
        state = "%02d" % int(data)
        store_tuya_attribute(self, NwkId, "Valve state", state)
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_response - ------ Request  MajDomoDevice(self, Devices, %s, %s, '0006', %s)" % (NwkId, srcEp, state),
        )
        MajDomoDevice(self, Devices, NwkId, srcEp, "0006", state)

    elif dp == 0x0B:
        store_tuya_attribute(self, NwkId, "Valve 0x0b", data)

    elif dp == 0x65:
        store_tuya_attribute(self, NwkId, "Valve 0x65", data)
    elif dp == 0x66:
        store_tuya_attribute(self, NwkId, "Valve 0x66", data)
    elif dp == 0x67:
        store_tuya_attribute(self, NwkId, "Valve 0x67", data)
    elif dp == 0x68:
        store_tuya_attribute(self, NwkId, "Valve 0x68", data)
    elif dp == 0x69:
        store_tuya_attribute(self, NwkId, "Valve 0x69", data)
    elif dp == 0x6A:
        store_tuya_attribute(self, NwkId, "Valve 0x6a", data)
    elif dp == 0x6B:
        store_tuya_attribute(self, NwkId, "Valve 0x6b", data)


# Tuya TS0601 - Curtain
def tuya_curtain_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    # dp 0x01 closing -- Data can be 00 , 01, 02 - Opening, Stopped, Closing
    # dp 0x02 Percent control - Percent control
    # db 0x03 and data '00000000'  - Percent state when arrived at position (report)
    # dp 0x05 and data - direction state
    # dp 0x07 and data 00, 01 - Opening, Closing
    # dp 0x69 and data '00000028'

    # 000104ef00010102 94fd 02 00000970020000 0202 0004 00000004

    self.log.logging(
        "Tuya", "Debug", "tuya_curtain_response - Nwkid: %s/%s dp: %s data: %s" % (NwkId, srcEp, dp, data), NwkId
    )

    if dp == 0x01:  # Open / Closing / Stopped
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_curtain_response - Open/Close/Stopped action Nwkid: %s/%s  %s" % (NwkId, srcEp, data),
            NwkId,
        )
        store_tuya_attribute(self, NwkId, "Action", data)

    elif dp == 0x02:
        # Percent Control
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_curtain_response - Percentage Control action Nwkid: %s/%s  %s" % (NwkId, srcEp, data),
            NwkId,
        )
        store_tuya_attribute(self, NwkId, "PercentControl", data)

    elif dp in (0x03, 0x07):
        slevel = _tuya_percentage_2_analog( data )
        store_tuya_attribute(self, NwkId, "PercentState", data)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0008", slevel)

    elif dp == 0x05:
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_curtain_response - Direction state Nwkid: %s/%s Action %s" % (NwkId, srcEp, data),
            NwkId,
        )
        store_tuya_attribute(self, NwkId, "DirectionState", data)

    elif dp in (0x67, 0x69):
        slevel = _tuya_percentage_2_analog( data )
        MajDomoDevice(self, Devices, NwkId, srcEp, "0008", slevel)
        store_tuya_attribute(self, NwkId, "dp_%s" % dp, data)

    else:
        attribute_name = "UnknowDp_0x%02x_Dt_0x%02x" % (dp, datatype)
        store_tuya_attribute(self, NwkId, attribute_name, data)


# TODO Rename this here and in `tuya_curtain_response`
def _tuya_percentage_2_analog(data):
    # Curtain Percentage
    # We need to translate percentage into Analog value between 0 - 255
    level = ((int(data, 16)) * 255) // 100
    return "%02x" % level


def tuya_curtain_openclose(self, NwkId, openclose):
    self.log.logging("Tuya", "Debug", "tuya_curtain_openclose - %s OpenClose: %s" % (NwkId, openclose), NwkId)
    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "0101"
    data = openclose
    tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_curtain_stop(self, NwkId):
    pass


def tuya_curtain_lvl(self, NwkId, percent):
    self.log.logging("Tuya", "Debug", "tuya_curtain_lvl - %s percent: %s" % (NwkId, percent), NwkId)

    level = percent
    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "0202"
    data = "%08x" % level
    tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


# Tuya Smart Dimmer Switch
def tuya_dimmer_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    #             cmd | status | transId | dp | DataType | fn | len | Data
    # Dim Down:     01     00        01     02      02      00    04   00000334
    # Dim Up:       01     00        01     02      02      00    04   0000005a
    # Switch Off:   01     00        01     01      01      00    01   00
    # Dim Up  :     01     00        01     01      01      00    01   01

    if dp in ( 0x01, 0x07):  # Switch On/Off
        ep = srcEp if dp == 0x01 else "02"
        MajDomoDevice(self, Devices, NwkId, ep, "0006", data)
        self.log.logging("Tuya", "Debug", "tuya_dimmer_response - Nwkid: %s/%s On/Off %s" % (NwkId, srcEp, data), NwkId)

    elif dp == 0x02:  # Dim Down/Up
        ep = srcEp if dp == 0x02 else "02"
        # As MajDomoDevice expect a value between 0 and 255, and Tuya dimmer is on a scale from 0 - 1000.
        analogValue = int(data, 16) / 10  # This give from 1 to 100
        level = int((analogValue * 255) / 100)

        self.log.logging( "Tuya", "Debug", "tuya_dimmer_response - Nwkid: %s/%s Dim up/dow %s %s" % (
            NwkId, srcEp, int(data, 16), level), NwkId, )
        MajDomoDevice(self, Devices, NwkId, ep, "0008", "%02x" % level)
        
    else:
        attribute_name = "UnknowDp_0x%02x_Dt_0x%02x" % (dp, datatype)
        store_tuya_attribute(self, NwkId, attribute_name, data)


def tuya_dimmer_onoff(self, NwkId, srcEp, OnOff):

    self.log.logging("Tuya", "Debug", "tuya_dimmer_onoff - %s OnOff: %s" % (NwkId, OnOff), NwkId)
    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "0101" if srcEp == "01" else "0701"
    data = OnOff
    tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_dimmer_dimmer(self, NwkId, srcEp, percent):
    self.log.logging("Tuya", "Debug", "tuya_dimmer_dimmer - %s percent: %s" % (NwkId, percent), NwkId)

    level = percent * 10
    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "0202" if srcEp == "01" else "0802"
    data = "%08x" % level
    tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


# Tuya Smart Cover Switch
def tuya_window_cover_calibration(self, nwkid, duration):
    # (0x0102) | Write Attributes (0x02) | 0xf003 | 0x21 16-Bit Unsigned Int | 600 0x0258) | 68 s
    self.log.logging( "tuyaSettings", "Debug", "tuya_window_cover_calibration - Nwkid: %s Calibration %s" % (
        nwkid, duration), nwkid, )

    self.log.logging( "tuyaSettings", "Debug", "tuya_window_cover_calibration - duration %s" % ( duration), nwkid, )
    write_attribute(self, nwkid, ZIGATE_EP, "01", "0102", "0000", "00", "f003", "21", "%04x" %duration, ackIsDisabled=False)


def tuya_window_cover_motor_reversal(self, nwkid, mode):
    # (0x0102) | Write Attributes (0x02) | 0xf002 | 8-Bit (0x30) | 0 (0x00) | Off / Default
    # (0x0102) | Write Attributes (0x02) | 0xf002 | 8-Bit (0x30) | 1 (0x01) | On
    if int(mode) in {0, 1}:
        write_attribute( self, nwkid, ZIGATE_EP, "01", "0102", "0000", "00", "f002", "30", "%02x" % int(mode), ackIsDisabled=False )


def tuya_curtain_mode(self, nwkid, mode):
    # (0x0006) | Write Attributes (0x02) | 0x8001 | 8-Bit (0x30) | 0 (0x00) | Kick Back
    # (0x0006) | Write Attributes (0x02) | 0x8001 | 8-Bit (0x30) | 1 (0x01) | Seesaw
    if int(mode) in {0, 1}:
        write_attribute( self, nwkid, ZIGATE_EP, "01", "0006", "0000", "00", "8001", "30", "%02x" % int(mode), ackIsDisabled=False )


def tuya_backlight_command(self, nwkid, mode):
    if int(mode) in {0, 1, 2}:
        backlist_attribute = ( "5000" if 'Model' in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Model"] in ("TS130F-_TZ3000_fvhunhxb", "TS130F-_TZ3000_1dd0d5yi",) else "8001"  )
        write_attribute( self, nwkid, ZIGATE_EP, "01", "0006", "0000", "00", backlist_attribute, "30", "%02x" % int(mode), ackIsDisabled=False )


def tuya_smartair_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):

    #             cmd | status | transId | dp | DataType | fn | len | Data
    #              01     00        00     12     02        00   04    00000101   257   --- Temperature
    #              01     00        00     13     02        00   04    0000018d   397   --- Humidity  Confirmed
    #              01     00        01     16     02        00   04    00000002     2   --- 0.002 ppm Formaldéhyde détécté
    #              01     00        01     15     02        00   04    00000001     1   --- VOC 0.1 ppm - Confirmed
    #              01     00        01     02     02        00   04    00000172   370   --- CO2 - Confirmed

    # The device is flooding data every seconds. This could have the impact to flow the Domoticz database/
    if (
        "Param" in self.ListOfDevices[NwkId]
        and "AcquisitionFrequency" in self.ListOfDevices[NwkId]["Param"]
        and self.ListOfDevices[NwkId]["Param"]["AcquisitionFrequency"] > 0
    ):
        previous_ts = get_tuya_attribute(self, NwkId, "TimeStamp_%s" % dp)
        if previous_ts and (previous_ts + self.ListOfDevices[NwkId]["Param"]["AcquisitionFrequency"]) > time.time():
            return
        store_tuya_attribute(self, NwkId, "TimeStamp_%s" % dp, time.time())

    # Temp/Humi/CarbonDioxyde/CH20/Voc
    if dp == 0x02:  # CO2 ppm
        co2_Attribute = "0005"
        co2_ppm = int(data, 16)
        store_tuya_attribute(
            self,
            NwkId,
            "CO2 ppm",
            co2_ppm,
        )
        MajDomoDevice(self, Devices, NwkId, srcEp, "0402", co2_ppm, Attribute_=co2_Attribute)

    elif dp == 0x12:  # Temperature
        temp = int(data, 16) / 10
        store_tuya_attribute(self, NwkId, "Temp", temp)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0402", temp)
        checkAndStoreAttributeValue(self, NwkId, srcEp, "0402", "0000", temp)

    elif dp == 0x13:  # Humidity %
        humi = int(data, 16) // 10
        store_tuya_attribute(self, NwkId, "Humi", humi)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0405", humi)

    elif dp == 0x15:  # VOC ppm
        voc_Attribute = "0003"
        voc_ppm = int(data, 16) / 10
        store_tuya_attribute(self, NwkId, "VOC ppm", voc_ppm)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0402", voc_ppm, Attribute_=voc_Attribute)

    elif dp == 0x16:  # Formaldéhyde µg/m3 ( Méthanal / CH2O_ppm)
        ch2O_Attribute = "0004"
        CH2O_ppm = int(data, 16)
        store_tuya_attribute(self, NwkId, "CH2O ppm", CH2O_ppm)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0402", CH2O_ppm, Attribute_=ch2O_Attribute)


# Tuya Smart Energy DIN Rail
def tuya_energy_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):

    if dp == 0x01 and datatype == 0x01:  # State On/Off
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_energy_response - Model: %s State Nwkid: %s/%s dp: %02x data type: %s data: %s"
            % (_ModelName, NwkId, srcEp, dp, datatype, data),
            NwkId,
        )
        store_tuya_attribute(self, NwkId, "State", data)
        MajDomoDevice(self, Devices, NwkId, "01", "0006", data)

    elif dp == 0x09:  # Countdown
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_energy_response - Model: %s State Nwkid: %s/%s dp: %02x data type: %s data: %s"
            % (_ModelName, NwkId, srcEp, dp, datatype, data),
            NwkId,
        )
        store_tuya_attribute(self, NwkId, "Countdown", data)

    elif dp == 0x11:  # Total Energy * 10
        analogValue = int(data, 16) * 10
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_energy_response - Model: %s Energy Nwkid: %s/%s dp: %02x data type: %s data: %s"
            % (_ModelName, NwkId, srcEp, dp, datatype, data),
            NwkId,
        )
        MajDomoDevice(self, Devices, NwkId, "01", "0702", str(analogValue), Attribute_="0000")
        checkAndStoreAttributeValue(self, NwkId, "01", "0702", "0000", analogValue)  # Store int
        store_tuya_attribute(self, NwkId, "Energy", str(analogValue))

    elif dp == 0x12:  # Current (Ampere) / 1000
        analogValue = int(data, 16) / 1000
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_energy_response - Model: %s Current Nwkid: %s/%s dp: %02x data type: %s data: %s"
            % (_ModelName, NwkId, srcEp, dp, datatype, data),
            NwkId,
        )
        MajDomoDevice(self, Devices, NwkId, "01", "0b04", str(analogValue), Attribute_="0508")
        store_tuya_attribute(self, NwkId, "Current", str(analogValue))

    elif dp == 0x13:  # Power / 10
        analogValue = int(data, 16) / 10
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_energy_response - Model: %s Power Nwkid: %s/%s dp: %02x data type: %s data: %s"
            % (_ModelName, NwkId, srcEp, dp, datatype, data),
            NwkId,
        )
        checkAndStoreAttributeValue(self, NwkId, "01", "0702", "0400", str(analogValue))
        MajDomoDevice(self, Devices, NwkId, "01", "0702", str(analogValue))
        store_tuya_attribute(self, NwkId, "InstantPower", str(analogValue))  # Store str

    elif dp == 0x14:  # Voltage / 10
        analogValue = int(data, 16) / 10
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_energy_response - Model: %s Voltage Nwkid: %s/%s dp: %02x data type: %s data: %s"
            % (_ModelName, NwkId, srcEp, dp, datatype, data),
            NwkId,
        )
        MajDomoDevice(self, Devices, NwkId, "01", "0001", str(analogValue))
        store_tuya_attribute(self, NwkId, "Voltage", str(analogValue))

    elif dp == 0x0E:  # tuya_switch_relay_status
        store_tuya_attribute(self, NwkId, "RelayStatus", data)

    elif dp == 0x0F:  # Led Indicator
        store_tuya_attribute(self, NwkId, "LedIndicator", data)

    elif dp == 0x1D:
        store_tuya_attribute(self, NwkId, "ChildLock", data)

    else:
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_energy_response - Model: %s Unknow Nwkid: %s/%s dp: %02x data type: %s data: %s"
            % (_ModelName, NwkId, srcEp, dp, datatype, data),
            NwkId,
        )


def tuya_energy_toggle(self, NwkId):
    tuya_energy_countdown(self, NwkId, 0x01)


def tuya_energy_onoff(self, NwkId, OnOff):
    # 0013 01 01 0001 01 Power On
    # 0014 01 01 0001 00 Power Off
    self.log.logging("Tuya", "Debug", "tuya_energy_onoff - %s OnOff: %s" % (NwkId, OnOff), NwkId)

    if (
        "Param" in self.ListOfDevices[NwkId]
        and "Countdown" in self.ListOfDevices[NwkId]["Param"]
        and self.ListOfDevices[NwkId]["Param"]["Countdown"]
    ):
        tuya_energy_countdown(self, NwkId, int(self.ListOfDevices[NwkId]["Param"]["Countdown"]))
    else:
        EPout = "01"
        sqn = get_and_inc_ZCL_SQN(self, NwkId)
        cluster_frame = "11"
        cmd = "00"  # Command
        action = "0101"
        data = OnOff
        tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_energy_countdown(self, NwkId, timing):

    # Countdown is 0x09 for Energy device
    # Countdown is 0x42 for Multigang Switch : https://developer.tuya.com/en/docs/iot/tuya-zigbee-multiple-switch-access-standard?id=K9ik6zvnqr09m#title-15-Countdown

    self.log.logging("Tuya", "Debug", "tuya_energy_countdown - %s timing: %s" % (NwkId, timing), NwkId)

    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "0902"
    data = "%08x" % timing
    tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_smart_motion_all_in_one(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    
    if dp == 0x6b:  # Temperature
        self.log.logging("Tuya", "Debug", "tuya_smart_motion_all_in_one - Temperature %s" % int(data, 16), NwkId)
        MajDomoDevice(self, Devices, NwkId, "02", "0402", (int(data, 16) / 10))
        checkAndStoreAttributeValue(self, NwkId, srcEp, "0402", "0000", (int(data, 16) / 10))
        store_tuya_attribute(self, NwkId, "Temperature", data)
        
    elif dp == 0x6c:  # Humidity
        self.log.logging("Tuya", "Debug", "tuya_smart_motion_all_in_one - Humidity %s" % int(data, 16), NwkId)
        MajDomoDevice(self, Devices, NwkId, "02", "0405", (int(data, 16)))
        store_tuya_attribute(self, NwkId, "Humidity", data)
        
    else:
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_smart_motion_all_in_one - Model: %s Unknow Nwkid: %s/%s dp: %02x data type: %s data: %s"
            % (_ModelName, NwkId, srcEp, dp, datatype, data),
            NwkId,
        )


def tuya_pir_keep_time_lookup( self, nwkid, keeptime):
    keeptime = min( keeptime // 30, 2)
    
    self.log.logging("tuyaSettings", "Debug", "tuya_pir_keep_time_lookup - keeptime duration %s secondes" % keeptime, nwkid)
    EPout = "01"
    
    write_attribute(self, nwkid, ZIGATE_EP, EPout, "0500", "0000", "00", "f001", "20", "%02x" %keeptime, ackIsDisabled=False)


def tuya_garage_door_response( self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    
    if dp == 0x01:
        # Switch / Trigger
        self.log.logging("Tuya", "Debug", "tuya_garage_door_response - Switch %s" % int(data, 16), NwkId)
        MajDomoDevice(self, Devices, NwkId, "01", "0006", "%02x" %(int(data, 16)) )
        store_tuya_attribute(self, NwkId, "DoorSwitch", data)

    elif dp == 0x03:
        # Door Contact: 0x00 => Closed, 0x01 => Open
        self.log.logging("Tuya", "Debug", "tuya_garage_door_response - Door Contact %s" % int(data, 16), NwkId)
        MajDomoDevice(self, Devices, NwkId, "01", "0500", "%02x" %(int(data, 16)) )
        store_tuya_attribute(self, NwkId, "DoorContact", data)

    elif dp == 0x0c:
        # Door Status
        # 00a8 0c 04 0001 02
        self.log.logging("Tuya", "Debug", "tuya_garage_door_response - Door Status %s" % int(data, 16), NwkId)
        store_tuya_attribute(self, NwkId, "DoorStatus", data)
        
    else:
        store_tuya_attribute(self, NwkId, "dp:%s-dt:%s" %(dp, datatype), data)


def tuya_garage_door_action( self, NwkId, onoff):
    # 000f/0101/0001/00
    # 0010/0101/0001/01
    self.log.logging("Tuya", "Debug", "tuya_garage_door_action - action %s" % onoff, NwkId)
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "0101"
    data = "%02x" %int(onoff)
    self.log.logging("Tuya", "Debug", "tuya_garage_door_action - action %s data: %s" % (action,data), NwkId)
    tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_garage_run_time(self, NwkId, duration):
    # 0006/0402/0004/0000001e  30 secondes
    # 0007/0402/0004/0000003c  60 secondes
    self.log.logging("tuyaSettings", "Debug", "tuya_garage_run_time - duration %s" % duration, NwkId)
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "0402"
    data = "%04x" % int(duration)
    tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_garage_timeout(self, NwkId, duration):
    # 0008/0502/0004/0000012c  300 secondes - 5 minutes
    self.log.logging("Tuya", "Debug", "tuya_garage_timeout - duration %s" % duration, NwkId)
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "0502"
    data = "%04x" % int(duration)
    tuya_cmd(self, NwkId, EPout, cluster_frame, sqn, cmd, action, data)


TUYA_TS0004_MANUF_CODE = "1141"
TUYA_CLUSTER_EOOO_ID = "e000"
TUYA_CLUSTER_EOO1_ID = "e001"
TUYA_SWITCH_MODE = {
    "Toggle": 0x00,
    "State": 0x01,
    "Momentary": 0x02,
    0: 0x00,
    1: 0x01,
    2: 0x02
}


def tuya_external_switch_mode( self, NwkId, mode):
 
    self.log.logging("tuyaSettings", "Debug", "tuya_external_switch_mode - mode %s" % mode, NwkId)
    if mode not in TUYA_SWITCH_MODE:
        self.log.logging("tuyaSettings", "Debug", "tuya_external_switch_mode - mode %s undefined" % mode, NwkId)
        return
    EPout = "01"
    mode = "%02x" %TUYA_SWITCH_MODE[mode]
    if "Model" in self.ListOfDevices[ NwkId ] and self.ListOfDevices[ NwkId ]["Model"] in ( "TS0002_relay_switch",):
        write_attribute(self, NwkId, ZIGATE_EP, EPout, TUYA_CLUSTER_EOO1_ID, "0000", "00", "d030", "30", mode, ackIsDisabled=False)
    else:
        write_attribute(self, NwkId, ZIGATE_EP, EPout, TUYA_CLUSTER_EOO1_ID, TUYA_TS0004_MANUF_CODE, "01", "d030", "30", mode, ackIsDisabled=False)


def tuya_TS0004_back_light(self, nwkid, mode):
    
    if int(mode) in {0, 1}:
        write_attribute(self, nwkid, ZIGATE_EP, "01", "0006", "0000", "00", "5000", "30", "%02x" %int(mode), ackIsDisabled=False)
    else:
        return


def tuya_TS0004_indicate_light(self, nwkid, mode):
    if int(mode) in {0, 1, 2}:
        write_attribute(self, nwkid, ZIGATE_EP, "01", "0006", "0000", "00", "8001", "30", "%02x" %int(mode), ackIsDisabled=False)
    else:
        return


def SmartRelayStatus_by_ep( self, nwkid, ep, mode):
    
    if int(mode) in {0, 1, 2}:
        return
    if ep not in self.ListOfDevices[nwkid]["Ep"]:
        self.log.logging("Heartbeat", "Error", "No ep: %s" %ep, nwkid)
        return
    if "e001" not in self.ListOfDevices[nwkid]["Ep"][ ep ]:
        self.log.logging("Heartbeat", "Log", "No Cluster: %s" %"e001", nwkid)
        return
    if "d010" not in self.ListOfDevices[nwkid]["Ep"][ ep ][ "e001" ]:
        self.log.logging("Heartbeat", "Log", "No Attribute: %s" %"d010", nwkid)

    write_attribute(self, nwkid, ZIGATE_EP, ep, "e001", "0000", "00", "d010", "30", "%02x" %int(mode), ackIsDisabled=False)


def SmartRelayStatus01(self, nwkid, mode):
    SmartRelayStatus_by_ep( self, nwkid, "01", mode)


def SmartRelayStatus02(self, nwkid, mode):
    SmartRelayStatus_by_ep( self, nwkid, "02", mode)


def SmartRelayStatus03(self, nwkid, mode): 
    SmartRelayStatus_by_ep( self, nwkid, "03", mode)


def SmartRelayStatus04(self, nwkid, mode):
    SmartRelayStatus_by_ep( self, nwkid, "04", mode)


def _check_tuya_attribute(self, nwkid, ep, cluster, attribute ):
    if ep not in self.ListOfDevices[nwkid]["Ep"]:
        self.log.logging("Heartbeat", "Log", "No ep: %s" %ep, nwkid)
        return False
    if cluster not in self.ListOfDevices[nwkid]["Ep"][ ep ]:
        self.log.logging("Heartbeat", "Log", "No Cluster: %s" %cluster, nwkid)
        return False
    if attribute not in self.ListOfDevices[nwkid]["Ep"][ ep ][ cluster ]:
        self.log.logging("Heartbeat", "Log", "No Attribute: %s" %attribute, nwkid)
        return False
    return True


def tuya_smoke_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):

    self.log.logging("Tuya", "Debug", "tuya_smoke_response - %s %s %s %s %s" % (NwkId, srcEp, dp, datatype, data), NwkId)
    if dp == 0x01:
        # State
        self.log.logging("Tuya", "Debug", "tuya_smoke_response - Smoke state %s %s %s" % (NwkId, srcEp, data), NwkId)
        store_tuya_attribute(self, NwkId, "SmokeState", data)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0500", data)

    elif dp == 0x0e:
        #  0: Low battery, 2:Full battery , 1: medium ????
        self.log.logging("Tuya", "Debug", "tuya_smoke_response - Battery Level %s %s %s" % (NwkId, srcEp, data), NwkId)
        store_tuya_attribute(self, NwkId, "Battery", data)
        if int(data,16) == 0:
            self.ListOfDevices[NwkId]["Battery"] = 25
            Update_Battery_Device(self, Devices, NwkId, 25) 
        elif int(data,16) == 1:
            self.ListOfDevices[NwkId]["Battery"] = 50
            Update_Battery_Device(self, Devices, NwkId, 50)
        else:
            self.ListOfDevices[NwkId]["Battery"] = 90
            Update_Battery_Device(self, Devices, NwkId, 90)

    elif dp == 0x04:
        # Tamper
        self.log.logging("Tuya", "Debug", "tuya_smoke_response - Tamper %s %s %s" % (NwkId, srcEp, data), NwkId)
        store_tuya_attribute(self, NwkId, "SmokeTamper", data)
        if int(data,16):
            MajDomoDevice(self, Devices, NwkId, srcEp, "0009", "01")
        else:
            MajDomoDevice(self, Devices, NwkId, srcEp, "0009", "00")

    else:
        self.log.logging("Tuya", "Debug", "tuya_smoke_response - Unknow %s %s %s %s %s" % (NwkId, srcEp, dp, datatype, data), NwkId)
        store_tuya_attribute(self, NwkId, "dp:%s-dt:%s" %(dp, datatype), data)


def tuya_command_f0( self, NwkId ):
    self.log.logging("Tuya", "Log", "Tuya 0xf0 command to  %s" %NwkId) 
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    payload = "11" + sqn + "f0"
    raw_APS_request(self, NwkId, "01", "0000", "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=False)   


def tuya_temphumi_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    
    self.log.logging("Tuya", "Debug", "tuya_temphumi_response - %s %s %s %s %s" % (NwkId, srcEp, dp, datatype, data), NwkId)
    manufacturer_name = self.ListOfDevices[NwkId].get('Manufacturer Name')

    if dp == 0x01:  # Temperature, 
        unsigned_value = int( data,16)
        signed_value = struct.unpack('>i', struct.pack('>I', unsigned_value))[0]

        store_tuya_attribute(self, NwkId, "Temp", signed_value)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0402", (signed_value / 10))
        checkAndStoreAttributeValue(self, NwkId, "01", "0402", "0000", (signed_value/ 10))

    elif dp == 0x02:   # Humi
        humi = int(data, 16)
        if manufacturer_name and manufacturer_name not in {'_TZE200_qoy0ekbd', '_TZE200_whkgqxse', '_TZE204_upagmta9'}:
            humi /= 10
        store_tuya_attribute(self, NwkId, "Humi", humi)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0405", humi)
        checkAndStoreAttributeValue(self, NwkId, "01", "0405", "0000", humi)

    elif dp == 0x04:   # Battery ????
        store_tuya_attribute(self, NwkId, "Battery", data)
        checkAndStoreAttributeValue(self, NwkId, "01", "0001", "0000", int(data, 16))
        self.ListOfDevices[NwkId]["Battery"] = int(data, 16)
        Update_Battery_Device(self, Devices, NwkId, int(data, 16))
        store_tuya_attribute(self, NwkId, "BatteryStatus", data)

    elif dp == 0x03:
        #  0: Low battery, 2:Full battery , 1: medium ????
        self.log.logging("Tuya", "Debug", "tuya_temphumi_response - Battery Level %s %s %s" % (NwkId, srcEp, data), NwkId)
        store_tuya_attribute(self, NwkId, "Battery", data)
        if int(data,16) == 0:
            self.ListOfDevices[NwkId]["Battery"] = 25
            Update_Battery_Device(self, Devices, NwkId, 25) 
        elif int(data,16) == 1:
            self.ListOfDevices[NwkId]["Battery"] = 50
            Update_Battery_Device(self, Devices, NwkId, 50)
        else:
            self.ListOfDevices[NwkId]["Battery"] = 90
            Update_Battery_Device(self, Devices, NwkId, 90)

    elif dp == 0x09:
        # Temp Unit
        self.log.logging("Tuya", "Debug", "tuya_temphumi_response - Temp Unit %s %s %s" % (NwkId, srcEp, data), NwkId)
        store_tuya_attribute(self, NwkId, "TempUnit", data)

        
    else:
        self.log.logging("Tuya", "Log", "tuya_temphumi_response - Unknow %s %s %s %s %s" % (NwkId, srcEp, dp, datatype, data), NwkId)
        store_tuya_attribute(self, NwkId, "dp:%s-dt:%s" %(dp, datatype), data)


def tuya_motion_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    
    self.log.logging("Tuya", "Debug", "tuya_motion_response - %s %s %s %s %s" % (NwkId, srcEp, dp, datatype, data), NwkId)

    if dp == 0x01:
        # Occupancy
        self.log.logging("Tuya", "Debug", "tuya_motion_response - Occupancy %s %s %s %s %s" % (NwkId, srcEp, dp, datatype, data), NwkId)
        # Looks like the Occupancy indicator is inverse
        occupancy = "%02x" %abs(int(data,16) -1 )
        store_tuya_attribute(self, NwkId, "Occupancy", data)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0406", occupancy )
        checkAndStoreAttributeValue(self, NwkId, "01", "0406", "0000", occupancy)

    elif dp == 0x04:
        # Battery
        self.log.logging("Tuya", "Debug", "tuya_motion_response - Battery %s %s %s %s %s" % (NwkId, srcEp, dp, datatype, data), NwkId)
        
        store_tuya_attribute(self, NwkId, "Battery", data)
        checkAndStoreAttributeValue(self, NwkId, "01", "0001", "0000", int(data, 16))
        self.ListOfDevices[NwkId]["Battery"] = int(data, 16)
        Update_Battery_Device(self, Devices, NwkId, int(data, 16))
        store_tuya_attribute(self, NwkId, "BatteryStatus", data)
  
    elif dp == 0x09:
        # Sensitivity - {'0': 'low', '1': 'medium', '2': 'high'}
        self.log.logging("Tuya", "Debug", "tuya_motion_response - Sensitivity %s %s %s %s %s" % (NwkId, srcEp, dp, datatype, data), NwkId)
        
        store_tuya_attribute(self, NwkId, "Sensitivity", data)
        
    elif dp == 0x0a:
        # Keep time - {'0': '10', '1': '30', '2': '60', '3': '120'}
        self.log.logging("Tuya", "Debug", "tuya_motion_response - Keep Time %s %s %s %s %s" % (NwkId, srcEp, dp, datatype, data), NwkId)
        
        store_tuya_attribute(self, NwkId, "KeepTime", data)
        
    elif dp == 0x0c:
        # Illuminance
        self.log.logging("Tuya", "Debug", "tuya_motion_response - Illuminance %s %s %s %s %s" % (NwkId, srcEp, dp, datatype, data), NwkId)
        
        store_tuya_attribute(self, NwkId, "Illuminance", data)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0400", (int(data, 16)) )
        checkAndStoreAttributeValue(self, NwkId, "01", "0400", "0000", int(data, 16))
   
    else:
        self.log.logging("Tuya", "Log", "tuya_motion_response - Unknow %s %s %s %s %s" % (NwkId, srcEp, dp, datatype, data), NwkId)
        store_tuya_attribute(self, NwkId, "dp:%s-dt:%s" %(dp, datatype), data)


def tuya_motion_zg204l_sensitivity(self, nwkid, sensitivity):
    # {'low': 0, 'medium': 1, 'high': 2}
    self.log.logging("tuyaSettings", "Debug", "tuya_motion_zg204l_keeptime - %s mode: %s" % (nwkid, sensitivity))
    if sensitivity not in (0x00, 0x01, 0x02):
        return
    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    action = "%02x04" % 0x09
    # determine which Endpoint
    EPout = "01"
    cluster_frame = "11"
    cmd = "00"  # Command
    data = "%02x" % sensitivity
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

    
def tuya_motion_zg204l_keeptime(self, nwkid, keep_time):
    # {'10': 0, '30': 1, '60': 2, '120': 3}
    self.log.logging("tuyaSettings", "Debug", "tuya_motion_zg204l_keeptime - %s mode: %s" % (nwkid, keep_time))
    if keep_time not in (0x00, 0x01, 0x02, 0x03 ):
        return
    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    action = "%02x04" % 0x0a
    # determine which Endpoint
    EPout = "01"
    cluster_frame = "11"
    cmd = "00"  # Command
    data = "%02x" % keep_time
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)
    

def tuya_radar_motion_sensitivity(self, nwkid, mode):
    # 00/35/0202000400000000
    self.log.logging("tuyaSettings", "Debug", "tuya_radar_motion_sensitivity - %s mode: %s" % (nwkid, mode))
    if mode > 7 and mode < 0 :
        self.log.logging("tuyaSettings", "Error", "tuya_radar_motion_sensitivity - %s Invalid sensitivity: %s" % (nwkid, mode))
        return 
    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    action = "%02x02" % 0x02
    # determine which Endpoint
    EPout = "01"
    cluster_frame = "11"
    cmd = "00"  # Command
    data = "%08x" % mode
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_radar_motion_radar_min_range(self, nwkid, mode):
    
    self.log.logging("tuyaSettings", "Debug", "tuya_radar_motion_radar_min_range - %s mode: %s" % (nwkid, mode))
    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    action = "%02x02" % 0x03
    # determine which Endpoint
    EPout = "01"
    cluster_frame = "11"
    cmd = "00"  # Command
    data = "%08x" % mode
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

        
def tuya_radar_motion_radar_max_range(self, nwkid, mode):
    
    self.log.logging("tuyaSettings", "Debug", "tuya_radar_motion_radar_max_range - %s mode: %s" % (nwkid, mode))
    if mode > ( 10 * 100):
        self.log.logging("tuyaSettings", "Error", "tuya_radar_motion_radar_max_range - %s Invalid max range: %s cm" % (nwkid, mode))
        return 

    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    action = "%02x02" % 0x04
    # determine which Endpoint
    EPout = "01"
    cluster_frame = "11"
    cmd = "00"  # Command
    data = "%08x" % mode
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

        
def tuya_radar_motion_radar_detection_delay(self, nwkid, mode):
    
    self.log.logging("tuyaSettings", "Debug", "tuya_radar_motion_radar_detection_delay - %s mode: %s" % (nwkid, mode))
    if mode > 100 and mode < 0:
        self.log.logging("tuyaSettings", "Error", "tuya_radar_motion_radar_detection_delay - %s Invalid delay: %s" % (nwkid, mode))
        return 

    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    action = "%02x02" % 0x65
    # determine which Endpoint
    EPout = "01"
    cluster_frame = "11"
    cmd = "00"  # Command
    data = "%08x" % mode
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

        
def tuya_radar_motion_radar_fading_time(self, nwkid, mode):
    
    self.log.logging("tuyaSettings", "Debug", "tuya_radar_motion_radar_fading_time - %s mode: %s" % (nwkid, mode))
    if mode > 15000 and mode < 0:
        self.log.logging("tuyaSettings", "Error", "tuya_radar_motion_radar_fading_time - %s Invalid delay: %s" % (nwkid, mode))
        return 

    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    action = "%02x02" % 0x66
    # determine which Endpoint
    EPout = "01"
    cluster_frame = "11"
    cmd = "00"  # Command
    data = "%08x" % mode
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_smart_door_lock(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):

    store_tuya_attribute(self, NwkId, "dp:%s-dt:%s" %(dp, datatype), data)

    if dp == 8:
        store_tuya_attribute(self, NwkId, "Open Or Close-%s" %(datatype), data)
    elif dp == 9:
        store_tuya_attribute(self, NwkId, "Alarm-%s" %(datatype), data)
    elif dp == 10:
        # %
        store_tuya_attribute(self, NwkId, "Battery-%s" %(datatype), data)
        Update_Battery_Device(self, Devices, NwkId, int(data, 16))
    elif dp == 12:
        store_tuya_attribute(self, NwkId, "Reverse Lock-%s" %(datatype), data)
    elif dp == 14:
        store_tuya_attribute(self, NwkId, "Doorbell-%s" %(datatype), data)
    elif dp == 16:
        store_tuya_attribute(self, NwkId, "SwitchDirection-%s" %(datatype), data)
    elif dp == 19:
        store_tuya_attribute(self, NwkId, "AutoLockTime-%s" %(datatype), data)
    elif dp == 38:
        store_tuya_attribute(self, NwkId, "Unlocked-%s" %(datatype), data)
    elif dp == 40:
        store_tuya_attribute(self, NwkId, "App Unlock Without Password-%s" %(datatype), data)
    elif dp == 41:
        store_tuya_attribute(self, NwkId, "App Unlock-%s" %(datatype), data)
    elif dp == 101:
        store_tuya_attribute(self, NwkId, "Auxiliary opening/locking-%s" %(datatype), data)


def ts110e_light_type( self, NwkId, mode):
    # led: 0, incandescent: 1, halogen: 2
    self.log.logging("tuyaSettings", "Debug", "ts110e_light_type - mode %s" % mode, NwkId)
    EPout = "01"
    mode = "%02x" %mode
    write_attribute(self, NwkId, ZIGATE_EP, EPout, "0008", "0000", "00", "fc02", "20", mode, ackIsDisabled=False)


def ts110e_switch01_type( self, NwkId, mode):
    ts110e_switch_type( self, NwkId, "01", mode)


def ts110e_switch02_type( self, NwkId, mode):
    ts110e_switch_type( self, NwkId, "02", mode)


def ts110e_switch_type( self, NwkId, EPout, mode):
    # momentary: 0, toggle: 1, state: 2
    self.log.logging("tuyaSettings", "Debug", "ts110e_switch_type - mode %s" % mode, NwkId)
    mode = "%02x" %mode
    write_attribute(self, NwkId, ZIGATE_EP, EPout, "0008", "0000", "00", "fc02", "20", mode, ackIsDisabled=False)


def tuya_lighting_color_control( self, NwkId, ColorCapabilities=25):
    # The ColorCapabilities attribute specifies the color capabilities of the device supporting the color control clus-
    # ter, as illustrated in Table 5.8. If a bit is set to 1, the corresponding attributes and commands SHALL become
    # mandatory. If a bit is set to 0, the corresponding attributes and commands need not be implemented.
    
    self.log.logging("Tuya", "Debug", "tuya_lighting_color_control - Color Capabilities %s" % ColorCapabilities, NwkId)
    write_attribute( self, NwkId, ZIGATE_EP, "01", "0300", "0000", "00", "400a", "19", "%04x" %ColorCapabilities, ackIsDisabled=False )
    self.log.logging("Tuya", "Debug", "tuya_lighting_color_control - Color Capabilities %s completed" % ColorCapabilities, NwkId)
        
    
def tuya_color_control_rgbMode( self, NwkId, mode):
    # Command 0xfe: Set mode (Tuya-specific command)
    # Change the mode.
    #    0: White light
    #    1: Colored light
    #    2: Scene
    #    3: Music
    # https://developer.tuya.com/en/docs/connect-subdevices-to-gateways/tuya-zigbee-lighting-access-standard?id=K9ik6zvod83fi#title-7-Color%20Control%20cluster

    self.log.logging("Tuya", "Debug", "tuya_color_control_rgbMode", NwkId)
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    payload = "11" + sqn + "f0" + mode
    raw_APS_request(self, NwkId, "01", "0300", "0104", payload, zigpyzqn=sqn, zigate_ep=ZIGATE_EP, ackIsDisabled=False)


def tuya_Move_To_Hue_Saturation( self, NwkId, EPout, hue, saturation, transition, level):
    # Command 0x06
    self.log.logging("Tuya", "Debug", "tuya_Move_To_Hue_Saturation", NwkId)
    
    hue = "%02x" % hue
    saturation = "%02x" % saturation

    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    payload = "11" + sqn + "06" + hue + saturation + "0000" + "%02x" %level
    
    raw_APS_request(self, NwkId, EPout, "0300", "0104", payload, zigpyzqn=sqn, zigate_ep=ZIGATE_EP, ackIsDisabled=False)


def tuya_Move_To_Hue_Saturation_Brightness( self, NwkId, epout, hue, saturation, brightness):
    # Command 0xe1
    self.log.logging("Tuya", "Debug", "tuya_Move_To_Hue_Saturation_Brightness", NwkId)
    
    saturation = "%04x" % struct.unpack("H", struct.pack(">H", saturation))[0]
    hue = "%04x" % struct.unpack("H", struct.pack(">H", hue, ))[0]
    brightness = "%04x" % struct.unpack("H", struct.pack(">H", brightness))[0]
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    payload = "11" + sqn + "e1" + hue + saturation + brightness
    
    raw_APS_request(self, NwkId, epout, "0300", "0104", payload, zigpyzqn=sqn, zigate_ep=ZIGATE_EP, ackIsDisabled=False)


def tuya_color_grandiant(self, NwkId, on_gradiant=None, off_gradiant=None):
    """ Tuya specific command which allows to define the gradiant time to switch On and to Switch off """

    self.log.logging("tuyaSettings", "Debug", f"tuya_color_grandiant {NwkId}, {on_gradiant}, {off_gradiant}", NwkId)

    on_gradiant = get_device_config_param( self, NwkId, "TuyaColorGradiantOnTime") or 10
    off_gradiant = get_device_config_param( self, NwkId, "TuyaColorGradiantOffTime") or 10

    cmd = "fb"
    epout = "01"
    sqn = get_and_inc_ZCL_SQN(self, NwkId)

    # gradiant should be expressed in tenth of second, while Tuya expect 1s = 1000
    on_gradiant *= 100
    off_gradiant *= 100

    payload = "11" + sqn + cmd + "%08x" % on_gradiant + "%06x" %off_gradiant

    self.log.logging("tuyaSettings", "Debug", f"tuya_color_grandiant {NwkId}, {epout}, payload: {payload}", NwkId)
    raw_APS_request(self, NwkId, epout, "0300", "0104", payload, zigpyzqn=sqn, zigate_ep=ZIGATE_EP, ackIsDisabled=False)


def ts0224_alarm_volume(self, nwkid, volume=0):
    self.log.logging("tuyaSettings", "Debug", f"ts0224_alarm_volume {nwkid}, Volume: {volume}", nwkid)

    # Volume: 0: Mute, 50 High, 30 Medium, 10 Low
    valid_values = [0, 10, 30, 50]
    if volume not in valid_values:
        volume = min(valid_values, key=lambda x: abs(x - volume))
        self.log.logging("tuyaSettings", "Debug", f"ts0224_alarm_volume {nwkid}, Volume: {volume} corrected as invalid", nwkid)
    write_attribute( self, nwkid, ZIGATE_EP, "01", "0502", "0000", "00", "0002","20", "%02x" %volume, ackIsDisabled=False, )


TUYA_DEVICE_PARAMETERS = {
    "TuyaColorGradiantOnTime": tuya_color_grandiant,
    "TuyaColorGradiantOffTime": tuya_color_grandiant,
    "LightIndicator": tuya_switch_indicate_light,
    "TuyaEnergyChildLock": tuya_energy_childLock,
    "TuyaMotoReversal": tuya_window_cover_motor_reversal,
    "TuyaBackLight": tuya_backlight_command,
    "TuyaCurtainMode": tuya_curtain_mode,
    "TuyaCalibrationTime": tuya_window_cover_calibration,
    "TS004FMode": tuya_cmd_ts004F,
    "moesCalibrationTime": tuya_window_cover_calibration,
    "TuyaGarageOpenerRunTime": tuya_garage_run_time,
    "TuyaSwitchMode": tuya_external_switch_mode,
    "SmartSwitchBackLight": tuya_TS0004_back_light,
    "SmartSwitchIndicateLight": tuya_TS0004_indicate_light,  
    "SmartRelayStatus01": SmartRelayStatus01,
    "SmartRelayStatus02": SmartRelayStatus02,
    "SmartRelayStatus03": SmartRelayStatus03,
    "SmartRelayStatus04": SmartRelayStatus04,
    "ZG204Z_MotionSensivity": tuya_motion_zg204l_sensitivity,
    "ZG204Z_MotionOccupancyTime": tuya_motion_zg204l_keeptime,
    "RadarMotionSensitivity": tuya_radar_motion_sensitivity,
    "RadarMotionMinRange": tuya_radar_motion_radar_min_range,
    "RadarMotionMaxRange": tuya_radar_motion_radar_max_range,
    "RadarMotionDelay": tuya_radar_motion_radar_detection_delay,
    "RadarMotionFading": tuya_radar_motion_radar_fading_time,
    "TuyaPIRKeepTime": tuya_pir_keep_time_lookup,
    "TS110ELightType": ts110e_light_type,
    "TS110ESwitch01Type": ts110e_switch01_type,
    "TS110ESwitch02Type": ts110e_switch02_type,
    "TuyaTS0224AlarmVolume": ts0224_alarm_volume
}
