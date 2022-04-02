#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: tuya.py

    Description: Tuya specific

"""

import struct

import Domoticz

from Modules.basicOutputs import raw_APS_request, write_attribute
from Modules.domoMaj import MajDomoDevice
from Modules.domoTools import Update_Battery_Device
from Modules.tools import (checkAndStoreAttributeValue, get_and_inc_ZCL_SQN,
                           is_ack_tobe_disabled)
from Modules.tuyaTools import store_tuya_attribute, tuya_cmd
from Modules.zigateConsts import ZIGATE_EP


def tuya_sirene_registration(self, nwkid):

    self.log.logging("Tuya", "Debug", "tuya_sirene_registration - Nwkid: %s" % nwkid)

    EPout = "01"
    payload = "11" + get_and_inc_ZCL_SQN(self, nwkid) + "10" + "002a"
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

    # (1) 3 x Write Attribute Cluster 0x0000 - Attribute 0xffde  - DT 0x20  - Value: 0x13
    EPout = "01"
    write_attribute(self, nwkid, ZIGATE_EP, EPout, "0000", "0000", "00", "ffde", "20", "13", ackIsDisabled=False)

    # (2) Cmd 0xf0 send on Cluster 0x0000 - no data
    payload = "11" + get_and_inc_ZCL_SQN(self, nwkid) + "f0"
    raw_APS_request(
        self,
        nwkid,
        EPout,
        "0000",
        "0104",
        payload,
        zigate_ep=ZIGATE_EP,
        ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
    )

    # (3) Cmd 0x03 on Cluster 0xef00  (Cluster Specific)
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

    # Set the Siren to °C
    tuya_siren_temp_unit(self, nwkid, unit="C")


def tuya_siren_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):

    self.log.logging("Tuya", "Debug", "tuya_siren_response - Nwkid: %s dp: %02x data: %s" % (NwkId, dp, data))
    # 000a/0504/0001/00
    if dp == 0x65:  # Power Mode ( 0x00 Battery, 0x04 USB )
        if data == "00":
            self.log.logging(
                "Tuya", "Log", "tuya_siren_response - Nwkid: %s/%s switch to Battery power" % (NwkId, srcEp), NwkId
            )

        elif data == "01":  # High
            self.ListOfDevices[NwkId]["Battery"] = 90
            Update_Battery_Device(self, Devices, NwkId, 90)

        elif data == "02":  # Medium
            self.ListOfDevices[NwkId]["Battery"] = 50
            Update_Battery_Device(self, Devices, NwkId, 50)

        elif data == "03":  # Low
            self.ListOfDevices[NwkId]["Battery"] = 25
            Update_Battery_Device(self, Devices, NwkId, 25)

        elif data == "04":
            self.log.logging(
                "Tuya", "Log", "tuya_siren_response - Nwkid: %s/%s switch to USB power" % (NwkId, srcEp), NwkId
            )

        store_tuya_attribute(self, NwkId, "PowerMode", data)

    elif dp == 0x66:
        self.log.logging("Tuya", "Debug", "tuya_siren_response - Alarm Melody 0x0473 %s" % int(data, 16), NwkId)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0006", (int(data, 16)))
        store_tuya_attribute(self, NwkId, "SirenMelody", data)

    elif dp == 0x67:
        self.log.logging("Tuya", "Debug", "tuya_siren_response - Current Siren Duration %s" % int(data, 16), NwkId)
        store_tuya_attribute(self, NwkId, "SirenDuration", data)

    elif dp == 0x68:  # Alarm set
        # Alarm
        store_tuya_attribute(self, NwkId, "Alarm", data)
        if data == "00":
            MajDomoDevice(self, Devices, NwkId, srcEp, "0006", "00", Attribute_="0168")
        else:
            MajDomoDevice(self, Devices, NwkId, srcEp, "0006", "01", Attribute_="0168")

    elif dp == 0x69:  # Temperature
        self.log.logging("Tuya", "Debug", "tuya_siren_response - Temperature %s" % int(data, 16), NwkId)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0402", (int(data, 16) / 10))
        store_tuya_attribute(self, NwkId, "Temperature", data)

    elif dp == 0x6A:  # Humidity
        self.log.logging("Tuya", "Debug", "tuya_siren_response - Humidity %s" % int(data, 16), NwkId)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0405", (int(data, 16)))
        store_tuya_attribute(self, NwkId, "Humidity", data)

    elif dp == 0x6B:  # Min Alarm Temperature
        self.log.logging("Tuya", "Debug", "tuya_siren_response - Current Min Alarm Temp %s" % int(data, 16), NwkId)
        store_tuya_attribute(self, NwkId, "MinAlarmTemp", data)

    elif dp == 0x6C:  # Max Alarm Temperature
        self.log.logging("Tuya", "Debug", "tuya_siren_response - Current Max Alarm Temp %s" % int(data, 16), NwkId)
        store_tuya_attribute(self, NwkId, "MaxAlarmTemp", data)

    elif dp == 0x6D and _ModelName == "TS0601-sirene":  # AMin Alarm Humidity
        self.log.logging("Tuya", "Debug", "tuya_siren_response - Current Min Alarm Humi %s" % int(data, 16), NwkId)
        store_tuya_attribute(self, NwkId, "MinAlarmHumi", data)

    elif dp == 0x6E:  # Max Alarm Humidity
        self.log.logging("Tuya", "Debug", "tuya_siren_response - Current Max Alarm Humi %s" % int(data, 16), NwkId)
        store_tuya_attribute(self, NwkId, "MaxAlarmHumi", data)

    elif dp == 0x70:
        self.log.logging("Tuya", "Log", "tuya_siren_response - Temperature Unit: %s " % (int(data, 16)), NwkId)
        store_tuya_attribute(self, NwkId, "TemperatureUnit", data)

    elif dp == 0x71:  # Alarm by Temperature
        self.log.logging("Tuya", "Log", "tuya_siren_response - Alarm by Temperature: %s" % (int(data, 16)), NwkId)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0006", data, Attribute_="0171")
        store_tuya_attribute(self, NwkId, "AlarmByTemp", data)

    elif dp == 0x72:  # Alarm by humidity
        self.log.logging("Tuya", "Log", "tuya_siren_response - Alarm by Humidity: %s" % (int(data, 16)), NwkId)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0006", data, Attribute_="0172")
        store_tuya_attribute(self, NwkId, "AlarmByHumi", data)

    elif dp == 0x74:  # Current Siren Volume
        self.log.logging("Tuya", "Debug", "tuya_siren_response - Current Siren Volume %s" % int(data, 16), NwkId)
        store_tuya_attribute(self, NwkId, "SirenVolume", data)

    else:
        self.log.logging(
            "Tuya",
            "Debug",
            "tuya_siren_response - Unknown attribut Nwkid: %s/%s decodeDP: %04x data: %s" % (NwkId, srcEp, dp, data),
            NwkId,
        )
        attribute_name = "UnknowDp_0x%02x_Dt_0x%02x" % (dp, datatype)
        store_tuya_attribute(self, NwkId, attribute_name, data)

        
        
def tuya_siren_alarm(self, nwkid, onoff, alarm_num=1):

    self.log.logging("Tuya", "Debug", "tuya_siren_alarm - %s onoff: %s" % (nwkid, onoff))
    duration = 5
    volume = 2
    if onoff == 0x01:
        alarm_attr = get_alarm_attrbutes(self, nwkid, alarm_num)
        duration = alarm_attr["Duration"]
        volume = alarm_attr["Volume"]
        melody = alarm_attr["Melody"]

        tuya_siren_alarm_duration(self, nwkid, duration)
        tuya_siren_alarm_volume(self, nwkid, volume)
        tuya_siren_alarm_melody(self, nwkid, melody)

    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "%04x" % struct.unpack("H", struct.pack(">H", 0x0168))[0]
    data = "%02x" % onoff
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def get_alarm_attrbutes(self, nwkid, alarm_num):

    default_value = {
        "Alarm1": {"Duration": 5, "Volume": 2, "Melody": 1},
        "Alarm2": {"Duration": 5, "Volume": 2, "Melody": 2},
        "Alarm3": {"Duration": 5, "Volume": 2, "Melody": 3},
        "Alarm4": {"Duration": 5, "Volume": 2, "Melody": 4},
        "Alarm5": {"Duration": 5, "Volume": 2, "Melody": 5},
    }

    alarm = "Alarm%s" % alarm_num
    if alarm not in default_value:
        Domoticz.Error("get_alarm_attrbutes - something wrong %s %s" % (alarm_num, alarm))
        return None

    default_alarm = default_value[alarm]
    if "Param" not in self.ListOfDevices[nwkid]:
        self.log.logging("Tuya", "Error", "get_alarm_attrbutes - default value to be used - no Param in DeviceList")
        return default_alarm

    if alarm not in self.ListOfDevices[nwkid]["Param"]:
        self.log.logging(
            "Tuya",
            "Error",
            "get_alarm_attrbutes - default value to be used - no %s in Param %s"
            % (alarm, self.ListOfDevices[nwkid]["Param"]),
        )
        return default_alarm

    alarm_attributes = self.ListOfDevices[nwkid]["Param"][alarm]
    if "Duration" not in alarm_attributes or "Volume" not in alarm_attributes or "Melody" not in alarm_attributes:
        self.log.logging(
            "Tuya",
            "Error",
            "get_alarm_attrbutes - default value to be used - Missing Duration, Volume or Melogy for alarm %s in Param %s - %s"
            % (alarm, self.ListOfDevices[nwkid]["Param"], alarm_attributes),
        )
        return default_alarm

    if alarm_attributes["Volume"] > 2:
        self.log.logging(
            "Tuya",
            "Error",
            "get_alarm_attrbutes - default value to be used - Volume can only be 0, 1 or 2 instead of %s - %s"
            % (alarm, alarm_attributes["Volume"]),
        )
        return default_alarm
    if alarm_attributes["Melody"] not in range(1, 16):
        self.log.logging(
            "Tuya",
            "Error",
            "get_alarm_attrbutes - default value to be used - Melody can only be between 1 to 15 instead of %s - %s"
            % (alarm, self.ListOfDevices[nwkid]["Param"]),
        )
        return default_alarm

    return alarm_attributes


def tuya_siren_temp_alarm(self, nwkid, onoff):
    self.log.logging("Tuya", "Debug", "tuya_siren_temp_alarm - %s onoff: %s" % (nwkid, onoff))
    min_temp = 18
    max_temp = 30

    if onoff:
        if (
            "Param" in self.ListOfDevices[nwkid]
            and "TemperatureMinAlarm" in self.ListOfDevices[nwkid]["Param"]
            and isinstance(self.ListOfDevices[nwkid]["Param"]["TemperatureMinAlarm"], int)
        ):
            min_temp = self.ListOfDevices[nwkid]["Param"]["TemperatureMinAlarm"]

        if (
            "Param" in self.ListOfDevices[nwkid]
            and "TemperatureMaxAlarm" in self.ListOfDevices[nwkid]["Param"]
            and isinstance(self.ListOfDevices[nwkid]["Param"]["TemperatureMaxAlarm"], int)
        ):
            max_temp = self.ListOfDevices[nwkid]["Param"]["TemperatureMaxAlarm"]
        tuya_siren_alarm_temp(self, nwkid, min_temp, max_temp)

    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "%04x" % struct.unpack("H", struct.pack(">H", 0x0171))[0]
    data = "%02x" % onoff
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_siren_humi_alarm(self, nwkid, onoff):
    self.log.logging("Tuya", "Debug", "tuya_siren_humi_alarm - %s onoff: %s" % (nwkid, onoff))
    min_humi = 25
    max_humi = 75

    if onoff:
        if (
            "Param" in self.ListOfDevices[nwkid]
            and "HumidityMinAlarm" in self.ListOfDevices[nwkid]["Param"]
            and isinstance(self.ListOfDevices[nwkid]["Param"]["HumidityMinAlarm"], int)
        ):
            min_humi = self.ListOfDevices[nwkid]["Param"]["HumidityMinAlarm"]

        if (
            "Param" in self.ListOfDevices[nwkid]
            and "HumidityMaxAlarm" in self.ListOfDevices[nwkid]["Param"]
            and isinstance(self.ListOfDevices[nwkid]["Param"]["HumidityMaxAlarm"], int)
        ):
            max_humi = self.ListOfDevices[nwkid]["Param"]["HumidityMaxAlarm"]
        tuya_siren_alarm_humidity(self, nwkid, min_humi, max_humi)

    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "%04x" % struct.unpack("H", struct.pack(">H", 0x0172))[0]
    data = "%02x" % onoff
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_siren_alarm_duration(self, nwkid, duration):
    # duration in second
    #     0s - 00 43 6702 0004 00000000
    #    10s - 00 44 6702 0004 0000000a
    #   250s - 00 45 6702 0004 000000fa
    #   300s - 00 46 6702 0004 0000012c

    self.log.logging("Tuya", "Debug", "tuya_siren_alarm_duration - %s duration: %s" % (nwkid, duration))
    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "%04x" % struct.unpack("H", struct.pack(">H", 0x0267))[0]
    data = "%08x" % duration
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_siren_alarm_volume(self, nwkid, volume):
    # 0-Max, 1-Medium, 2-Low
    # 0- 95db  00 3e 7404 0001 00
    # 1- 80db  00 3d 7404 0001 01
    # 2- 70db  00 3f 7404 0001 02
    self.log.logging("Tuya", "Debug", "tuya_siren_alarm_volume - %s volume: %s" % (nwkid, volume))
    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "%04x" % struct.unpack("H", struct.pack(">H", 0x0474))[0]
    data = "%02x" % volume
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_siren_alarm_melody(self, nwkid, melody):
    # 18-Melodies 1 -> 18 ==> 0x00 -- 0x11
    # 1- 00 40 6604 0001 00
    # 2- 00 41 6604 0001 01

    self.log.logging("Tuya", "Debug", "tuya_siren_alarm_melody - %s onoff: %s" % (nwkid, melody))
    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "%04x" % struct.unpack("H", struct.pack(">H", 0x0466))[0]
    data = "%02x" % melody
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_siren_temp_unit(self, nwkid, unit="C"):
    # From °c to °F: 00 39 7001 0001 00
    #                00 3b 7001 0001 00

    # From °F to °c: 00 3a 7001 0001 01
    #                00 3c 7001 0001 01
    unit = 0x01 if unit != "F" else 0x00
    self.log.logging("Tuya", "Debug", "tuya_siren_temp_unit - %s Unit Temp: %s" % (nwkid, unit))
    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "%04x" % struct.unpack("H", struct.pack(">H", 0x0170))[0]
    data = "%02x" % unit

    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_siren_alarm_humidity(self, nwkid, min_humi_alarm, max_humi_alarm):
    #                  Max humi            Min humi
    # 00 34 6e02 00 04 00000058 6d02 00 04 0000000c
    # 00 36 7201 00 01 01
    self.log.logging(
        "Tuya",
        "Debug",
        "tuya_siren_alarm_min_humidity - %s Min Humi: %s Max Humid: %s" % (nwkid, min_humi_alarm, max_humi_alarm),
    )
    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action1 = "%04x" % struct.unpack("H", struct.pack(">H", 0x026E))[0]
    data1 = "%08x" % max_humi_alarm

    action2 = "%04x" % struct.unpack("H", struct.pack(">H", 0x026D))[0]
    data2 = "%08x" % min_humi_alarm
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action1, data1, action2, data2)


def tuya_siren_alarm_temp(self, nwkid, min_temp_alarm, max_temp):
    # Enable Temp Alarm 18° <---> 33°c
    #                  Max temp                Min temp
    # 00 23 6c02 00 04 00000021     6b02 00 04 00000012
    # 00 24 7101 00 01 01
    #
    self.log.logging(
        "Tuya", "Debug", "tuya_siren_alarm_min_temp - %s Min Temp: %s Max Temp: %s" % (nwkid, min_temp_alarm, max_temp)
    )
    # determine which Endpoint
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action1 = "%04x" % struct.unpack("H", struct.pack(">H", 0x026C))[0]
    data1 = "%08x" % max_temp

    action2 = "%04x" % struct.unpack("H", struct.pack(">H", 0x026B))[0]
    data2 = "%08x" % min_temp_alarm

    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action1, data1, action2, data2)


def tuya_siren2_response(self, Devices, _ModelName, NwkId, srcEp, ClusterID, dstNWKID, dstEP, dp, datatype, data):
    
    self.log.logging("Tuya", "Debug", "tuya_siren2_response - Nwkid: %s dp: %02x data: %s" % (NwkId, dp, data))
    if dp == 0x05:    # Sound level
        # 000a/0504/00/01/00 Low
        # 000e/0504/00/01/02 Max
        self.log.logging("Tuya", "Debug", "tuya_siren2_response - Sound Level: %s" % (int(data, 16)), NwkId)
        store_tuya_attribute(self, NwkId, "AlarmLevel", data)
    
    elif dp == 0x07:   # Duration   
        # 0010/0702/00/04/0000003c
        self.log.logging("Tuya", "Debug", "tuya_siren2_response - Sound duration: %s" % (int(data, 16)), NwkId)
        store_tuya_attribute(self, NwkId, "AlarmDuration", data)
    
    elif dp == 0x15:    # Melodie
        # 0012/1504/0001/00
        self.log.logging("Tuya", "Debug", "tuya_siren2_response - Sound Melody: %s" % (int(data, 16)), NwkId)
        store_tuya_attribute(self, NwkId, "AlarmMelody", data)
        
    elif dp == 0x0d:   # OnOff
        self.log.logging("Tuya", "Debug", "tuya_siren2_response - OnOff: %s" % (int(data, 16)), NwkId)
        store_tuya_attribute(self, NwkId, "Alarm", data)
        MajDomoDevice(self, Devices, NwkId, srcEp, "0006", data)
        
    elif dp == 0x0f:   # Battery Percentage
        store_tuya_attribute(self, NwkId, "Battery", data)
        self.ListOfDevices[NwkId]["Battery"] = int(data,16)


def tuya_siren2_alarm_volume(self, nwkid, volume):
    # duration in second

    self.log.logging("Tuya", "Debug", "tuya_siren2_alarm_volume - %s volume: %s" % (nwkid, volume))
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "%04x" % struct.unpack("H", struct.pack(">H", 0x0405))[0]
    data = "%02x" % volume
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)


def tuya_siren2_alarm_duration(self, nwkid, duration):
    # duration in second

    self.log.logging("Tuya", "Debug", "tuya_siren2_alarm_duration - %s duration: %s" % (nwkid, duration))
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "%04x" % struct.unpack("H", struct.pack(">H", 0x0207))[0]
    data = "%08x" % duration
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)

def tuya_siren2_alarm_melody(self, nwkid, melody):
    # duration in second

    self.log.logging("Tuya", "Debug", "tuya_siren2_alarm_melody - %s melody: %s" % (nwkid, melody))
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "%04x" % struct.unpack("H", struct.pack(">H", 0x0415))[0]
    data = "%02x" % melody
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)




def tuya_siren2_trigger(self, nwkid, onoff):
    self.log.logging("Tuya", "Debug", "tuya_siren2_trigger - %s onoff: %s" % (nwkid, onoff))

    # 0017/ 0d01 00 01 01
    # 0023/ 0d01 00 01 01
    EPout = "01"
    sqn = get_and_inc_ZCL_SQN(self, nwkid)
    cluster_frame = "11"
    cmd = "00"  # Command
    action = "%04x" % struct.unpack("H", struct.pack(">H", 0x010d))[0]
    data = onoff
    tuya_cmd(self, nwkid, EPout, cluster_frame, sqn, cmd, action, data)
