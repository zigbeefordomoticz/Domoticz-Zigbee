#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

import os.path
import time
from pathlib import Path

instrument_time = True


# Decorator for profiling forwarder
def time_spent_forwarder():
    def profiling(f_in):
        def f_out(self, message):
            # Decorator to instrument the time spent in a function.
            if self.pluginconf.pluginConf["ZiGateReactTime"]:
                t_start = 1000 * time.time()
                result = f_in(self, message)
                t_end = 1000 * time.time()
                t_elapse = int(t_end - t_start)
                self.statistics.add_rxTiming(t_elapse)
                if t_elapse > 1000:
                    self.log.logging(
                        "debugTiming",
                        "Log",
                        "forward_message (F_out) spend more than 1s (%s ms) frame: %s" % (t_elapse, message),
                    )
            else:
                result = f_in(self, message)
            return result

        return f_out

    return profiling

def write_capture_rx_frames(self, *args):
    if self.captureRxFrame is None:
        return
    zigbee_frame = " %s |" %time.time()
    zigbee_frame += "".join(' %s |' %str(x) for x in args) 
    self.captureRxFrame.write( zigbee_frame[:-1] + '\n'  )

def open_capture_rx_frames(self):
    if "CaptureRxFrames" not in self.pluginconf.pluginConf or not self.pluginconf.pluginConf[ "CaptureRxFrames" ]:
        return
    
    captureRxFrame_filename = Path( self.pluginconf.pluginConf["pluginLogs"]) / ("Capture-Zigbee-Rx-Frames-%02d.csv" % self.hardwareid)
    header = (
        None
        if os.path.isfile(captureRxFrame_filename)
        else " Time Stamp | sender | profile | cluster | src_ep | dst_ep | raw | decoded(utf8) | dst_addressing \n"
    )
    self.captureRxFrame = open( captureRxFrame_filename,"at")
    if header:
        self.captureRxFrame.write( header )
        
        
def instrument_log_command_open( self):
    if "CaptureTxFrames" not in self.pluginconf.pluginConf or not self.pluginconf.pluginConf["CaptureTxFrames"]:
        return
    
    captureTxFrame_filename = Path( self.pluginconf.pluginConf["pluginLogs"]) / ("Capture-Zigbee-Tx-Frames-%02d.csv" % self.hardwareid)
    header = (
        None
        if os.path.isfile(captureTxFrame_filename)
        else " Time Stamp | Command | Function | SQN | Priority | ackIsDisabled | WaitForresponseIn | NwkId | Profile | Target addr | Target Ep | Src Ep | Cluster | Payload | Addr Mode | rxOnIddle \n"
    )

    self.structured_log_command_file_handler = open(captureTxFrame_filename, "a")
    if header:
        header = " Time Stamp | Command | Function | SQN | Priority | ackIsDisabled | WaitForresponseIn | NwkId | Profile | Target addr | Target Ep | Src Ep | Cluster | Payload | Addr Mode | rxOnIddle \n"
        self.structured_log_command_file_handler.write( header )

def instrument_sendData( self, cmd, datas, sqn, timestamp, highpriority, ackIsDisabled, waitForResponseIn, NwkId ):
    if self.structured_log_command_file_handler is None:
        return
    line = ""
    line += " %s " %timestamp
    line += "| %s " %cmd
    if datas is not None:
        line += "| %s " %datas["Function"] if "Function" in datas else ""
        line += "| %s " %sqn
        line += "| %s " %highpriority
        line += "| %s " %ackIsDisabled
        line += "| %s " %waitForResponseIn
        line += "| 0x%04x " %(NwkId) if NwkId is not None else "| None "
        line += "| 0x%04X " %(datas["Profile"]) if "Profile" in datas else "| "
        line += "| 0x%X " %(datas["TargetNwk"]) if "TargetNwk" in datas else "| "
        line += "| 0x%02X " %(datas["TargetEp"]) if "TargetEp" in datas else "| "
        line += "| 0x%02X " %(datas["SrcEp"]) if "SrcEp" in datas else "| "
        line += "| 0x%04X " %(datas["Cluster"]) if "Cluster" in datas else "| "
        line += "| %s " %(datas["payload"]) if "payload" in datas else "| "
        line += "| %s " %(datas["AddressMode"]) if "AddressMode" in datas else "| "
        line += "| %s " %(datas["RxOnIdle"]) if "RxOnIdle" in datas else "| "
        line += "\n"

    self.structured_log_command_file_handler.write( line )