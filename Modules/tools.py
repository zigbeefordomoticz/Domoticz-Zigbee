#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module : z_tools.py


    Description: Zigate toolbox
"""
import binascii
import time
import datetime
import struct
import json

import Domoticz

from Classes.AdminWidgets import AdminWidgets
from Modules.database import WriteDeviceList

def is_hex(s):

    hex_digits = set("0123456789abcdefABCDEF")
    return all(char in hex_digits for char in s)

def returnlen(taille , value) :
    while len(value)<taille:
        value="0"+value
    return str(value)


def Hex_Format(taille, value):
    value = hex(int(value))[2:]
    if len(value) > taille:
        return 'f' * taille
    while len(value)<taille:
        value="0"+value
    return str(value)

def voltage2batteryP( voltage, volt_max, volt_min):
    
    if voltage > volt_max: 
        ValueBattery = 100

    elif voltage < volt_min: 
        ValueBattery = 0

    else: 
        ValueBattery = 100 - round( ((volt_max - (voltage))/(volt_max - volt_min)) * 100 )

    return round(ValueBattery)

def IEEEExist(self, IEEE):
    #check in ListOfDevices for an existing IEEE
    return IEEE in self.ListOfDevices and IEEE != ''

def NwkIdExist( self, Nwkid):
    return Nwkid in self.ListOfDevices

def getSaddrfromIEEE(self, IEEE) :
    # Return Short Address if IEEE found.

    if IEEE != '' :
        for sAddr in self.ListOfDevices :
            if self.ListOfDevices[sAddr]['IEEE'] == IEEE :
                return sAddr
    return ''
    
def getListOfEpForCluster( self, NwkId, SearchCluster):
    """
    NwkId: Device
    Cluster: Cluster for which we are looking for Ep

    return List of Ep where Cluster is found and at least ClusterType is not empty. (If ClusterType is empty, this 
    indicate that there is no Widget associated and all informations in Ep are not used)
    In case ClusterType exists and not empty at Global Level, then just return the list of Ep for which Cluster is found
    """

    EpList = []
    oldFashion = 'ClusterType' in self.ListOfDevices[NwkId] and self.ListOfDevices[NwkId]['ClusterType'] != {} and self.ListOfDevices[NwkId]['ClusterType'] != ''
    for Ep in self.ListOfDevices[NwkId]['Ep']:
        if SearchCluster not in self.ListOfDevices[NwkId]['Ep'][ Ep ]:
            #Domoticz.Log("---- Cluster %s on %s" %( SearchCluster, str(self.ListOfDevices[NwkId]['Ep'][Ep] ) ))
            continue

        if oldFashion:
            EpList.append( Ep )
        else:
            if 'ClusterType' in self.ListOfDevices[NwkId]['Ep'][Ep] and \
                    self.ListOfDevices[NwkId]['Ep'][Ep]['ClusterType'] != {} and \
                    self.ListOfDevices[NwkId]['Ep'][Ep]['ClusterType'] != '' :
                EpList.append( Ep )
            #else:
            #    Domoticz.Log("------------> Skiping Cluster: %s Clustertype not found in %s" %(  SearchCluster, str(self.ListOfDevices[ NwkId]['Ep'][Ep]) ) )

    #Domoticz.Log("----------> NwkId: %s Ep: %s Cluster: %s oldFashion: %s EpList: %s" %( NwkId, Ep, SearchCluster, oldFashion, EpList))
    return EpList

def getEPforClusterType( self, NWKID, ClusterType ) :

    EPlist = []
    for EPout in self.ListOfDevices[NWKID]['Ep'] :
        if 'ClusterType' in self.ListOfDevices[NWKID]['Ep'][EPout]:
            for key in self.ListOfDevices[NWKID]['Ep'][EPout]['ClusterType'] :
                if self.ListOfDevices[NWKID]['Ep'][EPout]['ClusterType'][key].find(ClusterType) >= 0 :
                    EPlist.append(str(EPout))
                    break
    return EPlist

def getClusterListforEP( self, NWKID, Ep ) :

    ClusterList = []

    for cluster in ['fc00', '0500', '0502', '0406', '0400', '0402', '0001']:
        if cluster in self.ListOfDevices[NWKID]['Ep'][Ep]:
            ClusterList.append(cluster)

    if self.ListOfDevices[NWKID]['Ep'][Ep] :
        for cluster in self.ListOfDevices[NWKID]['Ep'][Ep] :
            if cluster not in  ('ClusterType', 'Type', 'ColorMode') and \
                    cluster not in ClusterList:
                ClusterList.append(cluster)
    return ClusterList

def getEpForCluster( self, nwkid, ClusterId):
    """ 
    Return the Ep or a list of Ep associated to the ClusterId 
    If not found return Ep: 01
    """

    EPout = []
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if ClusterId in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout.append( tmpEp )

    if not EPout:
        return EPout

    if len(self.ListOfDevices[nwkid]['Ep']) == 1:
        return [ self.ListOfDevices[nwkid]['Ep'].keys() ]

    return EPout

def DeviceExist(self, Devices, lookupNwkId , lookupIEEE = ''):
    """
    DeviceExist 
        check if the Device is existing in the ListOfDevice.
        lookupNwkId Mandatory field
        lookupIEEE Optional
    Return
        True if object found
        False if not found
    """

    found = False
    #Validity check
    if lookupNwkId == '':
        return False

    #1- Check if found in ListOfDevices
    #   Verify that Status is not 'UNKNOWN' otherwise condider not found
    if lookupNwkId in self.ListOfDevices:
        if 'Status' in self.ListOfDevices[lookupNwkId] :
            # Found, let's check the Status
            if self.ListOfDevices[lookupNwkId]['Status'] != 'UNKNOWN':
                found = True

    # 2- We might have found it with the lookupNwkId 
    # If we didnt find it, we should check if this is not a new ShortId  
    if lookupIEEE:
        if lookupIEEE not in self.IEEE2NWK:
            # Not found
            return found
        
        # We found IEEE, let's get the Short Address 
        exitsingNwkId = self.IEEE2NWK[ lookupIEEE ]
        if exitsingNwkId == lookupNwkId:
            # Everything fine, we have found it
            # and this is the same ShortId as the one existing
            return True

        if exitsingNwkId not in self.ListOfDevices:
            # Should not happen
            # We have an entry in IEEE2NWK, but no corresponding
            # in ListOfDevices !!
            # Let's clenup
            del self.IEEE2NWK[ lookupIEEE ]
            return False

        if 'Status' not in self.ListOfDevices[ exitsingNwkId ]:
            # Should not happen
            # That seems not correct
            # We might have to do some cleanup here !
            # Cleanup
            # Delete the entry in IEEE2NWK as it will be recreated in Decode004d
            del self.IEEE2NWK[ lookupIEEE ]

            # Delete the all Data Structure
            del self.ListOfDevices[ exitsingNwkId ]
            return False

        if self.ListOfDevices[ exitsingNwkId ]['Status'] in ( '004d', '0045', '0043', '8045', '8043', 'UNKNOW'):
            # We are in the discovery/provisioning process,
            # and the device got a new Short Id
            # we need to restart from the begiging and remove all existing datastructutre.
            # In case we receive asynchronously messages (which should be possible), they must be
            # droped in the corresponding Decodexxx function
            Domoticz.Status("DeviceExist - Device %s changed its ShortId: from %s to %s during provisioing. Restarting !" 
                %( lookupIEEE, exitsingNwkId , lookupNwkId ))

            # Delete the entry in IEEE2NWK as it will be recreated in Decode004d
            del self.IEEE2NWK[ lookupIEEE ]

            # Delete the all Data Structure
            del self.ListOfDevices[ exitsingNwkId ]

            return False

        # At that stage, we have found an entry for the IEEE, but doesn't match
        # the coming Short Address lookupNwkId.
        # Most likely , device has changed its NwkId   
        found = True        
        reconnectNWkDevice( self, lookupNwkId, lookupIEEE, exitsingNwkId)

        # Let's send a Notfification
        devName = ''
        for x in Devices:
            if Devices[x].DeviceID == lookupIEEE:
                devName = Devices[x].Name
                break
        self.adminWidgets.updateNotificationWidget( Devices, 'Reconnect %s with %s/%s' %( devName, lookupNwkId, lookupIEEE ))
 
    return found

def reconnectNWkDevice( self, newNWKID, IEEE, oldNWKID):

    # We got a new Network ID for an existing IEEE. So just re-connect.
    # - mapping the information to the new newNWKID
    if oldNWKID not in self.ListOfDevices:
        return

    self.ListOfDevices[newNWKID] = dict(self.ListOfDevices[oldNWKID])
    self.IEEE2NWK[IEEE] = newNWKID

    Domoticz.Status("NetworkID : " +str(newNWKID) + " is replacing " +str(oldNWKID) + " and is attached to IEEE : " +str(IEEE) )

    if 'ZDeviceName' in self.ListOfDevices[ newNWKID ]:
        devName = self.ListOfDevices[ newNWKID ]['ZDeviceName']

    if self.groupmgt:
        # We should check if this belongs to a group
        self.groupmgt.update_due_to_nwk_id_change( oldNWKID, newNWKID)

    # We will also reset ReadAttributes
    if 'ReadAttributes' in self.ListOfDevices[newNWKID]:
        del self.ListOfDevices[newNWKID]['ReadAttributes']

    if 'ConfigureReporting' in self.ListOfDevices[newNWKID]:
        del self.ListOfDevices[newNWKID]['ConfigureReporting']

    self.ListOfDevices[newNWKID]['Heartbeat'] = 0

    # MostLikely exitsingKey(the old NetworkID)  is not needed any more
    removeNwkInList( self, oldNWKID )    

    if self.ListOfDevices[newNWKID]['Status'] in ( 'Left', 'Leave') :
        Domoticz.Log("DeviceExist - Update Status from %s to 'inDB' for NetworkID : %s" %(self.ListOfDevices[newNWKID]['Status'], newNWKID) )
        self.ListOfDevices[newNWKID]['Status'] = 'inDB'
        self.ListOfDevices[newNWKID]['Heartbeat'] = 0
        WriteDeviceList(self, 0)

    return

def removeNwkInList( self, NWKID) :

    del self.ListOfDevices[NWKID]



def removeDeviceInList( self, Devices, IEEE, Unit ) :
    # Most likely call when a Device is removed from Domoticz
    # This is a tricky one, as you might have several Domoticz devices attached to this IoT and so you must remove only the corredpoing part.
    # Must seach in the NwkID dictionnary and remove only the corresponding device entry in the ClusterType.
    # In case there is no more ClusterType , then the full entry can be removed

    if IEEE in self.IEEE2NWK :
        key = self.IEEE2NWK[IEEE]
        ID = Devices[Unit].ID

        Domoticz.Log("removeDeviceInList - request to remove Device: %s with IEEE: %s " %(key, IEEE))

        if 'ClusterTye' in self.ListOfDevices[key]:               # We are in the old fasho V. 3.0.x Where ClusterType has been migrated from Domoticz
            if  str(ID) in self.ListOfDevices[key]['ClusterType']  :
                Domoticz.Log("removeDeviceInList - removing : "+str(ID) +" in "+str(self.ListOfDevices[key]['ClusterType']) )
                del self.ListOfDevices[key]['ClusterType'][ID] # Let's remove that entry
        else :
            for tmpEp in self.ListOfDevices[key]['Ep'] : 
                # Search this DeviceID in ClusterType
                if 'ClusterType' in self.ListOfDevices[key]['Ep'][tmpEp]:
                    if str(ID) in self.ListOfDevices[key]['Ep'][tmpEp]['ClusterType'] :
                        Domoticz.Log("removeDeviceInList - removing : "+str(ID) +" in " +str(tmpEp) + " - " +str(self.ListOfDevices[key]['Ep'][tmpEp]['ClusterType']) )
                        del self.ListOfDevices[key]['Ep'][tmpEp]['ClusterType'][str(ID)]

        # Finaly let's see if there is any Devices left in this .
        emptyCT = True
        if 'ClusterType' in self.ListOfDevices[key]: # Empty or Doesn't exist
            Domoticz.Log("removeDeviceInList - exitsing Global 'ClusterTpe'")
            if self.ListOfDevices[key]['ClusterType'] != {}:
                emptyCT = False
        for tmpEp in self.ListOfDevices[key]['Ep'] : 
            if 'ClusterType' in self.ListOfDevices[key]['Ep'][tmpEp]:
                Domoticz.Log("removeDeviceInList - exitsing Ep 'ClusterTpe'")
                if self.ListOfDevices[key]['Ep'][tmpEp]['ClusterType'] != {}:
                    emptyCT = False
        
        if emptyCT :     
            del self.ListOfDevices[key]
            del self.IEEE2NWK[IEEE]

            self.adminWidgets.updateNotificationWidget( Devices, 'Device fully removed %s with IEEE: %s' %( Devices[Unit].Name, IEEE ))
            Domoticz.Status('Device %s with IEEE: %s fully removed from the system.' %(Devices[Unit].Name, IEEE))

            return True
        return False



def initDeviceInList(self, Nwkid) :
    if Nwkid not in self.ListOfDevices:
        if Nwkid != '' :
            self.ListOfDevices[Nwkid]={}
            self.ListOfDevices[Nwkid]['Version']="3"
            self.ListOfDevices[Nwkid]['ZDeviceName']=""
            self.ListOfDevices[Nwkid]['Status']="004d"
            self.ListOfDevices[Nwkid]['SQN']=''
            self.ListOfDevices[Nwkid]['Ep']={}
            self.ListOfDevices[Nwkid]['Heartbeat']="0"
            self.ListOfDevices[Nwkid]['RIA']="0"
            self.ListOfDevices[Nwkid]['RSSI']={}
            self.ListOfDevices[Nwkid]['Battery']={}
            self.ListOfDevices[Nwkid]['Model']= ''
            self.ListOfDevices[Nwkid]['MacCapa']={}
            self.ListOfDevices[Nwkid]['IEEE']={}
            self.ListOfDevices[Nwkid]['Type']={}
            self.ListOfDevices[Nwkid]['ProfileID']={}
            self.ListOfDevices[Nwkid]['ZDeviceID']={}
            self.ListOfDevices[Nwkid]['App Version']=''
            self.ListOfDevices[Nwkid]['Attributes List']={}
            self.ListOfDevices[Nwkid]['DeviceType']=''
            self.ListOfDevices[Nwkid]['HW Version']=''
            self.ListOfDevices[Nwkid]['Last Cmds']= []
            self.ListOfDevices[Nwkid]['LogicalType']=''
            self.ListOfDevices[Nwkid]['Manufacturer']=''
            self.ListOfDevices[Nwkid]['Manufacturer Name']=''
            self.ListOfDevices[Nwkid]['NbEp']=''
            self.ListOfDevices[Nwkid]['PowerSource']=''
            self.ListOfDevices[Nwkid]['ReadAttributes']={}
            self.ListOfDevices[Nwkid]['ReceiveOnIdle']=''
            self.ListOfDevices[Nwkid]['Stack Version']=''
            self.ListOfDevices[Nwkid]['Stamp']={}
            self.ListOfDevices[Nwkid]['ZCL Version']=''
            self.ListOfDevices[Nwkid]['Health']=''
        
def timeStamped( self, key, Type ):
    if key in self.ListOfDevices:
        if 'Stamp' not in self.ListOfDevices[key]:
            self.ListOfDevices[key]['Stamp'] = {}
            self.ListOfDevices[key]['Stamp']['Time'] = {}
            self.ListOfDevices[key]['Stamp']['MsgType'] = {}
        self.ListOfDevices[key]['Stamp']['Time'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
        self.ListOfDevices[key]['Stamp']['MsgType'] = "%4x" %(Type)


def updSQN( self, key, newSQN) :

    if key not in self.ListOfDevices:
        return
    if newSQN == {}:
        return
    if newSQN is None:
        return

    #Domoticz.Log("-->SQN updated %s from %s to %s" %(key, self.ListOfDevices[key]['SQN'], newSQN))
    self.ListOfDevices[key]['SQN'] = newSQN
    return

def updRSSI( self, key, RSSI):

    if key not in self.ListOfDevices:
        return

    if 'RSSI' not in self.ListOfDevices[ key ]:
        self.ListOfDevices[ key ]['RSSI'] = {}
        
    if RSSI == '00':
        return
    
    if is_hex( RSSI ): # Check if the RSSI is Correct

        self.ListOfDevices[ key ]['RSSI'] = int( RSSI, 16)

        if 'RollingRSSI' not in self.ListOfDevices[ key ]:
           self.ListOfDevices[ key ]['RollingRSSI'] = []   

        if len(self.ListOfDevices[key]['RollingRSSI']) > 10:
            del self.ListOfDevices[key]['RollingRSSI'][0]
        self.ListOfDevices[ key ]['RollingRSSI'].append( int(RSSI, 16))

    return

#### Those functions will be use with the new DeviceConf structutre

def getTypebyCluster( self, Cluster ) :
    clustersType = { '0405' : 'Humi',
                    '0406' : 'Motion',
                    '0400' : 'Lux',
                    '0403' : 'Baro',
                    '0402' : 'Temp',
                    '0006' : 'Switch',
                    '0500' : 'Door',
                    '0012' : 'XCube',
                    '000c' : 'XCube',
                    '0008' : 'LvlControl',
                    '0300' : 'ColorControl'
            }

    if Cluster == '' or Cluster is None :
        return ''

    if Cluster in clustersType :
        return clustersType[Cluster]

    return ''

def getListofClusterbyModel( self, Model , InOut ) :
    """
    Provide the list of clusters attached to Ep In
    """
    listofCluster = list()
    if InOut == '' or InOut is None :
        return listofCluster
    if InOut != 'Epin' and InOut != 'Epout' :
        Domoticz.Error( "getListofClusterbyModel - Argument error : " +Model + " " +InOut )
        return ''

    if Model in self.DeviceConf :
        if InOut in self.DeviceConf[Model]:
            for ep in self.DeviceConf[Model][InOut] :
                seen = ''
                for cluster in sorted(self.DeviceConf[Model][InOut][ep]) :
                    if cluster in ( 'ClusterType', 'Type', 'ColorMode') or  cluster == seen :
                        continue
                    listofCluster.append( cluster )
                    seen = cluster
    return listofCluster


def getListofInClusterbyModel( self, Model ) :
    return getListofClusterbyModel( self, Model, 'Epin' )

def getListofOutClusterbyModel( self, Model ) :
    return getListofClusterbyModel( self, Model, 'Epout' )

    
def getListofTypebyModel( self, Model ):
    """
    Provide a list of Tuple ( Ep, Type ) for a given Model name if found. Else return an empty list
        Type is provided as a list of Type already.
    """
    EpType = []
    if Model in self.DeviceConf :
        for ep in self.DeviceConf[Model]['Epin'] :
            if 'Type' in self.DeviceConf[Model]['Epin'][ep]:
                EpinType = ( ep, getListofType( self.DeviceConf[Model]['Epin'][ep]['Type']) )
                EpType.append(EpinType)
    return EpType
    
def getModelbyZDeviceIDProfileID( self, ZDeviceID, ProfileID):
    """
    Provide a Model for a given ZdeviceID, ProfileID
    """
    for model in self.DeviceConf :
        if self.DeviceConf[model]['ProfileID'] == ProfileID and self.DeviceConf[model]['ZDeviceID'] == ZDeviceID :
            return model
    return ''


def getListofType( self, Type ):
    """
    For a given DeviceConf Type "Plug/Power/Meters" return a list of Type [ 'Plug', 'Power', 'Meters' ]
    """

    if Type == '' or Type is None :
        return ''
    retList = []
    retList= Type.split("/")
    return retList

def hex_to_rgb(value):
    """Return (red, green, blue) for the color given as #rrggbb."""
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

