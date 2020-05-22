
import Domoticz

from Modules.zigateConsts import ADDRESS_MODE
from GroupMgtv2.GrpDomoticz import update_domoticz_group_device_widget
from GroupMgtv2.GrpCommands import set_kelvin_color, set_rgb_color
 
def checkIfIkeaRound5BToBeAdded( self, NwkId, ep, ieee, GrpId):
    self.logging( 'Debug', "checkIfIkeaRound5BToBeAdded - Checking if Ikea Round 5B NwkId: %s, Ep: %s, Ieee: %s, GrpIp: %s" %(NwkId, ep, ieee, GrpId))
    if ( 'Ep' in self.ListOfDevices[NwkId] and '01' in self.ListOfDevices[NwkId]['Ep'] and 'ClusterType' in self.ListOfDevices[NwkId]['Ep']['01'] ):
        for DomoDeviceUnit in self.ListOfDevices[NwkId]['Ep']['01']['ClusterType']:
            if self.ListOfDevices[NwkId]['Ep']['01']['ClusterType'][DomoDeviceUnit] == 'Ikea_Round_5b':
                self.logging( 'Debug', "checkIfIkeaRound5BToBeAdded - Found Ikea Remote in ClusterType . Unit: %s" %DomoDeviceUnit)
                self.ListOfGroups[ GrpId ]['Tradfri Remote'] = { }
                self.ListOfGroups[ GrpId ]['Tradfri Remote']['Device Addr'] = NwkId
                self.ListOfGroups[ GrpId ]['Tradfri Remote']['Ep'] = ep
                self.ListOfGroups[ GrpId ]['Tradfri Remote']['Device Id'] = DomoDeviceUnit
                self.ListOfGroups[ GrpId ]['Tradfri Remote']['IEEE'] = ieee
                self.ListOfGroups[ GrpId ]['Tradfri Remote']['Color Mode'] = None
                Domoticz.Log("--> %s" %(self.ListOfGroups[ GrpId ]))
                # 
                update_domoticz_group_device_widget( self, GrpId)
                return True

    return False

def checkIfIkeaRound5BToBeRemoved( self, NwkId, ep, ieee, GrpId):
    self.logging( 'Debug', "checkIfIkeaRound5BToBeRemoved - Checking if Ikea Round 5B NwkId: %s, Ep: %s, Ieee: %s, GrpIp: %s" %(NwkId, ep, ieee, GrpId))
    if ( 'Tradfri Remote' in self.ListOfGroups[GrpId] and ieee == self.ListOfGroups[GrpId]['Tradfri Remote']['IEEE'] ):
        self.logging( 'Debug', "checkIfIkeaRound5BToBeRemoved - Found Ikea Remote %s" %ieee)
        del self.ListOfGroups[ GrpId ]['Tradfri Remote']
        if NwkId != self.IEEE2NWK[ ieee ]:
            NwkId = self.IEEE2NWK[ ieee ]
        device = [ NwkId, ep, ieee ]
        self.logging( 'Debug', "---------> Removing %s from %s" %(str(device), str( self.ListOfGroups[ GrpId]['Devices'] )))
        
        if device in self.ListOfGroups[ GrpId]['Devices']:
            self.logging( 'Debug', "checkIfIkeaRound5BToBeRemoved - Removing it from Group Device %s" %ieee)
            self.ListOfGroups[ GrpId]['Devices'].remove( device )

        update_domoticz_group_device_widget( self, GrpId)
        return True

    return False

def Ikea5BToBeAddedToListIfExist( self, GrpId ):
    ikea5b = None
    if 'Tradfri Remote' in self.ListOfGroups[ GrpId ]:
        ikea5b =  [ self.ListOfGroups[ GrpId ]['Tradfri Remote']['Device Addr'], self.ListOfGroups[ GrpId ]['Tradfri Remote']['Ep'], 
                    self.ListOfGroups[ GrpId ]['Tradfri Remote']['IEEE'] 
                  ]
    
    return ikea5b

def Ikea_update_due_to_nwk_id_change( self, GrpId, OldNwkId, NewNwkId):

    if ( 'Tradfri Remote' in self.ListOfGroups[GrpId] and self.ListOfGroups[GrpId]['Tradfri Remote']['Device Addr'] == OldNwkId ):
        self.ListOfGroups[ GrpId]['Tradfri Remote']['Device Addr'] = NewNwkId
 

