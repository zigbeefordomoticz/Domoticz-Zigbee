#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""Domoticz version check helpers extracted from tools.py"""


def is_domoticz_db_available(self):
    #  Domoticz 2021.1 build 13495

    if not self.VersionNewFashion:
        self.log.logging("PluginTools", "Debug", "is_domoticz_db_available: %s due to Fashion" % False)
        return False

    if self.DomoticzMajor < 2021:
        self.log.logging("PluginTools", "Debug", "is_domoticz_db_available: %s due to Major" % False)
        return False

    if self.DomoticzMajor == 2021 and self.DomoticzMinor < 1:
        self.log.logging("PluginTools", "Debug", "is_domoticz_db_available: %s due to Minor" % False)
        return False

    return True


def is_domoticz_below_2020(self) -> bool:
    """Return True if Domoticz version is below year 2020."""
    return self.DomoticzMajor < 2020


def is_domoticz_below_2021(self) -> bool:
    """Return True if Domoticz version is below year 2021."""
    return self.DomoticzMajor < 2021


def is_domoticz_below_2022(self) -> bool:
    """Return True if Domoticz version is below year 2022."""
    return self.DomoticzMajor < 2022

def is_domoticz_below_2023(self) -> bool:
    """Return True if Domoticz version is below year 2023."""
    return self.DomoticzMajor < 2023


def is_domoticz_above_2022(self) -> bool:
    """Return True if Domoticz version is above year 2022."""
    return self.DomoticzMajor > 2022


def is_domoticz_above_2022_2(self) -> bool:
    """
    Return True if Domoticz version is above 2022.2,
    meaning major version > 2022 or exactly 2022 with minor >= 2.
    """
    if self.DomoticzMajor > 2022:
        return True
    return self.DomoticzMajor == 2022 and self.DomoticzMinor >= 2


def is_domoticz_2023(self) -> bool:
    """Return True if Domoticz version is exactly 2023."""
    return self.DomoticzMajor == 2023


def is_domoticz_above_2023(self) -> bool:
    """Return True if Domoticz version is above year 2023."""
    return self.DomoticzMajor > 2023


def is_domoticz_below_2024(self) -> bool:
    """Return True if Domoticz version is below year 2024."""
    return self.DomoticzMajor < 2024


def is_domoticz_2024(self) -> bool:
    """Return True if Domoticz version is exactly 2024."""
    return self.DomoticzMajor == 2024


def is_domoticz_above_2024(self) -> bool:
    """Return True if Domoticz version is exactly 2024."""
    return self.DomoticzMajor > 2024

def is_domoticz_new_API(self) -> bool:
    """
        Check if Domoticz version supports the new API.

        - Versions below 2023 do not support new API.
        - For 2023, minor > 1 or (minor == 1 and build >= 15326) supports new API.
        - Versions 2024 and above support new API.
    """
    self.log.logging("PluginTools", "Debug", "is_domoticz_new_API() %s %s %s %s" %(
        is_domoticz_below_2023(self), is_domoticz_2023(self), self.DomoticzMinor, self.DomoticzBuild))
    if is_domoticz_below_2023(self):
        return False
    if is_domoticz_2023(self):
        return ( self.DomoticzMinor > 1 or ( self.DomoticzMinor == 1 and self.DomoticzBuild >= 15326 ))
    return True


def is_domoticz_latest_typename(self) -> bool:
    """
        Checks if Domoticz includes the latest typename.

        Returns True if:
          - version is 2024 or above, AND
          - minor version > 4 OR build number >= 15956
    """
    if is_domoticz_below_2024(self):
        return False
    return self.DomoticzMinor > 4 or self.DomoticzBuild >= 15956


def is_domoticz_new_blind(self) -> bool:
    """ Check if Domoticz version supports the new blind control API. """
    return is_domoticz_above_2022_2(self)


def is_domoticz_update_SuppressTriggers( self ) -> bool:
    """
        Check if Domoticz version uses updated suppress triggers flag.
        
        - Versions above 2022 always True.
        - Versions below 2021 always False.
        - Special case for 2021.1 build < 13374 returns False.
        - Default True otherwise.
    """
    
    if is_domoticz_above_2022(self):
        return True
    if is_domoticz_below_2021(self):
        return False
    return ( self.DomoticzMajor != 2021 or self.DomoticzMinor != 1 or self.DomoticzBuild >= 13374 )


def is_domoticz_touch(self) -> bool:
    """
    Check if Domoticz version supports touch features.

    - Returns True if VersionNewFashion is set or major version >= 2022.
    - Also True if major == 4 and minor >= 10547 (legacy condition?).
    """
    if self.VersionNewFashion or self.DomoticzMajor >= 2022:
        return True

    return self.DomoticzMajor == 4 and self.DomoticzMinor >= 10547


def get_device_config_param(self, NwkId, config_parameter):
    """Retrieve config_parameter from the Param section in Config or Device"""

    # Log debug information
    self.log.logging("Input", "Debug", f"get_device_config_param: {NwkId} Config: {config_parameter}")

    # Get the device dictionary for the given NwkId, defaulting to None if not found
    device = self.ListOfDevices.get(NwkId)

    # If device dictionary does not exist, return None
    if not device:
        return None

    # Get the "Param" section dictionary from the device, defaulting to None if not found
    param_section = device.get("Param")

    # If "Param" section dictionary does not exist, return None
    if not param_section:
        return None

    # Get the value of config_parameter from the "Param" section, defaulting to None if not found
    param_value = param_section.get(config_parameter)

    # Log debug information
    self.log.logging("Input", "Debug", f"get_device_config_param: {NwkId} Config: {config_parameter} return {param_value}")

    # Return the value of config_parameter
    return param_value