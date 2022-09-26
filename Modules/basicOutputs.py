#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: basicOutputs

    Description: All direct communications towards Zigate

"""


import struct
from datetime import datetime
from time import time

from Zigbee.encoder_tools import decode_endian_data
from Zigbee.zclCommands import (zcl_attribute_discovery_request,
                                zcl_get_list_attribute_extended_infos,
                                zcl_identify_send, zcl_read_attribute,
                                zcl_write_attribute,
                                zcl_write_attributeNoResponse,
                                zcl_identify_trigger_effect)
from Zigbee.zdpCommands import (zdp_get_permit_joint_status,
                                zdp_IEEE_address_request,
                                zdp_management_leave_request,
                                zdp_management_network_update_request,
                                zdp_many_to_one_route_request,
                                zdp_permit_joining_request,
                                zdp_raw_nwk_update_request, zdp_reset_device)
from Zigbee.zdpRawCommands import (zdp_management_binding_table_request,
                                   zdp_management_routing_table_request)

from Modules.sendZigateCommand import (raw_APS_request, send_zigatecmd_raw,
                                       send_zigatecmd_zcl_ack,
                                       send_zigatecmd_zcl_noack)
from Modules.tools import (build_fcf, get_and_inc_ZDP_SQN,
                           getListOfEpForCluster, is_ack_tobe_disabled, is_hex,
                           mainPoweredDevice, set_isqn_datastruct,
                           set_request_datastruct, set_timestamp_datastruct)
from Modules.zigateCommands import (zigate_blueled,
                                    zigate_firmware_default_response,
                                    zigate_get_nwk_state, zigate_get_time,
                                    zigate_remove_device, zigate_set_channel,
                                    zigate_set_extended_PanID, zigate_set_mode,
                                    zigate_set_time, zigate_start_nwk)
from Modules.zigateConsts import ZIGATE_EP, ZLL_DEVICES


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
    return "01" if nwkid == "0000" else "00"


def PermitToJoin(self, Interval, TargetAddress="FFFC"):

    if Interval == "00" and self.pluginconf.pluginConf["forceClosingAllNodes"]:
        for x in self.ListOfDevices:
            if mainPoweredDevice(self, x):
                self.log.logging("BasicOutput", "Log", "Request router: %s to close the network" % x)
                #send_zigatecmd_raw(self, "0049", x + Interval + get_TC_significance(x))
                zdp_permit_joining_request(self, x , Interval , get_TC_significance(x))
    else:
        #send_zigatecmd_raw(self, "0049", TargetAddress + Interval + get_TC_significance(TargetAddress))
        zdp_permit_joining_request(self, TargetAddress , Interval , get_TC_significance(TargetAddress))
    if TargetAddress in ("FFFC", "0000"):
        # Request a Status to update the various permitTojoin structure
        zdp_get_permit_joint_status(self)
        #send_zigatecmd_raw(self, "0014", "")  # Request status


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
        zigate_set_mode(self, 0x00)

        self.log.logging("BasicOutput", "Status", "Start network")
        zigate_start_nwk(self)
        #send_zigatecmd_raw(self, "0024", "")  # Start Network

        self.log.logging("BasicOutput", "Status", "Set Zigate as a TimeServer")
        setTimeServer(self)

        self.log.logging("BasicOutput", "Debug", "Request network Status")
        zdp_get_permit_joint_status(self)
        zigate_get_nwk_state(self)
        zdp_get_permit_joint_status(self)
        #send_zigatecmd_raw(self, "0014", "")  # Request status
        #send_zigatecmd_raw(self, "0009", "")  # Request status

        # Request a Status to update the various permitTojoin structure
        #send_zigatecmd_raw(self, "0014", "")  # Request status


def setTimeServer(self):

    EPOCTime = datetime(2000, 1, 1)
    UTCTime = int((datetime.now() - EPOCTime).total_seconds())
    # self.log.logging( "BasicOutput", "Status", "setTimeServer - Setting UTC Time to : %s" %( UTCTime) )

    #send_zigatecmd_raw(self, "0016", data)
    zigate_set_time(self, "%08x" % UTCTime)
    # Request Time
    #send_zigatecmd_raw(self, "0017", "")
    zigate_get_time(self)


def zigateBlueLed(self, OnOff):

    if OnOff:
        self.log.logging("BasicOutput", "Log", "Switch Blue Led On")
        zigate_blueled(self, "01")
        #send_zigatecmd_raw(self, "0018", "01")
    else:
        self.log.logging("BasicOutput", "Log", "Switch Blue Led off")
        #send_zigatecmd_raw(self, "0018", "00")
        zigate_blueled(self, "00")


def getListofAttribute(self, nwkid, EpOut, cluster, start_attribute="0000", manuf_specific="00", manuf_code="0000"):

    #datas = ZIGATE_EP + EpOut + cluster + start_attribute + "00" + manuf_specific + manuf_code + "01"
    #self.log.logging("BasicOutput", "Debug", "attribute_discovery_request - " + str(datas), nwkid)
    #send_zigatecmd_zcl_noack(self, nwkid, "0140", datas)
    zcl_attribute_discovery_request(self, nwkid, ZIGATE_EP, EpOut, cluster, start_attribute, manuf_specific, manuf_code)

def getListofAttributeExtendedInfos( self, nwkid, EpOut, cluster, start_attribute="0000", manuf_specific="00", manuf_code="0000"):

    #datas = ZIGATE_EP + EpOut + cluster + start_attribute + "00" + manuf_specific + manuf_code + "01"
    #self.log.logging("BasicOutput", "Debug", "attribute_discovery_request - " + str(datas), nwkid)
    #send_zigatecmd_zcl_noack(self, nwkid, "0141", datas)
    zcl_get_list_attribute_extended_infos(self, nwkid, ZIGATE_EP, EpOut, cluster, start_attribute, manuf_specific, manuf_code)


#def initiateTouchLink(self):
#
#    self.log.logging("BasicOutput", "Status", "initiate Touch Link")
#    send_zigatecmd_raw(self, "00D0", "")


#def factoryresetTouchLink(self):
#
#    self.log.logging("BasicOutput", "Status", "Factory Reset Touch Link Over The Air")
#    send_zigatecmd_raw(self, "00D2", "")


def identifySend(self, nwkid, ep, duration=0, withAck=False):
    zcl_identify_send( self, nwkid, ep, duration, withAck)


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
    zigate_set_channel(self, "%08.x" % (mask))
    #send_zigatecmd_raw(self, "0021", "%08.x" % (mask))


def channelChangeInitiate(self, channel):

    self.log.logging(
        "BasicOutput", "Status", "Change channel from [%s] to [%s] with nwkUpdateReq" % (self.currentChannel, channel)
    )
    self.log.logging("BasicOutput", "Log", "Not Implemented")
    # NwkMgtUpdReq( self, channel, 'change')


def channelChangeContinue(self):

    self.log.logging("BasicOutput", "Status", "Restart network")
    #send_zigatecmd_raw(self, "0024", "")  # Start Network
    zigate_start_nwk(self)
    #send_zigatecmd_raw(self, "0009", "")  # In order to get Zigate IEEE and NetworkID
    zigate_get_nwk_state(self)


def setExtendedPANID(self, extPANID):
    """
    setExtendedPANID MUST be call after an erase PDM. If you change it
    after having paired some devices, they won't be able to reach you anymore
    Extended PAN IDs (EPIDs) are 64-bit numbers that uniquely identify a PAN.
    ZigBee communicates using the shorter 16-bit PAN ID for all communication except one.
    """

    #datas = "%016x" % extPANID
    #self.log.logging("BasicOutput", "Debug", "set ExtendedPANID - %016x " % (extPANID))
    #send_zigatecmd_raw(self, "0020", datas)
    zigate_set_extended_PanID(self, "%016x" % extPANID)


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
            zdp_get_permit_joint_status(self)
            #send_zigatecmd_raw(self, "0014", "")  # Request status
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
                zdp_get_permit_joint_status(self)
                #send_zigatecmd_raw(self, "0014", "")  # Request status

        # Request a Re-Join and Do not remove children
        _leave = "01"
        _rejoin = "01"
        _rmv_children = "01"
        _dnt_rmv_children = "00"

        self.log.logging("BasicOutput", "Status", "Request a rejoin of (%s/%s)" % (saddr, ieee), saddr)
        return zdp_management_leave_request(self, saddr, ieee, _rejoin, _dnt_rmv_children)



def reset_device(self, nwkid, epout):

    self.log.logging("BasicOutput", "Debug", "reset_device - Send a Device Reset to %s/%s" % (nwkid, epout), nwkid)
    #return send_zigatecmd_raw(self, "0050", "02" + nwkid + ZIGATE_EP + epout)
    return zdp_reset_device(self, nwkid, ZIGATE_EP, epout)  


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

    #datas = _ieee + _rmv_children + _rejoin
    self.log.logging(
        "BasicOutput",
        "Debug",
        "---------> Sending a leaveRequest - NwkId: %s, IEEE: %s, RemoveChild: %s, Rejoin: %s"
        % (ShortAddr, IEEE, RemoveChild, Rejoin),
        ShortAddr,
    )
    return zdp_management_leave_request(self, ShortAddr, _ieee, _rejoin, _rmv_children)
    #return send_zigatecmd_raw(self, "0047", datas)


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
        if self.ControllerIEEE is None:
            self.log.logging(
                "BasicOutput",
                "Error",
                "Zigae IEEE unknown: %s" % self.ControllerIEEE,
                None,
                {"Error code": "BOUTPUTS-REMOVE-01"},
            )
            return None
        ParentAddr = self.ControllerIEEE

    ChildAddr = IEEE
    return zigate_remove_device(self, ParentAddr, ChildAddr)
    #return send_zigatecmd_raw(self, "0026", ParentAddr + ChildAddr)


def ballast_Configuration_max_level(self, nwkid, value):
    ListOfEp = getListOfEpForCluster(self, nwkid, "0301")
    if ListOfEp:
        for EPout in ListOfEp:
            write_attribute(
                self, nwkid, ZIGATE_EP, EPout, "0301", "0000", "00", "0011", "20", "%02x" % value, ackIsDisabled=False
            )
            read_attribute(self, nwkid, ZIGATE_EP, EPout, "0301", "00", "00", "0000", 1, "0011", ackIsDisabled=False)


def ballast_Configuration_min_level(self, nwkid, value):
    ListOfEp = getListOfEpForCluster(self, nwkid, "0301")
    if ListOfEp:
        for EPout in ListOfEp:
            write_attribute( self, nwkid, ZIGATE_EP, EPout, "0301", "0000", "00", "0010", "20", "%02x" % value, ackIsDisabled=False)
            read_attribute(self, nwkid, ZIGATE_EP, EPout, "0301", "00", "00", "0000", 1, "0010", ackIsDisabled=False)

def read_attribute(self, nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, lenAttr, Attr, ackIsDisabled=False):
    return zcl_read_attribute(self, nwkid, EpIn, EpOut, Cluster, direction, manufacturer_spec, manufacturer, lenAttr, Attr, ackIsDisabled)

def write_attribute( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled=False ):
    i_sqn = zcl_write_attribute( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled=ackIsDisabled )
    
    set_isqn_datastruct(self, "WriteAttributes", key, EPout, clusterID, attribute, i_sqn)
    set_request_datastruct( self, "WriteAttributes", key, EPout, clusterID, attribute, data_type, EPin, EPout, manuf_id, manuf_spec, data, ackIsDisabled, "requested", )
    set_timestamp_datastruct(self, "WriteAttributes", key, EPout, clusterID, int(time()))

def write_attributeNoResponse(self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data):
    return zcl_write_attributeNoResponse(self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data)


# Scene
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

    return zcl_identify_trigger_effect(self, nwkid, ep, "%02x" %effect_command[effect], "%02x" % 0)



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
    data_type = "30"  #

    if model_name in ( "TS0121", "TS0115", "TS011F-multiprise", "TS011F-2Gang-switches", "TS011F-plug" , "TS0004-_TZ3000_excgg5kb", ):
        attribute = "8002"
        if OnOffMode == 0xFF:
            OnOffMode = 0x02

    if model_name in ( "TS0004-_TZ3000_excgg5kb",):
        ListOfEp = ( "01", )
        
    self.log.logging( "BasicOutput", "Debug", "set_PowerOn_OnOff for %s - OnOff: %s %s %s" % (key, OnOffMode, attribute, ListOfEp), key )
    
    for EPout in ListOfEp:
        data = "%02x" % int(OnOffMode)
        self.log.logging( "BasicOutput", "Debug", "set_PowerOn_OnOff for %s/%s - OnOff: %s" % (key, EPout, OnOffMode), key )
        if attribute in self.ListOfDevices[key]["Ep"][EPout]["0006"]:
            del self.ListOfDevices[key]["Ep"][EPout]["0006"][attribute]
        return write_attribute( self, key, ZIGATE_EP, EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data, ackIsDisabled=True, )


def unknown_device_nwkid(self, nwkid):

    if nwkid in self.UnknownDevices:
        return

    self.log.logging("BasicOutput", "Debug", "unknown_device_nwkid is DISaBLED for now !!!", nwkid)

    self.UnknownDevices.append(nwkid)
    # If we didn't find it, let's trigger a NetworkMap scan if not one in progress
    if self.networkmap and not self.networkmap.NetworkMapPhase():
        self.networkmap.start_scan()


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
    zigate_firmware_default_response(self, mode)
    #sendZigateCmd(self, "0003", mode)


def do_Many_To_One_RouteRequest(self):

    bCacheRoute = "00"  # FALSE do not store routes
    u8Radius = "00"  # Maximum number of hops of route discovery message

    if self.ZiGateModel == 2 and int(self.FirmwareMajorVersion, 16) >= 5 and int(self.FirmwareVersion, 16) >= 0x0320:
        #sendZigateCmd(self, "004F", bCacheRoute + u8Radius)
        zdp_many_to_one_route_request(self, bCacheRoute, u8Radius)
        self.log.logging("BasicOutput", "Log", "do_Many_To_One_RouteRequest call !")


def mgt_routing_req(self, nwkid, start_index="00"):

    self.log.logging("BasicOutput", "Debug", "mgt_routing_req - %s" % nwkid)

    #if not (
    #    self.ZiGateModel == 2 and int(self.FirmwareMajorVersion, 16) >= 5 and int(self.FirmwareVersion, 16) >= 0x0320
    #):
    #    return
    self.log.logging("BasicOutput", "Debug", "mgt_routing_req - %s" % nwkid)
    if "RoutingTable" not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]["RoutingTable"] = {'Devices': []}

    payload = get_and_inc_ZDP_SQN(self, nwkid) + start_index
    zdp_management_routing_table_request(self, nwkid, payload)

def mgt_binding_table_req( self, nwkid, start_index="00"):

    #if not (
    #    self.ZiGateModel == 2 and int(self.FirmwareMajorVersion, 16) >= 5 and int(self.FirmwareVersion, 16) >= 0x0320
    #):
    #    return

    self.log.logging("BasicOutput", "Debug", "mgt_binding_table_req - %s" % nwkid)

    if "BindingTable" not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]["BindingTable"] = {'Devices': []}

    payload = get_and_inc_ZDP_SQN(self, nwkid) + start_index
    zdp_management_binding_table_request(self, nwkid, payload)


def initiate_change_channel(self, new_channel):

    self.log.logging("BasicOutput", "Debug", "initiate_change_channel - channel: %s" % new_channel)
    scanDuration = "fe"  # Initiate a change
 
    channel_mask = "%08x" % maskChannel(self, new_channel)
    target_address = "ffff"  # Broadcast to all devices

    if "ControllerInRawMode" in self.pluginconf.pluginConf and self.pluginconf.pluginConf["ControllerInRawMode"]:
        channel_mask = decode_endian_data(channel_mask, "1b")
        zdp_raw_nwk_update_request(self, target_address, channel_mask, scanDuration, scancount="00", nwkupdateid="01")
    else:
        zdp_management_network_update_request(self, target_address , channel_mask , scanDuration , scan_repeat="00" , nwk_updateid="01")
    #send_zigatecmd_raw(self, "004A", datas)
    zigate_get_nwk_state(self)
    if "0000" in self.ListOfDevices:
        self.ListOfDevices["0000"]["CheckChannel"] = new_channel