def manageIkeaTradfriRemoteLeftRight( self, NwkId, type_dir):

    # Identify which group the Remote belongs too
    Ikea5ButtonGroupId = None
    for x in self.ListOfGroups:
        if 'Tradfri Remote' not in self.ListOfGroups[x]:
            continue
        Ieee = self.ListOfGroups[ x ]['Tradfri Remote']['IEEE']
        TrueNwkId = self.IEEE2NWK[ Ieee ]

        if NwkId != self.ListOfGroups[x]['Tradfri Remote']['Device Addr'] and TrueNwkId != self.ListOfGroups[x]['Tradfri Remote']['Device Addr']:
            continue
        Ikea5ButtonGroupId = x
        break

    if Ikea5ButtonGroupId is None:
        Domoticz.Error("manageIkeaTradfriRemoteLeftRight - Remote %s not associated to any group" %NwkId)
        return

    if 'Tradfri Remote' not in self.ListOfGroups[Ikea5ButtonGroupId]:
        Domoticz.Error("manageIkeaTradfriRemoteLeftRight - Remote %s badly associated in GroupId: %s with %s" %( NwkId, Ikea5ButtonGroupId, self.ListOfGroups[Ikea5ButtonGroupId]))
        return

    if 'Color Mode' not in self.ListOfGroups[Ikea5ButtonGroupId]['Tradfri Remote']:
        Domoticz.Error("manageIkeaTradfriRemoteLeftRight - Remote %s badly associated in GroupId: %s with %s" %( NwkId, Ikea5ButtonGroupId, self.ListOfGroups[Ikea5ButtonGroupId]))
        return       
    DomoWidgetColorType = self.ListOfGroups[Ikea5ButtonGroupId]['Tradfri Remote']['Color Mode']

    if DomoWidgetColorType is None:
        Domoticz.Error("manageIkeaTradfriRemoteLeftRight - undefined Color Mode for %s" %DomoWidgetColorType)
        return

    self.logging( 'Debug', "manageIkeaTradfriRemoteLeftRight - Color model : %s" %DomoWidgetColorType)

    if DomoWidgetColorType in ('ColorControlWW'): # Will work in Kelvin
        if 'Actual T' not in self.ListOfGroups[Ikea5ButtonGroupId]['Tradfri Remote']:
            t = 128
        else:
            t = self.ListOfGroups[Ikea5ButtonGroupId]['Tradfri Remote']['Actual T']

        if type_dir == 'left':
            t -= self.pluginconf.pluginConf['TradfriKelvinStep']
            if t < 0: 
                t = 255
        elif type_dir == 'right':
            t += self.pluginconf.pluginConf['TradfriKelvinStep']
            if t > 255: 
                t = 0

        self.logging( 'Debug', "manageIkeaTradfriRemoteLeftRight - Kelvin T %s" %t)
        set_kelvin_color( self, ADDRESS_MODE['group'], Ikea5ButtonGroupId, '01', '01', t)
        self.ListOfGroups[Ikea5ButtonGroupId]['Tradfri Remote']['Actual T'] = t

    elif DomoWidgetColorType in ('ColorControlRGB','ColorControlRGBWW', 'ColorControl', 'ColorControlFull'): # Work in RGB
        # Here we will scroll R, G and B 

        PRESET_COLOR = (  
            (  10,  10,  10), # 
            ( 255,   0,   0), # Red
            (   0, 255,   0), # Green
            (   0,   0, 255), # Blue
            ( 255, 255,   0), # Yello
            (   0, 255, 255), # Aqua
            ( 255,   0, 255), # 
            ( 255, 255, 255)  # Whhite
        )

        if 'RGB' not in self.ListOfGroups[Ikea5ButtonGroupId]['Tradfri Remote']:
            seq_idx = 0
        else:
            seq_idx = self.ListOfGroups[Ikea5ButtonGroupId]['Tradfri Remote']['RGB']

        r, g, b = PRESET_COLOR[seq_idx]

        if type_dir == 'left': 
            seq_idx -= 1
        elif type_dir == 'right': 
            seq_idx += 1

        if seq_idx >= len(PRESET_COLOR): 
            seq_idx = 0
        if seq_idx < 0: 
            seq_idx = len(PRESET_COLOR) - 1

        self.logging( 'Debug', "manageIkeaTradfriRemoteLeftRight - R %s G %s B %s" %(r,g,b))
        set_rgb_color( self, ADDRESS_MODE['group'], Ikea5ButtonGroupId, '01', '01', r, g, b)
        self.ListOfGroups[Ikea5ButtonGroupId]['Tradfri Remote']['RGB'] = seq_idx