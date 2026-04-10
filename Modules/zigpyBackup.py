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

import json
import os.path
from pathlib import Path
import time

import Modules.tools
from Modules.domoticzAbstractLayer import getConfigItem, setConfigItem

def handle_zigpy_backup(self, backup):

    if not backup:
        self.log.logging("TransportZigpy", "Log","Backup is incomplete, it is not possible to restore")
        return

    _pluginData = Path( self.pluginconf.pluginConf["pluginData"] )
    _coordinator_backup = _pluginData / ("Coordinator-%02d.backup" %self.HardwareID )
    self.log.logging("TransportZigpy", "Debug", "Backups: %s" %backup)

    if os.path.exists(_coordinator_backup):
        Modules.tools.helper_versionFile(_coordinator_backup, self.pluginconf.pluginConf["numDeviceListVersion"])

    try:
        with open(_coordinator_backup, "wt") as file:
            file.write(json.dumps((backup.as_dict())))
            self.log.logging("TransportZigpy", "Status", "Coordinator backup is available: %s" %_coordinator_backup)

    except IOError:
        self.log.logging("TransportZigpy", "Error", "Error while Writing Coordinator backup %s" % _coordinator_backup)

    use_domoticz_db = self.pluginconf.pluginConf.get("useDomoticzDb")
    store_in_domoticz_db = self.pluginconf.pluginConf.get("storeDomoticzDb")
    if use_domoticz_db or store_in_domoticz_db:
        domoticz_backup(self, json.dumps((backup.as_dict())))
        self.log.logging("TransportZigpy", "Status", "Coordinator backup store in Domoticz")
        

def domoticz_backup(self, coordinator_backup):
    self.log.logging("Database", "Log", "Coordinator backup flushed on Domoticz records")
    return setConfigItem( Key="Coordinator", Attribute="b64-coordinator", Value={"TimeStamp": time.time(), "b64-coordinator": coordinator_backup} )


def domoticz_retrieve_last_backup( self ):
    self.log.logging("Database", "Log", "Retrieve last Coordinator backup from Domoticz records")
    record = getConfigItem( Key="Coordinator", Attribute="b64-coordinator" )
    if not record:
        return 0, None
    try:
        return record.get("TimeStamp"), json.loads(record.get("b64-coordinator"))
    except json.JSONDecodeError:
        return 0, None
    except Exception:
        return 0, None
    return 0, None


def handle_zigpy_retreive_last_backup( self ):
    
    # Return the last backup
    use_domoticz_db = self.pluginconf.pluginConf.get("useDomoticzDb")
    store_in_domoticz_db = self.pluginconf.pluginConf.get("storeDomoticzDb")
    dz_timestamp = 0
    txt_timestamp = 0
    last_domoticz_backup = None
    if use_domoticz_db or store_in_domoticz_db:
        dz_timestamp, last_domoticz_backup = domoticz_retrieve_last_backup(self)

    plugin_data_pathname = Path( self.pluginconf.pluginConf["pluginData"] )
    coordinator_filename = plugin_data_pathname / ("Coordinator-%02d.backup" %self.HardwareID)
    if not os.path.exists(coordinator_filename):
        return last_domoticz_backup

    if os.path.isfile(coordinator_filename):
        txt_timestamp = os.path.getmtime(coordinator_filename)

    if dz_timestamp > txt_timestamp:
        self.log.logging("Database", "Log", "Dz is more recent than Txt Dz: %s Txt: %s" % (dz_timestamp, txt_timestamp))
        return last_domoticz_backup

    with open(coordinator_filename, "r") as _coordinator:
        self.log.logging("TransportZigpy", "Debug", "Open : %s" % coordinator_filename)
        try:
            return json.load(_coordinator)

        except json.JSONDecodeError:
            return None
        except Exception:
            return None
    return None