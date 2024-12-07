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

from Classes.WebServer.headerResponse import (prepResponseMessage,
                                              setupHeadersResponse)

REST_COMMANDS = {}


def setup_list_rest_commands( self ):
    
    list_rest_commands = [
        ( {"Name": "battery-state", "Verbs": {"GET"}, "function": self.rest_battery_state} ),
        ( {"Name": "bind-lst-cluster", "Verbs": {"GET"}, "function": self.rest_bindLSTcluster} ),
        ( {"Name": "bind-lst-device", "Verbs": {"GET"}, "function": self.rest_bindLSTdevice} ),
        ( {"Name": "binding", "Verbs": {"PUT"}, "function": self.rest_binding} ),
        ( {"Name": "binding-table-req", "Verbs": {"GET"}, "function": self.rest_binding_table_req} ),
        ( {"Name": "binding-table-disp", "Verbs": {"GET"}, "function": self.rest_binding_table_disp} ),
        ( {"Name": "binding-group", "Verbs": {"PUT"}, "function": self.rest_group_binding} ),
        ( {"Name": "casaia-list-devices", "Verbs": {"GET"}, "function": self.rest_casa_device_list } ),
        ( {"Name": "casaia-update-ircode", "Verbs": {"PUT"}, "function": self.rest_casa_device_ircode_update } ),
        ( {"Name": "cfgrpt-ondemand", "Verbs": {"GET"}, "function": self.rest_cfgrpt_ondemand} ),
        ( {"Name": "cfgrpt-ondemand-config", "Verbs": { "GET", "PUT", "DELETE" }, "function": self.rest_cfgrpt_ondemand_with_config} ),
        ( {"Name": "change-channel", "Verbs": {"PUT"}, "function": self.rest_change_channel} ),
        ( {"Name": "change-model", "Verbs": {"PUT"}, "function": self.rest_change_model_name} ),
        ( {"Name": "clear-error-history", "Verbs": {"GET"}, "function": self.rest_logErrorHistoryClear } ),
        ( {"Name": "dev-cap", "Verbs": {"GET"}, "function": self.rest_dev_capabilities} ),
        ( {"Name": "dev-command", "Verbs": {"PUT"}, "function": self.rest_dev_command} ),
        ( {"Name": "device", "Verbs": {"GET"}, "function": self.rest_Device} ),
        ( {"Name": "device-settings-help", "Verbs": {"GET"}, "function": self.rest_device_settings_help} ),
        ( {"Name": "domoticz-env", "Verbs": {"GET"}, "function": self.rest_domoticz_env} ),
        ( {"Name": "help", "Verbs": {"GET"}, "function": None} ),
        ( {"Name": "full-reprovisionning", "Verbs": {"PUT"}, "function": self.rest_full_reprovisionning} ),
        ( {"Name": "log-error-history", "Verbs": {"GET"}, "function": self.rest_logErrorHistory} ),
        ( {"Name": "new-hrdwr", "Verbs": {"GET"}, "function": self.rest_new_hrdwr} ),
        ( {"Name": "nwk-stat", "Verbs": {"GET", "DELETE"}, "function": self.rest_nwk_stat} ),
        ( {"Name": "non-optmize-device-configuration", "Verbs": {"GET"}, "function": self.non_optmize_device_configuration} ),
        ( {"Name": "ota-firmware-available", "Verbs": {"GET"}, "function": self.rest_ota_firmware_available } ),
        ( {"Name": "ota-firmware-device-list", "Verbs": {"GET"}, "function": self.rest_ota_devices_for_manufcode } ),
        ( {"Name": "ota-firmware-list", "Verbs": {"GET"}, "function": self.rest_ota_firmware_list} ),
        ( {"Name": "ota-firmware-update", "Verbs": {"PUT"}, "function": self.rest_ota_firmware_update } ),
        ( {"Name": "permit-to-join", "Verbs": {"GET", "PUT"}, "function": self.rest_PermitToJoin} ),
        ( {"Name": "plugin-ping", "Verbs": {"GET"}, "function": self.rest_plugin_ping} ),
        ( {"Name": "plugin-health", "Verbs": {"GET"}, "function": self.rest_plugin_health} ),
        ( {"Name": "plugin-log", "Verbs": {"GET"}, "function": self.rest_logPlugin} ),
        ( {"Name": "plugin-upgrade", "Verbs": {"GET"}, "function": self.rest_plugin_upgrade} ),
        ( {"Name": "plugin-restart", "Verbs": {"GET"}, "function": self.rest_plugin_restart} ),
        ( {"Name": "plugin-stat", "Verbs": {"GET"}, "function": self.rest_plugin_stat} ),
        ( {"Name": "plugin", "Verbs": {"GET"}, "function": self.rest_PluginEnv} ),
        ( {"Name": "raw-command", "Verbs": {"PUT"}, "function": self.rest_raw_command} ),
        ( {"Name": "raw-zigbee", "Verbs": {"PUT"}, "function": self.rest_raw_zigbee} ),
        ( {"Name": "rcv-nw-hrdwr", "Verbs": {"GET"}, "function": self.rest_rcv_nw_hrdwr} ),
        ( {"Name": "recreate-widgets", "Verbs": {"PUT"}, "function": self.rest_recreate_widgets} ),
        ( {"Name": "reload-device-conf", "Verbs": {"GET"}, "function": self.rest_reload_device_conf} ),
        ( {"Name": "req-nwk-full", "Verbs": {"GET"}, "function": self.rest_req_nwk_full} ),
        ( {"Name": "req-nwk-inter", "Verbs": {"GET"}, "function": self.rest_req_nwk_inter} ),
        ( {"Name": "req-topologie", "Verbs": {"GET"}, "function": self.rest_req_topologie} ),
        ( {"Name": "rescan-groups", "Verbs": {"GET"}, "function": self.rest_rescan_group} ),
        ( {"Name": "restart-needed", "Verbs": {"GET"}, "function": self.rest_restart_needed} ),
        ( {"Name": "scan-device-for-grp", "Verbs": {"PUT"}, "function": self.rest_scan_devices_for_group } ),
        ( {"Name": "setting-debug", "Verbs": {"GET", "PUT"}, "function": self.rest_Settings_with_debug} ),
        ( {"Name": "setting", "Verbs": {"GET", "PUT"}, "function": self.rest_Settings_wo_debug} ),
        ( {"Name": "sw-reset-zigate", "Verbs": {"GET"}, "function": self.rest_reset_zigate} ),
        ( {"Name": "sw-reset-coordinator", "Verbs": {"GET"}, "function": self.rest_reset_zigate} ),
        ( {"Name": "topologie", "Verbs": {"GET", "DELETE"}, "function": self.rest_netTopologie} ),
        ( {"Name": "unbinding", "Verbs": {"PUT"}, "function": self.rest_unbinding} ),
        ( {"Name": "unbinding-group", "Verbs": {"PUT"}, "function": self.rest_group_unbinding} ),
        ( {"Name": "upgrade-certified-devices", "Verbs": {"GET"}, "function": self.rest_certified_devices_update} ),
        ( {"Name": "zdevice-name", "Verbs": {"GET", "PUT", "DELETE"}, "function": self.rest_zDevice_name} ),
        ( {"Name": "zdevice-raw", "Verbs": {"GET", "PUT"}, "function": self.rest_zDevice_raw} ),
        ( {"Name": "zdevice", "Verbs": {"GET", "DELETE"}, "function": self.rest_zDevice} ),
        ( {"Name": "zgroup-list-available-device", "Verbs": {"GET"}, "function": self.rest_zGroup_lst_avlble_dev } ),
        ( {"Name": "zgroup", "Verbs": {"GET", "PUT"}, "function": self.rest_zGroup} ),
        ( {"Name": "zigate-erase-PDM", "Verbs": {"GET"}, "function": self.rest_zigate_erase_PDM} ),
        ( {"Name": "zigate-mode", "Verbs": {"GET"}, "function": self.rest_zigate_mode} ),
        ( {"Name": "zigate", "Verbs": {"GET"}, "function": self.rest_zigate } ),
        ( {"Name": "zlinky", "Verbs": {"GET"}, "function": self.rest_zlinky } ),
        ( {"Name": "coordinator-erase-PDM", "Verbs": {"GET"}, "function": self.rest_zigate_erase_PDM} ),
        ( {"Name": "coordinator-mode", "Verbs": {"GET"}, "function": self.rest_zigate_mode} ),
        ( {"Name": "coordinator", "Verbs": {"GET"}, "function": self.rest_zigate} ), 
    ]
        
    for command in list_rest_commands:
        _name = command["Name"]
        _verbs = command["Verbs"]
        _function = command["function"]
        if _name in REST_COMMANDS:
            self.logging("Error", "setup_list_rest_commands - %s already loaded" %_name)
        REST_COMMANDS[ _name ] = { "Name": _name, "Verbs": _verbs, "function": _function}