def hex_to_xy(h):
    ''' convert hex color to xy tuple '''
    return rgb_to_xy(hex_to_rgb(h))

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def rgb_to_xy(rgb):
    ''' convert rgb tuple to xy tuple '''
    red, green, blue = rgb
    r = ((red + 0.055) / (1.0 + 0.055))**2.4 if (red > 0.04045) else (red / 12.92)
    g = ((green + 0.055) / (1.0 + 0.055))**2.4 if (green > 0.04045) else (green / 12.92)
    b = ((blue + 0.055) / (1.0 + 0.055))**2.4 if (blue > 0.04045) else (blue / 12.92)
    X = r * 0.664511 + g * 0.154324 + b * 0.162028
    Y = r * 0.283881 + g * 0.668433 + b * 0.047685
    Z = r * 0.000088 + g * 0.072310 + b * 0.986039
    cx = 0
    cy = 0
    if (X + Y + Z) != 0:
        cx = X / (X + Y + Z)
        cy = Y / (X + Y + Z)
    return (cx, cy)

def xy_to_rgb(x, y, brightness=1):

    x = 0.313
    y = 0.329

    x = float(x)
    y = float(y)
    z = 1.0 - x - y

    Y = brightness
    X = (Y / y) * x
    Z = (Y / y) * z

    r =  X * 1.656492 - Y * 0.354851 - Z * 0.255038
    g = -X * 0.707196 + Y * 1.655397 + Z * 0.036152
    b =  X * 0.051713 - Y * 0.121364 + Z * 1.011530

    r = 12.92 * r if r <= 0.0031308 else (1.0 + 0.055) * pow(r, (1.0 / 2.4)) - 0.055
    g = 12.92 * g if g <= 0.0031308 else (1.0 + 0.055) * pow(g, (1.0 / 2.4)) - 0.055
    b = 12.92 * b if b <= 0.0031308 else (1.0 + 0.055) * pow(b, (1.0 / 2.4)) - 0.055

    return {'r': round(r * 255, 3), 'g': round(g * 255, 3), 'b': round(b * 255, 3)}



