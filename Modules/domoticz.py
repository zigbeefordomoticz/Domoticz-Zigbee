#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: domoticz.py
    Description: All interactions with Domoticz database
"""

import json
import time

import Domoticz

from Modules.logging import loggingWidget
from Modules.zigateConsts import THERMOSTAT_MODE_2_LEVEL
from Modules.widgets import SWITCH_LVL_MATRIX

def CreateDomoDevice(self, Devices, NWKID):
    """
    CreateDomoDevice

    Create Domoticz Device accordingly to the Type.

    """

    def deviceName( self, NWKID, type_, IEEE_, EP_ ):
        """
        Return the Name of device to be created
        """

        _Model = _NickName = None
        devName = ''
        loggingWidget( self, "Debug", "deviceName - %s/%s - %s %s" %(NWKID, EP_, IEEE_, type_), NWKID)
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

        devName +=  type_ + "-" + IEEE_ + "-" + EP_
        loggingWidget( self, "Debug", "deviceName - Dev Name: %s" %devName, NWKID)

        return devName

 #   def getCreatedID(self, Devices, DeviceID, Name):
 #       """
 #       getCreateID
 #       Return DeviceID of the recently created device based  on its creation name.
 #       """
 #       # for x in Devices :
 #       #    if Devices[x].DeviceID == DeviceID and Devices[x].Name.find(Name) >= 0 :
 #       #        return Devices[x].ID
 #       return (Devices[x].ID for x in Devices if (Devices[x].DeviceID == DeviceID and Devices[x].Name.find(Name) >= 0))

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
        Domoticz.Log( "createSwitchSelector -  nbSelector: %s DeviceType: %s OffHidden: %s SelectorStyle %s " %(nbSelector,DeviceType,OffHidden,SelectorStyle))
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
    
            Domoticz.Log(" --> Options: %s" %str(Options))  

            Options[ 'LevelNames' ] = Options[ 'LevelNames' ][:-2] # Remove the last '| '
            Options[ 'LevelActions' ] = Options[ 'LevelActions' ][:-1] # Remove the last '|'

        if SelectorStyle:
            Options[ 'SelectorStyle'] = '%s' %SelectorStyle

        if OffHidden:
            Options[ 'LevelOffHidden'] = 'true'

        Domoticz.Log(" --> Options: %s" %str(Options))
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

        return 

    # Sanity check before starting the processing 
    if NWKID == '' or NWKID not in self.ListOfDevices:
        Domoticz.Error("CreateDomoDevice - Cannot create a Device without an IEEE or not in ListOfDevice .")
        return

    DeviceID_IEEE = self.ListOfDevices[NWKID]['IEEE']

    # When Type is at Global level, then we create all Type against the 1st EP
    # If Type needs to be associated to EP, then it must be at EP level and nothing at Global level
    GlobalEP = False
    GlobalType = []
    for Ep in self.ListOfDevices[NWKID]['Ep']:
        dType = aType = Type = ''
        # Use 'type' at level EndPoint if existe
        loggingWidget( self, "Debug", "CreatDomoDevice - Process EP : " + str(Ep), NWKID)
        if not GlobalEP:  # First time, or we dont't GlobalType
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
        else:
            break  # We have created already the Devices (as GlobalEP is set)

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

            # 4 Selector , OffHidden, Style 0 (command)
            if t in ('HACTMODE', 'DSwitch'):
                Options = createSwitchSelector( 4, DeviceType = t, OffHidden = True, SelectorStyle = 0 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in HACTMODE ..." %(t), NWKID)

            # 5 Selector , OffHidden, Style 0 (command)
            if t in ('ContractPower', ):
                Options = createSwitchSelector( 4, DeviceType = t, OffHidden = True, SelectorStyle = 0 )
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
            if t in ('Generic_5_buttons', 'LegrandSelector', 'SwitchAQ3', 'SwitchIKEA'): 
                Options = createSwitchSelector( 5,  DeviceType = t,SelectorStyle = 1 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in Generic_5" %(t), NWKID)

            # 6 Selectors, Style 1
            if t in ('AlarmWD', ):        
                Options = createSwitchSelector( 6,  DeviceType = t,SelectorStyle = 1 )
                createDomoticzWidget( self, Devices, NWKID, DeviceID_IEEE, Ep, t, widgetOptions = Options)
                loggingWidget( self, "Debug", "CreateDomoDevice - t: %s in AlarmWD" %(t), NWKID)

            # 6 Buttons, Style 1, OffHidden
            if t in ('GenericLvlControl', ): 
            
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

            if t == "Switch":  
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

                if t == 'ColorControlRGB':     Subtype_ = 0x02 # RGB color palette / Dimable
                elif t == 'ColorControlRGBWW': Subtype_ = 0x04  # RGB + WW / Dimable
                elif t == 'ColorControlFull':  Subtype_ = 0x07  # 3 Color palettes widget
                elif t == 'ColorControlWW':    Subtype_ = 0x08  # White color palette / Dimable
                else:
                    # Generic ColorControl, let's try to find a better one.
                    if 'ColorInfos' in self.ListOfDevices[NWKID]:
                        Subtype_ = subtypeRGB_FromProfile_Device_IDs( self.ListOfDevices[NWKID]['Ep'], self.ListOfDevices[NWKID]['Model'],
                            self.ListOfDevices[NWKID]['ProfileID'], self.ListOfDevices[NWKID]['ZDeviceID'], self.ListOfDevices[NWKID]['ColorInfos'])
                    else:
                        Subtype_ = subtypeRGB_FromProfile_Device_IDs( self.ListOfDevices[NWKID]['Ep'], self.ListOfDevices[NWKID]['Model'],
                            self.ListOfDevices[NWKID]['ProfileID'], self.ListOfDevices[NWKID]['ZDeviceID'], None)

                    if Subtype_ == 0x02:   t = 'ColorControlRGB'
                    elif Subtype_ == 0x04: t = 'ColorControlRGBWW'
                    elif Subtype_ == 0x07: t = 'ColorControlFull'
                    elif Subtype_ == 0x08: t = 'ColorControlWW'
                    else:                  t = 'ColorControlFull'

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

def MajDomoDevice(self, Devices, NWKID, Ep, clusterID, value, Attribute_='', Color_=''):
    '''
    MajDomoDevice
    Update domoticz device accordingly to Type found in EP and value/Color provided
    '''

    # Sanity Checks
    if NWKID not in self.ListOfDevices:
        Domoticz.Error("MajDomoDevice - %s not known" %NWKID)
        return
    if 'IEEE' not in self.ListOfDevices[NWKID]:
        Domoticz.Error("MajDomoDevice - no IEEE for %s" %NWKID)
        return

    # Get IEEE, as in Domoticz the unique reference is the Device
    DeviceID_IEEE = self.ListOfDevices[NWKID]['IEEE']
    loggingWidget( self, "Debug", 
        "MajDomoDevice - Device ID : " + str(DeviceID_IEEE) + " - Device EP : " + str(Ep) + " - Type : " + str(
            clusterID) + " - Value : " + str(value) + " - Hue : " + str(Color_) + "  - Attribute_ : " +str(Attribute_), NWKID)

    # Get the CluserType ( Action type) from Cluster Id
    ClusterType = TypeFromCluster(self, clusterID)
    loggingWidget( self, "Debug", "MajDomoDevice - Type = " + str(ClusterType), NWKID)
 
    x = 0
    # For each single Domoticz Widget (Device) we will look if the Widget needs update  from that request
    for x in Devices:

        # Search for the Widgets which have IEEE as the DeviceID
        if Devices[x].DeviceID != DeviceID_IEEE:
            continue

        loggingWidget( self, "Debug", "MajDomoDevice - NWKID = " + str(NWKID) + " IEEE = " + str(DeviceID_IEEE) + " Unit = " + str(Devices[x].ID), NWKID)

        ID = Devices[x].ID
        DeviceType = ""
        loggingWidget( self, "Debug", "MajDomoDevice - " + str(self.ListOfDevices[NWKID]['Ep'][Ep]), NWKID)

        # Before plugin v3.0 pragma Type was only available on full scope (not Endpoint specific)
        # pragmaTypeV3 is True if we are in the new style. This means we have found a Type in Endpoint
        pragmaTypeV3 = True
        if 'ClusterType' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['ClusterType'] != {}:
                # We are in the old fasho V. 3.0.x Where ClusterType has been migrated from Domoticz
                if str(ID) not in self.ListOfDevices[NWKID]['ClusterType']:
                    Domoticz.Error("MajDomoDevice - inconsistency on ClusterType. Id: %s not found in %s" \
                            %( str(ID), str(self.ListOfDevices[NWKID]['ClusterType'])))
                    return
                loggingWidget( self, "Debug", "MajDomoDevice - search ClusterType in : " + str(
                    self.ListOfDevices[NWKID]['ClusterType']) + " for : " + str(ID), NWKID)
                DeviceType = self.ListOfDevices[NWKID]['ClusterType'][str(ID)]
                pragmaTypeV3 = False
        #At that stage we have pragmaTypeV3 which indicate if we are post or pre V3
        # Now if we are post V3 we have Type in Endpoint, we need to see if we have only One Endpoint with Type, or several
        if pragmaTypeV3:
            # Are we in a situation with one Devices whatever Eps are ?
            # To do that, check there is only 1 ClusterType even if several EPs
            nbClusterType = 0
            ptEP = Ep
            for tmpEp in self.ListOfDevices[NWKID]['Ep']:
                if 'ClusterType' in self.ListOfDevices[NWKID]['Ep'][tmpEp]:
                    nbClusterType = nbClusterType + 1
                    ptEP_single = tmpEp

            loggingWidget( self, "Debug", "MajDomoDevice - We have " + str(nbClusterType) + " EPs with ClusterType", NWKID)

            if nbClusterType == 1:  
                # All status to a single Endpoint
                # 
                for key in self.ListOfDevices[NWKID]['Ep'][ptEP_single]['ClusterType']:
                    if str(ID) == str(key):
                        DeviceType = str(self.ListOfDevices[NWKID]['Ep'][ptEP_single]['ClusterType'][key])
                        break

            else:
                # Status must be done accordingly to the Endpoint
                ptEp_multi = Ep
                loggingWidget( self, "Debug", "MajDomoDevice - search ClusterType in : " + str(
                    self.ListOfDevices[NWKID]['Ep'][ptEp_multi]) + " for : " + str(ID), NWKID)
                if 'ClusterType' in self.ListOfDevices[NWKID]['Ep'][ptEp_multi]:
                    loggingWidget( self, "Debug", "MajDomoDevice - search ClusterType in : " + str(
                        self.ListOfDevices[NWKID]['Ep'][ptEp_multi]['ClusterType']) + " for : " + str(ID), NWKID)
                    for key in self.ListOfDevices[NWKID]['Ep'][ptEp_multi]['ClusterType']:
                        if str(ID) == str(key):
                            DeviceType = str(self.ListOfDevices[NWKID]['Ep'][ptEp_multi]['ClusterType'][key])
                            break
                else:
                    loggingWidget( self, "Debug", "MajDomoDevice - receive an update on an Ep which doesn't have any ClusterType !", NWKID)
                    loggingWidget( self, "Debug", "MajDomoDevice - Network Id : " + NWKID + " Ep : " + str(
                        ptEp_multi) + " Expected Cluster is " + str(clusterID), NWKID)
                    continue
        
        # Check that we have found one DeviceType ( Device Idx )
        if DeviceType == "":  # No match with ClusterType
            continue

        loggingWidget( self, "Debug", "MajDomoDevice - NWKID: %s SwitchType: %s, DeviceType: %s, ClusterType: %s, old_nVal: %s , old_sVal: %s" \
                        % (NWKID, Devices[x].SwitchType, DeviceType, ClusterType, Devices[x].nValue, Devices[x].sValue), NWKID)

        # Manage battery and Signal level
        if self.ListOfDevices[NWKID]['RSSI'] != 0:
            SignalLevel = self.ListOfDevices[NWKID]['RSSI']
        else:
            SignalLevel = 15
        if self.ListOfDevices[NWKID]['Battery'] != '':
            BatteryLevel = self.ListOfDevices[NWKID]['Battery']
        else:
            BatteryLevel = 255

        # Start the Big block where to manage the update.
        # we have know identify the Device Idx to be updated if applicable
        # What we have:
        # ID         : Widget Idx
        # ClusterType: This the Cluster action extracted for the particular Endpoint based on Clusters.
        # DeviceType : This is the Type of Widget defined at Widget Creation
        # value      : this is value comming mostelikely from readCluster. Be carreful depending on the cluster, the value is String or Int
        # Attribute_ : If used This is the Attribute from readCluster. Will help to route to the right action
        # Color_     : If used This is the color value to be set

        # Power and Meter usage are triggered only with the Instant Power usage.
        # it is assumed that if there is also summation provided by the device, that
        # such information is stored on the data structuture and here we will retreive it.

        if 'Power' in ClusterType: # Instant Power/Watts
            # value is expected as String
            if DeviceType == 'P1Meter' and Attribute_ == '0000' :
                # P1Meter report Instant and Cummulative Power.
                # We need to retreive the Cummulative Power.
                conso = 0
                if '0702' in self.ListOfDevices[NWKID]['Ep'][Ep]:
                    if '0400' in self.ListOfDevices[NWKID]['Ep'][Ep]['0702']:
                        conso = round(float(self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0400']),2)
                summation = round(float(value),2)
                nValue = 0
                sValue = "%s;%s;%s;%s;%s;%s" %(summation,0,0,0,conso,0)
                loggingWidget( self, "Debug", "MajDomoDevice P1Meter : " + sValue, NWKID)
                UpdateDevice_v2(self, Devices, x, 0, str(sValue), BatteryLevel, SignalLevel)

            elif DeviceType == "Power" and ( Attribute_== '' or clusterID == "000c"):  # kWh
                nValue = round(float(value),2)
                sValue = value
                loggingWidget( self, "Debug", "MajDomoDevice Power : " + sValue, NWKID)
                UpdateDevice_v2(self, Devices, x, nValue, str(sValue), BatteryLevel, SignalLevel)

        if 'Meter' in ClusterType: # Meter Usage. 
            # value is string an represent the Instant Usage
            if (DeviceType == "Meter" and Attribute_== '') or \
                (DeviceType == "Power" and clusterID == "000c" ):  # kWh

            # Let's check if we have Summation in the datastructutre
                summation = 0
                if '0702' in self.ListOfDevices[NWKID]['Ep'][Ep]:
                    if '0000' in self.ListOfDevices[NWKID]['Ep'][Ep]['0702']:
                        if self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0000'] != {} and self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0000'] != '' and \
                                self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0000'] != '0':
                            summation = int(self.ListOfDevices[NWKID]['Ep'][Ep]['0702']['0000'])

                Options = {}
                # Do we have the Energy Mode calculation already set ?
                if 'EnergyMeterMode' in Devices[ x ].Options:
                    # Yes, let's retreive it
                    Options = Devices[ x ].Options
                else:
                    # No, let's set to compute
                    Options['EnergyMeterMode'] = '0' # By default from device

                # Did we get Summation from Data Structure
                if summation:
                    # We got summation from Device, let's check that EnergyMeterMode is
                    # correctly set to 0, if not adjust
                    if Options['EnergyMeterMode'] != '0':
                        oldnValue = Devices[ x ].nValue
                        oldsValue = Devices[ x ].sValue
                        Options = {}
                        Options['EnergyMeterMode'] = '0'
                        Devices[ x ].Update( oldnValue, oldsValue, Options=Options )
                else:
                    # No summation retreive, so we make sure that EnergyMeterMode is
                    # correctly set to 1 (compute), if not adjust
                    if Options['EnergyMeterMode'] != '1':
                        oldnValue = Devices[ x ].nValue
                        oldsValue = Devices[ x ].sValue
                        Options = {}
                        Options['EnergyMeterMode']='1'
                        Devices[ x ].Update( oldnValue, oldsValue, Options=Options )

                nValue = round(float(value),2)
                summation = round(float(summation),2)
                sValue = "%s;%s" % (nValue, summation)
                loggingWidget( self, "Debug", "MajDomoDevice Meter : " + sValue)
                UpdateDevice_v2(self, Devices, x, 0, sValue, BatteryLevel, SignalLevel)

        if 'Voltage' in ClusterType:  # Volts
            # value is str
            if DeviceType == "Voltage": 
                nValue = round(float(value),2)
                sValue = "%s;%s" % (nValue, nValue)
                loggingWidget( self, "Debug", "MajDomoDevice Voltage : " + sValue, NWKID)
                UpdateDevice_v2(self, Devices, x, 0, sValue, BatteryLevel, SignalLevel)

        if 'ThermoSetpoint' in ClusterType: # Thermostat SetPoint
            # value is a str
            if  DeviceType == 'ThermoSetpoint' and Attribute_ in ( '4003', '0012'):
                setpoint = round(float(value),2)
                # Normalize SetPoint value with 2 digits
                strRound = lambda x, n: eval('"%.' + str(int(n)) + 'f" % ' + repr(x))
                nValue = 0
                sValue = strRound( float(setpoint), 2 )
                loggingWidget( self, "Debug", "MajDomoDevice Thermostat Setpoint: %s %s" %(0,setpoint), NWKID)
                UpdateDevice_v2(self, Devices, x, 0, sValue, BatteryLevel, SignalLevel)
    
        if 'ThermoMode' in ClusterType: # Thermostat Mode
           
            if DeviceType == 'ThermoModeEHZBRTS' and Attribute_ in ( '001c', 'e010'): # Thermostat Wiser
                 # value is str
                loggingWidget( self, "Debug", "MajDomoDevice EHZBRTS Schneider Thermostat Mode %s" %value, NWKID)
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
                    UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel)    

            elif DeviceType == 'HACTMODE' and Attribute_ == "e011":#  Wiser specific Fil Pilote
                 # value is str
                loggingWidget( self, "Debug", "MajDomoDevice ThermoMode HACTMODE: %s" %(value), NWKID)
                THERMOSTAT_MODE = { 0:'00', # Conventional
                    1:'10', 
                    2:'20', # Setpoint
                    3:'30'  # FIP
                    }
                _mode = int(value,16)

                if _mode in THERMOSTAT_MODE:
                    nValue = _mode
                    sValue = THERMOSTAT_MODE[ _mode ]
                    UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel)            
                    
            elif DeviceType == 'ThermoMode' and Attribute_ == '001c':
                # value seems to come as int or str. To be fixed
                loggingWidget( self, "Debug", "MajDomoDevice Thermostat Mode %s" %value, NWKID)
                nValue = value
                if isinstance( value, str):
                    nValue = int(value,16)
                if nValue in THERMOSTAT_MODE_2_LEVEL:
                    sValue = THERMOSTAT_MODE_2_LEVEL[nValue]
                    UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel)
                    loggingWidget( self, "Debug", "MajDomoDevice Thermostat Mode: %s %s" %(nValue,sValue), NWKID)

        if 'Temp' in ClusterType:  # temperature
            loggingWidget( self, "Debug", "MajDomoDevice Temp: %s, DeviceType: >%s<" %(value,DeviceType), NWKID)
            adjvalue = 0
            if self.domoticzdb_DeviceStatus:
                from Classes.DomoticzDB import DomoticzDB_DeviceStatus
                adjvalue = round(self.domoticzdb_DeviceStatus.retreiveAddjValue_temp( Devices[x].ID),1)
            loggingWidget( self, "Debug", "Adj Value : %s from: %s to %s " %(adjvalue, value, (value+adjvalue)), NWKID)
            CurrentnValue = Devices[x].nValue
            CurrentsValue = Devices[x].sValue
            if CurrentsValue == '':
                # First time after device creation
                CurrentsValue = "0;0;0;0;0"
            SplitData = CurrentsValue.split(";")
            NewNvalue = 0
            NewSvalue = ''
            if DeviceType == "Temp":
                NewNvalue = round(value + adjvalue,1)
                NewSvalue = str(round(value + adjvalue,1))
                loggingWidget( self, "Debug", "MajDomoDevice Temp update: %s - %s" %(NewNvalue, NewSvalue))
                UpdateDevice_v2(self, Devices, x, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif DeviceType == "Temp+Hum":
                NewNvalue = 0
                NewSvalue = '%s;%s;%s' %(round(value + adjvalue,1), SplitData[1], SplitData[2])
                loggingWidget( self, "Debug", "MajDomoDevice Temp+Hum update: %s - %s" %(NewNvalue, NewSvalue))
                UpdateDevice_v2(self, Devices, x, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif DeviceType == "Temp+Hum+Baro":  # temp+hum+Baro xiaomi
                NewNvalue = 0
                NewSvalue = '%s;%s;%s;%s;%s' %(round(value + adjvalue,1), SplitData[1], SplitData[2], SplitData[3], SplitData[4])
                UpdateDevice_v2(self, Devices, x, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

        if 'Humi' in ClusterType:  # humidite
            loggingWidget( self, "Debug", "MajDomoDevice Humi: %s, DeviceType: >%s<" %(value,DeviceType), NWKID)
            CurrentnValue = Devices[x].nValue
            CurrentsValue = Devices[x].sValue
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

            if DeviceType == "Humi":
                NewNvalue = value
                NewSvalue = "%s" %humiStatus
                loggingWidget( self, "Debug", "MajDomoDevice Humi update: %s - %s" %(NewNvalue, NewSvalue))
                UpdateDevice_v2(self, Devices, x, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif DeviceType == "Temp+Hum":  # temp+hum xiaomi
                NewNvalue = 0
                NewSvalue = '%s;%s;%s' % (SplitData[0], value, humiStatus)
                loggingWidget( self, "Debug", "MajDomoDevice Temp+Hum update: %s - %s" %(NewNvalue, NewSvalue))
                UpdateDevice_v2(self, Devices, x, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif DeviceType == "Temp+Hum+Baro":  # temp+hum+Baro xiaomi
                NewNvalue = 0
                NewSvalue = '%s;%s;%s;%s;%s' % (SplitData[0], value, humiStatus, SplitData[3], SplitData[4])
                UpdateDevice_v2(self, Devices, x, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

        if 'Baro' in ClusterType:  # barometre
            loggingWidget( self, "Debug", "MajDomoDevice Baro: %s, DeviceType: %s" %(value,DeviceType), NWKID)
            adjvalue = 0
            if self.domoticzdb_DeviceStatus:
                from Classes.DomoticzDB import DomoticzDB_DeviceStatus
                adjvalue = round(self.domoticzdb_DeviceStatus.retreiveAddjValue_baro( Devices[x].ID),1)
            baroValue = round( (value + adjvalue), 1)
            loggingWidget( self, "Debug", "Adj Value : %s from: %s to %s " %(adjvalue, value, baroValue), NWKID)

            CurrentnValue = Devices[x].nValue
            CurrentsValue = Devices[x].sValue
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

            if DeviceType == "Baro":
                NewSvalue = '%s;%s' %(baroValue, Bar_forecast)
                UpdateDevice_v2(self, Devices, x, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

            elif DeviceType == "Temp+Hum+Baro":
                NewSvalue = '%s;%s;%s;%s;%s' % (SplitData[0], SplitData[1], SplitData[2], baroValue, Bar_forecast)
                UpdateDevice_v2(self, Devices, x, NewNvalue, NewSvalue, BatteryLevel, SignalLevel)

        if 'BSO' in ClusterType: # Not fully tested / So far developped for Profalux
            # value is str
            if DeviceType == "BSO":
                # Receveive Level (orientation) in degrees to convert into % for the dimmer
                percent_value = (int(value) * 100 // 90)
                nValue = 2
                sValue = str(percent_value)
                UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel)

        if ClusterType in ( 'Door', 'Switch', 'Motion', 'Ikea_Round_5b', 'Ikea_Round_OnOff', 'Vibration', 'OrviboRemoteSquare'): # Plug, Door, Switch, Button ...
            # We reach this point because ClusterType is Door or Switch. It means that Cluster 0x0006 or 0x0500
            # So we might also have to manage case where we receive a On or Off for a LvlControl DeviceType like a dimming Bulb.

            if DeviceType in SWITCH_LVL_MATRIX:
                if value in SWITCH_LVL_MATRIX[ DeviceType ]:
                    if len(SWITCH_LVL_MATRIX[ DeviceType ][ value] ) == 2:
                        nValue, sValue = SWITCH_LVL_MATRIX[ DeviceType ][ value ]
                        _ForceUpdate =  SWITCH_LVL_MATRIX[ DeviceType ]['ForceUpdate']
                        loggingWidget( self, "Debug", "Switch update DeviceType: %s with %s" %(DeviceType, str(SWITCH_LVL_MATRIX[ DeviceType ])), NWKID)
                        UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_= _ForceUpdate) 
                    else:
                        loggingWidget( self, "Error", "MajDomoDevice - len(SWITCH_LVL_MATRIX[ %s ][ %s ]) == %s" %(DeviceType,value, len(SWITCH_LVL_MATRIX[ DeviceType ])), NWKID ) 
                else:
                    loggingWidget( self, "Error", "MajDomoDevice - value: %s not found in SWITCH_LVL_MATRIX[ %s ]" %(value, DeviceType), NWKID ) 

            elif DeviceType == "DSwitch":
                # double switch avec EP different 
                value = int(value)
                if value == 1 or value == 0:
                    if Ep == "01":
                        nValue = 1; sValue = '10'
                        UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel)
                    elif Ep == "02":
                        nValue = 2; sValue = '20'
                        UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel)
                    elif Ep == "03":
                        nValue = 3; sValue = '30'
                        UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel)

            elif DeviceType == "DButton":
                # double bouttons avec EP different lumi.sensor_86sw2 
                value = int(value)
                if value == 1:
                    if Ep == "01":
                        nValue = 1; sValue = '10'
                        UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                    elif Ep == "02":
                        nValue = 2; sValue = '20'
                        UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)
                    elif Ep == "03":
                        nValue = 3; sValue = '30'
                        UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif DeviceType == "DButton_3":
                # double bouttons avec EP different lumi.sensor_86sw2 
                value = int(value)
                data = '00'
                state = '00'
                if Ep == "01":
                    if value == 1: state = "10"; data = "01"
                    elif value == 2: state = "20"; data = "02"
                    elif value == 3: state = "30"; data = "03"
                    UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel,ForceUpdate_=True)
                                        
                elif Ep == "02":
                    if value == 1: state = "40"; data = "04"
                    elif value == 2: state = "50"; data = "05"
                    elif value == 3: state = "60"; data = "06"
                    UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel,ForceUpdate_=True)
                                        
                elif Ep == "03":
                    if value == 1: state = "70"; data = "07"
                    elif value == 2: state = "80"; data = "08"
                    elif value == 3: state = "90"; data = "09"
                    UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel,ForceUpdate_=True)
                                        
            elif DeviceType == "LvlControl" or DeviceType in ( 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl'):
                if Devices[x].SwitchType in (13,14,15,16):
                    # Required Numeric value
                    if value == "00":
                        UpdateDevice_v2(self, Devices, x, 0, '0', BatteryLevel, SignalLevel)
                    else:
                        # We are in the case of a Shutter/Blind inverse. If we receieve a Read Attribute telling it is On, great
                        # We only update if the shutter was off before, otherwise we will keep its Level.
                        if Devices[x].nValue == 0 and Devices[x].sValue == 'Off':
                            UpdateDevice_v2(self, Devices, x, 1, '100', BatteryLevel, SignalLevel)
                else:
                    # Required Off and On
                    if value == "00":
                        UpdateDevice_v2(self, Devices, x, 0, 'Off', BatteryLevel, SignalLevel)
                    else:
                        if Devices[x].sValue == "Off":
                            # We do update only if this is a On/off
                            UpdateDevice_v2(self, Devices, x, 1, 'On', BatteryLevel, SignalLevel)
            
            else:
                loggingWidget( self, "Debug", "MajDomoDevice - DeviceType: %s not found in  SWITCH_LVL_MATRIX" %( DeviceType), NWKID )

        if 'WindowCovering' in ClusterType: # 0x0102
            if DeviceType in ( 'VenetianInverted', 'Venetian', 'WindowCovering'):
                value = int(value,16)
                loggingWidget( self, "Debug", "MajDomoDevice - %s/%s Updating %s Value: %s" %(NWKID, Ep, DeviceType,value), NWKID)
                if DeviceType == "VenetianInverted":
                    value = 100 - value
                    loggingWidget( self, "Debug", "--------------- - Patching %s/%s Value: %s" %(NWKID, Ep,value), NWKID)
                if value == 0: 
                    nValue = 0
                elif value == 100: 
                    nValue = 1
                else: 
                    nValue = 2
                UpdateDevice_v2(self, Devices, x, nValue, str(value), BatteryLevel, SignalLevel)

        if 'LvlControl' in ClusterType: # LvlControl ( 0x0008)
            if DeviceType == "LvlControl":
                # We need to handle the case, where we get an update from a Read Attribute or a Reporting message
                # We might get a Level, but the device is still Off and we shouldn't make it On .
                nValue = None

                # Normalize sValue vs. analog value coomming from a ReadATtribute
                analogValue = int(value, 16)

                loggingWidget( self, "Debug", "--> LvlControl analogValue: -> %s" %analogValue, NWKID)
                if analogValue >= 255:
                    sValue = 100
                else:
                    sValue = round( ((int(value, 16) * 100) / 255))
                    if sValue > 100: 
                        sValue = 100
                    if sValue == 0 and analogValue > 0:
                        sValue = 1
                    # Looks like in the case of the Profalux shutter, we never get 0 or 100
                    if Devices[x].SwitchType in (13,14,15,16):
                        if sValue == 1 and analogValue == 1:
                            sValue = 0
                        if sValue == 99 and analogValue == 254:
                            sValue = 100

                loggingWidget( self, "Debug", "----> LvlControl sValue: -> %s" %sValue, NWKID)

                # In case we reach 0% or 100% we shouldn't switch Off or On, except in the case of Shutter/Blind
                if sValue == 0:
                    nValue = 0
                    if Devices[x].SwitchType in (13,14,15,16):
                        loggingWidget( self, "Debug", "--> LvlControl UpdateDevice: -> %s/%s SwitchType: %s" %(0,0, Devices[x].SwitchType), NWKID)
                        UpdateDevice_v2(self, Devices, x, 0, '0', BatteryLevel, SignalLevel)
                    else:
                        if Devices[x].nValue == 0 and Devices[x].sValue == 'Off':
                            pass
                        else:
                            #UpdateDevice_v2(Devices, x, 0, 'Off', BatteryLevel, SignalLevel)
                            loggingWidget( self, "Debug", "--> LvlControl UpdateDevice: -> %s/%s" %(0,0), NWKID)
                            UpdateDevice_v2(self, Devices, x, 0, '0', BatteryLevel, SignalLevel)

                elif sValue == 100:
                    nValue = 1
                    if Devices[x].SwitchType in (13,14,15,16):
                        loggingWidget( self, "Debug", "--> LvlControl UpdateDevice: -> %s/%s SwitchType: %s" %(1,100, Devices[x].SwitchType), NWKID)
                        UpdateDevice_v2(self, Devices, x, 1, '100', BatteryLevel, SignalLevel)
                    else:
                        if Devices[x].nValue == 0 and Devices[x].sValue == 'Off':
                            pass
                        else:
                            #UpdateDevice_v2(Devices, x, 1, 'On', BatteryLevel, SignalLevel)
                            loggingWidget( self, "Debug", "--> LvlControl UpdateDevice: -> %s/%s" %(1,100), NWKID)
                            UpdateDevice_v2(self, Devices, x, 1, '100', BatteryLevel, SignalLevel)
                else: # sValue != 0 and sValue != 100
                    if Devices[x].nValue == 0 and Devices[x].sValue == 'Off':
                        # Do nothing. We receive a ReadAttribute  giving the position of a Off device.
                        pass
                    elif Devices[x].SwitchType in (13,14,15,16):
                        loggingWidget( self, "Debug", "--> LvlControl UpdateDevice: -> %s/%s SwitchType: %s" %(nValue,sValue, Devices[x].SwitchType), NWKID)
                        UpdateDevice_v2(self, Devices, x, 2, str(sValue), BatteryLevel, SignalLevel)
                    else:
                        loggingWidget( self, "Debug", "--> LvlControl UpdateDevice: -> %s/%s SwitchType: %s" %(nValue,sValue, Devices[x].SwitchType), NWKID)
                        UpdateDevice_v2(self, Devices, x, 1, str(sValue), BatteryLevel, SignalLevel)

            elif DeviceType  in ( 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl'):
                if Devices[x].nValue == 0 and Devices[x].sValue == 'Off':
                    pass
                else:
                    nValue = 1
                    analogValue = int(value, 16)
                    if analogValue >= 255:
                        sValue = 100
                    else:
                        sValue = round(((int(value, 16) * 100) / 255))
                        if sValue > 100: sValue = 100
                        if sValue == 0 and analogValue > 0:
                            sValue = 1
                    UpdateDevice_v2(self, Devices, x, nValue, str(sValue), BatteryLevel, SignalLevel, Color_)


            elif DeviceType == 'LegrandSelector':
                loggingWidget( self, "Debug", "LegrandSelector : Value -> %s" %value, NWKID)
                if value == '00': nValue = 0 ; sValue = '00' #Off
                elif value == '01': nValue = 1 ; sValue = "10" # On
                elif value == 'moveup': nValue = 2 ; sValue = "20" # Move Up
                elif value == 'movedown': nValue = 3 ; sValue = "30" # Move Down
                elif value == 'stop': nValue = 4 ; sValue = "40" # Stop
                else:
                    Domoticz.Error("MajDomoDevice - %s LegrandSelector Unknown value %s" %(NWKID, value))
                    return
                UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif DeviceType == 'Generic_5_buttons':
                loggingWidget( self, "Debug", "Generic 5 buttons : Value -> %s" %value, NWKID)
                nvalue = 0
                state = '00'
                if value == '00': nvalue = 0; sValue = '00'
                elif value == '01': nvalue = 1; sValue = '10'
                elif value == '02': nvalue = 2; sValue = '20'
                elif value == '03': nvalue = 3; sValue = '30'
                elif value == '04': nvalue = 4; sValue = '40'
                UpdateDevice_v2(self, Devices, x, nvalue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif DeviceType == 'GenericLvlControl':
                # 1,10: Off
                # 2,20: On
                # 3,30: Move Up
                # 4,40: Move Down
                # 5,50: Stop
                loggingWidget( self, "Debug", "GenericLvlControl : Value -> %s" %value, NWKID)
                if value == 'off': nvalue = 1 ; sValue = '10' #Off
                elif value == 'on': nvalue = 2 ; sValue = "20" # On
                elif value == 'moveup': nvalue = 3 ; sValue = "30" # Move Up
                elif value == 'movedown': nvalue = 4 ; sValue = "40" # Move Down
                elif value == 'stop': nvalue = 5 ; sValue = "50" # Stop
                UpdateDevice_v2(self, Devices, x, nvalue, sValue, BatteryLevel, SignalLevel, ForceUpdate_=True)

            elif DeviceType == "INNR_RC110_SCENE":
                loggingWidget( self, "Debug", "MajDomoDevice - Updating INNR_RC110_SCENE (LvlControl) Value: %s" %value, NWKID)
                if value == "Off": nValue = 0
                elif value == "On": nValue = 1
                elif value == "clickup": nValue = 2
                elif value == "clickdown": nValue = 3
                elif value == "moveup": nValue = 4
                elif value == "movedown": nValue = 5
                elif value == "stop":   nValue = 6
                elif value == "scene1": nValue = 7
                elif value == "scene2": nValue = 8
                elif value == "scene3": nValue = 9
                elif value == "scene4": nValue = 10
                elif value == "scene5": nValue = 11
                elif value == "scene6": nValue = 12
                sValue = "%s" %(10 * nValue)
                UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel)

            elif DeviceType == 'INNR_RC110_LIGHT':
                loggingWidget( self, "Debug", "MajDomoDevice - Updating INNR_RC110_LIGHT (LvlControl) Value: %s" %value, NWKID)
                if value == "00": nValue = 0
                elif value == "01": nValue = 1
                elif value == "clickup": nValue = 2
                elif value == "clickdown": nValue = 3
                elif value == "moveup": nValue = 4
                elif value == "movedown": nValue = 5
                elif value == "stop":   nValue = 6
                sValue = "%s" %(10 * nValue)
                UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel)

        if ClusterType in ( 'ColorControlRGB', 'ColorControlWW', 'ColorControlRGBWW', 'ColorControlFull', 'ColorControl'):
            # We just manage the update of the Dimmer (Control Level)
            if ClusterType == DeviceType:
                nValue = 1
                analogValue = int(value, 16)
                if analogValue >= 255:
                    sValue = 100
                else:
                    sValue = round(((int(value, 16) * 100) / 255))
                    if sValue > 100: sValue = 100
                    if sValue == 0 and analogValue > 0:
                        sValue = 1

                UpdateDevice_v2(self, Devices, x, nValue, str(sValue), BatteryLevel, SignalLevel, Color_)

        if 'XCube' in ClusterType: # XCube Aqara or Xcube
            if DeviceType == "Aqara":
                if Ep == "02":  # Magic Cube Aqara
                    loggingWidget( self, "Debug", "MajDomoDevice - XCube update device with data = " + str(value), NWKID)
                    nValue = int(value)
                    sValue = value
                    UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_ = True)

                if Ep == "03":  # Magic Cube Aqara Rotation
                    if Attribute_ == '0055': # Rotation Angle
                        # Update Text widget ( unit + 1 )
                        nValue = 0
                        sValue = value
                        UpdateDevice_v2(self, Devices, x + 1, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_ = True)
                    else:
                        nValue = int(value)
                        sValue =  value
                        if nValue == 80:
                            nValue = 8
                        elif nValue == 90:
                            nValue = 9
                    loggingWidget( self, "Debug", "MajDomoDevice - XCube update device with data = %s , nValue: %s sValue: %s" %(value, nValue, sValue), NWKID)
                    UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_ = True)

            elif DeviceType == "XCube" and Ep == "02":  # cube xiaomi
                if value == "0000":  # shake
                     state = "10"
                     data = "01"
                     UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)
                elif value in ( "0204", "0200", "0203", "0201", "0202", "0205" ):
                     state = "50"
                     data = "05"
                     UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)
                elif value in ( "0103", "0100", "0104", "0101", "0102", "0105"): # Slide/M%ove
                     state = "20"
                     data = "02"
                     UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)
                elif value == "0003":  # Free Fall
                     state = "70"
                     data = "07"
                     UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)
                elif "0004" <= value <= "0059":  # 90°
                     state = "30"
                     data = "03"
                     UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)
                elif value >= "0060":  # 180°
                     state = "90"
                     data = "09"
                     UpdateDevice_v2(self, Devices, x, int(data), str(state), BatteryLevel, SignalLevel, ForceUpdate_ = True)

        if 'Orientation' in ClusterType:
            # Xiaomi Vibration
            if DeviceType == "Orientation":
                #value is a str containing all Orientation information to be updated on Text Widget
                nValue = 0
                sValue = value
                UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_ = True)

        if 'Strenght' in ClusterType:
            if DeviceType == "Strength":
                #value is a str containing all Orientation information to be updated on Text Widget
                nValue = 0
                sValue = value
                UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_ = True)

        if 'Lux' in ClusterType:
            if DeviceType == "Lux":
                nValue = int(value)
                sValue = value
                UpdateDevice_v2(self, Devices, x, nValue, sValue, BatteryLevel, SignalLevel, ForceUpdate_= True)

