#!/usr/bin/env python3 # coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#

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

import Domoticz

import binascii
import struct

from os import listdir
from os.path import isfile, join
from time import time
from datetime import datetime

from Modules.zigateConsts import ADDRESS_MODE, HEARTBEAT, MAX_LOAD_ZIGATE, ZIGATE_EP

from Classes.AdminWidgets import AdminWidgets
from Classes.LoggingManagement import LoggingManagement

OTA_CLUSTER_ID = '0019'

OTA_CODES = {
    'Ikea':      { 'Folder': 'IKEA-TRADFRI',    'ManufCode': 0x117c, 'ManufName': 'IKEA of Sweden',     'Enabled': True},
    'Ledvance':  { 'Folder': 'LEDVANCE',        'ManufCode': 0x1189, 'ManufName': 'LEDVANCE',           'Enabled': True},
    'Osram#1':   { 'Folder': 'LEDVANCE',        'ManufCode': 0xbbaa, 'ManufName': 'OSRAM',              'Enabled': True},
    'Osram#2':   { 'Folder': 'LEDVANCE',        'ManufCode': 0x110C, 'ManufName': 'OSRAM',              'Enabled': True},
    'Legrand':   { 'Folder': 'LEGRAND',         'ManufCode': 0x1021, 'ManufName': 'Legrand',            'Enabled': True},
    'Philips':   { 'Folder': 'PHILIPS',         'ManufCode': 0x100b, 'ManufName': 'Philips',            'Enabled': True},
    'Schneider': { 'Folder': 'SCHNEIDER-WISER', 'ManufCode': 0x105e, 'ManufName': 'Schneider Electric', 'Enabled': True},
    'Salus':     { 'Folder': 'SALUS',           'ManufCode': 0x1078, 'ManufName': 'Computime',          'Enabled': True},
}


