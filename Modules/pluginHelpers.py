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

"""Misc plugin lifecycle helpers: Domoticz/firmware version checks, device-database
housekeeping, and Python module requirements validation against constraints.txt."""

import importlib.metadata
import re
import sys
from pathlib import Path

import DomoticzEx as Domoticz
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from Modules.domoticzAbstractLayer import domoticz_error_api
from Modules.tools import how_many_devices

# zigpy-family modules tracked by parse_constraints()/check_python_modules_version()
PYTHON_MODULES = {
    "zigpy",
    "zigpy_znp",
    "zigpy_deconz",
    "bellows",
}

def networksize_update(self):
    """Refresh the NetworkSize plugin parameter from the current device count."""
    self.log.logging("Plugin", "Debug", "Devices size has changed , let's write ListOfDevices on disk")
    routers, enddevices = how_many_devices(self)
    self.pluginParameters["NetworkSize"] = "Total: %s | Routers: %s | End Devices: %s" %(
        routers + enddevices, routers, enddevices)


def decodeConnection(connection):
    """Parse a Domoticz Connection.Description-style string into a dict."""
    decoded = {}
    for i in connection.strip().split(","):
        label, value = i.split(": ")
        label = label.strip().strip("'")
        value = value.strip().strip("'")
        decoded[label] = value
    return decoded


def check_firmware_level(self):
    """Validate the ZiGate firmware version and flag Pluzzy-specific firmware."""
    # Check Firmware version
    if int(self.FirmwareVersion.lower(),16) == 0x2100:
        self.log.logging("Plugin", "Status", "Firmware for Pluzzy devices")
        self.PluzzyFirmware = True
        return True

    if int(self.FirmwareVersion.lower(),16) < 0x031d:
        self.log.logging("Plugin", "Error", "Firmware level not supported, please update ZiGate firmware")
        return False

    if int(self.FirmwareVersion.lower(),16) >= 0x031e:
        self.pluginconf.pluginConf["forceAckOnZCL"] = False
        return True

    return False


def update_DB_device_status_to_reinit( self ):
    """Mark every 'inDB' device as 'erasePDM' ahead of a ZiGate reset/re-pair."""
    for x in self.ListOfDevices:
        if 'Status' in self.ListOfDevices[ x ] and self.ListOfDevices[ x ]['Status'] == 'inDB':
            self.ListOfDevices[ x ]['Status'] = 'erasePDM'


def get_domoticz_version( self, domoticz_version  ):
    """Parse Domoticz's version string and populate self.DomoticzMajor/Minor/Build."""
    lst_version = domoticz_version.split(" ")
    if len(lst_version) == 1:
        return _old_fashon_domoticz(self, lst_version, domoticz_version)
    
    if len(lst_version) != 3:
        domoticz_error_api( "Domoticz version %s unknown not supported, please upgrade to a more recent"% (
            domoticz_version) )
        return _domoticz_not_compatible(self)

    major, minor = lst_version[0].split(".")
    build = lst_version[2].strip(")")
    self.DomoticzBuild = int(build)
    _update_domoticz_firmware_data(self, major, minor)
    return True


def _old_fashon_domoticz(self, lst_version, domoticz_version):
    """Handle the legacy Domoticz version format that carries no build number."""
    major, minor = lst_version[0].split(".")
    self.DomoticzBuild = 0
    _update_domoticz_firmware_data(self, major, minor)
    
    if self.DomoticzMajor >= 2020:
        return True
    
    # Old fashon Versioning
    domoticz_error_api( "Domoticz version %s %s %s not supported, please upgrade to a more recent" % (
        domoticz_version, major, minor) )
    return _domoticz_not_compatible(self)


def _update_domoticz_firmware_data(self, major, minor):
    """Store the parsed Domoticz major/minor version and mark it as new-fashion."""
    self.DomoticzMajor = int(major)
    self.DomoticzMinor = int(minor)
    self.VersionNewFashion = True


def _domoticz_not_compatible(self):
    """Stop the plugin because the running Domoticz version is unsupported."""
    self.VersionNewFashion = False
    self.onStop()
    return False


def check_python_modules_version(self):
    """Log an error for each loaded zigpy-family module that violates constraints.txt.

    No-op (returns True) when the "internetAccess" plugin setting is enabled.
    """
    if self.pluginconf.pluginConf["internetAccess"]:
        return True

    constraints = parse_constraints(self.pluginParameters["HomeFolder"])
    for module, specifier in constraints.items():
        current_version = Version(importlib.metadata.version(module))
        if current_version not in specifier:
            self.log.logging("Plugin", "Error", "The Python module %s version %s loaded is not compatible. Expected: %s" % (
                module, current_version, specifier))
            return False

    return True


def list_all_modules_loaded(self):
    """Log every imported/installed Python module and its version, for debugging."""
    # Get a list of modules imported by the main script
    main_modules = set(sys.modules.keys())

    installed_packages = {
        distribution.metadata["Name"].lower(): distribution.version
        for distribution in importlib.metadata.distributions()
    }
    # Combine the lists
    all_modules = set(installed_packages.keys()) | main_modules

    # Print the list of modules and their versions
    self.log.logging("Plugin", "Log", "=============================")
    for module_name in sorted(all_modules):
        version = installed_packages.get(module_name, "Not installed")
        self.log.logging("Plugin", "Log", f"{module_name}: {version}")
    self.log.logging("Plugin", "Log", "=============================")


def parse_constraints(home_folder):
    """Read constraints.txt and return {module: SpecifierSet} for the zigpy-family modules in PYTHON_MODULES."""
    constraints_file = Path(home_folder) / "constraints.txt"
    constraints = {}

    with constraints_file.open("r") as file:
        for line in file:
            line = line.split("#", 1)[0].strip()

            if not line:
                continue

            package = re.split(r"[<>!=~]+", line, maxsplit=1)[0].strip()

            if package in PYTHON_MODULES:
                constraint = line[len(package):].strip()
                constraints[package] = SpecifierSet(constraint)

    return constraints



def check_requirements(home_folder):
    """Validate every constraints.txt entry against the installed package versions.

    Returns True if all constraints are satisfied, False otherwise (logging the
    specific package/constraint that failed via Domoticz.Error).
    """
    constraints_file = Path(home_folder) / "constraints.txt"

    Domoticz.Status(
        f"Z4D checks Python modules {constraints_file}"
    )

    with constraints_file.open("r") as file:

        for line in file:

            req_str = line.split("#", 1)[0].strip()

            if not req_str:
                continue

            package = re.split(
                r"[<>!=~]+",
                req_str,
                maxsplit=1,
            )[0].strip()

            if not package:
                continue

            constraint = req_str[len(package):].strip()

            try:
                installed_version = Version(
                    importlib.metadata.version(package)
                )

                specifier = SpecifierSet(constraint)

            except importlib.metadata.PackageNotFoundError:
                Domoticz.Error(
                    f"Python module {package} is not installed. "
                    f"Required constraint: {req_str}"
                )
                return False

            except ValueError as error:
                Domoticz.Error(
                    f"Invalid version constraint '{req_str}': {error}"
                )
                return False

            if installed_version not in specifier:

                Domoticz.Error(
                    f"Python module {package} version "
                    f"{installed_version} does not satisfy "
                    f"constraint {constraint}"
                )

                return False

            Domoticz.Status(
                f"   - {package} {installed_version} "
                f"satisfies {constraint}"
            )

    return True
