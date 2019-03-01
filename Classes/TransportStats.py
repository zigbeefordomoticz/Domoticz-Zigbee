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
        self._crcErrors = 0  # count of crc errors
        self._frameErrors = 0  # count of frames error
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
        self._MaxLoad = 0
        self._start = int(time())
        self.pluginconf = pluginconf

    # Statistics methods 
    def starttime(self):
        return self._start

    def reTx(self):
        """ return the number of crc Errors """
        return self._reTx

    def crcErrors(self):
        ' return the number of crc Errors '
        return self._crcErrors

    def frameErrors(self):
        ' return the number of frame errors'
        return self._frameErrors

    def sent(self):
        ' return he number of sent messages'
        return self._sent

    def received(self):
        ' return the number of received messages'
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

    def printSummary(self):
        if self.received() == 0:
            return
        Domoticz.Status("Statistics on message")
        Domoticz.Status("Sent:")
        Domoticz.Status("   TX commands      : %s" % (self.sent()))
        Domoticz.Status("   Max Load (Queue) : %s " % (self._MaxLoad))
        Domoticz.Status("   TX failed        : %s (%s" % (self.ackKOReceived(), round((self.ackKOReceived()/self.sent())*10,2)) + '%)')
        Domoticz.Status("   TX timeout       : %s (%s" % (self.TOstatus(), round((self.TOstatus()/self.sent())*100,2)) + '%)')
        Domoticz.Status("   TX data timeout  : %s (%s" % (self.TOdata(), round((self.TOdata()/self.sent())*100,2)) + '%)')
        Domoticz.Status("   TX reTransmit    : %s (%s" % (self.reTx(), round((self.reTx()/self.sent())*100,2)) + '%)')
        Domoticz.Status("Received:")
        Domoticz.Status("   RX frame         : %s" % (self.received()))
        Domoticz.Status("   RX crc errors    : %s (%s" % (self.crcErrors(), round((self.crcErrors()/self.received())*100,2)) + '%)')
        Domoticz.Status("   RX lentgh errors : %s (%s" % (self.frameErrors(), round((self.frameErrors()/self.received())*100,2)) + '%)')
        Domoticz.Status("   RX clusters      : %s" % (self.clusterOK()))
        Domoticz.Status("   RX clusters KO   : %s" % (self.clusterKO()))
        t0 = self.starttime()
        t1 = int(time())
        hours = (t1 - t0) // 3600
        min = (t1 - t0) // 60
        sec = (t1 - t0) % 60
        Domoticz.Status("Operating time      : %s Hours %s Mins %s Secs" % (hours, min, sec))

    def writeReport(self):

        stats = {}
        stats['crcErrors'] = self._crcErrors
        stats['frameErrors'] = self._frameErrors
        stats['sent'] = self._sent
        stats['received'] = self._received
        stats['ack'] = self._ack
        stats['ackKO'] = self._ackKO
        stats['data'] = self._data
        stats['TOstatus'] = self._TOstatus
        stats['TOdata'] = self._TOdata
        stats['clusterOK'] = self._clusterOK
        stats['clusterKO'] = self._clusterKO
        stats['reTx'] = self._reTx
        stats['MaxLoad'] = self._MaxLoad
        stats['start'] = self._start
        stats['stop'] = int(time())

        json_filename = self.pluginconf.pluginReports + 'Transport-stats.json'
        with open( json_filename, 'at') as json_file:
            json_file.write('\n')
            json.dump( stats, json_file)