class OTAManagement(object):

    def __init__( self, PluginConf, adminWidgets, ZigateComm, HomeDirectory, hardwareID, Devices, ListOfDevices, IEEE2NWK, log, PluginHealth ):

        self.HB = 0
        self.ListOfDevices = ListOfDevices  # Point to the Global ListOfDevices
        self.IEEE2NWK = IEEE2NWK            # Point to the List of IEEE to NWKID
        self.Devices = Devices              # Point to the List of Domoticz Devices
        self.adminWidgets = adminWidgets
        self.ZigateComm = ZigateComm        # Point to the ZigateComm object
        self.pluginconf = PluginConf
        self.homeDirectory = HomeDirectory
        self.log = log
        self.PluginHealth = PluginHealth


        self.ListOfImages = {}      # List of available firmware loaded at plugin startup

        self.ImageLoaded = {        # Indicates information of the current Firmware/Image loaded on ZiGate
            'ImageVersion': None,
            'image_type': None,
            'manufacturer_code': None,
            'LoadedTimeStamp': 0,
            'Notified': False,
            'NotifiedTimeStamp': 0,
            }

        self.ListInUpdate = {       # Tracking requested update information
            'FileName': None,
            'intImageType': None,
            'intImageVersion': None,
            'ImageVersion': None,
            'Process': None,
            'LastBlockSent': 0,
            'NwkId': None,
            'Ep': None,
            'intManufCode': None,
            'LastBlockSent': 0,
            'AuthorizedForUpdate': [],
            'Retry': 0
        }


        self.once = True
        ota_scan_folder( self )

    def cancel_current_firmware_update( self ):
        self.ListInUpdate['NwkId'] = None
        self.ListInUpdate['LastBlockSent'] = 0
        self.ListInUpdate['Retry'] = 0
        self.ImageLoaded['NotifiedTimeStamp'] = 0
        self.ImageLoaded['LoadedTimeStamp'] = 0
        self.ListInUpdate['Process'] = None

    def ota_request_firmware( self , MsgData):  # OK 13/10
        # ota_request_firmware(self, Devices, MsgData, MsgLQI):  # OTA image block request
        # BLOCK_REQUEST  0x8501  ZiGate will receive this command when device asks OTA firmware
        logging( self,  'Debug+', "ota_request_firmware - Request Firmware Block (%s) %s" %(len(MsgData), MsgData))
        MsgSQN =                 MsgData[0:2]
        MsgEP =                  MsgData[2:4]
        # MsgClusterId =         MsgData[4:8]
        # MsgaddrMode =          MsgData[8:10]
        MsgSrcAddr =             MsgData[10:14]
        MsgIEEE =                MsgData[14:30]
        MsgFileOffset =          MsgData[30:38]
        intMsgImageVersion = int(MsgData[38:46],16)
        intMsgImageType =    int(MsgData[46:50],16)
        intMsgManufCode =    int(MsgData[50:54],16)
        MsgBlockRequestDelay =   MsgData[54:58]
        MsgMaxDataSize =         MsgData[58:60]
        intMsgFieldControl = int(MsgData[60:62],16)

        logging( self,  'Debug', "ota_request_firmware - Request Firmware %s/%s Offset: %s Version: 0x%08x Type: 0x%04X Manuf: 0x%04X Delay: %s MaxSize: %s Control: 0x%02X"
            %(MsgSrcAddr, MsgEP, int(MsgFileOffset,16), intMsgImageVersion, intMsgImageType, intMsgManufCode, int(MsgBlockRequestDelay,16), int(MsgMaxDataSize,16), intMsgFieldControl))

        if self.ListInUpdate['NwkId'] is None:
            logging( self,  'Debug', "ota_request_firmware - Async request from device: %s." %(MsgSrcAddr))
            if not async_request( self, MsgSrcAddr, MsgEP, MsgIEEE, MsgFileOffset, intMsgImageVersion, intMsgImageType, intMsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, intMsgFieldControl):
                logging( self,  'Debug', "ota_request_firmware %s/%s - Async request failed %s " %(MsgSrcAddr, MsgEP, self.ListInUpdate))
                return

        self.ListInUpdate['Retry'] = 0

        # Get all block information, and patch if needed ( Legrand )
        block_request = initialize_block_request( self, MsgSrcAddr, MsgEP, MsgFileOffset, intMsgImageVersion, intMsgImageType, 
                                            intMsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, intMsgFieldControl, MsgSQN) 
        if intMsgImageType != block_request['ImageType']:
            intMsgImageType = block_request['ImageType']

        if intMsgImageType not in self.ListOfImages['ImageType']:
            # Image Type unknown or not loaded
            logging( self,  'Error', "ota_request_firmware %s/%s - 0x%04x image not found" %(MsgSrcAddr, MsgEP, intMsgImageType))
            return                

        if self.ListInUpdate['NwkId'] and intMsgImageType != self.ListInUpdate['intImageType'] and MsgSrcAddr != self.ListInUpdate['NwkId']:
            # Request which do not belongs to the current upgrade
            logging( self,  'Error', "ota_request_firmware %s/%s - request update while an other is in progress %s " %(MsgSrcAddr, MsgEP, self.ListInUpdate['NwkId']))
            return

        logging( self,  'Debug', "ota_request_firmware - [%3s] OTA image Block request - %s/%s Offset: %s version: 0x%08X Type: 0%04X Code: 0x%04X Delay: %s MaxSize: %s Control: 0x%02X"
            %(int(MsgSQN,16), MsgSrcAddr, MsgEP, int(MsgFileOffset,16), intMsgImageVersion, intMsgImageType, intMsgManufCode, int(MsgBlockRequestDelay,16), int(MsgMaxDataSize,16), intMsgFieldControl))

        if self.ListInUpdate['Process'] is None:
            start_upgrade_infos( self, MsgSrcAddr, intMsgImageType, intMsgManufCode, MsgFileOffset, MsgMaxDataSize)
            self.ListInUpdate['Process'] = 'Started'
        else:
            self.ListInUpdate['Process'] = 'OnGoing'

        display_percentage_progress( self, MsgSrcAddr, MsgEP, intMsgImageType, MsgFileOffset )

        self.ListInUpdate['Status'] = 'Block requested'
        self.ListInUpdate['intFileOffset'] = int(MsgFileOffset,16)
        self.ListInUpdate['LastBlockSent'] = time()

        # self. ota_management( MsgSrcAddr, MsgEP )

        logging( self,  'Debug', "ota_request_firmware - Block Request for %s/%s Image Type: 0x%04X Image Version: %08X Seq: %s Offset: %s Size: %s FieldCtrl: 0x%02X" \
            %(MsgSrcAddr, block_request['ReqEp'], block_request['ImageType'], \
                block_request['ImageVersion'], MsgSQN, (block_request['Offset'],16), 
               int(block_request['MaxDataSize'],16), block_request['FieldControl']))

        ota_send_block( self, MsgSrcAddr, MsgEP, intMsgImageType, intMsgImageVersion, block_request )           


    def ota_request_firmware_completed( self , MsgData):
        # Decode8503(self, Devices, MsgData, MsgLQI):  # OTA image block request
        # UPGRADE_END_REQUEST    0x8503  Device will send this when it has received last part of firmware'
        #define OTA_STATUS_SUCCESS                        (uint8)0x00
        #define OTA_STATUS_ABORT                          (uint8)0x95
        #define OTA_STATUS_NOT_AUTHORISED                 (uint8)0x7E
        #define OTA_STATUS_IMAGE_INVALID                  (uint8)0x96
        #define OTA_STATUS_WAIT_FOR_DATA                  (uint8)0x97
        #define OTA_STATUS_NO_IMAGE_AVAILABLE             (uint8)0x98
        #define OTA_MALFORMED_COMMAND                     (uint8)0x80
        #define OTA_UNSUP_CLUSTER_COMMAND                 (uint8)0x81
        #define OTA_REQUIRE_MORE_IMAGE                    (uint8)0x99
        logging( self,  'Debug2', "Decode8503 - Request Firmware Completed %s/%s" %(MsgData, len(MsgData)))
        MsgSQN             = MsgData[0:2]
        MsgEP              = MsgData[2:4]
        MsgClusterId       = MsgData[4:8]
        MsgaddrMode        = MsgData[8:10]
        MsgSrcAddr         = MsgData[10:14]
        intMsgImageVersion = int(MsgData[14:22],16)
        image_type         = int(MsgData[22:26],16)
        intMsgManufCode    = int(MsgData[26:30],16)
        MsgStatus          = MsgData[30:32]

        logging( self, 'Debug', "OTA upgrade completed - %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s"
            %(MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus))

        if self.ListInUpdate['NwkId'] is None:
            logging( self,  'Log', "ota_request_firmware_completed - Receive Firmware Completed from %s most likely a duplicated packet as there is nothing in Progress. " %(MsgSrcAddr))
            return
        
        if self.ListInUpdate['NwkId'] and MsgSrcAddr != self.ListInUpdate['NwkId']:
            logging( self, 'Error', "ota_request_firmware_completed - OTA upgrade completed - %s not in Upgraded devices" %MsgSrcAddr)
            return

        if 'StartTime' not in self.ListInUpdate:
            logging( self, 'Error', "ota_request_firmware_completed - OTA upgrade completed - No Start Time for device: %s" %MsgSrcAddr)
            return

        if MsgStatus == '00': # OTA_STATUS_SUCCESS
            logging( self, 'Status', "OTA upgrade completed with success - %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s"
                %(MsgSrcAddr, MsgEP, MsgClusterId, intMsgImageVersion, image_type, intMsgManufCode, MsgStatus))
            ota_upgrade_end_response( self, MsgSrcAddr, MsgEP,intMsgImageVersion, image_type, intMsgManufCode )
            notify_upgrade_end( self, 'OK', MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion )

        elif MsgStatus == '95': # OTA_STATUS_ABORT The image download that is currently in progress should be cancelled
            logging( self,  'Error',"ota_request_firmware_completed - OTA Firmware aborted")
            notify_upgrade_end( self, 'Aborted', MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion )
            
        elif MsgStatus == '96': # OTA_STATUS_INVALID_IMAGE: The downloaded image failed the verification
                                # checks and will be discarded
            logging( self,  'Error',"ota_request_firmware_completed - OTA Firmware image validation failed")
            notify_upgrade_end( self, 'Failed', MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion )

        elif MsgStatus == '99': # OTA_REQUIRE_MORE_IMAGE: The downloaded image was successfully received 
                                # and verified, but the client requires multiple images before performing an upgrade
            logging( self,  'Status', "ota_request_firmware_completed - OTA Firmware  The downloaded image was successfully received, but there is a need for additional image")
            notify_upgrade_end( self, 'More', MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion )

        else:
            logging( self,  'Error',"ota_request_firmware_completed - OTA Firmware unexpected error %s" %MsgStatus)
            notify_upgrade_end( self, 'Aborted', MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion )

        cleanup_after_completed_upgrade( self, MsgSrcAddr, MsgStatus)


    def heartbeat( self ):

        if self.ListInUpdate['NwkId'] is None:
            # Nothing to do.
            logging( self,  'Debug', "ota_heartbeat - nothing to do")
            return

        logging( self,  'Debug', "ota_heartbeat - NwkId: %s Process: %s Loaded: 0x%s Time: %s Notified: %s Retry: %s Authorized: %s" 
            %(self.ListInUpdate['NwkId'],
            self.ListInUpdate['Process'] ,
            self.ImageLoaded['image_type'],
            self.ImageLoaded['LoadedTimeStamp'], 
            self.ImageLoaded['NotifiedTimeStamp'], 
            self.ListInUpdate['Retry'],
            self.ListInUpdate['AuthorizedForUpdate'] 
            ))

        # Do we have a TimeOut on Sending Blocks
        if self.ListInUpdate['NwkId'] and self.ListInUpdate['LastBlockSent'] != 0 and (time() > self.ListInUpdate['LastBlockSent'] + 300):
            logging( self,  'Error', "Ota detects Timeout while sending blocks for %s" %self.ListInUpdate['NwkId'])
            if self.ListInUpdate['NwkId'] in self.ListInUpdate['AuthorizedForUpdate']:
                self.ListInUpdate['AuthorizedForUpdate'].remove( self.ListInUpdate['NwkId'] )
            self.ListInUpdate['NwkId'] = None
            self.ListInUpdate['LastBlockSent'] = 0
            self.ImageLoaded['NotifiedTimeStamp'] = 0
            self.ImageLoaded['LoadedTimeStamp'] = 0
            self.ListInUpdate['Process'] = None
            return

        # Is an image loaded and we need to re-enforce the Notification
        if self.ListInUpdate['NwkId'] and self.ListInUpdate['LastBlockSent'] == 0 and self.ImageLoaded['LoadedTimeStamp'] != 0:
            # Retry every 5s (heartbeat) after 10s after first notification
            self.ListInUpdate['Retry'] += 1
            logging( self,  'Log', "Ota retries notifying device %s" %self.ListInUpdate['NwkId'])
            ota_image_advertize(self, 
                    self.ListInUpdate['NwkId'], 
                    self.ListInUpdate['Ep'], 
                    int( self.ImageLoaded['ImageVersion'],16) , 
                    int( self.ImageLoaded['image_type'],16) , 
                    int( self.ImageLoaded['manufacturer_code'],16) )

        if self.ListInUpdate['Retry'] == 10:
            logging( self,  'Error', "Ota detects Timeout while notifying device %s" %self.ListInUpdate['NwkId'])
            if self.ListInUpdate['NwkId'] in self.ListInUpdate['AuthorizedForUpdate']:
                self.ListInUpdate['AuthorizedForUpdate'].remove( self.ListInUpdate['NwkId'] )
            self.ListInUpdate['NwkId'] = None
            self.ListInUpdate['LastBlockSent'] = 0
            self.ListInUpdate['Retry'] = 0
            self.ImageLoaded['LoadedTimeStamp'] = 0
            self.ImageLoaded['NotifiedTimeStamp'] = 0
            self.ListInUpdate['Process'] = None


    def restapi_list_of_firmware( self ): # OK 26/10
        # Return list of available firmware
        available_firmware = []
        brand = {}
        for x in self.ListOfImages['Brands']:
            brand[x] = []
            for y in self.ListOfImages['Brands'][x]:
                image = {
                    'FileName': y,
                    'ImageType':          '%04x' %   self.ListOfImages['Brands'][x][y]['ImageType'],
                    'ManufCode':          '%04x' %   self.ListOfImages['Brands'][x][y]['intManufCode'],
                    'Version':            '%08x' %   self.ListOfImages['Brands'][x][y]['originalVersion'],
                    'ApplicationRelease': '%02x' % ((self.ListOfImages['Brands'][x][y]['originalVersion'] & 0xff000000) >> 24),
                    'ApplicationBuild':   '%02x' % ((self.ListOfImages['Brands'][x][y]['originalVersion'] & 0x00ff0000) >> 16),
                    'StackRelease':       '%02x' % ((self.ListOfImages['Brands'][x][y]['originalVersion'] & 0x0000ff00) >> 8),
                    'StackBuild':         '%02x' % ((self.ListOfImages['Brands'][x][y]['originalVersion'] & 0x000000ff)),
                }
                brand[x].append( image )
        available_firmware.append( brand )
        return available_firmware


    def restapi_firmware_update( self, data): # 

        if len(data) > 1:
            logging( self,  'Error', "For now we support only Update of 1 device at a time!")
            return
        for x in data:
            brand = x['Brand']
            file_name = x['FileName']
            target_nwkid = x['NwkId']
            target_ep = x['Ep']
            force_update = x['ForceUpdate']
            firmware_update( self, brand, file_name, target_nwkid, target_ep, force_update )


