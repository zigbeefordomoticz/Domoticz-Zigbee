#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import json
import mimetypes
import os
import os.path
from time import time

import Domoticz
from Classes.DomoticzDB import DomoticzDB_Preferences
from Classes.LoggingManagement import LoggingManagement
from Classes.PluginConf import SETTINGS
from Classes.WebServer.headerResponse import prepResponseMessage, setupHeadersResponse
from Modules.actuators import actuators
from Modules.basicOutputs import ZigatePermitToJoin, initiate_change_channel, setExtendedPANID, start_Zigate, zigateBlueLed , PermitToJoin
from Modules.enki import enki_set_poweron_after_offon
from Modules.philips import philips_set_poweron_after_offon
from Modules.tools import is_hex
from Modules.txPower import set_TxPower
from Modules.zigateConsts import CERTIFICATION_CODE, ZCL_CLUSTERS_LIST, ZIGATE_COMMANDS
from Modules.sendZigateCommand import (raw_APS_request, send_zigatecmd_raw,
                                       send_zigatecmd_zcl_ack,sendZigateCmd,
                                       send_zigatecmd_zcl_noack)
from Modules.zigateCommands import zigate_set_mode

MIMETYPES = {
    "gif": "image/gif",
    "htm": "text/html",
    "html": "text/html",
    "jpg": "image/jpeg",
    "png": "image/png",
    "css": "text/css",
    "xml": "application/xml",
    "js": "application/javascript",
    "json": "application/json",
    "swf": "application/x-shockwave-flash",
    "manifest": "text/cache-manifest",
    "appcache": "text/cache-manifest",
    "xls": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "m3u": "audio/mpegurl",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
    "php": "text/html",
    "wav": "audio/x-wav",
    "svg": "image/svg+xml",
    "db": "application/octet-stream",
    "otf": "application/x-font-otf",
    "ttf": "application/x-font-ttf",
    "woff": "application/x-font-woff",
}


