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
from Modules.output import sendZigateCmd, raw_APS_request
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
    if 'Ep' in self.ListOfDevices[nwkid]:
        if '01' in self.ListOfDevices[nwkid]['Ep']:
            if '0000' in self.ListOfDevices[nwkid]['Ep']['01']:
                if '0010' in self.ListOfDevices[nwkid]['Ep']['01']['0000']:
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

    cluster_frame = '11'
    sqn = '00'
    if 'SQN' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['SQN'] != {} and self.ListOfDevices[nwkid]['SQN'] != '':
            sqn = '%02x' % (int(self.ListOfDevices[nwkid]['SQN'],16) + 1)

    cmd = '03' # Ask the Tilt Blind to stop moving

    payload = cluster_frame + sqn + cmd 
    raw_APS_request( self, nwkid, EPout, '0008', '0104', payload, zigate_ep=ZIGATE_EP)
    loggingProfalux( self, 'Log', "profalux_stop ++++ %s/%s payload: %s" %( nwkid, EPout, payload), nwkid)

    return

def profalux_MoveToLevelWithOnOff( self, nwkid, level):

    # determine which Endpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "0008" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    cluster_frame = '11'
    sqn = '00'
    if 'SQN' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['SQN'] != {} and self.ListOfDevices[nwkid]['SQN'] != '':
            sqn = '%02x' %(int(self.ListOfDevices[nwkid]['SQN'],16) + 1)

    cmd = '04' # Ask the Tilt Blind to go to a certain Level

    payload = cluster_frame + sqn + cmd + '%02x' %level
    raw_APS_request( self, nwkid, EPout, '0008', '0104', payload, zigate_ep=ZIGATE_EP)
    loggingProfalux( self, 'Log', "profalux_MoveToLevelWithOnOff ++++ %s/%s Level: %s payload: %s" %( nwkid, EPout, level, payload), nwkid)
    return

def profalux_MoveWithOnOff( self, nwkid, OnOff):

    if OnOff != 0x00 and OnOff != 0x01:
        return

    # determine which Endpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "0008" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    cluster_frame = '11'

    sqn = '00'
    if 'SQN' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['SQN'] != {} and self.ListOfDevices[nwkid]['SQN'] != '':
            sqn = '%02x' %(int(self.ListOfDevices[nwkid]['SQN'],16) + 1)

    cmd = '05'  # Ask the Tilt Blind to open or Close

    payload = cluster_frame + sqn + cmd + '%02x' %OnOff
    raw_APS_request( self, nwkid, EPout, '0008', '0104', payload, zigate_ep=ZIGATE_EP)
    loggingProfalux( self, 'Log', "profalux_MoveWithOnOff ++++ %s/%s OnOff: %s payload: %s" %( nwkid, EPout, OnOff, payload), nwkid)

    return

def profalux_MoveToLiftAndTilt( self, nwkid, level=None, tilt=None):

    if level is None and tilt is None:
        return

    # determine which Endpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "0008" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    # Frame Control Field:
    #   0x10: Client to Server
    #   0x18: Server to Client
    #   0x14: Manuf Specific / Client to Server
    #   0x1c: Manuf Specific / Server to Client

    cluster_frame = '18'
    sqn = '00'
    if 'SQN' in self.ListOfDevices[nwkid]:
        if self.ListOfDevices[nwkid]['SQN'] != {} and self.ListOfDevices[nwkid]['SQN'] != '':
            sqn = '%02x' %(int(self.ListOfDevices[nwkid]['SQN'],16) + 1)

    cmd = '10' # Propriatary Command: Ask the Tilt Blind to go to a Certain Position and Orientate to a certain angle

    if level:
        level = ( 254 * level ) // 100

    if level and tilt:
        option = 0x03
    elif tilt:
        option = 0x02
        level = 0x00
    elif level:
       option = 0x01
       tilt = 0x00
    else:
        Domoticz.Error( "profalux_MoveToLiftAndTilt - level: %s titl: %s" %(level, tilt) )
        return
    
    # payload: 11 45 10 03 55 2d ffff
    # Option Parameter uint8   Bit0 Ask for lift action, Bit1 Ask fr a tilt action
    # Lift Parameter   uint8   Lift value between 1 to 254
    # Tilt Parameter   uint8   Tilt value between 0 and 90
    # Transition Time  uint16  Transition Time between current and asked position
    loggingProfalux( self, 'Log', "profalux_MoveToLiftAndTilt 0x18 ++++ %s/%s level: %s tilt: %s option: %s payload: %s" %( nwkid, EPout, level, tilt, option, payload), nwkid)
    payload = cluster_frame + sqn + cmd + '%02x' %option + '%02x' %level + '%02x' %tilt + 'ffff'
    raw_APS_request( self, nwkid, EPout, '0008', '0104', payload, zigate_ep=ZIGATE_EP)
 
    loggingProfalux( self, 'Log', "profalux_MoveToLiftAndTilt 0x10 ++++ %s/%s level: %s tilt: %s option: %s payload: %s" %( nwkid, EPout, level, tilt, option, payload), nwkid)   
    cluster_frame = '10'
    payload = cluster_frame + sqn + cmd + '%02x' %option + '%02x' %level + '%02x' %tilt + 'ffff'
    raw_APS_request( self, nwkid, EPout, '0008', '0104', payload, zigate_ep=ZIGATE_EP)
 
    loggingProfalux( self, 'Log', "profalux_MoveToLiftAndTilt 0x14 ++++ %s/%s level: %s tilt: %s option: %s payload: %s" %( nwkid, EPout, level, tilt, option, payload), nwkid)
    cluster_frame = '14'
    payload = cluster_frame + sqn + cmd + '%02x' %option + '%02x' %level + '%02x' %tilt + 'ffff'
    raw_APS_request( self, nwkid, EPout, '0008', '0104', payload, zigate_ep=ZIGATE_EP)

    loggingProfalux( self, 'Log', "profalux_MoveToLiftAndTilt 0x1c ++++ %s/%s level: %s tilt: %s option: %s payload: %s" %( nwkid, EPout, level, tilt, option, payload), nwkid)
    cluster_frame = '1c'
    payload = cluster_frame + sqn + cmd + '%02x' %option + '%02x' %level + '%02x' %tilt + 'ffff'
    raw_APS_request( self, nwkid, EPout, '0008', '0104', payload, zigate_ep=ZIGATE_EP)
    return
