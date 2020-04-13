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

from Modules.zigateConsts import ZLL_DEVICES, MAX_LOAD_ZIGATE, CLUSTERS_LIST, MAX_READATTRIBUTES_REQ, LEGRAND_REMOTES, ADDRESS_MODE, CFG_RPT_ATTRIBUTESbyCLUSTERS, SIZE_DATA_TYPE
from Modules.tools import getClusterListforEP, mainPoweredDevice
from Modules.logging import loggingOutput
from Modules.schneider_wiser import schneider_setpoint, schneider_EHZBRTS_thermoMode

def ZigatePermitToJoin( self, permit ):

    if permit:
        # Enable Permit to join
        if self.permitTojoin['Duration'] == 255:
            # Nothing to do , it is already in permanent pairing mode.
            sendZigateCmd(self, "0049","FFFC" + '%02x' %permit + "ff")
            pass
        else:
            if permit != 255:
                loggingOutput( self, "Status", "Request Accepting new Hardware for %s seconds " %permit)
            else:
                loggingOutput( self, "Status", "Request Accepting new Hardware for ever ")

            self.permitTojoin['Starttime'] = int(time())
            if permit == 1:
                self.permitTojoin['Duration'] = 0
            else:
                self.permitTojoin['Duration'] = permit
            sendZigateCmd(self, "0049","FFFC" + '%02x' %permit + "00")
    else: 
        # Disable Permit to Join
        #if self.permitTojoin['Duration'] == 0:
        #    # Nothing to do , Pairing is already off
        #    pass
        #else:
        self.permitTojoin['Starttime'] = int(time())
        self.permitTojoin['Duration'] = 0
        sendZigateCmd(self, "0049","FFFC" + '00' + "00")
        loggingOutput( self, "Status", "Request Disabling Accepting new Hardware")

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

    loggingOutput( self, "Status", "ZigateConf setting Channel(s) to: %s" \
            %self.pluginconf.pluginConf['channel'])
    setChannel(self, str(self.pluginconf.pluginConf['channel']))
    
    if Mode == 'Controller':
        loggingOutput( self, "Status", "Set Zigate as a Coordinator")
        sendZigateCmd(self, "0023","00")

        loggingOutput( self, "Status", "Set Zigate as a TimeServer")
        setTimeServer( self)

        loggingOutput( self, "Status", "Start network")
        sendZigateCmd(self, "0024", "" )   # Start Network
    
        loggingOutput( self, 'Debug', "Request network Status", '0000')
        sendZigateCmd( self, "0014", "" ) # Request status
        sendZigateCmd( self, "0009", "" ) # Request status

def setTimeServer( self ):

    EPOCTime = datetime(2000,1,1)
    UTCTime = int((datetime.now() - EPOCTime).total_seconds())
    #loggingOutput( self, "Status", "setTimeServer - Setting UTC Time to : %s" %( UTCTime) )
    data = "%08x" %UTCTime
    sendZigateCmd(self, "0016", data  )
    #Request Time
    sendZigateCmd(self, "0017", "")


def zigateBlueLed( self, OnOff):

    if OnOff:
        loggingOutput( self, 'Log', "Switch Blue Led On")
        sendZigateCmd(self, "0018","01")
    else:
        loggingOutput( self, 'Log', "Switch Blue Led off")
        sendZigateCmd(self, "0018","00")


