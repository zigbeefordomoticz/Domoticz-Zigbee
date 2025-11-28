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
OTAManagement class for managing Over-The-Air (OTA) firmware updates.

Args:
    zigbee_communitation: The Zigbee communication object.
    PluginConf: The plugin configuration object.
    DeviceConf: The device configuration object.
    adminWidgets: The admin widgets object.
    ZigateComm: The Zigate communication object.
    HomeDirectory: The home directory path.
    hardwareID: The hardware ID.
    Devices: The list of Domoticz devices.
    ListOfDevices: The global list of devices.
    IEEE2NWK: The list of IEEE to NWKID mappings.
    log: The logging object.
    PluginHealth: The plugin health object.
    readZclClusters: The ZCL clusters reader object.

Attributes:
    zigbee_communication: The Zigbee communication object.
    HB: The heartbeat value.
    ListOfDevices: The global list of devices.
    IEEE2NWK: The list of IEEE to NWKID mappings.
    Devices: The list of Domoticz devices.
    DeviceConf: The device configuration object.
    adminWidgets: The admin widgets object.
    ControllerLink: The Zigate communication object.
    pluginconf: The plugin configuration object.
    homeDirectory: The home directory path.
    log: The logging object.
    PluginHealth: The plugin health object.
    readZclClusters: The ZCL clusters reader object.
    ListOfImages: The list of available firmware loaded at plugin startup.
    ImageLoaded: The dictionary containing information about the loaded firmware image.
    ListInUpdate: The dictionary containing information about the firmware update in progress.
    authorized_device_downgrade: The dictionary containing information about devices authorized for downgrade.
    zigbee_ota_index: The Zigbee OTA index.
    zigbee_ota_found_in_index: The list of Zigbee OTA firmware found in the index.
    once: Flag indicating if the OTA process has started.

Methods:
    _reset_ota_state: Reset the OTA update state.
    cancel_current_firmware_update: Cancel the current firmware update.
    ota_image_block_request: Handle the OTA image block request.
    ota_image_page_request: Handle the OTA image page request.
    ota_upgrade_end_request: Handle the OTA upgrade end request.
    heartbeat: Perform the OTA heartbeat.
    restapi_list_of_firmware: Get the list of available firmware.
    restapi_firmware_update: Perform the firmware update.
    query_next_image_request: Handle the OTA query next image request.
