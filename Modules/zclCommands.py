#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: low level commands ZCL

    Description: 

"""

from Modules.sendZigateCommand import (send_zigatecmd_zcl_ack,
                                       send_zigatecmd_zcl_noack, sendZigateCmd)
from Modules.tools import Hex_Format
from Modules.zigateConsts import ZIGATE_EP

# Standard commands

WITHACK_DEFAULT = False

def zcl_configure_reporting_request(self, nwkid, epin, epout, cluster, direction, manufflag, manufcode, nbattribute, attributelist, withAck=WITHACK_DEFAULT):
    self.log.logging( "zclCommand", "Log","zcl_configure_reporting_request %s %s %s %s %s %s %s %s %s" %(
        nwkid, epin, epout, cluster, direction, manufflag, manufcode, nbattribute, attributelist ))
    data = epin + epout + cluster + direction + manufflag + manufcode + nbattribute+ attributelist
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "0120", data)
    return send_zigatecmd_zcl_noack(self, nwkid, "0120", data)    


# Cluster 0003
##############
def zcl_identify_send( self, nwkid, EPout, duration, withAck=WITHACK_DEFAULT):
    self.log.logging( "zclCommand", "Log","zcl_identify_send %s %s %s" %(nwkid, EPout, duration ))
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "0070", ZIGATE_EP + EPout + duration)
    return send_zigatecmd_zcl_noack(self, nwkid, "0070", ZIGATE_EP + EPout + duration)
    
def zcl_identify_trigger_effect( self, nwkid, EPout, effectId, effectGradient, withAck=WITHACK_DEFAULT):
    self.log.logging( "zclCommand", "Log","zcl_identify_trigger_effect %s %s %s %s" %(nwkid, EPout, effectId, effectGradient ))
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "00E0", nwkid+ ZIGATE_EP + EPout + effectId + effectGradient)
    return send_zigatecmd_zcl_noack(self, nwkid, "00E0", nwkid+ ZIGATE_EP + EPout + effectId + effectGradient)
   
# Cluster 0006
##############
def zcl_toggle(self, nwkid, EPout, withAck=WITHACK_DEFAULT):
    self.log.logging( "zclCommand", "Log","zcl_toggle %s %s" %(nwkid, EPout ))
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "0092", ZIGATE_EP + EPout + "02")
    return send_zigatecmd_zcl_noack(self, nwkid, "0092", ZIGATE_EP + EPout + "02")


def zcl_onoff_stop( self, nwkid, EPout, withAck=WITHACK_DEFAULT):
    self.log.logging( "zclCommand", "Log","zcl_onoff_stop %s %s" %(nwkid, EPout ))
    data = ZIGATE_EP + EPout
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "0083", data)
    return send_zigatecmd_zcl_noack(self, nwkid, "0083", data)
 
def zcl_onoff_on(self, nwkid, EPout, withAck=WITHACK_DEFAULT):
    self.log.logging( "zclCommand", "Log","zcl_onoff_on %s %s" %(nwkid, EPout ))
    data = ZIGATE_EP + EPout + "01"
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "0092", data)
    return send_zigatecmd_zcl_noack(self, nwkid, "0092", data)
    
def zcl_onoff_off_noeffect(self, nwkid, EPout, withAck=WITHACK_DEFAULT):
    self.log.logging( "zclCommand", "Log","zcl_onoff_off_noeffect %s %s" %(nwkid, EPout ))
    data = ZIGATE_EP + EPout + "00"
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "0092", data)
    return send_zigatecmd_zcl_noack(self, nwkid, "0092", data)
    
def zcl_onoff_off_witheffect(self, nwkid, EPout, effect, withAck=WITHACK_DEFAULT):
    self.log.logging( "zclCommand", "Log","zcl_onoff_off_witheffect %s %s %s" %(nwkid, EPout, effect ))
    data = ZIGATE_EP + EPout + effect
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "0094", data)
    return send_zigatecmd_zcl_noack(self, nwkid, "0094", data)
    
# Cluster 0008
##############
def zcl_level_move_to_level( self, nwkid, EPout, OnOff, level, transition="0000", withAck=WITHACK_DEFAULT):
    self.log.logging( "zclCommand", "Log","zcl_level_move_to_level %s %s %s %s %s" %(nwkid, EPout, OnOff, level, transition ))
    data = ZIGATE_EP + EPout + OnOff + level + transition
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "0081", data)
    return send_zigatecmd_zcl_noack(self, nwkid, "0081", data)


def zcl_move_to_level_with_onoff(self, nwkid, EPout, OnOff, level, transition="0000", withAck=WITHACK_DEFAULT):
    self.log.logging( "zclCommand", "Log","zcl_move_to_level_with_onoff %s %s %s %s %s" %(nwkid, EPout, OnOff, level, transition ))
    data = ZIGATE_EP + EPout + OnOff + level + transition
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "0081", data)
    return send_zigatecmd_zcl_noack(self, nwkid, "0081", data)

    
# Cluster 0102 ( Window Covering )
##################################
def zcl_window_covering_stop(self, nwkid, EPout, withAck=WITHACK_DEFAULT):
    # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
    self.log.logging( "zclCommand", "Log","zcl_window_covering_stop %s %s" %(nwkid, EPout ))
    data = ZIGATE_EP + EPout + "02"
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "00FA", data)
    return send_zigatecmd_zcl_noack(self, nwkid, "00FA", data)

def zcl_window_covering_on(self, nwkid, EPout, withAck=WITHACK_DEFAULT):
    # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
    self.log.logging( "zclCommand", "Log","zcl_window_covering_on %s %s" %(nwkid, EPout ))
    data = ZIGATE_EP + EPout + "00"
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "00FA", data)
    return send_zigatecmd_zcl_noack(self, nwkid, "00FA", data)

def zcl_window_covering_off(self, nwkid, EPout, withAck=WITHACK_DEFAULT):   
    # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
    self.log.logging( "zclCommand", "Log","zcl_window_covering_off %s %s" %(nwkid, EPout ))
    data = ZIGATE_EP + EPout + "01"
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "00FA", data)
    return send_zigatecmd_zcl_noack(self, nwkid, "00FA", data)

def zcl_window_coverting_level(self, nwkid, EPout, level, withAck=WITHACK_DEFAULT):
    self.log.logging( "zclCommand", "Log","zcl_window_coverting_level %s %s %s" %(nwkid, EPout, level ))
    data = ZIGATE_EP + EPout + "05" + level
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "00FA", data)
    return send_zigatecmd_zcl_noack(self, nwkid, "00FA", data)

# Cluster 0300   
##############
def zcl_move_to_colour_temperature( self, nwkid, EPout, temperature, transiton="0010", withAck=WITHACK_DEFAULT):
    self.log.logging( "zclCommand", "Log","zcl_move_to_colour_temperature %s %s %s %s" %(nwkid, EPout, temperature, transiton ))
    data = ZIGATE_EP + EPout + Hex_Format(4, temperature) + transiton
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "00C0", data)
    return send_zigatecmd_zcl_noack(self, nwkid, "00C0", data)

def zcl_move_hue_and_saturation(self, nwkid, EPout, hue, saturation, transition="0010", withAck=WITHACK_DEFAULT):
    self.log.logging( "zclCommand", "Log","zcl_move_hue_and_saturation %s %s %s %s %s" %(nwkid, EPout, hue, saturation, transition ))
    data = ZIGATE_EP + EPout + Hex_Format(2, hue) + Hex_Format(2, saturation) + transition
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "00B6", data)
    return send_zigatecmd_zcl_noack(self, nwkid, "00B6", data)
    
def zcl_move_to_colour(self, nwkid, EPout, colorX, colorY, transition="0010", withAck=WITHACK_DEFAULT):
    self.log.logging( "zclCommand", "Log","zcl_move_to_colour %s %s %s %s %s" %(nwkid, EPout, colorX, colorY, transition ))
    data = ZIGATE_EP + EPout + Hex_Format(4, colorX) + Hex_Format(4, colorY) + transition
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "00B7", data)
    return send_zigatecmd_zcl_noack(self, nwkid, "00B7", data)
