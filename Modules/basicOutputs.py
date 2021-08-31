#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: basicOutputs

    Description: All direct communications towards Zigate

"""
import Domoticz
import binascii
import struct
import json

from datetime import datetime
from time import time

from Modules.zigateConsts import ZIGATE_EP, ADDRESS_MODE, ZLL_DEVICES, ZIGATE_COMMANDS
from Modules.tools import (
    mainPoweredDevice,
    getListOfEpForCluster,
    set_request_datastruct,
    set_isqn_datastruct,
    set_timestamp_datastruct,
    get_and_inc_SQN,
    is_ack_tobe_disabled,
    build_fcf,
    is_hex,
)
from Classes.LoggingManagement import LoggingManagement


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
        if self.pluginconf.pluginConf["forceAckOnZCL"] or (
            address != "ffff" and cmd in self.ListOfDevices[address]["ForceAckCommands"]
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

    if self.ZigateComm is None:
        self.log.logging(
            "BasicOutput", "Error", "Zigate Communication error.", None, {"Error code": "BOUTPUTS-CMDRAW-01"}
        )
        return

    i_sqn = self.ZigateComm.sendData(cmd, datas, highpriority, ackIsDisabled, NwkId=NwkId)
    if self.pluginconf.pluginConf["debugzigateCmd"]:
        self.log.logging(
            "BasicOutput",
            "Log",
            "send_zigatecmd_raw       - [%s] %s %s %s Queue Length: %s"
            % (i_sqn, cmd, datas, NwkId, self.ZigateComm.loadTransmit()),
        )
    else:
        self.log.logging(
            "BasicOutput",
            "Debug",
            "====> send_zigatecmd_raw - [%s] %s %s %s Queue Length: %s"
            % (i_sqn, cmd, datas, NwkId, self.ZigateComm.loadTransmit()),
        )
    if self.ZigateComm.loadTransmit() > 15:
        self.log.logging(
            "BasicOutput",
            "Log",
            "WARNING - send_zigatecmd : [%s] %s %18s %s ZigateQueue: %s"
            % (i_sqn, cmd, datas, NwkId, self.ZigateComm.loadTransmit()),
        )

    return i_sqn


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


def send_zigate_mode(self, mode):
    # Mode: cf. https://github.com/fairecasoimeme/ZiGate/pull/307
    #  0x00 - ZiGate in norml operation
    #  0x01 - ZiGate in RAW mode
    #  0x02 - ZiGate in Hybrid mode ( All inbound messages are received via 0x8002 in addition of the normal one)

    send_zigatecmd_raw(self, "0002", "%02x" % mode)


def ZigatePermitToJoin(self, permit):
    """
    ZigatePermitToJoin will switch the Zigate in the Pairing mode or not based on the permit flag

    permit : 0 - disable Permit to Join
             1 - 254 - enable Permit to join from 1s to 254s
             255 - enable Permit to join (unlimited)
    """

    if permit:
        # Enable Permit to join
        if self.permitTojoin["Duration"] != 255:
            if permit != 255:
                self.log.logging("BasicOutput", "Status", "Request Accepting new Hardware for %s seconds " % permit)
            else:
                self.log.logging("BasicOutput", "Status", "Request Accepting new Hardware for ever ")

            self.permitTojoin["Starttime"] = int(time())
            self.permitTojoin["Duration"] = 0 if permit <= 5 else permit
    else:
        self.permitTojoin["Starttime"] = int(time())
        self.permitTojoin["Duration"] = 0
        self.log.logging("BasicOutput", "Status", "Request Disabling Accepting new Hardware")

    PermitToJoin(self, "%02x" % permit)

    self.log.logging("BasicOutput", "Debug", "Permit Join set :")
    self.log.logging("BasicOutput", "Debug", "---> self.permitTojoin['Starttime']: %s" % self.permitTojoin["Starttime"])
    self.log.logging("BasicOutput", "Debug", "---> self.permitTojoin['Duration'] : %s" % self.permitTojoin["Duration"])


def get_TC_significance(nwkid):
    if nwkid == "0000":
        return "01"

    return "00"


def PermitToJoin(self, Interval, TargetAddress="FFFC"):

    if Interval == "00" and self.pluginconf.pluginConf["forceClosingAllNodes"]:
        for x in self.ListOfDevices:
            if mainPoweredDevice(self, x):
                self.log.logging("BasicOutput", "Log", "Request router: %s to close the network" % x)
                send_zigatecmd_raw(self, "0049", x + Interval + get_TC_significance(x))
    else:
        send_zigatecmd_raw(self, "0049", TargetAddress + Interval + get_TC_significance(TargetAddress))
    if TargetAddress in ("FFFC", "0000"):
        # Request a Status to update the various permitTojoin structure
        send_zigatecmd_raw(self, "0014", "")  # Request status


def start_Zigate(self, Mode="Controller"):
    """
    Purpose is to run the start sequence for the Zigate
    it is call when Network is not started.

    """

    ZIGATE_MODE = ("Controller", "Router")

    if Mode not in ZIGATE_MODE:
        self.log.logging(
            "BasicOutput",
            "Error",
            "start_Zigate - Unknown mode: %s" % Mode,
            None,
            {"Error code": "BOUTPUTS-START-01", "Mode": Mode, "ZIGATE_MODE": ZIGATE_MODE},
        )
        return

    self.log.logging(
        "BasicOutput", "Status", "ZigateConf setting Channel(s) to: %s" % self.pluginconf.pluginConf["channel"]
    )
    setChannel(self, str(self.pluginconf.pluginConf["channel"]))

    if Mode == "Controller":
        # self.log.logging( "BasicOutput", "Status", "Set Zigate as a Coordinator" )
        # send_zigatecmd_raw(self, "0023","00")

        self.log.logging("BasicOutput", "Status", "Force ZiGate to Normal mode")
        send_zigate_mode(self, 0x00)

        self.log.logging("BasicOutput", "Status", "Start network")
        send_zigatecmd_raw(self, "0024", "")  # Start Network

        self.log.logging("BasicOutput", "Status", "Set Zigate as a TimeServer")
        setTimeServer(self)

        self.log.logging("BasicOutput", "Debug", "Request network Status")
        send_zigatecmd_raw(self, "0014", "")  # Request status
        send_zigatecmd_raw(self, "0009", "")  # Request status

        # Request a Status to update the various permitTojoin structure
        send_zigatecmd_raw(self, "0014", "")  # Request status


def setTimeServer(self):

    EPOCTime = datetime(2000, 1, 1)
    UTCTime = int((datetime.now() - EPOCTime).total_seconds())
    # self.log.logging( "BasicOutput", "Status", "setTimeServer - Setting UTC Time to : %s" %( UTCTime) )
    data = "%08x" % UTCTime
    send_zigatecmd_raw(self, "0016", data)
    # Request Time
    send_zigatecmd_raw(self, "0017", "")


def zigateBlueLed(self, OnOff):

    if OnOff:
        self.log.logging("BasicOutput", "Log", "Switch Blue Led On")
        send_zigatecmd_raw(self, "0018", "01")
    else:
        self.log.logging("BasicOutput", "Log", "Switch Blue Led off")
        send_zigatecmd_raw(self, "0018", "00")


def getListofAttribute(self, nwkid, EpOut, cluster, start_attribute=None, manuf_specific=None, manuf_code=None):

    if start_attribute is None:
        start_attribute = "0000"

    if (manuf_specific is None) or (manuf_code is None):
        manuf_specific = "00"
        manuf_code = "0000"

    datas = ZIGATE_EP + EpOut + cluster + start_attribute + "00" + manuf_specific + manuf_code + "01"
    self.log.logging("BasicOutput", "Debug", "attribute_discovery_request - " + str(datas), nwkid)
    send_zigatecmd_zcl_noack(self, nwkid, "0140", datas)


def getListofAttributeExtendedInfos(
    self, nwkid, EpOut, cluster, start_attribute=None, manuf_specific=None, manuf_code=None
):

    if start_attribute is None:
        start_attribute = "0000"

    if manuf_specific is None or manuf_code is None:
        manuf_specific = "00"
        manuf_code = "0000"

    datas = ZIGATE_EP + EpOut + cluster + start_attribute + "00" + manuf_specific + manuf_code + "01"
    self.log.logging("BasicOutput", "Debug", "attribute_discovery_request - " + str(datas), nwkid)
    send_zigatecmd_zcl_noack(self, nwkid, "0141", datas)


def initiateTouchLink(self):

    self.log.logging("BasicOutput", "Status", "initiate Touch Link")
    send_zigatecmd_raw(self, "00D0", "")


def factoryresetTouchLink(self):

    self.log.logging("BasicOutput", "Status", "Factory Reset Touch Link Over The Air")
    send_zigatecmd_raw(self, "00D2", "")


def identifySend(self, nwkid, ep, duration=0, withAck=False):

    # datas = "02" + "%s"%(nwkid) + ZIGATE_EP + ep + "%04x"%(duration)
    datas = ZIGATE_EP + ep + "%04x" % (duration)
    self.log.logging(
        "BasicOutput",
        "Debug",
        "identifySend - send an Identify Message to: %s for %04x seconds Ack: %s" % (nwkid, duration, withAck),
        nwkid,
    )
    self.log.logging("BasicOutput", "Debug", "identifySend - data sent >%s< " % (datas), nwkid)
    if withAck:
        return send_zigatecmd_zcl_ack(self, nwkid, "0070", datas)
    return send_zigatecmd_zcl_noack(self, nwkid, "0070", datas)


def maskChannel(self, channel):

    CHANNELS = {
        0: 0x00000000,  # Scan for all channels
        11: 0x00000800,
        12: 0x00001000,
        13: 0x00002000,
        14: 0x00004000,
        15: 0x00008000,
        16: 0x00010000,
        17: 0x00020000,
        18: 0x00040000,
        19: 0x00080000,
        20: 0x00100000,
        21: 0x00200000,
        22: 0x00400000,
        23: 0x00800000,
        24: 0x01000000,
        25: 0x02000000,
        26: 0x04000000,
    }

    mask = 0x00000000

    if isinstance(channel, list):
        for c in channel:
            if c.isdigit():
                if int(c) in CHANNELS:
                    mask += CHANNELS[int(c)]
            else:
                self.log.logging(
                    "BasicOutput",
                    "Error",
                    "maskChannel - invalid channel %s" % c,
                    None,
                    {"Error code": "BOUTPUTS-CHANNEL-01", "channel": channel},
                )

    elif isinstance(channel, int):
        if channel in CHANNELS:
            mask = CHANNELS[channel]
        else:
            self.log.logging(
                "BasicOutput",
                "Error",
                "Requested channel not supported by Zigate: %s" % channel,
                None,
                {"Error code": "BOUTPUTS-CHANNEL-02", "channel": channel},
            )

    elif isinstance(channel, str):
        lstOfChannels = channel.strip().split(",")
        for chnl in lstOfChannels:
            if chnl.isdigit():
                if int(chnl) in CHANNELS:
                    mask += CHANNELS[int(chnl)]
                else:
                    self.log.logging(
                        "BasicOutput",
                        "Error",
                        "Requested channel not supported by Zigate: %s" % chnl,
                        None,
                        {"Error code": "BOUTPUTS-CHANNEL-03", "channel": channel},
                    )
            else:
                self.log.logging(
                    "BasicOutput",
                    "Error",
                    "maskChannel - invalid channel %s" % chnl,
                    None,
                    {"Error code": "BOUTPUTS-CHANNEL-04", "channel": channel},
                )
    else:
        self.log.logging(
            "BasicOutput",
            "Error",
            "Requested channel is invalid: %s" % channel,
            None,
            {"Error code": "BOUTPUTS-CHANNEL-05", "channel": channel},
        )

    return mask


def setChannel(self, channel):
    """
    The channel list
    is a bitmap, where each bit describes a channel (for example bit 12
    corresponds to channel 12). Any combination of channels can be included.
    ZigBee supports channels 11-26.
    """
    mask = maskChannel(self, channel)
    self.log.logging("BasicOutput", "Status", "setChannel - Channel set to : %08.x " % (mask))

    send_zigatecmd_raw(self, "0021", "%08.x" % (mask))


def channelChangeInitiate(self, channel):

    self.log.logging(
        "BasicOutput", "Status", "Change channel from [%s] to [%s] with nwkUpdateReq" % (self.currentChannel, channel)
    )
    self.log.logging("BasicOutput", "Log", "Not Implemented")
    # NwkMgtUpdReq( self, channel, 'change')


def channelChangeContinue(self):

    self.log.logging("BasicOutput", "Status", "Restart network")
    send_zigatecmd_raw(self, "0024", "")  # Start Network
    send_zigatecmd_raw(self, "0009", "")  # In order to get Zigate IEEE and NetworkID


def setExtendedPANID(self, extPANID):
    """
    setExtendedPANID MUST be call after an erase PDM. If you change it
    after having paired some devices, they won't be able to reach you anymore
    Extended PAN IDs (EPIDs) are 64-bit numbers that uniquely identify a PAN.
    ZigBee communicates using the shorter 16-bit PAN ID for all communication except one.
    """

    datas = "%016x" % extPANID
    self.log.logging("BasicOutput", "Debug", "set ExtendedPANID - %016x " % (extPANID))
    send_zigatecmd_raw(self, "0020", datas)


def leaveMgtReJoin(self, saddr, ieee, rejoin=True):
    """
    E_SL_MSG_MANAGEMENT_LEAVE_REQUEST / 0x47


    This function requests a remote node to leave the network. The request also
    indicates whether the children of the leaving node should also be requested to leave
    and whether the leaving node(s) should subsequently attempt to rejoin the network.

    This function is provided in the ZDP API for the reason
    of interoperability with nodes running non-NXP ZigBee PRO
    stacks that support the generated request. On receiving a
    request from this function, the NXP ZigBee PRO stack will
    return the status ZPS_ZDP_NOT_SUPPORTED.

    """

    self.log.logging(
        "BasicOutput",
        "Log",
        "leaveMgtReJoin - sAddr: %s , ieee: %s, [%s/%s]"
        % (saddr, ieee, self.pluginconf.pluginConf["allowAutoPairing"], rejoin),
        saddr,
    )
    if not self.pluginconf.pluginConf["allowAutoPairing"]:
        self.log.logging(
            "BasicOutput",
            "Log",
            "leaveMgtReJoin - no action taken as 'allowAutoPairing' is %s"
            % self.pluginconf.pluginConf["allowAutoPairing"],
            saddr,
        )
        return None

    if rejoin:
        self.log.logging(
            "BasicOutput",
            "Status",
            "Switching Zigate in pairing mode to allow %s (%s) coming back" % (saddr, ieee),
            saddr,
        )

        # If Zigate not in Permit to Join, let's switch it to Permit to Join for 60'
        duration = self.permitTojoin["Duration"]
        stamp = self.permitTojoin["Starttime"]
        if duration == 0:
            dur_req = 60
            self.permitTojoin["Duration"] = 60
            self.permitTojoin["Starttime"] = int(time())
            self.log.logging(
                "BasicOutput", "Debug", "leaveMgtReJoin - switching Zigate in Pairing for %s sec" % dur_req, saddr
            )
            send_zigatecmd_raw(self, "0049", "FFFC" + "%02x" % dur_req + "00")
            self.log.logging("BasicOutput", "Debug", "leaveMgtReJoin - Request Pairing Status")
            send_zigatecmd_raw(self, "0014", "")  # Request status
        elif duration != 255:
            if int(time()) >= (self.permitTojoin["Starttime"] + 60):
                dur_req = 60
                self.permitTojoin["Duration"] = 60
                self.permitTojoin["Starttime"] = int(time())
                self.log.logging(
                    "BasicOutput", "Debug", "leaveMgtReJoin - switching Zigate in Pairing for %s sec" % dur_req, saddr
                )
                send_zigatecmd_raw(self, "0049", "FFFC" + "%02x" % dur_req + "00")
                self.log.logging("BasicOutput", "Debug", "leaveMgtReJoin - Request Pairing Status")
                send_zigatecmd_raw(self, "0014", "")  # Request status

        # Request a Re-Join and Do not remove children
        _leave = "01"
        _rejoin = "01"
        _rmv_children = "01"
        _dnt_rmv_children = "00"

        datas = saddr + ieee + _rejoin + _dnt_rmv_children
        self.log.logging("BasicOutput", "Status", "Request a rejoin of (%s/%s)" % (saddr, ieee), saddr)
        return send_zigatecmd_raw(self, "0047", datas)


def reset_device(self, nwkid, epout):

    self.log.logging("BasicOutput", "Debug", "reset_device - Send a Device Reset to %s/%s" % (nwkid, epout), nwkid)
    return send_zigatecmd_raw(self, "0050", "02" + nwkid + ZIGATE_EP + epout)


def leaveRequest(self, ShortAddr=None, IEEE=None, RemoveChild=0x00, Rejoin=0x00):
    """
    E_SL_MSG_LEAVE_REQUEST / 0x004C / ZPS_eAplZdoLeaveNetwork
    If you wish to move a whole network branch from under
    the requesting node to a different parent node, set
    bRemoveChildren to FALSE and bRejoin to TRUE.
    """

    _ieee = None

    if IEEE:
        _ieee = IEEE
    else:
        if ShortAddr and ShortAddr in self.ListOfDevices and "IEEE" in self.ListOfDevices[ShortAddr]:
            _ieee = self.ListOfDevices[ShortAddr]["IEEE"]
        else:
            self.log.logging(
                "BasicOutput",
                "Error",
                "leaveRequest - Unable to determine IEEE address for %s %s" % (ShortAddr, IEEE),
                ShortAddr,
                {"Error code": "BOUTPUTS-LEAVE-01", "ListOfDevices": self.ListOfDevices},
            )
            return None

    if Rejoin == 0x00 and ShortAddr:
        ep_list = getListOfEpForCluster(self, ShortAddr, "0000")
        if ep_list:
            self.log.logging(
                "BasicOutput", "Log", "reset_device - Send a Device Reset to %s/%s" % (ShortAddr, ep_list[0]), ShortAddr
            )
            reset_device(self, ShortAddr, ep_list[0])

    _rmv_children = "%02X" % RemoveChild
    _rejoin = "%02X" % Rejoin

    datas = _ieee + _rmv_children + _rejoin
    self.log.logging(
        "BasicOutput",
        "Debug",
        "---------> Sending a leaveRequest - NwkId: %s, IEEE: %s, RemoveChild: %s, Rejoin: %s"
        % (ShortAddr, IEEE, RemoveChild, Rejoin),
        ShortAddr,
    )
    return send_zigatecmd_raw(self, "0047", datas)


def removeZigateDevice(self, IEEE):
    """
    E_SL_MSG_NETWORK_REMOVE_DEVICE / 0x0026 / ZPS_teStatus ZPS_eAplZdoRemoveDeviceReq

    This function can be used (normally by the Co-ordinator/Trust Centre) to request
    another node (such as a Router) to remove one of its children from the network (for
    example, if the child node does not satisfy security requirements).

    The Router receiving this request will ignore the request unless it has originated from
    the Trust Centre or is a request to remove itself. If the request was sent without APS
    layer encryption, the device will ignore the request. If APS layer security is not in use,
    the alternative function ZPS_eAplZdoLeaveNetwork() should be used.


    u64ParentAddr 64-bit IEEE/MAC address of parent to be instructed
    u64ChildAddr 64-bit IEEE/MAC address of child node to be removed
    """

    if IEEE not in self.IEEE2NWK:
        return None

    nwkid = self.IEEE2NWK[IEEE]
    self.log.logging("BasicOutput", "Status", "Remove from Zigate Device = " + " IEEE = " + str(IEEE), nwkid)

    # Do we have to remove a Router or End Device ?
    if mainPoweredDevice(self, nwkid):
        ParentAddr = IEEE
    else:
        if self.ZigateIEEE is None:
            self.log.logging(
                "BasicOutput",
                "Error",
                "Zigae IEEE unknown: %s" % self.ZigateIEEE,
                None,
                {"Error code": "BOUTPUTS-REMOVE-01"},
            )
            return None
        ParentAddr = self.ZigateIEEE

    ChildAddr = IEEE
    return send_zigatecmd_raw(self, "0026", ParentAddr + ChildAddr)


def ballast_Configuration_max_level(self, nwkid, value):
    ListOfEp = getListOfEpForCluster(self, nwkid, "0301")
    if ListOfEp:
        for EPout in ListOfEp:
            write_attribute(
                self, nwkid, ZIGATE_EP, EPout, "0301", "0000", "00", "0011", "20", "%02x" % value, ackIsDisabled=True
            )
            read_attribute(self, nwkid, ZIGATE_EP, EPout, "0301", "00", "00", "0000", 1, "0011", ackIsDisabled=True)


def ballast_Configuration_min_level(self, nwkid, value):
    ListOfEp = getListOfEpForCluster(self, nwkid, "0301")
    if ListOfEp:
        for EPout in ListOfEp:
            write_attribute(
                self, nwkid, ZIGATE_EP, EPout, "0301", "0000", "00", "0010", "20", "%02x" % value, ackIsDisabled=True
            )
            read_attribute(self, nwkid, ZIGATE_EP, EPout, "0301", "00", "00", "0000", 1, "0010", ackIsDisabled=True)


def raw_APS_request(
    self,
    targetaddr,
    dest_ep,
    cluster,
    profileId,
    payload,
    zigate_ep=ZIGATE_EP,
    highpriority=False,
    ackIsDisabled=False,
):
    # This function submits a request to send data to a remote node, with no restrictions
    # on the type of transmission, destination address, destination application profile,
    # destination cluster and destination endpoint number - these destination parameters
    # do not need to be known to the stack or defined in the ZPS configuration. In this
    # sense, this is most general of the Data Transfer functions.

    # The data is sent in an Application Protocol Data Unit (APDU) instance,
    #   Command 0x0530
    #   address mode
    #   target short address 4
    #   source endpoint 2
    #   destination endpoint 2
    #   clusterId 4/
    #   profileId 4
    #   security mode 2
    #   radius 2
    #   data length 2
    #   data Array of 2

    # eSecurityMode is the security mode for the data transfer, one of:
    #         0x00 : ZPS_E_APL_AF_UNSECURE (no security enabled)
    #         0x01 : ZPS_E_APL_AF_SECURE Application-level security using link key and network key)
    #         0x02 : ZPS_E_APL_AF_SECURE_NWK (Network-level security using network key)
    #         0x10 : ZPS_E_APL_AF_SECURE | ZPS_E_APL_AF_EXT_NONCE (Application-level security using link key and network key with the extended NONCE included in the frame)
    #         0x20 : ZPS_E_APL_AF_WILD_PROFILE (May be combined with above flags using OR operator. Sends the message using the wild card profile (0xFFFF) instead of the profile in the associated Simple descriptor)
    # u8Radius is the maximum number of hops permitted to the destination node (zero value specifies that default maximum is to be used)

    SECURITY = 0x02
    RADIUS = 0x00

    security = "%02X" % SECURITY
    radius = "%02X" % RADIUS

    len_payload = (len(payload)) // 2
    len_payload = "%02x" % len_payload

    # APS RAW is always sent in NO-ACK below 31d (included)
    # APS RAW has ACK/NO-ACK option as of 31e
    self.log.logging(
        "inRawAPS",
        "Debug",
        "raw_APS_request - ackIsDisabled: %s Addr: %s Ep: %s Cluster: %s ProfileId: %s Payload: %s"
        % (ackIsDisabled, targetaddr, dest_ep, cluster, profileId, payload),
        dest_ep,
    )

    # In case of Firmware < 31e 0x0530 is always on noack even if address mode 0x02 is used.
    overwrittenackIsDisabled = ackIsDisabled
    if self.FirmwareVersion and self.FirmwareVersion <= "031d":
        ackIsDisabled = False  # Force the usage of 0x02 address mode
        overwrittenackIsDisabled = True  # Indicate that we are without Ack

    # self.log.logging( "BasicOutput", "Log", "Raw APS - ackIsDisabled: %s overwrittenackIsDisabled: %s" %(ackIsDisabled,overwrittenackIsDisabled))
    if self.pluginconf.pluginConf["ieeeForRawAps"]:
        ieee = self.ListOfDevices[targetaddr]["IEEE"]
        if ackIsDisabled:
            return send_zigatecmd_raw(
                self,
                "0530",
                "08" + ieee + zigate_ep + dest_ep + cluster + profileId + security + radius + len_payload + payload,
                highpriority,
                ackIsDisabled=overwrittenackIsDisabled,
            )
        return send_zigatecmd_raw(
            self,
            "0530",
            "03" + ieee + zigate_ep + dest_ep + cluster + profileId + security + radius + len_payload + payload,
            highpriority,
            ackIsDisabled=overwrittenackIsDisabled,
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


def read_attribute(
    self, addr, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, lenAttr, Attr, ackIsDisabled=True
):

    if self.pluginconf.pluginConf["RawReadAttribute"]:
        return rawaps_read_attribute_req(
            self, addr, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, Attr, ackIsDisabled
        )

    if ackIsDisabled:
        return send_zigatecmd_zcl_noack(
            self,
            addr,
            "0100",
            EpIn + EpOut + Cluster + direction + manufacturer_spec + manufacturer + "%02x" % lenAttr + Attr,
        )
    return send_zigatecmd_zcl_ack(
        self,
        addr,
        "0100",
        EpIn + EpOut + Cluster + direction + manufacturer_spec + manufacturer + "%02x" % lenAttr + Attr,
    )


def write_attribute(
    self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled=True
):
    #  write_attribute unicast , all with ack in < 31d firmware, ack/noack works since 31d
    #
    direction = "00"
    if data_type == "42":  # String
        # In case of Data Type 0x42 ( String ), we have to add the length of string before the string.
        data = "%02x" % (len(data) // 2) + data

    lenght = "01"  # Only 1 attribute

    datas = ZIGATE_EP + EPout + clusterID
    datas += direction + manuf_spec + manuf_id
    datas += lenght + attribute + data_type + data
    self.log.logging("BasicOutput", "Debug", "write_attribute for %s/%s - >%s<" % (key, EPout, datas), key)

    if self.pluginconf.pluginConf["RawWritAttribute"]:
        i_sqn = rawaps_write_attribute_req(
            self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled
        )
    else:
        # ATTENTION "0110" with firmware 31c are always call with Ack (overwriten by firmware)
        # if ackIsDisabled:
        #    i_sqn = send_zigatecmd_zcl_noack(self, key, "0110", str(datas))
        # else:
        #    i_sqn = send_zigatecmd_zcl_ack(self, key, "0110", str(datas))
        # For now send Write Attribute ALWAYS with Ack.
        i_sqn = send_zigatecmd_zcl_ack(self, key, "0110", str(datas))

    set_isqn_datastruct(self, "WriteAttributes", key, EPout, clusterID, attribute, i_sqn)

    set_request_datastruct(
        self,
        "WriteAttributes",
        key,
        EPout,
        clusterID,
        attribute,
        data_type,
        EPin,
        EPout,
        manuf_id,
        manuf_spec,
        data,
        ackIsDisabled,
        "requested",
    )
    set_timestamp_datastruct(self, "WriteAttributes", key, EPout, clusterID, int(time()))


def write_attributeNoResponse(self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data):
    """write_atttribute broadcast . ack impossible on broadcast"""
    # if key == 'ffff':
    #    addr_mode = '04'
    direction = "00"

    if data_type == "42":  # String
        # In case of Data Type 0x42 ( String ), we have to add the length of string before the string.
        data = "%02x" % (len(data) // 2) + data

    lenght = "01"  # Only 1 attribute

    datas = ZIGATE_EP + EPout + clusterID
    datas += direction + manuf_spec + manuf_id
    datas += lenght + attribute + data_type + data
    self.log.logging("BasicOutput", "Log", "write_attribute No Reponse for %s/%s - >%s<" % (key, EPout, datas), key)

    # Firmware <= 31c are in fact with ACK
    return send_zigatecmd_zcl_noack(self, key, "0113", str(datas))


def rawaps_read_attribute_req(
    self, NwkId, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, Attr, ackIsDisabled=True
):

    self.log.logging(
        "inRawAPS", "Log", "rawaps_read_attribute_req %s/%s Cluster: %s Attribute: %s" % (NwkId, EpOut, Cluster, Attr)
    )
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

    sqn = get_and_inc_SQN(self, NwkId)

    payload = fcf
    if manufacturer_spec == "01":
        payload += manufacturer_spec + manufacturer[4:2] + manufacturer[0:2]

    payload += sqn + cmd
    idx = 0
    while idx < len(Attr):
        attribute = Attr[idx : idx + 4]
        idx += 4
        payload += "%04x" % struct.unpack(">H", struct.pack("H", int(attribute, 16)))[0]

    raw_APS_request(self, NwkId, EpOut, Cluster, "0104", payload, zigate_ep=EpIn, ackIsDisabled=ackIsDisabled)


def rawaps_write_attribute_req(
    self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled=True
):

    self.log.logging(
        "inRawAPS",
        "Log",
        "rawaps_write_attribute_req %s/%s Cluster: %s Attribute: %s DataType: %s Value: %s"
        % (key, EPout, clusterID, attribute, data_type, data),
    )
    cmd = "02"  # Read Attribute Command Identifier
    cluster_frame = 0b00010000
    if manuf_spec == "01":
        cluster_frame += 0b00000100
    fcf = "%02x" % cluster_frame

    sqn = get_and_inc_SQN(self, key)

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

    raw_APS_request(self, key, EPout, clusterID, "0104", payload, zigate_ep=EPin, ackIsDisabled=ackIsDisabled)


## Scene
def scene_membership_request(self, nwkid, ep, groupid="0000"):

    datas = ZIGATE_EP + ep + groupid
    return send_zigatecmd_zcl_noack(self, nwkid, "00A6", datas)


def identifyEffect(self, nwkid, ep, effect="Blink"):

    """
    Blink   / Light is switched on and then off (once)
    Breathe / Light is switched on and off by smoothly increasing and
              then decreasing its brightness over a one-second period,
              and then this is repeated 15 times
    Okay    / •  Colour light goes green for one second
              •  Monochrome light flashes twice in one second
    Channel change / •  Colour light goes orange for 8 seconds
                     •  Monochrome light switches to
                        maximum brightness for 0.5 s and then to
                        minimum brightness for 7.5 s
    Finish effect  /  Current stage of effect is completed and then identification mode is
                      terminated (e.g. for the Breathe effect, only the current one-second
                      cycle will be completed)
    Stop effect    /  Current effect and id


    A variant of the selected effect can also be specified, but currently only the default
    (as described above) is available.
    """

    effect_command = {
        "Blink": 0x00,
        "Breathe": 0x01,
        "Okay": 0x02,
        "ChannelChange": 0x0B,
        "FinishEffect": 0xFE,
        "StopEffect": 0xFF,
    }

    identify = any("0300" in self.ListOfDevices[nwkid]["Ep"][iterEp] for iterEp in self.ListOfDevices[nwkid]["Ep"])

    if (
        "ZDeviceID" in self.ListOfDevices[nwkid]
        and self.ListOfDevices[nwkid]["ZDeviceID"] != {}
        and self.ListOfDevices[nwkid]["ZDeviceID"] != ""
        and int(self.ListOfDevices[nwkid]["ZDeviceID"], 16) in ZLL_DEVICES
    ):
        identify = True

    if not identify:
        return None

    if effect not in effect_command:
        effect = "Blink"

    # datas = "02" + "%s"%(nwkid) + ZIGATE_EP + ep + "%02x"%(effect_command[effect])  + "%02x" %0
    datas = ZIGATE_EP + ep + "%02x" % (effect_command[effect]) + "%02x" % 0
    return send_zigatecmd_zcl_noack(self, nwkid, "00E0", datas)


def set_PIROccupiedToUnoccupiedDelay(self, key, delay, ListOfEp=None):

    cluster_id = "0406"
    attribute = "0010"
    data_type = "21"
    manuf_id = "0000"
    manuf_spec = "00"
    if ListOfEp is None:
        ListOfEp = getListOfEpForCluster(self, key, cluster_id)
    for EPout in ListOfEp:
        data = "%04x" % delay
        self.log.logging(
            "BasicOutput", "Log", "set_PIROccupiedToUnoccupiedDelay for %s/%s - delay: %s" % (key, EPout, delay), key
        )
        if attribute in self.ListOfDevices[key]["Ep"][EPout][cluster_id]:
            del self.ListOfDevices[key]["Ep"][EPout][cluster_id][attribute]
        return write_attribute(
            self,
            key,
            ZIGATE_EP,
            EPout,
            cluster_id,
            manuf_id,
            manuf_spec,
            attribute,
            data_type,
            data,
            ackIsDisabled=False,
        )


def set_poweron_afteroffon(self, key, OnOffMode=0xFF):
    # OSRAM/LEDVANCE
    # 0xfc0f --> Command 0x01
    # 0xfc01 --> Command 0x01

    # Tuya Blitzworl
    # 0x0006 / 0x8002  -> 0x00 Off ; 0x01 On ; 0x02 Previous state

    # Ikea / Philips/ Legrand
    # 0x0006 / 0x4003 -> 0x00 Off, 0x01 On, 0xff Previous

    self.log.logging("BasicOutput", "Debug", "set_PowerOn_OnOff for %s - OnOff: %s" % (key, OnOffMode), key)
    if key not in self.ListOfDevices:
        self.log.logging("BasicOutput", "Error", "set_PowerOn_OnOff for %s not found" % (key), key)
        return
    model_name = ""
    if "Model" in self.ListOfDevices[key]:
        model_name = self.ListOfDevices[key]["Model"]
    manuf_spec = "00"
    manuf_id = "0000"

    ListOfEp = getListOfEpForCluster(self, key, "0006")
    cluster_id = "0006"
    attribute = "4003"

    if model_name in ("TS0121", "TS0115"):
        attribute = "8002"
        if OnOffMode == 0xFF:
            OnOffMode = 0x02

    data_type = "30"  #
    ListOfEp = getListOfEpForCluster(self, key, "0006")
    for EPout in ListOfEp:
        data = "%02x" % OnOffMode
        self.log.logging(
            "BasicOutput", "Debug", "set_PowerOn_OnOff for %s/%s - OnOff: %s" % (key, EPout, OnOffMode), key
        )
        if attribute in self.ListOfDevices[key]["Ep"][EPout]["0006"]:
            del self.ListOfDevices[key]["Ep"][EPout]["0006"][attribute]
        return write_attribute(
            self,
            key,
            ZIGATE_EP,
            EPout,
            cluster_id,
            manuf_id,
            manuf_spec,
            attribute,
            data_type,
            data,
            ackIsDisabled=True,
        )


def ieee_addr_request(self, nwkid):
    u8RequestType = "00"
    u8StartIndex = "00"
    sendZigateCmd(self, "0041", "02" + nwkid + u8RequestType + u8StartIndex)


def unknown_device_nwkid(self, nwkid):

    if nwkid in self.UnknownDevices:
        return

    self.log.logging("BasicOutput", "Debug", "unknown_device_nwkid is DISaBLED for now !!!", nwkid)

    self.UnknownDevices.append(nwkid)
    # If we didn't find it, let's trigger a NetworkMap scan if not one in progress
    if self.networkmap and not self.networkmap.NetworkMapPhase():
        self.networkmap.start_scan()
    ieee_addr_request(self, nwkid)


def send_default_response(
    self,
    Nwkid,
    srcEp,
    cluster,
    Direction,
    bDisableDefaultResponse,
    ManufacturerSpecific,
    u16ManufacturerCode,
    FrameType,
    response_to_command,
    sqn,
):

    # Response_To_Command
    # 0x01: Read Attributes Response
    # 0x02: Write Attribute
    # 0x03: Write Attributes Undivided
    # 0x04: Write Attributes Response
    # 0x05: Write Attributes No Response
    # 0x06: Configure Reporting
    # 0x07: Configure Reporting Response
    # 0x08: Read reporting Configuration
    # 0x09: Read Reporting Configuration Response
    # 0x0a: Report Attribute
    # 0x0b: Default response
    # 0x0c: Discover Attributes
    # 0x0d: Discober Attribute Response

    if Nwkid not in self.ListOfDevices:
        return

    # Take the reverse direction
    Direction = "%02x" % (not (int(Direction, 16)))

    fcf = build_fcf("00", ManufacturerSpecific, Direction, "01")
    cmd = "0b"  # Default response command
    status = "00"
    payload = fcf + sqn
    if ManufacturerSpecific == "01":
        payload += u16ManufacturerCode[2:4] + u16ManufacturerCode[0:2]
    payload += cmd + response_to_command + status
    raw_APS_request(
        self, Nwkid, srcEp, cluster, "0104", payload, zigate_ep=ZIGATE_EP, highpriority=True, ackIsDisabled=True
    )
    self.log.logging(
        "BasicOutput",
        "Debug",
        "send_default_response - [%s] %s/%s on cluster: %s with command: %s"
        % (sqn, Nwkid, srcEp, cluster, response_to_command),
    )


def disable_firmware_default_response(self, mode="00"):
    # Available as of Firmware 31e, it's allow to disable the disable the Default Response, and leave it to the plugin to send if needed.

    if mode not in ("00", "01"):
        self.log.logging("BasicOutput", "Error", "disable_firmware_default_response unknown mode: %s", mode)
        return
    sendZigateCmd(self, "0003", mode)


def do_Many_To_One_RouteRequest(self):

    bCacheRoute = "00"  # FALSE do not store routes
    u8Radius = "00"  # Maximum number of hops of route discovery message

    sendZigateCmd(self, "004F", bCacheRoute + u8Radius)
    self.log.logging("BasicOutput", "Debug", "do_Many_To_One_RouteRequest call !")


def mgt_routing_req(self, nwkid, start_index):

    if "RoutingTable" not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]["RoutingTable"] = {}
        self.ListOfDevices[nwkid]["RoutingTable"]["Devices"] = []
        self.ListOfDevices[nwkid]["RoutingTable"]["SQN"] = 0
    else:
        self.ListOfDevices[nwkid]["RoutingTable"]["SQN"] += 1

    payload = "%02x" % self.ListOfDevices[nwkid]["RoutingTable"]["SQN"] + start_index
    raw_APS_request(
        self,
        nwkid,
        "00",
        "0032",
        "0000",
        payload,
        zigate_ep="00",
        highpriority=False,
        ackIsDisabled=False,
    )


def initiate_change_channel(self, new_channel):

    self.log.logging("BasicOutput", "Log", "initiate_change_channel - channel: %s" % new_channel)
    scanDuration = "fe"  # Initiate a change

    channel_mask = "%08x" % maskChannel(self, new_channel)
    target_address = "ffff"  # Broadcast to all devices

    datas = target_address + channel_mask + scanDuration + "00" + "0000"
    self.log.logging("BasicOutput", "Log", "initiate_change_channel - 004A %s" % datas)
    send_zigatecmd_raw(self, "004A", datas)
    if "0000" in self.ListOfDevices:
        self.ListOfDevices["0000"]["CheckChannel"] = new_channel
