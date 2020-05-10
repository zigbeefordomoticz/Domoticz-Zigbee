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
from datetime import datetime

from Modules.output import *
from Modules.zigateConsts import ADDRESS_MODE, ZIGATE_EP
from Classes.PluginConf import PluginConf

ZONE_TYPE = { 0x0000: 'standard',
        0x000D: 'motion',
        0x0015: 'contact', 
        0x0028: 'fire',
        0x002A: 'water',
        0x002B: 'gas',
        0x002C: 'personal',
        0x002D: 'vibration',
        0x010F: 'remote_control',
        0x0115: 'key_fob',
        0x021D: 'key_pad',
        0x0225: 'standard_warning',
        0xFFFF: 'invalid' }

ENROLL_RESPONSE_CODE =  0x00

ZONE_ID = 0x00

class IAS_Zone_Management:

    def __init__( self , pluginconf, ZigateComm, ListOfDevices, loggingFileHandle, ZigateIEEE = None):
        self.devices = {}
        self.ListOfDevices = ListOfDevices
        self.tryHB = 0
        self.wip = False
        self.HB = 0
        self.ZigateComm = ZigateComm
        self.ZigateIEEE = None
        if ZigateIEEE != '':
            self.ZigateIEEE = ZigateIEEE
        self.pluginconf = pluginconf
        self.loggingFileHandle = loggingFileHandle

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

        self.debugIAS = self.pluginconf.pluginConf['debugIAS']
        if logType == 'Debug' and self.debugIAS:
            self._loggingDebug( message)
        elif logType == 'Log':
            self._loggingLog( message )
        elif logType == 'Status':
            self._loggingStatus( message)
        return

    def __write_attribute( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data):

        addr_mode = "02" # Short address
        direction = "00"
        lenght = "01" # Only 1 attribute
        datas = addr_mode + key + EPin + EPout + clusterID
        datas += direction + manuf_spec + manuf_id
        datas += lenght +attribute + data_type + data
        self.ZigateComm.sendData( "0110", datas )
        return


    def __ReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes ):

        direction = '00'
        manufacturer_spec = '00'
        manufacturer = '0000'
        if addr not in self.ListOfDevices:
            return
        #if 'Manufacturer' in self.ListOfDevices[addr]:
        #    manufacturer = self.ListOfDevices[addr]['Manufacturer']
        if not isinstance(ListOfAttributes, list):
            # We received only 1 attribute
            Attr = "%04x" %(ListOfAttributes)
            lenAttr = 1
            weight = 1
        else:
            lenAttr = len(ListOfAttributes)
            Attr =''
            for x in ListOfAttributes:
                Attr_ = "%04x" %(x)
                Attr += Attr_
        datas = "02" + addr + EpIn + EpOut + Cluster + direction + manufacturer_spec + manufacturer + "%02x" %(lenAttr) + Attr
        self.ZigateComm.sendData( "0100", datas )
        return

    def setZigateIEEE(self, ZigateIEEE):

        self.logging( 'Debug', "setZigateIEEE - Set Zigate IEEE: %s" %ZigateIEEE)
        self.ZigateIEEE = ZigateIEEE
        return

    def setIASzoneControlerIEEE( self, key, Epout ):

        self.logging( 'Debug', "setIASzoneControlerIEEE for %s allow: %s" %(key, Epout))
        manuf_id = "0000"
        if 'Manufacturer' in self.ListOfDevices[key]:
            manuf_id = self.ListOfDevices[key]['Manufacturer']

        manuf_spec = "00"
        cluster_id = "%04x" %0x0500
        attribute = "%04x" %0x0010
        data_type = "F0" # ZigBee_IeeeAddress = 0xf0
        data = str(self.ZigateIEEE)
        self.__write_attribute( key, ZIGATE_EP, Epout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)

    def readConfirmEnroll( self, key, Epout ):

        if not self.ZigateIEEE:
            self.logging( 'Log', "readConfirmEnroll - Zigate IEEE not yet known")
            return
        if key not in self.devices:
            self.logging( 'Log', "readConfirmEnroll - while not yet started")
            return

        cluster_id = "%04x" %0x0500
        attribute = 0x0000
        self.__ReadAttributeReq( key, ZIGATE_EP, Epout, cluster_id , attribute )

    def IASZone_enroll_response_( self, nwkid, Epout ):
        '''2.the CIE sends a ‘enroll’ message to the IAS Zone device'''

        if not self.ZigateIEEE:
            self.logging( 'Log', "IASZone_enroll_response_ - Zigate IEEE not yet known")
            return
        if nwkid not in self.devices:
            self.logging( 'Log', "IASZone_enroll_response - while not yet started")
            return

        self.logging( 'Debug', "IASZone_enroll_response for %s" %nwkid)
        addr_mode = "02"
        enroll_rsp_code =   "%02x" %ENROLL_RESPONSE_CODE
        zoneid = "%02x" %ZONE_ID

        datas = addr_mode + nwkid + ZIGATE_EP + Epout + enroll_rsp_code + zoneid
        self.ZigateComm.sendData( "0400", datas )
        return

    def IASZone_enroll_response_zoneID( self, nwkid, Epout ):
        '''4.the CIE sends again a ‘response’ message to the IAS Zone device with ZoneID'''

        if not self.ZigateIEEE:
            self.logging( 'Log', "IASZone_enroll_response_zoneID - Zigate IEEE not yet known")
            return
        if nwkid not in self.devices:
            self.logging( 'Log', "IASZone_enroll_response_zoneID - while not yet started")
            return

        self.logging( 'Debug', "IASZone_enroll_response for %s" %nwkid)
        addr_mode = "02"
        enroll_rsp_code =   "%02x" %ENROLL_RESPONSE_CODE
        zoneid = "%02x" %ZONE_ID

        datas = addr_mode + nwkid + ZIGATE_EP + Epout + enroll_rsp_code + zoneid
        self.ZigateComm.sendData( "0400", datas )
        return

    def IASWD_enroll( self, nwkid, Epout):

        cluster_id = "0502"
        manuf_id = "00"
        manuf_spec = "0000"
        attribute = "0000"
        data_type = "%02X" %0x21
        data = "%04X" %0xFFFE
        self.__write_attribute( nwkid, ZIGATE_EP, Epout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)

    def IASZone_attributes( self, nwkid, Epout):

        if not self.ZigateIEEE:
            self.logging( 'Log', "IASZone_attributes - Zigate IEEE not yet known")
            return
        if nwkid not in self.devices:
            self.logging( 'Log', "IASZone_attributes - while not yet started")
            return

        cluster_id = "%04x" %0x0500
        attribute = [ 0x0000, 0x0001, 0x0002 ]
        self.__ReadAttributeReq( nwkid, ZIGATE_EP, Epout, cluster_id , attribute )

    def IASZone_triggerenrollement( self, nwkid, Epout):

        self.logging( 'Debug', "IASZone_triggerenrollement - Addr: %s Ep: %s" %(nwkid, Epout))
        if not self.ZigateIEEE:
            self.logging( 'Log', "IASZone_triggerenrollement - Zigate IEEE not yet known")
            return
        if nwkid not in self.devices:
            self.devices[nwkid] = {}

        self.wip = True
        self.HB = 0
        self.devices[nwkid]['Step'] = 2
        self.devices[nwkid]['Ep'] = Epout
        self.setIASzoneControlerIEEE( nwkid, Epout)
        return

    def receiveIASmessages(self, nwkid , step, value):

        self.logging( 'Debug', "receiveIASmessages - from: %s Step: %s Value: %s" %(nwkid, step, value))

        if not self.ZigateIEEE:
            self.logging( 'Debug', "receiveIASmessages - Zigate IEEE not yet known")
            return
        if nwkid not in self.devices:
            self.logging( 'Debug', "receiveIASmessages - %s not in %s" %(nwkid, self.devices))
            return

        iterEp = self.devices[nwkid]['Ep']

        if  step == 3:  # Receive Write Attribute Message
            self.logging( 'Debug', "receiveIASmessages - Write rAttribute Response: %s" %value)
            self.HB = 0
            if self.devices[nwkid]['Step'] <= 4:
                self.devices[nwkid]['Step'] = 4
            self.readConfirmEnroll(nwkid, iterEp)
            self.IASZone_attributes( nwkid, iterEp)
            self.IASZone_enroll_response_zoneID( nwkid, iterEp )

        elif step == 5: # Receive Attribute 0x0001 and 0x0002

            if 'ticks_5' not in self.devices[nwkid]:
                self.devices[nwkid]['ticks_5'] = 0
            if self.devices[nwkid]['ticks_5'] > 3:
                self.logging( 'Debug', "receiveIASmessages - Timeout %s/%s at step 5" %(nwkid, iterEp))
                del self.devices[nwkid]
                return

            self.HB = 0
            if self.devices[nwkid]['Step'] <= 7:
                self.devices[nwkid]['Step'] = 7
            self.IASZone_attributes( nwkid, iterEp)
            self.IASZone_enroll_response_zoneID( nwkid, iterEp )
            self.readConfirmEnroll(nwkid, iterEp)

            self.devices[nwkid]['ticks_5'] += 1

        elif step == 7: # Receive Confirming Enrollement
            self.HB = 0
            self.wip = False
            self.devices[nwkid]['Step'] = 0
            self.IASZone_attributes( nwkid, iterEp)
            self.readConfirmEnroll(nwkid, iterEp)
            del self.devices[nwkid]

        return

    def decode8401(self, MsgSQN, MsgEp, MsgClusterId, MsgSrcAddrMode, MsgSrcAddr, MsgZoneStatus, MsgExtStatus, MsgZoneID, MsgDelay):


        # Custom Command Payload

        # ‘Zone Status Change Notification’ Payload
        # ZoneStatus : 0x01 (Not Enrolled ) / 0x02 (Enrolled)
        # Extended Status: 0x00
        # ZoneID is the index of the entry for the sending device
        # Delay is the time-delay in quarter-seconds between satus change taking place in ZoneState

        # IAS ZONE STATE
        # 0x00 not enrolled
        # 0x01 enrolled


        # Zone Status Change Notification
        # Bit 0: Alarm1
        #     1: Alarm2
        #     2: Tamper
        #     3: Battery
        #     4: Supervision reports
        #     5: Restore Reports
        #     6: Trouble
        #     7: AC Mains
        #     8: Test
        #     9: Battery defect
        # 10-15: Reserved

        return

    def IAS_heartbeat(self):

        self.HB += 1

        if not self.wip:
            return
        self.logging( 'Debug', "IAS_heartbeat ")
        if not self.ZigateIEEE:
            self.logging( 'Log', "IAS_heartbeat - Zigate IEEE not yet known")
            return
        remove_devices =[]
        for iterKey in self.devices:
            iterEp = self.devices[iterKey]['Ep']
            self.logging( 'Debug', "IAS_heartbeat - processing %s step: %s" %(iterKey, self.devices[iterKey]['Step']))
            if self.devices[iterKey]['Step'] == 0:
                continue

            if self.HB > 1 and self.devices[iterKey]['Step'] == 2:
                self.HB = 0
                self.devices[iterKey]['Ep'] = iterEp
                self.logging( 'Debug', "IAS_heartbeat - TO restart self.IASZone_attributes")
                self.IASZone_enroll_response_zoneID( iterKey, iterEp)
                self.IASZone_attributes( iterKey, iterEp)

            elif self.HB > 1 and self.devices[iterKey]['Step'] == 4:
                self.tryHB += self.tryHB
                self.HB = 0
                self.wip = True
                iterEp = self.devices[iterKey]['Ep']
                self.logging( 'Debug', "IAS_heartbeat - TO restart self.setIASzoneControlerIEEE")
                if self.tryHB > 3:
                    self.tryHB = 0
                    self.devices[iterKey]['Step'] = 5

            elif self.HB > 1 and self.devices[iterKey]['Step'] == 6:
                self.tryHB += self.tryHB
                self.HB = 0
                iterEp = self.devices[iterKey]['Ep']
                self.readConfirmEnroll(iterKey, iterEp)
                self.logging( 'Debug', "IAS_heartbeat - TO restart self.readConfirmEnroll")
                if self.tryHB > 3:
                    self.tryHB = 0
                    self.devices[iterKey]['Step'] = 7

            elif self.devices[iterKey]['Step'] == 7: # Receive Confirming Enrollement
                self.logging( 'Debug', "IAS_heartbeat - Enrollment confirmed/completed")
                self.HB = 0
                self.wip = False
                self.devices[iterKey]['Step'] = 0
                remove_devices.append(iterKey)
        
        for iter in remove_devices:
            del iter

        return

    def write_IAS_WD_Squawk( self, nwkid, ep, SquawkMode):

        """
        <address mode: uint8_t>
        <target short address: uint16_t>
        <source endpoint: uint8_t>
        <destination endpoint: uint8_t>
        <direction: uint8_t>
        <manufacturer specific: uint8_t>
        <manufacturer id: uint16_t>
        <SquawkModeStrobeAndLevel: uint8_t>

        Bits 	Description
        0-3 	Squawk Mode - indicates the meaning of the required ‘squawk’:
            0 - System is armed
            1 - System is disarmed
            All other values are reserved
        4 	Strobe - indicates whether a visual strobe indication of the ‘squawk’ is required:
            0 - No strobe
            1 - Use strobe
            5 	Reserved
        6-7 	Squawk Level - indicates the requested level of the audible squawk sound:
            0 - Low level
            1 - Medium level
            2 - High level
            3 - Very high level
        """
        SQUAWKMODE = { 'disarmed': 0b00000000,
                       'armed':    0b00000001
                       }

        if SquawkMode not in SQUAWKMODE:
            Domoticz.Error("_write_IAS_WD_Squawk - %s/%s Unknown Squawk Mode: %" %(nwkid, ep,SquawkMode))

        self.logging( 'Debug', "write_IAS_WD_Squawk - %s/%s - Squawk Mode: %s >%s<" %(nwkid, ep, SquawkMode, SQUAWKMODE[SquawkMode]))
        direction = 0x00
        manuf = 0x00
        manufid = 0x0000

        datas  = "%02X" %ADDRESS_MODE['short']
        datas += nwkid
        datas += ZIGATE_EP
        datas += ep
        datas += "%02x" %direction
        datas += "%02X" %manuf
        datas += "%04X" %manufid
        datas += "%02X" %SQUAWKMODE[SquawkMode]
    
        self.logging( 'Debug', "_write_IASWD - 0x0112 %s" %datas)
        self.ZigateComm.sendData( "0112", datas )

    # IAS Warning Device Cluster
    # https://www.nxp.com/docs/en/user-guide/JN-UG-3077.pdf
    # Section 28 - page 545
    def _write_IASWD( self, nwkid, ep, warning_mode, warning_duration, strobe_duty, strobe_level):

        """
        Zigate -> Obj	0x0111 	Write Attribute request IAS_WD (from v3.1a)
                        <address mode: uint8_t>
			<target short address: uint16_t>
			<source endpoint: uint8_t>
			<destination endpoint: uint8_t>
			<direction: uint8_t>
			<manufacturer specific: uint8_t>
			<manufacturer id: uint16_t>
			<Warning Mode: uint8_t>
			<Warning Duration: uint16_t>
			<Strobe duty cycle : uint8_t>
			<Strobe level : uint8_t>
        """

        direction = 0x00
        manuf = 0x00
        manufid = 0x0000
    
        datas  = "%02X" %ADDRESS_MODE['short']
        datas += nwkid
        datas += ZIGATE_EP
        datas += ep
        datas += "%02x" %direction
        datas += "%02X" %manuf
        datas += "%04X" %manufid
        datas += "%02X" %warning_mode
        datas += "%04X" %warning_duration
        datas += "%02X" %strobe_duty
        datas += "%02X" %strobe_level
    
        self.logging( 'Debug', "_write_IASWD - 0x0111 %s" %datas)
        self.ZigateComm.sendData( "0111", datas )

    def warningMode( self , nwkid, ep, mode='both'):


        STROBE_LEVEL = { 'Low':0x00, 'Medium': 0x01 }

        WARNING_MODE = { 'Stop': 0b00000000,
                    'Burglar': 0b00000001,
                    'Fire': 0b00000010,
                    'Emergency': 0b00000011,
                    'Police Panic': 0b00000100,
                    'Fire Panic': 0b00000101,
                    'Emergency': 0b00000110 }
        STROBE_MODE = { 'No Strobe':0b00000000,
                'Use Strobe':0b00010000 }

        SIRENE_MODE = ( 'both', 'siren', 'strobe', 'stop')

        warning_duration = 0x00
        strobe_duty = 0x00
        strobe_level = 0x00
        warning_duration = 0x01 # 1 seconde
        if self.ListOfDevices[nwkid]['Model'] == 'WarningDevice':
            strobe_duty =  0x00
            strobe_level = 0x01
            if mode == 'both':
                warning_mode = 0b00010111
            elif mode == 'siren':
                warning_mode = 0b00010011
            elif mode == 'strobe':
                warning_mode = 0b00000100
            elif mode == 'stop':
                warning_mode = 0b00000000

        elif mode in SIRENE_MODE:
            if mode == 'both':
                warning_mode = WARNING_MODE['Fire'] + STROBE_MODE['Use Strobe']
                strobe_duty = 0x1E  # % duty cycle in 10% steps
                strobe_level = STROBE_LEVEL['Low']
            elif mode == 'siren':
                warning_mode = WARNING_MODE['Fire'] + STROBE_MODE['No Strobe'] 
            elif mode == 'strobe':
                warning_mode = WARNING_MODE['Stop'] + STROBE_MODE['Use Strobe'] 
                strobe_duty = 0x1E  # % duty cycle in 10% steps
                strobe_level = STROBE_LEVEL['Low']
            elif mode == 'stop':
                warning_mode = WARNING_MODE['Stop']

        warning_duration = self.pluginconf.pluginConf['alarmDuration']

        self.logging( 'Debug', "warningMode - Mode: %s, Duration: %s, Duty: %s, Level: %s" \
                %(bin(warning_mode), warning_duration, strobe_duty, strobe_level))
        self._write_IASWD( nwkid, ep, warning_mode, warning_duration, strobe_duty, strobe_level)

        return

    def siren_both( self, nwkid, ep):

        self.logging( 'Debug', "Device Alarm On ( Siren + Strobe)")
        self.warningMode( nwkid, ep, 'both' )
        return

    def siren_only( self, nwkid, ep):

        self.logging( 'Debug', "Device Alarm On (Siren)")
        self.warningMode( nwkid, ep, 'siren' )
        return

    def strobe_only( self, nwkid, ep):

        self.logging( 'Debug', "Device Alarm On ( Strobe)")
        self.warningMode( nwkid, ep, 'strobe' )
        return

    def alarm_on( self, nwkid, ep):

        self.siren_both( nwkid, ep)
        return

    def alarm_off( self, nwkid, ep):

        self.logging( 'Debug', "Device Alarm Off")
        self.warningMode( nwkid, ep, 'stop' )
        return

