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
    Module: heartbeat.py

    Description: Manage all actions done during the onHeartbeat() call

"""

import datetime
import time

from DevicesModules.custom_Chameleon import erl_z3_master_info
from Modules.basicOutputs import getListofAttribute
from Modules.casaia import pollingCasaia
from Modules.danfoss import danfoss_room_sensor_polling
from Modules.domoticzAbstractLayer import (find_widget_unit_from_WidgetID,
                                           is_device_ieee_in_domoticz_db)
from Modules.domoTools import (retrieve_widget_type_list,
                               reset_device_ieee_unit_if_needed,
                               timedOutDevice)
from Modules.linky import collect_ticmeter_linky
from Modules.pairingProcess import (binding_needed_clusters_with_coordinator,
                                    processNotinDBDevices)
from Modules.paramDevice import sanity_check_of_param
from Modules.pluginDbAttributes import STORE_CONFIGURE_REPORTING
from Modules.readAttributes import (READ_ATTRIBUTES_REQUEST, ReadAttributeReq,
                                    ReadAttributeReq_Scheduled_linky_mode,
                                    ReadAttributeReq_Scheduled_ZLinky,
                                    ReadAttributeReq_ZLinky,
                                    ReadAttributeRequest_0b04_050b_0505_0508,
                                    ReadAttributeRequest_0001,
                                    ReadAttributeRequest_0006_0000,
                                    ReadAttributeRequest_0008_0000,
                                    ReadAttributeRequest_0101_0000,
                                    ReadAttributeRequest_0102_0008,
                                    ReadAttributeRequest_0201_0012,
                                    ReadAttributeRequest_0402,
                                    ReadAttributeRequest_0405,
                                    ReadAttributeRequest_0702_0000,
                                    ReadAttributeRequest_0702_0017,
                                    ReadAttributeRequest_0702_PC321,
                                    ReadAttributeRequest_0702_ZLinky_TIC,
                                    ReadAttributeRequest_ff66,
                                    ping_device_with_read_attribute,
                                    ping_devices_via_group, ping_tuya_device,
                                    read_attributes_gammatroniques_tic_meter,
                                    read_attributes_ticmeter_details,
                                    read_attributes_ticmeter_tarif)
from Modules.schneider_wiser import schneiderRenforceent
from Modules.switchSelectorWidgets import SWITCH_SELECTORS
from Modules.tools import (ReArrangeMacCapaBasedOnModel, deviceconf_device,
                           get_device_nickname, get_deviceconf_parameter_value,
                           getAttributeValue, getListOfEpForCluster, is_hex,
                           is_time_to_perform_work, mainPoweredDevice,
                           night_shift_jobs, drop_stale_nwkid)
from Modules.tuya import tuya_polling
from Modules.tuyaTRV import tuya_switch_online
from Modules.zb_tables_management import mgmt_rtg, mgtm_binding
from Modules.zigateConsts import HEARTBEAT, MAX_LOAD_ZIGATE
from Zigbee.zdpCommands import (zdp_node_descriptor_request,
                                zdp_NWK_address_request)

# Read Attribute trigger: Every 10"
# Configure Reporting trigger: Every 15
# Network Topology start: 15' after plugin start
# Network Energy start: 30' after plugin start
# Legrand re-enforcement: Every 5'


QUIET_AFTER_START = (60 // HEARTBEAT)  # Quiet periode after a plugin start
NETWORK_TOPO_START = (900 // HEARTBEAT)
NETWORK_ENRG_START = (1800 // HEARTBEAT)
READATTRIBUTE_FEQ = (10 // HEARTBEAT)  # 10seconds ...
CONFIGURERPRT_FEQ = (( 30 // HEARTBEAT) + 1)
LEGRAND_FEATURES = (( 300 // HEARTBEAT ) + 3)
SCHNEIDER_FEATURES = (( 300 // HEARTBEAT) + 5)
BINDING_TABLE_REFRESH = (( 3600 // HEARTBEAT ) + 11)
NODE_DESCRIPTOR_REFRESH = (( 3600 // HEARTBEAT) + 13)
ATTRIBUTE_DISCOVERY_REFRESH = (( 3600 // HEARTBEAT ) + 7)
CHECKING_DELAY_READATTRIBUTE = (( 60 // HEARTBEAT ) + 7)
PING_DEVICE_VIA_GROUPID = 3567 // HEARTBEAT    # Secondes ( 59minutes et 45 secondes )
FIRST_PING_VIA_GROUP = 127 // HEARTBEAT
CHECKING_TICMETER_KEY_ATTRIBUTES = (30 // HEARTBEAT)  # 30 Sec
CHECKING_ERLZ3_KEY_ATTRIBUTES = ( 300 // HEARTBEAT )  # 5 Min

def attributeDiscovery(self, NwkId):
    # If Attributes not yet discovered, let's do it
    if not self.ListOfDevices[NwkId].get("ConfigSource") or \
       self.ListOfDevices[NwkId]["ConfigSource"] == "DeviceConf" or \
       (self.ListOfDevices[NwkId].get("Attributes List") and len(self.ListOfDevices[NwkId]["Attributes List"]) > 0):
        return False

    self.ListOfDevices[NwkId].setdefault("Attributes List", {'Ep': {}})
    self.ListOfDevices[NwkId]["Attributes List"].setdefault("Request", {})

    for iterEp in self.ListOfDevices[NwkId]["Ep"]:
        if iterEp == "ClusterType":
            continue
        self.ListOfDevices[NwkId]["Attributes List"]["Request"].setdefault(iterEp, {})

        for iterCluster in self.ListOfDevices[NwkId]["Ep"][iterEp]:
            if iterCluster in ("Type", "ClusterType", "ColorMode"):
                continue
            if self.ListOfDevices[NwkId]["Attributes List"]["Request"][iterEp].get(iterCluster) != 0:
                continue

            if not self.busy and self.ControllerLink.loadTransmit() <= MAX_LOAD_ZIGATE:
                if int(iterCluster, 16) < 0x0FFF:
                    getListofAttribute(self, NwkId, iterEp, iterCluster)
                elif len(self.ListOfDevices[NwkId].get("Manufacturer", "")) == 4 and is_hex(self.ListOfDevices[NwkId].get("Manufacturer", "")):
                    getListofAttribute(self, NwkId, iterEp, iterCluster, manuf_specific="01", manuf_code=self.ListOfDevices[NwkId]["Manufacturer"])
                self.ListOfDevices[NwkId]["Attributes List"]["Request"][iterEp][iterCluster] = time.time()
            else:
                return True

    return False


def device_handle_custom_polling_if_defined(self, NwkId, HB):
    """
    Poll a device based on a custom polling structure.

    Expected structure in device parameters:

        'CustomPolling':
            {
                'EPin": '01',                     # Input endpoint
                'EPout': '01',                    # Output endpoint
                'Frequency': 60,                  # Frequency in seconds
                'ManufCode': '1234',              # Optional manufacturer code (hex string)
                'ClusterAttributesList': {        # Cluster-to-attributes map
                    '0702': ['0000', '0100', '0102', '0104', '0106', '0108', '010a', '0400'],
                    '0b01': ['000a', '000c', '000d', '000e'],
                    '0b04': ['0508', '0505']
                }
            }

    Note:
        - Frequency will be divided by HEARTBEAT value to determine polling interval.
        - If the current heartbeat modulo frequency is not zero, polling is skipped.
        - ManufCode is optional; if present, manufacturer-specific polling will be applied.
        - by default we take EPin and EPout as 01
        - if frequency or ClusterAttributesList is not defined, polling is skipped.
        - if frequency is 0, polling is disabled.

    Implemented for:
        - Chameleon TIC
    """

    self.log.logging([ "Heartbeat", "CustomDevicePolling"] , "Debug", f"++ device_handle_custom_polling_if_defined - {NwkId}", NwkId)

    # Check if device is busy or if the load is too high
    if self.busy or self.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE:
        return True

    device_info = self.ListOfDevices.get(NwkId, {})
    last_poll = device_info.get("LastCustomPolling")
    model_name = device_info.get("Model")

    # Get polling config from device parameters or fallback to device conf
    custom_polling = (
        device_info.get("Param", {}).get("CustomPolling")
        or self.DeviceConf.get(model_name, {}).get("CustomPolling")
    )

    if custom_polling is None:
        return False

    self.log.logging([ "Heartbeat", "CustomDevicePolling"], "Debug", f"++ device_handle_custom_polling_if_defined - {NwkId} {last_poll} {HB}", NwkId)
    if last_poll == HB:
        # This prevent multiple polling in the same cycle
        return False

    self.log.logging([ "Heartbeat", "CustomDevicePolling"], "Debug", f"++ device_handle_custom_polling_if_defined - {NwkId} {custom_polling}", NwkId)

    frequency = custom_polling.get("Frequency")
    if not frequency:
        return False
    freq_heartbeat = int(frequency) // HEARTBEAT
    if freq_heartbeat == 0 or (HB % freq_heartbeat) != 0:
        return False

    cluster_map = custom_polling.get("ClusterAttributesList")
    if not cluster_map:
        return False

    self.ListOfDevices[NwkId]["LastCustomPolling"] = HB
    
    self.log.logging([ "Heartbeat", "CustomDevicePolling"], "Debug", f"++ device_handle_custom_polling_if_defined - {NwkId} Ready to poll Frequency: {freq_heartbeat} / {HB}", NwkId)

    manuf_code = custom_polling.get("ManufCode", "0000")
    manuf_specif = "01" if manuf_code != "0000" else "00"

    ep_in = custom_polling.get("EPin", "01")
    ep_out = custom_polling.get("EPout", "01")


    for cluster, attributes in cluster_map.items():
        attr_ids = [int(attr, 16) for attr in attributes]
        self.log.logging(
            [ "Heartbeat", "CustomDevicePolling"],
            "Debug",
            f"++ device_handle_custom_polling_if_defined - {NwkId} trigger ReadAttributeRequest Cluster: {cluster} Attributes: {attributes} Manuf: {manuf_specif}/{manuf_code}",
            NwkId,
        )
        ReadAttributeReq(self, NwkId, ep_in, ep_out, cluster, attr_ids, manufacturer_spec=manuf_specif, manufacturer=manuf_code)

    return False


def ManufSpecOnOffPolling(self, NwkId):
    ReadAttributeRequest_0006_0000(self, NwkId)
    ReadAttributeRequest_0008_0000(self, NwkId)


def tuya_trv5_polling(self, NwkId):
    tuya_switch_online(self, NwkId, 0x01)


def check_delay_readattributes( self, NwkId ):
    
    if 'DelayReadAttributes' not in self.ListOfDevices[ NwkId ]:
        return
    
    if time.time() < self.ListOfDevices[ NwkId ]['DelayReadAttributes']['TargetTime']:
        return
    
    for cluster in list(self.ListOfDevices[ NwkId ]['DelayReadAttributes']['Clusters']):
        if self.busy or self.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE:
            return
        func = READ_ATTRIBUTES_REQUEST[cluster][0]
        func(self, NwkId)
        self.ListOfDevices[ NwkId ]['DelayReadAttributes']['Clusters'].remove( cluster )
        
    if len(self.ListOfDevices[ NwkId ]['DelayReadAttributes']['Clusters']) == 0:
        del self.ListOfDevices[ NwkId ]['DelayReadAttributes']


def check_delay_binding( self, NwkId, model ):
    # Profalux is the first one, but could get others
    # At pairing we need to leave time for the remote to get binded to the VR
    # Once it is done, then we can overwrite the binding

    if "DelayBindingAtPairing" in self.ListOfDevices[ NwkId ] and self.ListOfDevices[ NwkId ]["DelayBindingAtPairing"] == "Completed":
        self.log.logging( "Heartbeat", "Debug", "check_delay_binding -  %s DelayBindingAtPairing: %s" % (
            NwkId, self.ListOfDevices[ NwkId ]["DelayBindingAtPairing"]), NwkId, )
        return
    
    if model in ( "", {}):
        self.log.logging( "Heartbeat", "Debug", "check_delay_binding -  %s model: %s" % (
            NwkId, model), NwkId, )
        return

    if model not in self.DeviceConf or "DelayBindingAtPairing" not in self.DeviceConf[ model ] or self.DeviceConf[ model ]["DelayBindingAtPairing"] == 0:
        self.log.logging( "Heartbeat", "Debug", "check_delay_binding -  %s not applicable" % (
            NwkId), NwkId, )
        return
    
    if "ClusterToBind" not in self.DeviceConf[ model ] or len(self.DeviceConf[ model ]["ClusterToBind"]) == 0:
        self.log.logging( "Heartbeat", "Debug", "check_delay_binding -  %s Empty ClusterToBind" % (
            NwkId), NwkId, )
        return
    
    # We have a good candidate
    # We reached that step, because we have DelayindingAtPairing enabled and the BindTable is not empty.
    # Let's bind
    if self.configureReporting:
        if "Bind" in self.ListOfDevices[ NwkId ]:
            del self.ListOfDevices[ NwkId ]["Bind"]
            self.ListOfDevices[ NwkId ]["Bind"] = {}
        if STORE_CONFIGURE_REPORTING in self.ListOfDevices[ NwkId ]:
            del self.ListOfDevices[ NwkId ][STORE_CONFIGURE_REPORTING]
            self.ListOfDevices[ NwkId ]["Bind"] = {} 
        self.log.logging( "Heartbeat", "Debug", "check_delay_binding -  %s request Configure Reporting (and so bindings)" % (
            NwkId), NwkId, )
        binding_needed_clusters_with_coordinator(self, NwkId)
        self.configureReporting.processConfigureReporting( NwkId=NwkId ) 
        self.ListOfDevices[ NwkId ]["DelayBindingAtPairing"] = "Completed"


def pollingManufSpecificDevices(self, NwkId, HB):

    FUNC_MANUF = {
        "TuyaTRV5Polling": tuya_trv5_polling,
        "OnOffPollingFreq": ManufSpecOnOffPolling,
        "PowerPollingFreq": ReadAttributeRequest_0b04_050b_0505_0508,
        "MeterPollingFreq": ReadAttributeRequest_0702_0000,
        "PC321PollingFreq": ReadAttributeRequest_0702_PC321,
        "AC201Polling": pollingCasaia,
        "TuyaPing": ping_tuya_device,
        "BatteryPollingFreq": ReadAttributeRequest_0001,
        "DanfossRoomFreq": danfoss_room_sensor_polling,
        "TempPollingFreq": ReadAttributeRequest_0402,
        "HumiPollingFreq": ReadAttributeRequest_0405,
        "BattPollingFreq": ReadAttributeRequest_0001,
        "ZLinkyPollingLinkyMode": ReadAttributeReq_Scheduled_linky_mode,  # Linky Mode
        "ZLinkyPollingPTEC": ReadAttributeReq_Scheduled_ZLinky,     # Color of day and next day
        "ZLinkyPolling0702": ReadAttributeRequest_0702_ZLinky_TIC,  # Metering
        "ZLinkyPollingGlobal": ReadAttributeReq_ZLinky,             # All ZLinky Clusters/Attributes
        "PollingCusterff66": ReadAttributeRequest_ff66,             # All Manufacturer Specific ZLinky attributes
        "InletTempPolling": ReadAttributeRequest_0702_0017,      # Retreive Inlet Temperature
        "TICMeter_Tarif_Polling": read_attributes_ticmeter_tarif,        # Retreive Tarif
        "TICMeter_tic_specific": read_attributes_ticmeter_details,       # Retreive TICMeter details
        "TICMeter_force_refresh": read_attributes_gammatroniques_tic_meter,       # Retreive TICMeter details
    }

    def _scheduled_zlinky_read(self, NwkId, parameter, device_parameters, heartbeat_counter):
        """Handles scheduled ZLinky read operations based on time or heartbeat intervals."""

        _current_time = datetime.datetime.now().strftime("%H:%M")
        _target_value = device_parameters.get(parameter)

        # Determine execution condition
        should_execute = False
        if isinstance( _target_value, str) and ":" in _target_value:
            should_execute = (_current_time == _target_value)

        elif isinstance( _target_value, (int, float)):
            _target_value = _target_value // HEARTBEAT
            if _target_value != 0:
                should_execute = (heartbeat_counter % _target_value) == 0

        self.log.logging(
            ["Heartbeat", "ZLinky"], "Debug",
            f"++ pollingManufSpecificDevices - {NwkId} {parameter}: Current: {_current_time} Target: {_target_value} should_execute {should_execute}",
            NwkId,
        )

        if should_execute:
            if "ScheduledZLinkyRead" in self.ListOfDevices[NwkId]:
                return
            if parameter == "ZLinkyPollingPTEC":
                self.log.logging("Heartbeat", "Status", "Z4D reads ZLinky Color of Day and Next Day")

            self.ListOfDevices[NwkId]["ScheduledZLinkyRead"] = True
            func = FUNC_MANUF[param]
            func(self, NwkId)

        elif "ScheduledZLinkyRead" in self.ListOfDevices[NwkId]:
            # Prevent multiple executions within the same time unit
            self.ListOfDevices[NwkId].pop("ScheduledZLinkyRead", None)

    device_parameters = self.ListOfDevices[NwkId].get("Param")
    if device_parameters is None:
        return False

    if self.busy or self.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE:
        return True

    last_polling = self.ListOfDevices[ NwkId ].get("LastPollingManufSpecificDevices")
    if last_polling and last_polling == HB:
        return False

    self.log.logging( "Heartbeat", "Debug", "++ pollingManufSpecificDevices -  %s " % (NwkId,), NwkId, )

    for param in device_parameters:
        if param in ("ZLinkyPollingPTEC", "ScheduledZLinkyRead", "ZLinkyPolling0702", "ZLinkyPollingGlobal", "PollingCusterff66"):
            _scheduled_zlinky_read(self, NwkId, param, device_parameters, HB)

        elif param in FUNC_MANUF:
            _FEQ = device_parameters[param] // HEARTBEAT
            if _FEQ == 0:  # Disable
                continue
            self.log.logging( "Heartbeat", "Debug", "++ pollingManufSpecificDevices -  %s Found: %s=%s HB: %s FEQ: %s Cycle: %s" % (
                NwkId, param, device_parameters[param], HB, _FEQ, (HB % _FEQ)), NwkId, )
            if _FEQ and ((HB % _FEQ) != 0):
                continue
            self.log.logging( "Heartbeat", "Debug", "++ pollingManufSpecificDevices -  %s Found: %s=%s" % (
                NwkId, param, device_parameters[param]), NwkId, )

            func = FUNC_MANUF[param]
            func(self, NwkId)

    return False


def pollingDeviceStatus(self, NwkId):
    # """
    # Purpose is to trigger ReadAttrbute 0x0006 and 0x0008 on attribute 0x0000 if applicable
    # """

    if self.busy or self.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE:
        return True
    
    self.log.logging("Heartbeat", "Debug", "--------> pollingDeviceStatus Device %s" % NwkId, NwkId)
    if len(getListOfEpForCluster(self, NwkId, "0006")) != 0:
        ReadAttributeRequest_0006_0000(self, NwkId)
        self.log.logging("Heartbeat", "Debug", "++ pollingDeviceStatus -  %s  for ON/OFF" % (NwkId), NwkId)

    if len(getListOfEpForCluster(self, NwkId, "0008")) != 0:
        ReadAttributeRequest_0008_0000(self, NwkId)
        self.log.logging("Heartbeat", "Debug", "++ pollingDeviceStatus -  %s  for LVLControl" % (NwkId), NwkId)

    if len(getListOfEpForCluster(self, NwkId, "0102")) != 0:
        ReadAttributeRequest_0102_0008(self, NwkId)
        self.log.logging("Heartbeat", "Debug", "++ pollingDeviceStatus -  %s  for WindowCovering" % (NwkId), NwkId)

    if len(getListOfEpForCluster(self, NwkId, "0101")) != 0:
        ReadAttributeRequest_0101_0000(self, NwkId)
        self.log.logging("Heartbeat", "Debug", "++ pollingDeviceStatus -  %s  for DoorLock" % (NwkId), NwkId)

    if len(getListOfEpForCluster(self, NwkId, "0201")) != 0:
        ReadAttributeRequest_0201_0012(self, NwkId)
        self.log.logging("Heartbeat", "Debug", "++ pollingDeviceStatus -  %s  for Thermostat" % (NwkId), NwkId)
    return False