def rgb_to_hsl(rgb):
    ''' convert rgb tuple to hls tuple '''
    r, g, b = rgb
    r = float(r/255)
    g = float(g/255)
    b = float(b/255)
    high = max(r, g, b)
    low = min(r, g, b)
    h, s, l = ((high + low) / 2,)*3

    if high == low:
        h = 0.0
        s = 0.0
    else:
        d = high - low
        s = d / (2 - high - low) if l > 0.5 else d / (high + low)
        h = {
            r: (g - b) / d + (6 if g < b else 0),
            g: (b - r) / d + 2,
            b: (r - g) / d + 4,
        }[high]
        h /= 6

    return h, s, l

def decodeMacCapa( inMacCapa ):

    maccap = int(inMacCapa,16)
    alternatePANCOORDInator = (maccap & 0b00000001)
    deviceType              = (maccap & 0b00000010) >> 1
    powerSource             = (maccap & 0b00000100) >> 2
    receiveOnIddle          = (maccap & 0b00001000) >> 3
    securityCap             = (maccap & 0b01000000) >> 6
    allocateAddress         = (maccap & 0b10000000) >> 7

    MacCapa = []
    if alternatePANCOORDInator:
        MacCapa.append('Able to act Coordinator')
    if deviceType:
        MacCapa.append('Full-Function Device')
    else:
        MacCapa.append('Reduced-Function Device')
    if powerSource:
        MacCapa.append('Main Powered')
    if receiveOnIddle:
        MacCapa.append('Receiver during Idle')
    if securityCap:
        MacCapa.append('High security')
    else:
        MacCapa.append('Standard security')
    if allocateAddress:
        MacCapa.append('NwkAddr should be allocated')
    else:
        MacCapa.append('NwkAddr need to be allocated')
    return MacCapa

        
