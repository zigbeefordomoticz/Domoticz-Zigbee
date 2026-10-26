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
    ImageLoaded: The image headers last loaded into a ZiGate (native mode only).
    ota_requests: The OTA requests by IEEE, in arrival order: the queue and the transfers in progress.
    zigbee_ota_index: The Zigbee OTA index.
    zigbee_ota_found_in_index: The list of Zigbee OTA firmware found in the index.
    local_image_available_logged: The (IEEE, current version, image version) already reported by log_local_image_available().
    once: Flag indicating if the OTA process has started.

Methods:
    cancel_current_firmware_update: Cancel the firmware update of a device, or all of them.
    ota_image_block_request: Handle the OTA image block request.
    ota_image_page_request: Handle the OTA image page request.
    ota_upgrade_end_request: Handle the OTA upgrade end request.
    heartbeat: Perform the OTA heartbeat.
    restapi_list_of_firmware: Get the list of available firmware.
    restapi_firmware_update: Perform the firmware update.
    query_next_image_request: Handle the OTA query next image request.
"""

import contextlib
import json
import math
import os
import socket
import struct
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime
from os import listdir
from os.path import exists, isfile, join
from pathlib import Path
import http.client

import random

from Modules.sendZigateCommand import sendZigateCmd
from Modules.tools import get_device_nickname, mainPoweredDevice
from Modules.zigateConsts import ADDRESS_MODE, ZIGATE_EP
from Zigbee.zclRawCommands import (zcl_raw_default_response,
                                   zcl_raw_ota_image_block_response_abort,
                                   zcl_raw_ota_image_block_response_success,
                                   zcl_raw_ota_image_notify,
                                   zcl_raw_ota_query_next_image_response,
                                   zcl_raw_ota_upgrade_end_response)

# Maximum number of Image Notify retries (one per heartbeat) while waiting for a notified
# device to ask for its image, and grace period (seconds) after the first notification.
# A device that does not answer gives its transfer slot back but stays in the queue.
OTA_MAX_NOTIFY_RETRY = 10
OTA_NOTIFY_TIMEOUT = 600

# Up to OTA_MAX_TRANSFERS devices are upgraded at the same time. A battery-powered device
# that asks on its own gets one more slot, up to OTA_MAX_TRANSFERS_WITH_BATTERY, as it may
# not ask again for hours. The other requests wait in the queue for a free slot.
OTA_MAX_TRANSFERS = 2
OTA_MAX_TRANSFERS_WITH_BATTERY = 3

# A queued device stays authorized that long: a sleepy device asks for its image on its
# own schedule (ZCL rev 8 11.8.2). The request is then dropped and the user notified.
OTA_QUEUE_WAIT = 24 * 3600

# A transfer without any block request for that long (seconds) is dropped.
OTA_BLOCK_TIMEOUT = 300

# With several transfers in progress, the delay between two blocks of a device is multiplied
# by their number, so that together they request about as many blocks as a single transfer.
# The scaled delay (seconds) stays below this, so a client never waits long enough to repeat
# its request; a client asking for a longer delay keeps its own.
OTA_MAX_SCALED_BLOCK_DELAY = 1.0

# States of an OTA request
OTA_QUEUED = "Queued"          # waiting for a free transfer slot, not notified yet
OTA_NOTIFYING = "Notifying"    # Image Notify sent, waiting for the device: holds a slot
OTA_WAITING = "Waiting"        # did not answer the notifications: no slot, still authorized
OTA_TRANSFER = "Transfer"      # image offered, blocks served: holds a slot
OTA_ACTIVE_STATES = (OTA_NOTIFYING, OTA_TRANSFER)

OTA_CLUSTER_ID = "0019"

# Error codes put in the context of every OTA Error log ({"Error code": "OTAxxyy", ...}).
# xx is the area, yy the number within it. Never reuse or renumber a code: users quote them.
OTA_ERROR_CODES = {
    # 00 - firmware files (OTAFirmware folders)
    "OTA0001": "Firmware file cannot be read",
    "OTA0002": "Firmware file too short to be an OTA image",
    "OTA0003": "OTA file identifier 0x0BEEF11E not found in the firmware file",
    "OTA0004": "Truncated or malformed OTA header in the firmware file",
    # 01 - Query Next Image (reserved)
    # 02 - image block / page transfer
    "OTA0201": "Requested image type is not loaded",
    "OTA0202": "Block request from another device while a transfer is in progress",  # not raised since the OTA queue
    # 03 - Upgrade End
    "OTA0301": "Device aborted the upgrade (ABORT 0x95)",
    "OTA0302": "Device rejected the downloaded image (INVALID_IMAGE 0x96)",
    "OTA0303": "Unexpected Upgrade End status",
    # 04 - WebUI / REST API
    "OTA0401": "Firmware update request with missing attributes",
    # 05 - online firmware index
    "OTA0501": "Online firmware index cannot be loaded",
    # 09 - diagnostics
    "OTA0901": "OTA block trace file cannot be written",
}

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

    0x117C: {  # IKEA (TRÅDFRI / Dirigera)
        "max_data": 64,
        "min_delay": 0.250,
        "retry": 3,
        "notes": "Generally robust; failures often mesh-related."
    },

    0x1021: {  # Legrand / Netatmo
        "max_data": 64,
        "min_delay": 0.250,
        "retry": 3,
        "notes": "Very picky image metadata; some devices require vendor-style packaging."
    },

    0x1015: {  # Develco / frient
        "max_data": 56,
        "min_delay": 0.16,
        "retry": 2,
        "notes": "Known mid-OTA stalls; allow long idle periods."
    },

    0x128B: {  # NodOn
        "max_data": 52,
        "min_delay": 0.12,
        "retry": 3,
        "notes": "Verify manufacturer/image type; some ‘No image available’ errors."
    },

    0x1189: {  # Osram / LEDVANCE
        "max_data": 56,
        "min_delay": 0.12,
        "retry": 3,
        "notes": "Generally easier OTA; check mesh stability during upgrade."
    },
    0xBBAA: {  # Osram / LEDVANCE
        "max_data": 56,
        "min_delay": 0.12,
        "retry": 3,
        "notes": "Generally easier OTA; check mesh stability during upgrade."
    },
    0x110C: {  # Osram / LEDVANCE
        "max_data": 56,
        "min_delay": 0.12,
        "retry": 3,
        "notes": "Generally easier OTA; check mesh stability during upgrade."
    },
}


# A Zigbee manufacturer code is NOT unique across vendors: 0x1037 is shipped by
# Eurotronic, LiXee and Lumi, 0x1015 by Develco and frient. OTA matching is done on
# the (manufacturer_code, image_type) pair read from the image header itself (see
# is_image_for_query_next_image_request), so an entry below only decides which
# folders are scanned and which label the WebUI shows - it is never a matching key.
#
# A shared manufacturer code therefore gets ONE generic entry that owns it, so the
# code -> folder lookup has a single unambiguous answer and all images for that code
# land under one brand. "Folder" is a folder name, or a list of them: a generic entry
# lists its canonical GENERIC-<code> folder first, followed by the former per-vendor
# folders, which keep being scanned so an existing installation does not lose
# firmware already dropped there.
OTA_CODES = {
    "Danfoss": {"Folder": "DANFOSS", "ManufCode": 0x1246, "ManufName": "Danfoss", "Enabled": True},
    "Develco-frient": {"Folder": ["GENERIC-1015", "DEVELCO"], "ManufCode": 0x1015, "ManufName": "Develco / frient A/S", "Enabled": True},
    "EcoDim": {"Folder": "ECO-DIM", "ManufCode": 0x126a, "ManufName": "EcoDim", "Enabled": True},
    "Eurotronic-LiXee-Lumi": {"Folder": ["GENERIC-1037", "EUROTRONICS", "LIXEE", "LUMI"], "ManufCode": 0x1037, "ManufName": "Eurotronic / LiXee / Lumi", "Enabled": True},
    "Ikea": {"Folder": "IKEA-TRADFRI", "ManufCode": 0x117C, "ManufName": "IKEA of Sweden", "Enabled": True},
    "Innr": {"Folder": "INNR", "ManufCode": 0x1166, "ManufName": "INNR", "Enabled": True},
    "Ledvance": {"Folder": "LEDVANCE", "ManufCode": 0x1189, "ManufName": "LEDVANCE", "Enabled": True},
    "Legrand": {"Folder": "LEGRAND", "ManufCode": 0x1021, "ManufName": "Legrand", "Enabled": True},
    "Nodon": {"Folder": "NODON", "ManufCode": 0x128b, "ManufName": "NodOn", "Enabled": True},
    "Osram1": {"Folder": "OSRAM", "ManufCode": 0xBBAA, "ManufName": "OSRAM", "Enabled": True},
    "Osram2": {"Folder": "LEDVANCE", "ManufCode": 0x110C, "ManufName": "OSRAM", "Enabled": True},
    "Philips": {"Folder": "PHILIPS", "ManufCode": 0x100B, "ManufName": "Philips", "Enabled": True},
    "Salus": {"Folder": "SALUS", "ManufCode": 0x1078, "ManufName": "Computime", "Enabled": True},
    "Schneider": {"Folder": "SCHNEIDER-WISER", "ManufCode": 0x105E, "ManufName": "Schneider Electric", "Enabled": True},
    "SonOff": {"Folder": "SONOFF", "ManufCode": 0x1286, "ManufName": "Sonoff", "Enabled": True},
    "Xiaomi": {"Folder": "XIAOMI", "ManufCode": 0x115f, "ManufName": "Xiaomi", "Enabled": True},
    "devbis": {"Folder": "XIAOMI", "ManufCode": 0xdb15, "ManufName": "Lumi", "Enabled": True},
    "z03mmc": {"Folder": "XIAOMI", "ManufCode": 0x0084, "ManufName": "Lumi", "Enabled": True},
    "Namron": {"Folder": "NAMRON", "ManufCode": 0x1224, "ManufName": "Namron", "Enabled": True},
}


def ota_brand_folders(ota_code_entry):
    """Firmware folders to scan for one OTA_CODES entry.

    "Folder" is either a single folder name or a list of them; a generic entry
    owning a shared manufacturer code lists its canonical folder first, followed by
    the former per-vendor folders kept for backward compatibility.
    """
    folder = ota_code_entry["Folder"]

    return [folder] if isinstance(folder, str) else list(folder)


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

        # Properties for firmware/image management
        self.ListOfImages = {}  # List of available firmware loaded at plugin startup

        # Image headers last loaded into a ZiGate (native mode only)
        self.ImageLoaded = {
            "ImageVersion": None,
            "image_type": None,
            "manufacturer_code": None,
            "LoadedTimeStamp": 0,
        }

        # OTA requests by IEEE, in arrival order: the queue and the transfers in progress.
        # See new_ota_request() for the fields and OTA_QUEUED ... OTA_TRANSFER for the states.
        self.ota_requests = {}

        self.zigbee_ota_index = None
        self.zigbee_ota_found_in_index = []
        self.local_image_available_logged = set()
        self.once = True
        
        # Load Zigbee OTA index and scan the folder
        loading_zigbee_ota_index( self )
        logging(self, "Debug", "zigbee_ota_index: %s" %self.zigbee_ota_index)
        ota_scan_folder(self)


    def cancel_current_firmware_update(self, nwkid=None):
        """Drop the OTA request of a device, or every request."""
        for request in list(self.ota_requests.values()):
            if nwkid is None or request["NwkId"] == nwkid:
                end_ota_request(self, request, "Cancelled")


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
            f"Control: 0x{intMsgFieldControl:02X}", MsgSrcAddr
        )

        request = ota_request_for_block(self, MsgSrcAddr)
        if request is None:
            return

        prepare_and_send_block(
            self, request, MsgSrcAddr, MsgEP, MsgFileOffset, intMsgImageVersion,
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
            MsgSrcAddr, MsgEP, int(MsgFileOffset, 16), intMsgImageVersion, intMsgImageType, intMsgManufCode, MsgMaxDataSize, PageSize , intResponseSpacing, intMsgFieldControl, ), MsgSrcAddr)

        request = ota_request_for_block(self, MsgSrcAddr)
        if request is None:
            return
   
        # Page Size: The value indicates the number of bytes to be sent by the server before the client sends another Image Page
        #            Request command. In general, page size value SHALL be larger than the maximum data size value. 
        # Max data Size: The value indicates the largest possible length of data (in bytes) that the client can receive at once.
        # Response Spacing: The value indicates how fast the server SHALL send the data (via Image Block Response command) to the client. 
        # The value is determined by the client. The server SHALL wait at the minimum the (response) spacing value before sending more data to the client. 
        # The value is in milliseconds.
        
        # So we are going to break the page into blocks of at most max data size, as
        # Image Block Responses with increasing offset and sequence number (ZCL rev 8
        # 11.13.7.4 / 11.13.8.2.5), until the page or the image is complete. The offset
        # moves by what was actually sent: ota_send_block() may cap the block size to
        # the vendor profile.
        entry = retrieve_image(self, intMsgImageType, intMsgManufCode)
        if entry is None:
            _context = {"Error code": "OTA0201", "Request": "Image Page", "ImageType": f"0x{intMsgImageType:04X}", "ManufCode": f"0x{intMsgManufCode:04X}",
                        "FileVersion": f"0x{intMsgImageVersion:08X}", "Offset": int(MsgFileOffset, 16)}
            logging(self, "Error", f"ota_image_page_request {MsgSrcAddr}/{MsgEP} - 0x{intMsgImageType:04X} image not found", MsgSrcAddr, _context)
            return
        image_size = request["intSize"]

        _sqn = int(MsgSQN,16)
        _file_offset = int(MsgFileOffset,16)
        page_end = min(_file_offset + PageSize, image_size)
        while _file_offset < page_end:
            prepare_and_send_block(
                self, 
                request,
                MsgSrcAddr, 
                MsgEP, 
                "%08x" %_file_offset, 
                intMsgImageVersion, 
                intMsgImageType, 
                intMsgManufCode, 
                intResponseSpacing, 
                min(MsgMaxDataSize, page_end - _file_offset),
                intMsgFieldControl, 
                "%02x" %_sqn, 
                disableACK=True
            )

            sent_up_to = request.get("Sent", 0)
            if sent_up_to <= _file_offset:
                # Nothing was sent (error already logged by prepare_and_send_block)
                break
            _file_offset = sent_up_to
            _sqn = (_sqn + 1) & 0xFF


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
            MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus), MsgSrcAddr)

        request = find_ota_request(self, MsgSrcAddr)
        if request is None or request["State"] != OTA_TRANSFER:
            logging(self, "Warning", "ota_upgrade_end_request - Receive Firmware Completed from %s with status %s most likely a duplicated packet as there is no transfer in progress for it. " % (MsgSrcAddr, MsgStatus), MsgSrcAddr)
            return

        if MsgStatus == "00":
            logging(self, "Status", "OTA upgrade completed with success - %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s" % (
                MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus), MsgSrcAddr)
            ota_upgrade_end_response(self, MsgSQN, MsgSrcAddr, MsgEP, intMsgImageVersion, image_type, intMsgManufCode)
            notify_upgrade_end(self, request, "OK", MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion)

        elif MsgStatus == "95":
            _context = {"Error code": "OTA0301", "Status": MsgStatus, "ImageType": f"0x{image_type:04X}", "ManufCode": f"0x{intMsgManufCode:04X}", "FileVersion": f"0x{intMsgImageVersion:08X}"}
            logging(self, "Error", "OTA Firmware aborted - %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s" % (
                MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus), MsgSrcAddr, _context)
            notify_upgrade_end(self, request, "Aborted", MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion)

        elif MsgStatus == "96":
            _context = {"Error code": "OTA0302", "Status": MsgStatus, "ImageType": f"0x{image_type:04X}", "ManufCode": f"0x{intMsgManufCode:04X}", "FileVersion": f"0x{intMsgImageVersion:08X}"}
            logging(self, "Error", "OTA Firmware image validation failed %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s" % (
                MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus), MsgSrcAddr, _context)
            notify_upgrade_end(self, request, "Failed", MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion)

        elif MsgStatus == "97":
            logging(self, "Warning", "OTA Firmware image wait for data %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s" % (
                MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus), MsgSrcAddr)
            return
        elif MsgStatus == "99":
            logging(self, "Warning", "OTA Firmware  The downloaded image was successfully received, but there is a need for additional image %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s" % (
                MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus), MsgSrcAddr)
            notify_upgrade_end(self, request, "More", MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion)

        else:
            _context = {"Error code": "OTA0303", "Status": MsgStatus, "ImageType": f"0x{image_type:04X}", "ManufCode": f"0x{intMsgManufCode:04X}", "FileVersion": f"0x{intMsgImageVersion:08X}"}
            logging(self, "Error", "OTA Firmware unexpected error %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s" % (
                MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus), MsgSrcAddr, _context)
            notify_upgrade_end(self, request, "Aborted", MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion)

        cleanup_after_completed_upgrade(self, request, MsgStatus)


    def heartbeat(self):
        """Every heartbeat (HEARTBEAT, 5 s): notification retries and timeouts of each
        request, then the queued requests are notified while a transfer slot is free."""

        now = time.time()
        for request in list(self.ota_requests.values()):
            nwk_id = request["NwkId"]
            state = request["State"]

            logging(
                self,
                "Debug",
                "ota_heartbeat - NwkId: %s State: %s Process: %s Image: 0x%04X Block Sent: %s Notified: %s Retry Notif: %s Queued: %s"
                % (nwk_id, state, request["Process"], request["intImageType"], request["LastBlockSent"], request["NotifiedTimeStamp"], request["Retry"], request["QueuedTime"]), nwk_id
            )

            if state == OTA_TRANSFER:
                if now > request["LastBlockSent"] + OTA_BLOCK_TIMEOUT:
                    _handle_ota_timeout(self, request)

            elif state == OTA_NOTIFYING:
                if request["Retry"] < OTA_MAX_NOTIFY_RETRY:
                    _retry_notification(self, request)

                # Give the slot back once the notification retries are exhausted, or if the
                # device never engaged within the grace period after the first notification.
                if request["Retry"] >= OTA_MAX_NOTIFY_RETRY or now > request["NotifiedTimeStamp"] + OTA_NOTIFY_TIMEOUT:
                    _handle_timeout(self, request)

            elif now > request["QueuedTime"] + OTA_QUEUE_WAIT:
                _handle_queue_timeout(self, request)

        notify_queued_requests(self)


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
        Queue a firmware update for one or several Zigbee devices via REST API.

        Args:
            data (list[dict]): List of update requests, each with keys:
                - "Brand": str
                - "FileName": str
                - "NwkId": str
                - "Ep": int
                - "ForceUpdate": bool
        Returns:
            list[dict]: one result per request, {"NwkId", "Status": "Queued" | "Rejected", "Reason"}
        Note:
            The devices are upgraded OTA_MAX_TRANSFERS at a time, oldest request first.
        """
        if not data:
            logging(self, "Warning", "No update data received.")
            return []

        return [
            firmware_update(
                self,
                update_request.get("Brand"),
                update_request.get("FileName"),
                update_request.get("NwkId"),
                update_request.get("Ep"),
                update_request.get("ForceUpdate", False),
            )
            for update_request in data
        ]


    def query_next_image_request(self, srcnwkid, srcep, Sqn, Data):
        # This is a Client -> Server (direction set to 0x00)
        # The server takes the client’s information in the command and determines whether it has a suitable image for the particular client.
        # The decision SHOULD be based on specific policy that is specific to the upgrade server and outside the scope of this document... 
        # However, a recommended default policy is for the server to send back a response that indicates the availability of an image
        # that matches the manufacturer code, image type, and the highest available file version of that image on the server. 
        # However, the server MAY choose to up- grade or downgrade a clients’ image, as its policy dictates. 
        # If client’s hardware version is included in the command, the server SHALL examine the value against the minimum and
        # maximum hardware versions in- cluded in the OTA file header.

        # Command: 0x01

        fieldcontrol = int(Data[:2],16)
        logging(self, "Debug", f" Manuf: {Data[2:6]} Type: {Data[6:10]} Version: {Data[10:18]}", srcnwkid)
        manufcode = struct.unpack("H", bytes.fromhex(Data[2:6]))[0]
        imagetype = struct.unpack("H", bytes.fromhex(Data[6:10]))[0]
        currentVersion = struct.unpack("I", bytes.fromhex(Data[10:18]))[0]

        # Field control bit 0: Hardware Version present (ZCL rev 8, table 11-19)
        hardware_version = None
        if fieldcontrol & 0x01 and len(Data) >= 22:
            hardware_version = struct.unpack("<H", bytes.fromhex(Data[18:22]))[0]

        logging(self, "Debug", "OTA Query Next Image request for %s/%s [%s] - Control: 0x%02X Manuf: 0x%04X Type: 0x%04X Version: 0x%08X HW: %s" % (
            srcnwkid, srcep, Sqn, fieldcontrol, manufcode, imagetype, currentVersion, hardware_version ), srcnwkid)

        ota_client = self.ListOfDevices.setdefault(srcnwkid, {}).setdefault("OTAClient", {})
        ota_client["ManufacturerCode"] = manufcode
        ota_client["ImageType"] = imagetype
        ota_client["CurrentImageVersion"] = currentVersion
        
        request = find_ota_request(self, srcnwkid)
        force_update = request is not None and request["ForceUpdate"]

        image_found = is_image_for_query_next_image_request( self, srcnwkid, manufcode, imagetype, currentVersion , force_update)
        hardware_refused = bool(image_found) and not is_hardware_version_compatible(self, srcnwkid, image_found, hardware_version)
        if hardware_refused:
            image_found = None

        if image_found and request is not None and (image_found["intManufCode"], image_found["ImageType"]) != (request["intManufCode"], request["intImageType"]):
            logging(self, "Log", "OTA Query Next Image request - %s asks for image 0x%04X/0x%04X, not for the requested firmware %s" % (
                srcnwkid, manufcode, imagetype, request["FileName"]), srcnwkid)
            image_found = None

        if image_found:
            if request is None and self.pluginconf.pluginConf.get("autoServeOTA", False) and "IEEE" in self.ListOfDevices[srcnwkid]:
                # autoServeOTA: the device that asks is queued, and served now if a slot is free
                brand, file_name = retrieve_image(self, imagetype, manufcode, exact=True)
                request = new_ota_request(self, srcnwkid, srcep, brand, file_name, auto_serve=True)
                self.ota_requests[request["IEEE"]] = request
                logging(self, "Debug", f"OTA Query Next Image request - autoServeOTA queues {srcnwkid} for {file_name}", srcnwkid)

            if request is not None:
                return serve_query_next_image(self, request, Sqn, srcnwkid, srcep)

            log_local_image_available(self, srcnwkid, manufcode, imagetype, currentVersion, image_found)

        elif request is not None and (manufcode, imagetype) == (request["intManufCode"], request["intImageType"]):
            # Nothing to offer to a device picked in the WebUI: it already runs this firmware or
            # a newer one, or the firmware does not support its hardware version.
            drop_unserved_request(self, request, currentVersion, hardware_version if hardware_refused else None)

        elif "checkFirmwareAgainstZigbeeOTARepository" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["checkFirmwareAgainstZigbeeOTARepository"]:
            if (manufcode, imagetype, currentVersion) not in self.zigbee_ota_found_in_index:
                _ota_available = check_ota_availability_from_index( self, manufcode, imagetype, currentVersion )
                if _ota_available:
                    self.zigbee_ota_found_in_index.append( ( manufcode, imagetype, currentVersion)  )
                    notify_ota_firmware_available(self, srcnwkid, manufcode, imagetype, currentVersion, _ota_available )

        # No Image available.
        logging( self, "Debug", ( f"OTA Query Next Image request - No Image Available for now " f"Current device manufcode: 0x{manufcode:04x}, " f"imagetype: 0x{imagetype:04x}, " f"currentVersion: 0x{currentVersion:08x}" ), srcnwkid )
        return zcl_raw_ota_query_next_image_response(self, Sqn, srcnwkid, ZIGATE_EP, srcep, 0x98)