def checkHealth(self, NwkId):

    # Checking current state of the this Nwk
    if "Health" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Health"] = ""
        
    if self.ListOfDevices[NwkId]["Health"] == "Disabled":
        return False
                 
    if "Stamp" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["Stamp"] = {'LastPing': 0, 'LastSeen': 0}
        self.ListOfDevices[NwkId]["Health"] = "unknown"

    if "LastSeen" not in self.ListOfDevices[NwkId]["Stamp"]:
        self.ListOfDevices[NwkId]["Stamp"]["LastSeen"] = 0
        self.ListOfDevices[NwkId]["Health"] = "unknown"

    if (
        int(time.time()) > (self.ListOfDevices[NwkId]["Stamp"]["LastSeen"] + 21200)
        and self.ListOfDevices[NwkId]["Health"] == "Live"
    ):
        if "ZDeviceName" in self.ListOfDevices[NwkId]:
            self.log.logging("Heartbeat", "Debug", "Device Health - %s NwkId: %s,Ieee: %s , Model: %s seems to be out of the network" % (
                self.ListOfDevices[NwkId]["ZDeviceName"], NwkId, self.ListOfDevices[NwkId]["IEEE"], self.ListOfDevices[NwkId]["Model"],))
        else:
            self.log.logging("Heartbeat", "Debug", "Device Health - NwkId: %s,Ieee: %s , Model: %s seems to be out of the network" % (
                NwkId, self.ListOfDevices[NwkId]["IEEE"], self.ListOfDevices[NwkId]["Model"]) )
        self.ListOfDevices[NwkId]["Health"] = "Not seen last 24hours"

    # If device flag as Not Reachable, don't do anything
    return ( "Health" not in self.ListOfDevices[NwkId] or self.ListOfDevices[NwkId]["Health"] != "Not Reachable")


