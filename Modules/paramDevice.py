#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: paramDevice.py

    Description: implement the parameter device specific

"""

from Modules.philips import philips_set_poweron_after_offon_device
from Modules.enki import enki_set_poweron_after_offon_device
from Modules.basicOutputs import set_poweron_afteroffon
from Modules.readAttributes import ReadAttributeRequest_0006_400x

def param_PowerOnAfterOffOn(self, nwkid, mode):
    # 0 - stay Off after a Off/On
    # 1 - stay On after a Off/On
    # 255 - stay to previous state after a Off/On

    if mode not in ( 0, 1, 255 ):
        return

    if 'Manufacturer' not in self.ListOfDevices[ nwkid ]:
        return

    if self.ListOfDevices[ nwkid ]['Manufacturer'] == '100b': # Philips
        if '0b' not in self.ListOfDevices[ nwkid ]['Ep']:
            return
        if '0006' not in self.ListOfDevices[ nwkid ]['Ep']['0b']:
            return
        if '4003' not in self.ListOfDevices[ nwkid ]['Ep']['0b']['0006']:
            return
        if self.ListOfDevices[ nwkid ]['Ep']['0b']['0006']['4003'] != str(mode):
            philips_set_poweron_after_offon_device( self, mode, nwkid)
            ReadAttributeRequest_0006_400x(self, nwkid)

    elif self.ListOfDevices[ nwkid ]['Manufacturer'] == '1277': # Enki Leroy Merlin
        if '01' not in self.ListOfDevices[ nwkid ]['Ep']:
            return
        if '0006' not in self.ListOfDevices[ nwkid ]['Ep']['01']:
            return
        if '4003' not in self.ListOfDevices[ nwkid ]['Ep']['01']['0006']:
            return
        if self.ListOfDevices[ nwkid ]['Ep']['01']['0006']['4003'] != str(mode):
            enki_set_poweron_after_offon_device( self, mode, nwkid)
            ReadAttributeRequest_0006_400x(self, nwkid)

    else:
        # Ikea, Legrand, Tuya ( 'TS0121' BlitzWolf )
        for ep in self.ListOfDevices[ nwkid ]['Ep']:
            if '0006' not in self.ListOfDevices[ nwkid ]['Ep'][ ep ]:
                continue
            
            if '4003' in self.ListOfDevices[ nwkid ]['Ep'][ ep ]['0006'] and self.ListOfDevices[ nwkid ]['Ep'][ ep ]['0006']['4003'] == str(mode):
                    continue
                
            elif '8002' in self.ListOfDevices[ nwkid ]['Ep'][ ep ]['0006'] and self.ListOfDevices[ nwkid ]['Ep'][ ep ]['0006']['8002'] == str(mode):
                    continue
   
            set_poweron_afteroffon( self, nwkid, mode)
            ReadAttributeRequest_0006_400x(self, nwkid)