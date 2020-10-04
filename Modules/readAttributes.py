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
from Modules.basicOutputs import send_zigatecmd_zcl_ack, send_zigatecmd_zcl_noack, identifySend, read_attribute
from Modules.logging import loggingReadAttributes 
from Modules.tools import getListOfEpForCluster, check_datastruct, is_time_to_perform_work, set_isqn_datastruct, \
              set_status_datastruct, set_timestamp_datastruct, is_attr_unvalid_datastruct, reset_attr_datastruct, \
              ackDisableOrEnable


def ReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes , manufacturer_spec = '00', manufacturer = '0000', ackIsDisabled = True, checkTime=True):

    def split_list(l, wanted_parts=1):
        """
        Split the list of attrributes in wanted part
        """
        Domoticz.Log("Breaking %s ListOfAttribute into chunks of %s ==> %s" %( l, wanted_parts, str([  l[x: x+wanted_parts] for x in range(0, len(l), wanted_parts) ])))
        return [  l[x: x+wanted_parts] for x in range(0, len(l), wanted_parts) ]

    # That one is put in comment as it has some bad behaviour. It prevents doing 2 commands in the same minutes.
    #if checkTime:
    #    if not is_time_to_perform_work(self, 'ReadAttributes', addr, EpOut, Cluster, int(time()), 60 ):
    #        Domoticz.Log("Protection Not more than a Read Attribute per minute %s/%s Cluster: %s Attribute: %s"
    #            %( addr, EpOut, Cluster, str(ListOfAttributes)))
    #        # Do not perform more than once every minute !
    #        return

    # Check if we are in pairing mode and Read Attribute must be broken down in 1 attribute max, otherwise use the default value
    maxReadAttributesByRequest = MAX_READATTRIBUTES_REQ
    if 'PairingInProgress' in self.ListOfDevices[ addr ] and self.ListOfDevices[ addr ]['PairingInProgress']:
        maxReadAttributesByRequest = 1

    if not isinstance(ListOfAttributes, list) or len (ListOfAttributes) <= maxReadAttributesByRequest:
        normalizedReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes , manufacturer_spec, manufacturer, ackIsDisabled )
    else:
        loggingReadAttributes( self, 'Debug2', "----------> ------- %s/%s %s ListOfAttributes: " %(addr, EpOut, Cluster) + " ".join("0x{:04x}".format(num) for num in ListOfAttributes), nwkid=addr)
        for shortlist in split_list(ListOfAttributes, wanted_parts = maxReadAttributesByRequest):
            loggingReadAttributes( self, 'Debug2', "----------> ------- Shorter: " + ", ".join("0x{:04x}".format(num) for num in shortlist), nwkid=addr)
            normalizedReadAttributeReq( self, addr, EpIn, EpOut, Cluster , shortlist , manufacturer_spec , manufacturer , ackIsDisabled)

def normalizedReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes , manufacturer_spec, manufacturer, ackIsDisabled ):

    def skipThisAttribute( self, addr, EpOut, Cluster, Attr):

        if is_attr_unvalid_datastruct( self, 'ReadAttributes', addr, EpOut, Cluster , Attr ):
            return True

        if 'Model' in self.ListOfDevices[addr]:
            return False

        if self.ListOfDevices[addr]['Model'] not in self.DeviceConf:
            return False

        model = self.ListOfDevices[addr]['Model']
        if 'ReadAttributes' not in self.DeviceConf[ model ]:
            return False

        if Cluster not in self.DeviceConf[ model ]['ReadAttributes']:
            return False

        if Attr in self.DeviceConf[ model ]['ReadAttributes'][Cluster]:
            Domoticz.Log("Skip Attribute 6 %s/%s %s %s" %(addr, EpOut, Cluster , Attr))
            loggingReadAttributes( self, 'Debug2', "normalizedReadAttrReq - Skip Read Attribute due to DeviceConf Nwkid: %s Cluster: %s Attribute: %s"
                    %(addr, Cluster, Attr ), nwkid=addr)
            return False

        return True


    # Start method
    #Domoticz.Log("--> normalizedReadAttributeReq --> manufacturer_spec = '%s', manufacturer = '%s'" %(manufacturer_spec, manufacturer))
    if 'Health' in self.ListOfDevices[addr]:
        if self.ListOfDevices[addr]['Health'] == 'Not Reachable':
            return
    

    direction = '00'
    check_datastruct( self, 'ReadAttributes', addr, EpOut, Cluster )

    if not isinstance(ListOfAttributes, list):
        # We received only 1 attribute
        _tmpAttr = ListOfAttributes
        ListOfAttributes = []
        ListOfAttributes.append( _tmpAttr)

    
    lenAttr = 0
    weight = int ((lenAttr ) / 2) + 1
    Attr =''
    attributeList = []
    loggingReadAttributes( self, 'Debug2', "attributes: " +str(ListOfAttributes), nwkid=addr)
    for x in ListOfAttributes:
        Attr_ = "%04x" %(x)
        if skipThisAttribute(self,  addr, EpOut, Cluster, Attr_):
            #Domoticz.Log("Skiping attribute %s/%s %s %s" %(addr, EpOut, Cluster, Attr_))
            continue

        reset_attr_datastruct( self, 'ReadAttributes', addr, EpOut, Cluster , Attr_ )
        Attr += Attr_
        lenAttr += 1
        attributeList.append( Attr_ )
        
    if lenAttr == 0:
        return

    loggingReadAttributes( self, 
        'Debug', 
        "-- normalizedReadAttrReq ---- addr =" +str(addr) +" Cluster = " +str(Cluster) +" Attributes = " + ", ".join("0x{:04x}".format(num) for num in ListOfAttributes), nwkid=addr )
    i_sqn = read_attribute( self, addr ,EpIn , EpOut ,Cluster ,direction , manufacturer_spec , manufacturer , lenAttr, Attr, ackIsDisabled=ackIsDisabled )

    for x in attributeList:
        set_isqn_datastruct(self, 'ReadAttributes', addr, EpOut, Cluster, x, i_sqn )
    set_timestamp_datastruct(self, 'ReadAttributes', addr, EpOut, Cluster, int(time()) ) 

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
            '0020': [ 0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006 ],
            '0100': [ 0x0000, 0x0001, 0x0002, 0x0010, 0x0011],
            '0101': [ 0x0000, 0x0001, 0x0002, 0x0010, 0x0011, 0x0012, 0x0013, 0x0014, 0x0015, 0x0016, 0x0017, 0x0018, 0x0019, 0x0020, 0x0023, 0x0025, 0x0026, 0x0027, 0x0028, 0x0030, 0x0032, 0x0034, 0x0040, 0x0042, 0x0043, 0xfffd],
            '0102': [ 0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0007, 0x0008, 0x0009, 0x000A, 0x000B, 0x0010, 0x0011, 0x0014, 0x0017, 0xfffd],
            '0201': [ 0x0000, 0x0008, 0x0010, 0x0012,  0x0014, 0x0015, 0x0016, 0x001B, 0x001C, 0x001F],
            '0204': [ 0x0000, 0x0001, 0x0002 ],
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
            '0b05': [ 0x0000 ],
            'fc01': [ 0x0000, 0x0001, 0x0002 ],# Legrand Cluster
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

