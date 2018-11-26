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
import time
import struct
import json
import queue

import z_var
import z_tools

import time

def ZigateConf_light(self, discover ):
    '''
    It is called for normal startup
    '''
    sendZigateCmd(self, "0010", "") # Get Firmware version

    Domoticz.Debug("ZigateConf -  Request: Get List of Device " + str(self.FirmwareVersion))
    sendZigateCmd(self, "0015", "")

    utctime = int(time.time())
    Domoticz.Status("ZigateConf - Setting UTC Time to : %s" %( utctime) )
    sendZigateCmd(self, "0016", str(utctime) )

    sendZigateCmd(self, "0009", "") # In order to get Zigate IEEE and NetworkID

    Domoticz.Status("Start network")
    sendZigateCmd(self, "0024", "" )   # Start Network

    if str(discover) != "0":
        if str(discover)=="255": 
            Domoticz.Status("Zigate enter in discover mode for ever")
        else: 
            Domoticz.Status("Zigate enter in discover mode for " + str(discover) + " Secs" )
        sendZigateCmd(self, "0049","FFFC" + hex(int(discover))[2:4] + "00")

    Domoticz.Debug("Request network Status")
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

    Domoticz.Debug("ReadAttributeReq - addr =" +str(addr) +" Cluster = " +str(Cluster) +" Attributes = " +str(ListOfAttributes) ) 
    if not isinstance(ListOfAttributes, list):
        # We received only 1 attribute
        Attr = "%04x" %(ListOfAttributes)
        lenAttr = 1
        weight = 1
    else:
        lenAttr = len(ListOfAttributes)
        weight = int ((lenAttr ) / 2) + 1
        Attr =''
        Domoticz.Debug("attributes: " +str(ListOfAttributes) +" len =" +str(lenAttr) )
        for x in ListOfAttributes:
            Attr += "%04x" %(x)

    direction = '00'
    manufacturer_spec = '00'
    manufacturer = '0000'
    #if 'Manufacturer' in self.ListOfDevices[addr]:
    #    manufacturer = self.ListOfDevices[addr]['Manufacturer']

    datas = "02" + addr + EpIn + EpOut + Cluster + direction + manufacturer_spec + manufacturer + "%02x" %(lenAttr) + Attr
    sendZigateCmd(self, "0100", datas )

def ReadAttributeRequest_0000(self, key):
    # Basic Cluster
    # The Ep to be used can be challenging, as if we are in the discovery process, the list of Eps is not yet none and it could even be that the Device has only 1 Ep != 01

    EPin = "01"
    EPout= "01"

    # General
    listAttributes = []
    listAttributes.append(0x0001)        # Application Version
    listAttributes.append(0x0002)        # Stack Version
    listAttributes.append(0x0003)        # HW Version
    listAttributes.append(0x0004)        # Model Identifier
    listAttributes.append(0x0005)        # Model Identifier
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

