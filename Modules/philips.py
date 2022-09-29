#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
import struct

import Domoticz

import Modules.paramDevice
from Modules.basicOutputs import (raw_APS_request, set_poweron_afteroffon,
                                  write_attribute)
from Modules.domoMaj import MajDomoDevice
from Modules.readAttributes import (ReadAttributeRequest_0006_0000,
                                    ReadAttributeRequest_0006_400x,
                                    ReadAttributeRequest_0008_0000,
                                    ReadAttributeRequest_0406_philips_0030)
from Modules.tools import (checkAndStoreAttributeValue, is_hex,
                           retreive_cmd_payload_from_8002)
from Modules.zigateConsts import ZIGATE_EP

PHILIPS_POWERON_MODE = {0x00: "Off", 0x01: "On", 0xFF: "Previous state"}  # Off  # On  # Previous state


def pollingPhilips(self, key):
    """
    This fonction is call if enabled to perform any Manufacturer specific polling action
    The frequency is defined in the pollingSchneider parameter (in number of seconds)
    """

    # if  ( self.busy or self.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE):
    #    return True

    ReadAttributeRequest_0006_0000(self, key)
    ReadAttributeRequest_0008_0000(self, key)

    return False


def callbackDeviceAwake_Philips(self, Devices, NwkId, EndPoint, cluster):
    """
    This is fonction is call when receiving a message from a Manufacturer battery based device.
    The function is called after processing the readCluster part
    """

    Domoticz.Log("callbackDeviceAwake_Legrand - Nwkid: %s, EndPoint: %s cluster: %s" % (NwkId, EndPoint, cluster))


def default_response_for_philips_hue_reporting_attribute(self, Nwkid, srcEp, cluster, sqn):

    fcf = "10"
    cmd = "0b"
    cmd_reporting_attribute = "0a"
    status = "00"
    payload = fcf + sqn + cmd + cmd_reporting_attribute + "00"
    raw_APS_request(self, Nwkid, srcEp, cluster, "0104", payload, zigate_ep=ZIGATE_EP, ackIsDisabled=False)
    self.log.logging("Philips", "Log", "default_response_for_philips_hue_reporting_attribute - %s/%s " % (Nwkid, srcEp))


def philipsReadRawAPS(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload):

    # Zigbee Command:
    # 0x00: Read Attributes
    # 0x01: Read Attributes Response
    # 0x02: Write Attributes
    # 0x03:
    # 0x04: Write Attributes Response
    # 0x06: Configure Reporting
    # 0x0A: Report Attributes
    # 0x0C: Discover Attributes
    # 0x0D: Discover Attributes Response

    if srcNWKID not in self.ListOfDevices:
        return

    self.log.logging(
        "Philips",
        "Debug",
        "philipsReadRawAPS - Nwkid: %s Ep: %s, Cluster: %s, dstNwkid: %s, dstEp: %s, Payload: %s"
        % (srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload),
        srcNWKID,
    )

    # Motion
    # Nwkid: 329c/02 Cluster: 0001, Command: 07 Payload: 00
    # Nwkid: 329c/02 Cluster: 0001, Command: 0a Payload: 21002050

    if "Model" not in self.ListOfDevices[srcNWKID]:
        return

    _ModelName = self.ListOfDevices[srcNWKID]["Model"]

    default_response, GlobalCommand, sqn, ManufacturerCode, cmd, data = retreive_cmd_payload_from_8002(MsgPayload)

    if self.zigbee_communication == "native" and _ModelName == "RWL021" and cmd == "00" and ClusterID == "fc00":
        # This is handle by the firmware
        return
    elif self.zigbee_communication == "zigpy" and _ModelName == "RWL021" and cmd == "00" and ClusterID == "fc00":
        zigpy_philips_dimmer_switch(self, Devices, srcNWKID, srcEp, ClusterID, dstNWKID, dstEP, MsgPayload)
    self.log.logging(
        "Philips",
        "Debug",
        "philipsReadRawAPS - Nwkid: %s/%s Cluster: %s, GlobalCommand: %s sqn: %s, Command: %s Payload: %s"
        % (srcNWKID, srcEp, ClusterID, GlobalCommand, sqn, cmd, data),
    )


def philips_set_pir_occupancySensibility(self, nwkid, level):

    if level in (0, 1, 2):
        write_attribute(
            self, nwkid, ZIGATE_EP, "02", "0406", "100b", "01", "0030", "20", "%02x" % level, ackIsDisabled=False)
        ReadAttributeRequest_0406_philips_0030(self, nwkid)

