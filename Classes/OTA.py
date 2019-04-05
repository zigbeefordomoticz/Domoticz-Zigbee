#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#


"""
    References: 
        - https://www.nxp.com/docs/en/user-guide/JN-UG-3115.pdf ( section 40 - OTA Upgrade Cluster
        - https://github.com/fairecasoimeme/ZiGate/issues?utf8=%E2%9C%93&q=OTA

    1- On the server, when a new client image is available for download, the function eOTA_NewImageLoaded() should be called to request the OTA Upgrade cluster to validate the image. 
    2- The server must then notify the relevant client(s) of the availability of the new image.

    On arrival at the server, the Query Next Image Request message triggers a Query Next Image Request event
    3- The server automatically replies to the request with a Query Next Image Response (the application can also send this response by calling the function eOTA_ServerQueryNextImageResponse()).
    4- The OTA Upgrade cluster on the client now automatically requests the upgrade image one block at a time by sending an Image Block Request to the server (this request can also be sent by the application through a call to the function eOTA_ClientImageBlockRequest()).
    5- The server automatically responds to each block request with an Image Block Response containing a block of data (the application can also send this response by calling the function eOTA_ServerImageBlockResponse())
    6- The client determines when the entire image has been received (by referring to the image size that was quoted in the Query Next Image Response before the download started). Once the final block of image data has been received, the client application should transmit an Upgrade End Request to the server (i.e. by calling eOTA_HandleImageVerification()).
    This Upgrade End Request may report success or an invalid image. In the case of an invalid image, the image will be discarded by the client, which may initiate a new download of the image by sending a Query Next Image Request to the server.On arrival at the server, the Upgrade End Request message triggers an Upgrade End Request event
    7- The server replies to the request with an Upgrade End Response containing an instruction of when the client should use the downloaded image to upgrade the running software on the node (the message contains both the current time and the upgrade time, and hence an implied delay).On arrival at the client, the Upgrade End Response message triggers an Upgrade End Response event.
    8- The client will then count down to the upgrade time (in the Upgrade End Response) and on reaching it, start the upgrade. If the upgrade time has been set to an indefinite value (represented by 0xFFFFFFFF), the client should poll the server for an Upgrade Command at least once per minute and start the upgrade once this command has been received.
    9- Once triggered on the client, the upgrade process will proceed


    Process

    Server      Zigate      Client

    0x0500 ----->

    0x8501 <------------------
    0x0502 ------------------>
    0x0504 ------------------>

    0x8503 <-----------------

    or

    0x0500 ----->
    0x0505 ----------------->

    0x8501 <------------------
    0x0502 ------------------>
    0x0504 ------------------>


"""

import Domoticz

import binascii
import struct

from os import listdir
from os.path import isfile, join
from time import time

from Modules.consts import ADDRESS_MODE

from Classes.AdminWidgets import AdminWidgets

OTA_CLUSTER_ID = '0019'

class OTAManagement(object):

    def __init__( self, PluginConf, adminWidgets, ZigateComm, HomeDirectory, hardwareID, Devices, ListOfDevices, IEEE2NWK ):

        Domoticz.Debug("OTAManagement __init__")
        self.HB = 0
        self.ListOfDevices = ListOfDevices  # Point to the Global ListOfDevices
        self.IEEE2NWK = IEEE2NWK            # Point to the List of IEEE to NWKID
        self.Devices = Devices              # Point to the List of Domoticz Devices
        self.adminWidgets = adminWidgets
        self.ZigateComm = ZigateComm        # Point to the ZigateComm object
        self.pluginconf = PluginConf
        self.homeDirectory = HomeDirectory
        self.OTA = {} # Store Firmware infos
        self.OTA['Upgraded Device'] = {}
        self.availableManufCode = []
        self.upgradableDev = None
        self.upgradeInProgress = None

        self.ota_scan_folder()

    # Low level commands/messages
    def ota_decode_new_image( self, image ):
        'LOAD_NEW_IMAGE 	0x0500 	Load headers to ZiGate. Use this command first.'
        
        return

    def ota_load_new_image( self, key):
        " Send the image headers to Zigate."

        return

    def ota_request_firmware( self , MsgData):
        'BLOCK_REQUEST 	0x8501 	ZiGate will receive this command when device asks OTA firmware'

        return

    def ota_block_send( self , dest_addr, dest_ep, image, block_request):
        'BLOCK_SEND 	0x0502 	This is used to transfer firmware BLOCKS to device when it sends request 0x8501.'

        return 

    def ota_upgrade_end_response( self ):
        'UPGRADE_END_RESPONSE 	0x0504'

        return

    def ota_image_advertize(self, dest_addr, dest_ep):
        'IMAGE_NOTIFY 	0x0505 	Notify desired device that ota is available. After loading headers use this.'

        return


    def ota_management( self ):
        'SEND_WAIT_FOR_DATA_PARAMS 	0x0506 	Can be used to delay/pause OTA update'

        return True


    def ota_request_firmware_completed( self , MsgData):
        'UPGRADE_END_REQUEST 	0x8503 	Device will send this when it has received last part of firmware'

        return

    def ota_scan_folder( self):
        """
        Scanning the Firmware folder and processing them
        """
        return 

    def heartbeat( self ):
        """ call by plugin onHeartbeat """


        return
