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
    Module: z_database.py

    Description: Function to access Zigate Plugin Database & Dictionary

"""


import json
import os.path
import time
from pathlib import Path
from typing import Dict

from zigpy.backups import NetworkBackup

import Modules.tools
from Modules.domoticzAbstractLayer import getConfigItem, setConfigItem
from Modules.manufacturer_code import check_and_update_manufcode
from Modules.pluginDbAttributes import (STORE_CONFIGURE_REPORTING,
                                        STORE_CUSTOM_CONFIGURE_REPORTING,
                                        STORE_READ_CONFIGURE_REPORTING)
from Modules.pluginModels import check_found_plugin_model
from Modules.tuyaConst import TUYA_MANUFACTURER_NAME
from Modules.zlinky import update_zlinky_device_model_if_needed

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
    "CertifiedDevice"
)

MANUFACTURER_ATTRIBUTES = (
    "Legrand", 
    "Schneider", 
    "Lumi", 
    "LUMI", 
    "CASA.IA", 
    "Tuya", 
    "ZLinky",
    "Chameleon"
    )


def LoadDeviceList(self):
    # Load DeviceList.txt into ListOfDevices
    #
    ListOfDevices_from_Domoticz = None
    _pluginConf = Path( self.pluginconf.pluginConf["pluginData"] )
    txt_devicelist_filename = _pluginConf / self.DeviceListName

    # This can be enabled only with Domoticz version 2021.1 build 1395 and above, otherwise big memory leak
    ListOfDevices_from_Domoticz, saving_time = _read_DeviceList_Domoticz(self)

    if self.pluginconf.pluginConf["useDomoticzDatabase"] and is_domoticz_recent(self, saving_time, txt_devicelist_filename):
        self.log.logging( "Database", "Debug", "Database from Domoticz is recent: Loading from Domoticz Db")
        res = "Success"

        # Initialize the dictionaries directly from ListOfDevices_from_Domoticz
        self.ListOfDevices = dict(ListOfDevices_from_Domoticz.items())

        # Create IEEE2NWK by extracting the IEEE values
        self.IEEE2NWK = { device['IEEE']: nwkid for nwkid, device in self.ListOfDevices.items() if 'IEEE' in device }

        self.log.logging("Database", "Status", "Z4D %s entries loaded from Domoticz" % (len(self.ListOfDevices)))

    else:

        # Loading from TXT file
        if os.path.isfile(txt_devicelist_filename):
            res = loadTxtDatabase(self, txt_devicelist_filename)
        else:
            # Do not exist
            self.ListOfDevices = {}
            return True

        self.log.logging("Database", "Status", "Z4D loads %s entries from %s" % (len(self.ListOfDevices), txt_devicelist_filename))

        if ListOfDevices_from_Domoticz:
            self.log.logging( "Database", "Log", "==> Sanity check : Plugin Database loaded - %s entries from Domoticz, %s entries from DeviceList" % (
                len(ListOfDevices_from_Domoticz), len(self.ListOfDevices), ), )


        self.log.logging("Database", "Debug", "LoadDeviceList - DeviceList filename : %s" % txt_devicelist_filename)
        Modules.tools.helper_versionFile(txt_devicelist_filename, self.pluginconf.pluginConf["numDeviceListVersion"])

    # Keep the Size of the DeviceList in order to check changes
    self.DeviceListSize = os.path.getsize(txt_devicelist_filename)

    remove_stale_entries_from_tables( self)

    if self.pluginconf.pluginConf["ZigpyTopologyReport"]:
        # Cleanup the old Topology data
        remove_legacy_topology_datas(self)

    for nwkid in self.ListOfDevices:
        perform_cleanup_and_validation(self, nwkid)

    if self.pluginconf.pluginConf["resetReadAttributes"]:
        self.pluginconf.pluginConf["resetReadAttributes"] = False
        self.pluginconf.write_Settings()

    if self.pluginconf.pluginConf["resetConfigureReporting"]:
        self.pluginconf.pluginConf["resetConfigureReporting"] = False
        self.pluginconf.write_Settings()

    load_new_param_definition(self)

    return res


def perform_cleanup_and_validation(self, nwkid):
    """Perform cleanup and checks on the device data."""

    # Define actions and conditions for cleanup
    actions = [
        (fixing_consumption_lumi, True),
        (fixing_iSQN_None, True),
        (cleanup_ota, True),
        (hack_ts0601, True),
        (fixing_Issue566, self.pluginconf.pluginConf.get("Bug566") and self.ListOfDevices.get(nwkid, {}).get("Model") == "TRADFRI control outlet"),
        (Modules.tools.reset_datastruct, self.pluginconf.pluginConf.get("resetReadAttributes"), "ReadAttributes"),
        (Modules.tools.reset_datastruct, self.pluginconf.pluginConf.get("resetConfigureReporting"), STORE_CONFIGURE_REPORTING),
        (Modules.tools.reset_datastruct, self.pluginconf.pluginConf.get("resetConfigureReporting"), STORE_READ_CONFIGURE_REPORTING),
        (Modules.tools.reset_datastruct, self.ListOfDevices.get(nwkid, {}).get(STORE_READ_CONFIGURE_REPORTING, {}).get("Request"), STORE_READ_CONFIGURE_REPORTING),
        (update_device_health, self.ListOfDevices.get(nwkid, {}).get("Param", {}).get("Disabled")),
        (update_zlinky_device_model_if_needed, self.ListOfDevices.get(nwkid, {}).get("Model") == "ZLinky_TIC")
    ]

    # Execute each action if its condition is met
    for action in actions:
        func, condition = action[:2]
        args = action[2:] if len(action) > 2 else []
        if condition:
            self.log.logging("Database", "Log", f"{action} - {condition} -> {nwkid} {str(*args)}")
            func(self, nwkid, *args)

    # Log additional reset if needed
    if self.pluginconf.pluginConf.get("resetReadAttributes"):
        self.log.logging("Database", "Log", f"ReadAttributeReq - Reset ReadAttributes data {nwkid}")
    if self.pluginconf.pluginConf.get("resetConfigureReporting"):
        self.log.logging("Database", "Log", f"Reset ConfigureReporting data {nwkid}")


def update_device_health(self, nwkid):
    """Update the health status of the device to 'Disabled'."""
    if nwkid in self.ListOfDevices:
        self.ListOfDevices[nwkid]["Health"] = "Disabled"


def loadTxtDatabase(self, dbName):
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
                dlVal = eval(val)
            except (SyntaxError, NameError, TypeError, ZeroDivisionError):
                self.log.logging("Database", "Error", "LoadDeviceList failed on %s" % val)
                continue
            self.log.logging("Database", "Debug", "LoadDeviceList - " + str(key) + " => dlVal " + str(dlVal), key)
            if not dlVal.get("Version"):
                if key == "0000":  # Bug fixed in later version
                    continue
                self.log.logging("Database", "Error", "LoadDeviceList - entry " + key + " not loaded - not Version 3 - " + str(dlVal))
                res = "Failed"
                continue
            if dlVal["Version"] != "3":
                self.log.logging("Database", "Error", "LoadDeviceList - entry " + key + " not loaded - not Version 3 - " + str(dlVal))
                res = "Failed"
                continue
            else:
                nb += 1
                CheckDeviceList(self, key, val)
    return res


def _read_DeviceList_Domoticz(self):
    """ Retreive Plugin Db from Domoticz Configuration record"""

    configuration_record = getConfigItem(Key="ListOfDevices", Attribute="Devices")
    time_stamp = configuration_record.get("TimeStamp", 0)

    ListOfDevices_from_Domoticz = configuration_record.get("Devices", {})

    # Log timestamp if available
    if time_stamp:
        formatted_time = time.strftime("%A, %Y-%m-%d %H:%M:%S", time.localtime(time_stamp))
        self.log.logging("Database", "Debug", f"Plugin data found in Domoticz with date {formatted_time}")

    # Log number of devices and device data
    self.log.logging("Database", "Debug", f"Load plugin database from Domoticz: {len(ListOfDevices_from_Domoticz)} {ListOfDevices_from_Domoticz}")

    # Filter attributes for each device in ListOfDevices_from_Domoticz
    allowed_attributes = set(MANDATORY_ATTRIBUTES + MANUFACTURER_ATTRIBUTES + BUILD_ATTRIBUTES)
    for device_id, device_data in ListOfDevices_from_Domoticz.items():
        self.log.logging("Database", "Debug", f"--- Loading {device_id}")

        # Remove any attributes that aren't in the allowed set
        for attribute in list(device_data):
            if attribute not in allowed_attributes:
                self.log.logging("Database", "Debug", f"xxx Removing attribute: {attribute} for {device_id}")
                del device_data[attribute]

    return ListOfDevices_from_Domoticz, time_stamp


def is_domoticz_recent(self, dz_timestamp, filename):
    txt_timestamp = os.path.getmtime(filename) if os.path.isfile(filename) else 0

    comparison = "more recent" if dz_timestamp > txt_timestamp else "older"
    self.log.logging("Database", "Log", f"{filename} - Domoticz Timestamp is {comparison} than Filename ({dz_timestamp} versus {txt_timestamp})")

    return dz_timestamp > txt_timestamp


def WriteDeviceList(self, count):  # sourcery skip: merge-nested-ifs
    # In case count = -1 we request to force a write also on the Domoticz Database (when onStop is called)
    # When count = 0 we force a write

    if count != -1 and self.HBcount < count:
        self.HBcount = self.HBcount + 1
        return

    self.log.logging("Database", "Debug", "WriteDeviceList %s %s" %(self.HBcount, count))
    if self.pluginconf.pluginConf["pluginData"] is None or self.DeviceListName is None:
        self.log.logging("Database", "Error", "WriteDeviceList - self.pluginconf.pluginConf['pluginData']: %s , self.DeviceListName: %s" % (
            self.pluginconf.pluginConf["pluginData"], self.DeviceListName))
        return

    if self.pluginconf.pluginConf["expJsonDatabase"]:
        _write_DeviceList_json(self)

    _write_DeviceList_txt(self)

    if (
        count == -1
        and ( self.pluginconf.pluginConf["useDomoticzDatabase"] or self.pluginconf.pluginConf["storeDomoticzDatabase"]) 
    ):
        if _write_DeviceList_Domoticz(self) is None:
            # An error occured. Probably Dz.Configuration() is not available.
            _write_DeviceList_txt(self)

    self.HBcount = 0


def _write_DeviceList_txt(self):
    # Write in classic format ( .txt )
    _pluginData = Path( self.pluginconf.pluginConf["pluginData"] )
    _DeviceListFileName = _pluginData / self.DeviceListName
    try:
        self.log.logging("Database", "Debug", "Write %s = %s" % (_DeviceListFileName, str(self.ListOfDevices)))
        with open(_DeviceListFileName, "wt", encoding='utf-8') as file:
            for key in self.ListOfDevices:
                try:
                    file.write(key + " : " + str(self.ListOfDevices[key]) + "\n")
                    
                except UnicodeEncodeError:
                    self.log.logging( "Database", "Error", "UnicodeEncodeError while while saving %s : %s on file" %( 
                        key, self.ListOfDevices[key]))
                    continue

                except ValueError:
                    self.log.logging( "Database", "Error", "ValueError while saving %s : %s on file" %( 
                        key, self.ListOfDevices[key]))
                    continue
                
                except IOError:
                    self.log.logging( "Database", "Error", "IOError while writing to plugin Database %s" % _DeviceListFileName)
                    continue

        self.log.logging("Database", "Debug", "WriteDeviceList - flush Plugin db to %s" % _DeviceListFileName)
        
    except FileNotFoundError:
        self.log.logging( "Database", "Error", "WriteDeviceList - File not found >%s<" %_DeviceListFileName)
        
    except IOError:
        self.log.logging( "Database", "Error", "Error while Writing plugin Database %s" % _DeviceListFileName)


def _write_DeviceList_json(self):
    _pluginData = Path( self.pluginconf.pluginConf["pluginData"] )
# Incorrect error issue    
#    _DeviceListFileName = _pluginData / self.DeviceListName[:-3] + "json"
    _DeviceListFileName = _pluginData / (self.DeviceListName[:-3] + "json")
    self.log.logging("Database", "Debug", "Write %s = %s" % (_DeviceListFileName, str(self.ListOfDevices)))
    with open(_DeviceListFileName, "wt") as file:
        json.dump(self.ListOfDevices, file, sort_keys=True, indent=2)
    self.log.logging("Database", "Debug", "WriteDeviceList - flush Plugin db to %s" % _DeviceListFileName)


def _write_DeviceList_Domoticz(self):
    ListOfDevices_for_save = self.ListOfDevices.copy()
    self.log.logging("Database", "Debug", "WriteDeviceList - flush Plugin db to %s" % "Domoticz Sqlite Db")
    self.log.logging("Database", "Status", "+ Saving plugin database into Domoticz")

    return setConfigItem( Key="ListOfDevices", Attribute="Devices", Value={"TimeStamp": time.time(), "Devices": ListOfDevices_for_save} )


def write_coordinator_backup_domoticz(self, coordinator_backup):
    self.log.logging("Database", "Log", "write_coordinator_backup_domoticz - saving coordinator data to Domoticz Sqlite Db type: %s" %type(coordinator_backup))
    self.log.logging("Database", "Status", "+ Saving Coordinator database into Domoticz")

    return setConfigItem( Key="CoordinatorBackup", Attribute="NetworkBackup", Value={"TimeStamp": time.time(), "NetworkBackup": coordinator_backup } )


def read_coordinator_backup_domoticz(self):

    coordinator_backup = getConfigItem(Key="CoordinatorBackup", Attribute="NetworkBackup")
    self.log.logging( "Database", "Debug", "Coordinator backup entry from Domoticz %s" % str(coordinator_backup))

    time_stamp = coordinator_backup["TimeStamp"] if "TimeStamp" in coordinator_backup else 0
    coordinator_network_backup = coordinator_backup["NetworkBackup"] if "NetworkBackup" in coordinator_backup else None

    self.log.logging( "Database", "Debug", "Coordinator data found on DZ with date %s" % (
        time.strftime("%A, %Y-%m-%d %H:%M:%S", time.localtime(time_stamp))), )

    if coordinator_network_backup:
        self.log.logging( "Database", "Debug", "Load from Dz: %s %s %s" % (
            len(coordinator_network_backup), str(coordinator_network_backup), type(coordinator_network_backup) ))

    return (coordinator_network_backup, time_stamp)


def importDeviceConf(self):
    # Import DeviceConf.txt
    tmpread = ""
    self.DeviceConf = {}
    _pluginConfig = Path( self.pluginconf.pluginConf["pluginConfig"] )
    _DeviceConf = _pluginConfig / "DeviceConf.txt"
    if os.path.isfile(_DeviceConf):
        with open(_DeviceConf, "r") as myfile:
            tmpread += myfile.read().replace("\n", "")
            try:
                self.DeviceConf = eval(tmpread)
            except (SyntaxError, NameError, TypeError, ZeroDivisionError):
                self.log.logging("Database", "Error", "Error while loading %s in line : %s" % (
                    self.pluginconf.pluginConf["pluginConfig"] + "DeviceConf.txt", tmpread) )
                return

    # Remove comments
    for iterDevType in list(self.DeviceConf):
        if iterDevType == "":
            del self.DeviceConf[iterDevType]

    self.log.logging("Database", "Status", "Z4D loaded %s configuration from legacy database." %len(self.DeviceConf))


def import_local_device_conf(self):

    from os import listdir
    from os.path import isfile, join

    # Read DeviceConf for backward compatibility
    importDeviceConf(self)
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

                    if "Identifier" in model_definition:
                        self.log.logging( "Database", "Debug", "--> Identifier found %s" % (str(model_definition["Identifier"])) )
                        for x in model_definition["Identifier"]:
                            self.log.logging( "Database", "Debug", "-->     %s" %x)
                            self.ModelManufMapping[ (x[0], x[1] )] = device_model_name
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
    self.log.logging("Database", "Status", "Z4D loads %s configuration from the local certified Db." %len(self.DeviceConf))


def checkDevices2LOD(self, Devices):

    for nwkid in self.ListOfDevices:
        self.ListOfDevices[nwkid]["ConsistencyCheck"] = ""
        if self.ListOfDevices[nwkid]["Status"] == "inDB":
            self.ListOfDevices[nwkid]["ConsistencyCheck"] = next(("ok" for dev in Devices if Devices[dev].DeviceID == self.ListOfDevices[nwkid]["IEEE"]), "not in DZ")


def checkListOfDevice2Devices(self, Devices):
    """ This function is checking if any entry in Domoticz has a correspondance in ListOfDevices (Plugin database)"""

    for widget_idx, widget_info in self.ListOfDomoticzWidget.items():
        # Extract device ID and name for convenience
        device_id = widget_info["DeviceID"]
        widget_name = widget_info["Name"]

        # Log details for debugging
        self.log.logging("Database", "Debug", f"checkListOfDevice2Devices - Widget ID: {widget_idx} ({type(widget_idx)}), Device Info: {widget_info} ({type(widget_info)})")
        self.log.logging("Database", "Debug", f"checkListOfDevice2Devices - Device ID: {device_id}, Name: {widget_name}")

        # Skip invalid or specific device ID patterns
        if len(device_id) == 4 or device_id.startswith(("Zigate-01-", "Zigate-02-", "Zigate-03-")):
            continue

        # Check if the device ID exists in the IEEE to NWK mapping
        nwkid = self.IEEE2NWK.get(device_id)
        if nwkid:
            # Confirm if nwkid exists in ListOfDevices
            if nwkid in self.ListOfDevices:
                self.log.logging("Database", "Debug", f"checkListOfDevice2Devices - Found match for Widget ID: {widget_idx}, Device ID: {device_id}, NWK_ID: {nwkid}")
            else:
                self.log.logging("Database", "Error", f"loadListOfDevices - {widget_name} with IEEE = {device_id} not found in the Zigate plugin Database!")
        else:
            self.log.logging("Database", "Log", f"checkListOfDevice2Devices - {widget_name} not found in the plugin!")


def saveZigateNetworkData(self, nkwdata):
    _pluginData = Path( self.pluginconf.pluginConf["pluginConfig"] )
    json_filename = _pluginData / "Zigate.json"
    self.log.logging("Database", "Debug", "Write " + json_filename + " = " + str(self.ListOfDevices))
    try:
        with open(json_filename, "wt", encoding='utf-8') as json_file:
            json.dump(nkwdata, json_file, indent=4, sort_keys=True)
    except IOError:
        self.log.logging("Database", "Error", "Error while writing Zigate Network Details%s" % json_filename)


def CheckDeviceList(self, key, val):
    """
    This function is call during DeviceList load
    """

    self.log.logging("Database", "Debug", "CheckDeviceList - Address search : " + str(key), key)
    self.log.logging("Database", "Debug2", "CheckDeviceList - with value : " + str(val), key)

    DeviceListVal = eval(val)
    # Do not load Devices in State == 'unknown' or 'left'
    if "Status" in DeviceListVal and DeviceListVal["Status"] in (
        "UNKNOW",
        "failDB",
        "DUP",
        "Removed"
    ):
        self.log.logging("Database", "Error", "Not Loading %s as Status: %s" % (key, DeviceListVal["Status"]))
        return

    if key in self.ListOfDevices:
        # Suspect
        self.log.logging("Database", "Error", "CheckDeviceList - Object %s already in the plugin Db !!!" % key)
        return

    if Modules.tools.DeviceExist(self, key, DeviceListVal.get("IEEE", "")):
        # Do not load Devices
        self.log.logging("Database", "Error", "Not Loading %s as no existing IEEE: %s" % (key, str(val)))
        return

    if key == "0000":
        self.ListOfDevices[key] = {"Status": ""}
    else:
        Modules.tools.initDeviceInList(self, key)

    self.ListOfDevices[key]["RIA"] = "10"

    # List of Attribnutes that will be Loaded from the deviceList-xx.txt database

    if self.pluginconf.pluginConf["resetPluginDS"]:
        self.log.logging("Database", "Status", "Z4D resets Build Attributes for %s" % DeviceListVal["IEEE"])
        IMPORT_ATTRIBUTES = list(set(MANDATORY_ATTRIBUTES))

    elif key == "0000":
        # Reduce the number of Attributes loaded for Zigate
        self.log.logging(
            "Database", "Debug", "CheckDeviceList - Zigate (IEEE)  = %s Load Zigate Attributes" % DeviceListVal["IEEE"]
        )
        IMPORT_ATTRIBUTES = list(set(CIE_ATTRIBUTES))
        self.log.logging("Database", "Debug", "--> Attributes loaded: %s" % IMPORT_ATTRIBUTES)
    else:
        self.log.logging(
            "Database", "Debug", "CheckDeviceList - DeviceID (IEEE)  = %s Load Full Attributes" % DeviceListVal["IEEE"]
        )
        IMPORT_ATTRIBUTES = list(set(MANDATORY_ATTRIBUTES + BUILD_ATTRIBUTES + MANUFACTURER_ATTRIBUTES))

    self.log.logging("Database", "Debug", "--> Attributes loaded: %s" % IMPORT_ATTRIBUTES)
    for attribute in IMPORT_ATTRIBUTES:
        if attribute not in DeviceListVal:
            # self.log.logging( "Database", 'Debug', "--> Attributes not existing: %s" %attribute)
            continue

        self.ListOfDevices[key][attribute] = DeviceListVal[attribute]

        # Patching unitialize Model to empty
        if attribute == "Model" and self.ListOfDevices[key][attribute] == {}:
            self.ListOfDevices[key][attribute] = ""
        # If Model has a '/', just strip it as we strip it from now
        if attribute == "Model":
            OldModel = self.ListOfDevices[key][attribute]
            self.ListOfDevices[key][attribute] = self.ListOfDevices[key][attribute].replace("/", "")
            if OldModel != self.ListOfDevices[key][attribute]:
                self.log.logging("Database", "Status", "Z4D adjusted Model from %s to %s" % (
                    OldModel, self.ListOfDevices[key][attribute]))

    self.ListOfDevices[key]["Health"] = ""

    if "IEEE" in DeviceListVal:
        self.ListOfDevices[key]["IEEE"] = DeviceListVal["IEEE"]
        self.log.logging(
            "Database",
            "Debug",
            "CheckDeviceList - DeviceID (IEEE)  = " + str(DeviceListVal["IEEE"]) + " for NetworkID = " + str(key),
            key,
        )
        if DeviceListVal["IEEE"]:
            IEEE = DeviceListVal["IEEE"]
            self.IEEE2NWK[IEEE] = key
        else:
            self.log.logging(
                "Database",
                "Log",
                "CheckDeviceList - IEEE = " + str(DeviceListVal["IEEE"]) + " for NWKID = " + str(key),
                key,
            )

    profalux_fix_remote_device_model(self)
    check_and_update_manufcode(self)
    check_and_update_ForceAckCommands(self)


def check_and_update_ForceAckCommands(self):

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

    for ep in self.ListOfDevices[key]["Ep"]:
        if "Consumption" in self.ListOfDevices[key]["Ep"][ep]:
            del self.ListOfDevices[key]["Ep"][ep]["Consumption"]


def fixing_Issue566(self, key):

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

            # Overwrite the param by Existing Global parameter
            # if param in ( 'fadingOff', 'moveToHueSatu'  ,'moveToColourTemp','moveToColourRGB','moveToLevel'):
            #     # Use Global as default
            #     if self.DeviceConf[ model_name ]['Param'][ param ] != self.pluginconf.pluginConf[ param ]:
            #         self.ListOfDevices[ key ]['Param'][ param ] = self.pluginconf.pluginConf[ param ]

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
    for device_info in self.ListOfDevices.values():
        for table_name in ("RoutingTable", "AssociatedDevices", "Neighbours"):
            device_info.pop(table_name, None)


def remove_stale_entries_from_tables( self):

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
            self.log.logging( "Profalux", "Status", "Z4D forces Model Name from %s to %s" % (
                x, self.ListOfDevices[x]["Model"],), x)
            self.ListOfDevices[x]["Model"] = "Telecommande-Profalux"


def hack_ts0601(self, nwkid):
    # Purpose is to rename the Model name of potential working TS0601 as a Thermostat
    
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
    # Looks like we have a TS0601 and something wrong !!!
    self.log.logging("Tuya", "Error", "This device is not correctly configured, please contact us with the here after information")
    self.log.logging("Tuya", "Error", "    - Device        %s" %nwkid )
    self.log.logging("Tuya", "Error", "    - Model         %s" %model )
    self.log.logging("Tuya", "Error", "    - Manufacturer  %s" %manufacturer )


def hack_ts0601_rename_model( self, nwkid, modelName, manufacturer_name):

    suggested_model = check_found_plugin_model( self, modelName, manufacturer_name=manufacturer_name, manufacturer_code=None, device_id=None )
    
    if self.ListOfDevices[ nwkid ][ 'Model' ] != suggested_model:
        self.log.logging("Tuya", "Status", "Z4D adjusts Model name from %s to %s" %( modelName, suggested_model))
        self.ListOfDevices[ nwkid ][ 'Model' ] = suggested_model


def cleanup_ota(self, nwkid):
    
    if "OTAUpgrade" not in self.ListOfDevices[ nwkid ]:
        return

    existing_upgrade = []
    clean_ota = {}

    for stamp in sorted(self.ListOfDevices[ nwkid ]["OTAUpgrade"].keys(), reverse=True ):
        version = self.ListOfDevices[ nwkid ]["OTAUpgrade"][ stamp ]["Version"]
        image_type = self.ListOfDevices[ nwkid ]["OTAUpgrade"][ stamp ]["Type"]
        if ( version, image_type) not in existing_upgrade:
            time_stamp = self.ListOfDevices[ nwkid ]["OTAUpgrade"][ stamp ]["Time"]
            clean_ota[ stamp ] = {
                "Time": time_stamp,
                "Version": version,
                "Type": image_type,
            }
            existing_upgrade.append( ( version, image_type) )
            continue
    if clean_ota:
        del self.ListOfDevices[ nwkid ]["OTAUpgrade"]
        self.ListOfDevices[ nwkid ]["OTAUpgrade"] = dict(clean_ota)