# Routines sending Data

def ota_load_image_to_zigate( self, image_type, force_version=None): # OK 13/10
    # Load the image headers into Zigate

    if image_type not in self.ListOfImages['ImageType']:
        logging( self,  'Debug', "ota_load_image_to_zigate - Unknown Image %s in %s" %(image_type, self.ListOfImages['ImageType'].keys() ))
        return

    brand = self.ListOfImages['ImageType'][ image_type]
    image_entry = retreive_image_in_a_brand( self, image_type, brand)

    if image_entry is None:
        logging( self,  'Debug', "ota_load_image_to_zigate - Image %s inot found in %s" %(image_type, str(self.ListOfImages['Brands'][ brand ]).keys() ))
    image_entry = self.ListOfImages['Brands'][ brand ][ image_entry ]

    file_id = '%08X' %image_entry['Decoded Header']['file_id']
    header_version = '%04X' %image_entry['Decoded Header']['header_version']
    header_length = '%04X' %image_entry['Decoded Header']['header_length']
    header_fctl = '%04X' %image_entry['Decoded Header']['header_fctl']
    manufacturer_code =  '%04X' %image_entry['Decoded Header']['manufacturer_code']
    image_type = '%04X' %image_entry['Decoded Header']['image_type']
    image_version = '%08X' %image_entry['Decoded Header']['image_version']
    if force_version:
        image_version = '%08X' %force_version
    stack_version = '%04X' %image_entry['Decoded Header']['stack_version']
    header_str = ''
    for i in image_entry['Decoded Header']['header_str']:
        header_str += '%02X' %i

    size = '%08X' %image_entry['Decoded Header']['size']
    security_cred_version = '%02X' %image_entry['Decoded Header']['security_cred_version']
    upgrade_file_dest = '%016X' %image_entry['Decoded Header']['upgrade_file_dest']
    min_hw_version = '%04X' %image_entry['Decoded Header']['min_hw_version']
    max_hw_version = '%04X' %image_entry['Decoded Header']['max_hw_version']
    
    datas = "%02x" %ADDRESS_MODE['short'] + "0000"
    datas += file_id + header_version + header_length + header_fctl 
    datas += manufacturer_code + image_type + image_version 
    datas += stack_version + header_str + size 
    datas += security_cred_version + upgrade_file_dest + min_hw_version + max_hw_version

    logging( self,  'Debug', "ota_load_image_to_zigate: - len:%s datas: %s" %(len(datas),datas))
    self.ZigateComm.sendData( "0500", datas)

    self.ImageLoaded['ImageVersion'] = image_version
    self.ImageLoaded['image_type'] = image_type
    self.ImageLoaded['manufacturer_code'] = manufacturer_code
    self.ImageLoaded['LoadedTimeStamp'] = time()