def sendZigateCmd(self, cmd, datas ):

    if self.ZigateComm is None:
        Domoticz.Error("Zigate Communication error.")
        return
    if self.pluginconf.pluginConf['debugzigateCmd']:
        loggingOutput( self, 'Log', "sendZigateCmd - %s %s Queue Length: %s" %(cmd, datas, len(self.ZigateComm.zigateSendingFIFO)), 'ffff')
    else:
        loggingOutput( self, 'Debug', "=====> sendZigateCmd - %s %s Queue Length: %s" %(cmd, datas, len(self.ZigateComm.zigateSendingFIFO)), 'ffff')

    if len(self.ZigateComm.zigateSendingFIFO) > 15:
        loggingOutput( self, 'Log', "WARNING - ZigateCmd: %s %18s ZigateQueue: %s" %(cmd, datas, len(self.ZigateComm.zigateSendingFIFO)))

    self.ZigateComm.sendData( cmd, datas )

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
        loggingOutput( self, 'Debug2', "----------> ------- %s/%s %s ListOfAttributes: " %(addr, EpOut, Cluster) + " ".join("0x{:04x}".format(num) for num in ListOfAttributes), nwkid=addr)
        nbpart = - (  - len(ListOfAttributes) // MAX_READATTRIBUTES_REQ) 
        for shortlist in split_list(ListOfAttributes, wanted_parts=nbpart):
            loggingOutput( self, 'Debug2', "----------> ------- Shorter: " + ", ".join("0x{:04x}".format(num) for num in shortlist), nwkid=addr)
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
        #    loggingOutput( self, 'Debug2', "normalizedReadAttrReq - cannot get Attribute self.ListOfDevices[%s]['ReadAttributes']['Ep'][%s][%s][%s]: %s"
        #             %(addr, EpOut, Cluster, Attr, self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] ), nwkid=addr)
        #    skipReadAttr = True
        if not skipReadAttr and self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] in ( '86', '8c'):    # 8c Not supported, 86 No cluster match
            loggingOutput( self, 'Debug2', "normalizedReadAttrReq - Last status self.ListOfDevices[%s]['ReadAttributes']['Ep'][%s][%s][%s]: %s"
                     %(addr, EpOut, Cluster, Attr, self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] ), nwkid=addr)
            skipReadAttr = True
        if not skipReadAttr and self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] != '00' and \
                self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] != {}:
            loggingOutput( self, 'Debug2', "normalizedReadAttrReq - Last status self.ListOfDevices[%s]['ReadAttributes']['Ep'][%s][%s][%s]: %s"
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
                            loggingOutput( self, 'Debug2', "normalizedReadAttrReq - Skip Read Attribute due to DeviceConf Nwkid: %s Cluster: %s Attribute: %s"
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
    loggingOutput( self, 'Debug2', "attributes: " +str(ListOfAttributes), nwkid=addr)
    for x in ListOfAttributes:
        Attr_ = "%04x" %(x)
        if Attr_ in self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)]:
            if skipThisAttribute(self,  addr, EpOut, Cluster, Attr_):
                continue

            loggingOutput( self, 'Debug2', "normalizedReadAttrReq: %s for %s/%s" %(Attr_, addr, self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr_]), nwkid=addr)
            self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr_] = {}
        Attr += Attr_
        lenAttr += 1

    if lenAttr == 0:
        return

    loggingOutput( self, 'Debug', "-- normalizedReadAttrReq ---- addr =" +str(addr) +" Cluster = " +str(Cluster) +" Attributes = " + ", ".join("0x{:04x}".format(num) for num in ListOfAttributes), nwkid=addr )
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

    # Attribute based on the Attributes List given by the device
    if targetAttribute is None and 'Attributes List' in self.ListOfDevices[key]:
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

    # Attribute based on default
    if targetAttribute is None:
        loggingOutput( self, 'Debug2', "retreive_ListOfAttributesByCluster: default attributes list for cluster: %s" %cluster, nwkid=key)
        if cluster in ATTRIBUTES:
            targetAttribute = ATTRIBUTES[cluster]
        else:
            Domoticz.Debug("retreive_ListOfAttributesByCluster: Missing Attribute for cluster %s" %cluster)
            targetAttribute = [ 0x0000 ]

    loggingOutput( self, 'Debug', "---- retreive_ListOfAttributesByCluster: List of Attributes for cluster %s : " %(cluster) + " ".join("0x{:04x}".format(num) for num in targetAttribute), nwkid=key)

    return targetAttribute


def ReadAttributeRequest_0000_basic(self, key):

    loggingOutput( self, 'Debug', "Ping Device - Key: %s" %(key), nwkid=key)
    EPin = "01"
    EPout = '01'
    listAttributes = []
    listAttributes.append(0x0000)        # Attribut 0x0000
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0000" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
            EPout= tmpEp 

    ReadAttributeReq( self, key, EPin, EPout, "0000", listAttributes )

