#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: paramDevice.py

    Description: implement the parameter device specific

"""

import Domoticz

from Modules.philips import philips_set_poweron_after_offon_device, philips_set_pir_occupancySensibility
from Modules.enki import enki_set_poweron_after_offon_device
from Modules.basicOutputs import set_poweron_afteroffon, set_PIROccupiedToUnoccupiedDelay
from Modules.readAttributes import ReadAttributeRequest_0006_400x, ReadAttributeRequest_0406_0010

def sanity_check_of_param( self, NwkId):
    # Domoticz.Log("sanity_check_of_param for %s" %NwkId)
    
    if 'Param' not in self.ListOfDevices[ NwkId ]:
        return

    for param in self.ListOfDevices[ NwkId ]['Param']:
        if param == 'PowerOnAfterOffOn':
            param_PowerOnAfterOffOn(self, NwkId, self.ListOfDevices[ NwkId ]['Param'][ param ])

        if param == 'PIROccupiedToUnoccupiedDelay':
            param_Occupancy_settings_PIROccupiedToUnoccupiedDelay( self, NwkId, self.ListOfDevices[ NwkId ]['Param'][ param ])

        if param == 'occupancySensibility':
            philips_set_pir_occupancySensibility(self, NwkId, self.ListOfDevices[ NwkId ]['Param'][ param ])


def param_Occupancy_settings_PIROccupiedToUnoccupiedDelay( self, nwkid, delay):
    # Based on Philips HUE
    # 0x00 default
    # The PIROccupiedToUnoccupiedDelay attribute is 16 bits in length and 
    # specifies the time delay, in seconds,before the PIR sensor changes to 
    # its unoccupied state after the last detection of movement in the sensed area.

    #Domoticz.Log("param_Occupancy_settings_PIROccupiedToUnoccupiedDelay %s -> delay: %s" %(nwkid, delay))

    if self.ListOfDevices[ nwkid ]['Manufacturer'] == '100b' or self.ListOfDevices[ nwkid ]['Manufacturer Name'] == 'Philips': # Philips
        if '02' not in self.ListOfDevices[ nwkid ]['Ep']:
            return
        if '0406' not in self.ListOfDevices[ nwkid ]['Ep']['02']:
            return
        if '0010' not in self.ListOfDevices[ nwkid ]['Ep']['02']['0406']:
            set_PIROccupiedToUnoccupiedDelay( self, nwkid, delay)
            ReadAttributeRequest_0406_0010(self, nwkid)
        else:
            if int(self.ListOfDevices[ nwkid ]['Ep']['02']['0406']['0010'],16) != delay:
                set_PIROccupiedToUnoccupiedDelay( self, nwkid, delay)
                ReadAttributeRequest_0406_0010(self, nwkid)
    else:
        Domoticz.Log("=====> Unknown Manufacturer/Name")


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