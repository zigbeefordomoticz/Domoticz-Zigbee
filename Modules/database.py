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


"""Modules.database

High-level helpers to load, save and clean the plugin DeviceList and
related Zigbee database entries used by the Domoticz Zigbee plugin.

This module exposes functions to read/write the legacy text/json
device list, import local model configurations, validate and cleanup
entries, and apply a number of device-specific fixes required at
startup.

All functions accept ``self`` as the first parameter and operate on the
plugin instance state (for example ``self.ListOfDevices`` and
``self.pluginconf``).
"""



import ast
import contextlib
import json
import os.path
import time
from collections import deque
from pathlib import Path
from typing import Dict

import Modules.tools
from Classes.AdminWidgets import ADMIN_WIDGET_PREFIXES
from Modules.domoticzAbstractLayer import getConfigItem, setConfigItem
from Modules.manufacturer_code import check_and_update_manufcode
from Modules.pluginDbAttributes import (STORE_CONFIGURE_REPORTING,
                                        STORE_CUSTOM_CONFIGURE_REPORTING,
                                        STORE_READ_CONFIGURE_REPORTING)
from Modules.pluginModels import check_found_plugin_model
from Modules.tuyaConst import TUYA_MANUFACTURER_NAME
from Modules.zlinky import update_zlinky_device_model_if_needed

PLUGIN_DATABASE_RECORD_VERSION = 4

CIE_ATTRIBUTES = {
    "Version", 
    "ZDeviceName", 
    "Ep", 
    "IEEE", 
    "LogicalType", 
    "PowerSource", 
    "GroupMemberShip", 
    "Neighbours", 
    "NeighbourTableSize", 
    "RoutingTable", 
    "AssociatedDevices"
    }


MANDATORY_ATTRIBUTES = (
    "App Version",
    "Attributes List",
    "Bind",
    "WebBind",
    "Capability",
    "ColorInfos",
    "ClusterType",
    "ConfigSource",
    "DeviceType",
    "Ep",
    "Epv2",
    "ForceAckCommands",
    "HW Version",
    "Heartbeat",
    "IAS",
    "IEEE",
    "Location",
    "LogicalType",
    "MacCapa",
    "Manufacturer",
    "Manufacturer Name",
    "Model",
    "NbEp",
    "OTA",
    "OTAUpgrade",
    "OTAClient",
    "PowerSource",
    "ProfileID",
    "ReceiveOnIdle",
    "Stack Version",
    "RIA",
    "SWBUILD_1",
    "SWBUILD_2",
    "SWBUILD_3",
    "Stack Version",
    "Status",
    "Type",
    "Version",
    "ZCL Version",
    "ZDeviceID",
    "ZDeviceName",
    "Param",
    "_rawNodeDescriptor",
    "Max Buffer Size",
    "Max Rx",
    "Max Tx",
    "macapa",
    "bitfield",
    "server_mask",
    "descriptor_capability",
)

# List of Attributes whcih are going to be loaded, ut in case of Reset (resetPluginDS) they will be re-initialized.
BUILD_ATTRIBUTES = (
    "ParamConfigureReporting",
    "Log_UnknowDeviceFlag",
    "NeighbourTableSize",
    "BindingTable",
    "RoutingTable",
    "AssociatedDevices",
    "Battery",
    "BatteryUpdateTime",
    "GroupMemberShip",
    "Neighbours",
    STORE_CONFIGURE_REPORTING,
    STORE_READ_CONFIGURE_REPORTING,
    STORE_CUSTOM_CONFIGURE_REPORTING,
    "ReadAttributes",
    "WriteAttributes",
    "LQI",
    "RSSI",
    "SQN",
    "Stamp",
    "Health",
    "IASBattery",
    "Operating Time",
    "DelayBindingAtPairing",
    "CertifiedDevice",
    "OTAUpdate",
    "IAS_KEYPAD",
    "IAS_KEYPAD"
)

MANUFACTURER_ATTRIBUTES = (
    "Legrand", 
    "Schneider", 
    "Lumi", 
    "LUMI", 
    "CASA.IA", 
    "Tuya", 
    "ZLinky",
    "Chameleon",
    "GammaTroniques"
    )


def LoadDeviceList(self):
    """Load devices into ``self.ListOfDevices``.

    The function prefers the Domoticz plugin database when enabled and
    falls back to the plugin's device list file. It runs a set of
    cleanup and migration helpers to normalise entries and may update
    plugin configuration flags. Returns the loader result string
    (typically "Success") or True/False in some code paths.
    """
    ListOfDevices_from_Domoticz = None
    can_use_domoticz_db = False

    # This can be enabled only with Domoticz version 2021.1 build 1395 and above, otherwise big memory leak
    use_domoticz_db = self.pluginconf.pluginConf.get("useDomoticzDb")

    plugin_data = Path(self.pluginconf.pluginConf["pluginData"])
    device_name = self.DeviceListName
    device_list_txt_filename = plugin_data/ device_name
    
    if use_domoticz_db:
        # We try to load from Domoticz Db
        ListOfDevices_from_Domoticz, domoticz_db_saving_time, version = retreive_device_list_from_domoticz(self)
        
        if ListOfDevices_from_Domoticz is not None:
            can_use_domoticz_db = is_domoticz_recent(self, domoticz_db_saving_time, device_list_txt_filename)

        if can_use_domoticz_db:
            self.log.logging( "Database", "Log", "Database from Domoticz is more recent, loading from Domoticz Db" )
            
            self.ListOfDevices = ListOfDevices_from_Domoticz
            res = "Success"
            self.DeviceListSize = len(self.ListOfDevices)
            self.log.logging("Database", "Status", "Z4D loads %s entries from Domoticz (version %s)" % (self.DeviceListSize, version))
        
            # Need to populate IEEE2NWK mapping for later use
            for nwk_id, device in self.ListOfDevices.items():
                ieee = device.get("IEEE")
                if ieee:
                    self.IEEE2NWK[ieee] = nwk_id

    if not can_use_domoticz_db:
        # Loading from TXT file (Legacy)
        self.ListOfDevices = {}
        if os.path.isfile(device_list_txt_filename):
            res = loadTxtDatabase(self, device_list_txt_filename)
        else:
            # Do not exist
            return True

        self.log.logging("Database", "Status", "Z4D loads %s entries from %s" % (len(self.ListOfDevices), device_list_txt_filename))


        # Keep the Size of the DeviceList in order to check changes
        self.DeviceListSize = os.path.getsize(device_list_txt_filename)
        
    self.log.logging("Database", "Status", "Z4D creates a versioned backup of %s" % device_list_txt_filename)
    Modules.tools.rotate_file_versions(device_list_txt_filename, self.pluginconf.pluginConf["numDeviceListVersion"])

    cleanup_table_entries( self)

    if self.pluginconf.pluginConf["ZigpyTopologyReport"]:
        # Cleanup the old Topology data
        remove_legacy_topology_datas(self)
        
    for addr in self.ListOfDevices:
        model_name = self.ListOfDevices[addr].get("Model", "")
        
        # Fixing mistake done in the code.
        fixing_consumption_lumi(self, addr)
        fixing_iSQN_None(self, addr)

        # Cleaning OTA structure if needed
        cleanup_ota(self, addr)
        
        if self.pluginconf.pluginConf.get("resetOTAUpdate"):
            force_removal_ota_update(self, addr)

        # Fixing TS0601 which has been removed.
        hack_ts0601(self, addr)
        
        # Fixing GammaTroniques
        if model_name in ("TICMeter",):
            update_gamma_troniques_attributes_at_startup(self, addr)
        
        # Check if 566 fixs are needed
        if (
            self.pluginconf.pluginConf["Bug566"] 
            and model_name 
            and model_name == "TRADFRI control outlet"
        ):
            fixing_Issue566(self, addr)

        if self.pluginconf.pluginConf["resetReadAttributes"]:
            self.log.logging("Database", "Log", "ReadAttributeReq - Reset ReadAttributes data %s" % addr)
            Modules.tools.reset_device_attribute(self, "ReadAttributes", addr)

        if self.pluginconf.pluginConf["resetConfigureReporting"]:
            self.log.logging("Database", "Log", "Reset ConfigureReporting data %s" % addr)
            Modules.tools.reset_device_attribute(self, STORE_CONFIGURE_REPORTING, addr)
            Modules.tools.reset_device_attribute(self, STORE_READ_CONFIGURE_REPORTING, addr)
            
        if (
            STORE_READ_CONFIGURE_REPORTING in self.ListOfDevices[ addr ]
            and "Request" in self.ListOfDevices[ addr ][STORE_READ_CONFIGURE_REPORTING]
        ):
            Modules.tools.reset_device_attribute(self, STORE_READ_CONFIGURE_REPORTING, addr)

        # A plugin restart is a fresh start: drop any Configure Reporting mismatch backoff
        # counters so devices get a clean set of retry attempts.
        Modules.tools.reset_mismatch_retry_datastruct(self, STORE_CONFIGURE_REPORTING, addr)

        if (
            "Param" in self.ListOfDevices[addr] 
            and "Disabled" in self.ListOfDevices[addr]["Param"] 
            and self.ListOfDevices[addr]["Param"][ "Disabled" ]
        ):
            self.ListOfDevices[addr]["Health"] = "Disabled"
            
        if model_name and model_name == "ZLinky_TIC":
            # We need to adjust the Model to the right mode
            update_zlinky_device_model_if_needed(self, addr)

    if self.pluginconf.pluginConf["resetReadAttributes"]:
        self.pluginconf.pluginConf["resetReadAttributes"] = False
        self.pluginconf.write_Settings()

    if self.pluginconf.pluginConf["resetConfigureReporting"]:
        self.pluginconf.pluginConf["resetConfigureReporting"] = False
        self.pluginconf.write_Settings()

    load_new_param_definition(self)
    
    return res


