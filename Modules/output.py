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

from Modules.zigateConsts import ZLL_DEVICES, MAX_LOAD_ZIGATE, CLUSTERS_LIST, MAX_READATTRIBUTES_REQ, LEGRAND_REMOTES
from Modules.tools import getClusterListforEP, loggingOutput, mainPoweredDevice

def ZigatePermitToJoin( self, permit ):

    if permit:
        # Enable Permit to join
        if self.permitTojoin['Duration'] == 255:
            # Nothing to do , it is already in permanent pairing mode.
            pass
        else:
            if permit != 255:
                Domoticz.Status("Request Accepting new Hardware for %s seconds " %permit)
            else:
                Domoticz.Status("Request Accepting new Hardware for ever ")

            self.permitTojoin['Starttime'] = int(time())
            if permit == 1:
                self.permitTojoin['Duration'] = 0
            else:
                self.permitTojoin['Duration'] = permit

            sendZigateCmd(self, "0049","FFFC" + '%02x' %permit + "00")
    else: 
        # Disable Permit to Join
        if self.permitTojoin['Duration'] == 0:
            # Nothing to do , Pairing is already off
            pass
        else:
            self.permitTojoin['Starttime'] = int(time())
            self.permitTojoin['Duration'] = 0
            sendZigateCmd(self, "0049","FFFC" + '00' + "00")
        Domoticz.Status("Request Disabling Accepting new Hardware")

    loggingOutput( self, 'Debug', "Permit Join set :" , 'ffff' )
    loggingOutput( self, 'Debug', "---> self.permitTojoin['Starttime']: %s" %self.permitTojoin['Starttime'], 'ffff' )
    loggingOutput( self, 'Debug', "---> self.permitTojoin['Duration'] : %s" %self.permitTojoin['Duration'], 'ffff' )

    # Request Time in order to leave time to get the Zigate in pairing mode
    sendZigateCmd(self, "0017", "")

    # Request a Status to update the various permitTojoin structure
    sendZigateCmd( self, "0014", "" ) # Request status

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

        Domoticz.Status("Set Zigate as a TimeServer")
        setTimeServer( self)

        Domoticz.Status("Start network")
        sendZigateCmd(self, "0024", "" )   # Start Network
    
        loggingOutput( self, 'Debug', "Request network Status", '0000')
        sendZigateCmd( self, "0014", "" ) # Request status
        sendZigateCmd( self, "0009", "" ) # Request status

def setTimeServer( self ):

    EPOCTime = datetime(2000,1,1)
    UTCTime = int((datetime.now() - EPOCTime).total_seconds())
    Domoticz.Status("setTimeServer - Setting UTC Time to : %s" %( UTCTime) )
    data = "%08x" %UTCTime
    sendZigateCmd(self, "0016", data  )
    #Request Time
    sendZigateCmd(self, "0017", "")


def zigateBlueLed( self, OnOff):

    if OnOff:
        Domoticz.Log("Switch Blue Led On")
        sendZigateCmd(self, "0018","01")
    else:
        Domoticz.Log("Switch Blue Led off")
        sendZigateCmd(self, "0018","00")


def sendZigateCmd(self, cmd,datas ):

    loggingOutput( self, 'Debug', "sendZigateCmd - %s %s" %(cmd, datas))
    self.ZigateComm.sendData( cmd, datas )

def ReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes ):

    def split_list(alist, wanted_parts=1):
        length = len(alist)
        return [ alist[i*length // wanted_parts: (i+1)*length // wanted_parts] for i in range(wanted_parts) ]

    if not isinstance(ListOfAttributes, list) or len (ListOfAttributes) < 5:
        normalizedReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes )
    else:
        loggingOutput( self, 'Debug', "ReadAttributeReq - %s/%s %s ListOfAttributes: %s" %(addr, EpOut, Cluster, ListOfAttributes), nwkid=addr)
        chunk = MAX_READATTRIBUTES_REQ
        if chunk > 4 and 'Manufacturer Name' in self.ListOfDevices[addr]:
            if self.ListOfDevices[addr]['Manufacturer'] == '1021':
                # shorter list to 4 attributes max, Legrand seems not responding to that
                chunk = 4
            if self.ListOfDevices[addr]['Manufacturer Name'] == 'Legrand':
                # shorter list to 4 attributes max, Legrand seems not responding to that
                chunk = 4
            if self.ListOfDevices[addr]['Manufacturer Name'] == 'LIVOLO':
                # shorter list to 4 attributes max, Legrand seems not responding to that
                chunk = 4

        if  chunk > 4 and 'Model' in self.ListOfDevices[addr]:
            if self.ListOfDevices[addr]['Model'] != {}:
                if self.ListOfDevices[addr]['Model'] == 'TI0001':
                    # shorter list to 4 attributes max, Livolo seems not responding to that
                    chunk = 4

        nbpart = - (  - len(ListOfAttributes) // chunk) 
        for shortlist in split_list(ListOfAttributes, wanted_parts=nbpart):
            loggingOutput( self, 'Debug', "----> Shorter: %s" %( shortlist), nwkid=addr)
            normalizedReadAttributeReq( self, addr, EpIn, EpOut, Cluster , shortlist )

def normalizedReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes ):

    if 'Health' in self.ListOfDevices[addr]:
        if self.ListOfDevices[addr]['Health'] == 'Not Reachable':
            return

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
                loggingOutput( self, 'Debug', "normalizedReadAttrReq - Last value self.ListOfDevices[%s]['ReadAttributes']['Ep'][%s][%s][%s]: %s"
                         %(addr, EpOut, Cluster, Attr, self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] ), nwkid=addr)
                return
            loggingOutput( self, 'Debug', "normalizedReadAttrReq: %s for %s/%s" %(Attr, addr, self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr]), nwkid=addr)
            self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] = {}
    else:
        lenAttr = 0
        weight = int ((lenAttr ) / 2) + 1
        Attr =''
        loggingOutput( self, 'Debug', "attributes: " +str(ListOfAttributes), nwkid=addr)
        for x in ListOfAttributes:
            Attr_ = "%04x" %(x)
            if Attr_ in self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)]:
                if self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr_] != '00' and \
                        self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr_] != {} :
                    continue
                loggingOutput( self, 'Debug', "normalizedReadAttrReq: %s for %s/%s" %(Attr_, addr, self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr_]), nwkid=addr)
                self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr_] = {}
            Attr += Attr_
            lenAttr += 1

        if lenAttr == 0:
            return

    loggingOutput( self, 'Debug', "normalizedReadAttrReq - addr =" +str(addr) +" Cluster = " +str(Cluster) +" Attributes = " +str(ListOfAttributes), nwkid=addr )
    self.ListOfDevices[addr]['ReadAttributes']['TimeStamps'][EpOut+'-'+str(Cluster)] = int(time())
    datas = "02" + addr + EpIn + EpOut + Cluster + direction + manufacturer_spec + manufacturer + "%02x" %(lenAttr) + Attr
    sendZigateCmd(self, "0100", datas )

