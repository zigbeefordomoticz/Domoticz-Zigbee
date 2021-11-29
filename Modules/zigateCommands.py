#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: low level commands manuf. specific ZiGate

"""

from Modules.basicOutputs import sendZigateCmd

def zigate_get_nwk_state(self):
    sendZigateCmd(self, "0009", "")

def zigate_get_firmware_version(self):
    sendZigateCmd(self, "0010", "")
    
def zigate_soft_reset(self):
    sendZigateCmd(self, "0011", "" ) 
    
def zigate_erase_eeprom(self):
    sendZigateCmd(self, "0012", "")

def zigate_get_permit_joint_status(self):
    sendZigateCmd(self, "0014", "")  # Request Permit to Join status

def zigate_get_list_active_devices(self):
    sendZigateCmd(self, "0015", "")
    
def zigate_get_time(self):
    sendZigateCmd(self, "0017", "")

def zigate_set_certificate(self, certification_code ):
    sendZigateCmd(self, "0019", certification_code)
    
def zigate_remove_device(self, target_short_addr, extended_addr):
    sendZigateCmd(self, "0026", target_short_addr + extended_addr)