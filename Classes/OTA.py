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


# """
#     References:
#         - https://www.nxp.com/docs/en/user-guide/JN-UG-3115.pdf ( section 40 - OTA Upgrade Cluster
#         - https://github.com/fairecasoimeme/ZiGate/issues?utf8=%E2%9C%93&q=OTA
#
#     Server      Zigate      Client
#
#     0x0500 ----->
#     0x0505 ----------------->
#     0x8501 <------------------
#     0x0502 ------------------>
#
#     0x8503 <------------------
#
#     'Upgraded Device':
#         - Notified
#         - Block Requested
#         - Transfer Progress
#         - Transfer Completed
#         - Transfer Aborted
#         - Timeout
#
# """


import struct
import time
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
MAX_FRAME_DATA = 64

OTA_CODES = {
    
    "Danfoss": {"Folder": "DANFOSS", "ManufCode": 0x1246, "ManufName": "Danfoss", "Enabled": True},
    "Develco": {"Folder": "DEVELCO", "ManufCode": 0x1015, "ManufName": "Develco", "Enabled": True},
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
}


class OTAManagement(object):
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
        AuthorizedForDowngrade: The dictionary containing information about devices authorized for downgrade.
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


    def __init__(
        self,
        zigbee_communitation,
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
        internet_available
        ):
        
        # Pointers to external objects
        self.zigbee_communication = zigbee_communitation
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
        
        self.AuthorizedForDowngrade = {}
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


    def ota_image_block_request(self, MsgData):  # OK 13/10
        # ota_image_block_request(self, Devices, MsgData, MsgLQI):  # OTA image block request
        # BLOCK_REQUEST  0x8501  ZiGate will receive this command when device asks OTA firmware

        if len(MsgData) not in ( 60 , 62):
            logging(self, "Debug", "ota_image_block_request - Incorrect lenght (%s) %s" % (len(MsgData), MsgData))
            return
        MsgSQN = MsgData[:2]
        MsgEP = MsgData[2:4]
        MsgClusterId = MsgData[4:8]
        MsgaddrMode = MsgData[8:10]
        MsgSrcAddr = MsgData[10:14]
        MsgIEEE = MsgData[14:30]
        MsgFileOffset = MsgData[30:38]
        intMsgImageVersion = int(MsgData[38:46], 16)
        intMsgImageType = int(MsgData[46:50], 16)
        intMsgManufCode = int(MsgData[50:54], 16)
        MsgBlockRequestDelay = int(MsgData[54:58], 16)
        MsgMaxDataSize = int(MsgData[58:60], 16)
        intMsgFieldControl = int(MsgData[60:62], 16)

        logging( self, "Debug", "ota_image_block_request - Request Firmware %s/%s Offset: %s Version: 0x%08x Type: 0x%04X Manuf: 0x%04X Delay: %s MaxSize: %s Control: 0x%02X" % (
            MsgSrcAddr, MsgEP, int(MsgFileOffset, 16), intMsgImageVersion, intMsgImageType, intMsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, intMsgFieldControl, ),)

        if self.ListInUpdate["NwkId"] is None:
            logging(self, "Debug", "ota_image_block_request - Async request from device: %s." % (MsgSrcAddr))
            if not ota_aync_request( self, MsgSrcAddr, MsgEP, MsgIEEE, MsgFileOffset, intMsgImageVersion, intMsgImageType, intMsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, intMsgFieldControl, ):
                logging(
                    self,
                    "Debug",
                    "ota_image_block_request %s/%s - Async request failed %s " % (MsgSrcAddr, MsgEP, self.ListInUpdate),
                )
                return

        prepare_and_send_block(self, MsgSrcAddr, MsgEP, MsgFileOffset, intMsgImageVersion, intMsgImageType, intMsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, intMsgFieldControl, MsgSQN, )
            

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
        ResponseSpacing = MsgData[44:48]
        FieldControl = MsgData[48:50]
        intMsgFieldControl = int(FieldControl,16)
        if len(MsgData) == 64:
            RequestNodeAddress = MsgData[48:64]

        logging( self, "Debug", "ota_image_page_request - Request Firmware %s/%s Offset: %s Version: 0x%08x Type: 0x%04X Manuf: 0x%04X MaxSize: %s PageSize: %s ResponseSpacing: %s Control: 0x%02X" % (
            MsgSrcAddr, MsgEP, int(MsgFileOffset, 16), intMsgImageVersion, intMsgImageType, intMsgManufCode, MsgMaxDataSize, PageSize , int(ResponseSpacing,16), intMsgFieldControl, ),)

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
                ResponseSpacing, 
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
        logging(self, "Debug", "OTA upgrade completed - %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s" % (
            MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus))

        if self.ListInUpdate["NwkId"] is None:
            logging(self, "Log", "ota_upgrade_end_request - Receive Firmware Completed from %s most likely a duplicated packet as there is nothing in Progress. " % MsgSrcAddr)

            return
        if self.ListInUpdate["NwkId"] and MsgSrcAddr != self.ListInUpdate["NwkId"]:
            logging(self, "Error", "ota_upgrade_end_request - OTA upgrade completed - %s not in Upgraded devices" % MsgSrcAddr)

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
        process = self.ListInUpdate["Process"]
        image_type = self.ImageLoaded["image_type"]
        loaded_time_stamp = self.ImageLoaded["LoadedTimeStamp"]
        notified_time_stamp = self.ImageLoaded["NotifiedTimeStamp"]
        retry = self.ListInUpdate["Retry"]
        authorized_for_update = self.ListInUpdate["AuthorizedForUpdate"]

        if nwk_id is None:
            logging(self, "Debug", "ota_heartbeat - nothing to do")
            return

        logging(
            self,
            "Debug",
            "ota_heartbeat - NwkId: %s Process: %s Loaded: 0x%s Time: %s Notified: %s Retry: %s Authorized: %s"
            % (nwk_id, process, image_type, loaded_time_stamp, notified_time_stamp, retry, authorized_for_update),
        )

        if nwk_id and self.ListInUpdate["Status"] == "Transfer Progress" and self.ListInUpdate["LastBlockSent"] != 0 and (
                time.time() > self.ListInUpdate["LastBlockSent"] + 300):
            _handle_ota_timeout(self)
            return

        if nwk_id and self.ListInUpdate["LastBlockSent"] == 0 and loaded_time_stamp != 0:
            _retry_notification(self)

        if retry == 10:
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


    def restapi_firmware_update(self, data):  #

        if len(data) > 1:
            logging(self, "Error", "For now we support only Update of 1 device at a time!")
            return
        for x in data:
            brand = x["Brand"]
            file_name = x["FileName"]
            target_nwkid = x["NwkId"]
            target_ep = x["Ep"]
            force_update = x["ForceUpdate"]
            firmware_update(self, brand, file_name, target_nwkid, target_ep, force_update)
            if force_update:
                self.AuthorizedForDowngrade[ target_nwkid ] = True


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
            zcl_raw_ota_query_next_image_response(self, Sqn, srcnwkid, ZIGATE_EP, srcep, '98')
            return

        # Command: 0x01

        fieldcontrol = int(Data[:2],16)
        manufcode = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[2:6], 16)))[0]
        imagetype = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[6:10], 16)))[0]
        currentVersion = "%08x" % struct.unpack("I", struct.pack(">I", int(Data[10:18], 16)))[0]
        if fieldcontrol:
            hardwareversion = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[18:22], 16)))[0]

        logging(self, "Debug", "OTA Query Next Image request for %s/%s [%s] - %s %s %s %s" % (
            srcnwkid, srcep, Sqn, fieldcontrol, manufcode, imagetype, currentVersion ))

        if "OTAClient" not in self.ListOfDevices[srcnwkid]:
            self.ListOfDevices[srcnwkid]["OTAClient"] = {}
        self.ListOfDevices[srcnwkid]["OTAClient"]["ManufacturerCode"] = manufcode
        self.ListOfDevices[srcnwkid]["OTAClient"]["ImageType"] = imagetype
        self.ListOfDevices[srcnwkid]["OTAClient"]["CurrentImageVersion"] = currentVersion 

        image_found = is_image_for_query_next_image_request( self, srcnwkid, manufcode, imagetype, currentVersion )
        if image_found:     
            fileversion = "%08x" %image_found["originalVersion"]
            imagesize = "%08x" %image_found["intSize"]
            
            if "autoServeOTA" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["autoServeOTA"]:
                self.ListInUpdate["AuthorizedForUpdate"].append( srcnwkid )
                return zcl_raw_ota_query_next_image_response(self, Sqn, srcnwkid, ZIGATE_EP, srcep, '00', manufcode, imagetype, fileversion, imagesize)
            
            elif srcnwkid in self.ListInUpdate["AuthorizedForUpdate"]:
                # We are in the case were we get a request, but do not authorised selfserving OTA
                return zcl_raw_ota_query_next_image_response(self, Sqn, srcnwkid, ZIGATE_EP, srcep, '00', manufcode, imagetype, fileversion, imagesize)
            
        elif "checkFirmwareAgainstZigbeeOTARepository" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["checkFirmwareAgainstZigbeeOTARepository"]:
            if (int(manufcode,16), int(imagetype,16), int(currentVersion,16)) not in self.zigbee_ota_found_in_index:
                _ota_available = check_ota_availability_from_index( self, int(manufcode,16), int(imagetype,16), int(currentVersion,16) )
                if _ota_available:
                    self.zigbee_ota_found_in_index.append( ( int(manufcode,16), int(imagetype,16), int(currentVersion,16))  )
                    notify_ota_firmware_available(self, srcnwkid, int(manufcode,16), int(imagetype,16), int(currentVersion,16), _ota_available )

        # No Image available
        zcl_raw_ota_query_next_image_response(self, Sqn, srcnwkid, ZIGATE_EP, srcep, '98')


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
    return (
        f"{ADDRESS_MODE['short']:02x}0000"
        f"{decoded_header['file_id']} {decoded_header['header_version']} {decoded_header['header_length']} {decoded_header['header_fctl']}"
        f"{decoded_header['manufacturer_code']} {decoded_header['image_type']} {force_version or decoded_header['image_version']}"
        f"{decoded_header['stack_version']}{''.join('%02X' % i for i in decoded_header['header_str'])}{decoded_header['size']}"
        f"{decoded_header['security_cred_version']} {decoded_header['upgrade_file_dest']} {decoded_header['min_hw_version']} {decoded_header['max_hw_version']}"
    )


