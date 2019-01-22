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

from Modules.z_consts import ZLL_DEVICES
from Modules.z_tools import getClusterListforEP


def ZigateConf_light(self, discover ):
    '''
    It is called for normal startup
    '''
    sendZigateCmd(self, "0010", "") # Get Firmware version

    Domoticz.Debug("ZigateConf -  Request: Get List of Device " + str(self.FirmwareVersion))
    sendZigateCmd(self, "0015", "")

    # As per https://www.nxp.com/docs/en/user-guide/JN-UG-3077.pdf
    # Page 263
    # Set Time since  0 hours, 0 minutes, 0 seconds, on the 1st of January, 2000 UTC
    EPOCTime = datetime(2000,1,1)
    UTCTime = int((datetime.now() - EPOCTime).total_seconds())

    Domoticz.Status("ZigateConf - Setting UTC Time to : %s" %( UTCTime) )
    sendZigateCmd(self, "0016", str(UTCTime) )

    sendZigateCmd(self, "0009", "") # In order to get Zigate IEEE and NetworkID

    #Domoticz.Status("Start network scan")
    #sendZigateCmd(self, "0025", "" )   # Start Network Scan ( Network Formation )

    Domoticz.Status("Start network")
    sendZigateCmd(self, "0024", "" )   # Start Network

    if not str(discover).isdigit() :
        discover = 0
    else:
        discover = "%02.X" %int(discover)
    if discover == "FF":
        Domoticz.Status("Zigate enter in discover mode for ever")
        self.permitTojoin = 0xff
    else: 
        Domoticz.Status("Zigate enter in discover mode for %s Secs" %(int(discover,16)))
        self.permitTojoin = int(discover,16)

    if discover != "00":    # In order to avoid Devices's noise
        sendZigateCmd(self, "0049","FFFC" + discover + "00")

    Domoticz.Debug("Request Permit Join Status")
    sendZigateCmd( self, "0014", "" ) # Request status


def ZigateConf(self, discover ):
    '''
    Called after Erase and Software Reset
    '''
    ################### ZiGate - get Firmware version #############
    # answer is expected on message 8010
    sendZigateCmd(self, "0010","")

    ################### ZiGate - Set Type COORDINATOR #################
    sendZigateCmd(self, "0023","00")

    ################### ZiGate - set channel ##################
    Domoticz.Log("ZigateConf setting Channel(s) to: %s" %self.pluginconf.channel)
    setChannel(self, self.pluginconf.channel)

    ################### ZiGate - start network ##################
    sendZigateCmd(self, "0024","")

    sendZigateCmd(self, "0009","") # In order to get Zigate IEEE and NetworkID

    ################### ZiGate - Request Device List #############
    # answer is expected on message 8015. Only available since firmware 03.0b
    Domoticz.Debug("ZigateConf -  Request: Get List of Device " + str(self.FirmwareVersion) )
    sendZigateCmd(self, "0015","")

    ################### ZiGate - discover mode 255 sec Max ##################
    #### Set discover mode only if requested - so != 0                  #####
    if str(discover) != "0":
        if str(discover)=="255": 
            Domoticz.Status("Zigate enter in discover mode for ever")
        else: 
            Domoticz.Status("Zigate enter in discover mode for " + str(discover) + " Secs" )
        sendZigateCmd(self, "0049","FFFC" + hex(int(discover))[2:4] + "00")

    Domoticz.Debug("Request network Status")
    sendZigateCmd( self, "0014", "" ) # Request status
        
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

    if 'ReadAttributes' in self.ListOfDevices[addr]:
        if 'Ep' not in self.ListOfDevices[addr]['ReadAttributes']:
            self.ListOfDevices[addr]['ReadAttributes']['Ep'] = {}
        if EpOut in self.ListOfDevices[addr]['ReadAttributes']['Ep']:
            if str(Cluster) not in self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut]:
                self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)] = {}
        else:
            self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut] = {}
            self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)] = {}
        if 'TimeStamps' not in self.ListOfDevices[addr]['ReadAttributes']:
            self.ListOfDevices[addr]['ReadAttributes']['TimeStamps'] = {}
            self.ListOfDevices[addr]['ReadAttributes']['TimeStamps'][EpOut+'-'+str(Cluster)] = 0
    else:
        self.ListOfDevices[addr]['ReadAttributes'] = {}
        self.ListOfDevices[addr]['ReadAttributes']['Ep'] = {}
        self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut] = {}
        self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)] = {}
        self.ListOfDevices[addr]['ReadAttributes']['TimeStamps'] = {}
        self.ListOfDevices[addr]['ReadAttributes']['TimeStamps'][EpOut+'-'+str(Cluster)] = 0

    if not isinstance(ListOfAttributes, list):
        # We received only 1 attribute
        Attr = "%04x" %(ListOfAttributes)
        lenAttr = 1
        weight = 1

        if Attr in self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)]:
            if self.ListOfDevices[addr]['ReadAttributes']['Ep'][EpOut][str(Cluster)][Attr] == '86':
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

