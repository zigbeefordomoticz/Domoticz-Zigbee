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

"""
    Module: very low level to send command to ZiGate

    Description: 

"""

import sys
import time

from Modules.zigateConsts import ADDRESS_MODE, ZIGATE_COMMANDS, ZIGATE_EP


def add_Last_Cmds(self, isqn, address_mode, nwkid, cmd, datas):

    if nwkid not in self.ListOfDevices:
        return

    if "Last Cmds" not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]["Last Cmds"] = []

    if isinstance(self.ListOfDevices[nwkid]["Last Cmds"], dict):
        self.ListOfDevices[nwkid]["Last Cmds"] = []

    if len(self.ListOfDevices[nwkid]["Last Cmds"]) >= 10:
        # Remove the First element in the list.
        self.ListOfDevices[nwkid]["Last Cmds"].pop(0)

    if isqn is None:
        isqn = "None"
    self.ListOfDevices[nwkid]["Last Cmds"].append((isqn, address_mode, nwkid, cmd, datas))


def send_zigatecmd_zcl_ack(self, address, cmd, datas):
    # Send a ZCL command with ack
    # address can be a shortId or an IEEE
    ackIsDisabled = False
    _nwkid = None
    if len(address) == 4:
        # Short address
        _nwkid = address
        address_mode = "%02x" % ADDRESS_MODE["short"]
        if self.pluginconf.pluginConf["disableAckOnZCL"]:
            address_mode = "%02x" % ADDRESS_MODE["shortnoack"]
            ackIsDisabled = True
    else:
        address_mode = "%02x" % ADDRESS_MODE["ieee"]
        if self.pluginconf.pluginConf["disableAckOnZCL"]:
            address_mode = "%02x" % ADDRESS_MODE["ieeenoack"]
            ackIsDisabled = True
        if address in self.IEEE2NWK:
            _nwkid = self.IEEE2NWK[address]
    isqn = send_zigatecmd_raw(self, cmd, address_mode + address + datas, ackIsDisabled=ackIsDisabled, NwkId=_nwkid)
    add_Last_Cmds(self, isqn, address_mode, address, cmd, datas)
    self.log.logging(
        "BasicOutput", "Debug", "send_zigatecmd_zcl_ack - [%s] %s %s %s" % (isqn, cmd, address_mode, datas), _nwkid
    )
    return isqn


def send_zigatecmd_zcl_noack(self, address, cmd, datas):
    # Send a ZCL command with ack
    # address can be a shortId or an IEEE
    ackIsDisabled = True
    _nwkid = None
    if len(address) == 4:
        # Short address
        _nwkid = address
        address_mode = "%02x" % ADDRESS_MODE["shortnoack"]
        if (
            self.pluginconf.pluginConf["forceAckOnZCL"]
            or _nwkid != "ffff"
            and cmd in self.ListOfDevices[_nwkid]["ForceAckCommands"]
        ):
            self.log.logging("BasicOutput", "Debug", "Force Ack on %s %s" % (cmd, datas))
            address_mode = "%02x" % ADDRESS_MODE["short"]
            ackIsDisabled = False
    else:
        address_mode = "%02x" % ADDRESS_MODE["ieeenoack"]
        if self.pluginconf.pluginConf["forceAckOnZCL"]:
            address_mode = "%02x" % ADDRESS_MODE["ieee"]
            self.log.logging("BasicOutput", "Debug", "Force Ack on %s %s" % (cmd, datas))
            ackIsDisabled = False
        if address in self.IEEE2NWK:
            _nwkid = self.IEEE2NWK[address]
    isqn = send_zigatecmd_raw(self, cmd, address_mode + address + datas, ackIsDisabled=ackIsDisabled, NwkId=_nwkid)
    add_Last_Cmds(self, isqn, address_mode, address, cmd, datas)
    self.log.logging(
        "BasicOutput", "Debug", "send_zigatecmd_zcl_noack - [%s] %s %s %s" % (isqn, cmd, address_mode, datas), _nwkid
    )
    return isqn