def pingRetryDueToBadHealth(self, NwkId):

    now = int(time.time())
    # device is on Non Reachable state
    self.log.logging("Heartbeat", "Debug", "--------> ping Retry Check %s" % NwkId, NwkId)
    if "pingDeviceRetry" not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId]["pingDeviceRetry"] = {"Retry": 0, "TimeStamp": now}
    if self.ListOfDevices[NwkId]["pingDeviceRetry"]["Retry"] == 0:
        return

    if "Retry" in self.ListOfDevices[NwkId]["pingDeviceRetry"] and "TimeStamp" not in self.ListOfDevices[NwkId]["pingDeviceRetry"]:
        # This could be due to a previous version without TimeStamp
        self.ListOfDevices[NwkId]["pingDeviceRetry"]["Retry"] = 0
        self.ListOfDevices[NwkId]["pingDeviceRetry"]["TimeStamp"] = now

    lastTimeStamp = self.ListOfDevices[NwkId]["pingDeviceRetry"]["TimeStamp"]
    retry = self.ListOfDevices[NwkId]["pingDeviceRetry"]["Retry"]

    self.log.logging(
        "Heartbeat",
        "Debug",
        "--------> ping Retry Check %s Retry: %s Gap: %s" % (NwkId, retry, now - lastTimeStamp),
        NwkId,
    )
    # Retry #1
    if (
        retry == 0
        and self.ControllerLink.loadTransmit() == 0
        and now > (lastTimeStamp + 30)
    ):  # 30s
        self.log.logging("Heartbeat", "Debug", "--------> ping Retry 1 Check %s" % NwkId, NwkId)
        self.ListOfDevices[NwkId]["pingDeviceRetry"]["Retry"] += 1
        self.ListOfDevices[NwkId]["pingDeviceRetry"]["TimeStamp"] = now
        lookup_ieee = self.ListOfDevices[ NwkId ]['IEEE']
        zdp_NWK_address_request(self, "0000", lookup_ieee)
        submitPing(self, NwkId)
        return

    # Retry #2
    if (
        retry == 1
        and self.ControllerLink.loadTransmit() == 0
        and now > (lastTimeStamp + 120)
    ):  # 30 + 120s
        # Let's retry
        self.log.logging("Heartbeat", "Debug", "--------> ping Retry 2 Check %s" % NwkId, NwkId)
        self.ListOfDevices[NwkId]["pingDeviceRetry"]["Retry"] += 1
        self.ListOfDevices[NwkId]["pingDeviceRetry"]["TimeStamp"] = now
        lookup_ieee = self.ListOfDevices[ NwkId ]['IEEE']
        zdp_NWK_address_request(self, "fffd", lookup_ieee)
        submitPing(self, NwkId)
        return

    # Retry #3
    if (
        retry == 2
        and self.ControllerLink.loadTransmit() == 0
        and now > (lastTimeStamp + 300)
    ):  # 30 + 120 + 300
        # Let's retry
        self.log.logging("Heartbeat", "Debug", "--------> ping Retry 3 (last) Check %s" % NwkId, NwkId)
        self.ListOfDevices[NwkId]["pingDeviceRetry"]["Retry"] += 1
        self.ListOfDevices[NwkId]["pingDeviceRetry"]["TimeStamp"] = now
        lookup_ieee = self.ListOfDevices[ NwkId ]['IEEE']
        zdp_NWK_address_request(self, "FFFD", lookup_ieee)
        submitPing(self, NwkId)


