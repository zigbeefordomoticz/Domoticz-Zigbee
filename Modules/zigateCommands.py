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
    if self.zigbee_communication == "zigpy":
        self.log.logging( "zigateCommand", "Debug","zigate_set_mode %s not implemennted in zigpy" %mode)
        return
    self.log.logging( "zigateCommand", "Debug","zigate_set_mode %s" %mode)
    # Mode: cf. https://github.com/fairecasoimeme/ZiGate/pull/307
    #  0x00 - ZiGate in norml operation
    #  0x01 - ZiGate in RAW mode
    #  0x02 - ZiGate in Hybrid mode ( All inbound messages are received via 0x8002 in addition of the normal one)
    if mode == 0x00:
        self.pluginconf.pluginConf["ControllerInRawMode"] = False
        self.pluginconf.pluginConf["ControllerInHybridMode"] = False
    elif mode == 0x01:
        self.pluginconf.pluginConf["ControllerInRawMode"] = True
        self.pluginconf.pluginConf["ControllerInHybridMode"] = False
    elif mode == 0x02:
        self.pluginconf.pluginConf["ControllerInHybridMode"] = True
        self.pluginconf.pluginConf["ControllerInRawMode"] = False
    return send_zigatecmd_raw(self, "0002", "%02x" % mode)

def zigate_set_loglevel(self, loglevel):
    if self.zigbee_communication == "zigpy":
        self.log.logging( "zigateCommand", "Debug","zigate_set_loglevel %s not implemennted in zigpy" %loglevel)
        return
    self.log.logging( "zigateCommand", "Debug","zigate_set_loglevel %s" %loglevel)

def zigate_firmware_default_response(self, enable="00"):
    if self.zigbee_communication == "zigpy":
        self.log.logging( "zigateCommand", "Debug","zigate_firmware_default_response %s not implemennted in zigpy" %enable)
        return
    self.log.logging( "zigateCommand", "Debug","zigate_firmware_default_response %s" %enable)
    return send_zigatecmd_raw(self, "0003", enable)

def zigate_get_nwk_state(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_nwk_state")
    if self.zigbee_communication == "zigpy":
        # Should be done during zigpy layer startup()
        return self.ControllerLink.sendData( "REQ-NWK-STATUS", None) 
    return send_zigatecmd_raw(self, "0009", "")

def zigate_get_firmware_version(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_firmware_version")
    if self.zigbee_communication == "zigpy":
        # Should be done during zigpy startup()
        return
    return send_zigatecmd_raw(self, "0010", "")
    
def zigate_soft_reset(self):
    self.log.logging( "zigateCommand", "Debug","zigate_soft_reset")
    if self.zigbee_communication == "zigpy":
        return self.ControllerLink.sendData( "SOFT-RESET", None) 
    return send_zigatecmd_raw(self, "0011", "" ) 
    
def zigate_erase_eeprom(self):
    self.log.logging( "zigateCommand", "Debug","zigate_erase_eeprom")
    if self.zigbee_communication == "zigpy":
        return self.ControllerLink.sendData( "ERASE-PDM", None) 
    return send_zigatecmd_raw(self, "0012", "")

def zigate_get_list_active_devices(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_list_active_devices")
    if self.zigbee_communication == "zigpy":
        return
    return send_zigatecmd_raw(self, "0015", "")
   
def zigate_set_time(self, timeUTC):
    self.log.logging( "zigateCommand", "Debug","zigate_set_time %s" %timeUTC)
    if self.zigbee_communication == "zigpy":
        return self.ControllerLink.sendData( "SET-TIME", {"Param1": int(timeUTC,16)}) 
    return send_zigatecmd_raw(self, "0016", timeUTC)

def zigate_get_time(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_time")
    if self.zigbee_communication == "zigpy":
        return self.ControllerLink.sendData( "GET-TIME", None) 
    return send_zigatecmd_raw(self, "0017", "")

def zigate_blueled(self, OnOff):
    self.log.logging( "zigateCommand", "Debug","zigate_blueled %s" %OnOff)
    if self.zigbee_communication == "zigpy":
        return self.ControllerLink.sendData( "SET-LED", {"Param1": int(OnOff,16)}) 

    return send_zigatecmd_raw(self, "0018", OnOff)

def zigate_set_certificate(self, certification_code ):
    self.log.logging( "zigateCommand", "Debug","zigate_set_certificate %s" %certification_code)
    if self.zigbee_communication == "zigpy":
        value = 'FCC' if certification_code == '02' else 'CE'
        self.log.logging( "zigateCommand", "Debug","zigate_set_certificate value: %s" %value)
        return self.ControllerLink.sendData( "SET-CERTIFICATION", {"Param1": value}) 

    return send_zigatecmd_raw(self, "0019", certification_code)

def zigate_set_extended_PanID(self, extPanID):
    self.log.logging( "zigateCommand", "Debug","zigate_set_extended_PanID %s" %extPanID)
    if self.zigbee_communication == "zigpy":
        return self.ControllerLink.sendData( "SET-EXTPANID", {"Param1": int(extPanID,16)}) 
    return send_zigatecmd_raw(self, "0020", extPanID)

def zigate_set_channel(self, mask):
    self.log.logging( "zigateCommand", "Debug","zigate_set_channel %s" %mask)
    if self.zigbee_communication == "zigpy":
        return self.ControllerLink.sendData( "SET-CHANNEL", {"Param1": int(mask,16)}) 
    return send_zigatecmd_raw(self, "0021", mask)

def zigate_start_nwk(self):
    self.log.logging( "zigateCommand", "Debug","zigate_start_nwk")
    if self.zigbee_communication == "zigpy":
        return
    return send_zigatecmd_raw(self, "0024", "")

def zigate_remove_device(self, target_short_addr, extended_addr):
    self.log.logging( "zigateCommand", "Debug","zigate_remove_device %s %s" %(target_short_addr, extended_addr))
    if self.zigbee_communication == "zigpy":
        return self.ControllerLink.sendData( "REMOVE-DEVICE", {"Param1": int(extended_addr,16)}) 
    return send_zigatecmd_raw(self, "0026", target_short_addr + extended_addr)

def zigate_set_tx_power(self, value):
    self.log.logging( "zigateCommand", "Debug","zigate_set_tx_power %s" %value)
    return send_zigatecmd_raw(self, "0806", value)

def zigate_get_tx_power(self):
    self.log.logging( "zigateCommand", "Debug","zigate_get_tx_power")
    if self.zigbee_communication == "zigpy":
        return self.ControllerLink.sendData( "GET-EXTPANID", None) 
    return send_zigatecmd_raw(self, "0807", "")