def philips_led_indication(self, nwkid, onoff):

    if onoff in (0, 1):
        write_attribute(
            self, nwkid, ZIGATE_EP, "02", "0000", "100b", "01", "0033", "20", "%02x" % onoff, ackIsDisabled=False)
        ReadAttributeRequest_0406_philips_0030(self, nwkid)


def philips_set_poweron_after_offon(self, mode):
    # call from WebServer

    if mode not in PHILIPS_POWERON_MODE:
        Domoticz.Error("philips_set_poweron_after_offon - Unknown mode: %s" % mode)

    for nwkid in self.ListOfDevices:
        philips_set_poweron_after_offon_device(self, mode, nwkid)


def philips_set_poweron_after_offon_device(self, mode, nwkid):

    if "Manufacturer" not in self.ListOfDevices[nwkid]:
        return
    if self.ListOfDevices[nwkid]["Manufacturer"] != "100b":
        return
    # We have a Philips device
    if "0b" not in self.ListOfDevices[nwkid]["Ep"]:
        return
    if "0006" not in self.ListOfDevices[nwkid]["Ep"]["0b"]:
        return
    if "4003" not in self.ListOfDevices[nwkid]["Ep"]["0b"]["0006"]:
        Domoticz.Log("philips_set_poweron_after_offon Device: %s do not have a Set Power Attribute !" % nwkid)
        ReadAttributeRequest_0006_400x(self, nwkid)
        return

    # At that stage, we have a Philips device with Cluster 0006 and the right attribute
    self.log.logging(
        "Philips",
        "Debug",
        "philips_set_poweron_after_offon - Set PowerOn after OffOn of %s to %s" % (nwkid, PHILIPS_POWERON_MODE[mode]),
    )
    set_poweron_afteroffon(self, nwkid, OnOffMode=mode)
    ReadAttributeRequest_0006_400x(self, nwkid)

def zigpy_philips_dimmer_switch(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, dstNWKID, dstEP, MsgPayload):
    #        1d/0b10/2400/0300/00/30|01|21|1800 (long press)
    #                                      xxxx -> duration
    #                                xx-> Action
    #                     xxxx -> Attribute Id
    #           xxxx -> Manuf code
   
    MsgAttrID = "%04x" %struct.unpack("H", struct.pack(">H", int( MsgPayload[10:14], 16)))[0] 
    MsgClusterData = MsgPayload[14+2:]
    philips_dimmer_switch(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData)