def ResetDevice(self, Devices, ClusterType, HbCount):
    '''
        Reset all Devices from the ClusterType Motion after 30s
    '''

    x = 0
    for x in Devices:
        if Devices[x].nValue == 0 and Devices[x].sValue == "Off":
            # No need to spend time as it is already in the state we want, go to next device
            continue


        LUpdate = Devices[x].LastUpdate
        _tmpDeviceID_IEEE = Devices[x].DeviceID
        try:
            LUpdate = time.mktime(time.strptime(LUpdate, "%Y-%m-%d %H:%M:%S"))
        except:
            Domoticz.Error("Something wrong to decode Domoticz LastUpdate %s" %LUpdate)
            break

        current = time.time()

        # Look for the corresponding ClusterType
        if _tmpDeviceID_IEEE in self.IEEE2NWK:
            NWKID = self.IEEE2NWK[_tmpDeviceID_IEEE]

            if NWKID not in self.ListOfDevices:
                Domoticz.Error("ResetDevice " + str(NWKID) + " not found in " + str(self.ListOfDevices))
                continue

            ID = Devices[x].ID
            DeviceType = ''
            for tmpEp in self.ListOfDevices[NWKID]['Ep']:
                if 'ClusterType' in self.ListOfDevices[NWKID]['Ep'][tmpEp]:
                    if str(ID) in self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType']:
                        DeviceType = self.ListOfDevices[NWKID]['Ep'][tmpEp]['ClusterType'][str(ID)]
            if DeviceType == '':
                if 'ClusterType' in self.ListOfDevices[NWKID]:
                    if str(ID) in self.ListOfDevices[NWKID]['ClusterType']:
                        DeviceType = self.ListOfDevices[NWKID]['ClusterType'][str(ID)]
            
            if DeviceType not in ('Motion', 'Vibration'):
                continue

            if self.domoticzdb_DeviceStatus:
                from Classes.DomoticzDB import DomoticzDB_DeviceStatus

                # Let's check if we have a Device TimeOut specified by end user
                if self.domoticzdb_DeviceStatus.retreiveTimeOut_Motion( Devices[x].ID) > 0:
                    continue

            # Takes the opportunity to update RSSI and Battery
            SignalLevel = ''
            BatteryLevel = ''
            if self.ListOfDevices[NWKID].get('RSSI'):
                SignalLevel = self.ListOfDevices[NWKID]['RSSI']
            if self.ListOfDevices[NWKID].get('Battery'):
                BatteryLevel = self.ListOfDevices[NWKID]['Battery']

            _timeout = self.pluginconf.pluginConf['resetMotiondelay']
            #resetMotionDelay = 0

            #if self.domoticzdb_DeviceStatus:
            #    from Classes.DomoticzDB import DomoticzDB_DeviceStatus
            #    resetMotionDelay = round(self.domoticzdb_DeviceStatus.retreiveTimeOut_Motion( Devices[x].ID),1)

            #if resetMotionDelay > 0:
            #    _timeout = resetMotionDelay

            if (current - LUpdate) >= _timeout: 
                loggingWidget( self, "Debug", "Last update of the devices " + str(x) + " was : " + str(LUpdate) + " current is : " + str(
                    current) + " this was : " + str(current - LUpdate) + " secondes ago", NWKID)
                UpdateDevice_v2(self, Devices, x, 0, "Off", BatteryLevel, SignalLevel)
    return