"""

import json
import math
import os
import socket
import struct
import time
import urllib.error
import urllib.request
from datetime import datetime
from os import listdir
from os.path import exists, isfile, join
from pathlib import Path

from Modules.sendZigateCommand import sendZigateCmd
from Modules.tools import get_device_nickname
from Modules.zigateConsts import ADDRESS_MODE, ZIGATE_EP
from Zigbee.zclRawCommands import (zcl_raw_ota_image_block_response_success,
                                   zcl_raw_ota_image_notify,
                                   zcl_raw_ota_query_next_image_response,
                                   zcl_raw_ota_upgrade_end_response)

# This file is hosted on @koenkk repository.
# This file is maintained from the community, so make sure what you do.

OTA_CLUSTER_ID = "0019"

DEFAULT_OTA_PROFILE = {
    "max_data": 48,
    "min_delay": 0.300,
    "retry": 3,
}

VENDOR_PROFILES = {
    0x100B: {  # Philips Hue
        "max_data": 64,
        "min_delay": 0.300,
        "retry": 3,
        "notes": "Strict timing, small buffers, strong CRC/header validation."
    },

    0x118C: {  # IKEA (TRÅDFRI / Dirigera)
        "max_data": 56,
        "min_delay": 0.12,
        "retry": 3,
        "notes": "Generally robust; failures often mesh-related."
    },

    0x1021: {  # Legrand / Netatmo
        "max_data": 64,
        "min_delay": 0.10,
        "retry": 3,
        "notes": "Very picky image metadata; some devices require vendor-style packaging."
    },

    0x112D: {  # Develco / frient
        "max_data": 56,
        "min_delay": 0.16,
        "retry": 2,
        "notes": "Known mid-OTA stalls; allow long idle periods."
    },

    0x1224: {  # NodOn
        "max_data": 52,
        "min_delay": 0.12,
        "retry": 3,
        "notes": "Verify manufacturer/image type; some ‘No image available’ errors."
    },

    0x10A4: {  # Osram / LEDVANCE
        "max_data": 56,
        "min_delay": 0.12,
        "retry": 3,
        "notes": "Generally easier OTA; check mesh stability during upgrade."
    },
}


OTA_CODES = {
    "Danfoss": {"Folder": "DANFOSS", "ManufCode": 0x1246, "ManufName": "Danfoss", "Enabled": True},
    "Develco": {"Folder": "DEVELCO", "ManufCode": 0x1015, "ManufName": "Develco", "Enabled": True},
    "EcoDim": {"Folder": "ECO-DIM", "ManufCode": 0x126a, "ManufName": "EcoDim", "Enabled": True},
    "Eurotronics": {"Folder": "EUROTRONICS", "ManufCode": 0x1037, "ManufName": "Eurotronic", "Enabled": True},
    "Frient": {"Folder": "DEVELCO", "ManufCode": 0x1015, "ManufName": "frient A/S", "Enabled": True},
    "Ikea": {"Folder": "IKEA-TRADFRI", "ManufCode": 0x117C, "ManufName": "IKEA of Sweden", "Enabled": True},
    "Ledvance": {"Folder": "LEDVANCE", "ManufCode": 0x1189, "ManufName": "LEDVANCE", "Enabled": True},
    "Legrand": {"Folder": "LEGRAND", "ManufCode": 0x1021, "ManufName": "Legrand", "Enabled": True},
    "Lixee": {"Folder": "LIXEE", "ManufCode": 0x1037, "ManufName": "LiXee", "Enabled": True},
    "Nodon": {"Folder": "NODON", "ManufCode": 0x128b, "ManufName": "NodOn", "Enabled": True},
    "Osram1": {"Folder": "OSRAM", "ManufCode": 0xBBAA, "ManufName": "OSRAM", "Enabled": True},
    "Osram2": {"Folder": "LEDVANCE", "ManufCode": 0x110C, "ManufName": "OSRAM", "Enabled": True},
    "Philips": {"Folder": "PHILIPS", "ManufCode": 0x100B, "ManufName": "Philips", "Enabled": True},
    "Salus": {"Folder": "SALUS", "ManufCode": 0x1078, "ManufName": "Computime", "Enabled": True},
    "Schneider": {"Folder": "SCHNEIDER-WISER", "ManufCode": 0x105E, "ManufName": "Schneider Electric", "Enabled": True},
    "SonOff": {"Folder": "SONOFF", "ManufCode": 0x1286, "ManufName": "Sonoff", "Enabled": True},
    "Xiaomi": {"Folder": "XIAOMI", "ManufCode": 0x115f, "ManufName": "Xiaomi", "Enabled": True},
    "Lumi": {"Folder": "LUMI", "ManufCode": 0x1037, "ManufName": "Lumi", "Enabled": True},
    "devbis": {"Folder": "XIAOMI", "ManufCode": 0xdb15, "ManufName": "Lumi", "Enabled": True},
    "z03mmc": {"Folder": "XIAOMI", "ManufCode": 0x0084, "ManufName": "Lumi", "Enabled": True},
    "Namron": {"Folder": "NAMRON", "ManufCode": 0x11224, "ManufName": "Namron", "Enabled": True},
}


class OTAManagement(object):


    def __init__(
        self,
        zigbee_communication,
        PluginConf,
        DeviceConf,
        adminWidgets,
        ZigateComm,
        HomeDirectory,
        hardwareID,
        Devices,
        ListOfDevices,
        IEEE2NWK,
        log,
        PluginHealth,
        readZclClusters,
        internet_available,
        pairing_in_progress,
        ):
        
        # Pointers to external objects
        self.zigbee_communication = zigbee_communication
        self.HB = 0
        self.ListOfDevices = ListOfDevices  # Point to the Global ListOfDevices
        self.IEEE2NWK = IEEE2NWK  # Point to the List of IEEE to NWKID
        self.Devices = Devices  # Point to the List of Domoticz Devices
        self.DeviceConf = DeviceConf
        self.adminWidgets = adminWidgets
        self.ControllerLink = ZigateComm  # Point to the ZigateComm object
        self.pluginconf = PluginConf
        self.homeDirectory = HomeDirectory
        self.log = log
        self.PluginHealth = PluginHealth
        self.readZclClusters = readZclClusters
        self.internet_available = internet_available
        self.pairing_in_progress = pairing_in_progress
        self.latest_request_was_malformed = False

        # Properties for firmware/image management
        self.ListOfImages = {}  # List of available firmware loaded at plugin startup

        self.ImageLoaded = {
            "ImageVersion": None,
            "image_type": None,
            "manufacturer_code": None,
            "LoadedTimeStamp": 0,
            "Notified": False,
            "NotifiedTimeStamp": 0,
        }

        self.ListInUpdate = {
            "FileName": None,
            "Status": None,
            "intImageType": None,
            "intImageVersion": None,
            "ImageVersion": None,
            "Process": None,
            "NwkId": None,
            "Ep": None,
            "intManufCode": None,
            "LastBlockSent": 0,
            "AuthorizedForUpdate": [],
            "Retry": 0,
        }
        
        self.authorized_device_downgrade = {}
        self.zigbee_ota_index = None
        self.zigbee_ota_found_in_index = []
        self.once = True
        
        # Load Zigbee OTA index and scan the folder
        loading_zigbee_ota_index( self )
        logging(self, "Debug", "zigbee_ota_index: %s" %self.zigbee_ota_index)
        ota_scan_folder(self)


    def cancel_current_firmware_update(self):
        self.ListInUpdate["NwkId"] = None
        self.ListInUpdate["Status"] = None
        self.ListInUpdate["LastBlockSent"] = 0
        self.ListInUpdate["Retry"] = 0
        self.ImageLoaded["NotifiedTimeStamp"] = 0
        self.ImageLoaded["LoadedTimeStamp"] = 0
        self.ListInUpdate["Process"] = None


    def ota_image_block_request(self, MsgData):
        """
        Handle an OTA Image Block Request from a Zigbee device.

        Args:
            MsgData (bytes/hexstr): Raw message data from device.
        """
        if len(MsgData) not in (60, 62):
            logging(self, "Debug", f"ota_image_block_request - Incorrect length ({len(MsgData)}): {MsgData}")
            return

        # Slice message fields
        MsgSQN, MsgEP = MsgData[:2], MsgData[2:4]
        MsgClusterId, MsgaddrMode = MsgData[4:8], MsgData[8:10]
        MsgSrcAddr, MsgIEEE = MsgData[10:14], MsgData[14:30]
        MsgFileOffset = MsgData[30:38]

        intMsgImageVersion = int(MsgData[38:46], 16)
        intMsgImageType = int(MsgData[46:50], 16)
        intMsgManufCode = int(MsgData[50:54], 16)
        MsgBlockRequestDelay = int(MsgData[54:58], 16)
        MsgMaxDataSize = int(MsgData[58:60], 16)
        intMsgFieldControl = int(MsgData[60:62], 16) if len(MsgData) == 62 else 0

        logging(
            self,
            "Debug",
            f"ota_image_block_request - Request Firmware {MsgSrcAddr}/{MsgEP} "
            f"Offset: {int(MsgFileOffset, 16)} Version: 0x{intMsgImageVersion:08X} "
            f"Type: 0x{intMsgImageType:04X} Manuf: 0x{intMsgManufCode:04X} "
            f"Delay: {MsgBlockRequestDelay} MaxSize: {MsgMaxDataSize} "
            f"Control: 0x{intMsgFieldControl:02X}"
        )

        if self.ListInUpdate.get("NwkId") is None:
            logging(self, "Debug", f"ota_image_block_request - Async request from device: {MsgSrcAddr}")
            if not ota_aync_request(
                self, MsgSrcAddr, MsgEP, MsgIEEE, MsgFileOffset, intMsgImageVersion,
                intMsgImageType, intMsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize,
                intMsgFieldControl
            ):
                logging(self, "Debug", f"ota_image_block_request {MsgSrcAddr}/{MsgEP} - Async request failed {self.ListInUpdate}")
                return

        prepare_and_send_block(
            self, MsgSrcAddr, MsgEP, MsgFileOffset, intMsgImageVersion,
            intMsgImageType, intMsgManufCode, MsgBlockRequestDelay,
            MsgMaxDataSize, intMsgFieldControl, MsgSQN
        )


    def ota_image_page_request( self, MsgData ):
        MsgSQN = MsgData[:2]
        MsgEP = MsgData[2:4]
        MsgClusterId = MsgData[4:8]
        MsgaddrMode = MsgData[8:10]
        MsgSrcAddr = MsgData[10:14]
        MsgFileOffset = MsgData[14:22]
        intMsgImageVersion = int(MsgData[22:30], 16)
        intMsgImageType = int(MsgData[30:34], 16)
        intMsgManufCode = int(MsgData[34:38], 16)
        MsgMaxDataSize = int(MsgData[38:40],16)
        PageSize = int(MsgData[40:44],16)
        intResponseSpacing = int(MsgData[44:48],16)
        FieldControl = MsgData[48:50]
        intMsgFieldControl = int(FieldControl,16)
        if len(MsgData) == 64:
            RequestNodeAddress = MsgData[48:64]

        logging( self, "Debug", "ota_image_page_request - Request Firmware %s/%s Offset: %s Version: 0x%08x Type: 0x%04X Manuf: 0x%04X MaxSize: %s PageSize: %s ResponseSpacing: %s Control: 0x%02X" % (
            MsgSrcAddr, MsgEP, int(MsgFileOffset, 16), intMsgImageVersion, intMsgImageType, intMsgManufCode, MsgMaxDataSize, PageSize , intResponseSpacing, intMsgFieldControl, ),)

        if self.ListInUpdate["NwkId"] is None:
            logging(self, "Debug", "ota_image_page_request - Async request from device: %s." % (MsgSrcAddr))
            return
   
        # Page Size: The value indicates the number of bytes to be sent by the server before the client sends another Image Page
        #            Request command. In general, page size value SHALL be larger than the maximum data size value. 
        # Max data Size: The value indicates the largest possible length of data (in bytes) that the client can receive at once.
        # Response Spacing: The value indicates how fast the server SHALL send the data (via Image Block Response command) to the client. 
        # The value is determined by the client. The server SHALL wait at the minimum the (response) spacing value before sending more data to the client. 
        # The value is in milliseconds.
        
        # So we are going to break the pagesize into block of max data size
        number_blocks = PageSize // MsgMaxDataSize
        
        _sqn = int(MsgSQN,16)
        _file_offset = int(MsgFileOffset,16)
        for _ in range( number_blocks ):
            prepare_and_send_block(
                self, 
                MsgSrcAddr, 
                MsgEP, 
                "%08x" %_file_offset, 
                intMsgImageVersion, 
                intMsgImageType, 
                intMsgManufCode, 
                intResponseSpacing, 
                MsgMaxDataSize, 
                intMsgFieldControl, 
                "%02x" %_sqn, 
                disableACK=True
            )
            
            _file_offset += MsgMaxDataSize
            _sqn += 1
            if _sqn > 0xff:
                _sqn = 0


    def ota_upgrade_end_request(self, MsgData):
        logging(self, "Debug", "Decode8503 - Request Firmware Completed %s/%s" % (MsgData, len(MsgData)))

        MsgSQN = MsgData[:2]
        MsgEP = MsgData[2:4]
        MsgClusterId = MsgData[4:8]
        MsgaddrMode = MsgData[8:10]
        MsgSrcAddr = MsgData[10:14]
        intMsgImageVersion = int(MsgData[14:22], 16)
        image_type = int(MsgData[22:26], 16)
        intMsgManufCode = int(MsgData[26:30], 16)
        MsgStatus = MsgData[30:32]
        logging(self, "Log", "OTA upgrade completed - %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s" % (
            MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus))

        if self.ListInUpdate["NwkId"] is None:
            logging(self, "Log", "ota_upgrade_end_request - Receive Firmware Completed from %s with status %s most likely a duplicated packet as there is nothing in Progress. " % (MsgSrcAddr, MsgStatus))

            return
        if self.ListInUpdate["NwkId"] and MsgSrcAddr != self.ListInUpdate["NwkId"]:
            logging(self, "Error", "ota_upgrade_end_request - OTA upgrade completed - %s with status %s not in Upgraded devices" % (MsgSrcAddr, MsgStatus))

            return
        if "StartTime" not in self.ListInUpdate:
            logging(self, "Error", "ota_upgrade_end_request - OTA upgrade completed - No Start Time for device: %s" % MsgSrcAddr)
            return

        if MsgStatus == "00":
            logging(self, "Status", "OTA upgrade completed with success - %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s" % (
                MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus))
            ota_upgrade_end_response(self, MsgSQN, MsgSrcAddr, MsgEP, intMsgImageVersion, image_type, intMsgManufCode)
            notify_upgrade_end(self, "OK", MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion)

        elif MsgStatus == "95":
            logging(self, "Error", "ota_request_firmware_completed - OTA Firmware aborted - %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s" % (
                MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus))
            notify_upgrade_end(self, "Aborted", MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion)

        elif MsgStatus == "96":
            logging(self, "Error", "ota_request_firmware_completed - OTA Firmware image validation failed %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s" % (
                MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus))

            notify_upgrade_end(self, "Failed", MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion)

        elif MsgStatus == "97":
            logging(self, "Log", "ota_request_firmware_completed - OTA Firmware image wait for data %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s" % (
                MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus))

            return
        elif MsgStatus == "99":
            logging(self, "Status", "ota_request_firmware_completed - OTA Firmware  The downloaded image was successfully received, but there is a need for additional image %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s" % (
                MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus))

            notify_upgrade_end(self, "More", MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion)

        else:
            logging(self, "Error", "ota_request_firmware_completed - OTA Firmware unexpected error %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s" % (
                MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus))

            notify_upgrade_end(self, "Aborted", MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion)

        cleanup_after_completed_upgrade(self, MsgSrcAddr, MsgStatus)


    def heartbeat(self):
        
        nwk_id = self.ListInUpdate["NwkId"]
        if nwk_id is None:
            logging(self, "Debug", "ota_heartbeat - nothing to do")
            return

        process = self.ListInUpdate["Process"]
        image_type = self.ImageLoaded["image_type"]
        loaded_time_stamp = self.ImageLoaded["LoadedTimeStamp"]
        notified_time_stamp = self.ImageLoaded["NotifiedTimeStamp"]
        retry = self.ListInUpdate["Retry"]
        authorized_for_update = self.ListInUpdate["AuthorizedForUpdate"]

        logging(
            self,
            "Debug",
            "ota_heartbeat - NwkId: %s Process: %s Loaded: 0x%s Time: %s Notified: %s Retry: %s Authorized: %s"
            % (nwk_id, process, image_type, loaded_time_stamp, notified_time_stamp, retry, authorized_for_update),
        )

        if nwk_id and self.ListInUpdate["Status"] == "Transfer Progress" and self.ListInUpdate["LastBlockSent"] != 0 and (
                time.time() > self.ListInUpdate["LastBlockSent"] + 300):
            # TODO: retry mechanism per device
            _handle_ota_timeout(self)
            return

        if nwk_id and self.ListInUpdate["LastBlockSent"] == 0 and loaded_time_stamp != 0:
            _retry_notification(self)

        if retry == 10 or self.ImageLoaded["NotifiedTimeStamp"] != 0 and (time.time() > self.ImageLoaded["NotifiedTimeStamp"] + 600):
            _handle_timeout(self)


    def restapi_list_of_firmware(self):
        brand = {}
        for x in self.ListOfImages["Brands"]:
            brand[x] = []
            for y in self.ListOfImages["Brands"][x]:
                image = {
                    "FileName": y, 
                    "ImageType": "%04x" % self.ListOfImages["Brands"][x][y]["ImageType"], 
                    "ManufCode": "%04x" % self.ListOfImages["Brands"][x][y]["intManufCode"], 
                    "Version": "%08x" % self.ListOfImages["Brands"][x][y]["originalVersion"], 
                    "ApplicationRelease": "%02x" % ((self.ListOfImages["Brands"][x][y]["originalVersion"] & 4278190080) >> 24), 
                    "ApplicationBuild": "%02x" % ((self.ListOfImages["Brands"][x][y]["originalVersion"] & 16711680) >> 16), 
                    "StackRelease": "%02x" % ((self.ListOfImages["Brands"][x][y]["originalVersion"] & 65280) >> 8), 
                    "StackBuild": "%02x" % (self.ListOfImages["Brands"][x][y]["originalVersion"] & 255)
                    }
                brand[x].append(image)
        return [brand]


    def restapi_firmware_update(self, data):
        """
        Trigger a firmware update for one Zigbee device via REST API.

        Args:
            data (list[dict]): List of update requests, each with keys:
                - "Brand": str
                - "FileName": str
                - "NwkId": str
                - "Ep": int
                - "ForceUpdate": bool
        Note:
            Only one device update at a time is currently supported.
        """
        if not data:
            logging(self, "Warning", "No update data received.")
            return

        if len(data) > 1:
            logging(self, "Error", "Only one device update at a time is supported!")
            return

        # Process the single device update
        update_request = data[0]
        brand = update_request.get("Brand")
        file_name = update_request.get("FileName")
        target_nwkid = update_request.get("NwkId")
        target_ep = update_request.get("Ep")
        force_update = update_request.get("ForceUpdate", False)

        firmware_update(self, brand, file_name, target_nwkid, target_ep, force_update)

        # Allow downgrade if force update is requested
        if force_update:
            self.authorized_device_downgrade[target_nwkid] = True


    def query_next_image_request(self, srcnwkid, srcep, Sqn, Data):
        # This is a Client -> Server (direction set to 0x00)
        # The server takes the client’s information in the command and determines whether it has a suitable image for the particular client.
        # The decision SHOULD be based on specific policy that is specific to the upgrade server and outside the scope of this document... 
        # However, a recommended default policy is for the server to send back a response that indicates the availability of an image
        # that matches the manufacturer code, image type, and the highest available file version of that image on the server. 
        # However, the server MAY choose to up- grade or downgrade a clients’ image, as its policy dictates. 
        # If client’s hardware version is included in the command, the server SHALL examine the value against the minimum and
        # maximum hardware versions in- cluded in the OTA file header.

        # If we have already an OTA in progress, let's just respond that no image available for now
        if self.ListInUpdate["NwkId"] and self.ListInUpdate["NwkId"] != srcnwkid:
            zcl_raw_ota_query_next_image_response(self, Sqn, srcnwkid, ZIGATE_EP, srcep, 0x98)
            return

        # Command: 0x01

        fieldcontrol = int(Data[:2],16)
        logging(self, "Debug", f" Manuf: {Data[2:6]} Type: {Data[6:10]} Version: {Data[10:18]}")
        logging(self, "Debug", f" Manuf: {int(Data[2:6], 16)} Type: {int(Data[6:10], 16)} Version: {int(Data[10:18], 16)}")
        manufcode = struct.unpack("H", bytes.fromhex(Data[2:6]))[0]
        imagetype = struct.unpack("H", bytes.fromhex(Data[6:10]))[0]
        currentVersion = struct.unpack("I", bytes.fromhex(Data[10:18]))[0]

        if fieldcontrol:
            hardwareversion = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[18:22], 16)))[0]

        logging(self, "Debug", "OTA Query Next Image request for %s/%s [%s] - %s %s %s %s" % (
            srcnwkid, srcep, Sqn, fieldcontrol, manufcode, imagetype, currentVersion ))

        ota_client = self.ListOfDevices.setdefault(srcnwkid, {}).setdefault("OTAClient", {})
        ota_client["ManufacturerCode"] = manufcode
        ota_client["ImageType"] = imagetype
        ota_client["CurrentImageVersion"] = currentVersion
        
        authorized_device_downgrade = self.authorized_device_downgrade.get(srcnwkid, False)

        image_found = is_image_for_query_next_image_request( self, srcnwkid, manufcode, imagetype, currentVersion , authorized_device_downgrade)
        if image_found:
            fileversion = image_found["originalVersion"]   # integer
            imagesize = image_found["intSize"]           # integer

            if authorized_device_downgrade:
                logging(self, "Debug", f"OTA Query Next Image request - Device {srcnwkid} is authorized for downgrade.")
                fileversion = image_found["originalVersion"] + 0x10100000
            
            logging(self, "Debug", f"OTA Query Next Image request - Image found fileversion: 0x{fileversion:08x} imagesize: {imagesize}")

            if "autoServeOTA" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["autoServeOTA"]:
                logging(self, "Debug", f"OTA Query Next Image request - autoServeOTA fileversion: 0x{fileversion:08x} imagesize: {imagesize}")

                self.ListInUpdate["AuthorizedForUpdate"].append( srcnwkid )
                return zcl_raw_ota_query_next_image_response(
                    self, Sqn, srcnwkid, ZIGATE_EP, srcep,
                    0x00, manufcode, imagetype, fileversion, imagesize)

            elif srcnwkid in self.ListInUpdate["AuthorizedForUpdate"]:
                # We are in the case were we get a request, but do not authorised selfserving OTA
                logging(self, "Debug", f"OTA Query Next Image request - AuthorizedForUpdate fileversion: {fileversion} imagesize: {imagesize}")

                return zcl_raw_ota_query_next_image_response(
                    self, Sqn, srcnwkid, ZIGATE_EP, srcep,
                    0x00, manufcode, imagetype, fileversion, imagesize)

        elif "checkFirmwareAgainstZigbeeOTARepository" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["checkFirmwareAgainstZigbeeOTARepository"]:
            if (manufcode, imagetype, currentVersion) not in self.zigbee_ota_found_in_index:
                _ota_available = check_ota_availability_from_index( self, manufcode, imagetype, currentVersion )
                if _ota_available:
                    self.zigbee_ota_found_in_index.append( ( manufcode, imagetype, currentVersion)  )
                    notify_ota_firmware_available(self, srcnwkid, manufcode, imagetype, currentVersion, _ota_available )

        # No Image available
        logging( self, "Debug", ( f"OTA Query Next Image request - No Image Available for now " f"Current device manufcode: 0x{manufcode:04x}, " f"imagetype: 0x{imagetype:04x}, " f"currentVersion: 0x{currentVersion:08x}" ) )
        return zcl_raw_ota_query_next_image_response(self, Sqn, srcnwkid, ZIGATE_EP, srcep, 0x98)


# Local Routines and other helpers
def _handle_ota_timeout(self):
    logging(self, "Error", "Ota timed out on NwkId: %s for block: %s" % (
        self.ListInUpdate["NwkId"], self.ListInUpdate["intFileOffset"]))
    _reset_ota_state(self)


def _retry_notification(self):
    self.ListInUpdate["Retry"] += 1
    logging(self, "Log", "Ota retries notifying device %s" % self.ListInUpdate["NwkId"])
    
    ota_image_advertize(self, self.ListInUpdate["NwkId"], self.ListInUpdate["Ep"],
                        self.ImageLoaded["ImageVersion"], 
                        self.ImageLoaded["image_type"],
                        self.ImageLoaded["manufacturer_code"])


def _handle_timeout(self):
    logging(self, "Error", "Ota detects Timeout while notifying device %s" % self.ListInUpdate["NwkId"])
    _reset_ota_state(self)


def _reset_ota_state(self):
    if self.ListInUpdate["NwkId"] in self.ListInUpdate["AuthorizedForUpdate"]:
        self.ListInUpdate["AuthorizedForUpdate"].remove(self.ListInUpdate["NwkId"])
    self.ListInUpdate["NwkId"] = None
    self.ListInUpdate["Status"] = None
    self.ListInUpdate["LastBlockSent"] = 0
    self.ListInUpdate["Retry"] = 0
    self.ImageLoaded["LoadedTimeStamp"] = 0
    self.ImageLoaded["NotifiedTimeStamp"] = 0
    self.ListInUpdate["Process"] = None


def ota_load_image_to_zigate(self, image_type, force_version=None):
    # Load the image headers into Zigate

    if image_type not in self.ListOfImages["ImageType"]:
        _log_debug_unknown_image_type(self, image_type)
        return

    brand = self.ListOfImages["ImageType"][image_type]
    image_entry = retrieve_image_in_a_brand(self, image_type, brand)

    if image_entry is None:
        _log_debug_image_not_found(self, image_type, brand)
        return

    image_entry = self.ListOfImages["Brands"][brand][image_entry]
    decoded_header = image_entry["Decoded Header"]

    datas = _format_image_data(self, decoded_header, force_version)

    logging(self, "Debug", f"ota_load_image_to_zigate: - len:{len(datas)} datas: {datas}")

    if not _is_controller_in_raw_mode(self):
        self.ControllerLink.sendData("0500", datas, ackIsDisabled=True)

    _update_image_loaded_info(self, decoded_header, force_version)


def _log_debug_unknown_image_type(self, image_type):
    logging(self, "Debug", f"ota_load_image_to_zigate - Unknown Image {image_type} in {list(self.ListOfImages['ImageType'].keys())}")


def _log_debug_image_not_found(self, image_type, brand):
    logging(self, "Debug", f"ota_load_image_to_zigate - Image {image_type} not found in {list(self.ListOfImages['Brands'][brand].keys())}")


def _format_image_data(self, decoded_header, force_version):
    header_bytes = decoded_header['header_str'].encode('ascii')  # convert string back to bytes
    header_hex = ''.join('%02X' % b for b in header_bytes)

    return (
        f"{ADDRESS_MODE['short']:02x}0000"
        f"{decoded_header['file_id']} "
        f"{decoded_header['header_version']} "
        f"{decoded_header['header_length']} "
        f"{decoded_header['header_fctl']} "
        f"{decoded_header['manufacturer_code']} "
        f"{decoded_header['image_type']} "
        f"{force_version or decoded_header['image_version']} "
        f"{decoded_header['stack_version']}"
        f"{header_hex} "
        f"{decoded_header['image_size']} "
        f"{decoded_header['security_cred_version']} "
        f"{decoded_header['payload_offset']} "
        f"{decoded_header['min_hw_version']} "
        f"{decoded_header['max_hw_version']}"
    )


def _is_controller_in_raw_mode(self):
    return bool(self.pluginconf.pluginConf.get("ControllerInRawMode", False))


def _update_image_loaded_info(self, decoded_header, force_version):
    self.ImageLoaded["ImageVersion"] = force_version or decoded_header['image_version']
    self.ImageLoaded["image_type"] = decoded_header['image_type']
    self.ImageLoaded["manufacturer_code"] = decoded_header['manufacturer_code']
    self.ImageLoaded["LoadedTimeStamp"] = time.time()


def build_ota_data_block(self, block_request, max_data_size):
    """
    Build a single OTA block segment from the full OTA image.

    block_request fields must contain:
        - "Sequence": hex string
        - "Offset": hex string

    Returns:
        (sequence:int, offset:int, length:int, raw_ota_data:bytes)
    """
    ota_image = self.ListInUpdate["OtaImage"]

    sequence = int(block_request["Sequence"], 16)
    offset = int(block_request["Offset"], 16)

    if offset >= len(ota_image):
        return sequence, offset, 0, b""

    # Slice data safely
    end = offset + max_data_size
    raw_ota_data = ota_image[offset:end]

    # Actual number of bytes available
    length = len(raw_ota_data)

    return sequence, offset, length, raw_ota_data


def build_ota_message(
    self, dest_addr, dest_ep, sequence, status, offset,
    image_version, image_type, manufacturer_code, length, raw_ota_data
):
    """
    Build the Zigate OTA Image Block Response payload.

    All fields must already be in HEX string format except:
    - sequence: int
    - status: int
    - offset: int
    - length: int
    - raw_ota_data: bytes or iterable of ints (0–255)
    """

    # Core header
    header = (
        "02"                    # Start of frame / message ID
        f"{dest_addr}"
        f"{ZIGATE_EP}"
        f"{dest_ep}"
    )

    # OTA formatted block
    ota_fields = (
        f"{sequence:02x}"
        f"{status:02x}"
        f"{offset:08x}"
        f"{image_version}"
        f"{image_type}"
        f"{manufacturer_code}"
        f"{length:02x}"
    )

    # Payload data
    ota_payload = "".join(f"{b:02x}" for b in raw_ota_data)

    return header + ota_fields + ota_payload


def update_list_in_update(self, offset, length):
    info = self.ListInUpdate

    now = time.time()
    info["LastBlockSent"] = time.time()
    info["TimeStamps"] = now
    info["Status"] = "Transfer Progress"
    info["Received"] = offset
    info["Sent"] = offset + length

    self.ImageLoaded["NotifiedTimeStamp"] = 0
    


def ota_send_block(self, dest_addr, dest_ep, image_type, msg_image_version, block_request, disable_ack=False, block_delay=DEFAULT_OTA_PROFILE["min_delay"]):

    images = self.ListOfImages.get("ImageType", {})
    in_update = self.ListInUpdate
    if image_type not in images:
        logging(self, "Error", f"ota_send_block - unknown image_type {image_type}")
        return False

    expected_image_type = int(in_update["ImageType"], 16)
    if image_type != expected_image_type:
        logging(
            self, "Error",
            f"ota_send_block - inconsistent ImageType Received: {image_type} "
            f"Expecting: {in_update['ImageType']}"
        )
        return False

    # Build block, and Minimum Block Request Delay
    manufacturer_code = in_update['intManufCode']
    ota_profile = VENDOR_PROFILES.get( manufacturer_code, DEFAULT_OTA_PROFILE )
    max_data_size = min(block_request["MaxDataSize"], ota_profile["max_data"])
    block_delay = max(block_delay, ota_profile["min_delay"])

    sequence, offset, length, raw_ota_data = build_ota_data_block( self, block_request, max_data_size )

    # Hex representations
    image_version_hex = f"{msg_image_version:08x}"
    image_type_hex = f"{image_type:04x}"
    manufacturer_code_hex = f"{in_update['intManufCode']:04x}"

    data = build_ota_message(
        self, dest_addr, dest_ep, sequence, 0x00, offset,
        image_version_hex, image_type_hex, manufacturer_code_hex,
        length, raw_ota_data
    )

    if self.pluginconf.pluginConf.get("EnableOTATracing", False):
        trace_ota_block(
            self,
            dest_addr=dest_addr,
            image_type_hex=image_type_hex,
            offset=offset,
            size=length,
            sequence=sequence,
            raw_ota_data=raw_ota_data,
        )

    # Update progress tracking
    update_list_in_update(self, offset, length)

    logging( self, "Debug", f"ota_send_block - Block sent to {dest_addr}/{dest_ep} " f"Received yet: {offset} Sent now: {offset} Size: {max_data_size} Delay: {block_delay}" )

    # Determine OTA block status
    if length == 0 or data is None:
        logging( self, "Error", f"OTA {dest_addr}/{dest_ep} short of data, device request offset: {offset} expected size: {max_data_size} got only {length}" )
        
        if self.latest_request_was_malformed:
            # 2nd time in a row we get a malformed request, aborting
            status = 0x95  # ABORT
        else:
            # get a request for data we cannot provide
            status = 0x80  # MALFORMED_COMMAND
            self.latest_request_was_malformed = True
    else:
        status = 0x00  # Successblock_request_delay
        self.latest_request_was_malformed = False

    # --- Raw mode (controller internal testing) ---
    raw_mode = self.pluginconf.pluginConf.get("ControllerInRawMode", False)
    if raw_mode:
        raw_data_hex = "".join(f"{b:02x}" for b in raw_ota_data)

        return zcl_raw_ota_image_block_response_success(
            self,
            f"{sequence:02x}",
            dest_addr,
            ZIGATE_EP,
            dest_ep,
            f"{status:02x}",
            manufacturer_code_hex,
            image_type_hex,
            image_version_hex,
            f"{offset:08x}",
            f"{length:02x}",
            raw_data_hex,
            ackIsDisabled=disable_ack,
            min_block_delay=block_delay,
        )

    # --- Normal Zigate path ---
    self.ControllerLink.sendData( "0502", data, ackIsDisabled=False, NwkId=dest_addr )


def ota_image_advertize(self, dest_addr, dest_ep, image_version, image_type=0xFFFF, manufacturer_code=0xFFFF):
    # 'IMAGE_NOTIFY  0x0505  Notify desired device that ota is available. After loading headers use this.'
    # The 'query jitter' mechanism can be used to prevent a flood of replies to an Image Notify broadcast
    # or multicast (Step 2 above). The server includes a number, n, in the notification.
    # If interested in the image, the receiving client generates a random number in the range 1-100.
    # If this number is greater than n, the client discards the notification, otherwise it responds with
    # a Query Next Image Request. This results in only a fraction of interested clients responding.

    JITTER_OPTION = 100

    # teOTA_ImageNotifyPayloadType
    #   - 0: E_CLD_OTA_QUERY_JITTER Include only ‘Query Jitter’ in payload
    #   - 1: E_CLD_OTA_MANUFACTURER_ID_AND_JITTER Include ‘Manufacturer Code’ and ‘Query Jitter’ in payload
    #   - 2: E_CLD_OTA_ITYPE_MDID_JITTER Include ‘Image Type’, ‘Manufacturer Code’ and ‘Query Jit- ter’ in payload
    #   - 3: E_CLD_OTA_ITYPE_MDID_FVERSION_JITTER Include ‘Image Type’, ‘Manufacturer Code’,
    #        ‘File Version’ and ‘Query Jitter’ in payload

    IMG_NTFY_PAYLOAD_TYPE = 3

    self.ImageLoaded["Notified"] = True
    self.ImageLoaded["NotifiedTimeStamp"] = time.time()

    if IMG_NTFY_PAYLOAD_TYPE == 0:
        image_version = 0xFFFFFFFF  # Wildcard
        image_type = 0xFFFF  # Wildcard
        manufacturer_code = 0xFFFF  # Wildcard
    elif IMG_NTFY_PAYLOAD_TYPE == 1:
        image_version = 0xFFFFFFFF  # Wildcard
        image_type = 0xFFFF  # Wildcard
    elif IMG_NTFY_PAYLOAD_TYPE == 2:
        image_version = 0xFFFFFFFF  # Wildcard

    datas = (
        f"{ADDRESS_MODE['short']:02x}"
        f"{dest_addr}{ZIGATE_EP}{dest_ep}"
        f"{IMG_NTFY_PAYLOAD_TYPE:02x}"
        f"{image_version:08X}{image_type:04x}{manufacturer_code:04x}"
        f"{JITTER_OPTION:02x}"
    )
    
    logging(self, "Debug", f"ota_image_advertize - Type: 0x{image_type:04x}, Version: 0x{image_version:08X} => datas: {datas}")

    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return zcl_raw_ota_image_notify(self, dest_addr, ZIGATE_EP, dest_ep, f"{IMG_NTFY_PAYLOAD_TYPE:02x}", f"{JITTER_OPTION:02x}", f"{manufacturer_code:04x}", f"{image_type:04x}", f"{image_version:08X}")

    self.ControllerLink.sendData("0505", datas, ackIsDisabled=False, NwkId=dest_addr)


def ota_upgrade_end_response(self, sqn, dest_addr, dest_ep, file_version, image_type, manufacturer_code):  # OK 24/10 with Firmware Ok
    # This function issues an Upgrade End Response to a client to which the server has been
    # downloading an application image. The function is called after receiving an Upgrade
    # End Request from the client, indicating that the client has received the entire
    # application image and verified it
    #
    # UPGRADE_END_RESPONSE 	0x0504

    upgrade_time=0x00000000  # 0 seconds delay

    if self.pluginconf.pluginConf.get("ControllerInRawMode",False):
        current_time=0x00000000  # Now
        zcl_raw_ota_upgrade_end_response(
            self,
            sqn,
            dest_addr,
            ZIGATE_EP,
            dest_ep,
            manufacturer_code,   # INT
            image_type,          # INT
            file_version,        # INT
            current_time,        # INT
            upgrade_time,        # INT
        )
        logging( self, "Log", f"ota_management - zcl_raw_ota_upgrade_end_response( {sqn}, {dest_addr}, {ZIGATE_EP}, {dest_ep}, {manufacturer_code}, {image_type}, {file_version}, {current_time}, {upgrade_time})", )

    else:
        datas = "%02x" % ADDRESS_MODE["short"] + dest_addr + ZIGATE_EP + dest_ep
        datas += "%08x" % upgrade_time
        datas += "%08x" % 0x00
        datas += "%08x" % file_version
        datas += "%04x" % image_type
        datas += "%04x" % manufacturer_code

        self.ControllerLink.sendData("0504", datas, ackIsDisabled=False, NwkId=dest_addr)

    logging( self, "Log", "ota_management - sending Upgrade End Response, for %s Version: 0x%08X Type: 0x%04x, Manuf: 0x%04X" % (dest_addr, file_version, image_type, manufacturer_code), )

    ota_upgrade = self.ListOfDevices[dest_addr].setdefault("OTAUpgrade", {})

    # Ensure the structure is a dict
    if not isinstance(ota_upgrade, dict):
        self.ListOfDevices[dest_addr]["OTAUpgrade"] = {}
        ota_upgrade = self.ListOfDevices[dest_addr]["OTAUpgrade"]

    now = int(time.time())

    ota_upgrade[now] = {
        "Time": datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S"),
        "Version": f"{file_version:08X}",
        "Type": f"{image_type:04X}",
    }


def ota_management(self, MsgSrcAddr, MsgEP, delay=500):
    """
    Manage OTA update flow by instructing the client to wait before re-requesting
    an image block. Sends the 'SEND_WAIT_FOR_DATA_PARAMS' command (0x0506).

    Args:
        MsgSrcAddr (str): Short network address of the client (hex string).
        MsgEP (int): Endpoint of the client.
        delay (int, optional): Minimum block request delay in milliseconds. Default is 500 ms.
    """
    # OTA_STATUS_WAIT_FOR_DATA: instruct client to wait before next request
    OTA_STATUS_WAIT_FOR_DATA = 0x97

    # CurrentTime: UTC seconds on server (0 if not supported)
    CurrentTime = 0x00

    # RequestTime: UTC seconds at which client should re-issue a request
    RequestTime = 0x00

    # BlockRequestDelayMs: minimum delay in ms between consecutive block requests
    BlockRequestDelayMs = delay

    # Build payload
    datas = (
        f"{ADDRESS_MODE['short']:02x}"
        f"{MsgSrcAddr}"
        f"{ZIGATE_EP}"
        f"{MsgEP}"
        f"{OTA_STATUS_WAIT_FOR_DATA:02X}"
        f"{CurrentTime:08X}"
        f"{RequestTime:08X}"
        f"{BlockRequestDelayMs:04X}"
    )

    # Skip sending if controller is in raw mode
    if self.pluginconf.pluginConf.get("ControllerInRawMode", False):
        return

    # Zigate behaviour
    logging(
        self, "Debug",
        f"ota_management - Reduce Block request rate to {BlockRequestDelayMs} ms"
    )

    self.ControllerLink.sendData(
        "0506",
        datas,
        ackIsDisabled=False,
        NwkId=MsgSrcAddr
    )


def cleanup_after_completed_upgrade(self, NwkId, Status):
    """
    Cleanup and housekeeping after an OTA upgrade completes.

    Args:
        NwkId (str): Network ID of the device.
        Status (str): Upgrade status code ("00" indicates success).
    """
    logging(self, "Debug", f"cleanup_after_completed_upgrade - Cleanup and housekeeping {NwkId} {Status}")

    # Reset update tracking
    self.ListInUpdate["NwkId"] = None
    self.ListInUpdate["Status"] = None
    self.ListInUpdate["Process"] = None

    # Remove device from authorized update list if update was successful
    if Status == "00":
        authorized_list = self.ListInUpdate.get("AuthorizedForUpdate", [])
        if NwkId in authorized_list:
            authorized_list.remove(NwkId)

    logging(
        self,
        "Debug",
        f"cleanup_after_completed_upgrade - After cleanup "
        f"NwkId: {self.ListInUpdate['NwkId']}, "
        f"AuthorizedForUpdate: {self.ListInUpdate.get('AuthorizedForUpdate')}"
    )

    # Remove downgrade authorization if present
    if self.authorized_device_downgrade.get(NwkId):
        del self.authorized_device_downgrade[NwkId]

    # Refresh device attributes after upgrade
    delay_checking_version(self, NwkId)

    # Reset controller (Zigate in native mode only)
    if self.zigbee_communication == "native":
        sendZigateCmd(self, "0002", "00")  # Force Zigate to Normal mode
        sendZigateCmd(self, "0011", "")    # Software Reset


def delay_checking_version(self, NwkId):
    delay_attributes_key = 'DelayReadAttributes'

    if delay_attributes_key not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId][delay_attributes_key] = {'Clusters': []}

    target_time = time.time() + 120
    self.ListOfDevices[NwkId][delay_attributes_key]['TargetTime'] = target_time

    clusters = self.ListOfDevices[NwkId][delay_attributes_key]['Clusters']
    for cluster in ["0000", "0019"]:
        if cluster not in clusters:
            clusters.append(cluster)


def firmware_update(self, brand, file_name, target_nwkid, target_ep, force_update=False):

    if self.ListInUpdate["NwkId"]:
        logging(
            self,
            "Error",
            "There is already an Image loaded %s for device: %s please come back later"
            % (self.ListInUpdate["FileName"], self.ListInUpdate["NwkId"]),
        )
        return False

    if brand not in self.ListOfImages["Brands"]:
        logging(self, "Error", "restapi_firmware_update Brands %s unknown" % brand)
        return False

    if file_name not in self.ListOfImages["Brands"][brand]:
        logging(self, "Error", "restapi_firmware_update FileName %s unknown in this Brand %s" % (file_name, brand))
        return False

    if target_nwkid not in self.ListOfDevices:
        logging(self, "Error", "restapi_firmware_update NwkId: %s unknown" % target_nwkid)
        return False

    if target_ep not in self.ListOfDevices[target_nwkid]["Ep"]:
        logging(self, "Error", "restapi_firmware_update NwkId: %s Ep: %s unknown" % (target_nwkid, target_ep))
        return False

    image_type = self.ListOfImages["Brands"][brand][file_name]["ImageType"]
    manuf_code = self.ListOfImages["Brands"][brand][file_name]["intManufCode"]
    image_version = self.ListOfImages["Brands"][brand][file_name]["originalVersion"]

    self.ListInUpdate["NwkId"] = target_nwkid
    self.ListInUpdate["Ep"] = target_ep
    self.ListInUpdate["AuthorizedForUpdate"].append(target_nwkid)
    self.ListInUpdate["Process"] = None
    # Do we have to overwrite the Image Version in order to force update
    if force_update:
        # Increase Application release by + 0x10 and Application Build by +0x10
        image_version = self.ListOfImages["Brands"][brand][file_name]["originalVersion"] + 0x10100000
        logging(
            self,
            "Status",
            "----> Forcing update for Image: 0x%04x from Version: 0x%08X to Version: 0x%08X"
            % (image_type, self.ListOfImages["Brands"][brand][file_name]["originalVersion"], image_version),
        )
        self.ListOfImages["Brands"][brand][file_name]["intImageVersion"] = image_version
        ota_load_image_to_zigate(self, image_type, image_version)
    else:
        ota_load_image_to_zigate(self, image_type)
    ota_image_advertize(self, target_nwkid, target_ep, image_version=image_version, image_type=image_type, manufacturer_code=manuf_code)
    return True


def logging(self, logType, message, nwkid=None):  # OK 13/10
    self.log.logging("OTA", logType, message, nwkid)


def is_image_for_query_next_image_request( self, nwkid, manuf_code, image_type, file_version, authorized_device_downgrade):

    logging(self, "Debug", "is_image_for_query_next_image_request - %s %s %s Downgrade: %s" % (
        manuf_code, image_type, file_version, authorized_device_downgrade), nwkid)

    for brand_name in self.ListOfImages["Brands"]:
        logging(self, "Debug", "is_image_for_query_next_image_request - checking %s" %brand_name, nwkid)
        for file_name in self.ListOfImages["Brands"][brand_name]:
            logging(self, "Debug", "    - filename %s Manuf: %s Image: %s Version: %s" %(
                file_name,
                self.ListOfImages["Brands"][brand_name][file_name]["intManufCode"], 
                self.ListOfImages["Brands"][brand_name][file_name]["ImageType"],
                self.ListOfImages["Brands"][brand_name][file_name]["originalVersion"]
                ),
                nwkid
            )
            # Compliance with Brand
            if manuf_code != self.ListOfImages["Brands"][brand_name][file_name]["intManufCode"]:
                continue

            logging(self, "Debug", "is_image_for_query_next_image_request - potential brand name found:%s ..." % brand_name, nwkid)

            # Compliance with Image Type
            if image_type != self.ListOfImages["Brands"][brand_name][file_name]["ImageType"]:
                continue

            if authorized_device_downgrade:
                return self.ListOfImages["Brands"][brand_name][file_name]

            logging(self, "Debug", "is_image_for_query_next_image_request - potential image type found:%s with version %s..." % (
                brand_name, self.ListOfImages["Brands"][brand_name][file_name]["originalVersion"]), nwkid)

            # Compliance with Image Type
            if file_version < self.ListOfImages["Brands"][brand_name][file_name]["originalVersion"]:
                logging(self, "Debug", "is_image_for_query_next_image_request - We have newest firmware available for this device")
                return self.ListOfImages["Brands"][brand_name][file_name]

    return None


def retrieve_image_in_a_brand(self, image_type, brand):
    brand_images = self.ListOfImages.get("Brands", {}).get(brand, {})
    
    return next((image for image, info in brand_images.items() if info.get("ImageType") == image_type), None)


def retrieve_image(self, image_type):
    for brand, images in self.ListOfImages.get("Brands", {}).items():
        for image, info in images.items():
            if image_type == info.get("ImageType"):
                return brand, image
    return None


def ota_scan_folder(self):  # OK 13/10
    # Scanning the Firmware folder
    # At that stage ALL firmware available from each ENABLED folders
    # have been read , decoded and key informations stored in ListOfImages
    # ListOfImages have 2 entries either from brand or from Image Type

    self.ListOfImages["Brands"] = {}
    self.ListOfImages["ImageType"] = {}
    for brand in OTA_CODES:
        if not OTA_CODES[brand]["Enabled"]:
            continue
        
        self.ListOfImages["Brands"][brand] = {}
        ota_dir = self.pluginconf.pluginConf["pluginOTAFirmware"] + "/" + OTA_CODES[brand]["Folder"]
        # Check the folder exist
        if not exists(ota_dir):
            continue

        ota_image_files = [f for f in listdir(ota_dir) if isfile(join(ota_dir, f))]

        logging(self, "Debug", "   screening %s" %ota_dir)
        for ota_image_file in ota_image_files:
            if ota_image_file in ("README.md", "README.txt", ".PRECIOUS", ".precious"):
                continue
            logging(self, "Debug", "       found %s" %ota_image_file)
            header_return = ota_extract_image_headers(self, OTA_CODES[brand]["Folder"], ota_image_file)
            
            if header_return is None:
                continue
            image_type, headers, ota_image = header_return

            # Check if this Image is the latest version.
            if image_type in self.ListOfImages["ImageType"] and not check_image_valid_version(
                self, brand, image_type, ota_image_file, headers
            ):
                # Most likely we have a more higher version already loaded!
                continue

            # Check if the Image type is not used by another brand
            if image_type in self.ListOfImages["ImageType"] and self.ListOfImages["ImageType"][image_type] != brand:
                logging(self, "Error", "ota_scan_folder Firmware %s not loaded, another firmware with the same ImageType and another brand is already loaded" %ota_image_file)
                continue

            self.ListOfImages["ImageType"][image_type] = brand
            self.ListOfImages["Brands"][brand][ota_image_file] = {
                "Directory": ota_dir,
                "Process": False,
                "ImageType": image_type,
                "Decoded Header": headers,
                "OtaImage": ota_image,
                "intManufCode": headers["manufacturer_code"],
                "originalVersion": headers["image_version"],
                "intImageVersion": headers["image_version"],
                "intSize": headers["image_size"],
            }
    # Check if there are any firmware images loaded
    if self.ListOfImages:
        logging(self, "Status", "Z4D loads the firmware images")

        # Iterate over the loaded firmware images and log their details
        for brand, value in self.ListOfImages["Brands"].items():
            for ota_image_file in value:
                logging(self, "Status", " --> Brand: %s Image File: %s" % (brand, ota_image_file))


def check_image_valid_version(self, brand, image_type, ota_image_file, headers):  # OK 13/10
    # Purpose is to check if the already imported image has a higher version or not.
    # If the version number is the same we will take the existing one

    existing_image = retrieve_image(self, image_type)
    if existing_image is None:
        # Strange
        return False

    brand_image, ota_image_file = existing_image
    if brand != brand_image:
        return True

    existing_image = self.ListOfImages["Brands"][brand][ota_image_file]
    if existing_image["originalVersion"] >= headers["image_version"]:
        # The up coming Image is older than the one already scaned
        # drop it
        return False
    # Existing Image is an older version comparing to what we load.
    # Overwrite with the new one.
    # Remove the old ota_image_file and replace by the new one
    del self.ListOfImages["Brands"][brand][ota_image_file]
    return True


def ota_extract_image_headers(self, subfolder, image):
    ota_image = _open_image_file(self, Path(self.pluginconf.pluginConf["pluginOTAFirmware"]) / subfolder / image)

    if not ota_image:
        return None

    offset = offset_start_firmware(self, ota_image)
    if offset is None:
        return None

    ota_image = ota_image[offset:]  # trim before reading header
    headers = unpack_headers(self, ota_image)

    if headers is None:
        return None

    logging_OTA_headers(self, headers)
    logging(self, "Status", "Available Firmware - ManufCode: 0x%04x ImageType: 0x%04x FileVersion: 0x%08x Size: %s Bytes Filename: %s" % (
        headers["manufacturer_code"],
        headers["image_type"],
        headers["image_version"],
        headers["image_size"],
        image)
    )

    return headers["image_type"], headers, ota_image


def _open_image_file(self, filename):  # OK 13/10
    try:
        with open(filename, "rb") as file:
            ota_image = file.read()

    except OSError as err:
        logging(self, "Error", f"_open_image_file - error when opening {filename} - {err}")
        return None

    if len(ota_image) < 69:
        logging(self, "Error", f"_open_image_file - invalid file size read {filename} - {len(ota_image)}")
        return None

    return ota_image


def offset_start_firmware(self, ota_image):
    """Locate the OTA file identifier 0x0BEEF11E inside the firmware."""
    
    MAGIC = 0x0BEEF11E

    for i in range(len(ota_image) - 4):
        val = struct.unpack_from("<I", ota_image, i)[0]
        if val == MAGIC:
            logging(self, "Debug", f"Found OTA magic at offset {i}")
            return i

    logging(self, "Error", "Zigbee OTA magic not found in firmware image")
    return None


def debug_header_bytes(self, ota_image):
    logging(self, "Debug", "---- OTA HEADER DEBUG ----")
    logging(self, "Debug", f"Total file size: {len(ota_image)} bytes")

    # print first 80 bytes in hex, grouped for clarity
    raw = ota_image[:80]
    logging(self, "Debug", "Raw first 80 bytes:")

    for i in range(0, 80, 16):
        line = ota_image[i:i + 16]
        logging(self, "Debug", f"  {i:04x}: {line.hex(' ')}")

    logging(self, "Debug", "--------------------------")


def unpack_headers(self, ota_image: bytes):
    """
    Parse a Zigbee OTA image header according to the Zigbee Cluster Library (ZCL)
    OTA Upgrade specification (Cluster 0x0019).

    This function works with **all vendors** (standard, Legrand, Tuya, Ikea, OSRAM,
    Sonoff, Schneider, etc.) because it only parses the mandatory header fields,
    checks the Field Control flags, and treats all other data as vendor-specific.

    ---------------------------------------------------------------------------
    Zigbee OTA Header Structure (Mandatory Section – Always Present)
    ---------------------------------------------------------------------------
    Offset | Size | Field Name          | Format | Description
    -------+------+----------------------+--------+-------------------------------
      0    |  4   | File Identifier      |  L     | Magic: 0x0BEEF11E (little-endian)
      4    |  2   | Header Version       |  H     | Usually 0x0001
      6    |  2   | Header Length        |  H     | Total header size in bytes
      8    |  2   | Field Control        |  H     | Bitmask defining optional fields
     10    |  2   | Manufacturer Code    |  H     | ZCL manufacturer ID
     12    |  2   | Image Type           |  H     | Device-specific firmware type
     14    |  4   | File Version         |  L     | Firmware version
     18    |  2   | Stack Version        |  H     | Zigbee stack version
     20    | 32   | Header String        | 32s    | ASCII name padded with 0x00
     52    |  4   | Image Size           |  L     | Total firmware size

    Total mandatory length = 56 bytes

    ---------------------------------------------------------------------------
    Optional Fields (based on Field Control bits)
    ---------------------------------------------------------------------------
    Bit 0 (0x01): Hardware version fields included:
      - Minimum Hardware Version (uint16)
      - Maximum Hardware Version (uint16)

    Additional metadata may follow but is **vendor-specific** and not standardized.

    ---------------------------------------------------------------------------
    Vendor-Specific Fields
    ---------------------------------------------------------------------------
    Everything between:
       offset + header_length
       and
       offset + parsed_optional_fields_end
    is considered vendor-specific metadata.

    Examples:
      - Legrand firmwares add proprietary metadata directly after the header.
      - Tuya OTAs embed custom TLV metadata.
      - OSRAM and IKEA sometimes append signature blocks.

    This function preserves vendor data in raw form under "vendor_data" without
    attempting to parse it.

    ---------------------------------------------------------------------------
    Searching for the OTA Magic
    ---------------------------------------------------------------------------
    The function automatically finds the OTA header by scanning for:
        0x1E F1 EE 0B   (little-endian 0x0BEEF11E)

    This allows working with:
      - Encapsulated OTAs
      - Bootloader images prepended
      - Vendor-wrapped images

    ---------------------------------------------------------------------------
    Returns:
        dict with the following keys:

        file_id: int
        header_version: int
        header_length: int
        field_control: int
        manufacturer_code: int
        image_type: int
        file_version: int
        stack_version: int
        header_string: str
        image_size: int
        min_hw_version: Optional[int]
        max_hw_version: Optional[int]
        sec_cred_version: Optional[int]
        vendor_data: bytes  # raw vendor metadata block
        payload_offset: int # absolute offset of firmware payload inside file

    Raises:
        ValueError: If the OTA magic cannot be found or the header is malformed.

    ---------------------------------------------------------------------------
    Example:
        headers = unpack_headers(ota_data)
        print(headers["manufacturer_code"])
        print(headers["image_size"])
    ---------------------------------------------------------------------------
    """
    debug_header_bytes(self, ota_image)
    
    # --- 1. Magic search ---
    MAGIC = b"\x1e\xf1\xee\x0b"
    offset = ota_image.find(MAGIC)
    if offset < 0:
        raise ValueError("OTA Magic not found in image (0x0BEEF11E).")

    # --- 2. Base header (56 bytes) ---
    fmt_base = "<L H H H H H L H 32s L"
    BASE_HEADER_SIZE = struct.calcsize(fmt_base)

    base_slice = ota_image[offset : offset + BASE_HEADER_SIZE]

    (
        file_id,
        header_version,
        header_length,
        field_ctrl,
        manufacturer_code,
        image_type,
        file_version,
        stack_version,
        header_str_raw,
        image_size,
    ) = struct.unpack(fmt_base, base_slice)


    # --- 3. Optional hardware version fields ---
    # After unpacking base header
    extra_offset = offset + BASE_HEADER_SIZE

    # Bit 0 → Hardware Version
    min_hw_version, max_hw_version = None, None
    if field_ctrl & 0x01:
        fmt_hw = "<H H"
        hw_size = struct.calcsize(fmt_hw)
        hw_slice = ota_image[extra_offset : extra_offset + hw_size]
        min_hw_version, max_hw_version = struct.unpack(fmt_hw, hw_slice)
        extra_offset += hw_size

    # Bit 2 → Security Credential Version
    sec_cred_version = None
    if field_ctrl & 0x04:
        sec_cred_version = ota_image[extra_offset]
        extra_offset += 1

    # Vendor-specific data
    vendor_data = ota_image[extra_offset : offset + header_length]

    # --- 5. Construct result dictionary ---
    header_string = header_str_raw.rstrip(b"\x00").decode( "ascii", errors="ignore" )
    
    return {
        "file_id": file_id,
        "header_version": header_version,
        "header_length": header_length,
        "header_fctl": field_ctrl,
        "manufacturer_code": manufacturer_code,
        "image_type": image_type,
        "image_version": file_version,
        "stack_version": stack_version,
        "header_str": header_string,
        "image_size": image_size,
        "min_hw_version": min_hw_version,
        "max_hw_version": max_hw_version,
        "security_cred_version": sec_cred_version,
        "vendor_data": vendor_data,
        "payload_offset": offset + header_length,
    }


def prepare_and_send_block(
    self,
    MsgSrcAddr,
    MsgEP,
    MsgFileOffset,
    intMsgImageVersion,
    intMsgImageType,
    intMsgManufCode,
    MsgBlockRequestDelay,
    MsgMaxDataSize,
    intMsgFieldControl,
    MsgSQN,
    disableACK=False
):
    """
    Prepare OTA image block request and send it to the device.

    Args:
        MsgSrcAddr: Source network address of device
        MsgEP: Endpoint
        MsgFileOffset: File offset for block
        intMsgImageVersion: Image version
        intMsgImageType: Image type
        intMsgManufCode: Manufacturer code
        MsgBlockRequestDelay: Requested delay between blocks
        MsgMaxDataSize: Maximum data size per block
        intMsgFieldControl: Field control flags
        MsgSQN: Message sequence
        disableACK: If True, disable ACK for this block
    """
    self.ListInUpdate["Retry"] = 0

    # Initialize block request and patch ImageType if needed
    block_request = initialize_block_request(
        self, MsgSrcAddr, MsgEP, MsgFileOffset, intMsgImageVersion,
        intMsgImageType, intMsgManufCode, MsgBlockRequestDelay,
        MsgMaxDataSize, intMsgFieldControl, MsgSQN
    )
    intMsgImageType = block_request["ImageType"]

    if intMsgImageType not in self.ListOfImages["ImageType"]:
        logging(self, "Error", f"prepare_and_send_block {MsgSrcAddr}/{MsgEP} - 0x{intMsgImageType:04X} image not found", MsgSrcAddr)
        return

    nwk_id = self.ListInUpdate.get("NwkId")
    if nwk_id and intMsgImageType != self.ListInUpdate.get("intImageType") and MsgSrcAddr != nwk_id:
        logging(self, "Error", f"prepare_and_send_block {MsgSrcAddr}/{MsgEP} - request update while another is in progress {nwk_id}")
        return

    logging(
        self,
        "Debug",
        f"prepare_and_send_block - [{int(MsgSQN, 16):3}] request - {MsgSrcAddr}/{MsgEP} "
        f"Offset: {int(MsgFileOffset, 16)} Version: 0x{intMsgImageVersion:08X} "
        f"Type: 0x{intMsgImageType:04X} Code: 0x{intMsgManufCode:04X} "
        f"Delay: {MsgBlockRequestDelay} MaxSize: {MsgMaxDataSize} "
        f"Control: 0x{intMsgFieldControl:02X}",
        MsgSrcAddr
    )

    # Update upgrade process status
    if self.ListInUpdate.get("Process") is None:
        start_upgrade_infos(self, MsgSrcAddr, intMsgImageType, intMsgManufCode, MsgFileOffset, MsgMaxDataSize)
        self.ListInUpdate["Process"] = "Started"
    else:
        self.ListInUpdate["Process"] = "OnGoing"

    self.ListInUpdate.update({
        "Status": "Block requested",
        "intFileOffset": int(MsgFileOffset, 16),
        "LastBlockSent": time.time()
    })

    logging(
        self,
        "Debug",
        f"prepare_and_send_block - Block Request for {MsgSrcAddr}/{block_request['ReqEp']} "
        f"Image Type: 0x{block_request['ImageType']:04X} Image Version: {block_request['ImageVersion']:08X} "
        f"Seq: {MsgSQN} Offset: {block_request['Offset']} Size: {block_request['MaxDataSize']} "
        f"FieldCtrl: 0x{block_request['FieldControl']:02X}",
        MsgSrcAddr
    )

    block_request_delay = MsgBlockRequestDelay / 1000.0  # Convert ms to seconds

    ota_send_block(self, MsgSrcAddr, MsgEP, intMsgImageType, intMsgImageVersion, block_request, disable_ack=disableACK, block_delay=block_request_delay)
    display_percentage_progress(self, MsgSrcAddr, MsgEP, intMsgImageType, MsgFileOffset)


def initialize_block_request(self, MsgSrcAddr, MsgEP, MsgFileOffset, intMsgImageVersion, intMsgImageType, intMsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, intMsgFieldControl, MsgSQN):
    # Patching in order to make Legrand update with Image Page Request working
    if intMsgManufCode == 0x00C8 and self.ListInUpdate["NwkId"] == MsgSrcAddr:
        # Request a Page, and Note a Block
        # For the time being, we are forcing a response with a Block
        intMsgImageType = self.ListInUpdate["intImageType"]
        intMsgManufCode = 0x1021
        MsgBlockRequestDelay = 0xffff
        MsgMaxDataSize = 40
        intMsgFieldControl = 0x00
        logging(
            self,
            "Debug",
            f"Fixing - [{int(MsgSQN, 16):3}] OTA image Block request - {MsgSrcAddr}/{MsgEP} Offset: {int(MsgFileOffset, 16)} version: 0x{intMsgImageVersion:08X} Type: 0x{intMsgImageType:04X} Code: 0x{intMsgManufCode:04X} Delay: {MsgBlockRequestDelay} MaxSize: {MsgMaxDataSize} Control: 0x{intMsgFieldControl:02X}",
            MsgSrcAddr           
        )

    return {
        "ReqAddr": MsgSrcAddr,
        "ReqEp": MsgEP,
        "Offset": MsgFileOffset,
        "ImageVersion": intMsgImageVersion,
        "ImageType": intMsgImageType,
        "ManufCode": intMsgManufCode,
        "BlockReqDelay": MsgBlockRequestDelay,
        "MaxDataSize": MsgMaxDataSize,
        "FieldControl": intMsgFieldControl,
        "Sequence": MsgSQN,
    }


def ota_aync_request( self, MsgSrcAddr, MsgEP, MsgIEEE, MsgFileOffset, image_version, image_type, intMsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, intMsgFieldControl, ):
    # We are receiving an OTA request
    # Check if we have an available firmware
    # If yes, then load the firmware on ZiGate

    logging(self, "Debug", f"ota_aync_request: There is async request coming {MsgSrcAddr} against {self.ListInUpdate.get('AuthorizedForUpdate')}", MsgSrcAddr)

    if MsgSrcAddr not in self.ListInUpdate.get("AuthorizedForUpdate", []):
        if self.pluginconf.pluginConf.get("autoServeOTA", False):
            return False

        # We need to prevent looping on serving if it is not expected!
        logging(self, "Error", f"ota_aync_request: There is no upgrade plan for that device, drop request from {MsgSrcAddr}", MsgSrcAddr)
        return False

    if self.ListInUpdate.get("NwkId"):
        logging(
            self,
            "Debug",
            f"ota_aync_request: There is an upgrade in progress {self.ListInUpdate['NwkId']}, drop request from {MsgSrcAddr}", MsgSrcAddr
        )
        return False

    if image_type not in self.ListOfImages.get("ImageType", {}):
        logging(self, "Log", f"ota_aync_request: No Firmware available to satisfy this request by {MsgSrcAddr}", MsgSrcAddr)
        return False

    entry = retrieve_image(self, image_type)
    if entry is None:
        logging(self, "Error", f"ota_aync_request: No Firmware available to satisfy this request by {MsgSrcAddr} !!!", MsgSrcAddr)

    brand, ota_image_file = entry
    available_image = self.ListOfImages.get("Brands", {}).get(brand, {}).get(ota_image_file, {})
    logging(self, "Debug", f"ota_aync_request: brand: {brand} ota_image_file: {ota_image_file}", MsgSrcAddr)

    # Sanity Checks
    if intMsgManufCode != available_image.get("intManufCode"):
        logging(
            self,
            "Error",
            f"ota_aync_request: {MsgSrcAddr} Available Firmware {ota_image_file} is not for this Manufacturer Code {intMsgManufCode}. Dropping",
            MsgSrcAddr
        )
        return False

    logging(self, "Debug", f"OTA heartbeat - Image: 0x{image_type:04X} from file: {ota_image_file}", MsgSrcAddr)

    # Loading Image on Zigate
    if not self.ImageLoaded:
        ota_load_image_to_zigate(self, image_type)

    return True


def notify_upgrade_end(
    self,
    Status,
    MsgSrcAddr,
    MsgEP,
    image_type,
    intMsgManufCode,
    intMsgImageVersion,
    ):  # OK 26/10

    _transferTime_hh, _transferTime_mm, _transferTime_ss = convert_time(int(time.time() - self.ListInUpdate["StartTime"]))
    _ieee = self.ListOfDevices[MsgSrcAddr]["IEEE"]
    _name = None
    _textmsg = ""
    for x in self.Devices:
        if self.Devices[x].DeviceID == _ieee:
            _name = self.Devices[x].Name

    if Status == "OK":
        _textmsg = "Device: %s has been updated with firmware %s in %s hour %s min %s sec" % (
            _name,
            intMsgImageVersion,
            _transferTime_hh,
            _transferTime_mm,
            _transferTime_ss,
        )
        logging(self, "Status", _textmsg, MsgSrcAddr)
        if "Firmware Update" in self.PluginHealth and len(self.PluginHealth["Firmware Update"]) > 0:
            self.PluginHealth["Firmware Update"]["Progress"] = "Success"

    elif Status == "Aborted":
        _textmsg = "Firmware update aborted error code %s for Device %s in %s hour %s min %s sec" % (
            Status,
            _name,
            _transferTime_hh,
            _transferTime_mm,
            _transferTime_ss,
        )

        if "Firmware Update" in self.PluginHealth and len(self.PluginHealth["Firmware Update"]) > 0:
            self.PluginHealth["Firmware Update"]["Progress"] = "Aborted"
    elif Status == "Failed":
        _textmsg = "Firmware update aborted error code %s for Device %s in %s hour %s min %s sec" % (
            Status,
            _name,
            _transferTime_hh,
            _transferTime_mm,
            _transferTime_ss,
        )
        if "Firmware Update" in self.PluginHealth and len(self.PluginHealth["Firmware Update"]) > 0:
            self.PluginHealth["Firmware Update"]["Progress"] = "Failed"
    elif Status == "More":
        _textmsg = "Device: %s has been updated to latest firmware in %s hour %s min %s sec, but additional Image needed" % (
            _name,
            _transferTime_hh,
            _transferTime_mm,
            _transferTime_ss,
        )
        if "Firmware Update" in self.PluginHealth and len(self.PluginHealth["Firmware Update"]) > 0:
            self.PluginHealth["Firmware Update"]["Progress"] = "More"

    self.adminWidgets.updateNotificationWidget(self.Devices, _textmsg)


def convert_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return hours, minutes, seconds


def logging_OTA_headers(self, headers):
    """
    Print OTA header fields for debugging.

    - Skips vendor_data and stack_version by default.
    - Decodes file_version into Application Release/Build and Stack Release/Build.
    - Decodes stack version and security credential version into human-readable names.
    """

    if not self.pluginconf.pluginConf.get("debugOTA", False):
        return

    EXCLUDED_ATTRIBUTES = {"stack_version", "vendor_data", "image_version"}
    for attr, value in headers.items():
        if attr not in EXCLUDED_ATTRIBUTES:
            if isinstance(value, int):
                logging( self, "Debug", f"==>    {attr}: 0x{value:X}")
            else:
                logging( self, "Debug", f"==>    {attr}: {value}")

    # Decoding File Version
    file_version = headers["file_version"]
    logging( self, "Debug", f"==>    File Version:        0x{file_version:08X}")
    logging( self, "Debug", f"==>    Application Release: 0x{(file_version & 0xFF000000) >> 24:02X}", )
    logging( self, "Debug", f"==>    Application Build:   {(file_version & 0x00FF0000) >> 16}", )
    logging( self, "Debug", f"==>    Stack Release:       {(file_version & 0x0000FF00) >> 8}", )
    logging( self, "Debug", f"==>    Stack Build:         {file_version & 0x000000FF}" )

    # Stack version
    stack_version = headers["stack_version"]
    stack_names = {
        0x0000: "ZigBee 2006",
        0x0001: "ZigBee 2007",
        0x0002: "ZigBee Pro",
        0x0003: "ZigBee IP",
    }
    logging( self, "Debug", f"==>    Stack Name:          {stack_names.get(stack_version, 'Reserved')}")

    # Security Credential Version (optional)
    security_cred_version = headers.get("security_cred_version")
    if security_cred_version is not None:
        credential_names = {
            0x00: "SE 1.0",
            0x01: "SE 1.1",
            0x02: "SE 2.0",
        }
        logging( self, "Debug", f"==>    Security Credential: {credential_names.get(security_cred_version, 'Reserved')}", )
    else:
        logging( self, "Debug", "==>     Security Credential: None")
        
    vendor_data = headers.get("vendor_data", b"")
    if vendor_data:
        max_len = 64  # print only first 64 bytes
        data_to_log = vendor_data[:max_len]
        hex_data = ' '.join(f'{b:02X}' for b in data_to_log)
        logging( self, "Debug", f"==>    Vendor Data:         ({len(vendor_data)} bytes, first {len(data_to_log)} shown): {hex_data}")


def display_percentage_progress(self, MsgSrcAddr, MsgEP, intMsgImageType, MsgFileOffset):
    """
    Display firmware transfer progress and update device health.
    """
    # Ensure file offset is an integer
    offset = int(MsgFileOffset, 16) if isinstance(MsgFileOffset, str) else MsgFileOffset
    total_size = self.ListInUpdate.get("intSize", 1)  # Avoid division by zero

    completion_pct = round((offset / total_size) * 100, 1)

    # Log progress every 5%
    if completion_pct % 5 == 0:
        logging(self, "Status", f"Firmware transfer for {MsgSrcAddr}/{MsgEP} - Progress: {completion_pct:4.1f}%", MsgSrcAddr)
        update_firmware_health(self, MsgSrcAddr, completion_pct)


def update_firmware_health(self, MsgSrcAddr, completion):
    """
    Update firmware transfer progress in PluginHealth.
    """
    firmware_update_health = self.PluginHealth.setdefault("Firmware Update", {})
    firmware_update_health["Progress"] = f"{round(completion)}%"
    firmware_update_health["Device"] = MsgSrcAddr


def start_upgrade_infos(self, MsgSrcAddr, intMsgImageType, intMsgManufCode, MsgFileOffset, MsgMaxDataSize):
    """Start the firmware upgrade process for a device."""
    
    # Retrieve the image entry for the requested image type
    entry = retrieve_image(self, intMsgImageType)
    if entry is None:
        logging(self, "Error", f"start_upgrade_infos: No firmware available for request by {MsgSrcAddr}", MsgSrcAddr)
        return
    brand, ota_image_file = entry
    available_image = self.ListOfImages["Brands"][brand][ota_image_file]

    # Populate ListInUpdate with image details
    self.ListInUpdate.update({
        "intSize": available_image["intSize"],
        "ImageVersion": available_image["intImageVersion"],
        "Process": available_image["Process"],
        "Decoded Header": available_image["Decoded Header"],
        "OtaImage": available_image["OtaImage"],
        "ImageType": f"{intMsgImageType:04x}",
        "intImageType": intMsgImageType,
        "NwkId": MsgSrcAddr,
        "intManufCode": intMsgManufCode,
        "intFileOffset": int(MsgFileOffset, 16),
        "Brand": brand,
        "FileName": ota_image_file,
        "LastBlockSent": 0,
        "StartTime": time.time(),
    })

    # Initialize or reset the "Firmware Update" section in PluginHealth
    self.PluginHealth["Firmware Update"] = {
        "Progress": "0%",
        "Device": MsgSrcAddr
    }

    # Retrieve device name from IEEE address
    _ieee = self.ListOfDevices[MsgSrcAddr]["IEEE"]
    _name = next((dev.Name for dev in self.Devices.values() if dev.DeviceID == _ieee), None)

    # Estimate upload time. We expect to send 5 blocks in 1 second
    ota_profile = VENDOR_PROFILES.get( intMsgManufCode, DEFAULT_OTA_PROFILE )
    block_size = min(MsgMaxDataSize, ota_profile["max_data"])

    estimated_blocks = math.ceil(self.ListInUpdate["intSize"] / block_size)
    estimated_time_sec = estimated_blocks / 5

    # Convert estimated time into hours, minutes, and seconds
    _durhh, _durmm, _durss = convert_time(estimated_time_sec)

    # Generate notification text
    _textmsg = (f"Firmware update started for Device: {_name} with {self.ListInUpdate['FileName']} - "
                f"Estimated Time: {_durhh} H {_durmm} min {_durss} sec")
    self.adminWidgets.updateNotificationWidget(self.Devices, _textmsg)


def loading_zigbee_ota_index( self ):
    
    if not self.internet_available:
        return

    self.zigbee_ota_index = []
    if self.pluginconf.pluginConf["internetAccess"]:
        self.zigbee_ota_index = _load_json_from_url( self, self.pluginconf.pluginConf["ZigbeeOTA_Repository"] )
        self.zigbee_ota_index.extend( convert_ikea_format_to_list( _load_json_from_url( self, self.pluginconf.pluginConf["IkeaTradfri_Repository"] )) )
        self.zigbee_ota_index.extend( convert_sonoff_format_to_list( _load_json_from_url( self, self.pluginconf.pluginConf["Sonoff_Repository"] )) )


def convert_sonoff_format_to_list(zigbee_sonoff_index):
    return [
        {
            "fileVersion": image["fw_file_version"],
            "manufacturerCode": image["fw_manufacturer_id"],
            "imageType": image["fw_image_type"],
            "url": image["fw_binary_url"],
        }
        for image in zigbee_sonoff_index
    ]


def convert_ikea_format_to_list(zigbee_ikea_index):
    return [
        {
            "fileVersion": int(f"{image['fw_file_version_MSB']:04x}{image['fw_file_version_LSB']:04x}", 16),
            "manufacturerCode": image["fw_manufacturer_id"],
            "imageType": image["fw_image_type"],
            "url": image["fw_binary_url"],
        }
        for image in zigbee_ikea_index
        if "fw_file_version_MSB" in image and "fw_file_version_LSB" in image
    ]


def check_ota_availability_from_index( self, manufcode, imagetype, fileversion ):
    if self.zigbee_ota_index is None:
        return None
    logging(self, "Debug", "check_ota_availability_from_index: Index Size: %s Searching ImageType: 0x%04x (%s) Version: 0x%08x (%s) ManufCode: 0x%04x (%s)" %(
        len(self.zigbee_ota_index), imagetype, imagetype, fileversion, fileversion, manufcode, manufcode,))

    return next((_image for _image in self.zigbee_ota_index if (_image["manufacturerCode"] == manufcode and _image["imageType"] == imagetype and _image["fileVersion"] > fileversion)), {})


def notify_ota_firmware_available(self, srcnwkid, manufcode, imagetype, fileversion, _ota_available ):

    folder = next((OTA_CODES[supported_manufacturer]["Folder"] for supported_manufacturer in OTA_CODES if OTA_CODES[supported_manufacturer]["ManufCode"] == manufcode), None)

    logging(self, "Status", "We have detected a potential new firmware for the device %s [%s]" %( get_device_nickname( self, NwkId=srcnwkid, ), srcnwkid ))
    logging(self, "Status", "   current version: %s" % fileversion)
    logging(self, "Status", "     firmware type: %s" % imagetype)
    logging(self, "Status", "    newest version: %s" % _ota_available["fileVersion"])
    logging(self, "Status", "     firmware type: %s" % _ota_available["imageType"])
    logging(self, "Status", "   URL to download: %s" % _ota_available["url"])

    if srcnwkid in self.ListOfDevices:
        if "OTAUpdate" not in self.ListOfDevices[srcnwkid]:
            self.ListOfDevices[srcnwkid]["OTAUpdate"] = {}
        if imagetype in self.ListOfDevices[srcnwkid]["OTAUpdate"]:
            self.ListOfDevices[srcnwkid]["OTAUpdate"][imagetype].clear()
        self.ListOfDevices[srcnwkid]["OTAUpdate"][imagetype] = {
            "currentversion": str(fileversion),
            "newestversion" : str(_ota_available["fileVersion"]),
            "url": _ota_available["url"],
        }
        
    if folder:
        logging(self, "Status", "   Folder to store: %s" % folder)
    else:
        logging(self, "Status", "   to get this Manufacturer supported: %s" % manufcode)
        logging(self, "Status", "   provide those informations: %s" % _ota_available)
        logging(self, "Status", "   open an Issue on GitHub here: https://github.com/zigbeefordomoticz/Domoticz-Zigbee/issues/new?assignees=&labels=&template=feature_request.md&title=")



def _load_json_from_url(self, url):

    retries = 3
    last_reason = "unknown error"

    for _ in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                return json.load(response)

        except urllib.error.HTTPError as e:
            # HTTPError may wrap a timeout
            if e.code in (429, 504):
                last_reason = f"HTTP {e.code}: {e.reason}"
            elif isinstance(e.reason, socket.timeout):
                last_reason = f"HTTPError timeout: {e.reason}"
            else:
                last_reason = f"HTTPError: {e.reason}"

        except urllib.error.URLError as e:
            if isinstance(e.reason, socket.timeout):
                last_reason = f"URLError timeout: {e.reason}"
            else:
                last_reason = f"URLError: {e.reason}"

        except socket.timeout as e:
            last_reason = f"socket.timeout: {e}"

        time.sleep(1)

    logging(self, "Error",
            f"loading_zigbee_ota_index: Unable to access {url} Reason: {last_reason}")
    return []


def trace_ota_block(self, dest_addr, image_type_hex, offset, size, sequence, raw_ota_data):
    """
    Trace OTA block data into a dedicated file.

    Filename:
        ota_blocks_<dest_addr>_<image_type>.log

    Logged fields:
        timestamp | seq | offset | size | data_hex
    """
    filename = f"ota_blocks_{dest_addr}_{image_type_hex}.log"
    log_path = self.pluginconf.pluginConf.get("pluginLogs", "/tmp")
    full_path = os.path.join(log_path, filename)

    # Convert bytes → hex string
    data_hex = raw_ota_data.hex()

    try:
        with open(full_path, "a", encoding="utf-8") as f:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            f.write(
                f"{ts} | Seq:{sequence} | Offset:{offset} | "
                f"Size:{size} | Data:{data_hex}\n"
            )

    except Exception as e:
        logging(self, "Error", f"OTA trace logging {full_path} failed: {e}")
