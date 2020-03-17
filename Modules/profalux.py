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
from Modules.output import sendZigateCmd, raw_APS_request

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
        Domoticz.Log("++++++ Model Name for %s forced to : %s" %(nwkid, self.ListOfDevices[nwkid]['Model']))

    elif self.ListOfDevices[nwkid]['MacCapa'] == '80' and self.ListOfDevices[nwkid]['ZDeviceID'] == '0201':
        # Batterie Device => Remote command
        self.ListOfDevices[nwkid]['Model'] = 'Telecommande-Profalux'
        self.ListOfDevices[nwkid]['Manufacturer Name'] = 'Profalux'
        Domoticz.Log("++++++ Model Name for %s forced to : %s" %(nwkid, self.ListOfDevices[nwkid]['Model']))

def profalux_stop( self, nwkid ):

    # determine which Endpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "fc21" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    cluster_frame = '11'
    sqn = '00'
    cmd = '03'

    payload = cluster_frame + sqn + cmd 
    raw_APS_request( self, nwkid, EPout, 'fc21', '0104', payload, zigate_ep='01')
    Domoticz.Log("profalux_stop ++++ %s/%s payload: %s" %( nwkid, EPout, payload))

    return

def profalux_MoveToLevelWithOnOff( self, nwkid, level):

    # determine which Endpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "fc21" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    cluster_frame = '11'
    sqn = '00'
    cmd = '04'

    payload = cluster_frame + sqn + cmd + '%02x' %level
    raw_APS_request( self, nwkid, EPout, 'fc21', '0104', payload, zigate_ep='01')
    Domoticz.Log("profalux_MoveToLevelWithOnOff ++++ %s/%s Level: %s payload: %s" %( nwkid, EPout, level, payload))
    return

def profalux_MoveWithOnOff( self, nwkid, OnOff):

    if OnOff != 0x00 and OnOff != 0x01:
        return

    # determine which Endpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "fc21" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    cluster_frame = '11'
    sqn = '00'
    cmd = '05'

    payload = cluster_frame + sqn + cmd + '%02x' %OnOff
    raw_APS_request( self, nwkid, EPout, 'fc21', '0104', payload, zigate_ep='01')
    Domoticz.Log("profalux_MoveWithOnOff ++++ %s/%s OnOff: %s payload: %s" %( nwkid, EPout, OnOff, payload))

    return

def profalux_MoveToLiftAndTilt( self, nwkid, level=None, tilt=None):

    if level is None and tilt is None:
        return

    # determine which Endpoint
    EPout = '01'
    for tmpEp in self.ListOfDevices[nwkid]['Ep']:
        if "fc21" in self.ListOfDevices[nwkid]['Ep'][tmpEp]:
            EPout= tmpEp

    cluster_frame = '11'
    sqn = '00'
    cmd = '10'

    if level is None and tilt:
        option = 0x02
        level = 0x00
    elif level and tilt is None:
        option = 0x01
        tilt = 0x00
    elif level and tilt:
        option = 0x03

    payload = cluster_frame + sqn + cmd + '%02x' %option + '%02x' %level + '%02x' %tilt + 'ffff'
    raw_APS_request( self, nwkid, EPout, 'fc21', '0104', payload, zigate_ep='01')
    Domoticz.Log("profalux_MoveToLiftAndTilt ++++ %s/%s level: %s tilt: %s option: %s payload: %s" %( nwkid, EPout, level, tilt, option, payload))

    return