def UpdateDevice_v2(self, Devices, Unit, nValue, sValue, BatteryLvl, SignalLvl, Color_='', ForceUpdate_=False):

    loggingWidget( self, "Debug", "UpdateDevice_v2 %s:%s:%s_%s:%s_%s (%15s)" %( nValue, sValue, Color_, BatteryLvl, SignalLvl, ForceUpdate_, Devices[Unit].Name), self.IEEE2NWK[Devices[Unit].DeviceID])

    rssi = 12
    if isinstance(SignalLvl, int):
        rssi = round((SignalLvl * 12) / 255)
        loggingWidget( self, "Debug", "UpdateDevice_v2 for : " + str(Devices[Unit].Name) + " RSSI = " + str(rssi), self.IEEE2NWK[Devices[Unit].DeviceID])

    if BatteryLvl == '' or (not isinstance(BatteryLvl, int)):
        BatteryLvl = 255
    else:
        loggingWidget( self, "Debug", "UpdateDevice_v2 for : " + str(Devices[Unit].Name) + " BatteryLevel = " + str(BatteryLvl), self.IEEE2NWK[Devices[Unit].DeviceID])

    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if (Unit in Devices):
        if (Devices[Unit].nValue != int(nValue)) or (Devices[Unit].sValue != sValue) or \
            ( Color_ !='' and Devices[Unit].Color != Color_) or \
            ForceUpdate_ or \
            Devices[Unit].BatteryLevel != int(BatteryLvl) or \
            Devices[Unit].TimedOut:

            if self.pluginconf.pluginConf['logDeviceUpdate']:
                Domoticz.Log("UpdateDevice - (%15s) %s:%s" %( Devices[Unit].Name, nValue, sValue ))
            loggingWidget( self, "Debug", "Update Values %s:%s:%s %s:%s %s (%15s)" %( nValue, sValue, Color_, BatteryLvl, rssi, ForceUpdate_, Devices[Unit].Name), self.IEEE2NWK[Devices[Unit].DeviceID])
            if Color_:
                Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue), Color=Color_, SignalLevel=int(rssi), BatteryLevel=int(BatteryLvl), TimedOut=0)
            else:
                Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue),               SignalLevel=int(rssi), BatteryLevel=int(BatteryLvl), TimedOut=0)
    return


