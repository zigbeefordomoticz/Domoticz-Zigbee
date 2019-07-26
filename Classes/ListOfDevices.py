#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: ListOfDevices.py

    Description: Manage all recorded Devices

"""

class ListOfDevices():

    def __init__( self, ListOfDevices, IEEE2NWK ):
        self.ListOfDevices = ListOfDevices
        self.IEEE2NWK = IEEE2NWK

    def find( self, nwkid=None, ieee=None):
        if ieee == nwkid == None:
            return False

        if nwkid is None and ieee:
            if ieee not in self.IEEE2NWK:
                    return False
            nwkid = self.IEEE2NWK['IEEE']

        if nwkid in self.ListOfDevices:
            return nwkid
        else:
            return False

    def retreive( self, nwkid):
        if nwkid in self.ListOfDevices:
            return self.ListOfDevices[nwkid]



    
