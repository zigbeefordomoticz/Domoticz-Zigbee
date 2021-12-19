#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: low level commands ZCL

    Description: 

"""


from Modules.sendZigateCommand import (send_zigatecmd_raw,
                                       send_zigatecmd_zcl_ack,
                                       send_zigatecmd_zcl_noack)
from Modules.zclRawCommands import (raw_zcl_zcl_onoff,
                                    rawaps_read_attribute_req,
                                    rawaps_write_attribute_req,
                                    zcl_raw_level_move_to_level,
                                    zcl_raw_move_color)
from Modules.zigateConsts import ADDRESS_MODE, ZIGATE_EP

DEFAULT_ACK_MODE = False

# Standard commands



def zcl_read_attribute(self, nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, lenAttr, Attr, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug", "read_attribute %s %s %s %s %s %s %s %s %s" % (
        nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, lenAttr, Attr) )
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return rawaps_read_attribute_req( self, nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, Attr, ackIsDisabled )

    data = EpIn + EpOut + Cluster + direction + manufacturer_spec + manufacturer + "%02x" % lenAttr + Attr
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack( self, nwkid, "0100", data )
    return send_zigatecmd_zcl_ack( self, nwkid, "0100", data )


def zcl_write_attribute( self, nwkid, EPin, EPout, cluster, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled=DEFAULT_ACK_MODE ):
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
    
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
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


def zcl_configure_reporting_request(self, nwkid, epin, epout, cluster, direction, manufflag, manufcode, nbattribute, attributelist, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_configure_reporting_request %s %s %s %s %s %s %s %s %s" %(
        nwkid, epin, epout, cluster, direction, manufflag, manufcode, nbattribute, attributelist ))
    data = epin + epout + cluster + direction + manufflag + manufcode + nbattribute+ attributelist
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0120", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0120", data)    


def zcl_read_report_config_request(self, nwkid , epin , epout , cluster, direction , manuf_specific , manuf_code , nb_attribute, attribute_list, ackIsDisabled=DEFAULT_ACK_MODE):
    data = epin + epout + cluster + direction + nb_attribute + manuf_specific + manuf_code + attribute_list
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0122", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0122", data)       
  
# Cluster 0003
##############
def zcl_identify_send( self, nwkid, EPout, duration, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_identify_send %s %s %s" %(nwkid, EPout, duration ))
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0070", ZIGATE_EP + EPout + duration)
    return send_zigatecmd_zcl_ack(self, nwkid, "0070", ZIGATE_EP + EPout + duration)
    
def zcl_identify_trigger_effect( self, nwkid, EPout, effectId, effectGradient, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_identify_trigger_effect %s %s %s %s" %(nwkid, EPout, effectId, effectGradient ))
    if ackIsDisabled:
        return send_zigatecmd_zcl_ack(self, nwkid, "00E0", nwkid+ ZIGATE_EP + EPout + effectId + effectGradient)
    return send_zigatecmd_zcl_noack(self, nwkid, "00E0", nwkid+ ZIGATE_EP + EPout + effectId + effectGradient)

def zcl_group_identify_trigger_effect(self, nwkid, epin, epout, effectId, effectGradient):
    self.log.logging( "zclCommand", "Debug","zcl_group_identify_trigger_effect %s %s %s %s" %(nwkid, epout, effectId, effectGradient ))
    data = "%02d" % ADDRESS_MODE["group"] + nwkid + epin + epout + effectId + effectGradient
    return send_zigatecmd_raw( self, "00E0", data )

# Cluster 0004 - Groups
##############
def zcl_add_group_membership( self, nwkid , epin , epout , GrpId, ackIsDisabled=DEFAULT_ACK_MODE):
    
    data = epin + epout + GrpId
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0060", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0060", data)    


def zcl_check_group_member_ship(self, nwkid, epin, epout, GrpId, ackIsDisabled=DEFAULT_ACK_MODE):
    
    data = epin + epout + GrpId
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0061", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0061", data)


def zcl_look_for_group_member_ship(self, nwkid, epin, epout, nbgroup, group_list, ackIsDisabled=DEFAULT_ACK_MODE):
    
    data = epin + epout + nbgroup + group_list
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0062", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0062", data)


def zcl_remove_group_member_ship(self, nwkid, epin, epout, GrpId, ackIsDisabled=DEFAULT_ACK_MODE):
    
    data = epin + epout + GrpId
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0063", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0063", data)


def zcl_remove_all_groups( self, nwkid, epin, epout, ackIsDisabled=DEFAULT_ACK_MODE):
    data = epin + epout
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0062", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0064", data)


def zcl_send_group_member_ship_identify(self, nwkid, epin, epout, goup_addr, ackIsDisabled=DEFAULT_ACK_MODE):
    data = epin + epout + goup_addr
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0065", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0065", data)



  
# Cluster 0006
##############
def zcl_toggle(self, nwkid, EPout, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_toggle %s %s" %(nwkid, EPout ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return raw_zcl_zcl_onoff(self, nwkid, ZIGATE_EP, EPout, "Toggle", groupaddrmode=False, ackIsDisabled=ackIsDisabled)
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0092", ZIGATE_EP + EPout + "02")
    return send_zigatecmd_zcl_ack(self, nwkid, "0092", ZIGATE_EP + EPout + "02")

def zcl_onoff_stop( self, nwkid, EPout, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_onoff_stop %s %s" %(nwkid, EPout ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return raw_zcl_zcl_onoff(self, nwkid, ZIGATE_EP, EPout, "Stop", groupaddrmode=False, ackIsDisabled=ackIsDisabled)
    data = ZIGATE_EP + EPout
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0083", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0083", data)
    
def zcl_onoff_on(self, nwkid, EPout, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_onoff_on %s %s" %(nwkid, EPout ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return raw_zcl_zcl_onoff(self, nwkid, ZIGATE_EP, EPout, "On", groupaddrmode=False, ackIsDisabled=ackIsDisabled)
    data = ZIGATE_EP + EPout + "01"
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0092", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0092", data)
    
def zcl_onoff_off_noeffect(self, nwkid, EPout, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_onoff_off_noeffect %s %s" %(nwkid, EPout ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return raw_zcl_zcl_onoff(self, nwkid, ZIGATE_EP, EPout, "Off", groupaddrmode=False, ackIsDisabled=ackIsDisabled)
    data = ZIGATE_EP + EPout + "00"
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0092", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0092", data)
    
def zcl_onoff_off_witheffect(self, nwkid, EPout, effect, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_onoff_off_witheffect %s %s %s" %(nwkid, EPout, effect ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return raw_zcl_zcl_onoff(self, nwkid, ZIGATE_EP, EPout, "Off", effect=effect, groupaddrmode=False, ackIsDisabled=ackIsDisabled)
    data = ZIGATE_EP + EPout + effect
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0094", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0094", data)
    
def zcl_group_toggle(self, nwkid, epin, EPout):
    self.log.logging( "zclCommand", "Log","zcl_group_toggle %s %s" %(nwkid, EPout ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return raw_zcl_zcl_onoff(self, nwkid, epin, EPout, "Toggle", groupaddrmode=True)
    data = "%02d" % ADDRESS_MODE["group"] + nwkid + epin + EPout + "02"
    return send_zigatecmd_raw( self, "0092", data )
    
def zcl_group_onoff_stop( self, nwkid, epin, EPout):
    self.log.logging( "zclCommand", "Log","zcl_group_onoff_stop %s %s" %(nwkid, EPout ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return raw_zcl_zcl_onoff(self, nwkid, epin, EPout, "Stop", groupaddrmode=True)
    data = "%02d" % ADDRESS_MODE["group"] + nwkid + epin + EPout
    return send_zigatecmd_raw( self, "0083", data )
    
def zcl_group_onoff_on(self, nwkid, epin, EPout):
    self.log.logging( "zclCommand", "Debug","zcl_group_onoff_on %s %s" %(nwkid, EPout ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return raw_zcl_zcl_onoff(self, nwkid, epin, EPout, "On", groupaddrmode=True)
    data = "%02d" % ADDRESS_MODE["group"] + nwkid + epin + EPout + "01"
    return send_zigatecmd_raw( self, "0092", data )

def zcl_group_onoff_off_noeffect(self, nwkid, epin, EPout):
    self.log.logging( "zclCommand", "Log","zcl_group_onoff_off_noeffect %s %s %s" %(nwkid, epin, EPout ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return raw_zcl_zcl_onoff(self, nwkid, epin, EPout, "Off", groupaddrmode=True)
    data = "%02d" % ADDRESS_MODE["group"] + nwkid + epin + EPout + "00"
    return send_zigatecmd_raw( self, "0092", data )
    
def zcl_group_onoff_off_witheffect(self, nwkid, epin, EPout, effect):
    self.log.logging( "zclCommand", "Log","zcl_group_onoff_off_witheffect %s %s %s" %(nwkid, EPout, effect ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return raw_zcl_zcl_onoff(self, nwkid, epin, EPout, "Off", effect=effect, groupaddrmode=True)
    data = "%02d" % ADDRESS_MODE["group"] + nwkid + epin + EPout + effect
    return send_zigatecmd_raw( self, "0094", data )
    

 
# Cluster 0008
##############
def zcl_level_move_to_level( self, nwkid, EPout, OnOff, level, transition="0000", ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_level_move_to_level %s %s %s %s %s" %(nwkid, EPout, OnOff, level, transition ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return zcl_raw_level_move_to_level( self, nwkid, ZIGATE_EP, EPout, "MovetoLevel", level,transition, ackIsDisabled=ackIsDisabled)
    data = ZIGATE_EP + EPout + OnOff + level + transition
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0081", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0081", data)
    
def zcl_group_level_move_to_level( self, nwkid, epin, EPout, OnOff, level, transition="0000"):
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return zcl_raw_level_move_to_level( self, nwkid, ZIGATE_EP, EPout, "MovetoLevel", level,transition,  groupaddrmode=True)
    data = "%02d" % ADDRESS_MODE["group"] + nwkid + epin + EPout + OnOff + level + transition
    return send_zigatecmd_raw( self, "0081", data )
    
def zcl_move_to_level_with_onoff(self, nwkid, EPout, OnOff, level, transition="0000", ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_move_to_level_with_onoff %s %s %s %s %s" %(nwkid, EPout, OnOff, level, transition ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return zcl_raw_level_move_to_level( self, nwkid, ZIGATE_EP, EPout, "MovetoLevelWithOnOff", level,transition, ackIsDisabled=ackIsDisabled)
    data = ZIGATE_EP + EPout + OnOff + level + transition
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0081", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0081", data)

def zcl_group_move_to_level_with_onoff(self, nwkid, EPout, OnOff, level, transition="0000", ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_move_to_level_with_onoff %s %s %s %s %s" %(nwkid, EPout, OnOff, level, transition ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        return zcl_raw_level_move_to_level( self, nwkid, ZIGATE_EP, EPout, "MovetoLevelWithOnOff", level,transition="0010", groupaddrmode=True)
    data = ZIGATE_EP + EPout + OnOff + level + transition
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "0081", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "0081", data)
    
# Cluster 0102 ( Window Covering )
##################################
def zcl_window_covering_stop(self, nwkid, EPout, ackIsDisabled=DEFAULT_ACK_MODE):
    # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
    self.log.logging( "zclCommand", "Debug","zcl_window_covering_stop %s %s" %(nwkid, EPout ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        pass
    data = ZIGATE_EP + EPout + "02"
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "00FA", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "00FA", data)

def zcl_group_window_covering_stop(self, nwkid, epin, EPout):
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        pass
    data = "%02d" % ADDRESS_MODE["group"] + nwkid + epin + EPout + "02"
    return send_zigatecmd_raw( self, "00FA", data )


def zcl_window_covering_on(self, nwkid, EPout, ackIsDisabled=DEFAULT_ACK_MODE):
    # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
    self.log.logging( "zclCommand", "Debug","zcl_window_covering_on %s %s" %(nwkid, EPout ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        pass
    data = ZIGATE_EP + EPout + "00"
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "00FA", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "00FA", data)


def zcl_group_window_covering_on(self, nwkid, epin, EPout):
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        pass
    data = "%02d" % ADDRESS_MODE["group"] + nwkid + epin + EPout + "00"
    return send_zigatecmd_raw( self, "00FA", data )


def zcl_window_covering_off(self, nwkid, EPout, ackIsDisabled=DEFAULT_ACK_MODE):   
    # https://github.com/fairecasoimeme/ZiGate/issues/125#issuecomment-456085847
    self.log.logging( "zclCommand", "Debug","zcl_window_covering_off %s %s" %(nwkid, EPout ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        pass
    data = ZIGATE_EP + EPout + "01"
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "00FA", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "00FA", data)


def zcl_group_window_covering_off(self, nwkid, epin, EPout):
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        pass
    data = "%02d" % ADDRESS_MODE["group"] + nwkid + epin + EPout + "01"
    return send_zigatecmd_raw( self, "00FA", data )


def zcl_window_coverting_level(self, nwkid, EPout, level, ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_window_coverting_level %s %s %s" %(nwkid, EPout, level ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        pass
    data = ZIGATE_EP + EPout + "05" + level
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "00FA", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "00FA", data)


def zcl_group_window_covering_level(self, nwkid, epin, EPout, level):
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:
        pass
    data = "%02d" % ADDRESS_MODE["group"] + nwkid + epin + EPout + "05"
    return send_zigatecmd_raw( self, "00FA", data )

# Cluster 0300   
##############
def zcl_move_to_colour_temperature( self, nwkid, EPout, temperature, transition="0010", ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_move_to_colour_temperature %s %s %s %s" %(nwkid, EPout, temperature, transition ))

    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:    
        return zcl_raw_move_color( self, nwkid, ZIGATE_EP, EPout, "MovetoColorTemperature", temperature=temperature, transition=transition, ackIsDisabled=ackIsDisabled)

    data = ZIGATE_EP + EPout + temperature + transition    
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "00C0", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "00C0", data)

def zcl_group_move_to_colour_temperature( self, nwkid, epin, EPout, temperature, transition="0010"):
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:    
        return zcl_raw_move_color( self, nwkid, ZIGATE_EP, EPout, "MovetoColorTemperature", temperature=temperature, transitiont=transition, groupaddrmode=True)

    data = "%02d" % ADDRESS_MODE["group"] + nwkid + epin + EPout + temperature + transition
    return send_zigatecmd_raw( self, "00C0", data )

def zcl_move_hue_and_saturation(self, nwkid, EPout, hue, saturation, transition="0010", ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_move_hue_and_saturation %s %s %s %s %s" %(nwkid, EPout, hue, saturation, transition ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:    
        return zcl_raw_move_color( self, nwkid, ZIGATE_EP, EPout, "MovetoHueandSaturation", hue=hue, saturation=saturation, transition=transition, ackIsDisabled=ackIsDisabled)
    
    data = ZIGATE_EP + EPout + hue + saturation + transition
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "00B6", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "00B6", data)
 
def zcl_group_move_hue_and_saturation(self, nwkid, EPin, EPout, hue, saturation, transition="0010"):
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:    
        return zcl_raw_move_color( self, nwkid, ZIGATE_EP, EPout, "MovetoHueandSaturation", hue=hue, saturation=saturation, transition=transition, groupaddrmode=True)

    data = "%02d" % ADDRESS_MODE["group"] + nwkid + EPin + EPout + hue + saturation + transition
    return send_zigatecmd_raw( self, "00B6", data )
    
def zcl_move_to_colour(self, nwkid, EPout, colorX, colorY, transition="0010", ackIsDisabled=DEFAULT_ACK_MODE):
    self.log.logging( "zclCommand", "Debug","zcl_move_to_colour %s %s %s %s %s" %(nwkid, EPout, colorX, colorY, transition ))
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:    
        return zcl_raw_move_color( self, nwkid, ZIGATE_EP, EPout, "MovetoColor", colorX=colorX, colorY=colorY, transition=transition, ackIsDisabled=ackIsDisabled)
    data = ZIGATE_EP + EPout + colorX + colorY + transition
    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(self, nwkid, "00B7", data)
    return send_zigatecmd_zcl_ack(self, nwkid, "00B7", data)

def zcl_group_move_to_colour(self, nwkid, EPin, EPout, colorX, colorY, transition="0010"):
    if 'ZiGateInRawMode' in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ZiGateInRawMode"]:    
        return zcl_raw_move_color( self, nwkid, ZIGATE_EP, EPout, "MovetoColor", colorX=colorX, colorY=colorY, transition=transition, groupaddrmode=True)
    data = "%02d" % ADDRESS_MODE["group"] + nwkid + EPin + EPout + colorX + colorY + transition
    return send_zigatecmd_raw( self, "00B7", data )