def timedOutDevice( self, Devices, Unit=None, NwkId=None, TO=1):
 
    _Unit = _nValue = _sValue = None
    if Unit:
        _nValue = Devices[Unit].nValue
        _sValue = Devices[Unit].sValue
        _Unit = Unit
        if TO and not Devices[_Unit].TimedOut:
            Devices[_Unit].Update(nValue=_nValue, sValue=_sValue, TimedOut=1)
        elif not TO and Devices[_Unit].TimedOut:
            Devices[_Unit].Update(nValue=_nValue, sValue=_sValue, TimedOut=0)

    elif NwkId:
        if NwkId not in self.ListOfDevices:
            return
        if 'IEEE' not in self.ListOfDevices[NwkId]:
            return
        _IEEE = self.ListOfDevices[NwkId]['IEEE']
        if TO:
            self.ListOfDevices[NwkId]['Health'] = 'TimedOut'
        else:
            self.ListOfDevices[NwkId]['Health'] = 'Live'

        for x in Devices:
            if Devices[x].DeviceID == _IEEE:
                _nValue = Devices[x].nValue
                _sValue = Devices[x].sValue
                _Unit = x
                if Devices[_Unit].TimedOut:
                    if not TO:
                        loggingWidget( self, "Debug",  "reset timedOutDevice unit %s nwkid: %s " %( Devices[x].Name, NwkId ), NwkId)
                        Devices[_Unit].Update(nValue=_nValue, sValue=_sValue, TimedOut=0)
                else:
                    if TO:
                        loggingWidget( self, "Debug",  "timedOutDevice unit %s nwkid: %s " %( Devices[x].Name, NwkId ), NwkId)
                        Devices[_Unit].Update(nValue=_nValue, sValue=_sValue, TimedOut=1)


