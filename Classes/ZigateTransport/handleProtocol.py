# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import binascii
import time
from datetime import datetime

from Classes.ZigateTransport.compatibilityMode import decode8011_31c
from Classes.ZigateTransport.decode8000 import decode8000
from Classes.ZigateTransport.decode8011 import decode8011
from Classes.ZigateTransport.decode8012 import decode8012_8702
from Classes.ZigateTransport.instrumentation import time_spent_process_frame
from Classes.ZigateTransport.tools import (CMD_PDM_ON_HOST, STANDALONE_MESSAGE,
                                           get_isqn_from_ListOfCommands,
                                           release_command)
from Modules.errorCodes import ZCL_EXTENDED_ERROR_CODES
from Modules.zigateConsts import (MAX_SIMULTANEOUS_ZIGATE_COMMANDS,
                                  ZIGATE_COMMANDS)
from Zigbee.decode8002 import decode8002_and_process


@time_spent_process_frame()
def process_frame(self, decoded_frame):

    # self.logging_proto( 'Debug', "process_frame - receive frame: %s" %decoded_frame)

    # Sanity Check
    if decoded_frame == "" or decoded_frame is None or len(decoded_frame) < 12:
        return

    i_sqn = None
    MsgType = decoded_frame[2:6]
    MsgLength = decoded_frame[6:10]
    MsgCRC = decoded_frame[10:12]

    # self.logging_proto( 'Debug', "process_frame - MsgType: %s MsgLenght: %s MsgCrc: %s" %( MsgType, MsgLength, MsgCRC))


    # Payload
    MsgData = None
    if len(decoded_frame) < 18:
        return

    MsgData = decoded_frame[12 : len(decoded_frame) - 4]
    # self.logging_proto( 'Log', "process_frame -  MsgType: %s MsgData %s" % (MsgType, MsgData))

    if MsgType == "8001":
        # Async message
        NXP_log_message(self, decoded_frame)
        return

    if MsgType == "0302":  # PDM loaded, ZiGate ready (after an internal error, but also after an ErasePDM)
        self.logging_proto("Status", "ZiGate PDM loaded")
        if self.statistics.get_pdm_loaded() > 0:
            self.logging_proto( "Error",
                "Detected a PDM load, result of a ZiGate reset of (crash): #%s" % self.statistics.get_pdm_loaded(),
            )
        self.statistics.pdm_loaded()

        for x in list(self.ListOfCommands):
            if self.ListOfCommands[x]["cmd"] == "0012":
                release_command(self, x)
        # This could be also linked to a Reboot of the ZiGate firmware. In such case, it might be important to release Semaphore

        self.forwarder_queue.put(decoded_frame)
        return

    if MsgType in CMD_PDM_ON_HOST:
        # Manage PDM on Host commands
        return

    if MsgType in ("8035",):
        # Internal ZiGate Message, just drop
        return

    if MsgType == "9999":
        # Async message
        NXP_Extended_Error_Code(self, MsgData)
        return

    if MsgType in ("9998", "9997", "9996"):
        # Async message
        Akila_debuging(self, MsgType, MsgData)
        return

    if MsgType == "8000":  # Command Ack
        decode8000(self, decoded_frame)
        self.forwarder_queue.put(decoded_frame)
        return

    if MsgType in ("8012", "8702"):  # Transmission Akc for no-ack commands
        if self.firmware_with_8012:
            decode8012_8702(self, decoded_frame)
        return

    if MsgType == "8011":  # Command Ack (from target device)
        if self.firmware_with_aps_sqn:
            decode8011(self, decoded_frame)
        self.forwarder_queue.put(decoded_frame)
        return

    if MsgType == "8701":
        # Async message
        # Route Discovery, we don't handle it
        return

    if MsgType == "8002" and MsgData:
        # Data indication
        self.statistics._data += 1
        self.forwarder_queue.put(decode8002_and_process(self, decoded_frame))
        return

    #if ( self.pluginconf.pluginConf["ControllerInRawMode"] and MsgType 
    #    not in ( "004D", "8003", "8004", "8005", "8006", "8007", "8008", "8009", "8010", "8014", "8015", "8017", "8017", "8806", "8807", "8024", "8048") 
    #):
    #    self.logging_proto("Debug", "==> RawMode: droping packet %s %s" %(MsgType, decoded_frame))
    #    return

    if self.pluginconf.pluginConf["ControllerInHybridMode"] and MsgType in ( "8100", "8102", ):
        self.logging_proto("Debug", "==> Skiping message type %s as we are in HybridMode" %MsgType)
        return

    if self.firmware_compatibility_mode and MsgType in ("8102", "8100", "8110"):
        self.statistics._data += 1
        decode8011_31c(self, MsgType, decoded_frame)
        self.forwarder_queue.put(decoded_frame)
        return

    # Forward the message to plugin for further processing
    self.statistics._data += 1
    self.forwarder_queue.put(decoded_frame)


