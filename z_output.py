#!/usr/bin/env python3
# coding: utf-8 -*-
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

def ZigateConf_light(self,  channel, discover ):
    '''
    It is called for normal startup
    '''
    sendZigateCmd(self, "0010", "") # Get Firmware version

    Domoticz.Debug("ZigateConf -  Request: Get List of Device " + str(self.FirmwareVersion))
    sendZigateCmd(self, "0015", "")

    utctime = int(time.time())
    Domoticz.Log("ZigateConf - seting Time to : %s" %( utctime) )
    sendZigateCmd(self, "0016", str(utctime) )

    sendZigateCmd(self, "0009", "") # In order to get Zigate IEEE and NetworkID

    Domoticz.Status("Start network")
    sendZigateCmd(self, "0024", "" , 2 )   # Start Network

    if str(discover) != "0":
        if str(discover)=="255": 
            Domoticz.Status("Zigate enter in discover mode for ever")
        else: 
            Domoticz.Status("Zigate enter in discover mode for " + str(discover) + " Secs" )
        sendZigateCmd(self, "0049","FFFC" + hex(int(discover))[2:4] + "00", 2)

    Domoticz.Debug("Request network Status")
    sendZigateCmd( self, "0014", "", 2 ) # Request status


def ZigateConf(self, channel, discover ):
    '''
    Called after Erase
    '''
    ################### ZiGate - get Firmware version #############
    # answer is expected on message 8010
    sendZigateCmd(self, "0010","",1)

    ################### ZiGate - Set Type COORDINATOR #################
    sendZigateCmd(self, "0023","00", 1)

    ################### ZiGate - set channel ##################
    sendZigateCmd(self, "0021", "0000" + z_tools.returnlen(2,hex(int(channel))[2:4]) + "00", 2)

    ################### ZiGate - start network ##################
    sendZigateCmd(self, "0024","", 1)

    sendZigateCmd(self, "0009","") # In order to get Zigate IEEE and NetworkID

    ################### ZiGate - Request Device List #############
    # answer is expected on message 8015. Only available since firmware 03.0b
    Domoticz.Debug("ZigateConf -  Request: Get List of Device " + str(self.FirmwareVersion) )
    sendZigateCmd(self, "0015","",2)

    ################### ZiGate - discover mode 255 sec Max ##################
    #### Set discover mode only if requested - so != 0                  #####
    if str(discover) != "0":
        if str(discover)=="255": 
            Domoticz.Status("Zigate enter in discover mode for ever")
        else: 
            Domoticz.Status("Zigate enter in discover mode for " + str(discover) + " Secs" )
        sendZigateCmd(self, "0049","FFFC" + hex(int(discover))[2:4] + "00", 2)

    Domoticz.Debug("Request network Status")
    sendZigateCmd( self, "0014", "", 2 ) # Request status
        
