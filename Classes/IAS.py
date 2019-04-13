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

from Modules.output import *


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
        0x0225: 'standar_warning',
        0xFFFF: 'invalid' }

ENROLL_RESPONSE_CODE =  0x00

ZONE_ID = 0x00

class IAS_Zone_Management:

    def __init__( self , ZigateComm, ListOfDevices, ZigateIEEE = None):
        self.devices = {}
        self.ListOfDevices = ListOfDevices
        self.tryHB = 0
        self.wip = False
        self.HB = 0
        self.ZigateComm = ZigateComm
        self.ZigateIEEE = None
        if ZigateIEEE != '':
            self.ZigateIEEE = ZigateIEEE

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

        Domoticz.Debug("setZigateIEEE - Set Zigate IEEE: %s" %ZigateIEEE)
        self.ZigateIEEE = ZigateIEEE
        return

    def setIASzoneControlerIEEE( self, key, Epout ):

        Domoticz.Debug("setIASzoneControlerIEEE for %s allow: %s" %(key, Epout))
        manuf_id = "0000"
        if 'Manufacturer' in self.ListOfDevices[key]:
            manuf_id = self.ListOfDevices[key]['Manufacturer']

        manuf_spec = "00"
        cluster_id = "%04x" %0x0500
        attribute = "%04x" %0x0010
        data_type = "F0" # ZigBee_IeeeAddress = 0xf0
        data = str(self.ZigateIEEE)
        self.__write_attribute( key, "01", Epout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)

    def readConfirmEnroll( self, key, Epout ):

        if not self.ZigateIEEE:
            Domoticz.Log("readConfirmEnroll - Zigate IEEE not yet known")
            return
        if key not in self.devices:
            Domoticz.Log("readConfirmEnroll - while not yet started")
            return

        cluster_id = "%04x" %0x0500
        attribute = 0x0000
        self.__ReadAttributeReq( key, "01", Epout, cluster_id , attribute )

    def IASZone_enroll_response_( self, nwkid, Epout ):
        '''2.the CIE sends a ‘enroll’ message to the IAS Zone device'''

        if not self.ZigateIEEE:
            Domoticz.Log("IASZone_enroll_response_ - Zigate IEEE not yet known")
            return
        if nwkid not in self.devices:
            Domoticz.Log("IASZone_enroll_response - while not yet started")
            return

        Domoticz.Debug("IASZone_enroll_response for %s" %nwkid)
        addr_mode = "02"
        enroll_rsp_code =   "%02x" %ENROLL_RESPONSE_CODE
        zoneid = "%02x" %ZONE_ID

        datas = addr_mode + nwkid + "01" + Epout + enroll_rsp_code + zoneid
        self.ZigateComm.sendData( "0400", datas )
        return

    def IASZone_enroll_response_zoneID( self, nwkid, Epout ):
        '''4.the CIE sends again a ‘response’ message to the IAS Zone device with ZoneID'''

        if not self.ZigateIEEE:
            Domoticz.Log("IASZone_enroll_response_zoneID - Zigate IEEE not yet known")
            return
        if nwkid not in self.devices:
            Domoticz.Log("IASZone_enroll_response_zoneID - while not yet started")
            return

        Domoticz.Debug("IASZone_enroll_response for %s" %nwkid)
        addr_mode = "02"
        enroll_rsp_code =   "%02x" %ENROLL_RESPONSE_CODE
        zoneid = "%02x" %ZONE_ID

        datas = addr_mode + nwkid + "01" + Epout + enroll_rsp_code + zoneid
        self.ZigateComm.sendData( "0400", datas )
        return


    def IASZone_attributes( self, nwkid, Epout):

        if not self.ZigateIEEE:
            Domoticz.Log("IASZone_attributes - Zigate IEEE not yet known")
            return
        if nwkid not in self.devices:
            Domoticz.Log("IASZone_attributes - while not yet started")
            return

        cluster_id = "%04x" %0x0500
        attribute = [ 0x0000, 0x0001, 0x0002 ]
        self.__ReadAttributeReq( nwkid, "01", Epout, cluster_id , attribute )

    def IASZone_triggerenrollement( self, nwkid, Epout):

        Domoticz.Debug("IASZone_triggerenrollement - Addr: %s Ep: %s" %(nwkid, Epout))
        if not self.ZigateIEEE:
            Domoticz.Log("IASZone_triggerenrollement - Zigate IEEE not yet known")
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

        Domoticz.Debug("receiveIASmessages - from: %s Step: %s Value: %s" %(nwkid, step, value))

        if not self.ZigateIEEE:
            Domoticz.Log("receiveIASmessages - Zigate IEEE not yet known")
            return
        if nwkid not in self.devices:
            Domoticz.Log("receiveIASmessages - %s not in %s" %(nwkid, self.devices))
            return

        iterEp = self.devices[nwkid]['Ep']

        if  step == 3:  # Receive Write Attribute Message
            Domoticz.Debug("receiveIASmessages - Write rAttribute Response: %s" %value)
            self.HB = 0
            if self.devices[nwkid]['Step'] <= 4:
                self.devices[nwkid]['Step'] = 4
            self.readConfirmEnroll(nwkid, iterEp)
            self.IASZone_attributes( nwkid, iterEp)
            self.IASZone_enroll_response_zoneID( nwkid, iterEp )

        elif step == 5: # Receive Attribute 0x0001 and 0x0002
            self.HB = 0
            if self.devices[nwkid]['Step'] <= 7:
                self.devices[nwkid]['Step'] = 7
            self.IASZone_attributes( nwkid, iterEp)
            self.IASZone_enroll_response_zoneID( nwkid, iterEp )
            self.readConfirmEnroll(nwkid, iterEp)

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
        Domoticz.Debug("IAS_heartbeat ")
        if not self.ZigateIEEE:
            Domoticz.Log("IAS_heartbeat - Zigate IEEE not yet known")
            return
        remove_devices =[]
        for iterKey in self.devices:
            iterEp = self.devices[iterKey]['Ep']
            Domoticz.Debug("IAS_heartbeat - processing %s step: %s" %(iterKey, self.devices[iterKey]['Step']))
            if self.devices[iterKey]['Step'] == 0:
                continue

            if self.HB > 1 and self.devices[iterKey]['Step'] == 2:
                self.HB = 0
                self.devices[iterKey]['Ep'] = iterEp
                Domoticz.Debug("IAS_heartbeat - TO restart self.IASZone_attributes")
                self.IASZone_enroll_response_zoneID( iterKey, iterEp)
                self.IASZone_attributes( iterKey, iterEp)

            elif self.HB > 1 and self.devices[iterKey]['Step'] == 4:
                self.tryHB += self.tryHB
                self.HB = 0
                self.wip = True
                iterEp = self.devices[iterKey]['Ep']
                Domoticz.Debug("IAS_heartbeat - TO restart self.setIASzoneControlerIEEE")
                if self.tryHB > 3:
                    self.tryHB = 0
                    self.devices[iterKey]['Step'] = 5

            elif self.HB > 1 and self.devices[iterKey]['Step'] == 6:
                self.tryHB += self.tryHB
                self.HB = 0
                iterEp = self.devices[iterKey]['Ep']
                self.readConfirmEnroll(iterKey, iterEp)
                Domoticz.Debug("IAS_heartbeat - TO restart self.readConfirmEnroll")
                if self.tryHB > 3:
                    self.tryHB = 0
                    self.devices[iterKey]['Step'] = 7

            elif self.devices[iterKey]['Step'] == 7: # Receive Confirming Enrollement
                Domoticz.Debug("IAS_heartbeat - Enrollment confirmed/completed")
                self.HB = 0
                self.wip = False
                self.devices[iterKey]['Step'] = 0
                remove_devices.append(iterKey)
        
        for iter in remove_devices:
            del iter

        return
