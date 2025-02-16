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

from Modules.domoMaj import MajDomoDevice
from Modules.schneider_wiser import wiser2_setpoint_raiserlower
from Modules.tools import checkAndStoreAttributeValue, getAttributeValue

THERMOSTAT_CLUSTER = "0201"
LOCAL_TEMPERATURE = "0000"
OCCUPIED_SETPOINT = "0012"

TEMPERATURE_CLUSTER = "0402"
TEMPERATURE_VALUE = "0000"

HUMIDITY_CLUSTER = "0405"
HUMIDITY_VALUE = "0000"


def process_env_command(self, domoticz_devices, nwkid, ep, values):
    """
    Process an ENV command from the touch screen.
    
    Expected values list: ["ENV", setpoint, local_temp, humidity]
    """
    try:
        setpoint, local_temp, humidity = map(int, values[1:])
    except ValueError:
        self.log.logging("Schneider", "Error", f"Invalid ENV data: {values}", nwkid)
        return

    self.log.logging(
        "Schneider", "Debug",
        f"ENV Data - Setpoint: {setpoint}, LocalTemp: {local_temp}, Humidity: {humidity}",
        nwkid
    )

    # Update local temperature in thermostat and temperature clusters
    checkAndStoreAttributeValue(self, nwkid, ep, THERMOSTAT_CLUSTER, LOCAL_TEMPERATURE, local_temp)
    checkAndStoreAttributeValue(self, nwkid, ep, TEMPERATURE_CLUSTER, TEMPERATURE_VALUE, local_temp)
    MajDomoDevice(self, domoticz_devices, nwkid, ep, TEMPERATURE_CLUSTER, round(local_temp / 100, 1))

    # Update humidity
    checkAndStoreAttributeValue(self, nwkid, ep, HUMIDITY_CLUSTER, HUMIDITY_VALUE, humidity)
    MajDomoDevice(self, domoticz_devices, nwkid, ep, HUMIDITY_CLUSTER, round(humidity / 100))

    # Update setpoint
    checkAndStoreAttributeValue(self, nwkid, ep, THERMOSTAT_CLUSTER, OCCUPIED_SETPOINT, setpoint)
    MajDomoDevice(self, domoticz_devices, nwkid, ep, THERMOSTAT_CLUSTER, round(setpoint / 100, 1), Attribute_=OCCUPIED_SETPOINT)


def process_ui_command(self, domoticz_devices, nwkid, values):
    """
    Process a UI command from the touch screen.
    
    Expected values list: ["UI", command]
    """
    command = values[1]
    self.log.logging("Schneider", "Debug", f"Schneider UI Interface Cluster command: {command}", nwkid)

    if command == "ScreenWake":
        self.log.logging("Schneider", "Debug", "Schneider UI Interface Cluster ScreenWake", nwkid)

    elif command == "ButtonPressCenterDown":
        self.log.logging("Schneider", "Debug", "Schneider UI Interface Cluster ButtonPressCenterDown", nwkid)

    elif command == "ButtonPressPlusDown":
        self.log.logging("Schneider", "Debug", "Schneider UI Interface Cluster ButtonPressPlusDown", nwkid)
        wiser2_setpoint_raiserlower(self, domoticz_devices, nwkid, "00", "05")  # Increase setpoint by +0.5

    elif command == "ButtonPressMinusDown":
        self.log.logging("Schneider", "Debug", "Schneider UI Interface Cluster ButtonPressMinusDown", nwkid)
        wiser2_setpoint_raiserlower(self, domoticz_devices, nwkid, "00", "fb")  # Decrease setpoint by -0.5

    elif command == "ScreenSleep":
        self.log.logging("Schneider", "Debug", "Schneider UI Interface Cluster ScreenSleep", nwkid)


def schneider_touch_screen_cluster(self, domoticz_devices, nwkid, ep, cluster, attribut, value):
    """
    Process Schneider touch screen cluster commands.
    
    For cluster "fe03" (Touch Interface):
      - "ENV" commands with 4 comma-separated values update setpoint, local temperature, and humidity.
      - "UI" commands with 2 comma-separated values trigger UI-related actions.
    """
    if cluster != "fe03":
        return

    self.log.logging("Schneider", "Debug", f"Schneider UI Interface Cluster value: {value}", nwkid)
    values = value.split(',')

    if values[0] == "ENV" and len(values) == 4:
        process_env_command(self, domoticz_devices, nwkid, ep, values)

    elif values[0] == "UI" and len(values) == 2:
        process_ui_command(self, domoticz_devices, nwkid, values)
