#!/usr/bin/env python3
# coding: utf-8 -*-
#

import Domoticz

import z_var		  # Global variables


def upgrade_v2( self, Devices ) :

	for x in Devices : # initialise listeofdevices avec les devices en bases domoticz
		if Devices[x].Options.get('TypeName') :
			Domoticz.Status("You need to upgrade the Domoticz database in order to run this version of the plugin")

			oldDevicesOptions = dict(Devices[x].Options)
			oldTypeName = oldDevicesOptions['TypeName']
			ZigateV2 = dict(oldDevicesOptions['Zigate'])
			ZigateV2['Version'] = '2'
			nValue = Devices[x].nValue
			sValue = Devices[x].sValue

			Domoticz.Status("Upgrading " +str(Devices[x].Name) + " to version 2" )
			Domoticz.Log("Upgrading " +str(Devices[x].Name) + " to version 2 with Options['Zigate']= " +str(OptionsV2) )

			#Devices[x].Update(nValue=int(nValue), sValue=str(sValue), Options={"Zigate":str(ZigateV2),"ClusterType":oldTypeName}, SuppressTriggers=True )
			
