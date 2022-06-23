#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_IAS.py
    Description: IAS Zone management
"""


import time
import struct

import Domoticz
from Modules.bindings import bindDevice
from Modules.tools import getEpForCluster
from Modules.zigateConsts import ZIGATE_EP
from Zigbee.zclCommands import (zcl_ias_wd_command_squawk,
                                zcl_ias_wd_command_start_warning,
                                zcl_ias_zone_enroll_response,
                                zcl_read_attribute, zcl_write_attribute)
from Zigbee.zdpCommands import zdp_simple_descriptor_request

from Modules.basicOutputs import write_attribute
from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import get_and_inc_ZCL_SQN


# Synopsys
#

# Auto-Enroll-Response ( CasaIA/Owon)
# -------------------------
#
# Node -> Host : Simple Desc riptor Request Response
#   - If 0x0500 in then Host -> Node :  Read Attribute Request ( 0x0500 / 0x0000, 0x0001, 0x0002 )
#
# Node -> Host Receiving the Read Attribute Response on 0x0500 / 0x0000, 0x0001, 0x0002 )
#              if ZoneState: Note Enrolled ( 0x0000 )
#                       Host -> Node :  Write Attribute IAS_CIE ( 0x0500 / 0x0010 )
#
# Node -> Host : Receiving ZCL IAS Zone: Zone Enrollement Request ( 0x0500 - Command 0x01 )
# Host -> Node : Send ZCL IAS Zone: Zone Enrollment Response ( 0x0500 - Command 0x00 with Status = 0x00 ; Zone Id: 0x01
#
# Host -> Node :  Read Attribute Request ( 0x0500 / 0x0000, 0x0001, 0x0002 )

ENROLL_RESPONSE_OK_CODE = 0x00
ZONE_ID = 0x00

IAS_ATTRIBUT_ZONE_STATE = "0000"
IAS_ATTRIBUT_ZONE_TYPE = "0001"
IAS_ATTRIBUT_ZONE_STATUS = "0002"

ZONE_STATE = {
    '00': 'Not enrolled',
    '01': 'Enrolled'
}

ZONE_TYPE = {
    '0000': 'Standard CIE 0x000d Motion sensor',
    '0015': 'Contact switch',
    '0016': 'Door/Window handle',
    '0028': 'Fire sensor',
    '002a': 'Water sensor',
    '002b': 'Carbon Monoxide (CO) sensor',
    '002c': 'Personal emergency device',
    '002d': 'Vibration/Movement sensor',
    '010f': 'Remote Control',
    '0115': 'Key fob 0x021d Keypad',
    '0225': 'Standard Warning Device',
    '0226': 'Glass break sensor',
    '0229': 'Security repeater',
    'ffff': 'Invalid Zone type'
}


STROBE_LEVEL = {"Low": 0x00, "Medium": 0x01}
SIRENE_MODE = ("both", "siren", "strobe", "stop")
strobe_mode = 0x00


class IAS_Zone_Management:
    
    def __init__(self, pluginconf, ZigateComm, ListOfDevices, IEEE2NWK, DeviceConf, log, zigbee_communitation, FirmwareVersion, ZigateIEEE=None):
        self.ListOfDevices = ListOfDevices
        self.IEEE2NWK = IEEE2NWK
        self.DeviceConf = DeviceConf
        self.ControllerLink = ZigateComm
        self.ControllerIEEE = None
        if ZigateIEEE:
            self.ControllerIEEE = ZigateIEEE
        self.pluginconf = pluginconf
        self.log = log
        self.zigbee_communication = zigbee_communitation
        self.FirmwareVersion = FirmwareVersion

    def logging(self, logType, message):
        self.log.logging("IAS", logType, message)

    def setZigateIEEE(self, ZigateIEEE):
        self.logging("Debug", f"setZigateIEEE - Set Zigate IEEE: {ZigateIEEE}")
        self.ControllerIEEE = ZigateIEEE

    def IAS_device_enrollment(self, NwkId):
        # This is coming from the plugin.
        # Let's see first if anything has to be done
        if "Model" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Model"] in ( "MOSZB-140", "SMSZB-120"):
            # Frient trigger itself the Device Enrollment
            return

        ias_ep_list = getEpForCluster(self, NwkId, "0500", strict=True)
        self.logging("Debug", f"IAS device Enrollment for {NwkId} on {ias_ep_list}, type: {type(ias_ep_list)} ")
        self.logging("Debug", "IAS_EP_LIST: %s" %str(ias_ep_list))
        if not ias_ep_list:
            return
        
        if is_device_enrollment_completed(self, NwkId):
            return
        
        self.logging("Debug", f"IAS device Enrollment for {NwkId} on {ias_ep_list}, type: {type(ias_ep_list)} ")
        if "IAS" not in self.ListOfDevices[ NwkId ]:
            self.ListOfDevices[NwkId]["IAS"] = {}
        if "Auto-Enrollment" not in self.ListOfDevices[NwkId]["IAS"]:
            self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"] = {}
        if "Status" not in self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]:
            
            self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]["Status"] = "Enrollment In Progress"
        if "Ep" not in self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]:
            self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]["Ep"] ={}
            
        if self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]["Status"] == "Enrolled":
            return

        self.logging("Debug", f"IAS device Enrollment for {NwkId} - IAS_EP: {ias_ep_list}, Ep: {self.ListOfDevices[NwkId]['IAS']['Auto-Enrollment']['Ep']}")
        for ep in list(ias_ep_list):
            self.logging("Debug", f"IAS device Enrollment for {NwkId} - Checking Ep: {ep}")
            if self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]["Ep"] != {} and ep in self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]["Ep"]:
                continue
            
            self.logging("Debug", f"IAS device Enrollment for {NwkId} - start Enrollment on Ep: {ep}")
            self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]["Ep"][str(ep)] = {"Status": "Service Discovery", "TimeStamp": time.time()}
            IAS_CIE_service_discovery( self, NwkId, str(ep))
            
        if is_device_enrollment_completed(self, NwkId):
            self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]["Status"] = "Enrolled"

                
        
    def IAS_CIE_service_discovery_response( self, NwkId, ep, Data):
        self.logging("Debug", f"IAS device Enrollment for {NwkId} - received a Read Attribute Response on Discovery Request for Ep: {ep}")
        attributes = retreive_attributes(self, Data)
        self.logging("Debug", f"         Attributes : {attributes}")
        if IAS_ATTRIBUT_ZONE_STATE not in attributes:
            self.logging("Debug", f"IAS device Enrollment for {NwkId} - Attribute {IAS_ATTRIBUT_ZONE_STATE} not found in {attributes}")
            return
        if attributes[ IAS_ATTRIBUT_ZONE_STATE ]["Status"] != "00":
            self.logging("Debug", f"IAS device Enrollment for {NwkId} - Attribute {IAS_ATTRIBUT_ZONE_STATE} Status: {attributes[ IAS_ATTRIBUT_ZONE_STATE ]['Status']}")
            
        if attributes[ IAS_ATTRIBUT_ZONE_STATE ]["Value"] == "00":
            # Not Enrolled, let's start the process
            self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"][ep]["Status"] = "set IAS CIE Address"
            set_IAS_CIE_Address(self, NwkId, ep)
        elif attributes[ IAS_ATTRIBUT_ZONE_STATE ]["Value"] == "01":
            # Enrolled, let's req the IAS ICE address
            check_IAS_CIE_Address(self, NwkId, ep)
            self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"][ep]["Status"] = "Enrolled"
          
        if is_device_enrollment_completed(self, NwkId):
            self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]["Status"] = "Enrolled"
  
    def IAS_zone_enroll_request(self, NwkId, Ep, ZoneType, sqn):
        self.logging("Debug", f"IAS device Enrollment Request for {NwkId}/{Ep} ZoneType: {ZoneType}")

        if NwkId not in self.ListOfDevices:
            return

        if is_device_enrollment_completed(self, NwkId):
            return

        # Receiving an Enrollment Request
        if ( 
            "IAS" not in self.ListOfDevices[ NwkId ]
            or "Auto-Enrollment" not in self.ListOfDevices[ NwkId ]["IAS"]
            or "Ep" not in self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"] 
            or Ep not in self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"]
            or self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"][ Ep ]["Status"] != "Wait for Enrollment request"
        ):
            # We are receiving a spontenous Enrollment Request (Frient/Develco)
            # Process will be fast and Quick
            if "IAS" not in self.ListOfDevices[ NwkId ]:
                self.ListOfDevices[ NwkId ]["IAS"] = {}
            if "Auto-Enrollment" not in self.ListOfDevices[ NwkId ]["IAS"]:
                self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"] = {"Status": {}}
            if "Ep" not in self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]:
                self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"] = {}
            if Ep not in self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"]:
                self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"][ Ep ] = {}

            # We are may be in an Auto-Enrollment by the device ( Frient )
            self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"][ Ep ]["Status"] = "Enrolled2"
            self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"][ Ep ]["ZoneId"] = "%02x" %ZONE_ID
            IAS_Zone_enrollment_response(self, NwkId, Ep, sqn, ZONE_ID)
            check_IAS_CIE_Address(self, NwkId, Ep)
            IAS_CIE_service_discovery( self, NwkId, Ep)
            if Ep not in self.ListOfDevices[NwkId]["Ep"] or self.ListOfDevices[NwkId]["Ep"][ Ep ] in ( "", {}):
                # If we get the enrollment at the begin, it will then define the End Point, and we won't request it
                zdp_simple_descriptor_request(self, NwkId, Ep)
                
            bindDevice(self, self.ListOfDevices[ NwkId ]['IEEE'], Ep, "0500")
            if is_device_enrollment_completed(self, NwkId):
                self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]["Status"] = "Enrolled2"
            return

        if self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"][ Ep ]["Status"] in ( "Enrolled", "Enrolled2"):
            self.logging("Debug", f"IAS device Enrollment Request for {NwkId}/{Ep} already Enrolled !!!")
            check_IAS_CIE_Address(self, NwkId, Ep)
            return
        
        self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"][ Ep ]["Status"] = "Enrolled"
        self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"][ Ep ]["ZoneId"] = "%02x" %ZONE_ID
        IAS_Zone_enrollment_response(self, NwkId, Ep, sqn, ZONE_ID)
        check_IAS_CIE_Address(self, NwkId, Ep)
        IAS_CIE_service_discovery( self, NwkId, Ep)
        bindDevice(self, self.ListOfDevices[ NwkId ]['IEEE'], Ep, "0500")
        if is_device_enrollment_completed(self, NwkId):
            self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]["Status"] = "Enrolled"
            

    def IAS_zone_enroll_request_response(self, NwkId, Ep, EnrollResponseCode, ZoneId):
        self.logging("Debug", f"IAS device Enrollment Request Response for {NwkId}/{Ep} Response: {EnrollResponseCode} ZoneId: {ZoneId}")
        if ( 
            NwkId not in self.ListOfDevices 
            and "IAS" not in self.ListOfDevices[ NwkId ] 
            and "Auto-Enrollment" not in self.ListOfDevices[ NwkId ]["IAS"] 
            and "Ep" not in self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"] 
            and Ep not in self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"]
        ):
            self.logging("Error", f"IAS device Enrollment Request Response for {NwkId}/{Ep} Response: {EnrollResponseCode} ZoneId: {ZoneId}")
            return
        
        if EnrollResponseCode == "%02x" %ENROLL_RESPONSE_OK_CODE:
            self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"][ Ep ]["Status"] = "Enrolled"
        if is_device_enrollment_completed(self, NwkId):
            self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]["Status"] = "Enrolled"
            self.ListOfDevices[NwkId]["IAS"]["ZoneId"] = ZoneId
     
    def IAS_CIE_write_response(self, NwkId, Ep, Status):
        # We are receiving a Write Attribute response
        self.logging("Debug", f"IAS CIE write Response for {NwkId}/{Ep}  Status: {Status}")
        if ( 
            NwkId not in self.ListOfDevices 
            and "IAS" not in self.ListOfDevices[ NwkId ] 
            and "Auto-Enrollment" not in self.ListOfDevices[ NwkId ]["IAS"] 
            and "Ep" not in self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"] 
            and Ep not in self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"]
        ):
            return

        if self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"][ Ep ]["Status"] != "set IAS CIE Address":
            self.logging("Debug", f"IAS CIE write Response for {NwkId}/{Ep}  {self.ListOfDevices[ NwkId ]['IAS']['Auto-Enrollment']['Ep'][ Ep ]['Status']} !=  set IAS CIE Address")
            return

        # We got the confirmation. Now we have to wait for the Enrollment Request
        if Status == "00":
            self.logging("Debug", f"IAS CIE write Response for {NwkId}/{Ep}  Waiting for Enrollment request")
            self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"][ Ep ]["Status"] = "Wait for Enrollment request"

    def IASWD_enroll(self, NwkId, Epout):
        data_type = "%02X" % 0x21
        data = "%04X" % 0xFFFE
        zcl_write_attribute( self, NwkId, ZIGATE_EP, Epout, "0502", "00", "0000", "0000", data_type, data, ackIsDisabled=False )

    def IAS_WD_Maximum_duration(self, NwkId, Epout, duration):
        data_type = "21"
        duration = "%04x" %duration
        zcl_write_attribute( self, NwkId, ZIGATE_EP, Epout, "0502", "00", "0000", "0000", data_type, duration, ackIsDisabled=False )
        
    def write_IAS_WD_Squawk(self, NwkId, ep, SquawkMode):
        SQUAWKMODE = {"disarmed": 0b00000000, "armed": 0b00000001}

        if SquawkMode not in SQUAWKMODE:
            Domoticz.Error("_write_IAS_WD_Squawk - %s/%s Unknown Squawk Mode: %s" % (NwkId, ep, SquawkMode))

        self.logging(
            "Debug",
            "write_IAS_WD_Squawk - %s/%s - Squawk Mode: %s >%s<" % (NwkId, ep, SquawkMode, SQUAWKMODE[SquawkMode]),
        )
        if SquawkMode == 'disarmed':
            squawk_mode = 0x01
            strobe = 0x00
            squawk_level = 0x00
            
        elif SquawkMode == 'armed':
            squawk_mode = 0x00
            strobe = 0x01
            squawk_level = 0x01
        
        zcl_ias_wd_command_squawk(self, ZIGATE_EP, ep, NwkId, squawk_mode, strobe, squawk_level, ackIsDisabled=False)

    def warningMode(self, NwkId, ep, mode="both", siren_level=0x01, warning_duration=0x01, strobe_duty=0x32, strobe_level=0x00):

        if mode in ( "siren", "both") and "Param" in self.ListOfDevices[ NwkId ] and "sirenLevel" in self.ListOfDevices[ NwkId ]["Param"]:
            siren_level = self.ListOfDevices[ NwkId ]["Param"]["sirenLevel"]  
        if mode in ( "strobe", "both") and "Param" in self.ListOfDevices[ NwkId ] and "sirenLevel" in self.ListOfDevices[ NwkId ]["Param"]:    
            strobe_duty = self.ListOfDevices[ NwkId ]["Param"]["strobeDutyCycle"] 
    
        strobe_mode, warning_mode, strobe_level, warning_duration = ias_sirene_mode( self, NwkId , mode , warning_duration)
        self.logging("Debug", f"warningMode - Mode: {bin(warning_mode)}, Duration: {warning_duration}, Duty: {strobe_duty}, Level: {strobe_level}")
        zcl_ias_wd_command_start_warning(self, ZIGATE_EP, ep, NwkId, warning_mode, strobe_mode, siren_level, warning_duration, strobe_duty, strobe_level, groupaddrmode=False, ackIsDisabled=False)

    def siren_both(self, NwkId, ep):
        self.logging("Debug", "Device Alarm On ( Siren + Strobe)")
        self.warningMode(NwkId, ep, "both")

    def siren_only(self, NwkId, ep):
        self.logging("Debug", "Device Alarm On (Siren)")
        self.warningMode(NwkId, ep, "siren")

    def strobe_only(self, NwkId, ep):
        self.logging("Debug", "Device Alarm On ( Strobe)")
        self.warningMode(NwkId, ep, "strobe")

    def alarm_on(self, NwkId, ep):
        self.siren_both(NwkId, ep)

    def alarm_off(self, NwkId, ep):
        self.logging("Debug", "Device Alarm Off")
        self.warningMode(NwkId, ep, "stop")

    def iaswd_develco_warning(self, NwkId, ep, sirenonoff):

        if sirenonoff not in ( "00", "01"):
            return 

        cmd = "00"
        Cluster = "0502"
        cluster_frame = 0b00010001
        sqn = get_and_inc_ZCL_SQN(self, NwkId)

        # Warnindg mode , Strobe, Sirene Level
        if "Param" not in self.ListOfDevices[ NwkId ] or "AlarmDuration" not in self.ListOfDevices[ NwkId ]["Param"]:
            warningduration = 0x0a
        else:
            warningduration = int(self.ListOfDevices[ NwkId ]["Param"]["AlarmDuration"])

        payload = "%02x" % cluster_frame + sqn + cmd + sirenonoff + "%04x" %struct.unpack(">H", struct.pack("H", warningduration))[0]
        raw_APS_request(self, NwkId, ep, Cluster, "0104", payload, zigpyzqn=sqn, zigate_ep=ZIGATE_EP, ackIsDisabled=False)
        return sqn

def ias_sirene_mode( self, NwkId , mode, warning_duration ):
    strobe_mode = warning_mode = strobe_level = 0x00
    if self.ListOfDevices[NwkId]["Model"] == "WarningDevice":
        if mode == "both":
            strobe_mode = 0x01
            warning_mode = 0x01
        elif mode == "siren":
            warning_mode = 0x01
        elif mode == "stop":
            strobe_mode = 0x00
            warning_mode = 0x00
        elif mode == "strobe":
            strobe_mode = 0x01
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
    if "Param" in self.ListOfDevices[NwkId]:
        if "alarmDuration" in self.ListOfDevices[NwkId]["Param"]:
            warning_duration = int(self.ListOfDevices[NwkId]["Param"]["alarmDuration"])

        if mode == "strobe" and "alarmStrobeCode" in self.ListOfDevices[NwkId]["Param"]:
            strobe_mode = int(self.ListOfDevices[NwkId]["Param"]["alarmStrobeCode"])

        if mode in ("siren","both") and "alarmSirenCode" in self.ListOfDevices[NwkId]["Param"]:
            warning_mode = int(self.ListOfDevices[NwkId]["Param"]["alarmSirenCode"])

        if mode in ("strobe", "both") and "strobeLevel" in self.ListOfDevices[ NwkId ]["Param"]:
            strobe_level = self.ListOfDevices[ NwkId ]["Param"]["strobeLevel"]        

    return strobe_mode, warning_mode, strobe_level, warning_duration

def format_list_attributes( self, ListOfAttributes):
    if not isinstance(ListOfAttributes, list):
        # We received only 1 attribute
        Attr = "%04x" % (ListOfAttributes)
        lenAttr = 1
    else:
        lenAttr = len(ListOfAttributes)
        Attr = "".join("%04x" % (x) for x in ListOfAttributes)
    return lenAttr, Attr


# Host -> Node
def set_IAS_CIE_Address(self, NwkId, Epout):
    # If the IAS CIE determines it wants to enroll the IAS Zone server, 
    # it SHALL send a Write Attribute command on the IAS Zone server’s IAS_CIE_Address attribute with its IEEE address.
    self.logging("Debug", f"Write Attribute command on the IAS Zone server’s IAS_CIE_Address for {NwkId}/{Epout}")
    if not self.ControllerIEEE:
        self.logging("Error", "readConfirmEnroll - Zigate IEEE not yet known")
        return
    cluster_id = "%04x" % 0x0500
    attribute = "%04x" % 0x0010
    data_type = "F0"  # ZigBee_IeeeAddress = 0xf0
    data = str(self.ControllerIEEE)
    zcl_write_attribute( self, NwkId, ZIGATE_EP, Epout, cluster_id, "00", "0000", attribute, data_type, data, ackIsDisabled=False )
    
def check_IAS_CIE_Address(self, NwkId, Epout):
    self.logging("Debug", f"Request IAS CIE Address of the device {NwkId}/{Epout}")
    lenAttr, attributes = format_list_attributes( self, 0x010)
    zcl_read_attribute(self, NwkId, ZIGATE_EP, Epout, "0500", "00", "00", "0010", lenAttr, attributes, ackIsDisabled=False)

def IAS_CIE_service_discovery( self, NwkId, Epout):
    # IAS CIE MAY perform service discovery
    # request Zone Information
    self.logging("Debug", f"IAS CIE service discovery, look for Zone Information {NwkId}/{Epout}")
    if not self.ControllerIEEE:
        self.logging("Error", "readConfirmEnroll - Zigate IEEE not yet known")
        return
    lenAttr, attributes = format_list_attributes( self, [0x0000, 0x0001, 0x0002])
    zcl_read_attribute(self, NwkId, ZIGATE_EP, Epout, "0500", "00", "00", "0000", lenAttr, attributes, ackIsDisabled=False)

def IAS_Zone_enrollment_response(self, NwkId, Ep, sqn, ZoneID):
    # The IAS Zone server SHALL change its ZoneState attribute to 0x01 (enrolled). 
    self.logging("Debug", f"IAS Zone_enroll_response for {NwkId}/{Ep}")
    if not self.ControllerIEEE:
        self.logging("Error", "IASZone_enroll_response_zoneIDzoneID - Zigate IEEE not yet known")
        return
    self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Ep"][ Ep ]["Status"] = "Enrolled"
    zcl_ias_zone_enroll_response(self, NwkId, ZIGATE_EP, Ep, "%02x" %ENROLL_RESPONSE_OK_CODE, "%02x" %ZoneID, sqn=sqn, ackIsDisabled=False)

def retreive_attributes(self, MsgData):
    
    attributes ={}
    idx = 12
    while idx < len(MsgData):
        MsgAttrID = MsgAttStatus = MsgAttType = MsgAttSize = MsgClusterData = ""
        MsgAttrID = MsgData[idx : idx + 4]
        attributes[ MsgAttrID ] = {}
        idx += 4
        MsgAttStatus = MsgData[idx : idx + 2]
        attributes[ MsgAttrID ]["Status"] = MsgAttStatus
        idx += 2
        if MsgAttStatus == "00":
            MsgAttType = MsgData[idx : idx + 2]
            idx += 2
            MsgAttSize = MsgData[idx : idx + 4]
            idx += 4
            size = int(MsgAttSize, 16) * 2
            MsgClusterData = MsgData[idx : idx + size]
            attributes[ MsgAttrID ]["Value"] = MsgClusterData
            idx += size
        elif len(MsgData[idx:]) == 6:
            # crap, lets finish it
            # Domoticz.Log("Crap Data: %s len: %s" %(MsgData[idx:], len(MsgData[idx:])))
            idx += 6
    
    return attributes


def is_device_enrollment_completed(self, NwkId):
    
    if "IAS" not in self.ListOfDevices[NwkId]:
        return False
    if "Auto-Enrollment" not in self.ListOfDevices[NwkId]["IAS"]:
        return False
    if "Ep" not in self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]:
        return False
    if "Status" in self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"] and self.ListOfDevices[ NwkId ]["IAS"]["Auto-Enrollment"]["Status"] == "Enrolled":
        return True

    return not any(("Status" in self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]["Ep"][x] and self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]["Ep"][x]["Status"] not in ("Enrolled", "Enrolled2")) for x in self.ListOfDevices[NwkId]["IAS"]["Auto-Enrollment"]["Ep"])