def _is_controller_in_raw_mode(self):
    return "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]


def _update_image_loaded_info(self, decoded_header, force_version):
    self.ImageLoaded["ImageVersion"] = force_version or decoded_header['image_version']
    self.ImageLoaded["image_type"] = decoded_header['image_type']
    self.ImageLoaded["manufacturer_code"] = decoded_header['manufacturer_code']
    self.ImageLoaded["LoadedTimeStamp"] = time.time()


def build_ota_data_block(self, block_request, max_data_size):
    sequence = int(block_request["Sequence"], 16)
    offset = int(block_request["Offset"], 16)
    raw_ota_data = self.ListInUpdate["OtaImage"][offset: offset + max_data_size]
    length = min(max_data_size, len(raw_ota_data))

    return sequence, offset, length, raw_ota_data


def build_ota_message(self, dest_addr, dest_ep, sequence, status, offset, image_version, image_type, manufacturer_code, length, raw_ota_data):
    data = "02" + dest_addr + ZIGATE_EP + dest_ep
    data += f"{sequence:02x}{status:02x}{offset:08x}{image_version}{image_type}{manufacturer_code}{length:02x}"
    data += "".join(f"{i:02x}" for i in raw_ota_data)

    return data


def update_list_in_update(self, offset, length):
    self.ListInUpdate["TimeStamps"] = time.time()
    self.ListInUpdate["Status"] = "Transfer Progress"
    self.ListInUpdate["Received"] = offset
    self.ListInUpdate["Sent"] = offset + length


