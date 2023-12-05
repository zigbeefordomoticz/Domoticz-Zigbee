#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: domoMaj.py
    Description: Update of Domoticz Widget
"""

from Modules.domoticzAbstractLayer import (domo_check_unit,
                                           domo_read_nValue_sValue,
                                           domo_read_SwitchType_SubType_Type,
                                           domo_update_api,
                                           find_widget_unit_from_WidgetID)
from Modules.domoTools import (RetreiveSignalLvlBattery,
                               RetreiveWidgetTypeList, TypeFromCluster,
                               UpdateDevice_v2, remove_bad_cluster_type_entry)
from Modules.switchSelectorWidgets import SWITCH_SELECTORS
from Modules.tools import zigpy_plugin_sanity_check
from Modules.zigateConsts import THERMOSTAT_MODE_2_LEVEL
from Modules.zlinky import (ZLINK_CONF_MODEL, get_instant_power,
                            get_tarif_color, zlinky_sum_all_indexes)
from Zigbee.zdpCommands import zdp_IEEE_address_request


def MajDomoDevice(self, Devices, NWKID, Ep, clusterID, value, Attribute_="", Color_=""):
    """
    MajDomoDevice
    Update domoticz device accordingly to Type found in EP and value/Color provided
    """

    # Sanity Checks
    if self.CommiSSionning and NWKID not in self.ListOfDevices:
        return
    
    if NWKID not in self.ListOfDevices:
        self.log.logging("Widget", "Error", f"MajDomoDevice - {NWKID} not known", NWKID)
        zigpy_plugin_sanity_check(self, NWKID)
        return
    
    if "Health" in self.ListOfDevices.get(NWKID, {}) and self.ListOfDevices[NWKID]["Health"] == "Disabled":
        # If the device has been disabled, just drop the message
        self.log.logging("Widget", "Debug", f"MajDomoDevice - disabled device: {NWKID}/{Ep} dropping message", NWKID)
        return
    
    if Ep not in self.ListOfDevices.get(NWKID, {}).get("Ep", []):
        self.log.logging("Widget", "Error", f"MajDomoDevice - {NWKID}/{Ep} not known Endpoint", NWKID)
        return
    
    check_and_update_db_status(self, NWKID)
    
    device_status = self.ListOfDevices.get(NWKID, {}).get("Status", "")
    if device_status != "inDB":
        self.log.logging("Widget", "Log", f"MajDomoDevice NwkId: {NWKID} status: {device_status} not inDB. Requesting IEEE for possible reconnection", NWKID)
        
        if not zigpy_plugin_sanity_check(self, NWKID):
            # Broadcast to 0xfffd: macRxOnWhenIdle = TRUE
            zdp_IEEE_address_request(self, 'fffd', NWKID, u8RequestType="00", u8StartIndex="00")
            return
    
    device_id_ieee = self.ListOfDevices.get(NWKID, {}).get("IEEE")
    if device_id_ieee is None:
        self.log.logging("Widget", "Error", f"MajDomoDevice - no IEEE for {NWKID}", NWKID)
        return

    model_name = self.ListOfDevices[NWKID].get("Model", "")

    self.log.logging( "Widget", "Debug", "MajDomoDevice NwkId: %s Ep: %s ClusterId: %s Value: %s ValueType: %s Attribute: %s Color: %s ModelName: %s" % (
        NWKID, Ep, clusterID, value, type(value), Attribute_, Color_, model_name), NWKID, )

    # Get the CluserType ( Action type) from Cluster Id
    ClusterType = TypeFromCluster(self, clusterID)
    self.log.logging("Widget", "Debug", "------> ClusterType = " + str(ClusterType), NWKID)

    ClusterTypeList = RetreiveWidgetTypeList(self, Devices, NWKID)
    self.log.logging("Widget", "Debug", "------> ClusterTypeList = " + str(ClusterTypeList), NWKID)
    
    if len(ClusterTypeList) == 0:
        # We don't have any widgets associated to the NwkId
        return

    WidgetByPassEpMatch = ("XCube", "Aqara", "DSwitch", "DButton", "DButton_3")

    for WidgetEp, WidgetId, WidgetType in ClusterTypeList:
        if WidgetEp == "00":
            # Old fashion
            WidgetEp = "01"  # Force to 01

        self.log.logging( "Widget", "Debug", "----> processing WidgetEp: %s, WidgetId: %s, WidgetType: %s" % (
            WidgetEp, WidgetId, WidgetType), NWKID, )
        
        if WidgetType not in WidgetByPassEpMatch and WidgetEp != Ep:
            # We need to make sure that we are on the right Endpoint
            self.log.logging( "Widget", "Debug", "------> skiping this WidgetEp as do not match Ep : %s %s" % (
                WidgetEp, Ep), NWKID,)
            continue

        DeviceUnit = find_widget_unit_from_WidgetID(self, Devices, WidgetId )
        
        if DeviceUnit is None:
            self.log.logging( "Widget", "Error", "Device %s not found !!!" % WidgetId, NWKID)
            # House keeping, we need to remove this bad clusterType
            if remove_bad_cluster_type_entry(self, NWKID, Ep, clusterID, WidgetId ):
                self.log.logging( "Widget", "Log", "WidgetID %s not found, successfully remove the entry from device" % WidgetId, NWKID)
            else:
                self.log.logging( "Widget", "Error", "WidgetID %s not found, unable to remove the entry from device" % WidgetId, NWKID)
            continue
        
        elif domo_check_unit(self, Devices, device_id_ieee, DeviceUnit) not in Devices:
            continue

        prev_nValue, prev_sValue = domo_read_nValue_sValue(self, Devices, device_id_ieee, DeviceUnit)
        switchType, Subtype, _ = domo_read_SwitchType_SubType_Type(self, Devices, device_id_ieee, DeviceUnit)
       
        # device_id_ieee is the DeviceID (IEEE)
        # DeviceUnit is the Device unit
        # WidgetEp is the Endpoint to which the widget is linked to
        # WidgetId is the Device ID
        # WidgetType is the Widget Type at creation
        # ClusterType is the Type based on clusters
        # ClusterType: This the Cluster action extracted for the particular Endpoint based on Clusters.
        # WidgetType : This is the Type of Widget defined at Widget Creation
        # value      : this is value comming mostelikely from readCluster. Be carreful depending on the cluster, the value is String or Int
        # Attribute_ : If used This is the Attribute from readCluster. Will help to route to the right action
        # Color_     : If used This is the color value to be set

        self.log.logging( "Widget", "Debug", "------> ClusterType: %s WidgetEp: %s WidgetId: %s WidgetType: %s Attribute_: %s" % ( 
            ClusterType, WidgetEp, WidgetId, WidgetType, Attribute_), NWKID, )

        SignalLevel, BatteryLevel = RetreiveSignalLvlBattery(self, NWKID)
        self.log.logging("Widget", "Debug", "------> SignalLevel: %s , BatteryLevel: %s" % (SignalLevel, BatteryLevel), NWKID)

        if ClusterType == "Alarm" and WidgetType == "Alarm_ZL" and Attribute_ == "0005":
            # This is Alarm3 for ZLinky Intensity alert
            value, text = value.split("|")
            nValue = int(value)
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, text, BatteryLevel, SignalLevel)

        if ClusterType == "Alarm" and WidgetType == "Alarm_ZL2" and Attribute_ == "0001":
            # Notification Next Day Color and Peak
            
            tuple_value = value.split("|")
            if len(tuple_value) != 2:
                self.log.logging( "Widget", "Error", "------> Expecting 2 values got %s in Value = %s for Nwkid: %s Attribute: %s" % (
                    len(tuple_value), value, NWKID, Attribute_), NWKID, )
                continue

            value, text = tuple_value
            nValue = int(value)
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, text, BatteryLevel, SignalLevel)

        if ClusterType == "Alarm" and WidgetType == "Alarm_ZL3" and Attribute_ == "0020":
            if value is None or len(value) == 0:
                return
            # Notification Day Color and Peak
            if value == "TH..":
                # Toutes Heures
                nValue = 0
                sValue = "All Hours"

            elif value == "HC..":
                # Heures Creuses
                nValue = 1
                sValue = "Off-peak Hours"

            elif value == "HP..":
                # Heures Pleines
                nValue = 2
                sValue = "Peak Hours"

            elif value == "HN..":
                # Heures Normales
                nValue = 1
                sValue = "Normal Hours"

            elif value == "PM..":
                # Pointe Mobile
                nValue = 4
                sValue = "Mobile peak Hours"
                
            # Standard Tempo
            elif value == "BHC":
                nValue = 1
                sValue = "Bleu HC"
            elif value == "BHP":
                nValue = 1
                sValue = "Bleu HP"
                
            elif value == "WHC":
                nValue = 2
                sValue = "Blanc HC"
            elif value == "WHP":
                nValue = 2
                sValue = "Blanc HP"
                
            elif value == "RHC":
                nValue = 4
                sValue = "Rouge HC"
            elif value == "RHP":
                nValue = 4
                sValue = "Rouge HP"
                
            elif value[0] == "B":
                # Blue
                nValue = 1
                sValue = "Blue Hours"
            elif value[0] == "W":
                # Whte
                nValue = 2
                sValue = "White Hours"
            elif value[0] == "R":
                # Red
                nValue = 4
                sValue = "RED Hours"
                
            else:
                # Unknow
                nValue = 3
                sValue = "Unknown"
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

        if "Ampere" in ClusterType and WidgetType == "Ampere" and Attribute_ == "0508":
            sValue = "%s" % (round(float(value), 2))
            self.log.logging("Widget", "Debug", "------>  Ampere : %s" % sValue, NWKID)
            UpdateDevice_v2(self, Devices, DeviceUnit, 0, str(sValue), BatteryLevel, SignalLevel)

        if "Ampere" in ClusterType and WidgetType == "Ampere3" and Attribute_ in ("0508", "0908", "0a08"):
            # Retreive the previous values
            sValue = "%s;%s;%s" % (0, 0, 0)
                                        
            ampere1, ampere2, ampere3 = retrieve_data_from_current(self, Devices, device_id_ieee, DeviceUnit, "%s;%s;%s")
            if ampere2 == ampere3 == '65535.0':
                self.log.logging("Widget", "Debug", "------>  Something going wrong ..... ampere %s %s %s" %(ampere1, ampere2, ampere3))
                ampere2 = '0.0'
                ampere3 = '0.0'
            ampere = round(float(value), 2)
            if Attribute_ == "0508":
                # Line 1
                sValue = "%s;%s;%s" % (ampere, ampere2, ampere3)
            elif Attribute_ == "0908":
                # Line 2
                sValue = "%s;%s;%s" % (ampere1, ampere, ampere3)
            elif Attribute_ == "0a08":
                # Line 3
                sValue = "%s;%s;%s" % (ampere1, ampere2, ampere)

            self.log.logging("Widget", "Debug", "------>  Ampere3 : %s from Attribute: %s" % (sValue, Attribute_), NWKID)
            UpdateDevice_v2(self, Devices, DeviceUnit, 0, str(sValue), BatteryLevel, SignalLevel)

        if "PWFactor" == ClusterType and WidgetType == "PowerFactor":
            self.log.logging("Widget", "Debug", "PowerFactor %s WidgetType: %s Value: %s (%s)" % (
                NWKID, WidgetType, value, type(value)), NWKID)

            nValue = round(value, 1)
            sValue = str(nValue)
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

        if "Power" in ClusterType:  # Instant Power/Watts
            # Power and Meter usage are triggered only with the Instant Power usage.
            # it is assumed that if there is also summation provided by the device, that
            # such information is stored on the data structuture and here we will retreive it.
            # value is expected as String

            if WidgetType == "Power" and (Attribute_ in ("", "050f") or clusterID == "000c"):  # kWh
                if (( isinstance( value, (int, float)) and value < 0) or (float(value) < 0) ) and is_PowerNegative_widget( ClusterTypeList):
                    self.log.logging("Widget", "Debug", "------>There is a PowerNegative widget and the value is negative. Skiping here", NWKID)
                    UpdateDevice_v2(self, Devices, DeviceUnit, 0, "0", BatteryLevel, SignalLevel)
                    continue

                nValue = round(float(value), 2)
                sValue = value
                self.log.logging("Widget", "Debug", "------>Power  : %s" % sValue, NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(sValue), BatteryLevel, SignalLevel)

            if WidgetType == "ProdPower" and Attribute_ == "":
                if value > 0:
                    self.log.logging("Widget", "Debug", "------>the value is Positive. Skiping here", NWKID)
                    UpdateDevice_v2(self, Devices, DeviceUnit, 0, "0", BatteryLevel, SignalLevel)
                    continue

                nValue = abs( round(float(value), 2) )
                sValue = abs(value)
                self.log.logging("Widget", "Debug", "------>PowerNegative  : %s" % sValue, NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(sValue), BatteryLevel, SignalLevel)

            if WidgetType == "P1Meter" and Attribute_ == "0000":
                self.log.logging("Widget", "Debug", "------>  P1Meter : %s (%s)" % (value, type(value)), NWKID)
                # P1Meter report Instant and Cummulative Power.
                # We need to retreive the Cummulative Power.
                cur_usage1, cur_usage2, cur_return1, cur_return2, _, _ = retrieve_data_from_current(self, Devices, device_id_ieee, DeviceUnit, "0;0;0;0;0;0")
                
                usage1 = usage2 = return1 = return2 = cons = prod = 0
                
                if "0702" in self.ListOfDevices[NWKID]["Ep"][Ep] and "0400" in self.ListOfDevices[NWKID]["Ep"][Ep]["0702"]:
                    cons = round(float(self.ListOfDevices[NWKID]["Ep"][Ep]["0702"]["0400"]), 2)
                usage1 = int(float(value))

                sValue = "%s;%s;%s;%s;%s;%s" % (usage1, usage2, return1, return2, cons, prod)
                self.log.logging("Widget", "Debug", "------>  P1Meter : " + sValue, NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, str(sValue), BatteryLevel, SignalLevel)

            if (
                WidgetType == "P1Meter_ZL" 
                and model_name in ZLINK_CONF_MODEL 
                and Attribute_ in ( "0100", "0102", "0104", "0106", "0108", "010a")
                ):
 
                if Attribute_ != "050f" and Ep == "01" and Attribute_ not in ("0100", "0102"):
                    # Ep = 01, so we store Base, or HP,HC, or BBRHCJB, BBRHPJB
                    continue
                if Attribute_ != "050f" and Ep == "f2" and Attribute_ not in ("0104", "0106"):
                    # Ep = f2, so we store BBRHCJW, BBRHPJW
                    continue
                if Attribute_ != "050f" and Ep == "f3" and Attribute_ not in ("0108", "010a"):
                    # Ep == f3, so we store BBRHCJR, BBRHPJR
                    continue
                
                tarif_color = get_tarif_color( self, NWKID )

                self.log.logging("ZLinky", "Debug", "------>  P1Meter_ZL : %s Attribute: %s  Color: %s (%s)" % (
                    value, Attribute_, tarif_color, type(value)), NWKID)
                
                # P1Meter report Instant and Cummulative Power.
                # We need to retreive the Cummulative Power.
                cur_usage1, cur_usage2, cur_return1, cur_return2, cur_cons, cur_prod = retrieve_data_from_current(self, Devices, device_id_ieee, DeviceUnit, "0;0;0;0;0;0")
                usage1 = usage2 = return1 = return2 = cons = prod = 0
                self.log.logging("ZLinky", "Debug", "------>  P1Meter_ZL (%s): retreive value: %s;%s;%s;%s;%s;%s" % (Ep, cur_usage1, cur_usage2, cur_return1, cur_return2, cur_cons, cur_prod), NWKID)

                # We are so receiving a usage update
                self.log.logging( "ZLinky", "Debug", "------>  P1Meter_ZL : Trigger by Index Update %s Ep: %s" % (Attribute_, Ep), NWKID, )
                cons = get_instant_power(self, NWKID)
                if Attribute_ in ("0000", "0100", "0104", "0108"):
                    # Usage 1
                    usage1 = int(round(float(value), 0))
                    usage2 = cur_usage2
                    return1 = cur_return1
                    return2 = cur_return2
                    if usage1 == cur_usage1:
                        # Skip update as there is no consumption
                        continue

                elif Attribute_ in ("0102", "0106", "010a"):
                    # Usage 2
                    usage1 = cur_usage1
                    usage2 = int(round(float(value), 0))
                    return1 = cur_return1
                    return2 = cur_return2
                    if usage2 == cur_usage2:
                        # Skip update as there is no consumption
                        continue

                if tarif_color == "Blue" and Ep != "01" or tarif_color == "White" and Ep != "f2" or tarif_color == "Red" and Ep != "f3":
                    cons = 0.0

                sValue = "%s;%s;%s;%s;%s;%s" % (usage1, usage2, return1, return2, cons, cur_prod)
                self.log.logging("ZLinky", "Debug", "------>  P1Meter_ZL (%s): %s" % (Ep, sValue), NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, str(sValue), BatteryLevel, SignalLevel)

        if "Meter" in ClusterType:  # Meter Usage.
            
            if WidgetType == "GazMeter" and Attribute_ == "0000":
                # Gaz Meter 
                sValue = "%s" %value
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)
                
            elif WidgetType == "Counter" and Attribute_ == "0000":
                sValue = "%s" %int(value)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "ConsoMeter" and Attribute_ == "0000":
                # Consummed Energy
                sValue = "%s" %int(value)
                self.log.logging("Widget", "Debug", "------>ConsoMeter  : %s" % sValue, NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "ProdMeter" and Attribute_ == "0001":
                # Produced Energy injected
                sValue = "%s" %int(value)
                self.log.logging("Widget", "Debug", "------>ProdMeter  : %s" % sValue, NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)

            # value is string an represent the Instant Usage
            elif (
                model_name in ZLINK_CONF_MODEL
                and WidgetType == "Meter" 
                and ( 
                    Attribute_ == "0000" 
                    or ( Attribute_ in ("0100", "0102") and Ep == "01") 
                    or ( Attribute_ in ("0104", "0106") and Ep == "f2")
                    or ( Attribute_ in ("0108", "010a") and Ep == "f3")
                    )
                ):
                check_set_meter_widget( self, Devices, device_id_ieee, DeviceUnit, 0)    
                instant, _summation = retrieve_data_from_current(self, Devices, device_id_ieee, DeviceUnit, "0;0")
                summation = round(float(zlinky_sum_all_indexes( self, NWKID )), 2)
                self.log.logging("ZLinky", "Debug", "------> Summation for Meter : %s" %summation)
                
                sValue = "%s;%s" % (instant, summation)
                self.log.logging("ZLinky", "Debug", "------>  : " + sValue)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)
                
            elif WidgetType == "Meter" and Attribute_ == "050f":
                # We receive Instant Power
                check_set_meter_widget( self, Devices, device_id_ieee, DeviceUnit, 0)
                _instant, summation = retrieve_data_from_current(self, Devices, device_id_ieee, DeviceUnit, "0;0")
                instant = round(float(value), 2)
                sValue = "%s;%s" % (instant, summation)
                self.log.logging("Widget", "Debug", "------>  : " + sValue)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)

            elif (WidgetType == "Meter" and Attribute_ == "") or (WidgetType == "Power" and clusterID == "000c"):  # kWh
                # We receive Instant
                # Let's check if we have Summation in the datastructutre
                summation = 0
                if ( 
                    "0702" in self.ListOfDevices[NWKID]["Ep"][Ep] 
                    and "0000" in self.ListOfDevices[NWKID]["Ep"][Ep]["0702"] 
                    and self.ListOfDevices[NWKID]["Ep"][Ep]["0702"]["0000"] not in ({}, "", "0")
                ): 
                    # summation = int(self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0000'])
                    summation = self.ListOfDevices[NWKID]["Ep"][Ep]["0702"]["0000"]

                instant = round(float(value), 2)
                # Did we get Summation from Data Structure
                if summation != 0:
                    summation = int(float(summation))
                    sValue = "%s;%s" % (instant, summation)
                    # We got summation from Device, let's check that EnergyMeterMode is
                    # correctly set to 0, if not adjust
                    check_set_meter_widget( self, Devices, device_id_ieee, DeviceUnit, 0)

                else:
                    sValue = "%s;" % (instant)
                    check_set_meter_widget( self, Devices, device_id_ieee, DeviceUnit, 1)

                    # No summation retreive, so we make sure that EnergyMeterMode is
                    # correctly set to 1 (compute), if not adjust

                self.log.logging("Widget", "Debug", "------>  : " + sValue)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)

        if "WaterCounter" in ClusterType and WidgetType == "WaterCounter":
            # /json.htm?type=command&param=udevice&idx=IDX&nvalue=0&svalue=INCREMENT
            # INCREMENT = Integer of the increment of the counter. 
            # For Counters the standard counter dividers apply (menu setup - settings - tab counters)
            # will increment the counter value by 1. 
            # To reset an incremental counter, set the svalue to a negative integer equal to the current total of the counter. 
                sValue = "%s" %value 
                self.log.logging("Widget", "Debug", "WaterCounter ------>  : %s" %sValue, NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
  
        if "Voltage" in ClusterType:  # Volts
            # value is str
            if WidgetType == "Voltage" and Attribute_ == "":
                nValue = round(float(value), 2)
                sValue = "%s;%s" % (nValue, nValue)
                self.log.logging("Widget", "Debug", "------>  : " + sValue, NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)

        if "ThermoSetpoint" in ClusterType:  # Thermostat SetPoint
            # value is a str
            if WidgetType == "ThermoSetpoint" and Attribute_ in ("4003", "0012"):
                setpoint = round(float(value), 2)
                # Normalize SetPoint value with 2 digits
                nValue = 0
                sValue = str_round(float(setpoint), 2)  # 2 decimals
                self.log.logging("Widget", "Debug", "------>  Thermostat nValue: %s SetPoint: %s sValue: %s" % (
                    0, setpoint, sValue), NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)

        if "Analog" in ClusterType:
            if WidgetType == "Voc" and Attribute_ == "":
                sValue = str( value )
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "Motionac01" and Ep == "01":  # Motionac01
                if value <= 7:
                    nValue= value + 1
                    sValue = str(nValue * 10)
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
            
            elif WidgetType == "Analog":
                # Analog Value from Analog Input cluster
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, value, BatteryLevel, SignalLevel)

        if ("XCube" in ClusterType) or ("Analog" in ClusterType and model_name in ("lumi.sensor_cube.aqgl01", "lumi.sensor_cube")):  # XCube Aqara or Xcube
            if WidgetType == "Aqara" :
                self.log.logging(
                    "Widget",
                    "Debug",
                    "-------->  XCube Aqara Ep: %s Attribute_: %s Value: %s = " % (Ep, Attribute_, value),
                    NWKID,
                )
                if Ep == "02" and Attribute_ == "":  # Magic Cube Aqara
                    self.log.logging("Widget", "Debug", "---------->  XCube update device with data = " + str(value), NWKID)
                    nValue = int(value)
                    sValue = value
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif Ep == "03":  # Magic Cube Aqara Rotation
                    if Attribute_ == "0055":  # Rotation Angle
                        self.log.logging(
                            "Widget",
                            "Debug",
                            "---------->  XCube update Rotaion Angle with data = " + str(value),
                            NWKID,
                        )
                        # Update Text widget ( unit + 1 )
                        nValue = 0
                        sValue = value
                        UpdateDevice_v2(self, Devices, DeviceUnit + 1, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

                    else:
                        self.log.logging("Widget", "Debug", "---------->  XCube update  with data = " + str(value), NWKID)
                        nValue = int(value)
                        sValue = value
                        if nValue == 80:
                            nValue = 8

                        elif nValue == 90:
                            nValue = 9

                        self.log.logging(
                            "Widget",
                            "Debug",
                            "-------->  XCube update device with data = %s , nValue: %s sValue: %s" % (value, nValue, sValue),
                            NWKID,
                        )
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == "XCube" and Ep == "02":  # cube xiaomi
                if value == "0000":  # shake
                    state = "10"
                    data = "01"
                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif value in ("0204", "0200", "0203", "0201", "0202", "0205"):
                    state = "50"
                    data = "05"
                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif value in ("0103", "0100", "0104", "0101", "0102", "0105"):  # Slide/M%ove
                    state = "20"
                    data = "02"
                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif value == "0003":  # Free Fall
                    state = "70"
                    data = "07"
                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif "0004" <= value <= "0059":  # 90°
                    state = "30"
                    data = "03"
                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif value >= "0060":  # 180°
                    state = "90"
                    data = "09"
                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

        if "Valve" in ClusterType and (WidgetType == "Valve" and Attribute_ in ("026d", "4001", "0008")):
            nValue = round(value, 1)
            sValue = str(nValue)
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

        if "ThermoMode" in ClusterType:  # Thermostat Mode
            self.log.logging("Widget", "Debug", "ThermoMode %s WidgetType: %s Value: %s (%s) Attribute_: %s" % ( 
                NWKID, WidgetType, value, type(value), Attribute_), NWKID)

            if WidgetType == "ThermoModeEHZBRTS" and Attribute_ == "e010":  # Thermostat Wiser
                # value is str
                self.log.logging("Widget", "Debug", "------>  EHZBRTS Schneider Thermostat Mode %s" % value, NWKID)
                THERMOSTAT_MODE = {
                    0: "00",  # Mode Off
                    1: "10",  # Manual
                    2: "20",  # Schedule
                    3: "30",  # Energy Saver
                    4: "40",  # Schedule Energy Saver
                    5: "50",  # Holiday Off
                    6: "60",  # Holiday Frost Protection
                }
                _mode = int(value, 16)
                if _mode in THERMOSTAT_MODE:
                    nValue = _mode
                    sValue = THERMOSTAT_MODE[_mode]
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "HeatingSwitch" and Attribute_ == "001c":
                self.log.logging("Widget", "Debug", "------>  HeatingSwitch %s" % value, NWKID)
                if value == 0:
                    UpdateDevice_v2(self, Devices, DeviceUnit, 0, "Off", BatteryLevel, SignalLevel)
                elif value == 4:
                    UpdateDevice_v2(self, Devices, DeviceUnit, 1, "On", BatteryLevel, SignalLevel)

            elif WidgetType == "HeatingStatus" and Attribute_ == "0124":
                self.log.logging("Widget", "Debug", "------>  HeatingStatus %s" % value, NWKID)
                if value == 0:
                    UpdateDevice_v2(self, Devices, DeviceUnit, 0, "Not Heating", BatteryLevel, SignalLevel)
                elif value == 1:
                    UpdateDevice_v2(self, Devices, DeviceUnit, 1, "Heating", BatteryLevel, SignalLevel)

            elif WidgetType == "ThermoOnOff" and Attribute_ == "6501":
                self.log.logging("Widget", "Debug", "------>  Thermo On/Off %s" % value, NWKID)
                if value == 0:
                    UpdateDevice_v2(self, Devices, DeviceUnit, 0, "Off", BatteryLevel, SignalLevel)
                elif value == 1:
                    UpdateDevice_v2(self, Devices, DeviceUnit, 1, "On", BatteryLevel, SignalLevel)

            elif WidgetType == "HACTMODE" and Attribute_ == "e011":   # Wiser specific Fil Pilote
                # value is str
                self.log.logging("Widget", "Debug", "------>  ThermoMode HACTMODE: %s" % (value), NWKID)
                THERMOSTAT_MODE = {0: "10", 1: "20"}  # Conventional heater  # fip enabled heater
                _mode = ((int(value, 16) - 0x80) >> 1) & 1

                if _mode in THERMOSTAT_MODE:
                    sValue = THERMOSTAT_MODE[_mode]
                    nValue = _mode + 1
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "LegranCableMode" and clusterID == "fc01":    # Legrand
                # value is str
                self.log.logging("Widget", "Debug", "------>  Legrand Mode: %s" % (value), NWKID)
                THERMOSTAT_MODE = {0x0100: "10", 0x0200: "20"}    # Conventional heater  # fip enabled heater
                _mode = int(value, 16)

                if _mode not in THERMOSTAT_MODE:
                    return

                sValue = THERMOSTAT_MODE[_mode]
                nValue = int(sValue) // 10
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "FIP" and Attribute_ in ("0000", "e020"):     # Wiser specific Fil Pilote
                # value is str
                self.log.logging("Widget", "Debug", "------>  ThermoMode FIP: %s" % (value), NWKID)
                FIL_PILOT_MODE = {
                    0: "10",
                    1: "20",  # confort -1
                    2: "30",  # confort -2
                    3: "40",  # eco
                    4: "50",  # frost protection
                    5: "60",
                }
                _mode = int(value, 16)
                if _mode not in FIL_PILOT_MODE:
                    return
                nValue = _mode + 1
                sValue = FIL_PILOT_MODE[_mode]

                if Attribute_ == "e020":      # Wiser specific Fil Pilote
                    ep_data = self.ListOfDevices[NWKID].get("Ep", {}).get(Ep, {}).get("0201", {}).get("e011", "")

                    if "0201" in ep_data and "e011" in ep_data and ep_data["e011"] != {} and ep_data["e011"] != "":
                        _value_mode_hact = ep_data["e011"]
                        _mode_hact = ((int(_value_mode_hact, 16) - 0x80)) & 1

                        if _mode_hact == 0:
                            self.log.logging("Widget", "Debug", "------> Disable FIP widget: %s" % (value), NWKID)
                            nValue = 0
                    
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

                elif clusterID == "fc40":  # Legrand FIP
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "ThermoMode_3" and Attribute_ == "001c":
                # Mapping of values to nValue and sValue
                mode_mapping = {
                    0x00: (0, "Off"),
                    0x01: (1, "10"),
                    0x03: (2, "20")
                }

                if "ThermoMode_3" not in SWITCH_SELECTORS:
                    continue
                
                if int(value) in mode_mapping:
                    nValue, sValue = mode_mapping[int(value)]
                    self.log.logging("Widget", "Debug", f"------> Thermostat Mode 3 {value} {nValue}:{sValue}", NWKID)
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)
                else:
                    # Unknown value
                    self.log.logging("Widget", "Error", f"MajDomoDevice - Unknown value for {NWKID}/{Ep}, clusterID: {clusterID}, value: {value}, Attribute_: {Attribute_}", NWKID)
                    continue
                
            elif WidgetType == "ThermoMode_2" and Attribute_ == "001c":
                # Use by Tuya TRV
                if "ThermoMode_2" not in SWITCH_SELECTORS:
                    continue
                
                value_mapping = SWITCH_SELECTORS["ThermoMode_2"]

                if value in value_mapping:
                    nValue, sValue = value_mapping[value]
                    self.log.logging("Widget", "Debug", f"------> Thermostat Mode 2 {value} {nValue}:{sValue}", NWKID)
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)
                else:
                    self.log.logging("Widget", "Error", f"Unknown TermoMode2 value: {value}")
                    continue

            elif WidgetType == "ThermoMode_4" and Attribute_ == "001c":
                # Use by Tuya TRV
                nValue = value
                sValue = '%02d' %( nValue * 10)
                self.log.logging("Widget", "Debug", "------>  Thermostat Mode 4 %s %s:%s" % (value, nValue, sValue), NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType in ("ThermoMode_5", "ThermoMode_6") and Attribute_ == "001c":
                # Use by Tuya TRV
                nValue = value
                sValue = '%02d' %( nValue * 10)
                self.log.logging("Widget", "Debug", "------>  Thermostat Mode 5 %s %s:%s" % (value, nValue, sValue), NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)
                
            elif model_name == "TS0601-eTRV5" and WidgetType in ("ThermoMode_5",) and Attribute_ == "6501":   
                if value == 0:
                    self.log.logging("Widget", "Debug", "------>  Thermostat Mode 5 %s %s:%s" % (value, 0, '00'), NWKID)
                    UpdateDevice_v2(self, Devices, DeviceUnit, 0, '00', BatteryLevel, SignalLevel)
                            
            elif WidgetType in ("ThermoMode", "ACMode") and Attribute_ == "001c":
                self.log.logging("Widget", "Debug", f"------> Thermostat Mode {value} type: {type(value)}", NWKID)

                mode_mapping = {
                    "00": (0, "00"),  # Off
                    "20": (1, "10"),  # Cool
                    "30": (2, "20"),  # Heat
                    "40": (3, "30"),  # Dry
                    "50": (4, "40")   # Fan
                }

                if value in THERMOSTAT_MODE_2_LEVEL:
                    nValue, sValue = mode_mapping[THERMOSTAT_MODE_2_LEVEL[value]]
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType in ("CAC221ACMode", ) and Attribute_ == "001c":
                self.log.logging("Widget", "Debug", f"------> Thermostat CAC221ACMode {value} type: {type(value)}", NWKID)
            
                mode_mapping = {
                    "00": (0, "00"),  # Off
                    "10": (1, "10"),  # Auto
                    "20": (2, "20"),  # Cool
                    "30": (3, "30"),  # Heat
                    "40": (4, "40"),  # Dry
                    "50": (5, "50")   # Fan
                }
            
                if value in THERMOSTAT_MODE_2_LEVEL:
                    nValue, sValue = mode_mapping[THERMOSTAT_MODE_2_LEVEL[value]]
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)
                       
        if ClusterType == "PM25" and WidgetType == "PM25":
            nvalue = round(value, 0)
            svalue = "%s" % (nvalue,)
            UpdateDevice_v2(self, Devices, DeviceUnit, nvalue, svalue, BatteryLevel, SignalLevel)

        if ClusterType == "PM25" and WidgetType == "SmokePPM":
            nvalue = int(value)
            svalue = "%s" % (nvalue,)
            UpdateDevice_v2(self, Devices, DeviceUnit, nvalue, svalue, BatteryLevel, SignalLevel)
  
        if ClusterType == "Alarm" and WidgetType == "AirPurifierAlarm":
            sValue = "%s %% used" %( value, )
            # This is Alarm for Air Purifier
            if value >= 100:
                # Red
                nValue = 4
            elif value >= 90:
                # Orange
                nValue = 3
            elif value >= 70:
                # Yellow
                nValue = 2
            else:
                # Green
                nValue = 1
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)
            
        if Attribute_ == "0006" and ClusterType == "FanControl" and WidgetType == "AirPurifierMode":
            nValue = value
            sValue = "%s" %(10 * value,)
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)
    
        if Attribute_ == "0007" and ClusterType == "FanControl" and WidgetType == "FanSpeed":
            nValue = round(value, 1)
            sValue = str(nValue)
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType == "AirQuality" and Attribute_ == "0002":
            # eco2 for VOC_Sensor from Nexturn is provided via Temp cluster
            nvalue = round(value, 0)
            svalue = "%s" % (nvalue)
            UpdateDevice_v2(self, Devices, DeviceUnit, nvalue, svalue, BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType == "Voc" and Attribute_ == "0003":
            # voc for VOC_Sensor from Nexturn is provided via Temp cluster
            svalue = "%s" % (round(value, 1))
            UpdateDevice_v2(self, Devices, DeviceUnit, 0, svalue, BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType == "CH2O" and Attribute_ == "0004":
            # ch2o for Tuya Smart Air fis provided via Temp cluster
            svalue = "%s" % (round(value, 2))
            UpdateDevice_v2(self, Devices, DeviceUnit, 0, svalue, BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType == "CarbonDioxyde" and Attribute_ == "0005":
            # CarbonDioxyde for Tuya Smart Air provided via Temp cluster
            svalue = "%s" % (round(value, 1))
            UpdateDevice_v2(self, Devices, DeviceUnit, 0, svalue, BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType in ("Temp", "Temp+Hum", "Temp+Hum+Baro") and Attribute_ == "":  # temperature
            if check_erratic_value(self, NWKID, "Temp", value, -50, 100):
                # We got an erratic value, no update to Domoticz
                self.log.logging("Widget", "Debug", "%s Receive an erratic Temp: %s, WidgetType: >%s<" % (
                    NWKID, value, WidgetType), NWKID)
                return

            self.log.logging("Widget", "Log", "------> %s %s %s Temp: %s, WidgetType: >%s<" % (
                NWKID, ClusterType, WidgetType, value, WidgetType), NWKID)
            adjvalue = 0
            if self.domoticzdb_DeviceStatus:
                try:
                    adjvalue = round(self.domoticzdb_DeviceStatus.retreiveAddjValue_temp(Devices[DeviceUnit].ID), 1)
                except Exception as e:
                    self.log.logging("Widget", "Error", "Error while trying to get Adjusted Value for Temp %s %s %s %s" % (
                        NWKID, value, WidgetType, e), NWKID)

            current_temp, current_humi, current_hum_stat, current_baro, current_baro_forecast = retrieve_data_from_current(self, Devices, device_id_ieee, DeviceUnit, "0;0;0;0;0")

            self.log.logging("Widget", "Debug", f"------> Adj Value: {adjvalue} from: {value} to {value + adjvalue} [{current_temp}, {current_humi}, {current_hum_stat}, {current_baro}, {current_baro_forecast}]", NWKID)

            NewNvalue = 0
            NewSvalue = ""

            if WidgetType == "Temp":
                NewNvalue = round(value + adjvalue, 1)
                NewSvalue = str(NewNvalue)

            elif WidgetType == "Temp+Hum":
                NewSvalue = f"{round(value + adjvalue, 1)};{current_humi};{current_hum_stat}"

            elif WidgetType == "Temp+Hum+Baro":
                NewSvalue = f"{round(value + adjvalue, 1)};{current_humi};{current_hum_stat};{current_baro};{current_baro_forecast}"

            self.log.logging("Widget", "Debug", f"------> {WidgetType} update: {NewNvalue} - {NewSvalue}")
            UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

        if ClusterType == "Humi" and WidgetType in ("Humi", "Temp+Hum", "Temp+Hum+Baro"):

            self.log.logging("Widget", "Log", "------> %s %s %s Humi: %s, WidgetType: >%s<" % (
                NWKID, ClusterType, WidgetType, value, WidgetType), NWKID)
            
            NewNvalue = 0
            NewSvalue = ""
            humi_status = calculate_humidity_status(value)
            current_temp, current_humi, current_hum_stat, current_baro, current_baro_forecast = retrieve_data_from_current(self, Devices, device_id_ieee, DeviceUnit, "0;0;0;0;0")

            if WidgetType == "Humi":
                NewNvalue = value
                NewSvalue = str(humi_status)
                self.log.logging("Widget", "Debug", f"------> Humi update: {NewNvalue} - {NewSvalue}")
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum":
                NewSvalue = f"{current_temp};{value};{humi_status}"
                self.log.logging("Widget", "Debug", f"------> Temp+Hum update: {NewNvalue} - {NewSvalue}")
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum+Baro":
                NewSvalue = f"{current_temp};{value};{humi_status};{current_baro};{current_baro_forecast}"
                self.log.logging("Widget", "Debug", f"------> Temp+Hum+Baro update: {NewNvalue} - {NewSvalue}")
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

        if ClusterType == "Baro" and WidgetType in ("Baro", "Temp+Hum+Baro"):
            self.log.logging("Widget", "Log", "------> %s %s %s Baro: %s, WidgetType: >%s<" % (
                NWKID, ClusterType, WidgetType, value, WidgetType), NWKID)

            adjvalue = 0
            try:
                if self.domoticzdb_DeviceStatus:
                    adjvalue = round(self.domoticzdb_DeviceStatus.retreiveAddjValue_baro(Devices[DeviceUnit].ID), 1)
            except Exception as e:
                self.log.logging("Widget", "Error", f"Error while trying to get Adjusted Value for Temp {NWKID} {value} {WidgetType} {e}", NWKID)
        
            baroValue = round(value + adjvalue, 1)
            self.log.logging("Widget", "Debug", f"------> Adj Value: {adjvalue} from: {value} to {baroValue}", NWKID)
        
            NewNvalue = 0
            NewSvalue = ""
            
            Bar_forecast = calculate_baro_forecast(baroValue)
            current_temp, current_humi, current_hum_stat, current_baro, current_baro_forecast = retrieve_data_from_current(self, Devices, device_id_ieee, DeviceUnit, "0;0;0;0;0")
        
            if WidgetType == "Baro":
                NewSvalue = f"{baroValue};{Bar_forecast}"
            elif WidgetType == "Temp+Hum+Baro":
                NewSvalue = f"{current_temp};{current_humi};{current_hum_stat};{baroValue};{Bar_forecast}"
        
            UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

        if "BSO-Orientation" in ClusterType and WidgetType == "BSO-Orientation":
            angle = int(value, 16)
            nValue = min(10, round(angle / 10) + 1)
            sValue = str(nValue * 10)
            self.log.logging("Widget", "Debug", f"BSO-Orientation Angle: 0x{value}/{angle} Converted into nValue: {nValue} sValue: {sValue}")
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

        if ClusterType == "Switch" and WidgetType == "SwitchAlarm":
            if isinstance(value, str):
                nValue = int(value, 16)
            else:
                self.log.logging("Widget", "Error", "Looks like this value is not provided in str for %s/%s %s %s %s %s %s" %(
                    NWKID, Ep, model_name, clusterID, ClusterType, WidgetType, value))
                nValue = value
                
            sValue = "%02x" %nValue
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)
            
        if ClusterType == "TamperSwitch" and WidgetType == "SwitchAlarm":
            nValue = value
            sValue = "%02x" %nValue
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

        if "Notification" in ClusterType and WidgetType == "Notification":
            # Notification
            # value is a str containing all Orientation information to be updated on Text Widget
            nValue = 0
            sValue = value
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

                   
        if ClusterType in ( "Motion", "Door",) and WidgetType == "Motion":
            self.log.logging("Widget", "Debug", "------> Motion %s" % (value), NWKID)
            if isinstance(value, str):
                nValue = int(value, 16)
            else:
                self.log.logging("Widget", "Error", "Looks like this value is not provided in str for %s/%s %s %s %s %s %s" %(
                    NWKID, Ep, model_name, clusterID, ClusterType, WidgetType, value))
                nValue = value
                
            if nValue == 1:
                UpdateDevice_v2(self, Devices, DeviceUnit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=True)
            else:
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=False)
            continue

        excluded_widget_types = {
            "ThermoModeEHZBRTS", "HeatingSwitch", "HeatingStatus", "ThermoMode_2", "ThermoMode_3", "ThermoSetpoint", 
            "ThermoOnOff", "Motionac01"
        }

        allowed_conditions = {
            (ClusterType in ("IAS_ACE", "Door", "Switch", "SwitchButton", "AqaraOppleMiddle", "Ikea_Round_5b", "Ikea_Round_OnOff", 
                             "Vibration", "OrviboRemoteSquare", "Button_3", "LumiLock") and WidgetType not in excluded_widget_types),
            (ClusterType == WidgetType == "DoorLock"),
            (ClusterType == WidgetType == "Alarm"),
            (ClusterType == "Alarm" and WidgetType == "Tamper"),
            (ClusterType == "DoorLock" and WidgetType == "Vibration"),
            (ClusterType == "FanControl" and WidgetType == "FanControl"),
            ("ThermoMode" in ClusterType and WidgetType == "ACMode_2"),
            ("ThermoMode" in ClusterType and WidgetType == "ACSwing" and Attribute_ == "fd00"),
            ("ThermoMode" in ClusterType and WidgetType == "ThermoMode_7" and Attribute_ == "001c"),
            (WidgetType == "KF204Switch" and ClusterType in ("Switch", "Door")),
            (WidgetType == "Valve" and Attribute_ == "0014"),
            ("ThermoMode" in ClusterType and WidgetType == "ThermoOnOff"),
            ("Heiman" in ClusterType and WidgetType == "HeimanSceneSwitch")
        }

        if any(allowed_condition for allowed_condition in allowed_conditions):

            # Plug, Door, Switch, Button ...
            # We reach this point because ClusterType is Door or Switch. It means that Cluster 0x0006 or 0x0500
            # So we might also have to manage case where we receive a On or Off for a LvlControl WidgetType like a dimming Bulb.
            self.log.logging( "Widget", "Debug", "------> Generic Widget for %s ClusterType: %s WidgetType: %s Value: %s" % (
                NWKID, ClusterType, WidgetType, value), NWKID, )

            if ClusterType == "Switch" and WidgetType == "LvlControl":
                # Called with ClusterID: 0x0006 but we have to update a Dimmer, so we need to keep the level
                nValue = prev_nValue
                sValue = prev_sValue
                if switchType in (13, 16):
                    # Correct for Blinds where we have to display %
                    if value == "00":
                        nValue, sValue = 0, "0"
                    elif value == "01" and sValue == "100":
                        nValue, sValue = 1, "100"
                    else:
                        nValue = 2
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif ClusterType == "Switch" and WidgetType == "Alarm":
                pass
            
            elif ClusterType == "Door" and WidgetType in ( "Smoke", "DoorSensor"):
                nValue = int(value)
                if nValue == 0:
                    sValue = "Off"
                else:
                    sValue = "On"
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "DSwitch":
                # double switch avec EP different
                _value = int(value)
                if _value == 1 or _value == 0:
                    if Ep == "01":
                        nValue = 1
                        sValue = "10"
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

                    elif Ep == "02":
                        nValue = 2
                        sValue = "20"
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

                    elif Ep == "03":
                        nValue = 3
                        sValue = "30"
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif (WidgetType == "TuyaSirenHumi" and Attribute_ != "0172") or (WidgetType == "TuyaSirenTemp" and Attribute_ != "0171") or (WidgetType == "TuyaSiren" and Attribute_ != "0168"):
                return

            elif WidgetType == "ThermoOnOff" and Attribute_ != "6501":
                nValue = value
                if nValue == 0:
                    sValue = "Off"
                else:
                    sValue = "On"
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=False)

            elif WidgetType == "DButton":
                # double bouttons avec EP different lumi.sensor_86sw2
                _value = int(value)
                if _value == 1:
                    if Ep == "01":
                        nValue = 1
                        sValue = "10"
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

                    elif Ep == "02":
                        nValue = 2
                        sValue = "20"
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

                    elif Ep == "03":
                        nValue = 3
                        sValue = "30"
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == "DButton_3":
                # double bouttons avec EP different lumi.sensor_86sw2
                _value = int(value)
                data = "00"
                state = "00"
                if Ep == "01":
                    if _value == 1:
                        state = "10"
                        data = "01"

                    elif _value == 2:
                        state = "20"
                        data = "02"

                    elif _value == 3:
                        state = "30"
                        data = "03"

                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif Ep == "02":
                    if _value == 1:
                        state = "40"
                        data = "04"

                    elif _value == 2:
                        state = "50"
                        data = "05"

                    elif _value == 3:
                        state = "60"
                        data = "06"

                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif Ep == "03":
                    if _value == 1:
                        state = "70"
                        data = "07"

                    elif _value == 2:
                        state = "80"
                        data = "08"

                    elif _value == 3:
                        state = "90"
                        data = "09"

                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == "LvlControl" or WidgetType in ( "ColorControlRGB", "ColorControlWW", "ColorControlRGBWW", "ColorControlFull", "ColorControl", ):

                if switchType in (13, 14, 15, 16):
                    # Required Numeric value
                    if value == "00":
                        UpdateDevice_v2(self, Devices, DeviceUnit, 0, "0", BatteryLevel, SignalLevel)

                    else:
                        # We are in the case of a Shutter/Blind inverse. If we receieve a Read Attribute telling it is On, great
                        # We only update if the shutter was off before, otherwise we will keep its Level.
                        if prev_nValue == 0 and prev_sValue == "Off":
                            UpdateDevice_v2(self, Devices, DeviceUnit, 1, "100", BatteryLevel, SignalLevel)
                else:
                    # Required Off and On
                    if value == "00":
                        UpdateDevice_v2(self, Devices, DeviceUnit, 0, "Off", BatteryLevel, SignalLevel)

                    else:
                        if prev_sValue == "Off":
                            # We do update only if this is a On/off
                            UpdateDevice_v2(self, Devices, DeviceUnit, 1, "On", BatteryLevel, SignalLevel)

            elif WidgetType == "VenetianInverted" and model_name in ( "PR412", "CPR412", "CPR412-E") and clusterID == "0006":
                self.log.logging( "Widget", "Debug", "--++->  %s/%s ClusterType: %s Updating %s Value: %s" % (NWKID, Ep, ClusterType, WidgetType, value), NWKID, )
                # nValue will depends if we are on % or not
                if value == '01':
                    nValue = 0
                    sValue = "0"

                elif value == '00':
                    nValue = 1
                    sValue = "100"

                elif value == 'f0':
                    nValue = 17
                    sValue = "0"

                self.log.logging("Widget", "Debug", "------>  %s %s/%s Value: %s:%s" % (WidgetType, NWKID, Ep, nValue, sValue), NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType in ("VenetianInverted", "Venetian", "WindowCovering", "VanneInverted", "Vanne", "Curtain", "CurtainInverted"):
                _value = int(value, 16)
                self.log.logging( "Widget", "Debug", "------>  %s/%s ClusterType: %s Updating %s Value: %s" % (NWKID, Ep, ClusterType, WidgetType, _value), NWKID, )
                if WidgetType in ("VenetianInverted", "VanneInverted"):
                    _value = 100 - _value
                    self.log.logging("Widget", "Debug", "------>  Patching %s/%s Value: %s" % (NWKID, Ep, _value), NWKID)
                # nValue will depends if we are on % or not
                if _value == 0:
                    nValue = 0
                elif _value == 100:
                    nValue = 1
                else:
                    nValue = 17 if switchType in (4, 15) else 2
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(_value), BatteryLevel, SignalLevel)

            elif (
                (
                    (ClusterType == "FanControl" and WidgetType == "FanControl") 
                    or ("ThermoMode" in ClusterType and WidgetType == "ACSwing" and Attribute_ == "fd00")
                )
                and model_name in ("AC211", "AC221", "CAC221")
                and "Ep" in self.ListOfDevices[NWKID]
                and WidgetEp in self.ListOfDevices[NWKID]["Ep"]
                and "0201" in self.ListOfDevices[NWKID]["Ep"][WidgetEp]
                and "001c" in self.ListOfDevices[NWKID]["Ep"][WidgetEp]["0201"]
                and self.ListOfDevices[NWKID]["Ep"][WidgetEp]["0201"]["001c"] == 0x00
            ):
                # Thermo mode is Off, let's switch off Wing and Fan
                self.log.logging("Widget", "Debug", "------> Switch off as System Mode is Off")
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, "00", BatteryLevel, SignalLevel)

            elif WidgetType in SWITCH_SELECTORS and value in SWITCH_SELECTORS[WidgetType]:
                self.log.logging("Widget", "Debug", "------> Auto Update %s" % str(SWITCH_SELECTORS[WidgetType][value]))
                if len(SWITCH_SELECTORS[WidgetType][value]) == 2:
                    nValue, sValue = SWITCH_SELECTORS[WidgetType][value]
                    _ForceUpdate = SWITCH_SELECTORS[WidgetType]["ForceUpdate"]
                    self.log.logging( "Widget", "Debug", "------> Switch update WidgetType: %s with %s" % (
                        WidgetType, str(SWITCH_SELECTORS[WidgetType])), NWKID, )
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=_ForceUpdate)
                else:
                    self.log.logging( "Widget", "Error", "------>  len(SWITCH_SELECTORS[ %s ][ %s ]) == %s" % (
                        WidgetType, value, len(SWITCH_SELECTORS[WidgetType])), NWKID, )

        if "WindowCovering" in ClusterType:  # 0x0102
            if WidgetType in ("VenetianInverted", "Venetian", "Vanne", "VanneInverted", "WindowCovering", "Curtain", "CurtainInverted", "Blind"):
                _value = int(value, 16)
                self.log.logging(
                    "Widget",
                    "Debug",
                    "------>  %s/%s ClusterType: %s Updating %s Value: %s" % (NWKID, Ep, ClusterType, WidgetType, _value),
                    NWKID,
                )
                if WidgetType in ("VenetianInverted", "VanneInverted", "CurtainInverted"):
                    _value = 100 - _value
                    self.log.logging("Widget", "Debug", "------>  Patching %s/%s Value: %s" % (NWKID, Ep, _value), NWKID)
                # nValue will depends if we are on % or not
                if _value == 0:
                    nValue = 0
                elif _value == 100:
                    nValue = 1
                else:
                    nValue = 17 if switchType in (4, 15) else 2
                self.log.logging("Widget", "Debug", "------>  %s %s/%s Value: %s:%s" % (WidgetType, NWKID, Ep, nValue, _value), NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(_value), BatteryLevel, SignalLevel)

        if "LvlControl" in ClusterType:  # LvlControl ( 0x0008)
            if WidgetType == "LvlControl" or ( WidgetType in ( "BSO-Volet", "Blind", ) ):

                self.log.logging("Widget", "Debug", "------> LvlControl analogValue: -> %s" % value, NWKID)
                normalized_value = normalized_lvl_value(self, Devices, device_id_ieee, DeviceUnit, value)
                self.log.logging("Widget", "Debug", "------> LvlControl new sValue: -> %s old nValue/sValue %s:%s" % (
                    normalized_value, prev_nValue, prev_sValue), NWKID)

                # In case we reach 0% or 100%, we shouldn't switch Off or On, except in the case of Shutter/Blind
                if normalized_value == 0 or normalized_value == 100:
                    nValue = 0 if normalized_value == 0 else 1
                    if switchType:
                        self.log.logging("Widget", "Debug", "------> LvlControl UpdateDevice: -> %s/%s SwitchType: %s" % (
                            nValue, normalized_value, switchType), NWKID)
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(normalized_value), BatteryLevel, SignalLevel)
                    else:
                        if prev_nValue == 0 and (prev_sValue == "Off" or prev_sValue == str(normalized_value)):
                            pass
                        else:
                            self.log.logging("Widget", "Debug", "------> LvlControl UpdateDevice: -> %s/%s" % (nValue, normalized_value), NWKID)
                            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(normalized_value), BatteryLevel, SignalLevel)
                else:
                    if prev_nValue == 0 and (prev_sValue == "Off" or prev_sValue == str(normalized_value)):
                        pass
                    elif switchType in (13, 14, 15, 16):
                        self.log.logging("Widget", "Debug", "------> LvlControl UpdateDevice: -> %s/%s SwitchType: %s" % (
                            2, normalized_value, switchType), NWKID)
                        UpdateDevice_v2(self, Devices, DeviceUnit, 2, str(normalized_value), BatteryLevel, SignalLevel)
                    else:
                        # Just update the Level if Needed
                        self.log.logging("Widget", "Debug", "------> LvlControl UpdateDevice: -> %s/%s SwitchType: %s" % (
                            prev_nValue, normalized_value, switchType), NWKID)
                        UpdateDevice_v2(self, Devices, DeviceUnit, prev_nValue, str(normalized_value), BatteryLevel, SignalLevel)




            elif WidgetType in ( "ColorControlRGB", "ColorControlWW", "ColorControlRGBWW", "ColorControlFull", "ColorControl", ):
                if prev_nValue != 0 or prev_sValue != "Off":
                    nValue, sValue = getDimmerLevelOfColor(self, value)
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(sValue), BatteryLevel, SignalLevel, Color_)

            elif WidgetType == "LegrandSelector":
                self.log.logging("Widget", "Debug", "------> LegrandSelector : Value -> %s" % value, NWKID)
                if value == "00":
                    nValue = 0
                    sValue = "00"  # Off
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                elif value == "01":
                    nValue = 1
                    sValue = "10"  # On
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                elif value == "moveup":
                    nValue = 2
                    sValue = "20"  # Move Up
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                elif value == "movedown":
                    nValue = 3
                    sValue = "30"  # Move Down
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                elif value == "stop":
                    nValue = 4
                    sValue = "40"  # Stop
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                else:
                    self.log.logging("Widget", "Error", "------>  %s LegrandSelector Unknown value %s" % (NWKID, value))
                    
            elif WidgetType == "LegrandSleepWakeupSelector":
                self.log.logging("Widget", "Debug", "------> LegrandSleepWakeupSelector : Value -> %s" % value, NWKID)
                if value == "00":
                    nValue = 1
                    sValue = "10"  # sleep
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                elif value == "01":
                    nValue = 2
                    sValue = "20"  # wakeup
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                else:
                    self.log.logging("Widget", "Error", "------>  %s LegrandSleepWakeupSelector Unknown value %s" % (NWKID, value))

            elif WidgetType == "Generic_5_buttons":
                self.log.logging("Widget", "Debug", "------> Generic 5 buttons : Value -> %s" % value, NWKID)
                nvalue = 0
                state = "00"
                if value == "00":
                    nvalue = 0
                    sValue = "00"

                elif value == "01":
                    nvalue = 1
                    sValue = "10"

                elif value == "02":
                    nvalue = 2
                    sValue = "20"

                elif value == "03":
                    nvalue = 3
                    sValue = "30"

                elif value == "04":
                    nvalue = 4
                    sValue = "40"
                else:
                    return

                UpdateDevice_v2(self, Devices, DeviceUnit, nvalue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == "GenericLvlControl":
                # 1,10: Off
                # 2,20: On
                # 3,30: Move Up
                # 4,40: Move Down
                # 5,50: Stop
                self.log.logging("Widget", "Debug", "------> GenericLvlControl : Value -> %s" % value, NWKID)
                if value == "off":
                    nvalue = 1
                    sValue = "10"  # Off

                elif value == "on":
                    nvalue = 2
                    sValue = "20"  # On

                elif value == "moveup":
                    nvalue = 3
                    sValue = "30"  # Move Up

                elif value == "movedown":
                    nvalue = 4
                    sValue = "40"  # Move Down

                elif value == "stop":
                    nvalue = 5
                    sValue = "50"  # Stop
                else:
                    return

                UpdateDevice_v2(self, Devices, DeviceUnit, nvalue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == "HueSmartButton":
                self.log.logging("Widget", "Debug", "------> HueSmartButton : Value -> %s" % value, NWKID)
                if value == "toggle":
                    nvalue = 1
                    sValue = "10"  # toggle
                elif value == "move":
                    nvalue = 2
                    sValue = "20"  # Move
                else:
                    return
                UpdateDevice_v2(self, Devices, DeviceUnit, nvalue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == "INNR_RC110_SCENE":
                self.log.logging("Widget", "Debug", "------>  Updating INNR_RC110_SCENE (LvlControl) Value: %s" % value, NWKID)
                if value == "Off":
                    nValue = 0

                elif value == "On":
                    nValue = 1

                elif value == "clickup":
                    nValue = 2

                elif value == "clickdown":
                    nValue = 3

                elif value == "moveup":
                    nValue = 4

                elif value == "movedown":
                    nValue = 5

                elif value == "stop":
                    nValue = 6

                elif value == "scene1":
                    nValue = 7

                elif value == "scene2":
                    nValue = 8

                elif value == "scene3":
                    nValue = 9

                elif value == "scene4":
                    nValue = 10

                elif value == "scene5":
                    nValue = 11

                elif value == "scene6":
                    nValue = 12
                else:
                    return

                sValue = "%s" % (10 * nValue)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "INNR_RC110_LIGHT":
                self.log.logging("Widget", "Debug", "------>  Updating INNR_RC110_LIGHT (LvlControl) Value: %s" % value, NWKID)
                if value == "00":
                    nValue = 0

                elif value == "01":
                    nValue = 1

                elif value == "clickup":
                    nValue = 2

                elif value == "clickdown":
                    nValue = 3

                elif value == "moveup":
                    nValue = 4

                elif value == "movedown":
                    nValue = 5

                elif value == "stop":
                    nValue = 6
                else:
                    return

                sValue = "%s" % (10 * nValue)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "TINT_REMOTE_WHITE":
                nValue = int(value)
                sValue = "%s" % (10 * nValue)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

        if ClusterType in ( "ColorControlRGB", "ColorControlWW", "ColorControlRGBWW", "ColorControlFull", "ColorControl", ) and ClusterType == WidgetType:
            # We just manage the update of the Dimmer (Control Level)
            nValue, sValue = getDimmerLevelOfColor(self, value)
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(sValue), BatteryLevel, SignalLevel, Color_)

        if "Orientation" in ClusterType and WidgetType == "Orientation":
            # Xiaomi Vibration
            # value is a str containing all Orientation information to be updated on Text Widget
            nValue = 0
            sValue = value
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

        if "Strenght" in ClusterType and WidgetType == "Strenght":
            # value is a str containing all Orientation information to be updated on Text Widget
            nValue = 0
            sValue = value
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

        if "Distance" in ClusterType and WidgetType == "Distance":
            # value is a str containing all Distance information in cm
            nValue = 0
            sValue = value
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

        if "Lux" in ClusterType and WidgetType == "Lux":
            nValue = int(value)
            sValue = value
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=False)

        # Check if this Device belongs to a Group. In that case update group
        CheckUpdateGroup(self, NWKID, Ep, clusterID)


def CheckUpdateGroup(self, NwkId, Ep, ClusterId):

    if ClusterId not in ("0006", "0008", "0102"):
        return

    if self.groupmgt:
        self.groupmgt.checkAndTriggerIfMajGroupNeeded(NwkId, Ep, ClusterId)


def get_dimmer_level_of_color(self, value):
    nValue = 1
    analogValue = value if isinstance(value, int) else int(value, 16)

    if analogValue >= 255:
        sValue = 100
    else:
        sValue = min(round((analogValue / 255) * 100), 100)
        sValue = max(sValue, 1)

    return nValue, sValue

def check_erratic_value(self, NwkId, value_type, value, expected_min, expected_max):
    """
    Check if the value is in the range or not. If out of range and disableTrackingValue not set, will check for 5 consecutive errors to log as an error.
    Return False if the value is in the range
    Return True if the value is out of range
    """

    _attribute = "Erratic_" + value_type
    tracking_disable = self.ListOfDevices.get(NwkId, {}).get("Param", {}).get("disableTrackingEraticValue", False)

    valid_value = expected_min < value < expected_max

    if valid_value:
        self.ListOfDevices[NwkId].pop(_attribute, None)
        return False

    elif tracking_disable:
        return True

    # We have an erratic value and we have to track. Let's try to handle some erratic values.
    if _attribute not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId][_attribute] = {"ConsecutiveErraticValue": 1}
    else:
        self.ListOfDevices[NwkId][_attribute]["ConsecutiveErraticValue"] += 1

    consecutive_erratic_value = self.ListOfDevices[NwkId][_attribute]["ConsecutiveErraticValue"]

    if consecutive_erratic_value > 5:
        self.log.logging("Widget", "Error", "Aberrant %s: %s (below %s or above %s) for device: %s" % (
            value_type, value, expected_min, expected_max, NwkId), NwkId)
        self.ListOfDevices[NwkId].pop(_attribute, None)
        return True

    self.log.logging("Widget", "Debug", "Aberrant %s: %s (below %s or above %s) for device: %s [%s]" % (
        value_type, value, expected_min, expected_max, NwkId, consecutive_erratic_value), NwkId)
    return True

def check_set_meter_widget( self, Devices, DeviceId, Unit, mode):
    # Mode = 0 - From device (default)
    # Mode = 1 - Computed

    sMode = "%s" %mode

    Options = {'EnergyMeterMode': '0'}
    # Do we have the Energy Mode calculation already set ?
    if "EnergyMeterMode" in Devices[Unit].Options:
        # Yes, let's retreive it
        Options = Devices[Unit].Options

    if Options["EnergyMeterMode"] != sMode:
        oldnValue, oldsValue = domo_read_nValue_sValue(self, Devices, DeviceId, Unit)

        Options = { "EnergyMeterMode": sMode }
        domo_update_api(self, Devices, DeviceId, Unit, oldnValue, oldsValue, Options=Options ,)



def retrieve_data_from_current(self, Devices, DeviceID, Unit, _format):
    """
    Retrieve data from current.

    Args:
        Devices: The devices.
        DeviceID: The device ID.
        Unit: The unit.
        _format: The format.

    Returns:
        List[str]: The retrieved data from current.

    Examples:
        retrieve_data_from_current(self, "Device1", 123, 1, "A;B;C")
        ['0', '0', '0']
    """
    _, current_svalue = domo_read_nValue_sValue(self, Devices, DeviceID, Unit)

    if current_svalue == "":
        current_svalue = "0"

    # Calculate number of expected parameters from format_list directly
    # Create a zero_padded_list
    format_list = _format.split(";")
    nb_parameters, zero_padded_list = len(format_list), ["0"] * len(format_list)

    current_list_values = current_svalue.split(";")
    result_list = current_list_values + zero_padded_list[len(current_list_values):] if len(current_list_values) < nb_parameters else ["0"] * nb_parameters

    self.log.logging("Widget", "Log", f"retrieve_data_from_current - svalue: {current_svalue} Nb Param: {nb_parameters} returning {result_list}")

    return result_list


def normalized_lvl_value( self, Devices, DeviceID, DeviceUnit, value ):
    
    # Normalize sValue vs. analog value coomming from a ReadAttribute
    analogValue = value if isinstance( value, int) else int(value, 16)

    if analogValue >= 255:
        normalized_value = 255

    normalized_value = round(((analogValue * 100) / 255))
    normalized_value = min(normalized_value, 100)
    if normalized_value == 0 and analogValue > 0:
        normalized_value = 1

    # Looks like in the case of the Profalux shutter, we never get 0 or 100
    _switchtype, _, _ = domo_read_SwitchType_SubType_Type(self, Devices, DeviceID, DeviceUnit)
    if _switchtype in (13, 14, 15, 16):
        if normalized_value == 1 and analogValue == 1:
            normalized_value = 0
        if normalized_value == 99 and analogValue == 254:
            normalized_value = 100

    return normalized_value


def getDimmerLevelOfColor(self, value):
    nValue = 1
    analogValue = value if isinstance(value, int) else int(value, 16)

    if analogValue >= 255:
        sValue = 100
    else:
        sValue = min(round((analogValue / 255) * 100), 100)
        sValue = max(sValue, 1) if sValue > 0 else 0

    return nValue, sValue

def check_and_update_db_status( self, NWKID):
    if ( 
        "Status" in self.ListOfDevices[NWKID] 
        and self.ListOfDevices[NWKID]["Status"] == "erasePDM" 
        and "autoRestore" in self.pluginconf.pluginConf 
        and self.pluginconf.pluginConf["autoRestore"]
    ):
        # Most likely we have request a coordinator re-initialisation and the latest backup has been put in place
        # simply put the device back
        self.ListOfDevices[NWKID]["Status"] = "inDB"

def is_PowerNegative_widget( ClusterTypeList):
    return any( _widget_type == "ProdMeter" for _, _, _widget_type in ClusterTypeList )


def calculate_humidity_status(humidity_value):
    if humidity_value < 40:
        return 2
    elif 40 <= humidity_value < 70:
        return 1
    else:
        return 3
    
def calculate_baro_forecast(baroValue):

    if baroValue < 1000:
        return 4  # RAIN
    elif baroValue < 1020:
        return 3  # CLOUDY
    elif baroValue < 1030:
        return 2  # PARTLY CLOUDY
    else:
        return 1  # SUNNY


def str_round(value, n):
    return "{:.{n}f}".format(value, n=int(n))