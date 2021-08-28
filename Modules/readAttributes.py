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

from Classes.LoggingManagement import LoggingManagement

from Modules.zigateConsts import  MAX_READATTRIBUTES_REQ,  ZIGATE_EP
from Modules.basicOutputs import send_zigatecmd_zcl_ack, send_zigatecmd_zcl_noack, identifySend, read_attribute
from Modules.tools import getListOfEpForCluster, check_datastruct, is_time_to_perform_work, set_isqn_datastruct, \
              set_status_datastruct, set_timestamp_datastruct, is_attr_unvalid_datastruct, reset_attr_datastruct, \
              is_ack_tobe_disabled

ATTRIBUTES = { 
    '0000': [ 0x0004, 0x0005, 0x0000, 0x0001, 0x0002, 0x0003, 0x0006, 0x0007, 0x000A, 0x000F, 0x0010, 0x0015, 0x4000, 0xF000],
    '0001': [ 0x0000, 0x0001, 0x0003, 0x0020, 0x0021, 0x0033, 0x0035 ],
    '0003': [ 0x0000],
    '0004': [ 0x0000],
    '0005': [ 0x0001, 0x0002, 0x0003, 0x0004],
    '0006': [ 0x0000, 0x4001, 0x4002],
    '0008': [ 0x0000],
    '000a': [ 0x0000],
    '000c': [ 0x0051, 0x0055, 0x006f, 0xff05],
    '0019': [ 0x0002 ],
    '0020': [ 0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006 ],
    '0100': [ 0x0000, 0x0001, 0x0002, 0x0010, 0x0011],
    '0101': [ 0x0000, 0x0001, 0x0002, 0x0010, 0x0011, 0x0012, 0x0013, 0x0014, 0x0015, 0x0016, 0x0017, 0x0018, 0x0019, 0x0020, 0x0023, 0x0025, 0x0026, 0x0027, 0x0028, 0x0030, 0x0032, 0x0034, 0x0040, 0x0042, 0x0043, 0xfffd],
    '0102': [ 0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0007, 0x0008, 0x0009, 0x000A, 0x000B, 0x0010, 0x0011, 0x0014, 0x0017, 0xfffd],
    '0201': [ 0x0000, 0x0008, 0x0010, 0x0011, 0x0012,  0x0014, 0x0015, 0x0016, 0x001B, 0x001C, 0x001F, 0xfd00],
    '0202': [ 0x0000, 0x0001 ],
    '0204': [ 0x0000, 0x0001, 0x0002 ],
    '0300': [ 0x0000, 0x0001, 0x0003, 0x0004, 0x0007, 0x0008, 0x400a ],
    '0400': [ 0x0000],
    '0402': [ 0x0000],
    '0403': [ 0x0000],
    '0405': [ 0x0000],
    '0406': [ 0x0000, 0x0001, 0x0010, 0x0011, 0x0012],
    '0500': [ 0x0000, 0x0001, 0x0002],
    '0502': [ 0x0000],
    '0702': [ 0x0000, 0x0017, 0x0200, 0x0301, 0x0302, 0x0303, 0x0306, 0x0400],
    '000f': [ 0x0000, 0x0051, 0x0055, 0x006f, 0xfffd], 
    '0b04': [ 0x050b, 0x0505, 0x0508, ],
    '0b05': [ 0x0000 ],
    'fc01': [ 0x0000, 0x0001, 0x0002 ],# Legrand Cluster
    'fc21': [ 0x0001], 
    'fc40': [ 0x0000] # Legrand
    }


def ReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes , manufacturer_spec = '00', manufacturer = '0000', ackIsDisabled = True, checkTime=True):

    # Check if we are in pairing mode and Read Attribute must be broken down in 1 attribute max, otherwise use the default value
    maxReadAttributesByRequest = MAX_READATTRIBUTES_REQ
    if 'PairingInProgress' in self.ListOfDevices[ addr ] and self.ListOfDevices[ addr ]['PairingInProgress']:
        maxReadAttributesByRequest = 1

    if not isinstance(ListOfAttributes, list) or len (ListOfAttributes) <= maxReadAttributesByRequest:
        normalizedReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes , manufacturer_spec, manufacturer, ackIsDisabled )
    else:
        self.log.logging( "ReadAttributes", 
            'Debug2', "----------> ------- %s/%s %s ListOfAttributes: " %(addr, EpOut, Cluster) + " ".join("0x{:04x}".format(num) for num in ListOfAttributes), nwkid=addr)
        for shortlist in split_list(ListOfAttributes, wanted_parts = maxReadAttributesByRequest):
            self.log.logging( "ReadAttributes", 'Debug2', "----------> ------- Shorter: " + ", ".join("0x{:04x}".format(num) for num in shortlist), nwkid=addr)
            normalizedReadAttributeReq( self, addr, EpIn, EpOut, Cluster , shortlist , manufacturer_spec , manufacturer , ackIsDisabled)