def ReadAttributeRequest_0000(self, key, fullScope=True):
    # Basic Cluster
    # The Ep to be used can be challenging, as if we are in the discovery process, the list of Eps is not yet none and it could even be that the Device has only 1 Ep != 01

    Domoticz.Debug("ReadAttributeRequest_0000 - Key: %s " %key)
    EPin = "01"
    EPout= "01"

    # General
    listAttributes = []
    # By default only request attribute 0x0005 to get the model Identifier
    listAttributes.append(0x0000)        # 
    listAttributes.append(0x0005)        # Model Identifier

    if fullScope:
        listAttributes.append(0x0004)        # 

        listAttributes.append(0x0007)        # Power Source
        listAttributes.append(0x0010)        # Battery

    # Checking if Ep list is empty, in that case we are in discovery mode and we don't really know what are the EPs we can talk to.
    if self.ListOfDevices[key]['Ep'] is None or self.ListOfDevices[key]['Ep'] == {} :
        Domoticz.Debug("Request Basic  via Read Attribute request: " + key + " EPout = " + "01, 03, 07" )
        ReadAttributeReq( self, key, EPin, "01", "0000", listAttributes )
        ReadAttributeReq( self, key, EPin, "03", "0000", listAttributes )
        ReadAttributeReq( self, key, EPin, "09", "0000", listAttributes )
    else:
        for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0000" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                EPout= tmpEp 
        Domoticz.Debug("Request Basic  via Read Attribute request: " + key + " EPout = " + EPout )
        ReadAttributeReq( self, key, EPin, EPout, "0000", listAttributes )

def ReadAttributeRequest_Ack(self, key):

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
    listAttributes.append(0x0000)        # Mains information
    listAttributes.append(0x0010)        # Battery Voltage
    listAttributes.append(0x0020)        # Battery Voltage
    listAttributes.append(0x0021)        # Battery BatteryPercentageRemaining

    Domoticz.Log("Request Power Config via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, EPin, EPout, "0001", listAttributes )

def ReadAttributeRequest_0300(self, key):
    # Cluster 0x0300 - Color Control

    Domoticz.Debug("ReadAttributeRequest_0300 - Key: %s " %key)
    EPin = "01"
    EPout= "01"

    listAttributes = []
    listAttributes.append(0x0000)   # CurrentHue
    listAttributes.append(0x0001)   # CurrentSaturation
    listAttributes.append(0x0003)   # CurrentX
    listAttributes.append(0x0004)   # CurrentY
    listAttributes.append(0x0008)   # ColorMode

    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0300" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    Domoticz.Debug("Request Color Temp infos via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, EPin, EPout, "0300", listAttributes)


