#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: badz & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license


import json
import time
from pathlib import Path

from Modules.domoticzAbstractLayer import domoticz_log_api, domoticz_status_api

class TransportStatistics:
    def __init__(self, pluginconf, log, zigbee_communication):
        self._pdmLoads = 0  # count the number of PDM Loads ( should be 1 max)
        self._crcErrors = 0  # count of crc errors
        self._frameErrors = 0  # count of frames error
        self._APSFailure = 0  # Count APS Failure
        self._APSAck = 0  # Firmware 3.1b 0x8011 status 00
        self._APSNck = 0  # Firmware 3.1b 0x8011 status not 00
        self._sent = 0  # count of sent messages
        self._received = 0  # count of received messages
        self._ack = 0  # count number of 0x8000
        self._ackKO = 0  # count Ack with status != 0
        self._data = 0  # count data messages
        self._TOstatus = 0  # count the number of TO trigger while waiting for status
        self._TOdata = 0  # count the number of TO triggered while waiting for data
        self._clusterOK = 0
        self._clusterKO = 0
        self._reTx = 0
        self._Load = 0
        self._MaxLoad = 0
        self._MaxaPdu = 0
        self._MaxnPdu = 0
        self._serialInWaiting = 0
        self._serialOutWaiting = 0
        self._maxTiming8000 = self._cumulTiming8000 = self._cntTiming8000 = self._averageTiming8000 = 0
        self._maxTiming8011 = self._cumulTiming8011 = self._cntTiming8011 = self._averageTiming8011 = 0
        self._maxTiming8012 = self._cumulTiming8012 = self._cntTiming8012 = self._averageTiming8012 = 0
        self._maxRxProcesses = self._cumulRxProcess = self._cntRxProcess = self._averageRxProcess = 0
        self._max_reading_thread_timing = self._cumul_reading_thread_timing = self._cnt_reading_thread_timing = self._average_reading_thread_timing = 0
        self._max_reading_zigpy_timing = self._cumul_reading_zigpy_timing = self._cnt_reading_zigpy_timing = self._average_reading_zigpy_timing = 0
        self._start = int(time.time())
        self.TrendStats = []
        self.pluginconf = pluginconf
        self.log = log
        self.zigbee_communication = zigbee_communication

    # Statistics methods
    def starttime(self):
        return self._start


    def pdm_loaded(self):
        self._pdmLoads += 1


    def get_pdm_loaded(self):
        return self._pdmLoads


    def add_timing_zigpy(self, timing):
        self._cumul_reading_zigpy_timing += timing
        self._cnt_reading_zigpy_timing += 1
        self._average_reading_zigpy_timing = int((self._cumul_reading_zigpy_timing / self._cnt_reading_zigpy_timing))
        if timing > self._max_reading_zigpy_timing:
            self._max_reading_zigpy_timing = timing
            self.log.logging("TransportZigpy", "Log", f"ZigpyThread Max: {self._max_reading_zigpy_timing} ms with an average of: {self._average_reading_zigpy_timing} ms")

        
    def add_timing_thread(self, timing):
        self._cumul_reading_thread_timing += timing
        self._cnt_reading_thread_timing += 1
        self._average_reading_thread_timing = int((self._cumul_reading_thread_timing / self._cnt_reading_thread_timing))
        if timing > self._max_reading_thread_timing:
            self._max_reading_thread_timing = timing
            domoticz_log_api(
                "Coordinator Thread Serial Read Max: %s ms with an of average: %s ms"
                % (self._max_reading_thread_timing, self._average_reading_thread_timing)
            )


    def add_timing8000(self, timing):

        self._cumulTiming8000 += timing
        self._cntTiming8000 += 1
        self._averageTiming8000 = int((self._cumulTiming8000 / self._cntTiming8000))
        if timing > self._maxTiming8000:
            self._maxTiming8000 = timing
            domoticz_log_api(
                "Coordinator command round trip 0x8000 Max: %s ms with an of average: %s ms"
                % (self._maxTiming8000, self._averageTiming8000)
            )


    def add_timing8011(self, timing):

        self._cumulTiming8011 += timing
        self._cntTiming8011 += 1
        self._averageTiming8011 = int((self._cumulTiming8011 / self._cntTiming8011))
        if timing > self._maxTiming8011:
            self._maxTiming8011 = timing
            domoticz_log_api(
                "Coordinator command round trip 0x8011 Max: %s ms with an of average: %s ms"
                % (self._maxTiming8011, self._averageTiming8011)
            )


    def add_timing8012(self, timing):

        self._cumulTiming8012 += timing
        self._cntTiming8012 += 1
        self._averageTiming8012 = int((self._cumulTiming8012 / self._cntTiming8012))
        if timing > self._maxTiming8012:
            self._maxTiming8012 = timing
            domoticz_log_api(
                "Coordinator command round trip 0x8012 Max: %s ms with an of average: %s ms"
                % (self._maxTiming8012, self._averageTiming8012)
            )


    def add_rxTiming(self, timing):

        self._cumulRxProcess += timing
        self._cntRxProcess += 1
        self._averageRxProcess = int((self._cumulRxProcess / self._cntRxProcess))
        if timing > self._maxRxProcesses:
            self._maxRxProcesses = timing
            domoticz_log_api(
                "Coordinator receive message processing time Max: %s ms with an of average: %s ms"
                % (self._maxRxProcesses, self._averageRxProcess)
            )


    def addPointforTrendStats(self, TimeStamp):
        """
        Adds a point to the trend statistics table, tracking Rx, Tx, and Load metrics.

        Args:
            TimeStamp (int): The timestamp for the data point.

        Note:
            The table is capped at MAX_TREND_STAT_TABLE entries, with the oldest entry removed when the limit is reached.
        """
        MAX_TREND_STAT_TABLE = 120

        try:
            # Calculate uptime and transmission rates
            uptime = int(time.time() - self._start)
            if uptime <= 0:
                self.log.logging("Stats", "Error", "Invalid uptime calculation: uptime must be greater than 0.")
                return

            Rxps = round(self._received / uptime, 2)
            Txps = round(self._sent / uptime, 2)

            # Maintain the size of the TrendStats table
            if len(self.TrendStats) >= MAX_TREND_STAT_TABLE:
                self.TrendStats.pop(0)

            # Append the new data point
            self.TrendStats.append({
                "_TS": TimeStamp,
                "Rxps": Rxps,
                "Txps": Txps,
                "Load": self._Load
            })

        except Exception as e:
            self.log.logging("Stats", "Error", f"Failed to add point to trend stats: {e}")


    def reTx(self):
        """ return the number of crc Errors """
        return self._reTx


    def crcErrors(self):
        " return the number of crc Errors "
        return self._crcErrors


    def frameErrors(self):
        " return the number of frame errors"
        return self._frameErrors


    def sent(self):
        " return he number of sent messages"
        return self._sent


    def received(self):
        " return the number of received messages"
        return self._received


    def ackReceived(self):
        return self._ack


    def ackKOReceived(self):
        return self._ackKO


    def dataReceived(self):
        return self._data


    def TOstatus(self):
        return self._TOstatus


    def TOdata(self):
        return self._TOdata


    def clusterOK(self):
        return self._clusterOK


    def clusterKO(self):
        return self._clusterKO


    def APSFailure(self):
        return self._APSFailure


    def APSAck(self):
        return self._APSAck


    def APSNck(self):
        return self._APSNck


    def printSummary(self):
        """
        Prints a summary of plugin statistics, including transmission,
        reception, and timing metrics.
        """
        if self.received() == 0 or self.sent() == 0:
            return

        def print_with_percentage(label, value, total):
            percentage = round((value / total) * 100, 2)
            domoticz_status_api(f"{label}: {value} ({percentage}%)")

        domoticz_status_api("Plugin statistics")
        domoticz_status_api("  Messages Sent:")
        domoticz_status_api(f"     Max Load (Queue) : {self._MaxLoad}")
        domoticz_status_api(f"     TX commands      : {self.sent()}")

        print_with_percentage("     TX failed", self.ackKOReceived(), self.sent())

        if self.zigbee_communication == "native":
            print_with_percentage("     TX timeout", self.TOstatus(), self.sent())

        print_with_percentage("     TX data timeout", self.TOdata(), self.sent())
        print_with_percentage("     TX reTransmit", self.reTx(), self.sent())

        if self.zigbee_communication == "native":
            print_with_percentage("     TX APS Failure", self.APSFailure(), self.sent())

        print_with_percentage("     TX APS Ack", self.APSAck(), self.sent())
        print_with_percentage("     TX APS Nck", self.APSNck(), self.sent())

        domoticz_status_api("  Messages Received:")
        domoticz_status_api(f"     RX frame         : {self.received()}")
        domoticz_status_api(f"     RX clusters      : {self.clusterOK()}")
        domoticz_status_api(f"     RX clusters KO   : {self.clusterKO()}")

        if self.zigbee_communication == "native":
            domoticz_status_api("  Coordinator reacting time on Tx (if ReactTime enabled)")
            domoticz_status_api(f"     Max              : {self._maxTiming8000} sec")
            domoticz_status_api(f"     Average          : {self._averageTiming8000} sec")
        else:
            domoticz_status_api("  Plugin reacting time on Tx (if ReactTime enabled)")
            domoticz_status_api(f"     Max              : {self._max_reading_zigpy_timing} ms")
            domoticz_status_api(f"     Average          : {self._average_reading_zigpy_timing} ms")

        domoticz_status_api("  Plugin processing time on Rx (if ReactTime enabled)")
        timing_unit = "sec" if self.zigbee_communication == "native" else "ms"
        domoticz_status_api(f"     Max              : {self._maxRxProcesses} {timing_unit}")
        domoticz_status_api(f"     Average          : {self._averageRxProcess} {timing_unit}")

        days, hours, mins, secs = _plugin_uptime(self.starttime())
        domoticz_status_api("  Operating time      : %d Days %d Hours %d Mins %d Secs" % (days, hours, mins, secs))


    def writeReport(self):
        """
        Write transport statistics to a JSON file.
        """
        # Collect the current timestamp
        current_time = int(time.time())

        # Prepare stats dictionary
        stats = {
            current_time: {
                "crcErrors": self._crcErrors,
                "frameErrors": self._frameErrors,
                "sent": self._sent,
                "received": self._received,
                "APS Ack": self._APSAck,
                "APS Nck": self._APSNck,
                "ack": self._ack,
                "ackKO": self._ackKO,
                "data": self._data,
                "TOstatus": self._TOstatus,
                "TOdata": self._TOdata,
                "clusterOK": self._clusterOK,
                "clusterKO": self._clusterKO,
                "reTx": self._reTx,
                "MaxLoad": self._MaxLoad,
                "start": self._start,
                "stop": current_time,
            }
        }

        # Construct the JSON file path
        json_filename = Path(self.pluginconf.pluginConf["pluginReports"]) / "Transport-stats.json"

        try:
            # Append statistics to the JSON file
            with open(json_filename, "a") as json_file:  # Use 'a' for appending
                json_file.write("\n")
                json.dump(stats, json_file, indent=4)  # Add indent for better readability
        except Exception as e:
            self.log.logging("Plugin", "Error", f"Failed to write transport stats: {e}")


def _plugin_uptime(starttime):
    """
    Calculates the uptime since the given start time.

    Args:
        starttime (int): The start time in seconds since the epoch.

    Returns:
        tuple: Uptime in days, hours, minutes, and seconds.
    """
    t1 = int(time.time())
    _duration = t1 - starttime

    _days = _duration // (24 * 3600)
    _duration %= 24 * 3600
    _hours = _duration // 3600
    _duration %= 3600
    _mins = _duration // 60
    _secs = _duration % 60

    return _days, _hours, _mins, _secs
