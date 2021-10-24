#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import Domoticz
import struct

from Modules.tools import retreive_cmd_payload_from_8002
from Modules.pollControl import receive_poll_cluster

from Modules.domoMaj import MajDomoDevice

from Modules.schneider_wiser import schneiderReadRawAPS
from Modules.legrand_netatmo import legrandReadRawAPS
from Modules.livolo import livoloReadRawAPS
from Modules.orvibo import orviboReadRawAPS
from Modules.lumi import lumiReadRawAPS
from Modules.philips import philipsReadRawAPS
from Modules.tuya import tuyaReadRawAPS, TUYA_MANUFACTURER_NAME

from Modules.casaia import CASAIA_MANUF_CODE, casaiaReadRawAPS


## Requires Zigate firmware > 3.1d
CALLBACK_TABLE = {
    # Manuf : ( callbackDeviceAwake_xxxxx function )
    "105e": schneiderReadRawAPS,
    "1021": legrandReadRawAPS,
    "115f": lumiReadRawAPS,
    "100b": philipsReadRawAPS,
    "1002": tuyaReadRawAPS,
    CASAIA_MANUF_CODE: casaiaReadRawAPS,
}

CALLBACK_TABLE2 = {
    # Manufacturer Name
    "LIVOLO": livoloReadRawAPS,
    "欧瑞博": orviboReadRawAPS,
    "Legrand": legrandReadRawAPS,
    "Schneider": schneiderReadRawAPS,
    "Schneider Electric": schneiderReadRawAPS,
    "LUMI": lumiReadRawAPS,
    "Philips": philipsReadRawAPS,
    "OWON": casaiaReadRawAPS,
    "CASAIA": casaiaReadRawAPS,
}