def loadTxtDatabase(self, dbName):
    """Load and parse a legacy text device list file.

    The file contains lines with "key : <python-literal>" where the
    value is evaluated. Only entries with Version == '3' are loaded.

    Args:
        dbName: Path to the text database file to load

    Returns:
        str: "Success" when the parse completed without fatal problems,
             otherwise "Failed"
    """
    res = "Success"
    with open(dbName, "r", encoding='utf-8') as myfile2:
        self.log.logging("Database", "Debug", "Open : %s" % dbName)
        nb = 0
        for line in myfile2:
            if not line.strip():
                # Empty line
                continue
            (key, val) = line.split(":", 1)
            key = key.replace(" ", "")
            key = key.replace("'", "")
            # if key in  ( 'ffff', '0000'): continue
            if key in ("ffff"):
                continue
            try:
                dlVal = eval(val)  # nosec B307

            except (SyntaxError, NameError, TypeError, ZeroDivisionError):
                self.log.logging("Database", "Error", "LoadDeviceList failed on %s" % val)
                continue

            except Exception as e:
                self.log.logging("Database", "Error", f"LoadDeviceList unexpected error on {val} : {str(e)}")
                continue

            self.log.logging("Database", "Debug", "LoadDeviceList - " + str(key) + " => dlVal " + str(dlVal), key)
            if not dlVal.get("Version"):
                if key == "0000":  # Bug fixed in later version
                    continue
                self.log.logging("Database", "Error", "LoadDeviceList - entry " + key + " not loaded - not Version 3 - " + str(dlVal))
                res = "Failed"
                continue
            if int(dlVal["Version"]) > int(PLUGIN_DATABASE_RECORD_VERSION):
                self.log.logging("Database", "Error", f"LoadDeviceList - entry {key} not loaded - not Version {PLUGIN_DATABASE_RECORD_VERSION} or below\n" + str(dlVal))
                res = "Failed"
                continue
            else:
                nb += 1
                CheckDeviceList(self, key, val)
    return res


def retreive_device_list_from_domoticz(self):
    """Read device list from Domoticz plugin configuration.

    Returns:
        tuple: (devices_dict, timestamp) where devices_dict contains device
        entries filtered to only include known attributes used by the plugin
    """
    domoticz_configuration_record = getConfigItem(Key="ListOfDevices", Attribute="b64-devicelist")

    list_devices_from_domoticz = domoticz_configuration_record.get("b64-devicelist",{})
    if not isinstance(list_devices_from_domoticz, dict):
        self.log.logging(
            "Database",
            "Debug",
            f"Retrieved device list is not a dictionary. {list_devices_from_domoticz} with type {type(list_devices_from_domoticz)}. Initializing empty device list.",
        )
        return ({}, 0, 1)

    dz_timestamp = domoticz_configuration_record.get("TimeStamp",0) if list_devices_from_domoticz else 0
    human_date = time.strftime("%A, %Y-%m-%d %H:%M:%S", time.localtime(dz_timestamp))

    version = domoticz_configuration_record.get("Version", 1)
    
    self.log.logging(
        "Database",
        "Debug",
        f"Plugin data found on DZ with date {human_date} — version {version} Load from Dz: {len(list_devices_from_domoticz)} entries {list_devices_from_domoticz}"
    )
    allowed = set(MANDATORY_ATTRIBUTES) | set(MANUFACTURER_ATTRIBUTES) | set(BUILD_ATTRIBUTES)

    for device_id, attrs in list_devices_from_domoticz.items():
        self.log.logging("Database", "Debug", f"--- Loading {device_id}")

        for key in list(attrs):
            if key not in allowed:
                self.log.logging("Database", "Debug",
                                 f"xxx Removing attribute: {key} for {device_id}")
                attrs.pop(key)

    return (list_devices_from_domoticz, dz_timestamp, version)