# Extended Error Code:
def NXP_Extended_Error_Code(self, MsgData):

    if not self.pluginconf.pluginConf["NXPExtendedErrorCode"]:
        return

    if MsgData == self.previousExtendedErrorCode and self.previousEEC_time + 60 > time.time():
        # Avoid to log multiple time the same extended erro
        return
    self.previousExtendedErrorCode = MsgData
    self.previousEEC_time = time.time()

    StatusMsg = ""
    if MsgData in ZCL_EXTENDED_ERROR_CODES:
        StatusMsg = ZCL_EXTENDED_ERROR_CODES[MsgData]

    context = {
        "Error code": "TRANS-PROTO-01",
        "ExtendedErrorCode": MsgData,
        "ExtendedError": StatusMsg,
        "nPDU": self.npdu,
        "aPDU": self.apdu,
    }
    if self.firmware_with_8012:
        # We have a 31e firmware or above. We are not expecting extensive Extended Error code, so they will be logged
        self.logging_proto("Error", "NXP_Extended_Error_Code - Extended Error Code: [%s] %s" % (MsgData, StatusMsg), _context=context)
    else:
        self.logging_proto(
            "Log",
            "NXP_Extended_Error_Code - Extended Error Code: [%s] %s nPDU:%s aPDU: %s" % (MsgData, StatusMsg, self.npdu, self.apdu),
        )


def NXP_log_message(self, decoded_frame):  # Reception log Level

    LOG_FILE = "ZiGate"

    # self.logging_proto( 'Debug' , "8001 - %s" %decoded_frame )
    MsgData = decoded_frame[12 : len(decoded_frame) - 2]
    MsgLogLvl = MsgData[0:2]
    try:
        log_message = binascii.unhexlify(MsgData[2:]).decode("utf-8")
    except:
        log_message = binascii.unhexlify(MsgData[2:]).decode("utf-8", errors="ignore")
        log_message = log_message.replace("\x00", "")

    logfilename = self.pluginconf.pluginConf["pluginLogs"] + "/" + LOG_FILE + "_" + "%02d" % self.hardwareid + "_" + ".log"
    try:
        with open(logfilename, "at", encoding="utf-8") as file:
            try:
                if self.newline_required:
                    file.write("\n%s %s" % (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]), MsgLogLvl))
                self.newline_required = False

                file.write(" " + log_message)

                if decoded_frame[len(decoded_frame) - 4 : len(decoded_frame) - 2] == "20":
                    self.newline_required = True

            except IOError:
                self.logging_proto("Error", "Error while writing to ZiGate log file %s" % logfilename)
    except IOError:
        self.logging_proto("Error", "Error while Opening ZiGate log file %s" % logfilename)


def Akila_debuging(self, MsgType, MsgData):
    self.logging_proto("Log", "Firmware debug ==> %s - Ep: %s Event: %s" % (MsgType, MsgData[0:2], MsgData[2:]))