def philips_dimmer_switch(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, MsgClusterData):

    self.log.logging( "Philips", "Debug", "philips_dimmer_switch %s - %s/%s - MsgAttrID = %s MsgClusterData: %s" % ( 
        MsgSrcAddr, MsgSrcEp, MsgClusterId,MsgAttrID, MsgClusterData ))

    self.log.logging( "Philips", "Debug", "philips_dimmer_switch %s - %s/%s - reading self.ListOfDevices[%s]['Ep'][%s][%s][%s] = %s" % ( 
        MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID, self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId], ), MsgSrcAddr, )

    rwl021_dimmer_step = Modules.paramDevice.get_device_config_param(self, MsgSrcAddr, "RWL021_Dimmer_step")
    if rwl021_dimmer_step is None:
        rwl021_dimmer_step = 1
        
    self.log.logging( "Philips", "Debug", "philips_dimmer_switch %s/%s - dimming step: %s" %( MsgSrcAddr, MsgSrcEp, rwl021_dimmer_step))

    prev_Value = _retreive_current_position( self, MsgSrcAddr, MsgSrcEp, MsgClusterId)

    prev_onoffvalue = onoffValue = int(prev_Value[0], 16)
    prev_lvlValue = lvlValue = int(prev_Value[1], 16)
    prev_duration = duration = int(prev_Value[2], 16)

    self.log.logging( "Philips", "Debug", "philips_dimmer_switch - %s - %s/%s - past OnOff: %s, Lvl: %s" % (MsgClusterId, MsgSrcAddr, MsgSrcEp, onoffValue, lvlValue), MsgSrcAddr, )

    if MsgAttrID == "0001":  # On button
        self.log.logging( "Philips", "Debug", "philips_dimmer_switch - %s - %s/%s - ON Button detected" % (MsgClusterId, MsgSrcAddr, MsgSrcEp), MsgSrcAddr, )
        return _update_domoticz_widget( self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, prev_onoffvalue, 1, prev_lvlValue, lvlValue, duration )

    elif MsgAttrID == "0004":  # Off  Button
        self.log.logging( "Philips", "Debug", "philips_dimmer_switch - %s - %s/%s - OFF Button detected" % (
            MsgClusterId, MsgSrcAddr, MsgSrcEp), MsgSrcAddr, )
        onoffValue = 0
        return _update_domoticz_widget( self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, prev_onoffvalue, 0, prev_lvlValue, lvlValue, duration )
    
    elif MsgAttrID in ("0002", "0003"):  # Dim+ / 0002 is +, 0003 is -
        self.log.logging( "Philips", "Debug", "philips_dimmer_switch - %s - %s/%s - DIM Button detected" % (
            MsgClusterId, MsgSrcAddr, MsgSrcEp), MsgSrcAddr, )
        action = MsgClusterData[2:4]
        duration = struct.unpack("H", struct.pack(">H", int( MsgClusterData[6:10], 16)))[0]

        if action in ("00", ):  # Short press
            self.log.logging( "Philips", "Debug", "philips_dimmer_switch - %s - %s/%s - DIM Action: %s" % (
                MsgClusterId, MsgSrcAddr, MsgSrcEp, action), MsgSrcAddr, )
            onoffValue = 1
            # Short press/Release - Make one step   , we just report the press
            if MsgAttrID == "0002":
                lvlValue += rwl021_dimmer_step
            elif MsgAttrID == "0003":
                lvlValue -= rwl021_dimmer_step

        elif action in ("01",):  # Long press
            delta = duration - prev_duration  # Time press since last message
            onoffValue = 1
            if MsgAttrID == "0002":
                lvlValue += round(delta * rwl021_dimmer_step)
            elif MsgAttrID == "0003":
                lvlValue -= round(delta * rwl021_dimmer_step)

        elif action in ("03", "02"):  # Release after Long/short Press
            self.log.logging( "Philips", "Debug", "philips_dimmer_switch - %s - %s/%s - DIM Release after %s seconds" % (
                MsgClusterId, MsgSrcAddr, MsgSrcEp, round(duration / 10)), MsgSrcAddr, )

        else:
            self.log.logging( "Philips", "Debug", "philips_dimmer_switch - %s - %s/%s - DIM Action: %s not processed" % (
                MsgClusterId, MsgSrcAddr, MsgSrcEp, action), MsgSrcAddr, )
            return  # No need to update

        # Check if we reach the limits Min and Max
        lvlValue = min(lvlValue, 255)
        lvlValue = max(lvlValue, 0)
        self.log.logging( "Philips", "Debug", "philips_dimmer_switch - %s - %s/%s - Level: %s " % (
            MsgClusterId, MsgSrcAddr, MsgSrcEp, lvlValue), MsgSrcAddr, )
        return _update_domoticz_widget( self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, prev_onoffvalue, onoffValue, prev_lvlValue, lvlValue, duration )
        
    else:
        self.log.logging( "Philips", "Debug", "philips_dimmer_switch - %s - %s/%s unknown attribute: %s %s" % (
            MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgAttrID, MsgClusterData), MsgSrcAddr, )
    


def _update_domoticz_widget( self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, prev_onoffvalue, onoffValue, prev_lvlValue, lvlValue, duration ):
    # Update Domo
    sonoffValue = "%02x" % onoffValue
    slvlValue = "%02x" % lvlValue
    sduration = "%02x" % duration

    checkAndStoreAttributeValue(self, MsgSrcAddr, MsgSrcEp, MsgClusterId, "0000", "%s;%s;%s" % (sonoffValue, slvlValue, sduration))
    self.log.logging( "Philips", "Debug", "philips_dimmer_switch %s - %s/%s - updating self.ListOfDevices[%s]['Ep'][%s][%s] = %s" % ( 
        MsgClusterId, MsgSrcAddr, MsgSrcEp, MsgSrcAddr, MsgSrcEp, MsgClusterId, self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId], ),MsgSrcAddr,)

    if prev_onoffvalue != onoffValue:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, "0006", sonoffValue)
    if prev_lvlValue != lvlValue:
        MajDomoDevice(self, Devices, MsgSrcAddr, MsgSrcEp, MsgClusterId, slvlValue)

    
def _retreive_current_position( self, MsgSrcAddr, MsgSrcEp, MsgClusterId):
    if "0000" not in self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId]:
        return "0;80;0".split(";")
    prev_Value = str(self.ListOfDevices[MsgSrcAddr]["Ep"][MsgSrcEp][MsgClusterId]["0000"]).split(";")
    if len(prev_Value) != 3:
        return "0;80;0".split(";")  
    for val in prev_Value:
        if not is_hex(val):
            prev_Value = "0;80;0".split(";")
            break
    return prev_Value
