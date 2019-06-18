#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: z_output.py

    Description: All communications towards Zigate


"""

import Domoticz
import binascii
import struct
import json

from datetime import datetime
from time import time

from Modules.consts import ZLL_DEVICES, MAX_LOAD_ZIGATE
from Modules.tools import getClusterListforEP

def ZigatePermitToJoin( self, permit ):

    if permit:
        Domoticz.Log("Request discovery mode for %s seconds " %permit)
        self.permitTojoin['Starttime'] = int(time())
        self.permitTojoin['Duration'] = permit
        sendZigateCmd(self, "0049","FFFC" + '%02x' %permit + "00")
        sendZigateCmd( self, "0014", "" ) # Request status
    else: 
        if self.permitTojoin['Duration'] != 0:
            self.permitTojoin['Starttime'] = int(time())
            self.permitTojoin['Duration'] = 0
            sendZigateCmd(self, "0049","FFFC" + '00' + "00")
            sendZigateCmd( self, "0014", "" ) # Request status
        Domoticz.Log("Request stop discovery mode")

def start_Zigate(self, Mode='Controller'):
    """
    Purpose is to run the start sequence for the Zigate
    it is call when Network is not started.

    """

    ZIGATE_MODE = ( 'Controller', 'Router' )

    if Mode not in ZIGATE_MODE:
        Domoticz.Error("start_Zigate - Unknown mode: %s" %Mode)
        return

    Domoticz.Status("ZigateConf setting Channel(s) to: %s" \
            %self.pluginconf.pluginConf['channel'])
    setChannel(self, self.pluginconf.pluginConf['channel'])
    
    if Mode == 'Controller':
        Domoticz.Status("Set Zigate as a Coordinator")
        sendZigateCmd(self, "0023","00")

        EPOCTime = datetime(2000,1,1)
        UTCTime = int((datetime.now() - EPOCTime).total_seconds())
        Domoticz.Status("ZigateConf - Setting UTC Time to : %s" %( UTCTime) )
        sendZigateCmd(self, "0016", str(UTCTime) )

        Domoticz.Status("Start network")
        sendZigateCmd(self, "0024", "" )   # Start Network
    
        Domoticz.Debug("Request network Status")
        sendZigateCmd( self, "0014", "" ) # Request status
        sendZigateCmd( self, "0009", "" ) # Request status

def sendZigateCmd(self, cmd,datas ):

    self.ZigateComm.sendData( cmd, datas )

def ReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes ):

    # frame to be send is:
    # DeviceID 16bits / EPin 8bits / EPout 8bits / Cluster 16bits / Direction 8bits / Manufacturer_spec 8bits / Manufacturer_id 16 bits / Nb attributes 8 bits / List of attributes ( 16bits )

    direction = '00'
    manufacturer_spec = '00'
    manufacturer = '0000'
    #if 'Manufacturer' in self.ListOfDevices[addr]:
    #    manufacturer = self.ListOfDevices[addr]['Manufacturer']

    if 'ReadAttributes' not in self.ListOfDevices[addr]:
        self.ListOfDevices[addr]['ReadAttributes'] = {}

    if 'Ep' not in self.ListOfDevices[addr]['ReadAttributes']:
        self.ListOfDevices[addr]['ReadAttributes']['Ep'] = {}

    if EpOut not in self.ListOfDevices[addr]['ReadAttributes']['Ep']:
        self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut] = {}

    if str(Cluster) not in self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut]:
        self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)] = {}

    if 'TimeStamps' not in self.ListOfDevices[addr]['ReadAttributes']:
        self.ListOfDevices[addr]['ReadAttributes']['TimeStamps'] = {}
        self.ListOfDevices[addr]['ReadAttributes']['TimeStamps'][EpOut+'-'+str(Cluster)] = 0

    if not isinstance(ListOfAttributes, list):
        # We received only 1 attribute
        Attr = "%04x" %(ListOfAttributes)
        lenAttr = 1
        weight = 1

        if Attr in self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)]:
            if self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] in ( '86', '8c'):    # 8c Not supported, 86 No cluster match
                Domoticz.Debug("ReadAttributeReq - Last value self.ListOfDevices[%s]['ReadAttributes']['Ep'][%s][%s][%s]: %s"
                         %(addr, EpOut, Cluster, Attr, self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] ))
                return
            Domoticz.Debug("ReadAttributeReq: %s for %s/%s" %(Attr, addr, self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr]))
    else:
        lenAttr = 0
        weight = int ((lenAttr ) / 2) + 1
        Attr =''
        Domoticz.Debug("attributes: " +str(ListOfAttributes))
        for x in ListOfAttributes:
            Attr_ = "%04x" %(x)
            if Attr_ in self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)]:
                if self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr_] != '00' and \
                        self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr_] != {} :
                    continue
                Domoticz.Debug("ReadAttributeReq: %s for %s/%s" %(Attr_, addr, self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr_]))
            Attr += Attr_
            lenAttr += 1

        if lenAttr == 0:
            return

    Domoticz.Debug("ReadAttributeReq - addr =" +str(addr) +" Cluster = " +str(Cluster) +" Attributes = " +str(ListOfAttributes) ) 
    self.ListOfDevices[addr]['ReadAttributes']['TimeStamps'][str(EpOut) + '-' + str(Cluster)] = int(time())
    datas = "02" + addr + EpIn + EpOut + Cluster + direction + manufacturer_spec + manufacturer + "%02x" %(lenAttr) + Attr
    sendZigateCmd(self, "0100", datas )

def retreive_ListOfAttributesByCluster( self, key, Ep, cluster ):

    ATTRIBUTES = { 
            '0000': [ 0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007, 0x000A, 0x000F, 0x0010, 0x0015, 0x4000],
            '0001': [ 0x0000, 0x0001, 0x0003, 0x0020, 0x0021, 0x0035 ],
            '0003': [ 0x0000],
            '0004': [ 0x0000],
            '0005': [ 0x0001, 0x0002, 0x0003, 0x0004],
            '0006': [ 0x0000],
            '0008': [ 0x0000],
            '000a': [ 0x0000],
            '0102': [ 0x0000, 0x0001, 0x0003, 0x0007, 0x0008, 0x0009, 0x000A, 0x000B, 0x0011],
            '0300': [ 0x0000, 0x0001, 0x0003, 0x0004, 0x0008],
            '0400': [ 0x0000],
            '0402': [ 0x0000],
            '0403': [ 0x0000],
            '0405': [ 0x0000],
            '0406': [ 0x0000],
            '0702': [ 0x0000, 0x0200, 0x0301, 0x0302, 0x0400]
            }

    targetAttribute = None

    if 'Attributes List' in self.ListOfDevices[key]:
        if 'Ep' in self.ListOfDevices[key]['Attributes List']:
            if Ep in self.ListOfDevices[key]['Attributes List']['Ep']:
                if cluster in self.ListOfDevices[key]['Attributes List']['Ep'][Ep]:
                    targetAttribute = []
                    Domoticz.Debug("retreive_ListOfAttributesByCluster: Attributes from Attributes List")
                    for attr in  self.ListOfDevices[key]['Attributes List']['Ep'][Ep][cluster]:
                        targetAttribute.append( int(attr,16) )

    if targetAttribute is None:
        Domoticz.Debug("retreive_ListOfAttributesByCluster: default attributes list for cluster: %s" %cluster)
        if cluster in ATTRIBUTES:
            targetAttribute = ATTRIBUTES[cluster]
        else:
            Domoticz.Log("retreive_ListOfAttributesByCluster: Missing Attribute for cluster %s" %cluster)
            targetAttribute = [ 0x0000 ]
    Domoticz.Debug("retreive_ListOfAttributesByCluster: List of Attributes for cluster %s : %s" %(cluster, targetAttribute))

    return targetAttribute


def ReadAttributeRequest_0000(self, key, fullScope=True):
    # Basic Cluster
    # The Ep to be used can be challenging, as if we are in the discovery process, the list of Eps is not yet none and it could even be that the Device has only 1 Ep != 01

    Domoticz.Debug("ReadAttributeRequest_0000 - Key: %s " %key)
    EPin = "01"
    EPout = '01'

    # Checking if Ep list is empty, in that case we are in discovery mode and we don't really know what are the EPs we can talk to.
    if self.ListOfDevices[key]['Ep'] is None or self.ListOfDevices[key]['Ep'] == {} :

        listAttributes = []
        listAttributes.append(0x0004)        # Manufacturer
        listAttributes.append(0x0005)        # Model Identifier

        Domoticz.Debug("Request Basic  via Read Attribute request: " + key + " EPout = " + "01, 03, 07" )
        ReadAttributeReq( self, key, EPin, "01", "0000", listAttributes )
        ReadAttributeReq( self, key, EPin, "02", "0000", listAttributes )
        ReadAttributeReq( self, key, EPin, "03", "0000", listAttributes )
        ReadAttributeReq( self, key, EPin, "06", "0000", listAttributes ) # Livolo
        ReadAttributeReq( self, key, EPin, "09", "0000", listAttributes )

    else:
        for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0000" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                EPout= tmpEp 

        if fullScope:
            listAttributes = []
            for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0000'):
                listAttributes.append( iterAttr )

            if 'Model' in self.ListOfDevices[key]:
                if str(self.ListOfDevices[key]['Model']).find('lumi') != -1:
                    listAttributes.append(0xff01)
                    listAttributes.append(0xff02)
                if str(self.ListOfDevices[key]['Model']).find('SML00') != -1:
                    listAttributes.append(0x0032)
                    listAttributes.append(0x0033)

        listAttr1 = listAttr2 = None
        if len(listAttributes) > 9:
            # We can send only 10 attributes at a time, we need to split into 2 packs
            listAttr1 = listAttributes[:len(listAttributes)//2]
            listAttr2 = listAttributes[len(listAttributes)//2:]

        if listAttr1 == listAttr2 == None:
            Domoticz.Debug("Request Basic  via Read Attribute request %s/%s %s" %(key, EPout, str(listAttributes)))
            ReadAttributeReq( self, key, EPin, EPout, "0000", listAttributes )
        else:
            Domoticz.Debug("Request Basic  via Read Attribute request part1 %s/%s %s" %(key, EPout, str(listAttr1)))
            ReadAttributeReq( self, key, EPin, EPout, "0000", listAttr1 )
            Domoticz.Debug("Request Basic  via Read Attribute request part2 %s/%s %s" %(key, EPout, str(listAttr2)))
            ReadAttributeReq( self, key, EPin, EPout, "0000", listAttr2 )


def ReadAttributeRequest_Ack(self, key):

    return
    ### This is disabled for now
    EPin = "01"
    EPout= "01"

    # General
    listAttributes = []
    listAttributes.append(0x0000) 
    listAttributes.append(0xff01)

    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0000" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
            EPout= tmpEp
    Domoticz.Debug("Requesting Ack for %s/%s" %(key, EPout))
    ReadAttributeReq( self, key, EPin, EPout, "0000", listAttributes )


def ReadAttributeRequest_0001(self, key):

    Domoticz.Debug("ReadAttributeRequest_0001 - Key: %s " %key)
    # Power Config
    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0001" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0001'):
        listAttributes.append( iterAttr )

    Domoticz.Debug("Request Power Config via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, EPin, EPout, "0001", listAttributes )

def ReadAttributeRequest_0006(self, key):
    # Cluster 0x0006

    Domoticz.Debug("ReadAttributeRequest_0006 - Key: %s " %key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0006" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0006'):
        listAttributes.append( iterAttr )
    Domoticz.Debug("Request OnOff status via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, "01", EPout, "0006", listAttributes)


def ReadAttributeRequest_0008(self, key):
    # Cluster 0x0008 

    Domoticz.Debug("ReadAttributeRequest_0008 - Key: %s " %key)
    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0008" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0008'):
        listAttributes.append( iterAttr )
    Domoticz.Debug("Request Control level of shutter via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, "01", EPout, "0008", 0)

def ReadAttributeRequest_0300(self, key):
    # Cluster 0x0300 - Color Control

    Domoticz.Debug("ReadAttributeRequest_0300 - Key: %s " %key)
    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0300" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0300'):
        listAttributes.append( iterAttr )

    Domoticz.Debug("Request Color Temp infos via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, EPin, EPout, "0300", listAttributes)

def ReadAttributeRequest_000C(self, key):
    # Cluster 0x000C with attribute 0x0055 / Xiaomi Power and Metering

    Domoticz.Debug("ReadAttributeRequest_000C - Key: %s " %key)

    EPin = "01"
    EPout= "02"

    """
     Attribute Type: 39 Attribut ID: 0041
     Attribute Type: 10 Attribut ID: 0051
     Attribute Type: 39 Attribut ID: 0055
     Attribute Type: 18 Attribut ID: 006f
     Attribute Type: 23 Attribut ID: 0100
     Attribute Type: 39 Attribut ID: 0105
     Attribute Type: 39 Attribut ID: 0106
    """

    EPin = "01"
    EPout= "01"
    Domoticz.Debug("Request OnOff status for Xiaomi plug via Read Attribute request: " + key + " EPout = " + EPout )
    listAttributes = []
    listAttributes.append(0x41)
    listAttributes.append(0x51)
    listAttributes.append(0x55)
    listAttributes.append(0x6f)
    listAttributes.append(0x100)
    listAttributes.append(0x105)
    listAttributes.append(0x106)

    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "000c" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    Domoticz.Debug("Request 0x000c info via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, "01", EPout, "000C", listAttributes)

def ReadAttributeRequest_0102(self, key):

    Domoticz.Debug("Request Windows Covering status Read Attribute request: " + key )
    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "000c" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0102'):
        listAttributes.append( iterAttr )

    Domoticz.Debug("Request 0x0102 info via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, "01", EPout, "000C", listAttributes)

def ReadAttributeRequest_fc00(self, key):

    EPin = "01"
    EPout= "01"
    listAttributes = []

    if 'Model' in self.ListOfDevices[key]:
        if self.ListOfDevices[key]['Model'] == 'RWL02': # Hue dimmer Switch
            listAttributes.append(0x0000)

    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "fc00" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    Domoticz.Debug("Request 0xfc00 info via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, "01", EPout, "fc00", listAttributes)

def ReadAttributeRequest_0400(self, key):

    Domoticz.Debug("ReadAttributeRequest_0400 - Key: %s " %key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0400" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0400'):
        listAttributes.append( iterAttr )

    Domoticz.Debug("Illuminance info via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, EPin, EPout, "0400", listAttributes)

def ReadAttributeRequest_0402(self, key):

    Domoticz.Debug("ReadAttributeRequest_0402 - Key: %s " %key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0402" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0402'):
        listAttributes.append( iterAttr )

    Domoticz.Debug("Temperature info via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, EPin, EPout, "0402", listAttributes)

def ReadAttributeRequest_0403(self, key):

    Domoticz.Debug("ReadAttributeRequest_0403 - Key: %s " %key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0403" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0403'):
        listAttributes.append( iterAttr )

    Domoticz.Debug("Pression Atm info via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, EPin, EPout, "0403", listAttributes)

def ReadAttributeRequest_0405(self, key):

    Domoticz.Debug("ReadAttributeRequest_0405 - Key: %s " %key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0405" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0405'):
        listAttributes.append( iterAttr )

    Domoticz.Debug("Humidity info via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, EPin, EPout, "0405", listAttributes)

def ReadAttributeRequest_0406(self, key):

    Domoticz.Debug("ReadAttributeRequest_0406 - Key: %s " %key)
    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0406" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    if str(self.ListOfDevices[key]['Model']).find('SML00') != -1:
         listAttributes.append(0x0030)
         #listAttributes.append(0x0033)
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0406'):
        listAttributes.append( iterAttr )


    Domoticz.Debug("Occupancy info via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, EPin, EPout, "0406", listAttributes)

def ReadAttributeRequest_0702(self, key):
    # Cluster 0x0702 Metering

    Domoticz.Debug("ReadAttributeRequest_0702 - Key: %s " %key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0702" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0702'):
        listAttributes.append( iterAttr )

    Domoticz.Debug("Request Metering info via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, EPin, EPout, "0702", listAttributes)


def write_attribute( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data):

    addr_mode = "02" # Short address
    direction = "00"
    lenght = "01" # Only 1 attribute
    datas = addr_mode + key + EPin + EPout + clusterID 
    datas += direction + manuf_spec + manuf_id
    datas += lenght +attribute + data_type + data
    sendZigateCmd(self, "0110", str(datas) )

def setXiaomiVibrationSensitivity( self, key, sensitivity = 'medium'):

    VIBRATION_SENSIBILITY = { 'high':0x01, 'medium':0x0B, 'low':0x15}

    if sensitivity not in VIBRATION_SENSIBILITY:
        sensitivity = 'medium'

    manuf_id = "115F"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0000
    attribute = "%04x" %0xFF0D
    data_type = "20" # Int8
    data = "%02x" %VIBRATION_SENSIBILITY[sensitivity]
    write_attribute( self, key, "01", "01", cluster_id, manuf_id, manuf_spec, attribute, data_type, data)


def removeZigateDevice( self, IEEE ):
    # remove a device in Zigate
    # Key is the short address of the device
    # extended address is ieee address
    if self.ZigateIEEE != None:
        Domoticz.Status("Remove from Zigate Device = " + " IEEE = " +str(IEEE) )
        #sendZigateCmd(self, "0026", str(self.ZigateIEEE) + str(IEEE) )
    else:
        Domoticz.Error("removeZigateDevice - cannot remove due to unknown Zigate IEEE: ")

    return

def getListofAttribute(self, nwkid, EpOut, cluster):

    datas = "{:02n}".format(2) + nwkid + "01" + EpOut + cluster + "0000" + "00" + "00" + "0000" + "FF"
    Domoticz.Debug("attribute_discovery_request - " +str(datas) )
    sendZigateCmd(self, "0140", datas )



def processConfigureReporting( self, NWKID=None ):
    '''
    processConfigureReporting( self )
    Called at start of the plugin to configure Reporting of all connected object, based on their corresponding cluster

    Synopsis:
    - for each Device
        if they support Cluster we want to configure Reporting 

    '''

    ATTRIBUTESbyCLUSTERS = {
            # 0xFFFF sable reporting-
            # 6460   - 6 hours
            # 0x0E10 - 3600s A hour
            # 0x0708 - 30'
            # 0x0384 - 15'
            # 0x012C - 5'
            # 0x003C - 1'
        # Basic Cluster
        '0000': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'012C', 'MaxInterval':'FFFE', 'TimeOut':'0000','Change':'01'},
                                 '0032': {'DataType': '10', 'MinInterval':'0005', 'MaxInterval':'1C20', 'TimeOut':'0FFF','Change':'01'},
                                 '0033': {'DataType': '10', 'MinInterval':'0005', 'MaxInterval':'1C20', 'TimeOut':'0FFF','Change':'01'}}},

        # Power Cluster
        '0001': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'012C', 'MaxInterval':'FFFE', 'TimeOut':'0000','Change':'01'},
                                 '0020': {'DataType': '29', 'MinInterval':'0E10', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0021': {'DataType': '29', 'MinInterval':'0E10', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'}}},

        # On/Off Cluster
        '0006': {'Attributes': { '0000': {'DataType': '10', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}},

        # Level Control Cluster
        '0008': {'Attributes': { '0000': {'DataType': '20', 'MinInterval':'0005', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'05'}}},

        # Windows Covering
        '0102': {'Attributes': { '0000': {'DataType': '30', 'MinInterval':'0005', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'05'},
                                 '0003': {'DataType': '21', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0004': {'DataType': '21', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0008': {'DataType': '20', 'MinInterval':'0001', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'},
                                 '0009': {'DataType': '20', 'MinInterval':'0001', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'},
                                 '000A': {'DataType': '16', 'MinInterval':'0001', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'},
                                 '0011': {'DataType': '21', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0013': {'DataType': '21', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0017': {'DataType': '16', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'}}},
        # Thermostat
        '0201': {'Attributes': { '0000': {'DataType': '29', 'MinInterval':'012C', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'},
                                 '0001': {'DataType': '20', 'MinInterval':'0600', 'MaxInterval':'5460', 'TimeOut':'0FFF','Change':'01'},
                                 '0008': {'DataType': '29', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0011': {'DataType': '29', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0012': {'DataType': '29', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0014': {'DataType': '29', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '001B': {'DataType': '30', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '001C': {'DataType': '30', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'}}},
        # Colour Control
        '0300': {'Attributes': { '0007': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}, # Color Temp
                                 #'0000': {'DataType': '20', 'MinInterval':'0384', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 #'0001': {'DataType': '20', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}, 
                                 '0003': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}, # Color X
                                 '0004': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}, # Color Y
                                 '0008': {'DataType': '30', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}}, # Color Mode
        # Illuminance Measurement
        '0400': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'0005', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'0F'}}},
        # Temperature
        '0402': {'Attributes': { '0000': {'DataType': '29', 'MinInterval':'000A', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}},
        # Pression Atmo
        '0403': {'Attributes': { '0000': {'DataType': '20', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'},
                                 '0010': {'DataType': '29', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},
        # Humidity
        '0405': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},
        # Occupancy Sensing
        '0406': {'Attributes': { '0030': {'DataType': '20', 'MinInterval':'0005', 'MaxInterval':'1C20', 'TimeOut':'0FFF','Change':'01'},
                                 '0000': {'DataType': '18', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}},
        # IAS ZOne
        '0500': {'Attributes': { '0000': {'DataType': '30', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'},
                                 '0001': {'DataType': '31', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'},
                                 '0002': {'DataType': '19', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},
        # Power
        '0702': {'Attributes': { '0000': {'DataType': '25', 'MinInterval':'FFFF', 'MaxInterval':'0000', 'TimeOut':'0000','Change':'00'},
                                 '0400': {'DataType': '2a', 'MinInterval':'0005', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}}
        }

    now = int(time())
    if NWKID is None :
        if self.busy or len(self.ZigateComm._normalQueue) > MAX_LOAD_ZIGATE:
            Domoticz.Debug("configureReporting - skip configureReporting for now ... system too busy (%s/%s) for %s"
                  %(self.busy, len(self.ZigateComm._normalQueue), NWKID))
            return # Will do at the next round
        target = self.ListOfDevices
        clusterlist = None
    else:
        target = []
        target.append(NWKID)

    for key in target:
        # Let's check that we can do a Configure Reporting. Only during the pairing process (NWKID is provided) or we are on the Main Power
        Domoticz.Debug("configurereporting - processing %s" %key)
        if key == '0000': continue
        if key not in self.ListOfDevices:
            Domoticz.Error("processConfigureReporting - Unknown key: %s" %key)
            continue
        if 'Status' not in self.ListOfDevices[key]:
            Domoticz.Error("processConfigureReporting - no 'Status' flag for device %s !!!" %key)
            continue
        if self.ListOfDevices[key]['Status'] != 'inDB': continue
        if NWKID is None:
            if 'PowerSource' in self.ListOfDevices[key]:
                if self.ListOfDevices[key]['PowerSource'] != 'Main': continue
            if 'MacCapa' in self.ListOfDevices[key]:
                if self.ListOfDevices[key]['MacCapa'] != '8e': continue

        #if 'Manufacturer' in self.ListOfDevices[key]:
        #    manufacturer = self.ListOfDevices[key]['Manufacturer']
        #    manufacturer_spec = "01"
        manufacturer = "0000"
        manufacturer_spec = "00"
        direction = "00"
        addr_mode = "02"

        for Ep in self.ListOfDevices[key]['Ep']:
            #if NWKID is None:
            #    identifySend( self, key, Ep, 0)
            #else:
            #    identifySend( self, key, Ep, 15)
            Domoticz.Debug("Configurereporting - processing %s/%s" %(key,Ep))
            clusterList = getClusterListforEP( self, key, Ep )
            for cluster in clusterList:
                if cluster in ( 'Type', 'ColorMode', 'ClusterType' ):
                    continue
                if cluster not in ATTRIBUTESbyCLUSTERS:
                    continue

                Domoticz.Debug("Configurereporting - processing %s/%s - %s" %(key,Ep,cluster))
                if 'ConfigureReporting' not in self.ListOfDevices[key]:
                    self.ListOfDevices[key]['ConfigureReporting'] = {}
                if 'Ep' not in self.ListOfDevices[key]['ConfigureReporting']:
                    self.ListOfDevices[key]['ConfigureReporting']['Ep'] = {}
                if Ep not in self.ListOfDevices[key]['ConfigureReporting']['Ep']:
                    self.ListOfDevices[key]['ConfigureReporting']['Ep'][Ep] = {}
                if cluster not in self.ListOfDevices[key]['ConfigureReporting']['Ep'][Ep]:
                    self.ListOfDevices[key]['ConfigureReporting']['Ep'][Ep][cluster] = {}

                if self.ListOfDevices[key]['ConfigureReporting']['Ep'][Ep][str(cluster)] in ( '86', '8c') and \
                        self.ListOfDevices[key]['ConfigureReporting']['Ep'][Ep][str(cluster)] != {} :
                    Domoticz.Debug("configurereporting - skiping due to existing past")
                    continue

                _idx = Ep + '-' + str(cluster)
                if 'TimeStamps' not in self.ListOfDevices[key]['ConfigureReporting'] :
                    self.ListOfDevices[key]['ConfigureReporting']['TimeStamps'] = {}
                    self.ListOfDevices[key]['ConfigureReporting']['TimeStamps'][_idx] = 0
                else:
                    if _idx not in self.ListOfDevices[key]['ConfigureReporting']['TimeStamps']:
                        self.ListOfDevices[key]['ConfigureReporting']['TimeStamps'][_idx] = 0

                if  self.ListOfDevices[key]['ConfigureReporting']['TimeStamps'][_idx] != 0:
                     if now <  ( self.ListOfDevices[key]['ConfigureReporting']['TimeStamps'][_idx] + (21 * 3600)):  # Do almost every day
                        continue

                if NWKID is None and (self.busy or len(self.ZigateComm._normalQueue) > MAX_LOAD_ZIGATE):
                    Domoticz.Debug("configureReporting - skip configureReporting for now ... system too busy (%s/%s) for %s"
                        %(self.busy, len(self.ZigateComm._normalQueue), key))
                    Domoticz.Debug("QUEUE: %s" %str(self.ZigateComm._normalQueue))
                    return # Will do at the next round

                Domoticz.Debug("configureReporting - requested for device: %s on Cluster: %s" %(key, cluster))

                if self.pluginconf.pluginConf['allowReBindingClusters']:
                    if 'Bind' in self.ListOfDevices[key]:
                        del self.ListOfDevices[key]['Bind'] 
                    if 'IEEE' in self.ListOfDevices[key]:
                        bindDevice( self, self.ListOfDevices[key]['IEEE'], Ep, cluster )
                    else:
                        Domoticz.Error("configureReporting - inconsitency on %s no IEEE found : %s " %(key, str(self.ListOfDevices[key])))

                self.ListOfDevices[key]['ConfigureReporting']['TimeStamps'][_idx] = int(time())

                attrDisp = []   # Used only for printing purposes
                attrList = ''
                attrLen = 0
                for attr in ATTRIBUTESbyCLUSTERS[cluster]['Attributes']:
                    # Check if the Attribute is listed in the Attributes List (provided by the Device
                    # In case Attributes List exists, we have git the list of reported attribute.
                   
                    if 'Attributes List' in self.ListOfDevices[key]:
                        if 'Ep' in self.ListOfDevices[key]['Attributes List']:
                            if Ep in self.ListOfDevices[key]['Attributes List']['Ep']:
                                if cluster in self.ListOfDevices[key]['Attributes List']['Ep'][Ep]:
                                    if attr not in self.ListOfDevices[key]['Attributes List']['Ep'][Ep][cluster]:
                                        Domoticz.Debug("configureReporting: drop attribute %s" %attr)
                                        continue

                    attrdirection = "00"
                    attrType = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['DataType']
                    minInter = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['MinInterval']
                    maxInter = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['MaxInterval']
                    timeOut = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['TimeOut']
                    chgFlag = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['Change']

                    attrList += attrdirection + attrType + attr + minInter + maxInter + timeOut + chgFlag
                    attrLen += 1
                    attrDisp.append(attr)

                datas =   addr_mode + key + "01" + Ep + cluster + direction + manufacturer_spec + manufacturer 
                datas +=  "%02x" %(attrLen) + attrList
                Domoticz.Debug("configureReporting for [%s] - cluster: %s on Attribute: %s >%s< " %(key, cluster, attrDisp, datas) )
                sendZigateCmd(self, "0120", datas )

def bindDevice( self, ieee, ep, cluster, destaddr=None, destep="01"):
    '''
    Binding a device/cluster with ....
    if not destaddr and destep provided, we will assume that we bind this device with the Zigate coordinator
    '''

    mode = "03"     # IEEE
    if not destaddr:
        #destaddr = self.ieee # Let's grab the IEEE of Zigate
        if self.ZigateIEEE != None and self.ZigateIEEE != '':
            destaddr = self.ZigateIEEE
            destep = "01"
        else:
            Domoticz.Debug("bindDevice - self.ZigateIEEE not yet initialized")
            return

    # let's check if we alreardy bind .
    nwkid = self.IEEE2NWK[ieee]
    if 'Bind' not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]['Bind'] = {}

    if cluster not in self.ListOfDevices[nwkid]['Bind']:
        self.ListOfDevices[nwkid]['Bind'][cluster] = {}
        self.ListOfDevices[nwkid]['Bind'][cluster]['Stamp'] = int(time())
        self.ListOfDevices[nwkid]['Bind'][cluster]['Phase'] = 'requested'
        self.ListOfDevices[nwkid]['Bind'][cluster]['Status'] = ''

        Domoticz.Debug("bindDevice - ieee: %s, ep: %s, cluster: %s, Zigate_ieee: %s, Zigate_ep: %s" %(ieee,ep,cluster,destaddr,destep) )
        datas =  str(ieee)+str(ep)+str(cluster)+str(mode)+str(destaddr)+str(destep) 
        sendZigateCmd(self, "0030", datas )
    else:
        Domoticz.Debug("bindDevice - %s/%s - %s already done at %s" %(ieee, ep, cluster, self.ListOfDevices[nwkid]['Bind'][cluster]['Stamp']))

    return


def unbindDevice( self, ieee, ep, cluster, destaddr=None, destep="01"):
    '''
    unbind
    '''

    mode = "03"     # IEEE
    if not destaddr:
        #destaddr = self.ieee # Let's grab the IEEE of Zigate
        if self.ZigateIEEE != None and self.ZigateIEEE != '':
            destaddr = self.ZigateIEEE
            destep = "01"
        else:
            Domoticz.Debug("bindDevice - self.ZigateIEEE not yet initialized")
            return

    Domoticz.Debug("unbindDevice - ieee: %s, ep: %s, cluster: %s, Zigate_ieee: %s, Zigate_ep: %s" %(ieee,ep,cluster,destaddr,destep) )
    datas = str(ieee) + str(ep) + str(cluster) + str(mode) + str(destaddr) + str(destep)
    sendZigateCmd(self, "0031", datas )

    return


def rebind_Clusters( self, NWKID):

    # Binding devices
    CLUSTERS_LIST = [ 'fc00', '0500', '0406', '0402', '0400', '0001',
            '0102', '0403', '0405', '0500', '0702', '0006', '0008', '0201', '0204', '0300', '000A', '0020', '0000',
            'fc01', # Private cluster 0xFC01 to manage some Legrand Netatmo stuff
            'ff02'  # Used by Xiaomi devices for battery informations.
            ]

    for iterBindCluster in CLUSTERS_LIST:      # Bining order is important
        for iterEp in self.ListOfDevices[NWKID]['Ep']:
            if iterBindCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                Domoticz.Debug('Request an Unbind + Bind for %s/%s on Cluster %s' %(NWKID, iterEp, iterBindCluster))
                if 'Bind' in self.ListOfDevices[NWKID]:
                    del self.ListOfDevices[NWKID]['Bind']
                unbindDevice( self, self.ListOfDevices[NWKID]['IEEE'], iterEp, iterBindCluster)
                bindDevice( self, self.ListOfDevices[NWKID]['IEEE'], iterEp, iterBindCluster)


def identifyEffect( self, nwkid, ep, effect='Blink' ):

    '''
        Blink   / Light is switched on and then off (once)
        Breathe / Light is switched on and off by smoothly increasing and 
                  then decreasing its brightness over a one-second period, 
                  and then this is repeated 15 times
        Okay    / •  Colour light goes green for one second
                  •  Monochrome light flashes twice in one second
        Channel change / •  Colour light goes orange for 8 seconds
                         •  Monochrome light switches to
                            maximum brightness for 0.5 s and then to
                            minimum brightness for 7.5 s
        Finish effect  /  Current stage of effect is completed and then identification mode is
                          terminated (e.g. for the Breathe effect, only the current one-second
                          cycle will be completed)
        Stop effect    /  Current effect and id


        A variant of the selected effect can also be specified, but currently only the default
        (as described above) is available.
    '''

    effect_command = { 'Blink': 0x00 ,
            'Breathe': 0x01,
            'Okay': 0x02,
            'ChannelChange': 0x0b,
            'FinishEffect': 0xfe,
            'StopEffect': 0xff }


    identify = False

    for iterEp in  self.ListOfDevices[nwkid]['Ep']:
        if '0300' in self.ListOfDevices[nwkid]['Ep'][iterEp]:
            identify = True

    if 'ZDeviceID' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['ZDeviceID'] != {} and self.ListOfDevices[nwkid]['ZDeviceID'] != '':
            if int(self.ListOfDevices[nwkid]['ZDeviceID'],16) in ZLL_DEVICES:
                identify = True

    if not identify:
        return

    if effect not in effect_command:
        effect = 'Blink'

    datas = "02" + "%s"%(nwkid) + "01" + ep + "%02x"%(effect_command[effect])  + "%02x" %0
    sendZigateCmd(self, "00E0", datas )
    

def initiateTouchLink( self):

    Domoticz.Status("initiate Touch Link")
    sendZigateCmd(self, "00D0", '' )

def factoryresetTouchLink( self):

    Domoticz.Status("Factory Reset Touch Link Over The Air")
    sendZigateCmd(self, "00D2", '' )


def identifySend( self, nwkid, ep, duration=0):

    datas = "02" + "%s"%(nwkid) + "01" + ep + "%04x"%(duration) 
    Domoticz.Debug("identifySend - send an Identify Message to: %s for %04x seconds" %( nwkid, duration))
    Domoticz.Debug("identifySend - data sent >%s< " %(datas) )
    sendZigateCmd(self, "0070", datas )

def maskChannel( channel ):

    CHANNELS = { 0: 0x00000000, # Scan for all channels
            11: 0x00000800,
            #12: 0x00001000,
            #13: 0x00002000,
            #14: 0x00004000,
            15: 0x00008000,
            #16: 0x00010000,
            #17: 0x00020000,
            #18: 0x00040000,
            19: 0x00080000,
            20: 0x00100000,
            #21: 0x00200000,
            #22: 0x00400000,
            #23: 0x00800000,
            #24: 0x01000000,
            25: 0x02000000,
            26: 0x04000000 }

    mask = 0x00000000
    if isinstance(channel, list):
        for c in channel:
            if c.isdigit():
                if int(c) in CHANNELS:
                    mask += CHANNELS[int(c)]
            else:
                Domoticz.Error("maskChannel - invalid channel %s" %c)
    else:
            mask = CHANNELS[int(channel)]
    return mask


def setChannel( self, channel):
    '''
    The channel list
    is a bitmap, where each bit describes a channel (for example bit 12
    corresponds to channel 12). Any combination of channels can be included.
    ZigBee supports channels 11-26.
    '''
    mask = maskChannel( channel )
    Domoticz.Status("setChannel - Channel set to : %08.x " %(mask))

    sendZigateCmd(self, "0021", "%08.x" %(mask))
    return


def NwkMgtUpdReq( self, channel, mode='scan'  ):
    '''
    NwkMgtUpdReq( self, channel, mode )
        channel: channel to scan or to use
        mode: 'scan' => scanner
              'change' => change the Radio Channel
    '''
    # <target short address: uint16_t>
    # <channel mask: uint32_t>
    # <scan duration: uint8_t>
    # <scan count: uint8_t>
    # <network update ID: uint8_t>
    # <network manager short address: uint16_t>
    # Channel Mask:
    #    Mask of channels to scan
    # Scan Duration:
    # 0x00 - 0x05 : Time in Second
    #             : Indicates that an energy scan is required and determines the time to be spent 
    #               scanning each channel - this time is proportional to 2u8ScanDuration+1. 
    #               The set of channels to scan is specified through u32ScanChannels and the maximum 
    #               number of scans is equal to the value of u8ScanCount. Valid for unicasts only
    # 0x60 - 0xFD : Reserved
    # 0xFE        : Change radio channel to single channel specified through channel
    # 0xFF        : Update the stored radio channel mask
    # Scan count:
    #    Scan repeats 
    # Network Update ID:
    #    0 – 0xFF Transaction ID for scan

    # Scan Duration

    if mode == 'scan':
        scanDuration = 0x01 # 
    elif mode == 'change':
        scanDuration = 0xFE # Change radio channel
    elif mode == 'update':
        scanDuration = 0xFF # Update stored radui
    else:
        Domoticz.Error("NwkMgtUpdReq Unknown mode %s" %mode)
        return

    scanCount = 1

    mask = maskChannel( channel )
    Domoticz.Debug("NwkMgtUpdReq - Channel targeted: %08.x " %(mask))

    #datas = "0000" + "%08.x" %(mask) + "%02.x" %(scanDuration) + "%02.x" %(scanCount) + "00" + "0000"

    datas = "0000" + "07FFF800" + "01" + "01" + "01" + "0000"
    if mode == 'scan':
        Domoticz.Log("NwkMgtUpdReq - %s channel(s): %04.x duration: %02.x count: %s >%s<" \
                %( mode, mask, scanDuration, scanCount, datas) )
    elif mode in ('change', 'update'):
        Domoticz.Log("NwkMgtUpdReq - %s channel(s): %04.x" \
                %( mode, mask ) )

    Domoticz.Log("NwkMgtUpdReq - request a %s on channels %s for duration %s an count %s" \
            %( mode, channel, scanDuration, scanCount))
    Domoticz.Log("NwkScan - %s %s" %("004A", datas))
    sendZigateCmd(self, "004A", datas )
    return

def channelChangeInitiate( self, channel ):

    Domoticz.Status("Change channel from [%s] to [%s] with nwkUpdateReq" %(self.currentChannel, channel))
    NwkMgtUpdReq( self, channel, 'change')

def channelChangeContinue( self ):

    Domoticz.Status("Restart network")
    sendZigateCmd(self, "0024", "" )   # Start Network
    sendZigateCmd(self, "0009", "") # In order to get Zigate IEEE and NetworkID


def setExtendedPANID(self, extPANID):
    '''
    setExtendedPANID MUST be call after an erase PDM. If you change it 
    after having paired some devices, they won't be able to reach you anymore
    Extended PAN IDs (EPIDs) are 64-bit numbers that uniquely identify a PAN. 
    ZigBee communicates using the shorter 16-bit PAN ID for all communication except one.
    '''

    datas = "%016x" %extPANID
    Domoticz.Debug("set ExtendedPANID - %016x "\
            %( extPANID) )
    sendZigateCmd(self, "0020", datas )

def leaveMgtReJoin( self, saddr, ieee, rejoin=True):
    ' in case of receiving a leave, and that is not related to an explicit remove '

    return
    Domoticz.Log("leaveMgt - sAddr: %s , ieee: %s" %( saddr, ieee))
    # Request a Re-Join and Do not remove children
    #if rejoin:
    #    if self.permitTojoin != 0xff:
    #        Domoticz.Log("Switch to Permit to Join for 30s, to allow rejoin")
    #        discover = "%02.X" %int(30)
    #        sendZigateCmd(self, "0049","FFFC" + discover + "00")
    #    datas = saddr + ieee + '01' + '00'
    #else:
    #    datas = saddr + ieee + '00' + '00'

    #sendZigateCmd(self, "0047", datas )

def thermostat_Setpoint_SPZB(  self, key, setpoint):

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0x4003
    data_type = "29" # Int16
    Domoticz.Debug("setpoint: %s" %setpoint)
    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    Domoticz.Debug("setpoint: %s" %setpoint)
    Hdata = "%04x" %setpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    Domoticz.Debug("thermostat_Setpoint_SPZB - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,Hdata,cluster_id,Hattribute,data_type))
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)


def thermostat_Setpoint( self, key, setpoint):

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0x0012
    data_type = "29" # Int16
    Domoticz.Debug("setpoint: %s" %setpoint)
    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    Domoticz.Debug("setpoint: %s" %setpoint)
    Hdata = "%04x" %setpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    Domoticz.Debug("thermostat_Setpoint - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,Hdata,cluster_id,Hattribute,data_type))
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

def thermostat_eurotronic_hostflag( self, key, action):

    HOSTFLAG_ACTION = {
            'turn_display':0x000002,
            'boost':       0x000004,
            'clear_off':   0x000010,
            'set_off_mode':0x000020,
            'child_lock':  0x000080
            }

    if action not in HOSTFLAG_ACTION:
        Domoticz.Log("thermostat_eurotronic_hostflag - unknown action %s" %action)
        return

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    attribute = "%04x" %0x4008
    data_type = "22" # U24
    data = "%06x" %HOSTFLAG_ACTION[action]
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
    Domoticz.Debug("thermostat_eurotronic_hostflag - for %s with value %s / cluster: %s, attribute: %s type: %s action: %s"
            %(key,data,cluster_id,attribute,data_type, action))

def thermostat_Calibration( self, key, calibration):

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    attribute = "%04x" %0x0010
    data_type = "20" # Int8
    data = "%02x" %calibration
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
    Domoticz.Debug("thermostat_Calibration - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,attribute,data_type))

def configHeatSetpoint( self, key ):

    ddhostflags = 0xFFFFEB

def thermostat_Mode( self, key, mode ):

    SYSTEM_MODE = { 'Off' : 0x00 ,
            'Auto' : 0x01 ,
            'Reserved' : 0x02,
            'Cool' : 0x03,
            'Heat' :  0x04,
            'Emergency Heating' : 0x05,
            'Pre-cooling' : 0x06,
            'Fan only' : 0x07 }


    if mode not in SYSTEM_MODE:
        Domoticz.Log("thermostat_Mode - unknown system mode: %s" %mode)

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    attribute = "%04x" %0x001C
    data_type = "30" # Enum8
    data = "%02x" %SYSTEM_MODE[mode]

    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
    Domoticz.Debug("thermostat_Mode - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,attribute,data_type))

def ReadAttributeRequest_0201(self, key):

    Domoticz.Debug("ReadAttributeRequest_0201 - Key: %s " %key)
    # Power Config
    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp

    # Thermostat Information
    listAttributes = []
    listAttributes.append(0x0000)        # Local Temp / 0x29
    listAttributes.append(0x0008)        # Pi Heating Demand (valve position %)
    listAttributes.append(0x0010)        # Calibration / 0x28
    #listAttributes.append(0x0011)        # COOLING_SETPOINT / 0x29
    listAttributes.append(0x0012)        # HEATING_SETPOINT / 0x29
    listAttributes.append(0x0014)        # Unoccupied Heating Setpoint 0x29
    #listAttributes.append(0x0015)        # MIN HEATING / 0x29
    #listAttributes.append(0x0016)        # MAX HEATING / 0x29
    listAttributes.append(0x001B)        # Control sequence
    listAttributes.append(0x001C)        # System Mode
    listAttributes.append(0x001F)        # Set Mode
    Domoticz.Debug("Request 0201 %s/%s-%s 0201 %s " %(key, EPin, EPout, listAttributes))
    ReadAttributeReq( self, key, EPin, EPout, "0201", listAttributes )

    listAttributes = []
    if str(self.ListOfDevices[key]['Model']).find('SPZB') == 0:
        Domoticz.Debug("- req Attributes for Eurotronic")
        listAttributes.append(0x4000)        # TRV Mode
        listAttributes.append(0x4001)        # Set Valve Position
        listAttributes.append(0x4002)        # Errors
        listAttributes.append(0x4003)        # Curret Temperature Set point Eurotronics
        listAttributes.append(0x4008)        # HOst Flag
    elif str(self.ListOfDevices[key]['Model']).find('Super TR') == 0:
        Domoticz.Debug("- req Attributes for  Super TR")
        listAttributes.append(0x0403)    
        listAttributes.append(0x0408)   
        listAttributes.append(0x0409)  

    if len(listAttributes) > 0:
        Domoticz.Debug("Request 0201 %s/%s-%s 0201 %s " %(key, EPin, EPout, listAttributes))
        ReadAttributeReq( self, key, EPin, EPout, "0201", listAttributes )


def ReadAttributeRequest_0204(self, key):

    Domoticz.Debug("ReadAttributeRequest_0204 - Key: %s " %key)
    # Power Config
    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0204" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp

    listAttributes = []
    listAttributes.append(0x0001) # Read KeypadLockout

    if len(listAttributes) > 0:
        Domoticz.Debug("Request 0204 %s/%s-%s 0204 %s " %(key, EPin, EPout, listAttributes))
        ReadAttributeReq( self, key, EPin, EPout, "0204", listAttributes )

def Thermostat_LockMode( self, key, lockmode):


    LOCK_MODE = { 'unlocked':0x00,
            'templock':0x02,
            'off':0x04,
            'off':0x05
            }

    if lockmode not in LOCK_MODE:
        return

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0204
    Hattribute = "%04x" %0x0001
    data_type = "30" # Int16
    Domoticz.Debug("lockmode: %s" %lockmode)
    lockmode = LOCK_MODE[lockmode]
    Hdata = "%02x" %lockmode
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0204" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    Domoticz.Debug("Thermostat_LockMode - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,Hdata,cluster_id,Hattribute,data_type))
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

