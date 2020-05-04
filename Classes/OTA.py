#!/usr/bin/env python3 # coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#


"""
    References: 
        - https://www.nxp.com/docs/en/user-guide/JN-UG-3115.pdf ( section 40 - OTA Upgrade Cluster
        - https://github.com/fairecasoimeme/ZiGate/issues?utf8=%E2%9C%93&q=OTA

    Server      Zigate      Client

    0x0500 ----->
    0x0505 ----------------->
    0x8501 <------------------
    0x0502 ------------------>

    0x8503 <------------------

'Upgraded Device':
    - Notified
    - Block Requested
    - Transfer Progress
    - Transfer Completed
    - Transfer Aborted
    - Timeout

"""

import Domoticz

import binascii
import struct

from os import listdir
from os.path import isfile, join
from time import time
from datetime import datetime

from Modules.zigateConsts import ADDRESS_MODE, HEARTBEAT, MAX_LOAD_ZIGATE, ZIGATE_EP

from Classes.AdminWidgets import AdminWidgets

OTA_CLUSTER_ID = '0019'
OTA_CYLCLE = 21600      # We check Firmware upgrade every 5 minutes
TO_TRANSFER = 60        # Time before timed out for Transfer
TO_MAINPOWERED_NOTIFICATION = 15          # Time before timed out after notify for main powered devices
TO_BATTERYPOWERED_NOTIFICATION = 1 * 3600 # We will leave the Image loaded on Zigate and Notified by device during 1 hour max.

IKEA_MANUF_CODE = 0x117c
LEDVANCE_MANUF_CODE = ( 0x1189 )
OSRAM_MANUF_CODE    = ( 0xbbaa, 0x110C )

LEGRAND_MANUF_CODE = 0x1021
LEGRAND_MANUF_NAME = 'Legrand'

PHILIPS_MANUF_CODE = 0x100b
PHILIPS_MANUF_NAME = 'Philips'

OTA_MANUF_CODE = ( IKEA_MANUF_CODE, LEDVANCE_MANUF_CODE, OSRAM_MANUF_CODE , LEGRAND_MANUF_CODE, PHILIPS_MANUF_CODE)
OTA_MANUF_NAME = ( '117c', 'IKEA of Sweden', '1189', 'LEDVANCE', 'bbaa', '110c', 'OSRAM', '1021', 'Legrand', '100b', 'Philips')


BATTERY_TYPES = ( 4545, 4546, 4548, 4549 )
"""
  4353 - Control outlet
  4545 - Remote Control
  4546 - Wireless dimmer
  4548 - Motion sensor
  4549 - Switch On/Off 
  8705 - Bulb White spectrum
  8706 - Bulb White Spectrum 1000lm
  8707 - Bulb White Spectrum GU10
  8449 - Bulb white 1000lm
 10241 - Bulb Color + White Spectrum 
 16641 - Transformer
 16897 - Driver LP
 16898 - Driver HP
 16900 - ???
"""


"""
    Legrand Type

    0x0010: Micromodule

"""

