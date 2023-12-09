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
                                           domo_read_Device_Idx,
                                           domo_read_nValue_sValue,
                                           domo_read_Options,
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

WIDGET_TO_BYPASS_EP_MATCH = ("XCube", "Aqara", "DSwitch", "DButton", "DButton_3")


def is_time_to_domo_update(self, NwkId, Ep):

    if self.CommiSSionning and NwkId not in self.ListOfDevices:
        return False

    if NwkId not in self.ListOfDevices:
        self.log.logging("Widget", "Error", "MajDomoDevice - %s not known" % NwkId, NwkId)
        zigpy_plugin_sanity_check(self, NwkId)
        return False

    if ( "Health" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Health"] == "Disabled" ):
        # If the device has been disabled, just drop the message
        self.log.logging("Widget", "Debug", "MajDomoDevice - disabled device: %s/%s droping message " % (NwkId, Ep), NwkId)
        return False

    if Ep not in self.ListOfDevices[NwkId]["Ep"]:
        self.log.logging("Widget", "Error", "MajDomoDevice - %s/%s not known Endpoint" % (NwkId, Ep), NwkId)
        return False

    if ( 
        "Status" in self.ListOfDevices[NwkId] 
        and self.ListOfDevices[NwkId]["Status"] == "erasePDM" 
        and "autoRestore" in self.pluginconf.pluginConf 
        and self.pluginconf.pluginConf["autoRestore"]
        ):
        # Most likely we have request a coordinator re-initialisation and the latest backup has been put in place
        # simply put the device back
        self.ListOfDevices[NwkId]["Status"] = "inDB"
        
    elif "Status" in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]["Status"] != "inDB":
        self.log.logging(
            "Widget",
            "Log",
            "MajDomoDevice NwkId: %s status: %s not inDB request IEEE for possible reconnection" % (NwkId, self.ListOfDevices[NwkId]["Status"]),
            NwkId,
        )
        if not zigpy_plugin_sanity_check(self, NwkId):
            # Broadcast to 0xfffd: macRxOnWhenIdle = TRUE
            zdp_IEEE_address_request(self, 'fffd', NwkId, u8RequestType="00", u8StartIndex="00")
        return False


    if "IEEE" not in self.ListOfDevices[NwkId]:
        self.log.logging("Widget", "Error", "MajDomoDevice - no IEEE for %s" % NwkId, NwkId)
        return False
    
    return True


def MajDomoDevice(self, Devices, NwkId, Ep, ClusterId, value, Attribute_="", Color_=""):
    """
    MajDomoDevice
    Update domoticz device accordingly to Type found in EP and value/Color provided
    """

    if not is_time_to_domo_update(self, NwkId, Ep):
        return

    model_name = self.ListOfDevices.get(NwkId, {}).get("Model", "")
    device_id_ieee = self.ListOfDevices.get(NwkId, {}).get("IEEE")
    
    self.log.logging( "Widget", "Debug", "MajDomoDevice NwkId: %s Ep: %s ClusterId: %s Value: %s ValueType: %s Attribute: %s Color: %s ModelName: %s" % (
        NwkId, Ep, ClusterId, value, type(value), Attribute_, Color_, model_name), NwkId, )

    # Get the CluserType ( Action type) from Cluster Id
    ClusterType = TypeFromCluster(self, ClusterId)
    self.log.logging("Widget", "Debug", "------> ClusterType = " + str(ClusterType), NwkId)

    ClusterTypeList = RetreiveWidgetTypeList(self, Devices, NwkId)
    self.log.logging("Widget", "Debug", "------> ClusterTypeList = " + str(ClusterTypeList), NwkId)
    
    if len(ClusterTypeList) == 0:
        # We don't have any widgets associated to the NwkId
        return

    # Look for each entry in ClusterTypeList
    for WidgetEp, WidgetId, WidgetType in ClusterTypeList:
        _domo_maj_one_cluster_type_entry( self, Devices, NwkId, Ep, device_id_ieee, model_name, ClusterType, ClusterTypeList, ClusterId, value, Attribute_, Color_, WidgetEp, WidgetId, WidgetType )

    