def retreive_ListOfAttributesByCluster( self, key, Ep, cluster ):

    ATTRIBUTES = { 
            '0000': [ 0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007, 0x000A, 0x000F, 0x0010, 0x0015, 0x4000, 0xE000, 0xF000],
            '0001': [ 0x0000, 0x0001, 0x0003, 0x0020, 0x0021, 0x0035 ],
            '0003': [ 0x0000],
            '0004': [ 0x0000],
            '0005': [ 0x0001, 0x0002, 0x0003, 0x0004],
            '0006': [ 0x0000],
            '0008': [ 0x0000, 0x4000],
            '000a': [ 0x0000],
            '000c': [ 0x0051, 0x0055, 0x006f, 0xff05],
            '0102': [ 0x0000, 0x0001, 0x0002, 0x0003, 0x004, 0x0007, 0x0008, 0x0009, 0x000A, 0x000B, 0x0010, 0x0011, 0x0014, 0x0017, 0xfffd],
            '0300': [ 0x0000, 0x0001, 0x0003, 0x0004, 0x0007, 0x0008, 0x4010],
            '0400': [ 0x0000],
            '0402': [ 0x0000],
            '0403': [ 0x0000],
            '0405': [ 0x0000],
            '0406': [ 0x0000, 0x0001, 0x0010, 0x0011],
            '0500': [ 0x0000, 0x0002],
            '0502': [ 0x0000],
            '0702': [ 0x0000, 0x0200, 0x0301, 0x0302, 0x0303, 0x0306, 0x0400],
            '000f': [ 0x0000, 0x0051, 0x0055, 0x006f, 0xfffd], 
            '0b04': [ 0x0505, 0x0508, 0x050b], # https://docs.smartthings.com/en/latest/ref-docs/zigbee-ref.html
            'fc01': [ 0x0000, 0x0001]
            }

    targetAttribute = None

    if 'Attributes List' in self.ListOfDevices[key]:
        if 'Ep' in self.ListOfDevices[key]['Attributes List']:
            if Ep in self.ListOfDevices[key]['Attributes List']['Ep']:
                if cluster in self.ListOfDevices[key]['Attributes List']['Ep'][Ep]:
                    targetAttribute = []
                    loggingOutput( self, 'Debug', "retreive_ListOfAttributesByCluster: Attributes from Attributes List", nwkid=key)
                    for attr in  self.ListOfDevices[key]['Attributes List']['Ep'][Ep][cluster]:
                        targetAttribute.append( int(attr,16) )
                    if 'Model' in self.ListOfDevices[key]:
                        # Force Read Attributes 
                        if (self.ListOfDevices[key]['Model'] == 'SPE600' and cluster == '0702') or \
                           (self.ListOfDevices[key]['Model'] == 'TS0302' and cluster == '0102'):     # Zemismart Blind switch
                            for addattr in ATTRIBUTES[cluster]:
                                if addattr not in targetAttribute:
                                    targetAttribute.append( addattr )

    if targetAttribute is None:
        loggingOutput( self, 'Debug', "retreive_ListOfAttributesByCluster: default attributes list for cluster: %s" %cluster, nwkid=key)
        if cluster in ATTRIBUTES:
            targetAttribute = ATTRIBUTES[cluster]
        else:
            Domoticz.Log("retreive_ListOfAttributesByCluster: Missing Attribute for cluster %s" %cluster)
            targetAttribute = [ 0x0000 ]

    loggingOutput( self, 'Debug', "retreive_ListOfAttributesByCluster: List of Attributes for cluster %s : %s" %(cluster, targetAttribute), nwkid=key)

    return targetAttribute