def split_list(l, wanted_parts=1):
    """
    Split the list of attrributes in wanted part
    """
    return [  l[x: x+wanted_parts] for x in range(0, len(l), wanted_parts) ]

def normalizedReadAttributeReq( self, addr, EpIn, EpOut, Cluster , ListOfAttributes , manufacturer_spec, manufacturer, ackIsDisabled ):

    # Start method
    #Domoticz.Log("--> normalizedReadAttributeReq --> manufacturer_spec = '%s', manufacturer = '%s'" %(manufacturer_spec, manufacturer))
    if (
        'Health' in self.ListOfDevices[addr]
        and self.ListOfDevices[addr]['Health'] == 'Not Reachable'
    ):
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
    self.log.logging( "ReadAttributes", 'Debug2', "attributes: " +str(ListOfAttributes), nwkid=addr)
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

    self.log.logging( "ReadAttributes", 
        'Debug', 
        "-- normalizedReadAttrReq ---- addr =" +str(addr) +" Cluster = " +str(Cluster) +" Attributes = " + ", ".join("0x{:04x}".format(num) for num in ListOfAttributes), nwkid=addr )
    i_sqn = read_attribute( self, addr ,EpIn , EpOut ,Cluster ,direction , manufacturer_spec , manufacturer , lenAttr, Attr, ackIsDisabled=ackIsDisabled )

    for x in attributeList:
        set_isqn_datastruct(self, 'ReadAttributes', addr, EpOut, Cluster, x, i_sqn )
    set_timestamp_datastruct(self, 'ReadAttributes', addr, EpOut, Cluster, int(time()) ) 

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
        self.log.logging( "ReadAttributes", 'Debug2', "normalizedReadAttrReq - Skip Read Attribute due to DeviceConf Nwkid: %s Cluster: %s Attribute: %s"
                %(addr, Cluster, Attr ), nwkid=addr)
        return False
    return True

def retreive_ListOfAttributesByCluster( self, key, Ep, cluster ):
    
    targetAttribute = retreive_attributes_based_on_configuration(self, key, cluster)
    if targetAttribute is not None:
        return targetAttribute

    targetAttribute =  retreive_attributes_from_default_device_list( self, key, Ep, cluster )
    if targetAttribute is not None:
        return targetAttribute

    # Attribute based on default
    targetAttribute = retreive_attributes_from_default_plugin_list( self, key, Ep, cluster)
    if targetAttribute is not None:
        return targetAttribute
    return []


def retreive_attributes_based_on_configuration(self, key, cluster):
    if 'Model' not in self.ListOfDevices[key]:
        return None
    if self.ListOfDevices[key]['Model'] not in self.DeviceConf:
        return None
    if 'ReadAttributes' not in self.DeviceConf[ self.ListOfDevices[key]['Model'] ]:
        return None
    if cluster not in  self.DeviceConf[ self.ListOfDevices[key]['Model'] ]['ReadAttributes']:
        return None

    #Domoticz.Log("-->Attributes based on Configuration")
    targetAttribute = []
    for attr in self.DeviceConf[ self.ListOfDevices[key]['Model'] ]['ReadAttributes'][cluster]:
        targetAttribute.append( int(attr,16) )
    return targetAttribute

def retreive_attributes_from_default_device_list( self, key, Ep, cluster ):

    if 'Attributes List' not in self.ListOfDevices[key]:
        return None
    if 'Ep' not in self.ListOfDevices[key]['Attributes List']:
        return None
    if Ep in self.ListOfDevices[key]['Attributes List']['Ep']:
        return None
    if cluster not in self.ListOfDevices[key]['Attributes List']['Ep'][Ep]:
        return None

    targetAttribute = []
    self.log.logging( "ReadAttributes", 'Debug', "retreive_ListOfAttributesByCluster: Attributes from Attributes List", nwkid=key)
    for attr in  self.ListOfDevices[key]['Attributes List']['Ep'][Ep][cluster]:
        targetAttribute.append( int(attr,16) )

    # Special Hacks
    if 'Model' in self.ListOfDevices[key]:
        # Force Read Attributes 
        if (self.ListOfDevices[key]['Model'] == 'SPE600' and cluster == '0702') or \
            (self.ListOfDevices[key]['Model'] == 'TS0302' and cluster == '0102'):     # Zemismart Blind switch
            for addattr in ATTRIBUTES[cluster]:
                if addattr not in targetAttribute:
                    targetAttribute.append( addattr )
    return targetAttribute

