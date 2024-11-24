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

import importlib.metadata
import re
import sys
from pathlib import Path

#import DomoticzEx as Domoticz
import Domoticz as Domoticz

from Modules.tools import how_many_devices
from Modules.domoticzAbstractLayer import domoticz_error_api


def networksize_update(self):
    self.log.logging("Plugin", "Debug", "Devices size has changed , let's write ListOfDevices on disk")
    routers, enddevices = how_many_devices(self)
    self.pluginParameters["NetworkSize"] = "Total: %s | Routers: %s | End Devices: %s" %(
        routers + enddevices, routers, enddevices)


def decodeConnection(connection):

    decoded = {}
    for i in connection.strip().split(","):
        label, value = i.split(": ")
        label = label.strip().strip("'")
        value = value.strip().strip("'")
        decoded[label] = value
    return decoded


def check_firmware_level(self):
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

    # This function is called because the ZiGate will be reset, and so it is expected that all devices will be reseted and repaired

    for x in self.ListOfDevices:
        if 'Status' in self.ListOfDevices[ x ] and self.ListOfDevices[ x ]['Status'] == 'inDB':
            self.ListOfDevices[ x ]['Status'] = 'erasePDM'


def get_domoticz_version( self, domoticz_version  ):
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
    # No Build
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
    self.DomoticzMajor = int(major)
    self.DomoticzMinor = int(minor)
    self.VersionNewFashion = True


def _domoticz_not_compatible(self):
    self.VersionNewFashion = False
    self.onStop()
    return False


def check_python_modules_version(self):
    if self.pluginconf.pluginConf["internetAccess"]:
        return True

    zigpy_modules_version = parse_constraints(self.pluginParameters["HomeFolder"])
    for module, expected_version in zigpy_modules_version.items():
        current_version = importlib.metadata.version(module)
        if current_version != expected_version:
            self.log.logging("Plugin", "Error", "The Python module %s version %s loaded is not compatible. Expected version: %s" % (
                module, current_version, expected_version))
            return False

    return True


def check_requirements(home_folder):

    requirements_file = Path(home_folder) / "constraints.txt"
    Domoticz.Status("Checking Python modules %s" % requirements_file)

    with open(requirements_file, 'r') as file:
        requirements_list = file.readlines()

    for req_str in requirements_list:
        req_str = req_str.strip()

        package = re.split(r'[<>!=]+', req_str)[0].strip()
        if package == "":
            continue
        version = None
        try:
            installed_version = importlib.metadata.version(package)

            version = None
            if '==' in req_str:
                version = re.split('==', req_str)[1].strip()
                if installed_version != version:
                    python_module_with_wrong_version( req_str, version, installed_version)
                    return True
            elif '>=' in req_str:
                version = re.split('>=', req_str)[1].strip()
                if installed_version < version:
                    python_module_with_wrong_version( req_str, version, installed_version)
                    return True
            elif '<=' in req_str:
                version = re.split('<=', req_str)[1].strip()
                if installed_version > version:
                    python_module_with_wrong_version( req_str, version, installed_version)
                    return True

        except importlib.metadata.PackageNotFoundError as e:
            Domoticz.Error(f"An unexpected error occurred while checking package {package} - {req_str} - {e}")
            return True

        except importlib.metadata.MetadataError as e:
            Domoticz.Error(f"An unexpected error occurred while checking {package} - {req_str} - {e}")
            return True

        except Exception as e:
            Domoticz.Error(f"An unexpected error occurred: {package} - {e}")
            return True

        Domoticz.Status(f"   - {req_str} version required {version} installed {installed_version}")
    return False

def python_module_with_wrong_version( req_str, version, installed_version):
    Domoticz.Error(f"Looks like {req_str} Python module is not installed or does not meet the required version. Requires {version}, Installed {installed_version}." 
                   f"Make sure to install the required Python3 module with the correct version.")
    Domoticz.Error("Use the command:")
    Domoticz.Error("sudo python3 -m pip install -r requirements.txt --upgrade")


def list_all_modules_loaded(self):
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
    modules_version = {
        "zigpy": "",
        "zigpy_znp": "",
        "zigpy_deconz": "",
        "bellows": ""
    }

    constraints_file = Path(home_folder) / "constraints.txt"
    with open(constraints_file, 'r') as file:
        for line in file:
            # Remove leading/trailing whitespace and newlines
            line = line.strip()

            # Split line into module name and version
            if '==' in line:
                module, version = line.split('==')
            elif '>=' in line:
                module, version = line.split('>=')
            elif '<=' in line:
                module, version = line.split('<=')
            else:
                continue

            # Check if the module is one we are interested in
            if module in modules_version:
                modules_version[module] = version

    # Remove any entries where version is still empty
    modules_version = {k: v for k, v in modules_version.items() if v}

    return modules_version