def ReArrangeMacCapaBasedOnModel( self, nwkid, inMacCapa):
    """
    Function to check if the MacCapa should not be updated based on Model.
    As they are some bogous Devices which tell they are Main Powered and they are not !

    Return the old or the revised MacCapa and eventually fix some Attributes
    """

    if nwkid not in self.ListOfDevices:
        Domoticz.Error("%s not known !!!" %nwkid)
        return inMacCapa

    if 'Model' not in self.ListOfDevices[nwkid]:
        return inMacCapa

    if self.ListOfDevices[nwkid]['Model'] == 'TI0001':
        # Livol Switch, must be converted to Main Powered
        # Patch some status as Device Annouced doesn't provide much info
        self.ListOfDevices[nwkid]['LogicalType'] = 'Router'
        self.ListOfDevices[nwkid]['DevideType'] = 'FFD'
        self.ListOfDevices[nwkid]['MacCapa'] = '8e'
        self.ListOfDevices[nwkid]['PowerSource'] = 'Main'
        return '8e'

    if self.ListOfDevices[nwkid]['Model'] in ( 'lumi.remote.b686opcn01', 'lumi.remote.b486opcn01', 'lumi.remote.b286opcn01', 
                                             'lumi.remote.b686opcn01-bulb','lumi.remote.b486opcn01-bulb','lumi.remote.b286opcn01-bulb',
                                             'lumi.remote.b686opcn01' ):
        # Aqara Opple Switch, must be converted to Battery Devices
        self.ListOfDevices[nwkid]['MacCapa'] = '80'
        self.ListOfDevices[nwkid]['PowerSource'] = 'Battery'
        if (
            'Capability' in self.ListOfDevices[nwkid]
            and 'Main Powered' in self.ListOfDevices[nwkid]['Capability']
        ):
            self.ListOfDevices[nwkid]['Capability'].remove( 'Main Powered')
        return '80'

    return inMacCapa