def sendZigateCmd(self, cmd,datas, _weight=1 ):
    def ZigateEncode(Data):  # ajoute le transcodage
        Domoticz.Debug("ZigateEncode - Encodind data: " + Data)
        Out=""
        Outtmp=""
        Transcode = False
        for c in Data:
            Outtmp+=c
            if len(Outtmp)==2:
                if Outtmp[0] == "1" and Outtmp != "10":
                    if Outtmp[1] == "0":
                        Outtmp="0200"
                        Out+=Outtmp
                    else:
                        Out+=Outtmp
                elif Outtmp[0] == "0":
                    Out+="021" + Outtmp[1]
                else:
                    Out+=Outtmp
                Outtmp=""
        Domoticz.Debug("Transcode in: " + str(Data) + "  / out:" + str(Out) )
        return Out

    def getChecksum(msgtype,length,datas):
        temp = 0 ^ int(msgtype[0:2],16)
        temp ^= int(msgtype[2:4],16)
        temp ^= int(length[0:2],16)
        temp ^= int(length[2:4],16)
        for i in range(0,len(datas),2):
            temp ^= int(datas[i:i+2],16)
            chk=hex(temp)
        Domoticz.Debug("getChecksum - Checksum: " + str(chk))
        return chk[2:4]


    command = {}
    command['cmd'] = cmd
    command['datas'] = datas

    if datas == "":
        length="0000"
    else:
        length=z_tools.returnlen(4,(str(hex(int(round(len(datas)/2)))).split('x')[-1]))  # by Cortexlegeni 
        Domoticz.Debug("sendZigateCmd - length is: " + str(length) )
    if datas =="":
        checksumCmd=getChecksum(cmd,length,"0")
        if len(checksumCmd)==1:
            strchecksum="0" + str(checksumCmd)
        else:
            strchecksum=checksumCmd
        lineinput="01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + str(ZigateEncode(strchecksum)) + "03" 
    else:
        checksumCmd=getChecksum(cmd,length,datas)
        if len(checksumCmd)==1:
            strchecksum="0" + str(checksumCmd)
        else:
            strchecksum=checksumCmd
        lineinput="01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + str(ZigateEncode(strchecksum)) + str(ZigateEncode(datas)) + "03"   
    Domoticz.Debug("sendZigateCmd - Command send: " + str(lineinput))

    # Compute the Delay based on the weight of the command and the current queue
    # For instance if queue is empty , you can engage the command immediatly
    # _weight

    if z_var.cmdInProgress.qsize() == 0:     # reset Delay to 0 as we don't have any more request in the pipe
        delay = 0            # Allow immediate execution, and reset to default the liveSendDelay
        z_var.liveSendDelay = z_var.sendDelay 
    else:                    # Compute delay with _weight 
        delay = ( z_var.sendDelay * _weight) * ( z_var.cmdInProgress.qsize() )
        if delay < z_var.liveSendDelay:    # If the computed Delay is lower than previous, we must stay on the last one until queue is empty
            delay =  z_var.liveSendDelay
        else:
            z_var.liveSendDelay = delay

    z_var.cmdInProgress.put( command )
    Domoticz.Debug("sendZigateCmd - Command in queue: " + str( z_var.cmdInProgress.qsize() ) )
    if z_var.cmdInProgress.qsize() > 30:
        Domoticz.Debug("sendZigateCmd - Command in queue: > 30 - queue is: " + str( z_var.cmdInProgress.qsize() ) )
        Domoticz.Debug("sendZigateCmd(self, ) - Computed delay is: " + str(delay) + " liveSendDelay: " + str( z_var.liveSendDelay) + " based on _weight = " +str(_weight) + " sendDelay = " + str(z_var.sendDelay) + " Qsize = " + str(z_var.cmdInProgress.qsize()) )

    Domoticz.Debug("sendZigateCmd(self, ) - Computed delay is: " + str(delay) + " liveSendDelay: " + str( z_var.liveSendDelay) + " based on _weight = " +str(_weight) + " sendDelay = " + str(z_var.sendDelay) + " Qsize = " + str(z_var.cmdInProgress.qsize()) )

    if str(z_var.transport) == "USB" or str(z_var.transport) == "Wifi":
        z_var.ZigateConn.Send(bytes.fromhex(str(lineinput)), delay )
        self.stats['send'] += 1


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
    Domoticz.Debug("ReadAttributeReq - %s" %( datas) )
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
    listAttributes.append(0x0005)        # Model Identifier
    listAttributes.append(0x0007)        # Power Source
    listAttributes.append(0x0010)        # Battery

    # Checking if Ep list is empty, in that case we are in discovery mode and we don't really know what are the EPs we can talk to.
    if self.ListOfDevices[key]['Ep'] is None or self.ListOfDevices[key]['Ep'] == {} :
        Domoticz.Log("Request Basic  via Read Attribute request: " + key + " EPout = " + "01, 03, 07" )
        ReadAttributeReq( self, key, EPin, "01", "0000", listAttributes )
        ReadAttributeReq( self, key, EPin, "03", "0000", listAttributes )
        ReadAttributeReq( self, key, EPin, "09", "0000", listAttributes )

    else:
        for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0000" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                EPout= tmpEp 
        Domoticz.Log("Request Basic  via Read Attribute request: " + key + " EPout = " + EPout )
        ReadAttributeReq( self, key, EPin, EPout, "0000", listAttributes )