def ping_device_with_read_attribute(self, key):
    # In order to ping a device, we simply send a Read Attribute on Cluster 0x0000 and looking for Attribute 0x0000
    # This Cluster/Attribute is mandatory for each devices.
    PING_CLUSTER = '0000'
    PING_CLUSTER_ATTRIBUTE = '0000'

    loggingReadAttributes( self, 'Debug', "Ping Device Physical device - Key: %s" %(key), nwkid=key)

    if 'Model' in self.ListOfDevices[key] and self.ListOfDevices[key][
        'Model'
    ] in ('GL-B-007Z',):
        PING_CLUSTER = '0006'
        PING_CLUSTER_ATTRIBUTE = '0000'

    ListOfEp = getListOfEpForCluster( self, key, PING_CLUSTER )
    for EPout in ListOfEp:
        check_datastruct( self, 'ReadAttributes', key, EPout, '0000' )
        #       send_zigatecmd_zcl_ack( self, key, '0100', EpIn      + EpOut + Cluster      + dir  + ManufSpe + manufacturer + '%02x' %lenAttr + Attr )
        i_sqn = send_zigatecmd_zcl_ack( self, key, '0100', ZIGATE_EP + EPout + PING_CLUSTER + '00' + '00' + '0000' + "%02x" %(0x01) + PING_CLUSTER_ATTRIBUTE )
        set_isqn_datastruct(self, 'ReadAttributes', key, EPout, PING_CLUSTER, PING_CLUSTER_ATTRIBUTE, i_sqn )







def ReadAttributeRequest_0000(self, key, fullScope=True):
    # Basic Cluster
    # The Ep to be used can be challenging, as if we are in the discovery process, the list of Eps is not yet none and it could even be that the Device has only 1 Ep != 01

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0000 - Key: %s , Scope: %s" %(key, fullScope), nwkid=key)
    EPout = '01'

    disableAck = True
    if 'PowerSource' in self.ListOfDevices[ key ] and self.ListOfDevices[ key ]['PowerSource'] == 'Battery':
        disableAck = False

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
            loggingReadAttributes( self, 'Log', "Request Basic  via Read Attribute request: " + key + " EPout = " + "01, 02, 03, 06, 09" , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, "01", "0000", listAttributes, ackIsDisabled = False , checkTime = False)
            ReadAttributeReq( self, key, ZIGATE_EP, "0b", "0000", listAttributes, ackIsDisabled = False , checkTime = False) # Schneider
            ReadAttributeReq( self, key, ZIGATE_EP, "02", "0000", listAttributes, ackIsDisabled = False , checkTime = False)
            ReadAttributeReq( self, key, ZIGATE_EP, "03", "0000", listAttributes, ackIsDisabled = False , checkTime = False)
            ReadAttributeReq( self, key, ZIGATE_EP, "06", "0000", listAttributes, ackIsDisabled = False , checkTime = False) # Livolo
            ReadAttributeReq( self, key, ZIGATE_EP, "09", "0000", listAttributes, ackIsDisabled = False , checkTime = False)
        else:
            for epout in self.ListOfDevices[key]['Ep']:
                loggingReadAttributes( self, 'Log', "Request Basic  via Read Attribute request: " + key + " EPout = " + epout + " Attributes: " + str(listAttributes), nwkid=key)
                if self.ListOfDevices[ key ].get('Power', 'Battery') == 'Main':
                    ReadAttributeReq( self, key, ZIGATE_EP, epout, "0000", listAttributes, ackIsDisabled = False , checkTime = False)
                else:
                    ReadAttributeReq( self, key, ZIGATE_EP, epout, "0000", listAttributes, ackIsDisabled = False , checkTime = False)

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
            manufacturer_code = '0000'

            if ( 'Manufacturer' in self.ListOfDevices[key] and self.ListOfDevices[key]['Manufacturer'] == '105e' ) or \
                ( 'Manufacturer Name' in self.ListOfDevices[key] and self.ListOfDevices[key]['Manufacturer Name'] == 'Schneider Electric' ) or \
                ( 'Model' in self.ListOfDevices[key] and self.ListOfDevices[key]['Model'] in ( 'EH-ZB-VAC') ):
                # We need to break the Read Attribute between Manufacturer specifcs one and teh generic one
                Domoticz.Log("Specific Manufacturer !!!!")
                manufacturer_code = '105e'
                for _attr in list(listAttributes):
                    if _attr in ( 0xe000, 0xe001, 0xe002 ):
                        listAttrSpecific.append( _attr )
                    else:
                        listAttrGeneric.append( _attr )
                del listAttributes
                listAttributes = listAttrGeneric
            #Domoticz.Log("List Attributes: " + " ".join("0x{:04x}".format(num) for num in listAttributes) )
            
            if listAttributes:
                #loggingReadAttributes( self, 'Debug', "Request Basic  via Read Attribute request %s/%s %s" %(key, EPout, str(listAttributes)), nwkid=key)
                loggingReadAttributes( self, 'Debug', "Request Basic  via Read Attribute request %s/%s " %(key, EPout) + " ".join("0x{:04x}".format(num) for num in listAttributes), nwkid=key)
                ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0000", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key), checkTime = False )

            #Domoticz.Log("List Attributes Manuf Spec: " + " ".join("0x{:04x}".format(num) for num in listAttrSpecific) )
            if listAttrSpecific:
                #loggingReadAttributes( self, 'Debug', "Request Basic  via Read Attribute request Manuf Specific %s/%s %s" %(key, EPout, str(listAttrSpecific)), nwkid=key)
                loggingReadAttributes( self, 'Debug', "Request Basic  via Read Attribute request Manuf Specific %s/%s " %(key, EPout) + " ".join("0x{:04x}".format(num) for num in listAttrSpecific), nwkid=key)
                ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0000", listAttrSpecific, manufacturer_spec = '01', manufacturer = manufacturer_code , ackIsDisabled = ackDisableOrEnable(self, key) , checkTime = False)

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
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0001", listAttributes , ackIsDisabled = ackDisableOrEnable(self, key))

