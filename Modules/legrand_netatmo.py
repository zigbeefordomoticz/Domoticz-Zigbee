#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_output.py

    Description: All communications towards Zigate

"""

import struct
from time import time

import Domoticz

from Modules.basicOutputs import (read_attribute, write_attribute,
                                  write_attributeNoResponse)
from Modules.bindings import bindDevice, unbindDevice
from Modules.domoMaj import MajDomoDevice
from Modules.readAttributes import (ReadAttributeRequest_0b04_050b,
                                    ReadAttributeRequest_0001,
                                    ReadAttributeRequest_0006_0000,
                                    ReadAttributeRequest_fc01,
                                    ReadAttributeRequest_fc40)
from Modules.sendZigateCommand import raw_APS_request
from Modules.tools import (extract_info_from_8085, get_and_inc_ZCL_SQN,
                           is_ack_tobe_disabled,
                           retreive_cmd_payload_from_8002)
from Modules.zigateConsts import (HEARTBEAT, LEGRAND_REMOTES, MAX_LOAD_ZIGATE,
                                  ZIGATE_EP)

LEGRAND_CLUSTER_FC01 = {
    "Dimmer switch wo neutral": {"EnableLedInDark": "0001", "EnableDimmer": "0000", "EnableLedIfOn": "0002"},
    "Connected outlet": {"EnableLedIfOn": "0002"},
    "Mobile outlet": {"EnableLedIfOn": "0002"},
    "Shutter switch with neutral": {"EnableLedShutter": "0001"},
    "Micromodule switch": {"None": "None"},
}
 
def pollingLegrand(self, key):

    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """
    return False


