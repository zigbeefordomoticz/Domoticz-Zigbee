#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: very low level to send command to ZiGate

    Description: 

"""

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


def raw_APS_request( self, targetaddr, dest_ep, cluster, profileId, payload, zigate_ep=ZIGATE_EP, highpriority=False, ackIsDisabled=False, ):
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