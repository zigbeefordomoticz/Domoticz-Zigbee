#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: tuya.py

    Description: Tuya specific

"""
# https://github.com/zigpy/zha-device-handlers/issues/357

import Domoticz

from Modules.basicOutputs import raw_APS_request, write_attribute
from Modules.domoMaj import MajDomoDevice
from Modules.domoTools import Update_Battery_Device
from Modules.tools import (checkAndStoreAttributeValue, get_and_inc_ZCL_SQN,
                           is_ack_tobe_disabled, voltage2batteryP)
from Modules.tuyaTools import (get_tuya_attribute, store_tuya_attribute,
                               tuya_cmd)
from Modules.zigateConsts import ZIGATE_EP

TUYA_eTRV_MODEL = (
    "TS0601",
    "TS0601-eTRV",
    "TS0601-eTRV1",
    "TS0601-eTRV2",
    "TS0601-eTRV3",
    "TS0601-_TZE200_b6wax7g0",      # BRT-100  MOES by Tuya
    "TS0601-_TZE200_chyvmhay",      # Lidl Valve
    "TS0601-thermostat",
    "uhszj9s",
    "GbxAXL2",
    "88teujp",
    "kud7u2l",
    "eaxp72v",
    "fvq6avy",
    "ivfvd7h",
)

eTRV_MODELS = {
    # Thermostat
    "TS0601-thermostat": "TS0601-thermostat",
    
    # Siterwell GS361A-H04
    "ivfvd7h": "TS0601-eTRV1",
    "fvq6avy": "TS0601-eTRV1",
    "eaxp72v": "TS0601-eTRV1",
    "TS0601-eTRV1": "TS0601-eTRV1",
    
    # Moes HY368 / HY369
    "kud7u2l": "TS0601-eTRV2",
    "TS0601-eTRV2": "TS0601-eTRV2",
    
    # Saswell SEA802 / SEA801 Zigbee versions
    "88teujp": "TS0601-eTRV3",
    "GbxAXL2": "TS0601-eTRV3",
    "uhszj9s": "TS0601-eTRV3",
    "TS0601-eTRV3": "TS0601-eTRV3",
    
    # MOES BRT-100
    "TS0601-_TZE200_b6wax7g0": "TS0601-_TZE200_b6wax7g0",
    
    # Lidl Valve
    "TS0601-_TZE200_chyvmhay": "TS0601-_TZE200_chyvmhay"
}


def tuya_eTRV_registration(self, nwkid, device_reset=False):

    self.log.logging("Tuya", "Debug", "tuya_eTRV_registration - Nwkid: %s" % nwkid)
    # (1) 3 x Write Attribute Cluster 0x0000 - Attribute 0xffde  - DT 0x20  - Value: 0x13
    EPout = "01"
    write_attribute(self, nwkid, ZIGATE_EP, EPout, "0000", "0000", "00", "ffde", "20", "13", ackIsDisabled=False)

    # (3) Cmd 0x03 on Cluster 0xef00  (Cluster Specific)
    if device_reset and get_model_name(self, nwkid) not in ("TS0601-thermostat",):
        payload = "11" + get_and_inc_ZCL_SQN(self, nwkid) + "03"
        raw_APS_request(
            self,
            nwkid,
            EPout,
            "ef00",
            "0104",
            payload,
            zigate_ep=ZIGATE_EP,
            ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
        )
    if get_model_name(self, nwkid) in ("TS0601-_TZE200_b6wax7g0",):
        EPout = "01"
        payload = "11" + get_and_inc_ZCL_SQN(self, nwkid) + "10" + "0002"
        raw_APS_request(
            self,
            nwkid,
            EPout,
            "ef00",
            "0104",
            payload,
            zigate_ep=ZIGATE_EP,
            ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
        )

def receive_setpoint(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):

    setpoint = int(data, 16)
    self.log.logging("Tuya", "Debug", "receive_setpoint - Nwkid: %s/%s Setpoint: %s for model taget: %s" % (NwkId, srcEp, setpoint, model_target))
    if model_target in[ "TS0601-thermostat","TS0601-_TZE200_b6wax7g0"] :
        setpoint = int(data, 16)
    elif model_target in [ "TS0601-_TZE200_chyvmhay", ]:
        setpoint = int(data,16) / 2
    else:
        setpoint = int(data, 16) / 10
    self.log.logging("Tuya", "Debug", "receive_setpoint - After Nwkid: %s/%s Setpoint: %s for model taget: %s" % (NwkId, srcEp, setpoint, model_target))
        
    MajDomoDevice(self, Devices, NwkId, srcEp, "0201", setpoint, Attribute_="0012")
    checkAndStoreAttributeValue(self, NwkId, "01", "0201", "0012", int(data, 16) * 10)
    store_tuya_attribute(self, NwkId, "SetPoint", data)


def receive_temperature(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya", "Debug", "receive_temperature - Nwkid: %s/%s Temperature: %s" % (NwkId, srcEp, int(data, 16))
    )
    MajDomoDevice(self, Devices, NwkId, srcEp, "0402", (int(data, 16) / 10))
    checkAndStoreAttributeValue(self, NwkId, "01", "0402", "0000", int(data, 16))
    store_tuya_attribute(self, NwkId, "Temperature", data)


def receive_onoff(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging("Tuya", "Debug", "receive_onoff - Nwkid: %s/%s Mode to OffOn: %s" % (NwkId, srcEp, data))
    store_tuya_attribute(self, NwkId, "Switch", data)

    # Update ThermoOnOff widget ( 6501 )
    if model_target in ["TS0601-thermostat", "TS0601-eTRV3"]:
        store_tuya_attribute(self, NwkId, "Switch", data)
        if data == "00":
            checkAndStoreAttributeValue(self, NwkId, "01", "0201", "6501", "Off")
            MajDomoDevice(self, Devices, NwkId, srcEp, "0201", 0, Attribute_="6501")  # ThermoOnOff to Off
            MajDomoDevice(self, Devices, NwkId, srcEp, "0201", 0, Attribute_="001c")  # ThermoMode_2 to Off
        else:
            checkAndStoreAttributeValue(self, NwkId, "01", "0201", "6501", "On")
            MajDomoDevice(self, Devices, NwkId, srcEp, "0201", 1, Attribute_="6501")  # ThermoOnOff to On

    else:
        checkAndStoreAttributeValue(self, NwkId, "01", "0201", "6501", data)


def receive_mode(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya", "Debug", "receive_mode - Nwkid: %s/%s Dp: %s DataType: %s Mode: %s" % (NwkId, srcEp, dp, datatype, data)
    )
    store_tuya_attribute(self, NwkId, "Mode", data)


def receive_preset(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    # Update ThermoMode_2 widget ( 001c)
    self.log.logging(
        "Tuya",
        "Debug",
        "receive_preset - Nwkid: %s/%s Dp: %s DataType: %s Mode: %s" % (NwkId, srcEp, dp, datatype, data),
    )
    store_tuya_attribute(self, NwkId, "ChangeMode", data)

    if data == "00":
        if get_model_name(self, NwkId) == "TS0601-eTRV3":
            # Mode Manual
            self.log.logging("Tuya", "Debug", "receive_preset - Nwkid: %s/%s Mode to Manual" % (NwkId, srcEp))
            MajDomoDevice(self, Devices, NwkId, srcEp, "0201", 2, Attribute_="001c")
            checkAndStoreAttributeValue(self, NwkId, "01", "0201", "001c", "Manual")
        else:
            # Offline
            self.log.logging("Tuya", "Debug", "receive_preset - Nwkid: %s/%s Mode to Offline" % (NwkId, srcEp))
            MajDomoDevice(self, Devices, NwkId, srcEp, "0201", 0, Attribute_="001c")
            checkAndStoreAttributeValue(self, NwkId, "01", "0201", "001c", "OffLine")

    elif data == "01":
        # Auto
        self.log.logging("Tuya", "Debug", "receive_preset - Nwkid: %s/%s Mode to Auto" % (NwkId, srcEp))
        MajDomoDevice(self, Devices, NwkId, srcEp, "0201", 1, Attribute_="001c")
        checkAndStoreAttributeValue(self, NwkId, "01", "0201", "001c", "Auto")

    elif data == "02":
        # Manual
        self.log.logging("Tuya", "Debug", "receive_preset - Nwkid: %s/%s Mode to Manual" % (NwkId, srcEp))
        MajDomoDevice(self, Devices, NwkId, srcEp, "0201", 2, Attribute_="001c")
        checkAndStoreAttributeValue(self, NwkId, "01", "0201", "001c", "Manual")

def receive_LIDLMode(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya",
        "Debug",
        "receive_receive_LIDLMode - Nwkid: %s/%s Dp: %s DataType: %s Mode: %s" % (NwkId, srcEp, dp, datatype, data),
    )
    store_tuya_attribute(self, NwkId, "LIDLMode", data)

    self.log.logging("Tuya", "Debug", "receive_LIDLMode - Nwkid: %s/%s Mode %s" % (NwkId, srcEp, data))
    MajDomoDevice(self, Devices, NwkId, srcEp, "0201", int(data,16) + 1, Attribute_="001c")
    checkAndStoreAttributeValue(self, NwkId, "01", "0201", "001c", "%02x" %( int(data,16) + 1))
    
def receive_manual_mode(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    # Specific to Thermostat.
    # Indicate if the Manual mode is On or Off
    # Update ThermoMode_2 widget ( 001c)
    self.log.logging(
        "Tuya",
        "Debug",
        "receive_manual_mode - Nwkid: %s/%s Dp: %s DataType: %s ManualMode: %s" % (NwkId, srcEp, dp, datatype, data),
    )
    store_tuya_attribute(self, NwkId, "ManualMode", data)
    if data == "00":
        # Thermostat Mode Auto / As Manual mode is Off
        self.log.logging("Tuya", "Debug", "receive_manual_mode - Nwkid: %s/%s Manual Mode Off" % (NwkId, srcEp))
        MajDomoDevice(self, Devices, NwkId, srcEp, "0201", 2, Attribute_="001c")
        checkAndStoreAttributeValue(self, NwkId, "01", "0201", "001c", "Manual")


def receive_schedule_mode(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    # Specific to Thermostat.
    # Indicate if the Schedule mode is On or Off
    # Update ThermoMode_2 widget ( 001c)
    self.log.logging(
        "Tuya",
        "Debug",
        "receive_schedule_mode - Nwkid: %s/%s Dp: %s DataType: %s ScheduleMode: %s"
        % (NwkId, srcEp, dp, datatype, data),
    )
    store_tuya_attribute(self, NwkId, "ScheduleMode", data)
    if data == "00":
        self.log.logging("Tuya", "Debug", "receive_schedule_mode - Nwkid: %s/%s ScheduleMode Off" % (NwkId, srcEp))
        MajDomoDevice(self, Devices, NwkId, srcEp, "0201", 1, Attribute_="001c")
        checkAndStoreAttributeValue(self, NwkId, "01", "0201", "001c", "Auto")
        return


def receive_childlock(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging("Tuya", "Debug", "receive_childlock - Nwkid: %s/%s Child Lock/Unlock: %s" % (NwkId, srcEp, data))
    store_tuya_attribute(self, NwkId, "ChildLock", data)


def receive_windowdetection(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging("Tuya", "Debug", "receive_windowdetection - Nwkid: %s/%s Window Open: %s" % (NwkId, srcEp, data))
    if model_target in  ("TS0601-_TZE200_b6wax7g0",):
        data = "00" if data == "01" else "01"
    MajDomoDevice(self, Devices, NwkId, srcEp, "0500", data)
    store_tuya_attribute(self, NwkId, "OpenWindow", data)


def receive_windowdetection_status(
    self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data
):
    self.log.logging(
        "Tuya", "Debug", "receive_windowdetection_status - Nwkid: %s/%s Window Open: %s" % (NwkId, srcEp, data)
    )
    store_tuya_attribute(self, NwkId, "OpenWindowDetection", data)


def receive_valvestate(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya",
        "Debug",
        "receive_valvestate - Nwkid: %s/%s Valve Detection: %s %s" % (NwkId, srcEp, data, int(data, 16)),
    )
    store_tuya_attribute(self, NwkId, "ValveDetection", data)


def receive_battery(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    # Works for ivfvd7h model , _TYST11_zivfvd7h Manufacturer
    self.log.logging(
        "Tuya", "Debug", "receive_battery - Nwkid: %s/%s Battery status %s" % (NwkId, srcEp, int(data, 16))
    )
    if model_target == "TS0601-_TZE200_chyvmhay":
        # We received a voltage
        voltage = int(data,16) / 100
        percentage = voltage2batteryP(voltage * 100, 150, 100)
        checkAndStoreAttributeValue(self, NwkId, "01", "0001", "0000", voltage)
        checkAndStoreAttributeValue(self, NwkId, "01", "0001", "0010", voltage)
        checkAndStoreAttributeValue(self, NwkId, "01", "0001", "0020", voltage)
        checkAndStoreAttributeValue(self, NwkId, "01", "0001", "0021", percentage)
    else:
        checkAndStoreAttributeValue(self, NwkId, "01", "0001", "0000", int(data, 16))
        self.ListOfDevices[NwkId]["Battery"] = int(data, 16)
        Update_Battery_Device(self, Devices, NwkId, int(data, 16))
        store_tuya_attribute(self, NwkId, "BatteryStatus", data)


def receive_battery_state(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging("Tuya", "Debug", "receive_battery_state - Nwkid: %s/%s Battery state %s" % (NwkId, srcEp, data))
    # checkAndStoreAttributeValue( self, NwkId , '01', '0001', '0000' , int(data,16) )
    # self.ListOfDevices[ NwkId ]['Battery'] = int(data,16)
    store_tuya_attribute(self, NwkId, "BatteryState", data)


def receive_temporary_away(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging("Tuya", "Debug", "receive_temporary_away - Nwkid: %s/%s Status %s" % (NwkId, srcEp, data))
    store_tuya_attribute(self, NwkId, "TemporaryAway", data)


def receive_antiscale(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging("Tuya", "Debug", "receive_antiscale - Nwkid: %s/%s Status %s" % (NwkId, srcEp, data))
    store_tuya_attribute(self, NwkId, "AntiScale", data)


def receive_lowbattery(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya",
        "Debug",
        "receice_lowbattery - Nwkid: %s/%s DataType: %s Battery status %s" % (NwkId, srcEp, datatype, int(data, 16)),
    )
    store_tuya_attribute(self, NwkId, "LowBattery", data)


def receive_heating_state(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    # Thermostat
    self.log.logging("Tuya", "Debug", "receive_heating_state - Nwkid: %s/%s HeatingMode: %s" % (NwkId, srcEp, data))
    # Value inverted
    value = 1 if data == "00" else 0
    MajDomoDevice(self, Devices, NwkId, srcEp, "0201", value, Attribute_="0124")
    store_tuya_attribute(self, NwkId, "HeatingMode", data)


def receive_valveposition(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya", "Debug", "receive_valveposition - Nwkid: %s/%s Valve position: %s" % (NwkId, srcEp, int(data, 16))
    )
    MajDomoDevice(self, Devices, NwkId, srcEp, "0201", int(data, 16), Attribute_="026d")
    store_tuya_attribute(self, NwkId, "ValvePosition", data)


def receive_calibration(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya", "Debug", "receive_calibration - Nwkid: %s/%s Calibration: %s" % (NwkId, srcEp, int(data, 16))
    )
    store_tuya_attribute(self, NwkId, "Calibration", data)


def receive_program_mode(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya", "Debug", "receive_program_mode - Nwkid: %s/%s Program Mode: %s" % (NwkId, srcEp, int(data, 16))
    )
    store_tuya_attribute(self, NwkId, "TrvMode", data)


def receive_antifreeze(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya", "Debug", "receive_antifreeze - Nwkid: %s/%s AntiFreeze: %s" % (NwkId, srcEp, int(data, 16))
    )
    store_tuya_attribute(self, NwkId, "AntiFreeze", data)


def receive_sensor_mode(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya", "Debug", "receive_sensor_mode - Nwkid: %s/%s AntiFreeze: %s" % (NwkId, srcEp, int(data, 16))
    )
    store_tuya_attribute(self, NwkId, "SensorMode", data)


def receive_schedule(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    # Thanks to smanar for the decoding
    self.log.logging("Tuya", "Debug", "receive_schedule - Nwkid: %s/%s data: %s" % (NwkId, srcEp, data))

    if dp == 0x70:  # Workday
        store_tuya_attribute(self, NwkId, "Schedule_Workday", data)

    elif dp == 0x71:  # Holiday
        store_tuya_attribute(self, NwkId, "Schedule_Holiday", data)

    elif dp == 0x7B:  # Sunday
        store_tuya_attribute(self, NwkId, "Schedule_Sunday", decode_schedule_day(dp, data))
    elif dp == 0x7C:  # Monday
        store_tuya_attribute(self, NwkId, "Schedule_Monday", decode_schedule_day(dp, data))
    elif dp == 0x7D:  # Thuesday
        store_tuya_attribute(self, NwkId, "Schedule_Tuesday", decode_schedule_day(dp, data))
    elif dp == 0x7E:  # Wednesday
        store_tuya_attribute(self, NwkId, "Schedule_Wednesday", decode_schedule_day(dp, data))
    elif dp == 0x7F:  # Thursday
        store_tuya_attribute(self, NwkId, "Schedule_Thursday", decode_schedule_day(dp, data))
    elif dp == 0x80:  # Friday
        store_tuya_attribute(self, NwkId, "Schedule_Friday", decode_schedule_day(dp, data))
    elif dp == 0x81:  # Saturday
        store_tuya_attribute(self, NwkId, "Schedule_Saturday", decode_schedule_day(dp, data))

def receive_moe_schedule(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    # 00/11/  
    # Cmd: 65
    # Dt: 00
    # 0024
    #                    Period1  Period2   Period 3   Period 4
    # Monday to Friday : 0600/28/ 0800/1e/  1100/2c/   1600/1e
    # Saturday:          0600/28/ 0800/1e/  1100/2c/   1600/1e
    # Sunday:            0600/28/ 0800/1e/  1100/2c/   1600/1e
    # 0600-28/ 0b1e-2a/ 0d1e-2c 111e-2e
    # 0600-30/ 0c00-2e/ 0e1e-2c 111e-2a
    # 0600-26/ 0c1e-28/ 0e1e-2a 121e-28
    Domoticz.Log("receive_moe_schedule( %s )" %data) 
    schedule = {'Monday Friday': decode_moes_plan(data[:24])}
    schedule['Saturday'] = decode_moes_plan(data[24:48])
    schedule['Sunday'] = decode_moes_plan(data[48:72])
    store_tuya_attribute(self, NwkId, "Schedule", schedule )
        
def decode_moes_plan( data ):
    Domoticz.Log("decode_moes_plan( %s )" %data) 
    return {
        'Period1': decode_moes_period( data[:6] ),
        'Period2': decode_moes_period( data[6:12]) ,
        'Period3': decode_moes_period( data[12:18]) ,
        'Period4': decode_moes_period( data[18:24]),
    }

def decode_moes_period( data ):
    Domoticz.Log("decode_moes_period( %s )" %data)    
    return {
        'Start': data[:4],
        'Setpoint': int(data[4:6],16)
    } 
    
def decode_schedule_day(dp, data):

    return_value = {}
    if dp >= 0x7B and dp <= 0x81:
        #  Daily schedule (mode 8)(minut 16)(temperature 16)(minut 16)(temperature 16)(minut 16)(temperature 16)(minut 16)(temperature 16)
        # 04 0168 00c8 01e0 00a0 0438 00c8 0528 00a0

        schedule = {}
        idx = 0
        return_value["Mode"] = data[idx : idx + 2]
        idx += 2
        while idx < len(data):
            minutes = int(data[idx : idx + 4], 16)
            idx += 4
            setpoint = (int(data[idx : idx + 4], 16)) / 10
            idx += 4
            plug_hour = minutes // 60
            plug_min = minutes - (60 * plug_hour)
            cnt = "T%s" % len(schedule)
            schedule[cnt] = "%s:%s %s" % (plug_hour, plug_min, setpoint)
        return_value["Schedule"] = schedule

    return return_value

def receive_brt100_mode(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    # 0x00 - Auto, 0x01 - Manual, 0x02 - Temp Hand, 0x03 - Holliday
    BRT_MODE = {
        0x00: 'Auto',
        0x01: "Manual",
        0x02: "TemporaryManual",
        0x03: "Holidays",
    }

    self.log.logging(
        "Tuya", "Debug", "receive_brt100_mode - Nwkid: %s/%s : %s" % (NwkId, srcEp, int(data, 16))
    )
    mode = BRT_MODE.get(int(data, 16), int(data, 16))
    store_tuya_attribute(self, NwkId, "BRTMode", mode )
    MajDomoDevice(self, Devices, NwkId, srcEp, "0201", int(data, 16) + 1, Attribute_="001c")

def receive_rapid_heating_status(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya", "Debug", "receive_rapid_heating_status - Nwkid: %s/%s : %s" % (NwkId, srcEp, int(data, 16))
    )
    store_tuya_attribute(self, NwkId, "RapidHeating", data)

def receive_boost_time(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya", "Debug", "receive_boost_time - Nwkid: %s/%s : %s" % (NwkId, srcEp, int(data, 16))
    )
    store_tuya_attribute(self, NwkId, "BoostTime", data)
    
def receive_eco_temperature(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya", "Debug", "receive_boost_time - Nwkid: %s/%s : %s" % (NwkId, srcEp, int(data, 16))
    )
    store_tuya_attribute(self, NwkId, "EcoTemp", data)

def receive_max_temperature(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya", "Debug", "receive_max_temperature - Nwkid: %s/%s : %s" % (NwkId, srcEp, int(data, 16))
    )
    store_tuya_attribute(self, NwkId, "MaxSetpoint", data)

def receive_min_temperature(self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya", "Debug", "receive_min_temperature - Nwkid: %s/%s : %s" % (NwkId, srcEp, int(data, 16))
    )
    store_tuya_attribute(self, NwkId, "MinSetpoint", data)


eTRV_MATRIX = {
    "TS0601-thermostat": {
        # Thermostat Manual --> Auto
        #       Dp: 0x02 / 0x01 -- Manual Off
        #       Dp: 0x03 / 0x00 -- Schedule On
        # Thermostat Auto ---> Manual
        #       Dp: 0x02 / 0x00 -- Manual On
        #       Dp: 0x03 / 0x01 -- Manual Off

        "FromDevice": {  # @d2e2n2o / Electric
            0x01: receive_onoff,  # Ok - On / Off
            0x02: receive_manual_mode,
            0x03: receive_schedule_mode,
            0x10: receive_setpoint,  # Ok
            0x18: receive_temperature,  # Ok
            0x1b: receive_calibration,
            0x24: receive_heating_state,
            0x28: receive_childlock,
            0x1B: receive_calibration,
            0x2B: receive_sensor_mode,
        },
        "ToDevice": {
            "Switch": 0x01,  # Ok On / Off
            "ManualMode": 0x02,  # ????
            "ScheduleMode": 0x03,  # 01 Manual, 00 Schedule
            "SetPoint": 0x10,  # Ok
            "Calibration": 0x1B,
            "ChildLock": 0x28,
            "Calibration": 0x1B,
            "SensorMode": 0x2B,
        },
    },
    # eTRV
    "TS0601-eTRV1": {
        "FromDevice": {  # Confirmed with @d2e2n2o _TYST11_zivfvd7h
            0x02: receive_setpoint,
            0x03: receive_temperature,
            0x04: receive_preset,
            0x15: receive_battery,
        },
        "ToDevice": {"SetPoint": 0x02, "TrvMode": 0x04},
    },
    "TS0601-eTRV2": {
        "FromDevice": {  # https://github.com/pipiche38/Domoticz-Zigate/issues/779 ( @waltervl)
            0x02: receive_setpoint,
            0x03: receive_temperature,
            0x04: receive_preset,
            0x07: receive_childlock,
            0x12: receive_windowdetection,
            0x14: receive_valvestate,
            0x15: receive_battery,
            0x2C: receive_calibration,
            0x6D: receive_valveposition,
            0x6E: receive_lowbattery,
        },
        "ToDevice": {"SetPoint": 0x02, "TrvMode": 0x04, "Calibration": 0x2C},
    },
    "TS0601-eTRV3": {
        "FromDevice": {  # Confirmed with @d2e2n2o et @pipiche
            0x08: receive_windowdetection_status,
            0x12: receive_windowdetection,
            0x1B: receive_calibration,
            0x28: receive_childlock,
            0x65: receive_onoff,
            0x66: receive_temperature,
            0x67: receive_setpoint,
            0x6A: receive_temporary_away,
            0x6C: receive_preset,
            0x6D: receive_valveposition,
            0x70: receive_schedule,
            0x71: receive_schedule,
            0x7B: receive_schedule,
            0x7C: receive_schedule,
            0x7D: receive_schedule,
            0x7E: receive_schedule,
            0x7F: receive_schedule,
            0x80: receive_schedule,
            0x81: receive_schedule,
            0x82: receive_antiscale,
        },
        "ToDevice": {
            "Switch": 0x65,
            "SetPoint": 0x67,
            "ChildLock": 0x28,
            "ValveDetection": 0x14,
            "WindowDetection": 0x08,
            "Calibration": 0x1B,
            "TrvMode": 0x6C,
            "TrvSchedule": 0x6D,
        },
    },
    "TS0601-eTRV": {
        "FromDevice": {
            0x02: receive_setpoint,
            0x03: receive_temperature,
            0x04: receive_preset,
            0x08: receive_windowdetection_status,
            0x15: receive_battery,
            0x12: receive_windowdetection,
            0x1B: receive_calibration,
            0x28: receive_childlock,
            0x65: receive_onoff,
            0x66: receive_temperature,
            0x67: receive_setpoint,  # ????
            0x6A: receive_temporary_away,  # Temporary Away
            0x6C: receive_preset,
            0x6D: receive_valveposition,
            0x6E: receive_lowbattery,
            0x82: receive_antiscale,  # Anti Scale (Heater protection)
        },
        "ToDevice": {"SetPoint": 0x02, "TrvMode": 0x04},
    },
    "TS0601-_TZE200_b6wax7g0": {
        "FromDevice": {
            0x01: receive_brt100_mode,     # 0x00 - Auto, 0x01 - Manual, 0x02 - Temp Hand, 0x03 - Holliday
            0x02: receive_setpoint,
            0x03: receive_temperature,
            0x04: receive_rapid_heating_status,
            0x08: receive_windowdetection_status,
            0x09: receive_windowdetection,
            0x0D: receive_childlock,
            0x0E: receive_battery,
            0x65: receive_moe_schedule,
            0x67: receive_boost_time,
            0x68: receive_valveposition, 
            0x69: receive_calibration,
            0x6A: receive_temporary_away,
            0x6B: receive_eco_temperature,
            0x6C: receive_max_temperature,
            0x6D: receive_min_temperature,
        },
        "ToDevice": {
            "BRTMode": 0x01,         # => tuya_trv_brt100_set_mode() Type 04, lengh 0x01
            "SetPoint": 0x02,
            "RapidHeating": 0x04,    # => tuya_trv_boost()
            "WindowDetection": 0x08,
            "ChildLock": 0x0d,
            "BoostTime": 0x67,       # => tuya_trv_boost_time() Type: 0x02 lenght 0x04
            "Calibration": 0x69,
            "EcoMode": 0x6A,         # => tuya_trv_temporary_away() Type: 0x01 lenght 0x01
            "EcoTemp": 0x6B,         # => tuya_trv_eco_temp() Type: 02, lenght 0x04
            "MaxSetpoint": 0x6C,     # => tuya_trv_set_max_setpoint() Type 02, lenght 0x04
            "MinSetpoint": 0x6D,     # => tuya_trv_set_min_setpoint() type 02, lenght 0x04 
        },
    },
    "TS0601-_TZE200_chyvmhay": {
        "FromDevice": {
            0x02: receive_LIDLMode,
            0x10: receive_setpoint,
            0x18: receive_temperature,
            0x23: receive_battery,      # Battery Voltage ?
            0x28: receive_childlock,
            0x68: receive_calibration,
        },
        "ToDevice": {
            "SetPoint": 0x10,
            "LIDLMode": 0x02,
        }
    }
}


def tuya_eTRV_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    self.log.logging(
        "Tuya", "Debug", "tuya_eTRV_response - Nwkid: %s dp: %02x datatype: %s data: %s" % (NwkId, dp, datatype, data)
    )

    model_target = "TS0601-eTRV1"
    if _ModelName in eTRV_MODELS:
        model_target = eTRV_MODELS[_ModelName]

    manuf_name = get_manuf_name(self, NwkId)

    if model_target in eTRV_MATRIX:
        if dp in eTRV_MATRIX[model_target]["FromDevice"]:
            eTRV_MATRIX[model_target]["FromDevice"][dp](
                self, Devices, model_target, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data
            )
        else:
            attribute_name = "UnknowDp_0x%02x_Dt_0x%02x" % (dp, datatype)
            store_tuya_attribute(self, NwkId, attribute_name, data)
            self.log.logging(
                "Tuya",
                "Debug",
                "tuya_eTRV_response - Nwkid: %s dp: %02x datatype: %s data: %s UNKNOW dp for Manuf: %s, Model: %s"
                % (NwkId, dp, datatype, data, manuf_name, _ModelName),
            )
    else:
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_eTRV_response - Nwkid: %s dp: %02x datatype: %s data: %s UNKNOW Manuf %s, Model: %s"
            % (NwkId, dp, datatype, data, manuf_name, _ModelName),
        )


def tuya_lidl_set_mode(self, nwkid, mode):
    # 2: // away
    # 1: // manual
    # 0: // auto
    self.log.logging("Tuya", "Debug", "tuya_lidl_set_mode - %s mode: %s" % (nwkid, mode))
    if mode not in (0x00, 0x01, 0x02, ):
        return
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "LIDLMode")
    self.log.logging("Tuya", "Debug", "tuya_trv_brt100_set_mode - %s dp for mode: %s" % (nwkid, dp))
    if dp:
        action = "%02x04" % dp
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        data = "%02x" % mode
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

    
def tuya_trv_brt100_set_mode(self, nwkid, mode):
    # 0x00 - Auto, 0x01 - Manual, 0x02 - Temp Hand, 0x03 - Holliday
    self.log.logging("Tuya", "Debug", "tuya_trv_brt100_set_mode - %s mode: %s" % (nwkid, mode))
    if mode not in (0x00, 0x01, 0x02, 0x03):
        return
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "BRTMode")
    self.log.logging("Tuya", "Debug", "tuya_trv_brt100_set_mode - %s dp for mode: %s" % (nwkid, dp))
    if dp:
        action = "%02x04" % dp
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        data = "%02x" % mode
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)
    

def tuya_trv_boost(self, nwkid, onoff):
    self.log.logging("Tuya", "Debug", "tuya_trv_boost - %s onoff: %s" % (nwkid, onoff))
    if onoff not in (0x00, 0x01,0x03):
        return
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "RapidHeating")
    self.log.logging("Tuya", "Debug", "tuya_trv_boost - %s dp for mode: %s" % (nwkid, dp))
    if dp:
        action = "%02x01" % dp
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        data = "%02x" % onoff
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)
    
    
def tuya_trv_boost_time(self, nwkid, duration):
    self.log.logging("Tuya", "Debug", "tuya_trv_boost_time - %s duration: %s" % (nwkid, duration))
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "BoostTime")
    self.log.logging("Tuya", "Debug", "tuya_trv_boost_time - %s dp for duration: %s" % (nwkid, dp))
    if dp:
        action = "%02x02" % dp
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        data = "%08x" % duration
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)
    
def tuya_trv_temporary_away(self, nwkid, onoff):
    self.log.logging("Tuya", "Debug", "tuya_trv_temporary_away - %s onoff: %s" % (nwkid, onoff))
    if onoff not in (0x00, 0x01,0x03):
        return
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "RapidHeating")
    self.log.logging("Tuya", "Debug", "tuya_trv_temporary_away - %s dp for mode: %s" % (nwkid, dp))
    if dp:
        action = "%02x01" % dp
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        data = "%02x" % onoff
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)
    
def tuya_trv_eco_temp(self, nwkid, temperature):
    self.log.logging("Tuya", "Debug", "tuya_trv_eco_temp - %s duration: %s" % (nwkid, temperature))
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "EcoTemp")
    self.log.logging("Tuya", "Debug", "tuya_trv_eco_temp - %s dp for duration: %s" % (nwkid, dp))
    if dp:
        action = "%02x02" % dp
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        data = "%08x" % temperature
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_trv_set_max_setpoint(self, nwkid, maxsetpoint):
    self.log.logging("Tuya", "Debug", "tuya_trv_set_max_setpoint - %s duration: %s" % (nwkid, maxsetpoint))
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "MaxSetpoint")
    self.log.logging("Tuya", "Debug", "tuya_trv_set_max_setpoint - %s dp for duration: %s" % (nwkid, dp))
    if dp:
        action = "%02x02" % dp
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        data = "%08x" % maxsetpoint
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)
   
def tuya_trv_set_min_setpoint(self, nwkid, minsetpoint):
    self.log.logging("Tuya", "Debug", "tuya_trv_set_min_setpoint - %s duration: %s" % (nwkid, minsetpoint))
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "MinSetpoint")
    self.log.logging("Tuya", "Debug", "tuya_trv_set_min_setpoint - %s dp for duration: %s" % (nwkid, dp))
    if dp:
        action = "%02x02" % dp
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        data = "%08x" % minsetpoint
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)
    
        
def tuya_trv_valve_detection(self, nwkid, onoff):
    self.log.logging("Tuya", "Debug", "tuya_trv_valve_detection - %s ValveDetection: %s" % (nwkid, onoff))
    if onoff not in (0x00, 0x01):
        return
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "ValveDetection")
    self.log.logging("Tuya", "Debug", "tuya_trv_valve_detection - %s dp for SetPoint: %s" % (nwkid, dp))
    if dp:
        action = "%02x01" % dp
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        data = "%02x" % onoff
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_trv_window_detection(self, nwkid, onoff):
    self.log.logging("Tuya", "Debug", "tuya_trv_window_detection - %s WindowDetection: %s" % (nwkid, onoff))
    if onoff not in (0x00, 0x01):
        return
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "WindowDetection")
    self.log.logging("Tuya", "Debug", "tuya_trv_window_detection - %s dp for WindowDetection: %s" % (nwkid, dp))
    if dp:
        action = "%02x01" % dp
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        data = "%02x" % onoff
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_trv_child_lock(self, nwkid, onoff):
    self.log.logging("Tuya", "Debug", "tuya_trv_child_lock - %s ChildLock: %s" % (nwkid, onoff))
    if onoff not in (0x00, 0x01):
        return
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "ChildLock")
    self.log.logging("Tuya", "Debug", "tuya_trv_child_lock - %s dp for ChildLock: %s" % (nwkid, dp))
    if dp:
        action = "%02x01" % dp
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        data = "%02x" % onoff
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_trv_thermostat_sensor_mode(self, nwkid, mode):
    # Mode 0x00 - IN
    #      0x01 -- ALL
    #      0x02 - OUT
    self.log.logging("Tuya", "Debug", "tuya_trv_thermostat_sensor_mode - %s SensorMode: %s" % (nwkid, mode))
    if mode not in (0x00, 0x01, 0x02):
        return
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "SensorMode")
    self.log.logging("Tuya", "Debug", "tuya_trv_thermostat_sensor_mode - %s dp for SensorMode: %s" % (nwkid, dp))
    if dp:
        action = "%02x04" % dp
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        data = "%02x" % mode
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_set_calibration_if_needed(self, NwkId):
    target_calibration = None
    if (
        "Param" in self.ListOfDevices[NwkId]
        and "Calibration" in self.ListOfDevices[NwkId]["Param"]
        and isinstance(self.ListOfDevices[NwkId]["Param"]["Calibration"], (float, int))
    ):
        target_calibration = int(self.ListOfDevices[NwkId]["Param"]["Calibration"])

    if target_calibration is None:
        target_calibration = 0

    if target_calibration < -7 or target_calibration > 7:
        self.log.logging(
            "Tuya",
            "Error",
            "thermostat_Calibration - Wrong Calibration offset on %s off %s" % (NwkId, target_calibration),
        )
        target_calibration = 0

    if target_calibration < 0:
        # in two’s complement form
        target_calibration = abs(int(hex(-target_calibration - pow(2, 32)), 16))
        self.log.logging(
            "Tuya",
            "Debug",
            "thermostat_Calibration - 2 complement form of Calibration offset on %s off %s"
            % (NwkId, target_calibration),
        )

    if "Tuya" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Tuya"] = {}

    if "Calibration" not in self.ListOfDevices[NwkId]["Tuya"]:
        # Not existing feature !
        return

    if target_calibration == int(self.ListOfDevices[NwkId]["Tuya"]["Calibration"], 16):
        return

    self.log.logging(
        "Tuya",
        "Debug",
        "thermostat_Calibration - Set Thermostat offset on %s off %s/%08x"
        % (NwkId, target_calibration, target_calibration),
    )
    tuya_trv_calibration(self, NwkId, target_calibration)


def tuya_trv_calibration(self, nwkid, calibration):
    # 000d
    # Command: 69
    # Data Type: 02
    # 00
    # Len: 04
    # Data: 00000000
    self.log.logging("Tuya", "Debug", "tuya_trv_calibration - %s Calibration: %s" % (nwkid, calibration))
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "Calibration")
    self.log.logging("Tuya", "Debug", "tuya_trv_calibration - %s dp for Calibration: %s" % (nwkid, dp))
    if dp:
        action = "%02x02" % dp
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        if calibration < 0:
            calibration = abs(int(hex(-calibration - pow(2, 32)), 16))
        data = "%08x" % calibration
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_check_valve_detection(self, NwkId):
    if "ValveDetection" not in self.ListOfDevices[NwkId]["Param"]:
        return
    current_valve_detection = get_tuya_attribute(self, NwkId, "ValveDetection")
    if current_valve_detection != self.ListOfDevices[NwkId]["Param"]["ValveDetection"]:
        tuya_trv_valve_detection(self, NwkId, self.ListOfDevices[NwkId]["Param"]["ValveDetection"])


def tuya_check_window_detection(self, NwkId):
    if "WindowDetection" not in self.ListOfDevices[NwkId]["Param"]:
        return
    current_valve_detection = get_tuya_attribute(self, NwkId, "WindowDetection")
    if current_valve_detection != self.ListOfDevices[NwkId]["Param"]["WindowDetection"]:
        tuya_trv_window_detection(self, NwkId, self.ListOfDevices[NwkId]["Param"]["WindowDetection"])


def tuya_check_childlock(self, NwkId):
    if "ChildLock" not in self.ListOfDevices[NwkId]["Param"]:
        return
    current_valve_detection = get_tuya_attribute(self, NwkId, "ChildLock")
    if current_valve_detection != self.ListOfDevices[NwkId]["Param"]["ChildLock"]:
        tuya_trv_window_detection(self, NwkId, self.ListOfDevices[NwkId]["Param"]["ChildLock"])


def tuya_setpoint(self, nwkid, setpoint_value):

    tuya_set_calibration_if_needed(self, nwkid)
    self.log.logging("Tuya", "Debug", "tuya_setpoint - %s setpoint: %s" % (nwkid, setpoint_value))

    if get_model_name(self, nwkid) == "TS0601-eTRV3":
        # Force Manual mode
        self.log.logging("Tuya", "Debug", "tuya_setpoint - %s Force to be in Manual mode" % (nwkid))
        tuya_trv_switch_mode(self, nwkid, 20)

    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "SetPoint")
    self.log.logging("Tuya", "Debug", "tuya_setpoint - %s dp %s for SetPoint: %s" % (nwkid, dp, setpoint_value))
    if dp:
        action = "%02x02" % dp
        # In Domoticz Setpoint is in ° , In Modules/command.py we multiplied by 100 (as this is the Zigbee standard).
        # Looks like in the Tuya 0xef00 cluster it is only expressed in 10th of degree

        model_name = get_model_name(self, nwkid) 
        if model_name in[ "TS0601-thermostat","TS0601-_TZE200_b6wax7g0"]:
            tuya_trv_brt100_set_mode(self, nwkid, 0x01)   # Force to be in Manual
            # Setpoint is defined in ° and not centidegree
            setpoint_value = setpoint_value // 100
            
        elif model_name in [ "TS0601-_TZE200_chyvmhay", ]:
            setpoint_value = (setpoint_value // 100 ) * 2
    
        else:
            setpoint_value = setpoint_value // 10
        
        data = "%08x" % setpoint_value
        self.log.logging("Tuya", "Debug", "tuya_setpoint - %s dp %s to Tuya Format SetPoint: %s for model %s with data %s" % (nwkid, dp, setpoint_value, model_name,data))    
        
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)
    self.log.logging("Tuya", "Debug", "tuya_setpoint - %s dp %s cmd sent to Tuya Format SetPoint: %s" % (nwkid, dp, setpoint_value)) 

def tuya_trv_onoff(self, nwkid, onoff):
    self.log.logging("Tuya", "Debug", "tuya_trv_onoff - %s Switch: %s" % (nwkid, onoff))
    tuya_trv_switch_onoff(self, nwkid, onoff)
    if onoff == 0x01 and get_model_name(self, nwkid) == "TS0601-eTRV3":
        # We force the eTRV to switch to Manual mode
        tuya_trv_switch_mode(self, nwkid, 20)


def tuya_trv_mode(self, nwkid, mode):
    self.log.logging("Tuya", "Debug", "tuya_trv_mode - %s tuya_trv_mode: %s" % (nwkid, mode), nwkid)
    Domoticz.Log("type: %s" % type(mode))
    # Mode = 0  => Off
    # Mode = 10 => Auto
    # Mode = 20 => Manual

    if get_model_name(self, nwkid) in (
        "TS0601-eTRV3",
        "TS0601-thermostat",
    ):
        self.log.logging("Tuya", "Debug", "1", nwkid)
        if mode == 0:  # Switch Off
            self.log.logging("Tuya", "Debug", "1.1", nwkid)
            tuya_trv_switch_onoff(self, nwkid, 0x00)
        else:
            # Switch On if needed
            self.log.logging("Tuya", "Debug", "1.2", nwkid)
            if get_tuya_attribute(self, nwkid, "Switch") == "00":
                # If eTRV is Off, then let's switch it on
                self.log.logging("Tuya", "Debug", "1.2.1", nwkid)
                tuya_trv_switch_onoff(self, nwkid, 0x01)

    if get_model_name(self, nwkid) in ("TS0601-thermostat",):
        self.log.logging("Tuya", "Debug", "2", nwkid)
        if mode == 10:
            self.log.logging("Tuya", "Debug", "2.1", nwkid)
            # Thermostat Manual --> Auto
            #       Dp: 0x02 / 0x01 -- Manual Off
            #       Dp: 0x03 / 0x00 -- Schedule On
            tuya_trv_switch_manual(self, nwkid, 0x01)
            tuya_trv_switch_schedule(self, nwkid, 0x00)
        elif mode == 20:
            self.log.logging("Tuya", "Debug", "2.2", nwkid)
            # Thermostat Auto ---> Manual
            #       Dp: 0x02 / 0x00 -- Manual On
            #       Dp: 0x03 / 0x01 -- Manual Off
            tuya_trv_switch_manual(self, nwkid, 0x00)
            tuya_trv_switch_schedule(self, nwkid, 0x01)

    else:
        tuya_trv_switch_mode(self, nwkid, mode)


def tuya_trv_switch_manual(self, nwkid, offon):
    self.log.logging("Tuya", "Debug", "tuya_trv_switch_manual - %s Manual On/Off: %x" % (nwkid, offon), nwkid)
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "ManualMode")
    self.log.logging("Tuya", "Debug", "tuya_trv_switch_manual - %s dp for ManualMode: %x" % (nwkid, dp), nwkid)
    if dp:
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        action = "%02x04" % dp  # Mode
        data = "%02x" % (offon)
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_trv_switch_schedule(self, nwkid, offon):
    self.log.logging("Tuya", "Debug", "tuya_trv_switch_schedule - %s Schedule On/Off: %x" % (nwkid, offon), nwkid)
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "ScheduleMode")
    self.log.logging("Tuya", "Debug", "tuya_trv_switch_schedule - %s dp for ScheduleMode: %x" % (nwkid, dp), nwkid)
    if dp:
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        action = "%02x04" % dp  # Mode
        data = "%02x" % (offon)
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_trv_switch_mode(self, nwkid, mode):
    self.log.logging("Tuya", "Debug", "tuya_trv_switch_mode - %s Switch Mode: %x" % (nwkid, mode), nwkid)
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "TrvMode")
    self.log.logging("Tuya", "Debug", "tuya_trv_switch_mode - %s dp for TrvMode: %x" % (nwkid, dp), nwkid)
    if dp:
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        # Set Action
        if get_model_name(self, nwkid) == "TS0601-eTRV3":
            action = "%02x01" % dp  # Mode
        else:
            action = "%02x04" % dp  # Mode

        # Set data value
        if get_model_name(self, nwkid) == "TS0601-thermostat":
            data = "00" if mode == 10 else "01"
        elif get_model_name(self, nwkid) == "TS0601-eTRV3":
            data = "01" if mode == 10 else "00"
        else:
            data = "%02x" % (mode // 10)

        self.log.logging(
            "Tuya", "Debug", "tuya_trv_switch_mode - %s Action: %s Data: %s " % (nwkid, action, data), nwkid
        )
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_trv_switch_onoff(self, nwkid, onoff):
    self.log.logging("Tuya", "Debug", "tuya_trv_switch_onoff - %s Switch: %s" % (nwkid, onoff))
    if onoff not in (0x00, 0x01):
        return
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "Switch")
    self.log.logging("Tuya", "Debug", "tuya_trv_switch_onoff - %s dp for Switch: %s" % (nwkid, dp))
    if dp:
        action = "%02x01" % dp
        # determine which Endpoint
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        data = "%02x" % onoff
        tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_trv_reset_schedule(self, nwkid, schedule):

    # All days: 00:00 set 20°: 00 11 6d00 0012 7f 07 000000c8 000000c8 000000c8 000000c8
    # Monday                   00 12 6d00 0012 01 07 000000be 000000be 000000be 000000be
    # Tuesday                  00 13 6d00 0012 02 07 000000be 000000be 000000be 000000be
    # Wenesday                 00 14 6d00 0012 04 07 000000be 000000be 000000be 000000be
    # Thursday                 00 15 6d00 0012 08 07 000000be 000000be 000000be 000000be
    # Friday                   00 16 6d00 0012 10 07 000000be 000000be 000000be 000000be
    # Saturdat                 00 17 6d00 0012 20 07 000000be 000000be 000000be 000000be
    # Sunday                   00 18 6d00 0012 40 07 000000be 000000be 000000be 000000be
    # Mon/Tue/Wed              00 19 6d00 0012 07 07 000000c3 000000c3 000000c3 000000c3
    # Thu/Fri/Sat              00 1a 6d00 0012 38 07 000000b9 000000b9 000000b9 000000b9

    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    dp = get_datapoint_command(self, nwkid, "TrvSchedule")
    if dp:
        EPout = "01"
        cluster_frame = "11"
        cmd = "00"  # Command
        action = "%02x00" % dp  # 0x6d for eTRV3


def get_manuf_name(self, nwkid):
    if "Manufacturer Name" not in self.ListOfDevices[nwkid]:
        return None
    return self.ListOfDevices[nwkid]["Manufacturer Name"]


def get_model_name(self, nwkid):
    if "Model" not in self.ListOfDevices[nwkid]:
        return None
    _ModelName = self.ListOfDevices[nwkid]["Model"]
    return eTRV_MODELS[_ModelName] if _ModelName in eTRV_MODELS else "TS0601-eTRV1"


def get_datapoint_command(self, nwkid, cmd):
    _model_name = get_model_name(self, nwkid)
    if _model_name not in eTRV_MATRIX:
        self.log.logging(
            "Tuya", "Debug", "get_datapoint_command - %s %s not found in eTRV_MATRIX" % (nwkid, _model_name), nwkid
        )
        return None
    if cmd not in eTRV_MATRIX[_model_name]["ToDevice"]:
        self.log.logging(
            "Tuya",
            "Debug",
            "get_datapoint_command - %s %s not found in eTRV_MATRIX[ %s ]['ToDevice']" % (nwkid, cmd, _model_name),
            nwkid,
        )
        return None
    return eTRV_MATRIX[_model_name]["ToDevice"][cmd]