def mainPoweredDevice( self, nwkid):
    """
    return True is it is Main Powered device
    return False if it is not Main Powered
    """

    if nwkid not in self.ListOfDevices:
        Domoticz.Log("mainPoweredDevice - Unknown Device: %s" %nwkid)
        return False


    mainPower = False
    if (
        'MacCapa' in self.ListOfDevices[nwkid]
        and self.ListOfDevices[nwkid]['MacCapa'] != {}
    ):
        mainPower = ( '8e' == self.ListOfDevices[nwkid]['MacCapa']) or ( '84' ==  self.ListOfDevices[nwkid]['MacCapa'] )

    if (
        not mainPower
        and 'PowerSource' in self.ListOfDevices[nwkid]
        and self.ListOfDevices[nwkid]['PowerSource'] != {}
    ):
        mainPower = ('Main' == self.ListOfDevices[nwkid]['PowerSource'])

    # We need to take in consideration that Livolo is reporting a MacCapa of 0x80
    # That Aqara Opple are reporting MacCap 0x84 while they are Battery devices
    if 'Model' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['Model'] in ('lumi.remote.b686opcn01', 'lumi.remote.b486opcn01', 'lumi.remote.b286opcn01',
                                                  'lumi.remote.b686opcn01-bulb', 'lumi.remote.b486opcn01-bulb', 'lumi.remote.b286opcn01-bulb'):
            mainPower = False
        if self.ListOfDevices[nwkid]['Model'] == 'TI0001':
            mainPower = True

    return mainPower