def ota_send_block(self, dest_addr, dest_ep, image_type, msg_image_version, block_request, disable_ack=False):

    if image_type not in self.ListOfImages["ImageType"]:
        logging(self, "Error", f"ota_send_block - unknown image_type {image_type}")
        return False

    if image_type != int(self.ListInUpdate["ImageType"], 16):
        logging(self, "Error", f"ota_send_block - inconsistent ImageType Received: {image_type} Expecting: {self.ListInUpdate['ImageType']}")
        return False

    status = 0x00

    max_data_size = min(block_request["MaxDataSize"], MAX_FRAME_DATA)
    sequence, offset, length, raw_ota_data = build_ota_data_block(self, block_request, max_data_size)
    image_version_hex = f"{msg_image_version:08x}"
    image_type_hex = f"{image_type:04x}"
    manufacturer_code_hex = f"{self.ListInUpdate['intManufCode']:04x}"

    data = build_ota_message(self, dest_addr, dest_ep, sequence, status, offset, image_version_hex, image_type_hex, manufacturer_code_hex, length, raw_ota_data)

    update_list_in_update(self, offset, length)

    logging(self, "Debug", f"ota_send_block - Block sent to {dest_addr}/{dest_ep} Received yet: {offset} Sent now: {length}")

    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        raw_data_hex = "".join(f"{i:02x}" for i in raw_ota_data)
        return zcl_raw_ota_image_block_response_success(
            self, f"{sequence:02x}", dest_addr, ZIGATE_EP, dest_ep, f"{status:02x}",
            manufacturer_code_hex, image_type_hex, image_version_hex, f"{offset:08x}", f"{length:02x}", raw_data_hex, ackIsDisabled=disable_ack
        )

    self.ControllerLink.sendData("0502", data, ackIsDisabled=False, NwkId=dest_addr)


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