class OTAManagement(object):

    def __init__( self, PluginConf, adminWidgets, ZigateComm, HomeDirectory, hardwareID, Devices, ListOfDevices, IEEE2NWK, loggingFileHandle, PluginHealth ):

        self.HB = 0
        self.ListOfDevices = ListOfDevices  # Point to the Global ListOfDevices
        self.IEEE2NWK = IEEE2NWK            # Point to the List of IEEE to NWKID
        self.Devices = Devices              # Point to the List of Domoticz Devices
        self.adminWidgets = adminWidgets
        self.ZigateComm = ZigateComm        # Point to the ZigateComm object
        self.pluginconf = PluginConf
        self.homeDirectory = HomeDirectory
        self.OTA = {} # Store Firmware infos
        self.OTA['Filename'] = {}
        self.OTA['Images'] = {}
        self.OTA['Upgraded Device'] = {}
        self.logMessageDone = 0
        self.batteryTypeFirmware = []
        self.availableManufCode = []
        self.upgradableDev = None
        self.TypeInProgress = None
        self.upgradeInProgress = None
        self.upgradeOTAImage = None
        self.upgradeDone = None
        self.upgradeOTAImageType = None        
        self.stopOTA = None
        self.loggingFileHandle = loggingFileHandle
        self.PluginHealth = PluginHealth

        self.ota_scan_folder()

    def _loggingStatus( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Status( message )
        else:
            if self.loggingFileHandle:
                Domoticz.Status( message )
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
            else:
                Domoticz.Status( message )

    def _loggingLog( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Log( message )
        else:
            if self.loggingFileHandle:
                Domoticz.Log( message )
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
            else:
                Domoticz.Log( message )

    def _loggingDebug( self, message):

        if self.pluginconf.pluginConf['useDomoticzLog']:
            Domoticz.Log( message )
        else:
            if self.loggingFileHandle:
                message =  str(datetime.now().strftime('%b %d %H:%M:%S.%f')) + " " + message + '\n'
                self.loggingFileHandle.write( message )
                self.loggingFileHandle.flush()
            else:
                Domoticz.Log( message )

    def logging( self, logType, message):

        self.debugOTA = self.pluginconf.pluginConf['debugOTA']
        if logType == 'Debug' and self.debugOTA:
            self._loggingDebug( message)
        elif logType == 'Log':
            self._loggingLog( message )
        elif logType == 'Status':
            self._loggingStatus( message)
        return

    # Low level commands/messages
    def ota_decode_new_image( self, subfolder, image ):
        'LOAD_NEW_IMAGE 	0x0500 	Load headers to ZiGate. Use this command first.'
        
        try:
            with open( self.pluginconf.pluginConf['pluginOTAFirmware'] + subfolder + '/' + image, 'rb') as file:
                ota_image = file.read()

        except OSError as err:
            Domoticz.Error("ota_decode_new_image - error when opening %s - %s" %(image, err))
            return False

        if len(ota_image) < 69:
            Domoticz.Error("ota_decode_new_image - invalid file size read %s - %s" %(image,len(ota_image)))
            return False

        #Search for the OTA Upgrade File Identifier (  “0x0BEEF11E” )
        offset = None
        for i in range(len(ota_image)-4):
            if hex(struct.unpack('<I',ota_image[0+i:4+i])[0]) == '0xbeef11e':
                offset = i
                break

        self.logging( 'Debug', "ota_decode_new_image - offset:%s ..." %offset)
        ota_image = ota_image[offset:]

        try:
            header_data = list(struct.unpack('<LHHHHHLH32BLBQHH', ota_image[:69]))
        except struct.error:
            Domoticz.Error("ota_decode_new_image - Error when unpacking: %s" %ota_image[:69])
            return False

        for i in range(8, 40):
            if header_data[i] == 0x00:
                header_data[i] = 0x20

        self.logging( 'Debug', "ota_decode_new_image - header_data: %s" %str(header_data))
        header_data_compact = header_data[0:8] + [header_data[8:40]] + header_data[40:]
        header_headers = [ 'file_id', 'header_version', 'header_length', 'header_fctl', 
                'manufacturer_code', 'image_type', 'image_version', 
                'stack_version', 'header_str', 'size', 'security_cred_version', 'upgrade_file_dest',
                'min_hw_version', 'max_hw_version' ]
        headers = dict(zip(header_headers, header_data_compact))

        for attribut in headers:
            if attribut in ( 'stack_version', 'security_cred_version', 'image_version'):
                continue
            if isinstance(headers[attribut], int):
                self.logging( 'Debug', "==> %s : 0x%x" %(attribut,headers[attribut]))
            else:
                self.logging( 'Debug', "==> %s : %s" %(attribut,headers[attribut]))

        # Decoding File Version
        self.logging( 'Debug', "==> File Version: 0x%08X" %headers['image_version'])
        self.logging( 'Debug', "==>    Application Release: 0x%02x" % ( (headers['image_version'] & 0xff000000) >> 24))
        self.logging( 'Debug', "==>    Application Build: %s" %( (headers['image_version'] & 0x00ff0000) >> 16))
        self.logging( 'Debug', "==>    Stack Release: %s" %( (headers['image_version'] & 0x0000ff00) >> 8))
        self.logging( 'Debug', "==>    Stack Build: %s" %( (headers['image_version'] & 0x000000ff)))

        # Stack version
        if headers['stack_version'] == 0x0000:
            self.logging( 'Debug', "==> Stack Name: ZigBee 2006")
        elif headers['stack_version'] == 0x0001:
            self.logging( 'Debug', "==> Stack Name: ZigBee 2007")
        elif headers['stack_version'] == 0x0002:
            self.logging( 'Debug', "==> Stack Name: ZigBee Pro")
        elif headers['stack_version'] == 0x0003:
            self.logging( 'Debug', "==> Stack Name: ZigBee IP")
        else:
            self.logging( 'Debug', "==> Stack Name: Reserved")

        # Security Credential
        if headers['security_cred_version'] == 0x00:
            self.logging( 'Debug', "==> Security Credential: SE 1.0")
        elif headers['security_cred_version'] == 0x01:
            self.logging( 'Debug', "==> Security Credential: SE 1.1")
        elif headers['security_cred_version'] == 0x02:
            self.logging( 'Debug', "==> Security Credential: SE 2.0")
        else:
            self.logging( 'Debug', "==> Security Credential: Reserved")

        if headers['image_type'] in self.OTA['Images']:
            # Check if we have a better Version
            _imported_header = self.OTA['Images'][headers['image_type']]['Decoded Header']

            if headers['image_version'] <= _imported_header['image_version']:
                Domoticz.Log("ota_decode_new_image - Image %s already imported. Type: %s with better version %x versus %x" \
                        %(image, headers['image_type'], headers['image_version'], _imported_header['image_version']))
                return False
            # We will overwrite the new loaded image as it is more recent

        self.logging( 'Status', "Available Firmware - ManufCode: %4X ImageType: 0x%04X FileVersion: %8X Size: %8s Bytes Filename: %s" \
                %(headers['manufacturer_code'], headers['image_type'],  headers['image_version'], headers['size'], image ))
        for x in header_headers:
            if x == 'header_str':
                self.logging( 'Debug', "ota_decode_new_image - %21s : %s " %(x,str(struct.pack('B'*32,*headers[x]))))
            else:
                self.logging( 'Debug', "ota_decode_new_image - %21s : 0x%X " %(x,headers[x]))

        if self.pluginconf.pluginConf['forceOTAUpgrade']:
            forceVersion = headers['image_version'] + self.pluginconf.pluginConf['forceOTAMask']
            self.logging( 'Log', "----> Forcing update for Image: 0x%s from Version: 0x%08X to Version: 0x%08X" 
                %( image, headers['image_version'], forceVersion))
            headers['image_version'] = forceVersion

        key = headers['image_type']
        self.OTA['Images'][key] = {}
        self.OTA['Images'][key]['Filename'] = image
        self.OTA['Images'][key]['Decoded Header'] = headers
        self.OTA['Images'][key]['image'] = ota_image
        if self.OTA['Images'][key]['Decoded Header']['manufacturer_code'] not in self.availableManufCode:
            self.availableManufCode.append( self.OTA['Images'][key]['Decoded Header']['manufacturer_code'])

        self.OTA['Filename'][key] = {}
        self.OTA['Filename'][key]['subfolder'] = subfolder
        self.OTA['Filename'][key]['image'] = image
        subfolder, image

        if key in BATTERY_TYPES:    # In such case let's pile it so we will expsoe it a while after the powered Devices Type.
            self.logging( 'Debug', "ota_decode_new_image - Firmware for battery type detected - %s %s" %(key, image))
            self.batteryTypeFirmware.append( key )

        return key

    def ota_load_new_image( self, key):
        " Send the image headers to Zigate."

        if key not in self.OTA['Images']:
            self.logging( 'Debug', "ota_load_new_image - Unknown Image %s in %s" %(key, str(self.OTA['Images']).keys() ))
            return

        file_id = '%08X' %self.OTA['Images'][key]['Decoded Header']['file_id']
        header_version = '%04X' %self.OTA['Images'][key]['Decoded Header']['header_version']
        header_length = '%04X' %self.OTA['Images'][key]['Decoded Header']['header_length']
        header_fctl = '%04X' %self.OTA['Images'][key]['Decoded Header']['header_fctl']
        manufacturer_code =  '%04X' %self.OTA['Images'][key]['Decoded Header']['manufacturer_code']
        image_type = '%04X' %self.OTA['Images'][key]['Decoded Header']['image_type']
        image_version = '%08X' %self.OTA['Images'][key]['Decoded Header']['image_version']
        stack_version = '%04X' %self.OTA['Images'][key]['Decoded Header']['stack_version']
        header_str = ''
        for i in self.OTA['Images'][key]['Decoded Header']['header_str']:
            header_str += '%02X' %i

        size = '%08X' %self.OTA['Images'][key]['Decoded Header']['size']
        security_cred_version = '%02X' %self.OTA['Images'][key]['Decoded Header']['security_cred_version']
        upgrade_file_dest = '%016X' %self.OTA['Images'][key]['Decoded Header']['upgrade_file_dest']
        min_hw_version = '%04X' %self.OTA['Images'][key]['Decoded Header']['min_hw_version']
        max_hw_version = '%04X' %self.OTA['Images'][key]['Decoded Header']['max_hw_version']
        
        datas = "%02x" %ADDRESS_MODE['short'] + "0000"
        datas += file_id + header_version + header_length + header_fctl 
        datas += manufacturer_code + image_type + image_version 
        datas += stack_version + header_str + size 
        datas += security_cred_version + upgrade_file_dest + min_hw_version + max_hw_version

        self.logging( 'Debug', "ota_load_new_image: - len:%s datas: %s" %(len(datas),datas))
        self.ZigateComm.sendData( "0500", datas)
        return

    def notify_device( self, MsgManufCode, MsgImageType, MsgImageVersion, MsgSrcAddr, MsgEpOut=None ):

        """
        Purpose is to notifiy a specifc device.
        """
        self.logging( 'Log', "notify_device: Manuf: 0x%x Type: 0x%04x Version: 0x%08x Nwkid: %s EPOut: %s" %(MsgManufCode, MsgImageType, MsgImageVersion, MsgSrcAddr, MsgEpOut))

        if MsgImageType not in self.OTA['Images']:
            self.logging( 'Log', "notify_device: 0x%x Image Type not found in %s" %(MsgImageType, str(self.OTA['Images'].keys())))
            return

        self.OTA['Upgraded Device'][MsgSrcAddr] = {}

        self.upgradeInProgress = MsgSrcAddr
        if MsgEpOut is None:
            MsgEpOut = "01"
            if 'Ep' in self.ListOfDevices[self.upgradeInProgress]:
                for x in self.ListOfDevices[self.upgradeInProgress]['Ep']:
                    if OTA_CLUSTER_ID in self.ListOfDevices[self.upgradeInProgress]['Ep'][x]:
                        MsgEpOut = x
                        break
        self.ota_image_advertize(self.upgradeInProgress, MsgEpOut, \
                                self.OTA['Images'][MsgImageType]['Decoded Header']['image_version'], \
                                self.OTA['Images'][MsgImageType]['Decoded Header']['image_type'], \
                                self.OTA['Images'][MsgImageType]['Decoded Header']['manufacturer_code'])


    def async_request( self, MsgSrcAddr, MsgIEEE, MsgFileOffset, MsgImageVersion, MsgImageType, MsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, MsgFieldControl):

        """
        Purpose is to handle an Async request (most-likely Legrand), when there is nothing to do
        """

        if self.upgradeInProgress:
            self.logging( 'Debug', "async_request: There is an upgrade in progress, drop request from %s" %(MsgSrcAddr))
            return

        # Import the image is not loaded anymore
        if MsgImageType not in self.OTA['Images']:
            if MsgImageType in self.OTA['Filename']:
                self.ota_decode_new_image( self.OTA['Filename'][MsgImageType]['subfolder'], self.OTA['Filename'][MsgImageType]['image'])
            else:
                Domoticz.Log("async_request - %s request Type: %s (%s) not found in 'Filename': %s" \
                        %(MsgSrcAddr, MsgImageType, type(MsgImageType), str(self.OTA['Filename'].keys())))
                return
        else:
            Domoticz.Log("async_request - %s request Type: %s (%s) not found in 'Images': %s" \
                    %(MsgSrcAddr, MsgImageType, type(MsgImageType), str(self.OTA['Images'].keys())))
            return

        self.logging( 'Debug', "OTA heartbeat - Image: 0x%04X from file: %s" %(MsgImageType, self.OTA['Images'][MsgImageType]['Filename']))

        # Loading Image in Zigate
        self.ota_load_new_image( MsgImageType )
        self.upgradeOTAImage = MsgImageType
        Domoticz.Log("--self.upgradeOTAImage = %s" %self.upgradeOTAImage)
        self.upgradeOTAImageType = MsgImageType
        self.notify_device( MsgManufCode, MsgImageType, MsgImageVersion, MsgSrcAddr)


    def ota_request_firmware( self , MsgData):
        'BLOCK_REQUEST 	0x8501 	ZiGate will receive this command when device asks OTA firmware'

        self.logging( 'Debug', "Decode8501 - Request Firmware Block (%s) %s" %(len(MsgData), MsgData))

        MsgSQN = MsgData[0:2]
        MsgEP = MsgData[2:4]
        MsgClusterId = MsgData[4:8]
        MsgaddrMode = MsgData[8:10]
        MsgSrcAddr = MsgData[10:14]
        MsgIEEE = MsgData[14:30]
        MsgFileOffset = MsgData[30:38]
        MsgImageVersion = int(MsgData[38:46],16)
        MsgImageType = int(MsgData[46:50],16)
        MsgManufCode = int(MsgData[50:54],16)
        MsgBlockRequestDelay = MsgData[54:58]
        MsgMaxDataSize = MsgData[58:60]
        MsgFieldControl = int(MsgData[60:62],16)

        if self.upgradeInProgress != MsgSrcAddr:
            self.logging( 'Debug', "Unexpected request from device: %s, we are currently looking to serve device: %s" %(MsgSrcAddr, self.upgradeInProgress))
            self.async_request( MsgSrcAddr, MsgIEEE, MsgFileOffset, MsgImageVersion, MsgImageType, MsgManufCode, MsgBlockRequestDelay, MsgMaxDataSize, MsgFieldControl)
            return

        self.logging( 'Debug', "Decode8501 - [%3s] OTA image Block request - %s/%s Offset: %s version: 0x%08X Type: 0%04X Code: 0x%04X Delay: %s MaxSize: %s Control: 0x%02X"
            %(int(MsgSQN,16), MsgSrcAddr, MsgEP, int(MsgFileOffset,16), MsgImageVersion, MsgImageType, MsgManufCode, int(MsgBlockRequestDelay,16), int(MsgMaxDataSize,16), MsgFieldControl))
        
        # Patching in order to make Legrand update with Image Page Request working
        if MsgManufCode == 0x00C8 and self.TypeInProgress:
            # Request a Page , and Note a Block
            # For the time been , we are forcing a response with a Block
            MsgImageType = self.TypeInProgress
            MsgManufCode = 0x1021
            MsgBlockRequestDelay = 'ffff'
            MsgMaxDataSize = '40'
            MsgFieldControl = 0x00
            self.logging( 'Debug', "  Fixing   - [%3s] OTA image Block request - %s/%s Offset: %s version: 0x%08X Type: 0%04X Code: 0x%04X Delay: %s MaxSize: %s Control: 0x%02X"
                %(int(MsgSQN,16), MsgSrcAddr, MsgEP, int(MsgFileOffset,16), MsgImageVersion, MsgImageType, MsgManufCode, int(MsgBlockRequestDelay,16), int(MsgMaxDataSize,16), MsgFieldControl))

        block_request = {}
        block_request['ReqAddr'] = MsgSrcAddr
        block_request['ReqEp'] = MsgEP
        block_request['Offset'] = MsgFileOffset
        block_request['ImageVersion'] = MsgImageVersion
        block_request['ImageType'] = MsgImageType
        block_request['ManufCode'] = MsgManufCode
        block_request['BlockReqDelay'] = MsgBlockRequestDelay
        block_request['MaxDataSize'] = MsgMaxDataSize
        block_request['FieldControl'] = MsgFieldControl
        block_request['Sequence'] = MsgSQN

        if MsgSrcAddr not in self.OTA['Upgraded Device']:
            Domoticz.Error("OTA image Block request - Not in upgrade mode ...")
            return

        _size = self.OTA['Images'][MsgImageType]['Decoded Header']['size']
        _completion = round( ((int(MsgFileOffset,16) / _size ) * 100), 1 )
        if (_completion % 5) == 0:
            self.logging( 'Log', "Firmware transfert for %s/%s - Progress: %4s %%" %(MsgSrcAddr, MsgEP, _completion))
            if 'Firmware Update' not in self.PluginHealth:
                self.PluginHealth['Firmware Update'] = {}
            if self.PluginHealth['Firmware Update'] is None:
                self.PluginHealth['Firmware Update'] = {}
            self.PluginHealth['Firmware Update']['Progress'] = '%s %%' %round(_completion)
            self.PluginHealth['Firmware Update']['Device'] = MsgSrcAddr

        self.OTA['Upgraded Device'][MsgSrcAddr]['Status'] = 'Block Requested'

        self.logging( 'Debug', "                   Block Request for %s/%s Image Type: 0x%04X Image Version: %08X Seq: %s Offset: %s Size: %s FieldCtrl: 0x%02X" \
            %(MsgSrcAddr, block_request['ReqEp'], block_request['ImageType'], \
            block_request['ImageVersion'], MsgSQN, (block_request['Offset'],16), 
               int(block_request['MaxDataSize'],16), block_request['FieldControl']))

        if 'Start Time' not in self.OTA['Upgraded Device'][MsgSrcAddr]:
            # Starting Process
            self.upgradeDone = True
            if 'Firmware Update' in self.PluginHealth:
                self.PluginHealth['Firmware Update'] = {}
            if 'Firmware Update' not in self.PluginHealth:
                self.PluginHealth['Firmware Update'] = {}
            if self.PluginHealth['Firmware Update'] is None:
                self.PluginHealth['Firmware Update'] = {}
            self.PluginHealth['Firmware Update']['Progress'] = '0%'
            self.PluginHealth['Firmware Update']['Device'] = MsgSrcAddr

            self.logging( 'Status', "Starting firmware process on %s/%s" %(MsgSrcAddr, MsgEP))
            self.OTA['Upgraded Device'][MsgSrcAddr]['Start Time'] = time()

            _ieee = self.ListOfDevices[MsgSrcAddr]['IEEE']
            _name = None
            for x in self.Devices:
                if self.Devices[x].DeviceID == _ieee:
                    _name = self.Devices[x].Name

            #self. ota_management( MsgSrcAddr, MsgEP )
            _durhh, _durmm, _durss = convertTime( self.OTA['Images'][MsgImageType]['Decoded Header']['size'] // int(MsgMaxDataSize,16) )
            _textmsg = 'Firmware update started for Device: %s with %s - Estimated Time: %s H %s min %s sec ' \
                %(_name, self.OTA['Images'][MsgImageType]['Filename'], _durhh, _durmm, _durss)
            self.adminWidgets.updateNotificationWidget( self.Devices, _textmsg)
            return

        self.OTA['Upgraded Device'][MsgSrcAddr]['Last Block sent'] = int(time())
        self.ota_block_send( MsgSrcAddr, MsgEP, MsgImageType, block_request )
        return

    def ota_block_send( self , dest_addr, dest_ep, image, block_request):
        'BLOCK_SEND 	0x0502 	This is used to transfer firmware BLOCKS to device when it sends request 0x8501.'

        self.logging( 'Debug', "ota_block_send - Addr: %s/%s Type: 0x%X" %(dest_addr, dest_ep, image))
        if image not in self.OTA['Images']:
            Domoticz.Error("ota_block_send - unknown image %s" %image)
            return
        if dest_addr not in self.OTA['Upgraded Device']:
            Domoticz.Error("ota_block_send - unexpected call - lack of initialization")
            return
        if block_request['ImageVersion'] != self.OTA['Images'][image]['Decoded Header']['image_version']:
            Domoticz.Error("ota_block_send - Image version missmatch %s versus %s" \
                    %(block_request['ImageVersion'], self.OTA['Images'][image]['Decoded Header']['image_version']))
            if dest_addr in self.OTA['Upgraded Device']:
                self.OTA['Upgraded Device'][dest_addr]['Status'] = 'Transfer Aborted'
            return
        if block_request['ImageType'] != self.OTA['Images'][image]['Decoded Header']['image_type']:
            Domoticz.Error("ota_block_send - Image type missmatch %s versus %s" \
                    %(block_request['ImageType'], self.OTA['Images'][image]['Decoded Header']['image_type']))
            if dest_addr in self.OTA['Upgraded Device']:
                self.OTA['Upgraded Device'][dest_addr]['Status'] = 'Transfer Aborted'
            return
        if block_request['ManufCode'] != self.OTA['Images'][image]['Decoded Header']['manufacturer_code']:
            Domoticz.Error("ota_block_send - Manuf Code missmatch %s versus %s" \
                    %(block_request['ManufCode'], self.OTA['Images'][image]['Decoded Header']['manufacturer_code']))
            if dest_addr in self.OTA['Upgraded Device']:
                self.OTA['Upgraded Device'][dest_addr]['Status'] = 'Transfer Aborted'
            return

        self.TypeInProgress = image

        manufacturer_code =  '%04x' %self.OTA['Images'][image]['Decoded Header']['manufacturer_code']
        image_type = '%04x' %self.OTA['Images'][image]['Decoded Header']['image_type']
        image_version = '%08x' %self.OTA['Images'][image]['Decoded Header']['image_version']

        sequence = int(block_request['Sequence'],16)
        
        """
        Indicates whether a data block is included in the response:
            OTA_STATUS_SUCCESS: ( 0x00)  A data block is included
            OTA_STATUS_WAIT_FOR_DATA (0x97) : No data block is included - client should re-request a data block after a waiting time
        """
        _status = 0x00

        # Build the data block to be send based on the request
        _offset = int(block_request['Offset'],16)
        _lenght = int(block_request['MaxDataSize'],16)
        _raw_ota_data = self.OTA['Images'][image]['image'][_offset:_offset+_lenght]

        # Build the message and send
        datas = "%02x" %ADDRESS_MODE['short'] + dest_addr + ZIGATE_EP + dest_ep 
        datas += "%02x" %sequence + "%02x" %_status 
        datas += "%08x" %_offset 
        datas += image_version + image_type + manufacturer_code
        datas += "%02x" %_lenght
        for i in _raw_ota_data:
            datas += "%02x" %i

        self.ZigateComm.sendData( "0502", datas)
        self.OTA['Upgraded Device'][dest_addr]['Status'] = 'Transfer Progress'
        self.OTA['Upgraded Device'][dest_addr]['received'] = _offset
        self.OTA['Upgraded Device'][dest_addr]['sent'] = _offset + _lenght

        # This is to Hack a Firmware issue on Legrand which is requesting Page update and not Block
        self.logging( 'Debug', "ota_block_send - Block sent to %s/%s Received yet: %s Sent now: %s" 
                %( dest_addr, dest_ep, _offset, _lenght))
        return 

    def ota_upgrade_end_response( self, dest_addr, dest_ep, MsgImageVersion, MsgImageType, MsgManufCode ):
        """
        This function issues an Upgrade End Response to a client to which the server has been
        downloading an application image. The function is called after receiving an Upgrade 
        End Request from the client, indicating that the client has received the entire 
        application image and verified it
        """
        'UPGRADE_END_RESPONSE 	0x0504'

        # u32UpgradeTime is the UTC time, in seconds, at which the client should upgrade the running image with the downloaded image
        _UpgradeTime = 0x00 

        # u32CurrentTime is the current UTC time, in seconds, on the server.
        EPOCTime = datetime(2000,1,1)
        UTCTime = int((datetime.now() - EPOCTime).total_seconds())

        _FileVersion = MsgImageVersion
        _ImageType = MsgImageType
        _ManufacturerCode = MsgManufCode

        datas = "%02x" %ADDRESS_MODE['short'] + dest_addr + ZIGATE_EP + dest_ep 
        datas += "%08x" %_UpgradeTime
        datas += "%08x" %0x00
        datas += "%08x" %_FileVersion
        datas += "%04x" %_ImageType
        datas += "%04x" %_ManufacturerCode

        self.logging( 'Log', "ota_management - sending Upgrade End Response, for %s Version: 0x%08X Type: 0x%04x, Manuf: 0x%04X" %( dest_addr, _FileVersion, _ImageType, _ManufacturerCode))

        self.ZigateComm.sendData( "0504", datas)

        if 'OTA' not in self.ListOfDevices[ dest_addr ]:
            self.ListOfDevices[ dest_addr ]['OTA'] = {}
        if not isinstance(  self.ListOfDevices[ dest_addr ]['OTA'], dict):
            del  self.ListOfDevices[ dest_addr ]['OTA']
            self.ListOfDevices[ dest_addr ]['OTA'] = {}

        now = int(time())
        self.ListOfDevices[ dest_addr ]['OTA'][ now ] = {}
        self.ListOfDevices[ dest_addr ]['OTA'][ now ]['Time'] = datetime.fromtimestamp(time()).strftime('%Y-%m-%d %H:%M:%S')
        self.ListOfDevices[ dest_addr ]['OTA'][ now ]['Version'] =  '%08X' %_FileVersion
        self.ListOfDevices[ dest_addr ]['OTA'][ now ]['Type'] =  '%04X' %_ImageType

        return

    def ota_image_advertize(self, dest_addr, dest_ep, image_version = 0xFFFFFFFF, image_type = 0xFFFF, manufacturer_code = 0xFFFF, Flag_=False ):
        'IMAGE_NOTIFY 	0x0505 	Notify desired device that ota is available. After loading headers use this.'

        """
        The 'query jitter' mechanism can be used to prevent a flood of replies to an Image Notify broadcast
        or multicast (Step 2 above). The server includes a number, n, in the range 1-100 in the notification. 
        If interested in the image, the receiving client generates a random number in the range 1-100. 
        If this number is greater than n, the client discards the notification, otherwise it responds with 
        a Query Next Image Request. This results in only a fraction of interested clients res
        """
        JITTER_OPTION = 100

        """
        teOTA_ImageNotifyPayloadType
          - 0 : E_CLD_OTA_QUERY_JITTER Include only ‘Query Jitter’ in payload
          - 1 : E_CLD_OTA_MANUFACTURER_ID_AND_JITTER Include ‘Manufacturer Code’ and ‘Query Jitter’ in payload
          - 2 : E_CLD_OTA_ITYPE_MDID_JITTER Include ‘Image Type’, ‘Manufacturer Code’ and ‘Query Jit- ter’ in payload
          - 3 : E_CLD_OTA_ITYPE_MDID_FVERSION_JITTER Include ‘Image Type’, ‘Manufacturer Code’, ‘File Version’ and ‘Query Jitter’ in payload
        """
        IMG_NTFY_PAYLOAD_TYPE = 3

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
        datas += '%08X' %image_version + '%04X' %image_type + '%04X' %manufacturer_code 
        datas += "%02x" %JITTER_OPTION
        self.logging( 'Debug', "ota_image_advertize - Type: 0x%0X, Version: 0x%0X => datas: %s" %(image_type, image_version, datas))

        if not Flag_:
            self.OTA['Upgraded Device'][dest_addr] = {}
            self.OTA['Upgraded Device'][dest_addr][image_type] = {}
            self.OTA['Upgraded Device'][dest_addr]['Status'] = 'Notified'
            self.OTA['Upgraded Device'][dest_addr]['Notified Time'] = int(time())

        self.ZigateComm.sendData( "0505", datas)
        return

    def ota_management( self, MsgSrcAddr, MsgEP ):
        'SEND_WAIT_FOR_DATA_PARAMS 	0x0506 	Can be used to delay/pause OTA update'

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
        _BlockRequestDelayMs = 500

        datas = "%02x" %ADDRESS_MODE['short'] + MsgSrcAddr + ZIGATE_EP + MsgEP 
        datas += "%02X" %_status
        datas += "%08X" %_CurrentTime
        datas += "%08X" %_RequestTime
        datas += "%04X" %_BlockRequestDelayMs

        self.logging( 'Debug', "ota_management - Reduce Block request to a rate of %s ms" %_BlockRequestDelayMs)
        self.ZigateComm.sendData( "0506", datas)

        return 

    def ota_request_firmware_completed( self , MsgData):
        'UPGRADE_END_REQUEST 	0x8503 	Device will send this when it has received last part of firmware'

        self.logging( 'Debug', "Decode8503 - Request Firmware Block %s/%s" %(MsgData, len(MsgData)))
        MsgSQN = MsgData[0:2]
        MsgEP = MsgData[2:4]
        MsgClusterId = MsgData[4:8]
        MsgaddrMode = MsgData[8:10]
        MsgSrcAddr = MsgData[10:14]
        MsgImageVersion = int(MsgData[14:22],16)
        MsgImageType = int(MsgData[22:26],16)
        MsgManufCode = int(MsgData[26:30],16)
        MsgStatus = MsgData[30:32]

        if self.upgradeInProgress is None:
            self.logging( 'Debug', "ota_request_firmware_completed - Receive Firmware Completed from %s most likely a duplicated packet as there is nothing in Progress. %s" %(MsgSrcAddr, self.upgradeInProgress))
            return
            
        Domoticz.Log("Decode8503 - OTA upgrade completed - %s/%s %s Version: 0x%08x Type: 0x%04x Code: 0x%04x Status: %s"
            %(MsgSrcAddr, MsgEP, MsgClusterId, MsgImageVersion, MsgImageType, MsgManufCode, MsgStatus))

        if MsgSrcAddr not in self.OTA['Upgraded Device']:
            Domoticz.Error("Decode8503 - OTA upgrade completed - %s not in Upgraded devices" %MsgSrcAddr)
            return

        if 'Start Time' not in self.OTA['Upgraded Device'][MsgSrcAddr]:
            Domoticz.Error("Decode8503 - OTA upgrade completed - No Start Time for device: %s" %MsgSrcAddr)
            return

        _transferTime_hh, _transferTime_mm, _transferTime_ss = convertTime( int(time() - self.OTA['Upgraded Device'][MsgSrcAddr]['Start Time']))

        _ieee = self.ListOfDevices[MsgSrcAddr]['IEEE']
        _name = None
        for x in self.Devices:
            if self.Devices[x].DeviceID == _ieee:
                _name = self.Devices[x].Name

        #define OTA_STATUS_SUCCESS                        (uint8)0x00
        #define OTA_STATUS_ABORT                          (uint8)0x95
        #define OTA_STATUS_NOT_AUTHORISED                 (uint8)0x7E
        #define OTA_STATUS_IMAGE_INVALID                  (uint8)0x96
        #define OTA_STATUS_WAIT_FOR_DATA                  (uint8)0x97
        #define OTA_STATUS_NO_IMAGE_AVAILABLE             (uint8)0x98
        #define OTA_MALFORMED_COMMAND                     (uint8)0x80
        #define OTA_UNSUP_CLUSTER_COMMAND                 (uint8)0x81
        #define OTA_REQUIRE_MORE_IMAGE                    (uint8)0x99

        if MsgStatus == '00': # OTA_STATUS_SUCCESS
            if 'Firmware Update' in self.PluginHealth:
                if len(self.PluginHealth['Firmware Update']) > 0:
                    self.PluginHealth['Firmware Update']['Progress'] = 'Success'

            self.logging( 'Status', "ota_request_firmware_completed - OTA Firmware upload completed with success")
            self.OTA['Upgraded Device'][MsgSrcAddr]['Status'] = 'Transfer Completed'
            self.ota_upgrade_end_response( MsgSrcAddr, MsgEP,MsgImageVersion, MsgImageType, MsgManufCode )
            _textmsg = 'Device: %s has been updated with firmware %s in %s hour %s min %s sec' \
                    %(_name, MsgImageVersion, _transferTime_hh, _transferTime_mm, _transferTime_ss)
            self.logging( 'Status', _textmsg )
            self.upgradeInProgress = None

        elif MsgStatus == '95': # OTA_STATUS_ABORT The image download that is currently in progress should be cancelled
            if 'Firmware Update' in self.PluginHealth:
                if len(self.PluginHealth['Firmware Update']) > 0:
                    self.PluginHealth['Firmware Update']['Progress'] = 'Aborted'
            Domoticz.Error("ota_request_firmware_completed - OTA Firmware aborted")
            self.OTA['Upgraded Device'][MsgSrcAddr]['Status'] = 'Transfer Aborted'
            _textmsg = 'Firmware update aborted error code %s for Device %s in %s hour %s min %s sec' \
                    %(MsgStatus, _name, _transferTime_hh, _transferTime_mm, _transferTime_ss)

        elif MsgStatus == '96': # OTA_STATUS_INVALID_IMAGE: The downloaded image failed the verification
                                # checks and will be discarded
            if 'Firmware Update' in self.PluginHealth:
                if len(self.PluginHealth['Firmware Update']) > 0:
                    self.PluginHealth['Firmware Update']['Progress'] = 'Failed'
            Domoticz.Error("ota_request_firmware_completed - OTA Firmware image validation failed")
            self.OTA['Upgraded Device'][MsgSrcAddr]['Status'] = 'Transfer Aborted'
            _textmsg = 'Firmware update aborted error code %s for Device %s in %s hour %s min %s sec' \
                    %(MsgStatus, _name, _transferTime_hh, _transferTime_mm, _transferTime_ss)

        elif MsgStatus == '99': # OTA_REQUIRE_MORE_IMAGE: The downloaded image was successfully received 
                                # and verified, but the client requires multiple images before performing an upgrade
            self.logging( 'Status', "ota_request_firmware_completed - OTA Firmware  The downloaded image was successfully received, but there is a need for additional image")
            if 'Firmware Update' in self.PluginHealth:
                if len(self.PluginHealth['Firmware Update']) > 0:
                    self.PluginHealth['Firmware Update']['Progress'] = 'More'
            self.OTA['Upgraded Device'][MsgSrcAddr]['Status'] = 'Transfer Completed'
            _textmsg = 'Device: %s has been updated to latest firmware in %s hour %s min %s sec, but additional Image needed' \
                    %(MsgStatus, _name, _transferTime_hh, _transferTime_mm, _transferTime_ss)

        else:
            Domoticz.Error("ota_request_firmware_completed - OTA Firmware unexpected error %s" %MsgStatus)
            if 'Firmware Update' in self.PluginHealth:
                if len(self.PluginHealth['Firmware Update']) > 0:
                    self.PluginHealth['Firmware Update']['Progress'] = 'Aborted'
            self.OTA['Upgraded Device'][MsgSrcAddr]['Status'] = 'Transfer Aborted'
            _textmsg = 'Firmware update aborted error code %s for Device %s in %s hour %s min %s sec' \
                    %(MsgStatus, _name, _transferTime_hh, _transferTime_mm, _transferTime_ss)

        self.adminWidgets.updateNotificationWidget( self.Devices, _textmsg)
        return

    def ota_scan_folder( self):
        """
        Scanning the Firmware folder and processing them
        """

        for brand in ('IKEA-TRADFRI', 'LEDVANCE', 'LEGRAND' , 'PHILIPS'):
            ota_dir = self.pluginconf.pluginConf['pluginOTAFirmware'] + brand
            ota_image_files = [ f for f in listdir(ota_dir) if isfile(join(ota_dir, f))]

            for ota_image_file in ota_image_files:
                if ota_image_file in ( 'README.md', 'README.txt', '.PRECIOUS' ):
                    continue
                key = self.ota_decode_new_image( brand, ota_image_file )

    def heartbeat( self ):
        """ call by plugin onHeartbeat """


        if self.stopOTA:
            return

        self.HB += 1


        if self.HB < ( self.pluginconf.pluginConf['waitingOTA'] // HEARTBEAT): 
            return

        if  len(self.ZigateComm.zigateSendingFIFO) > MAX_LOAD_ZIGATE:
            self.logging( 'Debug', "heartbeat - normalQueue: %s : %s" %( len(self.ZigateComm.zigateSendingFIFO), str(self.ZigateComm.zigateSendingFIFO)))
            self.logging( 'Debug', "            Too busy, will come back later")
            return

        if 'Images' in self.OTA:
            if len(self.OTA['Images']) == 0 and \
                    self.upgradeInProgress is None and \
                    self.upgradableDev is None and \
                    self.upgradeOTAImage is None:
                # Nothing to do, let's wait OTA_Cycle to restart
                if ( self.HB % ( OTA_CYLCLE // HEARTBEAT) ) == 0: # Every 6 hours
                    self.ota_scan_folder()
                return

            if self.OTA['Images'] is None :
                _lenOTA = '?'
            else:
                _lenOTA =len(self.OTA['Images'])

        if self.upgradableDev is None:
            _lenUpgrade = '?'
        else:
            _lenUpgrade = len(self.upgradableDev)
                
        #Domoticz.Log("OTA heartbeat - HB: %s, upgradeInProgress: %s, upgradableDev: %s, _lenUpgrade: %s, upgradeOTAImage: %s, _lenOTA: %s "\
        #    %( self.HB, self.upgradeInProgress, self.upgradableDev, _lenUpgrade, self.upgradeOTAImage, _lenOTA))

        if self.upgradeInProgress:
            if self.upgradeInProgress in self.OTA['Upgraded Device']:
                if  self.OTA['Upgraded Device'][self.upgradeInProgress]['Status'] not in ( 'Block Requested', 'Transfer Progress' ):
                    if self.logMessageDone != 1:
                        if self.upgradeOTAImage:
                            Domoticz.Log("OTA heartbeat - [%s] Type:   0x%04X, %3s remaining Images, Device: %s, %3s remaining devices" \
                                %(self.HB, self.upgradeOTAImage, _lenOTA, self.upgradeInProgress, _lenUpgrade))
                        else:
                            Domoticz.Log("OTA heartbeat - [%s] Type: %6s, %3s remaining Images, Device: %s, %3s remaining devices" \
                                %(self.HB, self.upgradeOTAImage, _lenOTA, self.upgradeInProgress, _lenUpgrade))

                        self.logMessageDone = 1
            else:
                if self.logMessageDone != 2:
                    Domoticz.Log("OTA heartbeat - [%s] Type:   0x%04X, %3s remaining Images, Device: %s, %3s remaining devices, upgradeInProgress: %4s" \
                        %(self.HB, self.upgradeOTAImage, _lenOTA, self.upgradeInProgress, _lenUpgrade, self.upgradeInProgress))
                    self.logMessageDone = 2
        else:
            # Looks like we have completed one firmware update.
            if self.logMessageDone != 3:
                if self.upgradeOTAImage:
                    Domoticz.Log("OTA heartbeat - [%s] Type:   0x%04X, %3s remaining Images, Device: %s, %3s remaining devices, upgradeInProgress: %4s" \
                        %(self.HB, self.upgradeOTAImage, _lenOTA, self.upgradeInProgress, _lenUpgrade, self.upgradeInProgress))
                else:
                    Domoticz.Log("OTA heartbeat - [%s] Type: 0x%6s, %3s remaining Images, Device: %s, %3s remaining devices, upgradeInProgress: %4s" \
                        %(self.HB, self.upgradeOTAImage, _lenOTA, self.upgradeInProgress, _lenUpgrade, self.upgradeInProgress))

                self.logMessageDone = 3

        if self.upgradableDev is None: 
            self.upgradableDev = []
            for iterDev in self.ListOfDevices:
                if iterDev in ( '0000', 'ffff' ): continue
                if self.ListOfDevices[iterDev]['Health'] in ( 'TimedOut', 'Not Reachable'):
                    self.logging( 'Debug', "OTA heartbeat - skip %s not Live device" %iterDev)
                    continue

                _mainPowered = False
                if 'MacCapa' in self.ListOfDevices[iterDev]:
                    if self.ListOfDevices[iterDev]['MacCapa'] == '8e':
                        _mainPowered = True
                if 'PowerSource' in self.ListOfDevices[iterDev]:
                    if (self.ListOfDevices[iterDev]['PowerSource']) == 'Main':
                        _mainPowered = True

                if  not _mainPowered and not self.pluginconf.pluginConf['batteryOTA']:
                    self.logging( 'Debug', "OTA heartbeat - skip %s not main powered" %iterDev)
                    continue

                otaDevice = False
                manufCode = None
                if 'Manufacturer Name' in self.ListOfDevices[ iterDev ]:
                    if self.ListOfDevices[iterDev]['Manufacturer'] in OTA_MANUF_NAME:
                        manufCode = self.ListOfDevices[iterDev]['Manufacturer']
                        otaDevice = True
                if not otaDevice and 'Manufacturer' in self.ListOfDevices[ iterDev ]:
                    if self.ListOfDevices[iterDev]['Manufacturer Name'] in OTA_MANUF_NAME:
                        manufCode = self.ListOfDevices[iterDev]['Manufacturer']
                        otaDevice = True

                if not otaDevice:
                    self.logging( 'Debug', "OTA heartbeat - skip %s No firmware update for that product ManufCode: %s" %(iterDev,manufCode ))
                    continue

                upgradable = False
                for manufCode in self.availableManufCode:
                    if manufCode in OTA_MANUF_CODE:
                        upgradable = True
                        self.upgradableDev.append( iterDev )

                if not upgradable:
                    self.logging( 'Debug', "OTA heartbeat - skip %s manufcode %s is not in %s" %(iterDev, str( OTA_MANUF_CODE ), self.availableManufCode))
        else:
            if self.upgradeInProgress is None and len(self.upgradableDev) > 0 :
                # It is time to take a new Device
                if self.upgradeOTAImage is None:
                    if len(self.OTA['Images']) == 0:
                        return
                    for iterKey in iter(self.OTA['Images']):
                        if iterKey not in self.batteryTypeFirmware:
                            key = iterKey
                            break
                    else:
                        # Looks like we have the remaining firmware only for Battery devices
                        key = next(iter(self.OTA['Images']))

                    Domoticz.Log("OTA heartbeat - Image: 0x%04X from file: %s" %(key, self.OTA['Images'][key]['Filename']))

                    # Loading Image in Zigate
                    self.upgradeOTAImage = key
                    Domoticz.Log("----self.upgradeOTAImage = %s" %self.upgradeOTAImage)
                    self.upgradeOTAImageType = None
                    self.ota_load_new_image( key )
                    return # Will come back in the next cycle for Notification

                # At that stage: Image for key has been loaded into Zigate
                # Let's start the process
                self.upgradeInProgress = self.upgradableDev[0]
                del self.upgradableDev[0]
    
                if self.upgradeOTAImage in BATTERY_TYPES: # For batery Types , let's reduce the frequency of Notify
                    if ((self.HB % 60 ) != 0 ):
                        return

                # Find EP
                EPout = "01"
                if self.upgradeInProgress not in self.ListOfDevices:
                    return
                if 'Ep' not in self.ListOfDevices[self.upgradeInProgress]:
                    return
                for x in self.ListOfDevices[self.upgradeInProgress]['Ep']:
                    if OTA_CLUSTER_ID in self.ListOfDevices[self.upgradeInProgress]['Ep'][x]:
                        EPout = x
                        break
                for x in self.OTA['Images']:
                    if x == 'Upgraded Device': continue
                    if self.OTA['Images'][x]['Decoded Header']['manufacturer_code'] in OTA_MANUF_CODE and \
                        self.ListOfDevices[self.upgradeInProgress]['Manufacturer'] in OTA_MANUF_NAME:
                        if self.upgradeInProgress in self.ListOfDevices:
                            if 'Manufacturer' in self.ListOfDevices[self.upgradeInProgress]:
                                if int(self.ListOfDevices[self.upgradeInProgress]['Manufacturer'],16) != self.OTA['Images'][x]['Decoded Header']['manufacturer_code']:
                                    self.logging( 'Debug', "     No need to notify %s:  %s != %s" \
                                            %(self.upgradeInProgress, self.ListOfDevices[self.upgradeInProgress]['Manufacturer'], self.OTA['Images'][x]['Decoded Header']['manufacturer_code']))
                                    # No need to advertise as this is not a Manufacturer code match.
                                    continue

                        self.notify_device( self.OTA['Images'][x]['Decoded Header']['manufacturer_code'], self.OTA['Images'][x]['Decoded Header']['image_type'], 
                                self.OTA['Images'][x]['Decoded Header']['image_version'], self.upgradeInProgress, MsgEpOut=EPout )

                        #self.OTA['Upgraded Device'][self.upgradeInProgress] = {}
                        #self.logging( 'Debug', "OTA hearbeat - Request Advertizement for %s %s" \
                        #        %(self.upgradeInProgress, EPout))
                        #
                        #self.ota_image_advertize(self.upgradeInProgress, EPout, \
                        #        self.OTA['Images'][x]['Decoded Header']['image_version'], \
                        #        self.OTA['Images'][x]['Decoded Header']['image_type'], \
                        #        self.OTA['Images'][x]['Decoded Header']['manufacturer_code'])
                        break
            elif self.upgradeInProgress:
                # Check Timeout
                if self.upgradeInProgress not in self.OTA['Upgraded Device']:
                    self.OTA['Upgraded Device'][self.upgradeInProgress] = {}
                if 'Status' not in self.OTA['Upgraded Device'][self.upgradeInProgress]:
                    self.OTA['Upgraded Device'][self.upgradeInProgress]['Status'] = 'Notified'
                    self.OTA['Upgraded Device'][self.upgradeInProgress]['Notified Time'] = int(time())

                _status = self.OTA['Upgraded Device'][self.upgradeInProgress]['Status']
                _notifiedTime = self.OTA['Upgraded Device'][self.upgradeInProgress]['Notified Time']
                if _status == 'Timeout':
                    self.upgradeInProgress = None

                elif _status == 'Notified':
                    TO_notification = TO_MAINPOWERED_NOTIFICATION
                    if self.upgradeOTAImage in BATTERY_TYPES:
                        TO_notification = TO_BATTERYPOWERED_NOTIFICATION

                    if int(time()) > ( _notifiedTime + TO_notification):
                            self.logging( 'Debug', "OTA heartbeat - Timeout for %s Upgrade notified " \
                                    %self.upgradeInProgress)
                            self.OTA['Upgraded Device'][self.upgradeInProgress]['Status'] = 'Timeout'
                            self.upgradeInProgress = None
                    elif self.pluginconf.pluginConf['batteryOTA']:
                        EPout = "01"
                        if 'Ep' in self.ListOfDevices[self.upgradeInProgress]:
                            for x in self.ListOfDevices[self.upgradeInProgress]['Ep']:
                                if OTA_CLUSTER_ID in self.ListOfDevices[self.upgradeInProgress]['Ep'][x]:
                                    EPout = x
                                    break
                        _key = self.upgradeOTAImage
                        if _key in self.OTA['Images']:
                            self.upgradeOTAImageType = self.OTA['Images'][_key]['Decoded Header']['image_type']
                            self.ota_image_advertize(self.upgradeInProgress, EPout, \
                                self.OTA['Images'][_key]['Decoded Header']['image_version'], \
                                self.OTA['Images'][_key]['Decoded Header']['image_type'], \
                                self.OTA['Images'][_key]['Decoded Header']['manufacturer_code'], Flag_ = True)

                elif _status in ( 'Block Requested', 'Transfer Progress' ):
                    if 'Last Block sent' in self.OTA['Upgraded Device'][self.upgradeInProgress]:
                        _lastBlockTime = self.OTA['Upgraded Device'][self.upgradeInProgress]['Last Block sent']
                        if int(time()) > ( _lastBlockTime + TO_TRANSFER): # Tiemout 
                            Domoticz.Log("OTA heartbeat - Timeout -No new block sent in the last %s for %s" \
                                    %( TO_TRANSFER, self.upgradeInProgress))
                            Domoticz.Error("OTA heartbeat - Timeout for %s Block Requested or Transfer Progress " \
                                    %self.upgradeInProgress)
                            self.OTA['Upgraded Device'][self.upgradeInProgress]['Status'] = 'Timeout'
                            self.upgradeInProgress = None
                    else:
                        Domoticz.Log("OTA heartbeat - Transfer not yet started")

                elif _status in ( 'Transfer Aborted', 'Transfer Completed' ):
                    self.upgradeInProgress = None
                else:
                    Domoticz.Log("OTA heartbeat - _status: %s , upgradeInProgress: %s" %( _status, self.upgradeInProgress))

        if self.upgradeInProgress is None and len(self.upgradableDev) == 0 and \
                ((self.HB % ( self.pluginconf.pluginConf['OTAwait4nextImage'] // HEARTBEAT) ) == 0):
            # We have been through all Devices for this particular Image.
            # Let's go to the next Image
            if self.upgradeOTAImage:
                if self.upgradeOTAImage in self.OTA['Images']:
                    del self.OTA['Images'][self.upgradeOTAImage]
                else:
                    Domoticz.Log("OTA heartbeat - %s not found in %s" %( self.upgradeOTAImage, str(self.OTA['Images'].keys())))
            else:
                Domoticz.Log("OTA heartbeat - No device to be upgraded...")
                self.upgradeDone = None
                if 'Images' in self.OTA:
                    del self.OTA['Images']
                self.OTA['Images'] = {}

            self.upgradeOTAImage = None
            Domoticz.Log("------self.upgradeOTAImage = %s" %self.upgradeOTAImage)
            self.upgradableDev = None
            self.upgradeInProgress = None

            if self.upgradeDone is None and len(self.OTA['Images']) == 0:
                # In the last cycle we didn't do any upgrade
                # We can stop the OTAu now
                _textmsg = 'No new firmware to transfer, stop OTA upgrade'
                self.adminWidgets.updateNotificationWidget( self.Devices, _textmsg)
                self.stopOTA = True
                self.logging( 'Status', "OTA heartbeat - Stop OTA upgrade")


def convertTime( _timeInSec):

    _timeInSec_hh = _timeInSec // 3600
    _timeInSec = _timeInSec - ( _timeInSec_hh * 3600)
    _timeInSec_mm = _timeInSec // 60
    _timeInSec = _timeInSec - ( _timeInSec_mm * 60 )
    _timeInSec_ss = _timeInSec
    return _timeInSec_hh, _timeInSec_mm, _timeInSec_ss 

