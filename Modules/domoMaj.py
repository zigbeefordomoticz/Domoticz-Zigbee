#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: domoMaj.py
    Description: Update of Domoticz Widget
"""
import Domoticz

from Modules.domoTools import (RetreiveSignalLvlBattery,
                               RetreiveWidgetTypeList, TypeFromCluster,
                               UpdateDevice_v2)
from Modules.widgets import SWITCH_LVL_MATRIX
from Modules.zigateConsts import THERMOSTAT_MODE_2_LEVEL


def MajDomoDevice(self, Devices, NWKID, Ep, clusterID, value, Attribute_="", Color_=""):
    """
    MajDomoDevice
    Update domoticz device accordingly to Type found in EP and value/Color provided
    """

    # Sanity Checks
    if NWKID not in self.ListOfDevices:
        self.log.logging("Widget", "Error", "MajDomoDevice - %s not known" % NWKID, NWKID)
        return

    if Ep not in self.ListOfDevices[NWKID]["Ep"]:
        self.log.logging("Widget", "Error", "MajDomoDevice - %s/%s not known Endpoint" % (NWKID, Ep), NWKID)
        return

    if "Status" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Status"] != "inDB":
        self.log.logging(
            "Widget",
            "Log",
            "MajDomoDevice NwkId: %s status: %s not inDB" % (NWKID, self.ListOfDevices[NWKID]["Status"]),
            NWKID,
        )
        return

    if "IEEE" not in self.ListOfDevices[NWKID]:
        self.log.logging("Widget", "Error", "MajDomoDevice - no IEEE for %s" % NWKID, NWKID)
        return

    model_name = ""
    if "Model" in self.ListOfDevices[NWKID]:
        model_name = self.ListOfDevices[NWKID]["Model"]

    self.log.logging(
        "Widget",
        "Debug",
        "MajDomoDevice NwkId: %s Ep: %s ClusterId: %s Value: %s ValueType: %s Attribute: %s Color: %s ModelName: %s" % (
            NWKID, Ep, clusterID, value, type(value), Attribute_, Color_, model_name),
        NWKID,
    )

    # Get the CluserType ( Action type) from Cluster Id
    ClusterType = TypeFromCluster(self, clusterID)
    self.log.logging("Widget", "Debug", "------> ClusterType = " + str(ClusterType), NWKID)

    ClusterTypeList = RetreiveWidgetTypeList(self, Devices, NWKID)

    if len(ClusterTypeList) == 0:
        # We don't have any widgets associated to the NwkId
        return

    WidgetByPassEpMatch = ("XCube", "Aqara", "DSwitch", "DButton", "DButton_3")

    for WidgetEp, WidgetId, WidgetType in ClusterTypeList:
        if WidgetEp == "00":
            # Old fashion
            WidgetEp = "01"  # Force to 01

        self.log.logging(
            "Widget",
            "Debug",
            "----> processing WidgetEp: %s, WidgetId: %s, WidgetType: %s" % (WidgetEp, WidgetId, WidgetType),
            NWKID,
        )
        if WidgetType not in WidgetByPassEpMatch:
            # We need to make sure that we are on the right Endpoint
            if WidgetEp != Ep:
                self.log.logging(
                    "Widget",
                    "Debug",
                    "------> skiping this WidgetEp as do not match Ep : %s %s" % (WidgetEp, Ep),
                    NWKID,
                )
                continue

        DeviceUnit = 0
        for x in Devices:  # Found the Device Unit
            if Devices[x].ID == int(WidgetId):
                DeviceUnit = x
                break
        if DeviceUnit == 0:
            Domoticz.Error("Device %s not found !!!" % WidgetId)
            return

        Switchtype = Devices[DeviceUnit].SwitchType
        Subtype = Devices[DeviceUnit].SubType

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

        self.log.logging(
            "Widget",
            "Debug",
            "------> ClusterType: %s WidgetEp: %s WidgetId: %s WidgetType: %s Attribute_: %s" % (ClusterType, WidgetEp, WidgetId, WidgetType, Attribute_),
            NWKID,
        )

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
                self.log.logging(
                    "Widget",
                    "Error",
                    "------> Expecting 2 values got %s in Value = %s for Nwkid: %s Attribute: %s" % (
                        len(tuple_value), value, NWKID, Attribute_),
                    NWKID,
                )
                continue

            value, text = tuple_value
            nValue = int(value)
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, text, BatteryLevel, SignalLevel)

        if ClusterType == "Alarm" and WidgetType == "Alarm_ZL3" and Attribute_ == "0020":
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
            ampere1, ampere2, ampere3 = retreive_data_from_current(self, Devices, DeviceUnit, "%s;%s;%s")
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

            self.log.logging("Widget", "Log", "------>  Ampere3 : %s from Attribute: %s" % (sValue, Attribute_), NWKID)
            UpdateDevice_v2(self, Devices, DeviceUnit, 0, str(sValue), BatteryLevel, SignalLevel)

        if "Power" in ClusterType:  # Instant Power/Watts
            # Power and Meter usage are triggered only with the Instant Power usage.
            # it is assumed that if there is also summation provided by the device, that
            # such information is stored on the data structuture and here we will retreive it.
            # value is expected as String
            if WidgetType == "P1Meter" and Attribute_ == "0000":
                self.log.logging("Widget", "Debug", "------>  P1Meter : %s (%s)" % (value, type(value)), NWKID)
                # P1Meter report Instant and Cummulative Power.
                # We need to retreive the Cummulative Power.
                CurrentsValue = Devices[DeviceUnit].sValue
                if len(CurrentsValue.split(";")) != 6:
                    # First time after device creation
                    CurrentsValue = "0;0;0;0;0;0"
                SplitData = CurrentsValue.split(";")
                cur_usage1 = SplitData[0]
                cur_usage2 = SplitData[1]
                cur_return1 = SplitData[2]
                cur_return2 = SplitData[3]
                usage1 = usage2 = return1 = return2 = cons = prod = 0
                if "0702" in self.ListOfDevices[NWKID]["Ep"][Ep] and "0400" in self.ListOfDevices[NWKID]["Ep"][Ep]["0702"]:
                    cons = round(float(self.ListOfDevices[NWKID]["Ep"][Ep]["0702"]["0400"]), 2)
                usage1 = int(float(value))

                sValue = "%s;%s;%s;%s;%s;%s" % (usage1, usage2, return1, return2, cons, prod)
                self.log.logging("Widget", "Debug", "------>  P1Meter : " + sValue, NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, str(sValue), BatteryLevel, SignalLevel)

            if WidgetType == "P1Meter_ZL" and "Model" in self.ListOfDevices[NWKID] and self.ListOfDevices[NWKID]["Model"] == "ZLinky_TIC" and Attribute_ in ("0100", "0102", "0104", "0106", "0108", "010a", "050f"):
 
                if Attribute_ != "050f" and Ep == "01" and Attribute_ not in ("0100", "0102"):
                    # Ep = 01, so we store Base, or HP,HC, or BBRHCJB, BBRHPJB
                    continue
                if Attribute_ != "050f" and Ep == "f2" and Attribute_ not in ("0104", "0106"):
                    # Ep = f2, so we store BBRHCJW, BBRHPJW
                    continue
                if Attribute_ != "050f" and Ep == "f3" and Attribute_ not in ("0108", "010a"):
                    # Ep == f3, so we store BBRHCJR, BBRHPJR
                    continue
                tarif_color = None
                if "ZLinky" in self.ListOfDevices[NWKID] and "Color" in self.ListOfDevices[NWKID]["ZLinky"]:
                    tarif_color = self.ListOfDevices[NWKID]["ZLinky"]["Color"]

                self.log.logging("Widget", "Debug", "------>  P1Meter_ZL : %s (%s)" % (value, type(value)), NWKID)
                # P1Meter report Instant and Cummulative Power.
                # We need to retreive the Cummulative Power.
                cur_usage1, cur_usage2, cur_return1, cur_return2, cons, prod = retreive_data_from_current(self, Devices, DeviceUnit, "0;0;0;0;0;0")
                usage1 = usage2 = return1 = return2 = cons = prod = 0

                if Attribute_ == "050f":
                    self.log.logging(
                        "Widget",
                        "Debug",
                        "------>  P1Meter_ZL : Trigger by Puissance Apparente: Color: %s Ep: %s" % (tarif_color, Ep),
                        NWKID,
                    )
                    cons = round(float(value), 2)
                    usage1 = cur_usage1
                    usage2 = cur_usage2
                    return1 = cur_return1
                    return2 = cur_return2
                else:
                    # We are so receiving a usage update
                    self.log.logging(
                        "Widget",
                        "Debug",
                        "------>  P1Meter_ZL : Trigger by Index Update %s Ep: %s" % (Attribute_, Ep),
                        NWKID,
                    )
                    if "0b04" in self.ListOfDevices[NWKID]["Ep"]["01"] and "050f" in self.ListOfDevices[NWKID]["Ep"]["01"]["0b04"]:
                        cons = round(float(self.ListOfDevices[NWKID]["Ep"]["01"]["0b04"]["050f"]), 2)

                    if Attribute_ in ("0000", "0100", "0104", "0108"):
                        usage1 = int(round(float(value), 0))
                        usage2 = cur_usage2
                        return1 = cur_return1
                        return2 = cur_return2
                    elif Attribute_ in ("0102", "0106", "010a"):
                        usage1 = cur_usage1
                        usage2 = int(round(float(value), 0))
                        return1 = cur_return1
                        return2 = cur_return2

                    if tarif_color == "Blue" and Ep != "01" or tarif_color == "White" and Ep != "f2" or tarif_color == "Red" and Ep != "f3":
                        cons = 0.0

                sValue = "%s;%s;%s;%s;%s;%s" % (usage1, usage2, return1, return2, cons, prod)
                self.log.logging("Widget", "Debug", "------>  P1Meter_ZL (%s): %s" % (Ep, sValue), NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, str(sValue), BatteryLevel, SignalLevel)

            if WidgetType == "Power" and (Attribute_ in ("", "050f") or clusterID == "000c"):  # kWh
                nValue = round(float(value), 2)
                sValue = value
                self.log.logging("Widget", "Debug", "------>  : " + sValue, NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(sValue), BatteryLevel, SignalLevel)

        if "Meter" in ClusterType:  # Meter Usage.
            # value is string an represent the Instant Usage
            if WidgetType == "Meter" and Attribute_ == "050f":
                # We receive Instant Power
                check_set_meter_widget( Devices, DeviceUnit, 0)
                _instant, summation = retreive_data_from_current(self, Devices, DeviceUnit, "0;0")
                instant = round(float(value), 2)
                sValue = "%s;%s" % (instant, summation)
                self.log.logging("Widget", "Debug", "------>  : " + sValue)

                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "Meter" and ( Attribute_ == "0000" or 
                                            ( Attribute_ in ("0100", "0102") and Ep == "01") or
                                            ( Attribute_ in ("0104", "0106") and Ep == "f2") or
                                            ( Attribute_ in ("0108", "010a") and Ep == "f3")):
                
                # We are in the case were we receive Summation , let's find the last instant power and update
                check_set_meter_widget( Devices, DeviceUnit, 0)    
                instant, _summation = retreive_data_from_current(self, Devices, DeviceUnit, "0;0")
                summation = round(float(value), 2)
                
                sValue = "%s;%s" % (instant, summation)
                self.log.logging("Widget", "Debug", "------>  : " + sValue)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)

            elif (WidgetType == "Meter" and Attribute_ == "") or (WidgetType == "Power" and clusterID == "000c"):  # kWh
                # We receive Instant
                # Let's check if we have Summation in the datastructutre
                summation = 0
                if ( 
                    "0702" in self.ListOfDevices[NWKID]["Ep"][Ep] and 
                    "0000" in self.ListOfDevices[NWKID]["Ep"][Ep]["0702"] and 
                    self.ListOfDevices[NWKID]["Ep"][Ep]["0702"]["0000"] not in  ({}, "", "0")
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
                    check_set_meter_widget( Devices, DeviceUnit, 0)
                else:
                    sValue = "%s;" % (instant)
                    check_set_meter_widget( Devices, DeviceUnit, 1)
                    # No summation retreive, so we make sure that EnergyMeterMode is
                    # correctly set to 1 (compute), if not adjust

                self.log.logging("Widget", "Debug", "------>  : " + sValue)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)

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
                strRound = lambda DeviceUnit, n: eval('"%.' + str(int(n)) + 'f" % ' + repr(DeviceUnit))
                nValue = 0
                sValue = strRound(float(setpoint), 2)
                self.log.logging("Widget", "Debug", "------>  Thermostat Setpoint: %s %s" % (0, setpoint), NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)

        if "Analog" in ClusterType and model_name not in (
            "lumi.sensor_cube.aqgl01",
            "lumi.sensor_cube",
        ):  # Analog Value from Analog Input cluster
            UpdateDevice_v2(self, Devices, DeviceUnit, 0, value, BatteryLevel, SignalLevel)

        if "Valve" in ClusterType:  # Valve Position
            if WidgetType == "Valve" and Attribute_ in ("026d", "4001", "0008"):
                # value int is the % of the valve opening
                # Percentage Widget
                nValue = round(value, 1)
                sValue = str(nValue)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

        if "ThermoMode" in ClusterType:  # Thermostat Mode

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

            elif WidgetType == "HACTMODE" and Attribute_ == "e011":  #  Wiser specific Fil Pilote
                # value is str
                self.log.logging("Widget", "Debug", "------>  ThermoMode HACTMODE: %s" % (value), NWKID)
                THERMOSTAT_MODE = {0: "10", 1: "20"}  # Conventional heater  # fip enabled heater
                _mode = ((int(value, 16) - 0x80) >> 1) & 1

                if _mode in THERMOSTAT_MODE:
                    sValue = THERMOSTAT_MODE[_mode]
                    nValue = _mode + 1
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "LegranCableMode" and clusterID == "fc01":  #  Legrand
                # value is str
                self.log.logging("Widget", "Debug", "------>  Legrand Mode: %s" % (value), NWKID)
                THERMOSTAT_MODE = {0x0100: "10", 0x0200: "20"}  # Conventional heater  # fip enabled heater
                _mode = int(value, 16)

                if _mode not in THERMOSTAT_MODE:
                    return

                sValue = THERMOSTAT_MODE[_mode]
                nValue = int(sValue) // 10
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "FIP" and Attribute_ in ("0000", "e020"):  #  Wiser specific Fil Pilote
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

                if Attribute_ == "e020":  #  Wiser specific Fil Pilote
                    if "0201" in self.ListOfDevices[NWKID]["Ep"][Ep]:
                        if "e011" in self.ListOfDevices[NWKID]["Ep"][Ep]["0201"]:
                            if self.ListOfDevices[NWKID]["Ep"][Ep]["0201"]["e011"] != {} and self.ListOfDevices[NWKID]["Ep"][Ep]["0201"]["e011"] != "":
                                _value_mode_hact = self.ListOfDevices[NWKID]["Ep"][Ep]["0201"]["e011"]
                                _mode_hact = ((int(_value_mode_hact, 16) - 0x80)) & 1
                                if _mode_hact == 0:
                                    self.log.logging("Widget", "Debug", "------>  Disable FIP widget: %s" % (value), NWKID)
                                    nValue = 0
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

                elif clusterID == "fc40":  # Legrand FIP
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "ThermoMode_3" and Attribute_ == "001c":
                #   0x00: Off
                #   0x01: Confort
                #   0x03: No-Freeze
                if "ThermoMode_3" not in SWITCH_LVL_MATRIX:
                    continue
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
                    self.log.logging("Widget", "Error", "MajDomoDevice - Unknown value for %s/%s, clusterID: %s, value: %s, Attribute_=%s," % (NWKID, Ep, clusterID, value, Attribute_), NWKID)
                    continue
                self.log.logging("Widget", "Log", "------>  Thermostat Mode 3 %s %s:%s" % (value, nValue, sValue), NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "ThermoMode_2" and Attribute_ == "001c":
                # Use by Tuya TRV
                if "ThermoMode_2" not in SWITCH_LVL_MATRIX:
                    continue
                if value not in SWITCH_LVL_MATRIX["ThermoMode_2"]:
                    Domoticz.Error("Unknown TermoMode2 value: %s" % value)
                    continue
                nValue = SWITCH_LVL_MATRIX["ThermoMode_2"][value][0]
                sValue = SWITCH_LVL_MATRIX["ThermoMode_2"][value][1]
                self.log.logging("Widget", "Debug", "------>  Thermostat Mode 2 %s %s:%s" % (value, nValue, sValue), NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "ThermoMode_4" and Attribute_ == "001c":
                # Use by Tuya TRV
                nValue = value
                sValue = '%02d' %( nValue * 10)
                self.log.logging("Widget", "Debug", "------>  Thermostat Mode 4 %s %s:%s" % (value, nValue, sValue), NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "ThermoMode_5" and Attribute_ == "001c":
                # Use by Tuya TRV
                nValue = value
                sValue = '%02d' %( nValue * 10)
                self.log.logging("Widget", "Debug", "------>  Thermostat Mode 5 %s %s:%s" % (value, nValue, sValue), NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)


            elif WidgetType in ("ThermoMode", "ACMode") and Attribute_ == "001c":
                # value seems to come as int or str. To be fixed
                self.log.logging("Widget", "Debug", "------>  Thermostat Mode %s type: %s" % (value, type(value)), NWKID)

                if value in THERMOSTAT_MODE_2_LEVEL:
                    if THERMOSTAT_MODE_2_LEVEL[value] == "00":  # Off
                        UpdateDevice_v2(self, Devices, DeviceUnit, 0, "00", BatteryLevel, SignalLevel)
                    elif THERMOSTAT_MODE_2_LEVEL[value] == "20":  # Cool
                        UpdateDevice_v2(self, Devices, DeviceUnit, 1, "10", BatteryLevel, SignalLevel)
                    elif THERMOSTAT_MODE_2_LEVEL[value] == "30":  # Heat
                        UpdateDevice_v2(self, Devices, DeviceUnit, 2, "20", BatteryLevel, SignalLevel)
                    elif THERMOSTAT_MODE_2_LEVEL[value] == "40":  # Dry
                        UpdateDevice_v2(self, Devices, DeviceUnit, 3, "30", BatteryLevel, SignalLevel)
                    elif THERMOSTAT_MODE_2_LEVEL[value] == "50":  # Fan
                        UpdateDevice_v2(self, Devices, DeviceUnit, 4, "40", BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType == "AirQuality" and Attribute_ == "0002":
            # eco2 for VOC_Sensor from Nexturn is provided via Temp cluster
            nvalue = round(value, 0)
            svalue = "%s" % (nvalue)
            UpdateDevice_v2(self, Devices, DeviceUnit, nvalue, svalue, BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType == "Voc" and Attribute_ == "0003":
            # voc for VOC_Sensor from Nexturn is provided via Temp cluster
            value = "%s" % (round(value, 1))
            UpdateDevice_v2(self, Devices, DeviceUnit, 0, value, BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType == "CH2O" and Attribute_ == "0004":
            # ch2o for Tuya Smart Air fis provided via Temp cluster
            value = "%s" % (round(value, 2))
            UpdateDevice_v2(self, Devices, DeviceUnit, 0, value, BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType == "CarbonDioxyde" and Attribute_ == "0005":
            # CarbonDioxyde for Tuya Smart Air provided via Temp cluster
            value = "%s" % (round(value, 1))
            UpdateDevice_v2(self, Devices, DeviceUnit, 0, value, BatteryLevel, SignalLevel)

        if ClusterType == "Temp" and WidgetType in ("Temp", "Temp+Hum", "Temp+Hum+Baro") and Attribute_ == "":  # temperature

            if check_erratic_value(self, NWKID, "Temp", value, -50, 100):
                # We got an erratic value, no update to Domoticz
                continue

            self.log.logging("Widget", "Debug", "------>  Temp: %s, WidgetType: >%s<" % (value, WidgetType), NWKID)
            adjvalue = 0
            if self.domoticzdb_DeviceStatus:
                from Classes.DomoticzDB import DomoticzDB_DeviceStatus

                adjvalue = round(self.domoticzdb_DeviceStatus.retreiveAddjValue_temp(Devices[DeviceUnit].ID), 1)
            self.log.logging(
                "Widget",
                "Debug",
                "------> Adj Value : %s from: %s to %s " % (adjvalue, value, (value + adjvalue)),
                NWKID,
            )
            CurrentnValue = Devices[DeviceUnit].nValue
            CurrentsValue = Devices[DeviceUnit].sValue
            if CurrentsValue == "":
                # First time after device creation
                CurrentsValue = "0;0;0;0;0"
            SplitData = CurrentsValue.split(";")
            NewNvalue = 0
            NewSvalue = ""
            if WidgetType == "Temp":
                NewNvalue = round(value + adjvalue, 1)
                NewSvalue = str(round(value + adjvalue, 1))
                self.log.logging("Widget", "Debug", "------>  Temp update: %s - %s" % (NewNvalue, NewSvalue))
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum":
                NewNvalue = 0
                NewSvalue = "%s;%s;%s" % (round(value + adjvalue, 1), SplitData[1], SplitData[2])
                self.log.logging("Widget", "Debug", "------>  Temp+Hum update: %s - %s" % (NewNvalue, NewSvalue))
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum+Baro":  # temp+hum+Baro xiaomi
                NewNvalue = 0
                NewSvalue = "%s;%s;%s;%s;%s" % (
                    round(value + adjvalue, 1),
                    SplitData[1],
                    SplitData[2],
                    SplitData[3],
                    SplitData[4],
                )
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

        if ClusterType == "Humi" and WidgetType in ("Humi", "Temp+Hum", "Temp+Hum+Baro"):  # humidite
            self.log.logging("Widget", "Debug", "------>  Humi: %s, WidgetType: >%s<" % (value, WidgetType), NWKID)
            CurrentnValue = Devices[DeviceUnit].nValue
            CurrentsValue = Devices[DeviceUnit].sValue
            if CurrentsValue == "":
                # First time after device creation
                CurrentsValue = "0;0;0;0;0"
            SplitData = CurrentsValue.split(";")
            NewNvalue = 0
            NewSvalue = ""
            # Humidity Status
            if value < 40:
                humiStatus = 2
            elif 40 <= value < 70:
                humiStatus = 1
            else:
                humiStatus = 3

            if WidgetType == "Humi":
                NewNvalue = value
                NewSvalue = "%s" % humiStatus
                self.log.logging("Widget", "Debug", "------>  Humi update: %s - %s" % (NewNvalue, NewSvalue))
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum":  # temp+hum xiaomi
                NewNvalue = 0
                NewSvalue = "%s;%s;%s" % (SplitData[0], value, humiStatus)
                self.log.logging("Widget", "Debug", "------>  Temp+Hum update: %s - %s" % (NewNvalue, NewSvalue))
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum+Baro":  # temp+hum+Baro xiaomi
                NewNvalue = 0
                NewSvalue = "%s;%s;%s;%s;%s" % (SplitData[0], value, humiStatus, SplitData[3], SplitData[4])
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

        if ClusterType == "Baro" and WidgetType in ("Baro", "Temp+Hum+Baro"):  # barometre
            self.log.logging("Widget", "Debug", "------>  Baro: %s, WidgetType: %s" % (value, WidgetType), NWKID)
            adjvalue = 0
            if self.domoticzdb_DeviceStatus:
                from Classes.DomoticzDB import DomoticzDB_DeviceStatus

                adjvalue = round(self.domoticzdb_DeviceStatus.retreiveAddjValue_baro(Devices[DeviceUnit].ID), 1)
            baroValue = round((value + adjvalue), 1)
            self.log.logging("Widget", "Debug", "------> Adj Value : %s from: %s to %s " % (adjvalue, value, baroValue), NWKID)

            CurrentnValue = Devices[DeviceUnit].nValue
            CurrentsValue = Devices[DeviceUnit].sValue
            if len(CurrentsValue.split(";")) != 5:
                # First time after device creation
                CurrentsValue = "0;0;0;0;0"
            SplitData = CurrentsValue.split(";")
            NewNvalue = 0
            NewSvalue = ""

            if baroValue < 1000:
                Bar_forecast = 4  # RAIN
            elif baroValue < 1020:
                Bar_forecast = 3  # CLOUDY
            elif baroValue < 1030:
                Bar_forecast = 2  # PARTLY CLOUDY
            else:
                Bar_forecast = 1  # SUNNY

            if WidgetType == "Baro":
                NewSvalue = "%s;%s" % (baroValue, Bar_forecast)
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum+Baro":
                NewSvalue = "%s;%s;%s;%s;%s" % (SplitData[0], SplitData[1], SplitData[2], baroValue, Bar_forecast)
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

        if "BSO-Orientation" in ClusterType:  # 0xfc21 Not fully tested / So far developped for Profalux
            # value is str
            if WidgetType == "BSO-Orientation":
                # Receveive Level (orientation) in degrees to convert into % for the slider
                # Translate the Angle into Selector item
                nValue = 1 + (round(int(value, 16) / 10))
                if nValue > 10:
                    nValue = 10

                sValue = str(nValue * 10)
                Domoticz.Log(" BSO-Orientation Angle: 0x%s/%s Converted into nValue: %s sValue: %s" % (value, int(value, 16), nValue, sValue))
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)
                return

        if ClusterType == WidgetType == "Motion":
            nValue = int(value, 16)
            if nValue == 1:
                sValue = "On"
            else:
                sValue = "Off"
            UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

        if WidgetType not in ("ThermoModeEHZBRTS", "HeatingSwitch", "HeatingStatus", "ThermoMode_2", "ThermoMode_3", "ThermoSetpoint", "ThermoOnOff",) and (
            (
                ClusterType
                in (
                    "IAS_ACE",
                    "Door",
                    "Switch",
                    "SwitchButton",
                    "AqaraOppleMiddle",
                    "Ikea_Round_5b",
                    "Ikea_Round_OnOff",
                    "Vibration",
                    "OrviboRemoteSquare",
                    "Button_3",
                    "LumiLock",
                )
            )
            or (ClusterType == WidgetType == "DoorLock")
            or (ClusterType == WidgetType == "Alarm")
            or (ClusterType == "Alarm" and WidgetType == "Tamper")
            or (ClusterType == "DoorLock" and WidgetType == "Vibration")
            or (ClusterType == "FanControl" and WidgetType == "FanControl")
            or ("ThermoMode" in ClusterType and WidgetType == "ACMode_2")
            or ("ThermoMode" in ClusterType and WidgetType == "ACSwing" and Attribute_ == "fd00")
            or (WidgetType == "KF204Switch" and ClusterType in ("Switch", "Door"))
            or (WidgetType == "Valve" and Attribute_ == "0014")
            or ("ThermoMode" in ClusterType and WidgetType == "ThermoOnOff")
        ):

            # Plug, Door, Switch, Button ...
            # We reach this point because ClusterType is Door or Switch. It means that Cluster 0x0006 or 0x0500
            # So we might also have to manage case where we receive a On or Off for a LvlControl WidgetType like a dimming Bulb.
            self.log.logging(
                "Widget",
                "Debug",
                "------> Generic Widget for %s ClusterType: %s WidgetType: %s Value: %s" % (NWKID, ClusterType, WidgetType, value),
                NWKID,
            )

            if ClusterType == "Switch" and WidgetType == "LvlControl":
                # Called with ClusterID: 0x0006 but we have to update a Dimmer, so we need to keep the level
                nValue = int(value)
                sValue = Devices[DeviceUnit].sValue
                if Devices[DeviceUnit].SwitchType in (13, 16):
                    # Correct for Blinds where we have to display %
                    if value == "00":
                        nValue = 0
                        sValue = "0"
                    elif value == "01" and Devices[DeviceUnit].sValue == "100":
                        nValue = 1
                        sValue = "100"
                    else:
                        nValue = 2
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif ClusterType == "Door" and WidgetType == "DoorSensor":
                nValue = int(value)
                if nValue == 0:
                    sValue = "Off"
                else:
                    sValue = "On"
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)
                
            elif WidgetType == "DSwitch":
                # double switch avec EP different
                value = int(value)
                if value == 1 or value == 0:
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
                value = int(value)
                if value == 1:
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
                value = int(value)
                data = "00"
                state = "00"
                if Ep == "01":
                    if value == 1:
                        state = "10"
                        data = "01"

                    elif value == 2:
                        state = "20"
                        data = "02"

                    elif value == 3:
                        state = "30"
                        data = "03"

                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif Ep == "02":
                    if value == 1:
                        state = "40"
                        data = "04"

                    elif value == 2:
                        state = "50"
                        data = "05"

                    elif value == 3:
                        state = "60"
                        data = "06"

                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

                elif Ep == "03":
                    if value == 1:
                        state = "70"
                        data = "07"

                    elif value == 2:
                        state = "80"
                        data = "08"

                    elif value == 3:
                        state = "90"
                        data = "09"

                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == "LvlControl" or WidgetType in (
                "ColorControlRGB",
                "ColorControlWW",
                "ColorControlRGBWW",
                "ColorControlFull",
                "ColorControl",
            ):
                if Devices[DeviceUnit].SwitchType in (13, 14, 15, 16):
                    # Required Numeric value
                    if value == "00":
                        UpdateDevice_v2(self, Devices, DeviceUnit, 0, "0", BatteryLevel, SignalLevel)

                    else:
                        # We are in the case of a Shutter/Blind inverse. If we receieve a Read Attribute telling it is On, great
                        # We only update if the shutter was off before, otherwise we will keep its Level.
                        if Devices[DeviceUnit].nValue == 0 and Devices[DeviceUnit].sValue == "Off":
                            UpdateDevice_v2(self, Devices, DeviceUnit, 1, "100", BatteryLevel, SignalLevel)
                else:
                    # Required Off and On
                    if value == "00":
                        UpdateDevice_v2(self, Devices, DeviceUnit, 0, "Off", BatteryLevel, SignalLevel)

                    else:
                        if Devices[DeviceUnit].sValue == "Off":
                            # We do update only if this is a On/off
                            UpdateDevice_v2(self, Devices, DeviceUnit, 1, "On", BatteryLevel, SignalLevel)

            elif WidgetType in ("VenetianInverted", "Venetian", "WindowCovering", "VanneInverted", "Vanne"):
                value = int(value, 16)
                self.log.logging(
                    "Widget",
                    "Debug",
                    "------>  %s/%s ClusterType: %s Updating %s Value: %s" % (NWKID, Ep, ClusterType, WidgetType, value),
                    NWKID,
                )
                if WidgetType in ("VenetianInverted", "VanneInverted"):
                    value = 100 - value
                    self.log.logging("Widget", "Debug", "------>  Patching %s/%s Value: %s" % (NWKID, Ep, value), NWKID)
                # nValue will depends if we are on % or not
                if value == 0:
                    nValue = 0
                elif value == 100:
                    nValue = 1
                else:
                    if Switchtype in (4, 15):
                        nValue = 17
                    else:
                        nValue = 2
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(value), BatteryLevel, SignalLevel)

            elif (
                ((ClusterType == "FanControl" and WidgetType == "FanControl") or ("ThermoMode" in ClusterType and WidgetType == "ACSwing" and Attribute_ == "fd00"))
                and model_name in ("AC211", "AC221", "CAC221")
                and "Ep" in self.ListOfDevices[NWKID]
                and WidgetEp in self.ListOfDevices[NWKID]["Ep"]
                and "0201" in self.ListOfDevices[NWKID]["Ep"][WidgetEp]
                and "001c" in self.ListOfDevices[NWKID]["Ep"][WidgetEp]["0201"]
                and self.ListOfDevices[NWKID]["Ep"][WidgetEp]["0201"]["001c"] == 0x0
            ):
                # Thermo mode is Off, let's switch off Wing and Fan
                self.log.logging("Widget", "Debug", "------> Switch off as System Mode is Off")
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, "00", BatteryLevel, SignalLevel)

            elif WidgetType in SWITCH_LVL_MATRIX and value in SWITCH_LVL_MATRIX[WidgetType]:
                self.log.logging("Widget", "Debug", "------> Auto Update %s" % str(SWITCH_LVL_MATRIX[WidgetType][value]))
                if len(SWITCH_LVL_MATRIX[WidgetType][value]) == 2:
                    nValue, sValue = SWITCH_LVL_MATRIX[WidgetType][value]
                    _ForceUpdate = SWITCH_LVL_MATRIX[WidgetType]["ForceUpdate"]
                    self.log.logging(
                        "Widget",
                        "Debug",
                        "------> Switch update WidgetType: %s with %s" % (WidgetType, str(SWITCH_LVL_MATRIX[WidgetType])),
                        NWKID,
                    )
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=_ForceUpdate)
                else:
                    self.log.logging(
                        "Widget",
                        "Error",
                        "------>  len(SWITCH_LVL_MATRIX[ %s ][ %s ]) == %s" % (WidgetType, value, len(SWITCH_LVL_MATRIX[WidgetType])),
                        NWKID,
                    )

        if "WindowCovering" in ClusterType:  # 0x0102
            if WidgetType in ("VenetianInverted", "Venetian", "Vanne", "VanneInverted", "WindowCovering"):
                value = int(value, 16)
                self.log.logging(
                    "Widget",
                    "Debug",
                    "------>  %s/%s ClusterType: %s Updating %s Value: %s" % (NWKID, Ep, ClusterType, WidgetType, value),
                    NWKID,
                )
                if WidgetType in ("VenetianInverted", "VanneInverted"):
                    value = 100 - value
                    self.log.logging("Widget", "Debug", "------>  Patching %s/%s Value: %s" % (NWKID, Ep, value), NWKID)
                # nValue will depends if we are on % or not
                if value == 0:
                    nValue = 0
                elif value == 100:
                    nValue = 1
                else:
                    if Switchtype in (4, 15):
                        nValue = 17
                    else:
                        nValue = 2
                self.log.logging("Widget", "Debug", "------>  %s %s/%s Value: %s:%s" % (WidgetType, NWKID, Ep, nValue, value), NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(value), BatteryLevel, SignalLevel)

        if "LvlControl" in ClusterType:  # LvlControl ( 0x0008)
            if WidgetType == "LvlControl" or (
                WidgetType
                in (
                    "BSO-Volet",
                    "Blind",
                )
            ):
                # We need to handle the case, where we get an update from a Read Attribute or a Reporting message
                # We might get a Level, but the device is still Off and we shouldn't make it On .
                nValue = None
                # Normalize sValue vs. analog value coomming from a ReadATtribute
                analogValue = int(value, 16)
                self.log.logging("Widget", "Debug", "------>  LvlControl analogValue: -> %s" % analogValue, NWKID)
                if analogValue >= 255:
                    sValue = 100
                else:
                    sValue = round(((int(value, 16) * 100) / 255))
                    if sValue > 100:
                        sValue = 100
                    if sValue == 0 and analogValue > 0:
                        sValue = 1
                    # Looks like in the case of the Profalux shutter, we never get 0 or 100
                    if Devices[DeviceUnit].SwitchType in (13, 14, 15, 16):
                        if sValue == 1 and analogValue == 1:
                            sValue = 0
                        if sValue == 99 and analogValue == 254:
                            sValue = 100
                self.log.logging(
                    "Widget",
                    "Debug",
                    "------>  LvlControl new sValue: -> %s old nValue/sValue %s:%s" % (sValue, Devices[DeviceUnit].nValue, Devices[DeviceUnit].sValue),
                    NWKID,
                )
                # In case we reach 0% or 100% we shouldn't switch Off or On, except in the case of Shutter/Blind
                if sValue == 0:
                    nValue = 0
                    if Devices[DeviceUnit].SwitchType in (13, 14, 15, 16):
                        self.log.logging(
                            "Widget",
                            "Debug",
                            "------>  LvlControl UpdateDevice: -> %s/%s SwitchType: %s" % (0, 0, Devices[DeviceUnit].SwitchType),
                            NWKID,
                        )
                        UpdateDevice_v2(self, Devices, DeviceUnit, 0, "0", BatteryLevel, SignalLevel)
                    else:
                        # if Devices[DeviceUnit].nValue == 0 and Devices[DeviceUnit].sValue == 'Off':
                        if Devices[DeviceUnit].nValue == 0 and (Devices[DeviceUnit].sValue == "Off" or Devices[DeviceUnit].sValue == str(sValue)):
                            pass
                        else:
                            self.log.logging("Widget", "Debug", "------>  LvlControl UpdateDevice: -> %s/%s" % (0, 0), NWKID)
                            UpdateDevice_v2(self, Devices, DeviceUnit, 0, "0", BatteryLevel, SignalLevel)
                elif sValue == 100:
                    nValue = 1
                    if Devices[DeviceUnit].SwitchType in (13, 14, 15, 16):
                        self.log.logging(
                            "Widget",
                            "Debug",
                            "------>  LvlControl UpdateDevice: -> %s/%s SwitchType: %s" % (1, 100, Devices[DeviceUnit].SwitchType),
                            NWKID,
                        )
                        UpdateDevice_v2(self, Devices, DeviceUnit, 1, "100", BatteryLevel, SignalLevel)

                    else:
                        if Devices[DeviceUnit].nValue == 0 and (Devices[DeviceUnit].sValue == "Off" or Devices[DeviceUnit].sValue == str(sValue)):
                            pass
                        else:
                            self.log.logging("Widget", "Debug", "------>  LvlControl UpdateDevice: -> %s/%s" % (1, 100), NWKID)
                            UpdateDevice_v2(self, Devices, DeviceUnit, 1, "100", BatteryLevel, SignalLevel)

                else:  # sValue != 0 and sValue != 100

                    # if Devices[DeviceUnit].nValue == 0 and Devices[DeviceUnit].sValue == 'Off':
                    if Devices[DeviceUnit].nValue == 0 and (Devices[DeviceUnit].sValue == "Off" or Devices[DeviceUnit].sValue == str(sValue)):
                        # Do nothing. We receive a ReadAttribute  giving the position of a Off device.
                        pass
                    elif Devices[DeviceUnit].SwitchType in (13, 14, 15, 16):
                        self.log.logging(
                            "Widget",
                            "Debug",
                            "------>  LvlControl UpdateDevice: -> %s/%s SwitchType: %s" % (nValue, sValue, Devices[DeviceUnit].SwitchType),
                            NWKID,
                        )
                        UpdateDevice_v2(self, Devices, DeviceUnit, 2, str(sValue), BatteryLevel, SignalLevel)

                    else:
                        # Just update the Level if Needed
                        self.log.logging(
                            "Widget",
                            "Debug",
                            "------>  LvlControl UpdateDevice: -> %s/%s SwitchType: %s" % (nValue, sValue, Devices[DeviceUnit].SwitchType),
                            NWKID,
                        )
                        UpdateDevice_v2(
                            self,
                            Devices,
                            DeviceUnit,
                            Devices[DeviceUnit].nValue,
                            str(sValue),
                            BatteryLevel,
                            SignalLevel,
                        )

            elif WidgetType in (
                "ColorControlRGB",
                "ColorControlWW",
                "ColorControlRGBWW",
                "ColorControlFull",
                "ColorControl",
            ):
                if Devices[DeviceUnit].nValue != 0 or Devices[DeviceUnit].sValue != "Off":
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
                    Domoticz.Error("------>  %s LegrandSelector Unknown value %s" % (NWKID, value))

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

        if ClusterType in (
            "ColorControlRGB",
            "ColorControlWW",
            "ColorControlRGBWW",
            "ColorControlFull",
            "ColorControl",
        ):
            # We just manage the update of the Dimmer (Control Level)
            if ClusterType == WidgetType:
                nValue, sValue = getDimmerLevelOfColor(self, value)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(sValue), BatteryLevel, SignalLevel, Color_)

        if ("XCube" in ClusterType) or ("Analog" in ClusterType and model_name in ("lumi.sensor_cube.aqgl01", "lumi.sensor_cube")):  # XCube Aqara or Xcube
            if WidgetType == "Aqara":
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

        if "Orientation" in ClusterType:
            # Xiaomi Vibration
            if WidgetType == "Orientation":
                # value is a str containing all Orientation information to be updated on Text Widget
                nValue = 0
                sValue = value
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

        if "Strenght" in ClusterType:
            if WidgetType == "Strength":
                # value is a str containing all Orientation information to be updated on Text Widget
                nValue = 0
                sValue = value
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

        if "Lux" in ClusterType:
            if WidgetType == "Lux":
                nValue = int(value)
                sValue = value
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

        # Check if this Device belongs to a Group. In that case update group
        CheckUpdateGroup(self, NWKID, Ep, clusterID)


def CheckUpdateGroup(self, NwkId, Ep, ClusterId):

    if ClusterId not in ("0006", "0008", "0102"):
        return

    if self.groupmgt:
        self.groupmgt.checkAndTriggerIfMajGroupNeeded(NwkId, Ep, ClusterId)


def getDimmerLevelOfColor(self, value):

    nValue = 1
    analogValue = int(value, 16)
    if analogValue >= 255:
        sValue = 100

    else:
        sValue = round(((int(value, 16) * 100) / 255))
        if sValue > 100:
            sValue = 100

        if sValue == 0 and analogValue > 0:
            sValue = 1

    return (nValue, sValue)


def check_erratic_value(self, NwkId, value_type, value, expected_min, expected_max):

    _attribute = "Erratic_" + value_type
    if expected_min < value < expected_max:
        # Value is in the threasholds, every thing fine
        if _attribute in self.ListOfDevices[NwkId]:
            # Remove the attribute if we had a previous erratic value
            del self.ListOfDevices[NwkId][_attribute]
        return False

    if _attribute not in self.ListOfDevices[NwkId]:
        self.ListOfDevices[NwkId][_attribute] = {}
        self.ListOfDevices[NwkId][_attribute]["ConsecutiveErraticValue"] = 1

    self.ListOfDevices[NwkId][_attribute]["ConsecutiveErraticValue"] += 1
    if self.ListOfDevices[NwkId][_attribute]["ConsecutiveErraticValue"] > 3:
        self.log.logging(
            "Widget",
            "Error",
            "Aberrant %s: %s (below %s or above %s) for device: %s" % (value_type, value, expected_min, expected_max, NwkId),
            NwkId,
        )
    else:
        self.log.logging(
            "Widget",
            "Log",
            "Aberrant %s: %s (below % or above %s) for device: %s [%s]"
            % (
                value_type,
                value,
                expected_min,
                expected_max,
                NwkId,
                self.ListOfDevices[NwkId][_attribute]["ConsecutiveErraticValue"],
            ),
            NwkId,
        )
    return True

def check_set_meter_widget( Devices, Unit, mode):
    # Mode = 0 - From device (default)
    # Mode = 1 - Computed

    sMode = "%s" %mode

    Options = {'EnergyMeterMode': '0'}
    # Do we have the Energy Mode calculation already set ?
    if "EnergyMeterMode" in Devices[Unit].Options:
        # Yes, let's retreive it
        Options = Devices[Unit].Options

    if Options["EnergyMeterMode"] != sMode:
        oldnValue = Devices[Unit].nValue
        oldsValue = Devices[Unit].sValue
        Options = {}
        Options["EnergyMeterMode"] = sMode
        Devices[Unit].Update(oldnValue, oldsValue, Options=Options)


def retreive_data_from_current(self, Devices, Unit, _format):

    nb_parameters = len(_format.split(";"))
    currentsValue = Devices[Unit].sValue
    if len(currentsValue.split(";")) != nb_parameters:
        currentsValue = ""
        for x in range(0, nb_parameters):
            if x != nb_parameters - 1:
                currentsValue += "0;"
            else:
                currentsValue += "0"

    self.log.logging("Widget", "Debug", "retreive_data_from_current - Nb Param: %s returning %s" % (nb_parameters, currentsValue))

    return currentsValue.split(";")