def ota_send_block( self , dest_addr, dest_ep, image_type, msg_image_version, block_request): # OK 24/10
    # 'BLOCK_SEND 	0x0502 	This is used to transfer firmware BLOCKS to device when it sends request 0x8501.'
    # 
    # Indicates whether a data block is included in the response:
    #     OTA_STATUS_SUCCESS: ( 0x00)  A data block is included
    #     OTA_STATUS_WAIT_FOR_DATA (0x97) : No data block is included - client should re-request a data block after a waiting time

    logging( self,  'Debug2', "ota_send_block - Addr: %s/%s Type: 0x%X" %(dest_addr, dest_ep, image_type))
    if image_type not in self.ListOfImages['ImageType']:
        Domoticz.Error("ota_send_block - unknown image_type %s" %image_type)
        return False

    if image_type != int(self.ListInUpdate['ImageType'],16):
        Domoticz.Error("ota_send_block - inconsistent ImageType Received: %s Expecting: %s" %(image_type, self.ListInUpdate['ImageType']))
        return False       
    

    _status = 0x00

    sequence          = int(    block_request['Sequence'],16)
    _offset           = int(    block_request['Offset'],16)
    image_version     = '%08x' %self.ListInUpdate['ImageVersion']
    image_type        = '%04x' %image_type
    manufacturer_code = '%04x' %self.ListInUpdate['intManufCode']
    
    # Build the data block to be send based on the request
    _lenght           = int(block_request['MaxDataSize'],16)
    _raw_ota_data     = self.ListInUpdate['OtaImage'][_offset:_offset+_lenght]

    # Build the message and send
    datas = '07' + dest_addr + ZIGATE_EP + dest_ep 
    datas += "%02x" %sequence + "%02x" %_status 
    datas += "%08x" %_offset 
    datas += image_version + image_type + manufacturer_code
    datas += "%02x" %_lenght
    for i in _raw_ota_data:
        datas += "%02x" %i

    self.ListInUpdate['TimeStamps'] = time()
    self.ListInUpdate['Status'] = 'Transfer Progress'
    self.ListInUpdate['Received'] = _offset
    self.ListInUpdate['Sent'] = _offset + _lenght

    logging( self,  'Debug2', "ota_send_block - Block sent to %s/%s Received yet: %s Sent now: %s" 
            %( dest_addr, dest_ep, _offset, _lenght))

    self.ZigateComm.sendData( "0502", datas)


def ota_image_advertize(self, dest_addr, dest_ep, image_version , image_type = 0xFFFF, manufacturer_code = 0xFFFF ): # OK 24/10
    # 'IMAGE_NOTIFY 	0x0505 	Notify desired device that ota is available. After loading headers use this.'


    # The 'query jitter' mechanism can be used to prevent a flood of replies to an Image Notify broadcast
    # or multicast (Step 2 above). The server includes a number, n, in the range 1-100 in the notification. 
    # If interested in the image, the receiving client generates a random number in the range 1-100. 
    # If this number is greater than n, the client discards the notification, otherwise it responds with 
    # a Query Next Image Request. This results in only a fraction of interested clients res

    JITTER_OPTION = 100


    # teOTA_ImageNotifyPayloadType
    #   - 0 : E_CLD_OTA_QUERY_JITTER Include only ‘Query Jitter’ in payload
    #   - 1 : E_CLD_OTA_MANUFACTURER_ID_AND_JITTER Include ‘Manufacturer Code’ and ‘Query Jitter’ in payload
    #   - 2 : E_CLD_OTA_ITYPE_MDID_JITTER Include ‘Image Type’, ‘Manufacturer Code’ and ‘Query Jit- ter’ in payload
    #   - 3 : E_CLD_OTA_ITYPE_MDID_FVERSION_JITTER Include ‘Image Type’, ‘Manufacturer Code’, ‘File Version’ and ‘Query Jitter’ in payload


    IMG_NTFY_PAYLOAD_TYPE = 3

    self.ImageLoaded['Notified'] = True
    self.ImageLoaded['NotifiedTimeStamp'] = time()

    if IMG_NTFY_PAYLOAD_TYPE == 0:
        image_version = 0xFFFFFFFF  # Wildcard
        image_type = 0xFFFF         # Wildcard
        manufacturer_code = 0xFFFF  # Wildcard

    elif IMG_NTFY_PAYLOAD_TYPE == 1:
        image_version = 0xFFFFFFFF  # Wildcard
        image_type = 0xFFFF         # Wildcard

    elif IMG_NTFY_PAYLOAD_TYPE == 2:
        image_version = 0xFFFFFFFF  # Wildcard

    datas = "%02x" %ADDRESS_MODE['short'] + dest_addr + ZIGATE_EP + dest_ep + "%02x" %IMG_NTFY_PAYLOAD_TYPE
    datas += '%08X' %image_version + '%04x' %image_type + '%04x' %manufacturer_code 
    datas += "%02x" %JITTER_OPTION
    logging( self,  'Debug', "ota_image_advertize - Type: 0x%04x, Version: 0x%08x => datas: %s" %(image_type, image_version, datas))

    self.ZigateComm.sendData( "0505", datas)


