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
        self._APSFailure = 0 # Count APS Failure
        self._APSAck = 0 # Firmware 3.1b 0x8011 status 00
        self._APSNck = 0 # Firmware 3.1b 0x8011 status not 00
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
        self._start = int(time())
        self.TrendStats = []
        self.pluginconf = pluginconf

    # Statistics methods 
    def starttime(self):
        return self._start

    def addPointforTrendStats( self, TimeStamp ):

        MAX_TREND_STAT_TABLE = 120

        uptime = int( time() - self._start)
        Rxps = round( self._received / uptime, 2)
        Txps = round( self._sent / uptime, 2)
        if len(self.TrendStats) >= MAX_TREND_STAT_TABLE:
            del self.TrendStats[0]
        self.TrendStats.append( { "_TS":TimeStamp, "Rxps": Rxps,"Txps": Txps, "Load": self._Load} )

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

    def APSFailure(self):
        return self._APSFailure

    def APSAck(self):
        return self._APSAck
    
    def APSNck(self):
        return self._APSNck

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
        Domoticz.Status("   TX APS Failure   : %s (%s" % (self.APSFailure(), round((self.APSFailure()/self.sent())*100,2)) + '%)')
        Domoticz.Status("   TX APS Ack       : %s (%s" % (self.APSAck(), round((self.APSAck()/self.sent())*100,2)) + '%)')
        Domoticz.Status("   TX APS Nck       : %s (%s" % (self.APSNck(), round((self.APSNck()/self.sent())*100,2)) + '%)')
        Domoticz.Status("Received:")
        Domoticz.Status("   RX frame         : %s" % (self.received()))
        Domoticz.Status("   RX crc errors    : %s (%s" % (self.crcErrors(), round((self.crcErrors()/self.received())*100,2)) + '%)')
        Domoticz.Status("   RX lentgh errors : %s (%s" % (self.frameErrors(), round((self.frameErrors()/self.received())*100,2)) + '%)')
        Domoticz.Status("   RX clusters      : %s" % (self.clusterOK()))
        Domoticz.Status("   RX clusters KO   : %s" % (self.clusterKO()))
        t0 = self.starttime()
        t1 = int(time())
        _days = 0
        _duration = t1 -t0
        _hours = _duration // 3600
        _duration = _duration % 3600
        if _hours >= 24:
            _days = _hours // 24
            _hours = _hours % 24
        _min = _duration // 60
        _duration = _duration % 60
        _sec =  _duration % 60
        Domoticz.Status("Operating time      : %s Hours %s Mins %s Secs" % (_hours, _min, _sec))

    def writeReport(self):

        timing = int(time())
        stats = {timing: {}}
        stats[timing]['crcErrors'] = self._crcErrors
        stats[timing]['frameErrors'] = self._frameErrors
        stats[timing]['sent'] = self._sent
        stats[timing]['received'] = self._received
        stats[timing]['APS Ack'] = self._APSAck
        stats[timing]['APS Nck'] = self._APSNck
        stats[timing]['ack'] = self._ack
        stats[timing]['ackKO'] = self._ackKO
        stats[timing]['data'] = self._data
        stats[timing]['TOstatus'] = self._TOstatus
        stats[timing]['TOdata'] = self._TOdata
        stats[timing]['clusterOK'] = self._clusterOK
        stats[timing]['clusterKO'] = self._clusterKO
        stats[timing]['reTx'] = self._reTx
        stats[timing]['MaxLoad'] = self._MaxLoad
        stats[timing]['start'] = self._start
        stats[timing]['stop'] = timing

        json_filename = self.pluginconf.pluginConf['pluginReports'] + 'Transport-stats.json'
        with open( json_filename, 'at') as json_file:
            json_file.write('\n')
            json.dump( stats, json_file)