def lastSeenUpdate( self, Devices, Unit=None, NwkId=None):

    # Purpose is here just to touch the device and update the Last Seen
    # It might required to call Touch everytime we receive a message from the device and not only when update is requested.

    if Unit:
        loggingWidget( self, "Debug", "Touch unit %s" %( Devices[Unit].Name ))
        if not self.VersionNewFashion and (self.DomoticzMajor < 4 or ( self.DomoticzMajor == 4 and self.DomoticzMinor < 10547)):
            loggingWidget( self, "Debug", "Not the good Domoticz level for Touch")
            return
        # Extract NwkId from Device Unit
        IEEE = Devices[Unit].DeviceID
        if Devices[Unit].TimedOut:
            timedOutDevice( self, Devices, Unit=Unit, TO=0)
        else:
            Devices[Unit].Touch()
        if NwkId is None and 'IEEE' in self.IEEE2NWK:
            NwkId = self.IEEE2NWK[ IEEE ]

    if NwkId:
        if NwkId not in self.ListOfDevices:
            return
        if 'IEEE' not in self.ListOfDevices[NwkId]:
            return
        if 'Stamp' not in self.ListOfDevices[NwkId]:
            self.ListOfDevices[NwkId]['Stamp'] = {}
            self.ListOfDevices[NwkId]['Stamp']['Time'] = {}
            self.ListOfDevices[NwkId]['Stamp']['MsgType'] = {}
            self.ListOfDevices[NwkId]['Stamp']['LastSeen'] = 0
        if 'LastSeen' not in self.ListOfDevices[NwkId]['Stamp']:
            self.ListOfDevices[NwkId]['Stamp']['LastSeen'] = 0
        if 'ErrorManagement' in self.ListOfDevices[NwkId]:
            self.ListOfDevices[NwkId]['ErrorManagement'] = 0

        self.ListOfDevices[NwkId]['Health'] = 'Live'

        if time.time() < self.ListOfDevices[NwkId]['Stamp']['LastSeen'] + 5*60:
            loggingWidget( self, "Debug", "Too early for a new update of LastSeen %s" %NwkId, NwkId)
            return

        self.ListOfDevices[NwkId]['Stamp']['LastSeen'] = int(time.time())

        _IEEE = self.ListOfDevices[NwkId]['IEEE']
        if not self.VersionNewFashion or (self.DomoticzMajor <= 4 and ( self.DomoticzMajor == 4 and self.DomoticzMinor < 10547)):
            loggingWidget( self, "Debug", "Not the good Domoticz level for Touch", NwkId)
            return
        for x in Devices:
            if Devices[x].DeviceID == _IEEE:
                loggingWidget( self, "Debug",  "Touch unit %s nwkid: %s " %( Devices[x].Name, NwkId ), NwkId)
                if Devices[x].TimedOut:
                    timedOutDevice( self, Devices, Unit=x, TO=0)
                else:
                    Devices[x].Touch()

