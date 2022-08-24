#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: ikeaTradfri.py

    Description: 

"""

from Modules.domoMaj import MajDomoDevice
from Modules.domoTools import lastSeenUpdate
from Modules.tools import updSQN, extract_info_from_8085


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
    
    TYPE_ACTIONS = {
        "01": "hold_down",
        "02": "click_down",
        "03": "release_down",
        "05": "hold_up",
        "06": "click_up",
        "07": "release_up",
    }
        
    if MsgClusterId == "0008" and MsgCmd in TYPE_ACTIONS:
        selector = TYPE_ACTIONS[MsgCmd]
        self.log.logging("Input", "Debug", "Decode8085 - Selector: %s" % selector, MsgSrcAddr)
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", selector)
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = selector
    else:
        self.log.logging(
            "Input",
            "Log",
            "Decode8085 -  Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s" % (MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_),
        )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)

def ikea_remote_control_8095( self, Devices, MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_ ):
    self.log.logging("Input", "Debug", "ikea_remote_control_8095 - Command: %s" % MsgCmd, MsgSrcAddr)
    

    if MsgClusterId == "0006" and MsgCmd == "02":
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", "toggle")
    elif MsgClusterId == "0006" and MsgCmd == "00":
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", "click_down")
    elif MsgClusterId == "0006" and MsgCmd == "01":
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "rmt1", "click_up")
    else:
        self.log.logging(
            "Input",
            "Log",
            "Decode8095 - Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " % (MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_),
        )
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
            "Input",
            "Debug",
            "Decode8085 - =====> turning left step_size: %s transition: %s" % (step_size, transition),
            MsgSrcAddr,
        )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "moveup"
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "moveup")

    elif step_mod == "04" and up_down == "00" and step_size == "00" and transition == "01":
        # Off
        self.log.logging(
            "Input",
            "Debug",
            "Decode8085 - =====> turning left step_size: %s transition: %s" % (step_size, transition),
            MsgSrcAddr,
        )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "off"
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "off")

    elif step_mod == "04" and up_down == "ff" and step_size == "00" and transition == "01":
        # On
        self.log.logging(
            "Input",
            "Debug",
            "Decode8085 - =====> turning right step_size: %s transition: %s" % (step_size, transition),
            MsgSrcAddr,
        )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "on"
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "on")

    elif step_mod == "05":
        # Move Right
        self.log.logging(
            "Input",
            "Debug",
            "Decode8085 - =====> turning Right step_size: %s transition: %s" % (step_size, transition),
            MsgSrcAddr,
        )
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "movedown"
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "movedown")

    elif step_mod == "07":
        # Stop Moving
        self.log.logging(
            "Input",
            "Debug",
            "Decode8085 - =====> Stop moving step_size: %s transition: %s" % (step_size, transition),
            MsgSrcAddr,
        )
    else:
        self.log.logging(
            "Input",
            "Log",
            "Decode8085 - =====> Unknown step_mod: %s up_down: %s step_size: %s transition: %s" % (step_mod, up_down, step_size, transition),
            MsgSrcAddr,
        )

def ikea_motion_sensor_8095(self, Devices, MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_ ):
    if MsgClusterId == "0006" and MsgCmd == "42":  # Motion Sensor On
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0406", "01")
    else:
        self.log.logging(
            "Input",
            "Log",
            "Decode8095 - Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s " % ( MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_),
        )
    self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)