def is_domoticz_recent(self, dz_timestamp, device_list_txt_filename):
    """Check if Domoticz database is more recent than local file.

    Args:
        dz_timestamp: Unix timestamp from Domoticz database
        device_list_txt_filename: Path to local device list file

    Returns:
        bool: True if Domoticz data is more recent than the file
    """
    txt_timestamp = 0
    if os.path.isfile(device_list_txt_filename):
        txt_timestamp = os.path.getmtime(device_list_txt_filename)

    self.log.logging("Database", "Log", "%s timestamp is %s versus Dz: %s" % (device_list_txt_filename, txt_timestamp, dz_timestamp))
    if dz_timestamp >= txt_timestamp:
        self.log.logging("Database", "Log", "Dz is more recent than Txt Dz: %s Txt: %s" % (dz_timestamp, txt_timestamp))
        return True
    return False

def request_flush_plugin_listofdevices(self):
    self.flush_list_of_devices = True


def flush_plugin_listofdevice(self):  # sourcery skip: merge-nested-ifs
    """Persist the in-memory DeviceList to disk and Domoticz storage.

    Uses heartbeat counting to throttle writes. Will write both legacy text
    format and optionally JSON format files. If enabled and available, will
    also persist to Domoticz plugin storage.

    Args:
        count: Number of heartbeats to wait between writes
    """
    if self.log:
        self.log.logging("Database", "Debug", "flush_plugin_listofdevice")

    if self.pluginconf.pluginConf["pluginData"] is None or self.DeviceListName is None:
        if self.log:
            self.log.logging("Database", "Error", "flush_plugin_listofdevice - self.pluginconf.pluginConf['pluginData']: %s , self.DeviceListName: %s" % (
                self.pluginconf.pluginConf["pluginData"], self.DeviceListName))
        return

    if self.pluginconf.pluginConf["expJsonDatabase"]:
        _write_DeviceList_json(self)

    # 1st we write the text file as it is the legacy format and we want to be sure to have it updated even if Domoticz Db write fails for some reason. 
    # We will have always a backup of the database in the text file. Finally as by default we read the most recent between Domoticz Db and text file.
    _write_DeviceList_txt(self)

    use_domoticz_db = self.pluginconf.pluginConf.get("useDomoticzDb")
    store_in_domoticz_db = self.pluginconf.pluginConf.get("storeDomoticzDb")
    self.log.logging("Database", "Debug", f"flush_plugin_listofdevice - useDomoticzDb: {use_domoticz_db} storeDomoticzDb: {store_in_domoticz_db}")

    if ( Modules.tools.is_domoticz_db_available(self) and ( use_domoticz_db and store_in_domoticz_db)):
        if _write_DeviceList_Domoticz(self) is None:
            # An error occured. Probably Dz.Configuration() is not available.
            self.log.logging("Database", "Error", "flush_plugin_listofdevice - flush Plugin db to Domoticz failed, we secure it to %s file" % self.DeviceListName)
            _write_DeviceList_txt(self)

    self.HBcount = 0
    self.flush_list_of_devices = False


def _write_DeviceList_txt(self):
    """Write device list in legacy text format.

    Writes one device per line in "key : <python-literal>" format.

    The write is performed crash-safely: records are written to a temporary
    file which is then atomically renamed over the target. This guarantees
    the on-disk database is never left truncated/partial if the plugin is
    interrupted while writing (for example killed during a restart), which
    otherwise causes records to be silently lost on the next load.

    We also iterate over a snapshot of the device list instead of the live
    ``self.ListOfDevices`` dict. At ``onStop()`` the database is flushed
    before the transport/forwarder threads are stopped, so an inbound message
    could mutate the dict mid-write and raise "dictionary changed size during
    iteration", aborting the write and corrupting the file.
    """
    _pluginData = Path( self.pluginconf.pluginConf["pluginData"] )
    _DeviceListFileName = _pluginData / self.DeviceListName
    _tmpFileName = _pluginData / (self.DeviceListName + ".tmp")

    # Snapshot to protect against concurrent mutation from other threads.
    snapshot = list(self.ListOfDevices.items())
    _count = 0
    try:
        self.log.logging("Database", "Debug", "Write %s = %s" % (_DeviceListFileName, str(self.ListOfDevices)))
        with open(_tmpFileName, "wt", encoding='utf-8') as file:
            for key, value in snapshot:
                try:
                    safe_value = _flatten_deques(value)  # converts deque -> list
                    file.write(f"{key} : {repr(safe_value)}\n")
                    _count += 1

                except UnicodeEncodeError:
                    self.log.logging( "Database", "Error", "UnicodeEncodeError while while saving %s : %s on file" %(
                        key, value))
                    continue

                except ValueError:
                    self.log.logging( "Database", "Error", "ValueError while saving %s : %s on file" %(
                        key, value))
                    continue

            # Make sure the bytes hit the disk before we swap the file in.
            self.log.logging("Database", "Debug", "_write_DeviceList_txt - flush Plugin db to %s" % _DeviceListFileName)
            file.flush()
            os.fsync(file.fileno())

        # Atomic replace: the target is either the previous content or the
        # fully written new content, never a partial file.
        os.replace(_tmpFileName, _DeviceListFileName)
        self.log.logging("Database", "Debug", "_write_DeviceList_txt - flush Plugin db to %s" % _DeviceListFileName)

    except FileNotFoundError:
        self.log.logging( "Database", "Error", "_write_DeviceList_txt - File not found >%s<" %_DeviceListFileName)

    except IOError:
        self.log.logging( "Database", "Error", "Error while Writing plugin Database %s" % _DeviceListFileName)

    finally:
        # Best effort cleanup of the temporary file if the rename did not happen.
        with contextlib.suppress(OSError):
            if os.path.isfile(_tmpFileName):
                os.remove(_tmpFileName)

    if _count != len(snapshot):
        self.log.logging("Database", "Error", f"Plugin Database flushed on disk {_DeviceListFileName} {_count}/{len(snapshot)} records")
    else:
        self.log.logging("Database", "Log", f"Plugin Database flushed on disk {_DeviceListFileName} {_count}/{len(snapshot)} records")


