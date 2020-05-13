#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: domoCreat.py
    Description: Creation of Domoticz Widgets
"""

import json
import time

import Domoticz

from Modules.logging import loggingWidget
from Modules.zigateConsts import THERMOSTAT_MODE_2_LEVEL
from Modules.widgets import SWITCH_LVL_MATRIX
from Modules.domoTools import GetType, subtypeRGB_FromProfile_Device_IDs

def CreateDomoDevice(self, Devices, NWKID):
    """
    CreateDomoDevice

    Create Domoticz Device accordingly to the Type.

    """

    def deviceName( self, NWKID, DeviceType, IEEE_, EP_ ):
        """
        Return the Name of device to be created
        """

        _Model = _NickName = None
        devName = ''
        loggingWidget( self, "Debug", "deviceName - %s/%s - %s %s" %(NWKID, EP_, IEEE_, DeviceType), NWKID)
        if 'Model' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Model'] != {}:
                _Model = self.ListOfDevices[NWKID]['Model']
                loggingWidget( self, "Debug", "deviceName - Model found: %s" %_Model, NWKID)
                if _Model in self.DeviceConf:
                    if 'NickName' in self.DeviceConf[_Model]:
                        _NickName = self.DeviceConf[_Model]['NickName']
                        loggingWidget( self, "Debug", "deviceName - NickName found %s" %_NickName, NWKID)

        if _NickName is None and _Model is None:
            _Model = ''
        elif _NickName:
            devName = _NickName + '_'
        elif _Model:
            devName = _Model+ '_'

        devName +=  DeviceType + "-" + IEEE_ + "-" + EP_
        loggingWidget( self, "Debug", "deviceName - Dev Name: %s" %devName, NWKID)

        return devName

    def FreeUnit(self, Devices, nbunit_=1):
        '''
        FreeUnit
        Look for a Free Unit number. If nbunit > 1 then we look for nbunit consecutive slots
        '''
        FreeUnit = ""
        for x in range(1, 255):
            if x not in Devices:
                if nbunit_ == 1:
                    return x
                nb = 1
                for y in range(x+1, 255):
                    if y not in Devices:
                        nb += 1
                    else: 
                        break
                    if nb == nbunit_: # We have found nbunit consecutive slots
                        loggingWidget( self, "Debug", "FreeUnit - device " + str(x) + " available")
                        return x

        else:
            loggingWidget( self, "Debug", "FreeUnit - device " + str(len(Devices) + 1))
            return len(Devices) + 1

    def createSwitchSelector( nbSelector, DeviceType= None, OffHidden = False, SelectorStyle = 0 ):
        """
        Generate an Options attribute to handle the number of required button, if Off is hidden or notand SelectorStype

        Options = {"LevelActions": "|||", 
                    "LevelNames": "1 Click|2 Clicks|3 Clicks|4+ Clicks",
                    "LevelOffHidden": "false", "SelectorStyle": "1"}
        """

        Options = {}
        #Domoticz.Log( "createSwitchSelector -  nbSelector: %s DeviceType: %s OffHidden: %s SelectorStyle %s " %(nbSelector,DeviceType,OffHidden,SelectorStyle))
        if nbSelector <= 1:
            return Options
            
        Options[ 'LevelNames' ] = ''
        Options[ 'LevelActions'] = ''
        Options[ 'LevelOffHidden'] = 'false'
        Options[ 'SelectorStyle'] = '0'

        if DeviceType:
            if DeviceType in SWITCH_LVL_MATRIX:
                # In all cases let's populate with the Standard LevelNames
                if 'LevelNames' in SWITCH_LVL_MATRIX[ DeviceType ]:
                    Options[ 'LevelNames' ] = SWITCH_LVL_MATRIX[ DeviceType ]['LevelNames']

                # In case we have a localized version, we will overwrite the standard vesion
                if self.pluginconf.pluginConf['Lang'] != 'en-US':
                    lang = self.pluginconf.pluginConf['Lang']
                    if 'Language' in SWITCH_LVL_MATRIX[ DeviceType ]:
                        if lang in SWITCH_LVL_MATRIX[ DeviceType ]['Language']:
                            if 'LevelNames' in SWITCH_LVL_MATRIX[ DeviceType ]['Language'][ lang ]:
                                Options[ 'LevelNames'] = SWITCH_LVL_MATRIX[ DeviceType ]['Language'][ lang ]['LevelNames']

                if Options[ 'LevelNames' ] != '':
                    count = sum(map(lambda x : 1 if '|' in x else 0, Options[ 'LevelNames' ]))
                    #Domoticz.Log("----> How many Levels: %s" %count)
                    for bt in range(0, count):
                        Options[ 'LevelActions'] += '|'
        else:
            for bt in range(0, nbSelector):
                Options[ 'LevelNames' ] += 'BT %03s | ' %bt
                Options[ 'LevelActions'] += '|'
    
            #Domoticz.Log(" --> Options: %s" %str(Options))  

            Options[ 'LevelNames' ] = Options[ 'LevelNames' ][:-2] # Remove the last '| '
            Options[ 'LevelActions' ] = Options[ 'LevelActions' ][:-1] # Remove the last '|'

        if SelectorStyle:
            Options[ 'SelectorStyle'] = '%s' %SelectorStyle

        if OffHidden:
            Options[ 'LevelOffHidden'] = 'true'

        #Domoticz.Log(" --> Options: %s" %str(Options))
        return Options


    def createDomoticzWidget( self, Devices, nwkid, ieee, ep, cType, 
                                widgetType = None, Type_ = None, Subtype_ = None, Switchtype_ = None, 
                                widgetOptions = None, 
                                Image = None,
                                ForceClusterType = None):
        """
        widgetType are pre-defined widget Type
        Type_, Subtype_ and Switchtype_ allow to create a widget ( Switchtype_ is optional )
        Image is an optional parameter
        forceClusterType if you want to overwrite the ClusterType usally based with cType
        """

        unit = FreeUnit(self, Devices)
        loggingWidget( self, "Debug", "CreateDomoDevice - unit: %s" %unit, nwkid)
        
        loggingWidget( self, "Debug", "--- cType: %s widgetType: %s Type: %s Subtype: %s SwitchType: %s widgetOption: %s Image: %s ForceCluster: %s" \
            %(cType, widgetType , Type_ , Subtype_, Switchtype_ , widgetOptions , Image ,ForceClusterType), nwkid)
     
        widgetName = deviceName( self, nwkid, cType, ieee, ep)
        #oldFashionWidgetName = cType + "-" + ieee + "-" + ep

        if widgetType:
            # We only base the creation on widgetType
            myDev = Domoticz.Device( DeviceID = ieee, Name = widgetName, Unit = unit, TypeName = widgetType ) 

        elif widgetOptions:
            # In case of widgetOptions, we have a Selector widget
            Type_ = 244
            Subtype_ = 62
            Switchtype_ = 18
            myDev = Domoticz.Device( DeviceID = ieee, Name = widgetName, Unit = unit, 
                                        Type = Type_, Subtype = Subtype_, Switchtype = Switchtype_, 
                                        Options = widgetOptions )
        elif Image:
            myDev = Domoticz.Device( DeviceID = ieee, Name = widgetName, Unit = unit, 
                                        Type = Type_, Subtype = Subtype_, Switchtype = Switchtype_, Image= Image )       
        elif Switchtype_:
            myDev = Domoticz.Device( DeviceID = ieee, Name = widgetName, Unit = unit, 
                                        Type = Type_, Subtype = Subtype_, Switchtype = Switchtype_ )      
        else:
            myDev = Domoticz.Device( DeviceID = ieee, Name = widgetName, Unit = unit, 
                                        Type = Type_, Subtype = Subtype_ )   
 
        myDev.Create()
        ID = myDev.ID
        if myDev.ID == -1 :
            self.ListOfDevices[nwkid]['Status'] = "failDB"
            Domoticz.Error("Domoticz widget creation failed. Check that Domoticz can Accept New Hardware [%s]" %myDev )
        else:
            self.ListOfDevices[nwkid]['Status'] = "inDB"
            if ForceClusterType:
                self.ListOfDevices[nwkid]['Ep'][ep]['ClusterType'][str(ID)] = ForceClusterType
            else:
                self.ListOfDevices[nwkid]['Ep'][ep]['ClusterType'][str(ID)] = cType

 

    # Sanity check before starting the processing 
    if NWKID == '' or NWKID not in self.ListOfDevices:
        Domoticz.Error("CreateDomoDevice - Cannot create a Device without an IEEE or not in ListOfDevice .")
        return

    DeviceID_IEEE = self.ListOfDevices[NWKID]['IEEE']

    # When Type is at Global level, then we create all Type against the 1st EP
    # If Type needs to be associated to EP, then it must be at EP level and nothing at Global level
    GlobalEP = False
    GlobalType = []

    loggingWidget( self, "Debug", "CreatDomoDevice - Ep to be processed : %s " %self.ListOfDevices[NWKID]['Ep'].keys(), NWKID)
    for Ep in self.ListOfDevices[NWKID]['Ep']:
        dType = aType = Type = ''
        # Use 'type' at level EndPoint if existe
        loggingWidget( self, "Debug", "CreatDomoDevice - Process EP : " + str(Ep), NWKID)
        if GlobalEP:
            # We have created already the Devices (as GlobalEP is set)
            break

        # First time, or we dont't GlobalType
        if 'Type' in self.ListOfDevices[NWKID]['Ep'][Ep]:
            if self.ListOfDevices[NWKID]['Ep'][Ep]['Type'] != '':
                dType = self.ListOfDevices[NWKID]['Ep'][Ep]['Type']
                aType = str(dType)
                Type = aType.split("/")
                loggingWidget( self, "Debug", "CreateDomoDevice - Type via ListOfDevice: " + str(Type) + " Ep : " + str(Ep), NWKID)
            else:
                Type = GetType(self, NWKID, Ep).split("/")
                loggingWidget( self, "Debug", "CreateDomoDevice - Type via GetType: " + str(Type) + " Ep : " + str(Ep), NWKID)

        else:
            if self.ListOfDevices[NWKID]['Type'] == {} or self.ListOfDevices[NWKID]['Type'] == '':
                Type = GetType(self, NWKID, Ep).split("/")
                loggingWidget( self, "Debug", "CreateDomoDevice - Type via GetType: " + str(Type) + " Ep : " + str(Ep), NWKID)
            else:
                GlobalEP = True
                if 'Type' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Type'] != '':
                        Type = self.ListOfDevices[NWKID]['Type'].split("/")
                        loggingWidget( self, "Debug", "CreateDomoDevice - Type : '" + str(Type) + "'", NWKID)

        # Check if Type is known
        if len(Type) == 1 and Type[0] == '':
            continue

        for iterType in Type:
            if iterType not in GlobalType and iterType != '': 
                loggingWidget( self, "Debug", "adding Type : %s to Global Type: %s" %(iterType, str(GlobalType)), NWKID)
                GlobalType.append(iterType)

        # In case the Type has been autoamticaly detected based on Cluster, we might several times the same actuator
        # Precendece is Swicth -> LvlControl -> ColorControl
        if self.ListOfDevices[NWKID]['Model'] == {} or \
                self.ListOfDevices[NWKID][ 'Model'] not in self.DeviceConf:    # If Model is known, then Type must be set correctly
            if ("Switch" in Type) and ("LvlControl" in Type):
                Type = ['LvlControl']
                if 'ColorControl' in Type or 'ColorControlRGB' in Type or \
                    'ColorControlWW' in Type or 'ColorControlRGBWW' in Type or \
                    'ColorControlFull' in Type or 'ColorControl' in Type :
                        Type = ['ColorControl']

        loggingWidget( self, "Debug", "CreateDomoDevice - Creating devices based on Type: %s" % Type, NWKID)

        if 'ClusterType' not in self.ListOfDevices[NWKID]['Ep'][Ep]:
            self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'] = {}

        if "Humi" in Type and "Temp" in Type and "Baro" in Type:
             # Detecteur temp + Hum + Baro
            createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, "Temp+Hum+Baro", "Temp+Hum+Baro")
            loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Humi and Temp and Baro" %(Type), NWKID)

        if "Humi" in Type and "Temp" in Type:
            # Temp + Hum
            createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, "Temp+Hum", "Temp+Hum")
            loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Humi and Temp" %(Type), NWKID)

        for t in Type:
            loggingWidget( self, "Debug", "CreateDomoDevice - DevId: %s DevEp: %s Type: %s" %(DeviceID_IEEE, Ep, t), NWKID)

            # === Selector Switches

            # 3 Selectors, Style 0
            if t == "Toggle": 
                Options = createSwitchSelector( 3 , DeviceType = t, SelectorStyle = 0)
                createDomoticzWidget( self, subtypeRGB_FromProfile_Device_IDs, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Toggle" %(t), NWKID)

            # 3 Selector , OffHidden, Style 0 (command)
            if t in ('HACTMODE', ):
                Options = createSwitchSelector( 3, DeviceType = t, OffHidden = True, SelectorStyle = 0 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in HACTMODE..." %(t), NWKID)

            # 4 Selector , OffHidden, Style 0 (command)
            if t in ('DSwitch',):
                Options = createSwitchSelector( 4, DeviceType = t, OffHidden = True, SelectorStyle = 0 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in DSwitch..." %(t), NWKID)

            # 5 Selector , OffHidden, Style 0 (command)
            if t in ('ContractPower', ):
                Options = createSwitchSelector( 6, DeviceType = t, OffHidden = True, SelectorStyle = 0 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in ContractPower ..." %(t), NWKID)

            # 4 Selectors, OffHidden, Style 1
            if t in ('DButton', ):  
                Options = createSwitchSelector( 4, DeviceType = t, OffHidden= True, SelectorStyle = 1 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in DButton" %(t), NWKID)

            # 4 Selectors, Style 1  
            if t in ('Vibration', 'Button_3' , 'SwitchAQ2'):  
                Options = createSwitchSelector( 4, DeviceType = t, SelectorStyle = 1 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Vibration" %(t), NWKID)

            # 5 Selectors, Style 0 ( mode command)
            if t in ('ThermoMode', ):
                Options = createSwitchSelector( 5,  DeviceType = t,SelectorStyle = 0 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in ThermoMode" %(t), NWKID)

            # 5 Selectors, Style 1
            if t in ('Generic_5_buttons', 'LegrandSelector', 'SwitchAQ3', 'SwitchIKEA', 'AqaraOppleMiddleBulb'): 
                Options = createSwitchSelector( 5,  DeviceType = t,SelectorStyle = 1 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Generic_5" %(t), NWKID)

            # 6 Selectors, Style 1
            if t in ('AlarmWD', ):        
                Options = createSwitchSelector( 6,  DeviceType = t,SelectorStyle = 1 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in AlarmWD" %(t), NWKID)

            # 6 Buttons, Style 1, OffHidden
            if t in ('GenericLvlControl', 'AqaraOppleMiddle'): 
            
               Options = createSwitchSelector( 6,  DeviceType = t,OffHidden= True, SelectorStyle = 1 )
               createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
               loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in GenericLvlControl" %(t), NWKID)
            
            # 7 Selectors, Style 1
            if t in ('ThermoModeEHZBRTS', 'INNR_RC110_LIGHT'):             
                Options = createSwitchSelector( 7,  DeviceType = t,SelectorStyle = 1 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t,widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in ThermoModeEHZBRTS" %(t), NWKID)

            # 7 Selectors, Style 0, OffHidden
            if t in ('FIP', 'LegrandFilPilote' ):             
               Options = createSwitchSelector( 7,  DeviceType = t,OffHidden = True, SelectorStyle = 0 )
               createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
               loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in FIP" %(t), NWKID)

            # 10 Selectors, Style 1, OffHidden
            if t in ('DButton_3', ):  
               Options = createSwitchSelector( 10,  DeviceType = t,OffHidden = True, SelectorStyle = 1 )
               createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
               loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in DButton3" %(t), NWKID) 

            # 12 Selectors
            if t in ( 'OrviboRemoteSquare'):
                Options = createSwitchSelector( 13,  DeviceType = t,OffHidden = True, SelectorStyle = 1 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)                 

            # 13 Selectors, Style 1
            if t in ('INNR_RC110_SCENE', ):
                Options = createSwitchSelector( 13,  DeviceType = t,SelectorStyle = 1 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in INNR SCENE" %(t), NWKID)

            # 14 Selectors, Style 1
            if t in ('Ikea_Round_5b', ): 
                Options = createSwitchSelector( 14,  DeviceType = t,SelectorStyle = 1 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Ikea Round" %(t), NWKID)

            # ==== Classic Widget
            if t in ( 'Alarm', ):
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 243, Subtype_ = 22, Switchtype_= 0) 
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Alarm" %(t), NWKID)

            if t in ( "ThermoSetpoint", "TempSetCurrent"):
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 242, Subtype_ = 1)  
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in ThermoSetPoint" %(t), NWKID)
               
            if t == "Temp":
                # Detecteur temp
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, "Temperature")
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Temp" %(t), NWKID)

            if t == "Humi":  
                # Detecteur hum
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, "Humidity")
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Humidity" %(t), NWKID)

            if t == "Baro":  
                # Detecteur Baro
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, "Barometer")
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Barometer" %(t), NWKID)

            if t == "Power":  
               # Will display Watt real time
               createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, "Usage")
               loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Power" %(t), NWKID)

            if t == "Meter":  
               # Will display kWh
               createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, "kWh") 
               loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Meter" %(t), NWKID)

            if t == "Voltage":  
               # Voltage
               createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, "Voltage")
               loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Voltage" %(t), NWKID)                 

            if t == "Door":  
                # capteur ouverture/fermeture xiaomi
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 11 )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Door" %(t), NWKID)

            if t == "Motion":  
                # detecteur de presence
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 8 )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Motion" %(t), NWKID)

            if t in ( "LivoloSWL", "LivoloSWR" ):
                # Livolo Switch Left and Right
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 0 )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Livolo" %(t), NWKID)

            if t == "Smoke":  
                # detecteur de fumee
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 5 )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Smoke" %(t), NWKID)

            if t == "Lux":  
                # Lux sensors
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 246, Subtype_ = 1, Switchtype_ = 0 )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Lux" %(t), NWKID)

            if t in ( "Switch", "SwitchButton", "HeatingSwitch"):  
                # inter sans fils 1 touche 86sw1 xiaomi
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 0 )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Switch" %(t), NWKID)

            if t == "Button":  
                # inter sans fils 1 touche 86sw1 xiaomi
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 9 )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Button" %(t), NWKID)

            if t in ( "Aqara", "XCube"): 
                # Do not use the generic createDomoticzWidget , because this one required 2 continuous widget.
                # usage later on is based on that assumption
                #  
                # Xiaomi Magic Cube
                self.ListOfDevices[NWKID]['Status'] = "inDB"
                # Create the XCube Widget
                Options = createSwitchSelector( 10, OffHidden = True, SelectorStyle = 1 )
                unit = FreeUnit(self, Devices, nbunit_=2) # Look for 2 consecutive slots
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=244, Subtype=62, Switchtype=18, Options=Options)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    self.ListOfDevices[NWKID]['Status'] = "failDB"
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = t
                
                # Create the Status (Text) Widget to report Rotation angle
                unit += 1
                myDev = Domoticz.Device(DeviceID=str(DeviceID_IEEE), Name=deviceName( self, NWKID, t, DeviceID_IEEE, Ep), 
                                Unit=unit, Type=243, Subtype=19, Switchtype=0)
                myDev.Create()
                ID = myDev.ID
                if myDev.ID == -1 :
                    Domoticz.Error("Domoticz widget creation failed. %s" %(str(myDev)))
                else:
                    self.ListOfDevices[NWKID]['Ep'][Ep]['ClusterType'][str(ID)] = 'Text'

            if t == "Strength":
                # Vibration strength
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 243, Subtype_ = 31 )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Strenght" %(t), NWKID)

            if t == "Orientation":
                # Vibration Orientation (text)
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 243, Subtype_ = 19 )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Orientation" %(t), NWKID)

            if t == "Water":  
                # detecteur d'eau
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 0, Image = 11 )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Water" %(t), NWKID)

            if t == "Plug":  
                # prise pilote
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 0, Image = 1 )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Plug" %(t), NWKID)

            if t == "P1Meter":
                # P1 Smart Meter Energy Type 250, Subtype = 250
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 250, Subtype_ = 1, Switchtype_ = 1 )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in P1Meter" %(t), NWKID)
 
            # ====== Blind and Venetian
            # Subtype = 
            # Blind / Window covering
            #   13 Blind percentage
            #   16 Blind Percentage Inverted
            # Shade
            #   14 Venetian Blinds US
            #   15 Venetian Blind EU
            if t in ( "VenetianInverted", "Venetian"):
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 15 )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in VenetianInverted" %(t), NWKID)

            if t == 'BSO':
                # BSO for Profalux
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 13 )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in BSO" %(t), NWKID)
            
            if t == 'BlindInverted':
                # Blind Percentage Inverterd
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 16, ForceClusterType = 'LvlControl' )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in BlindInverted" %(t), NWKID)

            if t == 'Blind':
                # Blind Percentage
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 13, ForceClusterType = 'LvlControl' )
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Blind" %(t), NWKID)

            if t == 'WindowCovering':
                # Blind Percentage Inverted
                # or Venetian Blind EU
                if self.ListOfDevices[NWKID]['ProfileID'] == '0104' and self.ListOfDevices[NWKID]['ZDeviceID'] == '0202':
                    createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 16 )
                elif self.ListOfDevices[NWKID]['ProfileID'] == '0104' and self.ListOfDevices[NWKID]['ZDeviceID'] == '0200':
                    createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 15 )
                
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in WindowCovering" %(t), NWKID)

            # ======= Level Control / Dimmer
            if t == 'LvlControl':
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in LvlControl" %(t), NWKID)
                if self.ListOfDevices[NWKID]['Model'] != '' and self.ListOfDevices[NWKID]['Model'] != {} :  
                    loggingWidget( self, "Debug", "---> Shade based on ZDeviceID" , NWKID)
                    # Well Identified Model
                    # variateur de luminosite + On/off
                    createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 7 )

                else:
                    if self.ListOfDevices[NWKID]['ProfileID'] == '0104' and self.ListOfDevices[NWKID]['ZDeviceID'] == '0202':
                        # Windows Covering / Profalux -> Inverted 
                        createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 16 )

                    elif self.ListOfDevices[NWKID]['ProfileID'] == '0104' and self.ListOfDevices[NWKID]['ZDeviceID'] == '0200':
                        # Shade
                        loggingWidget( self, "Debug", "---> Shade based on ZDeviceID" , NWKID)
                        createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 15 )

                    else:
                        # variateur de luminosite + On/off
                        createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 244, Subtype_ = 73, Switchtype_ = 7 )

            # ======= Color Control: RGB, WW, Z or combinaisons
            if t in ( 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl'):
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Colorxxxx" %(t), NWKID)
                # variateur de couleur/luminosite/on-off

                if t == 'ColorControlRGB':     
                    Subtype_ = 0x02 # RGB color palette / Dimable
                elif t == 'ColorControlRGBWW': 
                    Subtype_ = 0x04  # RGB + WW / Dimable
                elif t == 'ColorControlFull':  
                    Subtype_ = 0x07  # 3 Color palettes widget
                elif t == 'ColorControlWW':    
                    Subtype_ = 0x08  # White color palette / Dimable
                else:
                    # Generic ColorControl, let's try to find a better one.
                    if 'ColorInfos' in self.ListOfDevices[NWKID]:
                        Subtype_ = subtypeRGB_FromProfile_Device_IDs( self.ListOfDevices[NWKID]['Ep'], self.ListOfDevices[NWKID]['Model'],
                            self.ListOfDevices[NWKID]['ProfileID'], self.ListOfDevices[NWKID]['ZDeviceID'], self.ListOfDevices[NWKID]['ColorInfos'])
                    else:
                        Subtype_ = subtypeRGB_FromProfile_Device_IDs( self.ListOfDevices[NWKID]['Ep'], self.ListOfDevices[NWKID]['Model'],
                            self.ListOfDevices[NWKID]['ProfileID'], self.ListOfDevices[NWKID]['ZDeviceID'], None)

                    if Subtype_ == 0x02:   
                        t = 'ColorControlRGB'
                    elif Subtype_ == 0x04: 
                        t = 'ColorControlRGBWW'
                    elif Subtype_ == 0x07: 
                        t = 'ColorControlFull'
                    elif Subtype_ == 0x08: 
                        t = 'ColorControlWW'
                    else:                  
                        t = 'ColorControlFull'

                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, Type_ = 241, Subtype_ = Subtype_, Switchtype_ = 7 )


    # for Ep
    loggingWidget( self, "Debug", "GlobalType: %s" %(str(GlobalType)), NWKID)
    if len(GlobalType) != 0:
        self.ListOfDevices[NWKID]['Type'] = ''
        for iterType in GlobalType:
            if self.ListOfDevices[NWKID]['Type'] == '':
                self.ListOfDevices[NWKID]['Type'] = iterType
            else:
                self.ListOfDevices[NWKID]['Type'] = self.ListOfDevices[NWKID]['Type'] + '/' + iterType
        loggingWidget( self, "Debug", "CreatDomoDevice - Set Type to : %s" %self.ListOfDevices[NWKID]['Type'], NWKID)