def ReadAttributeRequest_0006(self, key):
    # Cluster 0x0006

    Domoticz.Debug("ReadAttributeRequest_0006 - Key: %s " %key)

    EPin = "01"
    EPout= "01"

    listAttributes = []
    listAttributes.append(0x0000)

    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0006" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp

    Domoticz.Debug("Request OnOff status via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, "01", EPout, "0006", listAttributes)


def ReadAttributeRequest_0008(self, key):
    # Cluster 0x0008 

    Domoticz.Debug("ReadAttributeRequest_0008 - Key: %s " %key)

    EPin = "01"
    EPout= "01"
    listAttributes = []
    listAttributes.append(0x0000)

    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0008" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp

    Domoticz.Debug("Request Control level of shutter via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, "01", EPout, "0008", 0)

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

def ReadAttributeRequest_0702(self, key):
    # Cluster 0x0702 Metering

    Domoticz.Log("ReadAttributeRequest_0702 - Key: %s " %key)

    listAttributes = []
    listAttributes.append(0x0000) # Current Summation Delivered
    listAttributes.append(0x0200) # Status
    listAttributes.append(0x0301) # Multiplier
    listAttributes.append(0x0302) # Diviser
    listAttributes.append(0x0400) # Instantaneous Demand

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0702" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp

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
        sendZigateCmd(self, "0026", str(self.ZigateIEEE) + str(IEEE) )
    else:
        Domoticz.Log("removeZigateDevice - cannot remove due to unknown Zigate IEEE: ")

    return

def getListofAttribute(self, nwkid, EpOut, cluster):

    datas = "{:02n}".format(2) + nwkid + "01" + EpOut + cluster + "00" + "00" + "0000" + "FF"
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
            # 0x0E10 - 3600s A hour
            # 0x0708 - 30'
            # 0x0384 - 15'
            # 0x012C - 5'
            # 0x003C - 1'
        '0001': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'012C', 'MaxInterval':'FFFE', 'TimeOut':'0000','Change':'01'},
                                 '0020': {'DataType': '29', 'MinInterval':'0E10', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0021': {'DataType': '29', 'MinInterval':'0E10', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'}}},
        # On/Off
        '0006': {'Attributes': { '0000': {'DataType': '10', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}},
        # Level Control
        '0008': {'Attributes': { '0000': {'DataType': '20', 'MinInterval':'0005', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'05'}}},
        # Binary Input 
        #'000f': {'Attributes': { '0055': {'DataType': '39', 'MinInterval':'000A', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}},
        # Thermostat
        '0201': {'Attributes': { '0000': {'DataType': '29', 'MinInterval':'012C', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'},
                                 '0011': {'DataType': '29', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0012': {'DataType': '29', 'MinInterval':'012C', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'}}},
        # Colour Control
        '0300': {'Attributes': { '0007': {'DataType': '21', 'MinInterval':'0384', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'},
                                 '0000': {'DataType': '20', 'MinInterval':'0384', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0001': {'DataType': '20', 'MinInterval':'0384', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0003': {'DataType': '21', 'MinInterval':'0384', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0004': {'DataType': '21', 'MinInterval':'0384', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0008': {'DataType': '30', 'MinInterval':'0384', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'}}},
        # Illuminance Measurement
        '0400': {'Attributes': { '0000': {'DataType': '29', 'MinInterval':'0005', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'0F'}}},
        # Temperature
        '0402': {'Attributes': { '0000': {'DataType': '29', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},
        # Pression Atmo
        '0403': {'Attributes': { '0000': {'DataType': '20', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'},
                                 '0010': {'DataType': '29', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},
        # Humidity
        '0405': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},
        # Occupancy Sensing
        #'0406': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},
        # IAS ZOne
        '0500': {'Attributes': { '0000': {'DataType': '30', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'},
                                 '0001': {'DataType': '31', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'},
                                 '0002': {'DataType': '19', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},
        # Occupancy Sensing

        # Power
        '0702': {'Attributes': { '0000': {'DataType': '25', 'MinInterval':'FFFF', 'MaxInterval':'0000', 'TimeOut':'0000','Change':'00'},
                                 '0400': {'DataType': '2a', 'MinInterval':'003C', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}}
        }

    now = int(time())
    if NWKID is None :
        if self.busy or len(self.ZigateComm._normalQueue) > 2:
            Domoticz.Log("configureReporting - skip configureReporting for now ... system too busy (%s/%s) for %s"
                  %(self.busy, len(self.ZigateComm._normalQueue), NWKID))
            return # Will do at the next round
        target = self.ListOfDevices
    else:
        target = NWKID
        Domoticz.Debug("configureReporting for device : %s => %s" %(NWKID, self.ListOfDevices[NWKID]))

    for key in target:
        # Let's check that we can do a Configure Reporting. Only during the pairing process (NWKID is provided) or we are on the Main Power
        if key == '0000': continue
        if NWKID is None and 'PowerSource' in self.ListOfDevices[key]:
            if self.ListOfDevices[key]['PowerSource'] != 'Main': continue
        else: continue
        # We reach here because we have either a NWKID (we are pairing phase and we have a window to talk to the device even on battery mode

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
            clusterList = getClusterListforEP( self, key, Ep )
            for cluster in clusterList:
                if cluster in ( 'Type', 'ColorMode'):
                    continue

                if 'ConfigureReporting' in self.ListOfDevices[key]:
                    if Ep in self.ListOfDevices[key]['ConfigureReporting']['Ep']:
                        if str(cluster) in self.ListOfDevices[key]['ConfigureReporting']['Ep'][Ep]:
                            if self.ListOfDevices[key]['ConfigureReporting']['Ep'][Ep][str(cluster)] != '00' and \
                                    self.ListOfDevices[key]['ConfigureReporting']['Ep'][Ep][str(cluster)] != {} :
                                continue
                        else:
                            self.ListOfDevices[key]['ConfigureReporting']['Ep'][Ep][str(cluster)] = {}
                    else:
                        self.ListOfDevices[key]['ConfigureReporting']['Ep'][Ep] = {}
                        self.ListOfDevices[key]['ConfigureReporting']['Ep'][Ep][str(cluster)] = {}
                else:
                    self.ListOfDevices[key]['ConfigureReporting'] = {}
                    self.ListOfDevices[key]['ConfigureReporting']['Ep'] = {}
                    self.ListOfDevices[key]['ConfigureReporting']['Ep'][Ep] = {}
                    self.ListOfDevices[key]['ConfigureReporting']['Ep'][Ep][str(cluster)] = {}
                    self.ListOfDevices[key]['ConfigureReporting']['Ep'][Ep][str(cluster)] = ''

                _idx = Ep + '-' + str(cluster)
                if 'TimeStamps' not in self.ListOfDevices[key]['ConfigureReporting'] :
                    self.ListOfDevices[key]['ConfigureReporting']['TimeStamps'] = {}
                    self.ListOfDevices[key]['ConfigureReporting']['TimeStamps'][_idx] = 0
                else:
                    if _idx not in self.ListOfDevices[key]['ConfigureReporting']['TimeStamps']:
                        self.ListOfDevices[key]['ConfigureReporting']['TimeStamps'][_idx] = 0

                if  self.ListOfDevices[key]['ConfigureReporting']['TimeStamps'][_idx] != {}:
                     if now <= ( self.ListOfDevices[key]['ConfigureReporting']['TimeStamps'][_idx] + (24 * 3600)):  # Do only every day
                         continue

                if cluster in ATTRIBUTESbyCLUSTERS:
                    Domoticz.Log('Processing configureReporting for %s cluuster: %s' %(key,cluster))

                    if self.busy or len(self.ZigateComm._normalQueue) > 2:
                        Domoticz.Log("configureReporting - skip configureReporting for now ... system too busy (%s/%s) for %s"
                            %(self.busy, len(self.ZigateComm._normalQueue), key))
                        return # Will do at the next round

                    bindDevice( self, self.ListOfDevices[key]['IEEE'], Ep, cluster )

                    self.ListOfDevices[key]['ConfigureReporting']['TimeStamps'][_idx] = int(time())

                    attrDisp = []   # Used only for printing purposes
                    attrList = ''
                    attrLen = 0
                    for attr in ATTRIBUTESbyCLUSTERS[cluster]['Attributes']:
                        attrdirection = "00"
                        attrType = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['DataType']
                        minInter = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['MinInterval']
                        maxInter = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['MaxInterval']
                        timeOut = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['TimeOut']
                        chgFlag = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['Change']
                        attrList = attrdirection + attrType + attr + minInter + maxInter + timeOut + chgFlag
                        #attrLen = 1

                        attrList += attrdirection + attrType + attr + minInter + maxInter + timeOut + chgFlag
                        attrLen += 1
                        attrDisp.append(attr)

                        #datas =   addr_mode + key + "01" + Ep + cluster + direction + manufacturer_spec + manufacturer 
                        #datas +=  "%02x" %(attrLen) + attrList
                        #Domoticz.Debug("configureReporting - for [%s] - cluster: %s on Attribute: %s " %(key, cluster, attr) )
                        #sendZigateCmd(self, "0120", datas )

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

        Domoticz.Log("bindDevice - ieee: %s, ep: %s, cluster: %s, Zigate_ieee: %s, Zigate_ep: %s" %(ieee,ep,cluster,destaddr,destep) )
        datas =  str(ieee)+str(ep)+str(cluster)+str(mode)+str(destaddr)+str(destep) 
        sendZigateCmd(self, "0030", datas )
    else:
        Domoticz.Log("bindDevice - %s/%s - %s already done at %s" %(ieee, ep, cluster, self.ListOfDevices[nwkid]['Bind'][cluster]['Stamp']))

    return


def unbindDevice( self, ieee, ep, cluster, addmode, destaddr=None, destep="01"):
    '''
    unbind
    '''

    return

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
    

def identifySend( self, nwkid, ep, duration=0):

    datas = "02" + "%s"%(nwkid) + "01" + ep + "%04x"%(duration) 
    Domoticz.Debug("identifySend - send an Identify Message to: %s for %04x seconds" %( nwkid, duration))
    Domoticz.Debug("identifySend - data sent >%s< " %(datas) )
    sendZigateCmd(self, "0070", datas )

def maskChannel( channel ):
    CHANNELS = { 0: 0x00000000, # Scan for all channels
            11: 0x00000800,
            12: 0x00001000,
            13: 0x00002000,
            14: 0x00004000,
            15: 0x00008000,
            16: 0x00010000,
            17: 0x00020000,
            18: 0x00040000,
            19: 0x00080000,
            20: 0x00100000,
            21: 0x00200000,
            22: 0x00400000,
            23: 0x00800000,
            24: 0x01000000,
            25: 0x02000000,
            26: 0x04000000 }

    mask = 0x00000000
    Domoticz.Debug("setChannel - Channel list: %s" %(channel))
    if isinstance(channel, list):
        for c in channel:
            if c.isdigit():
                if c in ( '0', '11','12','13','14','15','16','17','18','19','20','21','22','23','24','25','26'):
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
    # 0x00 - 0x05 :  Time in Second
    # 0x60 - 0xFD : Reserved
    # 0xFE        : Change radio channel to single channel specified through channel
    # 0xFF        : Update the stored radio channel mask
    # Scan count:
    #    Scan repeats 0 – 5
    # Network Update ID:
    #    0 – 0xFF Transaction ID for scan

    # Scan Duration
    if mode == 'scan':
        scanDuration = 0x05 # 2 seconds
    elif mode == 'change':
        scanDuration = 0xFE # Change radio channel
    elif mode == 'update':
        scanDuration = 0xFF # Update stored radui
    else:
        Domoticz.Log("NwkMgtUpdReq Unknown mode %s" %mode)
        return

    scanCount = 1

    mask = maskChannel( channel )
    Domoticz.Debug("NwkMgtUpdReq - Channel targeted: %08.x " %(mask))

    datas = "0000" + "%08.x" %(mask) + "%02.x" %(scanDuration) + "%02.x" %(scanCount) + "01" + "0000"
    if mode == 'scan':
        Domoticz.Log("NwkMgtUpdReq - %s channel(s): %04.x duration: %02.x count: %s >%s<" \
                %( mode, mask, scanDuration, scanCount, datas) )
    elif mode in ('change', 'update'):
        Domoticz.Log("NwkMgtUpdReq - %s channel(s): %04.x" \
                %( mode, mask ) )

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

    datas = "%016.x" %(extPANID)
    Domoticz.Log("set ExtendedPANID - %16.x "\
            %( extPANID) )
    sendZigateCmd(self, "0020", datas )



def leaveMgtReJoin( self, saddr, ieee):
    ' in case of receiving a leave, and that is not related to an explicit remove '

    if self.permitTojoin != 0xff:
        Domoticz.Log("Switch to Permit to Join for 30s")
        discover = "%02.X" %int(30)
        sendZigateCmd(self, "0049","FFFC" + discover + "00")

    Domoticz.Log("leaveMgt - sAddr: %s , ieee: %s" %( saddr, ieee))
    # Request a Re-Join and Do not remove children
    datas = saddr + ieee + '01' + '00'
    sendZigateCmd(self, "0047", datas )

def thermostat_Setpoint( self, key, setpoint):

    manuf_id = "0000"
    manuf_spec = "00"
    cluster_id = "%04x" %0x0201
    Hattribute = "%04x" %0x0012
    data_type = "29" # Int16
    Hdata = "%04x" %setpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp

    Domoticz.Log("thermostat_Setpoint - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,Hdata,cluster_id,Hattribute,data_type))
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, Hattribute, data_type, Hdata)

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
    Domoticz.Log("thermostat_Calibration - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,attribute,data_type))

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
    attribute = "%04x" %0x001F
    data_type = "30" # Enum8
    data = "%02x" %SYSTEM_MODE[mode]

    EPout = '01'
    for tmpEp in self.ListOfDevices[key]['Ep']:
        if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]:
            EPout= tmpEp
    write_attribute( self, key, "01", EPout, cluster_id, manuf_id, manuf_spec, attribute, data_type, data)
    Domoticz.Log("thermostat_Mode - for %s with value %s / cluster: %s, attribute: %s type: %s"
            %(key,data,cluster_id,attribute,data_type))

def ReadAttributeRequest_0201(self, key):

    Domoticz.Log("ReadAttributeRequest_0201 - Key: %s " %key)
    # Power Config
    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0201" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp

    # Thermostat Information
    listAttributes = []
    listAttributes.append(0x0000)        # Local Temp / 0x29
    listAttributes.append(0x0010)        # Calibration / 0x28
    listAttributes.append(0x0011)        # COOLING_SETPOINT / 0x29
    listAttributes.append(0x0012)        # HEATING_SETPOINT / 0x29
    listAttributes.append(0x0015)        # MIN HEATING / 0x29
    listAttributes.append(0x0016)        # MAX HEATING / 0x29
    Domoticz.Debug("Request 0201 %s/%s-%s 0201 %s " %(key, EPin, EPout, listAttributes))
    ReadAttributeReq( self, key, EPin, EPout, "0201", listAttributes )