def retreive_attributes_from_default_plugin_list( self, key, Ep, cluster):

    targetAttribute = None
    self.log.logging( "ReadAttributes", 'Debug2', 
            "retreive_ListOfAttributesByCluster: default attributes list for cluster: %s" %cluster, nwkid=key)
    if cluster in ATTRIBUTES:
        targetAttribute = ATTRIBUTES[cluster]
    else:
        Domoticz.Debug("retreive_ListOfAttributesByCluster: Missing Attribute for cluster %s" %cluster)
        targetAttribute = [ 0x0000 ]
    self.log.logging( "ReadAttributes", 'Debug', 
        "---- retreive_ListOfAttributesByCluster: List of Attributes for cluster %s : " %(cluster) + 
        " ".join("0x{:04x}".format(num) for num in targetAttribute), nwkid=key)

    return targetAttribute

def ping_tuya_device( self, key ):

    PING_CLUSTER = '0000'
    PING_ATTRIBUTE = '0001'
    self.log.logging( "ReadAttributes", 'Log', "Ping Tuya Devices - Key: %s" %(key), nwkid=key)
    send_zigatecmd_zcl_ack( self, key, '0100', ZIGATE_EP + '01' + PING_CLUSTER + '00' + '00' + '0000' + "%02x" %(0x01) + PING_ATTRIBUTE )

def ping_device_with_read_attribute(self, key):
    # In order to ping a device, we simply send a Read Attribute on Cluster 0x0000 and looking for Attribute 0x0000
    # This Cluster/Attribute is mandatory for each devices.
    PING_CLUSTER = '0000'
    PING_CLUSTER_ATTRIBUTE = '0000'

    self.log.logging( "ReadAttributes", 'Debug', "Ping Device Physical device - Key: %s" %(key), nwkid=key)

    if 'Model' in self.ListOfDevices[key] and self.ListOfDevices[key]['Model'] in ('GL-B-007Z',):
        PING_CLUSTER = '0006'
        PING_CLUSTER_ATTRIBUTE = '0000'

    ListOfEp = getListOfEpForCluster( self, key, PING_CLUSTER )
    for EPout in ListOfEp:
        check_datastruct( self, 'ReadAttributes', key, EPout, PING_CLUSTER )
        #       send_zigatecmd_zcl_ack( self, key, '0100', EpIn      + EpOut + Cluster      + dir  + ManufSpe + manufacturer + '%02x' %lenAttr + Attr )
        i_sqn = send_zigatecmd_zcl_ack( self, key, '0100', ZIGATE_EP + EPout + PING_CLUSTER + '00' + '00' + '0000' + "%02x" %(0x01) + PING_CLUSTER_ATTRIBUTE )
        set_isqn_datastruct(self, 'ReadAttributes', key, EPout, PING_CLUSTER, PING_CLUSTER_ATTRIBUTE, i_sqn )
        # Let's ping only 1 EndPoint
        break

def ReadAttributeRequest_0000(self, key, fullScope=True):
    # Basic Cluster
    # The Ep to be used can be challenging, as if we are in the discovery process, the list of Eps is not yet none and it could even be that the Device has only 1 Ep != 01

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0000 - Key: %s , Scope: %s" %(key, fullScope), nwkid=key)
    EPout = '01'

    # Checking if Ep list is empty, in that case we are in discovery mode and 
        # we don't really know what are the EPs we can talk to.
    if not fullScope or self.ListOfDevices[key]['Ep'] is None or self.ListOfDevices[key]['Ep'] == {}:
        ReadAttributeRequest_0000_for_pairing( self, key )
    else:
        ReadAttributeRequest_0000_for_general( self, key )