def _domo_maj_one_cluster_type_entry( self, Devices, NwkId, Ep, device_id_ieee, model_name, ClusterType, ClusterTypeList, ClusterId, value, Attribute_, Color_, WidgetEp, WidgetId, WidgetType ):

        # device_unit is the Device unit
        # WidgetEp is the Endpoint to which the widget is linked to
        # WidgetId is the Device ID
        # WidgetType is the Widget Type at creation
        # ClusterType is the Type based on clusters
        # ClusterType: This the Cluster action extracted for the particular Endpoint based on Clusters.
        # WidgetType : This is the Type of Widget defined at Widget Creation
        # value      : this is value comming mostelikely from readCluster. Be carreful depending on the cluster, the value is String or Int
        # Attribute_ : If used This is the Attribute from readCluster. Will help to route to the right action
        # Color_     : If used This is the color value to be set

        self.log.logging( "Widget", "Debug", "_domo_maj_one_cluster_type_entry WidgetEp: %s, WidgetId: %s, WidgetType: %s" % (
            WidgetEp, WidgetId, WidgetType), NwkId, )
        
        if WidgetEp == "00":
            # Old fashion / keep it for backward compatibility
            WidgetEp = "01"  # Force to 01

        if WidgetType not in WIDGET_TO_BYPASS_EP_MATCH and WidgetEp != Ep:
            # We need to make sure that we are on the right Endpoint
            self.log.logging( "Widget", "Debug", "------> skiping this WidgetEp as do not match Ep : %s %s" % (WidgetEp, Ep), NwkId,)
            return

        device_unit = retreive_device_unit( self, Devices, NwkId, Ep, device_id_ieee, ClusterId, WidgetId )
        if device_unit is None:
            return
        
        prev_nValue, prev_sValue = domo_read_nValue_sValue(self, Devices, device_id_ieee, device_unit)
        switchType, Subtype, _ = domo_read_SwitchType_SubType_Type(self, Devices, device_id_ieee, device_unit)

        self.log.logging( "Widget", "Debug", "------> ClusterType: %s WidgetEp: %s WidgetId: %s WidgetType: %s Attribute_: %s" % ( 
            ClusterType, WidgetEp, WidgetId, WidgetType, Attribute_), NwkId, )

        SignalLevel, BatteryLevel = RetreiveSignalLvlBattery(self, NwkId)
        self.log.logging("Widget", "Debug", "------> SignalLevel: %s , BatteryLevel: %s" % (SignalLevel, BatteryLevel), NwkId)

        if ClusterType == "Alarm" and WidgetType == "Alarm_ZL" and Attribute_ == "0005":
            # This is Alarm3 for ZLinky Intensity alert
            value, text = value.split("|")
            nValue = int(value)
            UpdateDevice_v2(self, Devices, device_unit, nValue, text, BatteryLevel, SignalLevel)

        if ClusterType == "Alarm" and WidgetType == "Alarm_ZL2" and Attribute_ == "0001":
            # Notification Next Day Color and Peak
            
            tuple_value = value.split("|")
            if len(tuple_value) != 2:
                self.log.logging(
                    "Widget",
                    "Error",
                    "------> Expecting 2 values got %s in Value = %s for NwkId: %s Attribute: %s" % (
                        len(tuple_value), value, NwkId, Attribute_),
                    NwkId,
                )
                return

            value, text = tuple_value
            nValue = int(value)
            UpdateDevice_v2(self, Devices, device_unit, nValue, text, BatteryLevel, SignalLevel)

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
            UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

        if "Ampere" in ClusterType and WidgetType == "Ampere" and Attribute_ == "0508":
            sValue = "%s" % (round(float(value), 2))
            self.log.logging("Widget", "Debug", "------>  Ampere : %s" % sValue, NwkId)
            UpdateDevice_v2(self, Devices, device_unit, 0, str(sValue), BatteryLevel, SignalLevel)

        if "Ampere" in ClusterType and WidgetType == "Ampere3" and Attribute_ in ("0508", "0908", "0a08"):
            # Retreive the previous values
            sValue = "%s;%s;%s" % (0, 0, 0)
            ampere1, ampere2, ampere3 = retrieve_data_from_current(self, Devices, device_id_ieee, device_unit, "0;0;0")
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

            self.log.logging("Widget", "Debug", "------>  Ampere3 : %s from Attribute: %s" % (sValue, Attribute_), NwkId)
            UpdateDevice_v2(self, Devices, device_unit, 0, str(sValue), BatteryLevel, SignalLevel)

        if "PWFactor" == ClusterType and WidgetType == "PowerFactor":
            self.log.logging("Widget", "Debug", "PowerFactor %s WidgetType: %s Value: %s (%s)" % (
                NwkId, WidgetType, value, type(value)), NwkId)

            nValue = round(value, 1)
            sValue = str(nValue)
            UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

        if "Power" in ClusterType:  # Instant Power/Watts
            # Power and Meter usage are triggered only with the Instant Power usage.
            # it is assumed that if there is also summation provided by the device, that
            # such information is stored on the data structuture and here we will retreive it.
            # value is expected as String

            if WidgetType == "Power" and (Attribute_ in ("", "050f") or ClusterId == "000c"):  # kWh
                if (( isinstance( value, (int, float)) and value < 0) or (float(value) < 0) ) and is_PowerNegative_widget( ClusterTypeList):
                    self.log.logging("Widget", "Debug", "------>There is a PowerNegative widget and the value is negative. Skiping here", NwkId)
                    UpdateDevice_v2(self, Devices, device_unit, 0, "0", BatteryLevel, SignalLevel)
                    return

                nValue = round(float(value), 2)
                sValue = value
                self.log.logging("Widget", "Debug", "------>Power  : %s" % sValue, NwkId)
                UpdateDevice_v2(self, Devices, device_unit, nValue, str(sValue), BatteryLevel, SignalLevel)

            if WidgetType == "ProdPower" and Attribute_ == "":
                if value > 0:
                    self.log.logging("Widget", "Debug", "------>the value is Positive. Skiping here", NwkId)
                    UpdateDevice_v2(self, Devices, device_unit, 0, "0", BatteryLevel, SignalLevel)
                    return

                nValue = abs( round(float(value), 2) )
                sValue = abs(value)
                self.log.logging("Widget", "Debug", "------>PowerNegative  : %s" % sValue, NwkId)
                UpdateDevice_v2(self, Devices, device_unit, nValue, str(sValue), BatteryLevel, SignalLevel)

            if WidgetType == "P1Meter" and Attribute_ == "0000":
                self.log.logging("Widget", "Debug", "------>  P1Meter : %s (%s)" % (value, type(value)), NwkId)
                # P1Meter report Instant and Cummulative Power.
                # We need to retreive the Cummulative Power.
                cur_usage1, cur_usage2, cur_return1, cur_return2, cur_cons, cur_prod = retrieve_data_from_current(self, Devices, device_id_ieee, device_unit, "0;0;0;0;0;0")
                usage1 = usage2 = return1 = return2 = cons = prod = 0
                if "0702" in self.ListOfDevices[NwkId]["Ep"][Ep] and "0400" in self.ListOfDevices[NwkId]["Ep"][Ep]["0702"]:
                    cons = round(float(self.ListOfDevices[NwkId]["Ep"][Ep]["0702"]["0400"]), 2)
                usage1 = int(float(value))

                sValue = "%s;%s;%s;%s;%s;%s" % (usage1, usage2, return1, return2, cons, prod)
                self.log.logging("Widget", "Debug", "------>  P1Meter : " + sValue, NwkId)
                UpdateDevice_v2(self, Devices, device_unit, 0, str(sValue), BatteryLevel, SignalLevel)

            if (
                WidgetType == "P1Meter_ZL" 
                and "Model" in self.ListOfDevices[NwkId] 
                and self.ListOfDevices[NwkId]["Model"] in ZLINK_CONF_MODEL and Attribute_ in ( "0100", "0102", "0104", "0106", "0108", "010a")
                ):
 
                if Attribute_ != "050f" and Ep == "01" and Attribute_ not in ("0100", "0102"):
                    # Ep = 01, so we store Base, or HP,HC, or BBRHCJB, BBRHPJB
                    return
                if Attribute_ != "050f" and Ep == "f2" and Attribute_ not in ("0104", "0106"):
                    # Ep = f2, so we store BBRHCJW, BBRHPJW
                    return
                if Attribute_ != "050f" and Ep == "f3" and Attribute_ not in ("0108", "010a"):
                    # Ep == f3, so we store BBRHCJR, BBRHPJR
                    return
                
                tarif_color = get_tarif_color( self, NwkId )

                self.log.logging("ZLinky", "Debug", "------>  P1Meter_ZL : %s Attribute: %s  Color: %s (%s)" % (
                    value, Attribute_, tarif_color, type(value)), NwkId)
                
                # P1Meter report Instant and Cummulative Power.
                # We need to retreive the Cummulative Power.
                cur_usage1, cur_usage2, cur_return1, cur_return2, cur_cons, cur_prod = retrieve_data_from_current(self, Devices, device_id_ieee, device_unit, "0;0;0;0;0;0")
                usage1 = usage2 = return1 = return2 = cons = prod = 0
                self.log.logging("ZLinky", "Debug", "------>  P1Meter_ZL (%s): retreive value: %s;%s;%s;%s;%s;%s" % (Ep, cur_usage1, cur_usage2, cur_return1, cur_return2, cur_cons, cur_prod), NwkId)

                # We are so receiving a usage update
                self.log.logging( "ZLinky", "Debug", "------>  P1Meter_ZL : Trigger by Index Update %s Ep: %s" % (Attribute_, Ep), NwkId, )
                cons = get_instant_power(self, NwkId)
                if Attribute_ in ("0000", "0100", "0104", "0108"):
                    # Usage 1
                    usage1 = int(round(float(value), 0))
                    usage2 = cur_usage2
                    return1 = cur_return1
                    return2 = cur_return2
                    if usage1 == cur_usage1:
                        # Skip update as there is no consumption
                        return

                elif Attribute_ in ("0102", "0106", "010a"):
                    # Usage 2
                    usage1 = cur_usage1
                    usage2 = int(round(float(value), 0))
                    return1 = cur_return1
                    return2 = cur_return2
                    if usage2 == cur_usage2:
                        # Skip update as there is no consumption
                        return

                if tarif_color == "Blue" and Ep != "01" or tarif_color == "White" and Ep != "f2" or tarif_color == "Red" and Ep != "f3":
                    cons = 0.0

                sValue = "%s;%s;%s;%s;%s;%s" % (usage1, usage2, return1, return2, cons, cur_prod)
                self.log.logging("ZLinky", "Debug", "------>  P1Meter_ZL (%s): %s" % (Ep, sValue), NwkId)
                UpdateDevice_v2(self, Devices, device_unit, 0, str(sValue), BatteryLevel, SignalLevel)

        if "Meter" in ClusterType:  # Meter Usage.
            
            if WidgetType == "GazMeter" and Attribute_ == "0000":
                # Gaz Meter 
                sValue = "%s" %value
                UpdateDevice_v2(self, Devices, device_unit, 0, sValue, BatteryLevel, SignalLevel)
                
            elif WidgetType == "Counter" and Attribute_ == "0000":
                sValue = "%s" %int(value)
                UpdateDevice_v2(self, Devices, device_unit, 0, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "ConsoMeter" and Attribute_ == "0000":
                # Consummed Energy
                sValue = "%s" %int(value)
                self.log.logging("Widget", "Debug", "------>ConsoMeter  : %s" % sValue, NwkId)
                UpdateDevice_v2(self, Devices, device_unit, 0, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "ProdMeter" and Attribute_ == "0001":
                # Produced Energy injected
                sValue = "%s" %int(value)
                self.log.logging("Widget", "Debug", "------>ProdMeter  : %s" % sValue, NwkId)
                UpdateDevice_v2(self, Devices, device_unit, 0, sValue, BatteryLevel, SignalLevel)

            # value is string an represent the Instant Usage
            elif (
                "Model" in self.ListOfDevices[ NwkId ] 
                and self.ListOfDevices[ NwkId ]["Model"] in ZLINK_CONF_MODEL
                and WidgetType == "Meter" 
                and ( 
                    Attribute_ == "0000" 
                    or ( Attribute_ in ("0100", "0102") and Ep == "01") 
                    or ( Attribute_ in ("0104", "0106") and Ep == "f2")
                    or ( Attribute_ in ("0108", "010a") and Ep == "f3")
                    )
                ):
                check_set_meter_widget( self, Devices, device_id_ieee, device_unit, 0)    
                instant, _summation = retrieve_data_from_current(self, Devices, device_id_ieee, device_unit, "0;0")
                summation = round(float(zlinky_sum_all_indexes( self, NwkId )), 2)
                self.log.logging("ZLinky", "Debug", "------> Summation for Meter : %s" %summation)
                
                sValue = "%s;%s" % (instant, summation)
                self.log.logging("ZLinky", "Debug", "------>  : " + sValue)
                UpdateDevice_v2(self, Devices, device_unit, 0, sValue, BatteryLevel, SignalLevel)
                
            elif WidgetType == "Meter" and Attribute_ == "050f":
                # We receive Instant Power
                check_set_meter_widget(self, Devices, device_id_ieee, device_unit, 0)
                _instant, summation = retrieve_data_from_current(self, Devices, device_id_ieee, device_unit, "0;0")
                instant = round(float(value), 2)
                sValue = "%s;%s" % (instant, summation)
                self.log.logging("Widget", "Debug", "------>  : " + sValue)
                UpdateDevice_v2(self, Devices, device_unit, 0, sValue, BatteryLevel, SignalLevel)

            elif (WidgetType == "Meter" and Attribute_ == "") or (WidgetType == "Power" and ClusterId == "000c"):  # kWh
                # We receive Instant
                # Let's check if we have Summation in the datastructutre
                summation = 0
                if ( 
                    "0702" in self.ListOfDevices[NwkId]["Ep"][Ep] 
                    and "0000" in self.ListOfDevices[NwkId]["Ep"][Ep]["0702"] 
                    and self.ListOfDevices[NwkId]["Ep"][Ep]["0702"]["0000"] not in ({}, "", "0")
                ): 
                    # summation = int(self.ListOfDevices[NwkId]['Ep'][Ep]['0702']['0000'])
                    summation = self.ListOfDevices[NwkId]["Ep"][Ep]["0702"]["0000"]

                instant = round(float(value), 2)
                # Did we get Summation from Data Structure
                if summation != 0:
                    summation = int(float(summation))
                    sValue = "%s;%s" % (instant, summation)
                    # We got summation from Device, let's check that EnergyMeterMode is
                    # correctly set to 0, if not adjust
                    check_set_meter_widget( self, Devices, device_id_ieee, device_unit, 0)
                else:
                    sValue = "%s;" % (instant)
                    check_set_meter_widget( self, Devices, device_id_ieee, device_unit, 1)
                    # No summation retreive, so we make sure that EnergyMeterMode is
                    # correctly set to 1 (compute), if not adjust

                self.log.logging("Widget", "Debug", "------>  : " + sValue)
                UpdateDevice_v2(self, Devices, device_unit, 0, sValue, BatteryLevel, SignalLevel)

        if "WaterCounter" in ClusterType and WidgetType == "WaterCounter":
            # /json.htm?type=command&param=udevice&idx=IDX&nvalue=0&svalue=INCREMENT
            # INCREMENT = Integer of the increment of the counter. 
            # For Counters the standard counter dividers apply (menu setup - settings - tab counters)
            # will increment the counter value by 1. 
            # To reset an incremental counter, set the svalue to a negative integer equal to the current total of the counter. 
                sValue = "%s" %value 
                self.log.logging("Widget", "Log", "WaterCounter ------>  : %s" %sValue, NwkId)
                UpdateDevice_v2(self, Devices, device_unit, 0, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
  
        if "Voltage" in ClusterType and (WidgetType == "Voltage" and Attribute_ == ""):
            nValue = round(float(value), 2)
            sValue = "%s;%s" % (nValue, nValue)
            self.log.logging("Widget", "Debug", "------>  : " + sValue, NwkId)
            UpdateDevice_v2(self, Devices, device_unit, 0, sValue, BatteryLevel, SignalLevel)

        if "ThermoSetpoint" in ClusterType and (WidgetType == "ThermoSetpoint" and Attribute_ in ("4003", "0012")):
            setpoint = round(float(value), 2)
            # Normalize SetPoint value with 2 digits
            nValue = 0
            sValue = str_round(float(setpoint), 2)  # 2 decimals
            self.log.logging("Widget", "Debug", "------>  Thermostat Setpoint: %s %s" % (0, setpoint), NwkId)
            UpdateDevice_v2(self, Devices, device_unit, 0, sValue, BatteryLevel, SignalLevel)

        if "Analog" in ClusterType:
            if WidgetType == "Voc" and Attribute_ == "":
                sValue = str( value )
                UpdateDevice_v2(self, Devices, device_unit, 0, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "Motionac01" and Ep == "01":  # Motionac01
                if value <= 7:
                    nValue= value + 1
                    sValue = str(nValue * 10)
                    UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
            
            elif WidgetType == "Analog":
                # Analog Value from Analog Input cluster
                UpdateDevice_v2(self, Devices, device_unit, 0, value, BatteryLevel, SignalLevel)

        if ("XCube" in ClusterType) or ("Analog" in ClusterType and model_name in ("lumi.sensor_cube.aqgl01", "lumi.sensor_cube")):  # XCube Aqara or Xcube
            if WidgetType == "Aqara" :
                self.log.logging(
                    "Widget",
                    "Debug",
                    "-------->  XCube Aqara Ep: %s Attribute_: %s Value: %s = " % (Ep, Attribute_, value),
                    NwkId,
                )
                if Ep == "02" and Attribute_ == "":  # Magic Cube Aqara
                    self.log.logging("Widget", "Debug", "---------->  XCube update device with data = " + str(value), NwkId)
                    nValue = int(value)
                    sValue = value
                    UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif Ep == "03":  # Magic Cube Aqara Rotation
                    if Attribute_ == "0055":  # Rotation Angle
                        self.log.logging(
                            "Widget",
                            "Debug",
                            "---------->  XCube update Rotaion Angle with data = " + str(value),
                            NwkId,
                        )
                        # Update Text widget ( unit + 1 )
                        nValue = 0
                        sValue = value
                        UpdateDevice_v2(self, Devices, device_unit + 1, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

                    else:
                        self.log.logging("Widget", "Debug", "---------->  XCube update  with data = " + str(value), NwkId)
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
                            NwkId,
                        )
                        UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == "XCube" and Ep == "02":  # cube xiaomi
                if value == "0000":  # shake
                    state = "10"
                    data = "01"
                    UpdateDevice_v2(self, Devices, device_unit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif value in ("0204", "0200", "0203", "0201", "0202", "0205"):
                    state = "50"
                    data = "05"
                    UpdateDevice_v2(self, Devices, device_unit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif value in ("0103", "0100", "0104", "0101", "0102", "0105"):  # Slide/M%ove
                    state = "20"
                    data = "02"
                    UpdateDevice_v2(self, Devices, device_unit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif value == "0003":  # Free Fall
                    state = "70"
                    data = "07"
                    UpdateDevice_v2(self, Devices, device_unit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif "0004" <= value <= "0059":  # 90°
                    state = "30"
                    data = "03"
                    UpdateDevice_v2(self, Devices, device_unit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif value >= "0060":  # 180°
                    state = "90"
                    data = "09"
                    UpdateDevice_v2(self, Devices, device_unit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

        if "Valve" in ClusterType and (WidgetType == "Valve" and Attribute_ in ("026d", "4001", "0008")):
            nValue = round(value, 1)
            sValue = str(nValue)
            UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

        if "ThermoMode" in ClusterType:  # Thermostat Mode
            self.log.logging("Widget", "Debug", "ThermoMode %s WidgetType: %s Value: %s (%s) Attribute_: %s" % ( 
                NwkId, WidgetType, value, type(value), Attribute_), NwkId)

            if WidgetType == "ThermoModeEHZBRTS" and Attribute_ == "e010":  # Thermostat Wiser
                # value is str
                self.log.logging("Widget", "Debug", "------>  EHZBRTS Schneider Thermostat Mode %s" % value, NwkId)
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
                    UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "HeatingSwitch" and Attribute_ == "001c":
                self.log.logging("Widget", "Debug", "------>  HeatingSwitch %s" % value, NwkId)
                if value == 0:
                    UpdateDevice_v2(self, Devices, device_unit, 0, "Off", BatteryLevel, SignalLevel)
                elif value == 4:
                    UpdateDevice_v2(self, Devices, device_unit, 1, "On", BatteryLevel, SignalLevel)

            elif WidgetType == "HeatingStatus" and Attribute_ == "0124":
                self.log.logging("Widget", "Debug", "------>  HeatingStatus %s" % value, NwkId)
                if value == 0:
                    UpdateDevice_v2(self, Devices, device_unit, 0, "Not Heating", BatteryLevel, SignalLevel)
                elif value == 1:
                    UpdateDevice_v2(self, Devices, device_unit, 1, "Heating", BatteryLevel, SignalLevel)

            elif WidgetType == "ThermoOnOff" and Attribute_ == "6501":
                self.log.logging("Widget", "Debug", "------>  Thermo On/Off %s" % value, NwkId)
                if value == 0:
                    UpdateDevice_v2(self, Devices, device_unit, 0, "Off", BatteryLevel, SignalLevel)
                elif value == 1:
                    UpdateDevice_v2(self, Devices, device_unit, 1, "On", BatteryLevel, SignalLevel)

            elif WidgetType == "HACTMODE" and Attribute_ == "e011":   # Wiser specific Fil Pilote
                # value is str
                self.log.logging("Widget", "Debug", "------>  ThermoMode HACTMODE: %s" % (value), NwkId)
                THERMOSTAT_MODE = {0: "10", 1: "20"}  # Conventional heater  # fip enabled heater
                _mode = ((int(value, 16) - 0x80) >> 1) & 1

                if _mode in THERMOSTAT_MODE:
                    sValue = THERMOSTAT_MODE[_mode]
                    nValue = _mode + 1
                    UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "LegranCableMode" and ClusterId == "fc01":    # Legrand
                # value is str
                self.log.logging("Widget", "Debug", "------>  Legrand Mode: %s" % (value), NwkId)
                THERMOSTAT_MODE = {0x0100: "10", 0x0200: "20"}    # Conventional heater  # fip enabled heater
                _mode = int(value, 16)

                if _mode not in THERMOSTAT_MODE:
                    return

                sValue = THERMOSTAT_MODE[_mode]
                nValue = int(sValue) // 10
                UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "FIP" and Attribute_ in ("0000", "e020"):     # Wiser specific Fil Pilote
                # value is str
                self.log.logging("Widget", "Debug", "------>  ThermoMode FIP: %s" % (value), NwkId)
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
                    if "0201" in self.ListOfDevices[NwkId]["Ep"][Ep]:
                        if "e011" in self.ListOfDevices[NwkId]["Ep"][Ep]["0201"]:
                            if self.ListOfDevices[NwkId]["Ep"][Ep]["0201"]["e011"] != {} and self.ListOfDevices[NwkId]["Ep"][Ep]["0201"]["e011"] != "":
                                _value_mode_hact = self.ListOfDevices[NwkId]["Ep"][Ep]["0201"]["e011"]
                                _mode_hact = ((int(_value_mode_hact, 16) - 0x80)) & 1
                                if _mode_hact == 0:
                                    self.log.logging("Widget", "Debug", "------>  Disable FIP widget: %s" % (value), NwkId)
                                    nValue = 0
                    UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

                elif ClusterId == "fc40":  # Legrand FIP
                    UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "ThermoMode_3" and Attribute_ == "001c":
                #   0x00: Off
                #   0x01: Confort
                #   0x03: No-Freeze
                if "ThermoMode_3" not in SWITCH_SELECTORS:
                    return
                if int(value) == 0x00:
                    # Off # 00
                    nValue = 0
                    sValue = "Off"
                elif int(value) == 0x01:
                    # Confort # 10
                    nValue = 1
                    sValue = "10"
                elif int(value) == 0x03:
                    # No-Freeze # 20
                    nValue = 2
                    sValue = "20"
                else:
                    # Unknow
                    self.log.logging("Widget", "Error", "MajDomoDevice - Unknown value for %s/%s, ClusterId: %s, value: %s, Attribute_=%s," % (NwkId, Ep, ClusterId, value, Attribute_), NwkId)
                    return
                self.log.logging("Widget", "Log", "------>  Thermostat Mode 3 %s %s:%s" % (value, nValue, sValue), NwkId)
                UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "ThermoMode_2" and Attribute_ == "001c":
                # Use by Tuya TRV
                if "ThermoMode_2" not in SWITCH_SELECTORS:
                    return
                if value not in SWITCH_SELECTORS["ThermoMode_2"]:
                    self.log.logging("Widget", "Error", "Unknown TermoMode2 value: %s" % value)
                    return
                nValue = SWITCH_SELECTORS["ThermoMode_2"][value][0]
                sValue = SWITCH_SELECTORS["ThermoMode_2"][value][1]
                self.log.logging("Widget", "Debug", "------>  Thermostat Mode 2 %s %s:%s" % (value, nValue, sValue), NwkId)
                UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "ThermoMode_4" and Attribute_ == "001c":
                # Use by Tuya TRV
                nValue = value
                sValue = '%02d' %( nValue * 10)
                self.log.logging("Widget", "Debug", "------>  Thermostat Mode 4 %s %s:%s" % (value, nValue, sValue), NwkId)
                UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType in ("ThermoMode_5", "ThermoMode_6") and Attribute_ == "001c":
                # Use by Tuya TRV
                nValue = value
                sValue = '%02d' %( nValue * 10)
                self.log.logging("Widget", "Debug", "------>  Thermostat Mode 5 %s %s:%s" % (value, nValue, sValue), NwkId)
                UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)
                
            elif model_name == "TS0601-eTRV5" and WidgetType in ("ThermoMode_5",) and Attribute_ == "6501":   
                if value == 0:
                    self.log.logging("Widget", "Debug", "------>  Thermostat Mode 5 %s %s:%s" % (value, 0, '00'), NwkId)
                    UpdateDevice_v2(self, Devices, device_unit, 0, '00', BatteryLevel, SignalLevel)
                            
            elif WidgetType in ("ThermoMode", "ACMode", ) and Attribute_ == "001c":
                # value seems to come as int or str. To be fixed
                self.log.logging("Widget", "Debug", "------>  Thermostat Mode %s type: %s" % (value, type(value)), NwkId)
                if value in THERMOSTAT_MODE_2_LEVEL:
                    if THERMOSTAT_MODE_2_LEVEL[value] == "00":  # Off
                        UpdateDevice_v2(self, Devices, device_unit, 0, "00", BatteryLevel, SignalLevel)
                    elif THERMOSTAT_MODE_2_LEVEL[value] == "20":  # Cool
                        UpdateDevice_v2(self, Devices, device_unit, 1, "10", BatteryLevel, SignalLevel)
                    elif THERMOSTAT_MODE_2_LEVEL[value] == "30":  # Heat
                        UpdateDevice_v2(self, Devices, device_unit, 2, "20", BatteryLevel, SignalLevel)
                    elif THERMOSTAT_MODE_2_LEVEL[value] == "40":  # Dry
                        UpdateDevice_v2(self, Devices, device_unit, 3, "30", BatteryLevel, SignalLevel)
                    elif THERMOSTAT_MODE_2_LEVEL[value] == "50":  # Fan
                        UpdateDevice_v2(self, Devices, device_unit, 4, "40", BatteryLevel, SignalLevel)
                        
            elif WidgetType in ("CAC221ACMode", ) and Attribute_ == "001c":
                self.log.logging("Widget", "Debug", "------>  Thermostat CAC221ACMode %s type: %s" % (value, type(value)), NwkId)
                if value in THERMOSTAT_MODE_2_LEVEL:
                    if THERMOSTAT_MODE_2_LEVEL[value] == "00":  # Off
                        UpdateDevice_v2(self, Devices, device_unit, 0, "00", BatteryLevel, SignalLevel)
                    elif THERMOSTAT_MODE_2_LEVEL[value] == "10":  # Auto
                        UpdateDevice_v2(self, Devices, device_unit, 1, "10", BatteryLevel, SignalLevel)
                    elif THERMOSTAT_MODE_2_LEVEL[value] == "20":  # Cool
                        UpdateDevice_v2(self, Devices, device_unit, 2, "20", BatteryLevel, SignalLevel)
                    elif THERMOSTAT_MODE_2_LEVEL[value] == "30":  # Heat
                        UpdateDevice_v2(self, Devices, device_unit, 3, "30", BatteryLevel, SignalLevel)
                    elif THERMOSTAT_MODE_2_LEVEL[value] == "40":  # Dry
                        UpdateDevice_v2(self, Devices, device_unit, 4, "40", BatteryLevel, SignalLevel)
                    elif THERMOSTAT_MODE_2_LEVEL[value] == "50":  # Fan
                        UpdateDevice_v2(self, Devices, device_unit, 5, "50", BatteryLevel, SignalLevel)

        if ClusterType == "PM25" and WidgetType == "PM25":
            nvalue = round(value, 0)
            svalue = "%s" % (nvalue,)
            UpdateDevice_v2(self, Devices, device_unit, nvalue, svalue, BatteryLevel, SignalLevel)

        if ClusterType == "PM25" and WidgetType == "SmokePPM":
            nvalue = int(value)
            svalue = "%s" % (nvalue,)
            UpdateDevice_v2(self, Devices, device_unit, nvalue, svalue, BatteryLevel, SignalLevel)

            
        if ClusterType == "Alarm" and WidgetType == "AirPurifierAlarm":
            nValue = 0
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
            UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)
            
        if Attribute_ == "0006" and ClusterType == "FanControl" and WidgetType == "AirPurifierMode":
            nValue = value
            sValue = "%s" %(10 * value,)
            UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)
    
        if Attribute_ == "0007" and ClusterType == "FanControl" and WidgetType == "FanSpeed":
            nValue = round(value, 1)
            sValue = str(nValue)
            UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType == "AirQuality" and Attribute_ == "0002":
            # eco2 for VOC_Sensor from Nexturn is provided via Temp cluster
            nvalue = round(value, 0)
            svalue = "%s" % (nvalue)
            UpdateDevice_v2(self, Devices, device_unit, nvalue, svalue, BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType == "Voc" and Attribute_ == "0003":
            # voc for VOC_Sensor from Nexturn is provided via Temp cluster
            svalue = "%s" % (round(value, 1))
            UpdateDevice_v2(self, Devices, device_unit, 0, svalue, BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType == "CH2O" and Attribute_ == "0004":
            # ch2o for Tuya Smart Air fis provided via Temp cluster
            svalue = "%s" % (round(value, 2))
            UpdateDevice_v2(self, Devices, device_unit, 0, svalue, BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType == "CarbonDioxyde" and Attribute_ == "0005":
            # CarbonDioxyde for Tuya Smart Air provided via Temp cluster
            svalue = "%s" % (round(value, 1))
            UpdateDevice_v2(self, Devices, device_unit, 0, svalue, BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType in ("Temp", "Temp+Hum", "Temp+Hum+Baro") and Attribute_ == "":  # temperature
            
            if check_erratic_value(self, NwkId, "Temp", value, -50, 100):
                # We got an erratic value, no update to Domoticz
                self.log.logging("Widget", "Debug", "%s Receive an erratic Temp: %s, WidgetType: >%s<" % (
                    NwkId, value, WidgetType), NwkId)
                return

            self.log.logging("Widget", "Debug", "------>  Temp: %s, WidgetType: >%s<" % (value, WidgetType), NwkId)
            adjvalue = temp_adjustement_value(self, Devices, NwkId, device_id_ieee, device_unit)

            current_temp, current_humi, current_hum_stat, current_baro, current_baro_forecast = retrieve_data_from_current(self, Devices, device_id_ieee, device_unit, "0;0;0;0;0")

            if WidgetType == "Temp":
                NewNvalue = round(value + adjvalue, 1)
                NewSvalue = str(round(value + adjvalue, 1))
                self.log.logging("Widget", "Debug", "------>  Temp update: %s - %s" % (NewNvalue, NewSvalue))
                UpdateDevice_v2(self, Devices, device_unit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum":
                NewSvalue = f"{round(value + adjvalue, 1)};{current_humi};{current_hum_stat}"
                self.log.logging("Widget", "Debug", "------>  Temp+Hum update:  %s" % (NewSvalue))
                UpdateDevice_v2(self, Devices, device_unit, 0, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum+Baro":
                NewSvalue = f"{round(value + adjvalue, 1)};{current_humi};{current_hum_stat};{current_baro};{current_baro_forecast}"
                UpdateDevice_v2(self, Devices, device_unit, 0, NewSvalue, BatteryLevel, SignalLevel)

        if ClusterType == "Humi" and WidgetType in ("Humi", "Temp+Hum", "Temp+Hum+Baro"):  # humidite
            self.log.logging("Widget", "Debug", "------>  Humi: %s, WidgetType: >%s<" % (value, WidgetType), NwkId)
            # Humidity Status
            humi_status = calculate_humidity_status(value)
            current_temp, current_humi, current_hum_stat, current_baro, current_baro_forecast = retrieve_data_from_current(self, Devices, device_id_ieee, device_unit, "0;0;0;0;0")

            if WidgetType == "Humi":
                NewSvalue = "%s" % humi_status
                self.log.logging("Widget", "Debug", "------>  Humi update: %s - %s" % (value, NewSvalue))
                UpdateDevice_v2(self, Devices, device_unit, value, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum":
                NewSvalue = f"{current_temp};{value};{humi_status}"
                self.log.logging("Widget", "Debug", "------>  Temp+Hum update: %s" % (NewSvalue))
                UpdateDevice_v2(self, Devices, device_unit, 0, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum+Baro":
                NewSvalue = f"{current_temp};{value};{humi_status};{current_baro};{current_baro_forecast}"
                UpdateDevice_v2(self, Devices, device_unit, 0, NewSvalue, BatteryLevel, SignalLevel)

        if ClusterType == "Baro" and WidgetType in ("Baro", "Temp+Hum+Baro"):
            self.log.logging("Widget", "Debug", "------>  Baro: %s, WidgetType: %s" % (value, WidgetType), NwkId)
            
            adjvalue = baro_adjustement_value(self, Devices, NwkId, device_id_ieee, device_unit)

            baroValue = round((value + adjvalue), 1)
            self.log.logging("Widget", "Debug", "------> Adj Value : %s from: %s to %s " % (adjvalue, value, baroValue), NwkId)
            
            Bar_forecast = calculate_baro_forecast(baroValue)
            current_temp, current_humi, current_hum_stat, current_baro, current_baro_forecast = retrieve_data_from_current(self, Devices, device_id_ieee, device_unit, "0;0;0;0;0")

            if WidgetType == "Baro":
                NewSvalue = f"{baroValue};{Bar_forecast}"
                UpdateDevice_v2(self, Devices, device_unit, 0, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum+Baro":
                NewSvalue = f"{current_temp};{current_humi};{current_hum_stat};{baroValue};{Bar_forecast}"
                UpdateDevice_v2(self, Devices, device_unit, 0, NewSvalue, BatteryLevel, SignalLevel)

        if "BSO-Orientation" in ClusterType and WidgetType == "BSO-Orientation":
            nValue = 1 + (round(int(value, 16) / 10))
            if nValue > 10:
                nValue = 10
        
            sValue = str(nValue * 10)
            self.log.logging("Widget", "Debug", " BSO-Orientation Angle: 0x%s/%s Converted into nValue: %s sValue: %s" % (value, int(value, 16), nValue, sValue))
            UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)
            return

        if ClusterType == "Switch" and WidgetType == "SwitchAlarm":
            if isinstance(value, str):
                nValue = int(value, 16)
            else:
                self.log.logging("Widget", "Error", "Looks like this value is not provided in str for %s/%s %s %s %s %s %s" %(
                    NwkId, Ep, model_name, ClusterId, ClusterType, WidgetType, value))
                nValue = value
                
            sValue = "%02x" %nValue
            UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)
            
        if ClusterType == "TamperSwitch" and WidgetType == "SwitchAlarm":
            nValue = value
            sValue = "%02x" %nValue
            UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

        if "Notification" in ClusterType and WidgetType == "Notification":
            # Notification
            # value is a str containing all Orientation information to be updated on Text Widget
            nValue = 0
            sValue = value
            UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

                       
        if ClusterType in ( "Motion", "Door",) and WidgetType == "Motion":
            self.log.logging("Widget", "Debug", "------> Motion %s" % (value), NwkId)
            if isinstance(value, str):
                nValue = int(value, 16)
            else:
                self.log.logging("Widget", "Error", "Looks like this value is not provided in str for %s/%s %s %s %s %s %s" %(
                    NwkId, Ep, model_name, ClusterId, ClusterType, WidgetType, value))
                nValue = value
                
            if nValue == 1:
                UpdateDevice_v2(self, Devices, device_unit, 1, "On", BatteryLevel, SignalLevel, ForceUpdate_=True)
            else:
                UpdateDevice_v2(self, Devices, device_unit, 0, "Off", BatteryLevel, SignalLevel, ForceUpdate_=False)
            return

        if (
            WidgetType not in ("ThermoModeEHZBRTS", "HeatingSwitch", "HeatingStatus", "ThermoMode_2", "ThermoMode_3", "ThermoSetpoint", "ThermoOnOff", "Motionac01") 
            and ( 
                ClusterType in ( "IAS_ACE", "Door", "Switch", "SwitchButton", "AqaraOppleMiddle", "Ikea_Round_5b", "Ikea_Round_OnOff", "Vibration", "OrviboRemoteSquare", "Button_3", "LumiLock", )
                or (ClusterType == WidgetType == "DoorLock")
                or (ClusterType == WidgetType == "Alarm")
                or (ClusterType == "Alarm" and WidgetType == "Tamper")
                or (ClusterType == "DoorLock" and WidgetType == "Vibration")
                or (ClusterType == "FanControl" and WidgetType == "FanControl")
                or ("ThermoMode" in ClusterType and WidgetType == "ACMode_2")
                or ("ThermoMode" in ClusterType and WidgetType == "ACSwing" and Attribute_ == "fd00")
                or ("ThermoMode" in ClusterType and WidgetType == "ThermoMode_7" and Attribute_ == "001c")
                or (WidgetType == "KF204Switch" and ClusterType in ("Switch", "Door"))
                or (WidgetType == "Valve" and Attribute_ == "0014")
                or ("ThermoMode" in ClusterType and WidgetType == "ThermoOnOff")
                or ("Heiman" in ClusterType and WidgetType == "HeimanSceneSwitch")
            )
        ):

            # Plug, Door, Switch, Button ...
            # We reach this point because ClusterType is Door or Switch. It means that Cluster 0x0006 or 0x0500
            # So we might also have to manage case where we receive a On or Off for a LvlControl WidgetType like a dimming Bulb.
            self.log.logging( "Widget", "Debug", "------> Generic Widget for %s ClusterType: %s WidgetType: %s Value: %s" % (
                NwkId, ClusterType, WidgetType, value), NwkId, )

            if ClusterType == "Switch" and WidgetType == "LvlControl":
                # Called with ClusterId: 0x0006 but we have to update a Dimmer, so we need to keep the level
                nValue = int(value)
                sValue = prev_sValue
                if switchType in (13, 16):
                    # Correct for Blinds where we have to display %
                    if value == "00":
                        nValue = 0
                        sValue = "0"
                    elif value == "01" and prev_sValue == "100":
                        nValue = 1
                        sValue = "100"
                    else:
                        nValue = 2
                UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

            elif ClusterType == "Switch" and WidgetType == "Alarm":
                pass
            
            elif ClusterType == "Door" and WidgetType in ( "Smoke", "DoorSensor"):
                nValue = int(value)
                if nValue == 0:
                    sValue = "Off"
                else:
                    sValue = "On"
                UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "DSwitch":
                # double switch avec EP different
                _value = int(value)
                if _value == 1 or _value == 0:
                    if Ep == "01":
                        nValue = 1
                        sValue = "10"
                        UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

                    elif Ep == "02":
                        nValue = 2
                        sValue = "20"
                        UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

                    elif Ep == "03":
                        nValue = 3
                        sValue = "30"
                        UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

            elif (WidgetType == "TuyaSirenHumi" and Attribute_ != "0172") or (WidgetType == "TuyaSirenTemp" and Attribute_ != "0171") or (WidgetType == "TuyaSiren" and Attribute_ != "0168"):
                return

            elif WidgetType == "ThermoOnOff" and Attribute_ != "6501":
                nValue = value
                if nValue == 0:
                    sValue = "Off"
                else:
                    sValue = "On"
                UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=False)

            elif WidgetType == "DButton":
                # double bouttons avec EP different lumi.sensor_86sw2
                _value = int(value)
                if _value == 1:
                    if Ep == "01":
                        nValue = 1
                        sValue = "10"
                        UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

                    elif Ep == "02":
                        nValue = 2
                        sValue = "20"
                        UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

                    elif Ep == "03":
                        nValue = 3
                        sValue = "30"
                        UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

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

                    UpdateDevice_v2(self, Devices, device_unit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

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

                    UpdateDevice_v2(self, Devices, device_unit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

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

                    UpdateDevice_v2(self, Devices, device_unit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == "LvlControl" or WidgetType in ( "ColorControlRGB", "ColorControlWW", "ColorControlRGBWW", "ColorControlFull", "ColorControl", ):
                if switchType in (13, 14, 15, 16):
                    # Required Numeric value
                    if value == "00":
                        UpdateDevice_v2(self, Devices, device_unit, 0, "0", BatteryLevel, SignalLevel)

                    else:
                        # We are in the case of a Shutter/Blind inverse. If we receieve a Read Attribute telling it is On, great
                        # We only update if the shutter was off before, otherwise we will keep its Level.
                        if prev_nValue == 0 and prev_sValue == "Off":
                            UpdateDevice_v2(self, Devices, device_unit, 1, "100", BatteryLevel, SignalLevel)
                else:
                    # Required Off and On
                    if value == "00":
                        UpdateDevice_v2(self, Devices, device_unit, 0, "Off", BatteryLevel, SignalLevel)

                    else:
                        if prev_sValue == "Off":
                            # We do update only if this is a On/off
                            UpdateDevice_v2(self, Devices, device_unit, 1, "On", BatteryLevel, SignalLevel)

            elif WidgetType == "VenetianInverted" and model_name in ( "PR412", "CPR412", "CPR412-E") and ClusterId == "0006":
                self.log.logging( "Widget", "Debug", "--++->  %s/%s ClusterType: %s Updating %s Value: %s" % (NwkId, Ep, ClusterType, WidgetType, value), NwkId, )
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

                self.log.logging("Widget", "Debug", "------>  %s %s/%s Value: %s:%s" % (WidgetType, NwkId, Ep, nValue, sValue), NwkId)
                UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType in ("VenetianInverted", "Venetian", "WindowCovering", "VanneInverted", "Vanne", "Curtain", "CurtainInverted"):
                _value = int(value, 16)
                self.log.logging( "Widget", "Debug", "------>  %s/%s ClusterType: %s Updating %s Value: %s" % (NwkId, Ep, ClusterType, WidgetType, _value), NwkId, )
                if WidgetType in ("VenetianInverted", "VanneInverted"):
                    _value = 100 - _value
                    self.log.logging("Widget", "Debug", "------>  Patching %s/%s Value: %s" % (NwkId, Ep, _value), NwkId)
                # nValue will depends if we are on % or not
                if _value == 0:
                    nValue = 0
                elif _value == 100:
                    nValue = 1
                else:
                    if switchType in (4, 15):
                        nValue = 17
                    else:
                        nValue = 2
                UpdateDevice_v2(self, Devices, device_unit, nValue, str(_value), BatteryLevel, SignalLevel)

            elif (
                ((ClusterType == "FanControl" and WidgetType == "FanControl") or ("ThermoMode" in ClusterType and WidgetType == "ACSwing" and Attribute_ == "fd00"))
                and model_name in ("AC211", "AC221", "CAC221")
                and "Ep" in self.ListOfDevices[NwkId]
                and WidgetEp in self.ListOfDevices[NwkId]["Ep"]
                and "0201" in self.ListOfDevices[NwkId]["Ep"][WidgetEp]
                and "001c" in self.ListOfDevices[NwkId]["Ep"][WidgetEp]["0201"]
                and self.ListOfDevices[NwkId]["Ep"][WidgetEp]["0201"]["001c"] == 0x00
            ):
                # Thermo mode is Off, let's switch off Wing and Fan
                self.log.logging("Widget", "Debug", "------> Switch off as System Mode is Off")
                UpdateDevice_v2(self, Devices, device_unit, 0, "00", BatteryLevel, SignalLevel)

            elif WidgetType in SWITCH_SELECTORS and value in SWITCH_SELECTORS[WidgetType]:
                self.log.logging("Widget", "Debug", "------> Auto Update %s" % str(SWITCH_SELECTORS[WidgetType][value]))
                if len(SWITCH_SELECTORS[WidgetType][value]) == 2:
                    nValue, sValue = SWITCH_SELECTORS[WidgetType][value]
                    _ForceUpdate = SWITCH_SELECTORS[WidgetType]["ForceUpdate"]
                    self.log.logging( "Widget", "Debug", "------> Switch update WidgetType: %s with %s" % (
                        WidgetType, str(SWITCH_SELECTORS[WidgetType])), NwkId, )
                    UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=_ForceUpdate)
                else:
                    self.log.logging( "Widget", "Error", "------>  len(SWITCH_SELECTORS[ %s ][ %s ]) == %s" % (
                        WidgetType, value, len(SWITCH_SELECTORS[WidgetType])), NwkId, )

        if "WindowCovering" in ClusterType and WidgetType in ("VenetianInverted", "Venetian", "Vanne", "VanneInverted", "WindowCovering", "Curtain", "CurtainInverted", "Blind"):
            _value = int(value, 16)
            self.log.logging(
                "Widget",
                "Debug",
                "------>  %s/%s ClusterType: %s Updating %s Value: %s" % (NwkId, Ep, ClusterType, WidgetType, _value),
                NwkId,
            )
            if WidgetType in ("VenetianInverted", "VanneInverted", "CurtainInverted"):
                _value = 100 - _value
                self.log.logging("Widget", "Debug", "------>  Patching %s/%s Value: %s" % (NwkId, Ep, _value), NwkId)
            # nValue will depends if we are on % or not
            if _value == 0:
                nValue = 0
            elif _value == 100:
                nValue = 1
            else:
                if switchType in (4, 15):
                    nValue = 17
                else:
                    nValue = 2
            self.log.logging("Widget", "Debug", "------>  %s %s/%s Value: %s:%s" % (WidgetType, NwkId, Ep, nValue, _value), NwkId)
            UpdateDevice_v2(self, Devices, device_unit, nValue, str(_value), BatteryLevel, SignalLevel)

        if "LvlControl" in ClusterType:  # LvlControl ( 0x0008)
            if WidgetType == "LvlControl" or ( WidgetType in ( "BSO-Volet", "Blind", ) ):
                # We need to handle the case, where we get an update from a Read Attribute or a Reporting message
                # We might get a Level, but the device is still Off and we shouldn't make it On .
                nValue = None
                self.log.logging("Widget", "Debug", "------>  LvlControl analogValue: -> %s" % value, NwkId)
                
                normalized_value = normalized_lvl_value( switchType, value )
                self.log.logging( "Widget", "Debug", "------>  LvlControl new sValue: -> %s old nValue/sValue %s:%s" % (
                    normalized_value, prev_nValue, prev_sValue), NwkId, )
                
                # In case we reach 0% or 100% we shouldn't switch Off or On, except in the case of Shutter/Blind
                if normalized_value == 0:
                    nValue = 0
                    if switchType in (13, 14, 15, 16):
                        self.log.logging( "Widget", "Debug", "------>  LvlControl UpdateDevice: -> %s/%s SwitchType: %s" % (
                            0, 0, switchType), NwkId, )
                        UpdateDevice_v2(self, Devices, device_unit, 0, "0", BatteryLevel, SignalLevel)
                    else:
                        # if prev_nValue == 0 and prev_sValue == 'Off':
                        if prev_nValue == 0 and (prev_sValue == "Off" or prev_sValue == str(normalized_value)):
                            pass
                        else:
                            self.log.logging("Widget", "Debug", "------>  LvlControl UpdateDevice: -> %s/%s" % (0, 0), NwkId)
                            UpdateDevice_v2(self, Devices, device_unit, 0, "0", BatteryLevel, SignalLevel)

                elif normalized_value == 100:
                    nValue = 1
                    if switchType in (13, 14, 15, 16):
                        self.log.logging( "Widget", "Debug", "------>  LvlControl UpdateDevice: -> %s/%s SwitchType: %s" % (
                            1, 100, switchType), NwkId, )
                        UpdateDevice_v2(self, Devices, device_unit, 1, "100", BatteryLevel, SignalLevel)

                    else:
                        if prev_nValue == 0 and (prev_sValue == "Off" or prev_sValue == str(normalized_value)):
                            pass
                        else:
                            self.log.logging("Widget", "Debug", "------>  LvlControl UpdateDevice: -> %s/%s" % (1, 100), NwkId)
                            UpdateDevice_v2(self, Devices, device_unit, 1, "100", BatteryLevel, SignalLevel)

                else:  # sValue != 0 and sValue != 100

                    # if prev_nValue == 0 and prev_sValue == 'Off':
                    if prev_nValue == 0 and (prev_sValue == "Off" or prev_sValue == str(normalized_value)):
                        # Do nothing. We receive a ReadAttribute  giving the position of a Off device.
                        pass
                    elif switchType in (13, 14, 15, 16):
                        self.log.logging( "Widget", "Debug", "------>  LvlControl UpdateDevice: -> %s/%s SwitchType: %s" % (
                            nValue, normalized_value, switchType), NwkId, )
                        UpdateDevice_v2(self, Devices, device_unit, 2, str(normalized_value), BatteryLevel, SignalLevel)

                    else:
                        # Just update the Level if Needed
                        self.log.logging( "Widget", "Debug", "------>  LvlControl UpdateDevice: -> %s/%s SwitchType: %s" % (
                            nValue, normalized_value, switchType), NwkId, )
                        UpdateDevice_v2( self, Devices, device_unit, prev_nValue, str(normalized_value), BatteryLevel, SignalLevel, )

            elif WidgetType in ( "ColorControlRGB", "ColorControlWW", "ColorControlRGBWW", "ColorControlFull", "ColorControl", ):
                if prev_nValue != 0 or prev_sValue != "Off":
                    nValue, sValue = getDimmerLevelOfColor(self, value)
                    UpdateDevice_v2(self, Devices, device_unit, nValue, str(sValue), BatteryLevel, SignalLevel, Color_)

            elif WidgetType == "LegrandSelector":
                self.log.logging("Widget", "Debug", "------> LegrandSelector : Value -> %s" % value, NwkId)
                if value == "00":
                    nValue = 0
                    sValue = "00"  # Off
                    UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                elif value == "01":
                    nValue = 1
                    sValue = "10"  # On
                    UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                elif value == "moveup":
                    nValue = 2
                    sValue = "20"  # Move Up
                    UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                elif value == "movedown":
                    nValue = 3
                    sValue = "30"  # Move Down
                    UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                elif value == "stop":
                    nValue = 4
                    sValue = "40"  # Stop
                    UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                else:
                    self.log.logging("Widget", "Error", "------>  %s LegrandSelector Unknown value %s" % (NwkId, value))
                    
            elif WidgetType == "LegrandSleepWakeupSelector":
                self.log.logging("Widget", "Debug", "------> LegrandSleepWakeupSelector : Value -> %s" % value, NwkId)
                if value == "00":
                    nValue = 1
                    sValue = "10"  # sleep
                    UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                elif value == "01":
                    nValue = 2
                    sValue = "20"  # wakeup
                    UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                else:
                    self.log.logging("Widget", "Error", "------>  %s LegrandSleepWakeupSelector Unknown value %s" % (NwkId, value))

            elif WidgetType == "Generic_5_buttons":
                self.log.logging("Widget", "Debug", "------> Generic 5 buttons : Value -> %s" % value, NwkId)
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

                UpdateDevice_v2(self, Devices, device_unit, nvalue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == "GenericLvlControl":
                # 1,10: Off
                # 2,20: On
                # 3,30: Move Up
                # 4,40: Move Down
                # 5,50: Stop
                self.log.logging("Widget", "Debug", "------> GenericLvlControl : Value -> %s" % value, NwkId)
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

                UpdateDevice_v2(self, Devices, device_unit, nvalue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == "HueSmartButton":
                self.log.logging("Widget", "Debug", "------> HueSmartButton : Value -> %s" % value, NwkId)
                if value == "toggle":
                    nvalue = 1
                    sValue = "10"  # toggle
                elif value == "move":
                    nvalue = 2
                    sValue = "20"  # Move
                else:
                    return
                UpdateDevice_v2(self, Devices, device_unit, nvalue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == "INNR_RC110_SCENE":
                self.log.logging("Widget", "Debug", "------>  Updating INNR_RC110_SCENE (LvlControl) Value: %s" % value, NwkId)
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
                UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "INNR_RC110_LIGHT":
                self.log.logging("Widget", "Debug", "------>  Updating INNR_RC110_LIGHT (LvlControl) Value: %s" % value, NwkId)
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
                UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "TINT_REMOTE_WHITE":
                nValue = int(value)
                sValue = "%s" % (10 * nValue)
                UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel)

        if ClusterType in ( "ColorControlRGB", "ColorControlWW", "ColorControlRGBWW", "ColorControlFull", "ColorControl", ) and ClusterType == WidgetType:
            # We just manage the update of the Dimmer (Control Level)
            nValue, sValue = getDimmerLevelOfColor(self, value)
            UpdateDevice_v2(self, Devices, device_unit, nValue, str(sValue), BatteryLevel, SignalLevel, Color_)

        if "Orientation" in ClusterType and WidgetType == "Orientation":
            # Xiaomi Vibration
            # value is a str containing all Orientation information to be updated on Text Widget
            nValue = 0
            sValue = value
            UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

        if "Strenght" in ClusterType and WidgetType == "Strenght":
            # value is a str containing all Orientation information to be updated on Text Widget
            nValue = 0
            sValue = value
            UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

        if "Distance" in ClusterType and WidgetType == "Distance":
            # value is a str containing all Distance information in cm
            nValue = 0
            sValue = value
            UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

        if "Lux" in ClusterType and WidgetType == "Lux":
            nValue = int(value)
            sValue = value
            UpdateDevice_v2(self, Devices, device_unit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=False)

        # Check if this Device belongs to a Group. In that case update group
        CheckUpdateGroup(self, NwkId, Ep, ClusterId)


def retreive_device_unit( self, Devices, NwkId, Ep, device_id_ieee, ClusterId, WidgetId ):
    """ Retreive the Device Unit from the Plugin Database (ClusterType information), then check that unit exists in the Domoticz Devices """

    device_unit = find_widget_unit_from_WidgetID(self, Devices, WidgetId )
    
    if device_unit is None:
        self.log.logging( "Widget", "Error", "Device %s not found !!!" % WidgetId, NwkId)
        # House keeping, we need to remove this bad clusterType
        if remove_bad_cluster_type_entry(self, NwkId, Ep, ClusterId, WidgetId ):
            self.log.logging( "Widget", "Log", "WidgetID %s not found, successfully remove the entry from device" % WidgetId, NwkId)
        else:
            self.log.logging( "Widget", "Error", "WidgetID %s not found, unable to remove the entry from device" % WidgetId, NwkId)
        return None
    
    elif not domo_check_unit(self, Devices, device_id_ieee, device_unit):
        # device_id_ieee, device_unit not in Devices !!!
        return None
    
    return device_unit


def CheckUpdateGroup(self, NwkId, Ep, ClusterId):

    if ClusterId not in ("0006", "0008", "0102"):
        return

    if self.groupmgt:
        self.groupmgt.checkAndTriggerIfMajGroupNeeded(NwkId, Ep, ClusterId)


def getDimmerLevelOfColor(self, value):
    nValue = 1
    analogValue = value if isinstance(value, int) else int(value, 16)

    if analogValue >= 255:
        sValue = 100
    else:
        sValue = min(round((analogValue / 255) * 100), 100)
        sValue = max(sValue, 1) if sValue > 0 else 0

    return nValue, sValue


def check_erratic_value(self, NwkId, value_type, value, expected_min, expected_max):
    """
    Check if the value is in the range or not. If out of range and disableTrackingValue not set, will check for 5 consecutive errors to log as an error.
    Returns False if the value is in the range, True if the value is out of range.
    """
    attribute_key = "Erratic_" + value_type
    tracking_disable = _get_disable_tracking_eratic_value(self, NwkId)

    if expected_min < value < expected_max:
        # Value is in the thresholds, everything is fine
        _clear_erratic_attribute(self, NwkId, attribute_key)
        return False

    if tracking_disable:
        return True

    # We have an erratic value and we have to track, let's try to handle some erratic values
    consecutive_erratic_value = _increment_consecutive_erratic_value(self, NwkId, attribute_key)

    if consecutive_erratic_value > 5:
        _log_erratic_value_error(self, NwkId, value_type, value, expected_min, expected_max)
        _clear_erratic_attribute(self, NwkId, attribute_key)
        return True

    _log_erratic_value_debug(self, NwkId, value_type, value, expected_min, expected_max, consecutive_erratic_value)
    return True


def _get_disable_tracking_eratic_value(self, NwkId):
    param_data = self.ListOfDevices.get(NwkId, {}).get("Param", {})
    return param_data.get("disableTrackingEraticValue", False)


def _increment_consecutive_erratic_value(self, NwkId, attribute_key):
    device_data = self.ListOfDevices.setdefault(NwkId, {})
    erratic_data = device_data.setdefault(attribute_key, {"ConsecutiveErraticValue": 0})
    erratic_data["ConsecutiveErraticValue"] += 1
    return erratic_data["ConsecutiveErraticValue"]


def _clear_erratic_attribute(self, NwkId, attribute_key):
    device_data = self.ListOfDevices.get(NwkId, {})
    if attribute_key in device_data:
        del device_data[attribute_key]


def _log_erratic_value_error(self, NwkId, value_type, value, expected_min, expected_max):
    self.log.logging("Widget", "Error", f"Aberrant {value_type}: {value} (below {expected_min} or above {expected_max}) for device: {NwkId}", NwkId)


def _log_erratic_value_debug(self, NwkId, value_type, value, expected_min, expected_max, consecutive_erratic_value):
    self.log.logging("Widget", "Debug", f"Aberrant {value_type}: {value} (below {expected_min} or above {expected_max}) for device: {NwkId} [{consecutive_erratic_value}]", NwkId)


def check_set_meter_widget( self, Devices, DeviceId, Unit, mode):
    # Mode = 0 - From device (default)
    # Mode = 1 - Computed

    sMode = "%s" %mode

    Options = {'EnergyMeterMode': '0'}
    
    _device_options = domo_read_Options( self, Devices, DeviceId, Unit,)
    self.log.logging( "Widget", "Debug", "check_set_meter_widget Options: %s" %_device_options)
    
    # Do we have the Energy Mode calculation already set ?
    if "EnergyMeterMode" in _device_options:
        # Yes, let's retreive it
        Options = _device_options

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
    if len(current_list_values) == nb_parameters:
        result_list = current_list_values
        
    elif len(current_list_values) < nb_parameters:
        result_list = current_list_values + zero_padded_list[len(current_list_values):]
        
    else:
        result_list = zero_padded_list

    self.log.logging("Widget", "Log", f"retrieve_data_from_current - svalue: {current_svalue} Nb Param: {nb_parameters} returning {result_list}")

    return result_list


def normalized_lvl_value( switchType, value ):
    
    # Normalize sValue vs. analog value coomming from a ReadAttribute
    analogValue = value if isinstance( value, int) else int(value, 16)

    if analogValue >= 255:
        normalized_value = 255

    normalized_value = round(((analogValue * 100) / 255))
    normalized_value = min(normalized_value, 100)
    if normalized_value == 0 and analogValue > 0:
        normalized_value = 1

    # Looks like in the case of the Profalux shutter, we never get 0 or 100
    if switchType in (13, 14, 15, 16):
        if normalized_value == 1 and analogValue == 1:
            normalized_value = 0
        if normalized_value == 99 and analogValue == 254:
            normalized_value = 100

    return normalized_value


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


def baro_adjustement_value(self, Devices, NwkId, DeviceId, Device_Unit):
    if self.domoticzdb_DeviceStatus:
        try:
            return round(self.domoticzdb_DeviceStatus.retreiveAddjValue_baro(domo_read_Device_Idx(self, Devices, DeviceId, Device_Unit,)), 1)
        except Exception as e:
            self.log.logging("Widget", "Error", "Error while trying to get Adjusted Value for Baro %s %s" % (
                NwkId, e), NwkId)   
    return 0

def temp_adjustement_value(self, Devices, NwkId, DeviceId, Device_Unit):
    if self.domoticzdb_DeviceStatus:
        try:
            return round(self.domoticzdb_DeviceStatus.retreiveAddjValue_temp(domo_read_Device_Idx(self, Devices, DeviceId, Device_Unit,)), 1)
        except Exception as e:
            self.log.logging("Widget", "Error", "Error while trying to get Adjusted Value for Temp %s %s" % (
                NwkId, e), NwkId)
    return 0