#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

import Domoticz
import json
from time import time


class TransportStatistics:
    def __init__(self, pluginconf):
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
        self._max_reading_thread_timing = self._cumul_reading_thread_timing  = self._cnt_reading_thread_timing = self._average_reading_thread_timing = 0
        self._max_reading_zigpy_timing = self._cumul_reading_zigpy_timing  = self._cnt_reading_zigpy_timing = self._average_reading_zigpy_timing = 0
        self._start = int(time())
        self.TrendStats = []
        self.pluginconf = pluginconf

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
            Domoticz.Log(
                "Zigate Thread Serial Read Max: %s ms with an of average: %s ms"
                % (self._max_reading_zigpy_timing, self._average_reading_zigpy_timing)
            )
        Domoticz.Log(
            "Zigate Thread Serial Read Max: %s ms with an of average: %s ms"
            % (self._max_reading_zigpy_timing, self._average_reading_zigpy_timing)
        )

        
    def add_timing_thread(self, timing):
        self._cumul_reading_thread_timing += timing
        self._cnt_reading_thread_timing += 1
        self._average_reading_thread_timing = int((self._cumul_reading_thread_timing / self._cnt_reading_thread_timing))
        if timing > self._max_reading_thread_timing:
            self._max_reading_thread_timing = timing
            Domoticz.Log(
                "Zigate Thread Serial Read Max: %s ms with an of average: %s ms"
                % (self._max_reading_thread_timing, self._average_reading_thread_timing)
            )

    def add_timing8000(self, timing):

        self._cumulTiming8000 += timing
        self._cntTiming8000 += 1
        self._averageTiming8000 = int((self._cumulTiming8000 / self._cntTiming8000))
        if timing > self._maxTiming8000:
            self._maxTiming8000 = timing
            Domoticz.Log(
                "Zigate command round trip 0x8000 Max: %s ms with an of average: %s ms"
                % (self._maxTiming8000, self._averageTiming8000)
            )

    def add_timing8011(self, timing):

        self._cumulTiming8011 += timing
        self._cntTiming8011 += 1
        self._averageTiming8011 = int((self._cumulTiming8011 / self._cntTiming8011))
        if timing > self._maxTiming8011:
            self._maxTiming8011 = timing
            Domoticz.Log(
                "Zigate command round trip 0x8011 Max: %s ms with an of average: %s ms"
                % (self._maxTiming8011, self._averageTiming8011)
            )

    def add_timing8012(self, timing):

        self._cumulTiming8012 += timing
        self._cntTiming8012 += 1
        self._averageTiming8012 = int((self._cumulTiming8012 / self._cntTiming8012))
        if timing > self._maxTiming8012:
            self._maxTiming8012 = timing
            Domoticz.Log(
                "Zigate command round trip 0x8012 Max: %s ms with an of average: %s ms"
                % (self._maxTiming8012, self._averageTiming8012)
            )

    def add_rxTiming(self, timing):

        self._cumulRxProcess += timing
        self._cntRxProcess += 1
        self._averageRxProcess = int((self._cumulRxProcess / self._cntRxProcess))
        if timing > self._maxRxProcesses:
            self._maxRxProcesses = timing
            Domoticz.Log(
                "Zigate receive message processing time Max: %s ms with an of average: %s ms"
                % (self._maxRxProcesses, self._averageRxProcess)
            )

    def addPointforTrendStats(self, TimeStamp):

        MAX_TREND_STAT_TABLE = 120

        uptime = int(time() - self._start)
        Rxps = round(self._received / uptime, 2)
        Txps = round(self._sent / uptime, 2)
        if len(self.TrendStats) >= MAX_TREND_STAT_TABLE:
            del self.TrendStats[0]
        self.TrendStats.append({"_TS": TimeStamp, "Rxps": Rxps, "Txps": Txps, "Load": self._Load})

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
        if self.received() == 0:
            return
        if self.sent() == 0 or self.received() == 0:
            return
        Domoticz.Status("Statistics on message")
        Domoticz.Status("   PDM load(s)      : %s" % self._pdmLoads)
        Domoticz.Status("ZiGate reacting time")
        Domoticz.Status("   Max              : %s sec" % (self._maxTiming8000))
        Domoticz.Status("   Average          : %s sec" % (self._averageTiming8000))
        Domoticz.Status("ZiGate processing time on Rx")
        Domoticz.Status("   Max              : %s sec" % (self._maxRxProcesses))
        Domoticz.Status("   Average          : %s sec" % (self._averageRxProcess))
        Domoticz.Status("Sent:")
        Domoticz.Status("   TX commands      : %s" % (self.sent()))
        Domoticz.Status("   Max Load (Queue) : %s " % (self._MaxLoad))
        Domoticz.Status("   Max aPDU (Queue) : %s " % (self._MaxaPdu))
        Domoticz.Status("   Max nPDU (Queue) : %s " % (self._MaxnPdu))
        Domoticz.Status(
            "   TX failed        : %s (%s" % (self.ackKOReceived(), round((self.ackKOReceived() / self.sent()) * 10, 2))
            + "%)"
        )
        Domoticz.Status(
            "   TX timeout       : %s (%s" % (self.TOstatus(), round((self.TOstatus() / self.sent()) * 100, 2)) + "%)"
        )
        Domoticz.Status(
            "   TX data timeout  : %s (%s" % (self.TOdata(), round((self.TOdata() / self.sent()) * 100, 2)) + "%)"
        )
        Domoticz.Status(
            "   TX reTransmit    : %s (%s" % (self.reTx(), round((self.reTx() / self.sent()) * 100, 2)) + "%)"
        )
        Domoticz.Status(
            "   TX APS Failure   : %s (%s" % (self.APSFailure(), round((self.APSFailure() / self.sent()) * 100, 2))
            + "%)"
        )
        Domoticz.Status(
            "   TX APS Ack       : %s (%s" % (self.APSAck(), round((self.APSAck() / self.sent()) * 100, 2)) + "%)"
        )
        Domoticz.Status(
            "   TX APS Nck       : %s (%s" % (self.APSNck(), round((self.APSNck() / self.sent()) * 100, 2)) + "%)"
        )
        Domoticz.Status("Received:")
        Domoticz.Status("   RX frame         : %s" % (self.received()))
        Domoticz.Status(
            "   RX crc errors    : %s (%s" % (self.crcErrors(), round((self.crcErrors() / self.received()) * 100, 2))
            + "%)"
        )
        Domoticz.Status(
            "   RX lentgh errors : %s (%s"
            % (self.frameErrors(), round((self.frameErrors() / self.received()) * 100, 2))
            + "%)"
        )
        Domoticz.Status("   RX clusters      : %s" % (self.clusterOK()))
        Domoticz.Status("   RX clusters KO   : %s" % (self.clusterKO()))
        t0 = self.starttime()
        t1 = int(time())
        _days = 0
        _duration = t1 - t0
        _hours = _duration // 3600
        _duration = _duration % 3600
        if _hours >= 24:
            _days = _hours // 24
            _hours = _hours % 24
        _min = _duration // 60
        _duration = _duration % 60
        _sec = _duration % 60
        Domoticz.Status("Operating time      : %s Hours %s Mins %s Secs" % (_hours, _min, _sec))

    def writeReport(self):

        timing = int(time())
        stats = {timing: {}}
        stats[timing]["crcErrors"] = self._crcErrors
        stats[timing]["frameErrors"] = self._frameErrors
        stats[timing]["sent"] = self._sent
        stats[timing]["received"] = self._received
        stats[timing]["APS Ack"] = self._APSAck
        stats[timing]["APS Nck"] = self._APSNck
        stats[timing]["ack"] = self._ack
        stats[timing]["ackKO"] = self._ackKO
        stats[timing]["data"] = self._data
        stats[timing]["TOstatus"] = self._TOstatus
        stats[timing]["TOdata"] = self._TOdata
        stats[timing]["clusterOK"] = self._clusterOK
        stats[timing]["clusterKO"] = self._clusterKO
        stats[timing]["reTx"] = self._reTx
        stats[timing]["MaxLoad"] = self._MaxLoad
        stats[timing]["start"] = self._start
        stats[timing]["stop"] = timing

        json_filename = self.pluginconf.pluginConf["pluginReports"] + "Transport-stats.json"
        with open(json_filename, "at") as json_file:
            json_file.write("\n")
            json.dump(stats, json_file)