def ota_upgrade_end_response( self, dest_addr, dest_ep, intMsgImageVersion, image_type, intMsgManufCode ): # OK 24/10 with Firmware Ok
    # This function issues an Upgrade End Response to a client to which the server has been
    # downloading an application image. The function is called after receiving an Upgrade 
    # End Request from the client, indicating that the client has received the entire 
    # application image and verified it
    # 
    # UPGRADE_END_RESPONSE 	0x0504
    # u32UpgradeTime is the UTC time, in seconds, at which the client should upgrade the running image with the downloaded image
    
    # u32CurrentTime is the current UTC time, in seconds, on the server.
    _UpgradeTime = 0x00
    EPOCTime = datetime(2000,1,1)
    UTCTime = int((datetime.now() - EPOCTime).total_seconds())

    _FileVersion = intMsgImageVersion
    _ImageType = image_type
    _ManufacturerCode = intMsgManufCode

    datas = "%02x"  % ADDRESS_MODE['short'] + dest_addr + ZIGATE_EP + dest_ep
    datas += "%08x" % _UpgradeTime
    datas += "%08x" % 0x00
    datas += "%08x" % _FileVersion
    datas += "%04x" % _ImageType
    datas += "%04x" % _ManufacturerCode
    self.ZigateComm.sendData( "0504", datas)

    logging( self,  'Log', "ota_management - sending Upgrade End Response, for %s Version: 0x%08X Type: 0x%04x, Manuf: 0x%04X" % ( dest_addr, _FileVersion, _ImageType, _ManufacturerCode))

    if 'OTA' not in self.ListOfDevices[ dest_addr ]:
        self.ListOfDevices[ dest_addr ]['OTA'] = {}

    if not isinstance(  self.ListOfDevices[ dest_addr ]['OTA'], dict):
        del  self.ListOfDevices[ dest_addr ]['OTA']
        self.ListOfDevices[ dest_addr ]['OTA'] = {}

    now = int(time())
    self.ListOfDevices[dest_addr]['OTA'][now] = {
        'Time': datetime.fromtimestamp(time()).strftime('%Y-%m-%d %H:%M:%S')
    }

    self.ListOfDevices[ dest_addr ]['OTA'][ now ]['Version'] =  '%08X' %_FileVersion
    self.ListOfDevices[ dest_addr ]['OTA'][ now ]['Type'] =  '%04X' %_ImageType


def ota_management( self, MsgSrcAddr, MsgEP , delay = 500):
    # 'SEND_WAIT_FOR_DATA_PARAMS 	0x0506 	Can be used to delay/pause OTA update'

    # OTA_STATUS_WAIT_FOR_DATA: No data block is included - client should re-request
    #                           a data block after a waiting time
    _status = 0x97

    # CurrentTime is the current UTC time, in seconds, on the server. 
    # If UTC time is not supported by the server, this value should be set to zero
    _CurrentTime = 0x00

    # RequestTime is the UTC time, in seconds, at which the client should re- issue 
    # an Image Block Request
    _RequestTime = 0x00
    
    # BlockRequestDelayMs is used in ‘rate limiting’ to specify the value of the ‘block 
    # request delay’ attribute for the client - this is minimum time, in milliseconds, 
    # that the client must wait between consecutive block requests (the client will 
    # update the local attribute with this value)
    _BlockRequestDelayMs = delay

    datas =  "%02x" %ADDRESS_MODE['short'] + MsgSrcAddr 
    datas += ZIGATE_EP + MsgEP 
    datas += "%02X" %_status
    datas += "%08X" %_CurrentTime
    datas += "%08X" %_RequestTime
    datas += "%04X" %_BlockRequestDelayMs

    logging( self,  'Debug', "ota_management - Reduce Block request to a rate of %s ms" %_BlockRequestDelayMs)
    self.ZigateComm.sendData( "0506", datas)

################
# Local routines
def cleanup_after_completed_upgrade( self, NwkId, Status):
        # Cleanup
        logging( self,  'Debug',"cleanup_after_completed_upgrade - Cleanup and house keeping %s %s" %( NwkId, Status))
        self.ListInUpdate['NwkId'] = None
        if NwkId in self.ListInUpdate['AuthorizedForUpdate'] and Status == '00':
            self.ListInUpdate['AuthorizedForUpdate'].remove( NwkId )
        logging( self,  'Debug',"cleanup_after_completed_upgrade - After cleanup self.ListInUpdate['Nwkid']: %s self.ListInUpdate['AuthorizedForUpdate']: %s" 
            %( self.ListInUpdate['NwkId'], self.ListInUpdate['AuthorizedForUpdate']))
        self.ListInUpdate['Process'] = None

def firmware_update( self, brand, file_name, target_nwkid, target_ep , force_update=False):
    
    if self.ListInUpdate['NwkId']:
            logging( self,  'Error', "There is already an Image loaded %s for device: %s please come back later" 
                %(self.ListInUpdate['FileName'], self.ListInUpdate['NwkId']))
            return False

    if brand not in self.ListOfImages['Brands']:
        Domoticz.Error("restapi_firmware_update Brands %s unknown" %brand)
        return False

    if file_name not in self.ListOfImages['Brands'][brand]:
        Domoticz.Error("restapi_firmware_update FileName %s unknown in this Brand %s" %(file_name,brand ))
        return False

    if target_nwkid not in self.ListOfDevices:
        Domoticz.Error("restapi_firmware_update NwkId: %s unknown" %target_nwkid)
        return False

    if target_ep not in self.ListOfDevices[ target_nwkid]['Ep']:
        Domoticz.Error("restapi_firmware_update NwkId: %s Ep: %s unknown" %(target_nwkid, target_ep))
        return False

    image_type = self.ListOfImages['Brands'][brand][file_name]['ImageType']
    manuf_code = self.ListOfImages['Brands'][brand][file_name]['intManufCode']
    image_version = self.ListOfImages['Brands'][brand][file_name]['originalVersion']

    self.ListInUpdate['NwkId'] = target_nwkid
    self.ListInUpdate['Ep'] = target_ep
    self.ListInUpdate['AuthorizedForUpdate'].append ( target_nwkid )
    self.ListInUpdate['Process'] = None
    # Do we have to overwrite the Image Version in order to force update
    if force_update:
        image_version = self.ListOfImages['Brands'][brand][file_name]['originalVersion'] + 0x00100000
        logging( self,  'Status', "----> Forcing update for Image: 0x%04x from Version: 0x%08X to Version: 0x%08X" 
            %( image_type, self.ListOfImages['Brands'][brand][file_name]['originalVersion'], image_version))
        self.ListOfImages['Brands'][brand][file_name]['intImageVersion'] = image_version
        ota_load_image_to_zigate( self, image_type, image_version)
    else:
        ota_load_image_to_zigate( self, image_type)
    ota_image_advertize(self, target_nwkid, target_ep, image_version = image_version, image_type = image_type, manufacturer_code = manuf_code)
    return True