def send_zigatecmd_raw(self, cmd, datas, highpriority=False, ackIsDisabled=False, NwkId=None):
    #
    # Send the cmd directly to ZiGate

    if self.ControllerLink is None:
        self.log.logging(
            "BasicOutput", "Error", "Zigate Communication error.", None, {"Error code": "BOUTPUTS-CMDRAW-01"}
        )
        return

    i_sqn = self.ControllerLink.sendData(cmd, datas, highpriority, ackIsDisabled, NwkId=NwkId)
    if self.pluginconf.pluginConf["coordinatorCmd"]:
        self.log.logging(
            "BasicOutput",
            "Log",
            "send_zigatecmd_raw       - [%s] %s %s %s Queue Length: %s"
            % (i_sqn, cmd, datas, NwkId, self.ControllerLink.loadTransmit()),
        )
    else:
        self.log.logging(
            "BasicOutput",
            "Debug",
            "====> send_zigatecmd_raw - [%s] %s %s %s Queue Length: %s"
            % (i_sqn, cmd, datas, NwkId, self.ControllerLink.loadTransmit()),
        )
    if self.ControllerLink.loadTransmit() > 15:
        self.log.logging(
            "BasicOutput",
            "Log",
            "WARNING - send_zigatecmd : [%s] %s %18s %s ZigateQueue: %s"
            % (i_sqn, cmd, datas, NwkId, self.ControllerLink.loadTransmit()),
        )

    return i_sqn


def sendZigateCmd(self, cmd, datas, ackIsDisabled=False):
    
    """
    sendZigateCmd will send command to Zigate by using the SendData method
    cmd : 4 hex (str) which correspond to the Zigate command
    datas : string of hex char
    ackIsDisabled : If True, it means that usally a Ack is expected ( ZIGATE_COMMANDS), but here it has been disabled via Address Mode

    """
    if int(cmd, 16) not in ZIGATE_COMMANDS:
        self.log.logging(
            "BasicOutput",
            "Error",
            "Unexpected command: %s %s" % (cmd, datas),
            None,
            {"Error code": "BOUTPUTS-CMD-01", "Cmd": cmd, "datas": datas},
        )
        return None

    if ZIGATE_COMMANDS[int(cmd, 16)]["Layer"] == "ZCL":
        AddrMod = datas[0:2]
        NwkId = datas[2:6]

        self.log.logging("BasicOutput", "Debug", "sendZigateCmd - ZCL layer %s %s" % (cmd, datas), NwkId)

        if NwkId not in self.ListOfDevices:
            self.log.logging(
                "BasicOutput",
                "Error",
                "sendZigateCmd - Decoding error %s %s" % (cmd, datas),
                NwkId,
                {"Error code": "BOUTPUTS-CMD-02", "ListOfDevices": self.ListOfDevices},
            )
            return None
        if AddrMod == "01":
            # Group With Ack
            return send_zigatecmd_raw(
                self,
                cmd,
                datas,
            )

        if AddrMod == "02":
            # Short with Ack
            return send_zigatecmd_zcl_ack(
                self,
                NwkId,
                cmd,
                datas[6:],
            )

        if AddrMod == "07":
            # Short No Ack
            return send_zigatecmd_zcl_noack(
                self,
                NwkId,
                cmd,
                datas[6:],
            )

    return send_zigatecmd_raw(self, cmd, datas, ackIsDisabled)


def raw_APS_request( self, targetaddr, dest_ep, cluster, profileId, payload, zigate_ep=ZIGATE_EP, zigpyzqn=None, groupaddrmode=False, highpriority=False, ackIsDisabled=False, delayAfterSent=False):
    self.log.logging(
        "outRawAPS",
        "Debug",
        "raw_APS_request - Zigbee Communication: %s Profile: %s Cluster: %s TargetNwk: %s TargetEp: %s SrcEp: %s payload: %s ZDPsqn: %s GroupMode: %s ackIsDisable: %s"
        % (self.zigbee_communication, profileId, cluster, targetaddr, dest_ep, zigate_ep, payload, zigpyzqn, groupaddrmode, ackIsDisabled),
    )

    if self.zigbee_communication == "zigpy":
        return zigpy_raw_APS_request( self, targetaddr, dest_ep, cluster, profileId, payload, zigate_ep, zigpyzqn, groupaddrmode, highpriority, ackIsDisabled, delayAfterSent)
    
    return zigate_raw_APS_request( self, targetaddr, dest_ep, cluster, profileId, payload, zigate_ep, groupaddrmode, highpriority, ackIsDisabled)

