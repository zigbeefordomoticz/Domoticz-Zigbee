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

MODULES_VERSION = {
    "zigpy": "0.63.1",
    "zigpy_znp": "0.12.1",
    "zigpy_deconz": "0.23.1",
    "bellows": "0.38.1",
    }

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


def check_python_modules_version( self ):
    flag = True

    for x in MODULES_VERSION:
        if importlib.metadata.version( x ) != MODULES_VERSION[ x]:
            self.log.logging("Plugin", "Error", "The python module %s version %s loaded is not compatible as we are expecting this level %s" %(
                x, importlib.metadata.version( x ), MODULES_VERSION[ x] ))
            flag = False
            
    return flag


def check_requirements(home_folder):
    requirements_file = Path(home_folder) / "requirements.txt"
    Domoticz.Status("Checking Python modules %s" % requirements_file)

    with open(requirements_file, 'r') as file:
        requirements_list = file.readlines()

    for req_str in requirements_list:
        req_str = req_str.strip()
        package = re.split(r'[<>!=]+', req_str)[0].strip()

        try:
            installed_version = importlib.metadata.version(package)

            if '==' in req_str:
                version = re.split('==', req_str)[1].strip()
                if installed_version != version:
                    raise importlib.metadata.PackageNotFoundError
            elif '>=' in req_str:
                version = re.split('>=', req_str)[1].strip()
                if installed_version < version:
                    raise importlib.metadata.PackageNotFoundError
            elif '<=' in req_str:
                version = re.split('<=', req_str)[1].strip()
                if installed_version > version:
                    raise importlib.metadata.PackageNotFoundError

        except importlib.metadata.PackageNotFoundError:
            Domoticz.Error(f"Looks like {req_str} Python module is not installed or does not meet the required version. Requires {version}, Installed {installed_version}. "
                           f"Make sure to install the required Python3 module with the correct version.")
            Domoticz.Error("Use the command:")
            Domoticz.Error("sudo python3 -m pip install -r requirements.txt --upgrade")
            return True

        except importlib.metadata.MetadataError:
            Domoticz.Error(f"An unexpected error occurred while checking {req_str}")
            return True

        except Exception as e:
            Domoticz.Error(f"An unexpected error occurred: {e}")
            return True

    return False


#def list_all_modules_loaded(self):
#    # Get a list of installed packages and their versions
#    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
#
#    # Get a list of modules imported by the main script
#    main_modules = set(sys.modules.keys())
#
#    # Combine the lists
#    all_modules = set(installed_packages.keys()) | main_modules
#
#    # Print the list of modules and their versions
#    self.log.logging("Plugin", "Log", "=============================")
#    for module_name in sorted(all_modules):
#        version = installed_packages.get(module_name, "Not installed")
#        self.log.logging("Plugin", "Log", f"{module_name}: {version}")
#    self.log.logging("Plugin", "Log", "=============================")
#

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