def logging( self, logType, message): # OK 13/10   
    self.log.logging('OTA', logType, message)


def retreive_image_in_a_brand( self, image_type, brand): # OK 13/10
    if brand not in self.ListOfImages['Brands']:
        return None
    for y in self.ListOfImages['Brands'][ brand ]:
        if image_type == self.ListOfImages['Brands'][ brand ][ y ]['ImageType']:
            return y 


def retreive_image( self, image_type): # OK 13/10
    for x in self.ListOfImages['Brands']:
        for y in self.ListOfImages['Brands'][ x ]:
            if image_type == self.ListOfImages['Brands'][ x ][ y ]['ImageType']:
                return ( x , y )
    return None


def ota_scan_folder( self): #OK 13/10
    # Scanning the Firmware folder
    # At that stage ALL firmware available from each ENABLED folders
    # have been read , decoded and key informations stored in ListOfImages
    # ListOfImages have 2 entries either from brand or from Image Type

    self.ListOfImages['Brands'] = {}
    self.ListOfImages['ImageType'] = {}
    for brand in OTA_CODES:
        if not OTA_CODES[ brand ]['Enabled']:
            continue

        self.ListOfImages['Brands'][ brand ] = {}
        ota_dir = self.pluginconf.pluginConf['pluginOTAFirmware'] + OTA_CODES[ brand ]['Folder']
        ota_image_files = [ f for f in listdir(ota_dir) if isfile(join(ota_dir, f))]

        for ota_image_file in ota_image_files:
            if ota_image_file in ( 'README.md', 'README.txt', '.PRECIOUS', '.precious' ):
                continue

            header_return = ota_extract_image_headers( self, OTA_CODES[ brand ]['Folder'], ota_image_file )
            if header_return is None:
                continue
            image_type, headers, ota_image = header_return

            # Check if this Image is the latest version.
            if image_type in self.ListOfImages[ 'ImageType' ] and not check_image_valid_version( self, brand, image_type, ota_image_file, headers ):
                # Most likely we have a more higher version already loaded!
                continue

            self.ListOfImages['ImageType'][ image_type ] = brand
            self.ListOfImages['Brands'][ brand ][ ota_image_file ] = {
                'Directory'      : ota_dir,
                'Process'        : False,
                'ImageType'      : image_type,
                'Decoded Header' : headers,
                'OtaImage'       : ota_image,
                'intManufCode'   : headers['manufacturer_code'],
                'originalVersion': headers['image_version'],
                'intImageVersion': headers['image_version'],
                'intSize'        : headers['size'],
            }
    # Logging if Debug
    logging( self, 'Debug', 'ota_scan_folder Following Firmware have been loaded ')
    for brand, value in self.ListOfImages['Brands'].items():
        for ota_image_file in value:
            logging( self, 'Debug', " --> Brand: %s Image File: %s" %( brand, ota_image_file))


def check_image_valid_version( self, brand, image_type , ota_image_file, headers): # OK 13/10
    # Purpose is to check if the already imported image has a higher version or not.
    # If the version number is the same we will take the existing one

    existing_image = retreive_image( self, image_type)
    if existing_image is None:
        # Strange
        return False
    brand, ota_image_file = existing_image
    existing_image = self.ListOfImages['Brands'][ brand ][ ota_image_file ]
    if existing_image['originalVersion'] >= headers['image_version']:
        # The up coming Image is older than the one already scaned
        #drop it
        logging( self, 'Error', "ota_scan_folder - trying to load an older version of Image Type %s - Do remove file %s" %( image_type, ota_image_file ))
        return False
    # Existing Image is an older version comparing to what we load.
    # Overwrite with the new one.
    # Remove the old ota_image_file and replace by the new one
    del self.ListOfImages['Brands'][ brand ][ ota_image_file ]
    return True


def ota_extract_image_headers( self, subfolder, image ): # OK 13/10
    # Load headers from the image 
    ota_image = _open_image_file( self.pluginconf.pluginConf['pluginOTAFirmware'] + subfolder + '/' + image )
    if ota_image is None:
        return None

    offset = offset_start_firmware( ota_image )
    if offset is None:
        return None

    logging( self,  'Debug', "ota_extract_image_headers - offset:%s ..." %offset)
    ota_image = ota_image[offset:]
    headers = unpack_headers( ota_image)
    _logging_headers( self, headers )

    logging( self,  'Status', "Available Firmware - ManufCode: %4x ImageType: 0x%04x FileVersion: %8x Size: %8s Bytes Filename: %s" \
            %(headers['manufacturer_code'], headers['image_type'],  headers['image_version'], headers['size'], image ))
  
    return ( headers['image_type'], headers, ota_image )


def _open_image_file( filename ): # OK 13/10
    try:
        with open( filename , 'rb') as file:
            ota_image = file.read()
    except OSError as err:
        Domoticz.Error("ota_extract_image_headers - error when opening %s - %s" %(filename, err))
        return None
    if len(ota_image) < 69:
        Domoticz.Error("ota_extract_image_headers - invalid file size read %s - %s" %(filename,len(ota_image)))
        return None
    return ota_image


def offset_start_firmware( ota_image ): # OK 13/10
    #Search for the OTA Upgrade File Identifier (  “0x0BEEF11E” )
    offset = None
    for i in range(len(ota_image)-4):
        if hex(struct.unpack('<I',ota_image[0+i:4+i])[0]) == '0xbeef11e':
            return i
    return None


