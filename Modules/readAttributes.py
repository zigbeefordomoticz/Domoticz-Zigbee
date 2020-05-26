#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: readAttrbutes

    Description: 

"""

import Domoticz

from datetime import datetime
from time import time

from Modules.zigateConsts import  MAX_READATTRIBUTES_REQ,  ZIGATE_EP
from Modules.basicOutputs import sendZigateCmd
from Modules.logging import loggingReadAttributes 
from Modules.tools import getListOfEpForCluster


def ReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes , manufacturer_spec = '00', manufacturer = '0000'):

    def split_list(alist, wanted_parts=1):
        """
        Split the list of attrributes in wanted part
        """
        length = len(alist)
        return [ alist[i*length // wanted_parts: (i+1)*length // wanted_parts] for i in range(wanted_parts) ]

    if not isinstance(ListOfAttributes, list) or len (ListOfAttributes) < MAX_READATTRIBUTES_REQ:
        normalizedReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes )
    else:
        loggingReadAttributes( self, 'Debug2', "----------> ------- %s/%s %s ListOfAttributes: " %(addr, EpOut, Cluster) + " ".join("0x{:04x}".format(num) for num in ListOfAttributes), nwkid=addr)
        nbpart = - (  - len(ListOfAttributes) // MAX_READATTRIBUTES_REQ) 
        for shortlist in split_list(ListOfAttributes, wanted_parts=nbpart):
            loggingReadAttributes( self, 'Debug2', "----------> ------- Shorter: " + ", ".join("0x{:04x}".format(num) for num in shortlist), nwkid=addr)
            normalizedReadAttributeReq( self, addr, EpIn, EpOut, Cluster , shortlist )

def normalizedReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes , manufacturer_spec = '00', manufacturer = '0000'):

    def skipThisAttribute( self, addr, EpOut, Cluster, Attr):
        skipReadAttr = False

        if 'TimeStamps' not in  self.ListOfDevices[addr]['ReadAttributes']:
            skipReadAttr = True
        if not skipReadAttr and str(EpOut+'-'+str(Cluster)) not in self.ListOfDevices[addr]['ReadAttributes']['TimeStamps']:
            skipReadAttr = True
        if not skipReadAttr and 'ReadAttributes' not in self.ListOfDevices[addr]:
            skipReadAttr = True
        if not skipReadAttr and 'Ep' not in self.ListOfDevices[addr]['ReadAttributes']:
            skipReadAttr = True
        if not skipReadAttr and EpOut not in  self.ListOfDevices[addr]['ReadAttributes']['Ep']:
            skipReadAttr = True
        if not skipReadAttr and str(Cluster) not in  self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut]:
            skipReadAttr = True
        if not skipReadAttr and Attr not in self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)]:
            skipReadAttr = False

        #if  not skipReadAttr and self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] == {} and \
        #        self.ListOfDevices[addr]['ReadAttributes']['TimeStamps'][EpOut+'-'+str(Cluster)] != 0:
        #    loggingReadAttributes( self, 'Debug2', "normalizedReadAttrReq - cannot get Attribute self.ListOfDevices[%s]['ReadAttributes']['Ep'][%s][%s][%s]: %s"
        #             %(addr, EpOut, Cluster, Attr, self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] ), nwkid=addr)
        #    skipReadAttr = True
        if not skipReadAttr and self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] in ( '86', '8c'):    # 8c Not supported, 86 No cluster match
            loggingReadAttributes( self, 'Debug2', "normalizedReadAttrReq - Last status self.ListOfDevices[%s]['ReadAttributes']['Ep'][%s][%s][%s]: %s"
                     %(addr, EpOut, Cluster, Attr, self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] ), nwkid=addr)
            skipReadAttr = True
        if not skipReadAttr and self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] != '00' and \
                self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] != {}:
            loggingReadAttributes( self, 'Debug2', "normalizedReadAttrReq - Last status self.ListOfDevices[%s]['ReadAttributes']['Ep'][%s][%s][%s]: %s"
                     %(addr, EpOut, Cluster, Attr, self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] ), nwkid=addr)
            skipReadAttr = True

        if not skipReadAttr and 'Model' in self.ListOfDevices[addr]:
            if self.ListOfDevices[addr]['Model'] in self.DeviceConf:
                #Domoticz.Log("-----> Checking Attributes from Model for device %s" %addr)
                if 'ReadAttributes' in self.DeviceConf[ self.ListOfDevices[addr]['Model'] ]:
                    #Domoticz.Log("-------> Checking Attributes from Model is IN")
                    if Cluster in  self.DeviceConf[ self.ListOfDevices[addr]['Model'] ]['ReadAttributes']:
                        #Domoticz.Log("---------> Checking Attributes %s from Model is IN, Cluster %s against %s" %( Attr, Cluster, self.DeviceConf[ self.ListOfDevices[addr]['Model'] ]['ReadAttributes'][Cluster]))
                        if Attr not in self.DeviceConf[ self.ListOfDevices[addr]['Model'] ]['ReadAttributes'][Cluster]:
                            loggingReadAttributes( self, 'Debug2', "normalizedReadAttrReq - Skip Read Attribute due to DeviceConf Nwkid: %s Cluster: %s Attribute: %s"
                                    %(addr, Cluster, Attr ), nwkid=addr)
                            skipReadAttr = True

        return skipReadAttr

    # Start method
    if 'Health' in self.ListOfDevices[addr]:
        if self.ListOfDevices[addr]['Health'] == 'Not Reachable':
            return

    direction = '00'

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
        _tmpAttr = ListOfAttributes
        ListOfAttributes = []
        ListOfAttributes.append( _tmpAttr)

    lenAttr = 0
    weight = int ((lenAttr ) / 2) + 1
    Attr =''
    loggingReadAttributes( self, 'Debug2', "attributes: " +str(ListOfAttributes), nwkid=addr)
    for x in ListOfAttributes:
        Attr_ = "%04x" %(x)
        if Attr_ in self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)]:
            if skipThisAttribute(self,  addr, EpOut, Cluster, Attr_):
                continue

            loggingReadAttributes( self, 'Debug2', "normalizedReadAttrReq: %s for %s/%s" %(Attr_, addr, self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr_]), nwkid=addr)
            self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr_] = {}
        Attr += Attr_
        lenAttr += 1

    if lenAttr == 0:
        return

    loggingReadAttributes( self, 'Debug', "-- normalizedReadAttrReq ---- addr =" +str(addr) +" Cluster = " +str(Cluster) +" Attributes = " + ", ".join("0x{:04x}".format(num) for num in ListOfAttributes), nwkid=addr )
    self.ListOfDevices[addr]['ReadAttributes']['TimeStamps'][EpOut+'-'+str(Cluster)] = int(time())
    datas = "02" + addr + EpIn + EpOut + Cluster + direction + manufacturer_spec + manufacturer + "%02x" %(lenAttr) + Attr
    sendZigateCmd(self, "0100", datas )

def retreive_ListOfAttributesByCluster( self, key, Ep, cluster ):

    ATTRIBUTES = { 
            '0000': [ 0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007, 0x000A, 0x000F, 0x0010, 0x0015, 0x4000, 0xF000],
            '0001': [ 0x0000, 0x0001, 0x0003, 0x0020, 0x0021, 0x0033, 0x0035 ],
            '0003': [ 0x0000],
            '0004': [ 0x0000],
            '0005': [ 0x0001, 0x0002, 0x0003, 0x0004],
            '0006': [ 0x0000],
            '0008': [ 0x0000],
            '000a': [ 0x0000],
            '000c': [ 0x0051, 0x0055, 0x006f, 0xff05],
            '0100': [ 0x0000, 0x0001, 0x0002, 0x0010, 0x0011],
            '0102': [ 0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0007, 0x0008, 0x0009, 0x000A, 0x000B, 0x0010, 0x0011, 0x0014, 0x0017, 0xfffd],
            '0201': [ 0x0000, 0x0008, 0x0010, 0x0012,  0x0014, 0x0015, 0x0016, 0x001B, 0x001C, 0x001F],
            '0300': [ 0x0000, 0x0001, 0x0003, 0x0004, 0x0007, 0x0008, 0x4010],
            '0400': [ 0x0000],
            '0402': [ 0x0000],
            '0403': [ 0x0000],
            '0405': [ 0x0000],
            '0406': [ 0x0000, 0x0001, 0x0010, 0x0011],
            '0500': [ 0x0000, 0x0001, 0x0002],
            '0502': [ 0x0000],
            '0702': [ 0x0000, 0x0200, 0x0301, 0x0302, 0x0303, 0x0306, 0x0400],
            '000f': [ 0x0000, 0x0051, 0x0055, 0x006f, 0xfffd], 
            '0b04': [ 0x0505, 0x0508, 0x050b], # https://docs.smartthings.com/en/latest/ref-docs/zigbee-ref.html
            'fc01': [ 0x0000, 0x0001],
            'fc21': [ 0x0001]
            }

    targetAttribute = None

    # Attribute based on pre-cofnigured list in DeviceConf
    if 'Model' in self.ListOfDevices[key]:
        if self.ListOfDevices[key]['Model'] in self.DeviceConf:
            if 'ReadAttributes' in self.DeviceConf[ self.ListOfDevices[key]['Model'] ]:
                if cluster in  self.DeviceConf[ self.ListOfDevices[key]['Model'] ]['ReadAttributes']:
                    #Domoticz.Log("-->Attributes based on Configuration")
                    targetAttribute = []
                    for attr in self.DeviceConf[ self.ListOfDevices[key]['Model'] ]['ReadAttributes'][cluster]:
                        #Domoticz.Log("----> Device: %s Adding Attribute %s for Cluster %s" %(key, attr, cluster))
                        targetAttribute.append( int(attr,16) )
                    return targetAttribute

    # Attribute based on the Attributes List given by the device
    if targetAttribute is None and 'Attributes List' in self.ListOfDevices[key]:
        if 'Ep' in self.ListOfDevices[key]['Attributes List']:
            if Ep in self.ListOfDevices[key]['Attributes List']['Ep']:
                if cluster in self.ListOfDevices[key]['Attributes List']['Ep'][Ep]:
                    targetAttribute = []
                    loggingReadAttributes( self, 'Debug', "retreive_ListOfAttributesByCluster: Attributes from Attributes List", nwkid=key)
                    for attr in  self.ListOfDevices[key]['Attributes List']['Ep'][Ep][cluster]:
                        targetAttribute.append( int(attr,16) )
                    if 'Model' in self.ListOfDevices[key]:
                        # Force Read Attributes 
                        if (self.ListOfDevices[key]['Model'] == 'SPE600' and cluster == '0702') or \
                           (self.ListOfDevices[key]['Model'] == 'TS0302' and cluster == '0102'):     # Zemismart Blind switch
                            for addattr in ATTRIBUTES[cluster]:
                                if addattr not in targetAttribute:
                                    targetAttribute.append( addattr )

    # Attribute based on default
    if targetAttribute is None:
        loggingReadAttributes( self, 'Debug2', "retreive_ListOfAttributesByCluster: default attributes list for cluster: %s" %cluster, nwkid=key)
        if cluster in ATTRIBUTES:
            targetAttribute = ATTRIBUTES[cluster]
        else:
            Domoticz.Debug("retreive_ListOfAttributesByCluster: Missing Attribute for cluster %s" %cluster)
            targetAttribute = [ 0x0000 ]

    loggingReadAttributes( self, 'Debug', "---- retreive_ListOfAttributesByCluster: List of Attributes for cluster %s : " %(cluster) + " ".join("0x{:04x}".format(num) for num in targetAttribute), nwkid=key)

    return targetAttribute

def ReadAttributeRequest_0000_basic(self, key):
    # In order to ping a device, we simply send a Read Attribute on Cluster 0x0000 and looking for Attribute 0x0000
    # This Cluster/Attribute is mandatory for each devices.

    loggingReadAttributes( self, 'Debug', "Ping Device Physical device - Key: %s" %(key), nwkid=key)
    if 'ReadAttributes' not in self.ListOfDevices[key]:
        self.ListOfDevices[key]['ReadAttributes'] = {}
    if 'TimeStamps' not in self.ListOfDevices[key]['ReadAttributes']:
        self.ListOfDevices[key]['ReadAttributes']['TimeStamps'] = {}

    ListOfEp = getListOfEpForCluster( self, key, '0000' ) 
    for EPout in ListOfEp:
        self.ListOfDevices[key]['ReadAttributes']['TimeStamps'][ EPout + '-' + '0000'] = int(time())
        datas = '02' + key + ZIGATE_EP + EPout + '0000' + '00' + '00' + '0000' + '01' + '0000'
        sendZigateCmd(self, "0100", datas )
      

def ReadAttributeRequest_0000(self, key, fullScope=True):
    # Basic Cluster
    # The Ep to be used can be challenging, as if we are in the discovery process, the list of Eps is not yet none and it could even be that the Device has only 1 Ep != 01

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0000 - Key: %s , Scope: %s" %(key, fullScope), nwkid=key)
    EPout = '01'

    listAttributes = []

    # Checking if Ep list is empty, in that case we are in discovery mode and 
        # we don't really know what are the EPs we can talk to.
    if not fullScope or self.ListOfDevices[key]['Ep'] is None or self.ListOfDevices[key]['Ep'] == {}:
        loggingReadAttributes( self, 'Debug', "--> Not full scope", nwkid=key)
        loggingReadAttributes( self, 'Debug', "--> Build list of Attributes", nwkid=key)
        skipModel = False

        # Do we Have Manufacturer
        if self.ListOfDevices[key]['Manufacturer'] == '':
            loggingReadAttributes( self, 'Debug', "----> Adding: %s" %'0004', nwkid=key)
            listAttributes.append(0x0004)
        else:
            if self.ListOfDevices[key]['Manufacturer'] == 'Legrand':
                loggingReadAttributes( self, 'Debug', "----> Adding: %s" %'f000', nwkid=key)
                if 0x4000 not in listAttributes:
                    listAttributes.append(0x4000)
                if 0xf000 not in listAttributes:
                    listAttributes.append(0xf000)
                skipModel = True
            if self.ListOfDevices[key]['Manufacturer'] == '1110':
                listAttributes.append(0x0010)
                skipModel = True

        # Do We have Model Name
        if not skipModel and self.ListOfDevices[key]['Model'] in [{}, '']:
            loggingReadAttributes( self, 'Debug', "----> Adding: %s" %'0005', nwkid=key)
            listAttributes.append(0x0005)        # Model Identifier

        if ( 'Model' in self.ListOfDevices[key] and self.ListOfDevices[key]['Model'] != {} and self.ListOfDevices[key]['Model'] != '' ):
            readAttr = False
            if ( self.ListOfDevices[key]['Model'] in self.DeviceConf and \
                    'ReadAttributes' in self.DeviceConf[self.ListOfDevices[key]['Model']] and \
                    '0000' in self.DeviceConf[self.ListOfDevices[key]['Model']][ 'ReadAttributes' ] ):
                readAttr = True
                for attr in self.DeviceConf[ self.ListOfDevices[key]['Model'] ]['ReadAttributes']['0000']:
                    listAttributes.append( int( attr , 16))  

                        #if not readAttr and self.ListOfDevices[key]['Model'] != 'TI0001':
                        #    loggingReadAttributes( self, 'Debug', "----> Adding: %s" %'000A', nwkid=key)
                        #    listAttributes.append(0x000A)        # Product Code

        if self.ListOfDevices[key]['Ep'] is None or self.ListOfDevices[key]['Ep'] == {}:
            loggingReadAttributes( self, 'Debug', "Request Basic  via Read Attribute request: " + key + " EPout = " + "01, 02, 03, 06, 09" , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, "01", "0000", listAttributes )
            ReadAttributeReq( self, key, ZIGATE_EP, "02", "0000", listAttributes )
            ReadAttributeReq( self, key, ZIGATE_EP, "03", "0000", listAttributes )
            ReadAttributeReq( self, key, ZIGATE_EP, "06", "0000", listAttributes ) # Livolo
            ReadAttributeReq( self, key, ZIGATE_EP, "09", "0000", listAttributes )
        else:
            for tmpEp in self.ListOfDevices[key]['Ep']:
                if "0000" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout= tmpEp 
            loggingReadAttributes( self, 'Debug', "Request Basic  via Read Attribute request: " + key + " EPout = " + EPout + " Attributes: " + str(listAttributes), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0000", listAttributes )

    else:
        loggingReadAttributes( self, 'Debug', "--> Full scope", nwkid=key)
        ListOfEp = getListOfEpForCluster( self, key, '0000' ) 
        for EPout in ListOfEp:
            for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0000'):
                listAttributes.append( iterAttr )

            if ( 'Model' in self.ListOfDevices[key] and self.ListOfDevices[key]['Model'] != {} ):
                if str(self.ListOfDevices[key]['Model']).find('lumi') != -1:
                    listAttributes.append(0xff01)
                    listAttributes.append(0xff02)

                if str(self.ListOfDevices[key]['Model']).find('TS0302') != -1: # Inter Blind Zemismart
                    listAttributes.append(0xfffd)
                    listAttributes.append(0xfffe)
                    listAttributes.append(0xffe1)
                    listAttributes.append(0xffe2)
                    listAttributes.append(0xffe3)

            # Adjustement before request
            listAttrSpecific = []
            listAttrGeneric = []
            if ( 'Manufacturer' in self.ListOfDevices[key] and self.ListOfDevices[key]['Manufacturer'] == '105e' ):
                # We need to break the Read Attribute between Manufacturer specifcs one and teh generic one
                for _attr in list(listAttributes):
                    if _attr in ( 0xe000, 0xe001, 0xe002 ):
                        listAttrSpecific.append( _attr )
                    else:
                        listAttrGeneric.append( _attr )
                del listAttributes
                listAttributes = listAttrGeneric

            loggingReadAttributes( self, 'Debug', "Request Basic  via Read Attribute request %s/%s %s" %(key, EPout, str(listAttributes)), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0000", listAttributes )

            if listAttrSpecific:
                loggingReadAttributes( self, 'Debug', "Request Basic  via Read Attribute request Manuf Specific %s/%s %s" %(key, EPout, str(listAttributes)), nwkid=key)
                ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0000", listAttrSpecific,manufacturer_spec = '01', manufacturer = self.ListOfDevices[key]['Manufacturer'] )

def ReadAttributeRequest_0001(self, key):

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0001 - Key: %s " %key, nwkid=key)
    # Power Config
    ListOfEp = getListOfEpForCluster( self, key, '0001' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0001'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Request Power Config via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0001", listAttributes )

def ReadAttributeRequest_0006_0000(self, key):
    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0006 focus on 0x0000 Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0006' )
    for EPout in ListOfEp:
        listAttributes = [0]
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0006", listAttributes)

def ReadAttributeRequest_0006_400x(self, key):
    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0006 focus on 0x4000x attributes- Key: %s " %key, nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0006' )
    for EPout in ListOfEp:
        listAttributes = []

        if 'Model' in self.ListOfDevices[key] and self.ListOfDevices[key][ 'Model' ] in ('LCT001', 'LTW013'):
            Domoticz.Debug("-----requesting Attribute 0x0006/0x4003 for PowerOn state for device : %s" %key)
            listAttributes.append ( 0x4003 )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Request OnOff 0x4000x attributes via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0006", listAttributes)

def ReadAttributeRequest_0006(self, key):
    # Cluster 0x0006

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0006 - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0006' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0006'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Request OnOff status via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0006", listAttributes)

def ReadAttributeRequest_0008_0000(self, key):
    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0008 focus on 0x0008/0000 Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0008' )
    for EPout in ListOfEp:

        listAttributes = [0]
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0008", listAttributes)

def ReadAttributeRequest_0008(self, key):
    # Cluster 0x0008 

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0008 - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0008' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0008'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Request Level Control via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0008", 0)

def ReadAttributeRequest_0300(self, key):
    # Cluster 0x0300 - Color Control

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0300 - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0300' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0300'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Request Color Temp infos via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0300", listAttributes)

def ReadAttributeRequest_000C(self, key):
    # Cluster 0x000C with attribute 0x0055 / Xiaomi Power and Metering
    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_000C - Key: %s " %key, nwkid=key)

    listAttributes = [ 0x0051,0x0055, 0x006f, 0xff05 ]
    ListOfEp = getListOfEpForCluster( self, key, '000C' )
    for EPout in ListOfEp:
        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Request 0x000c info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "000C", listAttributes)

def ReadAttributeRequest_0100(self, key):

    loggingReadAttributes( self, 'Debug', "Request shade Configuration status Read Attribute request: " + key , nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0100' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0100'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Request 0x0100 info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0100", listAttributes)

def ReadAttributeRequest_0102(self, key):

    loggingReadAttributes( self, 'Debug', "Request Windows Covering status Read Attribute request: " + key , nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0102' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0102'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

            if listAttributes:
                loggingReadAttributes( self, 'Debug', "Request 0x0102 info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0102", listAttributes)

def ReadAttributeRequest_0102_0008( self, key):
    loggingReadAttributes( self, 'Log', "Request Windows Covering status Read Attribute request: " + key , nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0102' )
    for EPout in ListOfEp:
        listAttributes = [0x0008]
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0102", listAttributes)

def ReadAttributeRequest_0201(self, key):
    # Thermostat 

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0201 - Key: %s " %key, nwkid=key)

    if 'Model' in self.ListOfDevices[key]:
        _model = True

    ListOfEp = getListOfEpForCluster( self, key, '0201' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0201'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr ) 

            if _model and str(self.ListOfDevices[key]['Model']).find('Super TR') == 0:
                loggingReadAttributes( self, 'Debug', "- req Attributes for  Super TR", nwkid=key)
                listAttributes.append(0x0403)    
                listAttributes.append(0x0405)
                listAttributes.append(0x0406)
                listAttributes.append(0x0408)   
                listAttributes.append(0x0409)  

            # Adjustement before request
            listAttrSpecific = []
            listAttrGeneric = []
            if ( 'Manufacturer' in self.ListOfDevices[key] and self.ListOfDevices[key]['Manufacturer'] == '105e' ):
                # We need to break the Read Attribute between Manufacturer specifcs one and teh generic one
                for _attr in list(listAttributes):
                    if _attr ==  0xe011:
                        listAttrSpecific.append( _attr )
                    else:
                        listAttrGeneric.append( _attr )
                del listAttributes
                listAttributes = listAttrGeneric

            if listAttributes:
                loggingReadAttributes( self, 'Debug', "Request 0201 %s/%s 0201 %s " %(key, EPout, listAttributes), nwkid=key)
                ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0201", listAttributes )

            if listAttrSpecific:
                loggingReadAttributes( self, 'Debug', "Request Thermostat info via Read Attribute request Manuf Specific %s/%s %s" %(key, EPout, str(listAttributes)), nwkid=key)
                ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0201", listAttrSpecific, manufacturer_spec = '01', manufacturer = self.ListOfDevices[key]['Manufacturer'] )

def ReadAttributeRequest_0204(self, key):

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0204 - Key: %s " %key, nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0204' )
    for EPout in ListOfEp:
        listAttributes = [0x0001]
        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Request 0204 %s/%s 0204 %s " %(key, EPout, listAttributes), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0204", listAttributes )

def ReadAttributeRequest_fc00(self, key):

    pass

def ReadAttributeRequest_0400(self, key):

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0400 - Key: %s " %key, nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0400' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0400'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Illuminance info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0400", listAttributes)

def ReadAttributeRequest_0402(self, key):

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0402 - Key: %s " %key, nwkid=key)

    _model = 'Model' in self.ListOfDevices[key]
    ListOfEp = getListOfEpForCluster( self, key, '0402' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0402'):
            if iterAttr not in listAttributes:
                if (_model and self.ListOfDevices[key]['Model'] == 'lumi.light.aqcn02'):    # Aqara Blulb
                    continue
                listAttributes.append( iterAttr )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Temperature info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0402", listAttributes)

def ReadAttributeRequest_0403(self, key):

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0403 - Key: %s " %key, nwkid=key)
    _model = 'Model' in self.ListOfDevices[key]
    ListOfEp = getListOfEpForCluster( self, key, '0403' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0403'):
            if iterAttr not in listAttributes:
                if ( _model and self.ListOfDevices[key]['Model'] == 'lumi.light.aqcn02' ):    # Aqara Blulb
                    continue
                listAttributes.append( iterAttr )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Pression Atm info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0403", listAttributes)

def ReadAttributeRequest_0405(self, key):

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0405 - Key: %s " %key, nwkid=key)
    _model = 'Model' in self.ListOfDevices[key]
    ListOfEp = getListOfEpForCluster( self, key, '0405' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0405'):
            if iterAttr not in listAttributes:
                if _model and self.ListOfDevices[key]['Model'] == 'lumi.light.aqcn02': # Aqara Blulb
                    continue
                listAttributes.append( iterAttr )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Humidity info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0405", listAttributes)

def ReadAttributeRequest_0406(self, key):

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0406 - Key: %s " %key, nwkid=key)
    _model = 'Model' in self.ListOfDevices[key]
    ListOfEp = getListOfEpForCluster( self, key, '0406' )
    for EPout in ListOfEp:
        listAttributes = []

        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0406'):
            if iterAttr not in listAttributes:
                if _model and self.ListOfDevices[key]['Model'] == 'lumi.light.aqcn02': # Aqara Blulb
                    continue
                listAttributes.append( iterAttr )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Occupancy info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0406", listAttributes)

def ReadAttributeRequest_0500(self, key):

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0500 - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0500' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0500'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0500 - %s/%s - %s" %(key, EPout, listAttributes), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0500", listAttributes)
        
def ReadAttributeRequest_0502(self, key):

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0502 - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0502' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0502'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0502 - %s/%s - %s" %(key, EPout, listAttributes), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0502", listAttributes)

def ReadAttributeRequest_0702(self, key):
    # Cluster 0x0702 Metering

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0702 - Key: %s " %key, nwkid=key)
    _manuf = 'Manufacturer' in self.ListOfDevices[key]
    ListOfEp = getListOfEpForCluster( self, key, '0702' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0702'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )
    
        # Adjustement before request
        listAttrSpecific = []
        listAttrGeneric = []
        if _manuf and self.ListOfDevices[key]['Manufacturer'] == '105e':
            # We need to break the Read Attribute between Manufacturer specifcs one and teh generic one
            for _attr in list(listAttributes):
                if _attr in ( 0xe200, 0xe201, 0xe202 ):
                    listAttrSpecific.append( _attr )
                else:
                    listAttrGeneric.append( _attr )
            del listAttributes
            listAttributes = listAttrGeneric
    
        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Request Metering info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0702", listAttributes)
    
        if listAttrSpecific:
            loggingReadAttributes( self, 'Debug', "Request Metering info  via Read Attribute request Manuf Specific %s/%s %s" %(key, EPout, str(listAttributes)), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0702", listAttrSpecific, manufacturer_spec = '01', manufacturer = self.ListOfDevices[key]['Manufacturer'] )

def ReadAttributeRequest_000f(self, key):

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_000f - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '000f' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '000f'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', " Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "000f", listAttributes)

def ReadAttributeRequest_fc01(self, key):
    # Cluster Legrand
    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_fc01 - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, 'fc01' )
    for EPout in ListOfEp:
        listAttributes = [ 0x0000]
        loggingReadAttributes( self, 'Debug', "Request Legrand info via Read Attribute request: " + key + " EPout = " + EPout + " Attributes: " + str(listAttributes), nwkid=key)
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "fc01", listAttributes)

        listAttributes = [ 0x0001 ]
        loggingReadAttributes( self, 'Debug', "Request Legrand info via Read Attribute request: " + key + " EPout = " + EPout + " Attributes: " + str(listAttributes), nwkid=key)
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "fc01", listAttributes)

def ReadAttributeRequest_fc21(self, key):
    # Cluster PFX Profalux/ Manufacturer specific

    profalux = False
    if 'Manufacturer' in self.ListOfDevices[key]:
        profalux = ( self.ListOfDevices[key]['Manufacturer'] == '1110' and self.ListOfDevices[key]['ZDeviceID'] in ('0200', '0202') )

    if profalux:
        loggingReadAttributes( self, 'Log', "Request Profalux BSO via Read Attribute request: %s" %key, nwkid=key)
        datas = "02" + key + ZIGATE_EP + '01' + 'fc21' + '00' + '01' + '1110' + '01' + '0001'
        sendZigateCmd(self, "0100", datas )


READ_ATTRIBUTES_REQUEST = {
    # Cluster : ( ReadAttribute function, Frequency )
    '0000' : ( ReadAttributeRequest_0000, 'polling0000' ),
    '0001' : ( ReadAttributeRequest_0001, 'polling0001' ),
    '0006' : ( ReadAttributeRequest_0006, 'pollingONOFF' ),
    '0008' : ( ReadAttributeRequest_0008, 'pollingLvlControl' ),
    '000C' : ( ReadAttributeRequest_000C, 'polling000C' ),
    '0100' : ( ReadAttributeRequest_0100, 'polling0100' ),
    '0102' : ( ReadAttributeRequest_0102, 'polling0102' ),
    '0201' : ( ReadAttributeRequest_0201, 'polling0201' ),
    '0204' : ( ReadAttributeRequest_0204, 'polling0204' ),
    '0300' : ( ReadAttributeRequest_0300, 'polling0300' ),
    '0400' : ( ReadAttributeRequest_0400, 'polling0400' ),
    '0402' : ( ReadAttributeRequest_0402, 'polling0402' ),
    '0403' : ( ReadAttributeRequest_0403, 'polling0403' ),
    '0405' : ( ReadAttributeRequest_0405, 'polling0405' ),
    '0406' : ( ReadAttributeRequest_0406, 'polling0406' ),
    '0500' : ( ReadAttributeRequest_0500, 'polling0500' ),
    '0502' : ( ReadAttributeRequest_0502, 'polling0502' ),
    '0702' : ( ReadAttributeRequest_0702, 'polling0702' ),
    #'000f' : ( ReadAttributeRequest_000f, 'polling000f' ),
    'fc21' : ( ReadAttributeRequest_000f, 'pollingfc21' ),
    #'fc01' : ( ReadAttributeRequest_fc01, 'pollingfc01' ),
    }