def ReadAttributeRequest_0000_for_pairing( self, key ):
    self.log.logging( "ReadAttributes", 'Debug', "--> Not full scope", nwkid=key)
    self.log.logging( "ReadAttributes", 'Debug', "--> Build list of Attributes", nwkid=key)
    skipModel = False

    listAttributes = []
    # Do we Have Manufacturer
    if self.ListOfDevices[key]['Manufacturer'] == '' and self.ListOfDevices[key]['Ep'] and self.ListOfDevices[key]['Ep'] != {}:
        self.log.logging( "ReadAttributes", 'Log', "Request Basic  Manufacturer via Read Attribute request: %s" %'0004', nwkid=key)
        manuf_name = [ 0x0004 ]
        for x in self.ListOfDevices[key]['Ep']:
            ReadAttributeReq( self, key, ZIGATE_EP, x, "0000", manuf_name, ackIsDisabled = False , checkTime = False)

    # Do We have Model Name
    if not skipModel and self.ListOfDevices[key]['Model'] in [{}, ''] and self.ListOfDevices[key]['Ep'] and self.ListOfDevices[key]['Ep'] != {}:
        self.log.logging( "ReadAttributes", 'Debug', "Request Basic  Model Name via Read Attribute request: %s" %'0005', nwkid=key)
        model_name = [ 0x0005 ]
        for x in self.ListOfDevices[key]['Ep']:
            ReadAttributeReq( self, key, ZIGATE_EP, x, "0000", model_name, ackIsDisabled = False , checkTime = False)
    else:
        listAttributes.append(0x0005)

    # Check if Model Name should be requested
    if self.ListOfDevices[key]['Manufacturer'] == '1110': # Profalux.
        listAttributes.append(0x0010)
        skipModel = True

    elif self.ListOfDevices[key]['Manufacturer'] == 'Legrand':
        self.log.logging( "ReadAttributes", 'Debug', "----> Adding: %s" %'f000', nwkid=key)
        listAttributes.append(0x4000)
        listAttributes.append(0xf000)
        skipModel = True
    
    listAttributes = add_attributes_from_device_certified_conf( self, key, '0000' , listAttributes)
    self.log.logging( "ReadAttributes", 'Log', "EP: %s" %self.ListOfDevices[key]['Ep'])
                      
    if self.ListOfDevices[key]['Ep'] is None or self.ListOfDevices[key]['Ep'] == {}:
        # We don't have yet any Endpoint information , we will then try several known Endpoint, and luckly we will get some answers 
        self.log.logging( "ReadAttributes", 'Debug', "Request Basic  via Read Attribute request: " + key + " EPout = " + "01, 02, 03, 06, 09" , nwkid=key)
        ReadAttributeReq( self, key, ZIGATE_EP, "01", "0000", listAttributes, ackIsDisabled = False , checkTime = False)
        ReadAttributeReq( self, key, ZIGATE_EP, "0b", "0000", listAttributes, ackIsDisabled = False , checkTime = False) # Schneider
        ReadAttributeReq( self, key, ZIGATE_EP, "02", "0000", listAttributes, ackIsDisabled = False , checkTime = False)
        ReadAttributeReq( self, key, ZIGATE_EP, "03", "0000", listAttributes, ackIsDisabled = False , checkTime = False)
        ReadAttributeReq( self, key, ZIGATE_EP, "06", "0000", listAttributes, ackIsDisabled = False , checkTime = False) # Livolo
        ReadAttributeReq( self, key, ZIGATE_EP, "09", "0000", listAttributes, ackIsDisabled = False , checkTime = False)
        
    else:
        for epout in self.ListOfDevices[key]['Ep']:
            self.log.logging( "ReadAttributes", 'Debug', "Request Basic  via Read Attribute request: " + key + " EPout = " + epout + " Attributes: " + str(listAttributes), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, epout, "0000", listAttributes, ackIsDisabled = False , checkTime = False)

def add_attributes_from_device_certified_conf( self, key, cluster, listAttributes ):

    attributes = retreive_attributes_based_on_configuration(self, key, cluster)
    if attributes is None:
        return listAttributes

    for attr in attributes:
        if int( str(attr) , 16) not in listAttributes:
            listAttributes.append( int( attr , 16))  
    return listAttributes