def pingDevices(self, NwkId, health, checkHealthFlag, mainPowerFlag):

    if self.pluginconf.pluginConf["pingViaGroup"]:
        self.log.logging( "Heartbeat", "Debug", "No direct pinDevices as Group ping is enabled" , NwkId, )
        return
    
    if "pingDeviceRetry" in self.ListOfDevices[NwkId]:
        self.log.logging( "Heartbeat", "Debug", "------> pinDevices %s health: %s, checkHealth: %s, mainPower: %s, retry: %s" % (
            NwkId, health, checkHealthFlag, mainPowerFlag, self.ListOfDevices[NwkId]["pingDeviceRetry"]["Retry"]), NwkId, )
    else:
        self.log.logging( "Heartbeat", "Debug", "------> pinDevices %s health: %s, checkHealth: %s, mainPower: %s" % (
            NwkId, health, checkHealthFlag, mainPowerFlag), NwkId, )

    if not mainPowerFlag:
        return

    if (
        "Param" in self.ListOfDevices[NwkId]
        and "TuyaPing" in self.ListOfDevices[NwkId]["Param"]
        and int(self.ListOfDevices[NwkId]["Param"]["TuyaPing"]) == 1
    ):
        self.log.logging(
            "Heartbeat",
            "Debug",
            "------> pingDevice disabled for %s as TuyaPing enabled %s"
            % (
                NwkId,
                self.ListOfDevices[NwkId]["Param"]["TuyaPing"],
            ),
            NwkId,
        )
        return

    if (
        "Param" in self.ListOfDevices[NwkId]
        and "pingBlackListed" in self.ListOfDevices[NwkId]["Param"]
        and int(self.ListOfDevices[NwkId]["Param"]["pingBlackListed"]) == 1
    ):
        self.log.logging(
            "Heartbeat",
            "Debug",
            "------> pingDevice disabled for %s as pingBlackListed enabled %s"
            % (
                NwkId,
                self.ListOfDevices[NwkId]["Param"]["pingBlackListed"],
            ),
            NwkId,
        )
        return

    now = int(time.time())

    if (
        "time" in self.ListOfDevices[NwkId]["Stamp"]
        and now < self.ListOfDevices[NwkId]["Stamp"]["time"] + self.pluginconf.pluginConf["pingDevicesFeq"]
    ):
        # If we have received a message since less than 1 hours, then no ping to be done !
        self.log.logging("Heartbeat", "Debug", "------> %s no need to ping as we received a message recently " % (NwkId,), NwkId)
        return

    if not health:
        pingRetryDueToBadHealth(self, NwkId)
        return

    if "LastPing" not in self.ListOfDevices[NwkId]["Stamp"]:
        self.ListOfDevices[NwkId]["Stamp"]["LastPing"] = 0
    lastPing = self.ListOfDevices[NwkId]["Stamp"]["LastPing"]
    lastSeen = self.ListOfDevices[NwkId]["Stamp"]["LastSeen"]
    if checkHealthFlag and now > (lastPing + 60) and self.ControllerLink.loadTransmit() == 0:
        submitPing(self, NwkId)
        return

    self.log.logging( "Heartbeat", "Debug", "------> pinDevice %s time: %s LastPing: %s LastSeen: %s Freq: %s" % (
        NwkId, now, lastPing, lastSeen, self.pluginconf.pluginConf["pingDevicesFeq"]), NwkId, )
    if (
        (now > (lastPing + self.pluginconf.pluginConf["pingDevicesFeq"]))
        and (now > (lastSeen + self.pluginconf.pluginConf["pingDevicesFeq"]))
        and self.ControllerLink.loadTransmit() == 0
    ):

        self.log.logging( "Heartbeat", "Debug", "------> pinDevice %s time: %s LastPing: %s LastSeen: %s Freq: %s" % (
            NwkId, now, lastPing, lastSeen, self.pluginconf.pluginConf["pingDevicesFeq"]), NwkId, )

        submitPing(self, NwkId)


