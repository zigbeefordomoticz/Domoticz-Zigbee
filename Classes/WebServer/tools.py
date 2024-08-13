#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

from Modules.domoticzAbstractLayer import (domoticz_error_api,
                                           domoticz_log_api,
                                           domoticz_status_api)

MAX_BLOCK_SIZE = 8 * 1024  # Chunk size
DEBUG_HTTP = False


def keepConnectionAlive(self):

    self.heartbeats += 1


def DumpHTTPResponseToLog(httpDict):

    if not DEBUG_HTTP:
        return
    if isinstance(httpDict, dict):
        domoticz_log_api("HTTP Details (" + str(len(httpDict)) + "):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                domoticz_log_api("--->'" + x + " (" + str(len(httpDict[x])) + "):")
                for y in httpDict[x]:
                    domoticz_log_api("------->'" + y + "':'" + str(httpDict[x][y]) + "'")
            else:
                if x == "Data":
                    domoticz_log_api("--->'%s':'%.40s'" % (x, str(httpDict[x])))
                else:
                    domoticz_log_api("--->'" + x + "':'" + str(httpDict[x]) + "'")