def GetType(self, Addr, Ep):
    Type = ""
    loggingWidget( self, "Debug", "GetType - Model " + str(self.ListOfDevices[Addr]['Model']) + " Profile ID : " + str(
        self.ListOfDevices[Addr]['ProfileID']) + " ZDeviceID : " + str(self.ListOfDevices[Addr]['ZDeviceID']), Addr)

    _Model = self.ListOfDevices[Addr]['Model']
    if _Model != {} and _Model in list(self.DeviceConf.keys()):
        # verifie si le model a ete detecte et est connu dans le fichier DeviceConf.txt
        if Ep in self.DeviceConf[ _Model ]['Ep']:
            Domoticz.Log( "Ep: %s found in DeviceConf" %Ep)
            if 'Type' in self.DeviceConf[ _Model ]['Ep'][Ep]:
                Domoticz.Log(" 'Type' entry found inf DeviceConf")
                if self.DeviceConf[ _Model ]['Ep'][Ep]['Type'] != "":
                    loggingWidget( self, "Debug", "GetType - Found Type in DeviceConf : %s" %self.DeviceConf[ _Model ]['Ep'][Ep]['Type'], Addr)
                    Type = self.DeviceConf[ _Model ]['Ep'][Ep]['Type']
                    Type = str(Type)
                else:
                    loggingWidget( self, 'Debug'"GetType - Found EpEmpty Type in DeviceConf for %s/%s" %(Addr, Ep), Addr)
            else:
                loggingWidget( self, 'Debug'"GetType - EpType not found in DeviceConf for %s/%s" %(Addr, Ep), Addr)   
        else:
            Type = self.DeviceConf[ _Model ]['Type']
            loggingWidget( self, "Debug", "GetType - Found Type in DeviceConf for %s/%s: %s " %(Addr, Ep, Type), Addr)            
    else:
        loggingWidget( self, "Debug", "GetType - Model:  >%s< not found with Ep: %s in DeviceConf. Continue with ClusterSearch" %( self.ListOfDevices[Addr]['Model'], Ep), Addr)
        loggingWidget( self, "Debug", "        - List of Entries: %s" %str(self.DeviceConf.keys() ), Addr)
        Type = ""

        # Check ProfileID/ZDeviceD
        if 'Manufacturer' in self.ListOfDevices[Addr]:
            if self.ListOfDevices[Addr]['Manufacturer'] == '117c': # Ikea
                if ( self.ListOfDevices[Addr]['ProfileID'] == 'c05e' and self.ListOfDevices[Addr]['ZDeviceID'] == '0830') :
                    return "Ikea_Round_5b"
                elif self.ListOfDevices[Addr]['ProfileID'] == 'c05e' and self.ListOfDevices[Addr]['ZDeviceID'] == '0820':
                    return "Ikea_Round_OnOff"
            elif self.ListOfDevices[Addr]['Manufacturer'] == '100b': # Philipps Hue
                pass
            elif str(self.ListOfDevices[Addr]['Manufacturer']).find('LIVOLO') != -1:
                loggingWidget( self, "Debug", "GetType - Found Livolo based on Manufacturer", Addr)
                return 'LivoloSWL/LivoloSWR'

        # Finaly Chec on Cluster
        for cluster in self.ListOfDevices[Addr]['Ep'][Ep]:
            if cluster in ('Type', 'ClusterType', 'ColorMode'): continue
            loggingWidget( self, "Debug", "GetType - check Type for Cluster : " + str(cluster))
            if Type != "" and Type[:1] != "/":
                Type += "/"
            Type += TypeFromCluster(self, cluster, create_=True)
            loggingWidget( self, "Debug", "GetType - Type will be set to : " + str(Type))

        # Type+=Type
        # Ne serait-il pas plus simple de faire un .split( '/' ), puis un join ('/')
        # car j'ai un peu de problème sur cette serie de replace. 
        # ensuite j'ai vu également des Type avec un / à la fin !!!!!
        # Par exemple :  'Type': 'Switch/LvlControl/',
        Type = Type.replace("/////", "/")
        Type = Type.replace("////", "/")
        Type = Type.replace("///", "/")
        Type = Type.replace("//", "/")
        if Type[:-1] == "/":
            Type = Type[:-1]
        if Type[0:] == "/":
            Type = Type[1:]

        loggingWidget( self, "Debug", "GetType - ClusterSearch return : %s" %Type, Addr)

    loggingWidget(self, 'Debug', "GetType returning: %s" %Type, Addr)

    return Type