def submitPing(self, NwkId):
    # Pinging devices to check they are still Alive
    self.log.logging("Heartbeat", "Debug", "------------> call readAttributeRequest %s" % NwkId, NwkId)
    self.ListOfDevices[NwkId]["Stamp"]["LastPing"] = int(time.time())
    ping_device_with_read_attribute(self, NwkId)


def hr_process_device(self, Devices, NwkId):
    # Begin
    # Normalize Hearbeat value if needed

    device_hearbeat = int(self.ListOfDevices.get(NwkId, {}).get("Heartbeat", 0))
    self.ListOfDevices[NwkId]["Heartbeat"] = str(device_hearbeat - 0xFFF0) if device_hearbeat > 0xFFFF else str(device_hearbeat)

    # Hack bad devices
    ReArrangeMacCapaBasedOnModel(self, NwkId, self.ListOfDevices[NwkId]["MacCapa"])

    # Check if this is a Main powered device or Not. Source of information are: MacCapa and PowerSource
    _mainPowered = mainPoweredDevice(self, NwkId)
    _checkHealth = self.ListOfDevices[NwkId]["Health"] == ""
    health = checkHealth(self, NwkId)

    # Pinging devices to check they are still Alive
    if self.pluginconf.pluginConf["pingDevices"]:
        pingDevices(self, NwkId, health, _checkHealth, _mainPowered)

    # Check if we are in the process of provisioning a new device. If so, just stop
    if self.pairing_in_progress:
        return

    # If device flag as Not Reachable, don't do anything
    if not health:
        self.log.logging( "Heartbeat", "Debug", "hr_process_device -  %s stop here due to Health %s" % (NwkId, self.ListOfDevices[NwkId]["Health"]), NwkId, )
        return

    # If we reach this step, the device health is Live
    if "pingDeviceRetry" in self.ListOfDevices[NwkId]:
        self.log.logging("Heartbeat", "Log", f"Device {NwkId} '{get_device_nickname(self, NwkId=NwkId)}' recover from Non Reachable", NwkId)
        del self.ListOfDevices[NwkId]["pingDeviceRetry"]

    model = self.ListOfDevices[NwkId].get("Model", "") 
    enabledEndDevicePolling = get_deviceconf_parameter_value(self, model, "PollingEnabled", return_default=False)
    self.log.logging("Heartbeat", "Debug", f"Device {NwkId} Model {model} -> enabledEndDevicePolling {enabledEndDevicePolling}")

    check_param = self.ListOfDevices.get(NwkId, {}).get("CheckParam", False)
    if check_param and self.HeartbeatCount > QUIET_AFTER_START and self.ControllerLink.loadTransmit() < 5:
        sanity_check_of_param(self, NwkId)
        self.ListOfDevices[NwkId]["CheckParam"] = False

    if ( device_hearbeat % CHECKING_DELAY_READATTRIBUTE) == 0:
        check_delay_readattributes( self, NwkId )

    if ( 
        "DelayBindingAtPairing" in self.ListOfDevices[ NwkId ] 
        and isinstance(self.ListOfDevices[ NwkId ]["DelayBindingAtPairing"],int )
        and self.ListOfDevices[ NwkId ]["DelayBindingAtPairing"] > 0
        and time.time() > self.ListOfDevices[ NwkId ]["DelayBindingAtPairing"]
    ):   
        # Will check only after a Command has been sent, in order to limit.
        self.log.logging("Heartbeat", "Debug", "check_delay_binding inHB = %s" %device_hearbeat ) 
        check_delay_binding( self, NwkId, model )

    # Starting this point, it is ony relevant for Main Powered Devices.
    # Some battery based end device with ZigBee 30 use polling and can receive commands.
    # We should authporized them for Polling After Action, in order to get confirmation.
    
    if self.ListOfDevices[ NwkId ].get("Chameleon") and device_hearbeat % CHECKING_ERLZ3_KEY_ATTRIBUTES == 0:
        erl_z3_master_info(self, NwkId)
        
    if model == "TICMeter" and (device_hearbeat % CHECKING_TICMETER_KEY_ATTRIBUTES == 0):
        collect_ticmeter_linky(self, NwkId)

    if _mainPowered or enabledEndDevicePolling:
        process_main_powered_or_force_devices( self, NwkId, device_hearbeat, _mainPowered, enabledEndDevicePolling, model)


