#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module: ListOfDevices.py

    Description: Manage all recorded Devices

"""
MAX_CMD_PER_DEVICE = 5

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
        
        return False

    def add_Last_Cmds( self, nwkid, data):
        
        if nwkid in self.ListOfDevices:
            if 'Last Cmds' not in self.ListOfDevices[nwkid]:
                self.ListOfDevices[nwkid]['Last Cmds'] = []
            if isinstance(self.ListOfDevices[nwkid]['Last Cmds'], dict ):
                self.ListOfDevices[nwkid]['Last Cmds'] = []

            if len(self.ListOfDevices[nwkid]['Last Cmds']) >= MAX_CMD_PER_DEVICE:
                # Remove the First element in the list.
                self.ListOfDevices[nwkid]['Last Cmds'].pop(0)

            self.ListOfDevices[nwkid]['Last Cmds'].append( data )

    def retreive( self, nwkid):
        if nwkid in self.ListOfDevices:
            return self.ListOfDevices[nwkid]

