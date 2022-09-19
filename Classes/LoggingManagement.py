#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module : logging.py


    Description: Plugin logging routines

"""

import json
import logging
import os
import threading
import time
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from queue import PriorityQueue, Queue

import Domoticz

LOG_ERROR_HISTORY = "PluginZigbee_log_error_history.json"
LOG_FILE = "/PluginZigbee_"

class LoggingManagement:
    def __init__(self, pluginconf, PluginHealth, HardwareID, ListOfDevices, permitTojoin):
        self._newError = False
        self.LogErrorHistory = {}
        self.pluginconf = pluginconf
        self.PluginHealth = PluginHealth
        self.HardwareID = HardwareID
        self.ListOfDevices = ListOfDevices
        self.permitTojoin = permitTojoin
        self.FirmwareVersion = None
        self.FirmwareMajorVersion = None
        self.PluginVersion = None
        self.running = True
        self.logging_queue = None
        self.logging_thread = None
        self._startTime = int(time.time())
        self.zigpy_log_zigate = None
        self.zigpy_log_znp = None
        self.zigpy_login()

        start_logging_thread(self)

        # Thread log filter configuration
        self.threadLogConfig = {}
        self.threadLogConfig["MainThread"] = "Domoticz"
        self.threadLogConfig["ZigateSerial_%s" % HardwareID] = self.threadLogConfig[
            "ZigateTCPIP_%s" % HardwareID
        ] = self.threadLogConfig["ZigpyCom_%s" % HardwareID] = "Communication"
        self.threadLogConfig["ZigateForwader_%s" % HardwareID] = self.threadLogConfig[
            "ZigpyForwarder_%s" % HardwareID
        ] = "Forwarder"
        self.threadLogConfig["ZiGateWriter_%s" % HardwareID] = "Writer"

    def reset_new_error(self):
        self._newError = False

    def is_new_error(self):
        return bool(self._newError and bool(self.LogErrorHistory))

    def loggingUpdatePluginVersion(self, Version):
        self.PluginVersion = Version
        if (
            self.LogErrorHistory
            and self.LogErrorHistory["LastLog"]
            and "StartTime" in self.LogErrorHistory[str(self.LogErrorHistory["LastLog"])]
            and self.LogErrorHistory[str(self.LogErrorHistory["LastLog"])]["StartTime"] == self._startTime
        ):
            self.LogErrorHistory[str(self.LogErrorHistory["LastLog"])]["PluginVersion"] = Version

    def loggingUpdateFirmware(self, FirmwareVersion, FirmwareMajorVersion):
        if self.FirmwareVersion and self.FirmwareMajorVersion:
            return
        self.FirmwareVersion = FirmwareVersion
        self.FirmwareMajorVersion = FirmwareMajorVersion
        if (
            self.LogErrorHistory
            and self.LogErrorHistory["LastLog"]
            and "StartTime" in self.LogErrorHistory[str(self.LogErrorHistory["LastLog"])]
            and self.LogErrorHistory[str(self.LogErrorHistory["LastLog"])]["StartTime"] == self._startTime
        ):
            self.LogErrorHistory[str(self.LogErrorHistory["LastLog"])]["FirmwareVersion"] = FirmwareVersion
            self.LogErrorHistory[str(self.LogErrorHistory["LastLog"])]["FirmwareMajorVersion"] = FirmwareMajorVersion

    def zigpy_login(self):
        if ( "debugTransportZigpyZNP" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["debugTransportZigpyZNP"] ):
            # Debug ZNP
            zigpy_loging_mode("debug")
            zigpy_logging_znp("debug")

        elif ( "debugTransportZigpyEZSP" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["debugTransportZigpyEZSP"] ):
            # Debug Bellows/Ezsp
            zigpy_loging_mode("debug")
            zigpy_logging_ezsp("debug")

        elif ( "debugTransportZigpyZigate" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["debugTransportZigpyZigate"] ):
            # Debug Zigate
            zigpy_loging_mode("debug")
            zigpy_logging_zigate("debug")
            
        elif ( "debugTransportZigpydeCONZ" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["debugTransportZigpydeCONZ"] ):
            # Debug deConz
            zigpy_loging_mode("debug")
            zigpy_logging_deconz("debug")

        else:
            # Set to Warning Level
            zigpy_loging_mode("warning")
            zigpy_logging_zigate("warning")
            zigpy_logging_deconz("warning")
            zigpy_logging_ezsp("warning")
            zigpy_logging_znp("warning")

    def openLogFile(self):
        self.open_logging_mode()
        self.open_log_history()

    def open_logging_mode(self):
        if not self.pluginconf.pluginConf["enablePluginLogging"]:
            return

        logfilename = self.pluginconf.pluginConf["pluginLogs"] + LOG_FILE + "%02d" % self.HardwareID + ".log"
        _backupCount = 7  # Keep 7 days of Logging
        _maxBytes = 0
        if "loggingBackupCount" in self.pluginconf.pluginConf:
            _backupCount = int(self.pluginconf.pluginConf["loggingBackupCount"])
        if "loggingMaxMegaBytes" in self.pluginconf.pluginConf:
            _maxBytes = int(self.pluginconf.pluginConf["loggingMaxMegaBytes"]) * 1024 * 1024
        Domoticz.Status("Please watch plugin log into %s" % logfilename)
        if _maxBytes == 0:
            # Enable TimedRotating
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s %(levelname)-8s:%(message)s",
                handlers=[TimedRotatingFileHandler(logfilename, when="midnight", interval=1, backupCount=_backupCount)],
            )
        else:
            # Enable RotatingFileHandler
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s %(levelname)-8s:%(message)s",
                handlers=[RotatingFileHandler(logfilename, maxBytes=_maxBytes, backupCount=_backupCount)],
            )
        if "PluginLogMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["PluginLogMode"] in ( 0o640, 0o640, 0o644 ):
                os.chmod(logfilename, self.pluginconf.pluginConf["PluginLogMode"])



    def open_log_history(self):
        jsonLogHistory = self.pluginconf.pluginConf["pluginLogs"] + "/" + LOG_ERROR_HISTORY
        try:
            handle = open(jsonLogHistory, "r", encoding="utf-8")
        except Exception as e:
            Domoticz.Status("Log history not found, no error logged")
            # Domoticz.Error(repr(e))
            return

        try:
            self.LogErrorHistory = json.load(handle)
            # By default we will leave No Error even if there are from the past
            # if bool(self.LogErrorHistory):
            #    self._newError  = True

        except json.decoder.JSONDecodeError as e:
            loggingWriteErrorHistory(self)  # flush the file to avoid the error next startup
            Domoticz.Error("load Json LogErrorHistory poorly-formed %s, not JSON: %s" % (jsonLogHistory, e))

        except Exception as e:
            loggingWriteErrorHistory(self)  # flush the file to avoid the error next startup
            Domoticz.Error("load Json LogErrorHistory Error %s, not JSON: %s" % (jsonLogHistory, e))

        handle.close()

    def closeLogFile(self):
        if self.logging_thread is None:
            Domoticz.Error("closeLogFile - logging_thread is None")
            return

        self.running = False
        if self.logging_queue is None:
            Domoticz.Error("closeLogFile - logging_queue is None")
            return

        if self.logging_queue:
            self.logging_queue.put([str(time.time()), "QUIT"])
        if self.logging_thread:
            self.logging_thread.join()
        del self.logging_thread
        self.logging_thread = None
        del self.logging_queue
        self.logging_queue = None

        # Write to file
        loggingWriteErrorHistory(self)
        Domoticz.Log("Logging Thread shutdown")

    def loggingCleaningErrorHistory(self):
        if len(self.LogErrorHistory) > 1:
            idx = list(self.LogErrorHistory.keys())[1]
            if "Time" in self.LogErrorHistory[str(idx)]:
                if time.time() - self.LogErrorHistory[str(idx)]["Time"] > 1360800:  # 7 days for old structure
                    self.LogErrorHistory.pop(idx)
            elif len(self.LogErrorHistory[str(idx)]) > 4:
                idx2 = list(self.LogErrorHistory[str(idx)].keys())[4]
                if "Time" in self.LogErrorHistory[str(idx)][str(idx2)] and (
                    time.time() - self.LogErrorHistory[str(idx)][str(idx2)]["Time"] > 1360800
                ):  # 7 days
                    self.LogErrorHistory[idx].pop(idx2)
            else:
                self.LogErrorHistory.pop(idx)
        if len(self.LogErrorHistory) == 1:
            self.LogErrorHistory.clear()

    def loggingClearErrorHistory(self):
        self.LogErrorHistory.clear()
        self._newError = False

    def logging(self, module, logType, message, nwkid=None, context=None):
        if (
            "debugTransportZigpyZNP" in self.pluginconf.pluginConf
            and self.pluginconf.pluginConf["debugTransportZigpyZNP"]
        ):
            if not self.zigpy_log_znp:
                self.zigpy_log_znp = True
                self.zigpy_login()
        elif self.zigpy_log_znp:
            self.zigpy_log_znp = False
            self.zigpy_login()

        if (
            "debugTransportZigpyZigate" in self.pluginconf.pluginConf
            and self.pluginconf.pluginConf["debugTransportZigpyZigate"]
        ):
            if not self.zigpy_log_zigate:
                self.zigpy_log_zigate = True
                self.zigpy_login()
        elif self.zigpy_log_zigate:
            self.zigpy_log_zigate = False
            self.zigpy_login()

        try:
            thread_id = threading.current_thread().native_id
            # native_id exists since python 3.8.
        except AttributeError:
            thread_id = 0

        if self.logging_thread and self.logging_queue:
            logging_tuple = [
                str(time.time()),
                str(threading.current_thread().name),
                str(thread_id),
                str(module),
                str(logType),
                str(message),
                str(nwkid),
                str(context),
            ]
            self.logging_queue.put(logging_tuple)
        else:
            Domoticz.Log("%s" % message)


def _loggingStatus(self, thread_name, message):

    if self.pluginconf.pluginConf["enablePluginLogging"]:
        logging.info(" [%17s] " % thread_name + message)
        Domoticz.Status(message)

    elif self.pluginconf.pluginConf["logThreadName"]:
        Domoticz.Status(" [%17s] " % thread_name + message)
    else:
        Domoticz.Status(message)


def _loggingLog(self, thread_name, message):

    if not self.pluginconf.pluginConf["enablePluginLogging"]:
        if self.pluginconf.pluginConf["logThreadName"]:
            Domoticz.Log(" [%17s] " % thread_name + message)
        else:
            Domoticz.Log(message)
    else:
        logging.info(" [%17s] " % thread_name + message)


def _loggingDebug(self, thread_name, message):
    if not self.pluginconf.pluginConf["enablePluginLogging"]:
        if self.pluginconf.pluginConf["logThreadName"]:
            Domoticz.Log(" [%17s] " % thread_name + message)
        else:
            Domoticz.Log(message)
    else:
        logging.debug(" [%17s] " % thread_name + message)


def _logginfilter(self, thread_name, message, nwkid):

    if nwkid is None:
        _loggingDebug(self, thread_name, message)
    elif nwkid:
        nwkid = nwkid.lower()
        _debugMatchId = self.pluginconf.pluginConf["debugMatchId"].lower().split(",")
        if ("ffff" in _debugMatchId) or (nwkid in _debugMatchId) or (nwkid == "ffff"):
            _loggingDebug(self, thread_name, message)


def loggingDirector(self, thread_name, logType, message):
    if logType == "Log":
        _loggingLog(self, thread_name, message)
    elif logType == "Status":
        _loggingStatus(self, thread_name, message)


def loggingError(self, thread_name, module, message, nwkid, context):
    Domoticz.Error(message)
    self._newError = True

    # Log to file
    if self.pluginconf.pluginConf["enablePluginLogging"]:
        logging.error(" [%17s] " % thread_name + message)

    # Log empty
    if not self.LogErrorHistory or "LastLog" not in self.LogErrorHistory:
        self.LogErrorHistory["LastLog"] = 0
        self.LogErrorHistory["0"] = {
            "LastLog": 0,
            "StartTime": self._startTime,
            "FirmwareVersion": self.FirmwareVersion,
            "FirmwareMajorVersion": self.FirmwareMajorVersion,
            "PluginVersion": self.PluginVersion,
        }

        self.LogErrorHistory["0"]["0"] = loggingBuildContext(self, thread_name, module, message, nwkid, context)
        loggingWriteErrorHistory(self)
        return  # log created, leaving

    # check if existing log contains plugin launch time
    if "StartTime" in self.LogErrorHistory[str(self.LogErrorHistory["LastLog"])]:
        index = self.LogErrorHistory["LastLog"]
        # check if launch time if the same, otherwise, create a new entry
        if self.LogErrorHistory[str(index)]["StartTime"] != self._startTime:
            index += 1
    else:  # compatibility with older version
        index = self.LogErrorHistory["LastLog"] + 1

    # check if it's a new entry
    if str(index) not in self.LogErrorHistory:
        self.LogErrorHistory["LastLog"] += 1
        self.LogErrorHistory[str(index)] = {"LastLog": 0}
        self.LogErrorHistory[str(index)]["StartTime"] = self._startTime
        self.LogErrorHistory[str(index)]["FirmwareVersion"] = self.FirmwareVersion
        self.LogErrorHistory[str(index)]["FirmwareMajorVersion"] = self.FirmwareMajorVersion
        self.LogErrorHistory[str(index)]["PluginVersion"] = (self.PluginVersion,)
        self.LogErrorHistory[str(index)]["0"] = loggingBuildContext(self, thread_name, module, message, nwkid, context)
    else:
        self.LogErrorHistory[str(index)]["LastLog"] += 1
        self.LogErrorHistory[str(index)][str(self.LogErrorHistory[str(index)]["LastLog"])] = loggingBuildContext(
            self, thread_name, module, message, nwkid, context
        )

        if len(self.LogErrorHistory[str(index)]) > 20 + 4:  # log full for this launch time, remove oldest
            idx = list(self.LogErrorHistory[str(index)].keys())[4]
            self.LogErrorHistory[str(index)].pop(idx)

    if len(self.LogErrorHistory) > 5 + 1:  # log full, remove oldest
        idx = list(self.LogErrorHistory.keys())[1]
        self.LogErrorHistory.pop(idx)

    loggingWriteErrorHistory(self)


def loggingBuildContext(self, thread_name, module, message, nwkid, context):

    if not self.PluginHealth:
        _txt = "Not Started"
    if "Txt" not in self.PluginHealth:
        _txt = "Not Started"
    else:
        _txt = self.PluginHealth["Txt"]
    _context = {
        "Time": int(time.time()),
        "Module": module,
        "nwkid": nwkid,
        "PluginHealth": _txt,
        "message": message,
        "PermitToJoin": self.permitTojoin,
        "Thread": thread_name,
    }
    if nwkid and nwkid in self.ListOfDevices:
        _context["DeviceInfos"] = dict(self.ListOfDevices[nwkid])
    if context is not None:
        if isinstance(context, dict):
            _context["context"] = context.copy()
        elif isinstance(context, (str, int)):
            _context["context"] = str(context)
    return _context


def loggingWriteErrorHistory(self):
    jsonLogHistory = self.pluginconf.pluginConf["pluginLogs"] + "/" + LOG_ERROR_HISTORY
    with open(jsonLogHistory, "w", encoding="utf-8") as json_file:
        try:
            json.dump(dict(self.LogErrorHistory), json_file)
            json_file.write("\n")
        except Exception as e:
            Domoticz.Error("Hops ! Unable to write LogErrorHistory error: %s log: %s" % (e, self.LogErrorHistory))


def start_logging_thread(self):
    Domoticz.Log("start_logging_thread")
    if self.logging_thread:
        Domoticz.Error("start_logging_thread - Looks like logging_thread already started !!!")
        return

    self.logging_queue = PriorityQueue()
    self.logging_thread = threading.Thread(
        name="ZiGateLogging_%s" % self.HardwareID, target=logging_thread, args=(self,)
    )
    self.logging_thread.start()


def logging_thread(self):

    Domoticz.Log("logging_thread - listening")
    while self.running:
        # We loop until self.running is set to False,
        # which indicate plugin shutdown
        logging_tuple = self.logging_queue.get()
        if len(logging_tuple) == 2:
            timing, command = logging_tuple
            if command == "QUIT":
                Domoticz.Log("logging_thread Exit requested")
                break
        elif len(logging_tuple) == 8:
            (
                timing,
                thread_name,
                thread_id,
                module,
                logType,
                message,
                nwkid,
                context,
            ) = logging_tuple
            try:
                context = eval(context)
            except Exception as e:
                Domoticz.Error("Something went wrong and catch: context: %s" % str(context))
                Domoticz.Error("      logging_thread unexpected tuple %s" % (str(logging_tuple)))
                Domoticz.Error("      Error %s" % (str(e)))
                return
            if logType == "Error":
                loggingError(self, thread_name, module, message, nwkid, context)
            elif logType == "Debug":
                # thread filter
                threadFilter = [
                    x for x in self.threadLogConfig if self.pluginconf.pluginConf["debugThread" + self.threadLogConfig[x]] == 1
                ]
                if threadFilter:
                    if thread_name not in threadFilter:
                        continue
                thread_name=thread_name + " " + thread_id
                pluginConfModule = "debug" + str(module)
                if pluginConfModule in self.pluginconf.pluginConf:
                    if self.pluginconf.pluginConf[pluginConfModule]:
                        _logginfilter(self, thread_name, message, nwkid)
                else:
                    Domoticz.Error("%s debug module unknown %s" % (pluginConfModule, module))
                    _loggingDebug(self, thread_name, message)
            else:
                thread_name=thread_name + " " + thread_id
                loggingDirector(self, thread_name, logType, message)
        else:
            Domoticz.Error("logging_thread unexpected tuple %s" % (str(logging_tuple)))
    Domoticz.Log("logging_thread - ended")



def zigpy_loging_mode(mode):
    if mode == "debug":
        requests_logger = logging.getLogger("zigpy")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("zigpy.zdo")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("zigpy.zcl")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("zigpy.profiles")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("zigpy.quirks")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("zigpy.ota")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("zigpy.appdb_schemas")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("zigpy.backups")
        requests_logger.setLevel(logging.DEBUG)

    else:
        requests_logger = logging.getLogger("zigpy")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("zigpy.zdo")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("zigpy.zcl")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("zigpy.profiles")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("zigpy.quirks")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("zigpy.ota")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("zigpy.appdb_schemas")
        requests_logger.setLevel(logging.WARNING)
        
def zigpy_logging_znp(mode):
    if mode == "debug":
        requests_logger = logging.getLogger("zigpy_znp")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("Classes.ZigpyTransport.AppZnp")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("Classes.ZigpyTransport.AppGeneric")
        requests_logger.setLevel(logging.DEBUG)
    else:
        requests_logger = logging.getLogger("zigpy_znp")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("Classes.ZigpyTransport.AppZnp")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("Classes.ZigpyTransport.AppGeneric")
        requests_logger.setLevel(logging.WARNING)


def zigpy_logging_ezsp(mode):   
    if mode == "debug":    
        requests_logger = logging.getLogger("bellows")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("bellows.zigbee")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("bellows.uart")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("Classes.ZigpyTransport.AppBellows")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("Classes.ZigpyTransport.AppGeneric")
        requests_logger.setLevel(logging.DEBUG)

    else:
        requests_logger = logging.getLogger("bellows")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("bellows.zigbee")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("bellows.uart")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("Classes.ZigpyTransport.AppBellows")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("Classes.ZigpyTransport.AppGeneric")
        requests_logger.setLevel(logging.WARNING)


def zigpy_logging_zigate(mode):
    if mode == "debug":        
        requests_logger = logging.getLogger("zigpy_zigate")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("Classes.ZigpyTransport.AppZigate")
        requests_logger.setLevel(logging.DEBUG)
    else:
        requests_logger = logging.getLogger("zigpy_zigate")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("Classes.ZigpyTransport.AppZigate")
        requests_logger.setLevel(logging.WARNING)
        
        
def zigpy_logging_deconz(mode):
    if mode == "debug":        
        requests_logger = logging.getLogger("zigpy_deconz")
        requests_logger.setLevel(logging.DEBUG)
        requests_logger = logging.getLogger("Classes.ZigpyTransport.AppDeconz")
        requests_logger.setLevel(logging.DEBUG)
    else:
        requests_logger = logging.getLogger("zigpy_deconz")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("Classes.ZigpyTransport.AppDeconz")
        requests_logger.setLevel(logging.WARNING)
        requests_logger = logging.getLogger("Classes.ZigpyTransport.AppGeneric")
        requests_logger.setLevel(logging.WARNING)

