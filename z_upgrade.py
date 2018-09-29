#!/usr/bin/env python3
# coding: utf-8 -*-
#

import Domoticz

import z_var		  # Global variables


def upgrade_v2( self, Devices ) :

	nbdev = 0
	upgradedone = False
	for x in Devices : # initialise listeofdevices avec les devices en bases domoticz
		if Devices[x].Options.get('TypeName') :
			nbdev = nbdev + 1
			upgradedone = True
			oldDevicesOptions = dict(Devices[x].Options)
			oldTypeName = oldDevicesOptions['TypeName']
			ZigateV2 = eval(oldDevicesOptions['Zigate'])
			ZigateV2['Version'] = "2"
			nValue = Devices[x].nValue
			sValue = Devices[x].sValue

			Domoticz.Status("Upgrading " +str(Devices[x].Name) + " to version 2" )
			Domoticz.Debug("Upgrading " +str(Devices[x].Name) + " to version 2 with Options['Zigate']= " +str(ZigateV2) )

			Devices[x].Update(nValue=int(nValue), sValue=str(sValue), Options={"Zigate":str(ZigateV2),"ClusterType":oldTypeName}, SuppressTriggers=True )

	if upgradedone :
		Domoticz.Status("Upgrade of Zigate structure to V2 completed. " + str(nbdev) + " devices updated")
			