def inRawAps(
    self,
    Devices,
    srcnwkid,
    srcep,
    cluster,
    dstnwkid,
    dstep,
    Sqn,
    GlobalCommand,
    ManufacturerCode,
    Command,
    Data,
    payload,
):

    """
    This function is called by Decode8002
    """

    if srcnwkid not in self.ListOfDevices:
        return

    self.log.logging(
        "inRawAPS",
        "Debug",
        "inRawAps Nwkid: %s Ep: %s Cluster: %s ManufCode: %s Cmd: %s Data: %s"
        % (srcnwkid, srcep, cluster, ManufacturerCode, Command, Data),
    )
    if cluster == "0020":  # Poll Control ( Not implemented in firmware )
        # Domoticz.Log("Cluster 0020 -- POLL CLUSTER")
        receive_poll_cluster(self, srcnwkid, srcep, cluster, dstnwkid, dstep, Sqn, ManufacturerCode, Command, Data)
        return

    if cluster == "0019":  # OTA Cluster
        # Domoticz.Log("Cluster 0019 -- OTA CLUSTER")

        if Command == "01":
            # Query Next Image Request
            Domoticz.Log("Cluster 0019 -- OTA CLUSTER Command 01")
            # fieldcontrol = Data[0:2]
            manufcode = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[2:6], 16)))[0]
            imagetype = "%04x" % struct.unpack("H", struct.pack(">H", int(Data[6:10], 16)))[0]
            currentVersion = "%08x" % struct.unpack("I", struct.pack(">I", int(Data[10:18], 16)))[0]
            Domoticz.Log(
                "Cluster 0019 -- OTA CLUSTER Command 01Device %s Request OTA with current ManufCode: %s ImageType: %s Version: %s"
                % (srcnwkid, manufcode, imagetype, currentVersion)
            )

            if "OTA" not in self.ListOfDevices[srcnwkid]:
                self.ListOfDevices[srcnwkid]["OTA"] = {}
            self.ListOfDevices[srcnwkid]["OTA"]["ManufacturerCode"] = manufcode
            self.ListOfDevices[srcnwkid]["OTA"]["ImageType"] = imagetype
            self.ListOfDevices[srcnwkid]["OTA"]["CurrentImageVersion"] = currentVersion
        return

    if cluster == "0500":  # IAS Cluster
        # "00":
        # "01" # inRawAps 56ba/23 Cluster 0500 Manuf: None Command: 01 Data: 0d001510 Payload: 1922010d001510
        # 0x00  Zone Enroll Response
        # 0x01  Initiate Normal Operation Mode
        # 0x02  Initiate Test Mode

        enroll_response_code = Data[0:2]
        zone_id = Data[2:4]

        if Command == "00":
            pass

        elif Command == "01":
            pass

        elif Command == "02":
            pass

        return

    if cluster == "0501":  # IAS ACE
        # "00"
        # "01" Arm Day (Home Zones Only) - Command Arm 0x00 - Payload 0x01
        # "02" Emergency - Command Emergency 0x02
        # "03" Arm All Zones - Command Arm 0x00 - Payload Arm all Zone 0x03
        # "04" Disarm - Command 0x00 - Payload Disarm 0x00

        if Command == "00" and Data[0:2] == "00":
            # Disarm
            MajDomoDevice(self, Devices, srcnwkid, srcep, "0006", "04")

        elif Command == "00" and Data[0:2] == "01":
            # Command Arm Day (Home Zones Only)
            MajDomoDevice(self, Devices, srcnwkid, srcep, "0006", "01")

        elif Command == "00" and Data[0:2] == "03":
            # Arm All Zones
            MajDomoDevice(self, Devices, srcnwkid, srcep, "0006", "03")

        elif Command == "02":
            # Emergency
            MajDomoDevice(self, Devices, srcnwkid, srcep, "0006", "02")

        return

    if cluster == "0300":  # Color Control
        if Command == "0a":  # Move to Color Temperature
            color_temp_mired = payload[8:10] + payload[6:8]
            transition_time = payload[12:14] + payload[10:12]
            # Domoticz.Log("Move to Color Temp - Command: %s Temp_Mired: %s TransitionTime: %s" %(Command, color_temp_mired, transition_time))
            if "Model" in self.ListOfDevices[srcnwkid] and self.ListOfDevices[srcnwkid]["Model"] == "tint-Remote-white":
                COLOR_SCENE_WHITE = {
                    "022b": "09",
                    "01dc": "10",
                    "01a1": "11",
                    "0172": "12",
                    "00fa": "13",
                    "00c8": "14",
                    "0099": "15",
                }
                if color_temp_mired in COLOR_SCENE_WHITE:
                    MajDomoDevice(self, Devices, srcnwkid, srcep, "0008", COLOR_SCENE_WHITE[color_temp_mired])

        elif Command == "4b":  # Move Color Temperature
            move_mode = payload[6:8]
            rate = payload[10:12] + payload[8:10]
            color_temp_min_mireds = payload[14:16] + payload[12:14]
            color_temp_max_mireds = payload[18:20] + payload[16:18]
            # Domoticz.Log("Move Color Temperature - Command: %s mode: %s rate: %s min_mired: %s max_mired: %s" %(
            #    Command, move_mode, rate, color_temp_min_mireds, color_temp_max_mireds))
            if "Model" in self.ListOfDevices[srcnwkid] and self.ListOfDevices[srcnwkid]["Model"] == "tint-Remote-white":
                if move_mode == "01":  # Down
                    MajDomoDevice(self, Devices, srcnwkid, srcep, "0008", "16")

                elif move_mode == "03":  # Up
                    MajDomoDevice(self, Devices, srcnwkid, srcep, "0008", "17")

        elif Command == "47":  # Stop Move Step
            # Domoticz.Log("Stop Move Step - Command: %s" %Command)
            if "Model" in self.ListOfDevices[srcnwkid] and self.ListOfDevices[srcnwkid]["Model"] == "tint-Remote-white":
                MajDomoDevice(self, Devices, srcnwkid, srcep, "0008", "18")

        else:
            Domoticz.Log("Unknown Color Control Command: %s" % Command)

        return

    if "Manufacturer" not in self.ListOfDevices[srcnwkid]:
        return

    manuf = manuf_name = ""
    if "Manufacturer Name" in self.ListOfDevices[srcnwkid]:
        manuf_name = self.ListOfDevices[srcnwkid]["Manufacturer Name"]

    manuf = str(self.ListOfDevices[srcnwkid]["Manufacturer"])

    self.log.logging(
        "inRawAPS",
        "Debug",
        "inRawAps Nwkid: %s Ep: %s Cluster: %s ManufCode: %s manuf: %s manuf_name: %s Cmd: %s Data: %s"
        % (srcnwkid, srcep, cluster, ManufacturerCode, manuf, manuf_name, Command, Data),
    )

    func = None
    if manuf in CALLBACK_TABLE:
        # self.log.logging( "inRawAPS", 'Debug',"Found in CALLBACK_TABLE")
        func = CALLBACK_TABLE[manuf]
        # func( self, Devices, srcnwkid, srcep, cluster, dstnwkid, dstep, payload)
    elif manuf_name in CALLBACK_TABLE2:
        # self.log.logging( "inRawAPS", 'Debug',"Found in CALLBACK_TABLE2")
        func = CALLBACK_TABLE2[manuf_name]
        # func( self, Devices, srcnwkid, srcep, cluster, dstnwkid, dstep, payload)
    elif manuf_name in TUYA_MANUFACTURER_NAME:
        func = tuyaReadRawAPS
    else:
        Domoticz.Log(
            "inRawAps %s/%s Cluster %s Manuf: %s/%s Command: %s Data: %s Payload: %s not processed !!!"
            % (srcnwkid, srcep, cluster, manuf, manuf_name, Command, Data, payload)
        )

    if func:
        func(self, Devices, srcnwkid, srcep, cluster, dstnwkid, dstep, payload)