def loggingMessages( self, msgtype, sAddr=None, ieee=None, RSSI=None, SQN=None):

    if not self.pluginconf.pluginConf['logFORMAT']:
        return
    if sAddr == ieee == None:
        return
    _debugMatchId =  self.pluginconf.pluginConf['debugMatchId'].lower()
    if sAddr is None:
        # Get sAddr from IEEE
        sAddr = ''
        if ieee in self.IEEE2NWK:
            sAddr = self.IEEE2NWK[ieee]
    if ieee is None:
        # Get ieee from sAddr
        ieee = ''
        if sAddr in self.ListOfDevices:
            ieee = self.ListOfDevices[sAddr]['IEEE']
    if _debugMatchId != 'ffff' and _debugMatchId != sAddr:
        # If not matching _debugMatchId
        return

    zdevname = ''
    if sAddr in self.ListOfDevices:
        if 'ZDeviceName' in  self.ListOfDevices[sAddr]:
            zdevname = self.ListOfDevices[sAddr]['ZDeviceName']

    Domoticz.Log("Device activity for | %4s | %14s | %4s | %16s | %3s | 0x%02s |" \
        %( msgtype, zdevname, sAddr, ieee, int(RSSI,16), SQN))


def lookupForIEEE( self, nwkid , reconnect=False):

    """
    Purpose of this function is to search a Nwkid in the Neighbours table and find an IEEE
    """

    Domoticz.Log("lookupForIEEE - looking for %s in Neighbourgs table" %nwkid)
    for key in self.ListOfDevices:
        if 'Neighbours' not in self.ListOfDevices[key]:
            continue

        if len(self.ListOfDevices[key]['Neighbours']) == 0:
            continue

        # We are interested only on the last one
        lastScan = self.ListOfDevices[key]['Neighbours'][-1]
        for item in lastScan[ 'Devices' ]:            
            if nwkid not in item:
                continue
            # Found !
            if '_IEEE' in item[ nwkid ]:
                ieee = item[ nwkid ]['_IEEE']
                oldNWKID = 'none'
                if ieee in self.IEEE2NWK:
                    oldNWKID = self.IEEE2NWK[ ieee ]
                    if oldNWKID not in self.ListOfDevices:
                        Domoticz.Log("lookupForIEEE found an inconsitency %s nt existing but pointed by %s"
                            %( oldNWKID, ieee ))
                        del self.IEEE2NWK[ ieee ]
                        return None
                    if reconnect:
                        reconnectNWkDevice( self, nwkid, ieee, oldNWKID)
                Domoticz.Log("lookupForIEEE found IEEE %s for %s in %s known as %s  Neighbourg table" %(ieee, nwkid, oldNWKID, key))
                return ieee

    return None

