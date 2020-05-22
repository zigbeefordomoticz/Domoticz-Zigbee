# !/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: pipiche38
#

import Domoticz

def GrpMgtv2Migration( self ):

  Domoticz.Status("Group Migrating to new format")
  for GrpId in self.ListOfGroups:
    Domoticz.Status("--- GroupId: %s" %GrpId)
    for item in self.ListOfGroups[ GrpId]['Devices']:
      lenItem = len(item)
      if lenItem not in [2, 3]:
        Domoticz.Error("For Group: %s unexpected Group Device %s droping" %( GrpId, str(item)))
        continue

      if lenItem == 2:
          NwkId, Ep = item
          if 'IEEE' not in self.ListOfDevices[ NwkId ]:
              Domoticz.Error("For Group: %s unexpected Group Device %s droping" %( GrpId, str(item))) 
              continue

      elif lenItem == 3:
              NwkId, Ep, Ieee = item

      Domoticz.Status( "--- --- NwkId: %s Ep: %s Ieee: %s" %( NwkId, Ep, Ieee ))
      if 'GroupMemberShip' not in self.ListOfDevices[ NwkId ]:
          self.ListOfDevices[ NwkId ]['GroupMemberShip'] = {}

      if Ep not in self.ListOfDevices[ NwkId ]['GroupMemberShip']:
          self.ListOfDevices[ NwkId ]['GroupMemberShip'][ Ep ] = {}

      if GrpId not in self.ListOfDevices[ NwkId ]['GroupMemberShip'][ Ep ]:
          self.ListOfDevices[ NwkId ]['GroupMemberShip'][ Ep ][GrpId] = {}

      self.ListOfDevices[ NwkId ]['GroupMemberShip'][Ep][ GrpId ]['Status'] = 'OK'
      self.ListOfDevices[ NwkId ]['GroupMemberShip'][Ep][ GrpId ]['TimeStamp'] = 0