def ReadAttributeRequest_0000(self, key, fullScope=True):
    # Basic Cluster
    # The Ep to be used can be challenging, as if we are in the discovery process, the list of Eps is not yet none and it could even be that the Device has only 1 Ep != 01

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0000 - Key: %s , Scope: %s" %(key, fullScope), nwkid=key)
    EPin = EPout = '01'

    # Checking if Ep list is empty, in that case we are in discovery mode and 
    # we don't really know what are the EPs we can talk to.
    if not fullScope or self.ListOfDevices[key]['Ep'] is None or self.ListOfDevices[key]['Ep'] == {}:
        loggingOutput( self, 'Debug', "--> Not full scope", nwkid=key)
        listAttributes = []

        loggingOutput( self, 'Debug', "--> Build list of Attributes", nwkid=key)
        skipModel = False

        # Do we Have Manufacturer
        if self.ListOfDevices[key]['Manufacturer'] == '':
            loggingOutput( self, 'Debug', "----> Adding: %s" %'0004', nwkid=key)
            listAttributes.append(0x0004)
        else:
            if self.ListOfDevices[key]['Manufacturer'] == 'Legrand':
                loggingOutput( self, 'Debug', "----> Adding: %s" %'f000', nwkid=key)
                if 0x4000 not in listAttributes:
                    listAttributes.append(0x4000)
                if 0xf000 not in listAttributes:
                    listAttributes.append(0xf000)
                skipModel = True
            if self.ListOfDevices[key]['Manufacturer'] == '1110':
                listAttributes.append(0x0010)
                skipModel = True

        # Do We have Model Name
        if not skipModel and ( self.ListOfDevices[key]['Model'] == {} or self.ListOfDevices[key]['Model'] == ''):
            loggingOutput( self, 'Debug', "----> Adding: %s" %'0005', nwkid=key)
            listAttributes.append(0x0005)        # Model Identifier

        if 'Model' in self.ListOfDevices[key]:
            if self.ListOfDevices[key]['Model'] != {} and self.ListOfDevices[key]['Model'] != '':
                readAttr = False
                if self.ListOfDevices[key]['Model'] in self.DeviceConf:
                    if 'ReadAttributes' in self.DeviceConf[ self.ListOfDevices[key]['Model'] ]:
                        if '0000' in  self.DeviceConf[ self.ListOfDevices[key]['Model'] ]['ReadAttributes']:
                            readAttr = True
                            for attr in self.DeviceConf[ self.ListOfDevices[key]['Model'] ]['ReadAttributes']['0000']:
                                listAttributes.append( int( attr , 16))  

                #if not readAttr and self.ListOfDevices[key]['Model'] != 'TI0001':
                #    loggingOutput( self, 'Debug', "----> Adding: %s" %'000A', nwkid=key)
                #    listAttributes.append(0x000A)        # Product Code

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
        for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0000" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                EPout= tmpEp 

                for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0000'):
                    listAttributes.append( iterAttr )
        
                if 'Model' in self.ListOfDevices[key]:
                    if self.ListOfDevices[key]['Model'] != {}:
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
                if 'Manufacturer' in self.ListOfDevices[key]:
                    if self.ListOfDevices[key]['Manufacturer'] == '105e':
                        # We need to break the Read Attribute between Manufacturer specifcs one and teh generic one
                        for _attr in list(listAttributes):
                            if _attr in ( 0xe000, 0xe001, 0xe002 ):
                                listAttrSpecific.append( _attr )
                            else:
                                listAttrGeneric.append( _attr )
                        del listAttributes
                        listAttributes = listAttrGeneric
        
                loggingOutput( self, 'Debug', "Request Basic  via Read Attribute request %s/%s %s" %(key, EPout, str(listAttributes)), nwkid=key)
                ReadAttributeReq( self, key, EPin, EPout, "0000", listAttributes )
        
                if len(listAttrSpecific) > 0:
                    loggingOutput( self, 'Debug', "Request Basic  via Read Attribute request Manuf Specific %s/%s %s" %(key, EPout, str(listAttributes)), nwkid=key)
                    ReadAttributeReq( self, key, EPin, EPout, "0000", listAttrSpecific,manufacturer_spec = '01', manufacturer = self.ListOfDevices[key]['Manufacturer'] )