def TypeFromCluster( self, cluster, create_=False, ProfileID_='', ZDeviceID_=''):

    loggingWidget( self, "Debug", "ClusterSearch - Cluster: %s, ProfileID: %s, ZDeviceID: %s, create: %s" %(cluster, ProfileID_, ZDeviceID_, create_))

    TypeFromCluster = ''
    if ProfileID_ == 'c05e' and ZDeviceID_ == '0830':
        TypeFromCluster = 'Ikea_Round_5b'
    elif ProfileID_ == 'c05e' and ZDeviceID_ == '0820':
        TypeFromCluster = 'Ikea_Round_OnOff'
    elif cluster == "0001": TypeFromCluster = "Voltage"
    elif cluster == "0006": TypeFromCluster = "Switch"
    elif cluster == "0008": TypeFromCluster = "LvlControl"
    elif cluster == "000c" and not create_: TypeFromCluster = "XCube"
    elif cluster == "0012" and not create_: TypeFromCluster = "XCube"
    elif cluster == "0101": TypeFromCluster = "Vibration"
    elif cluster == "0102": TypeFromCluster = "WindowCovering"
    elif cluster == "0201": TypeFromCluster = "Temp/ThermoSetpoint/ThermoMode"
    elif cluster == "0300": TypeFromCluster = "ColorControl"
    elif cluster == "0400": TypeFromCluster = "Lux"
    elif cluster == "0402": TypeFromCluster = "Temp"
    elif cluster == "0403": TypeFromCluster = "Baro"
    elif cluster == "0405": TypeFromCluster = "Humi"
    elif cluster == "0406": TypeFromCluster = "Motion"
    elif cluster == "0702": TypeFromCluster = "Power/Meter"
    elif cluster == "0500": TypeFromCluster = "Door"
    elif cluster == "0502": TypeFromCluster = "AlarmWD"
    elif cluster == "0b04": TypeFromCluster = "Power/Meter"

    elif cluster == "fc00" : TypeFromCluster = 'LvlControl'   # RWL01 - Hue remote

    elif cluster == "fc21" : TypeFromCluster = 'BSO'   # PXF Cluster from Profalux

    # Propriatory Cluster. Plugin Cluster
    elif cluster == "rmt1": TypeFromCluster = "Ikea_Round_5b"

    # Xiaomi Strenght for Vibration
    elif cluster == "Strenght": TypeFromCluster = "Strenght"
    # Xiaomi Orientation for Vibration
    elif cluster == "Orientation": TypeFromCluster = "Orientation"

    return TypeFromCluster