# Local Routines and other helpers
def _handle_ota_timeout(self, request):
    nwkid = request["NwkId"]
    logging(self, "Warning", "Ota timed out on NwkId: %s for block: %s" % (nwkid, request.get("intFileOffset")), nwkid)
    self.adminWidgets.updateNotificationWidget(
        self.Devices, f"Firmware update stopped for Device: {ota_device_name(self, nwkid)} - no block requested for {OTA_BLOCK_TIMEOUT} sec"
    )
    end_ota_request(self, request, "Timeout")


def _retry_notification(self, request):

    request["Retry"] += 1
    logging(self, "Log", "Ota retries notifying device %s" % request["NwkId"], request["NwkId"])

    ota_image_advertize(self, request["NwkId"], request["Ep"], request["ImageVersion"], request["intImageType"], request["intManufCode"])


def log_local_image_available(self, nwkid, manufcode, imagetype, current_version, image):
    """A device asks for an image, a newer local firmware file suits it, but no update is
    planned for it (autoServeOTA off): it gets NO_IMAGE_AVAILABLE. Say so once per device and
    pair of versions, at Status level, so the update can be started from the WebUI."""
    key = (self.ListOfDevices.get(nwkid, {}).get("IEEE", nwkid), current_version, image["originalVersion"])
    if key in self.local_image_available_logged:
        return
    self.local_image_available_logged.add(key)

    entry = retrieve_image(self, imagetype, manufcode, exact=True)
    file_name = entry[1] if entry else f"0x{manufcode:04X}/0x{imagetype:04X}"
    logging(self, "Status", "Firmware %s (version 0x%08X) is available for %s [%s], which runs version 0x%08X: start the update from the WebUI" % (
        file_name, image["originalVersion"], ota_device_name(self, nwkid), nwkid, current_version), nwkid)


