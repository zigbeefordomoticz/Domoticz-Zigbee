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
    # Mode: cf. https://github.com/fairecasoimeme/ZiGate/pull/307
    #  0x00 - ZiGate in norml operation
    #  0x01 - ZiGate in RAW mode
    #  0x02 - ZiGate in Hybrid mode ( All inbound messages are received via 0x8002 in addition of the normal one)
    return send_zigatecmd_raw(self, "0002", "%02x" % mode)

def zigate_set_loglevel(self, loglevel):
    pass

def zigate_firmware_default_response(self, enable="00"):
    return send_zigatecmd_raw(self, "0003", enable)

def zigate_get_nwk_state(self):
    return send_zigatecmd_raw(self, "0009", "")

def zigate_get_firmware_version(self):
    return send_zigatecmd_raw(self, "0010", "")
    
def zigate_soft_reset(self):
    return send_zigatecmd_raw(self, "0011", "" ) 
    
def zigate_erase_eeprom(self):
    return send_zigatecmd_raw(self, "0012", "")

def zigate_get_permit_joint_status(self):
    return send_zigatecmd_raw(self, "0014", "")  # Request Permit to Join status

def zigate_get_list_active_devices(self):
    return send_zigatecmd_raw(self, "0015", "")
   
def zigate_set_time(self, timeUTC):
    return send_zigatecmd_raw(self, "0016", timeUTC)

def zigate_get_time(self):
    return send_zigatecmd_raw(self, "0017", "")

def zigate_blueled(self, OnOff):
    return send_zigatecmd_raw(self, "0018", OnOff)

def zigate_set_certificate(self, certification_code ):
    return send_zigatecmd_raw(self, "0019", certification_code)

def zigate_set_extended_PanID(self, extPanID):
    return send_zigatecmd_raw(self, "0020", extPanID)

def zigate_set_channel(self, mask):
    return send_zigatecmd_raw(self, "0021", mask)

def zigate_start_nwk(self):
    return send_zigatecmd_raw(self, "0024", "")

def zigate_remove_device(self, target_short_addr, extended_addr):
    return send_zigatecmd_raw(self, "0026", target_short_addr + extended_addr)

def zigate_set_tx_power(self, value):
    return send_zigatecmd_raw(self, "0806", value)

def zigate_get_tx_power(self):
    return send_zigatecmd_raw(self, "0807", "")