def ota_upgrade_end_response(self, sqn, dest_addr, dest_ep, intMsgImageVersion, image_type, intMsgManufCode):  # OK 24/10 with Firmware Ok
    # This function issues an Upgrade End Response to a client to which the server has been
    # downloading an application image. The function is called after receiving an Upgrade
    # End Request from the client, indicating that the client has received the entire
    # application image and verified it
    #
    # UPGRADE_END_RESPONSE 	0x0504
    # u32UpgradeTime is the UTC time, in seconds, at which the client should upgrade the running image with the downloaded image

    # u32CurrentTime is the current UTC time, in seconds, on the server.
    _UpgradeTime = 0x00
    EPOCTime = datetime(2000, 1, 1)
    UTCTime = int((datetime.now() - EPOCTime).total_seconds())

    _FileVersion = intMsgImageVersion
    _ImageType = image_type
    _ManufacturerCode = intMsgManufCode

    datas = "%02x" % ADDRESS_MODE["short"] + dest_addr + ZIGATE_EP + dest_ep
    datas += "%08x" % _UpgradeTime
    datas += "%08x" % 0x00
    datas += "%08x" % _FileVersion
    datas += "%04x" % _ImageType
    datas += "%04x" % _ManufacturerCode
    
    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        zcl_raw_ota_upgrade_end_response(self, sqn, dest_addr, ZIGATE_EP, dest_ep, "%04x" % _ManufacturerCode, "%04x" % _ImageType, "%08x" % _FileVersion, "%08x" %UTCTime, "%08x" % _UpgradeTime)
    else:
        self.ControllerLink.sendData("0504", datas, ackIsDisabled=False, NwkId=dest_addr)

    logging( self, "Log", "ota_management - sending Upgrade End Response, for %s Version: 0x%08X Type: 0x%04x, Manuf: 0x%04X" % (dest_addr, _FileVersion, _ImageType, _ManufacturerCode), )

    if "OTAUpgrade" not in self.ListOfDevices[dest_addr]:
        self.ListOfDevices[dest_addr]["OTAUpgrade"] = {}

    if not isinstance(self.ListOfDevices[dest_addr]["OTAUpgrade"], dict):
        del self.ListOfDevices[dest_addr]["OTAUpgrade"]
        self.ListOfDevices[dest_addr]["OTAUpgrade"] = {}

    now = int(time.time())
    self.ListOfDevices[dest_addr]["OTAUpgrade"][now] = {"Time": datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")}
 
    self.ListOfDevices[dest_addr]["OTAUpgrade"][now]["Version"] = "%08X" % _FileVersion
    self.ListOfDevices[dest_addr]["OTAUpgrade"][now]["Type"] = "%04X" % _ImageType


def ota_management(self, MsgSrcAddr, MsgEP, delay=500):
    # 'SEND_WAIT_FOR_DATA_PARAMS  0x0506  Can be used to delay/pause OTA update'

    # OTA_STATUS_WAIT_FOR_DATA: No data block is included - client should re-request
    #                           a data block after a waiting time
    _status = 0x97

    # CurrentTime is the current UTC time, in seconds, on the server.
    # If UTC time is not supported by the server, this value should be set to zero
    _CurrentTime = 0x00

    # RequestTime is the UTC time, in seconds, at which the client should re-issue
    # an Image Block Request
    _RequestTime = 0x00

    # BlockRequestDelayMs is used in ‘rate limiting’ to specify the value of the ‘block
    # request delay’ attribute for the client - this is the minimum time, in milliseconds,
    # that the client must wait between consecutive block requests (the client will
    # update the local attribute with this value)
    _BlockRequestDelayMs = delay

    datas = (
        f"{ADDRESS_MODE['short']:02x}"
        f"{MsgSrcAddr}{ZIGATE_EP}{MsgEP}"
        f"{_status:02X}"
        f"{_CurrentTime:08X}"
        f"{_RequestTime:08X}"
        f"{_BlockRequestDelayMs:04X}"
    )

    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        return

    logging(self, "Debug", f"ota_management - Reduce Block request to a rate of {_BlockRequestDelayMs} ms")
    self.ControllerLink.sendData("0506", datas, ackIsDisabled=False, NwkId=MsgSrcAddr)


def cleanup_after_completed_upgrade(self, NwkId, Status):
    # Cleanup
    logging(self, "Debug", "cleanup_after_completed_upgrade - Cleanup and house keeping %s %s" % (NwkId, Status))
    self.ListInUpdate["NwkId"] = None
    self.ListInUpdate["Status"] = None
    if NwkId in self.ListInUpdate["AuthorizedForUpdate"] and Status == "00":
        self.ListInUpdate["AuthorizedForUpdate"].remove(NwkId)
    logging(
        self,
        "Debug",
        "cleanup_after_completed_upgrade - After cleanup self.ListInUpdate['Nwkid']: %s self.ListInUpdate['AuthorizedForUpdate']: %s"
        % (self.ListInUpdate["NwkId"], self.ListInUpdate["AuthorizedForUpdate"]),
    )

    if NwkId in self.AuthorizedForDowngrade and self.AuthorizedForDowngrade[ NwkId ]:
        del self.AuthorizedForDowngrade[ NwkId ]

    self.ListInUpdate["Process"] = None

    # Read Attribute in order to refresh the Attributs
    delay_checking_version(self, NwkId)


    # Reset the controller (ziagte in native mode only for now)
    if self.zigbee_communication == "native":
        sendZigateCmd(self, "0002", "00")  # Force Zigate to Normal mode
        sendZigateCmd(self, "0011", "")  # Software Reset

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

def logging(self, logType, message):  # OK 13/10
    self.log.logging("OTA", logType, message)

def is_image_for_query_next_image_request( self, nwkid, manuf_code, image_type, file_version):

    logging(self, "Debug", "is_image_for_query_next_image_request - %s %s %s" % (manuf_code, image_type, file_version))
    for brand_name in self.ListOfImages["Brands"]:
        logging(self, "Debug", "is_image_for_query_next_image_request - checking %s" %brand_name)
        for file_name in self.ListOfImages["Brands"][brand_name]:
            logging(self, "Debug", "    - filename %s %s %s" %(
                file_name,
                self.ListOfImages["Brands"][brand_name][file_name]["intManufCode"], 
                self.ListOfImages["Brands"][brand_name][file_name]["ImageType"]
                )
            )
            if int(manuf_code,16) != self.ListOfImages["Brands"][brand_name][file_name]["intManufCode"]:
                continue
            logging(self, "Debug", "is_image_for_query_next_image_request - potential brand name found:%s ..." % brand_name)

            if int(image_type,16) != self.ListOfImages["Brands"][brand_name][file_name]["ImageType"]:
                continue

            logging(self, "Debug", "is_image_for_query_next_image_request - potential image type found:%s with version %s..." % (
                brand_name, self.ListOfImages["Brands"][brand_name][file_name]["originalVersion"]))

            if int(file_version,16) < self.ListOfImages["Brands"][brand_name][file_name]["originalVersion"]:
                logging(self, "Debug", "is_image_for_query_next_image_request - We have newest firmware available for this device")
                return self.ListOfImages["Brands"][brand_name][file_name]
            
            if nwkid in self.AuthorizedForDowngrade and self.AuthorizedForDowngrade[ nwkid ]:
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
                "intSize": headers["size"],
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


def ota_extract_image_headers(self, subfolder, image):  # OK 13/10
    # Load headers from the image
    ota_image = _open_image_file(self, Path(self.pluginconf.pluginConf["pluginOTAFirmware"]) / subfolder / image)
    if ota_image is None:
        return None

    offset = offset_start_firmware(self, ota_image)
    if offset is None:
        return None

    logging(self, "Debug", "ota_extract_image_headers - offset:%s ..." % offset)
    ota_image = ota_image[offset:]
    headers = unpack_headers(self, ota_image)
    _logging_headers(self, headers)

    logging(
        self,
        "Status",
        "Available Firmware - ManufCode: %4x ImageType: 0x%04x FileVersion: 0x%8x Size: %8s Bytes Filename: %s"
        % (headers["manufacturer_code"], headers["image_type"], headers["image_version"], headers["size"], image),
    )

    return headers["image_type"], headers, ota_image


def _open_image_file(self, filename):  # OK 13/10
    try:
        with open(filename, "rb") as file:
            ota_image = file.read()
    except OSError as err:
        logging(self, "Error", f"ota_extract_image_headers - error when opening {filename} - {err}")
        return None
    if len(ota_image) < 69:
        logging(self, "Error", f"ota_extract_image_headers - invalid file size read {filename} - {len(ota_image)}")
        return None
    return ota_image


def offset_start_firmware(self, ota_image):  # OK 13/10
    # Search for the OTA Upgrade File Identifier ( “0x0BEEF11E” )
    offset = None
    return next(
        (
            i
            for i in range(len(ota_image) - 4)
            if hex(struct.unpack("<I", ota_image[i : i + 4])[0]) == "0xbeef11e"
        ),
        None,
    )


def unpack_headers(self, ota_image):  # OK 13/10
    try:
        header_data = list(struct.unpack("<LHHHHHLH32BLBQHH", ota_image[:69]))
    except struct.error:
        logging(self, "Error", f"ota_extract_image_headers - Error when unpacking: {ota_image[:69]}")
        return None

    for i in range(8, 40):
        if header_data[i] == 0x00:
            header_data[i] = 0x20

    header_data_compact = header_data[:8] + [header_data[8:40]] + header_data[40:]
    header_headers = [
        "file_id",
        "header_version",
        "header_length",
        "header_fctl",
        "manufacturer_code",
        "image_type",
        "image_version",
        "stack_version",
        "header_str",
        "size",
        "security_cred_version",
        "upgrade_file_dest",
        "min_hw_version",
        "max_hw_version",
    ]

    return dict(zip(header_headers, header_data_compact))


def prepare_and_send_block(self, MsgSrcAddr, MsgEP, MsgFileOffset, intMsgImageVersion, intMsgImageType, intMsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, intMsgFieldControl, MsgSQN, disableACK=False):
    self.ListInUpdate["Retry"] = 0

    # Get all block information, and patch if needed ( Legrand )
    block_request = initialize_block_request( self, MsgSrcAddr, MsgEP, MsgFileOffset, intMsgImageVersion, intMsgImageType, intMsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, intMsgFieldControl, MsgSQN, )
    if intMsgImageType != block_request["ImageType"]:
        intMsgImageType = block_request["ImageType"]

    if intMsgImageType not in self.ListOfImages["ImageType"]:
        # Image Type unknown or not loaded
        logging( self, "Error", "prepare_and_send_block %s/%s - 0x%04x image not found" % (MsgSrcAddr, MsgEP, intMsgImageType), )
        return

    if self.ListInUpdate["NwkId"] and intMsgImageType != self.ListInUpdate["intImageType"] and MsgSrcAddr != self.ListInUpdate["NwkId"]:
        # Request which do not belongs to the current upgrade
        logging( self, "Error", "prepare_and_send_block %s/%s - request update while an other is in progress %s " % (MsgSrcAddr, MsgEP, self.ListInUpdate["NwkId"]), )
        return

    logging( self, "Debug", "prepare_and_send_block - [%3s] request - %s/%s Offset: %s version: 0x%08X Type: 0%04X Code: 0x%04X Delay: %s MaxSize: %s Control: 0x%02X" % ( 
        int(MsgSQN, 16), MsgSrcAddr, MsgEP, int(MsgFileOffset, 16), intMsgImageVersion, intMsgImageType, intMsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, intMsgFieldControl, ),)

    if self.ListInUpdate["Process"] is None:
        start_upgrade_infos(self, MsgSrcAddr, intMsgImageType, intMsgManufCode, MsgFileOffset, MsgMaxDataSize)
        self.ListInUpdate["Process"] = "Started"
    else:
        self.ListInUpdate["Process"] = "OnGoing"

    self.ListInUpdate["Status"] = "Block requested"
    self.ListInUpdate["intFileOffset"] = int(MsgFileOffset, 16)
    self.ListInUpdate["LastBlockSent"] = time.time()

    logging( self, "Debug", "prepare_and_send_block - Block Request for %s/%s Image Type: 0x%04X Image Version: %08X Seq: %s Offset: %s Size: %s FieldCtrl: 0x%02X" % ( 
        MsgSrcAddr, block_request["ReqEp"], block_request["ImageType"], block_request["ImageVersion"], MsgSQN, block_request["Offset"], block_request["MaxDataSize"], block_request["FieldControl"], ),)

    ota_send_block(self, MsgSrcAddr, MsgEP, intMsgImageType, intMsgImageVersion, block_request, disable_ack=disableACK)
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
            f"Fixing - [{int(MsgSQN, 16):3}] OTA image Block request - {MsgSrcAddr}/{MsgEP} Offset: {int(MsgFileOffset, 16)} version: 0x{intMsgImageVersion:08X} Type: 0x{intMsgImageType:04X} Code: 0x{intMsgManufCode:04X} Delay: {MsgBlockRequestDelay} MaxSize: {MsgMaxDataSize} Control: 0x{intMsgFieldControl:02X}"
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

    logging(self, "Debug", f"ota_aync_request: There is async request coming {MsgSrcAddr} against {self.ListInUpdate.get('AuthorizedForUpdate')}")

    if MsgSrcAddr not in self.ListInUpdate.get("AuthorizedForUpdate", []):
        if self.pluginconf.pluginConf.get("autoServeOTA", False):
            return False

        # We need to prevent looping on serving if it is not expected!
        logging(self, "Error", f"ota_aync_request: There is no upgrade plan for that device, drop request from {MsgSrcAddr}")
        return False

    if self.ListInUpdate.get("NwkId"):
        logging(
            self,
            "Debug",
            f"ota_aync_request: There is an upgrade in progress {self.ListInUpdate['NwkId']}, drop request from {MsgSrcAddr}",
        )
        return False

    if image_type not in self.ListOfImages.get("ImageType", {}):
        logging(self, "Log", f"ota_aync_request: No Firmware available to satisfy this request by {MsgSrcAddr}")
        return False

    entry = retrieve_image(self, image_type)
    if entry is None:
        logging(self, "Error", f"ota_aync_request: No Firmware available to satisfy this request by {MsgSrcAddr} !!!")

    brand, ota_image_file = entry
    available_image = self.ListOfImages.get("Brands", {}).get(brand, {}).get(ota_image_file, {})
    logging(self, "Debug", f"ota_aync_request: brand: {brand} ota_image_file: {ota_image_file}")

    # Sanity Checks
    if intMsgManufCode != available_image.get("intManufCode"):
        logging(
            self,
            "Error",
            f"ota_aync_request: {MsgSrcAddr} Available Firmware {ota_image_file} is not for this Manufacturer Code {intMsgManufCode}. Dropping",
        )
        return False

    logging(self, "Debug", f"OTA heartbeat - Image: 0x{image_type:04X} from file: {ota_image_file}")

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
        logging(self, "Status", _textmsg)
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


def _logging_headers(self, headers):  # OK 13/10

    if not self.pluginconf.pluginConf.get("debugOTA", False):
        return

    excluded_attributs = {"stack_version", "security_cred_version", "image_version"}
    
    for attribut, value in headers.items():
        if attribut not in excluded_attributs:
            if isinstance(value, int):
                logging(self, "Debug", f"==> {attribut}: 0x{value:X}")
            else:
                logging(self, "Debug", f"==> {attribut}: {value}")

    # Decoding File Version
    image_version = headers["image_version"]
    logging(self, "Debug", f"==> File Version: 0x{image_version:08X}")
    logging(self, "Debug", f"==>    Application Release: 0x{(image_version & 0xFF000000) >> 24:02X}")
    logging(self, "Debug", f"==>    Application Build: {(image_version & 0x00FF0000) >> 16}")
    logging(self, "Debug", f"==>    Stack Release: {(image_version & 0x0000FF00) >> 8}")
    logging(self, "Debug", f"==>    Stack Build: {image_version & 0x000000FF}")

    # Stack version
    stack_version = headers["stack_version"]
    stack_names = {
        0x0000: "ZigBee 2006",
        0x0001: "ZigBee 2007",
        0x0002: "ZigBee Pro",
        0x0003: "ZigBee IP",
    }
    logging(self, "Debug", f"==> Stack Name: {stack_names.get(stack_version, 'Reserved')}")

    # Security Credential
    security_cred_version = headers["security_cred_version"]
    credential_names = {
        0x00: "SE 1.0",
        0x01: "SE 1.1",
        0x02: "SE 2.0",
    }
    logging(self, "Debug", f"==> Security Credential: {credential_names.get(security_cred_version, 'Reserved')}")


def display_percentage_progress(self, MsgSrcAddr, MsgEP, intMsgImageType, MsgFileOffset):

    _size = self.ListInUpdate.get("intSize", 1)  # Default to 1 to avoid division by zero
    _completion = round((int(MsgFileOffset, 16) / _size) * 100, 1)

    if _completion % 5 == 0:
        logging(self, "Status", f"Firmware transfer for {MsgSrcAddr}/{MsgEP} - Progress: {_completion:4.1f} %")
        update_firmware_health(self, MsgSrcAddr, _completion)


def update_firmware_health(self, MsgSrcAddr, completion):
    firmware_update_health = self.PluginHealth.setdefault("Firmware Update", {})

    if "Progress" not in firmware_update_health:
        firmware_update_health["Progress"] = {}

    firmware_update_health["Progress"] = f"{round(completion)}%"
    firmware_update_health["Device"] = MsgSrcAddr


def start_upgrade_infos(self, MsgSrcAddr, intMsgImageType, intMsgManufCode, MsgFileOffset, MsgMaxDataSize):  # OK 24/10/2020

    entry = retrieve_image(self, intMsgImageType)
    if entry is None:
        logging(self, "Error", "start_upgrade_infos: No Firmware available to satify this request by %s !!!" % MsgSrcAddr)
        return
    brand, ota_image_file = entry

    available_image = self.ListOfImages["Brands"][brand][ota_image_file]
    self.ListInUpdate["intSize"] = available_image["intSize"]
    self.ListInUpdate["ImageVersion"] = available_image["intImageVersion"]
    self.ListInUpdate["Process"] = available_image["Process"]
    self.ListInUpdate["Decoded Header"] = available_image["Decoded Header"]
    self.ListInUpdate["OtaImage"] = available_image["OtaImage"]

    self.ListInUpdate["ImageType"] = "%04x" % intMsgImageType
    self.ListInUpdate["intImageType"] = intMsgImageType
    self.ListInUpdate["NwkId"] = MsgSrcAddr
    self.ListInUpdate["intManufCode"] = intMsgManufCode
    self.ListInUpdate["intFileOffset"] = int(MsgFileOffset, 16)
    self.ListInUpdate["Brand"] = brand
    self.ListInUpdate["FileName"] = ota_image_file
    self.ListInUpdate["LastBlockSent"] = 0
    self.ListInUpdate["StartTime"] = time.time()

    if "Firmware Update" not in self.PluginHealth:
        self.PluginHealth["Firmware Update"] = {}
    if "Firmware Update" in self.PluginHealth:
        self.PluginHealth["Firmware Update"] = {}
    if self.PluginHealth["Firmware Update"] is None:
        self.PluginHealth["Firmware Update"] = {}

    self.PluginHealth["Firmware Update"]["Progress"] = "0%"
    self.PluginHealth["Firmware Update"]["Device"] = MsgSrcAddr

    _ieee = self.ListOfDevices[MsgSrcAddr]["IEEE"]

    _name = next((self.Devices[x].Name for x in self.Devices if self.Devices[x].DeviceID == _ieee), None)

    _durhh, _durmm, _durss = convert_time(self.ListInUpdate["intSize"] // MsgMaxDataSize)
    _textmsg = "Firmware update started for Device: %s with %s - Estimated Time: %s H %s min %s sec " % (
        _name,
        self.ListInUpdate["FileName"],
        _durhh,
        _durmm,
        _durss,
    )
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
        len(self.zigbee_ota_index), manufcode, manufcode, imagetype, imagetype, fileversion, fileversion))

    return next((_image for _image in self.zigbee_ota_index if (_image["manufacturerCode"] == manufcode and _image["imageType"] == imagetype and _image["fileVersion"] > fileversion)), {})


