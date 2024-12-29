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
from Modules.database import (is_timestamp_recent_than_filename,
                              read_coordinator_backup_domoticz,
                              write_coordinator_backup_domoticz)


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
        self.log.logging("Database", "Status", f"+ Saving Coordinator database into {_coordinator_backup}")
        with open(_coordinator_backup, "wt") as file:
            file.write(json.dumps((backup.as_dict())))
            self.log.logging("TransportZigpy", "Debug", "Coordinator backup is available: %s" %_coordinator_backup)

    except IOError:
        self.log.logging("TransportZigpy", "Error", "Error while Writing Coordinator backup %s" % _coordinator_backup)

    if self.pluginconf.pluginConf["useDomoticzDatabase"] or self.pluginconf.pluginConf["storeDomoticzDatabase"]:
        write_coordinator_backup_domoticz(self, json.dumps((backup.as_dict())) )


def handle_zigpy_retreive_last_backup( self ):
    """ Return the last coordinator backup from txt or domoticz"""

    _pluginData = Path( self.pluginconf.pluginConf["pluginData"] )
    _coordinator_backup = _pluginData / ("Coordinator-%02d.backup" %self.HardwareID)

    file_latest_coordinator_backup_record = None

    # Retreive the coordinator backup from Text file
    if os.path.exists(_coordinator_backup):
        with open(_coordinator_backup, "r") as _coordinator:
            self.log.logging("TransportZigpy", "Debug", "Open : %s" % _coordinator_backup)
            loaded_from = _coordinator_backup
            try:
                file_latest_coordinator_backup_record = json.load(_coordinator)
            except (json.JSONDecodeError, Exception):
                file_latest_coordinator_backup_record = None

    # Retreive the coordinator backup from Domoticz Configuration record
    if (self.pluginconf.pluginConf["useDomoticzDatabase"] or self.pluginconf.pluginConf["storeDomoticzDatabase"]):
        latest_coordinator_backup = read_coordinator_backup_domoticz(self)
        self.log.logging("TransportZigpy", "Debug", "handle_zigpy_retreive_last_backup - Retreive latest_coordinator_backup %s (%s)" %(
            str(latest_coordinator_backup), type(latest_coordinator_backup)))

        dz_latest_coordinator_backup_record, dz_latest_coordinator_backup_timestamp = latest_coordinator_backup
        backup_domoticz_more_recent = is_timestamp_recent_than_filename(self, dz_latest_coordinator_backup_timestamp, _coordinator_backup ) if os.path.exists(_coordinator_backup) else True

        if isinstance(dz_latest_coordinator_backup_record, str):
            dz_latest_coordinator_backup_record = json.loads(dz_latest_coordinator_backup_record)

        self.log.logging("TransportZigpy", "Debug", "handle_zigpy_retreive_last_backup - Retreive latest Coordinator data from Domoticz : (%s) %s" %(
            type(dz_latest_coordinator_backup_record),dz_latest_coordinator_backup_record))

        self.log.logging( "Database", "Debug", "Coordinator Backup from Domoticz is recent: %s " % (
            is_timestamp_recent_than_filename(self, dz_latest_coordinator_backup_timestamp, _coordinator_backup) ))

        if file_latest_coordinator_backup_record != dz_latest_coordinator_backup_record:
            self.log.logging("TransportZigpy", "Error", f"==> Sanity check : Domoticz Coordinator Backup versus File Backup NOT equal!! Domoticz: {dz_latest_coordinator_backup_record}  {_coordinator_backup}: {file_latest_coordinator_backup_record}")

        # At that stage, we have loaded from Domoticz and from txt file.
        if dz_latest_coordinator_backup_record and self.pluginconf.pluginConf["useDomoticzDatabase"] and backup_domoticz_more_recent:
            # We will use the Domoticz import.
            self.log.logging("Database", "Status", "Z4D loads coordinator backup from Domoticz")
            return dz_latest_coordinator_backup_record

    self.log.logging("Database", "Status", f"Z4D loads coordinator backup from {_coordinator_backup}")
    return file_latest_coordinator_backup_record
