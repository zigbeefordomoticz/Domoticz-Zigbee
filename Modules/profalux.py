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

    location =''
    if (
        'Ep' in self.ListOfDevices[nwkid]
        and '01' in self.ListOfDevices[nwkid]['Ep']
        and '0000' in self.ListOfDevices[nwkid]['Ep']['01']
        and '0010' in self.ListOfDevices[nwkid]['Ep']['01']['0000']
    ):
        location = self.ListOfDevices[nwkid]['Ep']['01']['0000']['0010']

    if self.ListOfDevices[nwkid]['MacCapa'] == '8e' and self.ListOfDevices[nwkid]['ZDeviceID'] == '0200':
        self.ListOfDevices[nwkid]['Manufacturer Name'] = 'Profalux'
        # Main Powered device => Volet or BSO
        self.ListOfDevices[nwkid]['Model'] = 'VoletBSO-Profalux'
        if location.find('bso') != -1:
            self.ListOfDevices[nwkid]['Model'] = 'BSO-Profalux'
        if location.find('volet') != -1:
            self.ListOfDevices[nwkid]['Model'] = 'Volet-Profalux'
        loggingProfalux( self, 'Log', "++++++ Model Name for %s forced to : %s" %(nwkid, self.ListOfDevices[nwkid]['Model']), nwkid)

    elif self.ListOfDevices[nwkid]['MacCapa'] == '80' and self.ListOfDevices[nwkid]['ZDeviceID'] == '0201':
        # Batterie Device => Remote command
        self.ListOfDevices[nwkid]['Model'] = 'Telecommande-Profalux'
        self.ListOfDevices[nwkid]['Manufacturer Name'] = 'Profalux'
        loggingProfalux( self, 'Log', "++++++ Model Name for %s forced to : %s" %(nwkid, self.ListOfDevices[nwkid]['Model']), nwkid)

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
    loggingProfalux( self, 'Log', "profalux_stop ++++ %s/%s payload: %s" %( nwkid, EPout, payload), nwkid)

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
    loggingProfalux( self, 'Log', "profalux_MoveToLevelWithOnOff ++++ %s/%s Level: %s payload: %s" %( nwkid, EPout, level, payload), nwkid)
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
    loggingProfalux( self, 'Log', "profalux_MoveWithOnOff ++++ %s/%s OnOff: %s payload: %s" %( nwkid, EPout, OnOff, payload), nwkid)

    return

def profalux_MoveToLiftAndTilt( self, nwkid, level=None, tilt=None):

    def checkLevel( level):
        # Receive a value between 0 to 100
        if level == 0:
            level = 1
        elif level > 100:
            level = 100
        return ( 254 * level ) // 100

    def checkTilt( tilt ):
        # Receive a value between 0 to 90
        if tilt > 90:
            tilt = 90
        return tilt

    # Begin

    loggingProfalux( self, 'Log', "profalux_MoveToLiftAndTilt Nwkid: %s Level: %s Tilt: %s" %( nwkid, level, tilt))
    if level is None and tilt is None:
        return

    if level is None:
        # Let's check if we can get the Level from Attribute
        if '01' in self.ListOfDevices[ nwkid ]['Ep']:
            if '0008' in self.ListOfDevices[ nwkid ]['Ep']['01']:
                if '0000' in self.ListOfDevices[ nwkid ]['Ep']['01']['0008']:
                    level = int(self.ListOfDevices[ nwkid ]['Ep']['01']['0008']['0000'], 16)
                    Domoticz.Log("Retreive Level: %s" %level)

    if tilt is None:
        tilt = self.pluginconf.pluginConf['profaluxOrientBSO'] 
        # Let's check if we can get the Tilt from Attribute
        if '01' in self.ListOfDevices[ nwkid ]['Ep']:
            if 'fc21' in self.ListOfDevices[ nwkid ]['Ep']['01']:
                if '0001' in self.ListOfDevices[ nwkid ]['Ep']['01']['fc21']:
                    level = int(self.ListOfDevices[ nwkid ]['Ep']['01']['fc21']['0001'], 16)
                    Domoticz.Log("Retreive Tilt: %s" %level)

    loggingProfalux( self, 'Log', "profalux_MoveToLiftAndTilt after update Nwkid: %s Level: %s Tilt: %s" %( nwkid, level, tilt))
    
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
    level = checkLevel( level )
    tilt = checkTilt( tilt)

    # compute option 0x01 level, 0x02 tilt, 0x03 level + tilt    
    if level and tilt:
        option = 0x03
    elif tilt:
        option = 0x02
        level = 0x00
    elif level:
       option = 0x01
       tilt = 0x00
    
    Domoticz.Log("profalux_MoveToLiftAndTilt - Level: %s Tilt: %s" %( level, tilt))

    # payload: 11 45 10 03 55 2d ffff
    # Option Parameter uint8   Bit0 Ask for lift action, Bit1 Ask fr a tilt action
    # Lift Parameter   uint8   Lift value between 1 to 254
    # Tilt Parameter   uint8   Tilt value between 0 and 90
    # Transition Time  uint16  Transition Time between current and asked position
    
    ManfufacturerCode = '1110'

    sqn = '%02x' %(int(sqn,16) + 1)
    payload = cluster_frame + ManfufacturerCode[2:4] + ManfufacturerCode[0:2] + sqn + cmd + '%02x' %option + '%02x' %level + '%02x' %tilt + 'FFFF'
    loggingProfalux( self, 'Log', "profalux_MoveToLiftAndTilt %s ++++ %s %s/%s level: %s tilt: %s option: %s payload: %s" %( cluster_frame, sqn, nwkid, EPout, level, tilt, option, payload), nwkid)
    raw_APS_request( self, nwkid, '01', '0008', '0104', payload, zigate_ep=ZIGATE_EP)