def ReadAttributeRequest_0001(self, key):
    # Power Config
    EPin = "01"
    EPout= "01"
    listAttributes = []
    listAttributes.append(0x0000)        # Voltage
    listAttributes.append(0x0010)        # Battery Voltage
    listAttributes.append(0x0020)        # Battery %

    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0001" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp

    Domoticz.Debug("Request Power Config via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, EPin, EPout, "0001", listAttributes )

def ReadAttributeRequest_0300(self, key):

    EPin = "01"
    EPout= "01"

    listAttributes = []
    listAttributes.append(0x0007) 

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

    Domoticz.Log("Request OnOff status for Xiaomi plug via Read Attribute request: " + key + " EPout = " + EPout )
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
    Domoticz.Log("Request 0x000c info via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, "01", EPout, "000C", listAttributes)

def ReadAttributeRequest_0702(self, key):
    # Cluster 0x0702 Metering

    listAttributes = []
    listAttributes.append(0x0000) # Current Summation Delivered
    listAttributes.append(0x0200) # Status
    listAttributes.append(0x0301) # 
    listAttributes.append(0x0302) # 
    listAttributes.append(0x0400) # Instantaneous Demand

    EPin = "01"
    EPout= "01"
    for tmpEp in self.ListOfDevices[key]['Ep']:
            if "0702" in self.ListOfDevices[key]['Ep'][tmpEp]: #switch cluster
                    EPout=tmpEp

    Domoticz.Log("Request Metering info via Read Attribute request: " + key + " EPout = " + EPout )
    ReadAttributeReq( self, key, EPin, EPout, "0702", listAttributes)

def removeZigateDevice( self, key ):
    # remove a device in Zigate
    # Key is the short address of the device
    # extended address is ieee address

    if key in  self.ListOfDevices:
        ieee =  self.ListOfDevices[key]['IEEE']
        Domoticz.Log("Remove from Zigate Device = " + str(key) + " IEEE = " +str(ieee) )
        sendZigateCmd(self, "0026", str(ieee) + str(ieee) )
    else:
        Domoticz.Log("Unknow device to be removed - Device  = " + str(key))

    return

def getListofAttribute(self, nwkid, EpOut, cluster):

    datas = "{:02n}".format(2) + nwkid + "01" + EpOut + cluster + "00" + "00" + "0000" + "FF"
    Domoticz.Log("attribute_discovery_request - " +str(datas) )
    sendZigateCmd(self, "0140", datas , 2 )



def processConfigureReporting( self ):
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
        Attribute list: u16 each
        Attribute direc: u8
        Attribute Type: u8
        Min Interval  : u16
        Max Interval  : u16
        TimeOut       : u16
        Change          : u8

    '''

    ATTRIBUTESbyCLUSTERS = {
            # 0xFFFF sable reporting-
            # 0x0E10 - 3600s A hour
            # 0x0384 - 15'
            # 0x012C - 5'
            # 0x003C - 1'
        '0001': {'Attributes': { '0000': {'DataType': '21', 'MinInterval':'0001', 'MaxInterval':'FFFE', 'TimeOut':'0000','Change':'01'}}},
        '0008': {'Attributes': { '0000': {'DataType': '20', 'MinInterval':'0005', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'05'}}},
        '0006': {'Attributes': { '0000': {'DataType': '10', 'MinInterval':'0001', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'}}},
        #'000c': {'Attributes': { '0055': {'DataType': '39', 'MinInterval':'0001', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'}}},
        #'8021': {'Attributes': { '0000': {'DataType': '39', 'MinInterval':'0001', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'}}},
        #'0402': {'Attributes': { '0000': {'DataType': '37', 'MinInterval':'0001', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'}}},
        '0702': {'Attributes': { '0000': {'DataType': '25', 'MinInterval':'0001', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0200': {'DataType': '18', 'MinInterval':'0001', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0301': {'DataType': '22', 'MinInterval':'0001', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0302': {'DataType': '22', 'MinInterval':'0001', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'},
                                 '0400': {'DataType': '2a', 'MinInterval':'0001', 'MaxInterval':'0E10', 'TimeOut':'0FFF','Change':'01'}}}
        }

    for key in self.ListOfDevices:
        if 'PowerSource' in self.ListOfDevices[key]:
            if self.ListOfDevices[key]['PowerSource'] != 'Main': continue
        else: continue

        manufacturer = "0000"
        if 'Manufacturer' in self.ListOfDevices[key]:
            manufacturer = self.ListOfDevices[key]['Manufacturer']
        manufacturer_spec = "00"
        direction = "00"
        addr_mode = "02"

        for Ep in self.ListOfDevices[key]['Ep']:
            identifySend( self, key, Ep)

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
                        Domoticz.Status("configureReporting - for [%s] - cluster: %s on Attribute: %s " %(key, cluster, attr) )
                        sendZigateCmd(self, "0120", datas , 2)

                    #datas =   addr_mode + key + "01" + Ep + cluster + direction + manufacturer_spec + manufacturer 
                    ##datas +=  "%02x" %(attrLen) + attrList
                    #Domoticz.Status("configureReporting - for [%s] - cluster: %s on Attribute: %s " %(key, cluster, attrDisp) )
                    #Domoticz.Log("configureReporting for [%s] - cluster: %s on Attribute: %s >%s< " %(key, cluster, attrDisp, datas) )
                    #sendZigateCmd(self, "0120", datas , 2)
    
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
    Domoticz.Log("identifySend - send an Identify Message to: %s for %04x seconds" %( nwkid, duration))
    Domoticz.Log("identifySend - data sent >%s< " %(datas) )
    sendZigateCmd(self, "0070", datas )
