#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#
"""
    Module: batteryManagement.py

    Description: handling the battery informations

"""

from Modules.domoTools import Update_Battery_Device
from Modules.tools import voltage2batteryP, get_deviceconf_parameter_value

from time import time


def UpdateBatteryAttribute(self, Devices, MsgSrcAddr, MsgSrcEp):

    model_name = None
    if "Model" in self.ListOfDevices[MsgSrcAddr]:
        model_name = self.ListOfDevices[MsgSrcAddr]["Model"]

    if not get_deviceconf_parameter_value(self, self.ListOfDevices[MsgSrcAddr]["Model"], "BatteryDevice"):
        hack_battery(self, MsgSrcAddr)

    # Compute Battery %
    mainVolt = battVolt = battRemainingVolt = battRemainPer = None
    if "0000" in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0001"]:
        mainVolt = float(self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0001"]["0000"])
    if "0010" in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0001"]:
        battVolt = float(self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0001"]["0010"])
    if "0020" in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0001"] and self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0001"]["0020"] != {}:
        battRemainingVolt = float(self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0001"]["0020"])
    if "0021" in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0001"] and self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0001"]["0021"] != {}:
        battRemainPer = float(self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0001"]["0021"])
    self.log.logging(
        "Cluster",
        "Debug",
        f'readCluster 0001 - Device: {MsgSrcAddr} Model: {self.ListOfDevices[MsgSrcAddr]["Model"]} mainVolt:{mainVolt} , battVolt:{battVolt}, battRemainingVolt: {battRemainingVolt}, battRemainPer:{battRemainPer} ',
        MsgSrcAddr,
    )

    value = None
    # Based on % ( 0x0021 )
    if battRemainPer:
        value = battRemainPer
        BatteryPercentageConverter = get_deviceconf_parameter_value(self, self.ListOfDevices[MsgSrcAddr]["Model"], "BatteryPercentageConverter")
        if BatteryPercentageConverter:
            value = round(value / BatteryPercentageConverter)

    # Based on Remaining Voltage
    elif battRemainingVolt:
        MaxBatteryVoltage = get_deviceconf_parameter_value(self, self.ListOfDevices[MsgSrcAddr]["Model"], "MaxBatteryVoltage", 30)
        MinBatteryVoltage = get_deviceconf_parameter_value(self, self.ListOfDevices[MsgSrcAddr]["Model"], "MinBatteryVoltage", 25)
        value = voltage2batteryP(battRemainingVolt, MaxBatteryVoltage, MinBatteryVoltage)

    if value is None:
        return

    self.log.logging(
        "Cluster",
        "Debug",
        f'readCluster 0001 - Device: {MsgSrcAddr} Model: {self.ListOfDevices[MsgSrcAddr]["Model"]} Updating battery {self.ListOfDevices[MsgSrcAddr]["Battery"]} to {value}',
        MsgSrcAddr,
    )

    self.ListOfDevices[MsgSrcAddr]["BatteryUpdateTime"] = int(time())
    if value != self.ListOfDevices[MsgSrcAddr]["Battery"]:
        self.ListOfDevices[MsgSrcAddr]["Battery"] = value
        Update_Battery_Device(self, Devices, MsgSrcAddr, value)
        self.log.logging("Cluster", "Debug", f'readCluster 0001 - Device: {MsgSrcAddr} Model: {self.ListOfDevices[MsgSrcAddr]["Model"]} Updating battery to {value}', MsgSrcAddr)


def hack_battery(self, Nwkid):

    if self.ListOfDevices[Nwkid]["PowerSource"] == "Main" or self.ListOfDevices[Nwkid]["MacCapa"] in (
        "84",
        "8e",
    ):
        # This is a Main Powered device. Make sure we do not report battery
        self.ListOfDevices[Nwkid]["Battery"] = {}
        return
