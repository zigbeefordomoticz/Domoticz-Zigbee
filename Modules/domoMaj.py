#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: domoMaj.py
    Description: Update of Domoticz Widget
"""

import json
import time

import Domoticz

from Modules.logging import loggingWidget
from Modules.zigateConsts import THERMOSTAT_MODE_2_LEVEL
from Modules.widgets import SWITCH_LVL_MATRIX

from Modules.domoTools import TypeFromCluster, RetreiveSignalLvlBattery, UpdateDevice_v2, RetreiveWidgetTypeList

def MajDomoDevice(self, Devices, NWKID, Ep, clusterID, value, Attribute_='', Color_=''):
    """
    MajDomoDevice
    Update domoticz device accordingly to Type found in EP and value/Color provided
    """
    def CheckUpdateGroup( self, NwkId, Ep, ClusterId):

        if ClusterId not in ( '0006', '0008', '0102' ):
            return

        if self.groupmgt:
            self.groupmgt.checkAndTriggerIfMajGroupNeeded( NwkId, Ep, ClusterId)


    def getDimmerLevelOfColor( self, value):

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

        return ( nValue, sValue )

    # Sanity Checks
    if NWKID not in self.ListOfDevices:
        Domoticz.Error("MajDomoDevice - %s not known" %NWKID)
        return

    if 'IEEE' not in self.ListOfDevices[NWKID]:
        Domoticz.Error("MajDomoDevice - no IEEE for %s" %NWKID)
        return

    loggingWidget( self, "Debug", "MajDomoDevice NwkId: %s Ep: %s ClusterId: %s Value: %s ValueType: %s Attribute: %s Color: %s"
        %( NWKID, Ep, clusterID, value, type(value),Attribute_, Color_ ), NWKID )

    # Get the CluserType ( Action type) from Cluster Id
    ClusterType = TypeFromCluster(self, clusterID)
    loggingWidget( self, "Debug", "------> ClusterType = " + str(ClusterType), NWKID)
 
    ClusterTypeList = RetreiveWidgetTypeList( self, Devices, NWKID )

    if len(ClusterTypeList) == 0:
        # We don't have any widgets associated to the NwkId
        return

    WidgetByPassEpMatch = ( 'XCube', 'Aqara', 'DSwitch', 'DButton', 'DButton_3')

    for WidgetEp , WidgetId, WidgetType in ClusterTypeList:
        if WidgetEp == '00':
            # Old fashion
            WidgetEp = '01' # Force to 01

        loggingWidget( self, 'Debug', "----> processing WidgetEp: %s, WidgetId: %s, WidgetType: %s" %(WidgetEp, WidgetId, WidgetType), NWKID)
        if (WidgetType not in WidgetByPassEpMatch):
            # We need to make sure that we are on the right Endpoint
            if WidgetEp != Ep:
                loggingWidget( self, 'Debug', "------> skiping this WidgetEp as do not match Ep : %s %s" %(WidgetEp, Ep), NWKID)
                continue

        DeviceUnit = 0
        for x in Devices: # Found the Device Unit
            if Devices[x].ID == int(WidgetId):
                DeviceUnit = x
                break
        if DeviceUnit == 0:
            Domoticz.Error("Device %s not found !!!" %WidgetId)
            return

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

        loggingWidget( self, 'Debug', "------> WidgetEp: %s WidgetId: %s WidgetType: %s" %( WidgetEp , WidgetId, WidgetType), NWKID)

        SignalLevel,BatteryLevel = RetreiveSignalLvlBattery( self, NWKID)

        if 'Power' in ClusterType: # Instant Power/Watts
            # Power and Meter usage are triggered only with the Instant Power usage.
            # it is assumed that if there is also summation provided by the device, that
            # such information is stored on the data structuture and here we will retreive it.
            # value is expected as String
            if WidgetType == 'P1Meter' and Attribute_ == '0000' :
                # P1Meter report Instant and Cummulative Power.
                # We need to retreive the Cummulative Power.
                conso = 0
                if '0702' in self.ListOfDevices[NWKID]['Ep'][Ep]:
                    if '0400' in self.ListOfDevices[NWKID]['Ep'][Ep]['0702']:
                        conso = round(float(self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0400']),2)
                summation = round(float(value),2)
                nValue = 0
                sValue = "%s;%s;%s;%s;%s;%s" %(summation,0,0,0,conso,0)
                loggingWidget( self, "Debug", "------>  P1Meter : " + sValue, NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, str(sValue), BatteryLevel, SignalLevel)

            elif WidgetType == "Power" and ( Attribute_== '' or clusterID == "000c"):  # kWh
                nValue = round(float(value),2)
                sValue = value
                loggingWidget( self, "Debug", "------>  : " + sValue, NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(sValue), BatteryLevel, SignalLevel)

        if 'Meter' in ClusterType: # Meter Usage. 
            # value is string an represent the Instant Usage
            if (WidgetType == "Meter" and Attribute_== '') or \
                (WidgetType == "Power" and clusterID == "000c" ):  # kWh

            # Let's check if we have Summation in the datastructutre
                summation = 0
                if '0702' in self.ListOfDevices[NWKID]['Ep'][Ep]:
                    if '0000' in self.ListOfDevices[NWKID]['Ep'][Ep]['0702']:
                        if self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0000'] != {} and self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0000'] != '' and \
                                self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0000'] != '0':
                            summation = int(self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0000'])

                Options = {}
                # Do we have the Energy Mode calculation already set ?
                if 'EnergyMeterMode' in Devices[ DeviceUnit ].Options:
                    # Yes, let's retreive it
                    Options = Devices[ DeviceUnit ].Options
                else:
                    # No, let's set to compute
                    Options['EnergyMeterMode'] = '0' # By default from device

                # Did we get Summation from Data Structure
                if summation:
                    # We got summation from Device, let's check that EnergyMeterMode is
                    # correctly set to 0, if not adjust
                    if Options['EnergyMeterMode'] != '0':
                        oldnValue = Devices[ DeviceUnit ].nValue
                        oldsValue = Devices[ DeviceUnit ].sValue
                        Options = {}
                        Options['EnergyMeterMode'] = '0'
                        Devices[ DeviceUnit ].Update( oldnValue, oldsValue, Options=Options )
                else:
                    # No summation retreive, so we make sure that EnergyMeterMode is
                    # correctly set to 1 (compute), if not adjust
                    if Options['EnergyMeterMode'] != '1':
                        oldnValue = Devices[ DeviceUnit ].nValue
                        oldsValue = Devices[ DeviceUnit ].sValue
                        Options = {}
                        Options['EnergyMeterMode']='1'
                        Devices[ DeviceUnit ].Update( oldnValue, oldsValue, Options=Options )

                nValue = round(float(value),2)
                summation = round(float(summation),2)
                sValue = "%s;%s" % (nValue, summation)
                loggingWidget( self, "Debug", "------>  : " + sValue)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)

        if 'Voltage' in ClusterType:  # Volts
            # value is str
            if WidgetType == "Voltage": 
                nValue = round(float(value),2)
                sValue = "%s;%s" % (nValue, nValue)
                loggingWidget( self, "Debug", "------>  : " + sValue, NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)

        if 'ThermoSetpoint' in ClusterType: # Thermostat SetPoint
            # value is a str
            if  WidgetType == 'ThermoSetpoint' and Attribute_ in ( '4003', '0012'):
                setpoint = round(float(value),2)
                # Normalize SetPoint value with 2 digits
                strRound = lambda DeviceUnit, n: eval('"%.' + str(int(n)) + 'f" % ' + repr(DeviceUnit))
                nValue = 0
                sValue = strRound( float(setpoint), 2 )
                loggingWidget( self, "Debug", "------>  Thermostat Setpoint: %s %s" %(0,setpoint), NWKID)
                UpdateDevice_v2(self, Devices, DeviceUnit, 0, sValue, BatteryLevel, SignalLevel)
    
        if 'ThermoMode' in ClusterType: # Thermostat Mode
           
            if WidgetType == 'ThermoModeEHZBRTS' and Attribute_ == "e010": # Thermostat Wiser
                 # value is str
                loggingWidget( self, "Debug", "------>  EHZBRTS Schneider Thermostat Mode %s" %value, NWKID)
                THERMOSTAT_MODE = { 0:'00', # Mode Off
                    1:'10', # Manual
                    2:'20', # Schedule
                    3:'30', # Energy Saver
                    4:'40', # Schedule Ebergy Saver
                    5:'50', # Holiday Off
                    6:'60'  # Holiday Frost Protection
                    }
                _mode = int(value,16)
                if _mode in THERMOSTAT_MODE:
                    nValue = _mode
                    sValue = THERMOSTAT_MODE[ _mode ]
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)    

            elif WidgetType ==  'HeatingSwitch' and Attribute_ == "001c":
                loggingWidget( self, "Debug", "------>  HeatingSwitch %s" %value, NWKID)
                if value == 0:
                    UpdateDevice_v2(self, Devices, DeviceUnit, 0, 'Off', BatteryLevel, SignalLevel)
                elif value == 4:
                    UpdateDevice_v2(self, Devices, DeviceUnit, 1, 'On', BatteryLevel, SignalLevel)


            elif WidgetType == 'HACTMODE' and Attribute_ == "e011":#  Wiser specific Fil Pilote
                 # value is str
                loggingWidget( self, "Debug", "------>  ThermoMode HACTMODE: %s" %(value), NWKID)
                THERMOSTAT_MODE = {
                    0:'10', # Conventional heater
                    1:'20' # fip enabled heater
                    }
                _mode = ((int(value,16) - 0x80) >> 1 ) & 1

                if _mode in THERMOSTAT_MODE:
                    sValue = THERMOSTAT_MODE[ _mode ]
                    nValue = _mode + 1
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == 'FIP' and Attribute_ == "e020":#  Wiser specific Fil Pilote
                 # value is str
                loggingWidget( self, "Debug", "------>  ThermoMode FIP: %s" %(value), NWKID)
                FIL_PILOT_MODE = {
                    0 : '10',
                    1 : '20', # confort -1
                    2 : '30', # confort -2
                    3 : '40', # eco
                    4 : '50', # frost protection
                    5 : '60'
                }
                _mode = int(value,16)

                if _mode in FIL_PILOT_MODE:
                    sValue = FIL_PILOT_MODE[ _mode ]
                    nValue = _mode + 1
                    if '0201' in self.ListOfDevices[NWKID]['Ep'][Ep]:
                        if 'e011' in self.ListOfDevices[NWKID]['Ep'][Ep]['0201']:
                            if self.ListOfDevices[NWKID]['Ep'][Ep]['0201']['e011'] != {} and self.ListOfDevices[NWKID]['Ep'][Ep]['0201']['e011'] != '' :
                                _value_mode_hact  = self.ListOfDevices[NWKID]['Ep'][Ep]['0201']['e011']
                                _mode_hact = ((int(_value_mode_hact,16) - 0x80)  ) & 1
                                if _mode_hact  == 0 :
                                    loggingWidget( self, "Debug", "------>  Disable FIP widget: %s" %(value), NWKID)
                                    nValue =  0
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == 'ThermoMode' and Attribute_ == '001c':
                # value seems to come as int or str. To be fixed
                loggingWidget( self, "Debug", "------>  Thermostat Mode %s" %value, NWKID)
                nValue = value
                if isinstance( value, str):
                    nValue = int(value,16)
                if nValue in THERMOSTAT_MODE_2_LEVEL:
                    sValue = THERMOSTAT_MODE_2_LEVEL[nValue]
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)
                    loggingWidget( self, "Debug", "------>  Thermostat Mode: %s %s" %(nValue,sValue), NWKID)

        if ClusterType == 'Temp' and WidgetType in ( 'Temp', 'Temp+Hum', 'Temp+Hum+Baro'):  # temperature
            loggingWidget( self, "Debug", "------>  Temp: %s, WidgetType: >%s<" %(value,WidgetType), NWKID)
            adjvalue = 0
            if self.domoticzdb_DeviceStatus:
                from Classes.DomoticzDB import DomoticzDB_DeviceStatus
                adjvalue = round(self.domoticzdb_DeviceStatus.retreiveAddjValue_temp( Devices[DeviceUnit].ID),1)
            loggingWidget( self, "Debug", "------> Adj Value : %s from: %s to %s " %(adjvalue, value, (value+adjvalue)), NWKID)
            CurrentnValue = Devices[DeviceUnit].nValue
            CurrentsValue = Devices[DeviceUnit].sValue
            if CurrentsValue == '':
                # First time after device creation
                CurrentsValue = "0;0;0;0;0"
            SplitData = CurrentsValue.split(";")
            NewNvalue = 0
            NewSvalue = ''
            if WidgetType == "Temp":
                NewNvalue = round(value + adjvalue,1)
                NewSvalue = str(round(value + adjvalue,1))
                loggingWidget( self, "Debug", "------>  Temp update: %s - %s" %(NewNvalue, NewSvalue))
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum":
                NewNvalue = 0
                NewSvalue = '%s;%s;%s' %(round(value + adjvalue,1), SplitData[1], SplitData[2])
                loggingWidget( self, "Debug", "------>  Temp+Hum update: %s - %s" %(NewNvalue, NewSvalue))
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum+Baro":  # temp+hum+Baro xiaomi
                NewNvalue = 0
                NewSvalue = '%s;%s;%s;%s;%s' %(round(value + adjvalue,1), SplitData[1], SplitData[2], SplitData[3], SplitData[4])
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

        if ClusterType == 'Humi' and WidgetType in ( 'Humi', 'Temp+Hum', 'Temp+Hum+Baro'):  # humidite
            loggingWidget( self, "Debug", "------>  Humi: %s, WidgetType: >%s<" %(value,WidgetType), NWKID)
            CurrentnValue = Devices[DeviceUnit].nValue
            CurrentsValue = Devices[DeviceUnit].sValue
            if CurrentsValue == '':
                # First time after device creation
                CurrentsValue = "0;0;0;0;0"
            SplitData = CurrentsValue.split(";")
            NewNvalue = 0
            NewSvalue = ''
            # Humidity Status
            if value < 40:
                humiStatus = 2
            elif 40 <= value < 70:
                humiStatus = 1
            else:
                humiStatus = 3

            if WidgetType == "Humi":
                NewNvalue = value
                NewSvalue = "%s" %humiStatus
                loggingWidget( self, "Debug", "------>  Humi update: %s - %s" %(NewNvalue, NewSvalue))
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum":  # temp+hum xiaomi
                NewNvalue = 0
                NewSvalue = '%s;%s;%s' % (SplitData[0], value, humiStatus)
                loggingWidget( self, "Debug", "------>  Temp+Hum update: %s - %s" %(NewNvalue, NewSvalue))
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum+Baro":  # temp+hum+Baro xiaomi
                NewNvalue = 0
                NewSvalue = '%s;%s;%s;%s;%s' % (SplitData[0], value, humiStatus, SplitData[3], SplitData[4])
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

        if ClusterType == 'Baro' and WidgetType in ( 'Baro', 'Temp+Hum+Baro'):  # barometre
            loggingWidget( self, "Debug", "------>  Baro: %s, WidgetType: %s" %(value,WidgetType), NWKID)
            adjvalue = 0
            if self.domoticzdb_DeviceStatus:
                from Classes.DomoticzDB import DomoticzDB_DeviceStatus
                adjvalue = round(self.domoticzdb_DeviceStatus.retreiveAddjValue_baro( Devices[DeviceUnit].ID),1)
            baroValue = round( (value + adjvalue), 1)
            loggingWidget( self, "Debug", "------> Adj Value : %s from: %s to %s " %(adjvalue, value, baroValue), NWKID)

            CurrentnValue = Devices[DeviceUnit].nValue
            CurrentsValue = Devices[DeviceUnit].sValue
            if CurrentsValue == '':
                # First time after device creation
                CurrentsValue = "0;0;0;0;0"
            SplitData = CurrentsValue.split(";")
            NewNvalue = 0
            NewSvalue = ''

            if baroValue < 1000:
                Bar_forecast = 4 # RAIN
            elif baroValue < 1020:
                Bar_forecast = 3 # CLOUDY
            elif baroValue < 1030:
                Bar_forecast = 2 # PARTLY CLOUDY
            else:
                Bar_forecast = 1 # SUNNY

            if WidgetType == "Baro":
                NewSvalue = '%s;%s' %(baroValue, Bar_forecast)
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif WidgetType == "Temp+Hum+Baro":
                NewSvalue = '%s;%s;%s;%s;%s' % (SplitData[0], SplitData[1], SplitData[2], baroValue, Bar_forecast)
                UpdateDevice_v2(self, Devices, DeviceUnit, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

        if 'BSO-Orientation' in ClusterType: # 0xfc21 Not fully tested / So far developped for Profalux
            # value is str
            if WidgetType == "BSO-Orientation":
                # Receveive Level (orientation) in degrees to convert into % for the slider
                # Translate the Angle into Selector item
                selector = int(value)  + 10
                nValue = selector // 10
                sValue = str(selector)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

        if ClusterType in ( 'Alarm', 'Door', 'Switch', 'SwitchButton', 'AqaraOppleMiddle', 'Motion', 
                            'Ikea_Round_5b', 'Ikea_Round_OnOff', 'Vibration', 'OrviboRemoteSquare', 'Button_3'): # Plug, Door, Switch, Button ...
            # We reach this point because ClusterType is Door or Switch. It means that Cluster 0x0006 or 0x0500
            # So we might also have to manage case where we receive a On or Off for a LvlControl WidgetType like a dimming Bulb.
            loggingWidget( self, "Debug", "------> Generic Widget for %s ClusterType: %s WidgetType: %s Value: %s" %(NWKID, WidgetType, ClusterType , value), NWKID)
            
            AutoUpdate = False
            if WidgetType in SWITCH_LVL_MATRIX:
                if value in SWITCH_LVL_MATRIX[ WidgetType ]:
                    AutoUpdate = True
                    
            if AutoUpdate:
                if len(SWITCH_LVL_MATRIX[ WidgetType ][ value] ) == 2:
                    nValue, sValue = SWITCH_LVL_MATRIX[ WidgetType ][ value ]
                    _ForceUpdate =  SWITCH_LVL_MATRIX[ WidgetType ]['ForceUpdate']
                    loggingWidget( self, "Debug", "------> Switch update WidgetType: %s with %s" %(WidgetType, str(SWITCH_LVL_MATRIX[ WidgetType ])), NWKID)
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_= _ForceUpdate) 
                else:
                    loggingWidget( self, "Error", "------>  len(SWITCH_LVL_MATRIX[ %s ][ %s ]) == %s" %(WidgetType,value, len(SWITCH_LVL_MATRIX[ WidgetType ])), NWKID ) 

            elif WidgetType == "DSwitch":
                # double switch avec EP different 
                value = int(value)
                if value == 1 or value == 0:
                    if Ep == "01":
                        nValue = 1
                        sValue = '10'
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

                    elif Ep == "02":
                        nValue = 2
                        sValue = '20'
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

                    elif Ep == "03":
                        nValue = 3
                        sValue = '30'
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == "DButton":
                # double bouttons avec EP different lumi.sensor_86sw2 
                value = int(value)
                if value == 1:
                    if Ep == "01":
                        nValue = 1
                        sValue = '10'
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

                    elif Ep == "02":
                        nValue = 2
                        sValue = '20'
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

                    elif Ep == "03":
                        nValue = 3
                        sValue = '30'
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == "DButton_3":
                # double bouttons avec EP different lumi.sensor_86sw2 
                value = int(value)
                data = '00'
                state = '00'
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

                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel,ForceUpdate_=True)
                                        
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

                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel,ForceUpdate_=True)
                                        
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

                    UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel,ForceUpdate_=True)
                                        
            elif WidgetType == "LvlControl" or WidgetType in ( 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl'):
                if Devices[DeviceUnit].SwitchType in (13,14,15,16):
                    # Required Numeric value
                    if value == "00":
                        UpdateDevice_v2(self, Devices, DeviceUnit, 0, '0', BatteryLevel, SignalLevel)

                    else:
                        # We are in the case of a Shutter/Blind inverse. If we receieve a Read Attribute telling it is On, great
                        # We only update if the shutter was off before, otherwise we will keep its Level.
                        if Devices[DeviceUnit].nValue == 0 and Devices[DeviceUnit].sValue == 'Off':
                            UpdateDevice_v2(self, Devices, DeviceUnit, 1, '100', BatteryLevel, SignalLevel)
                else:
                    # Required Off and On
                    if value == "00":
                        UpdateDevice_v2(self, Devices, DeviceUnit, 0, 'Off', BatteryLevel, SignalLevel)

                    else:
                        if Devices[DeviceUnit].sValue == "Off":
                            # We do update only if this is a On/off
                            UpdateDevice_v2(self, Devices, DeviceUnit, 1, 'On', BatteryLevel, SignalLevel)
            
            else:
                loggingWidget( self, "Error", "------>  [%s:%s] WidgetType: %s not found in  SWITCH_LVL_MATRIX, ClusterType: %s Value: %s " 
                    %( NWKID, Ep, WidgetType, ClusterType, value), NWKID )

        if 'WindowCovering' in ClusterType: # 0x0102
            if WidgetType in ( 'VenetianInverted', 'Venetian', 'WindowCovering'):
                value = int(value,16)
                loggingWidget( self, "Debug", "------>  %s/%s Updating %s Value: %s" %(NWKID, Ep, WidgetType,value), NWKID)

                if WidgetType == "VenetianInverted":
                    value = 100 - value
                    loggingWidget( self, "Debug", "------>  Patching %s/%s Value: %s" %(NWKID, Ep,value), NWKID)

                if value == 0: 
                    nValue = 0

                elif value == 100: 
                    nValue = 1

                else: 
                    nValue = 2

                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(value), BatteryLevel, SignalLevel)

        if 'LvlControl' in ClusterType: # LvlControl ( 0x0008)
            if WidgetType == 'LvlControl' or WidgetType == 'BSO-Volet':
                # We need to handle the case, where we get an update from a Read Attribute or a Reporting message
                # We might get a Level, but the device is still Off and we shouldn't make it On .
                nValue = None

                # Normalize sValue vs. analog value coomming from a ReadATtribute
                analogValue = int(value, 16)

                loggingWidget( self, "Debug", "------>  LvlControl analogValue: -> %s" %analogValue, NWKID)
                if analogValue >= 255:
                    sValue = 100

                else:
                    sValue = round( ((int(value, 16) * 100) / 255))
                    if sValue > 100: 
                        sValue = 100

                    if sValue == 0 and analogValue > 0:
                        sValue = 1

                    # Looks like in the case of the Profalux shutter, we never get 0 or 100
                    if Devices[DeviceUnit].SwitchType in (13,14,15,16):
                        if sValue == 1 and analogValue == 1:
                            sValue = 0
                        if sValue == 99 and analogValue == 254:
                            sValue = 100

                loggingWidget( self, "Debug", "------>  LvlControl sValue: -> %s" %sValue, NWKID)

                # In case we reach 0% or 100% we shouldn't switch Off or On, except in the case of Shutter/Blind
                if sValue == 0:
                    nValue = 0
                    if Devices[DeviceUnit].SwitchType in (13,14,15,16):
                        loggingWidget( self, "Debug", "------>  LvlControl UpdateDevice: -> %s/%s SwitchType: %s" %(0,0, Devices[DeviceUnit].SwitchType), NWKID)
                        UpdateDevice_v2(self, Devices, DeviceUnit, 0, '0', BatteryLevel, SignalLevel)
                    else:
                        if Devices[DeviceUnit].nValue == 0 and Devices[DeviceUnit].sValue == 'Off':
                            pass

                        else:
                            #UpdateDevice_v2(Devices, DeviceUnit, 0, 'Off', BatteryLevel, SignalLevel)
                            loggingWidget( self, "Debug", "------>  LvlControl UpdateDevice: -> %s/%s" %(0,0), NWKID)
                            UpdateDevice_v2(self, Devices, DeviceUnit, 0, '0', BatteryLevel, SignalLevel)

                elif sValue == 100:
                    nValue = 1
                    if Devices[DeviceUnit].SwitchType in (13,14,15,16):
                        loggingWidget( self, "Debug", "------>  LvlControl UpdateDevice: -> %s/%s SwitchType: %s" %(1,100, Devices[DeviceUnit].SwitchType), NWKID)
                        UpdateDevice_v2(self, Devices, DeviceUnit, 1, '100', BatteryLevel, SignalLevel)

                    else:
                        if Devices[DeviceUnit].nValue == 0 and Devices[DeviceUnit].sValue == 'Off':
                            pass
                        else:
                            #UpdateDevice_v2(Devices, DeviceUnit, 1, 'On', BatteryLevel, SignalLevel)
                            loggingWidget( self, "Debug", "------>  LvlControl UpdateDevice: -> %s/%s" %(1,100), NWKID)
                            UpdateDevice_v2(self, Devices, DeviceUnit, 1, '100', BatteryLevel, SignalLevel)

                else: # sValue != 0 and sValue != 100
                    if Devices[DeviceUnit].nValue == 0 and Devices[DeviceUnit].sValue == 'Off':
                        # Do nothing. We receive a ReadAttribute  giving the position of a Off device.
                        pass
                    elif Devices[DeviceUnit].SwitchType in (13,14,15,16):
                        loggingWidget( self, "Debug", "------>  LvlControl UpdateDevice: -> %s/%s SwitchType: %s" %(nValue,sValue, Devices[DeviceUnit].SwitchType), NWKID)
                        UpdateDevice_v2(self, Devices, DeviceUnit, 2, str(sValue), BatteryLevel, SignalLevel)

                    else:
                        loggingWidget( self, "Debug", "------>  LvlControl UpdateDevice: -> %s/%s SwitchType: %s" %(nValue,sValue, Devices[DeviceUnit].SwitchType), NWKID)
                        UpdateDevice_v2(self, Devices, DeviceUnit, 1, str(sValue), BatteryLevel, SignalLevel)

            elif WidgetType  in ( 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl'):
                if Devices[DeviceUnit].nValue != 0 or Devices[DeviceUnit].sValue != 'Off':
                    nValue, sValue = getDimmerLevelOfColor( self,  value)
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(sValue), BatteryLevel, SignalLevel, Color_)

            elif WidgetType == 'LegrandSelector':
                loggingWidget( self, "Debug", "------> LegrandSelector : Value -> %s" %value, NWKID)
                if value == '00': 
                    nValue = 0 
                    sValue = '00' #Off
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                elif value == '01': 
                    nValue = 1 
                    sValue = "10" # On
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                elif value == 'moveup': 
                    nValue = 2 
                    sValue = "20" # Move Up
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                elif value == 'movedown': 
                    nValue = 3 
                    sValue = "30" # Move Down
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                elif value == 'stop': 
                    nValue = 4 
                    sValue = "40" # Stop
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                else:
                    Domoticz.Error("------>  %s LegrandSelector Unknown value %s" %(NWKID, value))         

            elif WidgetType == 'Generic_5_buttons':
                loggingWidget( self, "Debug", "------> Generic 5 buttons : Value -> %s" %value, NWKID)
                nvalue = 0
                state = '00'
                if value == '00': 
                    nvalue = 0
                    sValue = '00'

                elif value == '01': 
                    nvalue = 1
                    sValue = '10'

                elif value == '02': 
                    nvalue = 2
                    sValue = '20'

                elif value == '03': 
                    nvalue = 3
                    sValue = '30'

                elif value == '04': 
                    nvalue = 4
                    sValue = '40'

                UpdateDevice_v2(self, Devices, DeviceUnit, nvalue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == 'GenericLvlControl':
                # 1,10: Off
                # 2,20: On
                # 3,30: Move Up
                # 4,40: Move Down
                # 5,50: Stop
                loggingWidget( self, "Debug", "------> GenericLvlControl : Value -> %s" %value, NWKID)
                if value == 'off': 
                    nvalue = 1
                    sValue = '10' #Off

                elif value == 'on': 
                    nvalue = 2
                    sValue = "20" # On

                elif value == 'moveup': 
                    nvalue = 3
                    sValue = "30" # Move Up

                elif value == 'movedown': 
                    nvalue = 4
                    sValue = "40" # Move Down

                elif value == 'stop': 
                    nvalue = 5
                    sValue = "50" # Stop

                UpdateDevice_v2(self, Devices, DeviceUnit, nvalue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif WidgetType == "INNR_RC110_SCENE":
                loggingWidget( self, "Debug", "------>  Updating INNR_RC110_SCENE (LvlControl) Value: %s" %value, NWKID)
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

                sValue = "%s" %(10 * nValue)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

            elif WidgetType == 'INNR_RC110_LIGHT':
                loggingWidget( self, "Debug", "------>  Updating INNR_RC110_LIGHT (LvlControl) Value: %s" %value, NWKID)
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

                sValue = "%s" %(10 * nValue)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel)

        if ClusterType in ( 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl'):
            # We just manage the update of the Dimmer (Control Level)       
            if ClusterType == WidgetType:
                nValue, sValue = getDimmerLevelOfColor( self, value)
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, str(sValue), BatteryLevel, SignalLevel, Color_)

        if 'XCube' in ClusterType: # XCube Aqara or Xcube
            if WidgetType == "Aqara":
                loggingWidget( self, "Debug", "-------->  XCube Aqara Ep: %s Attribute_: %s Value: %s = " 
                    %( Ep, Attribute_, value ), NWKID)
                if Ep == "02" and Attribute_ == '':  # Magic Cube Aqara
                    loggingWidget( self, "Debug", "---------->  XCube update device with data = " + str(value), NWKID)
                    nValue = int(value)
                    sValue = value
                    UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_ = True)

                elif Ep == "03":  # Magic Cube Aqara Rotation
                    if Attribute_ == '0055': # Rotation Angle
                        loggingWidget( self, "Debug", "---------->  XCube update Rotaion Angle with data = " + str(value), NWKID)
                        # Update Text widget ( unit + 1 )
                        nValue = 0
                        sValue = value
                        UpdateDevice_v2(self, Devices, DeviceUnit + 1, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_ = True)

                    else:
                        loggingWidget( self, "Debug", "---------->  XCube update  with data = " + str(value), NWKID)
                        nValue = int(value)
                        sValue =  value
                        if nValue == 80:
                            nValue = 8

                        elif nValue == 90:
                            nValue = 9

                        loggingWidget( self, "Debug", "-------->  XCube update device with data = %s , nValue: %s sValue: %s" %(value, nValue, sValue), NWKID)
                        UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_ = True)

            elif WidgetType == "XCube" and Ep == "02":  # cube xiaomi
                if value == "0000":  # shake
                     state = "10"
                     data = "01"
                     UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)

                elif value in ( "0204", "0200", "0203", "0201", "0202", "0205" ):
                     state = "50"
                     data = "05"
                     UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)

                elif value in ( "0103", "0100", "0104", "0101", "0102", "0105"): # Slide/M%ove
                     state = "20"
                     data = "02"
                     UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)

                elif value == "0003":  # Free Fall
                     state = "70"
                     data = "07"
                     UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)

                elif "0004" <= value <= "0059":  # 90°
                     state = "30"
                     data = "03"
                     UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)

                elif value >= "0060":  # 180°
                     state = "90"
                     data = "09"
                     UpdateDevice_v2(self, Devices, DeviceUnit, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)

        if 'Orientation' in ClusterType:
            # Xiaomi Vibration
            if WidgetType == "Orientation":
                #value is a str containing all Orientation information to be updated on Text Widget
                nValue = 0
                sValue = value
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_ = True)

        if 'Strenght' in ClusterType:
            if WidgetType == "Strength":
                #value is a str containing all Orientation information to be updated on Text Widget
                nValue = 0
                sValue = value
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_ = True)

        if 'Lux' in ClusterType:
            if WidgetType == "Lux":
                nValue = int(value)
                sValue = value
                UpdateDevice_v2(self, Devices, DeviceUnit, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_= True)

        # Check if this Device belongs to a Group. In that case update group
        CheckUpdateGroup( self, NWKID, Ep,  clusterID )