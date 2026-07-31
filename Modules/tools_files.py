#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# SPDX-License-Identifier:    GPL-3.0 license

"""File/utility helpers extracted from tools.py"""


import contextlib
import datetime
import os.path
import shutil
from pathlib import Path



def _safe_file_transfer(source: str, dest: str, move: bool = True) -> None:
    """Move or copy a file with a text-mode fallback for resilience.

    Attempts a binary-safe shutil move/copy first. If that fails,
    falls back to line-by-line UTF-8 text copy.

    Args:
        source: Path to the source file.
        dest:   Destination file path.
        move:   If True (default), move the file; otherwise copy it.

    Raises:
        RuntimeError: If both the shutil operation and the fallback fail.
    """
    with contextlib.suppress(Exception):
        shutil.move(source, dest) if move else shutil.copy(source, dest)
        return

    try:
        with open(source, "r", encoding="utf-8") as src, \
             open(dest, "w", encoding="utf-8") as dst:
            dst.writelines(src)
    except Exception as fallback_error:
        raise RuntimeError(
            f"safe_file_transfer failed: {source!r} → {dest!r}: {fallback_error}"
        ) from fallback_error


def rotate_file_versions(source: str | Path, nb_versions: int) -> None:
    """Maintain a rotating set of versioned file backups.

    Shifts existing versions up by one (e.g. -02 → -03), then copies
    the source to -01. The oldest version beyond nb_versions is discarded.

    Args:
        source:      Path to the file to version.
        nb_versions: Number of versions to keep. No-op if 0.

    Example:
        rotate_file_versions("/data/myfile.db", 3)
        # Creates: myfile.db-01  (fresh copy)
        #          myfile.db-02  (previous -01)
        #          myfile.db-03  (previous -02)
    """
    source = Path(source)

    if nb_versions == 0:
        return

    # Shift existing versions up: -02 → -03, -01 → -02
    for version in range(nb_versions - 1, 0, -1):
        file_old = Path(f"{source}-{version:02d}")
        if not file_old.is_file():
            continue
        file_new = Path(f"{source}-{version + 1:02d}")
        _safe_file_transfer(str(file_old), str(file_new), move=True)

    # Slot -01 always gets a fresh copy of the source
    _safe_file_transfer(str(source), f"{source}-01", move=False)


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

