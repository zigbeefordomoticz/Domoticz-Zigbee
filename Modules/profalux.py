#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: profalux.py

    Description: 

"""

import Domoticz
from Modules.zigateConsts import ZIGATE_EP
from Modules.basicOutputs import sendZigateCmd, raw_APS_request
from Modules.logging import loggingProfalux

def profalux_fake_deviceModel( self , nwkid):

    """ 
    This method is called when in pairing process and the Manufacturer code is Profalux ( 0x1110 )
    The purpose will be to create a fake Model Name in order to use the Certified Device Conf
    """

    if nwkid not in self.ListOfDevices:
        return

    if 'ZDeviceID' not in self.ListOfDevices[nwkid]:
        return

    if 'ProfileID' not in self.ListOfDevices[nwkid]:
        return

    if 'MacCapa' not in self.ListOfDevices[nwkid]:
        return

    if 'Manufacturer' not in self.ListOfDevices[nwkid]:
        return

    if self.ListOfDevices[nwkid]['Manufacturer'] != '1110':
        return

    self.ListOfDevices[nwkid]['Manufacturer Name'] = 'Profalux'

    location =''
    if (
        'Ep' in self.ListOfDevices[nwkid]
        and '01' in self.ListOfDevices[nwkid]['Ep']
        and '0000' in self.ListOfDevices[nwkid]['Ep']['01']
        and '0010' in self.ListOfDevices[nwkid]['Ep']['01']['0000']
    ):
        location = self.ListOfDevices[nwkid]['Ep']['01']['0000']['0010']

    if self.ListOfDevices[nwkid]['MacCapa'] == '8e' and self.ListOfDevices[nwkid]['ZDeviceID'] == '0200':
    
        # Main Powered device => Volet or BSO
        self.ListOfDevices[nwkid]['Model'] = 'VoletBSO-Profalux'

        if location in ( 'BSO', 'bso', 'Bso'):
            # We found a BSO in attrbute 0010
            self.ListOfDevices[nwkid]['Model'] = 'BSO-Profalux'

        elif location in ( 'VOLET', 'volet', 'Volet' ):
            # We found a VR
            self.ListOfDevices[nwkid]['Model'] = 'Volet-Profalux'

        loggingProfalux( self, 'Debug', "++++++ Model Name for %s forced to : %s due to location: %s" %(nwkid, self.ListOfDevices[nwkid]['Model'], location), nwkid)

    elif self.ListOfDevices[nwkid]['MacCapa'] == '80':

        # Batterie Device => Remote command
        self.ListOfDevices[nwkid]['Model'] = 'Telecommande-Profalux'

        loggingProfalux( self, 'Debug', "++++++ Model Name for %s forced to : %s" %(nwkid, self.ListOfDevices[nwkid]['Model']), nwkid)

def checkAndTriggerConfigReporting( self, NwkId):

    loggingProfalux(self, 'Debug', "-- -- checkAndTriggerConfigReporting for %s" %NwkId)
    if 'ConfigureReporting' not in self.ListOfDevices[NwkId]:
        configureReportingForprofalux( self, NwkId)
        return
    if '01' not in self.ListOfDevices[NwkId]['ConfigureReporting']['Ep']:
        configureReportingForprofalux( self, NwkId)
        return
    if 'fc21' not in self.ListOfDevices[NwkId]['ConfigureReporting']['Ep']['01']:
        configureReportingForprofalux( self, NwkId)
        return
    if self.ListOfDevices[NwkId]['ConfigureReporting']['Ep']['01']['fc21'] == {}:
        configureReportingForprofalux( self, NwkId)
        return

def configureReportingForprofalux( self, NwkId):

    loggingProfalux(self, 'Debug', "-- -- -- configureReportingForprofalux for %s" %NwkId)
    if NwkId not in self.ListOfDevices:
        return

    attrList = '00' + '20' + '0001' + '0000' + '0000' + '0000' + '00'
    datas =   '02' + NwkId + ZIGATE_EP + '01' + 'fc21' + '00' + '01' + '1110' + '01' + attrList
    sendZigateCmd( self, "0120", datas )
    loggingProfalux(self, 'Debug', "-- -- -- configureReportingForprofalux for %s data: %s" %(NwkId, datas))

    # Configure Reporting iin Raw Mode
    #ZCLFrameControl = '04'
    #ManfufacturerCode = '1110'
    #Attribute = '0001'

    #sqn = '01'
    #if 'SQN' in self.ListOfDevices[NwkId]:
    #    if self.ListOfDevices[NwkId]['SQN'] != {} and self.ListOfDevices[NwkId]['SQN'] != '':
    #        sqn = '%02x' %(int(self.ListOfDevices[NwkId]['SQN'],16) + 1)
    #cmd = '06' 
    #payload = ZCLFrameControl + ManfufacturerCode[2:4] + ManfufacturerCode[0:2] + sqn + cmd + '00' + Attribute[2:4] + Attribute[0:2] + '20' + '0000' + '0000' + '00'

    #loggingProfalux( self, 'Log', "configureReportingForprofalux RAW APS %s %s" %(NwkId, payload))
    #raw_APS_request( self, NwkId, '01', 'fc21', '0104', payload, zigate_ep=ZIGATE_EP)

def profalux_stop( self, nwkid ):

    # determine which Endpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "0008" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    cluster_frame = '01'
    sqn = '00'
    if ( 'SQN' in self.ListOfDevices[nwkid] and self.ListOfDevices[nwkid]['SQN'] != {} and self.ListOfDevices[nwkid]['SQN'] != '' ):
        sqn = '%02x' % (int(self.ListOfDevices[nwkid]['SQN'],16) + 1)

    cmd = '03' # Ask the Tilt Blind to stop moving

    payload = cluster_frame + sqn + cmd
    raw_APS_request( self, nwkid, EPout, '0008', '0104', payload, zigate_ep=ZIGATE_EP)
    loggingProfalux( self, 'Debug', "profalux_stop ++++ %s/%s payload: %s" %( nwkid, EPout, payload), nwkid)

def profalux_MoveToLevelWithOnOff( self, nwkid, level):

    # determine which Endpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "0008" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    cluster_frame = '01'
    sqn = '00'
    if (
        'SQN' in self.ListOfDevices[nwkid]
        and self.ListOfDevices[nwkid]['SQN'] != {}
        and self.ListOfDevices[nwkid]['SQN'] != ''
    ):
        sqn = '%02x' %(int(self.ListOfDevices[nwkid]['SQN'],16) + 1)

    cmd = '04' # Ask the Tilt Blind to go to a certain Level

    payload = cluster_frame + sqn + cmd + '%02x' %level
    raw_APS_request( self, nwkid, EPout, '0008', '0104', payload, zigate_ep=ZIGATE_EP)
    loggingProfalux( self, 'Debug', "profalux_MoveToLevelWithOnOff ++++ %s/%s Level: %s payload: %s" %( nwkid, EPout, level, payload), nwkid)
    return

def profalux_MoveWithOnOff( self, nwkid, OnOff):

    if OnOff not in [0x00, 0x01]:
        return

    # determine which Endpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "0008" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    cluster_frame = '11'

    sqn = '00'
    if (
        'SQN' in self.ListOfDevices[nwkid]
        and self.ListOfDevices[nwkid]['SQN'] != {}
        and self.ListOfDevices[nwkid]['SQN'] != ''
    ):
        sqn = '%02x' %(int(self.ListOfDevices[nwkid]['SQN'],16) + 1)

    cmd = '05'  # Ask the Tilt Blind to open or Close

    payload = cluster_frame + sqn + cmd + '%02x' %OnOff
    raw_APS_request( self, nwkid, EPout, '0008', '0104', payload, zigate_ep=ZIGATE_EP)
    loggingProfalux( self, 'Debug', "profalux_MoveWithOnOff ++++ %s/%s OnOff: %s payload: %s" %( nwkid, EPout, OnOff, payload), nwkid)

    return

def profalux_MoveToLiftAndTilt( self, nwkid, level=None, tilt=None):

    def getLevel( self, nwkid):
        # Let's check if we can get the Level from Attribute
        level = None
        if (
            '01' in self.ListOfDevices[nwkid]['Ep']
            and '0008' in self.ListOfDevices[nwkid]['Ep']['01']
            and '0000' in self.ListOfDevices[nwkid]['Ep']['01']['0008']
        ):
            level = int(self.ListOfDevices[ nwkid ]['Ep']['01']['0008']['0000'], 16)

        return  level

    def getTilt( self, nwkid):
        tilt = self.pluginconf.pluginConf['profaluxOrientBSO']
        # Let's check if we can get the Tilt from Attribute
        if ( '01' in self.ListOfDevices[nwkid]['Ep'] and 'fc21' in self.ListOfDevices[nwkid]['Ep']['01'] and '0001' in self.ListOfDevices[nwkid]['Ep']['01']['fc21'] ):
            tilt = int(self.ListOfDevices[ nwkid ]['Ep']['01']['fc21']['0001'], 16)
        return tilt

    def setLevel( self, nwkid, level):
        if '01' not in self.ListOfDevices[nwkid]['Ep']:
            self.ListOfDevices[nwkid]['Ep']['01'] = {}
        if '0008' not in self.ListOfDevices[nwkid]['Ep']['01']:
            self.ListOfDevices[nwkid]['Ep']['01']['0008'] = {}
        self.ListOfDevices[nwkid]['Ep']['01']['0008']['0000'] = '%02x' %level

    def setTilt(self, nwkid, tilt):
        if '01' not in self.ListOfDevices[nwkid]['Ep']:
            self.ListOfDevices[nwkid]['Ep']['01'] = {}
        if 'fc21' not in self.ListOfDevices[nwkid]['Ep']['01']:
            self.ListOfDevices[nwkid]['Ep']['01']['fc21'] = {}
        self.ListOfDevices[nwkid]['Ep']['01']['fc21']['0001'] = '%02x' %tilt


    # Begin
    loggingProfalux( self, 'Debug', "profalux_MoveToLiftAndTilt Nwkid: %s Level: %s Tilt: %s" %( nwkid, level, tilt))
    if level is None and tilt is None:
        return

    # Disabled until 3.1c
    #checkAndTriggerConfigReporting( self, nwkid)
    if level is None:
        level = getLevel( self, nwkid)
 
    if tilt is None:
        tilt = getTilt( self, nwkid)

    loggingProfalux( self, 'Debug', "profalux_MoveToLiftAndTilt after update Nwkid: %s Level: %s Tilt: %s" %( nwkid, level, tilt))
    
    # determine which Endpoint
    EPout = '01'

    # Cluster Frame:
    #  Frame Type: Cluster Command (1)
    #  Manufacturer Specific True
    #  Command Direction: Client to Server (0)
    #  Disable default response: false
    #  Reserved : 0x00
    cluster_frame = '05'

    sqn = '00'
    if 'SQN' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['SQN'] != {} and self.ListOfDevices[nwkid]['SQN'] != '':
            sqn = '%02x' %(int(self.ListOfDevices[nwkid]['SQN'],16) + 1)


    cmd = '10' # Propriatary Command: Ask the Tilt Blind to go to a Certain Position and Orientate to a certain angle

    # compute option 0x01 level, 0x02 tilt, 0x03 level + tilt    
    if level and tilt:
        option = 0x03
    elif tilt:
        option = 0x02
        level = 0x00
    elif level:
       option = 0x01
       tilt = 0x00
    
    if tilt == 0:
        tilt = 1
    setTilt( self, nwkid, tilt)
    setLevel( self, nwkid, level)

    # payload: 11 45 10 03 55 2d ffff
    # Option Parameter uint8   Bit0 Ask for lift action, Bit1 Ask fr a tilt action
    # Lift Parameter   uint8   Lift value between 1 to 254
    # Tilt Parameter   uint8   Tilt value between 0 and 90
    # Transition Time  uint16  Transition Time between current and asked position
    
    ManfufacturerCode = '1110'



    payload = cluster_frame + ManfufacturerCode[2:4] + ManfufacturerCode[0:2] + sqn + cmd + '%02x' %option + '%02x' %level + '%02x' %tilt + 'FFFF'
    loggingProfalux( self, 'Debug', "profalux_MoveToLiftAndTilt %s ++++ %s %s/%s level: %s tilt: %s option: %s payload: %s" %( cluster_frame, sqn, nwkid, EPout, level, tilt, option, payload), nwkid)
    raw_APS_request( self, nwkid, '01', '0008', '0104', payload, zigate_ep=ZIGATE_EP)
