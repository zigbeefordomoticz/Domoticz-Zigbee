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

import Modules.tools
from Modules.database import write_coordinator_backup_domoticz, read_coordinator_backup_domoticz, is_domoticz_recent


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

    if self.pluginconf.pluginConf["storeDomoticzDatabase"]:
        write_coordinator_backup_domoticz(self, json.dumps((backup.as_dict())) )


def handle_zigpy_retreive_last_backup( self ):

    # Return the last backup
    _pluginData = Path( self.pluginconf.pluginConf["pluginData"] )
    _coordinator_backup = _pluginData / ("Coordinator-%02d.backup" %self.HardwareID)
    if not os.path.exists(_coordinator_backup):
        return None

    file_latest_coordinator_backup_record = None
    with open(_coordinator_backup, "r") as _coordinator:
        self.log.logging("TransportZigpy", "Debug", "Open : %s" % _coordinator_backup)
        try:
            file_latest_coordinator_backup_record = json.load(_coordinator)
        except json.JSONDecodeError:
            return None
        except Exception:
            return None

    if (self.pluginconf.pluginConf["useDomoticzDatabase"] or self.pluginconf.pluginConf["storeDomoticzDatabase"]):
        # Read the most recent coordinator backup from Domoticz Db
        latest_coordinator_backup = read_coordinator_backup_domoticz(self)
        self.log.logging("TransportZigpy", "Debug", "handle_zigpy_retreive_last_backup - Retreive latest_coordinator_backup %s (%s)" %(
            str(latest_coordinator_backup), type(latest_coordinator_backup)))

        dz_latest_coordinator_backup_record, dz_latest_coordinator_backup_timestamp = latest_coordinator_backup
        if dz_latest_coordinator_backup_record is None:
            return None

        if isinstance(dz_latest_coordinator_backup_record, str):
            dz_latest_coordinator_backup_record = json.loads(dz_latest_coordinator_backup_record)

        self.log.logging("TransportZigpy", "Debug", "handle_zigpy_retreive_last_backup - Retreive latest Coordinator data from Domoticz : (%s) %s" %(
            type(dz_latest_coordinator_backup_record),dz_latest_coordinator_backup_record))

        self.log.logging( "Database", "Debug", "Coordinator Backup from Dz is recent: %s " % (
            is_domoticz_recent(self, dz_latest_coordinator_backup_timestamp, _coordinator_backup) ))

        self.log.logging("TransportZigpy", "Log", "Domoticz Coordinator Backup versus File Backup equal : %s" % (
            file_latest_coordinator_backup_record == dz_latest_coordinator_backup_record))

    return file_latest_coordinator_backup_record