def ReadAttributeRequest_0001(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0001 - Key: %s " %key, nwkid=key)
    # Power Config
    EPin = EPout = "01"

    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0001" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
            EPout=tmpEp

            listAttributes = []
            for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0001'):
                if iterAttr not in listAttributes:
                    listAttributes.append( iterAttr )

            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "Request Power Config via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, EPin, EPout, "0001", listAttributes )

def ReadAttributeRequest_0006_400x(self, key):
    loggingOutput( self, 'Debug', "ReadAttributeRequest_0006 focus on 0x4000x attributes- Key: %s " %key, nwkid=key)

    EPin = EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0006" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                EPout=tmpEp

                listAttributes = []

                if 'Model' in self.ListOfDevices[key]:
                    if self.ListOfDevices[key]['Model'] in ( 'LCT001', 'LTW013' ):
                        Domoticz.Debug("-----requesting Attribute 0x0006/0x4003 for PowerOn state for device : %s" %key)
                        listAttributes.append ( 0x4003 )
            
                if len(listAttributes) > 0:
                    loggingOutput( self, 'Debug', "Request OnOff 0x4000x attributes via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                    ReadAttributeReq( self, key, "01", EPout, "0006", listAttributes)


def ReadAttributeRequest_0006(self, key):
    # Cluster 0x0006

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0006 - Key: %s " %key, nwkid=key)

    EPin = EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0006" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
            EPout=tmpEp

            listAttributes = []
            for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0006'):
                if iterAttr not in listAttributes:
                    listAttributes.append( iterAttr )
        
            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "Request OnOff status via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, "01", EPout, "0006", listAttributes)


def ReadAttributeRequest_0008(self, key):
    # Cluster 0x0008 

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0008 - Key: %s " %key, nwkid=key)

    EPin = EPout = "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0008" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
            EPout=tmpEp

            listAttributes = []
            for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0008'):
                if iterAttr not in listAttributes:
                    listAttributes.append( iterAttr )
        
            if len(listAttributes) > 0:
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

    if len(listAttributes) > 0:
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

    if len(listAttributes) > 0:
        loggingOutput( self, 'Debug', "Request 0x000c info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
        ReadAttributeReq( self, key, "01", EPout, "000C", listAttributes)

def ReadAttributeRequest_0100(self, key):

    loggingOutput( self, 'Debug', "Request shade Configuration status Read Attribute request: " + key , nwkid=key)
    EPin = EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0100" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
            EPout=tmpEp
            listAttributes = []
            for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0100'):
                if iterAttr not in listAttributes:
                    listAttributes.append( iterAttr )

            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "Request 0x0100 info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, "01", EPout, "0100", listAttributes)


def ReadAttributeRequest_0102(self, key):

    loggingOutput( self, 'Debug', "Request Windows Covering status Read Attribute request: " + key , nwkid=key)
    EPin = EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0102" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
            EPout=tmpEp
            listAttributes = []
            for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0102'):
                if iterAttr not in listAttributes:
                    listAttributes.append( iterAttr )
        
            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "Request 0x0102 info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, "01", EPout, "0102", listAttributes)

def ReadAttributeRequest_0201(self, key):
    # Thermostat 

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0201 - Key: %s " %key, nwkid=key)
    EPin = EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
            EPout=tmpEp

            listAttributes = []

            for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0201'):
                if iterAttr not in listAttributes:
                    listAttributes.append( iterAttr )
        
            if 'Model' in self.ListOfDevices[key]:
                _model = True

            if _model and str(self.ListOfDevices[key]['Model']).find('Super TR') == 0:
                loggingOutput( self, 'Debug', "- req Attributes for  Super TR", nwkid=key)
                listAttributes.append(0x0403)    
                listAttributes.append(0x0405)
                listAttributes.append(0x0406)
                listAttributes.append(0x0408)   
                listAttributes.append(0x0409)  

            # Adjustement before request
            listAttrSpecific = []
            listAttrGeneric = []
            if 'Manufacturer' in self.ListOfDevices[key]:
                if self.ListOfDevices[key]['Manufacturer'] == '105e':
                    # We need to break the Read Attribute between Manufacturer specifcs one and teh generic one
                    for _attr in list(listAttributes):
                        if _attr ==  0xe011:
                            listAttrSpecific.append( _attr )
                        else:
                            listAttrGeneric.append( _attr )
                    del listAttributes
                    listAttributes = listAttrGeneric
        
            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "Request 0201 %s/%s-%s 0201 %s " %(key, EPin, EPout, listAttributes), nwkid=key)
                ReadAttributeReq( self, key, EPin, EPout, "0201", listAttributes )

            if len(listAttrSpecific) > 0:
                loggingOutput( self, 'Debug', "Request Thermostat info via Read Attribute request Manuf Specific %s/%s %s" %(key, EPout, str(listAttributes)), nwkid=key)
                ReadAttributeReq( self, key, EPin, EPout, "0201", listAttrSpecific, manufacturer_spec = '01', manufacturer = self.ListOfDevices[key]['Manufacturer'] )



def ReadAttributeRequest_0204(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0204 - Key: %s " %key, nwkid=key)
    EPin = EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0204" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
            EPout=tmpEp

            listAttributes = []
            listAttributes.append(0x0001) # Read KeypadLockout
        
            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "Request 0204 %s/%s-%s 0204 %s " %(key, EPin, EPout, listAttributes), nwkid=key)
                ReadAttributeReq( self, key, EPin, EPout, "0204", listAttributes )



def ReadAttributeRequest_fc00(self, key):

    EPin = EPout= "01"

    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "fc00" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
            EPout=tmpEp
            listAttributes = []

            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "Request 0xfc00 info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, "01", EPout, "fc00", listAttributes)

def ReadAttributeRequest_0400(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0400 - Key: %s " %key, nwkid=key)

    EPin = EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0400" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
            EPout=tmpEp
            listAttributes = []
            for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0400'):
                if iterAttr not in listAttributes:
                    listAttributes.append( iterAttr )
        
            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "Illuminance info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, EPin, EPout, "0400", listAttributes)

def ReadAttributeRequest_0402(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0402 - Key: %s " %key, nwkid=key)

    EPin = EPout= "01"
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
        
            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "Temperature info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, EPin, EPout, "0402", listAttributes)

def ReadAttributeRequest_0403(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0403 - Key: %s " %key, nwkid=key)

    EPin = EPout= "01"
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
        
            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "Pression Atm info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, EPin, EPout, "0403", listAttributes)

def ReadAttributeRequest_0405(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0405 - Key: %s " %key, nwkid=key)

    EPin = EPout= "01"
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
        
            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "Humidity info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, EPin, EPout, "0405", listAttributes)

def ReadAttributeRequest_0406(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0406 - Key: %s " %key, nwkid=key)
    EPin = EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0406" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
            EPout=tmpEp
            listAttributes = []

            for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0406'):
                if iterAttr not in listAttributes:
                    if 'Model' in self.ListOfDevices[key]:
                        if self.ListOfDevices[key]['Model'] == 'lumi.light.aqcn02': # Aqara Blulb
                            continue
                    listAttributes.append( iterAttr )
        
            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "Occupancy info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, EPin, EPout, "0406", listAttributes)

def ReadAttributeRequest_0500(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0500 - Key: %s " %key, nwkid=key)

    EPin = EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0500" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
            EPout=tmpEp
            listAttributes = []
            for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0500'):
                if iterAttr not in listAttributes:
                    listAttributes.append( iterAttr )
        
            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "ReadAttributeRequest_0500 - %s/%s - %s" %(key, EPout, listAttributes), nwkid=key)
                ReadAttributeReq( self, key, "01", EPout, "0500", listAttributes)
        
def ReadAttributeRequest_0502(self, key):

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0502 - Key: %s " %key, nwkid=key)

    EPin = EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0502" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
            EPout=tmpEp
            listAttributes = []
            for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0502'):
                if iterAttr not in listAttributes:
                    listAttributes.append( iterAttr )
        
            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "ReadAttributeRequest_0502 - %s/%s - %s" %(key, EPout, listAttributes), nwkid=key)
                ReadAttributeReq( self, key, "01", EPout, "0502", listAttributes)


def ReadAttributeRequest_0702(self, key):
    # Cluster 0x0702 Metering

    loggingOutput( self, 'Debug', "ReadAttributeRequest_0702 - Key: %s " %key, nwkid=key)

    EPin = EPout = "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0702" in self.ListOfDevices[key]['Ep'][tmpEp]: 
            EPout=tmpEp

            listAttributes = []
            for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0702'):
                if iterAttr not in listAttributes:
                    listAttributes.append( iterAttr )
        
        
            # Adjustement before request
            listAttrSpecific = []
            listAttrGeneric = []
            if 'Manufacturer' in self.ListOfDevices[key]:
                if self.ListOfDevices[key]['Manufacturer'] == '105e':
                    # We need to break the Read Attribute between Manufacturer specifcs one and teh generic one
                    for _attr in list(listAttributes):
                        if _attr in ( 0xe200, 0xe201, 0xe202 ):
                            listAttrSpecific.append( _attr )
                        else:
                            listAttrGeneric.append( _attr )
                    del listAttributes
                    listAttributes = listAttrGeneric
        
            if len(listAttributes) > 0:
                loggingOutput( self, 'Debug', "Request Metering info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, EPin, EPout, "0702", listAttributes)
        
            if len(listAttrSpecific) > 0:
                loggingOutput( self, 'Debug', "Request Metering info  via Read Attribute request Manuf Specific %s/%s %s" %(key, EPout, str(listAttributes)), nwkid=key)
                ReadAttributeReq( self, key, EPin, EPout, "0702", listAttrSpecific, manufacturer_spec = '01', manufacturer = self.ListOfDevices[key]['Manufacturer'] )

def ReadAttributeRequest_000f(self, key):

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

    if len(listAttributes) == 0:
        return

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

def ReadAttributeRequest_fc21(self, key):

    # Cluster PFX Profalux
    loggingOutput( self, 'Log', "ReadAttributeRequest_fc21 - Key: %s " %key, nwkid=key)

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "fc21" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                EPout=tmpEp
    listAttributes = []
    listAttributes.append( 0x0001 )
    loggingOutput( self, 'Log', "Request Profalux BSO via Read Attribute request: " + key + " EPout = " + EPout + " Attributes: " + str(listAttributes), nwkid=key)
    ReadAttributeReq( self, key, EPin, EPout, "fc21", listAttributes)

def write_attribute( self, key, EPin, EPout, clusterID, manuf_id, manuf_spec, attribute, data_type, data):

    addr_mode = "02" # Short address
    direction = "00"
    if data_type == '42': # String
        # In case of Data Type 0x42 ( String ), we have to add the length of string before the string.
        data = '%02x' %(len(data)//2) + data

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

    # OSRAM/LEDVANCE
    # 0xfc0f --> Command 0x01
    # 0xfc01 --> Command 0x01

    # Tested on Ikea Bulb without any results !
    POWERON_MODE = ( 0x00, # Off
            0x01, # On
            0xfe # Previous state
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
            # Very bad Hack, but at that stage, there is no other information we can Use. PROFALUX
            if self.ListOfDevices[nwkid]['ProfileID'] == '0104':
                if self.ListOfDevices[nwkid]['ZDeviceID'] == '0201': # Remote
                    # Do not bind Remote Command
                    loggingOutput( self, 'Log',"----> Do not bind cluster %s for Profalux Remote command %s/%s" %(cluster, nwkid, ep), nwkid)
                    return

            if 'Model' in self.ListOfDevices[nwkid]:
                if self.ListOfDevices[nwkid]['Model'] != {}:
                    if self.ListOfDevices[nwkid]['Model'] in self.DeviceConf:
                        if 'ClusterToBind' in self.DeviceConf[ self.ListOfDevices[nwkid]['Model'] ]:
                            if cluster not in self.DeviceConf[ self.ListOfDevices[nwkid]['Model'] ]['ClusterToBind']:
                                loggingOutput( self, 'Debug',"----> Do not bind cluster %s due to Certified Conf for %s/%s" %(cluster, nwkid, ep), nwkid)
                                return

                    if self.ListOfDevices[nwkid]['Model'] == 'SML001' and ep != '02':
                        # only on Ep 02
                        loggingOutput( self, 'Debug',"Do not Bind SML001 to Zigate Ep %s Cluster %s" %(ep, cluster), nwkid)
                        return

                    if self.ListOfDevices[nwkid]['Model'] == 'lumi.remote.b686opcn01' and ep != '01':
                        # We bind only on EP 01
                        loggingOutput( self, 'Log',"Do not Bind lumi.remote.b686opcn01 to Zigate Ep %s Cluster %s" %(ep, cluster), nwkid)
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
        self.ListOfDevices[nwkid]['Bind'][ep][cluster]['Target'] = '0000' # Zigate
        self.ListOfDevices[nwkid]['Bind'][ep][cluster]['Stamp'] = int(time())
        self.ListOfDevices[nwkid]['Bind'][ep][cluster]['Phase'] = 'requested'
        self.ListOfDevices[nwkid]['Bind'][ep][cluster]['Status'] = ''

        loggingOutput( self, 'Debug', "bindDevice - ieee: %s, ep: %s, cluster: %s, Zigate_ieee: %s, Zigate_ep: %s" %(ieee,ep,cluster,destaddr,destep) , nwkid=nwkid)
        datas =  str(ieee)+str(ep)+str(cluster)+str(mode)+str(destaddr)+str(destep) 
        sendZigateCmd(self, "0030", datas )

    return

def webBind( self, sourceIeee, sourceEp, destIeee, destEp, Cluster):

    if sourceIeee not in self.IEEE2NWK:
        Domoticz.Error("---> unknown sourceIeee: %s" %sourceIeee)
        return

    if destIeee not in self.IEEE2NWK:
        Domoticz.Error("---> unknown destIeee: %s" %destIeee)
        return

    sourceNwkid = self.IEEE2NWK[sourceIeee]
    destNwkid = self.IEEE2NWK[destIeee]


    if sourceEp not in self.ListOfDevices[sourceNwkid]['Ep']:
        Domoticz.Error("---> unknown sourceEp: %s for sourceNwkid: %s" %(sourceEp, sourceNwkid))
        return
    loggingOutput( self, 'Debug', "Binding Device %s/%s with Device target %s/%s on Cluster: %s" %(sourceIeee, sourceEp, destIeee, destEp, Cluster), sourceNwkid)
    if Cluster not in self.ListOfDevices[sourceNwkid]['Ep'][sourceEp]:
        Domoticz.Error("---> Cluster %s not find in %s --> %s" %( Cluster, sourceNwkid, self.ListOfDevices[sourceNwkid]['Ep'][sourceEp].keys()))
        return
    loggingOutput( self, 'Debug', "Binding Device %s/%s with Device target %s/%s on Cluster: %s" %(sourceIeee, sourceEp, destIeee, destEp, Cluster), destNwkid)

    if destEp not in self.ListOfDevices[destNwkid]['Ep']:
        Domoticz.Error("---> unknown destEp: %s for destNwkid: %s" %(destEp, destNwkid))
        return

    mode = "03"     # IEEE
    datas =  str(sourceIeee)+str(sourceEp)+str(Cluster)+str(mode)+str(destIeee)+str(destEp)
    sendZigateCmd(self, "0030", datas )
    loggingOutput( self, 'Debug', "---> %s %s" %("0030", datas), sourceNwkid)

    if 'WebBind' not in self.ListOfDevices[sourceNwkid]:
        self.ListOfDevices[sourceNwkid]['WebBind'] = {}
    if sourceEp not in self.ListOfDevices[sourceNwkid]['WebBind']:
        self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp] = {}
    if Cluster not in self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp]:
        self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster] = {}
    self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster] = {}
    self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster]['Target'] = destNwkid
    self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster]['TargetIEEE'] = destIeee
    self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster]['TargetEp'] = destEp
    self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster]['Stamp'] = int(time())

def webUnBind( self, sourceIeee, sourceEp, destIeee, destEp, Cluster):

    if sourceIeee not in self.IEEE2NWK:
        Domoticz.Error("---> unknown sourceIeee: %s" %sourceIeee)
        return

    if destIeee not in self.IEEE2NWK:
        Domoticz.Error("---> unknown destIeee: %s" %destIeee)
        return

    sourceNwkid = self.IEEE2NWK[sourceIeee]
    destNwkid = self.IEEE2NWK[destIeee]

    if sourceEp not in self.ListOfDevices[sourceNwkid]['Ep']:
        Domoticz.Error("---> unknown sourceEp: %s for sourceNwkid: %s" %(sourceEp, sourceNwkid))
        return
    loggingOutput( self, 'Debug', "UnBinding Device %s/%s with Device target %s/%s on Cluster: %s" %(sourceIeee, sourceEp, destIeee, destEp, Cluster), sourceNwkid)
    if Cluster not in self.ListOfDevices[sourceNwkid]['Ep'][sourceEp]:
        Domoticz.Error("---> Cluster %s not find in %s --> %s" %( Cluster, sourceNwkid, self.ListOfDevices[sourceNwkid]['Ep'][sourceEp].keys()))
        return
    loggingOutput( self, 'Debug', "UnBinding Device %s/%s with Device target %s/%s on Cluster: %s" %(sourceIeee, sourceEp, destIeee, destEp, Cluster), destNwkid)

    if destEp not in self.ListOfDevices[destNwkid]['Ep']:
        Domoticz.Error("---> unknown destEp: %s for destNwkid: %s" %(destEp, destNwkid))
        return

    mode = "03"     # IEEE
    datas =  str(sourceIeee)+str(sourceEp)+str(Cluster)+str(mode)+str(destIeee)+str(destEp)
    sendZigateCmd(self, "0031", datas )
    loggingOutput( self, 'Debug', "---> %s %s" %("0031", datas), sourceNwkid)

    if 'WebBind' in self.ListOfDevices[sourceNwkid]:
       if sourceEp in self.ListOfDevices[sourceNwkid]['WebBind']:
            if Cluster in self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp]:
                del self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp][Cluster]
                if len(self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp]) == 0:
                    del self.ListOfDevices[sourceNwkid]['WebBind'][sourceEp]
                if len(self.ListOfDevices[sourceNwkid]['WebBind']) == 0:
                    del self.ListOfDevices[sourceNwkid]['WebBind']

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

    # User Configuration if exists
    if 'Model' in self.ListOfDevices[NWKID]:
        if self.ListOfDevices[NWKID]['Model'] != {}:
            if self.ListOfDevices[NWKID]['Model'] in self.DeviceConf:
                if 'ClusterToBind' in self.DeviceConf[ self.ListOfDevices[NWKID]['Model'] ]:
                    cluster_to_bind = self.DeviceConf[ self.ListOfDevices[NWKID]['Model'] ]['ClusterToBind']

    # If Bind information, then remove it
    if 'Bind' in self.ListOfDevices[NWKID]:
        del self.ListOfDevices[NWKID]['Bind']

    # If allow Unbind before Bind, then Unbind
    if self.pluginconf.pluginConf['doUnbindBind']:
        for iterBindCluster in cluster_to_bind:      
            for iterEp in self.ListOfDevices[NWKID]['Ep']:
                if iterBindCluster in self.ListOfDevices[NWKID]['Ep'][iterEp]:
                    loggingOutput( self, 'Debug', 'Request an Unbind for %s/%s on Cluster %s' %(NWKID, iterEp, iterBindCluster), nwkid=NWKID)
                    unbindDevice( self, self.ListOfDevices[NWKID]['IEEE'], iterEp, iterBindCluster)

    # Bind
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

    loggingOutput( self, "Status", "initiate Touch Link")
    sendZigateCmd(self, "00D0", '' )