def subtypeRGB_FromProfile_Device_IDs( EndPoints, Model, ProfileID, ZDeviceID, ColorInfos=None):

        # Type 0xF1    pTypeColorSwitch
        # Switchtype 7 STYPE_Dimmer
        # SubType sTypeColor_RGB_W                0x01 // RGB + white, either RGB or white can be lit
        # SubType sTypeColor_White                0x03 // Monochrome white
        # SubType sTypeColor_RGB_CW_WW            0x04 // RGB + cold white + warm white, either RGB or white can be lit
        # SubType sTypeColor_LivCol               0x05
        # SubType sTypeColor_RGB_W_Z              0x06 // Like RGBW, but allows combining RGB and white
        # The test should be done in an other way ( ProfileID for instance )
        # default: SubType sTypeColor_RGB_CW_WW_Z 0x07 // Like RGBWW, # but allows combining RGB and white

    ColorControlRGB   = 0x02 # RGB color palette / Dimable
    ColorControlRGBWW = 0x04  # RGB + WW
    ColorControlFull  = 0x07  # 3 Color palettes widget
    ColorControlWW    = 0x08  # WW


    Subtype = None
    ZLL_Commissioning = False

    ColorMode = 0
    if ColorInfos:
        if 'ColorMode' in ColorInfos:
            ColorMode = ColorInfos['ColorMode']

    for iterEp in EndPoints:
        if '1000' in  iterEp:
            ZLL_Commissioning = True
            break

    # Device specifics section
    if Model:
        if Model == 'lumi.light.aqcn02':    # Aqara Bulb White Dim
            Subtype = ColorControlWW

    # Philipps Hue
    if Subtype is None and ProfileID == "a1e0": 
        if ZDeviceID == "0061":
            Subtype = ColorControlRGBWW

    # ZLL LightLink
    if Subtype is None and  ProfileID == 'c05e': 
        # We should Check that ZLL Commissioning is also there. Cluster 0x1000
        if ZDeviceID == '0100': # LED1622G12.Tradfri ou phillips hue white
            pass
        elif ZDeviceID == '0200': # ampoule Tradfri LED1624G9
            Subtype = ColorControlFull
        elif ZDeviceID == '0210': # 
            Subtype = ColorControlRGBWW
        elif ZDeviceID == '0220': # ampoule Tradfi LED1545G12.Tradfri
            Subtype = ColorControlWW
            pass

    # Home Automation / ZHA
    if Subtype is None and ProfileID == '0104': # Home Automation
        if ZLL_Commissioning and ZDeviceID == '0100': # Most likely IKEA Tradfri bulb LED1622G12
            Subtype = ColorControlWW
        elif ZDeviceID == '0101': # Dimable light
            pass
        elif ZDeviceID == '0102': # Color dimable light
            Subtype = ColorControlFull
        elif ZDeviceID == '010c': # White color temperature light
            Subtype = ColorControlWW
        elif ZDeviceID == '010d': # Extended color light
            # ZBT-ExtendedColor /  Müller-Licht 44062 "tint white + color" (LED E27 9,5W 806lm 1.800-6.500K RGB)
            Subtype = ColorControlRGBWW


    if Subtype is None and ColorInfos:
        if ColorMode == 2:
            Subtype = ColorControlWW
        elif ColorMode == 1:
            Subtype = ColorControlRGB
        else:
            Subtype = ColorControlFull

    if Subtype is None:
        Subtype = ColorControlFull

 
    return Subtype