def do_rest(self, Connection, verb, data, version, command, parameters):
    
    self.logging("Debug", "do_rest - Verb: %s, Command: %s, Param: %s" % (verb, command, parameters))

    HTTPresponse = {}

    if command in REST_COMMANDS and verb in REST_COMMANDS[command]["Verbs"]:
        self.logging("Debug", "do_rest - Verb: %s, Command: %s, Param: %s found ready to execute" % (verb, command, parameters))
        HTTPresponse = execute_rest_command(self, verb, data, version, command, parameters)

    else:
        self.logging("Error", "do_rest - Verb: %s, Command: %s, Param: %s not found !" % (verb, command, parameters))

    self.logging("Debug", "==> return HTTPresponse: %s" % (HTTPresponse))
    if HTTPresponse == {} or HTTPresponse is None:
        # We reach here due to failure !
        HTTPresponse = prepare_error_message(self, command)

    self.logging("Debug", "==> sending HTTPresponse: %s to %s" % (HTTPresponse, Connection))
    self.sendResponse(Connection, HTTPresponse)


def execute_rest_command(self, verb, data, version, command, parameters):
    response = setupHeadersResponse()
    if self.pluginconf.pluginConf["enableKeepalive"]:
        response["Headers"]["Connection"] = "Keep-alive"
    else:
        response["Headers"]["Connection"] = "Close"
    response["Headers"]["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Headers"]["Pragma"] = "no-cache"
    response["Headers"]["Expires"] = "0"
    response["Headers"]["Accept"] = "*/*"
    
    if command == "help":
        response = prepare_help_response(self)

    elif version == "1" and REST_COMMANDS[command]["function"]:
        self.logging("Debug", "do_rest - calling REST_COMMANDS[%s]['function'] with %s %s %s" % (command, verb, data, parameters))
        response = REST_COMMANDS[command]["function"](verb, data, parameters)

    elif version == "2" and REST_COMMANDS[command]["functionv2"]:
        response = REST_COMMANDS[command]["functionv2"](verb, data, parameters)

    return response


def prepare_help_response(self):
    response = prepResponseMessage(self, setupHeadersResponse())
    _data = {}
    for x in REST_COMMANDS:
        _data[x] = {"Verbs": []}
        for y in REST_COMMANDS[x]["Verbs"]:
            _data[x]["Verbs"].append(y)
    response["Data"] = json.dumps(_data)
    return response

    
def prepare_error_message(self, command):
    response = prepResponseMessage(self, setupHeadersResponse())
    response["Status"] = "400 BAD REQUEST"
    response["Data"] = "Unknown REST command: %s" % command
    response["Headers"]["Content-Type"] = "text/plain; charset=utf-8"
    return response


def do_nothing(self, verb, data, parameters):
    pass
