#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_database.py

    Description: Function to access Zigate Plugin Database & Dictionary

"""

import json
import os.path
import time
from typing import Dict

import Domoticz

import Modules.tools
from Modules.manufacturer_code import check_and_update_manufcode

ZIGATE_ATTRIBUTES = {
    "Version",
    "ZDeviceName",
    "Ep",
    "IEEE",
    "LogicalType",
    "PowerSource",
    "Neighbours",
    "GroupMemberShip",
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
)

# List of Attributes whcih are going to be loaded, ut in case of Reset (resetPluginDS) they will be re-initialized.
BUILD_ATTRIBUTES = (
    "NeighbourTableSize",
    "BindingTable",
    "RoutingTable",
    "Battery",
    "BatteryUpdateTime",
    "GroupMemberShip",
    "Neighbours",
    "ConfigureReporting",
    "ReadAttributes",
    "WriteAttributes",
    "LQI",
    "SQN",
    "Stamp",
    "Health",
    "IASBattery",
    "Operating Time",
    "DelayBindingAtPairing"
)

MANUFACTURER_ATTRIBUTES = ("Legrand", "Schneider", "Lumi", "LUMI", "CASA.IA", "Tuya", "ZLinky")


def _copyfile(source, dest, move=True):

    try:
        import shutil

        if move:
            shutil.move(source, dest)
        else:
            shutil.copy(source, dest)
    except:
        with open(source, "r") as src, open(dest, "wt") as dst:
            for line in src:
                dst.write(line)


def _versionFile(source, nbversion):

    if nbversion == 0:
        return

    if nbversion == 1:
        _copyfile(source, source + "-%02d" % 1)
    else:
        for version in range(nbversion - 1, 0, -1):
            _fileversion_n = source + "-%02d" % version
            if not os.path.isfile(_fileversion_n):
                continue
            else:
                _fileversion_n1 = source + "-%02d" % (version + 1)
                _copyfile(_fileversion_n, _fileversion_n1)

        # Last one
        _copyfile(source, source + "-%02d" % 1, move=False)


def LoadDeviceList(self):
    # Load DeviceList.txt into ListOfDevices
    #
    # Let's check if we have a .json version. If so, we will be using it, otherwise
    # we fall back to the old fashion .txt
    jsonFormatDB = True

    # This can be enabled only with Domoticz version 2021.1 build 1395 and above, otherwise big memory leak

    if Modules.tools.is_domoticz_db_available(self) and self.pluginconf.pluginConf["useDomoticzDatabase"]:
        ListOfDevices_from_Domoticz, saving_time = _read_DeviceList_Domoticz(self)
        Domoticz.Log(
            "Database from Dz is recent: %s Loading from Domoticz Db"
            % is_domoticz_recent(self, saving_time, self.pluginconf.pluginConf["pluginData"] + self.DeviceListName)
        )

    if self.pluginconf.pluginConf["expJsonDatabase"]:
        if os.path.isfile(self.pluginconf.pluginConf["pluginData"] + self.DeviceListName[:-3] + "json"):
            # JSON Format
            _DeviceListFileName = self.pluginconf.pluginConf["pluginData"] + self.DeviceListName[:-3] + "json"
            jsonFormatDB = True
            res = loadJsonDatabase(self, _DeviceListFileName)

        elif os.path.isfile(self.pluginconf.pluginConf["pluginData"] + self.DeviceListName):
            _DeviceListFileName = self.pluginconf.pluginConf["pluginData"] + self.DeviceListName
            jsonFormatDB = False
            res = loadTxtDatabase(self, _DeviceListFileName)
        else:
            # Do not exist
            self.ListOfDevices = {}
            return True
    else:
        if os.path.isfile(self.pluginconf.pluginConf["pluginData"] + self.DeviceListName):
            _DeviceListFileName = self.pluginconf.pluginConf["pluginData"] + self.DeviceListName
            jsonFormatDB = False
            res = loadTxtDatabase(self, _DeviceListFileName)
        else:
            # Do not exist
            self.ListOfDevices = {}
            return True

    self.log.logging("Database", "Debug", "LoadDeviceList - DeviceList filename : " + _DeviceListFileName)
    _versionFile(_DeviceListFileName, self.pluginconf.pluginConf["numDeviceListVersion"])

    # Keep the Size of the DeviceList in order to check changes
    self.DeviceListSize = os.path.getsize(_DeviceListFileName)

    for addr in self.ListOfDevices:
        # Fixing mistake done in the code.
        fixing_consumption_lumi(self, addr)

        fixing_iSQN_None(self, addr)

        # Check if 566 fixs are needed
        if self.pluginconf.pluginConf["Bug566"]:
            if "Model" in self.ListOfDevices[addr]:
                if self.ListOfDevices[addr]["Model"] == "TRADFRI control outlet":
                    fixing_Issue566(self, addr)

        if self.pluginconf.pluginConf["resetReadAttributes"]:
            self.log.logging("Database", "Log", "ReadAttributeReq - Reset ReadAttributes data %s" % addr)
            Modules.tools.reset_datastruct(self, "ReadAttributes", addr)
            # self.ListOfDevices[addr]['ReadAttributes'] = {}
            # self.ListOfDevices[addr]['ReadAttributes']['Ep'] = {}
            # for iterEp in self.ListOfDevices[addr]['Ep']:
            #    self.ListOfDevices[addr]['ReadAttributes']['Ep'][iterEp] = {}

        if self.pluginconf.pluginConf["resetConfigureReporting"]:
            self.log.logging("Database", "Log", "Reset ConfigureReporting data %s" % addr)
            Modules.tools.reset_datastruct(self, "ConfigureReporting", addr)
            # self.ListOfDevices[addr]['ConfigureReporting'] = {}
            # self.ListOfDevices[addr]['ConfigureReporting']['Ep'] = {}
            # for iterEp in self.ListOfDevices[addr]['Ep']:
            #    self.ListOfDevices[addr]['ConfigureReporting']['Ep'][iterEp] = {}

    if self.pluginconf.pluginConf["resetReadAttributes"]:
        self.pluginconf.pluginConf["resetReadAttributes"] = False
        self.pluginconf.write_Settings()

    if self.pluginconf.pluginConf["resetConfigureReporting"]:
        self.pluginconf.pluginConf["resetConfigureReporting"] = False
        self.pluginconf.write_Settings()

    load_new_param_definition(self)
    self.log.logging("Database", "Status", "%s Entries loaded from %s" % (len(self.ListOfDevices), _DeviceListFileName))

    if Modules.tools.is_domoticz_db_available(self) and self.pluginconf.pluginConf["useDomoticzDatabase"]:
        self.log.logging(
            "Database",
            "Log",
            "Plugin Database loaded - BUT NOT USE - from Dz: %s from DeviceList: %s, checking deltas "
            % (
                len(ListOfDevices_from_Domoticz),
                len(self.ListOfDevices),
            ),
        )
        #try:
        #    import sys
#
        #    sys.path.append("/usr/lib/python3.8/site-packages")
        #    import deepdiff
#
        #    diff = deepdiff.DeepDiff(self.ListOfDevices, ListOfDevices_from_Domoticz)
        #    self.log.logging("Database", "Log", json.dumps(json.loads(diff.to_json()), indent=4))
#
        #except:
        #    # self.log.logging("Database", "Log", "Python Module deepdiff not found")
        #    pass

    return res


def loadTxtDatabase(self, dbName):
    res = "Success"
    with open(dbName, "r") as myfile2:
        self.log.logging("Database", "Debug", "Open : " + dbName)
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
                Domoticz.Error("LoadDeviceList failed on %s" % val)
                continue
            self.log.logging("Database", "Debug2", "LoadDeviceList - " + str(key) + " => dlVal " + str(dlVal), key)
            if not dlVal.get("Version"):
                if key == "0000":  # Bug fixed in later version
                    continue
                Domoticz.Error("LoadDeviceList - entry " + key + " not loaded - not Version 3 - " + str(dlVal))
                res = "Failed"
                continue
            if dlVal["Version"] != "3":
                Domoticz.Error("LoadDeviceList - entry " + key + " not loaded - not Version 3 - " + str(dlVal))
                res = "Failed"
                continue
            else:
                nb += 1
                CheckDeviceList(self, key, val)
    return res


def loadJsonDatabase(self, dbName):
    res = "Success"
    with open(dbName, "rt") as handle:
        _listOfDevices = {}
        try:
            _listOfDevices = json.load(handle)
        except json.decoder.JSONDecodeError as e:
            res = "Failed"
            Domoticz.Error("loadJsonDatabase poorly-formed %s, not JSON: %s" % (self.pluginConf["filename"], e))
    for key in _listOfDevices:
        CheckDeviceList(self, key, str(_listOfDevices[key]))
    return res


def _read_DeviceList_Domoticz(self):

    ListOfDevices_from_Domoticz = Modules.tools.getConfigItem(Key="ListOfDevices", Attribute="Devices")
    time_stamp = 0
    if "TimeStamp" in ListOfDevices_from_Domoticz:
        time_stamp = ListOfDevices_from_Domoticz["TimeStamp"]
        ListOfDevices_from_Domoticz = ListOfDevices_from_Domoticz["Devices"]
        self.log.logging(
            "Database",
            "Log",
            "Plugin data loaded where saved on %s"
            % (time.strftime("%A, %Y-%m-%d %H:%M:%S", time.localtime(time_stamp))),
        )

    self.log.logging(
        "Database", "Debug", "Load from Dz: %s %s" % (len(ListOfDevices_from_Domoticz), ListOfDevices_from_Domoticz)
    )
    if not isinstance(ListOfDevices_from_Domoticz, dict):
        ListOfDevices_from_Domoticz = {}
    else:
        for x in list(ListOfDevices_from_Domoticz):
            for attribute in list(ListOfDevices_from_Domoticz[x]):
                if attribute not in (MANDATORY_ATTRIBUTES + MANUFACTURER_ATTRIBUTES + BUILD_ATTRIBUTES):
                    self.log.logging("Database", "Log", "xxx Removing attribute: %s for %s" % (attribute, x))
                    del ListOfDevices_from_Domoticz[x][attribute]

    return (ListOfDevices_from_Domoticz, time_stamp)


def is_domoticz_recent(self, dz_timestamp, device_list_txt_filename):

    txt_timestamp = 0
    if os.path.isfile(device_list_txt_filename):
        txt_timestamp = os.path.getmtime(device_list_txt_filename)

    self.log.logging("Database", "Log", "%s timestamp is %s" % (device_list_txt_filename, txt_timestamp))
    if dz_timestamp > txt_timestamp:
        self.log.logging("Database", "Log", "Dz is more recent than Txt Dz: %s Txt: %s" % (dz_timestamp, txt_timestamp))
        return True
    return False


def WriteDeviceList(self, count):
    if self.HBcount < count:
        self.HBcount = self.HBcount + 1
        return

    if self.pluginconf.pluginConf["pluginData"] is None or self.DeviceListName is None:
        Domoticz.Error(
            "WriteDeviceList - self.pluginconf.pluginConf['pluginData']: %s , self.DeviceListName: %s"
            % (self.pluginconf.pluginConf["pluginData"], self.DeviceListName)
        )
        return

    if self.pluginconf.pluginConf["expJsonDatabase"]:
        _write_DeviceList_json(self)

    _write_DeviceList_txt(self)

    if Modules.tools.is_domoticz_db_available(self) and self.pluginconf.pluginConf["useDomoticzDatabase"]:
        # We need to patch None as 'None'
        if _write_DeviceList_Domoticz(self) is None:
            # An error occured. Probably Dz.Configuration() is not available.
            _write_DeviceList_txt(self)

    self.HBcount = 0


def _write_DeviceList_txt(self):
    # Write in classic format ( .txt )
    _DeviceListFileName = self.pluginconf.pluginConf["pluginData"] + self.DeviceListName
    try:
        self.log.logging("Database", "Debug", "Write " + _DeviceListFileName + " = " + str(self.ListOfDevices))
        with open(_DeviceListFileName, "wt") as file:
            for key in self.ListOfDevices:
                try:
                    file.write(key + " : " + str(self.ListOfDevices[key]) + "\n")
                except IOError:
                    Domoticz.Error("Error while writing to plugin Database %s" % _DeviceListFileName)
        self.log.logging("Database", "Debug", "WriteDeviceList - flush Plugin db to %s" % _DeviceListFileName)
    except IOError:
        Domoticz.Error("Error while Writing plugin Database %s" % _DeviceListFileName)


def _write_DeviceList_json(self):
    _DeviceListFileName = self.pluginconf.pluginConf["pluginData"] + self.DeviceListName[:-3] + "json"
    self.log.logging("Database", "Debug", "Write " + _DeviceListFileName + " = " + str(self.ListOfDevices))
    with open(_DeviceListFileName, "wt") as file:
        json.dump(self.ListOfDevices, file, sort_keys=True, indent=2)
    self.log.logging("Database", "Debug", "WriteDeviceList - flush Plugin db to %s" % _DeviceListFileName)


def _write_DeviceList_Domoticz(self):
    ListOfDevices_for_save = self.ListOfDevices.copy()
    self.log.logging("Database", "Log", "WriteDeviceList - flush Plugin db to %s" % "Domoticz")
    return Modules.tools.setConfigItem(
        Key="ListOfDevices", Attribute="Devices", Value={"TimeStamp": time.time(), "Devices": ListOfDevices_for_save}
    )


def importDeviceConf(self):
    # Import DeviceConf.txt
    tmpread = ""
    self.DeviceConf = {}

    if os.path.isfile(self.pluginconf.pluginConf["pluginConfig"] + "DeviceConf.txt"):
        with open(self.pluginconf.pluginConf["pluginConfig"] + "DeviceConf.txt", "r") as myfile:
            tmpread += myfile.read().replace("\n", "")
            try:
                self.DeviceConf = eval(tmpread)
            except (SyntaxError, NameError, TypeError, ZeroDivisionError):
                Domoticz.Error(
                    "Error while loading %s in line : %s"
                    % (self.pluginconf.pluginConf["pluginConfig"] + "DeviceConf.txt", tmpread)
                )
                return

    # Remove comments
    for iterDevType in list(self.DeviceConf):
        if iterDevType == "":
            del self.DeviceConf[iterDevType]

    # for iterDevType in list(self.DeviceConf):
    #    Domoticz.Log("%s - %s" %(iterDevType, self.DeviceConf[iterDevType]))

    self.log.logging("Database", "Status", "DeviceConf loaded - %s confs loaded" %len(self.DeviceConf))


def importDeviceConfV2(self):

    from os import listdir
    from os.path import isdir, isfile, join

    # Read DeviceConf for backward compatibility
    importDeviceConf(self)

    model_certified = self.pluginconf.pluginConf["pluginConfig"] + "Certified"

    if os.path.isdir(model_certified):
        model_brand_list = [f for f in listdir(model_certified) if isdir(join(model_certified, f))]

        for brand in model_brand_list:
            if brand in ("README.md", ".PRECIOUS"):
                continue

            model_directory = model_certified + "/" + brand

            model_list = [f for f in listdir(model_directory) if isfile(join(model_directory, f))]

            for model_device in model_list:
                if model_device in ("README.md", ".PRECIOUS"):
                    continue

                filename = str(model_directory + "/" + model_device)
                with open(filename, "rt") as handle:
                    try:
                        model_definition = json.load(handle)
                    except ValueError as e:
                        Domoticz.Error("--> JSON ConfFile: %s load failed with error: %s" % (str(filename), str(e)))
                        continue
                    except Exception as e:
                        Domoticz.Error("--> JSON ConfFile: %s load general error: %s" % (str(filename), str(e)))
                        continue

                try:
                    device_model_name = model_device.rsplit(".", 1)[0]

                    if device_model_name not in self.DeviceConf:
                        self.log.logging(
                            "Database", "Debug", "--> Config for %s/%s" % (str(brand), str(device_model_name))
                        )
                        self.DeviceConf[device_model_name] = dict(model_definition)
                    else:
                        self.log.logging(
                            "Database",
                            "Debug",
                            "--> Config for %s/%s not loaded as already defined" % (str(brand), str(device_model_name)),
                        )
                except:
                    Domoticz.Error("--> Unexpected error when loading a configuration file")

    self.log.logging("Database", "Debug", "--> Config loaded: %s" % self.DeviceConf.keys())
    self.log.logging("Database", "Status", "DeviceConf loaded - %s confs loaded" %len(self.DeviceConf))


def checkDevices2LOD(self, Devices):

    for nwkid in self.ListOfDevices:
        self.ListOfDevices[nwkid]["ConsistencyCheck"] = ""
        if self.ListOfDevices[nwkid]["Status"] == "inDB":
            for dev in Devices:
                if Devices[dev].DeviceID == self.ListOfDevices[nwkid]["IEEE"]:
                    self.ListOfDevices[nwkid]["ConsistencyCheck"] = "ok"
                    break
            else:
                self.ListOfDevices[nwkid]["ConsistencyCheck"] = "not in DZ"


def checkListOfDevice2Devices(self, Devices):

    # As of V3 we will be loading only the IEEE information as that is the only one existing in Domoticz area.
    # It is also expected that the ListOfDevices is already loaded.

    # At that stage the ListOfDevices has beene initialized.
    for x in Devices:  # initialise listeofdevices avec les devices en bases domoticz
        ID = Devices[x].DeviceID
        if len(str(ID)) == 4:
            # This is a Group Id (short address)
            continue
        elif ID.find("Zigate-01-") != -1 or ID.find("Zigate-02-") != -1 or ID.find("Zigate-03-") != -1:
            continue  # This is a Widget ID

        # Let's check if this is End Node
        if str(ID) not in self.IEEE2NWK:
            if self.pluginconf.pluginConf["allowForceCreationDomoDevice"] == 1:
                self.log.logging(
                    "Database",
                    "Log",
                    "checkListOfDevice2Devices - "
                    + str(Devices[x].Name)
                    + " - "
                    + str(ID)
                    + " not found in Plugin Database",
                )
            else:
                Domoticz.Error(
                    "checkListOfDevice2Devices - "
                    + str(Devices[x].Name)
                    + " - "
                    + str(ID)
                    + " not found in Plugin Database"
                )
                self.log.logging(
                    "Database",
                    "Debug",
                    "checkListOfDevice2Devices - " + str(ID) + " not found in " + str(self.IEEE2NWK),
                )
            continue
        NWKID = self.IEEE2NWK[ID]
        if str(NWKID) in self.ListOfDevices:
            self.log.logging(
                "Database",
                "Debug",
                "checkListOfDevice2Devices - we found a matching entry for ID %2s as DeviceID = %s NWK_ID = %s"
                % (x, ID, NWKID),
                NWKID,
            )
        else:
            Domoticz.Error(
                "loadListOfDevices -  : "
                + Devices[x].Name
                + " with IEEE = "
                + str(ID)
                + " not found in Zigate plugin Database!"
            )


def saveZigateNetworkData(self, nkwdata):

    json_filename = self.pluginconf.pluginConf["pluginData"] + "Zigate.json"
    self.log.logging("Database", "Debug", "Write " + json_filename + " = " + str(self.ListOfDevices))
    try:
        with open(json_filename, "wt") as json_file:
            json.dump(nkwdata, json_file, indent=4, sort_keys=True)
    except IOError:
        Domoticz.Error("Error while writing Zigate Network Details%s" % json_filename)


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
        self.ListOfDevices[key] = {}
        self.ListOfDevices[key]["Status"] = ""
    else:
        Modules.tools.initDeviceInList(self, key)

    self.ListOfDevices[key]["RIA"] = "10"

    # List of Attribnutes that will be Loaded from the deviceList-xx.txt database

    if self.pluginconf.pluginConf["resetPluginDS"]:
        self.log.logging("Database", "Status", "Reset Build Attributes for %s" % DeviceListVal["IEEE"])
        IMPORT_ATTRIBUTES = list(set(MANDATORY_ATTRIBUTES))

    elif key == "0000":
        # Reduce the number of Attributes loaded for Zigate
        self.log.logging(
            "Database", "Debug", "CheckDeviceList - Zigate (IEEE)  = %s Load Zigate Attributes" % DeviceListVal["IEEE"]
        )
        IMPORT_ATTRIBUTES = list(set(ZIGATE_ATTRIBUTES))
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
                Domoticz.Status(
                    "Model adjustement during import from %s to %s" % (OldModel, self.ListOfDevices[key][attribute])
                )

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
        Domoticz.Log(" Set: %s for device %s " % (self.DeviceConf[model]["ForceAckCommands"], x))
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
        Domoticz.Log("++++Issue #566: Fixing Cluster Revision for NwkId: %s" % key)
        del self.ListOfDevices[key]["Ep"]["Cluster Revision"]
        res = True

    for ep in self.ListOfDevices[key]["Ep"]:
        if "Cluster Revision" in self.ListOfDevices[key]["Ep"][ep]:
            Domoticz.Log("++++Issue #566 Cluster Revision NwkId: %s Ep: %s" % (key, ep))
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
        Domoticz.Log("++++Issue #566 ClusterType mixing NwkId: %s Ep 01 and 02" % key)
        self.ListOfDevices[key]["Ep"]["01"]["ClusterType"] = dict(self.ListOfDevices[key]["Ep"]["02"]["ClusterType"])
        self.ListOfDevices[key]["Ep"]["02"]["ClusterType"] = {}
        res = True
    return True


def fixing_iSQN_None(self, key):

    for DeviceAttribute in (
        "ConfigureReporting",
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
                Domoticz.Log("--->PluginConf %s <-- %s" % (param, plugin_generic_param))
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
                Domoticz.Log("--->PluginConf %s <-- %s" % (param, plugin_generic_param))
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
                Domoticz.Log("--->PluginConf %s <-- %s" % (param, plugin_generic_param))
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