def process_main_powered_or_force_devices(self, NwkId, device_hearbeat, _mainPowered, enabledEndDevicePolling, model):
    self.log.logging("Heartbeat", "Debug",f"Calling process_main_powered_or_force_devices with arguments: NwkId={NwkId}, device_hearbeat={device_hearbeat}, _mainPowered={_mainPowered}, enabledEndDevicePolling={enabledEndDevicePolling}, model={model}", NwkId)

    rescheduleAction = False

    if self.pluginconf.pluginConf["forcePollingAfterAction"] and device_hearbeat == 1:
        self.log.logging("Heartbeat", "Debug", f"process_main_powered_or_force_devices - {NwkId} due to device_hearbeat {device_hearbeat}", NwkId)
        rescheduleAction = rescheduleAction or pollingDeviceStatus(self, NwkId)
        return

    rescheduleAction = ( rescheduleAction or tuya_polling(self, NwkId) )

    rescheduleAction = ( rescheduleAction or device_handle_custom_polling_if_defined(self, NwkId, device_hearbeat) )

    rescheduleAction = ( rescheduleAction or pollingManufSpecificDevices(self, NwkId, device_hearbeat) )

    _doReadAttribute = (
        (self.pluginconf.pluginConf["enableReadAttributes"] or self.pluginconf.pluginConf["resetReadAttributes"])
        and device_hearbeat != 0
        and (device_hearbeat % READATTRIBUTE_FEQ) == 0
    )

    if should_delay_read_attribute(self, NwkId):
        return

    if _doReadAttribute:
        self.log.logging("Heartbeat", "Debug", f"process_main_powered_or_force_devices - {NwkId} device_hearbeat: {device_hearbeat} _mainPowered: {_mainPowered} doReadAttr: {_doReadAttribute}", NwkId)
        rescheduleAction = rescheduleAction or process_read_attributes(self, NwkId, model)

    if should_reenforce_schneider(self, NwkId):
        rescheduleAction = rescheduleAction or schneiderRenforceent(self, NwkId)

    if self.pluginconf.pluginConf["checkConfigurationReporting"]:
        rescheduleAction = rescheduleAction or check_configuration_reporting(self, NwkId, _mainPowered, device_hearbeat)

    if should_discover_attributes(self, NwkId, _mainPowered, enabledEndDevicePolling, device_hearbeat):
        rescheduleAction = rescheduleAction or attributeDiscovery(self, NwkId)

    if should_refresh_binding_table(self, NwkId, _mainPowered, enabledEndDevicePolling, device_hearbeat):
        mgtm_binding(self, NwkId, "BindingTable")

    if should_request_node_descriptor(self, NwkId, _mainPowered, device_hearbeat):
        rescheduleAction = rescheduleAction or zdp_node_descriptor_request(self, NwkId)

    if not self.busy and self.ControllerLink.loadTransmit() <= MAX_LOAD_ZIGATE:
        add_device_group_for_ping(self, NwkId)

    if rescheduleAction and device_hearbeat != 0:
        decrement_heartbeat(self, NwkId)
    else:
        clear_last_polling_data(self, NwkId)