def notify_ota_firmware_available(self, srcnwkid, manufcode, imagetype, fileversion, _ota_available ):

    folder = next((OTA_CODES[supported_manufacturer]["Folder"] for supported_manufacturer in OTA_CODES if OTA_CODES[supported_manufacturer]["ManufCode"] == manufcode), None)

    logging(self, "Status", "We have detected a potential new firmware for the device %s [%s]" %( get_device_nickname( self, NwkId=srcnwkid, ), srcnwkid ))
    logging(self, "Status", "   current version: %s" % fileversion)
    logging(self, "Status", "     firmware type: %s" % imagetype)
    logging(self, "Status", "    newest version: %s" % _ota_available["fileVersion"])
    logging(self, "Status", "     firmware type: %s" % _ota_available["imageType"])
    logging(self, "Status", "   URL to download: %s" % _ota_available["url"])

    if folder:
        logging(self, "Status", "   Folder to store: %s" % folder)
    else:
        logging(self, "Status", "   to get this Manufacturer supported: %s" % manufcode)
        logging(self, "Status", "   provide those informations: %s" % _ota_available)
        logging(self, "Status", "   open an Issue on GitHub here: https://github.com/zigbeefordomoticz/Domoticz-Zigbee/issues/new?assignees=&labels=&template=feature_request.md&title=")


def _load_json_from_url( self, url ):

    import json
    import socket
    import urllib.request

    retry = 3
    while retry:
        try:
            with urllib.request.urlopen( url ) as response:
                return json.loads( response.read() )

        except urllib.error.HTTPError as e:
            if e.code in [429,504]:  # 429=too many requests, 504=gateway timeout
                reason = f'{e.code} {str(e.reason)}'
            elif isinstance(e.reason, socket.timeout):
                reason = f'HTTPError socket.timeout {e.reason} - {e}'
            else:
                reason = f'unknown {e.reason} - {e}'
        except urllib.error.URLError as e:
            if isinstance(e.reason, socket.timeout):
                reason = f'URLError socket.timeout {e.reason} - {e}'
            else:
                reason = f'unknown {e.reason} - {e}'
        except socket.timeout as e:
            reason = f'socket.timeout {e}'

        time.sleep(1)
        retry -= 1

    logging(self, "Error", "loading_zigbee_ota_index: Unable to access %s Reason: %s" %(
        url, reason))
    return []
