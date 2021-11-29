#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: low level commands ZCL

    Description: 

"""
import struct

from Modules.sendZigateCommand import (raw_APS_request, send_zigatecmd_zcl_ack,
                                       send_zigatecmd_zcl_noack)
from Modules.tools import Hex_Format, get_and_inc_SQN
from Modules.zigateConsts import ZIGATE_EP

# Standard commands

WITHACK_DEFAULT = False

def zcl_read_attribute(self, nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, lenAttr, Attr, ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug", "read_attribute %s %s %s %s %s %s %s %s %s" % (
        nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, lenAttr, Attr) )
    if self.pluginconf.pluginConf["RawReadAttribute"]:
        return rawaps_read_attribute_req( self, nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, Attr, ackIsDisabled )

    data = EpIn + EpOut + Cluster + direction + manufacturer_spec + manufacturer + "%02x" % lenAttr + Attr
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack( self, nwkid, "0100", data )
    return send_zigatecmd_zcl_ack( self, nwkid, "0100", data )


def rawaps_read_attribute_req( self, nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, Attr, ackIsDisabled=True ):
    self.log.logging( "zclCommand", "Debug", "rawaps_read_attribute_req %s %s %s %s %s %s %s %s" %(
        nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, Attr) )
    
    cmd = "00"  # Read Attribute Command Identifier

    # Cluster Frame:
    # 0b xxxx xxxx
    #           |- Frame Type: Cluster Specific (0x00)
    #          |-- Manufacturer Specific False
    #         |--- Command Direction: Client to Server (0)
    #       | ---- Disable default response: True
    #    |||- ---- Reserved : 0x000
    #

    cluster_frame = 0b00010000
    if manufacturer_spec == "01":
        cluster_frame += 0b00000100
        
    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_SQN(self, nwkid)
    payload = fcf
    if manufacturer_spec == "01":
        payload += manufacturer_spec + manufacturer[4:2] + manufacturer[0:2]
    payload += sqn + cmd
    idx = 0
    while idx < len(Attr):
        attribute = Attr[idx : idx + 4]
        idx += 4
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(attribute, 16)))[0]
    return raw_APS_request(self, nwkid, EpOut, Cluster, "0104", payload, zigate_ep=EpIn, ackIsDisabled=ackIsDisabled)


def zcl_write_attribute( self, nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled=True ):
    self.log.logging("zclCommand", "Debug", "zcl_write_attribute %s %s %s %s %s %s %s %s %s" % (
        nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data))
    #  write_attribute unicast , all with ack in < 31d firmware, ack/noack works since 31d
    #
    direction = "00"
    if data_type == "42":  # String
        # In case of Data Type 0x42 ( String ), we have to add the length of string before the string.
        data = "%02x" % (len(data) // 2) + data

    lenght = "01"  # Only 1 attribute
    datas = EPin + EPout + cluster
    datas += direction + manuf_spec + manuf_id
    datas += lenght + attribute + data_type + data
    
    if self.pluginconf.pluginConf["RawWritAttribute"]:
        return rawaps_write_attribute_req( self, nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled )

    # ATTENTION "0110" with firmware 31c are always call with Ack (overwriten by firmware)
    # if ackIsDisabled:
    #    i_sqn = send_zigatecmd_zcl_noack(self, key, "0110", str(datas))
    # else:
    #    i_sqn = send_zigatecmd_zcl_ack(self, key, "0110", str(datas))
    # For now send Write Attribute ALWAYS with Ack.
    return send_zigatecmd_zcl_ack(self, nwkid, "0110", str(datas))


def zcl_write_attributeNoResponse(self, nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data):
    self.log.logging("zclCommand", "Debug", "zcl_write_attributeNoResponse %s %s %s %s %s %s %s %s %s" %(
        nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data))
    direction = "00"
    if data_type == "42":  # String
        # In case of Data Type 0x42 ( String ), we have to add the length of string before the string.
        data = "%02x" % (len(data) // 2) + data
    lenght = "01"  # Only 1 attribute
    datas = ZIGATE_EP + EPout + cluster
    datas += direction + manuf_spec + manuf_id
    datas += lenght + attribute + data_type + data
    return send_zigatecmd_zcl_noack(self, nwkid, "0113", str(datas))


def rawaps_write_attribute_req( self, nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled=True ):
    self.log.logging("zclCommand", "Debug", "rawaps_write_attribute_req %s %s %s %s %s %s %s %s %s" %(
        nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data))
    cmd = "02" 
    cluster_frame = 0b00010000
    if manuf_spec == "01":
        cluster_frame += 0b00000100
    fcf = "%02x" % cluster_frame
    sqn = get_and_inc_SQN(self, nwkid)
    payload = fcf
    if manuf_spec == "01":
        payload += manuf_spec + "%04x" % struct.unpack(">H", struct.pack("H", int(manuf_id, 16)))[0]
    payload += sqn + cmd
    payload += "%04x" % struct.unpack(">H", struct.pack("H", int(attribute, 16)))[0]
    payload += data_type
    if data_type in ("10", "18", "20", "28", "30"):
        payload += data
    elif data_type in ("09", "16", "21", "29", "31"):
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(data, 16)))[0]
    elif data_type in ("22", "2a"):
        payload += "%06x" % struct.unpack(">i", struct.pack("I", int(data, 16)))[0]
    elif data_type in ("23", "2b", "39"):
        payload += "%08x" % struct.unpack(">f", struct.pack("I", int(data, 16)))[0]
    else:
        payload += data
    return raw_APS_request(self, nwkid, EPout, cluster, "0104", payload, zigate_ep=EPin, ackIsDisabled=ackIsDisabled)


def zcl_configure_reporting_request(self, nwkid, epin, epout, cluster, direction, manufflag, manufcode, nbattribute, attributelist, ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_configure_reporting_request %s %s %s %s %s %s %s %s %s" %(
        nwkid, epin, epout, cluster, direction, manufflag, manufcode, nbattribute, attributelist ))
    data = epin + epout + cluster + direction + manufflag + manufcode + nbattribute+ attributelist
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0120", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0120", data)    

def zcl_read_report_config_request(self, nwkid , epin , epout , cluster, direction , manuf_specific , manuf_code , nb_attribute, attribute_list, ackIsDisabled=True):
    data = epin + epout + cluster + direction + nb_attribute + manuf_specific + manuf_code + attribute_list
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0122", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0122", data)       
    
# Cluster 0003
##############
def zcl_identify_send( self, nwkid, EPout, duration, ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_identify_send %s %s %s" %(nwkid, EPout, duration ))
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0070", ZIGATE_EP + EPout + duration)
    return send_zigatecmd_zcl_ack(self, nwkid, "0070", ZIGATE_EP + EPout + duration)
    
def zcl_identify_trigger_effect( self, nwkid, EPout, effectId, effectGradient, ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_identify_trigger_effect %s %s %s %s" %(nwkid, EPout, effectId, effectGradient ))
    if ackIsDisabled:
        return send_zigatecmd_zcl_ack(self, nwkid, "00E0", nwkid+ ZIGATE_EP + EPout + effectId + effectGradient)
    return send_zigatecmd_zcl_noack(self, nwkid, "00E0", nwkid+ ZIGATE_EP + EPout + effectId + effectGradient)
   
# Cluster 0006
##############
def zcl_toggle(self, nwkid, EPout, ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_toggle %s %s" %(nwkid, EPout ))
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0092", ZIGATE_EP + EPout + "02")
    return send_zigatecmd_zcl_ack(self, nwkid, "0092", ZIGATE_EP + EPout + "02")


def zcl_onoff_stop( self, nwkid, EPout, ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_onoff_stop %s %s" %(nwkid, EPout ))
    data = ZIGATE_EP + EPout
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0083", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0083", data)
 
def zcl_onoff_on(self, nwkid, EPout, ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_onoff_on %s %s" %(nwkid, EPout ))
    data = ZIGATE_EP + EPout + "01"
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0092", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0092", data)
    
def zcl_onoff_off_noeffect(self, nwkid, EPout, ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_onoff_off_noeffect %s %s" %(nwkid, EPout ))
    data = ZIGATE_EP + EPout + "00"
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0092", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0092", data)
    
def zcl_onoff_off_witheffect(self, nwkid, EPout, effect, ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_onoff_off_witheffect %s %s %s" %(nwkid, EPout, effect ))
    data = ZIGATE_EP + EPout + effect
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0094", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0094", data)
    
# Cluster 0008
##############
def zcl_level_move_to_level( self, nwkid, EPout, OnOff, level, transition="0000", ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_level_move_to_level %s %s %s %s %s" %(nwkid, EPout, OnOff, level, transition ))
    data = ZIGATE_EP + EPout + OnOff + level + transition
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0081", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0081", data)


def zcl_move_to_level_with_onoff(self, nwkid, EPout, OnOff, level, transition="0000", ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_move_to_level_with_onoff %s %s %s %s %s" %(nwkid, EPout, OnOff, level, transition ))
    data = ZIGATE_EP + EPout + OnOff + level + transition
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0081", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0081", data)

    
# Cluster 0102 ( Window Covering )
##################################
def zcl_window_covering_stop(self, nwkid, EPout, ackIsDisabled=True):
    # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
    self.log.logging( "zclCommand", "Debug","zcl_window_covering_stop %s %s" %(nwkid, EPout ))
    data = ZIGATE_EP + EPout + "02"
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "00FA", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "00FA", data)

def zcl_window_covering_on(self, nwkid, EPout, ackIsDisabled=True):
    # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
    self.log.logging( "zclCommand", "Debug","zcl_window_covering_on %s %s" %(nwkid, EPout ))
    data = ZIGATE_EP + EPout + "00"
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "00FA", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "00FA", data)

def zcl_window_covering_off(self, nwkid, EPout, ackIsDisabled=True):   
    # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
    self.log.logging( "zclCommand", "Debug","zcl_window_covering_off %s %s" %(nwkid, EPout ))
    data = ZIGATE_EP + EPout + "01"
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "00FA", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "00FA", data)

def zcl_window_coverting_level(self, nwkid, EPout, level, ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_window_coverting_level %s %s %s" %(nwkid, EPout, level ))
    data = ZIGATE_EP + EPout + "05" + level
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "00FA", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "00FA", data)

# Cluster 0300   
##############
def zcl_move_to_colour_temperature( self, nwkid, EPout, temperature, transiton="0010", ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_move_to_colour_temperature %s %s %s %s" %(nwkid, EPout, temperature, transiton ))
    data = ZIGATE_EP + EPout + Hex_Format(4, temperature) + transiton
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "00C0", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "00C0", data)

def zcl_move_hue_and_saturation(self, nwkid, EPout, hue, saturation, transition="0010", ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_move_hue_and_saturation %s %s %s %s %s" %(nwkid, EPout, hue, saturation, transition ))
    data = ZIGATE_EP + EPout + Hex_Format(2, hue) + Hex_Format(2, saturation) + transition
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "00B6", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "00B6", data)
    
def zcl_move_to_colour(self, nwkid, EPout, colorX, colorY, transition="0010", ackIsDisabled=True):
    self.log.logging( "zclCommand", "Debug","zcl_move_to_colour %s %s %s %s %s" %(nwkid, EPout, colorX, colorY, transition ))
    data = ZIGATE_EP + EPout + Hex_Format(4, colorX) + Hex_Format(4, colorY) + transition
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "00B7", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "00B7", data)