def factoryresetTouchLink( self):

    loggingOutput( self, "Status", "Factory Reset Touch Link Over The Air")
    sendZigateCmd(self, "00D2", '' )


def identifySend( self, nwkid, ep, duration=0):

    datas = "02" + "%s"%(nwkid) + "01" + ep + "%04x"%(duration) 
    loggingOutput( self, 'Debug', "identifySend - send an Identify Message to: %s for %04x seconds" %( nwkid, duration), nwkid=nwkid)
    loggingOutput( self, 'Debug', "identifySend - data sent >%s< " %(datas) , nwkid=nwkid)
    sendZigateCmd(self, "0070", datas )

def maskChannel( channel ):


    # https://github.com/fairecasoimeme/ZiGate/blob/c5a6b5569f6651f72daec9dabbc0d8688e797426/Module%20Radio/Firmware/src/ZiGate/Source/ZigbeeNodeControlBridge/ZigbeeNodeControlBridgeCoordinator.zpscfg#L513https
    #  <ChannelMask Channel11="true" Channel12="false" Channel13="false" Channel14="false" Channel15="true" 
    #  Channel16="false" Channel17="false" Channel18="false" Channel19="true" Channel20="true" Channel21="false" 
    #  Channel22="false" Channel23="false" Channel24="false" Channel25="true" Channel26="true"/>

    CHANNELS = { 0: 0x00000000, # Scan for all channels
            11: 0x00000800,
            #12: 0x00001000, # Not Zigate
            #13: 0x00002000, # Not Zigate
            #14: 0x00004000, # Not Zigate
            15: 0x00008000,
            #16: 0x00010000, # Not Zigate
            #17: 0x00020000, # Not Zigate
            #18: 0x00040000, # Not Zigate
            19: 0x00080000,
            20: 0x00100000,
            #21: 0x00200000, # Not Zigate
            #22: 0x00400000, # Not Zigate
            #23: 0x00800000, # Not Zigate
            #24: 0x01000000, # Not Zigate
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
            if isinstance( channel, int):
                if channel in CHANNELS:
                    mask = CHANNELS( channel )
                else:
                    Domoticz.Error("Requested channel not supported by Zigate: %s" %channel)
            else:
                if int(channel) in CHANNELS:
                    mask = CHANNELS[int(channel)]
                else:
                    Domoticz.Error("Requested channel not supported by Zigate: %s" %channel)
    return mask


def setChannel( self, channel):
    '''
    The channel list
    is a bitmap, where each bit describes a channel (for example bit 12
    corresponds to channel 12). Any combination of channels can be included.
    ZigBee supports channels 11-26.
    '''
    mask = maskChannel( channel )
    loggingOutput( self, "Status", "setChannel - Channel set to : %08.x " %(mask))

    sendZigateCmd(self, "0021", "%08.x" %(mask))
    return


def channelChangeInitiate( self, channel ):

    loggingOutput( self, "Status", "Change channel from [%s] to [%s] with nwkUpdateReq" %(self.currentChannel, channel))
    NwkMgtUpdReq( self, channel, 'change')

def channelChangeContinue( self ):

    loggingOutput( self, "Status", "Restart network")
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

    loggingOutput( self, 'Log', "leaveMgtReJoin - sAddr: %s , ieee: %s, [%s/%s]" %( saddr, ieee,  self.pluginconf.pluginConf['allowAutoPairing'], rejoin))
    if not self.pluginconf.pluginConf['allowAutoPairing']:
        loggingOutput( self, 'Log', "leaveMgtReJoin - no action taken as 'allowAutoPairing' is %s" %self.pluginconf.pluginConf['allowAutoPairing'])
        return

    if rejoin:
        loggingOutput( self, "Status", "Switching Zigate in pairing mode to allow %s (%s) coming back" %(saddr, ieee))

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
        loggingOutput( self, "Status", "Request a rejoin of (%s/%s)" %(saddr, ieee))
        sendZigateCmd(self, "0047", datas )

def leaveRequest( self, ShortAddr=None, IEEE= None, RemoveChild=0x00, Rejoin=0x00 ):

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
    #loggingOutput( self, "Status", "Sending a leaveRequest - %s %s" %( '0047', datas))
    loggingOutput( self, 'Log', "---------> Sending a leaveRequest - NwkId: %s, IEEE: %s, RemoveChild: %s, Rejoin: %s" %( ShortAddr, IEEE, RemoveChild, Rejoin))
    loggingOutput( self, 'Log', "---------> Sending a leaveRequest - payload %s" %( datas))
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
        if self.ListOfDevices[nwkid]['MacCapa'] in ( '8e', '84' ):
            router = True
    if 'PowerSource' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['PowerSource'] in ( 'Main'):
            router = True

        loggingOutput( self, "Status", "Remove from Zigate Device = " + " IEEE = " +str(IEEE) )

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

    loggingOutput( self, 'Debug', "thermostat_Setpoint - for %s with value %s" %(key,setpoint), nwkid=key)

    if 'Model' in self.ListOfDevices[key]:
        if self.ListOfDevices[key]['Model'] != {}:
            if self.ListOfDevices[key]['Model'] == 'SPZB0001':
                loggingOutput( self, 'Debug', "thermostat_Setpoint - calling SPZB for %s with value %s" %(key,setpoint), nwkid=key)
                thermostat_Setpoint_SPZB( self, key, setpoint)

            elif self.ListOfDevices[key]['Model'] in ( 'EH-ZB-RTS', 'EH-ZB-HACT', 'EH-ZB-VACT' ):
                loggingOutput( self, 'Debug', "thermostat_Setpoint - calling Schneider for %s with value %s" %(key,setpoint), nwkid=key)
                schneider_setpoint( self, key, setpoint)
                return

    loggingOutput( self, 'Debug', "thermostat_Setpoint - standard for %s with value %s" %(key,setpoint), nwkid=key)
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
        loggingOutput( self, 'Log', "thermostat_eurotronic_hostflag - unknown action %s" %action)
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
        Domoticz.Error("thermostat_Mode - unknown system mode: %s" %mode)
        return

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

    #SECURITY = 0x33
    SECURITY = 0x30
    RADIUS = 0x00

    addr_mode ='%02X' % ADDRESS_MODE['short']
    security = '%02X' %SECURITY
    radius = '%02X' %RADIUS

    len_payload = (len(payload)) // 2
    len_payload = '%02x' %len_payload

    loggingOutput( self, 'Debug', "raw_APS_request - Addr: %s Ep: %s Cluster: %s ProfileId: %s Payload: %s" %(targetaddr, dest_ep, cluster, profileId, payload))

    sendZigateCmd(self, "0530", addr_mode + targetaddr + zigate_ep + dest_ep + cluster + profileId + security + radius + len_payload + payload)


## Scene

def scene_membership_request( self, nwkid, ep, groupid='0000'):

    datas = '02' + nwkid + '01' + ep +  groupid
    sendZigateCmd(self, "00A6", datas )

def xiaomi_leave( self, NWKID):

    if self.permitTojoin['Duration'] != 255:
        loggingOutput( self, 'Log', "------> switch zigate in pairing mode")
        ZigatePermitToJoin(self, ( 1 * 60 ))

    # sending a Leave Request to device, so the device will send a leave
    loggingOutput( self, 'Log', "------> Sending a leave to Xiaomi battery devive: %s" %(NWKID))
    leaveRequest( self, IEEE= self.ListOfDevices[NWKID]['IEEE'], Rejoin=True )