def ReadAttributeRequest_0000_for_general( self, key ):

    
    listAttributes = []
    self.log.logging( "ReadAttributes", 'Debug', "--> Full scope", nwkid=key)
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
            #Domoticz.Log("Specific Manufacturer !!!!")
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
            #self.log.logging( "ReadAttributes", 'Debug', "Request Basic  via Read Attribute request %s/%s %s" %(key, EPout, str(listAttributes)), nwkid=key)
            self.log.logging( "ReadAttributes", 'Debug', "Request Basic  via Read Attribute request %s/%s " %(key, EPout) + " ".join("0x{:04x}".format(num) for num in listAttributes), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0000", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key), checkTime = False )

        #Domoticz.Log("List Attributes Manuf Spec: " + " ".join("0x{:04x}".format(num) for num in listAttrSpecific) )
        if listAttrSpecific:
            #self.log.logging( "ReadAttributes", 'Debug', "Request Basic  via Read Attribute request Manuf Specific %s/%s %s" %(key, EPout, str(listAttrSpecific)), nwkid=key)
            self.log.logging( "ReadAttributes", 'Debug', "Request Basic  via Read Attribute request Manuf Specific %s/%s " %(key, EPout) + " ".join("0x{:04x}".format(num) for num in listAttrSpecific), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0000", listAttrSpecific, manufacturer_spec = '01', manufacturer = manufacturer_code , ackIsDisabled = is_ack_tobe_disabled(self, key) , checkTime = False)


def ReadAttributeRequest_0001(self, key, force_disable_ack=None):

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0001 - Key: %s " %key, nwkid=key)

    # Power Config
    ListOfEp = getListOfEpForCluster( self, key, '0001' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0001'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Request Power Config via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            if force_disable_ack:
                ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0001", listAttributes , ackIsDisabled = True)
            else:
                ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0001", listAttributes , ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0006_0000(self, key):
    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0006 focus on 0x0000 Key: %s " %key, nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0006' )
    for EPout in ListOfEp:
        listAttributes = [0]
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0006", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0006_400x(self, key):
    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0006 focus on 0x400x attributes- Key: %s " %key, nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0006' )
    for EPout in ListOfEp:
        listAttributes = []
        if  ( 'Model' in self.ListOfDevices[key] and self.ListOfDevices[key]['Model'] in ( 'TS0121', 'TS0115') ):
            listAttributes.append ( 0x8002 )
            self.log.logging( "ReadAttributes", 'Debug',"-----requesting Attribute 0x0006/0x8002 for PowerOn state for device : %s" %key, nwkid=key)
        else:
            listAttributes.append ( 0x4003 )
            self.log.logging( "ReadAttributes", 'Debug',"-----requesting Attribute 0x0006/0x4003 for PowerOn state for device : %s" %key, nwkid=key)

        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Request OnOff 0x4000x attributes via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0006", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0006(self, key):
    # Cluster 0x0006

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0006 - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0006' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0006'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Request OnOff status via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0006", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0008_0000(self, key):
    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0008 focus on 0x0008/0000 Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0008' )
    for EPout in ListOfEp:

        listAttributes = [0]
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0008", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0008(self, key):
    # Cluster 0x0008 

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0008 - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0008' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0008'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Request Level Control via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0008", 0x0000, ackIsDisabled = is_ack_tobe_disabled(self, key) )

def ReadAttributeRequest_0020(self, key):

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0020 - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0020' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0020'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Request Polling via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0020", 0x0000)

def ReadAttributeRequest_000C(self, key):
    # Cluster 0x000C with attribute 0x0055 / Xiaomi Power and Metering
    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_000C - Key: %s " %key, nwkid=key)

    listAttributes = [ 0x0051,0x0055, 0x006f, 0xff05 ]
    ListOfEp = getListOfEpForCluster( self, key, '000C' )
    for EPout in ListOfEp:
        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Request 0x000c info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "000C", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0019(self, key):
    # Cluster 0x000C with attribute 0x0055 / Xiaomi Power and Metering
    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0019 - Key: %s " %key, nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0019' )
    for EPout in ListOfEp:
        listAttributes = retreive_ListOfAttributesByCluster( self, key, EPout,  '0019')
        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Request 0x0019 info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0019", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))


def ReadAttributeRequest_0100(self, key):

    self.log.logging( "ReadAttributes", 'Debug', "Request shade Configuration status Read Attribute request: " + key , nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0100' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0100'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Request 0x0100 info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0100", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0101(self, key):

    self.log.logging( "ReadAttributes", 'Debug', "Request Doorlock Read Attribute request: " + key , nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0101' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0101'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

            if listAttributes:
                self.log.logging( "ReadAttributes", 'Debug', "Request 0x0101 info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0101", listAttributes , ackIsDisabled = is_ack_tobe_disabled(self, key) )

def ReadAttributeRequest_0101_0000( self, key):
    self.log.logging( "ReadAttributes", 'Debug', "Request DoorLock Read Attribute request: " + key , nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0101' )
    for EPout in ListOfEp:
        listAttributes = [0x0000]
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0101", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))


def ReadAttributeRequest_0102(self, key):

    self.log.logging( "ReadAttributes", 'Debug', "Request Windows Covering status Read Attribute request: " + key , nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0102' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0102'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

            if listAttributes:
                self.log.logging( "ReadAttributes", 'Debug', "Request 0x0102 info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
                ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0102", listAttributes , ackIsDisabled = is_ack_tobe_disabled(self, key) )

def ReadAttributeRequest_0102_0008( self, key):
    self.log.logging( "ReadAttributes", 'Debug', "Request Windows Covering status Read Attribute request: " + key , nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0102' )
    for EPout in ListOfEp:
        listAttributes = [0x0008]
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0102", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0201(self, key):
    # Thermostat 

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0201 - Key: %s " %key, nwkid=key)
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
                self.log.logging( "ReadAttributes", 'Debug', "- req Attributes for  Super TR", nwkid=key)
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
            if self.ListOfDevices[key]['Manufacturer Name'] == 'Schneider Electric':
                manufacturer_code = '105e'
            elif self.ListOfDevices[key]['Manufacturer Name'] in ('OWON', 'CASAIA'):
                manufacturer_code = '113c'

            for _attr in list(listAttributes):
                if _attr in ( 0xe011, 0x0e20 , 0xfd00 ):
                    listAttrSpecific.append( _attr )
                else:
                    listAttrGeneric.append( _attr )
            del listAttributes
            listAttributes = listAttrGeneric

        #Domoticz.Log("List Attributes: " + " ".join("0x{:04x}".format(num) for num in listAttributes) )
        
        if listAttributes:
            #self.log.logging( "ReadAttributes", 'Debug', "Request 0201 %s/%s 0201 %s " %(key, EPout, listAttributes), nwkid=key)
            self.log.logging( "ReadAttributes", 'Debug', "Request Thermostat  via Read Attribute request %s/%s " %(key, EPout) + " ".join("0x{:04x}".format(num) for num in listAttributes), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0201", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key) , checkTime = False)

        #Domoticz.Log("List Attributes Manuf Spec: " + " ".join("0x{:04x}".format(num) for num in listAttrSpecific) )
        if listAttrSpecific:
            #self.log.logging( "ReadAttributes", 'Debug', "Request Thermostat info via Read Attribute request Manuf Specific %s/%s %s" %(key, EPout, str(listAttrSpecific)), nwkid=key)
            self.log.logging( "ReadAttributes", 'Debug', "Request Thermostat  via Read Attribute request Manuf Specific %s/%s " %(key, EPout) + " ".join("0x{:04x}".format(num) for num in listAttrSpecific), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0201", listAttrSpecific, manufacturer_spec = '01', manufacturer =  manufacturer_code , ackIsDisabled = is_ack_tobe_disabled(self, key), checkTime=False)

def ReadAttributeRequest_0201_0012(self, key):

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0201 - Key: %s " %key, nwkid=key)
    _model = False
    if 'Model' in self.ListOfDevices[key]:
        _model = True

    disableAck = True
    if 'PowerSource' in self.ListOfDevices[ key ] and self.ListOfDevices[ key ]['PowerSource'] == 'Battery':
        disableAck = False

    ListOfEp = getListOfEpForCluster( self, key, '0201' )
    for EPout in ListOfEp:
        listAttributes = [ 0x0012 ]

        if '0201' in self.ListOfDevices[ key ]['Ep'][ EPout] and '0010' in self.ListOfDevices[ key ]['Ep'][ EPout]['0201']:
            listAttributes.append ( 0x0010 )

        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0201", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key) )

def ReadAttributeRequest_0202(self, key):
    # Fan Control
    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0202 - Key: %s " %key, nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0202' )
    for EPout in ListOfEp:
        listAttributes = [0x0001]
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0202'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr ) 
        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Request 0202 %s/%s 0202 %s " %(key, EPout, listAttributes), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0202", listAttributes , ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0204(self, key):

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0204 - Key: %s " %key, nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0204' )
    for EPout in ListOfEp:
        listAttributes = [0x0001]
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0204'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr ) 
        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Request 0204 %s/%s 0204 %s " %(key, EPout, listAttributes), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0204", listAttributes , ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0300(self, key):
    # Cluster 0x0300 - Color Control

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0300 - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0300' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0300'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Request Color Temp infos via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0300", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key) )

def ReadAttributeRequest_0400(self, key):

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0400 - Key: %s " %key, nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0400' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0400'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Illuminance info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0400", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0402(self, key):

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0402 - Key: %s " %key, nwkid=key)

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
            self.log.logging( "ReadAttributes", 'Debug', "Temperature info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0402", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0403(self, key):

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0403 - Key: %s " %key, nwkid=key)
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
            self.log.logging( "ReadAttributes", 'Debug', "Pression Atm info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0403", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0405(self, key):

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0405 - Key: %s " %key, nwkid=key)
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
            self.log.logging( "ReadAttributes", 'Debug', "Humidity info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0405", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0406(self, key):

    manufacturer='0000'
    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0406 - Key: %s " %key, nwkid=key)
    _model = 'Model' in self.ListOfDevices[key]
    ListOfEp = getListOfEpForCluster( self, key, '0406' )
    for EPout in ListOfEp:
        listAttributes = []
        listAttrSpecific = []

        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0406'):
            if iterAttr not in listAttributes:
                if _model and self.ListOfDevices[key]['Model'] == 'lumi.light.aqcn02': # Aqara Blulb
                    continue
                listAttributes.append( iterAttr )

        # Adjustement before request
        listAttrSpecific = []
        listAttrGeneric = []
        if _model and self.ListOfDevices[key]['Model'] in ('SML001', 'SML002'):
            manufacturer = '100b'
            # We need to break the Read Attribute between Manufacturer specifcs one and teh generic one
            for _attr in list(listAttributes):
                if _attr in ( 0x0030 , 0x0031):
                    listAttrSpecific.append( _attr )
                else:
                    listAttrGeneric.append( _attr )
            del listAttributes
            listAttributes = listAttrGeneric


        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Occupancy info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0406", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

        if listAttrSpecific:
            self.log.logging( "ReadAttributes", 'Debug', "Occupancy info  via Read Attribute request Manuf Specific %s/%s %s" %(key, EPout, str(listAttributes)), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0406", listAttrSpecific, manufacturer_spec = '01', manufacturer = manufacturer, ackIsDisabled = True , checkTime=False)

def ReadAttributeRequest_0406_0010(self, key):

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0406/0010- Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0406' )
    listAttributes = [ 0x0010 ]
    for EPout in ListOfEp:
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0406", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0406_philips_0030(self, key):
    manufacturer = '100b'
    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0406/0010- Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0406' )
    listAttrSpecific = [ 0x0030 ]
    for EPout in ListOfEp:
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0406", listAttrSpecific, manufacturer_spec = '01', manufacturer = manufacturer, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0500(self, key):

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0500 - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0500' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0500'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0500 - %s/%s - %s" %(key, EPout, listAttributes), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0500", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))
        
def ReadAttributeRequest_0502(self, key):

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0502 - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '0502' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0502'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0502 - %s/%s - %s" %(key, EPout, listAttributes), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0502", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0702(self, key):
    # Cluster 0x0702 Metering

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0702 - Key: %s " %key, nwkid=key)
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
            self.log.logging( "ReadAttributes", 'Debug', "Request Metering info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0702", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key), checkTime=True)
    
        if listAttrSpecific:
            self.log.logging( "ReadAttributes", 'Debug', "Request Metering info  via Read Attribute request Manuf Specific %s/%s %s" %(key, EPout, str(listAttributes)), nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0702", listAttrSpecific, manufacturer_spec = '01', manufacturer = self.ListOfDevices[key]['Manufacturer'], ackIsDisabled = True , checkTime=False)

def ReadAttributeRequest_0702_0000(self, key):
    # Cluster 0x0702 Metering / Specific 0x0000 
    ListOfEp = getListOfEpForCluster( self, key, '0702' )
    for EPout in ListOfEp:
        listAttributes = [ 0x0000 ]
        self.log.logging( "ReadAttributes", 'Debug', "Request Summation on 0x0702 cluster: " + key + " EPout = " + EPout , nwkid=key)
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0702", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0b04(self, key):
    # Cluster 0x0b04 Metering

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0b04 - Key: %s " %key, nwkid=key)
    _manuf = 'Manufacturer' in self.ListOfDevices[key]
    ListOfEp = getListOfEpForCluster( self, key, '0b04' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0b04'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )
    
        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Request Metering info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0b04", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))


def ReadAttributeRequest_0b04_0505( self, key):
    # Cluster 0x0b04 Metering / Specific 0x0505 Attribute ( Voltage)
    ListOfEp = getListOfEpForCluster( self, key, '0b04' )
    for EPout in ListOfEp:
        listAttributes = [ 0x0505 ]
    
        self.log.logging( "ReadAttributes", 'Debug', "Request Metering Instant Power on 0x0b04 cluster: " + key + " EPout = " + EPout , nwkid=key)
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0b04", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0b04_050b( self, key):
    # Cluster 0x0b04 Metering / Specific 0x050B Attribute ( Instant Power)
    ListOfEp = getListOfEpForCluster( self, key, '0b04' )
    for EPout in ListOfEp:
        listAttributes = [ 0x050b ]
    
        self.log.logging( "ReadAttributes", 'Debug', "Request Metering Instant Power on 0x0b04 cluster: " + key + " EPout = " + EPout , nwkid=key)
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0b04", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_0b04_050b_0505_0508( self, key):
    # Cluster 0x0b04 Metering / Specific 0x050B Attribute ( Instant Power), 0x0505 ( Voltage), 0x058 (Current)
    # Use for Blitwolf Plug
    ListOfEp = getListOfEpForCluster( self, key, '0b04' )
    for EPout in ListOfEp:
        listAttributes = [ 0x0505, 0x0508, 0x050b ]
        self.log.logging( "ReadAttributes", 'Debug', "Request Metering Instant Power on 0x0b04 cluster: " + key + " EPout = " + EPout , nwkid=key)
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0b04", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))
        #istAttributes = [  0x0508 ]
        #eadAttributeReq( self, key, ZIGATE_EP, EPout, "0b04", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))


def ReadAttributeRequest_0b05(self, key):
    # Cluster Diagnostic

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_0b05 - Key: %s " %key, nwkid=key)

    ListOfEp = getListOfEpForCluster( self, key, '0b05' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '0b05'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )
        
        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', "Request Diagnostic info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "0b05", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_000f(self, key):

    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_000f - Key: %s " %key, nwkid=key)
    ListOfEp = getListOfEpForCluster( self, key, '000f' )
    for EPout in ListOfEp:
        listAttributes = []
        for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  '000f'):
            if iterAttr not in listAttributes:
                listAttributes.append( iterAttr )

        if listAttributes:
            self.log.logging( "ReadAttributes", 'Debug', " Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
            ReadAttributeReq( self, key, ZIGATE_EP, EPout, "000f", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))

def ReadAttributeRequest_fc00(self, key):
    pass

def ReadAttributeRequest_fc01(self, key):
    # Cluster Legrand
    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_fc01 - Key: %s " %key, nwkid=key)
    EPout = '01'

    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  'fc01'):
        if iterAttr not in listAttributes:
            listAttributes.append( iterAttr )
    
    if listAttributes:
        self.log.logging( "ReadAttributes", 'Debug', "Request Legrand attributes info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
        #ReadAttributeReq( self, key, ZIGATE_EP, EPout, "fc01", listAttributes, manufacturer_spec = '01', manufacturer = '1021', ackIsDisabled = is_ack_tobe_disabled(self, key))
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "fc01", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))



def ReadAttributeRequest_fc21(self, key):
    # Cluster PFX Profalux/ Manufacturer specific

    profalux = False
    if 'Manufacturer' in self.ListOfDevices[key]:
        profalux = ( self.ListOfDevices[key]['Manufacturer'] == '1110' and self.ListOfDevices[key]['ZDeviceID'] in ('0200', '0202') )

    if profalux:
        self.log.logging( "ReadAttributes", 'Debug', "Request Profalux BSO via Read Attribute request: %s" %key, nwkid=key)
        read_attribute( self, '02', key ,ZIGATE_EP , '01' ,'fc21' , '00' , '01' , '1110' , 0x01, '0001', aackIsDisabled = is_ack_tobe_disabled(self, key))

        # datas = "02" + key + ZIGATE_EP + '01' + 'fc21' + '00' + '01' + '1110' + '01' + '0001'
        # sendZigateCmd(self, "0100", datas )

def ReadAttributeRequest_fc40(self, key):
    # Cluster Legrand
    self.log.logging( "ReadAttributes", 'Debug', "ReadAttributeRequest_fc40 - Key: %s " %key, nwkid=key)
    EPout = '01'

    listAttributes = []
    for iterAttr in retreive_ListOfAttributesByCluster( self, key, EPout,  'fc40'):
        if iterAttr not in listAttributes:
            listAttributes.append( iterAttr )
    
    if listAttributes:
        self.log.logging( "ReadAttributes", 'Debug', "Request Legrand fc40 attributes info via Read Attribute request: " + key + " EPout = " + EPout , nwkid=key)
        ReadAttributeReq( self, key, ZIGATE_EP, EPout, "fc40", listAttributes, ackIsDisabled = is_ack_tobe_disabled(self, key))


READ_ATTRIBUTES_REQUEST = {
    # Cluster : ( ReadAttribute function, Frequency )
    '0000' : ( ReadAttributeRequest_0000, 'polling0000' ),
    '0001' : ( ReadAttributeRequest_0001, 'polling0001' ),
    '0008' : ( ReadAttributeRequest_0008, 'pollingLvlControl' ),
    '0006' : ( ReadAttributeRequest_0006, 'pollingONOFF' ),
    '000C' : ( ReadAttributeRequest_000C, 'polling000C' ),
    '0019' : ( ReadAttributeRequest_0019, 'polling0019' ),
    '0020' : ( ReadAttributeRequest_000C, 'polling0020' ),
    '0100' : ( ReadAttributeRequest_0100, 'polling0100' ),
    '0101' : ( ReadAttributeRequest_0101, 'polling0101' ),
    '0102' : ( ReadAttributeRequest_0102, 'polling0102' ),
    '0201' : ( ReadAttributeRequest_0201, 'polling0201' ),
    '0202' : ( ReadAttributeRequest_0202, 'polling0202' ),
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
    'fc40': ( ReadAttributeRequest_fc40, 'pollingfc40' ),
    }
