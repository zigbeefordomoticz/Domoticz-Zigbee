#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: low level commands manuf. specific ZiGate

"""

from Modules.sendZigateCommand import send_zigatecmd_raw


def zigate_set_mode(self, mode):
    self.log.logging( "zigateCommand", "Debug","zigate_set_mode %s" %mode)
    # Mode: cf. https://github.com/fairecasoimeme/ZiGate/pull/307
    #  0x00 - ZiGate in norml operation
    #  0x01 - ZiGate in RAW mode
    #  0x02 - ZiGate in Hybrid mode ( All inbound messages are received via 0x8002 in addition of the normal one)
    return send_zigatecmd_raw(self, "0002", "%02x" % mode)


def zigate_set_loglevel(self, loglevel):
    self.log.logging( "zigateCommand", "Debug","zigate_set_loglevel %s" %loglevel)


def zigate_firmware_default_response(self, enable="00"):
    self.log.logging( "zigateCommand", "Debug","zigate_firmware_default_response %s" %enable)
    return send_zigatecmd_raw(self, "0003", enable)

def zigate_get_nwk_state(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_nwk_state")
    if self.transport in ("ZigpyZNP", "ZigpyZiGate" ):
        self.ZigateIEEE = self.ZigateComm.get_zigate_ieee()
        self.ZigateNWKID =  self.ZigateComm.get_zigate_nwkid()
        self.ZigateExtendedPanId =  self.ZigateComm.get_zigate_extented_panId()
        self.ZigatePANId =  self.ZigateComm.get_zigate_panId()
        self.ZigateChannel = self.ZigateComm.get_zigate_channel()
        self.zigatedata["IEEE"] = self.ZigateIEEE
        self.zigatedata["Short Address"] = self.ZigateNWKID
        self.zigatedata["Channel"] = int(self.ZigateChannel, 16)
        self.zigatedata["PANID"] = self.ZigatePANId
        self.zigatedata["Extended PANID"] = self.ZigateExtendedPanId
        return
    return send_zigatecmd_raw(self, "0009", "")

def zigate_get_firmware_version(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_firmware_version")
    if self.transport in ("ZigpyZNP", "ZigpyZiGate" ):
        self.PDMready = True #TODO this must be done only if the initiatilisation went through
        version = self.ZigateComm.get_zigate_firmware_version()
        self.FirmwareBranch = version['Branch']
        self.FirmwareMajorVersion = version['Model']
        self.FirmwareVersion = version['Firmware']
        if self.FirmwareMajorVersion == "03":
            self.log.logging("Input", "Status", "ZiGate Classic PDM (legacy)")
            self.ZiGateModel = 1
        elif self.FirmwareMajorVersion == "04":
            self.log.logging("Input", "Status", "ZiGate Classic PDM (OptiPDM)")
            self.ZiGateModel = 1
        elif self.FirmwareMajorVersion == "05":
            self.log.logging("Input", "Status", "ZiGate+ (V2)")
            self.ZiGateModel = 2


        
        return None
    return send_zigatecmd_raw(self, "0010", "")
    
def zigate_soft_reset(self):
    self.log.logging( "zigateCommand", "Debug","zigate_soft_reset")
    return send_zigatecmd_raw(self, "0011", "" ) 
    
def zigate_erase_eeprom(self):
    self.log.logging( "zigateCommand", "Debug","zigate_erase_eeprom")
    return send_zigatecmd_raw(self, "0012", "")

def zigate_permit_joining_request(self, tgtnwkid , duration , significance):
    self.log.logging( "zdpCommand", "Log","zdp_permit_joining_request %s %s %s" %(tgtnwkid , duration , significance))
    return send_zigatecmd_raw(self, "0049", tgtnwkid + duration + significance)
       
def zigate_get_permit_joint_status(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_permit_joint_status")
    return send_zigatecmd_raw(self, "0014", "")  # Request Permit to Join status

def zigate_get_list_active_devices(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_list_active_devices")
    return send_zigatecmd_raw(self, "0015", "")
   
def zigate_set_time(self, timeUTC):
    self.log.logging( "zigateCommand", "Debug","zigate_set_time %s" %timeUTC)
    return send_zigatecmd_raw(self, "0016", timeUTC)

def zigate_get_time(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_time")
    return send_zigatecmd_raw(self, "0017", "")

def zigate_blueled(self, OnOff):
    self.log.logging( "zigateCommand", "Debug","zigate_blueled %s" %OnOff)
    return send_zigatecmd_raw(self, "0018", OnOff)

def zigate_set_certificate(self, certification_code ):
    self.log.logging( "zigateCommand", "Debug","zigate_set_certificate %s" %certification_code)
    return send_zigatecmd_raw(self, "0019", certification_code)

def zigate_set_extended_PanID(self, extPanID):
    self.log.logging( "zigateCommand", "Debug","zigate_set_extended_PanID %s" %extPanID)
    return send_zigatecmd_raw(self, "0020", extPanID)

def zigate_set_channel(self, mask):
    self.log.logging( "zigateCommand", "Debug","zigate_set_channel %s" %mask)
    return send_zigatecmd_raw(self, "0021", mask)

def zigate_start_nwk(self):
    self.log.logging( "zigateCommand", "Debug","zigate_start_nwk")
    return send_zigatecmd_raw(self, "0024", "")

def zigate_remove_device(self, target_short_addr, extended_addr):
    self.log.logging( "zigateCommand", "Debug","zigate_remove_device %s %s" %(target_short_addr, extended_addr))
    return send_zigatecmd_raw(self, "0026", target_short_addr + extended_addr)

def zigate_set_tx_power(self, value):
    self.log.logging( "zigateCommand", "Debug","zigate_set_tx_power %s" %value)
    return send_zigatecmd_raw(self, "0806", value)

def zigate_get_tx_power(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_tx_power")
    return send_zigatecmd_raw(self, "0807", "")