def ReadAttributeRequest_0001(self, key):
    # Power Config
    EPin = "01"
    EPout= "01"
    listAttributes = []
    listAttributes.append(0x0000)        # Mains information
    listAttributes.append(0x0001)        # Mains Settings
    listAttributes.append(0x0002)        # Battery Information
    listAttributes.append(0x0003)        # Battery Settings
    listAttributes.append(0x0004)        # Battery Source 2 Information
    listAttributes.append(0x0005)        # Battery Source 2 Settings
    listAttributes.append(0x0006)        # Battery Source 3 Information
    listAttributes.append(0x0007)        # Battery Source 3 Settings
    listAttributes.append(0x0020)        # Battery Voltage
    listAttributes.append(0x0021)        # Battery BatteryPercentageRemaining

    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0001" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp

    Domoticz.Debug("Request Power Config via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, EPin, EPout, "0001", listAttributes )

def ReadAttributeRequest_0300(self, key):
    # Cluster 0x0300 - Color Control

    EPin = "01"
    EPout= "01"

    listAttributes = []
    listAttributes.append(0x0000)   # CurrentHue
    listAttributes.append(0x0001)   # CurrentSaturation
    listAttributes.append(0x0003)   # CurrentX
    listAttributes.append(0x0004)   # CurrentY
    listAttributes.append(0x0005)   # DriftCompensation
    listAttributes.append(0x0006)   # CompensationText
    listAttributes.append(0x0007)   # ColorTemperatureMireds
    listAttributes.append(0x0008)   # ColorMode

    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0300" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp
    Domoticz.Debug("Request Color Temp infos via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, EPin, EPout, "0300", listAttributes)


def ReadAttributeRequest_0006(self, key):
    # Cluster 0x0006
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

def removeZigateDevice( self, IEEE ):
    # remove a device in Zigate
    # Key is the short address of the device
    # extended address is ieee address
    if self.ZigateIEEE != None:
        Domoticz.Log("Remove from Zigate Device = " + " IEEE = " +str(IEEE) )
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
        if they support Cluster we want to configure Reporting and if they have Manufacturer Id then configureReporting

    Format configure Reporting Zigate command

        Address Mode  : u8
        Network Address: u16
        Source EP     : u8
        Dest   EP     : u8
        ClusterId     : u16
        Direction     : u8
        Manufacturer spe: u8
        Manufacturer Id: u16
        Nb attributes : u8
        Attribute list: 72 each
            Attribute direc: u8
            Attribute Type: u8
            Min Interval  : u16
            Max Interval  : u16
            TimeOut       : u16
            Change        : u8

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
        '000f': {'Attributes': { '0055': {'DataType': '39', 'MinInterval':'000A', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}},
        # Colour Control
        '0300': {'Attributes': { '0007': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'},
                                 '0000': {'DataType': '20', 'MinInterval':'0E10', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0001': {'DataType': '20', 'MinInterval':'0E10', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0003': {'DataType': '21', 'MinInterval':'0E10', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0004': {'DataType': '21', 'MinInterval':'0E10', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0008': {'DataType': '30', 'MinInterval':'0E10', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'}}},
        # Illuminance Measurement
        '0400': {'Attributes': { '0000': {'DataType': '29', 'MinInterval':'0005', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'0F'}}},
        # Temperature
        '0402': {'Attributes': { '0000': {'DataType': '29', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},
        # Pression Atmo
        '0403': {'Attributes': { '0000': {'DataType': '20', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},
                                 '0010': {'DataType': '29', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'},
        # Humidity
        '0405': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'003C', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},
        # Occupancy Sensing
        #'0406': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'0384', 'TimeOut':'0FFF','Change':'01'}}},
        # Power
        '0702': {'Attributes': { '0000': {'DataType': '25', 'MinInterval':'FFFF', 'MaxInterval':'0000', 'TimeOut':'0000','Change':'00'},
                                 '0400': {'DataType': '2a', 'MinInterval':'003C', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}}
        #'0702': {'Attributes': { '0400': {'DataType': '2a', 'MinInterval':'0001', 'MaxInterval':'012C', 'TimeOut':'0FFF','Change':'01'}}}
        }

    if NWKID is None :
        target = self.ListOfDevices
    else:
        target = NWKID
        Domoticz.Debug("configureReporting for device : %s => %s" %(NWKID, self.ListOfDevices[NWKID]))

    for key in target:
        # Let's check that we can do a Configure Reporting. Only during the pairing process (NWKID is provided) or we are on the Main Power
        if NWKID is None and 'PowerSource' in self.ListOfDevices[key]:
            if self.ListOfDevices[key]['PowerSource'] != 'Main': continue
        else: continue
        # We reach here because we have either a NWKID (we are pairing phase and we have a window to talk to the device even on battery mode

        manufacturer = "0000"
        if 'Manufacturer' in self.ListOfDevices[key]:
            manufacturer = self.ListOfDevices[key]['Manufacturer']
        manufacturer_spec = "00"
        direction = "00"
        addr_mode = "02"

        for Ep in self.ListOfDevices[key]['Ep']:
            if NWKID is None:
                identifySend( self, key, Ep, 0)
            else:
                identifySend( self, key, Ep, 15)
            clusterList = z_tools.getClusterListforEP( self, key, Ep )
            for cluster in clusterList:
                if cluster in ATTRIBUTESbyCLUSTERS:
                    bindDevice( self, self.ListOfDevices[key]['IEEE'], Ep, cluster )
                    #attrDisp = []   # Used only for printing purposes
                    #attrList = ''
                    attrLen = 0
                    for attr in ATTRIBUTESbyCLUSTERS[cluster]['Attributes']:
                        attrdirection = "00"
                        attrType = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['DataType']
                        minInter = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['MinInterval']
                        maxInter = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['MaxInterval']
                        timeOut = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['TimeOut']
                        chgFlag = ATTRIBUTESbyCLUSTERS[cluster]['Attributes'][attr]['Change']
                        attrList = attrdirection + attrType + attr + minInter + maxInter + timeOut + chgFlag
                        #attrList += attrdirection + attrType + attr + minInter + maxInter + timeOut + chgFlag
                        attrLen = 1
                        #attrLen += 1
                        #attrDisp.append(attr)
                        #Domoticz.Log("configureReporting - %2d %s " %(attrLen, attrList) )
                        datas =   addr_mode + key + "01" + Ep + cluster + direction + manufacturer_spec + manufacturer 
                        datas +=  "%02x" %(attrLen) + attrList
                        Domoticz.Debug("configureReporting - for [%s] - cluster: %s on Attribute: %s " %(key, cluster, attr) )
                        sendZigateCmd(self, "0120", datas )

                    #datas =   addr_mode + key + "01" + Ep + cluster + direction + manufacturer_spec + manufacturer 
                    ##datas +=  "%02x" %(attrLen) + attrList
                    #Domoticz.Status("configureReporting - for [%s] - cluster: %s on Attribute: %s " %(key, cluster, attrDisp) )
                    #Domoticz.Log("configureReporting for [%s] - cluster: %s on Attribute: %s >%s< " %(key, cluster, attrDisp, datas) )
                    #sendZigateCmd(self, "0120", datas )
    
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

    Domoticz.Debug("bindDevice - ieee: %s, ep: %s, cluster: %s, dest_ieee: %s, desk_ep: %s" %(ieee,ep,cluster,destaddr,destep) )
    datas =  str(ieee)+str(ep)+str(cluster)+str(mode)+str(destaddr)+str(destep) 
    sendZigateCmd(self, "0030", datas )

    return


def unbindDevice( self, ieee, ep, cluster, addmode, destaddr=None, destep="01"):
    '''
    unbind
    '''

    return

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
    Domoticz.Debug("setChannel - Channel set to : %08.x " %(mask))

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
    Domoticz.Log("NwkMgtUpdReq - %s channel(s): %04.x duration: %02.x count: %s >%s<" \
            %( mode, mask, scanDuration, scanCount, datas) )
    sendZigateCmd(self, "004A", datas )
    return

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
