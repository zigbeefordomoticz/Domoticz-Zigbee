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
    if mode == 0x00:
        self.pluginconf.pluginConf["ZiGateInRawMode"] = False
        self.pluginconf.pluginConf["ZiGateInHybridMode"] = False
    elif mode == 0x01:
        self.pluginconf.pluginConf["ZiGateInRawMode"] = True
        self.pluginconf.pluginConf["ZiGateInHybridMode"] = False
    elif mode == 0x02:
        self.pluginconf.pluginConf["ZiGateInHybridMode"] = True
        self.pluginconf.pluginConf["ZiGateInRawMode"] = True
    return send_zigatecmd_raw(self, "0002", "%02x" % mode)

def zigate_set_loglevel(self, loglevel):
    self.log.logging( "zigateCommand", "Debug","zigate_set_loglevel %s" %loglevel)

def zigate_firmware_default_response(self, enable="00"):
    self.log.logging( "zigateCommand", "Debug","zigate_firmware_default_response %s" %enable)
    return send_zigatecmd_raw(self, "0003", enable)

def zigate_get_nwk_state(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_nwk_state")
    if self.zigbee_communitation == "zigpy":
        # Should be done during zigpy layer startup()
        return
    return send_zigatecmd_raw(self, "0009", "")

def zigate_get_firmware_version(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_firmware_version")
    if self.zigbee_communitation == "zigpy":
        # Should be done during zigpy startup()
        return
        #return self.ControllerLink.sendData( "GET-FIRMWARE-VERSION", None) 
        #self.PDMready = True #TODO this must be done only if the initiatilisation went through
        #version = self.ControllerLink.get_zigpy_firmware_version()
        #self.FirmwareBranch = version['Branch']
        #self.FirmwareMajorVersion = version['Model']
        #self.FirmwareVersion = version['Firmware']
        #if self.FirmwareMajorVersion == "03":
        #    self.log.logging("Input", "Status", "ZiGate Classic PDM (legacy)")
        #    self.ZiGateModel = 1
        #elif self.FirmwareMajorVersion == "04":
        #    self.log.logging("Input", "Status", "ZiGate Classic PDM (OptiPDM)")
        #    self.ZiGateModel = 1
        #elif self.FirmwareMajorVersion == "05":
        #    self.log.logging("Input", "Status", "ZiGate+ (V2)")
        #    self.ZiGateModel = 2
        #return None
    return send_zigatecmd_raw(self, "0010", "")
    
def zigate_soft_reset(self):
    self.log.logging( "zigateCommand", "Debug","zigate_soft_reset")
    if self.zigbee_communitation == "zigpy":
        return self.ControllerLink.sendData( "SOFT-RESET", None) 
    return send_zigatecmd_raw(self, "0011", "" ) 
    
def zigate_erase_eeprom(self):
    self.log.logging( "zigateCommand", "Debug","zigate_erase_eeprom")
    if self.zigbee_communitation == "zigpy":
        return self.ControllerLink.sendData( "ERASE-PDM", None) 
    return send_zigatecmd_raw(self, "0012", "")

def zigate_get_list_active_devices(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_list_active_devices")
    if self.zigbee_communitation == "zigpy":
        return
    return send_zigatecmd_raw(self, "0015", "")
   
def zigate_set_time(self, timeUTC):
    self.log.logging( "zigateCommand", "Debug","zigate_set_time %s" %timeUTC)
    if self.zigbee_communitation == "zigpy":
        return self.ControllerLink.sendData( "SET-TIME", {"Param1": int(timeUTC,16)}) 
    return send_zigatecmd_raw(self, "0016", timeUTC)

def zigate_get_time(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_time")
    if self.zigbee_communitation == "zigpy":
        return self.ControllerLink.sendData( "GET-TIME", None) 
    return send_zigatecmd_raw(self, "0017", "")

def zigate_blueled(self, OnOff):
    self.log.logging( "zigateCommand", "Debug","zigate_blueled %s" %OnOff)
    if self.zigbee_communitation == "zigpy":
        return self.ControllerLink.sendData( "SET-LED", {"Param1": int(OnOff,16)}) 

    return send_zigatecmd_raw(self, "0018", OnOff)

def zigate_set_certificate(self, certification_code ):
    self.log.logging( "zigateCommand", "Debug","zigate_set_certificate %s" %certification_code)
    if self.zigbee_communitation == "zigpy":
        value = 'CE' if certification_code == 0x01 else 'FCC'
        return self.ControllerLink.sendData( "SET-CERTIFICATION", {"Param1": value}) 

    return send_zigatecmd_raw(self, "0019", certification_code)

def zigate_set_extended_PanID(self, extPanID):
    self.log.logging( "zigateCommand", "Debug","zigate_set_extended_PanID %s" %extPanID)
    if self.zigbee_communitation == "zigpy":
        return self.ControllerLink.sendData( "SET-EXTPANID", {"Param1": int(extPanID,16)}) 
    return send_zigatecmd_raw(self, "0020", extPanID)

def zigate_set_channel(self, mask):
    self.log.logging( "zigateCommand", "Debug","zigate_set_channel %s" %mask)
    if self.zigbee_communitation == "zigpy":
        return self.ControllerLink.sendData( "SET-CHANNEL", {"Param1": int(mask,16)}) 
    return send_zigatecmd_raw(self, "0021", mask)

def zigate_start_nwk(self):
    self.log.logging( "zigateCommand", "Debug","zigate_start_nwk")
    if self.zigbee_communitation == "zigpy":
        return
    return send_zigatecmd_raw(self, "0024", "")

def zigate_remove_device(self, target_short_addr, extended_addr):
    self.log.logging( "zigateCommand", "Debug","zigate_remove_device %s %s" %(target_short_addr, extended_addr))
    if self.zigbee_communitation == "zigpy":
        return
    return send_zigatecmd_raw(self, "0026", target_short_addr + extended_addr)

def zigate_set_tx_power(self, value):
    self.log.logging( "zigateCommand", "Debug","zigate_set_tx_power %s" %value)
    if self.zigbee_communitation == "zigpy":
        return self.ControllerLink.sendData( "SET-TX-POWER", {"Param1": int(value,16)}) 

    return send_zigatecmd_raw(self, "0806", value)

def zigate_get_tx_power(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_tx_power")
    if self.zigbee_communitation == "zigpy":
        return self.ControllerLink.sendData( "GET-EXTPANID", None) 
    return send_zigatecmd_raw(self, "0807", "")
