#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
    Module: z_readClusters.py

    Description: manage all incoming Clusters messages

"""

import binascii
import struct
from time import time

from Modules.domoMaj import MajDomoDevice
from Modules.ikeaTradfri import ikea_air_purifier_cluster
from Modules.lumi import (AqaraOppleDecoding0012, cube_decode, decode_vibr,
                          decode_vibrAngle)
from Modules.philips import philips_dimmer_switch
from Modules.readZclClusters import (is_cluster_zcl_config_available,
                                     process_cluster_attribute_response)
from Modules.schneider_wiser import (receiving_heatingdemand_attribute,
                                     receiving_heatingpoint_attribute)
from Modules.tools import (DeviceExist, checkAndStoreAttributeValue,
                           checkAttribute, checkValidValue,
                           get_deviceconf_parameter_value, getEPforClusterType,
                           set_status_datastruct, set_timestamp_datastruct)
from Modules.zclClusterHelpers import compute_metering_conso
from Modules.zigateConsts import ZONE_TYPE


def decodeAttribute(self, AttType, Attribute, handleErrors=False):

    if len(Attribute) == 0:
        return ""

    self.log.logging( "Cluster", 'Debug', "decodeAttribute( %s, %s) " %(AttType, Attribute) )

    if int(AttType, 16) == 0x10:  # Boolean
        return Attribute[:2]

    if int(AttType, 16) == 0x18:  # 8Bit bitmap
        return int(Attribute[:8], 16)

    if int(AttType, 16) == 0x19:  # 16BitBitMap
        return str(int(Attribute[:4], 16))

    if int(AttType, 16) == 0x20:  # Uint8 / unsigned char
        return int(Attribute[:2], 16)

    if int(AttType, 16) == 0x21:  # 16BitUint
        return str(struct.unpack("H", struct.pack("H", int(Attribute[:4], 16)))[0])

    if int(AttType, 16) == 0x22:  # ZigBee_24BitUint
        return str(struct.unpack("I", struct.pack("I", int("0" + Attribute, 16)))[0])

    if int(AttType, 16) == 0x23:  # 32BitUint
        return str(struct.unpack("I", struct.pack("I", int(Attribute[:8], 16)))[0])

    if int(AttType, 16) == 0x25:  # ZigBee_48BitUint
        return str(struct.unpack("Q", struct.pack("Q", int(Attribute, 16)))[0])

    if int(AttType, 16) == 0x28:  # int8
        return int(Attribute, 16)

    if int(AttType, 16) == 0x29:  # 16Bitint   -> tested on Measurement clusters
        return str(struct.unpack("h", struct.pack("H", int(Attribute[:4], 16)))[0])

    if int(AttType, 16) == 0x2A:  # ZigBee_24BitInt
        return str(struct.unpack("i", struct.pack("I", int("0" + Attribute, 16)))[0])

    if int(AttType, 16) == 0x2B:  # 32Bitint
        return str(struct.unpack("i", struct.pack("I", int(Attribute[:8], 16)))[0])

    if int(AttType, 16) == 0x2D:  # ZigBee_48Bitint
        return str(struct.unpack("q", struct.pack("Q", int(Attribute, 16)))[0])

    if int(AttType, 16) == 0x30:  # 8BitEnum
        return int(Attribute[:2], 16)

    if int(AttType, 16) == 0x31:  # 16BitEnum
        return str(struct.unpack("h", struct.pack("H", int(Attribute[:4], 16)))[0])

    if int(AttType, 16) == 0x39:  # Xiaomi Float
        return str(struct.unpack("f", struct.pack("I", int(Attribute, 16)))[0])

    if int(AttType, 16) in ( 0x42, 0x43):  # CharacterString
        decode = ""
        self.log.logging("Cluster", "Debug", "decodeAttribute - DataType: %s to decode >%s<" % ( AttType, str(Attribute)))

        try:
            decode = binascii.unhexlify(Attribute).decode("utf-8")
            self.log.logging("Cluster", "Debug", "decodeAttribute - ======> >%s< (%s) len: %s" % (decode, type(decode), len(decode)))
        except Exception as e:
            if handleErrors:  # If there is an error we force the result to '' This is used for 0x0000/0x0005
                self.log.logging("Cluster", "Log", "decodeAttribute - seems errors decoding %s/%s, so returning empty" % (
                    str(Attribute), e))
                decode = ""
            else:
                decode = binascii.unhexlify(Attribute).decode("utf-8", errors="ignore")
                decode = decode.replace("\x00", "")
                decode = decode.strip()
                self.log.logging(
                    "Cluster",
                    "Debug",
                    "decodeAttribute - seems errors, returning with errors ignore From: %s to >%s<" % (str(Attribute), str(decode)),
                )

        # Cleaning
        decode = decode.strip("\x00")
        decode = decode.strip()
        if decode is None:
            decode = ""
        return decode

    # self.log.logging( "Cluster", 'Debug', "decodeAttribut(%s, %s) unknown, returning %s unchanged" %(AttType, Attribute, Attribute) )
    return Attribute


def storeReadAttributeStatus(self, MsgType, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus):
    set_status_datastruct(self, "ReadAttributes", MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus)
    set_timestamp_datastruct(self, "ReadAttributes", MsgSrcAddr, MsgSrcEp, MsgClusterId, int(time()))


def ReadCluster( self, Devices, MsgType, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus, MsgAttType, MsgAttSize, MsgClusterData, Source=None, ):

    if MsgSrcAddr not in self.ListOfDevices:
        _context = create_context(MsgClusterId, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)
        self.log.logging("Cluster", "Error", "ReadCluster - unknown device: %s" % (MsgSrcAddr), MsgSrcAddr, _context)
        return

    if not DeviceExist(self, Devices, MsgSrcAddr):
        # We cannot process a none existing device.
        return

    if (
        MsgSrcAddr in self.ListOfDevices
        and "Health" in self.ListOfDevices[MsgSrcAddr] 
        and self.ListOfDevices[MsgSrcAddr]["Health"] == "Disabled"
    ):
        # If the device has been disabled, just drop the message
        self.log.logging("Command", "Debug", "disabled device: %s/%s droping message " % (MsgSrcAddr, MsgSrcEp), MsgSrcAddr)
        return
    
    if "Ep" not in self.ListOfDevices[MsgSrcAddr]:
        return
    if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]["Ep"]:
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp] = {}
    if MsgClusterId not in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]:
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId] = {}

    self.log.logging( "Cluster", "Debug", "ReadCluster - %s - %s/%s AttrId: %s AttrType: %s Attsize: %s Status: %s AttrValue: %s" % (
        MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgAttrStatus, MsgClusterData),MsgSrcAddr,)

    if MsgAttrStatus != "00" and MsgClusterId != "0500":
        # We receive a Read Attribute response or a Report with a status error.
        storeReadAttributeStatus(self, MsgType, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus)
        self.log.logging( "Cluster", "Debug", "ReadCluster - Status %s for addr: %s/%s on cluster/attribute %s/%s" % (
            MsgAttrStatus, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID), nwkid=MsgSrcAddr, )
        self.statistics._clusterKO += 1
        return

    if is_cluster_zcl_config_available( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, attribute=MsgAttrID):
        storeReadAttributeStatus(self, MsgType, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus)
        process_cluster_attribute_response( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source, )
    
    elif MsgClusterId in DECODE_CLUSTER:
        storeReadAttributeStatus(self, MsgType, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus)

        _func = DECODE_CLUSTER[MsgClusterId]
        _func( self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source, )

    else:
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)
        _context = create_context(MsgClusterId, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)

        self.log.logging( "Cluster", "Error", "ReadCluster - Warning - unknow %s/%s Cluster: %s Attribute: %s Status: %s DataType: %s DataSize: %s Data: %s" %(
            MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttrStatus, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr, _context, )


def Cluster0006(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):
    # Cluster On/Off

    #if MsgAttrID in ("0000", "8000"):
    if MsgAttrID == "0000":
        if "Model" not in self.ListOfDevices[MsgSrcAddr]:
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)
            return

        if self.ListOfDevices[MsgSrcAddr]["Model"] == "lumi.ctrl_neutral1" and MsgSrcEp != "02":
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

            # endpoint 02 is for controlling the L1 output
            # Blacklist all EPs other than '02'
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - ClusterId=%s - Unexpected EP, %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, Value: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
                MsgSrcAddr,
            )
            return

        if self.ListOfDevices[MsgSrcAddr]["Model"] == "lumi.ctrl_neutral2" and MsgSrcEp != "02" and MsgSrcEp != "03":
            # EP 02 ON/OFF LEFT    -- OK
            # EP 03 ON/ON RIGHT    -- OK
            # EP 04 EVENT LEFT
            # EP 05 EVENT RIGHT
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - ClusterId=%s - not processed EP, %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, Value: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
                MsgSrcAddr,
            )
            return

        if self.ListOfDevices[MsgSrcAddr]["Model"] in ("CPR412-E", "CPR412", "PR412") and MsgClusterData not in ("01", "00"):
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - ClusterId=%s - not processed %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, Value: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
                MsgSrcAddr,
            )
            return

        if self.ListOfDevices[MsgSrcAddr]["Model"] == "3AFE170100510001":
            # Konke Multi Purpose Switch
            value = None
            if MsgClusterData in ("01", "80"):  # Simple Click
                value = "01"
            elif MsgClusterData in ("02", "81"):  # Multiple Click
                value = "02"
            elif MsgClusterData == "82":  # Long Click
                value = "03"
            elif MsgClusterData == "cd":  # short reset , a short click on the reset button
                return
            else:
                return
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - ClusterId=0006 - Konke Multi Purpose Switch reception General: On/Off: %s" % value,
                MsgSrcAddr,
            )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value)
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)
            return

        if self.ListOfDevices[MsgSrcAddr]["Model"] == "TS0601-Parkside-Watering-Timer":
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - ClusterId=0006 - %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, : %s" % (MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
                MsgSrcAddr,
            )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)
            return

        if self.ListOfDevices[MsgSrcAddr]["Model"] == "TI0001":
            # Livolo / Might get something else than On/Off
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - ClusterId=0006 - %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, : %s" % (MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
                MsgSrcAddr,
            )


        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0006 - reception General: On/Off: %s" % str(MsgClusterData),
            MsgSrcAddr,
        )

    elif MsgAttrID == "00f5":
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0006 -  Attr: %s Value: %s" % (MsgAttrID, MsgClusterData),
            MsgSrcAddr,
        )

        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))
        
    elif MsgAttrID == "4000":  # Global Scene Control
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0006 - Global Scene Control Attr: %s Value: %s" % (MsgAttrID, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))

    elif MsgAttrID == "4001":  # On Time
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0006 - On Time Attr: %s Value: %s" % (MsgAttrID, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))

    elif MsgAttrID == "4002":  # Off Wait Time
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0006 - Off Wait Time Attr: %s Value: %s" % (MsgAttrID, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))

    elif MsgAttrID == "4003":  # Power On On Off
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0006 - Power On OnOff Attr: %s Value: %s" % (MsgAttrID, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))

    elif MsgAttrID == "5000":
        # Back light for Tuya Smart Relay CH4
        self.log.logging(
            "Cluster",
            "Debug",
            "readCluster - %s - %s/%s Back Light: %s %s %s %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))
        
    elif MsgAttrID == "8000" and "Model" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Model"] in ("lumi.sensor_switch", "lumi.sensor_switch.aq2", ):
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0006 - reception General: On/Off: %s for Mija Button" % str(MsgClusterData),
            MsgSrcAddr,
        )       

    elif MsgAttrID == "8000":
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))

    elif MsgAttrID == "8001" and "Model" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Model"] in ( "TS130F-_TZ3000_fvhunhxb", "TS130F-_TZ3000_zirycpws", "TS130F-_TZ3000_8kzqqzu4", "TS130F-_TZ3000_femsaaua",) :
        # Curtain Mode
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0006 - NwkId: %s Ep: %s Attr: %s Value: %s Curtain Mode" % (
                MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgClusterData),
            MsgSrcAddr,
        )
        
                
    elif MsgAttrID == "8001":
        # Tuya SMart Relay CH4 Indicate Light
        self.log.logging(
            "Cluster",
            "Debug",
            "readCluster - %s - %s/%s Indicate Light: %s %s %s %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))

    elif MsgAttrID == "8002":
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0006 - Power On OnOff Attr: %s Value: %s" % (MsgAttrID, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))

    elif MsgAttrID == "8003":
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0006 - Power On OnOff Attr: %s Value: %s" % (MsgAttrID, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))

    elif MsgAttrID == "f000" and MsgAttType == "23" and MsgAttSize == "0004":
        value = int(decodeAttribute(self, MsgAttType, MsgClusterData))
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - Feedback from device %s/%s Attribute 0xf000 value: %s-%s" % (MsgSrcAddr, MsgSrcEp, MsgClusterData, value),
            MsgSrcAddr,
        )
        _Xiaomi_code = MsgClusterData[0:2]
        # _Xiaomi_sAddr = MsgClusterData[2:6]
        _Xiaomi_Value = MsgClusterData[6:8]

        XIAOMI_CODE = {
            "00": "Remote Aqara Bulb Off",
            "01": "Power outage",
            "02": "Power On",
            "03": "Physical Action",
            "04": "04 (please report to @pipiche)",
            "05": "05 (please report to @pipiche)",
            "06": "06 (please report to @pipiche)",
            "07": "Command count",
            "0a": "Pairing",
            "0c": "0c (please report to @pipiche)",
        }

        if _Xiaomi_code in XIAOMI_CODE:
            if "ZDeviceName" in self.ListOfDevices[MsgSrcAddr]:
                self.log.logging(
                    "Cluster",
                    "Debug",
                    "ReadCluster - Xiaomi 0006/f000 - %s %s/%s %s: %s"
                    % (
                        self.ListOfDevices[MsgSrcAddr]["ZDeviceName"],
                        MsgSrcAddr,
                        MsgSrcEp,
                        XIAOMI_CODE[_Xiaomi_code],
                        int(_Xiaomi_Value, 16),
                    ),
                    MsgSrcAddr,
                )
            else:
                self.log.logging(
                    "Cluster",
                    "Debug",
                    "ReadCluster - Xiaomi 0006/f000 - %s/%s %s: %s" % (MsgSrcAddr, MsgSrcEp, XIAOMI_CODE[_Xiaomi_code], int(_Xiaomi_Value, 16)),
                    MsgSrcAddr,
                )

        else:
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - Xiaomi 0006/f000 - - %s/%s Unknown Xiaomi Code %s raw data: %s (please report to @pipiche)" % (MsgSrcAddr, MsgSrcEp, _Xiaomi_code, MsgClusterData),
                MsgSrcAddr,
            )

    elif MsgAttrID == "fffd":
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0006 - unknown Attr: %s Value: %s" % (MsgAttrID, MsgClusterData),
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))

    else:
        self.log.logging(
            "Cluster",
            "Log",
            "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))


def Cluster0008(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):
    # LevelControl cluster

    checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    self.log.logging(
        "Cluster",
        "Debug",
        "ReadCluster - ClusterID: %s Addr: %s MsgAttrID: %s MsgAttType: %s MsgAttSize: %s MsgClusterData: %s" % (MsgClusterId, MsgSrcAddr, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
        MsgSrcAddr,
    )

    if MsgAttrID == "0000":  # Current Level
        if "Model" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Model"] == "TI0001" and MsgSrcEp == "06":  # Livolo switch
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - ClusterId=0008 - %s/%s MsgAttrID: %s, MsgAttType: %s, MsgAttSize: %s, : %s" % (MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
                MsgSrcAddr,
            )
            # Do nothing as the Livolo state is given by 0x0100
            return
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0008 - %s/%s Level Control: %s" % (MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)

    elif MsgAttrID == "0001":  # Remaining Time
        # The RemainingTime attribute represents the time remaining until the current
        # command is complete - it is specified in 1/10ths of a second.
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0008 - %s/%s Remaining Time: %s" % (MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )

    elif MsgAttrID == "0010":  # OnOffTransitionTime
        # The OnOffTransitionTime attribute represents the time taken to move to or from the target level
        # when On of Off commands are received by an On/Off cluster on the same endpoint. It is specified in 1/10ths of a second.
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0008 - %s/%s OnOff Transition Time: %s" % (MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )

    elif MsgAttrID == "0011":  # OnLevel
        # The OnLevel attribute determines the value that the CurrentLevel attribute is
        # set to when the OnOff attribute of an On/Off cluster on the same endpoint is set to On.
        # If the OnLevel attribute is not implemented, or is set to 0xff, it has no effect.
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0008 - %s/%s On Level : %s" % (MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )

    elif MsgAttrID == "4000":  #
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0008 - %s/%s Attr: %s Value: %s" % (MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgClusterData),
            MsgSrcAddr,
        )

    elif MsgAttrID == "f000":
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - ClusterId=0008 - %s/%s Attr: %s Value: %s" % (MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgClusterData),
            MsgSrcAddr,
        )

    else:
        self.log.logging(
            "Cluster",
            "Log",
            "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
            MsgSrcAddr,
        )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId][MsgAttrID] = str(decodeAttribute(self, MsgAttType, MsgClusterData))


def Cluster000c(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):
    # Analog Binary
    # Magic Cube Xiaomi rotation and Power Meter
    self.log.logging(
        "Cluster",
        "Debug",
        "ReadCluster - ClusterID=000C - MsgSrcEp: %s MsgAttrID: %s MsgAttType: %s MsgClusterData: %s " % (MsgSrcEp, MsgAttrID, MsgAttType, MsgClusterData),
        MsgSrcAddr,
    )
    checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))

    if MsgAttrID == "001c":  # Description
        self.log.logging("Cluster", "Debug", "%s/%s Description: %s" % (MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == "0051":  #
        self.log.logging("Cluster", "Debug", "%s/%s Out of service: %s" % (MsgSrcAddr, MsgSrcEp, MsgClusterData), MsgSrcAddr)

    elif MsgAttrID == "0055":  # The PresentValueattribute  indicates the current value  of the  input,  output or value
        xiaomi_power_endpoint = get_deviceconf_parameter_value(self, self.ListOfDevices[MsgSrcAddr]["Model"], "XIAOMI_POWER_EP")

        if self.ListOfDevices[MsgSrcAddr]["Model"] == "lumi.airmonitor.acn01":
            voc = decodeAttribute(self, MsgAttType, MsgClusterData)
            self.log.logging("Cluster", "Debug", "%s/%s Voc: %s" % (MsgSrcAddr, MsgSrcEp, voc), MsgSrcAddr)
            if not checkValidValue(self, MsgSrcAddr, MsgAttType, voc):
                self.log.logging( "Cluster", "Debug", "Voc - invalid Data Value found : %s" % (
                    voc), MsgSrcAddr, )
                return
            MajDomoDevice( self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, voc)
            return

        if xiaomi_power_endpoint:
            # The Power received via 0x0055
            value = round(float(decodeAttribute(self, MsgAttType, MsgClusterData)), 3)
            self.log.logging( "Cluster", "Debug", "readCluster - %s - %s/%s Xiaomi Power via PresentValue: %s:  %s " % (
                MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, value), MsgSrcAddr, )
            MajDomoDevice(self, Devices, MsgSrcAddr, xiaomi_power_endpoint, "0702", str(value))  # For to Power Cluster
            return

        if getEPforClusterType(self, MsgSrcAddr, "Analog") and MsgAttType == "39":
            # We have an Analog Widget created, so we can consider it is not a Xiaomi Plug nor an Aqara/XCube
            self.log.logging( "Cluster", "Debug", "readCluster - %s - %s/%s Xiaomi attribute: %s:  %s " % (
                MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, decodeAttribute(self, MsgAttType, MsgClusterData)), MsgSrcAddr, )
            if not checkValidValue(self, MsgSrcAddr, MsgAttType, MsgClusterData):
                self.log.logging( "Cluster", "Debug", "Cluster000c - MsgAttrID: %s MsgAttType: %s DataLen: %s : invalid Data Value found : %s" % (
                    MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr, )
                return
            MajDomoDevice( self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, str(decodeAttribute(self, MsgAttType, MsgClusterData)),)
            return

        EPforPower = getEPforClusterType(self, MsgSrcAddr, "Power")
        EPforMeter = getEPforClusterType(self, MsgSrcAddr, "Meter")
        EPforPowerMeter = getEPforClusterType(self, MsgSrcAddr, "PowerMeter")
        self.log.logging( "Cluster", "Debug", "EPforPower: %s, EPforMeter: %s, EPforPowerMeter: %s" % (
            EPforPower, EPforMeter, EPforPowerMeter), MsgSrcAddr, )

        if len(EPforPower) == len(EPforMeter) == len(EPforPowerMeter) == 0 and self.ListOfDevices[MsgSrcAddr]["Model"] != "lumi.airmonitor.acn01":
            # Magic Cub
            rotation_angle = struct.unpack("f", struct.pack("I", int(MsgClusterData, 16)))[0]
            self.log.logging("Cluster", "Debug", "ReadCluster - ClusterId=000c - Magic Cube angle: %s" % rotation_angle, MsgSrcAddr)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, str(int(rotation_angle)), Attribute_="0055")
            if rotation_angle < 0:
                # anti-clokc
                self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId][MsgAttrID] = "90"
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, "90")
            if rotation_angle >= 0:
                # Clock
                self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId][MsgAttrID] = "80"
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, "80")

        elif len(EPforPower) > 0 or len(EPforMeter) > 0 or len(EPforPowerMeter) > 0:  # We have several EPs in Power/Meter
            value = round(float(decodeAttribute(self, MsgAttType, MsgClusterData)), 3)
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - ClusterId=000c - MsgAttrID=0055 - on Ep " + str(MsgSrcEp) + " reception Conso Prise Xiaomi: " + str(value),
                MsgSrcAddr,
            )
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - ClusterId=000c - List of Power/Meter EPs" + str(EPforPower) + str(EPforMeter) + str(EPforPowerMeter),
                MsgSrcAddr,
            )
            self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId][MsgAttrID] = str(value)
            for ep in EPforPower + EPforMeter:
                if ep == MsgSrcEp:
                    self.log.logging(
                        "Cluster",
                        "Debug",
                        "ReadCluster - ClusterId=000c - MsgAttrID=0055 - reception Conso Prise Xiaomi: " + str(value),
                        MsgSrcAddr,
                    )
                    if "0702" not in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]:
                        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0702"] = {}
                    if not isinstance(self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0702"], dict):
                        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0702"] = {}
                    if "0400" not in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0702"]:
                        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0702"]["0400"] = {}

                    self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]["0702"]["0400"] = str(value)
                    MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0702", str(value))  # For to Power Cluster
                    break  # We just need to send once
        else:
            self.log.logging(
                "Cluster",
                "Log",
                "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
                MsgSrcAddr,
            )

    elif MsgAttrID == "006f":  # Status flag ( Bit 0 = IN ALARM, Bit 1 = FAULT, Bit 2 = OVERRIDDEN, Bit 3 = OUT OF SERVICE )
        status = int(MsgClusterData, 16)
        if status & 0b00000001:
            self.log.logging(
                "Cluster",
                "Log",
                "Device %s/%s IN ALARM"
                % (
                    MsgSrcAddr,
                    MsgSrcEp,
                ),
                MsgSrcAddr,
            )
        elif status & 0b00000010:
            self.log.logging(
                "Cluster",
                "Log",
                "Device %s/%s FAULT"
                % (
                    MsgSrcAddr,
                    MsgSrcEp,
                ),
                MsgSrcAddr,
            )
        elif status & 0b00000100:
            self.log.logging(
                "Cluster",
                "Log",
                "Device %s/%s OVERRIDDEN"
                % (
                    MsgSrcAddr,
                    MsgSrcEp,
                ),
                MsgSrcAddr,
            )
        elif status & 0b00001000:
            self.log.logging(
                "Cluster",
                "Log",
                "Device %s/%s OUT OF SERVICE"
                % (
                    MsgSrcAddr,
                    MsgSrcEp,
                ),
                MsgSrcAddr,
            )

    elif MsgAttrID == "ff05":  # Rotation - horinzontal
        self.log.logging("Cluster", "Debug", "ReadCluster - ClusterId=000c - Magic Cube Rotation: " + str(MsgClusterData), MsgSrcAddr)

    else:
        self.log.logging(
            "Cluster",
            "Log",
            "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
            MsgSrcAddr,
        )


def Cluster0012(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):

    if "Model" not in self.ListOfDevices[MsgSrcAddr]:
        return
    _modelName = self.ListOfDevices[MsgSrcAddr]["Model"]

    aqara_button3_behaviour = get_deviceconf_parameter_value(self, _modelName, "Aqara_Buton_3", return_default=None)
    self.log.logging( "Cluster", "Debug", "readCluster - %s - %s/%s MsgAttrID: %s MsgAttType: %s MsgAttSize: %s MsgClusterData: %s Model: >%s<" % (
        MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, _modelName), MsgSrcAddr, )

    # Hanlding Message from the Aqara Opple Switch 2,4,6 buttons
    if _modelName in ("lumi.remote.b686opcn01", "lumi.remote.b486opcn01", "lumi.remote.b286opcn01",):
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)
        AqaraOppleDecoding0012(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    elif aqara_button3_behaviour or _modelName in ("lumi.remote.b1acn01","lumi.remote.b28ac1", "lumi.remote.b186acn01","lumi.remote.b186acn02","lumi.remote.b286acn01","lumi.remote.b286acn02","lumi.remote.acn003"):
        # 0 -> Hold
        # 1 -> Short Release
        # 2 -> Double press
        # 255 -> Long Release
        value = int(decodeAttribute(self, MsgAttType, MsgClusterData))
        self.log.logging( "Cluster", "Debug", "ReadCluster - ClusterId=0012 - Switch Aqara: EP: %s Value: %s " % (
            MsgSrcEp, value), MsgSrcAddr, )
        if value == 0:
            value = 3

        # Force ClusterType Switch in order to behave as Switch
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006", str(value))
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, "0006", "0000", value)

    elif _modelName in ("lumi.sensor_switch.aq3", "lumi.sensor_switch.aq3t"):
        value = int(decodeAttribute(self, MsgAttType, MsgClusterData))
        self.log.logging( "Cluster", "Debug", "ReadCluster - ClusterId=0012 - Switch Aqara (AQ2): EP: %s Value: %s " % (
            MsgSrcEp, value), MsgSrcAddr, )

        # Store the value in Cluster 0x0006 (as well)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006", str(value))
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, "0006", "0000", value)

    elif _modelName in ("lumi.ctrl_ln2.aq1",):
        value = int(decodeAttribute(self, MsgAttType, MsgClusterData))
        self.log.logging( "Cluster", "Debug", "ReadCluster - ClusterId=0012 - Switch Aqara lumi.ctrl_ln2.aq1: EP: %s Attr: %s Value: %s " % (
            MsgSrcEp, MsgAttrID, value), MsgSrcAddr, )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

    elif _modelName in ("lumi.sensor_cube.aqgl01", "lumi.sensor_cube"):
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, cube_decode(self, MsgClusterData, MsgSrcAddr))

        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, cube_decode(self, MsgClusterData, MsgSrcAddr))
        self.log.logging( "Cluster", "Debug", "ReadCluster - ClusterId=0012 - reception Xiaomi Magic Cube Value: " + str(cube_decode(self, MsgClusterData, MsgSrcAddr)), MsgSrcAddr, )

    else:
        self.log.logging( "Cluster", "Log", "readCluster - %s - %s/%s unknown attribute: %s %s %s %s Model: %s" % (
            MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, _modelName), MsgSrcAddr, )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)


def Cluster0101(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):

    # Door Lock Cluster
    self.log.logging(
        "Cluster",
        "Debug",
        "ReadCluster 0101 - Dev: %s, EP:%s AttrID: %s, AttrType: %s, AttrSize: %s Attribute: %s Len: %s" % (MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, len(MsgClusterData)),
        MsgSrcAddr,
    )

    if MsgAttrID == "0000":  # Lockstate
        LOCKSTATE = {"00": "Not fully locked", "01": "Locked", "02": "Unlocked", "ff": "Undefined"}

        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)
        if MsgClusterData == "01":
            # Locked
            if "ZDeviceName" in self.ListOfDevices[MsgSrcAddr]:
                self.log.logging(
                    "Cluster",
                    "Status",
                    "%s DoorLock state %s (%s)" % (self.ListOfDevices[MsgSrcAddr]["ZDeviceName"], MsgClusterData, LOCKSTATE[MsgClusterData]),
                    MsgSrcAddr,
                )

            # Update the DoorLock widget seems to be inverted
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, "00")
            # Update the Door contact widget ( status )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0500", "00")

        elif MsgClusterData in ("00", "02", "ff"):
            # Not locked
            if "ZDeviceName" in self.ListOfDevices[MsgSrcAddr]:
                self.log.logging(
                    "Cluster",
                    "Status",
                    "%s DoorLock state %s (%s)" % (self.ListOfDevices[MsgSrcAddr]["ZDeviceName"], MsgClusterData, LOCKSTATE[MsgClusterData]),
                    MsgSrcAddr,
                )

            # Update the DoorLock widget seems to be inverted
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, "01")
            # Update the Door contact widget
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0500", "01")

        else:
            _context = create_context(MsgClusterId, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)
            self.log.logging(
                "Cluster",
                "Error",
                "ReadCluster 0101 - %s/%s Dev: Lock state %s " % (MsgSrcAddr, MsgSrcEp, MsgClusterData),
                MsgSrcAddr,
                _context,
            )

    elif MsgAttrID == "0001":  # Locktype
        self.log.logging("Cluster", "Debug", "ReadCluster 0101 - Dev: Lock type " + str(MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    elif MsgAttrID == "0002":  # Enabled
        self.log.logging("Cluster", "Debug", "ReadCluster 0101 - Dev: Enabled " + str(MsgClusterData), MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    # Aqara related
    elif MsgAttrID == "0055":  # Aqara Vibration: Vibration, Tilt, Drop
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster %s/%s - Aqara Vibration - Event: %s" % (MsgClusterId, MsgAttrID, MsgClusterData),
            MsgSrcAddr,
        )
        state = decode_vibr(MsgClusterData)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, state)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, state)

    elif MsgAttrID == "0503":  # Bed activties: Tilt angle
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster %s/%s -  Vibration Angle: %s" % (MsgClusterId, MsgAttrID, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

        if MsgClusterData == "0054":  # Following Tilt
            state = "10"
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, state)
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, state)

    elif MsgAttrID == "0505":  # Vibration Strenght
        # The vibration sensor has a function in the mihome app called "vibration curve"
        # with which I get a graph where I can see the value of "Strenght" as a function of time
        value = int(MsgClusterData, 16)
        strenght = (value >> 16) & 0xFFFF
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster %s/%s -  Vibration Strenght: %s %s %s" % (MsgClusterId, MsgAttrID, MsgClusterData, value, strenght),
            MsgSrcAddr,
        )
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "Strenght", str(strenght), Attribute_=MsgAttrID)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, strenght)

    elif MsgAttrID == "0508":  # Aqara Vibration / Liberation Mode / Orientation

        if len(MsgClusterData) != 12:
            # https://github.com/fairecasoimeme/ZiGate/issues/229
            self.log.logging( "Cluster", "Debug", "Needs Firmware 3.1b to decode this data")

        angleX, angleY, angleZ = decode_vibrAngle(MsgClusterData)

        self.log.logging(
            "Cluster",
            "Debug",
            " ReadCluster %s/%s - AttrType: %s AttrLenght: %s AttrData: %s Vibration ==> angleX: %s angleY: %s angleZ: %s" % (MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, angleX, angleY, angleZ),
            MsgSrcAddr,
        )
        MajDomoDevice(
            self,
            Devices,
            MsgSrcAddr,
            MsgSrcEp,
            "Orientation",
            "angleX: %s, angleY: %s, angleZ: %s" % (angleX, angleY, angleZ),
            Attribute_=MsgAttrID,
        )
        checkAndStoreAttributeValue(
            self,
            MsgSrcAddr,
            MsgSrcEp,
            MsgClusterId,
            MsgAttrID,
            "angleX: %s, angleY: %s, angleZ: %s" % (angleX, angleY, angleZ),
        )

    else:
        self.log.logging(
            "Cluster",
            "Log",
            "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
            MsgSrcAddr,
        )

        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)


def Cluster0201(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):

    # Thermostat cluster
    self.log.logging(
        "Cluster",
        "Debug",
        "ReadCluster - 0201 - %s/%s AttrId: %s AttrType: %s AttSize: %s Data: %s" % (MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
        MsgSrcAddr,
    )

    eurotronics = danfoss = False
    if "Manufacturer" in self.ListOfDevices[MsgSrcAddr]:
        if self.ListOfDevices[MsgSrcAddr]["Manufacturer"] == "1037":
            eurotronics = True
        elif self.ListOfDevices[MsgSrcAddr]["Manufacturer"] == "1246":
            danfoss = True

    if "Manufacturer Name" in self.ListOfDevices[MsgSrcAddr]:
        if self.ListOfDevices[MsgSrcAddr]["Manufacturer Name"] == "Eurotronic":
            eurotronics = True
        elif self.ListOfDevices[MsgSrcAddr]["Manufacturer Name"] == "Danfoss":
            danfoss = True

    value = decodeAttribute(self, MsgAttType, MsgClusterData)

    if MsgAttrID == "0000":  # Local Temperature (Zint16)
        if "Model" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Model"] == "VOC_Sensor":
            return
        ValueTemp = round(int(value) / 100, 2)
        if "Model" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Model"] == "TAFFETAS2 D1.00P1.01Z1.00":
            # This is use to communicate the SetPoint, so let's update the SetPoint on Cluster Thermostat
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, "0201", "0012", int(value))
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0201", ValueTemp, Attribute_="0012")
        else:
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0402", ValueTemp)
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, ValueTemp)
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, "0402", "0000", ValueTemp)
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Local Temp: %s" % ValueTemp, MsgSrcAddr)

    elif MsgAttrID == "0001":  # Outdoor Temperature
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - %s - %s/%s Outdoor Temp: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    elif MsgAttrID == "0002":  # Occupancy
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - %s - %s/%s Occupancy: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    elif MsgAttrID == "0003":  # Min Heat Setpoint Limit
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - %s - %s/%s Min Heat Setpoint Limit: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    elif MsgAttrID == "0004":  # Max Heat Setpoint Limit
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - %s - %s/%s Max Heat Setpoint Limit: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    elif MsgAttrID == "0005":  # Min Cool Setpoint Limit
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - %s - %s/%s Min Cool Setpoint Limit: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    elif MsgAttrID == "0006":  # Max Cool Setpoint Limit
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - %s - %s/%s Max Cool Setpoint Limit: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    elif MsgAttrID == "0007":  # Pi Cooling Demand  (valve position %)
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - %s - %s/%s Pi Cooling Demand: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    elif MsgAttrID == "0008":  # Pi Heating Demand  (valve position %)
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - %s - %s/%s Pi Heating Demand: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )
        if "Model" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Model"] in ("EH-ZB-VACT", 'iTRV'):
            receiving_heatingdemand_attribute( self, Devices, MsgSrcAddr, MsgSrcEp, value, MsgClusterId, MsgAttrID)
            
        # Per standard the demand is expressed in % between 0x00 to 0x64
        if eurotronics:
            value = ( value * 100 ) // 255
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0201", value, Attribute_="0008")

    elif MsgAttrID == "0009":  # HVAC System Type Config
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - %s - %s/%s HVAC System Type Config: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    elif MsgAttrID == "0010":  # Calibration / Adjustement
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Calibration: %s" % value, MsgSrcAddr)
        if value not in range(0x00, 0x19):
            # We are in Negative value. 0xE7 = -25 0xff = -01 )
            value = -(0xFF + 1 - value)
        value = round(value / 10, 2)
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Calibration: %s" % value, MsgSrcAddr)
        if "Model" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Model"] == "EH-ZB-VACT":
            if "Schneider" not in self.ListOfDevices[MsgSrcAddr]:
                self.ListOfDevices[MsgSrcAddr]["Schneider"] = {}
            self.ListOfDevices[MsgSrcAddr]["Schneider"]["Calibration"] = value
        if "Thermostat" not in self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]["Thermostat"] = {}
        self.ListOfDevices[MsgSrcAddr]["Thermostat"]["Calibration"] = value
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

    elif MsgAttrID == "0011":  # Cooling Setpoint (Zinte16)
        ValueTemp = round(int(value) / 100, 1)
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Cooling Setpoint: %s" % ValueTemp, MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, ValueTemp)

        if self.ListOfDevices[MsgSrcAddr]["Model"] in ("AC211", "AC221", "CAC221"):
            # We do report if AC211 and AC in Cool mode
            if MsgClusterId in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]:
                if "001c" in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId]:
                    if self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId]["001c"] in (0x03, 0x01):
                        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, ValueTemp, Attribute_="0012")

    elif MsgAttrID == "0012":  # Heat Setpoint (Zinte16)
        ValueTemp = round(int(value) / 100, 2)
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Heating Setpoint: %s ==> %s" % (value, ValueTemp), MsgSrcAddr)
        

        if "Model" in self.ListOfDevices[MsgSrcAddr]:
            if self.ListOfDevices[MsgSrcAddr]["Model"] == "AC201A":
                # We do not report this, as AC201 rely on 0xffad cluster
                checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, int(value))
                pass

            elif self.ListOfDevices[MsgSrcAddr]["Model"] in ("AC211", "AC221", "CAC221"):
                checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, int(value))
                # We do report if AC211 and AC in Heat mode
                if MsgClusterId in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp]:
                    if "001c" in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId]:
                        if self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId]["001c"] in (0x04, 0x01):
                            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, ValueTemp, Attribute_=MsgAttrID)

            elif self.ListOfDevices[MsgSrcAddr]["Model"] in ("EH-ZB-VACT", 'iTRV'):
                # In case of Schneider Wiser Valve, 
                receiving_heatingpoint_attribute( self, Devices, MsgSrcAddr, MsgSrcEp, ValueTemp, value, MsgClusterId, MsgAttrID)

            elif self.ListOfDevices[MsgSrcAddr]["Model"] != "SPZB0001":
                checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, int(value))
                # In case it is not a Eurotronic, let's Update heatPoint
                # As Eurotronics will rely on 0x4003 attributes
                self.log.logging(
                    "Cluster",
                    "Debug",
                    "ReadCluster - 0201 - Request update on Domoticz %s not a Schneider, not a Eurotronics" % MsgSrcAddr,
                    MsgSrcAddr,
                )
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, ValueTemp, Attribute_=MsgAttrID)
            else:
                checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, int(value))
        else:
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, int(value))

    elif MsgAttrID == "0014":  # Unoccupied Heating
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Unoccupied Heating:  %s" % value, MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

    elif MsgAttrID == "0015":  # MIN_HEAT_SETPOINT_LIMIT
        ValueTemp = round(int(value) / 100, 1)
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Min SetPoint: %s" % ValueTemp, MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, ValueTemp)

    elif MsgAttrID == "0016":  # MAX_HEAT_SETPOINT_LIMIT
        ValueTemp = round(int(value) / 100, 1)
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Max SetPoint: %s" % ValueTemp, MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, ValueTemp)

    elif MsgAttrID == "001a":  # Remote Sensing
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - %s - %s/%s Remote Sensing: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )

    elif MsgAttrID == "0025":  # Scheduler state
        # Bit #0 => disable/enable Scheduler
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Scheduler state:  %s" % value, MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

    elif MsgAttrID == "0029":  # Heating operation state
        # bit #0 heat On/Off state
        # bit #1 cool on/off state
        # Maj HeatingStatus
        value = 1 if int(value) else 0
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0201", value, Attribute_="0124")

        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Heating operation state:  %s" % value, MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

    elif MsgAttrID == "0045":  # ACLouverPosition
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - ACLouverPosition:  %s" % value, MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

    elif MsgAttrID == "001b":  # Control Sequence Operation

        # NOT USED
        # SEQ_OPERATION = {
        #     "00": "Cooling",
        #     "01": "Cooling with reheat",
        #     "02": "Heating",
        #     "03": "Heating with reheat",
        #     "04": "Cooling and heating",
        #     "05": "Cooling and heating with reheat",
        # }
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster %s - %s/%s Control Sequence Operation: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    elif MsgAttrID == "001c":  # System Mode
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - System Mode: %s" % (value), MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)     
        #if (
        #    value == 0x01  # Auto
        #    and "Model" in self.ListOfDevices[MsgSrcAddr]
        #    and self.ListOfDevices[MsgSrcAddr]["Model"] in ("AC211", "AC221", "CAC221")
        #    and "Param" in self.ListOfDevices[ MsgSrcAddr ] 
        #    and "CAC221ForceAuto2Off" in self.ListOfDevices[ MsgSrcAddr ]["Param"] 
        #    and self.ListOfDevices[ MsgSrcAddr ]["Param"]["CAC221ForceAuto2Off"]
        #):
        #    self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - System Mode: %s Forcing Mode to Off (CasaIA CAC221)" % (value), MsgSrcAddr)
        #    value = 0x00
        #    self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - System Mode: %s" % (value), MsgSrcAddr)
        #    checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)  
            
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value, Attribute_=MsgAttrID)

        # We shoudl also force Shutdown of FanControl and eventualy Wing
        if value == 0x00 and "Model" in self.ListOfDevices[MsgSrcAddr] and self.ListOfDevices[MsgSrcAddr]["Model"] in ("AC211", "AC221", "CAC221"):
            # Shutdown the other widgets
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0202", "%02x" % 0x0)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, "%02x" % 0x0, Attribute_="fd00")

    elif MsgAttrID == "001d":
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Alarm Mask: %s" % value, MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

    elif MsgAttrID == "0403":
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Attribute 403: %s" % value, MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

    elif MsgAttrID == "0405":
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - 0201 - Attribute 405 ( thermostat mode ?=regulator mode For Elko) : %s" % value,
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

    elif MsgAttrID == "0406":
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Attribute 406 : %s" % value, MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

    elif MsgAttrID == "0408":
        value = int(decodeAttribute(self, MsgAttType, MsgClusterData))
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - 0201 - Attribute 408 ( Elko power consumption in last 10 minutes): %s" % value,
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

    elif MsgAttrID == "0409":
        value = int(decodeAttribute(self, MsgAttType, MsgClusterData))
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Attribute 409: %s" % value, MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

    elif MsgAttrID in ("4000", "4001", "4002", "4003", "4008") and eurotronics:

        # Eurotronic SPZB Specifics
        if MsgAttrID == "4000":  # TRV Mode for EUROTRONICS
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - 0201 - %s/%s TRV Mode: %s" % (MsgSrcAddr, MsgSrcEp, value),
                MsgSrcAddr,
            )
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

        elif MsgAttrID == "4001":  # Valve position for EUROTRONICS
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - 0201 - %s/%s Valve position: %s" % (MsgSrcAddr, MsgSrcEp, value),
                MsgSrcAddr,
            )
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0201", int(value, 16), Attribute_="4001")

        elif MsgAttrID == "4002":  # Erreors for EUROTRONICS
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - 0201 - %s/%s Status: %s" % (MsgSrcAddr, MsgSrcEp, value),
                MsgSrcAddr,
            )
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

        elif MsgAttrID == "4003":  # Current Temperature Set point for EUROTRONICS
            setPoint = ValueTemp = round(int(value) / 100, 2)
            if "0012" in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId]:
                setPoint = self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId]["0012"]
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - 0201 - %s/%s Current Temp Set point: %s versus %s " % (MsgSrcAddr, MsgSrcEp, ValueTemp, setPoint),
                MsgSrcAddr,
            )
            if ValueTemp != float(setPoint):
                # Seems that there is a local setpoint
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0201", ValueTemp, Attribute_=MsgAttrID)
                checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, ValueTemp)
                checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, "0012", ValueTemp)

        elif MsgAttrID == "4008":  # Host Flags for EUROTRONICS

            # 0x00000005 ==> Boost
            # 0x00000001 ==> Normal
            # 0x00000011 ==> Window Detection

            # NOT USED
            # HOST_FLAGS = {
            #     0x000001: "???",
            #     0x000002: "Display Flipped",
            #     0x000004: "Boost mode",
            #     0x000010: "disable off mode",
            #     0x000020: "enable off mode",
            #     0x000080: "child lock",
            # }

            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster - 0201 - %s/%s Host Flags: %s" % (MsgSrcAddr, MsgSrcEp, value),
                MsgSrcAddr,
            )
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

            if (int(value, 16) & 0x000010) == 0x00000010:
                # Window Detection
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0500", "01")
            if (int(value, 16) & 0x000010) == 0x0:
                # Window Detection
                MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0500", "00")

    elif MsgAttrID in ("4000", "4003", "4010", "4011", "4012", "4013", "4014", "4015", "4020", "4030", "4031") and danfoss:
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

        if MsgAttrID == "4000" and self.ListOfDevices[MsgSrcAddr]["Model"] in ("eTRV0100"):
            # Open Window Detection for Danfoss eTRV
            if value in [ 3, 4 ]:
                value = "01"
            else:
                value = "00"
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0500", value)
        if MsgAttrID == "4003" and self.ListOfDevices[MsgSrcAddr]["Model"] in ("eTRV0100", "eT093WRO"):
            # External Open Window Detection for Danfoss eTRV
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0500", value)

    elif MsgAttrID in ("e010", "e011", "e012", "e013", "e014", "e030", "e031", "e020"):
        if MsgAttrID == "e010":  # Schneider Thermostat Mode
            THERMOSTAT_MODE = {
                "00": "Mode Off",
                "01": "Manual",
                "02": "Schedule",
                "03": "Energy Saver",
                "04": "Schedule Ebergy Saver",
                "05": "Holiday Off",
                "06": "Holiday Frost Protection",
            }

            if MsgClusterData in THERMOSTAT_MODE:
                self.log.logging(
                    "Cluster",
                    "Debug",
                    "readCluster - %s - %s/%s Schneider Thermostat Mode %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, THERMOSTAT_MODE[MsgClusterData]),
                    MsgSrcAddr,
                )
            else:
                self.log.logging(
                    "Cluster",
                    "Debug",
                    "readCluster - %s - %s/%s Schneider Thermostat Mode 0xe010 %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
                    MsgSrcAddr,
                )

            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0201", MsgClusterData, Attribute_=MsgAttrID)
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

        elif MsgAttrID == "e011":  # hact mode : fip or conventional and heating mode : fip or setpoint
            self.log.logging(
                "Cluster",
                "Debug",
                "readCluster - %s - %s/%s Schneider ATTRIBUTE_THERMOSTAT_HACT_CONFIG  %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
                MsgSrcAddr,
            )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0201", MsgClusterData, Attribute_=MsgAttrID)
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

        elif MsgAttrID == "e012":  # 57362, ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_STATUS
            self.log.logging(
                "Cluster",
                "Debug",
                "readCluster - %s - %s/%s Schneider ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_STATUS  %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
                MsgSrcAddr,
            )
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0500", MsgClusterData)

        elif MsgAttrID == "e013":  # 57363, ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_THRESHOLD
            self.log.logging(
                "Cluster",
                "Debug",
                "readCluster - %s - %s/%s Schneider ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_THRESHOLD  %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
                MsgSrcAddr,
            )
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

        elif MsgAttrID == "e014":  # 57364, ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_INTERVAL
            self.log.logging(
                "Cluster",
                "Debug",
                "readCluster - %s - %s/%s Schneider ATTRIBUTE_THERMOSTAT_OPEN_WINDOW_DETECTION_INTERVAL  %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
                MsgSrcAddr,
            )
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

        elif MsgAttrID == "e020":  # fip mode
            self.log.logging(
                "Cluster",
                "Debug",
                "readCluster - %s - %s/%s Schneider FIP mode  %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
                MsgSrcAddr,
            )
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0201", MsgClusterData, Attribute_=MsgAttrID)

        elif MsgAttrID == "e030":
            self.log.logging(
                "Cluster",
                "Debug",
                "readCluster - %s - %s/%s Schneider Valve Position  %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
                MsgSrcAddr,
            )
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0201", value, Attribute_="0008")

        elif MsgAttrID == "e031":
            self.log.logging(
                "Cluster",
                "Debug",
                "readCluster - %s - %s/%s Schneider Valve Calibration Status %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData),
                MsgSrcAddr,
            )
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    elif MsgAttrID == "fd00":
        # Casia.IA / Wing On/off
        self.log.logging("Cluster", "Debug", "ReadCluster - 0201 - Attribute fd00 (Wing): %s" % value, MsgSrcAddr)
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, value, Attribute_=MsgAttrID)

    else:
        self.log.logging(
            "Cluster",
            "Debug",
            "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
            MsgSrcAddr,
        )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)


def Cluster0500(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):

    """
    Cluster: Security & Safety IAZ Zone
    https://www.nxp.com/docs/en/user-guide/JN-UG-3077.pdf ( section 26.2 )
    """
    if MsgClusterData == "":
        return

    self.log.logging(
        "Cluster",
        "Debug",
        "ReadCluster0500 - Security & Safety IAZ Zone - Device: %s/%s  MsgAttrID: %s MsgAttType: %s MsgAttSize: %s MsgClusterData: %s" % (MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
        MsgSrcAddr,
    )

    checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

    if "IAS" not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]["IAS"] = {}

    if MsgSrcEp not in self.ListOfDevices[MsgSrcAddr]["IAS"]:
        self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp] = {}
        self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["EnrolledStatus"] = {}
        self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneType"] = {}
        self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneTypeName"] = {}
        self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"] = {}

    if not isinstance(self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"], dict):
        self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"] = {}

    if MsgAttrID == "0000":  # ZoneState ( 0x00 Not Enrolled / 0x01 Enrolled )
        if int(MsgClusterData, 16) == 0x00:
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster0500 - Device: %s/%s NOT ENROLLED (0x%02d)" % (MsgSrcAddr, MsgSrcEp, int(MsgClusterData, 16)),
                MsgSrcAddr,
            )
            self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["EnrolledStatus"] = int(MsgClusterData, 16)
        elif int(MsgClusterData, 16) == 0x01:
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster0500 - Device: %s/%s ENROLLED (0x%02d)" % (MsgSrcAddr, MsgSrcEp, int(MsgClusterData, 16)),
                MsgSrcAddr,
            )
            self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["EnrolledStatus"] = int(MsgClusterData, 16)


    elif MsgAttrID == "0001":  # ZoneType
        if int(MsgClusterData, 16) in ZONE_TYPE:
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster0500 - Device: %s/%s - ZoneType: %s" % (MsgSrcAddr, MsgSrcEp, ZONE_TYPE[int(MsgClusterData, 16)]),
                MsgSrcAddr,
            )
            self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneType"] = int(MsgClusterData, 16)
            self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneTypeName"] = ZONE_TYPE[int(MsgClusterData, 16)]
        else:

            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster0500 - Device: %s/%s - Unknown ZoneType: %s" % (MsgSrcAddr, MsgSrcEp, MsgClusterData),
                MsgSrcAddr,
            )

    elif MsgAttrID == "0002":  # Zone Status
        if MsgClusterData != "" and MsgAttType in ("19", "21"):
            alarm1 = int(MsgClusterData, 16) & 0b0000000000000001
            alarm2 = (int(MsgClusterData, 16) & 0b0000000000000010) >> 1
            tamper = (int(MsgClusterData, 16) & 0b0000000000000100) >> 2
            batter = (int(MsgClusterData, 16) & 0b0000000000001000) >> 3
            srepor = (int(MsgClusterData, 16) & 0b0000000000010000) >> 4
            rrepor = (int(MsgClusterData, 16) & 0b0000000000100000) >> 5
            troubl = (int(MsgClusterData, 16) & 0b0000000001000000) >> 6
            acmain = (int(MsgClusterData, 16) & 0b0000000010000000) >> 7
            test = (int(MsgClusterData, 16) & 0b0000000100000000) >> 8
            batdef = (int(MsgClusterData, 16) & 0b0000001000000000) >> 9
            doorbell = (int(MsgClusterData, 16) & 0b1000000000000000) >> 15

            self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId][MsgAttrID] = "alarm1: %s, alarm2: %s, tamper: %s, batter: %s, srepor: %s, rrepor: %s, troubl: %s, acmain: %s, test: %s, batdef: %s, doorbell: %s" % (
                alarm1,
                alarm2,
                tamper,
                batter,
                srepor,
                rrepor,
                troubl,
                acmain,
                test,
                batdef,
                doorbell
            )
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster 0500/0002 - IAS Zone - Device:%s status alarm1: %s, alarm2: %s, tamper: %s, batter: %s, srepor: %s, rrepor: %s, troubl: %s, acmain: %s, test: %s, batdef: %s, doorbell: %s"
                % (MsgSrcAddr, alarm1, alarm2, tamper, batter, srepor, rrepor, troubl, acmain, test, batdef, doorbell),
                MsgSrcAddr,
            )

            if "IAS" in self.ListOfDevices[MsgSrcAddr] and MsgSrcEp in self.ListOfDevices[MsgSrcAddr]["IAS"] and "ZoneStatus" in self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]:
                self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"]["alarm1"] = alarm1
                self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"]["alarm2"] = alarm2
                self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"]["tamper"] = tamper
                self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"]["battery"] = batter
                self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"]["Support Reporting"] = srepor
                self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"]["Restore Reporting"] = rrepor
                self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"]["trouble"] = troubl
                self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"]["acmain"] = acmain
                self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"]["test"] = test
                self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"]["battdef"] = batdef
                self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"]["doorbell"] = doorbell

            self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"]["GlobalInfos"] = "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s" % (
                alarm1, alarm2, tamper, batter, srepor, rrepor, troubl, acmain, test, batdef, doorbell )
            
            self.ListOfDevices[MsgSrcAddr]["IAS"][MsgSrcEp]["ZoneStatus"]["TimeStamp"] = int(time())
            model = self.ListOfDevices[MsgSrcAddr].get("Model", "")
            if model in ("RC-EF-3.0", "RC-EM"):   # alarm1 or alarm2 not used on thoses devices
                return
            
            ias_alarm1_2_merged = get_deviceconf_parameter_value( self, model, "IASAlarmMerge", return_default=None )
            self.log.logging( "Input", "Debug", "IASAlarmMerge = %s" % (ias_alarm1_2_merged))

            if ias_alarm1_2_merged:
                self.log.logging( "Input", "Debug", "IASAlarmMerge alarm1 %s alarm2 %s" % (alarm1, alarm2))
                combined_alarm = ( alarm2 << 1 ) | alarm1
                self.log.logging( "Input", "Debug", "IASAlarmMerge combined value = %02d" % (combined_alarm))
            else:
                combined_alarm = alarm1 or alarm2 or doorbell

            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, "%02d" % (combined_alarm))

            if batter:
                # Battery Warning
                self.log.logging(
                    "Input",
                    "Log",
                    "Decode8401 Low Battery or defective battery: Device: %s %s/%s" % (MsgSrcAddr, batdef, batter),
                    MsgSrcAddr,
                )
                self.ListOfDevices[MsgSrcAddr]["IASBattery"] = 5
            else:
                # Battery Ok
                self.ListOfDevices[MsgSrcAddr]["IASBattery"] = 100  # set to 100%


        else:
            self.log.logging(
                "Cluster",
                "Debug",
                "ReadCluster0500 - Device: %s empty data: %s" % (MsgSrcAddr, MsgClusterData),
                MsgSrcAddr,
            )

    elif MsgAttrID == "0010":  # IAS CIE Address
        self.log.logging("Cluster", "Debug", "ReadCluster0500 - IAS CIE Address: %s" % MsgClusterData, MsgSrcAddr)

    elif MsgAttrID == "0011":  # Zone ID
        self.log.logging("Cluster", "Debug", "ReadCluster0500 - ZoneID : %s" % MsgClusterData, MsgSrcAddr)

    elif MsgAttrID == "0013":  # CurrentZoneSensitivityLevel
        self.log.logging("Cluster", "Debug", "ReadCluster0500 - CurrentZoneSensitivityLevel : %s" % MsgClusterData, MsgSrcAddr)

    elif MsgAttrID == "f001":  # Tuya Keep Time Lookup
        self.log.logging("Cluster", "Debug", "ReadCluster0500 - TuyaKeepTimeLookup : %s" % MsgClusterData, MsgSrcAddr)
    
    else:
        self.log.logging(
            "Cluster",
            "Log",
            "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
            MsgSrcAddr,
        )

    self.log.logging("Cluster", "Debug", "ReadCluster0500 - Device: %s Data: %s" % (MsgSrcAddr, MsgClusterData), MsgSrcAddr)


def Cluster0502(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):

    self.log.logging(
        "Cluster",
        "Debug",
        "ReadCluster0502 - Security & Safety IAZ Zone - Device: %s MsgAttrID: %s MsgAttType: %s MsgAttSize: %s MsgClusterData: %s" % (MsgSrcAddr, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
        MsgSrcAddr,
    )

    checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, str(decodeAttribute(self, MsgAttType, MsgClusterData)))

    if MsgAttrID == "0000":  # Max Duration
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - 0502 - %s/%s Max Duration: %s" % (MsgSrcAddr, MsgSrcEp, str(decodeAttribute(self, MsgAttType, MsgClusterData))),
            MsgSrcAddr,
        )
        if "IAS WD" not in self.ListOfDevices[MsgSrcAddr]:
            self.ListOfDevices[MsgSrcAddr]["IAS WD"] = {}
        self.ListOfDevices[MsgSrcAddr]["IAS WD"]["MaxDuration"] = decodeAttribute(self, MsgAttType, MsgClusterData)

    elif MsgAttrID == "f000":
        # Looks like a reporting from the TS0216 / _TYZB01_8scntis1 - Heiman looks like Alarm
        # 0x00: Off
        # 0x01: Alarm
        # 0x02: Strobe
        # 0x03: Alarm + Strobe
        RPT_ATTR_WIDGET = {
            "00": "00",
            "01": "20",
            "02": "30",
            "03": "10"
        }
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - 0502 - %s/%s  %s %s %s %s" % (MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
            MsgSrcAddr,
        )
        if MsgClusterData not in RPT_ATTR_WIDGET:
            return

        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, RPT_ATTR_WIDGET[MsgClusterData ])
        

    elif MsgAttrID == "fffd":
        self.log.logging(
            "Cluster",
            "Debug",
            "ReadCluster - 0502 - %s/%s unknown attribute: %s %s %s %s" % (MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
            MsgSrcAddr,
        )

    else:
        self.log.logging(
            "Cluster",
            "Log",
            "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
            MsgSrcAddr,
        )


def Cluster0702(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):

    # Smart Energy Metering
    if int(MsgAttSize, 16) == 0:
        self.log.logging("Cluster", "Debug", "Cluster0702 - empty message ", MsgSrcAddr)
        return

    checkAttribute(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID)

    if not checkValidValue(self, MsgSrcAddr, MsgAttType, MsgClusterData):
        self.log.logging( "Cluster", "Error", "Cluster0702 - MsgAttrID: %s MsgAttType: %s DataLen: %s : invalid Data Value found : %s" % (
            MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr, )
        return

    value = decodeAttribute(self, MsgAttType, MsgClusterData)
    if MsgAttType not in ("41", "42"):
        # Convert to int
        value = int(value)

    self.log.logging( "Cluster", "Debug", "Cluster0702 - MsgAttrID: %s MsgAttType: %s DataLen: %s Data: %s decodedValue: %s" % (
        MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value), MsgSrcAddr, )

    if MsgAttrID in ( "5000", "5001", "5101", "5121", "5500", "5501", "5601", "5622", "5a20", "5a22", "e200", "e201", "e202", ):
        ELECTRICAL_MEASURES = {
            "5000": "electricCurrentMultiplier",
            "5001": "electricCurrentDivisor",
            "5121": "maxCurrentBeforeAlarm",
            "e200": "ctStatusRegister",
            "e201": "ctPowerConfiguration",
            "e202": "ctCalibrationMultiplier",
        }

        if MsgAttrID in ELECTRICAL_MEASURES:
            self.log.logging(
                "Cluster",
                "Debug",
                "Cluster0702 - %s/%s Schneider %s : %s " % (MsgSrcAddr, MsgSrcEp, ELECTRICAL_MEASURES[MsgAttrID], value),
                MsgSrcAddr,
            )
            checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)
        else:
            self.log.logging(
                "Cluster",
                "Debug",
                "readCluster - %s - %s/%s Schneider Attribute: %s  Raw Data: %s Decoded Data: %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgClusterData, value),
                MsgSrcAddr,
            )

    elif MsgAttrID in ("2000","2001","2002","2100","2101","2102","2103","3000","3001","3002", "3100","3101","3102","3103","4000","4001","4002","4100","4101","4102","4103","4104","4105","4106",):
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)
        # Report Line 1 on fake Ep "f1"
        # Report Line 2 on fake Ep "f2"
        # Report Line 3 on fake Ep "f3"

        if MsgAttrID in ("2000", "2001", "2002"):  # Lx phase Power
            line = 1 + (int(MsgAttrID, 16) - 0x2000)
            fake_ep = "f%s" % line
            conso = compute_metering_conso(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)

            checkAndStoreAttributeValue(self, MsgSrcAddr, fake_ep, MsgClusterId, MsgAttrID, str(conso))
            self.ListOfDevices[MsgSrcAddr]["Ep"][fake_ep][MsgClusterId]["0400"] = str(conso)

            self.log.logging(
                "Cluster",
                "Debug",
                "readCluster - %s - %s/%s CASAIA PC321 phase Power Line: %s Power %s" % (MsgClusterId, MsgSrcAddr, fake_ep, line, conso),
            )
            MajDomoDevice(self, Devices, MsgSrcAddr, fake_ep, MsgClusterId, str(conso))

        elif MsgAttrID in ("2100", "2101", "2102"):  # Reactive Power
            line = 1 + (int(MsgAttrID, 16) - 0x2100)
            fake_ep = "f%s" % line
            conso = compute_metering_conso(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, "0400", value)
            checkAndStoreAttributeValue(self, MsgSrcAddr, fake_ep, MsgClusterId, MsgAttrID, str(conso))

        elif MsgAttrID in ("3000", "3001", "3002"):  # Lx Voltage
            line = 1 + (int(MsgAttrID, 16) - 0x3000)
            fake_ep = "f%s" % line
            value /= 10

            checkAndStoreAttributeValue(self, MsgSrcAddr, fake_ep, MsgClusterId, MsgAttrID, str(value))
            if "0001" not in self.ListOfDevices[MsgSrcAddr]["Ep"][fake_ep]:
                self.ListOfDevices[MsgSrcAddr]["Ep"][fake_ep]["0001"] = {}
            self.ListOfDevices[MsgSrcAddr]["Ep"][fake_ep]["0001"]["0000"] = str(value)

            self.log.logging(
                "Cluster",
                "Debug",
                "readCluster - %s - %s/%s CASAIA PC321 phase Power Line: %s Voltage %s" % (MsgClusterId, MsgSrcAddr, fake_ep, line, value),
            )
            MajDomoDevice(self, Devices, MsgSrcAddr, fake_ep, "0001", str(value))

        elif MsgAttrID in ("3100", "3101", "3102"):  # Lx Current/Ampere
            line = 1 + (int(MsgAttrID, 16) - 0x3100)
            fake_ep = "f%s" % line
            value /= 1000

            checkAndStoreAttributeValue(self, MsgSrcAddr, fake_ep, MsgClusterId, MsgAttrID, str(value))
            if "0b04" not in self.ListOfDevices[MsgSrcAddr]["Ep"][fake_ep]:
                self.ListOfDevices[MsgSrcAddr]["Ep"][fake_ep]["0b04"] = {}
            self.ListOfDevices[MsgSrcAddr]["Ep"][fake_ep]["0b04"]["0508"] = str(value)

            self.log.logging(
                "Cluster",
                "Debug",
                "readCluster - %s - %s/%s CASAIA PC321 phase Power Line: %s Current %s" % (MsgClusterId, MsgSrcAddr, fake_ep, line, value),
            )
            MajDomoDevice(self, Devices, MsgSrcAddr, fake_ep, "0b04", str(value), Attribute_="0508")

        elif MsgAttrID in ("4000", "4001", "4002"):  # Lx Energy Consuption (Meter)
            line = 1 + (int(MsgAttrID, 16) - 0x4000)
            fake_ep = "f%s" % line
            conso = compute_metering_conso(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, "0000", value)

            checkAndStoreAttributeValue(self, MsgSrcAddr, fake_ep, MsgClusterId, MsgAttrID, str(value))
            self.ListOfDevices[MsgSrcAddr]["Ep"][fake_ep][MsgClusterId]["0000"] = str(conso)

            self.log.logging(
                "Cluster",
                "Debug",
                "readCluster - %s - %s/%s CASAIA PC321 phase Power Line: %s Summation Power %s" % (MsgClusterId, MsgSrcAddr, fake_ep, line, conso),
            )
            MajDomoDevice(self, Devices, MsgSrcAddr, fake_ep, "0702", str(conso), Attribute_="0000")

        elif MsgAttrID in ("4100", "4101", "4102"):  # Reactive energy summation
            line = 1 + (int(MsgAttrID, 16) - 0x4100)
            fake_ep = "f%s" % line
            conso = compute_metering_conso(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, "0000", value)
            checkAndStoreAttributeValue(self, MsgSrcAddr, fake_ep, MsgClusterId, MsgAttrID, str(conso))

        else:

            self.log.logging(
                "Cluster",
                "Debug",
                "readCluster - %s - %s/%s CASAIA PC321 phase Power Clamp: %s %s %s %s (value: %s)" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, value),
                MsgSrcAddr,
            )

    else:
        self.log.logging( "Cluster", "Log", "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " % (
            MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData), MsgSrcAddr, )
        checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, value)


def Clusterfe03(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):
    # Schneider Wiser (new)
    # Cluster 0xfe03
    # Manuf Id: 0x105e
    # Attribut: 0x20
    #  - UI,ButtonPressPlusDown
    #  - UI,ScreenWake
    #  - UI,ButtonPressMinusDown
    #  - UI,ScreenSleep
    #  - UI,ButtonPressCenterDown
    #  - UI,ButtonPressPlusDown
    #  - ENV,-32768,2637,4777
    model_name = pre_process_cluster_message(self, MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)


def Clusterfc00(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):
    model_name = pre_process_cluster_message(self, MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)

    if MsgAttrID not in ("0001", "0002", "0003", "0004"):
        _context = create_context(MsgClusterId, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)
        self.log.logging(
            "Cluster",
            "Error",
            "readCluster - %s - %s/%s unknown attribute: %s %s %s %s " % (MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData),
            MsgSrcAddr,
            _context,
        )
        return

    if model_name == "ROM001":
        if MsgAttrID == "0001":  # On button
            self.log.logging( "Cluster", "Debug", "ReadCluster - %s - %s/%s - ON Button detected" % (MsgClusterId, MsgSrcAddr, MsgSrcEp), MsgSrcAddr, )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0008", "on")
        elif MsgAttrID == "0004":  # Off  Button
            self.log.logging( "Cluster", "Debug", "ReadCluster - %s - %s/%s - Off Button detected" % (MsgClusterId, MsgSrcAddr, MsgSrcEp), MsgSrcAddr, )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0008", "off")
        elif MsgAttrID == "0002":  # Dim+
            self.log.logging( "Cluster", "Debug", "ReadCluster - %s - %s/%s - Dim+ Button detected" % (MsgClusterId, MsgSrcAddr, MsgSrcEp), MsgSrcAddr, )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0008", "moveup")
        elif MsgAttrID == "0003":  # Dim-
            self.log.logging( "Cluster", "Debug", "ReadCluster - %s - %s/%s - Dim- Button detected" % (MsgClusterId, MsgSrcAddr, MsgSrcEp), MsgSrcAddr, )
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0008", "movedown")
        return

    if get_deviceconf_parameter_value(self, self.ListOfDevices[MsgSrcAddr]["Model"], "HUE_RWL"):
        philips_dimmer_switch(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)
    

def pre_process_cluster_message(self, MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData):
    """pre-process a clustre/attribuute and return model name"""
    log_message = f"ReadCluster {MsgClusterId} - {MsgSrcAddr}/{MsgSrcEp} Attribute: {MsgAttrID} Type: {MsgAttType} Size: {MsgAttSize} Data: {MsgClusterData}"
    self.log.logging("Cluster", "Debug", log_message, MsgSrcAddr)

    checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, decodeAttribute(self, MsgAttType, MsgClusterData))

    return self.ListOfDevices.get(MsgSrcAddr, {}).get("Model")


def Clusterfc01(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):
    model = pre_process_cluster_message(self, MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)
    if model is None:
        return

    if "Legrand" not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]["Legrand"] = {}

    if MsgAttrID == "0000":
        if model == "Dimmer switch wo neutral":
            # Enable Dimmer  ( 16bitData)
            if MsgClusterData == "0101":
                # '0101' # Enable Dimmer
                self.ListOfDevices[MsgSrcAddr]["Legrand"]["EnableDimmer"] = 1
            else:
                # '0100' # Disable Dimmer
                self.ListOfDevices[MsgSrcAddr]["Legrand"]["EnableDimmer"] = 0

        elif model == "Cable outlet":
            # 0200 FIP
            # 0100 Normal
            # Legrand Fil Pilote ( 16bitData) 1-Enable, 2-Disable
            self.ListOfDevices[MsgSrcAddr]["Legrand"]["LegrandFilPilote"] = int(MsgClusterData, 16)
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)

    elif MsgAttrID == "0001":
        if model == "Dimmer switch wo neutral":
            # Enable Led in Dark
            self.ListOfDevices[MsgSrcAddr]["Legrand"]["EnableLedInDark"] = int(MsgClusterData, 16)

        elif model == "Shutter switch with neutral":
            # Enable Led Shutter
            self.ListOfDevices[MsgSrcAddr]["Legrand"]["EnableLedShutter"] = int(MsgClusterData, 16)

    elif MsgAttrID == "0002":
        if model in [
            "Dimmer switch wo neutral",
            "Connected outlet",
            "Mobile outlet",
        ]:
            # Enable Led if On
            self.ListOfDevices[MsgSrcAddr]["Legrand"]["EnableLedIfOn"] = int(MsgClusterData, 16)


def Clusterfc03(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):
    # Philips cluster - NOT IMPLEMENTED
    model = pre_process_cluster_message(self, MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)
    if model is None:
        return


def Clusterfc40(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):
    model = pre_process_cluster_message(self, MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)
    if model is None:
        return

    if "Legrand" not in self.ListOfDevices[MsgSrcAddr]:
        self.ListOfDevices[MsgSrcAddr]["Legrand"] = {}

    if MsgAttrID == "0000":
        # Confort': 0x00,
        # Confort -1' : 0x01,
        # Confort -2' : 0x02,
        # Eco': 0x03,
        # Hors-gel' : 0x04,
        # Off': 0x05
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)


def Clusterfc21(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):

    # FC21 : PFX Cluster Profalux
    # Attribute 0x0001 => Orientation ( value between 0 to 90)
    model = pre_process_cluster_message(self, MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)
    if MsgAttrID == "0001":
        self.log.logging( "Cluster", "Debug", "ReadCluster %s - %s/%s Orientation BSO: %s - %s °" % (
            MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgClusterData, int(MsgClusterData, 16)), MsgSrcAddr, )
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgClusterData)


def Clusterfc57(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):
    model = pre_process_cluster_message(self, MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)
    

def Clusterfc7d(self, Devices, MsgSQN, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData, Source):
    model = pre_process_cluster_message(self, MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData)
    
    ikea_air_purifier_cluster(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)


def create_context(MsgClusterId, MsgSrcEp, MsgAttrID, MsgAttType, MsgAttSize, MsgClusterData):
    """
    Create a context dictionary from the provided message attributes.

    Args:
    - MsgClusterId: The ID of the message cluster.
    - MsgSrcEp: The source endpoint of the message.
    - MsgAttrID: The attribute ID of the message.
    - MsgAttType: The attribute type of the message.
    - MsgAttSize: The attribute size of the message.
    - MsgClusterData: The data of the message cluster.

    Returns:
    - A dictionary containing the context information.
    """
    return {
        "MsgClusterId": str(MsgClusterId),
        "MsgSrcEp": str(MsgSrcEp),
        "MsgAttrID": str(MsgAttrID),
        "MsgAttType": str(MsgAttType),
        "MsgAttSize": str(MsgAttSize),
        "MsgClusterData": str(MsgClusterData),
    }


DECODE_CLUSTER = {
    "0006": Cluster0006,
    "0008": Cluster0008,
    "0012": Cluster0012,
    "000c": Cluster000c,
    "0101": Cluster0101,
    "0201": Cluster0201,
    "0500": Cluster0500,
    "0502": Cluster0502,
    "0702": Cluster0702,
    "fe03": Clusterfe03,
    "fc00": Clusterfc00,
    "fc01": Clusterfc01,
    "fc03": Clusterfc03,
    "fc7d": Clusterfc7d,
    "fc21": Clusterfc21,
    "fc40": Clusterfc40,

}