def ReadAttributeRequest_0006_0000(self, key):
    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0006 focus on 0x0000 Key: %s " %key, nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0006' )
    for EPout in ListOfEp:
        listAttributes = [0]
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0006", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

def ReadAttributeRequest_0006_400x(self, key):
    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0006 focus on 0x4000x attributes- Key: %s " %key, nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0006' )
    for EPout in ListOfEp:
        listAttributes = []
        loggingReadAttributes( self, 'Log',"-----requesting Attribute 0x0006/0x4003 for PowerOn state for device : %s" %key, nwkid=key)
        listAttributes.append ( 0x4003 )

        if listAttributes:
            loggingReadAttributes( self, 'Log', "Request OnOff 0x4000x attributes via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0006", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

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
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0006", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

def ReadAttributeRequest_0008_0000(self, key):
    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0008 focus on 0x0008/0000 Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0008' )
    for EPout in ListOfEp:

        listAttributes = [0]
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0008", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

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
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0008", 0x0000, ackIsDisabled = ackDisableOrEnable(self, key) )

def ReadAttributeRequest_0020(self, key):

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0020 - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0020' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0020'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Request Polling via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0020", 0x0000)


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
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0300", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key) )

def ReadAttributeRequest_000C(self, key):
    # Cluster 0x000C with attribute 0x0055 / Xiaomi Power and Metering
    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_000C - Key: %s " %key, nwkid=key)

    listAttributes = [ 0x0051,0x0055, 0x006f, 0xff05 ]
    ListOfEp = getListOfEpForCluster( self, key, '000C' )
    for EPout in ListOfEp:
        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Request 0x000c info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "000C", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

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
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0100", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

def ReadAttributeRequest_0101(self, key):

    loggingReadAttributes( self, 'Debug', "Request Doorlock Read Attribute request: " + key , nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0101' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0101'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

            if listAttributes:
                loggingReadAttributes( self, 'Debug', "Request 0x0101 info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0101", listAttributes , ackIsDisabled = ackDisableOrEnable(self, key) )

def ReadAttributeRequest_0101_0000( self, key):
    loggingReadAttributes( self, 'Debug', "Request DoorLock Read Attribute request: " + key , nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0101' )
    for EPout in ListOfEp:
        listAttributes = [0x0000]
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0101", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))


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
                ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0102", listAttributes , ackIsDisabled = ackDisableOrEnable(self, key) )

def ReadAttributeRequest_0102_0008( self, key):
    loggingReadAttributes( self, 'Debug', "Request Windows Covering status Read Attribute request: " + key , nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0102' )
    for EPout in ListOfEp:
        listAttributes = [0x0008]
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0102", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

def ReadAttributeRequest_0201(self, key):
    # Thermostat 

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0201 - Key: %s " %key, nwkid=key)
    _model = False
    if 'Model' in self.ListOfDevices[key]:
        _model = True

    disableAck = True
    if 'PowerSource' in self.ListOfDevices[ key ] and self.ListOfDevices[ key ]['PowerSource'] == 'Battery':
        disableAck = False

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
        manufacturer_code = '0000'
        
        if ( 'Manufacturer' in self.ListOfDevices[key] and self.ListOfDevices[key]['Manufacturer'] == '105e' ) or \
            ( 'Manufacturer Name' in self.ListOfDevices[key] and self.ListOfDevices[key]['Manufacturer Name'] == 'Schneider Electric' ):
            # We need to break the Read Attribute between Manufacturer specifcs one and teh generic one
            manufacturer_code = '105e'
            for _attr in list(listAttributes):
                if _attr in ( 0xe011, 0x0e20 ):
                    listAttrSpecific.append( _attr )
                else:
                    listAttrGeneric.append( _attr )
            del listAttributes
            listAttributes = listAttrGeneric

        #Domoticz.Log("List Attributes: " + " ".join("0x{:04x}".format(num) for num in listAttributes) )
        
        if listAttributes:
            #loggingReadAttributes( self, 'Debug', "Request 0201 %s/%s 0201 %s " %(key, EPout, listAttributes), nwkid=key)
            loggingReadAttributes( self, 'Debug', "Request Thermostat  via Read Attribute request %s/%s " %(key, EPout) + " ".join("0x{:04x}".format(num) for num in listAttributes), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0201", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key) , checkTime = False)

        #Domoticz.Log("List Attributes Manuf Spec: " + " ".join("0x{:04x}".format(num) for num in listAttrSpecific) )
        if listAttrSpecific:
            #loggingReadAttributes( self, 'Debug', "Request Thermostat info via Read Attribute request Manuf Specific %s/%s %s" %(key, EPout, str(listAttrSpecific)), nwkid=key)
            loggingReadAttributes( self, 'Debug', "Request Thermostat  via Read Attribute request Manuf Specific %s/%s " %(key, EPout) + " ".join("0x{:04x}".format(num) for num in listAttrSpecific), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0201", listAttrSpecific, manufacturer_spec = '01', manufacturer =  manufacturer_code , ackIsDisabled = ackDisableOrEnable(self, key), checkTime=False)

def ReadAttributeRequest_0201_0012(self, key):

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0201 - Key: %s " %key, nwkid=key)
    _model = False
    if 'Model' in self.ListOfDevices[key]:
        _model = True

    disableAck = True
    if 'PowerSource' in self.ListOfDevices[ key ] and self.ListOfDevices[ key ]['PowerSource'] == 'Battery':
        disableAck = False

    ListOfEp = getListOfEpForCluster( self, key, '0201' )
    for EPout in ListOfEp:
        listAttributes = [ 0x0012 ]

        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0201", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key) )

def ReadAttributeRequest_0204(self, key):

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0204 - Key: %s " %key, nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0204' )
    for EPout in ListOfEp:
        listAttributes = [0x0001]
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0204'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr ) 
        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Request 0204 %s/%s 0204 %s " %(key, EPout, listAttributes), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0204", listAttributes , ackIsDisabled = ackDisableOrEnable(self, key))

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
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0400", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

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
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0402", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

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
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0403", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

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
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0405", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

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
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0406", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

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
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0500", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))
        
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
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0502", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

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
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0702", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key), checkTime=True)
    
        if listAttrSpecific:
            loggingReadAttributes( self, 'Debug', "Request Metering info  via Read Attribute request Manuf Specific %s/%s %s" %(key, EPout, str(listAttributes)), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0702", listAttrSpecific, manufacturer_spec = '01', manufacturer = self.ListOfDevices[key]['Manufacturer'], ackIsDisabled = True , checkTime=False)

def ReadAttributeRequest_0b05(self, key):
    # Cluster Diagnostic

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0b05 - Key: %s " %key, nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0b05' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0b05'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )
        
        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Request Diagnostic info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0b05", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))
    
def ReadAttributeRequest_0b04(self, key):
    # Cluster 0x0b04 Metering

    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_0b04 - Key: %s " %key, nwkid=key)
    _manuf = 'Manufacturer' in self.ListOfDevices[key]
    ListOfEp = getListOfEpForCluster( self, key, '0b04' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0b04'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )
    
        if listAttributes:
            loggingReadAttributes( self, 'Debug', "Request Metering info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0b04", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

def ReadAttributeRequest_0b04_050b( self, key):
    # Cluster 0x0b04 Metering / Specific 0x050B Attribute ( Instant Power)
    ListOfEp = getListOfEpForCluster( self, key, '0b04' )
    for EPout in ListOfEp:
        listAttributes = [ 0x050b ]
    
        loggingReadAttributes( self, 'Debug', "Request Metering Instant Power on 0x0b04 cluster: " + key + " EPout = " + EPout , nwkid=key)
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0b04", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))


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
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "000f", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

def ReadAttributeRequest_fc01(self, key):
    # Cluster Legrand
    loggingReadAttributes( self, 'Debug', "ReadAttributeRequest_fc01 - Key: %s " %key, nwkid=key)
    EPout = '01'

    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  'fc01'):
        if iterAttr not in listAttributes:
            listAttributes.append( iterAttr )
    
    if listAttributes:
        loggingReadAttributes( self, 'Debug', "Request Legrand attributes info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "fc01", listAttributes, ackIsDisabled = ackDisableOrEnable(self, key))

def ReadAttributeRequest_fc21(self, key):
    # Cluster PFX Profalux/ Manufacturer specific

    profalux = False
    if 'Manufacturer' in self.ListOfDevices[key]:
        profalux = ( self.ListOfDevices[key]['Manufacturer'] == '1110' and self.ListOfDevices[key]['ZDeviceID'] in ('0200', '0202') )

    if profalux:
        loggingReadAttributes( self, 'Log', "Request Profalux BSO via Read Attribute request: %s" %key, nwkid=key)
        read_attribute( self, '02', key ,ZIGATE_EP , '01' ,'fc21' , '00' , '01' , '1110' , 0x01, '0001', aackIsDisabled = ackDisableOrEnable(self, key))

        # datas = "02" + key + ZIGATE_EP + '01' + 'fc21' + '00' + '01' + '1110' + '01' + '0001'
        # sendZigateCmd(self, "0100", datas )


READ_ATTRIBUTES_REQUEST = {
    # Cluster : ( ReadAttribute function, Frequency )
    '0000' : ( ReadAttributeRequest_0000, 'polling0000' ),
    '0001' : ( ReadAttributeRequest_0001, 'polling0001' ),
    '0006' : ( ReadAttributeRequest_0006, 'pollingONOFF' ),
    '0008' : ( ReadAttributeRequest_0008, 'pollingLvlControl' ),
    '000C' : ( ReadAttributeRequest_000C, 'polling000C' ),
    '0020' : ( ReadAttributeRequest_000C, 'polling0020' ),
    '0100' : ( ReadAttributeRequest_0100, 'polling0100' ),
    '0101' : ( ReadAttributeRequest_0101, 'polling0101' ),
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
    '0b05' : ( ReadAttributeRequest_0702, 'polling0b05' ),
    '0b04' : ( ReadAttributeRequest_0b04, 'polling0b04' ),
    #'000f' : ( ReadAttributeRequest_000f, 'polling000f' ),
    'fc01' : ( ReadAttributeRequest_fc01, 'pollingfc01' ),
    'fc21' : ( ReadAttributeRequest_000f, 'pollingfc21' ),

    }