def lookupForParentDevice( self, nwkid= None, ieee=None):

    """
    Purpose is to find a router to which this device is connected to.
    the IEEE will be returned if found otherwise None
    """

    if nwkid is None and ieee is None:
        return None
    
    # Got Short Address in Input
    if nwkid and ieee is None:
        if nwkid not in self.ListOfDevices:
            return
        if 'IEEE' in self.ListOfDevices[ nwkid ]:
            ieee = self.ListOfDevices[ nwkid ]['IEEE']

    # Got IEEE in Input
    if ieee and nwkid is None:
        if ieee not in self.IEEE2NWK:
            return
        nwkid = self.IEEE2NWK[ nwkid ]

    if mainPoweredDevice( self, nwkid):
        return ieee

    for PotentialRouter in self.ListOfDevices:
        if 'Neighbours' not in self.ListOfDevices[PotentialRouter]:
            continue
        if len(self.ListOfDevices[PotentialRouter]['Neighbours']) == 0:
            continue
        # We are interested only on the last one
        lastScan = self.ListOfDevices[PotentialRouter]['Neighbours'][-1]

        for item in lastScan[ 'Devices' ]:          
            if nwkid not in item:
                continue
            # found and PotentialRouter is one router
            if 'IEEE' not in self.ListOfDevices[ PotentialRouter ]:
                # This is problematic, let's try an other candidate
                continue

            return self.ListOfDevices[ PotentialRouter ]['IEEE']

    #Nothing found
    return None


def checkAttribute( self, MsgSrcAddr, MsgSrcEp, MsgClusterId, MsgAttrID ):
    
    if MsgClusterId not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp]:
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = {}

    if not isinstance( self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] , dict):
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId] = {}

    if MsgAttrID not in self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId]:
        self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = {}

def checkAndStoreAttributeValue( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID, Value ):
    
    checkAttribute( self, MsgSrcAddr, MsgSrcEp,MsgClusterId, MsgAttrID )    

    self.ListOfDevices[MsgSrcAddr]['Ep'][MsgSrcEp][MsgClusterId][MsgAttrID] = Value