def unpack_headers( ota_image): # OK 13/10
    
    try:
        header_data = list(struct.unpack('<LHHHHHLH32BLBQHH', ota_image[:69]))
    except struct.error:
        Domoticz.Error("ota_extract_image_headers - Error when unpacking: %s" %ota_image[:69])
        return None

    for i in range(8, 40):
        if header_data[i] == 0x00:
            header_data[i] = 0x20

    header_data_compact = header_data[0:8] + [header_data[8:40]] + header_data[40:]
    header_headers = [ 'file_id', 'header_version', 'header_length', 'header_fctl', 
            'manufacturer_code', 'image_type', 'image_version', 
            'stack_version', 'header_str', 'size', 'security_cred_version', 'upgrade_file_dest',
            'min_hw_version', 'max_hw_version' ]

    return dict(zip(header_headers, header_data_compact))


def initialize_block_request( # OK 13/10
    self, MsgSrcAddr, MsgEP, MsgFileOffset, intMsgImageVersion, 
    intMsgImageType, intMsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, intMsgFieldControl, MsgSQN):

    # Patching in order to make Legrand update with Image Page Request working
    if intMsgManufCode == 0x00C8 and self.ListInUpdate['NwkId'] == MsgSrcAddr:
        # Request a Page , and Note a Block
        # For the time been , we are forcing a response with a Block
        intMsgImageType = self.ListInUpdate['intImageType']
        intMsgManufCode = 0x1021
        MsgBlockRequestDelay = 'ffff'
        MsgMaxDataSize = '40'
        intMsgFieldControl = 0x00
        logging( self,  'Debug', "  Fixing   - [%3s] OTA image Block request - %s/%s Offset: %s version: 0x%08X Type: 0%04X Code: 0x%04X Delay: %s MaxSize: %s Control: 0x%02X"
            %(int(MsgSQN,16), MsgSrcAddr, MsgEP, int(MsgFileOffset,16), intMsgImageVersion, intMsgImageType, intMsgManufCode, int(MsgBlockRequestDelay,16), int(MsgMaxDataSize,16), intMsgFieldControl))

    return {
        'ReqAddr': MsgSrcAddr,
        'ReqEp': MsgEP,
        'Offset': MsgFileOffset,
        'ImageVersion': intMsgImageVersion,
        'ImageType': intMsgImageType,
        'ManufCode': intMsgManufCode,
        'BlockReqDelay': MsgBlockRequestDelay,
        'MaxDataSize': MsgMaxDataSize,
        'FieldControl': intMsgFieldControl,
        'Sequence': MsgSQN,
        }


def async_request(  # OK 24/10
    self, MsgSrcAddr, MsgEP, MsgIEEE, MsgFileOffset, image_version, 
    image_type, intMsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, intMsgFieldControl):
    # We are receiving an OTA request 
    # Check if we have an available firmware
    # If yes, then load the firmware on ZiGate

    logging( self,  'Debug', "async_request: There is async request comming %s" %(MsgSrcAddr))
        
    if MsgSrcAddr not in self.ListInUpdate['AuthorizedForUpdate']:
        # We need to prevent looping on serving if it is not expected!
        logging( self,  'Error', "async_request: There is no upgrade plan for that device, drop request from %s" %(MsgSrcAddr))
        return False

    if self.ListInUpdate['NwkId']:
        logging( self,  'Debug', "async_request: There is an upgrade in progress %s, drop request from %s" %(self.ListInUpdate['NwkId'], MsgSrcAddr))
        return False

    if image_type not in self.ListOfImages['ImageType']:
        logging( self,  'Log', "async_request: No Firmware available to satify this request by %s" %(MsgSrcAddr))
        return False

    entry = retreive_image( self, image_type )
    if entry is None:
        logging( self,  'Error', "async_request: No Firmware available to satify this request by %s !!!" %(MsgSrcAddr))

    brand, ota_image_file = entry
    available_image  = self.ListOfImages['Brands'][ brand ][ ota_image_file ]
    logging( self,  'Debug', "async_request: brand: %s ota_image_file: %s" %(brand, ota_image_file))

    # Sanity Checks
    if intMsgManufCode != available_image['intManufCode']:
        logging( self,  'Error', "async_request: %s Available Firmware %s is not for this Manufacturer Code %s . Droping" %(MsgSrcAddr, ota_image_file, intMsgManufCode))
        return False
    logging( self,  'Debug', "OTA heartbeat - Image: 0x%04X from file: %s" %(image_type, ota_image_file))

    # Loading Image on Zigate
    if len(self.ImageLoaded) == 0:
        ota_load_image_to_zigate( self, image_type )

    return True


def notify_upgrade_end( self, Status, MsgSrcAddr, MsgEP, image_type, intMsgManufCode, intMsgImageVersion, ): # OK 26/10

    _transferTime_hh, _transferTime_mm, _transferTime_ss = convertTime( int(time() - self.ListInUpdate['StartTime']))
    _ieee = self.ListOfDevices[MsgSrcAddr]['IEEE']
    _name = None
    _textmsg = ''
    for x in self.Devices:
        if self.Devices[x].DeviceID == _ieee:
            _name = self.Devices[x].Name

    if Status == 'OK':
        _textmsg = 'Device: %s has been updated with firmware %s in %s hour %s min %s sec' \
                %(_name, intMsgImageVersion, _transferTime_hh, _transferTime_mm, _transferTime_ss)
        logging( self,  'Status', _textmsg )
        if ( 'Firmware Update' in self.PluginHealth and len(self.PluginHealth['Firmware Update']) > 0 ):
            self.PluginHealth['Firmware Update']['Progress'] = 'Success'

    elif Status == 'Aborted':
        _textmsg = 'Firmware update aborted error code %s for Device %s in %s hour %s min %s sec' \
            %(Status, _name, _transferTime_hh, _transferTime_mm, _transferTime_ss)

        if ( 'Firmware Update' in self.PluginHealth and len(self.PluginHealth['Firmware Update']) > 0 ):
            self.PluginHealth['Firmware Update']['Progress'] = 'Aborted'
    elif Status == 'Failed':
        _textmsg = 'Firmware update aborted error code %s for Device %s in %s hour %s min %s sec' \
            %(Status, _name, _transferTime_hh, _transferTime_mm, _transferTime_ss)
        if ( 'Firmware Update' in self.PluginHealth and len(self.PluginHealth['Firmware Update']) > 0 ):
            self.PluginHealth['Firmware Update']['Progress'] = 'Failed'
    elif Status == 'More':
        _textmsg = 'Device: %s has been updated to latest firmware in %s hour %s min %s sec, but additional Image needed' \
            %(Status, _name, _transferTime_hh, _transferTime_mm, _transferTime_ss)
        if ( 'Firmware Update' in self.PluginHealth and len(self.PluginHealth['Firmware Update']) > 0 ):
            self.PluginHealth['Firmware Update']['Progress'] = 'More'

    self.adminWidgets.updateNotificationWidget( self.Devices, _textmsg)