def _handle_timeout(self, request):
    # The device did not answer: it gives its slot back and keeps its authorization, a
    # sleepy device asks for its image on its own schedule.
    nwkid = request["NwkId"]
    logging(self, "Log", "Ota: %s did not answer the Image Notify, it gets %s when it asks for it (within %s h)" % (
        nwkid, request["FileName"], OTA_QUEUE_WAIT // 3600), nwkid)
    request.update({"State": OTA_WAITING, "Progress": ""})
    update_firmware_health(self)


def _handle_queue_timeout(self, request):
    nwkid = request["NwkId"]
    logging(self, "Status", "Firmware update of %s dropped: the device did not ask for %s within %s h" % (
        nwkid, request["FileName"], OTA_QUEUE_WAIT // 3600), nwkid)
    self.adminWidgets.updateNotificationWidget(
        self.Devices, f"Firmware update dropped for Device: {ota_device_name(self, nwkid)} - it did not ask for {request['FileName']} within {OTA_QUEUE_WAIT // 3600} hours"
    )
    end_ota_request(self, request, "Dropped")


def ota_device_name(self, nwkid):
    device = self.ListOfDevices.get(nwkid, {})
    # ZDeviceName is "" until the user names the device in the WebUI
    return device.get("ZDeviceName") or device.get("IEEE", nwkid)


def new_ota_request(self, nwkid, ep, brand, file_name, force_update=False, auto_serve=False):
    """A queued OTA request for a device, with the image it is served from.

    A forced update offers the image as version + 0x10100000, for this request only.
    """
    image = self.ListOfImages["Brands"][brand][file_name]
    image_version = image["originalVersion"]
    if force_update:
        # Increase Application release by + 0x10 and Application Build by +0x10
        image_version += 0x10100000
        logging(
            self,
            "Status",
            "----> Forcing update for Image: 0x%04x from Version: 0x%08X to Version: 0x%08X" % (image["ImageType"], image["originalVersion"], image_version), nwkid
        )

    return {
        "IEEE": self.ListOfDevices[nwkid]["IEEE"],
        "NwkId": nwkid,
        "Ep": ep,
        "Brand": brand,
        "FileName": file_name,
        "ForceUpdate": bool(force_update),
        "AutoServe": auto_serve,
        "State": OTA_QUEUED,
        "QueuedTime": time.time(),
        "Retry": 0,
        "NotifiedTimeStamp": 0,
        "intImageType": image["ImageType"],
        "ImageType": f"{image['ImageType']:04x}",
        "intManufCode": image["intManufCode"],
        "ImageVersion": image_version,
        "intSize": image["intSize"],
        "OtaImage": image["OtaImage"],
        "Process": None,
        "Status": None,
        "LastBlockSent": 0,
        "MalformedRequest": False,
        "Progress": "",
    }


def find_ota_request(self, nwkid):
    """The OTA request of this device, or None.

    Requests are kept by IEEE: the short address is refreshed, as the device may have
    rejoined with a new one since it was queued.
    """
    ieee = self.ListOfDevices.get(nwkid, {}).get("IEEE")
    request = self.ota_requests.get(ieee) if ieee else None
    if request is not None:
        request["NwkId"] = nwkid
    return request


def active_ota_requests(self):
    """The requests holding a transfer slot: being notified, or being served."""
    return [request for request in self.ota_requests.values() if request["State"] in OTA_ACTIVE_STATES]


def ota_slot_available(self, nwkid, device_asks=False):
    """Can this device take a transfer slot now?

    OTA_MAX_TRANSFERS slots for any device. When a battery-powered device asks on its own,
    one more, up to OTA_MAX_TRANSFERS_WITH_BATTERY. A ZiGate holds one image at a time.
    """
    active = len(active_ota_requests(self))
    if not _is_controller_in_raw_mode(self):
        return active == 0

    if active < OTA_MAX_TRANSFERS:
        return True

    return device_asks and active < OTA_MAX_TRANSFERS_WITH_BATTERY and not mainPoweredDevice(self, nwkid)


def notify_queued_requests(self):
    """Notify the queued devices, oldest request first, while a transfer slot is free."""
    for request in list(self.ota_requests.values()):
        if request["State"] == OTA_QUEUED and ota_slot_available(self, request["NwkId"]):
            notify_ota_request(self, request)


def notify_ota_request(self, request):
    """Take a transfer slot for a queued request and send its first Image Notify."""
    nwkid = self.IEEE2NWK.get(request["IEEE"], request["NwkId"])
    if nwkid not in self.ListOfDevices:
        logging(self, "Log", "Firmware update of %s dropped: the device is no longer known" % request["IEEE"], nwkid)
        end_ota_request(self, request, "Cancelled")
        return

    request.update({"NwkId": nwkid, "State": OTA_NOTIFYING, "Retry": 0, "NotifiedTimeStamp": time.time(), "Progress": "Notified"})
    ota_load_image_to_zigate(self, request["intImageType"], request["ImageVersion"] if request["ForceUpdate"] else None, manuf_code=request["intManufCode"])
    ota_image_advertize(self, nwkid, request["Ep"], image_version=request["ImageVersion"], image_type=request["intImageType"], manufacturer_code=request["intManufCode"])
    update_firmware_health(self)


def start_transfer(self, request):
    """The device asked for its image: its blocks are served from now on. It holds a
    transfer slot until its Upgrade End, or OTA_BLOCK_TIMEOUT without block request."""
    if request["State"] not in OTA_ACTIVE_STATES:
        ota_load_image_to_zigate(self, request["intImageType"], request["ImageVersion"] if request["ForceUpdate"] else None, manuf_code=request["intManufCode"])

    if request["State"] != OTA_TRANSFER:
        request.update({"State": OTA_TRANSFER, "Process": None, "Progress": "0%"})
        update_firmware_health(self)

    request["LastBlockSent"] = time.time()


def serve_query_next_image(self, request, sqn, nwkid, ep):
    """Answer a Query Next Image Request with the image of the request, if a slot is free.

    A device in its notify window already holds a slot. Otherwise it takes a free one, or
    gets NO_IMAGE_AVAILABLE and stays in the queue, to be notified when its turn comes.
    """
    if request["State"] not in OTA_ACTIVE_STATES and not ota_slot_available(self, nwkid, device_asks=True):
        logging(self, "Log", "OTA Query Next Image request - %s transfers in progress, %s stays in the queue" % (len(active_ota_requests(self)), nwkid), nwkid)
        request["State"] = OTA_QUEUED
        return zcl_raw_ota_query_next_image_response(self, sqn, nwkid, ZIGATE_EP, ep, 0x98)

    start_transfer(self, request)
    logging(self, "Debug", f"OTA Query Next Image request - Image offered fileversion: 0x{request['ImageVersion']:08x} imagesize: {request['intSize']}", nwkid)
    return zcl_raw_ota_query_next_image_response(
        self, sqn, nwkid, ZIGATE_EP, ep,
        0x00, request["intManufCode"], request["intImageType"], request["ImageVersion"], request["intSize"])


def drop_unserved_request(self, request, current_version, refused_hardware_version=None):
    """A device picked in the WebUI asked, and there is nothing to offer it: drop its request."""
    nwkid = request["NwkId"]
    if refused_hardware_version is not None:
        reason = "the firmware does not support its hardware version 0x%04X" % refused_hardware_version
    else:
        reason = "it already runs version 0x%08X" % current_version

    logging(self, "Status", "Firmware update of %s with %s dropped: %s" % (nwkid, request["FileName"], reason), nwkid)
    self.adminWidgets.updateNotificationWidget(self.Devices, f"Firmware update not needed for Device: {ota_device_name(self, nwkid)} - {reason}")
    end_ota_request(self, request, "Not needed")


def ota_request_for_block(self, nwkid):
    """The request a block or page request is served for, or None.

    A device that asks for blocks without a Query Next Image first (it resumes a download)
    takes a transfer slot, if one is free.
    """
    request = find_ota_request(self, nwkid)
    if request is None:
        if not self.pluginconf.pluginConf.get("autoServeOTA", False):
            # We need to prevent looping on serving if it is not expected!
            logging(self, "Warning", f"ota_request_for_block: There is no upgrade plan for that device, drop request from {nwkid}", nwkid)
        return None

    if request["State"] not in OTA_ACTIVE_STATES and not ota_slot_available(self, nwkid, device_asks=True):
        logging(self, "Log", f"ota_request_for_block: {len(active_ota_requests(self))} transfers in progress, {nwkid} stays in the queue", nwkid)
        return None

    start_transfer(self, request)
    return request


def end_ota_request(self, request, final_status=None):
    """Remove a request: its slot, if it had one, goes to the next queued request on the
    next heartbeat."""
    self.ota_requests.pop(request["IEEE"], None)
    if final_status:
        request["Progress"] = final_status
    update_firmware_health(self, ended=request)


def ota_load_image_to_zigate(self, image_type, force_version=None, manuf_code=None):
    # Load the image headers into Zigate

    entry = retrieve_image(self, image_type, manuf_code)
    if entry is None:
        _log_debug_unknown_image_type(self, image_type)
        return

    brand, image_entry = entry

    image_entry = self.ListOfImages["Brands"][brand][image_entry]
    decoded_header = image_entry["Decoded Header"]

    datas = _format_image_data(self, decoded_header, force_version)

    logging(self, "Debug", f"ota_load_image_to_zigate: - len:{len(datas)} datas: {datas}")

    if not _is_controller_in_raw_mode(self):
        self.ControllerLink.sendData("0500", datas, ackIsDisabled=True)

    _update_image_loaded_info(self, decoded_header, force_version)


def _log_debug_unknown_image_type(self, image_type):
    logging(self, "Debug", f"ota_load_image_to_zigate - Unknown Image {image_type} in {list(self.ListOfImages['ImageType'].keys())}")


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


def build_ota_data_block(self, request, block_request, max_data_size):
    """
    Build a single OTA block segment from the OTA image of the request.

    block_request fields must contain:
        - "Sequence": hex string
        - "Offset": hex string

    Returns:
        (sequence:int, offset:int, length:int, raw_ota_data:bytes)
    """
    ota_image = request["OtaImage"]

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


def update_transfer_progress(self, request, offset, length):
    now = time.time()
    request["LastBlockSent"] = now
    request["TimeStamps"] = now
    request["Status"] = "Transfer Progress"
    request["Received"] = offset
    request["Sent"] = offset + length


def scaled_block_delay(self, block_delay):
    """The delay (seconds) between two blocks of a device, multiplied by the number of
    transfers being served, up to OTA_MAX_SCALED_BLOCK_DELAY (never below block_delay)."""
    transfers = sum(1 for request in self.ota_requests.values() if request["State"] == OTA_TRANSFER)
    if transfers <= 1:
        return block_delay

    return max(block_delay, min(block_delay * transfers, OTA_MAX_SCALED_BLOCK_DELAY))


def ota_send_block(self, request, dest_addr, dest_ep, image_type, msg_image_version, block_request, disable_ack=False, block_delay=DEFAULT_OTA_PROFILE["min_delay"]):

    in_update = request
    if retrieve_image(self, image_type, in_update.get("intManufCode")) is None:
        logging(self, "Warning", f"ota_send_block - unknown image_type {image_type}", dest_addr)
        return False

    expected_image_type = int(in_update["ImageType"], 16)
    if image_type != expected_image_type:
        logging(
            self, "Warning",
            f"ota_send_block - inconsistent ImageType Received: {image_type} "
            f"Expecting: {in_update['ImageType']}", dest_addr
        )
        return False

    # Build block, and Minimum Block Request Delay
    manufacturer_code = in_update['intManufCode']
    ota_profile = VENDOR_PROFILES.get( manufacturer_code, DEFAULT_OTA_PROFILE )
    max_data_size = min(block_request["MaxDataSize"], ota_profile["max_data"])
    block_delay = scaled_block_delay(self, max(block_delay, ota_profile["min_delay"]))

    sequence, offset, length, raw_ota_data = build_ota_data_block( self, request, block_request, max_data_size )

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
    update_transfer_progress(self, request, offset, length)

    logging( self, "Debug", f"ota_send_block - Block sent to {dest_addr}/{dest_ep} " f"Received yet: {offset} Sent now: {offset} Size: {max_data_size} Delay: {block_delay}", dest_addr )

    # Determine OTA block status
    if length == 0 or data is None:
        logging( self, "Warning", f"OTA {dest_addr}/{dest_ep} short of data, device request offset: {offset} expected size: {max_data_size} got only {length}", dest_addr )
        
        if request["MalformedRequest"]:
            # 2nd time in a row we get a malformed request, aborting
            status = 0x95  # ABORT
            # Let's rebuild the message with the correct status, so that we can trace it in the logs and have a clear feedback to the device about what is going on
            data = build_ota_message(
                self, dest_addr, dest_ep, sequence, 0x95, offset,
                image_version_hex, image_type_hex, manufacturer_code_hex,
                length, raw_ota_data
            )

        else:
            # get a request for data we cannot provide
            status = 0x80  # MALFORMED_COMMAND
            request["MalformedRequest"] = True
            
            # Let's rebuild the message with the correct status, so that we can trace it in the logs and have a clear feedback to the device about what is going on
            data = build_ota_message(
                self, dest_addr, dest_ep, sequence, 0x80, offset,
                image_version_hex, image_type_hex, manufacturer_code_hex,
                length, raw_ota_data
            )

    else:
        status = 0x00  # Successblock_request_delay
        request["MalformedRequest"] = False

    # --- Raw mode (controller internal testing) ---
    raw_mode = self.pluginconf.pluginConf.get("ControllerInRawMode", False)
    if raw_mode and status != 0x00:
        if status == 0x95:
            # ABORT: an Image Block Response carrying the status only (ZCL rev 8 11.13.8.2.1)
            return zcl_raw_ota_image_block_response_abort(self, dest_addr, ZIGATE_EP, dest_ep, "95", sqn=f"{sequence:02x}")
        # Invalid file offset: Default Response MALFORMED_COMMAND (ZCL rev 8 11.13.6.5.1 / 11.13.7.5.1).
        # Image Page Requests are the only callers that disable the APS ack.
        request_command = "04" if disable_ack else "03"
        return zcl_raw_default_response(self, dest_addr, ZIGATE_EP, dest_ep, OTA_CLUSTER_ID, request_command, f"{sequence:02x}", command_status="80")

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
    #
    # The notify is unicast: ZCL rev 8 11.13.3.3 recommends payload type 0 with a jitter of 100
    # for a unicast notify, so the client always answers with a Query Next Image Request.
    # Clients that apply the broadcast matching rules to a unicast notify with payload type 3
    # discard it. The image offered (version included) goes in the Query Next Image Response.

    IMG_NTFY_PAYLOAD_TYPE = 0

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
    
    logging(self, "Debug", f"ota_image_advertize - Type: 0x{image_type:04x}, Version: 0x{image_version:08X} => datas: {datas}", dest_addr)

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
        logging( self, "Log", f"ota_management - zcl_raw_ota_upgrade_end_response( {sqn}, {dest_addr}, {ZIGATE_EP}, {dest_ep}, {manufacturer_code}, {image_type}, {file_version}, {current_time}, {upgrade_time})", dest_addr )

    else:
        datas = "%02x" % ADDRESS_MODE["short"] + dest_addr + ZIGATE_EP + dest_ep
        datas += "%08x" % upgrade_time
        datas += "%08x" % 0x00
        datas += "%08x" % file_version
        datas += "%04x" % image_type
        datas += "%04x" % manufacturer_code

        self.ControllerLink.sendData("0504", datas, ackIsDisabled=False, NwkId=dest_addr)

    logging( self, "Log", "ota_management - sending Upgrade End Response, for %s Version: 0x%08X Type: 0x%04x, Manuf: 0x%04X" % (dest_addr, file_version, image_type, manufacturer_code), dest_addr )

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
        f"ota_management - Reduce Block request rate to {BlockRequestDelayMs} ms", MsgSrcAddr
    )

    self.ControllerLink.sendData(
        "0506",
        datas,
        ackIsDisabled=False,
        NwkId=MsgSrcAddr
    )


def cleanup_after_completed_upgrade(self, request, Status):
    """
    Cleanup and housekeeping after an OTA upgrade completes.

    Args:
        request (dict): The OTA request of the device.
        Status (str): Upgrade status code ("00" indicates success).
    """
    NwkId = request["NwkId"]
    logging(self, "Debug", f"cleanup_after_completed_upgrade - Cleanup and housekeeping {NwkId} {Status}", NwkId)

    # Whatever the status, the request ends and its slot goes to the next queued device.
    # A device that failed asks again on its own: with autoServeOTA, it is queued again.
    end_ota_request(self, request)

    logging(self, "Debug", f"cleanup_after_completed_upgrade - After cleanup {len(self.ota_requests)} OTA request(s) left", NwkId)

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


def firmware_update_result(nwkid, status, reason=None):
    """One entry of the REST answer to a firmware update request."""
    return {"NwkId": nwkid, "Status": status, "Reason": reason}


def firmware_update_rejection(self, brand, file_name, target_nwkid, target_ep, force_update=False):
    """Why this firmware update cannot start (the reason is logged), or None if it can."""

    if brand not in self.ListOfImages["Brands"]:
        logging(self, "Warning", "restapi_firmware_update Brands %s unknown" % brand, target_nwkid)
        return "Unknown brand"

    if file_name not in self.ListOfImages["Brands"][brand]:
        logging(self, "Warning", "restapi_firmware_update FileName %s unknown in this Brand %s" % (file_name, brand), target_nwkid)
        return "Unknown firmware file"

    if target_nwkid not in self.ListOfDevices:
        logging(self, "Warning", "restapi_firmware_update NwkId: %s unknown" % target_nwkid, target_nwkid)
        return "Unknown device"

    if target_ep not in self.ListOfDevices[target_nwkid]["Ep"]:
        logging(self, "Warning", "restapi_firmware_update NwkId: %s Ep: %s unknown" % (target_nwkid, target_ep), target_nwkid)
        return "Unknown endpoint"

    ieee = self.ListOfDevices[target_nwkid].get("IEEE")
    if ieee is None:
        logging(self, "Warning", "restapi_firmware_update NwkId: %s has no IEEE" % target_nwkid, target_nwkid)
        return "Unknown device"

    if ieee in self.ota_requests:
        logging(self, "Warning", "restapi_firmware_update NwkId: %s already has a firmware update %s for %s" % (
            target_nwkid, self.ota_requests[ieee]["State"], self.ota_requests[ieee]["FileName"]), target_nwkid)
        return "A firmware update is already queued or in progress for this device"

    current_version = known_version_of_image(self, target_nwkid, self.ListOfImages["Brands"][brand][file_name])
    if not force_update and current_version is not None and current_version >= self.ListOfImages["Brands"][brand][file_name]["originalVersion"]:
        logging(self, "Status", "Firmware update of %s with %s not queued: it already runs version 0x%08X, use Force Update to install it" % (
            target_nwkid, file_name, current_version), target_nwkid)
        return "The device already runs this firmware version or a newer one"

    return None


def known_version_of_image(self, nwkid, image):
    """The version the device reported in its last Query Next Image Request, if that was for this image's manufacturer and type."""
    ota_client = self.ListOfDevices[nwkid].get("OTAClient", {})
    if (ota_client.get("ManufacturerCode"), ota_client.get("ImageType")) != (image["intManufCode"], image["ImageType"]):
        return None
    return ota_client.get("CurrentImageVersion")


def firmware_update(self, brand, file_name, target_nwkid, target_ep, force_update=False):
    """Queue a firmware update for a device, notified at once if a transfer slot is free.

    Returns its firmware_update_result(): "Queued", or "Rejected" with the reason.
    """
    reason = firmware_update_rejection(self, brand, file_name, target_nwkid, target_ep, force_update)
    if reason:
        return firmware_update_result(target_nwkid, "Rejected", reason)

    request = new_ota_request(self, target_nwkid, target_ep, brand, file_name, force_update)
    self.ota_requests[request["IEEE"]] = request
    logging(self, "Status", "Firmware update queued for %s with %s (%s request(s) queued or in progress)" % (
        target_nwkid, file_name, len(self.ota_requests)), target_nwkid)

    notify_queued_requests(self)
    update_firmware_health(self)
    return firmware_update_result(target_nwkid, "Queued")


def logging(self, logType, message, nwkid=None, context=None):  # OK 13/10
    self.log.logging("OTA", logType, message, nwkid, context)


def is_image_for_query_next_image_request( self, nwkid, manuf_code, image_type, file_version, authorized_device_downgrade):

    logging(self, "Debug", "is_image_for_query_next_image_request - Manuf: 0x%04X Type: 0x%04X Version: 0x%08X Downgrade: %s" % (
        manuf_code, image_type, file_version, authorized_device_downgrade), nwkid)

    for brand_name in self.ListOfImages["Brands"]:
        logging(self, "Debug", "is_image_for_query_next_image_request - checking %s" %brand_name, nwkid)
        for file_name in self.ListOfImages["Brands"][brand_name]:
            logging(self, "Debug", "    - filename %s Manuf: 0x%04X Image: 0x%04X Version: 0x%08X" %(
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

            logging(self, "Debug", "is_image_for_query_next_image_request - potential image type found:%s with version 0x%08X..." % (
                brand_name, self.ListOfImages["Brands"][brand_name][file_name]["originalVersion"]), nwkid)

            # Compliance with Image Type
            if file_version < self.ListOfImages["Brands"][brand_name][file_name]["originalVersion"]:
                logging(self, "Debug", "is_image_for_query_next_image_request - We have newest firmware available for this device", nwkid)
                return self.ListOfImages["Brands"][brand_name][file_name]

    return None


def is_hardware_version_compatible(self, nwkid, image, hardware_version):
    """ZCL rev 8 11.13.4.4: a hardware version sent by the client SHALL be checked
    against the minimum / maximum hardware version of the image header.

    A client that does not send its hardware version is not refused.
    """
    if hardware_version is None:
        return True

    header = image["Decoded Header"]
    min_hw_version = header.get("min_hw_version")
    max_hw_version = header.get("max_hw_version")

    if (min_hw_version is not None and hardware_version < min_hw_version) or (max_hw_version is not None and hardware_version > max_hw_version):
        logging(self, "Log", "OTA image for 0x%04X not offered to %s: hardware version 0x%04X outside the image range 0x%04X - 0x%04X" % (
            header["image_type"], nwkid, hardware_version, min_hw_version or 0, max_hw_version or 0xFFFF), nwkid)
        return False

    return True


def retrieve_image_in_a_brand(self, image_type, brand, manuf_code=None):
    brand_images = self.ListOfImages.get("Brands", {}).get(brand, {})

    return next(
        (image for image, info in brand_images.items() if info.get("ImageType") == image_type and manuf_code in (None, info.get("intManufCode"))),
        None,
    )


def retrieve_image(self, image_type, manuf_code=None, exact=False):
    """(brand, file name) of the loaded image for this image type, or None.

    Image types are manufacturer specific (ZCL rev 8 11.4.2.6): the image whose
    manufacturer code matches manuf_code wins. Without such a match, the only image of
    that type is still returned (as before, e.g. the Legrand 0x00C8 requests patched in
    initialize_block_request), unless several manufacturers use the type or exact is set.
    """
    candidates = [
        (brand, image, info)
        for brand, images in self.ListOfImages.get("Brands", {}).items()
        for image, info in images.items()
        if info.get("ImageType") == image_type
    ]
    if manuf_code is not None:
        matching = [candidate for candidate in candidates if candidate[2].get("intManufCode") == manuf_code]
        if matching or exact or len(candidates) > 1:
            candidates = matching

    return candidates[0][:2] if candidates else None


def ota_scan_folder(self):  # OK 13/10
    # Scanning the Firmware folder
    # At that stage ALL firmware available from each ENABLED folders
    # have been read , decoded and key informations stored in ListOfImages
    # ListOfImages have 2 entries either from brand or from Image Type

    self.ListOfImages["Brands"] = {}
    self.ListOfImages["ImageType"] = {}   # (manufacturer code, image type) -> brand
    for brand in OTA_CODES:
        if not OTA_CODES[brand]["Enabled"]:
            continue
        
        self.ListOfImages["Brands"][brand] = {}
        for subfolder in ota_brand_folders(OTA_CODES[brand]):
            ota_dir = self.pluginconf.pluginConf["pluginOTAFirmware"] + "/" + subfolder
            # Check the folder exist
            if not exists(ota_dir):
                continue

            ota_image_files = [f for f in listdir(ota_dir) if isfile(join(ota_dir, f))]

            logging(self, "Debug", "   screening %s" %ota_dir)
            for ota_image_file in ota_image_files:
                if ota_image_file in ("README.md", "README.txt", ".PRECIOUS", ".precious"):
                    continue
                logging(self, "Debug", "       found %s" %ota_image_file)
                header_return = ota_extract_image_headers(self, subfolder, ota_image_file)

                if header_return is None:
                    continue
                image_type, headers, ota_image = header_return

                # An image is identified by manufacturer code AND image type (ZCL rev 8 11.13.6.4)
                image_key = (headers["manufacturer_code"], image_type)

                # Check if this Image is the latest version.
                if image_key in self.ListOfImages["ImageType"] and not check_image_valid_version(
                    self, brand, image_type, ota_image_file, headers
                ):
                    # Most likely we have a more higher version already loaded!
                    continue

                # Check if the same manufacturer code and image type are not used by another brand
                if image_key in self.ListOfImages["ImageType"] and self.ListOfImages["ImageType"][image_key] != brand:
                    logging(self, "Warning", "ota_scan_folder Firmware %s not loaded, another firmware with the same ImageType and another brand is already loaded" %ota_image_file)
                    continue

                self.ListOfImages["ImageType"][image_key] = brand
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

    existing_image = retrieve_image(self, image_type, headers["manufacturer_code"], exact=True)
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
    try:
        headers = unpack_headers(self, ota_image)

    except (ValueError, IndexError, struct.error) as err:
        # A file cut short after the OTA magic: skip it, keep scanning the others
        _context = {"Error code": "OTA0004", "Folder": str(subfolder), "File": str(image), "Size": len(ota_image), "Exception": str(err)}
        logging(self, "Error", f"ota_extract_image_headers - {subfolder}/{image} has a truncated or malformed OTA header ({err}), skipped", None, _context)
        return None

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
        _context = {"Error code": "OTA0001", "File": str(filename), "Exception": str(err)}
        logging(self, "Error", f"_open_image_file - error when opening {filename} - {err}", None, _context)
        return None

    if len(ota_image) < 69:
        _context = {"Error code": "OTA0002", "File": str(filename), "Size": len(ota_image)}
        logging(self, "Error", f"_open_image_file - invalid file size read {filename} - {len(ota_image)}", None, _context)
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

    _context = {"Error code": "OTA0003", "Size": len(ota_image)}
    logging(self, "Error", "Zigbee OTA magic not found in firmware image", None, _context)
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
    They follow the mandatory section in this order (ZCL rev 8, table 11-3):
    Bit 0 (0x01): Security Credential Version (uint8)
    Bit 1 (0x02): Upgrade File Destination (IEEE address, uint64)
    Bit 2 (0x04): Hardware Versions:
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
        upgrade_file_destination: Optional[int]
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


    # --- 3. Optional fields, in the order of ZCL rev 8 table 11-3 ---
    extra_offset = offset + BASE_HEADER_SIZE

    # Bit 0 → Security Credential Version
    sec_cred_version = None
    if field_ctrl & 0x01:
        sec_cred_version = ota_image[extra_offset]
        extra_offset += 1

    # Bit 1 → Upgrade File Destination (device specific file)
    upgrade_file_destination = None
    if field_ctrl & 0x02:
        upgrade_file_destination = struct.unpack_from("<Q", ota_image, extra_offset)[0]
        extra_offset += 8

    # Bit 2 → Minimum / Maximum Hardware Version
    min_hw_version, max_hw_version = None, None
    if field_ctrl & 0x04:
        min_hw_version, max_hw_version = struct.unpack_from("<HH", ota_image, extra_offset)
        extra_offset += 4

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
        "upgrade_file_destination": upgrade_file_destination,
        "vendor_data": vendor_data,
        "payload_offset": offset + header_length,
    }


def prepare_and_send_block(
    self,
    request,
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
        request: OTA request of the device, holding the image it is served from
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
    # Initialize block request and patch ImageType if needed
    block_request = initialize_block_request(
        self, request, MsgSrcAddr, MsgEP, MsgFileOffset, intMsgImageVersion,
        intMsgImageType, intMsgManufCode, MsgBlockRequestDelay,
        MsgMaxDataSize, intMsgFieldControl, MsgSQN
    )
    intMsgImageType = block_request["ImageType"]

    if retrieve_image(self, intMsgImageType, block_request["ManufCode"]) is None:
        _context = {"Error code": "OTA0201", "Request": "Image Block", "ImageType": f"0x{intMsgImageType:04X}", "ManufCode": f"0x{intMsgManufCode:04X}", "FileVersion": f"0x{intMsgImageVersion:08X}", "Offset": int(MsgFileOffset, 16)}
        logging(self, "Error", f"prepare_and_send_block {MsgSrcAddr}/{MsgEP} - 0x{intMsgImageType:04X} image not found", MsgSrcAddr, _context)
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
    if request.get("Process") is None:
        start_upgrade_infos(self, request, MsgSrcAddr, MsgFileOffset, MsgMaxDataSize)
        request["Process"] = "Started"
    else:
        request["Process"] = "OnGoing"

    request.update({
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

    ota_send_block(self, request, MsgSrcAddr, MsgEP, intMsgImageType, intMsgImageVersion, block_request, disable_ack=disableACK, block_delay=block_request_delay)
    display_percentage_progress(self, request, MsgSrcAddr, MsgEP, MsgFileOffset)


def initialize_block_request(self, request, MsgSrcAddr, MsgEP, MsgFileOffset, intMsgImageVersion, intMsgImageType, intMsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, intMsgFieldControl, MsgSQN):
    # Patching in order to make Legrand update with Image Page Request working
    if intMsgManufCode == 0x00C8:
        # Request a Page, and Note a Block
        # For the time being, we are forcing a response with a Block
        intMsgImageType = request["intImageType"]
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


def notify_upgrade_end(
    self,
    request,
    Status,
    MsgSrcAddr,
    MsgEP,
    image_type,
    intMsgManufCode,
    intMsgImageVersion,
    ):  # OK 26/10

    _transferTime_hh, _transferTime_mm, _transferTime_ss = convert_time(int(time.time() - request.get("StartTime", time.time())))
    _name = ota_device_name(self, MsgSrcAddr)
    _textmsg = ""

    if Status == "OK":
        _textmsg = "Device: %s has been updated with firmware %s in %s hour %s min %s sec" % (
            _name,
            intMsgImageVersion,
            _transferTime_hh,
            _transferTime_mm,
            _transferTime_ss,
        )
        logging(self, "Status", _textmsg, MsgSrcAddr)
        request["Progress"] = "Success"
        
        # The firmware announced by the online index is now installed: forget it. OTAUpdate is
        # keyed by the image type as notify_ota_firmware_available() stores it (an int), which
        # becomes its decimal string once the device list is reloaded from JSON.
        ota_update = self.ListOfDevices.get(MsgSrcAddr, {}).get("OTAUpdate", {})
        for key in (image_type, str(image_type), "%x" % image_type, "%04x" % image_type):
            ota_update.pop(key, None)

    elif Status == "Aborted":
        _textmsg = "Firmware update aborted error code %s for Device %s in %s hour %s min %s sec" % (
            Status,
            _name,
            _transferTime_hh,
            _transferTime_mm,
            _transferTime_ss,
        )

        request["Progress"] = "Aborted"

    elif Status == "Failed":
        _textmsg = "Firmware update aborted error code %s for Device %s in %s hour %s min %s sec" % (
            Status,
            _name,
            _transferTime_hh,
            _transferTime_mm,
            _transferTime_ss,
        )
        request["Progress"] = "Failed"

    elif Status == "More":
        _textmsg = "Device: %s has been updated to latest firmware in %s hour %s min %s sec, but additional Image needed" % (
            _name,
            _transferTime_hh,
            _transferTime_mm,
            _transferTime_ss,
        )
        request["Progress"] = "More"

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
    file_version = headers["image_version"]
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


def display_percentage_progress(self, request, MsgSrcAddr, MsgEP, MsgFileOffset):
    """
    Display firmware transfer progress and update device health.
    """
    # Ensure file offset is an integer
    offset = int(MsgFileOffset, 16) if isinstance(MsgFileOffset, str) else MsgFileOffset
    total_size = request.get("intSize") or 1  # Avoid division by zero

    # Log progress once per 5% step: the last 5% mark the offset has reached. Several blocks of
    # one page can land on the same mark, and a block can step over the mark itself.
    progress_step = int(offset * 100 // total_size) // 5 * 5
    if request["Progress"] == f"{progress_step}%":
        return

    logging(self, "Status", f"Firmware transfer for {MsgSrcAddr}/{MsgEP} - Progress: {progress_step:4.1f}%", MsgSrcAddr)
    request["Progress"] = f"{progress_step}%"
    update_firmware_health(self)


def update_firmware_health(self, ended=None):
    """
    Firmware updates in PluginHealth, for the WebUI.

    "Device" / "Progress": the requests holding a transfer slot, joined (", "). When the
    last one ends, its outcome stays there. "Requests": every request, "Active" when it
    holds a transfer slot, "Not Active" when it waits in the queue.
    """
    firmware_update_health = self.PluginHealth.setdefault("Firmware Update", {"Progress": "", "Device": ""})

    active = active_ota_requests(self)
    if active:
        firmware_update_health["Device"] = ", ".join(request["NwkId"] for request in active)
        firmware_update_health["Progress"] = ", ".join(request["Progress"] for request in active)
    elif ended is not None:
        firmware_update_health["Device"] = ended["NwkId"]
        firmware_update_health["Progress"] = ended["Progress"]

    firmware_update_health["Requests"] = [
        {
            "NwkId": request["NwkId"],
            "IEEE": request["IEEE"],
            "Name": ota_device_name(self, request["NwkId"]),
            "FileName": request["FileName"],
            "State": request["State"],
            "Status": "Active" if request["State"] in OTA_ACTIVE_STATES else "Not Active",
            "Progress": request["Progress"],
            "QueuedTime": int(request["QueuedTime"]),
        }
        for request in self.ota_requests.values()
    ]


def start_upgrade_infos(self, request, MsgSrcAddr, MsgFileOffset, MsgMaxDataSize):
    """Start the firmware upgrade process for a device: first block requested."""

    request.update({
        "NwkId": MsgSrcAddr,
        "intFileOffset": int(MsgFileOffset, 16),
        "LastBlockSent": 0,
        "StartTime": time.time(),
        "Progress": "0%",
    })
    update_firmware_health(self)

    _name = ota_device_name(self, MsgSrcAddr)

    # Estimate upload time. We expect to send 5 blocks in 1 second
    ota_profile = VENDOR_PROFILES.get( request["intManufCode"], DEFAULT_OTA_PROFILE )
    block_size = min(MsgMaxDataSize, ota_profile["max_data"])

    estimated_blocks = math.ceil(request["intSize"] / block_size)
    estimated_time_sec = estimated_blocks / 5

    # Convert estimated time into hours, minutes, and seconds
    _durhh, _durmm, _durss = convert_time(estimated_time_sec)

    # Generate notification text
    _textmsg = (f"Firmware update started for Device: {_name} with {request['FileName']} - "
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

    newer_images = [
        _image for _image in self.zigbee_ota_index
        if _image["manufacturerCode"] == manufcode and _image["imageType"] == imagetype and _image["fileVersion"] > fileversion
    ]
    # Report the newest one: the index can list several versions of an image
    return max(newer_images, key=lambda _image: _image["fileVersion"]) if newer_images else {}


def notify_ota_firmware_available(self, srcnwkid, manufcode, imagetype, fileversion, _ota_available ):

    # One entry owns each manufacturer code, so this lookup has a single answer;
    # a generic entry reports its canonical folder.
    folder = next((ota_brand_folders(OTA_CODES[supported_manufacturer])[0] for supported_manufacturer in OTA_CODES if OTA_CODES[supported_manufacturer]["ManufCode"] == manufcode), None)

    logging(self, "Status", "Z4D detects a potential new firmware for device %s [%s]" % ( get_device_nickname( self, NwkId=srcnwkid, ), srcnwkid ), srcnwkid)
    logging(self, "Status", "   current version: %s" % fileversion, srcnwkid)
    logging(self, "Status", "     firmware type: %s" % imagetype, srcnwkid)
    logging(self, "Status", "    newest version: %s" % _ota_available["fileVersion"], srcnwkid)
    logging(self, "Status", "     firmware type: %s" % _ota_available["imageType"], srcnwkid)
    logging(self, "Status", "   URL to download: %s" % _ota_available["url"], srcnwkid)

    if srcnwkid in self.ListOfDevices:
        ota = self.ListOfDevices[srcnwkid].setdefault("OTAUpdate", {})
        ota[imagetype] = {
            "currentversion": str(fileversion),
            "newestversion": str(_ota_available["fileVersion"]),
            "url": _ota_available["url"],
        }

    if folder:
        logging(self, "Status", "   Folder to store: %s" % folder, srcnwkid)
    else:
        logging(self, "Status", "   to get this Manufacturer supported: %s" % manufcode, srcnwkid)
        logging(self, "Status", "   provide those informations: %s" % _ota_available, srcnwkid)
        logging(self, "Status", "   open an Issue on GitHub here: https://github.com/zigbeefordomoticz/Domoticz-Zigbee/issues/new?assignees=&labels=&template=feature_request.md&title=", srcnwkid)


def _load_json_from_url(self, url, retries=3, timeout=5):
    last_reason = "unknown error"
    backoff = 1.0

    req = urllib.request.Request(url, headers={"User-Agent": "Z4D"})

    for attempt in range(retries):
        retry_after = None
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.load(response)

        except urllib.error.HTTPError as e:
            last_reason = f"HTTP {e.code}: {e.reason}"
            if e.code not in (429, 500, 502, 503, 504):
                # 400/403/404/... won't fix themselves — fail fast
                break
            # transient server-side — worth retrying
            retry_after = e.headers.get("Retry-After")

        except urllib.error.URLError as e:
            # covers DNS failures, connection refused, and URLError-wrapped timeouts
            last_reason = f"URLError: {e.reason}"

        except (socket.timeout, TimeoutError) as e:
            last_reason = f"timeout: {e}"

        except (json.JSONDecodeError, ValueError) as e:
            # malformed or truncated body
            last_reason = f"invalid JSON: {e}"

        except (http.client.IncompleteRead, ConnectionError, OSError) as e:
            last_reason = f"connection error: {e}"

        # don't sleep after the final attempt
        if attempt < retries - 1:
            delay = backoff
            if retry_after:
                # Retry-After may be an HTTP-date: then keep the backoff
                with contextlib.suppress(ValueError):
                    delay = min(float(retry_after), 30.0)
            time.sleep(delay + random.uniform(0, 0.5))  # nosec B311 - jitter only, not security-sensitive
            backoff *= 2

    _context = {"Error code": "OTA0501", "Url": url, "Reason": last_reason}
    logging(self, "Error",
            f"loading_zigbee_ota_index: Unable to access {url} Reason: {last_reason}", None, _context)
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
    # Use the plugin config if set, else a secure temp directory
    log_dir = self.pluginconf.pluginConf.get("pluginLogs")
    if log_dir is None:
        log_dir = tempfile.mkdtemp(prefix="ota_logs_")  # creates a unique temp dir

    full_path = os.path.join(log_dir, filename)

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
        _context = {"Error code": "OTA0901", "File": full_path, "Exception": str(e)}
        logging(self, "Error", f"OTA trace logging {full_path} failed: {e}", dest_addr, _context)