def callbackDeviceAwake_Legrand(self, Devices, NwkId, EndPoint, cluster):

    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part
    """

    # Domoticz.Log("callbackDeviceAwake_Legrand - Nwkid: %s, EndPoint: %s cluster: %s" \
    #        %(NwkId, EndPoint, cluster))

    return


def legrandReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):
    self.log.logging(
        "Legrand",
        "Debug",
        "legrandReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s"
        % (srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload),
    )
    # At Device Annoucement 0x00 and 0x05 are sent by device
    default_response, GlobalCommand, Sqn, ManufacturerCode, Command, Data = retreive_cmd_payload_from_8002(MsgPayload)
    self.log.logging(
        "Legrand",
        "Debug",
        " NwkId: %s/%s Cluster: %s Command: %s Data: %s" % (srcNWKID, srcEp, ClusterID, Command, Data),
    )

    if ClusterID == "0102" and Command == "00":  # No data (Cluster 0x0102)
        pass
    elif ClusterID == "0102" and Command == "01":  # No data (Cluster 0x0102)
        pass
    elif ClusterID == "fc01" and Command == "04":  # Write Attribute Responsee
        pass
    elif ClusterID == "fc01" and Command == "05":
        # Get _Ieee of Shutter Device
        _ieee = "%08x" % struct.unpack("q", struct.pack(">Q", int(Data[0:16], 16)))[0]
        assign_group_membership_to_legrand_remote(
            self,
            srcNWKID,
            srcEp,
        )

    elif ClusterID == "fc01" and Command == "09":
        # IEEE of End Device (remote  )
        _ieee = "%08x" % struct.unpack("q", struct.pack(">Q", int(Data[0:16], 16)))[0]
        leftright = Data[16:18] if len(Data) == 18 else None
        self.log.logging("Legrand", "Debug", "---> Decoding cmd 0x09 Ieee: %s leftright: %s" % (_ieee, leftright))
        assign_group_membership_to_legrand_remote(self, srcNWKID, srcEp, leftright)

    elif ClusterID == "fc01" and Command == "0a":
        LegrandGroupMemberShip = Data[0:4]
        _ieee = "%08x" % struct.unpack("q", struct.pack(">Q", int(Data[4:20], 16)))[0]  # IEEE of Device
        _code = Data[20:24]
        self.log.logging(
            "Legrand",
            "Debug",
            "---> Decoding cmd: 0x0a Group: %s, Ieee: %s Code: %s" % (LegrandGroupMemberShip, _ieee, _code),
        )
        status = "00"
        # _ieee = '%08x' %struct.unpack('q',struct.pack('>Q',int(ieee,16)))[0]
        _ieee = "4fa5820000740400"  # IEEE du Dimmer
        sendFC01Command(self, Sqn, srcNWKID, srcEp, ClusterID, "10", status + _code + _ieee)


def assign_group_membership_to_legrand_remote(self, NwkId, Ep, leftright=None):
    sqn = get_and_inc_ZCL_SQN(self, NwkId)
    cmd = "08"
    if leftright:
        cmd = "0c"
        self.log.logging(
            "Legrand", "Debug", "assign_group_membership_to_legrand_remote %s lefright: %s" % (NwkId, leftright)
        )

    groupid = get_groupid_for_remote(self, NwkId, Ep, leftright)
    if groupid:
        LegrandGroupMemberShip = "%04x" % struct.unpack("H", struct.pack(">H", int(groupid, 16)))[0]
        if leftright:
            sendFC01Command(self, sqn, NwkId, Ep, "fc01", cmd, LegrandGroupMemberShip + leftright)
        else:
            sendFC01Command(self, sqn, NwkId, Ep, "fc01", cmd, LegrandGroupMemberShip)


def get_groupid_for_remote(self, NwkId, Ep, leftright):
    GroupId = None
    if "Legrand" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Legrand"] = {}
    if "RemoteGroup" not in self.ListOfDevices[NwkId]["Legrand"]:
        self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"] = {}
    if leftright:
        if leftright not in self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"]:
            self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"][leftright] = None
        if self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"][leftright]:
            return self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"][leftright]
    else:
        if "Single" not in self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"]:
            self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"]["Single"] = None
        if self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"]["Single"]:
            return self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"]["Single"]

    # We need to create a groupId
    if self.groupmgt:
        GroupId = self.groupmgt.get_available_grp_id(0xFEFE, 0xFE00)
        if leftright:
            self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"][leftright] = GroupId
        else:
            self.ListOfDevices[NwkId]["Legrand"]["RemoteGroup"]["Single"] = GroupId
        if GroupId:
            self.groupmgt.add_group_member_ship_from_remote(NwkId, Ep, GroupId)
    return GroupId


def sendFC01Command(self, sqn, nwkid, ep, ClusterID, cmd, data):
    self.log.logging("Legrand", "Debug", "sendFC01Command Cmd: %s Data: %s" % (cmd, data))
    if cmd == "00":
        # Read Attribute received
        attribute = data[2:4] + data[0:2]
        if ClusterID == "0000" and attribute == "f000":
            # Respond to Time Of Operation
            cmd = "01"
            status = "00"
            cluster_frame = "1c"
            dataType = "23"  # Uint32
            PluginTimeOfOperation = "%08X" % (self.HeartbeatCount * HEARTBEAT)  # Time since the plugin started
            payload = (
                cluster_frame
                + sqn
                + cmd
                + attribute
                + status
                + dataType
                + PluginTimeOfOperation[6:8]
                + PluginTimeOfOperation[4:6]
                + PluginTimeOfOperation[0:2]
                + PluginTimeOfOperation[2:4]
            )
            raw_APS_request(
                self,
                nwkid,
                ep,
                ClusterID,
                "0104",
                payload,
                zigate_ep=ZIGATE_EP,
                ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
                highpriority=True,
            )
            self.log.logging(
                "Legrand",
                "Log",
                "loggingLegrand - Nwkid: %s/%s Cluster: %s, Command: %s Payload: %s"
                % (nwkid, ep, ClusterID, cmd, data),
            )
        return

    if cmd == "08":
        # Assign GroupId to a single remote
        manufspec = "2110"  # Legrand Manuf Specific : 0x1021
        cluster_frame = "1d"  # Cliuster Specifi, Manuf Specifi
        payload = cluster_frame + manufspec + sqn + cmd + data
        raw_APS_request(
            self,
            nwkid,
            ep,
            ClusterID,
            "0104",
            payload,
            zigate_ep=ZIGATE_EP,
            ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
            highpriority=True,
        )
        self.log.logging(
            "Legrand",
            "Log",
            "loggingLegrand - Nwkid: %s/%s Cluster: %s, Command: %s Payload: %s" % (nwkid, ep, ClusterID, cmd, data),
        )
        return

    if cmd == "0c":
        # Assign GroupId to a double remote
        manufspec = "2110"  # Legrand Manuf Specific : 0x1021
        cluster_frame = "1d"  # Cliuster Specifi, Manuf Specifi
        payload = cluster_frame + manufspec + sqn + cmd + data
        raw_APS_request(
            self,
            nwkid,
            ep,
            ClusterID,
            "0104",
            payload,
            zigate_ep=ZIGATE_EP,
            ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
            highpriority=True,
        )
        self.log.logging(
            "Legrand",
            "Log",
            "loggingLegrand - Nwkid: %s/%s Cluster: %s, Command: %s Payload: %s" % (nwkid, ep, ClusterID, cmd, data),
        )
        return


def rejoin_legrand_reset(self):

    # Check if we have any Legrand devices if so send teh Reset to the Air
    for x in self.ListOfDevices:
        if "Manufacturer" in self.ListOfDevices[x] and self.ListOfDevices[x]["Manufacturer"] == "1021":
            break
        if "Manufacturer Name" in self.ListOfDevices[x] and self.ListOfDevices[x]["Manufacturer Name"] == "Legrand":
            break
    else:
        # No Legrand devices found
        return

    # Send a Write Attributes no responses
    Domoticz.Status("Detected Legrand IEEE, broadcast Write Attribute 0x0000/0xf000")
    write_attributeNoResponse(self, "ffff", ZIGATE_EP, "01", "0000", "1021", "01", "f000", "23", "00000000")


def legrand_fc01(self, nwkid, command, OnOff):

    # EnableLedInDark -> enable to detect the device in dark
    # EnableDimmer -> enable/disable dimmer
    # EnableLedIfOn -> enable Led with device On

    self.log.logging("Legrand", "Debug", "legrand_fc01 Nwkid: %s Cmd: %s OnOff: %s " % (nwkid, command, OnOff), nwkid)

    LEGRAND_REFRESH_TIME = (3 * 3600) + 15
    LEGRAND_COMMAND_NAME = ("LegrandFilPilote", "EnableLedInDark", "EnableDimmer", "EnableLedIfOn", "EnableLedShutter")

    if nwkid not in self.ListOfDevices:
        return

    if command not in LEGRAND_COMMAND_NAME:
        Domoticz.Error("Unknown Legrand command %s" % command)
        return
    if "Model" not in self.ListOfDevices[nwkid]:
        return

    if self.ListOfDevices[nwkid]["Model"] in ( {} , "" ):
        return
    if self.ListOfDevices[nwkid]["Model"] not in LEGRAND_CLUSTER_FC01:
        self.log.logging(
            "Legrand",
            "Error",
            "%s is not an Legrand known model: %s" % (nwkid, self.ListOfDevices[nwkid]["Model"]),
            nwkid,
        )
        return
    if "Legrand" not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]["Legrand"] = {}
    for cmd in LEGRAND_COMMAND_NAME:
        if cmd not in self.ListOfDevices[nwkid]["Legrand"]:
            self.ListOfDevices[nwkid]["Legrand"][cmd] = 0xFF

    if command == "EnableLedInDark" and command in LEGRAND_CLUSTER_FC01[self.ListOfDevices[nwkid]["Model"]]:
        if (
            self.FirmwareVersion
            and self.FirmwareVersion.lower() <= "031c"
            and time() < self.ListOfDevices[nwkid]["Legrand"]["EnableLedInDark"] + LEGRAND_REFRESH_TIME
        ):
            return
        if self.FirmwareVersion and self.FirmwareVersion.lower() <= "031c":
            self.ListOfDevices[nwkid]["Legrand"]["EnableLedInDark"] = int(time())
        data_type = "10"  # Bool
        Hdata = "%02x" % OnOff
        self.log.logging(
            "Legrand",
            "Debug",
            "--------> %s  Nwkid: %s  data_type: %s Hdata: %s " % (command, nwkid, data_type, Hdata),
            nwkid,
        )

    elif command == "EnableLedShutter" and command in LEGRAND_CLUSTER_FC01[self.ListOfDevices[nwkid]["Model"]]:
        if (
            self.FirmwareVersion
            and self.FirmwareVersion.lower() <= "031c"
            and time() < self.ListOfDevices[nwkid]["Legrand"]["EnableLedShutter"] + LEGRAND_REFRESH_TIME
        ):
            return
        if self.FirmwareVersion and self.FirmwareVersion.lower() <= "031c":
            self.ListOfDevices[nwkid]["Legrand"]["EnableLedShutter"] = int(time())
        data_type = "10"  # Bool
        Hdata = "%02x" % OnOff
        self.log.logging(
            "Legrand",
            "Debug",
            "--------> %s  Nwkid: %s  data_type: %s Hdata: %s " % (command, nwkid, data_type, Hdata),
            nwkid,
        )

    elif command == "EnableDimmer" and command in LEGRAND_CLUSTER_FC01[self.ListOfDevices[nwkid]["Model"]]:
        if (
            self.FirmwareVersion
            and self.FirmwareVersion.lower() <= "031c"
            and time() < self.ListOfDevices[nwkid]["Legrand"]["EnableDimmer"] + LEGRAND_REFRESH_TIME
        ):
            return
        if self.FirmwareVersion and self.FirmwareVersion.lower() <= "031c":
            self.ListOfDevices[nwkid]["Legrand"]["EnableDimmer"] = int(time())
        data_type = "09"  # 16-bit Data
        if OnOff == 1:
            Hdata = "0101"  # Enable Dimmer
        elif OnOff == 0:
            Hdata = "0100"  # Disable Dimmer
        else:
            Hdata = "0000"
        self.log.logging(
            "Legrand",
            "Debug",
            "--------> %s  Nwkid: %s  data_type: %s Hdata: %s " % (command, nwkid, data_type, Hdata),
            nwkid,
        )

    elif command == "EnableLedIfOn" and command in LEGRAND_CLUSTER_FC01[self.ListOfDevices[nwkid]["Model"]]:
        if (
            self.FirmwareVersion
            and self.FirmwareVersion.lower() <= "031c"
            and time() < self.ListOfDevices[nwkid]["Legrand"]["EnableLedIfOn"] + LEGRAND_REFRESH_TIME
        ):
            return
        if self.FirmwareVersion and self.FirmwareVersion.lower() <= "031c":
            self.ListOfDevices[nwkid]["Legrand"]["EnableLedIfOn"] = int(time())
        data_type = "10"  # Bool
        Hdata = "%02x" % OnOff
        self.log.logging(
            "Legrand",
            "Debug",
            "--------> %s  Nwkid: %s  data_type: %s Hdata: %s " % (command, nwkid, data_type, Hdata),
            nwkid,
        )
    else:
        return

    Hattribute = LEGRAND_CLUSTER_FC01[self.ListOfDevices[nwkid]["Model"]][command]
    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" % 0xFC01

    EPout = "01"
    for tmpEp in self.ListOfDevices[nwkid]["Ep"]:
        if "fc01" in self.ListOfDevices[nwkid]["Ep"][tmpEp]:
            EPout = tmpEp

    self.log.logging(
        "Legrand",
        "Debug",
        "legrand %s OnOff - for %s with value %s / cluster: %s, attribute: %s type: %s"
        % (command, nwkid, Hdata, cluster_id, Hattribute, data_type),
        nwkid=nwkid,
    )
    write_attribute(
        self,
        nwkid,
        "01",
        EPout,
        cluster_id,
        manuf_id,
        manuf_spec,
        Hattribute,
        data_type,
        Hdata,
        ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
    )
    ReadAttributeRequest_fc01(self, nwkid)


def cable_connected_mode(self, nwkid, Mode):

    data_type = "09"  # 16-bit Data
    Hattribute = "0000"
    Hdata = "0000"

    if Mode == "10":
        # Sortie de Cable: 0x0100
        # Radiateur sans FIP: 0x0100
        # Appareil de cuisine: 0x0100
        Hdata = "0100"  # Disable FIP

    elif Mode == "20":
        # FIP
        # Radiateur avec FIP: 0x0200 + Bind fc40 + configReporting ( fc40 / 0000 / TimeOut 600 )
        Hdata = "0200"  # Enable FIP

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" % 0xFC01

    EPout = "01"
    for tmpEp in self.ListOfDevices[nwkid]["Ep"]:
        if "fc01" in self.ListOfDevices[nwkid]["Ep"][tmpEp]:
            EPout = tmpEp

    write_attribute(
        self,
        nwkid,
        "01",
        EPout,
        cluster_id,
        manuf_id,
        manuf_spec,
        Hattribute,
        data_type,
        Hdata[2:4] + Hdata[0:2],
        ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
    )
    ReadAttributeRequest_0006_0000(self, nwkid)
    ReadAttributeRequest_0b04_050b(self, nwkid)
    ReadAttributeRequest_fc40(self, nwkid)


def legrand_fc40(self, nwkid, Mode):
    # With the permission of @Thorgal789 who did the all reverse enginnering of this cluster

    CABLE_OUTLET_MODE = {
        "Confort": 0x00,
        "Confort -1": 0x01,
        "Confort -2": 0x02,
        "Eco": 0x03,
        "Frost Protection": 0x04,
        "Off": 0x05,
    }

    if Mode not in CABLE_OUTLET_MODE:
        Domoticz.Error(" Bad Mode : %s for %s" % (Mode, nwkid))
        return

    Hattribute = "0000"
    data_type = "30"  # 8bit Enum
    Hdata = CABLE_OUTLET_MODE[Mode]
    # manuf_id = "1021"  # Legrand Code
    # manuf_spec = "01"  # Manuf specific flag
    cluster_id = "%04x" % 0xFC40

    EPout = "01"
    for tmpEp in self.ListOfDevices[nwkid]["Ep"]:
        if "fc40" in self.ListOfDevices[nwkid]["Ep"][tmpEp]:
            EPout = tmpEp

    self.log.logging(
        "Legrand",
        "Debug",
        "legrand %s Set Fil pilote mode - for %s with value %s / cluster: %s, attribute: %s type: %s"
        % (Mode, nwkid, Hdata, cluster_id, Hattribute, data_type),
        nwkid=nwkid,
    )

    sqn = get_and_inc_ZCL_SQN(self, nwkid)

    fcf = "15"
    # manufspec = "01"
    manufcode = "1021"
    cmd = "00"
    data = "%02x" % CABLE_OUTLET_MODE[Mode]
    payload = fcf + manufcode[2:4] + manufcode[0:2] + sqn + cmd + data
    raw_APS_request(
        self,
        nwkid,
        EPout,
        "fc40",
        "0104",
        payload,
        zigate_ep=ZIGATE_EP,
        ackIsDisabled=is_ack_tobe_disabled(self, nwkid),
    )


def legrand_Dimmer_by_nwkid(self, NwkId, OnOff):
    self.log.logging("Legrand", "Debug", "legrand_Dimmer_by_nwkid - NwkId: %s OnOff: %s" % (NwkId, OnOff), NwkId)

    if "Manufacturer Name" not in self.ListOfDevices[NwkId]:
        return
    if self.ListOfDevices[NwkId]["Manufacturer Name"] != "Legrand":
        return
    if "Model" not in self.ListOfDevices[NwkId]:
        return
    if self.ListOfDevices[NwkId]["Model"] not in ("Dimmer switch wo neutral",):
        return
    if "Legrand" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Legrand"] = {}

    if int(self.FirmwareVersion, 16) >= 0x31D:
        if (
            "EnableDimmer" in self.ListOfDevices[NwkId]["Legrand"]
            and self.ListOfDevices[NwkId]["Legrand"]["EnableDimmer"] == OnOff
        ):
            self.log.logging("Legrand", "Debug", "legrand_Dimmer_by_nwkid - %s nothing to do" % NwkId, NwkId)
            return
        legrand_fc01(self, NwkId, "EnableDimmer", OnOff)
        del self.ListOfDevices[NwkId]["Legrand"]["EnableDimmer"]
        if OnOff:
            legrand_dimmer_enable(self, NwkId)
        else:
            legrand_dimmer_disable(self, NwkId)

    else:
        if "Legrand" in self.ListOfDevices[NwkId]:
            self.ListOfDevices[NwkId]["Legrand"]["EnableDimmer"] = 0
        legrand_fc01(self, NwkId, "EnableDimmer", OnOff)


def legrand_enable_Led_IfOn_by_nwkid(self, NwkId, OnOff):

    self.log.logging(
        "Legrand", "Debug", "legrand_enable_Led_IfOn_by_nwkid - NwkId: %s OnOff: %s" % (NwkId, OnOff), NwkId
    )

    if "Manufacturer Name" not in self.ListOfDevices[NwkId]:
        return
    if self.ListOfDevices[NwkId]["Manufacturer Name"] != "Legrand":
        return
    if "Model" not in self.ListOfDevices[NwkId]:
        return

    if "Legrand" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Legrand"] = {}

    if self.ListOfDevices[NwkId]["Model"] not in (
        "Connected outlet",
        "Mobile outlet",
        "Dimmer switch wo neutral",
        "Shutter switch with neutral",
        "Micromodule switch",
    ):
        return

    if int(self.FirmwareVersion, 16) >= 0x31D:
        if (
            "EnableLedIfOn" in self.ListOfDevices[NwkId]["Legrand"]
            and self.ListOfDevices[NwkId]["Legrand"]["EnableLedIfOn"] == OnOff
        ):
            self.log.logging("Legrand", "Debug", "legrand_enable_Led_IfOn_by_nwkid - %s nothing to do" % NwkId, NwkId)
            return
        legrand_fc01(self, NwkId, "EnableLedIfOn", OnOff)
        del self.ListOfDevices[NwkId]["Legrand"]["EnableLedIfOn"]

    else:
        if "Legrand" in self.ListOfDevices[NwkId]:
            self.ListOfDevices[NwkId]["Legrand"]["EnableLedIfOn"] = 0
        legrand_fc01(self, NwkId, "EnableLedIfOn", OnOff)


def legrand_enable_Led_Shutter_by_nwkid(self, NwkId, OnOff):

    self.log.logging(
        "Legrand", "Debug", "legrand_enable_Led_Shutter_by_nwkid - NwkId: %s OnOff: %s" % (NwkId, OnOff), NwkId
    )
    if "Manufacturer Name" not in self.ListOfDevices[NwkId]:
        return
    if self.ListOfDevices[NwkId]["Manufacturer Name"] != "Legrand":
        return
    if "Model" not in self.ListOfDevices[NwkId]:
        return

    if "Legrand" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Legrand"] = {}

    if self.ListOfDevices[NwkId]["Model"] not in ("Shutter switch with neutral"):
        return

    if int(self.FirmwareVersion, 16) >= 0x31D:
        if (
            "EnableLedShutter" in self.ListOfDevices[NwkId]["Legrand"]
            and self.ListOfDevices[NwkId]["Legrand"]["EnableLedShutter"] == OnOff
        ):
            self.log.logging(
                "Legrand", "Debug", "legrand_enable_Led_Shutter_by_nwkid - %s nothing to do" % NwkId, NwkId
            )
            return
        legrand_fc01(self, NwkId, "EnableLedShutter", OnOff)
        del self.ListOfDevices[NwkId]["Legrand"]["EnableLedShutter"]

    else:
        if "Legrand" in self.ListOfDevices[NwkId]:
            self.ListOfDevices[NwkId]["Legrand"]["EnableLedShutter"] = 0
        legrand_fc01(self, NwkId, "EnableLedShutter", OnOff)


def legrand_enable_Led_InDark_by_nwkid(self, NwkId, OnOff):

    self.log.logging(
        "Legrand", "Debug", "legrand_enable_Led_InDark_by_nwkid - NwkId: %s OnOff: %s" % (NwkId, OnOff), NwkId
    )
    if "Manufacturer Name" not in self.ListOfDevices[NwkId]:
        return
    if self.ListOfDevices[NwkId]["Manufacturer Name"] != "Legrand":
        return
    if "Model" not in self.ListOfDevices[NwkId]:
        return
    if "Legrand" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Legrand"] = {}

    if self.ListOfDevices[NwkId]["Model"] not in (
        "Connected outlet",
        "Mobile outlet",
        "Dimmer switch wo neutral",
        "Shutter switch with neutral",
        "Micromodule switch",
    ):
        return

    if int(self.FirmwareVersion, 16) >= 0x31D:
        if (
            "EnableLedInDark" in self.ListOfDevices[NwkId]["Legrand"]
            and self.ListOfDevices[NwkId]["Legrand"]["EnableLedInDark"] == OnOff
        ):
            self.log.logging("Legrand", "Debug", "legrand_enable_Led_InDark_by_nwkid - %s nothing to do" % NwkId, NwkId)
            return
        legrand_fc01(self, NwkId, "EnableLedInDark", OnOff)
        del self.ListOfDevices[NwkId]["Legrand"]["EnableLedInDark"]

    else:
        if "Legrand" in self.ListOfDevices[NwkId]:
            self.ListOfDevices[NwkId]["Legrand"]["EnableLedInDark"] = 0
        legrand_fc01(self, NwkId, "EnableLedInDark", OnOff)


def legrandReenforcement(self, NWKID):

    if "Health" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Health"] == "Not Reachable":
        return False

    if "Manufacturer Name" not in self.ListOfDevices[NWKID]:
        return False

    if self.ListOfDevices[NWKID]["Manufacturer Name"] != "Legrand":
        return False

    if "Legrand" not in self.ListOfDevices[NWKID]:
        self.ListOfDevices[NWKID]["Legrand"] = {
            'EnableDimmer': 255,
            'EnableLedIfOn': 255,
            'EnableLedShutter': 255,
            'EnableLedInDark': 255,
            'LegrandFilPilote': 255,
        }

    if "Model" not in self.ListOfDevices[NWKID]:
        return False

    model = self.ListOfDevices[NWKID]["Model"]
    if model not in LEGRAND_CLUSTER_FC01:
        return False

    for cmd in LEGRAND_CLUSTER_FC01[model]:
        if cmd == "None":
            continue

        if self.busy or self.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE:
            return True

        if cmd not in self.ListOfDevices[NWKID]["Legrand"]:
            self.ListOfDevices[NWKID]["Legrand"][cmd] = 0xFF

        if self.pluginconf.pluginConf[cmd] != self.ListOfDevices[NWKID]["Legrand"][cmd]:
            if self.pluginconf.pluginConf[cmd]:
                legrand_fc01(self, NWKID, cmd, "On")
            else:
                legrand_fc01(self, NWKID, cmd, "Off")

    return False


def legrand_refresh_battery_remote(self, nwkid):

    if "Model" not in self.ListOfDevices[nwkid]:
        return
    if self.ListOfDevices[nwkid]["Model"] not in LEGRAND_REMOTES:
        return
    if (
        "BatteryUpdateTime" in self.ListOfDevices[nwkid]
        and self.ListOfDevices[nwkid]["BatteryUpdateTime"] + 3600 > time()
    ):
        return
    ReadAttributeRequest_0001(self, nwkid, force_disable_ack=True)


def store_netatmo_attribute(self, NwkId, Attribute, Value):
    if "Legrand" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Legrand"] = {}
    self.ListOfDevices[NwkId]["Legrand"][Attribute] = Value


def legrand_dimmer_enable(self, NwkId):

    self.log.logging("Legrand", "Log", "legrand_dimmer_enable - %s " % NwkId, NwkId)

    # Bind
    if "IEEE" not in self.ListOfDevices[NwkId]:
        return
    ieee = self.ListOfDevices[NwkId]["IEEE"]
    if ieee not in self.IEEE2NWK:
        return
    bindDevice(self, ieee, "01", "0008", destaddr=None, destep="01")

    attribute_reporting_record = {
        "Attribute": "0000",
        "DataType": "20",
        "minInter": "0001",
        "maxInter": "0258",
        "timeOut": "0000",
    }

    self.configureReporting.send_configure_reporting_attributes_set(
        NwkId, ZIGATE_EP, "01", "0008", "00", "00", "0000", [ attribute_reporting_record,] )
    
    # 0x0008 / 0x00011 Change 0x01 Min: 0x00, Max 600
    attribute_reporting_record = {
        "Attribute": "0000",
        "DataType": "20",
        "minInter": "0000",
        "maxInter": "0258",
        "timeOut": "0000",
    }

    #self.configureReporting.send_configure_reporting_attributes_set(
    #    NwkId, ZIGATE_EP, "01", "0008", "00", "00", "0000", 1, "0020/0011/0000/0258/0000/01", [0x0011])
    self.configureReporting.send_configure_reporting_attributes_set(
        NwkId, ZIGATE_EP, "01", "0008", "00", "00", "0000", [attribute_reporting_record,])

    # Read Attribute 0x0008 / 0x0000 , 0x0011
    read_attribute(self, NwkId, ZIGATE_EP, "01", "0008", "00", "00", "0000", 1, "0000", ackIsDisabled=True)
    read_attribute(self, NwkId, ZIGATE_EP, "01", "0008", "00", "00", "0000", 1, "0011", ackIsDisabled=True)
    
    # Read Attribute 0x0006 / 0x0000
    read_attribute(self, NwkId, ZIGATE_EP, "01", "0006", "00", "00", "0000", 1, "0000", ackIsDisabled=True)


def legrand_dimmer_disable(self, NwkId):

    self.log.logging("Legrand", "Log", "legrand_dimmer_disable - %s " % NwkId, NwkId)
    # Unbind
    unbindDevice(self, self.ListOfDevices[NwkId]["IEEE"], "01", "0008")


def legrand_remote_switch_8095(self, Devices, MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_ ):
    if MsgCmd == "01":  # On
        self.log.logging(
            "Input",
            "Debug",
            "Decode8095 - Legrand: %s/%s, Cmd: %s, Unknown: %s " % (MsgSrcAddr, MsgEP, MsgCmd, unknown_),
            MsgSrcAddr,
        )
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd)
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)

    elif MsgCmd == "00":  # Off
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd)
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId] = {}
        self.log.logging(
            "Input",
            "Debug",
            "Decode8095 - Legrand: %s/%s, Cmd: %s, Unknown: %s " % (MsgSrcAddr, MsgEP, MsgCmd, unknown_),
            MsgSrcAddr,
        )

    elif MsgCmd == "02":  # Toggle
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, "02")
        self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = "Cmd: %s, %s" % (MsgCmd, unknown_)

def legrand_remote_switch_8085(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, MsgData):

    TYPE_ACTIONS = {
        None: "",
        "01": "move",
        "02": "click",
        "03": "stop",
    }
    DIRECTION = {None: "", "00": "up", "01": "down"}

    step_mod, up_down, step_size, transition = extract_info_from_8085(MsgData)

    if TYPE_ACTIONS[step_mod] in ("click", "move"):
        selector = TYPE_ACTIONS[step_mod] + DIRECTION[up_down]
    elif TYPE_ACTIONS[step_mod] == "stop":
        selector = TYPE_ACTIONS[step_mod]
    else:
        Domoticz.Error("Decode8085 - Unknown state for %s step_mod: %s up_down: %s" % (MsgSrcAddr, step_mod, up_down))
        return

    self.log.logging("Input", "Debug", "Decode8085 - Legrand selector: %s" % selector, MsgSrcAddr)
    if selector:
        if "Param" in self.ListOfDevices[MsgSrcAddr] and "netatmoReleaseButton" in self.ListOfDevices[MsgSrcAddr]["Param"] and self.ListOfDevices[MsgSrcAddr]["Param"]["netatmoReleaseButton"]:
            # self.log.logging( "Input", 'Log',"Receive: %s/%s %s" %(MsgSrcAddr,MsgEP,selector))
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, selector)
            self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = selector
        elif TYPE_ACTIONS[step_mod] != "stop":
            # self.log.logging( "Input", 'Log',"Receive: %s/%s %s REQUEST UPDATE" %(MsgSrcAddr,MsgEP,selector))
            MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, MsgClusterId, selector)
            self.ListOfDevices[MsgSrcAddr]["Ep"][MsgEP][MsgClusterId]["0000"] = selector


def legrand_motion_8095(self, Devices, MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_ ):
    self.log.logging(
        "Input",
        "Log",
        "Decode8095 - Legrand: %s/%s, Cmd: %s, Unknown: %s " % (MsgSrcAddr, MsgEP, MsgCmd, unknown_),
        MsgSrcAddr,
    )
    MajDomoDevice(self, Devices, MsgSrcAddr, MsgEP, "0406", unknown_)


def legrand_motion_8085(self, Devices, MsgSrcAddr,MsgEP, MsgClusterId, MsgCmd, unknown_, MsgData):
    step_mod, up_down, step_size, transition = extract_info_from_8085(MsgData)
    self.log.logging(
        "Input",
        "Log",
        "Decode8085 - Addr: %s, Ep: %s, Cluster: %s, Cmd: %s, Unknown: %s step_mode: %s up_down: %s step_size: %s transition: %s"
        % (MsgSrcAddr, MsgEP, MsgClusterId, MsgCmd, unknown_, step_mod, up_down, step_size, transition),
        MsgSrcAddr,
    )