def convertTime( _timeInSec): # Ok 13/10

    _timeInSec_hh = _timeInSec // 3600
    _timeInSec = _timeInSec - ( _timeInSec_hh * 3600)
    _timeInSec_mm = _timeInSec // 60
    _timeInSec = _timeInSec - ( _timeInSec_mm * 60 )
    _timeInSec_ss = _timeInSec
    return _timeInSec_hh, _timeInSec_mm, _timeInSec_ss 


def _logging_headers( self, headers ): # OK 13/10

    return
    for attribut in headers:
        if attribut in ( 'stack_version', 'security_cred_version', 'image_version'):
            continue
        if isinstance(headers[attribut], int):
            logging( self,  'Debug', "==> %s : 0x%x" %(attribut,headers[attribut]))
        else:
            logging( self,  'Debug', "==> %s : %s" %(attribut,headers[attribut]))

    # Decoding File Version
    logging( self,  'Debug', "==> File Version: 0x%08X" %headers['image_version'])
    logging( self,  'Debug', "==>    Application Release: 0x%02x" % ( (headers['image_version'] & 0xff000000) >> 24))
    logging( self,  'Debug', "==>    Application Build: %s" %( (headers['image_version'] & 0x00ff0000) >> 16))
    logging( self,  'Debug', "==>    Stack Release: %s" %( (headers['image_version'] & 0x0000ff00) >> 8))
    logging( self,  'Debug', "==>    Stack Build: %s" %( (headers['image_version'] & 0x000000ff)))

    # Stack version
    if headers['stack_version'] == 0x0000:
        logging( self,  'Debug', "==> Stack Name: ZigBee 2006")
    elif headers['stack_version'] == 0x0001:
        logging( self,  'Debug', "==> Stack Name: ZigBee 2007")
    elif headers['stack_version'] == 0x0002:
        logging( self,  'Debug', "==> Stack Name: ZigBee Pro")
    elif headers['stack_version'] == 0x0003:
        logging( self,  'Debug', "==> Stack Name: ZigBee IP")
    else:
        logging( self,  'Debug', "==> Stack Name: Reserved")

    # Security Credential
    if headers['security_cred_version'] == 0x00:
        logging( self,  'Debug', "==> Security Credential: SE 1.0")
    elif headers['security_cred_version'] == 0x01:
        logging( self,  'Debug', "==> Security Credential: SE 1.1")
    elif headers['security_cred_version'] == 0x02:
        logging( self,  'Debug', "==> Security Credential: SE 2.0")
    else:
        logging( self,  'Debug', "==> Security Credential: Reserved")


def display_percentage_progress( self, MsgSrcAddr, MsgEP, intMsgImageType, MsgFileOffset  ):

    _size = self.ListInUpdate['intSize']
    _completion = round( ( (int(MsgFileOffset,16) / _size ) * 100), 1 )

    if ( _completion % 5) == 0:
        logging( self,  'Log', "Firmware transfert for %s/%s - Progress: %4s %%" %(MsgSrcAddr, MsgEP, _completion))
        if 'Firmware Update' not in self.PluginHealth:
            self.PluginHealth['Firmware Update'] = {}

        if self.PluginHealth['Firmware Update'] is None:
            self.PluginHealth['Firmware Update'] = {}

    self.PluginHealth['Firmware Update']['Progress'] = '%s %%' %round(_completion)
    self.PluginHealth['Firmware Update']['Device'] = MsgSrcAddr


def start_upgrade_infos( self, MsgSrcAddr, intMsgImageType, intMsgManufCode, MsgFileOffset, MsgMaxDataSize): # OK 24/10/2020

    entry = retreive_image( self, intMsgImageType )
    if entry is None:
        logging( self,  'Error', "start_upgrade_infos: No Firmware available to satify this request by %s !!!" %MsgSrcAddr)
        return 
    brand, ota_image_file = entry

    available_image  = self.ListOfImages['Brands'][ brand ][ ota_image_file ]
    self.ListInUpdate['intSize']             = available_image['intSize']
    self.ListInUpdate['ImageVersion']        = available_image['intImageVersion']
    self.ListInUpdate['Process']             = available_image['Process']
    self.ListInUpdate['Decoded Header']      = available_image['Decoded Header']
    self.ListInUpdate['OtaImage']            = available_image['OtaImage']

    self.ListInUpdate['ImageType']           = '%04x' % intMsgImageType
    self.ListInUpdate['intImageType']        = intMsgImageType
    self.ListInUpdate['NwkId']               = MsgSrcAddr
    self.ListInUpdate['intManufCode']        = intMsgManufCode
    self.ListInUpdate['intFileOffset']       = int(MsgFileOffset,16)
    self.ListInUpdate['Brand']               = brand
    self.ListInUpdate['FileName']            = ota_image_file
    self.ListInUpdate['LastBlockSent']       = 0
    self.ListInUpdate['StartTime']           = time()

    if 'Firmware Update' not in self.PluginHealth:
        self.PluginHealth['Firmware Update'] = {}
    if 'Firmware Update' in self.PluginHealth:
        self.PluginHealth['Firmware Update'] = {}
    if self.PluginHealth['Firmware Update'] is None:
        self.PluginHealth['Firmware Update'] = {}

    self.PluginHealth['Firmware Update']['Progress'] = '0%'
    self.PluginHealth['Firmware Update']['Device'] = MsgSrcAddr

    _ieee = self.ListOfDevices[MsgSrcAddr]['IEEE']
    _name = None
    
    for x in self.Devices:
        if self.Devices[x].DeviceID == _ieee:
            _name = self.Devices[x].Name
            break

    _durhh, _durmm, _durss = convertTime( self.ListInUpdate['intSize'] // int(MsgMaxDataSize,16) )
    _textmsg = 'Firmware update started for Device: %s with %s - Estimated Time: %s H %s min %s sec ' \
        %(_name, self.ListInUpdate['FileName'], _durhh, _durmm, _durss)
    self.adminWidgets.updateNotificationWidget( self.Devices, _textmsg)
