#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: ikeaTradfri.py

    Description: 

"""

from Modules.basicOutputs import write_attribute
from Modules.domoMaj import MajDomoDevice
from Modules.domoTools import lastSeenUpdate
from Modules.tools import (extract_info_from_8085, get_cluster_attribute_value,
                           updSQN)
from Modules.zigateConsts import ZIGATE_EP


def ikeaReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):
    """Function called when raw APS indication are received for a schneider device - it then decide how to handle it
    Arguments:
        Devices {[type]} -- list of devices
        srcNWKID {[type]} -- id of the device that generated the request
        srcEp {[type]} -- Endpoint of the device that generated the request
        ClusterID {[type]} -- cluster Id of the device that generated the request
        dstNWKID {[type]} -- Id of the device that should receive the request
        dstEP {[type]} -- Endpoint of the device that should receive the request
        MsgPayload {[type]} -- [description]
    """
    self.log.logging("Ikea", "Debug", f"Ikea Read Raw APS nwkid: {srcNWKID} ep: {srcEp} , clusterId: {ClusterID}, dstnwkid: {dstNWKID}, dstep: {dstEP}, payload: {MsgPayload}", srcNWKID)
    


def ikea_openclose_remote(self, Devices, NwkId, Ep, command, Data, Sqn):


    if self.ListOfDevices[NwkId]["Status"] != "inDB":
        return

    updSQN(self, NwkId, Sqn)
    lastSeenUpdate(self, Devices, NwkId=NwkId)

    if command == "00":  # Close/Down
        MajDomoDevice(self, Devices, NwkId, Ep, "0006", "00")
    elif command == "01":  # Open/Up
        MajDomoDevice(self, Devices, NwkId, Ep, "0006", "01")
    elif command == "02":  # Stop
        MajDomoDevice(self, Devices, NwkId, Ep, "0006", "02")


def ikea_remote_control_8085( self, Devices, MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_ ):
    self.log.logging("Ikea", "Debug", "ikea_remote_control_8085 - %s %s %s %s %s" %(
        MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_), MsgSrcAddr)
    
    TYPE_ACTIONS = {
        "01": "hold_down",
        "02": "click_down",
        "03": "release_down",
        "05": "hold_up",
        "06": "click_up",
        "07": "release_up",
    }
        
    if MsgClusterId == "0008" and MsgCmd in TYPE_ACTIONS:
        prev_selector = self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] if "0000" in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId] else None
        if MsgCmd == "07" and prev_selector == "hold_down":
            selector = "release_down"
        else:
            selector = TYPE_ACTIONS[MsgCmd]
        self.log.logging("Ikea", "Debug", "Decode8085 - Selector: %s" % selector, MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", selector)
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = selector
    else:
        self.log.logging( "Ikea", "Log", "ikea_remote_control_8085 -  Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s" % (
            MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_),
        )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)

def ikea_remote_control_80A7( self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_ ):
    
    # Ikea Remote 5 buttons round.
    #  ( cmd, directioni, cluster )
    #  ( 0x07, 0x00, 0005 )  Click right button
    #  ( 0x07, 0x01, 0005 )  Click left button
    
    self.log.logging("Ikea", "Debug", "ikea_remote_control_80A7 - %s %s %s %s %s %s" % (
        MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_), MsgSrcAddr)
    
    TYPE_DIRECTIONS = {"00": "right", "01": "left", "02": "middle"}
    TYPE_ACTIONS = {"07": "click", "08": "hold", "09": "release"}
    
    if "Model" not in self.ListOfDevices[MsgSrcAddr]:
        return

    if MsgClusterId == "0005" and MsgDirection not in TYPE_DIRECTIONS:
        # Might be in the case of Release Left or Right
        self.log.logging( "Ikea", "Log", "Decode80A7 - Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Direction: %s, Unknown_ %s" % (
            MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_), )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, Direction: %s, %s" % ( MsgCmd, MsgDirection, unkown_, )

    elif MsgClusterId == "0005" and MsgCmd in TYPE_ACTIONS:
        selector = TYPE_DIRECTIONS[MsgDirection] + "_" + TYPE_ACTIONS[MsgCmd]
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", selector)
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = selector
        self.log.logging("Ikea", "Debug", "Decode80A7 - selector: %s" % selector, MsgSrcAddr)

        if self.groupmgt and TYPE_DIRECTIONS[MsgDirection] in ( "right", "left", ):
            self.groupmgt.manageIkeaTradfriRemoteLeftRight(MsgSrcAddr, TYPE_DIRECTIONS[MsgDirection])

def ikea_remoteN2_control_80A7( self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_ ):
    # Ikea Remote N2.

    # 07 00 000000 righ click
    # 08 00 000000 continue right long click

    # 01 01 000000 left click           
    # 08 01 000000 continue left long click

    # 09 00 000000 start long click    
    # 09 eb 000000 release long click 


    self.log.logging("Ikea", "Debug", "ikea_remoteN2_control_80A7 - %s %s %s %s %s %s" % (
        MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, MsgDirection, unkown_), MsgSrcAddr)

    if MsgClusterId != "0005":
        return

    N2_ACTIONS= {
        # Cmd, Direction
        ( "07", "00"): "right_click",
        ( "08", "00"): "right_hold",
        ( "07", "01"): "left_click",
        ( "08", "01"): "left_hold"
    }

    prev_selector = self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"]
    if MsgCmd == "09":
        if MsgDirection == "00":
            # Starting Long Click. Block 8095 actions
            self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "long"
            return

        elif prev_selector == "left_hold":
            selector = "left_release"

        elif prev_selector == "right_hold":
            selector = "right_release"
            
        else:
            return
            
    elif ( MsgCmd, MsgDirection) in N2_ACTIONS:
        selector = N2_ACTIONS[ ( MsgCmd, MsgDirection) ]
        
    else:
        self.log.logging("Ikea", "Error", "ikea_remoteN2_control_80A7 - %s/%s Unknow: %s %s %s" % (
            MsgSrcAddr, MsgEP, MsgCmd, MsgDirection, unkown_), MsgSrcAddr)
        return
    
    MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", selector)
    self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = selector
    self.log.logging("Ikea", "Debug", "ikea_remoteN2_control_80A7 - selector: %s" % selector, MsgSrcAddr)

    if self.groupmgt and "right" in selector:
        self.groupmgt.manageIkeaTradfriRemoteLeftRight(MsgSrcAddr, "right")
    elif self.groupmgt and "left" in selector:
        self.groupmgt.manageIkeaTradfriRemoteLeftRight(MsgSrcAddr, "left")


def ikea_remote_control_8095( self, Devices, MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_ ):
    
    if self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP]["0005"]["0000"] == "long":
        return
    
    self.log.logging("Ikea", "Debug", "ikea_remote_control_8095 - Command: %s" % MsgCmd, MsgSrcAddr)
    
    
    if MsgClusterId == "0006" and MsgCmd == "02":
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", "toggle")
    elif MsgClusterId == "0006" and MsgCmd == "00":
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", "click_down")
    elif MsgClusterId == "0006" and MsgCmd == "01":
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", "click_up")
    else:
        self.log.logging( "Ikea", "Log", "Decode8095 - Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " % (
            MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_), )
    self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)


def ikea_remote_switch_8085(self, Devices, MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_):

    if MsgClusterId == "0008":
        if MsgCmd == "05":  # Push Up
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0006", "02")
        elif MsgCmd == "01":  # Push Down
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0006", "03")
        elif MsgCmd == "07":  # Release Up & Down
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0006", "04")

    self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = MsgCmd

def ikea_remote_switch_8095(self, Devices, MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_):
    MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0006", MsgCmd)
    self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)


def ikea_wireless_dimer_8085( self, Devices, MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_, MsgData ):

    TYPE_ACTIONS = {
        None: "",
        "01": "moveleft",
        "02": "click",
        "03": "stop",
        "04": "OnOff",
        "05": "moveright",
        "06": "Step 06",
        "07": "stop",
    }
    DIRECTION = {None: "", "00": "left", "ff": "right"}

    step_mod, up_down, step_size, transition = extract_info_from_8085(MsgData)

    selector = None

    if step_mod == "01":
        # Move left
        self.log.logging(
            "Ikea",
            "Debug",
            "Decode8085 - =====> turning left step_size: %s transition: %s" % (step_size, transition),
            MsgSrcAddr,
        )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "moveup"
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "moveup")

    elif step_mod == "04" and up_down == "00" and step_size == "00" and transition == "01":
        # Off
        self.log.logging(
            "Ikea",
            "Debug",
            "Decode8085 - =====> turning left step_size: %s transition: %s" % (step_size, transition),
            MsgSrcAddr,
        )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "off"
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "off")

    elif step_mod == "04" and up_down == "ff" and step_size == "00" and transition == "01":
        # On
        self.log.logging(
            "Ikea",
            "Debug",
            "Decode8085 - =====> turning right step_size: %s transition: %s" % (step_size, transition),
            MsgSrcAddr,
        )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "on"
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "on")

    elif step_mod == "05":
        # Move Right
        self.log.logging(
            "Ikea",
            "Debug",
            "Decode8085 - =====> turning Right step_size: %s transition: %s" % (step_size, transition),
            MsgSrcAddr,
        )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "movedown"
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "movedown")

    elif step_mod == "07":
        # Stop Moving
        self.log.logging(
            "Ikea",
            "Debug",
            "Decode8085 - =====> Stop moving step_size: %s transition: %s" % (step_size, transition),
            MsgSrcAddr,
        )
    else:
        self.log.logging(
            "Ikea",
            "Log",
            "Decode8085 - =====> Unknown step_mod: %s up_down: %s step_size: %s transition: %s" % (step_mod, up_down, step_size, transition),
            MsgSrcAddr,
        )

def ikea_motion_sensor_8095(self, Devices, MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_ ):
    if MsgClusterId == "0006" and MsgCmd == "42":  # Motion Sensor On
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0406", "01")
    else:
        self.log.logging(
            "Ikea",
            "Log",
            "Decode8095 - Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " % ( MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_),
        )
    self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)

def ikea_air_purifier_mode( self, NwkId, Ep, mode ):
    # Cluster 0xfc7d
    # Attribute 0x0006
    self.log.logging( "Ikea", "Log", "ikea_air_purifier_mode %s/%s mode: %s" % (
        NwkId, Ep, mode), NwkId, )

    if mode not in ( 0, 1, 10, 20, 30, 40, 50 ):
        return
    write_attribute( self, NwkId, ZIGATE_EP, Ep, 'fc7d', '117c', '01', '0006', '20', '%02x' %mode, ackIsDisabled=False )
    
def ikea_air_purifier_cluster(self, Devices, NwkId, Ep, ClusterId, AttributeId, Data):
    
    self.log.logging( "Ikea", "Log", "ikea_air_purifier_cluster %s/%s %s %s %s" % ( NwkId, Ep, ClusterId, AttributeId, Data), )

    if ClusterId != "fc7d":
        return
    
    if AttributeId == "0001":
        # Replace Filter
        self.log.logging( "Ikea", "Log", " -- Replace Filter: %s" % ( Data), )
        # Let send Alarm with 100% usage
        if int(Data,16) == 0x01:
            MajDomoDevice(self, Devices, NwkId, Ep, "0009", 100)
        
    elif AttributeId == "0002":
        # Filter Life time
        self.log.logging( "Ikea", "Log", " -- Filter Life time: %s" % ( Data), )
        
    elif AttributeId == "0003":
        # Led Indication
        self.log.logging( "Ikea", "Log", " --  Led Indication: %s" % ( Data), )
        
    elif AttributeId == "0004":
        # PM25
        value = int( Data, 16)
        if value != 0xffff:
            self.log.logging( "Ikea", "Log", " --  PM25: %s --> %s" % ( Data, value), )
            MajDomoDevice(self, Devices, NwkId, Ep, "042a", value)
        
    elif AttributeId == "0005":
        # Locked
        self.log.logging( "Ikea", "Log", " --  Locked: %s" % ( Data), )
        
    elif AttributeId == "0006":
        self.log.logging( "Ikea", "Log", " --  Mode: %s" % ( Data), )
        mode = int( Data, 16 )
        if mode == 0:
            # Switch Off
            MajDomoDevice(self, Devices, NwkId, Ep, "0202", 0, Attribute_="0006", )
            MajDomoDevice(self, Devices, NwkId, Ep, "0202", 0, Attribute_="0007", )
        elif mode == 1:
            MajDomoDevice(self, Devices, NwkId, Ep, "0202", 1, Attribute_="0006", )
        elif 10 <= mode <= 50:
            level = int((( mode // 10 ) ) + 1)
            MajDomoDevice(self, Devices, NwkId, Ep, "0202", level, Attribute_="0006", )

    elif AttributeId == "0007":
        # Fan Speed should vary from 1 to 50
        fan_speed = convert_fan_speed_into_level( int(Data,16)  )
        
        self.log.logging( "Ikea", "Log", " --  Fan Speed: %s => %s" % ( Data, fan_speed), )
        MajDomoDevice(self, Devices, NwkId, Ep, "0202", fan_speed, Attribute_="0007", ) 

    elif AttributeId == "0008":
        # Filter runtime
        runtime = int(Data,16)
        lifetime = get_cluster_attribute_value( self, NwkId, Ep, ClusterId, "0002")
        if lifetime is not None:
            lifetime = int(lifetime,16)
            percentage = 100 * runtime // lifetime
            MajDomoDevice(self, Devices, NwkId, Ep, "0009", int(percentage))
        self.log.logging( "Ikea", "Log", " --  Filter runtime: %s / %s" % ( runtime, lifetime), )
    

def convert_fan_speed_into_level( fan_speed ):
    
    return round( ((fan_speed * 100 ) / 50 ), 1 )
    
