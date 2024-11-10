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
    Module: batteryManagement.py

    Description: handling the battery informations

"""

import time

from Modules.domoTools import Update_Battery_Device
from Modules.tools import get_deviceconf_parameter_value, voltage2batteryP


def get_float_value(device_data, keys):
    value = device_data
    for key in keys:
        value = value.get(key, {})
        if value == {}:
            return None
    return float(value)


def UpdateBatteryAttribute(self, Devices, MsgSrcAddr, MsgSrcEp):

    model_name = self.ListOfDevices[MsgSrcAddr].get("Model", None)

    if model_name and not get_deviceconf_parameter_value(self, model_name, "BatteryDevice"):
        hack_battery_to_main_power(self, MsgSrcAddr)
        return

    # Compute Battery %
    mainVolt = battVolt = battRemainingVolt = battRemainPer = None

    device_power_cluster = self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0001"]

    mainVolt = get_float_value(device_power_cluster, ["0000"])
    battVolt = get_float_value(device_power_cluster, ["0010"])
    battRemainingVolt = get_float_value(device_power_cluster, ["0020"])
    battRemainPer = get_float_value(device_power_cluster, ["0021"])

    battery_percengtage_timestamp = self.ListOfDevices[MsgSrcAddr].get("BatteryPercentage_TimeStamp", 0)
    battery_voltage_timestamp = self.ListOfDevices[MsgSrcAddr].get("BatteryVoltage_TimeStamp", 0)

    value = None
    # Based on % ( 0x0021 )
    if battRemainPer and battery_percengtage_timestamp >= battery_voltage_timestamp:
        value = battRemainPer
        BatteryPercentageConverter = get_deviceconf_parameter_value(self, model_name, "BatteryPercentageConverter")
        if BatteryPercentageConverter:
            value = round(value / BatteryPercentageConverter)

    # Based on Remaining Voltage
    elif battRemainingVolt and battery_voltage_timestamp >= battery_percengtage_timestamp:
        MaxBatteryVoltage = get_deviceconf_parameter_value(self, model_name, "MaxBatteryVoltage", 30)
        MinBatteryVoltage = get_deviceconf_parameter_value(self, model_name, "MinBatteryVoltage", 25)
        value = voltage2batteryP(battRemainingVolt, MaxBatteryVoltage, MinBatteryVoltage)

    self.log.logging( ["Cluster", "BatteryManagement"], "Debug", f'UpdateBatteryAttribute - Device: {MsgSrcAddr} Model: {model_name} mainVolt:{mainVolt} , battVolt:{battVolt}, battRemainingVolt: {battRemainingVolt}, battRemainPer:{battRemainPer} => value: {value} ', MsgSrcAddr, )

    if value is None:
        return

    self.ListOfDevices[MsgSrcAddr]["BatteryUpdateTime"] = int(time.time())
    if value != self.ListOfDevices[MsgSrcAddr]["Battery"]:
        self.ListOfDevices[MsgSrcAddr]["Battery"] = value
        Update_Battery_Device(self, Devices, MsgSrcAddr, value)

    self.ListOfDevices[MsgSrcAddr].pop("IASBattery", None)


def hack_battery_to_main_power(self, Nwkid):
    power_source = self.ListOfDevices[Nwkid].get("PowerSource")
    mac_capa = self.ListOfDevices[Nwkid].get("MacCapa")

    if power_source == "Main" or mac_capa in {"84", "8e"}:
        # This is a Main Powered device. Make sure we do not report battery
        self.ListOfDevices[Nwkid]["Battery"] = {}