def ReadAttributeRequest_0000(self, key, fullScope=True):
    # Basic Cluster
    # The Ep to be used can be challenging, as if we are in the discovery process, the list of Eps is not yet none and it could even be that the Device has only 1 Ep != 01

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0000 - Key: %s , Scope: %s" %(key, fullScope), nwkid=key)
    EPin = "01"
    EPout = '01'

    # Checking if Ep list is empty, in that case we are in discovery mode and we don't really know what are the EPs we can talk to.
    if not fullScope or self.ListOfDevices[key]['Ep'] is None or self.ListOfDevices[key]['Ep'] == {}:
        loggingOutput( self, 'Debug', "--> Not full scope", nwkid=key)
        listAttributes = []

        loggingOutput( self, 'Debug', "--> Build list of Attributes", nwkid=key)
        skipModel = False

        # Do We have Model Name
        if not skipModel and self.ListOfDevices[key]['Model'] == {}:
            loggingOutput( self, 'Debug', "----> Adding: %s" %'0005', nwkid=key)
            listAttributes.append(0x0005)        # Model Identifier

        # Do we Have Manufacturer
        if self.ListOfDevices[key]['Manufacturer'] == '':
            loggingOutput( self, 'Debug', "----> Adding: %s" %'0004', nwkid=key)
            listAttributes.append(0x0004)
        else:
            if self.ListOfDevices[key]['Manufacturer'] == 'Legrand' or self.ListOfDevices[key]['Manufacturer Name']:
                loggingOutput( self, 'Debug', "----> Adding: %s" %'f000', nwkid=key)
                listAttributes.append(0x4000)
                listAttributes.append(0xf000)
                skipModel = True

        if self.ListOfDevices[key]['Model'] != {} and self.ListOfDevices[key]['Model'] != 'TI0001':
            loggingOutput( self, 'Debug', "----> Adding: %s" %'000A', nwkid=key)
            listAttributes.append(0x000A)        # Product Code

        if self.ListOfDevices[key]['Ep'] is None or self.ListOfDevices[key]['Ep'] == {}:
            loggingOutput( self, 'Debug', "Request Basic  via Read Attribute request: " + key + " EPout = " + "01, 02, 03, 06, 09" , nwkid=key)
            ReadAttributeReq( self, key, EPin, "01", "0000", listAttributes )
            ReadAttributeReq( self, key, EPin, "02", "0000", listAttributes )
            ReadAttributeReq( self, key, EPin, "03", "0000", listAttributes )
            ReadAttributeReq( self, key, EPin, "06", "0000", listAttributes ) # Livolo
            ReadAttributeReq( self, key, EPin, "09", "0000", listAttributes )
        else:
            for tmpEp in self.ListOfDevices[key]['Ep']:
                if "0000" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout= tmpEp 
            loggingOutput( self, 'Debug', "Request Basic  via Read Attribute request: " + key + " EPout = " + EPout + " Attributes: " + str(listAttributes), nwkid=key)
            ReadAttributeReq( self, key, EPin, EPout, "0000", listAttributes )
    else:
        loggingOutput( self, 'Debug', "--> Full scope", nwkid=key)
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
            if str(self.ListOfDevices[key]['Model']).find('TS0302') != -1: # Inter Blind Zemismart
                listAttributes.append(0xfffd)
                listAttributes.append(0xfffe)
                listAttributes.append(0xffe1)
                listAttributes.append(0xffe2)
                listAttributes.append(0xffe3)

        if 'Model' in self.ListOfDevices[key]:
            if self.ListOfDevices[key]['Model'] != {}:
                if self.ListOfDevices[key]['Model'] == 'TI0001':
                    copylistAttributes= list( listAttributes)
                    listAttributes = []
                    for iterAttr in copylistAttributes:
                        if iterAttr not in ( 0x000a, 0x000f, 0x0015, 0x4000, 0xf000, 0x0001, 0x0002  ):
                            listAttributes.append( iterAttr)

        for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0000" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                EPout= tmpEp 

        listAttr1 = listAttr2 = None
        if len(listAttributes) > 9:
            # We can send only 10 attributes at a time, we need to split into 2 packs
            listAttr1 = listAttributes[:len(listAttributes)//2]
            listAttr2 = listAttributes[len(listAttributes)//2:]

        if listAttr1 == listAttr2 == None:
            loggingOutput( self, 'Debug', "Request Basic  via Read Attribute request %s/%s %s" %(key, EPout, str(listAttributes)), nwkid=key)
            ReadAttributeReq( self, key, EPin, EPout, "0000", listAttributes )
        else:
            loggingOutput( self, 'Debug', "Request Basic  via Read Attribute request part1 %s/%s %s" %(key, EPout, str(listAttr1)), nwkid=key)
            ReadAttributeReq( self, key, EPin, EPout, "0000", listAttr1 )
            loggingOutput( self, 'Debug', "Request Basic  via Read Attribute request part2 %s/%s %s" %(key, EPout, str(listAttr2)), nwkid=key)
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
    loggingOutput( self, 'Debug', "Requesting Ack for %s/%s" %(key, EPout), nwkid=key)
    ReadAttributeReq( self, key, EPin, EPout, "0000", listAttributes )


def ReadAttributeRequest_0001(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0001 - Key: %s " %key, nwkid=key)
    # Power Config
    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0001" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0001'):
        if iterAttr not in listAttributes:
            listAttributes.append( iterAttr )

    loggingOutput( self, 'Debug', "Request Power Config via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, EPin, EPout, "0001", listAttributes )

def ReadAttributeRequest_0006_400x(self, key):
    loggingOutput( self, 'Debug', "ReadAttributeRequest_0006 focus on 0x4000x attributes- Key: %s " %key, nwkid=key)

    if 'Model' in self.ListOfDevices[key]:
        if self.ListOfDevices[key]['Model'] != {}:
            if self.ListOfDevices[key]['Model'] == 'TI0001':
                loggingOutput( self, 'Debug', "ReadAttributeRequest_0006 - Skip Key: %s for Livolo Switch" %key, nwkid=key)
                return
    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0006" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []

    if 'Model' in self.ListOfDevices[key]:
        if self.ListOfDevices[key]['Model'] in ( 'RWL021', 'SML001', 'SML002', 'LCT001', 'LTW013' ):
            Domoticz.Log("-----requesting Attribute 0x0006/0x4003 for PowerOn state for device : %s" %key)
            listAttributes.append ( 0x4003 )

    loggingOutput( self, 'Debug', "Request OnOff 0x4000x attributes via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, "01", EPout, "0006", listAttributes)


def ReadAttributeRequest_0006(self, key):
    # Cluster 0x0006

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0006 - Key: %s " %key, nwkid=key)

    if 'Model' in self.ListOfDevices[key]:
        if self.ListOfDevices[key]['Model'] != {}:
            if self.ListOfDevices[key]['Model'] == 'TI0001':
                loggingOutput( self, 'Debug', "ReadAttributeRequest_0006 - Skip Key: %s for Livolo Switch" %key, nwkid=key)
                return

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0006" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0006'):
        if iterAttr not in listAttributes:
            listAttributes.append( iterAttr )

    loggingOutput( self, 'Debug', "Request OnOff status via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, "01", EPout, "0006", listAttributes)


def ReadAttributeRequest_0008(self, key):
    # Cluster 0x0008 

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0008 - Key: %s " %key, nwkid=key)
    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0008" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0008'):
        if iterAttr not in listAttributes:
            listAttributes.append( iterAttr )
    loggingOutput( self, 'Debug', "Request Control level of shutter via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, "01", EPout, "0008", 0)

def ReadAttributeRequest_0300(self, key):
    # Cluster 0x0300 - Color Control

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0300 - Key: %s " %key, nwkid=key)
    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0300" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0300'):
        if iterAttr not in listAttributes:
            listAttributes.append( iterAttr )

    loggingOutput( self, 'Debug', "Request Color Temp infos via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, EPin, EPout, "0300", listAttributes)

def ReadAttributeRequest_000C(self, key):
    # Cluster 0x000C with attribute 0x0055 / Xiaomi Power and Metering

    loggingOutput( self, 'Debug', "ReadAttributeRequest_000C - Key: %s " %key, nwkid=key)

    EPin = "01"
    EPout= "02"

    """
     Attribute Type: 10 Attribut ID: 0051
     Attribute Type: 39 Attribut ID: 0055
     Attribute Type: 18 Attribut ID: 006f
    """

    EPin = "01"
    EPout= "01"
    loggingOutput( self, 'Debug', "Request OnOff status for Xiaomi plug via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    listAttributes = []
    listAttributes.append(0x0051)
    listAttributes.append(0x0055)
    listAttributes.append(0x006f)
    listAttributes.append(0xff05)

    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "000c" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    loggingOutput( self, 'Debug', "Request 0x000c info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, "01", EPout, "000C", listAttributes)

def ReadAttributeRequest_0102(self, key):

    loggingOutput( self, 'Debug', "Request Windows Covering status Read Attribute request: " + key , nwkid=key)
    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0102" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0102'):
        if iterAttr not in listAttributes:
            listAttributes.append( iterAttr )

    loggingOutput( self, 'Debug', "Request 0x0102 info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, "01", EPout, "0102", listAttributes)

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
    loggingOutput( self, 'Debug', "Request 0xfc00 info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, "01", EPout, "fc00", listAttributes)

def ReadAttributeRequest_0400(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0400 - Key: %s " %key, nwkid=key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0400" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0400'):
        if iterAttr not in listAttributes:
            listAttributes.append( iterAttr )

    loggingOutput( self, 'Debug', "Illuminance info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, EPin, EPout, "0400", listAttributes)

def ReadAttributeRequest_0402(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0402 - Key: %s " %key, nwkid=key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0402" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0402'):
        if iterAttr not in listAttributes:
            if 'Model' in self.ListOfDevices[key]:
                if self.ListOfDevices[key]['Model'] == 'lumi.light.aqcn02': # Aqara Blulb
                    continue
            listAttributes.append( iterAttr )

    loggingOutput( self, 'Debug', "Temperature info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, EPin, EPout, "0402", listAttributes)

def ReadAttributeRequest_0403(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0403 - Key: %s " %key, nwkid=key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0403" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0403'):
        if iterAttr not in listAttributes:
            if 'Model' in self.ListOfDevices[key]:
                if self.ListOfDevices[key]['Model'] == 'lumi.light.aqcn02': # Aqara Blulb
                    continue
            listAttributes.append( iterAttr )

    loggingOutput( self, 'Debug', "Pression Atm info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, EPin, EPout, "0403", listAttributes)

def ReadAttributeRequest_0405(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0405 - Key: %s " %key, nwkid=key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0405" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0405'):
        if iterAttr not in listAttributes:
            if 'Model' in self.ListOfDevices[key]:
                if self.ListOfDevices[key]['Model'] == 'lumi.light.aqcn02': # Aqara Blulb
                    continue
            listAttributes.append( iterAttr )

    loggingOutput( self, 'Debug', "Humidity info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, EPin, EPout, "0405", listAttributes)

def ReadAttributeRequest_0406(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0406 - Key: %s " %key, nwkid=key)
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
        if iterAttr not in listAttributes:
            if 'Model' in self.ListOfDevices[key]:
                if self.ListOfDevices[key]['Model'] == 'lumi.light.aqcn02': # Aqara Blulb
                    continue
            listAttributes.append( iterAttr )

    loggingOutput( self, 'Debug', "Occupancy info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, EPin, EPout, "0406", listAttributes)

def ReadAttributeRequest_0500(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0500 - Key: %s " %key, nwkid=key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0500" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0500'):
        if iterAttr not in listAttributes:
            listAttributes.append( iterAttr )
    loggingOutput( self, 'Debug', "ReadAttributeRequest_0500 - %s/%s - %s" %(key, EPout, listAttributes), nwkid=key)
    ReadAttributeReq( self, key, "01", EPout, "0500", listAttributes)

def ReadAttributeRequest_0502(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0502 - Key: %s " %key, nwkid=key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0502" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0502'):
        if iterAttr not in listAttributes:
            listAttributes.append( iterAttr )
    loggingOutput( self, 'Debug', "ReadAttributeRequest_0502 - %s/%s - %s" %(key, EPout, listAttributes), nwkid=key)
    ReadAttributeReq( self, key, "01", EPout, "0502", listAttributes)


def ReadAttributeRequest_0702(self, key):
    # Cluster 0x0702 Metering

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0702 - Key: %s " %key, nwkid=key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0702" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0702'):
        if iterAttr not in listAttributes:
            listAttributes.append( iterAttr )

    loggingOutput( self, 'Debug', "Request Metering info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, EPin, EPout, "0702", listAttributes)

def ReadAttributeRequest_000f(self, key):
    # Cluster 0x0702 Metering

    loggingOutput( self, 'Debug', "ReadAttributeRequest_000f - Key: %s " %key, nwkid=key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "000f" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '000f'):
        if iterAttr not in listAttributes:
            listAttributes.append( iterAttr )

    loggingOutput( self, 'Debug', "Request Metering info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
    ReadAttributeReq( self, key, EPin, EPout, "000f", listAttributes)

def ReadAttributeRequest_fc01(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_fc01 - Key: %s " %key, nwkid=key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "fc01" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    listAttributes = []
    #for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  'fc01'):
    #    if iterAttr not in listAttributes:
    #        listAttributes.append( iterAttr )
    listAttributes.append( 0x0000 )
    loggingOutput( self, 'Debug', "Request Legrand info via Read Attribute request: " + key + " EPout = " + EPout + " Attributes: " + str(listAttributes), nwkid=key)
    ReadAttributeReq( self, key, EPin, EPout, "fc01", listAttributes)

    listAttributes = []
    listAttributes.append( 0x0001 )
    loggingOutput( self, 'Debug', "Request Legrand info via Read Attribute request: " + key + " EPout = " + EPout + " Attributes: " + str(listAttributes), nwkid=key)
    ReadAttributeReq( self, key, EPin, EPout, "fc01", listAttributes)

def write_attribute( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data):

    addr_mode = "02" # Short address
    direction = "00"
    lenght = "01" # Only 1 attribute
    datas = addr_mode + key + EPin + EPout + clusterID 
    datas += direction + manuf_spec + manuf_id
    datas += lenght +attribute + data_type + data
    loggingOutput( self, 'Debug', "write_attribute for %s/%s - >%s<" %(key, EPout, datas), key)
    sendZigateCmd(self, "0110", str(datas) )

def setPIRoccupancyTiming( self, key ):

    manuf_spec = "00"
    manuf_id = "0000"

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0406" in self.ListOfDevices[key]['Ep'][tmpEp]: 
            EPout=tmpEp
            cluster_id = "0406"

            for attribute, dataint in ( ( '0010', 5), ('0011', 10) ):
                data_type = "21" # uint16
                data = '%04x' %dataint

                loggingOutput( self, 'Debug', "setPIRoccupancyTiming for %s/%s - Attribute %s: %s" %(key, EPout, attribute, data), key)
                write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)

            ReadAttributeRequest_0406(self, key)


def setPowerOn_OnOff( self, key, OnOffMode=0xff):

    # Tested on Ikea Bulb without any results !
    POWERON_MODE = ( 0x00, # Off
            0x01, # On
            0xff # Previous state
            )

    if 'Manufacturer' in self.ListOfDevices[key]:
        manuf_spec = "01"
        manuf_id = self.ListOfDevices[key]['Manufacturer']
    else:
        manuf_spec = "00"
        manuf_id = "0000"

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0006" in self.ListOfDevices[key]['Ep'][tmpEp]: 
            EPout=tmpEp
            cluster_id = "0006"
            attribute = "4003"
            data_type = "30" # 
            data = "ff"
            if OnOffMode in POWERON_MODE:
                data = "%02x" %OnOffMode
            else:
                data = "%02x" %0xff
            loggingOutput( self, 'Debug', "set_PowerOn_OnOff for %s/%s - OnOff: %s" %(key, EPout, OnOffMode), key)
            write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
            ReadAttributeRequest_0006_400x( self, key)

        #if '0008' in self.ListOfDevices[key]['Ep'][tmpEp]:
        #    EPout=tmpEp
        #    cluster_id = "0008"
        #    attribute = "4000"
        #    data_type = "20" # 
        #    data = "ff"
        #    if OnOffMode in POWERON_MODE:
        #        data = "%02x" %OnOffMode
        #    else:
        #        data = "%02x" %0xff
        #        data = "%02x" %0xff
        #    loggingOutput( self, 'Log', "set_PowerOn_OnOff for %s/%s - OnOff: %s" %(key, EPout, OnOffMode), key)
        #    retreive_ListOfAttributesByCluster( self, key, EPout, '0008')

        #if '0300' in self.ListOfDevices[key]['Ep'][tmpEp]:
        #    EPout=tmpEp
        #    cluster_id = "0300"
        #    attribute = "4010"
        #    data_type = "21" # 
        ##    data = "ffff"
        #    if OnOffMode in POWERON_MODE:
        #        data = "%04x" %OnOffMode
        #    else:
        #        data = "%04x" %0xffff
        #        data = "%02x" %0xff
        #    loggingOutput( self, 'Log', "set_PowerOn_OnOff for %s/%s - OnOff: %s" %(key, EPout, OnOffMode), key)
        #    retreive_ListOfAttributesByCluster( self, key, EPout, '0300')




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


def getListofAttribute(self, nwkid, EpOut, cluster):

    datas = "{:02n}".format(2) + nwkid + "01" + EpOut + cluster + "0000" + "00" + "00" + "0000" + "FF"
    loggingOutput( self, 'Debug', "attribute_discovery_request - " +str(datas) , nwkid=nwkid)
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
        #'0000': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'012C', 'MaxInterval':'FFFE', 'TimeOut':'0000','Change':'01'},
        #                         '0032': {'DataType': '10', 'MinInterval':'0005', 'MaxInterval':'1C20', 'TimeOut':'0FFF','Change':'01'},
        #                         '0033': {'DataType': '10', 'MinInterval':'0005', 'MaxInterval':'1C20', 'TimeOut':'0FFF','Change':'01'}}},

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
                                 '0009': {'DataType': '20', 'MinInterval':'0001', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},
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
        '0300': {'Attributes': { '0000': {'DataType': '20', 'MinInterval':'0384', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01', 'ZDeviceID':{ "010D", "0210", "0105", "0200"}},
                                 '0001': {'DataType': '20', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01', 'ZDeviceID':{ "0105", "010D", "0210", "0200"}},
                                 '0003': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01', 'ZDeviceID':{ "010D", "0210", "0200"}}, # Color X
                                 '0004': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01', 'ZDeviceID':{ "010D", "0210", "0200"}}, # Color Y
                                 '0007': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01', 'ZDeviceID':{ "0102", "010D", "0210", "0220"}}, # Color Temp
                                 '0008': {'DataType': '30', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01', 'ZDeviceID':{ }}}}, # Color Mode
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
        '0406': {'Attributes': { '0000': {'DataType': '18', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'},
                                 # Sensitivy for HUE Motion
                                 '0030': {'DataType': '20', 'MinInterval':'0005', 'MaxInterval':'1C20', 'TimeOut':'0FFF','Change':'01'}}},
        # IAS ZOne
        '0500': {'Attributes': { '0000': {'DataType': '30', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'},
                                 '0001': {'DataType': '31', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'},
                                 '0002': {'DataType': '19', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},
        # IAS Warning Devices
        '0502': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},

        # Power
        '0702': {'Attributes': { 
                                '0000': {'DataType': '25', 'MinInterval':'FFFF', 'MaxInterval':'0000', 'TimeOut':'0000','Change':'00'},
                                '0400': {'DataType': '2a', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}},

        # Electrical Measurement
        '0b04': {'Attributes': {
                                '0505': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'},
                                '0508': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'},
                                '050b': {'DataType': '29', 'MinInterval':'0005', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}},

        #'fc01': {'Attributes': {
        #                        '0000': {'DataType': '09', 'MinInterval':'0005', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'},
        #                        '0001': {'DataType': '10', 'MinInterval':'0005', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}},

        # Binary Input ( Basic )
        #'000f': {'Attributes': {
        #                        '0055': {'DataType': '10', 'MinInterval':'000A', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}},
        }

    now = int(time())
    if NWKID is None :
        if self.busy or len(self.ZigateComm.zigateSendingFIFO) > MAX_LOAD_ZIGATE:
            loggingOutput( self, 'Debug', "configureReporting - skip configureReporting for now ... system too busy (%s/%s) for %s"
                  %(self.busy, len(self.ZigateComm.zigateSendingFIFO), NWKID), nwkid=NWKID)
            return # Will do at the next round
        target = list(self.ListOfDevices.keys())
        clusterlist = None
    else:
        target = []
        target.append(NWKID)

    for key in target:
        # Let's check that we can do a Configure Reporting. Only during the pairing process (NWKID is provided) or we are on the Main Power
        if key == '0000': continue

        if key not in self.ListOfDevices:
            Domoticz.Error("processConfigureReporting - Unknown key: %s" %key)
            continue
        if 'Status' not in self.ListOfDevices[key]:
            Domoticz.Error("processConfigureReporting - no 'Status' flag for device %s !!!" %key)
            continue
        if self.ListOfDevices[key]['Status'] != 'inDB': continue

        if NWKID is None:
            if not mainPoweredDevice(self, key):
                continue    #  Not Main Powered!

            if 'Health' in self.ListOfDevices[key]:
                if self.ListOfDevices[key]['Health'] == 'Not Reachable':
                    continue

            if self.ListOfDevices[key]['Model'] != {}:
                if self.ListOfDevices[key]['Model'] == 'TI0001': # Livolo switch
                    continue
                if self.ListOfDevices[key]['Model'] in LEGRAND_REMOTES:
                    # Skip configure Reporting for all Legrand Remotes
                    continue

        loggingOutput( self, 'Debug', "----> configurereporting - processing %s" %key, nwkid=key)

        manufacturer = "0000"
        manufacturer_spec = "00"
        direction = "00"
        addr_mode = "02"

        for Ep in self.ListOfDevices[key]['Ep']:
            loggingOutput( self, 'Debug', "------> Configurereporting - processing %s/%s" %(key,Ep), nwkid=key)
            clusterList = getClusterListforEP( self, key, Ep )
            loggingOutput( self, 'Debug', "------> Configurereporting - processing %s/%s ClusterList: %s" %(key,Ep, clusterList), nwkid=key)
            for cluster in clusterList:
                if cluster in ( 'Type', 'ColorMode', 'ClusterType' ):
                    continue
                if cluster not in ATTRIBUTESbyCLUSTERS:
                    continue
                if 'Model' in self.ListOfDevices[key]:
                    if  self.ListOfDevices[key]['Model'] != {}:
                        if self.ListOfDevices[key]['Model'] in (  '3AFE14010402000D' ):
                            if cluster == '0500': # Do not Configure Reporting the Konke Motion sensor
                                continue
                        if self.ListOfDevices[key]['Model'] == 'lumi.light.aqcn02':
                            if cluster in ( '0402', '0403', '0405', '0406'):
                                continue
                
                loggingOutput( self, 'Debug', "--------> Configurereporting - processing %s/%s - %s" %(key,Ep,cluster), nwkid=key)
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
                    loggingOutput( self, 'Debug', "--------> configurereporting - skiping due to existing error in the past", nwkid=key)
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
                        loggingOutput( self, 'Debug', "------> configurereporting - skiping due to done past", nwkid=key)
                        continue

                loggingOutput( self, 'Debug', "---> ConfigureReporting - Skip or not - NWKID: %s busy: %s Queue: %s" \
                        %(NWKID, self.busy, len(self.ZigateComm.zigateSendingFIFO)), nwkid=key)

                if NWKID is None and (self.busy or len(self.ZigateComm.zigateSendingFIFO) > MAX_LOAD_ZIGATE):
                    loggingOutput( self, 'Debug', "---> configureReporting - skip configureReporting for now ... system too busy (%s/%s) for %s"
                        %(self.busy, len(self.ZigateComm.zigateSendingFIFO), key), nwkid=key)
                    loggingOutput( self, 'Debug', "QUEUE: %s" %str(self.ZigateComm.zigateSendingFIFO), nwkid=key)
                    return # Will do at the next round

                loggingOutput( self, 'Debug', "---> configureReporting - requested for device: %s on Cluster: %s" %(key, cluster), nwkid=key)

                # If NWKID is not None, it means that we are asking a ConfigureReporting for a specific device
                # Which happens on the case of New pairing, or a re-join
                if self.pluginconf.pluginConf['allowReBindingClusters'] and NWKID is None:
                    # Correctif 22 Novembre. Delete only for the specific cluster and not the all Set
                    if 'Bind' in self.ListOfDevices[key]:
                        if Ep in self.ListOfDevices[key]['Bind']:
                            if cluster in self.ListOfDevices[key]['Bind'][ Ep ]:
                                del self.ListOfDevices[key]['Bind'][ Ep ][ cluster ]
                    if 'IEEE' in self.ListOfDevices[key]:
                        loggingOutput( self, 'Log', "---> configureReporting - requested Bind for %s on Cluster: %s" %(key, cluster), nwkid=key)
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
                    if cluster == '0300': 
                        # We need to evaluate the Attribute on ZDevice basis
                        if self.ListOfDevices[key]['ZDeviceID'] == {}:
                            continue

                        ZDeviceID = self.ListOfDevices[key]['ZDeviceID']
                        if 'ZDeviceID' in  ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]:
                            if ZDeviceID not in ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['ZDeviceID'] and \
                                    len( ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['ZDeviceID'] ) != 0:
                                loggingOutput( self, 'Debug',"configureReporting - %s/%s skip Attribute %s for Cluster %s due to ZDeviceID %s" %(key,Ep,attr, cluster, ZDeviceID), nwkid=key)
                                continue
                   
                    forceAttribute = False
                    if 'Model' in self.ListOfDevices[key]:
                        if self.ListOfDevices[key]['Model'] == 'SPE600':
                            if cluster == '0702' :
                                if attr == '0000':
                                    continue #We use only 0x0400
                                elif attr == '0400':
                                    forceAttribute = True

                    if 'Attributes List' in self.ListOfDevices[key] and not forceAttribute:
                        if 'Ep' in self.ListOfDevices[key]['Attributes List']:
                            if Ep in self.ListOfDevices[key]['Attributes List']['Ep']:
                                if cluster in self.ListOfDevices[key]['Attributes List']['Ep'][Ep]:
                                    if attr not in self.ListOfDevices[key]['Attributes List']['Ep'][Ep][cluster]:
                                        loggingOutput( self, 'Debug', "configureReporting: drop attribute %s" %attr, nwkid=key)
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

                loggingOutput( self, 'Log', "Configure Reporting %s/%s on cluster %s" %(key, Ep, cluster), nwkid=key)
                datas =   addr_mode + key + "01" + Ep + cluster + direction + manufacturer_spec + manufacturer 
                datas +=  "%02x" %(attrLen) + attrList

                sendZigateCmd(self, "0120", datas )
            # End for Cluster
        # End for Ep
    # End for key

def bindGroup( self, ieee, ep, cluster, groupid ):

    mode = "01"     # Group mode
    nwkid = 'ffff'
    if ieee in self.IEEE2NWK:
        nwkid = self.IEEE2NWK[ieee]

    loggingOutput( self, 'Debug', "bindGroup - ieee: %s, ep: %s, cluster: %s, Group: %s" %(ieee,ep,cluster,groupid) , nwkid=nwkid)
    datas =  ieee + ep + cluster + mode + groupid  
    sendZigateCmd(self, "0030", datas )


def unbindGroup( self, ieee , ep, cluster, groupid):

    mode = "01"     # Group mode
    nwkid = 'ffff'
    if ieee in self.IEEE2NWK:
        nwkid = self.IEEE2NWK[ieee]

    loggingOutput( self, 'Debug', "unbindGroup - ieee: %s, ep: %s, cluster: %s, Group: %s" %(ieee,ep,cluster,groupid) , nwkid=nwkid)
    datas =  ieee + ep + cluster + mode + groupid  
    sendZigateCmd(self, "0031", datas )

def bindDevice( self, ieee, ep, cluster, destaddr=None, destep="01"):
    '''
    Binding a device/cluster with ....
    if not destaddr and destep provided, we will assume that we bind this device with the Zigate coordinator
    '''

    if ieee in self.IEEE2NWK:
        nwkid = self.IEEE2NWK[ieee]
        if nwkid in self.ListOfDevices:
            if 'Model' in self.ListOfDevices[nwkid]:
                if self.ListOfDevices[nwkid]['Model'] != {}:
                    if self.ListOfDevices[nwkid]['Model'] == '3AFE14010402000D' and cluster == '0500':
                        loggingOutput( self, 'Debug',"Do not Bind Konke 3AFE14010402000D to Zigate Ep %s Cluster %s" %(ep, cluster), nwkid)
                        return    # Skip binding IAS for Konke Motion Sensor
                    elif self.ListOfDevices[nwkid]['Model'] == 'SML001' and ep != '02':
                        # only on Ep 02
                        loggingOutput( self, 'Debug',"Do not Bind SML001 to Zigate Ep %s Cluster %s" %(ep, cluster), nwkid)
                        return

    mode = "03"     # IEEE
    if not destaddr:
        #destaddr = self.ieee # Let's grab the IEEE of Zigate
        if self.ZigateIEEE != None and self.ZigateIEEE != '':
            destaddr = self.ZigateIEEE
            destep = "01"
        else:
            loggingOutput( self, 'Debug', "bindDevice - self.ZigateIEEE not yet initialized")
            return

    # let's check if we alreardy bind .
    nwkid = self.IEEE2NWK[ieee]
    if 'Bind' not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]['Bind'] = {}

    if ep not in self.ListOfDevices[nwkid]['Bind']:
        self.ListOfDevices[nwkid]['Bind'][ep] = {}

    if cluster not in self.ListOfDevices[nwkid]['Bind'][ep]:
        self.ListOfDevices[nwkid]['Bind'][ep][cluster] = {}
        self.ListOfDevices[nwkid]['Bind'][ep][cluster]['Stamp'] = int(time())
        self.ListOfDevices[nwkid]['Bind'][ep][cluster]['Phase'] = 'requested'
        self.ListOfDevices[nwkid]['Bind'][ep][cluster]['Status'] = ''

        loggingOutput( self, 'Log', "bindDevice - ieee: %s, ep: %s, cluster: %s, Zigate_ieee: %s, Zigate_ep: %s" %(ieee,ep,cluster,destaddr,destep) , nwkid=nwkid)
        datas =  str(ieee)+str(ep)+str(cluster)+str(mode)+str(destaddr)+str(destep) 
        sendZigateCmd(self, "0030", datas )

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
            loggingOutput( self, 'Debug', "bindDevice - self.ZigateIEEE not yet initialized")
            return

    nwkid = self.IEEE2NWK[ieee]

    # If doing unbind, the Configure Reporting is lost
    if 'ConfigureReporting' in self.ListOfDevices[nwkid]:
        del  self.ListOfDevices[nwkid]['ConfigureReporting']

    # Remove the Bind 
    if 'Bind' in self.ListOfDevices[nwkid]:
            if ep in self.ListOfDevices[nwkid]['Bind']:
                if cluster in self.ListOfDevices[nwkid]['Bind'][ep]:
                    del self.ListOfDevices[nwkid]['Bind'][ep][cluster]

    loggingOutput( self, 'Debug', "unbindDevice - ieee: %s, ep: %s, cluster: %s, Zigate_ieee: %s, Zigate_ep: %s" %(ieee,ep,cluster,destaddr,destep) , nwkid=nwkid)
    datas = str(ieee) + str(ep) + str(cluster) + str(mode) + str(destaddr) + str(destep)
    sendZigateCmd(self, "0031", datas )

    return


def rebind_Clusters( self, NWKID):

    cluster_to_bind = CLUSTERS_LIST

    if 'Manufacturer Name' in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Legrand':
            cluster_to_bind.append( '0003' )

    if 'Bind' in self.ListOfDevices[NWKID]:
        del self.ListOfDevices[NWKID]['Bind']
    if self.pluginconf.pluginConf['doUnbindBind']:
        for iterBindCluster in cluster_to_bind:      
            for iterEp in self.ListOfDevices[NWKID]['Ep']:
                if iterBindCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                    loggingOutput( self, 'Debug', 'Request an Unbind for %s/%s on Cluster %s' %(NWKID, iterEp, iterBindCluster), nwkid=NWKID)
                    unbindDevice( self, self.ListOfDevices[NWKID]['IEEE'], iterEp, iterBindCluster)

    for iterBindCluster in cluster_to_bind:      
        for iterEp in self.ListOfDevices[NWKID]['Ep']:
            if iterBindCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                loggingOutput( self, 'Debug', 'Request a Bind  for %s/%s on Cluster %s' %(NWKID, iterEp, iterBindCluster), nwkid=NWKID)
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
    loggingOutput( self, 'Debug', "identifySend - send an Identify Message to: %s for %04x seconds" %( nwkid, duration), nwkid=nwkid)
    loggingOutput( self, 'Debug', "identifySend - data sent >%s< " %(datas) , nwkid=nwkid)
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
    loggingOutput( self, 'Debug', "set ExtendedPANID - %016x "\
            %( extPANID) )
    sendZigateCmd(self, "0020", datas )

def leaveMgtReJoin( self, saddr, ieee, rejoin=True):
    """
    E_SL_MSG_MANAGEMENT_LEAVE_REQUEST / 0x47 


    This function requests a remote node to leave the network. The request also
    indicates whether the children of the leaving node should also be requested to leave
    and whether the leaving node(s) should subsequently attempt to rejoin the network.

    This function is provided in the ZDP API for the reason
    of interoperability with nodes running non-NXP ZigBee PRO
    stacks that support the generated request. On receiving a
    request from this function, the NXP ZigBee PRO stack will
    return the status ZPS_ZDP_NOT_SUPPORTED.

    """

    Domoticz.Log("leaveMgtReJoin - sAddr: %s , ieee: %s, [%s/%s]" %( saddr, ieee,  self.pluginconf.pluginConf['allowAutoPairing'], rejoin))
    if not self.pluginconf.pluginConf['allowAutoPairing']:
        Domoticz.Log("leaveMgtReJoin - no action taken as 'allowAutoPairing' is %s" %self.pluginconf.pluginConf['allowAutoPairing'])
        return

    if rejoin:
        Domoticz.Status("Switching Zigate in pairing mode to allow %s (%s) coming back" %(saddr, ieee))

        # If Zigate not in Permit to Join, let's switch it to Permit to Join for 60'
        duration = self.permitTojoin['Duration']
        stamp = self.permitTojoin['Starttime']
        if self.permitTojoin['Duration'] == 0:
            dur_req = 60
            self.permitTojoin['Duration'] = 60
            self.permitTojoin['Starttime'] = int(time())
            loggingOutput( self, 'Debug', "leaveMgtReJoin - switching Zigate in Pairing for %s sec" % dur_req)
            sendZigateCmd(self, "0049","FFFC" + '%02x' %dur_req + "00")
            loggingOutput( self, 'Debug', "leaveMgtReJoin - Request Pairing Status")
            sendZigateCmd( self, "0014", "" ) # Request status
        elif self.permitTojoin['Duration'] != 255:
            if  int(time()) >= ( self.permitTojoin['Starttime'] + 60):
                dur_req = 60
                self.permitTojoin['Duration'] = 60
                self.permitTojoin['Starttime'] = int(time())
                loggingOutput( self, 'Debug', "leaveMgtReJoin - switching Zigate in Pairing for %s sec" % dur_req)
                sendZigateCmd(self, "0049","FFFC" + '%02x' %dur_req + "00")
                loggingOutput( self, 'Debug', "leaveMgtReJoin - Request Pairing Status")
                sendZigateCmd( self, "0014", "" ) # Request status

        #Request a Re-Join and Do not remove children
        _leave = '01'
        _rejoin = '01'
        _rmv_children = '01'
        _dnt_rmv_children = '00'

        datas = saddr + ieee + _rejoin + _dnt_rmv_children
        Domoticz.Status("Request a rejoin of (%s/%s)" %(saddr, ieee))
        sendZigateCmd(self, "0047", datas )

def leaveRequest( self, ShortAddr=None, IEEE= None, RemoveChild=False, Rejoin=False ):

    """
    E_SL_MSG_LEAVE_REQUEST / 0x004C / ZPS_eAplZdoLeaveNetwork
    If you wish to move a whole network branch from under
    the requesting node to a different parent node, set
    bRemoveChildren to FALSE and bRejoin to TRUE.
    """

    _ieee = None

    if IEEE is None:
        if ShortAddr and IEEE is None:
            if ShortAddr in self.ListOfDevices:
                if 'IEEE' in self.ListOfDevices[ShortAddr]:
                    _ieee = self.ListOfDevices[ShortAddr]['IEEE']
    else:
        _ieee = IEEE

    if _ieee is None:
        Domoticz.Error("leaveRequest - Unable to determine IEEE address for %s %s" %(ShortAddr, IEEE))
        return

    _rmv_children = '%02X' %RemoveChild
    _rejoin = '%02X' %Rejoin

    datas = _ieee + _rmv_children + _rejoin
    #Domoticz.Status("Sending a leaveRequest - %s %s" %( '0047', datas))
    Domoticz.Log("---------> Sending a leaveRequest - NwkId: %s, IEEE: %s, RemoveChild: %s, Rejoin: %s" %( ShortAddr, IEEE, RemoveChild, Rejoin))
    Domoticz.Log("---------> Sending a leaveRequest - payload %s" %( datas))
    sendZigateCmd(self, "0047", datas )

def removeZigateDevice( self, IEEE ):
    """
    E_SL_MSG_NETWORK_REMOVE_DEVICE / 0x0026 / ZPS_teStatus ZPS_eAplZdoRemoveDeviceReq

    This function can be used (normally by the Co-ordinator/Trust Centre) to request
    another node (such as a Router) to remove one of its children from the network (for
    example, if the child node does not satisfy security requirements).

    The Router receiving this request will ignore the request unless it has originated from
    the Trust Centre or is a request to remove itself. If the request was sent without APS
    layer encryption, the device will ignore the request. If APS layer security is not in use,
    the alternative function ZPS_eAplZdoLeaveNetwork() should be used.


    u64ParentAddr 64-bit IEEE/MAC address of parent to be instructed
    u64ChildAddr 64-bit IEEE/MAC address of child node to be removed
    """

    nwkid = None
    if IEEE in self.IEEE2NWK:
        nwkid = self.IEEE2NWK[ IEEE ]

    if nwkid is None:
        Domoticz.Error("removeZigateDevice - Unable to find device for %s" %IEEE)
        return

    # Do we have to remove a Router or End Device ?
    router = False
    if 'LogicalType' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['LogicalType'] in ( 'Router' ):
            router = True
    if 'DeviceType' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['DeviceType'] in ( 'FFD' ):
            router = True
    if 'MacCapa' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['MacCapa'] in ( '8e' ):
            router = True
    if 'PowerSource' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['PowerSource'] in ( 'Main'):
            router = True

        Domoticz.Status("Remove from Zigate Device = " + " IEEE = " +str(IEEE) )

    if router:
        ParentAddr = IEEE
        ChildAddr = IEEE
    else:
        if self.ZigateIEEE is None:
            Domoticz.Error("Zigae IEEE unknown: %s" %self.ZigateIEEE)
            return
        ParentAddr = self.ZigateIEEE
        ChildAddr = IEEE

    sendZigateCmd(self, "0026", ParentAddr + ChildAddr )

    return


def thermostat_Setpoint_SPZB(  self, key, setpoint):

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0x4003
    data_type = "29" # Int16
    loggingOutput( self, 'Debug', "setpoint: %s" %setpoint, nwkid=key)
    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    loggingOutput( self, 'Debug', "setpoint: %s" %setpoint, nwkid=key)
    Hdata = "%04x" %setpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingOutput( self, 'Debug', "thermostat_Setpoint_SPZB - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,Hdata,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)


def thermostat_Setpoint( self, key, setpoint):

    if 'Model' in self.ListOfDevices[key]:
        if self.ListOfDevices[key]['Model'] != {}:
            if self.ListOfDevices[key]['Model'] == 'SPZB0001':
                thermostat_Setpoint_SPZB( self, key, setpoint)

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0x0012
    data_type = "29" # Int16
    loggingOutput( self, 'Debug', "setpoint: %s" %setpoint, nwkid=key)
    setpoint = int(( setpoint * 2 ) / 2)   # Round to 0.5 degrees
    loggingOutput( self, 'Debug', "setpoint: %s" %setpoint, nwkid=key)
    Hdata = "%04x" %setpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingOutput( self, 'Debug', "thermostat_Setpoint - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,Hdata,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

    ReadAttributeRequest_0201(self, key)


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
    loggingOutput( self, 'Debug', "thermostat_eurotronic_hostflag - for %s with value %s / cluster: %s, attribute: %s type: %s action: %s"
            %(key,data,cluster_id,attribute,data_type, action), nwkid=key)

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
    loggingOutput( self, 'Debug', "thermostat_Calibration - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,attribute,data_type), nwkid=key)

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
    loggingOutput( self, 'Debug', "thermostat_Mode - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,attribute,data_type), nwkid=key)

def ReadAttributeRequest_0201(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0201 - Key: %s " %key, nwkid=key)
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
    loggingOutput( self, 'Debug', "Request 0201 %s/%s-%s 0201 %s " %(key, EPin, EPout, listAttributes), nwkid=key)
    ReadAttributeReq( self, key, EPin, EPout, "0201", listAttributes )

    listAttributes = []
    if str(self.ListOfDevices[key]['Model']).find('SPZB') == 0:
        loggingOutput( self, 'Debug', "- req Attributes for Eurotronic", nwkid=key)
        listAttributes.append(0x4000)        # TRV Mode
        listAttributes.append(0x4001)        # Set Valve Position
        listAttributes.append(0x4002)        # Errors
        listAttributes.append(0x4003)        # Curret Temperature Set point Eurotronics
        listAttributes.append(0x4008)        # HOst Flag
    elif str(self.ListOfDevices[key]['Model']).find('Super TR') == 0:
        loggingOutput( self, 'Debug', "- req Attributes for  Super TR", nwkid=key)
        listAttributes.append(0x0403)    
        listAttributes.append(0x0405)
        listAttributes.append(0x0406)
        listAttributes.append(0x0408)   
        listAttributes.append(0x0409)  
    elif str(self.ListOfDevices[key]['Model']).find('EH-ZB-RTS') == 0:
        listAttributes.append(0xe010)  

    if len(listAttributes) > 0:
        loggingOutput( self, 'Debug', "Request 0201 %s/%s-%s 0201 %s " %(key, EPin, EPout, listAttributes), nwkid=key)
        ReadAttributeReq( self, key, EPin, EPout, "0201", listAttributes )


def ReadAttributeRequest_0204(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0204 - Key: %s " %key, nwkid=key)
    # Power Config
    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0204" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp

    listAttributes = []
    listAttributes.append(0x0001) # Read KeypadLockout

    if len(listAttributes) > 0:
        loggingOutput( self, 'Debug', "Request 0204 %s/%s-%s 0204 %s " %(key, EPin, EPout, listAttributes), nwkid=key)
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
    loggingOutput( self, 'Debug', "lockmode: %s" %lockmode, nwkid=key)
    lockmode = LOCK_MODE[lockmode]
    Hdata = "%02x" %lockmode
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0204" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingOutput( self, 'Debug', "Thermostat_LockMode - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,Hdata,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)


def schneider_thermostat( self, nwkid ):

    manuf_id = "105e"
    manuf_spec = "01"
    cluster_id = "%04x" %0x0000
    Hattribute = "%04x" %0xe050
    data_type = "10" # Boo
    data = "%02x" %True

    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0204" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingOutput( self, 'Log', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,Hdata,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)


    Hattribute = "%04x" %0x5011
    data_type = "42" # String
    data = "en" 
    loggingOutput( self, 'Log', "Schneider Write Attribute %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,Hdata,cluster_id,Hattribute,data_type), nwkid=key)
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

def legrand_fc01( self, nwkid, command, OnOff):

            # EnableLedInDark -> enable to detect the device in dark 
            # EnableDimmer -> enable/disable dimmer
            # EnableLedIfOn -> enable Led with device On

    LEGRAND_REFRESH_TIME = ( 3 * 3600) + 15
    LEGRAND_CLUSTER_FC01 = {
            'Dimmer switch w/o neutral':  { 'EnableLedInDark': '0001'  , 'EnableDimmer': '0000'   , 'EnableLedIfOn': '0002' },
            'Connected outlet': { 'EnableLedIfOn': '0002' },
            'Shutter switch with neutral': { 'EnableLedIfOn': '0001' },
            'Micromodule switch': { 'None': 'None' },
            'Cable outlet': { 'FilPilote': '0000' } }

    if nwkid not in self.ListOfDevices:
        return

    if command not in ( 'FilPilote', 'EnableLedInDark', 'EnableDimmer', 'EnableLedIfOn'):
        return

    if 'Model' not in self.ListOfDevices[nwkid]:
        return

    if self.ListOfDevices[nwkid]['Model'] == {}:
        return

    if self.ListOfDevices[nwkid]['Model'] not in LEGRAND_CLUSTER_FC01:
        return

    if 'Legrand' not in self.ListOfDevices[nwkid]:
        self.ListOfDevices[nwkid]['Legrand'] = {}
        self.ListOfDevices[nwkid]['Legrand']['FilPilote'] = 0
        self.ListOfDevices[nwkid]['Legrand']['EnableLedInDark'] = 0
        self.ListOfDevices[nwkid]['Legrand']['EnableDimmer'] = 0
        self.ListOfDevices[nwkid]['Legrand']['EnableLedIfOn'] = 0

    if command == 'EnableLedInDark' and command in LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ]:
        if time() < self.ListOfDevices[nwkid]['Legrand']['EnableLedInDark'] + LEGRAND_REFRESH_TIME:
            return
            
        self.ListOfDevices[nwkid]['Legrand']['EnableLedInDark'] = int(time())

        data_type = "10" # Bool
        if OnOff == 'On': Hdata = '01' # Enable Led in Dark
        elif OnOff == 'Off': Hdata = '00' # Disable led in dark
        else: Hdata = '00'
        
    elif command == 'EnableDimmer' and command in LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ]:
        if time() < self.ListOfDevices[nwkid]['Legrand']['EnableDimmer'] + LEGRAND_REFRESH_TIME:
            return

        self.ListOfDevices[nwkid]['Legrand']['EnableDimmer'] = int(time())
        data_type = "09" #  16-bit Data
        if OnOff == 'On': Hdata = '0101' # Enable Dimmer
        elif OnOff == 'Off': Hdata = '0100' # Disable Dimmer
        else: Hdata = '0000'

    elif command == 'FilPilote' and command in LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ]:
        if time() < self.ListOfDevices[nwkid]['Legrand']['FilPilote'] + LEGRAND_REFRESH_TIME:
            return

        self.ListOfDevices[nwkid]['Legrand']['FilPilote'] = int(time())
        data_type = "09" #  16-bit Data
        if OnOff == 'On': Hdata = '0001' # Enable 
        elif OnOff == 'Off': Hdata = '0002' # Disable
        else: Hdata = '0000'

    elif command == 'EnableLedIfOn' and command in LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ]:
        if time() < self.ListOfDevices[nwkid]['Legrand']['EnableLedIfOn'] + LEGRAND_REFRESH_TIME:
            return

        self.ListOfDevices[nwkid]['Legrand']['EnableLedIfOn'] = int(time())
        data_type = "10" # Bool
        if OnOff == 'On': Hdata = '01' # Enable Led when On
        elif OnOff == 'Off': Hdata = '00' # Disable led when On 
        else: Hdata = '00'
    else:
        return

    Hattribute = LEGRAND_CLUSTER_FC01[ self.ListOfDevices[nwkid]['Model'] ][command]
    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0xfc01

    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "fc01" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingOutput( self, 'Debug', "legrand %s OnOff - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(command, nwkid,Hdata,cluster_id,Hattribute,data_type), nwkid=nwkid)
    write_attribute( self, nwkid, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)


def legrand_fc40( self, Mode ):
    # With the permission of @Thorgal789 who did the all reverse enginnering of this cluster

    CABLE_OUTLET_MODE = { 
            'Confort': 0x00,
            'Confort -1' : 0x01,
            'Confort -2' : 0x02,
            'Eco': 0x03,
            'Hors-gel' : 0x04,
            'Off': 0x05
            }

    if Mode not in CABLE_OUTLET_MODE:
        return
    Hattribute = '0000'
    data_type = '30' # 8bit Enum
    Hdata = CABLE_OUTLET_MODE[ Mode ]
    manuf_id = "1021" #Legrand Code
    manuf_spec = "01" # Manuf specific flag
    cluster_id = "%04x" %0xfc40

    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "fc40" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    loggingOutput( self, 'Debug', "legrand %s Set Fil pilote mode - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(command, nwkid,Hdata,cluster_id,Hattribute,data_type), nwkid=nwkid)
    write_attribute( self, nwkid, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)



def legrand_dimOnOff( self, OnOff):
    '''
    Call from Web
    '''

    for NWKID in self.ListOfDevices:
        if 'Manufacturer Name' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Legrand':
                if 'Model' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Model'] != {}:
                        if self.ListOfDevices[NWKID]['Model'] in ( 'Dimmer switch w/o neutral', ):
                            legrand_fc01( self, NWKID, 'EnableDimmer', OnOff)
                        else:
                            Domoticz.Log("legrand_ledOnOff not a matching device, skip it .... %s " %self.ListOfDevices[NWKID]['Model'])


def legrand_ledIfOnOnOff( self, OnOff):
    '''
    Call from Web 
    '''

    for NWKID in self.ListOfDevices:
        if 'Manufacturer Name' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Legrand':
                if 'Model' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Model'] != {}:
                        if self.ListOfDevices[NWKID]['Model'] in ( 'Connected outlet', 'Dimmer switch w/o neutral', 'Shutter switch with neutral', 'Micromodule switch' ):
                            legrand_fc01( self, NWKID, 'EnableLedIfOn', OnOff)
                        else:
                            Domoticz.Log("legrand_ledOnOff not a matching device, skip it .... %s " %self.ListOfDevices[NWKID]['Model'])

def legrand_ledInDark( self, OnOff):
    '''
    Call from Web 
    '''

    for NWKID in self.ListOfDevices:
        if 'Manufacturer Name' in self.ListOfDevices[NWKID]:
            if self.ListOfDevices[NWKID]['Manufacturer Name'] == 'Legrand':
                if 'Model' in self.ListOfDevices[NWKID]:
                    if self.ListOfDevices[NWKID]['Model'] != {}:
                        if self.ListOfDevices[NWKID]['Model'] in ( 'Connected outlet', 'Dimmer switch w/o neutral', 'Shutter switch with neutral', 'Micromodule switch' ):
                            legrand_fc01( self, NWKID, 'EnableLedInDark', OnOff)
                        else:
                            Domoticz.Log("legrand_ledInDark not a matching device, skip it .... %s " %self.ListOfDevices[NWKID]['Model'])

"""
Livolo commands.

- looks like when Livolo switch is comming it is sending a Read Attribute to the Zigate on cluster 0x0001 Attributes: 0x895e, 0x1802, 0x4b00, 0x0012, 0x0021. In a malformed packet

- In order to bind the Livolo do:
(1) Send a Toggle
(2) Move to level 108 with transition 0.1 seconds
(3) Move to level 108 with transition 0.1 seconds
(4) Move to level 108 with transition 0.1 seconds

- When receiving 0x0001/0x0007 we must update the MacCapa attributes, accordingly to Mains (Single Phase)

"""


def livolo_bind( self, nwkid, EPout):

    livolo_OnOff(self, nwkid, EPout, 'All', 'Toggle')
    livolo_OnOff(self, nwkid, EPout, 'Left', 'On')
    livolo_OnOff(self, nwkid, EPout, 'Left', 'On')
    livolo_OnOff(self, nwkid, EPout, 'Left', 'On')

def livolo_OnOff( self, nwkid , EPout, devunit, onoff):
    """
    Levolo On/Off command are based on Level Control cluster
    Level: 108/0x6C  -> On
    Level: 1/0x01 -> Off
    Left Unit: Timing 1
    Right Unit: Timing 2
    """

    loggingOutput( self, 'Debug', "livolo_OnOff - devunit: %s, onoff: %s" %(devunit, onoff), nwkid=nwkid)

    if onoff not in ( 'On', 'Off', 'Toggle'): return
    if devunit not in ( 'Left', 'Right', 'All'): return

    if onoff == 'Toggle' and devunit == 'All':
        loggingOutput( self, 'Debug', "livolo_toggle" , nwkid=nwkid)
        sendZigateCmd(self, "0092","02" + nwkid + '01' + EPout + '02')
    else:
        level_value = timing_value = None
        if onoff == 'On': level_value = '%02x' %108
        elif onoff == 'Off': level_value = '%02x' %1

        if devunit == 'Left': timing_value = '0001'
        elif devunit == 'Right': timing_value = '0002'

        if level_value is not None and timing_value is not None:
            loggingOutput( self, 'Debug', "livolo_OnOff - %s/%s Level: %s, Timing: %s" %( nwkid, EPout, level_value, timing_value), nwkid=nwkid)
            sendZigateCmd(self, "0081","02" + nwkid + '01' + EPout + '00' + level_value + timing_value)
        else:
            Domoticz.Error( "livolo_OnOff - Wrong parameters sent ! onoff: %s devunit: %s" %(onoff, devunit))

def raw_APS_request( self, targetaddr, dest_ep, cluster, profileId, payload, zigate_ep='01'):

    """" Command
    This function submits a request to send data to a remote node, with no restrictions
    on the type of transmission, destination address, destination application profile,
    destination cluster and destination endpoint number - these destination parameters
    do not need to be known to the stack or defined in the ZPS configuration. In this
    sense, this is most general of the Data Transfer functions.

    The data is sent in an Application Protocol Data Unit (APDU) instance,

    Command 0x0530
    address mode
    target short address 4
    source endpoint 2
    destination endpoint 2
    clusterId 4
    profileId 4
    security mode 2
    radius 2
    data length 2
    data Array of 2

    eSecurityMode is the security mode for the data transfer, one of:
            0x00 : ZPS_E_APL_AF_UNSECURE (no security enabled)
            0x01 : ZPS_E_APL_AF_SECURE Application-level security using link key and network key)
            0x02 : ZPS_E_APL_AF_SECURE_NWK (Network-level security using network key)
            0x10 : ZPS_E_APL_AF_SECURE | ZPS_E_APL_AF_EXT_NONCE (Application-level security using link key and network key with the extended NONCE included in the frame)
            0x20 : ZPS_E_APL_AF_WILD_PROFILE (May be combined with above flags using OR operator. Sends the message using the wild card profile (0xFFFF) instead of the profile in the associated Simple descriptor)
    u8Radius is the maximum number of hops permitted to the destination node (zero value specifies that default maximum is to be used)

    """
    """ APS request command Payload

    target addr ( IEEE )
    target ep
    clusterID
    dest addr mode
    dest addr
    dest ep

    """

    SECURITY = 0x33
    RADIUS = 0x00

    addr_mode ='%02X' % ADDRESS_MODE['short']
    security = '%02X' %SECURTITY
    radius = '%02X' %RADIUS

    len_payload = len(payload)

    loggingOutput( self, 'Log', "raw_APS_request - Addr: %s Ep: %s Cluster: %s ProfileId: %s Payload: %s" %(targetaddr, dest_ep, cluster, profileId, payload))
    sendZigateCmd(self, "0530", addr_mode + targetaddr + zigate_ep + src_ep + cluster + profileId + security + radius + len_payload + payload)


## Scene

def scene_membership_request( self, nwkid, ep, groupid='0000'):

    datas = '02' + nwkid + '01' + ep +  groupid
    sendZigateCmd(self, "00A6", datas )

def xiaomi_leave( self, NWKID):

    if self.permitTojoin['Duration'] != 255:
        Domoticz.Log("------> switch zigate in pairing mode")
        ZigatePermitToJoin(self, ( 1 * 60 ))

    # sending a Leave Request to device, so the device will send a leave
    Domoticz.Log("------> Sending a leave to Xiaomi battery devive: %s" %(NWKID))
    leaveRequest( self, IEEE= self.ListOfDevices[NWKID]['IEEE'], Rejoin=True )


