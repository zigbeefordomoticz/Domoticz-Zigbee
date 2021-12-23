#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_IAS.py
    Description: IAS Zone management
"""


import Domoticz
from Modules.zigateConsts import ADDRESS_MODE, ZIGATE_EP
from Zigbee.zclCommands import (zcl_ias_wd_command_squawk,
                                zcl_ias_wd_command_start_warning,
                                zcl_ias_zone_enroll_response,
                                zcl_read_attribute, zcl_write_attribute)

ENROLL_RESPONSE_CODE = 0x00
ZONE_ID = 0x00


class IAS_Zone_Management:
    def __init__(self, pluginconf, ZigateComm, ListOfDevices, log, zigbee_communitation, FirmwareVersion, ZigateIEEE=None):
        self.devices = {}
        self.ListOfDevices = ListOfDevices
        self.tryHB = 0
        self.wip = []
        self.HB = 0
        self.ZigateComm = ZigateComm
        self.ZigateIEEE = None
        if ZigateIEEE:
            self.ZigateIEEE = ZigateIEEE
        self.pluginconf = pluginconf
        self.log = log
        self.zigbee_communitation = zigbee_communitation
        self.FirmwareVersion = FirmwareVersion

    def logging(self, logType, message):
        self.log.logging("IAS", logType, message)

    def __write_attribute(self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data):

        #addr_mode = "02"  # Short address
        #direction = "00"
        #lenght = "01"  # Only 1 attribute
        #datas = addr_mode + key + EPin + EPout + clusterID
        #datas += direction + manuf_spec + manuf_id
        #datas += lenght + attribute + data_type + data
        # Domoticz.Log("__write_attribute : %s" %self.ZigateComm)
        #self.ZigateComm.sendData("0110", datas, ackIsDisabled=False)
        zcl_write_attribute( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled=False )

    def __ReadAttributeReq(self, addr, EpIn, EpOut, Cluster, ListOfAttributes):

        direction = "00"
        manufacturer_spec = "00"
        manufacturer = "0000"
        if addr not in self.ListOfDevices:
            return
        # if 'Manufacturer' in self.ListOfDevices[addr]:
        #    manufacturer = self.ListOfDevices[addr]['Manufacturer']
        if not isinstance(ListOfAttributes, list):
            # We received only 1 attribute
            Attr = "%04x" % (ListOfAttributes)
            lenAttr = 1
        else:
            lenAttr = len(ListOfAttributes)
            Attr = ""
            for x in ListOfAttributes:
                Attr_ = "%04x" % (x)
                Attr += Attr_
        #datas = (
        #    "02"
        #    + addr
        #    + EpIn
        #    + EpOut
        #    + Cluster
        #    + direction
        #    + manufacturer_spec
        #    + manufacturer
        #    + "%02x" % (lenAttr)
        #    + Attr
        #)
        #self.ZigateComm.sendData("0100", datas, ackIsDisabled=False)
        zcl_read_attribute(self, addr, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, lenAttr, Attr, ackIsDisabled=False)

    def setZigateIEEE(self, ZigateIEEE):
        
        self.logging("Debug", "setZigateIEEE - Set Zigate IEEE: %s" % ZigateIEEE)
        self.ZigateIEEE = ZigateIEEE

    def setIASzoneControlerIEEE(self, key, Epout):

        self.logging("Debug", "setIASzoneControlerIEEE for %s allow: %s" % (key, Epout))
        if not self.ZigateIEEE:
            self.logging("Error", "readConfirmEnroll - Zigate IEEE not yet known")
            return

        manuf_id = "0000"
        manuf_spec = "00"
        cluster_id = "%04x" % 0x0500
        attribute = "%04x" % 0x0010
        data_type = "F0"  # ZigBee_IeeeAddress = 0xf0
        data = str(self.ZigateIEEE)
        self.__write_attribute(key, ZIGATE_EP, Epout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)


    def readConfirmEnroll(self, key, Epout):

        if not self.ZigateIEEE:
            self.logging("Error", "readConfirmEnroll - Zigate IEEE not yet known")
            return
        if key not in self.devices and Epout not in self.devices[key]:
            self.logging("Log", "readConfirmEnroll - while not yet started")
            return

        cluster_id = "%04x" % 0x0500
        attribute = 0x0000
        self.__ReadAttributeReq(key, ZIGATE_EP, Epout, cluster_id, attribute)


    def readConfirmIEEE(self, key, Epout):

        if not self.ZigateIEEE:
            self.logging("Error", "readConfirmEnroll - Zigate IEEE not yet known")
            return
        if key not in self.devices and Epout not in self.devices[key]:
            self.logging("Log", "readConfirmEnroll - while not yet started")
            return

        cluster_id = "%04x" % 0x0500
        attribute = 0x0010
        self.__ReadAttributeReq(key, ZIGATE_EP, Epout, cluster_id, attribute)

    def IASZone_enroll_response_zoneIDzoneID(self, nwkid, Epout):
        """2./4.the CIE sends again a ‘response’ message to the IAS Zone device with ZoneID"""

        if not self.ZigateIEEE:
            self.logging("Error", "IASZone_enroll_response_zoneIDzoneID - Zigate IEEE not yet known")
            return
        if nwkid not in self.devices and Epout not in self.devices[nwkid]:
            self.logging("Log", "IASZone_enroll_response_zoneIDzoneID - while not yet started")
            return

        self.logging("Debug", "IASZone_enroll_response for %s" % nwkid)
        addr_mode = "02"
        enroll_rsp_code = "%02x" % ENROLL_RESPONSE_CODE
        zoneid = "%02x" % ZONE_ID

        #datas = addr_mode + nwkid + ZIGATE_EP + Epout + enroll_rsp_code + zoneid
        #self.ZigateComm.sendData("0400", datas)
        zcl_ias_zone_enroll_response(self, nwkid, ZIGATE_EP, Epout, enroll_rsp_code, zoneid)

    def IASWD_enroll(self, nwkid, Epout):

        cluster_id = "0502"
        manuf_id = "00"
        manuf_spec = "0000"
        attribute = "0000"
        data_type = "%02X" % 0x21
        data = "%04X" % 0xFFFE
        self.__write_attribute(nwkid, ZIGATE_EP, Epout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)

    def IASZone_attributes(self, nwkid, Epout):

        if not self.ZigateIEEE:
            self.logging("Error", "IASZone_attributes - Zigate IEEE not yet known")
            return
        if nwkid not in self.devices and Epout not in self.devices[nwkid]:
            self.logging("Log", "IASZone_attributes - while not yet started")
            return

        cluster_id = "%04x" % 0x0500
        attribute = [0x0000, 0x0001, 0x0002]
        self.__ReadAttributeReq(nwkid, ZIGATE_EP, Epout, cluster_id, attribute)

    def IASZone_triggerenrollement(self, nwkid, Epout):

        self.logging("Debug", "IASZone_triggerenrollement - Addr: %s Ep: %s" % (nwkid, Epout))
        if not self.ZigateIEEE:
            self.logging("Error", "IASZone_triggerenrollement - Zigate IEEE not yet known")
            return
        if nwkid not in self.devices:
            self.devices[nwkid] = {}

        if Epout not in self.devices[nwkid]:
            self.devices[nwkid][Epout] = {}

        self.wip.append((nwkid, Epout))
        self.HB = 0
        self.devices[nwkid][Epout]["Step"] = 2

        self.setIASzoneControlerIEEE(nwkid, Epout)

    def receiveIASenrollmentRequestResponse(self, nwkid, SrcEp, EnrolmentCode, zoneid):

        if "IAS" not in self.ListOfDevices[nwkid]:
            self.ListOfDevices[nwkid]["IAS"] = {}

        if SrcEp not in self.ListOfDevices[nwkid]["IAS"]:
            self.ListOfDevices[nwkid]["IAS"][SrcEp] = {
                'EnrolledStatus': {},
                'ZoneType': {},
                'ZoneTypeName': {},
                'ZoneStatus': {},
            }

        if not isinstance(self.ListOfDevices[nwkid]["IAS"][SrcEp]["ZoneStatus"], dict):
            self.ListOfDevices[nwkid]["IAS"][SrcEp]["ZoneStatus"] = {}

        if "Model" in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]["Model"] == "MOSZB-140":

            if EnrolmentCode == "00":
                self.ListOfDevices[nwkid]["IAS"][SrcEp]["EnrolledStatus"] = 1
            self.ListOfDevices[nwkid]["IAS"][SrcEp]["ZoneId"] = zoneid

            if nwkid in self.devices and SrcEp in self.devices[nwkid] and "Step" in self.devices[nwkid][SrcEp]:
                self.devices[nwkid][SrcEp]["Step"] = 7

    def receiveIASmessages(self, nwkid, SrcEp, step, value):

        self.logging("Debug", "receiveIASmessages - from: %s Step: %s Value: %s" % (nwkid, step, value))

        if not self.ZigateIEEE:
            self.logging("Debug", "receiveIASmessages - Zigate IEEE not yet known")
            return
        if nwkid not in self.devices:
            self.logging("Debug", "receiveIASmessages - %s not in %s" % (nwkid, self.devices))
            return

        if step == 3:  # Receive Write Attribute Message
            self.logging("Debug", "receiveIASmessages - Write rAttribute Response: %s" % value)
            self.HB = 0
            self.devices[nwkid][SrcEp]["Step"] = max(self.devices[nwkid][SrcEp]["Step"], 4)
            self.readConfirmEnroll(nwkid, SrcEp)
            self.IASZone_enroll_response_zoneIDzoneID(nwkid, SrcEp)

        elif step == 5:  # Receive Attribute 0x0000 (Enrollment)
            if SrcEp not in self.devices[nwkid]:
                return
            if "ticks_5" not in self.devices[nwkid][SrcEp]:
                self.devices[nwkid][SrcEp]["ticks_5"] = 0

            if self.devices[nwkid][SrcEp]["ticks_5"] > 3:
                self.logging("Debug", "receiveIASmessages - Timeout %s/%s at step 5" % (nwkid, SrcEp))
                del self.devices[nwkid][SrcEp]
                return

            self.HB = 0
            if self.devices[nwkid][SrcEp]["Step"] <= 7 and value == "01":
                self.devices[nwkid][SrcEp]["Step"] = 7
                self.readConfirmIEEE(nwkid, SrcEp)
            self.IASZone_enroll_response_zoneIDzoneID(nwkid, SrcEp)
            self.readConfirmEnroll(nwkid, SrcEp)

            self.devices[nwkid][SrcEp]["ticks_5"] += 1

        elif step == 7:  # Receive Enrollement IEEEE
            self.logging("Debug", "IAS_heartbeat - Enrollment with IEEE:%s" % value)

    def decode8401(
        self, MsgSQN, MsgEp, MsgClusterId, MsgSrcAddrMode, MsgSrcAddr, MsgZoneStatus, MsgExtStatus, MsgZoneID, MsgDelay
    ):

        return

    def IAS_heartbeat(self):

        self.HB += 1

        if len(self.wip) == 0:
            return
        self.logging("Debug", "IAS_heartbeat ")
        if not self.ZigateIEEE:
            self.logging("Debug", "IAS_heartbeat - Zigate IEEE not yet known")
            return

        for iterKey in list(self.devices):
            for iterEp in list(self.devices[iterKey]):
                self.logging(
                    "Debug", "IAS_heartbeat - processing %s step: %s" % (iterKey, self.devices[iterKey][iterEp]["Step"])
                )
                if self.devices[iterKey][iterEp]["Step"] == 0:
                    continue

                if self.HB > 1 and self.devices[iterKey][iterEp]["Step"] == 2:
                    self.HB = 0

                    self.logging("Debug", "IAS_heartbeat - TO restart self.IASZone_attributes")
                    self.IASZone_enroll_response_zoneIDzoneID(iterKey, iterEp)
                    self.IASZone_attributes(iterKey, iterEp)

                elif self.HB > 1 and self.devices[iterKey][iterEp]["Step"] == 4:
                    self.tryHB += self.tryHB
                    self.HB = 0
                    if iterKey not in self.wip:
                        self.wip.append(iterKey)

                    self.logging("Debug", "IAS_heartbeat - TO restart self.setIASzoneControlerIEEE")
                    if self.tryHB > 3:
                        self.tryHB = 0
                        self.devices[iterKey][iterEp]["Step"] = 5

                elif self.HB > 1 and self.devices[iterKey][iterEp]["Step"] == 6:
                    self.tryHB += self.tryHB
                    self.HB = 0

                    self.readConfirmEnroll(iterKey, iterEp)
                    self.logging("Debug", "IAS_heartbeat - TO restart self.readConfirmEnroll")
                    if self.tryHB > 3:
                        self.tryHB = 0
                        self.devices[iterKey][iterEp]["Step"] = 7

                elif self.devices[iterKey][iterEp]["Step"] == 7:  # Receive Confirming Enrollement
                    self.logging("Debug", "IAS_heartbeat - Enrollment confirmed/completed")
                    self.HB = 0
                    if (iterKey, iterEp) in self.wip:
                        self.wip.remove((iterKey, iterEp))

                    self.devices[iterKey][iterEp]["Step"] = 0
                    del self.devices[iterKey][iterEp]
                    if len(self.devices[iterKey]) == 0:
                        del self.devices[iterKey]

    def write_IAS_WD_Squawk(self, nwkid, ep, SquawkMode):
        SQUAWKMODE = {"disarmed": 0b00000000, "armed": 0b00000001}

        if SquawkMode not in SQUAWKMODE:
            Domoticz.Error("_write_IAS_WD_Squawk - %s/%s Unknown Squawk Mode: %s" % (nwkid, ep, SquawkMode))

        self.logging(
            "Debug",
            "write_IAS_WD_Squawk - %s/%s - Squawk Mode: %s >%s<" % (nwkid, ep, SquawkMode, SQUAWKMODE[SquawkMode]),
        )
        if SquawkMode == 'disarmed':
            squawk_mode = 0x01
            strobe = 0x00
            squawk_level = 0x00
        elif SquawkMode == 'armed':
            squawk_mode = 0x00
            strobe = 0x01
            squawk_level = 0x01
        
        zcl_ias_wd_command_squawk(self, ZIGATE_EP, ep, nwkid, squawk_mode, strobe, squawk_level, ackIsDisabled=False)

    def warningMode(self, nwkid, ep, mode="both", siren_level = 0x00, warning_duration = 0x01, strobe_duty = 0x00, strobe_level = 0x00):

        STROBE_LEVEL = {"Low": 0x00, "Medium": 0x01}
        SIRENE_MODE = ("both", "siren", "strobe", "stop")
        strobe_mode = 0x00
        
        if self.ListOfDevices[nwkid]["Model"] == "WarningDevice":
            if mode == "both":
                strobe_mode = 0x01
                warning_mode = 0x01
            elif mode == "siren":
                warning_mode = 0x01
            elif mode == "strobe":
                strobe_mode = 0x01
                warning_mode = 0x00
            elif mode == "stop":
                strobe_mode = 0x00
                warning_mode = 0x00

        elif mode in SIRENE_MODE:
            if mode == "both":
                strobe_level = STROBE_LEVEL["Low"]
                strobe_mode = 0x02
                warning_mode = 0x01
            elif mode == "siren":
                warning_mode = 0x02
            elif mode == "stop":
                strobe_mode = 0x00
                warning_mode = 0x00         
            elif mode == "strobe":
                strobe_level = STROBE_LEVEL["Low"]
                strobe_mode = 0x01
                warning_mode = 0x00

        if "Param" in self.ListOfDevices[nwkid]:
            if "alarmDuration" in self.ListOfDevices[nwkid]["Param"]:
                warning_duration = int(self.ListOfDevices[nwkid]["Param"]["alarmDuration"])
                
            if mode == "strobe" and "alarmStrobeCode" in self.ListOfDevices[nwkid]["Param"]:
                strobe_mode = int(self.ListOfDevices[nwkid]["Param"]["alarmStrobeCode"])
                
            if mode == "siren" and "alarmSirenCode" in self.ListOfDevices[nwkid]["Param"]:
                warning_mode = int(self.ListOfDevices[nwkid]["Param"]["alarmSirenCode"])
                
        self.logging( "Debug", "warningMode - Mode: %s, Duration: %s, Duty: %s, Level: %s" % (bin(warning_mode), warning_duration, strobe_duty, strobe_level), )
        zcl_ias_wd_command_start_warning(self, ZIGATE_EP, ep, nwkid, warning_mode, strobe_mode, siren_level, warning_duration, strobe_duty, strobe_level, groupaddrmode=False, ackIsDisabled=False)

    def siren_both(self, nwkid, ep):
        self.logging("Debug", "Device Alarm On ( Siren + Strobe)")
        self.warningMode(nwkid, ep, "both")

    def siren_only(self, nwkid, ep):
        self.logging("Debug", "Device Alarm On (Siren)")
        self.warningMode(nwkid, ep, "siren")

    def strobe_only(self, nwkid, ep):
        self.logging("Debug", "Device Alarm On ( Strobe)")
        self.warningMode(nwkid, ep, "strobe")

    def alarm_on(self, nwkid, ep):
        self.siren_both(nwkid, ep)

    def alarm_off(self, nwkid, ep):
        self.logging("Debug", "Device Alarm Off")
        self.warningMode(nwkid, ep, "stop")
