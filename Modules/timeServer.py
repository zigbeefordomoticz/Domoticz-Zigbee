#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#


from Modules.basicInputs import read_attribute_response
from datetime import datetime


def timeserver_read_attribute_request(self, sqn, nwkid, ep, cluster, manuf_spec, manuf_code, attribute):

    self.log.logging(
        "Input",
        "Debug",
        "timeserver_read_attribute_request [%s] %s/%s Cluster: %s Attribute: %s" % (sqn, nwkid, ep, cluster, attribute),
    )
    data_type = value = None
    status = "86"

    if "SQN_000a" in self.ListOfDevices[nwkid] and sqn == self.ListOfDevices[nwkid]["SQN_000a"]:
        # Duplicate
        self.log.logging(
            "Input",
            "Debug",
            "timeserver_read_attribute_request [%s] %s/%s Cluster: %s Attribute: %s already processed"
            % (sqn, nwkid, ep, cluster, attribute),
        )
        return
    self.ListOfDevices[nwkid]["SQN_000a"] = sqn

    if attribute == "0000":  # Time (
        self.log.logging("Input", "Debug", "-->Local Time: %s" % datetime.now())
        EPOCTime = datetime(2000, 1, 1, 0, 0, 0, 0)
        UTCTime = int((datetime.now() - EPOCTime).total_seconds())
        value = "%08x" % UTCTime
        data_type = "e2"  # UTC Type
        status = "00"

    elif attribute == "0001":  # Time status
        self.log.logging("Input", "Debug", "-->Time Status: %s" % 0b00001100)
        value = "%02x" % 0x07  # Time Status: 0x07, Master, Synchronized, Master for Time Zone and DST
        data_type = "18"  # map8
        status = "00"

    elif attribute == "0002":  # Timezone
        diff = datetime.fromtimestamp(86400) - datetime.utcfromtimestamp(86400)
        self.log.logging("Input", "Debug", "--> TimeZone %s" % int(diff.total_seconds()))
        value = "%08x" % int(diff.total_seconds())
        data_type = "2b"  # int32
        status = "00"

    elif attribute == "0003": # Day Light saving Start
        self.log.logging("Input", "Debug", "--> DstStart %0x" % 0x00000000)
        value = "%08x" % 0xffffffff
        data_type = "23"  # unint32
        status = "00"
        
    elif attribute == "0004": # Day Light saving time End
        self.log.logging("Input", "Debug", "--> DstEnd %0x" % 0x00000000)
        value = "%08x" % 0xffffffff
        data_type = "23"  # unint32
        status = "00"
        
    elif attribute == "0005": # Day light saving shift
        self.log.logging("Input", "Debug", "--> DstShift %0x" % 0x00000000)
        value = "%08x" % 0x0
        data_type = "2B"  # int32
        status = "00"

    elif attribute == "0006": # StandardTime
        self.log.logging("Input", "Debug", "--> StandardTime %0x" % 0x00000000)
        value = "%08x" % 0x00000000
        data_type = "23"  # unint32
        status = "00"

    elif attribute == "0007":  # LocalTime
        self.log.logging("Input", "Debug", "-->Local Time: %s" % datetime.now())
        if "Model" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Model"] == "TS0601-thermostat":
            self.log.logging(
                "Input",
                "Debug",
                "timeserver_read_attribute_request Response use EPOCH from 1970,1,1 instead of 2000,1,1",
            )
            EPOCTime = datetime(1970, 1, 1, 0, 0, 0, 0)
        else:
            EPOCTime = datetime(2000, 1, 1, 0, 0, 0, 0)
        UTCTime = int((datetime.now() - EPOCTime).total_seconds())
        value = "%08x" % UTCTime
        data_type = "23"  # uint32
        status = "00"
        
    self.log.logging(
        "Input",
        "Debug",
        "timeserver_read_attribute_request Response: status: %s attribute: %s value: %s" % (status, attribute, value),
    )
    read_attribute_response(self, nwkid, ep, sqn, cluster, status, data_type, attribute, value, manuf_code="0000")