def _write_DeviceList_json(self):
    """Write device list as JSON file.

    Creates a JSON file alongside the text database with sorted keys
    and pretty printing enabled. Only called when JSON export is enabled
    in plugin configuration.
    """
    _pluginData = Path( self.pluginconf.pluginConf["pluginData"] )
    _DeviceListFileName = _pluginData / (self.DeviceListName[:-3] + "json")
    _tmpFileName = _pluginData / (self.DeviceListName[:-3] + "json.tmp")
    
    # Snapshot to avoid serialising a dict that other threads may mutate.
    snapshot = dict(self.ListOfDevices)
    self.log.logging("Database", "Debug", "Write %s = %s" % (_DeviceListFileName, str(snapshot)))
    try:
        with open(_tmpFileName, "wt") as file:
            json.dump(snapshot, file, sort_keys=True, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(_tmpFileName, _DeviceListFileName)
    finally:
        try:
            if os.path.isfile(_tmpFileName):
                os.remove(_tmpFileName)
        except OSError:
            pass
    self.log.logging("Database", "Debug", "_write_DeviceList_json - flush Plugin db to %s" % _DeviceListFileName)


def _write_DeviceList_Domoticz(self):
    """
    Store device list in Domoticz plugin configuration.

    Creates a JSON-safe snapshot of the device list and stores it
    with a timestamp in Domoticz plugin configuration storage.
    """

    ListOfDevices_for_save = _flatten_deques(self.ListOfDevices)

    self.log.logging(
        "Database",
        "Log",
        f"Plugin Database flushed on Domoticz {len(self.ListOfDevices)} records"
    )

    return setConfigItem(
        Key="ListOfDevices",
        Attribute="b64-devicelist",
        Value={
            "TimeStamp": time.time(),
            "b64-devicelist": ListOfDevices_for_save
        }
    )


def _sanitize_devices(devices):
    """
    Convert ListOfDevices into JSON-serializable structure.
    """
    def sanitize(value):
        if isinstance(value, deque):
            return list(value)
        if isinstance(value, dict):
            return {k: sanitize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [sanitize(v) for v in value]
        return value

    return sanitize(devices)


def _flatten_deques(obj):
    if isinstance(obj, deque):
        return list(obj)

    if isinstance(obj, dict):
        return {k: _flatten_deques(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_flatten_deques(v) for v in obj]

    return obj


def importDeviceConf(self):
    """Load legacy DeviceConf.txt configuration file.

    The file contains a Python literal which is evaluated into
    self.DeviceConf. Empty keys are removed afterwards. Returns
    None implicitly on success, or early on parse errors.
    """
    tmpread = ""
    self.DeviceConf = {}
    _pluginConfig = Path( self.pluginconf.pluginConf["pluginConfig"] )
    _DeviceConf = _pluginConfig / "DeviceConf.txt"
    if os.path.isfile(_DeviceConf):
        with open(_DeviceConf, "r") as myfile:
            tmpread += myfile.read().replace("\n", "")
            try:
                self.DeviceConf = eval(tmpread)  # nosec B307
            except (SyntaxError, NameError, TypeError, ZeroDivisionError):
                self.log.logging("Database", "Error", "Error while loading %s in line : %s" % (
                    self.pluginconf.pluginConf["pluginConfig"] + "DeviceConf.txt", tmpread) )
                return

    # Remove comments
    for iterDevType in list(self.DeviceConf):
        if iterDevType == "":
            del self.DeviceConf[iterDevType]

    self.log.logging("Database", "Status", "Z4D loads %s configuration from legacy database." % len(self.DeviceConf))


def import_local_device_conf(self):
    """Load JSON model definitions from Local-Devices folder.

    First loads legacy DeviceConf.txt, then processes each JSON file in the
    Local-Devices directory. Updates self.DeviceConf with model definitions
    and self.ModelManufMapping with any provided identifier mappings.

    Files named README.md and .PRECIOUS are skipped. JSON parse errors
    are logged but don't prevent processing other files.
    """
    from os import listdir
    from os.path import isfile, join

    # Read DeviceConf for backward compatibility
    importDeviceConf(self)
    legacy_config_loaded = len(self.DeviceConf)

    _pluginConfig = Path( self.pluginconf.pluginConf["pluginConfig"] )
    model_directory = _pluginConfig / "Local-Devices"

    if os.path.isdir(model_directory):
        model_list = [f for f in listdir(model_directory) if isfile(join(model_directory, f))]

        for model_device in model_list:
            if model_device in ("README.md", ".PRECIOUS"):
                continue

            filename = model_directory / model_device
            with open(filename, "rt", encoding='utf-8') as handle:
                try:
                    model_definition = json.load(handle)
                except ValueError as e:
                    self.log.logging("Database", "Error","--> JSON ConfFile: %s load failed with error: %s" % (filename, str(e)))

                    continue
                except Exception as e:
                    self.log.logging("Database", "Error","--> JSON ConfFile: %s load general error: %s" % (filename, str(e)))

                    continue

            try:
                device_model_name = model_device.rsplit(".", 1)[0]

                if device_model_name not in self.DeviceConf:
                    self.log.logging( "Database", "Debug", "--> Config for %s" % ( str(device_model_name)) )
                    self.DeviceConf[device_model_name] = dict(model_definition)
                    
                    self.log.logging("Database", "Status", f"++ Overwrite standard configuration model {device_model_name} with {filename}")

                    if "Identifier" in model_definition:
                        self.log.logging( "Database", "Debug", "--> Identifier found %s" % (str(model_definition["Identifier"])) )
                        for x in model_definition["Identifier"]:
                            self.log.logging( "Database", "Debug", "-->     %s" %x)
                            self.ModelManufMapping[ (x[0], x[1] )] = device_model_name
                            self.log.logging( "Database", "Status", f"++   Manufacturer mapping [ {x[0]}, {x[1]}" )
                        self.log.logging( "Database", "Status", "" )
                else:
                    self.log.logging(
                        "Database",
                        "Debug",
                        "--> Config for %s not loaded as already defined" % (str(device_model_name)),
                    )
            except Exception:
                self.log.logging("Database", "Error","--> Unexpected error when loading a configuration file")

    self.log.logging("Database", "Debug", "--> Config loaded: %s" % self.DeviceConf.keys())
    self.log.logging("Database", "Debug", "Local-Device ModelManufMapping loaded - %s" %self.ModelManufMapping.keys())
    self.log.logging("Database", "Status", "Z4D loads %s configuration from the local certified Db." %( len(self.DeviceConf) - legacy_config_loaded))


def checkDevices2LOD(self, Devices):
    """Mark each device with a consistency check flag.

    Compares IEEE addresses in self.ListOfDevices with Domoticz runtime
    devices and sets a ConsistencyCheck flag to "ok" or "not in DZ" for
    each device that has Status="inDB".

    Args:
        Devices: Dictionary of Domoticz device objects
    """
    for nwkid in self.ListOfDevices:
        self.ListOfDevices[nwkid]["ConsistencyCheck"] = ""
        if self.ListOfDevices[nwkid].get("Status") == "inDB":
            self.ListOfDevices[nwkid]["ConsistencyCheck"] = next(("ok" for dev in Devices if Devices[dev].DeviceID == self.ListOfDevices[nwkid]["IEEE"]), "not in DZ")


def checkListOfDevice2Devices(self, Devices):
    """Verify Domoticz widgets map to known plugin devices.

    Iterates self.ListOfDomoticzWidget and logs any widgets that cannot
    be mapped to a device in self.ListOfDevices via IEEE2NWK. Special
    device IDs like 4-char and Zigate-XX- prefixed ones are skipped.

    Args:
        Devices: Dictionary of Domoticz device objects (unused)
    """
    for widget_idx, widget_info in self.ListOfDomoticzWidget.items():
        self.log.logging("Database", "Debug", f"checkListOfDevice2Devices - {widget_idx} {type(widget_idx)} - {widget_info} {type(widget_info)}")
        
        device_id = widget_info["DeviceID"]
        widget_name = widget_info["Name"]

        self.log.logging("Database", "Debug", f"checkListOfDevice2Devices - {widget_idx} {device_id} {widget_name}")

        if len(device_id) == 4 or any(device_id.startswith(p) for p in ADMIN_WIDGET_PREFIXES):
            continue

        if device_id not in self.IEEE2NWK:
            self.log.logging("Database", "Log", f"checkListOfDevice2Devices - {widget_name} not found in the plugin!")
            continue

        nwkid = self.IEEE2NWK[device_id]
        if nwkid in self.ListOfDevices:
            self.log.logging("Database", "Debug", f"checkListOfDevice2Devices - found a matching entry for ID {widget_idx} as DeviceID {device_id} NWK_ID {nwkid}", nwkid)
        else:
            self.log.logging("Database", "Error", f"loadListOfDevices - {widget_name} with IEEE = {device_id} not found in the Zigate plugin Database!")


def saveZigateNetworkData(self, nkwdata):
    """Save Zigate network data to Zigate.json file.

    Args:
        nkwdata: Network data structure to save

    The data is written as pretty-printed JSON with sorted keys.
    IOErrors during write are caught and logged.
    """
    _pluginData = Path( self.pluginconf.pluginConf["pluginConfig"] )
    json_filename = _pluginData / "Zigate.json"
    self.log.logging("Database", "Debug", "Write " + json_filename + " = " + str(self.ListOfDevices))
    try:
        with open(json_filename, "wt", encoding='utf-8') as json_file:
            json.dump(nkwdata, json_file, indent=4, sort_keys=True)
    except IOError:
        self.log.logging("Database", "Error", "Error while writing Zigate Network Details%s" % json_filename)


def CheckDeviceList(self, key, val):
    """Import and validate a single device entry from the device list.

    Called during device list loading to process a single device. The
    function validates the device status, ensures no duplicates exist,
    and imports the appropriate attributes based on device type.

    Special handling is applied for device "0000" (coordinator) and
    for the resetPluginDS flag which limits imported attributes.

    Args:
        key: Network ID key as string
        val: String containing Python literal device data

    The function returns implicitly (None) and logs any validation
    errors encountered.
    """
    self.log.logging("Database", "Debug", "CheckDeviceList - Address search : " + str(key), key)
    self.log.logging("Database", "Debug2", "CheckDeviceList - with value : " + str(val), key)

    try:
        val = val.strip()  # Remove leading/trailing spaces or newlines
        device_list_dict = ast.literal_eval(val)

    except (SyntaxError, NameError, TypeError, ZeroDivisionError):
        self.log.logging("Database", "Error", "CheckDeviceList failed on %s" % val)
        return

    status = device_list_dict.get("Status")

    # Do not load Devices in State == 'unknown' or 'left'
    if status in ( "UNKNOW", "failDB", "DUP", "Removed" ):
        self.log.logging("Database", "Error", "Not Loading %s as Status: %s" % (key, status))
        return

    if key in self.ListOfDevices:
        # Suspect
        self.log.logging("Database", "Error", "CheckDeviceList - Object %s already in the plugin Db !!!" % key)
        return

    if Modules.tools.DeviceExist(self, key, device_list_dict.get("IEEE", "")):
        # Do not load Devices
        self.log.logging("Database", "Error", "Not Loading %s as no existing IEEE: %s" % (key, str(val)))
        return

    if key == "0000":
        self.ListOfDevices[key] = {"Status": ""}
    else:
        Modules.tools.initialize_device_record(self, key)

    self.ListOfDevices[key]["RIA"] = "10"

    # List of Attribnutes that will be Loaded from the deviceList-xx.txt database

    if self.pluginconf.pluginConf["resetPluginDS"]:
        self.log.logging("Database", "Status", "Z4D resets Build Attributes for %s" % device_list_dict["IEEE"])
        IMPORT_ATTRIBUTES = list(set(MANDATORY_ATTRIBUTES))

    elif key == "0000":
        # Reduce the number of Attributes loaded for Zigate
        self.log.logging(
            "Database", "Debug", "CheckDeviceList - Zigate (IEEE)  = %s Load Zigate Attributes" % device_list_dict["IEEE"]
        )
        IMPORT_ATTRIBUTES = list(set(CIE_ATTRIBUTES))
        self.log.logging("Database", "Debug", "--> Attributes loaded: %s" % IMPORT_ATTRIBUTES)
    else:
        self.log.logging(
            "Database", "Debug", "CheckDeviceList - DeviceID (IEEE)  = %s Load Full Attributes" % device_list_dict["IEEE"]
        )
        IMPORT_ATTRIBUTES = list(set(MANDATORY_ATTRIBUTES + BUILD_ATTRIBUTES + MANUFACTURER_ATTRIBUTES))

    self.log.logging("Database", "Debug", "--> Attributes loaded: %s" % IMPORT_ATTRIBUTES)
    for attribute in IMPORT_ATTRIBUTES:
        if attribute not in device_list_dict:
            # self.log.logging( "Database", 'Debug', "--> Attributes not existing: %s" %attribute)
            continue

        self.ListOfDevices[key][attribute] = device_list_dict[attribute]

        # Patching unitialize Model to empty
        if attribute == "Model" and self.ListOfDevices[key][attribute] == {}:
            self.ListOfDevices[key][attribute] = ""
        # If Model has a '/', just strip it as we strip it from now
        if attribute == "Model":
            OldModel = self.ListOfDevices[key][attribute]
            self.ListOfDevices[key][attribute] = self.ListOfDevices[key][attribute].replace("/", "")
            if OldModel != self.ListOfDevices[key][attribute]:
                self.log.logging("Database", "Status", "Z4D adjusts Model from %s to %s" % (
                    OldModel, self.ListOfDevices[key][attribute]))

    self.ListOfDevices[key]["Health"] = ""

    if "IEEE" in device_list_dict:
        self.ListOfDevices[key]["IEEE"] = device_list_dict["IEEE"]
        self.log.logging(
            "Database",
            "Debug",
            "CheckDeviceList - DeviceID (IEEE)  = " + str(device_list_dict["IEEE"]) + " for NetworkID = " + str(key),
            key,
        )
        if device_list_dict["IEEE"]:
            IEEE = device_list_dict["IEEE"]
            self.IEEE2NWK[IEEE] = key
        else:
            self.log.logging(
                "Database",
                "Log",
                "CheckDeviceList - IEEE = " + str(device_list_dict["IEEE"]) + " for NWKID = " + str(key),
                key,
            )

    profalux_fix_remote_device_model(self)
    check_and_update_manufcode(self)
    check_and_update_ForceAckCommands(self)


def check_and_update_ForceAckCommands(self):
    """Update ForceAckCommands list for devices based on model config.

    Iterates all devices and updates their ForceAckCommands list from
    the corresponding model configuration if available. Empty or missing
    model entries result in an empty ForceAckCommands list.
    """
    for x in self.ListOfDevices:
        if "Model" not in self.ListOfDevices[x]:
            continue
        if self.ListOfDevices[x]["Model"] in ("", {}):
            continue
        model = self.ListOfDevices[x]["Model"]

        if model not in self.DeviceConf:
            continue

        if "ForceAckCommands" not in self.DeviceConf[model]:
            self.ListOfDevices[x]["ForceAckCommands"] = []
            continue
        self.log.logging("Database", "Log"," Set: %s for device %s " % (self.DeviceConf[model]["ForceAckCommands"], x))
        self.ListOfDevices[x]["ForceAckCommands"] = list(self.DeviceConf[model]["ForceAckCommands"])


def fixing_consumption_lumi(self, key):
    """Remove legacy 'Consumption' entries from Lumi device endpoints.

    Args:
        key: Network ID of the device to process
    """
    for ep in self.ListOfDevices[key]["Ep"]:
        if "Consumption" in self.ListOfDevices[key]["Ep"][ep]:
            del self.ListOfDevices[key]["Ep"][ep]["Consumption"]


def fixing_Issue566(self, key):
    """Fix Issue #566 related to TRADFRI control outlet devices.

    Removes problematic Cluster Revision entries and corrects ClusterType
    assignment between endpoints 01 and 02.

    Args:
        key: Network ID of the device to process

    Returns:
        bool: True after applying fixes (or if no fixes needed)
    """
    if "Model" not in self.ListOfDevices[key]:
        return False
    if self.ListOfDevices[key]["Model"] != "TRADFRI control outlet":
        return False

    if "Cluster Revision" in self.ListOfDevices[key]["Ep"]:
        self.log.logging("Database", "Log", "++++Issue #566: Fixing Cluster Revision for NwkId: %s" % key)
        del self.ListOfDevices[key]["Ep"]["Cluster Revision"]
        res = True

    for ep in self.ListOfDevices[key]["Ep"]:
        if "Cluster Revision" in self.ListOfDevices[key]["Ep"][ep]:
            self.log.logging("Database", "Log","++++Issue #566 Cluster Revision NwkId: %s Ep: %s" % (key, ep))
            del self.ListOfDevices[key]["Ep"][ep]["Cluster Revision"]
            res = True

    if (
        "02" in self.ListOfDevices[key]["Ep"]
        and "01" in self.ListOfDevices[key]["Ep"]
        and "ClusterType" in self.ListOfDevices[key]["Ep"]["02"]
        and len(self.ListOfDevices[key]["Ep"]["02"]["ClusterType"]) != 0
        and "ClusterType" in self.ListOfDevices[key]["Ep"]["01"]
        and len(self.ListOfDevices[key]["Ep"]["01"]["ClusterType"]) == 0
    ):
        self.log.logging("Database", "Log","++++Issue #566 ClusterType mixing NwkId: %s Ep 01 and 02" % key)
        self.ListOfDevices[key]["Ep"]["01"]["ClusterType"] = dict(self.ListOfDevices[key]["Ep"]["02"]["ClusterType"])
        self.ListOfDevices[key]["Ep"]["02"]["ClusterType"] = {}
        res = True
    return True


def fixing_iSQN_None(self, key):
    """Remove iSQN entries that have None values.

    Iterates through device attributes related to reporting and removes
    any iSQN entries that have None values to prevent downstream errors.

    Args:
        key: Network ID of the device to process
    """
    for DeviceAttribute in (
        STORE_CONFIGURE_REPORTING,
        "ReadAttributes",
        "WriteAttributes",
    ):
        if DeviceAttribute not in self.ListOfDevices[key]:
            continue
        if "Ep" not in self.ListOfDevices[key][DeviceAttribute]:
            continue
        for endpoint in list(self.ListOfDevices[key][DeviceAttribute]["Ep"]):
            for clusterId in list(self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint]):
                if "iSQN" in self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]:
                    for attribute in list(self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"]):
                        if (
                            self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"][attribute]
                            is None
                        ):
                            del self.ListOfDevices[key][DeviceAttribute]["Ep"][endpoint][clusterId]["iSQN"][attribute]


def load_new_param_definition(self):
    """Populate missing device parameters from model definitions.

    For each device in ListOfDevices, copies default parameters from
    DeviceConf[model]['Param'] if they don't already exist. Some
    parameters are further mapped to plugin-wide configuration options
    based on the manufacturer (e.g. PowerOnAfterOffOn behavior).

    Special handling exists for:
    - PowerOnAfterOffOn (manufacturer-specific defaults)
    - PowerPollingFreq (device-specific polling intervals)
    - OnOffPollingFreq (manufacturer-specific polling)
    - AC201Polling (OWON/CASAIA specific)
    - Various Netatmo LED and control parameters
    """
    for key in self.ListOfDevices:
        if "Model" not in self.ListOfDevices[key]:
            continue
        if self.ListOfDevices[key]["Model"] not in self.DeviceConf:
            continue
        model_name = self.ListOfDevices[key]["Model"]
        if "Param" not in self.DeviceConf[model_name]:
            continue
        self.ListOfDevices[key]["CheckParam"] = True
        if "Param" not in self.ListOfDevices[key]:
            self.ListOfDevices[key]["Param"] = {}

        for param in self.DeviceConf[model_name]["Param"]:

            if param in self.ListOfDevices[key]["Param"]:
                continue

            # Initiatilize the parameter with the Configuration.
            self.ListOfDevices[key]["Param"][param] = self.DeviceConf[model_name]["Param"][param]

            if param == "Disabled" and "Disabled" in self.ListOfDevices[key]["Param"] and self.ListOfDevices[key]["Param"][ "Disabled" ]:
                self.ListOfDevices[key]["Health"] = "Disabled"
                
            if param in ("PowerOnAfterOffOn"):
                if "Manufacturer" not in self.ListOfDevices[key]:
                    return
                if self.ListOfDevices[key]["Manufacturer"] == "100b":  # Philips
                    self.ListOfDevices[key]["Param"][param] = self.pluginconf.pluginConf["PhilipsPowerOnAfterOffOn"]

                elif self.ListOfDevices[key]["Manufacturer"] == "1277":  # Enki Leroy Merlin
                    self.ListOfDevices[key]["Param"][param] = self.pluginconf.pluginConf["EnkiPowerOnAfterOffOn"]

                elif self.ListOfDevices[key]["Manufacturer"] == "1021":  # Legrand Netatmo
                    self.ListOfDevices[key]["Param"][param] = self.pluginconf.pluginConf["LegrandPowerOnAfterOffOn"]

                elif self.ListOfDevices[key]["Manufacturer"] == "117c":  # Ikea Tradfri
                    self.ListOfDevices[key]["Param"][param] = self.pluginconf.pluginConf["IkeaPowerOnAfterOffOn"]

            elif param in ("PowerPollingFreq",):
                POLLING_TABLE_SPECIFICS = {
                    "_TZ3000_g5xawfcq": "pollingBlitzwolfPower",
                    "LUMI": "pollingLumiPower",
                    "115f": "pollingLumiPower",
                }

                devManufCode = devManufName = ""
                if "Manufacturer" in self.ListOfDevices[key]:
                    devManufCode = self.ListOfDevices[key]["Manufacturer"]
                if "Manufacturer Name" in self.ListOfDevices[key]:
                    devManufName = self.ListOfDevices[key]["Manufacturer Name"]
                if devManufCode == devManufName == "":
                    return

                plugin_generic_param = None
                if devManufCode in POLLING_TABLE_SPECIFICS:
                    plugin_generic_param = POLLING_TABLE_SPECIFICS[devManufCode]
                if plugin_generic_param is None and devManufName in POLLING_TABLE_SPECIFICS:
                    plugin_generic_param = POLLING_TABLE_SPECIFICS[devManufName]

                if plugin_generic_param is None:
                    return False
                self.log.logging("Database", "Log","--->PluginConf %s <-- %s" % (param, plugin_generic_param))
                self.ListOfDevices[key]["Param"][param] = self.pluginconf.pluginConf[plugin_generic_param]

            elif param in ("OnOffPollingFreq",):
                POLLING_TABLE_SPECIFICS = {
                    "100b": "pollingPhilips",
                    "Philips": "pollingPhilips",
                    "GLEDOPTO": "pollingGledopto",
                }

                devManufCode = devManufName = ""
                if "Manufacturer" in self.ListOfDevices[key]:
                    devManufCode = self.ListOfDevices[key]["Manufacturer"]
                if "Manufacturer Name" in self.ListOfDevices[key]:
                    devManufName = self.ListOfDevices[key]["Manufacturer Name"]
                if devManufCode == devManufName == "":
                    return

                plugin_generic_param = None
                if devManufCode in POLLING_TABLE_SPECIFICS:
                    plugin_generic_param = POLLING_TABLE_SPECIFICS[devManufCode]
                if plugin_generic_param is None and devManufName in POLLING_TABLE_SPECIFICS:
                    plugin_generic_param = POLLING_TABLE_SPECIFICS[devManufName]

                if plugin_generic_param is None:
                    return False
                self.log.logging("Database", "Log","--->PluginConf %s <-- %s" % (param, plugin_generic_param))
                self.ListOfDevices[key]["Param"][param] = self.pluginconf.pluginConf[plugin_generic_param]

            elif param in ("AC201Polling",):
                POLLING_TABLE_SPECIFICS = {
                    "OWON": "pollingCasaiaAC201",
                    "CASAIA": "pollingCasaiaAC201",
                }

                devManufCode = devManufName = ""
                if "Manufacturer" in self.ListOfDevices[key]:
                    devManufCode = self.ListOfDevices[key]["Manufacturer"]
                if "Manufacturer Name" in self.ListOfDevices[key]:
                    devManufName = self.ListOfDevices[key]["Manufacturer Name"]
                if devManufCode == devManufName == "":
                    return

                plugin_generic_param = None
                if devManufCode in POLLING_TABLE_SPECIFICS:
                    plugin_generic_param = POLLING_TABLE_SPECIFICS[devManufCode]
                if plugin_generic_param is None and devManufName in POLLING_TABLE_SPECIFICS:
                    plugin_generic_param = POLLING_TABLE_SPECIFICS[devManufName]

                if plugin_generic_param is None:
                    return False
                self.log.logging("Database", "Log","--->PluginConf %s <-- %s" % (param, plugin_generic_param))
                self.ListOfDevices[key]["Param"][param] = self.pluginconf.pluginConf[plugin_generic_param]

            elif param == "netatmoLedIfOn":
                self.ListOfDevices[key]["Param"][param] = self.pluginconf.pluginConf["EnableLedIfOn"]
            elif param == "netatmoLedInDark":
                self.ListOfDevices[key]["Param"][param] = self.pluginconf.pluginConf["EnableLedInDark"]
            elif param == "netatmoLedShutter":
                self.ListOfDevices[key]["Param"][param] = self.pluginconf.pluginConf["EnableLedShutter"]
            elif param == "netatmoEnableDimmer":
                self.ListOfDevices[key]["Param"][param] = self.pluginconf.pluginConf["EnableDimmer"]
            elif param == "netatmoInvertShutter":
                self.ListOfDevices[key]["Param"][param] = self.pluginconf.pluginConf["InvertShutter"]
            elif param == "netatmoReleaseButton":
                self.ListOfDevices[key]["Param"][param] = self.pluginconf.pluginConf["EnableReleaseButton"]


def remove_legacy_topology_datas(self):
    """Remove legacy topology tables from all devices.

    Removes the following legacy tables from each device:
    - RoutingTable
    - AssociatedDevices
    - Neighbours

    These tables are no longer used with newer topology handling.
    """
    for device_info in self.ListOfDevices.values():
        for table_name in ("RoutingTable", "AssociatedDevices", "Neighbours"):
            device_info.pop(table_name, None)


def cleanup_table_entries( self):
    """Clean up invalid entries in device topology tables.

    Iterates through RoutingTable, AssociatedDevices and Neighbours
    tables for each device and removes entries that:
    - Are not lists
    - Missing Time or TimeStamp fields
    - Have Time as int but empty Devices list
    - Have Time field but not as an integer

    The cleanup runs in a loop to handle cases where removals affect
    list indices.
    """
    for tablename in ("RoutingTable", "AssociatedDevices", "Neighbours" ):
        self.log.logging("NetworkMap", "Debug", "purge processing %s " %( tablename))
        for nwkid in self.ListOfDevices:
            one_more_time = True
            while one_more_time:
                one_more_time = False
                self.log.logging("NetworkMap", "Debug", "purge processing %s %s" %( tablename, nwkid ))
                if tablename not in self.ListOfDevices[nwkid]:
                    continue
                if not isinstance(self.ListOfDevices[nwkid][tablename], list):
                    del self.ListOfDevices[nwkid][tablename]
                    continue
                idx = 0
                while idx < len(self.ListOfDevices[nwkid][tablename]):
                    self.log.logging("NetworkMap", "Debug", "purge processing %s %s %s \n %s" %( 
                        tablename, nwkid, idx , str(self.ListOfDevices[nwkid][tablename][ idx ])))
                    if (
                        "Time" not in self.ListOfDevices[nwkid][tablename][ idx ] 
                        or "TimeStamp" not in self.ListOfDevices[nwkid][tablename][ idx ]
                    ):
                        self.log.logging("NetworkMap", "Debug", "purge processing %s %s %s done" %( tablename, nwkid, idx ))
                        del self.ListOfDevices[nwkid][tablename][ idx ]
                        one_more_time = True
                        break
                    if (
                        isinstance(self.ListOfDevices[nwkid][tablename][idx]["Time"], int) 
                        and len(self.ListOfDevices[nwkid][tablename][idx]["Devices"]) == 0
                    ):
                        self.log.logging("NetworkMap", "Debug", "purge processing %s %s %s done" %( tablename, nwkid, idx ))
                        del self.ListOfDevices[nwkid][tablename][ idx ]
                        one_more_time = True
                        break
                    if (
                        "Time" in self.ListOfDevices[nwkid][tablename][ idx ]
                        and not isinstance(self.ListOfDevices[nwkid][tablename][ idx ]["Time"], int)
                    ):
                        self.log.logging("NetworkMap", "Debug", "purge processing %s %s %s done" %( tablename, nwkid, idx ))
                        del self.ListOfDevices[nwkid][tablename][ idx ]
                        one_more_time = True
                        break
                    idx += 1

          
def profalux_fix_remote_device_model(self):
    """Fix model names for Profalux remote devices.

    Identifies Profalux remote controls by their ZDeviceID (0201),
    Manufacturer code (1110) and MacCapa (80) and ensures they have:
    - Correct Manufacturer Name ("Profalux")
    - Correct Model name ("Telecommande-Profalux")
    """
    for x in self.ListOfDevices:
        
        if 'ZDeviceID' not in self.ListOfDevices[ x ] or self.ListOfDevices[ x ]['ZDeviceID'] != '0201':
            continue
        if "Manufacturer" not in self.ListOfDevices[ x ]:
            continue
        if self.ListOfDevices[ x ]["Manufacturer"] != "1110":
            continue
        if self.ListOfDevices[ x ]["Manufacturer Name"] != "Profalux":
            self.ListOfDevices[ x ]["Manufacturer Name"] = "Profalux"
        if "MacCapa" not in self.ListOfDevices[x]:
            continue
        if self.ListOfDevices[x]["MacCapa"] != "80":
            continue
        if "Model" in self.ListOfDevices[x] and self.ListOfDevices[x]["Model"] != "Telecommande-Profalux":
            self.log.logging("Profalux", "Status", "Z4D forces Model from %s to %s" % (
                x, self.ListOfDevices[x]["Model"],), x)
            self.ListOfDevices[x]["Model"] = "Telecommande-Profalux"


def hack_ts0601(self, nwkid):
    """Update model names for TS0601 devices based on manufacturer.

    Some TS0601 devices need their model names updated based on the
    manufacturer to ensure proper handling. This function:
    - Only processes devices with Model == 'TS0601'
    - Logs errors if manufacturer info is missing/invalid
    - Uses check_found_plugin_model() to determine correct model name
    - Updates the model name if a different one is suggested

    Args:
        nwkid: Network ID of the device to process
    """
    if ( 'Model' not in self.ListOfDevices[ nwkid ] or self.ListOfDevices[ nwkid ][ 'Model' ] != 'TS0601' ):
        return
    
    # This is a TS0601 based Model
    model_name = self.ListOfDevices[ nwkid ][ 'Model' ] 

    if 'Manufacturer Name' not in self.ListOfDevices[ nwkid ]:
        # This is not expected, log Error
        hack_ts0601_error(self, nwkid, model_name)
        return
    manuf_name = self.ListOfDevices[ nwkid ]['Manufacturer Name']
    
    if manuf_name in TUYA_MANUFACTURER_NAME:
        hack_ts0601_rename_model( self, nwkid, model_name, manuf_name)
        return
    hack_ts0601_error(self, nwkid, model_name, manufacturer=manuf_name)


def hack_ts0601_error(self, nwkid, model, manufacturer=None):
    """Log error details for TS0601 device configuration issues.

    Args:
        nwkid: Network ID of the problematic device
        model: Model name of the device
        manufacturer: Optional manufacturer information

    Logs device details to help troubleshoot TS0601 configuration
    problems.
    """
    self.log.logging("Tuya", "Error", "This device is not correctly configured, please contact us with the here after information")
    self.log.logging("Tuya", "Error", "    - Device        %s" %nwkid )
    self.log.logging("Tuya", "Error", "    - Model         %s" %model )
    self.log.logging("Tuya", "Error", "    - Manufacturer  %s" %manufacturer )
     

def hack_ts0601_rename_model( self, nwkid, modelName, manufacturer_name):
    """Update TS0601 model name based on manufacturer info.

    Uses check_found_plugin_model to determine the correct model name
    for a TS0601 device given its manufacturer. Updates the model name
    if a different one is suggested.

    Args:
        nwkid: Network ID of the device to update
        modelName: Current model name (should be 'TS0601')
        manufacturer_name: Manufacturer name to use for lookup
    """
    suggested_model = check_found_plugin_model( self, modelName, manufacturer_name=manufacturer_name, manufacturer_code=None, device_id=None )
    
    if self.ListOfDevices[ nwkid ][ 'Model' ] != suggested_model:
        self.log.logging("Tuya", "Status", "Z4D adjusts Model from %s to %s" % (modelName, suggested_model))
        self.ListOfDevices[ nwkid ][ 'Model' ] = suggested_model


def cleanup_ota(self, nwkid):
    """Clean up duplicate OTA upgrade entries.

    Processes OTAUpgrade entries for a device and removes duplicates
    based on Version and Type combinations. Keeps only the most recent
    entry for each unique combination.

    Args:
        nwkid: Network ID of the device to clean up
    """
    device = self.ListOfDevices.get(nwkid)
    if not device:
        return

    ota_upgrades = device.get("OTAUpgrade")
    if not ota_upgrades:
        return

    clean_ota = {}
    seen_versions = set()

    # Sort timestamps descending to keep latest versions first
    for stamp in sorted(ota_upgrades.keys(), key=lambda x: int(x), reverse=True):
        entry = ota_upgrades.get(stamp, {})
        version = entry.get("Version")
        image_type = entry.get("Type")
        time_stamp = entry.get("Time")

        if version is None or image_type is None or time_stamp is None:
            # Skip malformed entries
            continue

        key = (version, image_type)
        if key not in seen_versions:
            clean_ota[stamp] = {
                "Time": time_stamp,
                "Version": version,
                "Type": image_type,
            }
            seen_versions.add(key)

    if clean_ota:
        # Replace OTAUpgrade dict with the cleaned one
        self.ListOfDevices[nwkid]["OTAUpgrade"] = clean_ota

def force_removal_ota_update(self, nwkid):
    """
    force removal of OTAUpdate entry if it exists
    """
    self.ListOfDevices.get(nwkid, {}).pop("OTAUpdate", None)


def update_gamma_troniques_attributes_at_startup(self, nwkid):
    """Update GammaTroniques device attributes from endpoint data.

    Copies mode values from endpoint 01's ff42 cluster into the device's
    GammaTroniques attribute dictionary:
    - 002c -> ModeTIC
    - 002a -> ModeElect

    Args:
        nwkid: Network ID of the GammaTroniques device to update
    """
    self.log.logging("GammaTroniques", "Debug", f"update_gamma_troniques_attributes_at_startup - Nwkid: {nwkid}")

    device = self.ListOfDevices.get(nwkid)
    ep01 = device.get('Ep', {}).get('01') if device else None

    if not ep01:
        self.log.logging("GammaTroniques", "Debug", f"update_gamma_troniques_attributes_at_startup - Nwkid: {nwkid} No infos found")
        return

    ff42_infos = ep01.get("ff42", {})
    mode_tic = ff42_infos.get("002c")
    mode_elect = ff42_infos.get("002a")

    gamma = self.ListOfDevices[nwkid].setdefault("GammaTroniques", {})
    if mode_tic is not None:
        gamma["ModeTIC"] = mode_tic
    if mode_elect is not None:
        gamma["ModeElect"] = mode_elect