def should_delay_read_attribute(self, NwkId):
    if (
        self.ControllerLink.loadTransmit() > 5
        and "PairingTime" in self.ListOfDevices[NwkId]
        and time.time() <= (self.ListOfDevices[NwkId]["PairingTime"] + (self.ControllerLink.loadTransmit() // 5) + 15)
    ):
        self.log.logging("Heartbeat", "Debug", f"hr_process_device - {NwkId} delay the next ReadAttribute close to the pairing {self.ListOfDevices[NwkId]['PairingTime']}", NwkId)
        return True
    return False


def should_reenforce_schneider(self, NwkId):
    return self.pluginconf.pluginConf["reenforcementWiser"] and (self.HeartbeatCount % self.pluginconf.pluginConf["reenforcementWiser"]) == 0


def should_discover_attributes(self, NwkId, _mainPowered, enabledEndDevicePolling, device_hearbeat):
    return night_shift_jobs(self) and _mainPowered and not enabledEndDevicePolling and device_hearbeat != 0 and ((device_hearbeat % ATTRIBUTE_DISCOVERY_REFRESH) == 0)


def should_refresh_binding_table(self, NwkId, _mainPowered, enabledEndDevicePolling, device_hearbeat):
    return night_shift_jobs(self) and _mainPowered and not enabledEndDevicePolling and device_hearbeat != 0 and ((device_hearbeat % BINDING_TABLE_REFRESH) == 0)


def should_request_node_descriptor(self, NwkId, _mainPowered, device_hearbeat):
    required_keys = ["Manufacturer", "DeviceType", "LogicalType", "PowerSource", "ReceiveOnIdle", "_rawNodeDescriptor"]
    return (
        night_shift_jobs(self)
        and _mainPowered
        and device_hearbeat != 0
        and (device_hearbeat % NODE_DESCRIPTOR_REFRESH) == 0
        and any(
            key not in self.ListOfDevices.get(NwkId, {})
            for key in required_keys
        )
    )


def decrement_heartbeat(self, NwkId):
    self.ListOfDevices[NwkId]["Heartbeat"] = str(int(self.ListOfDevices[NwkId]["Heartbeat"]) - 1)


def clear_last_polling_data(self, NwkId):
    for key in ["LastPollingManufSpecificDevices", "LastCustomPolling"]:
        self.ListOfDevices[NwkId].pop(key, None)


def process_read_attributes(self, NwkId, model):
    self.log.logging("Heartbeat", "Debug", f"process_read_attributes - for {NwkId} {model}")
    now = int(time.time())
    device_infos = self.ListOfDevices.get(NwkId, {})

    for ep, clusters in device_infos.get("Ep", {}).items():
        if ep == "ClusterType":
            continue
        if model == "lumi.ctrl_neutral1" and ep != "02":
            continue
        if model == "lumi.ctrl_neutral2" and ep not in ("02", "03"):
            continue

        for Cluster in READ_ATTRIBUTES_REQUEST:
            if Cluster not in READ_ATTRIBUTES_REQUEST or Cluster not in clusters:
                continue

            if self.busy or self.ControllerLink.loadTransmit() > MAX_LOAD_ZIGATE:
                self.log.logging("Heartbeat", "Debug", f"process_read_attributes - {NwkId} skip ReadAttribute for now... system too busy ({self.busy}/{self.ControllerLink.loadTransmit()})", NwkId)
                return True

            timing = self.pluginconf.pluginConf.get(READ_ATTRIBUTES_REQUEST[Cluster][1])
            if not timing:
                self.log.logging("Heartbeat", "Error", f"process_read_attributes - missing timing attribute for Cluster: {Cluster} - {READ_ATTRIBUTES_REQUEST[Cluster][1]}", NwkId)
                continue

            if not is_time_to_perform_work(self, "ReadAttributes", NwkId, ep, Cluster, now, timing):
                continue

            self.log.logging("Heartbeat", "Debug", f"process_read_attributes - {NwkId}/{ep} and time to request ReadAttribute for {Cluster}", NwkId)
            READ_ATTRIBUTES_REQUEST[Cluster][0](self, NwkId)
            return True

    return False


def check_configuration_reporting(self, NwkId, _mainPowered, device_hearbeat):
    
    self.log.logging( "ConfigureReporting", "Debug", "check_configuration_reporting for %s %s %s %s %s >%s<" %(
        NwkId, _mainPowered, self.HeartbeatCount, device_hearbeat, self.pluginconf.pluginConf["checkConfigurationReporting"], self.zigbee_communication), NwkId)

    if self.configureReporting is None:
        # Cfg Reporting Object not yet ready
        return

    if self.HeartbeatCount < QUIET_AFTER_START:
        #  leave time at startup
        return

    if "Status" not in self.ListOfDevices[NwkId] or self.ListOfDevices[NwkId]["Status"] != "inDB":
        # Device is not a good state
        return False

    if device_hearbeat != 0 and (device_hearbeat % (60 // HEARTBEAT)) != 0:
        # check only every minute
        return

    if (
        "checkConfigurationReporting" not in self.pluginconf.pluginConf
        or self.pluginconf.pluginConf["checkConfigurationReporting"] == 0
    ):
        # Check if checkConfigurationReporting is enable
        return

    if deviceconf_device(self, NwkId) == {}:
        # Do only for plugin known devices
        return

    if not _mainPowered:
        # Process only with main powered devices
        return

    if not night_shift_jobs( self ):
        # In case we are in a night shift mode, then wait for the nigh window
        return

    if self.busy and self.ControllerLink.loadTransmit() > 3:
        # Only if the load is reasonable
        return True


    if self.zigbee_communication == "zigpy":
        self.log.logging( "ConfigureReporting", "Debug", "check_configuration_reporting for %s %s %s %s %s >%s<" %(
            NwkId, _mainPowered, self.HeartbeatCount, device_hearbeat, self.pluginconf.pluginConf["checkConfigurationReporting"], self.zigbee_communication), NwkId)

        if ( not self.configureReporting.check_configuration_reporting_for_device( NwkId, checking_period=self.pluginconf.pluginConf["checkConfigurationReporting"] )):
            # Nothing trigger, let's check if the configure reporting are correct
            self.configureReporting.check_and_redo_configure_reporting_if_needed( NwkId)

    elif self.zigbee_communication == "native":
        self.log.logging( "ConfigureReporting", "Debug", "Trying Configuration reporting for %s/%s !" %(
            NwkId, get_device_nickname( self, NwkId=NwkId)), NwkId)
        self.configureReporting.processConfigureReporting( NwkId, batch=True )
    return False


def processListOfDevices(self, Devices):
    # Let's check if we do not have a command in TimeOut

    # self.ControllerLink.checkTOwaitFor()
    entriesToBeRemoved = []

    for NwkId in list(self.ListOfDevices.keys()):
        if NwkId in ("ffff", "0000"):
            continue
        
        if NwkId not in self.ListOfDevices:
            continue

        # If this entry is empty, then let's remove it .
        if len(self.ListOfDevices[NwkId]) == 0:
            self.log.logging("Heartbeat", "Debug", "Bad devices detected (empty one), remove it, adr:" + str(NwkId), NwkId)
            entriesToBeRemoved.append(NwkId)
            continue

        device = self.ListOfDevices.get(NwkId, {})
        param = device.get("Param", {})
        health = device.get("Health", "")

        if "Disabled" in param:
            if param["Disabled"] and health == "Disabled":
                device["CheckParam"] = False
                continue
            
            if not param["Disabled"] and health == "Disabled":
                # Device was previously disabled and is now re-enabled; refresh it
                device["Health"] = ""
                device.pop("Stamp", None)
                device["RIA"] = "0"

        ria = device.get("RIA", "")
        if ria not in ( "", {}):
            RIA = int(ria)
        else:
            RIA = 0
            ria = "0"

        try:
            device["Heartbeat"] = str(int(device.get("Heartbeat", "0")) + 1)
        except ValueError:
            device["Heartbeat"] = "1"

        status = device.get("Status", {})
        if status == "failDB":
            entriesToBeRemoved.append(NwkId)
            continue

        # Known Devices
        if status == "inDB":
            hr_process_device(self, Devices, NwkId)

            # Check and reset if needed Motion, Vibrator and Switch Selector
            check_and_reset_device_if_needed(self, Devices, NwkId)

            # Timed out devices in Domoticz is needed
            timeout_hours = self.pluginconf.pluginConf.get("ForceDeviceTimedOut_afterXhours", 0)
            if timeout_hours:
                stamp = device.get("Stamp", {})
                last_seen = stamp.get("LastSeen", 0)

                if last_seen > 0 and (time.time() - last_seen) > (timeout_hours * 3600):
                    timedOutDevice(self, Devices, NwkId=NwkId)
                    self.log.logging(
                        "Heartbeat",
                        "Debug",
                        f"processListOfDevices - Device {NwkId} is timed out after {timeout_hours} hours",
                        NwkId
                    )

        elif status == "Leave":
            timedOutDevice(self, Devices, NwkId=NwkId)
            # Device has sentt a 0x8048 message annoucing its departure (Leave)
            # Most likely we should receive a 0x004d, where the device come back with a new short address
            # For now we will display a message in the log every 1'
            # We might have to remove this entry if the device get not reconnected.
            if ((int(self.ListOfDevices[NwkId]["Heartbeat"]) % 36) and int(self.ListOfDevices[NwkId]["Heartbeat"]) != 0) == 0:
                if "ZDeviceName" in self.ListOfDevices[NwkId]:
                    self.log.logging( "Heartbeat", "Debug", "processListOfDevices - Device: %s (%s) is in Status = 'Left' for %s HB" % (
                        self.ListOfDevices[NwkId]["ZDeviceName"], NwkId, self.ListOfDevices[NwkId]["Heartbeat"]), NwkId, )
                else:
                    self.log.logging( "Heartbeat", "Debug", "processListOfDevices - Device: (%s) is in Status = 'Left' for %s HB" % (
                        NwkId, self.ListOfDevices[NwkId]["Heartbeat"]), NwkId, )
                # Let's check if the device still exist in Domoticz
                if not is_device_ieee_in_domoticz_db(self, Devices, self.ListOfDevices[NwkId]["IEEE"]):
                    # Not devices found in Domoticz, so we are safe to remove it from Plugin
                    if self.ListOfDevices[NwkId]["IEEE"] in self.IEEE2NWK:
                        self.log.logging( "Heartbeat", "Status", "processListOfDevices - Removing %s / %s from IEEE2NWK." % (
                            self.ListOfDevices[NwkId]["IEEE"], NwkId) )
                        del self.IEEE2NWK[self.ListOfDevices[NwkId]["IEEE"]]
                    self.log.logging( "Heartbeat", "Status", "processListOfDevices - Removing the entry %s from ListOfDevice" % (NwkId))
                    drop_stale_nwkid(self, NwkId)

        elif status not in ("inDB", "UNKNOW", "erasePDM"):
            # Discovery process 0x004d -> 0x0042 -> 0x8042 -> 0w0045 -> 0x8045 -> 0x0043 -> 0x8043
            processNotinDBDevices(self, Devices, NwkId, status, RIA)

    should_ping_via_group = (
        self.groupmgt
        and self.pluginconf.pluginConf.get("pingViaGroup", False)  # Use .get() to avoid KeyErrors
        and (
            self.HeartbeatCount == FIRST_PING_VIA_GROUP  # First group ping after 2 minutes
            or self.HeartbeatCount % PING_DEVICE_VIA_GROUPID == 0  # Recurring group pings
        )
    )

    if should_ping_via_group:
        ping_devices_via_group(self)

    for iterDevToBeRemoved in entriesToBeRemoved:
        if "IEEE" in self.ListOfDevices[iterDevToBeRemoved]:
            del self.ListOfDevices[iterDevToBeRemoved]["IEEE"]
        del self.ListOfDevices[iterDevToBeRemoved]

    if self.pairing_in_progress or self.busy:
        self.log.logging( "Heartbeat", "Debug", "Skip LQI, ConfigureReporting and Networkscan du to Busy state: Busy: %s, Enroll: %s" % (
            self.busy, self.pairing_in_progress), )
        return  # We don't go further as we are Commissioning a new object and give the prioirty to it

    if self.pairing_in_progress and self.Ping['Permit'] is None and self.Ping['TimeStamp'] > time.time() + 60:
        self.log.logging( "Heartbeat", "Log", "Timeout on pairing in progress status, reseting")
        self.pairing_in_progress = False

    # Network Topology
    if self.networkmap:
        phase = self.networkmap.NetworkMapPhase()
        self.log.logging("Heartbeat", "Debug", "processListOfDevices checking Topology phase: %s" % phase)
        # if phase == 0:
        #    self.networkmap.start_scan( )
        if phase == 1:
            self.log.logging("Heartbeat", "Status", "Z4D starts Network Topology")
            self.networkmap.start_scan()
        elif phase == 2:
            self.log.logging( "Heartbeat", "Debug", "processListOfDevices Topology scan is possible %s" % self.ControllerLink.loadTransmit(), )
            if self.ControllerLink.loadTransmit() < MAX_LOAD_ZIGATE:
                self.networkmap.continue_scan()

    # if (self.HeartbeatCount > QUIET_AFTER_START) and (self.HeartbeatCount > NETWORK_ENRG_START):
    #    # Network Energy Level
    if self.networkenergy and self.ControllerLink.loadTransmit() <= MAX_LOAD_ZIGATE:
        self.networkenergy.do_scan()

    self.log.logging( "Heartbeat", "Debug", "processListOfDevices END with HB: %s, Busy: %s, Enroll: %s, Load: %s" % (
        self.HeartbeatCount, self.busy, self.pairing_in_progress, self.ControllerLink.loadTransmit()), )
    return


def check_and_reset_device_if_needed(self, Devices, NwkId):

    self.log.logging( "Heartbeat", "Debug", "Check for reseting %s" %NwkId)

    now = time.time()
    device_ieee = self.ListOfDevices[NwkId]["IEEE"]
    ClusterTypeList = retrieve_widget_type_list(self, Devices, device_ieee, NwkId)
    for WidgetEp, Widget_Idx, WidgetType in ClusterTypeList:
        
        if WidgetType in ( "Motion", "Vibration", SWITCH_SELECTORS):
            device_unit = find_widget_unit_from_WidgetID(self, Widget_Idx )
            self.log.logging( "Heartbeat", "Debug", "Candidate for reseting %s %s %s %s %s" %(device_ieee, device_unit, NwkId, WidgetType, Widget_Idx))
            reset_device_ieee_unit_if_needed( self, Devices, device_ieee, device_unit, NwkId, WidgetType, Widget_Idx, now)


def add_device_group_for_ping(self, NwkId):

    if self.groupmgt is None or not self.pluginconf.pluginConf["pingViaGroup"]:
        return
    
    if not mainPoweredDevice(self, NwkId):
        return
    
    if self.ListOfDevices[NwkId][ "LogicalType" ] != "Router":
        return
    
    if "Capability" in self.ListOfDevices[NwkId] and "Full-Function Device" not in self.ListOfDevices[NwkId][ "Capability" ]:
        return
    
    target_ep = None
    for ep in self.ListOfDevices[NwkId]["Ep"]:
        if "0004" in self.ListOfDevices[NwkId]["Ep"][ ep ]:
            target_ep = ep

    if target_ep is None:
        return
    
    target_groupid = "%04x" %self.pluginconf.pluginConf["pingViaGroup"]
    if (
        "GroupMemberShip" in self.ListOfDevices[NwkId] 
        and target_groupid in self.ListOfDevices[NwkId][ "GroupMemberShip"][ target_ep ]
    ):
        return
        
    target_ep = None
    for ep in self.ListOfDevices[NwkId]["Ep"]:
        if "0004" in self.ListOfDevices[NwkId]["Ep"][ ep ]:
            target_ep = ep
    
    if target_ep:
        self.groupmgt.addGroupMemberShip(NwkId, target_ep, target_groupid)
