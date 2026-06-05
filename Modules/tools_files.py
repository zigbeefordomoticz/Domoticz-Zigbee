#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""File/utility helpers extracted from tools.py"""

import datetime
import os.path
import shutil


def helper_copyfile(source, dest, move=True):
    """
    Copy or move a file from source to destination.

    If `move` is True, the source file is moved. Otherwise, it is copied.
    If the shutil operation fails (e.g., for non-binary-safe files), it falls back to line-by-line copying in text mode.

    Args:
        source (str): Path to the source file.
        dest (str): Destination file path.
        move (bool): Whether to move (True) or copy (False) the file.

    Returns:
        None
    """
    try:
        if move:
            shutil.move(source, dest)
        else:
            shutil.copy(source, dest)

    except Exception as e:
        # Fallback in case shutil fails (e.g., special file types or permissions)
        try:
            with open(source, "r", encoding="utf-8") as src, open(dest, "wt", encoding="utf-8") as dst:
                for line in src:
                    dst.write(line)
        except Exception as fallback_error:
            raise RuntimeError(f"Failed to copy {source} to {dest}: {fallback_error}") from e


def helper_versionFile(source, nbversion):
    """
    Maintain a versioned backup of a file.

    This function creates versioned copies of the given file, like `file-01`, `file-02`, ..., up to `file-nbversion`.
    Each call shifts the previous versions up by one (e.g., `file-02` becomes `file-03`, etc.).
    The most recent copy is always `file-01`.

    Args:
        source (str): The path of the file to version.
        nbversion (int): Number of versions to keep. If 0, does nothing.

    Returns:
        None
    """
    source = str(source)

    if nbversion == 0:
        return

    if nbversion == 1:
        helper_copyfile(source, f"{source}-01")
    else:
        # Shift existing versions up by 1
        for version in range(nbversion - 1, 0, -1):
            file_old = f"{source}-{version:02d}"
            if not os.path.isfile(file_old):
                continue

            file_new = f"{source}-{version + 1:02d}"
            helper_copyfile(file_old, file_new)

        # Create or update version 01
        helper_copyfile(source, f"{source}-01", move=False)


def night_shift_jobs( self ):
    # If NighShift not enable, then alwasy return True
    # Otherwise return True only if between midnight and 6am

    if not self.pluginconf.pluginConf["NightShift"]:
        #self.log.logging("PluginTools", "Debug", "Always On" )
        return True

    current = datetime.datetime.now().time()

    # Check against first part of the night
    start = datetime.time(23, 0,0)
    end = datetime.time(23,59,59)

    if start <= current <= end:
        self.log.logging("PluginTools", "Debug", "Inside of Night Shift period %s %s %s" %( start, current, end))
        return True

    # Check against the second part of the night
    start = datetime.time(0, 0,0)
    end = datetime.time(6,0,0)
    if start <= current <= end:
        self.log.logging("PluginTools", "Debug","Inside of Night Shift period %s %s %s" %( start, current, end))
        return True

    self.log.logging("PluginTools", "Debug", "Outside of Night Shift period %s %s %s" %( start, current, end))
    return False


def print_stack( self ):
    
    try:
        import inspect
    except Exception as e:
        self.log.logging( "PluginTools", "Error", "Cannot import python module inspect")
        return
    
    for x in inspect.stack():
        self.log.logging( "PluginTools", "Error", "[{:40}| {}:{}".format(x.function, x.filename, x.lineno))


def how_many_devices(self):
    routers = enddevices = 0
    
    for device in self.ListOfDevices.values():
        device_type = device.get("DeviceType")
        logical_type = device.get("LogicalType")
        mac_capa = device.get("MacCapa")

        if device_type == "FFD" or logical_type == "Router" or mac_capa == "8e":
            routers += 1
        elif device_type == "RFD" or logical_type == "End Device" or mac_capa == "80":
            enddevices += 1

    return routers, enddevices

