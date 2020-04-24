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
    for char in s:
        if not (char in hex_digits):
            return False
    return True

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

def IEEEExist(self, IEEE) :
    #check in ListOfDevices for an existing IEEE
    if IEEE :
        if IEEE in self.ListOfDevices and IEEE != '' :
            return True
        else:
            return False

def getSaddrfromIEEE(self, IEEE) :
    # Return Short Address if IEEE found.

    if IEEE != '' :
        for sAddr in self.ListOfDevices :
            if self.ListOfDevices[sAddr]['IEEE'] == IEEE :
                return sAddr

    Domoticz.Log("getSaddrfromIEEE no IEEE found " )

    return ''

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
    if lookupIEEE:
        if lookupIEEE not in self.IEEE2NWK:
            # Not found
            return found
        
        # We found IEEE, let's get the Short Address 
        exitsingNwkId = self.IEEE2NWK[ lookupIEEE ]
        if exitsingNwkId == lookupNwkId:
            # Everything fine, we have found it
            found = True

        elif exitsingNwkId not in self.ListOfDevices:
            # We have an entry in IEEE2NWK, but no corresponding
            # in ListOfDevices !!
            # Let's clenup
            del self.IEEE2NWK[ lookupIEEE ]
            found = False

        elif 'Status' not in self.ListOfDevices[ exitsingNwkId ]:
            # That seems not correct
            # We might have to do some cleanup here !
            found = False

        elif self.ListOfDevices[ exitsingNwkId ]['Status'] not in ( 'inDB' , 'Left', 'Leave'):
            # That seems not correct
            # Could be under Creation
            found = False

        else:
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
    self.ListOfDevices[newNWKID] = dict(self.ListOfDevices[oldNWKID])
    self.IEEE2NWK[IEEE] = newNWKID

    Domoticz.Status("NetworkID : " +str(newNWKID) + " is replacing " +str(oldNWKID) + " and is attached to IEEE : " +str(IEEE) )

    if 'ZDeviceName' in self.ListOfDevices[ newNWKID ]:
        devName = self.ListOfDevices[ newNWKID ]['ZDeviceName']

    if self.groupmgt:
        # We should check if this belongs to a group
        self.groupmgt.deviceChangeNetworkID( oldNWKID, newNWKID)

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
        else:
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
    else :
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

    
def getListofTypebyModel( self, Model ) :
    """
    Provide a list of Tuple ( Ep, Type ) for a given Model name if found. Else return an empty list
        Type is provided as a list of Type already.
    """
    EpType = list()
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


def getListofType( self, Type ) :
    """
    For a given DeviceConf Type "Plug/Power/Meters" return a list of Type [ 'Plug', 'Power', 'Meters' ]
    """

    if Type == '' or Type is None :
        return ''
    retList = list()
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

    x = float(x);
    y = float(y);
    z = 1.0 - x - y;

    Y = brightness;
    X = (Y / y) * x;
    Z = (Y / y) * z;

    r =  X * 1.656492 - Y * 0.354851 - Z * 0.255038;
    g = -X * 0.707196 + Y * 1.655397 + Z * 0.036152;
    b =  X * 0.051713 - Y * 0.121364 + Z * 1.011530;

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


def mainPoweredDevice( self, nwkid):
    """
    return True is it is Main Powered device
    return False if it is not Main Powered
    """

    if nwkid not in self.ListOfDevices:
        Domoticz.Log("mainPoweredDevice - Unknown Device: %s" %nwkid)
        return False

    mainPower = False
    if 'MacCapa' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['MacCapa'] != {}:
            mainPower = ( '8e' == self.ListOfDevices[nwkid]['MacCapa']) or ( '84' ==  self.ListOfDevices[nwkid]['MacCapa'] )

    if not mainPower and 'PowerSource' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['PowerSource'] != {}:
            mainPower = ('Main' == self.ListOfDevices[nwkid]['PowerSource'])

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
                    if reconnect:
                        reconnectNWkDevice( self, nwkid, ieee, oldNWKID)
                Domoticz.Log("lookupForIEEE found IEEE %s for %s in %s known as %s  Neighbourg table" %(ieee, nwkid, oldNWKID, key))
                return ieee

    return None
