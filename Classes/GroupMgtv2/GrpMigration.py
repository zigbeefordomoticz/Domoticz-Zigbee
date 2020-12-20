# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz

def migrateIfTradfriRemote(self, GrpId):

        if 'Tradfri Remote' not in self.ListOfGroups[GrpId]:
                return
        NwkId = self.ListOfGroups[ GrpId]['Tradfri Remote']['Device Addr']
        Domoticz.Status( "Migration of Ikea Tradfri %s in Group %s" %( NwkId, GrpId))

        if 'Ep' not in self.ListOfGroups[ GrpId]['Tradfri Remote']:
            self.ListOfGroups[ GrpId]['Tradfri Remote']['Ep'] = '01'

        if 'IEEE' not in self.ListOfGroups[ GrpId]['Tradfri Remote']:
            if NwkId in self.ListOfDevices:
                self.ListOfGroups[ GrpId]['Tradfri Remote']['IEEE'] =    self.ListOfDevices[NwkId]['IEEE']     
            else:
                Domoticz.Error("Cannot migrate Tradfri Remote . don't find Nwkid %s" %NwkId)
                del self.ListOfGroups[ GrpId]['Tradfri Remote']

def migrateTupleToList( self, GrpId, tupleItem ):

    lenItem = len(tupleItem)
    if lenItem not in [2, 3]:
        Domoticz.Error("For Group: %s unexpected Group Device %s droping" %( GrpId, str(tupleItem)))
        return
    
    if lenItem == 2:
        NwkId, Ep = tupleItem
        if 'IEEE' not in self.ListOfDevices[ NwkId ]:
            Domoticz.Error("For Group: %s unexpected Group Device %s droping" %( GrpId, str(tupleItem))) 
            return
        Ieee = self.ListOfDevices[ NwkId ]['IEEE']
        # Migrate from Tuple to List
        self.ListOfGroups[ GrpId]['Devices'].remove( ( NwkId, Ep ))
        self.ListOfGroups[ GrpId]['Devices'].append( [ NwkId, Ep, Ieee ])

    elif lenItem == 3:
        # Migrate from Tuple to List
        NwkId, Ep, Ieee = tupleItem
        self.ListOfGroups[ GrpId]['Devices'].remove( ( NwkId, Ep,Ieee ) )
        self.ListOfGroups[ GrpId]['Devices'].append( [ NwkId, Ep, Ieee ])

    Domoticz.Status( "--- --- NwkId: %s Ep: %s Ieee: %s" %( NwkId, Ep, Ieee ))
    if NwkId not in self.ListOfDevices:
        Domoticz.Error("migrateTupleToList - NwkId: %s not found in current database" %NwkId)
        if Ieee not in self.IEEE2NWK:
            return
        NwkId = self.IEEE2NWK[ Ieee ]
        Domoticz.Status("---> Retreive new NwkId: %s from Ieee: %s" %(NwkId, Ieee))

    if 'GroupMemberShip' not in self.ListOfDevices[ NwkId ]:
        self.ListOfDevices[ NwkId ]['GroupMemberShip'] = {}

    if Ep not in self.ListOfDevices[ NwkId ]['GroupMemberShip']:
        self.ListOfDevices[ NwkId ]['GroupMemberShip'][ Ep ] = {}

    if GrpId not in self.ListOfDevices[ NwkId ]['GroupMemberShip'][ Ep ]:
        self.ListOfDevices[ NwkId ]['GroupMemberShip'][ Ep ][GrpId] = {}

    self.ListOfDevices[ NwkId ]['GroupMemberShip'][Ep][ GrpId ]['Status'] = 'OK'
    self.ListOfDevices[ NwkId ]['GroupMemberShip'][Ep][ GrpId ]['TimeStamp'] = 0


def GrpMgtv2Migration( self ):

    Domoticz.Status( "Group Migration to new format")
    for GrpId in self.ListOfGroups:
        Domoticz.Status("--- GroupId: %s" %GrpId)
        migrateIfTradfriRemote( self, GrpId)
   
        for item in list(self.ListOfGroups[ GrpId]['Devices']):
            migrateTupleToList( self, GrpId, item)