class WebServer(object):

    from Classes.WebServer.com import onConnect, onDisconnect, onStop, startWebServer
    from Classes.WebServer.dispatcher import do_rest
    from Classes.WebServer.onMessage import onMessage
    from Classes.WebServer.rest_Bindings import rest_binding, rest_binding_table_disp, rest_binding_table_req, rest_bindLSTcluster, rest_bindLSTdevice, rest_group_binding, rest_group_unbinding, rest_unbinding
    from Classes.WebServer.rest_Casaia import rest_casa_device_ircode_update, rest_casa_device_list
    from Classes.WebServer.rest_Energy import rest_req_nwk_full, rest_req_nwk_inter
    from Classes.WebServer.rest_Groups import rest_rescan_group, rest_scan_devices_for_group, rest_zGroup, rest_zGroup_lst_avlble_dev
    from Classes.WebServer.rest_Ota import rest_ota_devices_for_manufcode, rest_ota_firmware_list, rest_ota_firmware_update
    from Classes.WebServer.rest_Provisioning import rest_full_reprovisionning, rest_new_hrdwr, rest_rcv_nw_hrdwr
    from Classes.WebServer.rest_recreateWidget import rest_recreate_widgets
    from Classes.WebServer.rest_Topology import rest_netTopologie, rest_req_topologie
    from Classes.WebServer.sendresponse import sendResponse
    from Classes.WebServer.tools import DumpHTTPResponseToLog, keepConnectionAlive

    hearbeats = 0

    def __init__(
        self,
        zigbee_communitation,
        ZigateData,
        PluginParameters,
        PluginConf,
        Statistics,
        adminWidgets,
        ZigateComm,
        HomeDirectory,
        hardwareID,
        Devices,
        ListOfDevices,
        IEEE2NWK,
        DeviceConf,
        permitTojoin,
        WebUserName,
        WebPassword,
        PluginHealth,
        httpPort,
        log,
    ):
        self.zigbee_communitation = zigbee_communitation
        self.httpServerConn = None
        self.httpClientConn = None
        self.httpServerConns = {}
        self.httpPort = httpPort
        self.log = log

        self.httpsServerConn = None
        self.httpsClientConn = None
        self.httpsServerConns = {}
        self.httpsPort = None

        self.PluginHealth = PluginHealth
        self.WebUsername = WebUserName
        self.WebPassword = WebPassword
        self.pluginconf = PluginConf
        self.ControllerData = ZigateData
        self.adminWidget = adminWidgets
        self.ControllerLink = ZigateComm
        self.statistics = Statistics
        self.pluginParameters = PluginParameters
        self.networkmap = None
        self.networkenergy = None

        self.permitTojoin = permitTojoin

        self.groupmgt = None
        self.OTA = None
        self.ListOfDevices = ListOfDevices
        self.DevicesInPairingMode = []
        self.fakeDevicesInPairingMode = 0
        self.IEEE2NWK = IEEE2NWK
        self.DeviceConf = DeviceConf
        self.Devices = Devices

        self.ControllerIEEE = None

        self.restart_needed = {"RestartNeeded": 0}
        self.homedirectory = HomeDirectory
        self.hardwareID = hardwareID
        mimetypes.init()

        self.FirmwareVersion = None
        # Start the WebServer
        self.startWebServer()

    def update_firmware(self, firmwareversion):
        self.FirmwareVersion = firmwareversion

    def update_networkenergy(self, networkenergy):
        self.networkenergy = networkenergy

    def update_networkmap(self, networkmap):
        self.networkmap = networkmap

    def add_element_to_devices_in_pairing_mode( self, nwkid):
        if nwkid not in self.DevicesInPairingMode:
            self.DevicesInPairingMode.append( nwkid )
        
    def update_groupManagement(self, groupmanagement):
        self.groupmgt = groupmanagement if groupmanagement else None

    def update_OTA(self, OTA):
        self.OTA = OTA if OTA else None

    def setZigateIEEE(self, ZigateIEEE):

        self.ControllerIEEE = ZigateIEEE

    def rest_plugin_health(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == "GET":
            health = {
                "HealthFlag": self.PluginHealth["Flag"],
                "HealthTxt": self.PluginHealth["Txt"],
            }

            if "Firmware Update" in self.PluginHealth:
                health["OTAupdateProgress"] = self.PluginHealth["Firmware Update"]["Progress"]
                health["OTAupdateDevice"] = self.PluginHealth["Firmware Update"]["Device"]

            if self.groupmgt:
                health["GroupStatus"] = self.groupmgt.GroupStatus

            _response["Data"] = json.dumps(health, sort_keys=True)

        return _response

    def rest_zigate_erase_PDM(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == "GET":
            self.logging("Status", "Erase ZiGate PDM")
            Domoticz.Error("Erase ZiGate PDM non implémenté pour l'instant")
            if self.pluginconf.pluginConf["eraseZigatePDM"]:
                if self.pluginParameters["Mode2"] != "None" and self.zigbee_communitation == "native":
                    sendZigateCmd(self, "0012", "")
                self.pluginconf.pluginConf["eraseZigatePDM"] = 0

            if self.pluginconf.pluginConf["extendedPANID"] is not None:
                self.logging("Status", "ZigateConf - Setting extPANID : 0x%016x" % (self.pluginconf.pluginConf["extendedPANID"]))
                if self.pluginParameters["Mode2"] != "None":
                    setExtendedPANID(self, self.pluginconf.pluginConf["extendedPANID"])
            action = {"Description": "Erase ZiGate PDM - Non Implemente"}
            # if self.pluginParameters['Mode2'] != 'None':
            #    start_Zigate( self )
        return _response

    def rest_reset_zigate(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == "GET":
            if self.pluginParameters["Mode2"] != "None" and self.zigbee_communitation == "native":
                self.ControllerData["startZigateNeeded"] = True
                # start_Zigate( self )
                sendZigateCmd(self, "0002", "00")  # Force Zigate to Normal mode
                sendZigateCmd(self, "0011", "")  # Software Reset
            action = {"Name": "Software reboot of ZiGate", "TimeStamp": int(time())}
        _response["Data"] = json.dumps(action, sort_keys=True)
        return _response

    def rest_zigate(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == "GET":
            
            if self.ControllerData:
                coordinator_infos = {}
                coordinator_infos["Firmware Version"] = self.ControllerData["Firmware Version"]
                coordinator_infos["IEEE"] = self.ControllerData["IEEE"]
                coordinator_infos["Short Address"] = self.ControllerData["Short Address"]
                coordinator_infos["Channel"] = self.ControllerData["Channel"]
                coordinator_infos["PANID"] = self.ControllerData["PANID"]
                coordinator_infos["Extended PANID"] = self.ControllerData["Extended PANID"]
                coordinator_infos["Branch Version"] = self.ControllerData["Branch Version"]
                coordinator_infos["Major Version"] = self.ControllerData["Major Version"] 
                coordinator_infos["Minor Version"] = self.ControllerData["Minor Version"] 

                if 0 < int(self.ControllerData["Branch Version"]) <= 20:   
                    coordinator_infos["Display Firmware Version"] = "Zig - %s" % self.ControllerData["Minor Version"] 
                elif 20 <= int(self.ControllerData["Branch Version"]) < 30:
                    # ZNP
                    coordinator_infos["Display Firmware Version"] = "Znp - %s" % self.ControllerData["Minor Version"] 

                elif 30 <= int(self.ControllerData["Branch Version"]) < 40:   
                    # Silicon Labs
                    coordinator_infos["Display Firmware Version"] = "Ezsp - %s.%s" %(
                        self.ControllerData["Major Version"] , self.ControllerData["Minor Version"] )
                else:
                    coordinator_infos["Display Firmware Version"] = "UNK - %s" % self.ControllerData["Minor Version"] 
                _response["Data"] = json.dumps(coordinator_infos, sort_keys=True)
            else:
                fake_zigate = {
                    "Firmware Version": "fake - 0310",
                    "IEEE": "00158d0001ededde",
                    "Short Address": "0000",
                    "Channel": "0b",
                    "PANID": "51cf",
                    "Extended PANID": "bd1247ec9d358634",
                }

                _response["Data"] = json.dumps(fake_zigate, sort_keys=True)
        return _response

    def rest_domoticz_env(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == "GET":

            dzenv = {}
            # dzenv['proto'] = self.pluginconf.pluginConf['proto']
            # dzenv['host'] = self.pluginconf.pluginConf['host']
            dzenv["port"] = self.pluginconf.pluginConf["port"]

            dzenv["WebUserName"] = self.WebUsername
            dzenv["WebPassword"] = self.WebPassword

            _response["Data"] = json.dumps(dzenv, sort_keys=True)
        return _response

    def rest_PluginEnv(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == "GET":
            _response["Data"] = json.dumps(self.pluginParameters, sort_keys=True)
        return _response

    def rest_nwk_stat(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        _filename = self.pluginconf.pluginConf["pluginReports"] + "NetworkEnergy-v3-" + "%02d" % self.hardwareID + ".json"

        _timestamps_lst = []  # Just the list of Timestamps
        _scan = {}
        if os.path.isfile(_filename):
            self.logging("Debug", "Opening file: %s" % _filename)
            with open(_filename, "rt") as handle:
                for line in handle:
                    if line[0] != "{" and line[-1] != "}":
                        continue

                    entry = json.loads(line)
                    for _ts in entry:
                        _timestamps_lst.append(_ts)
                        _scan[_ts] = entry[_ts]

        if verb == "DELETE":
            if len(parameters) == 0:
                # os.remove( _filename )
                action = {"Name": "File-Removed", "FileName": _filename}
                _response["Data"] = json.dumps(action, sort_keys=True)

            elif len(parameters) == 1:
                timestamp = parameters[0]
                if timestamp in _timestamps_lst:
                    self.logging("Debug", "Removing Report: %s from %s records" % (timestamp, len(_timestamps_lst)))
                    with open(_filename, "r+") as handle:
                        d = handle.readlines()
                        handle.seek(0)
                        for line in d:
                            if not (line[0] == "{" or line[-1] == "}"):
                                handle.write(line)
                                continue

                            entry = json.loads(line)
                            entry_ts = entry.keys()
                            if len(entry_ts) == 1:
                                if timestamp in entry_ts:
                                    self.logging("Debug", "--------> Skiping %s" % timestamp)
                                    continue

                            else:
                                continue
                            handle.write(line)
                        handle.truncate()

                    action = {"Name": "Report %s removed" % timestamp}
                    _response["Data"] = json.dumps(action, sort_keys=True)
                else:
                    Domoticz.Error("Removing Nwk-Energy %s not found" % timestamp)
                    _response["Data"] = json.dumps([], sort_keys=True)

        elif verb == "GET":
            if len(parameters) == 0:
                _response["Data"] = json.dumps(_timestamps_lst, sort_keys=True)

            elif len(parameters) == 1:
                timestamp = parameters[0]
                if timestamp in _scan:
                    for r in _scan[timestamp]:
                        self.logging("Debug", "report: %s" % r)
                        if r["_NwkId"] == "0000":
                            _response["Data"] = json.dumps(r["MeshRouters"], sort_keys=True)
                else:
                    _response["Data"] = json.dumps([], sort_keys=True)

        return _response

    def rest_plugin_restart(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == "GET":
            from Modules.restartPlugin import restartPluginViaDomoticzJsonApi

            restartPluginViaDomoticzJsonApi(self)

            info = {"Text": "Plugin restarted", "TimeStamp": int(time())}
            _response["Data"] = json.dumps(info, sort_keys=True)
        return _response

    def rest_restart_needed(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == "GET":
            _response["Data"] = json.dumps(self.restart_needed, sort_keys=True)
        return _response

    def rest_plugin_stat(self, verb, data, parameters):

        Statistics = {}
        self.logging("Debug", "self.statistics: %s" % self.statistics)
        self.logging("Debug", " --> Type: %s" % type(self.statistics))

        Statistics["Trend"] = []
        if self.pluginParameters["Mode2"] == "None":
            Statistics["CRC"] = 1
            Statistics["FrameErrors"] = 1
            Statistics["Sent"] = 5
            Statistics["Received"] = 10
            Statistics["Cluster"] = 268
            Statistics["ReTx"] = 3
            Statistics["CurrentLoad"] = 1
            Statistics["MaxLoad"] = 7
            Statistics["APSAck"] = 100
            Statistics["APSNck"] = 0
            Statistics["StartTime"] = int(time()) - 120
        else:
            Statistics["PDMLoads"] = self.statistics._pdmLoads
            Statistics["MaxZiGateRoundTime8000 "] = self.statistics._maxTiming8000
            Statistics["AvgZiGateRoundTime8000 "] = self.statistics._averageTiming8000
            Statistics["MaxZiGateRoundTime8011 "] = self.statistics._maxTiming8011
            Statistics["AvgZiGateRoundTime8011 "] = self.statistics._averageTiming8011
            Statistics["MaxZiGateRoundTime8012 "] = self.statistics._maxTiming8012
            Statistics["AvgZiGateRoundTime8012 "] = self.statistics._averageTiming8012
            Statistics["MaxTimeSpentInProcFrame"] = self.statistics._max_reading_thread_timing
            Statistics["AvgTimeSpentInProcFrame"] = self.statistics._average_reading_thread_timing
            Statistics["MaxTimeSendingZigpy"] = self.statistics._max_reading_zigpy_timing
            Statistics["AvgTimeSendingZigpy"] = self.statistics._average_reading_zigpy_timing

            Statistics["MaxTimeSpentInForwarder"] = self.statistics._maxRxProcesses
            Statistics["AvgTimeSpentInForwarder"] = self.statistics._averageRxProcess

            Statistics["CRC"] = self.statistics._crcErrors
            Statistics["FrameErrors"] = self.statistics._frameErrors
            Statistics["Sent"] = self.statistics._sent
            Statistics["Received"] = self.statistics._received
            Statistics["Cluster"] = self.statistics._clusterOK
            Statistics["ReTx"] = self.statistics._reTx
            Statistics["APSFailure"] = self.statistics._APSFailure
            Statistics["APSAck"] = self.statistics._APSAck
            Statistics["APSNck"] = self.statistics._APSNck
            Statistics["CurrentLoad"] = self.ControllerLink.loadTransmit()
            Statistics["MaxLoad"] = self.statistics._MaxLoad
            Statistics["StartTime"] = self.statistics._start

            Statistics["MaxApdu"] = self.statistics._MaxaPdu
            Statistics["MaxNpdu"] = self.statistics._MaxnPdu

            Statistics["ForwardedQueueCurrentSize"] = self.ControllerLink.get_forwarder_queue()
            Statistics["WriterQueueCurrentSize"] = self.ControllerLink.get_writer_queue()
            
            _nbitems = len(self.statistics.TrendStats)
            minTS = 0
            if len(self.statistics.TrendStats) == 120:
                # Identify the smallest TS (we cannot assumed the list is sorted)
                minTS = 120
                for item in self.statistics.TrendStats:
                    if item["_TS"] < minTS:
                        minTS = item["_TS"]
                minTS -= 1  # To correct as the dataset start at 1 (and not 0)

            # Renum
            for item in self.statistics.TrendStats:
                _TS = item["_TS"]
                if _nbitems >= 120:
                    # Rolling window in progress
                    _TS -= minTS

                Statistics["Trend"].append({"_TS": _TS, "Rxps": item["Rxps"], "Txps": item["Txps"], "Load": item["Load"]})

        Statistics["Uptime"] = int(time() - Statistics["StartTime"])
        if Statistics["Uptime"] > 0:

            Statistics["Txps"] = round(Statistics["Sent"] / Statistics["Uptime"], 2)
            Statistics["Txpm"] = round(Statistics["Sent"] / Statistics["Uptime"] * 60, 2)
            Statistics["Txph"] = round(Statistics["Sent"] / Statistics["Uptime"] * 3600, 2)
            Statistics["Rxps"] = round(Statistics["Received"] / Statistics["Uptime"], 2)
            Statistics["Rxpm"] = round(Statistics["Received"] / Statistics["Uptime"] * 60, 2)
            Statistics["Rxph"] = round(Statistics["Received"] / Statistics["Uptime"] * 3600, 2)

        # LogErrorHistory . Hardcode on the UI side
        Statistics["Error"] = self.log.is_new_error()
        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == "GET":
            _response["Data"] = json.dumps(Statistics, sort_keys=True)
        return _response

    def rest_Settings_wo_debug(self, verb, data, parameters):
        return self.rest_Settings(verb, data, parameters, sendDebug=False)

    def rest_Settings_with_debug(self, verb, data, parameters):
        return self.rest_Settings(verb, data, parameters, sendDebug=True)

    def rest_Settings(self, verb, data, parameters, sendDebug=False):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == "GET":
            if len(parameters) != 0:
                return

            setting_lst = []
            for _theme in sorted(SETTINGS.keys()):
                if _theme in ("Reserved", "PluginTransport"):
                    continue
                if sendDebug and _theme != "VerboseLogging":
                    continue
                if _theme == "VerboseLogging" and not sendDebug:
                    continue
                theme = {
                    "_Order": SETTINGS[_theme]["Order"],
                    "_Theme": _theme,
                    "ListOfSettings": [],
                }

                for param in sorted(self.pluginconf.pluginConf.keys()):
                    if param not in SETTINGS[_theme]["param"]:
                        continue
                    if SETTINGS[_theme]["param"][param]["hidden"]:
                        continue

                    setting = {
                        "Name": param,
                        "default_value": SETTINGS[_theme]["param"][param]["default"],
                        "DataType": SETTINGS[_theme]["param"][param]["type"],
                        "restart_need": SETTINGS[_theme]["param"][param]["restart"],
                        "Advanced": SETTINGS[_theme]["param"][param]["Advanced"],
                    }

                    if SETTINGS[_theme]["param"][param]["type"] == "hex":
                        Domoticz.Debug("--> %s: %s - %s" % (param, self.pluginconf.pluginConf[param], type(self.pluginconf.pluginConf[param])))
                        if isinstance(self.pluginconf.pluginConf[param], int):
                            setting["current_value"] = "%x" % self.pluginconf.pluginConf[param]
                        else:
                            setting["current_value"] = "%x" % int(self.pluginconf.pluginConf[param], 16)
                    elif SETTINGS[_theme]["param"][param]["type"] == "list":
                        setting["list"] = []
                        setting["current_value"] = self.pluginconf.pluginConf[param]
                        for x in sorted(SETTINGS[_theme]["param"][param]["list"].keys()):
                            ListItem = {x: SETTINGS[_theme]["param"][param]["list"][x]}
                            setting["list"].append(ListItem)

                    else:
                        setting["current_value"] = self.pluginconf.pluginConf[param]
                    theme["ListOfSettings"].append(setting)
                setting_lst.append(theme)
            _response["Data"] = json.dumps(setting_lst, sort_keys=True)

        elif verb == "PUT":
            _response["Data"] = None
            data = data.decode("utf8")
            self.logging("Debug", "Data: %s" % data)
            data = data.replace("true", "1")  # UI is coming with true and not True
            data = data.replace("false", "0")  # UI is coming with false and not False

            setting_lst = eval(data)
            upd = False
            for setting in setting_lst:
                found = False
                self.logging("Debug", "setting: %s = %s" % (setting, setting_lst[setting]["current"]))

                # Do we have to update ?
                for _theme in SETTINGS:
                    for param in SETTINGS[_theme]["param"]:
                        if param != setting:
                            continue

                        found = True
                        upd = True
                        if str(setting_lst[setting]["current"]) == str(self.pluginconf.pluginConf[param]):
                            # Nothing to do
                            continue
                        if SETTINGS[_theme]["param"][param]["type"] == "hex" and int(str(setting_lst[setting]["current"]), 16) == self.pluginconf.pluginConf[param]:
                            continue

                        self.logging(
                            "Debug",
                            "Updating %s from %s to %s on theme: %s" % (param, self.pluginconf.pluginConf[param], setting_lst[setting]["current"], _theme),
                        )

                        self.restart_needed["RestartNeeded"] = max(SETTINGS[_theme]["param"][param]["restart"], self.restart_needed["RestartNeeded"])

                        if param == "Certification":
                            if setting_lst[setting]["current"] in CERTIFICATION_CODE:
                                self.pluginconf.pluginConf["Certification"] = setting_lst[setting]["current"]
                                self.pluginconf.pluginConf["CertificationCode"] = CERTIFICATION_CODE[setting_lst[setting]["current"]]
                            else:
                                Domoticz.Error("Unknown Certification code %s (allow are CE and FCC)" % (setting_lst[setting]["current"]))
                                continue

                        elif param == "blueLedOnOff":
                            if self.pluginconf.pluginConf[param] != setting_lst[setting]["current"]:
                                self.pluginconf.pluginConf[param] = setting_lst[setting]["current"]
                                if self.pluginconf.pluginConf[param]:
                                    zigateBlueLed(self, True)
                                else:
                                    zigateBlueLed(self, False)

                        elif param == "debugMatchId":
                            if setting_lst[setting]["current"] == "ffff":
                                self.pluginconf.pluginConf[param] = setting_lst[setting]["current"]
                            else:
                                self.pluginconf.pluginConf["debugMatchId"] = ""
                                matchID = setting_lst[setting]["current"].lower().split(",")
                                for key in matchID:
                                    if len(key) == 4:
                                        if key not in self.ListOfDevices:
                                            continue

                                        self.pluginconf.pluginConf["debugMatchId"] += key + ","
                                    if len(key) == 16:
                                        # Expect an IEEE
                                        if key not in self.IEEE2NWK:
                                            continue

                                        self.pluginconf.pluginConf["debugMatchId"] += self.IEEE2NWK[key] + ","
                                self.pluginconf.pluginConf["debugMatchId"] = self.pluginconf.pluginConf["debugMatchId"][:-1]  # Remove the last ,
                                
                        elif param == "TXpower_set" and self.zigbee_communitation == "zigpy":
                            if self.pluginconf.pluginConf[param] != setting_lst[setting]["current"]:
                                self.pluginconf.pluginConf[param] = setting_lst[setting]["current"]
                                set_TxPower(self, self.pluginconf.pluginConf[param])
                            
                        else:
                            if SETTINGS[_theme]["param"][param]["type"] == "hex":
                                # Domoticz.Log("--> %s: %s - %s" %(param, self.pluginconf.pluginConf[param], type(self.pluginconf.pluginConf[param])))
                                self.pluginconf.pluginConf[param] = int(str(setting_lst[setting]["current"]), 16)
                            else:
                                self.pluginconf.pluginConf[param] = setting_lst[setting]["current"]

                if not found:
                    Domoticz.Error("Unexpected parameter: %s" % setting)
                    _response["Data"] = {"unexpected parameters %s" % setting}

            if upd:
                # We need to write done the new version of PluginConf
                self.pluginconf.write_Settings()

        return _response

    def rest_PermitToJoin(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == "GET":
            duration = self.permitTojoin["Duration"]
            timestamp = self.permitTojoin["Starttime"]
            info = {}
            if duration == 255:
                info["PermitToJoin"] = 255
            elif duration == 0:
                info["PermitToJoin"] = 0
            elif int(time()) >= timestamp + duration:
                info["PermitToJoin"] = 0
            else:
                rest = self.permitTojoin["Starttime"] + self.permitTojoin["Duration"] - int(time())

                self.logging("Debug", "remain %s s" % rest)
                info["PermitToJoin"] = rest
            _response["Data"] = json.dumps(info, sort_keys=True)

        elif verb == "PUT":
            _response["Data"] = None
            if len(parameters) == 0:
                data = data.decode("utf8")
                data = json.loads(data)
                self.logging("Debug", "parameters: %s value = %s" % ("PermitToJoin", data["PermitToJoin"]))
                if "Router" in data:
                    duration = int(data["PermitToJoin"])
                    router = data["Router"]
                    if router in self.ListOfDevices:
                        # Allow Permit to join from this specific router
                        if duration == 0:
                            self.logging("Log", "Requesting router: %s to disable Permit to join" % router)
                        else:
                            self.logging("Log", "Requesting router: %s to enable Permit to join" % router)
                        TcSignificance = "01" if router == "0000" else "00"
                        # TcSignificance determines whether the remote device is a ‘Trust Centre’: TRUE: A Trust Centre FALSE: Not a Trust Centre
                        #sendZigateCmd(self, "0049", router + "%02x" % duration + TcSignificance)
                        PermitToJoin(self, "%02x" % duration, TargetAddress=router)

                elif self.pluginParameters["Mode2"] != "None":
                    ZigatePermitToJoin(self, int(data["PermitToJoin"]))
        return _response

    def rest_Device(self, verb, data, parameters):
        def getDeviceInfos(self, UnitId):
            return {
                "_DeviceID": self.Devices[UnitId].DeviceID,
                "Name": self.Devices[UnitId].Name,
                "ID": self.Devices[UnitId].ID,
                "sValue": self.Devices[UnitId].sValue,
                "nValue": self.Devices[UnitId].nValue,
                "SignaleLevel": self.Devices[UnitId].SignalLevel,
                "BatteryLevel": self.Devices[UnitId].BatteryLevel,
                "TimedOut": self.Devices[UnitId].TimedOut,
                # _dictDevices['Type'] = self.Devices[UnitId].Type
                # _dictDevices['SwitchType'] = self.Devices[UnitId].SwitchType
            }

        _dictDevices = {}
        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == "GET":
            if self.Devices is None or len(self.Devices) == 0:
                return _response

            if len(parameters) == 0:
                # Return the Full List of ZiGate Domoticz Widget
                device_lst = []
                for x in self.Devices:
                    if len(self.Devices[x].DeviceID) != 16:
                        continue

                    device_info = getDeviceInfos(self, x)
                    device_lst.append(device_info)
                _response["Data"] = json.dumps(device_lst, sort_keys=True)

            elif len(parameters) == 1:
                for x in self.Devices:
                    if len(self.Devices[x].DeviceID) != 16:
                        continue

                    if parameters[0] == self.Devices[x].DeviceID:
                        _dictDevices = device_info = getDeviceInfos(self, x)
                        _response["Data"] = json.dumps(_dictDevices, sort_keys=True)
                        break

            else:
                device_lst = []
                for parm in parameters:
                    device_info = {}
                    for x in self.Devices:
                        if len(self.Devices[x].DeviceID) != 16:
                            continue

                        if parm == self.Devices[x].DeviceID:
                            device_info = getDeviceInfos(self, x)
                            device_lst.append(device_info)
                _response["Data"] = json.dumps(device_lst, sort_keys=True)
        return _response

    def rest_zDevice_name(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == "DELETE":
            if len(parameters) == 1:
                ieee = nwkid = None
                deviceId = parameters[0]
                if len(deviceId) == 4:  # Short Network Addr
                    if deviceId not in self.ListOfDevices:
                        Domoticz.Error("rest_zDevice - Device: %s to be DELETED unknown LOD" % (deviceId))
                        Domoticz.Error("Device %s to be removed unknown" % deviceId)
                        _response["Data"] = json.dumps([], sort_keys=True)
                        return _response
                    nwkid = deviceId
                    ieee = self.ListOfDevices[deviceId]["IEEE"]
                else:
                    if deviceId not in self.IEEE2NWK:
                        Domoticz.Error("rest_zDevice - Device: %s to be DELETED unknown in IEEE22NWK" % (deviceId))
                        Domoticz.Error("Device %s to be removed unknown" % deviceId)
                        _response["Data"] = json.dumps([], sort_keys=True)
                        return _response
                    ieee = deviceId
                    nwkid = self.IEEE2NWK[ieee]
                if nwkid:
                    del self.ListOfDevices[nwkid]
                if ieee:
                    del self.IEEE2NWK[ieee]

                # for a remove in case device didn't send the leave
                if "IEEE" in self.ControllerData and ieee:
                    # uParrentAddress + uChildAddress (uint64)
                    if self.zigbee_communitation == "native":
                        sendZigateCmd(self, "0026", self.ControllerData["IEEE"] + ieee)

                action = {"Name": "Device %s/%s removed" % (nwkid, ieee)}
                _response["Data"] = json.dumps(action, sort_keys=True)

        elif verb == "GET":
            _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
            
            
            if len(self.ControllerData) == 0:
                _response["Data"] = json.dumps(dummy_zdevice_name(), sort_keys=True)
            else:
                device_lst = []
                for x in self.ListOfDevices:
                    if x == "0000":
                        continue

                    device = {"_NwkId": x}
                    for item in (
                        "Param",
                        "ZDeviceName",
                        "IEEE",
                        "Model",
                        "MacCapa",
                        "Status",
                        "ConsistencyCheck",
                        "Health",
                        "LQI",
                        "Battery",
                    ):
                        if item in self.ListOfDevices[x]:
                            if item == "MacCapa":
                                device["MacCapa"] = []
                                mac_capability = int(self.ListOfDevices[x][item], 16)
                                AltPAN = mac_capability & 0x00000001
                                DeviceType = (mac_capability >> 1) & 1
                                PowerSource = (mac_capability >> 2) & 1
                                ReceiveonIdle = (mac_capability >> 3) & 1
                                if DeviceType == 1:
                                    device["MacCapa"].append("FFD")
                                else:
                                    device["MacCapa"].append("RFD")
                                if ReceiveonIdle == 1:
                                    device["MacCapa"].append("RxonIdle")
                                if PowerSource == 1:
                                    device["MacCapa"].append("MainPower")
                                else:
                                    device["MacCapa"].append("Battery")
                                self.logging(
                                    "Debug",
                                    "decoded MacCapa from: %s to %s" % (self.ListOfDevices[x][item], str(device["MacCapa"])),
                                )
                            elif item == "Param":
                                device[item] = str(self.ListOfDevices[x][item])
                            else:
                                if self.ListOfDevices[x][item] == {}:
                                    device[item] = ""
                                else:
                                    device[item] = self.ListOfDevices[x][item]
                        elif item == "Param":
                            # Seems unknown, so let's create it
                            device[item] = str({})
                        else:
                            device[item] = ""

                    device["WidgetList"] = []
                    for ep in self.ListOfDevices[x]["Ep"]:
                        if "ClusterType" in self.ListOfDevices[x]["Ep"][ep]:
                            clusterType = self.ListOfDevices[x]["Ep"][ep]["ClusterType"]
                            for widgetID in clusterType:
                                for widget in self.Devices:
                                    if self.Devices[widget].ID == int(widgetID):
                                        self.logging("Debug", "Widget Name: %s %s" % (widgetID, self.Devices[widget].Name))
                                        if self.Devices[widget].Name not in device["WidgetList"]:
                                            device["WidgetList"].append(self.Devices[widget].Name)

                        elif "ClusterType" in self.ListOfDevices[x]:
                            clusterType = self.ListOfDevices[x]["ClusterType"]
                            for widgetID in clusterType:
                                for widget in self.Devices:
                                    if self.Devices[widget].ID == int(widgetID):
                                        self.logging("Debug", "Widget Name: %s %s" % (widgetID, self.Devices[widget].Name))
                                        if self.Devices[widget].Name not in device["WidgetList"]:
                                            device["WidgetList"].append(self.Devices[widget].Name)

                    if device not in device_lst:
                        device_lst.append(device)
                    # _response["Data"] = json.dumps( device_lst, sort_keys=True )
                    self.logging("Debug", "zDevice_name - sending %s" % device_lst)
                    _response["Data"] = json.dumps(device_lst, sort_keys=True)

        elif verb == "PUT":
            _response["Data"] = None
            data = data.decode("utf8")
            self.logging("Debug", "Data: %s" % data)
            data = eval(data)
            for x in data:
                if "ZDeviceName" in x and "IEEE" in x:
                    for dev in self.ListOfDevices:
                        if self.ListOfDevices[dev]["IEEE"] == x["IEEE"]:
                            if self.ListOfDevices[dev]["ZDeviceName"] != x["ZDeviceName"]:
                                self.ListOfDevices[dev]["ZDeviceName"] = x["ZDeviceName"]
                                self.logging(
                                    "Debug",
                                    "Updating ZDeviceName to %s for IEEE: %s NWKID: %s" % (self.ListOfDevices[dev]["ZDeviceName"], self.ListOfDevices[dev]["IEEE"], dev),
                                )
                            if "Param" not in self.ListOfDevices[dev] or self.ListOfDevices[dev]["Param"] != x["Param"]:
                                self.ListOfDevices[dev]["Param"] = check_device_param(self, dev, x["Param"])
                                self.logging(
                                    "Debug",
                                    "Updating Param to %s for IEEE: %s NWKID: %s" % (self.ListOfDevices[dev]["Param"], self.ListOfDevices[dev]["IEEE"], dev),
                                )
                                self.ListOfDevices[dev]["CheckParam"] = True
                else:
                    Domoticz.Error("wrong data received: %s" % data)

        return _response

    def rest_zDevice(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == "DELETE":
            if len(parameters) == 1:
                deviceId = parameters[0]
                if len(deviceId) == 4:  # Short Network Addr
                    if deviceId not in self.ListOfDevices:
                        Domoticz.Error("rest_zDevice - Device: %s to be DELETED unknown LOD" % (deviceId))
                        Domoticz.Error("Device %s to be removed unknown" % deviceId)
                        _response["Data"] = json.dumps([], sort_keys=True)
                        return _response
                    nwkid = deviceId
                    ieee = self.ListOfDevice[deviceId]["IEEE"]
                else:
                    if deviceId not in self.IEEE2NWK:
                        Domoticz.Error("rest_zDevice - Device: %s to be DELETED unknown in IEEE22NWK" % (deviceId))
                        Domoticz.Error("Device %s to be removed unknown" % deviceId)
                        _response["Data"] = json.dumps([], sort_keys=True)
                        return _response
                    ieee = deviceId
                    nwkid = self.IEEE2NWK[ieee]

                del self.ListOfDevice[nwkid]
                del self.IEEE2NWK[ieee]
                action = {"Name": "Device %s/%s removed" % (nwkid, ieee)}
                _response["Data"] = json.dumps(action, sort_keys=True)
            return _response

        if verb == "GET":
            if self.Devices is None or len(self.Devices) == 0:
                return _response
            if self.ListOfDevices is None or len(self.ListOfDevices) == 0:
                return _response
            if len(parameters) == 0:
                zdev_lst = []
                for item in self.ListOfDevices:
                    if item == "0000":
                        continue
                    device = {"_NwkId": item}
                    # Main Attributes
                    for attribut in (
                        "ZDeviceName",
                        "ConsistencyCheck",
                        "Stamp",
                        "Health",
                        "Status",
                        "Battery",
                        "LQI",
                        "Model",
                        "IEEE",
                        "ProfileID",
                        "ZDeviceID",
                        "Manufacturer",
                        "DeviceType",
                        "LogicalType",
                        "PowerSource",
                        "ReceiveOnIdle",
                        "App Version",
                        "Stack Version",
                        "HW Version",
                    ):

                        if attribut in self.ListOfDevices[item]:
                            if self.ListOfDevices[item][attribut] == {}:
                                device[attribut] = ""

                            elif attribut == "ConsistencyCheck" and self.ListOfDevices[item]["Status"] == "notDB":
                                self.ListOfDevices[item][attribut] = "not in DZ"

                            elif self.ListOfDevices[item][attribut] == "" and self.ListOfDevices[item]["MacCapa"] == "8e":
                                if attribut == "DeviceType":
                                    device[attribut] = "FFD"
                                elif attribut == "LogicalType":
                                    device[attribut] = "Router"
                                elif attribut == "PowerSource":
                                    device[attribut] = "Main"

                            elif attribut == "LogicalType" and self.ListOfDevices[item][attribut] not in (
                                "Router",
                                "Coordinator",
                                "End Device",
                            ):
                                if self.ListOfDevices[item]["MacCapa"] == "8e":
                                    device[attribut] = "Router"
                                elif self.ListOfDevices[item]["MacCapa"] == "80":
                                    device[attribut] = "End Device"

                            else:
                                device[attribut] = self.ListOfDevices[item][attribut]
                        else:
                            device[attribut] = ""

                    # Last Seen Information
                    device["LastSeen"] = ""
                    if "Stamp" in self.ListOfDevices[item] and "LastSeen" in self.ListOfDevices[item]["Stamp"]:
                        device["LastSeen"] = self.ListOfDevices[item]["Stamp"]["LastSeen"]

                    # ClusterType
                    _widget_lst = []
                    if "ClusterType" in self.ListOfDevices[item]:
                        for widgetId in self.ListOfDevices[item]["ClusterType"]:
                            widget = {"_WidgetID": widgetId, "WidgetName": ""}
                            for x in self.Devices:
                                if self.Devices[x].ID == int(widgetId):
                                    widget["WidgetName"] = self.Devices[x].Name
                                    break

                            widget["WidgetType"] = self.ListOfDevices[item]["ClusterType"][widgetId]
                            _widget_lst.append(widget)

                    # Ep informations
                    ep_lst = []
                    if "Ep" in self.ListOfDevices[item]:
                        for epId in self.ListOfDevices[item]["Ep"]:
                            _ep = {"Ep": epId, "ClusterList": []}
                            for cluster in self.ListOfDevices[item]["Ep"][epId]:
                                if cluster == "ColorMode":
                                    continue

                                if cluster == "ClusterType":
                                    for widgetId in self.ListOfDevices[item]["Ep"][epId]["ClusterType"]:
                                        widget = {"_WidgetID": widgetId, "WidgetName": ""}
                                        for x in self.Devices:
                                            if self.Devices[x].ID == int(widgetId):
                                                widget["WidgetName"] = self.Devices[x].Name
                                                break

                                        widget["WidgetType"] = self.ListOfDevices[item]["Ep"][epId]["ClusterType"][widgetId]
                                        _widget_lst.append(widget)
                                    continue

                                elif cluster == "Type":
                                    device["Type"] = self.ListOfDevices[item]["Ep"][epId]["Type"]
                                    continue

                                _cluster = {}
                                if cluster in ZCL_CLUSTERS_LIST:
                                    _cluster[cluster] = ZCL_CLUSTERS_LIST[cluster]

                                else:
                                    _cluster[cluster] = "Unknown"
                                _ep["ClusterList"].append(_cluster)

                            ep_lst.append(_ep)
                    device["Ep"] = ep_lst
                    device["WidgetList"] = _widget_lst

                    # Last Commands
                    lastcmd_lst = []
                    if "Last Cmds" in self.ListOfDevices[item]:
                        for lastCmd in self.ListOfDevices[item]["Last Cmds"]:
                            timestamp = lastCmd[0]
                            cmd = lastCmd[1]
                            # payload = lastCmd[2]
                            _cmd = {"CmdCode": cmd, "TimeStamps": timestamp}
                            lastcmd_lst.append(_cmd)
                    device["LastCmds"] = lastcmd_lst
                    zdev_lst.append(device)

                _response["Data"] = json.dumps(zdev_lst, sort_keys=True)
        return _response

    def rest_zDevice_raw(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == "GET":
            if self.Devices is None or len(self.Devices) == 0:
                return _response
            if self.ListOfDevices is None or len(self.ListOfDevices) == 0:
                return _response
            if len(parameters) == 0:
                zdev_lst = []
                for item in self.ListOfDevices:
                    entry = dict(self.ListOfDevices[item])
                    entry["NwkID"] = item
                    zdev_lst.append(entry)
                _response["Data"] = json.dumps(zdev_lst, sort_keys=False)
            elif len(parameters) == 1:
                if parameters[0] in self.ListOfDevices:
                    _response["Data"] = json.dumps(self.ListOfDevices[parameters[0]], sort_keys=False)
                elif parameters[0] in self.IEEE2NWK:
                    _response["Data"] = json.dumps(self.ListOfDevices[self.IEEE2NWK[parameters[0]]], sort_keys=False)

        return _response

    def rest_change_channel(self, verb, data, parameters):
        Domoticz.Log("rest_change_channel - %s %s" % (verb, data))
        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb != "PUT":
            _response["Data"] = {"Error": "Unknow verb"}
            return _response

        _response["Data"] = None
        if len(parameters) == 0:
            data = data.decode("utf8")
            data = json.loads(data)
            Domoticz.Log("---> Data: %s" % str(data))
            if "Channel" not in data:
                Domoticz.Error("Unexpected request: %s" % data)
                _response["Data"] = {"Error": "Unknow verb"}
                return _response
            channel = data["Channel"]
            if channel not in range(11, 27):
                _response["Data"] = {"Error": "incorrect channel: %s" % channel}
                return _response
            initiate_change_channel(self, int(channel))

            _response["Data"] = {"Request channel: %s" % channel}
        return _response

    def rest_raw_command(self, verb, data, parameters):

        Domoticz.Log("raw_command - %s %s" % (verb, data))
        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == "PUT":
            _response["Data"] = None
            if len(parameters) == 0:
                data = data.decode("utf8")
                data = json.loads(data)
                Domoticz.Log("---> Data: %s" % str(data))
                if "Command" not in data and "payload" not in data:
                    Domoticz.Error("Unexpected request: %s" % data)
                    _response["Data"] = json.dumps("Executing %s on %s" % (data["Command"], data["payload"]))
                    return _response

                if not is_hex(data["Command"]) or (is_hex(data["Command"]) and int(data["Command"], 16) not in ZIGATE_COMMANDS):
                    Domoticz.Error("raw_command - Unknown MessageType received %s" % data["Command"])
                    _response["Data"] = json.dumps("Unknown MessageType received %s" % data["Command"])
                    return _response

                payload = data["payload"]
                if payload is None:
                    payload = ""
                sendZigateCmd(self, data["Command"], data["payload"])
                self.logging("Log", "rest_dev_command - Command: %s payload %s" % (data["Command"], data["payload"]))
                _response["Data"] = json.dumps("Executing %s on %s" % (data["Command"], data["payload"]))
        return _response

    def rest_dev_command(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == "PUT":
            _response["Data"] = None
            if len(parameters) == 0:
                data = data.decode("utf8")
                data = json.loads(data)
                Domoticz.Log("---> Data: %s" % str(data))
                self.logging(
                    "Log",
                    "rest_dev_command - Command: %s on object: %s with extra %s %s" % (data["Command"], data["NwkId"], data["Value"], data["Color"]),
                )
                _response["Data"] = json.dumps("Executing %s on %s" % (data["Command"], data["NwkId"]))
                if "Command" not in data:
                    return _response
                if data["Command"] == "":
                    return _response
                if data["Value"] == "" or data["Value"] is None:
                    Level = 0
                else:
                    if is_hex(str(data["Value"])):
                        Level = int(str(data["Value"]), 16)
                    else:
                        Level = int(str(data["Value"]))
                ColorMode = ColorValue = ""
                color = ""
                if data["Color"] == "" or data["Color"] is None:
                    Hue_List = {}
                else:
                    # Decoding RGB
                    # rgb(30,96,239)
                    ColorMode = data["Color"].split("(")[0]
                    ColorValue = data["Color"].split("(")[1].split(")")[0]
                    if ColorMode == "rgb":
                        Hue_List = {"m": 3}
                        Hue_List["r"], Hue_List["g"], Hue_List["b"] = ColorValue.split(",")
                    self.logging(
                        "Log",
                        "rest_dev_command -        Color decoding m: %s r:%s g: %s b: %s" % (Hue_List["m"], Hue_List["r"], Hue_List["g"], Hue_List["b"]),
                    )
                Color = json.dumps(Hue_List)
                epout = "01"
                if "Type" not in data:
                    actuators(self, data["Command"], data["NwkId"], epout, "Switch")
                else:
                    SWITCH_2_CLUSTER = {
                        "Switch": "0006",
                        "LivoloSWL": "0006",
                        "LivoloSWR": "0006",
                        "LvlControl": "0008",
                        "WindowCovering": "0102",
                        "ThermoSetpoint": "0201",
                        "ColorControlRGBWW": "0300",
                        "ColorControlWW": "0300",
                        "ColorControlRGB": "0300",
                    }

                    key = data["NwkId"]
                    if data["Type"] is None:
                        clusterCode = "0003"
                    else:
                        clusterCode = SWITCH_2_CLUSTER[data["Type"]]

                    for tmpEp in self.ListOfDevices[key]["Ep"]:
                        if clusterCode in self.ListOfDevices[key]["Ep"][tmpEp]:  # switch cluster
                            epout = tmpEp
                    actuators(self, data["Command"], key, epout, data["Type"], value=Level, color=Color)

        return _response

    def rest_dev_capabilities(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb != "GET":
            return _response

        if self.Devices is None or len(self.Devices) == 0:
            return _response

        if self.ListOfDevices is None or len(self.ListOfDevices) == 0:
            return _response

        if len(parameters) == 0:
            Domoticz.Error("rest_dev_capabilities - expecting a device id! %s" % (parameters))
            return _response

        if len(parameters) != 1:
            return

        if parameters[0] not in self.ListOfDevices and parameters[0] not in self.IEEE2NWK:
            Domoticz.Error("rest_dev_capabilities - Device %s doesn't exist" % (parameters[0]))
            return _response

        # Check Capabilities
        CLUSTER_INFOS = {
            "0003": [
                {"actuator": "Identify", "Value": "", "Type": ()},
                {"actuator": "IdentifyEffect", "Value": "hex", "Type": ()},
            ],
            "0006": [
                {"actuator": "On", "Value": "", "Type": ("Switch",)},
                {"actuator": "Off", "Value": "", "Type": ("Switch",)},
                {"actuator": "Toggle", "Value": "", "Type": ("Switch",)},
            ],
            "0008": [
                {"actuator": "SetLevel", "Value": "int", "Type": ("LvlControl",)},
            ],
            "0102": [
                {"actuator": "On", "Value": "", "Type": ("WindowCovering",)},
                {"actuator": "Off", "Value": "", "Type": ("WindowCovering",)},
                {"actuator": "Stop", "Value": "", "Type": ("WindowCovering",)},
                {"actuator": "SetLevel", "Value": "hex", "Type": ("WindowCovering",)},
            ],
            "0201": [
                {"actuator": "SetPoint", "Value": "hex", "Type": ("ThermoSetpoint",)},
            ],
            "0300": [
                {
                    "actuator": "SetColor",
                    "Value": "rgbww",
                    "Type": ("ColorControlRGBWW", "ColorControlWW", "ColorControlRGB"),
                },
            ],
        }
        dev_capabilities = {"NwkId": {}, "Capabilities": [], "Types": []}
        if parameters[0] in self.ListOfDevices:
            _nwkid = parameters[0]
        elif parameters[0] in self.IEEE2NWK:
            _nwkid = self.IEEE2NWK[parameters[0]]
        dev_capabilities["NwkId"] = _nwkid

        for ep in self.ListOfDevices[_nwkid]["Ep"]:
            for cluster in self.ListOfDevices[_nwkid]["Ep"][ep]:
                if cluster not in CLUSTER_INFOS:
                    continue
                for action in CLUSTER_INFOS[cluster]:
                    _capabilitie = {
                        "actuator": action["actuator"],
                        "Value": False if action["Value"] == "" else action["Value"],
                        "Type": True if len(action["Type"]) != 0 else False,
                    }
                    dev_capabilities["Capabilities"].append(_capabilitie)

                    for cap in action["Type"]:
                        if cap not in dev_capabilities["Types"]:
                            dev_capabilities["Types"].append(cap)

                    # Adding non generic Capabilities
                    if "Model" in self.ListOfDevices[_nwkid] and self.ListOfDevices[_nwkid]["Model"] != {} and self.ListOfDevices[_nwkid]["Model"] == "TI0001":
                        if "LivoloSWL" not in dev_capabilities["Types"]:
                            dev_capabilities["Types"].append("LivoloSWL")
                        if "LivoloSWR" not in dev_capabilities["Types"]:
                            dev_capabilities["Types"].append("LivoloSWR")

                if cluster == "0006" and "4003" in self.ListOfDevices[_nwkid]["Ep"][ep]["0006"]:
                    _capabilitie = {"actuator": "PowerStateAfterOffOn", "Value": "hex", "Type": False}
                    dev_capabilities["Capabilities"].append(_capabilitie)

        _response["Data"] = json.dumps(dev_capabilities)
        return _response

    def rest_zigate_mode(self, verb, data, parameters):

        Domoticz.Log("rest_zigate_mode mode: %s" % parameters)
        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == "GET":
            _response["Data"] = None
            if len(parameters) == 1:
                mode = parameters[0]
                if mode in ("0", "1", "2"):
                    zigate_set_mode(self, int(mode) )
                    #send_zigate_mode(self, int(mode))
                    _response["Data"] = {"ZiGate mode: %s requested" % mode}
        return _response

    def rest_logErrorHistory(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"

        if verb == "GET":
            if self.log.LogErrorHistory:
                try:
                    _response["Data"] = json.dumps(self.log.LogErrorHistory, sort_keys=False)
                    self.log.reset_new_error()
                except Exception as e:
                    Domoticz.Error("rest_logErrorHistory - Exception %s while saving: %s" % (e, str(self.log.LogErrorHistory)))
        return _response

    def rest_logErrorHistoryClear(self, verb, data, parameters):

        _response = prepResponseMessage(self, setupHeadersResponse())
        _response["Headers"]["Content-Type"] = "application/json; charset=utf-8"
        if verb == "GET":
            self.logging("Status", "Erase Log History")
            self.log.loggingClearErrorHistory()
        return _response

    def logging(self, logType, message):
        self.log.logging("WebServer", logType, message)

def dummy_zdevice_name():
    
    return [{"Battery": "", "ConsistencyCheck": "ok", "Health": "Live", "IEEE": "90fd9ffffe86c7a1", "LQI": 80, "MacCapa": ["FFD", "RxonIdle", "MainPower"], "Model": "TRADFRI bulb E27 WS clear 950lm", "Param": "{'PowerOnAfterOffOn': 255, 'fadingOff': 0, 'moveToHueSatu': 0, 'moveToColourTemp': 0, 'moveToColourRGB': 0, 'moveToLevel': 0}", "Status": "inDB", "WidgetList": ["Zigbee - TRADFRI bulb E27 WS clear 950lm_ColorControlWW-90fd9ffffe86c7a1-01"], "ZDeviceName": "Led Ikea", "_NwkId": "ada7"}, {"Battery": "", "ConsistencyCheck": "ok", "Health": "Live", "IEEE": "60a423fffe529d60", "LQI": 80, "MacCapa": ["FFD", "RxonIdle", "MainPower"], "Model": "LXEK-1", "Param": "{'PowerOnAfterOffOn': 255, 'fadingOff': 0, 'moveToHueSatu': 0, 'moveToColourTemp': 0, 'moveToColourRGB': 0, 'moveToLevel': 0}", "Status": "inDB", "WidgetList": ["Zigbee - LXEK-1_ColorControlRGBWW-60a423fffe529d60-01"], "ZDeviceName": "Led LKex", "_NwkId": "7173"}, {"Battery": "", "ConsistencyCheck": "ok", "Health": "Live", "IEEE": "680ae2fffe7aca89", "LQI": 80, "MacCapa": ["FFD", "RxonIdle", "MainPower"], "Model": "TRADFRI Signal Repeater", "Param": "{}", "Status": "inDB", "WidgetList": ["Zigbee - TRADFRI Signal Repeater_Voltage-680ae2fffe7aca89-01"], "ZDeviceName": "Repeater", "_NwkId": "a5ee"}, {"Battery": 16.0, "ConsistencyCheck": "ok", "Health": "Not seen last 24hours", "IEEE": "90fd9ffffeea89e8", "LQI": 25, "MacCapa": ["RFD", "Battery"], "Model": "TRADFRI remote control", "Param": "{}", "Status": "inDB", "WidgetList": ["Zigbee - TRADFRI remote control_Ikea_Round_5b-90fd9ffffeea89e8-01"], "ZDeviceName": "Remote Tradfri", "_NwkId": "cee1"}, {"Battery": 100, "ConsistencyCheck": "ok", "Health": "Live", "IEEE": "000d6f0011087079", "LQI": 116, "MacCapa": ["FFD", "RxonIdle", "MainPower"], "Model": "WarningDevice", "Param": "{}", "Status": "inDB", "WidgetList": ["Zigbee - WarningDevice_AlarmWD-000d6f0011087079-01"], "ZDeviceName": "IAS Sirene", "_NwkId": "2e33"}, {"Battery": 53, "ConsistencyCheck": "ok", "Health": "Live", "IEEE": "54ef441000298533", "LQI": 76, "MacCapa": ["RFD", "Battery"], "Model": "lumi.magnet.acn001", "Param": "{}", "Status": "inDB", "WidgetList": ["Zigbee - lumi.magnet.acn001_Door-54ef441000298533-01"], "ZDeviceName": "Lumi Door", "_NwkId": "bb45"}, {"Battery": "", "ConsistencyCheck": "ok", "Health": "Live", "IEEE": "00047400008aff8b", "LQI": 80, "MacCapa": ["FFD", "RxonIdle", "MainPower"], "Model": "Shutter switch with neutral", "Param": "{'netatmoInvertShutter': 0, 'netatmoLedShutter': 0}", "Status": "inDB", "WidgetList": ["Zigbee - Shutter switch with neutral_Venetian-00047400008aff8b-01"], "ZDeviceName": "Inter Shutter Legrand", "_NwkId": "06ab"}, {"Battery": "", "ConsistencyCheck": "ok", "Health": "Live", "IEEE": "000474000082a54f", "LQI": 18, "MacCapa": ["FFD", "RxonIdle", "MainPower"], "Model": "Dimmer switch wo neutral", "Param": "{'netatmoEnableDimmer': 1, 'PowerOnAfterOffOn': 255, 'BallastMaxLevel': 254, 'BallastMinLevel': 1}", "Status": "inDB", "WidgetList": ["Zigbee - Dimmer switch wo neutral_LvlControl-000474000082a54f-01"], "ZDeviceName": "Inter Dimmer Legrand", "_NwkId": "9c25"}, {"Battery": "", "ConsistencyCheck": "ok", "Health": "Live", "IEEE": "00047400001f09a4", "LQI": 80, "MacCapa": ["FFD", "RxonIdle", "MainPower"], "Model": "Micromodule switch", "Param": "{'PowerOnAfterOffOn': 255}", "Status": "inDB", "WidgetList": ["Zigbee - Micromodule switch_Switch-00047400001f09a4-01"], "ZDeviceName": "Micromodule Legrand", "_NwkId": "8706"}, {"Battery": "", "ConsistencyCheck": "ok", "Health": "", "IEEE": "00158d0003021601", "LQI": 0, "MacCapa": ["RFD", "Battery"], "Model": "lumi.sensor_motion.aq2", "Param": "{}", "Status": "inDB", "WidgetList": ["Zigbee - lumi.sensor_motion.aq2_Motion-00158d0003021601-01", "Zigbee - lumi.sensor_motion.aq2_Lux-00158d0003021601-01"], "ZDeviceName": "Lumi Motion", "_NwkId": "6f81"}, {"Battery": 100, "ConsistencyCheck": "ok", "Health": "Live", "IEEE": "0015bc001a01aa27", "LQI": 83, "MacCapa": ["RFD", "Battery"], "Model": "MOSZB-140", "Param": "{}", "Status": "inDB", "WidgetList": ["Zigbee - MOSZB-140_Motion-0015bc001a01aa27-23", "Zigbee - MOSZB-140_Tamper-0015bc001a01aa27-23", "Zigbee - MOSZB-140_Voltage-0015bc001a01aa27-23", "Zigbee - MOSZB-140_Temp-0015bc001a01aa27-26", "Zigbee - MOSZB-140_Lux-0015bc001a01aa27-27"], "ZDeviceName": "Motion frient", "_NwkId": "b9bc"}, {"Battery": 63, "ConsistencyCheck": "ok", "Health": "Live", "IEEE": "00158d000323dabe", "LQI": 61, "MacCapa": ["RFD", "Battery"], "Model": "lumi.sensor_switch", "Param": "{}", "Status": "inDB", "WidgetList": ["Zigbee - lumi.sensor_switch_SwitchAQ2-00158d000323dabe-01"], "ZDeviceName": "Lumi Switch (rond)", "_NwkId": "a029"}, {"Battery": 100.0, "ConsistencyCheck": "ok", "Health": "Live", "IEEE": "000d6ffffea1e6da", "LQI": 94, "MacCapa": ["RFD", "Battery"], "Model": "TRADFRI onoff switch", "Param": "{}", "Status": "inDB", "WidgetList": ["Zigbee - TRADFRI onoff switch_SwitchIKEA-000d6ffffea1e6da-01"], "ZDeviceName": "OnOff Ikea", "_NwkId": "c6ca"}, {"Battery": 100.0, "ConsistencyCheck": "ok", "Health": "Live", "IEEE": "000b57fffe2c0dde", "LQI": 87, "MacCapa": ["RFD", "Battery"], "Model": "TRADFRI wireless dimmer", "Param": "{}", "Status": "inDB", "WidgetList": ["Zigbee - TRADFRI wireless dimmer_GenericLvlControl-000b57fffe2c0dde-01"], "ZDeviceName": "Dim Ikea", "_NwkId": "6c43"}, {"Battery": 100, "ConsistencyCheck": "ok", "Health": "Live", "IEEE": "588e81fffe35f595", "LQI": 80, "MacCapa": ["RFD", "Battery"], "Model": "Wiser2-Thermostat", "Param": "{'WiserLockThermostat': 0, 'WiserRoomNumber': 1}", "Status": "inDB", "WidgetList": ["Zigbee - Wiser2-Thermostat_Temp+Hum-588e81fffe35f595-01", "Zigbee - Wiser2-Thermostat_Humi-588e81fffe35f595-01", "Zigbee - Wiser2-Thermostat_Temp-588e81fffe35f595-01", "Zigbee - Wiser2-Thermostat_ThermoSetpoint-588e81fffe35f595-01", "Zigbee - Wiser2-Thermostat_Valve-588e81fffe35f595-01"], "ZDeviceName": "Wiser Thermostat", "_NwkId": "5a00"}]


def check_device_param(self, nwkid, param):

    try:
        return eval(param)

    except Exception as e:
        if "ZDeviceName" in self.ListOfDevices[nwkid]:
            self.logging(
                "Error",
                "When updating Device Management, Device: %s/%s got a wrong Parameter syntax for '%s' - %s.\n Make sure to use JSON syntax" % (self.ListOfDevices[nwkid]["ZDeviceName"], nwkid, param, e),
            )
        else:
            self.logging(
                "Error",
                "When updating Device Management, Device: %s got a wrong Parameter syntax for '%s' - %s.\n Make sure to use JSON syntax" % (nwkid, param, e),
            )
    return {}
