#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

from Modules.basicOutputs import write_attribute, read_attribute
from Modules.tools import getListOfEpForCluster
from Modules.zigateConsts import ZIGATE_EP


def danfoss_exercise_day_of_week(self, NwkId, week_num):
    # 0 = Sunday, 1 = Monday, … 6 = Saturday, 7 = undefined
    

    if week_num > 6:
        return
    manuf_id = "1246"
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0201

    EPout = "01"
    for tmpEp in self.ListOfDevices[NwkId]["Ep"]:
        if "0201" in self.ListOfDevices[NwkId]["Ep"][tmpEp]:
            EPout = tmpEp

    Hattribute = "%04x" % 0x4010
    data_type = "30"  # enum8
    self.log.logging("Danfoss", "Debug", "Danfoss Aly Trigger_Week Num: %s" % week_num, nwkid=NwkId)

    Hdata = "%02x" % week_num

    self.log.logging(
        "Danfoss",
        "Debug",
        "danfoss_exercise_trigger_time - Week Num for %s with value %s / cluster: %s, attribute: %s type: %s"
        % (NwkId, Hdata, cluster_id, Hattribute, data_type),
        nwkid=NwkId,
    )
    write_attribute(self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata, ackIsDisabled=False)
    read_attribute(self, NwkId, ZIGATE_EP, EPout, cluster_id, "00", manuf_spec, manuf_id, 1, Hattribute, ackIsDisabled=False)


def danfoss_exercise_trigger_time(self, NwkId, min_from_midnight):

    # Minutes since midnight, 0xFFFF = undefined
    if min_from_midnight > 1439:
        return

    manuf_id = "1246"
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0201

    EPout = "01"
    for tmpEp in self.ListOfDevices[NwkId]["Ep"]:
        if "0201" in self.ListOfDevices[NwkId]["Ep"][tmpEp]:
            EPout = tmpEp

    Hattribute = "%04x" % 0x4011
    data_type = "21"  # uint16
    self.log.logging("Danfoss", "Debug", "Danfoss Aly Trigger_time Min from Midnigh: %s" % min_from_midnight, nwkid=NwkId)

    Hdata = "%04x" % min_from_midnight
    EPout = "01"

    self.log.logging(
        "Danfoss",
        "Debug",
        "danfoss_exercise_trigger_time - Trigger time for %s with value %s / cluster: %s, attribute: %s type: %s"
        % (NwkId, Hdata, cluster_id, Hattribute, data_type),
        nwkid=NwkId,
    )

    write_attribute(self, NwkId, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata, ackIsDisabled=False)
    read_attribute(self, NwkId, ZIGATE_EP, EPout, cluster_id, "00", manuf_spec, manuf_id, 1, Hattribute, ackIsDisabled=False)


def danfoss_write_external_sensor_temp(self, NwkId, temp):

    # 0110 02 955e 01 01 0201 00 01 1246 01 4015 29 02bc

    # Convert value to a 0.5 multiple

    temp = 50 * (temp // 50)

    manuf_id = "1246"
    manuf_spec = "01"
    cluster_id = "%04x" % 0x0201

    EPout = "01"
    for tmpEp in self.ListOfDevices[NwkId]["Ep"]:
        if "0201" in self.ListOfDevices[NwkId]["Ep"][tmpEp]:
            EPout = tmpEp

    Hattribute = "%04x" % 0x4015
    data_type = "29"  # Int16
    self.log.logging("Danfoss", "Debug", "danfoss_write_external_sensor_temp: %s" % temp, nwkid=NwkId)

    Hdata = "%04x" % temp

    self.log.logging(
        "Danfoss",
        "Debug",
        "danfoss_write_external_sensor_temp - Trigger time for %s with value %s / cluster: %s, attribute: %s type: %s"
        % (NwkId, Hdata, cluster_id, Hattribute, data_type),
        nwkid=NwkId,
    )

    write_attribute(self, NwkId, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata, ackIsDisabled=False)
    read_attribute(self, NwkId, ZIGATE_EP, EPout, cluster_id, "00", manuf_spec, manuf_id, 1, Hattribute, ackIsDisabled=False)


def danfoss_external_sensor(self, NwkId, room, temp):
    # We received a Temperature measures

    # search in all device if any Danfoss Aly belongs to this room
    for x in self.ListOfDevices:
        if x == NwkId:
            continue
        if "Param" not in self.ListOfDevices[x]:
            continue
        if "DanfossRoom" not in self.ListOfDevices[x]["Param"]:
            continue
        if self.ListOfDevices[x]["Param"]["DanfossRoom"] != room:
            continue
        self.log.logging(
            "Danfoss",
            "Debug",
            "danfoss_external_sensor - Found device %s part of the same room %s" % (NwkId, room),
            nwkid=NwkId,
        )
        if "01" not in self.ListOfDevices[x]["Ep"]:
            continue
        if "0201" not in self.ListOfDevices[x]["Ep"]["01"]:
            continue
        danfoss_write_external_sensor_temp(self, NwkId, temp)


def danfoss_room_sensor_polling(self, NwkId):

    # This has been triggered because "DanfossRoomFreq" exist and > 0
    # This is expected for a eTRV which belongs to a Room for which an external Temp sensor exist
    # External Temp Sensor will only have the "DanfossRoom" parameter

    self.log.logging(
        "Danfoss",
        "Debug",
        "danfoss_room_sensor_polling - Triggered for Nwkid: %s" % (NwkId,),
        nwkid=NwkId,
    )

    if "Param" not in self.ListOfDevices[NwkId]:
        return
    if "DanfossRoom" not in self.ListOfDevices[NwkId]["Param"]:
        return
    room = self.ListOfDevices[NwkId]["Param"]["DanfossRoom"]

    self.log.logging(
        "Danfoss",
        "Debug",
        "danfoss_room_sensor_polling - Triggered for Nwkid: %s - room: %s" % (NwkId, room),
        nwkid=NwkId,
    )

    # Search for Temp Sensor for that Room
    for x in self.ListOfDevices:
        if x == NwkId:
            continue
        if "Param" not in self.ListOfDevices[x]:
            continue
        if "DanfossRoom" not in self.ListOfDevices[x]["Param"]:
            continue
        if self.ListOfDevices[x]["Param"]["DanfossRoom"] != room:
            continue

        ep_list = ListOfEp = getListOfEpForCluster(self, x, "0402")
        if ep_list == []:
            continue

        ep = ep_list[0]

        if "0000" not in self.ListOfDevices[x]["Ep"][ep]["0402"]:
            continue

        # At that stage we have found a Device which is in the same room and as the 0402 Cluster
        # Temp value is store in 0x0402/0x0000 is degrees
        temp_room = self.ListOfDevices[x]["Ep"][ep]["0402"]["0000"]
        danfoss_write_external_sensor_temp(self, NwkId, temp_room)