def zigate_raw_APS_request( self, targetaddr, dest_ep, cluster, profileId, payload, zigate_ep=ZIGATE_EP, groupaddrmode=False, highpriority=False, ackIsDisabled=False):
            
    SECURITY = 0x02
    RADIUS = 0x00

    security = "%02X" % SECURITY
    radius = "%02X" % RADIUS

    len_payload = (len(payload)) // 2
    len_payload = "%02x" % len_payload

    # APS RAW is always sent in NO-ACK below 31d (included)
    # APS RAW has ACK/NO-ACK option as of 31e
    self.log.logging(
        "outRawAPS",
        "Debug",
        "zigate_raw_APS_request - ackIsDisabled: %s Addr: %s Ep: %s Cluster: %s ProfileId: %s Payload: %s"
        % (ackIsDisabled, targetaddr, dest_ep, cluster, profileId, payload),
        dest_ep,
    )

    # In case of Firmware < 31e 0x0530 is always on noack even if address mode 0x02 is used.
    overwrittenackIsDisabled = ackIsDisabled
    if self.zigbee_communication == 'zigate' and self.FirmwareVersion and self.FirmwareVersion <= "031d":
        ackIsDisabled = False  # Force the usage of 0x02 address mode
        overwrittenackIsDisabled = True  # Indicate that we are without Ack

    # self.log.logging( "BasicOutput", "Log", "Raw APS - ackIsDisabled: %s overwrittenackIsDisabled: %s" %(ackIsDisabled,overwrittenackIsDisabled))
    if groupaddrmode:
        return send_zigatecmd_raw(
            self,
            "0530",
            "01" + targetaddr + zigate_ep + dest_ep + cluster + profileId + security + radius + len_payload + payload,
            highpriority,
            ackIsDisabled=ackIsDisabled,
        )
        
    if ackIsDisabled:
        return send_zigatecmd_raw(
            self,
            "0530",
            "07" + targetaddr + zigate_ep + dest_ep + cluster + profileId + security + radius + len_payload + payload,
            highpriority,
            ackIsDisabled=ackIsDisabled,
        )
    return send_zigatecmd_raw(
        self,
        "0530",
        "02" + targetaddr + zigate_ep + dest_ep + cluster + profileId + security + radius + len_payload + payload,
        highpriority,
        ackIsDisabled=overwrittenackIsDisabled,
    )
    
    
def zigpy_raw_APS_request( self, targetaddr, dest_ep, cluster, profileId, payload, zigate_ep, zigpyzqn=None, groupaddrmode=False, highpriority=False, ackIsDisabled=False, delayAfterSent=False):

    if zigpyzqn is None:
        zigpyzqn = "0"
        
    # Debug mode
    callingfunction = sys._getframe(2).f_code.co_name
    data = {
        'Function': callingfunction,
        'Profile': int(profileId, 16),
        'Cluster': int(cluster, 16),
        'TargetNwk': int(targetaddr, 16),
        'TargetEp': int(dest_ep, 16),
        'SrcEp': int(zigate_ep, 16),
        'Sqn': int(zigpyzqn,16),
        'RxOnIdle': device_listening_on_iddle(self, targetaddr),
        'payload': payload,
        'delayAfterSent': delayAfterSent,
        'timestamp': time.time()
    }

    if groupaddrmode:
        data['AddressMode'] = 0x01
        ackIsDisabled = True
    elif ackIsDisabled:
        data['AddressMode'] = 0x07
    else:
        data['AddressMode'] = 0x02

    self.log.logging(
        "outRawAPS",
        "Debug",
        "zigpy_raw_APS_request - %s ==> Profile: %04x Cluster: %04x TargetNwk: %04x TargetEp: %02x SrcEp: %02x  payload: %s"
        % ( callingfunction, data['Profile'], data['Cluster'], data['TargetNwk'], data['TargetEp'], data['SrcEp'], data['payload'])
    )

    return self.ControllerLink.sendData( "RAW-COMMAND", data, NwkId=int(targetaddr,16), sqn=int(zigpyzqn,16), ackIsDisabled=ackIsDisabled )

def device_listening_on_iddle(self, nwkid):
    
    if nwkid not in self.ListOfDevices:
        return True
    
    if "Capability" in self.ListOfDevices[nwkid]:
        if "Reduced-Function Device" in self.ListOfDevices[nwkid]["Capability"]:
            return False
        if "Full-Function Device" in self.ListOfDevices[nwkid]["Capability"]:
            return True

    return False